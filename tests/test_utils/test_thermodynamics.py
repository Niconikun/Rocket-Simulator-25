"""Tests for the aerodynamic heating module (Phase 4)."""

import json
import math
from pathlib import Path

import numpy as np
import pytest

from src.utils.thermodynamics import (
    GAMMA_AIR,
    local_mach_from_cp,
    recovery_temperature,
    eckert_reference_temperature,
    stagnation_temperature,
    surface_heating,
    sutherland_mu,
)
from src.models.rocket.factory import create_aerodynamics


def _campanil():
    return json.loads(Path('data/rockets/configs/campanil_1a.json').read_text())


def _panel_aero(cfg, **opts):
    o = {'n_axial': 32, 'n_theta': 12}
    o.update(opts)
    return create_aerodynamics(
        mach=0.0, angle_attack=0.0, height=0.0, atmosphere=None,
        rocket_config=cfg,
        mass_props_before=cfg['CoM_before_burn'],
        mass_props_after=cfg['CoM_after_burn'],
        method='panel', panel_options=o,
    )


# ---------------------------------------------------------------------------
# Relations
# ---------------------------------------------------------------------------

def test_local_mach_from_cp_zero_cp_returns_freestream():
    M = local_mach_from_cp(np.array([0.0, 0.0]), 0.8)
    assert np.allclose(M, 0.8)


def test_local_mach_from_cp_stagnation_gives_zero():
    M_inf = 0.8
    cp_stag = (2.0 / (GAMMA_AIR * M_inf ** 2)) * (
        (1.0 + 0.5 * (GAMMA_AIR - 1.0) * M_inf ** 2) ** (GAMMA_AIR / (GAMMA_AIR - 1.0)) - 1.0)
    M = local_mach_from_cp(np.array([cp_stag]), M_inf)
    assert M[0] == pytest.approx(0.0, abs=1e-6)


def test_recovery_temperature():
    T_inf, M = 288.15, 2.0
    T_e = T_inf / (1.0 + 0.2 * M ** 2)
    T_r = recovery_temperature(np.array([T_e]), np.array([M]), 0.89)[0]
    assert T_r == pytest.approx(T_e * (1.0 + 0.89 * 0.2 * 4.0))
    # M=0 -> T_r = T_e = T_inf
    assert recovery_temperature(np.array([T_inf]), np.array([0.0]), 0.89)[0] == pytest.approx(T_inf)


def test_eckert_reference_temperature_bounds():
    T_w, T_e, T_r = 300.0, 250.0, 500.0
    T_star = eckert_reference_temperature(T_w, np.array([T_e]), np.array([T_r]))[0]
    assert T_e < T_star < T_r
    assert T_star == pytest.approx(0.5 * (T_w + T_e) + 0.22 * (T_r - T_e))


def test_stagnation_temperature():
    assert stagnation_temperature(288.15, 0.0) == pytest.approx(288.15)
    assert stagnation_temperature(288.15, 2.0) == pytest.approx(288.15 * 1.8)


def test_sutherland_monotonic():
    assert sutherland_mu(200.0) < sutherland_mu(300.0) < sutherland_mu(500.0)
    assert sutherland_mu(288.15) == pytest.approx(1.789e-5, rel=0.02)


# ---------------------------------------------------------------------------
# Laminar-turbulent transition threshold
# ---------------------------------------------------------------------------

def test_transition_threshold_shared_constant():
    from src.utils.thermodynamics import RE_LAMINAR_MAX
    from src.utils.simulation_constants import AerodynamicsConstants as ADC
    from src.models.panel_method import LAMINAR_TURBULENT_RE
    assert RE_LAMINAR_MAX == ADC.LAMINAR_TURBULENT_RE == LAMINAR_TURBULENT_RE == 5.0e5


def test_local_cf_laminar_vs_turbulent():
    from src.utils.thermodynamics import _local_cf, RE_LAMINAR_MAX
    re = np.array([1.0e5, 1.0e7])
    turb = re > RE_LAMINAR_MAX
    cf = _local_cf(re, turb)
    assert cf[0] == pytest.approx(0.664 / math.sqrt(1.0e5))      # laminar Blasius
    assert cf[1] == pytest.approx(0.0592 / 1.0e7 ** 0.2)           # turbulent
    # below transition, laminar Cf is lower than the turbulent correlation
    assert 0.664 / math.sqrt(1.0e5) < 0.0592 / 1.0e5 ** 0.2


def test_regime_decided_at_reference_reynolds():
    # campanil is L=1.19 m: at M=0.01 Re_L ~ 2.8e5 < 5e5 -> all laminar;
    # at M=3 Re* is huge -> (nearly) all turbulent. The regime must follow the
    # reference-temperature Re, not the freestream Re.
    cfg = _campanil()
    aero = _panel_aero(cfg)
    aero.update(mach=0.01, angle_attack=1.0, height=0.0, density=1.225)
    res_low = surface_heating(aero, 0.01, 0.0, 288.15, 101325.0)
    assert res_low['re_star_max'] < 5.0e5
    assert res_low['turbulent_fraction'] == pytest.approx(0.0)  # all laminar
    aero.update(mach=3.0, angle_attack=1.0, height=0.0, density=1.225)
    res_high = surface_heating(aero, 3.0, 0.0, 288.15, 101325.0)
    assert res_high['turbulent_fraction'] > 0.9  # turbulent at M=3
    assert res_high['max_heat_flux'] > res_low['max_heat_flux']


def test_panel_skin_friction_laminar_branch():
    # At very low Re (M=0.01, Re_L ~ 2.8e5 < 5e5) the panel drag must use the
    # laminar (lower) Blasius Cf instead of the turbulent-only correlation.
    # Same wetted area / roughness in both branches, so compare directly.
    cfg = _campanil()
    aero = _panel_aero(cfg)
    aero.update(mach=0.01, angle_attack=0.0, height=0.0, density=1.225)
    cd_laminar = aero._skin_friction_cd(0.01)
    Re_L = aero.rho * (0.01 * aero.speed_of_sound) * aero.mesh.L / 1.789e-5
    assert Re_L < 5.0e5
    assert cd_laminar > 0
    aero.update(mach=0.5, angle_attack=0.0, height=0.0, density=1.225)  # Re_L ~ 1.4e7, turbulent
    cd_turbulent = aero._skin_friction_cd(0.5)
    assert cd_laminar < 0.6 * cd_turbulent  # laminar Cf is ~4.8x lower at Re=2.8e5


# ---------------------------------------------------------------------------
# Surface heating on the panel method
# ---------------------------------------------------------------------------

def test_surface_heating_campanil_supersonic():
    cfg = _campanil()
    aero = _panel_aero(cfg)
    M = 2.0
    aero.update(mach=M, angle_attack=3.0, height=0.0, density=1.225)
    res = surface_heating(aero, mach=M, height=0.0, T_inf=288.15, p_inf=101325.0, T_wall=300.0)
    assert res is not None
    assert res['max_heat_flux'] > 0
    assert res['stagnation_temperature'] == pytest.approx(288.15 * 1.8)
    # Max heating near the nose (small x)
    assert res['x_max'] < 0.5 * cfg['geometry']['total_length']
    assert res['total_heat_load_rate'] > 0
    # shapes
    n = res['q'].shape
    assert res['x'].shape[0] == n[0] and res['az'].shape[0] == n[1]


def test_surface_heating_increases_with_mach():
    cfg = _campanil()
    aero = _panel_aero(cfg)
    aero.update(mach=0.5, angle_attack=2.0, height=0.0, density=1.225)
    q_low = surface_heating(aero, 0.5, 0.0, 288.15, 101325.0)['max_heat_flux']
    aero.update(mach=2.0, angle_attack=2.0, height=0.0, density=1.225)
    q_high = surface_heating(aero, 2.0, 0.0, 288.15, 101325.0)['max_heat_flux']
    assert q_high > q_low


def test_surface_heating_none_for_barrowman():
    cfg = _campanil()
    aero = create_aerodynamics(
        mach=1.0, angle_attack=2.0, height=0.0, atmosphere=None,
        rocket_config=cfg,
        mass_props_before=cfg['CoM_before_burn'],
        mass_props_after=cfg['CoM_after_burn'],
    )
    assert surface_heating(aero, 1.0, 0.0, 288.15, 101325.0) is None


def test_surface_heating_altitude_effect():
    # Lower density at altitude -> lower heat flux
    cfg = _campanil()
    aero = _panel_aero(cfg)
    aero.update(mach=2.0, angle_attack=2.0, height=0.0, density=1.225)
    q_sl = surface_heating(aero, 2.0, 0.0, 288.15, 101325.0)['max_heat_flux']
    aero.update(mach=2.0, angle_attack=2.0, height=10000.0, density=0.4135)
    q_hi = surface_heating(aero, 2.0, 10000.0, 223.15, 26436.0)['max_heat_flux']
    assert q_hi < q_sl
