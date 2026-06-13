"""
Monte Carlo Runner
==================
Orchestrates N simulation runs using ``SimulationWorker.run_with_params()``
and ``MonteCarloSampler``, emitting Qt signals for GUI integration.

Architecture
------------
::

    MonteCarloRunner (QObject, runs inside a QThread)
        │
        ├── MonteCarloSampler   — draws stochastic parameter overrides
        ├── SimulationWorker    — executes the 6-DOF physics engine per run
        └── incremental JSON Lines output  → data/simulations/mc_<batch_id>.jsonl

Signals
-------
- ``run_completed(int, dict)``   — emitted after each successful run (run_index, metrics)
- ``run_failed(int, str)``       — emitted after each failed run (run_index, reason)
- ``progress(int)``              — 0–100 overall completion percentage
- ``finished(dict)``             — emitted when all runs are done (batch summary)
- ``error(str)``                 — emitted if the batch is aborted by a fatal error

Usage (from a QWidget)
----------------------
::

    self._thread = QThread()
    self._runner = MonteCarloRunner(state, n_runs=100, seed=42)
    self._runner.moveToThread(self._thread)
    self._runner.progress.connect(self.progress_bar.setValue)
    self._runner.finished.connect(self.on_mc_finished)
    self._thread.started.connect(self._runner.run)
    self._thread.start()
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

from src.utils.monte_carlo_sampler import MonteCarloSampler, ParameterConfig
from workers.simulation_worker import SimulationWorker

logger = logging.getLogger(__name__)

# Directory where batch output files are written
_OUTPUT_DIR = os.path.join("data", "simulations")


class MonteCarloRunner(QObject):
    """Runs N simulations with stochastically sampled parameters.

    Parameters
    ----------
    state:
        Live ``ApplicationState`` instance (never mutated — each run uses a
        ``_StateProxy`` overlay via ``SimulationWorker.run_with_params()``).
    n_runs:
        Number of Monte Carlo iterations.
    seed:
        Optional integer seed for reproducible sampling sequences.
    sampler_configs:
        Optional ``{key: ParameterConfig}`` dict passed to
        ``MonteCarloSampler.from_state()``.  When ``None`` the defaults from
        :meth:`MonteCarloSampler.from_state` are used.
    save_trajectory:
        When ``True`` the full trajectory list is stored per-run in the JSONL
        output.  Set to ``False`` (default) to save only metrics and keep file
        sizes small.
    """

    # ---- Qt signals -------------------------------------------------------
    run_completed = pyqtSignal(int, dict)   # (run_index, metrics_dict)
    run_failed    = pyqtSignal(int, str)    # (run_index, reason)
    progress      = pyqtSignal(int)         # 0-100
    finished      = pyqtSignal(dict)        # batch summary
    error         = pyqtSignal(str)         # fatal error

    def __init__(
        self,
        state,
        n_runs: int = 100,
        seed: Optional[int] = None,
        sampler_configs: Optional[dict] = None,
        save_trajectory: bool = False,
    ) -> None:
        super().__init__()
        self._state = state
        self._n_runs = max(1, n_runs)
        self._seed = seed
        self._sampler_configs = sampler_configs
        self._save_trajectory = save_trajectory

        self._is_running = False
        self._batch_id: str = ""

    # ------------------------------------------------------------------
    # Public control
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Request a graceful stop after the current run finishes."""
        self._is_running = False
        logger.info("MonteCarloRunner stop requested.")

    # ------------------------------------------------------------------
    # Main entry point (called by QThread.started signal)
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Execute the full Monte Carlo batch."""
        self._is_running = True
        self._batch_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_mc_" + uuid.uuid4().hex[:6]

        logger.info("=" * 60)
        logger.info("Monte Carlo batch starting: %s (%d runs)", self._batch_id, self._n_runs)
        logger.info("=" * 60)

        # Build sampler
        sampler = MonteCarloSampler.from_state(
            self._state,
            seed=self._seed,
            extra_configs=self._sampler_configs,
        )
        logger.info(sampler.summary())

        # Build a persistent SimulationWorker (state will be overridden per run)
        worker = SimulationWorker(self._state)

        # Prepare output file
        output_path = os.path.join(_OUTPUT_DIR, f"{self._batch_id}.jsonl")
        os.makedirs(_OUTPUT_DIR, exist_ok=True)

        # Batch accumulators
        successful: list[dict] = []
        failed_runs: list[int] = []

        try:
            with open(output_path, "w", encoding="utf-8") as out_file:
                for i in range(self._n_runs):
                    if not self._is_running:
                        logger.info("Monte Carlo batch cancelled at run %d.", i)
                        break

                    overrides = sampler.sample()
                    logger.debug("Run %d/%d overrides: %s", i + 1, self._n_runs, overrides)

                    try:
                        # Run physics engine synchronously with this run's parameters
                        result = worker.run_with_params(overrides)

                        metrics = result.get("metrics", {})
                        impact_x, impact_y = self._extract_impact_position(result)

                        run_record = {
                            "run": i,
                            "overrides": overrides,
                            "metrics": {
                                "max_altitude":    metrics.get("max_altitude", 0.0),
                                "max_velocity":    metrics.get("max_velocity", 0.0),
                                "max_mach":        metrics.get("max_mach", 0.0),
                                "max_range":       metrics.get("max_range", 0.0),
                                "flight_duration": metrics.get("flight_duration", 0.0),
                                "apogee_time":     metrics.get("apogee_time", 0.0),
                                "max_accel_g":     metrics.get("max_accel_g", 0.0),
                                "impact_x":        impact_x,
                                "impact_y":        impact_y,
                            },
                        }
                        if self._save_trajectory:
                            run_record["trajectory"] = result.get("trajectory", [])

                        # Incremental write — safe even if interrupted
                        out_file.write(json.dumps(run_record) + "\n")
                        out_file.flush()

                        successful.append(run_record["metrics"])
                        self.run_completed.emit(i, run_record["metrics"])

                    except Exception as run_err:
                        reason = str(run_err)
                        logger.warning("Run %d failed: %s", i + 1, reason)
                        failed_runs.append(i)
                        self.run_failed.emit(i, reason)

                    # Emit overall progress
                    pct = int((i + 1) / self._n_runs * 100)
                    self.progress.emit(pct)

        except Exception as fatal:
            logger.error("Fatal error in Monte Carlo batch: %s", fatal, exc_info=True)
            self.error.emit(str(fatal))
            return

        # Build and emit summary
        summary = self._build_summary(
            batch_id=self._batch_id,
            n_requested=self._n_runs,
            successful=successful,
            failed_runs=failed_runs,
            output_path=output_path,
            sampler_summary=sampler.summary(),
        )

        # Write summary alongside the JSONL file
        summary_path = output_path.replace(".jsonl", "_summary.json")
        try:
            with open(summary_path, "w", encoding="utf-8") as sf:
                json.dump(summary, sf, indent=2)
        except Exception as save_err:
            logger.warning("Could not save batch summary: %s", save_err)

        logger.info(
            "Monte Carlo batch finished: %d/%d successful, %d failed.",
            len(successful), self._n_runs, len(failed_runs),
        )
        self.finished.emit(summary)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_impact_position(result: dict) -> tuple[float, float]:
        """Return the (x, y) ENU impact coordinates from a simulation result.

        Prefers the optimised ``history`` arrays; falls back to the last
        trajectory point.
        """
        history = result.get("history", {})
        if history:
            # history stores field arrays; r_enu is [x, y, z] × timesteps
            r_enu = history.get("r_enu")
            if r_enu is not None:
                try:
                    arr = np.asarray(r_enu)
                    if arr.ndim == 2 and arr.shape[1] >= 2:
                        return float(arr[-1, 0]), float(arr[-1, 1])
                    elif arr.ndim == 1 and len(arr) >= 2:
                        return float(arr[0]), float(arr[1])
                except Exception:
                    pass

        # Fallback: last trajectory point
        trajectory = result.get("trajectory", [])
        if trajectory:
            last = trajectory[-1]
            # trajectory stores horizontal range, not x/y separately
            range_val = last.get("range", 0.0)
            return float(range_val), 0.0

        return 0.0, 0.0

    @staticmethod
    def _build_summary(
        batch_id: str,
        n_requested: int,
        successful: list[dict],
        failed_runs: list[int],
        output_path: str,
        sampler_summary: str,
    ) -> dict:
        """Compute aggregate statistics over all successful runs."""
        n_ok = len(successful)

        summary: dict = {
            "batch_id":       batch_id,
            "timestamp":      datetime.now().isoformat(),
            "n_requested":    n_requested,
            "n_successful":   n_ok,
            "n_failed":       len(failed_runs),
            "failed_runs":    failed_runs,
            "output_file":    output_path,
            "sampler_config": sampler_summary,
            "statistics":     {},
        }

        if not successful:
            return summary

        # Scalar metrics to aggregate
        scalar_keys = [
            "max_altitude", "max_velocity", "max_mach",
            "max_range", "flight_duration", "apogee_time",
            "max_accel_g",
        ]
        stats: dict = {}
        for key in scalar_keys:
            values = np.array([r.get(key, np.nan) for r in successful], dtype=float)
            valid = values[~np.isnan(values)]
            if len(valid) == 0:
                continue
            stats[key] = {
                "mean":   float(np.mean(valid)),
                "std":    float(np.std(valid)),
                "min":    float(np.min(valid)),
                "p05":    float(np.percentile(valid, 5)),
                "median": float(np.median(valid)),
                "p95":    float(np.percentile(valid, 95)),
                "max":    float(np.max(valid)),
            }

        # Impact scatter (CEP & dispersion ellipse)
        impact_x = np.array([r.get("impact_x", np.nan) for r in successful])
        impact_y = np.array([r.get("impact_y", np.nan) for r in successful])
        valid_mask = ~(np.isnan(impact_x) | np.isnan(impact_y))
        ix = impact_x[valid_mask]
        iy = impact_y[valid_mask]

        if len(ix) >= 2:
            cep = _compute_cep(ix, iy)
            stats["impact_scatter"] = {
                "mean_x":  float(np.mean(ix)),
                "mean_y":  float(np.mean(iy)),
                "std_x":   float(np.std(ix)),
                "std_y":   float(np.std(iy)),
                "cep_m":   cep,
                "n_points": int(len(ix)),
            }

            # 1-sigma dispersion ellipse semi-axes (eigenvalues of covariance matrix)
            cov = np.cov(ix, iy)
            eigenvalues = np.linalg.eigvalsh(cov)
            eigenvalues = np.sort(eigenvalues)[::-1]  # descending
            stats["impact_scatter"]["ellipse_semi_major_m"] = float(np.sqrt(max(eigenvalues[0], 0.0)))
            stats["impact_scatter"]["ellipse_semi_minor_m"] = float(np.sqrt(max(eigenvalues[1], 0.0)))

        summary["statistics"] = stats
        return summary


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _compute_cep(x: np.ndarray, y: np.ndarray) -> float:
    """Compute the Circular Error Probable (CEP) of an impact scatter.

    CEP is the radius of the circle centred on the mean impact point that
    contains 50 % of the samples.

    For a bivariate normal distribution with equal variances σ, CEP ≈ 1.1774·σ.
    For unequal variances we use the approximation:

        CEP ≈ 0.59 · (σ_x + σ_y)

    which is accurate to < 5 % for variance ratios up to ~4:1 (RAND Corp. 1952).
    When N ≥ 20 we also compute the empirical 50th percentile of radial distances
    and return the more conservative of the two estimates.

    Parameters
    ----------
    x, y:
        1-D arrays of impact East / North coordinates (metres) relative to the
        launch pad.
    """
    if len(x) < 2:
        return 0.0

    mu_x, mu_y = np.mean(x), np.mean(y)
    sigma_x, sigma_y = np.std(x), np.std(y)

    # Analytical approximation
    cep_approx = 0.59 * (sigma_x + sigma_y)

    if len(x) >= 20:
        # Empirical 50th percentile of radial error
        radial_errors = np.sqrt((x - mu_x) ** 2 + (y - mu_y) ** 2)
        cep_empirical = float(np.percentile(radial_errors, 50))
        return max(cep_approx, cep_empirical)

    return float(cep_approx)
