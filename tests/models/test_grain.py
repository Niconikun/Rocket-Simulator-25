"""Tests for SRM grain geometries (src/models/grain.py)."""

import math

import numpy as np
import pytest

from src.models.grain import (
    BatesGrain,
    CSlotGrain,
    EndBurningGrain,
    InternalTubeGrain,
    StarGrain,
    WagonWheelGrain,
    create_grain,
    polygon_dilation_perimeter,
    star_polygon,
    wagon_wheel_polygon,
)
from src.utils.simulation_errors import InputValidationError


def _poly_perimeter(poly):
    return float(np.sum(np.hypot(*np.diff(np.vstack([poly, poly[:1]]), axis=0).T)))


class TestEndBurningGrain:
    def test_neutral_burn_constant_area(self):
        g = EndBurningGrain(diameter=0.05, length=0.2)
        expected = math.pi / 4.0 * 0.05 ** 2
        assert g.burning_surface(0.0) == pytest.approx(expected)
        assert g.burning_surface(0.1) == pytest.approx(expected)
        assert g.burning_surface(0.2) == pytest.approx(expected)

    def test_volume_and_web(self):
        g = EndBurningGrain(diameter=0.05, length=0.2)
        assert g.propellant_volume() == pytest.approx(math.pi / 4.0 * 0.05 ** 2 * 0.2)
        assert g.web_limit() == pytest.approx(0.2)
        assert g.remaining_volume(0.2) == pytest.approx(0.0, abs=1e-12)

    def test_invalid(self):
        with pytest.raises(InputValidationError):
            EndBurningGrain(diameter=0.0, length=0.2)
        with pytest.raises(InputValidationError):
            EndBurningGrain(diameter=0.05, length=-1.0)


class TestInternalTubeGrain:
    def test_area_grows_with_web(self):
        g = InternalTubeGrain(outer_diameter=0.075, core_diameter=0.03, length=0.15)
        assert g.burning_surface(0.0) == pytest.approx(math.pi * 0.03 * 0.15)
        assert g.burning_surface(0.01) == pytest.approx(math.pi * (0.03 + 0.02) * 0.15)

    def test_volume_and_web(self):
        g = InternalTubeGrain(outer_diameter=0.075, core_diameter=0.03, length=0.15)
        assert g.propellant_volume() == pytest.approx(
            math.pi / 4.0 * (0.075 ** 2 - 0.03 ** 2) * 0.15)
        assert g.web_limit() == pytest.approx((0.075 - 0.03) / 2.0)
        assert g.remaining_volume(g.web_limit()) == pytest.approx(0.0, abs=1e-12)

    def test_area_is_negative_volume_derivative(self):
        g = InternalTubeGrain(outer_diameter=0.075, core_diameter=0.03, length=0.15)
        w, dw = 0.01, 1e-6
        numeric = -(g.remaining_volume(w + dw) - g.remaining_volume(w - dw)) / (2 * dw)
        assert g.burning_surface(w) == pytest.approx(numeric, rel=1e-4)

    def test_core_must_fit(self):
        with pytest.raises(InputValidationError):
            InternalTubeGrain(outer_diameter=0.03, core_diameter=0.075, length=0.15)


class TestBatesGrain:
    def test_initial_area_closed_form(self):
        g = BatesGrain(outer_diameter=0.075, core_diameter=0.03,
                       segment_length=0.10, segments=3)
        expected = 3 * (math.pi * 0.03 * 0.10 + 0.5 * math.pi * (0.075 ** 2 - 0.03 ** 2))
        assert g.burning_surface(0.0) == pytest.approx(expected)

    def test_area_is_negative_volume_derivative(self):
        g = BatesGrain(outer_diameter=0.075, core_diameter=0.03,
                       segment_length=0.10, segments=3)
        for w in (0.002, 0.01, 0.02):
            dw = 1e-6
            numeric = -(g.remaining_volume(w + dw) - g.remaining_volume(w - dw)) / (2 * dw)
            assert g.burning_surface(w) == pytest.approx(numeric, rel=1e-4)

    def test_volume_and_web(self):
        g = BatesGrain(outer_diameter=0.075, core_diameter=0.03,
                       segment_length=0.10, segments=3)
        assert g.propellant_volume() == pytest.approx(
            3 * math.pi / 4.0 * (0.075 ** 2 - 0.03 ** 2) * 0.10)
        assert g.web_limit() == pytest.approx((0.075 - 0.03) / 2.0)
        assert g.remaining_volume(g.web_limit()) == pytest.approx(0.0, abs=1e-12)

    def test_near_neutral_profile(self):
        g = BatesGrain(outer_diameter=0.075, core_diameter=0.03,
                       segment_length=0.10, segments=3)
        ws = np.linspace(0.0, g.web_limit(), 50)
        areas = [g.burning_surface(w) for w in ws]
        assert max(areas) / min(areas) < 1.6


class TestPolygonDilationPerimeter:
    def test_square_matches_steiner(self):
        sq = np.array([[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0]])
        for w in (0.0, 0.1, 0.3):
            assert polygon_dilation_perimeter(sq, w) == pytest.approx(8.0 + 2 * math.pi * w)

    def test_disk_matches_circle(self):
        th = np.linspace(0, 2 * math.pi, 361)
        disk = np.column_stack([0.015 * np.cos(th), 0.015 * np.sin(th)])
        assert polygon_dilation_perimeter(disk, 0.0) == pytest.approx(2 * math.pi * 0.015, rel=1e-3)
        assert polygon_dilation_perimeter(disk, 0.005) == pytest.approx(2 * math.pi * 0.02, rel=1e-3)


class TestStarGrain:
    def test_initial_area_matches_polygon_perimeter(self):
        s = StarGrain(outer_diameter=0.075, length=0.15, n_points=5,
                      tip_diameter=0.03, half_angle_deg=30.0)
        per = _poly_perimeter(star_polygon(5, 0.015, 30.0))
        assert s.burning_surface(0.0) == pytest.approx(per * 0.15, rel=1e-9)

    def test_progressive_then_bounded(self):
        s = StarGrain(outer_diameter=0.075, length=0.30, n_points=5,
                      tip_diameter=0.03, half_angle_deg=35.0)
        ws = np.linspace(0.0, s.web_limit(), 30)
        areas = [s.burning_surface(w) for w in ws]
        assert all(a >= 0.0 for a in areas)
        assert max(areas) > areas[0]

    def test_volume_decreases_to_zero(self):
        s = StarGrain(outer_diameter=0.075, length=0.15, n_points=5,
                      tip_diameter=0.03, half_angle_deg=30.0)
        ws = np.linspace(0.0, s.web_limit(), 40)
        vols = [s.remaining_volume(w) for w in ws]
        assert vols[0] == pytest.approx(s.propellant_volume())
        assert all(v2 <= v1 + 1e-12 for v1, v2 in zip(vols, vols[1:]))
        assert vols[-1] < 0.02 * vols[0]

    def test_invalid_geometry(self):
        with pytest.raises(InputValidationError):
            StarGrain(outer_diameter=0.075, length=0.15, n_points=2,
                      tip_diameter=0.03, half_angle_deg=30.0)
        with pytest.raises(InputValidationError):
            StarGrain(outer_diameter=0.075, length=0.15, n_points=5,
                      tip_diameter=0.03, half_angle_deg=95.0)


class TestWagonWheelGrain:
    def test_initial_area_matches_polygon_perimeter(self):
        w = WagonWheelGrain(outer_diameter=0.075, length=0.15, n_points=4,
                            tip_diameter=0.03, valley_ratio=0.5)
        per = _poly_perimeter(wagon_wheel_polygon(4, 0.015, 0.5))
        assert w.burning_surface(0.0) == pytest.approx(per * 0.15, rel=1e-9)


class TestCSlotGrain:
    def test_slot_adds_burning_surface_over_tube(self):
        c = CSlotGrain(outer_diameter=0.075, length=0.15, core_diameter=0.03, slot_width=0.012)
        t = InternalTubeGrain(outer_diameter=0.075, core_diameter=0.03, length=0.15)
        assert c.burning_surface(0.0) > t.burning_surface(0.0)

    def test_volume_below_tube_and_full_case(self):
        c = CSlotGrain(outer_diameter=0.075, length=0.15, core_diameter=0.03, slot_width=0.012)
        t = InternalTubeGrain(outer_diameter=0.075, core_diameter=0.03, length=0.15)
        case_vol = math.pi / 4.0 * 0.075 ** 2 * 0.15
        assert c.propellant_volume() < t.propellant_volume() < case_vol


class TestCreateGrain:
    def test_dispatch_all_types(self):
        assert create_grain({'type': 'end_burning', 'diameter': 0.05, 'length': 0.2}).name == 'end_burning'
        assert create_grain({'type': 'internal_tube', 'outer_diameter': 0.075,
                             'core_diameter': 0.03, 'length': 0.15}).name == 'internal_tube'
        assert create_grain({'type': 'bates', 'outer_diameter': 0.075, 'core_diameter': 0.03,
                             'segment_length': 0.1, 'segments': 2}).name == 'bates'
        assert create_grain({'type': 'star', 'outer_diameter': 0.075, 'length': 0.15,
                             'n_points': 5, 'tip_diameter': 0.03,
                             'half_angle_deg': 30.0}).name == 'star'
        assert create_grain({'type': 'wagon_wheel', 'outer_diameter': 0.075, 'length': 0.15,
                             'n_points': 4, 'tip_diameter': 0.03}).name == 'wagon_wheel'
        assert create_grain({'type': 'c_slot', 'outer_diameter': 0.075, 'length': 0.15,
                             'core_diameter': 0.03, 'slot_width': 0.012}).name == 'c_slot'

    def test_dash_alias(self):
        g = create_grain({'type': 'c-slot', 'outer_diameter': 0.075, 'length': 0.15,
                          'core_diameter': 0.03, 'slot_width': 0.012})
        assert g.name == 'c_slot'

    def test_unknown_type_raises(self):
        with pytest.raises(InputValidationError):
            create_grain({'type': 'finocyl'})
        with pytest.raises(InputValidationError):
            create_grain({})
