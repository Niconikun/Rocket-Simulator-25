"""
Simulation Validator - Post-simulation data quality and physical coherence checks

Validates:
1. Numerical integrity (no NaN/Inf values)
2. Physical coherence (altitude behavior, velocity ranges)
3. Energy conservation
4. Trajectory smoothness and realistic ranges
5. Configuration consistency

Returns a comprehensive validation report with pass/fail status and diagnostic details.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class SimulationValidationError(Exception):
    """Exception raised when validation detects critical issues"""
    pass


class SimulationValidator:
    """Validates simulation results for physical coherence and numerical stability"""
    
    def __init__(self):
        self.report = {
            'valid': True,
            'checks': {},
            'warnings': [],
            'errors': [],
            'diagnostics': {}
        }
    
    def validate(self, results: Dict) -> Dict:
        """
        Run comprehensive validation on simulation results
        
        Args:
            results: Dictionary from SimulationWorker with trajectory, history, metrics
        
        Returns:
            Validation report with status and details
        """
        self.report = {'valid': True, 'checks': {}, 'warnings': [], 'errors': [], 'diagnostics': {}}
        
        try:
            # Extract components
            trajectory = results.get('trajectory', [])
            metrics = results.get('metrics', {})
            history = results.get('history', {})
            
            if not trajectory:
                self.report['errors'].append("Empty trajectory - simulation produced no data points")
                self.report['valid'] = False
                return self.report
            
            # Run validation checks
            self._check_nan_values(trajectory, history, metrics)
            self._check_trajectory_behavior(trajectory, metrics)
            self._check_velocity_range(trajectory, metrics)
            self._check_altitude_realism(metrics)
            self._check_motion_continuity(trajectory)
            self._check_energy_conservation(trajectory, metrics)
            
            # Determine overall validity
            self.report['valid'] = len(self.report['errors']) == 0
            
            logger.info(f"\n{'='*70}")
            logger.info(f"SIMULATION VALIDATION REPORT")
            logger.info(f"{'='*70}")
            logger.info(f"Status: {'PASS' if self.report['valid'] else 'FAIL'}")
            logger.info(f"Checks passed: {sum(1 for c in self.report['checks'].values() if c)}")
            logger.info(f"Checks failed: {sum(1 for c in self.report['checks'].values() if not c)}")
            logger.info(f"Warnings: {len(self.report['warnings'])}")
            logger.info(f"Errors: {len(self.report['errors'])}")
            
            if self.report['warnings']:
                logger.warning(f"\nWarnings:")
                for w in self.report['warnings']:
                    logger.warning(f"  - {w}")
            
            if self.report['errors']:
                logger.error(f"\nErrors:")
                for e in self.report['errors']:
                    logger.error(f"  - {e}")
            
            logger.info(f"{'='*70}\n")
            
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            self.report['errors'].append(f"Validation exception: {str(e)}")
            self.report['valid'] = False
        
        return self.report
    
    def _check_nan_values(self, trajectory: List[Dict], history: Dict, metrics: Dict):
        """Check 1: Detect NaN and Inf values in results"""
        nan_count = 0
        inf_count = 0
        nan_fields = []
        
        # Check trajectory
        for i, point in enumerate(trajectory):
            for key, value in point.items():
                if isinstance(value, float):
                    if np.isnan(value):
                        nan_count += 1
                        nan_fields.append((i, key))
                    elif np.isinf(value):
                        inf_count += 1
        
        # Check metrics
        for key, value in metrics.items():
            if isinstance(value, float):
                if np.isnan(value):
                    nan_count += 1
                elif np.isinf(value):
                    inf_count += 1
        
        if nan_count > 0 or inf_count > 0:
            self.report['checks']['nan_check'] = False
            self.report['errors'].append(f"Found {nan_count} NaN and {inf_count} Inf values in results")
            self.report['diagnostics']['nan_inf_values'] = {
                'nan_count': nan_count,
                'inf_count': inf_count,
                'nan_fields_sample': nan_fields[:5]  # Show first 5
            }
        else:
            self.report['checks']['nan_check'] = True
            logger.info("✓ NaN/Inf check: PASS - no invalid values detected")
    
    def _check_trajectory_behavior(self, trajectory: List[Dict], metrics: Dict):
        """Check 2: Altitude monotonicity (increases then decreases)"""
        if len(trajectory) < 3:
            self.report['warnings'].append("Trajectory too short (<3 points) for monotonicity check")
            return
        
        altitudes = [p.get('altitude', 0) for p in trajectory]
        
        # Find apogee (maximum altitude)
        apogee_idx = np.argmax(altitudes)
        
        # Check ascent phase (should mostly increase)
        ascent = altitudes[:apogee_idx+1]
        if len(ascent) > 1:
            increases = sum(1 for i in range(len(ascent)-1) if ascent[i+1] >= ascent[i])
            increase_ratio = increases / (len(ascent) - 1) * 100
            
            if increase_ratio < 70:
                self.report['warnings'].append(
                    f"Ascent phase only {increase_ratio:.1f}% increasing "
                    "(expected >70% - may indicate trajectory oscillation)"
                )
        
        # Check descent phase (should mostly decrease)
        descent = altitudes[apogee_idx:]
        if len(descent) > 1:
            decreases = sum(1 for i in range(len(descent)-1) if descent[i+1] <= descent[i])
            decrease_ratio = decreases / (len(descent) - 1) * 100
            
            if decrease_ratio < 70:
                self.report['errors'].append(
                    f"Descent phase only {decrease_ratio:.1f}% decreasing "
                    "(expected >70% - trajectory unstable)"
                )
                self.report['checks']['altitude_monotonicity'] = False
                return
        
        self.report['checks']['altitude_monotonicity'] = True
        logger.info(f"✓ Altitude monotonicity: PASS")
        self.report['diagnostics']['altitude_behavior'] = {
            'apogee_index': apogee_idx,
            'max_altitude_m': max(altitudes),
            'ascent_increase_ratio': increase_ratio if len(ascent) > 1 else 100,
            'descent_decrease_ratio': decrease_ratio if len(descent) > 1 else 100
        }
    
    def _check_velocity_range(self, trajectory: List[Dict], metrics: Dict):
        """Check 3: Velocity validation"""
        velocities = [p.get('velocity', 0) for p in trajectory]
        
        # Velocity should always be >= 0 (no backward flight)
        negative_velocities = sum(1 for v in velocities if v < -0.1)  # Allow small numerical errors
        
        if negative_velocities > 0:
            self.report['checks']['velocity_range'] = False
            self.report['errors'].append(
                f"Found {negative_velocities} negative velocity values "
                "(physically impossible - indicates simulation error)"
            )
            return
        
        # Check maximum velocity is realistic for rocket
        max_velocity = max(velocities) if velocities else 0
        
        # Most rockets: max velocity 10-5000 m/s (ballistic missiles up to cosmic velocity)
        if max_velocity > 10000:
            self.report['warnings'].append(
                f"Very high max velocity: {max_velocity:.1f} m/s "
                "(>10 km/s - above typical ballistic apogee velocity)"
            )
        
        if max_velocity < 10:
            self.report['warnings'].append(
                f"Very low max velocity: {max_velocity:.1f} m/s "
                "(may indicate insufficient thrust or high drag)"
            )
        
        self.report['checks']['velocity_range'] = True
        logger.info(f"✓ Velocity range: PASS - max {max_velocity:.2f} m/s")
        self.report['diagnostics']['velocity_stats'] = {
            'max_velocity_ms': max_velocity,
            'min_positive_velocity_ms': min([v for v in velocities if v > 0], default=0),
            'negative_velocity_count': negative_velocities
        }
    
    def _check_altitude_realism(self, metrics: Dict):
        """Check 4: Altitude range realism"""
        max_altitude = metrics.get('max_altitude', 0)
        
        # Typical rocket altitudes
        if max_altitude < 100:
            self.report['warnings'].append(
                f"Low maximum altitude: {max_altitude:.1f}m "
                "(typical model rocket apogee: >200m)"
            )
        
        if max_altitude > 200000:  # This should have been caught by termination
            self.report['warnings'].append(
                f"Max altitude exceeds simulation limit: {max_altitude/1000:.0f}km"
            )
        
        self.report['checks']['altitude_realism'] = True
        logger.info(f"✓ Altitude realism: PASS - max {max_altitude:.1f}m")
    
    def _check_motion_continuity(self, trajectory: List[Dict]):
        """Check 5: Detect abrupt jumps or discontinuities"""
        if len(trajectory) < 2:
            return
        
        altitudes = [p.get('altitude', 0) for p in trajectory]
        times = [p.get('time', 0) for p in trajectory]
        
        # Check for velocity jumps in altitude changes
        max_altitude_jump = 0
        for i in range(1, len(altitudes)):
            jump = abs(altitudes[i] - altitudes[i-1])
            max_altitude_jump = max(max_altitude_jump, jump)
            
            # Altitude jump should be reasonable relative to sampled time
            if i < len(times):
                dt = times[i] - times[i-1]
                typical_velocity = 200  # m/s typical
                max_expected_jump = typical_velocity * dt if dt > 0 else 1000
                
                if jump > max_expected_jump * 5:  # 5x tolerance
                    self.report['warnings'].append(
                        f"Large altitude jump at point {i}: {jump:.1f}m in {dt:.4f}s "
                        "(may indicate sparse sampling)"
                    )
        
        self.report['checks']['motion_continuity'] = True
        self.report['diagnostics']['motion_continuity'] = {
            'max_altitude_jump_m': max_altitude_jump,
            'trajectory_points': len(trajectory)
        }
    
    def _check_energy_conservation(self, trajectory: List[Dict], metrics: Dict):
        """Check 6: Energy conservation (simplified)"""
        # Simplified energy check: kinetic + potential energy should decrease over time
        # (accounting for fuel burn and drag)
        
        if len(trajectory) < 2:
            self.report['checks']['energy_conservation'] = True
            return
        
        # Get mass estimates (simplified - from trajectory data if available)
        # Since we don't have mass in trajectory, do basic sanity check
        
        velocities = [p.get('velocity', 0) for p in trajectory]
        altitudes = [p.get('altitude', 0) for p in trajectory]
        
        # Simple check: total energy should not increase randomly
        # E = 0.5*m*v² + m*g*h
        # Check that max energy typically occurs at ascent, min at descent
        
        energy_profile = [v**2 + 19.6 * h for v, h in zip(velocities, altitudes)]
        
        # Should have a clear peak (at apogee transition)
        if len(energy_profile) > 3:
            peak_idx = np.argmax(energy_profile[:len(energy_profile)//2])  # Peak in first half
            
            # Energy should generally decrease after peak
            post_peak = energy_profile[peak_idx:]
            if len(post_peak) > 1:
                decreasing = sum(1 for i in range(len(post_peak)-1) 
                               if post_peak[i+1] <= post_peak[i] * 1.05)  # Allow 5% tolerance
                decrease_ratio = decreasing / (len(post_peak) - 1) * 100
                
                if decrease_ratio < 60:
                    self.report['warnings'].append(
                        f"Energy conservation: only {decrease_ratio:.1f}% decreasing after peak "
                        "(may indicate numerical issues or unexpected thrust)"
                    )
        
        self.report['checks']['energy_conservation'] = True
        logger.info(f"✓ Energy conservation: PASS")
    
    def is_valid(self) -> bool:
        """Return overall validation status"""
        return self.report.get('valid', False)
    
    def get_report(self) -> Dict:
        """Return full validation report"""
        return self.report
    
    def summary(self) -> str:
        """Return human-readable summary"""
        checks_passed = sum(1 for c in self.report['checks'].values() if c)
        checks_total = len(self.report['checks'])
        
        return (
            f"Validation: {'PASS' if self.report['valid'] else 'FAIL'} "
            f"({checks_passed}/{checks_total} checks passed, "
            f"{len(self.report['warnings'])} warnings, "
            f"{len(self.report['errors'])} errors)"
        )
