# Author: Nicolas Sturm
#         Rocket Simulator - Clean Architecture Refactoring
#         Phase 4: Backward Compatibility Adapter

"""
Backward Compatibility Adapter for New Rocket Architecture

This module provides adapter classes that allow gradual migration from the
legacy monolithic Rocket class to the new component-based architecture.

For Phase 4, this adapter now uses the new component-based Rocket implementation
with full dependency injection support.

Usage:
    # Existing code continues to work:
    from src.models.rocket import Rocket
    rocket = Rocket(r_enu_0, v_enu_0, q_enu2b_0, w_enu_0, initial_mass)
    rocket.step(dt=0.1)  # Use new step() method instead of RK4_update()

Design Principles:
    - Maintain similar interface to old Rocket class
    - Use new component-based architecture
    - Provide foundation for realistic rocket simulations
"""

import numpy as np
from typing import Optional, Any
import json
import logging

# Use the new component-based Rocket
from src.models.rocket.rocket import Rocket as NewRocket
from src.models.engine import EnhancedEngine
from src.models.aerodynamics import Aerodynamics
from src.models.atmosphere import Atmosphere
from src.utils.simulation_constants import RocketConstants as RC

logger = logging.getLogger(__name__)


class LegacyRocketAdapter:
    """
    Adapter that provides compatibility with the old Rocket interface.
    
    For Phase 4, this creates a new component-based Rocket with default dependencies.
    """
    
    def __new__(cls, r_enu_0, v_enu_0, q_enu2b_0, w_enu_0, initial_mass, **kwargs):
        """
        Create a new Rocket instance using the new architecture.
        
        Args:
            r_enu_0: Initial position [m]
            v_enu_0: Initial velocity [m/s]
            q_enu2b_0: Initial quaternion
            w_enu_0: Initial angular velocity [rad/s]
            initial_mass: Initial mass [kg]
            **kwargs: Additional keyword arguments
        """
        # Create default dependencies
        atmosphere = Atmosphere(15.0)
        engine = EnhancedEngine(
            time=0.0,
            burn_time=kwargs.get('burn_time', 10.0),
            ambient_pressure=RC.DEFAULT_PRESSURE,
            nozzle_exit_diameter=kwargs.get('nozzle_exit_diameter', 0.05),
            propellant_mass=kwargs.get('propellant_mass', 1.0),
            specific_impulse=kwargs.get('specific_impulse', 200.0),
            mean_thrust=kwargs.get('mean_thrust', 500.0),
            max_thrust=kwargs.get('max_thrust', 600.0),
            mean_chamber_pressure=kwargs.get('mean_chamber_pressure', 1000000.0),
            max_chamber_pressure=kwargs.get('max_chamber_pressure', 1200000.0),
            thrust_to_weight_ratio=kwargs.get('thrust_to_weight_ratio', 20.0)
        )
        aerodynamics = Aerodynamics(cd=0.5, cl=0.0)
        
        # Create new Rocket with dependency injection
        return NewRocket(
            r_enu_0=r_enu_0,
            v_enu_0=v_enu_0,
            q_enu2b_0=q_enu2b_0,
            w_enu_0=w_enu_0,
            initial_mass=initial_mass,
            engine=engine,
            atmosphere=atmosphere,
            aerodynamics=aerodynamics,
            reference_area=kwargs.get('reference_area', 0.01)
        )


# For backward compatibility - Rocket now uses new architecture
Rocket = NewRocket

__all__ = ['LegacyRocketAdapter', 'Rocket']
