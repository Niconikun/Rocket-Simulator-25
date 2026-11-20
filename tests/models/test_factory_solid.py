"""Tests for solid-motor wiring in src/models/rocket/factory.py."""

import numpy as np
import pytest

from src.models.interfaces import IEngine
from src.models.rocket.factory import (
    EngineConfig,
    RocketBuilder,
    RocketConfigurationError,
    create_engine,
    create_rocket_from_config,
)
from src.models.solid_motor import SolidMotorEngine

SOLID_ENGINE_DATA = {
    'engine_model': 'solid',
    'motor': {
        'grain': {'type': 'bates', 'outer_diameter': 0.075, 'core_diameter': 0.030,
                  'segment_length': 0.10, 'segments': 3},
        'propellant': {'density': 1800.0, 'burn_rate_a': 5.0, 'burn_rate_n': 0.3},
        'nozzle': {'throat_diameter': 0.018, 'exit_diameter': 0.036},
    },
}


def test_create_engine_solid_returns_solid_motor():
    engine = create_engine(dict(SOLID_ENGINE_DATA), rocket_mass=12.0)
    assert isinstance(engine, SolidMotorEngine)
    assert isinstance(engine, IEngine)
    assert engine.thrust_source == 'solid-grain'


def test_create_engine_solid_backfills_scalar_keys():
    data = dict(SOLID_ENGINE_DATA)
    create_engine(data, rocket_mass=12.0)
    for key in ('burn_time', 'propellant_mass', 'specific_impulse', 'mean_thrust',
                'max_thrust', 'mean_chamber_pressure', 'max_chamber_pressure',
                'nozzle_exit_diameter', 'mass_flux', 'gas_speed', 'exit_pressure',
                'thrust_to_weight_ratio'):
        assert key in data, f"missing backfilled key {key}"
        assert data[key] > 0


def test_create_engine_solid_missing_motor_raises():
    with pytest.raises(RocketConfigurationError):
        create_engine({'engine_model': 'solid'})


def test_create_engine_solid_invalid_motor_raises():
    bad = dict(SOLID_ENGINE_DATA)
    bad['motor'] = {'grain': {'type': 'bates', 'outer_diameter': 0.01, 'core_diameter': 0.03,
                              'segment_length': 0.1, 'segments': 1},
                    'propellant': {'density': 1800.0, 'burn_rate_a': 5.0, 'burn_rate_n': 0.3},
                    'nozzle': {'throat_diameter': 0.018, 'exit_diameter': 0.036}}
    with pytest.raises(RocketConfigurationError):
        create_engine(bad)


def test_create_engine_legacy_enhanced_unchanged():
    from src.models.engine import EnhancedEngine
    data = {
        'burn_time': 5.0, 'nozzle_exit_diameter': 0.1, 'propellant_mass': 1.5,
        'specific_impulse': 250.0, 'mean_thrust': 1000.0, 'max_thrust': 1200.0,
        'mean_chamber_pressure': 1e6, 'max_chamber_pressure': 1.2e6,
        'thrust_to_weight_ratio': 50.0,
    }
    engine = create_engine(data)
    assert type(engine) is EnhancedEngine


def test_engine_config_dataclass_solid_fields():
    cfg = EngineConfig(burn_time=2.0, engine_model='solid',
                       motor_config=SOLID_ENGINE_DATA['motor'], rocket_mass=12.0)
    assert cfg.engine_model == 'solid'
    assert cfg.motor_config is not None


def test_rocket_builder_with_solid_engine_config():
    builder = RocketBuilder()
    rocket = (builder
              .with_position(np.array([0.0, 0.0, 0.0]))
              .with_velocity(np.array([0.0, 0.0, 10.0]))
              .with_attitude(np.array([0.0, 0.0, 0.0, 1.0]))
              .with_angular_velocity(np.array([0.0, 0.0, 0.0]))
              .with_initial_mass(12.0)
              .with_propellant_mass(2.0)
              .with_engine_config(EngineConfig(
                  burn_time=2.0, engine_model='solid',
                  motor_config=SOLID_ENGINE_DATA['motor'], rocket_mass=12.0))
              .with_mass_properties_config(_mass_cfg())
              .build())
    assert isinstance(rocket.engine, SolidMotorEngine)
    rocket.engine.update(time=1.0, ambient_pressure=101325.0)
    assert rocket.engine.get_thrust() > 0.0


def _mass_cfg():
    from src.models.rocket.factory import MassPropertiesConfig
    return MassPropertiesConfig(
        mass_before=12.0, mass_after=10.0,
        cm_before={'x': 0.5, 'y': 0.0, 'z': 0.0},
        cm_after={'x': 0.6, 'y': 0.0, 'z': 0.0},
        inertia_before={'x': 0.1, 'y': 0.5, 'z': 0.5},
        inertia_after={'x': 0.1, 'y': 0.4, 'z': 0.4},
    )


def test_create_rocket_from_config_solid_file():
    rocket, rocket_config, engine, aero, atm = create_rocket_from_config(
        r_enu_0=np.array([0.0, 0.0, 0.0]),
        v_enu_0=np.array([0.0, 0.0, 0.0]),
        q_enu2b_0=np.array([0.0, 0.0, 0.0, 1.0]),
        w_enu_0=np.array([0.0, 0.0, 0.0]),
        initial_mass=7.8,
        rocket_name='campanil_1a_solid',
    )
    assert isinstance(engine, SolidMotorEngine)
    assert engine.thrust_source == 'solid-grain'
    engine.update(time=1.0, ambient_pressure=101325.0)
    assert engine.get_thrust() > 0.0
