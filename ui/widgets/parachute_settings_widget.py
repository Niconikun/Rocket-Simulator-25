"""Parachute Settings Widget - Parachute configuration."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QCheckBox,
    QPushButton, QGroupBox, QFormLayout, QMessageBox, QComboBox, QFileDialog,
    QSpinBox, QPlainTextEdit
)
from PyQt6.QtCore import Qt
from models.app_state import ApplicationState
import logging
import json
import os
from pathlib import Path

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
        self.parachute_configs = {}
        self.current_parachute = None
        self.init_ui()
        self.load_parachute_configs()
    
    def init_ui(self):
        """Initialize the parachute settings widget UI."""
        main_layout = QVBoxLayout()
        
        # ===== PARACHUTE SELECTION =====
        selection_group = QGroupBox("Parachute Selection")
        selection_layout = QHBoxLayout()
        
        selection_layout.addWidget(QLabel("Select Parachute:"))
        self.parachute_combo = QComboBox()
        self.parachute_combo.addItem("Manual")
        self.parachute_combo.currentTextChanged.connect(self.on_parachute_selected)
        selection_layout.addWidget(self.parachute_combo)
        
        load_button = QPushButton("📁 Load File")
        load_button.clicked.connect(self.load_parachute_file)
        selection_layout.addWidget(load_button)
        
        save_button = QPushButton("💾 Save Configuration")
        save_button.clicked.connect(self.save_parachute_config)
        selection_layout.addWidget(save_button)
        
        selection_group.setLayout(selection_layout)
        main_layout.addWidget(selection_group)
        
        # ===== PARACHUTE ENABLE/DISABLE =====
        enable_group = QGroupBox("Parachute Control")
        enable_layout = QFormLayout()
        
        self.parachute_enabled_check = QCheckBox("Enable Main Parachute Deployment")
        self.parachute_enabled_check.setChecked(
            self.state.get('parachute_enabled', False)
        )
        self.parachute_enabled_check.stateChanged.connect(self.on_parachute_enabled)
        enable_layout.addRow(self.parachute_enabled_check)
        
        enable_group.setLayout(enable_layout)
        main_layout.addWidget(enable_group)
        
        # ===== MAIN PARACHUTE DEPLOYMENT SETTINGS =====
        deployment_group = QGroupBox("Main Parachute Configuration")
        deployment_layout = QFormLayout()
        
        # Parachute name
        self.parachute_name = QLabel("Standard Round")
        deployment_layout.addRow("Parachute Name:", self.parachute_name)
        
        # Diameter
        self.parachute_diameter = QDoubleSpinBox()
        self.parachute_diameter.setRange(0.1, 5.0)
        self.parachute_diameter.setDecimals(2)
        self.parachute_diameter.setValue(
            self.state.get('parachute_diameter', 0.6)
        )
        self.parachute_diameter.setSuffix(" m")
        self.parachute_diameter.valueChanged.connect(
            lambda v: self.state.set('parachute_diameter', v)
        )
        deployment_layout.addRow("Canopy Diameter:", self.parachute_diameter)
        
        # Drag coefficient
        self.parachute_cd = QDoubleSpinBox()
        self.parachute_cd.setRange(0.5, 2.5)
        self.parachute_cd.setDecimals(2)
        self.parachute_cd.setSingleStep(0.1)
        self.parachute_cd.setValue(
            self.state.get('parachute_cd', 1.5)
        )
        self.parachute_cd.valueChanged.connect(
            lambda v: self.state.set('parachute_cd', v)
        )
        deployment_layout.addRow("Drag Coefficient (Cd):", self.parachute_cd)
        
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
        deployment_layout.addRow("Deployment Altitude (Threshold):", self.deployment_altitude)
        
        # Minimum velocity
        self.min_velocity = QDoubleSpinBox()
        self.min_velocity.setRange(0, 200)
        self.min_velocity.setValue(
            self.state.get('parachute_min_velocity', 5.0)
        )
        self.min_velocity.setSuffix(" m/s")
        self.min_velocity.valueChanged.connect(
            lambda v: self.state.set('parachute_min_velocity', v)
        )
        deployment_layout.addRow("Min Safe Velocity:", self.min_velocity)
        
        # Maximum velocity
        self.max_velocity = QDoubleSpinBox()
        self.max_velocity.setRange(0, 300)
        self.max_velocity.setValue(
            self.state.get('parachute_max_velocity', 80.0)
        )
        self.max_velocity.setSuffix(" m/s")
        self.max_velocity.valueChanged.connect(
            lambda v: self.state.set('parachute_max_velocity', v)
        )
        deployment_layout.addRow("Max Safe Velocity:", self.max_velocity)
        
        # Inflation time
        self.inflation_time = QDoubleSpinBox()
        self.inflation_time.setRange(0.1, 5.0)
        self.inflation_time.setDecimals(2)
        self.inflation_time.setSuffix(" s")
        self.inflation_time.setValue(
            self.state.get('parachute_inflation_time', 0.5)
        )
        self.inflation_time.valueChanged.connect(
            lambda v: self.state.set('parachute_inflation_time', v)
        )
        deployment_layout.addRow("Inflation Time:", self.inflation_time)
        
        deployment_group.setLayout(deployment_layout)
        main_layout.addWidget(deployment_group)
        
        # ===== DROGUE PARACHUTE SETTINGS =====
        drogue_group = QGroupBox("Drogue Parachute Configuration")
        drogue_layout = QFormLayout()
        
        # Enable drogue
        self.drogue_enabled_check = QCheckBox("Enable Drogue Chute")
        self.drogue_enabled_check.setChecked(
            self.state.get('drogue_enabled', False)
        )
        self.drogue_enabled_check.stateChanged.connect(self.on_drogue_enabled)
        drogue_layout.addRow(self.drogue_enabled_check)
        
        # Drogue diameter
        self.drogue_diameter = QDoubleSpinBox()
        self.drogue_diameter.setRange(0.1, 2.0)
        self.drogue_diameter.setDecimals(2)
        self.drogue_diameter.setValue(
            self.state.get('drogue_diameter', 0.25)
        )
        self.drogue_diameter.setSuffix(" m")
        self.drogue_diameter.setEnabled(self.drogue_enabled_check.isChecked())
        self.drogue_diameter.valueChanged.connect(
            lambda v: self.state.set('drogue_diameter', v)
        )
        drogue_layout.addRow("Drogue Diameter:", self.drogue_diameter)
        
        # Drogue Cd
        self.drogue_cd = QDoubleSpinBox()
        self.drogue_cd.setRange(0.5, 2.5)
        self.drogue_cd.setDecimals(2)
        self.drogue_cd.setSingleStep(0.1)
        self.drogue_cd.setValue(
            self.state.get('drogue_cd', 1.5)
        )
        self.drogue_cd.setEnabled(self.drogue_enabled_check.isChecked())
        self.drogue_cd.valueChanged.connect(
            lambda v: self.state.set('drogue_cd', v)
        )
        drogue_layout.addRow("Drogue Cd:", self.drogue_cd)
        
        # Drogue deployment altitude
        self.drogue_deployment_altitude = QDoubleSpinBox()
        self.drogue_deployment_altitude.setRange(100, 20000)
        self.drogue_deployment_altitude.setValue(
            self.state.get('drogue_deployment_altitude', 800.0)
        )
        self.drogue_deployment_altitude.setSuffix(" m")
        self.drogue_deployment_altitude.setEnabled(self.drogue_enabled_check.isChecked())
        self.drogue_deployment_altitude.valueChanged.connect(
            lambda v: self.state.set('drogue_deployment_altitude', v)
        )
        drogue_layout.addRow("Drogue Deployment Altitude (Threshold):", self.drogue_deployment_altitude)
        
        drogue_group.setLayout(drogue_layout)
        main_layout.addWidget(drogue_group)
        
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
        
        descent_layout.addLayout(results_layout)
        
        descent_group.setLayout(descent_layout)
        main_layout.addWidget(descent_group)
        
        # ===== NOTES SECTION =====
        notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout()
        
        self.notes_text = QPlainTextEdit()
        self.notes_text.setPlaceholderText("Add notes about parachute configuration...")
        self.notes_text.setMaximumHeight(100)
        notes_layout.addWidget(self.notes_text)
        
        notes_group.setLayout(notes_layout)
        main_layout.addWidget(notes_group)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
    
    def load_parachute_configs(self):
        """Load available parachute configurations from config files."""
        config_dir = Path("data/parachutes/configs")
        
        if not config_dir.exists():
            logger.warning(f"Parachute config directory not found: {config_dir}")
            return
        
        try:
            for config_file in config_dir.glob("*.json"):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    config_name = config_file.stem
                    self.parachute_configs[config_name] = config
                    self.parachute_combo.addItem(config_name, config)
                    logger.info(f"Loaded parachute config: {config_name}")
                except Exception as e:
                    logger.error(f"Error loading parachute config {config_file}: {e}")
            
            logger.info(f"Loaded {len(self.parachute_configs)} parachute configurations")
        except Exception as e:
            logger.error(f"Error loading parachute configs: {e}")
    
    def on_parachute_selected(self, config_name: str):
        """Handle parachute selection from dropdown."""
        if config_name == "Manual":
            self.current_parachute = None
            return
        
        if config_name in self.parachute_configs:
            config = self.parachute_configs[config_name]
            self.current_parachute = config_name
            self.apply_parachute_config(config)
            logger.info(f"Selected parachute: {config_name}")
    
    def apply_parachute_config(self, config: dict):
        """Apply parachute configuration to UI controls."""
        try:
            # Main parachute
            self.parachute_name.setText(config.get('name', 'Unknown'))
            self.parachute_diameter.setValue(config.get('diameter', 0.6))
            self.parachute_cd.setValue(config.get('Cd', 1.5))
            
            deployment = config.get('deployment', {})
            self.deployment_altitude.setValue(deployment.get('altitude', 300.0))
            self.min_velocity.setValue(deployment.get('min_velocity', 5.0))
            self.max_velocity.setValue(deployment.get('max_velocity', 80.0))
            self.inflation_time.setValue(deployment.get('deployment_time', 0.5))
            
            # Drogue parachute
            drogue = config.get('drogue', {})
            drogue_enabled = drogue.get('enabled', False)
            self.drogue_enabled_check.setChecked(drogue_enabled)
            
            if drogue_enabled:
                self.drogue_diameter.setValue(drogue.get('diameter', 0.25))
                self.drogue_cd.setValue(drogue.get('Cd', 1.5))
                self.drogue_deployment_altitude.setValue(drogue.get('deployment_altitude', 800.0))
            
            # Update app state
            self.state.set('selected_parachute', config.get('name', 'Unknown'))
            self.parachute_enabled_check.setChecked(True)
            
            logger.info(f"Applied parachute config: {config.get('name')}")
        except Exception as e:
            logger.error(f"Error applying parachute config: {e}")
            QMessageBox.warning(self, "Error", f"Failed to apply parachute config: {e}")
    
    def load_parachute_file(self):
        """Load a parachute configuration from a file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Load Parachute Configuration",
            "data/parachutes/configs",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.apply_parachute_config(config)
                QMessageBox.information(
                    self, "Success",
                    f"Parachute configuration loaded: {config.get('name', 'Unknown')}"
                )
            except Exception as e:
                logger.error(f"Error loading parachute file: {e}")
                QMessageBox.critical(self, "Error", f"Failed to load parachute: {e}")
    
    def save_parachute_config(self):
        """Save current parachute configuration to a file."""
        config = {
            'name': self.parachute_name.text(),
            'diameter': self.parachute_diameter.value(),
            'Cd': self.parachute_cd.value(),
            'material': 'ripstop_nylon',
            'deployment': {
                'altitude': self.deployment_altitude.value(),
                'min_velocity': self.min_velocity.value(),
                'max_velocity': self.max_velocity.value(),
                'deployment_time': self.inflation_time.value()
            },
            'drogue': {
                'enabled': self.drogue_enabled_check.isChecked(),
                'diameter': self.drogue_diameter.value(),
                'Cd': self.drogue_cd.value(),
                'deployment_altitude': self.drogue_deployment_altitude.value(),
                'deployment_time': 0.3
            }
        }
        
        # Generate default filename
        default_filename = self.parachute_name.text().lower().replace(' ', '_') + '.json'
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Parachute Configuration",
            f"data/parachutes/configs/{default_filename}",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                
                QMessageBox.information(
                    self, "Success",
                    f"Parachute configuration saved to:\n{filepath}"
                )
                logger.info(f"Parachute configuration saved: {filepath}")
            except Exception as e:
                logger.error(f"Error saving parachute config: {e}")
                QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")
    
    def on_parachute_enabled(self, state):
        """Handle parachute enable/disable."""
        enabled = state == Qt.CheckState.Checked.value
        self.state.set('parachute_enabled', enabled)
        self.enable_parachute_controls(enabled)
        logger.info(f"Main parachute {'enabled' if enabled else 'disabled'}")
    
    def on_drogue_enabled(self, state):
        """Handle drogue chute enable/disable."""
        enabled = state == Qt.CheckState.Checked.value
        self.state.set('drogue_enabled', enabled)
        self.drogue_diameter.setEnabled(enabled)
        self.drogue_cd.setEnabled(enabled)
        self.drogue_deployment_altitude.setEnabled(enabled)
        logger.info(f"Drogue parachute {'enabled' if enabled else 'disabled'}")
    
    def enable_parachute_controls(self, enabled: bool):
        """Enable or disable parachute control widgets."""
        self.parachute_diameter.setEnabled(enabled)
        self.parachute_cd.setEnabled(enabled)
        self.deployment_altitude.setEnabled(enabled)
        self.min_velocity.setEnabled(enabled)
        self.max_velocity.setEnabled(enabled)
        self.inflation_time.setEnabled(enabled)
        self.drogue_enabled_check.setEnabled(enabled)
    
    def calculate_descent(self):
        """Calculate parachute descent parameters."""
        if not self.parachute_enabled_check.isChecked():
            QMessageBox.warning(self, "Warning", "Parachute is not enabled")
            return
        
        try:
            import numpy as np
            
            # Get rocket mass from state (you should set this when rocket is loaded)
            rocket_mass = self.state.get('initial_mass', 1.5)  # Default 1.5 kg
            
            # Parachute area
            diameter = self.parachute_diameter.value()
            area = np.pi * (diameter / 2.0) ** 2
            
            # Combined drag coefficient
            cd = self.parachute_cd.value()
            
            # Calculate equilibrium descent rate: v = sqrt(2*m*g / (rho * Cd * A))
            # Using sea level air density: 1.225 kg/m³
            air_density = 1.225  # kg/m³
            g = 9.81  # m/s²
            
            descent_rate = np.sqrt(2 * rocket_mass * g / (air_density * cd * area))
            
            # Calculate landing speed (same as descent rate at equilibrium)
            landing_speed = descent_rate
            
            # Estimate descent time from deployment altitude
            deployment_alt = self.deployment_altitude.value()
            descent_time = deployment_alt / descent_rate if descent_rate > 0 else 0
            
            self.descent_time_label.setText(f"{descent_time:.1f} s")
            self.landing_speed_label.setText(f"{landing_speed:.2f} m/s")
            
            QMessageBox.information(
                self, "Descent Calculated",
                f"Equilibrium Descent Rate: {descent_rate:.2f} m/s\n"
                f"Estimated Landing Speed: {landing_speed:.2f} m/s\n"
                f"Descent Time from {deployment_alt:.0f}m: {descent_time:.1f} s\n\n"
                f"Note: This is a simplified calculation assuming equilibrium conditions.\n"
                f"Actual descent may vary with wind and rocket orientation."
            )
            logger.info(f"Parachute descent calculated: {descent_time:.1f}s, {landing_speed:.2f}m/s")
        except Exception as e:
            logger.error(f"Error calculating descent: {e}")
            QMessageBox.critical(self, "Error", f"Failed to calculate descent: {e}")
    
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
