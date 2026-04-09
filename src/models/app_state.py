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
        self._state['sim_runtime'] = 600  # seconds
        self._state['sim_time_step'] = 0.001  # seconds
        self._state['sim_date'] = date.today()
        self._state['sim_time'] = time(12, 0)
        self._state['sim_timezone'] = "UTC"
        
        # Environment parameters
        self._state['average_temperature'] = 20.0  # Celsius
        self._state['average_pressure'] = 101325.0  # Pa
        self._state['launch_elevation'] = 60.0  # meters
        self._state['launch_site_orientation'] = 20.0  # degrees (magnetic declination at launch site)
        self._state['conditions'] = []  # Environmental conditions list (can be used for weather/wind data)
        
        # ========== ROCKET SELECTION & SETTINGS ==========
        self._state['selected_rocket'] = 'agni-1'  # Default rocket
        self._state['sim_location'] = None  # Currently selected location name
        
        # Launch site parameters
        self._state['launch_latitude'] = 0.0  # degrees
        self._state['launch_longitude'] = 0.0  # degrees
        self._state['launch_elevation_angle'] = 85.0  # degrees (launch rod elevation angle)
        self._state['launch_azimuth'] = 0.0  # degrees (direction of launch)
        self._state['launch_roll'] = 0.0  # degrees (rocket roll angle at launch)
        
        # Rocket properties (editable)
        self._state['initial_mass'] = 0.0  # kg
        self._state['burn_time'] = 0.0  # seconds
        self._state['reference_area'] = 0.0  # m²
        self._state['I_before_burn'] = {"x": 0.0, "y": 0.0, "z": 0.0}  # kg·m²
        self._state['I_after_burn'] = {"x": 0.0, "y": 0.0, "z": 0.0}  # kg·m²
        
        # ========== PARACHUTE SETTINGS ==========
        self._state['parachute_enabled'] = False
        self._state['parachute_deployment_altitude'] = 300.0  # meters
        self._state['parachute_diameter'] = 0.6  # meters
        self._state['parachute_cd'] = 1.5  # drag coefficient
        self._state['parachute_min_velocity'] = 5.0  # m/s
        self._state['parachute_max_velocity'] = 80.0  # m/s
        self._state['parachute_inflation_time'] = 0.5  # seconds
        self._state['selected_parachute'] = None  # Selected parachute name
        
        # Drogue parachute settings
        self._state['drogue_enabled'] = False
        self._state['drogue_diameter'] = 0.25  # meters
        self._state['drogue_cd'] = 1.5  # drag coefficient
        self._state['drogue_deployment_altitude'] = 800.0  # meters
        
        # ========== WIND MODEL PARAMETERS ==========
        self._state['wind_enabled'] = False  # Enable/disable wind simulation
        self._state['wind_model_type'] = 'logarithmic'  # Model type: constant, logarithmic, power_law, gust, shear
        self._state['wind_speed_ref'] = 5.0  # Reference wind speed [m/s]
        self._state['wind_reference_height'] = 10.0  # Reference height [m]
        self._state['wind_direction'] = 180.0  # Wind direction FROM (meteorological convention) [degrees]
        self._state['wind_roughness_length'] = 0.1  # Surface roughness z0 [m] (for logarithmic profile)
        self._state['wind_exponent'] = 0.2  # Power law exponent alpha [unitless] (for power_law profile)
        self._state['wind_gust_intensity'] = 0.0  # Turbulence intensity [0-1] (for gust model)
        self._state['wind_gust_length_scale'] = 300.0  # Gust length scale [m] (for gust model)
        
        # ========== MONTE CARLO PARAMETERS ==========
        self._state['monte_carlo_runs'] = 100  # number of simulation runs
        self._state['monte_carlo_variations'] = {}  # variation parameters dict
        
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
