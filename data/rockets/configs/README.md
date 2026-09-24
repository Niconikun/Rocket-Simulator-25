# Rocket Configuration Presets

This directory contains pre-configured rocket configuration files in JSON format for use with the Rocket Simulator Pro application.

## Available Presets

### 1. **Agni-1**
- **Category**: Tactical Ballistic Missile / ICBM Class
- **Description**: Large tactical ballistic missile with solid rocket motor propulsion
- **Initial Mass**: 12,000 kg
- **Propellant Mass**: 9,342 kg
- **Total Length**: 14.701 m
- **Diameter**: 1.0 m
- **Engine**: Solid Rocket Motor
- **Burn Time**: 49.0 seconds
- **Mean Thrust**: 454,930.5 N
- **Max Thrust**: 454,930.5 N
- **Specific Impulse**: 232.0 s
- **Thrust-to-Weight Ratio**: 3.9
- **Expected Apogee**: 450,000 m
- **Expected Max Velocity**: 2,100 m/s
- **Use Case**: Large scale ICBM trajectory and performance metrics validation

### 2. **Campanil 1-A**
- **Category**: High Power Rocket
- **Description**: Small high-power rocket with parabolic nosecone
- **Initial Mass**: 7.8 kg
- **Propellant Mass**: 1.5 kg
- **Total Length**: 1.19 m
- **Diameter**: 0.103 m
- **Engine**: Custom solid motor
- **Burn Time**: 2.79 seconds
- **Mean Thrust**: 544.36 N
- **Max Thrust**: 2,104.115 N
- **Specific Impulse**: 106.25 s
- **Thrust-to-Weight Ratio**: 11.2
- **Use Case**: Small high-power rocket with standard thrust curve

### 3. **Campanil 1-A Experimental**
- **Category**: High Power Rocket
- **Description**: Campanil 1-A variant with experimental thrust curve from load cell data
- **Initial Mass**: 7.8 kg
- **Propellant Mass**: 1.5 kg
- **Total Length**: 1.169 m
- **Diameter**: 0.103 m
- **Engine**: Custom solid motor
- **Burn Time**: 2.79 seconds
- **Mean Thrust**: 544.36 N
- **Max Thrust**: 2,104.115 N
- **Specific Impulse**: 106.25 s
- **Thrust Curve**: Experimental (uses data/thrust_curves/load_cell_1.csv)
- **Thrust Curve Unit**: kgf
- **Thrust-to-Weight Ratio**: 11.2
- **Use Case**: Experimental thrust curve validation with load cell data

### 4. **Coasting Test Rocket**
- **Category**: Test Configuration
- **Description**: Low-thrust configuration to test coasting phase and ballistic descent dynamics
- **Initial Mass**: 5.0 kg
- **Propellant Mass**: 0.10 kg
- **Total Length**: 0.80 m
- **Diameter**: 0.065 m
- **Engine**: Very Low Thrust
- **Burn Time**: 2.0 seconds
- **Mean Thrust**: 8.0 N
- **Max Thrust**: 10.0 N
- **Specific Impulse**: 150 s
- **Thrust-to-Weight Ratio**: 0.2
- **Expected Apogee**: 850 m
- **Expected Max Velocity**: 40 m/s
- **Coasting Phase Duration**: 3.0 seconds
- **Use Case**: Verify coasting phase dynamics without strong propulsive forces

### 5. **High Altitude Rocket**
- **Category**: High Altitude
- **Description**: High-performance rocket (J-class motor) designed for high-altitude flight from elevated launch site
- **Initial Mass**: 25.0 kg
- **Propellant Mass**: 8.5 kg
- **Total Length**: 2.65 m
- **Diameter**: 0.127 m (5-inch)
- **Engine**: J-Series
- **Burn Time**: 12.5 seconds
- **Mean Thrust**: 6,900 N
- **Max Thrust**: 9,200 N
- **Specific Impulse**: 510 s
- **Thrust Curve**: Experimental (uses data/thrust_curves/J570_thrust_curve.csv)
- **Thrust-to-Weight Ratio**: 36.8
- **Expected Apogee**: 28,500 m
- **Expected Max Velocity**: 385 m/s
- **Launch Site Altitude**: 3,600 m
- **Use Case**: Validate high-altitude performance with thin atmosphere and experimental thrust curve

### 6. **Medium HPR Rocket**
- **Category**: High Power Rocket
- **Description**: Medium high-power rocket (I-class motor) for mid-altitude demonstrations with parachute deployment
- **Initial Mass**: 18.5 kg
- **Propellant Mass**: 6.0 kg
- **Total Length**: 2.15 m
- **Diameter**: 0.1 m (4-inch)
- **Engine**: I-Series
- **Burn Time**: 10.5 seconds
- **Mean Thrust**: 5,600 N
- **Max Thrust**: 7,200 N
- **Specific Impulse**: 455 s
- **Thrust-to-Weight Ratio**: 38.6
- **Expected Apogee**: 15,200 m
- **Expected Max Velocity**: 265 m/s
- **Use Case**: Validate multi-stage parachute deployment and mid-altitude performance

### 7. **Rayo**
- **Category**: Sounding Rocket
- **Description**: Rayo sounding rocket - tactical class vehicle with solid motor propulsion
- **Initial Mass**: 9.48 kg
- **Propellant Mass**: 3.33 kg
- **Total Length**: 0.936 m
- **Diameter**: 0.0889 m
- **Engine**: Solid Rocket Motor
- **Burn Time**: 3.15 seconds
- **Mean Thrust**: 2,432 N
- **Max Thrust**: 2,918 N
- **Specific Impulse**: 223 s
- **Thrust-to-Weight Ratio**: 26.1
- **Use Case**: Sounding rocket for tactical applications

### 8. **Small Model Rocket**
- **Category**: Model Rocket
- **Description**: Educational small model rocket (F-class) for basic physics validation
- **Initial Mass**: 1.5 kg
- **Propellant Mass**: 0.35 kg
- **Total Length**: 0.45 m
- **Diameter**: 0.076 m (3-inch)
- **Engine**: F-Series
- **Burn Time**: 3.5 seconds
- **Mean Thrust**: 100 N
- **Max Thrust**: 140 N
- **Specific Impulse**: 260 s
- **Thrust-to-Weight Ratio**: 9.3
- **Expected Apogee**: 2,800 m
- **Expected Max Velocity**: 85 m/s
- **Use Case**: Verify basic 6-DOF dynamics and stability calculations

### 9. **Spin Stabilized Rocket**
- **Category**: Spin Stabilized
- **Description**: Spin-stabilized rocket with helical fins for attitude control validation via gyroscopic stabilization
- **Initial Mass**: 12.0 kg
- **Propellant Mass**: 3.5 kg
- **Total Length**: 1.50 m
- **Diameter**: 0.0825 m (3.25-inch)
- **Engine**: H-Series
- **Burn Time**: 8.0 seconds
- **Mean Thrust**: 1,800 N
- **Max Thrust**: 2,400 N
- **Specific Impulse**: 420 s
- **Thrust-to-Weight Ratio**: 20.0
- **Fin Type**: Helical (with 15° twist angle)
- **Initial Spin Rate**: 250 RPM (26.18 rad/s)
- **Expected Apogee**: 7,500 m
- **Expected Max Velocity**: 155 m/s
- **Spin Stability Margin**: 2.5
- **Use Case**: Validate gyroscopic stabilization from helical fins and initial spin rate

### 10. **Test Rocket**
- **Category**: Test Configuration
- **Description**: Large test rocket with heavy payload capability
- **Initial Mass**: 80.0 kg
- **Propellant Mass**: 30.0 kg
- **Total Length**: 3.15 m
- **Diameter**: 0.15 m
- **Engine**: High-thrust custom motor
- **Burn Time**: 10.0 seconds
- **Mean Thrust**: 24,000 N
- **Max Thrust**: 28,800 N
- **Specific Impulse**: 816 s
- **Thrust-to-Weight Ratio**: 30.6
- **Use Case**: General testing and validation

## File Format

Each rocket configuration is stored as a JSON file with the following structure:

```json
{
    "name": "Rocket name",
    "description": "Brief description",
    "category": "rocket category",
    "initial_mass": 0.0,
    "propellant_mass": 0.0,
    "dry_mass_kg": 0.0,
    "reference_area": 0.0,
    "I_before_burn": {"x": 0.0, "y": 0.0, "z": 0.0},
    "CoM_before_burn": {"x": 0.0, "y": 0.0, "z": 0.0},
    "I_after_burn": {"x": 0.0, "y": 0.0, "z": 0.0},
    "CoM_after_burn": {"x": 0.0, "y": 0.0, "z": 0.0},
    "engine": {...},
    "geometry": {...},
    "nosecone": {...},
    "fuselage": {...},
    "fins": {...},
    "rear_section": {...},
    "parachute": {...},
    "validation": {...}
}
```

## Adding Custom Presets

To add a custom rocket configuration:
1. Create a new JSON file in this directory
2. Follow the structure of existing presets
3. Ensure all units are in SI (meters, kilograms, seconds, etc.)
4. Restart the application to see the new preset in the dropdown menu

## Notes

- All geometry dimensions are in **meters**
- All masses are in **kilograms**
- All time values are in **seconds**
- Reference area is in **square meters**
- Moments of inertia are in **kg·m²**
- Center of mass positions are in **meters** from the nose tip
- Thrust values are in **Newtons** (unless otherwise specified in thrust_curve_unit)

## STL and OpenRocket Import

The Rocket Simulator Pro supports importing rocket configurations from:
- **OpenRocket (.ork files)**: Geometry and basic properties
- **STL files**: Reference area and inertia calculations (requires trimesh package)

These can be imported through the Rocket Settings widget using the import buttons.
