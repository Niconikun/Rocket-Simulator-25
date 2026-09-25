#!/usr/bin/env python3
"""
Test script to verify the factory.py implementation.

This script tests:
1. RocketBuilder class with fluent interface
2. All configuration dataclasses (EngineConfig, ParachuteConfig, etc.)
3. Backward compatibility functions (create_rocket_from_config, etc.)
4. New features (wind_model, parachute support)
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

PASS = "[PASS]"
FAIL = "[FAIL]"


def test_imports():
    """Test that all factory imports work correctly."""
    print("\n" + "="*60)
    print("Testing Factory Imports")
    print("="*60)
    
    try:
        from src.models.rocket.factory import (
            RocketBuilder,
            EngineConfig,
            ParachuteConfig,
            MassPropertiesConfig,
            AerodynamicsConfig,
            create_rocket_from_config,
            create_engine,
            create_aerodynamics,
            create_mass_properties,
            create_wind_model,
            create_parachute,
            load_rocket_config,
            update_rocket_for_step,
            run_simulation,
            RocketConfigurationError,
            RocketFileNotFoundError
        )
        print(f"{PASS} All factory imports successful")
        return True
    except ImportError as e:
        print(f"{FAIL} Failed to import factory modules: {e}")
        return False


def test_engine_config():
    """Test EngineConfig dataclass."""
    print("\n" + "="*60)
    print("Testing EngineConfig")
    print("="*60)
    
    try:
        from src.models.rocket.factory import EngineConfig
        from src.utils.simulation_constants import RocketConstants as RC
        
        # Test default values
        config = EngineConfig(burn_time=10.0)
        assert config.burn_time == 10.0
        assert config.ambient_pressure == RC.DEFAULT_PRESSURE
        assert config.nozzle_exit_diameter == 0.1
        assert config.propellant_mass == 1.5
        print(f"{PASS} EngineConfig default values work")
        
        # Test custom values
        config = EngineConfig(
            burn_time=5.0,
            ambient_pressure=100000.0,
            nozzle_exit_diameter=0.2,
            propellant_mass=2.0
        )
        assert config.burn_time == 5.0
        assert config.ambient_pressure == 100000.0
        assert config.nozzle_exit_diameter == 0.2
        print(f"{PASS} EngineConfig custom values work")
        
        return True
    except Exception as e:
        print(f"{FAIL} EngineConfig test failed: {e}")
        return False


def test_parachute_config():
    """Test ParachuteConfig dataclass."""
    print("\n" + "="*60)
    print("Testing ParachuteConfig")
    print("="*60)
    
    try:
        from src.models.rocket.factory import ParachuteConfig
        from src.utils.simulation_constants import ParachuteConstants as PC
        
        # Test default values
        config = ParachuteConfig()
        assert config.name == PC.DEFAULT_NAME
        assert config.diameter == PC.DEFAULT_DIAMETER
        assert config.Cd == PC.DEFAULT_CD
        print(f"{PASS} ParachuteConfig default values work")
        
        # Test custom values
        config = ParachuteConfig(
            name='Test Chute',
            diameter=2.0,
            Cd=1.8,
            deployment_altitude=200.0
        )
        assert config.name == 'Test Chute'
        assert config.diameter == 2.0
        assert config.Cd == 1.8
        assert config.deployment_altitude == 200.0
        print(f"{PASS} ParachuteConfig custom values work")
        
        return True
    except Exception as e:
        print(f"{FAIL} ParachuteConfig test failed: {e}")
        return False


def test_mass_properties_config():
    """Test MassPropertiesConfig dataclass."""
    print("\n" + "="*60)
    print("Testing MassPropertiesConfig")
    print("="*60)
    
    try:
        from src.models.rocket.factory import MassPropertiesConfig
        
        config = MassPropertiesConfig(
            mass_before=10.0,
            mass_after=8.0,
            cm_before={'x': 0.5, 'y': 0.0, 'z': 0.0},
            cm_after={'x': 0.6, 'y': 0.0, 'z': 0.0},
            inertia_before={'x': 0.1, 'y': 0.1, 'z': 0.05},
            inertia_after={'x': 0.08, 'y': 0.08, 'z': 0.04}
        )
        assert config.mass_before == 10.0
        assert config.mass_after == 8.0
        assert config.cm_before['x'] == 0.5
        print(f"{PASS} MassPropertiesConfig works")
        
        return True
    except Exception as e:
        print(f"{FAIL} MassPropertiesConfig test failed: {e}")
        return False


def test_rocket_builder_basic():
    """Test basic RocketBuilder functionality."""
    print("\n" + "="*60)
    print("Testing RocketBuilder - Basic Creation")
    print("="*60)
    
    try:
        from src.models.rocket.factory import RocketBuilder, EngineConfig
        
        # Test builder initialization
        builder = RocketBuilder()
        print(f"{PASS} RocketBuilder initialized")
        
        # Test fluent interface
        rocket = (builder
            .with_position(np.array([0, 0, 0]))
            .with_velocity(np.array([0, 0, 10]))
            .with_attitude(np.array([0, 0, 0, 1]))
            .with_angular_velocity(np.array([0, 0, 0]))
            .with_engine_config(EngineConfig(burn_time=5.0))
            .build())
        
        assert rocket is not None
        assert hasattr(rocket, 'position')
        assert hasattr(rocket, 'velocity')
        assert hasattr(rocket, 'step')
        print(f"{PASS} RocketBuilder fluent interface works")
        
        # Test that position and velocity are set correctly
        assert np.allclose(rocket.position, np.array([0, 0, 0]))
        assert np.allclose(rocket.velocity, np.array([0, 0, 10]))
        print(f"{PASS} RocketBuilder sets state correctly")
        
        return True
    except Exception as e:
        print(f"{FAIL} RocketBuilder basic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rocket_builder_with_parachute():
    """Test RocketBuilder with parachute configuration."""
    print("\n" + "="*60)
    print("Testing RocketBuilder - With Parachute")
    print("="*60)
    
    try:
        from src.models.rocket.factory import RocketBuilder, EngineConfig, ParachuteConfig
        
        # Create rocket with parachute config
        rocket = (RocketBuilder()
            .with_position(np.array([0, 0, 0]))
            .with_velocity(np.array([0, 0, 10]))
            .with_attitude(np.array([0, 0, 0, 1]))
            .with_angular_velocity(np.array([0, 0, 0]))
            .with_engine_config(EngineConfig(burn_time=5.0))
            .with_parachute_config(ParachuteConfig(
                diameter=1.5,
                Cd=1.8,
                deployment_altitude=200.0
            ))
            .build())
        
        assert rocket.parachute is not None
        print(f"{PASS} RocketBuilder creates parachute from config")
        
        return True
    except Exception as e:
        print(f"{FAIL} RocketBuilder parachute test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rocket_builder_validation():
    """Test RocketBuilder validation."""
    print("\n" + "="*60)
    print("Testing RocketBuilder - Validation")
    print("="*60)
    
    try:
        from src.models.rocket.factory import RocketBuilder, RocketConfigurationError
        
        # Test missing position
        builder = RocketBuilder()
        try:
            rocket = (builder
                .with_velocity(np.array([0, 0, 10]))
                .with_attitude(np.array([0, 0, 0, 1]))
                .with_angular_velocity(np.array([0, 0, 0]))
                .build())
            print(f"{FAIL} Should have raised RocketConfigurationError for missing position")
            return False
        except RocketConfigurationError as e:
            print(f"{PASS} Validation catches missing position")
        
        # Test missing velocity
        try:
            rocket = (builder
                .with_position(np.array([0, 0, 0]))
                .with_attitude(np.array([0, 0, 0, 1]))
                .with_angular_velocity(np.array([0, 0, 0]))
                .build())
            print(f"{FAIL} Should have raised RocketConfigurationError for missing velocity")
            return False
        except RocketConfigurationError:
            print(f"{PASS} Validation catches missing velocity")
        
        # Test invalid vector dimensions
        try:
            rocket = (builder
                .with_position(np.array([0, 0, 0, 0]))  # 4 elements instead of 3
                .with_velocity(np.array([0, 0, 10]))
                .with_attitude(np.array([0, 0, 0, 1]))
                .with_angular_velocity(np.array([0, 0, 0]))
                .build())
            print(f"{FAIL} Should have raised RocketConfigurationError for invalid position dimension")
            return False
        except RocketConfigurationError:
            print(f"{PASS} Validation catches invalid position dimension")
        
        return True
    except Exception as e:
        print(f"{FAIL} RocketBuilder validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test backward compatibility with create_rocket_from_config."""
    print("\n" + "="*60)
    print("Testing Backward Compatibility")
    print("="*60)
    
    try:
        from src.models.rocket.factory import create_rocket_from_config, RocketFileNotFoundError
        
        # Test with non-existent config (should raise error)
        try:
            rocket, config, engine, aero, atmosphere = create_rocket_from_config(
                r_enu_0=np.array([0, 0, 0]),
                v_enu_0=np.array([0, 0, 10]),
                q_enu2b_0=np.array([0, 0, 0, 1]),
                w_enu_0=np.array([0, 0, 0]),
                initial_mass=10.0,
                rocket_name='non_existent_rocket'
            )
            print(f"{FAIL} Should have raised RocketFileNotFoundError")
            return False
        except RocketFileNotFoundError:
            print(f"{PASS} create_rocket_from_config raises RocketFileNotFoundError for missing config")
        
        # Test that we can call the function (we can't test with actual config without the file)
        print(f"{PASS} create_rocket_from_config is callable")
        
        return True
    except Exception as e:
        print(f"{FAIL} Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_factory_utility_functions():
    """Test factory utility functions."""
    print("\n" + "="*60)
    print("Testing Factory Utility Functions")
    print("="*60)
    
    try:
        from src.models.rocket.factory import (
            create_engine,
            create_aerodynamics,
            create_mass_properties,
            create_wind_model,
            create_parachute
        )
        from src.models.atmosphere import Atmosphere
        
        # Test create_engine
        engine_data = {
            'burn_time': 5.0,
            'nozzle_exit_diameter': 0.1,
            'propellant_mass': 1.5,
            'specific_impulse': 250.0,
            'mean_thrust': 1000.0,
            'max_thrust': 1200.0,
            'mean_chamber_pressure': 1000000.0,
            'max_chamber_pressure': 1200000.0,
            'thrust_to_weight_ratio': 50.0
        }
        engine = create_engine(engine_data)
        assert engine is not None
        print(f"{PASS} create_engine works")
        
        # Test create_aerodynamics
        atmosphere = Atmosphere(15.0)
        aero = create_aerodynamics(
            mach=0.0,
            angle_attack=0.0,
            height=0.0,
            atmosphere=atmosphere,
            rocket_config={},
            mass_props_before={'x': 0.5, 'y': 0.0, 'z': 0.0},
            mass_props_after={'x': 0.6, 'y': 0.0, 'z': 0.0}
        )
        assert aero is not None
        print(f"{PASS} create_aerodynamics works")
        
        # Test create_mass_properties
        mass_props = create_mass_properties(
            initial_mass=10.0,
            propellant_mass=1.5,
            com_before={'x': 0.5, 'y': 0.0, 'z': 0.0},
            inertia_before={'x': 0.1, 'y': 0.1, 'z': 0.05},
            com_after={'x': 0.6, 'y': 0.0, 'z': 0.0},
            inertia_after={'x': 0.08, 'y': 0.08, 'z': 0.04}
        )
        assert mass_props is not None
        print(f"{PASS} create_mass_properties works")
        
        # Test create_wind_model
        wind_model = create_wind_model({'model_type': 'constant', 'wind_speed': 5.0})
        assert wind_model is not None
        print(f"{PASS} create_wind_model works")
        
        # Test create_parachute
        parachute = create_parachute({
            'name': 'Test Chute',
            'diameter': 1.0,
            'Cd': 1.5,
            'deployment_altitude': 300.0
        })
        assert parachute is not None
        print(f"{PASS} create_parachute works")
        
        return True
    except Exception as e:
        print(f"{FAIL} Factory utility functions test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rocket_simulation():
    """Test that a rocket created with the factory can be simulated."""
    print("\n" + "="*60)
    print("Testing Rocket Simulation")
    print("="*60)
    
    try:
        from src.models.rocket.factory import RocketBuilder, EngineConfig, ParachuteConfig
        
        # Create a rocket with the builder
        rocket = (RocketBuilder()
            .with_position(np.array([0, 0, 0]))
            .with_velocity(np.array([0, 0, 10]))
            .with_attitude(np.array([0, 0, 0, 1]))
            .with_angular_velocity(np.array([0, 0, 0]))
            .with_engine_config(EngineConfig(burn_time=5.0))
            .with_initial_mass(10.0)
            .with_reference_area(0.01)
            .build())
        
        # Test initial state
        assert rocket.time == 0.0
        assert rocket.mass == 10.0
        print(f"{PASS} Initial rocket state is correct")
        
        # Run a few steps
        for i in range(10):
            rocket.step(dt=0.1)
        
        # Check that time advanced
        assert rocket.time > 0.0
        print(f"{PASS} Rocket simulation advances time")
        
        # Check that mass decreased (due to propellant burn)
        assert rocket.mass < 10.0
        print(f"{PASS} Rocket mass decreases during burn")
        
        return True
    except Exception as e:
        print(f"{FAIL} Rocket simulation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("FACTORY IMPLEMENTATION TEST SUITE")
    print("="*60)
    
    tests = [
        ('Factory Imports', test_imports),
        ('EngineConfig', test_engine_config),
        ('ParachuteConfig', test_parachute_config),
        ('MassPropertiesConfig', test_mass_properties_config),
        ('RocketBuilder Basic', test_rocket_builder_basic),
        ('RocketBuilder with Parachute', test_rocket_builder_with_parachute),
        ('RocketBuilder Validation', test_rocket_builder_validation),
        ('Backward Compatibility', test_backward_compatibility),
        ('Factory Utility Functions', test_factory_utility_functions),
        ('Rocket Simulation', test_rocket_simulation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n{FAIL} Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = PASS if result else FAIL
        print(f"{status} {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "="*60)
        print(f"{PASS} ALL TESTS PASSED!")
        print("="*60)
        print("\nFactory implementation (Phase 3 Task 3.1) is complete and working.")
        return 0
    else:
        print("\n" + "="*60)
        print(f"{FAIL} SOME TESTS FAILED")
        print("="*60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
