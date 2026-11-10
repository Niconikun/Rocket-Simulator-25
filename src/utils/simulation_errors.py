# Author: Code Review Implementation
#         Rocket Simulator Improvements
#         Date: March 26, 2026

"""
Custom Exception Classes for Rocket Simulation

Provides structured error hierarchy for different failure modes.
"""


# ========== Exception Hierarchy ==========

class RocketSimulationError(Exception):
    """
    Base exception for all rocket simulation errors.
    
    All simulation-specific exceptions should inherit from this.
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
