"""Simulation Worker - Background thread for running rocket simulations with real physics engine."""

from PyQt6.QtCore import QThread, pyqtSignal
from models.app_state import ApplicationState
from src.models.rocket import Rocket
from src.models.planet import Planet
from src.models.atmosphere import Atmosphere
from src.models.clock import Clock
from src.utils.mattools import MatTools as Mat
import logging
import json
import os
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

# Constants
DEG_TO_RAD = np.pi / 180.0


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
    
    def __init__(self, state: ApplicationState):
        super().__init__()
        self.state = state
        self.is_running = True
    
    def run(self):
        """Execute the simulation with real physics engine in background thread."""
        try:
            logger.info("Starting rocket flight simulation with real physics engine")
            
            # Get simulation parameters from state
            runtime = self.state.get('sim_runtime', 600)  # seconds
            timestep = self.state.get('sim_time_step', 0.001)  # seconds
            rocket_name = self.state.get('selected_rocket', 'agni-1')
            location_name = self.state.get('sim_location', 'Unknown')
            
            # Load rocket configuration
            rocket_config = self._load_rocket_config(rocket_name)
            if not rocket_config:
                raise ValueError(f"Could not load rocket configuration: {rocket_name}")
            
            # Get environmental parameters
            temperature = self.state.get('average_temperature', 20.0)  # Celsius
            latitude = self.state.get('launch_latitude', 0.0)
            longitude = self.state.get('launch_longitude', 0.0)
            altitude = self.state.get('launch_elevation', 60.0)  # meters
            
            # Get launch parameters
            launch_elevation_angle = self.state.get('launch_elevation', 85.0)  # degrees
            launch_azimuth = self.state.get('launch_azimuth', 0.0)  # degrees
            launch_roll = self.state.get('launch_roll', 0.0)  # degrees
            
            # Get launch date/time
            launch_date = self.state.get('sim_date')
            launch_time = self.state.get('sim_time')
            
            # Initialize physics models
            logger.info(f"Initializing physics models for {rocket_name}")
            
            # Create time reference
            sim_datetime = datetime.combine(launch_date, launch_time)
            date = [sim_datetime.year, sim_datetime.month, sim_datetime.day,
                   sim_datetime.hour, sim_datetime.minute, sim_datetime.second]
            
            julian_date = Clock().julian_day(date)
            gmst_0 = Clock().gmst(julian_date, 1)
            
            # Initialize position and velocity
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
            
            # Initial mass
            initial_mass = rocket_config.get('initial_mass', 1000.0)
            
            # Create physics objects
            coordinates = np.array([latitude, longitude, altitude])
            earth = Planet(gmst_0)
            atmosphere = Atmosphere(temperature)
            rocket = Rocket(r_enu_0, v_enu_0, q_enu2b_0, w_enu_0, initial_mass)
            
            # Simulation parameters
            num_steps = int(runtime / timestep)
            reference_area = rocket_config.get('reference_area', 1.0)
            
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
            
            logger.info(f"Starting simulation loop: {num_steps} steps, {timestep}s timestep")
            
            # Main simulation loop
            t = 0.0
            prev_altitude = 0.0
            apogee_reached = False
            
            for i in range(num_steps):
                if not self.is_running:
                    logger.info("Simulation stopped by user")
                    break
                
                try:
                    # Update environmental models
                    earth.update(timestep)
                    rocket.update_gmst(earth.gmst)
                    
                    # Update rocket mass and inertia
                    rocket.update_mass_related(
                        rocket_config['engine']['burn_time'],
                        rocket_config['CoM_before_burn']['x'],
                        rocket_config['CoM_before_burn']['y'],
                        rocket_config['CoM_before_burn']['z'],
                        rocket_config['I_before_burn']['x'],
                        rocket_config['I_before_burn']['y'],
                        rocket_config['I_before_burn']['z'],
                        rocket_config['CoM_after_burn']['x'],
                        rocket_config['CoM_after_burn']['y'],
                        rocket_config['CoM_after_burn']['z'],
                        rocket_config['I_after_burn']['x'],
                        rocket_config['I_after_burn']['y'],
                        rocket_config['I_after_burn']['z'],
                    )
                    
                    # Update position in Earth reference frame
                    rocket.update_pos_vel(coordinates)
                    
                    # Update atmospheric properties
                    current_altitude = rocket.r_enu[2]
                    rocket.update_atmosphere(
                        atmosphere.give_dens(current_altitude),
                        atmosphere.give_press(current_altitude),
                        atmosphere.give_v_sonic(current_altitude)
                    )
                    
                    # Update aerodynamics
                    rocket.update_aerodynamics(rocket_name)
                    rocket.update_forces_aero(reference_area=reference_area)
                    
                    # Update propulsion
                    rocket.update_engine(rocket_name)
                    rocket.update_forces_engine()
                    rocket.update_forces_torques()
                    
                    # Update gravitational acceleration
                    rocket.update_g_accel(coordinates)
                    
                    # Integrate dynamics using RK4
                    rocket.RK4_update(timestep)
                    rocket.save_data()
                    
                    # Update metrics
                    current_altitude = rocket.r_enu[2]
                    current_velocity = np.linalg.norm(rocket.v_enu)
                    current_range = np.linalg.norm(rocket.r_enu[:2])
                    
                    metrics['max_altitude'] = max(metrics['max_altitude'], current_altitude)
                    metrics['max_velocity'] = max(metrics['max_velocity'], current_velocity)
                    metrics['max_mach'] = max(metrics['max_mach'], rocket.mach)
                    metrics['max_range'] = max(metrics['max_range'], current_range)
                    
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
                            'mach': rocket.mach,
                        })
                    
                    prev_altitude = current_altitude
                    
                    # Emit progress
                    progress_value = (i + 1) / num_steps
                    self.progress.emit(progress_value)
                    
                    # Check termination conditions
                    if current_altitude <= 0 and t > 1.0:
                        logger.info(f"Simulation terminated: rocket hit ground at t={t:.2f}s")
                        break
                    
                    if current_altitude > max_altitude:
                        logger.warning(f"Simulation terminated: maximum altitude exceeded at t={t:.2f}s")
                        break
                    
                    if current_range > max_range:
                        logger.warning(f"Simulation terminated: maximum range exceeded at t={t:.2f}s")
                        break
                    
                    if np.any(np.isnan([current_altitude, current_velocity])):
                        raise RuntimeError(f"Numerical instability detected at t={t:.2f}s")
                    
                    t += timestep
                    rocket.update_time(timestep)
                    
                except Exception as step_error:
                    logger.error(f"Error in simulation step at t={t:.3f}s: {step_error}")
                    raise
            
            # Final metrics
            metrics['flight_duration'] = t
            
            # Prepare results
            results = {
                'status': 'success',
                'trajectory': trajectory,
                'metrics': metrics,
                'total_steps': i + 1,
                'simulation_time': t,
                'rocket': rocket_name,
                'location': location_name,
            }
            
            logger.info(f"Simulation completed successfully: {i+1} steps, {t:.2f}s flight time")
            logger.info(f"Max altitude: {metrics['max_altitude']:.2f}m, Max velocity: {metrics['max_velocity']:.2f}m/s")
            
            self.finished.emit(results)
            
        except Exception as e:
            logger.error(f"Simulation error: {str(e)}", exc_info=True)
            self.error.emit(f"Simulation failed: {str(e)}")
    
    def _load_rocket_config(self, rocket_name: str) -> dict:
        """Load rocket configuration from JSON file."""
        try:
            config_path = f"data/rockets/configs/{rocket_name}.json"
            if not os.path.exists(config_path):
                logger.error(f"Rocket config not found: {config_path}")
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate and fix moment of inertia values (prevent singular matrices)
            # If inertia values are zero or too small, set minimum values
            min_inertia = 1.0  # kg·m² minimum to prevent singular matrices
            
            for inertia_key in ['I_before_burn', 'I_after_burn']:
                if inertia_key in config:
                    for axis in ['x', 'y', 'z']:
                        current_value = config[inertia_key].get(axis, 0)
                        if current_value < min_inertia:
                            logger.warning(
                                f"Inertia {inertia_key}[{axis}] = {current_value} is too small, "
                                f"setting to {min_inertia} kg·m² to prevent singularity"
                            )
                            config[inertia_key][axis] = min_inertia
            
            logger.info(f"Loaded rocket configuration: {rocket_name}")
            return config
        except Exception as e:
            logger.error(f"Error loading rocket config: {e}")
            return None
    
    def stop(self):
        """Stop the simulation worker."""
        self.is_running = False
        self.wait()
        logger.info("Simulation worker stopped")
