# Rocket Module Package

"""
Rocket simulation components using clean architecture.

This package contains the component-based Rocket simulation with dependency injection.

Phase 4 Status:
    - New Architecture: Fully migrated to component-based design
    - Legacy Rocket: Removed (rocket_legacy.py deleted)
    - All code now uses the new architecture with dependency injection

Structure:
    adapter.py: Backward compatible wrapper for new Rocket
    state.py: RocketState - Pure state management
    dynamics.py: RocketDynamics - Force and torque calculations
    simulation.py: RocketSimulation - Numerical integration and history
    rocket.py: Rocket - Composition root with dependency injection
    factory.py: Factory functions for creating configured rockets

Example (New Architecture):
    from src.models.rocket import Rocket
    from src.models.rocket.factory import create_rocket_from_config
    
    # Method 1: Direct instantiation with dependencies
    from src.models.engine import EnhancedEngine
    from src.models.aerodynamics import Aerodynamics
    from src.models.atmosphere import Atmosphere
    
    engine = EnhancedEngine(...)
    aerodynamics = Aerodynamics(mach=0.0, angle_attack=0.0, height=0.0,
                                  atmosphere=atmosphere, rocket_data=config)
    rocket = Rocket(r_enu_0, v_enu_0, q_enu2b_0, w_enu_0, initial_mass,
                   engine=engine, aerodynamics=aerodynamics, atmosphere=atmosphere)
    
    # Method 2: Using factory (recommended)
    rocket, config, engine, aero, atmosphere = create_rocket_from_config(
        r_enu_0=r_enu_0, v_enu_0=v_enu_0, q_enu2b_0=q_enu2b_0, 
        w_enu_0=w_enu_0, initial_mass=10.0, rocket_name='Campanil 1-A')
    
    # Use in simulation
    rocket.step(dt=0.1)
    position = rocket.position
    velocity = rocket.velocity
"""

# Use new architecture by default
from src.models.rocket.rocket import Rocket
from src.models.rocket.state import RocketState
from src.models.rocket.dynamics import RocketDynamics
from src.models.rocket.simulation import RocketSimulation
from src.models.rocket.adapter import LegacyRocketAdapter
from src.models.engine import EnhancedEngine
from src.models.aerodynamics import Aerodynamics
from src.models.atmosphere import Atmosphere
from src.models.parachute import Parachute
from src.models.clock import Clock
from src.models.planet import Planet
from src.models.mass_properties import MassProperties
from src.models.interfaces import (
    IEngine, IAerodynamics, IParachute, IAtmosphere, IMassProperties
)

__all__ = [
    'Rocket',
    'LegacyRocketAdapter',
    'RocketState',
    'RocketDynamics',
    'RocketSimulation',
    'create_rocket_from_config',
    'create_engine',
    'create_aerodynamics',
    'create_mass_properties',
    'load_rocket_config',
    'update_rocket_for_step',
    'run_simulation',
    'EnhancedEngine',
    'Aerodynamics',
    'Atmosphere',
    'Parachute',
    'Clock',
    'Planet',
    'MassProperties',
    'IEngine',
    'IAerodynamics',
    'IParachute',
    'IAtmosphere',
    'IMassProperties',
]

# Always export factory functions (available in both modes)
from src.models.rocket.factory import (
    create_rocket_from_config, create_engine, create_aerodynamics,
    create_mass_properties, create_wind_model, create_parachute, load_rocket_config,
    update_rocket_for_step, run_simulation,
    # Builder pattern components
    RocketBuilder,
    EngineConfig,
    ParachuteConfig,
    MassPropertiesConfig,
    AerodynamicsConfig,
    RocketConfigurationError,
    RocketFileNotFoundError
)

# Add factory functions to __all__
if 'create_rocket_from_config' not in __all__:
    __all__.extend([
        'create_rocket_from_config',
        'create_engine',
        'create_aerodynamics',
        'create_mass_properties',
        'create_wind_model',
        'create_parachute',
        'load_rocket_config',
        'update_rocket_for_step',
        'run_simulation',
        'RocketBuilder',
        'EngineConfig',
        'ParachuteConfig',
        'MassPropertiesConfig',
        'AerodynamicsConfig',
        'RocketConfigurationError',
        'RocketFileNotFoundError',
    ])
