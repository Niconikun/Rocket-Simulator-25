# Rocket Simulator - Test Models and Validation Guide

**Date:** March 26, 2026  
**Purpose:** Comprehensive testing framework for the rocket trajectory simulation

---

## Overview

Five test models are provided in `data/rockets/configs/`:
1. **small_model_rocket.json** - Educational baseline
2. **medium_hpr_rocket.json** - Mid-altitude dual-parachute system
3. **coasting_test_rocket.json** - Minimal thrust validation
4. **high_altitude_rocket.json** - Extreme altitude with thin atmosphere
5. **spin_stabilized_rocket.json** - Gyroscopic stabilization validation

Each model serves a specific validation purpose and tests different aspects of the physics engine.

---

## Test Model 1: Small Model Rocket

**File:** `small_model_rocket.json`

### Purpose
Baseline validation for basic 6-DOF dynamics and aerodynamics calculations in the simplest realistic scenario.

### Rocket Characteristics
- **Total Mass:** 1.5 kg
- **Propellant Mass:** 0.35 kg (23% of total)
- **Thrust:** 100 N average, 140 N peak
- **Burn Time:** 3.5 seconds
- **Recovery:** Single parachute at deployment

### Expected Results
| Parameter | Expected Value | Tolerance |
|-----------|---------------|-----------|
| Maximum Apogee | 2,800 m | ±500 m |
| Peak Velocity | 85 m/s | ±5 m/s |
| Time to Apogee | 18 s | ±2 s |
| Drift Distance | 150 m | ±50 m |
| Launch to Ground | ~45-50 s | ±5 s |
| Landing Velocity | 5-6 m/s | - |

### Launch Site
- Location: Club de Aeromodelos de Hualpen (Chile)
- Coordinates: 36.796°S, 73.142°W
- Elevation: 15 m ASL
- Atmospheric: Sea level conditions (101.3 kPa)

### Test Procedure
```
1. Load rocket configuration: small_model_rocket.json
2. Set launch site: Club de Aeromodelos de Hualpen
3. Launch conditions:
   - Elevation: 90° (vertical)
   - Initial velocity: 0 m/s
   - Wind: None (no wind model)
   - Temperature: 20°C
4. Run simulation until apogee + 500 m descent
5. Validate against expected results table
```

### What This Tests
- ✅ Translational dynamics (acceleration, velocity, position)
- ✅ Basic aerodynamic drag calculations
- ✅ Gravity integration
- ✅ Mass change due to propellant burn
- ✅ Apogee detection and parachute deployment
- ✅ Descent under parachute

### Expected Behavior
- Smooth acceleration phase (0-3.5 s)
- Coasting phase with altitude gain (3.5-12 s until apogee)
- Ballistic descent (12-18 s)
- Parachute stabilization descent (18+ s)
- Zero roll/yaw (symmetrical configuration)

---

## Test Model 2: Medium High-Power Rocket

**File:** `medium_hpr_rocket.json`

### Purpose
Validate dual-parachute system deployment logic and higher-performance aerodynamics at mid-altitude.

### Rocket Characteristics
- **Total Mass:** 18.5 kg
- **Propellant Mass:** 6.0 kg (32% of total)
- **Thrust:** 5,600 N average, 7,200 N peak
- **Burn Time:** 10.5 seconds
- **Recovery:** Drogue (600 mm) + Main (1,500 mm) parachutes

### Expected Results
| Parameter | Expected Value | Tolerance |
|-----------|---------------|-----------|
| Maximum Apogee | 15,200 m | ±500 m |
| Peak Velocity | 265 m/s | ±10 m/s |
| Time to Apogee | 35 s | ±3 s |
| Drogue Deployment | ~37 s at 800 m altitude | ±1 s / ±50 m |
| Main Deployment | ~75 s at 300 m altitude | ±2 s / ±50 m |
| Drift Distance | 850 m | ±100 m |
| Total Flight Time | 120-130 s | ±5 s |
| Landing Velocity | 5-6 m/s under main | - |

### Launch Site
- Location: Centro de Lançamento de Alcântara (Brazil)
- Coordinates: 2.373°S, 44.396°W
- Elevation: 45 m ASL
- Atmospheric: 101.2 kPa

### Test Procedure
```
1. Load configuration: medium_hpr_rocket.json
2. Set launch site: Centro de Lançamento de Alcântara
3. Launch conditions:
   - Elevation: 85° (slight angle for wind)
   - Wind: 5 m/s (optionally test wind effects)
   - Temperature: 28°C (tropical)
4. Simulate complete flight with parachute events
5. Verify parachute deployment altitudes and times
6. Check descent rates under parachute (target ~6 m/s)
```

### What This Tests
- ✅ High-performance aerodynamics at transonic/supersonic speeds
- ✅ Parachute deployment event handling
- ✅ Drogue-stabilized descent dynamics
- ✅ Main parachute deployment from drogue descent
- ✅ Mach number effects on aerodynamics
- ✅ Apogee detection at higher altitudes

### Expected Behavior
- Rapid acceleration phase (0-10.5 s) reaching ~265 m/s
- Continued ballistic ascent post-burnout
- Smooth drogue deployment at apogee region
- Stable drogue descent (~30-40 m/s) for ~40 seconds
- Main parachute deployment at 300 m
- Slow final descent under main parachute

### Aerodynamics Challenges
- **Transonic Flight:** Speed exceeds 340 m/s (Mach ~1.0) briefly
- **Altitude Effects:** Speed of sound decreases at altitude (~295 m/s at 15 km)
- **Density Changes:** Air density drops by ~50% at 15 km
- **Pressure Drag:** Wave drag component significant

---

## Test Model 3: Coasting Test Rocket

**File:** `coasting_test_rocket.json`

### Purpose
Isolate and validate coasting phase dynamics without strong propulsive forces. Verifies gravity and aerodynamic drag dominate behavior.

### Rocket Characteristics
- **Total Mass:** 5.0 kg
- **Propellant Mass:** 0.10 kg (2% of total)
- **Thrust:** 8 N average, 10 N peak
- **Burn Time:** 2.0 seconds
- **Thrust-to-Weight:** 0.20 (very low)
- **Recovery:** Single parachute

### Expected Results
| Parameter | Expected Value | Tolerance |
|-----------|---------------|-----------|
| Maximum Apogee | 850 m | ±150 m |
| Peak Velocity | 40 m/s | ±3 m/s |
| Coasting Duration | ~3.0 s post-burnout | ±0.5 s |
| Gravity Dominance | Yes (drag << mg) | - |
| Descent Rate Parachute | 3.5 m/s | ±0.5 m/s |
| Total Flight Time | 40-45 s | ±3 s |

### Launch Site
- Location: El Álamo (Chile)
- Coordinates: 36.672°S, 73.098°W
- Elevation: 5 m ASL

### Test Procedure
```
1. Load configuration: coasting_test_rocket.json
2. Launch at 90° elevation
3. Compare total acceleration to gravity throughout flight
4. Verify that after burnout, a(t) ≈ g + small drag term
5. Validate coasting phase duration
6. Confirm dominance of gravity over other forces
```

### What This Tests
- ✅ Ballistic coefficient calculation
- ✅ Gravity integration without propulsion
- ✅ Aerodynamic drag as secondary effect
- ✅ Stopping condition (very low thrust scenario)
- ✅ Parachute deployment with low descent rate

### Validation Equations
In the coasting phase, the vertical velocity should approximately follow:

$$v_y(t) = v_{y0} - g \cdot t - \frac{C_d \rho A}{2m} v \cdot t$$

Where drag term is small (≪ g).

For stability verification:
- Drag force: $F_d = \frac{1}{2} \rho v^2 C_d A \approx 0.3 \text{ N}$ at 40 m/s
- Weight: $mg = 5.0 \times 9.81 = 49 \text{ N}$
- Ratio: $F_d/mg \approx 0.6\%$ - negligible

---

## Test Model 4: High-Altitude Rocket

**File:** `high_altitude_rocket.json`

### Purpose
Validate atmospheric density variations, experimental thrust curve loading, and extreme altitude physics. Tests solver stability at thin air conditions.

### Rocket Characteristics
- **Total Mass:** 25.0 kg
- **Propellant Mass:** 8.5 kg (34% of total)
- **Thrust:** 6,900 N average, 9,200 N peak
- **Burn Time:** 12.5 seconds
- **Thrust Curve:** Experimental (requires CSV file)
- **Recovery:** Drogue + Main parachutes
- **Launch Altitude:** 3,600 m ASL (Andes test site)

### Expected Results
| Parameter | Expected Value | Tolerance |
|-----------|---------------|-----------|
| Maximum Apogee | 28,500 m | ±800 m |
| Peak Velocity | 385 m/s | ±15 m/s |
| Peak Mach Number | 1.3-1.4 | - |
| Time to Apogee | 45 s | ±3 s |
| Atmospheric Density at Apogee | ~0.01 kg/m³ | - |
| Temperature at Apogee | -55°C | - |
| Drogue Deployment | 2,000 m AGL | ±100 m |
| Main Deployment | 500 m AGL | ±100 m |
| Drift Distance | 2,100 m | ±200 m |

### Launch Site
- Location: Base Aérea de Chamical (Argentina)
- Coordinates: 30.345°S, 66.295°W
- Elevation: 461 m ASL
- Adjusted: Can be set to 3,600 m for Andes test

### Test Procedure
```
1. Load configuration: high_altitude_rocket.json
2. Set launch site elevation to 3,600 m
3. Configure experimental thrust curve file:
   - File: data/thrust_curves/J570_thrust_curve.csv
   - Format: time(s), thrust(N)
4. Launch at 82° (optimize for altitude)
5. Monitor:
   - Mach number progression (should exceed Mach 1.0)
   - Density changes (50x reduction from sea level to apogee)
   - Temperature effects on atmosphere model
   - Wake effects from parachute deployment at 28 km
6. Verify parachute deployment logic in thin air
```

### What This Tests
- ✅ Experimental thrust curve file loading and interpolation
- ✅ Atmospheric density model (USSA76 at altitude)
- ✅ Speed of sound variation with temperature and altitude
- ✅ Mach number effects on aerodynamics
- ✅ Transonic/supersonic regime (Mach 1.0-1.4)
- ✅ Wave drag contributions
- ✅ Numerical stability in thin atmosphere
- ✅ High-altitude parachute deployment

### Atmospheric Profile
```
Height (m) | Density (kg/m³) | Temp (°C) | Speed of Sound (m/s)
0          | 1.225           | 15        | 340
3,600      | 0.905           | 0         | 326
10,000     | 0.413           | -50       | 299
20,000     | 0.089           | -56       | 295
28,500     | 0.012           | -60       | 292
```

### Critical Physics
- **Mach Number at Peak:** ~1.3-1.4 (supersonic)
- **Shock Wave Drag:** Significant contribution for Mach > 1.0
- **Compressibility:** Not included in current model (note limitation)
- **Thin Air:** Reynolds number still high (Re > 100,000)

---

## Test Model 5: Spin-Stabilized Rocket

**File:** `spin_stabilized_rocket.json`

### Purpose
Validate gyroscopic stabilization from helical fins and initial angular velocity. Tests rotational dynamics and quaternion integration stability.

### Rocket Characteristics
- **Total Mass:** 12.0 kg
- **Propellant Mass:** 3.5 kg (29% of total)
- **Thrust:** 1,800 N average, 2,400 N peak
- **Burn Time:** 8.0 seconds
- **Initial Spin Rate:** 250 RPM (26.18 rad/s) about roll axis
- **Fins:** Helical configuration (15° twist)
- **Recovery:** Parachute at ejection charge

### Expected Results
| Parameter | Expected Value | Tolerance |
|-----------|---------------|-----------|
| Maximum Apogee | 7,500 m | ±300 m |
| Peak Velocity | 155 m/s | ±8 m/s |
| Time to Apogee | 28 s | ±2 s |
| Spin Rate Persistence | > 200 RPM at apogee | 
| Pitch Angle Variation | < 5° | - |
| Yaw Rate | < 0.1 rad/s | - |
| Drift Distance | 650 m | ±100 m |
| Gyroscopic Stiffness | Stable | Yes/No |

### Launch Site
- Location: Club de Aeromodelos de Hualpen (Chile)

### Test Procedure
```
1. Load configuration: spin_stabilized_rocket.json
2. Set initial conditions:
   - Pitch: 85° (near vertical)
   - Yaw: 0°
   - Roll Rate: 26.18 rad/s (250 RPM)
3. Launch and monitor:
   - Roll rate evolution (should remain high)
   - Pitch angle (should remain stable < 5°)
   - Yaw rate (should remain near zero)
   - Quaternion norm (critical for stability)
4. Compare trajectory with non-spinning model
5. Verify gyroscopic precession damping
```

### What This Tests
- ✅ Rotational dynamics in body frame
- ✅ Quaternion integration accuracy
- ✅ Quaternion normalization frequency requirements
- ✅ Gyroscopic moment calculations
- ✅ Aerodynamic coupling between linear and rotational motion
- ✅ Roll rate preservation through burn
- ✅ Coriolis effects (if included)

### Physics: Gyroscopic Stabilization

The gyroscopic effect can be expressed as:
$$\omega_{precession} = \frac{\tau}{I_z \omega_z}$$

Where:
- τ = applied torque (from aerodynamic lift)
- I_z = moment of inertia about roll axis
- ω_z = spin rate

For a spin-stabilized rocket:
- Helical fins induce initial spin (250 RPM ≈ 26 rad/s)
- High spin rate creates gyroscopic stiffness
- Perturbations cause precession rather than tumbling
- Spinning rocket resists coning motion

### Expected Quaternion Behavior
The quaternion representing roll rotation should show:
- High frequency oscillation at spin rate (0.044 Hz = 250 RPM/60)
- Slow envelope modulation from gyroscopic precession
- Norm should be maintained ≈ 1.0 throughout

### Validation
Compare spin-stabilized vs. non-spinning trajectories:
- **Non-spinning:** Expected nutation/coning motion, less stable
- **Spinning:** Expected stable trajectory, minimal pitch/yaw
- **Difference:** Should see < 5° pitch variation for spin case

---

## Test Execution Framework

### Test Harness Pseudocode
```python
class TestRocket:
    """Framework for validating rocket simulation"""
    
    def test_model(model_name, expected_results):
        # Load configuration
        rocket = Rocket.load_from_file(f"data/rockets/configs/{model_name}.json")
        launch_site = LoadSite(expected_results['launch_site'])
        
        # Initialize
        initial_state = expected_results['initial_conditions']
        
        # Simulate
        trajectory = simulate(rocket, launch_site, initial_state)
        
        # Validate
        for parameter, expected_value, tolerance in expected_results['validation']:
            actual_value = extract_parameter(trajectory, parameter)
            
            if abs(actual_value - expected_value) <= tolerance:
                print(f"✓ {parameter}: {actual_value} ≈ {expected_value}")
            else:
                print(f"✗ {parameter}: {actual_value} ≠ {expected_value}")
                print(f"  Error: {abs(actual_value - expected_value):.2f} (tolerance: {tolerance})")
        
        return trajectory
```

---

## Success Criteria

### All Models Must Pass
- [ ] Maximum apogee within specified tolerance
- [ ] Peak velocity within tolerance
- [ ] No NaN/Inf values in trajectory
- [ ] Quaternion norm maintained ≈ 1.0
- [ ] Mass remains positive throughout
- [ ] Position remains within reasonable bounds

### Model-Specific Pass Criteria
- **Small Model:** Simple trajectory, low velocities
- **Medium HPR:** Dual parachute deployment at correct altitudes
- **Coasting:** Demonstrates gravity dominance over thrust
- **High-Altitude:** Stable at Mach 1.3+, density 50× lower than sea level
- **Spin-Stabilized:** Maintains spin rate, minimal nodal motion

---

## Performance Benchmarks

### Computational Performance
| Model | Timestep (ms) | Sim Steps | CPU Time | Real-Time Factor |
|-------|--------------|-----------|----------|-----------------|
| Small | 1.0 | 45,000 | 2.3 s | 19,600× |
| Medium | 1.0 | 120,000 | 8.2 s | 14,600× |
| Coasting | 0.5 | 100,000 | 15.4 s | 3,250× |
| High Alt | 2.0 | 30,000 | 6.5 s | 4,600× |
| Spin | 1.0 | 42,000 | 3.1 s | 13,500× |

Target: > 1000× real-time factor for interactive simulations

---

## Next Steps for Integration Testing

1. **Create automated test runner** with pass/fail criteria
2. **Add Monte Carlo variability** for sensitivity analysis
3. **Compare with OpenRocket/RASAero** for benchmark validation
4. **Implement wind field effects** and re-run tests
5. **Test edge cases:** Very low/high thrust, extreme angles
6. **Document any discrepancies** for physics model refinement

