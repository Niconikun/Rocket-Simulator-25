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

import logging
import os
from math import sqrt, exp, sin, pi

import numpy as np
from scipy.interpolate import interp1d

from src.utils.thrust_processor import ThrustCurveData, ThrustCurveError, ThrustCurveProcessor

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
                 thrust_curve_unit='N',
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
            thrust_curve_file (str): Path to CSV file with thrust curve data
            thrust_curve_data (dict): Pre-loaded thrust curve data {'time': [], 'thrust': []}
            thrust_curve_unit (str): Unit of thrust column in CSV. Must be 'N' or 'kgf'.
                Required when thrust_curve_file or thrust_curve_data is provided.
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
        
        # Thrust curve configuration
        self.thrust_curve_file = thrust_curve_file
        self.thrust_curve_data = thrust_curve_data
        self.thrust_curve_unit = thrust_curve_unit

        # Interpolator and processed curve (set by _load_thrust_curve)
        self.thrust_interpolator = None
        self.use_experimental_thrust = False
        self._curve_data: ThrustCurveData | None = None

        # ---------------------------------------------------------------
        # B01 – Engine contract attributes
        # These expose a consistent public interface regardless of thrust
        # source (experimental or analytical).
        # ---------------------------------------------------------------
        #: Which source drives thrust: 'experimental' or 'analytical'
        self.thrust_source: str = 'analytical'
        #: Propellant consumed so far [kg]  (updated in Sprint 2)
        self.propellant_consumed: float = 0.0
        #: Remaining propellant [kg]  (updated in Sprint 2)
        self.remaining_propellant: float = propellant_mass
        #: Cumulative delivered impulse [N·s]  (updated in Sprint 2)
        self.total_impulse_delivered: float = 0.0
        #: True once the engine has burned out
        self.burnout_reached: bool = False

        # Load and process thrust curve data
        self._load_thrust_curve()

        # Initialize nozzle performance (thermodynamic constants)
        self._calculate_nozzle_performance()

        # B09 – Precompute analytical shape integral (numeric, not hardcoded)
        self._shape_integral_cached: float = self._compute_analytical_shape_integral()

        # B07 – Build cumulative impulse look-up table (O(log N) per step)
        self._cumul_time_arr: np.ndarray = np.array([0.0, self.burn_time])
        self._cumul_impulse_arr: np.ndarray = np.array([0.0, 0.0])
        self._precompute_cumulative_impulse()

        # B06 – Initial unified performance calculation
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
        """
        Load and validate experimental thrust curve data via ThrustCurveProcessor.

        Raises
        ------
        ThrustCurveError
            Propagated from ThrustCurveProcessor on any structural or physical
            violation so that callers fail early before the simulation loop.
        """
        has_file = bool(self.thrust_curve_file)
        has_dict = bool(self.thrust_curve_data)

        if not has_file and not has_dict:
            # No experimental curve – stay in analytical mode
            self.thrust_source = 'analytical'
            return

        # Delegate all parsing, validation and unit conversion to the processor.
        # ThrustCurveError is intentionally NOT caught here so the caller
        # (update_engine / simulation startup) sees the problem immediately.
        if has_file:
            curve_data = ThrustCurveProcessor.from_csv(
                self.thrust_curve_file, unit=self.thrust_curve_unit
            )
        else:
            curve_data = ThrustCurveProcessor.from_dict(
                self.thrust_curve_data, unit=self.thrust_curve_unit
            )

        # Build interpolator from validated SI data
        time_arr   = np.array(curve_data.time_s)
        thrust_arr = np.array(curve_data.thrust_N)
        self.thrust_interpolator = interp1d(
            time_arr, thrust_arr,
            kind='linear',
            bounds_error=False,
            fill_value=(thrust_arr[0], 0.0),
        )

        # Align burn_time with the curve if they diverge significantly
        if abs(curve_data.duration - self.burn_time) > 0.1:
            logging.info(
                "Updating burn_time from %.3fs to %.3fs based on thrust curve.",
                self.burn_time, curve_data.duration,
            )
            self.burn_time = curve_data.duration

        self._curve_data = curve_data
        self.use_experimental_thrust = True
        self.thrust_source = 'experimental'
        logging.info(
            "Experimental thrust curve ready: %d points, %.2fs, max=%.1fN.",
            curve_data.n_points, curve_data.duration, curve_data.max_thrust,
        )

    # ------------------------------------------------------------------
    # B09 – Thrust shape helpers
    # ------------------------------------------------------------------

    def _shape_function(self, t_norm: float) -> float:
        """
        Normalised shape factor for the analytical thrust profile.

        Parameters
        ----------
        t_norm : float
            Normalised time in (0, 1].  Returns 0 outside that range.

        Returns
        -------
        float
            Dimensionless shape factor ≥ 0.
        """
        if t_norm <= 0.0 or t_norm >= 1.0:
            return 0.0

        if t_norm < 0.02:           # ignition ramp-up
            ramp_up = t_norm / 0.02
            return 0.1 * ramp_up
        elif t_norm < 0.08:         # fast ramp-up (smoothstep)
            rp = (t_norm - 0.02) / 0.06
            return 0.1 + 0.4 * (3 * rp ** 2 - 2 * rp ** 3)
        elif t_norm < 0.15:         # approach to peak
            rp = (t_norm - 0.08) / 0.07
            return 0.5 + 0.5 * rp
        elif t_norm < 0.85:         # sustained phase
            oscillation = 0.05 * np.sin(2 * np.pi * t_norm * 4)
            decay = (0.85 - t_norm) / 0.70
            return 0.95 + 0.05 * decay + oscillation
        elif t_norm < 0.92:         # initial ramp-down
            return 0.7 * (1.0 - (t_norm - 0.85) / 0.07)
        elif t_norm < 0.97:         # fast ramp-down
            return 0.3 * (1.0 - (t_norm - 0.92) / 0.05)
        else:                       # tail-off
            tail_off = 1.0 - (t_norm - 0.97) / 0.03
            return 0.05 * np.exp(-4.0 * (1.0 - tail_off))

    def _compute_analytical_shape_integral(self) -> float:
        """
        Numerically integrate *_shape_function* over [0, 1] using the
        midpoint rule (N = 500 intervals).  Result replaces the old
        hardcoded value of 0.685 so that the normalisation is exact.

        Returns
        -------
        float
            Mean value of the shape function over [0, 1].
        """
        N = 500
        total = sum(self._shape_function((i + 0.5) / N) for i in range(N))
        integral = total / N
        logging.debug("Analytical shape integral = %.4f (N=%d)", integral, N)
        return integral

    def _thrust_at_time(self, t: float) -> float:
        """
        Pure function: instantaneous thrust at time *t* [N].

        Works for both experimental and analytical modes.  Does NOT
        mutate any instance state.

        Parameters
        ----------
        t : float
            Simulation time [s].

        Returns
        -------
        float
            Thrust in Newtons (≥ 0).
        """
        if t <= 0.0 or t > self.burn_time:
            return 0.0

        if self.use_experimental_thrust:
            if self.thrust_interpolator is None:
                return 0.0
            return max(0.0, float(self.thrust_interpolator(t)))

        # Analytical mode
        t_norm = t / self.burn_time
        try:
            shape = self._shape_function(t_norm)
            if self._shape_integral_cached > 0.0:
                # Scale so that the area under the curve ≈ mean_thrust * burn_time
                correction = self.mean_thrust / (self.max_thrust * self._shape_integral_cached)
                thrust = shape * correction * self.max_thrust
            else:
                thrust = shape * self.mean_thrust
            return float(max(0.0, min(thrust, self.max_thrust)))
        except Exception as exc:
            logging.error("_thrust_at_time analytical fallback: %s", exc)
            return self._fallback_thrust_value(t_norm)

    def _precompute_cumulative_impulse(self) -> None:
        """
        Build a cumulative impulse look-up table over [0, burn_time].

        Sampling 501 points is done once at engine creation so that
        ``_calculate_performance`` can look up total impulse delivered
        in O(log N) via ``np.interp`` instead of re-integrating every
        simulation step.
        """
        N = 500
        t_arr = np.linspace(0.0, self.burn_time, N + 1)
        T_arr = np.array([self._thrust_at_time(ti) for ti in t_arr])

        cumul = np.zeros(N + 1)
        for i in range(1, N + 1):
            cumul[i] = cumul[i - 1] + 0.5 * (T_arr[i - 1] + T_arr[i]) * (t_arr[i] - t_arr[i - 1])

        self._cumul_time_arr = t_arr
        self._cumul_impulse_arr = cumul

        measured  = float(cumul[-1])
        expected  = self.propellant_mass * self.specific_impulse * 9.80665
        error_pct = abs(measured - expected) / expected * 100.0 if expected > 0.0 else 0.0
        logging.info(
            "Cumulative impulse table ready: measured=%.1f N\u00b7s, "
            "expected=%.1f N\u00b7s (%.1f%% diff).",
            measured, expected, error_pct,
        )

    # ------------------------------------------------------------------
    # Retained for backward compatibility – delegates to _thrust_at_time
    # ------------------------------------------------------------------

    def _calculate_experimental_thrust(self, time=None):
        """Retained for backward compatibility – delegates to _thrust_at_time."""
        t = time if time is not None else self.time
        return self._thrust_at_time(t)

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

    def _calculate_performance(self) -> None:
        """
        Unified performance calculation (B06, B07, B08).

        Single computation flow for both experimental and analytical modes:

        1. Look up cumulative impulse at current time → propellant state.
        2. Check burnout condition (burn time exceeded OR propellant gone).
        3. Get instantaneous thrust via ``_thrust_at_time``.
        4. Derive ``mass_flux = thrust / (Isp · g0)`` — *same formula in
           both modes* so thrust and mass consumption are always consistent.
        """
        try:
            g0 = 9.80665

            # ── 1. Propellant accounting (B07) ──────────────────────────────
            t_query = float(np.clip(self.time, 0.0, self.burn_time))
            cumul_impulse = float(
                np.interp(t_query, self._cumul_time_arr, self._cumul_impulse_arr)
            )
            propellant_consumed = min(
                cumul_impulse / (self.specific_impulse * g0),
                self.propellant_mass,
            )
            remaining = max(0.0, self.propellant_mass - propellant_consumed)

            # ── 2. Burnout condition (B08) ───────────────────────────────────
            burned_out = (self.time > self.burn_time) or (remaining <= 0.0)

            # Update B01 contract attributes
            self.propellant_consumed     = propellant_consumed
            self.remaining_propellant    = remaining
            self.total_impulse_delivered = cumul_impulse
            self.burnout_reached         = burned_out

            if burned_out:
                self._thrust     = 0.0
                self._mass_flux  = 0.0
                self.gas_speed   = 0.0
                self.exit_pressure = self.ambient_pressure
                self.actual_isp  = 0.0
                return

            # ── 3. Instantaneous thrust (B06) ────────────────────────────────
            raw_thrust = self._thrust_at_time(self.time)

            if raw_thrust <= 0.0:
                self._thrust     = 0.0
                self._mass_flux  = 0.0
                self.gas_speed   = 0.0
                self.exit_pressure = self.ambient_pressure
                self.actual_isp  = 0.0
                return

            # ── 4. Consistent mass_flux (B06) ────────────────────────────────
            self._thrust     = raw_thrust
            self._mass_flux  = raw_thrust / (self.specific_impulse * g0)
            self.gas_speed   = self.specific_impulse * g0
            self.exit_pressure = self.ambient_pressure   # simplified nozzle model
            self.actual_isp  = self.specific_impulse

        except Exception as exc:
            logging.error("Performance calculation error: %s", exc)
            self._fallback_performance()

    def _fallback_performance(self) -> None:
        """
        Fallback performance calculation used when the primary path raises.

        Approximates a constant-thrust burn and updates B01 contract
        attributes with linear interpolation so callers always see
        consistent state.
        """
        g0 = 9.80665
        active = 0.0 < self.time <= self.burn_time
        self._thrust    = self.mean_thrust if active else 0.0
        self._mass_flux = self.mean_thrust / (self.specific_impulse * g0) if active else 0.0
        self.gas_speed  = self.specific_impulse * g0 if active else 0.0
        self.exit_pressure = self.ambient_pressure
        self.actual_isp = self.specific_impulse if active else 0.0
        # Approximate B01 contract attributes linearly
        frac = float(np.clip(self.time / self.burn_time, 0.0, 1.0)) if self.burn_time > 0 else 0.0
        self.propellant_consumed     = self.propellant_mass * frac
        self.remaining_propellant    = max(0.0, self.propellant_mass - self.propellant_consumed)
        self.total_impulse_delivered = self.propellant_consumed * self.specific_impulse * g0
        self.burnout_reached         = self.time > self.burn_time

    def _calculate_thrust_curve(self) -> float:
        """Analytical thrust at current time.  Thin wrapper over _thrust_at_time."""
        return self._thrust_at_time(self.time)

    def _fallback_thrust_value(self, t_norm: float) -> float:
        """
        Simple piecewise-linear fallback used when *_shape_function* raises.

        Parameters
        ----------
        t_norm : float
            Normalised time in [0, 1].
        """
        if 0.0 < t_norm < 0.05:
            return self.max_thrust * (t_norm / 0.05) * 0.3
        elif 0.05 <= t_norm < 0.15:
            return self.max_thrust * (0.3 + 0.5 * (t_norm - 0.05) / 0.10)
        elif 0.15 <= t_norm < 0.25:
            return self.max_thrust * (0.8 + 0.2 * (t_norm - 0.15) / 0.10)
        elif 0.25 <= t_norm < 0.75:
            return self.max_thrust * 0.95
        elif 0.75 <= t_norm < 0.85:
            return self.max_thrust * (0.95 - 0.3 * (t_norm - 0.75) / 0.10)
        elif 0.85 <= t_norm < 0.95:
            return self.max_thrust * (0.65 - 0.4 * (t_norm - 0.85) / 0.10)
        elif t_norm <= 1.0:
            return self.max_thrust * (0.25 - 0.25 * (t_norm - 0.95) / 0.05)
        return 0.0

    def validate_thrust_curve(self) -> dict:
        """
        Validate that the thrust curve produces the expected mean thrust.

        Uses ``_thrust_at_time`` so there is no ``self.time`` mutation.
        The tolerance is ±5 % of ``mean_thrust``.

        Returns
        -------
        dict
            Keys: valid, calculated_mean, expected_mean, error_percent,
            max_thrust_used.
        """
        N = 200
        t_samples   = [(i + 0.5) / N * self.burn_time for i in range(N)]
        thrust_vals = [self._thrust_at_time(t) for t in t_samples]

        calculated_mean = float(np.mean(thrust_vals))
        error = abs(calculated_mean - self.mean_thrust) / self.mean_thrust

        result = {
            'valid': error < 0.05,
            'calculated_mean': round(calculated_mean, 3),
            'expected_mean': self.mean_thrust,
            'error_percent': round(error * 100, 2),
            'max_thrust_used': round(max(thrust_vals), 3) if thrust_vals else 0.0,
        }
        if not result['valid']:
            logging.warning("Thrust curve validation: %s", result)
        return result

    def get_performance_metrics(self):
        """
        Return comprehensive performance metrics.

        Includes the B01 contract attributes so callers can track propulsion
        state without inspecting internal engine fields directly.

        Returns
        -------
        dict
            Complete performance metrics in SI units.
        """
        return {
            # Core outputs
            'thrust': self._thrust,
            'mass_flow': self._mass_flux,
            'specific_impulse': self.actual_isp,
            # Nozzle / thermodynamic
            'characteristic_velocity': self.characteristic_velocity,
            'thrust_coefficient': self.ideal_thrust_coefficient,
            'exit_pressure': self.exit_pressure,
            'exit_velocity': self.gas_speed,
            'chamber_pressure': self.mean_chamber_pressure,
            'throat_area': self.throat_area,
            'exit_area': self.exit_area,
            # B01 contract attributes
            'thrust_source': self.thrust_source,
            'propellant_consumed': self.propellant_consumed,
            'remaining_propellant': self.remaining_propellant,
            'total_impulse_delivered': self.total_impulse_delivered,
            'burnout_reached': self.burnout_reached,
        }

    def get_thrust_curve_info(self):
        """Return information about the loaded thrust curve."""
        if not self.use_experimental_thrust or self._curve_data is None:
            return {"available": False}

        cd = self._curve_data
        return {
            "available": True,
            "data_points": cd.n_points,
            "burn_time": cd.duration,
            "max_thrust": cd.max_thrust,
            "mean_thrust": cd.mean_thrust,
            "total_impulse": cd.total_impulse,
            "unit_declared": cd.unit_declared,
            "source": cd.source,
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