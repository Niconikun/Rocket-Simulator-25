"""
Monte Carlo Parameter Sampler
==============================
Defines probability distributions for uncertain simulation inputs and
generates per-run parameter overrides compatible with SimulationWorker.run_with_params().

Usage
-----
::

    from src.utils.monte_carlo_sampler import MonteCarloSampler, ParameterConfig

    config = {
        'launch_elevation_angle': ParameterConfig('normal', nominal=85.0, sigma=1.0),
        'wind_speed_ref':         ParameterConfig('normal', nominal=5.0,  sigma=1.5,
                                                   low=0.0),
        'average_temperature':    ParameterConfig('uniform', low=18.0, high=26.0),
    }
    sampler = MonteCarloSampler(config, seed=42)
    overrides = sampler.sample()   # dict ready for run_with_params()

Supported distribution types
-----------------------------
- ``'normal'``           – Gaussian with (nominal, sigma); optionally clipped to [low, high]
- ``'truncated_normal'`` – Gaussian strictly bounded to [low, high] (rejection sampling)
- ``'uniform'``          – Uniform on [low, high]
- ``'fixed'``            – Always returns the nominal value (useful to pin a parameter)

Predefined rocket parameter sets
---------------------------------
Call ``MonteCarloSampler.from_state(state)`` to build a sampler from an
``ApplicationState`` instance using sensible default uncertainties for all
standard parameters.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Distribution type alias
# ---------------------------------------------------------------------------
DistributionType = Literal['normal', 'truncated_normal', 'uniform', 'fixed']


@dataclass
class ParameterConfig:
    """Describes the probability distribution for a single simulation parameter.

    Attributes
    ----------
    distribution:
        One of ``'normal'``, ``'truncated_normal'``, ``'uniform'``, ``'fixed'``.
    nominal:
        Central / expected value. Required for ``'normal'`` and ``'fixed'``; used
        as the mean for ``'truncated_normal'``.
    sigma:
        Standard deviation. Required for ``'normal'`` and ``'truncated_normal'``.
    low:
        Lower bound. For ``'uniform'``: left edge. For ``'normal'`` / ``'truncated_normal'``:
        hard floor (samples below this are clipped / rejected). ``None`` = no floor.
    high:
        Upper bound. For ``'uniform'``: right edge. For ``'normal'`` / ``'truncated_normal'``:
        hard ceiling. ``None`` = no ceiling.
    """

    distribution: DistributionType = 'normal'
    nominal: Optional[float] = None
    sigma: Optional[float] = None
    low: Optional[float] = None
    high: Optional[float] = None

    def __post_init__(self) -> None:
        if self.distribution in ('normal', 'truncated_normal'):
            if self.nominal is None or self.sigma is None:
                raise ValueError(
                    f"'normal'/'truncated_normal' distributions require both "
                    f"'nominal' and 'sigma'. Got nominal={self.nominal}, sigma={self.sigma}"
                )
            if self.sigma < 0:
                raise ValueError(f"sigma must be >= 0, got {self.sigma}")

        if self.distribution == 'uniform':
            if self.low is None or self.high is None:
                raise ValueError("'uniform' distribution requires both 'low' and 'high'.")
            if self.low >= self.high:
                raise ValueError(
                    f"'uniform' requires low < high, got low={self.low}, high={self.high}"
                )

        if self.distribution == 'fixed':
            if self.nominal is None:
                raise ValueError("'fixed' distribution requires 'nominal'.")


# ---------------------------------------------------------------------------
# Sampler
# ---------------------------------------------------------------------------

class MonteCarloSampler:
    """Generates parameter overrides for each Monte Carlo run.

    Parameters
    ----------
    configs:
        Mapping of ``ApplicationState`` key → ``ParameterConfig``.
    seed:
        Optional integer seed for reproducibility. Pass ``None`` for a random seed.
    max_truncation_attempts:
        Maximum rejection-sampling iterations for ``'truncated_normal'`` before
        falling back to clipping. Default is 50.
    """

    def __init__(
        self,
        configs: Dict[str, ParameterConfig],
        seed: Optional[int] = None,
        max_truncation_attempts: int = 50,
    ) -> None:
        self._configs = configs
        self._rng = np.random.default_rng(seed)
        self._max_attempts = max_truncation_attempts
        self._run_count = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sample(self) -> Dict[str, Any]:
        """Draw one sample from every configured distribution.

        Returns
        -------
        dict
            Ready to pass directly to ``SimulationWorker.run_with_params()``.
        """
        overrides: Dict[str, Any] = {}
        for key, cfg in self._configs.items():
            overrides[key] = self._draw(key, cfg)
        self._run_count += 1
        logger.debug("MC sample #%d: %s", self._run_count, overrides)
        return overrides

    def sample_batch(self, n: int) -> list[Dict[str, Any]]:
        """Draw ``n`` independent samples.

        Parameters
        ----------
        n:
            Number of samples to generate.

        Returns
        -------
        list[dict]
            List of ``n`` override dicts.
        """
        return [self.sample() for _ in range(n)]

    def reset(self, seed: Optional[int] = None) -> None:
        """Re-seed the RNG and reset the run counter."""
        self._rng = np.random.default_rng(seed)
        self._run_count = 0

    @property
    def run_count(self) -> int:
        """Number of samples drawn since construction / last reset."""
        return self._run_count

    @property
    def parameter_names(self) -> list[str]:
        """Ordered list of parameter keys this sampler produces."""
        return list(self._configs.keys())

    def summary(self) -> str:
        """Human-readable summary of all configured distributions."""
        lines = ["MonteCarloSampler configuration:"]
        for key, cfg in self._configs.items():
            if cfg.distribution == 'normal':
                bounds = ""
                if cfg.low is not None or cfg.high is not None:
                    bounds = f", clipped [{cfg.low}, {cfg.high}]"
                lines.append(
                    f"  {key}: Normal(μ={cfg.nominal}, σ={cfg.sigma}){bounds}"
                )
            elif cfg.distribution == 'truncated_normal':
                lines.append(
                    f"  {key}: TruncatedNormal(μ={cfg.nominal}, σ={cfg.sigma}, "
                    f"[{cfg.low}, {cfg.high}])"
                )
            elif cfg.distribution == 'uniform':
                lines.append(f"  {key}: Uniform([{cfg.low}, {cfg.high}])")
            elif cfg.distribution == 'fixed':
                lines.append(f"  {key}: Fixed({cfg.nominal})")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Factory – build from ApplicationState
    # ------------------------------------------------------------------

    @classmethod
    def from_state(
        cls,
        state,
        seed: Optional[int] = None,
        extra_configs: Optional[Dict[str, ParameterConfig]] = None,
    ) -> "MonteCarloSampler":
        """Build a sampler pre-configured with sensible uncertainties from a live
        ``ApplicationState`` (or ``_StateProxy``) instance.

        The nominal values are read directly from ``state.get(key)``, so the
        sampler automatically adapts to whatever rocket / location is selected.

        Parameters
        ----------
        state:
            An ``ApplicationState`` (or compatible proxy) instance.
        seed:
            Optional RNG seed.
        extra_configs:
            Additional ``{key: ParameterConfig}`` entries that override or extend
            the defaults.

        Default uncertainty budget
        --------------------------
        ======================= =============================== ============
        Parameter               Distribution                    Justification
        ======================= =============================== ============
        launch_elevation_angle  Normal, σ=1°, floor 5°         Launch-rod alignment
        launch_azimuth          Normal, σ=2°, full wrap [0,360] Compass heading error
        launch_roll             Normal, σ=1°                    Roll at ignition
        average_temperature     Normal, σ=2°C                   Forecast uncertainty
        wind_speed_ref          TruncNormal, σ=20% of nominal   Anemometer error
        wind_direction          Normal, σ=10°                   Wind vane uncertainty
        parachute_deployment_altitude  Normal, σ=10 m, floor 50 m   Altimeter error
        parachute_cd            Normal, σ=5%, floor 0.5         Manufacturing spread
        ======================= =============================== ============
        """
        configs: Dict[str, ParameterConfig] = {}

        # ---- Launch geometry ----
        elev = float(state.get('launch_elevation_angle', 85.0))
        configs['launch_elevation_angle'] = ParameterConfig(
            distribution='truncated_normal',
            nominal=elev,
            sigma=1.0,
            low=5.0,
            high=90.0,
        )

        azimuth = float(state.get('launch_azimuth', 0.0))
        configs['launch_azimuth'] = ParameterConfig(
            distribution='truncated_normal',
            nominal=azimuth,
            sigma=2.0,
            low=0.0,
            high=360.0,
        )

        roll = float(state.get('launch_roll', 0.0))
        configs['launch_roll'] = ParameterConfig(
            distribution='normal',
            nominal=roll,
            sigma=1.0,
            low=-180.0,
            high=180.0,
        )

        # ---- Atmosphere ----
        temp = float(state.get('average_temperature', 20.0))
        configs['average_temperature'] = ParameterConfig(
            distribution='normal',
            nominal=temp,
            sigma=2.0,
            low=-50.0,
            high=50.0,
        )

        # ---- Wind ----
        if state.get('wind_enabled', False):
            wind_speed = float(state.get('wind_speed_ref', 5.0))
            wind_sigma = max(0.5, wind_speed * 0.20)   # 20% of nominal, min 0.5 m/s
            configs['wind_speed_ref'] = ParameterConfig(
                distribution='truncated_normal',
                nominal=wind_speed,
                sigma=wind_sigma,
                low=0.0,
                high=None,
            )

            wind_dir = float(state.get('wind_direction', 180.0))
            configs['wind_direction'] = ParameterConfig(
                distribution='truncated_normal',
                nominal=wind_dir,
                sigma=10.0,
                low=0.0,
                high=360.0,
            )

        # ---- Parachute ----
        if state.get('parachute_enabled', False):
            deploy_alt = float(state.get('parachute_deployment_altitude', 300.0))
            configs['parachute_deployment_altitude'] = ParameterConfig(
                distribution='truncated_normal',
                nominal=deploy_alt,
                sigma=10.0,
                low=50.0,
                high=None,
            )

            para_cd = float(state.get('parachute_cd', 1.5))
            configs['parachute_cd'] = ParameterConfig(
                distribution='truncated_normal',
                nominal=para_cd,
                sigma=para_cd * 0.05,   # 5% spread
                low=0.5,
                high=None,
            )

        # Allow caller to override / add parameters
        if extra_configs:
            configs.update(extra_configs)

        return cls(configs, seed=seed)

    # ------------------------------------------------------------------
    # Internal draw logic
    # ------------------------------------------------------------------

    def _draw(self, key: str, cfg: ParameterConfig) -> float:
        """Sample a single value from the given distribution."""
        if cfg.distribution == 'fixed':
            return float(cfg.nominal)  # type: ignore[arg-type]

        if cfg.distribution == 'uniform':
            return float(self._rng.uniform(cfg.low, cfg.high))

        if cfg.distribution == 'normal':
            value = float(self._rng.normal(cfg.nominal, cfg.sigma))
            # Soft clip
            if cfg.low is not None:
                value = max(value, cfg.low)
            if cfg.high is not None:
                value = min(value, cfg.high)
            return value

        if cfg.distribution == 'truncated_normal':
            return self._truncated_normal(key, cfg)

        raise ValueError(f"Unknown distribution '{cfg.distribution}' for parameter '{key}'")

    def _truncated_normal(self, key: str, cfg: ParameterConfig) -> float:
        """Rejection-sampling implementation of truncated normal.

        Falls back to soft clipping after ``max_truncation_attempts`` iterations
        to prevent infinite loops for very tight bounds.
        """
        low = cfg.low if cfg.low is not None else -np.inf
        high = cfg.high if cfg.high is not None else np.inf

        for attempt in range(self._max_attempts):
            value = float(self._rng.normal(cfg.nominal, cfg.sigma))
            if low <= value <= high:
                return value

        # Fallback: clip to bounds
        logger.warning(
            "Truncated normal for '%s' (μ=%.3f, σ=%.3f, [%.3f, %.3f]) did not converge "
            "in %d attempts. Clipping to bounds.",
            key, cfg.nominal, cfg.sigma, low, high, self._max_attempts,
        )
        value = float(self._rng.normal(cfg.nominal, cfg.sigma))
        return float(np.clip(value, low, high))
