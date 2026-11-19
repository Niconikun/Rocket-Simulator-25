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


_EXITSTATUS = None


def pytest_sessionfinish(session, exitstatus):
    """Remember the real test exit status (see pytest_unconfigure)."""
    global _EXITSTATUS
    _EXITSTATUS = int(exitstatus)


def pytest_unconfigure(config):
    """Exit immediately with the real test status when Qt was loaded.

    On headless runners the interpreter segfaults (SIGSEGV, exit 139) while
    tearing down Qt/pyvista/vtk objects after the run, which would mask the
    actual pytest result. unconfigure runs after the terminal summary is
    printed, so logs stay complete; skipping interpreter teardown then avoids
    the segfault.
    """
    if _EXITSTATUS is not None and "PyQt6.QtWidgets" in sys.modules:
        os._exit(_EXITSTATUS)
