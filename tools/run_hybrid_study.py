#!/usr/bin/env python3
"""Hybrid dry cooler study: sites x control strategies, in parallel, with facility energy and water.

  python tools/run_hybrid_study.py --idf models/datacenter_chiller_hybrid.idf --out runs/hyb \
      --sites weather/phoenix_tmyx weather/stockholm ... --t-on 16 20 24 28 32 [--jobs 32]

Cases per site: dry, wet (always, above freeze limit), threshold at each --t-on.
Writes <out>/hybrid_summary.csv.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "models"))
import prepare_hybrid  # noqa: E402
import summarize_dc_run  # noqa: E402
from prepare_model import DEFAULT_EPLUS  # noqa: E402


def case_name(strategy, t_on):
    return strategy if strategy != "threshold" else "T%g" % t_on


def collect(out: Path) -> dict:
    d = pd.read_csv(out / "out" / "eplusout.csv")
    d.columns = [c.strip() for c in d.columns]
    ts = [c for c in d.columns if c.endswith("(TimeStep)")]

    def col(key):
        return d[[c for c in ts if c.startswith(key + ":")][0]]
    n_h = 1.0 / int(__import__("json").loads((out / "hybrid_config.json").read_text())["timesteps_per_hour"])
    r = {
        "wet_hours": col("HC_Wet").sum() * n_h,
        "evap_m3": col("HC_Evap").sum() * n_h * 3600,
        "bleed_m3": col("HC_Bleed").sum() * n_h * 3600,
        "makeup_m3": col("HC_MakeupVol").sum(),
        "cooler_fan_MWh": col("HC_FanPower").sum() * n_h / 1e6,
        "pad_penalty_MWh": col("HC_FanPenalty").sum() * n_h / 1e6,
        "heat_MWh": col("HC_Heat").sum() * n_h / 1e6,
    }
    fac = summarize_dc_run.summarize(str(out / "out"), idf=str(out / "model.idf"))
    for k_out, k_in in (("IT_MWh", "IT energy (CPU+server fans) [MWh]"), ("facility_MWh", "Facility electricity [MWh]"),
                        ("PUE", "PUE (facility / IT)"), ("chillers_MWh", "Chillers [MWh]")):
        r[k_out] = fac.get(k_in, float("nan"))
    r["facility_MWh_with_pad_penalty"] = r["facility_MWh"] + r["pad_penalty_MWh"]
    r["WUE"] = r["makeup_m3"] * 1e3 / (r["IT_MWh"] * 1e3) if r["IT_MWh"] else float("nan")
    r["chiller_hours_outside_curve"] = fac.get("Chiller hours outside curve limits (any running chiller, TimeStep data)",
                                               float("nan"))
    return r


def one(job):
    idf, site, out, eplus, strategy, t_on, extra = job
    try:
        epw = sorted(site.glob("*.epw"))[0]
        ddy = sorted(site.glob("*.ddy"))[0]
        prepare_hybrid.main(["--idf", str(idf), "--epw", str(epw), "--ddy", str(ddy), "--out", str(out),
                             "--eplus", eplus, "--strategy", strategy, "--t-on", str(t_on)] + extra)
        with open(out / "run.log", "w") as log:
            subprocess.run([eplus, "-r", "-d", str(out / "out"), "-w", str(epw), str(out / "model.idf")],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        r = collect(out)
        r.update(site=site.name, case=case_name(strategy, t_on), strategy=strategy,
                 t_on=t_on if strategy == "threshold" else float("nan"))
        return r, None
    except Exception:
        return None, "%s/%s: %s" % (site.name, case_name(strategy, t_on), traceback.format_exc())


def recollect(root: Path):
    """Rebuild hybrid_summary.csv from finished runs (no re-simulation)."""
    rows = []
    for out in sorted(root.glob("*/*/out/eplusout.csv")):
        case_dir = out.parent.parent
        r = collect(case_dir)
        case = case_dir.name
        r.update(site=case_dir.parent.name, case=case, strategy=case if case in ("dry", "wet") else "threshold",
                 t_on=float(case[1:]) if case.startswith("T") else float("nan"))
        rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(root / "hybrid_summary.csv", index=False)
    return df


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--recollect":
        print(len(recollect(Path(sys.argv[2]))), "cases")
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument("--idf", required=True, type=Path)
    ap.add_argument("--sites", required=True, nargs="+", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--t-on", type=float, nargs="+", default=[16, 20, 24, 28, 32])
    ap.add_argument("--eplus", default=DEFAULT_EPLUS)
    ap.add_argument("--jobs", type=int, default=32)
    a, extra = ap.parse_known_args()
    cases = [("dry", 0.0), ("wet", 0.0)] + [("threshold", t) for t in a.t_on]
    jobs = [(a.idf.resolve(), s.resolve(), (a.out / s.name / case_name(st, t)).resolve(), a.eplus, st, t, extra)
            for s in a.sites if list(s.glob("*.epw")) for st, t in cases]
    a.out.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(a.jobs) as pool:
        res = list(pool.map(one, jobs))
    for _, e in res:
        if e:
            print("FAILED", e)
    df = pd.DataFrame([r for r, e in res if r])
    if df.empty:
        return 1
    df.to_csv(a.out / "hybrid_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(df[["site", "case", "wet_hours", "makeup_m3", "WUE", "PUE", "chillers_MWh", "cooler_fan_MWh",
              "facility_MWh"]].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
