"""
Application Constants

Centralized constants for the Rocket Simulator application.
Use these instead of magic numbers in your code.

Usage:
    from src.config import Constants
    
    max_runtime = Constants.SIMULATION_MAX_RUNTIME
    max_wind_speed = Constants.WIND_MAX_SPEED
"""


class SimulationConstants:
    """Constants related to simulation configuration."""
    
    # Runtime limits (seconds)
    MIN_RUNTIME = 1
    MAX_RUNTIME = 10000  # ~2.7 hours
    DEFAULT_RUNTIME = 600  # 10 minutes
    
    # Time step limits (seconds)
    MIN_TIMESTEP = 0.0001
    MAX_TIMESTEP = 1.0
    DEFAULT_TIMESTEP = 0.001
    
    # Launch parameters
    DEFAULT_LAUNCH_ANGLE = 85.0  # degrees from vertical
    MIN_LAUNCH_ANGLE = 5.0
    MAX_LAUNCH_ANGLE = 90.0
    
    DEFAULT_LAUNCH_AZIMUTH = 0.0  # degrees (0 = North)
    MIN_LAUNCH_AZIMUTH = 0.0
    MAX_LAUNCH_AZIMUTH = 360.0
    
    DEFAULT_LAUNCH_ROLL = 0.0  # degrees
    MIN_LAUNCH_ROLL = -180.0
    MAX_LAUNCH_ROLL = 180.0


class EnvironmentalConstants:
    """Constants related to environmental conditions."""
    
    # Temperature (Celsius)
    MIN_TEMPERATURE = -50.0
    MAX_TEMPERATURE = 60.0
    DEFAULT_TEMPERATURE = 20.0
    
    # Pressure (Pascals)
    MIN_PRESSURE = 50000.0
    MAX_PRESSURE = 110000.0
    DEFAULT_PRESSURE = 101325.0  # Sea level
    SEAA_LEVEL_PRESSURE = 101325.0
    
    # Elevation (meters)
    MIN_ELEVATION = -500.0
    MAX_ELEVATION = 10000.0
    DEFAULT_ELEVATION = 60.0


class RocketConstants:
    """Constants related to rocket configuration."""
    
    # Mass (kg)
    MIN_MASS = 0.1
    MAX_MASS = 100000.0  # 100 tonnes
    DEFAULT_MASS = 1.5
    
    # Dimensions (meters)
    MIN_DIAMETER = 0.001
    MAX_DIAMETER = 100.0
    DEFAULT_DIAMETER = 0.1
    
    MIN_LENGTH = 0.01
    MAX_LENGTH = 100.0
    
    # Reference area (m²)
    MIN_REFERENCE_AREA = 0.000001
    MAX_REFERENCE_AREA = 1000.0
    DEFAULT_REFERENCE_AREA = 0.01
    
    # Material properties
    DEFAULT_MATERIAL = "ripstop_nylon"


class WindConstants:
    """Constants related to wind configuration."""
    
    # Wind speed (m/s)
    MIN_WIND_SPEED = 0.0
    MAX_WIND_SPEED = 50.0  # ~180 km/h
    DEFAULT_WIND_SPEED = 5.0
    
    # Wind direction (degrees FROM, meteorological convention)
    MIN_WIND_DIRECTION = 0.0
    MAX_WIND_DIRECTION = 360.0
    DEFAULT_WIND_DIRECTION = 0.0  # From North
    
    # Reference height (meters)
    MIN_REFERENCE_HEIGHT = 0.1
    MAX_REFERENCE_HEIGHT = 1000.0
    DEFAULT_REFERENCE_HEIGHT = 10.0
    
    # Roughness length (meters)
    MIN_ROUGHNESS = 0.001
    MAX_ROUGHNESS = 2.0
    DEFAULT_ROUGHNESS = 0.1
    
    # Power law exponent
    MIN_POWER_LAW_EXPONENT = 0.05
    MAX_POWER_LAW_EXPONENT = 0.5
    DEFAULT_POWER_LAW_EXPONENT = 0.2
    
    # Gust parameters
    MIN_GUST_INTENSITY = 0.0
    MAX_GUST_INTENSITY = 1.0
    DEFAULT_GUST_INTENSITY = 0.1
    
    MIN_GUST_LENGTH = 10.0
    MAX_GUST_LENGTH = 5000.0
    DEFAULT_GUST_LENGTH = 300.0


class ParachuteConstants:
    """Constants related to parachute configuration."""
    
    # Deployment altitude (meters)
    MIN_DEPLOYMENT_ALTITUDE = 100.0
    MAX_DEPLOYMENT_ALTITUDE = 10000.0
    DEFAULT_DEPLOYMENT_ALTITUDE = 300.0
    
    # Diameter (meters)
    MIN_PARACHUTE_DIAMETER = 0.1
    MAX_PARACHUTE_DIAMETER = 5.0
    DEFAULT_PARACHUTE_DIAMETER = 0.6
    
    # Drag coefficient
    MIN_PARACHUTE_CD = 0.5
    MAX_PARACHUTE_CD = 2.5
    DEFAULT_PARACHUTE_CD = 1.5
    
    # Mass (kg)
    MIN_PARACHUTE_MASS = 0.0
    MAX_PARACHUTE_MASS = 50.0
    DEFAULT_PARACHUTE_MASS = 0.05
    
    # Inflation time (seconds)
    MIN_INFLATION_TIME = 0.1
    MAX_INFLATION_TIME = 5.0
    DEFAULT_INFLATION_TIME = 0.5
    
    # Velocity limits (m/s)
    MIN_SAFE_VELOCITY = 0.0
    MAX_SAFE_VELOCITY = 300.0
    DEFAULT_MIN_SAFE_VELOCITY = 5.0
    DEFAULT_MAX_SAFE_VELOCITY = 80.0


class LocationConstants:
    """Constants related to location configuration."""
    
    # Latitude (degrees)
    MIN_LATITUDE = -90.0
    MAX_LATITUDE = 90.0
    DEFAULT_LATITUDE = 0.0
    
    # Longitude (degrees)
    MIN_LONGITUDE = -180.0
    MAX_LONGITUDE = 180.0
    DEFAULT_LONGITUDE = 0.0


class MonteCarloConstants:
    """Constants related to Monte Carlo simulations."""
    
    # Number of runs
    MIN_MONTE_CARLO_RUNS = 2
    MAX_MONTE_CARLO_RUNS = 10000
    DEFAULT_MONTE_CARLO_RUNS = 100
    
    # Number of workers
    MIN_WORKERS = 1
    MAX_WORKERS = 32
    DEFAULT_WORKERS = 4
    
    # Uncertainty ranges (1 sigma)
    DEFAULT_SIGMA_ELEVATION = 1.0  # degrees
    DEFAULT_SIGMA_AZIMUTH = 2.0  # degrees
    DEFAULT_SIGMA_TEMPERATURE = 2.0  # Celsius
    DEFAULT_SIGMA_WIND_SPEED = 1.0  # m/s
    DEFAULT_SIGMA_WIND_DIRECTION = 10.0  # degrees
    DEFAULT_SIGMA_PARACHUTE_ALTITUDE = 10.0  # meters
    DEFAULT_SIGMA_PARACHUTE_CD = 0.075


class StateKeyConstants:
    """
    Standardized state key names.
    
    Use these constants instead of hardcoding state keys to ensure consistency
    across the application and make refactoring easier.
    
    Usage:
        from src.config import Constants
        
        # Instead of:
        self.state.set('sim_runtime', 600)
        
        # Use:
        self.state.set(Constants.StateKeys.SIM_RUNTIME, 600)
    """
    
    # Simulation keys
    SIM_RUNTIME = 'sim_runtime'
    SIM_TIME_STEP = 'sim_time_step'
    SIM_DATE = 'sim_date'
    SIM_TIME = 'sim_time'
    SIM_TIMEZONE = 'sim_timezone'
    SIMULATION_RUNNING = 'simulation_running'
    SIMULATION_RESULTS = 'simulation_results'
    SIMULATION_ERROR = 'simulation_error'
    
    # Environmental keys
    AVERAGE_TEMPERATURE = 'average_temperature'
    AVERAGE_PRESSURE = 'average_pressure'
    LAUNCH_ELEVATION = 'launch_elevation'
    
    # Launch parameters
    LAUNCH_ELEVATION_ANGLE = 'launch_elevation_angle'
    LAUNCH_AZIMUTH = 'launch_azimuth'
    LAUNCH_ROLL = 'launch_roll'
    
    # Location keys
    LAUNCH_LATITUDE = 'launch_latitude'
    LAUNCH_LONGITUDE = 'launch_longitude'
    SIM_LOCATION = 'sim_location'
    
    # Wind keys
    WIND_ENABLED = 'wind_enabled'
    WIND_MODEL_TYPE = 'wind_model_type'
    WIND_SPEED = 'wind_speed'
    WIND_SPEED_REF = 'wind_speed_ref'  # Reference wind speed
    WIND_DIRECTION = 'wind_direction'
    WIND_REFERENCE_HEIGHT = 'wind_reference_height'
    WIND_ROUGHNESS_LENGTH = 'wind_roughness_length'
    WIND_EXPONENT = 'wind_exponent'
    WIND_GUST_INTENSITY = 'wind_gust_intensity'
    WIND_GUST_LENGTH_SCALE = 'wind_gust_length_scale'
    
    # Wind scenario keys (advanced wind modeling)
    SHEAR_DIRECTION_CHANGE = 'shear_direction_change'
    SHEAR_ALTITUDE_RANGE = 'shear_altitude_range'
    VERTICAL_WIND = 'vertical_wind'
    
    # Rocket keys
    INITIAL_MASS = 'initial_mass'
    REFERENCE_AREA = 'reference_area'
    SELECTED_ROCKET = 'selected_rocket'
    
    # Parachute keys
    SELECTED_PARACHUTE = 'selected_parachute'
    PARACHUTE_ENABLED = 'parachute_enabled'
    PARACHUTE_DEPLOYMENT_ALTITUDE = 'parachute_deployment_altitude'
    PARACHUTE_DIAMETER = 'parachute_diameter'
    PARACHUTE_CD = 'parachute_cd'
    PARACHUTE_MATERIAL = 'parachute_material'
    PARACHUTE_MASS = 'parachute_mass'
    PARACHUTE_MIN_VELOCITY = 'parachute_min_velocity'
    PARACHUTE_MAX_VELOCITY = 'parachute_max_velocity'
    PARACHUTE_INFLATION_TIME = 'parachute_inflation_time'
    
    # Drogue parachute keys
    DROGUE_ENABLED = 'drogue_enabled'
    DROGUE_DEPLOYMENT_ALTITUDE = 'drogue_deployment_altitude'
    DROGUE_DIAMETER = 'drogue_diameter'
    DROGUE_CD = 'drogue_cd'
    DROGUE_MASS = 'drogue_mass'
    DROGUE_INFLATION_TIME = 'drogue_inflation_time'
    
    # Monte Carlo keys
    MONTE_CARLO_RUNS = 'monte_carlo_runs'
    MONTE_CARLO_WORKERS = 'monte_carlo_workers'
    MONTE_CARLO_RESULTS = 'monte_carlo_results'
    
    # Theme/UI keys
    DARK_MODE_ENABLED = 'dark_mode_enabled'
    CURRENT_TAB = 'current_tab'
    CURRENT_LANGUAGE = 'current_language'
    
    # Geometry keys
    FUSELAGE_LENGTH = 'fuselage_length'
    FUSELAGE_DIAMETER = 'fuselage_diameter'
    REAR_LENGTH = 'rear_length'
    REAR_DIAMETER = 'rear_diameter'
    TOTAL_LENGTH = 'total_length'
    LENGTH_NOSECONE_FINS = 'length_nosecone_fins'
    
    # Nosecone keys
    NOSECONE_TYPE = 'nosecone_type'
    NOSECONE_LENGTH = 'nosecone_length'
    NOSECONE_DIAMETER = 'nosecone_diameter'
    
    # Fin keys
    FIN_QUANTITY = 'n_fins'
    FIN_TYPE = 'fin_type'
    FIN_SPAN = 'fin_span'
    FIN_CHORD_ROOT = 'fin_chord_root'
    FIN_CHORD_TIP = 'fin_chord_tip'
    FIN_MID_CHORD = 'fin_mid_chord'
    FIN_SWEEP_ANGLE = 'fin_sweep_angle'
    
    # Inertia keys
    COM_BEFORE_X = 'com_before_x'
    COM_BEFORE_Y = 'com_before_y'
    COM_BEFORE_Z = 'com_before_z'
    COM_AFTER_X = 'com_after_x'
    COM_AFTER_Y = 'com_after_y'
    COM_AFTER_Z = 'com_after_z'
    I_BEFORE_X = 'i_before_x'
    I_BEFORE_Y = 'i_before_y'
    I_BEFORE_Z = 'i_before_z'
    I_AFTER_X = 'i_after_x'
    I_AFTER_Y = 'i_after_y'
    I_AFTER_Z = 'i_after_z'
    
    # Engine keys
    BURN_TIME = 'burn_time'
    PROPELLANT_MASS = 'propellant_mass'
    SPECIFIC_IMPULSE = 'specific_impulse'
    MEAN_THRUST = 'mean_thrust'
    MAX_THRUST = 'max_thrust'
    NOZZLE_DIAMETER = 'nozzle_diameter'
    MASS_FLUX = 'mass_flux'
    GAS_SPEED = 'gas_speed'
    EXIT_PRESSURE = 'exit_pressure'
    MEAN_CHAMBER_PRESSURE = 'mean_chamber_pressure'
    MAX_CHAMBER_PRESSURE = 'max_chamber_pressure'
    THRUST_TO_WEIGHT = 'thrust_to_weight'


class Constants:
    """Master constants class combining all sub-modules."""
    
    # Sub-modules
    Simulation = SimulationConstants
    Environmental = EnvironmentalConstants
    Rocket = RocketConstants
    Wind = WindConstants
    Parachute = ParachuteConstants
    Location = LocationConstants
    MonteCarlo = MonteCarloConstants
    StateKeys = StateKeyConstants
    
    # Common constants
    GRAVITY = 9.80665  # m/s²
    SEA_LEVEL_DENSITY = 1.225  # kg/m³
    SEA_LEVEL_PRESSURE = 101325.0  # Pa
    GAS_CONSTANT_AIR = 287.05  # J/(kg·K)
    GAMMA_AIR = 1.4  # Heat capacity ratio
    
    # Earth constants
    EARTH_RADIUS = 6371000  # meters
    DEGREES_TO_RADIANS = 0.017453292519943295
    RADIANS_TO_DEGREES = 57.29577951308232
    
    # Unit conversions
    METERS_PER_KM = 1000.0
    METERS_PER_FOOT = 0.3048
    METERS_PER_MILE = 1609.34
    KM_PER_DEGREE_LAT = 111.32
    
    # Version
    VERSION = "2.0.4"
