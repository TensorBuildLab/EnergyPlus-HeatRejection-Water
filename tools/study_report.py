#!/usr/bin/env python3
"""Tables and figures for the multi-climate data center study.

  python tools/study_report.py runs/dc        # -> results/study/*.csv, *.tex and results/figures/fig_dc_*.png/pdf
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "models"))
import analyze  # noqa: E402
import figstyle as fs  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import summarize_dc_run  # noqa: E402

ORDER = ["EPSAT", "MSAT", "BRAUN", "POPPE1", "LF", "ROT", "LAT"]
NICE = {"phoenix_tmyx": "Phoenix", "las_vegas": "Las Vegas", "portland_or": "Portland OR"}
SOURCE = "example_hard_groundwater"


def nice(site):
    return NICE.get(site, site.replace("_", " ").title())


def climate_zone(site):
    for f in (ROOT / "weather" / site).glob("*.stat"):
        m = re.search(r'Climate Zone "([0-9][A-C]?)"', f.read_text(encoding="latin-1"))
        if m:
            return m.group(1)
    return "?"


def site_table(run_root: Path) -> pd.DataFrame:
    summ = pd.read_csv(run_root / "summary.csv")
    scen = pd.read_csv(run_root / "scenarios.csv")
    rows = []
    for _, r in summ.iterrows():
        site = r["site"]
        fac = summarize_dc_run.summarize(str(run_root / site / "out"))
        it_kwh = fac["IT energy (CPU+server fans) [MWh]"] * 1e3
        cfg, frames, dt_h = analyze.load(run_root / site)
        d = frames[r["tower"]]
        sc = scen[(scen.site == site)]

        def mk(method, source, mode):
            x = sc[(sc.method == method) & (sc.source == source) & (sc["mode"] == mode)]
            return float(x.makeup_m3.iloc[0]) if len(x) else np.nan

        row = {
            "site": site, "name": nice(site), "cz": climate_zone(site),
            "wb_mean": d.site_wetbulb_temperature.mean(), "db_mean": d.site_drybulb_temperature.mean(),
            "PUE": fac["PUE (facility / IT)"], "IT_MWh": it_kwh / 1e3, "heat_MWh": r["heat_rejected_MWh"],
            "evap_POPPE_m3": r["POPPE_m3"], "evap_EP_m3": r["EP_evap_m3"],
            "EP_vs_POPPE_%": r["EP_vs_POPPE_%"],
            "L_per_kWh_heat_POPPE": r["POPPE_m3"] * 1e3 / (r["heat_rejected_MWh"] * 1e3),
            "WUE_EP": mk("EnergyPlus", "-", "fixed") * 1e3 / it_kwh,
            "WUE_POPPE_fixed": mk("POPPE", SOURCE, "fixed") * 1e3 / it_kwh,
            "WUE_POPPE_constituent": mk("POPPE", SOURCE, "constituent") * 1e3 / it_kwh,
            "WUE_POPPE_dynamic": mk("POPPE", SOURCE, "dynamic") * 1e3 / it_kwh,
            "WUE_POPPE_min_scen": min(mk("POPPE", s, m) for s in sc.source.unique() if s != "-"
                                      for m in ("constituent", "dynamic")) * 1e3 / it_kwh,
            "WUE_POPPE_max_scen": max(mk("POPPE", s, m) for s in sc.source.unique() if s != "-"
                                      for m in ("constituent", "dynamic")) * 1e3 / it_kwh,
            "fog_h": r["fog_hours"], "air_adjusted_share_%": r.get("ref_air_adjusted_share_%", 0.0),
            "air_scale_mean": r.get("air_scale_mean_adjusted", np.nan),
            "EPSAT_replica_err_%": r["EPSAT_replica_err_%"],
        }
        for m in ORDER:
            row["dev_" + m] = r["%s_vs_POPPE_%%" % m]
        rows.append(row)
    return pd.DataFrame(rows).sort_values("wb_mean").reset_index(drop=True)


# ---------------------------------------------------------------------------
def fig_deviation_heatmap(t, out):
    z = t[["dev_" + m for m in ORDER]].to_numpy()
    fig, ax = plt.subplots(figsize=(7.2, 0.33 * len(t) + 1.4))
    lim = 30
    im = ax.imshow(np.clip(z, -lim, lim), cmap=fs.DIVERGING, vmin=-lim, vmax=lim, aspect="auto")
    for i in range(z.shape[0]):
        for j in range(z.shape[1]):
            ax.text(j, i, "%+.1f" % z[i, j], ha="center", va="center", fontsize=7,
                    color="white" if abs(z[i, j]) > 0.6 * lim else fs.TEXT)
    ax.set_xticks(range(len(ORDER)))
    ax.set_xticklabels([fs.METHOD_LABEL[m].replace(" (reference)", "") for m in ORDER], rotation=30, ha="right")
    ax.set_yticks(range(len(t)))
    ax.set_yticklabels(["%s (%s, WB %.1f°C)" % (n, c, w) for n, c, w in zip(t.name, t.cz, t.wb_mean)])
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02, extend="both")
    cb.set_label("Annual evaporation vs Poppe [%]")
    ax.set_title("Annual tower evaporation of each method relative to Poppe (sites by mean wet-bulb)", loc="left")
    fs.save(fig, out / "fig_dc_method_deviation")


def fig_wue(t, out):
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    x = np.arange(len(t))
    ax.vlines(x, t.WUE_POPPE_min_scen, t.WUE_POPPE_max_scen, color=fs.SERIES[0], alpha=0.35, linewidth=6,
              label="Poppe, range over makeup sources and chemistry modes")
    ax.plot(x, t.WUE_POPPE_constituent, "o", color=fs.SERIES[0], markersize=7,
            label="Poppe, hard groundwater, constituent limits")
    ax.plot(x, t.WUE_EP, "D", color=fs.SERIES[3], markersize=6, markeredgecolor=fs.SURFACE,
            label="EnergyPlus default (SaturatedExit, 4 cycles)")
    ax.set_xticks(x)
    ax.set_xticklabels(t.name, rotation=35, ha="right")
    ax.set_ylabel("WUE, site makeup / IT energy [L/kWh]")
    ax.set_ylim(0, 3.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=2, fontsize=7.5)
    ax.set_title("Water usage effectiveness by climate (sites by mean wet-bulb)", loc="left")
    fs.save(fig, out / "fig_dc_wue")


def fig_monthly(run_root, sites, out):
    fig, axes = plt.subplots(1, len(sites), figsize=(7.2, 2.4), sharey=True, constrained_layout=True)
    for ax, site in zip(axes, sites):
        cfg, frames, dt_h = analyze.load(run_root / site)
        d = next(iter(frames.values())).copy()
        d["month"] = d.time.str.strip().str.slice(0, 2).astype(int)
        sec = dt_h * 3600
        g = d.groupby("month")[["pl_e_poppe", "pl_e_epsat", "pl_e_lf"]].sum() * sec / 1e3
        ax.plot(g.index, g.pl_e_poppe, color=fs.METHOD_COLOR["POPPE"], label="Poppe")
        ax.plot(g.index, g.pl_e_epsat, color=fs.METHOD_COLOR["EPSAT"], label="EnergyPlus SaturatedExit")
        ax.plot(g.index, g.pl_e_lf, color=fs.METHOD_COLOR["LF"], linestyle="--", label="LossFactor 0.2 %/K")
        ax.set_title(nice(site))
        ax.set_xticks([1, 4, 7, 10])
        ax.set_xticklabels(["Jan", "Apr", "Jul", "Oct"])
    axes[0].set_ylabel("Evaporation [1000 m³/month]")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=7.5, bbox_to_anchor=(0.5, -0.12))
    fs.save(fig, out / "fig_dc_monthly")


def fig_hourly_vs_ambient(run_root, sites, out):
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True, constrained_layout=True)
    xs, ys, ds = [], [], []
    for site in sites:
        _, frames, _ = analyze.load(run_root / site)
        d = next(iter(frames.values()))
        on = d[(d.ep_heat_transfer_rate > 0) & (d.pl_e_poppe > 0)]
        xs.append(on.site_drybulb_temperature)
        ys.append(on.site_humidity_ratio * 1e3)
        ds.append(100 * (on.pl_e_epsat / on.pl_e_poppe - 1))
    x, y, dv = pd.concat(xs), pd.concat(ys), pd.concat(ds)
    hb = axes[0].hexbin(x, dv, gridsize=45, cmap="Blues", mincnt=1, bins="log")
    axes[0].set_xlabel("Outdoor dry-bulb [°C]")
    axes[0].set_ylabel("EnergyPlus SaturatedExit vs Poppe [%]")
    axes[0].axhline(0, color=fs.TEXT2, linewidth=0.8)
    axes[1].hexbin(y, dv, gridsize=45, cmap="Blues", mincnt=1, bins="log")
    axes[1].set_xlabel("Outdoor humidity ratio [g/kg]")
    axes[1].axhline(0, color=fs.TEXT2, linewidth=0.8)
    fig.colorbar(hb, ax=axes, label="Timesteps (log)", shrink=0.85)
    fs.save(fig, out / "fig_dc_timestep_deviation")


def latex_table(t, path):
    cols = ["name", "cz", "wb_mean", "PUE", "heat_MWh", "evap_POPPE_m3", "L_per_kWh_heat_POPPE", "EP_vs_POPPE_%",
            "dev_LF", "WUE_EP", "WUE_POPPE_constituent"]
    head = ("Site & CZ & $\\bar T_{wb}$ & PUE & $Q$ [MWh] & $E_{Poppe}$ [m$^3$] & L/kWh$_{th}$ & EP SatExit [\\%] & "
            "LossFactor [\\%] & WUE$_{EP}$ & WUE$_{Poppe}$ \\\\")
    lines = ["\\begin{tabular}{llrrrrrrrrr}", "\\toprule", head, "\\midrule"]
    for _, r in t[cols].iterrows():
        lines.append("%s & %s & %.1f & %.3f & %.0f & %.0f & %.2f & %+.1f & %+.1f & %.2f & %.2f \\\\" % tuple(r))
    lines += ["\\bottomrule", "\\end{tabular}"]
    path.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_root", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    a = ap.parse_args()
    fs.apply()
    figs, study = a.out / "figures", a.out / "study"
    study.mkdir(parents=True, exist_ok=True)
    t = site_table(a.run_root)
    t.to_csv(study / "dc_sites.csv", index=False)
    latex_table(t, study / "dc_sites_table.tex")
    fig_deviation_heatmap(t, figs)
    fig_wue(t, figs)
    rep = [s for s in ("phoenix_tmyx", "singapore", "frankfurt", "stockholm") if s in set(t.site)]
    fig_monthly(a.run_root, rep, figs)
    fig_hourly_vs_ambient(a.run_root, list(t.site), figs)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(t.drop(columns=["site"]).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
