"""Location Settings Widget - Launch site configuration with interactive map."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
    QPushButton, QComboBox, QGroupBox, QFormLayout, QMessageBox, QFileDialog,
    QSplitter
)
from PyQt6.QtCore import Qt
from ui.widgets import BaseWidget
from models.app_state import ApplicationState
from src.models.state import StateProvider
from src.config import Constants
from typing import Optional
from src.utils.location_manager import LocationManager
from typing import Tuple
import json
import os
import logging
import math
from pathlib import Path
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar

# Try to import cartopy for embedded map rendering
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    HAS_CARTOPY = True
except ImportError:
    HAS_CARTOPY = False

logger = logging.getLogger(__name__)


class LocationSettingsWidget(BaseWidget):
    """
    Location settings widget for managing launch sites.
    
    Replaces pages/03_location_settings.py
    Allows users to:
    - Select or create launch locations
    - Configure latitude, longitude, elevation
    - Save location presets
    - Load weather data for location
    """
    
    @staticmethod
    def validate_location_data(data: dict, name: Optional[str] = None) -> Tuple[bool, str]:
        """Validate location data structure and values.
        
        Args:
            data (dict): Location data to validate
            name (str, optional): Location name for error messages
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        
        Validates:
            - data is dict
            - contains required keys: latitude, longitude, elevation
            - latitude in [-90, 90]
            - longitude in [-180, 180]
            - elevation is numeric
        """
        if not isinstance(data, dict):
            return False, "Location data must be a dictionary"
        
        required_keys = {'latitude', 'longitude', 'elevation'}
        missing = required_keys - set(data.keys())
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        
        try:
            lat = float(data['latitude'])
            lon = float(data['longitude'])
            elev = float(data['elevation'])
        except (TypeError, ValueError):
            return False, "Latitude, longitude, elevation must be numeric"
        
        if not (-90 <= lat <= 90):
            return False, f"Latitude {lat} out of range [-90, 90]"
        
        if not (-180 <= lon <= 180):
            return False, f"Longitude {lon} out of range [-180, 180]"
        
        if elev < -500 or elev > 10000:
            return False, f"Elevation {elev} unreasonable (outside -500 to 10000 m)"
        
        return True, ""
    
    def __init__(self, state: Optional[StateProvider] = None, parent=None):
        super().__init__(state=state, parent=parent)
        self.locations = {}
        self.location_manager = LocationManager()
        self.init_ui()
        self.load_locations()
        self.refresh_map()
    
    def init_ui(self):
        """Initialize the location settings widget UI with map and form.
        
        Creates a split-pane interface with:
        - Left panel: Location selection, properties form, action buttons
        - Right panel: Interactive world map with location markers
        
        Initializes UI controls with ApplicationState bindings for automatic
        state synchronization when values change.
        """
        main_layout = QVBoxLayout()
        
        # Create a splitter to divide map and form
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ===== LEFT PANEL: FORM =====
        form_widget = QWidget()
        form_layout = QVBoxLayout()
        
        # Location Selection
        selection_group = QGroupBox("Location Selection")
        selection_layout = QHBoxLayout()
        
        selection_layout.addWidget(QLabel("Select Location:"))
        self.location_combo = QComboBox()
        self.location_combo.currentTextChanged.connect(self.on_location_selected)
        selection_layout.addWidget(self.location_combo)
        
        load_button = QPushButton("📁 Load File")
        load_button.clicked.connect(self.load_location_file)
        selection_layout.addWidget(load_button)
        
        selection_group.setLayout(selection_layout)
        form_layout.addWidget(selection_group)
        
        # Location Properties
        props_group = QGroupBox("Location Properties")
        props_layout = QFormLayout()
        
        # Name
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.SIM_LOCATION, v)
        )
        props_layout.addRow("Location Name:", self.name_edit)
        
        # Latitude
        self.latitude_spinbox = QDoubleSpinBox()
        self.latitude_spinbox.setRange(Constants.Location.MIN_LATITUDE, Constants.Location.MAX_LATITUDE)
        self.latitude_spinbox.setDecimals(6)
        self.latitude_spinbox.setSuffix(" °")
        self.latitude_spinbox.valueChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.LAUNCH_LATITUDE, v)
        )
        props_layout.addRow("Latitude:", self.latitude_spinbox)
        
        # Longitude
        self.longitude_spinbox = QDoubleSpinBox()
        self.longitude_spinbox.setRange(Constants.Location.MIN_LONGITUDE, Constants.Location.MAX_LONGITUDE)
        self.longitude_spinbox.setDecimals(6)
        self.longitude_spinbox.setSuffix(" °")
        self.longitude_spinbox.valueChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.LAUNCH_LONGITUDE, v)
        )
        props_layout.addRow("Longitude:", self.longitude_spinbox)
        
        # Elevation
        self.elevation_spinbox = QDoubleSpinBox()
        self.elevation_spinbox.setRange(Constants.Environmental.MIN_ELEVATION, Constants.Environmental.MAX_ELEVATION)
        self.elevation_spinbox.setSuffix(" m")
        self.elevation_spinbox.setValue(self.state.get(Constants.StateKeys.LAUNCH_ELEVATION, Constants.Environmental.DEFAULT_ELEVATION))
        self.elevation_spinbox.valueChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.LAUNCH_ELEVATION, v)
        )
        props_layout.addRow("Elevation:", self.elevation_spinbox)
        
        props_group.setLayout(props_layout)
        form_layout.addWidget(props_group)
        
        # Action Buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("💾 Save Location")
        save_button.clicked.connect(self.save_location)
        button_layout.addWidget(save_button)
        
        delete_button = QPushButton("🗑️ Delete")
        delete_button.clicked.connect(self.delete_location)
        button_layout.addWidget(delete_button)
        
        refresh_button = QPushButton("🔄 Refresh Map")
        refresh_button.clicked.connect(self.refresh_map)
        button_layout.addWidget(refresh_button)
        
        form_layout.addLayout(button_layout)
        form_layout.addStretch()
        
        form_widget.setLayout(form_layout)
        splitter.addWidget(form_widget)
        
        # ===== RIGHT PANEL: MAP =====
        map_widget = QWidget()
        map_layout = QVBoxLayout()
        map_layout.setContentsMargins(0, 0, 0, 0)
        map_layout.setSpacing(0)
        
        # Embedded map using matplotlib + cartopy
        self._map_fig = Figure()
        self._map_fig.set_facecolor('none')
        self._map_canvas = FigureCanvas(self._map_fig)
        self._map_canvas.setSizePolicy(
            self._map_canvas.sizePolicy().horizontalPolicy(),
            self._map_canvas.sizePolicy().verticalPolicy()
        )
        self._map_canvas.setStyleSheet("background: transparent;")
        self._map_toolbar = NavigationToolbar(self._map_canvas, map_widget)
        map_layout.addWidget(self._map_toolbar)
        map_layout.addWidget(self._map_canvas, stretch=1)
        
        map_widget.setLayout(map_layout)
        splitter.addWidget(map_widget)
        
        # Set initial sizes (40% form, 60% map)
        splitter.setSizes([400, 600])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def refresh_map(self, focus_lat: Optional[float] = None,
                    focus_lon: Optional[float] = None,
                    radius_km: float = 50.0):
        """Redraw the world map.  When focus_lat/focus_lon are given the view
        zooms to a radius_km window around that point; otherwise shows the
        full globe."""
        try:
            self._map_fig.clear()
            focused = focus_lat is not None and focus_lon is not None

            if HAS_CARTOPY:
                ax = self._map_fig.add_subplot(
                    1, 1, 1, projection=ccrs.PlateCarree()
                )
                ax.set_facecolor('none')

                if focused:
                    # Higher-resolution features for close-up view
                    scale = '10m'
                    ax.add_feature( # type: ignore
                        cfeature.NaturalEarthFeature(
                            'physical', 'land', scale,
                            facecolor='#E8E8E8', edgecolor='none'
                        )
                    )
                    ax.add_feature( # type: ignore
                        cfeature.NaturalEarthFeature(
                            'physical', 'ocean', scale,
                            facecolor='#D4E6F1', edgecolor='none'
                        )
                    )
                    ax.add_feature( # type: ignore
                        cfeature.NaturalEarthFeature(
                            'cultural', 'admin_0_countries', scale,
                            facecolor='none', edgecolor='#999999',
                            linewidth=0.5
                        )
                    )
                    ax.add_feature( # type: ignore
                        cfeature.NaturalEarthFeature(
                            'physical', 'coastline', scale,
                            facecolor='none', edgecolor='#555555',
                            linewidth=0.7
                        )
                    )
                    ax.add_feature( # type: ignore
                        cfeature.NaturalEarthFeature(
                            'physical', 'rivers_lake_centerlines', '10m',
                            facecolor='none', edgecolor='#8ec6e6',
                            linewidth=0.5
                        )
                    )
                    # Compute extent in degrees
                    delta_lat = radius_km / 111.32
                    delta_lon = radius_km / (
                        111.32 * math.cos(math.radians(focus_lat)) # type: ignore
                    )
                    ax.set_extent( # type: ignore
                        [focus_lon - delta_lon, focus_lon + delta_lon, # type: ignore
                         focus_lat - delta_lat, focus_lat + delta_lat], # type: ignore
                        crs=ccrs.PlateCarree()
                    )
                    ax.gridlines( # type: ignore
                        draw_labels=True, linewidth=0.4,
                        color='gray', alpha=0.5, linestyle='--'
                    )
                else:
                    ax.add_feature(cfeature.LAND, facecolor='#E8E8E8') # type: ignore
                    ax.add_feature(cfeature.OCEAN, facecolor='#D4E6F1') # type: ignore
                    ax.add_feature( # type: ignore
                        cfeature.BORDERS, linewidth=0.4, edgecolor='#999999'
                    )
                    ax.add_feature(cfeature.COASTLINE, linewidth=0.6) # type: ignore
                    ax.set_global() # type: ignore

                data_transform = ccrs.PlateCarree()
            else:
                ax = self._map_fig.add_subplot(1, 1, 1)
                if focused:
                    delta = radius_km / 111.32
                    ax.set_xlim(focus_lon - delta, focus_lon + delta) # type: ignore
                    ax.set_ylim(focus_lat - delta, focus_lat + delta) # type: ignore
                else:
                    ax.set_xlim(-180, 180)
                    ax.set_ylim(-90, 90)
                ax.set_xlabel('Longitude')
                ax.set_ylabel('Latitude')
                ax.set_facecolor('#D4E6F1')
                ax.grid(True, alpha=0.3)
                data_transform = None

            if self.locations:
                for name, data in self.locations.items():
                    lat = data.get('latitude', 0)
                    lon = data.get('longitude', 0)
                    is_focused = (
                        focused
                        and abs(lat - focus_lat) < 1e-6
                        and abs(lon - focus_lon) < 1e-6
                    )
                    plot_kwargs = dict(
                        marker='*',
                        color='#FF2222' if is_focused else '#FF6B6B',
                        markersize=20 if is_focused else 12,
                        markeredgecolor='#8B0000' if is_focused else '#C92A2A',
                        markeredgewidth=2 if is_focused else 1.5,
                        linestyle='', zorder=6 if is_focused else 5
                    )
                    text_kwargs = dict(
                        fontsize=9 if is_focused else 8,
                        fontweight='bold' if is_focused else 'normal',
                        ha='center', color='#111111' if is_focused else '#333333',
                        zorder=7 if is_focused else 6
                    )
                    text_offset = delta_lat * 0.15 if (focused and is_focused) else 2
                    if data_transform:
                        ax.plot(lon, lat, transform=data_transform, **plot_kwargs) # type: ignore
                        ax.text(
                            lon, lat + text_offset, name,
                            transform=data_transform, **text_kwargs # type: ignore
                        )
                    else:
                        ax.plot(lon, lat, **plot_kwargs) # type: ignore
                        ax.text(lon, lat + text_offset, name, **text_kwargs) # type: ignore
            else:
                ax.text( # type: ignore
                    0.5, 0.5,
                    'Sin ubicaciones guardadas.\nHaz clic en "Save Location" para agregar.',
                    ha='center', va='center', fontsize=11, color='gray',
                    transform=ax.transAxes
                )

            title = (
                f'Sitio: {self.location_combo.currentText()} '
                f'(±{radius_km:.0f} km)'
                if focused
                else 'Mapa Mundial - Sitios de Lanzamiento'
            )
            ax.set_title(title, fontsize=11, fontweight='bold')
            self._map_fig.tight_layout()
            self._map_canvas.draw()

            logger.info(f"Map refreshed — focused={focused}, locations={len(self.locations)}")
        except Exception as e:
            logger.error(f"Error refreshing map: {e}")
            QMessageBox.critical(self, "Map Error", f"Failed to refresh map: {str(e)}")
    
    def load_locations(self):
        """Load all available locations from JSON file.
        
        Reads data/locations/launch_sites.json and populates the location combo box.
        Handles file not found gracefully by initializing empty locations dict.
        
        Logs errors if file parsing fails but continues operation.
        """
        try:
            self.location_combo.clear()
            self.locations.clear()
            
            if os.path.exists('data/locations/launch_sites.json'):
                with open('data/locations/launch_sites.json', 'r', encoding='utf-8') as f:
                    locations_data = json.load(f)
                    if isinstance(locations_data, dict):
                        self.locations = locations_data
                        for name in sorted(self.locations.keys()):
                            self.location_combo.addItem(name)
            logger.info(f"Loaded {len(self.locations)} locations")
        except Exception as e:
            logger.error(f"Error loading locations: {e}")
    
    def on_location_selected(self, location_name: str):
        """Handle location selection change from combo box."""
        if location_name in self.locations:
            location_data = self.locations[location_name]
            self.name_edit.setText(location_name)
            lat = location_data.get('latitude', 0.0)
            lon = location_data.get('longitude', 0.0)
            self.latitude_spinbox.setValue(lat)
            self.longitude_spinbox.setValue(lon)
            self.elevation_spinbox.setValue(location_data.get('elevation', 0.0))
            self.refresh_map(focus_lat=lat, focus_lon=lon, radius_km=50.0)
    
    def save_location(self):
        """Save location to file with validation.
        
        Validates location name and coordinates before saving to data/locations/launch_sites.json.
        Updates ApplicationState and refreshes location combo box and map display.
        
        Validation:
            - Name: non-empty, alphanumeric + space/dash/underscore
            - Latitude: -90 to 90 degrees
            - Longitude: -180 to 180 degrees
        
        Raises:
            OSError: File system permission or I/O errors (displays critical dialog)
            ValueError: Invalid location file structure (displays critical dialog)
            json.JSONDecodeError: Corrupted locations file (displays critical dialog)
        """
        location_name = self.name_edit.text().strip()
        if not location_name:
            QMessageBox.warning(self, "Warning", "Please enter a location name")
            return
        
        # Validate location name (no special characters that could break JSON keys)
        if not all(c.isalnum() or c in ' -_' for c in location_name):
            QMessageBox.warning(
                self, "Invalid Name",
                "Location name can only contain letters, numbers, spaces, hyphens, and underscores"
            )
            return
        
        # Validate location data
        latitude = self.latitude_spinbox.value()
        longitude = self.longitude_spinbox.value()
        elevation = self.elevation_spinbox.value()
        
        if not (-90 <= latitude <= 90):
            QMessageBox.warning(self, "Warning", "Latitude must be between -90 and 90")
            return
        if not (-180 <= longitude <= 180):
            QMessageBox.warning(self, "Warning", "Longitude must be between -180 and 180")
            return
        
        location_data = {
            'latitude': latitude,
            'longitude': longitude,
            'elevation': elevation
        }
        
        try:
            # Create directory if it doesn't exist
            os.makedirs('data/locations', exist_ok=True)
            
            # Load existing locations or create new dict
            locations_file = 'data/locations/launch_sites.json'
            if os.path.exists(locations_file):
                try:
                    with open(locations_file, 'r', encoding='utf-8') as f:
                        all_locations = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Corrupted locations file, starting fresh")
                    all_locations = {}
            else:
                all_locations = {}
            
            # Validate loaded data is a dict
            if not isinstance(all_locations, dict):
                raise ValueError("Invalid locations file structure")
            
            # Update with new location
            all_locations[location_name] = location_data
            
            # Write back to file
            with open(locations_file, 'w', encoding='utf-8') as f:
                json.dump(all_locations, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(
                self, "Success",
                f"Location '{location_name}' saved successfully"
            )
            logger.info(f"Location saved: {location_name} at ({latitude}, {longitude})")
            
            # Reload locations and refresh map
            self.load_locations()
            self.refresh_map()
            
        except OSError as e:
            error_msg = "Unable to save: "
            if e.errno == 13:  # Permission denied
                error_msg += "Permission denied. Check file permissions."
            else:
                error_msg += f"File system error: {str(e)}"
            QMessageBox.critical(self, "Save Error", error_msg)
            logger.error(f"OSError saving location: {error_msg}")
        except (json.JSONDecodeError, ValueError) as e:
            QMessageBox.critical(
                self, "Data Error",
                f"Failed to process location data: {str(e)}"
            )
            logger.error(f"Data error saving location: {str(e)}")
        except Exception as e:
            QMessageBox.critical(
                self, "Unexpected Error",
                f"Failed to save location: {str(e)}"
            )
            logger.error(f"Unexpected error saving location: {str(e)}")
    
    def delete_location(self):
        """Delete selected location with confirmation and validation.
        
        Prompts user for confirmation, validates file and location existence,
        then removes from data/locations/launch_sites.json.
        
        Validates:
            - Location selected (not empty)
            - File exists
            - File is valid JSON
            - Location exists in file
        
        Updates ApplicationState and UI (clears and reloads locations, refreshes map).
        
        Raises:
            FileNotFoundError: Locations file missing (displays warning)
            json.JSONDecodeError: File corrupted (displays critical)
            ValueError: Invalid file structure (displays critical)
            IOError: Unable to save after deletion (displays critical)
        """
        current = self.location_combo.currentText()
        if not current:
            QMessageBox.warning(self, "Warning", "No location selected")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete '{current}'?\n\n"
            f"This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            logger.info(f"Deletion of '{current}' cancelled by user")
            return
        
        try:
            locations_file = 'data/locations/launch_sites.json'
            
            # Check if file exists
            if not os.path.exists(locations_file):
                QMessageBox.warning(
                    self, "Warning",
                    "Locations file not found"
                )
                logger.warning(f"Locations file not found: {locations_file}")
                return
            
            # Load locations with error handling
            try:
                with open(locations_file, 'r', encoding='utf-8') as f:
                    all_locations = json.load(f)
            except json.JSONDecodeError as e:
                QMessageBox.critical(
                    self, "Data Error",
                    "Locations file is corrupted and cannot be read"
                )
                logger.error(f"Corrupted locations file: {str(e)}")
                return
            
            # Validate loaded data
            if not isinstance(all_locations, dict):
                QMessageBox.critical(
                    self, "Data Error",
                    "Invalid locations file structure"
                )
                logger.error("Locations file has invalid structure")
                return
            
            # Check if location exists
            if current not in all_locations:
                QMessageBox.warning(
                    self, "Not Found",
                    f"Location '{current}' not found in file"
                )
                logger.warning(f"Location not found for deletion: {current}")
                # Refresh UI to match actual file state
                self.load_locations()
                return
            
            # Delete location
            del all_locations[current]
            
            # Write updated data
            try:
                with open(locations_file, 'w', encoding='utf-8') as f:
                    json.dump(all_locations, f, indent=4, ensure_ascii=False)
            except (IOError, OSError) as e:
                QMessageBox.critical(
                    self, "Save Error",
                    f"Unable to save changes: {str(e)}"
                )
                logger.error(f"Failed to save after deletion: {str(e)}")
                return
            
            # Success - update UI
            QMessageBox.information(
                self, "Success",
                f"Location '{current}' deleted successfully"
            )
            logger.info(f"Location deleted: {current}")
            
            # Reload locations and refresh display
            self.locations.clear()
            self.location_combo.clear()
            self.load_locations()
            self.refresh_map()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Unexpected Error",
                f"Failed to delete location: {str(e)}"
            )
            logger.error(f"Unexpected error deleting location: {str(e)}")
    
    def load_location_file(self):
        """Load location from file and populate UI fields.
        
        Opens file dialog for user to select JSON file containing location data.
        Supports two file formats:
        1. Single location: {latitude: X, longitude: Y, elevation: Z}
        2. Multiple locations: {location_name: {latitude: X, ...}, ...}
        
        If multiple locations, loads first one. Single location file name becomes
        the location name in UI.
        
        Updates UI fields with signal blocking, syncs ApplicationState, refreshes map.
        
        Raises:
            json.JSONDecodeError: Invalid JSON file (displays error dialog)
            ValueError: Missing required fields or invalid data structure (displays error)
            FileNotFoundError: File not found or inaccessible (displays error)
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load Location", "",
            "JSON Files (*.json)"
        )
        if not filepath:
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate that data is a dict
            if not isinstance(data, dict):
                raise ValueError("Invalid location file: expected JSON object")
            
            # Handle two cases:
            # 1. Single location object with lat/lon/elevation keys
            # 2. Multiple locations object with location_name keys
            if 'latitude' in data and 'longitude' in data:
                # Case 1: Single location object
                location_name = Path(filepath).stem  # Use filename as location name
                location_data = data
            elif len(data) > 0:
                # Case 2: Multiple locations - use the first one
                location_name = list(data.keys())[0]
                location_data = data[location_name]
            else:
                raise ValueError("No location data found in file")
            
            # Validate location data using validator
            is_valid, error_msg = self.validate_location_data(location_data, location_name)
            if not is_valid:
                raise ValueError(error_msg)
            
            # Apply data to UI fields (block signals to avoid unnecessary updates)
            self.name_edit.blockSignals(True)
            self.latitude_spinbox.blockSignals(True)
            self.longitude_spinbox.blockSignals(True)
            self.elevation_spinbox.blockSignals(True)
            
            self.name_edit.setText(location_name)
            self.latitude_spinbox.setValue(float(location_data['latitude']))
            self.longitude_spinbox.setValue(float(location_data['longitude']))
            self.elevation_spinbox.setValue(float(location_data['elevation']))
            
            # Unblock signals
            self.name_edit.blockSignals(False)
            self.latitude_spinbox.blockSignals(False)
            self.longitude_spinbox.blockSignals(False)
            self.elevation_spinbox.blockSignals(False)
            
            # Update application state
            self.state.set(Constants.StateKeys.SIM_LOCATION, location_name)
            self.state.set(Constants.StateKeys.LAUNCH_LATITUDE, float(location_data['latitude']))
            self.state.set(Constants.StateKeys.LAUNCH_LONGITUDE, float(location_data['longitude']))
            self.state.set(Constants.StateKeys.LAUNCH_ELEVATION, float(location_data['elevation']))
            
            # Refresh map with new location
            self.refresh_map()
            
            QMessageBox.information(
                self, "Success",
                f"Location '{location_name}' loaded successfully"
            )
            logger.info(f"Location loaded from file: {location_name}")
            
        except (json.JSONDecodeError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Invalid location file: {str(e)}")
            logger.error(f"Failed to load location file: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load: {str(e)}")
            logger.error(f"Unexpected error loading location file: {str(e)}")
