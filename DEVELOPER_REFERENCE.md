# PyQt6 Developer Quick Reference

## Getting Started in 5 Minutes

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the App

```bash
python main.py
```

### 3. Build Executable

```bash
pyinstaller build/build.spec
# Output: dist/RocketSimulator/RocketSimulator.exe
```

---

## Project Layout

```bash
main.py              ← Entry point (run this)
models/
  app_state.py      ← Global state (ApplicationState singleton)
ui/
  main_window.py    ← Main window with tabs
  widgets/          ← 7 page widgets (one per tab)
workers/
  simulation_worker.py ← Background simulation thread
build/
  build.spec        ← PyInstaller configuration
```

---

## Core Concepts

### 1. State Management

Replace Streamlit's `st.session_state`:

```python
from models.app_state import ApplicationState

state = ApplicationState.get_instance()
state.set('key', value)           # Set value
value = state.get('key', default) # Get value
state.reset()                      # Reset to defaults
state.save_to_file('config.json') # Persist
state.load_from_file('config.json') # Load
```

### 2. Creating Widgets

Template for a new widget page:

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from models.app_state import ApplicationState

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create controls
        button = QPushButton("Click me")
        button.clicked.connect(self.on_button_click)
        layout.addWidget(button)
        
        self.setLayout(layout)
    
    def on_button_click(self):
        # Handle click
        value = self.state.get('my_setting', 0)
        self.state.set('my_setting', value + 1)
```

### 3. Background Threading

For long operations:

```python
from PyQt6.QtCore import QThread
from workers.simulation_worker import SimulationWorker

worker = SimulationWorker(self.state)
worker.progress.connect(self.on_progress)      # Signal: float 0.0-1.0
worker.finished.connect(self.on_finished)      # Signal: dict results
worker.error.connect(self.on_error)            # Signal: str error
worker.start()
```

### 4. Real Physics Engine Integration

The SimulationWorker now integrates the real physics engine from `src/models/`:

**Key Components:**

- `Rocket`: 6-DOF dynamics with aerodynamics and propulsion
- `Planet`: Gravitational field and rotational dynamics
- `Atmosphere`: Temperature, pressure, density profiles (ISA model)
- `Clock`: Time reference and GMST calculations

**Simulation Flow:**

```bash
1. Load rocket config (JSON)
2. Initialize physics objects:
   - Rocket: 6-DOF state (position, velocity, attitude)
   - Planet: Gravitational/magnetic field
   - Atmosphere: Environmental conditions
   
3. Main loop (Runge-Kutta 4th order integration):
   - Update environmental models
   - Update rocket mass/inertia (during burn)
   - Calculate aerodynamic forces
   - Calculate propulsive forces
   - Integrate 6-DOF equations of motion
   - Store trajectory data
   - Check termination conditions
   
4. Return results:
   - Trajectory (time, altitude, velocity, range)
   - Metrics (max altitude, max velocity, flight time)
```

**Rocket Configuration (data/rockets/configs/{name}.json):**

```json
{
  "name": "Example-Rocket",
  "initial_mass": 1000.0,
  "reference_area": 0.5,
  "CoM_before_burn": {"x": 0, "y": 2.0, "z": 0},
  "CoM_after_burn": {"x": 0, "y": 1.8, "z": 0},
  "I_before_burn": {"x": 10, "y": 50, "z": 10},
  "I_after_burn": {"x": 10, "y": 40, "z": 10},
  "engine": {
    "burn_time": 5.0,
    "propellant_mass": 200.0,
    "specific_impulse": 250.0,
    "mean_thrust": 400000.0
  }
}
```

**Required Application State Parameters:**

```python
state.set('sim_runtime', 600)           # Total simulation time (seconds)
state.set('sim_time_step', 0.001)       # Integration timestep (seconds)
state.set('selected_rocket', 'agni-1')  # Rocket name
state.set('sim_location', 'SITE-A')     # Launch site name
state.set('sim_date', date(2026, 3, 15))  # Launch date
state.set('sim_time', time(12, 0))      # Launch time (UTC)
state.set('average_temperature', 20.0)  # °C
state.set('launch_latitude', 35.5)      # degrees
state.set('launch_longitude', -82.3)    # degrees
state.set('launch_azimuth', 45.0)       # Launch direction (degrees)
state.set('launch_elevation', 85.0)     # Launch angle (degrees)
state.set('launch_roll', 0.0)           # Rocket roll angle (degrees)
```

---

## Common Tasks

### Show Message Box

```python
from PyQt6.QtWidgets import QMessageBox

QMessageBox.information(self, "Title", "Message")
QMessageBox.warning(self, "Title", "Warning")
QMessageBox.critical(self, "Title", "Error")
reply = QMessageBox.question(self, "Title", "Question?",
                             QMessageBox.StandardButton.Yes | 
                             QMessageBox.StandardButton.No)
```

### File Dialog

```python
from PyQt6.QtWidgets import QFileDialog

filepath, _ = QFileDialog.getOpenFileName(self, "Open", "", "JSON (*.json)")
filepath, _ = QFileDialog.getSaveFileName(self, "Save", "", "JSON (*.json)")
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Message")
logger.warning("Warning")
logger.error("Error")
logger.debug("Debug info")
```

### Connect Signals

```python
# Button click
button.clicked.connect(self.on_click)

# Value changed
spinbox.valueChanged.connect(self.on_value_changed)
combo.currentTextChanged.connect(self.on_selection_changed)
checkbox.stateChanged.connect(self.on_checked)

# Text changed
lineedit.textChanged.connect(self.on_text_changed)
```

---

## Commonly Used Widgets

| Widget | Purpose | Example |
|--------|---------|---------|
| `QLineEdit` | Text input | `QLineEdit()` |
| `QSpinBox` | Integer input | `QSpinBox(); spinbox.setRange(0, 100)` |
| `QDoubleSpinBox` | Float input | `QDoubleSpinBox(); spinbox.setDecimals(2)` |
| `QComboBox` | Dropdown | `combo.addItems(['a', 'b', 'c'])` |
| `QCheckBox` | Checkbox | `QCheckBox(); box.setChecked(True)` |
| `QPushButton` | Button | `QPushButton("Click"); btn.clicked.connect(...)` |
| `QLabel` | Text label | `QLabel("Hello")` |
| `QSlider` | Slider | `QSlider(); slider.setRange(0, 100)` |
| `QDateEdit` | Date picker | `QDateEdit()` |
| `QTimeEdit` | Time picker | `QTimeEdit()` |
| `QTableWidget` | Data table | `table.setColumnCount(3)` |
| `QGroupBox` | Group container | `group = QGroupBox("Title")` |
| `QTabWidget` | Tabs | Main window has this |
| `QProgressBar` | Progress | `progress.setValue(50)` |

---

## Layouts

```python
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout

# Vertical
vbox = QVBoxLayout()
vbox.addWidget(widget1)
vbox.addWidget(widget2)

# Horizontal
hbox = QHBoxLayout()
hbox.addWidget(widget1)
hbox.addWidget(widget2)

# Forms (label-field pairs)
form = QFormLayout()
form.addRow("Label:", widget)

# Grid
grid = QGridLayout()
grid.addWidget(widget, row, col)
```

---

## Widget Properties

```python
# Enable/Disable
widget.setEnabled(False)
widget.setVisible(False)

# Size
widget.setMinimumWidth(100)
widget.setMaximumWidth(500)
widget.setFixedSize(200, 100)

# Styling
widget.setStyleSheet("color: red; font-weight: bold;")

# Tooltips
widget.setToolTip("Hover text")

# Focus
widget.setFocus()
```

---

## 7 Pages Overview

| # | Tab | File | Purpose |
|---|-----|------|---------|
| 1 | Simulation | `simulation_widget.py` | Run simulations, configure params |
| 2 | Rocket Settings | `rocket_settings_widget.py` | Create/edit rockets |
| 3 | Location | `location_settings_widget.py` | Manage launch sites |
| 4 | Monte Carlo | `monte_carlo_widget.py` | Statistical analysis |
| 5 | Dashboard | `dashboard_widget.py` | View results, charts, export |
| 6 | Units | `units_converter_widget.py` | Convert between units |
| 7 | Parachute | `parachute_settings_widget.py` | Configure parachute system |

---

## Debugging

### Run with Debug Logging

Edit `main.py`:

```python
logging.basicConfig(level=logging.DEBUG)  # Change from INFO
```

### Run with Breakpoints

```bash
# PyCharm / VS Code: Set breakpoint and F5 to debug
python -m pdb main.py  # Python debugger
```

### View Logs

```bash
tail -f rocket_simulator.log  # Watch live
```

---

## Performance Tips

1. **Cache data loading** - Use `@functools.lru_cache()`
2. **Lazy loading** - Load data only when needed
3. **Threading** - Use `QThread` for long operations
4. **Avoid blocking UI** - Never do heavy work in main thread

---

## Architecture Pattern

Every widget follows this pattern:

```bash
__init__()
  ↓
init_ui()
  ├─ Create layouts
  ├─ Create widgets
  ├─ Load initial state
  └─ Connect signals
  ↓
on_<event>()
  ├─ Update state
  └─ Update UI
```

---

## Next Steps

1. **Understand ApplicationState** - Read `models/app_state.py`
2. **Study a widget** - Read `ui/widgets/simulation_widget.py`
3. **Add a feature** - Create new widget or extend existing
4. **Connect to simulation** - Link widgets to physics engine
5. **Add charts** - Integrate Matplotlib/Plotly
6. **Build executable** - Follow `BUILD_INSTRUCTIONS.md`

---

## Useful Links

- [PyQt6 Docs](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [Qt Designer](https://doc.qt.io/qt-6/qtdesigner-manual.html) - Visual layout tool
- [PyInstaller Docs](https://pyinstaller.org/en/stable/)
- [Python Logging](https://docs.python.org/3/library/logging.html)

---

## Keyboard Shortcuts (Major IDE)

| Action | VS Code | PyCharm |
|--------|---------|---------|
| Run | F5 | Shift+F10 |
| Debug | F5 | Shift+F9 |
| Breakpoint | F9 | Ctrl+F8 |
| Step Over | F10 | F8 |
| Step Into | F11 | F7 |

---

**Remember**: Save often, build frequently, test thoroughly! 🚀
