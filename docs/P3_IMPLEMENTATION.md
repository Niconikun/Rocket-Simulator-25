# P3 Implementation Guide

## Completed P3 Tasks

### P3_1: Internationalization (i18n) ✅

**Files Created:**
- `src/config/translations.py` - Translation manager with Qt integration
- `docs/TRANSLATIONS.md` - Complete guide for adding translations

**Files Modified:**
- `src/config/__init__.py` - Export translation utilities
- `ui/widgets/__init__.py` - Added `tr()` helper method to BaseWidget
- `ui/main_window.py` - Added Language menu and translation initialization

**Features:**
- Support for multiple languages via Qt's QTranslator
- Convenience `tr()` function for translating strings
- Language menu in main window
- Lazy translation support for class-level strings
- Logging for translation loading

**Usage:**
```python
from src.config import tr

label = QLabel(tr("Simulation Parameters"))
button = QPushButton(tr("Run Simulation"))
```

**Adding New Languages:**
1. Create `.ts` file using Qt's `lupdate` tool
2. Translate strings using Qt Linguist
3. Compile to `.qm` using `lrelease`
4. Add to `SUPPORTED_LANGUAGES` dictionary
5. Update `src/config/translations.py`

---

### P3_2: Event Bus ✅

**Files Created:**
- `src/utils/event_bus.py` - Event bus implementation with singleton pattern
- `docs/EVENT_BUS.md` - Complete guide for using the event bus

**Files Modified:**
- `src/utils/__init__.py` - Export event bus utilities
- `ui/widgets/simulation_widget.py` - Added event publishing for simulation lifecycle

**Features:**
- Singleton event bus using PyQt6 signals
- 20+ standard event types (Simulation, Configuration, Rocket, Location, Wind, Parachute, Monte Carlo, UI)
- Weak reference support to prevent memory leaks
- Thread-safe event publishing
- Convenience functions: `subscribe()`, `unsubscribe()`, `publish()`
- Automatic cleanup of dead subscribers

**Event Types:**
- `SIMULATION_STARTED`, `SIMULATION_COMPLETED`, `SIMULATION_ERROR`, etc.
- `WIND_SETTINGS_CHANGED`, `WIND_SCENARIO_SELECTED`
- `PARACHUTE_CONFIG_CHANGED`
- `THEME_CHANGED`, `LANGUAGE_CHANGED`, `TAB_CHANGED`
- And more...

**Usage:**
```python
from src.utils.event_bus import EventType, subscribe, publish

# Subscribe
def on_sim_started(data):
    print(f"Simulation started: {data}")

subscribe(EventType.SIMULATION_STARTED, on_sim_started)

# Publish
publish(EventType.SIMULATION_STARTED, {"timestamp": datetime.now().isoformat()})
```

---

### P3_3: Keyboard Shortcuts ✅

**Files Modified:**
- `ui/main_window.py` - Added shortcuts to menu actions
- `ui/widgets/simulation_widget.py` - Added shortcuts to control buttons

**Shortcuts Implemented:**

#### File Menu
- **Ctrl+N** - New Simulation
- **Ctrl+O** - Open Configuration
- **Ctrl+S** - Save Configuration
- **Ctrl+Q** - Exit

#### Edit Menu
- **Ctrl+R** - Reset to Defaults

#### View Menu
- **Ctrl+Shift+T** - Toggle Dark Mode

#### Simulation Widget
- **F5** - Run Simulation
- **F6** - Pause/Resume Simulation
- **F7** - Stop Simulation

#### Tab Navigation
- **Ctrl+Tab** - Next Tab (built-in QTabWidget)
- **Ctrl+Shift+Tab** - Previous Tab (built-in QTabWidget)

**Adding More Shortcuts:**
```python
# In __init__
action = QAction("My Action", self)
action.setShortcut("Ctrl+M")
action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
action.triggered.connect(self.my_handler)

# Or directly on QPushButton
button = QPushButton("Click Me")
button.setShortcut("F8")
```

---

## Feature Explanations

### Geocoding Integration 🌍

#### What is Geocoding?
Geocoding converts between human-readable addresses (e.g., "Kennedy Space Center, FL") and geographic coordinates (latitude, longitude). Reverse geocoding does the opposite.

#### Current State
The application currently supports:
- Manual entry of latitude/longitude
- Saving/loading location presets
- Map visualization using cartopy/matplotlib

#### Implementation Approach

**Option 1: Use OpenStreetMap Nominatim (Free)**
```python
import requests

def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Convert an address to latitude/longitude using Nominatim.
    
    Args:
        address: Human-readable address string
    
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={address}"
        response = requests.get(url, headers={'User-Agent': 'RocketSimulator/2.0'})
        results = response.json()
        if results:
            return float(results[0]['lat']), float(results[0]['lon'])
    except Exception as e:
        logger.error(f"Geocoding failed: {e}")
    return None

def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """
    Convert latitude/longitude to a human-readable address.
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
    
    Returns:
        Human-readable address or None
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        response = requests.get(url, headers={'User-Agent': 'RocketSimulator/2.0'})
        data = response.json()
        if 'display_name' in data:
            return data['display_name']
    except Exception as e:
        logger.error(f"Reverse geocoding failed: {e}")
    return None
```

**Option 2: Use Google Maps API (Paid, but more accurate)**
```python
import requests

GOOGLE_API_KEY = "YOUR_API_KEY"

def geocode_with_google(address: str) -> Optional[Tuple[float, float]]:
    """Geocode using Google Maps API."""
    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': address,
            'key': GOOGLE_API_KEY
        }
        response = requests.get(url, params=params)
        data = response.json()
        if data['status'] == 'OK' and data['results']:
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
    except Exception as e:
        logger.error(f"Google geocoding failed: {e}")
    return None
```

**Option 3: Offline Geocoding with Local Database**
- Use GeoNames database (free for non-commercial use)
- Store city/location data in a local SQLite database
- Less accurate but works offline

#### Integration Points

1. **Location Settings Widget** (`ui/widgets/location_settings_widget.py`)
   - Add "Geocode Address" button
   - Add address input field
   - Show address when coordinates are selected on map

2. **New Dependencies**
   ```
   # For Nominatim (already have requests)
   pip install requests
   
   # For Google Maps
   pip install google-maps
   ```

3. **Configuration**
   - Add API keys to settings
   - Add geocoding service selection (Nominatim/Google/Offline)
   - Add caching to avoid rate limits

4. **UI Changes**
   ```python
   # In location_settings_widget.py
   self.address_input = QLineEdit()
   self.address_input.setPlaceholderText(tr("Enter address for geocoding"))
   self.geocode_button = QPushButton(tr("Geocode"))
   self.geocode_button.clicked.connect(self.geocode_address)
   
   def geocode_address(self):
       address = self.address_input.text()
       lat, lon = geocode_address(address)
       if lat and lon:
           self.latitude_spinbox.setValue(lat)
           self.longitude_spinbox.setValue(lon)
           self.state.set(Constants.StateKeys.LAUNCH_LATITUDE, lat)
           self.state.set(Constants.StateKeys.LAUNCH_LONGITUDE, lon)
   ```

#### Benefits
- Users can search for launch sites by name
- Easier to find coordinates for real-world locations
- Improves usability for non-expert users

#### Considerations
- Rate limits: Nominatim has strict usage policies
- Privacy: Addresses are sent to external services
- Offline support: Consider caching results locally

---

### Weather Integration ☁️

#### What is Weather Integration?
Fetching real-time or forecast weather data (wind, temperature, pressure, humidity) for simulation locations to make simulations more accurate.

#### Current State
- Manual entry of weather parameters
- Wind model configuration
- No connection to real weather data

#### Implementation Approach

**Option 1: OpenWeatherMap API (Free tier available)**
```python
import requests
from datetime import datetime, timedelta

OPENWEATHER_API_KEY = "YOUR_API_KEY"

def fetch_weather_data(lat: float, lon: float) -> Optional[Dict]:
    """
    Fetch current weather data from OpenWeatherMap.
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
    
    Returns:
        Dictionary with weather data or None
    """
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'  # Get data in metric units
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('cod') == 200:
            return {
                'temperature': data['main']['temp'],  # Celsius
                'pressure': data['main']['pressure'] * 100,  # Pa (hPa to Pa)
                'humidity': data['main']['humidity'],  # %
                'wind_speed': data['wind']['speed'],  # m/s
                'wind_direction': data['wind']['deg'],  # degrees
                'visibility': data.get('visibility', 10000),  # meters
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Weather fetch failed: {e}")
    return None

def fetch_weather_forecast(lat: float, lon: float, hours: int = 24) -> Optional[List[Dict]]:
    """
    Fetch weather forecast from OpenWeatherMap.
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        hours: Number of hours to forecast
    
    Returns:
        List of weather data dictionaries or None
    """
    try:
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('cod') == '200':
            forecast = []
            for item in data['list'][:min(8, hours // 3)]:  # 3-hour intervals
                forecast.append({
                    'timestamp': datetime.fromtimestamp(item['dt']).isoformat(),
                    'temperature': item['main']['temp'],
                    'pressure': item['main']['pressure'] * 100,
                    'wind_speed': item['wind']['speed'],
                    'wind_direction': item['wind']['deg']
                })
            return forecast
    except Exception as e:
        logger.error(f"Weather forecast fetch failed: {e}")
    return None
```

**Option 2: NOAA/METAR Data (Free, aviation weather)**
```python
import requests
import re

def fetch_metar_data(icao: str) -> Optional[Dict]:
    """
    Fetch METAR data for an ICAO airport code.
    
    Args:
        icao: ICAO airport code (e.g., "KSC" for Kennedy Space Center)
    
    Returns:
        Dictionary with parsed METAR data or None
    """
    try:
        url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
        response = requests.get(url)
        metar_string = response.text.strip()
        
        if metar_string:
            return parse_metar(metar_string)
    except Exception as e:
        logger.error(f"METAR fetch failed: {e}")
    return None

def parse_metar(metar: str) -> Dict:
    """
    Parse a METAR string into a dictionary.
    
    Example METAR: "KSC 011253Z 22012KT 10SM FEW025 SCT250 25/15 A3006 RMK AO2"
    """
    # Implementation would parse the METAR string
    # This is simplified - use a proper METAR parser library
    return {
        'wind_speed': 12,  # knots -> would need conversion
        'wind_direction': 220,
        'visibility': 16093,  # 10SM in meters
        'temperature': 25,
        'pressure': 101800  # A3006 = 30.06 inHg -> Pa
    }
```

**Option 3: Local Weather Stations (Offline)**
- Store historical weather data for common launch sites
- Allow manual data entry
- Use interpolated data from nearby stations

#### Integration Points

1. **Simulation Widget** (`ui/widgets/simulation_widget.py`)
   - Add "Fetch Current Weather" button
   - Auto-fetch weather when location is selected
   - Display weather data source and timestamp

2. **Location Settings Widget**
   - Add weather data panel
   - Show current weather for selected location
   - Allow selecting forecast time

3. **New Weather Widget**
   - Create dedicated weather display widget
   - Show current conditions and forecast
   - Weather map visualization

4. **Event Integration**
   ```python
   # Publish weather update event
   publish(EventType.WEATHER_UPDATED, {
       'location': (lat, lon),
       'data': weather_data,
       'timestamp': datetime.now().isoformat()
   })
   
   # Subscribe to location changes to fetch weather
   subscribe(EventType.LOCATION_CHANGED, lambda data: self.fetch_weather(data['lat'], data['lon']))
   ```

5. **Configuration**
   - Add API key settings
   - Add weather service selection
   - Add auto-fetch toggle
   - Add caching options

#### Benefits
- More accurate simulations with real weather data
- Quick setup for real-world launch conditions
- Forecast support for planning future launches
- Multiple weather source options

#### Considerations
- API rate limits and costs
- Network connectivity requirements
- Data freshness and caching
- Privacy considerations
- Offline fallback

---

### Simulation Checkpointing 💾

#### What is Checkpointing?
Saving the complete simulation state at regular intervals so that:
- Long simulations can be paused and resumed
- If a simulation crashes, you can restart from the last checkpoint
- You can explore different "what-if" scenarios from a saved state

#### Current State
- Simulations run to completion or until stopped
- Results are saved at the end
- No intermediate state saving
- No pause/resume functionality (pause is implemented but doesn't save state)

#### Implementation Approach

**State to Checkpoint:**
```python
# Complete simulation state that needs to be saved:
checkpoint_data = {
    'time': current_time,           # Current simulation time
    'state': {
        'position': [x, y, z],       # Current position (ENU or ECEF)
        'velocity': [vx, vy, vz],    # Current velocity
        'attitude': [roll, pitch, yaw],  # Current attitude
        'mass': current_mass,        # Current rocket mass
        'engine_state': {             # Engine state
            'burn_time': elapsed_burn_time,
            'thrust': current_thrust,
            'mass_flow': current_mass_flow
        },
        'aerodynamics': {             # Aerodynamic state
            'aoa': angle_of_attack,
            'sideslip': sideslip_angle,
            'dynamic_pressure': q,
            'mach': current_mach
        },
        'environment': {              # Environmental state
            'altitude': altitude,
            'density': rho,
            'pressure': p,
            'temperature': temp,
            'gravity': g
        },
        'wind': {                    # Wind state at current position
            'velocity': [wind_x, wind_y, wind_z],
            'direction': wind_direction
        },
        'parachute': {               # Parachute state
            'deployed': is_deployed,
            'deployment_time': deployment_time,
            'inflation_complete': is_inflated
        }
    },
    'parameters': {                # Simulation parameters (constant)
        'rocket_config': rocket_config,
        'launch_parameters': launch_params,
        'wind_model': wind_model_config,
        'atmosphere_model': atmosphere_config
    },
    'random_state': random_seed,     # For reproducibility
    'metadata': {
        'start_time': start_timestamp,
        'checkpoint_time': datetime.now().isoformat(),
        'sim_id': simulation_id
    }
}
```

**Implementation:**

1. **Checkpoint Manager** (`src/utils/checkpoint_manager.py`)
   ```python
   import json
   import pickle
   import zlib
   from pathlib import Path
   from datetime import datetime
   
   class CheckpointManager:
       """Manages simulation checkpoints."""
       
       CHECKPOINT_DIR = Path('data/checkpoints')
       
       @classmethod
       def save_checkpoint(cls, simulation_id: str, state: Dict, compression: bool = True) -> Path:
           """
           Save a simulation checkpoint.
           
           Args:
               simulation_id: Unique identifier for the simulation
               state: Complete simulation state dictionary
               compression: Whether to compress the checkpoint
           
           Returns:
               Path to the saved checkpoint file
           """
           cls.CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
           timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
           filename = f"{simulation_id}_{timestamp}.chkpt"
           filepath = cls.CHECKPOINT_DIR / filename
           
           # Save with compression
           if compression:
               data = json.dumps(state).encode('utf-8')
               compressed = zlib.compress(data)
               with open(filepath, 'wb') as f:
                   f.write(compressed)
           else:
               with open(filepath, 'w', encoding='utf-8') as f:
                   json.dump(state, f, indent=2)
           
           return filepath
       
       @classmethod
       def load_checkpoint(cls, filepath: Path) -> Dict:
           """
           Load a simulation checkpoint.
           
           Args:
               filepath: Path to the checkpoint file
           
           Returns:
               Complete simulation state dictionary
           """
           try:
               with open(filepath, 'rb') as f:
                   compressed = f.read()
               try:
                   data = zlib.decompress(compressed)
                   return json.loads(data.decode('utf-8'))
               except zlib.error:
                   # Try uncompressed
                   filepath = Path(filepath)
                   with open(filepath, 'r', encoding='utf-8') as f:
                       return json.load(f)
           except Exception as e:
               logger.error(f"Failed to load checkpoint: {e}")
               raise
       
       @classmethod
       def list_checkpoints(cls, simulation_id: Optional[str] = None) -> List[Path]:
           """List available checkpoints for a simulation."""
           if not cls.CHECKPOINT_DIR.exists():
               return []
           
           if simulation_id:
               pattern = f"{simulation_id}_*.chkpt"
           else:
               pattern = "*.chkpt"
           
           return sorted(cls.CHECKPOINT_DIR.glob(pattern), reverse=True)
       
       @classmethod
       def delete_checkpoint(cls, filepath: Path) -> bool:
           """Delete a checkpoint file."""
           try:
               filepath.unlink()
               return True
           except Exception as e:
               logger.error(f"Failed to delete checkpoint: {e}")
               return False
   ```

2. **SimulationWorker Integration**
   ```python
   # In workers/simulation_worker.py
   
   class SimulationWorker(QThread):
       # ... existing code ...
       
       def __init__(self, state, checkpoint_interval: float = 60.0):
           super().__init__()
           self.state = state
           self.checkpoint_interval = checkpoint_interval  # seconds
           self.last_checkpoint_time = 0
       
       def run(self):
           # ... existing setup ...
           
           while not self._stop_requested:
               if self._paused:
                   time.sleep(0.1)
                   continue
               
               # Run simulation step
               self._run_step()
               
               # Check if we should save a checkpoint
               if self.simulation_time - self.last_checkpoint_time >= self.checkpoint_interval:
                   self._save_checkpoint()
                   self.last_checkpoint_time = self.simulation_time
           
           # ... existing cleanup ...
       
       def _save_checkpoint(self):
           """Save current simulation state as a checkpoint."""
           try:
               state = self._get_current_state()
               filepath = CheckpointManager.save_checkpoint(
                   self.sim_id,
                   state
               )
               self.checkpoint_saved.emit(str(filepath))
           except Exception as e:
               logger.error(f"Failed to save checkpoint: {e}")
       
       def _get_current_state(self) -> Dict:
           """Get complete simulation state for checkpointing."""
           # Extract state from the simulation
           return {
               'time': self.current_time,
               'state': self.simulation.get_state(),
               'parameters': self.parameters,
               'random_state': self.random_state.getstate()
           }
   ```

3. **UI Integration**
   - Add "Checkpoint" menu or panel
   - Show list of available checkpoints
   - Allow loading from checkpoint
   - Allow deleting checkpoints
   - Visualize checkpoint timeline

4. **Event Integration**
   ```python
   # New event types in event_bus.py
   class EventType(Enum):
       # ... existing events ...
       CHECKPOINT_SAVED = auto()
       CHECKPOINT_LOADED = auto()
       SIMULATION_PAUSED = auto()
       SIMULATION_RESUMED = auto()
   
   # Publish checkpoint events
   publish(EventType.CHECKPOINT_SAVED, {
       'filepath': checkpoint_path,
       'simulation_id': sim_id,
       'time': current_time
   })
   
   publish(EventType.SIMULATION_PAUSED, {
       'simulation_id': sim_id,
       'time': current_time,
       'can_resume': True
   })
   ```

5. **Configuration**
   - Add checkpoint interval setting
   - Add max checkpoints to keep
   - Add checkpoint compression toggle
   - Add auto-checkpoint toggle

#### Resume from Checkpoint

```python
# In main_window.py or simulation_widget.py

def load_from_checkpoint(self):
    """Load a simulation from a checkpoint."""
    filepath, _ = QFileDialog.getOpenFileName(
        self,
        "Open Checkpoint",
        "data/checkpoints",
        "Checkpoint Files (*.chkpt);;All Files (*)"
    )
    
    if filepath:
        try:
            checkpoint = CheckpointManager.load_checkpoint(Path(filepath))
            
            # Reset simulation to checkpoint state
            self.simulation_worker.load_from_checkpoint(checkpoint)
            
            # Update UI
            publish(EventType.CHECKPOINT_LOADED, {
                'filepath': filepath,
                'time': checkpoint['time']
            })
            
            self.statusBar().showMessage(f"Resumed from checkpoint: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load checkpoint: {e}")
```

#### Benefits
- Pause and resume long-running simulations
- Recover from crashes or interruptions
- "What-if" scenario testing from mid-simulation
- Better user experience for long simulations
- Reproducibility with saved random state

#### Considerations
- Checkpoint file size (use compression)
- Performance impact of frequent checkpoints
- Version compatibility (checkpoint format changes)
- Storage management (auto-delete old checkpoints)
- Thread safety for saving during simulation

---

### Advanced Visualizations 📊

#### Current Visualizations
- 2D plots (altitude, velocity, acceleration vs. time)
- 3D trajectory visualization
- Map-based launch site visualization
- Real-time progress tracking

#### Advanced Visualization Options

**1. 3D Trajectory with Terrain**
- Use elevation data to show terrain under flight path
- Integrate with SRTM or other DEM data
- Show impact prediction
- Animate trajectory in 3D

**Implementation:**
```python
import numpy as np
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D

def plot_3d_trajectory_with_terrain(self, trajectory):
    """
    Plot 3D trajectory with terrain elevation.
    
    Args:
        trajectory: List of (x, y, z) points in meters
    """
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Extract coordinates
    x = [p[0] for p in trajectory]
    y = [p[1] for p in trajectory]
    z = [p[2] for p in trajectory]
    
    # Plot trajectory
    ax.plot(x, y, z, 'r-', linewidth=2, label='Trajectory')
    
    # Add terrain (simplified - would use actual DEM data)
    # For demo, create a simple plane
    xx, yy = np.meshgrid(np.linspace(min(x), max(x), 10), 
                         np.linspace(min(y), max(y), 10))
    zz = np.zeros_like(xx)  # Flat terrain
    ax.plot_surface(xx, yy, zz, alpha=0.3, color='green')
    
    # Mark launch and impact points
    ax.scatter([x[0]], [y[0]], [z[0]], color='blue', s=100, label='Launch')
    ax.scatter([x[-1]], [y[-1]], [z[-1]], color='red', s=100, label='Impact')
    
    ax.set_xlabel('East (m)')
    ax.set_ylabel('North (m)')
    ax.set_zlabel('Altitude (m)')
    ax.set_title('3D Trajectory with Terrain')
    ax.legend()
    
    return fig
```

**2. Real-Time Telemetry Display**
- Dashboard-style display with gauges and meters
- Real-time updates during simulation
- Multiple data streams (altitude, velocity, acceleration, etc.)

**Implementation:**
```python
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import QTimer

class TelemetryDashboard(QWidget):
    """Real-time telemetry display."""
    
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        
        # Create gauges
        self.altitude_gauge = AnalogGauge("Altitude (m)", 0, 10000)
        self.velocity_gauge = AnalogGauge("Velocity (m/s)", 0, 1000)
        self.acceleration_gauge = AnalogGauge("Acceleration (g)", 0, 10)
        self.mach_gauge = AnalogGauge("Mach", 0, 5)
        
        # Layout
        layout = QVBoxLayout()
        gauge_layout = QHBoxLayout()
        gauge_layout.addWidget(self.altitude_gauge)
        gauge_layout.addWidget(self.velocity_gauge)
        layout.addLayout(gauge_layout)
        gauge_layout2 = QHBoxLayout()
        gauge_layout2.addWidget(self.acceleration_gauge)
        gauge_layout2.addWidget(self.mach_gauge)
        layout.addLayout(gauge_layout2)
        self.setLayout(layout)
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_gauges)
        self.update_timer.start(100)  # Update 10 times per second
    
    def update_gauges(self):
        """Update all gauges with current state."""
        sim_state = self.state.get('simulation_state', {})
        self.altitude_gauge.set_value(sim_state.get('altitude', 0))
        self.velocity_gauge.set_value(sim_state.get('velocity', 0))
        self.acceleration_gauge.set_value(sim_state.get('acceleration_g', 0))
        self.mach_gauge.set_value(sim_state.get('mach', 0))
```

**3. Wind Profile Visualization**
- 2D/3D wind vector field
- Wind speed/direction at different altitudes
- Gust visualization
- Time-varying wind patterns

**Implementation:**
```python
import matplotlib.pyplot as plt
import numpy as np

def plot_wind_profile(self, wind_model, altitude_range=(0, 10000)):
    """
    Plot wind speed and direction vs. altitude.
    
    Args:
        wind_model: Wind model instance
        altitude_range: Tuple of (min_altitude, max_altitude) in meters
    """
    altitudes = np.linspace(altitude_range[0], altitude_range[1], 100)
    wind_speeds = []
    wind_directions = []
    
    for alt in altitudes:
        speed, direction = wind_model.get_wind_at_altitude(alt)
        wind_speeds.append(speed)
        wind_directions.append(direction)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # Speed vs altitude
    ax1.plot(wind_speeds, altitudes / 1000)
    ax1.set_xlabel('Wind Speed (m/s)')
    ax1.set_ylabel('Altitude (km)')
    ax1.set_title('Wind Speed Profile')
    ax1.grid(True)
    
    # Direction vs altitude
    ax2.plot(wind_directions, altitudes / 1000)
    ax2.set_xlabel('Wind Direction (degrees from North)')
    ax2.set_ylabel('Altitude (km)')
    ax2.set_title('Wind Direction Profile')
    ax2.grid(True)
    
    plt.tight_layout()
    return fig

def plot_wind_vectors_3d(self, wind_model, grid_size=10):
    """
    Plot 3D wind vector field.
    
    Args:
        wind_model: Wind model instance
        grid_size: Number of points in each dimension
    """
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Create grid
    x = np.linspace(-5000, 5000, grid_size)
    y = np.linspace(-5000, 5000, grid_size)
    z = np.linspace(0, 10000, grid_size)
    
    xx, yy, zz = np.meshgrid(x, y, z)
    
    # Calculate wind vectors at each point
    u = np.zeros_like(xx)
    v = np.zeros_like(xx)
    w = np.zeros_like(xx)
    
    for i in range(grid_size):
        for j in range(grid_size):
            for k in range(grid_size):
                speed, direction = wind_model.get_wind_at_position(xx[i,j,k], yy[i,j,k], zz[i,j,k])
                # Convert polar to Cartesian
                u[i,j,k] = speed * np.sin(np.radians(direction))
                v[i,j,k] = speed * np.cos(np.radians(direction))
                # w stays 0 for horizontal wind
    
    # Plot every Nth vector for clarity
    stride = max(1, grid_size // 5)
    ax.quiver(
        xx[::stride, ::stride, ::stride],
        yy[::stride, ::stride, ::stride],
        zz[::stride, ::stride, ::stride],
        u[::stride, ::stride, ::stride],
        v[::stride, ::stride, ::stride],
        w[::stride, ::stride, ::stride],
        length=500, normalize=True, arrow_length_ratio=0.1
    )
    
    ax.set_xlabel('East (m)')
    ax.set_ylabel('North (m)')
    ax.set_zlabel('Altitude (m)')
    ax.set_title('3D Wind Vector Field')
    
    return fig
```

**4. Monte Carlo Results Visualization**
- Scatter plots of results distribution
- Histograms of key metrics
- Statistical analysis overlays
- Interactive filtering

**Implementation:**
```python
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

def plot_monte_carlo_results(self, results):
    """
    Plot Monte Carlo simulation results.
    
    Args:
        results: List of simulation results dictionaries
    """
    if not results:
        return None
    
    # Extract metrics
    max_altitudes = [r['metrics']['max_altitude'] for r in results]
    max_velocities = [r['metrics']['max_velocity'] for r in results]
    impacts = [r['metrics']['impact_distance'] for r in results]
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    # Max altitude distribution
    ax1.hist(max_altitudes, bins=30, alpha=0.7, color='blue')
    mean, std = np.mean(max_altitudes), np.std(max_altitudes)
    ax1.axvline(mean, color='red', linestyle='--', label=f'Mean: {mean:.0f} m')
    ax1.set_xlabel('Max Altitude (m)')
    ax1.set_ylabel('Frequency')
    ax1.set_title('Max Altitude Distribution')
    ax1.legend()
    ax1.grid(True)
    
    # Max velocity distribution
    ax2.hist(max_velocities, bins=30, alpha=0.7, color='green')
    mean, std = np.mean(max_velocities), np.std(max_velocities)
    ax2.axvline(mean, color='red', linestyle='--', label=f'Mean: {mean:.0f} m/s')
    ax2.set_xlabel('Max Velocity (m/s)')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Max Velocity Distribution')
    ax2.legend()
    ax2.grid(True)
    
    # Impact distance vs altitude scatter
    ax3.scatter(max_altitudes, impacts, alpha=0.5)
    ax3.set_xlabel('Max Altitude (m)')
    ax3.set_ylabel('Impact Distance (m)')
    ax3.set_title('Altitude vs Impact Distance')
    ax3.grid(True)
    
    # Q-Q plot for normality check
    stats.probplot(max_altitudes, dist="norm", plot=ax4)
    ax4.set_title('Q-Q Plot: Max Altitude')
    
    plt.tight_layout()
    return fig
```

**5. Comparable Simulation Visualization**
- Overlay multiple simulation results
- Compare different configurations
- Side-by-side metrics comparison
- Interactive parameter exploration

**6. Export Options**
- Export to CSV for external analysis
- Export to images (PNG, SVG)
- Export to interactive HTML (Plotly)
- Export to video (for animations)

**Integration:**
```python
# Add to dashboard_widget.py

class DashboardWidget(BaseWidget):
    # ... existing code ...
    
    def add_advanced_visualization_tab(self):
        """Add advanced visualization options."""
        advanced_tab = QWidget()
        layout = QVBoxLayout()
        
        # Add visualization selection
        self.vis_type_combo = QComboBox()
        self.vis_type_combo.addItems([
            tr("2D Plots"),
            tr("3D Trajectory"),
            tr("3D Trajectory with Terrain"),
            tr("Wind Profile"),
            tr("Monte Carlo Results"),
            tr("Comparative Analysis")
        ])
        self.vis_type_combo.currentTextChanged.connect(self.update_visualization)
        layout.addWidget(QLabel(tr("Visualization Type:")))
        layout.addWidget(self.vis_type_combo)
        
        # Add figure display
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
        
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)
        
        # Add export buttons
        export_layout = QHBoxLayout()
        self.export_png_button = QPushButton(tr("Export PNG"))
        self.export_png_button.clicked.connect(lambda: self.export_figure('png'))
        export_layout.addWidget(self.export_png_button)
        
        self.export_csv_button = QPushButton(tr("Export CSV"))
        self.export_csv_button.clicked.connect(self.export_csv)
        export_layout.addWidget(self.export_csv_button)
        
        layout.addLayout(export_layout)
        advanced_tab.setLayout(layout)
        
        self.tabs.addTab(advanced_tab, tr("Advanced Visualization"))
    
    def update_visualization(self, vis_type):
        """Update the visualization based on selection."""
        self.figure.clear()
        
        results = self.state.get(Constants.StateKeys.SIMULATION_RESULTS)
        if not results:
            return
        
        if vis_type == tr("3D Trajectory"):
            self.plot_3d_trajectory(results)
        elif vis_type == tr("3D Trajectory with Terrain"):
            self.plot_3d_trajectory_with_terrain(results)
        elif vis_type == tr("Wind Profile"):
            self.plot_wind_profile(results.get('wind_model'))
        elif vis_type == tr("Monte Carlo Results"):
            self.plot_monte_carlo_results(results)
        
        self.canvas.draw()
```

#### Benefits
- Better understanding of simulation results
- Professional-quality visualizations
- Export capabilities for reports and presentations
- Interactive exploration of data
- Comparison and analysis tools

#### Considerations
- Performance with large datasets
- Memory usage for high-resolution visualizations
- Dependency management (matplotlib, numpy, scipy)
- Thread safety for real-time updates
- Accessibility for colorblind users

---

## Summary

### Completed P3 Tasks
✅ **P3_1: Internationalization** - Full i18n infrastructure with Qt integration
✅ **P3_2: Event Bus** - Decoupled communication between widgets
✅ **P3_3: Keyboard Shortcuts** - Comprehensive shortcuts for all major actions

### Feature Explanations
📍 **Geocoding Integration** - Convert addresses to coordinates and vice versa
☁️ **Weather Integration** - Fetch real-time and forecast weather data
💾 **Simulation Checkpointing** - Save and resume simulations
📊 **Advanced Visualizations** - 3D terrain, telemetry, wind profiles, Monte Carlo analysis

All features are designed to be:
- Modular and pluggable
- Non-intrusive (existing functionality preserved)
- Well-documented
- Thread-safe
- Follow existing architecture patterns
