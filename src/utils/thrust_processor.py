"""
Thrust Curve Processor
======================
Single point of ingestion, validation and normalisation of experimental thrust curves.

Contract
--------
- All thrust values returned are in Newtons.
- Time arrays always start at 0.0 [s].
- The unit of the thrust column MUST be declared explicitly in the engine configuration
  via ``thrust_curve_unit`` ('N' or 'kgf').  No implicit conversion is performed.
- A :class:`ThrustCurveError` is raised on any structural or physical violation so that
  the simulation loop never receives a corrupt curve.

Public API
----------
``ThrustCurveProcessor.from_csv(file_path, unit)``   → :class:`ThrustCurveData`
``ThrustCurveProcessor.from_dict(raw_dict, unit)``   → :class:`ThrustCurveData`
``ThrustCurveProcessor.validate_impulse_consistency(data, propellant_mass, isp)`` → dict
"""

import logging
from dataclasses import dataclass, field
from typing import List

import numpy as np
import pandas as pd

from src.utils.simulation_constants import EngineConstants as EC

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_UNITS = ('N', 'kgf')
KGF_TO_N = EC.STANDARD_GRAVITY_G0

# Minimum thrust value accepted before raising an error.
# Small negative readings are common sensor noise and are clipped to 0 by the
# processor.  Values more negative than this floor indicate a data problem.
NEGATIVE_THRUST_TOLERANCE_N = -5.0


# ---------------------------------------------------------------------------
# Public exceptions and data structures
# ---------------------------------------------------------------------------

class ThrustCurveError(ValueError):
    """Raised when a thrust curve fails structural or physical validation."""


@dataclass
class ThrustCurveData:
    """
    Processed and validated thrust curve ready for use by :class:`EnhancedEngine`.

    All physical values are in SI units (seconds, Newtons).

    Attributes
    ----------
    time_s : List[float]
        Time array normalised to start at 0 [s].
    thrust_N : List[float]
        Thrust array in Newtons [N].  Non-negative (noise floor clipped to 0).
    duration : float
        Total burn duration [s].
    max_thrust : float
        Peak thrust [N].
    mean_thrust : float
        Mean thrust over the burn = total_impulse / duration [N].
    total_impulse : float
        Integral of thrust over time [N·s].
    n_points : int
        Number of data points.
    source : str
        File path or ``'dict'``.
    unit_declared : str
        Unit as declared by the caller ('N' or 'kgf').
    validation : dict
        Summary metrics produced during processing.
    """
    time_s: List[float]
    thrust_N: List[float]
    duration: float
    max_thrust: float
    mean_thrust: float
    total_impulse: float
    n_points: int
    source: str
    unit_declared: str
    validation: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Processor
# ---------------------------------------------------------------------------

class ThrustCurveProcessor:
    """
    Single point of ingestion, validation and normalisation for experimental
    thrust curves.

    All methods are class-methods or static-methods; no instantiation needed.

    Usage
    -----
    ::

        data   = ThrustCurveProcessor.from_csv('load_cell_1.csv', unit='kgf')
        data   = ThrustCurveProcessor.from_dict({'time': [...], 'thrust': [...]}, unit='N')
        report = ThrustCurveProcessor.validate_impulse_consistency(data, 1.5, 106.25)
    """

    # Recognised column-name synonyms (matched case-insensitively after strip)
    _TIME_SYNONYMS   = ('time', 'tiempo', 't')
    _THRUST_SYNONYMS = ('thrust', 'force', 'fuerza', 'empuje', 'f')

    # ------------------------------------------------------------------
    # Public class-methods
    # ------------------------------------------------------------------

    @classmethod
    def from_csv(cls, file_path: str, unit: str) -> ThrustCurveData:
        """
        Load and validate a thrust curve from a CSV file.

        Parameters
        ----------
        file_path : str
            Absolute or relative path to the CSV file.
        unit : str
            Declared unit of the thrust column.  Must be ``'N'`` or ``'kgf'``.

        Returns
        -------
        ThrustCurveData
            Processed curve with all values in SI units.

        Raises
        ------
        ThrustCurveError
            On any structural or physical violation.
        """
        cls._validate_unit(unit)
        try:
            df = pd.read_csv(file_path)
        except FileNotFoundError:
            raise ThrustCurveError(
                f"Thrust curve file not found: '{file_path}'. "
                "Check the 'thrust_curve_file' path in the engine configuration."
            )
        except Exception as exc:
            raise ThrustCurveError(
                f"Could not read CSV '{file_path}': {exc}"
            ) from exc
        return cls._process_dataframe(df, unit=unit, source=file_path)

    @classmethod
    def from_dict(cls, raw: dict, unit: str) -> ThrustCurveData:
        """
        Load and validate a thrust curve from a pre-loaded dictionary.

        Parameters
        ----------
        raw : dict
            Dictionary with at least two keys whose names match the recognised
            time and thrust synonyms (e.g. ``{'time': [...], 'thrust': [...]}``
            or ``{'Tiempo': [...], 'Fuerza': [...]}``)
        unit : str
            Declared unit of the thrust values.  Must be ``'N'`` or ``'kgf'``.

        Returns
        -------
        ThrustCurveData

        Raises
        ------
        ThrustCurveError
        """
        cls._validate_unit(unit)
        try:
            df = pd.DataFrame(raw)
        except Exception as exc:
            raise ThrustCurveError(
                f"Could not build DataFrame from provided dict: {exc}"
            ) from exc
        return cls._process_dataframe(df, unit=unit, source='dict')

    @staticmethod
    def validate_impulse_consistency(
        data: ThrustCurveData,
        propellant_mass: float,
        isp: float,
        tolerance: float = 0.20,
    ) -> dict:
        """
        Check that the measured total impulse is consistent with propellant
        mass and nominal specific impulse.

        Parameters
        ----------
        data : ThrustCurveData
            Processed curve from :meth:`from_csv` or :meth:`from_dict`.
        propellant_mass : float
            Expected propellant mass [kg].
        isp : float
            Nominal specific impulse [s].
        tolerance : float
            Allowed fractional error (default ``0.20`` = 20 %).

        Returns
        -------
        dict
            Keys: ``valid``, ``impulse_error_percent``, ``measured_impulse``,
            ``expected_impulse``, ``measured_avg_thrust``, ``expected_avg_thrust``.
        """
        g0 = EC.STANDARD_GRAVITY_G0
        expected_impulse = propellant_mass * isp * g0
        if expected_impulse <= 0.0:
            impulse_error = 0.0 if data.total_impulse <= 0.0 else 1.0
        else:
            impulse_error = abs(data.total_impulse - expected_impulse) / expected_impulse

        report = {
            'valid': impulse_error <= tolerance,
            'impulse_error_percent': round(impulse_error * 100, 2),
            'measured_impulse': round(data.total_impulse, 2),
            'expected_impulse': round(expected_impulse, 2),
            'measured_avg_thrust': round(data.mean_thrust, 2),
            'expected_avg_thrust': round(expected_impulse / data.duration, 2) if data.duration > 0 else 0.0,
        }

        if not report['valid']:
            logger.warning(
                "Impulse consistency check FAILED: measured %.1f N·s, "
                "expected %.1f N·s (%.1f%% error > %.0f%% tolerance)",
                data.total_impulse, expected_impulse,
                impulse_error * 100, tolerance * 100,
            )
        else:
            logger.info(
                "Impulse consistency check PASSED: %.1f%% error within %.0f%% tolerance",
                impulse_error * 100, tolerance * 100,
            )

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_unit(unit: str) -> None:
        if unit not in SUPPORTED_UNITS:
            raise ThrustCurveError(
                f"Invalid thrust_curve_unit '{unit}'. "
                f"Must be one of: {SUPPORTED_UNITS}. "
                "Set 'thrust_curve_unit' explicitly in the rocket engine configuration."
            )

    @classmethod
    def _detect_columns(cls, df: pd.DataFrame, source: str):
        """Return ``(time_col, thrust_col)`` or raise :class:`ThrustCurveError`."""
        time_col = thrust_col = None
        for col in df.columns:
            lower = col.lower().strip()
            if lower in cls._TIME_SYNONYMS:
                time_col = col
            elif lower in cls._THRUST_SYNONYMS:
                thrust_col = col
        if time_col is None or thrust_col is None:
            raise ThrustCurveError(
                f"Could not identify time and thrust columns in '{source}'. "
                f"Columns found: {list(df.columns)}. "
                f"Expected a time column from {cls._TIME_SYNONYMS} and "
                f"a thrust column from {cls._THRUST_SYNONYMS}."
            )
        return time_col, thrust_col

    @classmethod
    def _process_dataframe(
        cls, df: pd.DataFrame, unit: str, source: str
    ) -> ThrustCurveData:
        """Core pipeline: clean → validate structure → convert units → compute metrics."""

        # 1. Detect columns
        time_col, thrust_col = cls._detect_columns(df, source)

        # 2. Coerce to numeric, drop non-parseable rows
        df = df[[time_col, thrust_col]].copy()
        df[time_col]   = pd.to_numeric(df[time_col],   errors='coerce')
        df[thrust_col] = pd.to_numeric(df[thrust_col], errors='coerce')
        n_before = len(df)
        df = df.dropna()
        n_dropped = n_before - len(df)
        if n_dropped:
            logger.warning(
                "Dropped %d non-numeric row(s) from thrust curve '%s'.",
                n_dropped, source,
            )

        # 3. Minimum length guard
        if len(df) < 2:
            raise ThrustCurveError(
                f"Thrust curve '{source}' has fewer than 2 valid data points "
                "after cleaning non-numeric rows."
            )

        time_raw   = np.asarray(df[time_col].values.copy(), dtype=np.float64)
        thrust_raw = np.asarray(df[thrust_col].values.copy(), dtype=np.float64)

        # 4. Structural validations (B03)
        cls._check_time_monotonic(time_raw, source)
        cls._check_positive_duration(time_raw, source)
        cls._check_thrust_floor(thrust_raw, source, unit)

        # 5. Normalise time to start at 0
        time_s = time_raw - time_raw[0]

        # 6. Unit conversion – explicit only, no heuristic (B04)
        if unit == 'kgf':
            thrust_N = thrust_raw * KGF_TO_N
            logger.info(
                "Thrust curve '%s': converted from kgf -> N (×%.5f).", source, KGF_TO_N
            )
        else:  # unit == 'N'
            thrust_N = thrust_raw.copy()

        # 7. Clip residual negative values at noise floor to 0
        thrust_N = np.clip(thrust_N, 0.0, None)

        # 8. Derived metrics
        duration     = float(time_s[-1])
        max_thrust   = float(np.max(thrust_N))
        total_impulse = float(np.trapz(thrust_N, time_s))
        mean_thrust  = total_impulse / duration if duration > 0 else 0.0

        validation = {
            'n_points': int(len(time_s)),
            'n_dropped': int(n_dropped),
            'duration_s': round(duration, 4),
            'max_thrust_N': round(max_thrust, 2),
            'total_impulse_Ns': round(total_impulse, 2),
            'mean_thrust_N': round(mean_thrust, 2),
            'unit_declared': unit,
            'source': source,
        }

        logger.info(
            "Thrust curve loaded: source='%s', unit=%s, n_points=%d, "
            "duration=%.3fs, max_thrust=%.1fN, total_impulse=%.1fN·s",
            source, unit, len(time_s), duration, max_thrust, total_impulse,
        )

        return ThrustCurveData(
            time_s=time_s.tolist(),
            thrust_N=thrust_N.tolist(),
            duration=duration,
            max_thrust=max_thrust,
            mean_thrust=mean_thrust,
            total_impulse=total_impulse,
            n_points=int(len(time_s)),
            source=source,
            unit_declared=unit,
            validation=validation,
        )

    # ------------------------------------------------------------------
    # Structural checks (B03)
    # ------------------------------------------------------------------

    @staticmethod
    def _check_time_monotonic(time_array: np.ndarray[np.float64], source: str) -> None:
        diffs = np.diff(time_array)
        bad = np.where(diffs <= 0)[0]
        if len(bad):
            idx = int(bad[0])
            raise ThrustCurveError(
                f"Thrust curve '{source}': time is not strictly increasing at "
                f"row {idx + 1} "
                f"(t[{idx}]={time_array[idx]:.4f}, t[{idx+1}]={time_array[idx+1]:.4f}). "
                "Ensure rows are in chronological order and free of duplicates."
            )

    @staticmethod
    def _check_positive_duration(time_array: np.ndarray[np.float64], source: str) -> None:
        duration = time_array[-1] - time_array[0]
        if duration <= 0:
            raise ThrustCurveError(
                f"Thrust curve '{source}': computed duration is {duration:.4f}s "
                "(must be > 0)."
            )

    @staticmethod
    def _check_thrust_floor(
        thrust_array: np.ndarray[np.float64], source: str, unit: str
    ) -> None:
        """Validate minimum raw thrust value before unit conversion."""
        # Convert floor to declared unit for comparison
        floor = (
            NEGATIVE_THRUST_TOLERANCE_N / KGF_TO_N
            if unit == 'kgf'
            else NEGATIVE_THRUST_TOLERANCE_N
        )
        min_val = float(np.min(thrust_array))
        if min_val < floor:
            raise ThrustCurveError(
                f"Thrust curve '{source}': minimum thrust value {min_val:.2f} {unit} "
                f"is below the allowed noise floor ({floor:.2f} {unit}). "
                "Check that the correct column was selected and that the data is valid."
            )