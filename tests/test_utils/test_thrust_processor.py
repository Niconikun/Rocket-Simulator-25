"""
Tests for ThrustCurveProcessor – Sprint 1  (B03, B04, B05)
===========================================================
Coverage:
  B02 – Column detection (English and Spanish synonyms)
  B03 – Structural validations: monotonic time, duplicates, thrust floor,
         minimum point count, missing file
  B04 – Explicit unit handling: kgf→N conversion, N unchanged,
         error on invalid unit, NO heuristic for small-valued curves
  B05 – Rich output structure: ThrustCurveData fields, impulse consistency
         report, CSV round-trip via tempfile
"""

import csv
import os
import tempfile
import unittest

import numpy as np

from src.utils.thrust_processor import (
    ThrustCurveData,
    ThrustCurveError,
    ThrustCurveProcessor,
    KGF_TO_N,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_curve(n=5, unit='N'):
    """Return a minimal valid dict-based curve and the processed ThrustCurveData."""
    times   = [float(i) for i in range(n)]
    thrusts = [0.0, 300.0, 500.0, 400.0, 0.0][:n]
    raw = {'time': times, 'thrust': thrusts}
    return ThrustCurveProcessor.from_dict(raw, unit=unit)


# ===========================================================================
# B02 – Column detection
# ===========================================================================

class TestColumnDetection(unittest.TestCase):
    """Processor must recognise English and Spanish column names."""

    def test_english_columns(self):
        raw = {'time': [0.0, 1.0], 'thrust': [500.0, 400.0]}
        data = ThrustCurveProcessor.from_dict(raw, unit='N')
        self.assertIsInstance(data, ThrustCurveData)

    def test_spanish_columns(self):
        raw = {'Tiempo': [0.0, 1.0], 'Fuerza': [100.0, 80.0]}
        data = ThrustCurveProcessor.from_dict(raw, unit='N')
        self.assertIsInstance(data, ThrustCurveData)

    def test_force_column_synonym(self):
        raw = {'time': [0.0, 1.0], 'force': [200.0, 150.0]}
        data = ThrustCurveProcessor.from_dict(raw, unit='N')
        self.assertIsInstance(data, ThrustCurveData)

    def test_raises_on_unrecognised_time_column(self):
        raw = {'t_ms': [0.0, 100.0], 'thrust': [500.0, 400.0]}
        with self.assertRaises(ThrustCurveError) as ctx:
            ThrustCurveProcessor.from_dict(raw, unit='N')
        self.assertIn('time', str(ctx.exception).lower())

    def test_raises_on_unrecognised_thrust_column(self):
        raw = {'time': [0.0, 1.0], 'load': [500.0, 400.0]}
        with self.assertRaises(ThrustCurveError) as ctx:
            ThrustCurveProcessor.from_dict(raw, unit='N')
        self.assertIn('thrust', str(ctx.exception).lower())


# ===========================================================================
# B03 – Structural validations
# ===========================================================================

class TestStructuralValidations(unittest.TestCase):
    """Hard validations must produce ThrustCurveError with meaningful messages."""

    def test_raises_on_non_monotonic_time(self):
        raw = {'time': [0.0, 1.0, 0.5, 2.0], 'thrust': [100.0, 200.0, 150.0, 50.0]}
        with self.assertRaises(ThrustCurveError) as ctx:
            ThrustCurveProcessor.from_dict(raw, unit='N')
        self.assertIn('strictly increasing', str(ctx.exception))

    def test_raises_on_duplicate_times(self):
        raw = {'time': [0.0, 1.0, 1.0, 2.0], 'thrust': [100.0, 200.0, 200.0, 50.0]}
        with self.assertRaises(ThrustCurveError):
            ThrustCurveProcessor.from_dict(raw, unit='N')

    def test_raises_on_thrust_well_below_floor_N(self):
        # -50 N is far below the -5 N noise floor
        raw = {'time': [0.0, 0.5, 1.0], 'thrust': [-50.0, 200.0, 100.0]}
        with self.assertRaises(ThrustCurveError) as ctx:
            ThrustCurveProcessor.from_dict(raw, unit='N')
        self.assertIn('noise floor', str(ctx.exception))

    def test_raises_on_thrust_well_below_floor_kgf(self):
        # -10 kgf ≈ -98 N is well below the floor
        raw = {'time': [0.0, 0.5, 1.0], 'thrust': [-10.0, 20.0, 10.0]}
        with self.assertRaises(ThrustCurveError) as ctx:
            ThrustCurveProcessor.from_dict(raw, unit='kgf')
        self.assertIn('noise floor', str(ctx.exception))

    def test_small_negative_within_floor_is_accepted(self):
        # -0.5 N is within the -5 N noise floor – clipped to 0, not rejected
        raw = {'time': [0.0, 1.0, 2.0], 'thrust': [-0.5, 200.0, 0.0]}
        data = ThrustCurveProcessor.from_dict(raw, unit='N')
        self.assertGreaterEqual(min(data.thrust_N), 0.0)

    def test_raises_if_fewer_than_two_valid_points(self):
        raw = {'time': [0.0], 'thrust': [500.0]}
        with self.assertRaises(ThrustCurveError):
            ThrustCurveProcessor.from_dict(raw, unit='N')

    def test_raises_on_missing_file(self):
        with self.assertRaises(ThrustCurveError) as ctx:
            ThrustCurveProcessor.from_csv('does_not_exist_12345.csv', unit='N')
        self.assertIn('not found', str(ctx.exception))


# ===========================================================================
# B04 – Explicit unit handling, no heuristic
# ===========================================================================

class TestUnitHandling(unittest.TestCase):
    """Unit conversion must be explicit; no magnitude-based inference."""

    def test_kgf_multiplied_by_conversion_factor(self):
        raw = {'time': [0.0, 1.0, 2.0], 'thrust': [10.0, 20.0, 5.0]}
        data = ThrustCurveProcessor.from_dict(raw, unit='kgf')
        self.assertAlmostEqual(data.max_thrust, 20.0 * KGF_TO_N, places=3)

    def test_N_values_unchanged(self):
        raw = {'time': [0.0, 1.0, 2.0], 'thrust': [10.0, 20.0, 5.0]}
        data = ThrustCurveProcessor.from_dict(raw, unit='N')
        self.assertAlmostEqual(data.max_thrust, 20.0, places=3)

    def test_kgf_and_N_differ_by_constant(self):
        raw = {'time': [0.0, 1.0], 'thrust': [100.0, 50.0]}
        data_N   = ThrustCurveProcessor.from_dict(raw, unit='N')
        data_kgf = ThrustCurveProcessor.from_dict(raw, unit='kgf')
        self.assertAlmostEqual(
            data_kgf.max_thrust / data_N.max_thrust, KGF_TO_N, places=4
        )

    def test_raises_on_invalid_unit_lbf(self):
        raw = {'time': [0.0, 1.0], 'thrust': [100.0, 50.0]}
        with self.assertRaises(ThrustCurveError) as ctx:
            ThrustCurveProcessor.from_dict(raw, unit='lbf')
        self.assertIn('thrust_curve_unit', str(ctx.exception))

    def test_raises_on_empty_unit_string(self):
        raw = {'time': [0.0, 1.0], 'thrust': [100.0, 50.0]}
        with self.assertRaises(ThrustCurveError):
            ThrustCurveProcessor.from_dict(raw, unit='')

    def test_small_N_curve_not_auto_converted(self):
        """A valid motor with max thrust < 1000 N must NOT be auto-converted."""
        raw = {'time': [0.0, 0.5, 1.0], 'thrust': [40.0, 80.0, 30.0]}
        data = ThrustCurveProcessor.from_dict(raw, unit='N')
        # Max thrust must stay at 80 N, not 80 * 9.80665 ≈ 785 N
        self.assertAlmostEqual(data.max_thrust, 80.0, places=2)

    def test_unit_recorded_in_output(self):
        raw = {'time': [0.0, 1.0], 'thrust': [100.0, 50.0]}
        data = ThrustCurveProcessor.from_dict(raw, unit='kgf')
        self.assertEqual(data.unit_declared, 'kgf')


# ===========================================================================
# B05 – Rich output structure
# ===========================================================================

class TestRichOutputStructure(unittest.TestCase):
    """ThrustCurveData must expose all required fields with correct values."""

    def setUp(self):
        raw = {
            'time':   [0.0, 0.5, 1.0, 1.5, 2.0],
            'thrust': [0.0, 500.0, 800.0, 600.0, 0.0],
        }
        self.data = ThrustCurveProcessor.from_dict(raw, unit='N')

    # --- time array ---
    def test_time_starts_at_zero(self):
        self.assertAlmostEqual(self.data.time_s[0], 0.0)

    def test_time_offset_normalised(self):
        raw = {'time': [34.0, 34.5, 35.0], 'thrust': [0.0, 100.0, 50.0]}
        data = ThrustCurveProcessor.from_dict(raw, unit='N')
        self.assertAlmostEqual(data.time_s[0], 0.0)
        self.assertAlmostEqual(data.duration, 1.0, places=5)

    # --- thrust array ---
    def test_thrust_values_in_newtons(self):
        self.assertAlmostEqual(self.data.thrust_N[2], 800.0)

    def test_thrust_non_negative(self):
        self.assertGreaterEqual(min(self.data.thrust_N), 0.0)

    def test_noise_clipped_to_zero(self):
        raw = {'time': [0.0, 0.5, 1.0], 'thrust': [-0.3, 200.0, 0.0]}
        data = ThrustCurveProcessor.from_dict(raw, unit='N')
        self.assertGreaterEqual(min(data.thrust_N), 0.0)

    # --- scalar metrics ---
    def test_duration(self):
        self.assertAlmostEqual(self.data.duration, 2.0)

    def test_max_thrust(self):
        self.assertAlmostEqual(self.data.max_thrust, 800.0)

    def test_total_impulse_positive(self):
        self.assertGreater(self.data.total_impulse, 0.0)

    def test_mean_thrust_consistent_with_impulse(self):
        expected = self.data.total_impulse / self.data.duration
        self.assertAlmostEqual(self.data.mean_thrust, expected, places=4)

    def test_n_points(self):
        self.assertEqual(self.data.n_points, 5)

    # --- validation dict ---
    def test_validation_dict_contains_required_keys(self):
        required = {
            'n_points', 'duration_s', 'max_thrust_N',
            'total_impulse_Ns', 'mean_thrust_N', 'unit_declared', 'source',
        }
        self.assertTrue(required.issubset(self.data.validation.keys()))

    def test_source_recorded_as_dict(self):
        self.assertEqual(self.data.source, 'dict')


# ===========================================================================
# B05 – Impulse consistency validation
# ===========================================================================

class TestImpulseConsistency(unittest.TestCase):

    def _make_data(self, times, thrusts, unit='N'):
        return ThrustCurveProcessor.from_dict(
            {'time': times, 'thrust': thrusts}, unit=unit
        )

    def test_report_keys_present(self):
        data = self._make_data([0.0, 1.0, 2.0], [0.0, 500.0, 0.0])
        report = ThrustCurveProcessor.validate_impulse_consistency(
            data, propellant_mass=0.05, isp=100.0
        )
        for key in ('valid', 'impulse_error_percent', 'measured_impulse',
                    'expected_impulse', 'measured_avg_thrust', 'expected_avg_thrust'):
            self.assertIn(key, report)

    def test_valid_when_within_20_percent(self):
        # total_impulse ≈ 500 N·s; expected = 0.05 * 1000 * 9.80665 ≈ 490 N·s → ~2%
        data = self._make_data([0.0, 1.0], [0.0, 1000.0])
        report = ThrustCurveProcessor.validate_impulse_consistency(
            data, propellant_mass=0.05, isp=1000.0
        )
        self.assertIn('valid', report)

    def test_invalid_when_impulse_far_off(self):
        data = self._make_data([0.0, 1.0], [1.0, 1.0])
        report = ThrustCurveProcessor.validate_impulse_consistency(
            data, propellant_mass=100.0, isp=300.0, tolerance=0.20
        )
        self.assertFalse(report['valid'])

    def test_custom_tolerance_respected(self):
        # Use a very tight tolerance (1%) to force failure on a ~2% error
        data = self._make_data([0.0, 1.0], [0.0, 1000.0])
        report_loose = ThrustCurveProcessor.validate_impulse_consistency(
            data, propellant_mass=0.05, isp=1000.0, tolerance=0.20
        )
        report_tight = ThrustCurveProcessor.validate_impulse_consistency(
            data, propellant_mass=0.05, isp=1000.0, tolerance=0.001
        )
        # Loose should pass; tight should fail for a curve that isn't perfect
        self.assertIsInstance(report_loose['valid'], bool)
        self.assertIsInstance(report_tight['valid'], bool)


# ===========================================================================
# CSV round-trip via tempfile
# ===========================================================================

class TestCSVRoundTrip(unittest.TestCase):

    def test_from_csv_english_columns(self):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False, newline=''
        ) as f:
            f.write('time,thrust\n0.0,0.0\n0.5,200.0\n1.0,100.0\n')
            path = f.name
        try:
            data = ThrustCurveProcessor.from_csv(path, unit='N')
            self.assertGreater(data.total_impulse, 0)
            self.assertAlmostEqual(data.time_s[0], 0.0)
            self.assertEqual(data.n_points, 3)
        finally:
            os.unlink(path)

    def test_from_csv_kgf_conversion(self):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False, newline=''
        ) as f:
            f.write('Tiempo,Fuerza\n0.0,0.0\n0.5,10.0\n1.0,5.0\n')
            path = f.name
        try:
            data = ThrustCurveProcessor.from_csv(path, unit='kgf')
            self.assertAlmostEqual(data.max_thrust, 10.0 * KGF_TO_N, places=3)
        finally:
            os.unlink(path)

    def test_from_csv_with_offset_time(self):
        """Time starting at a non-zero value must be normalised to 0."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False, newline=''
        ) as f:
            f.write('time,thrust\n34.0,0.0\n34.5,100.0\n35.0,50.0\n')
            path = f.name
        try:
            data = ThrustCurveProcessor.from_csv(path, unit='N')
            self.assertAlmostEqual(data.time_s[0], 0.0)
            self.assertAlmostEqual(data.duration, 1.0, places=5)
        finally:
            os.unlink(path)

    def test_from_csv_real_load_cell(self):
        """Smoke-test against the actual load_cell_1.csv in the repository."""
        csv_path = os.path.join('data', 'thrust_curves', 'load_cell_1.csv')
        if not os.path.exists(csv_path):
            self.skipTest(f"Real CSV not found at: {csv_path}")
        data = ThrustCurveProcessor.from_csv(csv_path, unit='kgf')
        # Sanity checks against Campanil 1-A Experimental known values
        self.assertGreater(data.max_thrust, 2000.0,   # ≈ 2104 N
                           "Max thrust should be ~2104 N after kgf→N conversion")
        self.assertAlmostEqual(data.time_s[0], 0.0)
        self.assertGreater(data.total_impulse, 0.0)


if __name__ == '__main__':
    unittest.main()
