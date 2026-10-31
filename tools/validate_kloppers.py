#!/usr/bin/env python3
"""Check the Poppe implementation against 126 measured counterflow fill tests (Kloppers 2003, Appendices R-T).

For each test the measured inlet air, water temperatures and flows are given. We compute:
  * the Poppe Merkel number and compare it with Kloppers' own Poppe analysis of the same test (implementation check);
  * the Poppe outlet-air temperature and compare it with the MEASURED outlet-air temperature (physics check);
  * a rating test: fit the fill characteristic Me = c (L/G)^-n (or c Gw^b Ga^c) and predict the leaving-water
    temperature; also the single-point n = 0.6 law used in tools/review_analyses.py.

  python tools/validate_kloppers.py      # -> results/validation/kloppers_*.csv, results/figures/fig_kloppers_validation
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import figstyle as fs  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from tower_water import evaporation as ev  # noqa: E402
from tower_water import psychro as ps  # noqa: E402

DATA = ROOT / "data" / "equipment" / "kloppers2003_fill_tests.csv"
N_STEPS = 20


def rms(x):
    return float(np.sqrt(np.mean(np.square(x))))


def main():
    df = pd.read_csv(DATA)
    pts = []
    for r in df.itertuples():
        w = ps.w_from_twb(r.Tdb_in_C, r.Twb_in_C, r.p_Pa)
        res = ev.poppe(r.Tw_in_C, r.Tw_out_C, r.mw_kg_s, r.ma_kg_s, r.Tdb_in_C, w, r.p_Pa, n_steps=N_STEPS)
        me_m = ev.merkel_number_exact(r.Tw_in_C, r.Tw_out_C, r.mw_kg_s, r.ma_kg_s, ps.h_air(r.Tdb_in_C, w), r.p_Pa)
        pts.append(dict(fill=r.fill, Lfi_m=r.Lfi_m, test=r.test, LG=r.mw_kg_s / r.ma_kg_s, Gw=r.Gw, Ga=r.Ga,
                        tw_in=r.Tw_in_C, tw_out=r.Tw_out_C, mw=r.mw_kg_s, ma=r.ma_kg_s, tdb=r.Tdb_in_C, w=w, p=r.p_Pa,
                        MeP=res.merkel, MeP_K=r.Me_Poppe, MeM=me_m, MeM_K=r.Me_Merkel,
                        Ta_out=res.t_air_out, Ta_out_meas=r.Ta_out_meas_C, Ta_out_K=r.Ta_out_Poppe_C,
                        evap=res.evap_kg_s, status=res.status))
    p = pd.DataFrame(pts)
    summ = []
    for (fill, lfi), g in p.groupby(["fill", "Lfi_m"], sort=False):
        lg, gw, ga, me = g.LG.to_numpy(), g.Gw.to_numpy(), g.Ga.to_numpy(), g.MeP.to_numpy()
        c1, n1 = np.linalg.lstsq(np.c_[np.ones_like(lg), np.log(lg)], np.log(me), rcond=None)[0]
        a2, b2, c2 = np.linalg.lstsq(np.c_[np.ones_like(lg), np.log(gw), np.log(ga)], np.log(me), rcond=None)[0]
        i0 = int(np.argmin(abs(np.log(lg) - np.median(np.log(lg)))))
        e1, e2, e3, ev3 = [], [], [], []
        for i, o in enumerate(g.itertuples()):
            for m, e in ((math.exp(c1) * lg[i] ** n1, e1), (math.exp(a2) * gw[i] ** b2 * ga[i] ** c2, e2),
                         (me[i0] * (lg[i] / lg[i0]) ** -0.6, e3)):
                t = ev.outlet_temperature_poppe(m, o.tw_in, o.mw, o.ma, o.tdb, o.w, o.p, n_steps=N_STEPS)
                e.append(t - o.tw_out)
                if e is e3:
                    ev3.append(ev.poppe(o.tw_in, t, o.mw, o.ma, o.tdb, o.w, o.p, n_steps=N_STEPS).evap_kg_s / o.evap - 1)
        p.loc[g.index, "Tw_out_err_n06_K"] = e3
        summ.append(dict(fill=fill, Lfi_m=lfi, n=len(g),
                         MeP_vs_Kloppers_mean_pct=100 * np.mean(me / g.MeP_K - 1),
                         MeP_vs_Kloppers_maxabs_pct=100 * np.max(abs(me / g.MeP_K - 1)),
                         MeM_vs_Kloppers_mean_pct=100 * np.mean(g.MeM / g.MeM_K - 1),
                         Ta_out_vs_Kloppers_mean_K=float(np.mean(g.Ta_out - g.Ta_out_K)),
                         Ta_out_vs_meas_bias_K=float(np.mean(g.Ta_out - g.Ta_out_meas)),
                         Ta_out_vs_meas_rms_K=rms(g.Ta_out - g.Ta_out_meas),
                         fill_n_LG=-n1, fill_b_Gw=b2, fill_c_Ga=c2,
                         Tw_out_rms_fitLG_K=rms(e1), Tw_out_rms_fitGwGa_K=rms(e2), Tw_out_rms_n06_K=rms(e3),
                         evap_err_n06_mean_pct=100 * np.mean(ev3), evap_err_n06_maxabs_pct=100 * np.max(np.abs(ev3))))
    s = pd.DataFrame(summ)
    out = ROOT / "results" / "validation"
    out.mkdir(parents=True, exist_ok=True)
    p.drop(columns=["w"]).to_csv(out / "kloppers_points.csv", index=False)
    s.to_csv(out / "kloppers_summary.csv", index=False)
    allp = dict(n=len(p), MeP_mean_pct=100 * np.mean(p.MeP / p.MeP_K - 1),
                MeP_median_abs_pct=100 * np.median(abs(p.MeP / p.MeP_K - 1)),
                MeP_p95_abs_pct=100 * np.percentile(abs(p.MeP / p.MeP_K - 1), 95),
                Ta_vs_K_maxabs_K=float(np.max(abs(p.Ta_out - p.Ta_out_K))),
                Ta_vs_meas_bias_K=float(np.mean(p.Ta_out - p.Ta_out_meas)), Ta_vs_meas_rms_K=rms(p.Ta_out - p.Ta_out_meas),
                Kloppers_Ta_vs_meas_rms_K=rms(p.Ta_out_K - p.Ta_out_meas),
                evap_frac_min_pct=100 * float((p.evap / p.mw).min()), evap_frac_max_pct=100 * float((p.evap / p.mw).max()))
    pd.DataFrame([allp]).to_csv(out / "kloppers_overall.csv", index=False)

    # LaTeX table
    lines = ["\\begin{tabular}{llrrrrrr}", "\\toprule",
             "Fill & $L_{fi}$ [m] & $Me_P$ vs K. [\\%] & $T_{a,o}$ vs meas. bias / rms [K] & $n$ & "
             "$T_{w,o}$ rms, $n$=0.6 [K] & $T_{w,o}$ rms, $G_w,G_a$ fit [K] & $E$ err., $n$=0.6 [\\%] \\\\", "\\midrule"]
    for r in s.itertuples():
        lines.append("%s & %.2f & %+.1f (max %.1f) & %+.2f / %.2f & %.2f & %.2f & %.2f & %+.1f (max %.1f) \\\\" % (
            r.fill.replace("_", " "), r.Lfi_m, r.MeP_vs_Kloppers_mean_pct, r.MeP_vs_Kloppers_maxabs_pct,
            r.Ta_out_vs_meas_bias_K, r.Ta_out_vs_meas_rms_K, r.fill_n_LG, r.Tw_out_rms_n06_K, r.Tw_out_rms_fitGwGa_K,
            r.evap_err_n06_mean_pct, r.evap_err_n06_maxabs_pct))
    lines += ["\\bottomrule", "\\end{tabular}"]
    (ROOT / "results" / "study" / "kloppers_table.tex").write_text("\n".join(lines) + "\n")

    # Figure
    fs.apply()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), constrained_layout=True)
    fills = list(dict.fromkeys(p.fill))
    marks = ["o", "s", "^", "D"]
    for k, f in enumerate(fills):
        g = p[p.fill == f]
        kw = dict(marker=marks[k % 4], linestyle="none", markersize=4.5, color=fs.SERIES[k], label=f.replace("_", " "),
                  markeredgecolor=fs.SURFACE, markeredgewidth=0.6)
        axes[0].plot(g.MeP_K, g.MeP, **kw)
        axes[1].plot(g.Ta_out_meas, g.Ta_out, **kw)
    for ax, lab in ((axes[0], "Merkel number"), (axes[1], "Outlet air temperature [°C]")):
        lo, hi = ax.get_xlim()[0], ax.get_xlim()[1]
        lo, hi = min(lo, ax.get_ylim()[0]), max(hi, ax.get_ylim()[1])
        ax.plot([lo, hi], [lo, hi], color=fs.TEXT2, linewidth=0.8, zorder=0)
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_aspect("equal")
    axes[0].set_xlabel("$Me_P$, Kloppers (2003) Poppe analysis")
    axes[0].set_ylabel("$Me_P$, this implementation")
    axes[1].set_xlabel("$T_{a,o}$ measured [°C]")
    axes[1].set_ylabel("$T_{a,o}$ predicted, Poppe [°C]")
    axes[0].legend(fontsize=7, loc="upper left")
    fs.save(fig, ROOT / "results" / "figures" / "fig_kloppers_validation")
    pd.set_option("display.width", 250)
    print(s.round(3).to_string(index=False))
    print(pd.DataFrame([allp]).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
