# Author: Nicolas Sturm (refactored from Jorge Orozco's original)
#         Rocket Simulator - Clean Architecture Refactoring
#         Phase 4: Unified Aerodynamics Module with Barrowman Method

"""
Aerodynamics Module

Unified aerodynamics module with realistic calculations for rocket flight simulations.

This module provides a single implementation of IAerodynamics that uses:
- Barrowman method for normal force coefficients and center of pressure
- Component-based drag modeling (skin friction, pressure, base, interference, wave)
- Mach number corrections for transonic and supersonic regimes
- Geometry-based calculations from actual rocket dimensions

All calculations are performed in consistent SI units (meters, kg, seconds).

Design Principles:
    - Realistic physics-based calculations
    - Single source of truth for all aerodynamic properties
    - Clean, maintainable code without duplication
    - Proper unit handling (all inputs expected in SI units)

External dependencies:
    numpy - Numpy Python extension. http://numpy.org/

References:
    [Barro67] Barrowman (1967) - The Practical Calculation of the Aerodynamic 
               Characteristic of Slender Finned Vehicles
"""

import numpy as np
import math
import logging
from typing import Optional, Dict, Any

from src.models.interfaces import IAerodynamics
from src.utils.simulation_errors import InputValidationError

logger = logging.getLogger(__name__)

# Constants
from src.utils.simulation_constants import (
    AtmosphereConstants as AC,
    AerodynamicsConstants as ADC
)

MAX_ANGLE_OF_ATTACK = 20.0  # Maximum angle of attack in degrees [deg]
SEA_LEVEL_DENSITY = AC.SEA_LEVEL_DENSITY  # kg/m³
SEA_LEVEL_TEMPERATURE = AC.SEA_LEVEL_TEMPERATURE  # K
SPEED_OF_SOUND_SEA_LEVEL = ADC.SPEED_OF_SOUND_SEA_LEVEL  # m/s at sea level, 15°C
SUTHERLAND_C1 = ADC.SUTHERLAND_C1  # Sutherland's constant for air
SUTHERLAND_S = ADC.SUTHERLAND_S  # Sutherland's constant for air [K]
TURBULENT_SKIN_FRICTION_K = ADC.TURBULENT_SKIN_FRICTION_K  # Skin friction constant for turbulent flow


# =============================================================================
# Helper Functions
# =============================================================================

def _validate_angle(angle: float) -> float:
    """
    Validate and clamp angle of attack.
    
    Args:
        angle: Angle of attack [deg]
    
    Returns:
        Clamped angle of attack [deg]
    """
    if abs(angle) >= MAX_ANGLE_OF_ATTACK:
        return MAX_ANGLE_OF_ATTACK * (abs(angle) / angle) if angle != 0 else 0.0
    return float(angle)


def _calculate_dynamic_viscosity(temperature: float) -> float:
    """
    Calculate dynamic viscosity using Sutherland's formula.
    
    Args:
        temperature: Temperature [K]
    
    Returns:
        Dynamic viscosity [Pa·s]
    """
    T = temperature
    return (SUTHERLAND_C1 * T**1.5) / (T + SUTHERLAND_S)


# =============================================================================
# Aerodynamics Class (Primary Implementation with Barrowman Method)
# =============================================================================

class Aerodynamics(IAerodynamics):
    """
    Aerodynamics model for rocket flight simulations using Barrowman method.
    
    This implementation provides realistic aerodynamic coefficient calculations
    based on actual rocket geometry, including:
    - Component-based drag (skin friction, pressure, base, interference, wave)
    - Lift coefficient calculations using Barrowman method
    - Center of pressure and stability margin calculations
    - Mach number corrections for transonic and supersonic regimes
    
    The class can be initialized in two ways:
    1. With rocket configuration data (recommended for realistic simulations)
    2. With constant coefficients (for testing or when geometry data unavailable)
    
    Attributes:
        mach: Mach number [-]
        alpha: Angle of attack [deg]
        height: Altitude [m]
        cd: Drag coefficient [-]
        cl: Lift coefficient [-]
        xcp: Center of pressure position in body frame [x, y, z] [m]
        stability_margin: Stability margin in calibers (positive = stable)
    
    Usage:
        # Recommended: Initialize with rocket configuration
        aero = Aerodynamics(
            mach=0.0,
            angle_attack=0.0,
            height=0.0,
            atmosphere=atmosphere_instance,
            rocket_data=rocket_config_dict,
            mass_props=mass_properties_dict
        )
        
        # For testing: Initialize with constant coefficients
        aero = Aerodynamics(cd=0.5, cl=0.0)
        
        # Use in simulation
        cd, cl = aero.get_coefficients()
        forces = aero.get_aerodynamic_forces(dynamic_pressure=1000.0)
    """
    
    def __init__(
        self,
        # Mode 1: Full configuration with geometry (for realistic simulations)
        mach: Optional[float] = None,
        angle_attack: Optional[float] = None,
        height: Optional[float] = None,
        atmosphere: Optional[Any] = None,
        rocket_data: Optional[Dict[str, Any]] = None,
        mass_props: Optional[Dict[str, Any]] = None,
        # Mode 2: Simple constant coefficients (for testing/fallback)
        cd: Optional[float] = None,
        cl: Optional[float] = None,
        center_of_pressure_x: Optional[float] = None,
        stability_margin: Optional[float] = None,
        reference_area: Optional[float] = None
    ) -> None:
        """
        Initialize aerodynamics with either geometry data or constant coefficients.
        
        Args:
            mach: Initial Mach number [-]
            angle_attack: Initial angle of attack [deg]
            height: Initial altitude [m]
            atmosphere: Atmosphere object with give_dens, give_temp, give_v_sonic methods
            rocket_data: Dictionary containing rocket geometry configuration
            mass_props: Dictionary containing mass properties (CoM, inertia)
            cd: Drag coefficient [-] (for simple mode)
            cl: Lift coefficient [-] (for simple mode)
            center_of_pressure_x: X position of center of pressure [m] (for simple mode)
            stability_margin: Stability margin [calibers] (for simple mode)
            reference_area: Reference area [m²] (for simple mode)
        """
        # Determine if we're using enhanced mode (geometry-based) or simple mode
        self._use_geometry = (rocket_data is not None)
        
        if self._use_geometry:
            # Enhanced mode: Initialize with geometry data
            self._initialize_from_geometry(
                mach=mach or 0.0,
                angle_attack=angle_attack or 0.0,
                height=height or 0.0,
                atmosphere=atmosphere,
                rocket_data=rocket_data,
                mass_props=mass_props or {}
            )
        else:
            # Simple mode: Use constant coefficients
            self._initialize_simple(
                cd=cd or 0.5,
                cl=cl or 0.0,
                center_of_pressure_x=center_of_pressure_x or 0.5,
                stability_margin=stability_margin or 1.0,
                reference_area=reference_area or 0.01
            )
    
    def _initialize_from_geometry(
        self,
        mach: float,
        angle_attack: float,
        height: float,
        atmosphere: Optional[Any],
        rocket_data: Dict[str, Any],
        mass_props: Dict[str, Any]
    ) -> None:
        """Initialize aerodynamics using rocket geometry and Barrowman method."""
        logging.debug(f"Initializing aerodynamics from geometry: Mach={mach:.2f}, α={angle_attack:.1f}°, h={height:.1f}m")
        
        try:
            # Validate inputs
            if mach < 0:
                raise InputValidationError(f"Mach number must be non-negative, got {mach}")
            if height < 0:
                raise InputValidationError(f"Height must be non-negative, got {height}")
            
            # Store basic state
            self.mach = float(mach)
            self.alpha = _validate_angle(angle_attack)
            self.height = float(height)
            self.atmosphere = atmosphere
            self.rocket_data = rocket_data
            self.mass_props = mass_props
            
            # Extract atmospheric properties
            if atmosphere is not None:
                self.rho = atmosphere.give_dens(height)  # [kg/m³]
                self.temp = atmosphere.give_temp(height)  # [K]
                self.speed_of_sound = atmosphere.give_v_sonic(height)  # [m/s]
                self.velocity = mach * self.speed_of_sound  # [m/s]
            else:
                # Fallback values
                self.rho = SEA_LEVEL_DENSITY
                self.temp = SEA_LEVEL_TEMPERATURE
                self.speed_of_sound = SPEED_OF_SOUND_SEA_LEVEL
                self.velocity = mach * SPEED_OF_SOUND_SEA_LEVEL
            
            # Reference parameters
            self.ref_area = rocket_data.get('reference_area', 0.01)  # [m²]
            
            # Get fuselage diameter for reference
            fuselage = rocket_data.get('fuselage', {})
            self.ref_diameter = fuselage.get('diameter', 0.1)  # [m]
            
            # Calculate and store coefficients using geometry
            self._cd = self._calculate_drag_coefficient()
            self._cl = self._calculate_lift_coefficient()
            self._xcp = self._calculate_pressure_center()
            self._stability_margin = self._calculate_stability_margin()
            
            logging.debug(f"Coefficients calculated: CD={self._cd:.4f}, CL={self._cl:.4f}, "
                        f"Stability={self._stability_margin:.2f} calibers")
            
        except KeyError as e:
            logging.error(f"Missing required rocket_data key: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Error in aerodynamics initialization: {str(e)}")
            raise
    
    def _initialize_simple(
        self,
        cd: float,
        cl: float,
        center_of_pressure_x: float,
        stability_margin: float,
        reference_area: float
    ) -> None:
        """Initialize aerodynamics with constant coefficients."""
        self._cd = float(cd)
        self._cl = float(cl)
        self._reference_area = float(reference_area)
        self._center_of_pressure_x = float(center_of_pressure_x)
        self._xcp = np.array([center_of_pressure_x, 0.0, 0.0])
        self._stability_margin = float(stability_margin)
        
        # Initialize state variables
        self.mach = 0.0
        self.alpha = 0.0
        self.height = 0.0
        self.rocket_data = {}
        self.mass_props = {}
        
        logging.debug(f"Aerodynamics initialized with constants: CD={cd}, CL={cl}")
    
    # -------------------------------------------------------------------------
    # IAerodynamics Interface Methods
    # -------------------------------------------------------------------------
    
