# Referee report, round 2 (manuscript v3)

**Manuscript:** "Cooling tower evaporation models in building energy simulation: a verified multi-method EnergyPlus
framework and its implications for data center water use" (`paper/manuscript.tex`, v3)
**Journal:** Energy and Buildings
**Material checked:** manuscript, `references.bib`, all `\input` tables, all figures, `results/study/*.csv`,
`results/validation/*.csv`, `results/method_map/method_map.csv`, `results/archive/sens_modern_plant/summary.csv`,
`src/tower_water/{evaporation,chemistry,psychro}.py`, `tools/validate_kloppers.py`, `data/water_sources_sourced.json`,
`data/equipment/kloppers2003_fill_tests.csv`, `docs/EQUIPMENT_SPECS.md`, round-1 review and response.
Re-computations were done in a scratch session with the project environment; no repository file was changed.

---

## Summary

The paper implements eight cooling-tower evaporation models as an EnergyPlus 22.2 Python plugin. All eight are evaluated
at the EnergyPlus operating point every timestep, and makeup water is computed from a chemistry-based blowdown model.
Poppe is the reference model. The framework is applied to (i) a full-load climate map for a fixed tower and (ii) a 1 MW
water-cooled data center at 14 sites. Three things are new in v3: a comparison with 126 measured fill tests from
Kloppers (2003), sourced municipal water quality under five treatment limit sets, and an equipment-informed "modern"
plant variant. The main findings are:
- The EnergyPlus default (SaturatedExit) gives 3.7–9.3 % less annual evaporation than Poppe, or 3.5–7.6 % less against
  vapour-only Poppe.
- Site makeup-water quality changes makeup by −17 to +125 % relative to four cycles.
- The EnergyPlus `LossFactor` input is applied as a fraction rather than a percentage.

## Overall assessment

The revision is a real improvement. The paper now has one question. The model-to-model framing is mostly honest. The
mist/vapour split, the near-pinch statistics and the plant variants were the right responses to round 1. I re-derived
the Poppe equations against the code and found them consistent with Kloppers & Kröger (2005). Almost all quoted numbers
match the CSV outputs (see the consistency table at the end).

Three new v3 elements are, in my view, over-claimed or framed in a misleading way, and the abstract and highlights
depend on them:

1. **The Kloppers comparison** is presented as reproducing measured tests. It cannot discriminate between the models
   being compared. I recomputed it: a saturated-exit (Merkel) analysis of the same 126 tests reaches 1.10 K rms against
   the measured outlet-air temperature, compared with Poppe's 0.84 K, yet predicts 3–11 % (mean 7 %) less evaporation.
   All 126 tests also lie in one regime: supersaturated exhaust and mild inlet air.
2. **The "water quality matters more than the evaporation model" headline.** Both ends of its −17 to +125 % range are set
   by the model's own clamps (the 10-cycle cap and the 1.5-cycle floor), not by chemistry. The two effects it compares
   are also of different kinds.
3. **The "fixed physical fill" robustness check.** It uses design Merkel numbers of 6.5–7.6 at two of the four sites,
   which are not physical. It also normalises away an absolute evaporation change of −2.3 to +2.5 %.

None of these is fatal. They need re-framing, and two of them need small additional analyses that the authors already
have the tools for.

## Recommendation

**Minor revision bordering on major.** The modelling is sound. The remaining problems are in the framing of the
headline claims (abstract, highlights, conclusions 3 and 5) and in two analyses that should be added or re-run. I would
expect to accept after R2-M1 to R2-M4 are addressed.

---

## Major comments

### R2-M1. The Kloppers fill-test comparison is over-claimed: it does not validate evaporation, and it barely separates Poppe from the saturated-exit model it is used to judge

- **Abstract (l.24–25):** "reproduces 126 measured fill tests with an outlet-air temperature error of 0.84 K rms".
- **Highlight 2:** "verified against … 126 measured fill tests".
- **§4 (l.207–219).**

The authors correctly state that evaporation is not measured (l.214–215). The abstract and highlight still read as
validation of the reference model. I recomputed the same tests with the repository code (`merkel_saturated_exit`,
`braun_entu`, `poppe`; inlet state from `Tdb_in_C`/`Twb_in_C`):

| Model on the 126 tests | Outlet-air T bias vs measured | rms | Evaporation vs Poppe |
|---|---|---|---|
| Poppe (plugin) | −0.20 K | 0.84 K | — |
| Saturated exit (MSAT) | −0.75 K | 1.10 K | −7.2 % mean (−10.9 to −3.1 %) |
| Braun e-NTU | −0.71 K | 1.07 K | — |
| Kloppers' own Merkel column (`Ta_out_Merkel_C`) | −0.83 K | 1.16 K | — |

Three conclusions follow:

- **The test is weakly discriminating.** A 0.26 K rms improvement corresponds to a 7 % evaporation difference, which is
  the same size as the paper's headline effect. The direction favours Poppe (the Merkel bias is −0.75 K), which is
  useful evidence and should be reported. "Same as Kloppers' own analysis (0.85 K)" is an implementation check, not
  physics evidence.
- **The tests cover one regime.** Poppe predicts supersaturated exhaust in all 126 tests. Inlet air is 11.8–24.2 °C
  dry-bulb and 9.9–20.6 °C wet-bulb, hot water 33–53 °C, L/G 0.65–5.8. So the tests do not cover:
  - the hot–dry regime, where the map says saturated-exit models over-predict;
  - near-zero and sub-zero air, where the largest timestep differences (−15 to −29 %) occur;
  - data-center condenser temperatures of roughly 20–35 °C.
- **The "evaporation within ±4.4 % on average (max 11.5 %)" result (l.217; Table 3, last column) is not an error against
  data.** It is the change in Poppe evaporation caused by the n = 0.6 law's error in leaving-water temperature, relative
  to Poppe at the measured leaving-water temperature. As written ("evaporation within ±4.4 %") it reads as a measured
  error.

**Required:**
- (a) Rewrite the abstract and Highlight 2 to say that Poppe reproduces measured outlet-air temperature (0.84 K rms,
  against 1.10 K for a saturated-exit analysis), and that evaporation itself is not measured.
- (b) Add the MSAT/Braun rows above to Table 3 or the text. This turns the comparison into evidence about model choice
  rather than only about implementation.
- (c) State the range of conditions covered and that every test has supersaturated exhaust under Poppe.
- (d) Relabel the "E err." column, for example "change in predicted evaporation caused by the fill-law error in
  $T_{w,o}$", and rephrase l.217 accordingly.
- (e) Remove or rephrase "with different property routines" (l.212): both analyses solve the same Poppe equations, so
  agreement in $Me_P$ is expected. Give Kloppers' property set if it is known.

### R2-M2. "Water quality matters more than the evaporation model" rests on the model's clamps and compares unlike quantities

- **Abstract (l.31–33), Highlight 4, §6.6 (l.389–402), Conclusion 5.**

**(a) The range limits are artefacts of the model's bounds.**
- **−17 % is the 10-cycle cap.** At 10 cycles versus 4, makeup ∝ N/(N−1), and 1.111/1.333 − 1 = −16.7 %. It applies
  at every soft-water site: Portland, Madrid and Atlanta sit at exactly −17 to −17.
- **+125 % is the 1.5-cycle floor.** At 1.5 cycles makeup ∝ 3.0 versus 1.333 at four cycles, i.e. +125 %. The floor is
  reached because a 250 mg/L sulfate limit (BAC and ICC sets in `water_sources_sourced.json`) is applied to makeup water
  that already carries 209–239 mg/L. The computed allowable N is about 1.05, and the code then raises it to 1.5.
- **Neither end is an outcome of water chemistry.** The +125 % case is also not credible operation: the paper itself
  says such sites would use stainless steel, acid or side-stream treatment (l.397–398).

**(b) Missing constituents are silently non-limiting** (`chemistry.cycles_of_concentration` skips absent keys).
- Portland and Madrid have no sulfate or chloride.
- Mumbai has no sulfate.
- Stockholm, Dublin, Madrid, Riyadh and Mumbai have no silica.
- So several "10-cycle" results are partly a consequence of missing data, especially Madrid (low confidence, three of
  four constituents missing).

**(c) Corrosion limits are not modelled.** The paper concedes (l.400–401) that soft, low-alkalinity waters are
corrosion-limited, so the lower half of the range is optimistic by construction.

**(d) The two effects are different in kind.**
- The cycles of concentration are an operating set-point that the owner chooses and meters (a conductivity
  controller).
- The evaporation model is an epistemic modelling choice.
- The paper compares the envelope over five limit sets, including clamped cases, with a single-point model difference.
- The two effects are also multiplicative, not competing: the evaporation-model difference applies unchanged at any N.

**Required:**
- (i) Report the chemistry result excluding clamped cases, or show which limit sets hit the cap or floor (Table 8
  already marks "min."). Quote, for example, the median or inter-quartile range over credible limit sets.
- (ii) Remove "−17 to +125 %" from the abstract and Highlight 4, or explain in the same sentence that both ends are the
  modelled cycle cap and floor.
- (iii) Reword Conclusion 5. A supportable version: "Simulated makeup is at least as sensitive to the assumed cycles of
  concentration as to the evaporation model; site cycles (or water quality and treatment) should be stated with any
  simulated WUE." "Dominates makeup uncertainty" is not shown.
- (iv) State how missing constituents are treated, and flag the affected sites in Table 8.
- (v) Change "the largest change from using site-specific cycles (14–125 %) exceeds …" (l.398–399) to a like-for-like
  comparison.

### R2-M3. The "fixed physical fill" robustness check uses non-physical fills and normalises away a 2–2.5 % absolute effect

- **Abstract (l.29–30)** ("at most 0.17 % when Poppe is solved for a fixed physical fill"), **§6.3 (l.341–349), §6.5
  (l.376–377), Limitation (i), Conclusion 3.**
- `review_rating_check.csv` gives `Me_design` = 6.47 (Frankfurt) and 7.62 (Stockholm, which needed a further 3 % air
  increase at design). Phoenix is 2.35 and Singapore 1.56.
- Merkel numbers of 6–8 at L/G ≈ 1.6–1.7 do not describe a physical counterflow fill. The climate-map tower has
  $Me_P$ = 1.27, and Kloppers' fills span 0.4–2.5 (Fig. 2).
- These "fixed fills" therefore inherit EnergyPlus' near-pinch design point. They do not test what a physical fill
  would do. "Physical" in the abstract is incorrect.
- **The "≤ 0.17 %" refers to evaporation *per unit heat*.** The absolute fixed-fill evaporation differs from the
  accounting value by −2.3 % (Stockholm) to +1.8 % (Singapore, n = 0.6), and +2.5 % (Singapore, n = 0.78)
  (`review_rating_check_sweep.csv`, `evap_fixed_fill_vs_accounting_%`). Heat rejected differs by −2.4 to +1.8 %
  (+2.5 % at n = 0.78).
- An absolute effect of up to 2.5 % is a third to two thirds of the 3.7–9.3 % headline difference. A reader comparing
  "EnergyPlus vs Poppe" annual totals needs to see it.

**Required:**
- (a) Delete "physical" and report the design $Me_P$ and L/G per site.
- (b) State both the per-heat result (≤ 0.17 %) and the absolute evaporation and heat changes (−2.4 to +2.5 %) in
  §6.3, the abstract and Conclusion 3, and explain why per-heat is the relevant metric for the model comparison.
- (c) Preferably repeat the check with a fill of realistic $Me_P$ (e.g. the climate-map fill, or a Kloppers film fill
  scaled to the design duty).

### R2-M4. The climate signal is confounded with how close each site's tower design is to the pinch; this is not explained

- §5, §6.1, §6.3 and Table 4. The 3.9 K approach and 5.6 K range are applied at each site's own 0.4 % design wet-bulb,
  with N+1 water flow (L/G ≈ 1.6–1.8). At low design wet-bulb this design point is itself near the pinch: $Me$ 6.5–7.6
  at Frankfurt and Stockholm versus 1.6–2.4 at Singapore and Phoenix.
- Table 4 shows the near-pinch correction in 95–100 % of hours at Stockholm, Dublin and Portland, but 0 % at Montreal,
  which is equally cold. The paper does not explain why.
- In the equipment-informed plant, `ref_air_adjusted_share_%` is 0 at every site
  (`results/archive/sens_modern_plant/summary.csv`). The near-pinch regime is therefore a property of the base plant's
  UA curves and design point, not of climate.
- The sentence at l.311–313 ("the oversized tower runs at part load close to the pinch, where its exit air is near
  saturation even in dry weather") is used to explain why hot–dry sites do not show the full-load map's sign. The
  hot–dry sites (Phoenix, Las Vegas, Riyadh) have ≤ 0.23 % corrected hours, so the explanation does not fit them.

**Required:**
- (a) Add design $Me_P$ and design L/G per site to Table 4 or a supplementary table.
- (b) Explain the Montreal/Stockholm contrast.
- (c) Report that the modern plant needs no near-pinch correction at any site, and what that implies.
- (d) Give a correct explanation for the hot–dry sites, for example by showing that their annual result is dominated by
  hours with $T_{db}$ below the map's sign-change line. Fig. 6 could show this if coloured or binned by site class.
- (e) Discuss whether the cold-site results (−7.9 to −9.3 %) generalise to towers with ordinary fills.

### R2-M5. Robustness statements should be relative as well as absolute

- Abstract l.28–29 and Conclusion 3: "changes by at most 1.2 percentage points … robust to plant variants".
- At Phoenix the base result is −3.7 % and the modern plant gives −2.5 %, so 1.2 points is a 32 % relative change. At
  Singapore the change is 0.4 points (5 %).
- **Required:** say "by 0.4–1.2 points (up to a third of the difference at hot–dry sites)", or similar. Make "robust"
  specific about what is robust: the sign and ranking across sites are; the magnitude at hot–dry sites is not.

### R2-M6. Stale and contradictory statements about measured data and the scope of validation

- **Introduction l.98–99:** "Because no measured data are used, the comparisons are model-to-model." This is now false;
  measured fill data are used in §4. Revise to "no measured tower *makeup or evaporation* data are used".
- **Discussion l.433–435:** "verified against an independent solution … has not been validated against measured makeup
  water". Mention the fill tests and their limits here (see R2-M1).
- **Limitation (ii):** restate that the fill tests cover only mild, supersaturated-exhaust conditions.

---

## Minor comments

**Abstract, highlights and claims**
- **R2-m1 (Highlight 3).** "3.5–9.3 %" mixes the vapour-only lower bound (3.5 %, Phoenix) and the total upper bound
  (9.3 %), which come from different metrics. Use "3.7–9.3 % (3.5–7.6 % vapour only)" as in the abstract, or state
  "3.5–9.3 % depending on mist accounting".
- **R2-m2 (Highlight 5).** "EnergyPlus applies the LossFactor input 100 times too high". Say "as a fraction instead of a
  percentage (100-fold)". Before publication, file the issue with the EnergyPlus developers and cite the issue number.
  The appendix still says nothing has been reported.

**Introduction and Methods**
- **R2-m3 (l.82–95).** Missing key literature:
  - measured evaporation and drift-eliminator effects on tower performance, e.g. Lucas, Martínez & Viedma (2009,
    *Energy Convers. Manage.* 50, 490–497);
  - the e-NTU method of Jaber & Webb (1989, *J. Heat Transfer* 111);
  - Kröger (2004), *Air-cooled Heat Exchangers and Cooling Towers*, the standard Poppe reference;
  - ASHRAE Handbook (HVAC Applications, water treatment) or CTI guidance for cycles-of-concentration practice.

  `li2011control` (wastewater reuse) and `pan2018cooling` (thermoelectric plants) only loosely support "cycles are
  limited by scaling, corrosion and treatment" (l.180) in building towers.
- **R2-m4 (citations).**
  - `green2008perrys` carries the bib note "Edition and page UNCERTAIN, confirm in licensed copy". Confirm it or cite
    another source for the 0.00085 rule.
  - `demadis2003gordian` (a trade-magazine article) is cited for an acid-feed program at pH 7.5. The JSON says pH 7.5
    comes from a CED Engineering course.
  - The LSI$_{max}$ = 2.0 for the inhibitor programs comes from a PDHonline course (JSON description) and is not cited
    in the paper.
  - Treatment limits drive the headline result (R2-M2), so cite each limit's source in a supplementary table, and
    prefer manufacturer or standards sources over course notes.
- **R2-m5 (Nomenclature).**
  - $D$ is used both for the Poppe denominator (Eq. 2) and, as $D_r$, for drift. Rename the denominator (e.g. $\Delta$).
  - Table 1 uses $i_{fg}$, but the Nomenclature defines only $i_{fg0}$.
  - Add $B$, $LSI$, $pH_s$, $L/G$ and $K$ (BVP transfer coefficient).
- **R2-m6 (l.155 vs `validate_kloppers.py`).** The plugin uses 10 RK4 steps; the fill-test analysis uses 20
  (`N_STEPS = 20`). The difference is negligible: I find ≤ 0.007 % in evaporation. Still, say so instead of "the
  plugin's Poppe model".
- **R2-m7 (`evaporation.poppe`).** The exit-humidity fixed-point loop has `max_iter=6` and returns without a flag if it
  has not converged. Report the convergence criterion and the share of timesteps that hit the iteration limit, or add a
  status code.
- **R2-m8 (§2.4, LSI).**
  - The closed form $N_{LSI}=10^{(\ldots)/1.9}$ is correct for the code's pHs (the TDS term contributes +0.1 log N).
    Say so in one clause so readers can check the 1.9.
  - For the acid-feed set, alkalinity is still concentrated with N (JSON note), which the text calls conservative.
    State this explicitly for the acid case, which is where it matters.
- **R2-m9 (§2.4, "dynamic" mode).** N recomputed each timestep assumes the basin concentration responds instantly.
  Table 8 reports a time-mean N, but annual blowdown depends on Σ E_t/(N_t−1). Report the effective annual N, defined as
  E/(B+D_r)+1, so that table values reproduce the WUE.

**Verification (§4)**
- **R2-m10 (l.217–219).** The unexplained +2.5 to +4.3 % (mean +3.2 %) difference in the *Merkel* number against
  Kloppers is larger than the Poppe difference (+1.0 %). I checked that it is not the quadrature: four-point Chebyshev
  and 40-step Simpson both give +3.2 %. Since MSAT is one of the compared models, either resolve the cause (enthalpy
  reference, inlet air state, water-flow basis) or explain why it cannot affect the MSAT evaporation results.
- **R2-m11 (l.215–216 vs l.376–377).**
  - The fitted fill exponents are n = 0.51–0.60 in the L/G form, while the sweep uses 0.78, described as "the air-flow
    exponent of the film-fill data". The paper's own fit gives $G_a$ exponents of 0.56–0.74; 0.78 is Kloppers'
    published film correlation (`EQUIPMENT_SPECS.md` l.216).
  - An air-only exponent is not an L/G exponent. Clarify, and use the split $G_w^bG_a^c$ law directly since it is
    already fitted.
  - The modern plant's UA ∝ AFR^0.7 also does not match 0.78.
- **R2-m12 (Table 2).** The two Kloppers rows duplicate Table 3. Keep them in one place.

**Case study and results (§5–6)**
- **R2-m13 (Fig. 6, `fig:dcts`).** The figure is never referenced in the text. Reference it in §6.4 or the Discussion
  (where −29 % is quoted) or drop it.
- **R2-m14 (l.389 vs l.399).** The model effect on WUE is given twice on different bases:
  - "raises WUE by 3.9–10.3 %" is relative to EnergyPlus;
  - "3.8–9.3 %" is relative to Poppe (`water_quality_key.csv`, `model_effect_%`).

  Use one basis.
- **R2-m15 (l.393).** Mumbai (Ca 35 mg/L as CaCO$_3$) is grouped with "moderately hard supplies". Its limit is
  alkalinity, not hardness. Rephrase as "supplies with moderate alkalinity".
- **R2-m16 (l.401–402 vs Table 8).** The text lists low confidence at Atlanta, Dallas, Madrid and Mumbai, but Table 8
  gives Dallas "L–M". Make them consistent.
- **R2-m17 (Discussion l.440–441).** "Loss-factor and rule-of-thumb estimates change sign with climate". At the
  documented 0.2 %/K the LF result is positive at every site (+4 to +64 %). Only ROT (−20 to +26 %) and LAT (−11 to
  +40 %) change sign. LF exceeds +50 % only at the five coolest sites. Correct the sentence.
- **R2-m18 (§3, l.267).** The EPSAT map minimum is −18.5 % (MSAT/Braun −17.5 %). "−18" is borderline; give "−19 to
  +11 %", or state that −18 refers to Merkel/Braun.
- **R2-m19 (Appendix A, row 2).** "Not triggered in the case study, whose tower never enters free convection" holds for
  the base plant. In the modern plant, Montreal has 4.2 loaded hours with zero EnergyPlus evaporation
  (`EP_zero_evap_loaded_h`), probably the same defect. Check this and qualify the statement.
- **R2-m20 (data files).** `dc_sites.csv` (`air_adjusted_share_%`: Frankfurt 60.9, Madrid 57.7, Portland 93.9) and
  `review_mist_correction.csv` (65.8 / 65.9 / 95.1, the values in Table 4 and the text) disagree. Regenerate
  `dc_sites.csv`, or document which definition (timesteps or hours) each file uses.
- **R2-m21 (Fig. 7).** For Portland, Madrid and Atlanta the range bar collapses to a point hidden under the markers.
  Add a small marker or note for single-value ranges, and mark the cap and floor cases (R2-M2).
- **R2-m22 (Table 5).** "All sites (n)" is given only for the base and modern plants. Say in the caption that the other
  variants were run at four sites.

**Housekeeping**
- **R2-m23 (l.1).** The header comment still says "Manuscript v2". l.17 still has `\tbd{confirm affiliation}`.
- **R2-m24 (length and structure).** At about 250 abstract words, 7 figures and 8 tables the length is acceptable.
  - Contribution 4 bundles three different things: the case study, water quality and the EnergyPlus bug.
  - Fig. 4 (monthly) carries little that Table 4 and Fig. 3 do not.
  - Suggest moving Fig. 4 and Table 2 to the supplement, and keeping the water-quality material shorter and clearly
    secondary to the evaporation-model question, which is the paper's title.

---

## Numerical consistency check

Sources: `dc_sites.csv` (DS), `review_mist_correction.csv` (RM), `review_peak_lf.csv` (PK), `review_rating_check*.csv`
(RC), `review_braun_clipping.csv` (BC), `method_map.csv` (MM), `sensitivity_plant.csv` and
`archive/sens_modern_plant/summary.csv` (SP), `water_quality_key.csv` (WQ), `kloppers_overall.csv` and
`kloppers_summary.csv` (KV).

| # | Location | Quoted | Data | Status |
|---|---|---|---|---|
| 1 | Abstract, Tab. 2 | Poppe vs BVP within 0.01 % / 0.008 % | (BVP output not in results/; taken from text) | not verifiable from CSV |
| 2 | Abstract, §4, Tab. 2 | Ta,o rms 0.84 K; bias −0.20 K; Kloppers 0.85 K | KV 0.843 / −0.204 / 0.851 | OK |
| 3 | §4 | MeP +1.0 % mean, median 0.8 %, p95 2.0 %, max 8.8 % | KV 1.00 / 0.77 / 2.00 / 8.81 | OK |
| 4 | §4 | Ta,o within 0.3 K of Kloppers | KV 0.28 K | OK |
| 5 | §4 | n = 0.51–0.60 | KV 0.506–0.598 | OK |
| 6 | §4 | Tw,o rms 0.17–0.83 K; E ±4.4 % mean, max 11.5 % | KV 0.174–0.829; −4.40…+4.27; 11.54 | OK (but see R2-M1d) |
| 7 | §4 | Merkel numbers +2.5–4.3 % vs Kloppers | KV 2.46–4.30 | OK |
| 8 | Abstract, §3, Concl. 2 | Saturated exit −18 to +11 % | MM EPSAT −18.5…+10.5; MSAT −17.5…+11.0 | OK (R2-m18) |
| 9 | Abstract, §3 | Empirical −39 to +117 % | MM −39.3…+117.2 | OK |
| 10 | §3 | Braun 2.8–6.2 % less (unclipped), down to −18 %, 25 % clipped | BC −2.77…−6.15, −17.5, 25.2 % | OK |
| 11 | §3 | Lewis −4.2 to +1.8 % | MM −4.2…+1.8 | OK |
| 12 | §3 | LAT −32 to +84 % | MM −31.9…+84.0 | OK |
| 13 | §5 | mean 861 kW, 7,540 MWh/yr; PUE 1.24–1.28 | DS 7539.5 MWh (860.7 kW); 1.243–1.284 | OK |
| 14 | Abstract, §6.1, Concl. 3 | EP default −3.7 (Phoenix) to −9.3 % (Montreal, Stockholm) | DS −3.74 / −9.33 / −9.29 | OK |
| 15 | Abstract, §6.2 | Vapour-only 3.5 (Phoenix) to 7.6 % (Singapore) | RM −3.51 / −7.60 | OK |
| 16 | §6.1 | Replica within 0.2 % every site | DS max 0.20 (Singapore) | OK (at the limit) |
| 17 | §6.1 | E/Q 1.05 (Dublin, Stockholm) to 1.65 (Riyadh) | DS 1.051, 1.054, 1.654 | OK |
| 18 | §6.1 | Latent-only ≈ 1.48 L/kWh | DS·LAT 1.471–1.484 | OK (≈1.47–1.48) |
| 19 | §6.1 | Other sat-exit/e-NTU −2.2 to −7.3 % | DS MSAT −2.21…−7.26; BRAUN −3.19…−7.27 | OK |
| 20 | §6.1, §6.5 | Lewis factor 0.1–2.1 % | DS POPPE1 −0.14…−2.07 | OK |
| 21 | §6.2 | >0.1 g/kg liquid 400 h (Mumbai) to 7,200 h (Dublin) | DS fog_h 401 / 7245 | OK |
| 22 | §6.2 | Mist <0.4 % (PHX, RUH, LAS, BOM, SIN); 1.0–2.5 %; 3.1–4.9 % | RM 0.11–0.33; 0.97–2.45; 3.09–4.93 | OK |
| 23 | §6.2 | Mist ≈ half of EP difference (cold sites) | Stockholm 4.7/9.3 pts; Frankfurt 3.0/7.6 | OK (40–51 %) |
| 24 | §6.3 | Correction 66–100 % of hours at 5 sites; <0.3 % elsewhere | RM 65.8–100; Riyadh 0.23 | OK (DS disagrees, R2-m20) |
| 25 | §6.3 | Mean air factor 1.02–1.03, max 1.05 | RM 1.018–1.028; 1.05 | OK |
| 26 | §6.3 | Implied MeP median 1.6–6.2, max 78 | RM 1.58–6.16; 77.8 | OK |
| 27 | §6.3 | Design air correction 3 % at Stockholm | RC 1.03 | OK |
| 28 | §6.3 | ΔTw,out median −0.09 to +0.11 K | RC −0.090…+0.110 | OK |
| 29 | §6.3 | Heat −2.4 to +1.8 % | RC −2.36…+1.84 | OK (n = 0.6 only; +2.55 at n = 0.78) |
| 30 | §6.3 | Evaporation per heat ≤ 0.15 % | RC max 0.147 | OK |
| 31 | Abstract, §6.5, Concl. 3 | Fill-exponent sweep ≤ 0.17 % | RC sweep max 0.167 | OK (per heat; absolute up to 2.5 %, R2-M3) |
| 32 | Abstract | "fixed physical fill" | RC Me_design 6.47, 7.62 at two sites | MISMATCH in wording (R2-M3) |
| 33 | §6.4 | Peak day −1.2 to −7.2 % | PK −1.22…−7.22 | OK |
| 34 | Abstract, §6.5, Concl. 3 | Plant variants ≤ 1.2 points | SP max 1.24 (Phoenix, modern) | OK |
| 35 | §6.5, Tab. 5 | Modern plant −8.4 to −2.5 %, 0.4–1.2 pts smaller everywhere | SP −8.37…−2.50; diff 0.37–1.24 | OK |
| 36 | §6.5 | Modern plant PUE 1.24–1.28 | not in summary CSV | not checked |
| 37 | Abstract, §6.5, Concl. 4 | LF 0.15–0.27 %/K → −22 to +122 % | PK −21.7 (Riyadh) / +121.6 (Dublin) | OK |
| 38 | Tab. 4 | LF +4 to +64 % | DS 4.3–64.1 | OK |
| 39 | §6.6 | WUE +3.9–10.3 %, 1.56–2.63 → 1.72–2.74 | DS 3.89–10.29; 1.565–2.631; 1.723–2.739 | OK |
| 40 | §6.6 | Soft sites 5.7–10 cycles, −9 to −17 % | WQ 5.68–10; −8.98…−16.67 | OK |
| 41 | §6.6 | Dallas/Houston/Montreal/Mumbai −17 to +3 % | WQ −16.7…+3.45 | OK |
| 42 | §6.6 | Frankfurt 2.3–4.7 cycles, −5 to +31 % | WQ 2.34–4.71; −4.8…+31.0 | OK |
| 43 | §6.6 | Riyadh 2.1–4.1, −1 to +44 % | WQ 2.08–4.10; −0.8…+44.2 | OK |
| 44 | §6.6 | PHX/LAS sulfate 210–240 mg/L, 1.5–3.3 cycles, +7 to +125 % | WQ 209/239; 1.5–3.34; +7.0…+125 | OK (+125 = floor, R2-M2) |
| 45 | §6.6 | Largest site-specific change 14–125 % | WQ min over sites 13.7 (Dallas) | OK (rounded) |
| 46 | §6.6 | Model effect 3.8–9.3 % | WQ 3.75–9.27 (Poppe basis) | OK, but inconsistent with #39 (R2-m14) |
| 47 | Abstract, Concl. 5 | Cycles 1.5–10; −17 to +125 % | WQ | OK numerically; both ends are clamps (R2-M2) |
| 48 | Highlight 3 | 3.5–9.3 % | mixes vapour-only min and total max | MISMATCH in metric (R2-m1) |
| 49 | Discussion | LF and ROT "change sign" | LF +4…+64 at all sites | MISMATCH (R2-m17) |
| 50 | §6.6 / Tab. 8 | Low confidence: Atlanta, Dallas, Madrid, Mumbai | Tab. 8 Dallas "L–M" | MISMATCH (R2-m16) |
| 51 | §6.5 | 0.78 = "air-flow exponent of the film-fill data" | own fit Ga^0.69–0.74; 0.78 from Kloppers' correlation | Unclear (R2-m11) |
| 52 | §6.5 | Drift < 0.2 % of makeup | 0.001 % of flow vs makeup; not tabulated | not checked |

## Physics and code consistency (summary)

- **Poppe equations** (Eqs. 1–2), the supersaturated form and the Bošnjaković Lewis factor in `evaporation._derivs` and
  `lewis_bosnjakovic` match Kloppers & Kröger (2005) term by term. The local water flow
  (m_w/m_a − (ω_out − ω)) is implemented as described.
- **EPSAT** reproduces EnergyPlus' moist-air basis with inlet enthalpy at saturated wet-bulb, consistent with the
  replica claim. **MSAT** uses the dry-air basis and no evaporated-water enthalpy, as stated.
- **Braun:** NTU is back-calculated from the operating point, so in accounting mode only the exit-humidity relation
  differentiates Braun. This is worth one sentence in §2.2.
- **Chemistry:**
  - The blowdown balance and LSI closed form (factor 1.9) are correct.
  - The silica solubility is Fournier's amorphous-silica fit.
  - Missing constituents are non-limiting (R2-M2b).
  - The 1.5/10 clamps are in `TreatmentLimits` defaults (R2-M2a).
- **ROT:** 0.00085 × 1.8 = 0.153 %/K, consistent with Table 1.
