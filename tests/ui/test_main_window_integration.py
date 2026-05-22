"""Minimal GUI integration tests for MainWindow signal wiring."""

import os
import unittest

# Ensure Qt can initialize in headless CI/local test runs.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
import ui.widgets.location_settings_widget as location_widget_module
import ui.widgets.dashboard_widget as dashboard_widget_module


class TestMainWindowIntegration(unittest.TestCase):
    """Smoke tests for MainWindow and key widget signal integration."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        # Force lightweight label-based fallback to avoid WebEngine runtime requirements.
        self._old_location_webengine = location_widget_module.HAS_WEBENGINE
        self._old_dashboard_webengine = dashboard_widget_module.HAS_WEBENGINE
        location_widget_module.HAS_WEBENGINE = False
        dashboard_widget_module.HAS_WEBENGINE = False

        self.window = MainWindow()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        location_widget_module.HAS_WEBENGINE = self._old_location_webengine
        dashboard_widget_module.HAS_WEBENGINE = self._old_dashboard_webengine

    def test_main_window_builds_key_widgets(self):
        """MainWindow should build core widgets used by simulation workflow."""
        self.assertIsNotNone(self.window.simulation_widget)
        self.assertIsNotNone(self.window.dashboard_widget)
        self.assertIsNotNone(self.window.statusBar())

    def test_simulation_saved_refreshes_dashboard(self):
        """Emitting simulation_saved should invoke dashboard history reload."""
        calls = {"count": 0}

        def fake_reload(*args):
            calls["count"] += 1

        self.window.dashboard_widget.load_simulation_history = fake_reload

        self.window.simulation_widget.simulation_saved.emit("sim-test-001")
        self.app.processEvents()

        self.assertEqual(calls["count"], 1)

    def test_status_message_updates_status_bar(self):
        """Simulation status signal should be reflected in the main status bar."""
        expected_message = "Simulation paused"
        self.window.simulation_widget.status_message.emit(expected_message)
        self.app.processEvents()

        self.assertEqual(self.window.statusBar().currentMessage(), expected_message)


if __name__ == "__main__":
    unittest.main()
