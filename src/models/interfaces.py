# Author: Nicolas Sturm
#         Rocket Simulator - Clean Architecture Refactoring
#         Phase 1: Dependency Inversion via Interfaces

"""
Interfaces Module for Dependency Inversion

This module defines abstract base classes (interfaces) for the rocket simulation
components, enabling loose coupling and improved testability.

Interfaces:
    IEngine: Interface for propulsion systems
    IAerodynamics: Interface for aerodynamic calculations
    IParachute: Interface for recovery systems
    IAtmosphere: Interface for atmospheric models

Design Principles:
    - Dependency Inversion: High-level modules depend on abstractions, not concrete implementations
    - Interface Segregation: Clients should not be forced to depend on interfaces they don't use
    - Liskov Substitution: Implementations should be substitutable for their interfaces

Usage:
    from src.models.interfaces import IEngine, IAerodynamics
    
    class MyEngine(IEngine):
        def update(self, time: float, ambient_pressure: float) -> None:
            ...
        
        def get_performance_metrics(self) -> dict:
            ...
    
    # In Rocket class:
    def __init__(self, engine: IEngine, aerodynamics: IAerodynamics):
        self.engine = engine  # Accepts any IEngine implementation
        self.aerodynamics = aerodynamics
"""

from abc import ABC, abstractmethod
import numpy as np
from typing import Optional


# =============================================================================
# Engine Interface
# =============================================================================

class IEngine(ABC):
    """
    Abstract interface for rocket engine propulsion systems.
    
    This interface defines the contract that all engine implementations must fulfill,
    allowing the Rocket class to work with any propulsion system without tight coupling.
    
    Implementations:
        - EnhancedEngine: Full thermodynamics, thrust curves, performance tracking
        - SimpleEngine: Simplified constant-thrust model (for testing/quick sims)
        - ExperimentalEngine: Data-driven engine from test fires
    
    Example:
        >>> class TestEngine(IEngine):
        ...     def update(self, time: float, ambient_pressure: float) -> None:
        ...         self._thrust = 1000.0
        ...     
        ...     def get_performance_metrics(self) -> dict:
        ...         return {'thrust': 1000.0, 'mass_flow': 0.5}
        ...     
        ...     def get_thrust(self) -> float:
        ...         return self._thrust
        ...     
        ...     def get_mass_flow(self) -> float:
        ...         return 0.5
    """
    
    @abstractmethod
    def update(self, time: float, ambient_pressure: Optional[float] = None) -> None:
        """
        Update engine state to the given time and ambient conditions.
        
        This is the primary method called during the simulation loop to advance
        the engine's internal state and recalculate performance metrics.
        
        Args:
            time: Current simulation time in seconds [s]
            ambient_pressure: Current ambient pressure in Pascals [Pa]. 
                           If None, uses the engine's last known pressure.
        
        Returns:
            None. Updates internal state. Use getter methods to retrieve values.
        """
        pass
    
    @abstractmethod
    def get_performance_metrics(self) -> dict:
        """
        Get comprehensive performance metrics from the engine.
        
        Returns a dictionary containing all relevant engine performance data.
        This provides a consistent interface regardless of the underlying 
        implementation (analytical vs. experimental thrust curves).
        
        Returns:
            dict: Dictionary containing at least:
                - 'thrust': Current thrust in Newtons [N]
                - 'mass_flow': Current mass flow rate in kg/s [kg/s]
                - 'specific_impulse': Current specific impulse in seconds [s]
                - 'chamber_pressure': Chamber pressure in Pascals [Pa]
                - 'exit_velocity': Exhaust velocity in m/s [m/s]
                
            Additional keys may include:
                - 'thrust_source': 'analytical' or 'experimental'
                - 'propellant_consumed': Propellant consumed in kg [kg]
                - 'remaining_propellant': Remaining propellant in kg [kg]
                - 'total_impulse_delivered': Total impulse in N·s [N·s]
                - 'burnout_reached': Boolean indicating if burnout has occurred
        """
        pass
    
    @abstractmethod
    def get_thrust(self) -> float:
        """
        Get current thrust output.
        
        Returns:
            float: Current thrust in Newtons [N]. Returns 0.0 if engine is off or burned out.
        """
        pass
    
    @abstractmethod
    def get_mass_flow(self) -> float:
        """
        Get current mass flow rate.
        
        Returns:
            float: Current mass flow rate in kg/s [kg/s]. Returns 0.0 if no flow.
        """
        pass
    
    # Optional: Property accessors for convenience
    @property
    def thrust(self) -> float:
        """Current thrust [N]"""
        return self.get_thrust()
    
    @property
    def mass_flow(self) -> float:
        """Current mass flow rate [kg/s]"""
        return self.get_mass_flow()


# =============================================================================
# Aerodynamics Interface
# =============================================================================

class IAerodynamics(ABC):
    """
    Abstract interface for aerodynamic calculation systems.
    
    This interface defines the contract for aerodynamic coefficient calculations,
    allowing the Rocket class to work with any aerodynamics model.
    
    Implementations:
        - Aerodynamics: Unified model (SimpleAerodynamics is an alias)
        - CFDAerodynamics: CFD data-driven model
    
    Example:
        >>> class TestAerodynamics(IAerodynamics):
        ...     def __init__(self):
        ...         self._cd = 0.5
        ...         self._cl = 0.0
        ...         self._cp = np.array([0.5, 0, 0])
        ...     
        ...     def update(self, mach: float, angle_attack: float, 
        ...                height: float, density: float) -> None:
        ...         self._cd = 0.5
        ...         self._cl = 0.01 * angle_attack
        ...     
        ...     def get_coefficients(self) -> tuple[float, float]:
        ...         return self._cd, self._cl
        ...     
        ...     def get_center_of_pressure(self) -> np.ndarray:
        ...         return self._cp
    """
    
    @abstractmethod
    def update(self, mach: float, angle_attack: float, height: float, 
               density: float) -> None:
        """
        Update aerodynamic coefficients based on flight conditions.
        
        This method recalculates all aerodynamic coefficients (drag, lift, etc.)
        based on the current flight conditions.
        
        Args:
            mach: Mach number [-] (dimensionless)
            angle_attack: Angle of attack in degrees [deg]
            height: Altitude above sea level in meters [m]
            density: Air density in kg/m³ [kg/m³]
        
        Returns:
            None. Updates internal state. Use getter methods to retrieve values.
        """
        pass
    
    @abstractmethod
    def get_coefficients(self) -> tuple[float, float]:
        """
        Get drag and lift coefficients.
        
        Returns:
            tuple[float, float]: (drag_coefficient, lift_coefficient)
                - drag_coefficient: Cd [-] (dimensionless)
                - lift_coefficient: Cl [-] (dimensionless)
        """
        pass
    
    @abstractmethod
    def get_center_of_pressure(self) -> np.ndarray:
        """
        Get center of pressure position in body frame.
        
        Returns:
            np.ndarray: Center of pressure position as [x, y, z] in body frame [m]
        """
        pass
    
    @abstractmethod
    def get_stability_margin(self) -> float:
        """
        Get static stability margin.
        
        Returns:
            float: Stability margin in calibers (positive = stable) [calibers]
        """
        pass
    
    @abstractmethod
    def get_aerodynamic_forces(self, dynamic_pressure: float, 
                               reference_area: float) -> dict:
        """
        Calculate aerodynamic forces given dynamic pressure and reference area.
        
        Args:
            dynamic_pressure: Dynamic pressure in Pascals [Pa] (0.5 * rho * v²)
            reference_area: Reference area in square meters [m²]
        
        Returns:
            dict: Dictionary containing:
                - 'drag': Drag force in Newtons [N]
                - 'lift': Lift force in Newtons [N]
                - 'cd': Drag coefficient [-]
                - 'cl': Lift coefficient [-]
                - 'cp_position': Center of pressure position [x, y, z] [m]
                - 'stability_margin': Stability margin in calibers
        """
        pass
    
    # Optional: Property accessors for convenience
    @property
    def cd(self) -> float:
        """Drag coefficient [-]"""
        return self.get_coefficients()[0]
    
    @property
    def cl(self) -> float:
        """Lift coefficient [-]"""
        return self.get_coefficients()[1]
    
    @property
    def xcp(self) -> np.ndarray:
        """Center of pressure position [m]"""
        return self.get_center_of_pressure()


# =============================================================================
# Parachute Interface
# =============================================================================

class IParachute(ABC):
    """
    Abstract interface for recovery/parachute systems.
    
    This interface defines the contract for parachute systems that provide
    drag forces during descent and recovery phases.
    
    Implementations:
        - Parachute: Standard parachute model with deployment logic
        - DualStageParachute: Drogue + main parachute system
        - NoneParachute: Null object pattern for rockets without parachutes
    
    Example:
        >>> class TestParachute(IParachute):
        ...     def __init__(self):
        ...         self._deployed = False
        ...         self._diameter = 5.0
        ...     
        ...     def update(self, velocity: float, altitude: float) -> None:
        ...         self._deployed = altitude < 1000 and velocity > 0
        ...     
        ...     def get_force(self) -> float:
        ...         if self._deployed:
        ...             return 1000.0  # Simplified
        ...         return 0.0
        ...     
        ...     def is_deployed(self) -> bool:
        ...         return self._deployed
        ...     
        ...     def get_drag_coefficient(self) -> float:
        ...         return 1.5 if self._deployed else 0.0
    """
    
    @abstractmethod
    def update(self, velocity: float, altitude: float, density: float) -> None:
        """
        Update parachute state based on flight conditions.
        
        This method determines whether the parachute should be deployed based on
        altitude, velocity, and other flight parameters.
        
        Args:
            velocity: Current velocity magnitude in m/s [m/s]
            altitude: Current altitude above sea level in meters [m]
            density: Current air density in kg/m³ [kg/m³]
        
        Returns:
            None. Updates internal state. Use getter methods to retrieve values.
        """
        pass
    
    @abstractmethod
    def get_force(self) -> float:
        """
        Get current parachute drag force.
        
        Returns:
            float: Current drag force in Newtons [N]. Returns 0.0 if not deployed.
        """
        pass
    
    @abstractmethod
    def is_deployed(self) -> bool:
        """
        Check if parachute is deployed.
        
        Returns:
            bool: True if parachute is deployed and active, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_drag_coefficient(self) -> float:
        """
        Get current parachute drag coefficient.
        
        Returns:
            float: Drag coefficient [-] (dimensionless). Returns 0.0 if not deployed.
        """
        pass
    
    @abstractmethod
    def get_force_vector(self, velocity_vector: np.ndarray) -> np.ndarray:
        """
        Get parachute force vector in the opposite direction of velocity.
        
        Args:
            velocity_vector: Current velocity vector [vx, vy, vz] in any frame [m/s]
        
        Returns:
            np.ndarray: Force vector [fx, fy, fz] opposite to velocity [N]
        """
        pass
    
    # Optional: Property accessors for convenience
    @property
    def deployed(self) -> bool:
        """Whether parachute is deployed"""
        return self.is_deployed()
    
    @property
    def drag_force(self) -> float:
        """Current drag force [N]"""
        return self.get_force()


# =============================================================================
# Atmosphere Interface
# =============================================================================

class IAtmosphere(ABC):
    """
    Abstract interface for atmospheric models.
    
    This interface defines the contract for atmospheric property calculations,
    allowing different atmosphere models to be used interchangeably.
    
    Implementations:
        - Atmosphere: Standard ISA atmosphere model
        - CustomAtmosphere: User-defined atmosphere profiles
        - ConstantAtmosphere: Simplified constant-density model (for testing)
    
    Example:
        >>> class TestAtmosphere(IAtmosphere):
        ...     def give_dens(self, altitude: float) -> float:
        ...         return 1.225  # Sea level density
        ...     
        ...     def give_temp(self, altitude: float) -> float:
        ...         return 288.15  # Sea level temperature
        ...     
        ...     def give_v_sonic(self, altitude: float) -> float:
        ...         return 340.0  # Sea level speed of sound
        ...     
        ...     def give_pressure(self, altitude: float) -> float:
        ...         return 101325.0  # Sea level pressure
    """
    
    @abstractmethod
    def give_dens(self, altitude: float) -> float:
        """
        Get air density at given altitude.
        
        Args:
            altitude: Altitude above sea level in meters [m]
        
        Returns:
            float: Air density in kg/m³ [kg/m³]
        """
        pass
    
    @abstractmethod
    def give_temp(self, altitude: float) -> float:
        """
        Get air temperature at given altitude.
        
        Args:
            altitude: Altitude above sea level in meters [m]
        
        Returns:
            float: Air temperature in Kelvin [K]
        """
        pass
    
    @abstractmethod
    def give_v_sonic(self, altitude: float) -> float:
        """
        Get speed of sound at given altitude.
        
        Args:
            altitude: Altitude above sea level in meters [m]
        
        Returns:
            float: Speed of sound in m/s [m/s]
        """
        pass
    
    @abstractmethod
    def give_pressure(self, altitude: float) -> float:
        """
        Get atmospheric pressure at given altitude.
        
        Args:
            altitude: Altitude above sea level in meters [m]
        
        Returns:
            float: Atmospheric pressure in Pascals [Pa]
        """
        pass


# =============================================================================
# Mass Properties Interface
# =============================================================================

class IMassProperties(ABC):
    """
    Abstract interface for mass properties calculations.
    
    This interface provides access to rocket mass, center of mass, and inertia properties
    that change during flight (e.g., due to propellant consumption).
    
    Implementations:
        - MassProperties: Interpolated mass properties from before/after burn states
    """
    
    @abstractmethod
    def get_mass(self, burn_fraction: float) -> float:
        """
        Get current total mass based on burn fraction.
        
        Args:
            burn_fraction: Fraction of propellant burned (0.0 to 1.0) [-]
        
        Returns:
            float: Current total mass in kg [kg]
        """
        pass
    
    @abstractmethod
    def get_center_of_mass(self, burn_fraction: float) -> np.ndarray:
        """
        Get current center of mass position in body frame.
        
        Args:
            burn_fraction: Fraction of propellant burned (0.0 to 1.0) [-]
        
        Returns:
            np.ndarray: Center of mass position [x, y, z] in body frame [m]
        """
        pass
    
    @abstractmethod
    def get_inertia(self, burn_fraction: float) -> np.ndarray:
        """
        Get current moments of inertia in body frame.
        
        Args:
            burn_fraction: Fraction of propellant burned (0.0 to 1.0) [-]
        
        Returns:
            np.ndarray: Moments of inertia [Ixx, Iyy, Izz] in body frame [kg·m²]
        """
        pass
    
    @abstractmethod
    def get_burn_fraction(self, current_mass: float) -> float:
        """
        Calculate burn fraction from current mass.
        
        Args:
            current_mass: Current total mass [kg]
        
        Returns:
            float: Burn fraction (0.0 to 1.0) [-]
        """
        pass


# =============================================================================
# Exported Symbols
# =============================================================================

__all__ = [
    'IEngine',
    'IAerodynamics', 
    'IParachute',
    'IAtmosphere',
    'IMassProperties',
]
