"""
Regression tests for the worker -> dashboard data path (pyqt-gui review plan
point 6):

- every trajectory point carries 'acceleration': the dashboard CSV export
  writes point.get('acceleration', 0), which used to be missing and therefore
  exported as 0.00
- history contains 'hist_cm2cp_b' (x_cp - x_cm per step), consistent with
  hist_cp_b/hist_cm_b: the dashboard stability chart reads it as fallback
  (dashboard_widget chart 13) and previously found nothing
"""

import unittest

import numpy as np
import pytest

from src.models.state import MockStateProvider
from workers.simulation_worker import SimulationWorker

G = 9.80665


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
class TestTrajectoryAcceleration(unittest.TestCase):
    def test_trajectory_points_carry_acceleration(self):
        worker = SimulationWorker(_state(), use_cache=False)
        result = worker.run_with_params({})
        self.assertEqual(result['status'], 'success')

        trajectory = result['trajectory']
        self.assertGreater(len(trajectory), 0)
        for point in trajectory:
            self.assertIn('acceleration', point)
            accel = point['acceleration']
            self.assertIsInstance(accel, float)
            self.assertTrue(np.isfinite(accel))
            self.assertGreaterEqual(accel, 0.0)
        # acceleration includes gravity, so some point must be at least 1 g
        max_accel = max(p['acceleration'] for p in trajectory)
        self.assertGreaterEqual(max_accel, G - 1e-9)


@pytest.mark.monte_carlo
class TestHistoryCm2cp(unittest.TestCase):
    def test_hist_cm2cp_b_present_and_consistent_with_cm_cp(self):
        worker = SimulationWorker(_state(), use_cache=False)
        result = worker.run_with_params({})
        self.assertEqual(result['status'], 'success')

        history = result['history']
        self.assertIn('hist_cm2cp_b', history)
        times = history['hist_time']
        cm2cp = np.asarray(history['hist_cm2cp_b'], dtype=float)
        self.assertEqual(cm2cp.ndim, 1)
        self.assertEqual(len(cm2cp), len(times))

        cm_b = np.asarray(history['hist_cm_b'], dtype=float)
        cp_b = np.asarray(history['hist_cp_b'], dtype=float)
        self.assertEqual(cm_b.shape, (len(times), 3))
        self.assertEqual(cp_b.shape, (len(times), 3))
        # must match the dashboard's primary stability-margin computation
        # (chart 13: margin = cp_b[:, 0] - cm_b[:, 0] when both are 2-D)
        np.testing.assert_allclose(cm2cp, cp_b[:, 0] - cm_b[:, 0],
                                   rtol=1e-9, atol=1e-12)


if __name__ == '__main__':
    unittest.main()
