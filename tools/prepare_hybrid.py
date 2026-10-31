#!/usr/bin/env python3
"""Add the hybrid adiabatic dry cooler plugin to a model with FluidCooler:TwoSpeed objects on one OutdoorAir:Node.

  python tools/prepare_hybrid.py --idf models/datacenter_chiller_hybrid.idf --epw W.epw [--ddy W.ddy] --out runs/h \
      --strategy threshold --t-on 26 [--eps 0.85 --system media|spray --dp 0 ...]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from tower_water import idf  # noqa: E402
from tower_water.eplus_hybrid import OUTPUTS, PREFIX, required_output_variables  # noqa: E402
from prepare_model import DEFAULT_EPLUS, num  # noqa: E402

TWO = "FluidCooler:TwoSpeed"
# IDF field numbers (0 = Name) and .eio labels
FIELDS = dict(v_high=(14, "Air Flow Rate at High Fan Speed [m3/s]"), p_high=(15, "Fan Power at High Fan Speed [W]"),
              v_low=(16, "Air Flow Rate at Low Fan Speed [m3/s]"), p_low=(18, "Fan Power at Low Fan Speed [W]"),
              node=20)


def sizing(eplus, idf_path, epw, work):
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run([eplus, "-D", "-d", str(work), "-w", str(epw), str(idf_path)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    vals = {}
    for line in (work / "eplusout.eio").read_text(errors="replace").splitlines():
        p = [s.strip() for s in line.split(",")]
        if len(p) >= 5 and p[0] == "Component Sizing Information" and p[1].lower() == TWO.lower():
            try:
                vals[(p[2].upper(), p[3])] = float(p[4])
            except ValueError:
                pass
    return vals


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--idf", required=True, type=Path)
    ap.add_argument("--epw", required=True, type=Path)
    ap.add_argument("--ddy", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--eplus", default=DEFAULT_EPLUS)
    ap.add_argument("--annual", action="store_true")
    ap.add_argument("--strategy", choices=["dry", "wet", "threshold"], default="threshold")
    ap.add_argument("--t-on", type=float, default=26.0)
    ap.add_argument("--hysteresis", type=float, default=2.0)
    ap.add_argument("--t-freeze", type=float, default=5.0)
    ap.add_argument("--min-depression", type=float, default=0.0)
    ap.add_argument("--eps", type=float, default=0.85, help="pad effectiveness")
    ap.add_argument("--system", choices=["media", "spray"], default="media")
    ap.add_argument("--spray-efficiency", type=float, default=0.6)
    ap.add_argument("--dp", type=float, default=0.0, help="pad pressure drop at design velocity [Pa]")
    ap.add_argument("--source", default="example_hard_groundwater")
    ap.add_argument("--treatment", default="generic_inhibitor")
    ap.add_argument("--fixed-cycles", type=float, default=None)
    ap.add_argument("--coc-mode", default=None)
    a = ap.parse_args(argv)

    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    objs = idf.parse(a.idf.read_text(errors="replace"))
    if a.annual:
        objs = [o for o in objs if o[0].lower() != "runperiod"]
        objs.append(idf.obj("RunPeriod", "Annual", 1, 1, "", 12, 31, "", "", "Yes", "Yes", "No", "Yes", "Yes"))
    base = out / "base.idf"
    base.write_text(idf.dump(objs))
    if a.ddy:
        subprocess.run([sys.executable, str(ROOT / "models" / "set_design_days.py"), str(base), str(a.ddy), str(base),
                        "--pad-effectiveness", str(a.eps)], check=True)
        objs = idf.parse(base.read_text(errors="replace"))
    sizes = sizing(a.eplus, base, a.epw.resolve(), out / "sizing")

    coolers, nodes = [], set()
    for o in idf.find(objs, TWO):
        name = idf.field(o, 0)

        def val(key):
            fno, label = FIELDS[key]
            v = num(o, fno, None)
            if v is None:
                v = sizes.get((name.upper(), label))
            if v is None:
                raise SystemExit("No %s for %s" % (label, name))
            return v

        coolers.append({"name": name, **{k: val(k) for k in ("v_high", "p_high", "v_low", "p_low")}})
        nodes.add(idf.field(o, FIELDS["node"]))
    if not coolers:
        raise SystemExit("No FluidCooler:TwoSpeed found")
    if len(nodes) != 1 or "" in nodes:
        raise SystemExit("All coolers must share one OutdoorAir:Node (found %s)" % nodes)
    node = nodes.pop()

    ts = idf.find(objs, "Timestep")
    cfg = {
        "node": node, "coolers": coolers, "timesteps_per_hour": int(num(ts[0], 0, 6)) if ts else 6,
        "pad": {"eps_design": a.eps, "system": a.system, "spray_efficiency": a.spray_efficiency,
                "dp_design": a.dp, "v_design": sum(c["v_high"] for c in coolers)},
        "controller": {"strategy": a.strategy, "t_on": a.t_on, "hysteresis": a.hysteresis,
                       "t_freeze": a.t_freeze, "min_depression": a.min_depression},
        "water_library": str((ROOT / "data" / "water_sources.json").resolve()), "water_source": a.source,
        "treatment": a.treatment, "fixed_cycles": a.fixed_cycles, "coc_mode": a.coc_mode,
    }
    (out / "hybrid_config.json").write_text(json.dumps(cfg, indent=2))
    (out / "hybrid_model_plugin.py").write_text(
        "# Generated by tools/prepare_hybrid.py\n"
        "from tower_water.eplus_hybrid import HybridCoolerPlugin\n\n"
        "HybridCoolerPlugin.CONFIG_PATH = %r\n"
        "ModelHybridCooler = HybridCoolerPlugin\n" % str(out / "hybrid_config.json"))

    objs = [o for o in objs if not o[0].lower().startswith("pythonplugin:")]
    objs.append(idf.obj("PythonPlugin:SearchPaths", "Hybrid Paths", "Yes", "Yes", "No", str(ROOT / "src"), str(out)))
    objs.append(idf.obj("PythonPlugin:Instance", "HybridCooler", "Yes", "hybrid_model_plugin", "ModelHybridCooler"))
    g = [PREFIX + "_" + s for s, _, _ in OUTPUTS]
    for i in range(0, len(g), 10):
        objs.append(idf.obj("PythonPlugin:Variables", "Hybrid Vars %d" % (i // 10 + 1), *g[i:i + 10]))
    for s, units, kind in OUTPUTS:
        objs.append(idf.obj("PythonPlugin:OutputVariable", PREFIX + "_" + s, PREFIX + "_" + s, kind, "SystemTimestep", units))
    have = {(idf.field(o, 0, "*").upper(), idf.field(o, 1).upper(), idf.field(o, 2, "Hourly").upper())
            for o in idf.find(objs, "Output:Variable")}
    req = required_output_variables(cfg) + [(PREFIX + "_" + s, "PythonPlugin:OutputVariable") for s, _, _ in OUTPUTS]
    req += [(node, "System Node Temperature")]
    for key, var in req:
        if (key.upper(), var.upper(), "TIMESTEP") not in have and ("*", var.upper(), "TIMESTEP") not in have:
            objs.append(idf.obj("Output:Variable", key, var, "Timestep"))
    (out / "model.idf").write_text(idf.dump(objs))
    print("Wrote %s: %d coolers on node %s, strategy %s" % (out / "model.idf", len(coolers), node, a.strategy))
    for c in coolers:
        print("  %-18s V_high %.2f V_low %.2f m3/s  P_high %.0f P_low %.0f W" % (
            c["name"], c["v_high"], c["v_low"], c["p_high"], c["p_low"]))


if __name__ == "__main__":
    main()
