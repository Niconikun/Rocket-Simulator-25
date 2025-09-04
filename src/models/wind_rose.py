# Author: AI Assistant
# Implementation of Wind Rose Model for Monte Carlo Rocket Simulation

"""
Wind Rose Model for Rocket Trajectory Simulation

This module provides a comprehensive wind model based on wind rose data,
which includes directional and seasonal patterns typical of atmospheric
wind conditions. The model supports altitude-dependent variations and
is designed for use in Monte Carlo simulations.

Classes:
    WindRose: Main wind rose model with directional and seasonal patterns
    AltitudeWindProfile: Altitude-dependent wind profile model
    WindRoseIntegrator: Integration with rocket simulation

References:
    [WMO2017] World Meteorological Organization - Guide to Meteorological Practices
    [NASA2012] NASA Technical Memorandum - Atmospheric Wind Models
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import json
from dataclasses import dataclass
from enum import Enum

class Season(Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"

@dataclass
class WindCondition:
    """Wind condition at a specific point in time and space"""
    speed: float  # [m/s]
    direction: float  # [degrees] from North (meteorological convention)
    altitude: float  # [m]
    gust_factor: float  # Multiplicative factor for gusts
    turbulence_intensity: float  # [0-1] turbulence level

class WindRose:
    """
    Wind Rose Model for directional and seasonal wind patterns.
    
    Based on typical wind rose data with 16 directional sectors and
    seasonal variations. Includes probability distributions for
    wind speed and direction.
    """
    
    def __init__(self, location_name: str = "generic"):
        """
        Initialize wind rose model.
        
        Args:
            location_name: Location identifier for specific wind patterns
        """
        self.location_name = location_name
        
        # 16 directional sectors (22.5° each)
        self.directions = np.arange(0, 360, 22.5)  # N, NNE, NE, ENE, E, etc.
        self.direction_names = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
        ]
        
        # Wind speed bins [m/s]
        self.speed_bins = np.array([0, 2, 4, 6, 8, 10, 12, 15, 20, 25, 30])
        
        # Initialize default wind rose data (typical mid-latitude patterns)
        self._initialize_default_wind_rose()
        
    def _initialize_default_wind_rose(self):
        """Initialize default wind rose patterns for different seasons"""
        
        # Seasonal wind frequency by direction (normalized probabilities)
        # Based on typical mid-latitude continental patterns
        self.seasonal_direction_freq = {
            Season.SPRING: np.array([
                0.08, 0.07, 0.06, 0.05, 0.04, 0.04, 0.05, 0.06,  # N to SSE
                0.08, 0.09, 0.10, 0.12, 0.14, 0.10, 0.08, 0.08   # S to NNW
            ]),
            Season.SUMMER: np.array([
                0.06, 0.05, 0.04, 0.04, 0.05, 0.06, 0.08, 0.09,  # N to SSE
                0.10, 0.11, 0.12, 0.11, 0.10, 0.08, 0.06, 0.05   # S to NNW
            ]),
            Season.AUTUMN: np.array([
                0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.05, 0.06,  # N to SSE
                0.07, 0.08, 0.09, 0.11, 0.13, 0.11, 0.09, 0.09   # S to NNW
            ]),
            Season.WINTER: np.array([
                0.10, 0.09, 0.08, 0.07, 0.05, 0.04, 0.04, 0.05,  # N to SSE
                0.06, 0.07, 0.08, 0.10, 0.15, 0.12, 0.11, 0.10   # S to NNW
            ])
        }
        
        # Normalize probabilities
        for season in Season:
            self.seasonal_direction_freq[season] /= np.sum(self.seasonal_direction_freq[season])
        
        # Wind speed distribution parameters by season and direction
        # Each contains [mean, std] for Weibull-like distribution
        self.speed_parameters = {
            season: {
                'mean_speeds': np.full(16, 6.0 + np.random.normal(0, 1.0, 16)),  # Base mean ~6 m/s
                'std_speeds': np.full(16, 2.5 + np.random.normal(0, 0.5, 16))    # Base std ~2.5 m/s
            }
            for season in Season
        }
        
        # Seasonal adjustments
        self.speed_parameters[Season.WINTER]['mean_speeds'] *= 1.2  # Higher winter speeds
        self.speed_parameters[Season.SUMMER]['mean_speeds'] *= 0.8  # Lower summer speeds
        
        # Calm probability (wind < 1 m/s) by season
        self.calm_probability = {
            Season.SPRING: 0.05,
            Season.SUMMER: 0.08,
            Season.AUTUMN: 0.06,
            Season.WINTER: 0.04
        }
        
    def get_wind_condition(self, season: Season, altitude: float = 0.0,
                          time_of_day: Optional[float] = None) -> WindCondition:
        """
        Generate a wind condition based on wind rose probabilities.
        
        Args:
            season: Current season
            altitude: Altitude above ground level [m]
            time_of_day: Hour of day [0-24] for diurnal variations
            
        Returns:
            WindCondition object with speed, direction, and other parameters
        """
        
        # Check for calm conditions
        if np.random.random() < self.calm_probability[season]:
            return WindCondition(
                speed=np.random.uniform(0, 1),
                direction=np.random.uniform(0, 360),
                altitude=altitude,
                gust_factor=1.1,
                turbulence_intensity=0.1
            )
        
        # Sample direction based on seasonal probabilities
        direction_idx = np.random.choice(
            len(self.directions),
            p=self.seasonal_direction_freq[season]
        )
        
        base_direction = self.directions[direction_idx]
        # Add random variation within sector (±11.25°)
        direction = base_direction + np.random.uniform(-11.25, 11.25)
        direction = direction % 360  # Ensure 0-360 range
        
        # Sample wind speed using Weibull-like distribution
        mean_speed = self.speed_parameters[season]['mean_speeds'][direction_idx]
        std_speed = self.speed_parameters[season]['std_speeds'][direction_idx]
        
        # Use lognormal distribution for realistic wind speed distribution
        speed = np.random.lognormal(
            mean=np.log(mean_speed) - 0.5 * np.log(1 + (std_speed/mean_speed)**2),
            sigma=np.sqrt(np.log(1 + (std_speed/mean_speed)**2))
        )
        
        # Apply altitude correction (wind increases with altitude)
        altitude_factor = self._get_altitude_factor(altitude)
        speed *= altitude_factor
        
        # Apply diurnal variation if time provided
        if time_of_day is not None:
            diurnal_factor = self._get_diurnal_factor(time_of_day)
            speed *= diurnal_factor
        
        # Calculate gust factor and turbulence
        gust_factor = self._calculate_gust_factor(speed, season)
        turbulence_intensity = self._calculate_turbulence_intensity(speed, altitude)
        
        return WindCondition(
            speed=max(0, speed),  # Ensure non-negative
            direction=direction,
            altitude=altitude,
            gust_factor=gust_factor,
            turbulence_intensity=turbulence_intensity
        )
    
    def _get_altitude_factor(self, altitude: float) -> float:
        """Calculate wind speed factor based on altitude using power law"""
        # Power law wind profile: V(z) = V_ref * (z/z_ref)^α
        # α typically 0.1-0.4, use 0.2 for open terrain
        z_ref = 10.0  # Reference height [m]
        alpha = 0.2   # Power law exponent
        
        if altitude <= 0:
            return 1.0
        
        factor = (max(altitude, 1.0) / z_ref) ** alpha
        return min(factor, 3.0)  # Cap at 3x surface wind
    
    def _get_diurnal_factor(self, time_of_day: float) -> float:
        """Calculate diurnal variation factor (0.8-1.2)"""
        # Peak winds typically in afternoon, minimum at night
        time_radians = 2 * np.pi * (time_of_day - 14) / 24  # Peak at 14:00
        factor = 1.0 + 0.2 * np.cos(time_radians)
        return factor
    
    def _calculate_gust_factor(self, mean_speed: float, season: Season) -> float:
        """Calculate gust factor based on mean wind speed and season"""
        # Higher gust factors for higher speeds and winter conditions
        base_gust = 1.3 + 0.02 * mean_speed
        
        seasonal_factor = {
            Season.SPRING: 1.1,
            Season.SUMMER: 0.9,
            Season.AUTUMN: 1.0,
            Season.WINTER: 1.2
        }
        
        return base_gust * seasonal_factor[season]
    
    def _calculate_turbulence_intensity(self, speed: float, altitude: float) -> float:
        """Calculate turbulence intensity [0-1]"""
        # Higher turbulence at low altitudes and low speeds
        if speed < 1:
            return 0.3
        
        altitude_factor = max(0.1, 1.0 - altitude / 1000.0)  # Decrease with altitude
        speed_factor = max(0.05, 0.3 / speed)  # Decrease with speed
        
        turbulence = altitude_factor * speed_factor
        return min(turbulence, 0.8)  # Cap at 0.8
    
    def get_seasonal_statistics(self, season: Season) -> Dict:
        """Get statistical summary of wind patterns for a season"""
        return {
            'direction_frequencies': self.seasonal_direction_freq[season],
            'direction_names': self.direction_names,
            'mean_speeds': self.speed_parameters[season]['mean_speeds'],
            'calm_probability': self.calm_probability[season],
            'dominant_direction': self.direction_names[
                np.argmax(self.seasonal_direction_freq[season])
            ]
        }
    
    def export_wind_rose_data(self, filename: str):
        """Export wind rose data to JSON file"""
        data = {
            'location': self.location_name,
            'directions': self.directions.tolist(),
            'direction_names': self.direction_names,
            'seasonal_data': {}
        }
        
        for season in Season:
            data['seasonal_data'][season.value] = {
                'direction_frequencies': self.seasonal_direction_freq[season].tolist(),
                'mean_speeds': self.speed_parameters[season]['mean_speeds'].tolist(),
                'std_speeds': self.speed_parameters[season]['std_speeds'].tolist(),
                'calm_probability': self.calm_probability[season]
            }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_wind_rose_data(self, filename: str):
        """Load wind rose data from JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        self.location_name = data['location']
        
        for season_str, season_data in data['seasonal_data'].items():
            season = Season(season_str)
            self.seasonal_direction_freq[season] = np.array(season_data['direction_frequencies'])
            self.speed_parameters[season] = {
                'mean_speeds': np.array(season_data['mean_speeds']),
                'std_speeds': np.array(season_data['std_speeds'])
            }
            self.calm_probability[season] = season_data['calm_probability']

class AltitudeWindProfile:
    """
    Models wind variation with altitude using atmospheric boundary layer theory.
    """
    
    def __init__(self):
        """Initialize altitude wind profile model"""
        self.surface_roughness = 0.1  # [m] typical for open terrain
        self.boundary_layer_height = 1000.0  # [m] typical boundary layer height
        
    def get_wind_at_altitude(self, surface_wind: WindCondition, 
                           target_altitude: float) -> WindCondition:
        """
        Calculate wind conditions at target altitude based on surface conditions.
        
        Args:
            surface_wind: Wind condition at surface/reference height
            target_altitude: Target altitude [m]
            
        Returns:
            WindCondition at target altitude
        """
        
        if target_altitude <= surface_wind.altitude:
            return surface_wind
        
        # Power law wind speed scaling
        altitude_factor = self._get_altitude_factor(
            surface_wind.altitude, target_altitude
        )
        
        # Direction backing/veering with altitude (typical 15° veering)
        altitude_km = target_altitude / 1000.0
        direction_change = 15.0 * (1 - np.exp(-altitude_km / 2.0))
        new_direction = (surface_wind.direction + direction_change) % 360
        
        # Reduced turbulence with altitude
        turbulence_factor = max(0.1, 1.0 - target_altitude / self.boundary_layer_height)
        new_turbulence = surface_wind.turbulence_intensity * turbulence_factor
        
        return WindCondition(
            speed=surface_wind.speed * altitude_factor,
            direction=new_direction,
            altitude=target_altitude,
            gust_factor=surface_wind.gust_factor * (1.0 + 0.1 * altitude_factor),
            turbulence_intensity=new_turbulence
        )
    
    def _get_altitude_factor(self, ref_altitude: float, target_altitude: float) -> float:
        """Calculate wind speed scaling factor with altitude"""
        # Power law: V(z) = V_ref * (z/z_ref)^α
        alpha = 0.2  # Power law exponent for open terrain
        
        ref_height = max(ref_altitude, 10.0)  # Minimum 10m reference
        target_height = max(target_altitude, ref_height)
        
        return (target_height / ref_height) ** alpha

class WindRoseIntegrator:
    """
    Integrates wind rose model with rocket trajectory simulation.
    """
    
    def __init__(self, wind_rose: WindRose, altitude_profile: AltitudeWindProfile):
        """
        Initialize wind rose integrator.
        
        Args:
            wind_rose: Wind rose model
            altitude_profile: Altitude wind profile model
        """
        self.wind_rose = wind_rose
        self.altitude_profile = altitude_profile
        
    def get_wind_for_trajectory(self, altitude: float, season: Season,
                              time_of_day: Optional[float] = None,
                              add_turbulence: bool = True) -> Tuple[float, float, float]:
        """
        Get wind vector components for trajectory integration.
        
        Args:
            altitude: Current altitude [m]
            season: Current season
            time_of_day: Hour of day [0-24]
            add_turbulence: Whether to add turbulent fluctuations
            
        Returns:
            Tuple of (wind_east, wind_north, wind_up) in [m/s]
        """
        
        # Get surface wind condition
        surface_wind = self.wind_rose.get_wind_condition(season, 0.0, time_of_day)
        
        # Scale to altitude
        wind_at_altitude = self.altitude_profile.get_wind_at_altitude(
            surface_wind, altitude
        )
        
        # Convert to ENU components
        speed = wind_at_altitude.speed
        direction_rad = np.radians(wind_at_altitude.direction)
        
        # Meteorological convention: direction is "from" north, clockwise
        # Convert to mathematical convention and ENU components
        wind_east = -speed * np.sin(direction_rad)   # Negative because "from" direction
        wind_north = -speed * np.cos(direction_rad)  # Negative because "from" direction
        wind_up = 0.0  # Typically negligible for horizontal wind
        
        # Add turbulent fluctuations if requested
        if add_turbulence:
            turbulence_std = speed * wind_at_altitude.turbulence_intensity
            wind_east += np.random.normal(0, turbulence_std)
            wind_north += np.random.normal(0, turbulence_std)
            wind_up += np.random.normal(0, turbulence_std * 0.1)  # Smaller vertical component
        
        # Add gust effects (random multiplier)
        if np.random.random() < 0.1:  # 10% chance of gust
            gust_multiplier = np.random.uniform(1.0, wind_at_altitude.gust_factor)
            wind_east *= gust_multiplier
            wind_north *= gust_multiplier
        
        return wind_east, wind_north, wind_up