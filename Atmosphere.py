# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""

*** Atmosphere.py ***

Contains:
Atmosphere module based on US Standard Atmosphere 1976 model

External dependencies:
fluids      -Fluids Library. https://github.com/CalebBell/fluids
             Version: fluids 1.0.21

Internal dependencies:

Changelog:
Date          Name              Change
__ _          __ _              ____ _
15/08/2022    Jorge Orozco      Initial release

References:
Short     Author,Year     Title
___ _     _________ _     ___ _
[USSA76]                  U.S Standard Atmosphere 1976. https://ntrs.nasa.gov/citations/19770009539

"""
# Imports
from fluids import ATMOSPHERE_1976 as atmos76

# Define class for atmosphere
class Atmosphere(object):
    def __init__(self,temp_sensed):
        """
        Creates atmosphere using US Standard Atmosphere 1976, [USSA76]...
        Starts with height [m] and measured temperature [°C]...
        Source: US Standard Atmosphere 1976
        """
        self.sea_level_temp=288.15                          # [K]   # Sea level temperature  given by [USSA76]
        self.temp_sensed=temp_sensed+273.15                 # [K]   # Transforms [°C] to [K]
        self.offset=self.temp_sensed -self.sea_level_temp   # [K]   # Temperature offset 

    def give_temp(self,height):
        'Gets temperature [K]'

        self.atmosphere=atmos76(height,self.offset) 
        return self.atmosphere.T

    def give_press(self,height):
        'Gets atmospheric pressure [Pa]'

        self.atmosphere=atmos76(height,self.offset) 
        return self.atmosphere.P

    def give_dens(self,height):
        'Gets density [kg/m3]'

        self.atmosphere=atmos76(height,self.offset)
        return self.atmosphere.rho
    
    def give_v_sonic(self,height):
        'Gets sound speed [m/s]'
        
        self.atmosphere=atmos76(height,self.offset)
        return self.atmosphere.v_sonic