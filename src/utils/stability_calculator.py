"""Barrowman static stability calculator for the Rocket Simulator.

Computes the centre of pressure (CP) and static stability margin using the
classical Barrowman method (J. S. Barrowman, 1967).  All inputs are in SI
units (metres); helpers are provided to convert from the mm-based widget
values before calling :func:`compute_stability`.

Reference
---------
Barrowman, J. S. (1967). *The Practical Calculation of the Aerodynamic
Characteristics of Slender Finned Vehicles*. Thesis, Catholic University
of America.

Stability classification (following common model-rocketry conventions)
-----------------------------------------------------------------------
+------------------+----------------+
| Margin (calibres)| Category       |
+==================+================+
| < 0              | UNSTABLE       |
| 0 – 1            | MARGINAL       |
| 1 – 2            | STABLE         |
| > 2              | OVER-STABLE    |
+------------------+----------------+
"""

import math
from typing import Dict, Any

__all__ = ["compute_stability", "StabilityResult"]


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

class StabilityResult:
    """Container for Barrowman stability results.

    Attributes
    ----------
    xcp : float
        Total centre of pressure from nose tip [m].
    cn_alpha_nose : float
        Normal-force-coefficient derivative for the nosecone.
    cn_alpha_fins : float
        Normal-force-coefficient derivative for the fins.
    margin_calibers_before : float
        Stability margin in calibres before propellant burn.
    margin_calibers_after : float
        Stability margin in calibres after propellant burn.
    ref_diameter : float
        Body diameter used as calibre reference [m].
    category : str
        Human-readable stability classification.
    """

    _THRESHOLDS = [
        (2.0,  "OVER-STABLE"),
        (1.0,  "STABLE"),
        (0.0,  "MARGINAL"),
        (-1e9, "UNSTABLE"),
    ]

    def __init__(
        self,
        xcp: float,
        cn_alpha_nose: float,
        cn_alpha_fins: float,
        margin_calibers_before: float,
        margin_calibers_after: float,
        ref_diameter: float,
    ) -> None:
        self.xcp = xcp
        self.cn_alpha_nose = cn_alpha_nose
        self.cn_alpha_fins = cn_alpha_fins
        self.margin_calibers_before = margin_calibers_before
        self.margin_calibers_after = margin_calibers_after
        self.ref_diameter = ref_diameter

    @property
    def category(self) -> str:
        """Worst-case category (minimum of before/after margins)."""
        worst = min(self.margin_calibers_before, self.margin_calibers_after)
        for threshold, label in self._THRESHOLDS:
            if worst >= threshold:
                return label
        return "UNSTABLE"

    @property
    def color(self) -> str:
        """Qt-compatible CSS colour string for the stability category."""
        return {
            "STABLE":      "#4caf50",   # green
            "OVER-STABLE": "#2196f3",   # blue
            "MARGINAL":    "#ff9800",   # orange
            "UNSTABLE":    "#f44336",   # red
        }.get(self.category, "#ffffff")

    def summary_lines(self) -> list:
        """Return a list of human-readable summary strings."""
        return [
            f"Centre of Pressure (from nose): {self.xcp:.4f} m",
            "",
            f"  CNα nosecone : {self.cn_alpha_nose:.3f}",
            f"  CNα fins     : {self.cn_alpha_fins:.3f}",
            f"  Calibre (d)  : {self.ref_diameter*1000:.1f} mm",
            "",
            f"  Stability margin (before burn): "
            f"{self.margin_calibers_before:+.2f} cal",
            f"  Stability margin (after burn) : "
            f"{self.margin_calibers_after:+.2f} cal",
            "",
            f"  Classification: {self.category}",
        ]


# ---------------------------------------------------------------------------
# Nosecone CP factors (fraction of nose length)
# ---------------------------------------------------------------------------

_NOSE_CP_FRACTION: Dict[str, float] = {
    "ogive":       0.466,
    "conical":     0.333,
    "elliptical":  0.333,
    "parabolic":   0.500,
    "power":       0.500,
    "haack":       0.437,
    "von_karman":  0.437,
}

_DEFAULT_NOSE_FRACTION = 0.466  # ogive fallback


def _nose_cp_fraction(nose_shape: str) -> float:
    return _NOSE_CP_FRACTION.get(nose_shape.lower().strip(), _DEFAULT_NOSE_FRACTION)


# ---------------------------------------------------------------------------
# Core Barrowman functions
# ---------------------------------------------------------------------------

def _barrowman_nose(nose_length: float) -> float:
    """Return Barrowman CNα for the nosecone (always 2.0)."""
    return 2.0  # exact Barrowman result for any slender nosecone


def _barrowman_fins(
    n: int,
    span: float,
    chord_root: float,
    chord_tip: float,
    mid_chord: float,
    body_diameter: float,
) -> float:
    """Barrowman CNα for a single trapezoidal finset.

    Parameters (all in metres)
    --------------------------
    n            : number of fins
    span         : semi-span (fin height) [m]
    chord_root   : root chord [m]
    chord_tip    : tip chord [m]
    mid_chord    : mid chord (used for aspect ratio estimation) [m]
    body_diameter: body outer diameter at fin attachment [m]
    """
    if n == 0 or span <= 0 or body_diameter <= 0:
        return 0.0

    d = body_diameter
    s = span
    cr = chord_root
    ct = chord_tip

    # Tip chord guard
    if ct < 0:
        ct = 0.0

    # Fin aspect ratio (span-based)
    mean_chord = (cr + ct) / 2.0 if (cr + ct) > 0 else mid_chord
    if mean_chord <= 0:
        return 0.0

    AR = (2.0 * s) / mean_chord   # planform aspect ratio

    # Body interference factor
    K_B = 1.0 + d / (2.0 * s + d)   # Barrowman interference correction

    # CNα per fin group (Barrowman 1967, eq. 3.29)
    denom = 1.0 + math.sqrt(1.0 + (2.0 * s / (cr + ct)) ** 2)
    cn_alpha = K_B * (4.0 * n * (s / d) ** 2) / denom

    return cn_alpha


def _fin_cp_axial(
    chord_root: float,
    chord_tip: float,
    mid_chord: float,
    fin_leading_edge_from_nose: float,
) -> float:
    """Barrowman axial CP position for trapezoidal fins [m from nose tip]."""
    cr = chord_root
    ct = chord_tip if chord_tip >= 0 else 0.0
    mc = mid_chord

    if (cr + ct) <= 0:
        return fin_leading_edge_from_nose + mc / 3.0

    # Barrowman eq. 3.30 — axial offset from fin leading-edge root
    x_local = (
        mc / 3.0 * (cr + 2.0 * ct) / (cr + ct)
        + 1.0 / 6.0 * (cr + ct - cr * ct / (cr + ct))
    )

    return fin_leading_edge_from_nose + x_local


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_stability(
    *,
    nose_length_m: float,
    nose_shape: str,
    body_diameter_m: float,
    fin_n: int,
    fin_span_m: float,
    fin_chord_root_m: float,
    fin_chord_tip_m: float,
    fin_mid_chord_m: float,
    fin_position_from_nose_m: float,
    com_before_m: float,
    com_after_m: float,
) -> StabilityResult:
    """Compute Barrowman CP and stability margins.

    All length parameters must be in **metres**.

    Parameters
    ----------
    nose_length_m            : Nosecone length [m]
    nose_shape               : Shape key (e.g. ``"ogive"``, ``"conical"``)
    body_diameter_m          : Fuselage outer diameter [m]
    fin_n                    : Number of fins
    fin_span_m               : Fin semi-span (height) [m]
    fin_chord_root_m         : Root chord [m]
    fin_chord_tip_m          : Tip chord [m]
    fin_mid_chord_m          : Mid chord [m]
    fin_position_from_nose_m : Axial position of fin leading-edge root
                               from nose tip [m]
    com_before_m             : Centre of mass before burn [m]
    com_after_m              : Centre of mass after burn [m]

    Returns
    -------
    StabilityResult
    """
    # Barrowman normal-force-coefficient derivatives
    cn_nose = _barrowman_nose(nose_length_m)
    cn_fins = _barrowman_fins(
        n=fin_n,
        span=fin_span_m,
        chord_root=fin_chord_root_m,
        chord_tip=fin_chord_tip_m,
        mid_chord=fin_mid_chord_m,
        body_diameter=body_diameter_m,
    )

    # Axial CP positions
    cp_nose = _nose_cp_fraction(nose_shape) * nose_length_m
    cp_fins = _fin_cp_axial(
        chord_root=fin_chord_root_m,
        chord_tip=fin_chord_tip_m,
        mid_chord=fin_mid_chord_m,
        fin_leading_edge_from_nose=fin_position_from_nose_m,
    )

    # Total CP (weighted average)
    cn_total = cn_nose + cn_fins
    if cn_total <= 0:
        # Cannot compute — return CP at nose
        xcp = cp_nose
    else:
        xcp = (cn_nose * cp_nose + cn_fins * cp_fins) / cn_total

    # Stability margins in calibres
    if body_diameter_m <= 0:
        d_ref = 0.10  # 10 cm fallback
    else:
        d_ref = body_diameter_m

    margin_before = (xcp - com_before_m) / d_ref
    margin_after = (xcp - com_after_m) / d_ref

    return StabilityResult(
        xcp=round(xcp, 5),
        cn_alpha_nose=round(cn_nose, 4),
        cn_alpha_fins=round(cn_fins, 4),
        margin_calibers_before=round(margin_before, 3),
        margin_calibers_after=round(margin_after, 3),
        ref_diameter=round(d_ref, 5),
    )
