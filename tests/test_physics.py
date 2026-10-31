"""Physics checks for the standalone core. Run: python -m unittest discover -s tests -v"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from tower_water import evaporation as ev  # noqa: E402
from tower_water import psychro as ps  # noqa: E402
from tower_water.chemistry import ChemistryModel, TreatmentLimits, WaterQuality, blowdown, cycles_of_concentration  # noqa: E402

P = 101325.0


class Psychrometrics(unittest.TestCase):
    def test_saturation_pressure_matches_ashrae_table(self):
        # ASHRAE Fundamentals, Table 3 (saturation pressure, Pa)
        for t, pws in [(-10.0, 259.90), (0.0, 611.2), (20.0, 2339.3), (40.0, 7384.9)]:
            self.assertAlmostEqual(ps.p_sat(t) / pws, 1.0, delta=2e-3, msg=str(t))

    def test_saturation_humidity_ratio(self):
        # ASHRAE table value 0.014758 includes the enhancement factor (~1.004); we, like EnergyPlus, omit it
        self.assertAlmostEqual(ps.w_sat(20.0, P) / 0.014758, 1.0, delta=5e-3)

    def test_wetbulb_roundtrip(self):
        w = ps.w_from_twb(30.0, 20.0, P)
        self.assertAlmostEqual(ps.w_from_twb(20.0, 20.0, P), ps.w_sat(20.0, P), delta=1e-6)
        self.assertTrue(0 < w < ps.w_sat(20.0, P))

    def test_tsat_from_h_inverts_h_sat(self):
        self.assertAlmostEqual(ps.t_sat_from_h(ps.h_sat(27.3, P), P), 27.3, delta=1e-4)

    def test_water_density(self):
        self.assertAlmostEqual(ps.rho_water(20.0), 998.21, delta=0.05)


class Poppe(unittest.TestCase):
    def run_case(self, t_db=25.0, rh=0.5, tw_in=35.0, tw_out=28.0, mw=1.0, ma=0.8, n=10):
        w = ps.w_from_rh(t_db, rh, P)
        return w, ev.poppe(tw_in, tw_out, mw, ma, t_db, w, P, n_steps=n)

    def test_energy_balance_closes(self):
        w, r = self.run_case()
        self.assertEqual(r.status, ev.OK)
        h_in = ps.h_air(25.0, w)
        if r.supersaturated:
            self.skipTest("case is supersaturated")
        h_out = ps.h_air(r.t_air_out, r.w_air_out)
        air_gain = 0.8 * (h_out - h_in)
        water_loss = 1.0 * ps.CP_WATER * 35.0 - (1.0 - r.evap_kg_s) * ps.CP_WATER * 28.0
        self.assertAlmostEqual(air_gain / water_loss, 1.0, delta=1e-3)

    def test_step_convergence(self):
        _, r10 = self.run_case(n=10)
        _, r80 = self.run_case(n=80)
        self.assertAlmostEqual(r10.evap_kg_s / r80.evap_kg_s, 1.0, delta=1e-4)

    def test_exit_air_nearly_saturated_when_air_is_scarce(self):
        # Low air flow -> large Merkel number -> exit close to saturation -> close to saturated-exit result
        w, r = self.run_case(ma=0.5)
        self.assertEqual(r.status, ev.OK)
        rh_out = r.w_air_out / ps.w_sat(r.t_air_out, P)
        self.assertGreater(rh_out, 0.97)
        # Saturated-exit evaporation at the same exit enthalpy (same energy basis as Poppe)
        h_out = ps.h_air(r.t_air_out, r.w_air_out)
        sat = 0.5 * (ps.w_sat(ps.t_sat_from_h(h_out, P), P) - w)
        self.assertAlmostEqual(r.evap_kg_s / sat, 1.0, delta=0.02)

    def test_more_air_means_unsaturated_exit_and_less_evaporation(self):
        _, lo = self.run_case(ma=0.6)
        _, hi = self.run_case(ma=3.0)
        self.assertLess(hi.w_air_out / ps.w_sat(hi.t_air_out, P), 0.95)
        self.assertGreater(hi.merkel, 0.0)
        self.assertGreater(lo.merkel, hi.merkel)

    def test_cold_humid_air_fogs(self):
        _, r = self.run_case(t_db=2.0, rh=0.9, tw_in=30.0, tw_out=22.0, ma=0.7)
        self.assertEqual(r.status, ev.OK)
        self.assertTrue(r.supersaturated)

    def test_supersaturated_branch_conserves_energy_and_mass(self):
        # cold, humid air fogs; check energy with the supersaturated (vapour + mist) enthalpy (review M8)
        t_db, rh, tw_in, tw_out, mw, ma = 2.0, 0.9, 30.0, 22.0, 1.0, 0.7
        w, r = self.run_case(t_db=t_db, rh=rh, tw_in=tw_in, tw_out=tw_out, mw=mw, ma=ma, n=40)
        self.assertTrue(r.supersaturated)
        wsa = ps.w_sat(r.t_air_out, P)
        i_out = (ps.CP_AIR * r.t_air_out + wsa * (ps.H_FG0 + ps.CP_VAPOR * r.t_air_out)
                 + (r.w_air_out - wsa) * ps.CP_WATER * r.t_air_out)
        air_gain = ma * (i_out - ps.h_air(t_db, w))
        water_loss = mw * ps.CP_WATER * tw_in - (mw - r.evap_kg_s) * ps.CP_WATER * tw_out
        self.assertAlmostEqual(air_gain / water_loss, 1.0, delta=1e-3)
        self.assertAlmostEqual(r.evap_kg_s, ma * (r.w_air_out - w), places=12)

    def test_idle_and_no_airflow(self):
        w = ps.w_from_rh(25, 0.5, P)
        self.assertEqual(ev.poppe(30, 30, 1.0, 1.0, 25, w, P).status, ev.IDLE)
        self.assertEqual(ev.poppe(31, 30, 1.0, 0.0, 25, w, P).status, ev.NO_AIRFLOW)

    def test_infeasible_operating_point_is_flagged(self):
        # Far too little air to remove 20 K of range
        _, r = self.run_case(tw_in=45.0, tw_out=25.0, ma=0.05)
        self.assertEqual(r.status, ev.INFEASIBLE)


class Chemistry(unittest.TestCase):
    def test_limiting_constituent(self):
        water = WaterQuality("w", {"silica": 30.0, "calcium_hardness": 220.0, "chloride": 50.0})
        treat = TreatmentLimits("t", {"silica": 150.0, "calcium_hardness": 1000.0, "chloride": 500.0})
        coc, which = cycles_of_concentration(water, treat)
        self.assertAlmostEqual(coc, 1000.0 / 220.0)
        self.assertEqual(which, "calcium_hardness")

    def test_product_limit_and_bounds(self):
        water = WaterQuality("w", {"calcium_hardness": 200.0, "m_alkalinity": 200.0})
        treat = TreatmentLimits("t", {}, {"calcium_hardness*m_alkalinity": 160000.0}, max_cycles=10)
        self.assertAlmostEqual(cycles_of_concentration(water, treat)[0], 2.0)
        self.assertEqual(cycles_of_concentration(WaterQuality("pure", {}), treat)[0], 10)

    def test_blowdown(self):
        self.assertAlmostEqual(blowdown(4.0, 0.1, 5.0), 0.9)
        self.assertEqual(blowdown(1.0, 5.0, 3.0), 0.0)

    def test_library_loads(self):
        m = ChemistryModel.from_library(os.path.join(ROOT, "data", "water_sources.json"),
                                        "example_hard_groundwater", "generic_inhibitor")
        coc, _ = m.cycles()
        self.assertTrue(1.5 <= coc <= 10)


if __name__ == "__main__":
    unittest.main()
