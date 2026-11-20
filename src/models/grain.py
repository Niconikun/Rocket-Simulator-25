# Author: Rocket Simulator Team
#         Solid Rocket Motor (SRM) grain design module

"""
Solid rocket motor grain geometries (Nakka-style design methods).

Each grain exposes the three quantities needed by the internal-ballistics
solver in ``src.models.solid_motor``:

- ``burning_surface(web)``: burning surface area Ab [m^2] after a web
  thickness ``web`` [m] has burned.  For parallel burning surfaces
  Ab = -dV/dw exactly.
- ``remaining_volume(web)``: propellant volume left [m^3].
- ``propellant_volume()``: initial propellant volume [m^3].
- ``web_limit()``: web thickness at burnout [m].

Implemented geometries (the classic configurations recommended by
R. Nakka, http://www.nakka-rocketry.net):

- ``EndBurningGrain``   - "cigarette" burning, neutral (Ab = const)
- ``InternalTubeGrain`` - cylindrical core, ends inhibited (progressive)
- ``BatesGrain``        - segmented core-burning grain with burning ends
                          (near-neutral), closed-form 3-D areas
- ``StarGrain``         - star cross-section (progressive then regressive),
                          evaluated on a 2-D erosion grid
- ``WagonWheelGrain``   - wagon-wheel cross-section (same grid method)
- ``CSlotGrain``         - C-slot cross-section (same grid method)

The prismatic cross-section grains (star, wagon-wheel, C-slot) use the exact
set erosion ``core ⊕ disk(web)`` computed on a raster via the Euclidean
distance transform; ``burning_surface`` is obtained from ``-dV/dw`` so it
stays consistent with the remaining volume by construction.

References:
    - Nakka, R. "Solid Rocket Motor Design" (nakka-rocketry.net)
    - Sutton, G. P., & Biblarz, O. (2016). Rocket Propulsion Elements.
"""

import logging
from abc import ABC, abstractmethod
from math import cos, pi, radians, sin
from typing import Callable, Optional

import numpy as np
from scipy.ndimage import distance_transform_edt

from src.utils.simulation_errors import InputValidationError

logger = logging.getLogger(__name__)


class GrainGeometry(ABC):
    """Abstract grain cross-section / 3-D geometry.

    All lengths in SI (m, m^2, m^3).  ``web`` is the burned web thickness
    measured normal to the initial burning surface.
    """

    name: str = "grain"
    #: Whether the grain ends burn (BATES) or are inhibited (star, C-slot...)
    ends_burn: bool = False

    @abstractmethod
    def burning_surface(self, web: float) -> float:
        """Burning surface area Ab(web) [m^2], web in [0, web_limit()]."""

    @abstractmethod
    def remaining_volume(self, web: float) -> float:
        """Remaining propellant volume [m^3] after ``web`` has burned."""

    @abstractmethod
    def propellant_volume(self) -> float:
        """Initial propellant volume [m^3] (web = 0)."""

    @abstractmethod
    def web_limit(self) -> float:
        """Web thickness at burnout [m]."""

    def validate_web(self, web: float) -> float:
        """Clamp ``web`` to the valid range [0, web_limit()]."""
        return float(np.clip(web, 0.0, self.web_limit()))


class EndBurningGrain(GrainGeometry):
    """Cigarette / end-burning grain: neutral burn, Ab = pi/4 * D^2."""

    name = "end_burning"
    ends_burn = True

    def __init__(self, diameter: float, length: float):
        if diameter <= 0 or length <= 0:
            raise InputValidationError("End-burning grain needs diameter > 0 and length > 0")
        self.diameter = float(diameter)
        self.length = float(length)

    def burning_surface(self, web: float) -> float:
        return pi / 4.0 * self.diameter ** 2

    def remaining_volume(self, web: float) -> float:
        w = self.validate_web(web)
        return pi / 4.0 * self.diameter ** 2 * max(0.0, self.length - w)

    def propellant_volume(self) -> float:
        return pi / 4.0 * self.diameter ** 2 * self.length

    def web_limit(self) -> float:
        return self.length


class InternalTubeGrain(GrainGeometry):
    """Cylindrical core grain (tube).  Ends inhibited unless ``ends_burn``.

    Ab(web) = pi * (Di + 2w) * L  (+ pi/2 * (Di + 2w)^2 per burning end pair)
    """

    name = "internal_tube"

    def __init__(self, outer_diameter: float, core_diameter: float, length: float,
                 ends_burn: bool = False):
        if outer_diameter <= 0 or length <= 0:
            raise InputValidationError("Tube grain needs outer_diameter > 0 and length > 0")
        if not 0 < core_diameter < outer_diameter:
            raise InputValidationError("Tube grain needs 0 < core_diameter < outer_diameter")
        self.outer_diameter = float(outer_diameter)
        self.core_diameter = float(core_diameter)
        self.length = float(length)
        self.ends_burn = bool(ends_burn)

    def _core_d(self, web: float) -> float:
        return self.core_diameter + 2.0 * self.validate_web(web)

    def burning_surface(self, web: float) -> float:
        dc = self._core_d(web)
        ab = pi * dc * self.length
        if self.ends_burn:
            ab += 0.5 * pi * dc ** 2
        return ab

    def remaining_volume(self, web: float) -> float:
        dc = self._core_d(web)
        return pi / 4.0 * (self.outer_diameter ** 2 - dc ** 2) * self.length

    def propellant_volume(self) -> float:
        return pi / 4.0 * (self.outer_diameter ** 2 - self.core_diameter ** 2) * self.length

    def web_limit(self) -> float:
        return (self.outer_diameter - self.core_diameter) / 2.0


class BatesGrain(GrainGeometry):
    """BATES grain: N cylindrical segments, core and both ends burn.

    Per segment, with core diameter Dc = Di + 2w and receded length L - 2w:
        Ab_seg(w) = pi * Dc * (L - 2w) + pi/2 * (Do^2 - Dc^2)
    Near-neutral profile because the core (progressive) and end (regressive)
    surfaces roughly compensate.
    """

    name = "bates"
    ends_burn = True

    def __init__(self, outer_diameter: float, core_diameter: float,
                 segment_length: float, segments: int = 1):
        if outer_diameter <= 0 or segment_length <= 0:
            raise InputValidationError("BATES grain needs outer_diameter > 0 and segment_length > 0")
        if not 0 < core_diameter < outer_diameter:
            raise InputValidationError("BATES grain needs 0 < core_diameter < outer_diameter")
        if segments < 1:
            raise InputValidationError("BATES grain needs segments >= 1")
        self.outer_diameter = float(outer_diameter)
        self.core_diameter = float(core_diameter)
        self.segment_length = float(segment_length)
        self.segments = int(segments)

    def _core_d(self, web: float) -> float:
        return self.core_diameter + 2.0 * self.validate_web(web)

    def burning_surface(self, web: float) -> float:
        w = self.validate_web(web)
        dc = self._core_d(w)
        length = max(0.0, self.segment_length - 2.0 * w)
        ab_seg = pi * dc * length + 0.5 * pi * (self.outer_diameter ** 2 - dc ** 2)
        return self.segments * max(0.0, ab_seg)

    def remaining_volume(self, web: float) -> float:
        w = self.validate_web(web)
        dc = self._core_d(w)
        length = max(0.0, self.segment_length - 2.0 * w)
        return self.segments * pi / 4.0 * (self.outer_diameter ** 2 - dc ** 2) * length

    def propellant_volume(self) -> float:
        return (self.segments * pi / 4.0
                * (self.outer_diameter ** 2 - self.core_diameter ** 2)
                * self.segment_length)

    def web_limit(self) -> float:
        return (self.outer_diameter - self.core_diameter) / 2.0


def _points_in_polygon(X: np.ndarray, Y: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """Vectorized ray-casting point-in-polygon test."""
    inside = np.zeros(X.shape, dtype=bool)
    m = len(poly)
    j = m - 1
    for i in range(m):
        xi, yi = poly[i]
        xj, yj = poly[j]
        cond = ((yi > Y) != (yj > Y)) & (X < (xj - xi) * (Y - yi) / (yj - yi) + xi)
        inside ^= cond
        j = i
    return inside


def star_polygon(n_points: int, tip_radius: float, half_angle_deg: float) -> np.ndarray:
    """Nakka star polygon: n points, tip radius, edge half-angle theta.

    Each straight edge leaves the tip at angle theta from the radial line;
    valleys are the intersections of adjacent edges.  Returns an (2n, 2)
    vertex array ordered tip, valley, tip, valley, ...
    """
    if n_points < 3:
        raise InputValidationError("Star grain needs at least 3 points")
    if not 1.0 < half_angle_deg < 89.0:
        raise InputValidationError("Star half-angle must be in (1, 89) degrees")
    theta = radians(half_angle_deg)
    tips = [tip_radius * np.array([cos(2 * pi * i / n_points),
                                   sin(2 * pi * i / n_points)])
            for i in range(n_points)]
    verts = []
    for i in range(n_points):
        t0 = tips[i]
        t1 = tips[(i + 1) % n_points]
        phi0 = 2 * pi * i / n_points
        phi1 = 2 * pi * (i + 1) / n_points
        d0 = np.array([cos(phi0 + pi - theta), sin(phi0 + pi - theta)])
        d1 = np.array([cos(phi1 + pi + theta), sin(phi1 + pi + theta)])
        det = d0[0] * d1[1] - d0[1] * d1[0]
        if abs(det) < 1e-12:
            raise InputValidationError("Star geometry degenerate: edges are parallel")
        rhs = t1 - t0
        s = (rhs[0] * d1[1] - rhs[1] * d1[0]) / det
        valley = t0 + s * d0
        verts.append(t0)
        verts.append(valley)
    return np.array(verts)


def wagon_wheel_polygon(n_points: int, tip_radius: float, valley_ratio: float = 0.5) -> np.ndarray:
    """Wagon-wheel polygon: 2n alternating tip/valley vertices (straight edges)."""
    if n_points < 3:
        raise InputValidationError("Wagon-wheel grain needs at least 3 points")
    if not 0.0 < valley_ratio < 1.0:
        raise InputValidationError("Wagon-wheel valley_ratio must be in (0, 1)")
    rv = tip_radius * valley_ratio
    verts = []
    for i in range(n_points):
        phi_tip = 2 * pi * i / n_points
        phi_val = phi_tip + pi / n_points
        verts.append(tip_radius * np.array([cos(phi_tip), sin(phi_tip)]))
        verts.append(rv * np.array([cos(phi_val), sin(phi_val)]))
    return np.array(verts)


def polygon_dilation_perimeter(poly: np.ndarray, web: float) -> float:
    """Exact perimeter of ``polygon ⊕ disk(web)`` (outward dilation).

    Round joins at convex vertices (arcs of radius ``web``), miter joins at
    reflex vertices.  Valid while no offset edge vanishes; beyond that the
    clamped edge lengths approximate the collapsed shape (near burnout).
    """
    v = np.asarray(poly, dtype=float)
    e = np.roll(v, -1, axis=0) - v
    l = np.hypot(e[:, 0], e[:, 1])
    e_prev = np.roll(e, 1, axis=0)
    cross = e_prev[:, 0] * e[:, 1] - e_prev[:, 1] * e[:, 0]
    dot = e_prev[:, 0] * e[:, 0] + e_prev[:, 1] * e[:, 1]
    tau = np.arctan2(cross, dot)
    t_reflex = np.minimum(np.tan(tau / 2.0), 0.0)
    l_off = np.maximum(l + web * (t_reflex + np.roll(t_reflex, -1)), 0.0)
    arcs = float(np.where(tau > 0, web * tau, 0.0).sum())
    return float(l_off.sum()) + arcs


class PrismaticGrain(GrainGeometry):
    """Prismatic grain (extruded 2-D cross-section) with inhibited ends.

    The core cross-section is given either as a polygon (star, wagon-wheel)
    or as a boolean mask function (C-slot).  The burned core after web ``w``
    is the exact dilation ``core ⊕ disk(w)`` evaluated on a raster through
    the Euclidean distance transform.  A volume-vs-web table is precomputed
    once and ``burning_surface`` is ``-dV/dw`` of that table (smoothed), so
    area and volume stay consistent by construction.
    """

    name = "prismatic"

    def __init__(self, outer_diameter: float, length: float,
                 polygon: Optional[np.ndarray] = None,
                 core_mask_fn: Optional[Callable[[np.ndarray, np.ndarray], np.ndarray]] = None,
                 resolution: int = 256, ends_burn: bool = False):
        if outer_diameter <= 0 or length <= 0:
            raise InputValidationError("Prismatic grain needs outer_diameter > 0 and length > 0")
        if polygon is None and core_mask_fn is None:
            raise InputValidationError("Prismatic grain needs a polygon or a core_mask_fn")
        if resolution < 32:
            raise InputValidationError("Prismatic grain resolution must be >= 32")
        self.outer_diameter = float(outer_diameter)
        self.length = float(length)
        self.ends_burn = bool(ends_burn)
        ro = self.outer_diameter / 2.0
        n = int(resolution)
        h = 2.0 * ro / n
        xs = (np.arange(n) + 0.5) * h - ro
        X, Y = np.meshgrid(xs, xs)
        case = (X ** 2 + Y ** 2) <= ro ** 2
        if polygon is not None:
            poly = np.asarray(polygon, dtype=float)
            if np.max(np.hypot(poly[:, 0], poly[:, 1])) >= ro:
                raise InputValidationError("Grain core must fit inside the outer diameter")
            core = _points_in_polygon(X, Y, poly)
        else:
            core = np.asarray(core_mask_fn(X, Y), dtype=bool)
        core &= case
        if not core.any():
            raise InputValidationError("Grain core cross-section is empty")
        dist = distance_transform_edt(~core, sampling=h)
        dist_b = np.maximum(dist - 0.5 * h, 0.0)
        self._h = h
        self._case_area = float(case.sum()) * h * h
        self._w_max = float(dist_b[case].max())
        if self._w_max <= 0.0:
            raise InputValidationError("Grain web limit must be positive")

        n_grid = max(64, int(np.ceil(self._w_max / h)) + 1)
        w_grid = np.linspace(0.0, self._w_max, n_grid)
        rem = case[None, :, :] & (dist_b[None, :, :] > w_grid[:, None, None])
        v_grid = rem.sum(axis=(1, 2)) * h * h * self.length
        self._w_grid = w_grid
        self._v_grid = v_grid
        self._v0 = float(v_grid[0])
        ab_grid = -np.gradient(v_grid, w_grid)
        window = min(9, len(w_grid) // 2 * 2 - 1)
        if window >= 5:
            from scipy.signal import savgol_filter
            ab_grid = savgol_filter(ab_grid, window, 3)
        self._ab_grid = np.maximum(ab_grid, 0.0)

    def burning_surface(self, web: float) -> float:
        w = self.validate_web(web)
        ab = float(np.interp(w, self._w_grid, self._ab_grid))
        if self.ends_burn:
            v_rem = float(np.interp(w, self._w_grid, self._v_grid))
            ab += 2.0 * max(0.0, self._case_area - v_rem / self.length)
        return ab

    def remaining_volume(self, web: float) -> float:
        return float(np.interp(self.validate_web(web), self._w_grid, self._v_grid))

    def propellant_volume(self) -> float:
        return self._v0

    def web_limit(self) -> float:
        return self._w_max


class PolygonGrain(PrismaticGrain):
    """Prismatic grain whose core is a polygon: exact analytic Ab(web).

    Volume and web limit still come from the raster (exact mass), while the
    burning surface uses the exact polygon-dilation perimeter so the
    progressive/regressive profile of star-like grains is not distorted by
    raster discretization.
    """

    def __init__(self, outer_diameter: float, length: float, polygon: np.ndarray,
                 resolution: int = 256, ends_burn: bool = False):
        self._polygon = np.asarray(polygon, dtype=float)
        super().__init__(outer_diameter, length, polygon=self._polygon,
                         resolution=resolution, ends_burn=ends_burn)

    def burning_surface(self, web: float) -> float:
        w = self.validate_web(web)
        ab = polygon_dilation_perimeter(self._polygon, w) * self.length
        if self.ends_burn:
            v_rem = float(np.interp(w, self._w_grid, self._v_grid))
            ab += 2.0 * max(0.0, self._case_area - v_rem / self.length)
        return ab


class StarGrain(PolygonGrain):
    """Star grain (Nakka): n points, tip diameter, edge half-angle theta."""

    name = "star"

    def __init__(self, outer_diameter: float, length: float, n_points: int,
                 tip_diameter: float, half_angle_deg: float,
                 resolution: int = 256, ends_burn: bool = False):
        if not 0 < tip_diameter < outer_diameter:
            raise InputValidationError("Star grain needs 0 < tip_diameter < outer_diameter")
        poly = star_polygon(int(n_points), tip_diameter / 2.0, float(half_angle_deg))
        super().__init__(outer_diameter, length, poly,
                         resolution=resolution, ends_burn=ends_burn)
        self.n_points = int(n_points)
        self.tip_diameter = float(tip_diameter)
        self.half_angle_deg = float(half_angle_deg)


class WagonWheelGrain(PolygonGrain):
    """Wagon-wheel grain: n square-ish points, valley radius ratio."""

    name = "wagon_wheel"

    def __init__(self, outer_diameter: float, length: float, n_points: int,
                 tip_diameter: float, valley_ratio: float = 0.5,
                 resolution: int = 256, ends_burn: bool = False):
        if not 0 < tip_diameter < outer_diameter:
            raise InputValidationError("Wagon-wheel grain needs 0 < tip_diameter < outer_diameter")
        poly = wagon_wheel_polygon(int(n_points), tip_diameter / 2.0, float(valley_ratio))
        super().__init__(outer_diameter, length, poly,
                         resolution=resolution, ends_burn=ends_burn)
        self.n_points = int(n_points)
        self.tip_diameter = float(tip_diameter)
        self.valley_ratio = float(valley_ratio)


class CSlotGrain(PrismaticGrain):
    """C-slot grain: circular core plus a slot of given width open to the case."""

    name = "c_slot"

    def __init__(self, outer_diameter: float, length: float,
                 core_diameter: float, slot_width: float,
                 resolution: int = 320, ends_burn: bool = False):
        if not 0 < core_diameter < outer_diameter:
            raise InputValidationError("C-slot grain needs 0 < core_diameter < outer_diameter")
        if slot_width <= 0:
            raise InputValidationError("C-slot grain needs slot_width > 0")
        ro = outer_diameter / 2.0
        rc = core_diameter / 2.0
        half_w = slot_width / 2.0

        def mask_fn(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
            disk = (X ** 2 + Y ** 2) <= rc ** 2
            slot = (X >= 0.0) & (X <= ro) & (np.abs(Y) <= half_w)
            return disk | slot

        super().__init__(outer_diameter, length, core_mask_fn=mask_fn,
                         resolution=resolution, ends_burn=ends_burn)
        self.core_diameter = float(core_diameter)
        self.slot_width = float(slot_width)


GRAIN_TYPES = {
    'end_burning': EndBurningGrain,
    'internal_tube': InternalTubeGrain,
    'bates': BatesGrain,
    'star': StarGrain,
    'wagon_wheel': WagonWheelGrain,
    'c_slot': CSlotGrain,
}


def create_grain(config: dict) -> GrainGeometry:
    """Build a grain geometry from a configuration dict.

    Expected keys: ``type`` plus type-specific dimensions:

    - end_burning:   diameter, length
    - internal_tube: outer_diameter, core_diameter, length, ends_burn
    - bates:         outer_diameter, core_diameter, segment_length, segments
    - star:          outer_diameter, length, n_points, tip_diameter, half_angle_deg
    - wagon_wheel:   outer_diameter, length, n_points, tip_diameter, valley_ratio
    - c_slot:        outer_diameter, length, core_diameter, slot_width
    """
    if not isinstance(config, dict) or 'type' not in config:
        raise InputValidationError("Grain config must be a dict with a 'type' key")
    gtype = str(config.get('type', '')).lower().replace('-', '_')
    if gtype not in GRAIN_TYPES:
        raise InputValidationError(
            f"Unknown grain type {config.get('type')!r}; "
            f"valid types: {sorted(GRAIN_TYPES)}"
        )
    cls = GRAIN_TYPES[gtype]
    kwargs = {k: v for k, v in config.items() if k != 'type'}
    try:
        return cls(**kwargs)
    except TypeError as exc:
        raise InputValidationError(f"Invalid parameters for grain type {gtype!r}: {exc}") from exc


__all__ = [
    'GrainGeometry',
    'EndBurningGrain',
    'InternalTubeGrain',
    'BatesGrain',
    'PrismaticGrain',
    'StarGrain',
    'WagonWheelGrain',
    'CSlotGrain',
    'PolygonGrain',
    'star_polygon',
    'wagon_wheel_polygon',
    'polygon_dilation_perimeter',
    'GRAIN_TYPES',
    'create_grain',
]
