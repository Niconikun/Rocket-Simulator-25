"""
Unit tests for src.utils.monte_carlo_aggregator

Covers:
- scalar stats over per-run metrics
- NaN impact masking
- CEP delegation to monte_carlo_stats.compute_cep
- dispersion ellipse
- from_summary degraded fallback (no per-run records)
"""

import unittest

import numpy as np
import pytest

from src.utils.monte_carlo_aggregator import MonteCarloAggregator


def _runs(n=50, seed=0):
    rng = np.random.default_rng(seed)
    return [
        {
            "max_altitude": float(rng.normal(1000.0, 30.0)),
            "max_velocity": 200.0, "max_mach": 0.6, "max_range": 150.0,
            "flight_duration": 60.0, "apogee_time": 20.0, "max_accel_g": 5.0,
            "impact_x": float(rng.normal(100.0, 20.0)),
            "impact_y": float(rng.normal(0.0, 10.0)),
        }
        for _ in range(n)
    ]


@pytest.mark.monte_carlo
class TestScalarStats(unittest.TestCase):
    def test_scalar_stats_keys_and_values(self):
        agg = MonteCarloAggregator.from_runs(_runs())
        stats = agg.scalar_stats("max_altitude")
        for key in ("mean", "std", "min", "p05", "median", "p95", "max", "n_valid"):
            self.assertIn(key, stats)
        self.assertEqual(stats["n_valid"], 50)
        self.assertAlmostEqual(stats["mean"], 1000.0, delta=10.0)

    def test_missing_key_returns_empty(self):
        agg = MonteCarloAggregator.from_runs(_runs(3))
        self.assertEqual(agg.scalar_stats("nonexistent_key_all_nan"), {})

    def test_all_nan_key_returns_empty(self):
        runs = [{"max_altitude": float("nan")} for _ in range(3)]
        agg = MonteCarloAggregator.from_runs(runs)
        self.assertEqual(agg.scalar_stats("max_altitude"), {})


@pytest.mark.monte_carlo
class TestImpactStats(unittest.TestCase):
    def test_nan_impacts_are_masked(self):
        runs = _runs(10)
        runs[0]["impact_x"] = float("nan")
        runs[1]["impact_y"] = float("nan")
        agg = MonteCarloAggregator.from_runs(runs)
        ix, iy = agg.impact_arrays()
        self.assertEqual(len(ix), 8)
        self.assertFalse(np.isnan(ix).any() or np.isnan(iy).any())

    def test_cep_matches_shared_compute_cep(self):
        from src.utils.monte_carlo_stats import compute_cep
        agg = MonteCarloAggregator.from_runs(_runs(100))
        ix, iy = agg.impact_arrays()
        self.assertAlmostEqual(agg.cep(), compute_cep(ix, iy))

    def test_dispersion_ellipse_fields(self):
        agg = MonteCarloAggregator.from_runs(_runs(50))
        el = agg.dispersion_ellipse(sigma_level=2.0)
        self.assertEqual(el["n_points"], 50)
        self.assertGreaterEqual(el["semi_major"], el["semi_minor"])
        self.assertGreater(el["semi_major"], 0.0)
        self.assertIn("angle_deg", el)

    def test_dispersion_ellipse_needs_two_points(self):
        agg = MonteCarloAggregator.from_runs(_runs(1))
        self.assertEqual(agg.dispersion_ellipse(), {})


@pytest.mark.monte_carlo
class TestProbabilityInside(unittest.TestCase):
    def test_all_inside(self):
        runs = [{"impact_x": 10.0, "impact_y": 0.0}, {"impact_x": 0.0, "impact_y": 20.0}]
        agg = MonteCarloAggregator.from_runs(runs)
        pz = agg.probability_inside(100.0)
        self.assertEqual(pz["n"], 2)
        self.assertEqual(pz["inside"], 2)
        self.assertAlmostEqual(pz["p"], 1.0)

    def test_none_inside(self):
        runs = [{"impact_x": 1000.0, "impact_y": 0.0}]
        agg = MonteCarloAggregator.from_runs(runs)
        pz = agg.probability_inside(100.0)
        self.assertEqual(pz["inside"], 0)
        self.assertAlmostEqual(pz["p"], 0.0)

    def test_custom_center_and_nan_masking(self):
        runs = [{"impact_x": 100.0, "impact_y": 0.0},
                {"impact_x": 500.0, "impact_y": 0.0},
                {"impact_x": float("nan"), "impact_y": 0.0}]
        agg = MonteCarloAggregator.from_runs(runs)
        pz = agg.probability_inside(50.0, center_x=100.0, center_y=0.0)
        self.assertEqual(pz["n"], 2)  # NaN pair masked
        self.assertEqual(pz["inside"], 1)
        self.assertAlmostEqual(pz["p"], 0.5)

    def test_no_impacts_returns_nan_p(self):
        agg = MonteCarloAggregator.from_runs(
            [{"impact_x": float("nan"), "impact_y": float("nan")}])
        pz = agg.probability_inside(100.0)
        self.assertEqual(pz["n"], 0)
        self.assertTrue(np.isnan(pz["p"]))


@pytest.mark.monte_carlo
class TestFromSummary(unittest.TestCase):
    def test_degraded_when_no_per_run_records(self):
        summary = {
            "n_successful": 5,
            "statistics": {"max_altitude": {"mean": 1234.5, "std": 10.0}},
        }
        agg = MonteCarloAggregator.from_summary(summary)
        self.assertTrue(agg.degraded)
        stats = agg.scalar_stats("max_altitude")
        self.assertAlmostEqual(stats["mean"], 1234.5)
        self.assertEqual(stats["std"], 0.0)  # degenerate, hence "degraded"

    def test_raises_without_statistics_or_output_file(self):
        with self.assertRaises(ValueError):
            MonteCarloAggregator.from_summary({"n_successful": 3})

    def test_from_runs_not_degraded(self):
        agg = MonteCarloAggregator.from_runs(_runs(3))
        self.assertFalse(agg.degraded)


if __name__ == '__main__':
    unittest.main()
