import unittest
import numpy as np
from src.models.aerodynamics import Aerodynamics

class TestAerodynamics(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada prueba"""
        # Parámetros geométricos originales
        self.fins_chord_tip = 0.1        # [m] Cuerda en la punta de la aleta
        self.fins_mid_chord = 0.15       # [m] Cuerda media de la aleta
        self.len_rear = 0.1             # [m] Longitud de la sección trasera
        self.fins_span = 0.15           # [m] Envergadura de las aletas
        self.diameter_warhead_base = 0.1 # [m] Diámetro base de la ojiva
        self.diameter_bodytube = 0.1     # [m] Diámetro del cuerpo principal
        self.diameter_bodytube_fins = 0.1 # [m] Diámetro en la sección de aletas
        self.diameter_rear_bodytube = 0.1 # [m] Diámetro en la sección trasera
        self.end_diam_rear = 0.105       # [m] Diámetro final de la sección trasera
        self.N_fins = 4                  # [-] Número de aletas
        
        # Condiciones atmosféricas (mantenidas para los cálculos)
        self.density = 1.225            # [kg/m³] Densidad del aire
        self.viscosity = 1.789e-5       # [kg/m·s] Viscosidad dinámica
        self.sound_speed = 340          # [m/s] Velocidad del sonido
        
        # Crear instancia con los parámetros originales
        self.aero = Aerodynamics(
            self.fins_chord_tip,
            self.fins_mid_chord,
            self.len_rear,
            self.fins_span,
            self.diameter_warhead_base,
            self.diameter_bodytube,
            self.diameter_bodytube_fins,
            self.diameter_rear_bodytube,
            self.end_diam_rear,
            self.N_fins
        )

    def test_initialization(self):
        """Prueba la inicialización correcta"""
        self.assertEqual(self.aero.fins_chord_tip, self.fins_chord_tip)
        self.assertEqual(self.aero.fins_mid_chord, self.fins_mid_chord)
        self.assertEqual(self.aero.len_rear, self.len_rear)
        self.assertEqual(self.aero.fins_span, self.fins_span)
        self.assertEqual(self.aero.diameter_warhead_base, self.diameter_warhead_base)
        self.assertEqual(self.aero.diameter_bodytube, self.diameter_bodytube)
        self.assertEqual(self.aero.diameter_bodytube_fins, self.diameter_bodytube_fins)
        self.assertEqual(self.aero.diameter_rear_bodytube, self.diameter_rear_bodytube)
        self.assertEqual(self.aero.end_diam_rear, self.end_diam_rear)
        self.assertEqual(self.aero.N_fins, self.N_fins)

    def test_reference_area(self):
        """Prueba el cálculo del área de referencia"""
        expected_area = np.pi * (self.diameter_bodytube/2)**2
        self.assertAlmostEqual(self.aero.reference_area, expected_area)

    def test_reynolds_number(self):
        """Prueba el cálculo del número de Reynolds"""
        velocity = 100.0  # m/s
        Re = self.aero.calculate_reynolds(velocity, self.density, self.viscosity)
        expected_Re = (self.density * velocity * self.length) / self.viscosity
        self.assertAlmostEqual(Re, expected_Re)

    def test_mach_number(self):
        """Prueba el cálculo del número de Mach"""
        velocity = 200.0  # m/s
        mach = self.aero.calculate_mach(velocity, self.sound_speed)
        expected_mach = velocity / self.sound_speed
        self.assertAlmostEqual(mach, expected_mach)

    def test_drag_coefficient(self):
        """Prueba el cálculo del coeficiente de resistencia"""
        velocity = 100.0
        alpha = 0.0  # ángulo de ataque nulo
        
        Cd = self.aero.calculate_drag_coefficient(
            velocity, 
            alpha, 
            self.density, 
            self.viscosity, 
            self.sound_speed
        )
        
        # Verificar rango razonable para Cd
        self.assertGreater(Cd, 0.2)  # Mínimo típico
        self.assertLess(Cd, 1.0)     # Máximo típico

    def test_lift_coefficient(self):
        """Prueba el cálculo del coeficiente de sustentación"""
        velocity = 100.0
        alpha = np.radians(5.0)  # 5 grados de ángulo de ataque
        
        Cl = self.aero.calculate_lift_coefficient(
            velocity,
            alpha,
            self.density,
            self.viscosity,
            self.sound_speed
        )
        
        # Verificar que Cl aumenta con alpha
        self.assertGreater(Cl, 0.0)
        
        # Probar con alpha = 0
        Cl_zero = self.aero.calculate_lift_coefficient(
            velocity,
            0.0,
            self.density,
            self.viscosity,
            self.sound_speed
        )
        self.assertAlmostEqual(Cl_zero, 0.0)

    def test_center_of_pressure(self):
        """Prueba el cálculo del centro de presión"""
        velocity = 100.0
        alpha = np.radians(2.0)
        
        cp = self.aero.calculate_cp_location(
            velocity,
            alpha,
            self.density,
            self.viscosity,
            self.sound_speed
        )
        
        # CP debe estar entre la punta y la base
        self.assertGreater(cp[0], 0.0)
        self.assertLess(cp[0], self.length)

    def test_stability_margin(self):
        """Prueba el cálculo del margen de estabilidad"""
        # Posición del centro de masa (asumida)
        cg = np.array([0.6 * self.length, 0.0, 0.0])
        
        velocity = 100.0
        alpha = 0.0
        
        margin = self.aero.calculate_stability_margin(
            velocity,
            alpha,
            self.density,
            self.viscosity,
            self.sound_speed,
            cg
        )
        
        # Margen de estabilidad debe ser positivo y razonable
        self.assertGreater(margin, 0.0)
        self.assertLess(margin, 6.0)  # calibres

    def test_angle_of_attack_effects(self):
        """Prueba los efectos del ángulo de ataque"""
        velocity = 100.0
        test_angles = np.radians([0, 5, 10, 15])
        
        Cl_values = []
        Cd_values = []
        
        for alpha in test_angles:
            Cl = self.aero.calculate_lift_coefficient(
                velocity,
                alpha,
                self.density,
                self.viscosity,
                self.sound_speed
            )
            Cd = self.aero.calculate_drag_coefficient(
                velocity,
                alpha,
                self.density,
                self.viscosity,
                self.sound_speed
            )
            Cl_values.append(Cl)
            Cd_values.append(Cd)
        
        # Verificar que Cl aumenta con alpha
        self.assertTrue(all(x < y for x, y in zip(Cl_values, Cl_values[1:])))
        
        # Verificar que Cd aumenta con alpha
        self.assertTrue(all(x < y for x, y in zip(Cd_values, Cd_values[1:])))

if __name__ == '__main__':
    unittest.main()