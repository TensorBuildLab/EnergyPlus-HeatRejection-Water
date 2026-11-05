#!/usr/bin/env python3
"""Building prototypes used as case studies, made runnable in EnergyPlus 22.2.

1. LBNL/DOE large data center prototype (Sun et al., 2021), "LargeDataCenterHighITE", ASHRAE 90.1-2019, as generated
   by the OpenStudio-Standards gem (OpenStudio 3.7). Source: models/prototypes/lbnl_src/
   LargeDataCenterHighITE_3A_2019.osm, taken from the Stor4Build repository (ORNL, BSD-3-Clause), which stores the
   OpenStudio-Standards output. The OSM was translated to EnergyPlus 23.2 input with the OpenStudio 3.7 Python
   bindings (models/prototypes/translate_osm.py, separate environment) and is down-converted here to 22.2. The only
   field that differs between the two input dictionaries for the objects in this model is the trailing
   Controller:OutdoorAir "Economizer Operation Staging" (new in 23.1), which is dropped.
2. DOE large office reference building, RefBldgLargeOfficeNew2004_Chicago.idf, as shipped with EnergyPlus 22.2.

Changes to both (everything else is the prototype as published):
  * tower "Evaporation Loss Mode" = SaturatedExit (EnergyPlus' default; the data center prototype uses LossFactor).
    The thermal solution does not depend on it; it makes EnergyPlus' own evaporation output comparable with the
    plugin's EPSAT replica;
  * office only: SimulationControl set to simulate the weather-file run period (the example file runs design days
    only);
  * output meters for the facility, IT (ITE-CPU, ITE-Fans, ITE-UPS) and HVAC end uses (hourly and run period).
Climate-specific design days are applied per site by tools/run_climates.py --ddy-sizing (models/set_design_days.py).
Both prototypes size CoolingTower:SingleSpeed at EnergyPlus' fixed rating conditions, so the tower is the same at
every site (the data center tower fan power is the 90.1-2019 40.2 gpm/hp value set by OpenStudio-Standards).

  python models/prototypes/build_prototypes.py      # -> models/prototypes/lbnl_large_datacenter.idf, doe_large_office.idf
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tower_water import idf  # noqa: E402

EPLUS_DIR = Path("/srv/data1/EnergyPlus-22-2-0")
METERS = ["Electricity:Facility", "ITE-CPU:InteriorEquipment:Electricity", "ITE-Fans:InteriorEquipment:Electricity",
          "ITE-UPS:InteriorEquipment:Electricity", "Cooling:Electricity", "HeatRejection:Electricity",
          "Pumps:Electricity", "Fans:Electricity", "InteriorLights:Electricity", "InteriorEquipment:Electricity",
          "Heating:NaturalGas", "Heating:Electricity", "Humidifier:Electricity"]


def _common(objs):
    for o in objs:
        if o[0].lower() == "coolingtower:singlespeed":
            while len(o) < 25:
                o.append("")
            o[24] = "SaturatedExit"          # field 23 (0 = Name), list index = field + 1
    objs = [o for o in objs if o[0].lower() not in ("output:meter", "output:meter:meterfileonly", "output:sqlite")]
    for m in METERS:
        objs.append(idf.obj("Output:Meter", m, "Hourly"))
        objs.append(idf.obj("Output:Meter", m, "RunPeriod"))
    return objs


def lbnl_datacenter():
    src = HERE / "lbnl_src" / "LargeDataCenterHighITE_3A_2019_v232.idf"
    objs = idf.parse(src.read_text(errors="replace"))
    for o in objs:
        t = o[0].lower()
        if t == "version":
            o[1] = "22.2"
        elif t == "controller:outdoorair" and len(o) > 27:
            del o[27:]                       # "Economizer Operation Staging" does not exist in 22.2
    objs = [o for o in objs if not o[0].lower().startswith("lifecyclecost")]   # not needed; avoids 22.2 field names
    objs = _common(objs)
    out = HERE / "lbnl_large_datacenter.idf"
    out.write_text("! LBNL large data center prototype (High ITE, 90.1-2019), see models/prototypes/build_prototypes.py\n"
                   + idf.dump(objs))
    return out


def doe_office():
    src = EPLUS_DIR / "ExampleFiles" / "RefBldgLargeOfficeNew2004_Chicago.idf"
    objs = _common(idf.parse(src.read_text(errors="replace")))
    for o in objs:
        if o[0].lower() == "simulationcontrol":   # the example file simulates design days only
            o[4], o[5] = "No", "Yes"             # run sizing periods: No; run weather-file run periods: Yes
    out = HERE / "doe_large_office.idf"
    out.write_text("! DOE large office reference building (new construction 2004), see build_prototypes.py\n"
                   + idf.dump(objs))
    return out


if __name__ == "__main__":
    for f in (lbnl_datacenter(), doe_office()):
        print("wrote", f)
