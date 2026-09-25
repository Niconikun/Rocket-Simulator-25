"""
Application State Management

Singleton class that replaces Streamlit's session_state for managing
application-wide state across all PyQt widgets.

Features:
- Singleton pattern for centralized state management
- Automatic persistence to/from JSON files
- Thread-safe state access
- Support for testing with reset capability
"""
import json
import os
import threading
from datetime import datetime, date, time
from typing import Any, Dict, Optional, Set
import logging

from src.models.state import StateProvider

logger = logging.getLogger(__name__)

# Default session file name
DEFAULT_SESSION_FILE = "last_session.json"

# Valid types for state values
_VALID_STATE_TYPES = (bool, int, float, str, type(None), date, datetime, time, dict, list)

# Default session file name
DEFAULT_SESSION_FILE = "last_session.json"

# Valid types for state values
_VALID_STATE_TYPES = (bool, int, float, str, type(None), date, datetime, time, dict, list)


class ApplicationState(StateProvider):
    """
    Singleton pattern for managing application state.
    
    Replaces Streamlit's st.session_state with a centralized state container.
    All widgets access state through ApplicationState.get_instance()
    
    This class implements the StateProvider interface, enabling dependency
    injection and better testability.
    """
    
    _instance: Optional['ApplicationState'] = None
    _instance_lock = threading.Lock()  # Protect singleton creation
    
    def __new__(cls):
        # Thread-safe singleton creation
        with cls._instance_lock:
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
        self._state_lock = threading.Lock()  # Thread-safe state access
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
        self._state['parachute_material'] = 'ripstop_nylon'
        self._state['parachute_mass'] = 0.05  # kg (packed parachute mass)
        self._state['parachute_cd'] = 1.5  # drag coefficient
        self._state['parachute_min_velocity'] = 5.0  # m/s
        self._state['parachute_max_velocity'] = 80.0  # m/s
        self._state['parachute_inflation_time'] = 0.5  # seconds
        self._state['selected_parachute'] = None  # Selected parachute name
        
        # Drogue parachute settings
        self._state['drogue_enabled'] = False
        self._state['drogue_diameter'] = 0.25  # meters
        self._state['drogue_mass'] = 0.03  # kg (packed drogue mass)
        self._state['drogue_cd'] = 1.5  # drag coefficient
        self._state['drogue_deployment_altitude'] = 800.0  # meters
        self._state['drogue_inflation_time'] = 0.2  # seconds
        
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
        """Get a state value by key (thread-safe)."""
        with self._state_lock:
            return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a state value by key (thread-safe with validation)."""
        with self._state_lock:
            # Validate the value type
            if not isinstance(value, _VALID_STATE_TYPES):
                logger.warning(f"Invalid type for state[{key}]: {type(value).__name__}. Value must be one of: {_VALID_STATE_TYPES}")
                return
            
            old_value = self._state.get(key)
            self._state[key] = value
            logger.debug(f"State changed: {key} = {value}")
    
    def set_multiple(self, updates: Dict[str, Any]) -> None:
        """Set multiple state values at once (thread-safe)."""
        with self._state_lock:
            for key, value in updates.items():
                # Validate each value
                if not isinstance(value, _VALID_STATE_TYPES):
                    logger.warning(f"Invalid type for state[{key}]: {type(value).__name__}")
                    continue
                self._state[key] = value
            logger.debug(f"Multiple state values updated: {list(updates.keys())}")
    
    def get_all(self) -> Dict[str, Any]:
        """Get the entire state dictionary (thread-safe)."""
        with self._state_lock:
            return self._state.copy()
    
    def reset(self) -> None:
        """Reset all state to defaults (thread-safe)."""
        with self._state_lock:
            self._state.clear()
            self._initialize_defaults()
            logger.info("ApplicationState reset to defaults")
    
    def hard_reset(self) -> None:
        """Completely reset the singleton instance.
        
        This method clears the singleton instance, allowing a fresh instance
        to be created. Useful for testing to ensure a clean state.
        
        WARNING: This affects the global singleton state. Use with caution.
        """
        ApplicationState._instance = None
        logger.info("ApplicationState singleton instance cleared")
    
    @classmethod
    def reset_instance(cls) -> 'ApplicationState':
        """Reset the singleton instance and create a new one.
        
        Returns:
            A fresh ApplicationState instance
        """
        cls._instance = None
        new_instance = cls()
        logger.info("ApplicationState singleton reset and recreated")
        return new_instance
    
    def save_to_file(self, filepath: str = None) -> bool:
        """Save state to a JSON file.
        
        Args:
            filepath: Path to save file. If None, uses DEFAULT_SESSION_FILE.
        
        Returns:
            True if successful, False otherwise
        """
        if filepath is None:
            filepath = DEFAULT_SESSION_FILE
        
        try:
            serializable_state = {}
            for key, value in self._state.items():
                if isinstance(value, (date, datetime)):
                    serializable_state[key] = value.isoformat()
                elif isinstance(value, time):
                    serializable_state[key] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    # Handle nested structures
                    serializable_state[key] = self._serialize_nested(value)
                else:
                    serializable_state[key] = value
            
            # Ensure directory exists
            dirname = os.path.dirname(filepath)
            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(serializable_state, f, indent=2, default=str)
            
            logger.info(f"State saved to {filepath}")
            self._state['last_saved'] = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Failed to save state to {filepath}: {e}")
            return False
    
    def load_from_file(self, filepath: str = None) -> bool:
        """Load state from a JSON file.
        
        Args:
            filepath: Path to load file. If None, uses DEFAULT_SESSION_FILE.
        
        Returns:
            True if successful, False otherwise
        """
        if filepath is None:
            filepath = DEFAULT_SESSION_FILE
        
        if not os.path.exists(filepath):
            logger.warning(f"State file not found: {filepath}")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for key, value in data.items():
                if key == 'sim_date' and isinstance(value, str):
                    try:
                        self._state[key] = date.fromisoformat(value)
                    except ValueError:
                        # Try parsing datetime
                        self._state[key] = datetime.fromisoformat(value).date()
                elif key == 'sim_time' and isinstance(value, str):
                    try:
                        self._state[key] = time.fromisoformat(value)
                    except ValueError:
                        # Try parsing from datetime
                        dt = datetime.fromisoformat(value)
                        self._state[key] = time(dt.hour, dt.minute, dt.second)
                elif key == 'last_saved' and isinstance(value, str):
                    self._state[key] = datetime.fromisoformat(value)
                elif isinstance(value, dict):
                    self._state[key] = self._deserialize_nested(value)
                elif isinstance(value, list):
                    self._state[key] = self._deserialize_list(value)
                else:
                    self._state[key] = value
            
            logger.info(f"State loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load state from {filepath}: {e}")
            return False
    
    def _serialize_nested(self, obj: Any) -> Any:
        """Recursively serialize nested objects for JSON."""
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, time):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_nested(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._serialize_nested(item) for item in obj]
        elif isinstance(obj, (bool, int, float, str, type(None))):
            return obj
        else:
            # For complex objects, try to convert to string
            try:
                return str(obj)
            except Exception:
                return None
    
    def _deserialize_nested(self, obj: Any) -> Any:
        """Recursively deserialize nested objects from JSON."""
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                result[k] = self._deserialize_nested(v)
            return result
        elif isinstance(obj, list):
            return [self._deserialize_nested(item) for item in obj]
        elif isinstance(obj, str):
            # Try to parse as date or datetime
            try:
                return date.fromisoformat(obj)
            except ValueError:
                pass
            try:
                return datetime.fromisoformat(obj)
            except ValueError:
                pass
            return obj
        else:
            return obj
    
    def _deserialize_list(self, obj: list) -> list:
        """Deserialize a list, handling special types."""
        result = []
        for item in obj:
            if isinstance(item, str):
                # Try to parse as date or datetime
                try:
                    result.append(date.fromisoformat(item))
                except ValueError:
                    try:
                        result.append(datetime.fromisoformat(item))
                    except ValueError:
                        result.append(item)
            elif isinstance(item, dict):
                result.append(self._deserialize_nested(item))
            elif isinstance(item, list):
                result.append(self._deserialize_list(item))
            else:
                result.append(item)
        return result
    
    def save_session(self, filepath: str = None) -> bool:
        """Save current session to file (alias for save_to_file)."""
        return self.save_to_file(filepath)
    
    def load_session(self, filepath: str = None) -> bool:
        """Load session from file (alias for load_from_file)."""
        return self.load_from_file(filepath)
    
    def auto_save(self, filepath: str = None) -> bool:
        """Auto-save state with timestamp backup."""
        if filepath is None:
            filepath = DEFAULT_SESSION_FILE
        
        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filepath = f"{filepath}.bak_{timestamp}"
        
        # Save current state to backup first
        if os.path.exists(filepath):
            try:
                import shutil
                shutil.copy2(filepath, backup_filepath)
                logger.debug(f"Backup created: {backup_filepath}")
            except Exception as e:
                logger.warning(f"Failed to create backup: {e}")
        
        # Save current state
        return self.save_to_file(filepath)
