# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""

*** Gravitational.py ***

Contains:
Functions to obtain gravitational acceleration and torque

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
import logging
from src.utils.mattools import MatTools as Mat
from src.utils.simulation_constants import GravitationalConstants as GC

# Use constants from GravitationalConstants
MU_EARTH = GC.MU_EARTH
EARTH_MIN_RADIUS = GC.EARTH_MIN_RADIUS

logger = logging.getLogger(__name__)


def g_accel(r_eci):
    """
    Calculate gravitational acceleration.
    
    Args:
        r_eci (np.ndarray): Position vector in ECI frame [m]
        
    Returns:
        np.ndarray: Gravitational acceleration vector [m/s²]
        
    Raises:
        ValueError: If r_eci is not a 3-element array or has invalid values
    """
    # Validate input
    if not isinstance(r_eci, np.ndarray):
        raise ValueError(f"r_eci must be a numpy array, got {type(r_eci).__name__}")
    
    if r_eci.shape != (3,):
        raise ValueError(f"r_eci must be a 3-element array, got shape {r_eci.shape}")
    
    if not np.all(np.isfinite(r_eci)):
        raise ValueError(f"r_eci contains non-finite values: {r_eci}")
    
    r_mag = np.linalg.norm(r_eci)
    
    # Warn if position is unusually small (inside Earth)
    if r_mag < EARTH_MIN_RADIUS:
        logger.warning(f"Unusually small position magnitude: {r_mag:.2e}m (less than Earth radius)")
    
    # Avoid division by zero
    if r_mag == 0:
        logger.error("Position magnitude is zero - cannot calculate gravitational acceleration")
        return np.zeros(3)
    
    return -MU_EARTH * r_eci / (r_mag**3)


def g_torque(r_ecef, inertia, q_ecef_body):
    """
    Calculate gravitational gradient torque.
    
    Args:
        r_ecef (np.ndarray): Position vector in ECEF frame [m]
        inertia (np.ndarray): Principal moments of inertia [Ixx, Iyy, Izz] [kg·m²]
        q_ecef_body (np.ndarray): Quaternion for ECEF to body rotation [-]
        
    Returns:
        np.ndarray: Gravitational torque vector [N·m]
        
    Raises:
        ValueError: If inputs are invalid (wrong shape, non-finite values, etc.)
    """
    # Validate r_ecef
    if not isinstance(r_ecef, np.ndarray):
        raise ValueError(f"r_ecef must be a numpy array, got {type(r_ecef).__name__}")
    
    if r_ecef.shape != (3,):
        raise ValueError(f"r_ecef must be a 3-element array, got shape {r_ecef.shape}")
    
    if not np.all(np.isfinite(r_ecef)):
        raise ValueError(f"r_ecef contains non-finite values: {r_ecef}")
    
    # Validate inertia
    if not isinstance(inertia, np.ndarray):
        raise ValueError(f"inertia must be a numpy array, got {type(inertia).__name__}")
    
    if inertia.shape != (3,):
        raise ValueError(f"inertia must be a 3-element array, got shape {inertia.shape}")
    
    if not np.all(np.isfinite(inertia)):
        raise ValueError(f"inertia contains non-finite values: {inertia}")
    
    if np.any(inertia < 0):
        raise ValueError(f"inertia values must be non-negative, got {inertia}")
    
    # Validate quaternion
    if not isinstance(q_ecef_body, np.ndarray):
        raise ValueError(f"q_ecef_body must be a numpy array, got {type(q_ecef_body).__name__}")
    
    if q_ecef_body.shape != (4,):
        raise ValueError(f"q_ecef_body must be a 4-element array (quaternion), got shape {q_ecef_body.shape}")
    
    if not np.all(np.isfinite(q_ecef_body)):
        raise ValueError(f"q_ecef_body contains non-finite values: {q_ecef_body}")
    
    r_mag = np.linalg.norm(r_ecef)
    
    # Warn if position is unusually small
    if r_mag < EARTH_MIN_RADIUS:
        logger.warning(f"Unusually small position magnitude: {r_mag:.2e}m (less than Earth radius)")
    
    # Avoid division by zero
    if r_mag == 0:
        logger.error("Position magnitude is zero - cannot calculate gravitational torque")
        return np.zeros(3)
    
    # Convert position vector to body coordinates
    r_body = Mat.q_rot(r_ecef, q_ecef_body, 0)
    r_body_unit = Mat.normalise(r_body)
    
    # Calculate inertia differences
    I_diff = np.array([
        inertia[1] - inertia[2],
        inertia[2] - inertia[0],
        inertia[0] - inertia[1]
    ])
    
    # Calculate torque components using gravitational gradient formula
    torque = (3 * MU_EARTH / (2 * r_mag**3)) * np.array([
        I_diff[0] * r_body_unit[1] * r_body_unit[2],
        I_diff[1] * r_body_unit[2] * r_body_unit[0],
        I_diff[2] * r_body_unit[0] * r_body_unit[1]
    ])
    
    return torque
