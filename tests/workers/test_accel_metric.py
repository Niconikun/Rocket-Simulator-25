"""
Tests for the max_accel_g metric fix: total acceleration must include gravity
(workers.simulation_worker._total_accel_magnitude).
"""

import unittest

import numpy as np
import pytest

from workers.simulation_worker import _total_accel_magnitude, SimulationWorker
from src.models.state import MockStateProvider

G = 9.80665
IDENTITY_Q = np.array([0.0, 0.0, 0.0, 1.0])


@pytest.mark.monte_carlo
class TestTotalAccelMagnitude(unittest.TestCase):
    def test_free_fall_is_exactly_1g(self):
        # no non-gravity forces -> only gravity acts
        a = _total_accel_magnitude(np.zeros(3), mass=10.0, q_enu2b=IDENTITY_Q)
        self.assertAlmostEqual(a / G, 1.0)

    def test_thrust_along_body_x_with_identity_quat(self):
        # force = m*g along +x, gravity -z -> |a| = g*sqrt(2)
        a = _total_accel_magnitude(np.array([10.0 * G, 0.0, 0.0]), mass=10.0, q_enu2b=IDENTITY_Q)
        self.assertAlmostEqual(a / G, np.sqrt(2.0))

    def test_rotated_quaternion_changes_result(self):
        # 90 deg pitch about y: nose horizontal, gravity lies along body -x,
        # so thrust (m*g along body +x) exactly cancels gravity -> 0 g
        q = np.array([0.0, np.sin(np.pi / 4), 0.0, np.cos(np.pi / 4)])
        a = _total_accel_magnitude(np.array([10.0 * G, 0.0, 0.0]), mass=10.0, q_enu2b=q)
        self.assertAlmostEqual(a / G, 0.0, places=6)

    def test_free_fall_is_1g_for_any_attitude(self):
        q = np.array([0.0, np.sin(np.pi / 4), 0.0, np.cos(np.pi / 4)])
        a = _total_accel_magnitude(np.zeros(3), mass=10.0, q_enu2b=q)
        self.assertAlmostEqual(a / G, 1.0)


@pytest.mark.monte_carlo
class TestMaxAccelGMetric(unittest.TestCase):
    def test_run_reports_accel_at_least_1g(self):
        state = MockStateProvider({
            'selected_rocket': 'agni-1',
            'sim_runtime': 0.05,
            'sim_time_step': 0.01,
            'wind_enabled': False,
            'parachute_enabled': False,
        })
        worker = SimulationWorker(state, use_cache=False)
        result = worker.run_with_params({})
        self.assertEqual(result['status'], 'success')
        # with gravity included, any physical state is at least 1 g
        self.assertGreaterEqual(result['metrics']['max_accel_g'], 1.0)


if __name__ == '__main__':
    unittest.main()
