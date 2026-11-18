# Author: Nicolas Sturm
#         Rocket Simulator - Aerodynamics analysis helpers (Phase 3)

"""
Aerodynamics analysis helpers for the GUI.

Qt-free functions used by the rocket settings "Aerodynamics" tab to compute
and compare aerodynamic curves (CD/CL/x_cp/stability vs Mach, Cp profile)
for the Barrowman model and the panel method.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.models.rocket.factory import create_aerodynamics

logger = logging.getLogger(__name__)

DEFAULT_MACHS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0, 2.5, 3.0]


def rocket_data_from_config(rocket_config: Dict[str, Any]) -> Dict[str, Any]:
    """Build the rocket_data dict (as used by the factory) from a rocket config."""
    return {
        'reference_area': rocket_config.get('reference_area', 0.01),
        'geometry': rocket_config.get('geometry', {}),
        'fuselage': rocket_config.get('fuselage', {}),
        'nosecone': rocket_config.get('nosecone', {}),
        'rear_section': rocket_config.get('rear_section', {}),
        'fins': rocket_config.get('fins', {}),
    }


def _mass_props_from_config(rocket_config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'CoM_before_burn': rocket_config.get('CoM_before_burn', {'x': 0.0, 'y': 0.0, 'z': 0.0}),
        'CoM_after_burn': rocket_config.get('CoM_after_burn', {'x': 0.0, 'y': 0.0, 'z': 0.0}),
    }


def analyze_aero_curves(
    rocket_config: Dict[str, Any],
    machs: Optional[List[float]] = None,
    alpha_deg: float = 5.0,
    methods: Tuple[str, ...] = ('barrowman', 'panel'),
    panel_options: Optional[Dict[str, Any]] = None,
    height: float = 0.0,
    density: float = 1.225,
) -> Dict[str, Dict[str, np.ndarray]]:
    """
    Compute CD, CL, C_Nalpha, x_cp and stability margin vs Mach for each method.

    Returns:
        {method: {'mach': arr, 'cd': arr, 'cl': arr, 'c_nalpha': arr,
                  'x_cp': arr, 'stability': arr}}
    """
    machs = list(machs) if machs else list(DEFAULT_MACHS)
    rocket_data = rocket_data_from_config(rocket_config)
    mass_before = rocket_config.get('CoM_before_burn', {'x': 0.0, 'y': 0.0, 'z': 0.0})
    mass_after = rocket_config.get('CoM_after_burn', {'x': 0.0, 'y': 0.0, 'z': 0.0})
    aero_cfg = rocket_config.get('aerodynamics', {}) or {}

    out: Dict[str, Dict[str, np.ndarray]] = {}
    for method in methods:
        opts = dict(panel_options or {})
        if not opts:
            opts = {k: aero_cfg[k] for k in ('n_axial', 'n_theta', 'include_fins', 'viscous_crossflow')
                    if k in aero_cfg} or None
        aero = create_aerodynamics(
            mach=0.0, angle_attack=alpha_deg, height=height, atmosphere=None,
            rocket_config=rocket_config,
            mass_props_before=mass_before,
            mass_props_after=mass_after,
            method=method,
            panel_options=opts,
        )
        cd_l, cl_l, cna_l, xcp_l, stab_l = [], [], [], [], []
        alpha_rad = math.radians(alpha_deg)
        for m in machs:
            aero.update(mach=m, angle_attack=alpha_deg, height=height, density=density)
            cd, cl = aero.get_coefficients()
            cd_l.append(cd)
            cl_l.append(cl)
            cna_l.append(cl / math.cos(alpha_rad) / alpha_rad if alpha_rad > 0 else 0.0)
            xcp_l.append(float(aero.get_center_of_pressure()[0]))
            stab_l.append(float(aero.get_stability_margin()))
        out[method] = {
            'mach': np.array(machs),
            'cd': np.array(cd_l),
            'cl': np.array(cl_l),
            'c_nalpha': np.array(cna_l),
            'x_cp': np.array(xcp_l),
            'stability': np.array(stab_l),
        }
    return out


def cp_profile(
    rocket_config: Dict[str, Any],
    mach: float = 0.3,
    alpha_deg: float = 5.0,
    panel_options: Optional[Dict[str, Any]] = None,
    height: float = 0.0,
    density: float = 1.225,
) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """
    Surface pressure coefficient profile along the body (panel method only).

    Returns:
        (x, Cp_mean_over_azimuth, Cp_windward) or None if the panel method
        is not applicable (e.g. missing geometry).
    """
    rocket_data = rocket_data_from_config(rocket_config)
    mass_before = rocket_config.get('CoM_before_burn', {'x': 0.0, 'y': 0.0, 'z': 0.0})
    mass_after = rocket_config.get('CoM_after_burn', {'x': 0.0, 'y': 0.0, 'z': 0.0})
    aero_cfg = rocket_config.get('aerodynamics', {}) or {}
    opts = dict(panel_options or {})
    if not opts:
        opts = {k: aero_cfg[k] for k in ('n_axial', 'n_theta', 'include_fins', 'viscous_crossflow')
                if k in aero_cfg} or None
    try:
        aero = create_aerodynamics(
            mach=mach, angle_attack=alpha_deg, height=height, atmosphere=None,
            rocket_config=rocket_config,
            mass_props_before=mass_before,
            mass_props_after=mass_after,
            method='panel',
            panel_options=opts,
        )
    except Exception as e:
        logger.warning(f"cp_profile: panel method unavailable: {e}")
        return None
    aero.update(mach=mach, angle_attack=alpha_deg, height=height, density=density)
    get_cp = getattr(aero, 'get_surface_pressure', None)
    if not callable(get_cp):
        return None
    x, az, Cp = get_cp()
    return x, Cp.mean(axis=1), Cp.min(axis=1)  # mean and most-negative (suction) per strip


__all__ = ['analyze_aero_curves', 'cp_profile', 'rocket_data_from_config', 'DEFAULT_MACHS']
