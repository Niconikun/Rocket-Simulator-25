"""
Unit Tests for WindUtils Module

Tests:
- calculate_relative_velocity
- Wind vector operations
- Coordinate transformations
"""

import unittest
import numpy as np
from src.utils.wind_utils import calculate_relative_velocity


class TestWindUtils(unittest.TestCase):
    """Test suite for wind_utils module"""

    def test_relative_velocity_basic(self):
        """Test basic relative velocity calculation"""
        # Rocket moving at 100 m/s East, no wind
        rocket_vel = np.array([100.0, 0.0, 0.0])
        wind_vel = np.array([0.0, 0.0, 0.0])
        
        v_rel = calculate_relative_velocity(rocket_vel, wind_vel)
        
        self.assertTrue(np.allclose(v_rel, np.array([100.0, 0.0, 0.0])))

    def test_relative_velocity_with_headwind(self):
        """Test relative velocity with headwind"""
        # Rocket moving at 100 m/s East, headwind of 20 m/s (wind from East)
        rocket_vel = np.array([100.0, 0.0, 0.0])
        wind_vel = np.array([-20.0, 0.0, 0.0])  # Wind from East
        
        v_rel = calculate_relative_velocity(rocket_vel, wind_vel)
        
        # Relative velocity should be 120 m/s
        self.assertTrue(np.allclose(v_rel, np.array([120.0, 0.0, 0.0])))

    def test_relative_velocity_with_tailwind(self):
        """Test relative velocity with tailwind"""
        # Rocket moving at 100 m/s East, tailwind of 20 m/s (wind from West)
        rocket_vel = np.array([100.0, 0.0, 0.0])
        wind_vel = np.array([20.0, 0.0, 0.0])  # Wind from West
        
        v_rel = calculate_relative_velocity(rocket_vel, wind_vel)
        
        # Relative velocity should be 80 m/s
        self.assertTrue(np.allclose(v_rel, np.array([80.0, 0.0, 0.0])))

    def test_relative_velocity_with_crosswind(self):
        """Test relative velocity with crosswind"""
        # Rocket moving at 100 m/s East, crosswind of 10 m/s from North
        rocket_vel = np.array([100.0, 0.0, 0.0])
        wind_vel = np.array([0.0, 10.0, 0.0])  # Wind from South
        
        v_rel = calculate_relative_velocity(rocket_vel, wind_vel)
        
        # Relative velocity should have both East and North components
        self.assertAlmostEqual(v_rel[0], 100.0, places=6)
        self.assertAlmostEqual(v_rel[1], -10.0, places=6)
        self.assertAlmostEqual(v_rel[2], 0.0, places=6)

    def test_relative_velocity_3d(self):
        """Test relative velocity in 3D"""
        # Rocket moving East, North, and Up
        rocket_vel = np.array([100.0, 50.0, 10.0])
        wind_vel = np.array([10.0, -5.0, 2.0])
        
        v_rel = calculate_relative_velocity(rocket_vel, wind_vel)
        
        expected = np.array([90.0, 55.0, 8.0])
        self.assertTrue(np.allclose(v_rel, expected))

    def test_relative_velocity_with_lists(self):
        """Test that relative velocity works with lists instead of numpy arrays"""
        rocket_vel = [100.0, 0.0, 0.0]
        wind_vel = [10.0, 0.0, 0.0]
        
        v_rel = calculate_relative_velocity(rocket_vel, wind_vel)
        
        self.assertTrue(np.allclose(v_rel, np.array([90.0, 0.0, 0.0])))

    def test_relative_velocity_magnitude(self):
        """Test relative velocity magnitude calculation"""
        # Rocket moving at 100 m/s, wind at 30 m/s in same direction
        rocket_vel = np.array([100.0, 0.0, 0.0])
        wind_vel = np.array([30.0, 0.0, 0.0])
        
        v_rel = calculate_relative_velocity(rocket_vel, wind_vel)
        magnitude = np.linalg.norm(v_rel)
        
        self.assertAlmostEqual(magnitude, 70.0, places=6)


if __name__ == '__main__':
    unittest.main()
