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
        
        for height in test_heights:
            temp = self.atmosphere.give_temp(height)
            # Temperatura debe disminuir con la altura hasta la tropopausa
            if height < 11000:  # Tropopausa
                self.assertLess(temp, self.atmosphere.sea_level_temp + self.atmosphere.offset)
            self.assertGreater(temp, 0)  # Temperatura en K siempre positiva

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
            
            self.assertAlmostEqual(v_sonic, expected_v_sonic, places=2)

if __name__ == '__main__':
    unittest.main()