"""Wind Settings Widget - Wind configuration and parameters.

Allows users to:
- Enable/disable wind simulation
- Select wind model type (constant, logarithmic, power law, gust)
- Configure wind parameters (speed, direction, altitude effects)
- View wind model information and preview
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QCheckBox,
    QPushButton, QGroupBox, QFormLayout, QComboBox, QSpinBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.widgets import BaseWidget
from models.app_state import ApplicationState
from src.models.state import StateProvider
from src.utils.event_bus import EventType, publish
from typing import Optional
from src.config import Constants
from src.utils.wind_utils import create_wind_model_from_state, log_wind_config
from typing import Tuple, Dict, Any
import logging
import numpy as np

logger = logging.getLogger(__name__)


class WindSettingsWidget(BaseWidget):
    """Wind configuration widget for rocket simulations."""
    
    # Signal to notify main window of wind changes
    wind_changed = pyqtSignal()
    
    # Valid wind model types
    VALID_MODELS = {'constant', 'logarithmic', 'power_law', 'gust'}
    
    @staticmethod
    def validate_wind_parameters(model_type: str, params: dict) -> Tuple[bool, str]:
        """Validate wind model parameters.
        
        Args:
            model_type (str): Wind model type
            params (dict): Parameter dict with wind settings
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        
        Validates:
            - model_type is in VALID_MODELS
            - wind_speed >= 0
            - wind_direction in [0, 360)
            - wind_reference_height > 0
            - Model-specific parameters exist and are in valid ranges
        """
        if model_type not in WindSettingsWidget.VALID_MODELS:
            return False, f"Invalid wind model: {model_type}"
        
        try:
            wind_speed = float(params.get(Constants.StateKeys.WIND_SPEED, 0))
            wind_dir = float(params.get(Constants.StateKeys.WIND_DIRECTION, 0))
            ref_height = float(params.get(Constants.StateKeys.WIND_REFERENCE_HEIGHT, 10))
        except (TypeError, ValueError):
            return False, "Wind parameters must be numeric"
        
        if wind_speed < 0:
            return False, "Wind speed cannot be negative"
        if wind_speed > 100:
            return False, "Wind speed > 100 m/s is unrealistic"
        
        if not (0 <= wind_dir < 360):
            return False, "Wind direction must be in [0, 360)"
        
        if ref_height <= 0:
            return False, "Reference height must be positive"
        if ref_height > 10000:
            return False, "Reference height > 10000 m is unrealistic"
        
        # Model-specific validation
        if model_type in ['logarithmic', 'power_law']:
            roughness = float(params.get(Constants.StateKeys.WIND_ROUGHNESS_LENGTH, 0.1))
            if roughness < 0.001 or roughness > 10:
                return False, "Roughness length should be in [0.001, 10] m"
        
        if model_type == 'power_law':
            exponent = float(params.get(Constants.StateKeys.WIND_EXPONENT, 0.2))
            if not (0.05 <= exponent <= 0.5):
                return False, "Power law exponent should be in [0.05, 0.5]"
        
        if model_type == 'gust':
            intensity = float(params.get(Constants.StateKeys.WIND_GUST_INTENSITY, 0.1))
            length = float(params.get(Constants.StateKeys.WIND_GUST_LENGTH_SCALE, 300))
            if not (0 <= intensity <= 1):
                return False, "Gust intensity must be in [0, 1]"
            if length < 10 or length > 10000:
                return False, "Gust length scale should be in [10, 10000] m"
        
        return True, ""
    
    def __init__(self, state: Optional[StateProvider] = None, parent=None):
        super().__init__(state=state, parent=parent)
        self.wind_model = None
        self.init_ui()
        self.load_wind_settings()
    
    def init_ui(self):
        """Initialize the wind settings widget UI."""
        main_layout = QVBoxLayout()
        
        # ===== WIND ENABLE/DISABLE =====
        control_group = QGroupBox("Wind Simulation Control")
        control_layout = QFormLayout()
        
        self.wind_enabled_check = QCheckBox("Enable Wind Simulation")
        self.wind_enabled_check.setChecked(self.state.get(Constants.StateKeys.WIND_ENABLED, False))
        self.wind_enabled_check.stateChanged.connect(self.on_wind_enabled_changed)
        control_layout.addRow(self.wind_enabled_check)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # ===== WIND MODEL SELECTION =====
        model_group = QGroupBox("Wind Model Selection")
        model_layout = QFormLayout()
        
        model_layout.addRow(QLabel("Wind Model Type:"))
        self.wind_model_combo = QComboBox()
        self.wind_model_combo.addItems([
            'constant',
            'logarithmic',
            'power_law',
            'gust'
        ])
        self.wind_model_combo.setCurrentText(self.state.get(Constants.StateKeys.WIND_MODEL_TYPE, 'logarithmic'))
        self.wind_model_combo.currentTextChanged.connect(self.on_wind_model_changed)
        model_layout.addRow("Model Type:", self.wind_model_combo)
        
        model_group.setLayout(model_layout)
        main_layout.addWidget(model_group)
        
        # ===== WIND PARAMETERS TAB WIDGET =====
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Common Parameters
        self.tabs.addTab(self._create_common_params_tab(), "Common Parameters")
        
        # Tab 2: Model-Specific Parameters
        self.tabs.addTab(self._create_model_specific_tab(), "Model Parameters")
        
        # Tab 3: Wind Preview
        self.tabs.addTab(self._create_preview_tab(), "Preview")
        
        # ===== BUTTONS =====
        button_layout = QHBoxLayout()
        
        update_button = QPushButton("🔄 Update Wind Model")
        update_button.clicked.connect(self.update_wind_model)
        button_layout.addWidget(update_button)
        
        info_button = QPushButton("ℹ️ Wind Information")
        info_button.clicked.connect(self.show_wind_info)
        button_layout.addWidget(info_button)
        
        reset_button = QPushButton("🔄 Reset to Default")
        reset_button.clicked.connect(self.reset_to_default)
        button_layout.addWidget(reset_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def _create_common_params_tab(self):
        """Create tab for common wind parameters."""
        widget = QWidget()
        layout = QFormLayout()
        
        # Wind speed
        self.wind_speed_spin = QDoubleSpinBox()
        self.wind_speed_spin.setRange(Constants.Wind.MIN_WIND_SPEED, Constants.Wind.MAX_WIND_SPEED)
        self.wind_speed_spin.setValue(self.state.get(Constants.StateKeys.WIND_SPEED, Constants.Wind.DEFAULT_WIND_SPEED))
        self.wind_speed_spin.setSuffix(" m/s")
        self.wind_speed_spin.setSingleStep(0.5)
        self.wind_speed_spin.valueChanged.connect(self.on_parameter_changed)
        layout.addRow("Wind Speed:", self.wind_speed_spin)
        
        # Wind direction (FROM)
        self.wind_direction_spin = QDoubleSpinBox()
        self.wind_direction_spin.setRange(Constants.Wind.MIN_WIND_DIRECTION, Constants.Wind.MAX_WIND_DIRECTION)
        self.wind_direction_spin.setValue(self.state.get(Constants.StateKeys.WIND_DIRECTION, Constants.Wind.DEFAULT_WIND_DIRECTION))
        self.wind_direction_spin.setSuffix("°")
        self.wind_direction_spin.setSingleStep(1.0)
        self.wind_direction_spin.valueChanged.connect(self.on_parameter_changed)
        layout.addRow("Wind Direction (FROM):", self.wind_direction_spin)
        
        # Reference height (for wind profiles)
        self.wind_ref_height_spin = QDoubleSpinBox()
        self.wind_ref_height_spin.setRange(Constants.Wind.MIN_REFERENCE_HEIGHT, Constants.Wind.MAX_REFERENCE_HEIGHT)
        self.wind_ref_height_spin.setValue(self.state.get(Constants.StateKeys.WIND_REFERENCE_HEIGHT, Constants.Wind.DEFAULT_REFERENCE_HEIGHT))
        self.wind_ref_height_spin.setSuffix(" m")
        self.wind_ref_height_spin.setSingleStep(1.0)
        self.wind_ref_height_spin.valueChanged.connect(self.on_parameter_changed)
        layout.addRow("Reference Height:", self.wind_ref_height_spin)
        
        widget.setLayout(layout)
        return widget
    
    def _create_model_specific_tab(self):
        """Create tab for model-specific parameters."""
        widget = QWidget()
        layout = QFormLayout()
        
        # Logarithmic/Power Law: Roughness length or exponent
        self.wind_roughness_spin = QDoubleSpinBox()
        self.wind_roughness_spin.setRange(Constants.Wind.MIN_ROUGHNESS, Constants.Wind.MAX_ROUGHNESS)
        self.wind_roughness_spin.setValue(self.state.get(Constants.StateKeys.WIND_ROUGHNESS_LENGTH, Constants.Wind.DEFAULT_ROUGHNESS))
        self.wind_roughness_spin.setSuffix(" m")
        self.wind_roughness_spin.setSingleStep(0.01)
        self.wind_roughness_spin.valueChanged.connect(self.on_parameter_changed)
        self.roughness_label = QLabel("Roughness Length (z₀):")
        layout.addRow(self.roughness_label, self.wind_roughness_spin)
        
        # Power law exponent
        self.wind_exponent_spin = QDoubleSpinBox()
        self.wind_exponent_spin.setRange(Constants.Wind.MIN_POWER_LAW_EXPONENT, Constants.Wind.MAX_POWER_LAW_EXPONENT)
        self.wind_exponent_spin.setValue(self.state.get(Constants.StateKeys.WIND_EXPONENT, Constants.Wind.DEFAULT_POWER_LAW_EXPONENT))
        self.wind_exponent_spin.setSingleStep(0.01)
        self.exponent_label = QLabel("Power Law Exponent (α):")
        layout.addRow(self.exponent_label, self.wind_exponent_spin)
        self.wind_exponent_spin.valueChanged.connect(self.on_parameter_changed)
        
        # Gust parameters
        self.wind_gust_intensity_spin = QDoubleSpinBox()
        self.wind_gust_intensity_spin.setRange(Constants.Wind.MIN_GUST_INTENSITY, Constants.Wind.MAX_GUST_INTENSITY)
        self.wind_gust_intensity_spin.setValue(self.state.get(Constants.StateKeys.WIND_GUST_INTENSITY, Constants.Wind.DEFAULT_GUST_INTENSITY))
        self.wind_gust_intensity_spin.setSingleStep(0.05)
        self.gust_intensity_label = QLabel("Gust Intensity (I_u):")
        layout.addRow(self.gust_intensity_label, self.wind_gust_intensity_spin)
        self.wind_gust_intensity_spin.valueChanged.connect(self.on_parameter_changed)
        
        self.wind_gust_length_spin = QDoubleSpinBox()
        self.wind_gust_length_spin.setRange(Constants.Wind.MIN_GUST_LENGTH, Constants.Wind.MAX_GUST_LENGTH)
        self.wind_gust_length_spin.setValue(self.state.get(Constants.StateKeys.WIND_GUST_LENGTH_SCALE, Constants.Wind.DEFAULT_GUST_LENGTH))
        self.wind_gust_length_spin.setSuffix(" m")
        self.wind_gust_length_spin.setSingleStep(10.0)
        self.gust_length_label = QLabel("Gust Length Scale (L_u):")
        layout.addRow(self.gust_length_label, self.wind_gust_length_spin)
        self.wind_gust_length_spin.valueChanged.connect(self.on_parameter_changed)
        
        widget.setLayout(layout)
        return widget
    
    def _create_preview_tab(self):
        """Create wind preview tab showing wind profile."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Wind profile table
        layout.addWidget(QLabel("Wind Velocity Profile at Different Altitudes:"))
        
        self.wind_table = QTableWidget(0, 2)
        self.wind_table.setHorizontalHeaderLabels(["Altitude (m)", "Wind Speed (m/s)"])
        self.wind_table.setColumnWidth(0, 150)
        self.wind_table.setColumnWidth(1, 150)
        layout.addWidget(self.wind_table)
        
        # Wind vector visualization
        layout.addWidget(QLabel("\nWind Vector Components at Selected Altitude:"))
        
        altitude_layout = QHBoxLayout()
        altitude_layout.addWidget(QLabel("Altitude:"))
        self.preview_altitude_spin = QDoubleSpinBox()
        self.preview_altitude_spin.setRange(0, 10000)
        self.preview_altitude_spin.setValue(1000)
        self.preview_altitude_spin.setSuffix(" m")
        self.preview_altitude_spin.valueChanged.connect(self.update_preview)
        altitude_layout.addWidget(self.preview_altitude_spin)
        
        preview_button = QPushButton("Update Preview")
        preview_button.clicked.connect(self.update_preview)
        altitude_layout.addWidget(preview_button)
        layout.addLayout(altitude_layout)
        
        self.wind_info_text = QTextEdit()
        self.wind_info_text.setReadOnly(True)
        self.wind_info_text.setMaximumHeight(150)
        layout.addWidget(self.wind_info_text)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def load_wind_settings(self):
        """Load current wind settings from app state and populate UI.
        
        Reads all wind parameters from ApplicationState and updates UI controls.
        Calls update_wind_model_ui() to show/hide model-specific parameters.
        Calls update_preview() to populate wind profile table with initial values.
        
        Logs errors but continues operation if settings load fails.
        """
        try:
            # Update UI with current state values
            self.wind_enabled_check.setChecked(self.state.get(Constants.StateKeys.WIND_ENABLED, False))
            self.wind_model_combo.setCurrentText(self.state.get(Constants.StateKeys.WIND_MODEL_TYPE, 'logarithmic'))
            self.wind_speed_spin.setValue(self.state.get(Constants.StateKeys.WIND_SPEED, Constants.Wind.DEFAULT_WIND_SPEED))
            self.wind_direction_spin.setValue(self.state.get(Constants.StateKeys.WIND_DIRECTION, Constants.Wind.DEFAULT_WIND_DIRECTION))
            self.wind_ref_height_spin.setValue(self.state.get(Constants.StateKeys.WIND_REFERENCE_HEIGHT, Constants.Wind.DEFAULT_REFERENCE_HEIGHT))
            self.wind_roughness_spin.setValue(self.state.get(Constants.StateKeys.WIND_ROUGHNESS_LENGTH, Constants.Wind.DEFAULT_ROUGHNESS))
            self.wind_exponent_spin.setValue(self.state.get(Constants.StateKeys.WIND_EXPONENT, Constants.Wind.DEFAULT_POWER_LAW_EXPONENT))
            self.wind_gust_intensity_spin.setValue(self.state.get(Constants.StateKeys.WIND_GUST_INTENSITY, Constants.Wind.DEFAULT_GUST_INTENSITY))
            self.wind_gust_length_spin.setValue(self.state.get(Constants.StateKeys.WIND_GUST_LENGTH_SCALE, Constants.Wind.DEFAULT_GUST_LENGTH))
            
            # Update wind model UI
            self.update_wind_model_ui()
            # Populate preview table with initial values
            self.update_preview()
            
            logger.info("Wind settings loaded successfully")
        except Exception as e:
            logger.error(f"Error loading wind settings: {e}")
    
    def on_wind_enabled_changed(self, state):
        """Handle wind enable/disable toggle.
        
        Args:
            state: Qt checkbox state signal (ignored, uses button checked status).
        
        Updates ApplicationState wind_enabled flag. Enables/disables all other
        wind controls based on checkbox state. Emits wind_changed signal.
        """
        enabled = self.wind_enabled_check.isChecked()
        self.state.set(Constants.StateKeys.WIND_ENABLED, enabled)
        
        # Enable/disable other controls
        self.wind_model_combo.setEnabled(enabled)
        self.wind_speed_spin.setEnabled(enabled)
        self.wind_direction_spin.setEnabled(enabled)
        self.wind_ref_height_spin.setEnabled(enabled)
        self.wind_roughness_spin.setEnabled(enabled)
        self.wind_exponent_spin.setEnabled(enabled)
        self.wind_gust_intensity_spin.setEnabled(enabled)
        self.wind_gust_length_spin.setEnabled(enabled)
        
        logger.info(f"Wind simulation {'enabled' if enabled else 'disabled'}")
        self.wind_changed.emit()
    
    def on_wind_model_changed(self, model_type):
        """Handle wind model selection change.
        
        Args:
            model_type (str): Selected model type (constant, logarithmic, power_law, gust).
        
        Updates ApplicationState wind_model_type. Calls update_wind_model_ui() to
        show/hide model-specific parameters. Emits wind_changed signal.
        """
        self.state.set(Constants.StateKeys.WIND_MODEL_TYPE, model_type)
        self.update_wind_model_ui()
        logger.info(f"Wind model changed to: {model_type}")
        self.wind_changed.emit()
        
        # Publish wind scenario selected event
        publish(EventType.WIND_SCENARIO_SELECTED, {
            'model_type': model_type
        })
        logger.info(f"Published WIND_SCENARIO_SELECTED event for: {model_type}")
    
    def on_parameter_changed(self, value):
        """Handle wind parameter changes from spinboxes.
        
        Args:
            value: Spinbox signal value (unused, reads directly from spinboxes).
        
        Syncs all wind parameters to ApplicationState. Emits wind_changed signal.
        Called when wind speed, direction, reference height, roughness, exponent,
        gust intensity, or gust length scale changes.
        """
        # Update state with new values
        self.state.set(Constants.StateKeys.WIND_SPEED, self.wind_speed_spin.value())
        self.state.set(Constants.StateKeys.WIND_SPEED_REF, self.wind_speed_spin.value())
        self.state.set(Constants.StateKeys.WIND_DIRECTION, self.wind_direction_spin.value())
        self.state.set(Constants.StateKeys.WIND_REFERENCE_HEIGHT, self.wind_ref_height_spin.value())
        self.state.set(Constants.StateKeys.WIND_ROUGHNESS_LENGTH, self.wind_roughness_spin.value())
        self.state.set(Constants.StateKeys.WIND_EXPONENT, self.wind_exponent_spin.value())
        self.state.set(Constants.StateKeys.WIND_GUST_INTENSITY, self.wind_gust_intensity_spin.value())
        self.state.set(Constants.StateKeys.WIND_GUST_LENGTH_SCALE, self.wind_gust_length_spin.value())
        
        self.wind_changed.emit()
        
        # Publish wind settings changed event
        wind_data = {
            'wind_speed': self.wind_speed_spin.value(),
            'wind_direction': self.wind_direction_spin.value(),
            'reference_height': self.wind_ref_height_spin.value(),
            'model_type': self.wind_model_combo.currentText(),
            'roughness_length': self.wind_roughness_spin.value(),
            'exponent': self.wind_exponent_spin.value(),
            'gust_intensity': self.wind_gust_intensity_spin.value(),
            'gust_length_scale': self.wind_gust_length_spin.value()
        }
        publish(EventType.WIND_SETTINGS_CHANGED, wind_data)
        logger.debug(f"Published WIND_SETTINGS_CHANGED event")
    
    def update_wind_model_ui(self):
        """Update UI visibility based on wind model type.
        
        Hides all model-specific parameter controls by default, then shows
        only the controls relevant to the selected model:
        - logarithmic: shows roughness length (z₀)
        - power_law: shows power law exponent (α)
        - gust: shows gust intensity and length scale
        - constant: shows no additional parameters
        """
        model_type = self.wind_model_combo.currentText()
        
        # Hide all model-specific controls by default
        self.roughness_label.hide()
        self.wind_roughness_spin.hide()
        self.exponent_label.hide()
        self.wind_exponent_spin.hide()
        self.gust_intensity_label.hide()
        self.wind_gust_intensity_spin.hide()
        self.gust_length_label.hide()
        self.wind_gust_length_spin.hide()
        
        # Show relevant controls based on model
        if model_type == 'logarithmic':
            self.roughness_label.show()
            self.wind_roughness_spin.show()
        elif model_type == 'power_law':
            self.exponent_label.show()
            self.wind_exponent_spin.show()
        elif model_type == 'gust':
            self.gust_intensity_label.show()
            self.wind_gust_intensity_spin.show()
            self.gust_length_label.show()
            self.wind_gust_length_spin.show()
        # 'constant' model has no additional parameters
    
    def update_wind_model(self):
        """Update and validate wind model from current state.
        
        Creates wind model using create_wind_model_from_state() utility.
        Logs wind configuration if model created successfully.
        Updates preview table with new model data.
        
        Displays information dialog if model created successfully, or warning
        dialog if wind simulation is disabled.
        
        Raises:
            Exception: Logs and displays error dialog if model creation fails.
        """
        try:
            # Validate parameters before creating model
            model_type = self.wind_model_combo.currentText()
            is_valid, error_msg = self.validate_wind_parameters(model_type, self.state.get_all())
            
            if not is_valid:
                QMessageBox.warning(self, "Parameter Validation Error", error_msg)
                logger.warning(f"Wind parameter validation failed: {error_msg}")
                return
            
            self.wind_model = create_wind_model_from_state(self.state.get_all())
            
            if self.wind_model is not None:
                log_wind_config(self.state.get_all(), self.wind_model)
                QMessageBox.information(
                    self,
                    "Wind Model Updated",
                    f"Wind model '{self.wind_model_combo.currentText()}' updated successfully."
                )
                self.update_preview()
            else:
                QMessageBox.warning(self, "Wind Disabled", "Wind simulation is disabled.")
                self.wind_table.setRowCount(0)
            
            logger.info("Wind model updated successfully")
        except Exception as e:
            logger.error(f"Error updating wind model: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update wind model: {str(e)}")
    
    def update_preview(self):
        """Update wind preview table and vector components display.
        
        Generates wind velocity profile at altitudes [0, 100, 500, 1000, 2000, 5000, 10000] m.
        Populates wind_table with altitude and calculated wind speed.
        Shows wind vector components (East u, North v, Up w) at selected preview altitude.
        
        Validates wind enabled and model creation before populating table.
        Row-level error handling fills cells with "Error" if wind calculation fails.
        Applies styling to info text based on success/error state.
        
        Logs errors encountered during preview generation.
        """
        try:
            # Check if wind is enabled
            if not self.wind_enabled_check.isChecked():
                self.wind_table.setRowCount(0)
                self.wind_info_text.setText("Wind simulation is disabled.\nEnable wind to see preview.")
                return
            
            # Create wind model from current state
            self.wind_model = create_wind_model_from_state(self.state.get_all())
            if self.wind_model is None:
                self.wind_table.setRowCount(0)
                self.wind_info_text.setText("Unable to create wind model with current settings.")
                return
            
            # Generate wind profiles at different altitudes
            altitudes = [0, 100, 500, 1000, 2000, 5000, 10000]
            self.wind_table.setRowCount(len(altitudes))
            
            for row, alt in enumerate(altitudes):
                try:
                    wind_vec = self.wind_model.get_wind_vector(alt)
                    wind_speed = np.linalg.norm(wind_vec)
                    
                    # Altitude column
                    alt_item = QTableWidgetItem(f"{alt}")
                    alt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.wind_table.setItem(row, 0, alt_item)
                    
                    # Wind speed column
                    speed_item = QTableWidgetItem(f"{wind_speed:.2f}")
                    speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.wind_table.setItem(row, 1, speed_item)
                except Exception as row_error:
                    logger.warning(f"Error calculating wind at {alt}m: {row_error}")
                    # Fill with error placeholder
                    self.wind_table.setItem(row, 0, QTableWidgetItem(f"{alt}"))
                    self.wind_table.setItem(row, 1, QTableWidgetItem("Error"))
            
            # Show wind vector at selected altitude
            preview_alt = self.preview_altitude_spin.value()
            wind_vec = self.wind_model.get_wind_vector(preview_alt)
            wind_speed = np.linalg.norm(wind_vec)
            wind_direction = self.wind_model.get_wind_direction_at_altitude(preview_alt)
            
            # Format wind vector info with model type
            model_type = self.wind_model_combo.currentText()
            info_text = (
                f"Wind Model: {model_type.replace('_', ' ').title()}\n"
                f"Altitude: {preview_alt:.1f} m\n"
                f"Wind Speed: {wind_speed:.2f} m/s\n"
                f"Direction FROM: {wind_direction:.1f}°\n\n"
                f"Vector Components (East, North, Up):\n"
                f"  East (u):  {wind_vec[0]:+.3f} m/s\n"
                f"  North (v): {wind_vec[1]:+.3f} m/s\n"
                f"  Up (w):    {wind_vec[2]:+.3f} m/s"
            )
            self.wind_info_text.setText(info_text)
            self.wind_info_text.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
            
            logger.info(f"Wind preview updated for altitude {preview_alt}m")
            
        except Exception as e:
            logger.error(f"Error updating wind preview: {e}")
            self.wind_info_text.setText(f"Error generating preview:\n{str(e)}")
            self.wind_info_text.setStyleSheet("background-color: #ffe0e0; padding: 5px; color: #cc0000;")
    
    def show_wind_info(self):
        """Show wind model information in dialog.
        
        Displays comprehensive wind model details by calling wind_model.get_info().
        Shows warning if wind is disabled, or error dialog if model creation fails.
        
        Raises:
            Exception: Logs and displays error dialog if info retrieval fails.
        """
        try:
            if not self.wind_enabled_check.isChecked():
                QMessageBox.information(self, "Wind Info", "Wind simulation is currently disabled.")
                return
            
            self.wind_model = create_wind_model_from_state(self.state.get_all())
            if self.wind_model is None:
                QMessageBox.warning(self, "Wind Info", "Failed to create wind model.")
                return
            
            info = self.wind_model.get_info()
            info_text = "Wind Model Information:\n\n"
            for key, value in info.items():
                info_text += f"{key}: {value}\n"
            
            QMessageBox.information(self, "Wind Model Info", info_text)
        except Exception as e:
            logger.error(f"Error showing wind info: {e}")
            QMessageBox.critical(self, "Error", f"Failed to get wind info: {str(e)}")
    
    def reset_to_default(self):
        """Reset all wind settings to default values with confirmation.
        
        Prompts user for confirmation before resetting. Sets:
        - wind_enabled: False
        - wind_model_type: logarithmic
        - wind_speed: 0.0 m/s
        - wind_direction: 0.0°
        - wind_reference_height: 10.0 m
        - wind_roughness_length: 0.1 m
        - wind_exponent: 0.2
        - wind_gust_intensity: 0.1
        - wind_gust_length_scale: 300.0 m
        
        Emits wind_changed signal after reset. Logs reset action.
        """
        reply = QMessageBox.question(
            self,
            "Reset Wind Settings",
            "Reset all wind settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.wind_enabled_check.setChecked(False)
            self.wind_model_combo.setCurrentText('logarithmic')
            self.wind_speed_spin.setValue(0.0)
            self.wind_direction_spin.setValue(0.0)
            self.wind_ref_height_spin.setValue(10.0)
            self.wind_roughness_spin.setValue(0.1)
            self.wind_exponent_spin.setValue(0.2)
            self.wind_gust_intensity_spin.setValue(0.1)
            self.wind_gust_length_spin.setValue(300.0)
            
            logger.info("Wind settings reset to defaults")
            self.wind_changed.emit()
