"""
Monte Carlo Aggregator
======================
Computes statistics, CEP, and dispersion-ellipse data from a completed
Monte Carlo batch.  Accepts the summary dict produced by ``MonteCarloRunner``
or a list of per-run metric dicts (e.g. loaded from a ``.jsonl`` batch file).

This module is **pure numpy / Python** — no Qt dependency — so it can be used
from both GUI and command-line contexts.

Typical usage
-------------
::

    from src.utils.monte_carlo_aggregator import MonteCarloAggregator

    # From a MonteCarloRunner summary dict
    agg = MonteCarloAggregator.from_summary(summary)

    # From a list of per-run metrics (e.g. loaded from .jsonl)
    agg = MonteCarloAggregator.from_runs(metrics_list)

    print(agg.scalar_stats("max_altitude"))
    # {'mean': 1023.4, 'std': 87.2, 'min': 812.1, 'p05': 893.0,
    #  'median': 1020.5, 'p95': 1165.3, 'max': 1243.7}

    cep = agg.cep()            # metres
    ellipse = agg.dispersion_ellipse()
    fig = agg.plot_apogee_histogram()
    fig = agg.plot_impact_scatter()
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Scalar fields that are aggregated by default
_SCALAR_KEYS = (
    "max_altitude",
    "max_velocity",
    "max_mach",
    "max_range",
    "flight_duration",
    "apogee_time",
    "max_accel_g",
)


class MonteCarloAggregator:
    """Computes and caches statistics from a Monte Carlo batch.

    Parameters
    ----------
    metrics_list:
        List of per-run metric dicts.  Each dict must contain at least some of
        the keys in ``_SCALAR_KEYS`` plus optional ``impact_x`` / ``impact_y``.
    """

    def __init__(self, metrics_list: list[dict]) -> None:
        if not metrics_list:
            raise ValueError("metrics_list must contain at least one run.")
        self._runs = metrics_list
        self._n = len(metrics_list)

        # Pre-extract arrays for fast repeated access
        self._arrays: dict[str, np.ndarray] = {}
        for key in list(_SCALAR_KEYS) + ["impact_x", "impact_y"]:
            vals = np.array(
                [r.get(key, np.nan) for r in metrics_list], dtype=float
            )
            self._arrays[key] = vals

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def from_summary(cls, summary: dict) -> "MonteCarloAggregator":
        """Build from the summary dict produced by ``MonteCarloRunner``.

        The summary must have been created with ``save_trajectory=False`` or
        the full ``statistics`` block must be present.  This factory
        reconstructs the per-run list from the raw ``output_file`` path if
        available, otherwise it synthesises stub records from the aggregated
        statistics so that ``scalar_stats()`` still works.
        """
        # Try to load the .jsonl output file for full per-run data
        output_file = summary.get("output_file", "")
        if output_file:
            try:
                import json, os
                if os.path.exists(output_file):
                    runs = []
                    with open(output_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                record = json.loads(line)
                                runs.append(record.get("metrics", record))
                    if runs:
                        return cls(runs)
            except Exception as load_err:
                logger.warning("Could not load .jsonl file: %s", load_err)

        # Fallback: reconstruct stub list from pre-computed statistics block
        stats_block = summary.get("statistics", {})
        if not stats_block:
            raise ValueError(
                "Summary contains no 'statistics' block and output_file is unavailable."
            )

        n = summary.get("n_successful", 1)
        stub: dict = {}
        for key, stat in stats_block.items():
            if isinstance(stat, dict) and "mean" in stat:
                stub[key] = stat["mean"]
        return cls([stub] * n)

    @classmethod
    def from_runs(cls, metrics_list: list[dict]) -> "MonteCarloAggregator":
        """Build directly from a list of per-run metric dicts."""
        return cls(metrics_list)

    # ------------------------------------------------------------------
    # Basic statistics
    # ------------------------------------------------------------------

    @property
    def n_runs(self) -> int:
        """Number of successful runs loaded."""
        return self._n

    def scalar_stats(self, key: str) -> dict:
        """Return descriptive statistics for one scalar metric.

        Parameters
        ----------
        key:
            Any key present in the per-run metric dicts (e.g. ``'max_altitude'``).

        Returns
        -------
        dict with keys: mean, std, min, p05, median, p95, max, n_valid
        """
        arr = self._arrays.get(key)
        if arr is None:
            arr = np.array(
                [r.get(key, np.nan) for r in self._runs], dtype=float
            )
            self._arrays[key] = arr

        valid = arr[~np.isnan(arr)]
        if len(valid) == 0:
            return {}

        return {
            "mean":    float(np.mean(valid)),
            "std":     float(np.std(valid)),
            "min":     float(np.min(valid)),
            "p05":     float(np.percentile(valid, 5)),
            "median":  float(np.median(valid)),
            "p95":     float(np.percentile(valid, 95)),
            "max":     float(np.max(valid)),
            "n_valid": int(len(valid)),
        }

    def all_scalar_stats(self) -> dict[str, dict]:
        """Return ``scalar_stats`` for every default scalar key."""
        return {k: self.scalar_stats(k) for k in _SCALAR_KEYS}

    def values(self, key: str) -> np.ndarray:
        """Raw (possibly NaN-containing) array for a given key."""
        if key not in self._arrays:
            self._arrays[key] = np.array(
                [r.get(key, np.nan) for r in self._runs], dtype=float
            )
        return self._arrays[key]

    # ------------------------------------------------------------------
    # Impact scatter
    # ------------------------------------------------------------------

    def impact_arrays(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (x, y) impact arrays with NaN pairs removed."""
        ix = self._arrays["impact_x"]
        iy = self._arrays["impact_y"]
        mask = ~(np.isnan(ix) | np.isnan(iy))
        return ix[mask], iy[mask]

    def cep(self) -> float:
        """Circular Error Probable in metres (50th-percentile radial error).

        Uses the same two-path algorithm as ``MonteCarloRunner._compute_cep``:
        analytical approximation for N < 20, empirical percentile for N ≥ 20.
        """
        ix, iy = self.impact_arrays()
        if len(ix) < 2:
            return 0.0

        mu_x, mu_y = np.mean(ix), np.mean(iy)
        cep_approx = 0.59 * (np.std(ix) + np.std(iy))

        if len(ix) >= 20:
            radial = np.sqrt((ix - mu_x) ** 2 + (iy - mu_y) ** 2)
            return float(max(cep_approx, np.percentile(radial, 50)))

        return float(cep_approx)

    def dispersion_ellipse(self, sigma_level: float = 1.0) -> dict:
        """Compute the dispersion ellipse for impact scatter.

        Parameters
        ----------
        sigma_level:
            Scale factor (1.0 = 1σ, 2.0 = 2σ, 3.0 = 3σ).

        Returns
        -------
        dict with keys:
            center_x, center_y   – ellipse centre (m)
            semi_major            – semi-major axis length (m)
            semi_minor            – semi-minor axis length (m)
            angle_deg             – rotation angle of major axis (degrees CCW from East)
            sigma_level           – the requested scale factor
            n_points              – number of valid impact points used
        """
        ix, iy = self.impact_arrays()
        n = len(ix)
        if n < 2:
            return {}

        mu_x, mu_y = float(np.mean(ix)), float(np.mean(iy))
        cov = np.cov(ix, iy)

        # Eigendecomposition
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        # Sort descending
        order = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[order]
        eigenvectors = eigenvectors[:, order]

        semi_major = float(sigma_level * np.sqrt(max(eigenvalues[0], 0.0)))
        semi_minor = float(sigma_level * np.sqrt(max(eigenvalues[1], 0.0)))

        # Angle of major axis relative to East (+x)
        vx, vy = eigenvectors[:, 0]
        angle_rad = float(np.arctan2(vy, vx))
        angle_deg = float(np.degrees(angle_rad))

        return {
            "center_x":   mu_x,
            "center_y":   mu_y,
            "semi_major":  semi_major,
            "semi_minor":  semi_minor,
            "angle_deg":   angle_deg,
            "sigma_level": sigma_level,
            "n_points":    n,
        }

    # ------------------------------------------------------------------
    # Matplotlib figures  (return Figure objects; caller embeds or shows)
    # ------------------------------------------------------------------

    def plot_apogee_histogram(
        self,
        bins: int = 30,
        color: str = "#2196F3",
        title: str = "Apogee Altitude Distribution",
    ):
        """Return a matplotlib Figure with the apogee histogram.

        Parameters
        ----------
        bins:
            Number of histogram bins.
        color:
            Bar fill colour (hex or named colour).
        title:
            Figure title.

        Returns
        -------
        matplotlib.figure.Figure
        """
        import matplotlib.pyplot as plt

        altitudes = self.values("max_altitude")
        valid = altitudes[~np.isnan(altitudes)]

        fig, ax = plt.subplots(figsize=(6, 4), tight_layout=True)
        ax.hist(valid, bins=bins, color=color, edgecolor="white", alpha=0.85)

        stats = self.scalar_stats("max_altitude")
        ax.axvline(stats["mean"],   color="#F44336", lw=1.5, ls="--", label=f"Mean  {stats['mean']:.0f} m")
        ax.axvline(stats["median"], color="#FF9800", lw=1.5, ls=":",  label=f"Median {stats['median']:.0f} m")
        ax.axvline(stats["p05"],    color="#9C27B0", lw=1.0, ls="-.", label=f"P05   {stats['p05']:.0f} m")
        ax.axvline(stats["p95"],    color="#9C27B0", lw=1.0, ls="-.", label=f"P95   {stats['p95']:.0f} m")

        ax.set_xlabel("Max Altitude (m)")
        ax.set_ylabel("Count")
        ax.set_title(title)
        ax.legend(fontsize=8)
        fig.patch.set_facecolor("#1e1e1e")
        ax.set_facecolor("#2d2d2d")
        for spine in ax.spines.values():
            spine.set_edgecolor("#555")
        ax.tick_params(colors="white")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        ax.legend(facecolor="#333", edgecolor="#555", labelcolor="white", fontsize=8)
        return fig

    def plot_impact_scatter(
        self,
        sigma_levels: tuple[float, ...] = (1.0, 2.0, 3.0),
        point_color: str = "#4CAF50",
        title: str = "Impact Scatter",
    ):
        """Return a matplotlib Figure with impact scatter + dispersion ellipses.

        Parameters
        ----------
        sigma_levels:
            Tuple of σ levels to draw ellipses for.
        point_color:
            Colour for individual impact markers.
        title:
            Figure title.

        Returns
        -------
        matplotlib.figure.Figure
        """
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import Circle, Ellipse

        ix, iy = self.impact_arrays()
        fig, ax = plt.subplots(figsize=(6, 5), tight_layout=True)

        ax.scatter(ix, iy, s=8, alpha=0.5, color=point_color, label=f"Impacts (n={len(ix)})")

        # Draw ellipses
        ellipse_colors = ["#FFD700", "#FF9800", "#F44336"]
        for level, ec in zip(sigma_levels, ellipse_colors):
            el = self.dispersion_ellipse(sigma_level=level)
            if not el:
                continue
            ellipse = Ellipse(
                xy=(el["center_x"], el["center_y"]),
                width=2 * el["semi_major"],
                height=2 * el["semi_minor"],
                angle=el["angle_deg"],
                fill=False,
                edgecolor=ec,
                linewidth=1.5,
                label=f"{level:.0f}σ ellipse",
            )
            ax.add_patch(ellipse)

        # Mark mean
        mu_x, mu_y = np.mean(ix), np.mean(iy)
        ax.plot(mu_x, mu_y, "x", color="white", ms=8, mew=2, label=f"Mean ({mu_x:.0f}, {mu_y:.0f}) m")

        # CEP circle
        cep_val = self.cep()
        circle = Circle((float(mu_x), float(mu_y)), float(cep_val), fill=False,
                        linestyle="--", color="#03A9F4", linewidth=1.2,
                        label=f"CEP = {cep_val:.0f} m")
        ax.add_patch(circle)
        ax.set_aspect("equal", adjustable="datalim")

        ax.set_xlabel("East (m)")
        ax.set_ylabel("North (m)")
        ax.set_title(title)
        ax.legend(fontsize=8)

        # Dark theme
        fig.patch.set_facecolor("#1e1e1e")
        ax.set_facecolor("#2d2d2d")
        for spine in ax.spines.values():
            spine.set_edgecolor("#555")
        ax.tick_params(colors="white")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        ax.legend(facecolor="#333", edgecolor="#555", labelcolor="white", fontsize=8)
        return fig

    def plot_metric_boxplot(
        self,
        keys: Optional[tuple[str, ...]] = None,
        title: str = "Metric Distributions",
    ):
        """Return a matplotlib Figure with side-by-side box plots for scalar metrics.

        Parameters
        ----------
        keys:
            Tuple of metric names to include.  Defaults to all scalar keys.
        title:
            Figure title.

        Returns
        -------
        matplotlib.figure.Figure
        """
        import matplotlib.pyplot as plt

        if keys is None:
            keys = _SCALAR_KEYS

        data = []
        labels = []
        for k in keys:
            vals = self.values(k)
            valid = vals[~np.isnan(vals)]
            if len(valid) > 0:
                data.append(valid)
                labels.append(k.replace("_", "\n"))

        if not data:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return fig

        fig, ax = plt.subplots(figsize=(max(6, len(data) * 1.4), 4), tight_layout=True)
        bp = ax.boxplot(data, patch_artist=True,
                        medianprops=dict(color="#F44336", linewidth=2))
        ax.set_xticklabels(labels)
        for patch in bp["boxes"]:
            patch.set_facecolor("#2196F3")
            patch.set_alpha(0.7)

        ax.set_xlabel("Metric")
        ax.set_ylabel("Value")
        ax.set_title(title)

        fig.patch.set_facecolor("#1e1e1e")
        ax.set_facecolor("#2d2d2d")
        for spine in ax.spines.values():
            spine.set_edgecolor("#555")
        ax.tick_params(colors="white")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        return fig
