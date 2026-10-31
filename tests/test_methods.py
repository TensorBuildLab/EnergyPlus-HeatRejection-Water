"""Checks for the multi-method library, chemistry extensions and plugin core.

Run: python -m unittest discover -s tests -v
psychrolib (ASHRAE Handbook implementation) is used as an independent reference when installed.
"""
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from tower_water import chemistry as ch  # noqa: E402
from tower_water import evaporation as ev  # noqa: E402
from tower_water import methods as mt  # noqa: E402
from tower_water import psychro as ps  # noqa: E402
from tower_water.eplus_plugin import MERKEL, VS, compute_tower, setup_tower  # noqa: E402

try:
    import psychrolib
    psychrolib.SetUnitSystem(psychrolib.SI)
except ImportError:  # pragma: no cover
    psychrolib = None

P = 101325.0


def op(t_db=30.0, rh=0.4, tw_in=35.0, tw_out=29.0, mw=10.0, ma=9.0):
    w = ps.w_from_rh(t_db, rh, P)
    q = mw * ps.CP_WATER * (tw_in - tw_out)
    return mt.OperatingPoint(tw_in, tw_out, mw, q, ma, ma * (1 + w), t_db, ps.t_wb_from_w(t_db, w, P), w, P)


@unittest.skipIf(psychrolib is None, "psychrolib not installed")
class AgainstPsychroLib(unittest.TestCase):
    def test_saturation_pressure(self):
        for t in (-20, -5, 0.01, 10, 25, 40, 60):
            self.assertAlmostEqual(ps.p_sat(t) / psychrolib.GetSatVapPres(t), 1.0, delta=5e-4, msg=t)

    def test_humidity_ratio_and_enthalpy(self):
        for t in (0, 15, 30, 45):
            self.assertAlmostEqual(ps.w_sat(t, P) / psychrolib.GetSatHumRatio(t, P), 1.0, delta=1e-3)
            w = 0.6 * ps.w_sat(t, P)
            self.assertAlmostEqual(ps.h_air(t, w) / psychrolib.GetMoistAirEnthalpy(t, w), 1.0, delta=2e-3)

    def test_wetbulb(self):
        for t, rh in ((35, 0.15), (30, 0.6), (10, 0.8)):
            w = ps.w_from_rh(t, rh, P)
            self.assertAlmostEqual(ps.t_wb_from_w(t, w, P), psychrolib.GetTWetBulbFromHumRatio(t, w, P), delta=0.02)


class Properties(unittest.TestCase):
    def test_latent_heat(self):
        # IAPWS-95 values: 2453.5 kJ/kg at 20 C, 2406.0 at 40 C
        self.assertAlmostEqual(ps.h_fg(20.0) / 2453.5e3, 1.0, delta=1e-3)
        self.assertAlmostEqual(ps.h_fg(40.0) / 2406.0e3, 1.0, delta=3e-3)  # Henderson-Sellers: ~0.3 % at 40 C


class Methods(unittest.TestCase):
    def test_all_methods_run_and_are_positive(self):
        res = mt.evaluate(op())
        self.assertEqual(list(res), list(mt.METHODS))
        for m, r in res.items():
            self.assertGreater(r.evap_kg_s, 0.0, m)

    def test_physical_methods_agree_to_within_15_percent_at_a_normal_point(self):
        res = mt.evaluate(op())
        ref = res["POPPE"].evap_kg_s
        for m in ("MSAT", "BRAUN", "POPPE1"):
            self.assertAlmostEqual(res[m].evap_kg_s / ref, 1.0, delta=0.15, msg=m)

    def test_hot_dry_air_evaporates_more_than_latent_bound(self):
        # Air hotter than the water: sensible heat flows INTO the water, so E > Q/h_fg
        res = mt.evaluate(op(t_db=43.0, rh=0.12, tw_in=33.0, tw_out=27.0))
        self.assertGreater(res["POPPE"].evap_kg_s, res["LAT"].evap_kg_s)

    def test_cool_humid_air_evaporates_less_than_latent_bound(self):
        res = mt.evaluate(op(t_db=12.0, rh=0.7, tw_in=30.0, tw_out=24.0))
        self.assertLess(res["POPPE"].evap_kg_s, res["LAT"].evap_kg_s)

    def test_braun_tends_to_saturated_exit_at_high_ntu(self):
        o = op(ma=3.8)
        b = ev.braun_entu(o.q, o.t_w_in, o.t_w_out, o.m_w, o.m_a, o.t_db, o.w, P)
        s = ev.merkel_saturated_exit(o.q, o.m_a, o.t_db, o.w, P)
        self.assertGreater(b.ntu, 3.0)
        self.assertAlmostEqual(b.evap_kg_s / s.evap_kg_s, 1.0, delta=0.03)

    def test_entu_rating_and_ntu_inversion_roundtrip(self):
        o = op()
        me = 1.2
        t_out = ev.outlet_temperature_entu(me, o.t_w_in, o.m_w, o.m_a, o.t_db, o.w, P)
        q = o.m_w * ps.CP_WATER * (o.t_w_in - t_out)
        ntu, _ = ev.braun_ntu_from_operating_point(q, o.t_w_in, t_out, o.m_w, o.m_a, ps.h_air(o.t_db, o.w), P)
        self.assertAlmostEqual(ntu / (me * o.m_w / o.m_a), 1.0, delta=0.01)

    def test_poppe_rating_roundtrip(self):
        o = op()
        t_out = ev.outlet_temperature_poppe(1.0, o.t_w_in, o.m_w, o.m_a, o.t_db, o.w, P)
        r = ev.poppe(o.t_w_in, t_out, o.m_w, o.m_a, o.t_db, o.w, P)
        self.assertAlmostEqual(r.merkel, 1.0, delta=2e-3)

    def test_merkel_vs_poppe_rating_same_fill(self):
        o = op()
        tm = ev.outlet_temperature_merkel(1.0, o.t_w_in, o.m_w, o.m_a, o.t_db, o.w, P)
        tp = ev.outlet_temperature_poppe(1.0, o.t_w_in, o.m_w, o.m_a, o.t_db, o.w, P)
        te = ev.outlet_temperature_entu(1.0, o.t_w_in, o.m_w, o.m_a, o.t_db, o.w, P)
        self.assertLess(abs(tm - tp), 0.5)   # literature: methods agree within a few tenths of a kelvin
        self.assertLess(abs(tm - te), 0.5)

    def test_chebyshev_close_to_exact(self):
        o = op()
        h = ps.h_air(o.t_db, o.w)
        a = ev.merkel_number_chebyshev(o.t_w_in, o.t_w_out, o.m_w, o.m_a, h, P)
        b = ev.merkel_number_exact(o.t_w_in, o.t_w_out, o.m_w, o.m_a, h, P)
        self.assertAlmostEqual(a / b, 1.0, delta=0.01)

    def test_lewis_factor_typical_value(self):
        lef = ev.lewis_bosnjakovic(ps.w_sat(30.0, P), 0.010)
        self.assertTrue(0.88 < lef < 0.95, lef)


class NearPinch(unittest.TestCase):
    def test_marginal_operating_point_is_adjusted_not_dropped(self):
        # Real EnergyPlus Merkel-tower point (Dublin, 1 July 19:30): exit air within 0.4 % of the pinch
        p, tdb, w, tin, tout, mw, q, ma = 101621.5, 16.25, 0.006745, 22.40268, 18.0, 54.478239, 1002583.35, 31.16067
        o = mt.OperatingPoint(tin, tout, mw, q, ma, ma * (1 + w), tdb, ps.t_wb_from_w(tdb, w, p), w, p)
        r = mt.evaluate(o, ["POPPE", "MSAT"])
        self.assertEqual(r["POPPE"].status, ev.ADJUSTED)
        self.assertLessEqual(r["POPPE"].air_scale, 1.05)
        self.assertAlmostEqual(r["POPPE"].evap_kg_s / r["MSAT"].evap_kg_s, 1.0, delta=0.05)

    def test_physical_methods_share_the_adjusted_air_flow(self):
        p, tdb, w, tin, tout, mw, q, ma = 101621.5, 16.25, 0.006745, 22.40268, 18.0, 54.478239, 1002583.35, 31.16067
        o = mt.OperatingPoint(tin, tout, mw, q, ma, ma * (1 + w), tdb, ps.t_wb_from_w(tdb, w, p), w, p)
        r = mt.evaluate(o, ["POPPE", "MSAT", "EPSAT"])
        sc = r["POPPE"].air_scale
        self.assertGreater(sc, 1.0)
        self.assertEqual(r["MSAT"].air_scale, sc)
        msat_scaled = ev.merkel_saturated_exit(q, ma * sc, tdb, w, p).evap_kg_s
        self.assertAlmostEqual(r["MSAT"].evap_kg_s, msat_scaled, places=12)
        self.assertEqual(r["EPSAT"].air_scale, 1.0)     # EnergyPlus replica keeps EnergyPlus' air


class Chemistry(unittest.TestCase):
    water = ch.WaterQuality("w", {"tds": 650, "calcium_hardness": 220, "m_alkalinity": 180, "silica": 30})

    def test_lsi_limit_is_exact(self):
        n = ch.cycles_lsi_limit(self.water, 8.3, 2.5, 35.0)
        c = self.water.conc
        val = ch.lsi(8.3, c["tds"] * n, 35.0, c["calcium_hardness"] * n, c["m_alkalinity"] * n)
        self.assertAlmostEqual(val, 2.5, places=6)

    def test_ryznar(self):
        c = self.water.conc
        phs = ch.ph_s(c["tds"], 25, c["calcium_hardness"], c["m_alkalinity"])
        self.assertAlmostEqual(ch.rsi(8.0, c["tds"], 25, c["calcium_hardness"], c["m_alkalinity"]), 2 * phs - 8.0)

    def test_silica_solubility(self):
        self.assertAlmostEqual(ch.silica_solubility(25.0), 116.7, delta=1.0)
        self.assertGreater(ch.silica_solubility(40.0), ch.silica_solubility(20.0))

    def test_dynamic_mode_hotter_water_scales_sooner(self):
        t = ch.TreatmentLimits("t", {}, {}, lsi_max=2.5, ph_cycled=8.3)
        hot = ch.cycles_of_concentration(self.water, t, t_hot=40.0)[0]
        cool = ch.cycles_of_concentration(self.water, t, t_hot=25.0)[0]
        self.assertLess(hot, cool)


class PluginCore(unittest.TestCase):
    def tower(self, typ):
        t = {"name": "T", "type": typ, "prefix": "T", "design_air_flow": 50.0, "design_water_flow": 0.1,
             "free_conv_air_flow": 5.0, "min_air_flow_ratio": 0.2, "drift_fraction": 1e-5, "cells": 2,
             "water_source": "example_hard_groundwater", "treatment": "generic_inhibitor"}
        return setup_tower(t, {"water_library": os.path.join(ROOT, "data", "water_sources.json")})

    site = {"t_db": 20.0, "t_wb": 15.0, "w": ps.w_from_twb(20.0, 15.0, P), "p": P}

    def test_merkel_free_convection_uses_free_convection_air(self):
        v = {"t_in": 30.0, "t_out": 29.0, "m_w": 100.0, "q": 100.0 * 4186.0, "afr": 0.0, "cells_on": 2}
        out = compute_tower(self.tower(MERKEL), v, self.site)
        self.assertGreater(out["E_POPPE"], 0.0)
        self.assertEqual(out["E_EPSAT"], 0.0)       # EnergyPlus books zero evaporation here
        self.assertAlmostEqual(out["AirMass"], 5.0 * ps.rho_moist_air(20.0, self.site["w"], P) / (1 + self.site["w"]))

    def test_idle_tower_has_no_water(self):
        v = {"t_in": 30.0, "t_out": 30.0, "m_w": 100.0, "q": 0.0, "afr": 0.4, "cells_on": 2, "plr": 1.0}
        out = compute_tower(self.tower(VS), v, self.site)
        self.assertEqual(out["Makeup"], 0.0)
        self.assertTrue(all(out["E_" + m] == 0.0 for m in mt.METHODS))

    def test_water_balance(self):
        v = {"t_in": 32.0, "t_out": 27.0, "m_w": 100.0, "q": 100 * 4186.0 * 5, "afr": 0.8, "cells_on": 2, "plr": 1.0}
        out = compute_tower(self.tower(VS), v, self.site)
        self.assertAlmostEqual(out["Makeup"], out["E_POPPE"] + out["Drift"] + out["Blowdown"])
        self.assertAlmostEqual(out["Blowdown"], out["E_POPPE"] / (out["Cycles"] - 1) - out["Drift"])


if __name__ == "__main__":
    unittest.main()
