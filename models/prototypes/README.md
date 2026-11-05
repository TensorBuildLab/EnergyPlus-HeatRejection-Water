# Prototype buildings (case studies of manuscript v5)

| File | Building | Source |
|---|---|---|
| `lbnl_large_datacenter.idf` | LBNL/DOE large data center prototype, high IT density (3.0 MW design, 557 m²), ASHRAE 90.1-2019 | Sun et al. (2021), Energy and Buildings 231:110603, implemented in OpenStudio-Standards (`LargeDataCenterHighITE`). |
| `doe_large_office.idf` | DOE large office reference building, new construction 2004 (46,320 m²) | Deru et al. (2011), NREL/TP-5500-46861; `RefBldgLargeOfficeNew2004_Chicago.idf` shipped with EnergyPlus 22.2. |

## How the data center prototype was obtained

1. `lbnl_src/LargeDataCenterHighITE_3A_2019.osm` is the OpenStudio-Standards output for climate zone 3A, archived by
   the Stor4Build project (https://github.com/Stor4Build/stor4build, `models/3.7/`, BSD-3-Clause, ORNL and partners).
   Generating the prototype directly needs the OpenStudio command-line interface, whose Ruby measures were not run here.
2. `translate_osm.py` translates the OSM to EnergyPlus 23.2 input with the official OpenStudio 3.7 Python bindings
   (`pip install openstudio==3.7.0`, separate environment `/srv/data1/liangzhang/envs/ostudio`), giving
   `lbnl_src/LargeDataCenterHighITE_3A_2019_v232.idf`.
3. `build_prototypes.py` converts it to EnergyPlus 22.2. For the objects in this model the 22.2 and 23.2 input
   dictionaries differ only in the trailing `Controller:OutdoorAir` field "Economizer Operation Staging" (new in 23.1),
   which is dropped; the field-by-field comparison is reproducible with the 23.2 IDD exported from OpenStudio.

## Changes made to both prototypes (everything else as published)

* Tower `Evaporation Loss Mode` = `SaturatedExit` (EnergyPlus' default; the data center prototype uses `LossFactor`).
  The thermal solution does not depend on it; it makes EnergyPlus' own evaporation comparable with the plugin's replica.
* Output meters for the facility, IT (ITE-CPU, ITE-Fans, ITE-UPS) and HVAC end uses.
* Office only: `SimulationControl` set to simulate the weather-file run period (the distributed example simulates the
  design days only).
* Per site, `tools/run_climates.py --ddy-sizing --keep-plant-sizing` replaces the design days and location with the
  site's; tower and condenser-loop sizing stay as in the prototype. Both prototypes size their
  `CoolingTower:SingleSpeed` at EnergyPlus' fixed rating conditions (25.6 °C wet-bulb, 29.4 °C leaving water), so the
  tower is the same at every site.

## Known characteristics kept as published

* Data center: one chiller with an integrated water-side economizer, condenser setpoint = wet-bulb + 4.3 K
  (5.6–29.4 °C); the tower runs all year and cycles its fan in 96–99.9 % of hours. Envelope of climate zone 3A at all
  sites (negligible against the 3 MW IT load).
* Office: condenser setpoint = outdoor wet-bulb + 0 K, which the tower cannot reach, so its fan runs at full speed in
  96–99 % of operating hours. Chicago constructions at all sites.
