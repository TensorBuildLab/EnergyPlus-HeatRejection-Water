#!/usr/bin/env python3
"""Realistic-fill check (review round 2, R2-M3c / R2-M4e).

The base plant's EnergyPlus Merkel tower is sized at each site's 0.4 % design wet-bulb with a 3.9 K approach and N+1
water flow, which at low design wet-bulbs needs design Merkel numbers of 5-8 (near the pinch). This check replaces it
by a tower with an ORDINARY fill: design L/G = 1.2 (the climate-map tower) at the same design water flow and design
conditions, fill law Me_P = Me_d (L/G / LG_d)^-n. For every sampled loaded timestep the air flow that this tower needs to
deliver EnergyPlus' leaving-water temperature is solved (bisection on the dry-air flow, capped at the design air flow),
so heat rejected is identical by construction and the comparison isolates the thermal operating point:

  * Poppe at the realistic-fill air flow vs Poppe in accounting mode (EnergyPlus' air flow);
  * EnergyPlus SaturatedExit at the realistic-fill air flow vs Poppe at the same point (what an EnergyPlus user with an
    ordinary tower would see), and EnergyPlus' own evaporation vs the realistic-fill Poppe value.

  python tools/realistic_fill_check.py runs/dc      # -> results/study/realistic_fill_{check,sites}.csv, realistic_fill_table.tex
"""
from __future__ import annotations

import argparse
import math
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
from tower_water import psychro as ps  # noqa: E402

RHO_REF = ps.rho_water(20.0)
LG_DESIGN = 1.2
FILL_EXP = 0.6


def design(run, lg_d):
    cfg = analyze.load(run)[0]
    t = cfg["towers"][0]
    tow = [o for o in idf.parse((run / "model.idf").read_text()) if o[0].lower() == "coolingtower:variablespeed:merkel"][0]
    db, wb, appr, rng = (float(idf.field(tow, i)) for i in (24, 25, 26, 27))
    p = 101325.0
    w = ps.w_from_twb(db, wb, p)
    mw = t["design_water_flow"] * ps.rho_water(30.0)
    ma = mw / lg_d
    r = ev.poppe(wb + appr + rng, wb + appr, mw, ma, db, w, p, n_steps=40)
    return dict(Me_d=r.merkel if r.status == ev.OK else float("nan"), ma_d=ma, mw_d=mw, wb_d=wb, db_d=db)


def _me_req(tw_in, tw_out, mw, ma, tdb, w, p):
    r = ev.poppe(tw_in, tw_out, mw, ma, tdb, w, p, n_steps=10)
    return r.merkel if r.status == ev.OK else math.inf


def _point(args):
    me_d, lg_d, ma_max, n_exp, tw_in, tw_out, mw, tdb, twb, w, p = args
    fill = lambda ma: me_d * ((mw / ma) / lg_d) ** (-n_exp)          # noqa: E731
    g = lambda ma: _me_req(tw_in, tw_out, mw, ma, tdb, w, p) - fill(ma)  # decreasing in ma  # noqa: E731
    capped = False
    if g(ma_max) > 0:                       # even full fan cannot reach EnergyPlus' T_w,out
        capped = True
        ma = ma_max
        t_out = ev.outlet_temperature_poppe(fill(ma), tw_in, mw, ma, tdb, w, p)
    else:
        lo, hi = 0.02 * ma_max, ma_max
        if g(lo) < 0:
            hi = lo
        else:
            for _ in range(40):
                mid = math.sqrt(lo * hi)
                if g(mid) > 0:
                    lo = mid
                else:
                    hi = mid
                if hi / lo < 1 + 1e-5:
                    break
        ma, t_out = hi, tw_out
    if not np.isfinite(t_out):
        return (np.nan,) * 7
    r = ev.poppe(tw_in, t_out, mw, ma, tdb, w, p, n_steps=10)
    q = mw * ps.CP_WATER * (tw_in - t_out)
    eps = ev.eplus_saturated_exit(q, ma * (1 + w), tdb, twb, w, p) * RHO_REF
    liq = 0.0
    if r.supersaturated:
        liq = ma * max(r.w_air_out - ps.w_sat(r.t_air_out, p), 0.0)
    return ma, r.evap_kg_s, liq, eps, q, float(capped), fill(ma)


def site_check(run, d, lg_d=LG_DESIGN, n_exp=FILL_EXP, every=6, jobs=64):
    des = design(run, lg_d)
    on = d[(d.ep_heat_transfer_rate > 0) & (d.pl_airmass > 0)].iloc[::every]
    args = [(des["Me_d"], lg_d, des["ma_d"], n_exp, r.ep_inlet_temperature, r.ep_outlet_temperature, r.ep_mass_flow_rate,
             r.site_drybulb_temperature, r.site_wetbulb_temperature, r.site_humidity_ratio, r.site_barometric_pressure)
            for r in on.itertuples()]
    with ProcessPoolExecutor(jobs) as pool:
        res = np.array(list(pool.map(_point, args, chunksize=8)), dtype=float)
    ma, e_r, liq, eps_r, q_r, capped, me_op = res.T
    ok = np.isfinite(e_r)
    solved = ok & (capped == 0)
    q_ep = (on.ep_heat_transfer_rate.to_numpy())
    e_acc = on.pl_e_poppe.to_numpy() * RHO_REF
    e_epsat_acc = on.pl_e_epsat.to_numpy() * RHO_REF
    ma_ep = on.pl_airmass.to_numpy() * on.pl_airscale.to_numpy()
    s = solved
    return {
        "site": run.name, "LG_design": lg_d, "fill_exp": n_exp, "Me_design_realistic": des["Me_d"],
        "n_sampled": len(on), "capped_%": 100 * float(np.mean(capped[ok] > 0)), "failed_%": 100 * float(np.mean(~ok)),
        "air_ratio_realistic_vs_EP_median": float(np.median(ma[s] / ma_ep[s])),
        "Me_operating_median": float(np.median(me_op[s])),
        "poppe_realistic_vs_accounting_%": 100 * (e_r[s].sum() / e_acc[s].sum() - 1),
        "EPSAT_realistic_vs_poppe_realistic_%": 100 * (eps_r[s].sum() / e_r[s].sum() - 1),
        "EPSAT_realistic_vs_poppe_realistic_vapour_%": 100 * (eps_r[s].sum() / (e_r[s] - liq[s]).sum() - 1),
        "EPSAT_accounting_vs_poppe_accounting_%": 100 * (e_epsat_acc[s].sum() / e_acc[s].sum() - 1),
        "EP_vs_poppe_realistic_%": 100 * (e_epsat_acc[s].sum() / e_r[s].sum() - 1),
        "mist_share_realistic_%": 100 * liq[s].sum() / e_r[s].sum(),
        "heat_check_%": 100 * (q_r[s].sum() / q_ep[s].sum() - 1),
    }


def table(run_root, df):
    """Per-site design point of the EnergyPlus tower and the ordinary-fill result -> results/study/realistic_fill_table.tex."""
    import review_analyses as ra
    from study_report import nice
    study = ROOT / "results" / "study"
    sites = pd.read_csv(study / "dc_sites.csv").sort_values("wb_mean")
    mist = pd.read_csv(study / "review_mist_correction.csv").set_index("site")
    rows = []
    for site in sites.site:
        run = run_root / site
        me_ep, lg_ep, _ = ra.design_fill(run)
        tow = [o for o in idf.parse((run / "model.idf").read_text()) if o[0].lower() == "coolingtower:variablespeed:merkel"][0]
        g = df[df.site == site].set_index("LG_design")
        rows.append(dict(site=site, wb_design=float(idf.field(tow, 25)), Me_design_EP=me_ep, LG_design_EP=lg_ep,
                         corr_share=mist.loc[site, "adjusted_hours_share_%"],
                         ep_vs_poppe_base=mist.loc[site, "EP_vs_poppe_%"],
                         Me_design_ord=g.loc[1.2, "Me_design_realistic"],
                         ord_min=g["EPSAT_realistic_vs_poppe_realistic_%"].min(),
                         ord_max=g["EPSAT_realistic_vs_poppe_realistic_%"].max(),
                         ord_12=g.loc[1.2, "EPSAT_realistic_vs_poppe_realistic_%"],
                         poppe_shift=g.loc[1.2, "poppe_realistic_vs_accounting_%"],
                         air_ratio=g.loc[1.2, "air_ratio_realistic_vs_EP_median"],
                         capped=g.loc[1.2, "capped_%"]))
    t = pd.DataFrame(rows)
    t.to_csv(study / "realistic_fill_sites.csv", index=False)
    L = ["\\begin{tabular}{lrrrrrrrrr}", "\\toprule",
         " & \\multicolumn{4}{c}{EnergyPlus tower (base plant)} & \\multicolumn{5}{c}{Ordinary fill, design $L/G$ = 1.0--1.4} \\\\",
         "\\cmidrule(lr){2-5}\\cmidrule(lr){6-10}",
         "Site & $T_{wb,d}$ & $Me_{P,d}$ & corr. & EP vs P & $Me_{P,d}$ & EP vs P & EP vs P & P shift & capped \\\\",
         " & [\\textdegree C] & & [\\% h] & [\\%] & ($L/G$=1.2) & ($L/G$=1.2) [\\%] & range [\\%] & [\\%] & [\\% h] \\\\",
         "\\midrule"]
    for r in t.itertuples():
        L.append("%s & %.1f & %.1f & %.0f & %+.1f & %.2f & %+.1f & %+.1f to %+.1f & %+.1f & %.1f \\\\" % (
            nice(r.site), r.wb_design, r.Me_design_EP, r.corr_share, r.ep_vs_poppe_base, r.Me_design_ord, r.ord_12,
            r.ord_min, r.ord_max, r.poppe_shift, r.capped))
    L += ["\\bottomrule", "\\end{tabular}"]
    (study / "realistic_fill_table.tex").write_text("\n".join(L) + "\n")
    print(t.round(2).to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_root", type=Path)
    ap.add_argument("--lg", nargs="*", type=float, default=[1.0, LG_DESIGN, 1.4])
    ap.add_argument("--table-only", action="store_true", help="rebuild the table from realistic_fill_check.csv")
    a = ap.parse_args()
    if a.table_only:
        table(a.run_root, pd.read_csv(ROOT / "results" / "study" / "realistic_fill_check.csv"))
        return
    rows = []
    for run in sorted(p for p in a.run_root.iterdir() if (p / "out" / "eplusout.csv").exists()):
        _, frames, _ = analyze.load(run)
        d = next(iter(frames.values()))
        for lg in a.lg:
            rows.append(site_check(run, d, lg_d=lg))
            print("done", run.name, lg, flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "study" / "realistic_fill_check.csv", index=False)
    table(a.run_root, df)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(df.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
