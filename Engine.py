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

# Define Engine class for Engine module. Data given by [Valle22]  # All data SHOULD be obtained from external file
class Engine(object):
    """
    Clase para simular el comportamiento del motor cohete.

    Esta clase calcula el empuje y flujo másico del motor basándose en:
    - Tiempo de quemado
    - Presión atmosférica
    - Geometría de la tobera
    - Características del propelente

    Atributos:
        thrust (float): Empuje actual [N]
        mass_flux (float): Flujo másico actual [kg/s]
        burn_time (float): Tiempo total de quemado [s]
    """

    def __init__(self,sim_time,press_amb, burn_time, nozzle_exit_diameter, mass_flux, gas_speed, exit_pressure):
        """
        Inicializa un nuevo objeto Engine.

        Args:
            time (float): Tiempo actual de simulación [s]
            ambient_pressure (float): Presión atmosférica [Pa]
            burn_time (float): Tiempo total de quemado [s]
            nozzle_exit_diameter (float): Diámetro de salida de la tobera [m]
            mass_flux (float): Flujo másico nominal [kg/s]
            gas_speed (float): Velocidad de los gases de escape [m/s]
            exit_pressure (float): Presión en la salida de la tobera [Pa]
        """  
        self.sim_time=sim_time           # [s]    # Current simulation time
        self.area_exit=((nozzle_exit_diameter/2)**2)*pi   # [m2]   # Nozzle exit area
        self.press_amb=press_amb         # [Pa]   # Current environment pressure
        
        self.burn_time=burn_time              # [s]    # Total propellant burn time

        if self.sim_time==0 or self.sim_time>=self.burn_time:
            
            self.mass_flux=0            # [kg/s]      
            self.gas_speed=0            # [m/s]
            self.press_exit=0           # [Pa]
            self.thrust=0               # [N]
        else:                                   
            self.mass_flux=mass_flux        # [kg/s]
            self.gas_speed=gas_speed         # [m/s]
            self.press_exit=exit_pressure   # [Pa]   ## 1.86037 [bar] to be used in external files
            self.thrust=self.mass_flux*self.gas_speed + (self.press_exit-self.press_amb)*self.area_exit   #[N] 
            
            
            #self.thrust=2600    #[N]   # Thrust according to data provided by FAMAE