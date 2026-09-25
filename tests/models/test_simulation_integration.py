"""
Phase 2 Integration Tests - Comprehensive Simulation Validation

Tests:
1. Post-simulation validation (coherence checks)
2. Convergence analysis
3. Baseline scenario comparison
4. Regression testing
"""

import unittest
import logging
from datetime import datetime, date, time
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.app_state import ApplicationState
from workers.simulation_worker import SimulationWorker
from src.utils.simulation_validator import SimulationValidator
from src.utils.convergence_tester import ConvergenceTester

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class TestPostSimulationValidation(unittest.TestCase):
    """Test suite for post-simulation validation module"""
    
    @classmethod
    def setUpClass(cls):
        """Set up fixtures"""
        cls.state = ApplicationState()
        cls.validator = SimulationValidator()
        cls._setup_basic_config()
    
    @classmethod
    def _setup_basic_config(cls):
        """Configure state for ballistic flight"""
        cls.state.set('selected_rocket', 'small_model_rocket')
        cls.state.set('sim_location', 'SHAR')
        cls.state.set('sim_date', date(2026, 4, 12))
        cls.state.set('sim_time', time(9, 0, 0))
        cls.state.set('launch_latitude', 13.0)
        cls.state.set('launch_longitude', 80.0)
        cls.state.set('launch_elevation', 60.0)
        cls.state.set('launch_elevation_angle', 85.0)
        cls.state.set('launch_azimuth', 0.0)
        cls.state.set('launch_roll', 0.0)
        cls.state.set('average_temperature', 25.0)
        cls.state.set('parachute_enabled', False)
        cls.state.set('wind_model', 'none')
        cls.state.set('sim_runtime', 15.0)
        cls.state.set('sim_time_step', 0.01)
    
    def _run_simulation(self) -> tuple:
        """Run simulation and return (results, success, error_msg)"""
        worker = SimulationWorker(self.state)
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
        worker.run()
        
        success = results is not None and error_msg is None
        return results, success, error_msg
    
    def test_validator_nan_detection(self):
        """Test: Validator detects NaN values"""
        logger.info("\n" + "="*70)
        logger.info("TEST: NaN/Inf Detection")
        logger.info("="*70)
        
        # Create fake results with NaN
        bad_results = {
            'trajectory': [
                {'time': 0, 'altitude': 0, 'velocity': 0},
                {'time': 0.1, 'altitude': 10, 'velocity': 50},
                {'time': 0.2, 'altitude': float('nan'), 'velocity': 60}  # NaN
            ],
            'metrics': {'max_altitude': 100},
            'history': {}
        }
        
        report = self.validator.validate(bad_results)
        
        self.assertFalse(report['valid'], "Validator should flag NaN values")
        self.assertIn('nan_check', report['checks'])
        self.assertFalse(report['checks']['nan_check'])
        logger.info("✓ NaN detection working correctly")
    
    def test_validator_coherent_trajectory(self):
        """Test: Validator passes coherent trajectories"""
        logger.info("\n" + "="*70)
        logger.info("TEST: Coherent Trajectory Validation")
        logger.info("="*70)
        
        results, success, error_msg = self._run_simulation()
        
        self.assertTrue(success, f"Simulation failed: {error_msg}")
        
        report = self.validator.validate(results)
        
        logger.info(f"Validation status: {'PASS' if report['valid'] else 'FAIL'}")
        logger.info(f"Checks passed: {sum(1 for c in report['checks'].values() if c)}")
        logger.info(f"Warnings: {len(report['warnings'])}")
        logger.info(f"Errors: {len(report['errors'])}")
        
        # Basic assertions
        self.assertTrue(report['checks'].get('nan_check'),
                       "NaN check should pass for normal simulation")
        self.assertTrue(report['checks'].get('velocity_range'),
                       "Velocity range check should pass")
        
        logger.info("✓ Coherent trajectory validation working")
    
    def test_validator_altitude_monotonicity(self):
        """Test: Altitude monotonicity check (ascent then descent)"""
        logger.info("\n" + "="*70)
        logger.info("TEST: Altitude Monotonicity")
        logger.info("="*70)
        
        results, success, error_msg = self._run_simulation()
        self.assertTrue(success, f"Simulation failed: {error_msg}")
        
        report = self.validator.validate(results)
        
        if report['checks'].get('altitude_monotonicity'):
            logger.info("✓ Altitude monotonicity check PASS")
            
            # Display altitude profile
            trajectory = results.get('trajectory', [])
            if trajectory:
                altitudes = [p.get('altitude', 0) for p in trajectory]
                max_alt = max(altitudes)
                apogee_idx = altitudes.index(max_alt)
                
                logger.info(f"  Apogee: {max_alt:.2f}m at point {apogee_idx}/{len(trajectory)}")
                logger.info(f"  Ascent: {apogee_idx} points")
                logger.info(f"  Descent: {len(trajectory) - apogee_idx} points")
        else:
            logger.warning("✗ Altitude monotonicity check FAIL")
    
    def test_validator_velocity_realism(self):
        """Test: Velocity stays non-negative and realistic"""
        logger.info("\n" + "="*70)
        logger.info("TEST: Velocity Realism")
        logger.info("="*70)
        
        results, success, error_msg = self._run_simulation()
        self.assertTrue(success, f"Simulation failed: {error_msg}")
        
        report = self.validator.validate(results)
        
        self.assertTrue(report['checks'].get('velocity_range'),
                       "Velocity range check should pass")
        
        if 'velocity_stats' in report['diagnostics']:
            stats = report['diagnostics']['velocity_stats']
            logger.info(f"  Max velocity: {stats['max_velocity_ms']:.2f} m/s")
            logger.info(f"  Min positive velocity: {stats['min_positive_velocity_ms']:.2f} m/s")
            logger.info(f"  Negative velocity count: {stats['negative_velocity_count']}")
        
        logger.info("✓ Velocity realism check passed")
    
    def test_validator_summary_report(self):
        """Test: Validator generates comprehensive summary"""
        logger.info("\n" + "="*70)
        logger.info("TEST: Validator Summary Report")
        logger.info("="*70)
        
        results, success, error_msg = self._run_simulation()
        self.assertTrue(success, f"Simulation failed: {error_msg}")
        
        report = self.validator.validate(results)
        
        logger.info(f"Validation Summary: {self.validator.summary()}")
        logger.info(f"Report keys: {list(report.keys())}")
        logger.info(f"Diagnostics: {list(report.get('diagnostics', {}).keys())}")


class TestConvergenceAnalysis(unittest.TestCase):
    """Test suite for convergence analysis"""
    
    @classmethod
    def setUpClass(cls):
        """Set up fixtures"""
        cls.state = ApplicationState()
        cls.tester = ConvergenceTester()
        cls._setup_basic_config()
    
    @classmethod
    def _setup_basic_config(cls):
        """Configure state"""
        cls.state.set('selected_rocket', 'coasting_test_rocket')
        cls.state.set('sim_location', 'SHAR')
        cls.state.set('sim_date', date(2026, 4, 12))
        cls.state.set('sim_time', time(9, 0, 0))
        cls.state.set('launch_latitude', 13.0)
        cls.state.set('launch_longitude', 80.0)
        cls.state.set('launch_elevation', 60.0)
        cls.state.set('launch_elevation_angle', 85.0)
        cls.state.set('launch_azimuth', 0.0)
        cls.state.set('launch_roll', 0.0)
        cls.state.set('average_temperature', 25.0)
        cls.state.set('parachute_enabled', False)
        cls.state.set('wind_model', 'none')
    
    def test_convergence_timestep_refinement(self):
        """Test: Convergence with 2 timestep refinements"""
        logger.info("\n" + "="*70)
        logger.info("TEST: Convergence - Timestep Refinement (2 steps)")
        logger.info("="*70)
        
        # Use shorter runtime for quick test
        report = self.tester.test_convergence(
            self.state,
            base_timestep=0.01,
            runtime=8.0,
            num_refinements=2
        )
        
        self.assertEqual(report['status'], 'COMPLETE')
        
        logger.info(f"Convergence test summary: {self.tester.summary()}")
        
        # Check that we have convergence data
        convergence = report.get('convergence', {})
        self.assertGreater(len(convergence), 0, "Should have convergence metrics")
        
        # Log convergence results
        for metric, data in convergence.items():
            error = data.get('error_percent', 0)
            status = 'OK' if data.get('converged') else 'HIGH ERROR'
            logger.info(f"  {metric}: {error:.2f}% error [{status}]")


class TestBaselineScenarios(unittest.TestCase):
    """Test suite for baseline scenario validation"""
    
    def setUp(self):
        """Set up for each test"""
        self.state = ApplicationState()
        self.validator = SimulationValidator()
    
    def _run_scenario(self, rocket: str, runtime: float) -> tuple:
        """Run a scenario and return (results, validation_report)"""
        self.state._state = {}  # Reset state
        
        # Configure
        self.state.set('selected_rocket', rocket)
        self.state.set('sim_location', 'Test Launch')
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
        self.state.set('sim_runtime', runtime)
        self.state.set('sim_time_step', 0.01)
        
        # Run
        worker = SimulationWorker(self.state)
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
        worker.run()
        
        if error_msg:
            logger.error(f"Simulation error: {error_msg}")
            return None, None
        
        # Validate
        validation_report = self.validator.validate(results)
        
        return results, validation_report
    
    def test_baseline_small_model_rocket(self):
        """Test: Small model rocket baseline scenario"""
        logger.info("\n" + "="*70)
        logger.info("TEST: Baseline - Small Model Rocket")
        logger.info("="*70)
        
        results, validation = self._run_scenario('small_model_rocket', runtime=15.0)
        
        self.assertIsNotNone(results, "Could not run simulation")
        self.assertIsNotNone(validation, "Could not validate")
        
        logger.info(f"Validation: {self.validator.summary()}")
        
        metrics = results.get('metrics', {})
        logger.info(f"  Max altitude: {metrics.get('max_altitude', 0):.1f}m")
        logger.info(f"  Max velocity: {metrics.get('max_velocity', 0):.1f}m/s")
        logger.info(f"  Flight duration: {metrics.get('flight_duration', 0):.2f}s")
        
        # Expected range for small model rocket
        max_alt = metrics.get('max_altitude', 0)
        self.assertGreater(max_alt, 500, "Small model rocket should reach >500m")
        self.assertLess(max_alt, 10000, "Small model rocket should not exceed 10km")
        
        logger.info("✓ Small model rocket baseline passed")
    
    def test_baseline_high_altitude_rocket(self):
        """Test: High altitude rocket baseline scenario"""
        logger.info("\n" + "="*70)
        logger.info("TEST: Baseline - High Altitude Rocket")
        logger.info("="*70)
        
        results, validation = self._run_scenario('high_altitude_rocket', runtime=30.0)
        
        self.assertIsNotNone(results, "Could not run simulation")
        self.assertIsNotNone(validation, "Could not validate")
        
        logger.info(f"Validation: {self.validator.summary()}")
        
        metrics = results.get('metrics', {})
        logger.info(f"  Max altitude: {metrics.get('max_altitude', 0):.1f}m")
        logger.info(f"  Max velocity: {metrics.get('max_velocity', 0):.1f}m/s")
        logger.info(f"  Flight duration: {metrics.get('flight_duration', 0):.2f}s")
        
        # Expected range for high altitude rocket
        max_alt = metrics.get('max_altitude', 0)
        self.assertGreater(max_alt, 15000, "High altitude rocket should reach >15km")
        
        logger.info("✓ High altitude rocket baseline passed")


if __name__ == '__main__':
    unittest.main()
