#!/usr/bin/env python3
"""Archive the essential content of runs/ (28 GB raw EnergyPlus output) into results/archive/ (~100 MB, git-friendly).

Kept per run: exact model.idf and plugin config, eplusout.err (gzip), .eio sizing report (gzip), annual tables (gzip);
tower study: the full TIMESTEP plugin/EnergyPlus series used by the figures (csv.gz); hybrid study: HOURLY means of all
timestep columns (csv.gz). Raw .eso/.sql/.csv are dropped; everything is regenerable with reproduce.sh.

  python tools/archive_runs.py
"""
from __future__ import annotations

import gzip
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import analyze  # noqa: E402

RUNS, ARCH = ROOT / "runs", ROOT / "results" / "archive"


def gz(src: Path, dst: Path):
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(src, "rb") as a, gzip.open(str(dst) + ".gz", "wb", compresslevel=9) as b:
            shutil.copyfileobj(a, b)


def copy(src: Path, dst: Path):
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def keep_common(run: Path, dst: Path):
    for f in ("model.idf", "tower_water_config.json", "hybrid_config.json", "scenarios.csv"):
        copy(run / f, dst / f)
    for f in ("eplusout.err", "eplusout.eio", "eplustbl.csv"):
        gz(run / "out" / f, dst / f)


def tower_study():
    root = RUNS / "dc"
    if not root.exists():
        return
    for f in ("summary.csv", "scenarios.csv"):
        copy(root / f, ARCH / "dc" / f)
    for run in sorted(p for p in root.iterdir() if (p / "out" / "eplusout.csv").exists()):
        dst = ARCH / "dc" / run.name
        keep_common(run, dst)
        _, frames, _ = analyze.load(run)
        df = pd.concat(frames, names=["tower", "row"]).reset_index(level="row", drop=True).reset_index()
        df.to_csv(dst / "timestep.csv.gz", index=False, float_format="%.6g", compression="gzip")
        print("dc", run.name)


def hybrid_study():
    root = RUNS / "hyb"
    if not root.exists():
        return
    copy(root / "hybrid_summary.csv", ARCH / "hyb" / "hybrid_summary.csv")
    for run in sorted(p.parent.parent for p in root.glob("*/*/out/eplusout.csv")):
        dst = ARCH / "hyb" / run.parent.name / run.name
        keep_common(run, dst)
        d = pd.read_csv(run / "out" / "eplusout.csv")
        d.columns = [c.strip() for c in d.columns]
        ts = [c for c in d.columns if c.endswith("(TimeStep)")]
        x = d[["Date/Time"] + ts].dropna(subset=ts[:1]).copy()
        parts = x["Date/Time"].str.strip().str.extract(r"(\d+/\d+)\s+(\d+):(\d+)")
        minutes = parts[1].astype(int) * 60 + parts[2].astype(int)          # end of interval
        hour_ending = (minutes + 59) // 60                                   # 00:10..01:00 -> 1
        x["hour"] = parts[0] + " " + hour_ending.map(lambda h: "%02d:00" % h)
        h = x.groupby("hour", sort=False)[ts].mean()
        h.columns = [c.replace("(TimeStep)", "(hourly mean of timestep)") for c in h.columns]
        h.to_csv(dst / "hourly.csv.gz", float_format="%.6g", compression="gzip")
    print("hyb", len(list((ARCH / "hyb").glob("*/*/hourly.csv.gz"))), "runs")


def light_runs():
    """Earlier and sensitivity tower runs: summaries, scenarios, configs and logs only (no series)."""
    for root in sorted(RUNS.glob("sens_*")) + [RUNS / "dc_v1_independent_air"]:
        if not root.exists():
            continue
        for f in ("summary.csv", "scenarios.csv"):
            copy(root / f, ARCH / root.name / f)
        for run in sorted(p for p in root.iterdir() if (p / "out" / "eplusout.csv").exists()):
            keep_common(run, ARCH / root.name / run.name)
        print("light", root.name)


def dev_runs():
    for name in ("dcdev", "hybdev"):
        root = RUNS / name
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.is_file() and (f.suffix in (".json", ".txt", ".sh") or f.name in ("model.idf", "ems_precool.idf")) \
                    and f.stat().st_size < 2e6:
                copy(f, ARCH / name / f.relative_to(root))


if __name__ == "__main__":
    tower_study()
    hybrid_study()
    light_runs()
    dev_runs()
    total = sum(f.stat().st_size for f in ARCH.rglob("*") if f.is_file())
    big = [(f, f.stat().st_size) for f in ARCH.rglob("*") if f.is_file() and f.stat().st_size > 50e6]
    print("archive %.1f MB, files > 50 MB: %s" % (total / 1e6, big))
