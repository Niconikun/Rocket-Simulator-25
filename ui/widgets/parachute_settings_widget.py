"""Parachute Settings Widget - Parachute configuration."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QCheckBox,
    QPushButton, QGroupBox, QFormLayout, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt
from models.app_state import ApplicationState
import logging

logger = logging.getLogger(__name__)


class ParachuteSettingsWidget(QWidget):
    """
    Parachute configuration widget.
    
    Replaces pages/07_parachute_settings.py
    Allows users to:
    - Enable/disable parachute deployment
    - Configure deployment altitude
    - Set parachute area and parameters
    - View parachute descent simulation
    """
    
    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the parachute settings widget UI."""
        main_layout = QVBoxLayout()
        
        # ===== PARACHUTE ENABLE/DISABLE =====
        enable_group = QGroupBox("Parachute Control")
        enable_layout = QFormLayout()
        
        self.parachute_enabled_check = QCheckBox("Enable Parachute Deployment")
        self.parachute_enabled_check.setChecked(
            self.state.get('parachute_enabled', False)
        )
        self.parachute_enabled_check.stateChanged.connect(self.on_parachute_enabled)
        enable_layout.addRow(self.parachute_enabled_check)
        
        enable_group.setLayout(enable_layout)
        main_layout.addWidget(enable_group)
        
        # ===== DEPLOYMENT SETTINGS =====
        deployment_group = QGroupBox("Deployment Settings")
        deployment_layout = QFormLayout()
        
        # Deployment altitude
        self.deployment_altitude = QDoubleSpinBox()
        self.deployment_altitude.setRange(100, 10000)
        self.deployment_altitude.setValue(
            self.state.get('parachute_deployment_altitude', 300.0)
        )
        self.deployment_altitude.setSuffix(" m")
        self.deployment_altitude.valueChanged.connect(
            lambda v: self.state.set('parachute_deployment_altitude', v)
        )
        deployment_layout.addRow("Deployment Altitude:", self.deployment_altitude)
        
        # Deployment type
        self.deployment_type = QComboBox()
        self.deployment_type.addItems(["Altitude-triggered", "Acceleration-triggered", "Time-triggered"])
        deployment_layout.addRow("Deployment Type:", self.deployment_type)
        
        deployment_group.setLayout(deployment_layout)
        main_layout.addWidget(deployment_group)
        
        # ===== PARACHUTE PROPERTIES =====
        props_group = QGroupBox("Parachute Properties")
        props_layout = QFormLayout()
        
        # Canopy area
        self.canopy_area = QDoubleSpinBox()
        self.canopy_area.setRange(0.1, 100)
        self.canopy_area.setDecimals(2)
        self.canopy_area.setValue(
            self.state.get('parachute_area', 1.0)
        )
        self.canopy_area.setSuffix(" m²")
        self.canopy_area.valueChanged.connect(
            lambda v: self.state.set('parachute_area', v)
        )
        props_layout.addRow("Canopy Area:", self.canopy_area)
        
        # Drag coefficient
        self.drag_coefficient = QDoubleSpinBox()
        self.drag_coefficient.setRange(0.5, 3.0)
        self.drag_coefficient.setDecimals(2)
        self.drag_coefficient.setSingleStep(0.1)
        self.drag_coefficient.setValue(
            self.state.get('parachute_drag_coefficient', 1.5)
        )
        self.drag_coefficient.valueChanged.connect(
            lambda v: self.state.set('parachute_drag_coefficient', v)
        )
        props_layout.addRow("Drag Coefficient (Cd):", self.drag_coefficient)
        
        # Inflation time
        self.inflation_time = QDoubleSpinBox()
        self.inflation_time.setRange(0.0, 10.0)
        self.inflation_time.setDecimals(2)
        self.inflation_time.setSuffix(" s")
        self.inflation_time.setValue(1.0)
        props_layout.addRow("Inflation Time:", self.inflation_time)
        
        # Pack altitude
        self.pack_altitude = QDoubleSpinBox()
        self.pack_altitude.setRange(100, 20000)
        self.pack_altitude.setValue(500.0)
        self.pack_altitude.setSuffix(" m")
        props_layout.addRow("Pack Altitude Threshold:", self.pack_altitude)
        
        props_group.setLayout(props_layout)
        main_layout.addWidget(props_group)
        
        # ===== DESCENT ANALYSIS =====
        descent_group = QGroupBox("Descent Analysis")
        descent_layout = QVBoxLayout()
        
        # Calculate descent time
        button_layout = QHBoxLayout()
        
        calculate_button = QPushButton("📊 Calculate Descent")
        calculate_button.clicked.connect(self.calculate_descent)
        button_layout.addWidget(calculate_button)
        
        abort_button = QPushButton("🛑 Abort Deployment")
        abort_button.clicked.connect(self.abort_deployment)
        button_layout.addWidget(abort_button)
        
        descent_layout.addLayout(button_layout)
        
        # Descent results
        results_layout = QFormLayout()
        
        self.descent_time_label = QLabel("Not calculated")
        results_layout.addRow("Descent Time:", self.descent_time_label)
        
        self.landing_speed_label = QLabel("Not calculated")
        results_layout.addRow("Landing Speed:", self.landing_speed_label)
        
        self.descent_distance_label = QLabel("Not calculated")
        results_layout.addRow("Horizontal Drift:", self.descent_distance_label)
        
        descent_layout.addLayout(results_layout)
        
        descent_group.setLayout(descent_layout)
        main_layout.addWidget(descent_group)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
    
    def on_parachute_enabled(self, state):
        """Handle parachute enable/disable."""
        enabled = state == Qt.CheckState.Checked.value
        self.state.set('parachute_enabled', enabled)
        self.enable_parachute_controls(enabled)
        logger.info(f"Parachute {'enabled' if enabled else 'disabled'}")
    
    def enable_parachute_controls(self, enabled: bool):
        """Enable or disable parachute control widgets."""
        self.deployment_altitude.setEnabled(enabled)
        self.deployment_type.setEnabled(enabled)
        self.canopy_area.setEnabled(enabled)
        self.drag_coefficient.setEnabled(enabled)
        self.inflation_time.setEnabled(enabled)
        self.pack_altitude.setEnabled(enabled)
    
    def calculate_descent(self):
        """Calculate parachute descent parameters."""
        if not self.parachute_enabled_check.isChecked():
            QMessageBox.warning(self, "Warning", "Parachute is not enabled")
            return
        
        # Placeholder calculation
        descent_time = 45.5  # seconds
        landing_speed = 5.2  # m/s
        horizontal_drift = 150.0  # meters
        
        self.descent_time_label.setText(f"{descent_time:.1f} s")
        self.landing_speed_label.setText(f"{landing_speed:.2f} m/s")
        self.descent_distance_label.setText(f"{horizontal_drift:.1f} m")
        
        QMessageBox.information(
            self, "Descent Calculated",
            f"Descent Time: {descent_time:.1f} s\n"
            f"Landing Speed: {landing_speed:.2f} m/s\n"
            f"Horizontal Drift: {horizontal_drift:.1f} m"
        )
        logger.info("Parachute descent calculated")
    
    def abort_deployment(self):
        """Abort parachute deployment."""
        reply = QMessageBox.question(
            self, "Abort Deployment",
            "Are you sure you want to abort parachute deployment?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.parachute_enabled_check.setChecked(False)
            logger.warning("Parachute deployment aborted")
