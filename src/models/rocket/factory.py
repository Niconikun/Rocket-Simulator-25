# Author: Nicolas Sturm
#         Rocket Simulator - Clean Architecture Refactoring
#         Phase 4: Rocket Factory

"""
Rocket Factory Module

This module provides factory functions for creating Rocket instances with proper
dependency injection, making it easier to migrate from the legacy monolithic
Rocket to the new component-based architecture.

This implementation uses the Builder pattern for cleaner rocket construction
and better separation of concerns.

Usage:
    from src.models.rocket.factory import (
        RocketBuilder,
        create_rocket_from_config,
        create_rocket
    )
    
    # Option 1: Use builder pattern for programmatic construction
    builder = RocketBuilder()
    rocket = builder\
        .with_position(np.array([0, 0, 0]))\
        .with_velocity(np.array([0, 0, 10]))\
        .with_engine_config(engine_config)\\n        .with_wind_model(wind_model)\\n        .with_parachute(parachute)\\n        .build()
    
    # Option 2: Create from configuration file
    rocket = create_rocket_from_config(
        r_enu_0=np.array([0, 0, 0]),
        v_enu_0=np.array([0, 0, 10]),
        q_enu2b_0=np.array([0, 0, 0, 1]),
        w_enu_0=np.array([0, 0, 0]),
        initial_mass=10.0,
        rocket_name='my_rocket',
        wind_model=wind_model,
        parachute_config={'diameter': 1.0, 'Cd': 1.5}
    )
    
    # Then use it in simulation
    rocket.step(dt=0.1)
    
    # Or use the simulation helper
    results = run_simulation(rocket, runtime=10.0, timestep=0.1)

Design Principles:
    - Factory pattern with Builder for creating properly configured Rocket instances
    - Dependency injection for all components
    - Separation of configuration from instantiation
    - Gradual migration path from legacy to new architecture
    - Clear separation between creation and usage
    - Type safety and comprehensive error handling
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple, Union
from pathlib import Path

import numpy as np

from src.models.rocket.rocket import Rocket as NewRocket
from src.models.rocket.state import RocketState
from src.models.atmosphere import Atmosphere
from src.utils.simulation_constants import RocketConstants as RC
from src.models.engine import EnhancedEngine
from src.models.aerodynamics import Aerodynamics
from src.models.mass_properties import MassProperties
from src.models.wind import WindModel, LogarithmicWind, ConstantWind
from src.models.parachute import Parachute
from src.models.interfaces import IEngine, IAerodynamics, IAtmosphere, IMassProperties

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exceptions
# =============================================================================

class RocketConfigurationError(ValueError):
    """Raised when rocket configuration is invalid or incomplete."""
    pass


class RocketFileNotFoundError(FileNotFoundError):
    """Raised when a rocket configuration file is not found."""
    pass


# =============================================================================
# Data Classes for Configuration
# =============================================================================

@dataclass
class EngineConfig:
    """Configuration for engine creation."""
    burn_time: float
    ambient_pressure: float = RC.DEFAULT_PRESSURE
    nozzle_exit_diameter: float = 0.1
    propellant_mass: float = 1.5
    specific_impulse: float = 250.0
    mean_thrust: float = 1000.0
    max_thrust: float = 1200.0
    mean_chamber_pressure: float = 1000000.0
    max_chamber_pressure: float = 1200000.0
    thrust_to_weight_ratio: float = 50.0
    thrust_curve_file: Optional[str] = None
    thrust_curve_unit: str = 'N'
    thrust_curve_mode: str = 'analytical'


@dataclass
class ParachuteConfig:
    """Configuration for parachute creation."""
    name: str = 'Main Parachute'
    diameter: float = 1.0
    Cd: float = 1.5
    material: str = 'ripstop_nylon'
    inflation_time: float = 0.5
    deployment_altitude: float = 300.0
    min_velocity: float = 5.0
    max_velocity: float = 100.0
    drogue_enabled: bool = False
    drogue_diameter: float = 0.3
    drogue_Cd: float = 1.5
    drogue_deployment_altitude: float = 600.0
    drogue_inflation_time: float = 0.2


@dataclass
class MassPropertiesConfig:
    """Configuration for mass properties creation."""
    mass_before: float
    mass_after: float
    cm_before: Dict[str, float]
    cm_after: Dict[str, float]
    inertia_before: Dict[str, float]
    inertia_after: Dict[str, float]


@dataclass
class AerodynamicsConfig:
    """Configuration for aerodynamics creation."""
    mach: float = 0.0
    angle_attack: float = 0.0
    height: float = 0.0
    reference_area: float = 0.01
    geometry: Dict[str, Any] = field(default_factory=dict)
    fuselage: Dict[str, Any] = field(default_factory=dict)
    nosecone: Dict[str, Any] = field(default_factory=dict)
    rear_section: Dict[str, Any] = field(default_factory=dict)
    fins: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Rocket Builder (Builder Pattern)
# =============================================================================

class RocketBuilder:
    """
    Builder class for creating Rocket instances with a fluent interface.
    
    This class provides a clean, type-safe way to construct Rocket instances
    with all their dependencies, using the Builder pattern.
    
    Usage:
        builder = RocketBuilder()
        rocket = builder\
            .with_position(np.array([0, 0, 0]))\
            .with_velocity(np.array([0, 0, 10]))\
            .with_engine_config(EngineConfig(burn_time=5.0, ...))\
            .with_wind_model(LogarithmicWind(wind_speed_ref=5.0))\
            .with_parachute_config(ParachuteConfig(diameter=1.0))\
            .build()
    
    Attributes:
        All rocket configuration parameters are stored as attributes
        and can be set via fluent methods.
    """
    
    def __init__(self) -> None:
        """Initialize builder with default values."""
        # State parameters
        self._r_enu_0: Optional[np.ndarray] = None
        self._v_enu_0: Optional[np.ndarray] = None
        self._q_enu2b_0: Optional[np.ndarray] = None
        self._w_enu_0: Optional[np.ndarray] = None
        
        # Mass parameters
        self._initial_mass: float = 10.0
        self._propellant_mass: float = 1.5
        
        # Dependencies
        self._engine: Optional[IEngine] = None
        self._engine_config: Optional[EngineConfig] = None
        self._aerodynamics: Optional[IAerodynamics] = None
        self._aerodynamics_config: Optional[AerodynamicsConfig] = None
        self._atmosphere: Optional[IAtmosphere] = None
        self._mass_properties: Optional[IMassProperties] = None
        self._mass_properties_config: Optional[MassPropertiesConfig] = None
        self._wind_model: Optional[WindModel] = None
        self._wind_vector_enu: Optional[np.ndarray] = None
        self._parachute: Optional[Parachute] = None
        self._parachute_config: Optional[ParachuteConfig] = None
        
        # Other parameters
        self._reference_area: float = 0.01
        self._temperature: float = 15.0
        
        # Gravity turn parameters
        self._enable_gravity_turn: bool = False
        self._gravity_turn_rotation_rate: float = 20.0
        self._gravity_turn_min_velocity: float = 10.0
        self._gravity_turn_use_relative_velocity: bool = False
        
        logger.debug("RocketBuilder initialized with defaults")
    
    # -------------------------------------------------------------------------
    # Fluent Setter Methods
    # -------------------------------------------------------------------------
    
    def with_position(self, r_enu_0: np.ndarray) -> 'RocketBuilder':
        """Set initial position."""
        self._r_enu_0 = np.array(r_enu_0)
        return self
    
    def with_velocity(self, v_enu_0: np.ndarray) -> 'RocketBuilder':
        """Set initial velocity."""
        self._v_enu_0 = np.array(v_enu_0)
        return self
    
    def with_attitude(self, q_enu2b_0: np.ndarray) -> 'RocketBuilder':
        """Set initial attitude quaternion."""
        self._q_enu2b_0 = np.array(q_enu2b_0)
        return self
    
    def with_angular_velocity(self, w_enu_0: np.ndarray) -> 'RocketBuilder':
        """Set initial angular velocity."""
        self._w_enu_0 = np.array(w_enu_0)
        return self
    
    def with_initial_mass(self, initial_mass: float) -> 'RocketBuilder':
        """Set initial total mass."""
        self._initial_mass = float(initial_mass)
        return self
    
    def with_propellant_mass(self, propellant_mass: float) -> 'RocketBuilder':
        """Set initial propellant mass."""
        self._propellant_mass = float(propellant_mass)
        return self
    
    def with_engine(self, engine: IEngine) -> 'RocketBuilder':
        """Set engine instance directly."""
        self._engine = engine
        return self
    
    def with_engine_config(self, config: EngineConfig) -> 'RocketBuilder':
        """Set engine configuration."""
        self._engine_config = config
        return self
    
    def with_aerodynamics(self, aerodynamics: IAerodynamics) -> 'RocketBuilder':
        """Set aerodynamics instance directly."""
        self._aerodynamics = aerodynamics
        return self
    
    def with_aerodynamics_config(self, config: AerodynamicsConfig) -> 'RocketBuilder':
        """Set aerodynamics configuration."""
        self._aerodynamics_config = config
        return self
    
    def with_atmosphere(self, atmosphere: IAtmosphere) -> 'RocketBuilder':
        """Set atmosphere instance directly."""
        self._atmosphere = atmosphere
        return self
    
    def with_temperature(self, temperature: float) -> 'RocketBuilder':
        """Set initial temperature for atmosphere."""
        self._temperature = float(temperature)
        return self
    
    def with_mass_properties(self, mass_properties: IMassProperties) -> 'RocketBuilder':
        """Set mass properties instance directly."""
        self._mass_properties = mass_properties
        return self
    
    def with_mass_properties_config(self, config: MassPropertiesConfig) -> 'RocketBuilder':
        """Set mass properties configuration."""
        self._mass_properties_config = config
        return self
    
    def with_wind_model(self, wind_model: WindModel) -> 'RocketBuilder':
        """Set wind model instance."""
        self._wind_model = wind_model
        return self
    
    def with_wind_vector(self, wind_vector_enu: np.ndarray) -> 'RocketBuilder':
        """Set initial wind vector directly."""
        self._wind_vector_enu = np.array(wind_vector_enu)
        return self
    
    def with_parachute(self, parachute: Parachute) -> 'RocketBuilder':
        """Set parachute instance directly."""
        self._parachute = parachute
        return self
    
    def with_parachute_config(self, config: ParachuteConfig) -> 'RocketBuilder':
        """Set parachute configuration."""
        self._parachute_config = config
        return self
    
    # Gravity turn configuration
    def with_gravity_turn(self, enable: bool = True) -> 'RocketBuilder':
        """Enable or disable gravity turn."""
        self._enable_gravity_turn = enable
        return self
    
    def with_gravity_turn_rate(self, rate: float) -> 'RocketBuilder':
        """Set maximum rotation rate for gravity turn [deg/s]."""
        self._gravity_turn_rotation_rate = float(rate)
        return self
    
    def with_gravity_turn_min_velocity(self, min_vel: float) -> 'RocketBuilder':
        """Set minimum velocity to activate gravity turn [m/s]."""
        self._gravity_turn_min_velocity = float(min_vel)
        return self
    
    def with_gravity_turn_use_relative_velocity(self, use_relative: bool) -> 'RocketBuilder':
        """Set whether to use air-relative velocity for gravity turn alignment."""
        self._gravity_turn_use_relative_velocity = use_relative
        return self
    
    def with_reference_area(self, reference_area: float) -> 'RocketBuilder':
        """Set reference area for aerodynamics."""
        self._reference_area = float(reference_area)
        return self
    
    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    
    def _validate(self) -> None:
        """Validate all required parameters are set."""
        errors = []
        
        # Check state parameters
        if self._r_enu_0 is None:
            errors.append("Initial position (r_enu_0) is required")
        if self._v_enu_0 is None:
            errors.append("Initial velocity (v_enu_0) is required")
        if self._q_enu2b_0 is None:
            errors.append("Initial attitude (q_enu2b_0) is required")
        if self._w_enu_0 is None:
            errors.append("Initial angular velocity (w_enu_0) is required")
        
        # Check that we have either engine or engine_config
        if self._engine is None and self._engine_config is None:
            errors.append("Either engine instance or engine_config is required")
        
        if errors:
            raise RocketConfigurationError(
                "Rocket configuration is incomplete:\n" + "\n".join(f"  - {e}" for e in errors)
            )
        
        # Validate state vectors
        if self._r_enu_0 is not None and len(self._r_enu_0) != 3:
            raise RocketConfigurationError(
                f"r_enu_0 must be a 3-element array, got shape {self._r_enu_0.shape}"
            )
        if self._v_enu_0 is not None and len(self._v_enu_0) != 3:
            raise RocketConfigurationError(
                f"v_enu_0 must be a 3-element array, got shape {self._v_enu_0.shape}"
            )
        if self._q_enu2b_0 is not None and len(self._q_enu2b_0) != 4:
            raise RocketConfigurationError(
                f"q_enu2b_0 must be a 4-element array (quaternion), got shape {self._q_enu2b_0.shape}"
            )
        if self._w_enu_0 is not None and len(self._w_enu_0) != 3:
            raise RocketConfigurationError(
                f"w_enu_0 must be a 3-element array, got shape {self._w_enu_0.shape}"
            )
    
    # -------------------------------------------------------------------------
    # Build Methods
    # -------------------------------------------------------------------------
    
    def build(self) -> NewRocket:
        """
        Build and return a fully configured Rocket instance.
        
        Returns:
            NewRocket: Configured rocket instance
        
        Raises:
            RocketConfigurationError: If configuration is incomplete or invalid
        """
        self._validate()
        
        # After validation, we know these are not None - use assertions to satisfy type checker
        assert self._r_enu_0 is not None
        assert self._v_enu_0 is not None
        assert self._q_enu2b_0 is not None
        assert self._w_enu_0 is not None
        
        # Create atmosphere if not provided
        atmosphere = self._atmosphere
        if atmosphere is None:
            atmosphere = Atmosphere(self._temperature)
        
        # Create engine if config is provided
        engine = self._engine
        if engine is None and self._engine_config is not None:
            engine = self._create_engine_from_config(self._engine_config, atmosphere)
        
        if engine is None:
            raise RocketConfigurationError("No engine provided or created from config")
        
        # Create mass_properties if config is provided
        mass_properties = self._mass_properties
        if mass_properties is None and self._mass_properties_config is not None:
            mass_properties = self._create_mass_properties_from_config(
                self._mass_properties_config
            )
        
        # Create parachute if config is provided
        parachute = self._parachute
        if parachute is None and self._parachute_config is not None:
            parachute = self._create_parachute_from_config(self._parachute_config)
        
        # Create wind_model if not provided but wind_vector is
        wind_model = self._wind_model
        
        # Create rocket
        rocket = NewRocket(
            r_enu_0=self._r_enu_0,
            v_enu_0=self._v_enu_0,
            q_enu2b_0=self._q_enu2b_0,
            w_enu_0=self._w_enu_0,
            initial_mass=self._initial_mass,
            engine=engine,
            atmosphere=atmosphere,
            mass_properties=mass_properties,
            reference_area=self._reference_area,
            propellant_mass=self._propellant_mass,
            wind_vector_enu=self._wind_vector_enu,
            wind_model=wind_model,
            parachute=parachute,
            # Gravity turn parameters
            enable_gravity_turn=self._enable_gravity_turn,
            gravity_turn_rotation_rate=self._gravity_turn_rotation_rate,
            gravity_turn_min_velocity=self._gravity_turn_min_velocity,
            gravity_turn_use_relative_velocity=self._gravity_turn_use_relative_velocity
        )
        
        # Set aerodynamics if provided or create from config
        if self._aerodynamics is not None:
            rocket.set_aerodynamics(self._aerodynamics)
        elif self._aerodynamics_config is not None:
            aero = self._create_aerodynamics_from_config(
                self._aerodynamics_config, atmosphere
            )
            rocket.set_aerodynamics(aero)
        
        return rocket
    
    def _create_engine_from_config(
        self, config: EngineConfig, atmosphere: IAtmosphere
    ) -> IEngine:
        """Create engine from configuration."""
        return EnhancedEngine(
            time=0.0,
            burn_time=config.burn_time,
            ambient_pressure=config.ambient_pressure,
            nozzle_exit_diameter=config.nozzle_exit_diameter,
            propellant_mass=config.propellant_mass,
            specific_impulse=config.specific_impulse,
            mean_thrust=config.mean_thrust,
            max_thrust=config.max_thrust,
            mean_chamber_pressure=config.mean_chamber_pressure,
            max_chamber_pressure=config.max_chamber_pressure,
            thrust_to_weight_ratio=config.thrust_to_weight_ratio,
            thrust_curve_file=config.thrust_curve_file,
            thrust_curve_unit=config.thrust_curve_unit
        )
    
    def _create_mass_properties_from_config(
        self, config: MassPropertiesConfig
    ) -> IMassProperties:
        """Create mass properties from configuration."""
        return MassProperties(
            mass_before=config.mass_before,
            mass_after=config.mass_after,
            cm_before=np.array([
                config.cm_before['x'],
                config.cm_before['y'],
                config.cm_before['z']
            ]),
            cm_after=np.array([
                config.cm_after['x'],
                config.cm_after['y'],
                config.cm_after['z']
            ]),
            inertia_before=np.array([
                config.inertia_before['x'],
                config.inertia_before['y'],
                config.inertia_before['z']
            ]),
            inertia_after=np.array([
                config.inertia_after['x'],
                config.inertia_after['y'],
                config.inertia_after['z']
            ])
        )
    
    def _create_aerodynamics_from_config(
        self, config: AerodynamicsConfig, atmosphere: IAtmosphere
    ) -> IAerodynamics:
        """Create aerodynamics from configuration."""
        return Aerodynamics(
            mach=config.mach,
            angle_attack=config.angle_attack,
            height=config.height,
            atmosphere=atmosphere,
            rocket_data={
                'reference_area': config.reference_area,
                'geometry': config.geometry,
                'fuselage': config.fuselage,
                'nosecone': config.nosecone,
                'rear_section': config.rear_section,
                'fins': config.fins
            },
            mass_props={
                'CoM_before_burn': config.fuselage if config.fuselage else {'x': 0.5, 'y': 0, 'z': 0},
                'CoM_after_burn': config.fuselage if config.fuselage else {'x': 0.6, 'y': 0, 'z': 0},
                'I_before_burn': config.inertia_before if hasattr(config, 'inertia_before') else {'x': 0.1, 'y': 0.1, 'z': 0.05},
                'I_after_burn': config.inertia_after if hasattr(config, 'inertia_after') else {'x': 0.1, 'y': 0.1, 'z': 0.05}
            }
        )
    
    def _create_parachute_from_config(self, config: ParachuteConfig) -> Parachute:
        """Create parachute from configuration."""
        parachute_dict = {
            'name': config.name,
            'diameter': config.diameter,
            'Cd': config.Cd,
            'material': config.material,
            'inflation_time': config.inflation_time,
            'deployment_altitude': config.deployment_altitude,
            'min_velocity': config.min_velocity,
            'max_velocity': config.max_velocity,
            'drogue_enabled': config.drogue_enabled,
        }
        
        if config.drogue_enabled:
            parachute_dict.update({
                'drogue_diameter': config.drogue_diameter,
                'drogue_Cd': config.drogue_Cd,
                'drogue_deployment_altitude': config.drogue_deployment_altitude,
                'drogue_inflation_time': config.drogue_inflation_time
            })
        
        return Parachute(parachute_dict)


# =============================================================================
# Original Factory Functions (Maintained for backward compatibility)
# =============================================================================


def load_rocket_config(rocket_name: str, configs_dir: str = 'data/rockets/configs') -> dict:
    """
    Load rocket configuration from JSON file.
    
    Args:
        rocket_name: Name of the rocket configuration file (without .json extension)
        configs_dir: Directory containing rocket configuration files
    
    Returns:
        dict: Rocket configuration dictionary
    
    Raises:
        RocketFileNotFoundError: If configuration file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    config_path = Path(configs_dir) / f"{rocket_name}.json"
    
    if not config_path.exists():
        raise RocketFileNotFoundError(f"Rocket configuration not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config


def create_engine(
    engine_data: dict,
    time: float = 0.0,
    ambient_pressure: float = RC.DEFAULT_PRESSURE
) -> IEngine:
    """
    Create an engine instance from configuration dictionary.
    
    Args:
        engine_data: Engine configuration dictionary
        time: Initial time [s]
        ambient_pressure: Initial ambient pressure [Pa]
    
    Returns:
        IEngine: Configured engine instance
    
    Raises:
        RocketConfigurationError: If engine_data is missing required fields
    """
    # Validate required fields
    required_fields = [
        'burn_time',
        'nozzle_exit_diameter',
        'propellant_mass',
        'specific_impulse',
        'mean_thrust',
        'max_thrust',
        'mean_chamber_pressure',
        'max_chamber_pressure',
        'thrust_to_weight_ratio'
    ]
    
    for field in required_fields:
        if field not in engine_data:
            raise RocketConfigurationError(
                f"Engine configuration is missing required field: '{field}'"
            )
    
    thrust_curve_file = engine_data.get('thrust_curve_file')
    thrust_curve_unit = engine_data.get('thrust_curve_unit', 'N')
    
    # Handle experimental thrust curve mode
    if engine_data.get('thrust_curve_mode') == 'experimental':
        if not thrust_curve_file:
            raise RocketConfigurationError(
                "'thrust_curve_file' is required for experimental thrust curve mode"
            )
        if not thrust_curve_unit:
            raise RocketConfigurationError(
                "'thrust_curve_unit' is required for experimental thrust curve mode"
            )
    else:
        thrust_curve_file = None
    
    engine = EnhancedEngine(
        time=time,
        burn_time=engine_data["burn_time"],
        ambient_pressure=ambient_pressure,
        nozzle_exit_diameter=engine_data["nozzle_exit_diameter"],
        propellant_mass=engine_data["propellant_mass"],
        specific_impulse=engine_data["specific_impulse"],
        mean_thrust=engine_data["mean_thrust"],
        max_thrust=engine_data["max_thrust"],
        mean_chamber_pressure=engine_data["mean_chamber_pressure"],
        max_chamber_pressure=engine_data["max_chamber_pressure"],
        thrust_to_weight_ratio=engine_data["thrust_to_weight_ratio"],
        thrust_curve_file=thrust_curve_file,
        thrust_curve_unit=thrust_curve_unit,
    )
    
    return engine


def create_aerodynamics(
    mach: float,
    angle_attack: float,
    height: float,
    atmosphere: IAtmosphere,
    rocket_config: dict,
    mass_props_before: Dict[str, float],
    mass_props_after: Dict[str, float]
) -> IAerodynamics:
    """
    Create an aerodynamics instance from configuration.
    
    Args:
        mach: Initial Mach number
        angle_attack: Initial angle of attack [deg]
        height: Initial altitude [m]
        atmosphere: Atmosphere instance
        rocket_config: Full rocket configuration dictionary
        mass_props_before: Center of mass and inertia before burn
        mass_props_after: Center of mass and inertia after burn
    
    Returns:
        IAerodynamics: Configured aerodynamics instance
    """
    # Extract geometry from config
    geometry = rocket_config.get('geometry', {})
    fuselage = rocket_config.get('fuselage', {})
    nosecone = rocket_config.get('nosecone', {})
    rear_section = rocket_config.get('rear_section', {})
    fins = rocket_config.get('fins', {})
    
    # Build mass properties dict (for aerodynamics calculations)
    mass_props = {
        'CoM_before_burn': mass_props_before,
        'CoM_after_burn': mass_props_after,
        'I_before_burn': mass_props_before,  # Simplified - in reality these might differ
        'I_after_burn': mass_props_after,
    }
    
    # Build rocket data dict (for aerodynamics calculations)
    rocket_data = {
        'reference_area': rocket_config.get('reference_area', 0.01),
        'geometry': geometry,
        'fuselage': fuselage,
        'nosecone': nosecone,
        'rear_section': rear_section,
        'fins': fins,
    }
    
    # Create aerodynamics with geometry-based calculations (Barrowman method)
    aero = Aerodynamics(
        mach=mach,
        angle_attack=angle_attack,
        height=height,
        atmosphere=atmosphere,
        rocket_data=rocket_data,
        mass_props=mass_props
    )
    
    return aero


def create_mass_properties(
    initial_mass: float,
    propellant_mass: float,
    com_before: Dict[str, float],
    inertia_before: Dict[str, float],
    com_after: Dict[str, float],
    inertia_after: Dict[str, float]
) -> IMassProperties:
    """
    Create mass properties instance.
    
    Args:
        initial_mass: Initial total mass [kg]
        propellant_mass: Total propellant mass [kg]
        com_before: Center of mass before burn [x, y, z] in body frame [m]
        inertia_before: Moments of inertia before burn [Ixx, Iyy, Izz] [kg·m²]
        com_after: Center of mass after burn [x, y, z] in body frame [m]
        inertia_after: Moments of inertia after burn [Ixx, Iyy, Izz] [kg·m²]
    
    Returns:
        IMassProperties: Mass properties instance
    """
    mass_props = MassProperties(
        mass_before=initial_mass,
        mass_after=initial_mass - propellant_mass,
        cm_before=np.array([com_before['x'], com_before['y'], com_before['z']]),
        cm_after=np.array([com_after['x'], com_after['y'], com_after['z']]),
        inertia_before=np.array([inertia_before['x'], inertia_before['y'], inertia_before['z']]),
        inertia_after=np.array([inertia_after['x'], inertia_after['y'], inertia_after['z']])
    )
    
    return mass_props


def create_wind_model(
    wind_config: Optional[Dict[str, Any]] = None
) -> Optional[WindModel]:
    """
    Create a wind model from configuration.
    
    Args:
        wind_config: Wind configuration dictionary with keys:
            - model_type: 'constant', 'logarithmic', 'power_law', 'gust', 'shear'
            - wind_speed or wind_speed_ref: Reference wind speed [m/s]
            - wind_direction: Wind direction FROM [degrees]
            - Other model-specific parameters
    
    Returns:
        Optional[WindModel]: Configured wind model, or None if config is None
    """
    if wind_config is None:
        return None
    
    from src.models.wind import create_wind_model as wind_create_wind_model
    return wind_create_wind_model(**wind_config)


def create_parachute(
    parachute_config: Optional[Dict[str, Any]] = None
) -> Optional[Parachute]:
    """
    Create a parachute from configuration.
    
    Args:
        parachute_config: Parachute configuration dictionary with keys:
            - name: Parachute name
            - diameter: Canopy diameter [m]
            - Cd: Drag coefficient
            - deployment_altitude: Altitude trigger [m]
            - min_velocity: Minimum safe deployment velocity [m/s]
            - max_velocity: Maximum safe deployment velocity [m/s]
            - material: Material type
            - inflation_time: Time to full inflation [s]
            - drogue_enabled: Whether to use drogue chute
            - Other drogue-specific parameters
    
    Returns:
        Optional[Parachute]: Configured parachute, or None if config is None
    """
    if parachute_config is None:
        return None
    
    return Parachute(parachute_config)


def create_rocket_from_config(
    r_enu_0: np.ndarray,
    v_enu_0: np.ndarray,
    q_enu2b_0: np.ndarray,
    w_enu_0: np.ndarray,
    initial_mass: float,
    rocket_name: str,
    temperature: float = 15.0,
    configs_dir: str = 'data/rockets/configs',
    wind_vector_enu: Optional[np.ndarray] = None,
    reference_area: Optional[float] = None,
    wind_model_config: Optional[Dict[str, Any]] = None,
    parachute_config: Optional[Dict[str, Any]] = None,
    # Gravity turn parameters
    enable_gravity_turn: bool = False,
    gravity_turn_rotation_rate: float = 20.0,
    gravity_turn_min_velocity: float = 10.0,
    gravity_turn_use_relative_velocity: bool = False
) -> Tuple[NewRocket, dict, IEngine, IAerodynamics, IAtmosphere]:
    """
    Create a fully configured Rocket from a rocket configuration file.
    
    This is the main factory function for creating rockets with the new architecture.
    It loads the configuration, creates all dependencies, and returns a ready-to-use Rocket.
    
    Args:
        r_enu_0: Initial position in ENU frame [m]
        v_enu_0: Initial velocity in ENU frame [m/s]
        q_enu2b_0: Initial quaternion from ENU to body frame
        w_enu_0: Initial angular velocity in ENU frame [rad/s]
        initial_mass: Initial total mass [kg]
        rocket_name: Name of rocket configuration file (without .json)
        temperature: Initial temperature for atmosphere [°C]
        configs_dir: Directory containing rocket configurations
        wind_vector_enu: Initial wind vector in ENU frame [m/s]
        reference_area: Reference area for aerodynamics [m²]
        wind_model_config: Configuration for wind model (optional)
        parachute_config: Configuration for parachute (optional)
        enable_gravity_turn: Enable passive gravity turn (default: False)
        gravity_turn_rotation_rate: Max rotation rate [deg/s] (default: 20.0)
        gravity_turn_min_velocity: Minimum velocity to activate [m/s] (default: 10.0)
        gravity_turn_use_relative_velocity: Use air-relative velocity (default: False)
    
    Returns:
        Tuple containing:
        - NewRocket: Configured rocket instance
        - rocket_config: Loaded rocket configuration dictionary
        - engine: Configured engine instance
        - aerodynamics: Configured aerodynamics instance
        - atmosphere: Configured atmosphere instance
    
    Raises:
        RocketFileNotFoundError: If rocket configuration doesn't exist
        RocketConfigurationError: If configuration is invalid
    """
    # Load rocket configuration
    rocket_config = load_rocket_config(rocket_name, configs_dir)
    
    # Create atmosphere
    atmosphere = Atmosphere(temperature)
    
    # Create engine
    engine_data = rocket_config.get('engine', {})
    propellant_mass = engine_data.get('propellant_mass', 0.0)
    engine = create_engine(engine_data, time=0.0, ambient_pressure=atmosphere.give_pressure(0.0))
    
    # Create mass properties
    mass_props_before = rocket_config.get('CoM_before_burn', {'x': 0, 'y': 0, 'z': 0})
    mass_props_after = rocket_config.get('CoM_after_burn', {'x': 0, 'y': 0, 'z': 0})
    inertia_before = rocket_config.get('I_before_burn', {'x': 0.1, 'y': 0.1, 'z': 0.05})
    inertia_after = rocket_config.get('I_after_burn', {'x': 0.1, 'y': 0.1, 'z': 0.05})
    
    mass_properties = create_mass_properties(
        initial_mass=initial_mass,
        propellant_mass=propellant_mass,
        com_before=mass_props_before,
        inertia_before=inertia_before,
        com_after=mass_props_after,
        inertia_after=inertia_after
    )
    
    # Create wind model if config provided
    wind_model = create_wind_model(wind_model_config)
    
    # Create parachute if config provided
    parachute = create_parachute(parachute_config)
    
    # Get reference area from config or use provided
    ref_area = reference_area if reference_area is not None else rocket_config.get('reference_area', 0.01)
    
    # Get gravity turn parameters from config if not provided
    gravity_turn_config = rocket_config.get('gravity_turn', {})
    if 'enable_gravity_turn' in locals():
        # Use provided parameters
        gt_enabled = enable_gravity_turn
        gt_rotation_rate = gravity_turn_rotation_rate
        gt_min_velocity = gravity_turn_min_velocity
        gt_use_relative = gravity_turn_use_relative_velocity
    else:
        # Use config file parameters
        gt_enabled = gravity_turn_config.get('enabled', False)
        gt_rotation_rate = gravity_turn_config.get('rotation_rate', 20.0)
        gt_min_velocity = gravity_turn_config.get('min_velocity', 10.0)
        gt_use_relative = gravity_turn_config.get('use_relative_velocity', False)
    
    # Create rocket with dependency injection
    rocket = NewRocket(
        r_enu_0=r_enu_0,
        v_enu_0=v_enu_0,
        q_enu2b_0=q_enu2b_0,
        w_enu_0=w_enu_0,
        initial_mass=initial_mass,
        engine=engine,
        atmosphere=atmosphere,
        mass_properties=mass_properties,
        reference_area=ref_area,
        wind_vector_enu=wind_vector_enu,
        wind_model=wind_model,
        parachute=parachute,
        propellant_mass=propellant_mass,
        # Gravity turn parameters
        enable_gravity_turn=gt_enabled,
        gravity_turn_rotation_rate=gt_rotation_rate,
        gravity_turn_min_velocity=gt_min_velocity,
        gravity_turn_use_relative_velocity=gt_use_relative
    )
    
    # Create aerodynamics (requires rocket data and mass props)
    # We'll use initial values for now
    mach = 0.0
    angle_attack = 0.0
    height = r_enu_0[2]
    
    aerodynamics = create_aerodynamics(
        mach=mach,
        angle_attack=angle_attack,
        height=height,
        atmosphere=atmosphere,
        rocket_config=rocket_config,
        mass_props_before=mass_props_before,
        mass_props_after=mass_props_after
    )
    
    # Set aerodynamics on the rocket
    rocket.set_aerodynamics(aerodynamics)
    
    return rocket, rocket_config, engine, aerodynamics, atmosphere


# =============================================================================
# Utility Functions
# =============================================================================


def update_rocket_for_step(
    rocket: NewRocket,
    atmosphere: IAtmosphere,
    coordinates: np.ndarray,
    timestep: float,
    wind_vector_enu: Optional[np.ndarray] = None
) -> None:
    """
    Update rocket state for a simulation step.
    
    This function handles all the updates that were previously done by
    individual method calls in the legacy Rocket class.
    
    Args:
        rocket: Rocket instance to update
        atmosphere: Atmosphere instance
        coordinates: Launch coordinates [lat, lon, alt]
        timestep: Simulation timestep [s]
        wind_vector_enu: Wind vector in ENU frame [m/s]
    """
    # Update wind
    if wind_vector_enu is not None:
        rocket.set_wind(wind_vector_enu)
    
    # Update atmosphere based on current altitude
    altitude = rocket.state.r_enu[2]
    rocket.dynamics.update_atmosphere(altitude)
    
    # Update aerodynamics
    # Note: This would require updating the aerodynamics with current flight conditions
    # For now, we'll defer this to a future enhancement
    
    # Perform simulation step
    rocket.step(timestep)


def run_simulation(
    rocket: NewRocket,
    runtime: float,
    timestep: float,
    atmosphere: IAtmosphere,
    coordinates: np.ndarray,
    wind_vector_enu: Optional[np.ndarray] = None
) -> dict:
    """
    Run a complete simulation with the new Rocket architecture.
    
    This is a simplified simulation loop that demonstrates how to use
    the new architecture. For full functionality, see simulation_worker.py.
    
    Args:
        rocket: Configured Rocket instance
        runtime: Total simulation runtime [s]
        timestep: Simulation timestep [s]
        atmosphere: Atmosphere instance
        coordinates: Launch coordinates [lat, lon, alt]
        wind_vector_enu: Wind vector in ENU frame [m/s]
    
    Returns:
        dict: Simulation results with trajectory and metrics
    """
    num_steps = int(runtime / timestep)
    trajectory = []
    
    metrics = {
        'max_altitude': 0.0,
        'max_velocity': 0.0,
        'flight_duration': 0.0,
    }
    
    for i in range(num_steps):
        # Update rocket for this step
        update_rocket_for_step(rocket, atmosphere, coordinates, timestep, wind_vector_enu)
        
        # Record trajectory
        current_altitude = rocket.state.r_enu[2]
        current_velocity = float(np.linalg.norm(rocket.state.v_enu))
        
        metrics['max_altitude'] = max(metrics['max_altitude'], current_altitude)
        metrics['max_velocity'] = max(metrics['max_velocity'], current_velocity)
        
        if i % 10 == 0:  # Store every 10 steps
            trajectory.append({
                'time': rocket.state.time,
                'altitude': current_altitude,
                'velocity': current_velocity,
            })
        
        # Check termination (simplified)
        if current_altitude <= 0 and rocket.state.time > 1.0:
            metrics['flight_duration'] = rocket.state.time
            break
    
    return {
        'trajectory': trajectory,
        'metrics': metrics,
        'status': 'success'
    }


__all__ = [
    # Data classes
    'EngineConfig',
    'ParachuteConfig',
    'MassPropertiesConfig',
    'AerodynamicsConfig',
    # Builder
    'RocketBuilder',
    # Exceptions
    'RocketConfigurationError',
    'RocketFileNotFoundError',
    # Original functions (backward compatible)
    'load_rocket_config',
    'create_engine',
    'create_aerodynamics',
    'create_mass_properties',
    'create_wind_model',
    'create_parachute',
    'create_rocket_from_config',
    # Utility functions
    'update_rocket_for_step',
    'run_simulation',
]
