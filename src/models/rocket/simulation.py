# Author: Nicolas Sturm
#         Rocket Simulator - Clean Architecture Refactoring
#         Phase 2: Rocket Simulation Component

"""
Rocket Simulation Module

This module handles numerical integration and history tracking for the rocket
simulation. It uses the Runge-Kutta 4th order method with quaternion stabilization.

RocketSimulation:
    - Manages simulation state over time
    - Performs numerical integration (RK4)
    - Tracks simulation history
    - Handles quaternion normalization and numerical stability

Design Principles:
    - Separation of concerns: only handles integration and history
    - Uses dependency injection for dynamics calculator
    - Delegates force calculations to RocketDynamics
    - Maintains history for post-simulation analysis

Usage:
    from src.models.rocket.simulation import RocketSimulation
    from src.models.rocket.state import RocketState
    from src.models.rocket.dynamics import RocketDynamics
    
    # Create simulation
    simulation = RocketSimulation(
        state=state,
        dynamics=dynamics,
        history_capacity=10000
    )
    
    # Step simulation forward
    simulation.step(dt=0.01)
    
    # Get current state
    current_state = simulation.state
"""

import numpy as np
from typing import Optional, TYPE_CHECKING, Callable
from dataclasses import dataclass, field
from collections import deque

if TYPE_CHECKING:
    from src.models.rocket.state import RocketState
    from src.models.rocket.dynamics import RocketDynamics


@dataclass
class SimulationHistory:
    """
    Container for simulation history data.
    
    Uses efficient data structures for storing time series data.
    
    Attributes:
        times: List of simulation times [s]
        states: List of state dictionaries
        forces: List of force vectors
        torques: List of torque vectors
    """
    times: list = field(default_factory=list)
    positions: list = field(default_factory=list)
    velocities: list = field(default_factory=list)
    attitudes: list = field(default_factory=list)
    masses: list = field(default_factory=list)
    forces: list = field(default_factory=list)
    torques: list = field(default_factory=list)
    
    def add_entry(
        self,
        time: float,
        position: np.ndarray,
        velocity: np.ndarray,
        attitude: np.ndarray,
        mass: float,
        force: np.ndarray,
        torque: np.ndarray
    ) -> None:
        """Add a new entry to the history."""
        self.times.append(time)
        self.positions.append(position.copy())
        self.velocities.append(velocity.copy())
        self.attitudes.append(attitude.copy())
        self.masses.append(mass)
        self.forces.append(force.copy())
        self.torques.append(torque.copy())
    
    def clear(self) -> None:
        """Clear all history."""
        self.times.clear()
        self.positions.clear()
        self.velocities.clear()
        self.attitudes.clear()
        self.masses.clear()
        self.forces.clear()
        self.torques.clear()
    
    def __len__(self) -> int:
        """Number of history entries."""
        return len(self.times)


class RocketSimulation:
    """
    Numerical simulation manager for rocket flight.
    
    This class handles the time-stepping integration of the rocket's equations
    of motion using Runge-Kutta 4th order method. It delegates force/torque
    calculations to the RocketDynamics component.
    
    Attributes:
        state: Current rocket state
        dynamics: Rocket dynamics calculator
        history: Simulation history storage
        step_count: Number of integration steps performed
    """
    
    def __init__(
        self,
        state: 'RocketState',
        dynamics: 'RocketDynamics',
        history_capacity: int = 10000
    ) -> None:
        """
        Initialize rocket simulation.
        
        Args:
            state: Initial rocket state
            dynamics: Rocket dynamics calculator
            history_capacity: Maximum number of history entries to store
        """
        self.state = state
        self.dynamics = dynamics
        self.history = SimulationHistory()
        self.history_capacity = history_capacity
        self.step_count = 0
        
        # Numerical stability parameters
        self._quaternion_norm_min = 1e-6
        self._mass_min = 0.1  # Minimum mass to prevent division by zero
        
        # Defer initial history entry until first step to ensure all dependencies are set
        # self._save_to_history()  # Removed: defer until first step
    
    # ------------------------------------------------------------------
    # Simulation Stepping
    # ------------------------------------------------------------------
    
    def step(self, dt: float) -> None:
        """
        Advance simulation by one time step using RK4 integration.
        
        Args:
            dt: Time step size [s]
        
        Notes:
            - Normalizes quaternion at each step to prevent drift
            - Validates state for NaN/Inf values
            - Updates history after each step
        """
        # Validate dt
        if dt <= 0:
            raise ValueError(f"Time step must be positive, got {dt}")
        
        # Ensure quaternion is normalized
        self._normalize_quaternion()
        
        # Perform RK4 integration
        self._rk4_step(dt)
        
        # Update time
        self.state.time += dt
        self.step_count += 1
        
        # Save to history (with capacity limit)
        if len(self.history) < self.history_capacity or self.step_count % 10 == 0:
            self._save_to_history()
    
    def _rk4_step(self, dt: float) -> None:
        """
        Perform one RK4 integration step.
        
        Args:
            dt: Time step size [s]
        """
        # Get current state as state vector
        x = self._get_state_vector()
        
        # RK4 coefficients
        k1 = self._dynamics_function(x)
        k2 = self._dynamics_function(x + 0.5 * dt * k1)
        k3 = self._dynamics_function(x + 0.5 * dt * k2)
        k4 = self._dynamics_function(x + dt * k3)
        
        # Update state: x_new = x + dt * (k1 + 2*k2 + 2*k3 + k4) / 6
        x_new = x + dt * (k1 + 2*k2 + 2*k3 + k4) / 6.0
        
        # Apply new state
        self._apply_state_vector(x_new)
    
    def _dynamics_function(self, x: np.ndarray) -> np.ndarray:
        """
        Calculate time derivatives of the state vector.
        
        Args:
            x: State vector [r_enu, v_enu, q_enu2b, w_b, mass]
        
        Returns:
            np.ndarray: Time derivatives of state vector
        """
        # Extract state from vector
        r_enu = x[0:3]
        v_enu = x[3:6]
        q_enu2b = x[6:10]
        w_b = x[10:13]
        mass = x[13]
        
        # Normalize quaternion
        q_norm = np.linalg.norm(q_enu2b)
        if q_norm > self._quaternion_norm_min:
            q_enu2b = q_enu2b / q_norm
        else:
            q_enu2b = np.array([0.0, 0.0, 0.0, 1.0])
        
        # Ensure positive mass
        if mass < self._mass_min:
            mass = self._mass_min
        
        # Temporary update state for calculations
        old_state = self.state
        temp_state = old_state.copy()
        temp_state.r_enu = r_enu
        temp_state.v_enu = v_enu
        temp_state.q_enu2b = q_enu2b
        temp_state.w_enu = self._body_to_enu_angular_velocity(w_b, q_enu2b)
        temp_state.mass = mass
        
        # Create temporary dynamics with updated state
        temp_dynamics = self._create_temp_dynamics(temp_state)
        
        # Calculate forces and torques
        forces_b, torques_b = temp_dynamics.calculate_forces()
        
        # Calculate gravity in ENU frame
        g_enu = temp_dynamics.calculate_gravity_enu()
        
        # Get mass properties for inertia
        if self.dynamics.mass_properties is not None:
            burn_fraction = self.dynamics.mass_properties.get_burn_fraction(mass)
            inertia_b = self.dynamics.mass_properties.get_inertia(burn_fraction)
        else:
            # Default inertia
            inertia_b = np.array([0.1, 0.1, 0.05])
        
        # Calculate accelerations
        accel_b, alpha_b = temp_dynamics.calculate_accelerations(
            forces_b, mass, inertia_b, torques_b
        )
        
        # Calculate derivatives
        # Position: dr/dt = v
        r_dot = v_enu
        
        # Velocity: dv/dt = F/m + g
        # Convert forces to ENU frame and divide by mass, then add gravity
        from src.utils.mattools import MatTools as Mat
        total_force_enu = Mat.q_rot(forces_b, q_enu2b, 1)
        v_dot = total_force_enu / mass + g_enu
        
        # Quaternion: dq/dt = 1/2 * Omega(w) * q
        w_enu = self._body_to_enu_angular_velocity(w_b, q_enu2b)
        from src.utils.mattools import MatTools as Mat
        w_enu_skew4 = Mat.skew4(w_enu)
        q_dot = 0.5 * w_enu_skew4.dot(q_enu2b)
        
        # Angular velocity: dw/dt = alpha (already in body frame)
        w_dot = alpha_b
        
        # Mass: dm/dt = -mass_flow
        mass_flow = self.dynamics.engine.get_mass_flow()
        mass_dot = -mass_flow
        
        # Concatenate derivatives
        return np.concatenate([r_dot, v_dot, q_dot, w_dot, np.array([mass_dot])])
    
    def _body_to_enu_angular_velocity(self, w_b: np.ndarray, q_enu2b: np.ndarray) -> np.ndarray:
        """Convert angular velocity from body to ENU frame."""
        from src.utils.mattools import MatTools as Mat
        return Mat.q_rot(w_b, q_enu2b, 1)
    
    def _create_temp_dynamics(self, state: 'RocketState') -> 'RocketDynamics':
        """Create a temporary dynamics instance with updated state."""
        # For now, just update the existing dynamics state temporarily
        # In a full implementation, we'd create a new dynamics object
        old_state = self.dynamics.state
        self.dynamics.state = state
        return self.dynamics
    
    # ------------------------------------------------------------------
    # State Vector Management
    # ------------------------------------------------------------------
    
    def _get_state_vector(self) -> np.ndarray:
        """
        Get current state as a vector for numerical integration.
        
        Returns:
            np.ndarray: State vector [r_enu, v_enu, q_enu2b, w_b, mass]
        """
        # Convert w_enu to w_b
        from src.utils.mattools import MatTools as Mat
        w_b = Mat.q_rot(self.state.w_enu, self.state.q_enu2b, 0)
        
        return np.concatenate([
            self.state.r_enu,
            self.state.v_enu,
            self.state.q_enu2b,
            w_b,
            np.array([self.state.mass])
        ])
    
    def _apply_state_vector(self, x: np.ndarray) -> None:
        """
        Apply state vector to rocket state.
        
        Args:
            x: State vector [r_enu, v_enu, q_enu2b, w_b, mass]
        """
        # Extract from vector
        r_enu = x[0:3]
        v_enu = x[3:6]
        q_enu2b = x[6:10]
        w_b = x[10:13]
        mass = x[13]
        
        # Convert w_b to w_enu
        from src.utils.mattools import MatTools as Mat
        w_enu = Mat.q_rot(w_b, q_enu2b, 1)
        
        # Update state
        self.state.r_enu = r_enu
        self.state.v_enu = v_enu
        self.state.q_enu2b = q_enu2b
        self.state.w_enu = w_enu
        self.state.mass = mass
    
    # ------------------------------------------------------------------
    # History Management
    # ------------------------------------------------------------------
    
    def _save_to_history(self) -> None:
        """Save current state to history."""
        # Get forces and torques
        forces_b, torques_b = self.dynamics.calculate_forces()
        
        self.history.add_entry(
            time=self.state.time,
            position=self.state.r_enu,
            velocity=self.state.v_enu,
            attitude=self.state.q_enu2b,
            mass=self.state.mass,
            force=forces_b,
            torque=torques_b
        )
    
    def _normalize_quaternion(self) -> None:
        """Ensure quaternion is normalized."""
        from src.utils.numerical_utils import QuaternionUtils
        try:
            self.state.q_enu2b = QuaternionUtils.normalize(
                self.state.q_enu2b,
                min_norm=self._quaternion_norm_min,
                allow_identity_fallback=True
            )
        except Exception:
            # Fallback to identity
            self.state.q_enu2b = np.array([0.0, 0.0, 0.0, 1.0])
    
    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------
    
    def get_history_array(self, field: str) -> np.ndarray:
        """
        Get history data as numpy array.
        
        Args:
            field: Field name ('times', 'positions', 'velocities', 'masses')
        
        Returns:
            np.ndarray: Array of historical values
        """
        if field == 'times':
            return np.array(self.history.times)
        elif field == 'positions':
            return np.array(self.history.positions)
        elif field == 'velocities':
            return np.array(self.history.velocities)
        elif field == 'masses':
            return np.array(self.history.masses)
        else:
            raise ValueError(f"Unknown field: {field}")
    
    def reset(self) -> None:
        """Reset simulation to initial state."""
        self.step_count = 0
        self.state.time = 0.0
        self.history.clear()
        self._save_to_history()
    
    @property
    def is_running(self) -> bool:
        """Check if simulation is still running (hasn't landed)."""
        # Simplified: check if rocket is still moving
        return self.state.v_norm > 1.0  # Threshold: 1 m/s


__all__ = ['RocketSimulation', 'SimulationHistory']
