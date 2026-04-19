"""Location Settings Widget - Launch site configuration with interactive map."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
    QPushButton, QComboBox, QGroupBox, QFormLayout, QMessageBox, QFileDialog,
    QSplitter
)
from PyQt6.QtCore import Qt
from models.app_state import ApplicationState
from src.utils.location_manager import LocationManager
from typing import Tuple, Union, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
import json
import os
import logging
import plotly.graph_objects as go
import tempfile
from pathlib import Path
import webbrowser

# Try to import QWebEngineView; if it fails, use fallback
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

logger = logging.getLogger(__name__)


class LocationSettingsWidget(QWidget):
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
    
    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
        self.locations = {}
        self.location_manager = LocationManager()
        self.html_browser: Optional[Union["QWebEngineView", QLabel]] = None
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
            lambda v: self.state.set('sim_location', v)
        )
        props_layout.addRow("Location Name:", self.name_edit)
        
        # Latitude
        self.latitude_spinbox = QDoubleSpinBox()
        self.latitude_spinbox.setRange(-90, 90)
        self.latitude_spinbox.setDecimals(6)
        self.latitude_spinbox.setSuffix(" °")
        self.latitude_spinbox.valueChanged.connect(
            lambda v: self.state.set('launch_latitude', v)
        )
        props_layout.addRow("Latitude:", self.latitude_spinbox)
        
        # Longitude
        self.longitude_spinbox = QDoubleSpinBox()
        self.longitude_spinbox.setRange(-180, 180)
        self.longitude_spinbox.setDecimals(6)
        self.longitude_spinbox.setSuffix(" °")
        self.longitude_spinbox.valueChanged.connect(
            lambda v: self.state.set('launch_longitude', v)
        )
        props_layout.addRow("Longitude:", self.longitude_spinbox)
        
        # Elevation
        self.elevation_spinbox = QDoubleSpinBox()
        self.elevation_spinbox.setRange(-500, 5000)
        self.elevation_spinbox.setSuffix(" m")
        self.elevation_spinbox.setValue(self.state.get('launch_elevation', 60.0))
        self.elevation_spinbox.valueChanged.connect(
            lambda v: self.state.set('launch_elevation', v)
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
        
        map_label = QLabel("Interactive World Map")
        map_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        map_layout.addWidget(map_label)
        
        # Create map display widget (use QWebEngineView if available, otherwise fallback)
        if HAS_WEBENGINE:
            self.html_browser = QWebEngineView() # type: ignore
        else:
            # Fallback: create a widget with instructions to open map in browser
            self.html_browser = QLabel(
                "WebEngine not available. Map will open in your default web browser.\n\n"
                "Click 'Refresh Map' to generate and open the interactive map."
            )
            self.html_browser.setStyleSheet("color: #666; padding: 20px;")
            self.html_browser.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.map_file = None  # Will store path to temporary HTML file
        
        map_layout.addWidget(self.html_browser)
        
        map_widget.setLayout(map_layout)
        splitter.addWidget(map_widget)
        
        # Set initial sizes (40% form, 60% map)
        splitter.setSizes([400, 600])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def refresh_map(self):
        """Refresh and redraw the interactive world map with all locations.
        
        Generates a Plotly scattergeo visualization showing all saved locations
        as star markers. Displays map in QWebEngineView if available, otherwise
        opens in default browser. Shows empty state message if no locations saved.
        
        Raises:
            Exception: Logs and displays error dialog if map generation fails.
        """
        try:
            # Get all locations
            locations_list = []
            lats = []
            lons = []
            names = []
            elevations = []
            
            if self.locations:
                for name, data in self.locations.items():
                    lat = data.get('latitude', 0)
                    lon = data.get('longitude', 0)
                    elev = data.get('elevation', 0)
                    
                    lats.append(lat)
                    lons.append(lon)
                    names.append(name)
                    elevations.append(elev)
                    
                    locations_list.append({
                        'name': name,
                        'lat': lat,
                        'lon': lon,
                        'elev': elev
                    })
            
            # Create Plotly figure with scattergeo
            fig = go.Figure()
            
            # Add location markers
            if lats:
                fig.add_trace(go.Scattergeo(
                    lon=lons,
                    lat=lats,
                    mode='markers+text',
                    marker=dict(
                        size=12,
                        color='#FF6B6B',
                        line=dict(width=2, color='#C92A2A'),
                        symbol='star'
                    ),
                    text=names,
                    textposition='top center',
                    textfont=dict(size=10, color='#333'),
                    hovertemplate=(
                        '<b>%{text}</b><br>' +
                        'Latitude: %{lat:.6f}°<br>' +
                        'Longitude: %{lon:.6f}°<br>' +
                        '<extra></extra>'
                    ),
                    name='Launch Sites'
                ))
            else:
                # Show empty map message
                fig.add_annotation(
                    text="No locations saved. Click 'Save Location' to add launch sites.",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=14, color='gray')
                )
            
            # Update layout
            fig.update_layout(
                title='World Map - Launch Sites',
                geo=dict(
                    scope='world',
                    showcountries=True,
                    countrywidth=0.5,
                    coastlinewidth=1,
                    projection_type='equirectangular',
                    showland=True,
                    landcolor='#E8E8E8',
                    oceancolor='#D4E6F1',
                    bgcolor='#F8F9FA'
                ),
                height=500,
                margin=dict(l=0, r=0, t=40, b=0),
                hovermode='closest',
                template='plotly_white'
            )
            
            # Convert to HTML and display
            html_str = fig.to_html(include_plotlyjs='cdn', div_id='map')
            
            if HAS_WEBENGINE:
                # Display directly in QWebEngineView
                self.html_browser.setHtml(html_str)  # type: ignore
            else:
                # Save to temporary file and open in default browser
                temp_dir = Path(tempfile.gettempdir())
                map_file = temp_dir / 'rocket_map.html'
                
                with open(map_file, 'w', encoding='utf-8') as f:
                    f.write(html_str)
                
                self.map_file = str(map_file)
                self.html_browser.setText(  # type: ignore
                    f"Map saved to: {map_file}\n\n"
                    f"Opening in your default web browser..."
                )
                
                # Open in default browser
                webbrowser.open(f'file://{map_file}')
            
            logger.info(f"Map refreshed with {len(locations_list)} locations")
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
        """Handle location selection change from combo box.
        
        Args:
            location_name (str): Name of selected location from combo box.
        
        Updates UI fields (name, latitude, longitude, elevation) with values
        from self.locations dict. No-op if location_name not in locations.
        """
        if location_name in self.locations:
            location_data = self.locations[location_name]
            self.name_edit.setText(location_name)
            self.latitude_spinbox.setValue(location_data.get('latitude', 0.0))
            self.longitude_spinbox.setValue(location_data.get('longitude', 0.0))
            self.elevation_spinbox.setValue(location_data.get('elevation', 0.0))
    
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
            self.state.set('sim_location', location_name)
            self.state.set('launch_latitude', float(location_data['latitude']))
            self.state.set('launch_longitude', float(location_data['longitude']))
            self.state.set('launch_elevation', float(location_data['elevation']))
            
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
