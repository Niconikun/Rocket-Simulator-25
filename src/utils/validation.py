"""
Input Validation Utilities

Provides centralized validation functions for user inputs across all widgets.
This ensures consistent validation behavior and error messages.

Usage:
    from src.utils.validation import Validators, ValidationError
    
    # Use built-in validators
    if not Validators.validate_positive(value):
        raise ValidationError("Value must be positive")
    
    # Or create custom validators
    validator = Validators.range_validator(0, 100, "Value must be between 0 and 100")
    if not validator(value):
        raise ValidationError(validator.error_message)
"""

from typing import Callable, Optional, Tuple, Any, Union
from dataclasses import dataclass
import re


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    error_message: str = ""
    
    def __bool__(self) -> bool:
        return self.is_valid


class ValidationError(Exception):
    """Exception raised when validation fails."""
    pass


class Validators:
    """
    Collection of validation functions for common use cases.
    
    All validators follow the pattern:
    - Return ValidationResult with is_valid=True if validation passes
    - Return ValidationResult with is_valid=False and error_message if validation fails
    - Can be used as functions or as callable objects
    """
    
    # ========================================================================
    # Numeric Validators
    # ========================================================================
    
    @staticmethod
    def validate_positive(value: Union[int, float], 
                        error_msg: str = "Value must be positive") -> ValidationResult:
        """Validate that a numeric value is positive (> 0)."""
        try:
            if value is None:
                return ValidationResult(False, "Value cannot be None")
            if float(value) <= 0:
                return ValidationResult(False, error_msg)
            return ValidationResult(True)
        except (TypeError, ValueError):
            return ValidationResult(False, "Value must be a number")
    
    @staticmethod
    def validate_non_negative(value: Union[int, float],
                             error_msg: str = "Value must be non-negative") -> ValidationResult:
        """Validate that a numeric value is non-negative (>= 0)."""
        try:
            if value is None:
                return ValidationResult(False, "Value cannot be None")
            if float(value) < 0:
                return ValidationResult(False, error_msg)
            return ValidationResult(True)
        except (TypeError, ValueError):
            return ValidationResult(False, "Value must be a number")
    
    @staticmethod
    def validate_range(value: Union[int, float], 
                      min_val: float, max_val: float,
                      error_msg: Optional[str] = None) -> ValidationResult:
        """Validate that a numeric value is within a range [min_val, max_val]."""
        try:
            if value is None:
                return ValidationResult(False, "Value cannot be None")
            val = float(value)
            if val < min_val or val > max_val:
                msg = error_msg or f"Value must be between {min_val} and {max_val}"
                return ValidationResult(False, msg)
            return ValidationResult(True)
        except (TypeError, ValueError):
            return ValidationResult(False, "Value must be a number")
    
    @staticmethod
    def range_validator(min_val: float, max_val: float, 
                        error_msg: Optional[str] = None) -> Callable[[Union[int, float]], ValidationResult]:
        """Create a reusable range validator function."""
        def validator(value: Union[int, float]) -> ValidationResult:
            return Validators.validate_range(value, min_val, max_val, error_msg)
        return validator
    
    @staticmethod
    def validate_integer(value: Any, 
                        error_msg: str = "Value must be an integer") -> ValidationResult:
        """Validate that a value is an integer."""
        try:
            if value is None:
                return ValidationResult(False, "Value cannot be None")
            if not isinstance(value, int) or isinstance(value, bool):
                # Check if it's a float that's actually an integer
                if isinstance(value, float) and value.is_integer():
                    return ValidationResult(True)
                return ValidationResult(False, error_msg)
            return ValidationResult(True)
        except (TypeError, ValueError):
            return ValidationResult(False, error_msg)
    
    # ========================================================================
    # String Validators
    # ========================================================================
    
    @staticmethod
    def validate_non_empty(value: Optional[str],
                          error_msg: str = "Value cannot be empty") -> ValidationResult:
        """Validate that a string is not None and not empty/whitespace."""
        if value is None:
            return ValidationResult(False, "Value cannot be None")
        if not isinstance(value, str):
            return ValidationResult(False, "Value must be a string")
        if not value.strip():
            return ValidationResult(False, error_msg)
        return ValidationResult(True)
    
    @staticmethod
    def validate_max_length(value: Optional[str], max_length: int,
                            error_msg: Optional[str] = None) -> ValidationResult:
        """Validate that a string doesn't exceed maximum length."""
        result = Validators.validate_non_empty(value)
        if not result.is_valid:
            return result
        if len(value) > max_length:
            msg = error_msg or f"Value must be {max_length} characters or less"
            return ValidationResult(False, msg)
        return ValidationResult(True)
    
    @staticmethod
    def validate_safe_filename(value: Optional[str],
                              error_msg: str = "Invalid characters in filename") -> ValidationResult:
        """Validate that a string is a safe filename (no special chars)."""
        result = Validators.validate_non_empty(value)
        if not result.is_valid:
            return result
        # Allow alphanumeric, spaces, hyphens, underscores, periods
        if not all(c.isalnum() or c in ' .-_' for c in value):
            return ValidationResult(False, error_msg)
        # Prevent path traversal
        if '..' in value or '/' in value or '\\' in value:
            return ValidationResult(False, "Filename cannot contain path separators")
        return ValidationResult(True)
    
    @staticmethod
    def validate_filesystem_name(value: Optional[str],
                                 error_msg: str = "Invalid characters for save name") -> ValidationResult:
        """Validate a name for use as a key in JSON files or directory names."""
        result = Validators.validate_non_empty(value)
        if not result.is_valid:
            return result
        # Allow alphanumeric, spaces, hyphens, underscores
        if not all(c.isalnum() or c in ' -_' for c in value):
            return ValidationResult(False, error_msg)
        if len(value) > 100:
            return ValidationResult(False, "Name must be 100 characters or less")
        return ValidationResult(True)
    
    # ========================================================================
    # Specialized Validators for Rocket Simulator
    # ========================================================================
    
    @staticmethod
    def validate_latitude(value: Any) -> ValidationResult:
        """Validate latitude value (-90 to 90 degrees)."""
        return Validators.validate_range(
            value, -90, 90,
            "Latitude must be between -90 and 90 degrees"
        )
    
    @staticmethod
    def validate_longitude(value: Any) -> ValidationResult:
        """Validate longitude value (-180 to 180 degrees)."""
        return Validators.validate_range(
            value, -180, 180,
            "Longitude must be between -180 and 180 degrees"
        )
    
    @staticmethod
    def validate_elevation(value: Any, min_val: float = -500, max_val: float = 10000) -> ValidationResult:
        """Validate elevation value."""
        return Validators.validate_range(
            value, min_val, max_val,
            f"Elevation must be between {min_val} and {max_val} meters"
        )
    
    @staticmethod
    def validate_angle(value: Any, min_val: float = 0, max_val: float = 360) -> ValidationResult:
        """Validate angle value (0-360 degrees by default)."""
        return Validators.validate_range(
            value, min_val, max_val,
            f"Angle must be between {min_val} and {max_val} degrees"
        )
    
    @staticmethod
    def validate_wind_direction(value: Any) -> ValidationResult:
        """Validate wind direction (0-360 degrees)."""
        return Validators.validate_angle(value, 0, 360)
    
    @staticmethod
    def validate_wind_speed(value: Any, max_speed: float = 50.0) -> ValidationResult:
        """Validate wind speed (0 to max_speed m/s)."""
        return Validators.validate_range(
            value, 0, max_speed,
            f"Wind speed must be between 0 and {max_speed} m/s"
        )
    
    @staticmethod
    def validate_temperature(value: Any, min_temp: float = -50, max_temp: float = 60) -> ValidationResult:
        """Validate temperature value."""
        return Validators.validate_range(
            value, min_temp, max_temp,
            f"Temperature must be between {min_temp} and {max_temp} °C"
        )
    
    @staticmethod
    def validate_pressure(value: Any, min_pressure: float = 50000, max_pressure: float = 110000) -> ValidationResult:
        """Validate atmospheric pressure value."""
        return Validators.validate_range(
            value, min_pressure, max_pressure,
            f"Pressure must be between {min_pressure} and {max_pressure} Pa"
        )
    
    @staticmethod
    def validate_mass(value: Any, min_mass: float = 0.1, max_mass: float = 100000) -> ValidationResult:
        """Validate mass value."""
        return Validators.validate_range(
            value, min_mass, max_mass,
            f"Mass must be between {min_mass} and {max_mass} kg"
        )
    
    @staticmethod
    def validate_length(value: Any, min_len: float = 0.001, max_len: float = 100) -> ValidationResult:
        """Validate length/distance value."""
        return Validators.validate_range(
            value, min_len, max_len,
            f"Length must be between {min_len} and {max_len} meters"
        )
    
    @staticmethod
    def validate_time(value: Any, min_time: float = 0.0001, max_time: float = 10000) -> ValidationResult:
        """Validate time value."""
        return Validators.validate_range(
            value, min_time, max_time,
            f"Time must be between {min_time} and {max_time} seconds"
        )
    
    @staticmethod
    def validate_percentage(value: Any) -> ValidationResult:
        """Validate percentage value (0-100)."""
        return Validators.validate_range(value, 0, 100, "Percentage must be between 0 and 100")
    
    @staticmethod
    def validate_coefficient(value: Any, min_val: float = 0.0, max_val: float = 10.0) -> ValidationResult:
        """Validate a coefficient value (e.g., drag coefficient)."""
        return Validators.validate_range(
            value, min_val, max_val,
            f"Coefficient must be between {min_val} and {max_val}"
        )


class Validator:
    """
    Callable validator with chainable operations.
    
    Usage:
        validator = (Validator()
            .required()
            .is_numeric()
            .in_range(0, 100)
            .build())
        
        result = validator(value)
        if not result:
            print(result.error_message)
    """
    
    def __init__(self):
        self._checks: list[Tuple[Callable[[Any], bool], str]] = []
    
    def required(self, message: str = "Value is required") -> 'Validator':
        """Add required check (value is not None and not empty)."""
        def check(value: Any) -> bool:
            if value is None:
                return False
            if isinstance(value, str) and not value.strip():
                return False
            return True
        self._checks.append((check, message))
        return self
    
    def is_numeric(self, message: str = "Value must be a number") -> 'Validator':
        """Add numeric check."""
        def check(value: Any) -> bool:
            try:
                float(value)
                return True
            except (TypeError, ValueError):
                return False
        self._checks.append((check, message))
        return self
    
    def is_integer(self, message: str = "Value must be an integer") -> 'Validator':
        """Add integer check."""
        def check(value: Any) -> bool:
            if isinstance(value, bool):
                return False
            if isinstance(value, int):
                return True
            if isinstance(value, float):
                return value.is_integer()
            try:
                val = float(value)
                return val.is_integer()
            except (TypeError, ValueError):
                return False
        self._checks.append((check, message))
        return self
    
    def in_range(self, min_val: float, max_val: float,
                 message: Optional[str] = None) -> 'Validator':
        """Add range check."""
        msg = message or f"Value must be between {min_val} and {max_val}"
        def check(value: Any) -> bool:
            try:
                return min_val <= float(value) <= max_val
            except (TypeError, ValueError):
                return False
        self._checks.append((check, msg))
        return self
    
    def matches_pattern(self, pattern: str, message: str) -> 'Validator':
        """Add regex pattern check."""
        compiled = re.compile(pattern)
        def check(value: Any) -> bool:
            if not isinstance(value, str):
                return False
            return bool(compiled.match(value))
        self._checks.append((check, message))
        return self
    
    def custom(self, check_func: Callable[[Any], bool], message: str) -> 'Validator':
        """Add custom validation check."""
        self._checks.append((check_func, message))
        return self
    
    def build(self) -> Callable[[Any], ValidationResult]:
        """Build the validator function."""
        checks = self._checks
        
        def validator(value: Any) -> ValidationResult:
            for check_func, error_msg in checks:
                if not check_func(value):
                    return ValidationResult(False, error_msg)
            return ValidationResult(True)
        
        return validator


def validate_and_set(state_provider, key: str, value: Any, 
                    validator: Optional[Callable[[Any], ValidationResult]] = None,
                    error_callback: Optional[Callable[[str], None]] = None) -> bool:
    """
    Validate a value and set it in state if valid.
    
    Args:
        state_provider: The StateProvider instance
        key: The state key to set
        value: The value to validate and set
        validator: Optional validation function (returns ValidationResult)
        error_callback: Optional function to call with error message if validation fails
    
    Returns:
        True if value was valid and set, False otherwise
    """
    if validator:
        result = validator(value)
        if not result.is_valid:
            if error_callback:
                error_callback(result.error_message)
            return False
    
    state_provider.set(key, value)
    return True
