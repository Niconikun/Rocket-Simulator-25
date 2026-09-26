"""
Wind Configuration Controls

Reusable UI components for wind configuration.
This module extracts common wind-related controls to reduce code duplication
between wind_settings_widget.py and wind_scenario_editor_widget.py.

Usage:
    from ui.components.wind_controls import WindCommonControls, WindModelControls
    
    # Create common wind controls
    common_controls = WindCommonControls(state=state)
    common_controls.add_to_layout(layout)
    
    # Get current values
    speed = common_controls.wind_speed
    direction = common_controls.wind_direction
    ref_height = common_controls.reference_height
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QDoubleSpinBox, 
    QComboBox, QFormLayout, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from src.models.state import StateProvider, StateProxy
from typing import Optional, Callable, Any
from src.config import Constants
import logging

logger = logging.getLogger(__name__)


class WindCommonControls(QWidget):
    """
    Common wind configuration controls.
    
    Provides UI controls for:
    - Wind speed
    - Wind direction
    - Reference height
    
    Emits signals when values change.
    """
    
    wind_changed = pyqtSignal()
    
    def __init__(self, state: Optional[StateProvider] = None, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        self.state = state
        self._create_controls()
        self._setup_connections()
    
    def _create_controls(self):
        """Create the wind control widgets."""
        layout = QFormLayout(self)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Wind speed
        self.wind_speed_spin = QDoubleSpinBox()
        self.wind_speed_spin.setRange(
            Constants.Wind.MIN_WIND_SPEED,
            Constants.Wind.MAX_WIND_SPEED
        )
        self.wind_speed_spin.setValue(Constants.Wind.DEFAULT_WIND_SPEED)
        self.wind_speed_spin.setSuffix(" m/s")
        self.wind_speed_spin.setSingleStep(0.5)
        self.wind_speed_spin.setToolTip(
            f"Wind speed at reference height [{Constants.Wind.MIN_WIND_SPEED}-{Constants.Wind.MAX_WIND_SPEED} m/s]"
        )
        layout.addRow("Wind Speed:", self.wind_speed_spin)
        
        # Wind direction
        self.wind_direction_spin = QDoubleSpinBox()
        self.wind_direction_spin.setRange(
            Constants.Wind.MIN_WIND_DIRECTION,
            Constants.Wind.MAX_WIND_DIRECTION
        )
        self.wind_direction_spin.setValue(Constants.Wind.DEFAULT_WIND_DIRECTION)
        self.wind_direction_spin.setSuffix("°")
        self.wind_direction_spin.setSingleStep(1.0)
        self.wind_direction_spin.setToolTip(
            f"Wind direction (FROM) [{Constants.Wind.MIN_WIND_DIRECTION}-{Constants.Wind.MAX_WIND_DIRECTION}°]\n\n"
            "0° = from North (blows South)\n"
            "90° = from East (blows West)"
        )
        layout.addRow("Wind Direction (FROM):", self.wind_direction_spin)
        
        # Reference height
        self.wind_ref_height_spin = QDoubleSpinBox()
        self.wind_ref_height_spin.setRange(
            Constants.Wind.MIN_REFERENCE_HEIGHT,
            Constants.Wind.MAX_REFERENCE_HEIGHT
        )
        self.wind_ref_height_spin.setValue(Constants.Wind.DEFAULT_REFERENCE_HEIGHT)
        self.wind_ref_height_spin.setSuffix(" m")
        self.wind_ref_height_spin.setSingleStep(1.0)
        self.wind_ref_height_spin.setToolTip(
            f"Reference height for wind measurement [{Constants.Wind.MIN_REFERENCE_HEIGHT}-{Constants.Wind.MAX_REFERENCE_HEIGHT} m]"
        )
        layout.addRow("Reference Height:", self.wind_ref_height_spin)
    
    def _setup_connections(self):
        """Setup signal connections."""
        if self.state:
            # Load current values from state
            self.wind_speed_spin.setValue(
                self.state.get(Constants.StateKeys.WIND_SPEED, Constants.Wind.DEFAULT_WIND_SPEED)
            )
            self.wind_direction_spin.setValue(
                self.state.get(Constants.StateKeys.WIND_DIRECTION, Constants.Wind.DEFAULT_WIND_DIRECTION)
            )
            self.wind_ref_height_spin.setValue(
                self.state.get(Constants.StateKeys.WIND_REFERENCE_HEIGHT, Constants.Wind.DEFAULT_REFERENCE_HEIGHT)
            )
            
            # Connect value changed signals
            self.wind_speed_spin.valueChanged.connect(
                lambda v: self._on_value_changed(Constants.StateKeys.WIND_SPEED, v)
            )
            self.wind_direction_spin.valueChanged.connect(
                lambda v: self._on_value_changed(Constants.StateKeys.WIND_DIRECTION, v)
            )
            self.wind_ref_height_spin.valueChanged.connect(
                lambda v: self._on_value_changed(Constants.StateKeys.WIND_REFERENCE_HEIGHT, v)
            )
        else:
            # Connect directly to signal
            self.wind_speed_spin.valueChanged.connect(self.wind_changed.emit)
            self.wind_direction_spin.valueChanged.connect(self.wind_changed.emit)
            self.wind_ref_height_spin.valueChanged.connect(self.wind_changed.emit)
    
    def _on_value_changed(self, key: str, value: Any):
        """Handle value changes by updating state."""
        if self.state:
            self.state.set(key, value)
        self.wind_changed.emit()
    
    def set_enabled(self, enabled: bool):
        """Enable or disable all controls."""
        self.wind_speed_spin.setEnabled(enabled)
        self.wind_direction_spin.setEnabled(enabled)
        self.wind_ref_height_spin.setEnabled(enabled)
    
    def set_values(self, speed: float, direction: float, ref_height: float):
        """Set all control values."""
        self.wind_speed_spin.setValue(speed)
        self.wind_direction_spin.setValue(direction)
        self.wind_ref_height_spin.setValue(ref_height)
    
    def get_values(self) -> dict:
        """Get all control values as a dictionary."""
        return {
            'wind_speed': self.wind_speed_spin.value(),
            'wind_direction': self.wind_direction_spin.value(),
            'wind_reference_height': self.wind_ref_height_spin.value(),
        }
    
    @property
    def wind_speed(self) -> float:
        """Get current wind speed value."""
        return self.wind_speed_spin.value()
    
    @property
    def wind_direction(self) -> float:
        """Get current wind direction value."""
        return self.wind_direction_spin.value()
    
    @property
    def reference_height(self) -> float:
        """Get current reference height value."""
        return self.wind_ref_height_spin.value()


class WindModelControls(QWidget):
    """
    Wind model-specific configuration controls.
    
    Provides UI controls for model-specific parameters:
    - Model type selection (constant, logarithmic, power_law, gust)
    - Roughness length (for logarithmic/power_law)
    - Power law exponent (for power_law)
    - Gust intensity and length scale (for gust)
    
    Automatically shows/hides controls based on selected model type.
    """
    
    model_changed = pyqtSignal(str)  # Emits model type when changed
    
    # Valid wind model types
    VALID_MODELS = {'constant', 'logarithmic', 'power_law', 'gust'}
    
    def __init__(self, state: Optional[StateProvider] = None, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        self.state = state
        self._create_controls()
        self._setup_connections()
    
    def _create_controls(self):
        """Create the wind model control widgets."""
        layout = QFormLayout(self)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Model type
        self.model_combo = QComboBox()
        self.model_combo.addItems(list(self.VALID_MODELS))
        self.model_combo.setCurrentText('logarithmic')
        self.model_combo.setToolTip("Wind profile model type")
        layout.addRow("Wind Model Type:", self.model_combo)
        
        # Roughness length (for logarithmic/power_law)
        self.roughness_label = QLabel("Roughness Length (z₀):")
        self.roughness_label.setToolTip(
            f"Surface roughness [{Constants.Wind.MIN_ROUGHNESS}-{Constants.Wind.MAX_ROUGHNESS} m]"
        )
        self.roughness_spin = QDoubleSpinBox()
        self.roughness_spin.setRange(
            Constants.Wind.MIN_ROUGHNESS,
            Constants.Wind.MAX_ROUGHNESS
        )
        self.roughness_spin.setValue(Constants.Wind.DEFAULT_ROUGHNESS)
        self.roughness_spin.setSuffix(" m")
        self.roughness_spin.setSingleStep(0.01)
        layout.addRow(self.roughness_label, self.roughness_spin)
        
        # Power law exponent (for power_law)
        self.exponent_label = QLabel("Power Law Exponent (α):")
        self.exponent_label.setToolTip(
            f"Power law exponent [{Constants.Wind.MIN_POWER_LAW_EXPONENT}-{Constants.Wind.MAX_POWER_LAW_EXPONENT}]"
        )
        self.exponent_spin = QDoubleSpinBox()
        self.exponent_spin.setRange(
            Constants.Wind.MIN_POWER_LAW_EXPONENT,
            Constants.Wind.MAX_POWER_LAW_EXPONENT
        )
        self.exponent_spin.setValue(Constants.Wind.DEFAULT_POWER_LAW_EXPONENT)
        self.exponent_spin.setSingleStep(0.01)
        layout.addRow(self.exponent_label, self.exponent_spin)
        
        # Gust intensity (for gust)
        self.gust_intensity_label = QLabel("Gust Intensity (I_u):")
        self.gust_intensity_label.setToolTip(
            f"Turbulence intensity [{Constants.Wind.MIN_GUST_INTENSITY}-{Constants.Wind.MAX_GUST_INTENSITY}]"
        )
        self.gust_intensity_spin = QDoubleSpinBox()
        self.gust_intensity_spin.setRange(
            Constants.Wind.MIN_GUST_INTENSITY,
            Constants.Wind.MAX_GUST_INTENSITY
        )
        self.gust_intensity_spin.setValue(Constants.Wind.DEFAULT_GUST_INTENSITY)
        self.gust_intensity_spin.setSingleStep(0.05)
        layout.addRow(self.gust_intensity_label, self.gust_intensity_spin)
        
        # Gust length scale (for gust)
        self.gust_length_label = QLabel("Gust Length Scale (L_u):")
        self.gust_length_label.setToolTip(
            f"Integral length scale [{Constants.Wind.MIN_GUST_LENGTH}-{Constants.Wind.MAX_GUST_LENGTH} m]"
        )
        self.gust_length_spin = QDoubleSpinBox()
        self.gust_length_spin.setRange(
            Constants.Wind.MIN_GUST_LENGTH,
            Constants.Wind.MAX_GUST_LENGTH
        )
        self.gust_length_spin.setValue(Constants.Wind.DEFAULT_GUST_LENGTH)
        self.gust_length_spin.setSuffix(" m")
        self.gust_length_spin.setSingleStep(10.0)
        layout.addRow(self.gust_length_label, self.gust_length_spin)
    
    def _setup_connections(self):
        """Setup signal connections."""
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        
        if self.state:
            # Load current values from state
            model = self.state.get(Constants.StateKeys.WIND_MODEL_TYPE, 'logarithmic')
            if model in self.VALID_MODELS:
                self.model_combo.setCurrentText(model)
            
            self.roughness_spin.setValue(
                self.state.get(Constants.StateKeys.WIND_ROUGHNESS_LENGTH, Constants.Wind.DEFAULT_ROUGHNESS)
            )
            self.exponent_spin.setValue(
                self.state.get(Constants.StateKeys.WIND_EXPONENT, Constants.Wind.DEFAULT_POWER_LAW_EXPONENT)
            )
            self.gust_intensity_spin.setValue(
                self.state.get(Constants.StateKeys.WIND_GUST_INTENSITY, Constants.Wind.DEFAULT_GUST_INTENSITY)
            )
            self.gust_length_spin.setValue(
                self.state.get(Constants.StateKeys.WIND_GUST_LENGTH_SCALE, Constants.Wind.DEFAULT_GUST_LENGTH)
            )
            
            # Connect value changed signals
            self.roughness_spin.valueChanged.connect(
                lambda v: self._on_value_changed(Constants.StateKeys.WIND_ROUGHNESS_LENGTH, v)
            )
            self.exponent_spin.valueChanged.connect(
                lambda v: self._on_value_changed(Constants.StateKeys.WIND_EXPONENT, v)
            )
            self.gust_intensity_spin.valueChanged.connect(
                lambda v: self._on_value_changed(Constants.StateKeys.WIND_GUST_INTENSITY, v)
            )
            self.gust_length_spin.valueChanged.connect(
                lambda v: self._on_value_changed(Constants.StateKeys.WIND_GUST_LENGTH_SCALE, v)
            )
            
            self._update_visibility()
    
    def _on_model_changed(self, model_type: str):
        """Handle wind model selection change."""
        self._update_visibility()
        if self.state:
            self.state.set(Constants.StateKeys.WIND_MODEL_TYPE, model_type)
        self.model_changed.emit(model_type)
    
    def _on_value_changed(self, key: str, value: Any):
        """Handle value changes by updating state."""
        if self.state:
            self.state.set(key, value)
    
    def _update_visibility(self):
        """Update control visibility based on selected model."""
        model_type = self.model_combo.currentText()
        
        # Hide all model-specific controls by default
        self.roughness_label.setVisible(False)
        self.roughness_spin.setVisible(False)
        self.exponent_label.setVisible(False)
        self.exponent_spin.setVisible(False)
        self.gust_intensity_label.setVisible(False)
        self.gust_intensity_spin.setVisible(False)
        self.gust_length_label.setVisible(False)
        self.gust_length_spin.setVisible(False)
        
        # Show relevant controls based on model
        if model_type in ['logarithmic', 'power_law']:
            self.roughness_label.setVisible(True)
            self.roughness_spin.setVisible(True)
        
        if model_type == 'power_law':
            self.exponent_label.setVisible(True)
            self.exponent_spin.setVisible(True)
        
        if model_type == 'gust':
            self.gust_intensity_label.setVisible(True)
            self.gust_intensity_spin.setVisible(True)
            self.gust_length_label.setVisible(True)
            self.gust_length_spin.setVisible(True)
    
    def set_enabled(self, enabled: bool):
        """Enable or disable all controls."""
        self.model_combo.setEnabled(enabled)
        self.roughness_spin.setEnabled(enabled and self.roughness_spin.isVisible())
        self.exponent_spin.setEnabled(enabled and self.exponent_spin.isVisible())
        self.gust_intensity_spin.setEnabled(enabled and self.gust_intensity_spin.isVisible())
        self.gust_length_spin.setEnabled(enabled and self.gust_length_spin.isVisible())
    
    def set_values(self, model_type: str, roughness: float, exponent: float, 
                   gust_intensity: float, gust_length: float):
        """Set all control values."""
        if model_type in self.VALID_MODELS:
            self.model_combo.setCurrentText(model_type)
        self.roughness_spin.setValue(roughness)
        self.exponent_spin.setValue(exponent)
        self.gust_intensity_spin.setValue(gust_intensity)
        self.gust_length_spin.setValue(gust_length)
    
    def get_values(self) -> dict:
        """Get all control values as a dictionary."""
        return {
            'model_type': self.model_combo.currentText(),
            'roughness': self.roughness_spin.value(),
            'exponent': self.exponent_spin.value(),
            'gust_intensity': self.gust_intensity_spin.value(),
            'gust_length': self.gust_length_spin.value(),
        }
    
    @property
    def model_type(self) -> str:
        """Get current model type."""
        return self.model_combo.currentText()
    
    @property
    def roughness(self) -> float:
        """Get current roughness value."""
        return self.roughness_spin.value()
    
    @property
    def exponent(self) -> float:
        """Get current exponent value."""
        return self.exponent_spin.value()
    
    @property
    def gust_intensity(self) -> float:
        """Get current gust intensity value."""
        return self.gust_intensity_spin.value()
    
    @property
    def gust_length(self) -> float:
        """Get current gust length value."""
        return self.gust_length_spin.value()


class WindControlsFactory:
    """
    Factory for creating complete wind configuration UIs.
    
    Usage:
        # Create a complete wind configuration section
        factory = WindControlsFactory(state=state)
        wind_widget = factory.create_full_wind_controls()
        layout.addWidget(wind_widget)
    """
    
    @staticmethod
    def create_full_wind_controls(state: Optional[StateProvider] = None, 
                                   parent: Optional[QWidget] = None) -> QWidget:
        """Create a widget with all wind controls (common + model-specific)."""
        widget = QWidget(parent=parent)
        layout = QVBoxLayout(widget)
        
        # Create common controls group
        common_group = QGroupBox("Common Wind Parameters")
        common_controls = WindCommonControls(state=state)
        common_layout = QVBoxLayout(common_group)
        common_layout.addWidget(common_controls)
        layout.addWidget(common_group)
        
        # Create model controls group
        model_group = QGroupBox("Wind Model Parameters")
        model_controls = WindModelControls(state=state)
        model_layout = QVBoxLayout(model_group)
        model_layout.addWidget(model_controls)
        layout.addWidget(model_group)
        
        layout.addStretch()
        return widget
