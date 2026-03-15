"""
Application State Management

Singleton class that replaces Streamlit's session_state for managing
application-wide state across all PyQt widgets.
"""
from datetime import datetime, date, time
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ApplicationState:
    """
    Singleton pattern for managing application state.
    
    Replaces Streamlit's st.session_state with a centralized state container.
    All widgets access state through ApplicationState.get_instance()
    """
    
    _instance: Optional['ApplicationState'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ApplicationState, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize state with default values only once."""
        if self._initialized:
            return
        
        self._initialized = True
        self._state: Dict[str, Any] = {}
        self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Set up default values for all application parameters."""
        
        # ========== SIMULATION PARAMETERS ==========
        self._state['simulation_running'] = False
        self._state['simulation_progress'] = 0.0
        self._state['simulation_results'] = None
        self._state['simulation_error'] = None
        self._state['simulation_data'] = None
        
        # Time and location parameters
        self._state['sim_runtime'] = 600
        self._state['sim_time_step'] = 0.001
        self._state['sim_date'] = date.today()
        self._state['sim_time'] = time(12, 0)
        self._state['sim_timezone'] = "UTC"
        
        # Environment parameters
        self._state['average_temperature'] = 20.0  # Celsius
        self._state['average_pressure'] = 101325.0  # Pa
        self._state['launch_elevation'] = 60.0  # meters
        self._state['launch_site_orientation'] = 20.0  # degrees
        self._state['vel_initial'] = 0.0  # m/s
        self._state['conditions'] = []
        
        # ========== ROCKET SELECTION & SETTINGS ==========
        self._state['sim_rocket'] = None
        self._state['selected_rocket'] = 'agni-1'  # Default rocket
        self._state['sim_location'] = None
        
        # Launch site parameters
        self._state['launch_latitude'] = 0.0  # degrees
        self._state['launch_longitude'] = 0.0  # degrees
        self._state['launch_azimuth'] = 0.0  # degrees (direction of launch)
        self._state['launch_roll'] = 0.0  # degrees (rocket roll angle at launch)
        
        # Rocket properties (editable)
        self._state['rocket_name'] = ""
        self._state['initial_mass'] = 0.0
        self._state['burn_time'] = 0.0
        self._state['reference_area'] = 0.0
        self._state['I_before_burn'] = {"x": 0.0, "y": 0.0, "z": 0.0}
        self._state['I_after_burn'] = {"x": 0.0, "y": 0.0, "z": 0.0}
        
        # ========== PARACHUTE SETTINGS ==========
        self._state['parachute_enabled'] = False
        self._state['parachute_deployment_altitude'] = 300.0
        self._state['parachute_area'] = 1.0
        self._state['parachute_drag_coefficient'] = 1.5
        
        # ========== MONTE CARLO PARAMETERS ==========
        self._state['monte_carlo_runs'] = 100
        self._state['monte_carlo_variations'] = {}
        
        # ========== UI STATE ==========
        self._state['current_tab'] = 0
        self._state['last_saved'] = None
        
        logger.info("ApplicationState initialized with default values")
    
    @staticmethod
    def get_instance() -> 'ApplicationState':
        """Get or create the singleton instance."""
        if ApplicationState._instance is None:
            ApplicationState()
        return ApplicationState._instance
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a state value by key."""
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a state value by key."""
        old_value = self._state.get(key)
        self._state[key] = value
        logger.debug(f"State changed: {key} = {value}")
    
    def set_multiple(self, updates: Dict[str, Any]) -> None:
        """Set multiple state values at once."""
        for key, value in updates.items():
            self._state[key] = value
        logger.debug(f"Multiple state values updated: {list(updates.keys())}")
    
    def get_all(self) -> Dict[str, Any]:
        """Get the entire state dictionary."""
        return self._state.copy()
    
    def reset(self) -> None:
        """Reset all state to defaults."""
        self._state.clear()
        self._initialize_defaults()
        logger.info("ApplicationState reset to defaults")
    
    def save_to_file(self, filepath: str) -> bool:
        """Save state to a JSON file."""
        import json
        try:
            # Convert datetime objects to strings for JSON serialization
            serializable_state = {}
            for key, value in self._state.items():
                if isinstance(value, (date, datetime)):
                    serializable_state[key] = value.isoformat()
                elif isinstance(value, time):
                    serializable_state[key] = value.isoformat()
                else:
                    serializable_state[key] = value
            
            with open(filepath, 'w') as f:
                json.dump(serializable_state, f, indent=2)
            logger.info(f"State saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            return False
    
    def load_from_file(self, filepath: str) -> bool:
        """Load state from a JSON file."""
        import json
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Convert ISO format strings back to datetime objects
            for key, value in data.items():
                if key == 'sim_date' and isinstance(value, str):
                    self._state[key] = date.fromisoformat(value)
                elif key == 'sim_time' and isinstance(value, str):
                    self._state[key] = time.fromisoformat(value)
                elif key == 'last_saved' and isinstance(value, str):
                    self._state[key] = datetime.fromisoformat(value)
                else:
                    self._state[key] = value
            
            logger.info(f"State loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return False
