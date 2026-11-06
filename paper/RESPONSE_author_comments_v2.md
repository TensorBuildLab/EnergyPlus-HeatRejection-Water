# Response to the author's comments on manuscript v5

Comments: `paper/manuscript v5 Liang Zhang comments and edits.docx` (10 comments and one direct edit).
Revised manuscript: `paper/manuscript_v6_final.tex` and `paper/manuscript_v6_final.docx` (v6). v5 is kept as
`paper/manuscript_v5.tex` and `paper/manuscript_v5.docx`. Submission files: `paper/Energy and Buildings submission files/`.
Date: 2026-11-06.

## Summary of changes

- **New title:** "Evaluating cooling tower evaporation models for data center water use in building energy simulation".
- **Introduction:** a new paragraph on Arizona's water resources, the 20-year service life of heat rejection plants, and
  the choice between air-cooled and water-cooled systems.
- **GitHub repository:** introduced early (in the Introduction and in Section 3.4). Every supplementary file is now a
  direct GitHub link.
- **Table 1 and Section 2.2:** rebuilt so that all eight models are described.
- **Discussion:** new Section 7.3, recommendations for data center water modeling.
- **Conclusions:** rewritten as prose, now including the limitations and future work.
- **New Appendix A:** the plugin code and the EnergyPlus input objects.
- **Acknowledgements:** NSF Award No. 2623038.
- **Figures:** Figure 2 redrawn, and all figures regenerated with plain hyphens for negative numbers.
- **Energy and Buildings requirements:** checked and met. The abstract was cut to 249 words, and the manuscript gained
  seven keywords, a graphical abstract, a CRediT statement, the declarations and line numbers.
- **Plugin tutorial:** tested end to end and added to the repository (`docs/TUTORIAL.md`).

## Point-by-point responses

### Direct edit: title, author and affiliations left aligned
Accepted. The Word converter (`tools/make_docx.py`) now left-aligns the title, the author line, the affiliations and the
corresponding-author line, so the change survives every rebuild. Word's other changes on saving were checked one by
one: line numbering, footer page-number field and style normalisation. None of them changes the formatting. The LaTeX
version keeps the elsarticle layout, which the journal typesets itself.

### C1: title (data center focus, no question, concise, describes the whole paper, Energy and Buildings scope)
**Changed.** New title: *"Evaluating cooling tower evaporation models for data center water use in building energy
simulation"* (14 words).
- **Data center focus:** data centers are now named as the main focus. The office prototype is presented as a
  comparison case in the abstract, introduction and case studies.
- **Not a question:** the title is a statement.
- **Covers the whole paper:** model comparison (evaluating ... evaporation models), the application (data center water
  use) and the platform (building energy simulation, i.e. the EnergyPlus plugin).

Scope for Energy and Buildings: the journal publishes building energy simulation and building-system performance, and
it published the LBNL data center prototype used here (Sun et al., 2021). v6 is framed accordingly:
- the case studies are prototype buildings used in code development;
- the method works inside a whole-building simulation;
- the practical outcome is a recommendation for data center designers and modelers (new Section 7.3);
- the design question of air-cooled versus water-cooled heat rejection is addressed (Introduction).

Alternative titles if you prefer:
- (a) "Cooling tower evaporation models and data center water use: an EnergyPlus study across 14 climates";
- (b) "Physics-based cooling tower evaporation modeling for data center water use in building energy simulation".

### C7: do not use the math minus sign; use "-" throughout
**Changed.** The following now use the plain hyphen "-":
- all 42 negative numbers in the text (`$-$9` became `-9`);
- the abstract and conclusions;
- the figure tick labels (`axes.unicode_minus = False` in `tools/figstyle.py`; all paper figures regenerated).

The generated tables already used "-". Minus signs inside equations (for example $e^{-NTU}$ or $T_{w,i}-T_{w,o}$) are
subtraction operators and were kept.

### C12: Introduction: Arizona, water resources, long service life of the design, air-cooled systems
**Added** a paragraph after the first paragraph of the Introduction. All sources were opened and checked, and the
bibliography entries are in `references.bib`.
- **Colorado River:**
  - the first declared shortage on the Colorado River for 2022, which cut Arizona's apportionment by about 18 %
    [U.S. Bureau of Reclamation, 16 Aug 2021];
  - a deeper level for 2023 [Reclamation, 16 Aug 2022].
- **Phoenix groundwater:** the ADWR 100-year groundwater model for the Phoenix Active Management Area projects
  4.86 million acre-feet of unmet demand, so parts of the region can no longer demonstrate an assured groundwater supply
  [Arizona Governor's Office, Jun 2023; ASU Kyl Center, Jun 2023].
- **Service life:** cooling towers and chillers have median service lives of about 20 years [ASHRAE Handbook, HVAC
  Applications, 2015, Ch. 37, Table 4]. A design based on short-term water availability can therefore be wrong over the
  life of the facility.
- **Air-cooled versus water-cooled:**
  - air-cooled heat rejection consumes almost no water on site but uses more energy [DOE FEMP/NREL best-practices guide,
    2024; Karimi et al. 2022; Karimi et al. 2025];
  - in a hot, arid climate an air-cooled data center had a 13 % higher power usage effectiveness but a 66 % lower source
    WUE than a water-cooled one [Karimi et al. 2022];
  - accurate water estimates are therefore needed to choose between air-cooled, hybrid and water-cooled systems.

Notes:
- **ADWR:** its own website blocked automated access, so the 4.86 million acre-feet figure is cited through the
  Governor's press release and the ASU Kyl Center explainer. Please cite the ADWR report directly if you prefer it.
- **ASHRAE Handbook:** the service-life values come from the 2015 edition (Chapter 37), as reproduced by ASHRAE TC 7.8.
  In the 2019 and 2023 editions this is Chapter 38.
- **Phoenix data center growth:** I did not add a claim about growing data center construction in Phoenix, because I
  found no peer-reviewed or official source for it. Add one if you have a source.

### C22: the description does not cover all models; Table 1 needs a model-name column and an equation column
**Changed.**
- **Section 2.2:** rewritten in three paragraphs that describe all eight models in the order of the table:
  - the empirical models (LAT, ROT, LF);
  - the saturated-exit models (MSAT, and EPSAT with its three differences from Merkel: inlet enthalpy at wet-bulb
    saturation, moist-air basis, EnergyPlus' air flow and fan-cycling convention);
  - BRAUN, POPPE and POPPE1.
- **Table 1:** now has four columns: ID, Model name, Evaporation (the equation of each model) and Key assumptions.
  The equations were checked against the code (`src/tower_water/evaporation.py`, `methods.py`).
- **Nomenclature:** the new symbols (cooling range, NTU, the effective saturation humidity, subscripts) were added.

### C24: "at each timestep" in the Table 1 caption
**Removed.** The caption is now "Evaporation models compared", plus definitions of the symbols.

### C26: mention GitHub earlier, and give links for supplementary files
**Agreed and changed.**
- **Where the repository URL now appears:**
  - in the Introduction (new contribution item, followed by "All models, building models, data and scripts referred
    to below as supplementary files are in this repository");
  - in Section 3.4 (Implementation);
  - in Section 6.1 (with the tutorial link);
  - in the Data availability statement.
- **Supplementary files:** every reference is now a full GitHub link: `docs/WATER_QUALITY_SOURCES.md`,
  `models/DATACENTER_MODEL.md`, `docs/EQUIPMENT_SPECS.md`, `docs/METHODS.md`, `docs/TUTORIAL.md` and `bugreports/`.
- **Important:** the repository is currently **private**. Make it public, or at least give reviewers access, before
  you submit, otherwise these links will not open (see the checklist in the submission folder).

### C46: Figure 2 text outside the boxes
**Fixed.** `tools/fig_plugin.py` was rewritten so that every box is sized from the rendered text, which means no text
can cross a box edge. Three other changes:
- the arrows were rearranged;
- a label "next timestep" was added to the return arrow;
- the bullet characters were replaced by plain hyphens.

I checked the new figure visually.

### C72: conclusions not in bullets; typical order; move limitations into the conclusions
**Changed.** The Conclusions are now five paragraphs, in the usual order:
1. aim and approach;
2. main findings, with the key numbers;
3. implications and recommendations for practice;
4. limitations, moved here from the former Section 7.4;
5. future work: metered data from operating data center towers, a Poppe-based tower model, multi-year and future
   weather, corrosion-limited treatment, and hybrid and air-cooled systems.

The Discussion no longer has a Limitations subsection.

### C74: show the EnergyPlus Python plugin code
**Added** Appendix A, "Plugin code". It contains:
- the plugin class, abridged from `src/tower_water/eplus_plugin.py`: the constructor and the
  `on_end_of_system_timestep_before_hvac_reporting` callback, which reads EnergyPlus variables through the API,
  evaluates the models and writes plugin variables;
- the EnergyPlus input objects that the preparation step adds (`PythonPlugin:SearchPaths`, `:Instance`, `:Variables`,
  `:OutputVariable` and `Output:Variable`), copied from a prepared prototype model with the tower name shortened.

Sections 1, 3.4 and 6.1 point to the appendix.

### C76: acknowledgement with NSF Award No. 2623038
**Added** before the references, in the standard NSF wording: "This material is based upon work supported by the U.S.
National Science Foundation under Award No. 2623038. Any opinions, findings, and conclusions or recommendations
expressed in this material are those of the author and do not necessarily reflect the views of the National Science
Foundation."

### Requested earlier: data center recommendation paragraph
**Added** Section 7.3, "Recommendations for data center water modeling", with six numbered recommendations:
- fan-cycling towers;
- variable-speed towers in cold and mild climates;
- comparing WUE across sites and choosing a cooling technology;
- hourly and peak demand;
- loss factors and rules of thumb;
- what to report.

The Conclusions summarise them.

## Energy and Buildings requirements

The official Guide for Authors page (sciencedirect.com) blocks automated access. The requirements were therefore taken
from search excerpts of that page and from Elsevier's standard policies. Please check them once against the live guide
(the checklist in the submission folder lists each item).

| Requirement | v5 | v6 |
|---|---|---|
| Abstract at most 250 words | 282 words | 249 words |
| Highlights: 3-5 bullets, at most 85 characters each, separate file | 5, longest 87 | 5, longest 77; separate file |
| Graphical abstract, at submission | missing | `graphical_abstract.png/.pdf`, 3300 x 1320 px (minimum 1328 x 531) |
| Keywords (Elsevier: up to 7) | 6 | 7 (adds Data center, EnergyPlus) |
| Numbered references, Elsevier style | yes | yes |
| Declaration of generative AI use | missing | added (see note below) |
| Declaration of competing interest | missing | added in the manuscript and as a separate file |
| CRediT author statement | missing | added |
| Data availability statement | "Data and code availability" | "Data availability", with the repository link |
| Funding and acknowledgements | missing | NSF Award No. 2623038 |
| Line numbers for review | Word only | Word and LaTeX (`lineno`) |
| Editable source file (Word or LaTeX) | yes | both, plus a self-contained LaTeX folder |
| Cover letter, suggested reviewers | missing | drafted in the submission folder |

**Generative AI declaration:** Elsevier requires authors to disclose AI use. I wrote the statement in Elsevier's
template wording, naming Claude (Anthropic) for software development, analysis scripts, literature and reference
checking, and drafting and language editing. Please adjust it so that it describes your own use accurately. You are the
only one who can make this declaration.

## Other changes and checks

- **Arizona paragraph:** about 190 words. The new references are listed in `references.bib` under
  "added for manuscript v6".
- **New abbreviations:** LBNL and DOE are now defined at their first use in the text. "Power usage effectiveness" is
  used once and spelled out.
- **Numbers:** unchanged from v5, because no simulation was rerun. The figures were regenerated from the archived runs
  with the same scripts, and the tables they write are unchanged.
- **Tutorial:** `docs/TUTORIAL.md` was added to the repository and linked from `README.md`. Every command in it was
  run.

## Open items for the author

1. **Repository access:** make it public, or give reviewers access, before submission (it is cited in the Data
   availability statement).
2. **Generative AI declaration:** check and adjust the wording.
3. **Suggested reviewers:** check each candidate for co-authorship with you in Scopus or Google Scholar.
4. **Guide for Authors:** check the requirements once on the live page.
5. **Still open from v5:**
   - the co-authorship decision on Tianzhen Hong;
   - the Perry's, CTI and BAC references;
   - a visual check of the Word file in Word.
