import json
from pathlib import Path

import numpy as np

from src.models.rocket import Rocket


def load_config(name):
    config_path = Path('data/rockets/configs') / f'{name}.json'
    with config_path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def make_rocket(initial_mass=10.0):
    return Rocket(
        np.array([0.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 0.0, 1.0]),
        np.array([0.0, 0.0, 0.0]),
        initial_mass=initial_mass,
    )


class TestMassTelemetrySynchronization:
    def test_mass_related_uses_current_engine_telemetry(self):
        rocket = make_rocket()
        rocket.press_amb = 101325.0

        config = load_config('small_model_rocket')
        rocket.update_time(1.0)
        rocket.update_engine(rocket_name='small_model_rocket', engine_data=config['engine'])

        engine_remaining = rocket.engine_remaining_propellant
        rocket.update_mass_related(
            config['engine']['burn_time'],
            config['CoM_before_burn']['x'],
            config['CoM_before_burn']['y'],
            config['CoM_before_burn']['z'],
            config['I_before_burn']['x'],
            config['I_before_burn']['y'],
            config['I_before_burn']['z'],
            config['CoM_after_burn']['x'],
            config['CoM_after_burn']['y'],
            config['CoM_after_burn']['z'],
            config['I_after_burn']['x'],
            config['I_after_burn']['y'],
            config['I_after_burn']['z'],
            propellant_remaining=engine_remaining,
        )

        assert rocket.propellant_mass_remaining == engine_remaining
        assert rocket.mass == rocket.initial_mass - (rocket.propellant_mass_initial - engine_remaining)

    def test_mass_related_requires_propellant_telemetry(self):
        rocket = make_rocket()
        rocket.press_amb = 101325.0

        config = load_config('small_model_rocket')
        rocket.update_engine(rocket_name='small_model_rocket', engine_data=config['engine'])

        try:
            rocket.update_mass_related(
                config['engine']['burn_time'],
                config['CoM_before_burn']['x'],
                config['CoM_before_burn']['y'],
                config['CoM_before_burn']['z'],
                config['I_before_burn']['x'],
                config['I_before_burn']['y'],
                config['I_before_burn']['z'],
                config['CoM_after_burn']['x'],
                config['CoM_after_burn']['y'],
                config['CoM_after_burn']['z'],
                config['I_after_burn']['x'],
                config['I_after_burn']['y'],
                config['I_after_burn']['z'],
            )
        except TypeError:
            return

        raise AssertionError('update_mass_related should require propellant_remaining')
