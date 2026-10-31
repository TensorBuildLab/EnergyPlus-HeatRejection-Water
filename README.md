# tower_water: multi-method cooling tower water consumption for EnergyPlus

An EnergyPlus Python Plugin and standalone library that compute cooling tower water use with
**eight evaporation methods**, from rules of thumb to the full **Poppe** heat and mass transfer model.
They are evaluated on the same simulated operating point every timestep, together with **blowdown driven by
makeup-water chemistry**. Research context: `CONCEPT_NOTE.md` (Study 2 for the NSF CAREER proposal).

| Where | What |
|---|---|
| `docs/METHODS.md` | **Technical reference**: every equation, assumption, source, and verification |
| `docs/REFERENCES_CHECK.md` | Check of every reference and technical claim against publisher records |
| `docs/HYBRID_DRY_COOLER.md` | User guide for the hybrid adiabatic dry cooler model |
| `docs/PROJECT_LOG.md` | Record of decisions, findings and open items |
| `results/archive/` | Compact archive of every simulation run (models, configs, logs, timestep/hourly series); `tools/archive_runs.py` |
| `paper/manuscript.tex`, `paper/references.bib` | Journal manuscript v2 (Elsevier `elsarticle`), revised after review round 1 |
| `paper/REVIEW_round1.md`, `paper/RESPONSE_round1.md` | Referee-style review and point-by-point response |
| `paper/hybrid/manuscript_hybrid.tex` | Companion draft: hybrid dry cooler study (split off in review round 1) |
| `paper/manuscript.docx`, `docs/METHODS.docx` | Word versions (native editable equations; regenerate with `tools/make_docx.py`) |
| `results/figures/`, `results/study/` | Paper figures (PNG + PDF) and tables |
| `models/` | Representative 1 MW water-cooled data center (`DATACENTER_MODEL.md`) and stock examples |
| `bugreports/` | Four EnergyPlus water-accounting defects with reproductions |
| `reproduce.sh` | Regenerates every number and figure |

## Methods

| ID | Method | Reference |
|---|---|---|
| `LAT` | Latent-only, Q/h_fg | screening practice |
| `ROT` | Rule of thumb, 0.00085 × flow × range(°F) | Perry's handbook §12 |
| `LF` | EnergyPlus LossFactor as documented (%/K) | EnergyPlus I/O Ref. |
| `EPSAT` | EnergyPlus SaturatedExit, line-by-line replica | EnergyPlus source |
| `MSAT` | Merkel energy balance, saturated exit | Merkel 1925 |
| `BRAUN` | Effectiveness-NTU with unsaturated exit humidity | Braun, Klein & Mitchell 1989 |
| `POPPE` | Poppe, Bošnjaković Lewis factor, supersaturated air (**reference**) | Poppe & Rögener 1991; Kloppers & Kröger 2005 |
| `POPPE1` | Poppe with Le_f = 1 | same |

Blowdown chemistry modes: `fixed` (EnergyPlus), `constituent` (silica, hardness, chloride, TDS limits), and `dynamic`
(adds the Langelier-index limit at hot-water temperature and amorphous-silica solubility at cold-water temperature,
each timestep). Standalone **rating mode** solves cold-water temperature for a given fill (Merkel, Poppe, e-NTU),
for validation against manufacturer data.

**Hybrid adiabatic dry cooler** (`hybrid.py`, `eplus_hybrid.py`, `tools/prepare_hybrid.py`): wetted-pad pre-cooling imposed on
a `FluidCooler:TwoSpeed` bank through EMS outdoor-air-node actuators (changes the EnergyPlus solution), pad water from the
coolers' actual air flow, media or spray water systems, and dry / always-wet / switch-over-temperature control.

Supported towers: `CoolingTower:VariableSpeed:Merkel` (recommended, physically meaningful air flow) and
`CoolingTower:VariableSpeed`. EnergyPlus 22.2. The core is standard-library Python 3.8+.

## Use

```bash
PY=/srv/data1/liangzhang/envs/towerwater/bin/python      # numpy, scipy, pandas, matplotlib, psychrolib
E=/srv/data1/EnergyPlus-22-2-0

# add the plugin to any model (sizing run, config, IDF objects); --ddy makes sizing climate-specific
$PY tools/prepare_model.py --idf models/datacenter_chiller_tower.idf --epw weather/dublin/*.epw \
    --ddy weather/dublin/*.ddy --out runs/dublin [--methods POPPE,EPSAT,...] [--coc-mode dynamic] \
    [--source example_reclaimed] [--loss-factor 0.2]
$E/energyplus -r -d runs/dublin/out -w weather/dublin/*.epw runs/dublin/model.idf
$PY tools/analyze.py runs/dublin          # every method vs EnergyPlus
$PY tools/scenarios.py runs/dublin        # makeup for every method x water source x chemistry mode (offline)

# whole study
./reproduce.sh
```

Per-tower outputs (`<Prefix>_<Name>:PythonPlugin:OutputVariable`): `E_<method>` (m³/s) for every method; for the
reference method `Drift`, `Blowdown`, `Makeup`, `MakeupVol`, `Cycles`, `CycLimit`, `AirMass`, `AirOutT`, `AirOutW`,
`Fog`, `MePoppe`, `MeMerkel`, `NTU`, `AirScale`, `Status` (0 ok, 1 idle, 2 no air, 3 infeasible, 4 clipped, 5 air adjusted).

## Verification (details in `docs/METHODS.md` §7)

- 38 unit tests, including psychrometrics against PsychroLib (ASHRAE).
- Poppe vs an independent height-wise boundary-value solution (SciPy): < 1e-4 %.
- Rating mode: Merkel, Poppe and e-NTU agree within 0.5 K for the same fill.
- The EnergyPlus SaturatedExit replica matches EnergyPlus within 0.2 % at all 14 sites.

## Main results (1 MW data center, 14 climates, TMYx 2011–2025)

- EnergyPlus default (SaturatedExit) gives **3.7–9.3 % less annual evaporation than Poppe** (3.5–7.6 % excluding liquid mist);
  robust to plant variants (≤ 1.2 points) and to EnergyPlus' thermal operating point (≤ 0.15 %, fixed-fill check). Model-to-model, not measured.
- EnergyPlus LossFactor (as documented, 0.2 %/K) overestimates by 4–64 %; rule of thumb −20 to +26 %; latent-only −11 to +40 %.
- Evaporation 1.05–1.65 L/kWh of heat rejected; WUE 1.66–2.63 L/kWh IT.
- Makeup-water chemistry changes makeup by −13 to +22 %, as much as the choice of evaporation physics.
- Fixed tower at full load over all ambient conditions: saturated exit −18 to +11 %, empirical methods −39 to +117 %.
- **Hybrid dry cooler** (3 × 50 % fluid coolers, 7 control strategies): wetting above 28 °C keeps chillers within their rated
  range at all sites (dry-only: up to 3,285 h/yr outside) and uses 14–100 % less water than the tower; always-wet in Riyadh uses
  9 % *more* than the tower; electricity saved by wetting costs 100–240 L of water per kWh.
- **EnergyPlus defects:** fluid-cooler air flow autosized about three orders of magnitude too large; idle towers book water; Merkel free convection books none; capacity fraction used as air-flow
  ratio; **LossFactor applied 100× too high** (percent input used as a fraction).

## Before publishing

- Replace the placeholder water sources and treatment limits in `data/water_sources.json` with utility reports and vendor
  limits; confirm the source of the empirical LSI constants (`docs/REFERENCES_CHECK.md`).
- Validate against manufacturer performance tables and metered makeup and blowdown (concept note §6).
- Confirm the four EnergyPlus defects on v26.2 and file them upstream (`bugreports/README.md`).
- In the manuscript, resolve the three `\tbd{}` items (affiliation, Kloppers & Kröger claim, repository URL). Compile with
  pdflatex/bibtex or Overleaf (no LaTeX on this server).

## Next steps

- Full Poppe tower as a `PlantComponent:UserDefined` (the rating functions are ready); hybrid and adiabatic dry coolers
  (concept note 4.1); SingleSpeed and TwoSpeed towers and evaporative fluid coolers; water-side economizer variant of the
  data-center model; uncertainty analysis of the chemistry inputs.
