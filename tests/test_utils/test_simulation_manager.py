"""
Regression tests for SimulationManager metadata persistence (pyqt-gui review
plan point 6): launch_date/launch_time are written by the simulation widget
but used to be dropped by save_simulation, so dashboard PDF/CSV reports
showed 'Unknown'. They must survive save and the export/import round-trip.

Stdlib-only (SimulationManager has no Qt/numpy deps), so these run anywhere.
"""

import tempfile
import unittest
from pathlib import Path

from src.utils.simulation_manager import SimulationManager


class TestSimulationManagerMetadata(unittest.TestCase):
    """Metadata persistence contract between worker/widget and dashboard."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = self._tmp.name
        self.manager = SimulationManager(data_dir=self.data_dir)

    def _save_sample(self, extra_metadata=None):
        metadata = {
            'rocket': 'agni-1',
            'location': 'SHAR',
            'launch_date': '2026-04-12',
            'launch_time': '09:00:00',
            'launch_latitude': 13.0,
            'launch_longitude': 80.0,
            'launch_azimuth': 0.0,
            'max_altitude': 1.234,
            'max_velocity': 100.0,
            'max_range': 0.5,
            'max_mach': 0.3,
            'max_accel_g': 5.0,
            'flight_duration': 42.0,
            'temperature': 25.0,
            'pressure': 101325.0,
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        data = {
            'status': 'success',
            'trajectory': [{'time': 0.0, 'altitude': 0.0, 'velocity': 0.0,
                            'acceleration': 9.80665, 'range': 0.0}],
            'history': {'hist_time': [0.0]},
            'metrics': {'max_altitude': 1234.0},
        }
        return self.manager.save_simulation(data, metadata)

    def test_save_persists_launch_date_and_time(self):
        sim_id = self._save_sample()
        self.assertIsNotNone(sim_id)
        meta = self.manager.metadata[sim_id]
        self.assertEqual(meta['launch_date'], '2026-04-12')
        self.assertEqual(meta['launch_time'], '09:00:00')

    def test_saved_metadata_survives_reload_from_disk(self):
        sim_id = self._save_sample()
        reloaded = SimulationManager(data_dir=self.data_dir)
        self.assertEqual(reloaded.metadata[sim_id]['launch_date'], '2026-04-12')
        self.assertEqual(reloaded.metadata[sim_id]['launch_time'], '09:00:00')
        self.assertEqual(reloaded.load_simulation(sim_id)['status'], 'success')

    def test_export_import_roundtrip_preserves_launch_date_time(self):
        sim_id = self._save_sample()
        export_path = str(Path(self.data_dir) / 'export.json')
        self.assertTrue(self.manager.export_simulation(sim_id, export_path))

        fresh_dir = str(Path(self.data_dir) / 'fresh')
        new_manager = SimulationManager(data_dir=fresh_dir)
        new_id = new_manager.import_simulation(export_path)
        self.assertIsNotNone(new_id)
        meta = new_manager.metadata[new_id]
        self.assertEqual(meta['launch_date'], '2026-04-12')
        self.assertEqual(meta['launch_time'], '09:00:00')
        self.assertEqual(new_manager.load_simulation(new_id)['status'], 'success')

    def test_missing_launch_keys_default_to_unknown(self):
        sim_id = self.manager.save_simulation({'metrics': {}}, {'rocket': 'r'})
        self.assertIsNotNone(sim_id)
        meta = self.manager.metadata[sim_id]
        self.assertEqual(meta['launch_date'], 'Unknown')
        self.assertEqual(meta['launch_time'], 'Unknown')

    def test_dashboard_metadata_contract_keys_present(self):
        sim_id = self._save_sample()
        meta = self.manager.metadata[sim_id]
        for key in ('rocket', 'location', 'launch_date', 'launch_time',
                    'launch_latitude', 'launch_longitude', 'launch_azimuth',
                    'max_altitude', 'max_velocity', 'max_range', 'max_mach',
                    'max_accel_g', 'flight_duration', 'temperature', 'pressure'):
            self.assertIn(key, meta, f"metadata missing key {key!r} read by dashboard")


if __name__ == '__main__':
    unittest.main()
