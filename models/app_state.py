"""
Application State Compatibility Shim

This module preserves the legacy `models.app_state` import path while the
actual implementation has been moved to `src/models/app_state.py`.
"""

from src.models.app_state import ApplicationState

__all__ = ['ApplicationState']
