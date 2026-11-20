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
from src.models.state import StateProvider
from typing import Optional

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

from src.config import Paths, Constants
from src.utils.monte_carlo_sampler import MonteCarloSampler, ParameterConfig
from src.utils.monte_carlo_stats import extract_impact_position, compute_cep
from workers.simulation_worker import SimulationWorker
from workers.simulation_cache import get_cache, clear_cache, SimulationCache

logger = logging.getLogger(__name__)


def _output_dir() -> str:
    """Directory where batch output files are written (CWD-independent)."""
    Paths.ensure_dirs()
    return str(Paths.MONTE_CARLO_DIR)


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
    n_workers:
        Number of OS processes to run simulations in parallel with
        ``concurrent.futures.ProcessPoolExecutor``.  ``1`` (default) keeps the
        original single-process, single-thread behaviour.
    use_cache:
        Reuse cached Planet/Atmosphere/wind model objects across runs.
    clear_cache_before:
        When ``True`` (default) the global simulation cache — shared with the
        normal GUI simulation — is cleared at batch start.
    """

    # ---- Qt signals -------------------------------------------------------
    run_completed = pyqtSignal(int, dict)   # (run_index, metrics_dict)
    run_failed    = pyqtSignal(int, str)    # (run_index, reason)
    progress      = pyqtSignal(int)         # 0-100
    finished      = pyqtSignal(dict)        # batch summary
    error         = pyqtSignal(str)         # fatal error

    def __init__(
        self,
        state: StateProvider,
        n_runs: int = 100,
        seed: Optional[int] = None,
        sampler_configs: Optional[dict] = None,
        save_trajectory: bool = False,
        use_cache: bool = True,
        clear_cache_before: bool = True,
        n_workers: int = 1,
    ) -> None:
        super().__init__()
        self._state = state
        self._n_runs = max(1, n_runs)
        self._seed = seed
        self._sampler_configs = sampler_configs
        self._save_trajectory = save_trajectory
        self._use_cache = use_cache
        self._clear_cache_before = clear_cache_before
        self._n_workers = max(1, n_workers)

        self._is_running = False
        self._batch_id: str = ""
        self._cache: Optional[SimulationCache] = None

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

        # Initialize cache if enabled
        if self._use_cache:
            if self._clear_cache_before:
                clear_cache()
            self._cache = get_cache()
            logger.info("Simulation cache enabled for Monte Carlo batch")

        # Build sampler
        sampler = MonteCarloSampler.from_state(
            self._state,
            seed=self._seed,
            extra_configs=self._sampler_configs,
        )
        logger.info(sampler.summary())

        # Prepare output file
        output_path = os.path.join(_output_dir(), f"{self._batch_id}.jsonl")

        # Batch accumulators
        successful: list[dict] = []
        failed_runs: list[int] = []

        try:
            with open(output_path, "w", encoding="utf-8") as out_file:
                if self._n_workers > 1 and self._n_runs > 1:
                    self._run_parallel(sampler, out_file, successful, failed_runs)
                else:
                    self._run_serial(sampler, out_file, successful, failed_runs)

        except Exception as fatal:
            logger.error("Fatal error in Monte Carlo batch: %s", fatal, exc_info=True)
            self.error.emit(str(fatal))
            return

        # Build and emit summary
        cache_stats = None
        if self._cache is not None:
            cache_stats = self._cache.stats.to_dict()
            logger.info(f"Cache stats: {cache_stats}")
        
        summary = self._build_summary(
            batch_id=self._batch_id,
            n_requested=self._n_runs,
            successful=successful,
            failed_runs=failed_runs,
            output_path=output_path,
            sampler_summary=sampler.summary(),
            cache_stats=cache_stats,
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
        
        # Clear rocket object cache to free memory (keep configs and other objects)
        if self._cache is not None:
            self._cache.clear_rockets()
        
        self.finished.emit(summary)

    # ------------------------------------------------------------------
    # Execution strategies
    # ------------------------------------------------------------------

    @staticmethod
    def _mirror_wind_speed_override(overrides: dict) -> None:
        """Keep 'wind_speed' and 'wind_speed_ref' in sync in-place.

        wind_utils.create_wind_model_from_state() prefers the legacy
        'wind_speed' key over 'wind_speed_ref' when both exist in the base
        ApplicationState, which would silently shadow this run's sampled
        wind speed. Mirroring the value keeps both keys in agreement.
        """
        if 'wind_speed_ref' in overrides:
            overrides['wind_speed'] = overrides['wind_speed_ref']

    def _apply_gust_seed(self, sampler: MonteCarloSampler, overrides: dict) -> None:
        """Give gust wind models a fresh random realization per run, in-place.

        GustWind is stateful (Dryden filter) and would otherwise reuse the
        same realization for every run when 'random_seed' is fixed in state.
        The per-run seed also makes the wind cache key unique per run, so no
        two runs share a wind model object.
        """
        if not self._state.get(Constants.StateKeys.WIND_ENABLED, False):
            return
        if 'random_seed' in overrides:
            return
        model_type = self._state.get(
            Constants.StateKeys.WIND_MODEL_TYPE, self._state.get('model_type', 'logarithmic'))
        if str(model_type).lower() == 'gust':
            overrides['random_seed'] = sampler.draw_seed()

    def _record_result(
        self,
        run_index: int,
        metrics: dict,
        overrides: dict,
        out_file,
        successful: list[dict],
    ) -> None:
        run_record = {"run": run_index, "overrides": overrides, "metrics": metrics}
        out_file.write(json.dumps(run_record) + "\n")
        out_file.flush()
        successful.append(metrics)
        self.run_completed.emit(run_index, metrics)

    def _run_serial(self, sampler, out_file, successful: list[dict], failed_runs: list[int]) -> None:
        """Original single-process execution path (one run after another)."""
        worker = SimulationWorker(self._state, use_cache=self._use_cache)

        for i in range(self._n_runs):
            if not self._is_running:
                logger.info("Monte Carlo batch cancelled at run %d.", i)
                break

            overrides = sampler.sample()
            self._mirror_wind_speed_override(overrides)
            self._apply_gust_seed(sampler, overrides)
            logger.debug("Run %d/%d overrides: %s", i + 1, self._n_runs, overrides)

            try:
                result = worker.run_with_params(overrides)
                metrics = result.get("metrics", {})
                impact_x, impact_y = extract_impact_position(result)
                metrics_out = {
                    "max_altitude":    metrics.get("max_altitude", 0.0),
                    "max_velocity":    metrics.get("max_velocity", 0.0),
                    "max_mach":        metrics.get("max_mach", 0.0),
                    "max_range":       metrics.get("max_range", 0.0),
                    "flight_duration": metrics.get("flight_duration", 0.0),
                    "apogee_time":     metrics.get("apogee_time", 0.0),
                    "max_accel_g":     metrics.get("max_accel_g", 0.0),
                    "max_q":           metrics.get("max_q", 0.0),
                    "touchdown_velocity": metrics.get("touchdown_velocity", 0.0),
                    "impact_x":        impact_x,
                    "impact_y":        impact_y,
                    "landed":          not (np.isnan(impact_x) or np.isnan(impact_y)),
                    "termination_reason": (metrics.get("runtime_diagnostics", {}) or {}).get(
                        "termination_reason", ""),
                }
                self._record_result(i, metrics_out, overrides, out_file, successful)
            except Exception as run_err:
                reason = str(run_err)
                logger.warning("Run %d failed: %s", i + 1, reason)
                failed_runs.append(i)
                self.run_failed.emit(i, reason)

            self.progress.emit(int((i + 1) / self._n_runs * 100))

    def _run_parallel(self, sampler, out_file, successful: list[dict], failed_runs: list[int]) -> None:
        """Run simulations across multiple OS processes via ProcessPoolExecutor.

        Samples are still drawn sequentially in this (parent) process so the
        RNG sequence stays reproducible for a given seed; only the expensive
        physics integration itself is distributed across workers.
        """
        from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
        from workers.monte_carlo_process_worker import run_single_montecarlo

        base_state_dict = self._state.get_all()
        n_workers = min(self._n_workers, self._n_runs)
        completed = 0
        submitted = 0
        in_flight: dict = {}

        logger.info("Running Monte Carlo batch across %d parallel worker processes", n_workers)

        with ProcessPoolExecutor(max_workers=n_workers) as executor:

            def _submit_next() -> bool:
                nonlocal submitted
                if submitted >= self._n_runs or not self._is_running:
                    return False
                overrides = sampler.sample()
                self._mirror_wind_speed_override(overrides)
                self._apply_gust_seed(sampler, overrides)
                fut = executor.submit(
                    run_single_montecarlo, submitted, base_state_dict, overrides, self._use_cache
                )
                in_flight[fut] = submitted
                submitted += 1
                return True

            # Keep a bounded pipeline of in-flight tasks so memory stays capped
            # for very large batches while still saturating all worker processes.
            for _ in range(min(self._n_runs, n_workers * 2)):
                _submit_next()

            while in_flight:
                done, _ = wait(in_flight.keys(), return_when=FIRST_COMPLETED)
                for fut in done:
                    idx = in_flight.pop(fut)
                    completed += 1
                    try:
                        record = fut.result()
                    except Exception as exc:
                        record = {"run": idx, "overrides": {}, "error": str(exc), "metrics": None}

                    if record.get("error") is not None or record.get("metrics") is None:
                        reason = record.get("error") or "unknown error"
                        logger.warning("Run %d failed: %s", idx + 1, reason)
                        failed_runs.append(idx)
                        self.run_failed.emit(idx, reason)
                    else:
                        self._record_result(
                            idx, record["metrics"], record["overrides"], out_file, successful
                        )

                    self.progress.emit(int(completed / self._n_runs * 100))
                    _submit_next()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_summary(
        batch_id: str,
        n_requested: int,
        successful: list[dict],
        failed_runs: list[int],
        output_path: str,
        sampler_summary: str,
        cache_stats: Optional[dict] = None,
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
        
        # Add cache statistics if provided
        if cache_stats:
            summary["cache_stats"] = cache_stats

        if not successful:
            return summary

        # Scalar metrics to aggregate
        scalar_keys = [
            "max_altitude", "max_velocity", "max_mach",
            "max_range", "flight_duration", "apogee_time",
            "max_accel_g", "max_q", "touchdown_velocity",
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
            cep = compute_cep(ix, iy)
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
