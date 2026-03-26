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
