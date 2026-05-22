"""
Sprint 2 – B14: Physical behaviour tests for EnhancedEngine.

Validates the unified thrust/mass_flux pipeline (B06), propellant
accumulation (B07), burnout logic (B08) and the numerically-normalised
analytical curve (B09).
"""

import pytest
import numpy as np

from src.models.engine import EnhancedEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_G0 = 9.80665


def make_engine(time=0.0, **overrides):
    """Return a minimal EnhancedEngine in **analytical** mode."""
    defaults = dict(
        time=time,
        burn_time=5.0,
        ambient_pressure=101325.0,
        nozzle_exit_diameter=0.08,
        propellant_mass=2.0,
        specific_impulse=220.0,
        mean_thrust=1000.0,
        max_thrust=1400.0,
        mean_chamber_pressure=3_000_000.0,
        max_chamber_pressure=4_000_000.0,
        thrust_to_weight_ratio=5.0,
    )
    defaults.update(overrides)
    return EnhancedEngine(**defaults)


def make_engine_experimental(time=0.0, **overrides):
    """Return an EnhancedEngine using a minimal experimental thrust dict."""
    t_pts = [0.0, 0.1, 1.0, 4.9, 5.0]
    f_pts = [0.0, 900.0, 1050.0, 980.0, 0.0]
    thrust_data = {"time": t_pts, "thrust": f_pts}
    defaults = dict(
        time=time,
        burn_time=5.0,
        ambient_pressure=101325.0,
        nozzle_exit_diameter=0.08,
        propellant_mass=2.0,
        specific_impulse=220.0,
        mean_thrust=1000.0,
        max_thrust=1400.0,
        mean_chamber_pressure=3_000_000.0,
        max_chamber_pressure=4_000_000.0,
        thrust_to_weight_ratio=5.0,
        thrust_curve_data=thrust_data,
        thrust_curve_unit="N",
    )
    defaults.update(overrides)
    return EnhancedEngine(**defaults)


# ===========================================================================
# B09 – Analytical curve normalisation
# ===========================================================================

class TestAnalyticalCurveNormalisation:
    """The analytical curve must honour mean_thrust within ±5 %."""

    def test_shape_integral_is_numeric(self):
        eng = make_engine()
        # Must not be the old hardcoded value (0.685) – should be ≥ 0.70
        assert eng._shape_integral_cached >= 0.70, (
            f"shape_integral_cached={eng._shape_integral_cached:.4f} seems wrong"
        )

    def test_validate_thrust_curve_passes(self):
        eng = make_engine()
        result = eng.validate_thrust_curve()
        assert result["valid"], (
            f"Analytical curve mean error {result['error_percent']:.2f}% exceeds 5%"
        )

    def test_mean_thrust_within_5pct(self):
        eng = make_engine()
        N = 500
        dt = eng.burn_time / N
        t_pts = np.linspace(dt / 2, eng.burn_time - dt / 2, N)
        thrusts = [eng._thrust_at_time(t) for t in t_pts]
        calc_mean = float(np.mean(thrusts))
        error_pct = abs(calc_mean - eng.mean_thrust) / eng.mean_thrust * 100
        assert error_pct < 5.0, (
            f"Analytical mean={calc_mean:.1f} N vs expected={eng.mean_thrust:.1f} N "
            f"({error_pct:.2f}% error)"
        )

    def test_thrust_does_not_exceed_max(self):
        eng = make_engine()
        t_pts = np.linspace(0.01, eng.burn_time - 0.01, 1000)
        thrusts = np.array([eng._thrust_at_time(t) for t in t_pts])
        assert float(thrusts.max()) <= eng.max_thrust + 1e-6

    def test_shape_function_zero_at_boundaries(self):
        eng = make_engine()
        assert eng._shape_function(0.0) == 0.0
        assert eng._shape_function(1.0) == 0.0
        assert eng._shape_function(-0.1) == 0.0
        assert eng._shape_function(1.1) == 0.0

    def test_shape_function_positive_inside_burn(self):
        eng = make_engine()
        for t_norm in [0.05, 0.15, 0.50, 0.70, 0.90]:
            assert eng._shape_function(t_norm) > 0.0, (
                f"shape_function({t_norm}) should be > 0"
            )


# ===========================================================================
# B06 – Unified thrust / mass_flux pipeline
# ===========================================================================

class TestUnifiedThrustMassFlux:
    """thrust and mass_flux must always satisfy T = ṁ · Isp · g0."""

    def _check_consistency(self, eng):
        if eng.thrust > 0:
            expected_flux = eng.thrust / (eng.specific_impulse * _G0)
            assert abs(eng.mass_flux - expected_flux) < 1e-9 * max(1.0, expected_flux), (
                f"mass_flux={eng.mass_flux:.6f} but thrust/Isp/g0={expected_flux:.6f}"
            )
        else:
            assert eng.mass_flux == 0.0, "mass_flux must be 0 when thrust is 0"

    def test_analytical_mid_burn(self):
        eng = make_engine(time=2.5)
        self._check_consistency(eng)

    def test_analytical_after_burnout(self):
        eng = make_engine(time=10.0)
        self._check_consistency(eng)
        assert eng.thrust == 0.0
        assert eng.mass_flux == 0.0

    def test_analytical_before_ignition(self):
        eng = make_engine(time=0.0)
        self._check_consistency(eng)
        assert eng.thrust == 0.0
        assert eng.mass_flux == 0.0

    def test_experimental_mid_burn(self):
        eng = make_engine_experimental(time=2.5)
        self._check_consistency(eng)
        assert eng.thrust > 0.0

    def test_experimental_after_burnout(self):
        eng = make_engine_experimental(time=10.0)
        self._check_consistency(eng)
        assert eng.thrust == 0.0
        assert eng.mass_flux == 0.0

    def test_consistency_after_update(self):
        eng = make_engine()
        for t in np.linspace(0.1, 5.5, 20):
            eng.update(time=t)
            self._check_consistency(eng)


# ===========================================================================
# B07 – Propellant accumulation
# ===========================================================================

class TestPropellantAccumulation:
    """Propellant consumed must increase monotonically and stay ≤ propellant_mass."""

    def test_consumed_monotonically_increases(self):
        eng = make_engine()
        prev = 0.0
        for t in np.linspace(0.01, eng.burn_time, 50):
            eng.update(time=t)
            assert eng.propellant_consumed >= prev - 1e-10, (
                f"propellant_consumed decreased at t={t:.3f}s"
            )
            prev = eng.propellant_consumed

    def test_consumed_never_exceeds_propellant_mass(self):
        eng = make_engine()
        for t in np.linspace(0.01, eng.burn_time * 2, 100):
            eng.update(time=t)
            assert eng.propellant_consumed <= eng.propellant_mass + 1e-9

    def test_remaining_is_complement(self):
        eng = make_engine()
        for t in np.linspace(0.01, eng.burn_time, 30):
            eng.update(time=t)
            expected_remaining = eng.propellant_mass - eng.propellant_consumed
            assert abs(eng.remaining_propellant - expected_remaining) < 1e-10

    def test_remaining_nonnegative(self):
        eng = make_engine()
        for t in np.linspace(0.01, eng.burn_time * 1.5, 50):
            eng.update(time=t)
            assert eng.remaining_propellant >= 0.0

    def test_zero_consumed_before_burn(self):
        eng = make_engine(time=0.0)
        assert eng.propellant_consumed == 0.0
        assert eng.remaining_propellant == eng.propellant_mass

    def test_total_impulse_monotonically_increases(self):
        eng = make_engine()
        prev = 0.0
        for t in np.linspace(0.01, eng.burn_time, 50):
            eng.update(time=t)
            assert eng.total_impulse_delivered >= prev - 1e-10
            prev = eng.total_impulse_delivered

    def test_total_impulse_at_burnout_reasonable(self):
        """Total impulse at end-of-burn must be within 20% of mean_thrust * burn_time."""
        eng = make_engine()
        eng.update(time=eng.burn_time)
        expected_impulse = eng.mean_thrust * eng.burn_time
        error_pct = abs(eng.total_impulse_delivered - expected_impulse) / expected_impulse * 100
        assert error_pct < 20.0, (
            f"total_impulse_delivered={eng.total_impulse_delivered:.1f} N·s "
            f"vs expected≈{expected_impulse:.1f} N·s ({error_pct:.1f}%)"
        )

    def test_experimental_total_impulse_reasonable(self):
        eng = make_engine_experimental()
        eng.update(time=eng.burn_time)
        expected_impulse = eng.mean_thrust * eng.burn_time
        error_pct = abs(eng.total_impulse_delivered - expected_impulse) / expected_impulse * 100
        assert error_pct < 30.0, (
            f"Experimental total impulse error {error_pct:.1f}% > 30%"
        )


# ===========================================================================
# B08 – Burnout detection
# ===========================================================================

class TestBurnoutDetection:
    """Engine must reach burnout at burn_time and stay burned-out."""

    def test_not_burned_out_during_burn(self):
        eng = make_engine(time=2.5)
        assert not eng.burnout_reached

    def test_burned_out_after_burn_time(self):
        eng = make_engine(time=6.0)
        assert eng.burnout_reached

    def test_burned_out_at_burn_time_plus_epsilon(self):
        eng = make_engine()
        eng.update(time=eng.burn_time + 1e-6)
        assert eng.burnout_reached

    def test_zero_thrust_when_burned_out(self):
        eng = make_engine(time=10.0)
        assert eng.thrust == 0.0

    def test_zero_mass_flux_when_burned_out(self):
        eng = make_engine(time=10.0)
        assert eng.mass_flux == 0.0

    def test_burnout_flag_persists(self):
        eng = make_engine()
        eng.update(time=eng.burn_time + 1.0)
        assert eng.burnout_reached
        eng.update(time=eng.burn_time + 2.0)
        assert eng.burnout_reached

    def test_remaining_propellant_zero_after_burnout(self):
        """After burn_time, remaining propellant should be ≤ a small tolerance."""
        eng = make_engine()
        eng.update(time=eng.burn_time + 0.5)
        assert eng.remaining_propellant >= 0.0
        # By design, all propellant is consumed by burn_time
        # Allow up to 5 % margin for numerical integration errors
        assert eng.propellant_consumed >= eng.propellant_mass * 0.95

    def test_experimental_burnout(self):
        eng = make_engine_experimental(time=6.0)
        assert eng.burnout_reached
        assert eng.thrust == 0.0


# ===========================================================================
# B01 contract – get_performance_metrics exposes all fields
# ===========================================================================

class TestPerformanceMetricsContract:
    """get_performance_metrics must expose the full B01 interface."""

    REQUIRED_FIELDS = {
        "thrust", "mass_flow", "specific_impulse",
        "thrust_source", "propellant_consumed",
        "remaining_propellant", "total_impulse_delivered", "burnout_reached",
    }

    def test_all_fields_present_analytical(self):
        eng = make_engine(time=2.0)
        metrics = eng.get_performance_metrics()
        for field in self.REQUIRED_FIELDS:
            assert field in metrics, f"Missing field: {field}"

    def test_all_fields_present_experimental(self):
        eng = make_engine_experimental(time=2.0)
        metrics = eng.get_performance_metrics()
        for field in self.REQUIRED_FIELDS:
            assert field in metrics, f"Missing field: {field}"

    def test_thrust_source_analytical(self):
        eng = make_engine()
        assert eng.get_performance_metrics()["thrust_source"] == "analytical"

    def test_thrust_source_experimental(self):
        eng = make_engine_experimental()
        assert eng.get_performance_metrics()["thrust_source"] == "experimental"

    def test_metrics_consistent_with_properties(self):
        eng = make_engine(time=2.5)
        m = eng.get_performance_metrics()
        assert m["thrust"] == eng.thrust
        assert m["mass_flow"] == eng.mass_flux
        assert m["propellant_consumed"] == eng.propellant_consumed
        assert m["remaining_propellant"] == eng.remaining_propellant
        assert m["burnout_reached"] == eng.burnout_reached


# ===========================================================================
# _thrust_at_time – pure-function contract
# ===========================================================================

class TestThrustAtTime:
    """_thrust_at_time must be a side-effect-free function of time."""

    def test_zero_at_t_zero(self):
        eng = make_engine()
        assert eng._thrust_at_time(0.0) == 0.0

    def test_zero_at_negative_time(self):
        eng = make_engine()
        assert eng._thrust_at_time(-1.0) == 0.0

    def test_zero_beyond_burn_time(self):
        eng = make_engine()
        assert eng._thrust_at_time(eng.burn_time + 1.0) == 0.0

    def test_positive_during_burn(self):
        eng = make_engine()
        mid = eng.burn_time / 2
        assert eng._thrust_at_time(mid) > 0.0

    def test_does_not_mutate_self_time(self):
        eng = make_engine(time=1.0)
        eng._thrust_at_time(3.0)
        assert eng.time == 1.0, "_thrust_at_time must not mutate self.time"

    def test_experimental_matches_interpolator_midburn(self):
        eng = make_engine_experimental()
        t = 1.0
        expected = float(eng.thrust_interpolator(t))
        actual   = eng._thrust_at_time(t)
        assert abs(actual - expected) < 1e-9
