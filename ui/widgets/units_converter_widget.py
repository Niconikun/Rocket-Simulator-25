"""Units Conversion Widget - Unit conversion utility."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QGroupBox, QFormLayout, QPushButton, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from models.app_state import ApplicationState
import logging

logger = logging.getLogger(__name__)


class UnitsConverterWidget(QWidget):
    """
    Units conversion utility widget.
    
    Replaces pages/06_units_conversion.py
    Provides conversion between:
    - Length (m, km, ft, miles)
    - Velocity (m/s, km/h, ft/s, knots, mph)
    - Temperature (°C, °F, K)
    - Mass (kg, g, lbs, oz)
    - Pressure (Pa, atm, bar, mmHg, psi)
    """
    
    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the units converter UI."""
        main_layout = QVBoxLayout()
        
        # Create tabs for different conversions
        tabs = QTabWidget()
        
        # Length conversion
        tabs.addTab(self.create_length_tab(), "Length")
        
        # Velocity conversion
        tabs.addTab(self.create_velocity_tab(), "Velocity")
        
        # Temperature conversion
        tabs.addTab(self.create_temperature_tab(), "Temperature")
        
        # Mass conversion
        tabs.addTab(self.create_mass_tab(), "Mass")
        
        # Pressure conversion
        tabs.addTab(self.create_pressure_tab(), "Pressure")
        
        main_layout.addWidget(tabs)
        self.setLayout(main_layout)
    
    def create_length_tab(self):
        """Create length conversion tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.length_from = QLineEdit("1.0")
        self.length_from.textChanged.connect(self.convert_length)
        form.addRow("Value:", self.length_from)
        
        self.length_from_unit = QComboBox()
        self.length_from_unit.addItems(["meters", "kilometers", "feet", "miles"])
        form.addRow("From:", self.length_from_unit)
        
        self.length_result = QLineEdit()
        self.length_result.setReadOnly(True)
        form.addRow("Result:", self.length_result)
        
        self.length_to_unit = QComboBox()
        self.length_to_unit.addItems(["meters", "kilometers", "feet", "miles"])
        self.length_to_unit.setCurrentIndex(1)
        self.length_to_unit.currentTextChanged.connect(self.convert_length)
        form.addRow("To:", self.length_to_unit)
        
        layout.addLayout(form)
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_velocity_tab(self):
        """Create velocity conversion tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.velocity_from = QLineEdit("100.0")
        self.velocity_from.textChanged.connect(self.convert_velocity)
        form.addRow("Value:", self.velocity_from)
        
        self.velocity_from_unit = QComboBox()
        self.velocity_from_unit.addItems(["m/s", "km/h", "ft/s", "knots", "mph"])
        form.addRow("From:", self.velocity_from_unit)
        
        self.velocity_result = QLineEdit()
        self.velocity_result.setReadOnly(True)
        form.addRow("Result:", self.velocity_result)
        
        self.velocity_to_unit = QComboBox()
        self.velocity_to_unit.addItems(["m/s", "km/h", "ft/s", "knots", "mph"])
        self.velocity_to_unit.setCurrentIndex(1)
        self.velocity_to_unit.currentTextChanged.connect(self.convert_velocity)
        form.addRow("To:", self.velocity_to_unit)
        
        layout.addLayout(form)
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_temperature_tab(self):
        """Create temperature conversion tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.temp_from = QLineEdit("20.0")
        self.temp_from.textChanged.connect(self.convert_temperature)
        form.addRow("Value:", self.temp_from)
        
        self.temp_from_unit = QComboBox()
        self.temp_from_unit.addItems(["Celsius", "Fahrenheit", "Kelvin"])
        form.addRow("From:", self.temp_from_unit)
        
        self.temp_result = QLineEdit()
        self.temp_result.setReadOnly(True)
        form.addRow("Result:", self.temp_result)
        
        self.temp_to_unit = QComboBox()
        self.temp_to_unit.addItems(["Celsius", "Fahrenheit", "Kelvin"])
        self.temp_to_unit.setCurrentIndex(2)
        self.temp_to_unit.currentTextChanged.connect(self.convert_temperature)
        form.addRow("To:", self.temp_to_unit)
        
        layout.addLayout(form)
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_mass_tab(self):
        """Create mass conversion tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.mass_from = QLineEdit("1.0")
        self.mass_from.textChanged.connect(self.convert_mass)
        form.addRow("Value:", self.mass_from)
        
        self.mass_from_unit = QComboBox()
        self.mass_from_unit.addItems(["kg", "g", "lbs", "oz"])
        form.addRow("From:", self.mass_from_unit)
        
        self.mass_result = QLineEdit()
        self.mass_result.setReadOnly(True)
        form.addRow("Result:", self.mass_result)
        
        self.mass_to_unit = QComboBox()
        self.mass_to_unit.addItems(["kg", "g", "lbs", "oz"])
        self.mass_to_unit.setCurrentIndex(2)
        self.mass_to_unit.currentTextChanged.connect(self.convert_mass)
        form.addRow("To:", self.mass_to_unit)
        
        layout.addLayout(form)
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_pressure_tab(self):
        """Create pressure conversion tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.pressure_from = QLineEdit("101325")
        self.pressure_from.textChanged.connect(self.convert_pressure)
        form.addRow("Value:", self.pressure_from)
        
        self.pressure_from_unit = QComboBox()
        self.pressure_from_unit.addItems(["Pa", "atm", "bar", "mmHg", "psi"])
        form.addRow("From:", self.pressure_from_unit)
        
        self.pressure_result = QLineEdit()
        self.pressure_result.setReadOnly(True)
        form.addRow("Result:", self.pressure_result)
        
        self.pressure_to_unit = QComboBox()
        self.pressure_to_unit.addItems(["Pa", "atm", "bar", "mmHg", "psi"])
        self.pressure_to_unit.setCurrentIndex(1)
        self.pressure_to_unit.currentTextChanged.connect(self.convert_pressure)
        form.addRow("To:", self.pressure_to_unit)
        
        layout.addLayout(form)
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def convert_length(self):
        """Convert length units."""
        try:
            value = float(self.length_from.text())
            # Conversion logic would go here
            self.length_result.setText(f"{value * 3.28084:.4f}")  # m to ft example
        except ValueError:
            self.length_result.setText("")
    
    def convert_velocity(self):
        """Convert velocity units."""
        try:
            value = float(self.velocity_from.text())
            # Conversion logic would go here
            self.velocity_result.setText(f"{value * 3.6:.4f}")  # m/s to km/h example
        except ValueError:
            self.velocity_result.setText("")
    
    def convert_temperature(self):
        """Convert temperature units."""
        try:
            value = float(self.temp_from.text())
            # Conversion logic would go here
            self.temp_result.setText(f"{value + 273.15:.2f}")  # °C to K example
        except ValueError:
            self.temp_result.setText("")
    
    def convert_mass(self):
        """Convert mass units."""
        try:
            value = float(self.mass_from.text())
            # Conversion logic would go here
            self.mass_result.setText(f"{value * 2.20462:.4f}")  # kg to lbs example
        except ValueError:
            self.mass_result.setText("")
    
    def convert_pressure(self):
        """Convert pressure units."""
        try:
            value = float(self.pressure_from.text())
            # Conversion logic would go here
            self.pressure_result.setText(f"{value / 101325:.6f}")  # Pa to atm example
        except ValueError:
            self.pressure_result.setText("")
