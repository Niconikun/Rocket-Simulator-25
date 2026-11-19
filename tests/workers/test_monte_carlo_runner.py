"""
Integration tests for workers.monte_carlo_runner (Phase 2 behaviour):

- batch output goes to Paths.MONTE_CARLO_DIR (CWD-independent)
- runs that do not land get NaN impact + termination_reason recorded and are
  excluded from impact scatter statistics
- gust wind models get a distinct random_seed per run
- serial and parallel execution are reproducible with the same seed
"""

import json
import os
import unittest

import numpy as np
import pytest

from src.config import Paths
from src.models.state import MockStateProvider
from workers.monte_carlo_runner import MonteCarloRunner


def _state(**overrides):
    base = {
        'selected_rocket': 'agni-1',
        'sim_runtime': 0.05,      # short: the rocket never lands in these tests
        'sim_time_step': 0.01,
        'launch_elevation_angle': 85.0,
        'launch_azimuth': 10.0,
        'launch_roll': 0.0,
        'average_temperature': 20.0,
        'wind_enabled': False,
        'parachute_enabled': False,
    }
    base.update(overrides)
    return MockStateProvider(base)


def _run(state, n_runs=3, seed=42, n_workers=1):
    runner = MonteCarloRunner(state, n_runs=n_runs, seed=seed, n_workers=n_workers)
    holder = {}
    errors = []
    runner.finished.connect(lambda s: holder.setdefault('summary', s))
    runner.error.connect(lambda e: errors.append(e))
    runner.run()
    assert not errors, f"runner emitted errors: {errors}"
    return holder['summary']


def _records(summary):
    with open(summary['output_file']) as f:
        return [json.loads(line) for line in f if line.strip()]


def _cleanup(summary):
    for path in (summary['output_file'],
                 summary['output_file'].replace('.jsonl', '_summary.json')):
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.monte_carlo
class TestRunnerOutputs(unittest.TestCase):
    def test_output_written_under_monte_carlo_dir(self):
        s = _run(_state())
        try:
            self.assertEqual(os.path.dirname(s['output_file']),
                             str(Paths.MONTE_CARLO_DIR))
            self.assertTrue(os.path.exists(s['output_file']))
            self.assertEqual(s['n_successful'], 3)
            self.assertEqual(s['n_failed'], 0)
        finally:
            _cleanup(s)

    def test_non_landing_runs_get_nan_impact_and_are_excluded_from_scatter(self):
        s = _run(_state())
        try:
            recs = _records(s)
            self.assertEqual(len(recs), 3)
            for r in recs:
                self.assertTrue(np.isnan(r['metrics']['impact_x']))
                self.assertTrue(np.isnan(r['metrics']['impact_y']))
                self.assertIs(r['metrics']['landed'], False)
                self.assertIn('termination_reason', r['metrics'])
                self.assertNotEqual(r['metrics']['termination_reason'], '')
            # scalar stats still computed, but no impact scatter without landings
            self.assertIn('max_altitude', s['statistics'])
            self.assertNotIn('impact_scatter', s['statistics'])
        finally:
            _cleanup(s)

    def test_gust_runs_get_distinct_random_seeds(self):
        state = _state(wind_enabled=True, wind_model_type='gust',
                       wind_speed_ref=5.0, wind_direction=180.0,
                       wind_gust_intensity=0.1, wind_gust_length_scale=300.0)
        s = _run(state, n_runs=4)
        try:
            seeds = [r['overrides'].get('random_seed') for r in _records(s)]
            self.assertTrue(all(isinstance(v, int) for v in seeds))
            self.assertEqual(len(set(seeds)), len(seeds))
        finally:
            _cleanup(s)

    def test_no_gust_seed_for_non_gust_models(self):
        state = _state(wind_enabled=True, wind_model_type='constant',
                       wind_speed_ref=5.0, wind_direction=180.0)
        s = _run(state, n_runs=3)
        try:
            seeds = [r['overrides'].get('random_seed') for r in _records(s)]
            self.assertTrue(all(v is None for v in seeds))
        finally:
            _cleanup(s)


@pytest.mark.monte_carlo
@pytest.mark.slow
class TestSerialParallelEquivalence(unittest.TestCase):
    def test_same_seed_same_results(self):
        state = _state(wind_enabled=True, wind_model_type='constant',
                       wind_speed_ref=5.0, wind_direction=180.0)
        s1 = _run(state, n_runs=3, seed=7, n_workers=1)
        s2 = _run(state, n_runs=3, seed=7, n_workers=2)
        try:
            r1 = sorted(_records(s1), key=lambda r: r['run'])
            r2 = sorted(_records(s2), key=lambda r: r['run'])
            self.assertEqual([r['overrides'] for r in r1],
                             [r['overrides'] for r in r2])
            for a, b in zip(r1, r2):
                self.assertEqual(a['metrics'], b['metrics'])
        finally:
            _cleanup(s1)
            _cleanup(s2)


if __name__ == '__main__':
    unittest.main()
