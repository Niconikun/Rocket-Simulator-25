"""
Unit Tests for Units Module

Tests:
- Unit conversion functions
- Unit table consistency
- Common conversions (m to ft, N to lbf, etc.)
"""

import unittest
from src.utils.units import convert, unitTable, unitLabels


class TestUnits(unittest.TestCase):
    """Test suite for units module"""

    def test_unit_labels_exist(self):
        """Test that unit labels dictionary exists and has expected keys"""
        self.assertIn('m', unitLabels)
        self.assertIn('kg', unitLabels)
        self.assertIn('N', unitLabels)
        self.assertEqual(unitLabels['m'], 'Length')
        self.assertEqual(unitLabels['kg'], 'Mass')

    def test_unit_table_exist(self):
        """Test that unit table exists and has entries"""
        self.assertGreater(len(unitTable), 0)

    def test_convert_meters_to_feet(self):
        """Test conversion from meters to feet"""
        # 1 meter = 3.28 feet
        result = convert(1.0, 'm', 'ft')
        self.assertAlmostEqual(result, 3.28, places=2)
        
        # 10 meters = 32.8 feet
        result = convert(10.0, 'm', 'ft')
        self.assertAlmostEqual(result, 32.8, places=2)

    def test_convert_feet_to_meters(self):
        """Test conversion from feet to meters"""
        # 3.28 feet = 1 meter
        result = convert(3.28, 'ft', 'm')
        self.assertAlmostEqual(result, 1.0, places=2)

    def test_convert_newtons_to_lbf(self):
        """Test conversion from Newtons to pound-force"""
        # 1 N = 0.2248 lbf
        result = convert(1.0, 'N', 'lbf')
        self.assertAlmostEqual(result, 0.2248, places=4)

    def test_convert_pa_to_psi(self):
        """Test conversion from Pascal to PSI"""
        # 1 Pa = 1/6895 psi
        result = convert(1.0, 'Pa', 'psi')
        self.assertAlmostEqual(result, 1/6895, places=6)
        
        # 6895 Pa = 1 psi
        result = convert(6895.0, 'Pa', 'psi')
        self.assertAlmostEqual(result, 1.0, places=2)

    def test_convert_mps_to_ftps(self):
        """Test conversion from m/s to ft/s"""
        # 1 m/s = 3.28 ft/s
        result = convert(1.0, 'm/s', 'ft/s')
        self.assertAlmostEqual(result, 3.28, places=2)

    def test_convert_same_units(self):
        """Test conversion with same from and to units"""
        result = convert(100.0, 'm', 'm')
        self.assertEqual(result, 100.0)
        
        result = convert(50.0, 'kg', 'kg')
        self.assertEqual(result, 50.0)

    def test_convert_meters_to_mm(self):
        """Test conversion from meters to millimeters"""
        # 1 m = 1000 mm
        result = convert(1.0, 'm', 'mm')
        self.assertAlmostEqual(result, 1000.0, places=2)

    def test_convert_m3_to_ft3(self):
        """Test conversion from cubic meters to cubic feet"""
        # 1 m^3 = 3.28^3 ft^3 ≈ 35.29 ft^3
        result = convert(1.0, 'm^3', 'ft^3')
        expected = 3.28 ** 3
        self.assertAlmostEqual(result, expected, places=2)

    def test_convert_unknown_unit_raises_error(self):
        """Test that converting with unknown units raises an error"""
        with self.assertRaises(Exception):
            convert(1.0, 'unknown', 'm')
        
        with self.assertRaises(Exception):
            convert(1.0, 'm', 'unknown')


if __name__ == '__main__':
    unittest.main()
