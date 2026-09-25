import unittest
import numpy as np
from src.models.aerodynamics import Aerodynamics


class TestAerodynamics(unittest.TestCase):
    def setUp(self):
        # Use simple Aerodynamics with test coefficients
        self.cd = 0.45
        self.cl = 0.1
        self.aero = Aerodynamics(
            cd=self.cd,
            cl=self.cl,
            center_of_pressure_x=0.5,
            stability_margin=1.0,
            reference_area=0.01
        )

    def test_initialization(self):
        self.assertAlmostEqual(self.aero.cd, self.cd)
        self.assertAlmostEqual(self.aero.cl, self.cl)
        self.assertEqual(self.aero._reference_area, 0.01)

    def test_get_coefficients(self):
        cd, cl = self.aero.get_coefficients()
        self.assertAlmostEqual(cd, self.cd)
        self.assertAlmostEqual(cl, self.cl)

    def test_center_of_pressure(self):
        xcp = self.aero.get_center_of_pressure()
        self.assertTrue(isinstance(xcp, np.ndarray))
        self.assertEqual(xcp.shape, (3,))
        self.assertAlmostEqual(xcp[0], 0.5)
        self.assertAlmostEqual(xcp[1], 0.0)
        self.assertAlmostEqual(xcp[2], 0.0)

    def test_stability_margin(self):
        margin = self.aero.get_stability_margin()
        self.assertTrue(isinstance(margin, float))
        self.assertAlmostEqual(margin, 1.0)

    def test_update(self):
        # Update should store the values but not change coefficients
        self.aero.update(mach=0.8, angle_attack=10.0, height=500.0, density=0.5)
        self.assertAlmostEqual(self.aero.mach, 0.8)
        self.assertAlmostEqual(self.aero.alpha, 10.0)
        self.assertAlmostEqual(self.aero.height, 500.0)
        # Coefficients should remain unchanged
        cd, cl = self.aero.get_coefficients()
        self.assertAlmostEqual(cd, self.cd)
        self.assertAlmostEqual(cl, self.cl)

    def test_get_aerodynamic_forces(self):
        dynamic_pressure = 1000.0
        forces = self.aero.get_aerodynamic_forces(dynamic_pressure)
        
        self.assertIn('drag', forces)
        self.assertIn('lift', forces)
        self.assertIn('cd', forces)
        self.assertIn('cl', forces)
        self.assertIn('cp_position', forces)
        self.assertIn('stability_margin', forces)
        
        # Drag force = cd * q * ref_area
        expected_drag = self.cd * dynamic_pressure * 0.01
        self.assertAlmostEqual(forces['drag'], expected_drag)
        
        # Lift force = cl * q * ref_area
        expected_lift = self.cl * dynamic_pressure * 0.01
        self.assertAlmostEqual(forces['lift'], expected_lift)

    def test_from_rocket_config(self):
        # Test factory method
        rocket_config = {
            'aerodynamics': {
                'cd': 0.5,
                'cl': 0.2
            },
            'reference_area': 0.02
        }
        aero = Aerodynamics.from_rocket_config(rocket_config)
        cd, cl = aero.get_coefficients()
        self.assertAlmostEqual(cd, 0.5)
        self.assertAlmostEqual(cl, 0.2)
        self.assertAlmostEqual(aero._reference_area, 0.02)

    def test_setters(self):
        # Test setter methods
        self.aero.set_coefficients(0.6, 0.15)
        cd, cl = self.aero.get_coefficients()
        self.assertAlmostEqual(cd, 0.6)
        self.assertAlmostEqual(cl, 0.15)
        
        self.aero.set_stability_margin(2.0)
        self.assertAlmostEqual(self.aero.get_stability_margin(), 2.0)
        
        self.aero.set_reference_area(0.02)
        self.assertAlmostEqual(self.aero._reference_area, 0.02)
        
        self.aero.set_center_of_pressure(0.6, 0.1, 0.0)
        xcp = self.aero.get_center_of_pressure()
        self.assertAlmostEqual(xcp[0], 0.6)
        self.assertAlmostEqual(xcp[1], 0.1)
        self.assertAlmostEqual(xcp[2], 0.0)


if __name__ == '__main__':
    unittest.main()
