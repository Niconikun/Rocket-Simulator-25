"""Monte Carlo Widget - Landing zone (impact dispersion) prediction.

Purpose
-------
Determine WHERE the rocket is expected to land given uncertainty in launch
conditions, wind and (optionally) parachute descent. The batch reuses
whichever descent mode is currently configured in the Parachute tab: if the
parachute is disabled the flight is ballistic, otherwise it descends under
canopy. The main output is a 95% confidence landing area plotted on a map
around the launch site (falls back to a local East/North plot when no launch
coordinates or cartopy are available).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QDoubleSpinBox,
    QPushButton, QGroupBox, QFormLayout, QProgressBar, QMessageBox, QTableWidget,
    QTableWidgetItem, QTabWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches
from scipy.stats import chi2
from ui.widgets import BaseWidget
from models.app_state import ApplicationState
from src.models.state import StateProvider
from src.config import Constants
from typing import Optional
from src.utils.simulation_manager import SimulationManager
from src.utils.monte_carlo_aggregator import MonteCarloAggregator
from workers.monte_carlo_runner import MonteCarloRunner
import logging
import os
import numpy as np

logger = logging.getLogger(__name__)

# Optional cartopy background map (falls back to a local ENU plot when absent
# or when no launch latitude/longitude has been configured).
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    HAS_CARTOPY = True
except ImportError:
    HAS_CARTOPY = False

# Radial factor turning a 1σ dispersion ellipse into the 95% confidence
# region of a bivariate normal distribution (sqrt of the chi-square 95th
# percentile with 2 degrees of freedom).
_CONFIDENCE_95_FACTOR = float(np.sqrt(chi2.ppf(0.95, df=2)))

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


class MonteCarloWidget(BaseWidget):
    """
    Monte Carlo landing zone prediction widget.

    Connects MonteCarloRunner (real 6-DOF physics, wind + optional parachute)
    with MonteCarloAggregator (impact statistics) and presents results in
    three tabs:
      - Configuration  : runs, seed, per-parameter σ overrides
      - Landing Zone   : map with the 95% confidence landing area (main result)
      - Flight Performance : table of mean/std/p05/p95 per flight metric
    """

    # km per degree of latitude, used for the local ENU <-> lat/lon approximation
    _KM_PER_DEG_LAT = 111.32

    def __init__(self, state: Optional[StateProvider] = None):
        super().__init__(state=state)
        self._thread: QThread | None = None
        self._runner: MonteCarloRunner | None = None
        self._accumulated_runs: list[dict] = []   # grows as runs complete
        self._landing_canvas: _PlotCanvas | None = None
        self.init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def init_ui(self):
        root = QVBoxLayout(self)

        header = QLabel(
            "Predicts where the rocket will land, given launch, wind and "
            "(optional) parachute uncertainty. See the Landing Zone tab for the "
            "95% confidence impact area."
        )
        header.setWordWrap(True)
        root.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_config_tab(),  "Configuration")
        self.tabs.addTab(self._build_landing_tab(), "Landing Zone")
        self.tabs.addTab(self._build_stats_tab(),   "Flight Performance")
        self.tabs.currentChanged.connect(lambda _index: self._refresh_mode_labels())
        root.addWidget(self.tabs)

        self._refresh_mode_labels()

    def _build_config_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # ---- Current flight configuration (read-only summary) ----
        mode_group = QGroupBox("Current Flight Configuration")
        mode_form = QFormLayout(mode_group)

        self.cfg_mode_label = QLabel("—")
        mode_form.addRow("Descent Mode:", self.cfg_mode_label)

        self.cfg_wind_label = QLabel("—")
        mode_form.addRow("Wind Model:", self.cfg_wind_label)

        note = QLabel(
            "Descent mode and wind come from the Parachute and Wind tabs — this "
            "batch simply reuses whatever is currently active there."
        )
        note.setWordWrap(True)
        mode_form.addRow(note)

        layout.addWidget(mode_group)

        # ---- Run settings ----
        run_group = QGroupBox("Run Settings")
        run_form = QFormLayout(run_group)

        self.runs_spinbox = QSpinBox()
        self.runs_spinbox.setRange(Constants.MonteCarlo.MIN_MONTE_CARLO_RUNS, Constants.MonteCarlo.MAX_MONTE_CARLO_RUNS)
        self.runs_spinbox.setValue(self.state.get(Constants.StateKeys.MONTE_CARLO_RUNS, Constants.MonteCarlo.DEFAULT_MONTE_CARLO_RUNS))
        self.runs_spinbox.valueChanged.connect(lambda v: self.state.set(Constants.StateKeys.MONTE_CARLO_RUNS, v))
        run_form.addRow("Number of Runs:", self.runs_spinbox)

        self.seed_spinbox = QSpinBox()
        self.seed_spinbox.setSpecialValueText("Random")
        self.seed_spinbox.setRange(0, 999999)
        self.seed_spinbox.setValue(0)
        run_form.addRow("RNG Seed (0 = random):", self.seed_spinbox)

        self.workers_spinbox = QSpinBox()
        self.workers_spinbox.setRange(1, max(1, os.cpu_count() or 1))
        self.workers_spinbox.setValue(
            self.state.get(Constants.StateKeys.MONTE_CARLO_WORKERS, max(1, (os.cpu_count() or 1) - 1))
        )
        self.workers_spinbox.valueChanged.connect(lambda v: self.state.set(Constants.StateKeys.MONTE_CARLO_WORKERS, v))
        run_form.addRow("Parallel Workers (processes):", self.workers_spinbox)

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
        self.sigma_drogue_alt = _dspin(15.0, 0, 300, suffix="m  (only if drogue enabled)")
        self.sigma_drogue_cd  = _dspin(0.075, 0, 1.0, decimals=3, suffix="(only if drogue enabled)")

        unc_form.addRow("Launch elevation angle σ:", self.sigma_elev)
        unc_form.addRow("Launch azimuth σ:",          self.sigma_az)
        unc_form.addRow("Atmosphere temperature σ:",  self.sigma_temp)
        unc_form.addRow("Wind speed σ:",              self.sigma_wind)
        unc_form.addRow("Wind direction σ:",          self.sigma_winddir)
        unc_form.addRow("Parachute deploy altitude σ:", self.sigma_para_alt)
        unc_form.addRow("Parachute Cd σ:",            self.sigma_para_cd)
        unc_form.addRow("Drogue deploy altitude σ:",  self.sigma_drogue_alt)
        unc_form.addRow("Drogue Cd σ:",               self.sigma_drogue_cd)

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

    def _build_landing_tab(self) -> QWidget:
        """Main result: a map with the 95% confidence landing area."""
        page = QWidget()
        layout = QHBoxLayout(page)

        self._map_container = QWidget()
        self._map_layout = QVBoxLayout(self._map_container)
        self._map_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._map_container, stretch=3)

        summary_group = QGroupBox("Landing Zone Summary")
        summary_form = QFormLayout(summary_group)

        self.mode_value_label = QLabel("—")
        summary_form.addRow("Flight Mode:", self.mode_value_label)

        self.wind_value_label = QLabel("—")
        summary_form.addRow("Wind:", self.wind_value_label)

        self.runs_value_label = QLabel("—")
        summary_form.addRow("Successful Runs:", self.runs_value_label)

        self.landing_point_label = QLabel("—")
        self.landing_point_label.setWordWrap(True)
        summary_form.addRow("Predicted Landing Point:", self.landing_point_label)

        self.distance_value_label = QLabel("—")
        summary_form.addRow("Distance from Pad:", self.distance_value_label)

        self.bearing_value_label = QLabel("—")
        summary_form.addRow("Bearing from Pad:", self.bearing_value_label)

        self.cep_value_label = QLabel("—")
        summary_form.addRow("CEP (50%):", self.cep_value_label)

        self.ellipse_value_label = QLabel("—")
        self.ellipse_value_label.setWordWrap(True)
        summary_form.addRow("95% Landing Area (axes):", self.ellipse_value_label)

        self.area_value_label = QLabel("—")
        summary_form.addRow("95% Area (approx.):", self.area_value_label)

        summary_group.setMaximumWidth(300)
        layout.addWidget(summary_group, stretch=1)

        self._clear_landing_zone()
        return page

    def _build_stats_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.stats_label = QLabel(
            "No results yet. Run a Monte Carlo batch first. "
            "(This tab shows flight performance metrics — see the Landing Zone "
            "tab for the predicted impact area.)"
        )
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels(
            ["Metric", "Mean", "Std", "Min", "P05", "Median", "P95", "Max"]
        )
        header = self.results_table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        layout.addWidget(self.results_table)

        return page

    # ------------------------------------------------------------------
    # Flight-mode / landing-zone helpers
    # ------------------------------------------------------------------

    def _refresh_mode_labels(self):
        """Reflect the currently configured descent mode and wind model."""
        parachute_on = self.state.get(Constants.StateKeys.PARACHUTE_ENABLED, False)
        mode_txt = "Parachute descent" if parachute_on else "Ballistic (no parachute)"
        if parachute_on and self.state.get(Constants.StateKeys.DROGUE_ENABLED, False):
            mode_txt += " + drogue"
        self.cfg_mode_label.setText(mode_txt)

        if self.state.get(Constants.StateKeys.WIND_ENABLED, False):
            speed = self.state.get(Constants.StateKeys.WIND_SPEED_REF, self.state.get(Constants.StateKeys.WIND_SPEED, 0.0))
            direction = self.state.get(Constants.StateKeys.WIND_DIRECTION, 0.0)
            self.cfg_wind_label.setText(f"Enabled — {speed:.1f} m/s from {direction:.0f}°")
        else:
            self.cfg_wind_label.setText("Disabled")

    def _clear_landing_zone(self, add_placeholder: bool = True):
        """Remove the current map canvas (or placeholder) from the layout."""
        for i in reversed(range(self._map_layout.count())):
            item = self._map_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget is not None:
                widget.deleteLater()
        self._landing_canvas = None
        if add_placeholder:
            placeholder = QLabel("Run a Monte Carlo batch to see the predicted landing zone.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._map_layout.addWidget(placeholder)

    def _reset_landing_summary(self):
        for label in (
            self.mode_value_label, self.wind_value_label, self.runs_value_label,
            self.landing_point_label, self.distance_value_label,
            self.bearing_value_label, self.cep_value_label,
            self.ellipse_value_label, self.area_value_label,
        ):
            label.setText("—")

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

        elev = float(self.state.get(Constants.StateKeys.LAUNCH_ELEVATION_ANGLE, 85.0))
        extra[Constants.StateKeys.LAUNCH_ELEVATION_ANGLE] = ParameterConfig(
            'truncated_normal', nominal=elev,
            sigma=self.sigma_elev.value(), low=5.0, high=90.0)

        az = float(self.state.get(Constants.StateKeys.LAUNCH_AZIMUTH, 0.0))
        extra[Constants.StateKeys.LAUNCH_AZIMUTH] = ParameterConfig(
            'truncated_normal', nominal=az,
            sigma=self.sigma_az.value(), low=0.0, high=360.0)

        temp = float(self.state.get(Constants.StateKeys.AVERAGE_TEMPERATURE, 20.0))
        extra[Constants.StateKeys.AVERAGE_TEMPERATURE] = ParameterConfig(
            'normal', nominal=temp,
            sigma=self.sigma_temp.value(), low=-50.0, high=55.0)

        if self.state.get(Constants.StateKeys.WIND_ENABLED, False):
            ws = float(self.state.get(Constants.StateKeys.WIND_SPEED_REF, 5.0))
            extra[Constants.StateKeys.WIND_SPEED_REF] = ParameterConfig(
                'truncated_normal', nominal=ws,
                sigma=self.sigma_wind.value(), low=0.0)
            wd = float(self.state.get(Constants.StateKeys.WIND_DIRECTION, 180.0))
            extra[Constants.StateKeys.WIND_DIRECTION] = ParameterConfig(
                'truncated_normal', nominal=wd,
                sigma=self.sigma_winddir.value(), low=0.0, high=360.0)

        if self.state.get(Constants.StateKeys.PARACHUTE_ENABLED, False):
            pa = float(self.state.get(Constants.StateKeys.PARACHUTE_DEPLOYMENT_ALTITUDE, 300.0))
            extra[Constants.StateKeys.PARACHUTE_DEPLOYMENT_ALTITUDE] = ParameterConfig(
                'truncated_normal', nominal=pa,
                sigma=self.sigma_para_alt.value(), low=50.0)
            pc = float(self.state.get(Constants.StateKeys.PARACHUTE_CD, 1.5))
            extra[Constants.StateKeys.PARACHUTE_CD] = ParameterConfig(
                'truncated_normal', nominal=pc,
                sigma=self.sigma_para_cd.value(), low=0.5)

            if self.state.get(Constants.StateKeys.DROGUE_ENABLED, False):
                da = float(self.state.get(Constants.StateKeys.DROGUE_DEPLOYMENT_ALTITUDE, 800.0))
                extra[Constants.StateKeys.DROGUE_DEPLOYMENT_ALTITUDE] = ParameterConfig(
                    'truncated_normal', nominal=da,
                    sigma=self.sigma_drogue_alt.value(), low=100.0)
                dc = float(self.state.get(Constants.StateKeys.DROGUE_CD, 1.5))
                extra[Constants.StateKeys.DROGUE_CD] = ParameterConfig(
                    'truncated_normal', nominal=dc,
                    sigma=self.sigma_drogue_cd.value(), low=0.5)

        # Reset accumulators
        self._accumulated_runs.clear()
        self.results_table.setRowCount(0)
        self._clear_landing_zone()
        self._reset_landing_summary()
        self.progress_bar.setValue(0)

        # Create runner and thread
        self._thread = QThread()
        self._runner = MonteCarloRunner(
            self.state,
            n_runs=n_runs,
            seed=seed,
            sampler_configs=extra,
            n_workers=self.workers_spinbox.value(),
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
        n_workers = self.workers_spinbox.value()
        self.status_label.setText(f"Running 0 / {n_runs} … ({n_workers} parallel worker(s))")
        logger.info("Monte Carlo batch started: %d runs, seed=%s, workers=%d", n_runs, seed, n_workers)
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
            # Wait with timeout to avoid hanging
            if not self._thread.wait(5000):
                logger.warning("Monte Carlo thread did not stop gracefully")
                self._thread.terminate()
                self._thread.wait(5000)
        self._accumulated_runs.clear()
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        self._clear_landing_zone()
        self._reset_landing_summary()
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
        self.state.set(Constants.StateKeys.MONTE_CARLO_RESULTS, summary)

        if self._accumulated_runs:
            self._populate_stats_table(self._accumulated_runs)
            self._refresh_landing_zone(self._accumulated_runs)
            self.tabs.setCurrentIndex(1)  # bring the Landing Zone tab (main result) into view
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
            # Wait with timeout to avoid hanging
            if not self._thread.wait(5000):
                logger.warning("Monte Carlo thread did not stop gracefully")
                self._thread.terminate()
                self._thread.wait(5000)

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
    # Landing zone (main result)
    # ------------------------------------------------------------------

    def _refresh_landing_zone(self, runs: list[dict]):
        self._clear_landing_zone(add_placeholder=False)
        fig = self._build_landing_zone_figure(runs)
        self._landing_canvas = _PlotCanvas(fig)
        self._map_layout.addWidget(self._landing_canvas)
        self._update_landing_summary(runs)

    def _enu_to_latlon(self, x_m: np.ndarray, y_m: np.ndarray, lat0: float, lon0: float):
        """Approximate East/North offsets (m) from the launch pad as lat/lon.

        Uses a flat-Earth equirectangular approximation (consistent with the
        one used by the dashboard and location widgets); accurate enough for
        the sub-100 km dispersion areas typical of a Monte Carlo batch.
        """
        cos_lat0 = np.cos(np.radians(lat0))
        if abs(cos_lat0) < 1e-9:
            cos_lat0 = 1e-9
        dlat = (np.asarray(y_m, dtype=float) / 1000.0) / self._KM_PER_DEG_LAT
        dlon = (np.asarray(x_m, dtype=float) / 1000.0) / (self._KM_PER_DEG_LAT * cos_lat0)
        return lat0 + dlat, lon0 + dlon

    def _build_landing_zone_figure(self, runs: list[dict]) -> Figure:
        agg = MonteCarloAggregator.from_runs(runs)
        ix, iy = agg.impact_arrays()

        fig = Figure(figsize=(7, 6))
        if len(ix) == 0:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No valid impact data in this batch.",
                    ha="center", va="center", transform=ax.transAxes)
            return fig

        mean_x, mean_y = float(np.mean(ix)), float(np.mean(iy))
        ellipse = agg.dispersion_ellipse(sigma_level=_CONFIDENCE_95_FACTOR)

        lat0 = float(self.state.get(Constants.StateKeys.LAUNCH_LATITUDE, 0.0))
        lon0 = float(self.state.get(Constants.StateKeys.LAUNCH_LONGITUDE, 0.0))
        has_coords = abs(lat0) > 1e-9 or abs(lon0) > 1e-9
        mode_txt = "Parachute descent" if self.state.get(Constants.StateKeys.PARACHUTE_ENABLED, False) else "Ballistic (no parachute)"

        if HAS_CARTOPY and has_coords:
            return self._draw_map_landing_zone(fig, ix, iy, mean_x, mean_y, ellipse, lat0, lon0, mode_txt)
        return self._draw_local_landing_zone(fig, ix, iy, mean_x, mean_y, ellipse, mode_txt, has_coords)

    def _draw_map_landing_zone(self, fig, ix, iy, mean_x, mean_y, ellipse, lat0, lon0, mode_txt) -> Figure:
        """Plot the impact dispersion over a real map, centred on the launch site."""
        # View extent: covers the launch pad and the 95% ellipse with margin
        if ellipse:
            span_m = max(
                np.hypot(ellipse["center_x"], ellipse["center_y"]) / 2.0 + ellipse["semi_major"],
                ellipse["semi_major"],
            ) * 1.25
        else:
            span_m = max(float(np.max(np.hypot(ix, iy))), 100.0) * 1.25
        span_m = max(span_m, 250.0)

        center_x = (ellipse["center_x"] / 2.0) if ellipse else mean_x / 2.0
        center_y = (ellipse["center_y"] / 2.0) if ellipse else mean_y / 2.0
        center_lat, center_lon = self._enu_to_latlon(np.array([center_x]), np.array([center_y]), lat0, lon0)
        center_lat, center_lon = float(center_lat[0]), float(center_lon[0])

        pad_km = span_m / 1000.0
        delta_lat = pad_km / self._KM_PER_DEG_LAT
        cos_lat0 = np.cos(np.radians(lat0)) or 1e-9
        delta_lon = pad_km / (self._KM_PER_DEG_LAT * cos_lat0)
        extent = [center_lon - delta_lon, center_lon + delta_lon,
                  center_lat - delta_lat, center_lat + delta_lat]
        res = '10m' if pad_km < 50 else '50m' if pad_km < 300 else '110m'

        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        ax.set_extent(extent, crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.NaturalEarthFeature(
            'physical', 'land', res, facecolor='#e6dfa8', edgecolor='none'))
        ax.add_feature(cfeature.NaturalEarthFeature(
            'physical', 'ocean', res, facecolor='#a8d0e8', edgecolor='none'))
        ax.add_feature(cfeature.NaturalEarthFeature(
            'cultural', 'admin_0_countries', res, facecolor='none', edgecolor='#555555', linewidth=0.5))
        ax.add_feature(cfeature.NaturalEarthFeature(
            'physical', 'coastline', res, facecolor='none', edgecolor='#333333', linewidth=0.7))

        lat_pts, lon_pts = self._enu_to_latlon(ix, iy, lat0, lon0)
        ax.scatter(lon_pts, lat_pts, transform=ccrs.PlateCarree(), s=8, alpha=0.35,
                   color='#2E7D32', zorder=4, label=f'Impacts (n={len(ix)})')

        if ellipse:
            theta = np.linspace(0, 2 * np.pi, 120)
            ang = np.radians(ellipse["angle_deg"])
            ex = ellipse["semi_major"] * np.cos(theta)
            ey = ellipse["semi_minor"] * np.sin(theta)
            poly_x = ex * np.cos(ang) - ey * np.sin(ang) + ellipse["center_x"]
            poly_y = ex * np.sin(ang) + ey * np.cos(ang) + ellipse["center_y"]
            poly_lat, poly_lon = self._enu_to_latlon(poly_x, poly_y, lat0, lon0)
            ax.fill(poly_lon, poly_lat, transform=ccrs.PlateCarree(), color='#FFD700', alpha=0.30, zorder=5)
            ax.plot(poly_lon, poly_lat, transform=ccrs.PlateCarree(), color='#FF6F00',
                    linewidth=2, zorder=6, label='95% landing area')

        mean_lat, mean_lon = self._enu_to_latlon(np.array([mean_x]), np.array([mean_y]), lat0, lon0)
        ax.scatter([lon0], [lat0], transform=ccrs.PlateCarree(), color='red', marker='*',
                   s=200, zorder=7, label='Launch Site')
        ax.scatter(mean_lon, mean_lat, transform=ccrs.PlateCarree(), color='#2196F3', marker='X',
                   s=110, zorder=7, label='Predicted Landing (mean)')

        gl = ax.gridlines(draw_labels=True, linewidth=0.4, color='gray', alpha=0.5, linestyle='--')
        gl.top_labels = False
        gl.right_labels = False

        ax.set_title(
            f"Predicted Landing Zone — {mode_txt}\n"
            f"Launch: ({lat0:.5f}°, {lon0:.5f}°)", fontsize=10
        )
        ax.legend(loc='upper right', fontsize=8)
        fig.tight_layout()
        return fig

    def _draw_local_landing_zone(self, fig, ix, iy, mean_x, mean_y, ellipse, mode_txt, has_coords) -> Figure:
        """Fallback plot in local East/North coordinates around the launch pad."""
        ax = fig.add_subplot(111)
        ax.scatter(ix / 1000.0, iy / 1000.0, s=8, alpha=0.4, color='#4CAF50',
                   label=f'Impacts (n={len(ix)})', zorder=3)

        if ellipse:
            patch = mpatches.Ellipse(
                xy=(ellipse["center_x"] / 1000.0, ellipse["center_y"] / 1000.0),
                width=2 * ellipse["semi_major"] / 1000.0,
                height=2 * ellipse["semi_minor"] / 1000.0,
                angle=ellipse["angle_deg"],
                fill=True, facecolor='#FFD700', alpha=0.25,
                edgecolor='#FF6F00', linewidth=2, label='95% landing area', zorder=4,
            )
            ax.add_patch(patch)

        ax.scatter([0], [0], color='red', marker='*', s=200, zorder=6, label='Launch Site')
        ax.scatter([mean_x / 1000.0], [mean_y / 1000.0], color='#2196F3', marker='X',
                   s=120, zorder=6, label='Predicted Landing (mean)')

        ax.set_xlabel('East (km)')
        ax.set_ylabel('North (km)')
        subtitle = "" if has_coords else "\n(set launch latitude/longitude for a real map)"
        ax.set_title(f'Predicted Landing Zone — {mode_txt}{subtitle}', fontsize=10)
        ax.set_aspect('equal', adjustable='datalim')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc='best')

        fig.patch.set_facecolor('#1e1e1e')
        ax.set_facecolor('#2d2d2d')
        for spine in ax.spines.values():
            spine.set_edgecolor('#555')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        ax.legend(facecolor='#333', edgecolor='#555', labelcolor='white', fontsize=8)
        fig.tight_layout()
        return fig

    def _update_landing_summary(self, runs: list[dict]):
        agg = MonteCarloAggregator.from_runs(runs)
        ix, iy = agg.impact_arrays()

        self.runs_value_label.setText(str(len(ix)))
        parachute_on = self.state.get(Constants.StateKeys.PARACHUTE_ENABLED, False)
        mode_txt = "Parachute descent" if parachute_on else "Ballistic (no parachute)"
        if parachute_on and self.state.get(Constants.StateKeys.DROGUE_ENABLED, False):
            mode_txt += " + drogue"
        self.mode_value_label.setText(mode_txt)
        if self.state.get(Constants.StateKeys.WIND_ENABLED, False):
            speed = self.state.get(Constants.StateKeys.WIND_SPEED_REF, self.state.get(Constants.StateKeys.WIND_SPEED, 0.0))
            self.wind_value_label.setText(f"Enabled ({speed:.1f} m/s)")
        else:
            self.wind_value_label.setText("Disabled")

        if len(ix) == 0:
            for label in (
                self.landing_point_label, self.distance_value_label,
                self.bearing_value_label, self.cep_value_label,
                self.ellipse_value_label, self.area_value_label,
            ):
                label.setText("N/A")
            return

        mean_x, mean_y = float(np.mean(ix)), float(np.mean(iy))
        distance_m = float(np.hypot(mean_x, mean_y))
        bearing_deg = float(np.degrees(np.arctan2(mean_x, mean_y)) % 360)

        lat0 = float(self.state.get(Constants.StateKeys.LAUNCH_LATITUDE, 0.0))
        lon0 = float(self.state.get(Constants.StateKeys.LAUNCH_LONGITUDE, 0.0))
        if abs(lat0) > 1e-9 or abs(lon0) > 1e-9:
            lat_m, lon_m = self._enu_to_latlon(np.array([mean_x]), np.array([mean_y]), lat0, lon0)
            self.landing_point_label.setText(f"{float(lat_m[0]):.5f}°, {float(lon_m[0]):.5f}°")
        else:
            self.landing_point_label.setText(
                f"E {mean_x:+.0f} m, N {mean_y:+.0f} m (set launch coordinates for lat/lon)"
            )

        self.distance_value_label.setText(f"{distance_m:,.0f} m ({distance_m / 1000.0:.2f} km)")
        self.bearing_value_label.setText(f"{bearing_deg:.1f}°")
        self.cep_value_label.setText(f"{agg.cep():.0f} m")

        ellipse = agg.dispersion_ellipse(sigma_level=_CONFIDENCE_95_FACTOR)
        if ellipse:
            a, b = ellipse["semi_major"], ellipse["semi_minor"]
            self.ellipse_value_label.setText(f"{a:.0f} m × {b:.0f} m")
            self.area_value_label.setText(f"{(np.pi * a * b) / 1e6:.3f} km²")
        else:
            self.ellipse_value_label.setText("N/A (need ≥ 2 runs)")
            self.area_value_label.setText("N/A")

