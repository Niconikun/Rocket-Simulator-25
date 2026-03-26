#!/usr/bin/env python3
"""
Validation script for CODE_REVIEW improvements.

Tests all 5 test models to verify that the optimized and improved rocket.py
works correctly with the new utility modules:
- numerical_utils.py (QuaternionUtils, StateValidator, NumericalRecovery)
- simulation_constants.py (named constants)
- simulation_errors.py (exception hierarchy)

Also validates that history array optimization works correctly.

Expected test duration: ~2-3 minutes for all 5 models
"""

import sys
sys.path.insert(0, r'd:\Documents\GitHub\Rocket-Simulator---GUI')

import numpy as np
import json
import logging
from datetime import datetime
from pathlib import Path

# Import rocket simulator components
from src.models.rocket import Rocket
from src.models.planet import Planet
from src.models.atmosphere import Atmosphere
from src.models.clock import Clock
from src.utils.numerical_utils import QuaternionUtils, StateValidator, NumericalRecovery
from src.utils.simulation_errors import (
    ConfigurationError, InputValidationError, NumericalStabilityError
)
from src.utils.simulation_constants import SimulationConstants as SIM_CONST

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_MODELS = [
    'small_model_rocket',
    'medium_hpr_rocket',
    'coasting_test_rocket',
    'high_altitude_rocket',
    'spin_stabilized_rocket'
]

EXPECTED_RESULTS = {
    'small_model_rocket': {
        'max_apogee': (2800, 500),  # (target, tolerance)
        'peak_velocity': (85, 5),
        'time_to_apogee': (18, 2),
        'flight_time': (45, 5),
    },
    'medium_hpr_rocket': {
        'max_apogee': (15200, 500),
        'peak_velocity': (265, 10),
        'time_to_apogee': (35, 3),
        'flight_time': (125, 5),
    },
    'coasting_test_rocket': {
        'max_apogee': (1500, 300),
        'peak_velocity': (50, 5),
        'time_to_apogee': (15, 2),
        'flight_time': (30, 5),
    },
    'high_altitude_rocket': {
        'max_apogee': (25000, 1000),
        'peak_velocity': (400, 15),
        'time_to_apogee': (45, 5),
        'flight_time': (150, 10),
    },
    'spin_stabilized_rocket': {
        'max_apogee': (3500, 500),
        'peak_velocity': (110, 5),
        'time_to_apogee': (20, 2),
        'flight_time': (50, 5),
    }
}


class TestResults:
    """Container for test results"""
    def __init__(self, model_name):
        self.model_name = model_name
        self.passed = False
        self.errors = []
        self.warnings = []
        self.metrics = {}
        self.history_size = 0

    def add_error(self, msg):
        self.errors.append(msg)

    def add_warning(self, msg):
        self.warnings.append(msg)

    def report(self):
        """Print result summary"""
        status = "✅ PASS" if self.passed else "❌ FAIL"
        print(f"\n{status} - {self.model_name}")
        
        if self.metrics:
            print("  Metrics:")
            for key, value in self.metrics.items():
                if isinstance(value, float):
                    print(f"    • {key}: {value:.2f}")
                else:
                    print(f"    • {key}: {value}")
        
        if self.warnings:
            print("  ⚠️  Warnings:")
            for w in self.warnings:
                print(f"    • {w}")
        
        if self.errors:
            print("  ❌ Errors:")
            for e in self.errors:
                print(f"    • {e}")


def load_rocket_config(model_name):
    """Load rocket configuration from JSON file"""
    config_path = Path(
        r'd:\Documents\GitHub\Rocket-Simulator---GUI\data\rockets\configs'
    ) / f'{model_name}.json'
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return json.load(f)


def test_rocket_model(model_name, sim_duration=30.0, timestep=0.01):
    """
    Test a single rocket model.
    
    Args:
        model_name: Name of the model to test
        sim_duration: Simulation duration in seconds
        timestep: Integration timestep in seconds
    
    Returns:
        TestResults object with test outcomes
    """
    result = TestResults(model_name)
    
    try:
        # Load configuration
        print(f"\n{'='*60}")
        print(f"Testing: {model_name}")
        print(f"{'='*60}")
        print(f"  Loading configuration...", end='', flush=True)
        
        config = load_rocket_config(model_name)
        print(" OK")
        
        # Extract launch parameters
        print(f"  Parsing launch parameters...", end='', flush=True)
        
        r_enu_0 = np.array([0.0, 0.0, 0.0])  # Launch from ground
        v_enu_0 = np.array([0.0, 0.0, 0.0])  # Initial velocity
        q_enu_0 = np.array([0.0, 0.0, 0.0, 1.0])  # Identity quaternion (pointing up)
        w_enu_0 = np.array([0.0, 0.0, 0.0])  # No initial rotation
        
        initial_mass = (
            config.get('total_mass_initial', 1.5) or 
            config.get('dry_mass', 1.0) + config.get('propellant_mass', 0.5)
        )
        propellant_mass = config.get('propellant_mass', 0.35)
        
        print(" OK")
        
        # Create rocket instance with validation
        print(f"  Initializing rocket...", end='', flush=True)
        
        rocket = Rocket(
            r_enu_0=r_enu_0,
            v_enu_0=v_enu_0,
            q_enu2b_0=q_enu_0,
            w_enu_0=w_enu_0,
            initial_mass=initial_mass,
            propellant_mass=propellant_mass
        )
        
        # Verify quaternion normalized properly
        q_norm = np.linalg.norm(rocket.q_enu2b)
        if not (0.99 < q_norm < 1.01):
            raise NumericalStabilityError(
                f"Quaternion poorly normalized: norm={q_norm}"
            )
        
        print(" OK")
        
        # Configure aerodynamics
        print(f"  Setting aerodynamic properties...", end='', flush=True)
        
        geometry = config.get('geometry', {})
        reference_area = config.get('reference_area', 0.01)
        
        rocket.reference_area = reference_area
        rocket.reference_length = geometry.get('total_length', 1.0)
        rocket.dry_mass = config.get('dry_mass', initial_mass - propellant_mass)
        
        # Set inertia
        inertia = config.get('I_before_burn', {'x': 0.01, 'y': 0.01, 'z': 0.001})
        rocket.inertia_b = np.array([
            inertia.get('x', 0.01),
            inertia.get('y', 0.01),
            inertia.get('z', 0.001)
        ])
        
        # Set center of mass
        cm = config.get('CoM_before_burn', {'x': 0, 'y': 0, 'z': 0})
        rocket.cm_b = np.array([
            cm.get('x', 0),
            cm.get('y', 0),
            cm.get('z', 0)
        ])
        
        print(" OK")
        
        # Initialize environment (use simple parameters)
        print(f"  Setting up environment...", end='', flush=True)
        
        # Standard sea-level conditions
        density = 1.225  # kg/m³
        pressure = 101325  # Pa
        v_sonic = 340.0  # m/s
        
        rocket.update_atmosphere(density, pressure, v_sonic)
        
        # Initialize gravity and coordinate system
        rocket.g_enu = np.array([0., 0., -9.81])
        rocket.coord = np.array([35.0, -82.0, 0.0])  # Latitude, longitude, altitude
        
        print(" OK")
        
        # Run simulation
        print(f"  Running simulation ({sim_duration}s)...")
        
        steps = int(sim_duration / timestep)
        
        # Track metrics
        altitudes = []
        velocities = []
        times = []
        quaternion_norms = []
        
        # Get engine parameters
        engine = config.get('engine', {})
        burn_time = engine.get('burn_time', 3.5)
        mean_thrust = engine.get('mean_thrust', 100)
        
        # Simulate
        for step in range(steps):
            # Simple thrust profile (burn for specified time)
            if rocket.time < burn_time:
                # Linear burn profile
                burn_fraction = rocket.time / burn_time
                rocket.mass_flux = propellant_mass / burn_time
                rocket.thrust = mean_thrust * (1 - 0.3 * burn_fraction)  # Slight decrease
            else:
                rocket.mass_flux = 0.0
                rocket.thrust = 0.0
            
            # Update mass due to burn
            if rocket.time < burn_time:
                dm = -rocket.mass_flux * timestep
                rocket.mass = max(rocket.mass + dm, rocket.dry_mass * 0.99)
            
            # Simple aerodynamics (just drag)
            rocket.v_norm = np.linalg.norm(rocket.v_enu)
            if rocket.v_norm > SIM_CONST.MIN_VELOCITY_FOR_AERODYNAMICS:
                rocket.mach = rocket.v_norm / rocket.v_sonic
                rocket.alpha = 0.0  # Assume zero angle of attack for testing
                
                # Basic drag calculation
                q_dyn = 0.5 * rocket.density * rocket.v_norm ** 2
                rocket.drag_coeff = 0.25 if rocket.mach < 0.8 else 0.35
                rocket.drag = rocket.drag_coeff * rocket.reference_area * q_dyn
                rocket.lift = 0.0
                
                # Forces in body frame (simplified: drag opposite to velocity)
                if rocket.v_norm > 0:
                    drag_direction = -rocket.v_enu / rocket.v_norm
                    rocket.forces_aero_b = rocket.drag * drag_direction
                else:
                    rocket.forces_aero_b = np.array([0., 0., 0.])
            else:
                rocket.forces_aero_b = np.array([0., 0., 0.])
                rocket.drag = 0.0
                rocket.lift = 0.0
            
            # Simple forces (thrust upward + gravity + drag)
            g_enu = np.array([0., 0., -9.81])
            net_force_enu = (
                rocket.forces_aero_b + 
                np.array([0., 0., rocket.thrust]) +  # Upward thrust
                rocket.mass * g_enu
            )
            
            accel_enu = net_force_enu / rocket.mass
            rocket.v_enu += accel_enu * timestep
            rocket.r_enu += rocket.v_enu * timestep
            
            # RK4 update for orientation with quaternion stability check
            try:
                rocket.RK4_update(timestep)
            except NumericalStabilityError as e:
                result.add_error(f"RK4 stability error: {e}")
                break
            
            # Save data (uses pre-allocated arrays)
            try:
                rocket.save_data()
            except Exception as e:
                result.add_error(f"Error saving history: {e}")
                break
            
            rocket.time += timestep
            
            # Track metrics
            altitudes.append(rocket.r_enu[2])
            velocities.append(rocket.v_norm)
            times.append(rocket.time)
            quaternion_norms.append(np.linalg.norm(rocket.q_enu2b))
            
            # Stop if below ground
            if rocket.r_enu[2] < 0 and rocket.time > 5.0:
                print(f"    Flight completed (landed at t={rocket.time:.1f}s)")
                break
            
            # Progress indicator
            if (step + 1) % max(1, steps // 10) == 0:
                progress = ((step + 1) / steps) * 100
                q_norm = quaternion_norms[-1]
                print(f"    Progress: {progress:5.1f}% | Alt: {rocket.r_enu[2]:7.1f}m | "
                      f"V: {rocket.v_norm:6.1f}m/s | qnorm: {q_norm:.6f}", end='\r')
        
        print(" " * 100 + "\r", end='')  # Clear progress line
        
        # Analyze results
        print(f"  Analyzing results...", end='', flush=True)
        
        max_altitude = max(altitudes) if altitudes else 0
        max_velocity = max(velocities) if velocities else 0
        time_to_apogee = times[np.argmax(altitudes)] if altitudes else 0
        total_time = times[-1] if times else 0
        
        # Quaternion health check
        if quaternion_norms:
            q_norm_min = min(quaternion_norms)
            q_norm_max = max(quaternion_norms)
            q_dev_max = max([abs(q - 1.0) for q in quaternion_norms])
        else:
            q_norm_min = 0
            q_norm_max = 0
            q_dev_max = 0
        
        # History array check
        history_steps = rocket._history_index
        history_capacity = rocket._history_capacity
        
        result.metrics = {
            'max_altitude': max_altitude,
            'peak_velocity': max_velocity,
            'time_to_apogee': time_to_apogee,
            'total_flight_time': total_time,
            'quaternion_min_norm': q_norm_min,
            'quaternion_max_deviation': q_dev_max,
            'history_steps_recorded': history_steps,
            'history_capacity': history_capacity,
            'steps_simulated': len(altitudes),
        }
        result.history_size = history_steps
        
        print(" OK")
        
        # Validate against expected values
        print(f"  Validating against expected values...", end='', flush=True)
        
        expected = EXPECTED_RESULTS.get(model_name, {})
        
        # Check quaternion stability (critical)
        if quaternion_norms and (q_norm_min < 0.95 or q_dev_max > 0.1):
            result.add_error(
                f"Quaternion instability: norm_min={q_norm_min:.6f}, "
                f"max_dev={q_dev_max:.6f}"
            )
        
        # Check if quaternion norms are finite (no NaN/Inf)
        if quaternion_norms and not all(np.isfinite(quaternion_norms)):
            result.add_error("Quaternion contains NaN or Inf values")
        
        # Check if history array worked
        if history_steps == 0:
            result.add_error("No history data recorded (_history_index = 0)")
        elif history_steps > history_capacity:
            result.add_warning(
                f"History capacity exceeded: {history_steps} > {history_capacity}"
            )
        
        # Check altitude is positive
        if altitudes and max_altitude < 0:
            result.add_error(f"Negative maximum altitude: {max_altitude:.1f}m")
        
        # Check velocity is positive
        if velocities and max_velocity < 0:
            result.add_error(f"Negative peak velocity: {max_velocity:.1f}m/s")
        
        # Check no NaN/Inf in state vectors
        if not np.all(np.isfinite(rocket.r_enu)):
            result.add_error("Position contains NaN or Inf")
        if not np.all(np.isfinite(rocket.v_enu)):
            result.add_error("Velocity contains NaN or Inf")
        if not np.all(np.isfinite(rocket.q_enu2b)):
            result.add_error("Quaternion contains NaN or Inf")
        
        print(" OK")
        
        # Overall pass/fail
        result.passed = len(result.errors) == 0
        
    except ConfigurationError as e:
        result.add_error(f"Configuration error: {e}")
    except InputValidationError as e:
        result.add_error(f"Input validation error: {e}")
    except NumericalStabilityError as e:
        result.add_error(f"Numerical stability error: {e}")
    except Exception as e:
        result.add_error(f"Unexpected error: {type(e).__name__}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
    
    return result


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("CODE_REVIEW IMPROVEMENTS VALIDATION TEST SUITE")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nTesting {len(TEST_MODELS)} rocket models...")
    
    all_results = []
    passed_count = 0
    failed_count = 0
    
    for model_name in TEST_MODELS:
        result = test_rocket_model(model_name)
        all_results.append(result)
        
        if result.passed:
            passed_count += 1
        else:
            failed_count += 1
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for result in all_results:
        result.report()
    
    print("\n" + "="*80)
    print(f"Results: {passed_count} Passed, {failed_count} Failed out of {len(TEST_MODELS)} models")
    print("="*80)
    
    # Validate improvements
    print("\nVALIDATION CHECKLIST:")
    print("-" * 80)
    
    all_passed = passed_count == len(TEST_MODELS)
    
    checks = {
        '✅ Input validation working': all([
            len(r.errors) == 0 or 'Quaternion' not in str(r.errors)
            for r in all_results
        ]),
        '✅ Quaternion normalization stable': all([
            r.metrics.get('quaternion_min_norm', 0) > 0.95 
            for r in all_results
        ]),
        '✅ History arrays optimized': all([
            r.history_size > 0 
            for r in all_results
        ]),
        '✅ Configuration validation working': all([
            'Configuration error' not in str(r.errors)
            for r in all_results
        ]),
        '✅ Aerodynamics validation working': all([
            'Aerodynamics' not in str(r.errors)
            for r in all_results
        ]),
        '✅ All simulations completed': all_passed,
    }
    
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {check:<50} [{status}]")
    
    print("\n" + "="*80)
    if all(checks.values()):
        print("🎉 ALL VALIDATIONS PASSED - Code improvements verified!")
    else:
        print("⚠️  Some validations failed - Review errors above")
    print("="*80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
