"""Comprehensive Rocket Configuration Quality Validation"""

import json
import os
from pathlib import Path

def validate_rocket(filename, filepath):
    """Validate a single rocket configuration"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        return {
            'file': filename,
            'status': 'ERROR',
            'issues': [f"Cannot parse JSON: {e}"]
        }
    
    issues = []
    warnings = []
    
    # Check required fields
    required_fields = ['initial_mass', 'propellant_mass', 'reference_area', 'I_before_burn', 
                       'CoM_before_burn', 'engine', 'geometry', 'fins', 'nosecone']
    
    for field in required_fields:
        if field not in config:
            # Handle alternative names
            if field == 'initial_mass' and 'total_mass_initial' in config:
                config['initial_mass'] = config['total_mass_initial']
            elif field not in config:
                issues.append(f"Missing required field: {field}")
    
    # Mass validation
    try:
        initial_mass = config.get('initial_mass') or config.get('total_mass_initial', 0)
        propellant_mass = config.get('propellant_mass', 0)
        
        if initial_mass <= 0:
            issues.append(f"Invalid initial_mass: {initial_mass}")
        if propellant_mass < 0:
            issues.append(f"Negative propellant_mass: {propellant_mass}")
        if propellant_mass > initial_mass:
            issues.append(f"Propellant mass ({propellant_mass}) exceeds total mass ({initial_mass})")
        
        dry_mass = initial_mass - propellant_mass
        if dry_mass <= 0:
            issues.append(f"Invalid dry_mass: {dry_mass} kg (initial={initial_mass}, prop={propellant_mass})")
    except:
        issues.append("Cannot validate mass values")
    
    # Engine validation
    try:
        engine = config.get('engine', {})
        burn_time = engine.get('burn_time', 0)
        mass_flux = engine.get('mass_flux', 0)
        
        if burn_time > 0 and propellant_mass > 0:
            expected_flux = propellant_mass / burn_time
            if mass_flux > 0:
                flux_error = abs(mass_flux - expected_flux) / expected_flux * 100
                if flux_error > 5:
                    warnings.append(f"mass_flux inconsistency: expected {expected_flux:.3f}, got {mass_flux:.3f} ({flux_error:.1f}% error)")
            else:
                mass_flux_calc = expected_flux
                if NOT mass_flux:
                    warnings.append(f"mass_flux missing, calculated: {mass_flux_calc:.3f} kg/s")
        
        thrust_to_weight = engine.get('thrust_to_weight_ratio', 0)
        if thrust_to_weight > 0 and (thrust_to_weight < 2 or thrust_to_weight > 100):
            warnings.append(f"Unusual thrust-to-weight ratio: {thrust_to_weight}")
    except:
        issues.append("Cannot validate engine configuration")
    
    # Geometry validation
    try:
        geometry = config.get('geometry', {})
        
        # Check for legacy field name with space
        if 'length nosecone fins' in geometry:
            length_nc_fins = geometry['length nosecone fins']
        else:
            length_nc_fins = geometry.get('length_nosecone_fins', geometry.get('total_length', 0))
        
        if length_nc_fins == 0:
            issues.append("Geometry 'length_nosecone_fins' is 0 (causes simulator error)")
        elif length_nc_fins < 0:
            issues.append(f"Invalid geometry value: length_nosecone_fins = {length_nc_fins}")
    except:
        issues.append("Cannot validate geometry")
    
    # Inertia validation
    try:
        inertia_before = config.get('I_before_burn', {})
        for label, inertia_dict in [('I_before_burn', inertia_before)]:
            ix = inertia_dict.get('x', 0)
            iy = inertia_dict.get('y', 0)
            iz = inertia_dict.get('z', 0)
            
            # Check for zero values
            if ix == 0 or iz == 0:
                warnings.append(f"{label}: Ixx or Izz = 0 (suggests singular matrix)")
            
            # Check triangle inequality
            sorted_I = sorted([ix, iy, iz])
            if sorted_I[2] > sorted_I[0] + sorted_I[1]:
                warnings.append(f"{label}: Inertia triangle inequality violated (may be physically unrealistic)")
    except:
        issues.append("Cannot validate inertia")
    
    return {
        'file': filename,
        'status': 'GOOD' if not issues else 'ISSUES',
        'issues': issues,
        'warnings': warnings,
        'config': config
    }


def main():
    configs_dir = Path("d:\\Documents\\GitHub\\Rocket-Simulator---GUI\\data\\rockets\\configs")
    
    results = []
    for config_file in sorted(configs_dir.glob("*.json")):
        result = validate_rocket(config_file.name, config_file)
        results.append(result)
        
        status_icon = '✓' if result['status'] == 'GOOD' else '✗' if result['status'] == 'ERROR' else '⚠'
        print(f"{status_icon} {result['file']:<35} {result['status']}")
        
        if result['issues']:
            for issue in result['issues']:
                print(f"    ISSUE: {issue}")
        
        if result['warnings']:
            for warning in result['warnings']:
                print(f"    WARNING: {warning}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    good = len([r for r in results if r['status'] == 'GOOD'])
    warn = len([r for r in results if r['status'] == 'ISSUES'])
    error = len([r for r in results if r['status'] == 'ERROR'])
    
    print(f"✓ Good:    {good}")
    print(f"⚠ Issues:  {warn}")
    print(f"✗ Errors:  {error}")
    print(f"Total:   {len(results)}")
    
    print("\n" + "="*80)
    print("QUALITY ASSESSMENT")
    print("="*80)
    
    quality_level = "EXCELLENT" if error == 0 and warn <= 2 else "GOOD" if error == 0 else "NEEDS FIXES"
    print(f"Overall Quality: {quality_level}")
    
    if quality_level == "EXCELLENT":
        print("All rocket configurations are in good shape for simulation!")
    elif quality_level == "GOOD":
        print("Most rockets are ready for use. Review warnings above.")
    else:
        print("Some rockets have issues that may prevent simulation. Review errors above.")


if __name__ == '__main__':
    main()
