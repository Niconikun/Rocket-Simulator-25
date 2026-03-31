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
from models.app_state import ApplicationState
from src.utils.wind_utils import create_wind_model_from_state, log_wind_config
import logging
import numpy as np

logger = logging.getLogger(__name__)


class WindSettingsWidget(QWidget):
    """Wind configuration widget for rocket simulations."""
    
    # Signal to notify main window of wind changes
    wind_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
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
        self.wind_enabled_check.setChecked(self.state.get('wind_enabled', False))
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
        self.wind_model_combo.setCurrentText(self.state.get('wind_model_type', 'logarithmic'))
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
        self.wind_speed_spin.setRange(0.0, 50.0)
        self.wind_speed_spin.setValue(self.state.get('wind_speed', 0.0))
        self.wind_speed_spin.setSuffix(" m/s")
        self.wind_speed_spin.setSingleStep(0.5)
        self.wind_speed_spin.valueChanged.connect(self.on_parameter_changed)
        layout.addRow("Wind Speed:", self.wind_speed_spin)
        
        # Wind direction (FROM)
        self.wind_direction_spin = QDoubleSpinBox()
        self.wind_direction_spin.setRange(0.0, 360.0)
        self.wind_direction_spin.setValue(self.state.get('wind_direction', 0.0))
        self.wind_direction_spin.setSuffix("°")
        self.wind_direction_spin.setSingleStep(1.0)
        self.wind_direction_spin.valueChanged.connect(self.on_parameter_changed)
        layout.addRow("Wind Direction (FROM):", self.wind_direction_spin)
        
        # Reference height (for wind profiles)
        self.wind_ref_height_spin = QDoubleSpinBox()
        self.wind_ref_height_spin.setRange(0.1, 1000.0)
        self.wind_ref_height_spin.setValue(self.state.get('wind_reference_height', 10.0))
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
        self.wind_roughness_spin.setRange(0.001, 10.0)
        self.wind_roughness_spin.setValue(self.state.get('wind_roughness_length', 0.1))
        self.wind_roughness_spin.setSuffix(" m")
        self.wind_roughness_spin.setSingleStep(0.01)
        self.wind_roughness_spin.valueChanged.connect(self.on_parameter_changed)
        self.roughness_label = QLabel("Roughness Length (z₀):")
        layout.addRow(self.roughness_label, self.wind_roughness_spin)
        
        # Power law exponent
        self.wind_exponent_spin = QDoubleSpinBox()
        self.wind_exponent_spin.setRange(0.05, 0.5)
        self.wind_exponent_spin.setValue(self.state.get('wind_exponent', 0.2))
        self.wind_exponent_spin.setSingleStep(0.01)
        self.exponent_label = QLabel("Power Law Exponent (α):")
        layout.addRow(self.exponent_label, self.wind_exponent_spin)
        self.wind_exponent_spin.valueChanged.connect(self.on_parameter_changed)
        
        # Gust parameters
        self.wind_gust_intensity_spin = QDoubleSpinBox()
        self.wind_gust_intensity_spin.setRange(0.0, 1.0)
        self.wind_gust_intensity_spin.setValue(self.state.get('wind_gust_intensity', 0.1))
        self.wind_gust_intensity_spin.setSingleStep(0.05)
        self.gust_intensity_label = QLabel("Gust Intensity (I_u):")
        layout.addRow(self.gust_intensity_label, self.wind_gust_intensity_spin)
        self.wind_gust_intensity_spin.valueChanged.connect(self.on_parameter_changed)
        
        self.wind_gust_length_spin = QDoubleSpinBox()
        self.wind_gust_length_spin.setRange(10.0, 10000.0)
        self.wind_gust_length_spin.setValue(self.state.get('wind_gust_length_scale', 300.0))
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
        """Load current wind settings from app state."""
        try:
            # Update UI with current state values
            self.wind_enabled_check.setChecked(self.state.get('wind_enabled', False))
            self.wind_model_combo.setCurrentText(self.state.get('wind_model_type', 'logarithmic'))
            self.wind_speed_spin.setValue(self.state.get('wind_speed', 0.0))
            self.wind_direction_spin.setValue(self.state.get('wind_direction', 0.0))
            self.wind_ref_height_spin.setValue(self.state.get('wind_reference_height', 10.0))
            self.wind_roughness_spin.setValue(self.state.get('wind_roughness_length', 0.1))
            self.wind_exponent_spin.setValue(self.state.get('wind_exponent', 0.2))
            self.wind_gust_intensity_spin.setValue(self.state.get('wind_gust_intensity', 0.1))
            self.wind_gust_length_spin.setValue(self.state.get('wind_gust_length_scale', 300.0))
            
            # Update wind model UI
            self.update_wind_model_ui()
            logger.info("Wind settings loaded successfully")
        except Exception as e:
            logger.error(f"Error loading wind settings: {e}")
    
    def on_wind_enabled_changed(self, state):
        """Handle wind enable/disable toggle."""
        enabled = self.wind_enabled_check.isChecked()
        self.state.set('wind_enabled', enabled)
        
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
        """Handle wind model selection change."""
        self.state.set('wind_model_type', model_type)
        self.update_wind_model_ui()
        logger.info(f"Wind model changed to: {model_type}")
        self.wind_changed.emit()
    
    def on_parameter_changed(self, value):
        """Handle wind parameter changes."""
        # Update state with new values
        self.state.set('wind_speed', self.wind_speed_spin.value())
        self.state.set('wind_direction', self.wind_direction_spin.value())
        self.state.set('wind_reference_height', self.wind_ref_height_spin.value())
        self.state.set('wind_roughness_length', self.wind_roughness_spin.value())
        self.state.set('wind_exponent', self.wind_exponent_spin.value())
        self.state.set('wind_gust_intensity', self.wind_gust_intensity_spin.value())
        self.state.set('wind_gust_length_scale', self.wind_gust_length_spin.value())
        
        self.wind_changed.emit()
    
    def update_wind_model_ui(self):
        """Update UI visibility based on wind model type."""
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
        """Update and validate wind model."""
        try:
            self.wind_model = create_wind_model_from_state(self.state._state)
            
            if self.wind_model is not None:
                log_wind_config(self.state._state, self.wind_model)
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
        """Update wind preview table and info."""
        try:
            if not self.wind_enabled_check.isChecked():
                self.wind_table.setRowCount(0)
                self.wind_info_text.setText("Wind simulation is disabled.")
                return
            
            self.wind_model = create_wind_model_from_state(self.state._state)
            if self.wind_model is None:
                self.wind_table.setRowCount(0)
                return
            
            # Generate wind profiles at different altitudes
            altitudes = [0, 100, 500, 1000, 2000, 5000, 10000]
            self.wind_table.setRowCount(len(altitudes))
            
            for row, alt in enumerate(altitudes):
                wind_vec = self.wind_model.get_wind_vector(alt)
                wind_speed = np.linalg.norm(wind_vec)
                
                alt_item = QTableWidgetItem(f"{alt}")
                alt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.wind_table.setItem(row, 0, alt_item)
                
                speed_item = QTableWidgetItem(f"{wind_speed:.2f}")
                speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.wind_table.setItem(row, 1, speed_item)
            
            # Show wind vector at selected altitude
            preview_alt = self.preview_altitude_spin.value()
            wind_vec = self.wind_model.get_wind_vector(preview_alt)
            wind_speed = np.linalg.norm(wind_vec)
            
            info_text = (
                f"Altitude: {preview_alt:.1f} m\n"
                f"Wind Speed: {wind_speed:.2f} m/s\n"
                f"Components (East, North, Up):\n"
                f"  East: {wind_vec[0]:+.2f} m/s\n"
                f"  North: {wind_vec[1]:+.2f} m/s\n"
                f"  Up: {wind_vec[2]:+.2f} m/s\n"
                f"Direction FROM: {self.wind_model.get_wind_direction_at_altitude(preview_alt):.1f}°"
            )
            self.wind_info_text.setText(info_text)
            
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            self.wind_info_text.setText(f"Error: {str(e)}")
    
    def show_wind_info(self):
        """Show wind model information."""
        try:
            if not self.wind_enabled_check.isChecked():
                QMessageBox.information(self, "Wind Info", "Wind simulation is currently disabled.")
                return
            
            self.wind_model = create_wind_model_from_state(self.state._state)
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
        """Reset wind settings to default values."""
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
