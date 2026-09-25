#!/usr/bin/env python3
"""
Phase 2 Test Suite

This test suite verifies that all Phase 2 components work correctly:
1. MassProperties class
2. RocketState class
3. RocketDynamics class
4. RocketSimulation class
5. Rocket class (composition root)
6. Dependency injection works correctly
"""

import numpy as np
import sys

PASS = "[PASS]"
FAIL = "[FAIL]"


def test_mass_properties():
    """Test MassProperties class."""
    print("\n" + "="*60)
    print("Testing MassProperties...")
    print("="*60)
    
    try:
        from src.models.mass_properties import MassProperties, SimpleMassProperties
        
        # Test MassProperties
        mass_props = MassProperties(
            mass_before=10.0,
            mass_after=7.0,
            cm_before=np.array([0.5, 0, 0]),
            cm_after=np.array([0.6, 0, 0]),
            inertia_before=np.array([0.1, 0.1, 0.05]),
            inertia_after=np.array([0.08, 0.08, 0.04])
        )
        
        # Test mass interpolation
        assert abs(mass_props.get_mass(0.0) - 10.0) < 1e-6, "Mass at 0% burn should be 10.0"
        assert abs(mass_props.get_mass(1.0) - 7.0) < 1e-6, "Mass at 100% burn should be 7.0"
        assert abs(mass_props.get_mass(0.5) - 8.5) < 1e-6, "Mass at 50% burn should be 8.5"
        
        # Test CoM interpolation
        com_0 = mass_props.get_center_of_mass(0.0)
        com_1 = mass_props.get_center_of_mass(1.0)
        assert np.allclose(com_0, [0.5, 0, 0]), "CoM at 0% burn should be [0.5, 0, 0]"
        assert np.allclose(com_1, [0.6, 0, 0]), "CoM at 100% burn should be [0.6, 0, 0]"
        
        # Test inertia interpolation
        inertia_0 = mass_props.get_inertia(0.0)
        inertia_1 = mass_props.get_inertia(1.0)
        assert np.allclose(inertia_0, [0.1, 0.1, 0.05]), "Inertia at 0% burn incorrect"
        assert np.allclose(inertia_1, [0.08, 0.08, 0.04]), "Inertia at 100% burn incorrect"
        
        # Test propellant mass
        assert abs(mass_props.get_propellant_mass() - 3.0) < 1e-6, "Propellant mass should be 3.0"
        
        # Test SimpleMassProperties
        simple_props = SimpleMassProperties(
            mass=10.0,
            center_of_mass=np.array([0.5, 0, 0]),
            inertia=np.array([0.1, 0.1, 0.05])
        )
        assert simple_props.get_mass(0.5) == 10.0, "SimpleMassProperties mass should be constant"
        
        print(f"{PASS} MassProperties tests passed")
        return True
        
    except Exception as e:
        print(f"{FAIL} MassProperties tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rocket_state():
    """Test RocketState class."""
    print("\n" + "="*60)
    print("Testing RocketState...")
    print("="*60)
    
    try:
        from src.models.rocket.state import RocketState
        
        # Test creation
        state = RocketState(
            r_enu=np.array([0, 0, 0]),
            v_enu=np.array([0, 0, 10]),
            q_enu2b=np.array([0, 0, 0, 1]),
            w_enu=np.array([0, 0, 0]),
            mass=10.0
        )
        
        # Test properties
        assert np.allclose(state.r_enu, [0, 0, 0]), "Position incorrect"
        assert np.allclose(state.v_enu, [0, 0, 10]), "Velocity incorrect"
        assert state.mass == 10.0, "Mass incorrect"
        assert state.time == 0.0, "Time incorrect"
        
        # Test derived properties
        assert abs(state.v_norm - 10.0) < 1e-6, "Velocity norm should be 10.0"
        
        # Test setters
        state.r_enu = np.array([1, 2, 3])
        assert np.allclose(state.r_enu, [1, 2, 3]), "Position setter failed"
        
        state.mass = 9.5
        assert state.mass == 9.5, "Mass setter failed"
        
        # Test copy
        state_copy = state.copy()
        assert np.allclose(state_copy.r_enu, state.r_enu), "Copy failed"
        assert state_copy is not state, "Copy should create new object"
        
        # Test serialization
        state_dict = state.to_dict()
        state_restored = RocketState.from_dict(state_dict)
        assert np.allclose(state_restored.r_enu, state.r_enu), "Serialization failed"
        
        print(f"{PASS} RocketState tests passed")
        return True
        
    except Exception as e:
        print(f"{FAIL} RocketState tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_atmosphere():
    """Test Atmosphere with IAtmosphere interface."""
    print("\n" + "="*60)
    print("Testing Atmosphere...")
    print("="*60)
    
    try:
        from src.models.atmosphere import Atmosphere
        from src.models.interfaces import IAtmosphere
        
        # Test interface compliance
        atmos = Atmosphere(15.0)
        assert issubclass(Atmosphere, IAtmosphere), "Atmosphere should implement IAtmosphere"
        
        # Test methods exist
        assert hasattr(atmos, 'give_dens'), "Missing give_dens method"
        assert hasattr(atmos, 'give_temp'), "Missing give_temp method"
        assert hasattr(atmos, 'give_v_sonic'), "Missing give_v_sonic method"
        assert hasattr(atmos, 'give_pressure'), "Missing give_pressure method"
        
        # Test values at sea level
        density = atmos.give_dens(0)
        temp = atmos.give_temp(0)
        pressure = atmos.give_pressure(0)
        v_sonic = atmos.give_v_sonic(0)
        
        assert density > 0, "Density should be positive at sea level"
        assert temp > 0, "Temperature should be positive at sea level"
        assert pressure > 0, "Pressure should be positive at sea level"
        assert v_sonic > 0, "Speed of sound should be positive at sea level"
        
        print(f"{PASS} Atmosphere tests passed")
        print(f"  Sea level: density={density:.4f} kg/m3, temp={temp:.1f} K")
        print(f"             pressure={pressure:.1f} Pa, v_sonic={v_sonic:.1f} m/s")
        return True
        
    except Exception as e:
        print(f"{FAIL} Atmosphere tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_engine():
    """Test EnhancedEngine with IEngine interface."""
    print("\n" + "="*60)
    print("Testing EnhancedEngine...")
    print("="*60)
    
    try:
        from src.models.engine import EnhancedEngine
        from src.models.interfaces import IEngine
        
        # Test interface compliance
        assert issubclass(EnhancedEngine, IEngine), "EnhancedEngine should implement IEngine"
        
        # Test creation
        engine = EnhancedEngine(
            time=0.0,
            burn_time=10.0,
            ambient_pressure=101325.0,
            nozzle_exit_diameter=0.1,
            propellant_mass=3.0,
            specific_impulse=250.0,
            mean_thrust=1000.0,
            max_thrust=1200.0,
            mean_chamber_pressure=1000000.0,
            max_chamber_pressure=1200000.0,
            thrust_to_weight_ratio=50.0
        )
        
        # Test interface methods
        assert hasattr(engine, 'update'), "Missing update method"
        assert hasattr(engine, 'get_performance_metrics'), "Missing get_performance_metrics method"
        assert hasattr(engine, 'get_thrust'), "Missing get_thrust method"
        assert hasattr(engine, 'get_mass_flow'), "Missing get_mass_flow method"
        
        # Test method calls
        metrics = engine.get_performance_metrics()
        assert 'thrust' in metrics, "Metrics should contain thrust"
        assert 'mass_flow' in metrics, "Metrics should contain mass_flow"
        
        thrust = engine.get_thrust()
        mass_flow = engine.get_mass_flow()
        
        print(f"{PASS} EnhancedEngine tests passed")
        print(f"  Initial thrust: {thrust:.1f} N")
        print(f"  Initial mass flow: {mass_flow:.4f} kg/s")
        return True
        
    except Exception as e:
        print(f"{FAIL} EnhancedEngine tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rocket():
    """Test Rocket class with all dependencies."""
    print("\n" + "="*60)
    print("Testing Rocket (Composition Root)...")
    print("="*60)
    
    try:
        from src.models.rocket import Rocket
        from src.models.engine import EnhancedEngine
        from src.models.atmosphere import Atmosphere
        from src.models.interfaces import IAerodynamics
        
        # Create a simple aerodynamics implementation
        class SimpleAerodynamics(IAerodynamics):
            def __init__(self):
                self._cd = 0.5
                self._cl = 0.0
                self._xcp = np.array([0.5, 0, 0])
                self._stability_margin = 1.0
            
            def update(self, mach, angle_attack, height, density):
                self._cd = 0.5
                self._cl = 0.01 * angle_attack
            
            def get_coefficients(self):
                return self._cd, self._cl
            
            def get_center_of_pressure(self):
                return self._xcp.copy()
            
            def get_stability_margin(self):
                return self._stability_margin
            
            def get_aerodynamic_forces(self, dynamic_pressure, reference_area):
                cd, cl = self.get_coefficients()
                drag = cd * dynamic_pressure * reference_area
                lift = cl * dynamic_pressure * reference_area
                return {
                    'drag': drag,
                    'lift': lift,
                    'cd': cd,
                    'cl': cl,
                    'cp_position': self._xcp.copy(),
                    'stability_margin': self._stability_margin
                }
        
        # Create dependencies
        engine = EnhancedEngine(
            time=0.0,
            burn_time=10.0,
            ambient_pressure=101325.0,
            nozzle_exit_diameter=0.1,
            propellant_mass=3.0,
            specific_impulse=250.0,
            mean_thrust=1000.0,
            max_thrust=1200.0,
            mean_chamber_pressure=1000000.0,
            max_chamber_pressure=1200000.0,
            thrust_to_weight_ratio=50.0
        )
        
        atmos = Atmosphere(15.0)
        aero = SimpleAerodynamics()
        
        # Create rocket with dependency injection
        rocket = Rocket(
            r_enu_0=np.array([0, 0, 0]),
            v_enu_0=np.array([0, 0, 10]),
            q_enu2b_0=np.array([0, 0, 0, 1]),
            w_enu_0=np.array([0, 0, 0]),
            initial_mass=10.0,
            engine=engine,
            aerodynamics=aero,
            atmosphere=atmos,
            reference_area=0.01
        )
        
        # Test initial state
        assert np.allclose(rocket.position, [0, 0, 0]), "Initial position should be [0, 0, 0]"
        assert np.allclose(rocket.velocity, [0, 0, 10]), "Initial velocity should be [0, 0, 10]"
        assert rocket.mass == 10.0, "Initial mass should be 10.0"
        assert rocket.time == 0.0, "Initial time should be 0.0"
        
        # Test simulation step
        initial_position = rocket.position.copy()
        rocket.step(dt=0.1)
        
        assert rocket.time > 0, "Time should advance"
        assert rocket.simulation.step_count == 1, "Step count should increment"
        
        # Position should change (rocket is moving)
        assert not np.allclose(rocket.position, initial_position), "Position should change after step"
        
        # Test multiple steps
        for i in range(9):
            rocket.step(dt=0.1)
        
        assert abs(rocket.time - 1.0) < 1e-6, "Time should be ~1.0 after 10 steps of 0.1s"
        assert rocket.simulation.step_count == 10, "Step count should be 10"
        
        # Test dependency setters
        new_engine = EnhancedEngine(
            time=0.0,
            burn_time=5.0,
            ambient_pressure=101325.0,
            nozzle_exit_diameter=0.1,
            propellant_mass=2.0,
            specific_impulse=300.0,
            mean_thrust=1500.0,
            max_thrust=1800.0,
            mean_chamber_pressure=1000000.0,
            max_chamber_pressure=1200000.0,
            thrust_to_weight_ratio=60.0
        )
        rocket.set_engine(new_engine)
        assert rocket.engine is new_engine, "Engine setter failed"
        
        print(f"{PASS} Rocket tests passed")
        print(f"  Initial position: {initial_position}")
        print(f"  After 10 steps: position={rocket.position}")
        print(f"  Final time: {rocket.time:.2f} s")
        return True
        
    except Exception as e:
        print(f"{FAIL} Rocket tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dependency_injection():
    """Test that dependency injection works correctly."""
    print("\n" + "="*60)
    print("Testing Dependency Injection...")
    print("="*60)
    
    try:
        from src.models.rocket import Rocket
        from src.models.engine import EnhancedEngine
        from src.models.atmosphere import Atmosphere
        from src.models.interfaces import IAerodynamics, IEngine, IAtmosphere
        
        # Create a mock engine
        class MockEngine(IEngine):
            def __init__(self):
                self._thrust = 500.0
                self._mass_flow = 0.1
            
            def update(self, time, ambient_pressure=None):
                pass
            
            def get_performance_metrics(self):
                return {'thrust': self._thrust, 'mass_flow': self._mass_flow}
            
            def get_thrust(self):
                return self._thrust
            
            def get_mass_flow(self):
                return self._mass_flow
        
        # Create a mock atmosphere
        class MockAtmosphere(IAtmosphere):
            def give_dens(self, altitude):
                return 1.225  # Sea level density
            
            def give_temp(self, altitude):
                return 288.15  # Sea level temperature
            
            def give_v_sonic(self, altitude):
                return 340.0  # Sea level speed of sound
            
            def give_pressure(self, altitude):
                return 101325.0  # Sea level pressure
        
        # Create a mock aerodynamics
        class MockAerodynamics(IAerodynamics):
            def update(self, mach, angle_attack, height, density):
                pass
            
            def get_coefficients(self):
                return 0.5, 0.0
            
            def get_center_of_pressure(self):
                return np.array([0.5, 0, 0])
            
            def get_stability_margin(self):
                return 1.0
            
            def get_aerodynamic_forces(self, dynamic_pressure, reference_area):
                return {
                    'drag': 0.0,
                    'lift': 0.0,
                    'cd': 0.5,
                    'cl': 0.0,
                    'cp_position': np.array([0.5, 0, 0]),
                    'stability_margin': 1.0
                }
        
        # Create rocket with mock dependencies
        mock_engine = MockEngine()
        mock_atmos = MockAtmosphere()
        mock_aero = MockAerodynamics()
        
        rocket = Rocket(
            r_enu_0=np.array([0, 0, 0]),
            v_enu_0=np.array([0, 0, 10]),
            q_enu2b_0=np.array([0, 0, 0, 1]),
            w_enu_0=np.array([0, 0, 0]),
            initial_mass=10.0,
            engine=mock_engine,
            aerodynamics=mock_aero,
            atmosphere=mock_atmos,
            reference_area=0.01
        )
        
        # Test that mocks are used
        assert rocket.thrust == 500.0, "Mock engine thrust should be used"
        
        print(f"{PASS} Dependency injection tests passed")
        print(f"  Mock engine thrust: {rocket.thrust} N")
        return True
        
    except Exception as e:
        print(f"{FAIL} Dependency injection tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 2 tests."""
    print("\n" + "="*70)
    print("PHASE 2 TEST SUITE")
    print("="*70)
    
    tests = [
        ("MassProperties", test_mass_properties),
        ("RocketState", test_rocket_state),
        ("Atmosphere", test_atmosphere),
        ("Engine", test_engine),
        ("Rocket", test_rocket),
        ("Dependency Injection", test_dependency_injection),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n{FAIL} {name} test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = PASS if result else FAIL
        print(f"{status} {name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "="*70)
        print("ALL PHASE 2 TESTS PASSED!")
        print("Phase 2 (Dependency Injection & Component Split) is complete!")
        print("="*70)
        return 0
    else:
        print("\n" + "="*70)
        print(f"SOME TESTS FAILED ({total - passed} failures)")
        print("="*70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
