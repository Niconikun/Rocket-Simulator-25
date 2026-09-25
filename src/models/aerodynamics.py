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

    @classmethod
    def from_rocket_config(cls, rocket_config: Dict[str, Any]) -> "Aerodynamics":
        """
        Create Aerodynamics instance from rocket configuration.
        
        Args:
            rocket_config: Dictionary containing rocket configuration with aerodynamics section
            
        Returns:
            Aerodynamics: Instance initialized from configuration
        """
        aero_config = rocket_config.get("aerodynamics", {})
        cd = aero_config.get("cd", 0.5)
        cl = aero_config.get("cl", 0.0)
        center_of_pressure_x = aero_config.get("center_of_pressure_x", 0.5)
        stability_margin = aero_config.get("stability_margin", 1.0)
        reference_area = rocket_config.get("reference_area", 0.01)
        
        return cls(
            cd=cd,
            cl=cl,
            center_of_pressure_x=center_of_pressure_x,
            stability_margin=stability_margin,
            reference_area=reference_area
        )

    def set_coefficients(self, cd: float, cl: float) -> None:
        """Set drag and lift coefficients."""
        self._cd = float(cd)
        self._cl = float(cl)

    def set_stability_margin(self, stability_margin: float) -> None:
        """Set stability margin."""
        self._stability_margin = float(stability_margin)

    def set_reference_area(self, reference_area: float) -> None:
        """Set reference area."""
        if self._use_geometry:
            self.ref_area = float(reference_area)
        else:
            self._reference_area = float(reference_area)

    def set_center_of_pressure(self, x: float, y: float = 0.0, z: float = 0.0) -> None:
        """Set center of pressure position."""
        self._xcp = np.array([x, y, z])
        self._center_of_pressure_x = float(x)
    
    def update(self, mach: float, angle_attack: float, height: float, 
               density: float) -> None:
        """
        Update aerodynamic coefficients based on flight conditions.
        
        This method recalculates all aerodynamic coefficients based on the current
        flight conditions using Barrowman method and component-based calculations.
        
        Args:
            mach: Mach number [-]
            angle_attack: Angle of attack [deg]
            height: Altitude [m]
            density: Air density [kg/m³]
        """
        self.mach = float(mach)
        self.alpha = _validate_angle(angle_attack)
        self.height = float(height)
        self.rho = density
        
        # Update atmospheric properties if atmosphere object is available
        if hasattr(self, 'atmosphere') and self.atmosphere is not None:
            self.temp = self.atmosphere.give_temp(height)
            self.speed_of_sound = self.atmosphere.give_v_sonic(height)
            self.velocity = mach * self.speed_of_sound
        else:
            # Fallback: calculate velocity from mach and default speed of sound
            self.velocity = mach * SPEED_OF_SOUND_SEA_LEVEL
        
        # Recalculate coefficients if using geometry-based mode
        if self._use_geometry and self.rocket_data:
            self._cd = self._calculate_drag_coefficient()
            self._cl = self._calculate_lift_coefficient()
            self._xcp = self._calculate_pressure_center()
            self._stability_margin = self._calculate_stability_margin()
        
        logging.debug(f"Aerodynamics updated: CD={self._cd:.4f}, CL={self._cl:.4f}, "
                     f"Mach={mach:.2f}, α={angle_attack:.1f}°, h={height:.1f}m")
    
    def get_coefficients(self) -> tuple[float, float]:
        """
        Get drag and lift coefficients.
        
        Returns:
            tuple[float, float]: (drag_coefficient, lift_coefficient)
        """
        return float(self._cd), float(self._cl)
    
    def get_center_of_pressure(self) -> np.ndarray:
        """
        Get center of pressure position in body frame.
        
        Returns:
            np.ndarray: Center of pressure position as [x, y, z] in body frame [m]
        """
        return self._xcp.copy() if hasattr(self, '_xcp') else np.array([0.0, 0.0, 0.0])
    
    def get_stability_margin(self) -> float:
        """
        Get static stability margin.
        
        Returns:
            float: Stability margin in calibers (positive = stable)
        """
        return float(self._stability_margin) if hasattr(self, '_stability_margin') else 0.0
    
    # -------------------------------------------------------------------------
    # Backward Compatibility Properties
    # -------------------------------------------------------------------------
    
    @property
    def cd(self) -> float:
        """Drag coefficient (backward compatibility)."""
        return float(self._cd)
    
    @property
    def cl(self) -> float:
        """Lift coefficient (backward compatibility)."""
        return float(self._cl)
    
    @property
    def xcp(self) -> np.ndarray:
        """Center of pressure (backward compatibility)."""
        return self._xcp.copy()
    
    # -------------------------------------------------------------------------
    # Force Calculations
    # -------------------------------------------------------------------------
    
    def get_aerodynamic_forces(self, dynamic_pressure: float, 
                               reference_area: Optional[float] = None) -> dict:
        """
        Calculate aerodynamic forces in rocket frame.
        
        Args:
            dynamic_pressure: Dynamic pressure [Pa]
            reference_area: Reference area [m²] (optional, uses rocket ref_area if not provided)
        
        Returns:
            dict: Aerodynamic forces and coefficients
                - drag: Drag force [N]
                - lift: Lift force [N]
                - cd: Drag coefficient [-]
                - cl: Lift coefficient [-]
                - cp_position: Center of pressure [x, y, z] [m]
                - stability_margin: Stability margin [calibers]
        """
        ref_area = reference_area if reference_area is not None else (getattr(self, "ref_area", getattr(self, "_reference_area", 0.01)))
        drag_force = self._cd * dynamic_pressure * ref_area
        lift_force = self._cl * dynamic_pressure * ref_area
        
        return {
            'drag': float(drag_force),
            'lift': float(lift_force),
            'cd': float(self._cd),
            'cl': float(self._cl),
            'cp_position': self._xcp.copy(),
            'stability_margin': float(self._stability_margin)
        }
    
    # -------------------------------------------------------------------------
    # Drag Coefficient Calculations
    # -------------------------------------------------------------------------
    
    def _calculate_drag_coefficient(self) -> float:
        """Calculate total drag coefficient using component-based model."""
        try:
            # Calculate individual drag components
            cd_skin_friction = self._calculate_skin_friction_drag()
            cd_pressure = self._calculate_pressure_drag()
            cd_base = self._calculate_base_drag()
            cd_interference = self._calculate_interference_drag()
            cd_wave = self._calculate_wave_drag()
            
            # Sum all components for total drag
            total_cd = cd_skin_friction + cd_pressure + cd_base + cd_interference + cd_wave
            
            # Apply transonic drag divergence correction
            total_cd *= self._transonic_drag_correction()
            
            logging.debug(f"Drag components - Skin: {cd_skin_friction:.4f}, Pressure: {cd_pressure:.4f}, "
                        f"Base: {cd_base:.4f}, Interference: {cd_interference:.4f}, Wave: {cd_wave:.4f}")
            
            return float(total_cd)
            
        except Exception as e:
            logging.error(f"Error in drag calculation: {str(e)}")
            return self._simple_drag_estimate()
    
    def _calculate_skin_friction_drag(self) -> float:
        """Calculate skin friction drag for all components using Prandtl-Schlichting."""
        # Calculate Reynolds number based on rocket length
        geometry = self.rocket_data.get('geometry', {})
        L_ref = geometry.get('total_length', geometry.get('total length', 1.0))  # [m]
        mu = _calculate_dynamic_viscosity(self.temp)
        
        Re_L = (self.rho * self.velocity * L_ref) / mu if self.velocity > 0 else 0.0
        
        # Turbulent skin friction coefficient
        Cf = TURBULENT_SKIN_FRICTION_K / (Re_L ** 0.2) if Re_L > 0 else 0.0
        
        # Calculate wetted areas
        A_wet_nose = self._calculate_nose_wetted_area()
        A_wet_body = self._calculate_body_wetted_area()
        A_wet_fins = self._calculate_fins_wetted_area()
        
        total_A_wet = A_wet_nose + A_wet_body + A_wet_fins
        
        # Surface roughness factor
        roughness_factor = self._get_surface_roughness_factor()
        
        # Compressibility correction
        compressibility_factor = 1.0
        if self.mach > 0.6:
            compressibility_factor = 1 / (1 + 0.12 * self.mach**2)
        
        cd_skin = Cf * roughness_factor * compressibility_factor * (total_A_wet / self.ref_area)
        return cd_skin
    
    def _calculate_pressure_drag(self) -> float:
        """Calculate pressure (form) drag for nose cone and fins."""
        cd_nose = self._calculate_nose_pressure_drag()
        cd_fins = self._calculate_fins_pressure_drag()
        return cd_nose + cd_fins
    
    def _calculate_nose_pressure_drag(self) -> float:
        """Calculate pressure drag for nose cone based on shape."""
        nose_data = self.rocket_data.get('nosecone', {})
        shape = nose_data.get('shape', nose_data.get('type', 'conical')).lower()
        fineness_ratio = nose_data.get('length', 0.1) / max(nose_data.get('diameter', 0.1), 0.001)
        
        if shape == 'parabolic':
            cd_nose = 0.08 / (fineness_ratio ** 0.5)
        elif shape == 'ogive' or shape == 'ogival':
            cd_nose = 0.06 / (fineness_ratio ** 0.5)
        else:  # conical
            cd_nose = 0.10 / (fineness_ratio ** 0.5)
        
        if self.mach > 0.8:
            cd_nose *= (1 + 0.2 * (self.mach - 0.8))
        
        # Scale by area ratio
        return cd_nose * (self.ref_area / self._calculate_nose_frontal_area())
    
    def _calculate_fins_pressure_drag(self) -> float:
        """Calculate pressure drag for fins."""
        fins_data = self.rocket_data.get('fins', {})
        thickness = 0.003  # [m] - typical fin thickness
        chord_avg = (fins_data.get('chord_root', 0.1) + fins_data.get('chord_tip', 0.05)) / 2
        if chord_avg <= 0:
            return 0.0
        thickness_ratio = thickness / chord_avg
        cd_fins_form = 2.0 * thickness_ratio * (self._calculate_fins_planform_area() / self.ref_area)
        return cd_fins_form
    
    def _calculate_base_drag(self) -> float:
        """Calculate base drag based on rear section geometry."""
        rear_data = self.rocket_data.get('rear_section', {})
        base_diameter = rear_data.get('diameter', self.ref_diameter)  # [m]
        base_area = math.pi * (base_diameter / 2) ** 2
        
        if self.mach < 0.8:
            cd_base = 0.12 + 0.13 * self.mach**2
        else:
            cd_base = 0.25 / (1 + 0.5 * (self.mach - 0.8))
        
        return cd_base * (base_area / self.ref_area)
    
    def _calculate_interference_drag(self) -> float:
        """Calculate interference drag at fin-body junctions."""
        fins_data = self.rocket_data.get('fins', {})
        K_int = 0.1
        fin_planform_area = self._calculate_fins_planform_area()
        cd_fins_basic = 0.05 * (fin_planform_area / self.ref_area)
        cd_interference = K_int * cd_fins_basic * fins_data.get('N_fins', 4)
        return cd_interference
    
    def _calculate_wave_drag(self) -> float:
        """Calculate wave drag for transonic/supersonic regimes."""
        if self.mach < 0.8:
            return 0.0
        if self.mach <= 1.2:
            return 0.2 * (self.mach - 0.8) ** 2
        else:
            return 0.4 / (self.mach ** 1.5)
    
    def _transonic_drag_correction(self) -> float:
        """Apply transonic drag divergence correction."""
        if self.mach < 0.8:
            return 1.0
        elif self.mach <= 1.2:
            return 1.0 + 0.5 * ((self.mach - 0.8) / 0.4) ** 2
        else:
            return 1.2
    
    def _get_surface_roughness_factor(self) -> float:
        """Return surface roughness multiplier (1.0 = smooth, >1.0 = rough)."""
        return 1.1
    
    def _simple_drag_estimate(self) -> float:
        """Fallback simple drag estimation when geometry data is incomplete."""
        base_cd = 0.3
        mach_factor = 1.0 + 0.2 * abs(self.mach - 0.8) if self.mach > 0.8 else 1.0
        alpha_factor = 1.0 + 0.1 * abs(self.alpha)
        return base_cd * mach_factor * alpha_factor
    
    # -------------------------------------------------------------------------
    # Lift Coefficient Calculations (Barrowman Method)
    # -------------------------------------------------------------------------
    
    def _calculate_lift_coefficient(self) -> float:
        """Calculate lift coefficient based on normal force using Barrowman method."""
        Cn_coeffs = self._calculate_normal_force_coefficients()
        Cn_alpha_total = sum(Cn_coeffs.values())
        Cn = Cn_alpha_total * np.radians(self.alpha)
        Cl = Cn * np.cos(np.radians(self.alpha))
        
        # Mach correction
        if self.mach < 0.8:
            Cl /= max(0.3, math.sqrt(1 - self.mach**2))
        elif self.mach > 1.2:
            Cl /= math.sqrt(self.mach**2 - 1)
        
        return Cl
    
    def _calculate_normal_force_coefficients(self) -> Dict[str, float]:
        """Calculate normal force coefficients for each component using Barrowman method."""
        g = self.rocket_data
        alpha_rad = np.radians(self.alpha)
        
        # Nose cone
        Cn_alpha_nose = 2.0
        
        # Body tube - negligible for slender bodies
        Cn_alpha_body = 0.0
        
        # Fins
        fins = g.get('fins', {})
        s = fins.get('span', 0.1)  # [m]
        d = self.ref_diameter
        cr = fins.get('chord_root', 0.1)  # [m]
        ct = fins.get('chord_tip', 0.05)  # [m]
        n = fins.get('N_fins', 4)
        
        # Avoid division by zero
        if s <= 0 or d <= 0:
            return {'nose': Cn_alpha_nose, 'body': Cn_alpha_body, 'fins': 0.0}
        
        K_fin = 1.0 + (d / (2 * s))
        AR = (2 * s) / (cr + ct) if (cr + ct) > 0 else 1.0
        Cn_alpha_fins = (K_fin * 4 * n * (s / d)**2) / (1 + math.sqrt(1 + (2 * AR)**2))
        
        return {'nose': Cn_alpha_nose, 'body': Cn_alpha_body, 'fins': Cn_alpha_fins}
    
    # -------------------------------------------------------------------------
    # Center of Pressure Calculations
    # -------------------------------------------------------------------------
    
    def _calculate_pressure_center(self) -> np.ndarray:
        """Calculate total center of pressure position using Barrowman method."""
        Cn_coeffs = self._calculate_normal_force_coefficients()
        cp_positions = self._calculate_pressure_centers()
        total_Cn_alpha = sum(Cn_coeffs.values())
        
        if total_Cn_alpha == 0:
            return np.array([0., 0., 0.])
        
        xcp = sum(Cn_coeffs[k] * cp_positions[k] for k in Cn_coeffs.keys()) / total_Cn_alpha
        return np.array([xcp, 0, 0])
    
    def _calculate_pressure_centers(self) -> Dict[str, float]:
        """Calculate center of pressure position for each component."""
        g = self.rocket_data
        
        # Get lengths from geometry
        nose_length = g.get('nosecone', {}).get('length', 0.1)  # [m]
        body_length = g.get('fuselage', {}).get('length', 0.5)  # [m]
        
        # Nose cone CP (from Barrowman)
        cp_nose = 0.466 * nose_length
        
        # Body tube CP
        cp_body = nose_length + 0.5 * body_length
        
        # Fins CP
        fins = g.get('fins', {})
        root_chord = fins.get('chord_root', 0.1)  # [m]
        mid_chord = fins.get('mid_chord', (root_chord + fins.get('chord_tip', 0.05)) / 2)  # [m]
        
        # Position where fins are attached
        fin_position = g.get('geometry', {}).get('length_nosecone_fins', nose_length + 0.1)  # [m]
        
        # Fin CP from leading edge
        if mid_chord > 0 and (root_chord + fins.get('chord_tip', 0.05)) > 0:
            ct = fins.get('chord_tip', 0.05)
            x_fin_cp = (mid_chord / 3) * ((root_chord + 2 * ct) / (root_chord + ct))
        else:
            x_fin_cp = 0.6 * root_chord
        
        cp_fins = fin_position + x_fin_cp
        
        return {'nose': cp_nose, 'body': cp_body, 'fins': cp_fins}
    
    # -------------------------------------------------------------------------
    # Stability Margin Calculation
    # -------------------------------------------------------------------------
    
    def _calculate_stability_margin(self) -> float:
        """Calculate static stability margin in calibers."""
        x_cp = self._xcp[0] if hasattr(self, '_xcp') else 0.0
        
        # Get center of gravity from mass properties
        com_before = self.mass_props.get('CoM_before_burn', {})
        com_after = self.mass_props.get('CoM_after_burn', {})
        
        x_cg_before = com_before.get('x', 0.0) if com_before else 0.0
        x_cg_after = com_after.get('x', 0.0) if com_after else 0.0
        
        # Average CoG position
        x_cg = (x_cg_before + x_cg_after) / 2
        
        # Calculate stability margin in calibers
        # Note: x_cp and x_cg should be in the same units (meters)
        if self.ref_diameter > 0:
            stability_calibers = (x_cp - x_cg) / self.ref_diameter
        else:
            stability_calibers = 0.0
        
        return stability_calibers
    
    # -------------------------------------------------------------------------
    # Geometry Helper Methods
    # -------------------------------------------------------------------------
    
    def _calculate_nose_wetted_area(self) -> float:
        """Calculate wetted area of nose cone."""
        nose = self.rocket_data.get('nosecone', {})
        L = nose.get('length', 0.1)  # [m]
        R = nose.get('diameter', 0.1) / 2  # [m] - radius
        return math.pi * R * math.sqrt(R**2 + L**2)
    
    def _calculate_body_wetted_area(self) -> float:
        """Calculate wetted area of body tube."""
        body = self.rocket_data.get('fuselage', {})
        L = body.get('length', 0.5)  # [m]
        D = body.get('diameter', 0.1)  # [m]
        return math.pi * D * L
    
    def _calculate_fins_wetted_area(self) -> float:
        """Calculate wetted area of fins (both sides)."""
        fins = self.rocket_data.get('fins', {})
        span = fins.get('span', 0.1)  # [m]
        root_chord = fins.get('chord_root', 0.1)  # [m]
        tip_chord = fins.get('chord_tip', 0.05)  # [m]
        area_one_side = 0.5 * (root_chord + tip_chord) * span
        return 2 * area_one_side * fins.get('N_fins', 4)
    
    def _calculate_fins_planform_area(self) -> float:
        """Calculate planform area of fins (one side only)."""
        fins = self.rocket_data.get('fins', {})
        span = fins.get('span', 0.1)  # [m]
        root_chord = fins.get('chord_root', 0.1)  # [m]
        tip_chord = fins.get('chord_tip', 0.05)  # [m]
        area_one_fin = 0.5 * (root_chord + tip_chord) * span
        return area_one_fin * fins.get('N_fins', 4)
    
    def _calculate_nose_frontal_area(self) -> float:
        """Calculate frontal area of nose cone."""
        nose = self.rocket_data.get('nosecone', {})
        D = nose.get('diameter', 0.1)  # [m]
        return math.pi * (D/2) ** 2


# =============================================================================
# Backward Compatibility
# =============================================================================

# Keep SimpleAerodynamics as an alias for backward compatibility
SimpleAerodynamics = Aerodynamics

# Legacy aliases
AerodynamicsClass = Aerodynamics


__all__ = [
    'Aerodynamics',
    'SimpleAerodynamics',
    'AerodynamicsClass',
    'MAX_ANGLE_OF_ATTACK',
    'SEA_LEVEL_DENSITY',
    'SEA_LEVEL_TEMPERATURE',
    'SPEED_OF_SOUND_SEA_LEVEL',
    'SUTHERLAND_C1',
    'SUTHERLAND_S',
    'TURBULENT_SKIN_FRICTION_K',
    '_validate_angle',
    '_calculate_dynamic_viscosity',
]
