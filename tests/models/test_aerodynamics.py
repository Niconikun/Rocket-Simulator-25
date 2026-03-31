import unittest
import numpy as np
from src.models.aerodynamics import EnhancedAerodynamics


# Adaptación para EnhancedAerodynamics
class DummyAtmosphere:
    def give_dens(self, height):
        return 1.225
    def give_temp(self, height):
        return 288.15
    def give_v_sonic(self, height):
        return 340.0


# DummyRocketData adaptado a la interfaz real requerida por EnhancedAerodynamics

class DummyRocketData:
    _data = {
        'reference_area': 0.01,
        'fuselage': {
            'diameter': 100,
            'length': 1000
        },
        'geometry': {
            'total length': 1000,
            'length nosecone fins': 200
        },
        'nosecone': {
            'length': 200,
            'diameter': 100,
            'shape': 'conical'
        },
        'fins': {
            'number': 4,
            'root chord': 100,
            'chord_root': 100,
            'chord_tip': 80,
            'mid_chord': 90,
            'span': 50,
            'thickness': 5,
            'N_fins': 4
        },
        'rear_section': {
            'diameter': 100
        }
    }

    def __getitem__(self, key):
        return self._data[key]


class TestEnhancedAerodynamics(unittest.TestCase):
    def setUp(self):
        self.mach = 0.5
        self.angle_attack = 5.0
        self.height = 100.0
        self.atmosphere = DummyAtmosphere()
        self.rocket_data = DummyRocketData()
        # Adaptar mass_props con los campos requeridos
        self.mass_props = {
            'CoM_before_burn': {'x': 0.5},
            'CoM_after_burn': {'x': 0.6}
        }
        self.aero = EnhancedAerodynamics(
            self.mach,
            self.angle_attack,
            self.height,
            self.atmosphere,
            self.rocket_data,
            self.mass_props
        )


    def test_initialization(self):
        self.assertAlmostEqual(self.aero.mach, self.mach)
        self.assertAlmostEqual(self.aero.alpha, self.angle_attack)
        self.assertAlmostEqual(self.aero.height, self.height)
        self.assertEqual(self.aero.rho, 1.225)
        self.assertEqual(self.aero.temp, 288.15)

    def test_drag_coefficient(self):
        cd = self.aero.cd
        self.assertTrue(isinstance(cd, float))
        self.assertGreater(cd, 0)

    def test_lift_coefficient(self):
        cl = self.aero.cl
        self.assertTrue(isinstance(cl, float))

    def test_pressure_center(self):
        xcp = self.aero.xcp
        # Debe ser un np.ndarray de 3 elementos, primer valor float
        self.assertTrue(isinstance(xcp, np.ndarray))
        self.assertEqual(xcp.shape, (3,))
        self.assertTrue(isinstance(xcp[0], float))

    def test_stability_margin(self):
        margin = self.aero.stability_margin
        self.assertTrue(isinstance(margin, float))

