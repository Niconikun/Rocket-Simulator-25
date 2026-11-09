"""Simulation Widget - Main simulation control and execution interface."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QDoubleSpinBox,
    QPushButton, QProgressBar, QDateEdit, QTimeEdit, QComboBox, QGroupBox,
    QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTime
from datetime import datetime
from models.app_state import ApplicationState
from workers.simulation_worker import SimulationWorker
from src.utils.simulation_manager import SimulationManager
import logging
from ui.widgets import BaseWidget
from src.models.state import StateProvider
from src.config import Constants
from src.config.translations import tr
from typing import Optional

logger = logging.getLogger(__name__)

from src.utils.event_bus import EventType, publish

class SimulationWidget(BaseWidget):
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
    status_message = pyqtSignal(str)    # Emits short UI status updates
    def __init__(self, state: Optional[StateProvider] = None):
        """
        Initialize the simulation widget.
        
        Args:
            state: Optional StateProvider instance. If None, uses ApplicationState singleton.
        """
        super().__init__(state=state)
        self.simulation_manager = SimulationManager()
        self.simulation_worker = None
        self.simulation_paused = False
        self.init_ui()
    
    def init_ui(self):
        """Initialize the simulation widget UI."""
        main_layout = QVBoxLayout()
        
        # ===== PARAMETERS GROUP =====
        params_group = QGroupBox(tr("Simulation Parameters"))
        params_layout = QFormLayout()
        
        # Runtime
        self.runtime_spinbox = QSpinBox()
        self.runtime_spinbox.setRange(Constants.Simulation.MIN_RUNTIME, Constants.Simulation.MAX_RUNTIME)
        self.runtime_spinbox.setValue(self.state.get(Constants.StateKeys.SIM_RUNTIME, Constants.Simulation.DEFAULT_RUNTIME))
        self.runtime_spinbox.setSuffix(tr(" seconds"))
        self.runtime_spinbox.valueChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.SIM_RUNTIME, v)
        )
        params_layout.addRow(tr("Simulation Runtime:"), self.runtime_spinbox)
        
        # Timestep
        self.timestep_spinbox = QDoubleSpinBox()
        self.timestep_spinbox.setRange(Constants.Simulation.MIN_TIMESTEP, Constants.Simulation.MAX_TIMESTEP)
        self.timestep_spinbox.setValue(self.state.get(Constants.StateKeys.SIM_TIME_STEP, Constants.Simulation.DEFAULT_TIMESTEP))
        self.timestep_spinbox.setSingleStep(0.001)
        self.timestep_spinbox.setDecimals(4)
        self.timestep_spinbox.setSuffix(tr(" s"))
        self.timestep_spinbox.valueChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.SIM_TIME_STEP, v)
        )
        params_layout.addRow(tr("Time Step:"), self.timestep_spinbox)
        
        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)
        
        # ===== DATE/TIME GROUP =====
        datetime_group = QGroupBox(tr("Launch Date & Time"))
        datetime_layout = QFormLayout()
        
        # Date
        self.date_edit = QDateEdit()
        current_date = self.state.get(Constants.StateKeys.SIM_DATE)
        self.date_edit.setDate(QDate(current_date.year, current_date.month, current_date.day))
        self.date_edit.dateChanged.connect(
            lambda d: self.state.set(Constants.StateKeys.SIM_DATE, d.toPyDate())
        )
        datetime_layout.addRow(tr("Date:"), self.date_edit)
        
        # Time
        self.time_edit = QTimeEdit()
        current_time = self.state.get(Constants.StateKeys.SIM_TIME)
        self.time_edit.setTime(QTime(current_time.hour, current_time.minute))
        self.time_edit.timeChanged.connect(
            lambda t: self.state.set(Constants.StateKeys.SIM_TIME, t.toPyTime())
        )
        datetime_layout.addRow(tr("Time:"), self.time_edit)
        
        # Timezone
        self.timezone_combo = QComboBox()
        timezones = ["UTC", "UTC-5", "UTC-4", "UTC-3", "UTC-2", "UTC-1",
                     "UTC+1", "UTC+2", "UTC+3", "UTC+5:30", "UTC+8", "UTC+9"]
        self.timezone_combo.addItems(timezones)
        self.timezone_combo.setCurrentText(self.state.get(Constants.StateKeys.SIM_TIMEZONE, 'UTC'))
        self.timezone_combo.currentTextChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.SIM_TIMEZONE, v)
        )
        datetime_layout.addRow(tr("Timezone:"), self.timezone_combo)
        
        datetime_group.setLayout(datetime_layout)
        main_layout.addWidget(datetime_group)
        
        # ===== ENVIRONMENT GROUP =====
        env_group = QGroupBox(tr("Environmental Conditions"))
        env_layout = QFormLayout()
        
        # Temperature
        self.temp_spinbox = QDoubleSpinBox()
        self.temp_spinbox.setRange(Constants.Environmental.MIN_TEMPERATURE, Constants.Environmental.MAX_TEMPERATURE)
        self.temp_spinbox.setValue(self.state.get(Constants.StateKeys.AVERAGE_TEMPERATURE, Constants.Environmental.DEFAULT_TEMPERATURE))
        self.temp_spinbox.setSuffix(tr(" °C"))
        self.temp_spinbox.valueChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.AVERAGE_TEMPERATURE, v)
        )
        env_layout.addRow(tr("Temperature:"), self.temp_spinbox)
        
        # Pressure
        self.pressure_spinbox = QDoubleSpinBox()
        self.pressure_spinbox.setRange(Constants.Environmental.MIN_PRESSURE, Constants.Environmental.MAX_PRESSURE)
        self.pressure_spinbox.setValue(self.state.get(Constants.StateKeys.AVERAGE_PRESSURE, Constants.Environmental.DEFAULT_PRESSURE))
        self.pressure_spinbox.setSuffix(tr(" Pa"))
        self.pressure_spinbox.valueChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.AVERAGE_PRESSURE, v)
        )
        env_layout.addRow(tr("Pressure:"), self.pressure_spinbox)
        
        # Elevation
        self.elevation_spinbox = QDoubleSpinBox()
        self.elevation_spinbox.setRange(Constants.Environmental.MIN_ELEVATION, Constants.Environmental.MAX_ELEVATION)
        self.elevation_spinbox.setValue(self.state.get(Constants.StateKeys.LAUNCH_ELEVATION, Constants.Environmental.DEFAULT_ELEVATION))
        self.elevation_spinbox.setSuffix(tr(" m"))
        self.elevation_spinbox.valueChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.LAUNCH_ELEVATION, v)
        )
        env_layout.addRow(tr("Elevation:"), self.elevation_spinbox)
        
        env_group.setLayout(env_layout)
        main_layout.addWidget(env_group)
        
        # ===== LAUNCH PARAMETERS GROUP =====
        launch_group = QGroupBox(tr("Launch Parameters"))
        launch_layout = QFormLayout()
        
        # Launch elevation angle (rod angle)
        self.launch_angle_spinbox = QDoubleSpinBox()
        self.launch_angle_spinbox.setRange(Constants.Simulation.MIN_LAUNCH_ANGLE, Constants.Simulation.MAX_LAUNCH_ANGLE)
        self.launch_angle_spinbox.setValue(self.state.get(Constants.StateKeys.LAUNCH_ELEVATION_ANGLE, Constants.Simulation.DEFAULT_LAUNCH_ANGLE))
        self.launch_angle_spinbox.setSingleStep(1.0)
        self.launch_angle_spinbox.setDecimals(1)
        self.launch_angle_spinbox.setSuffix(tr(" °"))
        self.launch_angle_spinbox.valueChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.LAUNCH_ELEVATION_ANGLE, v)
        )
        launch_layout.addRow(tr("Launch Angle:"), self.launch_angle_spinbox)
        
        # Launch azimuth
        self.launch_azimuth_spinbox = QDoubleSpinBox()
        self.launch_azimuth_spinbox.setRange(Constants.Simulation.MIN_LAUNCH_AZIMUTH, Constants.Simulation.MAX_LAUNCH_AZIMUTH)
        self.launch_azimuth_spinbox.setValue(self.state.get(Constants.StateKeys.LAUNCH_AZIMUTH, Constants.Simulation.DEFAULT_LAUNCH_AZIMUTH))
        self.launch_azimuth_spinbox.setSingleStep(1.0)
        self.launch_azimuth_spinbox.setDecimals(1)
        self.launch_azimuth_spinbox.setSuffix(tr(" °"))
        self.launch_azimuth_spinbox.valueChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.LAUNCH_AZIMUTH, v)
        )
        launch_layout.addRow(tr("Launch Azimuth:"), self.launch_azimuth_spinbox)
        
        # Launch roll
        self.launch_roll_spinbox = QDoubleSpinBox()
        self.launch_roll_spinbox.setRange(Constants.Simulation.MIN_LAUNCH_ROLL, Constants.Simulation.MAX_LAUNCH_ROLL)
        self.launch_roll_spinbox.setValue(self.state.get(Constants.StateKeys.LAUNCH_ROLL, Constants.Simulation.DEFAULT_LAUNCH_ROLL))
        self.launch_roll_spinbox.setSingleStep(1.0)
        self.launch_roll_spinbox.setDecimals(1)
        self.launch_roll_spinbox.setSuffix(tr(" °"))
        self.launch_roll_spinbox.valueChanged.connect(
            lambda v: self.state.set(Constants.StateKeys.LAUNCH_ROLL, v)
        )
        launch_layout.addRow(tr("Launch Roll:"), self.launch_roll_spinbox)
        
        launch_group.setLayout(launch_layout)
        main_layout.addWidget(launch_group)
        
        # ===== SIMULATION CONTROL =====
        control_group = QGroupBox(tr("Simulation Control"))
        control_layout = QVBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        control_layout.addWidget(QLabel(tr("Progress:")))
        control_layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton(tr("▶️ Run Simulation"))
        self.run_button.setShortcut("F5")
        self.run_button.clicked.connect(self.run_simulation)
        button_layout.addWidget(self.run_button)
        
        self.pause_button = QPushButton(tr("⏸️ Pause"))
        self.pause_button.setShortcut("F6")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)
        button_layout.addWidget(self.pause_button)

        self.stop_button = QPushButton(tr("⏹️ Stop"))
        self.stop_button.setShortcut("F7")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_simulation)
        button_layout.addWidget(self.stop_button)
        
        self.reset_button = QPushButton(tr("🔄 Reset"))
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
        if self.simulation_worker is not None and self.simulation_worker.isRunning():
            QMessageBox.information(self, tr("Simulation Running"), tr("A simulation is already running."))
            return

        self.state.set(Constants.StateKeys.SIMULATION_RUNNING, True)
        self.status_message.emit(tr("Simulation started"))
        
        # Publish event via event bus
        publish(EventType.SIMULATION_STARTED, {"timestamp": datetime.now().isoformat()})
        
        self.run_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.pause_button.setText("⏸️ Pause")
        self.simulation_paused = False
        
        # SimulationWorker already inherits QThread; run it directly.
        self.simulation_worker = SimulationWorker(self.state)
        
        # Connect signals
        self.simulation_worker.progress.connect(self.on_simulation_progress)
        self.simulation_worker.finished.connect(self.on_simulation_finished)
        self.simulation_worker.error.connect(self.on_simulation_error)
        self.simulation_worker.start()
    
    def on_simulation_progress(self, progress: float):
        """Update progress bar."""
        self.progress_bar.setValue(int(progress * 100))
    
    def on_simulation_finished(self, results):
        """Handle simulation completion and save results."""
        self.state.set(Constants.StateKeys.SIMULATION_RESULTS, results)
        self.state.set(Constants.StateKeys.SIMULATION_RUNNING, False)
        self._reset_simulation_controls()
        
        # Publish event via event bus
        publish(EventType.SIMULATION_COMPLETED, {"results": results, "timestamp": datetime.now().isoformat()})
        
        # Save simulation results automatically
        try:
            # Prepare metadata from state
            metadata = {
                'rocket': self.state.get(Constants.StateKeys.SELECTED_ROCKET, 'Unknown'),
                'location': self.state.get(Constants.StateKeys.SIM_LOCATION, 'Unknown'),
                'temperature': self.state.get(Constants.StateKeys.AVERAGE_TEMPERATURE, 20.0),
                'pressure': self.state.get(Constants.StateKeys.AVERAGE_PRESSURE, 101325.0),
                'launch_date': str(self.state.get(Constants.StateKeys.SIM_DATE, '')),
                'launch_time': str(self.state.get(Constants.StateKeys.SIM_TIME, '')),
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

            # Save launch coordinates and azimuth for map rendering
            metadata[Constants.StateKeys.LAUNCH_LATITUDE] = self.state.get(Constants.StateKeys.LAUNCH_LATITUDE, 0.0)
            metadata[Constants.StateKeys.LAUNCH_LONGITUDE] = self.state.get(Constants.StateKeys.LAUNCH_LONGITUDE, 0.0)
            metadata[Constants.StateKeys.LAUNCH_AZIMUTH] = self.state.get(Constants.StateKeys.LAUNCH_AZIMUTH, 0.0)
            
            # Save to persistent storage
            sim_id = self.simulation_manager.save_simulation(results, metadata)
            
            # Notify other widgets that a new simulation was saved
            if sim_id:
                self.simulation_saved.emit(sim_id)
            
            QMessageBox.information(
                self, tr("Success"),
                f"{tr('Simulation completed successfully!')}\n\n"
                f"{tr('Results saved with ID:')}\n{sim_id}\n\n"
                f"{tr('You can view them in the Dashboard.')}"
            )
            logger.info(f"Simulation saved with ID: {sim_id}")
        except Exception as e:
            logger.error(f"Error saving simulation: {e}")
            QMessageBox.warning(
                self, tr("Warning"),
                f"{tr('Simulation completed but failed to save results:')}\n{str(e)}"
            )
    
    def on_simulation_error(self, error_msg: str):
        """Handle simulation errors."""
        self.state.set(Constants.StateKeys.SIMULATION_ERROR, error_msg)
        self.state.set(Constants.StateKeys.SIMULATION_RUNNING, False)
        self._reset_simulation_controls()
        QMessageBox.critical(self, tr("Simulation Error"), f"{tr('Error:')} {error_msg}")
        logger.error(f"Simulation error: {error_msg}")
        
        # Publish event via event bus
        publish(EventType.SIMULATION_ERROR, {"error": error_msg, "timestamp": datetime.now().isoformat()})

    def toggle_pause(self):
        """Pause or resume the active simulation."""
        if self.simulation_worker is None or not self.simulation_worker.isRunning():
            return

        if self.simulation_paused:
            self.simulation_worker.resume()
            self.simulation_paused = False
            self.pause_button.setText(tr("⏸️ Pause"))
            self.status_message.emit(tr("Simulation resumed"))
            logger.info("Simulation resumed from GUI")
            
            # Publish resumed event
            publish(EventType.SIMULATION_RESUMED, {
                "timestamp": datetime.now().isoformat()
            })
        else:
            self.simulation_worker.pause()
            self.simulation_paused = True
            self.pause_button.setText(tr("▶️ Resume"))
            self.status_message.emit(tr("Simulation paused"))
            logger.info("Simulation paused from GUI")
            
            # Publish paused event
            publish(EventType.SIMULATION_PAUSED, {
                "timestamp": datetime.now().isoformat()
            })

    def stop_simulation(self):
        """Request graceful stop for the active simulation."""
        if self.simulation_worker is None or not self.simulation_worker.isRunning():
            return

        self.simulation_worker.stop()
        self.status_message.emit(tr("Stopping simulation"))
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setText(tr("⏸️ Pause"))
        
        # Publish stopped event
        publish(EventType.SIMULATION_STOPPED, {
            "timestamp": datetime.now().isoformat()
        })
        logger.info("Simulation stopped by user")

    def _reset_simulation_controls(self):
        """Restore control states after simulation ends or errors."""
        self.run_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setText(tr("⏸️ Pause"))
        self.simulation_paused = False
        self.status_message.emit(tr("Simulation finished"))

        if self.simulation_worker is not None:
            self.simulation_worker.wait()
            self.simulation_worker = None
    
    def reset_simulation(self):
        """Reset simulation parameters to defaults."""
        self.stop_simulation()

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
        self.state.set(Constants.StateKeys.SIMULATION_RESULTS, None)
        self.state.set(Constants.StateKeys.SIMULATION_ERROR, None)
        self.state.set(Constants.StateKeys.SIMULATION_RUNNING, False)
        
        logger.info("Simulation parameters reset to defaults")
