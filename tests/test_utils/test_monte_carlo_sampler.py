"""
Unit tests for src.utils.monte_carlo_sampler

Covers:
- ParameterConfig validation
- normal / uniform / fixed / truncated_normal sampling
- wrap-around (modulo) sampling for angular parameters
- truncated-normal fallback to clipping
- MonteCarloSampler.from_state defaults (wind/parachute gating, wrap on angles)
- reproducibility via seed
"""

import unittest

import numpy as np
import pytest

from src.models.state import MockStateProvider
from src.utils.monte_carlo_sampler import MonteCarloSampler, ParameterConfig


@pytest.mark.monte_carlo
class TestParameterConfigValidation(unittest.TestCase):
    def test_normal_requires_nominal_and_sigma(self):
        with self.assertRaises(ValueError):
            ParameterConfig('normal', nominal=1.0)
        with self.assertRaises(ValueError):
            ParameterConfig('normal', sigma=1.0)

    def test_negative_sigma_rejected(self):
        with self.assertRaises(ValueError):
            ParameterConfig('normal', nominal=0.0, sigma=-1.0)

    def test_uniform_requires_low_high_and_order(self):
        with self.assertRaises(ValueError):
            ParameterConfig('uniform', low=1.0)
        with self.assertRaises(ValueError):
            ParameterConfig('uniform', low=5.0, high=5.0)
        with self.assertRaises(ValueError):
            ParameterConfig('uniform', low=6.0, high=5.0)

    def test_fixed_requires_nominal(self):
        with self.assertRaises(ValueError):
            ParameterConfig('fixed')

    def test_wrap_must_be_positive(self):
        with self.assertRaises(ValueError):
            ParameterConfig('normal', nominal=0.0, sigma=1.0, wrap=0.0)
        with self.assertRaises(ValueError):
            ParameterConfig('normal', nominal=0.0, sigma=1.0, wrap=-360.0)


@pytest.mark.monte_carlo
class TestSampling(unittest.TestCase):
    def test_fixed_returns_nominal(self):
        s = MonteCarloSampler({'x': ParameterConfig('fixed', nominal=3.5)}, seed=1)
        for _ in range(10):
            self.assertEqual(s.sample()['x'], 3.5)

    def test_uniform_within_bounds(self):
        s = MonteCarloSampler(
            {'x': ParameterConfig('uniform', low=2.0, high=4.0)}, seed=1)
        vals = [s.sample()['x'] for _ in range(500)]
        self.assertTrue(all(2.0 <= v <= 4.0 for v in vals))
        self.assertGreater(min(vals), 2.0)
        self.assertLess(max(vals), 4.0)

    def test_normal_clipped_to_bounds(self):
        s = MonteCarloSampler(
            {'x': ParameterConfig('normal', nominal=0.0, sigma=10.0,
                                  low=-1.0, high=1.0)}, seed=1)
        vals = [s.sample()['x'] for _ in range(500)]
        self.assertTrue(all(-1.0 <= v <= 1.0 for v in vals))

    def test_truncated_normal_within_bounds(self):
        s = MonteCarloSampler(
            {'x': ParameterConfig('truncated_normal', nominal=5.0, sigma=1.0,
                                  low=3.0, high=7.0)}, seed=1)
        vals = [s.sample()['x'] for _ in range(500)]
        self.assertTrue(all(3.0 <= v <= 7.0 for v in vals))

    def test_truncated_normal_fallback_clips_when_bounds_unreachable(self):
        s = MonteCarloSampler(
            {'x': ParameterConfig('truncated_normal', nominal=0.0, sigma=0.001,
                                  low=100.0, high=200.0)},
            seed=1, max_truncation_attempts=10)
        self.assertEqual(s.sample()['x'], 100.0)

    def test_wrap_keeps_values_in_range(self):
        s = MonteCarloSampler(
            {'az': ParameterConfig('normal', nominal=10.0, sigma=30.0, wrap=360.0)},
            seed=3)
        vals = [s.sample()['az'] for _ in range(500)]
        self.assertTrue(all(0.0 <= v < 360.0 for v in vals))

    def test_wrap_across_boundary_is_symmetric_not_piled_up(self):
        # nominal near 360: with truncation, mass piles at 360; with wrap it
        # should appear just below 360 AND just above 0 (mod 360)
        s = MonteCarloSampler(
            {'az': ParameterConfig('normal', nominal=359.0, sigma=2.0, wrap=360.0)},
            seed=7)
        vals = np.array([s.sample()['az'] for _ in range(4000)])
        self.assertTrue(np.all((vals >= 0.0) & (vals < 360.0)))
        frac_below_3 = np.mean(vals < 3.0)      # wrapped from [360, 362)
        frac_above_356 = np.mean(vals > 356.0)  # direct samples near 359
        self.assertGreater(frac_below_3, 0.05)
        self.assertGreater(frac_above_356, 0.05)
        # circular mean should be close to 359 deg, not 0/360 boundary pile-up
        z = np.mean(np.exp(1j * np.radians(vals)))
        circ_mean = np.degrees(np.angle(z)) % 360.0
        self.assertAlmostEqual(circ_mean, 359.0, delta=1.0)

    def test_reproducible_with_seed(self):
        cfgs = {'x': ParameterConfig('normal', nominal=0.0, sigma=1.0),
                'y': ParameterConfig('uniform', low=0.0, high=1.0)}
        a = MonteCarloSampler(cfgs, seed=42).sample_batch(20)
        b = MonteCarloSampler(cfgs, seed=42).sample_batch(20)
        self.assertEqual(a, b)

    def test_reset_reseeds(self):
        cfgs = {'x': ParameterConfig('normal', nominal=0.0, sigma=1.0)}
        s = MonteCarloSampler(cfgs, seed=42)
        first = s.sample_batch(5)
        s.reset(seed=42)
        self.assertEqual(first, s.sample_batch(5))


@pytest.mark.monte_carlo
class TestFromState(unittest.TestCase):
    def _state(self, **overrides):
        base = {
            'launch_elevation_angle': 85.0,
            'launch_azimuth': 12.0,
            'launch_roll': 0.0,
            'average_temperature': 20.0,
            'wind_enabled': False,
            'parachute_enabled': False,
        }
        base.update(overrides)
        return MockStateProvider(base)

    def test_wind_params_absent_when_disabled(self):
        s = MonteCarloSampler.from_state(self._state(), seed=1)
        self.assertNotIn('wind_speed_ref', s.parameter_names)
        self.assertNotIn('wind_direction', s.parameter_names)

    def test_wind_params_present_when_enabled(self):
        s = MonteCarloSampler.from_state(
            self._state(wind_enabled=True, wind_speed_ref=5.0,
                        wind_direction=180.0), seed=1)
        self.assertIn('wind_speed_ref', s.parameter_names)
        self.assertIn('wind_direction', s.parameter_names)

    def test_parachute_params_absent_when_disabled(self):
        s = MonteCarloSampler.from_state(self._state(), seed=1)
        self.assertNotIn('parachute_cd', s.parameter_names)

    def test_parachute_params_present_when_enabled(self):
        s = MonteCarloSampler.from_state(
            self._state(parachute_enabled=True, parachute_deployment_altitude=300.0,
                        parachute_cd=1.5), seed=1)
        self.assertIn('parachute_deployment_altitude', s.parameter_names)
        self.assertIn('parachute_cd', s.parameter_names)

    def test_azimuth_samples_wrap_mod_360(self):
        s = MonteCarloSampler.from_state(self._state(launch_azimuth=359.5), seed=11)
        vals = np.array([s.sample()['launch_azimuth'] for _ in range(2000)])
        self.assertTrue(np.all((vals >= 0.0) & (vals < 360.0)))
        self.assertLess(vals.min(), 3.0)  # wrapped around the 360 boundary

    def test_extra_configs_override_defaults(self):
        extra = {'launch_elevation_angle': ParameterConfig('fixed', nominal=80.0)}
        s = MonteCarloSampler.from_state(self._state(), seed=1, extra_configs=extra)
        for _ in range(5):
            self.assertEqual(s.sample()['launch_elevation_angle'], 80.0)

    def test_temperature_clip_uses_environmental_constants(self):
        from src.config.constants import EnvironmentalConstants
        s = MonteCarloSampler.from_state(self._state(), seed=1)
        # sample far in the tail to hit the clip bounds
        vals = [s.sample()['average_temperature'] for _ in range(2000)]
        self.assertGreaterEqual(min(vals), EnvironmentalConstants.MIN_TEMPERATURE)
        self.assertLessEqual(max(vals), EnvironmentalConstants.MAX_TEMPERATURE)

    def test_wind_nominal_falls_back_to_legacy_wind_speed(self):
        state = self._state(wind_enabled=True, wind_speed=7.5)
        s = MonteCarloSampler.from_state(state, seed=1)
        vals = [s.sample()['wind_speed_ref'] for _ in range(200)]
        self.assertAlmostEqual(float(np.mean(vals)), 7.5, delta=0.2)

    def test_wind_sigma_is_absolute_constant(self):
        from src.config.constants import MonteCarloConstants
        state = self._state(wind_enabled=True, wind_speed_ref=20.0)
        s = MonteCarloSampler.from_state(state, seed=1)
        vals = np.array([s.sample()['wind_speed_ref'] for _ in range(3000)])
        # absolute sigma (1.0 m/s), not 20% of a 20 m/s nominal (which would be 4.0)
        self.assertAlmostEqual(float(np.std(vals)), MonteCarloConstants.DEFAULT_SIGMA_WIND_SPEED, delta=0.1)

    def test_parachute_cd_sigma_is_absolute_constant(self):
        from src.config.constants import MonteCarloConstants
        state = self._state(parachute_enabled=True, parachute_cd=1.5)
        s = MonteCarloSampler.from_state(state, seed=1)
        vals = np.array([s.sample()['parachute_cd'] for _ in range(3000)])
        self.assertAlmostEqual(float(np.std(vals)), MonteCarloConstants.DEFAULT_SIGMA_PARACHUTE_CD, delta=0.02)


if __name__ == '__main__':
    unittest.main()
