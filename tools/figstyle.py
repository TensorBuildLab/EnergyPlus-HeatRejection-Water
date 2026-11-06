"""Shared figure style for the paper (static, print, light surface)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT2 = "#52514e"
GRID = "#e4e3df"
# Categorical slots in fixed order (validated palette)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
# Each method keeps its own colour everywhere (colour follows the entity)
METHOD_COLOR = {
    "POPPE": SERIES[0], "MSAT": SERIES[1], "BRAUN": SERIES[2], "EPSAT": SERIES[3],
    "POPPE1": SERIES[4], "LF": SERIES[5], "ROT": SERIES[6], "LAT": SERIES[7],
}
METHOD_LABEL = {
    "POPPE": "Poppe (reference)", "POPPE1": "Poppe, Le$_f$=1", "MSAT": "Merkel, saturated exit",
    "EPSAT": "EnergyPlus SaturatedExit", "BRAUN": "Braun e-NTU", "LF": "EnergyPlus LossFactor 0.2 %/K",
    "ROT": "Rule of thumb 0.153 %/K", "LAT": "Latent only Q/h$_{fg}$",
}
# Diverging blue <-> red with neutral gray midpoint
DIVERGING = LinearSegmentedColormap.from_list(
    "bluered", ["#0d366b", "#256abf", "#86b6ef", "#f0efec", "#f2a3a2", "#e34948", "#8f1d1d"])


def apply():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": TEXT, "text.color": TEXT,
        "xtick.color": TEXT2, "ytick.color": TEXT2, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 9, "axes.titlesize": 9.5, "axes.titleweight": "bold", "legend.frameon": False,
        "lines.linewidth": 2.0, "axes.unicode_minus": False, "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
    })


def save(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path.with_suffix(".png"))
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)
