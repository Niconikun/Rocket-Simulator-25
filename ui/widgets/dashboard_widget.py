"""Dashboard Widget - Simulation results visualization."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
    QGridLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QMessageBox, QFileDialog, QScrollArea, QTabWidget,
    QHeaderView, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette, QCloseEvent
from ui.widgets import BaseWidget
from models.app_state import ApplicationState
from src.models.state import StateProvider
from src.config import Constants
from typing import Optional
from src.utils.simulation_manager import SimulationManager
import logging
logger = logging.getLogger(__name__)
from datetime import datetime
import csv
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors

# Import matplotlib for plotting (kept for maps and compatibility)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

# Import PyQtGraph for performance charts
try:
    import pyqtgraph as pg
    from pyqtgraph import PlotWidget, PlotDataItem, PlotCurveItem, ViewBox, GraphicsLayoutWidget, InfiniteLine, mkPen
    from pyqtgraph.Qt import QtGui
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False
    logger.warning("PyQtGraph not available, falling back to matplotlib")

from pathlib import Path

from typing import Any

# Try to import cartopy for geographic map
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    HAS_CARTOPY = True
except ImportError:
    HAS_CARTOPY = False


class DashboardWidget(BaseWidget):
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
    
    def __init__(self, state: Optional[StateProvider] = None, parent=None):
        super().__init__(state=state, parent=parent)
        self.sim_manager = SimulationManager()
        self.current_sim_id = None
        self._active_figures = []  # matplotlib Figures tracked for explicit plt.close()
        self.init_ui()
        self.load_simulation_history()
    
    def closeEvent(self, event: QCloseEvent):
        """Clean up matplotlib figures when widget is closed."""
        self._close_active_figures()
        super().closeEvent(event)
    
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
    
    def load_simulation_history(self, *args):
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
        
        # Close previous figures to prevent memory leaks
        self._close_active_figures()
        
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
                                  parachute_info.get(Constants.StateKeys.DROGUE_DEPLOYMENT_ALTITUDE, 0),
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
            metadata.get(Constants.StateKeys.PARACHUTE_ENABLED, False) or
            (parachute_info and parachute_info.get('deployed', False))
        )
        
        self.parachute_group.setVisible(has_parachute)
        
        if not has_parachute:
            return
        
        deploy_alt = (parachute_info.get('deployment_altitude', 0) or
                     metrics.get(Constants.StateKeys.PARACHUTE_DEPLOYMENT_ALTITUDE, 0))
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
        """Generate performance charts as tabs from simulation data using PyQtGraph."""
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
            
            # Chart 1: Altitude & Velocity vs Time (Dual axis)
            plot1 = self._create_pyqtgraph_plot(
                "Altitude & Velocity",
                times, [altitudes, velocities], 
                ['Altitude [m]', 'Velocity [m/s]'], ['blue', 'red'],
                use_secondary_axis=True
            )
            self._add_pyqtgraph_as_tab(plot1, "Altitude & Velocity")
            
            # Chart 2: Flight Path - Altitude vs Range
            plot2 = self._create_pyqtgraph_simple_plot(
                "Flight Path",
                ranges, altitudes, 'Range [m]', 'Altitude [m]', color='blue', name='Flight Path'
            )
            self._add_pyqtgraph_as_tab(plot2, "Flight Path")
            
            # Chart 3: Mach Number vs Time
            plot3 = self._create_pyqtgraph_simple_plot(
                "Mach Number",
                times, machs, 'Time [s]', 'Mach', color='darkblue', name='Mach Number'
            )
            self._add_pyqtgraph_as_tab(plot3, "Mach Number")
            
            # Charts 4-13: Additional performance data if available from history
            # Generate advanced charts from history data using PyQtGraph
            self._generate_advanced_charts(history)
            
            logger.info("Performance charts generated successfully with PyQtGraph")
            
        except Exception as e:
            logger.error(f"Error generating charts: {e}")
            QMessageBox.warning(self, "Chart Error", f"Failed to generate charts: {str(e)}")
    
    def _generate_advanced_charts(self, history):
        """Generate advanced charts (4-13) using PyQtGraph."""
        if not isinstance(history, dict):
            # Fill with placeholders
            placeholders = ["Forces", "Mass & Altitude", "Attitude",
                          "Velocity Components", "Atmosphere", "Aero Coefficients",
                          "Dynamic Pressure", "Thrust/Weight", "Energy", "Stability"]
            for name in placeholders:
                plot = self._create_pyqtgraph_placeholder(name)
                self._add_pyqtgraph_as_tab(plot, name)
            return
        
        # Chart 4: Forces Analysis
        try:
            times = np.array(history.get('hist_time', []))
            thrust = np.array(history.get('hist_thrust', []))
            drag = np.array(history.get('hist_drag', []))
            lift = np.array(history.get('hist_lift', []))
            
            if len(times) > 0:
                plot4 = self._create_pyqtgraph_plot(
                    "Forces Analysis",
                    times, [thrust, drag, lift],
                    ['Thrust [N]', 'Drag [N]', 'Lift [N]'],
                    ['green', 'red', 'blue']
                )
            else:
                plot4 = self._create_pyqtgraph_placeholder("Forces Analysis")
        except Exception as e:
            logger.warning(f"Could not create forces chart: {e}")
            plot4 = self._create_pyqtgraph_placeholder("Forces Analysis")
        self._add_pyqtgraph_as_tab(plot4, "Forces")
        
        # Chart 5: Mass & Altitude
        try:
            times = np.array(history.get('hist_time', []))
            mass = np.array(history.get('hist_mass', []))
            altitude_hist = np.array(history.get('hist_alt', []))
            
            if len(times) > 0:
                plot5 = self._create_pyqtgraph_plot(
                    "Mass & Altitude",
                    times, [mass, altitude_hist],
                    ['Mass [kg]', 'Altitude [m]'],
                    ['purple', 'cyan']
                )
            else:
                plot5 = self._create_pyqtgraph_placeholder("Mass & Altitude")
        except Exception as e:
            logger.warning(f"Could not create mass chart: {e}")
            plot5 = self._create_pyqtgraph_placeholder("Mass & Altitude")
        self._add_pyqtgraph_as_tab(plot5, "Mass & Altitude")
        
        # Chart 6: Attitude (Euler Angles)
        try:
            times = np.array(history.get('hist_time', []))
            yaw = np.array(history.get('hist_yaw', []))
            pitch = np.array(history.get('hist_pitch', []))
            roll = np.array(history.get('hist_roll', []))
            
            if len(times) > 0:
                plot6 = self._create_pyqtgraph_plot(
                    "Attitude",
                    times, [np.degrees(yaw), np.degrees(pitch), np.degrees(roll)],
                    ['Yaw [°]', 'Pitch [°]', 'Roll [°]'],
                    ['orange', 'green', 'purple']
                )
            else:
                plot6 = self._create_pyqtgraph_placeholder("Attitude")
        except Exception as e:
            logger.warning(f"Could not create attitude chart: {e}")
            plot6 = self._create_pyqtgraph_placeholder("Attitude")
        self._add_pyqtgraph_as_tab(plot6, "Attitude")
        
        # Chart 7: Velocity Components
        try:
            times = np.array(history.get('hist_time', []))
            v_bx = np.array(history.get('hist_v_bx', []))
            v_by = np.array(history.get('hist_v_by', []))
            v_bz = np.array(history.get('hist_v_bz', []))
            
            if len(times) > 0:
                plot7 = self._create_pyqtgraph_plot(
                    "Velocity Components",
                    times, [v_bx, v_by, v_bz],
                    ['Vx [m/s]', 'Vy [m/s]', 'Vz [m/s]'],
                    ['red', 'green', 'blue']
                )
            else:
                plot7 = self._create_pyqtgraph_placeholder("Velocity Components")
        except Exception as e:
            logger.warning(f"Could not create velocity chart: {e}")
            plot7 = self._create_pyqtgraph_placeholder("Velocity Components")
        self._add_pyqtgraph_as_tab(plot7, "Velocity Components")
        
        # Chart 8: Atmospheric Conditions
        try:
            altitude_hist = np.array(history.get('hist_alt', []))
            density = np.array(history.get('hist_density', []))
            pressure = np.array(history.get('hist_press_amb', []))
            
            if len(altitude_hist) > 0 and len(density) > 0:
                plot8 = self._create_pyqtgraph_plot(
                    "Atmospheric Conditions",
                    altitude_hist, [density, pressure],
                    ['Density [kg/m³]', 'Pressure [Pa]'],
                    ['darkblue', 'darkgreen']
                )
            else:
                plot8 = self._create_pyqtgraph_placeholder("Atmosphere")
        except Exception as e:
            logger.warning(f"Could not create atmosphere chart: {e}")
            plot8 = self._create_pyqtgraph_placeholder("Atmosphere")
        self._add_pyqtgraph_as_tab(plot8, "Atmosphere")
        
        # Chart 9: Aerodynamic Coefficients
        try:
            times = np.array(history.get('hist_time', []))
            drag_coeff = np.array(history.get('hist_drag_coeff', []))
            lift_coeff = np.array(history.get('hist_lift_coeff', []))
            mach = np.array(history.get('hist_mach', []))
            
            if len(times) > 0:
                plot9 = self._create_pyqtgraph_plot(
                    "Aerodynamic Coefficients",
                    times, [drag_coeff, lift_coeff, mach],
                    ['Cd', 'Cl', 'Mach'],
                    ['brown', 'pink', 'gray']
                )
            else:
                plot9 = self._create_pyqtgraph_placeholder("Aero Coefficients")
        except Exception as e:
            logger.warning(f"Could not create aero coefficients chart: {e}")
            plot9 = self._create_pyqtgraph_placeholder("Aero Coefficients")
        self._add_pyqtgraph_as_tab(plot9, "Aero Coefficients")
        
        # Chart 10: Dynamic Pressure (Q)
        try:
            times = np.array(history.get('hist_time', []))
            density = np.array(history.get('hist_density', []))
            v_norm = np.array(history.get('hist_v_norm', []))
            
            if len(times) > 0 and len(density) > 0 and len(v_norm) > 0:
                q_dynamic = 0.5 * density * v_norm**2
                max_q_idx = np.argmax(q_dynamic)
                
                plot10 = self._create_pyqtgraph_simple_plot(
                    f"Dynamic Pressure (Max-Q: {q_dynamic[max_q_idx]:.0f} Pa @ {times[max_q_idx]:.2f}s)",
                    times, q_dynamic, 'Time [s]', 'Q [Pa]', color='darkred', name='Dynamic Pressure'
                )
                
                # Add vertical line at max-Q
                if HAS_PYQTGRAPH:
                    vr_line = InfiniteLine(pos=times[max_q_idx], angle=90,
                                          pen=mkPen(color=(255, 165, 0), width=1.5,
                                                     style=Qt.PenStyle.DashLine))
                    plot10.addItem(vr_line)
                    # Reuse the legend already created inside
                    # _create_pyqtgraph_simple_plot instead of calling
                    # addLegend() again, which would stack a second legend
                    # item on top of the first.
            else:
                plot10 = self._create_pyqtgraph_placeholder("Dynamic Pressure")
        except Exception as e:
            logger.warning(f"Could not create dynamic pressure chart: {e}")
            plot10 = self._create_pyqtgraph_placeholder("Dynamic Pressure")
        self._add_pyqtgraph_as_tab(plot10, "Dynamic Pressure")
        
        # Chart 11: Thrust-to-Weight Ratio
        try:
            times = np.array(history.get('hist_time', []))
            thrust = np.array(history.get('hist_thrust', []))
            mass = np.array(history.get('hist_mass', []))
            
            if len(times) > 0 and len(thrust) > 0 and len(mass) > 0:
                g0 = 9.80665
                twr = np.where(mass > 0, thrust / (mass * g0), 0)
                
                plot11 = self._create_pyqtgraph_simple_plot(
                    "Thrust-to-Weight Ratio",
                    times, twr, 'Time [s]', 'TWR', color='green', name='TWR'
                )
                
                # Add horizontal line at TWR = 1.0
                if HAS_PYQTGRAPH:
                    hr_line = InfiniteLine(pos=1.0, angle=0, 
                                          pen=mkPen(color=(255, 0, 0), width=1.5,
                                                     style=Qt.PenStyle.DashLine))
                    plot11.addItem(hr_line)
                    # Legend already created inside _create_pyqtgraph_simple_plot;
                    # do not call addLegend() again here.
            else:
                plot11 = self._create_pyqtgraph_placeholder("Thrust/Weight")
        except Exception as e:
            logger.warning(f"Could not create TWR chart: {e}")
            plot11 = self._create_pyqtgraph_placeholder("Thrust/Weight")
        self._add_pyqtgraph_as_tab(plot11, "Thrust/Weight")
        
        # Chart 12: Energy Analysis
        try:
            times = np.array(history.get('hist_time', []))
            mass = np.array(history.get('hist_mass', []))
            v_norm = np.array(history.get('hist_v_norm', []))
            altitude_hist = np.array(history.get('hist_alt', []))
            
            if len(times) > 0 and len(mass) > 0 and len(v_norm) > 0:
                g0 = 9.80665
                ke = 0.5 * mass * v_norm**2
                pe = mass * g0 * np.maximum(altitude_hist, 0)
                total_e = ke + pe
                
                plot12 = self._create_pyqtgraph_plot(
                    "Energy Analysis",
                    times, [ke / 1000, pe / 1000, total_e / 1000],
                    ['Kinetic [kJ]', 'Potential [kJ]', 'Total [kJ]'],
                    ['red', 'blue', 'purple']
                )
            else:
                plot12 = self._create_pyqtgraph_placeholder("Energy")
        except Exception as e:
            logger.warning(f"Could not create energy chart: {e}")
            plot12 = self._create_pyqtgraph_placeholder("Energy")
        self._add_pyqtgraph_as_tab(plot12, "Energy")
        
        # Chart 13: Stability Margin
        try:
            times = np.array(history.get('hist_time', []))
            cm_b = np.array(history.get('hist_cm_b', []))
            cp_b = np.array(history.get('hist_cp_b', []))
            
            if len(times) > 0 and len(cm_b) > 0 and len(cp_b) > 0:
                if cm_b.ndim == 2 and cp_b.ndim == 2:
                    margin = cp_b[:, 0] - cm_b[:, 0]
                else:
                    margin = np.array(history.get('hist_cm2cp_b', []))
                    if margin.ndim == 2:
                        margin = margin[:, 0]
                
                plot13 = self._create_pyqtgraph_simple_plot(
                    "Static Margin",
                    times, margin, 'Time [s]', 'Margin [m]', color='teal', name='Static Margin'
                )
                
                # Add horizontal line at y=0
                if HAS_PYQTGRAPH:
                    hr_line = InfiniteLine(pos=0, angle=0,
                                          pen=mkPen(color=(255, 0, 0, 128), width=1,
                                                     style=Qt.PenStyle.DashLine))
                    plot13.addItem(hr_line)
            else:
                plot13 = self._create_pyqtgraph_placeholder("Stability")
        except Exception as e:
            logger.warning(f"Could not create stability chart: {e}")
            plot13 = self._create_pyqtgraph_placeholder("Stability")
        self._add_pyqtgraph_as_tab(plot13, "Stability")
    
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
        """Add a matplotlib figure as a new tab with zoom/pan toolbar."""
        # Track this Figure so it can be explicitly closed (plt.close) the next
        # time a simulation is loaded - see _close_active_figures(). Figures
        # built directly via Figure() (as the 2D/3D maps do) are not managed by
        # pyplot's state machine and are not garbage-collected just because the
        # tab/canvas that displayed them gets replaced.
        self._track_figure(fig)

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(450)

        toolbar = NavigationToolbar(canvas, container)
        layout.addWidget(toolbar)
        layout.addWidget(canvas, stretch=1)
        container.setLayout(layout)

        self.charts_tab_widget.addTab(container, tab_name)
    
    def _add_pyqtgraph_as_tab(self, plot_widget, tab_name):
        """Add a PyQtGraph PlotWidget as a new tab."""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Apply dark theme to PyQtGraph if available
        if HAS_PYQTGRAPH:
            try:
                # Get current application palette to match theme
                app = QApplication.instance()
                if app:
                    palette = app.palette()
                    bg_color = palette.color(QPalette.ColorRole.Window)
                    text_color = palette.color(QPalette.ColorRole.WindowText)
                    
                    # Set background color to match dark theme
                    plot_widget.setBackground((bg_color.red(), bg_color.green(), bg_color.blue()))
                    
                    # Set text color
                    plot_widget.getAxis('bottom').setTextPen((text_color.red(), text_color.green(), text_color.blue()))
                    plot_widget.getAxis('left').setTextPen((text_color.red(), text_color.green(), text_color.blue()))
                    
                    # Set grid color
                    plot_widget.showGrid(x=True, y=True, alpha=0.3)
                    plot_widget.setMenuEnabled(False)  # Disable context menu for cleaner look
            except Exception as e:
                logger.warning(f"Could not apply theme to PyQtGraph: {e}")
        
        plot_widget.setMinimumHeight(450)
        layout.addWidget(plot_widget, stretch=1)
        container.setLayout(layout)
        
        self.charts_tab_widget.addTab(container, tab_name)
    
    def _color_to_pg(self, color):
        """Convert color to PyQtGraph format (RGB tuple 0-255)."""
        if isinstance(color, str):
            # Common color names mapping
            color_map = {
                'blue': (0, 0, 255), 'red': (255, 0, 0), 'green': (0, 255, 0),
                'cyan': (0, 255, 255), 'purple': (128, 0, 128), 'orange': (255, 165, 0),
                'brown': (165, 42, 42), 'pink': (255, 192, 203), 'gray': (128, 128, 128),
                'darkblue': (0, 0, 139), 'darkgreen': (0, 100, 0), 'teal': (0, 128, 128),
                'limegreen': (50, 205, 50), 'darkred': (139, 0, 0)
            }
            return color_map.get(color.lower(), (200, 200, 200))
        elif isinstance(color, tuple):
            # Assume it's already RGB (0-255 or 0-1)
            if len(color) >= 3:
                # Normalize if 0-1 range
                if all(0 <= c <= 1 for c in color[:3]):
                    return tuple(int(c * 255) for c in color[:3])
                return color[:3]
        return (200, 200, 200)  # Default gray
    
    def _create_pyqtgraph_plot(self, title, x_data, y_data_list, labels, colors_list, 
                               x_label="Time [s]", y_label="Value", use_secondary_axis=False):
        """Create a PyQtGraph plot widget with multiple curves."""
        if not HAS_PYQTGRAPH:
            return self._create_multiline_chart(title, x_data, y_data_list, labels, colors_list)
        
        try:
            plot_widget = PlotWidget(title=title)
            plot_widget.setMouseEnabled(x=True, y=True)
            plot_widget.setMouseTracking(True)
            plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            # Set labels
            plot_widget.setLabel('bottom', x_label)
            plot_widget.setLabel('left', y_label)
            
            if use_secondary_axis and len(y_data_list) > 1:
                # For dual axis, plot first dataset on left, second on right
                view1 = plot_widget.getViewBox()

                # Add legend BEFORE plotting so it reliably picks up curve1
                legend = plot_widget.addLegend()

                # Plot first dataset on primary (left) axis
                curve1 = plot_widget.plot(x_data, y_data_list[0], 
                                        pen=mkPen(color=self._color_to_pg(colors_list[0]), width=2), 
                                        name=labels[0])
                
                # Create right axis and plot second dataset
                axis2 = plot_widget.getAxis('right')
                axis2.show()
                axis2.setLabel(labels[1])
                
                # Create ViewBox linked to right axis
                axis2_view = ViewBox()
                axis2.linkToView(axis2_view)
                plot_widget.scene().addItem(axis2_view)
                axis2_view.setXLink(plot_widget)
                
                # Plot second dataset on right axis
                curve2 = PlotCurveItem(x_data, y_data_list[1], 
                                      pen=mkPen(color=self._color_to_pg(colors_list[1]), width=2))
                axis2_view.addItem(curve2)

                # Keep the right-hand ViewBox geometry (and autorange) in sync with
                # the left one on every resize/zoom/pan. Without this, curve2 only
                # aligns correctly at creation time and drifts as soon as the user
                # zooms, pans, or resizes the window.
                def _update_views(view1=view1, axis2_view=axis2_view):
                    axis2_view.setGeometry(view1.sceneBoundingRect())
                    axis2_view.linkedViewChanged(view1, axis2_view.XAxis)

                view1.sigResized.connect(_update_views)
                _update_views()

                # Keep strong references on the widget itself: axis2_view and the
                # callback must stay alive as long as the plot does, or the resize
                # signal silently stops updating the secondary axis.
                plot_widget._axis2_view = axis2_view
                plot_widget._update_views = _update_views

                # Add second curve to the legend (already created above)
                legend.addItem(curve2, labels[1])
            else:
                # Add legend BEFORE plotting so it reliably picks up all curves
                legend = None
                if len(y_data_list) > 1:
                    legend = plot_widget.addLegend()

                # Plot all datasets on same axis with proper legends
                for i, y_data in enumerate(y_data_list):
                    if len(y_data) > 0:
                        pen = mkPen(color=self._color_to_pg(colors_list[i]), width=2)
                        plot_widget.plot(x_data, y_data, pen=pen, name=labels[i])

                plot_widget._legend = legend
            
            return plot_widget
            
        except Exception as e:
            logger.error(f"Error creating PyQtGraph plot: {e}")
            import traceback
            traceback.print_exc()
            return self._create_multiline_chart(title, x_data, y_data_list, labels, colors_list)
    
    def _create_pyqtgraph_simple_plot(self, title, x_data, y_data, x_label, y_label, color='blue', name=None):
        """Create a simple PyQtGraph plot with single dataset."""
        if not HAS_PYQTGRAPH:
            return self._create_simple_chart(title, x_data, y_data, x_label, y_label)
        
        try:
            plot_widget = PlotWidget(title=title)
            plot_widget.setMouseEnabled(x=True, y=True)
            plot_widget.setLabel('bottom', x_label)
            plot_widget.setLabel('left', y_label)
            plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            pen = mkPen(color=self._color_to_pg(color), width=2)
            # Use provided name or extract from title
            data_name = name if name else title.split(' ')[0] if title else 'Data'

            # Add legend BEFORE plotting so it reliably picks up the curve
            legend = None
            if data_name and data_name != 'Data':
                legend = plot_widget.addLegend()

            plot_widget.plot(x_data, y_data, pen=pen, name=data_name)

            # Stash the legend (may be None) so callers can add more items to it
            # instead of calling addLegend() again and stacking a second legend
            # on top of it.
            plot_widget._legend = legend
            
            return plot_widget
        except Exception as e:
            logger.error(f"Error creating simple PyQtGraph plot: {e}")
            import traceback
            traceback.print_exc()
            return self._create_simple_chart(title, x_data, y_data, x_label, y_label)
    
    def _create_pyqtgraph_placeholder(self, title):
        """Create a placeholder PyQtGraph plot."""
        if not HAS_PYQTGRAPH:
            return self._create_placeholder_chart(title)
        
        try:
            plot_widget = PlotWidget(title=title)
            plot_widget.setMouseEnabled(x=False, y=False)
            
            # Add text item
            from pyqtgraph import TextItem
            text_item = TextItem(text='Data not available\nin current simulation',
                                 color=(150, 150, 150), anchor=(0.5, 0.5))
            text_item.setPos(0.5, 0.5)
            plot_widget.addItem(text_item)
            
            plot_widget.hideAxis('bottom')
            plot_widget.hideAxis('left')
            
            return plot_widget
        except Exception as e:
            logger.error(f"Error creating PyQtGraph placeholder: {e}")
            return self._create_placeholder_chart(title)
    
    def generate_trajectory_maps(self, sim_data, metadata):
        """Generate 2D map (as tab) and 3D trajectory (left panel) from simulation data."""
        try:
            trajectory = sim_data.get('trajectory', [])
            
            if not trajectory:
                logger.warning("No trajectory data for maps")
                return
            
            # Close any matplotlib Figures created for the previous simulation
            # before building new ones. self.charts_tab_widget.clear() (called in
            # generate_performance_charts) destroys the Qt widgets/canvases, but
            # standalone Figure() objects (not created via pyplot) are not
            # garbage-collected automatically just because their canvas widget
            # was destroyed - repeatedly loading simulations otherwise leaks
            # memory (this is especially costly for the 3D map, which also
            # renders an offscreen cartopy texture into its own Figure).
            self._close_active_figures()
            
            # Extract trajectory data
            times = np.array([p.get('time', 0) for p in trajectory])
            altitudes = np.array([p.get('altitude', 0) for p in trajectory])
            ranges = np.array([p.get('range', 0) for p in trajectory])
            
            # Generate 2D trajectory map (added as a tab)
            self._generate_2d_map(ranges, altitudes, metadata)
            
            # Generate 3D flight path (left panel)
            self._generate_3d_flight_path(times, ranges, altitudes, metadata)
            
            logger.info("Trajectory maps generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating maps: {e}")
    
    def _close_active_figures(self):
        """Close and release matplotlib Figures tracked from previous map/chart
        generation. Call this before creating new Figures for a newly loaded
        simulation to prevent unbounded memory growth."""
        figures = getattr(self, '_active_figures', [])
        for fig in figures:
            try:
                plt.close(fig)
            except Exception as e:
                logger.warning(f"Could not close figure: {e}")
        self._active_figures = []
    
    def _track_figure(self, fig):
        """Register a matplotlib Figure so it can be closed on the next refresh."""
        if not hasattr(self, '_active_figures'):
            self._active_figures = []
        self._active_figures.append(fig)
        return fig
    
    def _resolve_launch_coords(self, metadata: dict) -> tuple:
        """Return (lat, lon, azimuth) from metadata, falling back to launch_sites.json."""
        lat = metadata.get(Constants.StateKeys.LAUNCH_LATITUDE)
        lon = metadata.get(Constants.StateKeys.LAUNCH_LONGITUDE)
        az  = metadata.get(Constants.StateKeys.LAUNCH_AZIMUTH)

        # Missing or exactly zero may mean old simulation without coords saved
        if not lat and not lon:
            location_name = metadata.get('location', '')
            if location_name:
                try:
                    sites_path = Path(__file__).resolve().parents[2] / 'data' / 'locations' / 'launch_sites.json'
                    with open(sites_path, encoding='utf-8') as f:
                        sites = json.load(f)
                    site = sites.get(location_name, {})
                    lat = site.get('latitude', 0.0)
                    lon = site.get('longitude', 0.0)
                    if az is None:
                        az = site.get('azimuth', 0.0)
                except Exception as e:
                    logger.warning(f"Could not resolve launch coords from sites JSON: {e}")

        return float(lat or 0.0), float(lon or 0.0), float(az or 0.0)

    def _generate_2d_map(self, ranges, altitudes, metadata):
        """Generate a geographic 2D trajectory map using cartopy and add it as a tab."""
        if not HAS_CARTOPY:
            self._generate_2d_matplotlib_map(ranges, altitudes)
            return

        try:
            import math

            launch_lat, launch_lon, _ = self._resolve_launch_coords(metadata)
            max_range_m = float(ranges.max()) if len(ranges) > 0 else 0.0
            max_alt_km = float(altitudes.max()) / 1000.0 if len(altitudes) > 0 else 0.0
            max_range_km = max_range_m / 1000.0

            # Use launch azimuth from metadata (default 0° = North)
            _, _, azimuth_deg = self._resolve_launch_coords(metadata)
            azimuth_rad = math.radians(azimuth_deg)

            # Compute approximate landing coords from range + azimuth
            cos_lat = math.cos(math.radians(launch_lat)) or 1e-6
            delta_lat = (max_range_km / 111.32) * math.cos(azimuth_rad)
            delta_lon = (max_range_km / (111.32 * cos_lat)) * math.sin(azimuth_rad)
            landing_lat = launch_lat + delta_lat
            landing_lon = launch_lon + delta_lon
            apogee_lat = launch_lat + delta_lat / 2
            apogee_lon = launch_lon + delta_lon / 2

            # Map extent: pad around launch + landing
            pad_km = max(max_range_km * 1.5, 10.0)
            pad_lat = pad_km / 111.32
            pad_lon = pad_km / (111.32 * cos_lat)
            extent = [
                min(launch_lon, landing_lon) - pad_lon,
                max(launch_lon, landing_lon) + pad_lon,
                min(launch_lat, landing_lat) - pad_lat,
                max(launch_lat, landing_lat) + pad_lat,
            ]

            # Choose natural-earth resolution based on extent size
            res = '10m' if pad_km < 200 else '50m' if pad_km < 1000 else '110m'

            fig = Figure(figsize=(8, 6))
            ax: Any = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
            ax.set_extent(extent, crs=ccrs.PlateCarree())

            ax.add_feature(cfeature.NaturalEarthFeature(
                'physical', 'land', res, facecolor='#e6dfa8', edgecolor='none'))
            ax.add_feature(cfeature.NaturalEarthFeature(
                'physical', 'ocean', res, facecolor='#a8d0e8', edgecolor='none'))
            ax.add_feature(cfeature.NaturalEarthFeature(
                'cultural', 'admin_0_countries', res,
                facecolor='none', edgecolor='#555555', linewidth=0.5))
            ax.add_feature(cfeature.NaturalEarthFeature(
                'physical', 'coastline', res,
                facecolor='none', edgecolor='#333333', linewidth=0.7))

            # Trajectory line (launch → apogee midpoint → landing)
            ax.plot(
                [launch_lon, apogee_lon, landing_lon],
                [launch_lat, apogee_lat, landing_lat],
                'b-', linewidth=2, transform=ccrs.Geodetic(),
                label='Trajectory', zorder=5
            )

            # Key markers
            ax.scatter([launch_lon], [launch_lat], color='red', s=120, marker='*',
                       transform=ccrs.PlateCarree(), zorder=6, label='Launch')
            ax.scatter([landing_lon], [landing_lat], color='green', s=100, marker='X',
                       transform=ccrs.PlateCarree(), zorder=6, label='Landing')
            ax.scatter([apogee_lon], [apogee_lat], color='orange', s=80, marker='o',
                       transform=ccrs.PlateCarree(), zorder=6,
                       label=f'Apogee {max_alt_km:.1f} km')

            gl = ax.gridlines(draw_labels=True, linewidth=0.5,
                              color='gray', alpha=0.5, linestyle='--')
            gl.top_labels = False
            gl.right_labels = False

            ax.set_title(
                f'2D Trajectory Map\n'
                f'Launch: ({launch_lat:.4f}°, {launch_lon:.4f}°)  '
                f'Range: {max_range_km:.2f} km',
                fontsize=10
            )
            ax.legend(loc='upper right', fontsize=8)
            fig.tight_layout()

            self._add_chart_as_tab(fig, "2D Trajectory Map")

        except Exception as e:
            logger.error(f"Error generating 2D map: {e}")
            self._generate_2d_matplotlib_map(ranges, altitudes)
    
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
    
    def _generate_3d_flight_path(self, times, ranges, altitudes, metadata):
        """Generate a 3D flight path with cartopy map texture on the ground plane."""
        try:
            import math
            import io
            import matplotlib.image as mpimg
            from matplotlib.backends.backend_agg import FigureCanvasAgg

            launch_lat, launch_lon, azimuth_deg = self._resolve_launch_coords(metadata)
            azimuth_rad = math.radians(azimuth_deg)
            cos_lat = math.cos(math.radians(launch_lat)) or 1e-6

            ranges_km = ranges / 1000.0
            altitudes_km = altitudes / 1000.0
            max_range_km = float(ranges_km.max()) if len(ranges_km) > 0 else 1.0

            # Convert range -> East/North km offsets from launch
            # azimuth: degrees from North, clockwise
            x_km = ranges_km * math.sin(azimuth_rad)   # East (+)
            y_km = ranges_km * math.cos(azimuth_rad)   # North (+)

            # Geographic extent for ground map
            pad_km = max(max_range_km * 1.5, 10.0)
            pad_lat = pad_km / 111.32
            pad_lon = pad_km / (111.32 * cos_lat)
            extent = [
                launch_lon - pad_lon, launch_lon + pad_lon,
                launch_lat - pad_lat, launch_lat + pad_lat,
            ]

            # km offsets of extent edges from launch origin
            x_lo = -pad_lon * 111.32 * cos_lat
            x_hi =  pad_lon * 111.32 * cos_lat
            y_lo = -pad_lat * 111.32
            y_hi =  pad_lat * 111.32

            # ── Render cartopy map to RGBA numpy image ───────────────────
            ground_img = None
            if HAS_CARTOPY:
                try:
                    res = '10m' if pad_km < 200 else '50m' if pad_km < 1000 else '110m'
                    IMGPX = 120
                    map_fig = Figure(figsize=(IMGPX / 72, IMGPX / 72), dpi=72)
                    FigureCanvasAgg(map_fig)  # attach agg backend
                    map_ax: Any = map_fig.add_subplot(
                        1, 1, 1, projection=ccrs.PlateCarree())
                    map_ax.set_extent(extent, crs=ccrs.PlateCarree())
                    map_ax.add_feature(cfeature.NaturalEarthFeature(
                        'physical', 'land', res,
                        facecolor='#c8b97a', edgecolor='none'))
                    map_ax.add_feature(cfeature.NaturalEarthFeature(
                        'physical', 'ocean', res,
                        facecolor='#5b9ec9', edgecolor='none'))
                    map_ax.add_feature(cfeature.NaturalEarthFeature(
                        'cultural', 'admin_0_countries', res,
                        facecolor='none', edgecolor='#666666', linewidth=0.5))
                    map_ax.add_feature(cfeature.NaturalEarthFeature(
                        'physical', 'coastline', res,
                        facecolor='none', edgecolor='#333333', linewidth=0.7))
                    map_fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
                    buf = io.BytesIO()
                    map_fig.savefig(buf, format='png', dpi=72, pad_inches=0)
                    buf.seek(0)
                    ground_img = mpimg.imread(buf)   # (H, W, 4) RGBA float 0-1
                except Exception as img_err:
                    logger.warning(f"Cartopy ground texture failed: {img_err}")
                    ground_img = None
                finally:
                    # This Figure is only an offscreen render target for the
                    # ground texture - it is never added as a tab, so it must
                    # be closed here explicitly or it leaks on every reload.
                    if 'map_fig' in locals():
                        plt.close(map_fig)

            # ── Build 3D figure ──────────────────────────────────────────
            fig = Figure(figsize=(9, 7))
            ax3d = fig.add_subplot(111, projection='3d')

            if ground_img is not None:
                H_img, W_img = ground_img.shape[:2]
                xg = np.linspace(x_lo, x_hi, W_img)
                # Row 0 of image = North (y_hi); last row = South (y_lo)
                yg = np.linspace(y_hi, y_lo, H_img)
                XG, YG = np.meshgrid(xg, yg)
                ZG = np.zeros_like(XG)
                ax3d.plot_surface(
                    XG, YG, ZG,
                    facecolors=ground_img,
                    rstride=1, cstride=1,
                    shade=False, zorder=1, alpha=1.0,
                )
            else:
                # Plain coloured ground fallback
                gx = np.array([[x_lo, x_hi], [x_lo, x_hi]])
                gy = np.array([[y_lo, y_lo], [y_hi, y_hi]])
                gz = np.zeros_like(gx)
                ax3d.plot_surface(gx, gy, gz, color='#c8b97a', alpha=0.6)

            # 3D trajectory
            ax3d.plot(x_km, y_km, altitudes_km,
                      color='royalblue', linewidth=2.5,
                      label='Flight Path', zorder=5)

            # Shadow projection on ground
            ax3d.plot(x_km, y_km, np.zeros_like(altitudes_km),
                      color='royalblue', linestyle='--',
                      linewidth=1.0, alpha=0.35, zorder=2)

            # Markers
            ax3d.scatter([x_km[0]], [y_km[0]], [0], # type: ignore
                         color='red', s=120, marker='*',
                         label='Launch', zorder=6, depthshade=False)
            ax3d.scatter([x_km[-1]], [y_km[-1]], [0], # type: ignore
                         color='limegreen', s=100, marker='X',
                         label='Landing', zorder=6, depthshade=False)

            apogee_idx = int(np.argmax(altitudes_km))
            ax3d.scatter(
                [x_km[apogee_idx]], [y_km[apogee_idx]], [altitudes_km[apogee_idx]], # type: ignore
                color='orange', s=100, marker='o',
                label=f'Apogee {altitudes_km[apogee_idx]:.1f} km',
                zorder=6, depthshade=False,
            )

            # Vertical dashed line at apogee
            ax3d.plot(
                [x_km[apogee_idx], x_km[apogee_idx]],
                [y_km[apogee_idx], y_km[apogee_idx]],
                [0, altitudes_km[apogee_idx]],
                color='orange', linestyle=':', linewidth=1.2,
                alpha=0.6, zorder=3,
            )

            ax3d.set_xlabel('East [km]', labelpad=6)
            ax3d.set_ylabel('North [km]', labelpad=6)
            ax3d.set_zlabel('Altitude [km]', labelpad=6)
            ax3d.set_title(
                f'3D Flight Path  |  Az: {azimuth_deg:.1f}°  |  '
                f'Range: {max_range_km:.2f} km',
                fontsize=10,
            )
            ax3d.legend(loc='upper left', fontsize=8)
            fig.tight_layout()

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

