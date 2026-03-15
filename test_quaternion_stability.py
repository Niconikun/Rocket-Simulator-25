#!/usr/bin/env python3
"""
Extended test for quaternion numerical stability in RK4 integration.

This test verifies that the improvements to the Rocket.RK4_update() method
maintain quaternion stability over extended simulation times.

Test Scenarios:
1. 1-second simulation (baseline)
2. 10-second simulation (extended stability test)
3. 30-second simulation (stress test)
"""

import sys
sys.path.insert(0, 'd:\\Documents\\GitHub\\Rocket-Simulator---GUI')

import numpy as np
from src.models.rocket import Rocket
from src.models.planet import Planet
from src.models.atmosphere import Atmosphere
from src.models.clock import Clock
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_stability_test(test_duration=1.0):
    """
    Run a quaternion stability test for a specified duration.
    
    Args:
        test_duration (float): Duration of simulation in seconds
        
    Returns:
        dict: Test results with quaternion health metrics
    """
    
    print(f"\n{'='*70}")
    print(f"QUATERNION STABILITY TEST - {test_duration} SECOND(S)")
    print('='*70)
    
    try:
        # Load rocket
        print(f"Loading rocket configuration...")
        rocket_config_file = 'd:\\Documents\\GitHub\\Rocket-Simulator---GUI\\data\\rockets\\configs\\test_rocket.json'
        
        with open(rocket_config_file, 'r') as f:
            rocket_data = json.load(f)
        
        r_enu_0 = np.array(rocket_data['initial_conditions']['position'])
        v_enu_0 = np.array(rocket_data['initial_conditions']['velocity'])
        q_enu2b_0 = np.array(rocket_data['initial_conditions']['quaternion'])
        w_enu_0 = np.array(rocket_data['initial_conditions']['angular_velocity'])
        initial_mass = rocket_data['properties']['dry_mass'] + rocket_data['propulsion']['propellant_mass']
        
        # Normalize quaternion
        q_norm = np.linalg.norm(q_enu2b_0)
        q_enu2b_0 = q_enu2b_0 / q_norm if q_norm > 0 else np.array([0, 0, 0, 1])
        
        rocket = Rocket(r_enu_0, v_enu_0, q_enu2b_0, w_enu_0, initial_mass)
        
        props = rocket_data.get('properties', {})
        rocket.dry_mass = props.get('dry_mass', 2.0)
        rocket.inertia_b = np.array(props.get('inertia', [0.01, 0.01, 0.001]))
        rocket.reference_area = props.get('reference_area', 0.01)
        rocket.reference_length = props.get('reference_length', 1.5)
        rocket.cm_b = np.array(props.get('center_of_mass', [0, 0, 0]))
        
        print("✓ Rocket loaded")
        
        # Initialize environment
        print("Initializing environment models...")
        planet = Planet(name='Earth')
        atmosphere = Atmosphere(planet)
        clock = Clock()
        print("✓ Environment initialized")
        
        # Run simulation
        print(f"Running simulation...")
        timestep = 0.001  # 1 ms
        steps = int(test_duration / timestep)
        
        quaternion_norms = []
        velocity_magnitudes = []
        altitude_history = []
        error_events = []  # Track any errors
        
        for step in range(steps):
            # Track quaternion norm and velocity
            q_norm = np.linalg.norm(rocket.q_enu2b)
            quaternion_norms.append(q_norm)
            velocity_magnitudes.append(np.linalg.norm(rocket.v_enu))
            altitude_history.append(rocket.r_enu[2])
            
            # Update physics
            try:
                rocket.RK4_update(timestep)
                rocket.time += timestep
            except RuntimeError as e:
                error_events.append({
                    'step': step,
                    'time': rocket.time,
                    'error': str(e)
                })
                print(f"\n✗ Runtime error at step {step} (t={rocket.time:.3f}s): {e}")
                break
            except Exception as e:
                error_events.append({
                    'step': step,
                    'time': rocket.time,
                    'error': str(e)
                })
                print(f"\n✗ Unexpected error at step {step} (t={rocket.time:.3f}s): {e}")
                break
            
            # Progress indicator
            if (step + 1) % max(1, steps // 10) == 0:
                progress = ((step + 1) / steps) * 100
                print(f"   {progress:5.1f}% - q_norm={q_norm:.6f}", end='\r')
        
        print(f"\r✓ Simulation completed - {len(quaternion_norms)} steps executed               ")
        
        # Analyze quaternion stability
        q_norm_min = min(quaternion_norms)
        q_norm_max = max(quaternion_norms)
        q_norm_mean = np.mean(quaternion_norms)
        q_norm_std = np.std(quaternion_norms)
        
        # Quantify deviation from unit norm
        deviations = [abs(q - 1.0) for q in quaternion_norms]
        max_deviation = max(deviations)
        
        # Velocity statistics
        max_velocity = max(velocity_magnitudes)
        min_altitude = min(altitude_history)
        max_altitude = max(altitude_history)
        
        # Assessment
        print(f"\n{'-'*70}")
        print("QUATERNION STABILITY ANALYSIS:")
        print('-'*70)
        print(f"Norm Range:       {q_norm_min:.8f} → {q_norm_max:.8f} (ideal: 1.000000)")
        print(f"Mean:             {q_norm_mean:.8f}")
        print(f"Std Dev:          {q_norm_std:.8f}")
        print(f"Max Deviation:    {max_deviation:.8f}")
        
        # Health indicators
        print(f"\n{'─'*70}")
        print("HEALTH INDICATORS:")
        print('-'*70)
        
        health_ok = True
        
        if q_norm_min > 0.99:
            print(f"✓ Quaternion norm stayed within excellent range (>0.99)")
        elif q_norm_min > 0.95:
            print(f"⚠ Quaternion norm degraded to acceptable range (0.95-0.99)")
        elif q_norm_min > 0.5:
            print(f"✗ Quaternion norm degraded significantly (0.5-0.95)")
            health_ok = False
        else:
            print(f"✗ CRITICAL: Quaternion norm collapsed (<0.5)")
            health_ok = False
        
        if max_deviation < 0.01:
            print(f"✓ Norm deviation from unity very small (<0.01)")
        elif max_deviation < 0.1:
            print(f"⚠ Norm deviation moderate (0.01-0.1)")
        else:
            print(f"✗ Norm deviation excessive (>0.1)")
            health_ok = False
        
        if not error_events:
            print(f"✓ No runtime errors encountered")
        else:
            print(f"✗ {len(error_events)} error(s) encountered during simulation")
            health_ok = False
        
        # Trajectory validation
        print(f"\n{'-'*70}")
        print("TRAJECTORY VALIDATION:")
        print('-'*70)
        print(f"Altitude Range:   {min_altitude:.2f} m to {max_altitude:.2f} m")
        print(f"Max Velocity:     {max_velocity:.2f} m/s")
        
        test_passed = health_ok and len(error_events) == 0
        
        print(f"\n{'─'*70}")
        
        result = {
            'duration': test_duration,
            'steps_completed': len(quaternion_norms),
            'passed': test_passed,
            'q_norm_min': q_norm_min,
            'q_norm_max': q_norm_max,
            'q_norm_mean': q_norm_mean,
            'q_norm_std': q_norm_std,
            'max_deviation': max_deviation,
            'max_velocity': max_velocity,
            'altitude_range': (min_altitude, max_altitude),
            'errors': error_events
        }
        
        return result
        
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return {
            'duration': test_duration,
            'passed': False,
            'error': str(e)
        }


def main():
    """Run all stability tests."""
    
    print("\n")
    print("=" * 70)
    print("QUATERNION NUMERICAL STABILITY TEST SUITE".center(70))
    print("=" * 70)
    
    results = []
    
    # Test 1: 1-second baseline
    print("\n[TEST 1/3] Baseline Test - 1 second")
    print("-" * 70)
    result_1s = run_stability_test(1.0)
    results.append(('1s', result_1s))
    
    if result_1s['passed']:
        # Test 2: 10-second extended
        print("\n[TEST 2/3] Extended Test - 10 seconds")
        print("-" * 70)
        result_10s = run_stability_test(10.0)
        results.append(('10s', result_10s))
        
        if result_10s['passed']:
            # Test 3: 30-second stress
            print("\n[TEST 3/3] Stress Test - 30 seconds")
            print("-" * 70)
            result_30s = run_stability_test(30.0)
            results.append(('30s', result_30s))
    else:
        print("\n⚠ Skipping extended tests - baseline test failed")
        results.append(('10s', {'passed': False, 'skipped': True}))
        results.append(('30s', {'passed': False, 'skipped': True}))
    
    # Summary report
    print("\n\n")
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for name, result in results:
        status = "[PASS]" if result.get('passed', False) else "[FAIL]"
        if result.get('skipped'):
            status = "[SKIP]"
        
        print(f"{name:5s} - {status:10s} ", end='')
        
        if result.get('passed'):
            deviation_pct = result['max_deviation'] * 100
            print(f"(dev={deviation_pct:.4f}%)")
        elif result.get('skipped'):
            print(f"(skipped)")
        else:
            error_msg = result.get('error', 'Unknown error')[:40]
            print(f"({error_msg})")
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n✓ ALL TESTS PASSED - Quaternion stability is maintained!")
    else:
        print("\n✗ SOME TESTS FAILED - See details above")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
