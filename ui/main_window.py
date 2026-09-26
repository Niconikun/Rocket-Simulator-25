"""
Main Application Window

Central PyQt6 window that manages all application tabs and coordinates
between different widget pages.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QHBoxLayout, QWidget,
    QStatusBar, QMenuBar, QMenu, QMessageBox, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QAction, QPalette, QColor
from models.app_state import ApplicationState
import logging
from src.models.state import StateProvider, StateProxy
from src.config import Constants, TranslationManager, tr, SUPPORTED_LANGUAGES
from typing import Optional
import sys

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window with tabbed interface.
    
    Uses a PyQt6 QTabWidget to present the application pages.
    """
    
    def __init__(self, state: Optional[StateProvider] = None):
        """
        Initialize the main application window.
        
        Args:
            state: Optional StateProvider instance. If None, uses ApplicationState singleton.
        """
        super().__init__()
        # Use provided state or fall back to singleton (Phase 3: Dependency Injection)
        self.state = state if state is not None else ApplicationState.get_instance()
        self._app = QApplication.instance()  # Store reference to application
        
        # Initialize translation system
        TranslationManager.initialize(self._app)
        
        self.init_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
        self._setup_keyboard_shortcuts()
        
        # Apply theme based on state (after UI is initialized)
        self._apply_theme_from_state()
    
    def _apply_theme_from_state(self):
        """Apply theme based on saved state."""
        dark_mode = self.state.get(Constants.StateKeys.DARK_MODE_ENABLED, True)
        self.dark_mode_action.setChecked(dark_mode)
        if dark_mode:
            self._apply_dark_theme_to_app()
            self.setStyleSheet(self._get_dark_stylesheet())
        else:
            self._apply_light_theme_to_app()
            self.setStyleSheet(self._get_light_stylesheet())
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(tr("Rocket Simulator Pro"))
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
        from ui.widgets.wind_scenario_editor_widget import WindScenarioEditorWidget
        
        # Create widget instances (Phase 3: Dependency Injection)
        # Pass state to all widgets for better testability and decoupling
        self.simulation_widget = SimulationWidget(state=self.state)
        self.rocket_widget = RocketSettingsWidget(state=self.state)
        self.location_widget = LocationSettingsWidget(state=self.state)
        self.monte_carlo_widget = MonteCarloWidget(state=self.state)
        self.dashboard_widget = DashboardWidget(state=self.state)
        self.units_widget = UnitsConverterWidget(state=self.state)
        self.parachute_widget = ParachuteSettingsWidget(state=self.state)
        self.wind_widget = WindSettingsWidget(state=self.state)
        self.wind_scenario_editor_widget = WindScenarioEditorWidget(state=self.state)
        
        # Add tabs in order matching the application workflow
        self.tabs.addTab(self.simulation_widget, "🚀 Simulation")
        self.tabs.addTab(self.rocket_widget, "🛸 Rocket Settings")
        self.tabs.addTab(self.location_widget, "📍 Location")
        self.tabs.addTab(self.wind_widget, "💨 Wind")
        self.tabs.addTab(self.wind_scenario_editor_widget, "🌪️ Wind Scenarios")
        self.tabs.addTab(self.parachute_widget, "🪂 Parachute")
        self.tabs.addTab(self.dashboard_widget, "📊 Dashboard")
        self.tabs.addTab(self.monte_carlo_widget, "📈 Monte Carlo")
        self.tabs.addTab(self.units_widget, "⚖️ Units")
        
        
        # Connect widget signals for wind updates
        self.wind_widget.wind_changed.connect(self.on_wind_settings_changed)
        self.simulation_widget.status_message.connect(self.statusBar().showMessage) # pyright: ignore[reportOptionalMemberAccess]
        
        # Connect wind scenario editor signals
        self.wind_scenario_editor_widget.scenario_selected.connect(
            self.wind_widget.load_wind_settings
        )
        self.wind_scenario_editor_widget.scenario_selected.connect(
            lambda scenario: self.statusBar().showMessage( # pyright: ignore[reportOptionalMemberAccess]
                f"Wind scenario applied: {scenario.get('model_type', 'unknown')}"
            )
        )
        self.wind_scenario_editor_widget.scenario_saved.connect(
            lambda name: self.statusBar().showMessage(f"Scenario '{name}' saved") # pyright: ignore[reportOptionalMemberAccess]
        )
        
        # Set up two-way sync between wind widgets
        self.wind_scenario_editor_widget.set_wind_settings_widget(self.wind_widget)
        
        # Auto-refresh dashboard when a new simulation is saved
        self.simulation_widget.simulation_saved.connect(
            lambda _sim_id: self.dashboard_widget.load_simulation_history()
        )
        
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
        file_menu = menubar.addMenu(tr("File")) # type: ignore
        
        new_sim_action = QAction(tr("New Simulation"), self)
        new_sim_action.setShortcut("Ctrl+N")
        new_sim_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        new_sim_action.triggered.connect(self.new_simulation)
        file_menu.addAction(new_sim_action) # type: ignore
        
        open_action = QAction(tr("Open Configuration..."), self)
        open_action.setShortcut("Ctrl+O")
        open_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        open_action.triggered.connect(self.open_configuration)
        file_menu.addAction(open_action) # type: ignore
        
        save_action = QAction(tr("Save Configuration..."), self)
        save_action.setShortcut("Ctrl+S")
        save_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        save_action.triggered.connect(self.save_configuration)
        file_menu.addAction(save_action) # type: ignore
        
        file_menu.addSeparator() # type: ignore
        
        exit_action = QAction(tr("Exit"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        exit_action.triggered.connect(self.close_application)
        file_menu.addAction(exit_action) # type: ignore
        
        # Edit menu
        edit_menu = menubar.addMenu(tr("Edit")) # type: ignore
        
        reset_action = QAction(tr("Reset to Defaults"), self)
        reset_action.setShortcut("Ctrl+R")
        reset_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        reset_action.triggered.connect(self.reset_to_defaults)
        edit_menu.addAction(reset_action) # type: ignore
        
        # View menu
        view_menu = menubar.addMenu(tr("View")) # type: ignore
        
        # Dark mode toggle
        self.dark_mode_action = QAction(tr("Dark Mode"), self)
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.setShortcut("Ctrl+Shift+T")
        self.dark_mode_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.dark_mode_action.setChecked(True)  # Start with dark mode
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)
        view_menu.addAction(self.dark_mode_action) # type: ignore
        
        # Language menu
        language_menu = menubar.addMenu(tr("Language")) # type: ignore
        
        # Create language actions
        self.language_actions = {}
        for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
            action = QAction(lang_name, self)
            action.setCheckable(True)
            action.setData(lang_code)
            action.triggered.connect(self.change_language)
            language_menu.addAction(action) # type: ignore
            self.language_actions[lang_code] = action
        
        # Set current language
        current_lang = TranslationManager.get_current_language()
        if current_lang in self.language_actions:
            self.language_actions[current_lang].setChecked(True)
        
        # Help menu
        help_menu = menubar.addMenu(tr("Help")) # type: ignore
        
        about_action = QAction(tr("About"), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action) # type: ignore
    
    def setup_status_bar(self):
        """Setup application status bar."""
        self.statusBar().showMessage(tr("Ready")) # type: ignore
    
    def _setup_keyboard_shortcuts(self):
        """Setup global keyboard shortcuts for the main window."""
        # Tab navigation shortcuts
        # These will be handled by the tab widget itself
        # Ctrl+Tab and Ctrl+Shift+Tab work by default in QTabWidget
        
        # Additional shortcuts can be added here
        # Example: Ctrl+Shift+S for quick save
        # Example: F5 for refresh
        pass
    
    def on_tab_changed(self, index: int):
        """Handle tab change events."""
        self.state.set(Constants.StateKeys.CURRENT_TAB, index)
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
            self.statusBar().showMessage("New simulation created") # pyright: ignore[reportOptionalMemberAccess]
    
    def open_configuration(self):
        """Open a saved configuration file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Configuration", "",
            "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            if self.state.load_from_file(filepath):
                self.statusBar().showMessage(f"Configuration loaded from {filepath}") # pyright: ignore[reportOptionalMemberAccess]
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
                self.statusBar().showMessage(f"Configuration saved to {filepath}") # pyright: ignore[reportOptionalMemberAccess]
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
            self.statusBar().showMessage("All parameters reset to defaults") # pyright: ignore[reportOptionalMemberAccess]
    
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
    
    def toggle_dark_mode(self, checked: bool = None):  # type: ignore
        """Toggle dark mode on/off.
        
        Args:
            checked: If provided, set dark mode to this value.
                   If None, toggle current state.
        """
        if checked is None:
            checked = not self.dark_mode_action.isChecked()
        
        self.dark_mode_action.setChecked(checked)
        
        # Apply theme to the entire application
        if self._app is not None:
            if checked:
                self._apply_dark_theme_to_app()
            else:
                self._apply_light_theme_to_app()
        
        # Also update this window's stylesheet for consistency
        if checked:
            self.setStyleSheet(self._get_dark_stylesheet())
        else:
            self.setStyleSheet(self._get_light_stylesheet())
        
        # Save preference in state
        self.state.set(Constants.StateKeys.DARK_MODE_ENABLED, checked)
        self.statusBar().showMessage(f"Dark mode {'enabled' if checked else 'disabled'}") # pyright: ignore[reportOptionalMemberAccess]
    
    def change_language(self):
        """Change the application language."""
        action = self.sender()
        if action is None:
            return
        
        lang_code = action.data()
        if lang_code is None:
            return
        
        # Load the translation
        TranslationManager.load_translation(lang_code)
        
        # Update checked state
        for code, act in self.language_actions.items():
            act.setChecked(code == lang_code)
        
        # Save language preference in state
        self.state.set(Constants.StateKeys.CURRENT_LANGUAGE, lang_code)
        
        # Refresh UI - retranslate all UI elements
        self._retranslate_ui()
        
        # Show message in status bar
        self.statusBar().showMessage(tr("Language changed to ") + SUPPORTED_LANGUAGES.get(lang_code, lang_code)) # pyright: ignore[reportOptionalMemberAccess]
        logger.info(f"Language changed to: {lang_code}")
    
    def _retranslate_ui(self):
        """Retranslate all UI elements after language change."""
        # Retranslate window title
        self.setWindowTitle(tr("Rocket Simulator Pro"))
        
        # Retranslate status bar
        self.statusBar().showMessage(tr("Ready")) # type: ignore[reportOptionalMemberAccess]
        
        # Note: For full UI retranslation, widgets would need to be recreated
        # or implement a retranslateUi() method in each widget
        # For now, the tr() function uses fallback translations which work immediately
        
    def _apply_dark_theme_to_app(self):
        """Apply dark theme palette to the entire application."""
        if self._app is None:
            return
            
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
        
        self._app.setPalette(dark_palette) # type: ignore
    
    def _apply_light_theme_to_app(self):
        """Apply light theme palette to the entire application."""
        if self._app is None:
            return
            
        # Create explicit light palette (don't rely on system palette)
        light_palette = QPalette()
        
        # Base colors - light theme
        light_palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        light_palette.setColor(QPalette.ColorRole.WindowText, QColor(50, 50, 50))
        light_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(230, 230, 230))
        light_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        light_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(50, 50, 50))
        
        # Button colors
        light_palette.setColor(QPalette.ColorRole.Button, QColor(230, 230, 230))
        light_palette.setColor(QPalette.ColorRole.ButtonText, QColor(50, 50, 50))
        light_palette.setColor(QPalette.ColorRole.BrightText, QColor(0, 0, 0))
        
        # Highlight colors
        light_palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
        light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
        # Link colors
        light_palette.setColor(QPalette.ColorRole.Link, QColor(0, 120, 215))
        light_palette.setColor(QPalette.ColorRole.LinkVisited, QColor(120, 0, 215))
        
        # Placeholder text (for disabled state)
        light_palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(150, 150, 150))
        
        self._app.setPalette(light_palette) # type: ignore
    
    def _apply_dark_theme(self):
        """Apply dark theme to this window only (legacy)."""
        self._apply_dark_theme_to_app()
        self.setStyleSheet(self._get_dark_stylesheet())
    
    def _apply_light_theme(self):
        """Apply light theme to this window only (legacy)."""
        self._apply_light_theme_to_app()
        self.setStyleSheet(self._get_light_stylesheet())
    
    def _get_dark_stylesheet(self) -> str:
        """Get dark theme stylesheet."""
        return """
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
            QTabBar::tab:hover {
                background-color: #4a4a4a;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: #eee;
                border: 1px solid #555;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #777;
            }
            QLineEdit, QDoubleSpinBox, QSpinBox {
                background-color: #3a3a3a;
                color: #eee;
                border: 1px solid #555;
                padding: 4px;
            }
            QComboBox {
                background-color: #3a3a3a;
                color: #eee;
                border: 1px solid #555;
                padding: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #3a3a3a;
                color: #eee;
                selection-background-color: #0078d7;
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
            QCheckBox::indicator:checked {
                background-color: #0078d7;
                border: 1px solid #0078d7;
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
            QTextEdit {
                background-color: #3a3a3a;
                color: #eee;
                border: 1px solid #555;
            }
            QFrame {
                background-color: #2e2e2e;
            }
            QSplitter::handle {
                background-color: #444;
            }
        """
    
    def _get_light_stylesheet(self) -> str:
        """Get light theme stylesheet."""
        return """
            QMainWindow {
                background-color: #f0f0f0;
            }
            QTabWidget::pane {
                border: 1px solid #ccc;
                background-color: #f8f8f8;
            }
            QTabBar::tab {
                background-color: #e8e8e8;
                color: #333;
                padding: 8px 16px;
                border: 1px solid #ccc;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom: 2px solid #0078d7;
                margin-bottom: -1px;
            }
            QTabBar::tab:hover {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ccc;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QPushButton:disabled {
                background-color: #f8f8f8;
                color: #999;
            }
            QLineEdit, QDoubleSpinBox, QSpinBox {
                background-color: #ffffff;
                color: #333;
                border: 1px solid #ccc;
                padding: 4px;
            }
            QComboBox {
                background-color: #ffffff;
                color: #333;
                border: 1px solid #ccc;
                padding: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #333;
                selection-background-color: #0078d7;
                selection-color: white;
            }
            QLabel {
                color: #333;
            }
            QGroupBox {
                border: 1px solid #ccc;
                margin-top: 10px;
                background-color: #f8f8f8;
            }
            QGroupBox::title {
                color: #0078d7;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QStatusBar {
                background-color: #e8e8e8;
                color: #333;
            }
            QMenuBar {
                background-color: #f0f0f0;
                color: #333;
            }
            QMenuBar::item {
                background: transparent;
            }
            QMenuBar::item:selected {
                background-color: #e0e0e0;
            }
            QMenu {
                background-color: #f8f8f8;
                color: #333;
                border: 1px solid #ccc;
            }
            QMenu::item:selected {
                background-color: #0078d7;
                color: white;
            }
            QScrollArea {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
            }
            QWidget {
                background-color: #f0f0f0;
                color: #333;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d7;
                border: 1px solid #0078d7;
            }
            QTableWidget {
                background-color: #ffffff;
                color: #333;
                gridline-color: #ccc;
            }
            QTableWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
            QHeaderView::section {
                background-color: #e8e8e8;
                color: #333;
                padding: 4px;
                border: 1px solid #ccc;
            }
            QTextEdit {
                background-color: #ffffff;
                color: #333;
                border: 1px solid #ccc;
            }
            QFrame {
                background-color: #f0f0f0;
            }
            QSplitter::handle {
                background-color: #ccc;
            }
        """
    
    @staticmethod
    def create_icon():
        """Create application icon."""
        # For now, return empty QIcon
        # In production, load from assets
        return QIcon()
