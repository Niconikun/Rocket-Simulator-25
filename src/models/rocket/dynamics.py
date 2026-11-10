# Author: Nicolas Sturm
#         Rocket Simulator - Clean Architecture Refactoring
#         Phase 2: Rocket Dynamics Component

"""
Rocket Dynamics Module

This module handles force and torque calculations for the rocket simulation.
It uses injected dependencies (IEngine, IAerodynamics, IAtmosphere) instead of
creating them internally, enabling loose coupling and easy testing.

RocketDynamics:
    - Calculates aerodynamic forces and torques
    - Calculates engine forces and torques
    - Computes total forces and torques in body frame
    - Does NOT manage state or perform integration

Design Principles:
    - Pure calculation: no state mutation
    - Dependency injection: accepts interface types
    - Single responsibility: only calculates forces/torques
    - Testable: easy to mock dependencies

Usage:
    from src.models.rocket.dynamics import RocketDynamics
    from src.models.rocket.state import RocketState
    from src.models.interfaces import IEngine, IAerodynamics, IAtmosphere
    
    # Create with dependencies
    dynamics = RocketDynamics(
        state=state,
        engine=engine,
        aerodynamics=aerodynamics,
        atmosphere=atmosphere,
        reference_area=0.01
    )
    
    # Calculate forces
    forces_b, torques_b = dynamics.calculate_forces()
"""

import numpy as np
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.rocket.state import RocketState
    from src.models.interfaces import IEngine, IAerodynamics, IAtmosphere, IMassProperties, IParachute


class RocketDynamics:
    """
    Force and torque calculator for rocket simulation.
    
    This class calculates all forces and torques acting on the rocket:
    - Aerodynamic forces (drag, lift)
    - Engine forces (thrust)
    - Gravitational forces
    - Torques from aerodynamic and engine forces
    
    All calculations are performed in the body frame unless otherwise specified.
    
    Attributes:
        state: Current rocket state
        engine: Engine instance (IEngine)
        aerodynamics: Aerodynamics instance (IAerodynamics)
        atmosphere: Atmosphere instance (IAtmosphere)
        reference_area: Reference area for aerodynamic calculations [m²]
        wind_vector_enu: Current wind vector in ENU frame [m/s]
    """
    
    def __init__(
        self,
        state: 'RocketState',
        engine: 'IEngine',
        aerodynamics: 'IAerodynamics',
        atmosphere: 'IAtmosphere',
        reference_area: float,
        mass_properties: Optional['IMassProperties'] = None,
        wind_vector_enu: Optional[np.ndarray] = None,
        parachute: Optional['IParachute'] = None
    ) -> None:
        """
        Initialize rocket dynamics calculator.
        
        Args:
            state: Current rocket state
            engine: Engine instance implementing IEngine
            aerodynamics: Aerodynamics instance implementing IAerodynamics
            atmosphere: Atmosphere instance implementing IAtmosphere
            reference_area: Reference area for aerodynamic calculations [m²]
            mass_properties: Optional mass properties calculator
            wind_vector_enu: Optional wind vector in ENU frame [m/s]
            parachute: Optional parachute system for recovery
        """
        self.state = state
        self.engine = engine
        self.aerodynamics = aerodynamics
        self.atmosphere = atmosphere
        self.reference_area = float(reference_area)
        self.mass_properties = mass_properties
        self.wind_vector_enu = np.zeros(3) if wind_vector_enu is None else np.array(wind_vector_enu)
        self.parachute = parachute
        
        # Initialize derived values
        self._dynamic_pressure: float = 0.0
        self._mach: float = 0.0
        self._alpha: float = 0.0
        self._density: float = 0.0
        self._v_sonic: float = 0.0
        
        # Force/torque results (cached)
        self._forces_aero_b: Optional[np.ndarray] = None
        self._torques_aero_b: Optional[np.ndarray] = None
        self._forces_engine_b: Optional[np.ndarray] = None
        self._torques_engine_b: Optional[np.ndarray] = None
        self._forces_parachute_b: Optional[np.ndarray] = None
        self._torques_parachute_b: Optional[np.ndarray] = None
        self._forces_total_b: Optional[np.ndarray] = None
        self._torques_total_b: Optional[np.ndarray] = None
        
        # Flags
        self._cache_dirty = True
    
    # ------------------------------------------------------------------
    # Environment Updates
    # ------------------------------------------------------------------
    
    def update_environment(
        self,
        wind_vector_enu: Optional[np.ndarray] = None
    ) -> None:
        """
        Update environmental conditions.
        
        Args:
            wind_vector_enu: New wind vector in ENU frame [m/s]
        """
        if wind_vector_enu is not None:
            self.wind_vector_enu = np.array(wind_vector_enu)
        self._invalidate_cache()
    
    def update_atmosphere(self, altitude: float) -> None:
        """
        Update atmospheric properties based on altitude.
        
        Args:
            altitude: Current altitude [m]
        """
        density = self.atmosphere.give_dens(altitude)
        v_sonic = self.atmosphere.give_v_sonic(altitude)
        self._density = float(density) if density is not None else 0.0
        self._v_sonic = float(v_sonic) if v_sonic is not None else 0.0
        self._invalidate_cache()
    
    # ------------------------------------------------------------------
    # Aerodynamic Calculations
    # ------------------------------------------------------------------
    
    def calculate_aerodynamics(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculate aerodynamic forces and torques.
        
        Returns:
            tuple: (forces_aero_b, torques_aero_b) in body frame [N], [N·m]
        """
        self._ensure_cache()
        
        if self._forces_aero_b is not None and self._torques_aero_b is not None:
            return self._forces_aero_b.copy(), self._torques_aero_b.copy()
        
        # Skip if velocity is too low
        if self.state.v_norm < 1e-6:
            self._forces_aero_b = np.zeros(3)
            self._torques_aero_b = np.zeros(3)
            return self._forces_aero_b.copy(), self._torques_aero_b.copy()
        
        # Update aerodynamics
        self.aerodynamics.update(
            mach=self._mach,
            angle_attack=self._alpha,
            height=self.state.r_enu[2],  # Altitude is Z in ENU
            density=self._density
        )
        
        # Get coefficients
        cd, cl = self.aerodynamics.get_coefficients()
        cp_b = self.aerodynamics.get_center_of_pressure()
        
        # Calculate forces
        drag_force = cd * self._dynamic_pressure * self.reference_area
        lift_force = cl * self._dynamic_pressure * self.reference_area
        
        # Force vectors in body frame (drag opposite to velocity, lift perpendicular)
        # Simplified: drag in -X direction, lift in +Z direction
        forces_drag_b = np.array([-drag_force, 0.0, 0.0])
        forces_lift_b = np.array([0.0, 0.0, lift_force])
        forces_aero_b = forces_drag_b + forces_lift_b
        
        # Get center of mass
        if self.mass_properties is not None:
            # Calculate burn fraction from mass
            burn_fraction = self.mass_properties.get_burn_fraction(self.state.mass)
            cm_b = self.mass_properties.get_center_of_mass(burn_fraction)
        else:
            # Use simple approximation
            cm_b = np.array([0.5, 0.0, 0.0])
        
        # Calculate torque: cm2cp x forces
        cm2cp_b = cm_b - cp_b
        torques_aero_b = np.cross(cm2cp_b, forces_aero_b)
        
        # Cache results
        self._forces_aero_b = forces_aero_b
        self._torques_aero_b = torques_aero_b
        
        return forces_aero_b.copy(), torques_aero_b.copy()
    
    # ------------------------------------------------------------------
    # Engine Calculations
    # ------------------------------------------------------------------
    
    def calculate_engine_forces(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculate engine forces and torques.
        
        Returns:
            tuple: (forces_engine_b, torques_engine_b) in body frame [N], [N·m]
        """
        if self._forces_engine_b is not None and self._torques_engine_b is not None:
            return self._forces_engine_b.copy(), self._torques_engine_b.copy()
        
        # Update engine state
        self.engine.update(
            time=self.state.time,
            ambient_pressure=self.atmosphere.give_pressure(self.state.r_enu[2])
        )
        
        # Get thrust
        thrust = self.engine.get_thrust()
        
        # Engine force in body frame: thrust in +X direction
        # Note: Actual engine position might offset this, but simplified for now
        forces_engine_b = np.array([thrust, 0.0, 0.0])
        
        # Engine torque: assuming engine is aligned with CoM, no torque
        # In reality, engine might be offset or have gimbaling
        torques_engine_b = np.zeros(3)
        
        # Cache results
        self._forces_engine_b = forces_engine_b
        self._torques_engine_b = torques_engine_b
        
        return forces_engine_b.copy(), torques_engine_b.copy()
    
    # ------------------------------------------------------------------
    # Parachute Calculations
    # ------------------------------------------------------------------
    
    def calculate_parachute_forces(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculate parachute forces and torques.
        
        Returns:
            tuple: (forces_parachute_b, torques_parachute_b) in body frame [N], [N·m]
        """
        if self.parachute is None:
            self._forces_parachute_b = np.zeros(3)
            self._torques_parachute_b = np.zeros(3)
            return self._forces_parachute_b.copy(), self._torques_parachute_b.copy()
        
        if self._forces_parachute_b is not None and self._torques_parachute_b is not None:
            return self._forces_parachute_b.copy(), self._torques_parachute_b.copy()
        
        # Get parachute force vector in ENU frame (opposite to velocity)
        from src.utils.mattools import MatTools as Mat
        
        # Calculate relative velocity for parachute
        v_rel_enu = self.state.v_enu - self.wind_vector_enu
        parachute_force_enu = self.parachute.get_force_vector(v_rel_enu)
        
        # Convert parachute force from ENU to body frame
        # Parachute force is opposite to velocity direction
        forces_parachute_b = Mat.q_rot(parachute_force_enu, self.state.q_enu2b, 0)
        
        # Parachute typically acts at the nose or a specific attachment point
        # For simplicity, assume it acts at the center of pressure (nose)
        # This creates a small torque if not aligned with CoM
        if self.mass_properties is not None:
            burn_fraction = self.mass_properties.get_burn_fraction(self.state.mass)
            cm_b = self.mass_properties.get_center_of_mass(burn_fraction)
        else:
            cm_b = np.array([0.5, 0.0, 0.0])
        
        # Assume parachute attachment at nose (front of rocket, negative X direction)
        parachute_attachment_b = np.array([-0.5, 0.0, 0.0])
        
        # Calculate torque: (attachment - cm) x force
        lever_arm_b = parachute_attachment_b - cm_b
        torques_parachute_b = np.cross(lever_arm_b, forces_parachute_b)
        
        # Cache results
        self._forces_parachute_b = forces_parachute_b
        self._torques_parachute_b = torques_parachute_b
        
        return forces_parachute_b.copy(), torques_parachute_b.copy()
    
    # ------------------------------------------------------------------
    # Total Force/Torque Calculations
    # ------------------------------------------------------------------
    
    def calculate_forces(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculate total forces and torques acting on the rocket.
        
        Returns:
            tuple: (forces_total_b, torques_total_b) in body frame [N], [N·m]
        """
        # Calculate individual contributions
        forces_aero_b, torques_aero_b = self.calculate_aerodynamics()
        forces_engine_b, torques_engine_b = self.calculate_engine_forces()
        forces_parachute_b, torques_parachute_b = self.calculate_parachute_forces()
        
        # Sum forces and torques
        forces_total_b = forces_aero_b + forces_engine_b + forces_parachute_b
        torques_total_b = torques_aero_b + torques_engine_b + torques_parachute_b
        
        # Cache results
        self._forces_total_b = forces_total_b
        self._torques_total_b = torques_total_b
        
        return forces_total_b.copy(), torques_total_b.copy()
    
    # ------------------------------------------------------------------
    # Gravity Calculations
    # ------------------------------------------------------------------
    
    def calculate_gravity_enu(self) -> np.ndarray:
        """
        Calculate gravitational acceleration in ENU frame.
        
        Returns:
            np.ndarray: Gravity vector in ENU frame [m/s²]
        """
        from src.utils.simulation_constants import EngineConstants as EC
        
        # Standard gravity for ISP calculations
        g0 = EC.STANDARD_GRAVITY_G0  # m/s²
        
        # Gravity acts downward (negative Z in ENU)
        return np.array([0.0, 0.0, -g0])
    
    # ------------------------------------------------------------------
    # Dynamics Equations
    # ------------------------------------------------------------------
    
    def calculate_accelerations(
        self,
        forces_b: np.ndarray,
        mass: float,
        inertia_b: np.ndarray,
        torques_b: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculate linear and angular accelerations.
        
        Args:
            forces_b: Total forces in body frame [N]
            mass: Current mass [kg]
            inertia_b: Moments of inertia [Ixx, Iyy, Izz] [kg·m²]
            torques_b: Total torques in body frame [N·m]
        
        Returns:
            tuple: (accel_b, alpha_b) - linear and angular accelerations
                   [m/s²], [rad/s²]
        """
        # Validate mass
        if mass <= 0:
            raise ValueError(f"Mass must be positive, got {mass}")
        
        # Linear acceleration: F = ma -> a = F/m
        accel_b = forces_b / mass
        
        # Angular acceleration: tau = I * alpha -> alpha = inv(I) * tau
        # For now, use simplified diagonal inertia matrix
        inertia_matrix = np.diag(inertia_b)
        try:
            inertia_inv = np.linalg.inv(inertia_matrix)
        except np.linalg.LinAlgError:
            # Fallback: use pseudo-inverse or identity
            inertia_inv = np.eye(3) / np.max(inertia_b)
        
        alpha_b = np.dot(inertia_inv, torques_b - np.cross(self.state.w_b, np.dot(inertia_matrix, self.state.w_b)))
        
        return accel_b, alpha_b
    
    # ------------------------------------------------------------------
    # Cache Management
    # ------------------------------------------------------------------
    
    def _ensure_cache(self) -> None:
        """Calculate and cache derived values if needed."""
        if not self._cache_dirty:
            return
        
        self._calculate_derived()
        self._cache_dirty = False
    
    def _calculate_derived(self) -> None:
        """Calculate all derived aerodynamic values."""
        # Calculate relative velocity (rocket - wind)
        v_rel_enu = self.state.v_enu - self.wind_vector_enu
        v_rel_norm = np.linalg.norm(v_rel_enu)
        
        # Update atmosphere
        altitude = self.state.r_enu[2]
        density = self.atmosphere.give_dens(altitude)
        v_sonic = self.atmosphere.give_v_sonic(altitude)
        self._density = float(density) if density is not None else 0.0
        self._v_sonic = float(v_sonic) if v_sonic is not None else 0.0
        
        # Calculate Mach number
        if self._v_sonic > 0 and v_rel_norm > 0:
            self._mach = float(v_rel_norm / self._v_sonic)
        else:
            self._mach = 0.0
        
        # Calculate dynamic pressure
        self._dynamic_pressure = float(0.5 * self._density * (v_rel_norm ** 2))
        
        # Calculate angle of attack (simplified: angle between velocity and X-axis in body frame)
        # This is a simplified calculation; real implementation would use relative velocity
        from src.utils.mattools import MatTools as Mat
        v_b = Mat.q_rot(v_rel_enu, self.state.q_enu2b, 0)
        if v_rel_norm > 0:
            # Angle of attack: angle between velocity vector and body X-axis
            v_x = v_b[0]
            v_z = v_b[2]
            self._alpha = float(np.degrees(np.arctan2(v_z, v_x)))
        else:
            self._alpha = 0.0
    
    def _invalidate_cache(self) -> None:
        """Mark cached values as dirty."""
        self._cache_dirty = True
        self._forces_aero_b = None
        self._torques_aero_b = None
        self._forces_engine_b = None
        self._torques_engine_b = None
        self._forces_total_b = None
        self._torques_total_b = None
    
    # ------------------------------------------------------------------
    # Getters for cached values
    # ------------------------------------------------------------------
    
    @property
    def forces_aero_b(self) -> np.ndarray:
        """Aerodynamic forces in body frame [N]"""
        self._ensure_cache()
        return self._forces_aero_b.copy() if self._forces_aero_b is not None else np.zeros(3)
    
    @property
    def torques_aero_b(self) -> np.ndarray:
        """Aerodynamic torques in body frame [N·m]"""
        self._ensure_cache()
        return self._torques_aero_b.copy() if self._torques_aero_b is not None else np.zeros(3)
    
    @property
    def forces_engine_b(self) -> np.ndarray:
        """Engine forces in body frame [N]"""
        return self._forces_engine_b.copy() if self._forces_engine_b is not None else np.zeros(3)
    
    @property
    def torques_engine_b(self) -> np.ndarray:
        """Engine torques in body frame [N·m]"""
        return self._torques_engine_b.copy() if self._torques_engine_b is not None else np.zeros(3)
    
    @property
    def forces_total_b(self) -> np.ndarray:
        """Total forces in body frame [N]"""
        return self._forces_total_b.copy() if self._forces_total_b is not None else np.zeros(3)
    
    @property
    def torques_total_b(self) -> np.ndarray:
        """Total torques in body frame [N·m]"""
        return self._torques_total_b.copy() if self._torques_total_b is not None else np.zeros(3)
    
    @property
    def mach(self) -> float:
        """Current Mach number [-]"""
        self._ensure_cache()
        return self._mach
    
    @property
    def alpha(self) -> float:
        """Current angle of attack [deg]"""
        self._ensure_cache()
        return self._alpha
    
    @property
    def dynamic_pressure(self) -> float:
        """Current dynamic pressure [Pa]"""
        self._ensure_cache()
        return self._dynamic_pressure


__all__ = ['RocketDynamics']
