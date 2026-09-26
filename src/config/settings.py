"""
Application Settings

Manages application-wide settings and configuration.
Settings can be loaded from and saved to configuration files.

Usage:
    from src.config import Settings
    
    # Get a setting
    dark_mode = Settings.get('dark_mode_enabled', True)
    
    # Set a setting
    Settings.set('dark_mode_enabled', False)
    
    # Save to file
    Settings.save()
    
    # Load from file
    Settings.load()
"""

import json
import os
from pathlib import Path
from typing import Any, Optional, Dict
from .paths import Paths


class SettingsManager:
    """
    Manages application settings with automatic persistence.
    
    Settings are stored in a JSON file and loaded automatically on first access.
    Changes are written to disk when save() is called or automatically on shutdown.
    """
    
    _instance: Optional['SettingsManager'] = None
    _settings: Dict[str, Any] = {}
    _loaded: bool = False
    _file_path: Path = Paths.DATA_DIR / "settings.json"
    
    # Default settings
    _defaults: Dict[str, Any] = {
        'dark_mode_enabled': True,
        'theme': 'dark',
        'auto_save': True,
        'simulation_timeout': 3600,  # seconds
        'max_recent_simulations': 10,
        'show_tooltips': True,
        'show_advanced_options': False,
        'language': 'en',
        'unit_system': 'metric',
        'date_format': 'YYYY-MM-DD',
        'time_format': 'HH:mm:ss',
        'log_level': 'INFO',
    }
    
    def __new__(cls) -> 'SettingsManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """Initialize settings, loading from file if it exists."""
        if not self._loaded:
            self._settings = self._defaults.copy()
            self._load()
            self._loaded = True
    
    def _load(self) -> None:
        """Load settings from file."""
        try:
            if self._file_path.exists():
                with open(self._file_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    if isinstance(loaded_settings, dict):
                        # Merge with defaults (defaults take precedence for new keys)
                        self._settings.update(loaded_settings)
        except (OSError, json.JSONDecodeError) as e:
            # If loading fails, use defaults
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load settings: {e}. Using defaults.")
    
    def save(self) -> bool:
        """Save current settings to file.
        
        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Ensure directory exists
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._file_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            return True
        except OSError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save settings: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if key doesn't exist
        
        Returns:
            The setting value, or default if not found
        """
        self._initialize()
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value.
        
        Args:
            key: Setting key
            value: Value to set
        """
        self._initialize()
        self._settings[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings as a dictionary.
        
        Returns:
            A copy of all current settings
        """
        self._initialize()
        return self._settings.copy()
    
    def reset(self) -> None:
        """Reset all settings to defaults."""
        self._settings = self._defaults.copy()
    
    def reset_to_default(self, key: str) -> None:
        """Reset a specific setting to its default value.
        
        Args:
            key: Setting key to reset
        """
        if key in self._defaults:
            self._settings[key] = self._defaults[key]
    
    @property
    def file_path(self) -> Path:
        """Get the settings file path."""
        return self._file_path


# Singleton instance
Settings = SettingsManager()


# Convenience functions for direct access
def get(key: str, default: Any = None) -> Any:
    """Get a setting value."""
    return Settings.get(key, default)


def set(key: str, value: Any) -> None:
    """Set a setting value."""
    Settings.set(key, value)


def save() -> bool:
    """Save all settings."""
    return Settings.save()


def load() -> None:
    """Reload settings from file."""
    Settings._load()
