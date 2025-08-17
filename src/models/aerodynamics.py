# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""

*** Aerodynamics.py ***

Contains:
Aerodynamics module containing aerodynamic coefficients.

External dependencies:
numpy       -Numpy Python extension. http://numpy.org/
             Version: Numpy 1.22.3
scipy       -Scipy Python extension. https://www.scipy.org
             Version: Scipy 1.6.2

Changelog:
Date          Name              Change
__ _          __ _              ____ _
15/08/2022    Jorge Orozco      Initial release

References:
Short       Author,Year               Title
___ _       _________ _               ___ _
[Valle22]   Vallejos,2022             Mejora del alcance de un cohete chaff
[Barro67]   Barrowman,1967            The Practical Calculation of the Aerodynamic Characteristic of Slender Finned Vehicles
[Box09]     Box/Bishop/Hunt,2009      Estimating the dynamic and aerodynamic parameters of 
                                      passively controlled high power rockets for flight simulation
[Ketch92]   Ketchledge,1992           Active Guidance and Dynamic Flight Mechanics for Model Rockets
[Fleem01]   Fleeman,2001              Tactical Missile Design

        len_warhead [mm]     # Length of warhead or distance from tip of nose to base of nose
        len_nosecone_fins [mm]     # Length between nose cone tip and the point where the fin leading edge meets the body tube
        len_nosecone_rear [mm]     # Length between nose tip to rear
        
        len_bodytube_wo_rear [mm]     # Length of body tube (not considering rear)
        fins_chord_root [mm]     # Fins aerodynamic chord at root
        fins_chord_tip [mm]     # Fins aerodynamic chord at tip
        fins_mid_chord [mm]     # Fins aerodynamic mid-chord
        len_rear [mm]     # Length of rear
        fins_span [mm]     # Fins span

        diameter_warhead_base [mm]     # Diameter of base of warhead
        diameter_bodytube [mm]     # Diameter of body tube
        end_diam_rear [mm]     # Diameter of rear at the end
        
        N_fins [-]      # Number of fins


"""

# Imports
from os import path
import logging


path
import numpy as np
from scipy import interpolate

class Aerodynamics:
    def __init__(self, mach, angle_attack, geometry):
        logging.debug(f"Inicializando cálculos aerodinámicos: Mach={mach:.2f}, α={angle_attack:.1f}°")
        try:
            self.mach = mach
            self.alpha = self._validate_angle(angle_attack)
            self.geometry = self._validate_geometry(geometry)
            
            # Calcular coeficientes
            self.cd = self._calculate_drag_coefficient()
            self.cl = self._calculate_lift_coefficient()
            self.xcp = self._calculate_pressure_center()
            
            logging.debug(f"Coeficientes calculados: CD={self.cd:.3f}, CL={self.cl:.3f}")
        except Exception as e:
            logging.error(f"Error en cálculos aerodinámicos: {str(e)}")
            raise

    def _validate_angle(self, angle):
        """Valida y ajusta el ángulo de ataque"""
        a_max = 10  # [deg]
        if abs(angle) >= a_max:
            return a_max * (abs(angle)/angle)
        return angle

    def _validate_geometry(self, geometry):
        """
        Valida los parámetros geométricos y sus relaciones.
        
        Args:
            geometry (dict): Diccionario con parámetros geométricos
            
        Returns:
            dict: Geometría validada
            
        Raises:
            ValueError: Si algún parámetro es inválido o inconsistente
        """
        required_params = [
            'len_warhead', 'diameter_warhead_base', 'len_nosecone_fins',
            'fins_chord_root', 'fins_chord_tip', 'fins_mid_chord',
            'N_fins', 'fins_span', 'len_bodytube_wo_rear',
            'diameter_bodytube', 'len_rear', 'end_diam_rear', 
            'len_nosecone_rear', 'diameter_rear_bodytube', 'diameter_bodytube_fins'
        ]
        
        # Verificar existencia y positividad
        for param in required_params:
            if param not in geometry:
                raise ValueError(f"Falta parámetro geométrico: {param}")
            if geometry[param] <= 0:
                raise ValueError(f"Parámetro inválido {param}: {geometry[param]}")
        
        # Verificar relaciones geométricas
        if geometry['len_warhead'] > geometry['len_nosecone_rear']:
            raise ValueError("Longitud de ojiva mayor que longitud total")
            
        if geometry['fins_chord_tip'] > geometry['fins_chord_root']:
            raise ValueError("Cuerda de punta mayor que cuerda de raíz")
            
        if geometry['fins_span'] > geometry['diameter_bodytube'] * 2:
            raise ValueError("Envergadura de aletas mayor que diámetro del cuerpo")
        
        return geometry

    def _calculate_drag_coefficient(self):
        """Calcula el coeficiente de arrastre"""
        # Datos tabulados [Valle22]
        m = np.array([0.1, 0.4, 0.7, 0.8, 0.9, 1.0, 1.1, 1.15, 1.2, 1.25,
                     1.3, 1.4, 1.6, 1.9, 2.2, 2.5, 3.0])
        cd = np.array([0.32498, 0.32302, 0.32639, 0.32957, 0.34603,
                      0.45078, 0.50512, 0.525, 0.55998, 0.53465, 0.51829,
                      0.50535, 0.47411, 0.42844, 0.38992, 0.3556, 0.30924])
        
        spline = interpolate.splrep(m, cd)
        return float(interpolate.splev(self.mach, spline))

    def _calculate_normal_force_coefficients(self):
        """Calcula los coeficientes de fuerza normal para cada componente"""
        g = self.geometry
        alpha_rad = np.radians(self.alpha)
        
        # Ojiva [Box09]
        Cn_alpha_cone = 2.0
        
        # Cuerpo [Box09]
        Cn_alpha_body = (g['len_bodytube_wo_rear']/(np.pi*0.25*g['diameter_bodytube'])) * alpha_rad
        
        # Sección trasera [Box09]
        Cn_alpha_tail = 2.0 * (
            (g['end_diam_rear']/g['diameter_warhead_base'])**2 - 
            (g['diameter_rear_bodytube']/g['diameter_warhead_base'])**2
        )
        
        # Aletas [Box09]
        Kfb = 1.0 + ((0.5*g['diameter_bodytube_fins'])/(g['fins_span'] + 0.5*g['diameter_bodytube_fins']))
        Cn_alpha_fins = (Kfb*4*g['N_fins']) * (
            (g['fins_span']/g['diameter_warhead_base'])**2 /
            (1 + np.sqrt(1+(2*g['fins_mid_chord']/(g['fins_chord_root']+g['fins_chord_tip']))**2))
        )
        
        return {
            'cone': Cn_alpha_cone,
            'body': Cn_alpha_body,
            'tail': Cn_alpha_tail,
            'fins': Cn_alpha_fins
        }

    def _calculate_pressure_centers(self):
        """Calcula la posición del centro de presión para cada componente"""
        g = self.geometry
        
        cp = {
            'cone': 0.466 * g['len_warhead'],
            'body': g['len_warhead'] + 0.5 * g['len_bodytube_wo_rear'],
            'tail': g['len_nosecone_rear'] + (g['len_rear']/3) * (
                1 + 1/(1+(g['diameter_rear_bodytube']/g['diameter_warhead_base']))
            ),
            'fins': g['len_nosecone_fins'] + 
                   ((g['fins_mid_chord']/3) * 
                    ((g['fins_chord_root'] + 2*g['fins_chord_tip'])/
                     (g['fins_chord_root']+g['fins_chord_tip']))) +
                   ((1/6)*(g['fins_chord_root'] + g['fins_chord_tip']-
                    ((g['fins_chord_root']*g['fins_chord_tip'])/
                     (g['fins_chord_root']+g['fins_chord_tip']))))
        }
        
        return cp

    def _calculate_lift_coefficient(self):
        """Calcula el coeficiente de sustentación"""
        # Obtener coeficientes de fuerza normal
        Cn_coeffs = self._calculate_normal_force_coefficients()
        Cn_sum = sum(Cn_coeffs.values())
        cn = Cn_sum * np.radians(self.alpha)
        
        # Corrección de Ketchledge [Ketch92]
        if self.mach <= 0.8:
            return cn / np.sqrt(1 - (self.mach**2))
        elif self.mach > 0.8 and self.mach <= 1.2:
            return cn / np.sqrt(1 - (0.8**2))
        else:
            return cn / np.sqrt(-1 + (self.mach**2))

    def _calculate_pressure_center(self):
        """Calcula la posición del centro de presión"""
        Cn_coeffs = self._calculate_normal_force_coefficients()
        cp_positions = self._calculate_pressure_centers()
        
        # Centro de presión total [Box09]
        Cn_sum = sum(Cn_coeffs.values())
        if Cn_sum == 0:
            return np.array([0., 0., 0.])
            
        xcp = sum(Cn_coeffs[k] * cp_positions[k] for k in Cn_coeffs.keys()) / Cn_sum
        return np.array([xcp/1000, 0, 0])  # Convertir a metros

