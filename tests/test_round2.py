"""Tests added in review round 2 (paper/REVIEW_round2.md)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tower_water import evaporation as ev  # noqa: E402
from tower_water import psychro as ps  # noqa: E402


class PoppeConvergence(unittest.TestCase):
    def test_converged_flag_and_iteration_limit(self):
        p = 101325.0
        w = ps.w_from_twb(30.0, 22.0, p)
        r = ev.poppe(35.0, 28.0, 10.0, 8.0, 30.0, w, p)
        self.assertEqual(r.status, ev.OK)
        self.assertTrue(r.converged)
        r1 = ev.poppe(35.0, 28.0, 10.0, 8.0, 30.0, w, p, max_iter=1)
        self.assertFalse(r1.converged)
        # one pass is already within 1 % of the converged evaporation
        self.assertAlmostEqual(r1.evap_kg_s / r.evap_kg_s, 1.0, delta=0.01)


class EffectiveCycles(unittest.TestCase):
    def test_effective_cycles_reproduce_constant_cycles(self):
        import numpy as np
        e = np.array([1.0, 2.0, 3.0])
        drift = 0.01 * e
        n = 4.0
        b = np.maximum(e / (n - 1) - drift, 0)
        self.assertAlmostEqual(e.sum() / (b.sum() + drift.sum()) + 1, n, places=12)


class RealisticFill(unittest.TestCase):
    def test_point_meets_leaving_water_temperature(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import realistic_fill_check as rf
        p = 101325.0
        w = ps.w_from_twb(32.0, 21.0, p)
        mw = 10.0
        me_d = ev.poppe(30.5, 24.9, mw, mw / 1.2, 32.0, w, p, n_steps=40).merkel
        ma, e, liq, eps, q, capped, me_op = rf._point((me_d, 1.2, mw / 1.2, 0.6, 29.0, 25.0, mw, 30.0, 20.0,
                                                        ps.w_from_twb(30.0, 20.0, p), p))
        self.assertEqual(capped, 0.0)
        # at the solved air flow the Poppe Merkel number equals the fill's
        me_req = ev.poppe(29.0, 25.0, mw, ma, 30.0, ps.w_from_twb(30.0, 20.0, p), p).merkel
        self.assertAlmostEqual(me_req / me_op, 1.0, delta=1e-3)


if __name__ == "__main__":
    unittest.main()
