# Concept Note: Physics-Based Water Consumption for Heat Rejection in EnergyPlus

*Preliminary Study 2 for the NSF CAREER proposal "Environmentally Adaptive Heat Rejection for Data Centers"*
*Author: Liang Zhang (University of Arizona) · Drafted 2026-10-31*

---

## 1. Purpose

Build accurate, physics-based models of the water a heat-rejection plant consumes and add them to EnergyPlus, validated across climate zones.

This is **foundation work**: it builds a tool and evidence the CAREER proposal will use. It does **not** answer the proposal's research questions in advance (environmental cost framework, adaptive design and control).

## 2. Why it matters

- Data centers turn nearly all their electricity into heat, and that heat must be rejected to the environment through evaporated water, warmed air, or both.
- How much water this takes depends on three things that vary by place:
  1. the **outdoor air state** (dry-bulb, wet-bulb, humidity);
  2. **water quality** (hardness, silica, alkalinity), which limits how many times water can be reused;
  3. the **equipment and controls**, such as tower, closed-circuit cooler, hybrid dry cooler, and the wet/dry switching logic.
- EnergyPlus is the main open building-energy engine used worldwide, but it represents all three in simplified form. Water estimates for data centers, and for any building with cooling towers, are therefore uncertain, especially in climates far from design conditions.

## 3. Gap check: EnergyPlus 26.2.0 (latest release, 2026-09-30)

Checked against the v26.2.0 input data dictionary (`idd/Energy+.idd.in`, NatLabRockies/EnergyPlus) and GitHub issues and PRs on 2026-10-31.

| Gap | Status in 26.2.0 | Planned work found? | Decision |
|---|---|---|---|
| **Evaporation physics** (CoolingTower:SingleSpeed/TwoSpeed/VariableSpeed/VariableSpeed:Merkel, EvaporativeFluidCooler:SingleSpeed/TwoSpeed) | Only `SaturatedExit` (default) or `LossFactor` (0.15–0.27 %/K), both Merkel-type simplifications | None | **In scope** |
| **Blowdown** | Only fixed `ConcentrationRatio` or `ScheduledRate`. The IDD has no water-quality terms (silica, hardness, cycles of concentration) | None | **In scope** |
| **Hybrid / adiabatic dry coolers** on water loops | `FluidCooler:*` is fully dry, with no water fields. Wet pre-cooling exists only for DX coils (`Coil:Cooling:DX:VariableSpeed`) and evaporatively cooled condensers | None | **In scope (lead item)** |
| **Liquid-cooled IT equipment** | Not in the release | **Yes:** issue #11408 (2026-01) and LBNL PR #11667 `ElectricEquipment:ITE:LiquidCooled` (open, updated 2026-10-26), with cold-plate coils under separate PNNL/NLR efforts | **Out of scope.** Connect to it when merged |

The search covered GitHub only. Before starting, confirm with the EnergyPlus team or the PR #11667 authors that nobody is working on items 1–3 elsewhere.

## 4. Scope

### 4.1 Hybrid / adiabatic dry cooler model (lead)
- Dry coil with wet pre-cooling by pad or spray, with pad or spray effectiveness, wet/dry switching thresholds, and partial-wet operation.
- Outputs: heat rejected, fan power, water evaporated, pad bleed or overspray, and the hours spent in each mode.
- This is the most common water-saving design in new data centers, and EnergyPlus cannot model it today.

### 4.2 Blowdown driven by water chemistry
- Cycles of concentration set by the limiting constituent (silica, calcium hardness, alkalinity, chloride) and the treatment level, instead of a fixed number.
- Water-source profiles for typical regions: surface, groundwater, reclaimed, and desalinated.
- Outputs: blowdown, makeup water, and the share of water that goes to blowdown.

### 4.3 Evaporation physics
- A Poppe-type heat and mass transfer model that accounts for exhaust air that isn't saturated and for the water lost to evaporation.
- Compared against `SaturatedExit` and `LossFactor` across climates, to measure the error of the current methods in each climate.

### 4.4 Out of scope (left for the CAREER proposal)
- A combined environmental-cost framework (on-site water, grid water and carbon, local heat).
- Optimal equipment sizing and adaptive wet/dry/storage/defer control.
- Future-climate analysis.
- Liquid-cooled IT models, which belong to the national-lab effort above.

## 5. Climate coverage

The physics is universal. The study tests the models in climates that stress each part differently:

| Climate type | Example locations | What it tests |
|---|---|---|
| Hot-dry | Phoenix, Riyadh, Madrid | Large evaporation-model error; many wet hours for hybrid coolers |
| Hot-humid | Singapore, Houston, Mumbai | Small evaporation potential; tower behavior near saturation |
| Mixed / temperate | Northern Virginia, Dublin, Frankfurt | The largest data center markets; frequent wet/dry switching |
| Cold | Stockholm, Montreal | Mostly dry operation; winter fog and freezing limits |

Weather comes from TMY and actual-year EPW files for each site, organized by ASHRAE climate zone.

## 6. Validation plan

- **Manufacturer performance data** for towers, closed-circuit coolers and hybrid dry coolers, across a range of ambient conditions.
- **Published measurements** from several climates (to be compiled), including hourly Phoenix results (Karimi et al., 2025) as one hot-dry case.
- **Metered plant data**, if available: makeup water and blowdown meters from a campus central plant or data center. Ask facilities.
- **Code checks:** energy and mass balance closure, limiting cases (fully dry, fully wet), and agreement with the existing objects where the assumptions match.

## 7. Implementation path

1. **Prototype** with the EnergyPlus Python Plugin / EMS interface, which is fast to iterate on and works with released EnergyPlus.
2. **Standalone verification** in Python against the validation data.
3. **Contribution:** a New Feature Proposal and pull request to NatLabRockies/EnergyPlus once the models are stable. Upstream merge is not on the critical path.

## 8. Link to Study 1 and the CAREER proposal

| | Study 1 (done) | Study 2 (this note) |
|---|---|---|
| Repository | [TensorBuildLab/data-center-heat-rejection](https://github.com/TensorBuildLab/data-center-heat-rejection) | To be created |
| What it covers | Heat and humidity released to the neighborhood (validated plume model) | Water consumed by the heat-rejection plant |
| Shared physics | Cooling-tower exhaust state (`cooling_tower_source`) | Same energy and mass balance, so heat, water and power come from one consistent model |
| CAREER thrust supported | Thrust 1 (heat-rejection physics) and the local-heat part of Thrust 2 | Thrust 1 (heat-rejection physics) and the water part of Thrust 2 |

Proposal claim these studies support: *"I have built and validated the models for each way of rejecting heat (heat to air, water consumption). The CAREER will develop the framework for environmental cost and the adaptive designs."*

## 9. Open questions

1. Can metered makeup and blowdown data be obtained from a campus plant or a data center?
2. Is anyone at NLR, PNNL or LBNL modeling hybrid dry coolers or water chemistry? Would they provide a letter of support?
3. Which hybrid cooler designs to model first: pad, spray, or both?
4. Target journal and timing: *Energy and Buildings*, *Applied Thermal Engineering*, or *Journal of Building Performance Simulation*.

## 10. Next steps (not started)

- [ ] Confirm the gaps with the EnergyPlus team or the PR #11667 authors
- [ ] Compile validation sources for each climate type
- [ ] Ask facilities about metered cooling-tower water data
- [ ] Define the model equations for 4.1–4.3 (technical reference, as in Study 1)
- [ ] Set up the repo and Python plugin prototype
