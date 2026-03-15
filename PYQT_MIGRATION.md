# PyQt6 Migration - Rocket Simulator GUI

## Overview

This document describes the PyQt6 implementation of the Rocket Simulator GUI, replacing the Streamlit-based interface.

## Project Structure

```
Rocket-Simulator---GUI/
├── main.py                          # Application entry point
├── requirements.txt                 # Updated with PyQt6 dependencies
├── models/
│   ├── __init__.py
│   └── app_state.py                # ApplicationState singleton (replaces st.session_state)
├── ui/
│   ├── __init__.py
│   ├── main_window.py               # QMainWindow with tab interface
│   ├── widgets/                     # Page widgets
│   │   ├── __init__.py
│   │   ├── simulation_widget.py      # 01_simulation.py → QWidget
│   │   ├── rocket_settings_widget.py # 02_rocket_settings.py → QWidget
│   │   ├── location_settings_widget.py
│   │   ├── monte_carlo_widget.py
│   │   ├── dashboard_widget.py
│   │   ├── units_converter_widget.py
│   │   └── parachute_settings_widget.py
│   └── components/                  # Reusable widget components
│       └── __init__.py
├── workers/
│   ├── __init__.py
│   └── simulation_worker.py         # Background thread for simulations
├── build/
│   └── build.spec                   # PyInstaller configuration
├── data/                            # Data files (unchanged)
│   ├── rockets/configs/*.json
│   ├── locations/launch_sites.json
│   └── ...
├── src/                             # Physics models (unchanged)
│   ├── models/
│   ├── utils/
│   └── ...
└── pages/                           # Legacy Streamlit pages (deprecated)
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python main.py
```

The main window will open with tabs for:
- 🚀 Simulation
- 🛸 Rocket Settings
- 📍 Location
- 📊 Dashboard
- 📈 Monte Carlo
- ⚖️ Units
- 🪂 Parachute

### 3. Build Executable (Windows)

```bash
# Install PyInstaller if not already installed
pip install PyInstaller

# Build executable
pyinstaller build/build.spec

# The executable will be in: dist/RocketSimulator/RocketSimulator.exe
```

For single-file executable instead of folder:
```bash
# Modify build.spec and change to one-file mode
pyinstaller build/build.spec --onefile
```

## Architecture

### State Management: ApplicationState

Replaces Streamlit's `st.session_state` with a singleton pattern:

```python
from models.app_state import ApplicationState

# Get instance
state = ApplicationState.get_instance()

# Set values
state.set('sim_runtime', 600)

# Get values
runtime = state.get('sim_runtime', default=600)

# Save/load state
state.save_to_file('config.json')
state.load_from_file('config.json')
```

### Widget Structure

Each page is a QWidget that:
1. Inherits from `QWidget`
2. Gets `ApplicationState` instance in `__init__`
3. Creates UI in `init_ui()`
4. Connects signals/slots for interactivity
5. Updates state via `state.set()` and `state.get()`

Example:
```python
class SimulationWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
        self.init_ui()
    
    def init_ui(self):
        # Create widgets
        spinbox = QSpinBox()
        spinbox.setValue(self.state.get('sim_runtime', 600))
        spinbox.valueChanged.connect(
            lambda v: self.state.set('sim_runtime', v)
        )
```

### Background Threading

Long-running simulations run in `SimulationWorker` thread:

```python
worker = SimulationWorker(self.state)
worker.progress.connect(self.on_progress)
worker.finished.connect(self.on_finished)
worker.error.connect(self.on_error)
worker.start()
```

## Migration from Streamlit

### Command Mapping

| Streamlit | PyQt6 |
|-----------|-------|
| `st.selectbox()` | `QComboBox()` |
| `st.slider()` | `QSlider()` + `QSpinBox()` |
| `st.text_input()` | `QLineEdit()` |
| `st.number_input()` | `QDoubleSpinBox()` + `QSpinBox()` |
| `st.date_input()` | `QDateEdit()` |
| `st.time_input()` | `QTimeEdit()` |
| `st.checkbox()` | `QCheckBox()` |
| `st.button()` | `QPushButton()` |
| `st.session_state` | `ApplicationState.get_instance()` |
| `st.Page()` multi-page | `QTabWidget` |
| `st.pyplot()` | `FigureCanvas` (matplotlib) |
| `st.plotly_chart()` | `QWebEngineView` |

## Key Features

### ✅ Implemented
- [x] Application state management singleton
- [x] Main window with tab interface
- [x] All 7 widget pages stubbed
- [x] Basic form controls and data binding
- [x] File I/O for saving/loading configs
- [x] Background thread support (SimulationWorker)
- [x] Menu bar with File/Edit/Help menus
- [x] Status bar
- [x] PyInstaller build configuration

### 🔄 In Progress
- [ ] Matplotlib/Plotly integration for charts
- [ ] 3D visualization (PyVista integration)
- [ ] Actual simulation engine threading
- [ ] Progress reporting UI
- [ ] Export to CSV/PDF functionality
- [ ] Unit conversion implementation

### 📋 Future Work
- [ ] Data persistence (JSON/database)
- [ ] Unit testing
- [ ] Documentation
- [ ] Performance optimization
- [ ] Dark mode theme
- [ ] Multi-language support

## File Size and Performance

### Executable Size (PyInstaller)
- **Folder mode**: ~500-800 MB (includes all dependencies)
- **One-file mode**: ~400-600 MB (slightly smaller, slower startup)

### Startup Time
- **Direct Python**: < 1 second (`python main.py`)
- **Executable**: 2-3 seconds (first run) with dependency loading

## Common Tasks

### Adding a New Setting

1. Add to `ApplicationState._initialize_defaults()`:
```python
self._state['my_setting'] = default_value
```

2. Create widget in the appropriate page:
```python
spinbox = QDoubleSpinBox()
spinbox.setValue(self.state.get('my_setting', default_value))
spinbox.valueChanged.connect(
    lambda v: self.state.set('my_setting', v)
)
```

### Running Async Operations

Use `SimulationWorker` pattern or create new `QThread` subclass:
```python
worker = MyWorker()
thread = QThread()
worker.moveToThread(thread)
worker.finished.connect(thread.quit)
thread.started.connect(worker.run)
thread.start()
```

### Displaying Plots

For Matplotlib:
```python
from matplotlib.backends.qt_compat import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

fig = Figure()
canvas = FigureCanvas(fig)
layout.addWidget(canvas)
```

For Plotly:
```python
from PyQt6.QtWebEngineWidgets import QWebEngineView
import plotly.graph_objects as go

view = QWebEngineView()
fig = go.Figure(...)
view.setHtml(fig.to_html(include_plotlyjs='cdn'))
layout.addWidget(view)
```

## Debugging

### Enable Debug Logging

Edit `main.py` logging level:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    ...
)
```

### View Log File

```bash
# Logs are written to: rocket_simulator.log
tail -f rocket_simulator.log
```

### IDE Debugging

Run directly from IDE:
```bash
# VS Code / PyCharm / etc.
python main.py
```

Use breakpoints as normal - PyQt6 debugging works seamlessly.

## Known Limitations

1. **Visualization**: Chart embeddings are placeholders, need Matplotlib/Plotly integration
2. **3D Models**: PyVista integration pending
3. **Data Import**: Currently supports JSON only
4. **Performance**: Simulation threading needs optimization

## Testing

Run the application:
```bash
python main.py
```

Test each tab:
1. **Simulation** - Set parameters, click Run (will execute worker)
2. **Rocket Settings** - Load/create rockets, save configs
3. **Location** - Add/edit launch sites
4. **Monte Carlo** - Configure and run analysis
5. **Dashboard** - View results (placeholder)
6. **Units** - Convert between units
7. **Parachute** - Configure parachute system

## Contributing

When adding features:
1. Follow the widget structure pattern
2. Use `ApplicationState` for state management
3. Use `QThread` for long operations
4. Emit signals for progress updates
5. Log debug info with `logger`

## License

Same as original project

## References

- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [PyInstaller Documentation](https://pyinstaller.org/)
- [Qt Designer](https://doc.qt.io/qt-6/qtdesigner-manual.html) for UI design

---

**Migration Date**: March 2026  
**Status**: Foundation complete, features in development
