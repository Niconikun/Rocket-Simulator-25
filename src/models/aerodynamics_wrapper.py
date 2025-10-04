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
        self.v_norm = self.mach * 340.0  # Approximate speed of sound for calculations
        
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
            # Calculate reference area
            ref_diameter = self.geometry['diameter_bodytube'] / 1000.0
            ref_area = np.pi * (ref_diameter/2)**2
            
            if ref_area <= 0:
                return 0.5  # Fallback
                
            # Calculate component drag coefficients relative to reference area
            skin_friction = self._calculate_skin_friction()
            pressure_drag = self._calculate_pressure_drag()
            fin_drag = self._calculate_fin_drag()
            base_drag = self._calculate_base_drag()
            
            # Sum components (they're already normalized to reference area)
            total_cd = skin_friction + pressure_drag + fin_drag + base_drag
            
            # Apply corrections
            mach_factor = self._mach_correction()
            alpha_factor = self._alpha_correction()
            
            total_cd *= mach_factor * alpha_factor
            
            return max(0.1, min(2.0, total_cd))
            
        except Exception as e:
            logging.error(f"Drag calculation error: {e}")
            return 0.5

    def _calculate_skin_friction(self):
        """Calculate skin friction drag with proper Reynolds number"""
        try:
            # Characteristic length (rocket length)
            L = self.geometry['len_nosecone_rear'] / 1000.0  # [m]
            diameter = self.geometry['diameter_bodytube'] / 1000.0
            
            if L <= 0 or self.v_norm <= 0:
                return 0.01
                
            # Calculate Reynolds number
            # Dynamic viscosity of air (simplified)
            mu = 1.789e-5  # [Pa·s] at sea level
            Re = (self.density * self.v_norm * L) / mu
            
            # Turbulent skin friction coefficient (Schlichting)
            Cf = 0.074 / (Re ** 0.2) if Re > 0 else 0.0
            
            # Wetted area (simplified cylinder)
            wetted_area = np.pi * diameter * L
            
            # Reference area
            ref_area = np.pi * (diameter/2)**2
            
            if ref_area > 0:
                # Convert to coefficient based on reference area
                skin_friction_cd = Cf * (wetted_area / ref_area)
            else:
                skin_friction_cd = 0.01
                
            return max(0.001, min(0.1, skin_friction_cd))
            
        except Exception as e:
            logging.error(f"Skin friction calculation error: {e}")
            return 0.01

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

    def _calculate_fin_drag(self):
        """Calculate drag contribution from fins"""
        try:
            fin_params = self._calculate_fin_parameters()
            
            # Reference area
            ref_diameter = self.geometry['diameter_bodytube'] / 1000.0
            ref_area = np.pi * (ref_diameter/2)**2
            
            if ref_area <= 0:
                return 0.02
                
            # Fin drag relative to reference area
            fin_drag_area_ratio = fin_params['total_fin_area'] / ref_area
            
            # Base fin CD (depends on fin type and thickness)
            base_cd_fin = {
                "Trapezoidal": 0.008,
                "Delta": 0.006,
                "Tapered Swept": 0.007,
                "Elliptical": 0.005,
                "Custom": 0.008
            }.get(fin_params['fin_type'], 0.008)
            
            # Aspect ratio correction
            ar = fin_params['aspect_ratio']
            ar_correction = 1.0 / np.sqrt(1.0 + ar)  # More realistic correction
            
            # Mach correction for fins
            mach_correction = self._fin_mach_correction()
            
            # Interference factor (fins attached to body)
            interference_factor = 1.1
            
            total_fin_cd = base_cd_fin * fin_drag_area_ratio * ar_correction * mach_correction * interference_factor
            
            return max(0.001, min(0.1, total_fin_cd))
            
        except Exception as e:
            logging.warning(f"Fin drag calculation issue: {e}")
            return 0.02

    def _fin_mach_correction(self):
        """Mach correction specific to fin drag"""
        if self.mach < 0.8:
            return 1.0
        elif self.mach <= 1.2:
            return 1.0 + 0.5 * ((self.mach - 0.8) / 0.4)
        else:
            return 1.2

    def _calculate_base_drag(self):
        """Calculate base drag component"""
        if self.mach < 0.8:
            return 0.12 + 0.1 * self.mach
        else:
            return 0.08

    def _mach_correction(self):
        """Apply Mach number correction to drag"""
        if self.mach < 0.8:
            return 1.0
        elif self.mach <= 1.0:
            # Transonic drag rise (more accurate)
            return 1.0 + 1.2 * ((self.mach - 0.8) / 0.2)
        elif self.mach <= 1.2:
            # Supersonic transition
            return 2.2 - 0.5 * ((self.mach - 1.0) / 0.2)
        else:
            # Supersonic (1/Mach decay)
            return 1.7 / (1.0 + 0.2 * self.mach)

    def _alpha_correction(self):
        """Apply angle of attack correction"""
        alpha_rad = np.radians(abs(self.alpha))
        return 1.0 + 0.5 * alpha_rad**2

    def _calculate_lift_coefficient(self):
        """Enhanced lift coefficient calculation"""
        if abs(self.alpha) < 0.1:
            return 0.0
            
        try:
            alpha_rad = np.radians(self.alpha)
            fin_params = self._calculate_fin_parameters()
            
            # Lift primarily comes from fins for rockets
            # Fin lift curve slope (per radian)
            fin_cl_alpha = (2 * np.pi * fin_params['aspect_ratio']) / (
                2 + np.sqrt(4 + (fin_params['aspect_ratio'] * 0.95)**2 * (1 + np.tan(0)**2))
            )
            
            # Number of fins effect
            n_fins = self.geometry['N_fins']
            fin_effectiveness = min(1.0, n_fins / 4.0)  # 4 fins is optimal
            
            # Total lift coefficient from fins
            cl_fins = fin_cl_alpha * alpha_rad * fin_effectiveness
            
            # Body contribution (small for rockets)
            cl_body = 0.1 * alpha_rad  # Simplified body lift
            
            total_cl = cl_fins + cl_body
            
            # Mach correction
            if self.mach < 0.8:
                # Subsonic Prandtl-Glauert
                total_cl /= max(0.3, math.sqrt(1 - self.mach**2))
            elif self.mach > 1.2:
                # Supersonic (Ackeret theory)
                total_cl /= math.sqrt(self.mach**2 - 1)
                
            return total_cl
            
        except Exception as e:
            logging.error(f"Lift calculation error: {e}")
            return 0.0

    def _calculate_pressure_drag(self):
        """Enhanced pressure drag calculation with nosecone type consideration"""
        try:
            nosecone_drag = self._calculate_nosecone_drag()
            
            # Add body tube pressure drag (separate from base drag)
            body_drag = self._calculate_body_pressure_drag()
            
            return nosecone_drag + body_drag
            
        except Exception as e:
            logging.error(f"Pressure drag calculation error: {e}")
            return 0.3

    def _calculate_nosecone_drag(self):
        """Calculate nosecone drag coefficient based on nosecone type"""
        try:
            g = self.geometry
            nosecone_type = g.get('nosecone_type', 'Conical')
            length = g['len_warhead'] / 1000.0  # Convert to meters
            base_diameter = g['diameter_warhead_base'] / 1000.0
            
            if base_diameter <= 0 or length <= 0:
                return 0.1  # Fallback value
                
            # Fineness ratio (length to diameter ratio)
            fineness_ratio = length / base_diameter
            
            # Base drag coefficients for different nosecone types at Mach 0
            base_drag_coefficients = {
                "Conical": 0.50,
                "Ogival": 0.40,
                "Elliptical": 0.30,
                "Parabolic": 0.35,
                "Power Series": 0.38,
                "Von Kármán": 0.28,
                "Haack Series": 0.25
            }
            
            # Get base drag coefficient
            cd_base = base_drag_coefficients.get(nosecone_type, 0.40)
            
            # Fineness ratio correction
            if fineness_ratio > 5:
                fineness_factor = 0.7
            elif fineness_ratio > 3:
                fineness_factor = 0.8
            elif fineness_ratio > 2:
                fineness_factor = 0.9
            else:
                fineness_factor = 1.0
                
            # Type-specific adjustments
            if nosecone_type == "Conical":
                type_factor = 1.0
            elif nosecone_type == "Ogival":
                ogive_radius = g.get('ogive_radius', base_diameter * 2) / 1000.0
                if ogive_radius > base_diameter * 1.5:
                    type_factor = 0.9
                else:
                    type_factor = 1.0
            elif nosecone_type == "Elliptical":
                type_factor = 0.85
            elif nosecone_type == "Parabolic":
                parabolic_param = g.get('parabolic_parameter', 0.5)
                if parabolic_param < 0.3:
                    type_factor = 1.0
                elif parabolic_param > 0.7:
                    type_factor = 0.9
                else:
                    type_factor = 0.95
            elif nosecone_type == "Power Series":
                power_val = g.get('power_value', 0.5)
                if power_val < 0.3:
                    type_factor = 1.0
                elif power_val > 0.7:
                    type_factor = 0.9
                else:
                    type_factor = 0.95
            elif nosecone_type == "Von Kármán":
                type_factor = 0.8
            elif nosecone_type == "Haack Series":
                haack_type = g.get('haack_type', 'LV-Haack')
                if haack_type == "LD-Haack":
                    type_factor = 0.75
                else:
                    type_factor = 0.85
            else:
                type_factor = 1.0
                
            # Mach number correction for nosecone
            mach_factor = self._nosecone_mach_correction()
            
            # Calculate final nosecone drag coefficient
            cd_nose = cd_base * fineness_factor * type_factor * mach_factor
            
            return max(0.1, min(1.0, cd_nose))
            
        except Exception as e:
            logging.error(f"Nosecone drag calculation error: {e}")
            return 0.4

    def _nosecone_mach_correction(self):
        """Apply Mach number correction specific to nosecone drag"""
        if self.mach < 0.8:
            return 1.0
        elif self.mach <= 1.2:
            transonic_factor = 1.0 + 1.5 * ((self.mach - 0.8) / 0.4) ** 2
            return transonic_factor
        else:
            return 1.2 / (1.0 + 0.15 * self.mach)

    def _calculate_body_pressure_drag(self):
        """Calculate pressure drag from the rocket body tube"""
        try:
            g = self.geometry
            body_length = g['len_bodytube_wo_rear'] / 1000.0
            diameter = g['diameter_bodytube'] / 1000.0
            
            if body_length <= 0 or diameter <= 0:
                return 0.05
                
            # Body drag increases with length-to-diameter ratio
            l_d_ratio = body_length / diameter
            
            # Base body drag coefficient
            base_body_cd = 0.08
            
            # Correction for body length
            if l_d_ratio > 20:
                length_factor = 1.3
            elif l_d_ratio > 10:
                length_factor = 1.1
            elif l_d_ratio > 5:
                length_factor = 1.0
            else:
                length_factor = 0.9
                
            # Mach correction for body
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

    def _calculate_center_of_pressure_nosecone(self):
        """Calculate nosecone contribution to center of pressure"""
        try:
            g = self.geometry
            nosecone_type = g.get('nosecone_type', 'Conical')
            nose_length = g['len_warhead'] / 1000.0
            
            # CP position as fraction of nosecone length from tip
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