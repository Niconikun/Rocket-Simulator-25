import unittest
import numpy as np
from src.models.gravitational import g_accel, g_torque
from src.utils.mattools import MatTools as Mat

class TestGravitational(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada prueba"""
        self.precision = 6
        
        # Valores típicos para pruebas
        self.r_eci = np.array([6378137.0, 0.0, 0.0])  # Radio terrestre en ecuador
        # Momentos de inercia muy diferentes para generar torque significativo
        self.inertia = np.array([1000.0, 2000.0, 3000.0])  # kg·m²
        # Cuaternión con rotación de 45° en Y para generar torque
        self.q_ecef_body = np.array([0.0, np.sin(np.pi/4), 0.0, np.cos(np.pi/4)])

    def test_g_accel_magnitude(self):
        """Prueba magnitud de aceleración gravitacional"""
        g = g_accel(self.r_eci)
        g_mag = np.linalg.norm(g)
        
        # La aceleración a nivel del mar varía entre 9.78 y 9.83 m/s²
        self.assertGreaterEqual(g_mag, 9.78)
        self.assertLessEqual(g_mag, 9.83)

    def test_g_accel_direction(self):
        """Prueba dirección de aceleración gravitacional"""
        # Probar varios puntos
        test_points = [
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 1.0])
        ]
        
        for r in test_points:
            g = g_accel(r)
            r_unit = Mat.normalise(r)
            g_unit = Mat.normalise(g)
            
            # Dirección debe ser opuesta al vector posición
            np.testing.assert_array_almost_equal(-r_unit, g_unit, decimal=self.precision)

    def test_g_torque_zero_altitude(self):
        """Prueba torque gravitacional a nivel del mar"""
        r_ecef = np.array([6378137.0, 0.0, 0.0])  # Radio terrestre
        torque = g_torque(r_ecef, self.inertia, self.q_ecef_body)
        
        # Torque debe ser pequeño cerca de la superficie
        self.assertLess(np.linalg.norm(torque), 1e-3)

    def test_g_torque_symmetry(self):
        """Prueba simetría del torque gravitacional"""
        r_ecef = np.array([7378137.0, 0.0, 0.0])  # 1000 km de altitud
        
        # Torque con orientación normal
        torque1 = g_torque(r_ecef, self.inertia, self.q_ecef_body)
        
        # Torque con orientación invertida
        q_inv = np.array([0.0, 0.0, 1.0, 0.0])  # Rotación 180° en Z
        torque2 = g_torque(r_ecef, self.inertia, q_inv)
        
        # Los torques deben tener igual magnitud pero signo opuesto
        np.testing.assert_array_almost_equal(torque1, -torque2, decimal=self.precision)

    def test_g_torque_altitude_effect(self):
        """Prueba efecto de la altitud en el torque gravitacional"""
        # Prueba a diferentes altitudes
        altitudes = [0, 1000e3, 10000e3]  # 0, 1000km, 10000km
        torques = []
        
        # Usar momentos de inercia más grandes para esta prueba
        test_inertia = np.array([10000.0, 20000.0, 30000.0])  # kg·m²
        
        for alt in altitudes:
            r_ecef = np.array([6378137.0 + alt, 0.0, 0.0])
            torque = g_torque(r_ecef, test_inertia, self.q_ecef_body)
            torque_mag = np.linalg.norm(torque)
            torques.append(torque_mag)
            print(f"Altitud: {alt/1000:.1f} km, Torque: {torque_mag:.2e} N·m")
        
        # Verificar que los torques no son cero
        self.assertGreater(torques[0], 0.0, "El torque no debería ser cero")
        
        # Verificar que cada torque es menor que el anterior
        for i in range(len(torques)-1):
            self.assertGreater(torques[i], torques[i+1], 
                f"El torque a {altitudes[i]/1000:.1f}km ({torques[i]:.2e}) debería ser mayor "
                f"que a {altitudes[i+1]/1000:.1f}km ({torques[i+1]:.2e})")

if __name__ == '__main__':
    unittest.main()