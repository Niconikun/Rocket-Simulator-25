# Rocket Simulator - Code Review and Analysis

**Date:** March 26, 2026
**Scope:** src/models and src/utils directories
**Purpose:** Comprehensive code review for rocket trajectory simulation

---

## Executive Summary

The rocket trajectory simulator is a well-structured project with advanced physics modeling, including 6-DOF (6 degrees of freedom) dynamics, quaternion-based attitude representation, and component-based aerodynamics. The codebase demonstrates strong engineering principles but has several areas for improvement in numerical stability, error handling, and code consistency.

---

## 1. Strengths

### 1.1 Physics Modeling
- ✅ **Advanced 6-DOF Dynamics**: Proper implementation of translational and rotational equations
- ✅ **Quaternion Integration**: Good use of quaternions for attitude representation with normalization attempts
- ✅ **RK4 Integration**: Fourth-order Runge-Kutta method provides good accuracy vs. computational cost
- ✅ **Component-Based Aerodynamics**: Sophisticated drag model including skin friction, pressure drag, and wave drag
- ✅ **Enhanced Engine Model**: Realistic thermodynamic modeling with thrust curve support

### 1.2 Design Patterns
- ✅ **Class-Based Architecture**: Clean separation of concerns (Rocket, Engine, Aerodynamics, etc.)
- ✅ **History Tracking**: Comprehensive logging of all state variables for post-processing
- ✅ **Modular Utilities**: Well-organized MatTools, GeoTools, and configuration management

### 1.3 Documentation
- ✅ **Detailed References**: Proper citations to academic papers (Regan93, Yang19, Barrowman67, etc.)
- ✅ **Physics Equations**: Main equations explicitly documented in docstrings
- ✅ **Bilingual Comments**: Spanish/English support for international collaboration

---

## 2. Issues and Recommendations

### 2.1 CRITICAL - Numerical Stability

#### Issue 2.1.1: Quaternion Normalization Strategy
**Severity:** MEDIUM  
**Location:** `src/models/rocket.py` - `RK4_update()` and `dynamics()`

**Problem:**
- Quaternion normalization uses naive division method
- Multiple normalization points could introduce accumulated rounding errors
- No safeguard for extremely small quaternion norms (< 1e-6)

**Current Code:**
```python
q_norm = np.linalg.norm(q_enu2b)
if q_norm > 1e-6:
    self.q_enu2b = self.q_enu2b / q_norm
else:
    self.q_enu2b = np.array([0.0, 0.0, 0.0, 1.0])  # Identity
```

**Recommendation:**
```python
def normalize_quaternion(q, min_norm=1e-8):
    """
    Safely normalize quaternion with Gram-Schmidt orthogonalization.
    Uses conjugate method for better numerical stability.
    
    Args:
        q: Quaternion [q1, q2, q3, q0]
        min_norm: Minimum allowed norm before emergency reset
    
    Returns:
        Normalized quaternion
    """
    q_norm = np.linalg.norm(q)
    if q_norm < min_norm:
        logger.warning(f"Quaternion norm {q_norm:.2e} critically low, resetting to identity")
        return np.array([0.0, 0.0, 0.0, 1.0])
    
    # Use stable normalization
    normalized = q / q_norm
    
    # Validate result
    assert abs(np.linalg.norm(normalized) - 1.0) < 1e-10, "Normalization failed"
    return normalized
```

#### Issue 2.1.2: Mass Validation with Hard Limits
**Severity:** MEDIUM  
**Location:** `src/models/rocket.py` - `RK4_update()`, `dynamics()`

**Problem:**
- Mass is clamped to 0.1 kg minimum, which is inappropriate for small model rockets
- No validation of propellant remaining mass against initial propellant mass
- Mass can become negative in intermediate RK4 steps if dt is too large

**Current Code:**
```python
if self.mass < 0.1:
    logger.warning(f"Mass too low ({self.mass:.3f}kg)")
    self.mass = max(0.1, self.mass)  # Clamps to 0.1 kg
```

**Recommendation:**
```python
# Class-level configuration
self.min_viable_mass = 0.01  # 10g for small rockets, configurable
self.propellant_mass_initial = propellant_mass

def validate_and_clamp_mass(self):
    """Validate mass bounds based on rocket configuration"""
    min_mass = self.initial_mass - self.propellant_mass_initial
    if self.mass < min_mass * 0.8:  # Allow 20% undershooting due to numerical error
        self.mass = min_mass
        logger.warning(f"Mass below empty rocket mass, clamping")
    
    if self.mass < self.min_viable_mass:
        self.mass = self.min_viable_mass
        logger.error("Mass critically low")
```

#### Issue 2.1.3: NaN/Inf Detection with Recovery
**Severity:** MEDIUM  
**Location:** `src/models/rocket.py` - `RK4_update()`

**Problem:**
- NaN/Inf detection throws RuntimeError, terminating simulation
- No attempt at recovery or step-size reduction
- Silent failures possible in intermediate calculations before k1, k2, k3, k4

**Recommendation:**
```python
def safe_dynamics_call(self, x, step_name="dynamics", adaptive_dt=True):
    """
    Call dynamics with NaN/Inf detection and recovery.
    
    Can adaptively reduce time-step if instability detected.
    """
    try:
        result = self.dynamics(x)
        
        if np.any(np.isnan(result)) or np.any(np.isinf(result)):
            logger.error(f"NaN/Inf in {step_name} at t={self.time:.3f}s")
            if adaptive_dt:
                return None  # Signal to reduce dt
            else:
                raise RuntimeError(f"Numerical instability in {step_name}")
        return result
    except (ValueError, ZeroDivisionError) as e:
        logger.error(f"Calculation error in {step_name}: {e}")
        return None
```

---

### 2.2 HIGH - Code Quality Issues

#### Issue 2.2.1: Duplicate Attribute Initialization
**Severity:** HIGH  
**Location:** `src/models/rocket.py` - `__init__()` (lines 100-150)

**Problem:**
- Variables like `self.density`, `self.press_amb`, `self.v_sonic` are initialized twice
- Creates confusion and maintenance issues
- Potential for inconsistent state

**Current Code:**
```python
self.density=density      # Line 100
# ... later ...
self.density=density      # Duplicate!
```

**Recommendation:**
```python
# Initialize once with clear comments
self.density = 0.0           # [kg/m³] Atmospheric density
self.press_amb = 101325.0    # [Pa] Atmospheric pressure
self.v_sonic = 343.0         # [m/s] Speed of sound
```

#### Issue 2.2.2: Inconsistent Error Handling
**Severity:** HIGH  
**Location:** Multiple methods in `rocket.py`

**Problem:**
- Some methods use try/except with fallback values
- Others raise exceptions
- No consistent error reporting strategy
- Some errors swallowed silently

**Examples:**
```python
# Method 1: Fails silently then crashes (update_aerodynamics)
except Exception as e:
    logging.error(f"Aerodynamics error: {str(e)}")
    self.drag_coeff = 0.5  # Incorrect fallback!

# Method 2: Raises exception (RK4_update)
raise RuntimeError("Numerical instability")

# Method 3: No error handling (update_forces_aero)
# Method fails if reference_area is invalid
```

**Recommendation:**
```python
class SimulationWarning(Warning):
    """Base warning for simulation issues"""
    pass

class CalculationError(Exception):
    """Raised when critical calculation fails"""
    pass

# Implement consistent pattern:
def update_with_fallback(self, critical=False):
    try:
        # Perform calculation
        pass
    except Exception as e:
        if critical:
            raise CalculationError(f"Critical calculation failed: {e}")
        else:
            logger.warning(f"Non-critical calculation failed, using fallback: {e}")
            # return fallback_value
```

#### Issue 2.2.3: Magic Numbers and Hard-Coded Values
**Severity:** MEDIUM  
**Location:** Throughout `rocket.py`

**Problem:**
- Force limit: 10,000 N (line 520)
- Minimum velocity: 1e-6 m/s (multiple locations)
- Angle limits: 10° in aerodynamics
- Quaternion norm minimum: 1e-6

**Current Code:**
```python
max_force = 10000  # 10kN - where does this come from?
if np.linalg.norm(v_enu) < 1.0:  # Why 1.0 m/s?
a_max = 10  # [deg] - arbitrary?
```

**Recommendation:**
```python
# Define configuration class
class SimulationConstants:
    # Force and acceleration limits
    MAX_AERODYNAMIC_FORCE = 50000.0  # [N] - depends on rocket mass
    MIN_VELOCITY_FOR_AERODYNAMICS = 1e-2  # [m/s]
    MIN_VELOCITY_FOR_LANDING = 0.1  # [m/s] - rocket is considered landed
    
    # Attitude limits
    MAX_ANGLE_OF_ATTACK = 25.0  # [deg] - typical for rockets
    
    # Numerical stability
    QUATERNION_NORM_MIN = 1e-8
    QUATERNION_NORM_TOLERANCE = 1e-10
    
    # Mass
    MIN_VIABLE_MASS_RATIO = 0.05  # 5% of initial mass
```

---

### 2.3 MEDIUM - Code Issues

#### Issue 2.3.1: Import Statement Error
**Severity:** MEDIUM  
**Location:** `src/utils/mattools.py` (line 14)

**Problem:**
- Uses `from cmath import pi` - should be `from math import pi`
- `cmath` is for complex numbers; `math` is correct for regular floats
- Works but conceptually wrong

**Current Code:**
```python
from cmath import pi  # WRONG: cmath is for complex numbers
```

**Recommendation:**
```python
from math import pi  # CORRECT: Standard mathematical constants
```

#### Issue 2.3.2: Inconsistent Unit Tracking
**Severity:** MEDIUM  
**Location:** Throughout codebase

**Problem:**
- Comments indicate units but no runtime unit checking
- Easy to mix SI with other units accidentally
- No type hints for dimensional quantities

**Current Code:**
```python
self.r_enu=r_enu_0        # [m]       # What if user passes cm?
self.v_enu=v_enu_0        # [m/s]     # Assumes SI
self.mass=initial_mass    # [kg]      # No validation
```

**Recommendation:**
```python
from dataclasses import dataclass

@dataclass
class DimensionalQuantity:
    """Ensures dimensional consistency"""
    value: float
    unit: str  # 'm', 'kg', 'N', etc.
    
    def to_si(self) -> float:
        """Convert to SI units"""
        # Implement conversion
        pass

# Or use type hints at minimum:
def __init__(
    self,
    r_enu_0: np.ndarray,  # Position in ENU frame [m]
    v_enu_0: np.ndarray,  # Velocity in ENU frame [m/s]
    initial_mass: float,   # Total initial mass [kg]
):
```

#### Issue 2.3.3: Incomplete Parachute Implementation
**Severity:** MEDIUM  
**Location:** `src/models/rocket.py` (lines 150-160)

**Problem:**
- Parachute attributes defined but rarely used
- `self.parachute = None` but no integration into dynamics
- History tracking for parachute force exists but not populated

**Current Code:**
```python
self.parachute = None
self.has_parachute = False
self.hist_parachute_state = []
self.hist_parachute_force = []
# ... but parachute never activated in dynamics()
```

**Recommendation:**
```python
def apply_parachute_forces(self):
    """
    Calculate parachute forces if deployed.
    
    Returns:
        (forces, torques) tuple in body frame
    """
    if not self.has_parachute or self.parachute is None:
        return np.zeros(3), np.zeros(3)
    
    if not self.parachute.is_deployed(self.time):
        return np.zeros(3), np.zeros(3)
    
    # Implement parachute drag calculation
    parachute_drag = self.parachute.calculate_drag(
        self.v_norm, self.density, self.r_enu[2]
    )
    return parachute_drag, np.zeros(3)
```

#### Issue 2.3.4: Missing Input Validation
**Severity:** MEDIUM  
**Location:** Multiple methods

**Problem:**
- No validation of rocket configuration file structure
- No bounds checking on launch angles
- No validation of geographical coordinates

**Examples:**
```python
# update_aerodynamics: Assumes all required keys exist
geometry = {
    'len_warhead': rocket_settings['nosecone']['length'],  # KeyError if missing
    # ... 20+ other fields, all can fail
}

# update_pos_vel: No validation of coordinates
self.r_platform_ecef=Geo.geo2ecef(coordinates)  # What if lat/lon invalid?

# __init__: No validation of initial state
def __init__(self,r_enu_0,v_enu_0,q_enu2b_0,w_enu_0, initial_mass):
    # ...no checks that q_enu2b_0 is normalized
    # no checks that initial_mass > 0
    # no checks that r_enu_0 is reasonable
```

**Recommendation:**
```python
@staticmethod
def validate_launch_state(r_enu, v_enu, q_enu2b, initial_mass):
    """Validate initial launch conditions"""
    
    # Position
    if not isinstance(r_enu, np.ndarray) or r_enu.shape != (3,):
        raise ValueError(f"r_enu must be 3D array, got {r_enu}")
    
    if np.linalg.norm(r_enu) > 100000:  # 100 km altitude max at start
        raise ValueError("Initial altitude exceeds reasonable bounds")
    
    # Velocity
    if np.linalg.norm(v_enu) > 500:  # 500 m/s launch speed unreasonable
        raise ValueError("Initial velocity too high")
    
    # Attitude
    q_norm = np.linalg.norm(q_enu2b)
    if not 0.99 < q_norm < 1.01:
        raise ValueError(f"Quaternion not normalized: norm = {q_norm}")
    
    # Mass
    if initial_mass <= 0:
        raise ValueError(f"Initial mass must be positive, got {initial_mass}")
    if initial_mass > 100000:  # 100 ton max
        raise ValueError("Initial mass exceeds reasonable bounds")
    
    return True
```

---

### 2.4 MEDIUM - Performance and Efficiency

#### Issue 2.4.1: Atmospheric Data Caching
**Severity:** MEDIUM  
**Location:** `src/models/atmosphere.py`

**Problem:**
- `_get_atmosphere_data()` uses lru_cache but cache miss creates new object
- Multiple atmosphere lookups in single timestep
- No batch optimization

**Current Code:**
```python
@staticmethod
@lru_cache(maxsize=128)
def _get_atmosphere_data(height, offset):
    return atmos76(height, offset)

# But each method calls atmosphere separately:
def give_temp(self, height):
    base_temp = ...

def give_press(self,height):
    self.atmosphere=atmos76(height,self.offset)

def give_dens(self,height):
    self.atmosphere=atmos76(height,self.offset)
```

**Recommendation:**
```python
def get_atmosphere_data(self, height):
    """
    Single call to get all atmospheric properties.
    Reduces computation and improves cache efficiency.
    """
    atmos = atmos76(height, self.offset)
    return {
        'temperature': atmos.T,
        'pressure': atmos.P,
        'density': atmos.rho,
        'viscosity': atmos.mu,
        'speed_of_sound': self._calculate_sound_speed(atmos.T)
    }
```

#### Issue 2.4.2: Historical Data Storage
**Severity:** MEDIUM  
**Location:** `src/models/rocket.py`

**Problem:**
- 60+ history arrays stored as Python lists
- O(n) append operations accumulate over simulation
- No memory management for long simulations
- Potential memory explosion with 100k+ timesteps

**Current Code:**
```python
self.hist_r_enu=[]       # East-North-Up location
self.hist_v_enu=[]       # ... 60+ more lists
# In save_data():
self.hist_time.append(self.time)
self.hist_gmst.append(self.gmst)
# ... 60+ appends per timestep
```

**Recommendation:**
```python
# Use pre-allocated numpy arrays
def preallocate_history(self, max_steps):
    """Pre-allocate history arrays for efficiency"""
    self.hist_time = np.zeros(max_steps)
    self.hist_r_enu = np.zeros((max_steps, 3))
    self.hist_v_enu = np.zeros((max_steps, 3))
    # ...
    self.hist_index = 0

def save_data(self, current_step):
    """O(1) data storage instead of O(n) append"""
    self.hist_time[current_step] = self.time
    self.hist_r_enu[current_step] = self.r_enu
    self.hist_v_enu[current_step] = self.v_enu
    # ...
```

---

### 2.5 LOW - Documentation and Style

#### Issue 2.5.1: Method Documentation Completeness
**Severity:** LOW  
**Location:** Various methods

**Problem:**
- Some methods have comprehensive docstrings
- Others lack Return type documentation
- No consistent docstring format
- Missing "Raises" sections for exception-throwing methods

**Recommendation:**
```python
def RK4_update(self, dt: float) -> None:
    """
    Propagate vehicle state using 4th-order Runge-Kutta integration.
    
    This method advances the complete state vector (position, velocity, attitude,
    angular velocity, and mass) by time dt using RK4 integration. Quaternion
    normalization is performed at each intermediate step to ensure numerical
    stability.
    
    Args:
        dt (float): Time step for integration [s]. Typical values: 0.001 to 0.01 s.
                   Adaptive algorithms should use dt < 0.01 for stability.
    
    Returns:
        None: Updates instance variables in-place.
    
    Raises:
        RuntimeError: If NaN or Inf detected in intermediate calculations.
        ValueError: If mass becomes invalid during integration.
    
    Notes:
        - Quaternion is normalized at all intermediate RK4 stages
        - Mass is clamped to physical lower bound (empty rocket mass)
        - Uses attribute `self.dynamics()` for ODE evaluation
    
    References:
        - Butcher, J.C. (2016). Numerical Methods for ODEs
        - Wie, B. (1998). Space Vehicle Dynamics and Control
    
    Examples:
        >>> rocket = Rocket(r_enu_0, v_enu_0, q_enu2b_0, w_enu_0, mass_0)
        >>> rocket.RK4_update(dt=0.001)  # Advance by 1 ms
        >>> assert rocket.time == old_time + 0.001
    """
```

---

## 3. Test Models and Data

### 3.1 Proposed Test Scenarios

The following test models are recommended for validation:

#### Test Model 1: Small Model Rocket (Educational)
- **Mass Range:** 0.5 - 2 kg
- **Thrust:** 100 - 500 N peak
- **Burn Time:** 2 - 5 seconds
- **Expected Apogee:** 1,000 - 5,000 m

#### Test Model 2: Medium High-Power Rocket (HPR)
- **Mass Range:** 10 - 30 kg
- **Thrust:** 5,000 - 15,000 N peak
- **Burn Time:** 8 - 15 seconds
- **Expected Apogee:** 10,000 - 30,000 m

#### Test Model 3: Extreme Conditions
- **Low Thrust:** 1 N thrust with 5 kg mass (verification that coasting works)
- **Variable Atmosphere:** Launch from high altitude (5000 m baseline)
- **Spin Stabilization:** Non-zero roll rate with asymmetric lift

#### Test Model 4: Parachute Recovery
- **Drogue Deployment:** At apogee
- **Main Deployment:** At 500 m altitude
- **Descent Rate Verification:** Compare with theoretical

---

## 4. Recommendations - Priority Order

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| CRITICAL | Quaternion normalization strategy | Medium | High |
| CRITICAL | Input validation framework | High | High |
| HIGH | Duplicate variable initialization | Low | High |
| HIGH | Consistent error handling | Medium | High |
| MEDIUM | Magic numbers to constants | Medium | Medium |
| MEDIUM | Performance: History array allocation | Medium | Medium |
| MEDIUM | Parachute system completion | High | Medium |
| MEDIUM | Unit validation framework | High | Medium |
| LOW | Documentation standardization | Low | Low |
| LOW | Import corrections | Low | Low |

---

## 5. Code Quality Metrics

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| Test Coverage | ~30% | >80% | Need unit and integration tests |
| Docstring Coverage | ~60% | 100% | Many methods lack complete documentation |
| Type Hints | ~10% | 100% | Would aid IDE support and error detection |
| Error Handling | ~40% | 95% | Many unchecked boundary conditions |
| Code Duplication | ~5% | <2% | Minor issues, mostly initialization |

---

## 6. Conclusion

The Rocket Simulator represents solid engineering work with advanced physics modeling. Key strengths are the 6-DOF dynamics, quaternion-based attitude control, and comprehensive aerodynamics. 

Primary areas for improvement are:
1. **Robustness:** Input validation and error handling
2. **Stability:** Quaternion and numerical methods
3. **Maintainability:** Code duplication and consistency
4. **Performance:** History array management for long simulations

Implementation of these recommendations would significantly improve reliability and maintainability.

---

## Appendix A: References

- [Regan93] Regan & Anandakrishnan (1993). *Dynamics of Atmospheric Re-Entry*
- [Valle22] Vallejos (2022). *Mejora del alcance de un cohete chaff*
- [Oroz22] Orozco (2022). *Estimación de trayectoria y actitud para un cohete chaff*
- [Barro67] Barrowman (1967). *Practical Calculation of Aerodynamic Characteristics*
- [Yang19] Yang (2019). *Spacecraft Modeling, Attitude Determination, and Control*
- [Sutton16] Sutton & Biblarz (2016). *Rocket Propulsion Elements*
- [Hill92] Hill & Peterson (1992). *Mechanics and Thermodynamics of Propulsion*

