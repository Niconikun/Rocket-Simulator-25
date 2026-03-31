"""
Wind Utilities Module

Helper functions for wind model operations:
- Coordinate transformations
- Wind vector processing
- Relative velocity calculations
- Debug and visualization utilities

Author: Wind Model Integration
Date: 2026
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)


def calculate_relative_velocity(rocket_velocity_enu: np.ndarray, 
                               wind_vector_enu: np.ndarray) -> np.ndarray:
    """
    Calculate relative velocity between rocket and air (wind).
    
    The relative velocity is what the rocket "feels" aerodynamically.
    This is the velocity that affects drag, lift, and angle of attack.
    
    Formula:
        v_rel = v_rocket - v_wind
    
    Args:
        rocket_velocity_enu (np.ndarray): Rocket velocity in ENU frame [East, North, Up] [m/s]
        wind_vector_enu (np.ndarray): Wind velocity in ENU frame [East, North, Up] [m/s]
    
    Returns:
        np.ndarray: Relative velocity vector [East, North, Up] [m/s]
    
    Example:
        >>> rocket_vel = np.array([10, 0, 100])  # Moving East and Up
        >>> wind_vel = np.array([5, 0, 0])      # Wind from the West (moving East)
        >>> v_rel = calculate_relative_velocity(rocket_vel, wind_vel)
        >>> print(v_rel)  # [5, 0, 100] - rocket moves slower relative to air
    """
    if not isinstance(rocket_velocity_enu, np.ndarray):
        rocket_velocity_enu = np.array(rocket_velocity_enu)
    if not isinstance(wind_vector_enu, np.ndarray):
        wind_vector_enu = np.array(wind_vector_enu)
    
    relative_velocity = rocket_velocity_enu - wind_vector_enu
    return relative_velocity


def calculate_wind_corrected_angle_of_attack(rocket_velocity_enu: np.ndarray,
                                            wind_vector_enu: np.ndarray) -> float:
    """
    Calculate angle of attack accounting for wind effects.
    
    Without wind, angle of attack is based on rocket velocity.
    With wind, it's based on relative velocity between rocket and air.
    
    Formula:
        v_rel = v_rocket - v_wind
        α = arctan(v_rel_vertical / v_rel_horizontal)
    
    Args:
        rocket_velocity_enu (np.ndarray): Rocket velocity [m/s]
        wind_vector_enu (np.ndarray): Wind vector [m/s]
    
    Returns:
        float: Angle of attack [degrees]
    """
    v_rel = calculate_relative_velocity(rocket_velocity_enu, wind_vector_enu)
    
    # Horizontal component (along body axis, typically East)
    v_horizontal = np.sqrt(v_rel[0]**2 + v_rel[1]**2)
    
    # Vertical component (Up)
    v_vertical = v_rel[2]
    
    # Avoid division by zero
    if v_horizontal < 1e-6:
        return 90.0 if v_vertical > 0 else -90.0
    
    angle_rad = np.arctan2(v_vertical, v_horizontal)
    angle_deg = np.degrees(angle_rad)
    
    return angle_deg


def calculate_dynamic_pressure(relative_velocity_magnitude: float,
                              air_density: float) -> float:
    """
    Calculate dynamic pressure from relative velocity.
    
    Formula:
        q = 0.5 * ρ * v²
    
    Dynamic pressure is the kinetic energy per unit area.
    It drives all aerodynamic forces (drag, lift, etc.).
    
    Args:
        relative_velocity_magnitude (float): Magnitude of relative velocity [m/s]
        air_density (float): Air density [kg/m³]
    
    Returns:
        float: Dynamic pressure [Pa]
    
    Raises:
        ValueError: If inputs are negative
    """
    if relative_velocity_magnitude < 0 or air_density < 0:
        raise ValueError("Velocity and density must be non-negative")
    
    q = 0.5 * air_density * (relative_velocity_magnitude ** 2)
    return q


def get_wind_effect_metrics(rocket_velocity_enu: np.ndarray,
                           wind_vector_enu: np.ndarray,
                           air_density: float) -> dict:
    """
    Calculate comprehensive wind effect metrics for diagnostics/logging.
    
    Args:
        rocket_velocity_enu (np.ndarray): Rocket velocity [m/s]
        wind_vector_enu (np.ndarray): Wind vector [m/s]
        air_density (float): Air density [kg/m³]
    
    Returns:
        dict: Wind metrics including:
            - rocket_speed: Rocket ground speed [m/s]
            - wind_speed: Wind speed magnitude [m/s]
            - relative_velocity: Relative wind magnitude [m/s]
            - angle_of_attack: AOA with wind correction [degrees]
            - dynamic_pressure: Based on relative velocity [Pa]
            - wind_impact_percent: (1 - v_rel/v_rocket) * 100 [%]
    """
    v_rel = calculate_relative_velocity(rocket_velocity_enu, wind_vector_enu)
    
    rocket_speed = np.linalg.norm(rocket_velocity_enu[:2])  # Horizontal only
    wind_speed = np.linalg.norm(wind_vector_enu[:2])        # Horizontal only
    relative_speed = np.linalg.norm(v_rel[:2])              # Horizontal only
    
    aoa = calculate_wind_corrected_angle_of_attack(rocket_velocity_enu, wind_vector_enu)
    q_dyn = calculate_dynamic_pressure(np.linalg.norm(v_rel), air_density)
    
    # Calculate wind impact percentage
    if rocket_speed > 1e-6:
        wind_impact = (1.0 - relative_speed / rocket_speed) * 100.0
    else:
        wind_impact = 0.0
    
    return {
        'rocket_speed': rocket_speed,
        'wind_speed': wind_speed,
        'relative_velocity_magnitude': relative_speed,
        'angle_of_attack_degrees': aoa,
        'dynamic_pressure_pa': q_dyn,
        'wind_impact_percent': wind_impact,
        'rocket_velocity_enu': rocket_velocity_enu.copy(),
        'wind_vector_enu': wind_vector_enu.copy(),
        'relative_velocity_enu': v_rel.copy(),
    }


def validate_wind_state(wind_model) -> bool:
    """
    Validate that a wind model is properly initialized.
    
    Args:
        wind_model: WindModel instance to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if wind_model is None:
        return False
    
    try:
        # Test getting wind vector at surface
        vec = wind_model.get_wind_vector(0.0)
        
        # Check it's a valid numpy array
        if not isinstance(vec, np.ndarray):
            return False
        
        # Check shape and values
        if vec.shape != (3,):
            return False
        
        if not np.all(np.isfinite(vec)):
            return False
        
        return True
    except Exception as e:
        logger.warning(f"Wind model validation failed: {e}")
        return False


def log_wind_config(state: dict, wind_model) -> None:
    """
    Log wind configuration for debugging.
    
    Args:
        state (dict): ApplicationState containing wind parameters
        wind_model: Initialized WindModel instance
    """
    if not state.get('wind_enabled', False):
        logger.info("Wind simulation disabled")
        return
    
    info = wind_model.get_info()
    logger.info(f"Wind Configuration:")
    logger.info(f"  Model Type: {info.get('model_type', 'Unknown')}")
    logger.info(f"  Enabled: {info.get('enabled', False)}")
    logger.info(f"  Direction (FROM): {info.get('wind_direction', 0.0)}°")
    
    # Log model-specific parameters
    if 'wind_speed_ref' in info:
        logger.info(f"  Speed (ref): {info.get('wind_speed_ref')} m/s")
    if 'reference_height' in info:
        logger.info(f"  Reference Height: {info.get('reference_height')} m")
    if 'roughness_length' in info:
        logger.info(f"  Roughness Length: {info.get('roughness_length')} m")
    if 'exponent' in info:
        logger.info(f"  Exponent (α): {info.get('exponent')}")


def create_wind_model_from_state(state: dict):
    """
    Factory function to create wind model from ApplicationState.
    
    Reads wind configuration from state dictionary and creates
    appropriate wind model instance.
    
    Args:
        state (dict): ApplicationState._state dictionary or scenario dict
    
    Returns:
        WindModel: Initialized wind model, or None if wind disabled
    
    Raises:
        ValueError: If wind_model_type is invalid
    """
    from src.models.wind import create_wind_model
    
    # Allow scenarios without wind_enabled flag (for scenario editor)
    if 'wind_enabled' in state and not state.get('wind_enabled', False):
        return None
    
    # Support both wind_speed and wind_speed_ref keys
    wind_speed = state.get('wind_speed', state.get('wind_speed_ref', 5.0))
    
    model_type = state.get('model_type', state.get('wind_model_type', 'logarithmic')).lower()
    
    # Model-specific parameter handling
    if model_type == 'constant':
        wind = create_wind_model(
            'constant',
            wind_speed=wind_speed,
            wind_direction=state.get('wind_direction', 0.0),
            launch_altitude=state.get('launch_elevation', state.get('launch_altitude', 0.0))
        )
    elif model_type == 'logarithmic':
        wind = create_wind_model(
            'logarithmic',
            wind_speed_ref=wind_speed,
            reference_height=state.get('wind_reference_height', 10.0),
            roughness_length=state.get('wind_roughness_length', 0.1),
            wind_direction=state.get('wind_direction', 0.0),
            launch_altitude=state.get('launch_elevation', state.get('launch_altitude', 0.0))
        )
    elif model_type == 'power_law':
        wind = create_wind_model(
            'power_law',
            wind_speed_ref=wind_speed,
            reference_height=state.get('wind_reference_height', 10.0),
            exponent=state.get('wind_exponent', 0.2),
            wind_direction=state.get('wind_direction', 0.0),
            launch_altitude=state.get('launch_elevation', state.get('launch_altitude', 0.0))
        )
    elif model_type == 'gust':
        # Phase 4: Full Dryden spectrum implementation
        # First create base wind model (defaults to logarithmic)
        base_model_type = state.get('base_wind_model', 'logarithmic')
        
        if base_model_type == 'logarithmic':
            base_wind = create_wind_model(
                'logarithmic',
                wind_speed_ref=wind_speed,
                reference_height=state.get('wind_reference_height', 10.0),
                roughness_length=state.get('wind_roughness_length', 0.1),
                wind_direction=state.get('wind_direction', 0.0),
                launch_altitude=state.get('launch_elevation', state.get('launch_altitude', 0.0))
            )
        elif base_model_type == 'power_law':
            base_wind = create_wind_model(
                'power_law',
                wind_speed_ref=wind_speed,
                reference_height=state.get('wind_reference_height', 10.0),
                exponent=state.get('wind_exponent', 0.2),
                wind_direction=state.get('wind_direction', 0.0),
                launch_altitude=state.get('launch_elevation', state.get('launch_altitude', 0.0))
            )
        else:
            base_wind = create_wind_model(
                'constant',
                wind_speed=wind_speed,
                wind_direction=state.get('wind_direction', 0.0),
                launch_altitude=state.get('launch_elevation', state.get('launch_altitude', 0.0))
            )
        
        # Then create gust model with Dryden filtering
        wind = create_wind_model(
            'gust',
            base_wind_model=base_wind,
            gust_intensity=state.get('wind_gust_intensity', 0.1),
            gust_length_scale=state.get('wind_gust_length_scale', 300.0),
            random_seed=state.get('random_seed', None)
        )
    elif model_type == 'shear':
        # Phase 4: Full 3D wind shear implementation
        wind = create_wind_model(
            'shear',
            base_wind_speed=wind_speed,
            base_wind_direction=state.get('wind_direction', 0.0),
            shear_direction_change=state.get('shear_direction_change', 0.0),
            shear_altitude_range=state.get('shear_altitude_range', 1000.0),
            vertical_wind_speed=state.get('vertical_wind', state.get('vertical_wind_speed', 0.0)),
            launch_altitude=state.get('launch_elevation', state.get('launch_altitude', 0.0))
        )
    else:
        raise ValueError(f"Unknown wind model type: {model_type}")
    
    return wind
