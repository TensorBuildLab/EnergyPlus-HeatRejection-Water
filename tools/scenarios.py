#!/usr/bin/env python3
"""Offline water-balance scenarios for a finished run (no re-simulation).

For every evaporation method x makeup-water source x chemistry mode, recompute drift, blowdown and makeup
from the timestep evaporation and water temperatures stored in the run, and return annual totals.

  python tools/scenarios.py runs/dc/phoenix
  python tools/scenarios.py runs/dc/phoenix --library data/water_sources_sourced.json --treatment icc_advanced_inhibitor
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import analyze  # noqa: E402
from tower_water.chemistry import ChemistryModel  # noqa: E402

LIB = ROOT / "data" / "water_sources.json"
MODES = [("fixed", None), ("constituent", "generic_inhibitor"), ("dynamic", "generic_inhibitor_dynamic")]


def coc_series(model: ChemistryModel, t_hot: np.ndarray, t_cold: np.ndarray) -> np.ndarray:
    if model.mode != "dynamic":
        return np.full(len(t_hot), model.cycles()[0])
    cache = {}
    out = np.empty(len(t_hot))
    for i, (h, c) in enumerate(zip(np.round(t_hot, 1), np.round(t_cold, 1))):
        k = (h, c)
        if k not in cache:
            cache[k] = model.cycles(t_hot=h, t_cold=c)[0]
        out[i] = cache[k]
    return out


def run_scenarios(run: Path, fixed_cycles: float = None, library: Path = LIB, treatment: str = None) -> pd.DataFrame:
    """treatment=None: the example library's generic_inhibitor / generic_inhibitor_dynamic; else this treatment
    of `library` for both the constituent and the dynamic mode."""
    cfg, frames, dt_h = analyze.load(run)
    lib = json.loads(Path(library).read_text())
    modes = MODES if treatment is None else [("fixed", None), ("constituent", treatment), ("dynamic", treatment)]
    fixed_treat = "generic_inhibitor" if treatment is None else treatment
    sec = dt_h * 3600.0
    rows = []
    for t in cfg["towers"]:
        d = frames[t["name"]]
        loaded = (d["ep_heat_transfer_rate"] > 0).to_numpy()
        t_hot, t_cold = d["ep_inlet_temperature"].to_numpy(), d["ep_outlet_temperature"].to_numpy()
        drift = d["pl_drift"].to_numpy()
        n_fixed = fixed_cycles or t["eplus_concentration_ratio"]
        for source, (mode, treat) in itertools.product(lib["sources"], modes):
            if mode == "fixed":
                model = ChemistryModel.from_library(str(library), source, fixed_treat, n_fixed, "fixed")
            else:
                model = ChemistryModel.from_library(str(library), source, treat, None, mode)
            coc = coc_series(model, t_hot, t_cold)
            for m in analyze.method_ids(d):
                e = d["pl_e_" + m.lower()].to_numpy() * loaded
                b = np.maximum(e / (coc - 1.0) - drift, 0.0) * loaded
                rows.append({"tower": t["name"], "method": m, "source": source, "mode": mode,
                             "evap_m3": e.sum() * sec, "drift_m3": (drift * loaded).sum() * sec,
                             "blowdown_m3": b.sum() * sec, "makeup_m3": (e + drift * loaded + b).sum() * sec,
                             "coc_mean": float(np.mean(coc[loaded])) if loaded.any() else float("nan")})
        # EnergyPlus's own numbers for reference
        rows.append({"tower": t["name"], "method": "EnergyPlus", "source": "-", "mode": "fixed",
                     "evap_m3": d["ep_water_evaporation_volume_flow_rate"].sum() * sec,
                     "drift_m3": d["ep_water_drift_volume_flow_rate"].sum() * sec,
                     "blowdown_m3": d["ep_water_blowdown_volume_flow_rate"].sum() * sec,
                     "makeup_m3": d["ep_make_up_water_volume_flow_rate"].sum() * sec,
                     "coc_mean": t["eplus_concentration_ratio"]})
    df = pd.DataFrame(rows)
    return df.groupby(["method", "source", "mode"], as_index=False)[
        ["evap_m3", "drift_m3", "blowdown_m3", "makeup_m3"]].sum().merge(
        df.groupby(["method", "source", "mode"], as_index=False)["coc_mean"].mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--library", type=Path, default=LIB, help="water-quality library (default: %(default)s)")
    ap.add_argument("--treatment", default=None,
                    help="treatment for the constituent and dynamic modes (default: the example library's "
                         "generic_inhibitor / generic_inhibitor_dynamic)")
    ap.add_argument("--fixed-cycles", type=float, default=None,
                    help="cycles for the fixed mode (default: the tower's EnergyPlus concentration ratio)")
    a = ap.parse_args()
    pd.set_option("display.width", 200)
    df = run_scenarios(a.run, a.fixed_cycles, a.library, a.treatment)
    df.to_csv(a.run / "scenarios.csv", index=False)
    print(df[df.method.isin(["POPPE", "EPSAT", "EnergyPlus"])].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
