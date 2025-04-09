# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""

*** Gravitational.py ***

Contains:
Functions to obtain gravitational acceleration

External dependencies:
MatTools    -Self-written python module containing mathematical functions

Internal dependencies:

Changelog:
Date          Name              Change
__ _          __ _              ____ _
02/06/2022    Jorge Orozco      Initial release
25/06/2022    Jorge Orozco      Adds gravitational gradient torque

References:
Short       Author,Year                     Title
___ _       _________ _                     ___ _
[Curt20]    Curtis,2020                     Orbital Mechanics for Engineering Students
[Regan93]   Regan/Anandakrishnan,1993       Dynamics of Atmospheric Re-Entry

"""
# Imports
import MatTools as Mat
import numpy as np

mass_earth=5.972*(10**24)              # Mass of the Earth                 [kg]          [Regan93]
univers_constant=6.67384*(10**(-11))   # Universal gravitational constant  [N (kg2/m2)]  [Regan93]

def g_accel(r_eci):
    """
    Function for gravitational acceleration with constant magnitude, [Curt20]
    """
    # Unit vector for current position in Earth Centered Inertial
    norm=Mat.normalise(r_eci) # [-]
    
    # Gravitational acceleration with constant magnitude
    g=-9.81*norm              # [m/s2]
    
    return g

def g_torque(r_ecef,inertia,q_ecef_body):
    """
    Function for torque due to gravitational gradient, [Regan93]
    """
    # Inertia vector conversion to matrix
    j=Mat.vec2mat(inertia)  # [kg m2]                                           

    # Position of Rocket in Earth Centered-Earth Fixed but in bodyframe
    r_ecef_b=Mat.q_rot(r_ecef,q_ecef_body,0)  # [m]
    r=np.linalg.norm(r_ecef)                  # [m]
    
    # Gravitational gradient torque calculation
    torque_gg_b=(-3*mass_earth*univers_constant/(r**5))*np.cross(r_ecef_b,(np.dot(j,r_ecef_b))) # [N m]
   
    return torque_gg_b
