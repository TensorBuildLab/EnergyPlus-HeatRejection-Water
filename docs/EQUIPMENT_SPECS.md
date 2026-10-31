# Equipment specifications vs. model assumptions

This note checks the assumptions in `models/DATACENTER_MODEL.md` §2 (tower model) and §6.2 (hybrid dry-cooler model) against published data for equipment widely used in water-cooled data centers. The sources are manufacturer catalogs, O&M manuals, specifications and selection printouts, codes, DOE/ASHRAE guidance and peer-reviewed or thesis data. It closes with a ranked recommendation table (§6) of EnergyPlus inputs.

Data extracted for this note is in `data/equipment/` (§7). One file holds 126 **measured** counterflow fill-test points (Kloppers 2003). We used them to check `src/tower_water/evaporation.py` (§5).

Confidence levels:

- **H**: read in the primary document.
- **M**: good secondary source, or read from a chart.
- **L**: snippet or recollection; verify before citing.

Page numbers are the printed page numbers. Sources were accessed in October 2026.

---

## 1. Open cooling towers

### 1.1 Product data

| Item | BAC Series 3000 (crossflow) | SPX Marley NC (crossflow) | EVAPCO AT/UT/USS (counterflow) | Conf. |
|---|---|---|---|---|
| Source | Series 3000 handbook Vol. V, pp. B23–B32, <https://baltimoreaircoil.com/download_api_endpoint/536/b8_ct_s3000_20150914.pdf>. Spec <https://baltimoreaircoil.com/download_api_endpoint/7064/S3E_spec_20261019.rtf>. O&M RGOM300E01 R6.0 <https://baltimoreaircoil.com/download_api_endpoint/5765/RGOM300E01_R6.0_20230314_0.pdf> | TECH-NC-26 <https://spxcooling.com/wp-content/uploads/TECH-NC-26.pdf>. SPEC-NC-26 <https://spxcooling.com/wp-content/uploads/SPEC-NC-26.pdf>. User manual Z0628276_G <https://spxcooling.com/wp-content/uploads/Z0628276_G-1.pdf> | Bulletin 331G (2016) <https://www.evapco.com/sites/evapco.com/files/2018-06/ATSeries_Catalog_2016.indd_.pdf> | |
| Cell size | 171–1,446 nominal tons/cell, ≤ 4,500 gpm. Nominal ton = 3 gpm, 95→85 °F at 78 °F WB (p. B32 note 3) | ~100–1,000+ tons/cell, same 95/85/78 basis (pp. 5–7) | 33–5,141 nominal tons | H |
| Fill / distribution | BACross PVC crossflow film fill with integral eliminators; gravity hot-water basins, non-clog nozzles | PVC crossflow film fill; gravity distribution basins (SPEC p. 9) | Counterflow film fill; pressurised EvapJet spray | H |
| Fan efficiency, catalog basis | 45–59 gpm/hp for the standard models listed (p. B31–B32, §7). "XE" models are ≥ 2× the code minimum | 42–108 gpm/hp: the same box with different motors (pp. 5–7) | CTI-certified, 90.1 compliant | H |
| Min water flow per cell | **50 %** of design with weir dams; the spec calls for "weir dams and metering nozzles for at least 50 % turndown" (p. B24) | Variable-flow distribution is an option, with the minimum % left to the specifier (SPEC p. 24) | Not published | H |
| Fan VFD minimum | Gear drive: **≥ 450 rpm motor speed (≈ 25 %)**, lower only with a low-speed gear option. ENDURADRIVE direct drive: no minimum. Lock out resonant speeds; ≤ 6 starts/h (O&M) | Gearbox can be modified for operation "down to 10 % of full speed" (SPEC p. 7); 4–5 starts/h (manual p. 16) | Not published | H |
| Drift | Not found in the documents read | Base spec "0.005 % or less"; **0.0005 %** "readily available on many standard models". Drift is not CTI-certified and is hard to measure in the field below 0.001 % (SPEC p. 8) | "less than **0.001 %** … in most models" (p. 5) | H |
| Basin heater (hold 4.4 °C / 40 °F) | 0 °F ambient: 2×6 kW (8518 box) to 2×14 kW (1424 box). −20 °F: 2×9 to 2×20 kW (p. B23, 15 mph wind) | Holds 40 °F at the specified ambient (SPEC p. 16) | 14-ft box: 2–5 kW (0 °F), 3–7 kW (−20 °F). 19-ft box: 5–8 / 7–12 kW (p. 11) | H |
| Cycles of concentration | — | "acceptable levels … **2–4** concentrations"; at 10 °F range and 4 cycles, blowdown = 0.25 % of flow (manual p. 21) | — | H |

Not researched: Delta, Tower Tech, Marley NC Everest and MD Everest. Note that Marley NC is crossflow, not counterflow; the Everest line was not checked.

**Selection-software printouts.** These come from Marley UPDATE 4.7, NC8306/NC8305, 2 cells, 2,100 gpm at 95/85/79 °F. Source: <https://www.engr.psu.edu/AE/THESIS/portfolios/2006/ntp111/finalreport/patrick-appendix-b.pdf> (H).

- NC8306EL2: 15 bhp/cell, 191 rpm, rated **99.4 gpm/hp on the 90.1 basis**.
- NC8305FL2: 20 bhp/cell, 72.6 gpm/hp.
- Estimated evaporation is 23 gpm, i.e. **1.1 % of flow per 10 °F range** at design.
- The performance curves (cold water vs. WB at ranges of 6/10/12 °F) are printed only as graphics.
- No tabulated multi-flow, multi-speed curves from BAC, EVAPCO iES or SPX are public; they would have to be requested as a submittal.

**Evaporation rules of thumb.** Our Phoenix result is 1.47 L/kWh, about 99 % of the heat leaving as latent heat. The published rules agree with this to within their stated precision:

- Marley's makeup table (TECH-NC-26 p. 15) gives 13 gpm per 1,000 gpm at 10 °F range and 3 cycles. That implies evaporation ≈ **0.85–0.87 % per 10 °F**.
- The UPDATE printout above gives 1.1 % per 10 °F.
- Our own arithmetic gives ≈ 3 gpm per 100 tons of heat rejected (15,000 Btu/h per ton, ~1,000 Btu/lb).

### 1.2 What data-center guides ask for

| Topic | Guidance | Source | Conf. |
|---|---|---|---|
| Approach + reset | "a **5 °F to 7 °F approach** cooling tower plant with a condenser water temperature reset pairs nicely with a variable speed chiller"; oversized towers with VFD fans | DOE FEMP/NREL, *Best Practices Guide for Energy-Efficient Data Center Design* (rev. July 2024) §5.3.1–5.3.2 p. 16–17, <https://www.energy.gov/sites/default/files/2024-07/best-practice-guide-data-center-design.pdf> | H |
| Liquid-cooling classes | W17/W27/W32/W40/W45/W+ (5th ed. Thermal Guidelines, 2021) replace W1–W5 | same, p. 22 | H |
| Tower efficiency, approach | Tower ≥ **80 gpm/hp** (90.1 basis). Approach (°F) = 27 − ΔT_CW − 0.001·CDD50, limited to 2.5–9.5 °F | Taylor, "Optimizing Design & Control of Chilled Water Plants, Part 4", ASHRAE J. Mar 2012 p. 64, <https://tayloreng.egnyte.com/dd/QGwd1fAz2A/> | H |
| CW ΔT | ≈ **15 °F (8.3 K)** CW ΔT is the life-cycle optimum (≈ 2 gpm/ton) | Taylor Part 3 (2012), <https://tayloreng.egnyte.com/dd/th814oq8SP/>. Schwedler, ASHRAE J. Jan 2014 (500 t at 2 gpm/ton, 14 °F range, 4.5 °F approach), <https://Www.Trane.com/content/dam/Trane/Commercial/global/learning-center/ashrae-articles/Schwedler-012014--02262015feature.pdf> | H |
| Cell operation | Nozzles/dams "that allow half flow"; "always most efficient to run as many tower cells as possible … fans controlled to the same speed" | Taylor Part 5, ASHRAE J. June 2012, <https://tayloreng.egnyte.com/dd/kfU6kUgBF7/> | H |
| Cell operation | 4 cells at ≈ 56 % speed reject the same heat as 2 cells at 100 % with > 60 % less fan energy. Respect the manufacturer's minimum speed and flow. Closer approach pays for constant loads such as data centers | Morrison (BAC), "Saving energy with cooling towers", ASHRAE J. Feb 2014, <https://baltimoreaircoil.com/es/download_api_endpoint/528/ashrae_journal_feb2014_savingnrgwithct.pdf> | H |
| Fan minimum speed | Fans "generally not run at speeds below 30 %" (critical speeds, motor cooling, gearbox lubrication) | CTI/Baldor paper, <https://www.baldor.com/~/media/files/brands/baldor-reliance/energy%20savings/cooling%20tower%20materials/paper%20cooling%20technology%20institute.ashx> | M |
| Fan minimum speed | Belt drive allows "near zero"; gear drive needs ~20 % | Taylor Part 4 | H |
| N+1 cells | No Uptime or OCP text with a numeric rule was found. N+1 cells, concurrently maintainable, is common practice (assumption retained) | — | L |

For the model (≈ 7 °F range of 10 °F, ΔT_CW = 10 °F), Taylor's formula gives a larger approach than ours:

- Phoenix, CDD50 ≈ 8,000–8,500 °F·d (approximate, not looked up): ≈ 8.5–9 °F.
- Chicago, CDD50 ≈ 3,000 °F·d: capped at 9.5 °F.

The formula is a life-cycle cost optimum for variable-load comfort plants. For a constant data-center load, the FEMP 5–7 °F and Morrison's advice favour the closer approach we use.

### 1.3 Codes

| Requirement | Value | Source | Conf. |
|---|---|---|---|
| ASHRAE 90.1 Table 6.8.1-7, open-circuit axial-fan tower | **≥ 40.2 gpm/hp** at **95/85/75 °F** (CTI ATC-105, STD-201). Centrifugal: ≥ 20.0. Closed-circuit (102/90/75): 14.0 / 7.0. Centrifugal open towers ≥ 1,100 gpm must meet the axial value | BAC *Codes & Standards* handbook pp. J23–J24 (90.1-2013), <https://baltimoreaircoil.com/es/download_api_endpoint/1187/j22_tr_codesstandards_20150914.pdf>. SPEC-NC-26 p. 5 quotes 40.2 @ 95/85/75. Unchanged through 2019/2022 per the specs that cite them; the 2022 table itself was not seen | H (2013), M (2022) |
| 90.1 multi-cell control | Run the maximum number of fans the manufacturer allows, all at the same speed; stage only at minimum speed. Open-circuit towers on systems with multiple or variable CW pumps: **50 % flow turndown** per cell | Morrison 2014 p. 38 summarising 90.1-2013 §6.5.5 | M–H |
| Title 24-2022 §140.4(h) | Prescriptive **≥ 60 gpm/hp** for axial open towers ≥ 900 gpm (mandatory floor 42.1, Table 110.2-G). **50 % cell turndown** (h)3. Fans ≥ 7.5 hp capable of ≤ 2/3 speed. Drift eliminators ≤ 0.002 % (counterflow) / 0.005 % (crossflow) | Energy Code Ace, <https://energycodeace.com/content/table-4-11>. BAC handbook p. J31 | H |

**Basis conversion (important).** EnergyPlus's Merkel *Nominal Capacity* uses 5.382e-8 m³/s per W, i.e. 3 gpm per 12,000 Btu/h. This is the catalog nominal ton at 78 °F WB. On that basis:

- Fan W per W of nominal capacity ≈ **0.636 / (gpm/hp)**. This uses motor hp; electrical input is a further 5–8 % higher.
- Code gpm/hp is rated at 75 °F WB (a 10 °F approach), so the same tower scores **≈ 1.2–1.4× higher** on the code basis.
  - The Marley printout illustrates this: 99.4 code basis vs. ≈ 70 gpm/bhp at 79 °F WB.
- Rough equivalents in EnergyPlus terms:

  | Benchmark | Code basis | W/W |
  |---|---|---|
  | 90.1 minimum | 40.2 gpm/hp | ≈ 0.018–0.022 |
  | Title 24 | 60 gpm/hp | ≈ 0.013–0.015 |
  | Taylor | 80 gpm/hp | ≈ 0.0095–0.011 |
  | Catalog standard models (BAC 45–59, NC 42–108 gpm/hp) | — | ≈ 0.006–0.015, typically 0.011–0.012 |

- **The E+ default 0.0105 is an efficient, Taylor/XE-class selection (≈ 75–85 gpm/hp code basis), not a median one.** `DATACENTER_MODEL.md` §2 says "≈ 60 gpm/hp … better than ≈ 38–40". That compares a 78 °F-basis number with a 75 °F-basis minimum and understates the margin.

**Cell size check.** Our nominal capacity is 1.54 MW = 438 nominal tons ≈ 1,314 gpm, i.e. ≈ 146 tons / 438 gpm per cell. That is below BAC Series 3000's smallest cell (171 tons). It fits Marley NC8401/8402 (≈ 100–310 t), small EVAPCO AT boxes or BAC Series 1500.

---

## 2. Chillers

| Chiller | Min. entering condenser water (ECW) | Other limits | Source | Conf. |
|---|---|---|---|---|
| Trane CenTraVac (CVHE/CVHF/CDHF) | Steady operation down to a 3 psid (20.7 kPa) condenser–evaporator pressure difference. "can equate to safe minimum entering condenser water temperatures **at or below 55 °F (12.8 °C)**", depending on load and leaving chilled water temperature (LCHWT). Tracer chiller–tower optimisation floats the tower setpoint 50–90 °F | Selectable at 0.45 kW/ton at AHRI (large sizes). Reduced CW flow: 2–2.5 gpm/ton examples | Catalog CTV-PRC021G-EN (Dec 2024) p. 32 "Condenser Water Control" / "Water Flow"; EB CTV-PRB027*-EN. <https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Product%20Catalog/CTV-PRC021G-EN_12202024.pdf> | H |
| Daikin Magnitude WMC-D (86–400 t, magnetic bearing) | **Operating minimum 55 °F (12.8 °C)**; start-up minimum 40 °F; maximum 105 °F. Needs head-pressure control: tower bypass valve, condenser 2-way valve or condenser-pump VFD | LCHWT 38–**60 °F** (15.6 °C maximum). Lift target 30 psi | IOM 1210-8 (Jan 2023) p. 6 Table 1, p. 10. <https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/IOM1210-8_WMC-D_01102023_HR.pdf/> | H |
| Daikin Magnitude WME-D (250–450 t) | ECW "down to **40 °F**" | LCHWT up to **70 °F**; 10 % minimum capacity without hot-gas bypass. "As good as 0.48 FL / 0.30 IPLV kW/ton" (Magnitude family) | CAT-639 (Jul 2024) pp. 2–3. <https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/CAT639_pub_07-23-24.pdf> | H |
| York YZ (magnetic bearing) | "as low as 40 °F (4.5 °C)"; stable with ECW 30 °F below the LCHWT setpoint | — | york.com product page; press release (refindustry.com) | M |
| York YMC² | Ratings to 36 °F ECW | IPLV ≈ 0.304 | ABRAVA brochure PUBL-6963 | M |
| Carrier AquaEdge 19MV | 40–95 °F ECW, to 10 % load | — | carrier.com 19MV page | M |
| Carrier 19DV, Smardt/Turbocor | Not found | — | — | — |

**Condenser flow.**

- AHRI 550/590 rates at 85 °F ECW and 3.0 gpm/ton (0.054 L/s per kW). This is our 5.6 K range (H).
- Low-flow design is 2–2.5 gpm/ton (≈ 7–9 K range). Trane cites 30–35 % pump plus tower energy savings (CTV-PRC021G p. 32, H). Taylor and Schwedler also favour it (see §1.2).

**Efficiency. ASHRAE 90.1-2019 Table 6.8.1-3**, water-cooled centrifugal, kW/ton full load (FL) / IPLV. Path B is confirmed in Addendum bd, Tables J-1/J-4: <https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20addenda/90_1_2019_bd_20220531.pdf> (H). Path A is transcribed from WAC 51-11C (M).

| Size | Path A FL / IPLV | Path B FL / IPLV |
|---|---|---|
| < 150 t | 0.610 / 0.550 | 0.695 / 0.440 |
| **150–300 t (our 157 t units)** | 0.610 / 0.550 | **0.635 / 0.400** |
| 300–400 t | 0.560 / 0.520 | 0.595 / 0.390 |
| ≥ 400 t | 0.560 / 0.500 | 0.585 / 0.380 |

Our Carrier 19XR VSD curve set is 0.582 kW/ton FL and 0.513 IPLV (COP 6.04 / 6.86):

- Its full-load efficiency beats Path B.
- Its **IPLV is far worse than Path B (0.400) and the magnetic-bearing claims (0.30–0.35)**.

In operation the model reaches an annual COP of 8.7 (0.40 kW/ton) because of the low lift, so the curve is not unrealistic in absolute terms. Its part-load and low-lift shape is still that of a 2000s VSD machine.

**90.1-2019 Addendum bd, Normative Appendix J** (Appendix L in 90.1-2022) prescribes Chiller:Electric:EIR curves. Set S is centrifugal 150–300 t, Path B, 0.635/0.400, SI units (Table J-5), with reference 7/30 °C (H):

| Curve | Coefficients |
|---|---|
| EIR-f-T | 0.526475, −0.030843, 0.000735, 0.035532, −0.000510, 0.000216 |
| CAP-f-T | 0.971699, 0.036192, −0.001858, −0.005224, −0.000134, 0.000709 |
| EIR-f-PLR | 0.064979, 0.151829, 0.779131 |

- Valid for **CHWT 4–16 °C, ECT 12.8–40 °C**; minimum PLR 0.25.
- Limitation: EIR-f-PLR has no lift term. Chiller:Electric:ReformulatedEIR captures lift better (Hydeman et al., ASHRAE Trans. 2002; L–M).

**CHW supply temperature in data centers.**

- FEMP/NREL guide §5.3.2: "a medium-temperature … chilled water loop design using a water supply temperature of **55 °F or higher**" (H).
- Schneider Electric WP (Frankfurt case; WP number 227 from memory): 7 → 17 °C CHW gave 39 % cooling-energy savings. Above about 20 °C, redesigned CRAH coils are needed (M, secondary: <https://theenergyst.com/higher-chilled-water-temperatures-can-improve-energy-efficiency-64/>).
- Vertiv: data-center water is often > 20 °C (M).
- Google patents describe 55–70 °F CHW (US 9,554,491; M).
- **Modern colocation and hyperscale chilled-water plants: 15–18 °C supply, 6–8 K ΔT** (M). Our 10 °C is legacy-like.

**Heat rejection ratio.**

- The CTI tower ton is 15,000 Btu/h = 1.25 × the refrigeration ton, which implies COP ≈ 4.
- Physically the ratio is 1 + 1/COP: ≈ 1.17 at the 19XR's rated COP and ≈ 1.08–1.12 with CW reset.
- Our model gives tower Q / (IT + chiller) = 1.10 (plus UPS, CRAH fan and pump heat).
- The Merkel "Heat Rejection Capacity and Nominal Capacity Sizing Ratio" of 1.25 is the CTI convention and is appropriate.

**ASHRAE 90.4 maximum annualised MLC.** Source: 90.4-2022 Addendum g, Table 6.5, ITE > 300 kW (H): <https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20addenda/90_4_2022_g_20240131.pdf>.

| Climate zone | MLC |
|---|---|
| 0A | 0.29 |
| 1A | 0.30 |
| 2B (Phoenix) | 0.20 |
| 3B | 0.20 |
| 4A | 0.21 |
| 5A (Chicago) | 0.19 |
| 6A | 0.19 |
| 7 | 0.17 |
| 8 | 0.15 |

Our modelled mechanical overhead, chillers + CRAH fans + pumps + tower fans, is ≈ 0.20 of IT in both cities. That sits at the limit for 2B and 5A without an economizer, which is a useful plausibility statement for the paper. The comparison applies the MLC definition approximately; 90.4 excludes UPS from MLC.

---

## 3. Adiabatic / hybrid dry coolers (companion paper)

| Item | Finding | Source | Conf. |
|---|---|---|---|
| Pad effectiveness, Munters CELdek (60 L/min/m² wash) | 7090-150 mm: 88/86/83/81 % at 1.0/1.5/2.0/2.5 m/s. 7060-150: 82/77/74/72 %. 7060-100: 69/63/60/59 %. Wet ΔP 7060-150: 6/13/23 Pa at 1/1.5/2 m/s; 7090-150: 13/30 Pa at 1/1.5 m/s | CELdek-PS-EN-202204 p. 2 (chart line data), <https://www.munters.com/globalassets/digizuite/6108-en-celdek-ps-en-202204.pdf>. Cross-check: Rey Martínez et al., *Energies* 13 (2020) 2218, Table 2 | M |
| Pad effectiveness, independent test | Best of all pads tested: **78 % at 2.0 m/s, 76 % at 2.5, 74 % at 3.0**. 150 mm pads at 3 m/s: 60–74 %, 32–85 Pa. "None … achieved 90 % … in the normal operating velocity range". Most adiabatic coolers are selected at ≈ 3 m/s face velocity. Water rate 50–150 % and water temperature have little effect. Assuming 90 % instead of 70 % makes the unit ≈ 44 % smaller with 38 % less fan power | EVAPCO white paper (11/2018, CTI 2019) pp. 2, 5, 18–19, Table 3, <https://www.evapco.com/sites/evapco.com/files/2019-02/Adiabatic-Pad-Saturation-White-Paper-11.2018.pdf> | H |
| Marketing claim | Air cooled "to 1–3 °F above the wet-bulb" (ε > 0.9) | BAC TrilliumSeries brochure (2020) p. 2, <https://baltimoreaircoil.com/download_api_endpoint/1938/trillium_brochure_20200327.pdf> | M |
| Fan power | Eurovent dry-cooler classes are set by R = capacity / fan power at an ITD of 15 K (A > 110, B 70–110, … D 30–45; ThermoKey scale 24…240). Our 0.02 W/W at ITD 11.2 K ≈ R15 ≈ 67 (class C). Class A/B ≈ 0.007–0.014 W/W. BAC TSDC2-xxx-12.4: 9.2 kW of EC fans for 54–108 RT (≈ 0.02–0.04 W/W) | ThermoKey catalogue <https://www.thermokey.com/wp-content/uploads/2017/11/ThermoKey-Dry-Cooler_ENG.pdf> (H). Alfa Laval/Fincoil (M). BAC brochure p. 4 (M) | M |
| Approach | Rating basis 40/35 °C fluid with 25 °C air (10 K approach, ITD 15 K). An engrXiv preprint (Mokkapati & Das 2026, not peer reviewed) uses design approaches of 2.8/4.1/5.3 K at the 0.4/1/2 % points | ThermoKey (H); <https://engrxiv.org/preprint/download/7795/12658/10948> (M) | M |
| Control sequence | Pre-cooling starts **only after all fans reach maximum speed** and the dry→adiabatic setpoint is reached. Adiabatic blocked below **4 °C ambient**. ≤ 1 wet start/stop per day per side. Coil leaving water ≥ 10 °C if plain water | BAC TRF Trillium O&M MTRFv00EN pp. 13, 15. BAC SP-EC O&M MSP-ECv04EN p. 13 (baltimoreaircoil.eu) | H |
| Control sequence | "The adiabatic system is not triggered until the fans are running at 100 % speed and the set point is not satisfied" | EVAPCO eco-Air Controller Quick Start (Bulletin 1120) p. 7, <https://www.evapco.eu/sites/evapco.eu/files/2021-03/eco-Air%20Controller%20Quick%20Start%20Guide.pdf> | H |
| Switch point | Set from TMY bin analysis, example 70 °F (21 °C) (Güntner, ASHRAE MN 2021; snippet only). Adiabatic extends free cooling to 30–32 °C (Liebert AFC) | Güntner blog <https://guntner.com/en-us/our-impact/blog/planning-for-adiabatic-cooling-in-data-centers> | L–M |
| Water / bleed | Once-through spray: ≈ 4.3 L/min per 910 mm fan (SP2A 9, SP4A 17, SP7A 30 L/min), valid to 35 °C and RH ≥ 30 %. Water limits: < 20 °C, pH 6.5–9, TDS < 1,500 mg/L. Recirculating Trillium: sump drained and refilled every 2 h; fully drained and dried after each wet cycle (Legionella). Purge ≈ 25 % of evaporation (ICS Cool Energy example). Wet-hour limits: spray ≤ 500 h/yr, wet-fin ≤ 1,000, pads ≤ 8,000 h/yr | BAC SP-EC O&M p. 9 (H); TRF O&M pp. 9–10, 25 (H); <https://www.icscoolenergy.com/?p=1277> (M); ThermoKey pp. 4–5 (H) | M–H |
| Data-center water | Transtherm (UK), per 1,000 kW per year: adiabatic 92 m³ (≈ 3 % of hours wet); wetted-surface hybrid 8,647 m³; tower 18,220 m³. Mokkapati & Das: adiabatic saves a median 30.5 % of heat-rejection electricity at 31–213 L of water per kWh saved | *Intelligent Data Centres* Issue 01 p. 42 (M); engrXiv (M) | M |

Pad pressure drop is not in the current hybrid model. The 0.02 W/W fan power is close to what an EC-fan unit plus 20–80 Pa of wet pad needs.

---

## 4. Fill characteristic: is Me ∝ (L/G)^−0.6 right?

The exponents below are collected in `data/equipment/fill_correlations.csv`.

| Source | Fill / tower | n in Me = c (L/G)^−n |
|---|---|---|
| Kloppers 2003 PhD, Tables R.13, S.17, T.13 (Merkel-based fits) | trickle 1.08/1.53/1.98 m | 0.55 / 0.62 / 0.66 |
| | splash (0.1–0.4 m spacing) | 0.51–0.57 |
| | cross-corrugated film 0.6/0.9/1.2 m | 0.59 / 0.61 / 0.65 |
| Kloppers, Poppe-based fits (R.3, R.7) | trickle | 0.52–0.58 |
| **This work: Poppe refit of the measured points (§5)** | film | **0.57–0.60** |
| | trickle | 0.55–0.59 |
| | splash | 0.51 |
| Braun 1988 PhD Table 3.1 (Simpson & Sherwood lab towers) | 4 towers | 0.39, 0.73, 0.85, 0.62 |
| Braun 1988 §3.1.6 | D/FW airport field tower, 4 cells | 0.63 |
| Pirunkaset (ATC-105 worked example) | film | 0.61 |
| TRNSYS Type 51 manual | general | 0.35–1.1 |

- **n = 0.6 is well supported for counterflow film fill under a Poppe analysis.** Kloppers' film-fill data refit with our Poppe code give n = 0.57–0.60.
- Merkel-based fits are ≈ 0.03–0.09 higher, because Me_Poppe is 10–28 % above Me_Merkel for the same test.
- **The split form is better.** Kloppers' combined film correlation (eq. T.1; also Kloppers & Kröger, *IJHMT* 48 (2005) 765–777) is

  Me/L_fi = 1.0198 · G_w^−0.433 · G_a^0.783 · L_fi^−0.293 (G in kg/m²s).

  The water-flow and air-flow exponents differ. The apparent n is ≈ 0.75–0.78 when only the fan varies and ≈ 0.43 when only water varies.
  - The fixed-fill rating check in `tools/review_analyses.py` mostly varies air flow at fixed water flow, since the CW flow is constant per chiller. Its n = 0.6 is therefore **too low for that path**.
  - With the split form, the rms error in T_w,out on the measured data drops from 0.47–0.83 K (n = 0.6) to 0.13–0.21 K for film fill (§5).
- No published crossflow-fill exponents were found. Kloppers (App. H) notes a crossflow fill needs ≈ 7–8 % more Me than counterflow for the same duty. Most data-center towers listed in §1 are crossflow (BAC S3000, Marley NC), so state this as a limitation.

**Implication for the EnergyPlus UA curves.** If UA ∝ KaV = Me·ṁ_w, the fill data give UA/UA_d = AFR^c · WFR^(1+b):

| Fill | c (air) | 1 + b (water) | UA(AFR) | UA(WFR) |
|---|---|---|---|---|
| Film | 0.69–0.79 | 0.53–0.60 | ≈ AFR^0.7 | ≈ WFR^0.58 |
| Trickle | ≈ 0.6 | ≈ 0.45 | ≈ AFR^0.6 | ≈ WFR^0.45 |

Quadratic fits for EnergyPlus `Curve:Quadratic` objects (our fit):

| Curve | Fit range | Coefficients | Max error |
|---|---|---|---|
| UA(AFR) = AFR^0.7 | 0.2–1.0 | 0.1174 + 1.1082·x − 0.2292·x² | 0.006 |
| UA(AFR) = AFR^0.6 | 0.2–1.0 | 0.1807 + 1.0944·x − 0.2799·x² | 0.008 |
| UA(WFR) = WFR^0.58 | 0.3–1.5 | 0.2473 + 0.9169·x − 0.1617·x² | 0.010 |

Comparison with the current E+ example curves:

- UA(AFR) = 1.3x − 0.3x² gives 0.248 at x = 0.2, against 0.32–0.38 from the fill data. It is close above x ≈ 0.5 (0.575 vs 0.616 at 0.5).
- UA(WFR) = 0.1082 + 1.667x − 0.7713x² gives 0.879 at x = 0.67, against 0.79 from the fill data, and saturates above design (0.987 at 1.25 vs 1.14).

Our MaximalCell N+1 tower always runs at WFR ≈ 0.67. With the current curve, EnergyPlus therefore credits each cell with ~11 % more UA than film-fill data suggest. That makes the fans run slower than they would. This is a variant to test, not a proven error: the E+ "UA" is a Merkel-ε-NTU lumped parameter.

---

## 5. Measured-performance check of our Poppe model (Kloppers 2003 fill tests)

**Data.** Kloppers, J.C., *A critical evaluation and refinement of the performance prediction of wet-cooling towers*, PhD thesis, Stellenbosch University, 2003, Appendices R (trickle), S (splash) and T (film). <http://hdl.handle.net/10019.1/1476>. PDF: <https://scholar.sun.ac.za/server/api/core/bitstreams/fd4a81c4-3cec-466e-8cd3-94eb3b338405/content>.

- Counterflow test section of 1.5 × 1.5 m.
- Each test records measured T_db, T_wb, T_w,in, T_w,out, ṁ_a, ṁ_w, Δp, outlet air temperature and pressure.
- The thesis also tabulates Kloppers' own Me_Merkel, Me_eNTU and Me_Poppe and his Poppe/Merkel-predicted outlet air temperature.
- 126 points were extracted (7 fills × 18 tests) from the OCR text, with a handful of OCR typos fixed by hand. Every row passes ṁ_w/2.25 = G_w, ṁ_a/2.25 = G_a (±0.03), T_w,out < T_w,in and T_wb < T_db.
- File: `data/equipment/kloppers2003_fill_tests.csv`. Me columns are whole-fill values (thesis Me/L_fi × L_fi). For splash fill, L_fi = 2.5 m was assumed (check Table S.2).
- Not yet extracted, same format: splash fill at 0.2/0.3/0.4 m spacing (Tables S.5, S.9, S.13).
- These are fill tests, not full towers. No open, tabulated multi-point acceptance test of a full-scale tower (ATC-105 sheets or manufacturer curves) was found.

**Check.** We ran `evaporation.poppe` (Bosnjakovic Lewis factor, 20 RK4 steps) and `merkel_number_exact` on each measured point, then a rating test with `outlet_temperature_poppe`. The script is in the session scratchpad, not the repo; it is ≈ 60 lines and easy to rebuild from the description. Per-fill results are in `data/equipment/kloppers2003_poppe_check_summary.csv`; per-point results are in `…_points.csv`.

| Fill | Me_P ours vs Kloppers, mean (max) % | Me_Merkel ours vs Kloppers, % | T_a,out Poppe − measured, bias / rms K | Ours − Kloppers' Poppe T_a,out, K | T_w,out rms, fill c(L/G)^−n fit, K | T_w,out rms, G_w/G_a fit, K | T_w,out rms, n = 0.6 anchored at median point, K (max) | Evaporation error with n = 0.6 fill, mean (max\|\|) % |
|---|---|---|---|---|---|---|---|---|
| trickle 1.08 m | +0.8 (1.7) | +2.5 | +0.55 / 0.86 | +0.02 | 0.20 | 0.13 | 0.38 (0.85) | +1.0 (4.7) |
| trickle 1.53 m | +0.9 (2.2) | +3.6 | −0.88 / 1.18 | +0.03 | 0.17 | 0.13 | 0.18 (0.44) | −0.5 (2.7) |
| trickle 1.98 m | +1.6 (8.8) | +4.3 | −0.58 / 1.12 | +0.05 | 0.19 | 0.19 | 0.17 (0.59) | 0.0 (2.0) |
| splash 0.1 m | +0.9 (2.0) | +2.5 | +0.23 / 0.56 | +0.03 | 0.20 | 0.13 | 0.46 (1.15) | +1.0 (6.6) |
| film 0.6 m | +0.9 (1.8) | +3.0 | −0.34 / 0.68 | +0.04 | 0.55 | 0.21 | 0.83 (1.61) | +4.3 (11.5) |
| film 0.9 m | +1.0 (2.6) | +3.3 | −0.25 / 0.63 | +0.03 | 0.41 | 0.14 | 0.68 (1.44) | −4.4 (10.2) |
| film 1.2 m | +1.0 (3.4) | +3.5 | −0.16 / 0.64 | +0.03 | 0.32 | 0.13 | 0.47 (1.07) | −3.0 (7.7) |

Findings:

1. **Our Poppe implementation reproduces Kloppers' independent Poppe analysis.**
   - Me_P agrees within ≈ 1 % on average.
   - The predicted outlet air temperature agrees within 0.02–0.05 K.
   - Our Merkel numbers are 2.5–4 % above his. This is probably a psychrometric or c_p convention difference; it has not been investigated.
2. **Against the measurements**, the Poppe outlet-air temperature has an rms error of 0.6–1.2 K. That is the measurement scatter that Kloppers' own Poppe also shows. The water side closes by construction, because Me is derived from the measured T_w,out.
3. **Rating mode with a fixed fill.**
   - c(L/G)^−n predicts T_w,out within 0.17–0.55 K rms.
   - The split G_w^b G_a^c form gives 0.13–0.21 K.
   - A single-anchor n = 0.6 curve (our review analysis's approach) gives 0.17–0.83 K rms, max 1.6 K, and **evaporation errors up to ±11 %** on film fill when L/G varies 3–8×.
   - Over the much narrower L/G range of the data-center tower (fan speed 0.2–1.0, constant water flow), errors would be smaller. The **split form is still the defensible choice**.

Use in the paper: cite this as a validation of the Poppe solver against published measured fill data. It also brackets the uncertainty of the fixed-fill rating check (M3) and replaces "exponent is an assumption" with a sourced range.

---

## 6. Recommendations

**Base** = change it in the base model now. **Sens.** = sensitivity variant. Impacts are expected directions, not simulated; EnergyPlus was not run for this note. Ranked by importance for realism.

| # | Parameter (EnergyPlus input) | Current | Recommended | Sources | Conf. | Expected impact | Base / Sens. |
|---|---|---|---|---|---|---|---|
| 1 | CW reset floor (`SetpointManager:FollowOutdoorAirTemperature` Minimum Setpoint) | 18.0 °C | **15.5 °C (60 °F)** base. Variants 12.8 °C (55 °F: Trane/Daikin minimum with head-pressure control; also the lowest ECT of the 19XR and 90.1 App. J curves) and 18 °C (current) | Trane CTV-PRC021G p. 32; Daikin IOM 1210-8 Table 1; WME/YZ ≤ 40 °F; FEMP §5.3 | H | **Energy:** Chicago and other cool sites leave the floor more often, so chiller energy drops (climate finally shows up in PUE) while tower fan hours at high speed rise. **Water:** evaporation ∝ heat rejected, so a slight decrease. Low-WB fan operation changes the SaturatedExit latent fraction and thus the Poppe-vs-E+ gap in winter. More CW-unmet hours at low WB with a fixed approach (see #6) | Base |
| 2 | CHW supply temperature + chiller curves | 10 °C; Carrier 19XR VSD EIR curves (IPLV 0.513 kW/ton, CHW ≤ 10 °C) | **15.5–16 °C** supply, 6–8 K ΔT, with the **90.1-2019 App. J / 2022 App. L Set S** curves (centrifugal 150–300 t, Path B 0.635/0.400; valid CHWT 4–16 °C, ECT 12.8–40 °C). An 18 °C variant needs a high-LCHWT chiller (WME-D to 21 °C) and a curve set valid beyond 16 °C | FEMP §5.3.2 (≥ 55 °F); Schneider (17 °C); Daikin WMC-D max 60 °F; Addendum bd Table J-5 | M–H | **Energy:** chiller kW down ≈ 10–25 %. **Water:** tower heat down by the saved compressor energy (≈ 1–3 % less evaporation). Coil resizing changes CRAH flow. No effect on the Poppe/E+ method comparison itself | Base (with the curve change), or a "modern plant" variant if keeping 10 °C for continuity |
| 3 | Merkel UA modifier curves `fAirFlowRatio`, `fWaterFlowRatio` | E+ example: 1.3x − 0.3x²; 0.1082 + 1.667x − 0.7713x² | Fill-based: UA(AFR) ≈ AFR^0.7 → 0.1174 + 1.1082x − 0.2292x² (0.2–1.0); UA(WFR) ≈ WFR^0.58 → 0.2473 + 0.9169x − 0.1617x² (0.3–1.5) | Kloppers 2003 T.13 / eq. T.1; Kloppers & Kröger 2005; this work §4 | M | At WFR 0.67, UA is ~10 % lower, so higher fan speed (fan energy up, likely 10–30 % of tower fan kWh). Changes the air-flow input to SaturatedExit and Poppe and hence the evaporation comparison. Fan speeds near 0.2 change most (+30 % UA at AFR 0.2) | Sens. (report both) |
| 4 | Fill law in `tools/review_analyses.py` (`FILL_EXP`) | Me ∝ (L/G)^−0.6 | Keep 0.6 as the L/G form (sourced: Poppe film 0.57–0.60). Add the split form Me ∝ G_w^−0.43 G_a^+0.78 (film; trickle −0.48…−0.64 / +0.62…+0.67), which is closer to the air-only variation of this plant. Range n = 0.5–0.78 for sensitivity | §4–5 | H | Changes the M3 rating-check T_w,out and evaporation deviations. Expect the apparent fill to "improve" faster with fan speed, reducing the near-pinch correction. Cite the Kloppers validation | Base (analysis) |
| 5 | Design Fan Power per Unit of Nominal Capacity | 0.0105 W/W (≈ 60 gpm/hp catalog, ≈ 75–85 gpm/hp code basis) | Keep 0.0105 as an "efficient (Taylor ≥ 80 gpm/hp / BAC XE)" base. Variants: **0.0125** (median catalog selection, ≈ 50 gpm/hp) and **0.0145** (Title 24 60 gpm/hp minimum). 90.1 minimum ≈ 0.020 as an upper bound. Fix the gpm/hp statement in `DATACENTER_MODEL.md` §2 | BAC S3000 pp. B31–B32; TECH-NC-26; Taylor Part 4; Title 24 §140.4(h) | H | Tower fan 0.6–0.7 % of IT → up to ~1.3 %. PUE +0.005. Water: none directly (E+ air flow is fixed by UA, not fan power) | Sens. |
| 6 | CW reset logic (approach offset) | WB + 3.9 K fixed | Keep 3.9 K (7 °F) at design (FEMP 5–7 °F). Variant: approach widening at low WB, or a lift/PLR-based reset (Taylor Part 5; G36), to remove the Chicago unmet hours and excess fan hours | FEMP; Taylor Parts 4–5; Schwedler 2014 | M | Fewer high-fan hours in cold weather. Changes the air-flow distribution that drives the Poppe-vs-E+ difference | Sens. |
| 7 | Minimum Air Flow Rate Ratio | 0.2 | **0.25** (gear drive: BAC ≥ 450 rpm motor ≈ 25 %; CTI/Baldor "not below 30 %"). Keep 0.2 (or 0.1) only for direct-drive/belt (ENDURADRIVE, Marley gearbox option to 10 %) | BAC RGOM300E01; SPEC-NC-26 p. 7; Baldor/CTI; Taylor Part 4 | H | Chicago reaches 0.20; with 0.25 the tower cycles or overcools at minimum. Small energy effect. Affects low-load evaporation (more air → more sensible share) | Base |
| 8 | Cell Minimum Water Flow Rate Fraction | 0.33 | **0.5** (weir dams / 50 % turndown). Cell Maximum Water Flow Rate Fraction 2.5 → **1.2–1.25** (hot-basin overflow limit; typical +10–25 %, assumption) | BAC S3000 p. B24 and spec; Title 24 §140.4(h)3; 90.1 §6.5.5; Taylor Part 5 | H | None in normal N+1 operation (per-cell flow ≈ 0.67). Matters in a cell-outage or 1-chiller variant: a 0.5 minimum keeps 2 cells on rather than 3 | Base (no-cost realism) |
| 9 | Blowdown Concentration Ratio | 4 | Keep 4 (Marley 2–4). Variants **3** and **6** (treated or softened water); site water chemistry via `src/tower_water/chemistry.py` | Marley Z0628276 p. 21 | H | Blowdown = E/(C−1): 3 cycles +50 %, 6 cycles −40 % of blowdown (≈ ±8–13 % of make-up) | Sens. |
| 10 | Condenser flow / Design Range | 5.6 K (3 gpm/ton) | Keep for AHRI-standard comparability. Low-flow variant **8.3 K (2 gpm/ton)**: chiller *Reference Condenser Water Flow Rate*, `Design Water Flow Rate per Unit of Nominal Capacity` ≈ 3.6e-8 m³/s per W, Design Range 8.3 K | Taylor Part 3; Schwedler 2014; Trane CTV-PRC021G p. 32 | H | CW pump energy −50–70 %, chiller lift +, smaller tower flow and higher L/G-specific Me. Evaporation per kWh nearly unchanged (slightly higher, larger ΔT on air) | Sens. |
| 11 | Drift Loss Percent | 0.001 % | Keep (EVAPCO < 0.001 %; Marley 0.0005 % option). Variants 0.0005 % and 0.005 % (Marley base spec; Title 24 crossflow limit) | EVAPCO 331G p. 5; SPEC-NC-26 p. 8; Title 24 | H | Negligible for water (15–18 m³/yr; 0.005 % → ~90 m³ ≈ 0.5 % of make-up). Matters only for the drift/PM discussion | Base (keep) |
| 12 | Basin Heater Capacity / Setpoint | 0 W | Base keep 0 (towers run year-round under a constant IT load). For cold-climate variants with idle cells: ≈ 4–14 kW per cell (0 °F) to 9–20 kW (−20 °F) for 150–1,000 t cells, setpoint 4.4 °C (40 °F) | BAC S3000 p. B23; EVAPCO 331G p. 11 | H | Electrical only, and only when cells are idle | Sens. |
| 13 | Number of cells / nominal capacity | 3 × 146 nominal t (438 gpm/cell), N+1 | Keep. Note that cells this size map to Marley NC8401/8402, small EVAPCO AT or BAC S1500, not BAC S3000 (≥ 171 t) | §1.3 | M | None | — |
| 14 | Free Convection capacity / air flow | 0.1 / 0.1 (E+ defaults) | Keep. The commonly quoted ~10 % fan-off capacity was not verified in this search, and the model never enters this regime | — | L | None | — |
| 15 | Hybrid: pad effectiveness (`--pad-effectiveness`) | 0.85 | **0.75–0.80 base** (150 mm 7090-type at 2–2.5 m/s; EVAPCO best 76–78 %). 0.85 as the optimistic variant, 0.65 as the low variant (thin pads at 3 m/s) | EVAPCO white paper pp. 2, 18–19; Munters CELdek | H | Less pre-cooling → higher condenser temperature → more chiller kWh. Pad water per wet hour ↓ ≈ ε; wet hours ↑ | Base (companion) |
| 16 | Hybrid: switch-over logic | DB threshold 16–32 °C | Base: **wet only when fans are at 100 % and the CW setpoint is unmet** (BAC/EVAPCO default), plus a DB threshold of 21–26 °C, lockout < 4 °C, ≤ 1 wet start/day | BAC TRF O&M p. 15; EVAPCO Bulletin 1120 p. 7 | H | Fewer wet hours, much less water. Fan energy at the maximum before wetting | Base (companion) |
| 17 | Hybrid: pad ΔP and bleed | not modelled / bleed per plugin | Add 20–30 Pa at 2 m/s (up to 85 Pa at 3 m/s) of fan static pressure in wet mode (≈ +10–25 % fan power at 115 Pa). Bleed ≈ 25 % of evaporation (recirculating) or once-through ≈ 4.3 L/min per fan module | Munters; EVAPCO Table 3; ICS Cool Energy; BAC SP-EC p. 9 | M | Wet-mode fan energy up; water up ~25 % vs evaporation-only | Sens. (companion) |
| 18 | Hybrid: fan power 0.02 W/W | 0.02 | Keep (≈ Eurovent class C at our ITD, including pads). Variant 0.012 (class A/B) | ThermoKey; Eurovent classes | M | Fan energy ±40 % | Sens. (companion) |

**Not recommended to change:**

- The Merkel *Heat Rejection Capacity and Nominal Capacity Sizing Ratio* (1.25, the CTI tower-ton convention).
- *Design Water Flow Rate per Unit of Nominal Capacity* (5.382e-8, the 3 gpm/ton basis), except in the low-flow variant.
- The design approach of 3.9 K (FEMP 5–7 °F).
- SaturatedExit evaporation mode. It is the object of the comparison, not an input to tune.

---

## 7. Files in `data/equipment/`

| File | Content |
|---|---|
| `kloppers2003_fill_tests.csv` | 126 measured counterflow fill-test points: trickle 1.08/1.53/1.98 m, splash 0.1 m, film 0.6/0.9/1.2 m. Inlet and outlet states, flows, Δp, measured T_a,out, Kloppers' Me (Merkel/e-NTU/Poppe, whole fill) and predicted T_a,out. Source: Kloppers 2003, Tables R.1–R.10, S.1–S.2, T.1–T.10 |
| `kloppers2003_poppe_check_summary.csv` | Per-fill results of §5 (our Poppe/Merkel vs Kloppers and vs measured; fitted c, n and G_w/G_a exponents; rating-mode errors) |
| `kloppers2003_poppe_check_points.csv` | Per-point results of §5 |
| `fill_correlations.csv` | Published fill and tower characteristic correlations: Kloppers, Braun / Simpson & Sherwood, D/FW field tower, ATC-105 example |
| `tower_catalog_points.csv` | Catalog and selection-software tower data (gpm/hp, equivalent E+ W/W) and code benchmarks with basis conversions |
| `evap_pad_performance.csv` | Pad saturation efficiency and wet pressure drop vs face velocity and thickness (Munters, Rey Martínez et al., EVAPCO) |

## 8. Gaps / to verify before citing

- The ASHRAE 90.1-2022 Table 6.8.1-7 text itself (40.2 gpm/hp is assumed unchanged).
- The 90.4-2019 MLC table; the values used here are from the 90.4-2022 addendum.
- BAC drift guarantee.
- Delta and Tower Tech data.
- Carrier 19DV and Smardt minimum ECW.
- Taylor Part 2 text.
- Guideline 36 CW reset sequence.
- Kloppers trickle eq. R.1 G_w exponent (OCR unclear, p. R.11).
- Splash L_fi definition.
- A full-scale multi-point tower acceptance test or a manufacturer curve with numbers. Ask a BAC/SPX/EVAPCO rep for a submittal performance curve set at 3 flows × 3 ranges; this would be the next-best validation after the Kloppers fill data.
- Open-access leads not yet checked:
  - Navarro Cobacho et al., *Applied Thermal Engineering* (2022) 118719: prototype tower, Poppe vs Merkel.
  - Nunes, ASHRAE 2016: 7 field tests reanalysed with Poppe.
  - Skobalj et al., *Hung. J. Ind. Chem.* 30 (2002).
