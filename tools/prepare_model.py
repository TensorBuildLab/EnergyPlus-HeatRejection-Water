#!/usr/bin/env python3
"""Add the tower-water plugin to an EnergyPlus model.

Steps:
 1. Run a design-day-only simulation to get autosized tower flows (from the .eio).
 2. Read each supported tower (CoolingTower:SingleSpeed, :VariableSpeed, :VariableSpeed:Merkel): flows, drift, cells.
 3. Write <out>/tower_water_config.json and <out>/tower_water_model_plugin.py.
 4. Write <out>/model.idf = input IDF + PythonPlugin objects + output requests.

Example:
  python tools/prepare_model.py --idf base.idf --epw weather.epw --out runs/chicago \
      --source example_hard_groundwater --treatment generic_inhibitor --annual
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tower_water import idf  # noqa: E402
from tower_water.eplus_plugin import MERKEL, SS, SUPPORTED, VS, outputs, required_output_variables  # noqa: E402
from tower_water.methods import METHODS  # noqa: E402

# EnergyPlus binary: $ENERGYPLUS, else `energyplus` on PATH, else the author's install
DEFAULT_EPLUS = os.environ.get("ENERGYPLUS") or shutil.which("energyplus") or "/srv/data1/EnergyPlus-22-2-0/energyplus"

# IDF field numbers (0 = Name) and .eio labels per tower type (EnergyPlus 22.2 IDD)
FIELDS = {
    VS: dict(water=(8, "Design Water Flow Rate [m3/s]"), air=(9, "Design Air Flow Rate [m3/s]"),
             fc_air=(None, "Air Flow Rate in free convection regime [m3/s]"),
             min_afr=12, drift=19, conc=21, cells=25),
    MERKEL: dict(water=(8, "Design Water Flow Rate [m3/s]"), air=(10, "Design Air Flow Rate [m3/s]"),
                 fc_air=(16, "Design Free Convection Regime Air Flow Rate [m3/s]"),
                 min_afr=12, drift=33, conc=35, cells=39),
    SS: dict(water=(3, "Design Water Flow Rate [m3/s]"), air=(4, "Design Air Flow Rate [m3/s]"),
             fc_air=(7, "Free Convection Regime Air Flow Rate [m3/s]"),
             fc_ua=(9, "Free Convection U-Factor Times Area Value [W/K]"),
             min_afr=None, drift=25, conc=27, cells=32, capacity_control=31),
}


def prefix_for(name: str) -> str:
    p = re.sub(r"[^A-Za-z0-9]", "", name.title())
    return p if p[:1].isalpha() else "T" + p


def sizing_values(eplus: str, idf_path: Path, epw: Path, work: Path) -> dict:
    """{(TOWER NAME, field): value} from a design-day-only run."""
    work.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([eplus, "-D", "-d", str(work), "-w", str(epw), str(idf_path)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if r.returncode != 0:
        raise SystemExit("Sizing run (design days only) failed; see %s" % (work / "eplusout.err"))
    vals = {}
    for line in (work / "eplusout.eio").read_text(errors="replace").splitlines():
        parts = [s.strip() for s in line.split(",")]
        if len(parts) >= 5 and parts[0] == "Component Sizing Information" and parts[1].lower() in {
                x.lower() for x in SUPPORTED}:
            try:
                vals[(parts[2].upper(), parts[3])] = float(parts[4])
            except ValueError:
                pass
    return vals


def num(o, i, default):
    s = idf.field(o, i, "")
    try:
        return float(s)
    except ValueError:
        return default


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--idf", required=True, type=Path)
    ap.add_argument("--epw", required=True, type=Path, help="weather file (used for the sizing run)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--source", default="example_hard_groundwater", help="water source in the library")
    ap.add_argument("--treatment", default="generic_inhibitor")
    ap.add_argument("--library", type=Path, default=ROOT / "data" / "water_sources.json")
    ap.add_argument("--fixed-cycles", type=float, default=None,
                    help="use a fixed COC instead of chemistry (e.g. to match EnergyPlus)")
    ap.add_argument("--annual", action="store_true", help="replace run periods with one full year")
    ap.add_argument("--poppe-steps", type=int, default=10)
    ap.add_argument("--coc-mode", choices=["fixed", "constituent", "dynamic"], default=None,
                    help="chemistry mode (default: fixed if --fixed-cycles else constituent)")
    ap.add_argument("--methods", default=",".join(METHODS), help="comma-separated method IDs to evaluate")
    ap.add_argument("--loss-factor", type=float, default=0.2, help="LF method, percent per K")
    ap.add_argument("--ddy", type=Path, default=None, help="replace design days with this .ddy's (models/set_design_days.py)")
    ap.add_argument("--keep-plant-sizing", action="store_true",
                    help="with --ddy: replace design days only; keep the model's tower and condenser-loop sizing "
                         "(prototype buildings)")
    ap.add_argument("--eplus", default=DEFAULT_EPLUS, help="EnergyPlus binary (default: %(default)s)")
    a = ap.parse_args(argv)

    lib = json.loads(a.library.read_text())
    if a.source not in lib["sources"]:
        raise SystemExit("Unknown --source %r in %s (known: %s)" % (a.source, a.library, ", ".join(lib["sources"])))
    if a.treatment not in lib["treatments"]:
        raise SystemExit("Unknown --treatment %r in %s (known: %s)" % (
            a.treatment, a.library, ", ".join(lib["treatments"])))

    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    objs = idf.parse(a.idf.read_text(errors="replace"))

    if a.annual:
        objs = [o for o in objs if o[0].lower() != "runperiod"]
        objs.append(idf.obj("RunPeriod", "Annual", 1, 1, "", 12, 31, "", "", "Yes", "Yes", "No", "Yes", "Yes"))
        for o in idf.find(objs, "SimulationControl"):   # make sure the weather-file run period is simulated
            o.extend([""] * (6 - len(o)))
            o[5] = "Yes"

    base = out / "base.idf"
    base.write_text(idf.dump(objs))
    if a.ddy:
        subprocess.run([sys.executable, str(ROOT / "models" / "set_design_days.py"), str(base), str(a.ddy), str(base)]
                       + (["--no-tower-update"] if a.keep_plant_sizing else []), check=True)
        objs = idf.parse(base.read_text(errors="replace"))
    sizes = sizing_values(a.eplus, base, a.epw.resolve(), out / "sizing")

    towers = []
    for o in [o for o in objs if o[0] in SUPPORTED or o[0].lower() in {x.lower() for x in SUPPORTED}]:
        typ = next(x for x in SUPPORTED if x.lower() == o[0].lower())
        f = FIELDS[typ]
        name = idf.field(o, 0)
        key = name.upper()

        def sized(spec, required=True):
            field_no, label = spec
            v = num(o, field_no, None) if field_no is not None else None
            if v is None:
                v = sizes.get((key, label))
            if v is None and required:
                raise SystemExit("No %s for tower %s (not in IDF or .eio)" % (label, name))
            return v

        towers.append({
            "name": name,
            "type": typ,
            "prefix": prefix_for(name),
            "design_water_flow": sized(f["water"]),
            "design_air_flow": sized(f["air"]),
            "free_conv_air_flow": sized(f["fc_air"], required=False) or 0.0,
            "min_air_flow_ratio": num(o, f["min_afr"], 0.2) if f["min_afr"] is not None else 0.0,
            "free_conv_ua": (sized(f["fc_ua"], required=False) or 0.0) if "fc_ua" in f else 0.0,
            "capacity_control": idf.field(o, f["capacity_control"], "FanCycling") if "capacity_control" in f else "",
            "drift_fraction": num(o, f["drift"], 0.008) / 100.0,
            "eplus_concentration_ratio": num(o, f["conc"], 3.0),
            "cells": int(num(o, f["cells"], 1)),
            "water_source": a.source,
            "treatment": a.treatment,
            "fixed_cycles": a.fixed_cycles,
            "coc_mode": a.coc_mode,
        })
    others = sorted({o[0] for o in objs if o[0].lower().startswith(("coolingtower:", "evaporativefluidcooler"))}
                    - set(SUPPORTED))
    if others:
        print("Note: not yet supported, skipped:", ", ".join(others))
    if not towers:
        raise SystemExit("No supported cooling towers found.")

    ts = idf.find(objs, "Timestep")
    method_ids = [m.strip() for m in a.methods.split(",") if m.strip()]
    bad = [m for m in method_ids if m not in METHODS]
    if bad:
        raise SystemExit("Unknown methods: %s (known: %s)" % (bad, ", ".join(METHODS)))
    cfg = {"water_library": str(a.library.resolve()), "poppe_steps": a.poppe_steps,
           "methods": method_ids, "loss_factor_pct_per_k": a.loss_factor,
           "timesteps_per_hour": int(num(ts[0], 0, 6)) if ts else 6, "towers": towers}
    (out / "tower_water_config.json").write_text(json.dumps(cfg, indent=2))
    (out / "tower_water_model_plugin.py").write_text(
        "# Generated by tools/prepare_model.py\n"
        "# EnergyPlus requires the named class to define its callbacks itself, so alias the base class.\n"
        "from tower_water.eplus_plugin import TowerWaterPlugin\n\n"
        "TowerWaterPlugin.CONFIG_PATH = %r\n"
        "ModelTowerWater = TowerWaterPlugin\n" % str(out / "tower_water_config.json"))

    # --- plugin objects ---------------------------------------------------
    objs = [o for o in objs if not o[0].lower().startswith("pythonplugin:")]
    objs.append(idf.obj("PythonPlugin:SearchPaths", "TowerWater Paths", "Yes", "Yes", "No",
                        str(ROOT / "src"), str(out)))
    objs.append(idf.obj("PythonPlugin:Instance", "TowerWater", "No", "tower_water_model_plugin", "ModelTowerWater"))
    OUTPUTS = outputs(method_ids)
    globals_ = [t["prefix"] + "_" + s for t in towers for s, _, _ in OUTPUTS]
    for i in range(0, len(globals_), 10):
        objs.append(idf.obj("PythonPlugin:Variables", "TowerWater Vars %d" % (i // 10 + 1), *globals_[i:i + 10]))
    for t in towers:
        for s, units, kind in OUTPUTS:
            g = t["prefix"] + "_" + s
            objs.append(idf.obj("PythonPlugin:OutputVariable", g, g, kind, "SystemTimestep", units))

    # --- output requests --------------------------------------------------
    # Everything at Timestep. In v22.2 plugin outputs are named "PythonPlugin:OutputVariable",
    # keyed by the PythonPlugin:OutputVariable object name.
    def ts_key(o):
        return (idf.field(o, 0, "*").upper(), idf.field(o, 1).upper(), idf.field(o, 2, "Hourly").upper())
    have = {ts_key(o) for o in idf.find(objs, "Output:Variable")}
    req = required_output_variables(cfg)
    req += [(t["name"], v) for t in towers for v in (
        "Cooling Tower Water Evaporation Volume Flow Rate", "Cooling Tower Water Drift Volume Flow Rate",
        "Cooling Tower Water Blowdown Volume Flow Rate", "Cooling Tower Make Up Water Volume Flow Rate",
        "Cooling Tower Make Up Water Volume", "Cooling Tower Water Evaporation Volume")]
    req += [(t["prefix"] + "_" + s, "PythonPlugin:OutputVariable") for t in towers for s, _, _ in OUTPUTS]
    for key, var in req:
        if (key.upper(), var.upper(), "TIMESTEP") not in have and ("*", var.upper(), "TIMESTEP") not in have:
            objs.append(idf.obj("Output:Variable", key, var, "Timestep"))

    (out / "model.idf").write_text(idf.dump(objs))
    print("Wrote", out / "model.idf")
    for t in towers:
        print("  %-28s %-34s air %.4g m3/s (free conv %.3g)  water %.4g m3/s  drift %.3g  cells %d" % (
            t["name"], t["type"], t["design_air_flow"], t["free_conv_air_flow"], t["design_water_flow"],
            t["drift_fraction"], t["cells"]))


if __name__ == "__main__":
    main()
