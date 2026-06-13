"""Monte Carlo Widget - Statistical simulation analysis."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QDoubleSpinBox,
    QPushButton, QGroupBox, QFormLayout, QProgressBar, QMessageBox, QTableWidget,
    QTableWidgetItem, QCheckBox, QTabWidget, QSizePolicy, QScrollArea,
)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from models.app_state import ApplicationState
from src.utils.simulation_manager import SimulationManager
from src.utils.monte_carlo_aggregator import MonteCarloAggregator
from workers.monte_carlo_runner import MonteCarloRunner
import logging
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thin canvas wrapper for embedding matplotlib figures in Qt layouts
# ---------------------------------------------------------------------------

class _PlotCanvas(FigureCanvas):
    """Resizable matplotlib canvas widget."""

    def __init__(self, figure, parent=None):
        super().__init__(figure)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.updateGeometry()


class MonteCarloWidget(QWidget):
    """
    Monte Carlo statistical simulation widget.

    Connects MonteCarloRunner (real 6-DOF physics) with MonteCarloAggregator
    (statistics + figures) and presents results in three tabs:
      - Configuration  : runs, seed, per-parameter σ overrides
      - Statistics     : table of mean/std/p05/p95 per metric
      - Plots          : apogee histogram, impact scatter, box plots
    """

    def __init__(self):
        super().__init__()
        self.state = ApplicationState.get_instance()
        self._thread: QThread | None = None
        self._runner: MonteCarloRunner | None = None
        self._accumulated_runs: list[dict] = []   # grows as runs complete
        self._plot_canvases: list[_PlotCanvas] = []
        self.init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def init_ui(self):
        root = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._build_config_tab(),     "Configuration")
        tabs.addTab(self._build_stats_tab(),       "Statistics")
        tabs.addTab(self._build_plots_tab(),       "Plots")
        root.addWidget(tabs)

    def _build_config_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # ---- Run settings ----
        run_group = QGroupBox("Run Settings")
        run_form = QFormLayout(run_group)

        self.runs_spinbox = QSpinBox()
        self.runs_spinbox.setRange(2, 10000)
        self.runs_spinbox.setValue(self.state.get('monte_carlo_runs', 100))
        self.runs_spinbox.valueChanged.connect(lambda v: self.state.set('monte_carlo_runs', v))
        run_form.addRow("Number of Runs:", self.runs_spinbox)

        self.seed_spinbox = QSpinBox()
        self.seed_spinbox.setSpecialValueText("Random")
        self.seed_spinbox.setRange(0, 999999)
        self.seed_spinbox.setValue(0)
        run_form.addRow("RNG Seed (0 = random):", self.seed_spinbox)

        layout.addWidget(run_group)

        # ---- Parameter uncertainties ----
        unc_group = QGroupBox("Parameter Uncertainties  (σ = 1 standard deviation)")
        unc_form = QFormLayout(unc_group)

        def _dspin(val, lo=0.0, hi=999.0, decimals=2, suffix=""):
            w = QDoubleSpinBox()
            w.setRange(lo, hi)
            w.setDecimals(decimals)
            w.setValue(val)
            if suffix:
                w.setSuffix(f"  {suffix}")
            return w

        self.sigma_elev   = _dspin(1.0, 0, 45, suffix="°")
        self.sigma_az     = _dspin(2.0, 0, 45, suffix="°")
        self.sigma_temp   = _dspin(2.0, 0, 20, suffix="°C")
        self.sigma_wind   = _dspin(1.0, 0, 50, suffix="m/s  (only if wind enabled)")
        self.sigma_winddir= _dspin(10.0, 0, 90, suffix="°  (only if wind enabled)")
        self.sigma_para_alt = _dspin(10.0, 0, 200, suffix="m  (only if chute enabled)")
        self.sigma_para_cd  = _dspin(0.075, 0, 1.0, decimals=3, suffix="(only if chute enabled)")

        unc_form.addRow("Launch elevation angle σ:", self.sigma_elev)
        unc_form.addRow("Launch azimuth σ:",          self.sigma_az)
        unc_form.addRow("Atmosphere temperature σ:",  self.sigma_temp)
        unc_form.addRow("Wind speed σ:",              self.sigma_wind)
        unc_form.addRow("Wind direction σ:",          self.sigma_winddir)
        unc_form.addRow("Parachute deploy altitude σ:", self.sigma_para_alt)
        unc_form.addRow("Parachute Cd σ:",            self.sigma_para_cd)

        layout.addWidget(unc_group)

        # ---- Progress & buttons ----
        ctrl_group = QGroupBox("Execution")
        ctrl_layout = QVBoxLayout(ctrl_group)

        self.status_label = QLabel("Ready.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        ctrl_layout.addWidget(self.progress_bar)

        btn_row = QHBoxLayout()
        self.run_button   = QPushButton("▶  Run Monte Carlo")
        self.stop_button  = QPushButton("■  Stop")
        self.reset_button = QPushButton("↺  Reset")
        self.stop_button.setEnabled(False)

        self.run_button.clicked.connect(self.run_monte_carlo)
        self.stop_button.clicked.connect(self.stop_monte_carlo)
        self.reset_button.clicked.connect(self.reset_monte_carlo)

        btn_row.addWidget(self.run_button)
        btn_row.addWidget(self.stop_button)
        btn_row.addWidget(self.reset_button)
        ctrl_layout.addLayout(btn_row)
        layout.addWidget(ctrl_group)

        layout.addStretch()
        return page

    def _build_stats_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.stats_label = QLabel("No results yet. Run a Monte Carlo batch first.")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stats_label)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels(
            ["Metric", "Mean", "Std", "Min", "P05", "Median", "P95", "Max"]
        )
        self.results_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.results_table)

        return page

    def _build_plots_tab(self) -> QWidget:
        """Scrollable area for matplotlib canvases (populated after a run)."""
        self._plots_page = QWidget()
        self._plots_layout = QVBoxLayout(self._plots_page)
        self._plots_layout.addWidget(
            QLabel("Plots will appear here after a completed run.")
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._plots_page)

        wrapper = QWidget()
        QVBoxLayout(wrapper).addWidget(scroll)
        return wrapper

    # ------------------------------------------------------------------
    # Run / stop / reset
    # ------------------------------------------------------------------

    def run_monte_carlo(self):
        """Start the Monte Carlo batch in a background thread."""
        n_runs = self.runs_spinbox.value()
        seed_val = self.seed_spinbox.value()
        seed = seed_val if seed_val > 0 else None

        # Build extra_configs from the σ spin boxes
        from src.utils.monte_carlo_sampler import ParameterConfig
        extra: dict = {}

        elev = float(self.state.get('launch_elevation_angle', 85.0))
        extra['launch_elevation_angle'] = ParameterConfig(
            'truncated_normal', nominal=elev,
            sigma=self.sigma_elev.value(), low=5.0, high=90.0)

        az = float(self.state.get('launch_azimuth', 0.0))
        extra['launch_azimuth'] = ParameterConfig(
            'truncated_normal', nominal=az,
            sigma=self.sigma_az.value(), low=0.0, high=360.0)

        temp = float(self.state.get('average_temperature', 20.0))
        extra['average_temperature'] = ParameterConfig(
            'normal', nominal=temp,
            sigma=self.sigma_temp.value(), low=-50.0, high=55.0)

        if self.state.get('wind_enabled', False):
            ws = float(self.state.get('wind_speed_ref', 5.0))
            extra['wind_speed_ref'] = ParameterConfig(
                'truncated_normal', nominal=ws,
                sigma=self.sigma_wind.value(), low=0.0)
            wd = float(self.state.get('wind_direction', 180.0))
            extra['wind_direction'] = ParameterConfig(
                'truncated_normal', nominal=wd,
                sigma=self.sigma_winddir.value(), low=0.0, high=360.0)

        if self.state.get('parachute_enabled', False):
            pa = float(self.state.get('parachute_deployment_altitude', 300.0))
            extra['parachute_deployment_altitude'] = ParameterConfig(
                'truncated_normal', nominal=pa,
                sigma=self.sigma_para_alt.value(), low=50.0)
            pc = float(self.state.get('parachute_cd', 1.5))
            extra['parachute_cd'] = ParameterConfig(
                'truncated_normal', nominal=pc,
                sigma=self.sigma_para_cd.value(), low=0.5)

        # Reset accumulators
        self._accumulated_runs.clear()
        self.results_table.setRowCount(0)
        self._clear_plots()
        self.progress_bar.setValue(0)

        # Create runner and thread
        self._thread = QThread()
        self._runner = MonteCarloRunner(
            self.state,
            n_runs=n_runs,
            seed=seed,
            sampler_configs=extra,
        )
        self._runner.moveToThread(self._thread)

        self._runner.run_completed.connect(self._on_run_completed)
        self._runner.run_failed.connect(self._on_run_failed)
        self._runner.progress.connect(self._on_progress)
        self._runner.finished.connect(self._on_finished)
        self._runner.error.connect(self._on_error)
        self._thread.started.connect(self._runner.run)

        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText(f"Running 0 / {n_runs} …")
        logger.info("Monte Carlo batch started: %d runs, seed=%s", n_runs, seed)
        self._thread.start()

    def stop_monte_carlo(self):
        """Request a graceful stop."""
        if self._runner:
            self._runner.stop()
        self.status_label.setText("Stop requested — finishing current run…")
        self.stop_button.setEnabled(False)

    def reset_monte_carlo(self):
        """Stop any running batch and reset the UI."""
        if self._runner:
            self._runner.stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        self._accumulated_runs.clear()
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        self._clear_plots()
        self.status_label.setText("Ready.")
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        logger.info("Monte Carlo reset.")

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_run_completed(self, idx: int, metrics: dict):
        self._accumulated_runs.append(metrics)
        n_total = self.runs_spinbox.value()
        self.status_label.setText(
            f"Completed {len(self._accumulated_runs)} / {n_total}  "
            f"(failed: {idx + 1 - len(self._accumulated_runs)})"
        )

    def _on_run_failed(self, idx: int, reason: str):
        logger.warning("Run %d failed: %s", idx, reason)

    def _on_progress(self, pct: int):
        self.progress_bar.setValue(pct)

    def _on_finished(self, summary: dict):
        self._cleanup_thread()
        n_ok = summary.get("n_successful", 0)
        n_fail = summary.get("n_failed", 0)
        self.status_label.setText(
            f"Done — {n_ok} successful, {n_fail} failed."
        )
        self.state.set('monte_carlo_results', summary)

        if self._accumulated_runs:
            self._populate_stats_table(self._accumulated_runs)
            self._refresh_plots(self._accumulated_runs)
        elif n_ok == 0:
            QMessageBox.warning(self, "Monte Carlo", "No runs completed successfully.")

        logger.info("Monte Carlo batch finished: %s", summary.get("batch_id"))

    def _on_error(self, msg: str):
        self._cleanup_thread()
        self.status_label.setText(f"Error: {msg}")
        QMessageBox.critical(self, "Monte Carlo Error", msg)

    def _cleanup_thread(self):
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if self._thread:
            self._thread.quit()
            self._thread.wait()

    # ------------------------------------------------------------------
    # Stats table
    # ------------------------------------------------------------------

    def _populate_stats_table(self, runs: list[dict]):
        agg = MonteCarloAggregator.from_runs(runs)
        all_stats = agg.all_scalar_stats()

        self.results_table.setRowCount(0)

        # Also add CEP row if impact data available
        cep = agg.cep()

        LABELS = {
            "max_altitude":    "Max Altitude (m)",
            "max_velocity":    "Max Velocity (m/s)",
            "max_mach":        "Max Mach",
            "max_range":       "Max Range (m)",
            "flight_duration": "Flight Duration (s)",
            "apogee_time":     "Apogee Time (s)",
            "max_accel_g":     "Max Accel (g)",
        }

        for key, stats in all_stats.items():
            if not stats:
                continue
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(LABELS.get(key, key)))
            for col, stat_key in enumerate(["mean", "std", "min", "p05", "median", "p95", "max"], start=1):
                val = stats.get(stat_key, float("nan"))
                self.results_table.setItem(row, col, QTableWidgetItem(f"{val:.2f}"))

        if cep > 0:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem("CEP (m)"))
            self.results_table.setItem(row, 1, QTableWidgetItem(f"{cep:.2f}"))

        self.results_table.resizeColumnsToContents()
        self.stats_label.setText(
            f"{len(runs)} successful runs  |  CEP = {cep:.1f} m"
        )

    # ------------------------------------------------------------------
    # Plots
    # ------------------------------------------------------------------

    def _clear_plots(self):
        for canvas in self._plot_canvases:
            self._plots_layout.removeWidget(canvas)
            canvas.deleteLater()
        self._plot_canvases.clear()
        # Remove placeholder label if present
        for i in reversed(range(self._plots_layout.count())):
            item = self._plots_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

    def _refresh_plots(self, runs: list[dict]):
        self._clear_plots()
        agg = MonteCarloAggregator.from_runs(runs)

        for fig in (
            agg.plot_apogee_histogram(),
            agg.plot_impact_scatter(),
            agg.plot_metric_boxplot(),
        ):
            canvas = _PlotCanvas(fig)
            self._plots_layout.addWidget(canvas)
            self._plot_canvases.append(canvas)

        self._plots_layout.addStretch()
