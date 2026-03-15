"""Monte Carlo Widget - Statistical simulation analysis."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QDoubleSpinBox,
    QPushButton, QGroupBox, QFormLayout, QProgressBar, QMessageBox, QTableWidget,
    QTableWidgetItem, QCheckBox
)
from PyQt6.QtCore import Qt
from models.app_state import ApplicationState
import logging

logger = logging.getLogger(__name__)


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
        """Run Monte Carlo simulations."""
        num_runs = self.runs_spinbox.value()
        logger.info(f"Starting Monte Carlo simulation with {num_runs} runs")
        self.run_button.setEnabled(False)
        
        # Placeholder: In production, this would spawn worker threads
        QMessageBox.information(
            self, "Monte Carlo",
            f"Monte Carlo simulation with {num_runs} runs would execute here.\n"
            "This feature will be implemented with background threading."
        )
        
        self.run_button.setEnabled(True)
    
    def reset_monte_carlo(self):
        """Reset Monte Carlo results."""
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        logger.info("Monte Carlo simulation reset")
