# Response to the round-2 review (manuscript v3 → v4)

- **Review:** `paper/REVIEW_round2.md`, an independent referee-style review by a separate agent with no access to this
  response. Recommendation: minor revision bordering on major.
- **Revised manuscript:** `paper/manuscript.tex` (v4). v3 as reviewed: `paper/manuscript_v3_before_round2_review.tex`.
- **New or changed analyses:**
  - `tools/realistic_fill_check.py` (new);
  - `tools/validate_kloppers.py` (model comparison, conditions, step check);
  - `tools/water_quality_study.py` (cap/floor flags, effective cycles, missing data);
  - `src/tower_water/evaporation.py` (Poppe convergence flag);
  - `tools/review_tables.py` (ordinary-fill row).
- **Tests:** `tests/test_round2.py`. 55 tests pass.

We agree with almost all comments. The most consequential change came from R2-M3(c) and R2-M4(e). We replaced the
EnergyPlus tower by one with an ordinary fill. This showed that the hot–dry result of v3 (EnergyPlus lower than Poppe
everywhere) belongs to the EnergyPlus tower's operating point, not to the climate. The abstract, highlights, results,
discussion and conclusions now say so.

---

## Major comments

### R2-M1. Kloppers comparison over-claimed — **accepted, all parts done**
- **(a)** The abstract now reads "on 126 measured fill tests it predicts the outlet-air temperature within 0.84 K rms,
  against 1.10 K for a saturated-exit analysis, though evaporation was not measured". Highlight 2 now reads "Poppe fits
  126 measured fill tests better than saturated-exit analysis".
- **(b)** New Table `tab:kloppermodels` (`results/study/kloppers_models_table.tex`, `results/validation/kloppers_models.csv`).
  We reproduce the reviewer's numbers:

  | Model | Outlet-air temperature | Evaporation vs Poppe |
  |---|---|---|
  | Poppe | bias −0.20 K, rms 0.84 K | — |
  | Merkel saturated exit | bias −0.75 K, rms 1.10 K | −7.2 % (−10.9 to −3.1 %) |
  | Braun | rms 1.07 K | −7.3 % |
  | Kloppers' Merkel analysis | rms 1.16 K | — |
  | EnergyPlus formulation | — | −11.2 % |

  The text states that the test favours Poppe only weakly: 0.26 K of rms difference corresponds to 7 % of evaporation.
- **(c)** The covered conditions are stated: inlet air 11.8–24.2 °C dry-bulb and 9.9–20.6 °C wet-bulb, hot water 33–53 °C,
  L/G 0.65–5.8. Every test has supersaturated exhaust under Poppe. Hot–dry air, freezing air and data-center water
  temperatures are not covered. Limitation (ii) repeats this.
- **(d)** The column is relabelled "ΔE from $T_{w,o}$ error". The text and caption say it is not an error against
  measured evaporation.
- **(e)** "With different property routines" is removed. The text now says both analyses solve the same equations, so
  this is an implementation check. Kloppers' property set is that of Kröger (2004), now cited.

### R2-M2. "Water quality matters more than the evaporation model" — **accepted**
- **(i)** `water_quality_study.py` now flags each case at the 10-cycle cap or the 1.5-cycle floor, using the majority of
  loaded time. Table `tab:waterquality` marks the cap ($^c$) and floor ($^f$) ends and adds a column for the range over
  unclamped sets. Fig. 7 labels "cap" and "floor".
  - Excluding clamped cases, the range is **−16 to +44 %**, not −17 to +125 %.
  - At Phoenix and Las Vegas the three credible sets give 2.5–3.3 cycles (+7 to +25 %).
  - The +125 % floor case is explained as non-credible operation: sulfate in the makeup is already at 209–239 mg/L
    against a 250 mg/L limit.
- **(ii)** The abstract no longer quotes −17 to +125 %. It gives −16 to +44 % "excluding the model's cycle bounds". The
  water-quality highlight was removed, so the highlights focus on the paper's question (R2-m24).
- **(iii)** Conclusion 5 now says the cycles assumption is "at least as important for simulated WUE as the evaporation
  model and multiplies its effect". "Dominates makeup uncertainty" is removed.
- **(iv)** §2.4 states that a missing constituent imposes no limit. Table 8 marks the affected sites ($^\dagger$). The text
  says the results at Portland and Madrid reflect the cap partly because of missing data.
- **(v)** The like-for-like statement now reads: cycles are an operating set-point, their effect multiplies the model
  effect, and the model changes makeup by 3.7–9.3 % at any fixed N. The "14–125 % exceeds" sentence is removed.

### R2-M3. The "fixed physical fill" check — **accepted, and (c) done with a new analysis**
- **(a)** "Physical" is removed. Design $Me_P$ and L/G are reported for all 14 sites (new Table `tab:fill`).
- **(b)** §6.3 now reports all measures:
  - heat rejected: −2.4 to +2.5 %;
  - absolute evaporation: −2.3 to +2.5 %;
  - evaporation per unit heat: at most 0.17 %.

  It explains why per-heat is the relevant measure: accounting mode imposes EnergyPlus' heat on every model. It also says
  the fixed fill inherits the near-pinch design and does not represent an ordinary tower. The abstract and Conclusion 3 no
  longer quote "≤ 0.17 %".
- **(c)** New `tools/realistic_fill_check.py`:
  - **Setup:** a tower with an ordinary fill, design L/G 1.0, 1.2 or 1.4 (design $Me_P$ 1.0–2.7), at the same design
    water flow and conditions, with $Me_P\propto(L/G)^{-0.6}$.
  - **Method:** for every loaded hour at all 14 sites, solve the air flow this tower needs to deliver EnergyPlus'
    leaving-water temperature, so heat is unchanged.
  - **Results:**
    - the ordinary tower needs 11–45 % more air;
    - its Poppe evaporation differs from the accounting value by −0.1 to +6.4 %;
    - EnergyPlus SaturatedExit at that operating point vs Poppe:
      - cool sites (Stockholm, Montreal, Dublin, Frankfurt, Portland): −9.1 to −3.4 %;
      - Madrid and the warm–humid sites: −6.0 to +3.0 %;
      - Phoenix, Las Vegas and Riyadh: **−2.0 to +10.9 %**.
  - **Consequence:** the cold-climate shortfall is robust, but in hot–dry climates the sign depends on the tower's
    air-to-water ratio. This is consistent with the full-load map, which v3 had not reconciled with the case study. The
    abstract, Highlight 4, §6.1, §6.3, Table 5 (new last row), the Discussion, Limitation (i) and Conclusion 3 are
    revised accordingly.
  - **Exclusions:** hours the ordinary tower cannot meet are excluded and reported (up to 14 % at Houston and Mumbai).

### R2-M4. Climate signal confounded with the near-pinch design point — **accepted**
- **(a)** New Table `tab:fill`: design wet-bulb, design $Me_P$ and the share of corrected hours for every site.
- **(b)** Montreal vs Stockholm: the near-pinch correction follows the **design** wet-bulb, not the winter climate.
  - Stockholm's design wet-bulb is 20.0 °C, giving a design $Me_P$ of 7.6.
  - Montreal's is 23.5 °C, giving 2.8.
  - The five corrected sites all have design wet-bulbs ≤ 21 °C and design $Me_P$ 5.4–7.6.
  - Montreal nevertheless has the same −9.3 %, which shows that the cold-climate result does not come from the
    correction.
- **(c)** Stated: the equipment-informed plant needs no correction at any site.
- **(d)** The hot–dry explanation in §6.1 is replaced.
  - Even in hours above 30 °C, EnergyPlus is 3.4 % below Poppe at Phoenix. The cause is the operating point: a median L/G
    of 1.6–1.9 at EnergyPlus' air flow, against 1.2 in the map.
  - A direct calculation at 40 °C / 21 °C wet-bulb gives +2 % at L/G = 1.2 and −5 % at L/G = 1.64.
- **(e)** Answered by the ordinary-fill check (R2-M3c): the cold-site shortfall persists (−9.1 to −3.4 %).

### R2-M5. Relative robustness — **accepted**
§6.5 now reports that the modern plant's 0.4–1.2 point change is 5 % of the base result at Singapore and a third of it at
Phoenix. It specifies what is robust: the sign and the ranking across plant variants. It also states that replacing the
tower fill changes the sign at hot–dry sites. Limitation (iii) and Conclusion 3 are reworded. "≤ 1.2 points" is removed
from the abstract.

### R2-M6. Stale statements — **accepted**
- **Introduction:** "No measured tower evaporation or makeup data are used … checked against measured fill tests where
  these allow."
- **Discussion "Interpretation":** now mentions the fill tests and their limits.
- **Limitation (ii):** restated for mild, supersaturated-exhaust conditions.

---

## Minor comments

| # | Response |
|---|---|
| m1 | Highlight 3 now reads "3.7–9.3 %" (one metric). |
| m2 | Highlight 5 reads "applies its LossFactor input as a fraction, not a percentage". Appendix: the issues "will be filed before publication". Filing a public upstream issue is left to the author, because it is an external, public action; `bugreports/` holds the reproductions. **Open for the author.** |
| m3 | Added Jaber & Webb (1989), Kröger (2004), Lucas et al. (2009) and ASHRAE Handbook HVAC Applications, water-treatment chapter (2023). `li2011control` and `pan2018cooling` were removed from the cycles sentence. The chapter number and edition of the ASHRAE entry are flagged in `docs/REFERENCES_CHECK.md`. |
| m4 | The acid-feed pH 7.5 is now stated as an assumption; `demadis2003gordian` is cited only for the raised silica limit. $LSI_{\max}=2.0$ is stated as an assumption, with 2.8 attributed to ICC. Limit sources are listed in `docs/WATER_QUALITY_SOURCES.md`, as the text says. Perry's edition and page remain unconfirmed: we have no licensed copy, and it stays flagged in `docs/REFERENCES_CHECK.md`. **Open for the author.** |
| m5 | Poppe denominator renamed $\mathcal{D}$. Nomenclature now has $B$, $D_r$, $i_{fg}$, $K$, $L/G$, $LSI$, $pH_s$ and $N_{c,\mathrm{eff}}$. |
| m6 | `validate_kloppers.py` now uses the plugin's 10 steps. The text says 20 steps change evaporation by at most 0.006 %. The summary values are unchanged. |
| m7 | Added `EvapResult.converged`. §2.2 gives the criterion (1e-8 kg/kg, six passes). 0–0.38 % of case-study timesteps reach the limit, with an evaporation error below 5e-6 relative (checked against 50 passes). A verification-table row and a test were added. |
| m8 | The 1.9 in the LSI formula is explained in one clause. The acid-feed alkalinity assumption is stated explicitly. |
| m9 | Table 8 now reports the effective annual cycles $E/(B+D_r)+1$, which reproduce the WUE. The instantaneous-response assumption is stated. |
| m10 | Tested and ruled out: quadrature, air-mass basis (dry vs moist: +4.3 %) and inlet enthalpy at saturated wet-bulb (+3.5 %). The cause is still unknown. The text explains why it cannot affect MSAT: accounting-mode MSAT uses only the energy balance and the saturated exit state. |
| m11 | 0.78 is described as the air-flow exponent of Kloppers' published film correlation and an upper bound on the fitted L/G exponents (0.51–0.60). The fitted split-law $G_a$ exponents (0.56–0.74) are stated. We kept the L/G form in the fixed-fill check because EnergyPlus water flow varies little, so L/G captures the air-flow dependence. The modern plant's UA ∝ AFR^0.7 is a UA, not a Merkel-number, exponent; the two are not expected to match. |
| m12 | The Kloppers rows were removed from the code-verification table. A convergence row was added. |
| m13 | Fig. 6 is now referenced in §6.4. |
| m14 | One basis: "the EnergyPlus default gives a WUE 3.7–9.3 % below the Poppe value". |
| m15 | "Supplies with moderate alkalinity". |
| m16 | Dallas is "low to medium" in the text, matching the table. Atlanta, Madrid and Mumbai are low. |
| m17 | Corrected: LF is +4 to +64 % at every site (above +50 % at the five coolest). Only ROT and LAT change sign. |
| m18 | Map: "−19 to +11 % (EnergyPlus' formulation −18.5 to +10.5 %, Merkel −17.5 to +11.0 %)". Abstract and Conclusion 2 updated. |
| m19 | **Confirmed.** At Montreal in the modern plant: 25 timesteps (4.2 h) at −21 to −27 °C, fans off, about 320 kW rejected, zero EnergyPlus evaporation (Poppe 1.0 m³, 0.01 % of annual). Appendix row 2 changed from "code inspection only" to "reproduced". |
| m20 | The two files use different definitions: `dc_sites.csv` is evaporation-weighted, the review file counts hours. The `dc_sites.csv` column is renamed `air_adjusted_evap_share_%` and documented in `tools/analyze.py`. Table 4 and the text use the hour share. |
| m21 | Fig. 7 now draws range ends as ticks, so single-value ranges are visible, and labels cap and floor ends. |
| m22 | The Table 5 caption says "--" variants were run only at the four sites shown. |
| m23 | Header updated to v4. The affiliation `\tbd` stays: only the author can confirm it. **Open for the author.** |
| m24 | Contributions split into 4 (case study), 5 (water quality) and 6 (LossFactor). The water-quality highlight was removed and its text tightened. Fig. 4 (monthly) and Table 2 were kept: Fig. 4 is the only place that shows the loss factor's constant seasonal profile, and Table 2 is now a short code-verification table. Both can move to the supplement at the editor's request. |

## Numerical consistency
- All MISMATCH items in the reviewer's table (rows 32, 48, 49, 50) are fixed as above.
- Rows 1 and 52 ("not verifiable from CSV") are unchanged: the BVP numbers come from `tools/verify_poppe.py`, and drift is
  recomputed in `analyze.py`.
- Row 36 (modern-plant PUE 1.24–1.28) is not in the summary CSV. It is computed from the EnergyPlus outputs by
  `models/summarize_dc_run.py`, which gives 1.240–1.280 over the 14 sites.
