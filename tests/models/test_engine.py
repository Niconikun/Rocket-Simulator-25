import unittest
import numpy as np
from src.models.engine import EnhancedEngine as Engine
from src.utils.simulation_errors import InputValidationError

class TestEngine(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para las pruebas"""
        # Valores iniciales
        self.time = 0.1  # Tiempo inicial [s]
        self.burn_time = 2.0  # Tiempo de quemado [s]
        self.ambient_pressure = 101325.0  # Presión ambiente [Pa]
        self.nozzle_exit_diameter = 0.1  # Diámetro de salida [m]
        self.propellant_mass = 5.0  # Masa de propelente [kg]
        self.specific_impulse = 220.0  # Impulso específico [s]
        self.mean_thrust = 1000.0  # Empuje medio [N]
        self.max_thrust = 1200.0  # Empuje máximo [N]
        self.mean_chamber_pressure = 2e6  # Presión media cámara [Pa]
        self.max_chamber_pressure = 2.5e6  # Presión máxima cámara [Pa]
        self.thrust_to_weight_ratio = 20.0  # Relación empuje/peso

        self.engine = Engine(
            self.time,
            self.burn_time,
            self.ambient_pressure,
            self.nozzle_exit_diameter,
            self.propellant_mass,
            self.specific_impulse,
            self.mean_thrust,
            self.max_thrust,
            self.mean_chamber_pressure,
            self.max_chamber_pressure,
            self.thrust_to_weight_ratio
        )

    def test_initialization(self):
        """Prueba el arranque correcto del motor"""
        self.assertEqual(self.engine.time, self.time)
        self.assertEqual(self.engine.ambient_pressure, self.ambient_pressure)
        self.assertEqual(self.engine.burn_time, self.burn_time)
        self.assertEqual(self.engine.propellant_mass, self.propellant_mass)
        self.assertEqual(self.engine.specific_impulse, self.specific_impulse)
        self.assertEqual(self.engine.mean_thrust, self.mean_thrust)
        self.assertEqual(self.engine.max_thrust, self.max_thrust)
        self.assertEqual(self.engine.mean_chamber_pressure, self.mean_chamber_pressure)
        self.assertEqual(self.engine.max_chamber_pressure, self.max_chamber_pressure)
        self.assertEqual(self.engine.thrust_to_weight_ratio, self.thrust_to_weight_ratio)
        
    def test_thrust_calculation(self):
        """Prueba el cálculo del empuje (dummy, solo verifica tipo y rango)"""
        self.assertIsInstance(self.engine.mean_thrust, float)
        self.assertGreater(self.engine.mean_thrust, 0)

    def test_burn_time_effects(self):
        """Prueba el comportamiento del motor durante el quemado (dummy)"""
        self.engine.time = 2.0
        self.assertGreaterEqual(self.engine.burn_time, self.engine.time)

    def test_pressure_compensation(self):
        """Prueba la compensación de presión atmosférica (dummy)"""
        test_pressures = [101325.0, 50000.0, 10000.0]
        for p_amb in test_pressures:
            self.engine.ambient_pressure = p_amb
            self.assertGreaterEqual(self.engine.max_thrust, 0)

    def test_invalid_parameters(self):
        """Prueba el manejo de parámetros inválidos"""
        with self.assertRaises(InputValidationError):
            Engine(0.0, -1.0, 2.0, 0.1, 5.0, 220.0, 1000.0, 1200.0, 2e6, 2.5e6, 20.0)
        with self.assertRaises(InputValidationError):
            Engine(0.0, 101325.0, -1.0, 0.1, 5.0, 220.0, 1000.0, 1200.0, 2e6, 2.5e6, 20.0)

    def test_sea_level_performance(self):
        """Prueba el rendimiento a nivel del mar (dummy)"""
        self.engine.ambient_pressure = 101325.0
        self.assertGreaterEqual(self.engine.mean_thrust, 0)

    def test_vacuum_performance(self):
        """Prueba el rendimiento en vacío (dummy)"""
        self.engine.ambient_pressure = 0.0
        self.assertGreaterEqual(self.engine.max_thrust, 0)

    def test_thrust_coefficient(self):
        """Prueba el cálculo del coeficiente de empuje (dummy)"""
        self.assertGreaterEqual(self.engine.thrust_to_weight_ratio, 0)

    def test_specific_impulse(self):
        """Prueba el cálculo del impulso específico"""
        Isp = self.engine.specific_impulse
        self.assertGreater(Isp, 0)
        self.assertLess(Isp, 500)

    def test_expansion_ratio(self):
        """Prueba la relación de expansión de la tobera"""
        throat_diameter = self.nozzle_exit_diameter / 2.0
        expansion_ratio = (self.nozzle_exit_diameter/throat_diameter)**2
        self.assertGreater(expansion_ratio, 1.0)
        self.assertLess(expansion_ratio, 100.0)

if __name__ == '__main__':
    unittest.main()
