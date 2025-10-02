"""
Enhanced Aerodynamics Wrapper with robust error handling
"""

import numpy as np
import math
import logging

class AerodynamicsWrapper:
    def __init__(self, mach, angle_attack, geometry, height=0, density=1.225, temperature=288.15):
        """
        Robust aerodynamics wrapper with comprehensive error handling
        """
        self.mach = max(0.0, min(mach, 5.0))  # Clamp Mach between 0-5
        self.alpha = self._validate_angle(angle_attack)
        self.geometry = self._validate_geometry(geometry)
        self.height = height
        self.density = density
        self.temperature = temperature
        
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

    def _validate_angle(self, angle):
        """Valida y ajusta el ángulo de ataque"""
        a_max = 10  # [deg]
        if abs(angle) >= a_max:
            return a_max * (abs(angle)/angle)
        return angle

    def _validate_geometry(self, geometry):
        """Validates geometry dictionary and provides defaults for missing keys"""
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
        
        # Create a copy of the geometry with defaults for missing keys
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
        """Robust drag coefficient calculation with component breakdown"""
        try:
            # Base drag coefficient
            base_cd = 0.15
            
            # Skin friction component
            skin_friction = self._calculate_skin_friction()
            
            # Pressure drag component
            pressure_drag = self._calculate_pressure_drag()
            
            # Fin drag component
            fin_drag = self._calculate_fin_drag()
            
            # Base drag component
            base_component = self._calculate_base_drag()
            
            # Mach correction
            mach_factor = self._mach_correction()
            
            # Angle of attack correction
            alpha_factor = self._alpha_correction()
            
            total_cd = (base_cd + skin_friction + pressure_drag + fin_drag + base_component) * mach_factor * alpha_factor
            
            return max(0.1, min(2.0, total_cd))  # Reasonable bounds
            
        except Exception as e:
            logging.error(f"Drag calculation error: {e}")
            return 0.5  # Fallback value
    def _calculate_fin_parameters(self):
        """Calculate fin parameters based on fin type"""
        try:
            g = self.geometry
            fin_type = g.get('fin_type', 'Trapezoidal')
            span = g['fins_span'] / 1000.0
            root_chord = g['fins_chord_root'] / 1000.0
            tip_chord = g['fins_chord_tip'] / 1000.0
            n_fins = g['N_fins']
            
            if fin_type == "Trapezoidal":
                # Standard trapezoidal fin calculations
                fin_area = 0.5 * (root_chord + tip_chord) * span
                aspect_ratio = (span ** 2) / fin_area
                mean_chord = (root_chord + tip_chord) / 2
                
            elif fin_type == "Delta":
                # Delta fin (triangular)
                fin_area = 0.5 * root_chord * span
                aspect_ratio = (span ** 2) / fin_area
                mean_chord = root_chord * 2/3  # Mean aerodynamic chord for delta
                
            elif fin_type == "Tapered Swept":
                # Tapered swept fin
                fin_area = 0.5 * (root_chord + tip_chord) * span
                aspect_ratio = (span ** 2) / fin_area
                sweep_angle = g.get('sweep_angle', 30.0)
                mean_chord = (root_chord + tip_chord) / 2
                
            elif fin_type == "Elliptical":
                # Elliptical fin
                fin_area = (np.pi * root_chord * span) / 4
                aspect_ratio = (span ** 2) / fin_area
                mean_chord = root_chord * 0.848  # Mean chord for ellipse
                
            else:  # Custom or fallback
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
            # Fallback values
            return {
                'fin_area': 0.01,
                'total_fin_area': 0.01 * g.get('N_fins', 4),
                'aspect_ratio': 5.0,
                'mean_chord': 0.05,
                'fin_type': 'Trapezoidal'
            }

    def _calculate_skin_friction(self):
        """Calculate skin friction drag component"""
        # Simple skin friction model
        Re_ref = 1e6  # Reference Reynolds number
        Cf = 0.074 / (Re_ref ** 0.2)  # Turbulent skin friction
        
        # Wetted area factor (simplified)
        length_total = self.geometry['len_nosecone_rear'] / 1000.0  # [m]
        diameter = self.geometry['diameter_bodytube'] / 1000.0      # [m]
        wetted_area_ratio = (np.pi * diameter * length_total) / (np.pi * (diameter/2)**2)
        
        return Cf * wetted_area_ratio * 0.1

    def _calculate_pressure_drag(self):
        """Enhanced pressure drag calculation with nosecone type consideration"""
        nosecone_drag = self._calculate_nosecone_drag()
        
        # Add base drag component
        base_drag = self._calculate_base_drag()
        
        return nosecone_drag + base_drag
    
    def _calculate_center_of_pressure_nosecone(self):
        """Calculate nosecone contribution to center of pressure"""
        try:
            g = self.geometry
            nosecone_type = g.get('nosecone_type', 'Conical')
            nose_length = g['len_warhead'] / 1000.0
            
            # CP position as fraction of nosecone length from tip
            # Based on Barrowman theory and empirical data
            if nosecone_type == "Conical":
                cp_fraction = 0.666  # 2/3 of length from tip
            elif nosecone_type == "Ogival":
                cp_fraction = 0.466
            elif nosecone_type == "Elliptical":
                cp_fraction = 0.500
            elif nosecone_type == "Parabolic":
                parabolic_param = g.get('parabolic_parameter', 0.5)
                cp_fraction = 0.500 + 0.1 * parabolic_param
            elif nosecone_type == "Power Series":
                power_val = g.get('power_value', 0.5)
                cp_fraction = 0.466 + 0.1 * power_val
            elif nosecone_type == "Von Kármán":
                cp_fraction = 0.450
            elif nosecone_type == "Haack Series":
                cp_fraction = 0.455
            else:
                cp_fraction = 0.500
                
            return cp_fraction * nose_length
            
        except Exception as e:
            logging.error(f"Nosecone CP calculation error: {e}")
            return 0.0

    def _calculate_fin_drag(self):
        """Calculate drag contribution from fins considering fin type"""
        try:
            fin_params = self._calculate_fin_parameters()
            n_fins = self.geometry['N_fins']
            
            # Base fin drag coefficient
            if fin_params['fin_type'] == "Delta":
                base_cd_fin = 0.008
            elif fin_params['fin_type'] == "Elliptical":
                base_cd_fin = 0.006
            elif fin_params['fin_type'] == "Tapered Swept":
                base_cd_fin = 0.007
            else:  # Trapezoidal and Custom
                base_cd_fin = 0.01
                
            # Aspect ratio correction
            ar_correction = 1.0 / np.sqrt(fin_params['aspect_ratio'])
            
            # Mach correction for fins
            if self.mach < 0.8:
                mach_correction = 1.0
            elif self.mach <= 1.2:
                mach_correction = 1.0 + 0.5 * ((self.mach - 0.8) / 0.4)
            else:
                mach_correction = 1.2
                
            # Total fin area relative to reference area
            ref_diameter = self.geometry['diameter_bodytube'] / 1000.0
            ref_area = np.pi * (ref_diameter/2)**2
            
            if ref_area > 0:
                fin_area_ratio = fin_params['total_fin_area'] / ref_area
                return base_cd_fin * fin_area_ratio * ar_correction * mach_correction
            else:
                return base_cd_fin * n_fins * 0.1
                
        except Exception as e:
            logging.warning(f"Fin drag calculation issue: {e}")
            return 0.02 * self.geometry.get('N_fins', 4)

    def _calculate_base_drag(self):
        """Calculate base drag component"""
        if self.mach < 0.8:
            return 0.12 + 0.1 * self.mach
        else:
            return 0.08

    def _mach_correction(self):
        """Apply Mach number correction"""
        if self.mach < 0.8:
            return 1.0
        elif self.mach <= 1.2:
            # Transonic drag rise
            return 1.0 + 2.0 * ((self.mach - 0.8) / 0.4) ** 2
        else:
            # Supersonic
            return 1.2 / (1.0 + 0.2 * self.mach)

    def _alpha_correction(self):
        """Apply angle of attack correction"""
        alpha_rad = np.radians(abs(self.alpha))
        return 1.0 + 0.5 * alpha_rad**2

    def _calculate_lift_coefficient(self):
        """Enhanced lift coefficient calculation with fin type consideration"""
        if abs(self.alpha) < 0.1:
            return 0.0
            
        try:
            alpha_rad = np.radians(self.alpha)
            fin_params = self._calculate_fin_parameters()
            
            # Lift curve slope varies by fin type
            if fin_params['fin_type'] == "Delta":
                cl_alpha = 2.5 * np.pi  # Higher lift slope for delta wings
            elif fin_params['fin_type'] == "Elliptical":
                cl_alpha = 2.2 * np.pi  # Elliptical has good lift characteristics
            else:
                cl_alpha = 2.0 * np.pi  # Standard for trapezoidal
                
            # Aspect ratio effect
            ar_factor = fin_params['aspect_ratio'] / (2 + fin_params['aspect_ratio'])
            
            cl = cl_alpha * alpha_rad * ar_factor
            
            # Mach correction
            if self.mach < 0.8:
                cl /= max(0.1, math.sqrt(1 - self.mach**2))
            elif self.mach > 1.2:
                cl /= math.sqrt(self.mach**2 - 1)
                
            return cl * 0.3  # Scale factor for model rockets
            
        except Exception as e:
            logging.error(f"Lift calculation error: {e}")
            return 0.0

    def _calculate_pressure_center(self):
        """Robust center of pressure calculation with nosecone consideration"""
        try:
            g = self.geometry
            
            # Convert to meters
            nose_length = g['len_warhead'] / 1000.0
            body_length = g['len_bodytube_wo_rear'] / 1000.0
            fin_position = g['len_nosecone_fins'] / 1000.0
            
            # Nose cone CP (type-specific)
            cp_nose = self._calculate_center_of_pressure_nosecone()
            
            # Body tube CP (midpoint)
            cp_body = nose_length + 0.5 * body_length
            
            # Fins CP
            root_chord = g['fins_chord_root'] / 1000.0
            x_fin_cp = fin_position + 0.6 * root_chord  # 60% of root chord
            
            # Weighted average based on component areas
            # Nosecone has less influence than fins for stability
            ref_diameter = g['diameter_bodytube'] / 1000.0
            ref_area = np.pi * (ref_diameter/2)**2
            
            # Approximate relative influence (simplified)
            nosecone_weight = 0.15
            body_weight = 0.10
            fins_weight = 0.75
            
            xcp_total = (nosecone_weight * cp_nose + 
                        body_weight * cp_body + 
                        fins_weight * x_fin_cp)
            
            return np.array([xcp_total, 0, 0])
            
        except Exception as e:
            logging.error(f"CP calculation error: {e}")
            # Default CP position (50% of total length)
            total_length = g.get('len_nosecone_rear', 1199.47) / 1000.0
            return np.array([total_length * 0.5, 0, 0])