# Representative water-cooled data center model (EnergyPlus 22.2)

`models/datacenter_chiller_tower.idf` is a ~1 MW-IT data center whose heat goes out through a
water-cooled chiller plant and an evaporative `CoolingTower:VariableSpeed:Merkel`. It is the
host model for the tower-water plugin (see `README.md`, `CONCEPT_NOTE.md`).

| File | Purpose |
|---|---|
| `models/datacenter_chiller_tower.idf` | Base model. Phoenix design days are already in it |
| `models/datacenter_chiller_hybrid.idf` | **Hybrid adiabatic dry-cooler variant** (§6). Phoenix design days. Runs as a plain dry-cooler plant unless a plugin/EMS pre-cools its cooler air node |
| `models/build_datacenter_idf.py` | Generator (stdlib). **The IDF is generated from this script: change the script, then regenerate.** `--heat-rejection tower` (default) or `hybrid`. Diagnostic options: `--idle-tower-test`, `--tower2-threshold`, `--timestep`, plus an experimental `--wse` |
| `models/set_design_days.py` | Makes an IDF climate-specific (design days, site, tower or hybrid-cooler design air state, condenser design temperature; `--pad-effectiveness` for hybrid models) |
| `models/summarize_dc_run.py` | Annual summary (stdlib): PUE, end uses, tower water balance or dry-cooler heat/fans, WUE, chiller loading, chiller curve-validity hours (`--idf`), temperatures, unmet hours |

## 1. How to run

```bash
E=/srv/data1/EnergyPlus-22-2-0
cd /srv/data1/liangzhang/EnergyPlus-HeatRejection-Water

# (optional) regenerate the base IDF (Phoenix design days)
python3 models/build_datacenter_idf.py

# make it climate-specific (here: Chicago)
python3 models/set_design_days.py models/datacenter_chiller_tower.idf \
    $E/WeatherData/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.ddy runs/dcdev/chi.idf

# annual run (-r makes eplusout.csv) and summary
$E/energyplus -r -d runs/dcdev/chi/out -w $E/WeatherData/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw runs/dcdev/chi.idf
python3 models/summarize_dc_run.py runs/dcdev/chi/out
```

An annual run takes about **8 s** at 6 timesteps/h (6.6 s at 4/h) on this server, single thread.

`set_design_days.py IN.idf SITE.ddy OUT.idf [--no-tower-update]` does the following:

1. It removes all `SizingPeriod:DesignDay` and `Site:Location` objects.
2. It inserts the DDY's `Site:Location` and three design days:
   - `Ann Clg .4% Condns DB=>MWB`: the 0.4 % dry-bulb day with mean coincident wet-bulb. This is what the user spec calls "DB=>MCWB"; the DDY files label it `MWB`, and the script accepts either.
   - `Ann Clg .4% Condns WB=>MDB`: the 0.4 % wet-bulb (evaporation) day.
   - `Ann Htg 99.6% Condns DB`.
3. Unless `--no-tower-update` is given, it also changes the tower sizing inputs:
   - It sets each Merkel tower's *Design Inlet Air Dry-Bulb/Wet-Bulb Temperature* to the WB=>MDB condition. The IDD minimum of 20 °C is enforced, with a warning.
   - It sets the condenser `Sizing:Plant` *Design Loop Exit Temperature* = design WB + tower design approach.

   EnergyPlus solves the Merkel design UA from these inputs, so the tower is sized on the site's extreme wet-bulb. Without this step only the zone and coil loads would change from climate to climate.

The new objects go between marker comments, so the script can be re-applied to its own output. It also works on stock IDFs: it was tested on `ExampleFiles/CoolingTower_MerkelVariableSpeed.idf`, which ran with 0 Severe errors.

## 2. Design summary

"Assumption" means a value chosen by engineering judgement, with no specific published source. Sized values are from the Phoenix run (Chicago values in brackets).

| Item | Value | Source / justification |
|---|---|---|
| **Building** | 1 storey, 2 data halls of 25 × 20 × 4.5 m (2 × 500 m²), no windows, insulated metal panel walls, insulated roof deck, adiabatic floor, no infiltration, no outdoor air | Assumption: well-sealed, internal-load-dominated white space. The envelope carries < 1 % of the cooling load |
| **IT design power** | 1000 W/m² → 500 kW per hall, **1.0 MW total** (CPU + server fans) | Assumption (≈93 W/ft², typical air-cooled enterprise/colo density) |
| ITE object | `ElectricEquipment:ITE:AirCooled`, `FlowFromSystem`, `AdjustedSupply`, class A1 | EnergyPlus I/O Reference |
| CPU utilisation schedule | Weekdays 0.75 (00–06), 0.80 (06–09), 0.90 (09–18), 0.85 (18–22), 0.78 (22–24). Weekends/holidays 0.70 / 0.80 / 0.75. **1.0 on design days**, so equipment is sized at full design IT | Assumption (mild diurnal and weekly variation, 0.70–0.90 as requested) |
| CPU power vs utilisation u | P/P_design = 0.30 + 0.70·u (idle = 30 % of peak); no inlet-temperature term | Assumption, in line with published SPECpower-type idle fractions (≈20–40 %) for modern servers |
| Resulting IT power | 0.79–0.93 of design; annual mean **861 kW**, 7,540 MWh/yr | Model output |
| Server fans | 10 % of design ITE power; airflow 7.5e-5 m³/s per W (server ΔT ≈ 11 K); airflow fraction 0.6 + 0.4·u; fan power ∝ flow³ | Assumption |
| ITE recirculation | 5 %, constant (good aisle containment). ITE inlet = 20.55 °C | Assumption |
| UPS | η = 0.95, flat over the operating range; 100 % of losses to the zone, i.e. cooled by the CHW plant | Assumption (double-conversion UPS at 50–100 % load) |
| Lighting | 5 W/m², 50 % on | Assumption |
| **Air side** | One CRAH bank (`AirLoopHVAC`) per hall: CHW coil + VAV fan, 100 % recirculation, **no airside economizer** | Spec. An airside economizer is a possible variant; it was left out so the water-cooled path carries the load |
| Supply air | 20.0 °C at the fan outlet; coil leaving air 19.5 °C (`SetpointManager:MixedAir` for fan heat) | ASHRAE TC 9.9 *Thermal Guidelines for Data Processing Environments*: recommended inlet 18–27 °C |
| Zone (hot-aisle/return) setpoint | 31 °C cooling-only thermostat (CRAH ΔT ≈ 11 K, matching server ΔT) | Assumption |
| CHW coil | `Coil:Cooling:Water`, **DetailedAnalysis, CounterFlow**, autosized at 10 °C water, 31 → 19.5 °C air, ΔT_w = 6 K. 552 kW per hall | See §5 for why not SimpleAnalysis |
| CRAH fan | `Fan:VariableVolume`, 400 Pa, η_total = 0.65, motor 0.93, min 20 % flow. 40.7 m³/s per hall | Assumption. Fan curve: EnergyPlus VAV example coefficients |
| **Chillers** | 3 × `Chiller:Electric:EIR`, water-cooled **VSD centrifugal**, curves = `ElectricEIRChiller Carrier 19XR 1407kW/6.04COP/VSD` (DataSets/Chillers.idf). Reference COP 6.04 at 6.67 °C CHW / 29.44 °C ECW; IPLV (E+ report) 6.86 | DataSets/Chillers.idf. This curve set is the only centrifugal set whose range covers both CHW 10 °C (x ≤ 10.0) and ECW up to 32.2 °C |
| Chiller sizing / redundancy | Each chiller Sizing Factor 0.5 → **552 kW each (157 tons), 2 duty + 1 standby (N+1)** | Spec |
| Chiller dispatch | `PlantLoop` *SequentialUniformPLR*: chillers start in order until capacity ≥ load, then all running units share one PLR. Result: chillers 1 and 2 run all year, chiller 3 never runs (standby) | EnergyPlus I/O Reference |
| Chiller flow mode | LeavingSetpointModulated (variable primary); setpoint on each chiller outlet | — |
| **CHW loop** | Supply 10.0 °C, design ΔT 6 K; **variable primary** `Pump:VariableSpeed`, 250 kPa, motor 0.92, part-load curve P = 0.4·Q + 0.6·Q³ (DP-setpoint control); min flow fraction 0.25 | 10 °C "warm" CHW: assumption consistent with TC 9.9 inlet envelope; pump values are assumptions |
| **Tower** | `CoolingTower:VariableSpeed:Merkel`, NominalCapacity method, **3 cells, MaximalCell**. Nominal capacity (CTI 35/29.4 °C water, 25.6 °C WB) 1.54 MW → design air 44.2 m³/s, full-speed UA 160 kW/K [140], design fan 16.1 kW | Merkel tower required by spec |
| Tower design point | Design approach **3.9 K (7 °F)**, range **5.6 K (10 °F)**, at the site **0.4 % WB=>MDB** condition: PHX 24.1 °C WB / 33.9 °C DB; CHI 25.5 / 31.2. Condenser design exit = WB + 3.9 = 28.0 [29.4] °C | Phoenix DDY: 2025 ASHRAE Handbook—Fundamentals ch. 14; Chicago DDY (EnergyPlus 22.2 WeatherData): 2009 ASHRAE Handbook |
| Tower capacity rationale | The condenser-loop design flow is the sum of the 3 chiller condenser flows. That gives 1.5 × duty flow, i.e. **one cell per chiller (N+1 cells)**. With MaximalCell all 3 cells share the duty flow (per-cell water ≈ 0.67 of cell design, above the 0.33 minimum), which lowers fan speed | Spec (N+1); E+ cell logic |
| Tower curves | Fan power 0.02 + 0.98·AFR³; UA(AFR) = 1.3·AFR − 0.3·AFR²; UA(ΔWB) = 1 + 0.0081·ΔWB; UA(WFR) = 0.1082 + 1.667·WFR − 0.7713·WFR² | `ExampleFiles/CoolingTower_MerkelVariableSpeed.idf` |
| Tower fan sizing | 0.0105 W fan per W nominal capacity (E+ default). That is ≈ 60 gpm/hp at the CTI point, better than the ASHRAE 90.1 minimum for axial-fan open towers (≈ 38–40 gpm/hp) | E+ IDD default; the gpm/hp equivalent is our own calculation |
| Minimum air flow ratio | 0.2 | E+ default (VFD turndown) |
| Evaporation | SaturatedExit | Spec (EnergyPlus default) |
| **Drift** | 0.001 % of circulating flow | Assumption, typical of modern high-efficiency drift-eliminator specifications (≈ 0.0005–0.005 %); E+ default is 0.008 % |
| **Blowdown** | ConcentrationRatio, **4 cycles** | Spec; E+ IDD gives 3–5 as typical |
| Basin heater | 0 W (water flows all year) | Assumption |
| **CW loop** | `Pump:VariableSpeed`, 200 kPa, linear part-load curve (stands for staged dedicated pumps); flow = condenser flow of the running chillers (constant per chiller) | Assumption |
| CW reset | `SetpointManager:FollowOutdoorAirTemperature`, OutdoorAirWetBulb + **3.9 K**, min **18.0 °C**, max **29.4 °C** | Spec. The 18 °C floor is an assumption for the lowest entering condenser water a centrifugal chiller accepts without head-pressure control |
| Sizing | Zone, system and plant sizing on the 3 design days; Sizing:Parameters factor 1.0 | Spec |
| Simulation | Full year, 6 timesteps/h, weather-file run period only | Spec |

### Outputs in the IDF

- **Meters** (hourly and run period): `Electricity:Facility`, `ITE-CPU`/`ITE-Fans`/`ITE-UPS:InteriorEquipment:Electricity`, `InteriorLights:Electricity`, `Cooling:Electricity`, `Chillers:Cooling:Electricity`, `HeatRejection:Electricity`, `Pumps:Electricity`, `Fans:Electricity`, `Water:Facility`, `HeatRejection:Water`, `MainsWater:Facility`.
- **Hourly variables**:
  - all tower variables;
  - ITE CPU, fan and UPS power, inlet temperature and out-of-range time;
  - zone temperature and RH;
  - CRAH fan power and flow; coil load;
  - chiller power, evaporator and condenser heat, PLR, COP, temperatures and flows;
  - pumps;
  - CHW and CW node temperatures, setpoints and flows;
  - plant unmet demand;
  - site dry-bulb, wet-bulb, humidity ratio and pressure.

PUE = `Electricity:Facility` / (`ITE-CPU` + `ITE-Fans`). UPS losses count as facility overhead, following the Green Grid convention that IT energy is measured at the UPS output.

## 3. Verification (annual, TMY3, 6 timesteps/h)

| Metric | Phoenix (PHX) | Chicago (ORD) |
|---|---|---|
| Severe / warnings | 0 / 7 | 0 / 110 |
| IT energy (CPU + server fans) | 7,539.5 MWh (861 kW mean) | 7,539.5 MWh |
| **Annual PUE** | **1.254** | **1.250** |
| Hourly PUE min–max | 1.238–1.287 | 1.235–1.294 |
| Monthly PUE (Jan → Jul) | 1.243 → 1.270 | 1.240 → 1.269 |
| Overhead as % of IT: chillers / CRAH fans / UPS / pumps / tower fans / lights | 12.7 / 3.9 / 5.0 / 2.8 / 0.71 / 0.29 | 12.5 / 3.9 / 5.0 / 2.8 / 0.56 / 0.29 |
| Chillers running (h at 0/1/2/3 units) | 0 / 0 / 8760 / 0 | 0 / 0 / 8760 / 0 |
| Chiller PLR (mean, min–max) | 0.73 (0.65–0.86) | 0.73 (0.64–0.87) |
| Chiller annual COP | 8.69 | 8.78 |
| CHW supply / return | 10.00 / 15.0–15.8 °C | 10.00 / 15.0–15.9 °C |
| CW supply (min / mean / max) | 18.0 / 20.0 / 28.7 °C | 18.0 / 19.4 / 29.4 °C |
| CW return max | 33.9 °C | 34.6 °C |
| Tower heat rejected | 9,361 MWh (peak 1,210 kW) | 9,302 MWh (peak 1,213 kW) |
| Tower Q / (IT + chiller elec.) | 1.10 | 1.10 |
| Tower fan speed ratio (min / mean / max) | 0.33 / 0.68 / 0.96 | 0.20 / 0.58 / 1.00 |
| Hours with fan speed ratio > 0.8 | 2,421 | 2,119 |
| Operating cells | 3 always | 3 always |
| **Evaporation** | **13,715 m³** | **9,500 m³** |
| Drift | 17.8 m³ | 15.0 m³ |
| Blowdown | 4,554 m³ | 3,152 m³ |
| **Make-up** (= `Water:Facility`) | **18,286 m³** | **12,666 m³** |
| Evaporation per heat rejected | 1.47 L/kWh (≈ 99 % of heat as latent) | 1.02 L/kWh |
| **WUE** (make-up / IT energy) | **2.43 L/kWh** | **1.68 L/kWh** |
| Evaporation / IT energy | 1.82 L/kWh | 1.26 L/kWh |
| Zone T / ITE inlet T | 31.0 / 20.55 °C, 0 h out of class A1 | same |
| Unmet zone-setpoint hours (tabular) | 0 | 0 |
| CHW-loop hours with unmet demand > 1 kW | 0 | 0 |
| CW-loop hours with unmet demand > 1 kW | 0 | 92 (see §5) |
| CW above setpoint + 0.5 K | 0 h | 0 h |

### Plausibility checks

- **PUE 1.25.** This is plausible for an efficient chiller plant without economizer that counts only UPS losses on the electrical side. Uptime Institute surveys report fleet-average PUE of about 1.5–1.6. Our value sits low because transformer, switchgear, generator and support-space loads are not modelled.
- **Phoenix and Chicago PUE are almost the same.** The cause is the 18 °C condenser-water floor: Chicago spends most of the year on the floor, so its chiller lift barely drops below Phoenix's. With no economizer, climate shows up mainly in water use, not in energy.
- **Tower heat balance closes.** Tower Q = IT + UPS + lights + CRAH fans + pump heat + chiller power + envelope.
  - Phoenix: 7,540 + 377 + 22 + 296 + 954 + pump heat − envelope loss ≈ 9,361 MWh.
  - Tower Q / (IT + chiller) is 1.10 because UPS losses, CRAH fan heat and pump heat also end up in the tower.
  - The chiller condenser energy equals evaporator energy + compressor power to rounding.
- **Water balance is consistent.** Blowdown / evaporation = 0.332, which is 1/(4 − 1) after subtracting drift. Drift is 0.1 % of make-up.
- **WUE 1.7–2.4 L/kWh** matches the 1–2+ L/kWh usually reported for evaporatively cooled facilities. A commonly cited US average is about 1.8 L/kWh (Shehabi et al., 2016, LBNL). Phoenix's higher value comes from its hot, dry air: SaturatedExit puts almost all heat into evaporation.
- **The towers are not wildly oversized.** At design they are deliberately N+1 (1.5 × duty water flow). Phoenix's peak-WB hour still needs fan speed 0.96. Chicago reaches 1.0 when WB = 26.7 °C, above its 25.5 °C design WB.
  - Chicago's full-speed UA is lower than Phoenix's (140 vs 160 kW/K) even though its design WB is higher. Merkel theory predicts this: at higher wet-bulb, the same 3.9 K approach needs less UA.
- **Timestep sensitivity is negligible.** At 4 timesteps/h Phoenix gives the same PUE (1.254), evaporation (13,715 m³) and WUE (2.425 L/kWh).

## 4. Tower output variables and idle-tower behaviour (E+ 22.2)

### Variables reported for `CoolingTower:VariableSpeed:Merkel`

These come from `eplusout.rdd` with basin heater = 0 and mains-water supply. All are HVAC Average unless marked Sum.

- `Cooling Tower Inlet Temperature` [C]
- `Cooling Tower Outlet Temperature` [C]
- `Cooling Tower Mass Flow Rate` [kg/s]
- `Cooling Tower Heat Transfer Rate` [W]
- `Cooling Tower Fan Electricity Rate` [W]
- `Cooling Tower Fan Electricity Energy` [J, Sum]
- **`Cooling Tower Fan Speed Ratio`** []
- `Cooling Tower Operating Cells Count` []
- `Cooling Tower Make Up Water Volume Flow Rate` [m3/s]
- `Cooling Tower Make Up Water Volume` [m3, Sum]
- `Cooling Tower Make Up Mains Water Volume` [m3, Sum]
- `Cooling Tower Water Evaporation Volume Flow Rate` [m3/s]
- `Cooling Tower Water Evaporation Volume` [m3, Sum]
- `Cooling Tower Water Drift Volume Flow Rate` [m3/s]
- `Cooling Tower Water Drift Volume` [m3, Sum]
- `Cooling Tower Water Blowdown Volume Flow Rate` [m3/s]
- `Cooling Tower Water Blowdown Volume` [m3, Sum]

### Variables that do not exist for Merkel

- `Cooling Tower Air Flow Rate Ratio` and `Cooling Tower Bypass Fraction` are reported by `CoolingTower:VariableSpeed`, not by the Merkel tower. Requesting them on a Merkel model produces the "requested but not generated" warning.
- The Merkel tower's air-flow ratio is published as **`Cooling Tower Fan Speed Ratio`**. We checked that it is the air-flow-rate ratio used in the fan curve: at timestep level, the reported fan power equals design fan power × (0.02 + 0.98·r³) × cells_on/3, with r = Fan Speed Ratio, to the watt.
- Basin heater variables appear only when the basin heater capacity is > 0. Starved/storage-tank water variables appear only with a supply tank.

**A plugin that reads "Cooling Tower Air Flow Rate Ratio" must read "Cooling Tower Fan Speed Ratio" for Merkel towers.**

### Idle-tower test

We ran this test with `build_datacenter_idf.py --idle-tower-test`, Phoenix, timestep output. It uses a second identical Merkel tower in parallel.

1. **Tower 2 never in the operation scheme.** Water still flows through it all year (8,760 h with flow), with outlet = inlet. Its evaporation, drift and blowdown are **0**, as are heat transfer, fan speed and fan power.
2. **Tower 2 switched on only above 1.12 MW, alternating with tower 1.** Each tower toggles between running and idle many times (timestep data). Results:
   - In every idle timestep (7,050 for tower 1, 22,892 for tower 2) evaporation, drift and blowdown are exactly 0.
   - There were no timesteps with flow > 0 and Q ≈ 0.
   - **We found no stale-air-flow-ratio evaporation leak for the Merkel tower in these configurations.**
3. **One stale output does exist:** `Cooling Tower Operating Cells Count` reports **1** in timesteps when the tower has zero water flow.
4. **Not exercised:** a tower with water flow but its fan off because the setpoint is satisfied, i.e. a free-convection/off state on a running loop. This model never reaches that state, because the chiller condenser always loads the tower. The reported 22.2 issue (`calculateWaterUsage` using a stale `AirFlowRateRatio`) may be specific to `CoolingTower:VariableSpeed`, or to that flow-on/fan-off state; this test cannot rule it out.

## 5. Known limitations and modelling notes

- **Warnings, all reviewed.**
  - Four sizing warnings say the heating design load is zero (expected: cooling-only data halls).
  - The Merkel warning "Iteration limit exceeded calculating air flow ratio": E+ uses the computed ratio. It occurred 1× (PHX) and 105× (CHI) out of 52,560 timesteps.
- **The Chicago CW loop has 92 h with unmet demand > 1 kW.** In these hours the tower is at full fan, CW supply is at most 0.10 K (mean 0.03 K) above setpoint and the shortfall is ≤ 23 kW. All 92 h fall at WB 12.8–15.5 °C, in spring and autumn, where Merkel physics makes the 3.9 K approach unattainable at full load (approach grows as WB falls). Using a fixed approach reset also means many cold-weather hours at high fan speed (Chicago: 2,119 h above 0.8). This is the classic tower-fan vs. chiller-lift trade-off. An optimised reset is a natural variant.
- **Coil model choice.** With `SimpleAnalysis` the CHW coil controller converged to a low-flow solution with CHW ΔT 11–13 K (return 21–23 °C, chiller evaporator flow below 40 % of design). Which solution it reached depended on the run, which suggests more than one solution. `DetailedAnalysis` + CounterFlow gives a stable ΔT of 5–6 K, consistent with the 6 K design, and closes the energy balance. It is used in the base model.
- **Chiller curve range.** The CHW leaving temperature of 10.0 °C sits exactly at the curve's upper bound (no extrapolation, but no margin). ECW 18–29.4 °C lies inside the curve's 12.8–32.2 °C range. EnergyPlus does not enforce a minimum entering condenser temperature; the 18 °C reset floor does that here.
- **Not modelled:**
  - transformer/PDU/switchgear losses, generator heaters and support spaces (PUE is optimistic by a few hundredths; assumption);
  - CRAH N+1 redundancy (one aggregate CRAH loop per hall);
  - humidity control and outdoor-air pressurisation (zone humidity stays at its initial value, e.g. about 15 % RH in Phoenix);
  - ground coupling (adiabatic floor).

  None of these affects tower water use materially.
- **Synthetic load profile.** IT utilisation is synthetic (0.70–0.90). The IT load fixes the plant size almost exactly; only envelope loads differ by climate (< 0.3 % of coil load).
- **Water-side economizer variant: not delivered.** `--wse` builds an integrated WSE: a plate HX in series on the CHW supply inlet branch, its condenser side a parallel demand branch, CoolingSetpointModulated control, UA ≈ 767 kW/K, CW floor 7 °C. It is **not usable yet**:
  - With the DetailedAnalysis coil, the mere presence of an available HX (even with zero heat transfer) drove the plant into a non-physical state in summer: coil water-side heat 835 kW vs air-side 507 kW, 3 chillers running, zones at 32.8 °C, CHW unmet.
  - With the HX's availability schedule set to off, the same model behaves exactly like the base.
  - With SimpleAnalysis coils the summer state was normal, but CHW supply drifted above 10 °C for about 2,400 h during free cooling, and the high-ΔT coil issue came back.
  - It needs a different HX control (e.g. `CoolingSetpointOnOffWithComponentOverride` with chillers), or a non-integrated arrangement, before use. No `_wse.idf` is shipped.
- **Airside economizer:** deliberately absent; it is a possible variant.

## 6. Hybrid adiabatic dry-cooler variant (`datacenter_chiller_hybrid.idf`)

```bash
python3 models/build_datacenter_idf.py --heat-rejection hybrid          # -> models/datacenter_chiller_hybrid.idf (Phoenix)
python3 models/set_design_days.py models/datacenter_chiller_hybrid.idf SITE.ddy OUT.idf [--pad-effectiveness 0.85]
$E/energyplus -r -d OUT_DIR/out -w SITE.epw OUT.idf
python3 models/summarize_dc_run.py OUT_DIR/out [--idf OUT.idf]
```

Same building, IT load, air side, CHW loop and CW pump as the tower model; only the heat rejection, the
condenser reset and the chiller curves change. The tower model and its output are untouched: regenerating
with the default `--heat-rejection tower` gives a byte-identical `datacenter_chiller_tower.idf`, and
`set_design_days.py` gives byte-identical output for tower IDFs.

**Without a plugin the model is a plain dry-cooler plant.** A plugin turns it into a hybrid adiabatic
(wetted-pad) cooler by overriding the dry-bulb and wet-bulb of the coolers' shared air node with the EMS actuators
`Outdoor Air System Node` / `Drybulb Temperature` and `Wetbulb Temperature` on `Hybrid Cooler Air Inlet`.
The condenser setpoint follows that node, so pre-cooling also lowers the chiller lift.

### 6.1 Interface (names are fixed; a plugin finds objects by them)

| Object | Name(s) |
|---|---|
| Heat rejection | `FluidCooler:TwoSpeed` `Hybrid Cooler 1`, `Hybrid Cooler 2`, `Hybrid Cooler 3`, in parallel on the CW supply side (plus a bypass branch) |
| Shared air inlet | `OutdoorAir:Node` `Hybrid Cooler Air Inlet` (in every cooler's *Outdoor Air Inlet Node Name*) |
| CW reset | `SetpointManager:FollowSystemNodeTemperature` `Hybrid Condenser Setpoint` → `CW Supply Outlet Node` |
| Chillers | `Chiller:Electric:ReformulatedEIR` `Chiller 1..3` |
| Water nodes | `Hybrid Cooler k Water Inlet` / `Hybrid Cooler k Water Outlet` |

Output variables (verified in `eplusout.rdd`, E+ 22.2). The FluidCooler uses the tower variable names:

- Per cooler (key `HYBRID COOLER k`), HVAC Average:
  - `Cooling Tower Heat Transfer Rate` [W]
  - `Cooling Tower Inlet Temperature` [C]
  - `Cooling Tower Outlet Temperature` [C]
  - `Cooling Tower Mass Flow Rate` [kg/s]
  - `Cooling Tower Fan Electricity Rate` [W]
  - `Cooling Tower Fan Electricity Energy` [J, Sum; metered as HeatRejection:Electricity]
- There is no fan-speed or air-flow output. The two-speed stage can be inferred from fan power: high = 13.09 kW, low = 2.09 kW per cooler.
- Node `HYBRID COOLER AIR INLET`:
  - `System Node Temperature`
  - `System Node Wetbulb Temperature`
  - `System Node Humidity Ratio`
  - `System Node Pressure`
  - also available: Enthalpy, Relative Humidity, Dewpoint, Current Density, Wind Speed/Direction.
- The IDF also requests the following at Timestep **and** Hourly:
  - the cooler and node variables above;
  - `CW Supply Outlet Node` temperature, setpoint and flow, and the `CW Supply Inlet Node` temperature;
  - site outdoor DB/WB/humidity ratio/pressure;
  - chiller power, PLR, evaporator outlet and condenser inlet/outlet temperatures.
- The tower water meters are not requested: there is no EnergyPlus water use.

Checked behaviour of the node and actuators (EMS test, §6.4):

- The cooler reads `Node.Temp`, `HumRat`, `Press` and `OutAirWetBulb` of the node every HVAC step.
- The overridden dry-bulb reaches the node exactly (max error 0.0 K over 52,560 timesteps).
- The setpoint manager follows it in the **same** timestep (max |SP − clip(node DB + 5.6)| = 0.0 K).
- The node humidity ratio is recomputed from the overridden DB/WB (+3.9 g/kg mean in Phoenix).
- The reported node wet-bulb equals the overridden WB to within 0.5 K (mean 0.003 K).
- The EnergyPlus FluidCooler model is **dry**: its heat transfer depends only on the air dry-bulb. Its design wet-bulb input is used only for an input check (it must be < design air temperature) and for air density.

### 6.2 Design basis

"Assumption" means a value chosen by engineering judgement. Values below are per cooler unless stated.

| Item | Value | Source / justification |
|---|---|---|
| Number of coolers | **N = 3**, each 50 % of the design heat rejection → 2 duty + 1 standby (N+1), one per chiller | Spec (N+1 consistent with 3 × 50 % chillers) |
| Cooler operation | CondenserLoop *UniformLoad*: all three coolers run and share the flow (each 2/3 of design with 2 chillers on) | Assumption: N+1 EC-fan banks normally run all units at reduced speed. With *SequentialLoad*, E+ fills coolers 1–2 to design flow and leaves cooler 3 dry except when the setpoint cannot be met. In Phoenix (dry) *UniformLoad* cut cooler fan energy from 187 to 137 MWh and CW-unmet hours from 1,587 to 1,029; chiller energy was unchanged |
| Model / method | `FluidCooler:TwoSpeed`, *NominalCapacity* | Spec |
| Nominal capacity | **654.6 kW** = 552 kW × (1 + 1/5.38) (chiller reference capacity × condenser-heat factor at reference COP) | Derived. Hard value: not autosizable with NominalCapacity in E+ 22.2 |
| Design water flow | **0.02797 m³/s** = Q/(ρ c_p 5.6 K), with ρ = 999.9 and c_p = 4180. The chiller *Reference Condenser Water Flow Rate* is hard-sized to the same value. Loop 0.0839 m³/s | Derived; range 5.6 K (10 °F) as the tower model. Not autosized: E+ would give every cooler the *whole* loop flow |
| Design approach | **5.6 K (10 °F)** (leaving water − entering air) | Assumption: typical selection for adiabatic/dry coolers (≈ 4–8 K). It keeps the setpoint offset equal to the sizing approach |
| Design air state (wet design) | T_air = DB − 0.85 (DB − MWB) and WB = MWB, at the site **0.4 % DB=>MWB** condition. EWT = T_air + 5.6 + 5.6 | Spec. Pad effectiveness 0.85 is the spec default (`--pad-effectiveness`) |
| — Phoenix (0.4 %: 44.0 / 20.8 °C) | T_air 24.28 °C, WB 20.80, EWT 35.48, condenser design exit 29.88 °C | 2025 ASHRAE HoF via DDY |
| — Stockholm (27.3 / 18.0) | 19.39 / 18.00 / 30.59 / 24.99 °C | TMYx DDY |
| — Singapore (33.4 / 26.1) | 27.20 / 26.10 / 38.40 / 32.80 °C | TMYx DDY |
| High-speed air flow | **Q/(ρ_air c_p,air × 8 K)** at the design air state and site pressure: PHX ≈ 71.2, STO ≈ 67.6, SIN ≈ 69.0 m³/s (the 10 K values 56.93/54.09/55.19 × 10/8) | Assumption: **8 K** design air temperature rise (`HYB_AIR_DT`). Changed from 10 K after the 14-climate study: with 10 K the low-speed UA could not be sized at sites above ~600 m (Madrid, Las Vegas, Riyadh). Hard-sized because E+ 22.2 autosizes it as Q/(EWT−EAT)·4 (FluidCoolers.cc l.1045), about three orders of magnitude too large |
| High-speed fan power | **13.09 kW** = 0.02 W/W × Q (≈ 230 W per m³/s, i.e. ≈ 115 Pa at 50 % fan efficiency) | Assumption, typical EC-fan dry coolers. E+ would autosize 0.0105 W/W (a tower value) |
| Low speed | Air 0.5 × high (28.47 m³/s PHX). Fan 0.16 × high = 2.09 kW. Low-speed nominal capacity **357.5 kW (0.546 Q)**, chosen so that E+ sizes UA_low = **0.6 × UA_high** | E+ default ratios for air flow and fan. UA_low/UA_high = 0.6 ≈ 0.5^0.7 is an assumption (air-side-dominated UA). The E+ default capacity factor 0.5 gave UA_low/UA_high = 0.29. All hard values: E+ 22.2 cannot combine a hard low-speed capacity with an autocalculated low-speed air flow |
| Sized UA (E+, `eplusout.eio`) | UA_high **342.5 kW/K** (replica in `set_design_days.py`: 342.2, within 0.1 %), UA_low **205.7 kW/K** | E+ output |
| Plausibility of UA | Design C_air = 65.3 kW/K, C_water = 116.9 kW/K, C_r = 0.56, required ε = 10/11.2 = 0.89. **NTU = 5.2** in E+'s cross-flow ε-NTU form. A pure counterflow exchanger would need NTU ≈ 3.3 (LMTD 2.9 K, with a temperature cross: air leaves at T_air + 10 > water out at T_air + 5.6) | Our calculation for the original 10 K design. **The delivered model uses an 8 K air rise, NTU ≈ 2.3** (`HYB_AIR_DT`); the verification table below was produced with 10 K and should be re-run before quoting it. |
| CW reset | `SetpointManager:FollowSystemNodeTemperature`, NodeDryBulb of `Hybrid Cooler Air Inlet` + **5.6 K**, min **23.0 °C**, max **40.0 °C** | Offset = design approach (spec). The minimum of 23 °C (not 20) keeps the chiller's leaving condenser water ≥ the curve minimum of 26.77 °C at the normal 2-chiller PLR (≈ 0.6–0.9; condenser rise ≥ 4.3 K, Stockholm minimum). The maximum of 40 °C is an assumption (ECW limit of a high-lift centrifugal); above DB ≈ 34.4 °C the coolers simply run at full fan |
| Chillers | 3 × `Chiller:Electric:ReformulatedEIR`, curves **`ReformEIRChiller Trane CVHE 1329kW/5.38COP/Vanes`** (centrifugal, inlet vanes). Reference COP **5.38** at 6.11 °C CHW / 34.80 °C leaving condenser. E+ IPLV report 5.32. PLR 0.29–1.02 | DataSets/Chillers.idf. Searched all EIR and ReformulatedEIR sets: no set covers ECW ≥ 45 °C. This is the only set with leaving-condenser limit > 37 °C that also covers 10 °C CHW |
| Curve validity | Intersection of CAPFT, EIRFT and EIRFPLR: **CHW leaving 6.11–10.00 °C, leaving condenser 26.77–41.11 °C, PLR 0.29–1.02**. EnergyPlus clamps each curve input to these limits (no extrapolation) and warns. Hours outside are counted by `summarize_dc_run.py` | The dataset has no curve set with ECW limit > 35 °C (EIR) or LCW limit > 42.3 °C (ReformEIR) |
| Chiller capacity | Reference capacity **hard-sized 552 kW** (the base model's autosized value; 549.6–551.9 kW at the 14 sites). At 10 °C CHW the capacity is 552 × CAPFT = 580–675 kW | E+ autosizes ReformEIR reference capacity as design load / CAPFT(design) = 482 kW. Because *SequentialUniformPLR* stages on reference capacity, 2 × 482 kW < peak load started the standby chiller for ≈ 2,500 h/yr. With 552 kW the staging is the same as the base model (2 duty, 1 standby) |
| CHW 10.0 °C | At the curve's upper limit. E+ warns "evaporator outlet temperature (10.00 C) is outside the range … 6.11 C to 10.00 C" when the outlet is a round-off above 10.00; summary counts 0 h outside (0.01 K tolerance) | — |
| Low ambient / freeze | The dry cooler has no free-convection capacity in E+ (fan off ⇒ Q = 0). At low ambient it cycles its low-speed fan to hold the 23 °C minimum; loop water never falls below 23 °C. Water (no glycol) is modelled; real dry coolers in freezing climates need glycol or drain-down (not modelled; it does not affect energy here). No water-side economizer | Spec |

### 6.3 Verification: dry baseline (no plugin), annual, 6 timesteps/h, TMYx weather and DDY

| Metric | Phoenix (dry) | Stockholm (dry) | Singapore (dry) |
|---|---|---|---|
| Severe / warnings | 0 / 206,142 | 0 / 715 | 0 / 57,928 |
| Warning types | 4 zero-heating-load sizing notes; CHW 10.00 round-off at curve limit; **leaving condenser > 41.11 °C curve limit** (almost all) | as PHX, minus the condenser one; 1 transient `PsyTwbFnTdbWPb` input −126 °C (once, 03/24) | as PHX |
| **PUE** | **1.343** (hourly 1.309–1.397) | **1.313** | **1.347** |
| Chiller energy | 1,539.0 MWh | 1,412.7 MWh | 1,588.1 MWh |
| Chiller plant annual COP | 5.39 | 5.82 | 5.22 |
| Chillers running (h at 0/1/2/3) | 0/0/8760/0 | 0/0/8760/0 | 0/0/8760/0 |
| Cooler fan energy (3 coolers) | 136.7 MWh (1.37 % of Q) | 45.1 MWh (0.46 %) | 126.3 MWh (1.26 %) |
| Hours at full high-speed fan (per cooler) | 943 | 0 | 0 |
| Heat rejected | 9,958 MWh (= 1.097 × (IT + chiller)) | 9,765 MWh | 9,998 MWh |
| CW supply min/mean/max | 23.0 / 31.3 / **48.5 °C** | 23.0 / 23.3 / 34.5 °C | 28.6 / 33.6 / 39.4 °C |
| CW setpoint min/mean/max | 23.0 / 31.0 / 40.0 °C | 23.0 / 23.3 / 34.5 °C | 28.6 / 33.6 / 39.4 °C |
| Hours setpoint at min / pinned at max | 2,249 / 1,610 | 7,644 / 1 | 2 / 1 |
| CW supply > setpoint + 0.5 K / + 2 K (timestep) | **855 h / 552 h** (max 8.75 K) | 0 / 0 | 0 / 0 |
| CW-loop hours with unmet demand > 1 kW | 1,029 | 0 | 0 |
| **Chiller hours outside curve limits** (any running chiller, timestep data) | **2,803 h**, all leaving condenser > 41.11 °C; max 53.9 °C (12.8 K above) | **0 h** (max 40.0 °C) | **1,208 h**, all leaving condenser > 41.11 °C; max 44.8 °C (3.7 K above) |
| Leaving condenser < 26.77 °C / CHW or PLR out of range | 0 / 0 | 0 / 0 | 0 / 0 |
| CHW supply | 10.00 °C always; CHW unmet 0 h | same | same |
| Unmet zone hours (table) / ITE out of class A1 | 0 / 0 | 0 / 0 | 0 / 0 |

Notes:

- **Chiller energy in hot dry hours is underestimated.** EnergyPlus holds the curves at their 41.11 °C limit, so the 2,803 Phoenix hours (and 1,208 Singapore hours) above the limit are computed at limit performance. In the dry Phoenix case the plant also cannot hold its setpoint for 855 h, because the dry coolers are sized for pad-cooled air.
- **The PUE difference from the tower model (≈ 1.25) is mostly chiller technology.** This curve set (inlet-vane centrifugal, COP_ref 5.38) is much less efficient than the VSD Carrier 19XR curves of the tower model (annual COP 8.6–8.8). A like-for-like water vs. energy comparison should keep that in mind, or use one chiller curve set for both plants.
- Cooler 3 shares the flow (all three identical, UniformLoad).

### 6.4 EMS coupling test (scratch copy, not in the delivered IDF)

`runs/hybdev/ems_precool.idf` is appended to the Phoenix model in `runs/hybdev/phoenix_ems/`. At
`BeginTimestepBeforePredictor` it sets the `Hybrid Cooler Air Inlet` dry-bulb to DB − 0.85 (DB − WB) and its wet-bulb to WB:

| Phoenix, annual | Dry (no plugin) | EMS wet (ε = 0.85, always on) | Change |
|---|---|---|---|
| Cooler inlet air node DB mean / max | 24.6 / 45.6 °C | 15.2 / 32.6 °C | −9.35 K mean |
| CW setpoint mean / max | 31.0 / 40.0 °C | 24.8 / 38.2 °C | −6.2 K mean |
| CW supply mean / max | 31.3 / 48.5 °C | 24.8 / 38.2 °C | — |
| Hours CW > setpoint + 0.5 K | 855 | 0 | — |
| Cooler fan energy | 136.7 MWh | 73.9 MWh | −46 % |
| Chiller energy / plant COP | 1,539.0 MWh / 5.39 | 1,439.9 MWh / 5.76 | −6.4 % |
| Chiller hours outside curve limits | 2,803 | 3.2 (max LCW 43.0 °C) | — |
| PUE | 1.343 | 1.322 | −0.021 |
| Severe / warnings | 0 / 206,142 | 0 / 728 | — |

The EMS run wets the pads all year, including cold hours where the node goes down to −2.6 °C. The
setpoint is then at its 23 °C floor for 5,216 h, so only fan energy, not chiller energy, benefits in those
hours. A real controller (the plugin) would wet only above a threshold.
