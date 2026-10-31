# Hybrid adiabatic dry cooler: user guide

Equations and assumptions: `docs/METHODS.md` §6b. Data-center model: `models/DATACENTER_MODEL.md` §6.
Results: `results/study/hybrid_key.csv`, `results/figures/fig_hybrid_*.png`, paper §7.

## What it is

EnergyPlus has dry fluid coolers but no water-side hybrid (adiabatic) cooler. This tool builds one:

```
outdoor air ──► wetted pads (plugin) ──► OutdoorAir:Node "Hybrid Cooler Air Inlet" ──► FluidCooler:TwoSpeed bank (EnergyPlus)
                    │  T_pre = T_db − ε (T_db − T_wb),  ω from adiabatic saturation            │
                    └─ water: E = Σ f_k ṁ_a,k (ω_pre − ω_in) + bleed / runoff                    └─► condenser setpoint follows the node
```

Each zone timestep, the plugin (`src/tower_water/eplus_hybrid.py`) decides wet or dry. In wet mode it overrides the node's
dry-bulb with the pad-leaving temperature and keeps the wet-bulb, using EMS actuators
(`Outdoor Air System Node` → `Drybulb Temperature` / `Wetbulb Temperature`). EnergyPlus then simulates the coils with
pre-cooled air, and `SetpointManager:FollowSystemNodeTemperature` lowers the condenser setpoint in the same timestep (verified,
0.0 K error). At the end of each system timestep the plugin books pad water from the coolers' actual air flow, which it recovers
exactly from the reported fan power (two-speed cycling logic of `FluidCoolerspecs::calcTwoSpeed`).

**This plugin changes the EnergyPlus solution** (fan energy, condenser temperature, chiller energy). The tower plugin
(`eplus_plugin.py`) does not.

## Requirements on the model

- One or more `FluidCooler:TwoSpeed` objects, all with the same `OutdoorAir:Node` in "Outdoor Air Inlet Node Name".
- **Hard-sized air flows and fan powers.** EnergyPlus 22.2 autosizes fluid-cooler air flow about three orders of magnitude too large
  (`bugreports/README.md` §5), which would make pad water meaningless.
- Optional but recommended: a condenser setpoint manager that follows the node dry-bulb, so wet operation benefits the chillers.
- `models/build_datacenter_idf.py --heat-rejection hybrid` builds a complete example (`models/datacenter_chiller_hybrid.idf`).

## Run

```bash
PY=/srv/data1/liangzhang/envs/towerwater/bin/python
E=/srv/data1/EnergyPlus-22-2-0
$PY tools/prepare_hybrid.py --idf models/datacenter_chiller_hybrid.idf \
    --epw weather/phoenix_tmyx/*.epw --ddy weather/phoenix_tmyx/*.ddy --out runs/h_phx \
    --strategy threshold --t-on 28
$E/energyplus -r -d runs/h_phx/out -w weather/phoenix_tmyx/*.epw runs/h_phx/model.idf

# study: sites x strategies, then figures/tables
$PY tools/run_hybrid_study.py --idf models/datacenter_chiller_hybrid.idf --out runs/hyb --sites weather/* --t-on 16 20 24 28 32
$PY tools/hybrid_report.py runs/hyb
```

`--ddy` resizes the plant for the site: `models/set_design_days.py` sets the coolers' wet design point
(entering air = T_db − ε(T_db − T_wb) at the 0.4 % DB=>MWB condition), air flows (8 K design air rise), low-speed capacity and
the condenser design temperature.

### Options (`tools/prepare_hybrid.py`)

| option | default | meaning |
|---|---|---|
| `--strategy` | `threshold` | `dry` (never wet), `wet` (always above `--t-freeze`), `threshold` |
| `--t-on`, `--hysteresis` | 26, 2 K | wet when T_db ≥ T_on; back to dry below T_on − hysteresis |
| `--t-freeze` | 5 °C | never wet below this dry-bulb |
| `--min-depression` | 0 K | require T_db − T_wb ≥ this to wet |
| `--eps` | 0.85 | pad effectiveness (assumption; replace with manufacturer data) |
| `--system` | `media` | `media`: recirculating pads with bleed E/(N−1); `spray`: once-through, runoff E(1/η − 1) |
| `--spray-efficiency` | 0.6 | η for spray systems (assumption) |
| `--dp` | 0 Pa | pad pressure drop at design velocity; reported as `HC_FanPenalty`, not added to EnergyPlus fan power |
| `--source`, `--treatment`, `--fixed-cycles`, `--coc-mode` | | water chemistry for the media bleed (same library as towers) |

### Outputs (`HC_<name>:PythonPlugin:OutputVariable`, bank totals)

`Wet` (0/1), `PreT` and `PreW` (air leaving pads), `Eps`, `Air` (kg/s dry air through the coils), `Heat` and `FanPower` (sum of
coolers), `FanPenalty` (W), `Evap`, `Bleed`, `Makeup` (m³/s), `MakeupVol` (m³ per timestep), `Cycles`.

## Verification

`tests/test_hybrid.py` (10 tests): pad state at ε = 1 equals the ASHRAE wet-bulb saturation state (0.2 %); pad-leaving air keeps
the inlet wet-bulb (0.03 K); energy conservation to 1e-9; fan-state inversion reproduces EnergyPlus fan power exactly;
media/spray water balances; controller hysteresis and freeze lock-out; plugin actuation and water booking are consistent
(same ε, same air state). In EnergyPlus: node dry-bulb equals the imposed value (0.0 K), the setpoint follows in the same
timestep, the dry case reproduces the plugin-free model exactly (PUE 1.343 both).

## Known limitations

- Constant ε in the plugin (velocity-dependent ε exists in `hybrid.pad_effectiveness` for standalone use).
- Pads wet only while fans run; drying-out, flushing, start-up water and freeze protection beyond the lock-out are not modelled.
- Control uses the current timestep's weather (perfect knowledge); no demand-based control yet (wet only when the setpoint
  cannot be held).
- The coolers themselves are EnergyPlus' dry cross-flow e-NTU model; wetted-coil (spray-on-coil) hybrids are not modelled.
- Data-center study: no dataset chiller is valid above 41.1 °C leaving condenser water, so dry-mode chiller energy is
  underestimated in hot hours (reported per case as `chiller_hours_outside_curve`); the hybrid and tower plants use different
  chiller curve sets, so energy is compared only among hybrid strategies.
