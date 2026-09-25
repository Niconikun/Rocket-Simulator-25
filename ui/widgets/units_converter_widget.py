"""Units Conversion Widget - Unit conversion utility."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QGroupBox, QFormLayout, QPushButton, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from ui.widgets import BaseWidget
from models.app_state import ApplicationState
from src.models.state import StateProvider
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Conversion factors to/from base units
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
        ('m/s', 'km/h'): 3.6,
        ('m/s', 'ft/s'): 3.28084,
        ('m/s', 'knots'): 1.94384,
        ('m/s', 'mph'): 2.23694,
        ('km/h', 'm/s'): 0.27778,
        ('km/h', 'ft/s'): 0.911344,
        ('km/h', 'knots'): 0.539957,
        ('km/h', 'mph'): 0.621371,
        ('ft/s', 'm/s'): 0.3048,
        ('ft/s', 'km/h'): 1.09728,
        ('ft/s', 'knots'): 0.592484,
        ('ft/s', 'mph'): 0.681818,
        ('knots', 'm/s'): 0.51444,
        ('knots', 'km/h'): 1.852,
        ('knots', 'ft/s'): 1.68781,
        ('knots', 'mph'): 1.15078,
        ('mph', 'm/s'): 0.44704,
        ('mph', 'km/h'): 1.60934,
        ('mph', 'ft/s'): 1.46667,
        ('mph', 'knots'): 0.868976,
    },
    'mass': {
        ('kg', 'g'): 1000,
        ('kg', 'lbs'): 2.20462,
        ('kg', 'oz'): 35.274,
        ('g', 'kg'): 0.001,
        ('g', 'lbs'): 0.00220462,
        ('g', 'oz'): 0.035274,
        ('lbs', 'kg'): 0.453592,
        ('lbs', 'g'): 453.592,
        ('lbs', 'oz'): 16,
        ('oz', 'kg'): 0.0283495,
        ('oz', 'g'): 28.3495,
        ('oz', 'lbs'): 0.0625,
    },
    'pressure': {
        ('Pa', 'atm'): 9.8692e-6,
        ('Pa', 'bar'): 1e-5,
        ('Pa', 'mmHg'): 0.00750062,
        ('Pa', 'psi'): 0.000145038,
        ('atm', 'Pa'): 101325,
        ('atm', 'bar'): 1.01325,
        ('atm', 'mmHg'): 760,
        ('atm', 'psi'): 14.6959,
        ('bar', 'Pa'): 100000,
        ('bar', 'atm'): 0.986923,
        ('bar', 'mmHg'): 750.062,
        ('bar', 'psi'): 14.5038,
        ('mmHg', 'Pa'): 133.322,
        ('mmHg', 'atm'): 0.00131579,
        ('mmHg', 'bar'): 0.00133322,
        ('mmHg', 'psi'): 0.0193368,
        ('psi', 'Pa'): 6894.76,
        ('psi', 'atm'): 0.068046,
        ('psi', 'bar'): 0.0689476,
        ('psi', 'mmHg'): 51.7149,
    },
}


class UnitsConverterWidget(BaseWidget):
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
    
    def __init__(self, state: Optional[StateProvider] = None):
        super().__init__(state=state)
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
        self.length_from_unit.currentTextChanged.connect(self.convert_length)
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
        self.velocity_from_unit.currentTextChanged.connect(self.convert_velocity)
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
        self.temp_from_unit.currentTextChanged.connect(self.convert_temperature)
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
        self.mass_from_unit.currentTextChanged.connect(self.convert_mass)
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
        self.pressure_from_unit.currentTextChanged.connect(self.convert_pressure)
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
            from_unit = self.length_from_unit.currentText()
            to_unit = self.length_to_unit.currentText()
            
            if from_unit == to_unit:
                result = value
            else:
                factor = CONVERSIONS['length'].get((from_unit, to_unit))
                if factor is None:
                    self.length_result.setText("Conversion not available")
                    return
                result = value * factor
            
            self.length_result.setText(f"{result:.6f}")
        except ValueError:
            self.length_result.setText("Invalid input")
    
    def convert_velocity(self):
        """Convert velocity units."""
        try:
            value = float(self.velocity_from.text())
            from_unit = self.velocity_from_unit.currentText()
            to_unit = self.velocity_to_unit.currentText()
            
            if from_unit == to_unit:
                result = value
            else:
                factor = CONVERSIONS['velocity'].get((from_unit, to_unit))
                if factor is None:
                    self.velocity_result.setText("Conversion not available")
                    return
                result = value * factor
            
            self.velocity_result.setText(f"{result:.6f}")
        except ValueError:
            self.velocity_result.setText("Invalid input")
    
    def convert_temperature(self):
        """Convert temperature units."""
        try:
            value = float(self.temp_from.text())
            from_unit = self.temp_from_unit.currentText()
            to_unit = self.temp_to_unit.currentText()
            
            # Temperature requires special handling due to offset
            # Convert to Celsius first
            if from_unit == "Celsius":
                celsius = value
            elif from_unit == "Fahrenheit":
                celsius = (value - 32) * 5 / 9
            elif from_unit == "Kelvin":
                celsius = value - 273.15
            else:
                self.temp_result.setText("Invalid unit")
                return
            
            # Convert from Celsius to target unit
            if to_unit == "Celsius":
                result = celsius
            elif to_unit == "Fahrenheit":
                result = celsius * 9 / 5 + 32
            elif to_unit == "Kelvin":
                result = celsius + 273.15
            else:
                self.temp_result.setText("Invalid unit")
                return
            
            self.temp_result.setText(f"{result:.2f}")
        except ValueError:
            self.temp_result.setText("Invalid input")
    
    def convert_mass(self):
        """Convert mass units."""
        try:
            value = float(self.mass_from.text())
            from_unit = self.mass_from_unit.currentText()
            to_unit = self.mass_to_unit.currentText()
            
            if from_unit == to_unit:
                result = value
            else:
                factor = CONVERSIONS['mass'].get((from_unit, to_unit))
                if factor is None:
                    self.mass_result.setText("Conversion not available")
                    return
                result = value * factor
            
            self.mass_result.setText(f"{result:.6f}")
        except ValueError:
            self.mass_result.setText("Invalid input")
    
    def convert_pressure(self):
        """Convert pressure units."""
        try:
            value = float(self.pressure_from.text())
            from_unit = self.pressure_from_unit.currentText()
            to_unit = self.pressure_to_unit.currentText()
            
            if from_unit == to_unit:
                result = value
            else:
                factor = CONVERSIONS['pressure'].get((from_unit, to_unit))
                if factor is None:
                    self.pressure_result.setText("Conversion not available")
                    return
                result = value * factor
            
            self.pressure_result.setText(f"{result:.6f}")
        except ValueError:
            self.pressure_result.setText("Invalid input")
