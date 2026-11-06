#!/usr/bin/env python3
"""Schematic of the plugin workflow (results/figures/fig_plugin_workflow.png/pdf).

Box sizes are computed from the rendered text, so no text can cross a box edge.

  python tools/fig_plugin.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import figstyle as fs  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

FILL = {"user": "#eef4fc", "eplus": "#f4f3f0", "plugin": "#e9f7f1", "out": "#fdf3e1"}
EDGE = {"user": fs.SERIES[0], "eplus": fs.TEXT2, "plugin": fs.SERIES[2], "out": fs.SERIES[3]}
PAD = 0.12      # inner padding [in]
GAP_COL = 0.55  # horizontal gap between columns [in] (room for arrows)
GAP_ROW = 0.38  # vertical gap between stacked boxes [in]
TITLE_FS, BODY_FS = 8.0, 6.8

BOXES = {
    "prep": ("user", "1  Prepare (once per model)",
             ["tools/prepare_model.py", "- sizing run: tower design flows", "- writes model.idf with the",
              "  PythonPlugin objects and outputs", "- writes tower_water_config.json",
              "  (towers, water source, treatment)"]),
    "eplus": ("eplus", "2  EnergyPlus simulation",
              ["building, HVAC and plant model", "(any model with CoolingTower:", "SingleSpeed, :VariableSpeed",
               "or :VariableSpeed:Merkel)", "", "thermal solution unchanged:", "heat rejected, temperatures,",
               "flows and fan state", "(plugin outputs do not feed back)"]),
    "plugin": ("plugin", "3  Plugin, every system timestep",
               ["a. read the operating point", "   water temperatures and flow, heat,",
                "   fan or cycling ratio, cells;", "   outdoor dry-bulb, wet-bulb, humidity, pressure",
                "b. reconstruct the steady states", "   fan cycling: fan-on and free convection",
                "   variable speed: one state, near-pinch check", "c. evaluate the 8 evaporation models",
                "   LAT, ROT, LF, EPSAT, MSAT, BRAUN,", "   POPPE (reference), POPPE1",
                "d. water balance", "   drift; cycles from makeup chemistry",
                "   (fixed, constituent, LSI, silica);", "   blowdown and makeup",
                "e. diagnostics", "   exhaust state, mist, Merkel number, status"]),
    "out": ("out", "4  Outputs",
            ["per tower and timestep:", "<Tower>_E_<MODEL> [m3/s]", "_Drift, _Blowdown, _Makeup",
             "_Cycles, _CycLimit", "_AirOutT, _AirOutW, _Mist", "_MePoppe, _Status", "",
             "written to eplusout.csv like", "any EnergyPlus output variable"]),
    "post": ("user", "5  Post-process",
             ["tools/analyze.py:", "annual totals, model differences", "tools/scenarios.py:",
              "water quality and cycles offline"]),
}


def measure(fig, title, lines):
    """Width and height [in] of a box's title + body text, plus padding."""
    r = fig.canvas.get_renderer()
    t = fig.text(0, 0, title, fontsize=TITLE_FS, fontweight="bold")
    b = fig.text(0, 0, "\n".join(lines), fontsize=BODY_FS, linespacing=1.35)
    wt, ht = t.get_window_extent(r).width / fig.dpi, t.get_window_extent(r).height / fig.dpi
    wb, hb = b.get_window_extent(r).width / fig.dpi, b.get_window_extent(r).height / fig.dpi
    t.remove()
    b.remove()
    return max(wt, wb) + 2 * PAD, ht + hb + 0.10 + 2 * PAD, ht


def draw(ax, x, y, w, h, key, ht):
    kind, title, lines = BOXES[key]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                facecolor=FILL[kind], edgecolor=EDGE[kind], linewidth=1.2))
    ax.text(x + PAD, y + h - PAD, title, fontsize=TITLE_FS, fontweight="bold", va="top", color=fs.TEXT)
    ax.text(x + PAD, y + h - PAD - ht - 0.10, "\n".join(lines), fontsize=BODY_FS, va="top", color=fs.TEXT,
            linespacing=1.35)


def arrow(ax, a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10, linewidth=1.1, color=fs.TEXT2,
                                 shrinkA=0, shrinkB=0))


def main():
    fs.apply()
    plt.rcParams["savefig.bbox"] = "standard"   # the axes are sized to the content
    fig = plt.figure(figsize=(8, 5))
    m = {k: measure(fig, BOXES[k][1], BOXES[k][2]) for k in BOXES}
    w1 = max(m["prep"][0], m["eplus"][0])
    w2 = m["plugin"][0]
    w3 = max(m["out"][0], m["post"][0])
    h1 = m["prep"][1] + GAP_ROW + m["eplus"][1]
    h3 = m["out"][1] + GAP_ROW + m["post"][1]
    H = max(h1, m["plugin"][1], h3)
    W = w1 + w2 + w3 + 2 * GAP_COL
    plt.close(fig)

    M = 0.06
    fig = plt.figure(figsize=(W + 2 * M, H + 2 * M))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-M, W + M)
    ax.set_ylim(-M, H + M)
    ax.axis("off")
    x1, x2, x3 = 0.0, w1 + GAP_COL, w1 + w2 + 2 * GAP_COL
    hp = m["prep"][1]
    he = H - hp - GAP_ROW              # simulation box stretched to the bottom
    hq = m["post"][1]
    ho = H - hq - GAP_ROW              # outputs box absorbs spare height
    draw(ax, x1, H - hp, w1, hp, "prep", m["prep"][2])
    draw(ax, x1, 0, w1, he, "eplus", m["eplus"][2])
    draw(ax, x2, 0, w2, H, "plugin", m["plugin"][2])
    draw(ax, x3, H - ho, w3, ho, "out", m["out"][2])
    draw(ax, x3, 0, w3, hq, "post", m["post"][2])

    # prepare -> simulation
    arrow(ax, (x1 + w1 / 2, H - hp), (x1 + w1 / 2, he))
    ax.text(x1 + w1 / 2 + 0.08, he + GAP_ROW / 2, "model.idf", fontsize=BODY_FS, color=fs.TEXT2, va="center")
    # simulation <-> plugin
    ya, yb = he * 0.62, he * 0.30
    arrow(ax, (x1 + w1, ya), (x2, ya))
    ax.text(x1 + w1 + GAP_COL / 2, ya + 0.05, "operating\npoint", fontsize=6.0, ha="center", va="bottom",
            color=fs.TEXT2)
    arrow(ax, (x2, yb), (x1 + w1, yb))
    ax.text(x1 + w1 + GAP_COL / 2, yb + 0.05, "next\ntimestep", fontsize=6.0, ha="center", va="bottom",
            color=fs.TEXT2)
    # plugin -> outputs -> post-process
    yo = H - ho / 2
    arrow(ax, (x2 + w2, yo), (x3, yo))
    arrow(ax, (x3 + w3 / 2, H - ho), (x3 + w3 / 2, hq))
    fs.save(fig, ROOT / "results" / "figures" / "fig_plugin_workflow")


if __name__ == "__main__":
    main()
