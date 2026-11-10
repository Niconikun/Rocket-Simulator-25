# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""
Atmosphere Module

Provides atmospheric property calculations based on the US Standard Atmosphere 1976 model.

This module calculates temperature, pressure, density, and speed of sound at various
altitudes, using the internationally recognized USSA76 standard.

External dependencies:
    fluids - Fluids Library. https://github.com/CalebBell/fluids
              Version: fluids 1.0.21

Changelog:
    Date          Name              Change
    __ _          __ _              ____ _
    15/08/2022    Jorge Orozco      Initial release

References:
    [USSA76] U.S Standard Atmosphere 1976. https://ntrs.nasa.gov/citations/19770009539

Examples:
    >>> from src.models.atmosphere import Atmosphere
    >>> atmos = Atmosphere(15.0)  # 15°C at sea level
    >>> temp = atmos.give_temp(1000)  # Temperature at 1000m
    >>> press = atmos.give_press(1000)  # Pressure at 1000m
    >>> dens = atmos.give_dens(1000)  # Density at 1000m
    >>> v_sonic = atmos.give_v_sonic(1000)  # Speed of sound at 1000m
"""

# Imports
from __future__ import annotations
from typing import Any
import logging
import numpy as np
from functools import lru_cache

logger = logging.getLogger(__name__)

from fluids.atmosphere import ATMOSPHERE_1976 as atmos76
from src.models.interfaces import IAtmosphere

class Atmosphere(IAtmosphere):
    """
    Atmospheric model based on US Standard Atmosphere 1976.
    
    Implements IAtmosphere interface for dependency injection and loose coupling.
    
    This class provides atmospheric property calculations (temperature, pressure,
    density, speed of sound) at various altitudes, with support for temperature
    offsets from standard conditions.
    
    The US Standard Atmosphere 1976 model divides the atmosphere into layers with
    different temperature gradients, providing accurate properties for altitudes
    from sea level to the edge of space.
    
    Attributes:
        sea_level_temp: Standard temperature at sea level [K]
        temp_sensed: Measured temperature converted to Kelvin [K]
        offset: Temperature offset from standard [K]
    
    Examples:
        >>> # Create atmosphere with standard conditions (15°C at sea level)
        >>> atmos = Atmosphere(15.0)
        >>> 
        >>> # Get properties at different altitudes
        >>> temp_0 = atmos.give_temp(0)      # ~288.15 K at sea level
        >>> press_0 = atmos.give_press(0)    # ~101325 Pa at sea level
        >>> dens_0 = atmos.give_dens(0)      # ~1.225 kg/m³ at sea level
    """
    
    def __init__(self, temp_sensed: float) -> None:
        """
        Initialize Atmosphere model with measured temperature.
        
        Args:
            temp_sensed: Measured temperature at reference location [°C].
                         This is used to calculate the temperature offset from
                         the standard atmosphere model.
        
        Raises:
            TypeError: If temp_sensed is not a number
        """
        if not isinstance(temp_sensed, (int, float)):
            raise TypeError(f"temp_sensed must be a number, got {type(temp_sensed).__name__}")
        
        self.sea_level_temp: float = 288.15  # [K] Sea level temperature (USSA76)
        self.temp_sensed: float = temp_sensed + 273.15  # [K] Convert °C to K
        self.offset: float = self.temp_sensed - self.sea_level_temp  # [K] Temperature offset

    @staticmethod
    @lru_cache(maxsize=128)
    def _get_atmosphere_data(height: float, offset: float) -> Any:
        """
        Get atmosphere data from US Standard Atmosphere 1976 model with caching.
        
        This static method is cached to avoid repeated calculations for the same
        height and offset values, improving performance in simulations with
        many atmospheric property lookups.
        
        Args:
            height: Altitude above sea level [m]
            offset: Temperature offset from standard [K]
        
        Returns:
            Fluids Atmosphere object with temperature, pressure, and density properties
        """
        return atmos76(height, offset)
    
    def give_temp(self, height: float) -> float:
        """
        Get atmospheric temperature at a given height.
        
        Uses US Standard Atmosphere 1976 model for consistency with pressure and density
        calculations. This ensures physical consistency across all atmospheric properties.
        
        Args:
            height: Altitude above sea level [m]. Must be non-negative.
        
        Returns:
            Temperature [K]
        
        Raises:
            TypeError: If height is not a number
        
        Examples:
            >>> atmos = Atmosphere(15.0)
            >>> atmos.give_temp(0)    # ~288.15 K (sea level)
            >>> atmos.give_temp(1000) # ~281.65 K (1000m altitude)
        """
        if not isinstance(height, (int, float)):
            raise TypeError(f"height must be a number, got {type(height).__name__}")
        
        self.atmosphere = self._get_atmosphere_data(float(height), self.offset)
        return float(self.atmosphere.T)

    def give_pressure(self, height: float) -> float:
        """
        Get atmospheric pressure at a given height.
        
        Uses US Standard Atmosphere 1976 model, consistent with give_temp(),
        give_dens(), and give_v_sonic() methods.
        
        This is the primary method for pressure retrieval. The give_press() method
        is maintained for backward compatibility.
        
        Args:
            height: Altitude above sea level [m]. Must be non-negative.
        
        Returns:
            Pressure [Pa]
        
        Raises:
            TypeError: If height is not a number
        
        Examples:
            >>> atmos = Atmosphere(15.0)
            >>> atmos.give_pressure(0)    # ~101325 Pa (sea level)
            >>> atmos.give_pressure(1000) # ~89876 Pa (1000m altitude)
        """
        if not isinstance(height, (int, float)):
            raise TypeError(f"height must be a number, got {type(height).__name__}")
        
        self.atmosphere = self._get_atmosphere_data(float(height), self.offset)
        return float(self.atmosphere.P)
    
    def give_press(self, height: float) -> float:
        """
        Get atmospheric pressure at a given height.
        
        DEPRECATED: Use give_pressure() instead. This method is maintained for
        backward compatibility only.
        
        Args:
            height: Altitude above sea level [m]. Must be non-negative.
        
        Returns:
            Pressure [Pa]
        
        Raises:
            TypeError: If height is not a number
        
        Examples:
            >>> atmos = Atmosphere(15.0)
            >>> atmos.give_press(0)    # ~101325 Pa (sea level)
            >>> atmos.give_press(1000) # ~89876 Pa (1000m altitude)
        """
        import warnings
        warnings.warn(
            "give_press() is deprecated, use give_pressure() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return self.give_pressure(height)

    def give_dens(self, height: float) -> float:
        """
        Get atmospheric density at a given height.
        
        Uses US Standard Atmosphere 1976 model, consistent with give_temp(),
        give_pressure(), and give_v_sonic() methods.
        
        Args:
            height: Altitude above sea level [m]. Must be non-negative.
        
        Returns:
            Density [kg/m³]
        
        Raises:
            TypeError: If height is not a number
        
        Examples:
            >>> atmos = Atmosphere(15.0)
            >>> atmos.give_dens(0)    # ~1.225 kg/m³ (sea level)
            >>> atmos.give_dens(1000) # ~1.112 kg/m³ (1000m altitude)
        """
        if not isinstance(height, (int, float)):
            raise TypeError(f"height must be a number, got {type(height).__name__}")
        
        self.atmosphere = self._get_atmosphere_data(float(height), self.offset)
        return float(self.atmosphere.rho)
    
    def give_v_sonic(self, height: float) -> float:
        """
        Calculate the speed of sound at a given height.
        
        The speed of sound is calculated using the formula:
            v_sonic = sqrt(gamma * R * temperature)
        where gamma is the heat capacity ratio (1.4 for air) and R is the
        specific gas constant for air (287.058 J/(kg·K)).
        
        Args:
            height: Altitude above sea level [m]. Must be non-negative.
        
        Returns:
            Speed of sound [m/s]
        
        Raises:
            TypeError: If height is not a number
        
        Examples:
            >>> atmos = Atmosphere(15.0)
            >>> atmos.give_v_sonic(0)    # ~340.0 m/s (sea level)
            >>> atmos.give_v_sonic(1000) # ~336.4 m/s (1000m altitude)
        """
        if not isinstance(height, (int, float)):
            raise TypeError(f"height must be a number, got {type(height).__name__}")
        
        gamma: float = 1.4  # Heat capacity ratio for air [-]
        R: float = 287.058  # Specific gas constant for air [J/(kg·K)]
        temp: float = self.give_temp(float(height))
        
        return float(np.sqrt(gamma * R * temp))
    

