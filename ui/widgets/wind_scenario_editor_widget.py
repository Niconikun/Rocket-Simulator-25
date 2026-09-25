"""
Wind Scenario Editor Widget - Phase 4 Advanced Features

Allows users to create, edit, and manage wind scenarios for simulations.
Includes preset templates, custom configurations, and visual preview.

Features:
    - Pre-built wind scenario templates
    - Custom scenario creation
    - Wind profile visualization
    - Scenario saving/loading from JSON
    - Parameter validation
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

import numpy as np
import matplotlib
# Use Agg backend for non-interactive plotting, then display as image
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox, QFormLayout,
    QComboBox, QDoubleSpinBox, QSpinBox, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QDialog, QLineEdit, QCheckBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont

from src.models.wind import (
    WindModel, ConstantWind, LogarithmicWind, PowerLawWind, 
    GustWind, WindShearWind, create_wind_model_from_state
)
from ui.widgets import BaseWidget
from models.app_state import ApplicationState
from src.models.state import StateProvider
from typing import Optional

logger = logging.getLogger(__name__)


# Pre-defined wind scenario templates
WIND_SCENARIOS = {
    "Calm Day": {
        "model_type": "constant",
        "wind_speed": 1.0,
        "wind_direction": 0.0,
        "wind_reference_height": 10.0,
        "wind_exponent": 0.2,
        "wind_roughness_length": 0.1,
        "wind_gust_intensity": 0.0,
        "wind_gust_length_scale": 300.0,
    },
    "Light Breeze": {
        "model_type": "logarithmic",
        "wind_speed": 3.0,
        "wind_direction": 0.0,
        "wind_reference_height": 10.0,
        "wind_roughness_length": 0.05,
        "wind_exponent": 0.15,
        "wind_gust_intensity": 0.05,
        "wind_gust_length_scale": 200.0,
    },
    "Moderate Wind": {
        "model_type": "logarithmic",
        "wind_speed": 8.0,
        "wind_direction": 45.0,
        "wind_reference_height": 10.0,
        "wind_roughness_length": 0.1,
        "wind_exponent": 0.2,
        "wind_gust_intensity": 0.15,
        "wind_gust_length_scale": 300.0,
    },
    "Strong Wind": {
        "model_type": "logarithmic",
        "wind_speed": 15.0,
        "wind_direction": 90.0,
        "wind_reference_height": 10.0,
        "wind_roughness_length": 0.2,
        "wind_exponent": 0.25,
        "wind_gust_intensity": 0.2,
        "wind_gust_length_scale": 400.0,
    },
    "Turbulent (Thunderstorm)": {
        "model_type": "gust",
        "wind_speed": 12.0,
        "wind_direction": 180.0,
        "wind_reference_height": 10.0,
        "wind_roughness_length": 0.5,
        "wind_exponent": 0.3,
        "wind_gust_intensity": 0.5,
        "wind_gust_length_scale": 500.0,
    },
    "Directional Shear": {
        "model_type": "shear",
        "wind_speed": 10.0,
        "wind_direction": 0.0,
        "wind_reference_height": 10.0,
        "wind_roughness_length": 0.1,
        "wind_exponent": 0.2,
        "wind_gust_intensity": 0.1,
        "wind_gust_length_scale": 300.0,
        "shear_direction_change": 45.0,  # degrees
        "shear_altitude_range": 1000.0,  # meters
        "vertical_wind": 0.5,  # m/s updraft
    },
    "High Altitude Jet": {
        "model_type": "logarithmic",
        "wind_speed": 25.0,
        "wind_direction": 270.0,
        "wind_reference_height": 1000.0,
        "wind_roughness_length": 0.01,
        "wind_exponent": 0.1,
        "wind_gust_intensity": 0.1,
        "wind_gust_length_scale": 1000.0,
    },
}


class WindScenarioEditorWidget(BaseWidget):
    """
    Widget for creating and managing wind scenarios.
    
    Signals:
        scenario_selected(dict): Emitted when a scenario is selected/modified
        scenario_saved(str): Emitted when a scenario is saved
    """
    
    scenario_selected = pyqtSignal(dict)
    scenario_saved = pyqtSignal(str)
    
    def __init__(self, parent=None, state=None):
        """
        Initialize wind scenario editor.
        
        Args:
            state: ApplicationState instance (optional, for dependency injection)
            parent: Parent widget
        """
        super().__init__(parent)
        self.state = state if state is not None else ApplicationState()
        self.current_scenario = None
        self.scenarios_dir = Path("data/scenarios")
        self.scenarios_dir.mkdir(exist_ok=True)
        
        # For graphical preview
        self.figure = None
        self.canvas = None
        self.plot_dialog = None
        
        # For two-way sync with wind settings
        self.wind_settings_widget = None
        
        self.init_ui()
        self.load_custom_scenarios()
        
        logger.info("Wind Scenario Editor initialized")
    
    def init_ui(self):
        """Initialize user interface with tabs."""
        layout = QVBoxLayout(self)
        
        # Create tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Template scenarios
        self.templates_tab = self._create_templates_tab()
        self.tabs.addTab(self.templates_tab, "📚 Templates")
        
        # Tab 2: Custom scenarios
        self.custom_tab = self._create_custom_tab()
        self.tabs.addTab(self.custom_tab, "⚙️ Custom")
        
        # Tab 3: Scenario management
        self.manage_tab = self._create_manage_tab()
        self.tabs.addTab(self.manage_tab, "💾 Manage")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    
    def _create_templates_tab(self) -> QWidget:
        """Create template scenarios selection tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("Pre-defined Wind Scenarios")
        title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Select from pre-built wind scenarios for common atmospheric conditions. "
            "Each template can be further customized."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Scenario list
        list_label = QLabel("Available Scenarios:")
        layout.addWidget(list_label)
        
        self.template_list = QListWidget()
        self.template_list.itemSelectionChanged.connect(self._on_template_selected)
        
        # Populate with templates
        for scenario_name in WIND_SCENARIOS.keys():
            self.template_list.addItem(scenario_name)
        
        layout.addWidget(self.template_list)
        
        # Details grid
        details_box = QGroupBox("Scenario Details")
        details_layout = QVBoxLayout(details_box)
        
        self.template_details = QTableWidget()
        self.template_details.setColumnCount(2)
        self.template_details.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.template_details.horizontalHeader().setStretchLastSection(True)
        self.template_details.setMaximumHeight(200)
        
        details_layout.addWidget(self.template_details)
        layout.addWidget(details_box)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        use_template_btn = QPushButton("Use This Scenario")
        use_template_btn.clicked.connect(self._on_use_template)
        button_layout.addWidget(use_template_btn)
        
        customize_btn = QPushButton("Customize & Use")
        customize_btn.clicked.connect(self._on_customize_template)
        button_layout.addWidget(customize_btn)
        
        # Apply and simulate button for templates
        apply_simulate_template_btn = QPushButton("Apply & Simulate")
        apply_simulate_template_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        apply_simulate_template_btn.clicked.connect(lambda: self._on_apply_and_simulate(self.current_scenario))
        button_layout.addWidget(apply_simulate_template_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        return widget
    
    def _create_custom_tab(self) -> QWidget:
        """Create custom scenario configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("Create Custom Scenario")
        title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Scenario name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Scenario Name:")
        name_label.setToolTip("Name for your custom wind scenario (used for saving)")
        name_layout.addWidget(name_label)
        self.scenario_name_input = QLineEdit()
        self.scenario_name_input.setPlaceholderText("e.g., My Custom Wind")
        self.scenario_name_input.setToolTip("Enter a descriptive name for your scenario")
        name_layout.addWidget(self.scenario_name_input)
        layout.addLayout(name_layout)
        
        # Wind model selection
        model_layout = QHBoxLayout()
        self.custom_model_label = QLabel("Wind Model:")
        self.custom_model_label.setToolTip("Type of atmospheric wind model\n\n"
                               "• constant: Uniform wind at all altitudes\n"
                               "• logarithmic: Industry standard boundary layer profile\n"
                               "• power_law: Simplified algebraic profile\n"
                               "• gust: Turbulent fluctuations (Dryden spectrum)\n"
                               "• shear: Directional and magnitude variation with altitude")
        model_layout.addWidget(self.custom_model_label)
        self.custom_model_combo = QComboBox()
        self.custom_model_combo.addItems(["constant", "logarithmic", "power_law", "gust", "shear"])
        self.custom_model_combo.setToolTip("Select wind model type")
        self.custom_model_combo.currentTextChanged.connect(self._on_custom_model_changed)
        model_layout.addWidget(self.custom_model_combo)
        layout.addLayout(model_layout)
        
        # Parameters form
        params_box = QGroupBox("Wind Parameters")
        params_layout = QFormLayout(params_box)
        
        # Common parameters
        speed_label = QLabel("Wind Speed:")
        speed_label.setToolTip("Wind speed at reference height [m/s]\n\n"
                              "Typical values:\n"
                              "• Calm: 0-2 m/s\n"
                              "• Light breeze: 2-5 m/s\n"
                              "• Moderate: 5-10 m/s\n"
                              "• Strong: 10-15 m/s\n"
                              "• Storm: >15 m/s")
        self.custom_speed_spin = QDoubleSpinBox()
        self.custom_speed_spin.setRange(0.0, 50.0)
        self.custom_speed_spin.setValue(5.0)
        self.custom_speed_spin.setSuffix(" m/s")
        self.custom_speed_spin.setToolTip("Wind speed at reference height")
        params_layout.addRow(speed_label, self.custom_speed_spin)
        
        direction_label = QLabel("Wind Direction (FROM):")
        direction_label.setToolTip("Direction wind is coming FROM (meteorological convention)\n\n"
                                   "0° = from North (blows South)\n"
                                   "90° = from East (blows West)\n"
                                   "180° = from South (blows North)\n"
                                   "270° = from West (blows East)")
        self.custom_direction_spin = QDoubleSpinBox()
        self.custom_direction_spin.setRange(0.0, 360.0)
        self.custom_direction_spin.setValue(0.0)
        self.custom_direction_spin.setSuffix("°")
        self.custom_direction_spin.setToolTip("Wind direction in degrees (FROM)")
        params_layout.addRow(direction_label, self.custom_direction_spin)
        
        ref_height_label = QLabel("Reference Height:")
        ref_height_label.setToolTip("Height at which reference wind speed is measured [m]\n\n"
                                    "Standard meteorological reference height is 10m above ground")
        self.custom_ref_height_spin = QDoubleSpinBox()
        self.custom_ref_height_spin.setRange(1.0, 100.0)
        self.custom_ref_height_spin.setValue(10.0)
        self.custom_ref_height_spin.setSuffix(" m")
        self.custom_ref_height_spin.setToolTip("Reference height for wind speed measurement")
        params_layout.addRow(ref_height_label, self.custom_ref_height_spin)
        
        # Model-specific parameters
        self.custom_roughness_label = QLabel("Roughness Length (z₀):")
        self.custom_roughness_label.setToolTip("Surface roughness length [m] - affects logarithmic wind profile\n\n"
                                   "Typical values:\n"
                                   "• 0.0002: Water surface\n"
                                   "• 0.01: Grassland\n"
                                   "• 0.1: Forest edge\n"
                                   "• 0.5: Dense forest/urban")
        self.custom_roughness_spin = QDoubleSpinBox()
        self.custom_roughness_spin.setRange(0.001, 2.0)
        self.custom_roughness_spin.setValue(0.1)
        self.custom_roughness_spin.setSuffix(" m")
        self.custom_roughness_spin.setToolTip("Surface roughness for logarithmic profile")
        params_layout.addRow(self.custom_roughness_label, self.custom_roughness_spin)
        
        self.custom_exponent_label = QLabel("Power Law Exponent (α):")
        self.custom_exponent_label.setToolTip("Power law exponent for wind profile\n\n"
                                  "Typical values:\n"
                                  "• 0.10-0.14: Smooth surfaces (water, grass)\n"
                                  "• 0.20: Average surfaces (crop land, suburban)\n"
                                  "• 0.40: Rough surfaces (forest, urban)")
        self.custom_exponent_spin = QDoubleSpinBox()
        self.custom_exponent_spin.setRange(0.05, 0.5)
        self.custom_exponent_spin.setValue(0.2)
        self.custom_exponent_spin.setToolTip("Power law exponent (α)")
        params_layout.addRow(self.custom_exponent_label, self.custom_exponent_spin)
        
        # Gust parameters
        self.custom_gust_intensity_label = QLabel("Gust Intensity:")
        self.custom_gust_intensity_label.setToolTip("Turbulence intensity (std dev / mean wind)\n\n"
                                       "0.0 = No turbulence\n"
                                       "0.1 = Light turbulence\n"
                                       "0.2-0.3 = Moderate turbulence\n"
                                       "0.5+ = Severe turbulence")
        self.custom_gust_intensity_spin = QDoubleSpinBox()
        self.custom_gust_intensity_spin.setRange(0.0, 1.0)
        self.custom_gust_intensity_spin.setValue(0.1)
        self.custom_gust_intensity_spin.setToolTip("Turbulence intensity (0-1)")
        params_layout.addRow(self.custom_gust_intensity_label, self.custom_gust_intensity_spin)
        
        self.custom_gust_length_label = QLabel("Gust Length Scale:")
        self.custom_gust_length_label.setToolTip("Integral length scale for Dryden turbulence model [m]\n\n"
                                      "Typical values:\n"
                                      "• 200-400m: Low altitude (<600m)\n"
                                      "• 500-2000m: Medium/high altitude")
        self.custom_gust_length_spin = QDoubleSpinBox()
        self.custom_gust_length_spin.setRange(50.0, 5000.0)
        self.custom_gust_length_spin.setValue(300.0)
        self.custom_gust_length_spin.setSuffix(" m")
        self.custom_gust_length_spin.setToolTip("Gust length scale for turbulence")
        params_layout.addRow(self.custom_gust_length_label, self.custom_gust_length_spin)
        
        # Shear parameters
        self.custom_shear_angle_label = QLabel("Direction Change (Shear):")
        self.custom_shear_angle_label.setToolTip("Total wind direction change over shear range [°]\n\n"
                                     "Positive = Clockwise (backing)\n"
                                     "Negative = Counter-clockwise (veering)")
        self.custom_shear_angle_spin = QDoubleSpinBox()
        self.custom_shear_angle_spin.setRange(-180.0, 180.0)
        self.custom_shear_angle_spin.setValue(0.0)
        self.custom_shear_angle_spin.setSuffix("°")
        self.custom_shear_angle_spin.setToolTip("Direction change over altitude range")
        params_layout.addRow(self.custom_shear_angle_label, self.custom_shear_angle_spin)
        
        self.custom_shear_range_label = QLabel("Shear Altitude Range:")
        self.custom_shear_range_label.setToolTip("Altitude range over which directional shear occurs [m]\n\n"
                                    "Wind direction changes linearly from base at ground to base+change at this altitude")
        self.custom_shear_range_spin = QDoubleSpinBox()
        self.custom_shear_range_spin.setRange(100.0, 5000.0)
        self.custom_shear_range_spin.setValue(1000.0)
        self.custom_shear_range_spin.setSuffix(" m")
        self.custom_shear_range_spin.setToolTip("Altitude range for directional shear")
        params_layout.addRow(self.custom_shear_range_label, self.custom_shear_range_spin)
        
        self.custom_vertical_wind_label = QLabel("Vertical Wind:")
        self.custom_vertical_wind_label.setToolTip("Vertical wind component [m/s]\n\n"
                                       "Positive = Updraft\n"
                                       "Negative = Downdraft\n"
                                       "0 = No vertical wind")
        self.custom_vertical_wind_spin = QDoubleSpinBox()
        self.custom_vertical_wind_spin.setRange(-20.0, 20.0)
        self.custom_vertical_wind_spin.setValue(0.0)
        self.custom_vertical_wind_spin.setSuffix(" m/s")
        self.custom_vertical_wind_spin.setToolTip("Vertical wind component (updraft/downdraft)")
        params_layout.addRow(self.custom_vertical_wind_label, self.custom_vertical_wind_spin)
        
        layout.addWidget(params_box)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        preview_btn = QPushButton("Preview Wind Profile")
        preview_btn.clicked.connect(self._on_preview_custom)
        button_layout.addWidget(preview_btn)
        
        save_btn = QPushButton("Save Scenario")
        save_btn.clicked.connect(self._on_save_custom_scenario)
        button_layout.addWidget(save_btn)
        
        use_btn = QPushButton("Use Scenario")
        use_btn.clicked.connect(self._on_use_custom_scenario)
        button_layout.addWidget(use_btn)
        
        # Apply and simulate button
        apply_simulate_btn = QPushButton("Apply & Simulate")
        apply_simulate_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        apply_simulate_btn.clicked.connect(self._on_apply_and_simulate)
        button_layout.addWidget(apply_simulate_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        # Update visible parameters based on model
        self._on_custom_model_changed()
        
        return widget
    
    def _create_manage_tab(self) -> QWidget:
        """Create scenario management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("Manage Saved Scenarios")
        title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Saved scenarios list
        list_layout = QHBoxLayout()
        
        # Left side: list
        list_box_layout = QVBoxLayout()
        list_box_layout.addWidget(QLabel("Saved Scenarios:"))
        
        self.saved_scenarios_list = QListWidget()
        self.saved_scenarios_list.itemSelectionChanged.connect(self._on_saved_scenario_selected)
        list_box_layout.addWidget(self.saved_scenarios_list)
        
        list_layout.addLayout(list_box_layout, 1)
        
        # Right side: buttons
        button_column = QVBoxLayout()
        
        load_btn = QPushButton("Load & Use")
        load_btn.clicked.connect(self._on_load_scenario)
        button_column.addWidget(load_btn)
        
        view_btn = QPushButton("View Details")
        view_btn.clicked.connect(self._on_view_scenario_details)
        button_column.addWidget(view_btn)
        
        # Apply and simulate button
        apply_simulate_mgmt_btn = QPushButton("Apply & Simulate")
        apply_simulate_mgmt_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        apply_simulate_mgmt_btn.clicked.connect(self._on_apply_and_simulate_from_saved)
        button_column.addWidget(apply_simulate_mgmt_btn)
        
        button_column.addStretch()
        
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("background-color: #ff6b6b;")
        delete_btn.clicked.connect(self._on_delete_scenario)
        button_column.addWidget(delete_btn)
        
        list_layout.addLayout(button_column)
        
        layout.addLayout(list_layout)
        
        # Import/Export
        file_layout = QHBoxLayout()
        
        import_btn = QPushButton("Import from File")
        import_btn.clicked.connect(self._on_import_scenario)
        file_layout.addWidget(import_btn)
        
        export_btn = QPushButton("Export to File")
        export_btn.clicked.connect(self._on_export_scenario)
        file_layout.addWidget(export_btn)
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self.load_custom_scenarios)
        file_layout.addWidget(refresh_btn)
        
        layout.addLayout(file_layout)
        layout.addStretch()
        
        return widget
    
    def _on_template_selected(self):
        """Handle template selection."""
        item = self.template_list.currentItem()
        if item is None:
            return
        
        scenario_name = item.text()
        scenario = WIND_SCENARIOS.get(scenario_name)
        
        if scenario:
            self.current_scenario = scenario
            self._display_scenario_details(scenario)
    
    def _on_use_template(self):
        """Use selected template scenario."""
        if self.current_scenario is None:
            QMessageBox.warning(self, "No Selection", "Please select a scenario first.")
            return
        
        self._apply_scenario(self.current_scenario)
        QMessageBox.information(self, "Applied", "Wind scenario applied to simulation.")
    
    def _on_customize_template(self):
        """Switch to custom tab with template values."""
        if self.current_scenario is None:
            QMessageBox.warning(self, "No Selection", "Please select a scenario first.")
            return
        
        # Populate custom tab with template values
        self._populate_custom_from_scenario(self.current_scenario)
        self.tabs.setCurrentIndex(1)  # Switch to custom tab
    
    def _on_custom_model_changed(self):
        """Update visible parameters based on selected model."""
        model_type = self.custom_model_combo.currentText()
        
        # Show/hide parameters based on model
        show_roughness = model_type in ["logarithmic", "gust"]
        show_exponent = model_type in ["power_law", "gust"]
        show_gust = model_type in ["gust"]
        show_shear = model_type == "shear"
        
        # Model label is always visible
        self.custom_roughness_label.setVisible(show_roughness)
        self.custom_roughness_spin.setVisible(show_roughness)
        
        self.custom_exponent_label.setVisible(show_exponent)
        self.custom_exponent_spin.setVisible(show_exponent)
        
        self.custom_gust_intensity_label.setVisible(show_gust)
        self.custom_gust_intensity_spin.setVisible(show_gust)
        self.custom_gust_length_label.setVisible(show_gust)
        self.custom_gust_length_spin.setVisible(show_gust)
        
        self.custom_shear_angle_label.setVisible(show_shear)
        self.custom_shear_angle_spin.setVisible(show_shear)
        self.custom_shear_range_label.setVisible(show_shear)
        self.custom_shear_range_spin.setVisible(show_shear)
        self.custom_vertical_wind_label.setVisible(show_shear)
        self.custom_vertical_wind_spin.setVisible(show_shear)
    
    def _on_preview_custom(self):
        """Preview custom scenario wind profile with graphical plot."""
        try:
            from io import BytesIO
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
            from PyQt6.QtGui import QPixmap, QImage
            
            scenario = self._get_custom_scenario()
            wind_model = create_wind_model_from_state(scenario)
            
            # Calculate wind profile at various altitudes
            max_altitude = 2000
            altitudes = np.linspace(0, max_altitude, 100)
            wind_magnitudes = []
            directions = []
            
            for alt in altitudes:
                wind_vec = wind_model.get_wind_vector(alt)
                mag = np.linalg.norm(wind_vec[:2])
                wind_magnitudes.append(mag)
                directions.append(wind_model.get_direction_from(alt))
            
            # Create figure with two subplots
            self.figure = plt.Figure(figsize=(10, 6), dpi=100)
            self.figure.suptitle(f'Wind Profile Preview: {scenario.get("model_type", "unknown").title()} Model', 
                                  fontsize=12, fontweight='bold')
            
            # Subplot 1: Wind Speed vs Altitude
            ax1 = self.figure.add_subplot(2, 1, 1)
            ax1.plot(wind_magnitudes, altitudes, 'b-', linewidth=2, label='Wind Speed')
            ax1.fill_betweenx(altitudes, 0, wind_magnitudes, alpha=0.2, color='blue')
            ax1.set_xlabel('Wind Speed [m/s]')
            ax1.set_ylabel('Altitude [m]')
            ax1.set_title('Wind Speed Profile')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            ax1.set_xlim(0, max(wind_magnitudes) * 1.1 if max(wind_magnitudes) > 0 else 1)
            ax1.set_ylim(0, max_altitude)
            
            # Subplot 2: Wind Direction vs Altitude
            ax2 = self.figure.add_subplot(2, 1, 2)
            ax2.plot(directions, altitudes, 'r-', linewidth=2, label='Wind Direction')
            ax2.set_xlabel('Wind Direction [° FROM]')
            ax2.set_ylabel('Altitude [m]')
            ax2.set_title('Wind Direction Profile')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            ax2.set_xlim(0, 360)
            ax2.set_ylim(0, max_altitude)
            
            # Adjust layout
            self.figure.tight_layout()
            
            # Save to buffer and display
            buf = BytesIO()
            self.figure.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            
            # Convert to QImage and QPixmap
            img_data = buf.getvalue()
            img = QImage.fromData(img_data)
            pixmap = QPixmap.fromImage(img)
            
            # Create dialog to show the plot
            plot_dialog = QDialog(self)
            plot_dialog.setWindowTitle("Wind Profile Preview")
            plot_dialog.setMinimumSize(700, 600)
            
            dialog_layout = QVBoxLayout(plot_dialog)
            
            # Create label to display the image
            img_label = QLabel()
            img_label.setPixmap(pixmap)
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dialog_layout.addWidget(img_label)
            
            # Add close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(plot_dialog.accept)
            dialog_layout.addWidget(close_btn)
            
            plot_dialog.exec()
            
            # Clean up
            plt.close(self.figure)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not generate preview: {str(e)}")
            logger.error(f"Preview error: {e}", exc_info=True)
    
    def _on_save_custom_scenario(self):
        """Save custom scenario to file."""
        scenario_name = self.scenario_name_input.text().strip()
        
        if not scenario_name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a scenario name.")
            return
        
        try:
            scenario = self._get_custom_scenario()
            scenario['name'] = scenario_name
            
            # Save to JSON file
            scenario_file = self.scenarios_dir / f"{scenario_name}.json"
            with open(scenario_file, 'w') as f:
                json.dump(scenario, f, indent=2)
            
            logger.info(f"Scenario saved: {scenario_name}")
            QMessageBox.information(self, "Saved", f"Scenario '{scenario_name}' saved successfully.")
            
            self.scenario_saved.emit(scenario_name)
            self.load_custom_scenarios()
            self.scenario_name_input.clear()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save scenario: {str(e)}")
    
    def _on_use_custom_scenario(self):
        """Use custom scenario configuration."""
        try:
            scenario = self._get_custom_scenario()
            self._apply_scenario(scenario)
            QMessageBox.information(self, "Applied", "Custom wind scenario applied to simulation.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid scenario: {str(e)}")
    
    def _on_apply_and_simulate(self, scenario=None):
        """Apply scenario and run simulation."""
        try:
            if scenario is None:
                scenario = self._get_custom_scenario()
            
            self._apply_scenario(scenario)
            
            # Trigger simulation
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._trigger_simulation)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not apply and simulate: {str(e)}")
    
    def _on_apply_and_simulate_from_saved(self):
        """Apply saved scenario and run simulation."""
        item = self.saved_scenarios_list.currentItem()
        if item is None:
            QMessageBox.warning(self, "No Selection", "Please select a scenario.")
            return
        
        scenario_name = item.text()
        scenario_file = self.scenarios_dir / f"{scenario_name}.json"
        
        try:
            with open(scenario_file, 'r') as f:
                scenario = json.load(f)
            
            self._apply_scenario(scenario)
            
            # Trigger simulation
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._trigger_simulation)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not apply and simulate: {str(e)}")
    
    def _trigger_simulation(self):
        """Trigger simulation from the main window's simulation widget."""
        try:
            # Find the main window and trigger its simulation widget
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'simulation_widget'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'simulation_widget'):
                # Focus on simulation tab and run
                main_window.tabs.setCurrentIndex(0)  # Switch to Simulation tab
                main_window.simulation_widget.run_simulation()
            else:
                QMessageBox.information(self, "Info", "Simulation started. Please check the Simulation tab.")
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not auto-start simulation: {str(e)}")
            logger.warning(f"Auto-simulation failed: {e}")
    
    def _on_saved_scenario_selected(self):
        """Handle saved scenario selection."""
        # Selection handled by view/load buttons
        pass
    
    def _on_load_scenario(self):
        """Load and use saved scenario."""
        item = self.saved_scenarios_list.currentItem()
        if item is None:
            QMessageBox.warning(self, "No Selection", "Please select a scenario.")
            return
        
        scenario_name = item.text()
        scenario_file = self.scenarios_dir / f"{scenario_name}.json"
        
        try:
            with open(scenario_file, 'r') as f:
                scenario = json.load(f)
            
            self._apply_scenario(scenario)
            QMessageBox.information(self, "Loaded", f"Scenario '{scenario_name}' loaded and applied.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load scenario: {str(e)}")
    
    def _on_view_scenario_details(self):
        """View details of selected scenario."""
        item = self.saved_scenarios_list.currentItem()
        if item is None:
            QMessageBox.warning(self, "No Selection", "Please select a scenario.")
            return
        
        scenario_name = item.text()
        scenario_file = self.scenarios_dir / f"{scenario_name}.json"
        
        try:
            with open(scenario_file, 'r') as f:
                scenario = json.load(f)
            
            details_str = "Scenario Details:\n\n"
            for key, value in scenario.items():
                if key != 'name':
                    details_str += f"{key}: {value}\n"
            
            QMessageBox.information(self, f"Scenario: {scenario_name}", details_str)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not view scenario: {str(e)}")
    
    def _on_delete_scenario(self):
        """Delete saved scenario."""
        item = self.saved_scenarios_list.currentItem()
        if item is None:
            QMessageBox.warning(self, "No Selection", "Please select a scenario.")
            return
        
        scenario_name = item.text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete scenario '{scenario_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            scenario_file = self.scenarios_dir / f"{scenario_name}.json"
            try:
                scenario_file.unlink()
                logger.info(f"Scenario deleted: {scenario_name}")
                self.load_custom_scenarios()
                QMessageBox.information(self, "Deleted", "Scenario deleted successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete scenario: {str(e)}")
    
    def _on_import_scenario(self):
        """Import scenario from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Scenario", "", "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r') as f:
                scenario = json.load(f)
            
            name = Path(file_path).stem
            scenario_file = self.scenarios_dir / f"{name}.json"
            
            with open(scenario_file, 'w') as f:
                json.dump(scenario, f, indent=2)
            
            self.load_custom_scenarios()
            QMessageBox.information(self, "Imported", f"Scenario '{name}' imported successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not import scenario: {str(e)}")
    
    def _on_export_scenario(self):
        """Export scenario to file."""
        item = self.saved_scenarios_list.currentItem()
        if item is None:
            QMessageBox.warning(self, "No Selection", "Please select a scenario.")
            return
        
        scenario_name = item.text()
        scenario_file = self.scenarios_dir / f"{scenario_name}.json"
        
        export_path, _ = QFileDialog.getSaveFileName(
            self, "Export Scenario", scenario_name, "JSON Files (*.json)"
        )
        
        if not export_path:
            return
        
        try:
            with open(scenario_file, 'r') as f:
                scenario = json.load(f)
            
            with open(export_path, 'w') as f:
                json.dump(scenario, f, indent=2)
            
            QMessageBox.information(self, "Exported", f"Scenario exported to {export_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not export scenario: {str(e)}")
    
    def load_custom_scenarios(self):
        """Load custom scenarios from disk."""
        self.saved_scenarios_list.clear()
        
        try:
            if self.scenarios_dir.exists():
                for scenario_file in self.scenarios_dir.glob("*.json"):
                    self.saved_scenarios_list.addItem(scenario_file.stem)
        except Exception as e:
            logger.error(f"Could not load scenarios: {e}")
    
    def _get_custom_scenario(self) -> dict:
        """Get current custom scenario configuration."""
        return {
            'model_type': self.custom_model_combo.currentText(),
            'wind_speed': self.custom_speed_spin.value(),
            'wind_direction': self.custom_direction_spin.value(),
            'wind_reference_height': self.custom_ref_height_spin.value(),
            'wind_roughness_length': self.custom_roughness_spin.value(),
            'wind_exponent': self.custom_exponent_spin.value(),
            'wind_gust_intensity': self.custom_gust_intensity_spin.value(),
            'wind_gust_length_scale': self.custom_gust_length_spin.value(),
            'shear_direction_change': self.custom_shear_angle_spin.value(),
            'shear_altitude_range': self.custom_shear_range_spin.value(),
            'vertical_wind': self.custom_vertical_wind_spin.value(),
        }
    
    def _populate_custom_from_scenario(self, scenario: dict):
        """Populate custom tab from scenario dict."""
        self.custom_model_combo.setCurrentText(scenario.get('model_type', 'logarithmic'))
        self.custom_speed_spin.setValue(scenario.get('wind_speed', 5.0))
        self.custom_direction_spin.setValue(scenario.get('wind_direction', 0.0))
        self.custom_ref_height_spin.setValue(scenario.get('wind_reference_height', 10.0))
        self.custom_roughness_spin.setValue(scenario.get('wind_roughness_length', 0.1))
        self.custom_exponent_spin.setValue(scenario.get('wind_exponent', 0.2))
        self.custom_gust_intensity_spin.setValue(scenario.get('wind_gust_intensity', 0.1))
        self.custom_gust_length_spin.setValue(scenario.get('wind_gust_length_scale', 300.0))
        self.custom_shear_angle_spin.setValue(scenario.get('shear_direction_change', 0.0))
        self.custom_shear_range_spin.setValue(scenario.get('shear_altitude_range', 1000.0))
        self.custom_vertical_wind_spin.setValue(scenario.get('vertical_wind', 0.0))
    
    def _display_scenario_details(self, scenario: dict):
        """Display scenario details in table."""
        self.template_details.setRowCount(0)
        
        for row, (key, value) in enumerate(scenario.items()):
            self.template_details.insertRow(row)
            
            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            value_item = QTableWidgetItem(str(value))
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            self.template_details.setItem(row, 0, key_item)
            self.template_details.setItem(row, 1, value_item)
    
    def _apply_scenario(self, scenario: dict):
        """Apply scenario to application state."""
        # Update app state with scenario parameters
        self.state.set('wind_enabled', True)
        self.state.set('wind_model_type', scenario.get('model_type', 'logarithmic'))
        self.state.set('wind_speed', scenario.get('wind_speed', 5.0))
        self.state.set('wind_direction', scenario.get('wind_direction', 0.0))
        self.state.set('wind_reference_height', scenario.get('wind_reference_height', 10.0))
        self.state.set('wind_roughness_length', scenario.get('wind_roughness_length', 0.1))
        self.state.set('wind_exponent', scenario.get('wind_exponent', 0.2))
        self.state.set('wind_gust_intensity', scenario.get('wind_gust_intensity', 0.1))
        self.state.set('wind_gust_length_scale', scenario.get('wind_gust_length_scale', 300.0))
        
        self.current_scenario = scenario
        self.scenario_selected.emit(scenario)
        logger.info(f"Wind scenario applied: {scenario.get('model_type')}")
    
    def sync_from_wind_settings(self):
        """Update custom tab UI from wind settings widget state."""
        try:
            # Get current values from state
            model_type = self.state.get('wind_model_type', 'logarithmic')
            wind_speed = self.state.get('wind_speed', 5.0)
            wind_direction = self.state.get('wind_direction', 0.0)
            ref_height = self.state.get('wind_reference_height', 10.0)
            roughness = self.state.get('wind_roughness_length', 0.1)
            exponent = self.state.get('wind_exponent', 0.2)
            gust_intensity = self.state.get('wind_gust_intensity', 0.1)
            gust_length = self.state.get('wind_gust_length_scale', 300.0)
            shear_angle = self.state.get('shear_direction_change', 0.0)
            shear_range = self.state.get('shear_altitude_range', 1000.0)
            vertical_wind = self.state.get('vertical_wind', 0.0)
            
            # Update UI without triggering signals
            self.custom_model_combo.blockSignals(True)
            self.custom_model_combo.setCurrentText(model_type)
            self.custom_model_combo.blockSignals(False)
            
            self.custom_speed_spin.setValue(wind_speed)
            self.custom_direction_spin.setValue(wind_direction)
            self.custom_ref_height_spin.setValue(ref_height)
            self.custom_roughness_spin.setValue(roughness)
            self.custom_exponent_spin.setValue(exponent)
            self.custom_gust_intensity_spin.setValue(gust_intensity)
            self.custom_gust_length_spin.setValue(gust_length)
            self.custom_shear_angle_spin.setValue(shear_angle)
            self.custom_shear_range_spin.setValue(shear_range)
            self.custom_vertical_wind_spin.setValue(vertical_wind)
            
            # Update parameter visibility based on model
            self._on_custom_model_changed()
            
            logger.info("Wind scenario editor synced from wind settings")
            
        except Exception as e:
            logger.error(f"Error syncing from wind settings: {e}")
    
    def set_wind_settings_widget(self, wind_widget):
        """Set reference to wind settings widget for two-way sync."""
        self.wind_settings_widget = wind_widget
        if wind_widget:
            wind_widget.wind_changed.connect(self.sync_from_wind_settings)
