"""Parachute simulation module for rocket recovery systems."""

import numpy as np
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)
from src.utils.simulation_constants import ParachuteConstants as PC



class Parachute:
    """
    Simulates parachute deployment and descent dynamics.
    
    Handles:
    - Main parachute deployment at specified altitude/velocity threshold
    - Drogue chute deployment (optional)
    - Drag force calculation during descent
    - Descent rate and landing speed calculations
    """
    
    def __init__(self, config: Dict):
        """
        Initialize parachute system from configuration.
        
        Args:
            config: Dictionary with parachute parameters
                - name (str): Parachute name
                - diameter (float): Canopy diameter in meters
                - Cd (float): Drag coefficient (typically 1.2-1.8)
                - deployment_altitude (float): Altitude trigger in meters
                - min_velocity (float): Minimum safe deployment velocity m/s
                - max_velocity (float): Maximum safe deployment velocity m/s
                - material (str): Material type (ripstop_nylon, silnylon, kevlar)
                - inflation_time (float): Time to full inflation in seconds
                - drogue_enabled (bool): Whether to use drogue chute
                - drogue_diameter (float): Drogue diameter in meters
                - drogue_Cd (float): Drogue drag coefficient
                - drogue_deployment_altitude (float): Drogue deploy altitude in meters
        """
        self.name = config.get('name', PC.DEFAULT_NAME)
        self.diameter = config.get('diameter', PC.DEFAULT_DIAMETER)  # meters
        self.Cd = config.get('Cd', PC.DEFAULT_CD)  # drag coefficient
        self.material = config.get('material', PC.DEFAULT_MATERIAL)
        self.inflation_time = config.get('inflation_time', PC.DEFAULT_INFLATION_TIME)  # seconds
        
        # Deployment settings for main parachute
        self.deployment_altitude = config.get('deployment_altitude', PC.DEFAULT_DEPLOYMENT_ALTITUDE)  # meters
        self.min_velocity = config.get('min_velocity', PC.DEFAULT_MIN_VELOCITY)  # m/s
        self.max_velocity = config.get('max_velocity', PC.DEFAULT_MAX_VELOCITY)  # m/s
        
        # Drogue chute settings
        self.drogue_enabled = config.get('drogue_enabled', False)
        if self.drogue_enabled:
            self.drogue_diameter = config.get('drogue_diameter', PC.DEFAULT_DROGUE_DIAMETER)  # meters
            self.drogue_Cd = config.get('drogue_Cd', PC.DEFAULT_DROGUE_CD)
            self.drogue_deployment_altitude = config.get('drogue_deployment_altitude', PC.DEFAULT_DROGUE_DEPLOYMENT_ALTITUDE)  # meters
            self.drogue_inflation_time = config.get('drogue_inflation_time', PC.DEFAULT_DROGUE_INFLATION_TIME)  # seconds
        
        # State variables
        self.deployed = False
        self.deployment_time: Optional[float] = None
        self.deployment_altitude_actual: Optional[float] = None
        self.deployment_velocity: Optional[float] = None
        
        self.drogue_deployed = False
        self.drogue_deployment_time: Optional[float] = None
        self.drogue_deployment_altitude_actual: Optional[float] = None
        
        self.inflation_progress = 0.0  # 0.0 = not deployed, 1.0 = fully inflated
        self.previous_altitude = 0.0
        
        # Performance metrics
        self.max_descent_rate = 0.0
        self.landing_speed = 0.0
        
        logger.info(f"Parachute initialized: {self.name}, diameter={self.diameter}m, Cd={self.Cd}")
    
    def check_deployment(self, altitude: float, velocity: float, time: float) -> bool:
        """
        Check if parachute should deploy.
        
        Args:
            altitude: Current altitude above ground in meters
            velocity: Current vertical velocity (positive downward) in m/s
            time: Current simulation time in seconds
        
        Returns:
            True if deployment triggered, False otherwise
        """
        if self.deployed:
            return False
        
        # Check if we've reached deployment altitude
        if altitude < self.deployment_altitude:
            # Check velocity constraints
            if self.min_velocity <= velocity <= self.max_velocity:
                self.deployed = True
                self.deployment_time = time
                self.deployment_altitude_actual = altitude
                self.deployment_velocity = velocity
                logger.info(
                    f"Parachute deployed at {altitude:.1f}m, "
                    f"velocity={velocity:.1f}m/s, time={time:.2f}s"
                )
                return True
            elif velocity > self.max_velocity:
                logger.warning(
                    f"Deployment unsafe: velocity {velocity:.1f}m/s > max {self.max_velocity}m/s"
                )
            elif velocity < self.min_velocity:
                logger.warning(
                    f"Deployment unsafe: velocity {velocity:.1f}m/s < min {self.min_velocity}m/s"
                )
        
        return False
    
    def check_drogue_deployment(self, altitude: float, time: float) -> bool:
        """
        Check if drogue chute should deploy.
        
        Args:
            altitude: Current altitude above ground in meters
            time: Current simulation time in seconds
        
        Returns:
            True if drogue should deploy, False otherwise
        """
        if not self.drogue_enabled or self.drogue_deployed:
            return False
        
        if altitude < self.drogue_deployment_altitude:
            self.drogue_deployed = True
            self.drogue_deployment_time = time
            self.drogue_deployment_altitude_actual = altitude
            logger.info(
                f"Drogue parachute deployed at {altitude:.1f}m, time={time:.2f}s"
            )
            return True
        
        return False
    
    def update_inflation(self, delta_time: float) -> None:
        """
        Update parachute inflation progress.
        
        Args:
            delta_time: Time step in seconds
        """
        if not self.deployed:
            return
        
        if self.inflation_progress < 1.0:
            self.inflation_progress = min(
                1.0,
                self.inflation_progress + delta_time / self.inflation_time
            )
    
    def calculate_drag_force(
        self, velocity_magnitude: float, air_density: float
    ) -> float:
        """
        Calculate drag force produced by parachute(s).
        
        Drag equation: F_d = 0.5 * ρ * v² * C_d * A
        
        Args:
            velocity_magnitude: Speed through air in m/s
            air_density: Air density in kg/m³
        
        Returns:
            Drag force in Newtons
        """
        if not self.deployed:
            return 0.0
        
        # Main parachute drag (including inflation)
        area = np.pi * (self.diameter / 2.0) ** 2
        effective_cd = self.Cd * self.inflation_progress  # No drag while inflating
        drag_main = 0.5 * air_density * velocity_magnitude**2 * effective_cd * area
        
        # Drogue chute drag (if deployed)
        drag_drogue = 0.0
        if self.drogue_deployed:
            drogue_area = np.pi * (self.drogue_diameter / 2.0) ** 2
            # Drogue inflates faster (assume full inflation)
            drag_drogue = 0.5 * air_density * velocity_magnitude**2 * self.drogue_Cd * drogue_area
        
        return drag_main + drag_drogue
    
    def calculate_descent_rate(
        self, mass: float, air_density: float, g: float = PC.STANDARD_GRAVITY
    ) -> float:
        """
        Calculate equilibrium descent rate under parachute.
        
        At equilibrium: D = mg, so:
        v_eq = sqrt(2*m*g / (rho * C_d * A))
        
        Args:
            mass: Rocket mass in kg
            air_density: Air density in kg/m³
            g: Gravitational acceleration in m/s²
        
        Returns:
            Equilibrium descent rate in m/s
        """
        if not self.deployed or air_density <= 0:
            return 0.0
        
        # Combined parachute area
        area = np.pi * (self.diameter / 2.0) ** 2
        if self.drogue_deployed:
            area += np.pi * (self.drogue_diameter / 2.0) ** 2
        
        # Combined drag coefficient (approximate)
        effective_cd = self.Cd + (self.drogue_Cd if self.drogue_deployed else 0)
        
        descent_rate = np.sqrt(2 * mass * g / (air_density * effective_cd * area))
        return descent_rate
    
    def get_deployment_info(self) -> Dict:
        """
        Get deployment event information for logging.
        
        Returns:
            Dictionary with deployment details
        """
        info = {
            'parachute_name': self.name,
            'deployed': self.deployed,
            'deployment_time': self.deployment_time,
            'deployment_altitude': self.deployment_altitude_actual,
            'deployment_velocity': self.deployment_velocity,
            'inflation_progress': self.inflation_progress,
        }
        
        if self.drogue_enabled:
            info.update({
                'drogue_deployed': self.drogue_deployed,
                'drogue_deployment_time': self.drogue_deployment_time,
                'drogue_deployment_altitude': self.drogue_deployment_altitude_actual,
            })
        
        return info
    
    def finalize(self) -> Dict:
        """
        Finalize parachute simulation and return final metrics.
        
        Returns:
            Dictionary with parachute deployment metrics
        """
        metrics = {
            'parachute_deployed': self.deployed,
            'parachute_deployment_time': self.deployment_time,
            'parachute_deployment_altitude': self.deployment_altitude_actual,
            'parachute_deployment_velocity': self.deployment_velocity,
            'parachute_max_descent_rate': self.max_descent_rate,
            'parachute_landing_speed': self.landing_speed,
        }
        
        if self.drogue_enabled:
            metrics.update({
                'drogue_deployed': self.drogue_deployed,
                'drogue_deployment_time': self.drogue_deployment_time,
                'drogue_deployment_altitude': self.drogue_deployment_altitude_actual,
            })
        
        return metrics
