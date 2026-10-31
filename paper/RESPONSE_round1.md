# Response to review round 1

Review: `paper/REVIEW_round1.md` (independent referee-style review, recommendation: major revision).
Revised manuscript: `paper/manuscript.tex` (v2); reviewed version kept as `paper/manuscript_v1_before_review.tex`.
New analyses: `tools/review_analyses.py`, `tools/review_tables.py` → `results/study/review_*.csv`, `dc_sites_table_v2.tex`,
`sensitivity_plant_table.tex`. Unless stated otherwise, every comment was accepted.

**Why a review skill was not used:** the requested `paper-review` skill is not available on this machine (the synced
skills are docs, docx, import-memory, morning, pdf, pptx, skill-creator, xlsx). Installing an unvetted third-party
plugin unattended was not appropriate, so the review was done by an independent agent with fresh context.

## Major comments

**M1 — two or three papers in one.** *Accepted.* The hybrid dry cooler study moved to a separate draft,
`paper/hybrid/manuscript_hybrid.tex`, with all text, figures and tables kept; its open issues (M7) are listed at the top.
Only the LossFactor defect stays in the main text (§7); the other EnergyPlus issues are in Appendix A. The paper is now one
question: how much do evaporation estimates depend on the evaporation model inside building energy simulation?

**M2 — "underestimates"/"really" frame model differences as errors.** *Accepted.* The title no longer asks "how much water
… really use". Throughout, results are "gives X % less evaporation than Poppe". The introduction states that comparisons
are model-to-model and Poppe is the most complete model, not ground truth, and the Discussion opens with this.

**M3 — accounting mode not self-consistent near the pinch.** *Accepted, with new analyses.*
(a) All physical models (MSAT, BRAUN, POPPE1) are now evaluated at the same adjusted air flow as Poppe (`methods.COMMON_AIR`,
tested); EPSAT keeps EnergyPlus' air flow by design. The 14-climate study was re-run: the EnergyPlus–Poppe difference is
unchanged (it never depended on the adjustment) and MSAT/BRAUN shift by at most 0.15 points at near-pinch sites.
(b) Correction statistics are reported (Table 4 column "corr.", §6.3): 66–100 % of hours at five mild sites, mean factor
1.02–1.03, max 1.05, below 0.3 % of hours elsewhere; implied $Me_P$ median 1.6–6.2, max 78.
(c) A fixed-fill rating check (§6.3): Poppe solved for a fixed fill ($Me_P$ from the tower design point,
$Me_P\propto(L/G)^{-0.6}$) at EnergyPlus' inlet conditions for every loaded hour at four sites. Cold-water temperature differs
by −0.09 to +0.11 K (median), heat by −2.4 to +1.8 %, and evaporation per unit heat by ≤ 0.15 %. The conclusions therefore
do not depend on how EnergyPlus' tower reaches its operating point. The fill exponent is stated as an assumption.

**M4 — liquid mist drives half of the cold-climate result; supersaturated branch unverified.** *Accepted; the reviewer's
estimate was correct.* Poppe evaporation is now split into vapour and mist (§6.2, Table 4): mist is 3.1–4.9 % of Poppe
evaporation at the four coldest sites and about half of the EnergyPlus difference there. Against vapour-only Poppe the
EnergyPlus default is 3.5–7.6 % lower; both bounds are reported, and the abstract and conclusions give the range.
"Fog hours" are no longer a result; supersaturated hours are described with their liquid threshold. The supersaturated
branch is now verified (see M8).

**M5 — results reflect the chosen plant and one weather year.** *Accepted in part.* New plant variants at four sites
(Table 5): tower sized for duty instead of N+1, condenser floor 15 °C instead of 18 °C, and both. The difference changes by
at most 1.2 points. Peak-day results added (§6.4: −1.2 to −7.2 %). *Not done:* multi-year weather (only one typical year
per site is on hand), which is stated as a limitation. A water-side economizer variant was not added because it did not
give physical results in the earlier model work (`models/DATACENTER_MODEL.md`); it is acknowledged in §5.

**M6 — chemistry results come from placeholder data; pH/alkalinity inconsistency.** *Accepted.* Headline results now use
EnergyPlus' fixed four cycles; the "as important as evaporation physics" claim was removed; chemistry is shown only as a
labelled demonstration (§6.6, Fig. 7 caption), and the 10-cycle cap is named. The LSI limit is described as assuming a
controlled pH without alkalinity reduction by acid feed, which makes it conservative; this is the inconsistency the reviewer
noted, and it is now stated rather than hidden. Real makeup data remain an open item.

**M7 — hybrid cooler weaknesses.** *Accepted; moved with the hybrid study (M1).* All five points (dry baseline cannot hold
setpoint, clamped chiller curves up to 12.8 K beyond range, different chillers between plants, zero pad pressure drop and
untested ε and air-rise assumptions, unreliable L/kWh-saved ratios at tiny savings) are listed as required work at the top of
`paper/hybrid/manuscript_hybrid.tex`. The hybrid results will not be published until these are addressed.

**M8 — verification narrower than claimed.** *Partly accepted.* The independent BVP now includes the supersaturated state
and two near-pinch cases ($Me_P\approx4$, exhaust supersaturated): evaporation agrees within 0.008 %, $Me_P$ within 0.003 %
(40 steps; 10 steps give 0.5 % error in $Me_P$ near the pinch but 0.003 % in evaporation). A supersaturated energy- and
mass-closure unit test was added. §4 now states that both formulations share the property functions. *Not done:* reproducing
a published worked example; the Kröger (2004) and Kloppers & Kröger (2005) texts are paywalled and were not accessible
here. Marked `[TBD]` in §4.

**M9 — thin literature.** *Accepted.* 20 references were found and verified against Crossref/doi.org
(`paper/LITERATURE_ADDITIONS.md`). The introduction now cites data-center water studies (Shehabi 2024, Siddik 2021,
Lei & Masanet 2022, Ristic 2015, Li 2025, Karimi 2022/2025), the closest simulation work (Powers 2016, SimBuild), further
Poppe/Merkel/Lewis work (Klimanek & Białecki 2009, Khan & Zubair 2001, Navarro 2022, Qureshi & Zubair 2006) and blowdown
practice (Li 2011, Altman 2012, Pan 2018, Soliman 2022). Hybrid-cooler references (Asvapoositkul 2014, He 2014,
Alkhedhair 2013, Ndukaife 2019, Yang 2020) are reserved for the companion paper. 37 references are cited (was 14).

**M10 — EnergyPlus defects unevenly evidenced.** *Accepted.* Only the LossFactor defect, which is reproduced by simulation,
is in the main text (§7). The others are in Appendix A with their evidence status (reproduced / code inspection only / not
triggered in the case study). The fluid-cooler wording is corrected to "about 2,900 times a physical value at a 10 K air rise"
("about three orders of magnitude" in the documentation). The paper states that none has been confirmed on v26.2 or filed.

**M11 — no uncertainty or sensitivity analysis.** *Accepted.* §6.5 adds plant variants, the documented loss-factor range
(0.15–0.27 %/K → −22 to +122 %), the Lewis factor (0.1–2.1 %) and drift (< 0.2 % of makeup). *Not done:* a formal Monte-Carlo
analysis and weather-year variability; the dominant structural uncertainty (vapour vs mist) is given as a range instead.

**M12 — reproducibility gaps.** *Mostly accepted.* `reproduce.sh` no longer hard-codes the interpreter (`PY`, `EPLUS`
environment variables); the EnergyPlus build hash is given (§5); the 8 K vs 10 K inconsistency in `models/DATACENTER_MODEL.md`
is fixed and flagged; the defect count is consistent. Repository URL and licence remain `[TBD]`: the repository could not be
created automatically, and the licence is the author's decision.

## Minor comments

| ID | Action |
|---|---|
| m1 | Title rewritten (no overclaim). |
| m2 | Abstract cut to ~226 words; Highlights and a Nomenclature table added. |
| m3 | Contributions list now matches (four items). |
| m4 | ROT row corrected: 0.153 %/K = 0.85 % per 10 °F. |
| m5 | Nomenclature added; drift is $D_r$, cycles $N_c$; enthalpy is $i$ throughout. |
| m6 | Units defined in §2.4 and Nomenclature (L/kWh$_{th}$, L/kWh$_{IT}$). |
| m7 | Replica tolerance stated once: annual, 0.2 %, every site. |
| m8 | Fig. 3 caption and text distinguish the replica from EnergyPlus output. |
| m9 | Braun clipping disclosed (25 % of map points) with the unclipped range (−2.8 to −6.2 %). |
| m10 | Map caption explains the step (EnergyPlus ice/water saturation switch at 0 °C wet-bulb) and the blank region; +84 % latent-only now in the text. |
| m11 | Empirical results kept but discussed together in one paragraph. |
| m12 | "LF as documented (0.2 %/K)" stated in Table 1, §7 and Fig. 4 caption. |
| m13 | Figure titles removed. The heatmap scale stays at ±30 % so the physical models remain readable; values are printed and the caption says the scale is limited. |
| m14 | Monthly plot now shows mean daily evaporation, so month length no longer causes a February dip. |
| m15 | Caption explains the low cluster (freezing hours with supersaturated Poppe exhaust). Colouring by site was not added: 14 categories exceed what can be told apart in a scatter. |
| m16–m17, m19–m20, m27 | Hybrid figures, numbers and control description moved to the companion draft; listed there. |
| m18 | Table 4 adds mist share, vapour-only difference and correction share. |
| m21 | Climate zones are from the weather files' ASHRAE 169-2021 design conditions (source now stated). Riyadh is listed as 1B in that file; the reviewer's "0B" is marked "check" in the review and was not adopted without evidence. |
| m22 | Wording: Merkel "sets the Lewis factor to one". |
| m23 | "Which model to use" rewritten, no longer circular; cites the −29 % timestep differences. |
| m24 | $\dot Q$ is defined in the Nomenclature as EnergyPlus' $\dot m_{w,i}c_{pw}\Delta T$; Poppe's air-side balance includes the evaporated water's enthalpy (docs/METHODS.md §3.6). |
| m25 | Kloppers & Kröger (2005b) Lewis-factor paper now cited. |
| m26 | Drift 0.001 % stated as a modern-eliminator assumption; its share of makeup (< 0.2 %) reported. |
| m28 | EnergyPlus 22.2.0 build c249759bad stated. |
| m29 | Six keywords. |
| m30 | The unfinished Kloppers & Kröger claim was replaced by what the cited papers support; specific magnitudes were not quoted because the full texts were not accessible. |
| m31 | 18 °C floor explained (chiller minimum condenser temperature); the tower never idles or enters free convection, stated in §5. |

## Remaining open items (cannot be done without the author or external data)
1. Affiliation, repository URL, licence.
2. Published worked example for Poppe (Kröger 2004 / Kloppers & Kröger 2005).
3. Measured validation (manufacturer tables, metered makeup and blowdown).
4. Real makeup water quality and treatment limits.
5. Confirm and file the EnergyPlus issues on v26.2.
