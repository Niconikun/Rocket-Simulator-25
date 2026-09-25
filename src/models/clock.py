# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""
Clock Module

Contains:
    Clock object to calculate date related variables

External dependencies:
    numpy - Numpy Python extension. http://numpy.org/
    datetime - Datetime Library. https://docs.python.org/3/library/datetime.html

Internal dependencies:
    None

Changelog:
    Date          Name              Change
    15/08/2022    Jorge Orozco      Initial release

References:
    [Vall13]    Vallado/McClain,2013   Fundamentals of Astrodynamics and Applications
    [Schl17]    Schlyter,2017          TIMESCALES. https://stjarnhimlen.se/comp/time.html#deltat72p
"""

# Imports
from datetime import datetime, timezone, date, time
import numpy as np
from typing import Optional, Union, Tuple
import logging

from src.utils.simulation_constants import ClockConstants as CC
from src.utils.simulation_errors import InputValidationError

logger = logging.getLogger(__name__)


class Clock:
    """
    Clock class for time and date calculations.
    
    This class provides Julian day calculations, GMST (Greenwich Mean Sidereal Time),
    and current UTC time for astronomical and simulation purposes.
    
    Attributes:
        Delta_UT1: UT1 - UTC time difference [s]
        time_vector: Current time as numpy array [year, month, day, hour, minute, second]
        j_day: Current Julian day
    """
    
    def __init__(self) -> None:
        """
        Initialize Clock with current time.
        """
        self.Delta_UT1: float = 0.0  # [s]
        self.time_vector: np.ndarray = self._get_current_time()
        self.j_day: float = self.julian_day(self.time_vector)
        
        logger.debug(f"Clock initialized: JD={self.j_day:.2f}, UTC={self.time_vector}")
    
    def time_utc(self) -> np.ndarray:
        """
        Returns current UTC time vector with Delta_UT1 applied.
        
        Returns:
            numpy array: [year, month, day, hour, minute, second] with Delta_UT1 applied
        """
        time_vec: np.ndarray = self._get_current_time()
        
        # Apply Delta_UT1 only to seconds
        time_vec[5] = time_vec[5] + self.Delta_UT1
        
        # Handle second wraparound if necessary
        if time_vec[5] >= 60:
            time_vec[5] = time_vec[5] % 60
            time_vec[4] += 1  # Increment minutes
        
        return time_vec
    
    def julian_day(self, time_vector: np.ndarray) -> float:
        """
        Calculate Julian Day from time vector.
        
        Args:
            time_vector: numpy array [year, month, day, hour, minute, second]
            
        Returns:
            Julian Day number
            
        Raises:
            InputValidationError: If time_vector is not a 6-element array
        """
        if not isinstance(time_vector, np.ndarray) or time_vector.shape != (6,):
            raise InputValidationError("time_vector must be a 6-element numpy array [year, month, day, hour, minute, second]")
        
        j_day: float = (
            367 * time_vector[0] - int((7 * (time_vector[0] + int((time_vector[1] + 9) / 12))) / 4) +
            int((275 * time_vector[1]) / 9) + time_vector[2] + 1721013.5 +
            (((time_vector[5] / 60) + time_vector[4]) / 60 + time_vector[3]) / 24
        )
        
        return j_day
    
    def gmst(self, julian_day: float, rad_or_deg: int = 1) -> float:
        """
        Calculate Greenwich Mean Sidereal Time using Vallado's first Method.
        
        Args:
            julian_day: Julian Day number
            rad_or_deg: Output unit - 1 for radians, 2 for degrees
            
        Returns:
            GMST in requested units [rad or deg]
            
        Raises:
            InputValidationError: If rad_or_deg is not 1 or 2
        """
        if rad_or_deg not in (1, 2):
            raise InputValidationError(f"rad_or_deg must be 1 (radians) or 2 (degrees), got {rad_or_deg}")
        
        self.T_ut1: float = (julian_day - CC.JD_REFERENCE) / 36525
        self.Theta_GMST: float = (
            CC.GMST_COEFF_A + CC.GMST_COEFF_B * self.T_ut1 +
            CC.GMST_COEFF_C * (self.T_ut1 ** 2) + CC.GMST_COEFF_D * (self.T_ut1 ** 3)
        )
        self.GMST_leap: float = self.Theta_GMST - (int(self.Theta_GMST / CC.SECONDS_PER_DAY) * CC.SECONDS_PER_DAY)
        self.GMST_degrees: float = self.GMST_leap / 240
        
        # Correct angle for interval between 0° to 360°
        if self.GMST_degrees < 0:
            self.GMST_degrees += 360
        elif self.GMST_degrees > 360:
            self.GMST_degrees -= 360
        
        # Return in requested units
        if rad_or_deg == 2:
            return self.GMST_degrees
        else:
            return self.GMST_degrees * CC.DEG2RAD
    
    def _calculate_julian_day(self) -> float:
        """
        Internal method to calculate Julian Day from current time_vector.
        
        Returns:
            Julian Day number
        """
        self.j_day = (
            367 * self.time_vector[0] -
            int((7 * (self.time_vector[0] + int((self.time_vector[1] + 9) / 12))) / 4) +
            int((275 * self.time_vector[1]) / 9) + self.time_vector[2] + 1721013.5 +
            (((self.time_vector[5] / 60) + self.time_vector[4]) / 60 + self.time_vector[3]) / 24
        )
        return self.j_day
    
    def _get_current_time(self) -> np.ndarray:
        """
        Get current UTC time as numpy array.
        
        Returns:
            numpy array: [year, month, day, hour, minute, second.fraction]
        """
        current: datetime = datetime.now(timezone.utc)
        return np.array([
            current.year,
            current.month,
            current.day,
            current.hour,
            current.minute,
            current.second + current.microsecond / 1e6
        ])
