"""
Rocket Simulator Pro - PyQt6 Application Entry Point

This is the main entry point for the PyQt6 version of the Rocket Simulator GUI.

To run:
    python main.py

To run as executable (after PyInstaller):
    RocketSimulator.exe
"""

import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rocket_simulator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    """
    Main application entry point.
    
    Creates and runs the PyQt6 application with MainWindow.
    """
    logger.info("="*60)
    logger.info("Rocket Simulator Pro v2.0 - Starting Application")
    logger.info("="*60)
    
    try:
        # Create Qt Application
        app = QApplication(sys.argv)
        
        # Set application properties
        app.setApplicationName("Rocket Simulator Pro")
        app.setApplicationVersion("2.0.0")
        #app.setApplicationAuthor("Rocket Simulator Team")
        
        logger.info("PyQt6 Application initialized")
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("Main window displayed")
        
        # Run application event loop
        exit_code = app.exec()
        
        logger.info(f"Application closed with exit code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"FATAL ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
