# Tutorial: cooling tower water use with the tower_water EnergyPlus plugin

This tutorial takes you from a fresh clone to annual cooling tower water results for an EnergyPlus model.
It assumes you know EnergyPlus (IDF files, output variables, `eplusout.csv`) but not this repository.
Every command below was run as written from the repository root (see [Tested with](#tested-with)).

Contents

1. [What the plugin does](#1-what-the-plugin-does)
2. [Requirements](#2-requirements)
3. [Install](#3-install)
4. [Example 1: data center prototype in Phoenix](#4-example-1-data-center-prototype-in-phoenix)
5. [Reading the outputs](#5-reading-the-outputs)
6. [What the preparer adds to the IDF](#6-what-the-preparer-adds-to-the-idf)
7. [Example 2: your own model](#7-example-2-your-own-model)
8. [Water-quality scenarios without re-simulating](#8-water-quality-scenarios-without-re-simulating)
9. [Many climates in one command](#9-many-climates-in-one-command)
10. [Running the tests](#10-running-the-tests)
11. [Troubleshooting](#11-troubleshooting)
12. [How to cite](#12-how-to-cite)

## 1. What the plugin does

The plugin is an EnergyPlus Python Plugin. At the end of every system timestep it reads the operating point of each
cooling tower (water flow, inlet and outlet water temperature, heat rejected, fan state) and the outdoor air state, and
computes tower evaporation with eight methods: `LAT`, `ROT`, `LF`, `EPSAT`, `MSAT`, `BRAUN`, `POPPE`, `POPPE1`
(equations and sources in [`METHODS.md`](METHODS.md)). For the reference method (`POPPE`) it also computes drift,
blowdown from the makeup-water chemistry, and makeup. The plugin only reads and reports values: it does **not**
change the EnergyPlus thermal solution, so energy results are the same with and without it.

## 2. Requirements

| What | Version | Used for |
|---|---|---|
| EnergyPlus | 22.2 (tested). The IDF must be in 22.2 format. | Simulation; its bundled Python runs the plugin |
| Python | 3.8 or newer | `tools/*.py` (preparing models, post-processing) |
| numpy, pandas | any recent version | `tools/analyze.py`, `tools/scenarios.py`, `tools/run_climates.py` |
| scipy, matplotlib, psychrolib | optional | verification scripts and figures only |

The plugin itself (`src/tower_water/`) uses only the Python standard library, so nothing has to be installed into
EnergyPlus' bundled Python. Supported tower objects: `CoolingTower:SingleSpeed`, `CoolingTower:VariableSpeed`,
`CoolingTower:VariableSpeed:Merkel`.

## 3. Install

```bash
git clone https://github.com/TensorBuildLab/EnergyPlus-HeatRejection-Water
cd EnergyPlus-HeatRejection-Water
```

Install numpy and pandas with your usual package manager (pip or conda); the optional extras are listed under
`analysis` in `pyproject.toml`. Check that the Python you will use sees them, and that EnergyPlus is found:

```bash
python -c "import numpy, pandas; print(numpy.__version__, pandas.__version__)"
energyplus --version
```

If `energyplus` is not on your `PATH`, use its full path in the commands below (for example
`/usr/local/EnergyPlus-22-2-0/energyplus`) and give the same path to the tools with `--eplus`, or set the environment
variable `ENERGYPLUS`. `tools/prepare_model.py` looks for EnergyPlus in this order: `--eplus`, `$ENERGYPLUS`,
`energyplus` on the `PATH`.

All commands are written for a bash shell (Linux, macOS, or Git Bash/WSL on Windows). In other shells, replace the
`*.epw` / `*.ddy` wildcards with the full file names.

## 4. Example 1: data center prototype in Phoenix

The model is the LBNL/DOE large data center prototype (`models/prototypes/lbnl_large_datacenter.idf`, 3 MW IT,
one `CoolingTower:SingleSpeed` with two cells and fan cycling; see `models/prototypes/README.md`). The weather is the
Phoenix TMYx file shipped in `weather/phoenix_tmyx/`. The makeup water is Phoenix's municipal supply from the sourced
library, treated with the EVAPCO galvanized-steel inhibitor limits.

### Step 1: prepare the model (about 2 s)

```bash
python tools/prepare_model.py --idf models/prototypes/lbnl_large_datacenter.idf \
    --epw weather/phoenix_tmyx/*.epw --ddy weather/phoenix_tmyx/*.ddy --keep-plant-sizing --annual \
    --library data/water_sources_sourced.json --source phoenix_tmyx --treatment evapco_galvanized_inhibitor \
    --out runs/tutorial_test/phoenix
```

This (1) replaces the design days and location with Phoenix's, keeping the prototype's own tower and condenser-loop
sizing (`--keep-plant-sizing`), (2) sets one annual run period, (3) runs a design-day-only simulation to read the
autosized tower flows from the `.eio`, and (4) writes the run folder:

| File | Content |
|---|---|
| `model.idf` | Your model plus the plugin objects and output requests (section 6). Simulate this file. |
| `tower_water_config.json` | Tower data (flows, drift, cells, cycles) and options (methods, water source, treatment) |
| `tower_water_model_plugin.py` | Three-line module EnergyPlus imports; points the plugin at the config |
| `base.idf`, `sizing/` | Intermediate model and the sizing run |

The last lines of the output list the towers found:

```
Wrote .../runs/tutorial_test/phoenix/model.idf
  Centrifugal Fan Cycling Open Cooling Tower 40.2 gpm/hp CoolingTower:SingleSpeed  air 352.6 m3/s (free conv 35.3)  water 0.496 m3/s  drift 8e-05  cells 2
```

### Step 2: run EnergyPlus (about 1 min 40 s)

```bash
energyplus -r -d runs/tutorial_test/phoenix/out -w weather/phoenix_tmyx/*.epw runs/tutorial_test/phoenix/model.idf
```

`eplusout.err` should contain lines such as
`PythonPlugin: Class ModelTowerWater imported from: .../tower_water_model_plugin.py` and end with
`EnergyPlus Completed Successfully-- 13 Warning; 0 Severe Errors`.

### Step 3: summarize (about 5 s)

```bash
python tools/analyze.py runs/tutorial_test/phoenix --csv runs/tutorial_test/phoenix/timestep.csv
```

This prints the annual summary per tower (below) and, with `--csv`, writes a tidy timestep table (`ep_*` columns are
EnergyPlus outputs, `pl_*` columns plugin outputs, `site_*` columns outdoor air).

### Annual results of Example 1

Phoenix TMYx 2011-2025, 8,760 h of tower operation, 23,514 MWh of heat rejected. Deviation is relative to `POPPE`.

| Method | Annual evaporation (m3) | vs POPPE (%) |
|---|---:|---:|
| EnergyPlus (`SaturatedExit`) | 60,377 | +31.5 |
| `EPSAT` (replica of EnergyPlus) | 60,369 | +31.4 |
| `MSAT` | 50,973 | +11.0 |
| `POPPE1` | 46,621 | +1.5 |
| **`POPPE` (reference)** | **45,928** | 0 |
| `BRAUN` | 44,653 | -2.8 |
| `LF` (0.2 %/K) | 40,546 | -11.7 |
| `LAT` | 34,527 | -24.8 |
| `ROT` | 31,018 | -32.5 |

| Water balance | EnergyPlus | Plugin (POPPE, Phoenix water) |
|---|---:|---:|
| Cycles of concentration | 3.0 (fixed input) | 2.50 (limited by TDS, `CycLimit` = 7) |
| Annual makeup (m3) | 90,566 | 76,465 |

Other lines of the summary: `EPSAT_replica_err_%` = -0.01 (the replica reproduces EnergyPlus' own number),
`ref_fallback_share_%` = 0 (Poppe solved every timestep), `status_hours` = `{'ok': 8760.0}`, `fog_hours` = 1.7.
Per heat rejected, Poppe gives 45,928 m3 / 23,514 MWh = 1.95 L/kWh.

Most of the EnergyPlus overprediction for this tower comes from the way EnergyPlus averages fan cycling (see the
paper and `tools/single_speed_check.py`); for variable-speed towers the differences are much smaller (Example 2).

## 5. Reading the outputs

All plugin outputs are reported at the zone timestep in `out/eplusout.csv` (and `.eso`). The tower prefix is the tower
name with non-alphanumeric characters removed (`Centrifugal Fan Cycling Open Cooling Tower 40.2 gpm/hp` becomes
`CentrifugalFanCyclingOpenCoolingTower402GpmHp`). Column header format:

```
CentrifugalFanCyclingOpenCoolingTower402GpmHp_E_POPPE:PythonPlugin:OutputVariable [m3/s](TimeStep)
```

| Output (`<Prefix>_...`) | Units | Meaning |
|---|---|---|
| `E_LAT`, `E_ROT`, `E_LF`, `E_EPSAT`, `E_MSAT`, `E_BRAUN`, `E_POPPE`, `E_POPPE1` | m3/s | Evaporation by each method (only the methods you selected) |
| `Drift` | m3/s | Drift (tower drift fraction x water flow) |
| `Blowdown` | m3/s | Blowdown for `POPPE` evaporation at the chemistry cycles |
| `Makeup` | m3/s | Makeup = evaporation + drift + blowdown (POPPE) |
| `MakeupVol` | m3 | Makeup volume in the timestep (sum it for annual totals) |
| `Cycles` | - | Cycles of concentration used |
| `CycLimit` | - | Limiting constraint: 0 fixed, 1 max cycles, 2 silica, 3 calcium hardness, 4 alkalinity, 5 chloride, 6 sulfate, 7 TDS, 8 LSI, 9 silica solubility |
| `AirMass` | kg/s | Dry-air mass flow through the tower (time-averaged) |
| `AirOutT`, `AirOutW` | C, kg/kg | Exhaust air temperature and humidity ratio (POPPE) |
| `Fog` | - | 1 when the exhaust is supersaturated |
| `Mist` | m3/s | Liquid water carried by supersaturated exhaust (part of `E_POPPE`) |
| `MePoppe`, `MeMerkel`, `NTU` | - | Merkel numbers and NTU of the operating point |
| `AirScale` | - | Air-flow scaling applied at operating points beyond the thermodynamic limit (1 = none) |
| `Status` | - | 0 ok, 1 idle, 2 no air flow, 3 infeasible, 4 clipped, 5 air adjusted (status 2 and 3 use `MSAT` for that timestep) |

EnergyPlus' own tower water outputs (`Cooling Tower Water Evaporation Volume Flow Rate`, `... Drift ...`,
`... Blowdown ...`, `Cooling Tower Make Up Water Volume Flow Rate`) are requested as well, so you can compare.

To use the outputs directly, note that models with "Do HVAC Sizing Simulation for Sizing Periods" also write the
design days to `eplusout.csv` before the annual period (the data center prototype does). Keep the last 8,760 x
timesteps-per-hour rows (`tools/analyze.py` does this for you):

```bash
python - <<'EOF'
import pandas as pd
df = pd.read_csv("runs/tutorial_test/phoenix/out/eplusout.csv").tail(8760 * 6)  # drop design-day rows
p = "CentrifugalFanCyclingOpenCoolingTower402GpmHp"
e_poppe = df[p + "_E_POPPE:PythonPlugin:OutputVariable [m3/s](TimeStep)"]          # m3/s per 10-min timestep
print("Poppe evaporation  %.0f m3" % (e_poppe.sum() * 600))
print("Plugin makeup      %.0f m3" % df[p + "_MakeupVol:PythonPlugin:OutputVariable [m3](TimeStep)"].sum())
EOF
```

Output: `Poppe evaporation  45928 m3` and `Plugin makeup      76465 m3`, the same as `tools/analyze.py`.

## 6. What the preparer adds to the IDF

`tools/prepare_model.py` copies your model and appends the objects below (shortened from the `model.idf` of
Example 1). If you prefer to add them by hand, you still need `tower_water_config.json` and the plugin module, so
running the preparer once is the easiest way to get them.

```
PythonPlugin:SearchPaths,
    TowerWater Paths,                                  ! name
    Yes,                                               ! add current working directory
    Yes,                                               ! add input file directory
    No,                                                ! add epin environment variable
    /path/to/EnergyPlus-HeatRejection-Water/src,       ! search path 1: the tower_water package
    /path/to/EnergyPlus-HeatRejection-Water/runs/tutorial_test/phoenix;   ! search path 2: the generated module

PythonPlugin:Instance,
    TowerWater,                                        ! name
    No,                                                ! run during warmup days
    tower_water_model_plugin,                          ! Python module (tower_water_model_plugin.py)
    ModelTowerWater;                                   ! class

PythonPlugin:Variables,                                ! global variables the plugin writes, 10 per object
    TowerWater Vars 1,
    CentrifugalFanCyclingOpenCoolingTower402GpmHp_E_LAT,
    CentrifugalFanCyclingOpenCoolingTower402GpmHp_E_ROT,
    ...
    CentrifugalFanCyclingOpenCoolingTower402GpmHp_Blowdown;

PythonPlugin:OutputVariable,                           ! one per global variable
    CentrifugalFanCyclingOpenCoolingTower402GpmHp_E_POPPE,   ! name (the output key)
    CentrifugalFanCyclingOpenCoolingTower402GpmHp_E_POPPE,   ! global variable
    Averaged,                                          ! type (Summed for MakeupVol)
    SystemTimestep,                                    ! update frequency
    m3/s;                                              ! units

Output:Variable,                                       ! inputs the plugin reads (handles need these requests)
    Centrifugal Fan Cycling Open Cooling Tower 40.2 gpm/hp,
    Cooling Tower Heat Transfer Rate,
    Timestep;

Output:Variable,
    Environment,
    Site Outdoor Air Wetbulb Temperature,
    Timestep;

Output:Variable,                                       ! the plugin results
    CentrifugalFanCyclingOpenCoolingTower402GpmHp_E_POPPE,
    PythonPlugin:OutputVariable,
    Timestep;
```

The generated `tower_water_model_plugin.py` is:

```python
from tower_water.eplus_plugin import TowerWaterPlugin

TowerWaterPlugin.CONFIG_PATH = '/path/to/.../runs/tutorial_test/phoenix/tower_water_config.json'
ModelTowerWater = TowerWaterPlugin
```

The search paths and `CONFIG_PATH` are absolute. If you move the repository or the run folder, prepare the model
again.

## 7. Example 2: your own model

### What the tower must look like

- One or more `CoolingTower:SingleSpeed`, `CoolingTower:VariableSpeed` or `CoolingTower:VariableSpeed:Merkel` objects
  in a working plant loop. Other heat-rejection objects (for example `CoolingTower:TwoSpeed`) are skipped with a note.
- Design water flow, design air flow and free-convection air flow may be autosized: the preparer reads them from the
  sizing run. Drift loss percent (default 0.008 %), blowdown concentration ratio (default 3), number of cells and,
  for the single-speed tower, capacity control (fan cycling or fluid bypass) are read from the object.
- Set `Evaporation Loss Mode` to `SaturatedExit` (EnergyPlus' default) if you want EnergyPlus' own evaporation to be
  comparable with the `EPSAT` replica. The thermal solution does not depend on this field.
- The IDF must be EnergyPlus 22.2 input (use EnergyPlus' IDFVersionUpdater for older files).

### Run

The example uses `models/CoolingTower_MerkelVariableSpeed.idf` (the EnergyPlus example file: DOE large office with two
`CoolingTower:VariableSpeed:Merkel` towers) in Atlanta. Replace `--idf`, `--epw` and `--ddy` with your own files.

```bash
python tools/prepare_model.py --idf models/CoolingTower_MerkelVariableSpeed.idf \
    --epw weather/atlanta/*.epw --ddy weather/atlanta/*.ddy --annual \
    --methods POPPE,EPSAT,MSAT,LF --loss-factor 0.2 \
    --library data/water_sources_sourced.json --source atlanta --treatment icc_advanced_inhibitor --coc-mode dynamic \
    --out runs/tutorial_test/my_model
energyplus -r -d runs/tutorial_test/my_model/out -w weather/atlanta/*.epw runs/tutorial_test/my_model/model.idf
python tools/analyze.py runs/tutorial_test/my_model
```

The EnergyPlus run takes about 80 s. Annual results for the first tower (`TowerWaterSys CoolTower1`, 3,740 MWh
rejected): `POPPE` 5,792 m3; EnergyPlus 5,539 m3 (-4.4 %); `MSAT` -2.3 %; `LF` +11.4 %. Makeup: EnergyPlus 8,308 m3 at
3 cycles, plugin 6,436 m3 at 10 cycles (the soft Atlanta water reaches the 10-cycle cap of the treatment program).

### Options of `tools/prepare_model.py`

| Option | Default | What it does |
|---|---|---|
| `--idf`, `--epw`, `--out` | required | Input model, weather file (also used for the sizing run), output folder |
| `--methods` | all eight | Comma-separated method IDs. Keep `POPPE` in the list: the water balance and `analyze.py` use it as reference. Poppe costs most of the run time. |
| `--loss-factor` | 0.2 | Loss factor of the `LF` method, percent per K of range |
| `--library` | `data/water_sources.json` | Water-quality library. `data/water_sources_sourced.json` has sourced makeup water for the 14 sites in `weather/` and five sourced treatment programs (`docs/WATER_QUALITY_SOURCES.md`). `data/water_sources.json` has three illustrative sources, not from any utility. |
| `--source` | `example_hard_groundwater` | Makeup-water source in the library. Sourced: `atlanta`, `dallas`, `houston`, `las_vegas`, `phoenix_tmyx`, `portland_or`, `montreal`, `dublin`, `frankfurt`, `madrid`, `stockholm`, `riyadh`, `mumbai`, `singapore`. Example library: `example_soft_surface`, `example_hard_groundwater`, `example_reclaimed`. |
| `--treatment` | `generic_inhibitor` | Treatment limits. Sourced: `evapco_galvanized_inhibitor`, `icc_advanced_inhibitor`, `acid_feed_ph7p5`, `bac_galvanized`, `evapco_stainless316`. Example library: `generic_inhibitor`, `generic_inhibitor_dynamic` (use the latter with `--coc-mode dynamic`). |
| `--coc-mode` | `constituent` (or `fixed` with `--fixed-cycles`) | `fixed`: given cycles, as EnergyPlus. `constituent`: cycles from the constituent limits (silica, hardness, alkalinity, chloride, sulfate, TDS), constant. `dynamic`: adds the Langelier index at the hot-water temperature and silica solubility at the cold-water temperature, every timestep. |
| `--fixed-cycles` | none | Use this number of cycles instead of chemistry (for example 4) |
| `--ddy` | none | Replace the design days and location with this `.ddy` file's (0.4 % cooling DB and WB, 99.6 % heating). Without `--keep-plant-sizing` it also sets Merkel towers' design inlet air and the condenser `Sizing:Plant` exit temperature (WB + tower approach), so the tower is sized for the climate. |
| `--keep-plant-sizing` | off | With `--ddy`: replace the design days only, keep the model's tower and condenser-loop sizing (use for the prototypes) |
| `--annual` | off | One run period, 1 Jan to 31 Dec, and "Run Simulation for Weather File Run Periods" = Yes |
| `--poppe-steps` | 10 | Integration steps of the Poppe method |
| `--eplus` | `$ENERGYPLUS`, else `energyplus` on `PATH` | EnergyPlus binary for the sizing run |

## 8. Water-quality scenarios without re-simulating

Blowdown and makeup depend on the makeup water and the treatment, but evaporation does not. `tools/scenarios.py`
recomputes drift, blowdown and makeup for every method x water source x chemistry mode from the timestep evaporation
and water temperatures stored in a finished run, in about a second:

```bash
python tools/scenarios.py runs/tutorial_test/phoenix
python tools/scenarios.py runs/tutorial_test/phoenix --library data/water_sources_sourced.json \
    --treatment evapco_galvanized_inhibitor --fixed-cycles 4
```

The first command uses the illustrative library with the generic treatments; the second evaluates all 14 sourced
sources under one sourced treatment, with 4 cycles for the `fixed` mode (default: the tower's EnergyPlus
concentration ratio). Results go to `<run>/scenarios.csv` (columns `method, source, mode, evap_m3, drift_m3,
blowdown_m3, makeup_m3, coc_mean`; one `EnergyPlus` row with EnergyPlus' own numbers); the screen shows `POPPE`,
`EPSAT` and EnergyPlus. From the second command, for the Phoenix data center:

| POPPE evaporation, 45,928 m3 | Cycles | Blowdown (m3) | Makeup (m3) |
|---|---:|---:|---:|
| Phoenix water, fixed 4 cycles | 4.00 | 14,611 | 61,238 |
| Phoenix water, constituent limits | 2.50 | 29,839 | 76,465 |
| Dublin water, constituent limits | 10.00 | 4,405 | 51,031 |

The Phoenix constituent row reproduces the plugin's makeup from the simulation (76,465 m3).

## 9. Many climates in one command

`tools/run_climates.py` prepares, simulates and summarizes one model for several `weather/<site>` folders (each with
one `.epw` and one `.ddy`) in parallel. Options it does not know are passed to `prepare_model.py`.

```bash
python tools/run_climates.py --idf models/prototypes/doe_large_office.idf --out runs/tutorial_test/office \
    --sites weather/phoenix_tmyx weather/stockholm --ddy-sizing --keep-plant-sizing --annual --fixed-cycles 4 --jobs 2
```

`--ddy-sizing` passes each site's `.ddy` as `--ddy`; `--jobs` sets the number of parallel EnergyPlus runs (default 16).
Use `--sites weather/*` for all 14 sites. Two sites with two jobs took about 1 min 50 s. Output: one folder per site
(as in Example 1, with `run.log` and `scenarios.csv`), plus `summary.csv` (the `analyze.py` summary, one row per site
and tower) and `scenarios.csv` (all sites). Result for the DOE large office prototype:

| Site | Heat rejected (MWh) | POPPE (m3) | EnergyPlus (m3) | EnergyPlus vs POPPE (%) |
|---|---:|---:|---:|---:|
| Phoenix | 8,964 | 23,083 | 25,695 | +11.3 |
| Stockholm | 1,626 | 2,782 | 2,940 | +5.7 |

## 10. Running the tests

The tests use the standard `unittest` module (no extra package needed; psychrolib is used as an independent check
when installed):

```bash
python -m unittest discover -s tests
```

Expected: `Ran 60 tests ... OK` (under a second).

## 11. Troubleshooting

| Message | Cause and fix |
|---|---|
| `Note: not yet supported, skipped: CoolingTower:TwoSpeed` and `No supported cooling towers found.` | The model has no supported tower. Use one of the three supported objects. |
| `Unknown --source 'dublin' in .../water_sources.json (known: ...)` | The source or treatment is not in the library. The sourced site names are in `data/water_sources_sourced.json`: add `--library data/water_sources_sourced.json`. |
| `Sizing run (design days only) failed; see <out>/sizing/eplusout.err` | Your model does not run in EnergyPlus on the design days; read that `eplusout.err`. One case we met: `--ddy` without `--keep-plant-sizing` at a cool site (design wet-bulb below 20 C, the IDD minimum for the Merkel tower's design inlet wet-bulb) gave `Autosizing of cooling tower UA failed` for the stock Merkel example in Dublin. Use `--keep-plant-sizing`, or enter the tower's `Design Approach Temperature` and `Design Range Temperature` (3.9 and 5.6 K worked there). |
| `** Severe ** TowerWaterPlugin: missing handles: <tower> / Cooling Tower Fan Speed Ratio` followed by `returned 1 to indicate EnergyPlus should abort` | An input variable the plugin reads is not requested, or the tower was renamed after preparing. The plugin needs the `Output:Variable` requests that `prepare_model.py` adds (section 6). Prepare the model again after any change to tower names. |
| `** Severe ** Failed to import module "tower_water_model_plugin"` (`ModuleNotFoundError`) | The `PythonPlugin:SearchPaths` do not point to the run folder and to `src/`, for example because the folder was moved. Prepare the model again. |
| `** Warning ** Version: in IDF="9.6" not the same as expected="22.2"`, or tower flows in the config that look wrong | The tools read tower fields by position in the EnergyPlus 22.2 input dictionary, and plugin outputs are named as in 22.2. Convert the IDF to 22.2 (IDFVersionUpdater) and use EnergyPlus 22.2. Other versions are not tested. |
| `energyplus: command not found` | Use the full path to the binary, and pass it to the tools with `--eplus` or `ENERGYPLUS=...`. |
| No results for the year (only design days in `eplusout.csv`) | The model's `SimulationControl` does not simulate the weather-file run period. Use `--annual`, which sets it. |

## 12. How to cite

Please cite the repository:

> L. Zhang, tower_water: multi-method cooling tower water consumption for EnergyPlus (software),
> https://github.com/TensorBuildLab/EnergyPlus-HeatRejection-Water

The paper describing the methods and results (L. Zhang, "Evaluating cooling tower evaporation models for data center
water use in building energy simulation") is under review; this section will give the full reference once it is
published.

## Tested with

EnergyPlus 22.2.0 (c249759bad) with its bundled Python 3.8, Python 3.11.18 with numpy 2.4.6 and pandas 3.1.0, on
Linux. Run times above are for one core of that machine.
