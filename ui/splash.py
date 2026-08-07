"""
Splash Screen Module
===================

Programmatic splash screen for Rocket Simulator Pro with progress bar.

This module provides a custom splash screen that can display loading progress
and status messages during application initialization.

Usage:
    from ui.splash import SplashScreen
    
    splash = SplashScreen()
    splash.show()
    splash.update_progress(25, "Loading models...")
    app.processEvents()
    
    # Later...
    splash.update_progress(75, "Initializing UI...")
    app.processEvents()
    
    # Finally
    splash.finish(main_window)
"""

from PyQt6.QtWidgets import QSplashScreen
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient, QBrush, QPen, QPolygon
from PyQt6.QtCore import pyqtSignal, QObject
import logging

logger = logging.getLogger(__name__)


class SplashScreen(QSplashScreen):
    """Custom splash screen with progress bar and status messages.
    
    Features:
    - Programmatic drawing (no external image dependencies)
    - Progress bar at bottom
    - Status message display
    - Smooth animations
    - Configurable colors and sizes
    """
    
    # Signals for async notifications
    progress_updated = pyqtSignal(int, str)  # progress_percent, message
    
    def __init__(self, width: int = 600, height: int = 400):
        """Initialize splash screen with custom size."""
        # Initialize instance variables first
        self._width = width
        self._height = height
        self._progress = 0
        self._message = "Loading..."
        self._show_progress_bar = True
        self._progress_color = QColor(255, 100, 30)
        self._background_color = QColor(15, 20, 40)
        self._text_color = QColor(255, 255, 255)
        self._accent_color = QColor(100, 180, 255)
        
        # Create pixmap after instance variables are set
        self._pixmap = self._create_pixmap(width, height)
        
        # Call parent constructor
        super().__init__(self._pixmap)
        
        # Set window properties
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(QSize(width, height))
        
        # Center on screen
        self.move_to_center()
    
    def _create_pixmap(self, width: int, height: int) -> QPixmap:
        """Create the splash screen pixmap with all static elements."""
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        self._draw_background(painter, width, height)
        
        # Draw accent lines
        self._draw_accent_lines(painter, width, height)
        
        # Draw title and subtitle
        self._draw_title(painter, width, height)
        
        # Draw rocket icon
        self._draw_rocket(painter, width, height)
        
        # Draw version
        self._draw_version(painter, width, height)
        
        painter.end()
        return pixmap
    
    def _draw_background(self, painter: QPainter, width: int, height: int):
        """Draw the gradient background."""
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0.0, QColor(10, 14, 35))
        gradient.setColorAt(0.6, QColor(18, 28, 60))
        gradient.setColorAt(1.0, QColor(8, 10, 25))
        painter.fillRect(0, 0, width, height, QBrush(gradient))
    
    def _draw_accent_lines(self, painter: QPainter, width: int, height: int):
        """Draw the accent lines at top and bottom."""
        pen = QPen(self._accent_color)
        pen.setWidth(4)
        painter.setPen(pen)
        painter.drawLine(0, 3, width, 3)
        painter.drawLine(0, height - 3, width, height - 3)
    
    def _draw_title(self, painter: QPainter, width: int, height: int):
        """Draw the application title and subtitle."""
        # Title
        title_font = QFont("Segoe UI", 32, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(
            0, 80, width, 60,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "Rocket Simulator Pro"
        )
        
        # Subtitle
        sub_font = QFont("Segoe UI", 13)
        painter.setFont(sub_font)
        painter.setPen(QColor(180, 200, 255))
        painter.drawText(
            0, 145, width, 36,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "6-DOF Flight Simulation"
        )
    
    def _draw_rocket(self, painter: QPainter, width: int, height: int):
        """Draw the rocket icon programmatically."""
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
        painter.drawPolygon(QPolygon([QPoint(x, y) for x, y in body_points]))
        
        # Window
        painter.setBrush(QBrush(QColor(100, 180, 255, 200)))
        painter.setPen(QPen(QColor(80, 140, 220), 1))
        painter.drawEllipse(cx - 7, rocket_top + 22, 14, 14)
        
        # Left fin
        painter.setBrush(QBrush(QColor(255, 100, 30)))
        painter.setPen(QPen(QColor(200, 70, 10), 1))
        fin_l = [
            QPoint(cx - 12, rocket_top + 50),
            QPoint(cx - 24, rocket_top + 72),
            QPoint(cx - 12, rocket_top + 65)
        ]
        painter.drawPolygon(QPolygon(fin_l))
        
        # Right fin
        fin_r = [
            QPoint(cx + 12, rocket_top + 50),
            QPoint(cx + 24, rocket_top + 72),
            QPoint(cx + 12, rocket_top + 65)
        ]
        painter.drawPolygon(QPolygon(fin_r))
        
        # Flame
        flame_gradient = QLinearGradient(cx, rocket_top + 65, cx, rocket_top + 90)
        flame_gradient.setColorAt(0.0, QColor(255, 200, 50, 230))
        flame_gradient.setColorAt(0.5, QColor(255, 100, 10, 180))
        flame_gradient.setColorAt(1.0, QColor(255, 50, 0, 0))
        painter.setBrush(QBrush(flame_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        flame = [
            QPoint(cx - 8, rocket_top + 65),
            QPoint(cx, rocket_top + 90),
            QPoint(cx + 8, rocket_top + 65)
        ]
        painter.drawPolygon(QPolygon(flame))
    
    def _draw_version(self, painter: QPainter, width: int, height: int):
        """Draw the version information."""
        ver_font = QFont("Segoe UI", 10)
        painter.setFont(ver_font)
        painter.setPen(QColor(130, 150, 200))
        painter.drawText(
            0, height - 45, width, 25,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "Version 2.0.0"
        )
    
    def move_to_center(self):
        """Center the splash screen on the primary screen."""
        screen = self.screen()
        if screen is not None:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)
    
    def update_progress(self, percent: int, message: str = "") -> None:
        """Update the progress bar and status message.
        
        Args:
            percent: Progress percentage (0-100)
            message: Status message to display
        """
        self._progress = max(0, min(100, percent))
        if message:
            self._message = message
        
        # Force repaint
        self._update_pixmap()
        self.repaint()
        
        # Emit signal for external tracking
        self.progress_updated.emit(self._progress, self._message)
    
    def set_message(self, message: str) -> None:
        """Set the status message without changing progress."""
        self._message = message
        self._update_pixmap()
        self.repaint()
    
    def show_progress_bar(self, show: bool = True) -> None:
        """Show or hide the progress bar."""
        self._show_progress_bar = show
        self._update_pixmap()
        self.repaint()
    
    def _update_pixmap(self) -> None:
        """Update the pixmap with current progress and message."""
        # Create new pixmap with static elements
        new_pixmap = self._create_pixmap(self._width, self._height)
        
        # Add dynamic elements
        painter = QPainter(new_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw progress bar if enabled
        if self._show_progress_bar:
            self._draw_progress_bar(painter)
        
        # Draw status message
        self._draw_status_message(painter)
        
        painter.end()
        
        self._pixmap = new_pixmap
        self.setPixmap(self._pixmap)
    
    def _draw_progress_bar(self, painter: QPainter) -> None:
        """Draw the progress bar at the bottom of the splash screen."""
        width = self._width
        height = self._height
        
        # Progress bar background
        bar_height = 8
        bar_y = height - 25
        bar_margin = 40
        bar_width = width - 2 * bar_margin
        
        # Background (dark)
        painter.setBrush(QBrush(QColor(20, 25, 45)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(bar_margin, bar_y, bar_width, bar_height)
        
        # Progress fill (accent color)
        fill_width = int(bar_width * self._progress / 100)
        if fill_width > 0:
            painter.setBrush(QBrush(self._progress_color))
            painter.drawRect(bar_margin, bar_y, fill_width, bar_height)
        
        # Border
        painter.setPen(QPen(QColor(80, 90, 120), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(bar_margin, bar_y, bar_width, bar_height)
    
    def _draw_status_message(self, painter: QPainter) -> None:
        """Draw the status message at the bottom."""
        width = self._width
        height = self._height
        
        # Message font
        msg_font = QFont("Segoe UI", 9)
        painter.setFont(msg_font)
        painter.setPen(self._progress_color)
        
        # Draw message above progress bar
        painter.drawText(
            0, height - 20, width, 20,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            self._message
        )
    
    def set_colors(self, 
                   background: QColor = None,
                   text: QColor = None,
                   accent: QColor = None,
                   progress: QColor = None) -> None:
        """Set custom colors for the splash screen.
        
        Args:
            background: Background gradient base color
            text: Text color
            accent: Accent color for lines and highlights
            progress: Progress bar color
        """
        if background:
            self._background_color = background
        if text:
            self._text_color = text
        if accent:
            self._accent_color = accent
        if progress:
            self._progress_color = progress
        
        self._update_pixmap()
        self.repaint()
    
    def set_dark_theme(self) -> None:
        """Set dark theme colors."""
        self.set_colors(
            background=QColor(10, 14, 35),
            text=QColor(255, 255, 255),
            accent=QColor(100, 180, 255),
            progress=QColor(255, 100, 30)
        )
    
    def set_light_theme(self) -> None:
        """Set light theme colors."""
        self.set_colors(
            background=QColor(240, 245, 255),
            text=QColor(30, 40, 60),
            accent=QColor(50, 100, 200),
            progress=QColor(255, 100, 30)
        )


def create_splash_pixmap(width: int = 600, height: int = 380) -> QPixmap:
    """Create a programmatic splash screen pixmap (backward compatibility).
    
    This function is kept for backward compatibility with existing code.
    For new code, use SplashScreen class directly.
    """
    splash = SplashScreen(width, height)
    return splash._pixmap


class SplashManager(QObject):
    """Manager for splash screen with automatic progress updates.
    
    This class provides a convenient way to manage splash screen with
    automatic progress tracking across multiple initialization steps.
    
    Usage:
        manager = SplashManager()
        manager.show()
        
        manager.begin_step("Loading models", 25)
        # ... load models ...
        
        manager.begin_step("Initializing UI", 50)
        # ... init UI ...
        
        manager.finish(window)
    """
    
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self, use_dark_theme: bool = True):
        super().__init__()
        self._splash: Optional[SplashScreen] = None
        self._use_dark_theme = use_dark_theme
        self._total_steps = 0
        self._current_step = 0
        self._step_weights = []
    
    def show(self) -> None:
        """Create and show the splash screen."""
        self._splash = SplashScreen()
        if self._use_dark_theme:
            self._splash.set_dark_theme()
        self._splash.show()
    
    def begin_step(self, message: str, weight: int = 1) -> None:
        """Begin a new initialization step.
        
        Args:
            message: Description of the current step
            weight: Weight of this step (1 = equal to others)
        """
        if self._splash is None:
            return
        
        self._total_steps += weight
        self._step_weights.append(weight)
        self._current_step += weight
        
        progress = min(100, int(100 * self._current_step / max(1, self._total_steps)))
        self._splash.update_progress(progress, message)
    
    def increment_step(self, amount: int = 1) -> None:
        """Increment progress within current step."""
        if self._splash is None:
            return
        
        self._current_step += amount
        progress = min(100, int(100 * self._current_step / max(1, self._total_steps)))
        self._splash.update_progress(progress)
    
    def set_message(self, message: str) -> None:
        """Set status message without changing progress."""
        if self._splash is not None:
            self._splash.set_message(message)
    
    def finish(self, window) -> None:
        """Finish splash and show main window."""
        if self._splash is not None:
            self._splash.finish(window)
            self._splash = None
    
    def hide(self) -> None:
        """Hide the splash screen without finishing."""
        if self._splash is not None:
            self._splash.hide()
    
    @property
    def is_visible(self) -> bool:
        """Check if splash screen is currently visible."""
        return self._splash is not None and self._splash.isVisible()