# Author: Nicolas Sturm
#         Rocket Simulator - Aerodynamic heating (Phase 4)

"""
Aerodynamic heating / thermodynamics module.

Enabled by the panel method's surface pressure distribution Cp(x, theta)
(src/models/panel_method.py::get_surface_pressure). For each surface panel:

    1. Local edge Mach M_e from the isentropic inversion of Cp at freestream M_inf
       (subsonic/transonic; supersonic panels use the same engineering inversion
       on the Ackeret Cp, a documented approximation behind shocks).
    2. Edge temperature T_e = T_inf / (1 + (gamma-1)/2 M_e^2); edge pressure
       p_e = p_inf (1 + gamma M_inf^2 Cp / 2).
    3. Recovery temperature T_r = T_e (1 + r (gamma-1)/2 M_e^2), with recovery
       factor r = Pr^0.5 (laminar, ~0.85) or Pr^(1/3) (turbulent, ~0.89).
    4. Eckert reference temperature T* = 0.5 (T_w + T_e) + 0.22 (T_r - T_e);
       transport properties mu*, rho* = p_e/(R T*), cp* = gamma R/(gamma-1)
       evaluated at T* (Sutherland law for mu*).
    5. Local skin friction Cf from flat-plate correlations at Re_x with the
       reference-temperature properties; Reynolds analogy
       St = Cf/2 Pr^(-2/3) (turbulent) or Cf/2 Pr^(-1/2) (laminar),
       h = St rho* V_e cp*, heat flux q = h (T_r - T_w).

Aggregates: max heat flux and its location, stagnation (nose) temperature,
total heat load rate Qdot = sum q_i A_i. The stagnation point uses the adiabatic
stagnation temperature (r = 1 at M_e = 0, i.e. Cp -> Cp_stag -> Newtonian 2 in the
supersonic limit).

References: Eckert reference-temperature method; Reynolds analogy
(Anderson, "Hypersonics and High Temperature Gas Dynamics"); Fay-Riddell
stagnation heating (engineering form used for the nose tip).
"""

import logging
import math
from typing import Any, Dict, Optional, Tuple

import numpy as np

from src.utils.simulation_constants import AerodynamicsConstants as ADC

logger = logging.getLogger(__name__)

GAMMA_AIR = 1.4
R_AIR = 287.05          # J/(kg K)
PRANDTL = 0.71
SUTHERLAND_C1 = 1.458e-6
SUTHERLAND_S = 110.4    # K
# Laminar-turbulent transition threshold (critical local Re_x, flat plate ~5e5).
# Shared with the panel method skin friction via AerodynamicsConstants.
RE_LAMINAR_MAX = ADC.LAMINAR_TURBULENT_RE

RECOVERY_LAMINAR = PRANDTL ** 0.5    # ~0.84
RECOVERY_TURBULENT = PRANDTL ** (1.0 / 3.0)  # ~0.89


def sutherland_mu(T: float) -> float:
    """Dynamic viscosity of air [Pa s] via Sutherland's law."""
    return SUTHERLAND_C1 * T ** 1.5 / (T + SUTHERLAND_S)


def local_mach_from_cp(Cp: np.ndarray, M_inf: float, gamma: float = GAMMA_AIR) -> np.ndarray:
    """
    Local edge Mach number from the pressure coefficient (isentropic inversion).

    Cp = (2/(gamma M_inf^2)) (p_e/p_inf - 1),  p_e/p_inf = (p0/p_e)^(-gamma/(gamma-1)) ...
    Clamped to M_e >= 0 (Cp above stagnation gives M_e = 0).
    """
    p_ratio = 1.0 + 0.5 * gamma * M_inf ** 2 * np.asarray(Cp, dtype=float)
    p_ratio = np.maximum(p_ratio, 1e-6)
    t0_ratio = (1.0 + 0.5 * (gamma - 1.0) * M_inf ** 2)  # p0/p_inf ^ ((g-1)/g) base
    m_e2 = (2.0 / (gamma - 1.0)) * (t0_ratio / np.power(p_ratio, (gamma - 1.0) / gamma) - 1.0)
    return np.sqrt(np.maximum(m_e2, 0.0))


def recovery_temperature(T_e: np.ndarray, M_e: np.ndarray, recovery: float,
                         gamma: float = GAMMA_AIR) -> np.ndarray:
    """Adiabatic wall recovery temperature T_r = T_e (1 + r (gamma-1)/2 M_e^2)."""
    return T_e * (1.0 + recovery * 0.5 * (gamma - 1.0) * M_e ** 2)


def eckert_reference_temperature(T_w: float, T_e: np.ndarray, T_r: np.ndarray) -> np.ndarray:
    """Eckert reference temperature T* = 0.5 (T_w + T_e) + 0.22 (T_r - T_e)."""
    return 0.5 * (T_w + T_e) + 0.22 * (T_r - T_e)


def stagnation_temperature(T_inf: float, M_inf: float, gamma: float = GAMMA_AIR) -> float:
    """Adiabatic stagnation temperature T0 = T_inf (1 + (gamma-1)/2 M_inf^2)."""
    return T_inf * (1.0 + 0.5 * (gamma - 1.0) * M_inf ** 2)


def _local_cf(re_x: np.ndarray, turbulent: np.ndarray) -> np.ndarray:
    """Flat-plate local skin friction coefficient (laminar Blasius / turbulent)."""
    cf = np.empty_like(re_x)
    lam = ~turbulent
    re = np.maximum(re_x, 1.0)
    cf[lam] = 0.664 / np.sqrt(re[lam])
    cf[~lam] = 0.0592 / re[~lam] ** 0.2
    return cf


def surface_heating(
    aero: Any,
    mach: float,
    height: float,
    T_inf: float,
    p_inf: float,
    T_wall: float = 300.0,
    gamma: float = GAMMA_AIR,
) -> Optional[Dict[str, Any]]:
    """
    Per-panel aerodynamic heating for a panel-method aero object.

    Args:
        aero: IAerodynamics instance exposing get_surface_pressure() (panel method)
        mach: freestream Mach
        height: altitude [m] (for logging/reference)
        T_inf: freestream static temperature [K]
        p_inf: freestream static pressure [Pa]
        T_wall: wall temperature [K]

    Returns:
        dict with per-panel arrays (x, az, Cp, M_e, T_e, T_r, q) plus aggregates:
        max_heat_flux [W/m^2], its location (x_max, az_max), stagnation_temperature [K],
        total_heat_load_rate [W]. None if the aero model has no surface pressure.
    """
    get_cp = getattr(aero, 'get_surface_pressure', None)
    if not callable(get_cp):
        return None
    try:
        x, az, Cp = get_cp()
    except Exception as e:
        logger.warning(f"surface_heating: no Cp available: {e}")
        return None

    Cp = np.asarray(Cp, dtype=float)
    M_inf = float(mach)

    # Edge conditions per panel (isentropic: T0 and p0 are constant along a streamline)
    M_e = local_mach_from_cp(Cp, M_inf, gamma)
    T_e = T_inf * (1.0 + 0.5 * (gamma - 1.0) * M_inf ** 2) / (1.0 + 0.5 * (gamma - 1.0) * M_e ** 2)
    p_e = p_inf * (1.0 + 0.5 * gamma * M_inf ** 2 * Cp)

    # Boundary layer regime: two passes. First guess at freestream properties,
    # then re-decide at the reference-temperature Re (re_star) so that the
    # regime, recovery factor and Cf all use the SAME Reynolds number
    # (at high Mach T* >> T_inf, so re_star < re_x and the regime can flip).
    V_e = M_e * np.sqrt(gamma * R_AIR * T_e)
    # characteristic length per strip = x (distance from nose tip)
    x_len = np.maximum(x, 1e-3)[:, None]
    mu_inf = sutherland_mu(T_inf)
    rho_inf = p_inf / (R_AIR * T_inf)
    re_x = rho_inf * np.maximum(V_e, 1e-6) * x_len / mu_inf
    turbulent = re_x > RE_LAMINAR_MAX

    for _ in range(2):
        recovery = np.where(turbulent, RECOVERY_TURBULENT, RECOVERY_LAMINAR)
        T_r = recovery_temperature(T_e, M_e, recovery, gamma)
        T_star = eckert_reference_temperature(T_wall, T_e, T_r)
        mu_star = sutherland_mu(T_star)
        rho_star = p_e / (R_AIR * T_star)
        re_star = rho_star * np.maximum(V_e, 1e-6) * x_len / mu_star
        turbulent = re_star > RE_LAMINAR_MAX
    cp_star = gamma * R_AIR / (gamma - 1.0)

    cf = _local_cf(re_star, turbulent)

    # Reynolds analogy
    pr = PRANDTL
    st = np.where(turbulent, cf / 2.0 * pr ** (-2.0 / 3.0), cf / 2.0 * pr ** (-0.5))
    h = st * rho_star * np.maximum(V_e, 1e-6) * cp_star
    q = h * (T_r - T_wall)  # [W/m^2]

    # Stagnation (nose tip): adiabatic stagnation temperature
    T_stag = stagnation_temperature(T_inf, M_inf, gamma)

    # Aggregates
    q_flat = q.ravel()
    i_max = int(np.argmax(q_flat))
    n_theta = Cp.shape[1]
    x_max = float(x[i_max // n_theta])
    az_max = float(az[i_max % n_theta])

    # Total heat load rate needs panel areas: recompute from mesh if available
    total_q = None
    mesh = getattr(aero, 'mesh', None)
    if mesh is not None:
        cell_area = mesh.cell_area  # (N, 1)
        total_q = float(np.sum(q * cell_area))

    return {
        'x': x, 'az': az, 'Cp': Cp, 'M_e': M_e, 'T_e': T_e, 'T_r': T_r,
        'q': q, 'mach': M_inf, 'T_inf': T_inf, 'p_inf': p_inf, 'T_wall': T_wall,
        'max_heat_flux': float(np.max(q_flat)),
        'x_max': x_max, 'az_max': az_max,
        'stagnation_temperature': float(T_stag),
        'total_heat_load_rate': total_q,
        'turbulent_fraction': float(np.mean(turbulent)),
        're_star_max': float(np.max(re_star)),
    }


__all__ = [
    'surface_heating',
    'local_mach_from_cp',
    'recovery_temperature',
    'eckert_reference_temperature',
    'stagnation_temperature',
    'sutherland_mu',
    'GAMMA_AIR', 'R_AIR', 'PRANDTL',
]
