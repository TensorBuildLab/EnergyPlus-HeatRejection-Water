#!/usr/bin/env python3
"""Checks for fan-cycling single-speed towers (CoolingTower:SingleSpeed), per site.

1. Replica check: in timesteps where the fan stays off (free convection only), EnergyPlus reports the free-convection
   leaving temperature directly; the plugin's replica of calculateSimpleTowerOutletTemp must reproduce it.
2. Decomposition of EnergyPlus SaturatedExit vs Poppe into
     (a) the averaging convention: EnergyPlus applies the timestep-average heat to the full fan air flow whenever
         the fan ran at all; the same saturated-exit formula applied to each steady state (fan on, fan off) and
         time-weighted gives EPSAT_states;
     (b) the physics: EPSAT_states vs Poppe (both on the two steady states).
3. Sensitivity of Poppe to the state split: two states vs one state at the time-averaged air flow.

  python tools/single_speed_check.py runs/proto_dc     # -> results/study/single_speed_check_<run_root name>.csv
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]
import analyze  # noqa: E402
from tower_water import eplus_plugin as P  # noqa: E402
from tower_water import evaporation as ev  # noqa: E402
from tower_water import psychro as ps  # noqa: E402

RHO = ps.rho_water(20.0)


def _row(args):
    t, v, site = args
    p, tdb, twb, w = site["p"], site["t_db"], site["t_wb"], site["w"]
    states = P.single_speed_states(t, v, site)
    rho_a = ps.rho_moist_air(tdb, w, p)
    eps_states = 0.0
    pop_states = 0.0
    for wt, t_o, m_t, air in states:
        q_k = m_t * ev.cp_water(v["t_in"]) * (v["t_in"] - t_o)
        eps_states += wt * ev.eplus_saturated_exit(q_k, air * rho_a, tdb, twb, w, p) * RHO
        r = ev.poppe(v["t_in"], t_o, m_t, air * rho_a / (1 + w), tdb, w, p, n_steps=10)
        pop_states += wt * (r.evap_kg_s if r.status == ev.OK else np.nan)
    f = v["fcr"]
    cells = t["cells"]
    frac = (v["cells_on"] or cells) / cells
    air_avg = (f * t["design_air_flow"] + (1 - f) * t["free_conv_air_flow"]) * frac
    r1 = ev.poppe(v["t_in"], v["t_out"], v["m_w"], air_avg * rho_a / (1 + w), tdb, w, p, n_steps=10)
    pop_avg = r1.evap_kg_s if r1.status == ev.OK else np.nan
    t_rep = np.nan
    if f <= 0.0:
        t_rep = ev.eplus_simple_tower_outlet(v["t_in"], v["m_w"] / (v["cells_on"] or cells),
                                             t["free_conv_air_flow"] / cells, t["free_conv_ua"] / cells, tdb, twb, w, p)
    return eps_states, pop_states, pop_avg, t_rep, len(states)


def site_check(run, every=3, jobs=64):
    cfg, frames, dt_h = analyze.load(run)
    t = cfg["towers"][0]
    d = next(iter(frames.values()))
    on = d[(d.ep_heat_transfer_rate > 0) & (d.ep_mass_flow_rate > 0)].iloc[::every]
    args = []
    for r in on.itertuples():
        v = dict(t_in=r.ep_inlet_temperature, t_out=r.ep_outlet_temperature, m_w=r.ep_mass_flow_rate,
                 q=r.ep_heat_transfer_rate, fcr=r.ep_fan_cycling_ratio, cells_on=r.ep_operating_cells_count,
                 bypass=getattr(r, "ep_bypass_fraction", 0.0))
        site = dict(t_db=r.site_drybulb_temperature, t_wb=r.site_wetbulb_temperature, w=r.site_humidity_ratio,
                    p=r.site_barometric_pressure)
        args.append((t, v, site))
    with ProcessPoolExecutor(jobs) as pool:
        res = np.array(list(pool.map(_row, args, chunksize=16)), dtype=float)
    eps_s, pop_s, pop_a, t_rep, nst = res.T
    f = on.ep_fan_cycling_ratio.to_numpy()
    e_pl_pop = on.pl_e_poppe.to_numpy() * RHO
    e_pl_eps = on.pl_e_epsat.to_numpy() * RHO
    e_ep = on.ep_water_evaporation_volume_flow_rate.to_numpy() * RHO
    off = np.isfinite(t_rep)
    dt_rep = t_rep[off] - on.ep_outlet_temperature.to_numpy()[off]
    ok = np.isfinite(pop_s) & np.isfinite(pop_a)
    cyc = (f > 0) & (f < 1)
    return {
        "site": run.name, "n_sampled": len(on),
        "fan_off_share_%": 100 * np.mean(f <= 0), "cycling_share_%": 100 * np.mean(cyc), "full_fan_share_%": 100 * np.mean(f >= 1),
        "mean_fan_ratio": float(np.mean(f)),
        "evap_share_cycling_%": 100 * e_pl_pop[cyc].sum() / e_pl_pop.sum(),
        "replica_Toff_bias_K": float(np.mean(dt_rep)) if off.any() else np.nan,
        "replica_Toff_maxabs_K": float(np.max(np.abs(dt_rep))) if off.any() else np.nan,
        "EP_own_vs_EPSAT_replica_%": 100 * (e_ep.sum() / e_pl_eps.sum() - 1),
        "EPSAT_vs_POPPE_%": 100 * (e_pl_eps.sum() / e_pl_pop.sum() - 1),
        "convention_EPSAT_vs_EPSATstates_%": 100 * (e_pl_eps.sum() / eps_s.sum() - 1),
        "physics_EPSATstates_vs_POPPE_%": 100 * (eps_s.sum() / e_pl_pop.sum() - 1),
        "POPPE_avgstate_vs_states_%": 100 * (pop_a[ok].sum() / pop_s[ok].sum() - 1),
        "plugin_vs_recomputed_POPPE_%": 100 * (e_pl_pop[ok].sum() / pop_s[ok].sum() - 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_root", type=Path)
    ap.add_argument("--every", type=int, default=3)
    a = ap.parse_args()
    rows = []
    for run in sorted(p for p in a.run_root.iterdir() if (p / "out" / "eplusout.csv").exists()):
        rows.append(site_check(run, a.every))
        print("done", run.name, flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "study" / ("single_speed_check_%s.csv" % a.run_root.name), index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(df.round(3).T.to_string())


if __name__ == "__main__":
    main()
