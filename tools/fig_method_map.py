#!/usr/bin/env python3
"""Figures from tools/method_map.py: deviation of each method from Poppe over ambient conditions."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import figstyle as fs  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

GROUPS = {
    "fig_method_map_physical": (["EPSAT", "MSAT", "BRAUN", "POPPE1"], 20),
    "fig_method_map_empirical": (["LF", "ROT", "LAT"], 120),
}


def main(csv=ROOT / "results" / "method_map" / "method_map.csv", out=ROOT / "results" / "figures"):
    fs.apply()
    df = pd.read_csv(csv)
    tdb = np.sort(df.t_db.unique())
    rh = np.sort(df.rh.unique())
    for name, (ms, lim) in GROUPS.items():
        fig, axes = plt.subplots(1, len(ms), figsize=(2.6 * len(ms) + 0.8, 2.9), sharey=True, constrained_layout=True)
        for ax, m in zip(axes, ms):
            dev = 100 * (df["E_" + m] / df["E_POPPE"] - 1)
            z = pd.DataFrame({"t": df.t_db, "rh": df.rh, "d": dev}).pivot(index="rh", columns="t", values="d")
            z = z.reindex(index=rh, columns=tdb)
            im = ax.pcolormesh(tdb, 100 * rh, z.values, cmap=fs.DIVERGING, vmin=-lim, vmax=lim, shading="nearest")
            wb = pd.DataFrame({"t": df.t_db, "rh": df.rh, "wb": df.t_wb}).pivot(index="rh", columns="t", values="wb")
            wb = wb.reindex(index=rh, columns=tdb)
            cs = ax.contour(tdb, 100 * rh, wb.values, levels=[5, 15, 25], colors=fs.TEXT2, linewidths=0.6)
            ax.clabel(cs, fmt="WB %d°C", fontsize=6.5)
            ax.set_title(fs.METHOD_LABEL[m])
            ax.set_xlabel("Outdoor dry-bulb [°C]")
            ax.grid(False)
        axes[0].set_ylabel("Relative humidity [%]")
        cb = fig.colorbar(im, ax=axes, shrink=0.9, pad=0.01)
        cb.set_label("Evaporation vs Poppe [%]")
        fs.save(fig, out / name)
    print("wrote", out)


if __name__ == "__main__":
    main()
