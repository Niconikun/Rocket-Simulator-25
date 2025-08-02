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
import numpy as np
from src.utils.mattools import MatTools as Mat

def g_accel(r_eci):
    """
    Calcula la aceleración gravitacional.
    
    Args:
        r_eci (np.ndarray): Vector posición en ECI [m]
    
    Returns:
        np.ndarray: Vector aceleración gravitacional [m/s²]
    """
    mu = 3.986004418e14  # Constante gravitacional de la Tierra [m³/s²]
    r_mag = np.linalg.norm(r_eci)
    return -mu * r_eci / (r_mag**3)

def g_torque(r_ecef, inertia, q_ecef_body):
    """
    Calcula el torque gravitacional.
    
    Args:
        r_ecef (np.ndarray): Vector posición en ECEF [m]
        inertia (np.ndarray): Vector de momentos de inercia principales [kg·m²]
        q_ecef_body (np.ndarray): Cuaternión de rotación ECEF a body
    
    Returns:
        np.ndarray: Vector torque gravitacional [N·m]
    """
    mu = 3.986004418e14  # Constante gravitacional de la Tierra [m³/s²]
    r_mag = np.linalg.norm(r_ecef)
    
    # Convertir vector posición a coordenadas del cuerpo
    r_body = Mat.q_rot(r_ecef, q_ecef_body, 0)
    r_body_unit = Mat.normalise(r_body)
    
    # Calcular diferencias de momentos de inercia
    I_diff = np.array([
        inertia[1] - inertia[2],
        inertia[2] - inertia[0],
        inertia[0] - inertia[1]
    ])
    
    # Calcular componentes del torque usando la fórmula del gradiente gravitacional
    torque = (3 * mu / (2 * r_mag**3)) * np.array([
        I_diff[0] * r_body_unit[1] * r_body_unit[2],
        I_diff[1] * r_body_unit[2] * r_body_unit[0],
        I_diff[2] * r_body_unit[0] * r_body_unit[1]
    ])
    
    return torque
