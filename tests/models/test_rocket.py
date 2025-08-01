import unittest
import numpy as np
from src.models.rocket import Rocket
from src.models.engine import Engine
from src.utils.mattools import MatTools as Mat

class TestRocket(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada prueba"""
        # Valores iniciales típicos
        self.r_enu_0 = np.array([0., 0., 0.])
        self.v_enu_0 = np.array([0., 0., 0.])
        self.q_enu2b_0 = np.array([0., 0., 0., 1.])  # Cuaternión identidad
        self.w_enu_0 = np.array([0., 0., 0.])
        self.initial_mass = 10.0  # kg
        
        # Crear instancia de cohete
        self.rocket = Rocket(self.r_enu_0, self.v_enu_0, 
                           self.q_enu2b_0, self.w_enu_0, 
                           self.initial_mass)

        # Inicializar atributos adicionales necesarios
        self.rocket.w_b = self.w_enu_0.copy()
        self.rocket.alpha = 0.0
        self.rocket.v_b = np.array([0., 0., 0.])
        self.rocket.cp_b = np.array([0., 0., 0.])
        self.rocket.cm_b = np.array([0., 0., 0.])
        
        # Inicializar todas las fuerzas
        self.rocket.forces_drag_b = np.zeros(3)
        self.rocket.forces_lift_b = np.zeros(3)
        self.rocket.forces_aero_b = np.zeros(3)
        self.rocket.forces_engine_b = np.zeros(3)
        self.rocket.forces_b = np.zeros(3)  # Agregar esta línea
        self.rocket.forces_enu = np.zeros(3)  # Y esta también
        
        # Inicializar todos los torques
        self.rocket.torques_aero_b = np.zeros(3)
        self.rocket.torques_engine_b = np.zeros(3)
        self.rocket.torques_b = np.zeros(3)
        self.rocket.torques_enu = np.zeros(3)
    
        # Parámetros del motor
        self.rocket.mass_flux = 0.0  # [kg/s] Flujo másico inicial
        self.rocket.thrust = 0.0     # [N] Empuje inicial
        self.rocket.burn_time = 0.0  # [s] Tiempo de quemado
    
        # Otros parámetros necesarios
        self.rocket.inertia_b = np.array([1.0, 1.0, 1.0])
        self.rocket.density = 1.225  # Densidad del aire a nivel del mar
        self.rocket.v_sonic = 340.0  # Velocidad del sonido
        self.rocket.press_amb = 101325.0  # Presión atmosférica
        self.rocket.g_enu = np.array([0., 0., -9.81])  # Vector gravedad
        self.rocket.g_b = np.array([0., 0., -9.81])    # Vector gravedad en marco del cuerpo
        self.rocket.g_vector_enu = np.array([0., 0., -1.])  # Vector unitario de gravedad

    def test_initialization(self):
        """Prueba la inicialización correcta del cohete"""
        self.assertTrue(np.array_equal(self.rocket.r_enu, self.r_enu_0))
        self.assertTrue(np.array_equal(self.rocket.v_enu, self.v_enu_0))
        self.assertTrue(np.array_equal(self.rocket.q_enu2b, self.q_enu2b_0))
        self.assertEqual(self.rocket.mass, self.initial_mass)

    def test_update_atmosphere(self):
        """Prueba la actualización de parámetros atmosféricos"""
        density = 1.225  # kg/m³
        pressure = 101325  # Pa
        v_sonic = 340  # m/s
        
        self.rocket.update_atmosphere(density, pressure, v_sonic)
        
        self.assertEqual(self.rocket.density, density)
        self.assertEqual(self.rocket.press_amb, pressure)
        self.assertEqual(self.rocket.v_sonic, v_sonic)

    def test_aerodynamic_forces(self):
        """Prueba el cálculo de fuerzas aerodinámicas"""
        # Configurar condiciones completas
        self.rocket.density = 1.225
        self.rocket.v_norm = 100.0
        self.rocket.drag_coeff = 0.5
        self.rocket.alpha = 5.0  # 5 grados de ángulo de ataque
        self.rocket.v_b = np.array([98.48, 0.0, 8.72])  # Velocidad correspondiente a alpha=5°
        reference_area = 0.01  # m²
        
        # Calcular fuerzas
        self.rocket.update_forces_aero(reference_area)
        
        # Verificaciones más completas
        self.assertTrue(self.rocket.drag > 0)
        self.assertLess(self.rocket.drag, 10000)
        self.assertTrue(np.all(np.isfinite(self.rocket.forces_aero_b)))
        self.assertTrue(np.all(np.isfinite(self.rocket.torques_aero_b)))

    def test_quaternion_normalization(self):
        """Prueba la normalización del cuaternión"""
        # Crear un cuaternión no normalizado
        q_test = np.array([1., 1., 1., 1.])
        self.rocket.q_enu2b = q_test
        self.rocket.w_enu = np.array([0., 0., 0.])  # Agregar esto
        
        # Simular un paso de tiempo
        dt = 0.01
        self.rocket.RK4_update(dt)
        
        # Verificar que el cuaternión resultante está normalizado
        q_norm = np.linalg.norm(self.rocket.q_enu2b)
        self.assertAlmostEqual(q_norm, 1.0, places=6)

    def test_mass_conservation(self):
        """Prueba la conservación de masa durante el quemado"""
        initial_mass = self.rocket.mass
        mass_flux = 0.1  # kg/s
        burn_time = 2.0  # s
        
        # Simular quemado
        self.rocket.mass_flux = mass_flux
        dt = 0.1
        steps = int(burn_time/dt)
        
        for _ in range(steps):
            self.rocket.RK4_update(dt)
        
        expected_mass = initial_mass - mass_flux * burn_time
        self.assertAlmostEqual(self.rocket.mass, expected_mass, places=3)

    def test_rk4_integration_constant_velocity(self):
        """
        Prueba la integración RK4 con velocidad constante.
        Verifica que la posición cambia correctamente.
        """
        # Configurar condiciones iniciales
        self.rocket.v_enu = np.array([10.0, 0.0, 0.0])  # 10 m/s en dirección Este
        self.rocket.r_enu = np.array([0.0, 0.0, 0.0])   # Origen
        initial_pos = self.rocket.r_enu.copy()
        
        # Integrar por 1 segundo
        dt = 0.01
        steps = int(1.0/dt)
        for _ in range(steps):
            self.rocket.RK4_update(dt)
        
        # Verificar posición final (debe ser aproximadamente 10m en x)
        expected_position = initial_pos + np.array([10.0, 0.0, 0.0])
        np.testing.assert_array_almost_equal(self.rocket.r_enu, expected_position, decimal=2)

    def test_coordinate_transformations(self):
        """
        Prueba las transformaciones entre marcos de referencia ENU y Body.
        """
        # Configurar un cuaternión para rotación de 90 grados alrededor de z
        self.rocket.q_enu2b = np.array([0.0, 0.0, 0.707, 0.707])  # 90° en z
        
        # Vector en ENU
        v_enu = np.array([1.0, 0.0, 0.0])  # Vector apuntando al Este
        
        # Transformar a marco del cuerpo
        v_body = Mat.q_rot(v_enu, self.rocket.q_enu2b, 0)
        
        # Para rotación de 90° en z, el vector debe apuntar al Norte en marco del cuerpo
        expected_v_body = np.array([0.0, 1.0, 0.0])
        np.testing.assert_array_almost_equal(v_body, expected_v_body, decimal=2)

    def test_gravitational_effects(self):
        """
        Prueba los efectos gravitacionales en el cohete.
        """
        # Configurar masa y gravedad
        self.rocket.mass = 10.0  # kg
        dt = 0.1  # segundos
        
        # Velocidad inicial cero
        self.rocket.v_enu = np.array([0.0, 0.0, 0.0])
        initial_vel = self.rocket.v_enu.copy()
        
        # Integrar por 1 segundo
        steps = int(1.0/dt)
        for _ in range(steps):
            self.rocket.RK4_update(dt)
        
        # Verificar cambio en velocidad vertical (aproximadamente -9.81 m/s)
        expected_velocity = initial_vel + np.array([0.0, 0.0, -9.81])
        np.testing.assert_array_almost_equal(self.rocket.v_enu, expected_velocity, decimal=2)

    def test_engine_thrust_effects(self):
        """
        Prueba los efectos del empuje del motor.
        """
        # Configurar empuje
        self.rocket.thrust = 100.0  # N
        self.rocket.mass = 10.0     # kg
        dt = 0.1                    # segundos
        
        # Alinear cohete verticalmente (sin rotación)
        self.rocket.q_enu2b = np.array([0.0, 0.0, 0.0, 1.0])
        
        # Velocidad inicial cero
        self.rocket.v_enu = np.array([0.0, 0.0, 0.0])
        initial_vel = self.rocket.v_enu.copy()
        
        # Integrar por 1 segundo
        steps = int(1.0/dt)
        for _ in range(steps):
            self.rocket.RK4_update(dt)
        
        # Verificar aceleración (F = ma -> a = F/m = 10 m/s²)
        expected_velocity = initial_vel + np.array([10.0, 0.0, -9.81]) # Incluye gravedad
        np.testing.assert_array_almost_equal(self.rocket.v_enu, expected_velocity, decimal=2)

    def test_aerodynamic_stability(self):
        """
        Prueba la estabilidad aerodinámica del cohete.
        """
        # Configurar condiciones de vuelo estable
        self.rocket.v_norm = 100.0  # m/s
        self.rocket.alpha = 5.0     # 5 grados de ángulo de ataque
        self.rocket.cm_b = np.array([1.0, 0.0, 0.0])  # Centro de masa
        self.rocket.cp_b = np.array([1.5, 0.0, 0.0])  # Centro de presión detrás del CM
        
        # Calcular fuerzas aerodinámicas
        reference_area = 0.01  # m²
        self.rocket.update_forces_aero(reference_area)
        
        # Verificar momento estabilizador
        torque_magnitude = np.linalg.norm(self.rocket.torques_aero_b)
        self.assertTrue(torque_magnitude > 0)  # Debe existir un momento
        self.assertTrue(self.rocket.torques_aero_b[1] < 0)  # Momento debe tender a reducir alpha

    def test_invalid_mass_input(self):
        """
        Prueba el manejo de masas inválidas en la inicialización.
        """
        with self.assertRaises(ValueError):
            invalid_rocket = Rocket(self.r_enu_0, self.v_enu_0, 
                                  self.q_enu2b_0, self.w_enu_0, 
                                  -1.0)  # Masa negativa

    def test_extreme_velocities(self):
        """
        Prueba el comportamiento con velocidades extremadamente altas.
        """
        # Velocidad cercana a orbital
        self.rocket.v_enu = np.array([7800.0, 0.0, 0.0])  # ~7.8 km/s
        self.rocket.v_norm = np.linalg.norm(self.rocket.v_enu)
        self.rocket.density = 1e-10  # Densidad muy baja (alta altitud)
        
        reference_area = 0.01
        self.rocket.update_forces_aero(reference_area)
        
        # Verificar que las fuerzas no son NaN o inf
        self.assertTrue(np.all(np.isfinite(self.rocket.forces_aero_b)))
        self.assertTrue(np.all(np.isfinite(self.rocket.torques_aero_b)))

    def test_zero_thrust_conditions(self):
        """
        Prueba el comportamiento cuando el empuje es exactamente cero.
        """
        self.rocket.thrust = 0.0
        self.rocket.mass = 10.0
        dt = 0.1
        
        # Velocidad inicial vertical
        self.rocket.v_enu = np.array([0.0, 0.0, 10.0])
        initial_vel = self.rocket.v_enu.copy()
        
        # Simular un segundo
        steps = int(1.0/dt)
        for _ in range(steps):
            self.rocket.RK4_update(dt)
        
        # Solo debería actuar la gravedad
        expected_velocity = initial_vel + np.array([0.0, 0.0, -9.81])
        np.testing.assert_array_almost_equal(self.rocket.v_enu, expected_velocity, decimal=2)

    def test_extreme_angles_of_attack(self):
        """
        Prueba el comportamiento con ángulos de ataque extremos.
        """
        extreme_angles = [-180, -90, 90, 180]
        
        for angle in extreme_angles:
            self.rocket.alpha = angle
            self.rocket.v_norm = 100.0
            reference_area = 0.01
            
            # No debería lanzar excepciones
            try:
                self.rocket.update_forces_aero(reference_area)
            except Exception as e:
                self.fail(f"Falló con ángulo {angle}: {str(e)}")
            
            # Fuerzas deberían ser finitas
            self.assertTrue(np.all(np.isfinite(self.rocket.forces_aero_b)))

    def test_numerical_stability(self):
        """
        Prueba la estabilidad numérica con pasos de tiempo muy pequeños y grandes.
        """
        # Configuración inicial
        self.rocket.v_enu = np.array([10.0, 0.0, 0.0])
        self.rocket.r_enu = np.array([0.0, 0.0, 0.0])
        initial_pos = self.rocket.r_enu.copy()
        
        # Prueba con paso muy pequeño
        dt_small = 1e-6
        steps_small = int(0.001/dt_small)
        
        for _ in range(steps_small):
            self.rocket.RK4_update(dt_small)
        
        pos_small = self.rocket.r_enu.copy()
        
        # Reiniciar posición
        self.rocket.r_enu = initial_pos.copy()
        
        # Prueba con paso más grande
        dt_large = 0.001
        steps_large = 1
        
        for _ in range(steps_large):
            self.rocket.RK4_update(dt_large)
        
        # Comparar resultados (deberían ser similares)
        np.testing.assert_array_almost_equal(self.rocket.r_enu, pos_small, decimal=3)

    def test_conservation_energy(self):
        """
        Prueba la conservación de energía en condiciones ideales.
        """
        # Configurar condiciones sin pérdidas
        self.rocket.density = 0.0  # Sin resistencia del aire
        self.rocket.thrust = 0.0   # Sin empuje
        self.rocket.mass = 10.0    # kg
        
        # Dar energía inicial
        v0 = 100.0  # m/s
        h0 = 1000.0 # m
        self.rocket.v_enu = np.array([v0, 0.0, 0.0])
        self.rocket.r_enu = np.array([0.0, 0.0, h0])
        
        # Energía inicial
        E0 = 0.5 * self.rocket.mass * v0**2 + self.rocket.mass * 9.81 * h0
        
        # Simular movimiento
        dt = 0.01
        for _ in range(100):
            self.rocket.RK4_update(dt)
            
            # Calcular energía actual
            v = np.linalg.norm(self.rocket.v_enu)
            h = self.rocket.r_enu[2]
            E = 0.5 * self.rocket.mass * v**2 + self.rocket.mass * 9.81 * h
            
            # Verificar conservación (con cierta tolerancia numérica)
            self.assertAlmostEqual(E, E0, delta=E0*0.01)  # 1% de tolerancia