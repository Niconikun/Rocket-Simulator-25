"""
Path Configuration

Centralized path management for the Rocket Simulator application.
All file paths should be accessed through this module to ensure consistency
and easy configuration.

Usage:
    from src.config import Paths
    
    # Access paths
    config_path = Paths.ROCKETS_DIR
    locations_file = Paths.LOCATIONS_FILE
    
    # Ensure all directories exist
    Paths.ensure_dirs()
"""

from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


class AppPaths:
    """
    Centralized path configuration for the Rocket Simulator.
    
    All paths are relative to the project root or user data directory.
    Use these constants instead of hardcoding paths in your code.
    """
    
    # ========================================================================
    # Base Directories
    # ========================================================================
    
    # Project root (where main.py is located)
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    
    # Data directory (relative to project root)
    DATA_DIR: Path = BASE_DIR / "data"
    
    # ========================================================================
    # Subdirectories
    # ========================================================================
    
    # Rockets
    ROCKETS_DIR: Path = DATA_DIR / "rockets"
    ROCKETS_CONFIGS_DIR: Path = ROCKETS_DIR / "configs"
    
    # Locations
    LOCATIONS_DIR: Path = DATA_DIR / "locations"
    LOCATIONS_FILE: Path = LOCATIONS_DIR / "launch_sites.json"
    
    # Simulations
    SIMULATIONS_DIR: Path = DATA_DIR / "simulations"
    SIMULATIONS_HISTORY_FILE: Path = SIMULATIONS_DIR / "history.json"
    
    # Wind Scenarios
    SCENARIOS_DIR: Path = DATA_DIR / "scenarios"
    
    # Parachutes
    PARACHUTES_DIR: Path = DATA_DIR / "parachutes"
    PARACHUTES_CONFIGS_DIR: Path = PARACHUTES_DIR / "configs"
    
    # Monte Carlo Results
    MONTE_CARLO_DIR: Path = DATA_DIR / "monte_carlo"
    
    # Logs
    LOGS_DIR: Path = DATA_DIR / "logs"
    
    # Temp
    TEMP_DIR: Path = DATA_DIR / "temp"
    
    # Reports/Exports
    EXPORTS_DIR: Path = DATA_DIR / "exports"
    
    # ========================================================================
    # Path Management Methods
    # ========================================================================
    
    @classmethod
    def ensure_dirs(cls) -> None:
        """
        Ensure all required directories exist.
        
        Creates all necessary directories if they don't exist.
        Safe to call multiple times.
        """
        directories = [
            cls.DATA_DIR,
            cls.ROCKETS_DIR,
            cls.ROCKETS_CONFIGS_DIR,
            cls.LOCATIONS_DIR,
            cls.SIMULATIONS_DIR,
            cls.SCENARIOS_DIR,
            cls.PARACHUTES_DIR,
            cls.PARACHUTES_CONFIGS_DIR,
            cls.MONTE_CARLO_DIR,
            cls.LOGS_DIR,
            cls.TEMP_DIR,
            cls.EXPORTS_DIR,
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured directory exists: {directory}")
            except OSError as e:
                logger.warning(f"Failed to create directory {directory}: {e}")
    
    @classmethod
    def get_rocket_config_path(cls, name: str) -> Path:
        """Get path for a rocket configuration file."""
        return cls.ROCKETS_CONFIGS_DIR / f"{name}.json"
    
    @classmethod
    def get_parachute_config_path(cls, name: str) -> Path:
        """Get path for a parachute configuration file."""
        return cls.PARACHUTES_CONFIGS_DIR / f"{name}.json"
    
    @classmethod
    def get_scenario_path(cls, name: str) -> Path:
        """Get path for a wind scenario file."""
        return cls.SCENARIOS_DIR / f"{name}.json"
    
    @classmethod
    def get_simulation_path(cls, sim_id: str) -> Path:
        """Get path for a simulation data file."""
        return cls.SIMULATIONS_DIR / f"{sim_id}.json"
    
    @classmethod
    def get_export_path(cls, filename: str) -> Path:
        """Get path for an export file."""
        return cls.EXPORTS_DIR / filename
    
    @classmethod
    def get_temp_path(cls, filename: str) -> Path:
        """Get path for a temporary file."""
        return cls.TEMP_DIR / filename
    
    @classmethod
    def get_log_path(cls, filename: str) -> Path:
        """Get path for a log file."""
        return cls.LOGS_DIR / filename


# Create alias for backward compatibility
Paths = AppPaths


# Ensure directories exist on module import
Paths.ensure_dirs()
