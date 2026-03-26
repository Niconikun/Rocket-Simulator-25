# Author: Code Review Implementation
#         Rocket Simulator Improvements
#         Date: March 26, 2026

"""
Custom Exception and Warning Classes for Rocket Simulation

Provides structured error hierarchy for different failure modes:
- Configuration errors (bad input data)
- Simulation errors (computation failures)
- Physics errors (physical constraint violations)
- Numeric errors (numerical instabilities)
"""


# ========== Exception Hierarchy ==========

class RocketSimulationError(Exception):
    """
    Base exception for all rocket simulation errors.
    
    All simulation-specific exceptions should inherit from this.
    """
    pass


class ConfigurationError(RocketSimulationError):
    """
    Raised when configuration data is invalid or incomplete.
    
    Examples:
    - Missing required keys in rocket config JSON
    - Invalid geometric parameters
    - Out-of-bounds engine specifications
    """
    pass


class InputValidationError(RocketSimulationError):
    """
    Raised when input parameters fail validation.
    
    Examples:
    - Initial velocity exceeds reasonable bounds
    - Position underground or at unreasonable altitude
    - Mass is negative or exceeds initial mass
    """
    pass


class PhysicsCalculationError(RocketSimulationError):
    """
    Raised when physics calculation fails.
    
    Examples:
    - Aerodynamic coefficient calculation fails
    - Thrust calculation fails
    - Gravitational acceleration calculation fails
    """
    pass


class NumericalStabilityError(RocketSimulationError):
    """
    Raised when numerical instability is detected and unrecoverable.
    
    Examples:
    - Quaternion norm collapses to zero
    - State vector contains NaN or Inf
    - RK4 integration produces invalid state
    """
    pass


class FileOperationError(RocketSimulationError):
    """
    Raised when file operations fail.
    
    Examples:
    - Configuration file not found
    - Thrust curve data file missing
    - Cannot write trajectory data
    """
    pass


class AtmosphereError(RocketSimulationError):
    """Raised when atmosphere model fails."""
    pass


class EngineError(RocketSimulationError):
    """Raised when engine calculations fail."""
    pass


class AerodynamicsError(RocketSimulationError):
    """Raised when aerodynamics calculations fail."""
    pass


# ========== Warning Classes ==========

class RocketSimulationWarning(UserWarning):
    """Base warning class for non-critical simulation issues."""
    pass


class NumericalWarning(RocketSimulationWarning):
    """Warning for numerical stability concerns."""
    pass


class PhysicsWarning(RocketSimulationWarning):
    """Warning for unusual (but not impossible) physics behavior."""
    pass


class PerformanceWarning(RocketSimulationWarning):
    """Warning for performance-related issues."""
    pass


# ========== Helper Functions ==========

def raise_if_invalid(condition, exception_class, message):
    """
    Raise exception if condition is False.
    
    Args:
        condition (bool): Condition that must be True
        exception_class: Exception class to raise
        message (str): Error message
    
    Raises:
        exception_class: If condition is False
    """
    if not condition:
        raise exception_class(message)


def warn_if_invalid(condition, warning_class, message):
    """
    Issue warning if condition is False.
    
    Args:
        condition (bool): Condition that should be True
        warning_class: Warning class to issue
        message (str): Warning message
    """
    import warnings
    if not condition:
        warnings.warn(message, warning_class, stacklevel=2)


# ========== Exception Details Context Manager ==========

class ErrorContext:
    """
    Context manager for detailed error reporting.
    
    Example:
        with ErrorContext("Aerodynamics calculation"):
            cd = calculate_cd(rocket, height)
    """
    
    def __init__(self, operation_name):
        self.operation_name = operation_name
        self.error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if issubclass(exc_type, RocketSimulationError):
                # Already a simulation error, just re-raise
                return False
            else:
                # Convert to simulation error with context
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error in {self.operation_name}: {exc_val}")
                
                raise PhysicsCalculationError(
                    f"Failed during {self.operation_name}: {exc_val}"
                ) from exc_val
        
        return False


# ========== Error Recovery Recommendations ==========

ERROR_RECOVERY_HINTS = {
    'ConfigurationError': [
        'Check JSON file syntax with json.tool',
        'Verify all required keys are present in rocket config',
        'Check numeric parameters are in valid ranges'
    ],
    'InputValidationError': [
        'Verify initial state vector is reasonable',
        'Check position is not underground',
        'Ensure initial velocity is not excessive'
    ],
    'NumericalStabilityError': [
        'Try reducing timestep (dt)',
        'Check quaternion normalization is working',
        'Verify state vector for NaN/Inf values'
    ],
    'PhysicsCalculationError': [
        'Check atmospheric model is initialized',
        'Verify rocket configuration is complete',
        'Ensure physical parameters (area, mass) are positive'
    ],
    'FileOperationError': [
        'Check file path is correct',
        'Verify file exists and is readable',
        'Check file format is JSON or CSV as expected'
    ]
}


def get_recovery_hints(error):
    """Get recovery suggestions for an error."""
    error_type = type(error).__name__
    return ERROR_RECOVERY_HINTS.get(error_type, ['Consult documentation'])
