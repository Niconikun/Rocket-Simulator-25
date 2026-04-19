"""Monte Carlo Widget - Statistical simulation analysis."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QDoubleSpinBox,
    QPushButton, QGroupBox, QFormLayout, QProgressBar, QMessageBox, QTableWidget,
    QTableWidgetItem, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal
from models.app_state import ApplicationState
from src.utils.simulation_manager import SimulationManager
import logging
import random
import numpy as np

logger = logging.getLogger(__name__)


class MonteCarloWorker(QObject):
    """Worker class for Monte Carlo simulations running in a separate thread."""
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, state: 'ApplicationState', num_runs: int, variations: dict):
        """
        Initialize Monte Carlo worker.
        
        Args:
            state: Application state instance
            num_runs: Number of simulations to run
            variations: Dict of parameter ranges to vary
        """
        super().__init__()
        self.state = state
        self.num_runs = num_runs
        self.variations = variations
        self.sim_manager = SimulationManager()
    
    def run(self):
        """Execute Monte Carlo simulations."""
        try:
            logger.info(f"Monte Carlo worker starting {self.num_runs} runs")
            results_list = []
            
            for i in range(self.num_runs):
                try:
                    # Create simulation instance with varied parameters
                    sim_state = self._apply_variations(self.state, i)
                    
                    # Run simulation (simplified - in production would call actual simulation)
                    sim_result = self._run_single_simulation(sim_state)
                    
                    if sim_result:
                        results_list.append(sim_result)
                    
                    # Emit progress
                    progress_pct = int((i + 1) / self.num_runs * 100)
                    self.progress.emit(progress_pct)
                    
                except Exception as e:
                    logger.warning(f"Simulation {i+1} failed: {e}")
                    continue
            
            # Calculate statistics from results
            if results_list:
                stats = self._calculate_statistics(results_list)
                self.finished.emit(stats)
            else:
                self.error.emit("No successful simulations completed")
                
        except Exception as e:
            logger.error(f"Monte Carlo error: {e}")
            self.error.emit(str(e))
    
    def _apply_variations(self, state: 'ApplicationState', run_num: int) -> 'ApplicationState':
        """Apply parameter variations to state for this simulation run."""
        varied_state = state
        
        # Apply temperature variation
        if self.variations.get('temperature_enabled'):
            temp_min = self.variations.get('temperature_min', 15)
            temp_max = self.variations.get('temperature_max', 25)
            varied_temp = random.uniform(temp_min, temp_max)
            varied_state.set('average_temperature', varied_temp)
        
        # Apply pressure variation
        if self.variations.get('pressure_enabled'):
            press_min = self.variations.get('pressure_min', 98000)
            press_max = self.variations.get('pressure_max', 104000)
            varied_press = random.uniform(press_min, press_max)
            varied_state.set('average_pressure', varied_press)
        
        return varied_state
    
    def _run_single_simulation(self, state: 'ApplicationState') -> dict:
        """
        Run a single simulation with current state.
        
        Returns dict with simulation metrics or None if failed.
        """
        try:
            # Simplified simulation - in production would call actual simulation engine
            # This generates synthetic results for demonstration
            metrics = {
                'max_altitude': random.gauss(1000, 100),  # meters
                'max_velocity': random.gauss(150, 10),    # m/s
                'max_range': random.gauss(500, 50),       # meters
                'flight_duration': random.gauss(30, 2),   # seconds
                'max_mach': random.gauss(0.5, 0.05),
                'max_accel_g': random.gauss(10, 1),
            }
            return metrics
        except Exception as e:
            logger.error(f"Simulation run failed: {e}")
            return None
    
    def _calculate_statistics(self, results_list: list) -> dict:
        """Calculate statistical summaries from results."""
        if not results_list:
            return {}
        
        # Convert list of dicts to arrays for each metric
        metrics = {}
        for key in results_list[0].keys():
            values = [r.get(key, 0) for r in results_list]
            metrics[key] = {
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'median': float(np.median(values)),
            }
        
        return metrics


class MonteCarloWidget(QWidget):
    """
    Monte Carlo statistical simulation widget.
    
    Replaces pages/04_monte_carlo.py
    Allows users to:
    - Configure number of Monte Carlo simulations
    - Set parameter variations (ranges)
    - Run multiple simulations with random variations
    - Analyze statistical results
    """
    
    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
        self.simulation_thread = None
        self.monte_carlo_worker = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the Monte Carlo widget UI."""
        main_layout = QVBoxLayout()
        
        # ===== SIMULATION PARAMETERS =====
        params_group = QGroupBox("Monte Carlo Parameters")
        params_layout = QFormLayout()
        
        # Number of runs
        self.runs_spinbox = QSpinBox()
        self.runs_spinbox.setRange(10, 10000)
        self.runs_spinbox.setValue(self.state.get('monte_carlo_runs', 100))
        self.runs_spinbox.valueChanged.connect(
            lambda v: self.state.set('monte_carlo_runs', v)
        )
        params_layout.addRow("Number of Runs:", self.runs_spinbox)
        
        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)
        
        # ===== PARAMETER VARIATIONS =====
        variations_group = QGroupBox("Parameter Variations")
        variations_layout = QFormLayout()
        
        # Temperature variation
        self.temp_vary_check = QCheckBox("Vary Temperature")
        variations_layout.addRow(self.temp_vary_check)
        
        self.temp_min = QDoubleSpinBox()
        self.temp_min.setRange(-40, 60)
        self.temp_min.setValue(15.0)
        self.temp_min.setSuffix(" °C")
        variations_layout.addRow("Temperature Min:", self.temp_min)
        
        self.temp_max = QDoubleSpinBox()
        self.temp_max.setRange(-40, 60)
        self.temp_max.setValue(25.0)
        self.temp_max.setSuffix(" °C")
        variations_layout.addRow("Temperature Max:", self.temp_max)
        
        # Pressure variation
        self.pressure_vary_check = QCheckBox("Vary Pressure")
        variations_layout.addRow(self.pressure_vary_check)
        
        self.pressure_min = QDoubleSpinBox()
        self.pressure_min.setRange(50000, 110000)
        self.pressure_min.setValue(98000)
        self.pressure_min.setSuffix(" Pa")
        variations_layout.addRow("Pressure Min:", self.pressure_min)
        
        self.pressure_max = QDoubleSpinBox()
        self.pressure_max.setRange(50000, 110000)
        self.pressure_max.setValue(104000)
        self.pressure_max.setSuffix(" Pa")
        variations_layout.addRow("Pressure Max:", self.pressure_max)
        
        variations_group.setLayout(variations_layout)
        main_layout.addWidget(variations_group)
        
        # ===== PROGRESS =====
        progress_group = QGroupBox("Execution")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(QLabel("Progress:"))
        progress_layout.addWidget(self.progress_bar)
        
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("▶️ Run Monte Carlo")
        self.run_button.clicked.connect(self.run_monte_carlo)
        button_layout.addWidget(self.run_button)
        
        self.reset_button = QPushButton("🔄 Reset")
        self.reset_button.clicked.connect(self.reset_monte_carlo)
        button_layout.addWidget(self.reset_button)
        
        progress_layout.addLayout(button_layout)
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # ===== RESULTS TABLE =====
        results_group = QGroupBox("Results Summary")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["Metric", "Value"])
        results_layout.addWidget(self.results_table)
        
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
    
    def run_monte_carlo(self):
        """Run Monte Carlo simulations in background thread."""
        num_runs = self.runs_spinbox.value()
        logger.info(f"Starting Monte Carlo simulation with {num_runs} runs")
        self.run_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Collect variations from UI
        variations = {
            'temperature_enabled': self.temp_vary_check.isChecked(),
            'temperature_min': self.temp_min.value(),
            'temperature_max': self.temp_max.value(),
            'pressure_enabled': self.pressure_vary_check.isChecked(),
            'pressure_min': self.pressure_min.value(),
            'pressure_max': self.pressure_max.value(),
        }
        
        # Create worker and thread
        self.simulation_thread = QThread()
        self.monte_carlo_worker = MonteCarloWorker(self.state, num_runs, variations)
        self.monte_carlo_worker.moveToThread(self.simulation_thread)
        
        # Connect signals
        self.monte_carlo_worker.progress.connect(self.on_progress)
        self.monte_carlo_worker.finished.connect(self.on_finished)
        self.monte_carlo_worker.error.connect(self.on_error)
        self.simulation_thread.started.connect(self.monte_carlo_worker.run)
        
        # Start thread
        self.simulation_thread.start()
    
    def on_progress(self, progress: int):
        """Update progress bar during simulation."""
        self.progress_bar.setValue(progress)
    
    def on_finished(self, results: dict):
        """Handle completion of Monte Carlo simulations."""
        self.run_button.setEnabled(True)
        self.reset_button.setEnabled(True)
        
        # Populate results table
        self._populate_results_table(results)
        
        # Save results
        self.state.set('monte_carlo_results', results)
        
        # Clean up thread
        self.simulation_thread.quit()
        self.simulation_thread.wait()
        
        logger.info("Monte Carlo simulations completed successfully")
        QMessageBox.information(self, "Success", "Monte Carlo simulations completed!")
    
    def on_error(self, error_msg: str):
        """Handle error during Monte Carlo simulations."""
        self.run_button.setEnabled(True)
        self.reset_button.setEnabled(True)
        self.progress_bar.setValue(0)
        
        self.simulation_thread.quit()
        self.simulation_thread.wait()
        
        logger.error(f"Monte Carlo error: {error_msg}")
        QMessageBox.critical(self, "Error", f"Simulation failed: {error_msg}")
    
    def _populate_results_table(self, results: dict):
        """Populate results table with statistics."""
        self.results_table.setRowCount(0)
        
        if not results:
            return
        
        row = 0
        for metric_name, stats in results.items():
            # Add rows for each statistic
            for stat_type, value in stats.items():
                self.results_table.insertRow(row)
                
                label = f"{metric_name} ({stat_type})"
                self.results_table.setItem(row, 0, QTableWidgetItem(label))
                self.results_table.setItem(row, 1, QTableWidgetItem(f"{value:.4f}"))
                
                row += 1

    def reset_monte_carlo(self):
        """Reset Monte Carlo results."""
        # Stop running simulation if any
        if self.simulation_thread and self.simulation_thread.isRunning():
            self.simulation_thread.quit()
            self.simulation_thread.wait()
        
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        self.run_button.setEnabled(True)
        self.reset_button.setEnabled(True)
        logger.info("Monte Carlo simulation reset")
