# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""
Planet Module

Contains:
    Module that updates Greenwich Mean Sidereal Time from simulation time

External dependencies:
    None

Internal dependencies:
    math - Python math library

Changelog:
    Date          Name              Change
    15/08/2022    Jorge Orozco      Initial release

References:
    [Regan93]   Regan/Anandakrishnan,1993   Dynamics of Atmospheric Re-Entry
"""


# Imports
import math
from typing import List, Optional
import logging
from src.utils.simulation_constants import PlanetConstants as PC
from src.utils.simulation_errors import InputValidationError

logger = logging.getLogger(__name__)


# Use constants from PlanetConstants
EARTH_ROTATION_SPEED = PC.EARTH_ROTATION_SPEED
TWO_PI = PC.TWO_PI


class Planet:
    """
    Planet class for tracking Greenwich Mean Sidereal Time (GMST).
    
    This class simulates Earth's rotation and tracks the Greenwich Mean Sidereal Time
    which is used for astronomical calculations and coordinate transformations.
    
    Attributes:
        gmst: Current Greenwich Mean Sidereal Time [rad]
        rotation_speed: Earth rotation velocity [rad/s]
        hist_gmst: Historical list of GMST values [rad]
    """
    
    def __init__(self, gmst_0: float) -> None:
        """
        Initialize Planet with initial GMST value.
        
        Args:
            gmst_0: Initial Greenwich Mean Sidereal Time [rad]
            
        Raises:
            InputValidationError: If gmst_0 is negative
        """
        if gmst_0 < 0:
            raise InputValidationError(f"Initial GMST must be non-negative, got {gmst_0}")
        
        self.gmst: float = float(gmst_0)  # [rad]
        self.rotation_speed: float = EARTH_ROTATION_SPEED  # [rad/s]
        self.hist_gmst: List[float] = []
        
        logger.debug(f"Planet initialized with GMST={self.gmst:.4f} rad")
    
    def update(self, dt: float) -> None:
        """
        Updates GMST value according to simulation time step.
        
        Args:
            dt: Time step [s]
            
        Raises:
            InputValidationError: If dt is negative
        """
        if dt < 0:
            raise InputValidationError(f"Time step must be non-negative, got {dt}")
        
        self.gmst += self.rotation_speed * dt  # [rad]
        
        # Limit GMST between 0 and 2pi radians
        self.gmst %= TWO_PI
        
        logger.debug(f"GMST updated to {self.gmst:.4f} rad")
    
    def save_data(self) -> None:
        """
        Saves current GMST value to history.
        """
        self.hist_gmst.append(self.gmst)
        logger.debug(f"GMST saved to history, total entries: {len(self.hist_gmst)}")
    
    def give_gmst(self) -> float:
        """
        Returns current GMST value.
        
        Returns:
            Current Greenwich Mean Sidereal Time [rad]
        """
        return self.gmst
