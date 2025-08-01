import unittest
import numpy as np
from src.models.planet import Planet

class TestPlanet(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada prueba"""
        self.gmst_0 = 0.0  # [rad] GMST inicial
        self.planet = Planet(self.gmst_0)
        self.precision = 6

    def test_initialization(self):
        """Prueba la inicialización correcta"""
        self.assertEqual(self.planet.gmst, self.gmst_0)
        self.assertAlmostEqual(self.planet.rotation_speed, 7.2722e-5, places=9)  # [rad/s]
        self.assertEqual(len(self.planet.hist_gmst), 0)

    def test_gmst_update(self):
        """Prueba la actualización del GMST"""
        dt = 3600.0  # 1 hora [s]
        expected_rotation = self.planet.rotation_speed * dt
        
        self.planet.update(dt)
        
        self.assertAlmostEqual(self.planet.gmst, expected_rotation, places=self.precision)

    def test_gmst_limits(self):
        """Prueba que GMST se mantiene entre 0 y 2π"""
        dt = 86400.0  # 24 horas [s]
        self.planet.update(dt)
        
        self.assertGreaterEqual(self.planet.gmst, 0.0)
        self.assertLess(self.planet.gmst, 2*np.pi)

    def test_data_saving(self):
        """Prueba el guardado de datos históricos"""
        dt = 3600.0  # [s]
        steps = 5
        
        for _ in range(steps):
            self.planet.update(dt)
            self.planet.save_data()
        
        self.assertEqual(len(self.planet.hist_gmst), steps)
        self.assertTrue(all(0 <= x < 2*np.pi for x in self.planet.hist_gmst))

if __name__ == '__main__':
    unittest.main()