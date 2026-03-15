"""
Location Data Management

Utilities for managing location data with coordinate validation
and persistence.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LocationManager:
    """
    Manages location data for launch sites.
    
    Features:
    - Load/save locations
    - Validate coordinates
    - Get location by name
    - List all locations
    """
    
    def __init__(self, locations_file: str = "data/locations/launch_sites.json"):
        """Initialize the location manager."""
        self.locations_file = Path(locations_file)
        self.locations: Dict[str, Dict] = {}
        self._ensure_directory()
        self._load_locations()
    
    def _ensure_directory(self):
        """Create necessary directories if they don't exist."""
        self.locations_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_locations(self):
        """Load locations from file or create new."""
        if self.locations_file.exists():
            try:
                with open(self.locations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.locations = data if isinstance(data, dict) else {}
                logger.info(f"Loaded {len(self.locations)} locations")
            except Exception as e:
                logger.error(f"Error loading locations: {e}")
                self.locations = {}
        else:
            self.locations = {}
    
    def _save_locations(self):
        """Save locations to file."""
        try:
            self._ensure_directory()
            with open(self.locations_file, 'w', encoding='utf-8') as f:
                json.dump(self.locations, f, indent=2, ensure_ascii=False)
            logger.debug("Locations saved successfully")
        except Exception as e:
            logger.error(f"Error saving locations: {e}")
    
    def add_location(self, name: str, latitude: float, longitude: float, 
                     elevation: float = 0.0, **kwargs) -> bool:
        """
        Add or update a location.
        
        Args:
            name: Location name
            latitude: Latitude (-90 to 90)
            longitude: Longitude (-180 to 180)
            elevation: Elevation in meters
            **kwargs: Additional metadata
        
        Returns:
            True if successful
        """
        if not self._validate_coordinates(latitude, longitude):
            logger.warning(f"Invalid coordinates: {latitude}, {longitude}")
            return False
        
        self.locations[name] = {
            'latitude': latitude,
            'longitude': longitude,
            'elevation': elevation,
            **kwargs
        }
        self._save_locations()
        logger.info(f"Added/updated location: {name}")
        return True
    
    def get_location(self, name: str) -> Optional[Dict]:
        """Get location by name."""
        return self.locations.get(name)
    
    def list_locations(self) -> List[Tuple[str, float, float]]:
        """
        Get list of all locations as (name, lat, lon) tuples.
        
        Returns:
            List of location tuples
        """
        return [
            (name, data.get('latitude', 0), data.get('longitude', 0))
            for name, data in self.locations.items()
        ]
    
    def delete_location(self, name: str) -> bool:
        """Delete a location."""
        if name in self.locations:
            del self.locations[name]
            self._save_locations()
            logger.info(f"Deleted location: {name}")
            return True
        return False
    
    def get_all_locations(self) -> Dict:
        """Get all locations dictionary."""
        return self.locations.copy()
    
    @staticmethod
    def _validate_coordinates(latitude: float, longitude: float) -> bool:
        """Validate latitude and longitude ranges."""
        return -90 <= latitude <= 90 and -180 <= longitude <= 180
