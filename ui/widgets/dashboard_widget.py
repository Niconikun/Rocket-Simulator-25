"""Dashboard Widget - Simulation results visualization."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
    QGridLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QMessageBox, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from models.app_state import ApplicationState
from src.utils.simulation_manager import SimulationManager
import logging
from datetime import datetime
import csv
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors

# Import matplotlib for plotting
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

# Try to import folium for maps
try:
    import folium
    from folium.plugins import AntPath
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

# Try to import QWebEngineView for map display
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class DashboardWidget(QWidget):
    """
    Dashboard for displaying simulation results and metrics.
    
    Replaces pages/05_dashboard.py
    Displays:
    - Key flight metrics (max altitude, max velocity, range, etc.)
    - Recent and historical simulations
    - Flight trajectory plots
    - Performance charts
    - Comparison analysis
    """
    
    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
        self.sim_manager = SimulationManager()
        self.current_sim_id = None
        self.init_ui()
        self.load_simulation_history()
    
    def init_ui(self):
        """Initialize the dashboard UI."""
        main_layout = QVBoxLayout()
        
        # ===== SIMULATION SELECTION =====
        selection_group = QGroupBox("Simulations")
        selection_layout = QHBoxLayout()
        
        selection_layout.addWidget(QLabel("Load Simulation:"))
        
        self.sim_combo = QComboBox()
        self.sim_combo.currentIndexChanged.connect(self.on_simulation_selected)
        selection_layout.addWidget(self.sim_combo)
        
        load_button = QPushButton("Load")
        load_button.clicked.connect(self.load_selected_simulation)
        selection_layout.addWidget(load_button)
        
        delete_button = QPushButton("🗑️ Delete")
        delete_button.clicked.connect(self.delete_selected_simulation)
        selection_layout.addWidget(delete_button)
        
        selection_group.setLayout(selection_layout)
        main_layout.addWidget(selection_group)
        
        # ===== KEY METRICS =====
        metrics_group = QGroupBox("Flight Metrics")
        metrics_layout = QGridLayout()
        
        # Metric display labels
        self.metric_labels = {}
        metrics = [
            ("max_altitude", "Max Altitude"),
            ("max_velocity", "Max Velocity"),
            ("max_range", "Max Range"),
            ("max_mach", "Max Mach"),
            ("flight_duration", "Flight Time"),
            ("max_accel_g", "Max Acceleration"),
        ]
        
        for i, (key, label) in enumerate(metrics):
            row = i // 3
            col = i % 3
            
            metric_subgroup = QGroupBox(label)
            metric_layout = QVBoxLayout()
            metric_value = QLabel("No data")
            metric_value.setStyleSheet("font-size: 18px; font-weight: bold;")
            self.metric_labels[key] = metric_value
            metric_layout.addWidget(metric_value)
            metric_layout.addStretch()
            metric_subgroup.setLayout(metric_layout)
            
            metrics_layout.addWidget(metric_subgroup, row, col)
        
        metrics_group.setLayout(metrics_layout)
        main_layout.addWidget(metrics_group)
        
        # ===== SIMULATION INFO =====
        info_group = QGroupBox("Simulation Information")
        info_layout = QGridLayout()
        
        self.info_labels = {}
        info_fields = [
            ("rocket", "Rocket"),
            ("location", "Location"),
            ("temperature", "Temperature"),
            ("pressure", "Pressure"),
        ]
        
        for i, (key, label) in enumerate(info_fields):
            row = i // 2
            col = (i % 2) * 2
            
            info_layout.addWidget(QLabel(f"{label}:"), row, col)
            value_label = QLabel("N/A")
            self.info_labels[key] = value_label
            info_layout.addWidget(value_label, row, col + 1)
        
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        # ===== FLIGHT PROFILES CHARTS =====
        charts_group = QGroupBox("Flight Profiles")
        charts_layout = QVBoxLayout()
        
        # Scrollable area for charts
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(900)  # Set minimum height for charts
        scroll_area.setMinimumWidth(1200)  # Set minimum width to prevent squeezing
        
        self.charts_container = QWidget()
        self.charts_grid_layout = QGridLayout()
        self.charts_grid_layout.setSpacing(15)  # Add spacing between charts
        self.charts_grid_layout.setContentsMargins(10, 10, 10, 10)  # Add margins around charts
        self.charts_container.setLayout(self.charts_grid_layout)
        
        scroll_area.setWidget(self.charts_container)
        charts_layout.addWidget(scroll_area)
        
        charts_group.setLayout(charts_layout)
        # Make charts group expandable
        main_layout.addWidget(charts_group, 1)  # Stretch factor of 1 to expand
        
        # ===== TRAJECTORY MAPS =====
        maps_group = QGroupBox("Trajectory Overview")
        maps_layout = QHBoxLayout()
        
        # 2D Trajectory Map
        map_2d_subgroup = QGroupBox("2D Trajectory Map")
        map_2d_layout = QVBoxLayout()
        
        if HAS_WEBENGINE:
            self.map_2d_view = QWebEngineView()
            self.map_2d_view.setMinimumHeight(400)
            map_2d_layout.addWidget(self.map_2d_view)
        else:
            self.map_2d_view = None
            self.map_2d_container = QWidget()
            self.map_2d_container.setLayout(QVBoxLayout())
            map_2d_layout.addWidget(self.map_2d_container)
            map_2d_layout.addWidget(QLabel("QWebEngineView not available\nUsing matplotlib fallback"))
        
        map_2d_subgroup.setLayout(map_2d_layout)
        maps_layout.addWidget(map_2d_subgroup)
        
        # 3D Flight Path
        map_3d_subgroup = QGroupBox("3D Flight Path")
        map_3d_layout = QVBoxLayout()
        
        self.map_3d_canvas = None
        self.map_3d_container = QWidget()
        self.map_3d_container.setLayout(QVBoxLayout())
        map_3d_layout.addWidget(self.map_3d_container)
        
        map_3d_subgroup.setLayout(map_3d_layout)
        maps_layout.addWidget(map_3d_subgroup)
        
        maps_group.setLayout(maps_layout)
        main_layout.addWidget(maps_group)
        
        # ===== EXPORT BUTTONS =====
        export_layout = QHBoxLayout()
        
        csv_button = QPushButton("📥 Export to CSV")
        csv_button.clicked.connect(self.export_csv)
        export_layout.addWidget(csv_button)
        
        pdf_button = QPushButton("📄 Generate PDF Report")
        pdf_button.clicked.connect(self.generate_pdf)
        export_layout.addWidget(pdf_button)
        
        refresh_button = QPushButton("🔄 Refresh")
        refresh_button.clicked.connect(self.refresh_dashboard)
        export_layout.addWidget(refresh_button)
        
        main_layout.addLayout(export_layout)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
    
    def load_simulation_history(self):
        """Load list of simulations from manager."""
        self.sim_combo.blockSignals(True)
        self.sim_combo.clear()
        
        simulations = self.sim_manager.list_simulations()
        
        if not simulations:
            self.sim_combo.addItem("No simulations", None)
            self.sim_combo.blockSignals(False)
            return
        
        # Add "Recent" option with most recent simulation
        recent = self.sim_manager.get_recent_simulation()
        if recent:
            recent_id = recent.get('id', '')
            recent_text = f"Recent - {recent.get('rocket', 'Unknown')} @ {recent.get('location', 'Unknown')}"
            self.sim_combo.addItem(recent_text, recent_id)
        
        # Add separator
        self.sim_combo.insertSeparator(self.sim_combo.count())
        
        # Add all simulations
        for sim in simulations:
            sim_id = sim.get('id', '')
            timestamp = sim.get('timestamp', 'Unknown')
            if isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    timestamp = timestamp[:16]
            
            rocket = sim.get('rocket', 'Unknown')
            location = sim.get('location', 'Unknown')
            
            display_text = f"{timestamp} - {rocket} @ {location}"
            self.sim_combo.addItem(display_text, sim_id)
        
        self.sim_combo.blockSignals(False)
    
    def on_simulation_selected(self, index: int):
        """Handle simulation selection."""
        if index >= 0:
            sim_id = self.sim_combo.currentData()
            if sim_id:
                self.load_selected_simulation()
    
    def load_selected_simulation(self):
        """Load the selected simulation data."""
        sim_id = self.sim_combo.currentData()
        
        if not sim_id:
            QMessageBox.warning(self, "Warning", "No simulation selected")
            return
        
        sim_data = self.sim_manager.load_simulation(sim_id)
        if not sim_data:
            QMessageBox.critical(self, "Error", f"Could not load simulation {sim_id}")
            return
        
        metadata = self.sim_manager.metadata.get(sim_id, {})
        
        # Update current simulation ID
        self.current_sim_id = sim_id
        
        # Update metrics
        self.metric_labels['max_altitude'].setText(
            f"{metadata.get('max_altitude', 0):.3f} km"
        )
        self.metric_labels['max_velocity'].setText(
            f"{metadata.get('max_velocity', 0):.2f} m/s"
        )
        self.metric_labels['max_range'].setText(
            f"{metadata.get('max_range', 0):.2f} km"
        )
        self.metric_labels['flight_duration'].setText(
            f"{metadata.get('flight_duration', 0):.2f} s"
        )
        
        # Update info
        self.info_labels['rocket'].setText(metadata.get('rocket', 'N/A'))
        self.info_labels['location'].setText(metadata.get('location', 'N/A'))
        self.info_labels['temperature'].setText(
            f"{metadata.get('temperature', 0):.1f} °C"
        )
        self.info_labels['pressure'].setText(
            f"{metadata.get('pressure', 0):.0f} Pa"
        )
        
        # Generate charts and maps from simulation data
        self.generate_performance_charts(sim_data)
        self.generate_trajectory_maps(sim_data, metadata)
        
        logger.info(f"Loaded simulation: {sim_id}")
        QMessageBox.information(self, "Success", f"Loaded simulation {sim_id}")
    
    def delete_selected_simulation(self):
        """Delete the selected simulation."""
        sim_id = self.sim_combo.currentData()
        
        if not sim_id:
            QMessageBox.warning(self, "Warning", "No simulation selected")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete simulation {sim_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.sim_manager.delete_simulation(sim_id):
                self.load_simulation_history()
                QMessageBox.information(self, "Success", "Simulation deleted")
                logger.info(f"Deleted simulation: {sim_id}")
            else:
                QMessageBox.critical(self, "Error", "Could not delete simulation")
    
    def generate_performance_charts(self, sim_data):
        """Generate 9 performance charts from simulation data."""
        # Clear previous charts
        while self.charts_grid_layout.count():
            item = self.charts_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not sim_data or isinstance(sim_data, dict) and 'trajectory' not in sim_data:
            logger.warning("No trajectory data available for charts")
            return
        
        try:
            trajectory = sim_data.get('trajectory', [])
            history = sim_data.get('history', {})
            
            if not trajectory:
                logger.warning("Empty trajectory data")
                return
            
            # Convert trajectory to numpy arrays for easier manipulation
            times = np.array([p.get('time', 0) for p in trajectory])
            altitudes = np.array([p.get('altitude', 0) for p in trajectory])
            velocities = np.array([p.get('velocity', 0) for p in trajectory])
            ranges = np.array([p.get('range', 0) for p in trajectory])
            machs = np.array([p.get('mach', 0) for p in trajectory])
            
            # Chart 1: Altitude & Velocity vs Time
            fig1 = self._create_chart(
                "Altitude [m] & Velocity [m/s] vs Time [s]",
                times, [altitudes, velocities], 
                ['Altitude', 'Velocity'], ['blue', 'red']
            )
            self._add_chart_to_grid(fig1, 0, 0)
            
            # Chart 2: Flight Path - Altitude vs Range
            fig2 = self._create_simple_chart(
                "Flight Path - Altitude [m] vs Range [m]",
                ranges, altitudes, 'Range', 'Altitude'
            )
            self._add_chart_to_grid(fig2, 0, 1)
            
            # Chart 3: Mach & AoA vs Time  (placeholder - use mach data)
            fig3 = self._create_simple_chart(
                "Mach Number vs Time [s]",
                times, machs, 'Time', 'Mach'
            )
            self._add_chart_to_grid(fig3, 0, 2)
            
            # Charts 4-9: Additional performance data if available from history
            if history:
                # Try to extract data from history
                if isinstance(history, dict):
                    # Chart 4: Forces Analysis
                    try:
                        times = np.array(history.get('hist_time', []))
                        thrust = np.array(history.get('hist_thrust', []))
                        drag = np.array(history.get('hist_drag', []))
                        lift = np.array(history.get('hist_lift', []))
                        
                        if len(times) > 0:
                            fig4 = self._create_multiline_chart(
                                "Forces Analysis [N] vs Time [s]",
                                times, [thrust, drag, lift],
                                ['Thrust', 'Drag', 'Lift'],
                                ['green', 'red', 'blue']
                            )
                        else:
                            fig4 = self._create_placeholder_chart("Forces Analysis [N] vs Time [s]")
                    except Exception as e:
                        logger.warning(f"Could not create forces chart: {e}")
                        fig4 = self._create_placeholder_chart("Forces Analysis [N] vs Time [s]")
                    self._add_chart_to_grid(fig4, 1, 0)
                    
                    # Chart 5: Mass & Altitude
                    try:
                        times = np.array(history.get('hist_time', []))
                        mass = np.array(history.get('hist_mass', []))
                        altitude = np.array(history.get('hist_alt', []))
                        
                        if len(times) > 0:
                            fig5 = self._create_chart(
                                "Mass [kg] & Altitude [m] vs Time [s]",
                                times, [mass, altitude],
                                ['Mass', 'Altitude'], ['purple', 'cyan']
                            )
                        else:
                            fig5 = self._create_placeholder_chart("Mass [kg] & Altitude [m] vs Time [s]")
                    except Exception as e:
                        logger.warning(f"Could not create mass chart: {e}")
                        fig5 = self._create_placeholder_chart("Mass [kg] & Altitude [m] vs Time [s]")
                    self._add_chart_to_grid(fig5, 1, 1)
                    
                    # Chart 6: Attitude (Euler Angles)
                    try:
                        times = np.array(history.get('hist_time', []))
                        yaw = np.array(history.get('hist_yaw', []))
                        pitch = np.array(history.get('hist_pitch', []))
                        roll = np.array(history.get('hist_roll', []))
                        
                        if len(times) > 0:
                            fig6 = self._create_multiline_chart(
                                "Attitude - Euler Angles [°] vs Time [s]",
                                times, [np.degrees(yaw), np.degrees(pitch), np.degrees(roll)],
                                ['Yaw', 'Pitch', 'Roll'],
                                ['orange', 'green', 'purple']
                            )
                        else:
                            fig6 = self._create_placeholder_chart("Attitude Analysis - Euler Angles [°] vs Time [s]")
                    except Exception as e:
                        logger.warning(f"Could not create attitude chart: {e}")
                        fig6 = self._create_placeholder_chart("Attitude Analysis - Euler Angles [°] vs Time [s]")
                    self._add_chart_to_grid(fig6, 1, 2)
                    
                    # Chart 7: Velocity Components
                    try:
                        times = np.array(history.get('hist_time', []))
                        v_bx = np.array(history.get('hist_v_bx', []))
                        v_by = np.array(history.get('hist_v_by', []))
                        v_bz = np.array(history.get('hist_v_bz', []))
                        
                        if len(times) > 0:
                            fig7 = self._create_multiline_chart(
                                "Velocity Components [m/s] vs Time [s]",
                                times, [v_bx, v_by, v_bz],
                                ['Vx', 'Vy', 'Vz'],
                                ['red', 'green', 'blue']
                            )
                        else:
                            fig7 = self._create_placeholder_chart("Velocity Components [m/s] vs Time [s]")
                    except Exception as e:
                        logger.warning(f"Could not create velocity chart: {e}")
                        fig7 = self._create_placeholder_chart("Velocity Components [m/s] vs Time [s]")
                    self._add_chart_to_grid(fig7, 2, 0)
                    
                    # Chart 8: Atmospheric Conditions
                    try:
                        altitude = np.array(history.get('hist_alt', []))
                        density = np.array(history.get('hist_density', []))
                        pressure = np.array(history.get('hist_press_amb', []))
                        
                        if len(altitude) > 0 and len(density) > 0:
                            fig8 = self._create_chart(
                                "Atmospheric Conditions vs Altitude [m]",
                                altitude, [density, pressure],
                                ['Density [kg/m³]', 'Pressure [Pa]'],
                                ['darkblue', 'darkgreen']
                            )
                        else:
                            fig8 = self._create_placeholder_chart("Atmospheric Conditions vs Altitude [m]")
                    except Exception as e:
                        logger.warning(f"Could not create atmosphere chart: {e}")
                        fig8 = self._create_placeholder_chart("Atmospheric Conditions vs Altitude [m]")
                    self._add_chart_to_grid(fig8, 2, 1)
                    
                    # Chart 9: Aerodynamic Coefficients
                    try:
                        times = np.array(history.get('hist_time', []))
                        drag_coeff = np.array(history.get('hist_drag_coeff', []))
                        lift_coeff = np.array(history.get('hist_lift_coeff', []))
                        mach = np.array(history.get('hist_mach', []))
                        
                        if len(times) > 0:
                            fig9 = self._create_multiline_chart(
                                "Aerodynamic Coefficients [-] vs Time [s]",
                                times, [drag_coeff, lift_coeff, mach],
                                ['Cd', 'Cl', 'Mach'],
                                ['brown', 'pink', 'gray']
                            )
                        else:
                            fig9 = self._create_placeholder_chart("Aerodynamic Coefficients [-] vs Time [s]")
                    except Exception as e:
                        logger.warning(f"Could not create aero coefficients chart: {e}")
                        fig9 = self._create_placeholder_chart("Aerodynamic Coefficients [-] vs Time [s]")
                    self._add_chart_to_grid(fig9, 2, 2)
            else:
                # Fill remaining charts with placeholders if no history
                for i in range(1, 3):
                    for j in range(3):
                        fig = self._create_placeholder_chart(f"Chart ({i}, {j})")
                        self._add_chart_to_grid(fig, i, j)
            
            logger.info("Performance charts generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating charts: {e}")
            QMessageBox.warning(self, "Chart Error", f"Failed to generate charts: {str(e)}")
    
    def _create_chart(self, title, x_data, y_data_list, labels, colors_list):
        """Create a matplotlib figure with multiple y-axes."""
        fig, ax1 = plt.subplots(figsize=(8, 6), dpi=100)
        fig.suptitle(title, fontsize=12, fontweight='bold')
        
        # Plot first dataset
        color = colors_list[0]
        ax1.set_xlabel('Time [s]')
        ax1.set_ylabel(labels[0], color=color)
        ax1.plot(x_data, y_data_list[0], color=color, linewidth=2)
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, alpha=0.3)
        
        # Plot second dataset on secondary y-axis
        if len(y_data_list) > 1:
            ax2 = ax1.twinx()
            color = colors_list[1]
            ax2.set_ylabel(labels[1], color=color)
            ax2.plot(x_data, y_data_list[1], color=color, linewidth=2)
            ax2.tick_params(axis='y', labelcolor=color)
        
        plt.tight_layout()
        return fig
    
    def _create_simple_chart(self, title, x_data, y_data, x_label, y_label):
        """Create a simple matplotlib figure with single dataset."""
        fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        fig.suptitle(title, fontsize=12, fontweight='bold')
        
        ax.plot(x_data, y_data, 'b-', linewidth=2)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def _create_multiline_chart(self, title, x_data, y_data_list, labels, colors_list):
        """Create a matplotlib figure with multiple lines on same y-axis."""
        fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        fig.suptitle(title, fontsize=12, fontweight='bold')
        
        for i, y_data in enumerate(y_data_list):
            if len(y_data) > 0:
                ax.plot(x_data, y_data, color=colors_list[i], linewidth=2, label=labels[i])
        
        ax.set_xlabel('Time [s]')
        ax.set_ylabel('Value')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def _create_placeholder_chart(self, title):
        """Create a placeholder chart."""
        fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        fig.suptitle(title, fontsize=12, fontweight='bold')
        
        ax.text(0.5, 0.5, 'Data not available\nin current simulation', 
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes, fontsize=12, color='gray')
        ax.axis('off')
        
        plt.tight_layout()
        return fig
    
    def _add_chart_to_grid(self, fig, row, col):
        """Add a matplotlib figure to the grid layout."""
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(500)
        canvas.setMinimumWidth(650)
        self.charts_grid_layout.addWidget(canvas, row, col)
    
    def generate_trajectory_maps(self, sim_data, metadata):
        """Generate 2D and 3D trajectory maps from simulation data."""
        try:
            trajectory = sim_data.get('trajectory', [])
            
            if not trajectory:
                logger.warning("No trajectory data for maps")
                return
            
            # Extract trajectory data
            times = np.array([p.get('time', 0) for p in trajectory])
            altitudes = np.array([p.get('altitude', 0) for p in trajectory])
            ranges = np.array([p.get('range', 0) for p in trajectory])
            
            # Generate 2D trajectory map
            self._generate_2d_map(ranges, altitudes, metadata)
            
            # Generate 3D flight path
            self._generate_3d_flight_path(times, ranges, altitudes)
            
            logger.info("Trajectory maps generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating maps: {e}")
    
    def _generate_2d_map(self, ranges, altitudes, metadata):
        """Generate a 2D trajectory map showing flight path from above."""
        try:
            if not HAS_WEBENGINE or not self.map_2d_view:
                return
            
            # Create a 2D map using folium if available
            if HAS_FOLIUM:
                # Get launch coordinates from metadata or use default
                launch_lat = metadata.get('launch_latitude', 0.0)
                launch_lon = metadata.get('launch_longitude', 0.0)
                
                # Create base map
                m = folium.Map(
                    location=[launch_lat, launch_lon],
                    zoom_start=14,
                    tiles='OpenStreetMap'
                )
                
                # Add launch site marker
                folium.CircleMarker(
                    location=[launch_lat, launch_lon],
                    radius=8,
                    popup='Launch Site',
                    color='red',
                    fill=True,
                    fillColor='red',
                    fillOpacity=0.7,
                    weight=2
                ).add_to(m)
                
                # Calculate approximate landing coordinates
                # Assuming ranges are downrange distances (simplified)
                max_range_km = ranges.max() / 1000  # Convert m to km
                lat_delta = max_range_km / 111.32  # 1 degree ≈ 111.32 km
                
                landing_lat = launch_lat + lat_delta
                landing_lon = launch_lon
                
                # Add landing site marker
                folium.CircleMarker(
                    location=[landing_lat, landing_lon],
                    radius=8,
                    popup='Landing Site',
                    color='green',
                    fill=True,
                    fillColor='green',
                    fillOpacity=0.7,
                    weight=2
                ).add_to(m)
                
                # Draw trajectory approximation (simplified as line between launch and landing)
                coords = [[launch_lat, launch_lon], [landing_lat, landing_lon]]
                folium.PolyLine(
                    coords,
                    color='blue',
                    weight=3,
                    opacity=0.8,
                    popup='Flight Path'
                ).add_to(m)
                
                # Add max altitude circle
                max_alt_km = altitudes.max() / 1000
                folium.CircleMarker(
                    location=[launch_lat + lat_delta/2, launch_lon],
                    radius=6,
                    popup=f'Apogee: {max_alt_km:.2f} km',
                    color='orange',
                    fill=True,
                    fillColor='orange',
                    fillOpacity=0.5,
                    weight=2
                ).add_to(m)
                
                # Save map to HTML and display
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                    m.save(f.name)
                    self.map_2d_view.setUrl(f"file:///{f.name}")
                    
            else:
                # Fallback: Create a simple 2D matplotlib plot
                self._generate_2d_matplotlib_map(ranges, altitudes)
                
        except Exception as e:
            logger.error(f"Error generating 2D map: {e}")
    
    def _generate_2d_matplotlib_map(self, ranges, altitudes):
        """Generate a simple 2D map using matplotlib (fallback)."""
        fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        
        # Plot range vs altitude as trajectory
        ax.plot(ranges / 1000, altitudes / 1000, 'b-', linewidth=2, label='Flight Path')
        ax.scatter([0], [0], color='red', s=100, marker='*', label='Launch', zorder=5)
        ax.scatter([ranges.max()/1000], [0], color='green', s=100, marker='X', label='Landing', zorder=5)
        ax.scatter([ranges[altitudes.argmax()]/1000], [altitudes.max()/1000], 
                  color='orange', s=100, marker='o', label='Apogee', zorder=5)
        
        ax.set_xlabel('Range [km]')
        ax.set_ylabel('Altitude [km]')
        ax.set_title('2D Flight Trajectory')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Create canvas
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(500)
        
        # Add to map container if it exists
        if hasattr(self, 'map_2d_container') and self.map_2d_container:
            map_layout = self.map_2d_container.layout()
            if map_layout is None:
                map_layout = QVBoxLayout()
                self.map_2d_container.setLayout(map_layout)
            
            # Clear previous widgets
            while map_layout.count():
                map_layout.takeAt(0).widget().deleteLater()
            
            map_layout.addWidget(canvas)
    
    def _generate_3d_flight_path(self, times, ranges, altitudes):
        """Generate a 3D flight path visualization."""
        try:
            # Clear previous canvas
            if self.map_3d_canvas:
                self.map_3d_canvas.deleteLater()
            
            # Create 3D plot
            fig = plt.figure(figsize=(8, 7), dpi=100)
            ax = fig.add_subplot(111, projection='3d')
            
            # Convert to km for better scale
            ranges_km = ranges / 1000
            altitudes_km = altitudes / 1000
            
            # Create 3D trajectory
            ax.plot(ranges_km, np.zeros_like(ranges_km), altitudes_km, 'b-', linewidth=2, label='Flight Path')
            
            # Mark key points
            ax.scatter([0], [0], [0], color='red', s=100, marker='*', label='Launch', zorder=5)
            ax.scatter([ranges_km[-1]], [0], [0], color='green', s=100, marker='X', label='Landing', zorder=5)
            
            # Find and mark apogee
            apogee_idx = np.argmax(altitudes_km)
            ax.scatter([ranges_km[apogee_idx]], [0], [altitudes_km[apogee_idx]], 
                      color='orange', s=100, marker='o', label='Apogee', zorder=5)
            
            # Ground plane
            ax.plot([0, ranges_km.max()], [0, 0], [0, 0], 'k--', alpha=0.3)
            
            ax.set_xlabel('Range [km]')
            ax.set_ylabel('Lateral [km]')
            ax.set_zlabel('Altitude [km]')
            ax.set_title('3D Flight Path')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Add to container
            self.map_3d_canvas = FigureCanvas(fig)
            self.map_3d_canvas.setMinimumHeight(500)
            
            # Clear and add to layout
            map_3d_layout = self.map_3d_container.layout()
            if map_3d_layout is None:
                map_3d_layout = QVBoxLayout()
                self.map_3d_container.setLayout(map_3d_layout)
            
            # Clear previous widgets
            while map_3d_layout.count():
                map_3d_layout.takeAt(0).widget().deleteLater()
            
            map_3d_layout.addWidget(self.map_3d_canvas)
            
        except Exception as e:
            logger.error(f"Error generating 3D flight path: {e}")
    
    def export_csv(self):
        """Export simulation data to CSV."""
        if not self.current_sim_id:
            QMessageBox.warning(self, "Warning", "No simulation loaded")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", f"simulation_{self.current_sim_id[:8]}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not filepath:
            return
        
        try:
            sim_data = self.sim_manager.load_simulation(self.current_sim_id)
            metadata = self.sim_manager.metadata.get(self.current_sim_id, {})
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write metadata section
                writer.writerow(["SIMULATION METADATA"])
                writer.writerow(["Simulation ID", self.current_sim_id])
                writer.writerow(["Rocket", metadata.get('rocket', 'Unknown')])
                writer.writerow(["Location", metadata.get('location', 'Unknown')])
                writer.writerow(["Date", metadata.get('launch_date', 'Unknown')])
                writer.writerow(["Time", metadata.get('launch_time', 'Unknown')])
                writer.writerow(["Temperature", f"{metadata.get('temperature', 0):.2f} °C"])
                writer.writerow(["Pressure", f"{metadata.get('pressure', 0):.0f} Pa"])
                writer.writerow([])
                
                # Write metrics section
                writer.writerow(["KEY METRICS"])
                writer.writerow(["Metric", "Value", "Unit"])
                writer.writerow(["Max Altitude", f"{metadata.get('max_altitude', 0):.3f}", "km"])
                writer.writerow(["Max Velocity", f"{metadata.get('max_velocity', 0):.2f}", "m/s"])
                writer.writerow(["Max Mach", f"{metadata.get('max_mach', 0):.2f}", ""])
                writer.writerow(["Flight Duration", f"{metadata.get('flight_duration', 0):.2f}", "s"])
                writer.writerow(["Max Acceleration", f"{metadata.get('max_accel_g', 0):.2f}", "g"])
                writer.writerow([])
                
                # Write trajectory data if available
                if isinstance(sim_data, dict) and 'trajectory' in sim_data:
                    writer.writerow(["FLIGHT TRAJECTORY"])
                    writer.writerow(["Time (s)", "Altitude (m)", "Velocity (m/s)", "Acceleration (m/s²)"])
                    
                    trajectory = sim_data['trajectory']
                    if isinstance(trajectory, list):
                        for point in trajectory:
                            if isinstance(point, dict):
                                writer.writerow([
                                    f"{point.get('time', 0):.3f}",
                                    f"{point.get('altitude', 0):.2f}",
                                    f"{point.get('velocity', 0):.2f}",
                                    f"{point.get('acceleration', 0):.2f}"
                                ])
                    writer.writerow([])
                
                # Write raw data section
                writer.writerow(["RAW SIMULATION DATA (JSON)"])
                writer.writerow([json.dumps(sim_data, indent=2)])
            
            QMessageBox.information(
                self, "Success",
                f"Data exported successfully to:\n{filepath}"
            )
            logger.info(f"CSV exported: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV:\n{str(e)}")
            logger.error(f"CSV export error: {e}")
    
    def generate_pdf(self):
        """Generate PDF report."""
        if not self.current_sim_id:
            QMessageBox.warning(self, "Warning", "No simulation loaded")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Generate PDF", f"simulation_{self.current_sim_id[:8]}.pdf",
            "PDF Files (*.pdf);;All Files (*)"
        )
        
        if not filepath:
            return
        
        try:
            sim_data = self.sim_manager.load_simulation(self.current_sim_id)
            metadata = self.sim_manager.metadata.get(self.current_sim_id, {})
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            elements = []
            
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f77b4'),
                spaceAfter=30,
                alignment=1  # Center
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#2ca02c'),
                spaceAfter=12,
                spaceBefore=12
            )
            
            # Title
            elements.append(Paragraph("Rocket Flight Simulation Report", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Metadata section
            elements.append(Paragraph("Simulation Information", heading_style))
            
            metadata_data = [
                ["Property", "Value"],
                ["Simulation ID", self.current_sim_id],
                ["Rocket", metadata.get('rocket', 'Unknown')],
                ["Location", metadata.get('location', 'Unknown')],
                ["Launch Date", metadata.get('launch_date', 'Unknown')],
                ["Launch Time", metadata.get('launch_time', 'Unknown')],
                ["Timestamp", metadata.get('timestamp', 'Unknown')[:19]],
            ]
            
            metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
            metadata_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            elements.append(metadata_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Key metrics section
            elements.append(Paragraph("Flight Metrics", heading_style))
            
            metrics_data = [
                ["Metric", "Value", "Unit"],
                ["Max Altitude", f"{metadata.get('max_altitude', 0):.3f}", "km"],
                ["Max Velocity", f"{metadata.get('max_velocity', 0):.2f}", "m/s"],
                ["Max Mach Number", f"{metadata.get('max_mach', 0):.2f}", ""],
                ["Max Range", f"{metadata.get('max_range', 0):.2f}", "km"],
                ["Flight Duration", f"{metadata.get('flight_duration', 0):.2f}", "s"],
                ["Max Acceleration", f"{metadata.get('max_accel_g', 0):.2f}", "g"],
            ]
            
            metrics_table = Table(metrics_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ca02c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightcyan),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            elements.append(metrics_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Environmental conditions
            elements.append(Paragraph("Environmental Conditions", heading_style))
            
            env_data = [
                ["Parameter", "Value"],
                ["Temperature", f"{metadata.get('temperature', 0):.1f} °C"],
                ["Pressure", f"{metadata.get('pressure', 0):.0f} Pa"],
            ]
            
            env_table = Table(env_data, colWidths=[2*inch, 4*inch])
            env_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d62728')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(env_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Footer
            elements.append(Spacer(1, 0.5*inch))
            footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            elements.append(Paragraph(footer_text, ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.grey,
                alignment=2  # Right align
            )))
            
            # Build PDF
            doc.build(elements)
            
            QMessageBox.information(
                self, "Success",
                f"PDF report generated successfully:\n{filepath}"
            )
            logger.info(f"PDF generated: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{str(e)}")
            logger.error(f"PDF generation error: {e}")
    
    def refresh_dashboard(self):
        """Refresh dashboard with latest results."""
        self.load_simulation_history()
        
        # Try to load recent simulation
        recent = self.sim_manager.get_recent_simulation()
        if recent:
            self.current_sim_id = recent.get('id')
            self.sim_combo.setCurrentIndex(0)
            logger.info("Dashboard refreshed with recent simulation")
        else:
            logger.info("Dashboard refreshed (no simulations)")

