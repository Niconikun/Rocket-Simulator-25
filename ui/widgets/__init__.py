"""UI widgets package - contains all page widgets.

This package provides the base widget class and all page widgets for the
Rocket Simulator application.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSlot
from src.models.state import StateProvider
from src.models.app_state import ApplicationState
from src.config import tr
from typing import Optional, Any, Callable


class BaseWidget(QWidget):
    """
    Base class for all UI widgets that need access to application state.
    
    This class provides a consistent way to handle state management across all
    widgets, supporting both dependency injection and backward compatibility.
    
    Usage:
        # With explicit state (preferred for testing)
        widget = MyWidget(state=mock_state)
        
        # Without state (uses singleton for backward compatibility)
        widget = MyWidget()
    
    Args:
        state: Optional StateProvider instance. If None, uses ApplicationState singleton.
        parent: Optional parent widget.
    """
    
    def __init__(self, state: Optional[StateProvider] = None, parent=None):
        super().__init__(parent=parent)
        
        # Use provided state or fall back to singleton
        self.state = state if state is not None else ApplicationState.get_instance()
    
    def set_state(self, state: StateProvider) -> None:
        """
        Set or update the state provider for this widget.
        
        Useful for testing or when state needs to be swapped after initialization.
        
        Args:
            state: The StateProvider instance to use
        """
        self.state = state
    
    def create_state_setter(self, key: str, emit_signal: Optional[Callable] = None) -> Callable[[Any], None]:
        """
        Create a lambda function that sets a state value.
        
        This is a helper method to reduce repetitive lambda patterns like:
            lambda v: self.state.set('key', v)
        
        Args:
            key: The state key to set
            emit_signal: Optional signal to emit after setting state
        
        Returns:
            A callable that sets the state value and optionally emits a signal
        
        Usage:
            self.spinbox.valueChanged.connect(
                self.create_state_setter(Constants.StateKeys.SIM_RUNTIME)
            )
            
            # With signal emission
            self.spinbox.valueChanged.connect(
                self.create_state_setter(Constants.StateKeys.WIND_SPEED, self.wind_changed.emit)
            )
        """
        def setter(value: Any) -> None:
            self.state.set(key, value)
            if emit_signal is not None:
                emit_signal()
        return setter
    
    def create_state_setter_with_emit(self, key: str, signal: Callable) -> Callable[[Any], None]:
        """
        Create a lambda function that sets a state value and emits a signal.
        
        Convenience method when you always want to emit a signal after setting state.
        
        Args:
            key: The state key to set
            signal: The signal to emit (e.g., self.changed, self.wind_changed.emit)
        
        Returns:
            A callable that sets the state value and emits the signal
        
        Usage:
            self.spinbox.valueChanged.connect(
                self.create_state_setter_with_emit(Constants.StateKeys.WIND_SPEED, self.wind_changed.emit)
            )
        """
        def setter(value: Any) -> None:
            self.state.set(key, value)
            signal()
        return setter
    
    def get_state_value(self, key: str, default: Any = None) -> Any:
        """
        Get a value from state with a default.
        
        Convenience wrapper around self.state.get().
        
        Args:
            key: The state key to get
            default: Default value if key doesn't exist
        
        Returns:
            The value from state or default
        """
        return self.state.get(key, default)
    
    @staticmethod
    def tr(text: str, context: Optional[str] = None) -> str:
        """
        Translate a string using the application's translation system.
        
        This is a static method that wraps the global tr() function.
        
        Args:
            text: The text to translate
            context: Optional context for disambiguation
        
        Returns:
            The translated string
        
        Usage:
            label = QLabel(self.tr("Simulation Parameters"))
            button = QPushButton(self.tr("Run Simulation"))
        """
        return tr(text, context)
