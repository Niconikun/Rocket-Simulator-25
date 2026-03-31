"""Location Settings Widget - Launch site configuration with interactive map."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
    QPushButton, QComboBox, QGroupBox, QFormLayout, QMessageBox, QTableWidget,
    QTableWidgetItem, QFileDialog, QSplitter
)
from PyQt6.QtCore import Qt
from models.app_state import ApplicationState
from src.utils.location_manager import LocationManager
import json
import os
import logging
import plotly.graph_objects as go
import plotly.express as px
import tempfile
from pathlib import Path
import webbrowser

# Try to import QWebEngineView; if it fails, use fallback
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False
    # Fallback: use a simple label or file dialog
    QWebEngineView = None

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
    
    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
        self.locations = {}
        self.location_manager = LocationManager()
        self.html_browser = None
        self.init_ui()
        self.load_locations()
        self.refresh_map()
    
    def init_ui(self):
        """Initialize the location settings widget UI with map and form."""
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
            self.html_browser = QWebEngineView()
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
        """Refresh and redraw the interactive world map with all locations."""
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
                self.html_browser.setHtml(html_str)
            else:
                # Save to temporary file and open in default browser
                import webbrowser
                temp_dir = Path(tempfile.gettempdir())
                map_file = temp_dir / 'rocket_map.html'
                
                with open(map_file, 'w', encoding='utf-8') as f:
                    f.write(html_str)
                
                self.map_file = str(map_file)
                self.html_browser.setText(
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
        """Load all available locations from JSON file."""
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
        """Handle location selection change."""
        if location_name in self.locations:
            location_data = self.locations[location_name]
            self.name_edit.setText(location_name)
            self.latitude_spinbox.setValue(location_data.get('latitude', 0.0))
            self.longitude_spinbox.setValue(location_data.get('longitude', 0.0))
            self.elevation_spinbox.setValue(location_data.get('elevation', 0.0))
    
    def save_location(self):
        """Save location to file."""
        location_name = self.name_edit.text()
        if not location_name:
            QMessageBox.warning(self, "Warning", "Please enter a location name")
            return
        
        location_data = {
            'latitude': self.latitude_spinbox.value(),
            'longitude': self.longitude_spinbox.value(),
            'elevation': self.elevation_spinbox.value()
        }
        
        try:
            os.makedirs('data/locations', exist_ok=True)
            
            if os.path.exists('data/locations/launch_sites.json'):
                with open('data/locations/launch_sites.json', 'r', encoding='utf-8') as f:
                    all_locations = json.load(f)
            else:
                all_locations = {}
            
            all_locations[location_name] = location_data
            
            with open('data/locations/launch_sites.json', 'w', encoding='utf-8') as f:
                json.dump(all_locations, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(self, "Success", f"Location '{location_name}' saved")
            logger.info(f"Location saved: {location_name}")
            
            # Reload locations and refresh map
            self.load_locations()
            self.refresh_map()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
    
    def delete_location(self):
        """Delete selected location."""
        current = self.location_combo.currentText()
        if not current:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete location '{current}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists('data/locations/launch_sites.json'):
                    with open('data/locations/launch_sites.json', 'r', encoding='utf-8') as f:
                        all_locations = json.load(f)
                    
                    if current in all_locations:
                        del all_locations[current]
                    
                    with open('data/locations/launch_sites.json', 'w', encoding='utf-8') as f:
                        json.dump(all_locations, f, indent=4, ensure_ascii=False)
                    
                    QMessageBox.information(self, "Success", f"Deleted '{current}'")
                    self.locations.clear()
                    self.location_combo.clear()
                    self.load_locations()
                    self.refresh_map()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")
    
    def load_location_file(self):
        """Load location from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load Location", "",
            "JSON Files (*.json)"
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    location_data = json.load(f)
                    QMessageBox.information(self, "Success", "Location loaded")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {str(e)}")
