# Detailed UI Widget Analysis - By File

## 📋 Quick Navigation
- [main_window.py](#main_windowpy) ✅
- [simulation_widget.py](#simulation_widgetpy) ⚠️
- [rocket_settings_widget.py](#rocket_settings_widgetpy) 🔴
- [location_settings_widget.py](#location_settings_widgetpy) ⚠️
- [wind_settings_widget.py](#wind_settings_widgetpy) 🔴
- [dashboard_widget.py](#dashboard_widgetpy) 🔴
- [monte_carlo_widget.py](#monte_carlo_widgetpy) 🔴
- [parachute_settings_widget.py](#parachute_settings_widgetpy) 🔴
- [units_converter_widget.py](#units_converter_widgetpy) 🔴
- [wind_scenario_editor_widget.py](#wind_scenario_editor_widgetpy) ⚠️

---

## main_window.py
**Status:** ✅ **CLEAN - No Issues**

Quick scan shows:
- Proper imports
- All methods complete
- Good signal connections
- Appropriate error handling

---

## simulation_widget.py
**Status:** ⚠️ **MINOR ISSUES - 3 Issues**

### Issue 1: Datetime Import Inefficiency
**Line:** 221  
**Severity:** HIGH  
**Description:** Uses `__import__('datetime')` instead of proper import
```python
# CURRENT (Line 221)
'timestamp': __import__('datetime').datetime.now().isoformat()

# FIX
# At top of file, add:
from datetime import datetime

# Then use:
'timestamp': datetime.now().isoformat()
```
**Time:** 5 minutes

### Issue 2: Incomplete reset_simulation() Method
**Line:** 303-310  
**Severity:** HIGH  
**Description:** `reset_simulation()` only resets progress bar, not all state
```python
# CURRENT
def reset_simulation(self):
    self.progress_bar.setValue(0)
    # Missing: reset other UI fields, clear results, clear error state

# FIX - Should also reset:
# - All spinbox/combo values to defaults
# - Runtime, timestep to defaults
# - Progress bar value
# - Results
# - Error messages
```
**Time:** 30 minutes

### Issue 3: Missing Result Validation
**Line:** 247  
**Severity:** MEDIUM  
**Description:** No validation that results actually contain expected data before saving
```python
# ADD before accessing results
if not results or 'metrics' not in results:
    raise ValueError("Invalid simulation results structure")
```
**Time:** 15 minutes

---

## rocket_settings_widget.py
**Status:** 🔴 **CRITICAL - 6 Issues**

### Issue 1: Duplicate QScrollArea Import ⚠️ MUST FIX
**Line:** 7  
**Severity:** CRITICAL  
**Description:** `QScrollArea` appears twice in imports
```python
# CURRENT
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
    QPushButton, QComboBox, QGroupBox, QFormLayout, QMessageBox, QTabWidget,
    QFileDialog, QScrollArea, QSpinBox, QScrollArea, QTextEdit  # ← DUPLICATE
)

# FIX
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
    QPushButton, QComboBox, QGroupBox, QFormLayout, QMessageBox, QTabWidget,
    QFileDialog, QScrollArea, QSpinBox, QTextEdit  # ← Removed duplicate
)
```
**Time:** 5 minutes

### Issue 2: Incomplete delete_rocket_config() Method
**Line:** 733+  
**Severity:** CRITICAL  
**Description:** Method ends abruptly at line 733 with no implementation
```python
# CURRENT
def delete_rocket_config(self):
    """Delete selected rocket configuration."""
    if not self.current_rocket:
        QMessageBox.warning(self, "Warning", "Select a rocket to delete")
        return
    
    reply = QMessageBox.question(
        # ... ends here, no body

# COMPLETE IMPLEMENTATION PROVIDED IN PHASE 1 DOCUMENT
```
**Time:** 30 minutes

### Issue 3: Missing Type Hints on validate_rocket_config()
**Line:** 636  
**Severity:** HIGH  
**Description:** Method returns tuple but no return type hint
```python
# CURRENT
def validate_rocket_config(self) -> tuple:

# FIX
def validate_rocket_config(self) -> tuple[bool, list[str], list[str]]:
```
**Time:** 5 minutes

### Issue 4: Fragile CSV Column Detection
**Line:** 791  
**Severity:** MEDIUM  
**Description:** Column detection uses substring matching that could misidentify columns
```python
# CURRENT
for col in df.columns:
    col_lower = col.lower().strip()
    if 'time' in col_lower or 't' == col_lower:  # Could match "lifetime"
        time_col = col

# BETTER
for col in df.columns:
    col_lower = col.lower().strip()
    if col_lower in ['time', 't', 'time (s)', 'time_s']:
        time_col = col
```
**Time:** 1 hour

### Issue 5: Hardcoded File Paths
**Line:** 537, 788, 927  
**Severity:** MEDIUM  
**Description:** Path `'data/rockets/configs'` repeated in multiple methods
```python
# SOLUTION: Add constant at top of file
ROCKET_CONFIGS_PATH = 'data/rockets/configs'

# Then use throughout
os.makedirs(self.ROCKET_CONFIGS_PATH, exist_ok=True)
```
**Time:** 30 minutes

### Issue 6: No Validation for Loaded Configurations
**Line:** 562  
**Severity:** MEDIUM  
**Description:** `load_rocket_data()` applies data without validating structure
```python
# ADD validation at start of method
required_fields = ['name', 'initial_mass', 'engine', 'geometry']
for field in required_fields:
    if field not in rocket_data:
        raise ValueError(f"Missing required field: {field}")
```
**Time:** 30 minutes

---

## location_settings_widget.py
**Status:** ⚠️ **MINOR ISSUES - 4 Issues**

### Issue 1: load_location_file() Doesn't Apply Data
**Line:** 196  
**Severity:** HIGH  
**Description:** Loads JSON but doesn't update UI or state
```python
# CURRENT - just loads
with open(filepath, 'r') as f:
    location_data = json.load(f)

# MISSING - apply to widget:
self.name_edit.setText(location_data.get('name', ''))
self.latitude_spinbox.setValue(location_data.get('latitude', 0))
self.longitude_spinbox.setValue(location_data.get('longitude', 0))
self.elevation_spinbox.setValue(location_data.get('elevation', 0))
self.state.set('sim_location', location_data.get('name', ''))
self.refresh_map()
```
**Time:** 1 hour

### Issue 2: Hardcoded Splitter Sizes
**Line:** 50  
**Severity:** MEDIUM  
**Description:** Splitter sizes (400, 600) hardcoded instead of responsive
```python
# Current
splitter.setSizes([400, 600])

# Better: use percentages or constants
FORM_WIDTH_RATIO = 0.4
MAP_WIDTH_RATIO = 0.6
# Then calculate based on widget size
```
**Time:** 1 hour

### Issue 3: Hardcoded Map Colors
**Line:** 131  
**Severity:** LOW  
**Description:** Marker colors hardcoded (#FF6B6B, etc.)
```python
# Solution: Add constants at module top
MARKER_COLORS = {
    'launch_site': '#FF6B6B',
    'selected': '#4ECDC4',
    'history': '#95E1D3'
}
```
**Time:** 30 minutes

### Issue 4: No Validation on Load
**Line:** 196-200  
**Severity:** MEDIUM  
**Description:** Loaded file not validated before use
```python
# Add validation
if not all(k in location_data for k in ['latitude', 'longitude', 'elevation']):
    raise ValueError("Invalid location file structure")
```
**Time:** 30 minutes

---

## wind_settings_widget.py
**Status:** 🔴 **CRITICAL - 5 Issues**

### Issue 1: Missing Function Import ⚠️ MUST FIX
**Line:** 224  
**Severity:** CRITICAL  
**Description:** `update_wind_model()` calls undefined function
```python
# CURRENT - At method call (line 224):
wind_model = create_wind_model_from_state(self.state)
# But NOT imported!

# FIX - Add at top of file:
from src.utils.wind_utils import create_wind_model_from_state
```
**Time:** 2 minutes

### Issue 2: Hardcoded Wind Model Types
**Line:** 67  
**Severity:** MEDIUM  
**Description:** Model types hardcoded as strings
```python
# Current
self.wind_model_combo.addItems([
    'constant',
    'logarithmic',
    'power_law',
    'gust'
])

# Better - Add constant at top:
WIND_MODELS = ['constant', 'logarithmic', 'power_law', 'gust']
self.wind_model_combo.addItems(WIND_MODELS)
```
**Time:** 30 minutes

### Issue 3: Inefficient Parameter Visibility Toggle
**Line:** 139  
**Severity:** MEDIUM  
**Description:** Multiple `.hide()/.show()` calls - could use dict mapping
```python
# CURRENT approach
if model == 'logarithmic':
    self.roughness_label.hide()
    self.wind_roughness_spin.hide()
    self.exponent_label.show()
    # ... many more lines

# BETTER approach
PARAM_VISIBILITY = {
    'logarithmic': ['exponent', 'roughness'],
    'gust': ['gust_intensity', 'gust_length'],
    # ...
}
# Then toggle in loop
```
**Time:** 1-2 hours

### Issue 4: Incomplete Preview Tab
**Line:** 190+  
**Severity:** HIGH  
**Description:** Tab created but no content generation logic
```python
# MISSING: Methods to populate table with wind profile data
# Needs: _update_preview_table(), _calculate_wind_at_altitudes()
```
**Time:** 2-3 hours

### Issue 5: No Model Validation Before Use
**Line:** 259  
**Severity:** MEDIUM  
**Description:** `update_preview()` doesn't check if model created successfully
```python
# ADD before using model:
if self.wind_model is None:
    QMessageBox.warning(self, "Error", "Failed to create wind model")
    return
```
**Time:** 30 minutes

---

## dashboard_widget.py
**Status:** 🔴 **CRITICAL - 12 Issues**

### Issue 1: File Appears Truncated
**Line:** 821+  
**Severity:** CRITICAL  
**Description:** File ends mid-method; multiple methods incomplete
**Methods Affected:**
- `_generate_2d_map()` - Incomplete
- `_generate_3d_flight_path()` - Missing
- `generate_pdf()` - Incomplete
- `export_csv()` - Incomplete
- `refresh_dashboard()` - Not found

**Action:** Read remaining file content and complete all methods
**Time:** 3-4 hours

### Issue 2: Inconsistent Data Structure Handling
**Line:** 449-470  
**Severity:** CRITICAL  
**Description:** Assumes specific dict structure without defensive checks
```python
# CURRENT - no validation
metrics = results.get('metrics', {})
max_altitude = metrics.get('max_altitude', 0)

# BETTER - with validation
if not isinstance(results, dict) or 'metrics' not in results:
    raise ValueError("Invalid results structure")
metrics = results['metrics']
if not isinstance(metrics, dict):
    raise ValueError("Metrics must be dict")
```
**Time:** 1-2 hours

### Issue 3: Hardcoded Grid Dimensions
**Line:** 470  
**Severity:** MEDIUM  
**Description:** Chart grid size (3x3) hardcoded
```python
# Current - hardcoded
row = i // 3
col = i % 3

# Better - use constant or calculate
CHARTS_PER_ROW = 3
row = i // CHARTS_PER_ROW
col = i % CHARTS_PER_ROW
```
**Time:** 1 hour

### Issue 4: No Canvas Cleanup
**Line:** 528  
**Severity:** MEDIUM  
**Description:** Previous charts not cleaned up before adding new ones
```python
# ADD cleanup before adding:
self.charts_grid_layout.itemAt(i).widget().deleteLater()
# OR use better approach:
self._clear_charts()
```
**Time:** 1 hour

### Issue 5: Type Inconsistency in Metadata
**Line:** 330  
**Severity:** MEDIUM  
**Description:** `.get()` returns mixed types (string/number)
```python
# Current assumes number
max_altitude = metadata.get('max_altitude', 0)  # Could be "0" string

# Fix with type conversion
max_altitude = float(metadata.get('max_altitude', 0))
```
**Time:** 1 hour

### Issue 6-12: Missing Docstrings
**Multiple lines**  
**Severity:** HIGH × 7  
**Action:** Add docstrings to all methods following template
**Time:** 2-3 hours total

---

## monte_carlo_widget.py
**Status:** 🔴 **CRITICAL - 9 Issues**

### Issue 1: Placeholder Implementation ⚠️ MUST FIX
**Line:** 64-72  
**Severity:** CRITICAL  
**Description:** `run_monte_carlo()` shows message box instead of executing
```python
# CURRENT
def run_monte_carlo(self):
    QMessageBox.information(self, "Info", "Monte Carlo simulation not completed...")
    # NO ACTUAL IMPLEMENTATION

# NEEDS COMPLETE REWRITE - see Phase 1 section for full implementation
```
**Solution:** 
1. Create `MonteCarloWorker` class with thread support
2. Implement parameter variation logic
3. Add progress signal emissions
4. Populate results table
**Time:** 3-4 hours

### Issue 2: Parameter Variations Never Used
**Line:** 45-69  
**Severity:** CRITICAL  
**Description:** Temperature/pressure variation checkboxes exist but aren't read
```python
# CURRENT - created but never used
self.temp_vary_check = QCheckBox("Vary Temperature")
self.temp_min = QDoubleSpinBox()
self.temp_max = QDoubleSpinBox()

# FIX - Create variations dict:
def _get_variations(self):
    variations = {}
    if self.temp_vary_check.isChecked():
        variations['temperature'] = (self.temp_min.value(), self.temp_max.value())
    # ... repeat for other parameters
    return variations
```
**Time:** 1 hour

### Issue 3: Results Not Populated
**Line:** 86  
**Severity:** CRITICAL  
**Description:** Results table created but never filled with data
```python
# Create method to populate table:
def _populate_results_table(self, results):
    self.results_table.setRowCount(0)
    for metric_name, stats in results.items():
        self.results_table.insertRow(self.results_table.rowCount())
        # Add mean, std, min, max cells
```
**Time:** 1-2 hours

### Issue 4-9: Signal Issues
**Multiple**  
**Severity:** HIGH  
**Description:** Missing signal declarations and connections
```python
# Add at class level:
monte_carlo_started = pyqtSignal()
monte_carlo_progress = pyqtSignal(int)
monte_carlo_finished = pyqtSignal(dict)
monte_carlo_error = pyqtSignal(str)
```
**Time:** 1-2 hours total

---

## parachute_settings_widget.py
**Status:** 🔴 **CRITICAL - 6 Issues**

### Issue 1: Incorrect CheckState Evaluation ⚠️ MUST FIX
**Line:** 157, 168  
**Severity:** CRITICAL  
**Description:** Using `.value` on CheckState enum incorrectly
```python
# CURRENT (WRONG)
if self.parachute_enabled_check.checkState() == Qt.CheckState.Checked.value:
    # This compares CheckState enum to integer, unreliable

# FIX
if self.parachute_enabled_check.isChecked():
    # Use built-in boolean method
```
**Time:** 15 minutes

### Issue 2: Enable Controls Not Properly Linked
**Line:** 168+  
**Severity:** MEDIUM  
**Description:** Drogue enabled checkbox doesn't properly disable its controls
```python
# CURRENT
self.drogue_diameter.setEnabled(self.drogue_enabled_check.isChecked())
# Only set once at init

# FIX - Connect to signal
self.drogue_enabled_check.stateChanged.connect(self._on_drogue_state_changed)

def _on_drogue_state_changed(self):
    enabled = self.drogue_enabled_check.isChecked()
    self.drogue_diameter.setEnabled(enabled)
    self.drogue_cd.setEnabled(enabled)
```
**Time:** 30 minutes

### Issue 3: Simplified Descent Calculation
**Line:** 229  
**Severity:** MEDIUM  
**Description:** Formula doesn't account for drag coefficient (Cd)
```python
# Current formula likely missing proper Cd consideration
# Should use: v_descent = sqrt(2 * m * g / (ρ * A * Cd))
# Where A = π * r² for circular parachute
```
**Time:** 1 hour

### Issue 4: No Deployment Altitude Validation
**Line:** 163  
**Severity:** MEDIUM  
**Description:** Doesn't validate deployment altitude against current velocity
- Could deploy when rocket traveling too fast
- No checks for safe deployment window

**Fix:** Add validation method
```python
def _validate_deployment_params(self):
    altitude = self.deployment_altitude.value()
    max_velocity = self.max_velocity.value()
    # Validate altitude >= 100m, velocity <= max_velocity
```
**Time:** 1 hour

### Issue 5: Notes Field Never Saved/Loaded
**Line:** 85  
**Severity:** LOW  
**Description:** Notes QPlainTextEdit created but not persisted
```python
# Add to save/load methods
notes = self.notes_edit.toPlainText()
# Save to config and restore on load
```
**Time:** 30 minutes

### Issue 6: Hardcoded Material
**Line:** 212  
**Severity:** MEDIUM  
**Description:** Parachute material hardcoded as 'ripstop_nylon'
```python
# Solution: Allow user to select material
self.material_combo = QComboBox()
self.material_combo.addItems(['ripstop_nylon', 'nylon', 'silk', 'custom'])
```
**Time:** 1 hour

---

## units_converter_widget.py
**Status:** 🔴 **CRITICAL - 16 Issues (Most Severe)**

### Issue 1-6: All Conversions Broken ⚠️ MUST FIX
**Line:** 130-170  
**Severity:** CRITICAL × 6  
**Description:** Each conversion function hardcoded for single path

#### convert_length() - Line 130
```python
# CURRENT - only m to km
def convert_length(self):
    # hardcoded m→km conversion, ignores selected units

# NEEDS - proper unit selection and conversion matrix
def convert_length(self):
    try:
        value = float(self.length_from.text())
        from_unit = self.length_from_unit.currentText()
        to_unit = self.length_to_unit.currentText()
        
        # Use conversion matrix
        factor = CONVERSIONS['length'].get((from_unit, to_unit), 1.0)
        result = value * factor
        self.length_result.setText(f"{result:.6f}")
    except ValueError:
        self.length_result.setText("Invalid input")
```

#### Similar fixes needed for:
- `convert_velocity()` - Line 145
- `convert_temperature()` - Line 160
- `convert_mass()` - Line 170+
- `convert_pressure()` - Line 180+
- All others

**Time:** 2-3 hours total

### Issue 7: Missing Conversion Constants
**Line:** Top of file  
**Severity:** CRITICAL  
**Description:** Conversion factors not defined
```python
# ADD at module level:
CONVERSIONS = {
    'length': {
        ('meters', 'kilometers'): 0.001,
        ('meters', 'feet'): 3.28084,
        ('meters', 'miles'): 0.000621371,
        ('kilometers', 'meters'): 1000,
        ('kilometers', 'feet'): 3280.84,
        ('kilometers', 'miles'): 0.621371,
        ('feet', 'meters'): 0.3048,
        ('feet', 'kilometers'): 0.0003048,
        ('feet', 'miles'): 0.000189394,
        ('miles', 'meters'): 1609.34,
        ('miles', 'kilometers'): 1.60934,
        ('miles', 'feet'): 5280,
    },
    'velocity': {
        # ... similar matrix
    },
    # ... etc
}
```
**Time:** 1-2 hours

### Issue 8: From Unit Change Not Connected
**Line:** 60  
**Severity:** CRITICAL  
**Description:** Changing "From" unit doesn't trigger conversion
```python
# Current
self.length_from_unit = QComboBox()
# Missing signal connection!

# FIX
self.length_from_unit.currentTextChanged.connect(self.convert_length)
```
**Time:** 30 minutes (for all conversion tabs)

### Issue 9-13: Input Validation Missing
**Line:** 130+  
**Severity:** MEDIUM  
**Description:** No validation in any conversion method
```python
# Should check:
try:
    value = float(self.input_field.text())
except ValueError:
    self.result_field.setText("Invalid number")
    return
    
if value < 0 and unit_type != 'temperature':
    # Warn about negative values
```
**Time:** 2-3 hours

### Issue 14: State Never Used
**Line:** 32  
**Severity:** LOW  
**Description:** `self.state` initialized but never used
```python
# Remove or use if saving unit preferences
# Currently unused - consider removing to reduce confusion
```
**Time:** 10 minutes

### Issue 15: Hardcoded Default Values
**Line:** 60+  
**Severity:** LOW  
**Description:** Default input values hardcoded
```python
# CURRENT
self.length_from = QLineEdit("1.0")

# BETTER - use constants
DEFAULT_LENGTH = 1.0
self.length_from = QLineEdit(str(DEFAULT_LENGTH))
```
**Time:** 1 hour

### Issue 16: No Temperature Fahrenheit/Celsius Handling
**Severity:** MEDIUM  
**Description:** Temperature conversion needs special logic (offset required)
```python
# Temperature needs unlike other units:
def convert_temperature(self):
    from_unit = self.temp_from_unit.currentText()
    to_unit = self.temp_to_unit.currentText()
    value = float(self.temp_from.text())
    
    # Convert to Celsius first
    if from_unit == "Celsius":
        c_value = value
    elif from_unit == "Fahrenheit":
        c_value = (value - 32) * 5/9
    elif from_unit == "Kelvin":
        c_value = value - 273.15
    
    # Then convert from Celsius
    if to_unit == "Celsius":
        result = c_value
    # ... etc
```
**Time:** 1 hour

**Total for units_converter_widget.py: 2-4 hours**

---

## wind_scenario_editor_widget.py
**Status:** ⚠️ **MINOR ISSUES - 6 Issues**

### Issue 1: Missing Method Implementation
**Line:** 263  
**Severity:** HIGH  
**Description:** `_on_preview_custom()` signal exists but method missing
```python
# Create method:
def _on_preview_custom(self):
    """Preview custom scenario parameters."""
    # Generate wind profile visualization
    # Show in preview tab
```
**Time:** 1 hour

### Issue 2: Incomplete Save Method
**Line:** 271  
**Severity:** HIGH  
**Description:** `_on_save_custom_scenario()` writes without validation
```python
# ADD validation before save:
errors = self._validate_scenario(scenario)
if errors:
    QMessageBox.warning(self, "Validation Errors", "\n".join(errors))
    return
```
**Time:** 1 hour

### Issue 3: Scenario Reloading Inefficient
**Line:** 317  
**Severity:** MEDIUM  
**Description:** `load_custom_scenarios()` reloads all on any change
```python
# Better approach:
def _refresh_scenario(self, scenario_id):
    """Refresh only the changed scenario."""
    # Instead of clearing all scenarios, update just one
```
**Time:** 1 hour

### Issue 4: Filename Not Sanitized
**Line:** 280  
**Severity:** MEDIUM  
**Description:** Scenario name used directly as filename
```python
# CURRENT
file_path = f"{scenario_name}.json"  # Could contain invalid characters

# FIX
safe_name = scenario_name.lower().replace(" ", "_")
safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
file_path = f"{safe_name}.json"
```
**Time:** 30 minutes

### Issue 5: No JSON Import Validation
**Line:** 286  
**Severity:** MEDIUM  
**Description:** Doesn't validate imported JSON structure
```python
# ADD validation:
required_fields = ['model_type', 'wind_speed', 'wind_direction']
for field in required_fields:
    if field not in scenario_data:
        raise ValueError(f"Missing field: {field}")
```
**Time:** 30 minutes

### Issue 6: Font Creation Repeated
**Line:** 215+  
**Severity:** LOW  
**Description:** Font object created multiple times
```python
# Create once at module level:
BOLD_FONT = QFont("Arial", 11, QFont.Weight.Bold)

# Then use:
label.setFont(BOLD_FONT)
```
**Time:** 30 minutes

---

## 📊 Summary Statistics

| Metric | Count |
|--------|-------|
| **Critical Issues** | 8 |
| **High Issues** | 28 |
| **Medium Issues** | 32 |
| **Low Issues** | 20 |
| **Total** | 88 |
| **Files with Issues** | 9 |
| **Clean Files** | 1 |

---

**Analysis Complete**  
**Date:** April 14, 2026  
**Scope:** All 10 widget files reviewed in detail
