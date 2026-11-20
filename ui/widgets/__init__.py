"""UI widgets package - contains all page widgets.

This package provides the base widget class and all page widgets for the
Rocket Simulator application.
"""

from PyQt6.QtWidgets import QWidget
from src.models.state import StateProvider
from src.models.app_state import ApplicationState
from src.config import tr
from typing import Optional


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
