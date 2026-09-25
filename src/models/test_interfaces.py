#!/usr/bin/env python3
"""
Test script to verify that all classes properly implement their interfaces.

This script checks that:
1. EnhancedEngine implements IEngine
2. EnhancedAerodynamics implements IAerodynamics
3. Parachute implements IParachute
4. Atmosphere implements IAtmosphere
"""

import sys
from abc import ABC

PASS = "[PASS]"
FAIL = "[FAIL]"

# Test imports
try:
    from src.models.interfaces import (
        IEngine, IAerodynamics, IParachute, IAtmosphere, IMassProperties
    )
    print(f"{PASS} Successfully imported all interfaces")
except ImportError as e:
    print(f"{FAIL} Failed to import interfaces: {e}")
    sys.exit(1)

# Test that interfaces are abstract
for interface_name in ['IEngine', 'IAerodynamics', 'IParachute', 'IAtmosphere']:
    interface = getattr(sys.modules['src.models.interfaces'], interface_name)
    if not issubclass(interface, ABC):
        print(f"{FAIL} {interface_name} is not an abstract base class")
        sys.exit(1)
    print(f"{PASS} {interface_name} is an abstract base class")

# Test EnhancedEngine
try:
    from src.models.engine import EnhancedEngine
    
    # Check inheritance
    if not issubclass(EnhancedEngine, IEngine):
        print(f"{FAIL} EnhancedEngine does not inherit from IEngine")
        sys.exit(1)
    print(f"{PASS} EnhancedEngine inherits from IEngine")
    
    # Check required methods exist
    required_methods = ['update', 'get_performance_metrics', 'get_thrust', 'get_mass_flow']
    for method in required_methods:
        if not hasattr(EnhancedEngine, method):
            print(f"{FAIL} EnhancedEngine missing method: {method}")
            sys.exit(1)
    print(f"{PASS} EnhancedEngine has all required methods")
    
except ImportError as e:
    print(f"{FAIL} Failed to import EnhancedEngine: {e}")
    sys.exit(1)
except Exception as e:
    print(f"{FAIL} Error testing EnhancedEngine: {e}")
    sys.exit(1)

# Test EnhancedAerodynamics
try:
    from src.models.aerodynamics import EnhancedAerodynamics
    
    # Check inheritance
    if not issubclass(EnhancedAerodynamics, IAerodynamics):
        print(f"{FAIL} EnhancedAerodynamics does not inherit from IAerodynamics")
        sys.exit(1)
    print(f"{PASS} EnhancedAerodynamics inherits from IAerodynamics")
    
    # Check required methods exist
    required_methods = [
        'update', 
        'get_coefficients', 
        'get_center_of_pressure',
        'get_stability_margin',
        'get_aerodynamic_forces'
    ]
    for method in required_methods:
        if not hasattr(EnhancedAerodynamics, method):
            print(f"{FAIL} EnhancedAerodynamics missing method: {method}")
            sys.exit(1)
    print(f"{PASS} EnhancedAerodynamics has all required methods")
    
except ImportError as e:
    print(f"{FAIL} Failed to import EnhancedAerodynamics: {e}")
    sys.exit(1)
except Exception as e:
    print(f"{FAIL} Error testing EnhancedAerodynamics: {e}")
    sys.exit(1)

# Test Parachute
try:
    from src.models.parachute import Parachute
    
    # Check inheritance
    if not issubclass(Parachute, IParachute):
        print(f"{FAIL} Parachute does not inherit from IParachute")
        sys.exit(1)
    print(f"{PASS} Parachute inherits from IParachute")
    
    # Check required methods exist
    required_methods = [
        'update',
        'get_force',
        'is_deployed',
        'get_drag_coefficient',
        'get_force_vector'
    ]
    for method in required_methods:
        if not hasattr(Parachute, method):
            print(f"{FAIL} Parachute missing method: {method}")
            sys.exit(1)
    print(f"{PASS} Parachute has all required methods")
    
except ImportError as e:
    print(f"{FAIL} Failed to import Parachute: {e}")
    sys.exit(1)
except Exception as e:
    print(f"{FAIL} Error testing Parachute: {e}")
    sys.exit(1)

# Test Atmosphere
try:
    from src.models.atmosphere import Atmosphere
    
    # Check inheritance
    if not issubclass(Atmosphere, IAtmosphere):
        print(f"{FAIL} Atmosphere does not inherit from IAtmosphere")
        sys.exit(1)
    print(f"{PASS} Atmosphere inherits from IAtmosphere")
    
    # Check required methods exist
    required_methods = [
        'give_dens',
        'give_temp',
        'give_v_sonic',
        'give_pressure'
    ]
    for method in required_methods:
        if not hasattr(Atmosphere, method):
            print(f"{FAIL} Atmosphere missing method: {method}")
            sys.exit(1)
    print(f"{PASS} Atmosphere has all required methods")
    
except ImportError as e:
    print(f"{FAIL} Failed to import Atmosphere: {e}")
    sys.exit(1)
except Exception as e:
    print(f"{FAIL} Error testing Atmosphere: {e}")
    sys.exit(1)

print("\n" + "="*60)
print(f"{PASS} All interface implementation tests passed!")
print("="*60)
print("\nPhase 1 (Interfaces) is complete.")
print("All classes now implement their respective interfaces.")
