# Author: Code Review Implementation
#         Rocket Simulator Improvements
#         Date: March 26, 2026

"""
Simulation Configuration Constants

Centralized configuration for simulation parameters, preventing magic numbers
and enabling easy tuning for different rocket classes.
"""


class SimulationConstants:
    """Global simulation configuration constants."""
    
    # ========== Force and Acceleration Limits ==========
    MAX_AERODYNAMIC_FORCE = 50_000.0      # [N] Maximum reasonable aerodynamic force
    MIN_VELOCITY_FOR_AERODYNAMICS = 1e-2  # [m/s] Below this, aerodynamics = 0
    MIN_VELOCITY_FOR_LANDING = 0.1        # [m/s] Below this, rocket is landed
    
    # ========== Attitude Limits ==========
    MAX_ANGLE_OF_ATTACK = 25.0    # [deg] Maximum angle of attack before warning
    MAX_PITCH_VELOCITY = 360.0     # [deg/s] Maximum pitch rate (2 rev/s)
    MAX_ROLL_RATE = 720.0          # [deg/s] Maximum roll rate (2 rev/s in degrees)
    
    # ========== Numerical Stability ==========
    QUATERNION_NORM_MIN = 1e-8                    # Minimum quaternion norm
    QUATERNION_NORM_TOLERANCE = 1e-10             # Acceptable deviation from 1.0
    DYNAMIC_PRESSURE_MIN = 1e-3                   # [Pa] Minimum for aerocalc
    REYNOLDS_NUMBER_MIN = 100                     # Minimum reynold number
    
    # ========== Mass Bounds ==========
    MIN_VIABLE_MASS_RATIO = 0.05  # Minimum mass as fraction of initial (5%)
    MAX_MASS_CHANGE_PER_STEP = 0.10  # Max 10% mass change per timestep
    
    # ========== Integration ==========
    MAX_TIMESTEP = 0.01      # [s] Maximum recommended timestep
    MIN_TIMESTEP = 0.00001   # [s] Minimum timestep before warning
    
    # ========== Physical Limits ==========
    MAX_ALTITUDE = 100_000.0      # [m] 100 km maximum altitude
    MAX_VELOCITY = 10_000.0        # [m/s] 10 km/s maximum velocity
    MIN_PRESSURE = 1.0             # [Pa] Minimum atmospheric pressure
    MAX_MACH = 5.0                 # Maximum Mach number (high hypersonic)
    
    # ========== Atmosphere Model ==========
    TROPOSPHERE_HEIGHT = 11_000.0  # [m] Upper bound of troposphere
    STANDARD_GRAVITY = 9.81        # [m/s²] Standard gravity at sea level
    EARTH_RADIUS = 6_371_000.0     # [m] Mean Earth radius
    
    # ========== Aerodynamics Limits ==========
    MAX_DRAG_COEFFICIENT = 2.0      # Maximum reasonable drag coefficient
    MAX_LIFT_COEFFICIENT = 1.5      # Maximum reasonable lift coefficient
    MIN_REFERENCE_AREA = 0.001      # [m²] Minimum reference area (1 cm²)


class RocketClassConstants:
    """Configuration for different rocket classes."""
    
    MODEL_ROCKET = {
        'name': 'Model Rocket',
        'min_mass': 0.1,           # [kg]
        'max_mass': 5.0,           # [kg]
        'max_thrust': 1_000,       # [N]
        'max_velocity': 200,       # [m/s]
        'max_altitude': 10_000,    # [m]
        'min_reference_area': 0.005,  # [m²]
    }
    
    HIGH_POWER = {
        'name': 'High Power Rocket',
        'min_mass': 5.0,           # [kg]
        'max_mass': 50.0,          # [kg]
        'max_thrust': 20_000,      # [N]
        'max_velocity': 500,       # [m/s]
        'max_altitude': 50_000,    # [m]
        'min_reference_area': 0.02,  # [m²]
    }
    
    AMATEUR_ROCKET = {
        'name': 'Amateur Rocket',
        'min_mass': 50.0,          # [kg]
        'max_mass': 500.0,         # [kg]
        'max_thrust': 100_000,     # [N]
        'max_velocity': 2_000,     # [m/s]
        'max_altitude': 100_000,   # [m]
        'min_reference_area': 0.05,   # [m²]
    }
    
    SPACE_LAUNCH = {
        'name': 'Space Launch Vehicle',
        'min_mass': 500.0,         # [kg]
        'max_mass': 1_000_000.0,   # [kg]
        'max_thrust': 10_000_000,  # [N]
        'max_velocity': 8_000,     # [m/s]
        'max_altitude': 1_000_000, # [m]
        'min_reference_area': 0.1,    # [m²]
    }
    
    @staticmethod
    def get_class(rocket_mass):
        """Automatically determine rocket class from mass."""
        if rocket_mass < 5:
            return RocketClassConstants.MODEL_ROCKET
        elif rocket_mass < 50:
            return RocketClassConstants.HIGH_POWER
        elif rocket_mass < 500:
            return RocketClassConstants.AMATEUR_ROCKET
        else:
            return RocketClassConstants.SPACE_LAUNCH


class AtmosphereConstants:
    """Standard atmosphere model constants."""
    
    # Sea level conditions
    SEA_LEVEL_PRESSURE = 101_325.0     # [Pa]
    SEA_LEVEL_TEMPERATURE = 288.15     # [K] 15°C
    SEA_LEVEL_DENSITY = 1.225          # [kg/m³]
    SEA_LEVEL_SOUND_SPEED = 340.3      # [m/s]
    
    # Model layers
    TROPOSPHERE_TEMP_LAPSE = 0.0065    # [K/m] Temperature decrease with altitude
    STRATOSPHERE_BASE = 11_000.0       # [m]
    STRATOSPHERE_TOP = 47_000.0        # [m]
    
    # Gas properties of air
    GAMMA = 1.4                        # Specific heat ratio
    GAS_CONSTANT_AIR = 287.058         # [J/(kg·K)]
    DYNAMIC_VISCOSITY_REF = 1.81e-5    # [Pa·s] at 15°C


class AerodynamicsConstants:
    """Constants for aerodynamic calculations."""
    
    # Drag model components
    SKIN_FRICTION_K1 = 0.0010          # Skin friction coefficient
    PRESSURE_DRAG_FACTOR = 0.5         # Pressure drag multiplier
    BASE_DRAG_COEFFICIENT = 0.12       # Base drag for typical rocket
    INTERFERENCE_DRAG = 0.02           # Interference drag estimate
    
    # Transonic/supersonic
    TRANSONIC_MACH_MIN = 0.8           # Start of transonic region
    TRANSONIC_MACH_MAX = 1.2           # End of transonic region
    SUPERSONIC_WAVE_DRAG_K = 1.5       # Wave drag scaling factor
    
    # Stability calculations (Barrowman method)
    BARROWMAN_K_N = 2.0                # Nosecone drag coefficient
    BARROWMAN_K_F = 1.0                # Fin interacting factor
    BARROWMAN_K_B = 1.0                # Base drag factor


class EngineConstants:
    """Constants for engine calculations."""
    
    # Chamber conditions
    DEFAULT_CHAMBER_TEMPERATURE = 3000.0   # [K]
    DEFAULT_CHAMBER_PRESSURE = 5e6         # [Pa] 5 MPa
    
    # Nozzle flow
    THROAT_AREA_DEFAULT = 0.001           # [m²]
    EXPANSION_RATIO_DEFAULT = 8.0         # Nozzle expansion ratio
    
    # Propellant properties
    TYPICAL_EXIT_VELOCITY = 4500.0         # [m/s] Typical rocket exit velocity
    TYPICAL_SPECIFIC_IMPULSE = 450         # [s] Typical ISP
    
    # Thrust curve
    THRUST_CURVE_INTERPOLATION = 'cubic'   # Method for thrust curve interpolation


class WindConstants:
    """Constants for wind model calculations and limits."""
    
    # Wind speed limits
    MAX_WIND_SPEED = 100.0              # [m/s] Maximum realistic wind speed
    MIN_WIND_SPEED = 0.0                # [m/s] Minimum wind speed
    DEFAULT_WIND_SPEED = 5.0           # [m/s] Default wind speed
    
    # Altitude limits
    DEFAULT_REFERENCE_HEIGHT = 10.0    # [m] Standard reference height for wind measurements
    DEFAULT_LAUNCH_ALTITUDE = 0.0        # [m] Default launch site elevation
    DEFAULT_SHEAR_ALTITUDE_RANGE = 1000.0  # [m] Default altitude range for shear
    
    # Surface roughness (z0)
    ROUGHNESS_WATER = 0.0002            # [m] Water surface
    ROUGHNESS_GRASSLAND = 0.01          # [m] Grassland
    ROUGHNESS_FOREST = 0.1              # [m] Forest/edge
    ROUGHNESS_URBAN = 0.5               # [m] Dense forest/urban
    DEFAULT_ROUGHNESS = 0.1            # [m] Default surface roughness
    
    # Power law exponent (alpha)
    POWER_LAW_SMOOTH = 0.10             # Smooth surfaces (water, grass)
    POWER_LAW_AVERAGE = 0.20            # Average surfaces (crop land, suburban)
    POWER_LAW_ROUGH = 0.40              # Rough surfaces (forest, urban)
    DEFAULT_POWER_LAW_EXPONENT = 0.2    # Default exponent
    MIN_POWER_LAW_EXPONENT = 0.05        # Minimum reasonable exponent
    MAX_POWER_LAW_EXPONENT = 0.50        # Maximum reasonable exponent
    
    # Gust parameters
    DEFAULT_GUST_INTENSITY = 0.1        # [0-1] Default turbulence intensity
    DEFAULT_GUST_LENGTH_SCALE = 300.0   # [m] Default gust length scale
    MIN_GUST_LENGTH_SCALE = 1.0         # [m] Minimum gust length scale
    MAX_GUST_INTENSITY = 1.0            # Maximum turbulence intensity
    NOMINAL_WIND_SPEED = 10.0           # [m/s] Reference speed for Dryden filter
    
    # Vertical wind limits
    MAX_VERTICAL_WIND = 20.0            # [m/s] Maximum vertical wind (updraft/downdraft)
    MIN_VERTICAL_WIND = -20.0           # [m/s] Minimum vertical wind
    
    # Shear parameters
    DEFAULT_SHEAR_DIRECTION_CHANGE = 0.0  # [deg] Default directional shear
    DEFAULT_VERTICAL_WIND = 0.0         # [m/s] Default vertical wind speed
    SHEAR_SPEED_INCREASE_FACTOR = 0.1    # Speed increase factor per shear altitude range
    
    # Wind direction
    DEFAULT_WIND_DIRECTION = 0.0        # [deg] Default wind direction (from North)
    NORTH = 0.0                         # [deg] Wind from North
    EAST = 90.0                        # [deg] Wind from East
    SOUTH = 180.0                      # [deg] Wind from South
    WEST = 270.0  # [deg] Wind from West


class GravitationalConstants:
    """Constants for gravitational calculations."""
    
    # Earth gravitational parameter
    MU_EARTH = 3.986004418e14  # [m³/s²] Earth gravitational parameter
    
    # Earth dimensions
    EARTH_MIN_RADIUS = 6.371e6  # [m] Minimum reasonable distance from Earth center
    EARTH_MEAN_RADIUS = 6_371_000.0  # [m] Mean Earth radius (duplicate from AtmosphereConstants for convenience)


class ParachuteConstants:
    """Constants for parachute deployment and descent calculations."""
    
    # Default parachute parameters
    DEFAULT_DIAMETER = 1.0  # [m] Default canopy diameter
    DEFAULT_CD = 1.5  # [-] Default drag coefficient
    DEFAULT_NAME = 'Main Parachute'  # Default parachute name
    DEFAULT_MATERIAL = 'ripstop_nylon'  # Default parachute material
    DEFAULT_INFLATION_TIME = 0.5  # [s] Default time to full inflation
    
    # Deployment parameters
    DEFAULT_DEPLOYMENT_ALTITUDE = 300.0  # [m] Default altitude for main parachute deployment
    DEFAULT_MIN_VELOCITY = 5.0  # [m/s] Minimum safe deployment velocity
    DEFAULT_MAX_VELOCITY = 100.0  # [m/s] Maximum safe deployment velocity
    
    # Drogue chute parameters
    DEFAULT_DROGUE_DIAMETER = 0.3  # [m] Default drogue diameter
    DEFAULT_DROGUE_CD = 1.5  # [-] Default drogue drag coefficient
    DEFAULT_DROGUE_DEPLOYMENT_ALTITUDE = 600.0  # [m] Default drogue deployment altitude
    DEFAULT_DROGUE_INFLATION_TIME = 0.2  # [s] Default drogue inflation time
    
    # Physics constants
    STANDARD_GRAVITY = 9.81  # [m/s²] Standard gravitational acceleration (duplicate for convenience)


class PlanetConstants:
    """Constants for planet/Earth rotation calculations."""
    
    # Earth rotation
    EARTH_ROTATION_SPEED = 7.2722e-5  # [rad/s] Earth rotation velocity
    
    # Mathematical constants
    TWO_PI = 2.0 * 3.141592653589793  # [rad] Full circle in radians (2π)
