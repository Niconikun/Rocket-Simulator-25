import unittest
import numpy as np
from src.models.engine import Engine

class TestEngine(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada prueba"""
        # Parámetros típicos del motor
        self.time = 0.0
        self.ambient_pressure = 101325.0  # Presión atmosférica a nivel del mar [Pa]
        self.burn_time = 5.0             # Tiempo de quemado [s]
        self.nozzle_exit_diameter = 0.05 # Diámetro de salida [m]
        self.mass_flux = 0.1             # Flujo másico [kg/s]
        self.gas_speed = 2000.0          # Velocidad de gases [m/s]
        self.exit_pressure = 101325.0    # Presión de salida [Pa]
        
        # Crear instancia del motor
        self.engine = Engine(
            self.time,
            self.ambient_pressure,
            self.burn_time,
            self.nozzle_exit_diameter,
            self.mass_flux,
            self.gas_speed,
            self.exit_pressure
        )

    def test_initialization(self):
        """Prueba la inicialización correcta del motor"""
        self.assertEqual(self.engine.time, self.time)
        self.assertEqual(self.engine.ambient_pressure, self.ambient_pressure)
        self.assertEqual(self.engine.burn_time, self.burn_time)
        self.assertEqual(self.engine.mass_flux, self.mass_flux)
        
    def test_thrust_calculation(self):
        """Prueba el cálculo del empuje"""
        # Empuje esperado = ṁv + (pe - pa)A
        exit_area = np.pi * (self.nozzle_exit_diameter/2)**2
        expected_thrust = (self.mass_flux * self.gas_speed + 
                         (self.exit_pressure - self.ambient_pressure) * exit_area)
        
        self.assertAlmostEqual(self.engine.thrust, expected_thrust, places=2)

    def test_burn_time_effects(self):
        """Prueba el comportamiento del motor durante el quemado"""
        # Antes del tiempo de quemado
        self.engine.time = 2.0  # Durante el quemado
        self.assertEqual(self.engine.mass_flux, self.mass_flux)
        
        # Después del tiempo de quemado
        self.engine.time = 6.0  # Después del quemado
        self.assertEqual(self.engine.mass_flux, 0.0)
        self.assertEqual(self.engine.thrust, 0.0)

    def test_pressure_compensation(self):
        """Prueba la compensación de presión atmosférica"""
        # Prueba a diferentes altitudes
        test_pressures = [101325.0, 50000.0, 10000.0]  # Presiones a diferentes altitudes
        
        for p_amb in test_pressures:
            self.engine.ambient_pressure = p_amb
            exit_area = np.pi * (self.nozzle_exit_diameter/2)**2
            expected_thrust = (self.mass_flux * self.gas_speed + 
                             (self.exit_pressure - p_amb) * exit_area)
            
            self.assertAlmostEqual(self.engine.thrust, expected_thrust, places=2)

    def test_invalid_parameters(self):
        """Prueba el manejo de parámetros inválidos"""
        with self.assertRaises(ValueError):
            Engine(0.0, -1.0, 5.0, 0.05, 0.1, 2000.0, 101325.0)  # Presión negativa
            
        with self.assertRaises(ValueError):
            Engine(0.0, 101325.0, -1.0, 0.05, 0.1, 2000.0, 101325.0)  # Tiempo de quemado negativo

    def test_sea_level_performance(self):
        """Prueba el rendimiento a nivel del mar"""
        # Condiciones a nivel del mar
        self.engine.ambient_pressure = 101325.0
        self.engine.exit_pressure = 101325.0
        
        # El empuje debería ser principalmente debido al flujo másico
        expected_thrust = self.mass_flux * self.gas_speed
        actual_thrust = self.engine.thrust
        
        # Tolerancia del 1%
        self.assertLess(abs(actual_thrust - expected_thrust)/expected_thrust, 0.01)

    def test_vacuum_performance(self):
        """Prueba el rendimiento en vacío"""
        # Condiciones de vacío
        self.engine.ambient_pressure = 0.0
        
        exit_area = np.pi * (self.nozzle_exit_diameter/2)**2
        expected_thrust = (self.mass_flux * self.gas_speed + 
                         self.exit_pressure * exit_area)  # pa = 0
        
        self.assertAlmostEqual(self.engine.thrust, expected_thrust, places=2)

    def test_thrust_coefficient(self):
        """Prueba el cálculo del coeficiente de empuje"""
        # Calcular coeficiente de empuje
        exit_area = np.pi * (self.nozzle_exit_diameter/2)**2
        p_c = self.exit_pressure * 2  # Asumiendo una relación de expansión típica
        
        C_f = self.engine.thrust / (p_c * exit_area)
        
        # Verificar que está en un rango razonable (típicamente entre 1.0 y 2.0)
        self.assertGreater(C_f, 0.5)
        self.assertLess(C_f, 2.5)

    def test_specific_impulse(self):
        """
        Prueba el cálculo del impulso específico.
        """
        # Isp = F/(ṁg0)
        g0 = 9.81  # Gravedad estándar
        Isp = self.engine.thrust / (self.mass_flux * g0)
        
        # Verificar que está en un rango típico para motores cohete sólidos (180-250s)
        self.assertGreater(Isp, 150)
        self.assertLess(Isp, 300)
        
        # Verificar que aumenta en vacío
        self.engine.ambient_pressure = 0.0
        Isp_vacuum = self.engine.thrust / (self.mass_flux * g0)
        self.assertGreater(Isp_vacuum, Isp)

    def test_transient_behavior(self):
        """
        Prueba el comportamiento transitorio del motor durante el encendido y apagado.
        """
        # Justo antes del encendido
        self.engine.time = -0.1
        self.assertEqual(self.engine.thrust, 0.0)
        
        # Durante el encendido
        self.engine.time = 0.1
        self.assertGreater(self.engine.thrust, 0.0)
        
        # Justo antes del apagado
        self.engine.time = self.burn_time - 0.1
        self.assertGreater(self.engine.thrust, 0.0)
        
        # Después del apagado
        self.engine.time = self.burn_time + 0.1
        self.assertEqual(self.engine.thrust, 0.0)

    def test_expansion_ratio(self):
        """
        Prueba la relación de expansión de la tobera.
        """
        # Asumiendo una garganta típica
        throat_diameter = self.nozzle_exit_diameter / 2.0  # Relación de expansión = 4
        expansion_ratio = (self.nozzle_exit_diameter/throat_diameter)**2
        
        # Verificar que la relación de expansión es razonable
        self.assertGreater(expansion_ratio, 1.0)  # Debe ser convergente-divergente
        self.assertLess(expansion_ratio, 100.0)   # Límite superior típico

    def test_thermal_constraints(self):
        """
        Prueba las restricciones térmicas del motor.
        """
        # Temperatura de combustión típica para propelente sólido
        T_chamber = 3000  # K
        
        # Velocidad del sonido en gases calientes
        gamma = 1.2  # Razón de calores específicos típica
        R = 8314/30  # Constante de gas específica (J/kg·K) para gases de escape típicos
        a = np.sqrt(gamma * R * T_chamber)
        
        # La velocidad de los gases no debe superar la velocidad del sonido en la garganta
        self.assertLess(self.gas_speed, a)

    def test_performance_parameters(self):
        """
        Prueba varios parámetros de rendimiento del motor.
        """
        # Calcular potencia del motor
        power = 0.5 * self.mass_flux * self.gas_speed**2
        
        # Calcular impulso total
        total_impulse = self.engine.thrust * self.burn_time
        
        # Verificaciones
        self.assertGreater(power, 0)
        self.assertLess(power, 1e7)  # Límite superior razonable para motores pequeños
        self.assertGreater(total_impulse, 0)
        self.assertLess(total_impulse, 1e6)  # Límite superior razonable

    def test_mass_flow_consistency(self):
        """
        Prueba la consistencia del flujo másico durante el quemado.
        """
        # Masa total de propelente
        total_propellant_mass = self.mass_flux * self.burn_time
        
        # Simular quemado en intervalos
        time_steps = np.linspace(0, self.burn_time, 100)
        accumulated_mass = 0
        
        for t in time_steps:
            self.engine.time = t
            accumulated_mass += self.engine.mass_flux * (self.burn_time/100)
        
        # Verificar conservación de masa
        self.assertAlmostEqual(accumulated_mass, total_propellant_mass, places=2)

if __name__ == '__main__':
    unittest.main()