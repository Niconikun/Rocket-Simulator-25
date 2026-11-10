"""STL rocket geometry importer.

Uses ``trimesh`` (optional dependency) to load an STL mesh and compute:

    - **Reference area**: projected frontal area perpendicular to the rocket axis (X)
- **Volume**: convex hull volume (used as a proxy for structural analysis)
- **Moments of inertia**: for a uniform-density solid of the given mass

If ``trimesh`` is not installed, :func:`is_available` returns ``False`` and
an :class:`ImportError` is raised when attempting to load a mesh.

Install trimesh with: pip install trimesh
Or with optional dependencies: pip install rocket-simulator-pro[stl]

Usage::

    from src.utils.stl_importer import StlImporter, is_available

    if is_available():
        imp = StlImporter("rocket.stl", mass_kg=2.5)
        result = imp.compute()
        print(result["reference_area"])   # m²
        print(result["inertia"])          # {'x': ..., 'y': ..., 'z': ...}
"""

import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    try:
        import trimesh
    except ImportError:
        trimesh = None  # type: ignore[assignment]

import numpy as np

logger = logging.getLogger(__name__)


def is_available() -> bool:
    """Return True if ``trimesh`` is installed and importable."""
    try:
        import trimesh  # noqa: F401
        return True
    except ImportError:
        return False


class StlImporter:
    """Load an STL mesh and derive rocket physical properties.

    Parameters
    ----------
    filepath:
        Path to the ``.stl`` (or any trimesh-supported mesh) file.
    mass_kg:
        Total rocket mass in kg. Required to compute moments of inertia.
    rocket_axis:
        Axis index aligned with the rocket's longitudinal axis.
        0 = X (default), 1 = Y, 2 = Z.
    """

    def __init__(
        self,
        filepath: str,
        mass_kg: float = 1.0,
        rocket_axis: int = 0,
    ) -> None:
        if not is_available():
            raise ImportError(
                "trimesh is not installed. "
                "Install it with: pip install trimesh"
            )
        if rocket_axis not in (0, 1, 2):
            raise ValueError("rocket_axis must be 0 (X), 1 (Y), or 2 (Z)")
        self.filepath = str(filepath)
        self.mass_kg = max(mass_kg, 1e-9)
        self.rocket_axis = rocket_axis

    # ------------------------------------------------------------------

    def _load_mesh(self):
        """Load the mesh via trimesh."""
        import trimesh
        mesh = trimesh.load(self.filepath, force="mesh")
        if not hasattr(mesh, "vertices") or len(mesh.vertices) == 0:
            raise ValueError(f"Could not load mesh from '{self.filepath}'")
        return mesh

    @staticmethod
    def _reference_area(mesh, axis: int) -> float:
        """Compute the projected frontal area perpendicular to ``axis``.

        This projects all vertices onto the plane perpendicular to the axis
        and returns the area of the 2-D convex hull of that projection. This
        is a silhouette area, not a sampled area of individual cross-sections.
        """
        # Project vertices onto the plane normal to `axis`
        axes = [i for i in range(3) if i != axis]
        pts_2d = mesh.vertices[:, axes]

        # 2-D convex hull area via the shoelace formula
        try:
            from scipy.spatial import ConvexHull  # type: ignore
            hull = ConvexHull(pts_2d)
            area = hull.volume  # in 2-D, ConvexHull.volume is the area
            return float(area)
        except Exception:
            # Fall back: use bounding rectangle area
            mins = pts_2d.min(axis=0)
            maxs = pts_2d.max(axis=0)
            area = float((maxs[0] - mins[0]) * (maxs[1] - mins[1]))
            # Approximate circle from rectangle: A_circle ≈ π/4 * Arect
            return area * math.pi / 4.0

    @staticmethod
    def _inertia_tensor(mesh, mass_kg: float) -> Dict[str, float]:
        """Compute moments of inertia assuming uniform density.

        Returns the principal diagonal of the inertia tensor (Ixx, Iyy, Izz)
        scaled to the given mass.

        Notes
        -----
        trimesh.inertia.mass_properties returns the inertia tensor for
        unit density. We scale by (mass / volume) to get the correct values.
        """
        volume = mesh.volume
        if volume <= 0:
            volume = mesh.convex_hull.volume

        if volume <= 0:
            # Cannot compute; fall back to thin rod approximation
            bounds = mesh.bounds  # [[xmin,ymin,zmin],[xmax,ymax,zmax]]
            dims = bounds[1] - bounds[0]
            L = float(dims.max())
            r = float(dims[dims != dims.max()].min()) / 2.0
            i_x = 0.5 * mass_kg * r ** 2
            i_yz = mass_kg * (3 * r ** 2 + L ** 2) / 12.0
            return {"x": round(i_x, 6), "y": round(i_yz, 6), "z": round(i_yz, 6)}

        density = mass_kg / volume
        # trimesh inertia tensor (3×3) computed for the mesh at unit density
        inertia_unit = mesh.moment_inertia  # already uses density=1 kg/m³
        # Scale to actual mass
        scaled = inertia_unit * density
        return {
            "x": round(float(scaled[0, 0]), 6),
            "y": round(float(scaled[1, 1]), 6),
            "z": round(float(scaled[2, 2]), 6),
        }

    # ------------------------------------------------------------------

    def compute(self) -> Dict[str, Any]:
        """Load the mesh and compute physical properties.

        Returns
        -------
        dict with keys:
            - ``reference_area`` (float): m²
            - ``inertia`` (dict): ``{x, y, z}`` in kg·m²
            - ``volume`` (float): m³ (convex hull)
            - ``bounding_box`` (dict): ``{length, diameter_max}`` in m
            - ``com_offset`` (float): centroid x-coordinate (m from mesh origin)

        Raises
        ------
        FileNotFoundError
            If the STL file does not exist.
        ValueError
            If trimesh cannot load the file.
        """
        if not Path(self.filepath).exists():
            raise FileNotFoundError(f"STL file not found: {self.filepath}")

        mesh = self._load_mesh()

        ref_area = self._reference_area(mesh, self.rocket_axis)
        inertia = self._inertia_tensor(mesh, self.mass_kg)

        # Bounding box along the rocket axis
        bounds = mesh.bounds  # shape (2, 3)
        dims = bounds[1] - bounds[0]
        length = float(dims[self.rocket_axis])
        perp_axes = [i for i in range(3) if i != self.rocket_axis]
        diameter_max = float(max(dims[perp_axes[0]], dims[perp_axes[1]]))

        # Centroid in rocket-axis direction
        centroid = mesh.centroid
        com_offset = float(centroid[self.rocket_axis])

        volume = float(mesh.convex_hull.volume)

        result: Dict[str, Any] = {
            "reference_area": round(ref_area, 6),
            "inertia": inertia,
            "volume": round(volume, 8),
            "bounding_box": {
                "length": round(length, 5),
                "diameter_max": round(diameter_max, 5),
            },
            "com_offset": round(com_offset, 5),
        }

        logger.info(
            "StlImporter: '%s' → ref_area=%.6f m², vol=%.6f m³, "
            "I=(%.4f, %.4f, %.4f) kg·m²",
            Path(self.filepath).name,
            result["reference_area"],
            result["volume"],
            inertia["x"], inertia["y"], inertia["z"],
        )
        return result
