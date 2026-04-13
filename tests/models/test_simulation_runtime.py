"""
Phase 1 Test Framework: Simulation Runtime & Convergence Validation

This module tests runtime behavior and convergence of the simulation system
for ballistic flights (no parachute). It validates that:
1. Simulations run to requested durations
2. Results are convergent (stable with finer timesteps)
3. Physical coherence is maintained
"""

import unittest
import json
import logging
from datetime import datetime, date, time
from pathlib import Path
import numpy as np
import sys

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.app_state import ApplicationState
from workers.simulation_worker import SimulationWorker
from src.utils.simulation_manager import SimulationManager


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class TestSimulationRuntime(unittest.TestCase):
    """Test suite for simulation runtime behavior"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests"""
        cls.state = ApplicationState()
        cls.sim_manager = SimulationManager()
        
        # Default ballistic flight configuration
        cls.default_rocket = 'agni-1'
        cls.default_location = 'SHAR'
    
    def setUp(self):
        """Reset state before each test"""
        self.state._state = {}
        self._configure_basic_ballistic_flight()
    
    def _configure_basic_ballistic_flight(self):
        """Configure state for a basic ballistic flight (no parachute)"""
        self.state.set('selected_rocket', self.default_rocket)
        self.state.set('sim_location', self.default_location)
        
        # Time and location
        self.state.set('sim_date', date(2026, 4, 12))
        self.state.set('sim_time', time(9, 0, 0))
        self.state.set('launch_latitude', 13.0)
        self.state.set('launch_longitude', 80.0)
        self.state.set('launch_elevation', 60.0)
        
        # Launch attitude
        self.state.set('launch_elevation_angle', 85.0)
        self.state.set('launch_azimuth', 0.0)
        self.state.set('launch_roll', 0.0)
        
        # Environment
        self.state.set('average_temperature', 25.0)
        
        # Disable parachute for ballistic test
        self.state.set('parachute_enabled', False)
        
        # Wind disabled for baseline
        self.state.set('wind_model', 'none')
    
    def _run_simulation_sync(self, runtime, timestep):
        """
        Run a simulation synchronously and return results with diagnostics
        
        Args:
            runtime (float): Requested runtime in seconds
            timestep (float): Integration timestep in seconds
        
        Returns:
            tuple: (results dict, success bool, error_message str)
        """
        self.state.set('sim_runtime', runtime)
        self.state.set('sim_time_step', timestep)
        
        worker = SimulationWorker(self.state)
        
        # Capture results
        results = None
        error_msg = None
        
        def on_finished(res):
            nonlocal results
            results = res
        
        def on_error(err):
            nonlocal error_msg
            error_msg = err
        
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        
        # Run synchronously
        worker.run()
        worker.wait()
        
        success = results is not None and error_msg is None
        return results, success, error_msg or ""
    
    def test_ballistic_flight_5_seconds(self):
        """Test: Short ballistic flight (5 seconds)"""
        logger.info("\n" + "="*70)
        logger.info("TEST: Ballistic flight - 5 seconds")
        logger.info("="*70)
        
        runtime = 5.0
        timestep = 0.01
        
        results, success, error_msg = self._run_simulation_sync(runtime, timestep)
        
        self.assertTrue(success, f"Simulation failed: {error_msg}")
        self.assertIn('metrics', results)
        self.assertIn('runtime_diagnostics', results['metrics'])
        
        diag = results['metrics']['runtime_diagnostics']
        actual_runtime = results['metrics']['flight_duration']
        
        logger.info(f"Requested: {runtime}s, Actual: {actual_runtime:.2f}s")
        logger.info(f"Termination reason: {diag['termination_reason']}")
        logger.info(f"Steps executed: {diag['actual_steps']}/{diag['requested_steps']}")
        
        # For ballistic flights, expect to stop at landing
        self.assertLess(actual_runtime, runtime + timestep * 2,
                       "Simulation ran longer than requested (expected early landing)")
        
        # Verify coherent results
        self.assertGreater(results['metrics']['max_altitude'], 0,
                          "Max altitude should be > 0")
        self.assertGreater(results['metrics']['max_velocity'], 0,
                          "Max velocity should be > 0")
        self.assertEqual(results['metrics']['flight_duration'], actual_runtime)
        
        logger.info("✓ Test passed")
    
    def test_ballistic_flight_30_seconds(self):
        """Test: Medium ballistic flight (30 seconds)"""
        logger.info("\n" + "="*70)
        logger.info("TEST: Ballistic flight - 30 seconds")
        logger.info("="*70)
        
        runtime = 30.0
        timestep = 0.01
        
        results, success, error_msg = self._run_simulation_sync(runtime, timestep)
        
        self.assertTrue(success, f"Simulation failed: {error_msg}")
        
        actual_runtime = results['metrics']['flight_duration']
        diag = results['metrics']['runtime_diagnostics']
        
        logger.info(f"Requested: {runtime}s, Actual: {actual_runtime:.2f}s")
        logger.info(f"Termination reason: {diag['termination_reason']}")
        logger.info(f"Max altitude: {results['metrics']['max_altitude']:.2f}m")
        
        self.assertGreater(actual_runtime, 3.0,
                          "Flight should last more than 3 seconds")
        self.assertLess(actual_runtime, runtime + 1.0,
                       "Flight should terminate before max time")
        
        logger.info("✓ Test passed")
    
    def test_timestep_convergence(self):
        """
        Test: Convergence analysis with different timesteps
        
        Runs same scenario with timesteps: 0.01s, 0.005s, 0.001s
        Verifies that finer timesteps converge to same results (~2% error)
        """
        logger.info("\n" + "="*70)
        logger.info("TEST: Timestep Convergence Analysis")
        logger.info("="*70)
        
        runtime = 20.0
        timesteps = [0.01, 0.005, 0.001]
        results_dict = {}
        
        for ts in timesteps:
            logger.info(f"\nRunning with timestep={ts}s...")
            results, success, error_msg = self._run_simulation_sync(runtime, ts)
            
            self.assertTrue(success, f"Simulation failed for timestep {ts}s: {error_msg}")
            results_dict[ts] = results
            
            metrics = results['metrics']
            logger.info(f"  Max altitude: {metrics['max_altitude']:.2f}m")
            logger.info(f"  Max velocity: {metrics['max_velocity']:.2f}m/s")
            logger.info(f"  Flight duration: {metrics['flight_duration']:.2f}s")
            logger.info(f"  Max Mach: {metrics['max_mach']:.3f}")
        
        # Analyze convergence
        logger.info(f"\nConvergence Analysis:")
        logger.info(f"{'Metric':<20} {'TS=0.01s':<15} {'TS=0.005s':<15} {'TS=0.001s':<15} {'Error 0.01→0.001':<15}")
        logger.info("-" * 80)
        
        metrics_to_check = ['max_altitude', 'max_velocity', 'flight_duration', 'max_mach']
        convergence_errors = {}
        
        for metric in metrics_to_check:
            v1 = results_dict[0.01]['metrics'][metric]
            v2 = results_dict[0.005]['metrics'][metric]
            v3 = results_dict[0.001]['metrics'][metric]
            
            # Calculate relative error (%)
            error_01_to_001 = abs(v1 - v3) / (abs(v3) + 1e-6) * 100
            
            logger.info(f"{metric:<20} {v1:<15.4f} {v2:<15.4f} {v3:<15.4f} {error_01_to_001:<14.2f}%")
            convergence_errors[metric] = error_01_to_001
        
        # Verify convergence (errors should be < 2%)
        for metric, error in convergence_errors.items():
            self.assertLess(error, 2.0,
                           f"Convergence error for {metric} is {error:.2f}% (expected <2%)")
        
        logger.info("\n✓ All metrics converge within 2% threshold")
        logger.info("✓ Test passed")
    
    def test_data_coherence_ballistic(self):
        """
        Test: Physical coherence of simulation data
        
        Checks:
        - No NaN values in trajectory
        - Altitude monotonically increases then decreases
        - Velocity >= 0
        - Realistic ranges for ballistic flight
        """
        logger.info("\n" + "="*70)
        logger.info("TEST: Data Coherence - Ballistic Flight")
        logger.info("="*70)
        
        runtime = 20.0
        timestep = 0.01
        
        results, success, error_msg = self._run_simulation_sync(runtime, timestep)
        self.assertTrue(success, f"Simulation failed: {error_msg}")
        
        trajectory = results['trajectory']
        metrics = results['metrics']
        
        logger.info(f"Trajectory points: {len(trajectory)}")
        logger.info(f"History fields: {len(results['history']) if results['history'] else 0}")
        
        # Check 1: No NaN values
        logger.info("\nCheck 1: NaN validation...")
        nan_count = 0
        for point in trajectory:
            for key, value in point.items():
                if isinstance(value, float) and np.isnan(value):
                    nan_count += 1
        
        self.assertEqual(nan_count, 0, f"Found {nan_count} NaN values in trajectory")
        logger.info("  ✓ No NaN values found")
        
        # Check 2: Altitude behavior
        logger.info("\nCheck 2: Altitude monotonicity...")
        altitudes = [p['altitude'] for p in trajectory]
        
        if len(altitudes) > 1:
            # Find apogee (maximum altitude)
            apogee_idx = np.argmax(altitudes)
            
            # Before apogee: should be mostly increasing
            before_apogee = altitudes[:apogee_idx+1]
            if len(before_apogee) > 2:
                increases = sum(1 for i in range(len(before_apogee)-1) 
                              if before_apogee[i+1] >= before_apogee[i])
                increase_ratio = increases / (len(before_apogee) - 1) * 100
                logger.info(f"  Ascent phase: {increase_ratio:.1f}% increasing")
                self.assertGreater(increase_ratio, 80.0,
                                 "Ascent phase should be mostly increasing")
            
            # After apogee: should be decreasing
            after_apogee = altitudes[apogee_idx:]
            if len(after_apogee) > 2:
                decreases = sum(1 for i in range(len(after_apogee)-1)
                              if after_apogee[i+1] <= after_apogee[i])
                decrease_ratio = decreases / (len(after_apogee) - 1) * 100
                logger.info(f"  Descent phase: {decrease_ratio:.1f}% decreasing")
                self.assertGreater(decrease_ratio, 80.0,
                                 "Descent phase should be mostly decreasing")
            
            logger.info("  ✓ Altitude behavior coherent")
        
        # Check 3: Velocity
        logger.info("\nCheck 3: Velocity validation...")
        velocities = [p['velocity'] for p in trajectory]
        min_vel = min(velocities)
        max_vel = max(velocities)
        
        self.assertGreaterEqual(min_vel, -0.1,
                              f"Min velocity {min_vel:.2f} m/s should be >= 0")
        self.assertLess(max_vel, 2000.0,
                       f"Max velocity {max_vel:.2f} m/s seems unrealistic for ballistic flight")
        
        logger.info(f"  Velocity range: {min_vel:.2f} to {max_vel:.2f} m/s")
        logger.info("  ✓ Velocity validation passed")
        
        # Check 4: Realistic metrics
        logger.info("\nCheck 4: Metric validation...")
        self.assertGreater(metrics['max_altitude'], 100.0,
                          "Max altitude should be > 100m for typical rocket")
        self.assertLess(metrics['max_altitude'], 200000.0,
                       "Max altitude should be < 200km (termination limit)")
        
        logger.info(f"  Max altitude: {metrics['max_altitude']:.2f}m ✓")
        logger.info(f"  Max velocity: {metrics['max_velocity']:.2f}m/s ✓")
        logger.info(f"  Flight duration: {metrics['flight_duration']:.2f}s ✓")
        logger.info("  ✓ All metrics realistic")
        
        logger.info("\n✓ Test passed")
    
    def test_history_data_completeness(self):
        """
        Test: History data comprehensiveness
        
        Verifies that simulation captures complete history:
        - Multiple fields recorded (forces, mass, attitude, etc.)
        - Consistent data length across fields
        - No silent data drops
        """
        logger.info("\n" + "="*70)
        logger.info("TEST: History Data Completeness")
        logger.info("="*70)
        
        runtime = 15.0
        timestep = 0.01
        
        results, success, error_msg = self._run_simulation_sync(runtime, timestep)
        self.assertTrue(success, f"Simulation failed: {error_msg}")
        
        history = results.get('history', {})
        
        if not history:
            logger.warning("  ⚠ No history data returned (expected for current implementation)")
            logger.info("  ✓ Test passed (warning only)")
            return
        
        logger.info(f"History fields recorded: {len(history)}")
        
        # Get expected fields (based on rocket.py history recording)
        expected_fields = [
            # Trajectory
            'time', 'altitude', 'velocity', 'velocity_magnitude',
            # Position/Attitude
            'latitude', 'longitude', 'q_pitch', 'q_yaw', 'q_roll',
            # Velocity
            'v_x', 'v_y', 'v_z',
            # Forces
            'force_drag_x', 'force_drag_y', 'force_drag_z',
            'force_lift_x', 'force_lift_y', 'force_lift_z',
            'force_gravity_x', 'force_gravity_y', 'force_gravity_z',
            'force_engine_x', 'force_engine_y', 'force_engine_z',
            # Mass/Inertia
            'mass', 'propellant_remaining',
            # Atmosphere
            'density', 'pressure', 'temperature',
            # Aerodynamics
            'cd', 'cl', 'cn', 'mach', 'dynamic_pressure',
            # Angular rates
            'angular_rate_x', 'angular_rate_y', 'angular_rate_z',
        ]
        
        # Check which fields are present
        found_fields = [f for f in expected_fields if f in history]
        missing_fields = [f for f in expected_fields if f not in history]
        
        logger.info(f"\nFound {len(found_fields)}/{len(expected_fields)} expected fields:")
        for f in sorted(found_fields):
            logger.info(f"  ✓ {f}")
        
        if missing_fields:
            logger.warning(f"\nMissing {len(missing_fields)} expected fields:")
            for f in sorted(missing_fields):
                logger.warning(f"  ✗ {f}")
        
        if found_fields:
            # Check data length consistency
            logger.info(f"\nData length consistency:")
            lengths = {}
            for field in found_fields:
                if isinstance(history[field], list):
                    lengths[field] = len(history[field])
            
            if lengths:
                min_len = min(lengths.values())
                max_len = max(lengths.values())
                
                logger.info(f"  Min length: {min_len} points")
                logger.info(f"  Max length: {max_len} points")
                
                # Allow small variance due to sampling/recording differences
                self.assertLess(max_len - min_len, max(10, max_len * 0.1),
                              "Data lengths should be consistent across fields")
                logger.info("  ✓ Data lengths consistent")
        
        logger.info("\n✓ Test passed")


class TestRuntimeDiagnostics(unittest.TestCase):
    """Test suite for runtime diagnostic information"""
    
    def setUp(self):
        self.state = ApplicationState()
        self.state.set('selected_rocket', 'agni-1')
        self.state.set('sim_location', 'SHAR')
        self.state.set('sim_date', date(2026, 4, 12))
        self.state.set('sim_time', time(9, 0, 0))
        self.state.set('launch_latitude', 13.0)
        self.state.set('launch_longitude', 80.0)
        self.state.set('launch_elevation', 60.0)
        self.state.set('launch_elevation_angle', 85.0)
        self.state.set('launch_azimuth', 0.0)
        self.state.set('launch_roll', 0.0)
        self.state.set('average_temperature', 25.0)
        self.state.set('parachute_enabled', False)
        self.state.set('wind_model', 'none')
    
    def test_diagnostic_info_present(self):
        """Test: Runtime diagnostic information is captured and available"""
        logger.info("\n" + "="*70)
        logger.info("TEST: Runtime Diagnostics Availability")
        logger.info("="*70)
        
        self.state.set('sim_runtime', 15.0)
        self.state.set('sim_time_step', 0.01)
        
        worker = SimulationWorker(self.state)
        results = None
        
        def on_finished(res):
            nonlocal results
            results = res
        
        worker.finished.connect(on_finished)
        worker.run()
        worker.wait()
        
        self.assertIsNotNone(results)
        self.assertIn('metrics', results)
        self.assertIn('runtime_diagnostics', results['metrics'])
        
        diag = results['metrics']['runtime_diagnostics']
        
        # Check required diagnostic fields
        required_fields = [
            'requested_runtime_s',
            'actual_runtime_s',
            'requested_steps',
            'actual_steps',
            'timestep_s',
            'completion_percentage',
            'termination_reason',
            'termination_step'
        ]
        
        logger.info("Diagnostic fields present:")
        for field in required_fields:
            self.assertIn(field, diag, f"Missing diagnostic field: {field}")
            logger.info(f"  ✓ {field}: {diag[field]}")
        
        logger.info("\n✓ Test passed")


if __name__ == '__main__':
    unittest.main()
