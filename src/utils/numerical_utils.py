# Author: Code Review Implementation
#         Rocket Simulator Improvements
#         Date: March 26, 2026

"""
Utilities for numerical stability and validation in rocket simulations.

This module provides:
- Safe quaternion normalization with edge case handling
- Input validation framework
- Error recovery mechanisms
- Numerical stability helpers
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)


class QuaternionUtils:
    """Utilities for numerically stable quaternion operations."""
    
    # Configuration constants
    QUATERNION_NORM_MIN = 1e-8
    QUATERNION_NORM_TOLERANCE = 1e-10
    IDENTITY_QUATERNION = np.array([0.0, 0.0, 0.0, 1.0])
    
    @staticmethod
    def normalize(q, min_norm=QUATERNION_NORM_MIN, allow_identity_fallback=True):
        """
        Safely normalize quaternion with Gram-Schmidt orthogonalization.
        
        Uses stable normalization with fallback to identity quaternion
        if norm becomes critically small.
        
        Args:
            q (np.ndarray): Quaternion [q1, q2, q3, q0] (4-element)
            min_norm (float): Minimum allowed norm before emergency reset
            allow_identity_fallback (bool): If True, use identity on failure
        
        Returns:
            np.ndarray: Normalized quaternion with norm ≈ 1.0
        
        Raises:
            ValueError: If norm is invalid and fallback disabled
        """
        if not isinstance(q, np.ndarray) or q.shape != (4,):
            raise ValueError(f"Quaternion must be 4-element numpy array, got {type(q)}")
        
        q_norm = np.linalg.norm(q)
        
        # Check for critically small norm
        if q_norm < min_norm:
            if allow_identity_fallback:
                logger.warning(
                    f"Quaternion norm {q_norm:.2e} critically small, "
                    f"resetting to identity quaternion"
                )
                return QuaternionUtils.IDENTITY_QUATERNION.copy()
            else:
                raise ValueError(
                    f"Quaternion norm {q_norm:.2e} below minimum {min_norm}, "
                    "and fallback disabled"
                )
        
        # Standard normalization
        normalized = q / q_norm
        
        # Validate result
        final_norm = np.linalg.norm(normalized)
        if abs(final_norm - 1.0) > QuaternionUtils.QUATERNION_NORM_TOLERANCE:
            logger.warning(
                f"Quaternion normalization resulted in norm={final_norm:.6f}, "
                f"expected ≈1.0"
            )
        
        return normalized
    
    @staticmethod
    def validate(q, min_norm=QUATERNION_NORM_MIN, tolerance=QUATERNION_NORM_TOLERANCE):
        """
        Check if quaternion is properly normalized and valid.
        
        Args:
            q (np.ndarray): Quaternion to validate
            min_norm (float): Minimum allowed norm
            tolerance (float): Allowed deviation from norm=1.0
        
        Returns:
            tuple: (is_valid, reasons) where reasons is list of issues if not valid
        """
        issues = []
        
        if not isinstance(q, np.ndarray):
            issues.append("Not a numpy array")
            return False, issues
        
        if q.shape != (4,):
            issues.append(f"Shape is {q.shape}, expected (4,)")
        
        if np.any(np.isnan(q)):
            issues.append("Contains NaN values")
        
        if np.any(np.isinf(q)):
            issues.append("Contains Inf values")
        
        q_norm = np.linalg.norm(q)
        
        if q_norm < min_norm:
            issues.append(f"Norm {q_norm:.2e} below minimum {min_norm}")
        
        if abs(q_norm - 1.0) > tolerance:
            issues.append(f"Norm {q_norm:.6f} deviates from 1.0 by {abs(q_norm-1.0):.2e}")
        
        return len(issues) == 0, issues


class StateValidator:
    """Validates rocket state vectors for consistency and bounds."""
    
    # Configuration constants - can be customized per rocket
    MAX_ALTITUDE = 100_000.0          # [m] - 100 km max altitude
    MAX_VELOCITY = 10_000.0            # [m/s] - 10 km/s max velocity
    MIN_MASS_FRACTION = 0.05           # Minimum viable mass (5% of initial)
    MAX_FORCE = 100_000.0              # [N] - 100 kN maximum reasonable force
    
    @staticmethod
    def validate_position(r_enu, max_altitude=MAX_ALTITUDE):
        """
        Validate position vector.
        
        Args:
            r_enu (np.ndarray): Position [east, north, up] in meters
            max_altitude (float): Maximum reasonable altitude [m]
        
        Returns:
            tuple: (is_valid, reason_if_invalid)
        """
        if not isinstance(r_enu, np.ndarray) or r_enu.shape != (3,):
            return False, "Position must be 3-element array"
        
        if np.any(np.isnan(r_enu)):
            return False, "Position contains NaN"
        
        if np.any(np.isinf(r_enu)):
            return False, "Position contains Inf"
        
        altitude = r_enu[2]
        if altitude > max_altitude:
            return False, f"Altitude {altitude:.0f}m exceeds maximum {max_altitude:.0f}m"
        
        # Warn if unreasonably low (below -10 m, underground)
        if altitude < -10:
            logger.warning(f"Position below ground: altitude = {altitude:.1f} m")
        
        return True, None
    
    @staticmethod
    def validate_velocity(v_enu, max_velocity=MAX_VELOCITY):
        """Validate velocity vector."""
        if not isinstance(v_enu, np.ndarray) or v_enu.shape != (3,):
            return False, "Velocity must be 3-element array"
        
        if np.any(np.isnan(v_enu)):
            return False, "Velocity contains NaN"
        
        if np.any(np.isinf(v_enu)):
            return False, "Velocity contains Inf"
        
        v_norm = np.linalg.norm(v_enu)
        if v_norm > max_velocity:
            return False, f"Speed {v_norm:.0f}m/s exceeds maximum {max_velocity:.0f}m/s"
        
        return True, None
    
    @staticmethod
    def validate_mass(mass, initial_mass, propellant_mass):
        """
        Validate mass is within physical bounds.
        
        Args:
            mass (float): Current mass [kg]
            initial_mass (float): Initial mass [kg]
            propellant_mass (float): Propellant mass [kg]
        
        Returns:
            tuple: (is_valid, reason_if_invalid)
        """
        if not isinstance(mass, (int, float)):
            return False, "Mass must be a number"
        
        if np.isnan(mass) or np.isinf(mass):
            return False, "Mass is NaN or Inf"
        
        # Mass must be between dry mass and initial mass
        dry_mass = initial_mass - propellant_mass
        
        if mass < 0:
            return False, f"Mass {mass:.3f}kg is negative"
        
        if mass < dry_mass * 0.9:  # Allow 10% numerical error
            return False, f"Mass {mass:.3f}kg below dry mass {dry_mass:.3f}kg"
        
        if mass > initial_mass * 1.05:  # Allow 5% rounding error
            return False, f"Mass {mass:.3f}kg exceeds initial {initial_mass:.3f}kg"
        
        return True, None
    
    @staticmethod
    def validate_quaternion(q):
        """Validate quaternion is properly formed."""
        is_valid, issues = QuaternionUtils.validate(q)
        reason = "; ".join(issues) if issues else None
        return is_valid, reason
    
    @staticmethod
    def validate_complete_state(r_enu, v_enu, q_enu2b, mass, initial_mass, propellant_mass):
        """
        Validate entire state vector.
        
        Args:
            r_enu, v_enu, q_enu2b (np.ndarray): State components
            mass (float): Current mass
            initial_mass (float): Initial mass
            propellant_mass (float): Propellant mass
        
        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []
        
        valid, reason = StateValidator.validate_position(r_enu)
        if not valid:
            errors.append(f"Position: {reason}")
        
        valid, reason = StateValidator.validate_velocity(v_enu)
        if not valid:
            errors.append(f"Velocity: {reason}")
        
        valid, reason = StateValidator.validate_quaternion(q_enu2b)
        if not valid:
            errors.append(f"Quaternion: {reason}")
        
        valid, reason = StateValidator.validate_mass(mass, initial_mass, propellant_mass)
        if not valid:
            errors.append(f"Mass: {reason}")
        
        return len(errors) == 0, errors


class NumericalRecovery:
    """Mechanisms for recovering from numerical instabilities."""
    
    @staticmethod
    def safe_divide(numerator, denominator, fallback=0.0, min_denominator=1e-10):
        """
        Perform division with protection against divide-by-zero.
        
        Args:
            numerator: Dividend
            denominator: Divisor
            fallback: Value to return if denominator too small
            min_denominator: Minimum denominator magnitude
        
        Returns:
            Result of division or fallback value
        """
        if isinstance(denominator, np.ndarray):
            denom_abs = np.abs(denominator)
        else:
            denom_abs = abs(denominator)
        
        if np.any(denom_abs < min_denominator):
            logger.warning(f"Division denominator {denominator} too small, using fallback {fallback}")
            return fallback
        
        return numerator / denominator
    
    @staticmethod
    def clamp(value, min_val, max_val, warn_if_clamped=True):
        """
        Clamp value to bounds with optional warning.
        
        Args:
            value: Value to clamp
            min_val: Minimum bound
            max_val: Maximum bound
            warn_if_clamped: Log warning if clamping occurs
        
        Returns:
            Clamped value
        """
        if value < min_val:
            if warn_if_clamped:
                logger.warning(f"Value {value} clamped to minimum {min_val}")
            return min_val
        elif value > max_val:
            if warn_if_clamped:
                logger.warning(f"Value {value} clamped to maximum {max_val}")
            return max_val
        return value
    
    @staticmethod
    def detect_anomaly(value, name="value"):
        """
        Check if value contains NaN or Inf.
        
        Args:
            value: Value or array to check
            name: Name for error messages
        
        Returns:
            tuple: (has_anomaly, anomaly_type)
        """
        if isinstance(value, np.ndarray):
            if np.any(np.isnan(value)):
                return True, "NaN"
            if np.any(np.isinf(value)):
                return True, "Inf"
        else:
            if np.isnan(value):
                return True, "NaN"
            if np.isinf(value):
                return True, "Inf"
        
        return False, None
