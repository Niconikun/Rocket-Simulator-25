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
import numpy as np
import json

class MotorConfig():
    """Contains the settings required for simulation, including environmental conditions and details about
    how to run the simulation."""
    def __init__(self, maxPressure, maxMassFlux, maxMachNumber, minPortThroat, flowSeparationWarnPercent, burnoutWebThres, burnoutThrustThres, timestep, ambPressure, mapDim, sepPressureRatio):
        # Limits
        self.maxPressure = maxPressure #Max Allowed Pressure [Pa]
        self.maxMassFlux = maxMassFlux #Maximum Allowed Mass Flux [kg/(m^2*s)]
        self.maxMachNumber = maxMachNumber #Maximum Allowed Core Mach Number [-]
        self.minPortThroat = minPortThroat #Minimum Allowed Port/Throat Ratio [-]
        self.flowSeparationWarnPercent = flowSeparationWarnPercent #Flow Separation Warning Threshold [-]
        # Simulation
        self.burnoutWebThres = burnoutWebThres #Web Burnout Threshold [m]
        self.burnoutThrustThres = burnoutThrustThres #Thrust Burnout Threshold [%]
        self.timestep = timestep #Simulation Timestep [s]
        self.ambPressure = ambPressure #Ambient Pressure [Pa]
        self.mapDim = mapDim #Grain Map Dimension [-]
        self.sepPressureRatio = sepPressureRatio #Separation Pressure Ratio [-]

# Define Engine class for Engine module. Data given by [Valle22]  # All data SHOULD be obtained from external file
class Engine:
    """
    Clase que modela el comportamiento del motor cohete.
    
    Atributos:
        time (float): Tiempo actual de operación [s]
        ambient_pressure (float): Presión ambiente [Pa]
        burn_time (float): Tiempo total de quemado [s]
        nozzle_exit_diameter (float): Diámetro de salida de la tobera [m]
        _mass_flux (float): Flujo másico [kg/s]
        gas_speed (float): Velocidad de los gases de escape [m/s]
        exit_pressure (float): Presión de salida [Pa]
    """
    
    def __init__(self, time, ambient_pressure, burn_time, nozzle_exit_diameter, 
                 mass_flux_max, gas_speed, exit_pressure,
                 length_chamber, diameter_chamber,
                 grain_outer_diameter, grain_length, grain_inner_diameter, N_grains, rho_grain, rho_percentage):
        """
        Inicializa el motor cohete.

        Args:
            time (float): Tiempo actual [s]
            ambient_pressure (float): Presión ambiente [Pa]
            burn_time (float): Tiempo total de quemado [s]
            nozzle_exit_diameter (float): Diámetro de salida de la tobera [m]
            mass_flux_max (float): Flujo másico máximo [kg/s]
            gas_speed (float): Velocidad de los gases [m/s]
            exit_pressure (float): Presión de salida [Pa]

        Raises:
            ValueError: Si algún parámetro es negativo o físicamente inválido
        """
        # Validación extendida de parámetros
        try:
            # Cargar configuración del cohete
            with open('data/propellant/propellant_data.json', 'r') as file:
                propellant_data = json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError("No se encontró el archivo de configuración del cohete")
        except json.JSONDecodeError:
            raise ValueError("Error al leer el archivo de configuración del cohete")

        if ambient_pressure < 0:
            raise ValueError("La presión ambiente no puede ser negativa")
        if burn_time <= 0:
            raise ValueError("El tiempo de quemado debe ser positivo")
        if nozzle_exit_diameter <= 0:
            raise ValueError("El diámetro de la tobera debe ser positivo")
        if mass_flux_max <= 0:
            raise ValueError("El flujo másico máximo debe ser positivo")
        if gas_speed <= 0:
            raise ValueError("La velocidad de los gases debe ser positiva")
        if exit_pressure <= 0:
            raise ValueError("La presión de salida debe ser positiva")

        # Validaciones físicas adicionales
        if exit_pressure < ambient_pressure/100:  # Factor de seguridad para vacío
            raise ValueError("La presión de salida es demasiado baja")
        if gas_speed > 5000:  # Límite superior típico para motores químicos
            raise ValueError("Velocidad de gases demasiado alta")
            
        # Validaciones térmicas
        T_chamber = 3000  # K (temperatura típica de combustión)
        gamma = 1.2  # Razón de calores específicos
        R = 8314/30  # Constante de gas específica (J/kg·K)
        a_throat = np.sqrt(gamma * R * T_chamber)
        max_exit_mach = 3.5
        max_allowed_speed = max_exit_mach * a_throat

        if gas_speed <= a_throat:
            raise ValueError("La velocidad de los gases debe ser supersónica en la salida")
        if gas_speed >= max_allowed_speed:
            raise ValueError(f"La velocidad de los gases no puede superar Mach {max_exit_mach}")

        self.time = time
        self.ambient_pressure = ambient_pressure
        self.burn_time = burn_time
        self.nozzle_exit_diameter = nozzle_exit_diameter
        self._mass_flux_max = mass_flux_max
        self.gas_speed = gas_speed
        self.exit_pressure = exit_pressure
        
        # Área de salida de la tobera
        self.exit_area = np.pi * (self.nozzle_exit_diameter/2)**2

        self.length_chamber = length_chamber
        self.diameter_chamber = diameter_chamber
        self.chamber_volume = np.pi * (self.diameter_chamber / 2)**2 * self.length_chamber

        self.grain_outer_diameter = grain_outer_diameter
        self.grain_length = grain_length
        self.grain_inner_diameter = grain_inner_diameter
        self.N_grains = N_grains
        self.rho_grain = rho_grain
        self.rho_percentage = rho_percentage

        self.grain_volume_initial = np.pi * (self.grain_outer_diameter / 2)**2 * self.grain_length * self.N_grains - np.pi * (self.grain_inner_diameter / 2)**2 * self.grain_length * self.N_grains
        self.grain_mass_initial = self.grain_volume_initial * self.rho_grain * self.rho_percentage

        # Inicializar valores
        self._mass_flux = 0.0
        self._thrust = 0.0
        
        # Calcular valores iniciales
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
        """Calcula el rendimiento del motor basado en el tiempo actual"""
        # Inicializar valores
        self._mass_flux = 0.0
        self._thrust = 0.0
        
        # Calcular flujo másico durante el tiempo de operación
        if 0 <= self.time <= self.burn_time:
            if self.time < 0.1:  # Rampa de encendido
                ramp_factor = self.time/0.1
                self._mass_flux = self._mass_flux_max * ramp_factor
            elif self.time > (self.burn_time - 0.1):  # Rampa de apagado
                remaining_time = self.burn_time - self.time
                ramp_factor = remaining_time/0.1
                self._mass_flux = self._mass_flux_max * ramp_factor
            else:  # Operación nominal
                self._mass_flux = self._mass_flux_max
    
            # Asegurar límites del flujo másico y manejar valores muy pequeños
            self._mass_flux = max(0.0, min(self._mass_flux, self._mass_flux_max))
        
            # Usar un umbral más alto para el flujo másico en transiciones
            if self._mass_flux > 1e-3:  # Umbral aumentado para mejor transición
                momentum_thrust = self._mass_flux * self.gas_speed
                pressure_thrust = (self.exit_pressure - self.ambient_pressure) * self.exit_area
                self._thrust = momentum_thrust + pressure_thrust
            else:
                # En transiciones con flujo muy bajo, forzar todo a cero
                self._mass_flux = 0.0
                self._thrust = 0.0
        else:
            # Fuera del tiempo de operación, asegurar que todo sea cero
            self._mass_flux = 0.0
            self._thrust = 0.0

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
        
        # Recalcular el rendimiento con los nuevos valores
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
        g0 = 9.80665  # Aceleración gravitacional estándar [m/s²]
        
        # Usar la presión ambiente actual si no se especifica otra
        p_amb = self.ambient_pressure if ambient_pressure is None else ambient_pressure
        
        # Calcular el empuje para esta presión
        momentum_thrust = self._mass_flux * self.gas_speed
        pressure_thrust = (self.exit_pressure - p_amb) * self.exit_area
        total_thrust = momentum_thrust + pressure_thrust
        
        # Calcular el impulso específico
        if self._mass_flux > 0:
            return total_thrust / (self._mass_flux * g0)
        return 0.0

    @property
    def specific_impulse(self):
        """Impulso específico actual [s]"""
        return self.calculate_specific_impulse()

    @property
    def vacuum_specific_impulse(self):
        """Impulso específico en vacío [s]"""
        return self.calculate_specific_impulse(0.0)