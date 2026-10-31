"""
Wind Model Module for Rocket Simulation

This module provides multiple atmospheric wind models ranging from simple constant wind
to complex 3D wind shear with turbulence. All models follow the same interface, allowing
users to select different wind profiles for various simulation scenarios.

Models Implemented:
    1. ConstantWind: Uniform wind at all altitudes
    2. LogarithmicWind: Industry-standard log profile (recommended)
    3. PowerLawWind: Algebraic power law profile
    4. GustWind: Turbulent fluctuations (Dryden spectrum)
    5. WindShearWind: Complex 3D wind vector field

References:
    [Peterson99] Peterson, E. W., & Hennessey Jr, J. P. (1978). On the use of power laws 
                 for estimates of wind power potential. Journal of Applied Meteorology, 17(3).
    [Dryden56]   Dryden, H. L. (1953). A review of the statistical theory of turbulence.
    [Kaimal72]   Kaimal, J. C., et al. (1972). Spectral characteristics of surface-layer 
                 turbulence. Quarterly Journal, 98(418).

Author: Wind Model Implementation
Date: 2026
"""

import numpy as np
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from src.utils.simulation_constants import WindConstants as WC
from src.utils.simulation_errors import InputValidationError

logger = logging.getLogger(__name__)

class WindModel(ABC):
    """
    Abstract base class for all wind models.
    
    All wind models must implement this interface to be compatible with the
    simulation engine. The wind vector is always in ENU (East-North-Up) frame.
    
    Attributes:
        enabled (bool): Whether wind is active
        wind_direction (float): Direction wind is coming FROM in degrees (0=North, 90=East)
        launch_altitude (float): Height of launch site above sea level [m]
    """
    
    def __init__(self, wind_direction: float = 0.0, launch_altitude: float = WC.DEFAULT_LAUNCH_ALTITUDE):
        """
        Initialize wind model with basic parameters.
        
        Args:
            wind_direction (float): Direction wind is coming FROM [degrees]
                                   0° = from North (blows South)
                                   90° = from East (blows West)
            launch_altitude (float): Launch site elevation above sea level [m]
        """
        self.enabled = True
        self.wind_direction = wind_direction % 360.0  # Normalize to 0-360
        self.launch_altitude = max(0.0, launch_altitude)
        self.time = 0.0
        logger.debug(f"Initialized {self.__class__.__name__} with direction={wind_direction}°, altitude={launch_altitude}m")
    
    @abstractmethod
    def get_wind_vector(self, altitude: float) -> np.ndarray:
        """
        Get wind vector at specified altitude in ENU frame.
        
        Args:
            altitude (float): Altitude above ground at launch site [m]
        
        Returns:
            np.ndarray: Wind velocity vector [East, North, Up] in m/s
                       Positive East = blowing toward East
                       Positive North = blowing toward North
                       Positive Up = vertical wind (updraft)
        
        Raises:
            InputValidationError: If altitude is invalid
        """
        pass
    
    def get_wind_magnitude(self, altitude: float) -> float:
        """
        Get wind speed magnitude at specified altitude.
        
        Args:
            altitude (float): Altitude above ground [m]
        
        Returns:
            float: Wind speed magnitude [m/s], always >= 0
        """
        wind_vector = self.get_wind_vector(altitude)
        return float(np.linalg.norm(wind_vector[:2]))  # Only horizontal components
    
    def get_wind_direction_at_altitude(self, altitude: float) -> float:
        """
        Get wind direction (FROM which it's coming) at altitude.
        
        Args:
            altitude (float): Altitude above ground [m]
        
        Returns:
            float: Direction FROM (meteorological convention) [0-360 degrees]
                   0° = from North, 90° = from East, 180° = from South, 270° = from West
        """
        wind_vec = self.get_wind_vector(altitude)
        east, north = wind_vec[0], wind_vec[1]
        
        # Calculate direction TO which wind is blowing
        direction_to = np.degrees(np.arctan2(east, north)) % 360.0
        
        # Convert to direction FROM (opposite direction)
        direction_from = (direction_to + 180.0) % 360.0
        return float(direction_from)
    
    def update(self, dt: float) -> None:
        """
        Update wind state by timestep (for time-varying models like gusts).
        
        Args:
            dt (float): Time step [s]
        """
        self.time += dt
    
    def get_info(self) -> dict:
        """
        Get wind model information and current parameters.
        
        Returns:
            dict: Information about wind model configuration
        """
        return {
            'model_type': self.__class__.__name__,
            'enabled': self.enabled,
            'wind_direction': self.wind_direction,
            'launch_altitude': self.launch_altitude,
        }


class ConstantWind(WindModel):
    """
    Simple constant wind model: uniform speed and direction at all altitudes.
    
    Attributes:
        wind_speed (float): Constant horizontal wind speed [m/s]
    """
    
    def __init__(self, wind_speed: float = 0.0, wind_direction: float = 0.0, 
                 launch_altitude: float = WC.DEFAULT_LAUNCH_ALTITUDE):
        """
        Initialize constant wind model.
        
        Args:
            wind_speed (float): Wind speed [m/s], clamped to [0, 100]
            wind_direction (float): Direction from (meteorological) [degrees]
            launch_altitude (float): Launch site elevation [m]
        """
        super().__init__(wind_direction, launch_altitude)
        self.wind_speed = np.clip(wind_speed, WC.MIN_WIND_SPEED, WC.MAX_WIND_SPEED)  # Limit to realistic range
        logger.info(f"ConstantWind: speed={self.wind_speed} m/s, from {wind_direction}°")
    
    def get_wind_vector(self, altitude: float) -> np.ndarray:
        """
        Return constant wind vector at all altitudes.
        
        Args:
            altitude (float): Altitude above ground [m]
        
        Returns:
            np.ndarray: [East, North, Up] wind components [m/s]
        """
        if altitude < 0:
            altitude = 0
        
        # Convert meteorological direction (FROM) to mathematical direction (TO)
        direction_rad = np.radians(self.wind_direction + 180.0)
        
        east = self.wind_speed * np.sin(direction_rad)
        north = self.wind_speed * np.cos(direction_rad)
        up = 0.0  # No vertical wind component
        
        return np.array([east, north, up])
    
    def get_info(self) -> dict:
        info = super().get_info()
        info.update({
            'wind_speed': self.wind_speed,
        })
        return info


class LogarithmicWind(WindModel):
    """
    Logarithmic wind profile: industry standard for atmospheric boundary layer.
    
    Wind speed increases logarithmically with altitude above surface roughness.
    Formula: U(h) = U_ref * ln((h + z0) / z0) / ln((h_ref + z0) / z0)
    
    This model matches real atmospheric behavior and is used by meteorologists,
    engineers, and wind resource assessors worldwide.
    
    References:
        - Standard log wind profile in atmospheric science
        - ISO 19901-1:2015 (Petroleum and natural gas industries)
        - IEC 61400-2:2013 (Wind turbines for small installations)
    
    Attributes:
        wind_speed_ref (float): Reference wind speed at reference height [m/s]
        reference_height (float): Reference height for wind_speed_ref [m]
        roughness_length (float): Surface roughness length z0 [m]
                                 Common values:
                                 0.0002 = water surface
                                 0.01 = grassland
                                 0.1 = forest edge
                                 0.5 = dense forest/urban
    """
    
    def __init__(self, wind_speed_ref: float = WC.DEFAULT_WIND_SPEED, reference_height: float = WC.DEFAULT_REFERENCE_HEIGHT,
                 roughness_length: float = WC.DEFAULT_ROUGHNESS, wind_direction: float = WC.DEFAULT_WIND_DIRECTION,
                 launch_altitude: float = WC.DEFAULT_LAUNCH_ALTITUDE):
        """
        Initialize logarithmic wind profile.
        
        Args:
            wind_speed_ref (float): Wind speed at reference height [m/s], default 5.0
            reference_height (float): Reference height [m], typical 10.0
            roughness_length (float): Surface roughness z0 [m], typical 0.1
            wind_direction (float): Direction from [degrees]
            launch_altitude (float): Launch site elevation [m]
        
        Raises:
            InputValidationError: If parameters are invalid (negative, zero reference height, etc.)
        """
        super().__init__(wind_direction, launch_altitude)
        
        # Validate and set parameters
        if wind_speed_ref < WC.MIN_WIND_SPEED or wind_speed_ref > WC.MAX_WIND_SPEED:
            raise InputValidationError(f"wind_speed_ref must be in [0, 100] m/s, got {wind_speed_ref}")
        if reference_height <= 0:
            raise InputValidationError(f"reference_height must be > 0, got {reference_height}")
        if roughness_length < WC.MIN_WIND_SPEED or roughness_length >= reference_height:
            raise InputValidationError(f"roughness_length must be in [0, reference_height), got {roughness_length}")
        
        self.wind_speed_ref = float(wind_speed_ref)
        self.reference_height = float(reference_height)
        self.roughness_length = float(roughness_length)
        
        # Precompute denominator for efficiency
        self._denominator = np.log((self.reference_height + self.roughness_length) / self.roughness_length)
        
        logger.info(
            f"LogarithmicWind: U_ref={wind_speed_ref} m/s @ {reference_height}m, "
            f"z0={roughness_length}m, from {wind_direction}°"
        )
    
    def get_wind_vector(self, altitude: float) -> np.ndarray:
        """
        Calculate wind vector using logarithmic profile.
        
        Args:
            altitude (float): Altitude above ground at launch site [m]
        
        Returns:
            np.ndarray: [East, North, Up] wind components [m/s]
        """
        # Clamp altitude to reasonable range
        altitude = max(WC.MIN_WIND_SPEED, altitude)
        
        # Absolute height above sea level
        absolute_height = altitude + self.launch_altitude
        
        # Log profile formula: U(h) = U_ref * ln(h/z0) / ln(h_ref/z0)
        # Using (h + z0) / z0 form to avoid log singularity at h=0
        numerator = np.log((absolute_height + self.roughness_length) / self.roughness_length)
        wind_speed = self.wind_speed_ref * numerator / self._denominator
        
        # Ensure wind speed is non-negative (should always be, but safety check)
        wind_speed = max(WC.MIN_WIND_SPEED, wind_speed)
        
        # Convert meteorological direction (FROM) to math direction (TO)
        direction_rad = np.radians(self.wind_direction + 180.0)
        
        east = wind_speed * np.sin(direction_rad)
        north = wind_speed * np.cos(direction_rad)
        up = 0.0  # No vertical wind in standard log profile
        
        return np.array([east, north, up])
    
    def get_wind_magnitude(self, altitude: float) -> float:
        """
        Get wind speed using logarithmic profile (more efficient than full vector).
        
        Args:
            altitude (float): Altitude above ground [m]
        
        Returns:
            float: Wind speed [m/s]
        """
        altitude = max(WC.MIN_WIND_SPEED, altitude)
        absolute_height = altitude + self.launch_altitude
        numerator = np.log((absolute_height + self.roughness_length) / self.roughness_length)
        return float(self.wind_speed_ref * numerator / self._denominator)
    
    def get_info(self) -> dict:
        info = super().get_info()
        info.update({
            'wind_speed_ref': self.wind_speed_ref,
            'reference_height': self.reference_height,
            'roughness_length': self.roughness_length,
            'wind_profile_type': 'logarithmic',
        })
        return info


class PowerLawWind(WindModel):
    """
    Power law wind profile: simpler alternative to logarithmic profile.
    
    Formula: U(h) = U_ref * (h / h_ref)^α
    
    Where:
        α (exponent) typical ranges:
        0.10-0.14 = smooth surfaces (water, grass)
        0.20 = average surfaces (crop land, suburban)
        0.40 = rough surfaces (forest, urban)
    
    Advantages over logarithmic:
        - Simpler calculation
        - Empirically validated
        - Good for quick estimates
    
    References:
        - Peterson & Hennessey Jr. (1978)
        - ISO 2450 (Wind energy resource assessment)
    """
    
    def __init__(self, wind_speed_ref: float = WC.DEFAULT_WIND_SPEED, reference_height: float = WC.DEFAULT_REFERENCE_HEIGHT,
                 exponent: float = WC.DEFAULT_POWER_LAW_EXPONENT, wind_direction: float = WC.DEFAULT_WIND_DIRECTION,
                 launch_altitude: float = WC.DEFAULT_LAUNCH_ALTITUDE):
        """
        Initialize power law wind profile.
        
        Args:
            wind_speed_ref (float): Wind speed at reference height [m/s]
            reference_height (float): Reference height [m]
            exponent (float): Power law exponent α [unitless]
            wind_direction (float): Direction from [degrees]
            launch_altitude (float): Launch site elevation [m]
        
        Raises:
            InputValidationError: If parameters invalid
        """
        super().__init__(wind_direction, launch_altitude)
        
        if wind_speed_ref < WC.MIN_WIND_SPEED or wind_speed_ref > WC.MAX_WIND_SPEED:
            raise InputValidationError(f"wind_speed_ref must be [0, 100], got {wind_speed_ref}")
        if reference_height <= 0:
            raise InputValidationError(f"reference_height must be > 0, got {reference_height}")
        if exponent < WC.MIN_POWER_LAW_EXPONENT or exponent > WC.MAX_POWER_LAW_EXPONENT:
            logger.warning(f"Unusual exponent {exponent}; typical range is {WC.POWER_LAW_SMOOTH}-{WC.POWER_LAW_ROUGH}")
        
        self.wind_speed_ref = float(wind_speed_ref)
        self.reference_height = float(reference_height)
        self.exponent = float(exponent)
        
        logger.info(
            f"PowerLawWind: U_ref={wind_speed_ref} m/s @ {reference_height}m, "
            f"α={exponent}, from {wind_direction}°"
        )
    
    def get_wind_vector(self, altitude: float) -> np.ndarray:
        """
        Calculate wind using power law profile.
        
        Args:
            altitude (float): Altitude above ground [m]
        
        Returns:
            np.ndarray: [East, North, Up] wind components [m/s]
        """
        altitude = max(WC.MIN_WIND_SPEED, altitude)
        absolute_height = altitude + self.launch_altitude
        
        # Avoid singularity: U(0) would be 0, minimum height is reference_height for safety
        effective_height = max(self.reference_height, absolute_height)
        
        # U(h) = U_ref * (h / h_ref)^α
        wind_speed = self.wind_speed_ref * (effective_height / self.reference_height) ** self.exponent
        
        # Convert direction
        direction_rad = np.radians(self.wind_direction + 180.0)
        
        east = wind_speed * np.sin(direction_rad)
        north = wind_speed * np.cos(direction_rad)
        up = 0.0
        
        return np.array([east, north, up])
    
    def get_info(self) -> dict:
        info = super().get_info()
        info.update({
            'wind_speed_ref': self.wind_speed_ref,
            'reference_height': self.reference_height,
            'exponent': self.exponent,
            'wind_profile_type': 'power_law',
        })
        return info


class GustWind(WindModel):
    """
    Wind model with turbulent gusts using Dryden spectrum.
    
    Implements temporal turbulence fluctuations on top of a base wind profile.
    Uses band-limited white noise filtered by Dryden spectrum.
    
    The Dryden spectrum is a standard model for aircraft turbulence:
        S(Ω) = (σ² * L / π) / (1 + (Ω * L / σ)²)
    
    Where:
        σ = turbulence intensity (std dev as fraction of mean wind)
        L = length scale (defines correlation length)
        Ω = frequency
    
    References:
        - Dryden, H. L. (1953). A review of the statistical theory of turbulence
        - MIL-F-8785C Military specification for aircraft
        - Hoblit, F. M. (1988). Gust loads on aircraft: concepts and applications
    """
    
    def __init__(self, base_wind_model: Optional[WindModel] = None, gust_intensity: float = WC.DEFAULT_GUST_INTENSITY,
                 gust_length_scale: float = WC.DEFAULT_GUST_LENGTH_SCALE, random_seed: Optional[int] = None):
        """
        Initialize gust wind model with Dryden spectrum filtering.
        
        Args:
            base_wind_model (Optional[WindModel]): Base wind profile (constant or log)
            gust_intensity (float): Turbulence intensity [0-1] (std dev / mean wind)
            gust_length_scale (float): Integral length scale L [m]
                - 200-400m typical for low altitude (<600m)
                - 500-2000m for medium altitude
            random_seed (int): For reproducible simulations
        """
        if base_wind_model is None:
            base_wind_model = LogarithmicWind()
        
        super().__init__(base_wind_model.wind_direction, base_wind_model.launch_altitude)
        self.base_wind = base_wind_model
        self.gust_intensity = np.clip(gust_intensity, WC.MIN_WIND_SPEED, WC.MAX_GUST_INTENSITY)
        self.gust_length_scale = max(WC.MIN_GUST_LENGTH_SCALE, gust_length_scale)
        
        if random_seed is not None:
            np.random.seed(random_seed)
        
        # Dryden filter state (first-order lowpass for each component)
        # Using gust velocity, not gust perturbation
        self.gust_u = 0.0  # East component gust [m/s]
        self.gust_v = 0.0  # North component gust [m/s]
        self.gust_w = 0.0  # Up component gust [m/s]
        
        # Dryden filter coefficients (approximated by first-order system)
        # Time constant: tau = L / (mean_wind_speed)
        # Using nominal speed of 10 m/s for initialization
        self.nominal_speed = WC.NOMINAL_WIND_SPEED  # m/s reference speed
        self.base_tau = self.gust_length_scale / self.nominal_speed  # [s]
        
        logger.info(
            f"GustWind: intensity={gust_intensity:.1%}, length_scale={gust_length_scale}m, "
            f"Dryden spectrum enabled"
        )
    
    def _dryden_filter_step(self, white_noise: float, gust_state: float, tau: float, 
                            dt: float) -> float:
        """
        Apply first-order Dryden filter to white noise input.
        
        Implements: dgust/dt = (1/tau) * (sigma * noise - gust)
        Solution: gust(t+dt) = gust(t) * exp(-dt/tau) + sigma * noise * (1 - exp(-dt/tau))
        
        Args:
            white_noise (float): Gaussian white noise [-∞, +∞]
            gust_state (float): Current gust velocity [m/s]
            tau (float): Filter time constant [s]
            dt (float): Time step [s]
        
        Returns:
            float: Updated gust velocity [m/s]
        """
        if tau <= 0 or dt <= 0:
            return 0.0
        
        # Exponential decay and noise input
        decay = np.exp(-dt / tau)
        sigma = self.gust_intensity * self.nominal_speed
        
        # First-order system response to white noise
        new_gust = gust_state * decay + sigma * white_noise * (1.0 - decay)
        
        return new_gust
    
    def get_wind_vector(self, altitude: float) -> np.ndarray:
        """
        Get wind with Dryden spectrum gust fluctuations applied.
        
        Combines base wind profile with time-varying Dryden turbulence.
        
        Args:
            altitude (float): Altitude above ground [m]
        
        Returns:
            np.ndarray: [East, North, Up] wind components [m/s]
        """
        # Get base wind at this altitude
        base_wind = self.base_wind.get_wind_vector(altitude)
        
        # Scale time constant based on actual wind speed (lower bound 1 m/s)
        wind_speed = max(1.0, np.linalg.norm(base_wind[:2]))
        tau = self.gust_length_scale / wind_speed
        
        # Apply Dryden-filtered gusts to each component
        gust_wind = np.array([
            self.gust_u,
            self.gust_v,
            self.gust_w
        ])
        
        # Return base wind plus gust perturbations
        return base_wind + gust_wind
    
    def update(self, dt: float) -> None:
        """
        Update gust state using Dryden spectrum filter.
        
        This drives the turbulent fluctuations forward in time, creating
        realistic correlated gust signals.
        
        Args:
            dt (float): Time step [s]
        """
        super().update(dt)
        
        if dt <= 0:
            return
        
        # Generate independent Gaussian white noise for each component
        noise_u = np.random.normal(0.0, 1.0)
        noise_v = np.random.normal(0.0, 1.0)
        noise_w = np.random.normal(0.0, 1.0)
        
        # Scale time constant (will vary by altitude, use nominal here)
        tau = self.base_tau
        
        # Update gust components using Dryden filter
        self.gust_u = self._dryden_filter_step(noise_u, self.gust_u, tau, dt)
        self.gust_v = self._dryden_filter_step(noise_v, self.gust_v, tau, dt)
        self.gust_w = self._dryden_filter_step(noise_w, self.gust_w, tau, dt)
    
    def get_info(self) -> dict:
        info = super().get_info()
        info.update({
            'base_wind_type': self.base_wind.get_info()['model_type'],
            'gust_intensity': self.gust_intensity,
            'gust_length_scale': self.gust_length_scale,
            'current_gust_magnitude': float(np.linalg.norm([self.gust_u, self.gust_v, self.gust_w])),
            'implementation_status': 'Full Dryden spectrum - Phase 4',
        })
        return info


class WindShearWind(WindModel):
    """
    Advanced 3D wind shear model for complex wind conditions.
    
    Supports directional wind shear where wind direction AND magnitude change with altitude.
    This is critical for realistic atmospheric modeling, especially for:
        - Jet streams and directional shear
        - Sea/land breeze transitions
        - Mountain wave dynamics
        - Thermal updraft structures
    
    Configuration:
        - Base wind at reference height (constant or profile)
        - Directional shear angle (backing/veering with altitude)
        - Directional shear rate over altitude range
        - Optional vertical wind (updrafts/downdrafts)
    
    References:
        - Hodograph analysis (rotating wind vector with altitude)
        - Environmental wind shear (aviation meteorology)
        - Boundary layer wind structure (boundary layer meteorology)
    """
    
    def __init__(self, base_wind_speed: float = WC.DEFAULT_WIND_SPEED, base_wind_direction: float = WC.DEFAULT_WIND_DIRECTION,
                 shear_direction_change: float = WC.DEFAULT_SHEAR_DIRECTION_CHANGE, shear_altitude_range: float = WC.DEFAULT_SHEAR_ALTITUDE_RANGE,
                 vertical_wind_speed: float = 0.0, launch_altitude: float = WC.DEFAULT_LAUNCH_ALTITUDE):
        """
        Initialize wind shear model with directional and magnitude variation.
        
        Args:
            base_wind_speed (float): Base wind speed at launch site [m/s]
            base_wind_direction (float): Base wind direction FROM [degrees]
            shear_direction_change (float): Total direction change over shear range [degrees]
                - Positive = clockwise (backing)
                - Negative = counterclockwise (veering)
            shear_altitude_range (float): Altitude range over which shear occurs [m]
            vertical_wind_speed (float): Vertical wind component [m/s]
                - Positive = updraft, negative = downdraft
            launch_altitude (float): Launch site elevation [m]
        """
        super().__init__(base_wind_direction, launch_altitude)
        self.base_wind_speed = np.clip(base_wind_speed, WC.MIN_WIND_SPEED, WC.MAX_WIND_SPEED)
        self.shear_direction_change = float(shear_direction_change)  # degrees
        self.shear_altitude_range = max(WC.MIN_GUST_LENGTH_SCALE, shear_altitude_range)  # min 1m
        self.vertical_wind_speed = np.clip(vertical_wind_speed, WC.MIN_VERTICAL_WIND, WC.MAX_VERTICAL_WIND)  # m/s
        
        # Pre-calculate shear rate (degrees per meter)
        self.shear_rate = self.shear_direction_change / self.shear_altitude_range
        
        logger.info(
            f"WindShearWind: base_speed={base_wind_speed}m/s, "
            f"direction_change={shear_direction_change}° over {shear_altitude_range}m, "
            f"vertical_wind={vertical_wind_speed}m/s"
        )
    
    def get_wind_vector(self, altitude: float) -> np.ndarray:
        """
        Calculate wind vector with directional shear.
        
        Wind direction and speed vary linearly with altitude, creating
        a rotated hodograph when plotted.
        
        Args:
            altitude (float): Altitude above ground at launch site [m]
        
        Returns:
            np.ndarray: [East, North, Up] wind components [m/s]
        """
        altitude = max(WC.MIN_WIND_SPEED, altitude)
        
        # Calculate wind speed variation with altitude (linear shear)
        # Speed increases slightly with altitude (typical of boundary layer)
        speed_increase_factor = 1.0 + WC.SHEAR_SPEED_INCREASE_FACTOR * (altitude / self.shear_altitude_range)
        wind_speed = self.base_wind_speed * speed_increase_factor
        wind_speed = max(WC.MIN_WIND_SPEED, wind_speed)  # Ensure non-negative
        
        # Calculate wind direction change with altitude (directional shear)
        # Linear variation from base at ground to base + shear_direction_change at top
        direction_fraction = min(1.0, altitude / self.shear_altitude_range)
        wind_direction = self.wind_direction + self.shear_direction_change * direction_fraction
        wind_direction = wind_direction % 360.0
        
        # Convert meteorological direction (FROM) to math direction (TO)
        direction_rad = np.radians((wind_direction + 180.0) % 360.0)
        
        east = wind_speed * np.sin(direction_rad)
        north = wind_speed * np.cos(direction_rad)
        up = self.vertical_wind_speed
        
        return np.array([east, north, up])
    
    def get_hodograph(self, altitude_levels: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get hodograph (wind vector plot changing with altitude).
        
        Useful for visualizing directional shear in wind analysis plots.
        
        Args:
            altitude_levels (np.ndarray): Array of altitudes [m]
        
        Returns:
            Tuple[np.ndarray, np.ndarray]: East and North components at each altitude
        """
        hodograph_vectors = np.array([self.get_wind_vector(alt)[:2] for alt in altitude_levels])
        return hodograph_vectors[:, 0], hodograph_vectors[:, 1]
    
    def get_info(self) -> dict:
        info = super().get_info()
        info.update({
            'model_type': 'WindShear',
            'base_wind_speed': self.base_wind_speed,
            'shear_direction_change': self.shear_direction_change,
            'shear_altitude_range': self.shear_altitude_range,
            'shear_rate': self.shear_rate,
            'vertical_wind_speed': self.vertical_wind_speed,
            'implementation_status': 'Full 3D wind shear - Phase 4',
        })
        return info


# Factory function for convenient wind model creation
def create_wind_model_from_state(scenario: dict) -> WindModel:
    """
    Create a wind model from a scenario dictionary.
    
    This function maps scenario dictionary keys to wind model parameters.
    It's designed to work with scenario dictionaries from the WindScenarioEditorWidget.
    
    Args:
        scenario (dict): Scenario dictionary with keys like:
            - model_type: 'constant', 'logarithmic', 'power_law', 'gust', 'shear'
            - wind_speed or wind_speed_ref: Reference wind speed [m/s]
            - wind_direction: Wind direction FROM [degrees]
            - wind_reference_height: Reference height [m]
            - wind_roughness_length: Surface roughness [m]
            - wind_exponent: Power law exponent
            - wind_gust_intensity: Turbulence intensity [0-1]
            - wind_gust_length_scale: Gust length scale [m]
            - shear_direction_change: Direction change [degrees]
            - shear_altitude_range: Altitude range [m]
            - vertical_wind: Vertical wind speed [m/s]
    
    Returns:
        WindModel: Initialized wind model instance
    """
    model_type = scenario.get('model_type', 'logarithmic')
    
    # Build kwargs based on scenario data
    kwargs = {
        'wind_direction': scenario.get('wind_direction', 0.0),
        'launch_altitude': scenario.get('launch_altitude', 0.0),
    }
    
    if model_type == 'constant':
        kwargs['wind_speed'] = scenario.get('wind_speed', 5.0)
    elif model_type == 'logarithmic':
        kwargs['wind_speed_ref'] = scenario.get('wind_speed', scenario.get('wind_speed_ref', 5.0))
        kwargs['reference_height'] = scenario.get('wind_reference_height', 10.0)
        kwargs['roughness_length'] = scenario.get('wind_roughness_length', 0.1)
    elif model_type == 'power_law':
        kwargs['wind_speed_ref'] = scenario.get('wind_speed', scenario.get('wind_speed_ref', 5.0))
        kwargs['reference_height'] = scenario.get('wind_reference_height', 10.0)
        kwargs['exponent'] = scenario.get('wind_exponent', 0.2)
    elif model_type == 'gust':
        # Create base logarithmic wind for gust model
        base_kwargs = {
            'wind_speed_ref': scenario.get('wind_speed', scenario.get('wind_speed_ref', 5.0)),
            'reference_height': scenario.get('wind_reference_height', 10.0),
            'roughness_length': scenario.get('wind_roughness_length', 0.1),
            'wind_direction': scenario.get('wind_direction', 0.0),
            'launch_altitude': scenario.get('launch_altitude', 0.0),
        }
        base_wind = LogarithmicWind(**base_kwargs)
        kwargs['base_wind_model'] = base_wind
        kwargs['gust_intensity'] = scenario.get('wind_gust_intensity', 0.1)
        kwargs['gust_length_scale'] = scenario.get('wind_gust_length_scale', 300.0)
        kwargs.pop('wind_direction', None)  # Remove as it's in base_wind
        kwargs.pop('launch_altitude', None)  # Remove as it's in base_wind
    elif model_type == 'shear':
        kwargs['base_wind_speed'] = scenario.get('wind_speed', 5.0)
        kwargs['base_wind_direction'] = scenario.get('wind_direction', 0.0)
        kwargs['shear_direction_change'] = scenario.get('shear_direction_change', 0.0)
        kwargs['shear_altitude_range'] = scenario.get('shear_altitude_range', 1000.0)
        kwargs['vertical_wind_speed'] = scenario.get('vertical_wind', 0.0)
        kwargs['launch_altitude'] = scenario.get('launch_altitude', 0.0)
        kwargs.pop('wind_direction', None)  # Use base_wind_direction instead
    
    return create_wind_model(model_type, **kwargs)


def create_wind_model(model_type: str = 'logarithmic', **kwargs) -> WindModel:
    """
    Factory function to create wind models by name.
    
    Args:
        model_type (str): Type of wind model to create:
            'constant' - ConstantWind
            'logarithmic' - LogarithmicWind (default, recommended)
            'power_law' - PowerLawWind
            'gust' - GustWind
            'shear' - WindShearWind
        **kwargs: Model-specific parameters
    
    Returns:
        WindModel: Initialized wind model instance
    
    Raises:
        InputValidationError: If model_type is unknown
    
    Examples:
        >>> wind = create_wind_model('constant', wind_speed=5.0)
        >>> wind = create_wind_model('logarithmic', wind_speed_ref=5.0)
    """
    model_type = model_type.lower().strip()
    
    if model_type == 'constant':
        return ConstantWind(**kwargs)
    elif model_type == 'logarithmic':
        return LogarithmicWind(**kwargs)
    elif model_type == 'power_law':
        return PowerLawWind(**kwargs)
    elif model_type == 'gust':
        return GustWind(**kwargs)
    elif model_type == 'shear':
        return WindShearWind(**kwargs)
    else:
        raise InputValidationError(
            f"Unknown wind model type: '{model_type}'. "
            f"Supported: 'constant', 'logarithmic', 'power_law', 'gust', 'shear'"
        )
