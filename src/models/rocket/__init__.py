# Rocket Module Package

"""
Rocket simulation components using clean architecture.

This package contains the refactored Rocket simulation components,
organized by responsibility and using dependency injection.

Phase 4 Status:
    - Legacy Rocket: src/models/rocket_legacy.py (renamed from rocket.py)
    - New Architecture: src/models/rocket/ package with clean separation
    - Backward Compatibility: This __init__.py provides both implementations

Migration Strategy:
    - Default: Use legacy Rocket for backward compatibility
    - Future: Gradually migrate simulation_worker.py to use new architecture
    - Set ROCKET_USE_NEW_ARCHITECTURE=true to enable new architecture (WIP)

Structure:
    adapter.py: LegacyRocketAdapter - Backward compatible wrapper
    state.py: RocketState - Pure state management
    dynamics.py: RocketDynamics - Force and torque calculations
    simulation.py: RocketSimulation - Numerical integration and history
    rocket.py: Rocket - Composition root (new architecture)

Example (New Architecture):
    from src.models.rocket.rocket import Rocket as NewRocket
    from src.models.rocket.state import RocketState
    from src.models.rocket.dynamics import RocketDynamics
    from src.models.engine import EnhancedEngine
    from src.models.aerodynamics import EnhancedAerodynamics
    from src.models.atmosphere import Atmosphere
    
    # Create dependencies
    engine = EnhancedEngine(...)
    aerodynamics = EnhancedAerodynamics(...)
    atmosphere = Atmosphere(15.0)
    
    # Create new Rocket with dependency injection
    rocket = NewRocket(
        r_enu_0=r_enu_0,
        v_enu_0=v_enu_0,
        q_enu2b_0=q_enu2b_0,
        w_enu_0=w_enu_0,
        initial_mass=10.0,
        engine=engine,
        aerodynamics=aerodynamics,
        atmosphere=atmosphere
    )

Example (Legacy - Backward Compatible):
    from src.models.rocket import Rocket
    rocket = Rocket(r_enu_0, v_enu_0, q_enu2b_0, w_enu_0, initial_mass)
    # All old methods work
    rocket.update_engine(rocket_name, engine_data)
    rocket.RK4_update(timestep)
"""

import os

# Configuration: Use new architecture or legacy
# Set ROCKET_USE_NEW_ARCHITECTURE=true to use the new component-based Rocket
USE_NEW_ARCHITECTURE = os.environ.get('ROCKET_USE_NEW_ARCHITECTURE', 'false').lower() == 'true'

if USE_NEW_ARCHITECTURE:
    # New architecture mode (Phase 4 - Work in Progress)
    from src.models.rocket.rocket import Rocket as NewRocket
    from src.models.rocket.state import RocketState
    from src.models.rocket.dynamics import RocketDynamics
    from src.models.rocket.simulation import RocketSimulation
    from src.models.rocket.adapter import LegacyRocketAdapter
    from src.models.engine import EnhancedEngine
    from src.models.aerodynamics import EnhancedAerodynamics, AerodynamicsWrapper
    from src.models.atmosphere import Atmosphere
    from src.models.parachute import Parachute
    from src.models.clock import Clock
    from src.models.planet import Planet
    from src.models.mass_properties import MassProperties, SimpleMassProperties
    from src.models.interfaces import (
        IEngine, IAerodynamics, IParachute, IAtmosphere, IMassProperties
    )
    
    # For now, Rocket still delegates to legacy via adapter
    # As we migrate simulation_worker.py, we'll update this
    from src.models.rocket.adapter import Rocket
    
    __all__ = [
        'Rocket',
        'LegacyRocketAdapter',
        'NewRocket',
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
        'EnhancedAerodynamics',
        'AerodynamicsWrapper',
        'Atmosphere',
        'Parachute',
        'Clock',
        'Planet',
        'MassProperties',
        'SimpleMassProperties',
        'IEngine',
        'IAerodynamics',
        'IParachute',
        'IAtmosphere',
        'IMassProperties',
    ]

else:
    # Legacy mode (default for backward compatibility)
    from src.models.rocket_legacy import Rocket
    from src.models.engine import EnhancedEngine
    from src.models.aerodynamics import AerodynamicsWrapper, EnhancedAerodynamics
    from src.models.atmosphere import Atmosphere
    from src.models.parachute import Parachute
    from src.models.clock import Clock
    from src.models.planet import Planet
    from src.models.rocket.adapter import LegacyRocketAdapter
    
    # Re-export all commonly used classes
    __all__ = [
        'Rocket',
        'LegacyRocketAdapter',
        'EnhancedEngine',
        'AerodynamicsWrapper',
        'EnhancedAerodynamics',
        'Atmosphere',
        'Parachute',
        'Clock',
        'Planet',
    ]
    
    # Also export legacy-specific classes
    try:
        from src.models.rocket_legacy import (
            RocketSimulationError, NumericalStabilityError, 
            PhysicsCalculationError, InputValidationError, ConfigurationError
        )
        __all__.extend(['RocketSimulationError', 'NumericalStabilityError', 
                       'PhysicsCalculationError', 'InputValidationError', 
                       'ConfigurationError'])
    except ImportError:
        pass

# Always export factory functions (available in both modes)
from src.models.rocket.factory import (
    create_rocket_from_config, create_engine, create_aerodynamics,
    create_mass_properties, load_rocket_config, update_rocket_for_step,
    run_simulation
)

# Add factory functions to __all__
if 'create_rocket_from_config' not in __all__:
    __all__.extend([
        'create_rocket_from_config',
        'create_engine',
        'create_aerodynamics',
        'create_mass_properties',
        'load_rocket_config',
        'update_rocket_for_step',
        'run_simulation',
    ])
