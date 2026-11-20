# Author: Rocket Simulator Team
#         Solid Rocket Motor (SRM) engine model

"""
Physics-based solid rocket motor engine driven by grain design.

Implements the quasi-steady internal ballistics method recommended by
R. Nakka (http://www.nakka-rocketry.net) for solid rocket motor design:

1. Grain geometry gives the burning surface Ab(web) as the web burns
   (see ``src.models.grain``).
2. Propellant burn rate follows the Saint-Robert / Vieille law
   ``r_b = a * Pc^n``.
3. Chamber pressure equilibrium (choked nozzle, mass balance):
   ``rho_p * Ab * r_b = Pc * At / c*``  =>  with Kn = Ab/At
   ``Pc = (rho_p * a * c* * Kn)^(1/(1-n))``
4. Mass flow ``mdot = Pc * At / c*``.
5. Thrust ``F = Cf * Pc * At`` with the isentropic nozzle thrust coefficient
   ``Cf = Gamma*sqrt(2g/(g-1)*(1-(pe/pc)^((g-1)/g))) + eps*(pe-pa)/pc``,
   where pe/pc follows from the expansion ratio eps = Ae/At.  Splitting the
   pressure term lets the thrust track ambient pressure (altitude) as
   ``F(t, pa) = Cf_m*Pc(t)*At + (pe(t) - pa)*Ae``.
6. Burn progression: ``dw/dt = r_b(Pc(w))`` is integrated on a web grid to
   obtain t(web); burnout when the remaining propellant falls below the
   sliver fraction of the initial grain mass.

The class implements ``IEngine`` and exposes the same B01 contract
attributes as ``EnhancedEngine`` (``thrust_source``, ``propellant_consumed``,
``remaining_propellant``, ``total_impulse_delivered``, ``burnout_reached``),
so it can be injected anywhere an ``IEngine`` is expected.  An experimental
thrust curve (CSV) may optionally override the computed curve.

References:
    - Nakka, R. "Solid Rocket Motor Design" (nakka-rocketry.net)
    - Sutton, G. P., & Biblarz, O. (2016). Rocket Propulsion Elements, ch. 3 & 12.
"""

import logging
from math import sqrt
from typing import Optional, cast

import numpy as np
from scipy.integrate import cumulative_trapezoid
from scipy.interpolate import interp1d

from src.models.grain import GrainGeometry, create_grain
from src.models.interfaces import IEngine
from src.utils.simulation_constants import EngineConstants as EC
from src.utils.simulation_constants import RocketConstants as RC
from src.utils.simulation_errors import InputValidationError
from src.utils.thrust_processor import ThrustCurveData, ThrustCurveProcessor

logger = logging.getLogger(__name__)

G0 = EC.STANDARD_GRAVITY_G0

#: Default propellant / motor values (APCP-like composite propellant)
DEFAULT_PROPELLANT_DENSITY = 1800.0        # [kg/m^3]
DEFAULT_BURN_RATE_A = 5.0                  # [mm/s] at 1 MPa, r = a*P[MPa]^n
DEFAULT_BURN_RATE_N = 0.30                 # [-] pressure exponent
DEFAULT_CHAMBER_TEMPERATURE = 3200.0       # [K]
DEFAULT_GAS_CONSTANT = 320.0               # [J/(kg*K)] (M ~ 26 g/mol)
DEFAULT_GAMMA = 1.20                       # [-]
DEFAULT_SLIVER_FRACTION = 0.005            # [-] burnout mass fraction


def gamma_function(gamma: float) -> float:
    """Isentropic Gamma function: sqrt(g)*((2/(g+1))^((g+1)/(2*(g-1))))."""
    return sqrt(gamma) * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))


def characteristic_velocity(gas_constant: float, chamber_temperature: float,
                            gamma: float) -> float:
    """c* = sqrt(R*Tc/gamma) / Gamma(gamma)  [m/s]."""
    return sqrt(gas_constant * chamber_temperature / gamma) / gamma_function(gamma)


def exit_mach_from_expansion_ratio(expansion_ratio: float, gamma: float) -> float:
    """Supersonic exit Mach from the area-Mach relation (bisection)."""
    def area_ratio(m: float) -> float:
        return (1.0 / m) * ((2.0 / (gamma + 1.0))
                            * (1.0 + 0.5 * (gamma - 1.0) * m * m)) ** (
                                (gamma + 1.0) / (2.0 * (gamma - 1.0)))
    lo, hi = 1.0001, 100.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if area_ratio(mid) < expansion_ratio:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def burn_rate_coefficient_si(a: float, n: float, unit: str = 'mm/s',
                             pressure_unit: str = 'MPa') -> float:
    """Convert a Nakka-style burn-rate coefficient to SI (m/s per Pa^n).

    ``r = a_si * Pc[Pa]^n`` with ``a_si = a * length_scale / pressure_scale^n``,
    e.g. Nakka's usual ``r[mm/s] = a * Pc[MPa]^n``.
    """
    length_scale = {'mm/s': 1e-3, 'm/s': 1.0}.get(unit.lower())
    pressure_scale = {'mpa': 1e6, 'pa': 1.0}.get(pressure_unit.lower())
    if length_scale is None or pressure_scale is None:
        raise InputValidationError(
            f"Unknown burn-rate units: unit={unit!r}, pressure_unit={pressure_unit!r}"
        )
    return a * length_scale / pressure_scale ** n


class SolidMotorEngine(IEngine):
    """Solid rocket motor engine with grain-driven internal ballistics.

    Implements ``IEngine``; thrust and mass flow are computed from the
    grain burning-surface evolution and the chamber-pressure equilibrium,
    and vary with ambient pressure (altitude) through the nozzle pressure
    term.
    """

    def __init__(self, grain: GrainGeometry,
                 propellant_density: float = DEFAULT_PROPELLANT_DENSITY,
                 burn_rate_a: float = DEFAULT_BURN_RATE_A,
                 burn_rate_n: float = DEFAULT_BURN_RATE_N,
                 throat_diameter: float = 0.02,
                 exit_diameter: float = 0.04,
                 ambient_pressure: float = RC.DEFAULT_PRESSURE,
                 time: float = 0.0,
                 burn_rate_unit: str = 'mm/s',
                 burn_rate_pressure_unit: str = 'MPa',
                 chamber_temperature: float = EC.DEFAULT_CHAMBER_TEMPERATURE,
                 gas_constant: float = EC.DEFAULT_GAS_CONSTANT,
                 gamma: float = EC.DEFAULT_GAMMA,
                 characteristic_velocity_value: Optional[float] = None,
                 sliver_fraction: float = DEFAULT_SLIVER_FRACTION,
                 n_web: int = 241,
                 n_time: int = 400,
                 rocket_mass: Optional[float] = None,
                 thrust_curve_file: Optional[str] = None,
                 thrust_curve_data: Optional[dict] = None,
                 thrust_curve_unit: str = 'N'):
        if propellant_density <= 0:
            raise InputValidationError("Propellant density must be positive")
        if burn_rate_a <= 0:
            raise InputValidationError("Burn-rate coefficient 'a' must be positive")
        if not 0.0 <= burn_rate_n < 1.0:
            raise InputValidationError(
                "Burn-rate exponent 'n' must be in [0, 1) for a stable motor"
            )
        if throat_diameter <= 0:
            raise InputValidationError("Throat diameter must be positive")
        if exit_diameter <= throat_diameter:
            raise InputValidationError("Exit diameter must be larger than throat diameter")
        if ambient_pressure < 0:
            raise InputValidationError("Ambient pressure cannot be negative")
        if time < 0:
            raise InputValidationError("Time cannot be negative")
        if not 0.0 < sliver_fraction < 0.5:
            raise InputValidationError("sliver_fraction must be in (0, 0.5)")

        self.grain = grain
        self.propellant_density = float(propellant_density)
        self.burn_rate_a = float(burn_rate_a)
        self.burn_rate_n = float(burn_rate_n)
        self.burn_rate_unit = burn_rate_unit
        self.burn_rate_pressure_unit = burn_rate_pressure_unit
        self.throat_diameter = float(throat_diameter)
        self.nozzle_exit_diameter = float(exit_diameter)
        self.ambient_pressure = float(ambient_pressure)
        self.time = float(time)
        self.chamber_temperature = float(chamber_temperature)
        self.gas_constant = float(gas_constant)
        self.gamma = float(gamma)
        self.sliver_fraction = float(sliver_fraction)

        self._a_si = burn_rate_coefficient_si(
            self.burn_rate_a, self.burn_rate_n,
            unit=burn_rate_unit, pressure_unit=burn_rate_pressure_unit)

        if characteristic_velocity_value is not None and characteristic_velocity_value > 0:
            self.characteristic_velocity = float(characteristic_velocity_value)
        else:
            self.characteristic_velocity = characteristic_velocity(
                self.gas_constant, self.chamber_temperature, self.gamma)

        self.throat_area = np.pi / 4.0 * self.throat_diameter ** 2
        self.exit_area = np.pi / 4.0 * self.nozzle_exit_diameter ** 2
        self.expansion_ratio = self.exit_area / self.throat_area
        self.exit_mach = exit_mach_from_expansion_ratio(self.expansion_ratio, self.gamma)
        self.pe_over_pc = (1.0 + 0.5 * (self.gamma - 1.0) * self.exit_mach ** 2) ** (
            -self.gamma / (self.gamma - 1.0))
        gamma_fn = gamma_function(self.gamma)
        self.momentum_thrust_coefficient = gamma_fn * sqrt(
            (2.0 * self.gamma / (self.gamma - 1.0))
            * (1.0 - self.pe_over_pc ** ((self.gamma - 1.0) / self.gamma))
        )

        self.propellant_mass = self.propellant_density * grain.propellant_volume()
        self.thrust_to_weight_ratio = 0.0
        self._rocket_mass = rocket_mass

        self.thrust_curve_file = thrust_curve_file
        self.thrust_curve_data = thrust_curve_data
        self.thrust_curve_unit = thrust_curve_unit
        self.thrust_interpolator = None
        self.use_experimental_thrust = False
        self._curve_data: ThrustCurveData | None = None
        self._load_thrust_curve()

        self._build_ballistics_tables(n_web=int(n_web), n_time=int(n_time))

        summary = self.summary()
        self.burn_time = summary['burn_time']
        self.specific_impulse = summary['specific_impulse']
        self.mean_thrust = summary['mean_thrust']
        self.max_thrust = summary['max_thrust']
        self.mean_chamber_pressure = summary['mean_chamber_pressure']
        self.max_chamber_pressure = summary['max_chamber_pressure']
        if rocket_mass is not None and rocket_mass > 0:
            self.thrust_to_weight_ratio = self.max_thrust / (rocket_mass * G0)

        self.thrust_source = 'experimental' if self.use_experimental_thrust else 'solid-grain'
        self.propellant_consumed = 0.0
        self.remaining_propellant = self.propellant_mass
        self.total_impulse_delivered = 0.0
        self.burnout_reached = False
        self._thrust = 0.0
        self._mass_flux = 0.0
        self._chamber_pressure = 0.0
        self._exit_pressure = 0.0
        self._exit_velocity = 0.0
        self._thrust_coefficient = 0.0
        self._actual_isp = 0.0
        self._web = 0.0
        self._calculate_performance()

    def _load_thrust_curve(self) -> None:
        """Optionally load an experimental thrust curve overriding the model."""
        has_file = bool(self.thrust_curve_file)
        has_dict = bool(self.thrust_curve_data)
        if not has_file and not has_dict:
            return
        if has_file:
            curve_data = ThrustCurveProcessor.from_csv(
                cast(str, self.thrust_curve_file), unit=self.thrust_curve_unit)
        else:
            curve_data = ThrustCurveProcessor.from_dict(
                cast(dict, self.thrust_curve_data), unit=self.thrust_curve_unit)
        time_arr = np.array(curve_data.time_s)
        thrust_arr = np.array(curve_data.thrust_N)
        self.thrust_interpolator = interp1d(
            time_arr, thrust_arr, kind='linear', bounds_error=False,
            fill_value=(float(thrust_arr[0]), 0.0))
        self._curve_data = curve_data
        self.use_experimental_thrust = True
        logger.info("SolidMotorEngine: experimental curve loaded (%d points, %.2f s)",
                    curve_data.n_points, curve_data.duration)

    def _build_ballistics_tables(self, n_web: int, n_time: int) -> None:
        """Precompute Pc(w), r_b(w), t(w) on a web grid and the time tables."""
        w_max = self.grain.web_limit()
        w = np.linspace(0.0, w_max, n_web)
        ab = np.array([self.grain.burning_surface(wi) for wi in w])
        v_rem = np.array([self.grain.remaining_volume(wi) for wi in w])
        v0 = self.grain.propellant_volume()

        sliver_mask = v_rem >= self.sliver_fraction * v0
        if not sliver_mask.any():
            sliver_mask[0] = True
        w_end = w[sliver_mask].max()
        keep = w <= w_end + 1e-12
        w, ab, v_rem = w[keep], ab[keep], v_rem[keep]

        kn = ab / self.throat_area
        pc = (self.propellant_density * self._a_si * self.characteristic_velocity * kn) ** (
            1.0 / (1.0 - self.burn_rate_n))
        r_b = self._a_si * pc ** self.burn_rate_n
        r_b = np.maximum(r_b, 1e-6)
        t = cumulative_trapezoid(1.0 / r_b, w, initial=0.0)
        t = np.maximum.accumulate(t) + np.arange(len(t)) * 1e-12
        burn_time = float(t[-1])
        if not np.isfinite(burn_time) or burn_time <= 0.0:
            raise InputValidationError("Solid motor burn time is not finite; check grain/nozzle sizing")

        t_arr = np.linspace(0.0, burn_time, n_time)
        w_t = np.interp(t_arr, t, w)
        pc_t = np.interp(w_t, w, pc)
        ab_t = np.interp(w_t, w, ab)
        v_t = np.interp(w_t, w, v_rem)
        r_b_t = np.maximum(self._a_si * pc_t ** self.burn_rate_n, 1e-12)

        f_mom = self.momentum_thrust_coefficient * pc_t * self.throat_area
        pe_ae = self.pe_over_pc * pc_t * self.exit_area
        mdot = pc_t * self.throat_area / self.characteristic_velocity
        f_ref = f_mom + pe_ae - self.ambient_pressure * self.exit_area
        f_ref = np.maximum(f_ref, 0.0)
        cumul = cumulative_trapezoid(f_ref, t_arr, initial=0.0)
        consumed = self.propellant_density * np.maximum(v0 - v_t, 0.0)

        self._w_arr = w
        self._t_arr = t_arr
        self._w_t = w_t
        self._pc_t = pc_t
        self._ab_t = ab_t
        self._r_b_t = r_b_t
        self._f_mom_t = f_mom
        self._pe_ae_t = pe_ae
        self._mdot_t = mdot
        self._cumul_t = cumul
        self._consumed_t = consumed
        self._v0 = v0
        self._burn_time = burn_time

    def _thrust_at_time(self, t: float) -> float:
        """Instantaneous thrust at time t with the current ambient pressure."""
        if t < 0.0 or t > self._burn_time:
            return 0.0
        if self.use_experimental_thrust and self.thrust_interpolator is not None:
            return max(0.0, float(self.thrust_interpolator(t)))
        f_mom = float(np.interp(t, self._t_arr, self._f_mom_t))
        pe_ae = float(np.interp(t, self._t_arr, self._pe_ae_t))
        return max(0.0, f_mom + pe_ae - self.ambient_pressure * self.exit_area)

    def _calculate_performance(self) -> None:
        """Update thrust, mass flow and propellant state at ``self.time``."""
        t = float(np.clip(self.time, 0.0, self._burn_time))
        burned_out = self.time > self._burn_time

        self._web = float(np.interp(t, self._t_arr, self._w_t))
        self._chamber_pressure = float(np.interp(t, self._t_arr, self._pc_t))
        consumed = float(np.interp(t, self._t_arr, self._consumed_t))
        self.propellant_consumed = float(min(consumed, self.propellant_mass))
        self.remaining_propellant = max(0.0, self.propellant_mass - self.propellant_consumed)
        self.total_impulse_delivered = float(np.interp(t, self._t_arr, self._cumul_t))
        self.burnout_reached = burned_out or self.remaining_propellant <= 0.0

        if self.burnout_reached or self.use_experimental_thrust:
            thrust = self._thrust_at_time(self.time)
        else:
            f_mom = float(np.interp(t, self._t_arr, self._f_mom_t))
            pe_ae = float(np.interp(t, self._t_arr, self._pe_ae_t))
            thrust = max(0.0, f_mom + pe_ae - self.ambient_pressure * self.exit_area)

        self._thrust = 0.0 if self.burnout_reached else thrust
        if self.use_experimental_thrust:
            isp = self.specific_impulse if self.specific_impulse > 0 else 200.0
            self._mass_flux = self._thrust / (isp * G0) if self._thrust > 0 else 0.0
            self._exit_velocity = isp * G0
            self._actual_isp = isp if self._thrust > 0 else 0.0
        else:
            self._mass_flux = float(np.interp(t, self._t_arr, self._mdot_t)) if not self.burnout_reached else 0.0
            self._exit_velocity = self._thrust / self._mass_flux if self._mass_flux > 0 else 0.0
            self._actual_isp = self._exit_velocity / G0 if self._mass_flux > 0 else 0.0
        self._exit_pressure = self.pe_over_pc * self._chamber_pressure
        self._thrust_coefficient = (
            self._thrust / (self._chamber_pressure * self.throat_area)
            if self._chamber_pressure > 0 else 0.0)

    def summary(self) -> dict:
        """Derived scalar performance summary (used to fill legacy engine fields)."""
        f_ref = self._f_mom_t + self._pe_ae_t - self.ambient_pressure * self.exit_area
        f_ref = np.maximum(f_ref, 0.0)
        total_impulse = float(self._cumul_t[-1])
        isp = total_impulse / (self.propellant_mass * G0) if self.propellant_mass > 0 else 0.0
        return {
            'burn_time': self._burn_time,
            'propellant_mass': self.propellant_mass,
            'total_impulse': total_impulse,
            'specific_impulse': isp,
            'mean_thrust': float(np.mean(f_ref)),
            'max_thrust': float(np.max(f_ref)),
            'mean_chamber_pressure': float(np.mean(self._pc_t)),
            'max_chamber_pressure': float(np.max(self._pc_t)),
            'mean_burning_surface': float(np.mean(self._ab_t)),
            'mass_flux': self.propellant_mass / self._burn_time,
            'gas_speed': isp * G0,
            'exit_pressure': self.pe_over_pc * float(np.mean(self._pc_t)),
            'nozzle_exit_diameter': self.nozzle_exit_diameter,
            'throat_diameter': self.throat_diameter,
            'characteristic_velocity': self.characteristic_velocity,
            'exit_mach': self.exit_mach,
            'expansion_ratio': self.expansion_ratio,
            'grain_type': self.grain.name,
            'web_limit': self.grain.web_limit(),
            'thrust_source': 'experimental' if self.use_experimental_thrust else 'solid-grain',
        }

    def validate_thrust_curve(self) -> dict:
        """Check the computed curve against the summary mean thrust (±5 %)."""
        n = 200
        t_samples = [(i + 0.5) / n * self._burn_time for i in range(n)]
        saved_pa = self.ambient_pressure
        try:
            thrust_vals = [self._thrust_at_time(t) for t in t_samples]
        finally:
            self.ambient_pressure = saved_pa
        calculated_mean = float(np.mean(thrust_vals)) if thrust_vals else 0.0
        error = (abs(calculated_mean - self.mean_thrust) / self.mean_thrust
                 if self.mean_thrust > 0 else 0.0)
        return {
            'valid': error < 0.05,
            'calculated_mean': round(calculated_mean, 3),
            'expected_mean': round(self.mean_thrust, 3),
            'error_percent': round(error * 100, 2),
            'max_thrust_used': round(max(thrust_vals), 3) if thrust_vals else 0.0,
        }

    def get_performance_metrics(self) -> dict:
        """Performance metrics dict (same keys as EnhancedEngine)."""
        return {
            'thrust': self._thrust,
            'mass_flow': self._mass_flux,
            'specific_impulse': self._actual_isp,
            'characteristic_velocity': self.characteristic_velocity,
            'thrust_coefficient': self._thrust_coefficient,
            'exit_pressure': self._exit_pressure,
            'exit_velocity': self._exit_velocity,
            'chamber_pressure': self._chamber_pressure,
            'throat_area': self.throat_area,
            'exit_area': self.exit_area,
            'thrust_source': self.thrust_source,
            'propellant_consumed': self.propellant_consumed,
            'remaining_propellant': self.remaining_propellant,
            'total_impulse_delivered': self.total_impulse_delivered,
            'burnout_reached': self.burnout_reached,
            'web_burned': self._web,
        }

    def get_thrust_curve_info(self) -> dict:
        """Info about the active thrust curve (computed or experimental)."""
        if self.use_experimental_thrust and self._curve_data is not None:
            cd = self._curve_data
            return {
                'available': True,
                'data_points': cd.n_points,
                'burn_time': cd.duration,
                'max_thrust': cd.max_thrust,
                'mean_thrust': cd.mean_thrust,
                'total_impulse': cd.total_impulse,
                'unit_declared': cd.unit_declared,
                'source': cd.source,
            }
        s = self.summary()
        return {
            'available': True,
            'data_points': len(self._t_arr),
            'burn_time': s['burn_time'],
            'max_thrust': s['max_thrust'],
            'mean_thrust': s['mean_thrust'],
            'total_impulse': s['total_impulse'],
            'unit_declared': 'N',
            'source': 'solid-grain',
        }

    def update(self, time: Optional[float] = None, ambient_pressure: Optional[float] = None) -> None:
        """Update engine state (IEngine contract)."""
        if time is not None:
            if time < 0:
                raise InputValidationError("Time cannot be negative")
            self.time = float(time)
        if ambient_pressure is not None:
            if ambient_pressure < 0:
                raise InputValidationError("Ambient pressure cannot be negative")
            self.ambient_pressure = float(ambient_pressure)
        self._calculate_performance()

    def get_thrust(self) -> float:
        return self._thrust

    def get_mass_flow(self) -> float:
        return self._mass_flux

    @property
    def thrust(self) -> float:
        return self._thrust

    @property
    def mass_flux(self) -> float:
        return self._mass_flux


def create_solid_motor(config: dict, time: float = 0.0,
                       ambient_pressure: float = RC.DEFAULT_PRESSURE,
                       rocket_mass: Optional[float] = None) -> SolidMotorEngine:
    """Build a SolidMotorEngine from a ``motor`` configuration dict.

    Expected structure::

        {
          "grain": {"type": "bates", "outer_diameter": ..., ...},
          "propellant": {"density": ..., "burn_rate_a": ..., "burn_rate_n": ...,
                         "burn_rate_unit": "mm/s", "burn_rate_pressure_unit": "MPa",
                         "chamber_temperature": ..., "gas_constant": ..., "gamma": ...,
                         "characteristic_velocity": optional},
          "nozzle": {"throat_diameter": ..., "exit_diameter": ...},
          "sliver_fraction": optional,
          "thrust_curve_file"/"thrust_curve_data"/"thrust_curve_unit": optional
        }
    """
    if not isinstance(config, dict):
        raise InputValidationError("Motor config must be a dict")
    grain_cfg = config.get('grain')
    if not grain_cfg:
        raise InputValidationError("Motor config is missing the 'grain' section")
    prop = dict(config.get('propellant', {}))
    nozzle = dict(config.get('nozzle', {}))
    if 'throat_diameter' not in nozzle:
        raise InputValidationError("Motor config nozzle is missing 'throat_diameter'")
    if 'exit_diameter' not in nozzle:
        raise InputValidationError("Motor config nozzle is missing 'exit_diameter'")

    grain = create_grain(grain_cfg)
    return SolidMotorEngine(
        grain=grain,
        propellant_density=prop.get('density', DEFAULT_PROPELLANT_DENSITY),
        burn_rate_a=prop.get('burn_rate_a', DEFAULT_BURN_RATE_A),
        burn_rate_n=prop.get('burn_rate_n', DEFAULT_BURN_RATE_N),
        throat_diameter=nozzle['throat_diameter'],
        exit_diameter=nozzle['exit_diameter'],
        ambient_pressure=ambient_pressure,
        time=time,
        burn_rate_unit=prop.get('burn_rate_unit', 'mm/s'),
        burn_rate_pressure_unit=prop.get('burn_rate_pressure_unit', 'MPa'),
        chamber_temperature=prop.get('chamber_temperature', DEFAULT_CHAMBER_TEMPERATURE),
        gas_constant=prop.get('gas_constant', DEFAULT_GAS_CONSTANT),
        gamma=prop.get('gamma', DEFAULT_GAMMA),
        characteristic_velocity_value=prop.get('characteristic_velocity'),
        sliver_fraction=config.get('sliver_fraction', DEFAULT_SLIVER_FRACTION),
        rocket_mass=rocket_mass,
        thrust_curve_file=config.get('thrust_curve_file'),
        thrust_curve_data=config.get('thrust_curve_data'),
        thrust_curve_unit=config.get('thrust_curve_unit', 'N'),
    )


__all__ = [
    'SolidMotorEngine',
    'create_solid_motor',
    'gamma_function',
    'characteristic_velocity',
    'exit_mach_from_expansion_ratio',
    'burn_rate_coefficient_si',
    'DEFAULT_PROPELLANT_DENSITY',
    'DEFAULT_BURN_RATE_A',
    'DEFAULT_BURN_RATE_N',
]
