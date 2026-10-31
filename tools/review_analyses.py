#!/usr/bin/env python3
"""Additional analyses requested in review round 1 (paper/REVIEW_round1.md).

  python tools/review_analyses.py runs/dc      # -> results/study/review_*.csv

1. M4  Poppe evaporation split into vapour and liquid mist (supersaturated exit air).
2. M3  Near-pinch air-flow correction statistics and implied Merkel number distribution.
3. M3  Fixed-fill rating check: for hourly-sampled loaded timesteps, solve T_w,out with Poppe for a FIXED fill
       (Me_P sized at the tower design point, Me ~ (L/G)^-0.6 off-design; exponent is an assumption) at EnergyPlus'
       T_w,in, water flow, air flow and weather; compare T_w,out and evaporation with the accounting-mode values.
4. M5  Peak-day evaporation: EnergyPlus vs Poppe.
5. M11 Loss-factor range 0.15-0.27 %/K (documented range) vs Poppe.
6. m9  Braun clipping share in the climate map.
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import analyze  # noqa: E402
from tower_water import evaporation as ev  # noqa: E402
from tower_water import idf  # noqa: E402
from tower_water import methods as mt  # noqa: E402
from tower_water import psychro as ps  # noqa: E402

RHO_REF = ps.rho_water(20.0)
FILL_EXP = 0.6       # Me ~ (L/G)^-n, typical counterflow fill exponent range 0.4-0.8 (assumption)


def mist_and_correction(site, d, dt_h):
    sec = dt_h * 3600
    on = d[d.ep_heat_transfer_rate > 0]
    ws = np.array([ps.w_sat(t, p) for t, p in zip(on.pl_airoutt, on.site_barometric_pressure)])
    liq = np.where(on.pl_fog > 0, np.maximum(on.pl_airoutw - ws, 0.0), 0.0) * on.pl_airmass / RHO_REF   # m3/s
    poppe = on.pl_e_poppe.sum() * sec
    liq_m3 = liq.sum() * sec
    ep = on.ep_water_evaporation_volume_flow_rate.sum() * sec
    adj = on.pl_status.round() == 5
    me = on.pl_mepoppe[on.pl_mepoppe > 0]
    return {
        "site": site, "poppe_m3": poppe, "mist_m3": liq_m3, "mist_share_%": 100 * liq_m3 / poppe,
        "EP_vs_poppe_%": 100 * (ep / poppe - 1), "EP_vs_poppe_vapour_only_%": 100 * (ep / (poppe - liq_m3) - 1),
        "adjusted_hours_share_%": 100 * adj.mean(), "air_factor_mean_adj": on.pl_airscale[adj].mean() if adj.any() else np.nan,
        "air_factor_p95_adj": on.pl_airscale[adj].quantile(0.95) if adj.any() else np.nan,
        "air_factor_max": on.pl_airscale.max(),
        "MeP_median": me.median(), "MeP_p95": me.quantile(0.95), "MeP_max": me.max(),
    }


def peak_and_lf(site, d, dt_h):
    sec = dt_h * 3600
    day = d.time.str.strip().str.slice(0, 5)
    g = d.groupby(day)[["ep_water_evaporation_volume_flow_rate", "pl_e_poppe", "pl_e_lf"]].sum() * sec
    pk = g.pl_e_poppe.idxmax()
    poppe = d.pl_e_poppe.sum() * sec
    lf = d.pl_e_lf.sum() * sec
    return {"site": site, "peak_day": pk, "peak_poppe_m3": g.pl_e_poppe.max(), "peak_EP_m3": g.loc[pk].ep_water_evaporation_volume_flow_rate,
            "peak_EP_vs_poppe_%": 100 * (g.loc[pk].ep_water_evaporation_volume_flow_rate / g.pl_e_poppe.max() - 1),
            "max_EP_day_m3": g.ep_water_evaporation_volume_flow_rate.max(),
            "LF015_vs_poppe_%": 100 * (lf * 0.15 / 0.2 / poppe - 1), "LF020_vs_poppe_%": 100 * (lf / poppe - 1),
            "LF027_vs_poppe_%": 100 * (lf * 0.27 / 0.2 / poppe - 1)}


def design_fill(run):
    cfg = analyze.load(run)[0]
    t = cfg["towers"][0]
    tow = [o for o in idf.parse((run / "model.idf").read_text()) if o[0].lower() == "coolingtower:variablespeed:merkel"][0]
    db, wb, appr, rng = (float(idf.field(tow, i)) for i in (24, 25, 26, 27))
    p = 101325.0
    w = ps.w_from_twb(db, wb, p)
    mw = t["design_water_flow"] * ps.rho_water(30.0)
    ma = t["design_air_flow"] * ps.rho_moist_air(db, w, p) / (1 + w)
    # same minimal air adjustment as the plugin when the EnergyPlus design point lies beyond Poppe's limit
    for sc in (1.0,) + mt.AIR_SCALES:
        r = ev.poppe(wb + appr + rng, wb + appr, mw, ma * sc, db, w, p, n_steps=40)
        if r.status == ev.OK:
            return r.merkel, mw / (ma * sc), sc
    return float("nan"), mw / ma, float("nan")


def _rating_point(args):
    me_d, lg_d, tw_in, mw, ma, t_db, w, p, tw_out_ep, n_exp = args
    me = me_d * ((mw / ma) / lg_d) ** (-n_exp)
    t_out = ev.outlet_temperature_poppe(me, tw_in, mw, ma, t_db, w, p, n_steps=10)
    if not np.isfinite(t_out):
        return np.nan, np.nan, np.nan
    r = ev.poppe(tw_in, t_out, mw, ma, t_db, w, p)
    q_ep = mw * ps.CP_WATER * (tw_in - tw_out_ep)
    return t_out - tw_out_ep, r.evap_kg_s, mw * ps.CP_WATER * (tw_in - t_out) / q_ep - 1 if q_ep > 0 else np.nan


def rating_check(run, d, jobs=32, every=6, n_exp=FILL_EXP):
    me_d, lg_d, sc_d = design_fill(run)
    on = d[(d.ep_heat_transfer_rate > 0) & (d.pl_airmass > 0)].iloc[::every]
    args = [(me_d, lg_d, r.ep_inlet_temperature, r.ep_mass_flow_rate, r.pl_airmass, r.site_drybulb_temperature,
             r.site_humidity_ratio, r.site_barometric_pressure, r.ep_outlet_temperature, n_exp) for r in on.itertuples()]
    with ProcessPoolExecutor(jobs) as pool:
        res = list(pool.map(_rating_point, args, chunksize=16))
    dT = np.array([x[0] for x in res])
    e_fix = np.array([x[1] for x in res])
    dq = np.array([x[2] for x in res])
    e_acc = on.pl_e_poppe.to_numpy() * RHO_REF
    ok = np.isfinite(dT)
    return {"site": run.name, "fill_exp": n_exp, "Me_design": me_d, "LG_design": lg_d, "design_air_factor": sc_d, "n_sampled": len(on), "solved_%": 100 * ok.mean(),
            "dTwout_median_K": np.median(dT[ok]), "dTwout_p95_K": np.percentile(dT[ok], 95),
            "heat_fixed_fill_vs_EP_%": 100 * np.nanmean(dq[ok]),
            "evap_fixed_fill_vs_accounting_%": 100 * (e_fix[ok].sum() / e_acc[ok].sum() - 1),
            "evap_per_heat_fixed_vs_accounting_%": 100 * ((e_fix[ok].sum() / (1 + np.nanmean(dq[ok]))) / e_acc[ok].sum() - 1)}


def braun_clipping():
    f = ROOT / "results" / "method_map" / "method_map.csv"
    if not f.exists():
        return None
    m = pd.read_csv(f)
    dev = 100 * (m.E_BRAUN / m.E_POPPE - 1)
    clip = m.status_BRAUN == ev.CLIPPED
    return pd.DataFrame([{"points": len(m), "clipped_%": 100 * clip.mean(), "dev_all_min": dev.min(), "dev_all_max": dev.max(),
                          "dev_unclipped_min": dev[~clip].min(), "dev_unclipped_max": dev[~clip].max()}])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_root", type=Path)
    ap.add_argument("--rating-sites", nargs="*", default=["phoenix_tmyx", "singapore", "frankfurt", "stockholm"])
    ap.add_argument("--fill-exp-sweep", nargs="*", type=float, default=[],
                    help="only run the fixed-fill check for these exponents -> review_rating_check_sweep.csv")
    a = ap.parse_args()
    if a.fill_exp_sweep:
        rows = []
        for run in sorted(p for p in a.run_root.iterdir() if p.name in a.rating_sites):
            _, frames, _ = analyze.load(run)
            d = next(iter(frames.values()))
            for n in a.fill_exp_sweep:
                rows.append(rating_check(run, d, n_exp=n))
                print("rating check", run.name, n)
        df = pd.DataFrame(rows)
        df.to_csv(ROOT / "results" / "study" / "review_rating_check_sweep.csv", index=False)
        print(df.round(3).to_string(index=False))
        return
    out = ROOT / "results" / "study"
    out.mkdir(parents=True, exist_ok=True)
    rows1, rows2, rows3 = [], [], []
    for run in sorted(p for p in a.run_root.iterdir() if (p / "out" / "eplusout.csv").exists()):
        _, frames, dt_h = analyze.load(run)
        d = next(iter(frames.values()))
        rows1.append(mist_and_correction(run.name, d, dt_h))
        rows2.append(peak_and_lf(run.name, d, dt_h))
        if run.name in a.rating_sites:
            rows3.append(rating_check(run, d))
            print("rating check", run.name)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    for name, rows in (("review_mist_correction", rows1), ("review_peak_lf", rows2), ("review_rating_check", rows3)):
        df = pd.DataFrame(rows)
        df.to_csv(out / (name + ".csv"), index=False)
        print("\n" + name)
        print(df.round(3).to_string(index=False))
    b = braun_clipping()
    if b is not None:
        b.to_csv(out / "review_braun_clipping.csv", index=False)
        print("\nbraun clipping\n" + b.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
