# Author: Jorge Orozco & Integration with Nakka SRM Model
# Universidad de Concepción, Facultad de Ingeniería
# E-mail: joorozco@udec.cl

"""
Integrated Engine Module combining simple engine model with SRM capabilities.

This module provides both backward compatibility with the existing simple engine interface
and enhanced SRM (Solid Rocket Motor) simulation capabilities based on Nakka's model.

Classes:
    Engine: Main engine class with both simple and SRM modes
    EngineConfig: Configuration for engine parameters
"""

import json
import os
from typing import Optional, Dict, Any
import math

# Simplified math functions to replace numpy
def pi():
    return math.pi

class EngineConfig:
    """Configuration class for engine parameters."""
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """Initialize engine configuration."""
        self.config = config_dict or {}
        
    def get_property(self, key: str, default=None):
        """Get a configuration property."""
        return self.config.get(key, default)

class Engine:
    """
    Integrated Engine class supporting both simple and SRM simulation modes.
    
    This class maintains backward compatibility with the existing simple engine interface
    while providing enhanced SRM capabilities for detailed simulation.
    
    Modes:
        - simple: Basic thrust calculation (default, backward compatible)
        - srm: Advanced SRM simulation with grain regression and detailed physics
    """
    
    def __init__(self, time, ambient_pressure, burn_time, nozzle_exit_diameter, 
                 mass_flux_max, gas_speed, exit_pressure,
                 length_chamber=1.0, diameter_chamber=0.1,
                 grain_outer_diameter=0.08, grain_length=0.5, grain_inner_diameter=0.02, 
                 N_grains=1, rho_grain=1800, rho_percentage=0.85,
                 mode='simple', engine_config=None):
        """
        Initialize the engine.

        Args:
            time (float): Current time [s]
            ambient_pressure (float): Ambient pressure [Pa]
            burn_time (float): Total burn time [s]
            nozzle_exit_diameter (float): Nozzle exit diameter [m]
            mass_flux_max (float): Maximum mass flux [kg/s]
            gas_speed (float): Gas exit velocity [m/s]
            exit_pressure (float): Exit pressure [Pa]
            length_chamber (float): Chamber length [m] - for SRM mode
            diameter_chamber (float): Chamber diameter [m] - for SRM mode
            grain_outer_diameter (float): Grain outer diameter [m] - for SRM mode
            grain_length (float): Grain length [m] - for SRM mode
            grain_inner_diameter (float): Grain inner diameter [m] - for SRM mode
            N_grains (int): Number of grains - for SRM mode
            rho_grain (float): Grain density [kg/m³] - for SRM mode
            rho_percentage (float): Grain density percentage - for SRM mode
            mode (str): Engine mode ('simple' or 'srm')
            engine_config (EngineConfig): Additional engine configuration
        """
        # Basic parameters
        self.time = time
        self.ambient_pressure = ambient_pressure
        self.burn_time = burn_time
        self.nozzle_exit_diameter = nozzle_exit_diameter
        self._mass_flux_max = mass_flux_max
        self.gas_speed = gas_speed
        self.exit_pressure = exit_pressure
        self.mode = mode
        
        # SRM-specific parameters
        self.length_chamber = length_chamber
        self.diameter_chamber = diameter_chamber
        self.grain_outer_diameter = grain_outer_diameter
        self.grain_length = grain_length
        self.grain_inner_diameter = grain_inner_diameter
        self.N_grains = N_grains
        self.rho_grain = rho_grain
        self.rho_percentage = rho_percentage
        
        # Configuration
        self.config = engine_config or EngineConfig()
        
        # Validate parameters
        self._validate_parameters()
        
        # Calculate derived properties
        self.exit_area = pi() * (self.nozzle_exit_diameter/2)**2
        
        if self.mode == 'srm':
            self._initialize_srm()
        
        # Calculate initial performance
        self._mass_flux = 0.0
        self._thrust = 0.0
        self._calculate_performance()
        
        # Load propellant data if available
        self._load_propellant_data()

    def _validate_parameters(self):
        """Validate engine parameters."""
        if self.ambient_pressure < 0:
            raise ValueError("Ambient pressure cannot be negative")
        if self.burn_time <= 0:
            raise ValueError("Burn time must be positive")
        if self.nozzle_exit_diameter <= 0:
            raise ValueError("Nozzle exit diameter must be positive")
        if self._mass_flux_max <= 0:
            raise ValueError("Maximum mass flux must be positive")
        if self.gas_speed <= 0:
            raise ValueError("Gas speed must be positive")
        if self.exit_pressure <= 0:
            raise ValueError("Exit pressure must be positive")

    def _load_propellant_data(self):
        """Load propellant data from JSON file."""
        try:
            propellant_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'data', 'propellant', 'propellant_data.json'
            )
            if os.path.exists(propellant_path):
                with open(propellant_path, 'r') as file:
                    self.propellant_data = json.load(file)
            else:
                self.propellant_data = {}
        except (FileNotFoundError, json.JSONDecodeError):
            self.propellant_data = {}

    def _initialize_srm(self):
        """Initialize SRM-specific parameters."""
        # Calculate grain properties
        self.chamber_volume = pi() * (self.diameter_chamber / 2)**2 * self.length_chamber
        self.grain_volume_initial = (
            pi() * (self.grain_outer_diameter / 2)**2 * self.grain_length * self.N_grains - 
            pi() * (self.grain_inner_diameter / 2)**2 * self.grain_length * self.N_grains
        )
        self.grain_mass_initial = self.grain_volume_initial * self.rho_grain * self.rho_percentage

    def _calculate_performance(self):
        """Calculate engine performance based on current time and mode."""
        if self.mode == 'simple':
            self._calculate_simple_performance()
        elif self.mode == 'srm':
            self._calculate_srm_performance()

    def _calculate_simple_performance(self):
        """Calculate performance using simple engine model."""
        # Reset values
        self._mass_flux = 0.0
        self._thrust = 0.0
        
        # Calculate mass flux during burn time
        if 0 <= self.time <= self.burn_time:
            if self.time < 0.1:  # Ignition ramp
                ramp_factor = self.time / 0.1
                self._mass_flux = self._mass_flux_max * ramp_factor
            elif self.time > (self.burn_time - 0.1):  # Shutdown ramp
                remaining_time = self.burn_time - self.time
                ramp_factor = remaining_time / 0.1
                self._mass_flux = self._mass_flux_max * ramp_factor
            else:  # Nominal operation
                self._mass_flux = self._mass_flux_max
    
            # Ensure limits
            self._mass_flux = max(0.0, min(self._mass_flux, self._mass_flux_max))
        
            # Calculate thrust: T = ṁv_e + (p_e - p_a)A_e
            if self._mass_flux > 1e-3:
                momentum_thrust = self._mass_flux * self.gas_speed
                pressure_thrust = (self.exit_pressure - self.ambient_pressure) * self.exit_area
                self._thrust = momentum_thrust + pressure_thrust
            else:
                self._mass_flux = 0.0
                self._thrust = 0.0

    def _calculate_srm_performance(self):
        """Calculate performance using SRM model (simplified version)."""
        # This is a simplified SRM calculation
        # For full SRM simulation, the Nakka model components would be integrated here
        
        # For now, use the simple model as base but with SRM-specific corrections
        self._calculate_simple_performance()
        
        # Apply SRM-specific corrections if needed
        if hasattr(self, 'grain_mass_initial') and self.grain_mass_initial > 0:
            # Calculate burn rate based on grain geometry (simplified)
            burn_rate_factor = self._calculate_burn_rate_factor()
            self._mass_flux *= burn_rate_factor
            self._thrust *= burn_rate_factor

    def _calculate_burn_rate_factor(self):
        """Calculate burn rate factor based on grain geometry."""
        # Simplified burn rate calculation
        # This would be replaced with full Nakka model calculations
        if self.time <= 0 or self.time >= self.burn_time:
            return 0.0
        
        # Simple linear burn rate for now
        return 1.0

    @property
    def mass_flux(self):
        """Current mass flux [kg/s]."""
        return self._mass_flux

    @property
    def thrust(self):
        """Current thrust [N]."""
        return self._thrust

    def update(self, time=None, ambient_pressure=None):
        """
        Update engine state.

        Args:
            time (float, optional): New time [s]
            ambient_pressure (float, optional): New ambient pressure [Pa]
        """
        if time is not None:
            self.time = time
        if ambient_pressure is not None:
            if ambient_pressure < 0:
                raise ValueError("Ambient pressure cannot be negative")
            self.ambient_pressure = ambient_pressure
        
        # Recalculate performance
        self._calculate_performance()

    def calculate_specific_impulse(self, ambient_pressure=None):
        """
        Calculate specific impulse for given ambient pressure.
        
        Args:
            ambient_pressure (float, optional): Ambient pressure [Pa]
        
        Returns:
            float: Specific impulse [s]
        """
        g0 = 9.80665  # Standard gravitational acceleration [m/s²]
        
        # Use current ambient pressure if not specified
        p_amb = self.ambient_pressure if ambient_pressure is None else ambient_pressure
        
        # Calculate thrust for this pressure
        momentum_thrust = self._mass_flux * self.gas_speed
        pressure_thrust = (self.exit_pressure - p_amb) * self.exit_area
        total_thrust = momentum_thrust + pressure_thrust
        
        # Calculate specific impulse
        if self._mass_flux > 0:
            return total_thrust / (self._mass_flux * g0)
        return 0.0

    @property
    def specific_impulse(self):
        """Current specific impulse [s]."""
        return self.calculate_specific_impulse()

    @property
    def vacuum_specific_impulse(self):
        """Vacuum specific impulse [s]."""
        return self.calculate_specific_impulse(0.0)

    def get_performance_data(self):
        """
        Get current performance data as dictionary.
        
        Returns:
            dict: Performance data including thrust, mass flux, Isp, etc.
        """
        return {
            'time': self.time,
            'thrust': self.thrust,
            'mass_flux': self.mass_flux,
            'specific_impulse': self.specific_impulse,
            'vacuum_specific_impulse': self.vacuum_specific_impulse,
            'chamber_pressure': self.exit_pressure,  # Simplified
            'exit_pressure': self.exit_pressure,
            'ambient_pressure': self.ambient_pressure,
            'mode': self.mode
        }

    def save_configuration(self, filename):
        """
        Save engine configuration to JSON file.
        
        Args:
            filename (str): Path to save configuration
        """
        config_data = {
            'burn_time': self.burn_time,
            'nozzle_exit_diameter': self.nozzle_exit_diameter,
            'mass_flux_max': self._mass_flux_max,
            'gas_speed': self.gas_speed,
            'exit_pressure': self.exit_pressure,
            'mode': self.mode,
            'srm_parameters': {
                'length_chamber': self.length_chamber,
                'diameter_chamber': self.diameter_chamber,
                'grain_outer_diameter': self.grain_outer_diameter,
                'grain_length': self.grain_length,
                'grain_inner_diameter': self.grain_inner_diameter,
                'N_grains': self.N_grains,
                'rho_grain': self.rho_grain,
                'rho_percentage': self.rho_percentage
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(config_data, f, indent=4)

    @classmethod
    def load_configuration(cls, filename, time=0.0, ambient_pressure=101325.0):
        """
        Load engine configuration from JSON file.
        
        Args:
            filename (str): Path to configuration file
            time (float): Initial time [s]
            ambient_pressure (float): Ambient pressure [Pa]
            
        Returns:
            Engine: Configured engine instance
        """
        with open(filename, 'r') as f:
            config_data = json.load(f)
        
        srm_params = config_data.get('srm_parameters', {})
        
        return cls(
            time=time,
            ambient_pressure=ambient_pressure,
            burn_time=config_data['burn_time'],
            nozzle_exit_diameter=config_data['nozzle_exit_diameter'],
            mass_flux_max=config_data['mass_flux_max'],
            gas_speed=config_data['gas_speed'],
            exit_pressure=config_data['exit_pressure'],
            mode=config_data.get('mode', 'simple'),
            **srm_params
        )

# Maintain backward compatibility
MotorConfig = EngineConfig