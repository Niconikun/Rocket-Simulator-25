"""Picklable worker function for running Monte Carlo iterations in parallel.

Executed inside separate OS processes via ``concurrent.futures.ProcessPoolExecutor``
so the CPU-bound 6-DOF physics loop bypasses the GIL and scales across cores.
Must stay import-light and free of any GUI/event-loop assumptions: only
synchronous, self-contained computation happens here.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class _FrozenState:
    """Minimal, picklable stand-in for ApplicationState inside a worker process.

    Implements the StateProvider interface for compatibility with StateProxy.
    Used by SimulationWorker/StateProxy for Monte Carlo simulations.
    """

    def __init__(self, data: dict):
        self._state = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        # Worker processes never write back to the GUI's ApplicationState.
        self._state[key] = value
    
    def get_all(self) -> dict:
        """Get the entire state dictionary."""
        return self._state.copy()


def extract_impact_position(result: dict) -> tuple[float, float]:
    """Return the (east, north) ENU impact offset in metres from the launch pad."""
    history = result.get("history", {})
    if history:
        east = history.get("hist_east")
        north = history.get("hist_north")
        if east and north:
            return float(east[-1]), float(north[-1])

        r_enu = history.get("hist_r_enu")
        if r_enu is not None:
            try:
                arr = np.asarray(r_enu)
                if arr.ndim == 2 and arr.shape[1] >= 2:
                    return float(arr[-1, 0]), float(arr[-1, 1])
            except Exception:
                pass

    # Fallback: only total horizontal range is known, direction is lost
    trajectory = result.get("trajectory", [])
    if trajectory:
        range_val = trajectory[-1].get("range", 0.0)
        return float(range_val), 0.0

    return 0.0, 0.0


def run_single_montecarlo(
    run_index: int,
    base_state_dict: dict,
    overrides: dict,
    use_cache: bool = True,
) -> dict:
    """Execute one Monte Carlo iteration in an isolated process.

    Returns a small, picklable dict: ``{'run', 'overrides', 'metrics', 'error'}``.
    Never raises — failures are reported via the ``'error'`` key so the parent
    process can keep the batch going instead of losing the whole pool.
    """
    try:
        # Deferred imports: keep module import light for the process-pool
        # bootstrap and avoid pulling in PyQt6 until a task actually runs.
        from workers.simulation_worker import SimulationWorker

        # Each worker process logs independently; keep it quiet by default.
        logging.getLogger().setLevel(logging.WARNING)

        state = _FrozenState(dict(base_state_dict))
        worker = SimulationWorker(state, use_cache=use_cache)
        result = worker.run_with_params(overrides)

        metrics = result.get("metrics", {})
        impact_x, impact_y = extract_impact_position(result)

        return {
            "run": run_index,
            "overrides": overrides,
            "error": None,
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
    except Exception as exc:  # pragma: no cover - defensive, reported to parent
        return {"run": run_index, "overrides": overrides, "error": str(exc), "metrics": None}
