"""Single-speed (fan-cycling / fluid-bypass) tower support (author-comments round, v5)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tower_water import eplus_plugin as P  # noqa: E402
from tower_water import evaporation as ev  # noqa: E402
from tower_water import psychro as ps  # noqa: E402

SITE = dict(t_db=25.0, t_wb=18.0, w=ps.w_from_twb(25.0, 18.0, 101325.0), p=101325.0)


class _Chem:
    mode = "fixed"


def tower(**kw):
    t = dict(name="T", type=P.SS, design_air_flow=200.0, free_conv_air_flow=20.0, free_conv_ua=60000.0, cells=2,
             design_water_flow=0.45, drift_fraction=1e-5, _chem=_Chem(), _coc=4.0, _limit="fixed")
    t.update(kw)
    return t


def op(t_out, f, bypass=0.0, m_w=450.0, t_in=32.0):
    return dict(t_in=t_in, t_out=t_out, m_w=m_w, q=m_w * ev.cp_water(t_in) * (t_in - t_out), fcr=f, cells_on=2,
                bypass=bypass)


class TestReplica(unittest.TestCase):
    def test_limits(self):
        a = (SITE["t_db"], SITE["t_wb"], SITE["w"], SITE["p"])
        self.assertEqual(ev.eplus_simple_tower_outlet(32.0, 100.0, 50.0, 0.0, *a), 32.0)
        t_big = ev.eplus_simple_tower_outlet(32.0, 100.0, 500.0, 1e9, *a)
        self.assertGreater(t_big, SITE["t_wb"] - 1e-6)
        self.assertLess(t_big, SITE["t_wb"] + 0.5)
        t_mid = ev.eplus_simple_tower_outlet(32.0, 100.0, 50.0, 5e4, *a)
        self.assertTrue(t_big < t_mid < 32.0)


class TestStates(unittest.TestCase):
    def test_cycling_energy_closure(self):
        t = tower()
        v = op(29.5, 0.4)
        st = P.single_speed_states(t, v, SITE)
        self.assertEqual(len(st), 2)
        (f_on, t_on, _, a_on), (f_off, t_off, _, a_off) = st
        self.assertAlmostEqual(f_on * t_on + f_off * t_off, v["t_out"], places=9)
        self.assertAlmostEqual(a_on, 200.0)
        self.assertAlmostEqual(a_off, 20.0)

    def test_bypass_reduces_fill_flow(self):
        st = P.single_speed_states(tower(), op(29.0, 1.0, bypass=0.25), SITE)
        self.assertEqual(len(st), 1)
        self.assertAlmostEqual(st[0][2], 0.75 * 450.0)
        self.assertLess(st[0][1], 29.0)          # fill outlet colder than the mixed outlet

    def test_full_fan_matches_direct_poppe(self):
        t = tower()
        v = op(28.0, 1.0)
        out = P.compute_tower(t, v, SITE)
        m_a = 200.0 * ps.rho_moist_air(SITE["t_db"], SITE["w"], SITE["p"]) / (1 + SITE["w"])
        r = ev.poppe(32.0, 28.0, 450.0, m_a, SITE["t_db"], SITE["w"], SITE["p"], n_steps=10)
        self.assertAlmostEqual(out["E_POPPE"] * ps.rho_water(20.0), r.evap_kg_s, places=9)

    def test_epsat_uses_energyplus_convention(self):
        t = tower()
        v = op(29.5, 0.4)
        out = P.compute_tower(t, v, SITE)
        m_air = ev.eplus_air_mass_flow(1.0, 200.0, 2, 2, SITE["t_db"], SITE["w"], SITE["p"])
        e = ev.eplus_saturated_exit(v["q"], m_air, SITE["t_db"], SITE["t_wb"], SITE["w"], SITE["p"])
        self.assertAlmostEqual(out["E_EPSAT"], e, places=12)


if __name__ == "__main__":
    unittest.main()
