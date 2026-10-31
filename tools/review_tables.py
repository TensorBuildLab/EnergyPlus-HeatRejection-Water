#!/usr/bin/env python3
"""LaTeX tables for manuscript v2 (after review round 1): sites table with vapour/mist split and correction
statistics, plant-sensitivity table. Run after study_report.py and review_analyses.py."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "results" / "study"


def sites():
    t = pd.read_csv(S / "dc_sites.csv")
    m = pd.read_csv(S / "review_mist_correction.csv").set_index("site")
    t = t.join(m[["mist_share_%", "EP_vs_poppe_vapour_only_%", "adjusted_hours_share_%"]], on="site")
    lines = [r"\begin{tabular}{llrrrrrrrrrr}", r"\toprule",
             r"Site & CZ & $\bar T_{wb}$ & PUE & $Q$ & $E_{P}$ & mist & $E_P/Q$ & \multicolumn{2}{c}{EP SatExit vs Poppe [\%]} & corr. & LF \\",
             r" & & [\textdegree C] & & [MWh] & [m$^3$] & [\%] & [L/kWh$_{th}$] & total & vapour & [\% h] & [\%] \\", r"\midrule"]
    for _, r in t.iterrows():
        lines.append("%s & %s & %.1f & %.2f & %.0f & %.0f & %.1f & %.2f & %+.1f & %+.1f & %.0f & %+.0f \\\\" % (
            r["name"], r.cz, r.wb_mean, r.PUE, r.heat_MWh, r.evap_POPPE_m3, r["mist_share_%"], r.L_per_kWh_heat_POPPE,
            r["EP_vs_POPPE_%"], r["EP_vs_poppe_vapour_only_%"], r["adjusted_hours_share_%"], r.dev_LF))
    lines += [r"\bottomrule", r"\end{tabular}"]
    (S / "dc_sites_table_v2.tex").write_text("\n".join(lines) + "\n")


def sensitivity():
    rows = []
    base = pd.read_csv(ROOT / "runs" / "dc" / "summary.csv").set_index("site")
    sites = ["phoenix_tmyx", "singapore", "frankfurt", "stockholm"]
    variants = [("Base (N+1 tower, 18\\,\\textdegree C floor)", base)]
    for v, lab in (("duty_sized", "Tower sized for duty (2 chillers)"), ("cw_floor_15", "Condenser floor 15\\,\\textdegree C"),
                   ("duty_sized_cw_floor_15", "Both")):
        f = ROOT / "runs" / ("sens_" + v) / "summary.csv"
        if f.exists():
            variants.append((lab, pd.read_csv(f).set_index("site")))
    for lab, d in variants:
        rows.append([lab] + ["%+.1f" % d.loc[s, "EP_vs_POPPE_%"] for s in sites])
    lines = [r"\begin{tabular}{lrrrr}", r"\toprule", r"Plant variant & Phoenix & Singapore & Frankfurt & Stockholm \\",
             r"\midrule"] + [" & ".join(r) + r" \\" for r in rows] + [r"\bottomrule", r"\end{tabular}"]
    (S / "sensitivity_plant_table.tex").write_text("\n".join(lines) + "\n")
    pd.DataFrame(rows, columns=["variant"] + sites).to_csv(S / "sensitivity_plant.csv", index=False)
    print(pd.DataFrame(rows, columns=["variant"] + sites).to_string(index=False))


if __name__ == "__main__":
    sites()
    sensitivity()
