"""Rocket Settings Widget - Rocket configuration and management."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
    QPushButton, QComboBox, QGroupBox, QFormLayout, QMessageBox, QTableWidget,
    QTableWidgetItem, QFileDialog
)
from PyQt6.QtCore import Qt
from models.app_state import ApplicationState
import json
import os
import logging

logger = logging.getLogger(__name__)


class RocketSettingsWidget(QWidget):
    """
    Rocket configuration widget for creating and editing rocket properties.
    
    Replaces pages/02_rocket_settings.py
    Allows users to:
    - Load existing rocket configurations
    - Edit rocket properties (mass, dimensions, inertia, etc.)
    - Save custom rocket configurations
    - View 3D model of rocket
    """
    
    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
        self.rockets = {}
        self.init_ui()
        self.load_rocket_configs()
    
    def init_ui(self):
        """Initialize the rocket settings widget UI."""
        main_layout = QVBoxLayout()
        
        # ===== ROCKET SELECTION =====
        selection_group = QGroupBox("Rocket Selection")
        selection_layout = QHBoxLayout()
        
        selection_layout.addWidget(QLabel("Select Rocket:"))
        self.rocket_combo = QComboBox()
        self.rocket_combo.addItem("Manual")
        self.rocket_combo.currentTextChanged.connect(self.on_rocket_selected)
        selection_layout.addWidget(self.rocket_combo)
        
        load_button = QPushButton("Load")
        load_button.clicked.connect(self.load_rocket_config_file)
        selection_layout.addWidget(load_button)
        
        selection_group.setLayout(selection_layout)
        main_layout.addWidget(selection_group)
        
        # ===== ROCKET PROPERTIES =====
        props_group = QGroupBox("Rocket Properties")
        props_layout = QFormLayout()
        
        # Name
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(
            lambda v: self.state.set('rocket_name', v)
        )
        props_layout.addRow("Rocket Name:", self.name_edit)
        
        # Initial Mass
        self.mass_spinbox = QDoubleSpinBox()
        self.mass_spinbox.setRange(0.1, 10000)
        self.mass_spinbox.setValue(self.state.get('initial_mass', 0.0))
        self.mass_spinbox.setSuffix(" kg")
        self.mass_spinbox.valueChanged.connect(
            lambda v: self.state.set('initial_mass', v)
        )
        props_layout.addRow("Initial Mass:", self.mass_spinbox)
        
        # Burn Time
        self.burn_time_spinbox = QDoubleSpinBox()
        self.burn_time_spinbox.setRange(0.1, 3600)
        self.burn_time_spinbox.setValue(self.state.get('burn_time', 0.0))
        self.burn_time_spinbox.setSuffix(" s")
        self.burn_time_spinbox.valueChanged.connect(
            lambda v: self.state.set('burn_time', v)
        )
        props_layout.addRow("Burn Time:", self.burn_time_spinbox)
        
        # Reference Area
        self.area_spinbox = QDoubleSpinBox()
        self.area_spinbox.setRange(0.001, 10)
        self.area_spinbox.setValue(self.state.get('reference_area', 0.0))
        self.area_spinbox.setSuffix(" m²")
        self.area_spinbox.setDecimals(4)
        self.area_spinbox.valueChanged.connect(
            lambda v: self.state.set('reference_area', v)
        )
        props_layout.addRow("Reference Area:", self.area_spinbox)
        
        props_group.setLayout(props_layout)
        main_layout.addWidget(props_group)
        
        # ===== INERTIA PROPERTIES =====
        inertia_group = QGroupBox("Moment of Inertia (before burn)")
        inertia_layout = QFormLayout()
        
        self.inertia_x = QDoubleSpinBox()
        self.inertia_x.setRange(0, 100000)
        self.inertia_x.setSuffix(" kg·m²")
        self.inertia_x.setValue(self.state.get('I_before_burn', {}).get('x', 0.0))
        inertia_layout.addRow("I_x:", self.inertia_x)
        
        self.inertia_y = QDoubleSpinBox()
        self.inertia_y.setRange(0, 100000)
        self.inertia_y.setSuffix(" kg·m²")
        self.inertia_y.setValue(self.state.get('I_before_burn', {}).get('y', 0.0))
        inertia_layout.addRow("I_y:", self.inertia_y)
        
        self.inertia_z = QDoubleSpinBox()
        self.inertia_z.setRange(0, 100000)
        self.inertia_z.setSuffix(" kg·m²")
        self.inertia_z.setValue(self.state.get('I_before_burn', {}).get('z', 0.0))
        inertia_layout.addRow("I_z:", self.inertia_z)
        
        inertia_group.setLayout(inertia_layout)
        main_layout.addWidget(inertia_group)
        
        # ===== ACTION BUTTONS =====
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("💾 Save Configuration")
        save_button.clicked.connect(self.save_rocket_config)
        button_layout.addWidget(save_button)
        
        delete_button = QPushButton("🗑️ Delete")
        delete_button.clicked.connect(self.delete_rocket_config)
        button_layout.addWidget(delete_button)
        
        main_layout.addLayout(button_layout)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
    
    def load_rocket_configs(self):
        """Load all available rocket configurations."""
        try:
            configs_path = 'data/rockets/configs'
            if os.path.exists(configs_path):
                for filename in os.listdir(configs_path):
                    if filename.endswith('.json'):
                        with open(os.path.join(configs_path, filename), 'r', encoding='utf-8') as f:
                            rocket_data = json.load(f)
                            rocket_name = rocket_data.get('name', filename)
                            self.rockets[rocket_name] = rocket_data
                            self.rocket_combo.addItem(rocket_name)
            logger.info(f"Loaded {len(self.rockets)} rocket configurations")
        except Exception as e:
            logger.error(f"Error loading rocket configs: {e}")
    
    def on_rocket_selected(self, rocket_name: str):
        """Handle rocket selection change."""
        if rocket_name == "Manual":
            return
        
        if rocket_name in self.rockets:
            rocket_data = self.rockets[rocket_name]
            self.name_edit.setText(rocket_data.get('name', ''))
            self.mass_spinbox.setValue(rocket_data.get('initial_mass', 0.0))
            self.burn_time_spinbox.setValue(rocket_data.get('engine', {}).get('burn_time', 0.0))
            self.area_spinbox.setValue(rocket_data.get('reference_area', 0.0))
            
            inertia_before = rocket_data.get('I_before_burn', {})
            self.inertia_x.setValue(inertia_before.get('x', 0.0))
            self.inertia_y.setValue(inertia_before.get('y', 0.0))
            self.inertia_z.setValue(inertia_before.get('z', 0.0))
            
            self.state.set('sim_rocket', rocket_name)
    
    def save_rocket_config(self):
        """Save rocket configuration to file."""
        configs_path = 'data/rockets/configs'
        os.makedirs(configs_path, exist_ok=True)
        
        rocket_data = {
            'name': self.name_edit.text(),
            'initial_mass': self.mass_spinbox.value(),
            'reference_area': self.area_spinbox.value(),
            'engine': {'burn_time': self.burn_time_spinbox.value()},
            'I_before_burn': {
                'x': self.inertia_x.value(),
                'y': self.inertia_y.value(),
                'z': self.inertia_z.value()
            }
        }
        
        try:
            safe_name = self.name_edit.text().lower().replace(" ", "_")
            file_path = os.path.join(configs_path, f"{safe_name}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(rocket_data, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(self, "Success", f"Rocket saved to {file_path}")
            logger.info(f"Rocket configuration saved: {file_path}")
            
            # Reload configurations
            self.rockets.clear()
            self.rocket_combo.clear()
            self.rocket_combo.addItem("Manual")
            self.load_rocket_configs()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
            logger.error(f"Error saving rocket: {e}")
    
    def delete_rocket_config(self):
        """Delete selected rocket configuration."""
        current = self.rocket_combo.currentText()
        if current == "Manual":
            QMessageBox.warning(self, "Warning", "Cannot delete Manual rocket")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete rocket '{current}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                configs_path = 'data/rockets/configs'
                safe_name = current.lower().replace(" ", "_")
                file_path = os.path.join(configs_path, f"{safe_name}.json")
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    QMessageBox.information(self, "Success", f"Deleted '{current}'")
                    
                    # Reload configurations
                    self.rockets.clear()
                    self.rocket_combo.clear()
                    self.rocket_combo.addItem("Manual")
                    self.load_rocket_configs()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")
    
    def load_rocket_config_file(self):
        """Load a rocket configuration from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load Rocket Configuration", "",
            "JSON Files (*.json)"
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    rocket_data = json.load(f)
                    self.on_rocket_selected(rocket_data.get('name', 'Loaded'))
                    QMessageBox.information(self, "Success", "Rocket configuration loaded")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {str(e)}")
