"""
Convergence Tester - Validates numerical stability via timestep refinement

Performs convergence analysis by running same scenario with progressively finer
timesteps and comparing results. Ensures simulation converges to stable solution.
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, time, date
from models.app_state import ApplicationState
from workers.simulation_worker import SimulationWorker

logger = logging.getLogger(__name__)


class ConvergenceTester:
    """Tests numerical convergence of simulation with different timesteps"""
    
    def __init__(self):
        self.results = {}
        self.errors = {}
        self.report = {}
    
    def test_convergence(self, state: ApplicationState, 
                        base_timestep: float = 0.01,
                        runtime: float = 15.0,
                        num_refinements: int = 3) -> Dict:
        """
        Run convergence test with progressively finer timesteps
        
        Args:
            state: ApplicationState with simulation configuration
            base_timestep: Initial timestep (e.g., 0.01 seconds)
            runtime: Duration to simulate (seconds)
            num_refinements: Number of finer timesteps to test (e.g., 3 → 0.01, 0.005, 0.0025)
        
        Returns:
            Convergence analysis report with error metrics
        """
        logger.info("\n" + "="*70)
        logger.info("CONVERGENCE TEST")
        logger.info("="*70)
        logger.info(f"Testing convergence with {num_refinements} timestep refinements")
        logger.info(f"Base timestep: {base_timestep}s, Runtime: {runtime}s")
        
        self.results = {}
        self.errors = {}
        
        # Generate timestep sequence: coarse to fine
        timesteps = [base_timestep / (2**i) for i in range(num_refinements)]
        
        logger.info(f"Timesteps to test: {[f'{ts:.6f}s' for ts in timesteps]}")
        
        # Run simulations with each timestep
        for i, ts in enumerate(timesteps, 1):
            logger.info(f"\n[{i}/{num_refinements}] Running simulation with timestep={ts:.6f}s...")
            
            # Create fresh state for each run
            test_state = ApplicationState()
            test_state._state = state._state.copy()
            test_state.set('sim_time_step', ts)
            test_state.set('sim_runtime', runtime)
            
            # Run simulation
            worker = SimulationWorker(test_state)
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
                logger.error(f"Simulation failed: {error_msg}")
                self.report['status'] = 'FAILED'
                self.report['error'] = error_msg
                return self.report
            
            if results:
                self.results[ts] = results
                metrics = results.get('metrics', {})
                logger.info(f"  Max altitude: {metrics.get('max_altitude', 0):.2f}m")
                logger.info(f"  Max velocity: {metrics.get('max_velocity', 0):.2f}m/s")
                logger.info(f"  Flight duration: {metrics.get('flight_duration', 0):.2f}s")
                logger.info(f"  Steps executed: {results.get('total_steps', 0)}")
        
        # Analyze convergence
        self._analyze_convergence(timesteps)
        
        return self.report
    
    def _analyze_convergence(self, timesteps: List[float]):
        """Analyze convergence between different timestep solutions"""
        
        if len(self.results) < 2:
            self.report = {
                'status': 'INSUFFICIENT_DATA',
                'message': 'Need at least 2 simulations for convergence analysis'
            }
            return
        
        # Extract metrics from simulations
        metrics_keys = ['max_altitude', 'max_velocity', 'flight_duration', 'max_mach', 'max_range']
        
        logger.info(f"\n{'='*70}")
        logger.info("CONVERGENCE ANALYSIS")
        logger.info(f"{'='*70}")
        
        # Build convergence table
        convergence_data = {}
        for metric in metrics_keys:
            convergence_data[metric] = {}
            
            for ts in timesteps:
                if ts in self.results:
                    value = self.results[ts].get('metrics', {}).get(metric, None)
                    convergence_data[metric][ts] = value
        
        # Calculate errors between successive timesteps
        self.report = {
            'status': 'COMPLETE',
            'timesteps': timesteps,
            'convergence': {},
            'metrics_converged': {},
            'all_converged': True
        }
        
        # Display convergence table
        header_parts = [f"{'Metric':<20}", f"{'TS='+f'{timesteps[0]}':<15}"]
        for ts in timesteps[1:]:
            header_parts.append(f"{'TS='+f'{ts:.6f}':<15}")
        header_parts.append(f"{'Error %':<12}")
        logger.info("")
        logger.info("".join(header_parts))
        logger.info("-" * 100)
        
        for metric in metrics_keys:
            values = [convergence_data[metric].get(ts) for ts in timesteps]
            
            # Skip if any values are None
            if any(v is None for v in values):
                continue
            
            # Build row string
            row_parts = [f"{metric:<20}"]
            for v in values:
                row_parts.append(f" {v:<14.4f}")
            
            # Calculate error (relative to finest timestep)
            finest_value = values[-1]
            coarsest_value = values[0]
            
            if finest_value != 0:
                error = abs(coarsest_value - finest_value) / abs(finest_value) * 100
            else:
                error = 0
            
            row_parts.append(f" {error:<11.2f}%")
            logger.info("".join(row_parts))
            
            convergence_data[metric]['error_percent'] = error
            self.report['convergence'][metric] = {
                'values': values,
                'error_percent': error,
                'converged': error < 2.0  # 2% tolerance
            }
            
            if error >= 2.0:
                self.report['all_converged'] = False
                logger.warning(f"  ⚠ {metric}: Error {error:.2f}% exceeds 2% threshold")
            else:
                logger.info(f"  ✓ {metric}: Converged ({error:.2f}% error)")
        
        # Summary
        logger.info(f"\n{'='*70}")
        logger.info("CONVERGENCE SUMMARY")
        logger.info(f"{'='*70}")
        
        converged_count = sum(1 for m in self.report['convergence'].values() if m.get('converged'))
        total_count = len(self.report['convergence'])
        
        logger.info(f"Metrics converged: {converged_count}/{total_count}")
        
        if self.report['all_converged']:
            logger.info("✓ CONVERGENT: Solution stable with timestep refinement")
        else:
            logger.warning("✗ NON-CONVERGENT: Solution varies with timestep")
            logger.warning("  Recommendation: Use finer timestep for production simulations")
        
        logger.info(f"{'='*70}\n")
    
    def get_report(self) -> Dict:
        """Return convergence analysis report"""
        return self.report
    
    def is_converged(self, tolerance: float = 0.02) -> bool:
        """Check if all metrics converge within tolerance (default 2%)"""
        if self.report.get('status') != 'COMPLETE':
            return False
        
        for metric_data in self.report.get('convergence', {}).values():
            if metric_data.get('error_percent', 0) > tolerance * 100:
                return False
        
        return True
    
    def summary(self) -> str:
        """Return human-readable summary"""
        if self.report.get('status') == 'COMPLETE':
            convergence = self.report.get('convergence', {})
            converged = self.report.get('all_converged', False)
            conv_count = sum(1 for m in convergence.values() if m.get('converged'))
            total = len(convergence)
            
            return (
                f"Convergence: {'PASS' if converged else 'FAIL'} "
                f"({conv_count}/{total} metrics converged, error <2%)"
            )
        else:
            return f"Convergence test status: {self.report.get('status', 'UNKNOWN')}"
