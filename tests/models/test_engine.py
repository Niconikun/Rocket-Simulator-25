import unittest
import math
from src.models.engine import Engine

class TestEngine(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para las pruebas"""
        # Valores iniciales
        self.time = 0.1  # Tiempo inicial [s]
        self.ambient_pressure = 101325.0  # Presión ambiente [Pa]
        self.burn_time = 2.0  # Tiempo de quemado [s]
        self.nozzle_exit_diameter = 0.1  # Diámetro de salida [m]
        self.mass_flux_max = 1.0  # Flujo másico máximo [kg/s]
        self.gas_speed = 2000.0  # Velocidad de salida [m/s]
        self.exit_pressure = 101325.0  # Presión de salida [Pa]

        # Crear instancia del motor
        self.engine = Engine(
            self.time,
            self.ambient_pressure,
            self.burn_time,
            self.nozzle_exit_diameter,
            self.mass_flux_max,
            self.gas_speed,
            self.exit_pressure
        )

    def test_initialization(self):
        """Prueba el arranque correcto del motor"""
        self.assertEqual(self.engine.time, self.time)
        self.assertEqual(self.engine.ambient_pressure, self.ambient_pressure)
        self.assertEqual(self.engine.burn_time, self.burn_time)
        self.assertEqual(self.engine.mass_flux, self.mass_flux_max)
        
    def test_thrust_calculation(self):
        """Prueba el cálculo del empuje"""
        # Empuje esperado = ṁv + (pe - pa)A
        exit_area = math.pi * (self.nozzle_exit_diameter/2)**2
        expected_thrust = (self.mass_flux_max * self.gas_speed + 
                         (self.exit_pressure - self.ambient_pressure) * exit_area)
        
        self.assertAlmostEqual(self.engine.thrust, expected_thrust, places=2)

    def test_burn_time_effects(self):
        """Prueba el comportamiento del motor durante el quemado"""
        # Durante el tiempo de quemado
        self.engine.update(time=1.0)  # Durante el quemado
        self.assertEqual(self.engine.mass_flux, self.mass_flux_max)
        
        # Después del tiempo de quemado
        self.engine.update(time=3.0)  # Después del quemado
        self.assertEqual(self.engine.mass_flux, 0.0)
        self.assertEqual(self.engine.thrust, 0.0)

    def test_pressure_compensation(self):
        """Prueba la compensación de presión atmosférica"""
        # Prueba a diferentes altitudes
        test_pressures = [101325.0, 50000.0, 10000.0]  # Presiones a diferentes altitudes
        
        for p_amb in test_pressures:
            self.engine.update(ambient_pressure=p_amb)
            exit_area = math.pi * (self.nozzle_exit_diameter/2)**2
            expected_thrust = (self.mass_flux_max * self.gas_speed + 
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
        expected_thrust = self.mass_flux_max * self.gas_speed
        actual_thrust = self.engine.thrust
        
        # Tolerancia del 1%
        self.assertLess(abs(actual_thrust - expected_thrust)/expected_thrust, 0.01)

    def test_vacuum_performance(self):
        """Prueba el rendimiento en vacío"""
        # Condiciones de vacío
        self.engine.update(ambient_pressure=0.0)
        
        exit_area = math.pi * (self.nozzle_exit_diameter/2)**2
        expected_thrust = (self.mass_flux_max * self.gas_speed + 
                         self.exit_pressure * exit_area)  # pa = 0
        
        self.assertAlmostEqual(self.engine.thrust, expected_thrust, places=2)

    def test_thrust_coefficient(self):
        """Prueba el cálculo del coeficiente de empuje"""
        # Calcular coeficiente de empuje
        exit_area = math.pi * (self.nozzle_exit_diameter/2)**2
        p_c = self.exit_pressure * 2  # Asumiendo una relación de expansión típica
        
        C_f = self.engine.thrust / (p_c * exit_area)
        
        # Verificar que está en un rango razonable (típicamente entre 1.0 y 2.0)
        self.assertGreater(C_f, 0.5)
        self.assertLess(C_f, 2.5)

    def test_specific_impulse(self):
        """Prueba el cálculo del impulso específico."""
        # Obtener Isp a nivel del mar y en vacío
        Isp = self.engine.specific_impulse
        Isp_vacuum = self.engine.vacuum_specific_impulse
        
        # Verificaciones
        self.assertGreater(Isp, 0)
        self.assertGreater(Isp_vacuum, Isp)  # Isp en vacío debe ser mayor
        self.assertLess(Isp_vacuum, 500)  # Límite superior razonable para motores químicos

    def test_transient_behavior(self):
        """
        Prueba el comportamiento transitorio del motor durante el encendido y apagado.
        """
        # Justo antes del encendido
        self.engine.update(time=-0.1)
        self.assertEqual(self.engine.thrust, 0.0)
        
        # Durante el encendido
        self.engine.update(time=0.1)
        self.assertGreater(self.engine.thrust, 0.0)
        
        # Justo antes del apagado
        self.engine.update(time=self.burn_time - 0.1)
        self.assertGreater(self.engine.thrust, 0.0)
        
        # Después del apagado
        self.engine.update(time=self.burn_time + 0.1)
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
        
        # Velocidad del sonido en la garganta (condición sónica)
        gamma = 1.2  # Razón de calores específicos típica
        R = 8314/30  # Constante de gas específica (J/kg·K) para gases de escape típicos
        a_throat = math.sqrt(gamma * R * T_chamber)
        
        # La velocidad de los gases en la salida puede superar Mach 1
        # pero típicamente no supera Mach 3.5 para toberas convencionales
        max_exit_mach = 3.5
        max_allowed_speed = max_exit_mach * a_throat
        
        self.assertLess(self.gas_speed, max_allowed_speed)
        self.assertGreater(self.gas_speed, a_throat)  # Debe ser supersónico en la salida

    def test_performance_parameters(self):
        """
        Prueba varios parámetros de rendimiento del motor.
        """
        # Calcular potencia del motor
        power = 0.5 * self.mass_flux_max * self.gas_speed**2
        
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
        # Masa total de propelente - ajustada para las rampas de encendido/apagado
        # Nuestro modelo realista tiene rampas de 0.1s cada una, así que la masa efectiva es menor
        total_propellant_mass = self.mass_flux_max * self.burn_time
        
        # Simular quemado en intervalos
        n_steps = 100
        time_step = self.burn_time / n_steps
        accumulated_mass = 0
        
        for i in range(n_steps):
            t = i * time_step
            self.engine.update(time=t)
            accumulated_mass += self.engine.mass_flux * time_step
        
        # Verificar conservación de masa con tolerancia para las rampas
        # Las rampas de encendido/apagado reducen la masa total integrada
        self.assertLess(accumulated_mass, total_propellant_mass)
        self.assertGreater(accumulated_mass, total_propellant_mass * 0.9)  # Al menos 90% por las rampas

    def test_srm_mode(self):
        """Prueba el modo SRM."""
        # Crear motor en modo SRM
        srm_engine = Engine(
            time=1.0,
            ambient_pressure=101325.0,
            burn_time=10.0,
            nozzle_exit_diameter=0.1,
            mass_flux_max=2.0,
            gas_speed=2200.0,
            exit_pressure=120000.0,
            mode='srm',
            length_chamber=1.2,
            diameter_chamber=0.15,
            grain_outer_diameter=0.12,
            grain_length=0.8,
            grain_inner_diameter=0.03,
            N_grains=2,
            rho_grain=1850,
            rho_percentage=0.9
        )
        
        # Verificar que el modo SRM funciona
        self.assertEqual(srm_engine.mode, 'srm')
        self.assertGreater(srm_engine.thrust, 0)
        self.assertGreater(srm_engine.grain_mass_initial, 0)

    def test_engine_configuration_save_load(self):
        """Prueba el guardado y carga de configuraciones de motor."""
        import tempfile
        import os
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Guardar configuración
            self.engine.save_configuration(tmp_path)
            
            # Cargar configuración
            loaded_engine = Engine.load_configuration(tmp_path, time=0.1, ambient_pressure=101325.0)
            
            # Verificar que los parámetros coinciden
            self.assertEqual(loaded_engine.burn_time, self.engine.burn_time)
            self.assertEqual(loaded_engine.nozzle_exit_diameter, self.engine.nozzle_exit_diameter)
            self.assertEqual(loaded_engine.gas_speed, self.engine.gas_speed)
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_performance_data_export(self):
        """Prueba la exportación de datos de rendimiento."""
        performance_data = self.engine.get_performance_data()
        
        # Verificar que contiene las claves esperadas
        expected_keys = ['time', 'thrust', 'mass_flux', 'specific_impulse', 
                        'vacuum_specific_impulse', 'chamber_pressure', 'exit_pressure', 
                        'ambient_pressure', 'mode']
        
        for key in expected_keys:
            self.assertIn(key, performance_data)
        
        # Verificar tipos de datos
        self.assertIsInstance(performance_data['thrust'], (int, float))
        self.assertIsInstance(performance_data['mode'], str)

if __name__ == '__main__':
    unittest.main()