"""
Configuration Module

Centralized configuration for the Rocket Simulator application.
Includes path management, constants, settings, and translations.
"""

from .paths import Paths
from .constants import Constants
from .settings import Settings
from .translations import TranslationManager, tr, tr_lazy, SUPPORTED_LANGUAGES

# Initialize paths on import
Paths.ensure_dirs()

__all__ = ['Paths', 'Constants', 'Settings', 'TranslationManager', 'tr', 'tr_lazy', 'SUPPORTED_LANGUAGES']
