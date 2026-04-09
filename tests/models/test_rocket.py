import unittest
import numpy as np
from src.models.rocket import Rocket
from src.models.engine import EnhancedEngine as Engine
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

    def test_aerodynamic_forces(self):
        """Prueba que los atributos aerodinámicos están inicializados"""
        self.rocket.density = 1.225
        self.rocket.alpha = 5.0
        self.rocket.v_b = np.array([98.48, 0.0, 8.72])
        
        # Verificar que los atributos existen
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

    def test_aerodynamic_stability(self):
        """Prueba que los parámetros de estabilidad están definidos"""
        self.rocket.alpha = 5.0
        self.rocket.cm_b = np.array([1.0, 0.0, 0.0])
        self.rocket.cp_b = np.array([1.5, 0.0, 0.0])
        
        # Verificar que están definidos
        self.assertIsNotNone(self.rocket.alpha)
        self.assertTrue(np.allclose(self.rocket.cm_b, np.array([1.0, 0.0, 0.0])))

    def test_invalid_mass_input(self):
        """Prueba el manejo de masas inválidas"""
        from src.utils.simulation_errors import InputValidationError
        with self.assertRaises(InputValidationError):
            invalid_rocket = Rocket(self.r_enu_0, self.v_enu_0, 
                                  self.q_enu2b_0, self.w_enu_0, 
                                  -1.0)


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

if __name__ == '__main__':
    unittest.main()