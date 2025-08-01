import unittest
import numpy as np
from datetime import datetime, timezone
from src.models.clock import Clock

class TestClock(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada prueba"""
        self.clock = Clock()
        self.precision = 6

    def test_initialization(self):
        """Prueba la inicialización correcta"""
        self.assertIsNotNone(self.clock.Delta_UT1)
        self.assertIsInstance(self.clock.time_vector, np.ndarray)
        self.assertEqual(len(self.clock.time_vector), 6)  # [año,mes,día,hora,min,seg]

    def test_time_utc(self):
        """Prueba obtención de tiempo UTC"""
        time_vector = self.clock.time_utc()
        current_time = datetime.now(timezone.utc)
        
        self.assertEqual(time_vector[0], current_time.year)
        self.assertEqual(time_vector[1], current_time.month)
        self.assertEqual(time_vector[2], current_time.day)

    def test_julian_day(self):
        """Prueba cálculo del día juliano"""
        # Test con fecha conocida: 1 enero 2000 12:00:00 UT1
        test_time = np.array([2000, 1, 1, 12, 0, 0])
        j_day = self.clock.julian_day(test_time)
        
        # J2000.0 = 2451545.0
        self.assertAlmostEqual(j_day, 2451545.0, places=self.precision)

    def test_gmst_calculation(self):
        """Prueba cálculo de GMST"""
        # Test con J2000.0
        j_day = 2451545.0
        
        # Prueba en radianes
        gmst_rad = self.clock.gmst(j_day, 1)
        self.assertGreaterEqual(gmst_rad, 0)
        self.assertLess(gmst_rad, 2*np.pi)
        
        # Prueba en grados
        gmst_deg = self.clock.gmst(j_day, 2)
        self.assertGreaterEqual(gmst_deg, 0)
        self.assertLess(gmst_deg, 360)

    def test_gmst_consistency(self):
        """Prueba consistencia entre GMST en radianes y grados"""
        j_day = self.clock.j_day
        
        gmst_rad = self.clock.gmst(j_day, 1)
        gmst_deg = self.clock.gmst(j_day, 2)
        
        # Convertir grados a radianes y comparar
        gmst_rad_from_deg = gmst_deg * np.pi/180
        self.assertAlmostEqual(gmst_rad, gmst_rad_from_deg, places=self.precision)

    def test_delta_ut1_effect(self):
        """Prueba el efecto de Delta_UT1"""
        original_delta = self.clock.Delta_UT1
        self.clock.Delta_UT1 = 0.5  # Cambiar offset
        
        time_vector = self.clock.time_utc()
        self.assertAlmostEqual(time_vector[5] % 1, 0.5, places=1)
        
        # Restaurar valor original
        self.clock.Delta_UT1 = original_delta

if __name__ == '__main__':
    unittest.main()