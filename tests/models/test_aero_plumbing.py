"""Phase 2 tests: aerodynamics config section, schema and state plumbing."""

import json
from pathlib import Path

import pytest

from src.models.rocket.factory import (
    validate_aerodynamics_section,
    aero_selection_from_state,
    create_aerodynamics,
    VALID_AERO_METHODS,
)
from src.models.panel_method import PanelMethodAerodynamics
from src.models.aerodynamics import Aerodynamics
from src.config.constants import Constants


# ---------------------------------------------------------------------------
# Section validation
# ---------------------------------------------------------------------------

def test_validate_section_empty():
    assert validate_aerodynamics_section(None) == {'errors': [], 'warnings': []}
    assert validate_aerodynamics_section({}) == {'errors': [], 'warnings': []}


def test_validate_section_valid_panel():
    cfg = {'method': 'panel', 'n_axial': 48, 'n_theta': 16,
           'include_fins': True, 'viscous_crossflow': True, 'thermo_enabled': False}
    rep = validate_aerodynamics_section(cfg)
    assert rep['errors'] == []


def test_validate_section_invalid_method():
    rep = validate_aerodynamics_section({'method': 'cfd'})
    assert any('method' in e for e in rep['errors'])


def test_validate_section_invalid_resolution():
    rep = validate_aerodynamics_section({'method': 'panel', 'n_axial': 4})
    assert any('n_axial' in e for e in rep['errors'])
    rep = validate_aerodynamics_section({'n_theta': 'lots'})
    assert any('n_theta' in e for e in rep['errors'])


def test_validate_section_thermo_warning():
    rep = validate_aerodynamics_section({'method': 'panel', 'thermo_enabled': True})
    assert rep['errors'] == []
    assert any('thermo' in w for w in rep['warnings'])


# ---------------------------------------------------------------------------
# State -> (method, options) plumbing
# ---------------------------------------------------------------------------

def test_aero_selection_default():
    method, options = aero_selection_from_state({})
    assert method is None and options == {}
    method, options = aero_selection_from_state({Constants.StateKeys.AERO_METHOD: 'default'})
    assert method is None and options == {}


def test_aero_selection_panel_with_options():
    state = {
        Constants.StateKeys.AERO_METHOD: 'panel',
        Constants.StateKeys.AERO_PANEL_N_AXIAL: 32,
        Constants.StateKeys.AERO_PANEL_N_THETA: 12,
        Constants.StateKeys.AERO_INCLUDE_FINS: False,
        Constants.StateKeys.AERO_VISCOUS_CROSSFLOW: True,
    }
    method, options = aero_selection_from_state(state)
    assert method == 'panel'
    assert options == {'n_axial': 32, 'n_theta': 12,
                       'include_fins': False, 'viscous_crossflow': True}


def test_aero_selection_invalid_method_falls_back():
    method, options = aero_selection_from_state({Constants.StateKeys.AERO_METHOD: 'magic'})
    assert method is None  # rocket file default


def test_state_override_beats_config_file():
    p = Path('data/rockets/configs/campanil_1a.json')
    cfg = json.loads(p.read_text())
    assert cfg['aerodynamics']['method'] == 'barrowman'  # file default unchanged
    # state says panel -> panel wins even though file says barrowman
    method, options = aero_selection_from_state({Constants.StateKeys.AERO_METHOD: 'panel',
                                                 Constants.StateKeys.AERO_PANEL_N_AXIAL: 24,
                                                 Constants.StateKeys.AERO_PANEL_N_THETA: 8})
    aero = create_aerodynamics(
        mach=0.0, angle_attack=0.0, height=0.0, atmosphere=None,
        rocket_config=cfg,
        mass_props_before=cfg['CoM_before_burn'],
        mass_props_after=cfg['CoM_after_burn'],
        method=method, panel_options=options,
    )
    assert isinstance(aero, PanelMethodAerodynamics)
    assert aero.mesh.n_axial == 24
    # no state override -> file default (barrowman)
    method, options = aero_selection_from_state({})
    aero2 = create_aerodynamics(
        mach=0.0, angle_attack=0.0, height=0.0, atmosphere=None,
        rocket_config=cfg,
        mass_props_before=cfg['CoM_before_burn'],
        mass_props_after=cfg['CoM_after_burn'],
        method=method, panel_options=options,
    )
    assert type(aero2) is Aerodynamics


# ---------------------------------------------------------------------------
# JSON schema
# ---------------------------------------------------------------------------

def _aero_subschema():
    jsonschema = pytest.importorskip('jsonschema')
    schema = json.loads(Path('data/schemas/rocket.schema.json').read_text())
    return jsonschema, schema['properties']['aerodynamics']


def test_rocket_schema_accepts_aerodynamics_section():
    # Validate the aerodynamics subschema against the shipped configs that
    # carry the section (full-config validation has pre-existing mismatches
    # in the geometry keys, unrelated to this change)
    jsonschema, sub = _aero_subschema()
    cfg = json.loads(Path('data/rockets/configs/campanil_1a.json').read_text())
    jsonschema.validate(cfg['aerodynamics'], sub)  # must not raise
    jsonschema.validate({'method': 'panel', 'n_axial': 64, 'n_theta': 24}, sub)


def test_rocket_schema_rejects_bad_method():
    jsonschema, sub = _aero_subschema()
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({'method': 'cfd'}, sub)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({'method': 'panel', 'n_axial': 4}, sub)


def test_valid_methods_constant():
    assert 'barrowman' in VALID_AERO_METHODS and 'panel' in VALID_AERO_METHODS
