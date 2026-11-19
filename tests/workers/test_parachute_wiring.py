"""
Tests that the parachute is actually attached to the rocket dynamics and that
its drag force reaches the RK4 integration (temp dynamics):

- Rocket.set_parachute wires both rocket.parachute and rocket.dynamics.parachute
- Simulation._create_temp_dynamics propagates the parachute to the temporary
  dynamics used by every RK4 substep
- calculate_parachute_forces produces a non-zero force opposite to the
  relative velocity once the parachute is deployed
- SimulationWorker attaches the parachute when parachute_enabled is set
"""

import unittest
from unittest import mock

import numpy as np
import pytest

from src.models.parachute import Parachute
from src.models.rocket.factory import create_rocket_from_config
from src.models.rocket.rocket import Rocket
from src.models.state import MockStateProvider


def _make_rocket():
    return create_rocket_from_config(
        r_enu_0=np.zeros(3),
        v_enu_0=np.zeros(3),
        q_enu2b_0=np.array([0.0, 0.0, 0.0, 1.0]),
        w_enu_0=np.zeros(3),
        initial_mass=10.0,
        rocket_name='agni-1',
    )[0]


def _make_parachute():
    return Parachute({
        'name': 'test-chute',
        'diameter': 0.6,
        'Cd': 1.5,
        'deployment_altitude': 10000.0,  # deploys immediately at low altitude
        'min_velocity': 0.0,
        'max_velocity': 1000.0,
        'inflation_time': 0.1,
    })


@pytest.mark.monte_carlo
class TestParachuteAttachment(unittest.TestCase):
    def test_set_parachute_wires_dynamics(self):
        rocket = _make_rocket()
        p = _make_parachute()
        rocket.set_parachute(p)
        self.assertIs(rocket.parachute, p)
        self.assertIs(rocket.dynamics.parachute, p)

    def test_temp_dynamics_carry_parachute(self):
        rocket = _make_rocket()
        p = _make_parachute()
        rocket.set_parachute(p)
        temp = rocket.simulation._create_temp_dynamics(rocket.state.copy())
        self.assertIs(temp.parachute, p)

    def test_parachute_force_opposes_velocity_when_deployed(self):
        rocket = _make_rocket()
        p = _make_parachute()
        rocket.set_parachute(p)
        # deployment is descent-gated: simulate a previous higher-altitude step
        p.previous_altitude = 200.0
        p.update(velocity=50.0, altitude=100.0, density=1.225)
        self.assertTrue(p.is_deployed())

        state = rocket.state.copy()
        state.v_enu = np.array([0.0, 0.0, -50.0])  # falling at 50 m/s
        temp = rocket.simulation._create_temp_dynamics(state)
        forces_b, _ = temp.calculate_parachute_forces()
        force_enu = np.array(forces_b)
        # body frame == ENU here (identity quaternion)
        self.assertGreater(force_enu[2], 0.0)  # drag pushes up while falling
        expected = 0.5 * 1.225 * 50.0**2 * 1.5 * np.pi * (0.6 / 2.0) ** 2
        self.assertAlmostEqual(np.linalg.norm(force_enu), expected, delta=expected * 0.01)

    def test_no_parachute_means_zero_force(self):
        rocket = _make_rocket()
        state = rocket.state.copy()
        state.v_enu = np.array([0.0, 0.0, -50.0])
        temp = rocket.simulation._create_temp_dynamics(state)
        forces_b, _ = temp.calculate_parachute_forces()
        self.assertTrue(np.allclose(forces_b, 0.0))

    def test_total_forces_include_parachute_drag(self):
        rocket = _make_rocket()
        p = _make_parachute()
        rocket.set_parachute(p)
        # deployment is descent-gated: simulate a previous higher-altitude step
        p.previous_altitude = 200.0
        p.update(velocity=50.0, altitude=100.0, density=1.225)

        state = rocket.state.copy()
        state.r_enu = np.array([0.0, 0.0, 100.0])
        state.v_enu = np.array([0.0, 0.0, -50.0])  # falling at 50 m/s

        temp_chute = rocket.simulation._create_temp_dynamics(state)
        f_chute, _ = temp_chute.calculate_forces()

        rocket.dynamics.parachute = None
        temp_plain = rocket.simulation._create_temp_dynamics(state)
        f_plain, _ = temp_plain.calculate_forces()

        delta = f_chute - f_plain
        expected = 0.5 * 1.225 * 50.0**2 * 1.5 * np.pi * (0.6 / 2.0) ** 2
        self.assertAlmostEqual(float(delta[2]), expected, delta=expected * 0.05)
        self.assertTrue(np.allclose(delta[:2], 0.0, atol=1e-6))


@pytest.mark.monte_carlo
class TestWorkerAttachesParachute(unittest.TestCase):
    def _state(self, parachute_enabled):
        return MockStateProvider({
            'selected_rocket': 'agni-1',
            'sim_runtime': 0.05,
            'sim_time_step': 0.01,
            'parachute_enabled': parachute_enabled,
            'wind_enabled': False,
        })

    def test_worker_attaches_parachute_when_enabled(self):
        from workers.simulation_worker import SimulationWorker

        worker = SimulationWorker(self._state(True), use_cache=False)
        with mock.patch.object(Rocket, 'set_parachute', autospec=True) as spy:
            result = worker.run_with_params({})
        self.assertEqual(result.get('status'), 'success')
        self.assertTrue(spy.called)
        attached = spy.call_args[0][1]
        self.assertIsInstance(attached, Parachute)
        self.assertIn('parachute_info', result)

    def test_worker_does_not_attach_parachute_when_disabled(self):
        from workers.simulation_worker import SimulationWorker

        worker = SimulationWorker(self._state(False), use_cache=False)
        with mock.patch.object(Rocket, 'set_parachute', autospec=True) as spy:
            result = worker.run_with_params({})
        self.assertEqual(result.get('status'), 'success')
        self.assertFalse(spy.called)
        self.assertNotIn('parachute_info', result)


if __name__ == '__main__':
    unittest.main()
