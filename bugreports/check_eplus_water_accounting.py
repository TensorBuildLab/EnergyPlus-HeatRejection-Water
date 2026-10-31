#!/usr/bin/env python3
"""Reproduce two EnergyPlus cooling-tower water-accounting issues with stock files only (no plugin).

Issue 1 (idle tower books water): a tower with zero heat transfer reports evaporation/makeup.
Issue 2 (Merkel free convection books no water): CoolingTower:VariableSpeed:Merkel rejects heat with
         the fan off (free convection) but reports zero evaporation.

  python bugreports/check_eplus_water_accounting.py [--eplus /path/energyplus] [--idf X.idf --epw Y.epw]

Default case: ExampleFiles/CoolingTower_VariableSpeed.idf with Golden CO TMY3, annual, timestep output.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tower_water import idf  # noqa: E402

E = Path("/srv/data1/EnergyPlus-22-2-0")
VARS = ["Cooling Tower Heat Transfer Rate", "Cooling Tower Water Evaporation Volume",
        "Cooling Tower Make Up Water Volume", "Cooling Tower Fan Electricity Rate"]


def run(eplus, idf_path, epw, work):
    objs = idf.parse(Path(idf_path).read_text(errors="replace"))
    objs = [o for o in objs if o[0].lower() not in ("runperiod", "output:variable")]
    objs.append(idf.obj("RunPeriod", "Annual", 1, 1, "", 12, 31, "", "", "Yes", "Yes", "No", "Yes", "Yes"))
    for v in VARS:
        objs.append(idf.obj("Output:Variable", "*", v, "Timestep"))
    m = Path(work) / "in.idf"
    m.write_text(idf.dump(objs))
    subprocess.run([eplus, "-r", "-d", str(Path(work) / "out"), "-w", str(epw), str(m)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return Path(work) / "out" / "eplusout.csv"


def analyse(csv_path):
    with open(csv_path) as fh:
        rows = list(csv.reader(fh))
    head = [h.strip() for h in rows[0]]
    towers = defaultdict(dict)
    for i, h in enumerate(head):
        for v in VARS:
            if h.endswith(":" + v + h[h.find(" [") if " [" in h else len(h):]) or (":" + v + " [") in h:
                towers[h.split(":")[0]][v] = i
    print("%-28s %10s %14s %18s %16s %20s" % ("tower", "MWh rej.", "evap m3", "evap m3 @ Q=0", "steps Q=0,E>0",
                                               "steps Q>0,E=0,fan=0"))
    for name, idx in towers.items():
        q_i, e_i, f_i = idx[VARS[0]], idx[VARS[1]], idx.get(VARS[3])
        tot_q = tot_e = idle_e = 0.0
        n_idle = n_fc = 0
        for r in rows[1:]:
            try:
                q, e = float(r[q_i]), float(r[e_i])
                f = float(r[f_i]) if f_i is not None else 0.0
            except (ValueError, IndexError):
                continue
            tot_e += e
            if q <= 0.0:
                if e > 0.0:
                    idle_e += e
                    n_idle += 1
            else:
                tot_q += q
                if e <= 0.0 and f <= 0.0:
                    n_fc += 1
        dt_h = 1.0 / max(1, round((len(rows) - 1) / 8760))
        print("%-28s %10.1f %14.3f %18.3f %16d %20d" % (name, tot_q * dt_h / 1e6, tot_e, idle_e, n_idle, n_fc))
    print("\nIssue 1 is present if 'evap m3 @ Q=0' > 0. Issue 2 is present if the last column > 0 for a Merkel tower.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eplus", default=str(E / "energyplus"))
    ap.add_argument("--idf", default=str(E / "ExampleFiles" / "CoolingTower_VariableSpeed.idf"))
    ap.add_argument("--epw", default=str(E / "WeatherData" / "USA_CO_Golden-NREL.724666_TMY3.epw"))
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as work:
        analyse(run(a.eplus, a.idf, a.epw, work))


if __name__ == "__main__":
    main()
