"""Tests for ui.widgets.monte_carlo_widget (Phase 2 behaviour):

- failed-run counter stays correct when runs complete out of order (parallel)
- landing-zone figure falls back to the local ENU plot when map rendering fails
- landing summary handles batches where no run landed (NaN impacts)
"""

import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

import numpy as np
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.state import MockStateProvider
from ui.widgets import monte_carlo_widget as mcw
from ui.widgets.monte_carlo_widget import MonteCarloWidget


def _runs(n=5):
    rng = np.random.default_rng(0)
    return [
        {
            "max_altitude": 1000.0 + rng.normal(0, 10),
            "max_velocity": 200.0, "max_mach": 0.6, "max_range": 100.0,
            "flight_duration": 60.0, "apogee_time": 20.0, "max_accel_g": 5.0,
            "impact_x": float(rng.normal(100, 20)),
            "impact_y": float(rng.normal(0, 10)),
        }
        for _ in range(n)
    ]


class TestMonteCarloWidgetBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.state = MockStateProvider({
            'monte_carlo_runs': 10,
            'parachute_enabled': False,
            'wind_enabled': False,
            'launch_latitude': 4.5,
            'launch_longitude': -70.3,
        })
        # Isolate the widget from the global EventBus singleton
        self._bus_patches = [
            mock.patch.object(mcw, name) for name in ('subscribe', 'unsubscribe', 'publish')
        ]
        for p in self._bus_patches:
            p.start()
            self.addCleanup(p.stop)
        self.widget = MonteCarloWidget(state=self.state)
        self.app.processEvents()

    def tearDown(self):
        self.widget.close()
        self.widget.deleteLater()
        self.app.processEvents()


class TestFailedCount(TestMonteCarloWidgetBase):
    def test_failed_count_correct_with_out_of_order_completion(self):
        self.widget.runs_spinbox.setValue(10)
        # parallel path can complete run 5 before run 0
        self.widget._on_run_completed(5, {'max_altitude': 1.0})
        self.widget._on_run_failed(2, 'boom')
        self.widget._on_run_completed(0, {'max_altitude': 2.0})
        self.widget._on_run_failed(7, 'boom')
        text = self.widget.status_label.text()
        self.assertIn('Completed 2 / 10', text)
        self.assertIn('(failed: 2)', text)

    def test_failed_count_reset_on_new_run(self):
        self.widget._on_run_failed(0, 'boom')
        self.widget._on_run_failed(1, 'boom')
        # the reset that run_monte_carlo() performs before a new batch
        self.widget._accumulated_runs.clear()
        self.widget._failed_count = 0
        self.widget._on_run_completed(0, {'max_altitude': 1.0})
        self.assertIn('(failed: 0)', self.widget.status_label.text())


class TestLandingZoneFallback(TestMonteCarloWidgetBase):
    def test_map_failure_falls_back_to_local_plot(self):
        with mock.patch.object(mcw, 'HAS_CARTOPY', True), \
             mock.patch.object(MonteCarloWidget, '_draw_map_landing_zone',
                               side_effect=RuntimeError('Natural Earth download failed')):
            fig = self.widget._build_landing_zone_figure(_runs())
        self.assertIsNotNone(fig)
        self.assertEqual(fig.axes[0].get_xlabel(), 'East (km)')

    def test_summary_handles_batch_with_no_landings(self):
        runs = [dict(r, impact_x=float('nan'), impact_y=float('nan')) for r in _runs(3)]
        self.widget._update_landing_summary(runs)
        self.assertEqual(self.widget.runs_value_label.text(), '0')
        self.assertEqual(self.widget.cep_value_label.text(), 'N/A')
        self.assertEqual(self.widget.landing_point_label.text(), 'N/A')

    def test_summary_reports_landing_stats(self):
        self.widget._update_landing_summary(_runs(5))
        self.assertEqual(self.widget.runs_value_label.text(), '5')
        self.assertNotEqual(self.widget.cep_value_label.text(), 'N/A')
        self.assertIn('m', self.widget.distance_value_label.text())


if __name__ == '__main__':
    unittest.main()
