import json
from pathlib import Path

import numpy as np

from models.app_state import ApplicationState
from src.models.rocket import Rocket
from src.utils.simulation_validator import SimulationValidator
from workers.simulation_worker import SimulationWorker


def make_rocket(initial_mass=10.0):
    return Rocket(
        np.array([0.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 0.0, 1.0]),
        np.array([0.0, 0.0, 0.0]),
        initial_mass=initial_mass,
    )


def load_config(name):
    config_path = Path('data/rockets/configs') / f'{name}.json'
    with config_path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


class TestPersistentEngineLifecycle:
    def test_update_engine_reuses_same_instance(self):
        rocket = make_rocket()
        rocket.press_amb = 101325.0

        config = load_config('small_model_rocket')
        rocket.update_engine(rocket_name='small_model_rocket', engine_data=config['engine'])
        first_engine_id = id(rocket._engine_model)

        rocket.update_time(0.05)
        rocket.update_engine()
        second_engine_id = id(rocket._engine_model)

        assert first_engine_id == second_engine_id
        assert rocket.thrust >= 0.0
        assert rocket.mass_flux >= 0.0

    def test_cached_engine_config_supports_argless_updates(self):
        rocket = make_rocket()
        rocket.press_amb = 101325.0

        config = load_config('small_model_rocket')
        rocket.update_engine(rocket_name='small_model_rocket', engine_data=config['engine'])

        rocket.update_time(0.10)
        rocket.update_engine()

        assert rocket._engine_config is not None
        assert rocket._engine_rocket_name == 'small_model_rocket'


class TestPreSimulationPropulsionValidation:
    def test_missing_experimental_curve_fails_validation(self):
        worker = SimulationWorker(ApplicationState())
        config = load_config('high_altitude_rocket')

        report = worker._validate_rocket_config(config, 'high_altitude_rocket')

        assert not report['valid']
        assert any('Thrust curve file not found' in err for err in report['errors'])

    def test_analytical_config_passes_propulsion_validation(self):
        worker = SimulationWorker(ApplicationState())
        config = load_config('small_model_rocket')

        report = worker._validate_rocket_config(config, 'small_model_rocket')

        assert report['valid']
        assert 'propulsion' in report['diagnostics']
        assert report['diagnostics']['propulsion']['thrust_source'] == 'analytical'


class TestPostSimulationPropulsionValidation:
    def test_propulsion_consistency_passes_for_coherent_history(self):
        validator = SimulationValidator()
        thrust = [10.0, 10.0, 0.0]
        isp = [200.0, 200.0, 0.0]
        mass_flux = [10.0 / (200.0 * 9.80665), 10.0 / (200.0 * 9.80665), 0.0]

        results = {
            'trajectory': [
                {'time': 0.0, 'altitude': 0.0, 'velocity': 0.0},
                {'time': 1.0, 'altitude': 20.0, 'velocity': 10.0},
                {'time': 2.0, 'altitude': 10.0, 'velocity': 2.0},
            ],
            'history': {
                'hist_time': [0.0, 1.0, 2.0],
                'hist_thrust': thrust,
                'hist_mass_flux': mass_flux,
                'hist_engine_isp': isp,
                'hist_propellant_mass': [1.0, 0.5, 0.0],
            },
            'metrics': {
                'max_altitude': 20.0,
                'propulsion': {
                    'thrust_source': 'analytical',
                    'total_impulse_delivered': 15.0,
                    'burnout_reached': True,
                },
            },
        }

        report = validator.validate(results)

        assert report['checks']['propulsion_consistency']
        assert report['valid']

    def test_propulsion_consistency_fails_for_inconsistent_mass_flux(self):
        validator = SimulationValidator()
        results = {
            'trajectory': [
                {'time': 0.0, 'altitude': 0.0, 'velocity': 0.0},
                {'time': 1.0, 'altitude': 20.0, 'velocity': 10.0},
                {'time': 2.0, 'altitude': 10.0, 'velocity': 2.0},
            ],
            'history': {
                'hist_time': [0.0, 1.0, 2.0],
                'hist_thrust': [10.0, 10.0, 0.0],
                'hist_mass_flux': [0.50, 0.25, 0.0],
                'hist_engine_isp': [200.0, 200.0, 0.0],
                'hist_propellant_mass': [1.0, 1.1, 0.8],
            },
            'metrics': {
                'max_altitude': 20.0,
                'propulsion': {
                    'thrust_source': 'analytical',
                    'total_impulse_delivered': 15.0,
                    'burnout_reached': False,
                },
            },
        }

        report = validator.validate(results)

        assert not report['checks']['propulsion_consistency']
        assert not report['valid']
        assert any('Propulsion inconsistency' in err or 'Remaining propellant increased' in err
                   for err in report['errors'])