import unittest
import numpy as np
from src.models.aerodynamics import Aerodynamics

class TestAerodynamics(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada prueba"""
        # Parámetros geométricos típicos
        self.diameter = 0.1          # [m] Diámetro del cohete
        self.length = 1.0            # [m] Longitud del cohete
        self.nose_length = 0.2       # [m] Longitud de la ojiva
        self.fin_span = 0.15         # [m] Envergadura de aleta
        self.fin_root_chord = 0.2    # [m] Cuerda raíz de aleta
        self.fin_tip_chord = 0.1     # [m] Cuerda punta de aleta
        self.num_fins = 4            # [-] Número de aletas
        
        # Condiciones atmosféricas
        self.density = 1.225         # [kg/m³] Densidad del aire
        self.viscosity = 1.789e-5    # [kg/m·s] Viscosidad dinámica
        self.sound_speed = 340       # [m/s] Velocidad del sonido
        
        # Crear instancia
        self.aero = Aerodynamics(
            self.diameter,
            self.length,
            self.nose_length,
            self.fin_span,
            self.fin_root_chord,
            self.fin_tip_chord,
            self.num_fins
        )

    def test_initialization(self):
        """Prueba la inicialización correcta"""
        self.assertEqual(self.aero.diameter, self.diameter)
        self.assertEqual(self.aero.length, self.length)
        self.assertEqual(self.aero.num_fins, self.num_fins)

    def test_reference_area(self):
        """Prueba el cálculo del área de referencia"""
        expected_area = np.pi * (self.diameter/2)**2
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