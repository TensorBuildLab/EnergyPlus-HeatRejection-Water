"""Tests for the hybrid adiabatic dry cooler module. Run: python -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from tower_water import hybrid as hy  # noqa: E402
from tower_water import psychro as ps  # noqa: E402
from tower_water.eplus_hybrid import HybridState  # noqa: E402

P = 101325.0


class PadPhysics(unittest.TestCase):
    def test_full_effectiveness_reaches_wet_bulb_state(self):
        for t, rh in ((40.0, 0.15), (30.0, 0.5), (15.0, 0.7)):
            w = ps.w_from_rh(t, rh, P)
            pc = hy.precool(t, w, P, 1.0)
            self.assertAlmostEqual(pc.t_db, pc.t_wb, places=6)
            # independent: ASHRAE wet-bulb relation gives the saturated state at T_wb
            self.assertAlmostEqual(pc.w / ps.w_sat(pc.t_wb, P), 1.0, delta=2e-3)

    def test_partial_effectiveness_is_on_the_wet_bulb_line(self):
        w = ps.w_from_rh(40.0, 0.15, P)
        pc = hy.precool(40.0, w, P, 0.85)
        self.assertAlmostEqual(ps.t_wb_from_w(pc.t_db, pc.w, P), pc.t_wb, delta=0.03)
        self.assertAlmostEqual(pc.t_db, 40.0 - 0.85 * (40.0 - pc.t_wb), places=9)
        self.assertGreater(pc.dw, 0.0)

    def test_energy_is_conserved(self):
        w = ps.w_from_rh(35.0, 0.2, P)
        pc = hy.precool(35.0, w, P, 0.8)
        lhs = ps.h_air(35.0, w) + pc.dw * ps.CP_WATER * pc.t_wb
        self.assertAlmostEqual(ps.h_air(pc.t_db, pc.w) / lhs, 1.0, delta=1e-9)

    def test_effectiveness_scales_with_velocity(self):
        self.assertAlmostEqual(hy.pad_effectiveness(0.85, 1.0), 0.85, places=9)
        self.assertGreater(hy.pad_effectiveness(0.85, 0.5), 0.85)
        self.assertLess(hy.pad_effectiveness(0.85, 1.5), 0.85)
        self.assertEqual(hy.pad_effectiveness(0.85, 0.0), 0.0)


class FanStates(unittest.TestCase):
    def test_two_speed_inversion(self):
        self.assertEqual(hy.fan_states(0.0, 10, 2, 100, 50), [])
        self.assertEqual(hy.fan_states(1.0, 10, 2, 100, 50), [(0.5, 50)])
        st = hy.fan_states(6.0, 10, 2, 100, 50)
        self.assertAlmostEqual(st[0][0], 0.5)
        self.assertEqual(st[0][1], 100)
        self.assertAlmostEqual(st[1][0], 0.5)
        # inverse of EnergyPlus: P = f P_high + (1 - f) P_low
        self.assertAlmostEqual(st[0][0] * 10 + st[1][0] * 2, 6.0)
        self.assertEqual(hy.fan_states(10.0, 10, 2, 100, 50), [(1.0, 100)])


class Water(unittest.TestCase):
    def test_media_and_spray(self):
        self.assertEqual(hy.water_supply(1.0, hy.PadConfig(system="media"), 3.0), (1.5, 0.5))
        m, r = hy.water_supply(1.2, hy.PadConfig(system="spray", spray_efficiency=0.6), None)
        self.assertAlmostEqual(m, 2.0)
        self.assertAlmostEqual(r, 0.8)

    def test_pad_timestep_mass_balance(self):
        w = ps.w_from_rh(38.0, 0.2, P)
        cfg = hy.PadConfig(eps_design=0.85)
        r = hy.pad_timestep([(0.5, 100.0)], True, 38.0, w, P, cfg)
        m = 0.5 * 100.0 * ps.rho_moist_air(38.0, w, P) / (1 + w)
        self.assertAlmostEqual(r.air_kg_s, m)
        self.assertAlmostEqual(r.evap_kg_s, m * hy.precool(38.0, w, P, 0.85).dw)
        self.assertEqual(hy.pad_timestep([(0.5, 100.0)], False, 38.0, w, P, cfg).evap_kg_s, 0.0)


class Control(unittest.TestCase):
    def test_threshold_with_hysteresis_and_freeze(self):
        c = hy.Controller(strategy="threshold", t_on=26.0, hysteresis=2.0)
        seq = [(25.0, 15), (26.0, 16), (25.0, 15), (23.9, 14), (25.0, 15)]
        self.assertEqual([c.step(t, wb) for t, wb in seq], [False, True, True, False, False])
        self.assertEqual(c.switches, 2)
        self.assertFalse(hy.Controller(strategy="wet").step(3.0, 1.0))
        self.assertTrue(hy.Controller(strategy="wet").step(12.0, 8.0))
        self.assertFalse(hy.Controller(strategy="wet", min_depression=3.0).step(20.0, 18.5))


class PluginState(unittest.TestCase):
    def cfg(self, **ctrl):
        return {"node": "N", "coolers": [{"name": "C1", "v_high": 50.0, "v_low": 25.0, "p_high": 10e3, "p_low": 1.5e3}],
                "pad": {"eps_design": 0.85}, "controller": ctrl,
                "water_library": os.path.join(ROOT, "data", "water_sources.json"),
                "water_source": "example_hard_groundwater", "treatment": "generic_inhibitor"}

    def test_wet_actuation_and_accounting_are_consistent(self):
        st = HybridState(self.cfg(strategy="wet"))
        w = ps.w_from_rh(40.0, 0.15, P)
        twb = ps.t_wb_from_w(40.0, w, P)
        db, wb = st.begin_timestep(40.0, twb, w, P)
        self.assertLess(db, 40.0)
        self.assertAlmostEqual(wb, twb)
        out = st.end_timestep([(st.cfg["coolers"][0], {"q": 5e5, "p_fan": 10e3, "t_in": 45, "t_out": 39})], 600.0)
        m = 50.0 * ps.rho_moist_air(40.0, w, P) / (1 + w)
        self.assertAlmostEqual(out["Evap"] * ps.rho_water(20.0), m * (st.pre.w - w), places=9)
        self.assertAlmostEqual(out["PreT"], db)
        self.assertAlmostEqual(out["Makeup"], out["Evap"] + out["Bleed"])

    def test_dry_mode_uses_no_water(self):
        st = HybridState(self.cfg(strategy="dry"))
        db, _ = st.begin_timestep(40.0, 20.0, 0.007, P)
        self.assertEqual(db, 40.0)
        out = st.end_timestep([(st.cfg["coolers"][0], {"q": 5e5, "p_fan": 10e3, "t_in": 45, "t_out": 39})], 600.0)
        self.assertEqual(out["Makeup"], 0.0)


if __name__ == "__main__":
    unittest.main()
