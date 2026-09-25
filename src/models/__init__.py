"""Models package for Rocket Simulator

This package contains all the physics and simulation models used by the
Rocket Simulator application.

Available classes:
    - ApplicationState: Singleton for managing application state
    - Atmosphere: US Standard Atmosphere 1976 model
    - Clock: Time and date calculations with GMST
    - Aerodynamics: Unified aerodynamics model (SimpleAerodynamics is an alias)
    - EnhancedEngine: Rocket engine simulation
    - Parachute: Parachute deployment and descent simulation
    - Planet: Earth rotation tracking (GMST)
    - Rocket: Main rocket simulation class
    - WindModel: Base class for wind models
    - ConstantWind: Simple constant wind model
    - LogarithmicWind: Logarithmic wind profile (recommended)
    - PowerLawWind: Power law wind profile
    - GustWind: Wind with turbulent gusts
    - WindShearWind: 3D wind shear model

Factory functions:
    - create_wind_model: Create wind models by name
    - create_wind_model_from_state: Create wind models from scenario dict

Note: EnhancedAerodynamics and AerodynamicsWrapper have been replaced
with the unified Aerodynamics class for simplicity and maintainability.
"""

from .app_state import ApplicationState
from .atmosphere import Atmosphere
from .state import StateProvider, StateProxy, MockStateProvider, ReadOnlyStateProvider
from .clock import Clock
from .aerodynamics import Aerodynamics, SimpleAerodynamics
from .engine import EnhancedEngine
from .gravitational import g_accel, g_torque
from .parachute import Parachute
from .planet import Planet
from .rocket import Rocket
from .wind import (
    WindModel,
    ConstantWind,
    LogarithmicWind,
    PowerLawWind,
    GustWind,
    WindShearWind,
    create_wind_model,
    create_wind_model_from_state,
)

__all__ = [
    # State management
    'ApplicationState',
    'StateProvider',
    'StateProxy',
    'MockStateProvider',
    'ReadOnlyStateProvider',
    # Atmosphere
    'Atmosphere',
    # Time
    'Clock',
    # Aerodynamics
    'Aerodynamics',
    'SimpleAerodynamics',
    # Engine
    'EnhancedEngine',
    # Gravity
    'g_accel',
    'g_torque',
    # Parachute
    'Parachute',
    # Planet
    'Planet',
    # Rocket
    'Rocket',
    # Wind models
    'WindModel',
    'ConstantWind',
    'LogarithmicWind',
    'PowerLawWind',
    'GustWind',
    'WindShearWind',
    'create_wind_model',
    'create_wind_model_from_state',
]
