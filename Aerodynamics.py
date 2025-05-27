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

Internal dependencies:
cmath       -cMath Python extension. https://docs.python.org/3/library/cmath.html

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

"""
# Imports
from os import path


path
import numpy as np
from scipy import interpolate
from cmath import pi

# Auxiliary functions
deg2rad=pi/180
rad2deg=180/pi

class Aerodynamics(object):
    def __init__(self,mach,a):                          

        #______________________Drag Coefficient____________________________#
        
        # m= Mach number [-], [Valle22]      ## To be obtained from external file
        m = np.array([0.1,0.4,0.7,0.8,0.9,1,1.1,1.15,1.2,1.25,1.3,1.4,1.6,1.9,2.2,2.5,3])  
       
        # cd= Drag coefficient [-], [Valle22]    ## To be obtained from external file
        cd = np.array([0.32498,0.32302,0.32639,0.32957,0.34603,
                      0.45078,0.50512,0.525,0.55998,0.53465,0.51829,
                      0.50535,0.47411,0.42844,0.38992,0.3556,0.30924,])
  
        # Interpolation from data to create a curve function that describes cd behavior
        spline = interpolate.splrep(m, cd)           

        self.mach=mach     # [-]          # Mach number
        
        # Obtains cd from interpolation and given Mach number
        self.cd=interpolate.splev(self.mach, spline)  
       
        #_____________Lift Coefficient and Centre of Pressure_____________#
        
        # Angle of attack must be very close to zero degrees [Barro67]
        a_max=10              # [deg]    # Limit for angle of attack
        if abs(a)>=a_max:
            angle=a_max*((abs(a))/a)
        else:
            angle=a
    
        alpha=angle*deg2rad  # [rad]

        # Coefficient of normal force approximation for subsonic regime, [Box09] and [Barro67]   
        X_b=205.35            # [mm]     # Length of warhead or distance from tip of nose to base of nose
        X_f=856               # [mm]     # Length between nose cone tip and the point where the fin leading edge meets the body tube
        X_c=936               # [mm]     # Length between nose tip to rear
        
        l_n=205.35            # [mm]     # Length of warhead or distance from tip of nose to base of nose
        l_b=730               # [mm]     # Length of body tube (not considering rear)
        l_r=76.32             # [mm]     # Fins aerodynamic chord at root
        l_t=33.6722           # [mm]     # Fins aerodynamic chord at tip
        l_m=46.6440           # [mm]     # Fins aerodynamic mid-chord
        l_c=62                # [mm]     # Length of rear
        l_s=41.75             # [mm]     # Fins span

        d_n=88.9              # [mm]     # Diameter of base of warhead
        d_b=88.9              # [mm]     # Diameter of body tube
        d_f=88.9              # [mm]     # Diameter of body tube where fins are met
        d_u=88.9              # [mm]     # Diameter of rear where it meets body tube
        d_d=93                # [mm]     # Diameter of rear at the end
        
        fins=4                # [-]      # Number of fins

        # Cone [Box09]:
        Cn_alpha_cone=2       # [-]      # Normal force coefficient gradient for cone (warhead)
        Xcp_cone=0.466*l_n    # [mm]     # Centre of pressure of cone

        # Body, [Box09]:
        Cn_alpha_body=(l_b/(pi*0.25*d_b))*alpha            # [-]        # Normal force coefficient gradient for body tube
        Xcp_body=X_b + 0.5*l_b                             # [mm]       # Centre of pressure of body tube
        
        # Cn_alpha_body=2*alpha     # Fleeman's method for Rocket's body [Fleem01]
        # Xcp_body=X_b + 0.5*l_b    
        
        # Cn_alpha_body=0           # Box cites a previous version that doesn't consider body's effect on lift or normal force coefficient
        # Xcp_body=0
        
        # Tail, [Box09]:
        Cn_alpha_tail=2*(((d_d/d_n)**2) - ((d_u/d_n)**2))  # [-]        # Normal force coefficient gradient for rear 
        Xcp_tail= X_c + (l_c/3)* (1 + 1/(1+(d_u/d_n)))     # [mm]       # Centre of pressure of rear
        # Fins [Box09]:
        Kfb=1 + ((0.5*d_f)/(l_s + 0.5*d_f))                                                           # [-]     # Coefficient for interference effects between the fin and the body
        Cn_alpha_fins=(Kfb*4*fins)*(((l_s/d_n)**2)/(1 + (np.sqrt(1+(2*l_m/(l_r+l_t))**2))))           # [-]     # Normal force coefficient gradient for fins
        Xcp_fins= X_f+((l_m/3)*((l_r + 2*l_t)/(l_r+l_t)))+((1/6)*(l_r + l_t-((l_r*l_t)/(l_r+l_t))))   # [mm]    # Centre of pressure of fins
 
        # Results, [Box09]:
        Cn_sum=Cn_alpha_cone + Cn_alpha_body + Cn_alpha_tail + Cn_alpha_fins # [-]      # Sum of all coefficients gradients
        cn=Cn_sum*alpha                                                      # [-]      # Obtaining of rocket's normal force coefficient
    
        # Centre of pressure location from nose tip using [Box09]:
        xcp=((Cn_alpha_cone*Xcp_cone + Cn_alpha_body*Xcp_body + Cn_alpha_tail*Xcp_tail + Cn_alpha_fins*Xcp_fins)/Cn_sum)/1000  # [m]
        self.xcp=np.array([xcp,0,0])
        
        #Ketchledge correction, [Ketch92] and [Box09]
        if self.mach<=0.8:
            # Subsonic case
            self.cl=cn/(np.sqrt(1-(self.mach**2)))   # [-]

        elif self.mach>=0.8 and self.mach<=1.2:
            # Transonic case
            self.cl=cn/(np.sqrt(1-(0.8**2)))         # [-]

        else:
            # Supersonic case
            self.cl=cn/(np.sqrt(-1+(self.mach**2)))  # [-]

