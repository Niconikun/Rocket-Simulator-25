"""
Rocket Simulator Pro - PyQt6 Application Entry Point

This is the main entry point for the PyQt6 version of the Rocket Simulator GUI.

To run:
    python main.py

To run as executable (after PyInstaller):
    RocketSimulator.exe
"""

import sys
import os
import logging
import traceback
from pathlib import Path
from datetime import datetime

# Disable Qt WebEngine sandbox before any Qt imports (required on Windows)
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rocket_simulator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.splash import SplashScreen, SplashManager
from ui.main_window import MainWindow
from models.app_state import ApplicationState

from src.models.state import StateProvider

def apply_dark_theme(app):
    """Apply dark theme to the application."""
    from PyQt6.QtGui import QPalette, QColor
    
    dark_palette = QPalette()
    
    # Base colors
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(40, 40, 40))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(55, 55, 55))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 220, 220))
    
    # Button colors
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 50))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    
    # Disabled state - Note: In Qt6, disabled colors use the Disabled color group
    # For text colors in disabled state, we use PlaceholderText as it's commonly used
    dark_palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(120, 120, 120))
    
    # Highlight colors
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    
    # Link colors
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(50, 150, 255))
    dark_palette.setColor(QPalette.ColorRole.LinkVisited, QColor(200, 100, 255))
    
    app.setPalette(dark_palette)
    
    # Set style sheet for better dark theme
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2e2e2e;
        }
        QTabWidget::pane {
            border: 1px solid #444;
        }
        QTabBar::tab {
            background-color: #3a3a3a;
            color: #ddd;
            padding: 8px 16px;
            border: 1px solid #444;
        }
        QTabBar::tab:selected {
            background-color: #4a4a4a;
            border-bottom: 2px solid #0078d7;
        }
        QPushButton {
            background-color: #4a4a4a;
            color: #eee;
            border: 1px solid #555;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background-color: #5a5a5a;
        }
        QPushButton:pressed {
            background-color: #3a3a3a;
        }
        QLineEdit, QDoubleSpinBox, QSpinBox {
            background-color: #3a3a3a;
            color: #eee;
            border: 1px solid #555;
        }
        QComboBox {
            background-color: #3a3a3a;
            color: #eee;
            border: 1px solid #555;
        }
        QComboBox QAbstractItemView {
            background-color: #3a3a3a;
            color: #eee;
        }
        QLabel {
            color: #ddd;
        }
        QGroupBox {
            border: 1px solid #444;
            margin-top: 10px;
        }
        QGroupBox::title {
            color: #0078d7;
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QStatusBar {
            background-color: #3a3a3a;
            color: #ddd;
        }
        QMenuBar {
            background-color: #3a3a3a;
            color: #ddd;
        }
        QMenuBar::item {
            background: transparent;
        }
        QMenuBar::item:selected {
            background-color: #4a4a4a;
        }
        QMenu {
            background-color: #3a3a3a;
            color: #ddd;
            border: 1px solid #555;
        }
        QMenu::item:selected {
            background-color: #0078d7;
            color: white;
        }
        QScrollArea {
            background-color: #2e2e2e;
            border: 1px solid #444;
        }
        QWidget {
            background-color: #2e2e2e;
            color: #ddd;
        }
        QCheckBox {
            spacing: 5px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
        QTableWidget {
            background-color: #3a3a3a;
            color: #ddd;
            gridline-color: #444;
        }
        QTableWidget::item:selected {
            background-color: #0078d7;
            color: white;
        }
        QHeaderView::section {
            background-color: #4a4a4a;
            color: #eee;
            padding: 4px;
            border: 1px solid #555;
        }
    """)


def load_state(app, state):
    """Load application state from file."""
    state_file = "last_session.json"
    if os.path.exists(state_file):
        try:
            logger.info(f"Loading session from {state_file}")
            if state.load_from_file(state_file):
                logger.info("Session loaded successfully")
                return True
        except Exception as e:
            logger.warning(f"Failed to load session: {e}")
    return False


def save_state(app, state):
    """Save application state to file."""
    state_file = "last_session.json"
    try:
        logger.info(f"Saving session to {state_file}")
        if state.save_to_file(state_file):
            logger.info("Session saved successfully")
            return True
    except Exception as e:
        logger.warning(f"Failed to save session: {e}")
    return False


def main():
    """
    Main application entry point.
    
    Creates and runs the PyQt6 application with MainWindow.
    """
    logger.info("="*60)
    logger.info("Rocket Simulator Pro v2.0.3 - Starting Application")
    logger.info("="*60)
    
    try:
        # Create Qt Application
        app = QApplication(sys.argv)
        
        # Set application properties
        app.setApplicationName("Rocket Simulator Pro")
        app.setApplicationVersion("2.0.3")
        app.setOrganizationName("Rocket Simulator Team")
        
        logger.info("PyQt6 Application initialized")

        # Initialize ApplicationState explicitly (Phase 3: Dependency Injection)
        # Create the singleton instance explicitly for dependency injection
        state = ApplicationState()
        
        # Show splash screen with progress
        splash_manager = SplashManager(use_dark_theme=True)
        splash_manager.show()
        app.processEvents()
        
        # Update splash with initialization steps
        splash_manager.begin_step("Initializing application...", 10)
        app.processEvents()
        
        # Apply dark theme
        splash_manager.begin_step("Applying dark theme...", 20)
        app.processEvents()
        apply_dark_theme(app)
        logger.info("Dark theme applied")
        
        # Load last session if available
        splash_manager.begin_step("Loading previous session...", 30)
        app.processEvents()
        load_state(app, state)
        
        # Initialize main window
        splash_manager.begin_step("Creating main window...", 60)
        app.processEvents()
        window = MainWindow(state=state)
        
        # Connect state persistence to window using aboutToQuit signal
        app.aboutToQuit.connect(lambda: save_state(app, state))
        
        # Final step
        splash_manager.begin_step("Finalizing...", 100)
        app.processEvents()
        
        # Create and show main window (maximized)
        window.showMaximized()

        # Close splash once the main window is ready
        splash_manager.finish(window)
        
        logger.info("Main window displayed")
        
        # Run application event loop
        exit_code = app.exec()
        
        # Ensure state is saved on exit
        save_state(app, state)
        
        logger.info(f"Application closed with exit code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        traceback.print_exc()
        print(f"FATAL ERROR: {e}")
        return 1


if __name__ == "__main__":
    # Required so PyInstaller-frozen builds don't relaunch the whole app when
    # the Monte Carlo widget spawns ProcessPoolExecutor worker processes.
    import multiprocessing
    multiprocessing.freeze_support()

    exit_code = main()
    sys.exit(exit_code)
