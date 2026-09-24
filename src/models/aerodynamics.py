# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""
Aerodynamics Module

Unified aerodynamics module combining:
- EnhancedAerodynamics: Component-based drag modeling with Barrowman stability
- AerodynamicsWrapper: Robust wrapper with geometry validation

Both classes provide drag (Cd), lift (Cl), and center of pressure (xcp) calculations
for rocket flight simulations.

External dependencies:
    numpy - Numpy Python extension. http://numpy.org/
    scipy - Scipy Python extension. https://www.scipy.org
    fluids - For atmospheric properties (via Atmosphere class)

Changelog:
    Date          Name              Change
    15/08/2022    Jorge Orozco      Initial EnhancedAerodynamics release
    [Current]     Unified            Merged AerodynamicsWrapper into single module

References:
    [Barro67] Barrowman (1967) - The Practical Calculation of the Aerodynamic 
               Characteristic of Slender Finned Vehicles
"""

import numpy as np
import math
import logging

logger = logging.getLogger(__name__)

# Constants for both classes
MAX_ANGLE_OF_ATTACK = 10.0  # Maximum angle of attack in degrees [deg]
SUTHERLAND_C1 = 1.458e-6  # Sutherland's constant for air [kg/(m·s·K^0.5)]
SUTHERLAND_S = 110.4  # Sutherland's temperature constant for air [K]
SPEED_OF_SOUND_SEA_LEVEL = 340.0  # Approximate speed of sound at sea level [m/s]


# =============================================================================
# Shared Helper Functions
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
# EnhancedAerodynamics Class
# =============================================================================

class EnhancedAerodynamics:
    """
    Enhanced aerodynamics module with component-based drag modeling
    and Barrowman stability calculations.
    
    This class provides comprehensive aerodynamic coefficient calculations
    for rocket flight simulations, including:
    - Component-based drag (skin friction, pressure, base, interference, wave)
    - Lift coefficient calculations
    - Center of pressure and stability margin
    
    Attributes:
        mach: Mach number [-]
        alpha: Angle of attack [deg]
        height: Altitude [m]
        cd: Drag coefficient [-]
        cl: Lift coefficient [-]
        xcp: Center of pressure position [m]
        stability_margin: Stability margin [calibers]
    """
    
    def __init__(
        self,
        mach: float,
        angle_attack: float,
        height: float,
        atmosphere: any,
        rocket_data: dict,
        current_mass_props: dict
    ) -> None:
        """
        Initialize aerodynamics calculations.
        
        Args:
            mach: Mach number [-]
            angle_attack: Angle of attack [deg]
            height: Altitude [m]
            atmosphere: Atmosphere object with give_dens, give_temp, give_v_sonic methods
            rocket_data: Dictionary containing rocket configuration
            current_mass_props: Dictionary containing mass properties
            
        Raises:
            KeyError: If required rocket_data keys are missing
            ValueError: If input values are invalid
        """
        logging.debug(f"Initializing aerodynamics: Mach={mach:.2f}, α={angle_attack:.1f}°, h={height:.1f}m")
        
        try:
            # Validate inputs
            if mach < 0:
                raise ValueError(f"Mach number must be non-negative, got {mach}")
            if height < 0:
                raise ValueError(f"Height must be non-negative, got {height}")
            
            self.mach = float(mach)
            self.alpha = _validate_angle(angle_attack)
            self.height = float(height)
            self.atmosphere = atmosphere
            self.rocket_data = rocket_data
            self.mass_props = current_mass_props
            
            # Atmospheric properties
            self.rho = atmosphere.give_dens(height)  # [kg/m³]
            self.temp = atmosphere.give_temp(height)  # [K]
            self.speed_of_sound = atmosphere.give_v_sonic(height)  # [m/s]
            self.velocity = mach * self.speed_of_sound  # [m/s]
            
            # Reference parameters
            self.ref_area = rocket_data['reference_area']  # [m²]
            self.ref_diameter = rocket_data['fuselage']['diameter'] / 1000.0  # [m]
            
            # Calculate coefficients
            self.cd = self._calculate_drag_coefficient()
            self.cl = self._calculate_lift_coefficient()
            self.xcp = self._calculate_pressure_center()
            self.stability_margin = self._calculate_stability_margin()
            
            logging.debug(f"Coefficients calculated: CD={self.cd:.3f}, CL={self.cl:.3f}, Stability={self.stability_margin:.2f} calibers")
            
        except KeyError as e:
            logging.error(f"Missing required rocket_data key: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Error in aerodynamics: {str(e)}")
            raise

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

    def _calculate_skin_friction_drag(self):
        """Calculate skin friction drag for all components using Prandtl-Schlichting"""
        # Calculate Reynolds number based on rocket length
        L_ref = self.rocket_data['geometry']['total length'] / 1000.0  # [m]
        mu = _calculate_dynamic_viscosity(self.temp)
        
        Re_L = (self.rho * self.velocity * L_ref) / mu
        
        # Turbulent skin friction coefficient
        Cf = 0.074 / (Re_L ** 0.2)
        
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

    def _calculate_pressure_drag(self):
        """Calculate pressure (form) drag for nose cone and fins"""
        cd_nose = self._calculate_nose_pressure_drag()
        cd_fins = self._calculate_fins_pressure_drag()
        return cd_nose + cd_fins

    def _calculate_nose_pressure_drag(self):
        """Calculate pressure drag for nose cone based on shape"""
        nose_data = self.rocket_data['nosecone']
        shape = nose_data.get('shape', 'conical')
        fineness_ratio = nose_data['length'] / nose_data['diameter']
        
        if shape == 'parabolic':
            cd_nose = 0.08 / (fineness_ratio ** 0.5)
        elif shape == 'ogive':
            cd_nose = 0.06 / (fineness_ratio ** 0.5)
        else:  # conical
            cd_nose = 0.10 / (fineness_ratio ** 0.5)
        
        if self.mach > 0.8:
            cd_nose *= (1 + 0.2 * (self.mach - 0.8))
        
        return cd_nose * (self.ref_area / self._calculate_nose_frontal_area())

    def _calculate_fins_pressure_drag(self):
        """Calculate pressure drag for fins"""
        fins_data = self.rocket_data['fins']
        thickness = 3.0  # [mm]
        chord_avg = (fins_data['chord_root'] + fins_data['chord_tip']) / 2
        thickness_ratio = thickness / chord_avg
        cd_fins_form = 2.0 * thickness_ratio * (self._calculate_fins_planform_area() / self.ref_area)
        return cd_fins_form

    def _calculate_base_drag(self):
        """Calculate base drag based on rear section geometry"""
        rear_data = self.rocket_data['rear_section']
        base_diameter = rear_data['diameter'] / 1000.0
        base_area = math.pi * (base_diameter / 2) ** 2
        
        if self.mach < 0.8:
            cd_base = 0.12 + 0.13 * self.mach**2
        else:
            cd_base = 0.25 / (1 + 0.5 * (self.mach - 0.8))
        
        return cd_base * (base_area / self.ref_area)

    def _calculate_interference_drag(self):
        """Calculate interference drag at fin-body junctions"""
        fins_data = self.rocket_data['fins']
        K_int = 0.1
        fin_planform_area = self._calculate_fins_planform_area()
        cd_fins_basic = 0.05 * (fin_planform_area / self.ref_area)
        cd_interference = K_int * cd_fins_basic * fins_data['N_fins']
        return cd_interference

    def _calculate_wave_drag(self):
        """Calculate wave drag for transonic/supersonic regimes"""
        if self.mach < 0.8:
            return 0.0
        if self.mach <= 1.2:
            return 0.2 * (self.mach - 0.8) ** 2
        else:
            return 0.4 / (self.mach ** 1.5)

    def _transonic_drag_correction(self):
        """Apply transonic drag divergence correction"""
        if self.mach < 0.8:
            return 1.0
        elif self.mach <= 1.2:
            return 1.0 + 0.5 * ((self.mach - 0.8) / 0.4) ** 2
        else:
            return 1.2

    def _get_surface_roughness_factor(self):
        """Return surface roughness multiplier (1.0 = smooth, >1.0 = rough)"""
        return 1.1

    def _calculate_nose_wetted_area(self):
        """Calculate wetted area of nose cone"""
        nose = self.rocket_data['nosecone']
        L = nose['length'] / 1000.0
        R = nose['diameter'] / 2000.0
        return math.pi * R * math.sqrt(R**2 + L**2)

    def _calculate_body_wetted_area(self):
        """Calculate wetted area of body tube"""
        body = self.rocket_data['fuselage']
        L = body['length'] / 1000.0
        D = body['diameter'] / 1000.0
        return math.pi * D * L

    def _calculate_fins_wetted_area(self):
        """Calculate wetted area of fins (both sides)"""
        fins = self.rocket_data['fins']
        span = fins['span'] / 1000.0
        root_chord = fins['chord_root'] / 1000.0
        tip_chord = fins['chord_tip'] / 1000.0
        area_one_side = 0.5 * (root_chord + tip_chord) * span
        return 2 * area_one_side * fins['N_fins']

    def _calculate_fins_planform_area(self):
        """Calculate planform area of fins (one side only)"""
        fins = self.rocket_data['fins']
        span = fins['span'] / 1000.0
        root_chord = fins['chord_root'] / 1000.0
        tip_chord = fins['chord_tip'] / 1000.0
        area_one_fin = 0.5 * (root_chord + tip_chord) * span
        return area_one_fin * fins['N_fins']

    def _calculate_nose_frontal_area(self):
        """Calculate frontal area of nose cone"""
        nose = self.rocket_data['nosecone']
        D = nose['diameter'] / 1000.0
        return math.pi * (D/2) ** 2

    def _simple_drag_estimate(self):
        """Fallback simple drag estimation"""
        base_cd = 0.3
        mach_factor = 1.0 + 0.2 * abs(self.mach - 0.8) if self.mach > 0.8 else 1.0
        alpha_factor = 1.0 + 0.1 * abs(self.alpha)
        return base_cd * mach_factor * alpha_factor

    def _calculate_normal_force_coefficients(self):
        """Calculate normal force coefficients for each component using Barrowman"""
        g = self.rocket_data
        alpha_rad = np.radians(self.alpha)
        
        # Nose cone
        Cn_alpha_nose = 2.0
        
        # Body tube - negligible for slender bodies
        Cn_alpha_body = 0.0
        
        # Fins
        fins = g['fins']
        s = fins['span'] / 1000.0
        d = self.ref_diameter
        cr = fins['chord_root'] / 1000.0
        ct = fins['chord_tip'] / 1000.0
        n = fins['N_fins']
        
        K_fin = 1.0 + (d / (2 * s))
        AR = (2 * s) / (cr + ct)
        Cn_alpha_fins = (K_fin * 4 * n * (s / d)**2) / (1 + math.sqrt(1 + (2 * AR)**2))
        
        return {'nose': Cn_alpha_nose, 'body': Cn_alpha_body, 'fins': Cn_alpha_fins}

    def _calculate_pressure_centers(self):
        """Calculate center of pressure position for each component"""
        g = self.rocket_data
        nose_length = g['nosecone']['length'] / 1000.0
        body_length = g['fuselage']['length'] / 1000.0
        
        # Nose cone CP
        cp_nose = 0.466 * nose_length
        
        # Body tube CP
        cp_body = nose_length + 0.5 * body_length
        
        # Fins CP
        fins = g['fins']
        root_chord = fins['chord_root'] / 1000.0
        mid_chord = fins['mid_chord'] / 1000.0
        x_fin_cp = (mid_chord / 3) * ((root_chord + 2 * ct) / (root_chord + ct)) if 'ct' in dir() else 0.6 * root_chord
        fin_position = g['geometry'].get('length_nosecone_fins', g['geometry'].get('length nosecone fins', 0)) / 1000.0
        cp_fins = fin_position + x_fin_cp
        
        return {'nose': cp_nose, 'body': cp_body, 'fins': cp_fins}

    def _calculate_lift_coefficient(self):
        """Calculate lift coefficient based on normal force"""
        Cn_coeffs = self._calculate_normal_force_coefficients()
        Cn_alpha_total = sum(Cn_coeffs.values())
        Cn = Cn_alpha_total * np.radians(self.alpha)
        Cl = Cn * np.cos(np.radians(self.alpha))
        
        # Mach correction
        if self.mach < 0.8:
            Cl /= math.sqrt(1 - self.mach**2)
        elif self.mach > 1.2:
            Cl /= math.sqrt(self.mach**2 - 1)
        
        return Cl

    def _calculate_pressure_center(self):
        """Calculate total center of pressure position"""
        Cn_coeffs = self._calculate_normal_force_coefficients()
        cp_positions = self._calculate_pressure_centers()
        total_Cn_alpha = sum(Cn_coeffs.values())
        
        if total_Cn_alpha == 0:
            return np.array([0., 0., 0.])
        
        xcp = sum(Cn_coeffs[k] * cp_positions[k] for k in Cn_coeffs.keys()) / total_Cn_alpha
        return np.array([xcp, 0, 0])

    def _calculate_stability_margin(self):
        """Calculate static stability margin in calibers"""
        x_cp = self.xcp[0]
        x_cg_before = self.mass_props['CoM_before_burn']['x']
        x_cg_after = self.mass_props['CoM_after_burn']['x']
        x_cg = (x_cg_before + x_cg_after) / 2
        stability_calibers = (x_cp - x_cg) / self.ref_diameter
        return stability_calibers

    def get_aerodynamic_forces(self, dynamic_pressure: float) -> dict:
        """Return aerodynamic forces in rocket frame.
        
        Args:
            dynamic_pressure: Dynamic pressure [Pa]
        
        Returns:
            Dictionary with drag, lift, coefficients, and stability info
        """
        drag_force = self.cd * dynamic_pressure * self.ref_area
        lift_force = self.cl * dynamic_pressure * self.ref_area
        
        return {
            'drag': float(drag_force),
            'lift': float(lift_force),
            'cd': float(self.cd),
            'cl': float(self.cl),
            'cp_position': self.xcp,
            'stability_margin': float(self.stability_margin)
        }


# =============================================================================
# AerodynamicsWrapper Class (Compatibility Layer)
# =============================================================================

class AerodynamicsWrapper:
    """
    Robust aerodynamics wrapper with comprehensive error handling.
    
    This class provides a simpler interface for aerodynamics calculations,
    with geometry validation and fallback values. It uses similar calculation
    methods to EnhancedAerodynamics but with a different parameter structure.
    
    For new code, prefer using EnhancedAerodynamics directly.
    
    Attributes:
        mach: Mach number [-]
        alpha: Angle of attack [deg]
        geometry: Geometry dictionary
        height: Altitude [m]
        density: Air density [kg/m³]
        temperature: Air temperature [K]
        cd: Drag coefficient [-]
        cl: Lift coefficient [-]
        xcp: Center of pressure position [m]
    """
    
    def __init__(self, mach, angle_attack, geometry, height=0, density=1.225, temperature=288.15):
        """
        Initialize aerodynamics wrapper with comprehensive error handling.
        
        Args:
            mach: Mach number
            angle_attack: Angle of attack [deg]
            geometry: Dictionary with rocket geometry parameters
            height: Altitude [m] (default: 0)
            density: Air density [kg/m³] (default: 1.225)
            temperature: Air temperature [K] (default: 288.15)
        """
        self.mach = max(0.0, min(mach, 5.0))
        self.alpha = _validate_angle(angle_attack)
        self.geometry = self._validate_geometry(geometry)
        self.height = height
        self.density = density
        self.temperature = temperature
        self.v_norm = self.mach * SPEED_OF_SOUND_SEA_LEVEL
        
        # Calculate coefficients with error handling
        try:
            self.cd = self._calculate_drag_coefficient()
            self.cl = self._calculate_lift_coefficient()
            self.xcp = self._calculate_pressure_center()
        except Exception as e:
            logging.warning(f"Aerodynamics calculation failed, using defaults: {e}")
            self.cd = 0.5
            self.cl = 0.0
            self.xcp = np.array([0.5, 0, 0])

    def _validate_geometry(self, geometry):
        """Validate geometry dictionary and provide defaults for missing keys."""
        required_keys = {
            'len_warhead': 200.0,
            'diameter_warhead_base': 103.0,
            'len_nosecone_fins': 1000.0,
            'len_nosecone_rear': 1199.47,
            'len_bodytube_wo_rear': 930.0,
            'diameter_bodytube': 103.0,
            'len_rear': 69.334,
            'end_diam_rear': 71.7,
            'diameter_rear_bodytube': 71.7,
            'diameter_bodytube_fins': 103.0,
            'fins_chord_root': 130.0,
            'fins_chord_tip': 43.92,
            'fins_mid_chord': 86.96,
            'fins_span': 139.119,
            'N_fins': 4
        }
        
        validated_geometry = geometry.copy()
        for key, default_value in required_keys.items():
            if key not in validated_geometry:
                logging.warning(f"Missing geometry parameter '{key}', using default: {default_value}")
                validated_geometry[key] = default_value
            elif validated_geometry[key] <= 0:
                logging.warning(f"Invalid geometry parameter '{key}': {validated_geometry[key]}, using default: {default_value}")
                validated_geometry[key] = default_value
        
        return validated_geometry

    def _calculate_drag_coefficient(self):
        """Robust drag coefficient calculation with component breakdown."""
        try:
            ref_diameter = self.geometry['diameter_bodytube'] / 1000.0
            ref_area = np.pi * (ref_diameter/2)**2
            
            if ref_area <= 0:
                return 0.5
            
            skin_friction = self._calculate_skin_friction()
            pressure_drag = self._calculate_pressure_drag()
            fin_drag = self._calculate_fin_drag()
            base_drag = self._calculate_base_drag()
            
            total_cd = skin_friction + pressure_drag + fin_drag + base_drag
            
            mach_factor = self._mach_correction()
            alpha_factor = self._alpha_correction()
            
            total_cd *= mach_factor * alpha_factor
            return max(0.1, min(2.0, total_cd))
        except Exception as e:
            logging.error(f"Drag calculation error: {e}")
            return 0.5

    def _calculate_skin_friction(self):
        """Calculate skin friction drag with proper Reynolds number."""
        try:
            L = self.geometry['len_nosecone_rear'] / 1000.0
            diameter = self.geometry['diameter_bodytube'] / 1000.0
            
            if L <= 0 or self.v_norm <= 0:
                return 0.01
            
            mu = 1.789e-5
            Re = (self.density * self.v_norm * L) / mu
            Cf = 0.074 / (Re ** 0.2) if Re > 0 else 0.0
            wetted_area = np.pi * diameter * L
            ref_area = np.pi * (diameter/2)**2
            
            if ref_area > 0:
                skin_friction_cd = Cf * (wetted_area / ref_area)
            else:
                skin_friction_cd = 0.01
            
            return max(0.001, min(0.1, skin_friction_cd))
        except Exception as e:
            logging.error(f"Skin friction calculation error: {e}")
            return 0.01

    def _calculate_fin_parameters(self):
        """Calculate fin parameters based on fin type."""
        try:
            g = self.geometry
            fin_type = g.get('fin_type', 'Trapezoidal')
            span = g['fins_span'] / 1000.0
            root_chord = g['fins_chord_root'] / 1000.0
            tip_chord = g['fins_chord_tip'] / 1000.0
            n_fins = g['N_fins']
            
            if fin_type == "Trapezoidal":
                fin_area = 0.5 * (root_chord + tip_chord) * span
                aspect_ratio = (span ** 2) / fin_area
                mean_chord = (root_chord + tip_chord) / 2
            elif fin_type == "Delta":
                fin_area = 0.5 * root_chord * span
                aspect_ratio = (span ** 2) / fin_area
                mean_chord = root_chord * 2/3
            elif fin_type == "Tapered Swept":
                fin_area = 0.5 * (root_chord + tip_chord) * span
                aspect_ratio = (span ** 2) / fin_area
                sweep_angle = g.get('sweep_angle', 30.0)
                mean_chord = (root_chord + tip_chord) / 2
            elif fin_type == "Elliptical":
                fin_area = (np.pi * root_chord * span) / 4
                aspect_ratio = (span ** 2) / fin_area
                mean_chord = root_chord * 0.848
            else:
                fin_area = 0.5 * (root_chord + tip_chord) * span
                aspect_ratio = (span ** 2) / fin_area
                mean_chord = g.get('fins_mid_chord', (root_chord + tip_chord) / 2) / 1000.0
            
            return {
                'fin_area': fin_area,
                'total_fin_area': fin_area * n_fins,
                'aspect_ratio': aspect_ratio,
                'mean_chord': mean_chord,
                'fin_type': fin_type
            }
        except Exception as e:
            logging.warning(f"Fin parameter calculation issue: {e}")
            return {
                'fin_area': 0.01,
                'total_fin_area': 0.01 * g.get('N_fins', 4),
                'aspect_ratio': 5.0,
                'mean_chord': 0.05,
                'fin_type': 'Trapezoidal'
            }

    def _calculate_fin_drag(self):
        """Calculate drag contribution from fins."""
        try:
            fin_params = self._calculate_fin_parameters()
            ref_diameter = self.geometry['diameter_bodytube'] / 1000.0
            ref_area = np.pi * (ref_diameter/2)**2
            
            if ref_area <= 0:
                return 0.02
            
            fin_drag_area_ratio = fin_params['total_fin_area'] / ref_area
            base_cd_fin = {
                "Trapezoidal": 0.008,
                "Delta": 0.006,
                "Tapered Swept": 0.007,
                "Elliptical": 0.005,
                "Custom": 0.008
            }.get(fin_params['fin_type'], 0.008)
            
            ar = fin_params['aspect_ratio']
            ar_correction = 1.0 / np.sqrt(1.0 + ar)
            mach_correction = self._fin_mach_correction()
            interference_factor = 1.1
            
            total_fin_cd = base_cd_fin * fin_drag_area_ratio * ar_correction * mach_correction * interference_factor
            return max(0.001, min(0.1, total_fin_cd))
        except Exception as e:
            logging.warning(f"Fin drag calculation issue: {e}")
            return 0.02

    def _fin_mach_correction(self):
        """Mach correction specific to fin drag."""
        if self.mach < 0.8:
            return 1.0
        elif self.mach <= 1.2:
            return 1.0 + 0.5 * ((self.mach - 0.8) / 0.4)
        else:
            return 1.2

    def _calculate_base_drag(self):
        """Calculate base drag component."""
        if self.mach < 0.8:
            return 0.12 + 0.1 * self.mach
        else:
            return 0.08

    def _mach_correction(self):
        """Apply Mach number correction to drag."""
        if self.mach < 0.8:
            return 1.0
        elif self.mach <= 1.0:
            return 1.0 + 1.2 * ((self.mach - 0.8) / 0.2)
        elif self.mach <= 1.2:
            return 2.2 - 0.5 * ((self.mach - 1.0) / 0.2)
        else:
            return 1.7 / (1.0 + 0.2 * self.mach)

    def _alpha_correction(self):
        """Apply angle of attack correction."""
        alpha_rad = np.radians(abs(self.alpha))
        return 1.0 + 0.5 * alpha_rad**2

    def _calculate_lift_coefficient(self):
        """Enhanced lift coefficient calculation."""
        if abs(self.alpha) < 0.1:
            return 0.0
        
        try:
            alpha_rad = np.radians(self.alpha)
            fin_params = self._calculate_fin_parameters()
            
            fin_cl_alpha = (2 * np.pi * fin_params['aspect_ratio']) / (
                2 + np.sqrt(4 + (fin_params['aspect_ratio'] * 0.95)**2 * (1 + np.tan(0)**2))
            )
            
            n_fins = self.geometry['N_fins']
            fin_effectiveness = min(1.0, n_fins / 4.0)
            cl_fins = fin_cl_alpha * alpha_rad * fin_effectiveness
            cl_body = 0.1 * alpha_rad
            total_cl = cl_fins + cl_body
            
            if self.mach < 0.8:
                total_cl /= max(0.3, math.sqrt(1 - self.mach**2))
            elif self.mach > 1.2:
                total_cl /= math.sqrt(self.mach**2 - 1)
            
            return total_cl
        except Exception as e:
            logging.error(f"Lift calculation error: {e}")
            return 0.0

    def _calculate_pressure_drag(self):
        """Enhanced pressure drag calculation with nosecone type consideration."""
        try:
            nosecone_drag = self._calculate_nosecone_drag()
            body_drag = self._calculate_body_pressure_drag()
            return nosecone_drag + body_drag
        except Exception as e:
            logging.error(f"Pressure drag calculation error: {e}")
            return 0.3

    def _calculate_nosecone_drag(self):
        """Calculate nosecone drag coefficient based on nosecone type."""
        try:
            g = self.geometry
            nosecone_type = g.get('nosecone_type', 'Conical')
            length = g['len_warhead'] / 1000.0
            base_diameter = g['diameter_warhead_base'] / 1000.0
            
            if base_diameter <= 0 or length <= 0:
                return 0.1
            
            fineness_ratio = length / base_diameter
            
            base_drag_coefficients = {
                "Conical": 0.50,
                "Ogival": 0.40,
                "Elliptical": 0.30,
                "Parabolic": 0.35,
                "Power Series": 0.38,
                "Von Karman": 0.28,
                "Haack Series": 0.25
            }
            
            cd_base = base_drag_coefficients.get(nosecone_type, 0.40)
            
            if fineness_ratio > 5:
                fineness_factor = 0.7
            elif fineness_ratio > 3:
                fineness_factor = 0.8
            elif fineness_ratio > 2:
                fineness_factor = 0.9
            else:
                fineness_factor = 1.0
            
            type_factor = 1.0
            if nosecone_type == "Ogival":
                ogive_radius = g.get('ogive_radius', base_diameter * 2) / 1000.0
                if ogive_radius > base_diameter * 1.5:
                    type_factor = 0.9
                else:
                    type_factor = 1.0
            elif nosecone_type == "Elliptical":
                type_factor = 0.85
            elif nosecone_type == "Parabolic":
                type_factor = 0.95
            elif nosecone_type == "Von Karman":
                type_factor = 0.8
            elif nosecone_type == "Haack Series":
                type_factor = 0.85
            
            mach_factor = self._nosecone_mach_correction()
            cd_nose = cd_base * fineness_factor * type_factor * mach_factor
            return max(0.1, min(1.0, cd_nose))
        except Exception as e:
            logging.error(f"Nosecone drag calculation error: {e}")
            return 0.4

    def _nosecone_mach_correction(self):
        """Apply Mach number correction specific to nosecone drag."""
        if self.mach < 0.8:
            return 1.0
        elif self.mach <= 1.2:
            return 1.0 + 1.5 * ((self.mach - 0.8) / 0.4) ** 2
        else:
            return 1.2 / (1.0 + 0.15 * self.mach)

    def _calculate_body_pressure_drag(self):
        """Calculate pressure drag from the rocket body tube."""
        try:
            g = self.geometry
            body_length = g['len_bodytube_wo_rear'] / 1000.0
            diameter = g['diameter_bodytube'] / 1000.0
            
            if body_length <= 0 or diameter <= 0:
                return 0.05
            
            l_d_ratio = body_length / diameter
            base_body_cd = 0.08
            
            if l_d_ratio > 20:
                length_factor = 1.3
            elif l_d_ratio > 10:
                length_factor = 1.1
            elif l_d_ratio > 5:
                length_factor = 1.0
            else:
                length_factor = 0.9
            
            if self.mach < 0.8:
                mach_factor = 1.0
            elif self.mach <= 1.2:
                mach_factor = 1.0 + 0.5 * ((self.mach - 0.8) / 0.4)
            else:
                mach_factor = 1.1
            
            return base_body_cd * length_factor * mach_factor
        except Exception as e:
            logging.error(f"Body pressure drag calculation error: {e}")
            return 0.05

    def _calculate_pressure_center(self):
        """Calculate center of pressure with nosecone consideration."""
        try:
            g = self.geometry
            nose_length = g['len_warhead'] / 1000.0
            body_length = g['len_bodytube_wo_rear'] / 1000.0
            fin_position = g['len_nosecone_fins'] / 1000.0
            
            cp_nose = self._calculate_center_of_pressure_nosecone()
            cp_body = nose_length + 0.5 * body_length
            root_chord = g['fins_chord_root'] / 1000.0
            x_fin_cp = fin_position + 0.6 * root_chord
            
            ref_diameter = g['diameter_bodytube'] / 1000.0
            ref_area = np.pi * (ref_diameter/2)**2
            
            nosecone_weight = 0.15
            body_weight = 0.10
            fins_weight = 0.75
            
            xcp_total = (nosecone_weight * cp_nose +
                        body_weight * cp_body +
                        fins_weight * x_fin_cp)
            
            return np.array([xcp_total, 0, 0])
        except Exception as e:
            logging.error(f"CP calculation error: {e}")
            total_length = g.get('len_nosecone_rear', 1199.47) / 1000.0
            return np.array([total_length * 0.5, 0, 0])

    def _calculate_center_of_pressure_nosecone(self):
        """Calculate nosecone contribution to center of pressure."""
        try:
            g = self.geometry
            nosecone_type = g.get('nosecone_type', 'Conical')
            nose_length = g['len_warhead'] / 1000.0
            
            if nosecone_type == "Conical":
                cp_fraction = 0.666
            elif nosecone_type == "Ogival":
                cp_fraction = 0.466
            elif nosecone_type == "Elliptical":
                cp_fraction = 0.500
            elif nosecone_type == "Parabolic":
                cp_fraction = 0.500 + 0.1 * g.get('parabolic_parameter', 0.5)
            elif nosecone_type == "Power Series":
                cp_fraction = 0.466 + 0.1 * g.get('power_value', 0.5)
            elif nosecone_type == "Von Karman":
                cp_fraction = 0.450
            elif nosecone_type == "Haack Series":
                cp_fraction = 0.455
            else:
                cp_fraction = 0.500
            
            return cp_fraction * nose_length
        except Exception as e:
            logging.error(f"Nosecone CP calculation error: {e}")
            return 0.0
