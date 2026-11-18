"""Tests for the Qt-free aero analysis helpers used by the GUI (Phase 3)."""

import json
import math
from pathlib import Path

import numpy as np
import pytest

from src.utils.aero_analysis import analyze_aero_curves, cp_profile, rocket_data_from_config


def _campanil():
    return json.loads(Path('data/rockets/configs/campanil_1a.json').read_text())


def test_rocket_data_from_config_keys():
    cfg = _campanil()
    rd = rocket_data_from_config(cfg)
    for key in ('reference_area', 'geometry', 'fuselage', 'nosecone', 'rear_section', 'fins'):
        assert key in rd


def test_analyze_aero_curves_both_methods():
    cfg = _campanil()
    curves = analyze_aero_curves(cfg, machs=[0.2, 0.5, 0.8, 1.5, 2.5], alpha_deg=5.0,
                                 methods=('barrowman', 'panel'),
                                 panel_options={'n_axial': 32, 'n_theta': 12})
    assert set(curves.keys()) == {'barrowman', 'panel'}
    for method, data in curves.items():
        for key in ('mach', 'cd', 'cl', 'c_nalpha', 'x_cp', 'stability'):
            assert key in data and len(data[key]) == 5
        assert np.all(data['cd'] > 0)          # drag positive across regimes
        assert np.all(data['c_nalpha'] > 0)    # positive lift slope
        assert np.all(data['x_cp'] > 0)        # CP aft of nose tip


def test_analyze_curves_panel_close_to_barrowman():
    # Same order of magnitude at subsonic Mach (sanity, not equality)
    cfg = _campanil()
    curves = analyze_aero_curves(cfg, machs=[0.3], alpha_deg=5.0,
                                 panel_options={'n_axial': 40, 'n_theta': 12})
    b, p = curves['barrowman'], curves['panel']
    assert 0.2 < p['c_nalpha'][0] / b['c_nalpha'][0] < 5.0
    assert 0.2 < p['cd'][0] / b['cd'][0] < 5.0
    # Stability margin same sign
    assert np.sign(p['stability'][0]) == np.sign(b['stability'][0])


def test_cp_profile_shapes():
    cfg = _campanil()
    prof = cp_profile(cfg, mach=0.3, alpha_deg=5.0,
                      panel_options={'n_axial': 32, 'n_theta': 12})
    assert prof is not None
    x, cp_mean, cp_suction = prof
    assert x.shape == cp_mean.shape == cp_suction.shape
    assert np.all(np.diff(x) > 0)  # x increases from nose tip
    # Suction side is below the azimuthal mean
    assert np.all(cp_suction <= cp_mean + 1e-9)
    # Stagnation region near the nose: elevated Cp at the first strips at low Mach
    assert cp_mean.max() > 0.3


def test_cp_profile_supersonic_positive_on_nose():
    cfg = _campanil()
    prof = cp_profile(cfg, mach=2.0, alpha_deg=0.0,
                      panel_options={'n_axial': 32, 'n_theta': 12})
    assert prof is not None
    x, cp_mean, _ = prof
    # Ackeret: compression (Cp > 0) on the nose cone, near zero on the cylinder
    assert cp_mean[0] > 0 or cp_mean[: len(x) // 4].max() > 0
