"""OpenRocket .ork file importer.

.ork files are ZIP archives that contain an XML file describing rocket geometry
and component properties in SI units (metres, kilograms).

This module parses them and converts the data to the project's JSON config
format so they can be loaded directly by RocketSettingsWidget.

Usage::

    from src.utils.ork_importer import OrkImporter

    importer = OrkImporter("my_rocket.ork")
    config = importer.parse()          # returns dict
    importer.save_json("output.json")  # convenience wrapper
"""

import io
import math
import zipfile
import xml.etree.ElementTree as ET
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Nosecone shape name mapping: OpenRocket → project schema
# ---------------------------------------------------------------------------
_ORK_SHAPE_MAP: Dict[str, str] = {
    "OGIVE": "ogive",
    "CONICAL": "conical",
    "ELLIPSOID": "elliptical",
    "SPHERICAL": "elliptical",
    "POWER": "power",
    "PARABOLIC": "parabolic",
    "HAACK": "haack",
    "VON_KARMAN": "von_karman",
    "VONKARMAN": "von_karman",
}

_ORK_HAACK_MAP: Dict[str, str] = {
    "LD-HAACK": "LD-Haack",
    "LV-HAACK": "LV-Haack",
    "KARMAN": "LD-Haack",
}


# ---------------------------------------------------------------------------
# XML helper utilities
# ---------------------------------------------------------------------------

def _child_text(elem: ET.Element, tag: str, default: str = "") -> str:
    """Return text of the first matching child element, stripped."""
    child = elem.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return default


def _child_float(elem: ET.Element, tag: str, default: float = 0.0) -> float:
    """Return float value of a child element."""
    text = _child_text(elem, tag)
    if text:
        try:
            return float(text)
        except ValueError:
            pass
    return default


def _child_int(elem: ET.Element, tag: str, default: int = 0) -> int:
    """Return int value of a child element."""
    text = _child_text(elem, tag)
    if text:
        try:
            return int(text)
        except ValueError:
            pass
    return default


def _attr_float(elem: ET.Element, attr: str, default: float = 0.0) -> float:
    val = elem.get(attr, "")
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Component collectors
# ---------------------------------------------------------------------------

def _walk_subcomponents(parent: ET.Element) -> List[ET.Element]:
    """Recursively yield all descendant elements inside <subcomponents> tags."""
    result: List[ET.Element] = []
    sub = parent.find("subcomponents")
    if sub is None:
        return result
    for child in sub:
        result.append(child)
        result.extend(_walk_subcomponents(child))
    return result


# ---------------------------------------------------------------------------
# Main importer class
# ---------------------------------------------------------------------------

class OrkImporter:
    """Parse an OpenRocket ``.ork`` file into the project's JSON config format.

    Parameters
    ----------
    filepath:
        Path to the ``.ork`` file.
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = str(filepath)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_xml(self) -> ET.Element:
        """Open the ZIP archive and parse the XML payload."""
        with zipfile.ZipFile(self.filepath, "r") as zf:
            names = zf.namelist()
            if not names:
                raise ValueError(f"Empty archive: {self.filepath}")
            # The primary XML entry is usually the first file or has .ork extension
            xml_name = next(
                (n for n in names if n.lower().endswith(".ork")),
                names[0],
            )
            with zf.open(xml_name) as fh:
                content = fh.read()
        try:
            return ET.fromstring(content)
        except ET.ParseError as exc:
            raise ValueError(f"Failed to parse XML inside .ork file: {exc}") from exc

    def _find_rocket_element(self, root: ET.Element) -> ET.Element:
        rocket = root.find("rocket")
        if rocket is None:
            raise ValueError(
                "No <rocket> element found in the OpenRocket file. "
                "This may not be a valid .ork file."
            )
        return rocket

    # ------------------------------------------------------------------
    # Per-component extractors
    # ------------------------------------------------------------------

    def _parse_nosecone(self, elem: ET.Element) -> Dict[str, Any]:
        shape_raw = _child_text(elem, "shape", "OGIVE").upper()
        nc_len = _child_float(elem, "length")
        # OpenRocket stores aftradius (half-diameter) for nosecone
        nc_radius = _child_float(elem, "aftradius")
        # Fall back to radius attribute if present
        if nc_radius == 0.0:
            nc_radius = _child_float(elem, "radius")
        nc_diam = nc_radius * 2.0
        shape_param = _child_float(elem, "shapeparameter", 0.5)
        haack_raw = _child_text(elem, "shapetype", "LD-HAACK").upper()
        return {
            "type": shape_raw.capitalize(),
            "shape": _ORK_SHAPE_MAP.get(shape_raw, "ogive"),
            "length": round(nc_len, 5),
            "diameter": round(nc_diam, 5),
            "ogive_radius": round(nc_len * 2.0, 5),   # sensible default
            "parabolic_parameter": round(shape_param, 4),
            "power_value": round(shape_param, 4),
            "haack_type": _ORK_HAACK_MAP.get(haack_raw, "LD-Haack"),
        }

    def _parse_body_tube(self, elem: ET.Element) -> Dict[str, Any]:
        length = _child_float(elem, "length")
        radius = _child_float(elem, "radius")
        if radius == 0.0:
            radius = _child_float(elem, "aftradius")
        return {
            "length": round(length, 5),
            "diameter": round(radius * 2.0, 5),
        }

    def _parse_finset(self, elem: ET.Element) -> Dict[str, Any]:
        tag = elem.tag.lower()
        n_fins = _child_int(elem, "fincount", 3)
        root_chord = _child_float(elem, "rootchord")
        tip_chord = _child_float(elem, "tipchord")
        height = _child_float(elem, "height")   # semi-span
        sweep_len = _child_float(elem, "sweeplength")

        # Sweep angle from geometry
        if height > 0:
            sweep_angle = math.degrees(math.atan2(sweep_len, height))
        else:
            sweep_angle = 0.0

        if "elliptical" in tag:
            fin_type = "Elliptical"
            tip_chord = 0.0
            mid_chord = root_chord * 0.7
        elif "delta" in tag:
            fin_type = "Delta"
            tip_chord = 0.0
            mid_chord = root_chord * 0.5
        else:
            fin_type = "Trapezoidal"
            mid_chord = (root_chord + tip_chord) / 2.0

        return {
            "fin_type": fin_type,
            "N_fins": n_fins,
            "span": round(height, 5),
            "chord_root": round(root_chord, 5),
            "chord_tip": round(tip_chord, 5),
            "mid_chord": round(mid_chord, 5),
            "sweep_angle": round(sweep_angle, 3),
        }

    # ------------------------------------------------------------------
    # Inertia estimation
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_inertia(
        mass: float, radius: float, length: float
    ) -> Dict[str, float]:
        """Estimate moments of inertia using a thin-walled hollow cylinder.

        I_axial  = m * r²        (spin axis, x)
        I_transverse = m * (3r² + L²) / 12   (pitch/yaw, y/z)
        """
        if mass <= 0 or radius <= 0 or length <= 0:
            return {"x": 0.0, "y": 0.0, "z": 0.0}
        i_x = round(mass * radius ** 2, 6)
        i_yz = round(mass * (3.0 * radius ** 2 + length ** 2) / 12.0, 6)
        return {"x": i_x, "y": i_yz, "z": i_yz}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> Dict[str, Any]:
        """Parse the ``.ork`` file and return a project-compatible config dict.

        Returns
        -------
        dict
            Rocket configuration compatible with the project JSON schema.

        Raises
        ------
        ValueError
            If the file cannot be parsed or does not contain expected elements.
        FileNotFoundError
            If the file does not exist.
        """
        import os
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")

        root = self._load_xml()
        rocket = self._find_rocket_element(root)
        rocket_name = _child_text(rocket, "name", default="Imported Rocket")

        all_components = _walk_subcomponents(rocket)

        # ---------------------------------------------------------------
        # Categorise components
        # ---------------------------------------------------------------
        nosecone_elem: Optional[ET.Element] = None
        body_tubes: List[ET.Element] = []
        finsets: List[ET.Element] = []
        total_component_mass = 0.0

        for c in all_components:
            tag = c.tag.lower()
            if tag == "nosecone" and nosecone_elem is None:
                nosecone_elem = c
            elif tag == "bodytube":
                body_tubes.append(c)
            elif tag in (
                "trapezoidfinset",
                "ellipticalfinset",
                "freeformfinset",
                "canted finset",
                "deltafinset",
            ):
                finsets.append(c)
            # Accumulate component masses
            mass_elem = c.find("mass")
            if mass_elem is not None and mass_elem.text:
                try:
                    total_component_mass += float(mass_elem.text.strip())
                except ValueError:
                    pass

        # ---------------------------------------------------------------
        # Nosecone
        # ---------------------------------------------------------------
        nosecone: Dict[str, Any] = {
            "type": "Ogive",
            "shape": "ogive",
            "length": 0.0,
            "diameter": 0.0,
            "ogive_radius": 0.0,
            "parabolic_parameter": 0.5,
            "power_value": 0.5,
            "haack_type": "LD-Haack",
        }
        if nosecone_elem is not None:
            nosecone = self._parse_nosecone(nosecone_elem)

        # ---------------------------------------------------------------
        # Fuselage — longest body tube
        # ---------------------------------------------------------------
        fuselage: Dict[str, Any] = {"length": 0.0, "diameter": 0.0}
        if body_tubes:
            main_tube = max(body_tubes, key=lambda t: _child_float(t, "length"))
            fuselage = self._parse_body_tube(main_tube)

        # ---------------------------------------------------------------
        # Rear section — second body tube (if any)
        # ---------------------------------------------------------------
        rear_section: Dict[str, Any] = {
            "length": 0.0,
            "diameter": fuselage.get("diameter", 0.0),
        }
        if len(body_tubes) >= 2:
            others = [t for t in body_tubes
                      if t is not max(body_tubes, key=lambda x: _child_float(x, "length"))]
            if others:
                rear_section = self._parse_body_tube(others[0])

        # ---------------------------------------------------------------
        # Fins
        # ---------------------------------------------------------------
        fins: Dict[str, Any] = {
            "fin_type": "Trapezoidal",
            "N_fins": 0,
            "span": 0.0,
            "chord_root": 0.0,
            "chord_tip": 0.0,
            "mid_chord": 0.0,
            "sweep_angle": 0.0,
        }
        if finsets:
            fins = self._parse_finset(finsets[0])

        # ---------------------------------------------------------------
        # Geometry
        # ---------------------------------------------------------------
        nc_len = nosecone.get("length", 0.0)
        fus_len = fuselage.get("length", 0.0)
        rear_len = rear_section.get("length", 0.0)
        total_length = round(nc_len + fus_len + rear_len, 5)
        len_nc_fins = round(nc_len + fus_len, 5)

        geometry: Dict[str, Any] = {
            "total length": total_length,
            "length nosecone fins": len_nc_fins,
            "total_length": total_length,
            "length_nosecone_fins": len_nc_fins,
        }

        # ---------------------------------------------------------------
        # Masses
        # ---------------------------------------------------------------
        # Prefer override mass on the rocket element; fall back to sum
        override_text = _child_text(rocket, "overridemass")
        try:
            initial_mass = float(override_text) if override_text else 0.0
        except ValueError:
            initial_mass = 0.0

        if initial_mass <= 0.0:
            initial_mass = total_component_mass if total_component_mass > 0.0 else 1.0

        initial_mass = round(initial_mass, 4)

        # ---------------------------------------------------------------
        # Reference area (from fuselage or nosecone diameter)
        # ---------------------------------------------------------------
        ref_diam = fuselage.get("diameter", nosecone.get("diameter", 0.0))
        if ref_diam > 0.0:
            reference_area = round(math.pi * (ref_diam / 2.0) ** 2, 6)
        else:
            reference_area = 0.0

        # ---------------------------------------------------------------
        # Inertia estimation
        # ---------------------------------------------------------------
        inertia = self._estimate_inertia(
            mass=initial_mass,
            radius=ref_diam / 2.0 if ref_diam > 0.0 else 0.05,
            length=total_length if total_length > 0.0 else 1.0,
        )
        com_x = round(total_length * 0.45, 5)
        com = {"x": com_x, "y": 0.0, "z": 0.0}

        # ---------------------------------------------------------------
        # Engine (empty — user fills manually or from thrust curve)
        # ---------------------------------------------------------------
        engine: Dict[str, Any] = {
            "burn_time": 0.0,
            "propellant_mass": 0.0,
            "specific_impulse": 0.0,
            "mean_thrust": 0.0,
            "max_thrust": 0.0,
            "nozzle_exit_diameter": 0.0,
            "mass_flux": 0.0,
            "gas_speed": 0.0,
            "exit_pressure": 0.0,
            "mean_chamber_pressure": 0.0,
            "max_chamber_pressure": 0.0,
            "thrust_to_weight_ratio": 0.0,
        }

        # ---------------------------------------------------------------
        # Assemble final config
        # ---------------------------------------------------------------
        config: Dict[str, Any] = {
            "name": rocket_name,
            "initial_mass": initial_mass,
            "propellant_mass": 0.0,
            "dry_mass_kg": initial_mass,
            "reference_area": reference_area,
            "I_before_burn": inertia,
            "CoM_before_burn": com,
            "I_after_burn": inertia,
            "CoM_after_burn": com,
            "engine": engine,
            "geometry": geometry,
            "fuselage": fuselage,
            "rear_section": rear_section,
            "nosecone": nosecone,
            "fins": fins,
        }

        logger.info(
            "OrkImporter: parsed '%s' — mass=%.3f kg, total_length=%.3f m, "
            "ref_area=%.6f m²",
            rocket_name, initial_mass, total_length, reference_area,
        )
        return config

    def save_json(self, output_path: str) -> None:
        """Parse the ``.ork`` file and save the result as a JSON config.

        Parameters
        ----------
        output_path:
            Destination ``.json`` file path.
        """
        config = self.parse()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=4, ensure_ascii=False)
        logger.info("OrkImporter: saved config to '%s'", output_path)
