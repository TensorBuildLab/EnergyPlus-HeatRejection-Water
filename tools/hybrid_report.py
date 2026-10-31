#!/usr/bin/env python3
"""Hybrid adiabatic dry cooler: figures and tables for the paper.

Energy is compared only within the hybrid plant (identical hardware across control strategies). The evaporative
tower plant uses a different chiller curve set (no dataset chiller covers both condenser ranges), so the tower
enters only as a water reference.

  python tools/hybrid_report.py runs/hyb [--tower results/study/dc_sites.csv]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import figstyle as fs  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

NICE = {"phoenix_tmyx": "Phoenix", "las_vegas": "Las Vegas", "portland_or": "Portland OR"}
CASES = ["dry", "T32", "T28", "T24", "T20", "T16", "wet"]
OUT_OF_RANGE_H = 50.0          # flag cases with more chiller hours outside curve limits than this
REP = ["riyadh", "phoenix_tmyx", "las_vegas", "dallas", "singapore", "frankfurt"]


def nice(s):
    return NICE.get(s, s.replace("_", " ").title())


def load(run_root, tower_csv):
    h = pd.read_csv(run_root / "hybrid_summary.csv")
    dry = h[h.case == "dry"].set_index("site")
    h["saved_MWh"] = h.site.map(dry.facility_MWh) - h.facility_MWh
    h["saved_pct"] = 100 * h.saved_MWh / h.site.map(dry.facility_MWh)
    h["L_per_kWh_saved"] = np.where(h.saved_MWh > 1.0, h.makeup_m3 / h.saved_MWh, np.nan)
    tw = pd.read_csv(tower_csv).set_index("site") if tower_csv.exists() else None
    if tw is not None:
        h["tower_WUE"] = h.site.map(tw.WUE_POPPE_constituent)
        h["wb_mean"] = h.site.map(tw.wb_mean)
        h["cz"] = h.site.map(tw.cz)
    return h


def fig_tradeoff(h, out):
    sites = [s for s in REP if s in set(h.site)]
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.6), constrained_layout=True)
    for ax, site in zip(axes.flat, sites):
        d = h[h.site == site].set_index("case").loc[CASES].reset_index()
        x = d.saved_pct
        ax.plot(x, d.WUE, "-", color=fs.SERIES[0], linewidth=1.5)
        ok = d.chiller_hours_outside_curve <= OUT_OF_RANGE_H
        ax.plot(x[ok], d.WUE[ok], "o", color=fs.SERIES[0], markersize=5, label="Hybrid, chillers within curve range")
        ax.plot(x[~ok], d.WUE[~ok], "o", markerfacecolor=fs.SURFACE, markeredgecolor=fs.SERIES[0], markersize=5,
                label="Hybrid, chillers > %d h outside curve range" % OUT_OF_RANGE_H)
        for _, r in d.iterrows():
            if r.case in ("dry", "T28", "wet"):
                ax.annotate(r.case, (r.saved_pct, r.WUE), textcoords="offset points", xytext=(4, -9), fontsize=6.5,
                            color=fs.TEXT2)
        if "tower_WUE" in d:
            ax.axhline(d.tower_WUE.iloc[0], color=fs.SERIES[1], linestyle="--", linewidth=1.3,
                       label="Evaporative tower WUE (Poppe)")
        ax.set_title(nice(site))
        ax.set_ylim(0, max(3.0, d.WUE.max() * 1.1))
        ax.set_xlabel("Facility electricity saved vs dry [%]")
    for ax in axes[:, 0]:
        ax.set_ylabel("WUE [L/kWh IT]")
    hdl, lab = axes[0][0].get_legend_handles_labels()
    fig.legend(hdl, lab, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.07), fontsize=7)
    fs.save(fig, out / "fig_hybrid_tradeoff")


def fig_wue_by_site(h, out):
    sites = h[h.case == "dry"].sort_values("wb_mean").site.tolist() if "wb_mean" in h else sorted(set(h.site))
    x = np.arange(len(sites))
    piv = h.pivot_table(index="site", columns="case", values="WUE").loc[sites]
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    tw = h.drop_duplicates("site").set_index("site").loc[sites, "tower_WUE"]
    ax.plot(x, tw, "D", color=fs.SERIES[1], markersize=6, markeredgecolor=fs.SURFACE, label="Evaporative tower (Poppe)")
    ax.plot(x, piv["wet"], "o", color=fs.SERIES[0], markersize=5, markerfacecolor=fs.SURFACE, label="Hybrid, always wet")
    ax.plot(x, piv["T28"], "o", color=fs.SERIES[0], markersize=6, label="Hybrid, wet above 28 °C")
    ax.vlines(x, piv["T28"], piv["wet"], color=fs.SERIES[0], alpha=0.35, linewidth=2)
    ax.set_xticks(x)
    ax.set_xticklabels([nice(s) for s in sites], rotation=35, ha="right")
    ax.set_ylabel("WUE [L/kWh IT]")
    ax.set_ylim(0, 3.2)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3, fontsize=7.5)
    fs.save(fig, out / "fig_hybrid_wue")


def tables(h, study):
    t = h.pivot_table(index="site", columns="case", values=["WUE", "chiller_hours_outside_curve", "saved_pct",
                                                            "L_per_kWh_saved", "wet_hours", "PUE"])
    t.to_csv(study / "hybrid_table.csv")
    rows = []
    for site, d in h.groupby("site"):
        d = d.set_index("case")
        rows.append({"site": site, "name": nice(site), "cz": d["cz"].iloc[0] if "cz" in d else "",
                     "wb": d["wb_mean"].iloc[0] if "wb_mean" in d else np.nan,
                     "tower_WUE": d["tower_WUE"].iloc[0], "WUE_T28": d.loc["T28", "WUE"], "WUE_wet": d.loc["wet", "WUE"],
                     "red_T28_pct": 100 * (1 - d.loc["T28", "WUE"] / d["tower_WUE"].iloc[0]),
                     "out_dry_h": d.loc["dry", "chiller_hours_outside_curve"],
                     "out_T28_h": d.loc["T28", "chiller_hours_outside_curve"],
                     "saved_T28_pct": d.loc["T28", "saved_pct"], "L_kWh_T28": d.loc["T28", "L_per_kWh_saved"],
                     "PUE_dry": d.loc["dry", "PUE"], "PUE_T28": d.loc["T28", "PUE"]})
    k = pd.DataFrame(rows).sort_values("wb")
    k.to_csv(study / "hybrid_key.csv", index=False)
    lines = ["\\begin{tabular}{llrrrrrrrr}", "\\toprule",
             "Site & CZ & WUE$_{tower}$ & WUE$_{T28}$ & WUE$_{wet}$ & $\\Delta$WUE$_{T28}$ [\\%] & "
             "h$_{out}$ dry & h$_{out}$ T28 & $\\Delta E_{T28}$ [\\%] & L/kWh$_{saved}$ \\\\", "\\midrule"]
    for _, r in k.iterrows():
        lk = "--" if not np.isfinite(r.L_kWh_T28) else "%.0f" % r.L_kWh_T28
        lines.append("%s & %s & %.2f & %.2f & %.2f & %+.0f & %.0f & %.0f & %.2f & %s \\\\" % (
            r["name"], r.cz, r.tower_WUE, r.WUE_T28, r.WUE_wet, -r.red_T28_pct, r.out_dry_h, r.out_T28_h,
            r.saved_T28_pct, lk))
    lines += ["\\bottomrule", "\\end{tabular}"]
    (study / "hybrid_table.tex").write_text("\n".join(lines) + "\n")
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_root", type=Path)
    ap.add_argument("--tower", type=Path, default=ROOT / "results" / "study" / "dc_sites.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    a = ap.parse_args()
    fs.apply()
    h = load(a.run_root, a.tower)
    (a.out / "study").mkdir(parents=True, exist_ok=True)
    fig_tradeoff(h, a.out / "figures")
    fig_wue_by_site(h, a.out / "figures")
    k = tables(h, a.out / "study")
    pd.set_option("display.width", 250)
    print(k.drop(columns=["site"]).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
