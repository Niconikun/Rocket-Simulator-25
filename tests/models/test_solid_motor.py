"""Tests for the grain-driven solid motor engine (src/models/solid_motor.py).

The physics checks follow Nakka's quasi-steady internal ballistics:
Pc = (rho_p * a * c* * Kn)^(1/(1-n)), r_b = a * Pc^n, mdot = Pc*At/c*,
F = Cf * Pc * At.
"""

import math

import numpy as np
import pytest

from src.models.grain import BatesGrain, EndBurningGrain, InternalTubeGrain, StarGrain
from src.models.interfaces import IEngine
from src.models.solid_motor import (
    SolidMotorEngine,
    burn_rate_coefficient_si,
    characteristic_velocity,
    create_solid_motor,
    exit_mach_from_expansion_ratio,
    gamma_function,
)
from src.utils.simulation_errors import InputValidationError

G0 = 9.80665

BATES_CFG = {
    'grain': {'type': 'bates', 'outer_diameter': 0.075, 'core_diameter': 0.030,
              'segment_length': 0.10, 'segments': 3},
    'propellant': {'density': 1800.0, 'burn_rate_a': 5.0, 'burn_rate_n': 0.3},
    'nozzle': {'throat_diameter': 0.018, 'exit_diameter': 0.036},
}

END_BURN_CFG = {
    'grain': {'type': 'end_burning', 'diameter': 0.05, 'length': 0.20},
    'propellant': {'density': 1800.0, 'burn_rate_a': 5.0, 'burn_rate_n': 0.3,
                   'characteristic_velocity': 1500.0},
    'nozzle': {'throat_diameter': 0.006, 'exit_diameter': 0.012},
}

STAR_CFG = {
    'grain': {'type': 'star', 'outer_diameter': 0.075, 'length': 0.30, 'n_points': 5,
              'tip_diameter': 0.030, 'half_angle_deg': 35.0},
    'propellant': {'density': 1800.0, 'burn_rate_a': 5.0, 'burn_rate_n': 0.3},
    'nozzle': {'throat_diameter': 0.012, 'exit_diameter': 0.024},
}


class TestHelpers:
    def test_gamma_function_value(self):
        assert gamma_function(1.2) == pytest.approx(0.64853, rel=1e-4)
        assert gamma_function(1.4) == pytest.approx(0.6847, rel=1e-3)

    def test_characteristic_velocity(self):
        cstar = characteristic_velocity(320.0, 3200.0, 1.2)
        assert cstar == pytest.approx(1421.0, rel=0.02)

    def test_exit_mach_supersonic(self):
        me = exit_mach_from_expansion_ratio(4.0, 1.2)
        assert me > 1.0
        area = (1.0 / me) * ((2.0 / 2.2) * (1.0 + 0.1 * me * me)) ** (2.2 / 0.4)
        assert area == pytest.approx(4.0, rel=1e-6)

    def test_burn_rate_coefficient_si_nakka_units(self):
        a_si = burn_rate_coefficient_si(5.0, 0.3, unit='mm/s', pressure_unit='MPa')
        r = a_si * (7e6) ** 0.3
        assert r == pytest.approx(5.0e-3 * 7.0 ** 0.3, rel=1e-12)

    def test_burn_rate_units_validation(self):
        with pytest.raises(InputValidationError):
            burn_rate_coefficient_si(5.0, 0.3, unit='furlongs', pressure_unit='MPa')


class TestSolidMotorEngineContract:
    def test_implements_iengine(self):
        m = create_solid_motor(BATES_CFG)
        assert isinstance(m, IEngine)
        assert isinstance(m, SolidMotorEngine)
        assert m.thrust_source == 'solid-grain'

    def test_metrics_keys_match_enhanced_engine(self):
        m = create_solid_motor(BATES_CFG)
        keys = set(m.get_performance_metrics().keys())
        expected = {
            'thrust', 'mass_flow', 'specific_impulse', 'characteristic_velocity',
            'thrust_coefficient', 'exit_pressure', 'exit_velocity', 'chamber_pressure',
            'throat_area', 'exit_area', 'thrust_source', 'propellant_consumed',
            'remaining_propellant', 'total_impulse_delivered', 'burnout_reached',
        }
        assert expected <= keys

    def test_thrust_positive_during_burn_zero_after_burnout(self):
        m = create_solid_motor(BATES_CFG)
        s = m.summary()
        m.update(time=s['burn_time'] / 2.0, ambient_pressure=101325.0)
        assert m.get_thrust() > 0.0
        assert m.get_mass_flow() > 0.0
        m.update(time=s['burn_time'] * 1.5, ambient_pressure=101325.0)
        assert m.get_thrust() == 0.0
        assert m.get_mass_flow() == 0.0
        assert m.burnout_reached is True

    def test_propellant_mass_conservation_at_burnout(self):
        m = create_solid_motor(BATES_CFG)
        s = m.summary()
        m.update(time=s['burn_time'], ambient_pressure=101325.0)
        assert m.propellant_consumed == pytest.approx(m.propellant_mass, rel=1e-2)
        assert 0.0 <= m.remaining_propellant <= 4 * m.sliver_fraction * m.propellant_mass
        assert m.total_impulse_delivered == pytest.approx(
            s['total_impulse'], rel=1e-3)

    def test_thrust_increases_in_vacuum(self):
        m = create_solid_motor(BATES_CFG)
        s = m.summary()
        t = s['burn_time'] / 2.0
        m.update(time=t, ambient_pressure=101325.0)
        f_sl = m.get_thrust()
        m.update(time=t, ambient_pressure=0.0)
        f_vac = m.get_thrust()
        assert f_vac > f_sl

    def test_invalid_inputs(self):
        bad = dict(BATES_CFG)
        bad['propellant'] = {'density': 1800.0, 'burn_rate_a': 5.0, 'burn_rate_n': 1.2}
        with pytest.raises(InputValidationError):
            create_solid_motor(bad)
        bad2 = dict(BATES_CFG)
        bad2['nozzle'] = {'throat_diameter': 0.05, 'exit_diameter': 0.01}
        with pytest.raises(InputValidationError):
            create_solid_motor(bad2)
        with pytest.raises(InputValidationError):
            create_solid_motor({'grain': BATES_CFG['grain']})

    def test_update_validates_inputs(self):
        m = create_solid_motor(BATES_CFG)
        with pytest.raises(InputValidationError):
            m.update(time=-1.0)
        with pytest.raises(InputValidationError):
            m.update(ambient_pressure=-1.0)


class TestInternalBallistics:
    def test_equilibrium_pressure_matches_nakka_formula(self):
        m = create_solid_motor(END_BURN_CFG)
        grain = m.grain
        kn = grain.burning_surface(0.0) / m.throat_area
        pc_expected = (m.propellant_density * m._a_si * m.characteristic_velocity * kn) ** (
            1.0 / (1.0 - m.burn_rate_n))
        m.update(time=0.0, ambient_pressure=101325.0)
        assert m.get_performance_metrics()['chamber_pressure'] == pytest.approx(pc_expected, rel=1e-6)

    def test_end_burner_is_neutral(self):
        m = create_solid_motor(END_BURN_CFG)
        s = m.summary()
        ts = np.linspace(0.05, 0.95, 10) * s['burn_time']
        pcs, thrusts = [], []
        for t in ts:
            m.update(time=float(t), ambient_pressure=101325.0)
            pcs.append(m.get_performance_metrics()['chamber_pressure'])
            thrusts.append(m.get_thrust())
        assert np.ptp(pcs) / np.mean(pcs) < 0.02
        assert np.ptp(thrusts) / np.mean(thrusts) < 0.02

    def test_tube_grain_is_progressive(self):
        cfg = {
            'grain': {'type': 'internal_tube', 'outer_diameter': 0.075,
                      'core_diameter': 0.03, 'length': 0.30},
            'propellant': {'density': 1800.0, 'burn_rate_a': 5.0, 'burn_rate_n': 0.3},
            'nozzle': {'throat_diameter': 0.012, 'exit_diameter': 0.024},
        }
        m = create_solid_motor(cfg)
        s = m.summary()
        ts = np.linspace(0.05, 0.95, 8) * s['burn_time']
        pcs = []
        for t in ts:
            m.update(time=float(t), ambient_pressure=101325.0)
            pcs.append(m.get_performance_metrics()['chamber_pressure'])
        assert pcs[-1] > pcs[0] * 1.2

    def test_star_grain_progressive_thrust(self):
        m = create_solid_motor(STAR_CFG)
        s = m.summary()
        ts = np.linspace(0.05, 0.95, 8) * s['burn_time']
        thrusts = []
        for t in ts:
            m.update(time=float(t), ambient_pressure=101325.0)
            thrusts.append(m.get_thrust())
        assert thrusts[-1] > thrusts[0]

    def test_mass_flow_matches_choked_nozzle(self):
        m = create_solid_motor(BATES_CFG)
        s = m.summary()
        m.update(time=s['burn_time'] / 2.0, ambient_pressure=101325.0)
        pc = m.get_performance_metrics()['chamber_pressure']
        mdot_expected = pc * m.throat_area / m.characteristic_velocity
        assert m.get_mass_flow() == pytest.approx(mdot_expected, rel=1e-3)

    def test_summary_consistency(self):
        m = create_solid_motor(BATES_CFG)
        s = m.summary()
        assert s['mean_thrust'] * s['burn_time'] == pytest.approx(s['total_impulse'], rel=0.02)
        assert s['specific_impulse'] == pytest.approx(
            s['total_impulse'] / (s['propellant_mass'] * G0), rel=1e-9)
        assert s['max_thrust'] >= s['mean_thrust'] > 0.0
        assert s['max_chamber_pressure'] >= s['mean_chamber_pressure'] > 0.0
        assert s['propellant_mass'] == pytest.approx(
            m.propellant_density * m.grain.propellant_volume(), rel=1e-9)

    def test_validate_thrust_curve(self):
        m = create_solid_motor(BATES_CFG)
        result = m.validate_thrust_curve()
        assert result['valid'] is True
        assert result['error_percent'] < 5.0

    def test_curve_info(self):
        m = create_solid_motor(BATES_CFG)
        info = m.get_thrust_curve_info()
        assert info['available'] is True
        assert info['source'] == 'solid-grain'
        assert info['burn_time'] == pytest.approx(m.summary()['burn_time'])


class TestSolidMotorConstruction:
    def test_direct_constructor(self):
        grain = BatesGrain(outer_diameter=0.075, core_diameter=0.03,
                           segment_length=0.10, segments=3)
        m = SolidMotorEngine(
            grain=grain, propellant_density=1800.0, burn_rate_a=5.0, burn_rate_n=0.3,
            throat_diameter=0.018, exit_diameter=0.036, rocket_mass=12.0)
        assert m.thrust_to_weight_ratio == pytest.approx(
            m.summary()['max_thrust'] / (12.0 * G0), rel=1e-9)
        assert m.burn_time > 0.0

    def test_characteristic_velocity_override(self):
        cfg = dict(END_BURN_CFG)
        cfg['propellant'] = dict(END_BURN_CFG['propellant'])
        cfg['propellant']['characteristic_velocity'] = 1600.0
        m = create_solid_motor(cfg)
        assert m.characteristic_velocity == pytest.approx(1600.0)

    def test_experimental_curve_override(self):
        curve = {'time': [0.0, 0.5, 1.0, 1.5], 'thrust': [100.0, 500.0, 500.0, 0.0]}
        cfg = dict(BATES_CFG)
        cfg['thrust_curve_data'] = curve
        cfg['thrust_curve_unit'] = 'N'
        m = create_solid_motor(cfg)
        assert m.use_experimental_thrust is True
        assert m.thrust_source == 'experimental'
        m.update(time=0.5, ambient_pressure=101325.0)
        assert m.get_thrust() == pytest.approx(500.0)
        info = m.get_thrust_curve_info()
        assert info['available'] is True and info['data_points'] == 4
