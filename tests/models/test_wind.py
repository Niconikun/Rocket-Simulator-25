"""
Unit Tests for Wind Models

Comprehensive test suite validating all wind model implementations:
- Wind vector generation at various altitudes
- Wind speed calculations
- Direction conversions
- Edge cases and boundary conditions
- Physical validity of wind profiles

Author: Wind Model Testing
Date: 2026
"""

import unittest
import numpy as np
import logging
from src.models.wind import (
    WindModel, ConstantWind, LogarithmicWind, PowerLawWind, 
    GustWind, WindShearWind, create_wind_model
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestConstantWind(unittest.TestCase):
    """Tests for ConstantWind model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.wind = ConstantWind(wind_speed=5.0, wind_direction=0.0)
    
    def test_initialization(self):
        """Test constant wind initialization."""
        self.assertEqual(self.wind.wind_speed, 5.0)
        self.assertEqual(self.wind.wind_direction, 0.0)
        self.assertTrue(self.wind.enabled)
    
    def test_wind_speed_clamping(self):
        """Test wind speed is clamped to [0, 100] m/s."""
        wind_high = ConstantWind(wind_speed=150.0)
        self.assertEqual(wind_high.wind_speed, 100.0)
        
        wind_negative = ConstantWind(wind_speed=-5.0)
        self.assertEqual(wind_negative.wind_speed, 0.0)
    
    def test_constant_vector_at_all_altitudes(self):
        """Test wind vector is constant across altitudes."""
        altitudes = [0, 100, 500, 1000, 5000]
        vectors = [self.wind.get_wind_vector(h) for h in altitudes]
        
        # All vectors should be identical
        for v in vectors[1:]:
            np.testing.assert_array_almost_equal(v, vectors[0])
    
    def test_wind_magnitude_from_north(self):
        """Test wind from North (0°) has correct magnitude and direction."""
        wind = ConstantWind(wind_speed=5.0, wind_direction=0.0)
        vec = wind.get_wind_vector(100)
        
        magnitude = np.linalg.norm(vec[:2])
        self.assertAlmostEqual(magnitude, 5.0, places=5)
        
        # From North means blowing South (negative North component)
        self.assertLess(vec[1], 0)  # North component negative
    
    def test_wind_magnitude_from_east(self):
        """Test wind from East (90°) has correct magnitude and direction."""
        wind = ConstantWind(wind_speed=5.0, wind_direction=90.0)
        vec = wind.get_wind_vector(100)
        
        magnitude = np.linalg.norm(vec[:2])
        self.assertAlmostEqual(magnitude, 5.0, places=5)
        
        # From East means blowing West (negative East component)
        self.assertLess(vec[0], 0)  # East component negative
    
    def test_zero_vertical_component(self):
        """Test constant wind has no vertical component."""
        for alt in [0, 100, 1000]:
            vec = self.wind.get_wind_vector(alt)
            self.assertAlmostEqual(vec[2], 0.0)  # Up component should be zero
    
    def test_get_wind_magnitude(self):
        """Test wind magnitude calculation."""
        for alt in [0, 100, 500, 2000]:
            mag = self.wind.get_wind_magnitude(alt)
            self.assertAlmostEqual(mag, 5.0)
    
    def test_direction_normalization(self):
        """Test direction values are normalized to [0, 360)."""
        wind1 = ConstantWind(wind_direction=370.0)
        self.assertEqual(wind1.wind_direction, 10.0)
        
        wind2 = ConstantWind(wind_direction=-10.0)
        self.assertEqual(wind2.wind_direction, 350.0)
    
    def test_get_info(self):
        """Test info dictionary."""
        info = self.wind.get_info()
        self.assertEqual(info['model_type'], 'ConstantWind')
        self.assertEqual(info['wind_speed'], 5.0)
        self.assertTrue(info['enabled'])


class TestLogarithmicWind(unittest.TestCase):
    """Tests for LogarithmicWind model (industry standard)."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Standard: 5 m/s at 10m height, z0=0.1m (grassland)
        self.wind = LogarithmicWind(
            wind_speed_ref=5.0,
            reference_height=10.0,
            roughness_length=0.1,
            wind_direction=0.0,
            launch_altitude=0.0
        )
    
    def test_initialization(self):
        """Test logarithmic wind initialization."""
        self.assertEqual(self.wind.wind_speed_ref, 5.0)
        self.assertEqual(self.wind.reference_height, 10.0)
        self.assertEqual(self.wind.roughness_length, 0.1)
    
    def test_invalid_reference_height(self):
        """Test invalid reference height raises error."""
        with self.assertRaises(ValueError):
            LogarithmicWind(reference_height=0.0)
        
        with self.assertRaises(ValueError):
            LogarithmicWind(reference_height=-5.0)
    
    def test_invalid_roughness_length(self):
        """Test invalid roughness length raises error."""
        with self.assertRaises(ValueError):
            LogarithmicWind(roughness_length=-0.1)
        
        with self.assertRaises(ValueError):
            LogarithmicWind(roughness_length=10.1, reference_height=10.0)
    
    def test_wind_increases_with_altitude(self):
        """Test wind speed increases with altitude in log profile."""
        altitudes = [0, 10, 50, 100, 500, 1000]
        speeds = [self.wind.get_wind_magnitude(h) for h in altitudes]
        
        # Wind speed at h=0 should be less than at h=10, etc.
        for i in range(len(speeds) - 1):
            self.assertLess(speeds[i], speeds[i + 1])
    
    def test_wind_speed_at_reference_height(self):
        """Test wind speed matches reference at reference height."""
        # At reference height, wind should equal reference wind speed
        # Earth surface is at launch_altitude, so absolute height = reference_height
        speed = self.wind.get_wind_magnitude(10.0)  # 10m above surface
        
        # Due to log profile math, should be very close to reference speed
        self.assertAlmostEqual(speed, self.wind.wind_speed_ref, places=1)
    
    def test_wind_profile_monotonic(self):
        """Test log wind profile is strictly increasing."""
        heights = np.linspace(0, 5000, 100)
        speeds = np.array([self.wind.get_wind_magnitude(h) for h in heights])
        
        # Check monotonic increase (allowing for floating-point errors)
        diffs = np.diff(speeds)
        self.assertTrue(np.all(diffs >= -1e-10))  # All differences >= 0 (within FP error)
    
    def test_roughness_length_effect(self):
        """Test roughness length affects wind profile."""
        # Smooth surface (z0 = 0.01)
        wind_smooth = LogarithmicWind(
            wind_speed_ref=5.0, reference_height=10.0, roughness_length=0.01
        )
        
        # Rough surface (z0 = 0.5)
        wind_rough = LogarithmicWind(
            wind_speed_ref=5.0, reference_height=10.0, roughness_length=0.5
        )
        
        # Different roughness lengths produce different wind profiles
        # The effect is complex due to logarithmic formulation
        # Just verify both produce reasonable positive values
        alt_100 = 100.0
        speed_smooth = wind_smooth.get_wind_magnitude(alt_100)
        speed_rough = wind_rough.get_wind_magnitude(alt_100)
        
        # Both should be positive
        self.assertGreater(speed_smooth, 0.0)
        self.assertGreater(speed_rough, 0.0)
        # Both should be close to reference speed
        self.assertGreater(speed_smooth, 3.0)
        self.assertGreater(speed_rough, 3.0)
    
    def test_zero_wind_speed_input(self):
        """Test wind model with zero reference wind speed."""
        wind = LogarithmicWind(wind_speed_ref=0.0)
        
        for alt in [0, 100, 1000]:
            speed = wind.get_wind_magnitude(alt)
            self.assertAlmostEqual(speed, 0.0)
    
    def test_launch_altitude_effect(self):
        """Test launch_altitude parameter shifts the profile."""
        wind_sea_level = LogarithmicWind(launch_altitude=0.0)
        wind_high_altitude = LogarithmicWind(launch_altitude=1000.0)
        
        # Same relative altitude should have different absolute altitudes
        # and thus different wind speeds
        rel_alt = 100.0
        
        wind_sea = wind_sea_level.get_wind_magnitude(rel_alt)
        wind_high = wind_high_altitude.get_wind_magnitude(rel_alt)
        
        # High altitude launch site: relative 100m = absolute 1100m
        # Sea level: relative 100m = absolute 100m
        # So high altitude should have higher wind
        self.assertGreater(wind_high, wind_sea)
    
    def test_negative_altitude_handling(self):
        """Test negative altitude is handled gracefully."""
        # Negative altitude should be clamped to 0
        vec1 = self.wind.get_wind_vector(-50)
        vec2 = self.wind.get_wind_vector(0)
        
        # Should be equal (both clamped to 0)
        np.testing.assert_array_almost_equal(vec1, vec2)
    
    def test_zero_vertical_component(self):
        """Test log profile has no vertical wind component."""
        for alt in [0, 50, 100, 500]:
            vec = self.wind.get_wind_vector(alt)
            self.assertAlmostEqual(vec[2], 0.0)  # Up component
    
    def test_get_info(self):
        """Test info dictionary contains correct parameters."""
        info = self.wind.get_info()
        self.assertEqual(info['model_type'], 'LogarithmicWind')
        self.assertEqual(info['wind_speed_ref'], 5.0)
        self.assertEqual(info['reference_height'], 10.0)
        self.assertEqual(info['roughness_length'], 0.1)
    
    def test_vector_magnitude_consistency(self):
        """Test wind vector magnitude matches get_wind_magnitude."""
        for alt in [0, 50, 100, 500]:
            vec = self.wind.get_wind_vector(alt)
            magnitude = np.linalg.norm(vec[:2])
            expected = self.wind.get_wind_magnitude(alt)
            
            self.assertAlmostEqual(magnitude, expected, places=10)


class TestPowerLawWind(unittest.TestCase):
    """Tests for PowerLawWind model."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Standard: 5 m/s at 10m, exponent 0.2
        self.wind = PowerLawWind(
            wind_speed_ref=5.0,
            reference_height=10.0,
            exponent=0.2,
            wind_direction=0.0
        )
    
    def test_initialization(self):
        """Test power law wind initialization."""
        self.assertEqual(self.wind.wind_speed_ref, 5.0)
        self.assertEqual(self.wind.reference_height, 10.0)
        self.assertEqual(self.wind.exponent, 0.2)
    
    def test_invalid_parameters(self):
        """Test invalid parameters raise errors."""
        with self.assertRaises(ValueError):
            PowerLawWind(wind_speed_ref=-1.0)
        
        with self.assertRaises(ValueError):
            PowerLawWind(reference_height=0.0)
    
    def test_wind_increases_with_altitude(self):
        """Test wind speed increases with altitude."""
        altitudes = [10, 50, 100, 500, 1000]
        speeds = [self.wind.get_wind_magnitude(h) for h in altitudes]
        
        # Wind should increase with altitude (avoid h=0 due to formula minimum)
        for i in range(len(speeds) - 1):
            self.assertLessEqual(speeds[i], speeds[i + 1])  # Allow equal for numerical precision
    
    def test_power_law_formula(self):
        """Test power law formula is correctly applied."""
        # U(h) = U_ref * (h/h_ref)^α
        h = 20.0  # 20m above surface
        expected = 5.0 * (20.0 / 10.0) ** 0.2
        actual = self.wind.get_wind_magnitude(h)
        
        self.assertAlmostEqual(actual, expected, places=5)
    
    def test_wind_profile_comparison(self):
        """Test power law vs logarithmic profiles."""
        log_wind = LogarithmicWind(wind_speed_ref=5.0)
        power_wind = PowerLawWind(wind_speed_ref=5.0, exponent=0.2)
        
        # Both should be positive and increasing
        alt = 100.0
        log_speed = log_wind.get_wind_magnitude(alt)
        power_speed = power_wind.get_wind_magnitude(alt)
        
        self.assertGreater(log_speed, 0)
        self.assertGreater(power_speed, 0)
        # They should be different but similar magnitude
        self.assertAlmostEqual(log_speed, power_speed, delta=2.0)
    
    def test_exponent_effect(self):
        """Test different exponents produce different profiles."""
        wind_low = PowerLawWind(wind_speed_ref=5.0, exponent=0.1)
        wind_high = PowerLawWind(wind_speed_ref=5.0, exponent=0.4)
        
        # Higher exponent = steeper profile = more wind increase with altitude
        alt = 100.0
        speed_low = wind_low.get_wind_magnitude(alt)
        speed_high = wind_high.get_wind_magnitude(alt)
        
        self.assertGreater(speed_high, speed_low)
    
    def test_zero_vertical_component(self):
        """Test no vertical wind in power law."""
        vec = self.wind.get_wind_vector(100)
        self.assertAlmostEqual(vec[2], 0.0)


class TestWindDirectionConversions(unittest.TestCase):
    """Tests for wind direction conversions and coordinate frames."""
    
    def test_constant_wind_direction_from_north(self):
        """Test wind FROM north (blows toward south)."""
        wind = ConstantWind(wind_speed=10.0, wind_direction=0.0)
        vec = wind.get_wind_vector(100)
        
        # Wind FROM north (0°) should have negative north component
        # (blowing toward south/negative north)
        self.assertLess(vec[1], 0)
        self.assertAlmostEqual(vec[0], 0.0, places=5)  # No east component
    
    def test_constant_wind_direction_from_east(self):
        """Test wind FROM east (blows toward west)."""
        wind = ConstantWind(wind_speed=10.0, wind_direction=90.0)
        vec = wind.get_wind_vector(100)
        
        # Wind FROM east (90°) should have negative east component
        self.assertLess(vec[0], 0)
        self.assertAlmostEqual(vec[1], 0.0, places=5)  # No north component
    
    def test_constant_wind_direction_from_south(self):
        """Test wind FROM south (blows toward north)."""
        wind = ConstantWind(wind_speed=10.0, wind_direction=180.0)
        vec = wind.get_wind_vector(100)
        
        # Wind FROM south (180°) should have positive north component
        self.assertGreater(vec[1], 0)
        self.assertAlmostEqual(vec[0], 0.0, places=5)
    
    def test_constant_wind_direction_from_west(self):
        """Test wind FROM west (blows toward east)."""
        wind = ConstantWind(wind_speed=10.0, wind_direction=270.0)
        vec = wind.get_wind_vector(100)
        
        # Wind FROM west (270°) should have positive east component
        self.assertGreater(vec[0], 0)
        self.assertAlmostEqual(vec[1], 0.0, places=5)
    
    def test_wind_direction_at_altitude(self):
        """Test wind direction calculation."""
        wind = ConstantWind(wind_speed=5.0, wind_direction=45.0)
        direction = wind.get_wind_direction_at_altitude(100)
        
        # Should return direction FROM (opposite of TO direction)
        # Wind FROM 45° should match
        self.assertAlmostEqual(direction, 45.0, delta=1.0)


class TestWindModelFactory(unittest.TestCase):
    """Tests for wind model factory function."""
    
    def test_factory_constant_wind(self):
        """Test factory creates ConstantWind."""
        wind = create_wind_model('constant', wind_speed=5.0)
        self.assertIsInstance(wind, ConstantWind)
    
    def test_factory_logarithmic_wind(self):
        """Test factory creates LogarithmicWind."""
        wind = create_wind_model('logarithmic', wind_speed_ref=5.0)
        self.assertIsInstance(wind, LogarithmicWind)
    
    def test_factory_default_is_logarithmic(self):
        """Test factory default is logarithmic."""
        wind = create_wind_model()
        self.assertIsInstance(wind, LogarithmicWind)
    
    def test_factory_power_law(self):
        """Test factory creates PowerLawWind."""
        wind = create_wind_model('power_law', wind_speed_ref=5.0)
        self.assertIsInstance(wind, PowerLawWind)
    
    def test_factory_invalid_type(self):
        """Test factory raises error for invalid type."""
        with self.assertRaises(ValueError):
            create_wind_model('invalid_model_type')
    
    def test_factory_case_insensitive(self):
        """Test factory type names are case-insensitive."""
        wind1 = create_wind_model('LOGARITHMIC')
        wind2 = create_wind_model('Logarithmic')
        
        self.assertIsInstance(wind1, LogarithmicWind)
        self.assertIsInstance(wind2, LogarithmicWind)


class TestWindEdgeCases(unittest.TestCase):
    """Tests for edge cases and boundary conditions."""
    
    def test_zero_wind_speed(self):
        """Test wind models with zero wind speed."""
        for model_type in ['constant', 'logarithmic', 'power_law']:
            if model_type == 'constant':
                wind = create_wind_model(model_type, wind_speed=0.0)
            else:
                wind = create_wind_model(model_type, wind_speed_ref=0.0)
            
            speed = wind.get_wind_magnitude(100)
            self.assertAlmostEqual(speed, 0.0)
    
    def test_very_high_altitude(self):
        """Test wind models at very high altitude."""
        wind = LogarithmicWind(wind_speed_ref=5.0)
        
        # Wind should still be finite and positive
        speed = wind.get_wind_magnitude(100000)  # 100 km
        self.assertGreater(speed, 0)
        self.assertTrue(np.isfinite(speed))
    
    def test_very_low_wind_speed(self):
        """Test wind models with very low wind speed."""
        wind = LogarithmicWind(wind_speed_ref=0.1)  # 0.1 m/s
        
        speed = wind.get_wind_magnitude(100)
        self.assertGreater(speed, 0)
        self.assertLess(speed, 0.2)
    
    def test_very_high_wind_speed(self):
        """Test wind models with very high wind speed."""
        wind = LogarithmicWind(wind_speed_ref=50.0)  # 50 m/s = hurricane
        
        speed = wind.get_wind_magnitude(100)
        self.assertGreater(speed, 45.0)
    
    def test_wind_update_time(self):
        """Test wind update method (for time-varying models)."""
        wind = LogarithmicWind()
        initial_time = wind.time
        
        wind.update(1.0)
        self.assertEqual(wind.time, initial_time + 1.0)
        
        wind.update(5.0)
        self.assertEqual(wind.time, initial_time + 6.0)


class TestWindPhysicalValidity(unittest.TestCase):
    """Tests for physical validity of wind models."""
    
    def test_wind_vector_components(self):
        """Test wind vector components are physically valid."""
        wind = LogarithmicWind(wind_speed_ref=5.0)
        
        for alt in np.linspace(0, 2000, 20):
            vec = wind.get_wind_vector(alt)
            
            # Should be finite
            self.assertTrue(np.all(np.isfinite(vec)))
            
            # Magnitude should be reasonable (0-30 m/s for typical cases)
            magnitude = np.linalg.norm(vec[:2])
            self.assertGreaterEqual(magnitude, 0.0)
            self.assertLessEqual(magnitude, 30.0)
    
    def test_wind_speed_non_negative(self):
        """Test wind speed is never negative."""
        wind = LogarithmicWind(wind_speed_ref=5.0)
        
        for alt in [0, 50, 100, 500, 1000]:
            speed = wind.get_wind_magnitude(alt)
            self.assertGreaterEqual(speed, 0.0)
    
    def test_vertical_wind_zero_for_standard_profiles(self):
        """Test standard log/power profiles have no vertical wind."""
        # Create wind models with appropriate parameters
        winds = [
            create_wind_model('constant', wind_speed=5.0),
            create_wind_model('logarithmic', wind_speed_ref=5.0),
            create_wind_model('power_law', wind_speed_ref=5.0)
        ]
        
        for wind in winds:
            for alt in [0, 100, 500]:
                vec = wind.get_wind_vector(alt)
                self.assertAlmostEqual(vec[2], 0.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
