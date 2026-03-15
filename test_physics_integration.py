#!/usr/bin/env python
"""
Quick test to verify physics engine integration with SimulationWorker.

This script tests that:
1. SimulationWorker can be instantiated
2. Physics models load correctly
3. Rocket configuration loads
4. Simulation runs without crashing
"""

import sys
import logging
from datetime import date, time
from models.app_state import ApplicationState
from workers.simulation_worker import SimulationWorker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_physics_worker():
    """Test the physics-integrated simulation worker."""
    
    print("\n" + "="*60)
    print("Testing Physics Engine Integration")
    print("="*60 + "\n")
    
    # Initialize application state
    logger.info("1. Initializing ApplicationState...")
    state = ApplicationState.get_instance()
    
    # Set required simulation parameters
    logger.info("2. Configuring simulation parameters...")
    state.set('sim_runtime', 10)  # 10 seconds (short test)
    state.set('sim_time_step', 0.01)  # 0.01 second timestep
    state.set('selected_rocket', 'agni-1')
    state.set('sim_location', 'Test-Site')
    state.set('sim_date', date(2026, 3, 15))
    state.set('sim_time', time(12, 0, 0))
    state.set('average_temperature', 20.0)
    state.set('launch_latitude', 35.5)
    state.set('launch_longitude', -82.3)
    state.set('launch_azimuth', 45.0)
    state.set('launch_elevation', 85.0)
    state.set('launch_roll', 0.0)
    
    logger.info("3. Creating SimulationWorker...")
    worker = SimulationWorker(state)
    
    # Setup signal handlers
    results_received = {'success': False, 'data': None, 'error': None}
    
    def on_progress(value):
        print(f"   Progress: {value*100:.1f}%", end='\r')
    
    def on_finished(results):
        results_received['success'] = True
        results_received['data'] = results
        logger.info(f"[PASS] Simulation finished successfully!")
        logger.info(f"   - Max altitude: {results['metrics'].get('max_altitude', 0):.2f} m")
        logger.info(f"   - Max velocity: {results['metrics'].get('max_velocity', 0):.2f} m/s")
        logger.info(f"   - Flight time: {results['simulation_time']:.2f} s")
        logger.info(f"   - Total steps: {results['total_steps']}")
    
    def on_error(error_msg):
        results_received['error'] = error_msg
        logger.error(f"[FAIL] Simulation failed: {error_msg}")
    
    worker.progress.connect(on_progress)
    worker.finished.connect(on_finished)
    worker.error.connect(on_error)
    
    # Run simulation
    logger.info("4. Running simulation...")
    worker.run()  # Use run() instead of start() for synchronous testing
    
    # Check results
    print("\n")
    if results_received['success']:
        print("[PASS] Physics Integration Test PASSED")
        print("\nResults Summary:")
        data = results_received['data']
        print(f"  Rocket: {data['rocket']}")
        print(f"  Location: {data['location']}")
        print(f"  Duration: {data['simulation_time']:.2f} seconds")
        print(f"  Max Altitude: {data['metrics']['max_altitude']:.2f} m")
        print(f"  Max Velocity: {data['metrics']['max_velocity']:.2f} m/s")
        print(f"  Max Mach: {data['metrics']['max_mach']:.2f}")
        print(f"  Trajectory Points: {len(data['trajectory'])}")
        return 0
    else:
        print("[FAIL] Physics Integration Test FAILED")
        if results_received['error']:
            print(f"Error: {results_received['error']}")
        return 1


if __name__ == '__main__':
    try:
        exit_code = test_physics_worker()
        print("\n" + "="*60 + "\n")
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        sys.exit(1)
