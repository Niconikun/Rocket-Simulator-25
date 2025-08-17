import unittest
import numpy as np
from src.models.to_be_implemented.parachute import Parachute

class TestParachute(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada prueba"""
        # Parámetros típicos para un paracaídas principal
        self.diameter = 1.5        # [m]
        self.Cd = 1.75            # [-]
        self.deploy_alt = 300.0   # [m]
        self.deploy_time = 1.0    # [s]
        
        # Crear instancia del paracaídas
        self.chute = Parachute(
            self.diameter,
            self.Cd,
            self.deploy_alt,
            self.deploy_time
        )

    def test_initialization(self):
        """Prueba la inicialización correcta del paracaídas"""
        self.assertEqual(self.chute.diameter, self.diameter)
        self.assertEqual(self.chute.Cd, self.Cd)
        self.assertEqual(self.chute.deployment_altitude, self.deploy_alt)
        self.assertEqual(self.chute.deployment_time, self.deploy_time)
        self.assertFalse(self.chute.is_deployed)
        
        # Verificar área calculada
        expected_area = np.pi * (self.diameter/2)**2
        self.assertAlmostEqual(self.chute.area, expected_area)

    def test_deployment_conditions(self):
        """Prueba las condiciones de despliegue"""
        # Caso 1: Altitud correcta, velocidad segura
        altitude = 290  # Por debajo de deployment_altitude
        velocity = 50   # Velocidad segura
        self.assertTrue(self.chute._check_deployment_conditions(altitude, velocity))
        
        # Caso 2: Altitud muy baja
        altitude = 10
        self.assertFalse(self.chute._check_deployment_conditions(altitude, velocity))
        
        # Caso 3: Velocidad muy alta
        altitude = 290
        velocity = 200
        self.assertFalse(self.chute._check_deployment_conditions(altitude, velocity))

    def test_drag_force(self):
        """Prueba el cálculo de la fuerza de arrastre"""
        # Condiciones atmosféricas típicas
        density = 1.225     # [kg/m³]
        velocity = 20.0     # [m/s]
        
        # Calcular fuerza esperada
        q = 0.5 * density * velocity**2
        expected_force = q * self.chute.area * self.chute.Cd
        
        # Obtener fuerza calculada
        calculated_force = self.chute.calculate_drag(density, velocity)
        
        self.assertAlmostEqual(calculated_force, expected_force)

    def test_deployment_sequence(self):
        """Prueba la secuencia de despliegue"""
        # Iniciar despliegue
        initial_time = 10.0
        self.chute.start_deployment(initial_time)
        
        # Verificar estado inicial de despliegue
        self.assertTrue(self.chute.is_deploying)
        self.assertEqual(self.chute.deployment_start_time, initial_time)
        
        # Verificar factor de despliegue en diferentes momentos
        # t = 0% del tiempo de despliegue
        factor = self.chute.get_deployment_factor(initial_time)
        self.assertAlmostEqual(factor, 0.0)
        
        # t = 50% del tiempo de despliegue
        half_time = initial_time + self.deploy_time/2
        factor = self.chute.get_deployment_factor(half_time)
        self.assertAlmostEqual(factor, 0.5)
        
        # t = 100% del tiempo de despliegue
        final_time = initial_time + self.deploy_time
        factor = self.chute.get_deployment_factor(final_time)
        self.assertAlmostEqual(factor, 1.0)
        
        # Verificar estado final
        self.assertTrue(self.chute.is_deployed)

    def test_invalid_parameters(self):
        """Prueba el manejo de parámetros inválidos"""
        # Diámetro negativo
        with self.assertRaises(ValueError):
            Parachute(-1.0, self.Cd, self.deploy_alt)
        
        # Cd negativo
        with self.assertRaises(ValueError):
            Parachute(self.diameter, -1.0, self.deploy_alt)
        
        # Altitud de despliegue negativa
        with self.assertRaises(ValueError):
            Parachute(self.diameter, self.Cd, -100)

if __name__ == '__main__':
    unittest.main()