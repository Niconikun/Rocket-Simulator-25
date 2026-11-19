"""
Tests for Monte Carlo sampling of rocket/engine parameters:

- SimulationWorker._apply_state_config_overrides overlays positive state
  values (GUI edits, MC samples) onto the rocket config and engine config
- run_with_params with an engine override actually changes the flight
- new metrics max_q / touchdown_velocity are present in results
"""

import unittest

import pytest

from src.models.state import MockStateProvider, StateProxy
from workers.simulation_worker import SimulationWorker


def _state(**overrides):
    base = {
        'selected_rocket': 'agni-1',
        'sim_runtime': 0.2,
        'sim_time_step': 0.005,
        'wind_enabled': False,
        'parachute_enabled': False,
    }
    base.update(overrides)
    return MockStateProvider(base)


@pytest.mark.monte_carlo
class TestApplyStateConfigOverrides(unittest.TestCase):
    def test_positive_state_values_override_config(self):
        base = _state()
        worker = SimulationWorker(base, use_cache=False)
        worker.state = StateProxy(base, {
            'initial_mass': 123.0, 'mean_thrust': 999.0, 'burn_time': 0.0,
        })
        cfg = worker._apply_state_config_overrides({
            'initial_mass': 100.0,
            'propellant_mass': 50.0,
            'reference_area': 0.5,
            'engine': {'mean_thrust': 500.0, 'burn_time': 2.0},
        })
        self.assertEqual(cfg['initial_mass'], 123.0)          # override wins
        self.assertEqual(cfg['engine']['mean_thrust'], 999.0)  # override wins
        self.assertEqual(cfg['engine']['burn_time'], 2.0)      # 0.0 in state = unset
        self.assertEqual(cfg['propellant_mass'], 50.0)         # untouched

    def test_zero_and_none_state_values_ignored(self):
        base = _state()  # no mass keys -> MockStateProvider returns None
        worker = SimulationWorker(base, use_cache=False)
        cfg = worker._apply_state_config_overrides({
            'initial_mass': 100.0,
            'engine': {'mean_thrust': 500.0},
        })
        self.assertEqual(cfg['initial_mass'], 100.0)
        self.assertEqual(cfg['engine']['mean_thrust'], 500.0)

    def test_bool_values_ignored(self):
        base = _state()
        worker = SimulationWorker(base, use_cache=False)
        worker.state = StateProxy(base, {'initial_mass': True})
        cfg = worker._apply_state_config_overrides({'initial_mass': 100.0})
        self.assertEqual(cfg['initial_mass'], 100.0)


@pytest.mark.monte_carlo
class TestEngineOverrideAffectsFlight(unittest.TestCase):
    def test_thrust_override_changes_apogee(self):
        worker = SimulationWorker(_state(), use_cache=False)
        base_result = worker.run_with_params({})
        worker2 = SimulationWorker(_state(), use_cache=False)
        hot = worker2.run_with_params({'mean_thrust': 2.0 * 454930.5})
        self.assertEqual(base_result['status'], 'success')
        self.assertEqual(hot['status'], 'success')
        self.assertGreater(hot['metrics']['max_altitude'],
                           base_result['metrics']['max_altitude'])

    def test_new_metrics_present(self):
        worker = SimulationWorker(_state(), use_cache=False)
        result = worker.run_with_params({})
        metrics = result['metrics']
        self.assertIn('max_q', metrics)
        self.assertIn('touchdown_velocity', metrics)
        self.assertGreaterEqual(metrics['max_q'], 0.0)


if __name__ == '__main__':
    unittest.main()
