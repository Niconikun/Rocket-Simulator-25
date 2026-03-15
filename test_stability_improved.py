#!/usr/bin/env python3
"""
Extended test for quaternion numerical stability in RK4 integration.

This test verifies that the improvements to the Rocket.RK4_update() method
maintain quaternion stability over extended simulation times.
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

logging.basicConfig(level=logging.WARNING)

def run_stability_test(test_duration=1.0):
    """Run a quaternion stability test for a specified duration."""
    
    print(f"\nQuaternion Stability Test - {test_duration} Second(s)")
    print("="*60)
    
    try:
        # Load rocket
        print("Loading rocket configuration...")
        rocket_config_file = 'd:\\Documents\\GitHub\\Rocket-Simulator---GUI\\data\\rockets\\configs\\test_rocket.json'
        
        with open(rocket_config_file, 'r') as f:
            rocket_data = json.load(f)
        
        r_enu_0 = np.array(rocket_data['initial_conditions']['position'])
        v_enu_0 = np.array(rocket_data['initial_conditions']['velocity'])
        q_enu2b_0 = np.array(rocket_data['initial_conditions']['quaternion'])
        w_enu_0 = np.array(rocket_data['initial_conditions']['angular_velocity'])
        initial_mass = rocket_data['properties']['dry_mass'] + rocket_data['propulsion']['propellant_mass']
        
        q_norm = np.linalg.norm(q_enu2b_0)
        q_enu2b_0 = q_enu2b_0 / q_norm if q_norm > 0 else np.array([0, 0, 0, 1])
        
        rocket = Rocket(r_enu_0, v_enu_0, q_enu2b_0, w_enu_0, initial_mass)
        
        props = rocket_data.get('properties', {})
        rocket.dry_mass = props.get('dry_mass', 2.0)
        rocket.inertia_b = np.array(props.get('inertia', [0.01, 0.01, 0.001]))
        rocket.reference_area = props.get('reference_area', 0.01)
        rocket.reference_length = props.get('reference_length', 1.5)
        rocket.cm_b = np.array(props.get('center_of_mass', [0, 0, 0]))
        
        print("OK - Rocket loaded")
        
        # Initialize environment
        print("Initializing environment...")
        planet = Planet(name='Earth')
        atmosphere = Atmosphere(planet)
        clock = Clock()
        print("OK - Environment initialized")
        
        # Run simulation
        print(f"Running simulation...")
        timestep = 0.001
        steps = int(test_duration / timestep)
        
        quaternion_norms = []
        velocity_magnitudes = []
        altitude_history = []
        
        for step in range(steps):
            q_norm = np.linalg.norm(rocket.q_enu2b)
            quaternion_norms.append(q_norm)
            velocity_magnitudes.append(np.linalg.norm(rocket.v_enu))
            altitude_history.append(rocket.r_enu[2])
            
            rocket.RK4_update(timestep)
            rocket.time += timestep
            
            if (step + 1) % max(1, steps // 10) == 0:
                progress = ((step + 1) / steps) * 100
                print(f"Progress: {progress:5.1f}% - q_norm={q_norm:.6f}", end='\r')
        
        print(f"\nOK - {len(quaternion_norms)} steps completed")
        
        # Analyze
        q_norm_min = min(quaternion_norms)
        q_norm_max = max(quaternion_norms)
        q_norm_mean = np.mean(quaternion_norms)
        q_norm_std = np.std(quaternion_norms)
        
        deviations = [abs(q - 1.0) for q in quaternion_norms]
        max_deviation = max(deviations)
        
        max_velocity = max(velocity_magnitudes)
        min_altitude = min(altitude_history)
        max_altitude = max(altitude_history)
        
        print("\nQuaternion Analysis:")
        print(f"  Norm: {q_norm_min:.8f} to {q_norm_max:.8f}")
        print(f"  Mean: {q_norm_mean:.8f}")
        print(f"  StdDev: {q_norm_std:.8f}")
        print(f"  Max Deviation: {max_deviation:.8f}")
        
        print("\nTrajectory:")
        print(f"  Altitude: {min_altitude:.2f} to {max_altitude:.2f} m")
        print(f"  Max Velocity: {max_velocity:.2f} m/s")
        
        # Health check
        if q_norm_min > 0.99:
            health = "EXCELLENT"
        elif q_norm_min > 0.95:
            health = "GOOD"
        elif q_norm_min > 0.5:
            health = "DEGRADED"
        else:
            health = "FAILED"
        
        print(f"\nHealth: {health}")
        
        test_passed = (q_norm_min > 0.95) and (max_deviation < 0.1)
        
        result = {
            'duration': test_duration,
            'steps': len(quaternion_norms),
            'passed': test_passed,
            'q_norm_min': q_norm_min,
            'q_norm_mean': q_norm_mean,
            'max_deviation': max_deviation,
        }
        
        return result
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return {'passed': False, 'error': str(e)}


def main():
    print("\n" + "="*60)
    print("QUATERNION STABILITY TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: 1-second
    print("\n[Test 1/2] Baseline - 1 second")
    result_1s = run_stability_test(1.0)
    results.append(('1s', result_1s))
    
    if result_1s['passed']:
        # Test 2: 10-second
        print("\n[Test 2/2] Extended - 10 seconds")
        result_10s = run_stability_test(10.0)
        results.append(('10s', result_10s))
    else:
        print("\n[Test 2/2] SKIPPED - baseline failed")
        results.append(('10s', {'passed': False}))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, result in results:
        status = "[PASS]" if result.get('passed', False) else "[FAIL]"
        if result.get('error'):
            print(f"{name:5s} - {status:10s} ERROR: {result['error']}")
        elif result.get('passed'):
            dev_pct = result['max_deviation'] * 100
            print(f"{name:5s} - {status:10s} (deviation={dev_pct:.4f}%)")
        else:
            print(f"{name:5s} - {status:10s}")
        
        if not result.get('passed'):
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\nSUCCESS: All quaternion stability tests passed!")
    else:
        print("\nFAILURE: Some tests did not pass")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
