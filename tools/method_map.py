#!/usr/bin/env python3
"""Method-error map over ambient conditions for a fixed tower (standalone, no EnergyPlus).

A counterflow tower is sized so that, with the Poppe model, it gives the design approach and range at the
design wet-bulb. Its fill Merkel number Me and L/G are then held fixed. For each ambient (dry-bulb, RH) on a
grid, the heat load (range) is held at design and the cold-water temperature is solved with Poppe (rating
mode). All evaporation methods are evaluated at that operating point.

Outputs: <out>/method_map.csv and figures (if matplotlib is available).

  python tools/method_map.py --out results/method_map
"""
from __future__ import annotations

import argparse
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tower_water import evaporation as ev  # noqa: E402
from tower_water import methods as mt  # noqa: E402
from tower_water import psychro as ps  # noqa: E402

P = 101325.0
DESIGN = dict(t_db=35.0, t_wb=25.6, range_k=5.6, approach_k=3.9, lg=1.2)   # 95 F DB / 78 F WB, 10 F range, 7 F approach
M_W = 100.0   # kg/s, scales out of all ratios


def design_fill():
    d = DESIGN
    w = ps.w_from_twb(d["t_db"], d["t_wb"], P)
    t_out = d["t_wb"] + d["approach_k"]
    t_in = t_out + d["range_k"]
    m_a = M_W / d["lg"]
    r = ev.poppe(t_in, t_out, M_W, m_a, d["t_db"], w, P, n_steps=20)
    assert r.status == ev.OK
    return r.merkel, m_a


def solve_point(args):
    t_db, rh, me, m_a = args
    w = ps.w_from_rh(t_db, rh, P)
    t_wb = ps.t_wb_from_w(t_db, w, P)
    rng = DESIGN["range_k"]

    def me_of(t_out):
        r = ev.poppe(t_out + rng, t_out, M_W, m_a, t_db, w, P, n_steps=10)
        return r.merkel if r.status == ev.OK else float("inf")

    lo, hi = t_wb + 0.05, t_wb + 30.0
    if me_of(hi) > me:
        return None
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if me_of(mid) > me:
            lo = mid
        else:
            hi = mid
    t_out = 0.5 * (lo + hi)
    t_in = t_out + rng
    q = M_W * ps.CP_WATER * rng
    op = mt.OperatingPoint(t_in, t_out, M_W, q, m_a, m_a * (1 + w), t_db, t_wb, w, P)
    res = mt.evaluate(op)
    row = {"t_db": t_db, "rh": rh, "t_wb": t_wb, "t_w_out": t_out, "approach": t_out - t_wb,
           "fog": int(res["POPPE"].supersaturated), "t_air_out": res["POPPE"].t_air_out}
    kwh = q / 1000.0     # kW thermal -> per hour = kWh
    for m, r in res.items():
        row["E_" + m] = r.evap_kg_s
        row["L_per_kWh_" + m] = r.evap_kg_s * 3600.0 / ps.rho_water(20.0) * 1000.0 / kwh
        row["status_" + m] = r.status
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "method_map")
    ap.add_argument("--jobs", type=int, default=32)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    me, m_a = design_fill()
    print("Design fill: Me_P = %.4f, L/G = %.2f" % (me, DESIGN["lg"]))
    grid = [(t, rh / 100.0, me, m_a) for t in range(-5, 47, 1) for rh in range(5, 101, 5)]
    grid = [g for g in grid if ps.t_wb_from_w(g[0], ps.w_from_rh(g[0], g[1], P), P) < 32.0]
    with ProcessPoolExecutor(a.jobs) as pool:
        rows = [r for r in pool.map(solve_point, grid, chunksize=8) if r]
    import pandas as pd
    df = pd.DataFrame(rows)
    df.to_csv(a.out / "method_map.csv", index=False)
    for m in mt.METHODS:
        df["dev_" + m] = 100 * (df["E_" + m] / df["E_POPPE"] - 1)
    print(df[["dev_" + m for m in mt.METHODS]].describe(percentiles=[0.05, 0.5, 0.95]).round(2).to_string())
    print("fog points: %d of %d" % (df.fog.sum(), len(df)))
    print("wrote", a.out / "method_map.csv")


if __name__ == "__main__":
    main()
