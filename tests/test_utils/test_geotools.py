import unittest
import numpy as np
from src.utils.geotools import GeoTools as Geo

class TestGeoTools(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para las pruebas"""
        self.precision = 6  # Precisión decimal para comparaciones
        # Coordenadas de prueba (Concepción, Chile)
        self.test_coord = [-36.8282, -73.0503, 0]  # [lat, long, alt]
        
    def test_enu2ecef_conversion(self):
        """Prueba la conversión de coordenadas ENU a ECEF"""
        r_enu = np.array([100.0, 200.0, 300.0])  # metros
        r_ecef = Geo.enu2ecef(self.test_coord[:2], r_enu)
        
        # Convertir de vuelta a ENU
        r_enu_back = Geo.ecef2enu(self.test_coord[:2], r_ecef)
        
        # Verificar que la conversión ida y vuelta preserva las coordenadas
        np.testing.assert_array_almost_equal(r_enu, r_enu_back, self.precision)

    def test_geo2ecef_conversion(self):
        """Prueba la conversión de coordenadas geodésicas a ECEF"""
        r_ecef = Geo.geo2ecef(self.test_coord)
        
        # Convertir de vuelta a geodésicas
        coord_back = Geo.ecef2geo(r_ecef)
        
        # Verificar que la conversión ida y vuelta preserva las coordenadas
        np.testing.assert_array_almost_equal(self.test_coord, coord_back, self.precision)

    def test_rotation_matrix(self):
        """Prueba el cálculo de la matriz de rotación"""
        lat, long = self.test_coord[:2]
        R = Geo.calculate_rotation_matrix(lat, long)
        
        # Verificar que es una matriz ortogonal (R·R^T = I)
        I = np.eye(3)
        R_orthogonal = R.dot(R.T)
        np.testing.assert_array_almost_equal(R_orthogonal, I, self.precision)
        
        # Verificar determinante = 1 (preserva orientación)
        det = np.linalg.det(R)
        self.assertAlmostEqual(det, 1.0, places=self.precision)

    def test_geodetic_radius(self):
        """Prueba el cálculo del radio geodésico"""
        lat = self.test_coord[0]
        N = Geo.calculate_geodetic_radius(lat)
        
        # Verificar que está entre el radio polar y ecuatorial
        self.assertGreater(N, Geo.b)
        self.assertLess(N, Geo.a)

    def test_constants(self):
        """Prueba las constantes del elipsoide WGS84"""
        # Verificar relación entre parámetros
        f = (Geo.a - Geo.b) / Geo.a
        self.assertAlmostEqual(f, Geo.f, places=self.precision)
        
        # Verificar primera excentricidad
        e2 = (Geo.a**2 - Geo.b**2) / Geo.a**2
        self.assertAlmostEqual(e2, Geo.e2, places=self.precision)
        
        # Verificar segunda excentricidad
        eps2 = (Geo.a**2 - Geo.b**2) / Geo.b**2
        self.assertAlmostEqual(eps2, Geo.eps2, places=self.precision)

    def test_coordinate_ranges(self):
        """Prueba rangos válidos de coordenadas"""
        # Prueba con coordenadas extremas
        test_coords = [
            [90.0, 180.0, 1000.0],    # Polo Norte
            [-90.0, -180.0, -100.0],  # Polo Sur
            [0.0, 0.0, 0.0]           # Origen
        ]
        
        for coord in test_coords:
            r_ecef = Geo.geo2ecef(coord)
            coord_back = Geo.ecef2geo(r_ecef)
            # Verificar que las coordenadas se mantienen en rangos válidos
            self.assertGreaterEqual(coord_back[0], -90.0)
            self.assertLessEqual(coord_back[0], 90.0)
            self.assertGreaterEqual(coord_back[1], -180.0)
            self.assertLessEqual(coord_back[1], 180.0)

if __name__ == '__main__':
    unittest.main()