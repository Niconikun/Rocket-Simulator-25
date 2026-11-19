"""Shared pytest fixtures for the Rocket Simulator test suite."""

import os
import sys

import pytest

# Headless Qt for any test that touches QObject/pyqtSignal (also set in CI)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session", autouse=True)
def qapplication():
    """Provide a session-wide QApplication.

    Several non-UI modules (e.g. src/utils/event_bus.py) emit pyqtSignals on
    QObject instances. Emitting a Qt signal without a QApplication segfaults
    Qt on headless runners, so create one once per test session.
    """
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Exit immediately with the real test status when Qt was loaded.

    On headless runners the interpreter segfaults (SIGSEGV, exit 139) while
    tearing down Qt/pyvista/vtk objects at shutdown, which would mask the
    actual pytest result. Skipping interpreter teardown avoids that.
    trylast so the terminal summary/failure details are printed first.
    """
    if "PyQt6.QtWidgets" in sys.modules:
        os._exit(int(exitstatus))
