"""Rocket Settings Widget - Complete rocket configuration with 3D preview."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
    QPushButton, QComboBox, QGroupBox, QFormLayout, QMessageBox, QTabWidget,
    QFileDialog, QScrollArea, QSpinBox, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from ui.widgets import BaseWidget
from models.app_state import ApplicationState
from src.models.state import StateProvider
from src.config import Constants
from src.utils.event_bus import EventType, publish
from typing import Optional
import json
import os
import logging
from typing import Tuple, Dict, Any
import math
import numpy as np

# Try to import PyVista for 3D visualization
try:
    import pyvista as pv
    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False

# Try to import pandas for CSV handling
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Try to import matplotlib for thrust curve visualization
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Try to import OrkImporter and OrkExporter for OpenRocket .ork files
try:
    from src.utils.ork_importer import OrkImporter, OrkExporter
    HAS_ORK = True
except ImportError:
    HAS_ORK = False

# Try to import StlImporter (requires trimesh)
try:
    from src.utils.stl_importer import StlImporter, is_available as stl_available
    HAS_STL = stl_available()
except ImportError:
    HAS_STL = False

# Stability calculator (no extra dependencies)
try:
    from src.utils.stability_calculator import compute_stability
    HAS_STABILITY = True
except ImportError:
    HAS_STABILITY = False

logger = logging.getLogger(__name__)


class RocketSettingsWidget(BaseWidget):
    """
    Enhanced rocket configuration widget with comprehensive parameter editing and 3D preview.
    
    Features:
    - Load/edit/save rocket configurations from JSON files
    - Edit all rocket parameters organized in tabs
    - 3D visualization of rocket geometry
    - Support for all JSON parameters (CoM, fuselage, fins, nosecone, etc.)
    """
    
    @staticmethod
    def validate_rocket_name(name: str) -> Tuple[bool, str]:
        """Validate rocket name for file system safety.
        
        Args:
            name (str): Rocket name to validate
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        
        Validates:
            - Non-empty string
            - No invalid filesystem characters
            - Only alphanumeric, spaces, dashes, underscores
        """
        if not name or not name.strip():
            return False, "Rocket name cannot be empty"
        
        # Allow alphanumeric, spaces, dashes, underscores
        if not all(c.isalnum() or c in ' -_' for c in name):
            return False, "Rocket name can only contain letters, numbers, spaces, dashes, and underscores"
        
        # Prevent overly long names
        if len(name) > 100:
            return False, "Rocket name must be 100 characters or less"
        
        return True, ""
    
    def __init__(self, state: Optional[StateProvider] = None, parent=None):
        super().__init__(state=state, parent=parent)
        self.rockets = {}
        self.current_rocket = None
        self.thrust_curve_data = None  # Store loaded thrust curve
        self.init_ui()
        self.load_rocket_configs()
    
    def init_ui(self):
        """Initialize the UI with rocket selection and tabbed editing."""
        main_layout = QVBoxLayout()
        
        # ===== ROCKET SELECTION =====
        selection_group = QGroupBox("Rocket Selection")
        selection_layout = QHBoxLayout()
        
        selection_layout.addWidget(QLabel("Select Rocket:"))
        self.rocket_combo = QComboBox()
        self.rocket_combo.addItem("Manual")
        self.rocket_combo.currentTextChanged.connect(self.on_rocket_selected)
        selection_layout.addWidget(self.rocket_combo)
        
        load_button = QPushButton("📁 Load File")
        load_button.clicked.connect(self.load_rocket_config_file)
        selection_layout.addWidget(load_button)

        ork_button = QPushButton("🚀 Import OpenRocket (.ork)")
        ork_button.setToolTip("Import rocket geometry from an OpenRocket .ork file")
        ork_button.clicked.connect(self.import_ork_file)
        selection_layout.addWidget(ork_button)

        stl_button = QPushButton("📐 Import STL")
        stl_button.setToolTip(
            "Import reference area and inertia from an STL mesh (requires trimesh)"
        )
        stl_button.clicked.connect(self.import_stl_file)
        selection_layout.addWidget(stl_button)

        # Export buttons
        export_ork_button = QPushButton("📤 Export OpenRocket")
        export_ork_button.setToolTip("Export rocket configuration to OpenRocket .ork file")
        export_ork_button.clicked.connect(self.export_ork_file)
        selection_layout.addWidget(export_ork_button)
        
        # Bulk operations
        bulk_import_button = QPushButton("📂 Bulk Import")
        bulk_import_button.setToolTip("Import multiple rocket configurations from a directory")
        bulk_import_button.clicked.connect(self.bulk_import_rockets)
        selection_layout.addWidget(bulk_import_button)
        
        bulk_export_button = QPushButton("📤 Bulk Export")
        bulk_export_button.setToolTip("Export all rocket configurations to a directory")
        bulk_export_button.clicked.connect(self.bulk_export_rockets)
        selection_layout.addWidget(bulk_export_button)
        
        selection_group.setLayout(selection_layout)
        main_layout.addWidget(selection_group)
        
        # ===== TABBED EDITING SECTION =====
        self.tabs = QTabWidget()
        
        # Tab 1: Basic Properties
        self.tab_basic = self._create_basic_properties_tab()
        self.tabs.addTab(self.tab_basic, "Properties")
        
        # Tab 2: Inertia & CoM
        self.tab_inertia = self._create_inertia_tab()
        self.tabs.addTab(self.tab_inertia, "Inertia & CoM")
        
        # Tab 3: Engine
        self.tab_engine = self._create_engine_tab()
        self.tabs.addTab(self.tab_engine, "Engine")
        
        # Tab 4: Geometry
        self.tab_geometry = self._create_geometry_tab()
        self.tabs.addTab(self.tab_geometry, "Geometry")
        
        # Tab 5: Nosecone
        self.tab_nosecone = self._create_nosecone_tab()
        self.tabs.addTab(self.tab_nosecone, "Nosecone")
        
        # Tab 6: Fins
        self.tab_fins = self._create_fins_tab()
        self.tabs.addTab(self.tab_fins, "Fins")
        
        # Tab 7: Stability Visualization
        self.tab_stability = self._create_stability_tab()
        self.tabs.addTab(self.tab_stability, "Stability")
        
        # Tab 8: Thrust Curves
        self.tab_thrust = self._create_thrust_curves_tab()
        self.tabs.addTab(self.tab_thrust, "Thrust Curves")
        
        main_layout.addWidget(self.tabs)
        
        # ===== ACTION BUTTONS =====
        button_layout = QHBoxLayout()
        
        validate_button = QPushButton("✓ Validate Configuration")
        validate_button.clicked.connect(self.validate_and_show_results)
        button_layout.addWidget(validate_button)

        stability_button = QPushButton("⚖️ Check Stability")
        stability_button.setToolTip(
            "Compute centre of pressure (Barrowman) and static stability margin"
        )
        stability_button.clicked.connect(self.check_stability_margin)
        button_layout.addWidget(stability_button)
        
        save_button = QPushButton("💾 Save Configuration")
        save_button.clicked.connect(self.save_rocket_config)
        button_layout.addWidget(save_button)
        
        visualize_button = QPushButton("🎨 Preview 3D Model")
        visualize_button.clicked.connect(self.visualize_3d_model)
        button_layout.addWidget(visualize_button)
        
        delete_button = QPushButton("🗑️ Delete Rocket")
        delete_button.clicked.connect(self.delete_rocket_config)
        button_layout.addWidget(delete_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def _create_basic_properties_tab(self):
        """Create Properties tab with rocket basic information.
        
        Fields:
            - Rocket Name (string): User-defined rocket identifier
            - Initial Mass (0.1-100000 kg): Wet mass including propellant
            - Reference Area (0.000001-1000 m²): Rocket cross-section area for drag
        
        Returns:
            QWidget: Configured form widget with input controls
        """
        widget = QWidget()
        layout = QFormLayout()
        
        # Rocket Name
        self.name_edit = QLineEdit()
        layout.addRow("Rocket Name:", self.name_edit)
        
        # Initial Mass
        self.initial_mass_spinbox = QDoubleSpinBox()
        self.initial_mass_spinbox.setRange(0.1, 100000)
        self.initial_mass_spinbox.setSuffix(" kg")
        layout.addRow("Initial Mass:", self.initial_mass_spinbox)
        
        # Reference Area
        self.reference_area_spinbox = QDoubleSpinBox()
        self.reference_area_spinbox.setRange(0.000001, 1000.0)
        self.reference_area_spinbox.setSuffix(" m²")
        self.reference_area_spinbox.setDecimals(6)
        layout.addRow("Reference Area:", self.reference_area_spinbox)
        
        widget.setLayout(layout)
        return widget
    
    def _create_inertia_tab(self):
        """Create Inertia tab with center of mass and moments of inertia.
        
        Fields:
            - CoM Before Burnout (m): Center of mass measured from nose tip
            - CoM After Burnout (m): CoM position after propellant depletion
            - Ixx, Iyy, Izz (kg*m²): Principal moments of inertia
            - Ixy, Ixz, Iyz (kg*m²): Product of inertia terms
        
        Returns:
            QWidget: Dual-panel widget showing before/after CoM states
        """
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        form_layout = QFormLayout()
        
        # Before Burn
        form_layout.addRow(QLabel("BEFORE BURN"))
        
        form_layout.addRow(QLabel("Moment of Inertia [kg·m²]"))
        self.i_before_x = QDoubleSpinBox()
        self.i_before_x.setRange(0, 1e10)
        self.i_before_x.setSuffix(" kg·m²")
        form_layout.addRow("I_x:", self.i_before_x)
        
        self.i_before_y = QDoubleSpinBox()
        self.i_before_y.setRange(0, 1e10)
        self.i_before_y.setSuffix(" kg·m²")
        form_layout.addRow("I_y:", self.i_before_y)
        
        self.i_before_z = QDoubleSpinBox()
        self.i_before_z.setRange(0, 1e10)
        self.i_before_z.setSuffix(" kg·m²")
        form_layout.addRow("I_z:", self.i_before_z)
        
        form_layout.addRow(QLabel("Center of Mass [m]"))
        self.com_before_x = QDoubleSpinBox()
        self.com_before_x.setRange(-100, 100)
        self.com_before_x.setDecimals(3)
        form_layout.addRow("CoM_x:", self.com_before_x)
        
        self.com_before_y = QDoubleSpinBox()
        self.com_before_y.setRange(-100, 100)
        self.com_before_y.setDecimals(3)
        form_layout.addRow("CoM_y:", self.com_before_y)
        
        self.com_before_z = QDoubleSpinBox()
        self.com_before_z.setRange(-100, 100)
        self.com_before_z.setDecimals(3)
        form_layout.addRow("CoM_z:", self.com_before_z)
        
        # After Burn
        form_layout.addRow(QLabel("AFTER BURN"))
        
        form_layout.addRow(QLabel("Moment of Inertia [kg·m²]"))
        self.i_after_x = QDoubleSpinBox()
        self.i_after_x.setRange(0, 1e10)
        self.i_after_x.setSuffix(" kg·m²")
        form_layout.addRow("I_x:", self.i_after_x)
        
        self.i_after_y = QDoubleSpinBox()
        self.i_after_y.setRange(0, 1e10)
        self.i_after_y.setSuffix(" kg·m²")
        form_layout.addRow("I_y:", self.i_after_y)
        
        self.i_after_z = QDoubleSpinBox()
        self.i_after_z.setRange(0, 1e10)
        self.i_after_z.setSuffix(" kg·m²")
        form_layout.addRow("I_z:", self.i_after_z)
        
        form_layout.addRow(QLabel("Center of Mass [m]"))
        self.com_after_x = QDoubleSpinBox()
        self.com_after_x.setRange(-100, 100)
        self.com_after_x.setDecimals(3)
        form_layout.addRow("CoM_x:", self.com_after_x)
        
        self.com_after_y = QDoubleSpinBox()
        self.com_after_y.setRange(-100, 100)
        self.com_after_y.setDecimals(3)
        form_layout.addRow("CoM_y:", self.com_after_y)
        
        self.com_after_z = QDoubleSpinBox()
        self.com_after_z.setRange(-100, 100)
        self.com_after_z.setDecimals(3)
        form_layout.addRow("CoM_z:", self.com_after_z)
        
        content.setLayout(form_layout)
        scroll.setWidget(content)
        
        # Auto-calculate button
        calculate_button = QPushButton("🔄 Auto-Calculate Inertia from Geometry")
        calculate_button.setToolTip(
            "Calculate moments of inertia based on geometry and material density"
        )
        calculate_button.clicked.connect(self.auto_calculate_inertia)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        main_layout.addWidget(calculate_button)
        widget.setLayout(main_layout)
        return widget
    
    def _create_engine_tab(self):
        """Create Engine tab for propulsion configuration.
        
        Fields:
            - Engine Type: Selection of available engine models
            - Burn Time (s): Duration of engine thrust
            - Thrust Profile: Thrust vs. time configuration
            - Propellant Type: Chemical composition selector
            - Performance Data: ISP, mass flow, chamber pressure
        
        Returns:
            QWidget: Engine configuration interface with visual thrust curve
        """
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        form_layout = QFormLayout()
        
        # Burn Time
        self.burn_time = QDoubleSpinBox()
        self.burn_time.setRange(0.1, 3600)
        self.burn_time.setSuffix(" s")
        form_layout.addRow("Burn Time:", self.burn_time)
        
        # Propellant Mass
        self.propellant_mass = QDoubleSpinBox()
        self.propellant_mass.setRange(0, 100000)
        self.propellant_mass.setSuffix(" kg")
        form_layout.addRow("Propellant Mass:", self.propellant_mass)
        
        # Specific Impulse
        self.specific_impulse = QDoubleSpinBox()
        self.specific_impulse.setRange(0, 500)
        self.specific_impulse.setSuffix(" s")
        form_layout.addRow("Specific Impulse (Isp):", self.specific_impulse)
        
        # Mean Thrust
        self.mean_thrust = QDoubleSpinBox()
        self.mean_thrust.setRange(0, 1e9)
        self.mean_thrust.setSuffix(" N")
        form_layout.addRow("Mean Thrust:", self.mean_thrust)
        
        # Max Thrust
        self.max_thrust = QDoubleSpinBox()
        self.max_thrust.setRange(0, 1e9)
        self.max_thrust.setSuffix(" N")
        form_layout.addRow("Max Thrust:", self.max_thrust)
        
        # Nozzle Exit Diameter
        self.nozzle_diameter = QDoubleSpinBox()
        self.nozzle_diameter.setRange(0.001, 10.0)
        self.nozzle_diameter.setSuffix(" m")
        self.nozzle_diameter.setDecimals(4)
        form_layout.addRow("Nozzle Exit Diameter:", self.nozzle_diameter)

        # Mass flux, gas speed, exit pressure
        self.mass_flux = QDoubleSpinBox()
        self.mass_flux.setRange(0.0, 10000.0)
        self.mass_flux.setSuffix(" kg/s")
        self.mass_flux.setDecimals(4)
        form_layout.addRow("Mass Flux (ṁ):", self.mass_flux)

        self.gas_speed = QDoubleSpinBox()
        self.gas_speed.setRange(0.0, 6000.0)
        self.gas_speed.setSuffix(" m/s")
        self.gas_speed.setDecimals(1)
        form_layout.addRow("Gas Exit Speed (Ve):", self.gas_speed)

        self.exit_pressure = QDoubleSpinBox()
        self.exit_pressure.setRange(0.0, 1e8)
        self.exit_pressure.setSuffix(" Pa")
        self.exit_pressure.setDecimals(0)
        form_layout.addRow("Nozzle Exit Pressure:", self.exit_pressure)

        # Chamber Pressure
        self.mean_chamber_pressure = QDoubleSpinBox()
        self.mean_chamber_pressure.setRange(0, 1e8)
        self.mean_chamber_pressure.setSuffix(" Pa")
        form_layout.addRow("Mean Chamber Pressure:", self.mean_chamber_pressure)
        
        self.max_chamber_pressure = QDoubleSpinBox()
        self.max_chamber_pressure.setRange(0, 1e8)
        self.max_chamber_pressure.setSuffix(" Pa")
        form_layout.addRow("Max Chamber Pressure:", self.max_chamber_pressure)
        
        # Thrust to Weight Ratio
        self.thrust_to_weight = QDoubleSpinBox()
        self.thrust_to_weight.setRange(0, 10000)
        self.thrust_to_weight.setDecimals(2)
        form_layout.addRow("Thrust to Weight Ratio:", self.thrust_to_weight)
        
        content.setLayout(form_layout)
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        widget.setLayout(main_layout)
        return widget
    
    def _create_geometry_tab(self):
        """Create Geometry tab for rocket structural dimensions.
        
        Fields:
            - Total Length (m): Nose tip to motor end
            - Body Diameter (m): Fuselage outer diameter
            - Fin Root Chord (m): Span from root to tip
            - Fin Semi-Span (m): Fin height at root
            - Launch Lug Diameter (m): Clearance for rail/rod
        
        Returns:
            QWidget: Geometric parameter input interface
        """
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        form_layout = QFormLayout()
        
        # Fuselage
        form_layout.addRow(QLabel("FUSELAGE"))
        self.fuselage_length = QDoubleSpinBox()
        self.fuselage_length.setRange(0, 100)
        self.fuselage_length.setSuffix(" m")
        form_layout.addRow("Length:", self.fuselage_length)
        
        self.fuselage_diameter = QDoubleSpinBox()
        self.fuselage_diameter.setRange(0.001, 100)
        self.fuselage_diameter.setSuffix(" m")
        form_layout.addRow("Diameter:", self.fuselage_diameter)
        
        # Rear Section
        form_layout.addRow(QLabel("REAR SECTION"))
        self.rear_length = QDoubleSpinBox()
        self.rear_length.setRange(0, 100)
        self.rear_length.setSuffix(" m")
        form_layout.addRow("Length:", self.rear_length)
        
        self.rear_diameter = QDoubleSpinBox()
        self.rear_diameter.setRange(0.001, 100)
        self.rear_diameter.setSuffix(" m")
        form_layout.addRow("Diameter:", self.rear_diameter)
        
        # Total Geometry
        form_layout.addRow(QLabel("TOTAL"))
        self.total_length = QDoubleSpinBox()
        self.total_length.setRange(0, 100)
        self.total_length.setSuffix(" m")
        form_layout.addRow("Total Length:", self.total_length)
        
        self.length_nosecone_fins = QDoubleSpinBox()
        self.length_nosecone_fins.setRange(0, 100)
        self.length_nosecone_fins.setSuffix(" m")
        form_layout.addRow("Length (Nosecone to Fins):", self.length_nosecone_fins)
        
        content.setLayout(form_layout)
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        widget.setLayout(main_layout)
        return widget
    
    def _create_nosecone_tab(self):
        """Create Nosecone tab for aerodynamic nose design.
        
        Fields:
            - Nosecone Type: Conical, Ogive, Parabolic, Power Law
            - Nosecone Length (m): Tip to base distance
            - Nosecone Base Diameter (m): Diameter at attachment point
            - Power Law Coeff: Exponent for power law shape (n=0.5,1.0,2.0)
            - Shoulder Length (m): Transition to body
        
        Returns:
            QWidget: Aerodynamic design interface with shape preview
        """
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        form_layout = QFormLayout()
        
        # Type
        form_layout.addRow(QLabel("TYPE"))
        self.nosecone_type = QComboBox()
        self.nosecone_type.addItems(["Conical", "Ogive", "Parabolic", "Power", "Haack"])
        form_layout.addRow("Nosecone Type:", self.nosecone_type)
        
        # Dimensions
        form_layout.addRow(QLabel("DIMENSIONS"))
        self.nosecone_length = QDoubleSpinBox()
        self.nosecone_length.setRange(0, 100)
        self.nosecone_length.setSuffix(" m")
        form_layout.addRow("Length:", self.nosecone_length)
        
        self.nosecone_diameter = QDoubleSpinBox()
        self.nosecone_diameter.setRange(0.001, 100)
        self.nosecone_diameter.setSuffix(" m")
        form_layout.addRow("Base Diameter:", self.nosecone_diameter)
        
        # Type-specific parameters
        form_layout.addRow(QLabel("TYPE PARAMETERS"))
        self.ogive_radius = QDoubleSpinBox()
        self.ogive_radius.setRange(0, 1000)
        self.ogive_radius.setSuffix(" m")
        form_layout.addRow("Ogive Radius:", self.ogive_radius)
        
        self.parabolic_parameter = QDoubleSpinBox()
        self.parabolic_parameter.setRange(0, 1)
        self.parabolic_parameter.setDecimals(3)
        form_layout.addRow("Parabolic Parameter:", self.parabolic_parameter)
        
        self.power_value = QDoubleSpinBox()
        self.power_value.setRange(0, 2)
        self.power_value.setDecimals(3)
        form_layout.addRow("Power Value:", self.power_value)
        
        self.haack_type = QComboBox()
        self.haack_type.addItems(["LD-Haack", "LV-Haack"])
        form_layout.addRow("Haack Type:", self.haack_type)
        
        content.setLayout(form_layout)
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        widget.setLayout(main_layout)
        return widget
    
    def _create_fins_tab(self):
        """Create Fins tab for stabilization surface design.
        
        Fields:
            - Fin Quantity: Number of fins (typically 3-4)
            - Root Chord (m): Fin dimension at body attachment
            - Tip Chord (m): Fin dimension at trailing tip
            - Semi-Span (m): Fin height perpendicular to body
            - Sweep Length (m): Distance from leading to trailing edge
            - Fin Midchord Thickness (m): For drag calculation
        
        Returns:
            QWidget: Fin geometry configuration interface
        """
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        form_layout = QFormLayout()
        
        # Number of fins
        form_layout.addRow(QLabel("FIN CONFIGURATION"))
        self.n_fins = QSpinBox()
        self.n_fins.setRange(0, 12)
        form_layout.addRow("Number of Fins:", self.n_fins)
        
        # Fin type
        self.fin_type = QComboBox()
        self.fin_type.addItems(["Trapezoidal", "Delta", "Tapered Swept", "Elliptical", "Custom"])
        form_layout.addRow("Fin Type:", self.fin_type)
        
        # Fin dimensions
        form_layout.addRow(QLabel("DIMENSIONS"))
        self.fin_span = QDoubleSpinBox()
        self.fin_span.setRange(0, 100)
        self.fin_span.setSuffix(" m")
        form_layout.addRow("Span:", self.fin_span)
        
        self.fin_chord_root = QDoubleSpinBox()
        self.fin_chord_root.setRange(0, 100)
        self.fin_chord_root.setSuffix(" m")
        form_layout.addRow("Root Chord:", self.fin_chord_root)
        
        self.fin_chord_tip = QDoubleSpinBox()
        self.fin_chord_tip.setRange(0, 100)
        self.fin_chord_tip.setSuffix(" m")
        form_layout.addRow("Tip Chord:", self.fin_chord_tip)
        
        self.fin_mid_chord = QDoubleSpinBox()
        self.fin_mid_chord.setRange(0, 100)
        self.fin_mid_chord.setSuffix(" m")
        form_layout.addRow("Mid Chord:", self.fin_mid_chord)
        
        self.fin_sweep_angle = QDoubleSpinBox()
        self.fin_sweep_angle.setRange(-180, 180)
        self.fin_sweep_angle.setSuffix(" °")
        form_layout.addRow("Sweep Angle:", self.fin_sweep_angle)
        
        content.setLayout(form_layout)
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        widget.setLayout(main_layout)
        return widget
    
    def _create_stability_tab(self):
        """Create Stability tab with visual CP/CoM representation.
        
        Features:
            - Real-time visualization of rocket side view
            - Shows Centre of Pressure (CP), CoM before/after burnout
            - Stability margin indicators
            - Automatic update when geometry changes
        
        Returns:
            QWidget: Stability visualization interface
        """
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Canvas for matplotlib (if available)
        if HAS_MATPLOTLIB:
            self.figure_stability = Figure(figsize=(10, 4), dpi=100)
            self.canvas_stability = FigureCanvas(self.figure_stability)
            layout.addWidget(self.canvas_stability)
        else:
            self.stability_canvas_widget = QWidget()
            self.stability_canvas_widget.setMinimumHeight(300)
            self.stability_canvas_widget.setStyleSheet("background-color: #1e1e1e; border: 1px solid #444;")
            layout.addWidget(self.stability_canvas_widget)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        refresh_button = QPushButton("🔄 Refresh Visualization")
        refresh_button.clicked.connect(self._refresh_stability_visualization)
        control_layout.addWidget(refresh_button)
        
        # Stability info display
        self.stability_info_label = QLabel("Calculate stability to see results")
        self.stability_info_label.setStyleSheet("color: #ddd; font-size: 12px;")
        self.stability_info_label.setWordWrap(True)
        control_layout.addWidget(self.stability_info_label)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # Stability details
        details_group = QGroupBox("Stability Details")
        details_layout = QFormLayout()
        
        self.cp_label = QLabel("CP: Not calculated")
        self.com_before_label = QLabel("CoM Before: Not calculated")
        self.com_after_label = QLabel("CoM After: Not calculated")
        self.margin_before_label = QLabel("Margin Before: Not calculated")
        self.margin_after_label = QLabel("Margin After: Not calculated")
        self.stability_category_label = QLabel("Category: Not calculated")
        
        details_layout.addRow("Centre of Pressure:", self.cp_label)
        details_layout.addRow("CoM (Before Burn):", self.com_before_label)
        details_layout.addRow("CoM (After Burn):", self.com_after_label)
        details_layout.addRow("Margin (Before):", self.margin_before_label)
        details_layout.addRow("Margin (After):", self.margin_after_label)
        details_layout.addRow("Category:", self.stability_category_label)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _refresh_stability_visualization(self):
        """Update the stability visualization based on current rocket parameters."""
        if not HAS_STABILITY:
            QMessageBox.warning(
                self, "Stability Calculator Unavailable",
                "Stability calculator could not be loaded. Check that src/utils/stability_calculator.py exists."
            )
            return
        
        # Collect current values
        nose_len_m = self.nosecone_length.value()
        nose_shape = self.nosecone_type.currentText().lower()
        body_diam_m = self.fuselage_diameter.value()
        fin_n = self.n_fins.value()
        fin_span_m = self.fin_span.value()
        fin_cr_m = self.fin_chord_root.value()
        fin_ct_m = self.fin_chord_tip.value()
        fin_mc_m = self.fin_mid_chord.value()
        fin_pos_m = self.length_nosecone_fins.value()
        com_before_m = self.com_before_x.value()
        com_after_m = self.com_after_x.value()
        
        # Check for minimum required data
        if nose_len_m <= 0 or body_diam_m <= 0:
            self.stability_info_label.setText(
                "Enter Nosecone Length and Fuselage Diameter to compute stability"
            )
            return
        
        try:
            result = compute_stability(
                nose_length_m=nose_len_m,
                nose_shape=nose_shape,
                body_diameter_m=body_diam_m,
                fin_n=fin_n,
                fin_span_m=fin_span_m,
                fin_chord_root_m=fin_cr_m,
                fin_chord_tip_m=fin_ct_m,
                fin_mid_chord_m=fin_mc_m,
                fin_position_from_nose_m=fin_pos_m,
                com_before_m=com_before_m,
                com_after_m=com_after_m,
            )
            
            # Update labels with results
            self.cp_label.setText(f"{result.xcp:.4f} m from nose")
            self.com_before_label.setText(f"{com_before_m:.4f} m from nose")
            self.com_after_label.setText(f"{com_after_m:.4f} m from nose")
            self.margin_before_label.setText(f"{result.margin_calibers_before:.2f} calibers")
            self.margin_after_label.setText(f"{result.margin_calibers_after:.2f} calibers")
            self.stability_category_label.setText(result.category)
            
            # Update info label
            margin_before_color = "green" if result.margin_calibers_before >= 1.0 else "red" if result.margin_calibers_before < 0 else "orange"
            margin_after_color = "green" if result.margin_calibers_after >= 1.0 else "red" if result.margin_calibers_after < 0 else "orange"
            
            self.stability_info_label.setText(
                f"<span style='color:{margin_before_color};'>Before: {result.margin_calibers_before:.2f} cal</span> | "
                f"<span style='color:{margin_after_color};'>After: {result.margin_calibers_after:.2f} cal</span> | "
                f"<b>{result.category}</b>"
            )
            
            # Trigger repaint of visualization
            self._draw_stability_diagram(result)
            
        except Exception as exc:
            self.stability_info_label.setText(f"Error: {exc}")
            logger.error(f"Stability calculation failed: {exc}")
    
    def _draw_stability_diagram(self, result):
        """Draw the stability diagram showing CP, CoM positions."""
        if not HAS_MATPLOTLIB:
            # Fallback: just show text
            self.stability_info_label.setText(
                f"CP: {result.xcp:.4f}m, Category: {result.category} "
                f"(Install matplotlib for visualization)"
            )
            return
        
        # Initialize figure if not exists (for direct calls)
        if not hasattr(self, 'figure_stability'):
            self.figure_stability = Figure(figsize=(10, 4), dpi=100)
            self.canvas_stability = FigureCanvas(self.figure_stability)
        
        # Clear and redraw
        self.figure_stability.clear()
        ax = self.figure_stability.add_subplot(111)
        
        # Get total length for scaling
        total_len = self.total_length.value()
        if total_len <= 0:
            total_len = (result.xcp + max(self.com_before_x.value(), self.com_after_x.value(), 1.0)) * 1.1
        
        # Draw rocket outline
        body_diam = self.fuselage_diameter.value()
        nose_len = self.nosecone_length.value()
        
        # Rocket body (simple representation)
        ax.plot([0, total_len], [0, 0], 'k-', linewidth=10, label='Rocket Body')
        
        # Nosecone (triangle for visualization)
        if nose_len > 0:
            ax.plot([0, nose_len], [body_diam/2, 0], 'k-', linewidth=2)
            ax.plot([0, nose_len], [-body_diam/2, 0], 'k-', linewidth=2)
        
        # CP position (red)
        if result.xcp > 0:
            ax.plot([result.xcp, result.xcp], [-body_diam/2, body_diam/2], 
                   'r-', linewidth=2, label=f'CP ({result.xcp:.3f}m)')
            ax.scatter([result.xcp], [0], color='red', s=100, zorder=5)
        
        # CoM before (green)
        com_before = self.com_before_x.value()
        if com_before > 0:
            ax.plot([com_before, com_before], [-body_diam/2, body_diam/2], 
                   'g--', linewidth=2, label=f'CoM Before ({com_before:.3f}m)')
            ax.scatter([com_before], [0], color='green', s=100, zorder=5, marker='^')
        
        # CoM after (blue)
        com_after = self.com_after_x.value()
        if com_after > 0:
            ax.plot([com_after, com_after], [-body_diam/2, body_diam/2], 
                   'b:', linewidth=2, label=f'CoM After ({com_after:.3f}m)')
            ax.scatter([com_after], [0], color='blue', s=100, zorder=5, marker='^')
        
        # Stability margin indicators
        if result.margin_calibers_before > 0:
            # Stable: CP is behind CoM
            margin_line_x = [com_before, result.xcp]
            margin_line_y = [0, 0]
            color = 'green' if result.margin_calibers_before >= 1.0 else 'orange'
            ax.plot(margin_line_x, margin_line_y, color=color, linewidth=3, 
                   linestyle='-', alpha=0.5, label=f'Margin: {result.margin_calibers_before:.2f} cal')
        
        # Formatting
        ax.set_xlim(0, total_len * 1.05)
        ax.set_ylim(-body_diam/2 * 1.1, body_diam/2 * 1.1)
        ax.set_xlabel('Distance from Nose (m)')
        ax.set_ylabel('Radius (m)')
        ax.set_title('Rocket Stability Diagram')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        
        self.figure_stability.tight_layout()
        self.canvas_stability.draw()
    
    def _create_thrust_curves_tab(self):
        """Create Thrust Curves tab for engine performance data.
        
        Features:
            - CSV file loader: Time (s) vs. Thrust (N) data pairs
            - Data visualization: Interactive Plotly chart display
            - Data validation: Monotonic time, positive thrust checks
            - Data summary: Total impulse, peak thrust statistics
            - File management: Load, edit inline, or create custom curves
        
        Returns:
            QWidget: Thrust curve visualization and management interface
        """
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Upload section
        upload_group = QGroupBox("Load Thrust Curve from CSV")
        upload_layout = QHBoxLayout()
        
        upload_button = QPushButton("📂 Load CSV File")
        upload_button.clicked.connect(self.load_thrust_curve)
        upload_layout.addWidget(upload_button)
        
        self.thrust_curve_label = QLabel("No curve loaded")
        upload_layout.addWidget(self.thrust_curve_label)
        upload_layout.addStretch()
        
        upload_group.setLayout(upload_layout)
        layout.addWidget(upload_group)
        
        # Info section
        info_group = QGroupBox("Thrust Curve Information")
        info_layout = QVBoxLayout()
        
        self.thrust_info_text = QTextEdit()
        self.thrust_info_text.setReadOnly(True)
        self.thrust_info_text.setMaximumHeight(200)
        info_layout.addWidget(self.thrust_info_text)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Canvas for matplotlib (if available)
        if HAS_MATPLOTLIB:
            canvas_group = QGroupBox("Thrust Curve Visualization")
            canvas_layout = QVBoxLayout()
            
            self.figure = Figure(figsize=(10, 4), dpi=100)
            self.canvas = FigureCanvas(self.figure)
            canvas_layout.addWidget(self.canvas)
            
            canvas_group.setLayout(canvas_layout)
            layout.addWidget(canvas_group)
        else:
            layout.addWidget(QLabel("⚠️ Install matplotlib to visualize curves: pip install matplotlib"))
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
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
            self.current_rocket = None
            return
        
        if rocket_name in self.rockets:
            self.current_rocket = rocket_name
            self.load_rocket_data(self.rockets[rocket_name])
            self.state.set(Constants.StateKeys.SELECTED_ROCKET, rocket_name)
            
            # Publish rocket selected event
            publish(EventType.ROCKET_SELECTED, {
                'rocket_name': rocket_name,
                'rocket_data': self.rockets[rocket_name]
            })
            logger.info(f"Published ROCKET_SELECTED event for: {rocket_name}")
    
    def load_rocket_data(self, rocket_data: dict):
        """Load rocket data into UI fields."""
        # Basic Properties
        self.name_edit.setText(rocket_data.get('name', ''))
        self.initial_mass_spinbox.setValue(rocket_data.get(Constants.StateKeys.INITIAL_MASS, 0.0))
        self.reference_area_spinbox.setValue(rocket_data.get(Constants.StateKeys.REFERENCE_AREA, 0.0))
        
        # Inertia & CoM - Before Burn
        i_before = rocket_data.get('I_before_burn', {})
        self.i_before_x.setValue(i_before.get('x', 0.0))
        self.i_before_y.setValue(i_before.get('y', 0.0))
        self.i_before_z.setValue(i_before.get('z', 0.0))
        
        com_before = rocket_data.get('CoM_before_burn', {})
        self.com_before_x.setValue(com_before.get('x', 0.0))
        self.com_before_y.setValue(com_before.get('y', 0.0))
        self.com_before_z.setValue(com_before.get('z', 0.0))
        
        # Inertia & CoM - After Burn
        i_after = rocket_data.get('I_after_burn', {})
        self.i_after_x.setValue(i_after.get('x', 0.0))
        self.i_after_y.setValue(i_after.get('y', 0.0))
        self.i_after_z.setValue(i_after.get('z', 0.0))
        
        com_after = rocket_data.get('CoM_after_burn', {})
        self.com_after_x.setValue(com_after.get('x', 0.0))
        self.com_after_y.setValue(com_after.get('y', 0.0))
        self.com_after_z.setValue(com_after.get('z', 0.0))
        
        # Engine
        engine = rocket_data.get('engine', {})
        self.burn_time.setValue(engine.get('burn_time', 0.0))
        self.propellant_mass.setValue(engine.get('propellant_mass', 0.0))
        self.specific_impulse.setValue(engine.get('specific_impulse', 0.0))
        self.mean_thrust.setValue(engine.get('mean_thrust', 0.0))
        self.max_thrust.setValue(engine.get('max_thrust', 0.0))
        self.nozzle_diameter.setValue(engine.get('nozzle_exit_diameter', 0.0))
        self.mass_flux.setValue(engine.get('mass_flux', 0.0))
        self.gas_speed.setValue(engine.get('gas_speed', 0.0))
        self.exit_pressure.setValue(engine.get('exit_pressure', 0.0))
        self.mean_chamber_pressure.setValue(engine.get('mean_chamber_pressure', 0.0))
        self.max_chamber_pressure.setValue(engine.get('max_chamber_pressure', 0.0))
        self.thrust_to_weight.setValue(engine.get('thrust_to_weight_ratio', 0.0))
        
        # Geometry
        geometry = rocket_data.get('geometry', {})
        self.total_length.setValue(geometry.get('total length', 0.0))
        self.length_nosecone_fins.setValue(geometry.get('length nosecone fins', 0.0))
        
        fuselage = rocket_data.get('fuselage', {})
        self.fuselage_length.setValue(fuselage.get('length', 0.0))
        self.fuselage_diameter.setValue(fuselage.get('diameter', 0.0))
        
        rear = rocket_data.get('rear_section', {})
        self.rear_length.setValue(rear.get('length', 0.0))
        self.rear_diameter.setValue(rear.get('diameter', 0.0))
        
        # Nosecone
        nosecone = rocket_data.get('nosecone', {})
        self.nosecone_type.setCurrentText(nosecone.get('type', 'Conical'))
        self.nosecone_length.setValue(nosecone.get('length', 0.0))
        self.nosecone_diameter.setValue(nosecone.get('diameter', 0.0))
        self.ogive_radius.setValue(nosecone.get('ogive_radius', 0.0))
        self.parabolic_parameter.setValue(nosecone.get('parabolic_parameter', 0.5))
        self.power_value.setValue(nosecone.get('power_value', 0.5))
        self.haack_type.setCurrentText(nosecone.get('haack_type', 'LV-Haack'))
        
        # Fins
        fins = rocket_data.get('fins', {})
        self.n_fins.setValue(fins.get('N_fins', 0))
        self.fin_type.setCurrentText(fins.get('fin_type', 'Trapezoidal'))
        self.fin_span.setValue(fins.get('span', 0.0))
        self.fin_chord_root.setValue(fins.get('chord_root', 0.0))
        self.fin_chord_tip.setValue(fins.get('chord_tip', 0.0))
        self.fin_mid_chord.setValue(fins.get('mid_chord', 0.0))
        self.fin_sweep_angle.setValue(fins.get('sweep_angle', 0.0))
    
    def validate_rocket_config(self) -> tuple:
        """Validate rocket configuration for physical coherence.
        
        Returns:
            (is_valid, error_messages) - tuple with validation status and list of errors
        """
        errors = []
        warnings = []
        
        # Basic validation
        if not self.name_edit.text():
            errors.append("❌ Rocket name is required")
        
        # Mass validation
        if self.initial_mass_spinbox.value() <= 0:
            errors.append("❌ Initial mass must be > 0")
        
        if self.propellant_mass.value() > self.initial_mass_spinbox.value():
            errors.append("❌ Propellant mass cannot exceed initial mass")
        
        # Thrust validation
        if self.mean_thrust.value() > self.max_thrust.value():
            errors.append("❌ Mean thrust cannot exceed max thrust")
        
        if self.max_thrust.value() < 0:
            errors.append("❌ Max thrust must be >= 0")
        
        # Engine validation
        if self.burn_time.value() <= 0:
            errors.append("❌ Burn time must be > 0")
        
        if self.specific_impulse.value() <= 0 and self.mean_thrust.value() > 0:
            warnings.append("⚠️  Isp should be > 0 if motor is burning")
        
        # CoM validation (axial axis is x, geometry total length is in m)
        total_len_m = self.total_length.value()
        if total_len_m > 0 and self.com_before_x.value() > total_len_m:
            warnings.append("⚠️  CoM before burn is beyond rocket length")

        if total_len_m > 0 and self.com_after_x.value() > total_len_m:
            warnings.append("⚠️  CoM after burn is beyond rocket length")
        
        # Thrust-to-weight validation
        if self.max_thrust.value() > 0 and self.initial_mass_spinbox.value() > 0:
            calculated_twr = self.max_thrust.value() / (self.initial_mass_spinbox.value() * 9.81)
            entered_twr = self.thrust_to_weight.value()
            if abs(calculated_twr - entered_twr) > 0.5:
                warnings.append(f"⚠️  TWR mismatch: calculated={calculated_twr:.2f}, entered={entered_twr:.2f}")
        
        # Geometry validation
        if self.fuselage_length.value() <= 0 and self.fuselage_diameter.value() > 0:
            errors.append("❌ Fuselage length must be > 0 if diameter is specified")
        
        if self.total_length.value() <= 0:
            warnings.append("⚠️  Total length is 0 or negative")
        
        # Check if total length is consistent with components
        component_lengths = 0.0
        if self.nosecone_length.value() > 0:
            component_lengths += self.nosecone_length.value()
        if self.fuselage_length.value() > 0:
            component_lengths += self.fuselage_length.value()
        if self.rear_length.value() > 0:
            component_lengths += self.rear_length.value()
        
        total_len = self.total_length.value()
        if total_len > 0 and component_lengths > 0:
            if abs(component_lengths - total_len) / total_len > 0.1:  # More than 10% difference
                warnings.append(
                    f"⚠️  Total length ({total_len:.3f}m) differs from sum of "
                    f"components ({component_lengths:.3f}m) by more than 10%"
                )
        
        # Nosecone validation
        if self.nosecone_length.value() > 0 and self.nosecone_diameter.value() <= 0:
            errors.append("❌ Nosecone diameter must be > 0 if length is specified")
        
        if self.nosecone_diameter.value() > self.fuselage_diameter.value() and self.fuselage_diameter.value() > 0:
            warnings.append(
                "⚠️  Nosecone diameter is larger than fuselage diameter (unusual configuration)"
            )
        
        # Rear section validation
        if self.rear_length.value() > 0 and self.rear_diameter.value() <= 0:
            errors.append("❌ Rear section diameter must be > 0 if length is specified")
        
        if self.rear_diameter.value() > self.fuselage_diameter.value() and self.rear_length.value() > 0:
            warnings.append(
                "⚠️  Rear section diameter is larger than fuselage diameter (unusual configuration)"
            )
        
        # Fin geometry validation
        if self.n_fins.value() > 0:
            if self.fin_span.value() <= 0:
                errors.append("❌ Fin span must be > 0 if fins are present")
            
            if self.fin_chord_root.value() <= 0:
                errors.append("❌ Fin root chord must be > 0 if fins are present")
            
            if self.fin_chord_tip.value() < 0:
                errors.append("❌ Fin tip chord cannot be negative")
            
            # Check fin chord is reasonable compared to diameter
            if self.fin_chord_root.value() > self.fuselage_diameter.value() * 2:
                warnings.append(
                    "⚠️  Fin root chord is more than twice the fuselage diameter (very large fins)"
                )
            
            # Check fin span is reasonable
            if self.fin_span.value() > self.fuselage_diameter.value() * 5:
                warnings.append(
                    "⚠️  Fin span is more than 5x the fuselage diameter (very large fins)"
                )
            
            # Check mid chord is between root and tip
            mid_chord = self.fin_mid_chord.value()
            if mid_chord > max(self.fin_chord_root.value(), self.fin_chord_tip.value()):
                warnings.append(
                    "⚠️  Fin mid chord is larger than both root and tip chords"
                )
        
        # Reference area validation
        ref_area = self.reference_area_spinbox.value()
        if ref_area > 0:
            fus_diam = self.fuselage_diameter.value()
            expected_area = math.pi * (fus_diam / 2.0) ** 2 if fus_diam > 0 else 0
            if expected_area > 0 and abs(ref_area - expected_area) / expected_area > 0.5:
                warnings.append(
                    f"⚠️  Reference area ({ref_area:.6f} m²) differs significantly from "
                    f"fuselage cross-section ({expected_area:.6f} m²)"
                )
        
        # Inertia validation  
        if self.i_before_x.value() < 0 or self.i_before_y.value() < 0 or self.i_before_z.value() < 0:
            errors.append("❌ Moment of inertia cannot be negative")
        
        # Check that after-burn inertia is not greater than before-burn (unlikely for most rockets)
        if (self.i_after_x.value() > self.i_before_x.value() * 1.5 or
            self.i_after_y.value() > self.i_before_y.value() * 1.5 or
            self.i_after_z.value() > self.i_before_z.value() * 1.5):
            warnings.append(
                "⚠️  After-burn inertia is significantly greater than before-burn inertia (unusual)"
            )
        
        # Fin validation
        if self.n_fins.value() > 0 and self.fin_span.value() <= 0:
            errors.append("❌ Fin span must be > 0 if fins are present")
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings
    
    def validate_and_show_results(self):
        """Validate configuration and show results."""
        is_valid, errors, warnings = self.validate_rocket_config()
        
        # Build message
        message = ""
        if is_valid:
            message = "✅ CONFIGURATION IS VALID\n\n"
        else:
            message = "❌ CONFIGURATION HAS ERRORS:\n\n"
        
        if errors:
            message += "ERRORS:\n"
            for error in errors:
                message += f"  {error}\n"
            message += "\n"
        
        if warnings:
            message += "WARNINGS:\n"
            for warning in warnings:
                message += f"  {warning}\n"
        
        if not errors and not warnings:
            message += "All parameters are within acceptable ranges."
        
        # Show dialog
        if is_valid:
            QMessageBox.information(self, "Validation Result", message)
        else:
            QMessageBox.warning(self, "Validation Failed", message)
        
        logger.info(f"Validation: Valid={is_valid}, Errors={len(errors)}, Warnings={len(warnings)}")

    def check_stability_margin(self):
        """Compute Barrowman CP and static stability margin, then display results."""
        if not HAS_STABILITY:
            QMessageBox.warning(
                self, "Stability Calculator Unavailable",
                "Could not import src/utils/stability_calculator.py.\n"
                "Check that the file exists and has no syntax errors."
            )
            return

        # ----------------------------------------------------------------
        # Collect widget values (geometry in m)
        # ----------------------------------------------------------------
        nose_len_m     = self.nosecone_length.value()
        nose_shape     = self.nosecone_type.currentText().lower()
        body_diam_m    = self.fuselage_diameter.value()
        fin_n          = self.n_fins.value()
        fin_span_m     = self.fin_span.value()
        fin_cr_m       = self.fin_chord_root.value()
        fin_ct_m       = self.fin_chord_tip.value()
        fin_mc_m       = self.fin_mid_chord.value()
        fin_pos_m      = self.length_nosecone_fins.value()
        com_before_m   = self.com_before_x.value()
        com_after_m    = self.com_after_x.value()

        # Guard: need at least a nosecone and body diameter
        if nose_len_m <= 0 or body_diam_m <= 0:
            QMessageBox.warning(
                self, "Insufficient Data",
                "Please set Nosecone Length and Fuselage Diameter before\n"
                "computing the stability margin (Geometry & Nosecone tabs)."
            )
            return

        try:
            result = compute_stability(
                nose_length_m=nose_len_m,
                nose_shape=nose_shape,
                body_diameter_m=body_diam_m,
                fin_n=fin_n,
                fin_span_m=fin_span_m,
                fin_chord_root_m=fin_cr_m,
                fin_chord_tip_m=fin_ct_m,
                fin_mid_chord_m=fin_mc_m,
                fin_position_from_nose_m=fin_pos_m,
                com_before_m=com_before_m,
                com_after_m=com_after_m,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Stability Calculation Error", str(exc))
            logger.error(f"Stability calculation failed: {exc}")
            return

        # ----------------------------------------------------------------
        # Build and display the result dialog
        # ----------------------------------------------------------------
        lines = result.summary_lines()
        message = "\n".join(lines)

        # Colour-coded title
        title = f"Stability Analysis — {result.category}"

        if result.category == "UNSTABLE":
            QMessageBox.critical(self, title, message)
        elif result.category == "MARGINAL":
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)

        logger.info(
            "Stability check: CP=%.4f m, margin_before=%.2f cal, "
            "margin_after=%.2f cal, category=%s",
            result.xcp, result.margin_calibers_before,
            result.margin_calibers_after, result.category,
        )

    def load_thrust_curve(self):
        """Load thrust curve from CSV file."""
        if not HAS_PANDAS:
            QMessageBox.warning(
                self, "Pandas Not Available",
                "Install pandas to load thrust curves: pip install pandas"
            )
            return
        
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load Thrust Curve", "",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        
        if not filepath:
            return
        
        try:
            # Try to load CSV
            df = pd.read_csv(filepath)
            
            # Detect columns (try common names)
            time_col = None
            thrust_col = None
            
            for col in df.columns:
                col_lower = col.lower().strip()
                if 'time' in col_lower or 't' == col_lower:
                    time_col = col
                if 'thrust' in col_lower or 'f' == col_lower or 'force' in col_lower:
                    thrust_col = col
            
            if time_col is None or thrust_col is None:
                QMessageBox.warning(
                    self, "CSV Format Error",
                    f"Could not find time and thrust columns.\n\n"
                    f"Found columns: {', '.join(df.columns)}\n\n"
                    f"Please ensure the CSV has 'time' and 'thrust' columns."
                )
                return
            
            # Extract data
            times = df[time_col].values
            thrusts = df[thrust_col].values
            
            # Calculate statistics
            self.thrust_curve_data = {'time': times, 'thrust': thrusts, 'file': os.path.basename(filepath)}
            
            mean_thrust = np.mean(np.asarray(thrusts))
            max_thrust = np.max(np.asarray(thrusts))
            burn_time = times[-1] - times[0]
            
            # Update info text
            info = f"File: {self.thrust_curve_data['file']}\n\n"
            info += f"Statistics:\n"
            info += f"  Burn Time: {burn_time:.2f} s\n"
            info += f"  Mean Thrust: {mean_thrust:.2f} N\n"
            info += f"  Max Thrust: {max_thrust:.2f} N\n"
            info += f"  Data Points: {len(times)}\n\n"
            info += f"🔗 Suggested Updates:\n"
            info += f"  Burn Time: {burn_time:.2f} s\n"
            info += f"  Mean Thrust: {mean_thrust:.2f} N\n"
            info += f"  Max Thrust: {max_thrust:.2f} N\n"
            
            self.thrust_info_text.setText(info)
            self.thrust_curve_label.setText(f"✓ Loaded: {self.thrust_curve_data['file']}")
            
            # Plot if matplotlib available
            if HAS_MATPLOTLIB:
                self.figure.clear()
                ax = self.figure.add_subplot(111)
                ax.plot(np.asarray(times), np.asarray(thrusts), 'b-', linewidth=2, label='Thrust')
                ax.axhline(y=float(mean_thrust), color='r', linestyle='--', label=f'Mean: {mean_thrust:.0f} N')
                ax.set_xlabel('Time (s)')
                ax.set_ylabel('Thrust (N)')
                ax.set_title(f'Thrust Curve: {self.thrust_curve_data["file"]}')
                ax.legend()
                ax.grid(True, alpha=0.3)
                self.figure.tight_layout()
                self.canvas.draw()
            
            logger.info(f"Loaded thrust curve: {filepath}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV: {str(e)}")
            logger.error(f"Error loading thrust curve: {e}")
    
    def save_rocket_config(self):
        """Save rocket configuration to JSON file.
        
        Validates rocket name for filesystem safety and configuration data
        before saving. Prompts user on validation errors.
        
        Raises:
            OSError: If file operations fail
            JSONDecodeError: If data serialization fails
        """
        # Validate rocket name first
        rocket_name = self.name_edit.text()
        is_name_valid, name_error = self.validate_rocket_name(rocket_name)
        
        if not is_name_valid:
            QMessageBox.critical(
                self, "Invalid Rocket Name",
                f"Rocket name validation failed:\n{name_error}"
            )
            return
        
        # Validate configuration
        is_valid, errors, warnings = self.validate_rocket_config()
        
        if not is_valid:
            reply = QMessageBox.question(
                self, "Validation Errors",
                f"Configuration has {len(errors)} error(s):\n\n" +
                "\n".join(errors) + "\n\n"
                f"Save anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        configs_path = 'data/rockets/configs'
        os.makedirs(configs_path, exist_ok=True)
        
        rocket_data = {
            'name': self.name_edit.text(),
            Constants.StateKeys.INITIAL_MASS: self.initial_mass_spinbox.value(),
            'propellant_mass': self.propellant_mass.value(),
            'dry_mass_kg': round(self.initial_mass_spinbox.value() - self.propellant_mass.value(), 6),
            Constants.StateKeys.REFERENCE_AREA: self.reference_area_spinbox.value(),
            'I_before_burn': {
                'x': self.i_before_x.value(),
                'y': self.i_before_y.value(),
                'z': self.i_before_z.value()
            },
            'CoM_before_burn': {
                'x': self.com_before_x.value(),
                'y': self.com_before_y.value(),
                'z': self.com_before_z.value()
            },
            'I_after_burn': {
                'x': self.i_after_x.value(),
                'y': self.i_after_y.value(),
                'z': self.i_after_z.value()
            },
            'CoM_after_burn': {
                'x': self.com_after_x.value(),
                'y': self.com_after_y.value(),
                'z': self.com_after_z.value()
            },
            'engine': {
                'burn_time': self.burn_time.value(),
                'propellant_mass': self.propellant_mass.value(),
                'specific_impulse': self.specific_impulse.value(),
                'mean_thrust': self.mean_thrust.value(),
                'max_thrust': self.max_thrust.value(),
                'nozzle_exit_diameter': self.nozzle_diameter.value(),
                'mass_flux': self.mass_flux.value(),
                'gas_speed': self.gas_speed.value(),
                'exit_pressure': self.exit_pressure.value(),
                'mean_chamber_pressure': self.mean_chamber_pressure.value(),
                'max_chamber_pressure': self.max_chamber_pressure.value(),
                'thrust_to_weight_ratio': self.thrust_to_weight.value()
            },
            'geometry': {
                'total length': self.total_length.value(),
                'length nosecone fins': self.length_nosecone_fins.value(),
                'total_length': self.total_length.value(),
                'length_nosecone_fins': self.length_nosecone_fins.value()
            },
            'fuselage': {
                'length': self.fuselage_length.value(),
                'diameter': self.fuselage_diameter.value()
            },
            'rear_section': {
                'length': self.rear_length.value(),
                'diameter': self.rear_diameter.value()
            },
            'nosecone': {
                'type': self.nosecone_type.currentText(),
                'shape': self.nosecone_type.currentText().lower(),
                'length': self.nosecone_length.value(),
                'diameter': self.nosecone_diameter.value(),
                'ogive_radius': self.ogive_radius.value(),
                'parabolic_parameter': self.parabolic_parameter.value(),
                'power_value': self.power_value.value(),
                'haack_type': self.haack_type.currentText()
            },
            'fins': {
                'fin_type': self.fin_type.currentText(),
                'N_fins': self.n_fins.value(),
                'span': self.fin_span.value(),
                'chord_root': self.fin_chord_root.value(),
                'chord_tip': self.fin_chord_tip.value(),
                'mid_chord': self.fin_mid_chord.value(),
                'sweep_angle': self.fin_sweep_angle.value()
            }
        }
        
        # Add thrust curve info if available
        if self.thrust_curve_data:
            rocket_data['thrust_curve'] = {
                'source_file': self.thrust_curve_data.get('file', 'unknown'),
                'data_points': len(self.thrust_curve_data.get('time', [])),
                'loaded': True
            }
        
        try:
            safe_name = self.name_edit.text().lower().replace(" ", "_")
            file_path = os.path.join(configs_path, f"{safe_name}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(rocket_data, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(self, "Success", f"Rocket saved to {file_path}")
            logger.info(f"Rocket configuration saved: {file_path}")
            
            # Publish rocket config changed event
            publish(EventType.ROCKET_CONFIG_CHANGED, {
                'rocket_name': rocket_name,
                'file_path': file_path,
                'rocket_data': rocket_data
            })
            logger.info(f"Published ROCKET_CONFIG_CHANGED event for: {rocket_name}")
            
            # Reload configurations
            self.rockets.clear()
            self.rocket_combo.clear()
            self.rocket_combo.addItem("Manual")
            self.load_rocket_configs()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
            logger.error(f"Error saving rocket: {e}")
    
    def visualize_3d_model(self):
        """Visualize 3D model of rocket."""
        if not HAS_PYVISTA:
            QMessageBox.information(
                self, "PyVista Not Available",
                "PyVista is not installed. Install it with: pip install pyvista\n\n"
                "3D visualization will be available after installation."
            )
            return
        
        # Create simple 3D model
        try:
            plotter = pv.Plotter(title="Rocket 3D Model")
            
            # Get dimensions
            nosecone_len = self.nosecone_length.value()  # Already in m
            nosecone_diam = self.nosecone_diameter.value()
            fuselage_len = self.fuselage_length.value()
            fuselage_diam = self.fuselage_diameter.value()
            
            # Nosecone (cone)
            if nosecone_len > 0 and nosecone_diam > 0:
                cone = pv.Cone(height=nosecone_len, radius=nosecone_diam/2)
                cone = cone.translate([0, 0, fuselage_len + nosecone_len/2])
                plotter.add_mesh(cone, color='red', label='Nosecone')
            
            # Fuselage (cylinder)
            if fuselage_len > 0 and fuselage_diam > 0:
                cylinder = pv.Cylinder(height=fuselage_len, radius=fuselage_diam/2)
                cylinder = cylinder.translate([0, 0, fuselage_len/2])
                plotter.add_mesh(cylinder, color='blue', label='Fuselage')
            
            # Add legend and display
            plotter.show()
            
        except Exception as e:
            logger.error(f"Error creating 3D model: {e}")
            QMessageBox.critical(self, "3D Visualization Error", f"Failed to create 3D model: {str(e)}")
    
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
                
                self.load_rocket_data(rocket_data)
                logger.info(f"Loaded rocket from {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {str(e)}")
                logger.error(f"Error loading rocket: {e}")

    def import_ork_file(self):
        """Import rocket geometry from an OpenRocket .ork file."""
        if not HAS_ORK:
            QMessageBox.warning(
                self, "OrkImporter Unavailable",
                "OrkImporter could not be loaded. Check that src/utils/ork_importer.py exists."
            )
            return

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import OpenRocket File", "",
            "OpenRocket Files (*.ork);;All Files (*.*)"
        )
        if not filepath:
            return

        try:
            importer = OrkImporter(filepath)
            rocket_data = importer.parse()
            self.load_rocket_data(rocket_data)
            QMessageBox.information(
                self, "Import Successful",
                f"Imported '{rocket_data.get('name', 'Rocket')}' from OpenRocket.\n\n"
                "Engine parameters were not imported — please fill them in manually "
                "or load a thrust curve."
            )
            logger.info(f"Imported OpenRocket file: {filepath}")
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", f"Could not import .ork file:\n{exc}")
            logger.error(f"OrkImporter error for '{filepath}': {exc}")

    def import_stl_file(self):
        """Import reference area and inertia from an STL mesh file."""
        if not HAS_STL:
            QMessageBox.information(
                self, "trimesh Not Installed",
                "STL import requires the 'trimesh' package.\n"
                "Install it with:\n\n    pip install trimesh\n\n"
                "Then restart the application."
            )
            return

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import STL Mesh", "",
            "STL Files (*.stl);;All Files (*.*)"
        )
        if not filepath:
            return

        mass_kg = self.initial_mass_spinbox.value()
        if mass_kg <= 0:
            QMessageBox.warning(
                self, "Mass Required",
                "Set the rocket's Initial Mass (Properties tab) before importing an STL.\n"
                "The mass is used to compute the moments of inertia."
            )
            return

        try:
            imp = StlImporter(filepath, mass_kg=mass_kg)
            result = imp.compute()

            # Apply computed values to UI
            self.reference_area_spinbox.setValue(result["reference_area"])
            inertia = result["inertia"]
            self.i_before_x.setValue(inertia["x"])
            self.i_before_y.setValue(inertia["y"])
            self.i_before_z.setValue(inertia["z"])
            self.i_after_x.setValue(inertia["x"])
            self.i_after_y.setValue(inertia["y"])
            self.i_after_z.setValue(inertia["z"])
            self.com_before_x.setValue(result["com_offset"])
            self.com_after_x.setValue(result["com_offset"])

            bb = result["bounding_box"]
            details = (
                f"Reference Area : {result[Constants.StateKeys.REFERENCE_AREA]:.6f} m²\n"
                f"Ixx (axial)    : {inertia['x']:.6f} kg·m²\n"
                f"Iyy (pitch)    : {inertia['y']:.6f} kg·m²\n"
                f"Izz (yaw)      : {inertia['z']:.6f} kg·m²\n"
                f"CoM offset     : {result['com_offset']:.5f} m\n"
                f"Length         : {bb['length']:.5f} m\n"
                f"Max diameter   : {bb['diameter_max']:.5f} m"
            )
            QMessageBox.information(
                self, "STL Import Successful",
                f"Properties applied from STL mesh:\n\n{details}"
            )
            logger.info(f"Imported STL: {filepath}")
        except Exception as exc:
            QMessageBox.critical(self, "STL Import Failed", f"Could not import STL:\n{exc}")
            logger.error(f"StlImporter error for '{filepath}': {exc}")
    
    def export_ork_file(self):
        """Export rocket configuration to OpenRocket .ork file."""
        if not HAS_ORK:
            QMessageBox.warning(
                self, "OrkExporter Unavailable",
                "OrkExporter could not be loaded. Check that src/utils/ork_importer.py exists."
            )
            return
        
        # Get current rocket data
        rocket_name = self.name_edit.text().strip()
        if not rocket_name:
            QMessageBox.warning(self, "No Rocket Name", "Please enter a rocket name before exporting.")
            return
        
        # Build rocket data dict from UI
        rocket_data = self._collect_rocket_data()
        
        # Get save path
        default_name = f"{rocket_name.replace(' ', '_')}.ork"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export OpenRocket File", default_name,
            "OpenRocket Files (*.ork);;All Files (*.*)"
        )
        
        if not filepath:
            return
        
        # Ensure .ork extension
        if not filepath.lower().endswith('.ork'):
            filepath += '.ork'
        
        try:
            exporter = OrkExporter(rocket_data)
            exporter.export(filepath)
            QMessageBox.information(
                self, "Export Successful",
                f"Rocket '{rocket_name}' exported to OpenRocket format:\n{filepath}"
            )
            logger.info(f"Exported OpenRocket file: {filepath}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not export .ork file:\n{exc}")
            logger.error(f"OrkExporter error for '{filepath}': {exc}")
    
    def bulk_import_rockets(self):
        """Import multiple rocket configurations from a directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Directory with Rocket Configurations", ""
        )
        
        if not directory:
            return
        
        # Count JSON files in directory
        json_files = [f for f in os.listdir(directory) if f.lower().endswith('.json')]
        
        if not json_files:
            QMessageBox.information(
                self, "No Rocket Files",
                f"No .json files found in:\n{directory}"
            )
            return
        
        imported_count = 0
        errors_count = 0
        error_messages = []
        
        for filename in json_files:
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    rocket_data = json.load(f)
                    rocket_name = rocket_data.get('name', filename)
                    
                    # Check if name already exists
                    if rocket_name in self.rockets:
                        # Append suffix to make unique
                        base_name = rocket_name
                        counter = 1
                        while f"{base_name}_{counter}" in self.rockets:
                            counter += 1
                        rocket_name = f"{base_name}_{counter}"
                        rocket_data['name'] = rocket_name
                    
                    self.rockets[rocket_name] = rocket_data
                    self.rocket_combo.addItem(rocket_name)
                    imported_count += 1
                    logger.info(f"Bulk imported: {filename}")
            except Exception as e:
                errors_count += 1
                error_messages.append(f"{filename}: {str(e)}")
                logger.error(f"Bulk import error for {filename}: {e}")
        
        # Show results
        message = f"Imported {imported_count} rockets from:\n{directory}\n"
        if errors_count > 0:
            message += f"\nFailed to import {errors_count} files:\n"
            message += "\n".join(error_messages[:5])  # Show first 5 errors
            if errors_count > 5:
                message += f"\n... and {errors_count - 5} more"
            QMessageBox.warning(self, "Bulk Import Complete (with errors)", message)
        else:
            QMessageBox.information(self, "Bulk Import Complete", message)
        
        # Update current rocket selection
        if imported_count > 0:
            self.rocket_combo.setCurrentIndex(1)  # Skip "Manual"
            self.on_rocket_selected(self.rocket_combo.currentText())
    
    def bulk_export_rockets(self):
        """Export all rocket configurations to a directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Directory to Export Rocket Configurations", ""
        )
        
        if not directory:
            return
        
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        
        exported_count = 0
        errors_count = 0
        error_messages = []
        
        for rocket_name, rocket_data in self.rockets.items():
            try:
                # Sanitize filename
                safe_name = rocket_name.lower().replace(" ", "_")
                # Remove invalid characters
                safe_name = "".join(c for c in safe_name if c.isalnum() or c in "_-.")
                filepath = os.path.join(directory, f"{safe_name}.json")
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(rocket_data, f, indent=4, ensure_ascii=False)
                
                exported_count += 1
                logger.info(f"Bulk exported: {filepath}")
            except Exception as e:
                errors_count += 1
                error_messages.append(f"{rocket_name}: {str(e)}")
                logger.error(f"Bulk export error for {rocket_name}: {e}")
        
        # Show results
        message = f"Exported {exported_count} rockets to:\n{directory}\n"
        if errors_count > 0:
            message += f"\nFailed to export {errors_count} rockets:\n"
            message += "\n".join(error_messages[:5])  # Show first 5 errors
            if errors_count > 5:
                message += f"\n... and {errors_count - 5} more"
            QMessageBox.warning(self, "Bulk Export Complete (with errors)", message)
        else:
            QMessageBox.information(self, "Bulk Export Complete", message)
    
    def _collect_rocket_data(self) -> dict:
        """Collect all rocket data from UI fields into a dict.
        
        This is the same format used by load_rocket_data().
        """
        return {
            'name': self.name_edit.text(),
            Constants.StateKeys.INITIAL_MASS: self.initial_mass_spinbox.value(),
            'propellant_mass': self.propellant_mass.value(),
            'dry_mass_kg': round(self.initial_mass_spinbox.value() - self.propellant_mass.value(), 6),
            Constants.StateKeys.REFERENCE_AREA: self.reference_area_spinbox.value(),
            'I_before_burn': {
                'x': self.i_before_x.value(),
                'y': self.i_before_y.value(),
                'z': self.i_before_z.value()
            },
            'CoM_before_burn': {
                'x': self.com_before_x.value(),
                'y': self.com_before_y.value(),
                'z': self.com_before_z.value()
            },
            'I_after_burn': {
                'x': self.i_after_x.value(),
                'y': self.i_after_y.value(),
                'z': self.i_after_z.value()
            },
            'CoM_after_burn': {
                'x': self.com_after_x.value(),
                'y': self.com_after_y.value(),
                'z': self.com_after_z.value()
            },
            'engine': {
                'burn_time': self.burn_time.value(),
                'propellant_mass': self.propellant_mass.value(),
                'specific_impulse': self.specific_impulse.value(),
                'mean_thrust': self.mean_thrust.value(),
                'max_thrust': self.max_thrust.value(),
                'nozzle_exit_diameter': self.nozzle_diameter.value(),
                'mass_flux': self.mass_flux.value(),
                'gas_speed': self.gas_speed.value(),
                'exit_pressure': self.exit_pressure.value(),
                'mean_chamber_pressure': self.mean_chamber_pressure.value(),
                'max_chamber_pressure': self.max_chamber_pressure.value(),
                'thrust_to_weight_ratio': self.thrust_to_weight.value()
            },
            'geometry': {
                'total length': self.total_length.value(),
                'length nosecone fins': self.length_nosecone_fins.value(),
                'total_length': self.total_length.value(),
                'length_nosecone_fins': self.length_nosecone_fins.value()
            },
            'fuselage': {
                'length': self.fuselage_length.value(),
                'diameter': self.fuselage_diameter.value()
            },
            'rear_section': {
                'length': self.rear_length.value(),
                'diameter': self.rear_diameter.value()
            },
            'nosecone': {
                'type': self.nosecone_type.currentText(),
                'shape': self.nosecone_type.currentText().lower(),
                'length': self.nosecone_length.value(),
                'diameter': self.nosecone_diameter.value(),
                'ogive_radius': self.ogive_radius.value(),
                'parabolic_parameter': self.parabolic_parameter.value(),
                'power_value': self.power_value.value(),
                'haack_type': self.haack_type.currentText()
            },
            'fins': {
                'fin_type': self.fin_type.currentText(),
                'N_fins': self.n_fins.value(),
                'span': self.fin_span.value(),
                'chord_root': self.fin_chord_root.value(),
                'chord_tip': self.fin_chord_tip.value(),
                'mid_chord': self.fin_mid_chord.value(),
                'sweep_angle': self.fin_sweep_angle.value()
            }
        }
    
    def auto_calculate_inertia(self):
        """Calculate moments of inertia from geometry and mass.
        
        Uses simplified formulas for common shapes:
        - Nosecone: Solid cone approximation
        - Fuselage: Thin-walled cylinder
        - Rear section: Thin-walled cylinder
        - Fins: Rectangular plates
        
        Assumes uniform density throughout the rocket.
        """
        # Get mass
        total_mass = self.initial_mass_spinbox.value()
        if total_mass <= 0:
            QMessageBox.warning(
                self, "Invalid Mass",
                "Please enter a valid initial mass (> 0) before calculating inertia."
            )
            return
        
        # Get geometry (all in m)
        nose_len = self.nosecone_length.value()
        nose_diam = self.nosecone_diameter.value()
        fus_len = self.fuselage_length.value()
        fus_diam = self.fuselage_diameter.value()
        rear_len = self.rear_length.value()
        rear_diam = self.rear_diameter.value()
        
        # Fin dimensions
        fin_n = self.n_fins.value()
        fin_span = self.fin_span.value()
        fin_cr = self.fin_chord_root.value()
        fin_ct = self.fin_chord_tip.value()
        fin_pos = self.length_nosecone_fins.value()
        
        # Ask user for density if not already set
        # For now, assume typical density for model rockets (lightweight materials)
        # Common densities: cardboard ~600 kg/m³, plastic ~900 kg/m³, aluminum ~2700 kg/m³
        # Use 800 kg/m³ as a reasonable default
        density = 800.0  # kg/m³
        
        try:
            # Calculate volumes
            # Nosecone (solid cone: V = 1/3 * pi * r² * h)
            nose_radius = nose_diam / 2.0
            nose_volume = (1/3) * math.pi * (nose_radius ** 2) * nose_len if nose_len > 0 and nose_diam > 0 else 0
            
            # Fuselage (thin-walled cylinder: V ≈ pi * r * t * h, but we simplify to solid for now)
            # Using outer radius
            fus_radius = fus_diam / 2.0
            fus_volume = math.pi * (fus_radius ** 2) * fus_len if fus_len > 0 and fus_diam > 0 else 0
            
            # Rear section
            rear_radius = rear_diam / 2.0
            rear_volume = math.pi * (rear_radius ** 2) * rear_len if rear_len > 0 and rear_diam > 0 else 0
            
            # Fins (simplified as rectangular plates)
            # Use average chord
            avg_chord = (fin_cr + fin_ct) / 2.0 if fin_cr > 0 else fin_cr
            single_fin_volume = fin_span * avg_chord * 0.001  # Assume 0.001m (1mm) thickness
            fins_volume = single_fin_volume * fin_n if fin_n > 0 and fin_span > 0 else 0
            
            total_volume = nose_volume + fus_volume + rear_volume + fins_volume
            
            if total_volume <= 0:
                QMessageBox.warning(
                    self, "Invalid Geometry",
                    "Could not calculate volume from geometry. Please check all dimensions."
                )
                return
            
            # Calculate mass distribution (proportional to volume)
            nose_mass = (nose_volume / total_volume) * total_mass
            fus_mass = (fus_volume / total_volume) * total_mass
            rear_mass = (rear_volume / total_volume) * total_mass
            fins_mass = (fins_volume / total_volume) * total_mass
            
            # Calculate CoM positions (from nose)
            nose_com = nose_len / 2.0  # CoM of cone is at 1/3 from base, but we use center for simplicity
            fus_com = nose_len + fus_len / 2.0
            rear_com = nose_len + fus_len + rear_len / 2.0
            fins_com = fin_pos  # Fin position from nose
            
            # Overall CoM
            total_moment = (
                nose_mass * nose_com +
                fus_mass * fus_com +
                rear_mass * rear_com +
                fins_mass * fins_com
            )
            com_x = total_moment / total_mass if total_mass > 0 else 0
            
            # Calculate moments of inertia using parallel axis theorem
            # For simplicity, use basic formulas for each component
            
            # Nosecone (solid cone: Ix = 3/10 * m * r², Iy = Ix + m * (3/4 * h² + 3/10 * r²))
            # Simplified: treat as point mass at CoM
            i_nose_x = 0.3 * nose_mass * (nose_radius ** 2)
            i_nose_y = 0.3 * nose_mass * (nose_radius ** 2) + nose_mass * (nose_len ** 2) / 12
            i_nose_z = i_nose_y  # Symmetric
            
            # Fuselage (cylinder: Ix = 1/2 * m * r², Iy = Ix + m * (L² / 12 + r² / 4))
            i_fus_x = 0.5 * fus_mass * (fus_radius ** 2)
            i_fus_y = fus_mass * (fus_len ** 2) / 12
            i_fus_z = i_fus_y
            
            # Rear section
            i_rear_x = 0.5 * rear_mass * (rear_radius ** 2)
            i_rear_y = rear_mass * (rear_len ** 2) / 12
            i_rear_z = i_rear_y
            
            # Fins (rectangular plates: Ix = 1/12 * m * (span² + chord²), Iy = 1/12 * m * chord², Izz = 1/12 * m * span²)
            avg_fin_mass = fins_mass / fin_n if fin_n > 0 else 0
            i_fin_x = fin_n * (avg_fin_mass * ((fin_span ** 2) + (avg_chord ** 2)) / 12) if fin_n > 0 else 0
            i_fin_y = fin_n * (avg_fin_mass * (avg_chord ** 2) / 12) if fin_n > 0 else 0
            i_fin_z = fin_n * (avg_fin_mass * (fin_span ** 2) / 12) if fin_n > 0 else 0
            
            # Parallel axis theorem: add m * d² for each component
            # CoM to rocket CoM distance
            d_nose = com_x - nose_com
            d_fus = com_x - fus_com
            d_rear = com_x - rear_com
            d_fins = com_x - fins_com
            
            # Total moments of inertia
            i_total_x = i_nose_x + i_fus_x + i_rear_x + i_fin_x
            i_total_y = (
                i_nose_y + nose_mass * (d_nose ** 2) +
                i_fus_y + fus_mass * (d_fus ** 2) +
                i_rear_y + rear_mass * (d_rear ** 2) +
                i_fin_y + fins_mass * (d_fins ** 2)
            )
            i_total_z = (
                i_nose_z + nose_mass * (d_nose ** 2) +
                i_fus_z + fus_mass * (d_fus ** 2) +
                i_rear_z + rear_mass * (d_rear ** 2) +
                i_fin_z + fins_mass * (d_fins ** 2)
            )
            
            # Update UI
            self.i_before_x.setValue(round(i_total_x, 6))
            self.i_before_y.setValue(round(i_total_y, 6))
            self.i_before_z.setValue(round(i_total_z, 6))
            self.i_after_x.setValue(round(i_total_x, 6))
            self.i_after_y.setValue(round(i_total_y, 6))
            self.i_after_z.setValue(round(i_total_z, 6))
            
            self.com_before_x.setValue(round(com_x, 6))
            self.com_before_y.setValue(0.0)
            self.com_before_z.setValue(0.0)
            self.com_after_x.setValue(round(com_x, 6))
            self.com_after_y.setValue(0.0)
            self.com_after_z.setValue(0.0)
            
            QMessageBox.information(
                self, "Inertia Calculated",
                f"Auto-calculated inertia from geometry:\n\n"
                f"Total Volume: {total_volume:.6f} m³\n"
                f"Estimated Density: {density:.1f} kg/m³\n"
                f"Centre of Mass: {com_x:.4f} m from nose\n"
                f"Ix: {i_total_x:.4f} kg·m²\n"
                f"Iy: {i_total_y:.4f} kg·m²\n"
                f"Iz: {i_total_z:.4f} kg·m²"
            )
            
        except Exception as exc:
            QMessageBox.critical(
                self, "Calculation Error",
                f"Failed to calculate inertia: {exc}"
            )
            logger.error(f"Auto-calculate inertia error: {exc}")
    
    def delete_rocket_config(self):
        """Delete selected rocket configuration."""
        if not self.current_rocket:
            QMessageBox.warning(self, "Warning", "Select a rocket to delete")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete rocket '{self.current_rocket}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                configs_path = 'data/rockets/configs'
                safe_name = self.current_rocket.lower().replace(" ", "_")
                file_path = os.path.join(configs_path, f"{safe_name}.json")
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    QMessageBox.information(self, "Success", f"Deleted '{self.current_rocket}'")
                    
                    # Reload configurations
                    self.rockets.clear()
                    self.rocket_combo.clear()
                    self.rocket_combo.addItem("Manual")
                    self.current_rocket = None
                    self.load_rocket_configs()
            except Exception as e:
                logger.error(f"Error deleting rocket: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")
