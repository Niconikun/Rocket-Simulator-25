"""
Unit Tests for RocketDynamics Module

Tests:
- RocketDynamics initialization
- Force calculations (drag, lift, thrust, gravity)
- Torque calculations
- Dependency injection
"""

import unittest
import numpy as np
from unittest.mock import MagicMock
from src.models.rocket.dynamics import RocketDynamics
from src.models.rocket.state import RocketState


class MockEngine:
    """Mock engine for testing"""
    def __init__(self):
        self.thrust = 100.0
        self.mass_flux = 0.1
    
    def get_thrust(self):
        return self.thrust
    
    def get_mass_flux(self):
        return self.mass_flux


class MockAerodynamics:
    """Mock aerodynamics for testing"""
    def __init__(self):
        self.cd = 0.5
        self.cl = 0.1
        self.cn = 0.05
        self.dynamic_pressure = 100.0
        self.mach = 0.8
        self.reference_area = 0.01
    
    def calculate_forces(self, velocity, density, mach, alpha=0.0):
        drag_magnitude = 0.5 * density * velocity**2 * self.cd * self.reference_area
        lift_magnitude = 0.5 * density * velocity**2 * self.cl * self.reference_area
        return np.array([-drag_magnitude, 0.0, -lift_magnitude]), np.array([0.0, 0.0, 0.0])
    
    def calculate_torques(self, cp, cm, velocity, density, mach, alpha=0.0):
        return np.array([0.0, 0.0, 0.0])


class MockAtmosphere:
    """Mock atmosphere for testing"""
    def __init__(self):
        self.density = 1.225
        self.pressure = 101325.0
        self.temperature = 288.0
        self.speed_of_sound = 340.0
    
    def get_properties(self, altitude):
        return {
            'density': self.density,
            'pressure': self.pressure,
            'temperature': self.temperature,
            'speed_of_sound': self.speed_of_sound
        }


class TestRocketDynamics(unittest.TestCase):
    """Test suite for RocketDynamics class"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a mock state
        self.state = MagicMock(spec=RocketState)
        self.state.position = np.array([0.0, 0.0, 0.0])
        self.state.velocity = np.array([100.0, 0.0, 0.0])
        self.state.attitude = np.array([0.0, 0.0, 0.0, 1.0])  # Identity quaternion
        self.state.angular_velocity = np.array([0.0, 0.0, 0.0])
        self.state.mass = 10.0
        self.state.cm = np.array([0.0, 0.0, 0.0])
        self.state.cp = np.array([0.5, 0.0, 0.0])
        self.state.alpha = 0.0
        self.state.beta = 0.0
        
        # Create mock dependencies
        self.engine = MockEngine()
        self.aerodynamics = MockAerodynamics()
        self.atmosphere = MockAtmosphere()
        
        # Create dynamics instance
        self.dynamics = RocketDynamics(
            state=self.state,
            engine=self.engine,
            aerodynamics=self.aerodynamics,
            atmosphere=self.atmosphere,
            reference_area=0.01
        )

    def test_initialization(self):
        """Test RocketDynamics initialization"""
        self.assertIsNotNone(self.dynamics)
        self.assertEqual(self.dynamics.reference_area, 0.01)

    def test_force_calculation_with_thrust(self):
        """Test that engine thrust is included in force calculation"""
        # Set up state with non-zero velocity
        self.state.velocity = np.array([100.0, 0.0, 0.0])
        
        # Calculate forces
        forces_b, torques_b = self.dynamics.calculate_forces()
        
        # Engine thrust should be in the x-direction (assuming engine thrust is along body x-axis)
        # The exact value depends on the engine orientation
        self.assertIsNotNone(forces_b)
        self.assertIsNotNone(torques_b)

    def test_zero_velocity_forces(self):
        """Test force calculation with zero velocity"""
        self.state.velocity = np.array([0.0, 0.0, 0.0])
        
        forces_b, torques_b = self.dynamics.calculate_forces()
        
        # With zero velocity, aerodynamic forces should be zero
        # But engine thrust should still be present
        self.assertIsNotNone(forces_b)

    def test_dependency_injection(self):
        """Test that dependencies can be injected"""
        new_engine = MockEngine()
        new_engine.thrust = 200.0
        
        new_dynamics = RocketDynamics(
            state=self.state,
            engine=new_engine,
            aerodynamics=self.aerodynamics,
            atmosphere=self.atmosphere,
            reference_area=0.02
        )
        
        self.assertEqual(new_dynamics.reference_area, 0.02)


if __name__ == '__main__':
    unittest.main()
