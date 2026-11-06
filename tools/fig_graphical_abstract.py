#!/usr/bin/env python3
"""Graphical abstract for the Energy and Buildings submission.

Elsevier: image at least 531 x 1328 pixels (h x w), readable at 5 x 13 cm. This figure is 4.4 x 11 in at 300 dpi.
Reads results/study/buildings_sites.csv (written by tools/building_study.py).

  python tools/fig_graphical_abstract.py   # -> results/figures/graphical_abstract.png/.pdf
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import figstyle as fs  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

CASES = [("dc_proto", "Data center prototype\n(single-speed, fan cycling)", fs.SERIES[0]),
         ("office", "Office prototype\n(single-speed)", fs.SERIES[1]),
         ("dc_vs", "Data center\n(variable-speed tower)", fs.SERIES[2])]


def load():
    rows = list(csv.DictReader(open(ROOT / "results" / "study" / "buildings_sites.csv")))
    return {c: [(r["name"], float(r["dev_EPSAT"])) for r in rows if r["case"] == c] for c, _, _ in CASES}


def panel_box(ax, title, lines, edge):
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.add_patch(FancyBboxPatch((0.01, 0.02), 0.98, 0.96, boxstyle="round,pad=0,rounding_size=0.04",
                                facecolor="#ffffff", edgecolor=edge, linewidth=1.4, transform=ax.transAxes))
    ax.text(0.07, 0.90, title, fontsize=10.5, fontweight="bold", va="top", color=fs.TEXT)
    ax.text(0.07, 0.78, "\n".join(lines), fontsize=8.6, va="top", color=fs.TEXT, linespacing=1.55)


def main():
    fs.apply()
    plt.rcParams["savefig.bbox"] = "standard"
    data = load()
    fig = plt.figure(figsize=(11, 4.4))
    a1 = fig.add_axes([0.01, 0.04, 0.26, 0.92])
    a2 = fig.add_axes([0.445, 0.20, 0.285, 0.62])
    a3 = fig.add_axes([0.755, 0.04, 0.235, 0.92])
    panel_box(a1, "Method", [
        "8 evaporation models, from rules", "of thumb to the Poppe model,",
        "evaluated at the same simulated", "operating point every timestep",
        "", "Open-source EnergyPlus plugin;", "fan cycling resolved into", "fan-on and free-convection states",
        "", "3 buildings x 14 climates"], fs.TEXT2)

    for k, (case, label, color) in enumerate(CASES):
        y = len(CASES) - 1 - k
        vals = [v for _, v in data[case]]
        lo, hi = min(vals), max(vals)
        a2.plot([lo, hi], [y, y], color=color, linewidth=6, alpha=0.25, solid_capstyle="round")
        a2.scatter(vals, [y] * len(vals), s=26, color=color, edgecolor=fs.SURFACE, linewidth=0.8, zorder=3)
        a2.text(lo, y + 0.25, "%+.0f to %+.0f %%" % (lo, hi), va="center", ha="left", fontsize=8.4, color=fs.TEXT, zorder=4, bbox=dict(boxstyle="square,pad=0.15", facecolor=fs.SURFACE, edgecolor="none"))
    a2.axvline(0, color=fs.TEXT2, linewidth=1.0)
    a2.set_yticks(range(len(CASES)))
    a2.set_yticklabels([c[1] for c in CASES][::-1], fontsize=8.2)
    a2.set_xlim(-12, 42)
    a2.set_ylim(-0.6, len(CASES) - 0.4)
    a2.grid(axis="y", visible=False)
    a2.set_xlabel("Difference in annual evaporation [%]", fontsize=8.6)
    a2.set_title("EnergyPlus default vs Poppe\n(each dot is one climate)", fontsize=9.2, loc="left")

    panel_box(a3, "Finding", [
        "Error follows the exhaust-air state:", "- hot, dry air leaves unsaturated:",
        "  saturated-exit models overpredict", "- cold air leaves supersaturated:",
        "  they underpredict", "", "The tower's air-to-water ratio", "(its part-load control) decides",
        "which regime dominates"], fs.TEXT2)
    out = ROOT / "results" / "figures" / "graphical_abstract"
    fs.save(fig, out)
    print("wrote", out.with_suffix(".png"))


if __name__ == "__main__":
    main()
