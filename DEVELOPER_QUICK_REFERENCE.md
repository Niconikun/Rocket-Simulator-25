# Rocket Simulator - Developer Quick Reference

**Last Updated:** March 26, 2026

---

## File Structure at a Glance

```
src/
├── models/           # Physics calculations
│   ├── rocket.py     # 🔴 Core 6-DOF dynamics (950+ lines) - MOST IMPORTANT
│   ├── engine.py     # Thrust & thermodynamics
│   ├── aerodynamics.py/.py # Component-based drag
│   ├── atmosphere.py # USSA 1976 air properties
│   ├── planet.py     # Gravitational model
│   ├── clock.py      # Time/GMST tracking
│   └── gravitational.py
│
└── utils/           # Utilities & helpers
    ├── mattools.py  # 🟡 Vector/quaternion ops (has import bug line 14)
    ├── geotools.py  # Coordinate frame transforms
    ├── units.py     # Unit conversion tables
    ├── simulation_manager.py  # Save/load trajectory data
    ├── location_manager.py
    └── thrust_processor.py
```

---

## Understanding the Main Simulation Loop

### State Vector Definition
```python
x = [
    r_enu[0:3],      # Position in ENU frame [m]
    v_enu[3:6],      # Velocity in ENU frame [m/s]  
    q_enu2b[6:10],   # Quaternion (attitude) [-]
    w_b[10:13],      # Angular velocity in body frame [rad/s]
    mass[13],        # Vehicle mass [kg]
]
```

### Integration Method: RK4
```python
# In workers/simulation_worker.py, called every timestep (typically 1 ms):
rocket.RK4_update(dt)

# Inside RK4_update (rocket.py, line ~724):
1. Call dynamics(x) → k1
2. Call dynamics(x + 0.5*dt*k1) → k2  [normalize quaternion]
3. Call dynamics(x + 0.5*dt*k2) → k3  [normalize quaternion]
4. Call dynamics(x + dt*k3) → k4      [normalize quaternion]
5. Update: x_new = x + (dt/6)*(k1 + 2*k2 + 2*k3 + k4)
6. Normalize final quaternion
```

### Physics in `dynamics()` Method
Called 4× per timestep. Returns time derivatives:
```python
def dynamics(self, x):
    # Extract state
    r_enu, v_enu, q_enu2b, w_b, mass = unpack(x)
    
    # Translational: F = ma
    r_dot = v_enu
    v_dot = (self.forces_b + gravity) / mass
    
    # Rotational: τ = dL/dt = dω/dt * I + ω × L
    q_dot = 0.5 * ω_skew @ q
    w_dot = I_inv @ (torques - cross(ω, I @ ω))
    
    # Mass: dm/dt from propellant burn
    m_dot = -mass_flow_rate
    
    return concatenate([r_dot, v_dot, q_dot, w_dot, m_dot])
```

---

## Critical Things to Know

### ⚠️ Quaternions Are Fragile
- Always normalized (norm = 1.0)
- Small floating-point errors accumulate
- **Must normalize** after each RK4 step or they diverge
- If norm < 1e-6, use identity: [0, 0, 0, 1]

**Code Location:** `rocket.py` lines 724-950 (RK4_update method)

```python
# EVERY RK4 intermediate step normalizes:
q_norm = np.linalg.norm(q_k2)
if q_norm > 1e-6:
    q_k2 = q_k2 / q_norm  # ← CRITICAL
```

### ⚠️ Mass Boundaries
**Current code:** Clamps mass to 0.1 kg minimum
- Problem: Too high for small model rockets (< 10g)
- Should be: mass ≥ (initial_mass - propellant_mass)

**Fix Location:** `rocket.py` lines 850-860

### ⚠️ History Arrays Are Slow
- 60+ Python lists, O(n) append each step
- For 100,000 steps: 6,000,000 append operations
- **Better:** Pre-allocate numpy arrays with O(1) indexing

**Location:** `rocket.py` lines 153-200

### ⚠️ No Input Validation
Configuration files assumed valid - missing keys → KeyError
- Test before using: Check required keys exist
- Validate bounds: mass > 0, positions reasonable
- Validate files: load_json() should have try/except

**Location:** `rocket.py` lines 383-410 (update_aerodynamics)

---

## Common Operations

### Loading Rocket Config
```python
import json

with open('data/rockets/configs/test_rocket.json') as f:
    config = json.load(f)

# Config structure:
config['engine']['burn_time']       # float [s]
config['engine']['mean_thrust']     # float [N]
config['geometry']['total_length']  # float [m]
config['fins']['N_fins']            # int [-]
config['initial_mass']              # float [kg]
```

### Creating Rocket Instance
```python
from src.models.rocket import Rocket
import numpy as np

r_enu = np.array([0.0, 0.0, 0.0])        # Position at origin
v_enu = np.array([0.1, 0.1, 0.0])        # Small initial velocity  
q_enu2b = np.array([0.0, 0.0, 0.0, 1.0]) # Identity quaternion (no rotation)
w_enu = np.array([0.0, 0.0, 0.0])         # No angular velocity
initial_mass = 1.5

rocket = Rocket(
    r_enu_0=r_enu,
    v_enu_0=v_enu,
    q_enu2b_0=q_enu2b,
    w_enu_0=w_enu,
    initial_mass=initial_mass
)
```

### Advancing Simulation by dt
```python
dt = 0.001  # 1 millisecond

# Single step
rocket.RK4_update(dt)

# After step, data stored in:
print(rocket.r_enu)      # New position
print(rocket.v_enu)      # New velocity
print(rocket.mass)       # New mass
print(rocket.time)       # Updated time

# Save all history
rocket.save_data()  # Appends to all hist_* lists
```

### Checking Simulation State
```python
# Is rocket off ground?
altitude = rocket.r_enu[2]  # Z component of position
is_flying = altitude > 0.1

# Did it land?
velocity = np.linalg.norm(rocket.v_enu)
is_landed = (altitude < 0.1) and (velocity < 0.5)

# What's the attitude?
pitch = rocket.pitch      # [deg] from horizontal
yaw = rocket.yaw          # [deg] from East  
roll = rocket.roll        # [deg] around axis

# Is it supersonic?
mach = rocket.mach        # Dimensionless
is_supersonic = mach > 1.0
```

---

## Key Methods in Rocket Class

### Update Methods (Call These)
| Method | Purpose | When |
|--------|---------|------|
| `update_aerodynamics(rocket_name)` | Calculate drag/lift | Each step |
| `update_engine(rocket_name)` | Get thrust | Each step |
| `update_atmosphere(dens, P, c_sound)` | Set air properties | Each step |
| `update_pos_vel(coordinates)` | Calculate angles/attitude | Each step |
| `update_forces_aero(ref_area)` | Calculate aerodynamic forces | Each step |
| `update_forces_engine()` | Calculate engine forces | Each step |
| `RK4_update(dt)` | Integrate dynamics | Main loop |
| `save_data()` | Store history | Once per significant step |

### Key Attributes (Read These)
| Attribute | Type | Units | Meaning |
|-----------|------|-------|---------|
| `r_enu` | np.array(3,) | [m] | Position |
| `v_enu` | np.array(3,) | [m/s] | Velocity |
| `q_enu2b` | np.array(4,) | [-] | **Quaternion (normalizes itself)** |
| `w_enu` | np.array(3,) | [rad/s] | Angular velocity |
| `mass` | float | [kg] | Current mass |
| `pitch` | float | [deg] | Pitch angle |
| `mach` | float | [-] | Mach number |
| `time` | float | [s] | Simulation time |

---

## Common Bugs and How to Spot Them

### NaN/Inf in Results
**Symptom:** Trajectory suddenly has NaN values
**Cause 1:** Quaternion degraded (norm ≠ 1)
**Cause 2:** Division by zero (velocity = 0)
**Cause 3:** Excessive forces (aerodynamics blow up)

**Check:**
```python
# After each step:
assert not np.any(np.isnan(rocket.r_enu)), "Position is NaN!"
assert not np.any(np.isinf(rocket.v_enu)), "Velocity is Inf!"
assert 0.99 < np.linalg.norm(rocket.q_enu2b) < 1.01, "Quaternion denormalized!"
```

### Attitude Flipping
**Symptom:** Rocket suddenly tumbles
**Cause:** Quaternion norm diverged below 1e-6
**Fix:** Check normalization in RK4_update (lines ~800-850)

### Excessive Drift
**Symptom:** Rocket drifts sideways unreasonably
**Cause:** Launch angle includes yaw/wind effects
**Check:** Compare against simple ballistic trajectory

### Crash at Start
**Symptom:** RuntimeError "NaN/Inf" immediately
**Cause:** Invalid initial state (e.g., q_enu2b not normalized)
**Fix:** Validate inputs before creating Rocket

---

## Testing Workflow

### Quick Sanity Check
```python
from src.models.rocket import Rocket
from src.models.atmosphere import Atmosphere
from src.models.planet import Planet
import numpy as np

# Create rocket
rocket = Rocket(
    r_enu_0=np.array([0,0,0]),
    v_enu_0=np.array([0,0,0]),
    q_enu2b_0=np.array([0,0,0,1]),
    w_enu_0=np.array([0,0,0]),
    initial_mass=1.5
)

# Simulate 100 steps
for i in range(100):
    # Update atmosphere
    atm = Atmosphere(temp_sensed=20)
    rocket.update_atmosphere(
        atm.give_dens(rocket.r_enu[2]),
        atm.give_press(rocket.r_enu[2]),
        atm.give_v_sonic(rocket.r_enu[2])
    )
    
    # Update aerodynamics & engine
    rocket.update_aerodynamics("test_rocket")
    rocket.update_engine("test_rocket")
    
    # Integrate
    rocket.RK4_update(dt=0.001)
    
    # Save
    rocket.save_data()

print(f"Final altitude: {rocket.r_enu[2]:.1f} m")
print(f"Final velocity: {np.linalg.norm(rocket.v_enu):.1f} m/s")
print(f"Final mass: {rocket.mass:.2f} kg")
```

### Using Test Models
```bash
# Test models are in:
data/rockets/configs/small_model_rocket.json
data/rockets/configs/medium_hpr_rocket.json
data/rockets/configs/high_altitude_rocket.json
data/rockets/configs/spin_stabilized_rocket.json
data/rockets/configs/coasting_test_rocket.json

# Expected results in:
TEST_MODELS_GUIDE.md
```

---

## Performance Profiling

```python
import time
import cProfile

# Profile a simulation
profiler = cProfile.Profile()
profiler.enable()

# Run simulation
for _ in range(10000):
    rocket.RK4_update(0.001)

profiler.disable()
profiler.print_stats(sort='cumulative')

# Look for:
# - dynamics() taking >80% of time (normal)
# - list.append() taking >10% (means history is slow)
# - sqrt/exp taking >5% (can optimize)
```

---

## Debug Print Template

When something goes wrong:
```python
def debug_rocket_state(rocket):
    print(f"Time: {rocket.time:.3f}s")
    print(f"  Position: r_enu = {rocket.r_enu}")
    print(f"  Velocity: v_enu = {rocket.v_enu} (norm={np.linalg.norm(rocket.v_enu):.2f} m/s)")
    print(f"  Attitude: q = {rocket.q_enu2b} (norm={np.linalg.norm(rocket.q_enu2b):.6f})")
    print(f"  Rates: w_enu = {rocket.w_enu}")
    print(f"  Mass: {rocket.mass:.3f} kg")
    print(f"  Thrust: {rocket.thrust:.0f} N")
    print(f"  Drag: {rocket.drag:.0f} N")
    print(f"  Mach: {rocket.mach:.2f}")
    print(f"  Pitch/Yaw/Roll: {rocket.pitch:.1f}°/{rocket.yaw:.1f}°/{rocket.roll:.1f}°")
```

---

## Useful Constants

```python
import numpy as np

# Physical constants
g = 9.81                    # [m/s²]
R_earth = 6_371_000         # [m]
mu_earth = 3.986e14         # [m³/s²]
omega_earth = 7.2921e-5     # [rad/s]

# Atmospheric (at sea level)
rho_0 = 1.225               # [kg/m³]
P_0 = 101_325               # [Pa]
T_0 = 288.15                # [K]
c_sound_0 = 340             # [m/s]

# Quaternion identity
q_identity = np.array([0.0, 0.0, 0.0, 1.0])

# Typical rocket values
typical_mass = 5.0          # [kg]
typical_thrust = 5000       # [N]
typical_cd = 0.35           # [-]
typical_area = 0.05         # [m²]
```

---

## Debugging Checklist

When simulation fails:
- [ ] Did rocket start with normalized quaternion? (q_norm should be 1.0)
- [ ] Are initial r/v/m reasonable? (< 1000 km altitude, < 5 km/s velocity)
- [ ] Did you load rocket config file? (JSON parsing worked?)
- [ ] Is atmosphere model initialized? (density > 0)
- [ ] Is timestep small enough? (dt ≤ 0.01 s recommended)
- [ ] Are forces reasonable magnitude? (thrust N,drag N ≈ same order as weight)
- [ ] Did quaternion norm drift? (check every step)
- [ ] Are NaNs appearing at specific time? (log all values at that step)

---

## Further Reading

See complete analysis:
- 📄 **CODE_REVIEW.md** - Detailed technical review (80+ issues/recommendations)
- 📄 **TEST_MODELS_GUIDE.md** - How to validate with 5 test rockets
- 📄 **REVIEW_SUMMARY.md** - Priority-ordered action items

Created models for testing:
- ✅ small_model_rocket.json (1.5 kg baseline)
- ✅ medium_hpr_rocket.json (18.5 kg dual parachute)
- ✅ high_altitude_rocket.json (25 kg, Mach 1.3+)
- ✅ spin_stabilized_rocket.json (12 kg spinning)
- ✅ coasting_test_rocket.json (5 kg, minimal thrust)

---

**Remember:** The quaternion is king. Protect its norm, and most physics will work.

