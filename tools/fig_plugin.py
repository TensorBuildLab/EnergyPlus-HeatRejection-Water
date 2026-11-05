#!/usr/bin/env python3
"""Schematic of the plugin workflow (results/figures/fig_plugin_workflow.png/pdf).

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


def box(ax, x, y, w, h, kind, title, lines):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.015",
                                facecolor=FILL[kind], edgecolor=EDGE[kind], linewidth=1.2))
    ax.text(x + 0.012, y + h - 0.03, title, fontsize=7.4, fontweight="bold", va="top", color=fs.TEXT)
    ax.text(x + 0.012, y + h - 0.075, "\n".join(lines), fontsize=6.2, va="top", color=fs.TEXT, linespacing=1.35)


def arrow(ax, a, b, text=None, off=(0, 0.015)):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=9, linewidth=1.1, color=fs.TEXT2))
    if text:
        ax.text((a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1], text, fontsize=6.6, ha="center",
                color=fs.TEXT2)


def main():
    fs.apply()
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.set_xlim(-0.015, 1.02)
    ax.set_ylim(0, 1)
    ax.axis("off")
    box(ax, 0.00, 0.60, 0.27, 0.38, "user", "1  Prepare (once per model)",
        ["tools/prepare_model.py", "• sizing run → tower design flows", "• writes model.idf with",
         "  PythonPlugin:Instance,", "  :Variables, :OutputVariable", "• tower_water_config.json",
         "  (towers, water source, treatment)"])
    box(ax, 0.00, 0.04, 0.27, 0.46, "eplus", "2  EnergyPlus simulation",
        ["building, HVAC and plant model", "(any IDF with CoolingTower:", " SingleSpeed, :VariableSpeed or",
         " :VariableSpeed:Merkel)", "", "thermal solution unchanged:", "heat rejected, temperatures,",
         "flows, fan state per timestep", "(plugin outputs do not feed back)"])
    box(ax, 0.355, 0.04, 0.345, 0.94, "plugin", "3  Plugin, every system timestep",
        ["a. read operating point", "   T_w,in, T_w,out, m_w, Q, fan ratio or", "   cycling ratio, cells; outdoor T_db,",
         "   T_wb, ω, p", "b. reconstruct steady states", "   fan-cycling: fan-on + free convection",
         "   variable speed: one state (air flow,", "   near-pinch check)",
         "c. evaluate 8 evaporation models", "   LAT, ROT, LF, EPSAT, MSAT, BRAUN,", "   POPPE (reference), POPPE1",
         "d. water balance", "   drift, cycles from makeup chemistry", "   (fixed / constituent / LSI, silica),",
         "   blowdown, makeup", "e. diagnostics: exit air state, mist,", "   Merkel number, status"])
    box(ax, 0.775, 0.40, 0.225, 0.58, "out", "4  Outputs",
        ["per tower and timestep:", "<Tower>_E_<MODEL>, m³/s", "_Drift, _Blowdown, _Makeup",
         "_Cycles, _CycLimit", "_AirOutT, _AirOutW, _Mist", "_MePoppe, _Status", "", "in eplusout.csv like any",
         "EnergyPlus output variable"])
    box(ax, 0.775, 0.04, 0.225, 0.28, "user", "5  Post-process",
        ["tools/analyze.py: annual", "totals, model differences", "tools/scenarios.py: water",
         "quality and cycles offline"])
    arrow(ax, (0.135, 0.595), (0.135, 0.505))
    ax.text(0.15, 0.548, "model.idf", fontsize=6.2, color=fs.TEXT2, va="center")
    arrow(ax, (0.272, 0.32), (0.352, 0.32))
    ax.text(0.312, 0.345, "operating\npoint", fontsize=5.6, ha="center", color=fs.TEXT2)
    arrow(ax, (0.352, 0.18), (0.272, 0.18))
    arrow(ax, (0.703, 0.70), (0.772, 0.70))
    arrow(ax, (0.887, 0.395), (0.887, 0.325))
    fs.save(fig, ROOT / "results" / "figures" / "fig_plugin_workflow")


if __name__ == "__main__":
    main()
