# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""
*** EnhancedAerodynamics.py ***

Enhanced aerodynamics module with component-based drag modeling
and Barrowman stability calculations.

External dependencies:
numpy       -Numpy Python extension. http://numpy.org/
scipy       -Scipy Python extension. https://www.scipy.org
fluids      -For atmospheric properties (via Atmosphere class)

Changelog:
Date          Name              Change
15/08/2022    Jorge Orozco      Initial release
[Current]     Enhanced          Component-based drag model & Barrowman method
"""

import numpy as np
import math
from scipy import interpolate
import logging

class EnhancedAerodynamics:
    def __init__(self, mach, angle_attack, height, atmosphere, rocket_data, current_mass_props):
        logging.debug(f"Inicializando cálculos aerodinámicos: Mach={mach:.2f}, α={angle_attack:.1f}°, h={height:.1f}m")
        try:
            self.mach = mach
            self.alpha = self._validate_angle(angle_attack)
            self.height = height
            self.atmosphere = atmosphere
            self.rocket_data = rocket_data
            self.mass_props = current_mass_props
            
            # Atmospheric properties
            self.rho = atmosphere.give_dens(height)
            self.temp = atmosphere.give_temp(height)
            self.speed_of_sound = atmosphere.give_v_sonic(height)
            self.velocity = mach * self.speed_of_sound
            
            # Reference parameters
            self.ref_area = rocket_data['reference_area']  # [m²]
            self.ref_diameter = rocket_data['fuselage']['diameter'] / 1000.0  # [m]
            
            # Calculate coefficients
            self.cd = self._calculate_drag_coefficient()
            self.cl = self._calculate_lift_coefficient()
            self.xcp = self._calculate_pressure_center()
            self.stability_margin = self._calculate_stability_margin()
            
            logging.debug(f"Coeficientes calculados: CD={self.cd:.3f}, CL={self.cl:.3f}, Stability={self.stability_margin:.2f} calibers")
            
        except Exception as e:
            logging.error(f"Error en cálculos aerodinámicos: {str(e)}")
            raise

    def _validate_angle(self, angle):
        """Valida y ajusta el ángulo de ataque"""
        a_max = 10  # [deg]
        if abs(angle) >= a_max:
            return a_max * (abs(angle)/angle)
        return angle

    def _calculate_drag_coefficient(self):
        """Calculates total drag coefficient using component-based model"""
        try:
            # Calculate individual drag components
            cd_skin_friction = self._calculate_skin_friction_drag()
            cd_pressure = self._calculate_pressure_drag()
            cd_base = self._calculate_base_drag()
            cd_interference = self._calculate_interference_drag()
            cd_wave = self._calculate_wave_drag()  # For transonic/supersonic
            
            # Sum all components for total drag
            total_cd = cd_skin_friction + cd_pressure + cd_base + cd_interference + cd_wave
            
            # Apply transonic drag divergence correction
            total_cd *= self._transonic_drag_correction()
            
            logging.debug(f"Drag components - Skin: {cd_skin_friction:.4f}, Pressure: {cd_pressure:.4f}, "
                         f"Base: {cd_base:.4f}, Interference: {cd_interference:.4f}, Wave: {cd_wave:.4f}")
            
            return total_cd
            
        except Exception as e:
            logging.error(f"Error in drag calculation: {str(e)}")
            # Fallback to simple model
            return self._simple_drag_estimate()

    def _calculate_skin_friction_drag(self):
        """Calculates skin friction drag for all components using Prandtl-Schlichting"""
        # Calculate Reynolds number based on rocket length
        L_ref = self.rocket_data['geometry']['total length'] / 1000.0  # [m]
        mu = self._calculate_dynamic_viscosity()  # Dynamic viscosity
        
        Re_L = (self.rho * self.velocity * L_ref) / mu
        
        # Turbulent skin friction coefficient (Prandtl-Schlichting)
        Cf = 0.074 / (Re_L ** 0.2)
        
        # Calculate wetted areas
        A_wet_nose = self._calculate_nose_wetted_area()
        A_wet_body = self._calculate_body_wetted_area()
        A_wet_fins = self._calculate_fins_wetted_area()
        
        total_A_wet = A_wet_nose + A_wet_body + A_wet_fins
        
        # Surface roughness factor (1.0 for smooth, up to 1.5 for rough)
        roughness_factor = self._get_surface_roughness_factor()
        
        # Compressibility correction
        compressibility_factor = 1.0
        if self.mach > 0.6:
            compressibility_factor = 1 / (1 + 0.12 * self.mach**2)
        
        cd_skin = Cf * roughness_factor * compressibility_factor * (total_A_wet / self.ref_area)
        
        return cd_skin

    def _calculate_pressure_drag(self):
        """Calculates pressure (form) drag for nose cone and fins"""
        cd_nose = self._calculate_nose_pressure_drag()
        cd_fins = self._calculate_fins_pressure_drag()
        
        return cd_nose + cd_fins

    def _calculate_nose_pressure_drag(self):
        """Calculates pressure drag for nose cone based on shape"""
        nose_data = self.rocket_data['nosecone']
        shape = nose_data.get('shape', 'conical')
        fineness_ratio = nose_data['length'] / nose_data['diameter']
        
        # Base drag coefficients for different nose shapes (subsonic)
        if shape == 'parabolic':
            cd_nose = 0.08 / (fineness_ratio ** 0.5)
        elif shape == 'ogive':
            cd_nose = 0.06 / (fineness_ratio ** 0.5)
        else:  # conical
            cd_nose = 0.10 / (fineness_ratio ** 0.5)
        
        # Mach number correction
        if self.mach > 0.8:
            cd_nose *= (1 + 0.2 * (self.mach - 0.8))
        
        return cd_nose * (self.ref_area / self._calculate_nose_frontal_area())

    def _calculate_fins_pressure_drag(self):
        """Calculates pressure drag for fins"""
        fins_data = self.rocket_data['fins']
        
        # Fin thickness ratio (assuming 3mm thickness if not specified)
        thickness = 3.0  # [mm]
        chord_avg = (fins_data['chord_root'] + fins_data['chord_tip']) / 2
        thickness_ratio = thickness / chord_avg
        
        # Form drag coefficient for fins
        cd_fins_form = 2.0 * thickness_ratio * (self._calculate_fins_planform_area() / self.ref_area)
        
        return cd_fins_form

    def _calculate_base_drag(self):
        """Calculates base drag based on rear section geometry"""
        rear_data = self.rocket_data['rear_section']
        
        # Base area
        base_diameter = rear_data['diameter'] / 1000.0  # [m]
        base_area = math.pi * (base_diameter / 2) ** 2
        
        # Base drag coefficient (empirical)
        if self.mach < 0.8:
            cd_base = 0.12 + 0.13 * self.mach**2
        else:
            cd_base = 0.25 / (1 + 0.5 * (self.mach - 0.8))
        
        return cd_base * (base_area / self.ref_area)

    def _calculate_interference_drag(self):
        """Calculates interference drag at fin-body junctions"""
        fins_data = self.rocket_data['fins']
        
        # Interference drag factor (empirical)
        K_int = 0.1  # 10% of fin drag
        
        # Estimate fin drag component
        fin_planform_area = self._calculate_fins_planform_area()
        cd_fins_basic = 0.05 * (fin_planform_area / self.ref_area)
        
        cd_interference = K_int * cd_fins_basic * fins_data['N_fins']
        
        return cd_interference

    def _calculate_wave_drag(self):
        """Calculates wave drag for transonic/supersonic regimes"""
        if self.mach < 0.8:
            return 0.0
        
        # Wave drag becomes significant above Mach 0.8
        if self.mach <= 1.2:
            # Transonic drag rise
            cd_wave = 0.2 * (self.mach - 0.8) ** 2
        else:
            # Supersonic wave drag
            cd_wave = 0.4 / (self.mach ** 1.5)
        
        return cd_wave

    def _transonic_drag_correction(self):
        """Applies transonic drag divergence correction"""
        if self.mach < 0.8:
            return 1.0
        elif self.mach <= 1.2:
            # Drag divergence in transonic region
            return 1.0 + 0.5 * ((self.mach - 0.8) / 0.4) ** 2
        else:
            return 1.2  # Constant factor for supersonic

    def _calculate_dynamic_viscosity(self):
        """Calculates dynamic viscosity using Sutherland's formula"""
        T = self.temp  # [K]
        # Sutherland's constants for air
        C1 = 1.458e-6  # [kg/(m·s·K^0.5)]
        S = 110.4      # [K]
        
        return (C1 * T**1.5) / (T + S)

    def _get_surface_roughness_factor(self):
        """Returns surface roughness multiplier (1.0 = smooth, >1.0 = rough)"""
        # Could be enhanced with material-specific roughness values
        return 1.1  # Slightly rough for painted surface

    # Geometry calculation methods
    def _calculate_nose_wetted_area(self):
        """Calculates wetted area of nose cone"""
        nose = self.rocket_data['nosecone']
        L = nose['length'] / 1000.0  # [m]
        R = nose['diameter'] / 2000.0  # [m]
        
        # Approximation for parabolic nose
        return math.pi * R * math.sqrt(R**2 + L**2)

    def _calculate_body_wetted_area(self):
        """Calculates wetted area of body tube"""
        body = self.rocket_data['fuselage']
        L = body['length'] / 1000.0  # [m]
        D = body['diameter'] / 1000.0  # [m]
        
        return math.pi * D * L

    def _calculate_fins_wetted_area(self):
        """Calculates wetted area of fins (both sides)"""
        fins = self.rocket_data['fins']
        span = fins['span'] / 1000.0  # [m]
        root_chord = fins['chord_root'] / 1000.0  # [m]
        tip_chord = fins['chord_tip'] / 1000.0  # [m]
        
        # Area of one fin (one side)
        area_one_side = 0.5 * (root_chord + tip_chord) * span
        # Total wetted area (both sides of all fins)
        return 2 * area_one_side * fins['N_fins']

    def _calculate_fins_planform_area(self):
        """Calculates planform area of fins (one side only)"""
        fins = self.rocket_data['fins']
        span = fins['span'] / 1000.0  # [m]
        root_chord = fins['chord_root'] / 1000.0  # [m]
        tip_chord = fins['chord_tip'] / 1000.0  # [m]
        
        area_one_fin = 0.5 * (root_chord + tip_chord) * span
        return area_one_fin * fins['N_fins']

    def _calculate_nose_frontal_area(self):
        """Calculates frontal area of nose cone"""
        nose = self.rocket_data['nosecone']
        D = nose['diameter'] / 1000.0  # [m]
        return math.pi * (D/2) ** 2

    def _simple_drag_estimate(self):
        """Fallback simple drag estimation"""
        # Basic drag coefficient estimation
        base_cd = 0.3
        mach_factor = 1.0 + 0.2 * abs(self.mach - 0.8) if self.mach > 0.8 else 1.0
        alpha_factor = 1.0 + 0.1 * abs(self.alpha)
        
        return base_cd * mach_factor * alpha_factor

    # Stability and Lift Calculations (enhanced with your existing methods)
    def _calculate_normal_force_coefficients(self):
        """Calcula los coeficientes de fuerza normal para cada componente usando Barrowman"""
        g = self.rocket_data
        alpha_rad = np.radians(self.alpha)
        
        # Nose cone [Barrowman]
        Cn_alpha_nose = 2.0
        
        # Body tube [Barrowman - negligible for slender bodies at small alpha]
        body_diameter = g['fuselage']['diameter'] / 1000.0
        body_length = g['fuselage']['length'] / 1000.0
        Cn_alpha_body = 0.0  # Small contribution compared to fins
        
        # Fins [Barrowman method]
        fins = g['fins']
        s = fins['span'] / 1000.0
        d = body_diameter
        cr = fins['chord_root'] / 1000.0
        ct = fins['chord_tip'] / 1000.0
        n = fins['N_fins']
        
        # Fin efficiency factor
        K_fin = 1.0 + (d / (2 * s))  # Body interference factor
        
        # Fin normal force coefficient derivative
        AR = (2 * s) / (cr + ct)  # Aspect ratio approximation
        Cn_alpha_fins = (K_fin * 4 * n * (s / d)**2) / (1 + math.sqrt(1 + (2 * AR)**2))
        
        return {
            'nose': Cn_alpha_nose,
            'body': Cn_alpha_body,
            'fins': Cn_alpha_fins
        }

    def _calculate_pressure_centers(self):
        """Calcula la posición del centro de presión para cada componente usando Barrowman"""
        g = self.rocket_data
        
        # Nose cone CP (Barrowman: 0.466 * length for ogive)
        nose_length = g['nosecone']['length'] / 1000.0
        cp_nose = 0.466 * nose_length
        
        # Body tube CP (approximately at midpoint)
        body_length = g['fuselage']['length'] / 1000.0
        cp_body = nose_length + 0.5 * body_length
        
        # Fins CP (Barrowman method for trapezoidal fins)
        fins = g['fins']
        root_chord = fins['chord_root'] / 1000.0
        tip_chord = fins['chord_tip'] / 1000.0
        mid_chord = fins['mid_chord'] / 1000.0
        
        # Fin CP location from root leading edge
        x_fin_cp = (mid_chord / 3) * ((root_chord + 2 * tip_chord) / (root_chord + tip_chord)) + (1/6) * (root_chord + tip_chord - (root_chord * tip_chord) / (root_chord + tip_chord))
        
        # Position from nose tip
        fin_position = g['geometry']['length nosecone fins'] / 1000.0
        cp_fins = fin_position + x_fin_cp
        
        return {
            'nose': cp_nose,
            'body': cp_body,
            'fins': cp_fins
        }

    def _calculate_lift_coefficient(self):
        """Calcula el coeficiente de sustentación basado en fuerza normal"""
        Cn_coeffs = self._calculate_normal_force_coefficients()
        Cn_alpha_total = sum(Cn_coeffs.values())
        
        # Normal force coefficient
        Cn = Cn_alpha_total * np.radians(self.alpha)
        
        # For small angles, lift ≈ normal force
        Cl = Cn * np.cos(np.radians(self.alpha))
        
        # Mach correction (Prandtl-Glauert)
        if self.mach < 0.8:
            Cl /= math.sqrt(1 - self.mach**2)
        elif self.mach > 1.2:
            Cl /= math.sqrt(self.mach**2 - 1)
        
        return Cl

    def _calculate_pressure_center(self):
        """Calcula la posición del centro de presión total"""
        Cn_coeffs = self._calculate_normal_force_coefficients()
        cp_positions = self._calculate_pressure_centers()
        
        total_Cn_alpha = sum(Cn_coeffs.values())
        if total_Cn_alpha == 0:
            return np.array([0., 0., 0.])
            
        xcp = sum(Cn_coeffs[k] * cp_positions[k] for k in Cn_coeffs.keys()) / total_Cn_alpha
        
        return np.array([xcp, 0, 0])  # Already in meters

    def _calculate_stability_margin(self):
        """Calculates static stability margin in calibers"""
        x_cp = self.xcp[0]  # Center of pressure [m]
        
        # Use current CG from mass properties (interpolate between before/after burn if needed)
        # For now, use average CG position
        x_cg_before = self.mass_props['CoM_before_burn']['x']
        x_cg_after = self.mass_props['CoM_after_burn']['x']
        x_cg = (x_cg_before + x_cg_after) / 2  # Simple average
        
        stability_calibers = (x_cp - x_cg) / self.ref_diameter
        
        return stability_calibers

    def get_aerodynamic_forces(self, dynamic_pressure):
        """Returns aerodynamic forces in rocket frame"""
        drag_force = self.cd * dynamic_pressure * self.ref_area
        lift_force = self.cl * dynamic_pressure * self.ref_area
        
        return {
            'drag': drag_force,
            'lift': lift_force,
            'cd': self.cd,
            'cl': self.cl,
            'cp_position': self.xcp,
            'stability_margin': self.stability_margin
        }