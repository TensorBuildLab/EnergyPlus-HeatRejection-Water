#!/usr/bin/env python3
"""Prepare, run and post-process one model across many climates, in parallel.

Each site is a folder under weather/ holding one .epw and one .ddy. With --ddy-sizing, design days are replaced
by the site's (models/set_design_days.py), so plant sizing is climate-specific.

  python tools/run_climates.py --idf models/datacenter_chiller_tower.idf --out runs/dc \
      --sites weather/* --ddy-sizing [prepare_model.py options...]
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
import analyze  # noqa: E402
import prepare_model  # noqa: E402
import scenarios  # noqa: E402


def one(job):
    idf, site_dir, out, extra, eplus, ddy_sizing = job
    try:
        epw = sorted(site_dir.glob("*.epw"))[0]
        ddy = sorted(site_dir.glob("*.ddy"))
        args = ["--idf", str(idf), "--epw", str(epw), "--out", str(out), "--eplus", eplus] + extra
        if ddy_sizing and ddy:
            args += ["--ddy", str(ddy[0])]
        prepare_model.main(args)
        with open(out / "run.log", "w") as log:
            subprocess.run([eplus, "-r", "-d", str(out / "out"), "-w", str(epw), str(out / "model.idf")],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        s = analyze.summarize(out)
        s.insert(0, "site", site_dir.name)
        sc = scenarios.run_scenarios(out)
        sc.insert(0, "site", site_dir.name)
        sc.to_csv(out / "scenarios.csv", index=False)
        return s, sc, None
    except Exception:
        return None, None, "%s: %s" % (site_dir.name, traceback.format_exc())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idf", required=True, type=Path)
    ap.add_argument("--sites", required=True, nargs="+", type=Path, help="weather/<site> folders")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--eplus", default=prepare_model.DEFAULT_EPLUS)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--ddy-sizing", action="store_true")
    a, extra = ap.parse_known_args()
    sites = [s.resolve() for s in a.sites if s.is_dir() and list(s.glob("*.epw"))]
    jobs = [(a.idf.resolve(), s, (a.out / s.name).resolve(), extra, a.eplus, a.ddy_sizing) for s in sites]
    a.out.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(a.jobs) as pool:
        res = list(pool.map(one, jobs))
    errs = [e for _, _, e in res if e]
    for e in errs:
        print("FAILED", e)
    ok = [(s, sc) for s, sc, e in res if not e]
    if not ok:
        return 1
    summary = pd.concat([s for s, _ in ok]).reset_index().set_index(["site", "tower"])
    summary.to_csv(a.out / "summary.csv")
    pd.concat([sc for _, sc in ok]).to_csv(a.out / "scenarios.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    cols = [c for c in summary.columns if c.endswith("_vs_POPPE_%") or c in (
        "heat_rejected_MWh", "POPPE_m3", "EP_evap_m3", "EP_zero_evap_loaded_h", "fog_hours", "ref_fallback_share_%")]
    print(summary[cols].round(2).to_string())
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
