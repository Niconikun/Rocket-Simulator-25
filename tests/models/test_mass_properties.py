"""
Unit Tests for MassProperties Module

Tests:
- MassProperties initialization
- Mass interpolation during burn
- Center of mass interpolation
- Inertia interpolation
- Edge cases (0% and 100% burn)
"""

import unittest
import numpy as np
from src.models.mass_properties import MassProperties
from src.utils.simulation_errors import InputValidationError


class TestMassProperties(unittest.TestCase):
    """Test suite for MassProperties class"""

    def test_initialization(self):
        """Test MassProperties initialization with valid parameters"""
        mass_props = MassProperties(
            mass_before=10.0,
            mass_after=7.0,
            cm_before=np.array([0.5, 0.0, 0.0]),
            cm_after=np.array([0.6, 0.0, 0.0]),
            inertia_before=np.array([0.1, 0.1, 0.05]),
            inertia_after=np.array([0.08, 0.08, 0.04])
        )
        
        self.assertEqual(mass_props.mass_before, 10.0)
        self.assertEqual(mass_props.mass_after, 7.0)
        self.assertTrue(np.allclose(mass_props.cm_before, np.array([0.5, 0.0, 0.0])))
        self.assertTrue(np.allclose(mass_props.cm_after, np.array([0.6, 0.0, 0.0])))

    def test_initialization_with_invalid_mass(self):
        """Test that initialization raises error for invalid mass values"""
        with self.assertRaises(InputValidationError):
            MassProperties(
                mass_before=-1.0,
                mass_after=7.0,
                cm_before=np.array([0.5, 0.0, 0.0]),
                cm_after=np.array([0.6, 0.0, 0.0]),
                inertia_before=np.array([0.1, 0.1, 0.05]),
                inertia_after=np.array([0.08, 0.08, 0.04])
            )
        
        with self.assertRaises(InputValidationError):
            MassProperties(
                mass_before=10.0,
                mass_after=15.0,  # mass_after > mass_before
                cm_before=np.array([0.5, 0.0, 0.0]),
                cm_after=np.array([0.6, 0.0, 0.0]),
                inertia_before=np.array([0.1, 0.1, 0.05]),
                inertia_after=np.array([0.08, 0.08, 0.04])
            )

    def test_mass_interpolation_at_zero_burn(self):
        """Test mass at 0% burn fraction (beginning)"""
        mass_props = MassProperties(
            mass_before=10.0,
            mass_after=7.0,
            cm_before=np.array([0.5, 0.0, 0.0]),
            cm_after=np.array([0.6, 0.0, 0.0]),
            inertia_before=np.array([0.1, 0.1, 0.05]),
            inertia_after=np.array([0.08, 0.08, 0.04])
        )
        
        mass = mass_props.get_mass(0.0)
        self.assertAlmostEqual(mass, 10.0, places=6)

    def test_mass_interpolation_at_full_burn(self):
        """Test mass at 100% burn fraction (end)"""
        mass_props = MassProperties(
            mass_before=10.0,
            mass_after=7.0,
            cm_before=np.array([0.5, 0.0, 0.0]),
            cm_after=np.array([0.6, 0.0, 0.0]),
            inertia_before=np.array([0.1, 0.1, 0.05]),
            inertia_after=np.array([0.08, 0.08, 0.04])
        )
        
        mass = mass_props.get_mass(1.0)
        self.assertAlmostEqual(mass, 7.0, places=6)

    def test_mass_interpolation_at_mid_burn(self):
        """Test mass at 50% burn fraction"""
        mass_props = MassProperties(
            mass_before=10.0,
            mass_after=7.0,
            cm_before=np.array([0.5, 0.0, 0.0]),
            cm_after=np.array([0.6, 0.0, 0.0]),
            inertia_before=np.array([0.1, 0.1, 0.05]),
            inertia_after=np.array([0.08, 0.08, 0.04])
        )
        
        mass = mass_props.get_mass(0.5)
        expected = 8.5  # Linear interpolation
        self.assertAlmostEqual(mass, expected, places=6)

    def test_center_of_mass_interpolation(self):
        """Test center of mass interpolation"""
        mass_props = MassProperties(
            mass_before=10.0,
            mass_after=7.0,
            cm_before=np.array([0.5, 0.0, 0.0]),
            cm_after=np.array([0.6, 0.0, 0.0]),
            inertia_before=np.array([0.1, 0.1, 0.05]),
            inertia_after=np.array([0.08, 0.08, 0.04])
        )
        
        # At 0% burn
        com_0 = mass_props.get_center_of_mass(0.0)
        self.assertTrue(np.allclose(com_0, np.array([0.5, 0.0, 0.0])))
        
        # At 100% burn
        com_1 = mass_props.get_center_of_mass(1.0)
        self.assertTrue(np.allclose(com_1, np.array([0.6, 0.0, 0.0])))
        
        # At 50% burn
        com_05 = mass_props.get_center_of_mass(0.5)
        # Should be weighted average
        self.assertTrue(np.allclose(com_05, np.array([0.55, 0.0, 0.0]), atol=0.01))

    def test_inertia_interpolation(self):
        """Test inertia interpolation"""
        mass_props = MassProperties(
            mass_before=10.0,
            mass_after=7.0,
            cm_before=np.array([0.5, 0.0, 0.0]),
            cm_after=np.array([0.6, 0.0, 0.0]),
            inertia_before=np.array([0.1, 0.1, 0.05]),
            inertia_after=np.array([0.08, 0.08, 0.04])
        )
        
        # At 0% burn
        inertia_0 = mass_props.get_inertia(0.0)
        self.assertTrue(np.allclose(inertia_0, np.array([0.1, 0.1, 0.05])))
        
        # At 100% burn
        inertia_1 = mass_props.get_inertia(1.0)
        self.assertTrue(np.allclose(inertia_1, np.array([0.08, 0.08, 0.04])))

    def test_propellent_mass_calculation(self):
        """Test propellant mass calculation"""
        mass_props = MassProperties(
            mass_before=10.0,
            mass_after=7.0,
            cm_before=np.array([0.5, 0.0, 0.0]),
            cm_after=np.array([0.6, 0.0, 0.0]),
            inertia_before=np.array([0.1, 0.1, 0.05]),
            inertia_after=np.array([0.08, 0.08, 0.04])
        )
        
        propellant_mass = mass_props.propellant_mass
        self.assertAlmostEqual(propellant_mass, 3.0, places=6)


if __name__ == '__main__':
    unittest.main()
