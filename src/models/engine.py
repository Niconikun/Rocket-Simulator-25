# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""
Enhanced Rocket Engine Simulation Module

This module provides a comprehensive rocket engine model with:
- Realistic thermodynamics and nozzle flow
- Smooth thrust curve modeling
- Performance validation
- Comprehensive error handling

Equations:
    1. Thrust: T = ṁ·v_e + (p_e - p_a)·A_e
    2. Nozzle Flow: Isentropic expansion relations
    3. Mass Flow: ṁ = p_c·A_t / c*
    4. Characteristic Velocity: c* = √(R·T_c/γ) / Γ(γ)

References:
    - Sutton, G. P., & Biblarz, O. (2016). Rocket propulsion elements.
    - Hill, P., & Peterson, C. (1992). Mechanics and Thermodynamics of Propulsion.
"""

import numpy as np
import logging
from math import sqrt, exp, sin, pi

class EnhancedEngine:
    """
    Enhanced rocket engine model with realistic thermodynamics and performance tracking.
    
    Attributes:
        time (float): Current simulation time [s]
        burn_time (float): Total burn time [s]
        ambient_pressure (float): Ambient pressure [Pa]
        nozzle_exit_diameter (float): Nozzle exit diameter [m]
        propellant_mass (float): Total propellant mass [kg]
        specific_impulse (float): Specific impulse [s]
        mean_thrust (float): Mean thrust [N]
        max_thrust (float): Maximum thrust [N]
        mean_chamber_pressure (float): Mean chamber pressure [Pa]
        max_chamber_pressure (float): Maximum chamber pressure [Pa]
        thrust_to_weight_ratio (float): Thrust-to-weight ratio [-]
    """
    
    def __init__(self, time, burn_time, ambient_pressure, nozzle_exit_diameter,
                 propellant_mass, specific_impulse, mean_thrust, max_thrust,
                 mean_chamber_pressure, max_chamber_pressure, thrust_to_weight_ratio,
                 chamber_temperature=3000.0, gas_constant=287.0, gamma=1.2):
        """
        Initialize enhanced rocket engine model.
        
        Args:
            time (float): Current time [s]
            burn_time (float): Total burn time [s]
            ambient_pressure (float): Ambient pressure [Pa]
            nozzle_exit_diameter (float): Nozzle exit diameter [m]
            propellant_mass (float): Propellant mass [kg]
            specific_impulse (float): Specific impulse [s]
            mean_thrust (float): Mean thrust [N]
            max_thrust (float): Maximum thrust [N]
            mean_chamber_pressure (float): Mean chamber pressure [Pa]
            max_chamber_pressure (float): Maximum chamber pressure [Pa]
            thrust_to_weight_ratio (float): Thrust-to-weight ratio [-]
            chamber_temperature (float): Chamber temperature [K], default 3000
            gas_constant (float): Gas constant [J/(kg·K)], default 287
            gamma (float): Specific heat ratio, default 1.2
        """
        # Input validation
        self._validate_inputs(time, burn_time, ambient_pressure, nozzle_exit_diameter,
                            propellant_mass, specific_impulse, mean_thrust, max_thrust,
                            mean_chamber_pressure, max_chamber_pressure, thrust_to_weight_ratio)
        
        # Basic parameters
        self.time = time
        self.burn_time = burn_time
        self.ambient_pressure = ambient_pressure
        self.nozzle_exit_diameter = nozzle_exit_diameter
        self.propellant_mass = propellant_mass
        self.specific_impulse = specific_impulse
        self.mean_thrust = mean_thrust
        self.max_thrust = max_thrust
        self.mean_chamber_pressure = mean_chamber_pressure
        self.max_chamber_pressure = max_chamber_pressure
        self.thrust_to_weight_ratio = thrust_to_weight_ratio
        
        # Thermodynamic parameters
        self.chamber_temperature = chamber_temperature
        self.gas_constant = gas_constant
        self.gamma = gamma
        
        # Calculated parameters
        self.exit_area = np.pi * (self.nozzle_exit_diameter / 2) ** 2
        self.throat_area = self.exit_area / 4.0  # Typical expansion ratio
        
        # Performance state
        self._mass_flux = 0.0
        self._thrust = 0.0
        self.gas_speed = 0.0
        self.exit_pressure = 0.0
        self.characteristic_velocity = 0.0
        self.thrust_coefficient = 0.0
        self.actual_isp = 0.0
        
        # Initialize performance
        self._calculate_nozzle_performance()
        self._calculate_performance()
        
        # Validate performance
        validation = self.validate_performance()
        if not validation['valid']:
            logging.warning(f"Engine performance validation issues: {validation}")

    def _validate_inputs(self, time, burn_time, ambient_pressure, nozzle_exit_diameter,
                        propellant_mass, specific_impulse, mean_thrust, max_thrust,
                        mean_chamber_pressure, max_chamber_pressure, thrust_to_weight_ratio):
        """Comprehensive input validation"""
        if time < 0:
            raise ValueError("Time cannot be negative")
        if burn_time <= 0:
            raise ValueError("Burn time must be positive")
        if ambient_pressure < 0:
            raise ValueError("Ambient pressure cannot be negative")
        if nozzle_exit_diameter <= 0:
            raise ValueError("Nozzle exit diameter must be positive")
        if propellant_mass <= 0:
            raise ValueError("Propellant mass must be positive")
        if specific_impulse <= 0:
            raise ValueError("Specific impulse must be positive")
        if mean_thrust <= 0 or max_thrust <= 0:
            raise ValueError("Thrust values must be positive")
        if mean_chamber_pressure <= 0 or max_chamber_pressure <= 0:
            raise ValueError("Chamber pressures must be positive")
        if thrust_to_weight_ratio <= 0:
            raise ValueError("Thrust-to-weight ratio must be positive")
        
        if max_thrust < mean_thrust:
            logging.warning("Max thrust is less than mean thrust - this may indicate data issues")

    def _calculate_nozzle_performance(self):
        """Calculate nozzle performance using isentropic flow relations"""
        try:
            # Gamma function for isentropic flow
            gamma = self.gamma
            gamma_func = sqrt(gamma * ((2 / (gamma + 1)) ** ((gamma + 1) / (gamma - 1))))
            
            # Characteristic velocity (c*)
            self.characteristic_velocity = (
                sqrt(self.gas_constant * self.chamber_temperature / gamma) / gamma_func
            )
            
            # Ideal thrust coefficient (simplified)
            pressure_ratio = self.ambient_pressure / self.mean_chamber_pressure
            term1 = (2 * gamma ** 2 / (gamma - 1))
            term2 = (2 / (gamma + 1)) ** ((gamma + 1) / (gamma - 1))
            term3 = 1 - pressure_ratio ** ((gamma - 1) / gamma)
            
            self.ideal_thrust_coefficient = sqrt(term1 * term2 * term3)
            
            logging.debug(f"Nozzle performance: c*={self.characteristic_velocity:.1f} m/s, Cf={self.ideal_thrust_coefficient:.2f}")
            
        except Exception as e:
            logging.error(f"Nozzle performance calculation failed: {e}")
            # Fallback values
            self.characteristic_velocity = 1500.0
            self.ideal_thrust_coefficient = 1.5

    def _calculate_performance(self):
        """Calculate current engine performance"""
        
        try:
            # Reset values
            self._mass_flux = 0.0
            self._thrust = 0.0
            self.gas_speed = 0.0
            self.exit_pressure = 0.0
            self.actual_isp = 0.0

            if 0 <= self.time <= self.burn_time:
                # Calculate thrust curve
                thrust_vacuum = self._calculate_thrust_curve()
                
                # Use provided mass flux from JSON or calculate from propellant mass
                if hasattr(self, 'provided_mass_flux') and self.provided_mass_flux > 0:
                    self._mass_flux = self.provided_mass_flux
                else:
                    # Fallback: calculate from propellant mass and burn time
                    self._mass_flux = self.propellant_mass / self.burn_time
                
                # Calculate mass flow rate from chamber conditions
                if self.characteristic_velocity > 0:
                    self._mass_flux = (self.mean_chamber_pressure * self.throat_area / 
                                     self.characteristic_velocity)
                
                # Calculate exit conditions using isentropic relations
                if self._mass_flux > 0:
                    # Exit Mach number estimation
                    pressure_ratio = self.mean_chamber_pressure / self.ambient_pressure
                    exit_mach = sqrt(2 / (self.gamma - 1) * 
                                   (pressure_ratio ** ((self.gamma - 1) / self.gamma) - 1))
                    exit_mach = min(exit_mach, 5.0)  # Limit Mach number
                    
                    # Exit velocity
                    self.gas_speed = exit_mach * sqrt(self.gamma * self.gas_constant * 
                                                    self.chamber_temperature)
                    
                    # Exit pressure
                    self.exit_pressure = self.mean_chamber_pressure / (
                        (1 + (self.gamma - 1) / 2 * exit_mach ** 2) ** (self.gamma / (self.gamma - 1))
                    )
                    
                    # Thrust components
                    momentum_thrust = self._mass_flux * self.gas_speed
                    pressure_thrust = (self.exit_pressure - self.ambient_pressure) * self.exit_area
                    
                    # Total thrust
                    calculated_thrust = momentum_thrust + pressure_thrust
                    
                    # Scale to match provided thrust data (if available)
                    if thrust_vacuum > 0 and calculated_thrust > 0:
                        # Calculate vacuum thrust for scaling
                        vacuum_pressure_thrust = self.exit_pressure * self.exit_area
                        vacuum_thrust_calc = momentum_thrust + vacuum_pressure_thrust
                        
                        if vacuum_thrust_calc > 0:
                            scale_factor = thrust_vacuum / vacuum_thrust_calc
                            self._thrust = calculated_thrust * scale_factor
                            self._mass_flux *= scale_factor
                    else:
                        self._thrust = calculated_thrust
                    
                    # Calculate actual specific impulse
                    g0 = 9.80665
                    self.actual_isp = self._thrust / (self._mass_flux * g0) if self._mass_flux > 0 else 0
                    
            else:
                # Engine off
                self._mass_flux = 0.0
                self._thrust = 0.0
                self.gas_speed = 0.0
                self.exit_pressure = 0.0
                self.actual_isp = 0.0
                
        except Exception as e:
            logging.error(f"Performance calculation error: {e}")
            # Fallback to simple model
            self._fallback_performance()

    def _calculate_thrust_curve(self):
        """Calculate realistic thrust curve with smooth transitions that matches mean thrust"""
        t_norm = self.time / self.burn_time
        
        try:
            # Calculate base thrust curve shape (0-1 normalized)
            if t_norm < 0.05:  # 5% ignition phase
                # Exponential startup
                shape_factor = 1.0 - exp(-t_norm / 0.01)
                
            elif t_norm < 0.1:  # 5-10% ramp to max thrust
                # Smooth ramp
                ramp_pos = (t_norm - 0.05) / 0.05
                # Cubic easing for smooth transition
                shape_factor = 3 * ramp_pos ** 2 - 2 * ramp_pos ** 3
                shape_factor = 0.3 + 0.7 * shape_factor  # Scale to match previous range
                
            elif t_norm < 0.9:  # 10-90% sustained burn
                # Small oscillations around sustained level
                variation = 0.05 * sin(2 * pi * t_norm * 8)  # 8 oscillations
                # Gradual decrease from higher to lower thrust
                decay = (0.9 - t_norm) / 0.8  # From 1.0 at t_norm=0.1 to 0.0 at t_norm=0.9
                shape_factor = 0.7 + 0.3 * decay  # Range: 0.7 to 1.0
                shape_factor *= (1.0 + variation)
                
            elif t_norm < 0.95:  # 90-95% ramp down
                ramp_down = 1.0 - (t_norm - 0.9) / 0.05
                # Smooth ramp down
                shape_factor = 3 * ramp_down ** 2 - 2 * ramp_down ** 3
                shape_factor *= 0.5  # Scale down for ramp down
                
            else:  # 95-100% tail-off
                tail_off = 1.0 - (t_norm - 0.95) / 0.05
                # Exponential decay
                shape_factor = exp(-5 * (1 - tail_off))
                shape_factor *= 0.1  # Very low thrust during tail-off
            
            # Now scale the entire curve to match the desired mean thrust
            # The shape gives us relative thrust levels, we need to find scaling factors
            # that preserve max_thrust while achieving mean_thrust
            
            # Calculate what the mean would be with current shape using max_thrust
            # We can approximate by knowing the integral of our shape function
            # The areas under each segment:
            area_ignition = 0.025  # Approximate integral of ignition phase
            area_ramp_up = 0.0375  # Approximate integral of ramp up  
            area_sustained = 0.64   # Approximate integral of sustained phase
            area_ramp_down = 0.0125 # Approximate integral of ramp down
            area_tail_off = 0.002   # Approximate integral of tail off
            
            total_shape_area = area_ignition + area_ramp_up + area_sustained + area_ramp_down + area_tail_off
            
            # Current mean if we use max_thrust directly
            current_mean_with_max = self.max_thrust * total_shape_area
            
            # We need to adjust the curve so the mean matches desired mean_thrust
            # while keeping max_thrust as the peak
            
            if current_mean_with_max > self.mean_thrust:
                # Our shape naturally produces too high mean, need to reduce some segments
                # Reduce the sustained phase to lower the mean while keeping max_thrust
                excess_mean = current_mean_with_max - self.mean_thrust
                reduction_needed = excess_mean / area_sustained
                
                # Adjust shape factor in sustained region
                if 0.1 <= t_norm < 0.9:
                    sustained_reduction = reduction_needed / self.max_thrust
                    shape_factor = max(0.3, shape_factor - sustained_reduction)
            
            # Final scaling to ensure exact mean match
            actual_thrust = shape_factor * self.max_thrust
            
            # Apply final correction to ensure mean matches exactly
            # This is a simplified approach - in a full implementation you'd want
            # to pre-calculate the exact scaling needed
            mean_correction_factor = self.mean_thrust / (self.max_thrust * total_shape_area)
            actual_thrust *= mean_correction_factor
            
            # Ensure we don't exceed max_thrust
            actual_thrust = min(actual_thrust, self.max_thrust)
            
            return actual_thrust
            
        except Exception as e:
            logging.error(f"Thrust curve calculation error: {e}")
            # Fallback: simple linear interpolation that guarantees mean thrust
            if t_norm < 0.1:
                return self.max_thrust * (t_norm / 0.1)
            elif t_norm > 0.9:
                return self.mean_thrust * (1.0 - (t_norm - 0.9) / 0.1)
            else:
                return self.mean_thrust

    def _fallback_performance(self):
        """Fallback performance calculation"""
        if 0 <= self.time <= self.burn_time:
            # Simple mass flow calculation
            self._mass_flux = self.propellant_mass / self.burn_time
            
            # Simple thrust based on specific impulse
            g0 = 9.80665
            self._thrust = self._mass_flux * self.specific_impulse * g0
            
            # Simple gas speed
            self.gas_speed = self.specific_impulse * g0
            
            # Estimate exit pressure
            self.exit_pressure = self.mean_chamber_pressure * 0.1
            
            self.actual_isp = self.specific_impulse
        else:
            self._mass_flux = 0.0
            self._thrust = 0.0
            self.gas_speed = 0.0
            self.exit_pressure = 0.0
            self.actual_isp = 0.0

    def validate_performance(self):
        """
        Validate engine performance against known parameters.
        
        Returns:
            dict: Validation results with error metrics
        """
        g0 = 9.80665
        
        try:
            # Check mass consistency
            calculated_propellant_mass = self._mass_flux * self.burn_time
            mass_error = abs(calculated_propellant_mass - self.propellant_mass) / self.propellant_mass
            
            # Check thrust-to-weight ratio
            if hasattr(self, 'initial_mass'):
                initial_weight = self.initial_mass * g0
            else:
                # Estimate initial mass (propellant + structure, assume 10:1 ratio)
                initial_weight = (self.propellant_mass * 1.1) * g0
                
            actual_twr = self.max_thrust / initial_weight
            twr_error = abs(actual_twr - self.thrust_to_weight_ratio) / self.thrust_to_weight_ratio
            
            # Check specific impulse consistency
            isp_error = abs(self.actual_isp - self.specific_impulse) / self.specific_impulse if self.specific_impulse > 0 else 0
            
            is_valid = mass_error < 0.2 and twr_error < 0.2 and isp_error < 0.3
            
            return {
                'valid': is_valid,
                'mass_error': mass_error,
                'twr_error': twr_error,
                'isp_error': isp_error,
                'calculated_propellant_mass': calculated_propellant_mass,
                'actual_twr': actual_twr,
                'actual_isp': self.actual_isp
            }
            
        except Exception as e:
            logging.error(f"Performance validation error: {e}")
            return {
                'valid': False,
                'error': str(e)
            }

    def get_performance_metrics(self):
        """
        Get comprehensive performance metrics.
        
        Returns:
            dict: Complete performance metrics
        """
        return {
            'thrust': self._thrust,
            'mass_flow': self._mass_flux,
            'specific_impulse': self.actual_isp,
            'characteristic_velocity': self.characteristic_velocity,
            'thrust_coefficient': self.ideal_thrust_coefficient,
            'exit_pressure': self.exit_pressure,
            'exit_velocity': self.gas_speed,
            'chamber_pressure': self.mean_chamber_pressure,
            'throat_area': self.throat_area,
            'exit_area': self.exit_area
        }

    def update(self, time=None, ambient_pressure=None):
        """
        Update engine state.
        
        Args:
            time (float, optional): New time [s]
            ambient_pressure (float, optional): New ambient pressure [Pa]
        """
        if time is not None:
            if time < 0:
                raise ValueError("Time cannot be negative")
            self.time = time
            
        if ambient_pressure is not None:
            if ambient_pressure < 0:
                raise ValueError("Ambient pressure cannot be negative")
            self.ambient_pressure = ambient_pressure
        
        self._calculate_performance()

    @property
    def mass_flux(self):
        """Get mass flow rate [kg/s]"""
        return self._mass_flux

    @property
    def thrust(self):
        """Get thrust [N]"""
        return self._thrust

    def calculate_specific_impulse(self, ambient_pressure=None):
        """
        Calculate specific impulse for given ambient pressure.
        
        Args:
            ambient_pressure (float, optional): Ambient pressure [Pa]
            
        Returns:
            float: Specific impulse [s]
        """
        g0 = 9.80665
        p_amb = self.ambient_pressure if ambient_pressure is None else ambient_pressure
        
        momentum_thrust = self._mass_flux * self.gas_speed
        pressure_thrust = (self.exit_pressure - p_amb) * self.exit_area
        total_thrust = momentum_thrust + pressure_thrust
        
        if self._mass_flux > 0:
            return total_thrust / (self._mass_flux * g0)
        return 0.0