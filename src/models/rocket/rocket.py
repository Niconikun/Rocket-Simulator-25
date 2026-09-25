# Author: Nicolas Sturm
#         Rocket Simulator - Clean Architecture Refactoring
#         Phase 2: Rocket Composition Root

"""
Rocket Module - Composition Root

This is the main Rocket class that composes all the individual components
using dependency injection. It serves as the public interface for rocket simulation.

Architecture:
    Rocket (this class)
    ├── RocketState: Pure state management
    ├── RocketDynamics: Force and torque calculations
    ├── RocketSimulation: Numerical integration and history
    └── External Dependencies (injected):
        ├── IEngine: Propulsion system
        ├── IAerodynamics: Aerodynamic calculations
        ├── IAtmosphere: Atmospheric model
        └── IMassProperties: Mass property calculations

Design Principles:
    - Composition over inheritance
    - Dependency injection (interfaces, not concrete classes)
    - Single responsibility for each component
    - Loose coupling between components
    - Testable through mock dependencies

Usage:
    from src.models.rocket import Rocket
    from src.models.engine import EnhancedEngine
    from src.models.aerodynamics import Aerodynamics
    from src.models.atmosphere import Atmosphere
    from src.models.mass_properties import MassProperties
    
    # Create dependencies
    engine = EnhancedEngine(
        time=0.0, burn_time=10.0, ambient_pressure=101325.0,
        nozzle_exit_diameter=0.1, propellant_mass=5.0,
        specific_impulse=250.0, mean_thrust=1000.0, max_thrust=1200.0,
        mean_chamber_pressure=1000000.0, max_chamber_pressure=1200000.0,
        thrust_to_weight_ratio=50.0
    )
    
    # Create rocket with dependency injection
    rocket = Rocket(
        r_enu_0=np.array([0, 0, 0]),
        v_enu_0=np.array([0, 0, 10]),
        q_enu2b_0=np.array([0, 0, 0, 1]),
        w_enu_0=np.array([0, 0, 0]),
        initial_mass=10.0,
        engine=engine,
        atmosphere=Atmosphere(15.0),
        reference_area=0.01
    )
    
    # Run simulation
    for i in range(100):
        rocket.step(dt=0.1)
    
    # Get current state
    position = rocket.state.r_enu
    velocity = rocket.state.v_enu
"""

import numpy as np
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.interfaces import IEngine, IAerodynamics, IAtmosphere, IMassProperties
    from src.models.mass_properties import MassProperties

from src.models.rocket.state import RocketState
from src.models.rocket.dynamics import RocketDynamics
from src.models.rocket.simulation import RocketSimulation
from src.models.atmosphere import Atmosphere


class Rocket:
    """
    Main rocket simulation class using clean architecture.
    
    This class composes all rocket simulation components and provides a clean,
    testable interface for rocket flight simulation. It uses dependency injection
    to accept interface types rather than creating concrete implementations internally.
    
    Attributes:
        state: Current rocket state (RocketState)
        dynamics: Dynamics calculator (RocketDynamics)
        simulation: Simulation manager (RocketSimulation)
        engine: Propulsion system (IEngine)
        aerodynamics: Aerodynamic calculations (IAerodynamics)
        atmosphere: Atmospheric model (IAtmosphere)
        mass_properties: Mass property calculations (IMassProperties)
    
    Key Differences from Original Rocket:
        - Uses dependency injection (accepts IEngine, IAerodynamics, etc.)
        - Separated into focused components (State, Dynamics, Simulation)
        - No direct instantiation of engine or aerodynamics
        - No tight coupling between components
        - Easier to test and extend
    """
    
    def __init__(
        self,
        r_enu_0: np.ndarray,
        v_enu_0: np.ndarray,
        q_enu2b_0: np.ndarray,
        w_enu_0: np.ndarray,
        initial_mass: float,
        engine: Optional['IEngine'] = None,
        aerodynamics: Optional['IAerodynamics'] = None,
        atmosphere: Optional['IAtmosphere'] = None,
        mass_properties: Optional['IMassProperties'] = None,
        reference_area: float = 0.01,
        propellant_mass: float = 0.0,
        wind_vector_enu: Optional[np.ndarray] = None
    ) -> None:
        """
        Initialize rocket with state and dependencies.
        
        Args:
            r_enu_0: Initial position in ENU frame [m]
            v_enu_0: Initial velocity in ENU frame [m/s]
            q_enu2b_0: Initial quaternion from ENU to body frame [-]
            w_enu_0: Initial angular velocity in ENU frame [rad/s]
            initial_mass: Initial total mass [kg]
            engine: Engine instance implementing IEngine (optional)
            aerodynamics: Aerodynamics instance implementing IAerodynamics (optional)
            atmosphere: Atmosphere instance implementing IAtmosphere (optional)
            mass_properties: Mass properties instance (optional)
            reference_area: Reference area for aerodynamics [m²]
            propellant_mass: Initial propellant mass [kg]
            wind_vector_enu: Initial wind vector in ENU frame [m/s]
        
        Raises:
            ValueError: If required dependencies are not provided
        """
        # Create or use provided state
        self._initial_mass = initial_mass
        self._propellant_mass = propellant_mass
        
        # Create initial state
        self.state = RocketState(
            r_enu=r_enu_0,
            v_enu=v_enu_0,
            q_enu2b=q_enu2b_0,
            w_enu=w_enu_0,
            mass=initial_mass
        )
        
        # Create or use provided atmosphere
        if atmosphere is None:
            from src.models.atmosphere import Atmosphere
            atmosphere = Atmosphere(15.0)  # Default: 15°C at sea level
        self.atmosphere = atmosphere
        
        # Store other dependencies
        self.engine = engine
        self.aerodynamics = aerodynamics
        self.mass_properties = mass_properties
        self.reference_area = reference_area
        self.wind_vector_enu = np.zeros(3) if wind_vector_enu is None else np.array(wind_vector_enu)
        
        # Create dynamics (requires engine, aerodynamics is optional)
        if engine is None:
            raise ValueError("Engine is required. Provide an IEngine implementation.")
        
        # If aerodynamics is None, create a simple placeholder
        # This will be updated later via set_aerodynamics()
        if aerodynamics is None:
            from src.models.aerodynamics import Aerodynamics
            aerodynamics = Aerodynamics()
            self.aerodynamics = aerodynamics
        
        # Create dynamics calculator
        self.dynamics = RocketDynamics(
            state=self.state,
            engine=self.engine,
            aerodynamics=self.aerodynamics,
            atmosphere=self.atmosphere,
            reference_area=self.reference_area,
            mass_properties=self.mass_properties,
            wind_vector_enu=self.wind_vector_enu
        )
        
        # Create simulation manager
        self.simulation = RocketSimulation(
            state=self.state,
            dynamics=self.dynamics
        )
    
    # ------------------------------------------------------------------
    # Simulation Control
    # ------------------------------------------------------------------
    
    def step(self, dt: float) -> None:
        """
        Advance simulation by one time step.
        
        Args:
            dt: Time step size [s]
        """
        # Update environment
        self.dynamics.update_environment(wind_vector_enu=self.wind_vector_enu)
        self.dynamics.update_atmosphere(self.state.r_enu[2])
        
        # Update engine state BEFORE integration to get current thrust/mass flow
        if self.engine is not None:
            self.engine.update(
                time=self.state.time,
                ambient_pressure=self.atmosphere.give_pressure(self.state.r_enu[2])
            )
        
        # Update mass based on engine mass flow
        if self.engine is not None:
            mass_flow = self.engine.get_mass_flow()
            self.state.mass -= mass_flow * dt
        
        # Perform integration step
        self.simulation.step(dt)
    
    def run(self, duration: float, dt: float) -> None:
        """
        Run simulation for a specified duration.
        
        Args:
            duration: Total simulation duration [s]
            dt: Time step size [s]
        """
        num_steps = int(duration / dt)
        for _ in range(num_steps):
            self.step(dt)
    
    def reset(self) -> None:
        """Reset simulation to initial state."""
        self.state = RocketState(
            r_enu=self.state.r_enu * 0,  # Reset to origin
            v_enu=np.zeros(3),
            q_enu2b=np.array([0, 0, 0, 1]),
            w_enu=np.zeros(3),
            mass=self._initial_mass
        )
        self.simulation.reset()
    
    # ------------------------------------------------------------------
    # Dependency Setters
    # ------------------------------------------------------------------
    
    def set_engine(self, engine: 'IEngine') -> None:
        """
        Set the engine implementation.
        
        Args:
            engine: Engine instance implementing IEngine
        """
        self.engine = engine
        self.dynamics.engine = engine
    
    def set_aerodynamics(self, aerodynamics: 'IAerodynamics') -> None:
        """
        Set the aerodynamics implementation.
        
        Args:
            aerodynamics: Aerodynamics instance implementing IAerodynamics
        """
        self.aerodynamics = aerodynamics
        self.dynamics.aerodynamics = aerodynamics
    
    def set_atmosphere(self, atmosphere: 'IAtmosphere') -> None:
        """
        Set the atmosphere implementation.
        
        Args:
            atmosphere: Atmosphere instance implementing IAtmosphere
        """
        self.atmosphere = atmosphere
        self.dynamics.atmosphere = atmosphere
    
    def set_mass_properties(self, mass_properties: 'IMassProperties') -> None:
        """
        Set the mass properties implementation.
        
        Args:
            mass_properties: Mass properties instance implementing IMassProperties
        """
        self.mass_properties = mass_properties
        self.dynamics.mass_properties = mass_properties
    
    def set_wind(self, wind_vector_enu: np.ndarray) -> None:
        """
        Set the wind vector.
        
        Args:
            wind_vector_enu: Wind vector in ENU frame [m/s]
        """
        self.wind_vector_enu = np.array(wind_vector_enu)
        self.dynamics.update_environment(wind_vector_enu=wind_vector_enu)
    
    # ------------------------------------------------------------------
    # Convenience Getters
    # ------------------------------------------------------------------
    
    @property
    def position(self) -> np.ndarray:
        """Current position [m]"""
        return self.state.r_enu
    
    @property
    def velocity(self) -> np.ndarray:
        """Current velocity [m/s]"""
        return self.state.v_enu
    
    @property
    def mass(self) -> float:
        """Current mass [kg]"""
        return self.state.mass
    
    @property
    def time(self) -> float:
        """Current simulation time [s]"""
        return self.state.time
    
    @property
    def thrust(self) -> float:
        """Current thrust [N]"""
        if self.engine is not None:
            return self.engine.get_thrust()
        return 0.0
    
    @property
    def mach(self) -> float:
        """Current Mach number [-]"""
        return self.dynamics.mach
    
    @property
    def alpha(self) -> float:
        """Current angle of attack [deg]"""
        return self.dynamics.alpha
    
    # ------------------------------------------------------------------
    # History Access
    # ------------------------------------------------------------------
    
    def get_history_positions(self) -> np.ndarray:
        """Get history of positions."""
        return self.simulation.get_history_array('positions')
    
    def get_history_velocities(self) -> np.ndarray:
        """Get history of velocities."""
        return self.simulation.get_history_array('velocities')
    
    def get_history_times(self) -> np.ndarray:
        """Get history of times."""
        return self.simulation.get_history_array('times')
    
    def get_history_masses(self) -> np.ndarray:
        """Get history of masses."""
        return self.simulation.get_history_array('masses')
    
    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------
    
    def get_state_dict(self) -> dict:
        """
        Get current state as a dictionary.
        
        Returns:
            dict: Current state values
        """
        return {
            'time': self.state.time,
            'position': self.state.r_enu.tolist(),
            'velocity': self.state.v_enu.tolist(),
            'attitude': self.state.q_enu2b.tolist(),
            'mass': self.state.mass,
            'yaw': self.state.yaw,
            'pitch': self.state.pitch,
            'roll': self.state.roll,
            'thrust': self.thrust,
            'mach': self.mach,
            'alpha': self.alpha
        }
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Rocket(time={self.state.time:.2f}s, "
            f"mass={self.state.mass:.2f}kg, "
            f"pos={self.state.r_enu.tolist()}, "
            f"vel={self.state.v_enu.tolist()})"
        )


# Backward compatibility: keep the same name for the main class
RocketClass = Rocket

__all__ = ['Rocket', 'RocketClass']
