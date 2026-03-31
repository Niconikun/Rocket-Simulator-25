import unittest
import numpy as np
from src.models.parachute import Parachute

class TestParachute(unittest.TestCase):
    def setUp(self):
        self.diameter = 1.5
        self.Cd = 1.75
        self.deploy_alt = 300.0
        self.config = {
            'diameter': self.diameter,
            'Cd': self.Cd,
            'deployment_altitude': self.deploy_alt
        }
        self.chute = Parachute(self.config)

    def test_initialization(self):
        self.assertEqual(self.chute.diameter, self.diameter)
        self.assertEqual(self.chute.Cd, self.Cd)
        self.assertEqual(self.chute.deployment_altitude, self.deploy_alt)
        self.assertIsNone(self.chute.deployment_time)
        self.assertFalse(self.chute.deployed)
        expected_area = np.pi * (self.diameter/2)**2
        area = np.pi * (self.chute.diameter/2)**2
        self.assertAlmostEqual(area, expected_area)

    def test_check_deployment(self):
        altitude = 290
        velocity = 50
        time = 10.0
        result = self.chute.check_deployment(altitude, velocity, time)
        self.assertTrue(result)
        self.assertTrue(self.chute.deployed)
        self.assertEqual(self.chute.deployment_time, time)

    def test_check_deployment_fails(self):
        # Altitud demasiado alta
        altitude = 350
        velocity = 50
        time = 10.0
        result = self.chute.check_deployment(altitude, velocity, time)
        self.assertFalse(result)
        self.assertFalse(self.chute.deployed)

    def test_drag_force(self):
        density = 1.225
        velocity = 20.0
        self.chute.check_deployment(290, 50, 10.0)
        self.chute.inflation_progress = 1.0
        area = np.pi * (self.chute.diameter/2)**2
        expected_force = 0.5 * density * velocity**2 * self.chute.Cd * area
        calculated_force = self.chute.calculate_drag_force(velocity, density)
        self.assertAlmostEqual(calculated_force, expected_force)

    def test_invalid_parameters(self):
        # Diámetro negativo
        config = {'diameter': -1.0, 'Cd': self.Cd, 'deployment_altitude': self.deploy_alt}
        with self.assertRaises(ValueError):
            Parachute(config)

        # Cd negativo
        config = {'diameter': self.diameter, 'Cd': -1.0, 'deployment_altitude': self.deploy_alt}
        with self.assertRaises(ValueError):
            Parachute(config)

        # Altitud de despliegue negativa
        config = {'diameter': self.diameter, 'Cd': self.Cd, 'deployment_altitude': -100}
        with self.assertRaises(ValueError):
            Parachute(config)


import unittest
import numpy as np
from src.models.parachute import Parachute

class TestParachute(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada prueba"""
        # Parámetros típicos para un paracaídas principal
        self.diameter = 1.5        # [m]
        self.Cd = 1.75            # [-]
        self.deploy_alt = 300.0   # [m]

        import unittest
        import numpy as np
        from src.models.parachute import Parachute

        class TestParachute(unittest.TestCase):
            def setUp(self):
                self.diameter = 1.5
                self.Cd = 1.75
                self.deploy_alt = 300.0
                self.config = {
                    'diameter': self.diameter,
                    'Cd': self.Cd,
                    'deployment_altitude': self.deploy_alt
                }
                self.chute = Parachute(self.config)

            def test_initialization(self):
                self.assertEqual(self.chute.diameter, self.diameter)
                self.assertEqual(self.chute.Cd, self.Cd)
                self.assertEqual(self.chute.deployment_altitude, self.deploy_alt)
                self.assertIsNone(self.chute.deployment_time)
                self.assertFalse(self.chute.deployed)
                expected_area = np.pi * (self.diameter/2)**2
                area = np.pi * (self.chute.diameter/2)**2
                self.assertAlmostEqual(area, expected_area)

            def test_check_deployment(self):
                altitude = 290
                velocity = 50
                time = 10.0
                result = self.chute.check_deployment(altitude, velocity, time)
                self.assertTrue(result)
                self.assertTrue(self.chute.deployed)
                self.assertEqual(self.chute.deployment_time, time)

            def test_check_deployment_fails(self):
                # Altitud demasiado alta
                altitude = 350
                velocity = 50
                time = 10.0
                result = self.chute.check_deployment(altitude, velocity, time)
                self.assertFalse(result)
                self.assertFalse(self.chute.deployed)

            def test_drag_force(self):
                density = 1.225
                velocity = 20.0
                self.chute.check_deployment(290, 50, 10.0)
                self.chute.inflation_progress = 1.0
                area = np.pi * (self.chute.diameter/2)**2
                expected_force = 0.5 * density * velocity**2 * self.chute.Cd * area
                calculated_force = self.chute.calculate_drag_force(velocity, density)
                self.assertAlmostEqual(calculated_force, expected_force)

            def test_invalid_parameters(self):
                # Diámetro negativo
                config = {'diameter': -1.0, 'Cd': self.Cd, 'deployment_altitude': self.deploy_alt}
                with self.assertRaises(ValueError):
                    Parachute(config)

                # Cd negativo
                config = {'diameter': self.diameter, 'Cd': -1.0, 'deployment_altitude': self.deploy_alt}
                with self.assertRaises(ValueError):
                    Parachute(config)

                # Altitud de despliegue negativa
                config = {'diameter': self.diameter, 'Cd': self.Cd, 'deployment_altitude': -100}
