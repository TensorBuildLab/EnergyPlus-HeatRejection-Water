# EnergyPlus cooling tower water-accounting issues (v22.2; same code on `develop`, Oct 2026)

Draft material for upstream issues on NatLabRockies/EnergyPlus. Confirm on the latest release (26.2.0) before filing.

## 1. Idle towers report evaporation, drift, blowdown and makeup

**Where:** `src/EnergyPlus/CondenserLoopTowers.cc`, `CoolingTower::simulate()` calls
`calculateWaterUsage()` and then `report(RunFlag)`. When `RunFlag` is false, `report()` zeroes `Qactual`,
`AirFlowRatio`, `NumCellOn` and fan energy, but the water rates were already computed with the
`airFlowRateRatio` left over from an earlier call. `WaterUsage`, `EvaporationVdot`, `DriftVdot` and `BlowdownVdot`
are not reset.

**Reproduce:** `python bugreports/check_eplus_water_accounting.py` (stock `CoolingTower_VariableSpeed.idf`,
Golden CO TMY3, annual):

| tower | heat rejected | evaporation | evaporation with Q = 0 | timesteps with Q = 0 and E > 0 |
|---|---|---|---|---|
| CENTRAL TOWER | > 0 | 10.79 m³ | 0 | 0 |
| CENTRAL TOWER 2 | 0 | 8.65 m³ | **8.65 m³** | **2,823** |

**Suggested fix:** in `report()` when `!RunFlag`, also zero `EvaporationVdot`, `DriftVdot`, `BlowdownVdot`,
`MakeUpVdot`, `WaterUsage` and their volume counterparts (or reset `airFlowRateRatio` at the start of each calc routine).

## 2. Merkel tower: no evaporation in free convection

**Where:** `calculateMerkelVariableSpeedTower()`, free-convection branch: `airFlowRateRatio = 0.0; Qactual = FreeConvQdot;`.
`calculateWaterUsage()` then computes the air mass flow as `airFlowRateRatio * HighSpeedAirFlowRate * ...` = 0, so
`SaturatedExit` evaporation is zero while heat is rejected by evaporative free convection.

**Reproduce:** run any model whose Merkel tower reaches free convection and count timesteps with
`Cooling Tower Heat Transfer Rate > 0`, `Cooling Tower Fan Electricity Rate = 0` and
`Cooling Tower Water Evaporation Volume Flow Rate = 0` (last column of `check_eplus_water_accounting.py`).
Result for the data-center model: see `results/` (to be added).

**Suggested fix:** use `FreeConvAirFlowRate` as the air flow in `calculateWaterUsage()` when in the free-convection regime.

## 3. VariableSpeed (YorkCalc/CoolTools) tower: capacity fraction used as an air-flow ratio

In fan-off and fan-cycling operation `airFlowRateRatio` is set to the free-convection *capacity* fraction (or a
blend with the minimum air-flow ratio), and `calculateWaterUsage()` treats it as an air-flow ratio. The free-convection
air flow reported in sizing (`Air Flow Rate in free convection regime`) differs from it (0.2 vs 0.125 of design in
the stock example). Evaporation is therefore computed with an air flow that is not the modelled one.

## 4. `LossFactor` evaporation is 100× the documented rate

**Where:** `GetTowerInput()` reads `tower.UserEvapLossFactor = NumArray(...)` with no `/100`, while the IDD documents
the field in **percent/K** (default 0.2, "typical values 0.15 to 0.27"). `calculateWaterUsage()` then uses
`EvapVdot = UserEvapLossFactor * (Tin - Tout) * mdot / rho`. Drift percent, read the same way, *is* divided by 100.
Same in all four tower types (lines ~422, 758, 1382, 1635 of v22.2.0) and on `develop`.

**Reproduce:** stock `CoolingTower_VariableSpeed.idf`, both towers switched to `LossFactor` with factor 0.2, Chicago TMY3:
implied factor E / (range × flow) = **0.2001 per K = 20 %/K**; evaporation reaches **24 % of the circulating flow**.
Users report entering 0.0015–0.0027 as a workaround (unmethours.com).

**Suggested fix:** divide by 100 on input (and add a transition rule if existing files rely on the workaround).

## 5. Fluid-cooler air flow autosizing is ~1000× too large

**Where:** `FluidCoolers.cc` (v22.2.0, line ~1045), `FluidCoolerspecs::size()`:
`tmpHighSpeedAirFlowRate = FluidCoolerNominalCapacity / (DesignEnteringWaterTemp - DesignEnteringAirTemp) * 4.0;`
Capacity is in W and the result is used as m³/s.

**Reproduce:** stock `ExampleFiles/FluidCoolerTwoSpeed.idf` (58,601 W nominal, 51.67 °C water / 35 °C air) →
`.eio`: `Air Flow Rate at High Fan Speed [m3/s], 14061.43` (≈17,000 kg/s of air for 58.6 kW).
A physical value at a 10 K air temperature rise is ≈ 4.9 m³/s.

**Impact:** UA is then sized against this air flow, so heat rejection is self-consistent, but the air side (any model that needs
air mass flow, such as adiabatic pre-cooling water) is unphysical. Check whether the constant was meant for kW
(58.6 / 16.67 × 4 = 14.1 m³/s, still about 3× a typical dry-cooler air flow).
