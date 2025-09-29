# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""
Módulo de simulación del motor cohete.

Este módulo maneja el cálculo del empuje y flujo másico del motor,
considerando los efectos de la presión atmosférica y el tiempo de quemado.

Ecuaciones Principales:
    1. Empuje:
       T = ṁv_e + (p_e - p_a)A_e
       
    2. Flujo Másico:
       ṁ = m_prop/t_burn  (asumiendo quemado constante)

Referencias:
    - Sutton, G. P., & Biblarz, O. (2016). Rocket propulsion elements.
    - Hill, P., & Peterson, C. (1992). Mechanics and Thermodynamics of Propulsion.
"""
# Imports
from cmath import pi
import numpy as np

# Define Engine class for Engine module. Data given by [Valle22]  # All data SHOULD be obtained from external file
class Engine:
    """
    Clase que modela el comportamiento del motor cohete.
    
    Atributos:
        time (float): Tiempo actual de operación [s]
        ambient_pressure (float): Presión ambiente [Pa]
        burn_time (float): Tiempo total de quemado [s]
        nozzle_exit_diameter (float): Diámetro de salida de la tobera [m]
        propellant_mass (float): Masa de propelente [kg]
        specific_impulse (float): Impulso específico [s]
        mean_thrust (float): Empuje medio [N]
        max_thrust (float): Empuje máximo [N]
        mean_chamber_pressure (float): Presión media de cámara [Pa]
        max_chamber_pressure (float): Presión máxima de cámara [Pa]
        thrust_to_weight_ratio (float): Relación empuje/peso [-]
    """
    
    def __init__(self, time, burn_time, ambient_pressure, nozzle_exit_diameter,
                 propellant_mass, specific_impulse, mean_thrust, max_thrust,
                 mean_chamber_pressure, max_chamber_pressure, thrust_to_weight_ratio):
        """
        Inicializa el motor cohete con los nuevos parámetros.

        Args:
            time (float): Tiempo actual [s]
            burn_time (float): Tiempo total de quemado [s]
            ambient_pressure (float): Presión ambiente [Pa]
            nozzle_exit_diameter (float): Diámetro de salida de la tobera [m]
            propellant_mass (float): Masa de propelente [kg]
            specific_impulse (float): Impulso específico [s]
            mean_thrust (float): Empuje medio [N]
            max_thrust (float): Empuje máximo [N]
            mean_chamber_pressure (float): Presión media de cámara [Pa]
            max_chamber_pressure (float): Presión máxima de cámara [Pa]
            thrust_to_weight_ratio (float): Relación empuje/peso [-]
        """
        # Validaciones básicas
        if ambient_pressure < 0:
            raise ValueError("La presión ambiente no puede ser negativa")
        if burn_time <= 0:
            raise ValueError("El tiempo de quemado debe ser positivo")
        if nozzle_exit_diameter <= 0:
            raise ValueError("El diámetro de la tobera debe ser positivo")
        if propellant_mass <= 0:
            raise ValueError("La masa de propelente debe ser positiva")
        if specific_impulse <= 0:
            raise ValueError("El impulso específico debe ser positivo")
        if mean_thrust <= 0 or max_thrust <= 0:
            raise ValueError("El empuje debe ser positivo")
        if mean_chamber_pressure <= 0 or max_chamber_pressure <= 0:
            raise ValueError("La presión de cámara debe ser positiva")
        if thrust_to_weight_ratio <= 0:
            raise ValueError("La relación empuje/peso debe ser positiva")

        self.time = time
        self.ambient_pressure = ambient_pressure
        self.burn_time = burn_time
        self.nozzle_exit_diameter = nozzle_exit_diameter
        self.propellant_mass = propellant_mass
        self.specific_impulse = specific_impulse
        self.mean_thrust = mean_thrust
        self.max_thrust = max_thrust
        self.mean_chamber_pressure = mean_chamber_pressure
        self.max_chamber_pressure = max_chamber_pressure
        self.thrust_to_weight_ratio = thrust_to_weight_ratio

        # Área de salida de la tobera
        self.exit_area = np.pi * (self.nozzle_exit_diameter/2)**2

        # Flujo másico medio (ṁ = m_prop / t_burn)
        self._mass_flux_mean = self.propellant_mass / self.burn_time

        # Empuje instantáneo (rampa de encendido/apagado)
        self._mass_flux = 0.0
        self._thrust = 0.0
        self.gas_speed = 0.0
        self.exit_pressure = 0.0

        self._calculate_performance()

    @property
    def mass_flux(self):
        """Getter para el flujo másico"""
        return self._mass_flux

    @property
    def thrust(self):
        """Getter para el empuje"""
        return self._thrust

    def _calculate_performance(self):
        """Calcula el rendimiento del motor basado en el tiempo actual y los nuevos parámetros"""
        self._mass_flux = 0.0
        self._thrust = 0.0
        self.gas_speed = 0.0
        self.exit_pressure = 0.0

        if 0 <= self.time <= self.burn_time:
            # Rampa de encendido/apagado (primeros/últimos 0.1s)
            if self.time < 0.1:
                ramp_factor = self.time / 0.1
                thrust = self.max_thrust * ramp_factor
            elif self.time > (self.burn_time - 0.1):
                remaining_time = self.burn_time - self.time
                ramp_factor = remaining_time / 0.1
                thrust = self.max_thrust * ramp_factor
            else:
                thrust = self.mean_thrust

            self._thrust = max(0.0, min(thrust, self.max_thrust))

            # Flujo másico instantáneo (ṁ = T / (Isp * g0))
            g0 = 9.80665
            if self.specific_impulse > 0:
                self._mass_flux = self._thrust / (self.specific_impulse * g0)
            else:
                self._mass_flux = 0.0

            # Velocidad de gases (v_e = Isp * g0)
            self.gas_speed = self.specific_impulse * g0

            # Presión de salida estimada (usando presión media de cámara y área)
            # Aproximación: p_e = p_c * (A_throat / A_exit)^(gamma/(gamma-1)), pero aquí solo se usa media
            self.exit_pressure = self.mean_chamber_pressure * 0.1  # Factor arbitrario, ajustar según modelo real

        else:
            self._mass_flux = 0.0
            self._thrust = 0.0
            self.gas_speed = 0.0
            self.exit_pressure = 0.0

    def update(self, time=None, ambient_pressure=None):
        """
        Actualiza el estado del motor.

        Args:
            time (float, opcional): Nuevo tiempo [s]
            ambient_pressure (float, opcional): Nueva presión ambiente [Pa]
        """
        if time is not None:
            self.time = time
        if ambient_pressure is not None:
            if ambient_pressure < 0:
                raise ValueError("La presión ambiente no puede ser negativa")
            self.ambient_pressure = ambient_pressure
        
        self._calculate_performance()

    def calculate_specific_impulse(self, ambient_pressure=None):
        """
        Calcula el impulso específico para una presión ambiente dada.
        
        Args:
            ambient_pressure (float, opcional): Presión ambiente [Pa].
                Si no se especifica, usa la presión ambiente actual.
        
        Returns:
            float: Impulso específico [s]
        """
        g0 = 9.80665
        p_amb = self.ambient_pressure if ambient_pressure is None else ambient_pressure
        momentum_thrust = self._mass_flux * self.gas_speed
        pressure_thrust = (self.exit_pressure - p_amb) * self.exit_area
        total_thrust = momentum_thrust + pressure_thrust
        if self._mass_flux > 0:
            return total_thrust / (self._mass_flux * g0)
        return 0.0