# Makeup-water quality and treatment limits: sources

This file documents `data/water_sources_sourced.json`, which replaces the placeholder library `data/water_sources.json`. It covers sourced makeup-water chemistry for the 14 study sites and citable recirculating-water limit sets for cooling towers. Compiled 2026-10-31.

**Units.** Concentrations are mg/L. Hardness and alkalinity are expressed as CaCO3, and silica as SiO2.

**Conversions used:**
- Ca hardness = Ca × 2.497
- Alkalinity = HCO3 × 0.82
- German alkalinity: Säurekapazität K_S4.3 (mmol/L) × 50, or carbonate hardness °dH × 17.85
- SiO2 = Si × 2.139
- TDS = conductivity (µS/cm) × 0.65, used only where TDS itself is not reported

**Reading the tables.**
- *est.* marks an estimate rather than a measured value. Its basis is given in the notes.
- `null` (shown as —) means not reported or not found. The model then skips that constraint.
- In the JSON, each site carries an `estimated` list naming its estimated keys.

**Data quality.** Where a utility's consumer confidence report (CCR) reports only regulated contaminants, which is the case for Atlanta and Dallas, I used USGS NWIS source-water medians from the Water Quality Portal instead. Each table states this. Those are raw-water values. Treated water usually has somewhat higher Ca and alkalinity (from lime or caustic dosing) and higher sulfate (from alum or ferric sulfate coagulant).

## 1. Makeup water by site

### Atlanta, GA (`atlanta`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 8.1 | mg/L as CaCO3 |
| M-alkalinity | 11.5 | mg/L as CaCO3 |
| Silica | 6.0 | mg/L as SiO2 |
| Chloride | 3.3 | mg/L |
| Sulfate | 3.9 | mg/L |
| TDS | 49.4 | mg/L |
| pH | — | – |

- **Source / notes:** Atlanta DWM (Chattahoochee R.). Utility CCR 2025 has no mineral data; values are USGS NWIS raw-river medians at 02336000 Chattahoochee R. at Atlanta (Ca, alk, SiO2, Cl, SO4: 1995-2009, n=2); TDS = median specific conductance 2010-2024 (76 uS/cm, n=306) x 0.65. Treated water is likely somewhat higher in Ca/alkalinity (lime/caustic) and sulfate (coagulant).
- **Year:** 1995-2024
- **URL:** https://www.waterqualitydata.us/data/Result/search?siteid=USGS-02336000
- **Confidence:** low (raw river, sparse major-ion samples)

### Dallas, TX (`dallas`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 104.9 | mg/L as CaCO3 |
| M-alkalinity | 110.0 | mg/L as CaCO3 |
| Silica | 3.9 | mg/L as SiO2 |
| Chloride | 20.0 | mg/L |
| Sulfate | 33.0 | mg/L |
| TDS | 198.0 | mg/L |
| pH | — | – |

- **Source / notes:** Dallas Water Utilities (Elm Fork Trinity / Lewisville, Ray Roberts, Grapevine, Ray Hubbard, Tawakoni). DWU 2025 CCR has no mineral data; values are USGS NWIS raw-water medians at 08053000 Elm Fork Trinity R. nr Lewisville, 1985-1997 (n~70). Alternative East Fork (Ray Hubbard, 08061750): Ca 51.5, alk 115, SiO2 7.9, Cl 45, SO4 51, TDS 302.
- **Year:** 1985-1997
- **URL:** https://www.waterqualitydata.us/data/Result/search?siteid=USGS-08053000
- **Confidence:** low-medium (raw source water, dated)

### Houston, TX (`houston`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 97.4 | mg/L as CaCO3 |
| M-alkalinity | 95.0 | mg/L as CaCO3 |
| Silica | 6.6 | mg/L as SiO2 |
| Chloride | 38.4 | mg/L |
| Sulfate | 20.8 | mg/L |
| TDS | 260.0 | mg/L |
| pH | 7.8 | – |

- **Source / notes:** City of Houston Main System (~90% surface water, Lake Houston/Trinity). Cl, SO4, TDS, pH = 2025 CCR averages (total hardness avg 135.5, range 43.5-229). Ca hardness, alkalinity, SiO2 not in CCR -> USGS NWIS medians at 08066500 Trinity R. at Romayor 1985-1995 (Ca 39 mg/L x 2.497).
- **Year:** 2025 (Ca/alk/SiO2: USGS 1985-1995)
- **URL:** https://www.houstonpublicworks.org/sites/g/files/nwywnm456/files/doc/003_2025_houston_water_quality_report.pdf ; https://www.waterqualitydata.us/data/Result/search?siteid=USGS-08066500
- **Confidence:** medium

### Las Vegas, NV (`las_vegas`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 187.3 | mg/L as CaCO3 |
| M-alkalinity | 112.3 | mg/L as CaCO3 |
| Silica | 8.3 | mg/L as SiO2 |
| Chloride | 98.6 | mg/L |
| Sulfate | 209.0 | mg/L |
| TDS | 591.0 | mg/L |
| pH | 7.8 | – |

- **Source / notes:** LVVWD (Lake Mead / Colorado R.) 2026 Water Quality Summary annual averages. Ca 75 mg/L x 2.497; alkalinity 137 mg/L as HCO3 x 0.82. 2024 summary: Ca 79, Cl 104, SiO2 7.6, SO4 235, TDS 642.
- **Year:** 2026 summary
- **URL:** https://www.lvvwd.com/assets/pdf/water-quality-summary-las-vegas-valley.pdf
- **Confidence:** high

### Phoenix, AZ (`phoenix_tmyx`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 188.5 | mg/L as CaCO3 |
| M-alkalinity | 132.0 | mg/L as CaCO3 |
| Silica | 8.0 | mg/L as SiO2 |
| Chloride | 89.8 | mg/L |
| Sulfate | 239.0 | mg/L |
| TDS | 623.0 | mg/L |
| pH | 8.2 | – |

- **Source / notes:** Phoenix, CAP (Colorado R.) supply assumed for a data center (west/north Phoenix plants). USGS NWIS medians at 09427520 Colorado R. below Parker Dam (CAP intake reach), 2005-2023 (n~50; SiO2 n=4). Consistent with City of Phoenix 2025 CCR distribution ranges: total hardness 172-302, alkalinity 121-167, TDS 464-716, pH 6.6-8.8. Alternative SRP Salt/Verde water: higher Na/Cl and TDS (up to ~700), not quantified.
- **Year:** 2005-2023 (USGS); 2025 (city CCR ranges)
- **URL:** https://www.waterqualitydata.us/data/Result/search?siteid=USGS-09427520 ; https://www.phoenix.gov/waterqualityreport
- **Confidence:** medium-high

### Portland, OR (`portland_or`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 4.7 | mg/L as CaCO3 |
| M-alkalinity | 29.0 | mg/L as CaCO3 |
| Silica | 8.1 | mg/L as SiO2 |
| Chloride | — | mg/L |
| Sulfate | — | mg/L |
| TDS | 60.0 | mg/L |
| pH | 8.8 | – |

- **Source / notes:** Portland Water Bureau, 100% Bull Run (test-results page, updated Jul 2026). Total hardness 7; Ca ~1.9 mg/L x 2.497 (unconfirmed secondary table); silica 3.8 mg/L as Si x 2.139. Cl and SO4 not reported. Alternative Columbia South Shore groundwater: hardness 68, alk 91, SiO2 40.6 (19 as Si), TDS 125, pH 8.2.
- **Year:** 2025-2026
- **URL:** https://www.portland.gov/water/drinking-water-quality/about-drinking-water-quality/test-results
- **Confidence:** high (Ca medium)

### Montréal, QC (`montreal`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 77.2 | mg/L as CaCO3 |
| M-alkalinity | 93.0 | mg/L as CaCO3 |
| Silica | 1.07 | mg/L as SiO2 |
| Chloride | 25.8 | mg/L |
| Sulfate | 21.5 | mg/L |
| TDS | 198.9 | mg/L |
| pH | 7.78 | – |

- **Source / notes:** Ville de Montreal (Atwater + Charles-J.-Des Baillets, St. Lawrence), distributed water 2022 annual mean (min-max): Ca 30.9 (28-33) mg/L x 2.497; alkalinity 93 (87-96); SiO2 1.07; Cl 25.8; SO4 21.5; conductivity 306 uS/cm; LSI -0.46. TDS = conductivity x 0.65 (report 'solides totaux' 146, 'solides fixes' 180 are inconsistent).
- **Year:** 2022
- **URL:** https://portail-m4s.s3.montreal.ca/pdf/2022_rapport_annuel_montreal_montreal_ouest_et_mont-royal.pdf
- **Confidence:** high

### Dublin, IE (`dublin`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 47.4 | mg/L as CaCO3 |
| M-alkalinity | 28.0 | mg/L as CaCO3 |
| Silica | — | mg/L as SiO2 |
| Chloride | 25.0 | mg/L |
| Sulfate | 35.0 | mg/L |
| TDS | 95.0 | mg/L |
| pH | 8.0 | – |

- **Source / notes:** Uisce Eireann Ballymore Eustace (Liffey) supply, largest Dublin source; parameter guide values (dlrcoco 2013): Ca 18-20 mg/L (x 2.497 -> 45-50), total hardness 55, alkalinity 28, Cl <25, SO4 <35 (upper bounds used), TDS 95, pH 7.5-8.5. Silica not reported. Alternative Leixlip (harder; Ca hardness 100-250, alk 70-200; low-confidence council replies).
- **Year:** 2013
- **URL:** https://dlrcoco.ie/sites/default/files/atoms/files/parameter_guide_values_vartry_2013.pdf
- **Confidence:** medium (guide values; Cl/SO4 are upper bounds)

### Frankfurt, DE (`frankfurt`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 169.8 | mg/L as CaCO3 |
| M-alkalinity | 171.0 (est.) | mg/L as CaCO3 |
| Silica | 18.2 | mg/L as SiO2 |
| Chloride | 21.5 (est.) | mg/L |
| Sulfate | 44.8 | mg/L |
| TDS | 310.8 (est.) | mg/L |
| pH | 7.7 | – |

- **Source / notes:** Mainova/Hessenwasser Frankfurt: blend of soft (Vogelsberg/Spessart) and hard (Hessisches Ried) waters. Ca 68.0 and SO4 44.8 = 2019 city-wide annual means (Ca x 2.497). Alkalinity, Cl, TDS, pH = linear mix of 2018 Innenstadt soft/hard analyses with hard fraction 0.56 implied by the Ca mean (soft: Ks4.3 1.0-1.6 mmol/L, Cl 8, cond 194; hard: Ks4.3 5.1 mmol/L, Cl 32, cond 703 uS/cm); alkalinity = Ks4.3 x 50; TDS = cond x 0.65. SiO2 ~18 in both waters (reported as SiO2).
- **Year:** 2018-2019
- **URL:** https://www.mainova.de/resource/blob/65874/f0e73743b4d24d00b065dc6042901655/jahresmittelwerte-trinkwasseranalysen-mainova-2019-data.pdf ; https://www.mainova.de/resource/blob/35310/d00ef76d46d72327dae8e121a5496e4d/inn-analysenbericht-trinkwasser-innenstadt-stand-2018-data.pdf
- **Confidence:** medium (zone-dependent; alk/Cl/TDS by mixing inference)

### Madrid, ES (`madrid`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 40.0 (est.) | mg/L as CaCO3 |
| M-alkalinity | 40.0 (est.) | mg/L as CaCO3 |
| Silica | — | mg/L as SiO2 |
| Chloride | — | mg/L |
| Sulfate | — | mg/L |
| TDS | 90.0 (est.) | mg/L |
| pH | 7.8 | – |

- **Source / notes:** Canal de Isabel II (Sierra granite reservoirs; very soft, low conductivity per Ayuntamiento de Madrid). No utility table found. Ca 16 mg/L (x 2.497), total hardness 55, TDS ~90 from tapwaterscan.com (secondary, uncited, updated 2026). Alkalinity ESTIMATE = 40 mg/L as CaCO3 (assumed ~ Ca+Mg hardness for Ca-HCO3 granite water; no source). SiO2, Cl, SO4 not found.
- **Year:** n/a (page 2026)
- **URL:** https://tapwaterscan.com/madrid
- **Confidence:** low

### Stockholm, SE (`stockholm`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 64.9 | mg/L as CaCO3 |
| M-alkalinity | 45.1 | mg/L as CaCO3 |
| Silica | — | mg/L as SiO2 |
| Chloride | 16.0 | mg/L |
| Sulfate | 44.0 | mg/L |
| TDS | 162.5 | mg/L |
| pH | 8.2 | – |

- **Source / notes:** Stockholm Vatten och Avfall, Norsborg (Lake Malaren), 2024 annual averages at Haninge receiving point: Ca 26 mg/L x 2.497; total hardness 4.7 dH (84 as CaCO3); Cl 16; SO4 44; conductivity 25 mS/m -> TDS x 0.65; pH 8.2. Alkalinity ~55 mg/L HCO3 x 0.82 (2019 declaration). Silica not reported. Lovo plant (same lake) assumed similar.
- **Year:** 2024 (alk 2019)
- **URL:** https://haninge.se/siteassets/bygga-bo-och-miljo/vatten-och-avlopp/dokument-va/norsborgs-vattenverk-2024.pdf
- **Confidence:** medium-high

### Riyadh, SA (`riyadh`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 146.4 | mg/L as CaCO3 |
| M-alkalinity | 80.0 (est.) | mg/L as CaCO3 |
| Silica | — | mg/L as SiO2 |
| Chloride | 120.0 | mg/L |
| Sulfate | 88.5 | mg/L |
| TDS | 395.6 | mg/L |
| pH | 7.88 | – |

- **Source / notes:** Riyadh distribution network (desalinated Jubail water ~2/3 blended with treated groundwater ~1/3). Ca 58.6, Cl 120, SO4 88.5, TDS 396, pH 7.88 = means of 15 network sites sampled 2020, Aleid et al. (2023) Arabian J. Chem. 17:105431 (Ca x 2.497). Alkalinity not reported: ESTIMATE 80 mg/L as CaCO3 = upper end of SWA mandated desal-water range 50-80 (Fellows & Al-Hamzah 2026, Table 2); blend may be higher. Silica not reported.
- **Year:** 2020 sampling (pub. 2023)
- **URL:** https://doi.org/10.1016/j.arabjc.2023.105431
- **Confidence:** medium (academic, not utility; alkalinity estimated)

### Mumbai, IN (`mumbai`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 35.0 (est.) | mg/L as CaCO3 |
| M-alkalinity | 97.3 | mg/L as CaCO3 |
| Silica | — | mg/L as SiO2 |
| Chloride | 9.5 | mg/L |
| Sulfate | — | mg/L |
| TDS | 120.0 (est.) | mg/L |
| pH | 7.3 | – |

- **Source / notes:** MCGM/BMC (Vaitarna, Bhatsa, Tansa reservoirs; Bhandup/Panjrapur WTPs). No utility ion data found. Total hardness 46.8 (soft), alkalinity 97.3, Cl 9.5, pH 7.0-7.5 from an MSc study of Mumbai tap water (academia.edu, read via search snippet only). Ca hardness ESTIMATE = 0.75 x total hardness. TDS ESTIMATE 120 (no source; 2019 BIS survey: all Mumbai samples met IS 10500, i.e. TDS <500). SiO2, SO4 not found.
- **Year:** unknown
- **URL:** https://www.academia.edu/32312303/ANALYSIS_OF_WATER_FOR_LEAD_pH_ALKALINITY_HARDNESS_AND_CHLORIDE_CONTENT_FROM_DIFFERENT_PARTS_OF_MUMBAI_The_Degree_of_Master_of_Science_By_Papers_In_Biochemistry
- **Confidence:** low

### Singapore (`singapore`)

| Constituent | Value | Unit |
|---|---|---|
| Ca hardness | 38.7 | mg/L as CaCO3 |
| M-alkalinity | 35.0 | mg/L as CaCO3 |
| Silica | 1.23 | mg/L as SiO2 |
| Chloride | 30.0 | mg/L |
| Sulfate | 7.2 | mg/L |
| TDS | 116.0 | mg/L |
| pH | 8.0 | – |

- **Source / notes:** PUB potable water (waterworks + desalination), Jan-Dec 2025 averages (ranges): Ca 15.5 (2.8-74.6) mg/L x 2.497; total hardness 42.7; alkalinity 35 (7-68); SiO2 1.23 (0.17-7.4); Cl 30 (<5-167); SO4 7.2; TDS 116 (63-542); pH 8.0 (7.5-8.9). Alternative: NEWater (industrial; Ca <20, hardness <50, Cl <20, SiO2 <3 upper limits).
- **Year:** 2025
- **URL:** https://www.pub.gov.sg/-/media/PUB/PDF/SG-Drinking-Water-Quality.pdf
- **Confidence:** high

## 2. Treatment limit sets

Values are recirculating-water maxima. In the JSON, `tds` is conductivity × 0.65 wherever the source gives conductivity instead of TDS.

| Set (JSON key) | SiO2 | Ca hardness | M-alk | Cl | SO4 | TDS | pH | LSI max | Max N | Source (page/section) |
|---|---|---|---|---|---|---|---|---|---|---|
| `evapco_galvanized_inhibitor`: conventional inhibitor, no acid, G-235 galvanized | 150 | 500 (min 50) | 400 (min 75) | 300 | — | 1560 (cond. 2400) | 7.0–8.8 (8.5 assumed) | 2.0 | 10 | EVAPCO *O&M Instructions, Induced/Forced Draft Towers* TWR19AOM (10/2019) p.18, Table 3 "Recommended Water Chemistry Guidelines"; LSI 2.0 for polyacrylate/phosphonate from Bhatia, PDHonline M324 *Cooling Water Treatment* p.11 |
| `icc_advanced_inhibitor`: modern stabilizer, no acid, galvanized at ≤43.3 °C | 150 | 800 | 500 | 300 | 250 | 2600 (cond. 4000) | 8.5 assumed | 2.8 | 10 | ICC 2014 Committee Action Hearings, GEW174-14 (D. Cline, EVAPCO), proposed IgCC Table 703.7.7. This was a proposal, not adopted code. |
| `acid_feed_ph7p5`: acid feed, pH held at 7.5, plus stabilizer | 200 | 800 | n/a (destroyed by acid) | 300 | n/a | 2600 | 7.5 | 2.8 | 10 | SiO2 ≤200 at pH <7.5: Demadis, "Water Treatment's Gordian Knot", *Chemical Processing* (2003). Ca, Cl, conductivity, LSI: ICC GEW174-14. pH 7–8: CED Engineering *An Introduction to Cooling Tower Water Treatment*. |
| `bac_galvanized`: BAC galvanized | 150 (EVAPCO; BAC gives none) | 600 (BAC limit is *total* hardness) | 500 | 250 | 250 (or Cl+SO4 ≤500) | 1500 (cond. 2400) | 6.5–9.0 (8.5 assumed) | 2.0 | 10 | BAC *Baltibond* product sheet PRD1201v04EN p.2, "Circulating water quality guidelines", galvanized column |
| `evapco_stainless316`: 316 stainless steel | 150 | 600 | 600 | 2000 | — | 3250 (cond. 5000) | 6.0–9.5 (8.5 assumed) | 2.8 | 10 | EVAPCO TWR19AOM Table 3, 316 SS column; LSI from ICC |

URLs:
- EVAPCO: https://www.evapco.com/sites/evapco.com/files/2019-10/O&M-TWR19AOM-10.2019.pdf. A search summary says the 2026 edition (TWR26OM_7_2026.pdf) has the same Ca, Cl and SiO2 values; that edition was not read.
- ICC: https://www.iccsafe.org/wp-content/uploads/GEW174.pdf
- BAC: https://www.BaltimoreAircoil.eu/sites/default/files/uploads/media/document/BAC_Baltibond_PRD1201v04EN.pdf
- Bhatia: https://pdhonline.com/courses/m324/m324content.pdf
- Demadis: https://www.chemicalprocessing.com/articles/2003/235
- FEMP BMP #10: https://www.energy.gov/node/849241

**Other citable statements:**
- EVAPCO 304 SS column: Ca <600, alkalinity <600, Cl <500, SiO2 <150, conductivity <4000.
- BAC 304L / Baltibond: total hardness 70–750, alkalinity ≤600, TDS ≤2050, Cl ≤300, SO4 ≤350, with Cl+SO4 ≤650.
- EVAPCO, on passivation (first 6–12 weeks): pH ≤8.3, Ca hardness ≥50, Cl or SO4 ≤250, alkalinity ≤300. EVAPCO "does not recommend the routine use of acid", but permits automated, pre-diluted acid feed.
- Bhatia (PDHonline M324, p.11): "polyacrylate and phosphonate can be utilized if the … LSI … does not exceed 2.0. Cycled cooling water SI values up to 3.5 can be obtained by use of co- and terpolymers … scale free at cycled LSI values from 2.5 to 3.5 without pH adjustment." This is the citable support for LSI of about 2.5–3.5 with modern stabilizers.
- Demadis (2003): keep silica below 200 ppm at pH <7.5 and below 100 ppm at pH >7.5. Above pH 8.5 magnesium silicate is the concern.
- Mg × SiO2 product rule: US Patent 6,645,384 cites "the maximum value of 20,000 repeatedly noted in the literature", with Mg as CaCO3 × SiO2 in ppm (unit convention assumed). I found no source for the often-quoted 35,000–40,000. The rule is **not** included in the JSON because the library has no Mg constituent.
- Typical achievable cycles, from FEMP BMP #10: "Many systems operate at two to four cycles of concentration, while six cycles or more may be possible."

**Modelling caveats for the acid-feed set:**
- `chemistry.py` scales alkalinity by N inside the LSI calculation. Under acid feed, alkalinity is held down, so the computed LSI is conservative, meaning too high.
- Sulfate added by H2SO4 dosing is not tracked, so no sulfate limit is applied.
- With pH held at 7.5 the LSI limit seldom binds.

**`ph_cycled` assumption.** The value 8.5 used for the no-acid sets is an assumed equilibrium pH of cycled water without acid. It lies inside the manufacturers' 7.0–8.8 and 6.5–9.0 ranges but is not taken from a source.

## 3. Resulting cycles of concentration (verification run)

The table below was produced by loading every site × treatment through `ChemistryModel.from_library("data/water_sources_sourced.json", site, treatment)`.
- **const** = constituent mode.
- **dyn** = dynamic mode at T_hot = 35 °C and T_cold = 27 °C. Amorphous-silica solubility at 27 °C is 121.5 mg/L.
- Each cell gives N, then the limiting constraint.

| site | evapco_galvanized_inhibitor (const / dyn) | icc_advanced_inhibitor (const / dyn) | acid_feed_ph7p5 (const / dyn) | bac_galvanized (const / dyn) | evapco_stainless316 (const / dyn) |
|---|---|---|---|---|---|
| atlanta | 10.0 max_cycles | 10.0 max_cycles | 10.0 max_cycles | 10.0 max_cycles | 10.0 max_cycles |
| dallas | 3.6 m_alkalinity | 4.5 m_alkalinity | 7.6 calcium_hardness | 4.5 m_alkalinity / 4.1 LSI | 5.5 m_alkalinity |
| houston | 4.2 m_alkalinity | 5.3 m_alkalinity | 7.8 chloride | 5.3 m_alkalinity / 4.7 LSI | 6.2 calcium_hardness |
| las_vegas | 2.6 tds | 1.5 sulfate→min | 3.0 chloride | 1.5 sulfate→min | 3.2 calcium_hardness |
| phoenix_tmyx | 2.5 tds | 1.5 sulfate→min | 3.3 chloride | 1.5 sulfate→min | 3.2 calcium_hardness |
| portland_or | 10.0 max_cycles | 10.0 max_cycles | 10.0 max_cycles | 10.0 max_cycles | 10.0 max_cycles |
| montreal | 4.3 m_alkalinity | 5.4 m_alkalinity | 10.0 max_cycles | 5.4 m_alkalinity / 5.3 LSI | 6.5 m_alkalinity |
| dublin | 10.0 max_cycles | 7.1 sulfate | 10.0 max_cycles | 7.1 sulfate | 10.0 max_cycles |
| frankfurt | 2.3 m_alkalinity | 2.9 m_alkalinity | 4.7 calcium_hardness | 2.9 m_alkalinity / 2.6 LSI | 3.5 m_alkalinity |
| madrid | 10.0 max_cycles | 10.0 max_cycles | 10.0 max_cycles | 10.0 max_cycles | 10.0 max_cycles |
| stockholm | 7.7 calcium_hardness | 5.7 sulfate | 10.0 max_cycles | 5.7 sulfate | 9.2 calcium_hardness |
| riyadh | 2.5 chloride | 2.5 chloride | 2.5 chloride | 2.1 chloride | 4.1 calcium_hardness |
| mumbai | 4.1 m_alkalinity | 5.1 m_alkalinity | 10.0 max_cycles | 5.1 m_alkalinity | 6.2 m_alkalinity |
| singapore | 10.0 max_cycles | 10.0 max_cycles | 10.0 max_cycles | 8.3 chloride | 10.0 max_cycles |

When a cell shows a single value, the const and dyn modes gave the same result. `→min` means the computed N fell below 1.5 and was raised to `min_cycles`.

## 4. Which constituent limits cycles, by site

**Soft waters: Atlanta, Portland (Bull Run), Madrid, Singapore, and Dublin under the no-sulfate sets.**
- No constituent limit binds below 10 cycles, so N = `max_cycles`.
- In practice the operating limit for these waters is corrosion, not scale. Their LSI is negative, and EVAPCO asks for a minimum of Ca hardness 50 and alkalinity 75 for galvanized steel.
- Results here are therefore set by the `max_cycles` cap.
- Under the BAC set, Singapore's chloride (30, maximum 167) binds at about 8 cycles.

**Moderate-hardness, bicarbonate waters: Dallas, Houston, Montréal, Mumbai, Frankfurt.**
- **M-alkalinity binds** under the no-acid sets:
  - EVAPCO (400): about 3.6–4.3 cycles; Frankfurt 2.3.
  - ICC (500): about 4.5–5.4; Frankfurt 2.9.
- Under the BAC set the LSI limit (2.0 at pH 8.5, 35 °C) binds slightly earlier than the alkalinity limit for Dallas, Houston, Montréal and Frankfurt.
- **Acid feed** removes the alkalinity limit:
  - Ca hardness binds next for Dallas (7.6) and Frankfurt (4.7).
  - Chloride binds next for Houston (7.8).
  - Montréal and Mumbai reach the 10-cycle cap.

**Colorado River water: Las Vegas, Phoenix (CAP).**
- **Sulfate (209–239 mg/L) already sits near the 250 mg/L galvanized limit** in the ICC and BAC sets, so N collapses to `min_cycles`.
- Under EVAPCO the limit is TDS/conductivity at about 2.5–2.6 cycles.
- Acid feed and 316 SS allow about 3 cycles, limited by chloride and Ca hardness respectively.
- Real Colorado River towers commonly run 3–5 cycles with stainless or coated basins. The 250 mg/L sulfate guideline is a galvanized warranty limit, so results here are very sensitive to tower material. Consider BAC's alternative Cl+SO4 ≤500 rule or the stainless sets.

**Riyadh.**
- **Chloride (120 mg/L) binds** at 2.1–2.5 cycles for every galvanized set, including acid feed.
- 316 SS lifts the chloride limit, and Ca hardness then binds at 4.1.

**Stockholm.**
- Ca hardness binds under EVAPCO (7.7).
- Sulfate binds under ICC and BAC (5.7).

**Dublin.**
- Sulfate binds under ICC and BAC (7.1). Its input is the upper-bound value of "<35" mg/L.

**Silica.** Silica never binds at these sites, because makeup SiO2 is 8.3 mg/L or less everywhere. The highest is Frankfurt at 18 mg/L, which gives N = 6.7 against the solubility limit, but alkalinity binds first.
- Two sites could change this:
  - Portland's Columbia South Shore groundwater (SiO2 about 41) would be silica-limited at about 3–3.7 cycles.
  - Silica is missing for Riyadh and Mumbai. Riyadh's groundwater component could matter.

## 5. Gaps and things I could not find

**Atlanta.**
- The 2025 CCR reports regulated contaminants only.
- All values are USGS raw-river data. The major-ion samples are few (1995 and 2009), and treated-water Ca, alkalinity and sulfate are unknown.

**Dallas.**
- The 2025 CCR has no mineral data.
- Values are USGS 1985–1997 raw Elm Fork data. TCEQ Drinking Water Watch (secondary constituents) was not retrieved and is the best next source.
- pH: no source found.

**Houston.**
- Ca, alkalinity and SiO2 are not in the CCR. They are taken from 1985–1995 USGS Trinity River data.

**Phoenix.**
- The city CCR gives ranges only, with no Cl, SO4 or SiO2 and no split between SRP and CAP.
- Values are USGS Colorado River (CAP) data. The SRP (Salt/Verde) alternative was not quantified.

**Portland.**
- Cl and SO4 are not reported (both very low in Bull Run).
- The Ca value comes from an unconfirmed secondary table.

**Dublin.**
- Silica: not found.
- The values are 2013 guide values, not measured annual statistics.
- Cl and SO4 are given only as "<25" and "<35", and those upper bounds are used.
- The Leixlip supply is harder; its numbers are low confidence.

**Frankfurt.**
- The city mean covers Ca, Mg and SO4 only. Alkalinity, Cl and TDS were inferred by mixing the two 2018 zone analyses.
- The result is strongly zone-dependent: the Ried groundwater zone has alkalinity of about 255 and Ca hardness of about 265.

**Madrid.** This is the weakest site.
- No Canal de Isabel II table was found. The only figures (Ca 16, hardness 55, TDS 90) come from a secondary consumer site.
- Alkalinity is an unsourced estimate.
- SiO2, Cl and SO4: not found.
- Next step: SINAC (sinac.sanidad.gob.es) or the Canal de Isabel II monthly bulletins.

**Stockholm.**
- Silica: not found.
- The alkalinity figure is from 2019.

**Riyadh.**
- No NWC or SWA utility data was found. Values are from a 2020 academic sampling of 15 network sites (Aleid et al., 2023), and the site-to-site spread is large: TDS 110–611.
- Alkalinity is an estimate: the upper end of the SWA desalinated-water mandate of 50–80 (Fellows & Al-Hamzah 2026).
- SiO2: not found.

**Mumbai.**
- No MCGM data was found.
- Hardness, alkalinity, Cl and pH come from an MSc thesis read only through a search snippet.
- Ca hardness and TDS are estimates.
- SiO2 and SO4: not found.
- The alkalinity of 97 exceeds the total hardness of 47, which is unusual and needs verification.

**Singapore.**
- Complete, from the 2025 PUB data.
- NEWater, which a data center may use, is much purer: Ca <20, Cl <20, SiO2 <3.

**Treatment limits not obtained:**
- ASHRAE Handbook (HVAC Applications, Water Treatment chapter): paywalled.
- Veolia/SUEZ *Handbook of Industrial Water Treatment* cooling-water chapter: not retrieved.
- ChemTreat and Nalco guides: not retrieved.
- EPA WaterSense at Work: not retrieved.
- Puckorius & Brooke (1991): not found online.
- SPX Marley guidelines: not retrieved.
- The US BAC "Water Quality Guidelines" table: an image, not extractable.
- I found no direct source for "LSI 2.5–3.0 with acid feed" or for an Mg × SiO2 limit of 35,000–40,000.
