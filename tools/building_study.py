#!/usr/bin/env python3
"""Compare evaporation models across building cases (prototype buildings, tower types) and climates.

Each case is a run root produced by tools/run_climates.py. Output: results/study/buildings_sites.csv (one row per case
and site), buildings_table.tex, buildings_summary.csv and figure results/figures/fig_buildings_deviation.

  python tools/building_study.py dc_proto=runs/proto_dc office=runs/proto_office dc_vs=runs/dc
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools"), str(ROOT / "models")]
import analyze  # noqa: E402
import figstyle as fs  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import summarize_dc_run  # noqa: E402
from study_report import climate_zone, nice  # noqa: E402
from tower_water import psychro as ps  # noqa: E402

RHO = ps.rho_water(20.0)
METHODS = ["EPSAT", "MSAT", "BRAUN", "POPPE1", "LF", "ROT", "LAT"]
LABEL = {"dc_proto": "Data center prototype (single-speed tower)",
         "office": "Office prototype (single-speed tower)",
         "dc_vs": "Data center, variable-speed tower"}


def mist_m3(d, sec):
    if "pl_mist" in d:
        return float(d.pl_mist.sum() * sec)
    ws = np.array([ps.w_sat(t, p) for t, p in zip(d.pl_airoutt, d.site_barometric_pressure)])
    liq = np.where(d.pl_fog > 0, np.maximum(d.pl_airoutw - ws, 0.0), 0.0) * d.pl_airmass / RHO
    return float(liq.sum() * sec)


def case_rows(case, root: Path):
    rows = []
    for run in sorted(p for p in root.iterdir() if (p / "out" / "eplusout.csv").exists()):
        cfg, frames, dt_h = analyze.load(run)
        sec = dt_h * 3600.0
        d = next(iter(frames.values()))
        on = d[d.ep_heat_transfer_rate > 0]
        q = on.ep_heat_transfer_rate * sec
        e = {m: float(on["pl_e_" + m.lower()].sum() * sec) for m in METHODS + ["POPPE"]}
        mist = mist_m3(on, sec)
        it_mwh = np.nan
        it_mwh = summarize_dc_run.it_energy_mwh(str(run / "out")) or np.nan   # office: no IT equipment
        t = cfg["towers"][0]
        lg = on.ep_mass_flow_rate / on.pl_airmass.where(on.pl_airmass > 0)
        row = {
            "case": case, "site": run.name, "name": nice(run.name), "cz": climate_zone(run.name),
            "wb_mean": d.site_wetbulb_temperature.mean(),
            "tower_type": t["type"], "heat_MWh": q.sum() / 3.6e9, "hours_loaded": len(on) * dt_h,
            "heat_share_below_0C_%": 100 * q[on.site_drybulb_temperature < 0].sum() / q.sum(),
            "heat_share_Tdb_above_30C_%": 100 * q[on.site_drybulb_temperature > 30].sum() / q.sum(),
            "heat_share_Oct_Apr_%": 100 * q[on.time.str.strip().str.slice(0, 2).astype(int).isin(
                [10, 11, 12, 1, 2, 3, 4])].sum() / q.sum(),
            "LG_median": float(np.nanmedian(lg)),
            "POPPE_m3": e["POPPE"], "L_per_kWh_th": e["POPPE"] * 1e3 / (q.sum() / 3.6e6),
            "mist_share_%": 100 * mist / e["POPPE"],
            "EP_own_vs_POPPE_%": 100 * (on.ep_water_evaporation_volume_flow_rate.sum() * sec / e["POPPE"] - 1),
            "EPSAT_vs_POPPE_vapour_%": 100 * (e["EPSAT"] / (e["POPPE"] - mist) - 1),
            "IT_MWh": it_mwh,
            "WUE_POPPE_4cyc": np.nan, "WUE_EPSAT_4cyc": np.nan,
        }
        if "ep_fan_cycling_ratio" in on:
            row["fan_cycling_ratio_mean"] = float(on.ep_fan_cycling_ratio.mean())
        for m in METHODS:
            row["dev_" + m] = 100 * (e[m] / e["POPPE"] - 1)
        if np.isfinite(it_mwh):
            drift = float(on.pl_drift.sum() * sec)
            for m in ("POPPE", "EPSAT"):
                b = max(e[m] / 3.0 - drift, 0.0)          # 4 cycles: B = E/(N-1) - D
                row["WUE_%s_4cyc" % m] = (e[m] + drift + b) * 1e3 / (it_mwh * 1e3)
        rows.append(row)
        print("done", case, run.name, flush=True)
    return rows


def figure(df, out):
    fs.apply()
    order = (df[df.case == df.case.iloc[0]].sort_values("wb_mean").site.tolist())
    cases = [c for c in LABEL if c in set(df.case)]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6), sharey=True, constrained_layout=True)
    y = np.arange(len(order))
    for ax, m, title in zip(axes, ["EPSAT", "MSAT"], ["EnergyPlus SaturatedExit vs Poppe",
                                                       "Merkel saturated exit vs Poppe"]):
        ax.axvline(0, color=fs.TEXT2, linewidth=0.8)
        for k, c in enumerate(cases):
            g = df[df.case == c].set_index("site").reindex(order)
            ax.plot(g["dev_" + m], y + (k - 1) * 0.22, "o", markersize=5.5, color=fs.SERIES[k],
                    markeredgecolor=fs.SURFACE, markeredgewidth=0.8, label=LABEL[c], linestyle="none")
        ax.set_title(title)
        ax.set_xlabel("Annual evaporation difference [%]")
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([nice(s) for s in order])
    axes[0].invert_yaxis()
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=3, fontsize=7, bbox_to_anchor=(0.5, -0.1))
    fs.save(fig, out / "fig_buildings_deviation")


def table(df, path):
    cases = [c for c in LABEL if c in set(df.case)]
    order = df[df.case == cases[0]].sort_values("wb_mean")
    lines = ["\\begin{tabular}{ll" + "rrr" * len(cases) + "}", "\\toprule",
             " & & " + " & ".join("\\multicolumn{3}{c}{%s}" % {"dc_proto": "Data center prototype",
                                                                 "office": "Office prototype",
                                                                 "dc_vs": "Data center, VS tower"}[c] for c in cases)
             + " \\\\",
             "".join("\\cmidrule(lr){%d-%d}" % (3 + 3 * k, 5 + 3 * k) for k in range(len(cases))),
             "Site & CZ & " + " & ".join(["L/kWh$_{th}$ & EPSAT & MSAT"] * len(cases)) + " \\\\",
             "\\midrule"]
    for r in order.itertuples():
        cells = []
        for c in cases:
            g = df[(df.case == c) & (df.site == r.site)]
            if len(g):
                g = g.iloc[0]
                cells.append("%.2f & %+.1f & %+.1f" % (g.L_per_kWh_th, g.dev_EPSAT, g.dev_MSAT))
            else:
                cells.append("-- & -- & --")
        lines.append("%s & %s & %s \\\\" % (r.name, r.cz, " & ".join(cells)))
    lines += ["\\bottomrule", "\\end{tabular}"]
    path.write_text("\n".join(lines) + "\n")


def main():
    cases = dict(a.split("=", 1) for a in sys.argv[1:])
    rows = []
    for c, root in cases.items():
        rows += case_rows(c, ROOT / root if not Path(root).is_absolute() else Path(root))
    df = pd.DataFrame(rows)
    study = ROOT / "results" / "study"
    df.to_csv(study / "buildings_sites.csv", index=False)
    num = df.select_dtypes("number").columns
    summ = df.groupby("case")[list(num)].agg(["min", "max", "median"])
    summ.to_csv(study / "buildings_summary.csv")
    table(df, study / "buildings_table.tex")
    figure(df, ROOT / "results" / "figures")
    # per-case figures for the core case (data center prototype) in results/proto/figures
    if "dc_proto" in cases:
        import study_report as sr
        root = ROOT / cases["dc_proto"]
        figs = ROOT / "results" / "proto" / "figures"
        t = df[df.case == "dc_proto"].sort_values("wb_mean").reset_index(drop=True)
        sr.fig_deviation_heatmap(t, figs)
        sr.fig_monthly(root, ["phoenix_tmyx", "singapore", "frankfurt", "stockholm"], figs)
        sr.fig_hourly_vs_ambient(root, list(t.site), figs)
        # copies under distinct names next to the other paper figures (graphicspath of the manuscript)
        import shutil
        for f in sorted(figs.glob("fig_dc_*.p*")):
            shutil.copy(f, ROOT / "results" / "figures" / f.name.replace("fig_dc_", "fig_proto_dc_"))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 50)
    cols = ["case", "name", "heat_MWh", "heat_share_below_0C_%", "heat_share_Oct_Apr_%", "LG_median", "L_per_kWh_th",
            "mist_share_%", "dev_EPSAT", "dev_MSAT", "dev_BRAUN", "dev_POPPE1", "dev_LF", "dev_ROT", "dev_LAT",
            "EP_own_vs_POPPE_%", "WUE_POPPE_4cyc"]
    print(df[cols].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
