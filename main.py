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
from pathlib import Path

# Disable Qt WebEngine sandbox before any Qt imports (required on Windows)
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")

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

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient, QBrush, QPen
from ui.main_window import MainWindow


def create_splash_pixmap(width: int = 600, height: int = 380) -> QPixmap:
    """Create a programmatic splash screen pixmap."""
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background gradient (dark space theme)
    gradient = QLinearGradient(0, 0, 0, height)
    gradient.setColorAt(0.0, QColor(10, 14, 35))
    gradient.setColorAt(0.6, QColor(18, 28, 60))
    gradient.setColorAt(1.0, QColor(8, 10, 25))
    painter.fillRect(0, 0, width, height, QBrush(gradient))

    # Accent line at top
    pen = QPen(QColor(255, 100, 30))
    pen.setWidth(4)
    painter.setPen(pen)
    painter.drawLine(0, 3, width, 3)

    # Accent line at bottom
    painter.drawLine(0, height - 3, width, height - 3)

    # App title
    title_font = QFont("Segoe UI", 32, QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(0, 80, width, 60, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "Rocket Simulator Pro")

    # Subtitle / tagline
    sub_font = QFont("Segoe UI", 13)
    painter.setFont(sub_font)
    painter.setPen(QColor(180, 200, 255))
    painter.drawText(0, 145, width, 36, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "6-DOF Flight Simulation")

    # Simple rocket icon (drawn programmatically)
    cx = width // 2
    rocket_top = 200

    # Body
    painter.setBrush(QBrush(QColor(220, 225, 240)))
    painter.setPen(QPen(QColor(150, 160, 200), 1))
    body_points = [
        (cx - 12, rocket_top + 30),
        (cx, rocket_top),
        (cx + 12, rocket_top + 30),
        (cx + 12, rocket_top + 65),
        (cx - 12, rocket_top + 65),
    ]
    from PyQt6.QtGui import QPolygon
    from PyQt6.QtCore import QPoint
    painter.drawPolygon(QPolygon([QPoint(x, y) for x, y in body_points]))

    # Window
    painter.setBrush(QBrush(QColor(100, 180, 255, 200)))
    painter.setPen(QPen(QColor(80, 140, 220), 1))
    painter.drawEllipse(cx - 7, rocket_top + 22, 14, 14)

    # Left fin
    painter.setBrush(QBrush(QColor(255, 100, 30)))
    painter.setPen(QPen(QColor(200, 70, 10), 1))
    fin_l = [QPoint(cx - 12, rocket_top + 50), QPoint(cx - 24, rocket_top + 72), QPoint(cx - 12, rocket_top + 65)]
    painter.drawPolygon(QPolygon(fin_l))

    # Right fin
    fin_r = [QPoint(cx + 12, rocket_top + 50), QPoint(cx + 24, rocket_top + 72), QPoint(cx + 12, rocket_top + 65)]
    painter.drawPolygon(QPolygon(fin_r))

    # Flame
    flame_gradient = QLinearGradient(cx, rocket_top + 65, cx, rocket_top + 90)
    flame_gradient.setColorAt(0.0, QColor(255, 200, 50, 230))
    flame_gradient.setColorAt(0.5, QColor(255, 100, 10, 180))
    flame_gradient.setColorAt(1.0, QColor(255, 50, 0, 0))
    painter.setBrush(QBrush(flame_gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    flame = [QPoint(cx - 8, rocket_top + 65), QPoint(cx, rocket_top + 90), QPoint(cx + 8, rocket_top + 65)]
    painter.drawPolygon(QPolygon(flame))

    # Version label
    ver_font = QFont("Segoe UI", 10)
    painter.setFont(ver_font)
    painter.setPen(QColor(130, 150, 200))
    painter.drawText(0, height - 45, width, 25, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "Version 2.0.0")

    # Loading label
    load_font = QFont("Segoe UI", 9)
    painter.setFont(load_font)
    painter.setPen(QColor(255, 100, 30))
    painter.drawText(0, height - 22, width, 20, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "Loading...")

    painter.end()
    return pixmap


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

        # Show splash screen
        splash = QSplashScreen(create_splash_pixmap())
        splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        splash.show()
        app.processEvents()

        # Create and show main window (maximized)
        window = MainWindow()
        window.showMaximized()

        # Close splash once the main window is ready
        splash.finish(window)
        
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
