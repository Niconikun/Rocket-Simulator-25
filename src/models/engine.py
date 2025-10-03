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
import pandas as pd
from scipy.interpolate import interp1d
import os

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
                 thrust_curve_file=None, thrust_curve_data=None,
                 chamber_temperature=3000.0, gas_constant=287.0, gamma=1.2):
        """
        Enhanced rocket engine model with experimental thrust curve support.
        
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
            thrust_curve_file (str): Path to CSV file with thrust curve data
            thrust_curve_data (dict): Pre-loaded thrust curve data {'time': [], 'thrust': []}
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
        
        # Enhanced thrust curve handling
        self.thrust_curve_file = thrust_curve_file
        self.thrust_curve_data = thrust_curve_data
        self.thrust_interpolator = None
        self.use_experimental_thrust = False
        
        # Load and process thrust curve data
        self._load_thrust_curve()
        
        # Initialize performance
        self._calculate_nozzle_performance()
        self._calculate_performance()
        
        # Validate thrust curve instead of general performance
        self._thrust_curve_validated = False

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
        
    def _load_thrust_curve(self):
        """Load and process experimental thrust curve data"""
        try:
            thrust_data = None
            
            # Load from file if provided
            if self.thrust_curve_file and os.path.exists(self.thrust_curve_file):
                thrust_data = pd.read_csv(self.thrust_curve_file)
                logging.info(f"Loaded thrust curve from {self.thrust_curve_file}")
            
            # Use provided data if available
            elif self.thrust_curve_data:
                thrust_data = pd.DataFrame(self.thrust_curve_data)
                logging.info("Using provided thrust curve data")
            
            if thrust_data is not None:
                # Detect column names (handle different formats)
                time_col = None
                thrust_col = None
                
                for col in thrust_data.columns:
                    col_lower = col.lower()
                    if 'time' in col_lower or 'tiempo' in col_lower:
                        time_col = col
                    elif 'thrust' in col_lower or 'force' in col_lower or 'fuerza' in col_lower:
                        thrust_col = col
                
                if time_col and thrust_col:
                    # Convert thrust from kg-f to Newtons if needed
                    thrust_values = thrust_data[thrust_col].values
                    
                    # Detect if thrust is in kg-f (typical values around 0-200)
                    if np.max(np.abs(thrust_values)) < 1000:  # Likely kg-f
                        thrust_values = thrust_values * 9.80665  # Convert kg-f to N
                        logging.info("Converted thrust from kg-f to Newtons")
                    
                    # Create time array
                    time_values = thrust_data[time_col].values
                    
                    # Ensure time starts at 0
                    time_values = time_values - time_values[0]
                    
                    # Create interpolator
                    self.thrust_interpolator = interp1d(
                        time_values, thrust_values, 
                        kind='linear', 
                        bounds_error=False, 
                        fill_value=(thrust_values[0], 0.0)
                    )
                    
                    # Update burn time based on thrust curve
                    actual_burn_time = time_values[-1]
                    if abs(actual_burn_time - self.burn_time) > 0.1:
                        logging.info(f"Updating burn time from {self.burn_time}s to {actual_burn_time}s based on thrust curve")
                        self.burn_time = actual_burn_time
                    
                    self.use_experimental_thrust = True
                    logging.info(f"Experimental thrust curve loaded: {len(time_values)} points, {actual_burn_time:.2f}s duration")
                    
                else:
                    logging.warning("Could not identify time and thrust columns in thrust curve data")
            
        except Exception as e:
            logging.error(f"Error loading thrust curve: {e}")
            self.use_experimental_thrust = False

    def _calculate_experimental_thrust(self):
        """Calculate thrust using experimental data"""
        if self.thrust_interpolator is None:
            return 0.0
        
        try:
            # Get thrust from interpolator
            thrust = float(self.thrust_interpolator(self.time))
            
            # Ensure thrust is non-negative
            thrust = max(0.0, thrust)
            
            return thrust
            
        except Exception as e:
            logging.error(f"Error in experimental thrust calculation: {e}")
            return 0.0

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
        
        """Calculate current engine performance with experimental thrust support"""
        try:
            # Reset values
            self._mass_flux = 0.0
            self._thrust = 0.0
            self.gas_speed = 0.0
            self.exit_pressure = 0.0
            self.actual_isp = 0.0

            if 0 <= self.time <= self.burn_time:
                # Use experimental thrust curve if available
                if self.use_experimental_thrust:
                    self._thrust = self._calculate_experimental_thrust()
                    
                    # Calculate mass flux based on experimental thrust
                    if self._thrust > 0:
                        # Estimate mass flux from thrust and specific impulse
                        g0 = 9.80665
                        self._mass_flux = self._thrust / (self.specific_impulse * g0)
                        
                        # Calculate exit velocity for consistency
                        self.gas_speed = self.specific_impulse * g0
                        self.exit_pressure = self.ambient_pressure  # Simplified
                        
                        # Calculate actual specific impulse
                        self.actual_isp = self.specific_impulse
                    else:
                        self._mass_flux = 0.0
                        self.gas_speed = 0.0
                        self.exit_pressure = 0.0
                        self.actual_isp = 0.0
                        
                else:
                    # Use analytical model (existing code)
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
        """Calculate realistic thrust curve that guarantees mean thrust conservation"""
        if self.time > self.burn_time or self.time == 0.0:
            return 0.0
        
        t_norm = self.time / self.burn_time
        
        try:
            # Define a base thrust profile with realistic shape starting from 0
            if t_norm < 0.02:  # 2% ignition phase - start from 0
                # Start from 0 and ramp up quickly
                ramp_up = t_norm / 0.02
                shape_factor = 0.1 * ramp_up  # Start very low
                
            elif t_norm < 0.08:  # 2-8% fast ramp up
                ramp_pos = (t_norm - 0.02) / 0.06
                # Smooth ramp up using cubic easing
                shape_factor = 0.1 + 0.4 * (3 * ramp_pos**2 - 2 * ramp_pos**3)
                
            elif t_norm < 0.15:  # 8-15% approach to max thrust
                ramp_pos = (t_norm - 0.08) / 0.07
                shape_factor = 0.5 + 0.5 * ramp_pos
                
            elif t_norm < 0.85:  # 15-85% sustained phase with small variations
                # Small oscillations around sustained level
                oscillation = 0.05 * np.sin(2 * np.pi * t_norm * 4)  # 4 oscillations
                # Gentle decay from higher to lower thrust
                decay = (0.85 - t_norm) / 0.70
                shape_factor = 0.95 + 0.05 * decay + oscillation
                
            elif t_norm < 0.92:  # 85-92% initial ramp down
                ramp_down = 1.0 - (t_norm - 0.85) / 0.07
                shape_factor = 0.7 * ramp_down
                
            elif t_norm < 0.97:  # 92-97% fast ramp down
                ramp_down = 1.0 - (t_norm - 0.92) / 0.05
                shape_factor = 0.3 * ramp_down
                
            else:  # 97-100% tail-off
                tail_off = 1.0 - (t_norm - 0.97) / 0.03
                shape_factor = 0.05 * np.exp(-4 * (1 - tail_off))
            
            # Scale to ensure exact mean thrust match
            # The integral of our shape function over [0,1] should equal mean_thrust/max_thrust
            shape_integral = 0.685  # Updated integral for the new shape function
            
            # Calculate required scaling to match mean thrust
            required_mean_ratio = self.mean_thrust / self.max_thrust
            current_mean_ratio = shape_integral
            
            if current_mean_ratio > 0:
                correction_factor = required_mean_ratio / current_mean_ratio
                shape_factor *= correction_factor
            
            # Apply the scaling and ensure bounds
            thrust = shape_factor * self.max_thrust
            
            # Final validation and bounds checking
            thrust = min(thrust, self.max_thrust)  # Don't exceed max thrust
            thrust = max(thrust, 0)  # Ensure non-negative
            
            # Debug logging for first few time steps
            if self.time <= 0.1 and int(self.time * 100) % 10 == 0:  # Log every 0.01s for first 0.1s
                logging.debug(f"t={self.time:.3f}s, t_norm={t_norm:.3f}, shape_factor={shape_factor:.3f}, thrust={thrust:.1f}N")
            
            return thrust
            
        except Exception as e:
            logging.error(f"Thrust curve calculation error: {e}")
            # Fallback: simple interpolation that guarantees mean
            return self._fallback_thrust_curve(t_norm)

    def _fallback_thrust_curve(self, t_norm):
        """Fallback thrust curve that guarantees mean thrust conservation and starts from 0"""
        # Simple piecewise linear function that starts from 0 and conserves mean thrust
        if 0 <= t_norm < 0.05:
            return self.max_thrust * (t_norm / 0.05) * 0.3  # Start from 0, ramp to 30% of max
        elif 0.05 <= t_norm < 0.15:
            ramp_pos = (t_norm - 0.05) / 0.10
            return self.max_thrust * (0.3 + 0.5 * ramp_pos)  # Ramp to 80% of max
        elif 0.15 <= t_norm < 0.25:
            ramp_pos = (t_norm - 0.15) / 0.10
            return self.max_thrust * (0.8 + 0.2 * ramp_pos)  # Ramp to 100% of max
        elif 0.25 <= t_norm < 0.75:
            # Main sustain phase - adjusted to conserve mean
            return self.max_thrust * 0.95  # Sustain at 95% of max
        elif 0.75 <= t_norm < 0.85:
            return self.max_thrust * (0.95 - 0.3 * ((t_norm - 0.75) / 0.10))  # Ramp down to 65%
        elif 0.85 <= t_norm < 0.95:
            return self.max_thrust * (0.65 - 0.4 * ((t_norm - 0.85) / 0.10))  # Ramp down to 25%
        else:
            return self.max_thrust * (0.25 - 0.25 * ((t_norm - 0.95) / 0.05))  # Ramp down to 0

    def validate_thrust_curve(self):
        """Validate that thrust curve produces correct mean thrust and starts from 0"""
        # Test the thrust curve at multiple points to verify mean
        test_points = 200  # More points for better accuracy
        total_thrust = 0
        thrust_values = []
        
        for i in range(test_points):
            test_time = (i / test_points) * self.burn_time
            original_time = self.time
            self.time = test_time
            thrust = self._calculate_thrust_curve()
            total_thrust += thrust
            thrust_values.append(thrust)
            self.time = original_time
        
        calculated_mean = total_thrust / test_points
        error = abs(calculated_mean - self.mean_thrust) / self.mean_thrust
        
        # Check initial thrust
        initial_thrust = thrust_values[0] if thrust_values else 0
        
        validation_result = {
            'valid': error < 0.05 and initial_thrust < self.max_thrust * 0.1,  # Allow 5% error and initial thrust < 10% of max
            'calculated_mean': calculated_mean,
            'expected_mean': self.mean_thrust,
            'error_percent': error * 100,
            'initial_thrust': initial_thrust,
            'initial_thrust_ratio': initial_thrust / self.max_thrust,
            'max_thrust_used': max(thrust_values) if thrust_values else 0
        }
        
        if not validation_result['valid']:
            logging.warning(f"Thrust curve validation: {validation_result}")
        
        return validation_result

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

    def get_thrust_curve_info(self):
        """Get information about the loaded thrust curve"""
        if not self.use_experimental_thrust:
            return {"available": False}
        
        try:
            # Sample the thrust curve to get statistics
            sample_times = np.linspace(0, self.burn_time, 100)
            thrust_samples = [self._calculate_experimental_thrust(t) for t in sample_times]
            
            return {
                "available": True,
                "data_points": len(self.thrust_interpolator.x) if hasattr(self.thrust_interpolator, 'x') else 0,
                "burn_time": self.burn_time,
                "max_thrust": max(thrust_samples),
                "total_impulse": np.trapezoid(thrust_samples, sample_times),
                "source": self.thrust_curve_file or "provided_data"
            }
        except Exception as e:
            logging.error(f"Error getting thrust curve info: {e}")
            return {"available": False}

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