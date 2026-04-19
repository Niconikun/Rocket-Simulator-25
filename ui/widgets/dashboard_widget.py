"""Dashboard Widget - Simulation results visualization."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
    QGridLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QMessageBox, QFileDialog, QScrollArea, QTabWidget,
    QHeaderView
)
from PyQt6.QtCore import Qt, QUrl
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
        # Outer layout holds the scroll area
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Inner widget contains all dashboard content
        inner_widget = QWidget()
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
        
        # ===== FLIGHT EVENTS TIMELINE =====
        events_group = QGroupBox("Flight Events Timeline")
        events_layout = QVBoxLayout()
        
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(4)
        self.events_table.setHorizontalHeaderLabels(["Event", "Time [s]", "Altitude [m]", "Velocity [m/s]"])
        header = self.events_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.events_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.events_table.setAlternatingRowColors(True)
        self.events_table.setMaximumHeight(200)
        events_layout.addWidget(self.events_table)
        
        events_group.setLayout(events_layout)
        main_layout.addWidget(events_group)
        
        # ===== PARACHUTE RECOVERY SUMMARY =====
        self.parachute_group = QGroupBox("Parachute Recovery")
        parachute_layout = QGridLayout()
        
        self.parachute_labels = {}
        parachute_fields = [
            ("deploy_alt", "Deployment Altitude"),
            ("deploy_vel", "Deployment Velocity"),
            ("deploy_time", "Deployment Time"),
            ("landing_speed", "Landing Speed"),
            ("max_descent", "Max Descent Rate"),
            ("drogue_status", "Drogue Status"),
        ]
        
        for i, (key, label) in enumerate(parachute_fields):
            row = i // 3
            col = (i % 3) * 2
            parachute_layout.addWidget(QLabel(f"{label}:"), row, col)
            value_label = QLabel("N/A")
            value_label.setStyleSheet("font-weight: bold;")
            self.parachute_labels[key] = value_label
            parachute_layout.addWidget(value_label, row, col + 1)
        
        self.parachute_group.setLayout(parachute_layout)
        self.parachute_group.setVisible(False)  # Hidden by default
        main_layout.addWidget(self.parachute_group)
        
        # ===== FLIGHT VISUALIZATION (all charts as tabs) =====
        viz_group = QGroupBox("Flight Visualization")
        viz_layout = QVBoxLayout()
        self.charts_tab_widget = QTabWidget()
        self.charts_tab_widget.setMinimumHeight(550)
        viz_layout.addWidget(self.charts_tab_widget)
        viz_group.setLayout(viz_layout)
        main_layout.addWidget(viz_group, 1)  # Stretch factor to expand
        
        # --- 2D Trajectory Map (kept as a tab or webengine fallback) ---
        if HAS_WEBENGINE:
            self.map_2d_view = QWebEngineView()
            self.map_2d_view.setMinimumHeight(400)
        else:
            self.map_2d_view = None
            self.map_2d_container = QWidget()
            self.map_2d_container.setLayout(QVBoxLayout())
        
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
        inner_widget.setLayout(main_layout)
        scroll_area.setWidget(inner_widget)
        outer_layout.addWidget(scroll_area)
        self.setLayout(outer_layout)
    
    def load_simulation_history(self):
        """Load list of simulations from manager."""
        self.sim_combo.blockSignals(True)
        self.sim_combo.clear()
        
        # Reload metadata from disk to pick up new simulations
        self.sim_manager.reload_metadata()
        
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
        
        # Fallback: if metadata lacks max_mach/max_accel_g, compute from sim_data
        sim_metrics = sim_data.get('metrics', {}) if isinstance(sim_data, dict) else {}
        if not metadata.get('max_mach') and sim_metrics.get('max_mach'):
            metadata['max_mach'] = sim_metrics['max_mach']
        if not metadata.get('max_accel_g') and sim_metrics.get('max_accel_g'):
            metadata['max_accel_g'] = sim_metrics['max_accel_g']
        
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
        self.metric_labels['max_mach'].setText(
            f"{metadata.get('max_mach', 0):.2f}"
        )
        self.metric_labels['flight_duration'].setText(
            f"{metadata.get('flight_duration', 0):.2f} s"
        )
        self.metric_labels['max_accel_g'].setText(
            f"{metadata.get('max_accel_g', 0):.2f} g"
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
        
        # Populate flight events timeline
        self._populate_flight_events(sim_data)
        
        # Populate parachute summary
        self._populate_parachute_summary(sim_data, metadata)
        
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
    
    def _populate_flight_events(self, sim_data):
        """Detect and display flight events in the events table."""
        self.events_table.setRowCount(0)
        
        if not sim_data or not isinstance(sim_data, dict):
            return
        
        history = sim_data.get('history', {})
        metrics = sim_data.get('metrics', {})
        parachute_info = sim_data.get('parachute_info', {})
        
        events = []
        
        # Event 1: Ignition (always at t=0)
        events.append(("🔥 Ignition", 0.0, 0.0, 0.0))
        
        if isinstance(history, dict) and history:
            times = np.array(history.get('hist_time', []))
            altitudes = np.array(history.get('hist_alt', []))
            velocities = np.array(history.get('hist_v_norm', []))
            thrust = np.array(history.get('hist_thrust', []))
            
            if len(times) > 0:
                # Event 2: Burnout (thrust drops to ~0)
                if len(thrust) > 0:
                    burn_mask = thrust > 0.1
                    if burn_mask.any() and not burn_mask.all():
                        burnout_idx = np.where(burn_mask)[0][-1]
                        events.append(("🛑 Burnout", 
                                      times[burnout_idx],
                                      altitudes[burnout_idx] if len(altitudes) > burnout_idx else 0,
                                      velocities[burnout_idx] if len(velocities) > burnout_idx else 0))
                
                # Event 3: Max-Q
                density = np.array(history.get('hist_density', []))
                if len(density) > 0 and len(velocities) > 0:
                    q = 0.5 * density * velocities**2
                    maxq_idx = np.argmax(q)
                    events.append(("💨 Max-Q",
                                  times[maxq_idx],
                                  altitudes[maxq_idx] if len(altitudes) > maxq_idx else 0,
                                  velocities[maxq_idx] if len(velocities) > maxq_idx else 0))
                
                # Event 4: Apogee
                if len(altitudes) > 0:
                    apogee_idx = np.argmax(altitudes)
                    events.append(("🏔️ Apogee",
                                  times[apogee_idx],
                                  altitudes[apogee_idx],
                                  velocities[apogee_idx] if len(velocities) > apogee_idx else 0))
                
                # Event 5: Parachute deployment
                if parachute_info and parachute_info.get('deployed', False):
                    events.append(("🪂 Parachute Deploy",
                                  parachute_info.get('deployment_time', 0),
                                  parachute_info.get('deployment_altitude', 0),
                                  parachute_info.get('deployment_velocity', 0)))
                
                # Event 6: Drogue deployment
                if parachute_info and parachute_info.get('drogue_deployed', False):
                    events.append(("🪂 Drogue Deploy",
                                  parachute_info.get('drogue_deployment_time', 0),
                                  parachute_info.get('drogue_deployment_altitude', 0),
                                  0))
                
                # Event 7: Landing (last data point)
                events.append(("🎯 Landing",
                              times[-1],
                              altitudes[-1] if len(altitudes) > 0 else 0,
                              velocities[-1] if len(velocities) > 0 else 0))
        
        # Sort events by time
        events.sort(key=lambda x: x[1])
        
        # Populate table
        self.events_table.setRowCount(len(events))
        for row, (event, time, alt, vel) in enumerate(events):
            self.events_table.setItem(row, 0, QTableWidgetItem(event))
            self.events_table.setItem(row, 1, QTableWidgetItem(f"{time:.3f}"))
            self.events_table.setItem(row, 2, QTableWidgetItem(f"{alt:.2f}"))
            self.events_table.setItem(row, 3, QTableWidgetItem(f"{vel:.2f}"))
    
    def _populate_parachute_summary(self, sim_data, metadata):
        """Populate the parachute recovery summary panel."""
        parachute_info = sim_data.get('parachute_info', {}) if isinstance(sim_data, dict) else {}
        metrics = sim_data.get('metrics', {}) if isinstance(sim_data, dict) else {}
        
        has_parachute = bool(
            metadata.get('parachute_enabled', False) or
            (parachute_info and parachute_info.get('deployed', False))
        )
        
        self.parachute_group.setVisible(has_parachute)
        
        if not has_parachute:
            return
        
        deploy_alt = (parachute_info.get('deployment_altitude', 0) or
                     metrics.get('parachute_deployment_altitude', 0))
        deploy_vel = (parachute_info.get('deployment_velocity', 0) or
                     metrics.get('parachute_deployment_velocity', 0))
        deploy_time = (parachute_info.get('deployment_time', 0) or
                      metrics.get('parachute_deployment_time', 0))
        landing_speed = metrics.get('parachute_landing_speed', 0)
        max_descent = metrics.get('parachute_max_descent_rate', 0)
        drogue = parachute_info.get('drogue_deployed', False)
        
        self.parachute_labels['deploy_alt'].setText(f"{deploy_alt:.1f} m")
        self.parachute_labels['deploy_vel'].setText(f"{deploy_vel:.1f} m/s")
        self.parachute_labels['deploy_time'].setText(f"{deploy_time:.2f} s")
        self.parachute_labels['landing_speed'].setText(
            f"{landing_speed:.1f} m/s" if landing_speed else "N/A"
        )
        self.parachute_labels['max_descent'].setText(
            f"{max_descent:.1f} m/s" if max_descent else "N/A"
        )
        self.parachute_labels['drogue_status'].setText(
            "Deployed ✅" if drogue else "Not deployed"
        )
    
    def generate_performance_charts(self, sim_data):
        """Generate performance charts as tabs from simulation data."""
        # Clear previous tabs
        self.charts_tab_widget.clear()
        
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
            self._add_chart_as_tab(fig1, "Altitude & Velocity")
            
            # Chart 2: Flight Path - Altitude vs Range
            fig2 = self._create_simple_chart(
                "Flight Path - Altitude [m] vs Range [m]",
                ranges, altitudes, 'Range', 'Altitude'
            )
            self._add_chart_as_tab(fig2, "Flight Path")
            
            # Chart 3: Mach & AoA vs Time  (placeholder - use mach data)
            fig3 = self._create_simple_chart(
                "Mach Number vs Time [s]",
                times, machs, 'Time', 'Mach'
            )
            self._add_chart_as_tab(fig3, "Mach Number")
            
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
                    self._add_chart_as_tab(fig4, "Forces")
                    
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
                    self._add_chart_as_tab(fig5, "Mass & Altitude")
                    
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
                    self._add_chart_as_tab(fig6, "Attitude")
                    
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
                    self._add_chart_as_tab(fig7, "Velocity Components")
                    
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
                    self._add_chart_as_tab(fig8, "Atmosphere")
                    
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
                    self._add_chart_as_tab(fig9, "Aero Coefficients")
                    
                    # Chart 10: Dynamic Pressure (Q)
                    try:
                        times = np.array(history.get('hist_time', []))
                        density = np.array(history.get('hist_density', []))
                        v_norm = np.array(history.get('hist_v_norm', []))
                        
                        if len(times) > 0 and len(density) > 0 and len(v_norm) > 0:
                            q_dynamic = 0.5 * density * v_norm**2
                            max_q_idx = np.argmax(q_dynamic)
                            
                            fig10, ax = plt.subplots(figsize=(8, 6), dpi=100)
                            fig10.suptitle("Dynamic Pressure (Q) [Pa] vs Time [s]", fontsize=12, fontweight='bold')
                            ax.plot(times, q_dynamic, color='darkred', linewidth=2, label='Q')
                            ax.axvline(x=times[max_q_idx], color='orange', linestyle='--', linewidth=1.5,
                                      label=f'Max-Q: {q_dynamic[max_q_idx]:.0f} Pa @ {times[max_q_idx]:.2f}s')
                            ax.set_xlabel('Time [s]')
                            ax.set_ylabel('Dynamic Pressure [Pa]')
                            ax.legend(loc='best')
                            ax.grid(True, alpha=0.3)
                            plt.tight_layout()
                        else:
                            fig10 = self._create_placeholder_chart("Dynamic Pressure (Q) [Pa] vs Time [s]")
                    except Exception as e:
                        logger.warning(f"Could not create dynamic pressure chart: {e}")
                        fig10 = self._create_placeholder_chart("Dynamic Pressure (Q) [Pa] vs Time [s]")
                    self._add_chart_as_tab(fig10, "Dynamic Pressure")
                    
                    # Chart 11: Thrust-to-Weight Ratio
                    try:
                        times = np.array(history.get('hist_time', []))
                        thrust = np.array(history.get('hist_thrust', []))
                        mass = np.array(history.get('hist_mass', []))
                        
                        if len(times) > 0 and len(thrust) > 0 and len(mass) > 0:
                            g0 = 9.80665
                            twr = np.where(mass > 0, thrust / (mass * g0), 0)
                            
                            fig11, ax = plt.subplots(figsize=(8, 6), dpi=100)
                            fig11.suptitle("Thrust-to-Weight Ratio vs Time [s]", fontsize=12, fontweight='bold')
                            ax.plot(times, twr, color='green', linewidth=2, label='TWR')
                            ax.axhline(y=1.0, color='red', linestyle='--', linewidth=1.5, label='TWR = 1.0')
                            ax.set_xlabel('Time [s]')
                            ax.set_ylabel('TWR [-]')
                            ax.legend(loc='best')
                            ax.grid(True, alpha=0.3)
                            plt.tight_layout()
                        else:
                            fig11 = self._create_placeholder_chart("Thrust-to-Weight Ratio vs Time [s]")
                    except Exception as e:
                        logger.warning(f"Could not create TWR chart: {e}")
                        fig11 = self._create_placeholder_chart("Thrust-to-Weight Ratio vs Time [s]")
                    self._add_chart_as_tab(fig11, "Thrust/Weight")
                    
                    # Chart 12: Energy Analysis
                    try:
                        times = np.array(history.get('hist_time', []))
                        mass = np.array(history.get('hist_mass', []))
                        v_norm = np.array(history.get('hist_v_norm', []))
                        altitude = np.array(history.get('hist_alt', []))
                        
                        if len(times) > 0 and len(mass) > 0 and len(v_norm) > 0:
                            g0 = 9.80665
                            ke = 0.5 * mass * v_norm**2
                            pe = mass * g0 * np.maximum(altitude, 0)
                            total_e = ke + pe
                            
                            # Convert to kJ for readability
                            fig12 = self._create_multiline_chart(
                                "Energy Analysis [kJ] vs Time [s]",
                                times, [ke / 1000, pe / 1000, total_e / 1000],
                                ['Kinetic', 'Potential', 'Total'],
                                ['red', 'blue', 'purple']
                            )
                        else:
                            fig12 = self._create_placeholder_chart("Energy Analysis [kJ] vs Time [s]")
                    except Exception as e:
                        logger.warning(f"Could not create energy chart: {e}")
                        fig12 = self._create_placeholder_chart("Energy Analysis [kJ] vs Time [s]")
                    self._add_chart_as_tab(fig12, "Energy")
                    
                    # Chart 13: Stability Margin (CM to CP distance)
                    try:
                        times = np.array(history.get('hist_time', []))
                        cm_b = np.array(history.get('hist_cm_b', []))
                        cp_b = np.array(history.get('hist_cp_b', []))
                        
                        if len(times) > 0 and len(cm_b) > 0 and len(cp_b) > 0:
                            # Static margin = distance from CM to CP along rocket axis (index 0)
                            if cm_b.ndim == 2 and cp_b.ndim == 2:
                                margin = cp_b[:, 0] - cm_b[:, 0]
                            else:
                                margin = np.array(history.get('hist_cm2cp_b', []))
                                if margin.ndim == 2:
                                    margin = margin[:, 0]
                            
                            fig13, ax = plt.subplots(figsize=(8, 6), dpi=100)
                            fig13.suptitle("Static Margin [m] vs Time [s]", fontsize=12, fontweight='bold')
                            ax.plot(times, margin, color='teal', linewidth=2, label='Static Margin')
                            ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7, label='Neutral stability')
                            ax.set_xlabel('Time [s]')
                            ax.set_ylabel('Static Margin [m]')
                            ax.legend(loc='best')
                            ax.grid(True, alpha=0.3)
                            plt.tight_layout()
                        else:
                            fig13 = self._create_placeholder_chart("Static Margin [m] vs Time [s]")
                    except Exception as e:
                        logger.warning(f"Could not create stability chart: {e}")
                        fig13 = self._create_placeholder_chart("Static Margin [m] vs Time [s]")
                    self._add_chart_as_tab(fig13, "Stability")
            else:
                # Fill remaining charts with placeholders if no history
                placeholders = ["Forces", "Mass & Altitude", "Attitude",
                                "Velocity Components", "Atmosphere", "Aero Coefficients",
                                "Dynamic Pressure", "Thrust/Weight", "Energy", "Stability"]
                for name in placeholders:
                    fig = self._create_placeholder_chart(name)
                    self._add_chart_as_tab(fig, name)
            
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
    
    def _add_chart_as_tab(self, fig, tab_name):
        """Add a matplotlib figure as a new tab in the charts tab widget."""
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(450)
        
        # Wrap in a scroll area so individual charts can be scrolled
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(canvas)
        
        self.charts_tab_widget.addTab(scroll, tab_name)
    
    def generate_trajectory_maps(self, sim_data, metadata):
        """Generate 2D map (as tab) and 3D trajectory (left panel) from simulation data."""
        try:
            trajectory = sim_data.get('trajectory', [])
            
            if not trajectory:
                logger.warning("No trajectory data for maps")
                return
            
            # Extract trajectory data
            times = np.array([p.get('time', 0) for p in trajectory])
            altitudes = np.array([p.get('altitude', 0) for p in trajectory])
            ranges = np.array([p.get('range', 0) for p in trajectory])
            
            # Generate 2D trajectory map (added as a tab)
            self._generate_2d_map(ranges, altitudes, metadata)
            
            # Generate 3D flight path (left panel)
            self._generate_3d_flight_path(times, ranges, altitudes)
            
            logger.info("Trajectory maps generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating maps: {e}")
    
    def _generate_2d_map(self, ranges, altitudes, metadata):
        """Generate a 2D trajectory map and add it as a tab."""
        try:
            if HAS_WEBENGINE and self.map_2d_view and HAS_FOLIUM:
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
                max_range_km = ranges.max() / 1000
                lat_delta = max_range_km / 111.32
                
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
                
                # Draw trajectory approximation
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
                
                # Save map to HTML and display in a tab
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                    m.save(f.name)
                    self.map_2d_view.setUrl(QUrl.fromLocalFile(f.name))
                
                # Add webengine view as a tab
                self.charts_tab_widget.addTab(self.map_2d_view, "2D Trajectory Map")
            else:
                # Fallback: matplotlib-based 2D map as a tab
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
        
        # Add as a tab
        self._add_chart_as_tab(fig, "2D Trajectory Map")
    
    def _generate_3d_flight_path(self, times, ranges, altitudes):
        """Generate a 3D flight path visualization as a tab."""
        try:
            # Create 3D plot
            fig = plt.figure(figsize=(8, 7), dpi=100)
            ax = fig.add_subplot(111, projection='3d')
            
            # Convert to km for better scale
            ranges_km = ranges / 1000
            altitudes_km = altitudes / 1000
            
            # Create 3D trajectory
            ax.plot(ranges_km, np.zeros_like(ranges_km), altitudes_km, 'b-', linewidth=2, label='Flight Path')
            
            # Mark key points
            ax.scatter(0, 0, 0, color='red', s=100, marker='*', label='Launch', zorder=5)
            ax.scatter(ranges_km[-1], 0, 0, color='green', s=100, marker='X', label='Landing', zorder=5)
            
            # Find and mark apogee
            apogee_idx = np.argmax(altitudes_km)
            ax.scatter(ranges_km[apogee_idx], 0, altitudes_km[apogee_idx], 
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
            
            # Add as a tab
            self._add_chart_as_tab(fig, "3D Flight Path")
            
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

