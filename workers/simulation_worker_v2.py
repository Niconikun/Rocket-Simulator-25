"""
Simulation Worker V2 - Using New Rocket Architecture

This is the Phase 4 version of simulation_worker that uses the new
component-based Rocket architecture with dependency injection.

This file demonstrates how to migrate from the legacy approach to the
new architecture. It maintains the same interface as SimulationWorker
for backward compatibility.

Status: Work in Progress - Phase 4

To use this instead of the legacy simulation_worker:
    from workers.simulation_worker_v2 import SimulationWorkerV2 as SimulationWorker
"""

from PyQt6.QtCore import QThread, pyqtSignal
from models.app_state import ApplicationState
from src.models.state import StateProvider, StateProxy
from src.models.rocket.rocket import Rocket as NewRocket
from src.models.rocket.factory import create_rocket_from_config
from src.models.planet import Planet
from src.models.atmosphere import Atmosphere
from src.models.clock import Clock
from src.models.parachute import Parachute
from src.models.engine import EnhancedEngine
from src.utils.mattools import MatTools as Mat
from src.utils.wind_utils import create_wind_model_from_state, log_wind_config
from src.utils.simulation_validator import SimulationValidator
from workers.simulation_cache import get_cache, SimulationCache
import logging
import json
import os
import copy
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Constants
DEG_TO_RAD = np.pi / 180.0

# Use StateProxy from src.models.state for new code
_StateProxy = StateProxy


class SimulationWorkerV2(QThread):
    """
    Worker thread for executing rocket flight simulations using the NEW architecture.
    
    This is the Phase 4 version that uses component-based Rocket with dependency injection.
    
    Uses new physics models from src/models/rocket/:
    - NewRocket: Component-based with dependency injection
    - RocketState: Pure state management
    - RocketDynamics: Force and torque calculations
    - RocketSimulation: Numerical integration and history
    
    Emits signals:
    - progress: (float) 0.0 to 1.0 indicating simulation progress
    - finished: (dict) simulation results with trajectory and metrics
    - error: (str) error message if simulation fails
    
    Comparison to Legacy SimulationWorker:
    - Simpler: ~15 method calls per step → 1 step() call
    - Clearer: Each component has a single responsibility
    - More testable: Dependencies can be mocked
    - More maintainable: Clear separation of concerns
    """
    
    # Define signals (same as legacy)
    progress = pyqtSignal(float)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, state: StateProvider, use_cache: bool = True):
        """Initialize simulation worker with a state provider."""
        super().__init__()
        self.state = state
        self.is_running = True
        self.is_paused = False
        self.use_cache = use_cache
        self._cache: Optional[SimulationCache] = None
        if self.use_cache:
            self._cache = get_cache()
    
    def run(self):
        """Execute the simulation with new physics architecture."""
        try:
            results = self._run_core()
            self.finished.emit(results)
        except Exception as e:
            logger.error(f"Simulation error: {str(e)}", exc_info=True)
            self.error.emit(f"Simulation failed: {str(e)}")

    def _run_core(self) -> dict:
        """
        Core simulation logic using new architecture.
        
        This is the Phase 4 implementation that uses the new Rocket class.
        """
        # Get simulation parameters from state
        state_dict = self.state.get_all()
        
        # Extract parameters
        launch_elevation_angle = state_dict.get('launch_elevation_angle', 85.0)
        launch_azimuth = state_dict.get('launch_azimuth', 0.0)
        launch_roll = state_dict.get('launch_roll', 0.0)
        runtime = state_dict.get('runtime', 10.0)
        timestep = state_dict.get('timestep', 0.1)
        temperature = state_dict.get('average_temperature', 15.0)
        latitude = state_dict.get('latitude', 0.0)
        longitude = state_dict.get('longitude', 0.0)
        altitude = state_dict.get('altitude', 0.0)
        rocket_name = state_dict.get('rocket', 'coasting_test_rocket')
        location_name = state_dict.get('location', 'default')
        
        # Calculate GMST
        sim_datetime = datetime.now()
        gmst_0 = Mat.gmst_from_date(sim_datetime)
        
        # Initialize coordinates
        coordinates = np.array([latitude, longitude, altitude])
        
        # Create initial state vectors
        r_enu_0 = np.array([0.0, 0.0, 0.0])  # Starting at launch site
        v_enu_0 = np.array([0.0, 0.0, 0.0])  # Starting from rest
        
        # Initialize attitude (quaternions)
        q_pitch = np.array([
            0,
            np.sin(-launch_elevation_angle * 0.5 * DEG_TO_RAD),
            0,
            np.cos(-launch_elevation_angle * 0.5 * DEG_TO_RAD)
        ])
        
        q_yaw = np.array([
            0,
            0,
            np.sin(launch_azimuth * 0.5 * DEG_TO_RAD),
            np.cos(launch_azimuth * 0.5 * DEG_TO_RAD)
        ])
        
        q_roll = np.array([
            np.sin(launch_roll * 0.5 * DEG_TO_RAD),
            0,
            0,
            np.cos(launch_roll * 0.5 * DEG_TO_RAD)
        ])
        
        q_temp = Mat.hamilton(q_pitch, q_roll)
        q_enu2b_0 = Mat.hamilton(q_yaw, q_temp)
        
        # Angular velocity (start from rest)
        w_enu_0 = np.array([0.0, 0.0, 0.0])
        
        # Create physics objects with caching
        if self._cache is not None:
            earth = self._cache.get_planet(latitude, longitude, gmst_0)
            atmosphere = self._cache.get_atmosphere(temperature)
        else:
            earth = Planet(gmst_0)
            atmosphere = Atmosphere(temperature)
        
        # =====================================================================
        # PHASE 4: Use new architecture with dependency injection
        # =====================================================================
        
        # Load rocket configuration
        try:
            with open(f'data/rockets/configs/{rocket_name}.json', 'r') as f:
                rocket_config = json.load(f)
        except FileNotFoundError:
            raise ValueError(f"Rocket configuration not found: {rocket_name}")
        
        # Get initial mass from config or use default
        initial_mass = rocket_config.get('initial_mass', 10.0)
        
        # Use factory to create properly configured rocket
        rocket, rocket_config, engine, aerodynamics, atm = create_rocket_from_config(
            r_enu_0=r_enu_0,
            v_enu_0=v_enu_0,
            q_enu2b_0=q_enu2b_0,
            w_enu_0=w_enu_0,
            initial_mass=initial_mass,
            rocket_name=rocket_name,
            temperature=temperature,
            reference_area=rocket_config.get('reference_area', 0.01)
        )
        
        # Note: The factory returns the atmosphere it created, but we may have
        # a cached one. Use the cached one if available.
        if self._cache is not None:
            rocket.set_atmosphere(atmosphere)
        
        # ===== WIND MODEL INITIALIZATION =====
        wind_config = self.state.get_all()
        if self._cache is not None:
            wind = self._cache.get_wind_model(wind_config)
        else:
            wind = create_wind_model_from_state(wind_config)
        
        if wind is not None:
            log_wind_config(wind_config, wind)
            logger.info(f"Wind simulation enabled: {wind.get_info()['model_type']}")
        else:
            logger.info("Wind simulation disabled")
        
        # Get reference area
        reference_area = rocket_config.get('reference_area', 0.01)
        
        # ===== PARACHUTE INITIALIZATION =====
        # Create parachute if configured
        parachute = None
        parachute_config = rocket_config.get('parachute')
        if parachute_config:
            parachute = Parachute(**parachute_config)
            rocket.has_parachute = True
        
        # Simulation parameters
        num_steps = int(runtime / timestep)
        
        # Termination conditions
        max_altitude = 200000.0  # 200 km
        max_range = 500000.0  # 500 km
        
        # Results storage
        trajectory = []
        metrics = {
            'max_altitude': 0.0,
            'max_velocity': 0.0,
            'max_accel_g': 0.0,
            'max_mach': 0.0,
            'max_range': 0.0,
            'flight_duration': 0.0,
            'apogee_time': 0.0,
            'launch_time': str(sim_datetime),
            'rocket': rocket_name,
            'location': location_name,
        }
        
        # Phase 1: Diagnostic tracking
        termination_reason = None
        termination_step = None
        
        logger.info(f"Starting simulation loop: {num_steps} steps, {timestep}s timestep")
        logger.info(f"Requested runtime: {runtime}s, Timestep: {timestep}s")
        
        # Main simulation loop
        t = 0.0
        prev_altitude = 0.0
        apogee_reached = False
        
        for i in range(num_steps):
            if not self.is_running:
                termination_reason = "USER_STOP: Simulation cancelled by user"
                termination_step = i
                break
            
            # Cooperative pause
            while self.is_paused and self.is_running:
                self.msleep(50)
            
            try:
                # =============================================================
                # NEW ARCHITECTURE: Single step() call does everything!
                # =============================================================
                
                # Update environmental models
                earth.update(timestep)
                
                # Update wind vector
                wind_vector_enu = np.array([0.0, 0.0, 0.0])
                if wind is not None:
                    altitude_above_ground = rocket.state.r_enu[2]
                    wind_vector_enu = wind.get_wind_vector(altitude_above_ground)
                    wind.update(timestep)
                
                # Set wind on rocket
                rocket.set_wind(wind_vector_enu)
                
                # Single step call handles:
                # - Environment updates
                # - Atmosphere updates
                # - Aerodynamics updates
                # - Engine updates
                # - Force/torque calculations
                # - Numerical integration (RK4)
                # - History tracking
                rocket.step(timestep)
                
                # Update time
                t = rocket.state.time
                
                # ===== PARACHUTE HANDLING =====
                if parachute is not None:
                    current_altitude = rocket.state.r_enu[2]
                    vertical_velocity = abs(rocket.state.v_enu[2])
                    
                    # Apogee-triggered drogue
                    is_descending = current_altitude < prev_altitude
                    if (is_descending and parachute.drogue_enabled
                            and not parachute.drogue_deployed):
                        parachute.drogue_deployed = True
                        parachute.drogue_deployment_time = t
                        parachute.drogue_deployment_altitude_actual = current_altitude
                        logger.info(
                            "Drogue deployed at apogee: altitude=%.1fm, t=%.2fs",
                            current_altitude, t,
                        )
                    
                    # Altitude-based deployment checks
                    if parachute.check_deployment(current_altitude, vertical_velocity, t):
                        logger.info(
                            "Main parachute deployed: altitude=%.1fm, velocity=%.1fm/s",
                            current_altitude, vertical_velocity,
                        )
                    
                    # Advance inflation counter
                    parachute.update_inflation(timestep)
                    
                    # Apply parachute drag force
                    if parachute.deployed:
                        v_rel = rocket.state.v_enu  # Simplified: using ground-relative velocity
                        speed_rel = float(np.linalg.norm(v_rel))
                        if speed_rel > 0:
                            drag_force = parachute.calculate_drag_force(
                                speed_rel, atmosphere.give_dens(current_altitude)
                            )
                            # Apply force opposite to velocity direction
                            # In new architecture, this would need to be integrated into dynamics
                            # For now, we'll log it but not apply it
                            logger.info(f"Parachute drag: {drag_force:.1f}N at {current_altitude:.1f}m")
                            parachute.max_descent_rate = max(
                                parachute.max_descent_rate, vertical_velocity
                            )
                
                # Update metrics
                current_altitude = rocket.state.r_enu[2]
                current_velocity = float(np.linalg.norm(rocket.state.v_enu))
                current_range = float(np.linalg.norm(rocket.state.r_enu[:2]))
                
                # Calculate Mach number
                mach = current_velocity / atmosphere.give_v_sonic(current_altitude) if current_velocity > 0 else 0.0
                
                # Calculate acceleration in g's
                # In new architecture, we'd need to access this from dynamics
                # For now, use a simplified calculation
                accel_magnitude = 0.0  # Would need to be tracked
                
                metrics['max_altitude'] = max(metrics['max_altitude'], current_altitude)
                metrics['max_velocity'] = max(metrics['max_velocity'], current_velocity)
                metrics['max_mach'] = max(metrics['max_mach'], mach)
                metrics['max_range'] = max(metrics['max_range'], current_range)
                metrics['max_accel_g'] = max(metrics['max_accel_g'], accel_magnitude / 9.80665)
                
                # Detect apogee
                if current_altitude < prev_altitude and not apogee_reached:
                    metrics['apogee_time'] = t
                    apogee_reached = True
                
                # Store trajectory point
                if i % max(1, int(0.1 / timestep)) == 0:
                    trajectory.append({
                        'time': t,
                        'altitude': current_altitude,
                        'velocity': current_velocity,
                        'range': current_range,
                        'mach': mach,
                    })
                
                prev_altitude = current_altitude
                
                # Emit progress
                progress_value = (i + 1) / num_steps
                self.progress.emit(progress_value)
                
                # Check termination conditions
                if current_altitude <= 0 and t > 1.0:
                    termination_reason = "LANDING: Altitude <= 0m"
                    termination_step = i
                    break
                
                if current_altitude > max_altitude:
                    termination_reason = "MAX_ALTITUDE: Exceeded 200km"
                    termination_step = i
                    break
                
                if current_range > max_range:
                    termination_reason = "MAX_RANGE: Exceeded 500km"
                    termination_step = i
                    break
                
                if np.any(np.isnan([current_altitude, current_velocity])):
                    termination_reason = "NAN_DETECTED: Numerical instability"
                    termination_step = i
                    raise RuntimeError(f"Numerical instability at t={t:.2f}s")
                
            except Exception as step_error:
                logger.error(f"Error in simulation step at t={t:.3f}s: {step_error}")
                raise
        
        # Final metrics
        metrics['flight_duration'] = t
        metrics['propulsion'] = {
            'thrust_source': 'analytical',  # Would need to get from engine
            'propellant_consumed': 0.0,  # Would need to get from engine
            'remaining_propellant': 0.0,  # Would need to get from engine
            'total_impulse_delivered': 0.0,  # Would need to get from engine
            'burnout_reached': False,  # Would need to get from engine
            'configured_propellant_mass': rocket_config['engine'].get('propellant_mass', 0.0),
            'configured_burn_time': rocket_config['engine'].get('burn_time', 0.0),
        }
        
        # Runtime diagnostics
        runtime_diagnostics = {
            'requested_runtime_s': runtime,
            'actual_runtime_s': t,
            'requested_steps': num_steps,
            'actual_steps': i + 1,
            'timestep_s': timestep,
            'completion_percentage': f"{((i+1)/num_steps)*100:.1f}%",
            'termination_reason': termination_reason or "NORMAL: Completed all steps",
            'termination_step': termination_step or i,
        }
        metrics['runtime_diagnostics'] = runtime_diagnostics
        
        # Parachute metrics
        if parachute is not None:
            parachute_metrics = parachute.finalize()
            metrics.update(parachute_metrics)
        
        # Get history from rocket simulation
        try:
            history_data = {
                'time': rocket.simulation.get_history_array('times'),
                'positions': rocket.simulation.get_history_array('positions'),
                'velocities': rocket.simulation.get_history_array('velocities'),
                'masses': rocket.simulation.get_history_array('masses'),
            }
            # Convert to lists for JSON serialization
            history_data = {k: v.tolist() if isinstance(v, np.ndarray) else v 
                          for k, v in history_data.items()}
        except Exception as history_error:
            logger.warning(f"Could not get history: {history_error}")
            history_data = {}
        
        # Prepare results
        results = {
            'status': 'success',
            'trajectory': trajectory,
            'history': history_data,
            'metrics': metrics,
            'total_steps': i + 1,
            'simulation_time': t,
            'rocket': rocket_name,
            'location': location_name,
        }
        
        if parachute is not None:
            results['parachute_info'] = parachute.get_deployment_info()
        
        # Post-simulation validation
        try:
            validator = SimulationValidator()
            validation_report = validator.validate(results)
            results['validation'] = validation_report
        except Exception as validation_error:
            logger.warning(f"Could not validate: {validation_error}")
            results['validation'] = {'valid': None, 'error': str(validation_error)}
        
        return results


# For backward compatibility, alias as SimulationWorker
SimulationWorker = SimulationWorkerV2


__all__ = ['SimulationWorkerV2', 'SimulationWorker']
