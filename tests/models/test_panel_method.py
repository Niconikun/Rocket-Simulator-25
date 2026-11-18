"""Tests for the panel method aerodynamics (Phase 1).

Benchmarks:
    - Cone in incompressible flow: C_Nalpha -> 2/rad (slender body), x_cp = 2L/3.
    - Long cylinder in crossflow: stagnation Cp ~ 1, side Cp ~ -3 (2D cylinder).
    - Supersonic cone at alpha=0: Ackeret wave drag C_A ~ 2*sin(delta)/sqrt(M^2-1).
Plus factory switching, dynamics integration and panel-vs-Barrowman sanity.
"""

import math

import numpy as np
import pytest

from src.models.interfaces import IAerodynamics
from src.models.aerodynamics import Aerodynamics
from src.models.panel_method import PanelMethodAerodynamics, BodyOfRevolutionMesh
from src.models.rocket.factory import create_aerodynamics, create_rocket_from_config


def cone_rocket_data(L=1.0, D=0.1):
    return {
        'reference_area': math.pi * (D / 2.0) ** 2,
        'geometry': {'total_length': L, 'length_nosecone_fins': L},
        'nosecone': {'shape': 'conical', 'type': 'Conical', 'length': L, 'diameter': D},
        'fuselage': {'length': 0.0, 'diameter': D},
        'rear_section': {'length': 0.0, 'diameter': D},
        'fins': {'span': 0.0, 'chord_root': 0.0, 'chord_tip': 0.0, 'N_fins': 0},
    }


def cylinder_rocket_data(L=1.0, D=0.1):
    data = cone_rocket_data(L, D)
    data['nosecone'] = {'shape': 'conical', 'type': 'Conical', 'length': 1e-6, 'diameter': D}
    data['fuselage'] = {'length': L, 'diameter': D}
    data['geometry'] = {'total_length': L + 1e-6, 'length_nosecone_fins': L}
    return data


def make_panel(rocket_data, **kw):
    opts = dict(n_axial=48, n_theta=16, include_fins=False)
    opts.update(kw)
    return PanelMethodAerodynamics(
        mach=0.0, angle_attack=0.0, height=0.0,
        rocket_data=rocket_data, mass_props={}, **opts
    )


# ---------------------------------------------------------------------------
# Mesh
# ---------------------------------------------------------------------------

def test_mesh_cone_profile():
    mesh = BodyOfRevolutionMesh(cone_rocket_data(L=1.0, D=0.1), n_axial=32, n_theta=8)
    assert mesh.L == pytest.approx(1.0)
    assert mesh.r_c[-1] == pytest.approx(0.05, rel=0.05)  # base radius
    assert mesh.r_c[0] < mesh.r_c[-1]  # cone grows toward the base
    assert np.all(mesh.area > 0)
    # normals of a cone point outward and forward (negative x)
    assert np.all(mesh.nx < 0)
    assert np.all(mesh.nr > 0)


def test_requires_rocket_data():
    with pytest.raises(Exception):
        PanelMethodAerodynamics(rocket_data=None)


# ---------------------------------------------------------------------------
# Interface conformance
# ---------------------------------------------------------------------------

def test_implements_iaerodynamics():
    aero = make_panel(cone_rocket_data())
    assert isinstance(aero, IAerodynamics)
    assert aero.accepts_v_rel_body is True
    aero.update(mach=0.3, angle_attack=5.0, height=100.0, density=1.2)
    cd, cl = aero.get_coefficients()
    assert cd > 0
    cp = aero.get_center_of_pressure()
    assert isinstance(cp, np.ndarray) and cp.shape == (3,)
    forces = aero.get_aerodynamic_forces(1000.0, 0.01)
    for key in ('drag', 'lift', 'cd', 'cl', 'cp_position', 'stability_margin'):
        assert key in forces
    assert aero.get_stability_margin() == pytest.approx(
        (cp[0] - 0.0) / 0.1)  # empty mass props -> x_cg = 0


# ---------------------------------------------------------------------------
# Analytic benchmarks
# ---------------------------------------------------------------------------

def test_cone_normal_force_slender_body():
    # Potential flow past a slender cone: C_Nalpha = 2 per rad
    aero = make_panel(cone_rocket_data(L=1.0, D=0.05), viscous_crossflow=False)
    alpha = 5.0
    aero.update(mach=0.2, angle_attack=alpha, height=0.0, density=1.225)
    cd, cl = aero.get_coefficients()
    c_n = cl / math.cos(math.radians(alpha))
    c_nalpha = c_n / math.radians(alpha)
    assert 1.6 < c_nalpha < 2.4


def test_cone_center_of_pressure():
    # Slender cone: x_cp = 2L/3 from the nose tip
    aero = make_panel(cone_rocket_data(L=1.0, D=0.05), viscous_crossflow=False)
    aero.update(mach=0.2, angle_attack=5.0, height=0.0, density=1.225)
    x_cp = aero.get_center_of_pressure()[0]
    assert x_cp == pytest.approx(2.0 / 3.0, rel=0.15)


def test_cylinder_crossflow_pressure():
    # Long cylinder in pure crossflow approximates the 2D cylinder:
    # Cp = 1 - 4 sin^2(theta) -> stagnation ~ +1, sides ~ -3
    aero = make_panel(cylinder_rocket_data(L=1.0, D=0.1), viscous_crossflow=False)
    aero.update(mach=0.2, angle_attack=90.0, height=0.0, density=1.225)
    x, az, Cp = aero.get_surface_pressure()
    mid = Cp[Cp.shape[0] // 4: 3 * Cp.shape[0] // 4, :]  # away from the ends
    assert mid.max() == pytest.approx(1.0, abs=0.35)
    assert mid.min() == pytest.approx(-3.0, abs=0.9)


def test_supersonic_cone_wave_drag():
    # Ackeret on a cone at alpha=0: C_A(wave) = 2 sin(delta) / sqrt(M^2 - 1)
    L, D = 1.0, 0.1
    aero = make_panel(cone_rocket_data(L, D))
    M = 2.0
    aero.update(mach=M, angle_attack=0.0, height=0.0, density=0.5)
    delta = math.atan((D / 2.0) / L)
    expected = 2.0 * math.sin(delta) / math.sqrt(M * M - 1.0)
    c_ax = aero._last['c_ax']
    assert c_ax == pytest.approx(expected, rel=0.35)


def test_prandtl_glauert_scaling():
    # Subsonic compressibility: C_Nalpha(M) ~ C_Nalpha(0) / sqrt(1 - M^2)
    aero = make_panel(cone_rocket_data(L=1.0, D=0.05), viscous_crossflow=False)
    aero.update(mach=0.0, angle_attack=5.0, height=0.0, density=1.225)
    cl0 = aero.get_coefficients()[1]
    aero.update(mach=0.6, angle_attack=5.0, height=0.0, density=1.0)
    cl6 = aero.get_coefficients()[1]
    ratio = cl6 / cl0
    beta = math.sqrt(1.0 - 0.36)
    assert ratio == pytest.approx(1.0 / beta, rel=0.15)


def test_cache_and_state():
    aero = make_panel(cone_rocket_data())
    aero.update(mach=0.3, angle_attack=5.0, height=10.0, density=1.2)
    cd1, cl1 = aero.get_coefficients()
    aero.update(mach=0.3, angle_attack=5.0, height=10.0, density=1.2)
    cd2, cl2 = aero.get_coefficients()
    assert (cd1, cl1) == (cd2, cl2)
    assert aero.mach == pytest.approx(0.3)
    aero.update(mach=0.3, angle_attack=10.0, height=10.0, density=1.2)
    assert aero.get_coefficients()[1] > cl1  # more alpha -> more lift


def test_v_rel_body_sideslip():
    # Full relative velocity must produce a side force (sideslip preserved)
    aero = make_panel(cone_rocket_data())
    aero.update(mach=0.3, angle_attack=0.0, height=0.0, density=1.2,
                v_rel_body=np.array([1.0, 0.3, 0.1]))
    assert abs(aero._last['c_cy']) > 1e-3
    assert aero._last['c_cz'] > 0
    # Without v_rel_body the crossflow is in the x-z plane only
    aero.update(mach=0.3, angle_attack=5.0, height=0.0, density=1.2)
    assert aero._last['c_cy'] == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# Factory seam
# ---------------------------------------------------------------------------

def _campanil_config():
    import json
    from pathlib import Path
    p = Path('data/rockets/configs/campanil_1a.json')
    with open(p) as f:
        return json.load(f)


def test_factory_default_is_barrowman():
    cfg = _campanil_config()
    aero = create_aerodynamics(
        mach=0.0, angle_attack=0.0, height=0.0, atmosphere=None,
        rocket_config=cfg,
        mass_props_before=cfg['CoM_before_burn'],
        mass_props_after=cfg['CoM_after_burn'],
    )
    assert type(aero) is Aerodynamics


def test_factory_panel_method():
    cfg = _campanil_config()
    aero = create_aerodynamics(
        mach=0.0, angle_attack=0.0, height=0.0, atmosphere=None,
        rocket_config=cfg,
        mass_props_before=cfg['CoM_before_burn'],
        mass_props_after=cfg['CoM_after_burn'],
        method='panel',
        panel_options={'n_axial': 32, 'n_theta': 12},
    )
    assert isinstance(aero, PanelMethodAerodynamics)
    assert aero.mesh.n_axial == 32
    assert aero.mesh.n_theta == 12


def test_factory_method_from_config_section():
    cfg = _campanil_config()
    cfg = dict(cfg)
    cfg['aerodynamics'] = {'method': 'panel', 'n_axial': 24, 'n_theta': 8}
    aero = create_aerodynamics(
        mach=0.0, angle_attack=0.0, height=0.0, atmosphere=None,
        rocket_config=cfg,
        mass_props_before=cfg['CoM_before_burn'],
        mass_props_after=cfg['CoM_after_burn'],
    )
    assert isinstance(aero, PanelMethodAerodynamics)
    assert aero.mesh.n_axial == 24


def test_create_rocket_from_config_panel():
    rocket, cfg, engine, aero, atm = create_rocket_from_config(
        r_enu_0=np.array([0.0, 0.0, 0.0]),
        v_enu_0=np.array([0.0, 0.0, 0.0]),
        q_enu2b_0=np.array([0.0, 0.0, 0.0, 1.0]),
        w_enu_0=np.array([0.0, 0.0, 0.0]),
        initial_mass=7.8,
        rocket_name='campanil_1a',
        aero_method='panel',
        aero_options={'n_axial': 24, 'n_theta': 8},
    )
    assert isinstance(rocket.aerodynamics, PanelMethodAerodynamics)
    assert rocket.dynamics.aerodynamics is rocket.aerodynamics


# ---------------------------------------------------------------------------
# Dynamics integration
# ---------------------------------------------------------------------------

def test_dynamics_panel_force_moment_path():
    rocket, cfg, engine, aero, atm = create_rocket_from_config(
        r_enu_0=np.array([0.0, 0.0, 0.0]),
        v_enu_0=np.array([0.0, 0.0, 50.0]),
        q_enu2b_0=np.array([0.0, 0.0, 0.0, 1.0]),
        w_enu_0=np.array([0.0, 0.0, 0.0]),
        initial_mass=7.8,
        rocket_name='campanil_1a',
        aero_method='panel',
        aero_options={'n_axial': 24, 'n_theta': 8},
    )
    # Give the rocket a small angle of attack (velocity tilted in body z)
    rocket.state.v_enu = np.array([0.0, 0.0, 50.0])
    rocket.state.q_enu2b = np.array([0.0, 0.0, math.sin(math.radians(5.0) / 2.0),
                                      math.cos(math.radians(5.0) / 2.0)])
    rocket.dynamics.update_atmosphere(0.0)
    forces_b, torques_b = rocket.dynamics.calculate_aerodynamics()
    assert forces_b.shape == (3,) and torques_b.shape == (3,)
    assert np.linalg.norm(forces_b) > 0
    # Lift should be along +Z body for positive alpha
    assert forces_b[2] > 0


def test_dynamics_scalar_fallback_still_works():
    # Barrowman path must be unchanged
    rocket, cfg, engine, aero, atm = create_rocket_from_config(
        r_enu_0=np.array([0.0, 0.0, 0.0]),
        v_enu_0=np.array([0.0, 0.0, 50.0]),
        q_enu2b_0=np.array([0.0, 0.0, 0.0, 1.0]),
        w_enu_0=np.array([0.0, 0.0, 0.0]),
        initial_mass=7.8,
        rocket_name='campanil_1a',
    )
    assert type(rocket.aerodynamics) is Aerodynamics
    forces_b, torques_b = rocket.dynamics.calculate_aerodynamics()
    assert forces_b.shape == (3,)


def test_panel_vs_barrowman_same_order():
    cfg = _campanil_config()
    barrow = create_aerodynamics(
        mach=0.3, angle_attack=5.0, height=0.0, atmosphere=None,
        rocket_config=cfg,
        mass_props_before=cfg['CoM_before_burn'],
        mass_props_after=cfg['CoM_after_burn'],
    )
    panel = create_aerodynamics(
        mach=0.3, angle_attack=5.0, height=0.0, atmosphere=None,
        rocket_config=cfg,
        mass_props_before=cfg['CoM_before_burn'],
        mass_props_after=cfg['CoM_after_burn'],
        method='panel',
        panel_options={'n_axial': 40, 'n_theta': 12},
    )
    barrow.update(mach=0.3, angle_attack=5.0, height=0.0, density=1.225)
    panel.update(mach=0.3, angle_attack=5.0, height=0.0, density=1.225)
    _, cl_b = barrow.get_coefficients()
    _, cl_p = panel.get_coefficients()
    assert cl_b > 0 and cl_p > 0
    assert 0.25 < (cl_p / cl_b) < 4.0
    # Stability margins should be the same sign (both stable or both not)
    assert np.sign(panel.get_stability_margin()) == np.sign(barrow.get_stability_margin())
