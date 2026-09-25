# Author: Nicolas Sturm
#         Rocket Simulator - Clean Architecture Refactoring
#         Phase 2: Rocket State Component

"""
Rocket State Module

This module provides pure state management for the rocket, separating state
from behavior. This is a key step in applying the Single Responsibility Principle.

RocketState:
    - Stores position, velocity, attitude, and mass
    - Provides getters/setters with validation
    - Does NOT contain any calculation logic
    - Can be serialized/deserialized for save/load

Design Principles:
    - State is immutable except through explicit setters
    - All state changes are validated
    - State can be copied/cloned
    - State can be serialized for persistence

Usage:
    from src.models.rocket.state import RocketState
    
    # Create initial state
    state = RocketState(
        r_enu=np.array([0, 0, 0]),
        v_enu=np.array([0, 0, 10]),
        q_enu2b=np.array([0, 0, 0, 1]),
        w_enu=np.array([0, 0, 0]),
        mass=10.0
    )
    
    # Access state
    position = state.r_enu
    velocity = state.v_enu
    
    # Update state (validated)
    state.r_enu = np.array([1, 2, 3])
    state.mass = 9.5  # Validated to be > 0
"""

import numpy as np
from typing import Optional
from src.utils.numerical_utils import QuaternionUtils, StateValidator
from src.utils.simulation_errors import InputValidationError, NumericalStabilityError
from src.utils.simulation_constants import SimulationConstants as SIM_CONST


class RocketState:
    """
    Pure state container for rocket simulation.
    
    This class stores all state variables for the rocket simulation without
    containing any calculation or simulation logic. This separation of state
    from behavior enables better testing, serialization, and maintainability.
    
    Attributes:
        r_enu: Position in ENU frame [m] (East, North, Up)
        v_enu: Velocity in ENU frame [m/s]
        q_enu2b: Quaternion rotation from ENU to body frame [-] (normalized)
        w_enu: Angular velocity in ENU frame [rad/s]
        mass: Current total mass [kg]
        time: Current simulation time [s]
    
    Note:
        Additional derived state (w_b, yaw, pitch, roll, etc.) can be calculated
        from these primary state variables using helper methods.
    """
    
    def __init__(
        self,
        r_enu: np.ndarray,
        v_enu: np.ndarray,
        q_enu2b: np.ndarray,
        w_enu: np.ndarray,
        mass: float,
        time: float = 0.0
    ) -> None:
        """
        Initialize rocket state with position, velocity, attitude, and mass.
        
        Args:
            r_enu: Initial position in ENU frame [m] (3-element array)
            v_enu: Initial velocity in ENU frame [m/s] (3-element array)
            q_enu2b: Initial quaternion from ENU to body (4-element array, normalized)
            w_enu: Initial angular velocity in ENU frame [rad/s] (3-element array)
            mass: Initial total mass [kg] (must be positive)
            time: Initial simulation time [s] (default: 0.0)
        
        Raises:
            InputValidationError: If any input is invalid or out of bounds
        """
        # Validate and store state
        self._r_enu = self._validate_position(r_enu)
        self._v_enu = self._validate_velocity(v_enu)
        self._q_enu2b = self._validate_quaternion(q_enu2b)
        self._w_enu = self._validate_angular_velocity(w_enu)
        self._mass = self._validate_mass(mass)
        self._time = float(time)
        
        # Derived state (cached for performance)
        self._w_b: Optional[np.ndarray] = None
        self._yaw: Optional[float] = None
        self._pitch: Optional[float] = None
        self._roll: Optional[float] = None
        self._v_norm: Optional[float] = None
        self._v_b: Optional[np.ndarray] = None
        
        # Cache is dirty initially
        self._cache_dirty = True
    
    # ------------------------------------------------------------------
    # Validation methods
    # ------------------------------------------------------------------
    
    @staticmethod
    def _validate_position(r_enu: np.ndarray) -> np.ndarray:
        """Validate and return position array."""
        if not isinstance(r_enu, np.ndarray) or r_enu.shape != (3,):
            raise InputValidationError("Position must be 3-element numpy array")
        valid, reason = StateValidator.validate_position(
            r_enu, max_altitude=SIM_CONST.MAX_ALTITUDE
        )
        if not valid:
            raise InputValidationError(f"Invalid position: {reason}")
        return np.array(r_enu, dtype=float)
    
    @staticmethod
    def _validate_velocity(v_enu: np.ndarray) -> np.ndarray:
        """Validate and return velocity array."""
        if not isinstance(v_enu, np.ndarray) or v_enu.shape != (3,):
            raise InputValidationError("Velocity must be 3-element numpy array")
        valid, reason = StateValidator.validate_velocity(
            v_enu, max_velocity=SIM_CONST.MAX_VELOCITY
        )
        if not valid:
            raise InputValidationError(f"Invalid velocity: {reason}")
        return np.array(v_enu, dtype=float)
    
    @staticmethod
    def _validate_quaternion(q_enu2b: np.ndarray) -> np.ndarray:
        """Validate, normalize, and return quaternion."""
        if not isinstance(q_enu2b, np.ndarray) or q_enu2b.shape != (4,):
            raise InputValidationError("Quaternion must be 4-element numpy array")
        try:
            normalized = QuaternionUtils.normalize(
                q_enu2b, 
                allow_identity_fallback=True
            )
            return np.array(normalized, dtype=float)
        except Exception as e:
            raise InputValidationError(f"Invalid quaternion: {e}") from e
    
    @staticmethod
    def _validate_angular_velocity(w_enu: np.ndarray) -> np.ndarray:
        """Validate and return angular velocity array."""
        if not isinstance(w_enu, np.ndarray) or w_enu.shape != (3,):
            raise InputValidationError("Angular velocity must be 3-element numpy array")
        return np.array(w_enu, dtype=float)
    
    @staticmethod
    def _validate_mass(mass: float) -> float:
        """Validate and return mass."""
        if not isinstance(mass, (int, float)) or mass <= 0:
            raise InputValidationError(f"Mass must be positive number, got {mass}")
        return float(mass)
    
    # ------------------------------------------------------------------
    # State Properties (with validation)
    # ------------------------------------------------------------------
    
    @property
    def r_enu(self) -> np.ndarray:
        """Position in ENU frame [m] (East, North, Up)"""
        return self._r_enu.copy()
    
    @r_enu.setter
    def r_enu(self, value: np.ndarray) -> None:
        """Set position with validation."""
        self._r_enu = self._validate_position(value)
        self._invalidate_cache()
    
    @property
    def v_enu(self) -> np.ndarray:
        """Velocity in ENU frame [m/s]"""
        return self._v_enu.copy()
    
    @v_enu.setter
    def v_enu(self, value: np.ndarray) -> None:
        """Set velocity with validation."""
        self._v_enu = self._validate_velocity(value)
        self._invalidate_cache()
    
    @property
    def q_enu2b(self) -> np.ndarray:
        """Quaternion from ENU to body frame [-] (normalized)"""
        return self._q_enu2b.copy()
    
    @q_enu2b.setter
    def q_enu2b(self, value: np.ndarray) -> None:
        """Set quaternion with validation and normalization."""
        self._q_enu2b = self._validate_quaternion(value)
        self._invalidate_cache()
    
    @property
    def w_enu(self) -> np.ndarray:
        """Angular velocity in ENU frame [rad/s]"""
        return self._w_enu.copy()
    
    @w_enu.setter
    def w_enu(self, value: np.ndarray) -> None:
        """Set angular velocity with validation."""
        self._w_enu = self._validate_angular_velocity(value)
        self._invalidate_cache()
    
    @property
    def mass(self) -> float:
        """Current total mass [kg]"""
        return self._mass
    
    @mass.setter
    def mass(self, value: float) -> None:
        """Set mass with validation."""
        self._mass = self._validate_mass(value)
    
    @property
    def time(self) -> float:
        """Current simulation time [s]"""
        return self._time
    
    @time.setter
    def time(self, value: float) -> None:
        """Set time."""
        self._time = float(value)
    
    # ------------------------------------------------------------------
    # Derived Properties (calculated on demand)
    # ------------------------------------------------------------------
    
    @property
    def w_b(self) -> np.ndarray:
        """Angular velocity in body frame [rad/s]"""
        self._ensure_cache()
        return self._w_b.copy()
    
    @property
    def v_norm(self) -> float:
        """Velocity magnitude [m/s]"""
        self._ensure_cache()
        return self._v_norm
    
    @property
    def v_b(self) -> np.ndarray:
        """Velocity in body frame [m/s]"""
        self._ensure_cache()
        return self._v_b.copy()
    
    @property
    def yaw(self) -> float:
        """Yaw angle [deg]"""
        self._ensure_cache()
        return self._yaw
    
    @property
    def pitch(self) -> float:
        """Pitch angle [deg]"""
        self._ensure_cache()
        return self._pitch
    
    @property
    def roll(self) -> float:
        """Roll angle [deg]"""
        self._ensure_cache()
        return self._roll
    
    # ------------------------------------------------------------------
    # Cache Management
    # ------------------------------------------------------------------
    
    def _invalidate_cache(self) -> None:
        """Mark cached derived values as dirty."""
        self._cache_dirty = True
        self._w_b = None
        self._yaw = None
        self._pitch = None
        self._roll = None
        self._v_norm = None
        self._v_b = None
    
    def _ensure_cache(self) -> None:
        """Calculate and cache derived values if needed."""
        if not self._cache_dirty:
            return
        
        # Calculate derived values
        self._calculate_derived()
        self._cache_dirty = False
    
    def _calculate_derived(self) -> None:
        """Calculate all derived state variables."""
        import navpy as nav
        from src.utils.mattools import MatTools as Mat
        
        # Angular velocity in body frame
        self._w_b = Mat.q_rot(self._w_enu, self._q_enu2b, 0)
        
        # Velocity magnitude
        self._v_norm = float(np.linalg.norm(self._v_enu))
        
        # Velocity in body frame
        self._v_b = Mat.q_rot(self._v_enu, self._q_enu2b, 0)
        
        # Euler angles from quaternion
        q0 = self._q_enu2b[3]  # Scalar part
        qvec = self._q_enu2b[0:3]  # Vector part
        angles = nav.quat2angle(q0, qvec, output_unit='deg', rotation_sequence='ZYX')
        self._yaw = float(angles[0])  # Rotation about Z (East)
        self._pitch = float(-angles[1])  # Negativo cuando apunta arriba en plano XZ
        self._roll = float(angles[2])  # Rotation about X (longitudinal)
    
    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------
    
    def copy(self) -> 'RocketState':
        """
        Create a deep copy of the state.
        
        Returns:
            RocketState: New state object with same values
        """
        return RocketState(
            r_enu=self._r_enu.copy(),
            v_enu=self._v_enu.copy(),
            q_enu2b=self._q_enu2b.copy(),
            w_enu=self._w_enu.copy(),
            mass=self._mass,
            time=self._time
        )
    
    def to_dict(self) -> dict:
        """
        Convert state to dictionary for serialization.
        
        Returns:
            dict: State as dictionary
        """
        return {
            'r_enu': self._r_enu.tolist(),
            'v_enu': self._v_enu.tolist(),
            'q_enu2b': self._q_enu2b.tolist(),
            'w_enu': self._w_enu.tolist(),
            'mass': self._mass,
            'time': self._time
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RocketState':
        """
        Create state from dictionary.
        
        Args:
            data: Dictionary with state values
        
        Returns:
            RocketState: New state object
        """
        return cls(
            r_enu=np.array(data['r_enu']),
            v_enu=np.array(data['v_enu']),
            q_enu2b=np.array(data['q_enu2b']),
            w_enu=np.array(data['w_enu']),
            mass=data['mass'],
            time=data.get('time', 0.0)
        )
    
    def __repr__(self) -> str:
        """String representation of state."""
        return (
            f"RocketState(time={self._time:.2f}s, "
            f"mass={self._mass:.2f}kg, "
            f"pos={self._r_enu.tolist()}, "
            f"vel={self._v_enu.tolist()})"
        )


__all__ = ['RocketState']
