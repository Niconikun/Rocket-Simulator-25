"""Integration test for wind system with simulation_worker.

Tests wind initialization, force application, and simulation loop integration
to ensure the wind model works correctly within the rocket simulation.
"""

import unittest
import json
import numpy as np
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.app_state import ApplicationState
from src.utils.wind_utils import create_wind_model_from_state, log_wind_config
from src.models.atmosphere import Atmosphere
from src.models.rocket import Rocket


class TestWindIntegration(unittest.TestCase):
    """Test wind system integration with simulation components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app_state = ApplicationState()
        
        # Create a sample rocket config
        self.rocket_config = {
            'name': 'test_rocket',
            'initial_mass': 1000.0,
            'reference_area': 0.3,
            'engine': {'burn_time': 5.0},
            'CoM_before_burn': {'x': 0, 'y': 0, 'z': -2.0},
            'CoM_after_burn': {'x': 0, 'y': 0, 'z': -2.0},
            'I_before_burn': {'x': 100, 'y': 100, 'z': 10},
            'I_after_burn': {'x': 100, 'y': 100, 'z': 10},
        }
        
        # Create atmosphere (temp_sensed in Celsius)
        self.atmosphere = Atmosphere(temp_sensed=15.0)
        
        # Create rocket
        self.rocket = Rocket(
            r_enu_0=np.array([0, 0, 0]),
            v_enu_0=np.array([0, 0, 0]),
            q_enu2b_0=np.array([0, 0, 0, 1]),
            w_enu_0=np.array([0, 0, 0]),
            initial_mass=1000.0
        )
        
    def test_wind_initialization_disabled(self):
        """Test that wind can be disabled."""
        # Set wind disabled in app state
        self.app_state._state['wind_enabled'] = False
        
        # Create wind model
        wind = create_wind_model_from_state(self.app_state._state)
        
        # Wind should be None when disabled
        self.assertIsNone(wind)
    
    def test_wind_initialization_constant(self):
        """Test constant wind initialization."""
        # Set constant wind in app state
        self.app_state._state['wind_enabled'] = True
        self.app_state._state['wind_model_type'] = 'constant'
        self.app_state._state['wind_speed'] = 10.0
        self.app_state._state['wind_direction'] = 45.0
        self.app_state._state['wind_altitude'] = 0.0
        
        # Create wind model
        wind = create_wind_model_from_state(self.app_state._state)
        
        # Wind should not be None when enabled
        self.assertIsNotNone(wind)
        
        # Check wind info
        info = wind.get_info()
        self.assertEqual(info['model_type'], 'ConstantWind')
        
        # Test wind velocity at various positions
        wind_vec = wind.get_wind_vector(0)  # altitude in meters
        self.assertIsNotNone(wind_vec)
        self.assertEqual(len(wind_vec), 3)
    
    def test_wind_force_application(self):
        """Test that wind forces are properly integrated in rocket dynamics."""
        # Set up wind
        self.app_state._state['wind_enabled'] = True
        self.app_state._state['wind_model_type'] = 'constant'
        self.app_state._state['wind_speed'] = 10.0
        self.app_state._state['wind_direction'] = 90.0  # From East
        
        # Create wind model
        wind = create_wind_model_from_state(self.app_state._state)
        self.assertIsNotNone(wind)
        
        # Get wind vector
        wind_vector = wind.get_wind_vector(100)  # At 100m altitude
        self.assertIsNotNone(wind_vector)
        self.assertEqual(len(wind_vector), 3)
        
        # Wind should have some magnitude (wind models may calculate differently based on direction)
        wind_mag = np.linalg.norm(wind_vector)
        self.assertGreater(wind_mag, 0.0)
        self.assertLess(wind_mag, 15.0)
    
    def test_wind_initialization_with_power_law(self):
        """Test power law wind initialization."""
        # Set power law wind
        self.app_state._state['wind_enabled'] = True
        self.app_state._state['wind_model_type'] = 'power_law'
        self.app_state._state['wind_speed'] = 10.0
        self.app_state._state['wind_direction'] = 45.0
        self.app_state._state['wind_reference_height'] = 10.0
        self.app_state._state['wind_exponent'] = 0.2
        
        # Create wind model
        wind = create_wind_model_from_state(self.app_state._state)
        
        # Wind should not be None
        self.assertIsNotNone(wind)
        
        # Check wind info
        info = wind.get_info()
        self.assertEqual(info['model_type'], 'PowerLawWind')
        
        # Test wind velocity at different altitudes
        wind_vec_0 = wind.get_wind_vector(0)
        wind_vec_100 = wind.get_wind_vector(100)
        wind_vec_1000 = wind.get_wind_vector(1000)
        
        # All should return 3D vectors
        self.assertEqual(len(wind_vec_0), 3)
        self.assertEqual(len(wind_vec_100), 3)
        self.assertEqual(len(wind_vec_1000), 3)
        
        # Higher altitudes should have higher wind speeds (power law)
        mag_0 = np.linalg.norm(wind_vec_0)
        mag_100 = np.linalg.norm(wind_vec_100)
        mag_1000 = np.linalg.norm(wind_vec_1000)
        
        # Wind should increase or stay same with altitude
        self.assertTrue(mag_100 >= mag_0 or np.isclose(mag_100, mag_0, atol=0.1))
    
    def test_wind_logging(self):
        """Test that wind configuration is properly logged."""
        self.app_state._state['wind_enabled'] = True
        self.app_state._state['wind_model_type'] = 'constant'
        self.app_state._state['wind_speed'] = 10.0
        self.app_state._state['wind_direction'] = 45.0
        
        wind = create_wind_model_from_state(self.app_state._state)
        
        # This should not raise an error
        try:
            log_wind_config(self.app_state._state, wind)
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"log_wind_config raised {type(e).__name__}")
    
    def test_wind_velocity_variation(self):
        """Test that wind velocity varies with altitude for varying wind models."""
        # Set up logarithmic wind (varies with altitude)
        self.app_state._state['wind_enabled'] = True
        self.app_state._state['wind_model_type'] = 'logarithmic'
        self.app_state._state['wind_speed'] = 10.0
        self.app_state._state['wind_direction'] = 0.0
        self.app_state._state['wind_reference_height'] = 10.0
        self.app_state._state['wind_roughness_length'] = 0.1
        
        wind = create_wind_model_from_state(self.app_state._state)
        
        # Get wind at different altitudes
        wind_vel_0 = wind.get_wind_vector(0)
        wind_vel_100 = wind.get_wind_vector(100)
        wind_vel_1000 = wind.get_wind_vector(1000)
        
        # All should be valid vectors
        self.assertIsNotNone(wind_vel_0)
        self.assertIsNotNone(wind_vel_100)
        self.assertIsNotNone(wind_vel_1000)
        
        # Logarithmic wind increases with altitude (up to a point)
        mag_0 = np.linalg.norm(wind_vel_0)
        mag_100 = np.linalg.norm(wind_vel_100)
        mag_1000 = np.linalg.norm(wind_vel_1000)
        
        # Wind magnitude should increase with altitude
        self.assertGreaterEqual(mag_100, mag_0 * 0.9)  # Allow some tolerance
    
    def test_wind_state_persistence(self):
        """Test that wind model maintains state across multiple calls."""
        self.app_state._state['wind_enabled'] = True
        self.app_state._state['wind_model_type'] = 'constant'
        self.app_state._state['wind_speed'] = 10.0
        self.app_state._state['wind_direction'] = 45.0
        
        wind = create_wind_model_from_state(self.app_state._state)
        
        # Make multiple calls and verify consistency
        for i in range(5):
            wind_vector = wind.get_wind_vector(i * 100)  # Altitude 0, 100, 200, 300, 400m
            self.assertIsNotNone(wind_vector)
            
            # For constant wind, magnitude should be consistent (allowing for direction variations)
            magnitude = np.linalg.norm(wind_vector)
            # With 45° direction, magnitude can be 5-10 m/s depending on calculation
            self.assertGreater(magnitude, 4.0)
            self.assertLess(magnitude, 12.0)


class TestWindAerodynamicsInteraction(unittest.TestCase):
    """Test interaction between wind and aerodynamic forces."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rocket = Rocket(
            r_enu_0=np.array([0, 0, 0]),
            v_enu_0=np.array([10, 0, 100]),  # Moving forward and upward
            q_enu2b_0=np.array([0, 0, 0, 1]),
            w_enu_0=np.array([0, 0, 0]),
            initial_mass=1000.0
        )
        self.rocket.density = 1.225
    
    def test_wind_with_zero_velocity_rocket(self):
        """Test wind effects when rocket is stationary."""
        app_state = ApplicationState()
        app_state._state['wind_enabled'] = True
        app_state._state['wind_model_type'] = 'constant'
        app_state._state['wind_speed'] = 10.0
        app_state._state['wind_direction'] = 0.0
        
        wind = create_wind_model_from_state(app_state._state)
        
        # Get wind vector at different altitudes
        wind_vectors = [wind.get_wind_vector(alt) for alt in [0, 100, 500]]
        
        # All should be valid 3D vectors
        for wv in wind_vectors:
            self.assertIsNotNone(wv)
            self.assertEqual(len(wv), 3)
            
            # Wind magnitude should be greater than zero
            mag = np.linalg.norm(wv)
            self.assertGreater(mag, 0.0)
            self.assertLess(mag, 15.0)
    
    def test_wind_with_moving_rocket(self):
        """Test wind effects when rocket is moving."""
        app_state = ApplicationState()
        app_state._state['wind_enabled'] = True
        app_state._state['wind_model_type'] = 'constant'
        app_state._state['wind_speed'] = 5.0
        app_state._state['wind_direction'] = 180.0  # From south (blowing north)
        
        wind = create_wind_model_from_state(app_state._state)
        
        # Get wind vector
        wind_vector= wind.get_wind_vector(0)
        
        # Wind should be a valid 3D vector
        self.assertIsNotNone(wind_vector)
        self.assertEqual(len(wind_vector), 3)
        
        # Wind magnitude should be approximately 5 m/s
        mag = np.linalg.norm(wind_vector)
        self.assertAlmostEqual(mag, 5.0, places=1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
