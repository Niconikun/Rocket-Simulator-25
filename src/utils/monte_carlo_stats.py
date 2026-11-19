"""
Shared Monte Carlo statistics helpers
======================================
Single implementation of impact-point extraction and CEP used by
``MonteCarloRunner``, ``monte_carlo_process_worker`` and
``MonteCarloAggregator`` so the serial and parallel paths cannot drift apart.

- :func:`extract_impact_position` returns the (east, north) ENU impact point in
  metres, linearly interpolated at the ground crossing (altitude = 0) between
  the last two history samples.  Runs that did not end in a landing return
  ``(nan, nan)`` so aggregators can mask them out.
- :func:`compute_cep` returns the Circular Error Probable: the empirical
  50th-percentile radial error for N >= 20 samples, and the analytical
  approximation ``0.59 * (sigma_x + sigma_y)`` for smaller batches.
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np

logger = logging.getLogger(__name__)


def _is_landing(result: dict) -> bool:
    """Whether the simulation ended by reaching the ground."""
    metrics = result.get("metrics", {}) or {}
    diagnostics = metrics.get("runtime_diagnostics", {}) or {}
    reason = str(diagnostics.get("termination_reason", "") or "")
    if reason:
        return reason.startswith("LANDING")
    # Older results without diagnostics: infer from the last altitude sample
    history = result.get("history", {}) or {}
    alt = history.get("hist_alt")
    if alt:
        return float(alt[-1]) <= 0.0
    trajectory = result.get("trajectory", []) or []
    if trajectory:
        return float(trajectory[-1].get("altitude", 1.0)) <= 0.0
    return False


def _interpolate_ground_crossing(
    east: np.ndarray, north: np.ndarray, alt: np.ndarray
) -> Tuple[float, float]:
    """Linearly interpolate east/north at the altitude = 0 crossing."""
    above = np.nonzero(alt > 0.0)[0]
    if len(above) == 0 or above[-1] + 1 >= len(alt):
        return float(east[-1]), float(north[-1])
    i = int(above[-1])
    j = i + 1
    a0, a1 = float(alt[i]), float(alt[j])
    frac = 0.0 if a0 == a1 else a0 / (a0 - a1)
    x = float(east[i]) + frac * (float(east[j]) - float(east[i]))
    y = float(north[i]) + frac * (float(north[j]) - float(north[i]))
    return x, y


def extract_impact_position(result: dict) -> Tuple[float, float]:
    """Return the (east, north) ENU impact coordinates from a simulation result.

    Prefers the ``hist_east`` / ``hist_north`` / ``hist_alt`` arrays and
    interpolates the ground crossing; falls back to ``hist_r_enu`` and then to
    the lossy trajectory range (impact collapsed onto the +x axis).  Returns
    ``(nan, nan)`` when the run did not terminate by landing.
    """
    if not _is_landing(result):
        return float("nan"), float("nan")

    history = result.get("history", {}) or {}
    east = history.get("hist_east")
    north = history.get("hist_north")
    if east and north:
        alt = history.get("hist_alt")
        if alt and len(alt) == len(east) and len(east) >= 2:
            return _interpolate_ground_crossing(
                np.asarray(east, dtype=float),
                np.asarray(north, dtype=float),
                np.asarray(alt, dtype=float),
            )
        return float(east[-1]), float(north[-1])

    r_enu = history.get("hist_r_enu")
    if r_enu is not None:
        try:
            arr = np.asarray(r_enu, dtype=float)
            if arr.ndim == 2 and arr.shape[1] >= 2 and arr.shape[0] >= 2:
                if arr.shape[1] >= 3:
                    return _interpolate_ground_crossing(arr[:, 0], arr[:, 1], arr[:, 2])
                return float(arr[-1, 0]), float(arr[-1, 1])
        except Exception:
            pass

    trajectory = result.get("trajectory", []) or []
    if trajectory:
        # Lossy fallback: only total horizontal range is known, direction is lost
        return float(trajectory[-1].get("range", 0.0)), 0.0

    return float("nan"), float("nan")


def compute_cep(x: np.ndarray, y: np.ndarray) -> float:
    """Circular Error Probable in metres (50th-percentile radial error).

    For N >= 20 the empirical median radial distance from the mean impact
    point is used; for smaller batches the analytical approximation
    ``0.59 * (sigma_x + sigma_y)`` (accurate to < 5% for variance ratios up to
    ~4:1, RAND Corp. 1952) is used instead.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2:
        return 0.0

    mu_x, mu_y = float(np.mean(x)), float(np.mean(y))
    if len(x) >= 20:
        radial = np.sqrt((x - mu_x) ** 2 + (y - mu_y) ** 2)
        return float(np.percentile(radial, 50))

    return float(0.59 * (np.std(x) + np.std(y)))


def sensitivity_from_records(records: list, metric: str, min_abs_r: float = 0.0) -> dict:
    """Pearson correlation between each sampled override and a run metric.

    Parameters
    ----------
    records:
        List of per-run dicts as written to the batch JSONL, i.e. each with
        ``'overrides'`` and ``'metrics'`` sub-dicts.
    metric:
        Metric key inside ``records[i]['metrics']`` (e.g. ``'max_altitude'``).
    min_abs_r:
        Only return parameters whose |r| is at least this (0 = all).

    Returns
    -------
    dict mapping parameter name -> correlation coefficient, sorted by
    descending |r|.  (Tornado-plot ready.)
    """
    xs: dict = {}
    ys = []
    for rec in records:
        overrides = rec.get("overrides", {}) or {}
        metrics = rec.get("metrics", {}) or {}
        y = metrics.get(metric)
        if y is None or (isinstance(y, float) and np.isnan(y)):
            continue
        ys.append(float(y))
        for key, value in overrides.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                xs.setdefault(key, []).append(float(value))

    n = len(ys)
    if n < 3:
        return {}
    y_arr = np.asarray(ys, dtype=float)
    y_arr = y_arr - y_arr.mean()
    y_norm = float(np.sqrt(np.dot(y_arr, y_arr)))
    if y_norm == 0.0:
        return {}

    result = {}
    for key, values in xs.items():
        if len(values) != n:
            continue
        x_arr = np.asarray(values, dtype=float)
        x_arr = x_arr - x_arr.mean()
        x_norm = float(np.sqrt(np.dot(x_arr, x_arr)))
        if x_norm == 0.0:
            continue
        r = float(np.dot(x_arr, y_arr) / (x_norm * y_norm))
        if abs(r) >= min_abs_r:
            result[key] = r
    return dict(sorted(result.items(), key=lambda kv: abs(kv[1]), reverse=True))
