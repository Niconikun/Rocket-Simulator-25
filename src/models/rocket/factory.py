# Author: Nicolas Sturm
#         Rocket Simulator - Clean Architecture Refactoring
#         Phase 4: Rocket Factory

"""
Rocket Factory Module

This module provides factory functions for creating Rocket instances with proper
dependency injection, making it easier to migrate from the legacy monolithic
Rocket to the new component-based architecture.

Usage:
    from src.models.rocket.factory import create_rocket_from_config
    
    # Create a fully configured rocket from a rocket configuration
    rocket = create_rocket_from_config(
        r_enu_0=r_enu_0,
        v_enu_0=v_enu_0,
        q_enu2b_0=q_enu2b_0,
        w_enu_0=w_enu_0,
        initial_mass=10.0,
        rocket_name='rocket_name',
        engine_data=engine_config,
        reference_area=0.01
    )
    
    # Then use it in simulation
    rocket.step(dt=0.1)
    
    # Or use the simulation helper
    results = run_simulation(rocket, runtime=10.0, timestep=0.1)

Design Principles:
    - Factory pattern for creating properly configured Rocket instances
    - Dependency injection for all components
    - Gradual migration path from legacy to new architecture
    - Clear separation between creation and usage
"""

import json
import logging
import numpy as np
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from src.models.rocket.rocket import Rocket as NewRocket
from src.models.rocket.state import RocketState
from src.models.atmosphere import Atmosphere
from src.models.engine import EnhancedEngine
from src.models.aerodynamics import Aerodynamics, SimpleAerodynamics
from src.models.mass_properties import MassProperties
from src.models.interfaces import IEngine, IAerodynamics, IAtmosphere, IMassProperties

logger = logging.getLogger(__name__)


def load_rocket_config(rocket_name: str, configs_dir: str = 'data/rockets/configs') -> dict:
    """
    Load rocket configuration from JSON file.
    
    Args:
        rocket_name: Name of the rocket configuration file (without .json extension)
        configs_dir: Directory containing rocket configuration files
    
    Returns:
        dict: Rocket configuration dictionary
    
    Raises:
        FileNotFoundError: If configuration file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    config_path = Path(configs_dir) / f"{rocket_name}.json"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Rocket configuration not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config


def create_engine(engine_data: dict, time: float = 0.0, ambient_pressure: float = 101325.0) -> IEngine:
    """
    Create an engine instance from configuration.
    
    Args:
        engine_data: Engine configuration dictionary
        time: Initial time [s]
        ambient_pressure: Initial ambient pressure [Pa]
    
    Returns:
        IEngine: Configured engine instance
    """
    thrust_curve_file = engine_data.get('thrust_curve_file')
    thrust_curve_unit = engine_data.get('thrust_curve_unit', 'N')
    
    # Handle experimental thrust curve mode
    if engine_data.get('thrust_curve_mode') == 'experimental':
        if not thrust_curve_file:
            raise ValueError("'thrust_curve_file' is required for experimental thrust curve mode")
        if not thrust_curve_unit:
            raise ValueError("'thrust_curve_unit' is required for experimental thrust curve mode")
    else:
        thrust_curve_file = None
    
    engine = EnhancedEngine(
        time=time,
        burn_time=engine_data["burn_time"],
        ambient_pressure=ambient_pressure,
        nozzle_exit_diameter=engine_data["nozzle_exit_diameter"],
        propellant_mass=engine_data["propellant_mass"],
        specific_impulse=engine_data["specific_impulse"],
        mean_thrust=engine_data["mean_thrust"],
        max_thrust=engine_data["max_thrust"],
        mean_chamber_pressure=engine_data["mean_chamber_pressure"],
        max_chamber_pressure=engine_data["max_chamber_pressure"],
        thrust_to_weight_ratio=engine_data["thrust_to_weight_ratio"],
        thrust_curve_file=thrust_curve_file,
        thrust_curve_unit=thrust_curve_unit,
    )
    
    return engine


def create_aerodynamics(
    mach: float,
    angle_attack: float,
    height: float,
    atmosphere: IAtmosphere,
    rocket_config: dict,
    mass_props_before: Dict[str, float],
    mass_props_after: Dict[str, float]
) -> IAerodynamics:
    """
    Create an aerodynamics instance from configuration.
    
    Args:
        mach: Initial Mach number
        angle_attack: Initial angle of attack [deg]
        height: Initial altitude [m]
        atmosphere: Atmosphere instance
        rocket_config: Full rocket configuration dictionary
        mass_props_before: Center of mass and inertia before burn
        mass_props_after: Center of mass and inertia after burn
    
    Returns:
        IAerodynamics: Configured aerodynamics instance
    """
    # Extract geometry from config
    geometry = rocket_config.get('geometry', {})
    fuselage = rocket_config.get('fuselage', {})
    nosecone = rocket_config.get('nosecone', {})
    rear_section = rocket_config.get('rear_section', {})
    fins = rocket_config.get('fins', {})
    
    # Build mass properties dict (for aerodynamics calculations)
    mass_props = {
        'CoM_before_burn': mass_props_before,
        'CoM_after_burn': mass_props_after,
        'I_before_burn': mass_props_before,  # Simplified - in reality these might differ
        'I_after_burn': mass_props_after,
    }
    
    # Build rocket data dict (for aerodynamics calculations)
    rocket_data = {
        'reference_area': rocket_config.get('reference_area', 0.01),
        'geometry': geometry,
        'fuselage': fuselage,
        'nosecone': nosecone,
        'rear_section': rear_section,
        'fins': fins,
    }
    
    # Create aerodynamics with geometry-based calculations (Barrowman method)
    aero = Aerodynamics(
        mach=mach,
        angle_attack=angle_attack,
        height=height,
        atmosphere=atmosphere,
        rocket_data=rocket_data,
        mass_props=mass_props
    )
    
    return aero


def create_mass_properties(
    initial_mass: float,
    propellant_mass: float,
    com_before: Dict[str, float],
    inertia_before: Dict[str, float],
    com_after: Dict[str, float],
    inertia_after: Dict[str, float]
) -> IMassProperties:
    """
    Create mass properties instance.
    
    Args:
        initial_mass: Initial total mass [kg]
        propellant_mass: Total propellant mass [kg]
        com_before: Center of mass before burn [x, y, z] in body frame [m]
        inertia_before: Moments of inertia before burn [Ixx, Iyy, Izz] [kg·m²]
        com_after: Center of mass after burn [x, y, z] in body frame [m]
        inertia_after: Moments of inertia after burn [Ixx, Iyy, Izz] [kg·m²]
    
    Returns:
        IMassProperties: Mass properties instance
    """
    mass_props = MassProperties(
        mass_before=initial_mass,
        mass_after=initial_mass - propellant_mass,
        cm_before=np.array([com_before['x'], com_before['y'], com_before['z']]),
        cm_after=np.array([com_after['x'], com_after['y'], com_after['z']]),
        inertia_before=np.array([inertia_before['x'], inertia_before['y'], inertia_before['z']]),
        inertia_after=np.array([inertia_after['x'], inertia_after['y'], inertia_after['z']])
    )
    
    return mass_props


def create_rocket_from_config(
    r_enu_0: np.ndarray,
    v_enu_0: np.ndarray,
    q_enu2b_0: np.ndarray,
    w_enu_0: np.ndarray,
    initial_mass: float,
    rocket_name: str,
    temperature: float = 15.0,
    configs_dir: str = 'data/rockets/configs',
    wind_vector_enu: Optional[np.ndarray] = None,
    reference_area: Optional[float] = None
) -> Tuple[NewRocket, dict, IEngine, IAerodynamics, IAtmosphere]:
    """
    Create a fully configured Rocket from a rocket configuration file.
    
    This is the main factory function for creating rockets with the new architecture.
    It loads the configuration, creates all dependencies, and returns a ready-to-use Rocket.
    
    Args:
        r_enu_0: Initial position in ENU frame [m]
        v_enu_0: Initial velocity in ENU frame [m/s]
        q_enu2b_0: Initial quaternion from ENU to body frame
        w_enu_0: Initial angular velocity in ENU frame [rad/s]
        initial_mass: Initial total mass [kg]
        rocket_name: Name of rocket configuration file (without .json)
        temperature: Initial temperature for atmosphere [°C]
        configs_dir: Directory containing rocket configurations
        wind_vector_enu: Initial wind vector in ENU frame [m/s]
        reference_area: Reference area for aerodynamics [m²]
    
    Returns:
        Tuple containing:
        - NewRocket: Configured rocket instance
        - rocket_config: Loaded rocket configuration dictionary
        - engine: Configured engine instance
        - aerodynamics: Configured aerodynamics instance
        - atmosphere: Configured atmosphere instance
    
    Raises:
        FileNotFoundError: If rocket configuration doesn't exist
        ValueError: If configuration is invalid
    """
    # Load rocket configuration
    rocket_config = load_rocket_config(rocket_name, configs_dir)
    
    # Create atmosphere
    atmosphere = Atmosphere(temperature)
    
    # Create engine
    engine_data = rocket_config.get('engine', {})
    propellant_mass = engine_data.get('propellant_mass', 0.0)
    engine = create_engine(engine_data, time=0.0, ambient_pressure=atmosphere.give_pressure(0.0))
    
    # Create mass properties
    mass_props_before = rocket_config.get('CoM_before_burn', {'x': 0, 'y': 0, 'z': 0})
    mass_props_after = rocket_config.get('CoM_after_burn', {'x': 0, 'y': 0, 'z': 0})
    inertia_before = rocket_config.get('I_before_burn', {'x': 0.1, 'y': 0.1, 'z': 0.05})
    inertia_after = rocket_config.get('I_after_burn', {'x': 0.1, 'y': 0.1, 'z': 0.05})
    
    mass_properties = create_mass_properties(
        initial_mass=initial_mass,
        propellant_mass=propellant_mass,
        com_before=mass_props_before,
        inertia_before=inertia_before,
        com_after=mass_props_after,
        inertia_after=inertia_after
    )
    
    # Get reference area from config or use provided
    ref_area = reference_area if reference_area is not None else rocket_config.get('reference_area', 0.01)
    
    # Create rocket with dependency injection
    rocket = NewRocket(
        r_enu_0=r_enu_0,
        v_enu_0=v_enu_0,
        q_enu2b_0=q_enu2b_0,
        w_enu_0=w_enu_0,
        initial_mass=initial_mass,
        engine=engine,
        atmosphere=atmosphere,
        mass_properties=mass_properties,
        reference_area=ref_area,
        wind_vector_enu=wind_vector_enu,
        propellant_mass=propellant_mass
    )
    
    # Create aerodynamics (requires rocket data and mass props)
    # We'll use initial values for now
    mach = 0.0
    angle_attack = 0.0
    height = r_enu_0[2]
    
    aerodynamics = create_aerodynamics(
        mach=mach,
        angle_attack=angle_attack,
        height=height,
        atmosphere=atmosphere,
        rocket_config=rocket_config,
        mass_props_before=mass_props_before,
        mass_props_after=mass_props_after
    )
    
    # Set aerodynamics on the rocket
    rocket.set_aerodynamics(aerodynamics)
    
    return rocket, rocket_config, engine, aerodynamics, atmosphere


def update_rocket_for_step(
    rocket: NewRocket,
    atmosphere: IAtmosphere,
    coordinates: np.ndarray,
    timestep: float,
    wind_vector_enu: Optional[np.ndarray] = None
) -> None:
    """
    Update rocket state for a simulation step.
    
    This function handles all the updates that were previously done by
    individual method calls in the legacy Rocket class.
    
    Args:
        rocket: Rocket instance to update
        atmosphere: Atmosphere instance
        coordinates: Launch coordinates [lat, lon, alt]
        timestep: Simulation timestep [s]
        wind_vector_enu: Wind vector in ENU frame [m/s]
    """
    # Update wind
    if wind_vector_enu is not None:
        rocket.set_wind(wind_vector_enu)
    
    # Update atmosphere based on current altitude
    altitude = rocket.state.r_enu[2]
    rocket.dynamics.update_atmosphere(altitude)
    
    # Update aerodynamics
    # Note: This would require updating the aerodynamics with current flight conditions
    # For now, we'll defer this to a future enhancement
    
    # Perform simulation step
    rocket.step(timestep)


def run_simulation(
    rocket: NewRocket,
    runtime: float,
    timestep: float,
    atmosphere: IAtmosphere,
    coordinates: np.ndarray,
    wind_vector_enu: Optional[np.ndarray] = None
) -> dict:
    """
    Run a complete simulation with the new Rocket architecture.
    
    This is a simplified simulation loop that demonstrates how to use
    the new architecture. For full functionality, see simulation_worker.py.
    
    Args:
        rocket: Configured Rocket instance
        runtime: Total simulation runtime [s]
        timestep: Simulation timestep [s]
        atmosphere: Atmosphere instance
        coordinates: Launch coordinates [lat, lon, alt]
        wind_vector_enu: Wind vector in ENU frame [m/s]
    
    Returns:
        dict: Simulation results with trajectory and metrics
    """
    num_steps = int(runtime / timestep)
    trajectory = []
    
    metrics = {
        'max_altitude': 0.0,
        'max_velocity': 0.0,
        'flight_duration': 0.0,
    }
    
    for i in range(num_steps):
        # Update rocket for this step
        update_rocket_for_step(rocket, atmosphere, coordinates, timestep, wind_vector_enu)
        
        # Record trajectory
        current_altitude = rocket.state.r_enu[2]
        current_velocity = float(np.linalg.norm(rocket.state.v_enu))
        
        metrics['max_altitude'] = max(metrics['max_altitude'], current_altitude)
        metrics['max_velocity'] = max(metrics['max_velocity'], current_velocity)
        
        if i % 10 == 0:  # Store every 10 steps
            trajectory.append({
                'time': rocket.state.time,
                'altitude': current_altitude,
                'velocity': current_velocity,
            })
        
        # Check termination (simplified)
        if current_altitude <= 0 and rocket.state.time > 1.0:
            metrics['flight_duration'] = rocket.state.time
            break
    
    return {
        'trajectory': trajectory,
        'metrics': metrics,
        'status': 'success'
    }


__all__ = [
    'load_rocket_config',
    'create_engine',
    'create_aerodynamics',
    'create_mass_properties',
    'create_rocket_from_config',
    'update_rocket_for_step',
    'run_simulation',
]
