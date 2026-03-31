# Parachute Module - Quick Reference Guide

## What Was Implemented

A complete parachute recovery system module for the Rocket Simulator with the following capabilities:

### ✨ Features

1. **Main Parachute Configuration**
   - Canopy diameter (0.1-5.0 meters)
   - Drag coefficient (0.5-2.5)
   - Deployment altitude threshold
   - Safe velocity constraints (min/max)
   - Inflation time simulation

2. **Drogue Chute Support**
   - Optional two-stage descent system
   - Separate diameter and drag coefficient
   - Independent deployment altitude threshold
   - Improves stability during high-speed descent

3. **Save/Load Parachute Configs**
   - Store configurations as JSON files
   - Pre-configured examples included
   - Create custom parachute types
   - Easy sharing and reuse

4. **Deployment Tracking**
   - Records exact deployment time
   - Logs deployment altitude
   - Tracks deployment velocity
   - Calculates landing speed
   - Monitors descent rate

5. **Drag Physics**
   - Realistic drag force calculation
   - Equilibrium descent rate computation
   - Inflation progress modeling
   - Multiple parachute drag combination

## Where to Find Everything

### **Parachute Settings Tab** (UI)
- Path: `ui/widgets/parachute_settings_widget.py`
- Access: Click "🪂 Parachute" tab in main window

### **Parachute Model** (Physics)
- Path: `src/models/parachute.py`
- Contains: All deployment logic and calculations

### **Configuration Files**
- Path: `data/parachutes/configs/`
- Files:
  - `standard_round.json` - Basic model rocket setup
  - `large_elliptical.json` - High-altitude with drogue
  - `drogue_dual_descent.json` - Two-stage descent
  - `high_performance_kevlar.json` - Advanced system

### **Simulation Integration**
- Main simulation: `workers/simulation_worker.py`
- Data storage: `src/utils/simulation_manager.py`
- App state: `models/app_state.py`

## How to Use

### **Quick Start**

1. Open "🪂 Parachute" tab
2. Select a preset (e.g., "standard_round")
3. Parameters auto-fill
4. Enable parachute deployment checkbox
5. Configure drogue if needed
6. Save if you want to keep the configuration
7. Run simulation

### **Create Custom Parachute**

1. In Parachute tab, set "Manual"
2. Adjust all parameters:
   - Diameter (typically 0.3-1.5 m)
   - Drag coefficient (typically 1.4-1.7)
   - Deployment altitude (triggers at this height)
   - Min velocity (won't deploy if slower)
   - Max velocity (won't deploy if faster)
3. Click "💾 Save Configuration"
4. Choose name and location
5. File saved - can load later

### **Two-Stage Descent (Drogue)**

1. Enable main parachute
2. Check "Enable Drogue Chute" box
3. Set drogue diameter (20-50% of main)
4. Set drogue deployment altitude (higher than main)
5. Drogue deploys first, main deploys lower

### **Analyze Descent**

1. Configure parachute parameters
2. Click "📊 Calculate Descent"
3. See estimated:
   - Descent rate
   - Landing speed
   - Descent time

## Key Parameters Explained

### Diameter
- Size of parachute canopy in meters
- Larger = slower descent
- Typical range: 0.3-1.5 m

### Drag Coefficient (Cd)
- Aerodynamic resistance
- 1.2-1.8 typical for parachutes
- Higher = more drag = slower descent

### Deployment Altitude
- Height at which parachute deploys
- In meters above ground level
- Safety: must be > landing elevation

### Min/Max Velocity
- Safe velocity window for deployment
- Below min: parachute may not inflate properly
- Above max: opening shock too high
- Example: 5-80 m/s for small model rockets

### Inflation Time
- Time for parachute to reach full drag
- 0.3-1.0 seconds typical
- Affects transient forces

## Simulation Results

After running a simulation with parachute, results include:

```
Parachute Deployed: Yes/No
Deployment Time: X.XX seconds
Deployment Altitude: X,XXX meters
Deployment Velocity: XX.X m/s
Max Descent Rate: X.X m/s
Landing Speed: X.X m/s
Drogue Deployed: Yes/No (if enabled)
Drogue Deployment Time: X.XX seconds
Drogue Deployment Altitude: X,XXX meters
```

## Configuration Examples

### Model Rocket (Small, <2 kg)
```
Diameter: 0.6-0.8 m
Cd: 1.5
Deployment Altitude: 300 m
Min Velocity: 5 m/s
Max Velocity: 80 m/s
Drogue: No
```

### High-Power Rocket (2-5 kg)
```
Diameter: 1.0-1.2 m
Cd: 1.5
Deployment Altitude: 400 m
Min Velocity: 10 m/s
Max Velocity: 100 m/s
Drogue: Yes (0.3 m diameter)
Drogue Deploy: 800 m
```

### High-Altitude Flight (>5 km)
```
Diameter: 1.2-1.5 m
Cd: 1.6
Deployment Altitude: 500 m
Min Velocity: 15 m/s
Max Velocity: 120 m/s
Drogue: Yes (0.35 m diameter)
Drogue Deploy: 1200 m
Material: Kevlar (ripstop_nylon)
```

## Troubleshooting

### Parachute Won't Deploy
- Check if "Enable Main Parachute Deployment" is checked
- Verify deployment altitude < max altitude reached
- Check velocity is within min/max window
- Review simulation log for deployment attempts

### Landing Speed Too High
- Reduce deployment altitude (more time to descend)
- Increase parachute diameter
- Verify drag coefficient is realistic
- Add drogue chute for two-stage system

### Unstable Descent
- Increase inflation time slightly
- Verify parameters match parachute design
- Check if drogue would help
- Review velocity at deployment

### Can't Save Configuration
- Verify `data/parachutes/configs/` directory exists
- Check write permissions
- Try saving to different location
- Ensure JSON is valid format

## Tips & Tricks

1. **Start with presets**: For first time, use provided configs
2. **Test calculations**: Click "Calculate Descent" before running
3. **Small diameter = faster descent**: Adjust for safe landing speed
4. **Use notes field**: Document why you chose specific parameters
5. **Two-stage better**: For high-speed flights, drogue helps stability
6. **Export configs**: Share parachute setups with team members
7. **Match mass**: Ensure parachute sized for actual rocket weight

## File Locations Summary

```
Project Root/
├── data/
│   └── parachutes/
│       └── configs/                    # Parachute configuration files
│           ├── standard_round.json
│           ├── large_elliptical.json
│           ├── drogue_dual_descent.json
│           └── high_performance_kevlar.json
├── src/
│   └── models/
│       └── parachute.py                # Physics model
├── ui/
│   └── widgets/
│       └── parachute_settings_widget.py # UI component
├── models/
│   └── app_state.py                    # State management
├── workers/
│   └── simulation_worker.py            # Simulation loop
├── src/utils/
│   └── simulation_manager.py           # Results storage
└── PARACHUTE_MODULE.md                 # Full documentation
```

## Next Steps

1. Try the parachute tab with different configurations
2. Run simulations with parachute enabled
3. Compare landing speeds with/without parachute
4. Create custom configurations for your rockets
5. Export and save successful configurations

---

**Need Help?** Check `PARACHUTE_MODULE.md` for detailed technical documentation.
