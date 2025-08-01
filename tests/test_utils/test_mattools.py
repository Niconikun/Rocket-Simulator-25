import unittest
import numpy as np
from src.utils.mattools import MatTools as Mat

class TestMatTools(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para las pruebas"""
        self.precision = 6  # Precisión decimal para comparaciones

    def test_quaternion_normalization(self):
        """Prueba la normalización de cuaterniones"""
        # Cuaternión no normalizado
        q = np.array([1.0, 1.0, 1.0, 1.0])
        q_norm = Mat.normalise(q)  # Cambio a método de clase
        
        magnitude = np.linalg.norm(q_norm)
        self.assertAlmostEqual(magnitude, 1.0, places=self.precision)

    def test_quaternion_multiplication(self):
        """Prueba la multiplicación de cuaterniones"""
        q1 = np.array([0.0, 0.0, np.sin(np.pi/4), np.cos(np.pi/4)])
        q2 = np.array([0.0, 0.0, np.sin(np.pi/4), np.cos(np.pi/4)])
        
        q_result = Mat.hamilton(q1, q2)  # Cambio a método de clase
        
        expected = np.array([0.0, 0.0, 1.0, 0.0])
        np.testing.assert_array_almost_equal(q_result, expected, self.precision)

    def test_quaternion_rotate_vector(self):
        """Prueba la rotación de vectores usando cuaterniones"""
        v = np.array([1.0, 0.0, 0.0])
        q = np.array([0.0, 0.0, np.sin(np.pi/4), np.cos(np.pi/4)])
        
        v_rotated = Mat.q_rot(v, q, 0)  # Cambio a método de clase
        
        expected = np.array([0.0, 1.0, 0.0])
        np.testing.assert_array_almost_equal(v_rotated, expected, self.precision)

    def test_skew_matrices(self):
        """Prueba la generación de matrices antisimétricas"""
        v = np.array([1.0, 2.0, 3.0])
        
        # Prueba matriz 3x3
        skew3 = Mat.skew3(v)
        self.assertEqual(skew3.shape, (3, 3))
        self.assertTrue(np.allclose(-skew3, skew3.T))
        
        # Prueba matriz 4x4
        skew4 = Mat.skew4(v)
        self.assertEqual(skew4.shape, (4, 4))
        self.assertTrue(np.allclose(-skew4, skew4.T))

    def test_dcm_conversions(self):
        """Prueba conversiones DCM"""
        # Rotación de 90° en Z
        q = np.array([0.0, 0.0, np.sin(np.pi/4), np.cos(np.pi/4)])
        
        # Cuaternión a DCM
        dcm = Mat.quat2mat(q)
        
        # DCM a cuaternión
        q_back = Mat.mat2quat(dcm)
        
        # Verificar que la conversión ida y vuelta preserva la rotación
        np.testing.assert_array_almost_equal(q, q_back, self.precision)

if __name__ == '__main__':
    unittest.main()