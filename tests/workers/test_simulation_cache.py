"""
Unit tests for workers.simulation_cache Monte Carlo related behaviour:

- get_planet returns a fresh, unshared Planet per run (no GMST drift between
  Monte Carlo runs)
- get_wind_model cache key depends only on wind-relevant keys, not on the
  rest of the application state (e.g. simulation_results)
"""

import unittest

import pytest

from workers.simulation_cache import get_cache, clear_cache


@pytest.mark.monte_carlo
class TestPlanetCache(unittest.TestCase):
    def setUp(self):
        self.cache = get_cache()
        self.cache.clear()

    def test_get_planet_returns_fresh_instance(self):
        p1 = self.cache.get_planet(4.5, -70.3, 1.0)
        p2 = self.cache.get_planet(4.5, -70.3, 1.0)
        self.assertIsNot(p1, p2)

    def test_planet_state_does_not_leak_between_runs(self):
        p1 = self.cache.get_planet(4.5, -70.3, 1.0)
        p1.update(500.0)  # advances gmst like a simulation step would
        p2 = self.cache.get_planet(4.5, -70.3, 1.0)
        self.assertAlmostEqual(p2.give_gmst(), 1.0)
        self.assertNotAlmostEqual(p1.give_gmst(), p2.give_gmst())

    def test_different_location_gives_different_entry(self):
        self.cache.get_planet(4.5, -70.3, 1.0)
        self.cache.get_planet(4.6, -70.3, 1.0)
        self.assertEqual(self.cache.stats.planets, 2)


@pytest.mark.monte_carlo
class TestWindModelCacheKey(unittest.TestCase):
    def setUp(self):
        self.cache = get_cache()
        self.cache.clear()

    def _cfg(self, **overrides):
        cfg = {
            'wind_enabled': True,
            'wind_model_type': 'constant',
            'wind_speed': 5.0,
            'wind_direction': 180.0,
        }
        cfg.update(overrides)
        return cfg

    def test_unrelated_state_keys_do_not_change_cache_key(self):
        cfg_a = self._cfg(simulation_results={'history': list(range(2000))})
        cfg_b = self._cfg(simulation_results={'history': [1, 2, 3]})
        w1 = self.cache.get_wind_model(cfg_a)
        hits_before = self.cache.stats.hits
        w2 = self.cache.get_wind_model(cfg_b)
        self.assertIs(w1, w2)
        self.assertEqual(self.cache.stats.hits, hits_before + 1)

    def test_wind_key_change_creates_new_model(self):
        w1 = self.cache.get_wind_model(self._cfg(wind_speed=5.0))
        w2 = self.cache.get_wind_model(self._cfg(wind_speed=8.0))
        self.assertIsNot(w1, w2)

    def test_wind_disabled_returns_none(self):
        w = self.cache.get_wind_model(self._cfg(wind_enabled=False))
        self.assertIsNone(w)


if __name__ == '__main__':
    unittest.main()
