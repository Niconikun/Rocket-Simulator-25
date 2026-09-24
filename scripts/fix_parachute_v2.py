#!/usr/bin/env python3
"""Fix parachute.py to use constants from simulation_constants - version 2."""

from pathlib import Path

PARACHUTE_PY = Path("D:/Documents/GitHub/Rocket-Simulator---GUI/src/models/parachute.py")

with open(PARACHUTE_PY, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Track if we've added the import
import_added = False

# Process each line
new_lines = []
for i, line in enumerate(lines):
    # Add import after logger line
    if not import_added and line.strip() == 'logger = logging.getLogger(__name__)':
        new_lines.append(line)
        new_lines.append('from src.utils.simulation_constants import ParachuteConstants as PC\n')
        new_lines.append('\n')
        import_added = True
        continue
    
    # Replace config.get() defaults with constants
    # We need to be specific about the context
    if not import_added:
        new_lines.append(line)
        continue
    
    # Replace in __init__ method
    if "self.name = config.get('name'" in line:
        line = line.replace("'Main Parachute'", "PC.DEFAULT_NAME")
    elif "self.diameter = config.get('diameter'" in line:
        line = line.replace("1.0)", "PC.DEFAULT_DIAMETER)")
    elif "self.Cd = config.get('Cd'" in line and "drogue" not in line:
        line = line.replace("1.5)", "PC.DEFAULT_CD)")
    elif "self.material = config.get('material'" in line:
        line = line.replace("'ripstop_nylon'", "PC.DEFAULT_MATERIAL")
    elif "self.inflation_time = config.get('inflation_time'" in line:
        line = line.replace("0.5)", "PC.DEFAULT_INFLATION_TIME)")
    elif "self.deployment_altitude = config.get('deployment_altitude'" in line:
        line = line.replace("300.0)", "PC.DEFAULT_DEPLOYMENT_ALTITUDE)")
    elif "self.min_velocity = config.get('min_velocity'" in line:
        line = line.replace("5.0)", "PC.DEFAULT_MIN_VELOCITY)")
    elif "self.max_velocity = config.get('max_velocity'" in line:
        line = line.replace("100.0)", "PC.DEFAULT_MAX_VELOCITY)")
    elif "self.drogue_diameter = config.get('drogue_diameter'" in line:
        line = line.replace("0.3)", "PC.DEFAULT_DROGUE_DIAMETER)")
    elif "self.drogue_Cd = config.get('drogue_Cd'" in line:
        line = line.replace("1.5)", "PC.DEFAULT_DROGUE_CD)")
    elif "self.drogue_deployment_altitude = config.get('drogue_deployment_altitude'" in line:
        line = line.replace("600.0)", "PC.DEFAULT_DROGUE_DEPLOYMENT_ALTITUDE)")
    elif "self.drogue_inflation_time = config.get('drogue_inflation_time'" in line:
        line = line.replace("0.2)", "PC.DEFAULT_DROGUE_INFLATION_TIME)")
    elif "g: float = 9.81" in line:
        line = line.replace("9.81", "PC.STANDARD_GRAVITY")
    
    new_lines.append(line)

# Write back
with open(PARACHUTE_PY, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"[OK] Updated parachute.py with ParachuteConstants")
