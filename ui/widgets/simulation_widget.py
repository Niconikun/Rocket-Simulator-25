"""Simulation Widget - Main simulation control and execution interface."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QDoubleSpinBox,
    QPushButton, QProgressBar, QDateEdit, QTimeEdit, QComboBox, QGroupBox,
    QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QDate, QTime
from datetime import datetime
from models.app_state import ApplicationState
from workers.simulation_worker import SimulationWorker
from src.utils.simulation_manager import SimulationManager
import logging

logger = logging.getLogger(__name__)


class SimulationWidget(QWidget):
    """
    Simulation control panel for running rocket flight simulations.
    
    Replaces pages/01_simulation.py
    Allows users to:
    - Configure simulation parameters (runtime, timestep)
    - Set launch date and time
    - Select rocket and location
    - Execute simulation with progress tracking
    - View results
    """
    
    simulation_saved = pyqtSignal(str)  # Emits sim_id when a simulation is saved
    
    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
        self.simulation_manager = SimulationManager()
        self.simulation_worker = None
        self.simulation_thread = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the simulation widget UI."""
        main_layout = QVBoxLayout()
        
        # ===== PARAMETERS GROUP =====
        params_group = QGroupBox("Simulation Parameters")
        params_layout = QFormLayout()
        
        # Runtime
        self.runtime_spinbox = QSpinBox()
        self.runtime_spinbox.setRange(1, 10000)
        self.runtime_spinbox.setValue(self.state.get('sim_runtime', 600))
        self.runtime_spinbox.setSuffix(" seconds")
        self.runtime_spinbox.valueChanged.connect(
            lambda v: self.state.set('sim_runtime', v)
        )
        params_layout.addRow("Simulation Runtime:", self.runtime_spinbox)
        
        # Timestep
        self.timestep_spinbox = QDoubleSpinBox()
        self.timestep_spinbox.setRange(0.0001, 1.0)
        self.timestep_spinbox.setValue(self.state.get('sim_time_step', 0.001))
        self.timestep_spinbox.setSingleStep(0.001)
        self.timestep_spinbox.setDecimals(4)
        self.timestep_spinbox.setSuffix(" s")
        self.timestep_spinbox.valueChanged.connect(
            lambda v: self.state.set('sim_time_step', v)
        )
        params_layout.addRow("Time Step:", self.timestep_spinbox)
        
        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)
        
        # ===== DATE/TIME GROUP =====
        datetime_group = QGroupBox("Launch Date & Time")
        datetime_layout = QFormLayout()
        
        # Date
        self.date_edit = QDateEdit()
        current_date = self.state.get('sim_date')
        self.date_edit.setDate(QDate(current_date.year, current_date.month, current_date.day))
        self.date_edit.dateChanged.connect(
            lambda d: self.state.set('sim_date', d.toPyDate())
        )
        datetime_layout.addRow("Date:", self.date_edit)
        
        # Time
        self.time_edit = QTimeEdit()
        current_time = self.state.get('sim_time')
        self.time_edit.setTime(QTime(current_time.hour, current_time.minute))
        self.time_edit.timeChanged.connect(
            lambda t: self.state.set('sim_time', t.toPyTime())
        )
        datetime_layout.addRow("Time:", self.time_edit)
        
        # Timezone
        self.timezone_combo = QComboBox()
        timezones = ["UTC", "UTC-5", "UTC-4", "UTC-3", "UTC-2", "UTC-1",
                     "UTC+1", "UTC+2", "UTC+3", "UTC+5:30", "UTC+8", "UTC+9"]
        self.timezone_combo.addItems(timezones)
        self.timezone_combo.setCurrentText(self.state.get('sim_timezone', 'UTC'))
        self.timezone_combo.currentTextChanged.connect(
            lambda v: self.state.set('sim_timezone', v)
        )
        datetime_layout.addRow("Timezone:", self.timezone_combo)
        
        datetime_group.setLayout(datetime_layout)
        main_layout.addWidget(datetime_group)
        
        # ===== ENVIRONMENT GROUP =====
        env_group = QGroupBox("Environmental Conditions")
        env_layout = QFormLayout()
        
        # Temperature
        self.temp_spinbox = QDoubleSpinBox()
        self.temp_spinbox.setRange(-40, 60)
        self.temp_spinbox.setValue(self.state.get('average_temperature', 20.0))
        self.temp_spinbox.setSuffix(" °C")
        self.temp_spinbox.valueChanged.connect(
            lambda v: self.state.set('average_temperature', v)
        )
        env_layout.addRow("Temperature:", self.temp_spinbox)
        
        # Pressure
        self.pressure_spinbox = QDoubleSpinBox()
        self.pressure_spinbox.setRange(50000, 110000)
        self.pressure_spinbox.setValue(self.state.get('average_pressure', 101325.0))
        self.pressure_spinbox.setSuffix(" Pa")
        self.pressure_spinbox.valueChanged.connect(
            lambda v: self.state.set('average_pressure', v)
        )
        env_layout.addRow("Pressure:", self.pressure_spinbox)
        
        # Elevation
        self.elevation_spinbox = QDoubleSpinBox()
        self.elevation_spinbox.setRange(-500, 5000)
        self.elevation_spinbox.setValue(self.state.get('launch_elevation', 60.0))
        self.elevation_spinbox.setSuffix(" m")
        self.elevation_spinbox.valueChanged.connect(
            lambda v: self.state.set('launch_elevation', v)
        )
        env_layout.addRow("Elevation:", self.elevation_spinbox)
        
        env_group.setLayout(env_layout)
        main_layout.addWidget(env_group)
        
        # ===== LAUNCH PARAMETERS GROUP =====
        launch_group = QGroupBox("Launch Parameters")
        launch_layout = QFormLayout()
        
        # Launch elevation angle (rod angle)
        self.launch_angle_spinbox = QDoubleSpinBox()
        self.launch_angle_spinbox.setRange(0, 90)
        self.launch_angle_spinbox.setValue(self.state.get('launch_elevation_angle', 85.0))
        self.launch_angle_spinbox.setSingleStep(1.0)
        self.launch_angle_spinbox.setDecimals(1)
        self.launch_angle_spinbox.setSuffix(" °")
        self.launch_angle_spinbox.valueChanged.connect(
            lambda v: self.state.set('launch_elevation_angle', v)
        )
        launch_layout.addRow("Launch Angle:", self.launch_angle_spinbox)
        
        # Launch azimuth
        self.launch_azimuth_spinbox = QDoubleSpinBox()
        self.launch_azimuth_spinbox.setRange(0, 360)
        self.launch_azimuth_spinbox.setValue(self.state.get('launch_azimuth', 0.0))
        self.launch_azimuth_spinbox.setSingleStep(1.0)
        self.launch_azimuth_spinbox.setDecimals(1)
        self.launch_azimuth_spinbox.setSuffix(" °")
        self.launch_azimuth_spinbox.valueChanged.connect(
            lambda v: self.state.set('launch_azimuth', v)
        )
        launch_layout.addRow("Launch Azimuth:", self.launch_azimuth_spinbox)
        
        # Launch roll
        self.launch_roll_spinbox = QDoubleSpinBox()
        self.launch_roll_spinbox.setRange(-180, 180)
        self.launch_roll_spinbox.setValue(self.state.get('launch_roll', 0.0))
        self.launch_roll_spinbox.setSingleStep(1.0)
        self.launch_roll_spinbox.setDecimals(1)
        self.launch_roll_spinbox.setSuffix(" °")
        self.launch_roll_spinbox.valueChanged.connect(
            lambda v: self.state.set('launch_roll', v)
        )
        launch_layout.addRow("Launch Roll:", self.launch_roll_spinbox)
        
        launch_group.setLayout(launch_layout)
        main_layout.addWidget(launch_group)
        
        # ===== SIMULATION CONTROL =====
        control_group = QGroupBox("Simulation Control")
        control_layout = QVBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        control_layout.addWidget(QLabel("Progress:"))
        control_layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("▶️ Run Simulation")
        self.run_button.clicked.connect(self.run_simulation)
        button_layout.addWidget(self.run_button)
        
        self.pause_button = QPushButton("⏸️ Pause")
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)
        
        self.reset_button = QPushButton("🔄 Reset")
        self.reset_button.clicked.connect(self.reset_simulation)
        button_layout.addWidget(self.reset_button)
        
        control_layout.addLayout(button_layout)
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
    
    def run_simulation(self):
        """Start the simulation in a background thread."""
        logger.info("Starting simulation...")
        self.state.set('simulation_running', True)
        self.run_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        
        # Create worker thread
        self.simulation_thread = QThread()
        self.simulation_worker = SimulationWorker(self.state)
        self.simulation_worker.moveToThread(self.simulation_thread)
        
        # Connect signals
        self.simulation_worker.progress.connect(self.on_simulation_progress)
        self.simulation_worker.finished.connect(self.on_simulation_finished)
        self.simulation_worker.error.connect(self.on_simulation_error)
        self.simulation_thread.started.connect(self.simulation_worker.run)
        
        self.simulation_thread.start()
    
    def on_simulation_progress(self, progress: float):
        """Update progress bar."""
        self.progress_bar.setValue(int(progress * 100))
    
    def on_simulation_finished(self, results):
        """Handle simulation completion and save results."""
        self.state.set('simulation_results', results)
        self.state.set('simulation_running', False)
        self.run_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        if self.simulation_thread is not None:
            self.simulation_thread.quit()
            self.simulation_thread.wait()
        
        # Save simulation results automatically
        try:
            # Prepare metadata from state
            metadata = {
                'rocket': self.state.get('selected_rocket', 'Unknown'),
                'location': self.state.get('sim_location', 'Unknown'),
                'temperature': self.state.get('average_temperature', 20.0),
                'pressure': self.state.get('average_pressure', 101325.0),
                'launch_date': str(self.state.get('sim_date', '')),
                'launch_time': str(self.state.get('sim_time', '')),
                'timestamp': datetime.now().isoformat()
            }
            
            # Validate results structure before processing
            if not results or not isinstance(results, dict):
                raise ValueError("Invalid simulation results: expected dict with metrics")
            
            # Extract key metrics from results - they are nested in 'metrics' dict
            metrics = results.get('metrics', {})
            if not metrics or not isinstance(metrics, dict):
                raise ValueError("Missing metrics in simulation results")
            
            metadata['max_altitude'] = metrics.get('max_altitude', 0) / 1000.0  # Convert to km
            metadata['max_velocity'] = metrics.get('max_velocity', 0)
            metadata['max_range'] = metrics.get('max_range', 0) / 1000.0  # Convert to km
            metadata['flight_duration'] = metrics.get('flight_duration', 0)
            metadata['max_mach'] = metrics.get('max_mach', 0)
            metadata['max_accel_g'] = metrics.get('max_accel_g', 0)
            
            # Save to persistent storage
            sim_id = self.simulation_manager.save_simulation(results, metadata)
            
            # Notify other widgets that a new simulation was saved
            if sim_id:
                self.simulation_saved.emit(sim_id)
            
            QMessageBox.information(
                self, "Success",
                f"Simulation completed successfully!\n\n"
                f"Results saved with ID:\n{sim_id}\n\n"
                f"You can view them in the Dashboard."
            )
            logger.info(f"Simulation saved with ID: {sim_id}")
        except Exception as e:
            logger.error(f"Error saving simulation: {e}")
            QMessageBox.warning(
                self, "Warning",
                f"Simulation completed but failed to save results:\n{str(e)}"
            )
    
    def on_simulation_error(self, error_msg: str):
        """Handle simulation errors."""
        self.state.set('simulation_error', error_msg)
        self.state.set('simulation_running', False)
        self.run_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        if self.simulation_thread is not None:
            self.simulation_thread.quit()
            self.simulation_thread.wait()
        QMessageBox.critical(self, "Simulation Error", f"Error: {error_msg}")
        logger.error(f"Simulation error: {error_msg}")
    
    def reset_simulation(self):
        """Reset simulation parameters to defaults."""
        # Reset UI elements
        self.progress_bar.setValue(0)
        self.runtime_spinbox.setValue(600)
        self.timestep_spinbox.setValue(0.001)
        self.temp_spinbox.setValue(20.0)
        self.pressure_spinbox.setValue(101325.0)
        self.elevation_spinbox.setValue(60.0)
        self.launch_angle_spinbox.setValue(85.0)
        self.launch_azimuth_spinbox.setValue(0.0)
        self.launch_roll_spinbox.setValue(0.0)
        self.timezone_combo.setCurrentText('UTC')
        
        # Reset state
        self.state.set('simulation_results', None)
        self.state.set('simulation_error', None)
        self.state.set('simulation_running', False)
        
        logger.info("Simulation parameters reset to defaults")
