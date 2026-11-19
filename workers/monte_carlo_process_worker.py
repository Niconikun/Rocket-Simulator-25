"""Picklable worker function for running Monte Carlo iterations in parallel.

Executed inside separate OS processes via ``concurrent.futures.ProcessPoolExecutor``
so the CPU-bound 6-DOF physics loop bypasses the GIL and scales across cores.
Must stay import-light and free of any GUI/event-loop assumptions: only
synchronous, self-contained computation happens here.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

import numpy as np

from src.utils.monte_carlo_stats import extract_impact_position

logger = logging.getLogger(__name__)

# For type checking only - at runtime, we use duck typing
# This avoids importing PyQt6-heavy modules during process pool bootstrap
if TYPE_CHECKING:
    from src.models.state import StateProvider


class _FrozenState:
    """Minimal, picklable stand-in for ApplicationState inside a worker process.

    Implements the StateProvider interface for compatibility with StateProxy.
    Used by SimulationWorker/StateProxy for Monte Carlo simulations.
    
    Note: This class implements the StateProvider protocol via duck typing.
    At runtime, it has all the required methods (get, set, get_all, reset).
    For type checking, we document that it's compatible with StateProvider.
    """

    def __init__(self, data: dict):
        self._state = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        # Worker processes never write back to the GUI's ApplicationState.
        self._state[key] = value
    
    def get_all(self) -> dict[str, Any]:
        """Get the entire state dictionary."""
        return self._state.copy()
    
    def reset(self) -> None:
        """Reset all state to empty."""
        self._state.clear()


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
        worker = SimulationWorker(state, use_cache=use_cache)  # type: ignore[arg-type]
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
                "landed":          not (np.isnan(impact_x) or np.isnan(impact_y)),
                "termination_reason": (metrics.get("runtime_diagnostics", {}) or {}).get(
                    "termination_reason", ""),
            },
        }
    except Exception as exc:  # pragma: no cover - defensive, reported to parent
        return {"run": run_index, "overrides": overrides, "error": str(exc), "metrics": None}
