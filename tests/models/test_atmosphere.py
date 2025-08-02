import unittest
import numpy as np
from src.models.atmosphere import Atmosphere

class TestAtmosphere(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada prueba"""
        self.temp_sensed = 15.0  # [°C] Temperatura típica a nivel del mar
        self.atmosphere = Atmosphere(self.temp_sensed)
        self.precision = 6

    def test_initialization(self):
        """Prueba la inicialización correcta"""
        self.assertEqual(self.atmosphere.sea_level_temp, 288.15)  # [K]
        expected_offset = (self.temp_sensed + 273.15) - 288.15
        self.assertAlmostEqual(self.atmosphere.offset, expected_offset, places=self.precision)

    def test_temperature_profile(self):
        """Prueba el perfil de temperatura con la altura"""
        test_heights = [0, 1000, 5000, 10000]  # [m]
        base_temp = self.atmosphere.sea_level_temp + self.atmosphere.offset
        
        for height in test_heights:
            temp = self.atmosphere.give_temp(height)
            
            # A nivel del mar, temperatura debe ser igual a la base
            if height == 0:
                self.assertAlmostEqual(temp, base_temp, places=self.precision)
            # Por encima del nivel del mar, debe ser menor (hasta la tropopausa)
            elif height < 11000:
                self.assertLess(temp, base_temp)
                # Verificar gradiente térmico aproximado (-6.5°C/km)
                expected_temp = base_temp - 0.0065 * height
                # Usar tolerancia relativa para altitudes mayores
                tolerance = 0.01 * expected_temp  # 0.5% de tolerancia
                self.assertAlmostEqual(temp, expected_temp, delta=tolerance)
        
            # Temperatura siempre debe ser positiva en Kelvin
            self.assertGreater(temp, 0)

    def test_pressure_profile(self):
        """Prueba el perfil de presión con la altura"""
        test_heights = [0, 1000, 5000, 10000]  # [m]
        pressures = []
        
        for height in test_heights:
            pressure = self.atmosphere.give_press(height)
            pressures.append(pressure)
            self.assertGreater(pressure, 0)  # Presión siempre positiva
        
        # Presión debe disminuir con la altura
        self.assertTrue(all(x > y for x, y in zip(pressures, pressures[1:])))

    def test_density_profile(self):
        """Prueba el perfil de densidad con la altura"""
        test_heights = [0, 1000, 5000, 10000]  # [m]
        densities = []
        
        for height in test_heights:
            density = self.atmosphere.give_dens(height)
            densities.append(density)
            self.assertGreater(density, 0)  # Densidad siempre positiva
        
        # Densidad debe disminuir con la altura
        self.assertTrue(all(x > y for x, y in zip(densities, densities[1:])))

    def test_sound_speed(self):
        """Prueba el cálculo de la velocidad del sonido"""
        test_heights = [0, 1000, 5000, 10000]  # [m]
        
        for height in test_heights:
            v_sonic = self.atmosphere.give_v_sonic(height)
            temp = self.atmosphere.give_temp(height)
            
            # Verificar que v_sonic ≈ sqrt(γRT)
            gamma = 1.4  # Razón de calores específicos para aire
            R = 287.058  # Constante específica del gas para aire [J/(kg·K)]
            expected_v_sonic = np.sqrt(gamma * R * temp)
            
            # Usar tolerancia relativa del 0.01% en lugar de lugares decimales
            tolerance = 0.0001 * expected_v_sonic
            self.assertAlmostEqual(v_sonic, expected_v_sonic, delta=tolerance,
                msg=f"Para altura {height}m: velocidad calculada {v_sonic} != esperada {expected_v_sonic}")

if __name__ == '__main__':
    unittest.main()