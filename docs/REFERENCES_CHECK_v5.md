# Reference check v5 (`paper/references.bib`)

Checked 2026-11-05. Sources: Crossref REST API (every DOI was resolved and its record compared field by field), doi.org / DataCite, and publisher or organization pages. The original file is backed up as `paper/references_before_refcheck.bib`. Citation keys were not changed and no entries were added. `paper/manuscript.tex` was not edited.

Status key:
- **verified**: all fields match an authoritative record.
- **verified (secondary)**: no primary record could be reached; the entry matches consistent secondary citations and was left unchanged.
- **corrected**: one or more fields were changed (old → new).
- **unverifiable**: left unchanged; the author must confirm it (see the last section).

## 1. Entry-by-entry results

| Key | Status | Change (old → new) | Source |
|---|---|---|---|
| ashrae2021fundamentals | verified (from v1 check) | — | ashrae.org 2021 Fundamentals TOC (see REFERENCES_CHECK.md row 1) |
| bosnjakovic1965technical | verified (secondary) | — | library catalogue (REFERENCES_CHECK.md row 2) |
| braun1989effectiveness | verified (secondary) | — (ASHRAE 1989 Vancouver TOC PDF is an image scan, so the pages could not be read from it) | Mitchell & Braun SM3 reference list |
| cti2019atc105 | unverifiable (edition) | — | CTI/GlobalSpec listings: there are 2019 and 2022 editions |
| doe2022engref | verified | — (the NREL GitHub URL now redirects to github.com/NatLabRockies/EnergyPlus but still resolves) | https://github.com/NREL/EnergyPlus/tree/v22.2.0/doc/engineering-reference |
| doe2022ioref | verified | — (same redirect) | https://github.com/NREL/EnergyPlus/tree/v22.2.0/doc/input-output-reference |
| fournier1977chemical | verified | — | Crossref 10.1016/0375-6505(77)90007-4 |
| hendersonsellers1984new | verified | — | Crossref 10.1002/qj.49711046626 |
| hyland1983formulations | **corrected** | pages 500--513 → **500--519**; note "Page range per secondary sources; UNCERTAIN" → "Paper 2793 (RP-216)" | ASHRAE's own TOC for Trans. Vol. 89 Pt 2A (1983 Washington DC meeting): Paper 2793 starts on p. 500 and the companion Paper 2794 starts on p. 520. https://www.ashrae.org/File%20Library/Technical%20Resources/ASHRAE%20Transactions%20and%20Conferences%20Programs/1983-Washington-DC-TOC.pdf |
| jaber1989design | **corrected** (duplicate) | The key appeared **twice** in the .bib. The second, lower-case copy (added from memory) was removed. The remaining entry matches Crossref (J. Heat Transfer 111(4) 837–843, doi 10.1115/1.3250794). | Crossref 10.1115/1.3250794 |
| kell1975density | verified | — (Crossref's ACS title encoding is "0.deg. to 150.deg.."; the bib's "0° to 150 °C" follows the printed title) | Crossref 10.1021/je60064a005 |
| kloppers2005critical | verified | — | Crossref 10.1016/j.ijheatmasstransfer.2004.09.004 |
| kloppers2005lewis | verified | — | Crossref 10.1016/j.ijthermalsci.2005.03.006 |
| kloppers2005cooling | verified | — | Crossref 10.1115/1.1787504 |
| kloppers2004cooling | **corrected** | added pages **24--29** (authors Kloppers & Kröger confirmed) | the article PDF's running footers "R & D Journal, 2004, 20(1)", pp. 24–29: https://scielo.org.za/pdf/rd/v20/06.pdf |
| kroger2004air | **corrected** (duplicate) | The key appeared **twice**; the second copy (no volumes or ISBN) was removed. In the remaining entry: added note "Two volumes; ISBN 0-87814-896-5 (Vol. 1), 1-59370-019-9 (Vol. 2)". Title, author (Kröger), publisher (PennWell, Tulsa) and year 2004 were all verified. | PennWell product pages (Vol. 1 and Vol. 2); Blackwell's 9781593700195; Stellenbosch repository |
| langelier1936analytical | verified | — | Crossref 10.1002/j.1551-8833.1936.tb13785.x |
| merkel1925verdunstungskuhlung | verified (secondary) | — | REFERENCES_CHECK.md row 16 |
| meyer2019psychrolib | verified | — | Crossref 10.21105/joss.01137 |
| mytton2021data | **corrected** (minor) | added number = 1 (11 is the article number) | Crossref 10.1038/s41545-021-00101-w |
| green2008perrys | unverifiable | — | 8th-ed. Section 12 title confirmed (GlobalSpec); the 8th-ed. ISBN is correct; Eq. (12-14c) and its page are not confirmed |
| poppe1991berechnung | verified (secondary) | — | Kloppers & Kröger reference lists |
| qureshi2006prediction | verified | — | Crossref 10.1080/01457630600846372 |
| qureshi2007prediction | verified | — | Crossref 10.1016/j.applthermaleng.2006.06.008 |
| ryznar1944new | verified | — | Crossref 10.1002/j.1551-8833.1944.tb20016.x |
| shehabi2016united | verified | — | Crossref/OSTI 10.2172/1372902 |
| greengrid2011wue | verified | — (dated 1 March 2011; ed. M. Patterson) | https://www.thegreengrid.org/en/resources/library-and-tools/238-WP |
| wagner2002iapws | verified | — | Crossref 10.1063/1.1461829 |
| carrier1965handbook | unverifiable | — (content not seen; uncited in either manuscript) | — |
| klimanek2009solution | verified | — | Crossref 10.1016/j.icheatmasstransfer.2009.03.007 |
| navarro2022critical | verified | — | Crossref 10.1016/j.applthermaleng.2022.118719 |
| khan2001improved | verified | — | Crossref 10.1115/1.1376395 |
| siddik2021environmental | verified | — | Crossref 10.1088/1748-9326/abfba1 |
| lei2022climate | verified | — | Crossref 10.1016/j.resconrec.2022.106323 |
| shehabi2024united | verified | — The DOI is a DataCite DOI (not in Crossref) and resolves to eScholarship 32d6m0d1. The author list and order, LBNL-2001637 and the date (19 Dec 2024) all match. DataCite lists the year as 2025; 2024 was kept because it is the date on the report. | https://eta-publications.lbl.gov/publications/2024-lbnl-data-center-energy-usage-report ; api.datacite.org/dois/10.71468/P1WC7Q |
| li2025making | verified | — | Crossref 10.1145/3724499 |
| ristic2015water | verified | — (Crossref/MDPI print "Ristic"; the bib keeps the diacritic, "Ristić", which is the author's own spelling) | Crossref 10.3390/su70811260 |
| powers2016new | verified | — (pp. 9–16 confirmed) | Crossref 10.26868/25746308.2016.C002 ; https://publications.ibpsa.org/conference/paper/?id=simbuild2016_C002 |
| karimi2022water | verified | — (Crossref splits "Degraft-Johnson" wrongly; the bib is correct) | Crossref 10.1016/j.resconrec.2022.106194 |
| karimi2025energy | verified | — | Crossref 10.1016/j.applthermaleng.2025.126802 |
| li2020model | verified | — | Crossref 10.1016/j.enbuild.2020.110407 |
| asvapoositkul2014comparative | verified | — | Crossref 10.1016/j.applthermaleng.2014.06.023 |
| he2014experimental | verified | — | Crossref 10.1016/j.enconman.2014.07.084 |
| alkhedhair2013numerical | verified | — | Crossref 10.1016/j.applthermaleng.2013.08.012 |
| ndukaife2019optimization | verified | — | Crossref 10.1080/01457632.2018.1436418 |
| yang2020experimental | verified | — | Crossref 10.1016/j.egyr.2020.04.001 |
| altman2012membrane | verified | — | Crossref 10.1016/j.desal.2011.09.052 |
| li2011control | verified | — | Crossref 10.1016/j.watres.2010.08.052 |
| soliman2022treatment | verified | — (Crossref gives the first author as "Mariam"; the bib's "Mariam N." was not checked against MDPI) | Crossref 10.3390/su14010376 |
| pan2018cooling | verified | — | Crossref 10.1016/j.wen.2018.04.002 |
| kloppers2003critical | verified | — | Stellenbosch repository, handle 10019.1/1476 (PhD 2003, supervisor D.G. Kröger) |
| ashrae2019addendumbd | **corrected** | year 2021 → **2022**; title prefixed "ANSI/ASHRAE/IES"; howpublished "ASHRAE, Atlanta, GA" → "ASHRAE, Peachtree Corners, GA"; added URL and note "Approved by ASHRAE and ANSI on 31 May 2022" | Addendum PDF title page: https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20addenda/90_1_2019_bd_20220531.pdf (Table J-5 exists in it) |
| evapco2019om | **corrected** | title "Operation and Maintenance Instructions, Induced and Forced Draft Cooling Towers (TWR19AOM)" → "Operation and Maintenance Instructions for EVAPCO Induced Draft and Forced Draft Cooling Towers (Bulletin TWR19OM)"; "EVAPCO Inc., Taneytown, MD" → "EVAPCO, Inc., Westminster, MD". Table 3 "Recommended Water Chemistry Guidelines" (p. 18) confirmed. | the PDF at the URL in the entry (cover page, back cover "©2019 … TWR19OM") |
| bac2020baltibond | unverifiable | — The URL now redirects to a BAC "file-access-restriction" page, and the year 2020 is still unconfirmed. | — |
| icc2014gew174 | verified | — (PDF footer reads "ICC Committee Action Hearings, April 2014"; proponent D. Cline, EVAPCO) | https://www.iccsafe.org/wp-content/uploads/GEW174.pdf |
| demadis2003gordian | **corrected** | title "Water treatment's {Gordian} knot" → "Water treatment's 'Gordian knot'"; added month = may (published 27 May 2003); URL updated to the current canonical page (the old URL redirects there) | https://www.chemicalprocessing.com/environmental-protection/water-wastewater/article/11380085/water-treatmentsgordian-knot |
| lucas2009experimental | **corrected** | **doi 10.1016/j.enconman.2008.11.006 → 10.1016/j.enconman.2008.11.008.** The old DOI resolves to an unrelated paper (Haghighi et al., "Three-dimensional inverse transient heat transfer analysis…", pp. 450–457). Authors, title, vol. 50(3) and pp. 490–497 were already correct. | Crossref 10.1016/j.enconman.2008.11.008 |
| ashrae2023water | **corrected** | title "Water treatment: deposition, corrosion, and biological control" → "**Water Treatment: Deposition, Corrosion, Fouling, and Biological Control**" (the 2023 edition adds "Fouling"); added chapter = **50**; address Atlanta → Peachtree Corners, GA; removed the "to be confirmed" note | ASHRAE Handbook Online page title for 2023 Applications Ch. 50: https://handbook.ashrae.org/Handbooks/A23/SI/a23_ch50/a23_ch50_si.aspx (the 2019 edition's Ch. 50 is titled without "Fouling") |

Totals: 58 unique entries; 44 verified (4 of them verified (secondary): bosnjakovic, braun, merkel, poppe), 10 corrected, 4 unverifiable (cti2019atc105, green2008perrys, carrier1965handbook, bac2020baltibond).

## 2. Cross-check of citations against the .bib

- **Keys cited but missing from the .bib:** none (`paper/manuscript.tex` and `paper/hybrid/manuscript_hybrid.tex`).
- **Duplicate keys in the .bib (fixed):** `jaber1989design` and `kroger2004air` each appeared twice. BibTeX keeps the first copy and raises an error for the second.
- **In the .bib but not cited in `manuscript.tex`:** alkhedhair2013numerical, asvapoositkul2014comparative, carrier1965handbook, cti2019atc105, doe2022ioref, he2014experimental, kloppers2004cooling, li2011control, ndukaife2019optimization, pan2018cooling, qureshi2007prediction, ryznar1944new, yang2020experimental.
- **Cited by neither manuscript (main or hybrid):** carrier1965handbook, cti2019atc105, doe2022ioref, kloppers2004cooling, li2011control, pan2018cooling, qureshi2007prediction, ryznar1944new. These were kept as instructed.

## 3. Items the author must confirm

1. **green2008perrys:** the edition (7th 1997 or 8th 2008) and the page of Eq. (12-14c), W_e = 0.00085 W_c (T1 − T2). Check in a licensed copy.
2. **cti2019atc105:** cite the edition consulted (2019, or the 2022 revision).
3. **bac2020baltibond:** the year (2020) is unconfirmed, and the URL is now behind BAC's access-restriction page. Keep a local copy or use an archived URL.
4. **carrier1965handbook:** content not seen; it is not cited in either manuscript.
5. **braun1989effectiveness / hyland1983formulations:** neither has a DOI. The Hyland–Wexler range 500–519 is set by the next paper starting on p. 520. If the paper's own last page (before any discussion) is earlier, use that.
6. **kroger2004air** (cited for the Poppe method): consider citing the volume and chapter. Per PennWell, Vol. 2 holds Chs. 6–10, including the cooling-tower chapters.
7. **ashrae2023water:** the chapter title follows the ASHRAE Handbook Online page title (2023 edition). If the 2019 chapter was the one consulted, change the year to 2019 and drop "Fouling" from the title.
8. **evapco2019om:** the bulletin code printed on the document is "TWR19OM", while the URL file name says "TWR19AOM". Use the printed code.
