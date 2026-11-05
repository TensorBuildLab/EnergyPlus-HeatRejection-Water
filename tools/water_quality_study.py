#!/usr/bin/env python3
"""Site-specific makeup-water quality: cycles of concentration, blowdown and WUE (no re-simulation).

Each site is paired with its own municipal supply (data/water_sources_sourced.json, sources documented in
docs/WATER_QUALITY_SOURCES.md) and evaluated under every sourced treatment program. Blowdown and makeup are
recomputed from the stored timestep evaporation and water temperatures, as in tools/scenarios.py.

  python tools/water_quality_study.py runs/dc     # -> results/study/water_quality_*.csv/.tex, fig_dc_water_quality
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "models"))
import analyze  # noqa: E402
import figstyle as fs  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import summarize_dc_run  # noqa: E402
from scenarios import coc_series  # noqa: E402
from study_report import climate_zone, nice  # noqa: E402
from tower_water.chemistry import ChemistryModel  # noqa: E402

LIB = ROOT / "data" / "water_sources_sourced.json"
FIXED = 4.0
METHODS = ["POPPE", "EPSAT"]


def site_rows(run: Path, lib: dict, it_kwh: float):
    cfg, frames, dt_h = analyze.load(run)
    sec = dt_h * 3600.0
    site = run.name
    d = next(iter(frames.values()))
    loaded = (d["ep_heat_transfer_rate"] > 0).to_numpy()
    t_hot, t_cold = d["ep_inlet_temperature"].to_numpy(), d["ep_outlet_temperature"].to_numpy()
    drift = d["pl_drift"].to_numpy() * loaded
    rows = []
    cases = [("fixed_%g" % FIXED, None, "fixed")]
    for tk, tr in lib["treatments"].items():
        mode = "dynamic" if tr.get("lsi_max") is not None or tr.get("silica_solubility_factor") else "constituent"
        cases.append((tk, tk, mode))
    for case, treat, mode in cases:
        if mode == "fixed":
            model = ChemistryModel.from_library(str(LIB), site, next(iter(lib["treatments"])), FIXED, "fixed")
        else:
            model = ChemistryModel.from_library(str(LIB), site, treat, None, mode)
        coc = coc_series(model, t_hot, t_cold)
        tl = model.treatment
        at_cap = float(np.mean(np.isclose(coc[loaded], tl.max_cycles))) if mode != "fixed" else 0.0
        at_floor = float(np.mean(np.isclose(coc[loaded], tl.min_cycles))) if mode != "fixed" else 0.0
        # limiting constraint at the annual-mean temperatures (dynamic) or constant (constituent)
        if mode == "dynamic":
            which = model.cycles(t_hot=float(np.mean(t_hot[loaded])), t_cold=float(np.mean(t_cold[loaded])))[1]
        else:
            which = model.cycles()[1]
        for m in METHODS:
            e = d["pl_e_" + m.lower()].to_numpy() * loaded
            b = np.maximum(e / (coc - 1.0) - drift, 0.0) * loaded
            mk = (e + drift + b).sum() * sec
            rows.append({"site": site, "case": case, "mode": mode, "method": m,
                         "coc_mean": float(np.mean(coc[loaded])), "coc_min": float(np.min(coc[loaded])),
                         "limit": which, "evap_m3": e.sum() * sec, "blowdown_m3": b.sum() * sec, "makeup_m3": mk,
                         # effective annual cycles: N such that E/(N-1) = B + D over the year (reproduces the WUE)
                         "coc_effective": e.sum() / (b.sum() + drift.sum()) + 1.0,
                         "at_cap_share": at_cap, "at_floor_share": at_floor,
                         "clamp": "cap" if at_cap > 0.5 else ("floor" if at_floor > 0.5 else ""),
                         "WUE": mk * 1e3 / it_kwh})
    return rows


def conf_code(text):
    t = text.split("(")[0].strip().lower()
    return {"high": "H", "medium-high": "M--H", "medium": "M", "low-medium": "L--M", "low": "L"}.get(t, "?")


LIMIT_NAMES = {"m_alkalinity": "alkalinity", "max_cycles": "cap (10)", "calcium_hardness": "Ca hardness",
               "silica_solubility": "silica", "LSI": "LSI"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_root", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    a = ap.parse_args()
    lib = json.loads(LIB.read_text())
    rows = []
    for run in sorted(p for p in a.run_root.iterdir() if (p / "out" / "eplusout.csv").exists()):
        if run.name not in lib["sources"]:
            print("no water data for", run.name)
            continue
        it_kwh = summarize_dc_run.it_energy_mwh(str(run / "out")) * 1e3
        rows += site_rows(run, lib, it_kwh)
        print("done", run.name)
    df = pd.DataFrame(rows)
    study = a.out / "study"
    df.to_csv(study / "water_quality_cases.csv", index=False)

    p = df[df.method == "POPPE"]
    e = df[df.method == "EPSAT"]
    treat = [c for c in p.case.unique() if not c.startswith("fixed")]
    key = []
    for site, g in p.groupby("site"):
        g = g.set_index("case")
        ge = e[e.site == site].set_index("case")
        fixed = g.loc["fixed_%g" % FIXED]
        tr = g.loc[treat]
        src = lib["sources"][site]
        free = tr[tr.clamp == ""]
        limited = set()
        for t in lib["treatments"].values():
            limited |= set(t.get("limits", {}))
        missing = [c for c in ("silica", "chloride", "sulfate", "calcium_hardness", "m_alkalinity")
                   if c in limited and not src.get(c)]
        key.append({
            "site": site, "name": nice(site), "cz": climate_zone(site),
            "ca": src.get("calcium_hardness"), "alk": src.get("m_alkalinity"), "sio2": src.get("silica"),
            "cl": src.get("chloride"), "so4": src.get("sulfate"), "tds": src.get("tds"),
            "conf": conf_code(src.get("confidence", "")),
            "N_min": tr.coc_mean.min(), "N_max": tr.coc_mean.max(),
            "Neff_min": tr.coc_effective.min(), "Neff_max": tr.coc_effective.max(),
            "n_cap": int((tr.clamp == "cap").sum()), "n_floor": int((tr.clamp == "floor").sum()), "n_sets": len(tr),
            "missing": "/".join(missing),
            "unclamped_min_%": 100 * (free.WUE.min() / fixed.WUE - 1) if len(free) else np.nan,
            "unclamped_max_%": 100 * (free.WUE.max() / fixed.WUE - 1) if len(free) else np.nan,
            "unclamped_median_%": 100 * (free.WUE.median() / fixed.WUE - 1) if len(free) else np.nan,
            "limit_at_min": tr.loc[tr.coc_mean.idxmin(), "limit"],
            "WUE_fixed4": fixed.WUE, "WUE_min": tr.WUE.min(), "WUE_max": tr.WUE.max(),
            "chem_vs_fixed_min_%": 100 * (tr.WUE.min() / fixed.WUE - 1),
            "chem_vs_fixed_max_%": 100 * (tr.WUE.max() / fixed.WUE - 1),
            # evaporation-model effect on makeup, at fixed 4 cycles
            "model_effect_%": 100 * (ge.loc["fixed_%g" % FIXED].WUE / fixed.WUE - 1),
        })
    k = pd.DataFrame(key)
    order = pd.read_csv(study / "dc_sites.csv")[["site", "wb_mean"]] if (study / "dc_sites.csv").exists() else None
    if order is not None:
        k = k.merge(order, on="site").sort_values("wb_mean")
    k.to_csv(study / "water_quality_key.csv", index=False)

    def f(v, fmt="%.0f"):
        return "--" if v is None or (isinstance(v, float) and not np.isfinite(v)) else fmt % v
    lines = ["\\begin{tabular}{lrrrrlrlrrr}", "\\toprule",
             "Site & Ca & Alk. & SO$_4$ & Cl & Data & $N_{c,\\mathrm{eff}}$ & Limit (lowest $N_c$) & WUE$_{N=4}$ & "
             "$\\Delta$WUE, all sets & $\\Delta$WUE, unclamped \\\\",
             " & \\multicolumn{4}{c}{[mg/L; Ca, Alk.\\ as CaCO$_3$]} & & & & [L/kWh] & [\\%] & [\\%] \\\\",
             "\\midrule"]
    for _, r in k.iterrows():
        lim = str(r.limit_at_min).split(" ")[0]
        lo, hi = r["chem_vs_fixed_min_%"], r["chem_vs_fixed_max_%"]
        lo_s = "%+.0f%s" % (lo, "$^c$" if r.n_cap else "")
        hi_s = "%+.0f%s" % (hi, "$^f$" if r.n_floor else "")
        unc = "--" if not np.isfinite(r["unclamped_min_%"]) else "%+.0f to %+.0f" % (r["unclamped_min_%"], r["unclamped_max_%"])
        lines.append("%s & %s & %s & %s & %s & %s%s & %.1f--%.1f & %s & %.2f & %s to %s & %s \\\\" % (
            r["name"], f(r.ca), f(r.alk), f(r.so4), f(r.cl), r.conf, "$^\\dagger$" if r.missing else "",
            r.Neff_min, r.Neff_max, LIMIT_NAMES.get(lim, lim) + (" (min.)" if "raised" in str(r.limit_at_min) else ""),
            r.WUE_fixed4, lo_s, hi_s, unc))
    lines += ["\\bottomrule", "\\end{tabular}"]
    (study / "water_quality_table.tex").write_text("\n".join(lines) + "\n")

    fs.apply()
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    x = np.arange(len(k))
    ax.vlines(x, k.WUE_min, k.WUE_max, color=fs.SERIES[0], alpha=0.4, linewidth=6,
              label="Poppe, local makeup water, range over treatment programs")
    ax.plot(x, k.WUE_min, "_", color=fs.SERIES[0], markersize=12, markeredgewidth=2)
    ax.plot(x, k.WUE_max, "_", color=fs.SERIES[0], markersize=12, markeredgewidth=2)
    for i, r in enumerate(k.itertuples()):
        if r.n_cap:
            ax.annotate("cap", (i, r.WUE_min), xytext=(0, -10), textcoords="offset points", ha="center", fontsize=6.5,
                        color=fs.TEXT2)
        if r.n_floor:
            ax.annotate("floor", (i, r.WUE_max), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=6.5,
                        color=fs.TEXT2)
    ax.plot(x, k.WUE_fixed4, "o", color=fs.SERIES[0], markersize=7, label="Poppe, fixed 4 cycles")
    ax.plot(x, k.WUE_fixed4 * (1 + k["model_effect_%"] / 100), "D", color=fs.SERIES[3], markersize=6,
            markeredgecolor=fs.SURFACE, label="EnergyPlus SaturatedExit, fixed 4 cycles")
    ax.set_xticks(x)
    ax.set_xticklabels(k.name, rotation=35, ha="right")
    ax.set_ylabel("WUE, site makeup / IT energy [L/kWh]")
    ax.set_ylim(0, max(3.5, float(k.WUE_max.max()) * 1.08))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=2, fontsize=7.5)
    fs.save(fig, a.out / "figures" / "fig_dc_water_quality")
    pd.set_option("display.width", 250)
    print(k.drop(columns=["site"]).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
