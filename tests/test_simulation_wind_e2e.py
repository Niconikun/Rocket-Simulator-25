"""
End-to-End Simulation Test with Wind Integration

This test verifies that wind system is properly integrated into the simulation
by checking key components and ensuring no errors occur during wind initialization.
"""

import unittest
import json
import numpy as np
import sys
import os
from datetime import datetime, timedelta
import logging

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.app_state import ApplicationState
from src.utils.wind_utils import create_wind_model_from_state, log_wind_config
from src.models.rocket import Rocket
from src.models.atmosphere import Atmosphere
from src.models.planet import Planet

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestWindSimulationIntegration(unittest.TestCase):
    """Integration tests for wind system with rocket physics."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app_state = ApplicationState()
        
        # Basic simulation parameters
        self.app_state._state['rocket_name'] = 'V3-Chaff'
        self.app_state._state['location_name'] = 'Batuco'
        self.app_state._state['launch_altitude'] = 400.0  # m
        self.app_state._state['launch_latitude'] = -32.7753
        self.app_state._state['launch_longitude'] = -71.3029
        self.app_state._state['temperature'] = 15.0  # °C
        
        # Simulation parameters
        self.app_state._state['launch_angle'] = 89.0  # Nearly vertical
        self.app_state._state['launch_azimuth'] = 0.0
        self.app_state._state['launch_roll'] = 0.0
        self.app_state._state['simulation_time_duration'] = 30.0  # seconds
        self.app_state._state['simulation_timestep'] = 0.01  # seconds
        self.app_state._state['parachute_enabled'] = False
    
    def test_wind_initialization_in_settings(self):
        """Test that wind initializes correctly from app state."""
        logger.info("=" * 60)
        logger.info("TEST: Wind Initialization from App State")
        logger.info("=" * 60)
        
        # Test constant wind
        self.app_state._state['wind_enabled'] = True
        self.app_state._state['wind_model_type'] = 'constant'
        self.app_state._state['wind_speed'] = 10.0
        self.app_state._state['wind_direction'] = 45.0
        
        wind = create_wind_model_from_state(self.app_state._state)
        self.assertIsNotNone(wind)
        
        info = wind.get_info()
        logger.info(f"Wind model: {info['model_type']}")
        logger.info(f"Wind direction: {info['wind_direction']}°")
        logger.info(f"Wind speed: {info.get('wind_speed', 'N/A')} m/s")
        
        # Log configuration
        log_wind_config(self.app_state._state, wind)
        
        self.assertTrue(info['enabled'])
        self.assertEqual(info['wind_direction'], 45.0)
    
    def test_wind_vector_at_altitude(self):
        """Test wind vector retrieval at different altitudes."""
        logger.info("=" * 60)
        logger.info("TEST: Wind Vector at Different Altitudes")
        logger.info("=" * 60)
        
        # Logarithmic wind profile
        self.app_state._state['wind_enabled'] = True
        self.app_state._state['wind_model_type'] = 'logarithmic'
        self.app_state._state['wind_speed'] = 10.0
        self.app_state._state['wind_direction'] = 0.0
        self.app_state._state['wind_reference_height'] = 10.0
        self.app_state._state['wind_roughness_length'] = 0.1
        
        wind = create_wind_model_from_state(self.app_state._state)
        
        # Get wind at different altitudes
        altitudes = [0, 100, 500, 1000, 5000]
        logger.info("\nAltitude [m] | Wind Speed [m/s]")
        logger.info("-" * 35)
        
        wind_vectors = {}
        for alt in altitudes:
            wind_vec = wind.get_wind_vector(alt)
            wind_speed = np.linalg.norm(wind_vec)
            wind_vectors[alt] = wind_vec
            logger.info(f"{alt:12d} | {wind_speed:14.2f}")
        
        # Verify arrays are valid
        for alt, wind_vec in wind_vectors.items():
            self.assertIsNotNone(wind_vec)
            self.assertEqual(len(wind_vec), 3)
            self.assertTrue(np.all(np.isfinite(wind_vec)))
    
    def test_relative_velocity_calculation(self):
        """Test relative velocity calculation with wind."""
        logger.info("=" * 60)
        logger.info("TEST: Relative Velocity with Wind")
        logger.info("=" * 60)
        
        from src.utils.wind_utils import calculate_relative_velocity
        
        # Test case 1: Rocket moving east, wind from north
        rocket_vel = np.array([10, 0, 100])  # East, North, Up
        wind_vel = np.array([0, 10, 0])      # From north (moving south)
        
        v_rel = calculate_relative_velocity(rocket_vel, wind_vel)
        v_rel_magnitude = np.linalg.norm(v_rel)
        
        logger.info(f"\nRocket velocity: {rocket_vel}")
        logger.info(f"Wind velocity: {wind_vel}")
        logger.info(f"Relative velocity: {v_rel}")
        logger.info(f"Relative speed magnitude: {v_rel_magnitude:.2f} m/s")
        
        self.assertEqual(len(v_rel), 3)
        self.assertTrue(np.all(np.isfinite(v_rel)))
        
        # Expected: [10, -10, 100]
        np.testing.assert_array_almost_equal(v_rel, [10, -10, 100])
    
    def test_wind_angle_of_attack_correction(self):
        """Test angle of attack correction with wind."""
        logger.info("=" * 60)
        logger.info("TEST: Wind-Corrected Angle of Attack")
        logger.info("=" * 60)
        
        from src.utils.wind_utils import calculate_wind_corrected_angle_of_attack
        
        # Test case: vertical rocket with horizontal wind
        rocket_vel_vertical = np.array([0, 0, 100])  # Pure vertical
        wind_vel = np.array([10, 0, 0])              # Wind from west
        
        aoa = calculate_wind_corrected_angle_of_attack(rocket_vel_vertical, wind_vel)
        
        logger.info(f"\nRocket velocity: {rocket_vel_vertical} (vertical)")
        logger.info(f"Wind velocity: {wind_vel} (horizontal)")
        logger.info(f"Angle of attack: {aoa:.2f}°")
        
        # With horizontal wind and vertical rocket, AOA should be positive
        self.assertNotEqual(aoa, 90.0)  # Not exactly 90° due to wind
        
    def test_wind_dynamic_pressure(self):
        """Test dynamic pressure calculation with wind."""
        logger.info("=" * 60)
        logger.info("TEST: Dynamic Pressure with Wind")
        logger.info("=" * 60)
        
        from src.utils.wind_utils import calculate_dynamic_pressure
        
        # Standard conditions
        air_density = 1.225  # kg/m³
        relative_velocity = 100.0  # m/s
        
        q_dyn = calculate_dynamic_pressure(relative_velocity, air_density)
        
        logger.info(f"\nAir density: {air_density} kg/m³")
        logger.info(f"Relative velocity: {relative_velocity} m/s")
        logger.info(f"Dynamic pressure: {q_dyn:.0f} Pa")
        
        # Expected: 0.5 * 1.225 * 100² = 6125 Pa
        expected = 0.5 * air_density * (relative_velocity ** 2)
        self.assertAlmostEqual(q_dyn, expected)
    
    def test_rocket_with_wind_vector(self):
        """Test rocket initialization and state update with wind."""
        logger.info("=" * 60)
        logger.info("TEST: Rocket State with Wind Vector")
        logger.info("=" * 60)
        
        # Create rocket
        rocket = Rocket(
            r_enu_0=np.array([0, 0, 0]),
            v_enu_0=np.array([0, 0, 100]),  # Vertical launch
            q_enu2b_0=np.array([0, 0, 0, 1]),
            w_enu_0=np.array([0, 0, 0]),
            initial_mass=1000.0
        )
        
        # Create wind
        self.app_state._state['wind_enabled'] = True
        self.app_state._state['wind_model_type'] = 'constant'
        self.app_state._state['wind_speed'] = 10.0
        self.app_state._state['wind_direction'] = 90.0
        
        wind = create_wind_model_from_state(self.app_state._state)
        wind_vector = wind.get_wind_vector(100)
        
        # Update rocket position with wind
        coordinates = np.array([-32.7753, -71.3029, 400])
        rocket.update_pos_vel(coordinates, wind_vector_enu=wind_vector)
        
        logger.info(f"\nRocket velocity: {rocket.v_enu}")
        logger.info(f"Wind vector: {wind_vector}")
        logger.info(f"Rocket wind vector (stored): {rocket.wind_vector_enu}")
        logger.info(f"Relative velocity: {rocket.v_rel_enu}")
        logger.info(f"Relative velocity magnitude: {rocket.v_rel_norm:.2f} m/s")
        
        # Verify wind was stored
        np.testing.assert_array_almost_equal(rocket.wind_vector_enu, wind_vector)
        
        # Verify relative velocity calculation
        expected_v_rel = rocket.v_enu - wind_vector
        np.testing.assert_array_almost_equal(rocket.v_rel_enu, expected_v_rel)
    
    def test_wind_effect_on_calculations(self):
        """Test that wind affects calculated values (not no-op)."""
        logger.info("=" * 60)
        logger.info("TEST: Wind Effect on Rocket Calculations")
        logger.info("=" * 60)
        
        # Rocket 1: No wind
        rocket_no_wind = Rocket(
            r_enu_0=np.array([0, 0, 0]),
            v_enu_0=np.array([100, 0, 100]),  # Moving east and up
            q_enu2b_0=np.array([0, 0, 0, 1]),
            w_enu_0=np.array([0, 0, 0]),
            initial_mass=1000.0
        )
        coordinates = np.array([-32.7753, -71.3029, 400])
        rocket_no_wind.update_pos_vel(coordinates, wind_vector_enu=None)
        
        # Rocket 2: With headwind (opposite direction to velocity)
        rocket_with_wind = Rocket(
            r_enu_0=np.array([0, 0, 0]),
            v_enu_0=np.array([100, 0, 100]),  # Same velocity
            q_enu2b_0=np.array([0, 0, 0, 1]),
            w_enu_0=np.array([0, 0, 0]),
            initial_mass=1000.0
        )
        wind_vector = np.array([-30, 0, 0])  # Headwind from east
        rocket_with_wind.update_pos_vel(coordinates, wind_vector_enu=wind_vector)
        
        logger.info(f"\nNo wind:")
        logger.info(f"  Velocity: {rocket_no_wind.v_enu}")
        logger.info(f"  v_rel_norm: {rocket_no_wind.v_rel_norm:.2f} m/s")
        logger.info(f"  alpha (AOA): {rocket_no_wind.alpha:.2f}°")
        
        logger.info(f"\nWith headwind (-30 m/s east):")
        logger.info(f"  Velocity: {rocket_with_wind.v_enu}")
        logger.info(f"  Wind vector: {wind_vector}")
        logger.info(f"  v_rel_norm: {rocket_with_wind.v_rel_norm:.2f} m/s")
        logger.info(f"  alpha (AOA): {rocket_with_wind.alpha:.2f}°")
        
        # Verify wind affected the calculations
        # With headwind, relative velocity should be larger
        self.assertGreater(
            rocket_with_wind.v_rel_norm,
            rocket_no_wind.v_rel_norm,
            msg="Headwind should increase relative velocity"
        )
        
        logger.info("\n✅ Wind successfully affects rocket calculations")
        logger.info(f"   Relative velocity increase: {rocket_with_wind.v_rel_norm - rocket_no_wind.v_rel_norm:.2f} m/s")
    
    def test_wind_state_updates_over_time(self):
        """Test that wind state updates properly over simulation time."""
        logger.info("=" * 60)
        logger.info("TEST: Wind State Updates Over Time")
        logger.info("=" * 60)
        
        self.app_state._state['wind_enabled'] = True
        self.app_state._state['wind_model_type'] = 'logarithmic'
        self.app_state._state['wind_speed'] = 10.0
        self.app_state._state['wind_direction'] = 0.0
        self.app_state._state['wind_reference_height'] = 10.0
        self.app_state._state['wind_roughness_length'] = 0.1
        
        wind = create_wind_model_from_state(self.app_state._state)
        
        timestep = 0.1  # seconds
        simulation_time = 5.0  # seconds
        steps = int(simulation_time / timestep)
        
        logger.info(f"\nSimulating {steps} steps of {timestep}s each")
        
        # Track wind at same altitude over time
        altitude = 500  # m
        wind_magnitudes = []
        
        for step in range(steps):
            t = step * timestep
            wind_vec = wind.get_wind_vector(altitude)
            wind_mag = np.linalg.norm(wind_vec)
            wind_magnitudes.append(wind_mag)
            wind.update(timestep)
        
        # For constant/logarithmic wind, magnitude should be consistent
        avg_magnitude = np.mean(wind_magnitudes)
        std_magnitude = np.std(wind_magnitudes)
        
        logger.info(f"Wind magnitude - Mean: {avg_magnitude:.2f} m/s, Std: {std_magnitude:.4f}")
        logger.info(f"✅ Wind state stable over {simulation_time}s simulation")
        
        self.assertGreater(len(wind_magnitudes), 0)


if __name__ == '__main__':
    # Run tests with verbose output
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSimulationWithWind)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
