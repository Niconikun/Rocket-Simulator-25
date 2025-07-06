# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""

*** Engine.py ***

Contains:
Engine module containing performance parameters.

External dependencies:

Internal dependencies:
cmath       -cMath Python extension. https://docs.python.org/3/library/cmath.html

Changelog:
Date          Name              Change
__ _          __ _              ____ _
15/08/2022    Jorge Orozco      Initial release

References:
Short      Author,Year     Title
___ _      _________ _     ___ _
[Valle22]  Vallejos,2022   Mejora del alcance de un cohete chaff

"""
# Imports
from cmath import pi

# Define Engine class for Engine module. Data given by [Valle22]  # All data SHOULD be obtained from external file
class Engine(object):
    def __init__(self,sim_time,press_amb, burn_time, nozzle_exit_diameter, mass_flux, gas_speed, exit_pressure):  
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