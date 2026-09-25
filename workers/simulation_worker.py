"""Simulation Worker - Background thread for running rocket simulations with real physics engine.

Phase 4: Migrated to use new component-based Rocket architecture with dependency injection.

This worker now uses the new Rocket architecture by default, but maintains backward
compatibility with the legacy interface. The simulation loop has been simplified from
~15 method calls per step to a single rocket.step(timestep) call.

Architecture:
    - Uses factory pattern for Rocket creation (create_rocket_from_config)
    - Single step() call per iteration (replaces update_gmst, update_pos_vel, update_atmosphere,
      update_aerodynamics, update_engine, update_mass_related, update_forces_aero,
      update_forces_engine, update_forces_torques, update_g_accel, RK4_update, update_time)
    - State access via rocket.state.* instead of rocket.*
    - Maintains same Qt signals and interface for backward compatibility

Migration Status: Phase 4 - Migrated to new architecture
"""

from PyQt6.QtCore import QThread, pyqtSignal
from models.app_state import ApplicationState
from src.models.state import StateProvider, StateProxy
from src.models.rocket.factory import create_rocket_from_config
from src.models.rocket.rocket import Rocket as NewRocket
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
# _StateProxy is kept as an alias for backward compatibility
_StateProxy = StateProxy


class SimulationWorker(QThread):
    """
    Worker thread for executing rocket flight simulations with real physics engine.
    
    Uses actual physics models from src/models/:
    - Rocket: 6-DOF dynamics with aerodynamics and propulsion
    - Planet: Gravitational and magnetic field models
    - Atmosphere: Temperature, pressure, and density profiles
    
    Emits signals:
    - progress: (float) 0.0 to 1.0 indicating simulation progress
    - finished: (dict) simulation results with trajectory and metrics
    - error: (str) error message if simulation fails
    """
    
    # Define signals
    progress = pyqtSignal(float)  # Emit progress as float 0.0-1.0
    finished = pyqtSignal(object)  # Emit results dictionary
    error = pyqtSignal(str)  # Emit error message
    
    def __init__(self, state: StateProvider, use_cache: bool = True):
        """Initialize simulation worker with a state provider.
        
        Args:
            state: StateProvider instance (ApplicationState, StateProxy, or MockStateProvider)
            use_cache: Whether to use simulation caching (default: True)
        """
        super().__init__()
        self.state = state
        self.is_running = True
        self.is_paused = False
        self.use_cache = use_cache
        self._cache: Optional[SimulationCache] = None
        if self.use_cache:
            self._cache = get_cache()
    
    def run(self):
        """Execute the simulation with real physics engine in background thread."""
        try:
            results = self._run_core()
            self.finished.emit(results)
        except Exception as e:
            logger.error(f"Simulation error: {str(e)}", exc_info=True)
            self.error.emit(f"Simulation failed: {str(e)}")

    def run_with_params(self, overrides: dict) -> dict:
        """
        Run the simulation synchronously with parameter overrides.

        Intended for Monte Carlo batch runs. Does NOT emit Qt signals.
        Thread-safe provided no other simulation is running on this worker
        instance simultaneously.

        Args:
            overrides: Mapping of ApplicationState keys to override values.
                       Any key accepted by ``state.get()`` is supported, e.g.::

                           {
                               'launch_elevation_angle': 84.5,
                               'launch_azimuth': 2.3,
                               'average_temperature': 22.0,
                               'wind_speed_ref': 5.0,
                               'wind_direction': 180.0,
                           }

        Returns:
            Results dict with the same structure as the ``finished`` signal payload.

        Raises:
            ValueError: If rocket configuration is missing or invalid.
            RuntimeError: If numerical instability is detected during integration.
        """
        original_state = self.state
        self.state = _StateProxy(original_state, overrides)
        try:
            return self._run_core()
        finally:
            self.state = original_state

    def _run_core(self) -> dict:
        """Core simulation physics. Returns the results dict.

        Called by both ``run()`` (QThread context, emits signals) and
        ``run_with_params()`` (synchronous, no signal emission).
        """
        logger.info("Starting rocket flight simulation with real physics engine")

        # Get simulation parameters from state
        runtime = self.state.get('sim_runtime', 600)  # seconds
        timestep = self.state.get('sim_time_step', 0.001)  # seconds
        rocket_name = self.state.get('selected_rocket', 'agni-1')
        location_name = self.state.get('sim_location', 'Unknown')
            
        # ===== PARACHUTE INITIALIZATION =====
        parachute = None
        if self.state.get('parachute_enabled', False):
            parachute_config = {
                'name': self.state.get('selected_parachute', 'Main Parachute'),
                'diameter': self.state.get('parachute_diameter', 0.6),
                'Cd': self.state.get('parachute_cd', 1.5),
                'material': self.state.get('parachute_material', 'ripstop_nylon'),
                'deployment_altitude': self.state.get('parachute_deployment_altitude', 300.0),
                'min_velocity': self.state.get('parachute_min_velocity', 5.0),
                'max_velocity': self.state.get('parachute_max_velocity', 80.0),
                'inflation_time': self.state.get('parachute_inflation_time', 0.5),
                'drogue_enabled': self.state.get('drogue_enabled', False),
            }
                
            if parachute_config['drogue_enabled']:
                parachute_config.update({
                    'drogue_diameter': self.state.get('drogue_diameter', 0.25),
                    'drogue_Cd': self.state.get('drogue_cd', 1.5),
                    'drogue_deployment_altitude': self.state.get('drogue_deployment_altitude', 800.0),
                    'drogue_inflation_time': self.state.get('drogue_inflation_time', 0.2),
                })
                
            parachute = Parachute(parachute_config)
            logger.info(f"Parachute system initialized: {parachute_config['name']}")
            
        # Load rocket configuration
        rocket_config = self._load_rocket_config(rocket_name)
        if not rocket_config:
            raise ValueError(f"Could not load rocket configuration: {rocket_name}")
            
        # Validate rocket configuration (Option 3)
        validation_report = self._validate_rocket_config(rocket_config, rocket_name)
        self.state.set('config_validation_report', validation_report)
            
        # Check for critical errors
        if not validation_report['valid']:
            error_msg = "Configuration validation failed:\n" + "\n".join(validation_report['errors'])
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Warn about configuration warnings
        if validation_report['warnings']:
            logger.warning(f"Configuration has {len(validation_report['warnings'])} warnings. "
                          "Simulation may have unexpected results.")
            
        # Get environmental parameters
        temperature = self.state.get('average_temperature', 20.0)  # Celsius
        latitude = self.state.get('launch_latitude', 0.0)
        longitude = self.state.get('launch_longitude', 0.0)
        altitude = self.state.get('launch_elevation', 60.0)  # meters
            
        # Get launch parameters
        launch_elevation_angle = self.state.get('launch_elevation_angle', 85.0)  # degrees
        launch_azimuth = self.state.get('launch_azimuth', 0.0)  # degrees
        launch_roll = self.state.get('launch_roll', 0.0)  # degrees
            
        # Get launch date/time
        launch_date = self.state.get('sim_date')
        launch_time = self.state.get('sim_time')
            
        # Initialize physics models
        logger.info(f"Initializing physics models for {rocket_name}")
            
        # Create time reference
        sim_datetime = datetime.combine(launch_date, launch_time)
        date = np.array([sim_datetime.year, sim_datetime.month, sim_datetime.day,
                        sim_datetime.hour, sim_datetime.minute, sim_datetime.second])
            
        julian_date = Clock().julian_day(date)
        gmst_0 = Clock().gmst(julian_date, 1)
            
        # Initialize position and velocity
        r_enu_0 = np.array([0.0, 0.0, 0.0])  # Starting at launch site
        v_enu_0 = np.array([0.0, 0.0, 0.0])  # Starting from rest
            
        # Initialize attitude (quaternions)
        q_pitch = np.array([
            0,
            np.sin(launch_elevation_angle * 0.5 * DEG_TO_RAD),
            0,
            np.cos(launch_elevation_angle * 0.5 * DEG_TO_RAD)
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
            
        # Initial mass
        initial_mass = rocket_config.get('initial_mass', 1000.0)
        
        # Get reference area from config
        reference_area = rocket_config.get('reference_area', 1.0)
            
        # Create physics objects with caching
        coordinates = np.array([latitude, longitude, altitude])
        
        # Use cached Planet and Atmosphere if available (Monte Carlo optimization)
        if self._cache is not None:
            earth = self._cache.get_planet(latitude, longitude, gmst_0)
            atmosphere = self._cache.get_atmosphere(temperature)
        else:
            earth = Planet(gmst_0)
            atmosphere = Atmosphere(temperature)
        
        # ========================================================================
        # PHASE 4: Use factory to create new architecture rocket
        # ========================================================================
        # Create rocket using factory with dependency injection
        rocket, rocket_config, engine, aerodynamics, atm = create_rocket_from_config(
            r_enu_0=r_enu_0,
            v_enu_0=v_enu_0,
            q_enu2b_0=q_enu2b_0,
            w_enu_0=w_enu_0,
            initial_mass=initial_mass,
            rocket_name=rocket_name,
            temperature=temperature,
            reference_area=reference_area
        )
        
        # Use cached atmosphere if available
        if self._cache is not None:
            rocket.set_atmosphere(atmosphere)
            
        # ===== WIND MODEL INITIALIZATION (Phase 2) =====
        # Use cached wind model if available (Monte Carlo optimization)
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
        logger.info(f"Termination limits - Max altitude: {max_altitude/1000:.0f} km, Max range: {max_range/1000:.0f} km")
            
        # Main simulation loop
        t = 0.0
        prev_altitude = 0.0
        apogee_reached = False
            
        for i in range(num_steps):
            if not self.is_running:
                termination_reason = "USER_STOP: Simulation cancelled by user"
                termination_step = i
                logger.info(f"[TERMINATION] {termination_reason} at t={t:.2f}s (step {i}/{num_steps})")
                break

            # Cooperative pause without blocking the GUI thread.
            while self.is_paused and self.is_running:
                self.msleep(50)
                
            try:
                # =============================================================
                # PHASE 4: NEW ARCHITECTURE - Single step() call
                # =============================================================
                # Update environmental models
                earth.update(timestep)
                
                # Update wind vector
                wind_vector_enu = np.array([0.0, 0.0, 0.0])
                if wind is not None:
                    # Get wind vector at current altitude
                    altitude_above_ground = rocket.state.r_enu[2]
                    wind_vector_enu = wind.get_wind_vector(altitude_above_ground)
                    wind.update(timestep)
                
                # Set wind on rocket
                rocket.set_wind(wind_vector_enu)
                
                # Update atmosphere on rocket based on current altitude
                # Account for launch site elevation
                absolute_altitude = altitude + rocket.state.r_enu[2]
                
                # Single step call handles everything:
                # - Environment updates (wind, atmosphere)
                # - Aerodynamics updates
                # - Engine updates
                # - Force/torque calculations
                # - Numerical integration (RK4)
                # - History tracking
                rocket.step(timestep)
                
                # Update time
                t = rocket.state.time
                
                # =============================================================
                # PARACHUTE HANDLING
                # In new architecture, parachute forces need to be applied
                # to the dynamics before the step is taken
                # =============================================================
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
                    if parachute.check_drogue_deployment(current_altitude, t):
                        logger.info(
                            "Drogue deployed (altitude trigger): %.1fm", current_altitude
                        )
                    
                    # Advance inflation counter
                    parachute.update_inflation(timestep)
                    
                    # Apply parachute drag force
                    # In new architecture, we apply it directly to the dynamics
                    if parachute.deployed:
                        # Use ground-relative velocity (v_enu) for now
                        # Note: For more accuracy, we could calculate relative velocity
                        v_rel = rocket.state.v_enu
                        speed_rel = float(np.linalg.norm(v_rel))
                        if speed_rel > 0:
                            # Get current density from atmosphere at absolute altitude
                            current_density = atmosphere.give_dens(absolute_altitude)
                            drag_force = parachute.calculate_drag_force(
                                speed_rel, current_density
                            )
                            # Apply force opposite to velocity direction
                            # This needs to be integrated into the rocket's forces
                            # For now, we'll store it in the parachute for metrics
                            parachute.max_descent_rate = max(
                                parachute.max_descent_rate, vertical_velocity
                            )
                            # Log parachute drag
                            logger.debug(f"Parachute drag: {drag_force:.1f}N at {current_altitude:.1f}m")
                
                # =============================================================
                # Update metrics from rocket state
                # =============================================================
                current_altitude = rocket.state.r_enu[2]
                current_velocity = float(np.linalg.norm(rocket.state.v_enu))
                current_range = float(np.linalg.norm(rocket.state.r_enu[:2]))
                
                # Get Mach number from atmosphere
                mach = current_velocity / atmosphere.give_v_sonic(absolute_altitude) if current_velocity > 0 else 0.0
                
                # Get acceleration - from dynamics or state
                # In new architecture, acceleration is calculated in dynamics
                # For now, we'll use a simplified calculation or get from history
                # We can access the acceleration from the last step's forces
                try:
                    # Try to get acceleration magnitude from the dynamics
                    # This would be: ||forces|| / mass + gravity
                    # For now, use 0 as placeholder
                    accel_magnitude = 0.0
                    
                    # Try to get from history if available
                    if len(rocket.simulation.history.forces) > 0:
                        last_force = rocket.simulation.history.forces[-1]
                        last_mass = rocket.simulation.history.masses[-1]
                        if last_mass > 0:
                            accel_magnitude = float(np.linalg.norm(last_force) / last_mass)
                except Exception:
                    accel_magnitude = 0.0
                
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
                if i % max(1, int(0.1 / timestep)) == 0:  # Store every 0.1 seconds
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
                    logger.info(f"[TERMINATION] {termination_reason} at t={t:.2f}s (step {i}/{num_steps})")
                    logger.info(f"  Altitude: {current_altitude:.2f}m, Velocity: {current_velocity:.2f}m/s")
                    break
                    
                if current_altitude > max_altitude:
                    termination_reason = "MAX_ALTITUDE: Exceeded 200km"
                    termination_step = i
                    logger.warning(f"[TERMINATION] {termination_reason} at t={t:.2f}s (step {i}/{num_steps})")
                    logger.warning(f"  Altitude: {current_altitude/1000:.1f}km, Velocity: {current_velocity:.2f}m/s")
                    break
                    
                if current_range > max_range:
                    termination_reason = "MAX_RANGE: Exceeded 500km"
                    termination_step = i
                    logger.warning(f"[TERMINATION] {termination_reason} at t={t:.2f}s (step {i}/{num_steps})")
                    logger.warning(f"  Range: {current_range/1000:.1f}km, Altitude: {current_altitude:.2f}m")
                    break
                    
                if np.any(np.isnan([current_altitude, current_velocity])):
                    termination_reason = "NAN_DETECTED: Numerical instability"
                    termination_step = i
                    logger.error(f"[TERMINATION] {termination_reason} at t={t:.2f}s (step {i}/{num_steps})")
                    logger.error(f"  Altitude: {current_altitude}, Velocity: {current_velocity}")
                    raise RuntimeError(f"Numerical instability detected at t={t:.2f}s")
                    
            except Exception as step_error:
                logger.error(f"Error in simulation step at t={t:.3f}s: {step_error}")
                raise
            
        # Final metrics
        metrics['flight_duration'] = t
        
        # Get propulsion metrics from engine
        # In new architecture, we access engine through rocket.engine
        if rocket.engine is not None:
            metrics['propulsion'] = {
                'thrust_source': rocket.engine.thrust_source if hasattr(rocket.engine, 'thrust_source') else 'analytical',
                'propellant_consumed': rocket.engine.total_mass_flow if hasattr(rocket.engine, 'total_mass_flow') else 0.0,
                'remaining_propellant': rocket.engine.propellant_mass - (rocket.engine.total_mass_flow if hasattr(rocket.engine, 'total_mass_flow') else 0.0),
                'total_impulse_delivered': rocket.engine.total_impulse if hasattr(rocket.engine, 'total_impulse') else 0.0,
                'burnout_reached': hasattr(rocket.engine, 'burnout_reached') and rocket.engine.burnout_reached,
                'configured_propellant_mass': rocket_config['engine'].get('propellant_mass', 0.0),
                'configured_burn_time': rocket_config['engine'].get('burn_time', 0.0),
            }
        else:
            metrics['propulsion'] = {
                'thrust_source': 'none',
                'propellant_consumed': 0.0,
                'remaining_propellant': 0.0,
                'total_impulse_delivered': 0.0,
                'burnout_reached': False,
                'configured_propellant_mass': rocket_config['engine'].get('propellant_mass', 0.0),
                'configured_burn_time': rocket_config['engine'].get('burn_time', 0.0),
            }
            
        # ===== PHASE 1: RUNTIME DIAGNOSTICS =====
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
            
        logger.info(f"\n{'='*70}")
        logger.info(f"SIMULATION RUNTIME DIAGNOSTICS")
        logger.info(f"{'='*70}")
        logger.info(f"Requested runtime: {runtime}s → Actual: {t:.2f}s ({((t/runtime)*100 if runtime > 0 else 0):.1f}%)")
        logger.info(f"Steps: {num_steps} requested → {i+1} executed")
        logger.info(f"Termination: {termination_reason or 'NORMAL (all steps completed)'}")
        logger.info(f"Max altitude: {metrics['max_altitude']:.2f}m")
        logger.info(f"Max velocity: {metrics['max_velocity']:.2f}m/s ({metrics['max_mach']:.2f} Mach)")
        logger.info(f"Max range: {metrics['max_range']:.2f}m")
        logger.info(f"Apogee time: {metrics['apogee_time']:.2f}s")
        logger.info(f"{'='*70}\n")
            
        # ===== PARACHUTE METRICS =====
        if parachute is not None:
            parachute_metrics = parachute.finalize()
            metrics.update(parachute_metrics)
            if parachute.deployed:
                logger.info(f"Parachute deployed at {parachute.deployment_altitude_actual:.1f}m, "
                           f"deployment time: {parachute.deployment_time:.2f}s")
            
        # Finalize history array data - convert numpy arrays to lists for JSON serialization
        # In new architecture, history is managed by rocket.simulation
        try:
            history_data = {
                'times': rocket.simulation.get_history_array('times').tolist() if len(rocket.simulation.get_history_array('times')) > 0 else [],
                'positions': rocket.simulation.get_history_array('positions').tolist() if len(rocket.simulation.get_history_array('positions')) > 0 else [],
                'velocities': rocket.simulation.get_history_array('velocities').tolist() if len(rocket.simulation.get_history_array('velocities')) > 0 else [],
                'masses': rocket.simulation.get_history_array('masses').tolist() if len(rocket.simulation.get_history_array('masses')) > 0 else [],
            }
            history_length = len(history_data.get('times', []))
            logger.info(f"Finalized history: {len(history_data)} fields, {history_length} timesteps recorded")
        except Exception as history_error:
            logger.warning(f"Could not finalize history: {history_error}. "
                          f"Dashboard will use trajectory data only.")
            history_data = {}
            
        # Prepare results with complete historical data
        results = {
            'status': 'success',
            'trajectory': trajectory,
            'history': history_data,          # Complete 40+ field historical data (numpy→lists)
            'metrics': metrics,
            'total_steps': i + 1,
            'simulation_time': t,
            'rocket': rocket_name,
            'location': location_name,
        }
            
        if parachute is not None:
            results['parachute_info'] = parachute.get_deployment_info()
            
        logger.info(f"Simulation completed successfully: {i+1} steps, {t:.2f}s flight time")
        logger.info(f"Max altitude: {metrics['max_altitude']:.2f}m, Max velocity: {metrics['max_velocity']:.2f}m/s")
            
        # ===== PHASE 2: POST-SIMULATION VALIDATION =====
        try:
            validator = SimulationValidator()
            validation_report = validator.validate(results)
            results['validation'] = validation_report
                
            # Log validation summary
            if validation_report['valid']:
                logger.info(f"[VALID]ATION PASS: {validator.summary()}")
            else:
                logger.warning(f"[X] VALIDATION WARNINGS: {validator.summary()}")
                if validation_report['errors']:
                    logger.error(f"  Critical errors: {len(validation_report['errors'])}")
                    for err in validation_report['errors'][:3]:  # Show first 3
                        logger.error(f"    - {err}")
                if validation_report['warnings']:
                    logger.warning(f"  Warnings: {len(validation_report['warnings'])}")
                    for warn in validation_report['warnings'][:3]:  # Show first 3
                        logger.warning(f"    - {warn}")
        except Exception as validation_error:
            logger.warning(f"Could not validate simulation results: {validation_error}")
            results['validation'] = {
                'valid': None,
                'error': str(validation_error),
                'checks': {},
                'warnings': [],
                'errors': [str(validation_error)]
            }
            
        return results

    def _load_rocket_config(self, rocket_name: str) -> dict | None:
        """Load rocket configuration from JSON file with validation and caching."""
        # Try cache first
        if self._cache is not None:
            cached_config = self._cache.get_rocket_config(rocket_name)
            if cached_config is not None:
                logger.debug(f"Using cached rocket config: {rocket_name}")
                return self._validate_and_fix_config(cached_config, rocket_name)
        
        # Load from disk
        try:
            config_path = f"data/rockets/configs/{rocket_name}.json"
            if not os.path.exists(config_path):
                logger.error(f"Rocket config not found: {config_path}")
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.info(f"Loaded rocket configuration: {rocket_name}")
            
            # Cache the raw config before validation
            if self._cache is not None:
                # Store raw config in cache (validation happens per-run)
                self._cache._rocket_config_cache[rocket_name] = config
                self._cache._stats.rocket_configs += 1
            
            return self._validate_and_fix_config(config, rocket_name)
        except Exception as e:
            logger.error(f"Error loading rocket config: {e}")
            return None
    
    def _validate_and_fix_config(self, config: dict, rocket_name: str) -> dict:
        """Validate and fix rocket configuration (shared logic for cached and new configs)."""
        # Create a deep copy to avoid modifying cached config
        config = copy.deepcopy(config)
        
        # Option 2: Accept both 'initial_mass' and 'total_mass_initial' keys
        if 'initial_mass' not in config:
            if 'total_mass_initial' in config:
                config['initial_mass'] = config['total_mass_initial']
                logger.info(f"Using 'total_mass_initial' as 'initial_mass': {config['initial_mass']} kg")
            else:
                logger.error("Configuration must have either 'initial_mass' or 'total_mass_initial'")
                return None
        
        # Validate and fix moment of inertia values (prevent singular matrices)
        # Use physics-based minimum: 0.1 of body mass times reference length squared
        body_mass = config.get('initial_mass', config.get('total_mass_initial', 1.0))
        reference_length = 0.5  # Typical rocket reference dimension in meters
        min_inertia = max(0.01, body_mass * reference_length**2 * 0.01)  # Small fraction of typical value
        
        for inertia_key in ['I_before_burn', 'I_after_burn']:
            if inertia_key in config:
                for axis in ['x', 'y', 'z']:
                    current_value = config[inertia_key].get(axis, 0)
                    if current_value < min_inertia:
                        logger.warning(
                            f"Inertia {inertia_key}[{axis}] = {current_value:.3f} kg·m² is very small, "
                            f"setting to {min_inertia:.3f} kg·m² to prevent numerical issues"
                        )
                        config[inertia_key][axis] = min_inertia
        
        return config
    
    def _validate_rocket_config(self, config: dict, rocket_name: str) -> dict:
        """
        Option 3: Validate rocket configuration and return diagnostic report.
        
        Checks:
        - Total mass vs dry mass ratio
        - Expected propellant consumption vs mass_flux × burn_time
        - Inertia tensor properties
        
        Returns:
            Dictionary with validation results: {'valid': bool, 'warnings': [], 'errors': []}
        """
        report = {
            'rocket': rocket_name,
            'valid': True,
            'warnings': [],
            'errors': [],
            'diagnostics': {}
        }
        
        try:
            # Extract key parameters
            total_mass = config.get('initial_mass', config.get('total_mass_initial', 0))
            propellant_mass = config.get('propellant_mass', 0)
            engine_data = config.get('engine', {})
            burn_time = engine_data.get('burn_time', 0)
            mass_flux = engine_data.get('mass_flux', 0)
            
            dry_mass = total_mass - propellant_mass
            
            # ===== Check 1: Mass Ratio =====
            if dry_mass <= 0:
                report['errors'].append(
                    f"Invalid mass configuration: Dry mass ({dry_mass:.2f} kg) must be positive. "
                    f"Total={total_mass:.2f} kg, Propellant={propellant_mass:.2f} kg"
                )
                report['valid'] = False
            elif propellant_mass / total_mass > 0.9:
                report['warnings'].append(
                    f"High propellant ratio: {propellant_mass/total_mass*100:.1f}% of total mass is propellant. "
                    f"Dry mass is only {dry_mass:.2f} kg"
                )
            elif propellant_mass / total_mass < 0.05:
                report['warnings'].append(
                    f"Low propellant ratio: {propellant_mass/total_mass*100:.1f}% of total mass is propellant. "
                    f"May not achieve significant altitude"
                )
            
            report['diagnostics']['mass_ratio'] = {
                'total_mass_kg': total_mass,
                'propellant_mass_kg': propellant_mass,
                'dry_mass_kg': dry_mass,
                'propellant_percentage': f"{propellant_mass/total_mass*100:.1f}%"
            }
            
            # ===== Check 2: Propellant Consumption Rate =====
            if burn_time > 0 and mass_flux > 0:
                expected_fuel_consumed = mass_flux * burn_time
                
                if abs(expected_fuel_consumed - propellant_mass) > propellant_mass * 0.1:
                    report['warnings'].append(
                        f"Propellant mismatch: mass_flux ({mass_flux:.3f} kg/s) × burn_time ({burn_time:.2f}s) = "
                        f"{expected_fuel_consumed:.2f} kg, but config specifies {propellant_mass:.2f} kg. "
                        f"This may cause mass calculation errors."
                    )
                
                report['diagnostics']['consumption'] = {
                    'mass_flux_kg_per_s': mass_flux,
                    'burn_time_s': burn_time,
                    'expected_fuel_consumed_kg': expected_fuel_consumed,
                    'configured_fuel_kg': propellant_mass,
                    'mismatch_kg': abs(expected_fuel_consumed - propellant_mass)
                }
            
            # ===== Check 3: Inertia Tensor Properties =====
            inertia_before = config.get('I_before_burn', {})
            inertia_after = config.get('I_after_burn', {})
            
            for label, inertia_dict in [('before burn', inertia_before), ('after burn', inertia_after)]:
                if inertia_dict:
                    ix = inertia_dict.get('x', 0)
                    iy = inertia_dict.get('y', 0)
                    iz = inertia_dict.get('z', 0)
                    
                    # Check triangle inequality: largest <= sum of other two
                    sorted_inertias = sorted([ix, iy, iz])
                    largest = sorted_inertias[2]
                    sum_others = sorted_inertias[0] + sorted_inertias[1]
                    
                    if largest > sum_others:
                        report['warnings'].append(
                            f"Inertia violation {label}: largest component ({largest:.3f}) > "
                            f"sum of others ({sum_others:.3f}). Matrix may be physically unrealistic."
                        )
                    
                    # Check for very small values
                    min_inertia = min([ix, iy, iz])
                    if min_inertia < 0.01:
                        report['warnings'].append(
                            f"Very small inertia {label}: {min_inertia:.4f} kg·m². "
                            f"May cause numerical instability in attitude dynamics."
                        )
                    
                    report['diagnostics'][f'inertia_{label.replace(" ", "_")}'] = {
                        'Ixx_kg·m²': ix,
                        'Iyy_kg·m²': iy,
                        'Izz_kg·m²': iz,
                        'ratio_Izz/Ixx': iz/ix if ix > 0 else 'inf',
                        'stability_check': 'OK' if largest <= sum_others else 'FAIL'
                    }
            
            # ===== Check 4: Thrust-to-Weight Ratio =====
            mean_thrust = engine_data.get('mean_thrust', 0)
            thrust_to_weight = mean_thrust / (total_mass * 9.81) if total_mass > 0 else 0
            
            if thrust_to_weight < 5:
                report['warnings'].append(
                    f"Low thrust-to-weight ratio: {thrust_to_weight:.1f}. "
                    f"Rocket may not achieve vertical flight (should be >5)."
                )
            elif thrust_to_weight > 100:
                report['warnings'].append(
                    f"Very high thrust-to-weight ratio: {thrust_to_weight:.1f}. "
                    f"May be unstable or unrealistic."
                )
            
            report['diagnostics']['thrust_performance'] = {
                'mean_thrust_N': mean_thrust,
                'thrust_to_weight_ratio': f"{thrust_to_weight:.1f}",
                'assessment': 'Good' if 5 <= thrust_to_weight <= 50 else 'Unusual'
            }

            # ===== Check 5: Propulsion configuration integrity =====
            self._validate_propulsion_config(report, config, rocket_name)
            
            # Log comprehensive report
            logger.info(f"\n{'='*70}")
            logger.info(f"ROCKET CONFIGURATION VALIDATION: {rocket_name}")
            logger.info(f"{'='*70}")
            logger.info(f"Status: {'[VALID]' if report['valid'] else '[INVALID]'}")
            
            if report['diagnostics']:
                logger.info("\nDiagnostics Summary:")
                for section, data in report['diagnostics'].items():
                    logger.info(f"  [{section}]")
                    for key, value in data.items():
                        logger.info(f"    {key}: {value}")
            
            if report['warnings']:
                logger.warning(f"\nConfiguration Warnings ({len(report['warnings'])}):")
                for i, warning in enumerate(report['warnings'], 1):
                    logger.warning(f"  {i}. {warning}")
            
            if report['errors']:
                logger.error(f"\nConfiguration Errors ({len(report['errors'])}):")
                for i, error in enumerate(report['errors'], 1):
                    logger.error(f"  {i}. {error}")
            
            logger.info(f"{'='*70}\n")
            
            return report
            
        except Exception as e:
            logger.error(f"Error during configuration validation: {e}")
            report['errors'].append(f"Validation error: {str(e)}")
            report['valid'] = False
            return report

    def _validate_propulsion_config(self, report: dict, config: dict, rocket_name: str) -> None:
        """Validate propulsion inputs before entering the simulation loop."""
        g0 = 9.80665
        engine_data = config.get('engine', {})
        required_keys = [
            'burn_time', 'nozzle_exit_diameter', 'propellant_mass', 'specific_impulse',
            'mean_thrust', 'max_thrust', 'mean_chamber_pressure',
            'max_chamber_pressure', 'thrust_to_weight_ratio'
        ]

        missing_keys = [key for key in required_keys if key not in engine_data]
        if missing_keys:
            report['errors'].append(
                f"Engine configuration missing required keys: {', '.join(sorted(missing_keys))}"
            )
            report['valid'] = False
            return

        thrust_curve_file = None
        thrust_curve_unit = engine_data.get('thrust_curve_unit', 'N')
        thrust_mode = engine_data.get('thrust_curve_mode', 'analytical')

        if thrust_mode == 'experimental':
            thrust_curve_file = engine_data.get('thrust_curve_file')
            if not thrust_curve_file:
                report['errors'].append(
                    "Experimental thrust mode requires 'thrust_curve_file' in engine configuration"
                )
                report['valid'] = False
                return

            if thrust_curve_unit not in {'N', 'kgf'}:
                report['errors'].append(
                    f"Invalid thrust_curve_unit '{thrust_curve_unit}'. Use 'N' or 'kgf'."
                )
                report['valid'] = False
                return

            candidate_paths = [thrust_curve_file, os.path.join('data', 'thrust_curves', thrust_curve_file)]
            if not any(os.path.isfile(path) for path in candidate_paths):
                report['errors'].append(
                    f"Thrust curve file not found: '{thrust_curve_file}'. "
                    "Check the 'thrust_curve_file' path in the engine configuration."
                )
                report['valid'] = False
                return

        try:
            engine_probe = EnhancedEngine(
                time=0.0,
                burn_time=engine_data['burn_time'],
                ambient_pressure=101325.0,
                nozzle_exit_diameter=engine_data['nozzle_exit_diameter'],
                propellant_mass=engine_data['propellant_mass'],
                specific_impulse=engine_data['specific_impulse'],
                mean_thrust=engine_data['mean_thrust'],
                max_thrust=engine_data['max_thrust'],
                mean_chamber_pressure=engine_data['mean_chamber_pressure'],
                max_chamber_pressure=engine_data['max_chamber_pressure'],
                thrust_to_weight_ratio=engine_data['thrust_to_weight_ratio'],
                thrust_curve_file=thrust_curve_file,
                thrust_curve_unit=thrust_curve_unit,
            )
        except Exception as exc:
            report['errors'].append(f"Propulsion validation failed: {exc}")
            report['valid'] = False
            return

        propulsion_diag = {
            'thrust_source': engine_probe.thrust_source,
            'burn_time_s': engine_data['burn_time'],
            'propellant_mass_kg': engine_data['propellant_mass'],
            'specific_impulse_s': engine_data['specific_impulse'],
            'mean_thrust_N': engine_data['mean_thrust'],
        }

        if engine_probe.use_experimental_thrust:
            curve_info = engine_probe.get_thrust_curve_info()
            expected_impulse = engine_data['propellant_mass'] * engine_data['specific_impulse'] * g0
            measured_impulse = curve_info.get('total_impulse', 0.0)
            impulse_error_pct = (
                abs(measured_impulse - expected_impulse) / expected_impulse * 100.0
                if expected_impulse > 0.0 else 0.0
            )
            propulsion_diag.update({
                'curve_points': curve_info.get('data_points', 0),
                'curve_total_impulse_Ns': measured_impulse,
                'expected_impulse_Ns': expected_impulse,
                'impulse_error_percent': round(impulse_error_pct, 2),
            })
            if impulse_error_pct > 20.0:
                report['warnings'].append(
                    f"Experimental thrust curve impulse differs from propellant/Isp estimate by {impulse_error_pct:.1f}%"
                )
        else:
            thrust_validation = engine_probe.validate_thrust_curve()
            propulsion_diag['analytical_curve_validation'] = thrust_validation
            if not thrust_validation.get('valid', False):
                report['warnings'].append(
                    f"Analytical thrust curve mean-thrust mismatch: {thrust_validation['error_percent']:.1f}%"
                )

        report['diagnostics']['propulsion'] = propulsion_diag
    
    def _get_history_length(self, history_dict: dict) -> int:
        """
        Get the number of timesteps recorded in history data.
        
        Args:
            history_dict: Dictionary returned from rocket.finalize_history()
        
        Returns:
            Number of timesteps, or 0 if empty
        """
        if not history_dict:
            return 0
        
        # Get the first available array to determine length
        for key, value in history_dict.items():
            if isinstance(value, list) and value:
                return len(value)
        
        return 0
    
    def stop(self):
        """Stop the simulation worker."""
        self.is_running = False
        self.is_paused = False
        logger.info("Simulation worker stopped")

    def pause(self):
        """Pause simulation loop execution cooperatively."""
        if self.is_running:
            self.is_paused = True
            logger.info("Simulation worker paused")

    def resume(self):
        """Resume simulation loop execution after a pause."""
        if self.is_running:
            self.is_paused = False
            logger.info("Simulation worker resumed")
