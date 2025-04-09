# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""

*** Planet.py ***

Contains:
Module that updates Greenwich Mean Sidereal Time from simulation time

External dependencies:

Internal dependencies:
cmath       -cMath Python extension. https://docs.python.org/3/library/cmath.html

Changelog:
Date          Name              Change
__ _          __ _              ____ _
15/08/2022    Jorge Orozco      Initial release

References:
Short       Author,Year                 Title
___ _       _________ _                 ___ _
[Regan93]   Regan/Anandakrishnan,1993   Dynamics of Atmospheric Re-Entry

"""
# Imports
from cmath import pi

# Define Planet class for Planet module
class Planet(object):
    def __init__(self, gmst_0):
        'gmst_0= Initial Greenwich Mean Sidereal Time in [rad]'
        self.gmst=gmst_0    # [rad]

        # Earth rotation velocity, [Regan93]
        self.rotation_speed=7.2722*1e-5    # [rad/s]               
  
        # List to save data
        self.hist_gmst=[]          
    
    def update(self,dt):
        'Updates gmst value according to simulation current cycle. dt in [s]'

        self.gmst += self.rotation_speed*dt  # [rad]
        
        # Limits for gmst between 0 rad and 2pi rad
        self.gmst%=2*pi                     
    
    def save_data(self):
        'Saves current rotation in hist_gmst'

        self.hist_gmst.append(self.gmst)

    def give_gmst(self): 
        'Delivers gmst value in [rad]'

        return self.gmst    #[rad]

