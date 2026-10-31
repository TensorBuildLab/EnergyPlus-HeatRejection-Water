# Referee report, round 1

**Manuscript:** "How much water does a data center cooling tower really use? A multi-method, physics-based evaporation and blowdown framework for EnergyPlus"
**Journal:** Energy and Buildings
**Recommendation:** **Major revision**

---

## Summary of the submission

The manuscript describes an EnergyPlus Python plugin. At each timestep the plugin reads the cooling-tower operating point from EnergyPlus: water temperatures, water flow, heat rejected, and air flow reconstructed from the fan state. It then evaluates eight evaporation models at that point, from rules of thumb to a Poppe model with the Bošnjaković Lewis factor and supersaturated exit air. Blowdown comes from a makeup-water chemistry model: constituent limits, the LSI and silica solubility.

The Poppe code is checked numerically against a height-wise boundary-value formulation. A standalone "climate map" for a fixed full-load tower shows where the simplified methods diverge from Poppe.

The models are then applied to a 1 MW chiller and cooling-tower data centre at 14 TMYx sites. Against Poppe, the EnergyPlus SaturatedExit method gives 3.7–9.3 % less annual evaporation, and the documented loss factor gives 4–64 % more. Makeup-water chemistry moves annual makeup by −13 to +22 %.

A second model emulates a hybrid adiabatic dry cooler. It overrides the dry-bulb of an EnergyPlus fluid-cooler air node through EMS, and the authors compare seven wet/dry control strategies with the tower. Finally, the paper lists five EnergyPlus heat-rejection "defects", including a 100× unit error in the LossFactor input and a ~1000× fluid-cooler air-flow autosizing error.

## Overall assessment and justification

The engineering is careful, and the core idea is useful to the building-simulation community. That idea is to evaluate many evaporation models at one simulated operating point, with water chemistry for blowdown. The EnergyPlus replica matches EnergyPlus output to within 0.4 %, the software is tested, and the authors are unusually open about their assumptions.

However, the manuscript is not ready for publication, for five main reasons:

1. **The headline claims outrun the evidence.** The paper says EnergyPlus "underestimates" water use, and the title asks how much water a tower "really" uses. Yet no measured data are used. The reference model (Poppe) is itself unvalidated here.
2. **Two of the most quotable results are artefacts of choices the authors made:**
   - The chemistry range (−13/+22 %) is set by placeholder water qualities and a 10-cycle cap. The project's own data file says these values must be replaced before results are published.
   - The hybrid "litres per kWh saved" figures rest on a dry baseline in which chillers run up to 12.8 K above their curve limits, with clamped curves.
3. **The cold-climate result needs a decomposition the authors do not provide.** This result says EnergyPlus is most biased in cold climates. Using the supplementary run outputs, I estimate that about half of the EnergyPlus–Poppe gap at the coldest sites is liquid mist in supersaturated exit air. The paper does not separate this mist out or verify it. The Poppe BVP verification covers unsaturated air only.
4. **The paper is two papers in one.** One is an evaporation and blowdown framework with a tower case study. The other is a hybrid dry-cooler water–energy study. A third strand, the EnergyPlus bug list, sits on top. Each part is treated too briefly to be fully convincing, and the paper cites only 14 references.
5. **Reproducibility statements are incomplete.** The repository URL, licence and affiliation are still marked TBD, and the supplementary documents contradict each other in places.

None of this is fatal. The tower part, with honest framing, a mist/vapour decomposition, a self-consistency check of accounting mode, sensitivity analysis and better positioning, would be a solid Energy and Buildings paper. I recommend major revision. I also strongly suggest moving the hybrid analysis to a separate paper or cutting it substantially.

---

## Major comments

### M1. Scope: two (or three) papers in one

**Issue.** The manuscript combines three strands:
- (a) a multi-method evaporation and blowdown framework with a 14-site tower study;
- (b) a hybrid adiabatic dry-cooler model and a 14 × 7 control study;
- (c) a list of five EnergyPlus defects.

The equations for (a) are mostly in the supplementary material. The hybrid model gets roughly one page. Its energy results are explicitly flagged by the authors as not quantitatively usable: "a high-lift chiller characterisation and manufacturer pad data are needed before the energy side is used quantitatively". The Introduction announces "four contributions" and then lists five.

**Why it matters.** Each strand is underdeveloped. The weakest strand, the hybrid energy results, weakens confidence in the strongest one, the tower water accounting. Reviewers and readers cannot judge a contribution whose methods sit in a GitHub markdown file.

**Requested change.** Pick one of two options:
- **Option 1 (preferred).** Make this paper (a) only. Bring the key equations (EPSAT replica, Braun exit humidity, chemistry) into the main text or an appendix. Expand the verification, sensitivity and validation work (M2–M8). Move (b) to a separate paper once the chiller and pad issues in M7 are fixed. Move (c) to an appendix, keeping only defect 4 in the main text (see M10).
- **Option 2.** Keep the hybrid section as a short demonstration of the EMS coupling. Report water results only, and drop the energy and "L/kWh saved" claims from the abstract and conclusions.

### M2. "Underestimates" and "really": a model-to-model comparison presented as error

**Issue.** Poppe is used as the reference throughout. The abstract and conclusions say the EnergyPlus default "underestimates annual evaporation by 3.7–9.3 %", and the title asks how much water a tower "really" uses. But the paper contains:
- no measured evaporation, makeup or blowdown data;
- no manufacturer performance data;
- no CTI test data.

The authors list "No measured validation yet" as limitation (iii). The Poppe model's own uncertainties are not discussed: the Lewis-factor correlation, the treatment of supersaturation and mist, and fill-dependent transfer. Poppe being more complete does not make it the truth for evaporation, especially in the supersaturated regime that drives the cold-climate result (M4).

There is also a framing point. Braun's e-NTU model is, by the authors' own statement, "thermodynamically consistent with the EnergyPlus `CoolingTower:VariableSpeed:Merkel` object". In accounting mode it is therefore arguably the most internally consistent water estimate for that object. It still differs from Poppe by 3–7 %.

**Why it matters.** Practitioners and permitting agencies will read "EnergyPlus underestimates by up to 9 %" as an empirical finding. It is the difference between two models.

**Requested change.**
- (i) Rephrase throughout: "differs from / is lower than the Poppe model by …", not "underestimates". Retitle: drop "really"; something like "Multi-method evaporation and chemistry-based blowdown modelling of data-centre cooling-tower water use in EnergyPlus".
- (ii) Add at least one validation layer:
  - manufacturer selection data (thermal) for a tower similar to the case-study design; and/or
  - published measured tower evaporation or makeup data; and/or
  - metered makeup and blowdown from one real facility, even a single site with a mass balance on conductivity.

  If no such data can be obtained, say so plainly in the abstract.
- (iii) Discuss the evidence for Poppe's evaporation predictions in the literature, not just its theoretical completeness.

### M3. Accounting mode: the operating point is not self-consistent with Poppe, and this is under-reported

**Issue.** Accounting mode evaluates all methods at EnergyPlus' $(T_{w,i}, T_{w,o}, \dot m_w, \dot m_a)$. At equal heat duty this is a legitimate and useful definition: "how much water accompanies this heat rejection at this air flow". But the paper itself shows that EnergyPlus' Merkel tower, which linearises the saturation enthalpy and picks the minimum fan speed, puts the exit air close to, or beyond, Poppe's thermodynamic limit.

The supplementary results show how often this happens:

| Site group | Share of timesteps needing the air-flow "adjustment" |
|---|---|
| Stockholm | 100 % |
| Dublin | 99.3 % |
| Portland | 94 % |
| Frankfurt | 61 % |
| Madrid | 58 % |
| Montreal, Atlanta, Phoenix, Singapore and the remaining sites | ~0 % |

The adjustment itself is small: the factor is 1.01–1.05, mostly 1.02–1.03. But three things follow from it.

- (a) **The same-operating-point premise breaks.** After adjustment, Poppe is evaluated at a different air flow from EPSAT, MSAT and Braun, even if the effect is ≲0.3 %.
- (b) **The implied fill characteristic is erratic.** I read the `MePoppe` output from the supplementary runs:

  | Site | $Me_P$, 5th–50th–95th percentile | Maximum |
  |---|---|---|
  | Stockholm | 2.0 – 3.6 – 11.4 | 74 |
  | Dublin | 2.6 – 3.9 – 16.6 | 72 |
  | Montreal | 1.2 – 2.2 – 3.2 | 3.5 |
  | Phoenix | 1.6 – 2.3 – 2.8 | — |
  | Singapore | 1.5 – 1.6 – 1.8 | — |

  For Stockholm and Dublin, a single physical tower would need its transfer characteristic to vary by more than an order of magnitude from hour to hour. In other words, the water difference in cold climates partly reflects a thermal solution that Poppe physics cannot reproduce with any fixed fill. It is not only "evaporation physics alone", as the Methods claim.
- (c) **Two climatically similar sites behave in opposite ways.** Stockholm (100 % adjusted, $Me_P$ up to 74) and Montreal (0 %, $Me_P \le 3.5$) give the same −9.3 % deviation. This is unexplained; it probably reflects the different design wet-bulbs, and therefore different relative tower sizes.

**Why it matters.** The paper's central claim is that differences "isolate evaporation physics". That holds only where the operating point is physically realisable under each model.

**Requested change.**
- (i) Report, per site, the share of adjusted timesteps, the distribution of the factor, and the distribution of the implied $Me_P$ and $Me_M$. Add a column to Table 4.
- (ii) Evaluate all physical methods at the same (adjusted) air flow, or show that the inconsistency is negligible.
- (iii) Add a self-consistent check for at least 2–3 sites, for example a cold one and a hot-dry one. The authors' own rating mode is suited to this, and the Outlook mentions a user-defined plant component. One way: fit a fill characteristic, $Me = c\,(L/G)^{-n}$, to the EnergyPlus tower at design. Then solve, per timestep, the air flow that meets the condenser setpoint under Poppe and under Merkel, and compare annual evaporation. This would show whether the 4–9 % gap survives when thermal and water physics are consistent.
- (iv) Explain the Stockholm/Montreal contrast.

### M4. Supersaturation, "fog" and mist: half of the cold-climate gap is liquid water, and that branch is not verified

**Issue.** The cold-climate EnergyPlus deviations (−7.9 to −9.3 %) are attributed to "supersaturated exit air carrying liquid mist". Using the supplementary timestep outputs (`AirOutT`, `AirOutW`, `AirMass`), I estimated the liquid content as $\omega_{out}-\omega_s(T_{a,out})$:

| Site | Liquid mist leaving the tower | Share of the EPSAT–Poppe gap |
|---|---|---|
| Stockholm | ~480 m³/yr | ~53 % |
| Montreal | ~480 m³/yr | ~51 % |
| Dublin | ~340 m³/yr | ~44 % |
| Phoenix | — | ~6 % |
| Singapore | — | ~4 % |

So about half of the headline "most in cold climates" result is condensed liquid that Poppe books as evaporation.

The physics of this liquid is uncertain:
- whether drift eliminators capture part of it;
- whether it re-deposits;
- whether a real fill reaches that state at all.

Further problems:
- **Not verified.** The independent BVP check (`tools/verify_poppe.py`) covers unsaturated air only, and its five cases are far from the pinch. The supersaturated branch, which drives this result, is not verified.
- **"Fog hours" are unvalidated and possibly misleading.** Up to 7,200 h/yr in Dublin, i.e. 83 % of the year, rests on an arbitrary 0.1 g/kg threshold. The authors' own documentation calls it "a reporting choice, not a visibility criterion". Calling it "fog" invites confusion with visible plume, which depends on mixing with ambient air after the tower exit.

**Why it matters.** This is the most climate-sensitive and most quotable result of the paper. Its largest component rests on the least verified part of the model.

**Requested change.**
- (i) Split Poppe evaporation into vapour and liquid. Report both per site, and the share of the EnergyPlus deviation explained by each.
- (ii) Verify the supersaturated formulation independently, for example by extending the height-wise BVP or reproducing a published supersaturated worked example (Kröger's 2004 textbook has Poppe sample calculations; please check which cases are covered).
- (iii) Discuss the fate of the mist: eliminator capture, and the evidence on Poppe in fogging conditions.
- (iv) Rename "fog hours" to "hours with supersaturated exit air (liquid > 0.1 g/kg)". Show the sensitivity of the count to the threshold, or remove it from the abstract-level results.

### M5. The case-study configuration drives the climate signal; no sensitivity analysis

**Issue.** The authors note that "whether a simplified method over- or underpredicts … depends on how close the tower operates to the pinch, not only on climate". The case study is configured in a way that keeps the tower near the pinch for much of the year:
- an N+1 tower (1.5× duty flow; all three cells share the flow);
- a fixed $T_{wb}+3.9$ K reset with an 18 °C floor;
- no water-side or air-side economiser (the supplementary model documentation says the WSE variant "is not usable yet").

In cold climates, a real data centre would normally run economisers for much of the year. This would change both the tower load and the pinch proximity. In short, the reported climate trend ("most in cold climates") is a property of this plant as much as of climate.

**Why it matters.** The abstract and conclusions generalise the climate trend.

**Requested change.** Add a sensitivity analysis on at least:
- tower sizing (N vs N+1 cells, design approach);
- condenser reset (fixed setpoint, a different floor, an optimised reset);
- if at all possible, a water-side economiser (or a non-integrated WSE).

Show how the EnergyPlus–Poppe deviation changes. Either qualify the climate conclusions as specific to this plant, or show they are robust.

Also discuss the single TMYx year. Typical years under-represent extremes, which matter for peak water demand and hybrid capacity. The Discussion argues that "hourly water matters (peak demand on a utility, drought curtailment)", so report peak-day makeup (m³/day) per site, and ideally results from a few actual years.

### M6. Chemistry results rest on placeholder data; the "as important as evaporation physics" claim is not a finding

**Issue.** In `data/water_sources.json`, the three makeup sources and the treatment limits are labelled "PLACEHOLDER VALUES … not taken from any utility report … Replace both … before publishing results". The constituent-limited cycles show that the reported range is set mechanically by these placeholders:

| Makeup source | Limiting constraint | Cycles of concentration |
|---|---|---|
| Hard groundwater | 1000/220 calcium hardness | 4.55 |
| Reclaimed water | 500/180 chloride | 2.78 |
| Soft surface water | `max_cycles` cap | 10.0 |

The −13 % end of the range is set by the 10-cycle cap. "Dynamic" mode is identical to "constituent" mode for two of the three sources at every site checked. With $B=E/(N-1)$, a spread of cycles from 2.8 to 10 gives −13/+22 % by algebra alone. The statement that makeup-water quality is "as important as the choice of evaporation physics" therefore follows from the chosen inputs; it is not a result.

Further issues:
- **pH assumption.** The LSI limit uses a fixed recirculating pH (an acid-feed setpoint) while alkalinity scales with $N$. Under acid feed, alkalinity is consumed, so these two assumptions are inconsistent.
- **Silica solubility.** The Fournier (1977) relation is a geothermometer fit, applied at 15–40 °C without confirming the calibration range.
- **LSI constants.** The empirical A–D form of $pH_s$ is still of unconfirmed origin (the authors' own `REFERENCES_CHECK.md`).

**Why it matters.** A reader cannot separate a physical result from a chosen input.

**Requested change.** Either:
- use real utility water-quality reports for the actual sites, which are public for many utilities, plus cited treatment limits; or
- recast the chemistry part as a transparent parametric analysis: makeup vs cycles of concentration, with the chemistry model as a tool for choosing $N$.

In either case:
- remove the "as important as evaporation physics" claim from the abstract and conclusions;
- resolve the pH/alkalinity inconsistency;
- justify or replace the silica relation;
- cite a confirmed source for the $pH_s$ constants, or use the Standard Methods 2330 equilibrium calculation.

### M7. Hybrid cooler: the energy baseline is invalid in hot climates, the plants are not comparable, and key assumptions are untested

**Issue.** Five problems:

- **(a) The dry baseline is not a viable plant in hot climates.** The coolers are sized for *wet* operation at the 0.4 % dry-bulb. The supplementary verification for Phoenix in dry mode shows:
  - the condenser water exceeds its setpoint by more than 0.5 K for 855 h;
  - condenser supply reaches 48.5 °C;
  - chiller leaving-condenser temperature reaches 53.9 °C, 12.8 K above the curve limit, and EnergyPlus clamps the curves there.

  Dry-mode chiller energy is therefore underestimated by an unknown and possibly large amount in hot climates. This affects ΔE, "L per kWh saved" (100–122 and 107–241 L/kWh) and the conclusion that "saving electricity with pad water is expensive". The authors say these figures "overstate the cost somewhat", but give no bound. Also, the finding that "wet operation is primarily a capacity measure" partly follows from sizing the coolers for wet operation in the first place.
- **(b) The two plants use different chillers.** The tower plant uses Carrier 19XR VSD curves (annual COP ≈ 8.7); the hybrid plant uses Trane CVHE inlet-vane curves (reference COP 5.38). Their condenser floors also differ (18 vs 23 °C). As a result, hybrid PUE is 1.31–1.35 against 1.24–1.28 for the tower, mainly because of the chiller choice. The tower-vs-hybrid comparison, which is what designers need, is therefore water-only. The ~0.07 PUE gap (~500–700 MWh/yr at this scale) is not negligible, even in water terms. At typical grid water-consumption intensities (Macknick et al., 2012, Environ. Res. Lett.), it could offset much of the hybrid's water saving in Riyadh (about 2,800 m³/yr at T28).
- **(c) Pad pressure drop is set to zero**, while the assumed cooler fan static is only ~115 Pa. Rigid-media pressure drop is of the same order. Fan energy is about one-third of the electricity "saved" by T28 in Riyadh (58 of 168 MWh), so this assumption directly biases the savings. If pads sit permanently in the airstream, the dry mode pays this drop too.
- **(d) Untested assumptions.** The finding that always-wet Riyadh uses 9 % more water than the tower depends on a design air rise of 8 K and on ε = 0.85. Both are assumptions; air flow scales as 1/ΔT. No sensitivity is shown.
- **(e) Inconsistent design air rise.** The supplementary model documentation (§6.2) still states 10 K; the code and manuscript use 8 K.

**Requested change.**
- (i) Use the same chiller curve set for both plants, or a high-lift curve set built from manufacturer data. Otherwise remove all energy comparisons.
- (ii) Exclude or bound the clamped hours, for example by extrapolating the curves with a physically based lift model to give a range.
- (iii) Implement the demand-based control mentioned in the Outlook (wet only when the setpoint cannot be held). It is the practically relevant strategy and avoids the infeasible dry baseline.
- (iv) Include pad pressure drop.
- (v) Show sensitivity to ε, design air rise and switch-over temperature.
- (vi) Report source water (site + electricity-related) alongside site WUE, or at least discuss it.
- (vii) Fix the 8/10 K inconsistency.

### M8. Verification is narrower than presented

**Issue.** The abstract highlights agreement with "an independent boundary-value solution … to <10⁻⁴ %". Three caveats apply:

- **The BVP is not fully independent.** It uses the same psychrometric functions and the same Lewis-factor function. Strictly, it verifies the change of variable and the integration, which is valuable but narrow.
- **It does not cover the regimes that matter.** It covers unsaturated air only (see M4), and five cases far from the pinch. RK4 with 10 steps is checked against 80 steps generally, but not for near-pinch timesteps where $D\to 0$. These dominate the cold-climate sites.
- **One table entry is not verification.** "Rating mode, Merkel/Poppe/e-NTU $T_{w,o}$ within 0.5 K" (Table 2) compares models; it is not code verification.

**Requested change.**
- Reproduce at least one published worked Poppe example (Kröger 2004, or Kloppers & Kröger 2005a). The paper should also resolve its own `\tbd` note on what Kloppers & Kröger actually report about evaporation differences.
- Add supersaturated and near-pinch cases.
- Show step convergence on the actual adjusted timesteps.
- Move the rating-mode comparison out of the verification table.
- Tone down the abstract sentence: precision to <10⁻⁴ % is not accuracy.

### M9. Positioning and literature are insufficient for the journal

**Issue.** Only 14 references are cited in the text. Several relevant entries are in the .bib file but never cited: Qureshi & Zubair 2006 (prediction of evaporation losses in wet cooling towers), Jaber & Webb 1989, Kröger 2004, Kloppers & Kröger 2005b (Lewis factor), CTI ATC-105.

The novelty claim ("These findings have not been carried into building energy simulation") needs support against existing work in several areas.

**Requested change.** Add and discuss at least the following. Topics and authors are listed only where I am confident. Items marked *check* must be verified by the authors.

- **Merkel / e-NTU / Poppe and evaporation.** Kloppers & Kröger (2004 R&D J.; 2005a,b,c); Qureshi & Zubair (2006 HTE; 2007 Appl. Therm. Eng. on evaporative fluid coolers, which EnergyPlus uses for its fluid-cooler loss-factor default); Jaber & Webb (1989); Sutherland (1983, J. Heat Transfer, on Merkel-assumption errors); Baker & Shryock (1961, J. Heat Transfer); Kröger (2004). Also numerical Poppe-type fill models, e.g. Klimanek & Białecki (2009) *check*.
- **Data-centre water use estimation.** Mytton (2021); Shehabi et al. (2016) and the 2024 LBNL update (Shehabi et al., 2024); Siddik, Shehabi & Marston (2021, Environ. Res. Lett.); Lei & Masanet (2022, Resour. Conserv. Recycl.), whose climate- and technology-specific PUE/WUE estimates are the closest prior work and must be compared; Li, Yang, Islam & Ren ("Making AI less thirsty", 2023) *check final venue*; Karimi et al. (2022) on data-centre water–energy trade-offs in hot-arid climates *check*; Ristic, Madani & Makuch (2015) *check*.
- **Energy-related (indirect) water.** Macknick et al. (2012, Environ. Res. Lett.), needed for M7(b).
- **Hybrid / adiabatic pre-cooling.** ASHRAE Handbook—HVAC Systems and Equipment (evaporative air cooling chapter); ANSI/ASHRAE Standard 133 (method of testing direct evaporative air coolers); studies on wetted-media pre-cooling of dry coolers and air-cooled condensers, e.g. He, Gurgenci, Guan et al. on natural-draft dry cooling towers *check*.
- **Simulation tools.** EnergyPlus `EvaporativeFluidCooler:*` objects, which are a water-side evaporative device; the Introduction's statement that EnergyPlus has "no water-side hybrid cooler" needs nuance. The Modelica Buildings Library cooling-tower models (Wetter et al., 2014, J. Build. Perf. Sim.). TRNSYS tower types *check*.
- **Measured / operator WUE.** Hyperscale operators publish fleet WUE in sustainability reports, often well below 1 L/kWh because of economisation and adiabatic cooling *check values*. These should be used to put the 1.66–2.63 L/kWh results in context. The results are for a no-economiser chilled-water plant.

### M10. The EnergyPlus "defects": evidence and framing

**Issue.** The five defects take an abstract sentence and a conclusion, but the evidence is uneven:

| Defect | Evidence / problem |
|---|---|
| (1) Idle towers book water | Reproduced, but the supplementary documents give inconsistent magnitudes: "4.5–12 m³/yr" in METHODS §8 vs 8.65 m³ in `bugreports/README.md` |
| (2) No water in free convection | Supplementary evidence is "to be added" |
| (3) Capacity fraction used as air-flow ratio | Argued qualitatively from the code, not quantified |
| (4) LossFactor 100× | Well evidenced (implied 0.2001 K⁻¹) |
| (5) Fluid-cooler air-flow autosizing | Described as ~1000×, but the authors' own physical estimate is 4.9 m³/s against 14,061 m³/s, i.e. ~2,900×. Their notes say "to be checked against the I/O Reference" |

Also, all results use EnergyPlus v22.2 (2022). The authors' own notes say the defects should be "confirmed on the latest release (26.2.0) before filing". There is no indication of upstream issue numbers, or of a check for existing reports. Unmethours users already describe the LossFactor workaround, for example.

**Why it matters.** A journal paper should not be the first public report of unconfirmed software defects. In any case, bug reports are not research findings unless they change a quantitative conclusion. Defect 4 does change one: the LF results describe the documented intent, while EnergyPlus as shipped would book ~100× more. Defects 1–3 did not occur in the case study.

**Requested change.**
- Confirm all five on the current release and file them upstream. Cite issue or PR numbers and the commit hash checked.
- Complete the evidence for (2), and quantify (3) and (5).
- Keep defect 4 in the main text, because it is needed to interpret Table 1, Fig. 3 and the LF numbers.
- Move the others to an appendix or the supplement, and remove them from the abstract.

### M11. No uncertainty or sensitivity quantification

**Issue.** All results are single deterministic numbers. Inputs that plausibly move the answer are fixed without any sensitivity shown:
- Lewis-factor model (Bošnjaković vs constant values, and fill-dependent $Le_f$; see Kloppers & Kröger 2005b);
- loss factor (the documented range is 0.15–0.27 %/K, but only 0.2 is used);
- drift fraction (0.001 % here vs the EnergyPlus default of 0.008 %);
- design approach and range;
- pad effectiveness and design air rise (M7);
- water chemistry (M6);
- weather year (M5).

**Requested change.** Add a compact one-at-a-time or global sensitivity analysis on 2–3 representative sites. Use it to give ranges, not point values, in the abstract. Report the LF results as a band over 0.15–0.27 %/K.

### M12. Reproducibility and data availability are not yet adequate

**Issue.**
- **Placeholders in the manuscript.** Repository URL, affiliation and one literature claim are still `\tbd`.
- **No licence** is given for the code.
- **Hard-coded environment.** `reproduce.sh` hard-codes an absolute interpreter path.
- **Inconsistent supplementary material:**
  - 10 K vs 8 K design air rise;
  - "four" defects in the README vs five in the paper;
  - inconsistent idle-tower magnitudes.
- **Data file warning.** The chemistry data file carries an explicit "do not publish" warning.
- **Missing equations.** The main text refers readers to `docs/METHODS.md` for equations.

**Requested change.**
- Archive the code, IDFs, weather metadata and post-processing with a DOI (e.g. Zenodo) under an explicit licence.
- Pin the environment, for example with a lock file or container that includes EnergyPlus 22.2.
- Provide the reduced timestep outputs needed to regenerate the figures, not 28 GB of raw runs.
- Make the supplementary documents consistent with the paper.
- Cite the technical reference as Supplementary Material S1, not as a repository path.
- Include the Elsevier declarations: CRediT, competing interests, funding (the README mentions an NSF CAREER context), data availability and, if applicable, use of generative AI.

---

## Minor comments

**m1. Title.** It is a question and implies measurement ("really"). See M2.

**m2. Abstract length.** The abstract is ~300 words and packs in about 15 numbers across three topics. Check the journal's limit, cut it to the main tower findings, and add the required Highlights (3–5 bullets, ≤85 characters each). Consider adding a nomenclature table.

**m3. Introduction.** "This paper makes four contributions" is followed by five items.

**m4. ROT row of Table 1.** "1 % per 10 °F range" is inconsistent with $0.00153\,\dot m_w\Delta T$. 1 %/10 °F is 0.0018 K⁻¹; 0.00153 K⁻¹ is Perry's 0.00085 °F⁻¹, i.e. 0.85 %/10 °F. Fix the text and cite Perry's Handbook (edition to be confirmed, per the authors' own reference check).

**m5. Notation clashes:**
- $D$ is used for drift, for the Poppe denominator, and for the LSI alkalinity term;
- $N$ is used for both cycles of concentration and number of cells;
- $E$ is used for both evaporation and electricity ($\Delta E_{T28}$);
- enthalpy is $i$ in the equations but $h_{fg}$ in figures and $i_{fg}$ in Table 1.

Note in the main text that $Me_P$ is defined on the local water flow; this is currently only in the supplement.

**m6. Units.** L/kWh, L/kWh$_{th}$, "L/kWh IT" and "L/kWh saved" all appear. Define each once. Write "L per kWh of facility electricity saved" explicitly.

**m7. EPSAT replica tolerance.** "0.4 % at every loaded timestep" (Section 3) vs "0.2 % at every site" (Section 6.1). State that one is per timestep and the other annual.

**m8. EPSAT replica vs EnergyPlus output.** Fig. 3 shows the EPSAT replica (Phoenix −3.8 %, Stockholm −9.2 %); the text and abstract quote EnergyPlus' own output (−3.7 %, −9.3 %). State which is plotted, or use one consistently.

**m9. Braun in the climate map.** "The Braun e-NTU model underpredicts everywhere by 3–18 %" is misleading. In `method_map.csv`, 234 of 928 grid points (25 %, cold and humid) have status CLIPPED, i.e. Braun is limited to saturated exit and equals MSAT. Over unclipped points Braun's range is −2.8 to −6.2 %. Disclose this and hatch the clipped region in Fig. 1.

**m10. Fig. 1 (method map):**
- The EnergyPlus SaturatedExit panel has a sharp, near-vertical discontinuity at dry-bulb ≈ 5–10 °C for RH ≲ 40 %. Explain it; it may come from the 4 °C water-density clamp or the saturated-at-$T_{wb}$ inlet enthalpy.
- Explain the blank upper-right region (grid limited to $T_{wb}\le 32$ °C?).
- The text mentions only the latent-only method's −32 %. It also over-predicts by up to +84 % in cold air, which should be stated.
- State clearly that a full-load tower at fixed $L/G$ at −5 °C is a thermodynamic illustration, not an operating condition.

**m11. Empirical methods.** LF, ROT and LAT are all proportional to $Q$ (or to range × flow), so their deviations follow directly from Poppe's L/kWh$_{th}$. This can be said in one sentence, freeing space.

**m12. LossFactor.** In Table 1 and the abstract, state explicitly that "LF" is the plugin's implementation of the *documented* 0.2 %/K. EnergyPlus as shipped applies 20 %/K.

**m13. In-figure titles.** Figs. 3, 6 and 8 have titles inside the graphic that duplicate the captions; remove them (Elsevier style). In Fig. 3 the colour scale saturates at ±30 % while values reach +64 %; say so in the caption.

**m14. Fig. 4 (monthly).** The February dip comes from month length. Plot m³/day or L/kWh$_{th}$ instead, or note it.

**m15. Fig. 5 (timestep deviation):**
- A distinct cluster at −8 to −10 % around 25–30 °C dry-bulb (probably the hot-humid sites) is not discussed.
- Colour or facet by site group or by status (adjusted / supersaturated), so readers can see what drives the scatter.

**m16. Fig. 6 (WUE).** The Riyadh Poppe marker is hidden behind the EnergyPlus marker. The legend says "hard groundwater"; add "(illustrative)".

**m17. Fig. 7 (hybrid trade-off):**
- Label every threshold point, not only T28 and "wet".
- Make the y-axis tick format consistent (the Riyadh panel differs).
- State in the caption that the dry baseline has clamped chiller curves (see M7).

**m18. Table 4 (sites):**
- Add the share of adjusted timesteps, the mean/max air scale, liquid-mist volume and supersaturated hours (M3, M4).
- Label the chemistry source in the caption as illustrative.

**m19. Hybrid text vs Table 5:**
- Riyadh "3,285 h" in the text vs 3,284 in the table.
- Las Vegas (2,185 h dry-mode out-of-range) is left out of the list of hot sites.
- The abstract says chillers stay "within their rated range at every site", but Houston, Singapore, Mumbai, Phoenix and Dallas still have 1–5 h.
- "100–240 L/kWh" in the abstract and conclusions merges the T28 range (100–122) and the always-wet range (107–241); give them separately.

**m20. Near-zero savings.** For Montreal, Frankfurt and Portland, ΔE_T28 is 0.03–0.08 %, i.e. 3–8 MWh/yr out of ~9,900. These are near the level of solver tolerance and convergence noise, so their L/kWh$_{saved}$ values (114–122) are ratios of near-zero quantities. Flag them or omit them.

**m21. Climate-zone labels.** State the source and version.
- With the TMYx mean dry-bulb of 26.9 °C, Riyadh's CDD10 is ≈6,100, which would place it in zone 0B under ASHRAE 169 thresholds rather than 1B (*check*).
- Phoenix (1B), Las Vegas (2B) and Dallas (2A) differ from the commonly used IECC county assignments (2B, 3B, 3A). Say that station-based assignments are used.

**m22. Wording on Merkel.** "Merkel's method neglects the Lewis factor" should read "assumes $Le_f = 1$".

**m23. Discussion, "Which method to use":**
- "Within about 10 % of Poppe" holds for annual totals only. Timestep deviations reach −29 %; say so.
- "Poppe is preferable because its error relative to saturated exit is concentrated in cold, humid hours" is circular. It assumes Poppe is right. Rephrase.

**m24. Heat balance.** Poppe's energy balance includes the enthalpy of the evaporated water, while EnergyPlus' $Q$ does not account for water loss. State how $Q$ is defined for each method in accounting mode, and how large the inconsistency is.

**m25. Lewis factor.** Cite Kloppers & Kröger (2005b), which is in the .bib but not cited. Write the coefficient as $0.865^{2/3}$, as the authors' reference check recommends.

**m26. Drift.** Justify 0.001 % against the EnergyPlus default of 0.008 %, and state that drift is negligible (~0.1 % of makeup) in all results.

**m27. Hybrid control.** "Perfect knowledge of the current dry-bulb" describes a normal reactive threshold controller on measured dry-bulb; rephrase. Also state:
- the minimum wet/dry dwell time;
- that pad flushing and dry-out are not modelled;
- that the freezing-climate coolers have no glycol and no free-convection capacity.

**m28. "Unchanged on the development branch in October 2026".** Give the commit hash.

**m29. Keywords.** Nine keywords are listed; check the journal limit.

**m30. Unresolved `\tbd` items.** Resolve the Kloppers & Kröger claim in the Introduction (line 64). The claim that Merkel/e-NTU and Poppe give similar heat rejection but different evaporation needs a precise statement and page/figure reference.

**m31. Model description.** Section 5 should state the 18 °C condenser floor's rationale and the fact that the tower runs all 8,760 h (never idles). This explains why defects 1–3 do not appear.

---

## Strongest points

1. **The accounting-mode concept.** Evaluating many evaporation models at one simulated operating point, alongside the native EnergyPlus calculation, is simple, transparent and practically useful. The line-by-line EPSAT replica, which matches EnergyPlus within 0.4 % per timestep, is a convincing check that the plugin reads the right state.
2. **A careful, tested Poppe implementation.** It includes the supersaturated branch, a Lewis-factor option, explicit status flags (clipped, adjusted, infeasible), a fallback rule, and 48 passing unit tests. Supplementary documentation records every equation and its source.
3. **A physically informative result.** Evaporation per unit heat rejected ranges from 1.05 to 1.65 L/kWh$_{th}$ across climates, against a latent-only value of ≈1.48. This shows clearly that the "all heat is latent" assumption fails in both directions.
4. **Defect 4 (LossFactor applied 100×)** is well evidenced and matters to every EnergyPlus user of that option.
5. **Honest reporting of limitations.** The authors report clamped-curve hours, the air-flow adjustment and the placeholder chemistry, and the reproduction script and repository structure are good. The problems above are mostly about framing and scope, not concealment.
6. **A useful practical message.** Hybrid wet/dry control should be set for capacity rather than energy saving, and always-wet operation in hot-dry climates can use more water than a tower. This is worth developing properly in a dedicated study.
