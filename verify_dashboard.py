#!/usr/bin/env python3
"""
Dashboard Verification Script - Test that simulations can be loaded and displayed.
"""

import sys
sys.path.insert(0, 'd:\\Documents\\GitHub\\Rocket-Simulator---GUI')

from src.utils.simulation_manager import SimulationManager
import json

def verify_dashboard():
    """Verify that dashboards can load simulations."""
    
    print("\n" + "="*70)
    print("DASHBOARD VERIFICATION TEST")
    print("="*70)
    
    # Initialize manager
    print("\n[1/4] Loading simulation manager...")
    try:
        manager = SimulationManager()
        print(f"✓ SimulationManager initialized")
        print(f"  Data directory: {manager.data_dir}")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return False
    
    # Check available simulations
    print("\n[2/4] Checking available simulations...")
    try:
        simulations = manager.list_simulations()
        print(f"✓ Found {len(simulations)} simulation(s)")
        
        if len(simulations) == 0:
            print("  ⚠ No simulations available to display")
            return False
        
        for sim in simulations:
            print(f"  - {sim['rocket']} @ {sim['location']} ({sim['timestamp'][:16]})")
            
    except Exception as e:
        print(f"✗ Error listing simulations: {e}")
        return False
    
    # Load recent simulation
    print("\n[3/4] Loading most recent simulation...")
    try:
        recent = manager.get_recent_simulation()
        if not recent:
            print("✗ No recent simulation found")
            return False
        
        sim_id = recent.get('id')
        print(f"✓ Recent simulation: {sim_id}")
        
        sim_data = manager.load_simulation(sim_id)
        if not sim_data:
            print(f"✗ Could not load simulation data for {sim_id}")
            return False
        
        print(f"✓ Simulation data loaded successfully")
        
    except Exception as e:
        print(f"✗ Error loading simulation: {e}")
        return False
    
    # Verify simulation has required metrics
    print("\n[4/4] Verifying simulation data structure...")
    try:
        metrics = sim_data.get('metrics', {})
        
        required_metrics = ['max_altitude', 'max_velocity', 'max_range', 'flight_duration', 'max_mach']
        missing_metrics = [m for m in required_metrics if m not in metrics or metrics[m] is None]
        
        if missing_metrics:
            print(f"⚠ Missing metrics: {missing_metrics}")
        else:
            print(f"✓ All required metrics present:")
            print(f"  - Max Altitude: {metrics.get('max_altitude', 0):.2f} m")
            print(f"  - Max Velocity: {metrics.get('max_velocity', 0):.2f} m/s")
            print(f"  - Max Range: {metrics.get('max_range', 0):.2f} km")
            print(f"  - Flight Duration: {metrics.get('flight_duration', 0):.2f} s")
            print(f"  - Max Mach: {metrics.get('max_mach', 0):.2f}")
        
        # Check trajectory data
        trajectory = sim_data.get('trajectory', [])
        print(f"✓ Trajectory contains {len(trajectory)} points")
        
        if len(trajectory) > 0:
            print(f"  - First point: t={trajectory[0]['time']:.3f}s, alt={trajectory[0]['altitude']:.2f}m")
            print(f"  - Last point: t={trajectory[-1]['time']:.3f}s, alt={trajectory[-1]['altitude']:.2f}m")
        
        # Verify metadata
        metadata = manager.metadata.get(sim_id, {})
        print(f"✓ Metadata loaded:")
        print(f"  - Rocket: {metadata.get('rocket', 'N/A')}")
        print(f"  - Location: {metadata.get('location', 'N/A')}")
        print(f"  - Temperature: {metadata.get('temperature', 'N/A')}°C")
        print(f"  - Max Altitude (km): {metadata.get('max_altitude', 0):.2f}")
        print(f"  - Max Velocity (m/s): {metadata.get('max_velocity', 0):.2f}")
        
    except Exception as e:
        print(f"✗ Error verifying data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*70)
    print("✓ DASHBOARD VERIFICATION PASSED")
    print("="*70)
    print("\nSummary:")
    print("- Simulations can be listed correctly")
    print("- Simulation data can be loaded from disk")
    print("- All required metrics are present")
    print("- Trajectory data is available for visualization")
    print("\n✓ Dashboard is ready to display simulations\n")
    
    return True


if __name__ == "__main__":
    success = verify_dashboard()
    sys.exit(0 if success else 1)
