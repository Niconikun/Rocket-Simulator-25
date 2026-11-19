"""
Unit tests for src.utils.monte_carlo_stats (shared impact/CEP helpers).

Covers:
- ground-crossing interpolation of the impact point
- NaN impact for runs that did not land
- history / r_enu / trajectory fallbacks
- CEP: approximation for N < 20, empirical median for N >= 20
"""

import unittest

import numpy as np
import pytest

from src.utils.monte_carlo_stats import extract_impact_position, compute_cep

LANDING = "LANDING: Altitude <= 0m"
NORMAL = "NORMAL: Completed all steps"


def _result(east, north, alt, reason=LANDING):
    return {
        "metrics": {"runtime_diagnostics": {"termination_reason": reason}},
        "history": {
            "hist_east": list(east),
            "hist_north": list(north),
            "hist_alt": list(alt),
        },
    }


@pytest.mark.monte_carlo
class TestExtractImpactPosition(unittest.TestCase):
    def test_interpolates_ground_crossing(self):
        # alt goes 10 -> 5 -> -5, crossing zero halfway between samples 1 and 2
        result = _result(east=[0.0, 100.0, 200.0], north=[0.0, 0.0, 0.0],
                         alt=[10.0, 5.0, -5.0])
        x, y = extract_impact_position(result)
        self.assertAlmostEqual(x, 150.0)
        self.assertAlmostEqual(y, 0.0)

    def test_non_landing_run_returns_nan(self):
        result = _result(east=[0.0, 100.0], north=[0.0, 0.0],
                         alt=[10.0, 5.0], reason=NORMAL)
        x, y = extract_impact_position(result)
        self.assertTrue(np.isnan(x))
        self.assertTrue(np.isnan(y))

    def test_landing_without_alt_uses_last_history_point(self):
        result = {
            "metrics": {"runtime_diagnostics": {"termination_reason": LANDING}},
            "history": {"hist_east": [1.0, 42.0], "hist_north": [2.0, 24.0]},
        }
        x, y = extract_impact_position(result)
        self.assertEqual((x, y), (42.0, 24.0))

    def test_hist_r_enu_fallback_interpolates(self):
        result = {
            "metrics": {"runtime_diagnostics": {"termination_reason": LANDING}},
            "history": {"hist_r_enu": [[0.0, 0.0, 10.0], [50.0, 20.0, -2.0]]},
        }
        x, y = extract_impact_position(result)
        frac = 10.0 / 12.0
        self.assertAlmostEqual(x, 50.0 * frac)
        self.assertAlmostEqual(y, 20.0 * frac)

    def test_trajectory_fallback_is_range_on_x_axis(self):
        result = {
            "metrics": {"runtime_diagnostics": {"termination_reason": LANDING}},
            "history": {},
            "trajectory": [{"range": 123.0}],
        }
        x, y = extract_impact_position(result)
        self.assertEqual((x, y), (123.0, 0.0))

    def test_missing_reason_infers_landing_from_altitude(self):
        result = {"metrics": {}, "history": {"hist_east": [5.0], "hist_north": [6.0],
                                              "hist_alt": [-0.5]}}
        x, y = extract_impact_position(result)
        self.assertEqual((x, y), (5.0, 6.0))

    def test_empty_result_returns_nan(self):
        x, y = extract_impact_position({})
        self.assertTrue(np.isnan(x) and np.isnan(y))


@pytest.mark.monte_carlo
class TestComputeCep(unittest.TestCase):
    def test_fewer_than_two_points_returns_zero(self):
        self.assertEqual(compute_cep(np.array([1.0]), np.array([2.0])), 0.0)
        self.assertEqual(compute_cep(np.array([]), np.array([])), 0.0)

    def test_small_batch_uses_analytical_approximation(self):
        rng = np.random.default_rng(0)
        x = rng.normal(0.0, 3.0, size=10)
        y = rng.normal(0.0, 1.0, size=10)
        expected = 0.59 * (np.std(x) + np.std(y))
        self.assertAlmostEqual(compute_cep(x, y), expected)

    def test_large_batch_uses_empirical_median_radial(self):
        rng = np.random.default_rng(1)
        x = rng.normal(10.0, 4.0, size=200)
        y = rng.normal(-5.0, 2.0, size=200)
        radial = np.sqrt((x - x.mean()) ** 2 + (y - y.mean()) ** 2)
        expected = float(np.percentile(radial, 50))
        self.assertAlmostEqual(compute_cep(x, y), expected)

    def test_perfect_circle_has_cep_equal_to_radius(self):
        theta = np.linspace(0, 2 * np.pi, 100, endpoint=False)
        x, y = 50.0 * np.cos(theta), 50.0 * np.sin(theta)
        self.assertAlmostEqual(compute_cep(x, y), 50.0, places=6)


if __name__ == '__main__':
    unittest.main()
