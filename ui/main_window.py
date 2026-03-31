"""
Main Application Window

Central PyQt6 window that manages all application tabs and coordinates
between different widget pages.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QHBoxLayout, QWidget,
    QStatusBar, QMenuBar, QMenu, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QAction
from models.app_state import ApplicationState
import logging

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window with tabbed interface.
    
    Replaces Streamlit's multi-page approach with PyQt6 QTabWidget.
    Each tab represents a page from the original Streamlit app.
    """
    
    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
        self.init_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Rocket Simulator Pro")
        self.setWindowIcon(self.create_icon())
        self.setMinimumSize(QSize(1200, 800))
        
        # Create central widget with tab container
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(False)
        self.tabs.setTabsClosable(False)
        
        # Import widget classes (will be created in separate files)
        from ui.widgets.simulation_widget import SimulationWidget
        from ui.widgets.rocket_settings_widget import RocketSettingsWidget
        from ui.widgets.location_settings_widget import LocationSettingsWidget
        from ui.widgets.monte_carlo_widget import MonteCarloWidget
        from ui.widgets.dashboard_widget import DashboardWidget
        from ui.widgets.units_converter_widget import UnitsConverterWidget
        from ui.widgets.parachute_settings_widget import ParachuteSettingsWidget
        from ui.widgets.wind_settings_widget import WindSettingsWidget
        
        # Create widget instances
        self.simulation_widget = SimulationWidget()
        self.rocket_widget = RocketSettingsWidget()
        self.location_widget = LocationSettingsWidget()
        self.monte_carlo_widget = MonteCarloWidget()
        self.dashboard_widget = DashboardWidget()
        self.units_widget = UnitsConverterWidget()
        self.parachute_widget = ParachuteSettingsWidget()
        self.wind_widget = WindSettingsWidget()
        
        # Add tabs in order matching original Streamlit app
        self.tabs.addTab(self.simulation_widget, "🚀 Simulation")
        self.tabs.addTab(self.rocket_widget, "🛸 Rocket Settings")
        self.tabs.addTab(self.location_widget, "📍 Location")
        self.tabs.addTab(self.wind_widget, "💨 Wind")
        self.tabs.addTab(self.dashboard_widget, "📊 Dashboard")
        self.tabs.addTab(self.monte_carlo_widget, "📈 Monte Carlo")
        self.tabs.addTab(self.units_widget, "⚖️ Units")
        self.tabs.addTab(self.parachute_widget, "🪂 Parachute")
        
        # Connect widget signals for wind updates
        self.wind_widget.wind_changed.connect(self.on_wind_settings_changed)
        
        # Connect tab change signal
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Set the default tab (Simulation)
        self.tabs.setCurrentIndex(0)
        
        layout.addWidget(self.tabs)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
    
    def setup_menu_bar(self):
        """Setup application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_sim_action = QAction("New Simulation", self)
        new_sim_action.triggered.connect(self.new_simulation)
        file_menu.addAction(new_sim_action)
        
        open_action = QAction("Open Configuration...", self)
        open_action.triggered.connect(self.open_configuration)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save Configuration...", self)
        save_action.triggered.connect(self.save_configuration)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close_application)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        reset_action = QAction("Reset to Defaults", self)
        reset_action.triggered.connect(self.reset_to_defaults)
        edit_menu.addAction(reset_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_status_bar(self):
        """Setup application status bar."""
        self.statusBar().showMessage("Ready")
    
    def on_tab_changed(self, index: int):
        """Handle tab change events."""
        self.state.set('current_tab', index)
        logger.info(f"Switched to tab {index}")
    
    def on_wind_settings_changed(self):
        """Handle wind settings changes from the wind widget."""
        logger.info("Wind settings changed - updating simulation parameters")
    
    def new_simulation(self):
        """Create a new simulation."""
        reply = QMessageBox.question(
            self, "New Simulation",
            "Reset all parameters to create a new simulation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.state.reset()
            self.statusBar().showMessage("New simulation created")
    
    def open_configuration(self):
        """Open a saved configuration file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Configuration", "",
            "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            if self.state.load_from_file(filepath):
                self.statusBar().showMessage(f"Configuration loaded from {filepath}")
            else:
                QMessageBox.critical(self, "Error", "Failed to load configuration")
    
    def save_configuration(self):
        """Save current configuration to file."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration", "",
            "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            if self.state.save_to_file(filepath):
                self.statusBar().showMessage(f"Configuration saved to {filepath}")
            else:
                QMessageBox.critical(self, "Error", "Failed to save configuration")
    
    def reset_to_defaults(self):
        """Reset application state to defaults."""
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            "Are you sure you want to reset all parameters to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.state.reset()
            self.statusBar().showMessage("All parameters reset to defaults")
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About Rocket Simulator Pro",
            "Rocket Simulator Pro v2.0\n\n"
            "A comprehensive rocket flight simulation tool\n\n"
            "Built with PyQt6\n"
            "Physics Engine: Custom\n\n"
            "© 2026 Rocket Simulator Team"
        )
    
    def close_application(self):
        """Close the application."""
        self.close()
    
    @staticmethod
    def create_icon():
        """Create application icon."""
        # For now, return empty QIcon
        # In production, load from assets
        return QIcon()
