#!/usr/bin/env python3
"""Summarize one plugin run: every evaporation method vs EnergyPlus, per tower.

  python tools/analyze.py runs/chicago                # summary table
  python tools/analyze.py runs/chicago --csv x.csv    # also save the tidy timestep table
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tower_water import psychro as ps  # noqa: E402
from tower_water.methods import REFERENCE  # noqa: E402

FOG_LIQUID_GKG = 0.1

STATUS = {0: "ok", 1: "idle", 2: "no airflow", 3: "infeasible", 4: "clipped", 5: "air adjusted"}


def load(run: Path):
    """(config, {tower: DataFrame}, dt_hours). Columns: site_*, ep_* (EnergyPlus), pl_* (plugin)."""
    cfg = json.loads((run / "tower_water_config.json").read_text())
    raw = pd.read_csv(run / "out" / "eplusout.csv")
    raw.columns = [c.strip() for c in raw.columns]
    raw = raw[[c for c in raw.columns if c.endswith("(TimeStep)") or c == "Date/Time"]]
    # keep the weather-file run period only: models with "Do HVAC Sizing Simulation for Sizing Periods" also report
    # the design days, which precede the annual period in eplusout.csv
    day = raw["Date/Time"].astype(str).str.strip().str.slice(0, 5)
    starts = [i for i in range(len(day)) if day.iat[i] == "01/01" and (i == 0 or day.iat[i - 1] != "01/01")]
    if starts and starts[-1] > 0:
        raw = raw.iloc[starts[-1]:].reset_index(drop=True)
    site = {}
    for c in raw.columns:
        m = re.match(r"Environment:Site Outdoor Air (.+?) \[", c)
        if m:
            site["site_" + m.group(1).replace(" ", "_").lower()] = raw[c]
    frames = {}
    for t in cfg["towers"]:
        d = {"time": raw["Date/Time"]}
        d.update(site)
        for c in raw.columns:
            if c.upper().startswith(t["name"].upper() + ":COOLING TOWER "):
                d["ep_" + re.sub(r"\W+", "_", c.split(":Cooling Tower ")[1].split(" [")[0]).lower()] = raw[c]
            elif c.startswith(t["prefix"] + "_"):
                d["pl_" + c[len(t["prefix"]) + 1:].split(":")[0].lower()] = raw[c]
        frames[t["name"]] = pd.DataFrame(d).dropna()
    return cfg, frames, 1.0 / cfg["timesteps_per_hour"]


def method_ids(df):
    return [c[5:].upper() for c in df.columns if c.startswith("pl_e_")]


def summarize(run: Path) -> pd.DataFrame:
    cfg, frames, dt_h = load(run)
    sec = dt_h * 3600.0
    rows = []
    for t in cfg["towers"]:
        d = frames[t["name"]]
        ep = d["ep_water_evaporation_volume_flow_rate"]
        loaded = d["ep_heat_transfer_rate"] > 0
        st = d["pl_status"].round().astype(int)
        row = {
            "tower": t["name"],
            "hours_loaded": loaded.sum() * dt_h,
            "heat_rejected_MWh": d["ep_heat_transfer_rate"].sum() * sec / 3.6e9,
            "EP_evap_m3": ep.sum() * sec,
            "EP_evap_idle_m3": ep[~loaded].sum() * sec,
            "EP_zero_evap_loaded_h": (loaded & (ep <= 0)).sum() * dt_h,
        }
        mids = method_ids(d)
        ref = d["pl_e_" + REFERENCE.lower()].sum() * sec
        for m in mids:
            v = d["pl_e_" + m.lower()].sum() * sec
            row["%s_m3" % m] = v
        for m in mids:
            row["%s_vs_%s_%%" % (m, REFERENCE)] = 100 * (row["%s_m3" % m] / ref - 1) if ref else float("nan")
        if "EPSAT" in mids:
            lo = loaded & (ep > 0)
            row["EPSAT_replica_err_%"] = 100 * (d.loc[lo, "pl_e_epsat"].sum() / ep[lo].sum() - 1) if lo.any() else float("nan")
        row["EP_vs_%s_%%" % REFERENCE] = 100 * (row["EP_evap_m3"] / ref - 1) if ref else float("nan")
        fb = loaded & st.isin([2, 3])
        row["ref_fallback_share_%"] = 100 * d.loc[fb, "pl_e_" + REFERENCE.lower()].sum() * sec / ref if ref else float("nan")
        adj = loaded & (st == 5)
        # share of annual Poppe evaporation in timesteps with the near-pinch air-flow adjustment (evaporation-weighted;
        # review_analyses.py reports the share of loaded timesteps)
        row["ref_air_adjusted_share_%"] = 100 * d.loc[adj, "pl_e_" + REFERENCE.lower()].sum() * sec / ref if ref else float("nan")
        row["air_scale_mean_adjusted"] = d.loc[adj, "pl_airscale"].mean() if adj.any() else float("nan")
        row["fog_hours_any"] = d["pl_fog"].sum() * dt_h
        # liquid carried by exit air [g/kg]; "fog" counted above FOG_LIQUID_GKG (traces at the pinch are not counted)
        ws = pd.Series([ps.w_sat(tt, pp) for tt, pp in zip(d["pl_airoutt"], d["site_barometric_pressure"])], index=d.index)
        liq = 1e3 * (d["pl_airoutw"] - ws) * (d["pl_fog"] > 0)
        row["fog_hours"] = (liq > FOG_LIQUID_GKG).sum() * dt_h
        row["EP_makeup_m3"] = d["ep_make_up_water_volume_flow_rate"].sum() * sec
        row["plugin_makeup_m3"] = d["pl_makeup"].sum() * sec
        row["EP_cycles"] = t["eplus_concentration_ratio"]
        row["chem_cycles_mean"] = d.loc[loaded, "pl_cycles"].mean() if loaded.any() else d["pl_cycles"].iloc[0]
        row["status_hours"] = {STATUS.get(k, k): round(v * dt_h, 2) for k, v in st[loaded].value_counts().items()}
        rows.append(row)
    return pd.DataFrame(rows).set_index("tower")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--csv", type=Path)
    a = ap.parse_args()
    pd.set_option("display.width", 200)
    print(summarize(a.run).T.to_string())
    if a.csv:
        _, frames, _ = load(a.run)
        pd.concat(frames, names=["tower"]).to_csv(a.csv)


if __name__ == "__main__":
    main()
