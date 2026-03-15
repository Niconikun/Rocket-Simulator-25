"""Dashboard Widget - Simulation results visualization."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
    QGridLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QMessageBox, QFileDialog
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
from datetime import datetime

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
        
        # ===== CHARTS PLACEHOLDER =====
        charts_group = QGroupBox("Flight Profiles")
        charts_layout = QVBoxLayout()
        
        chart_label = QLabel("Charts will be displayed here\n(Altitude vs Time, Velocity vs Time, etc.)")
        chart_label.setStyleSheet("color: gray; padding: 40px;")
        charts_layout.addWidget(chart_label)
        
        charts_group.setLayout(charts_layout)
        main_layout.addWidget(charts_group)
        
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

