# Response to the author's comments on manuscript v4

Comments file: `paper/manuscript_Liang Zhang comment v1.docx` (17 comments plus direct edits).
Revised manuscript: `paper/manuscript.tex` and `paper/manuscript.docx` (v5). Previous version kept as
`paper/manuscript_v4_before_author_comments.tex` and `paper/manuscript_v4.docx`.

## Summary of the main changes

1. **Reframed around evaporation physics.** The paper now asks where and why simplified models depart from the Poppe
   model, with EnergyPlus as the test platform; the data center is the primary case study, not the subject.
   - New title: *How much does the evaporation model matter? Cooling tower water use in building energy simulation
     across climates, tower controls and building types.*
   - New Section 2 (physics): what sets evaporation per unit heat.
     1. the sensible share of the heat transfer;
     2. the Lewis factor;
     3. the state of the exhaust air.
   - The discussion now gives one physical statement: the error of a simplified model follows the exhaust-air state,
     and that state depends on the weather and on the tower's air-to-water ratio.
2. **The LBNL/DOE large data center prototype is now the core case study.** The DOE large office prototype was added
   to show how far the conclusions carry beyond data centers. The earlier 1 MW model is kept as the variable-speed-tower
   case.
3. **New physics result: fan cycling.** Both prototypes use single-speed, fan-cycling towers. The plugin was extended to
   resolve each fan-cycling timestep into its fan-on and free-convection states.
   - EnergyPlus applies the average heat to the full air flow; this alone adds 5–22 % evaporation for the data center
     prototype.
   - The EnergyPlus default vs Poppe now spans:
     - −9 to −4 % for the variable-speed tower;
     - −5 to +16 % for the office;
     - +2 to +38 % for the data center prototype.
4. **New Section 6.1 on the plugin.** Covers what it does, how to install and use it, its outputs and its run-time
   cost. Adds a workflow figure (Fig. 2) and an outputs table (Table 6).
5. **Removed:**
   - the EnergyPlus loss-factor section;
   - the appendix on EnergyPlus water-accounting issues;
   - the corresponding highlight, abstract sentence and conclusion.
   One sentence in "Data and code availability" points to `bugreports/` so nothing is lost.
6. **Formatting:**
   - numbered sections, tables and figures;
   - ruled tables;
   - numbered citations;
   - consistent heading fonts;
   - title block with both affiliations;
   - Highlights as bullets and Keywords;
   - line and page numbers.
7. **References:** all 58 existing entries checked against Crossref, DataCite and publisher pages; 10 corrected; 7 new
   ones added (`docs/REFERENCES_CHECK_v5.md`).

## Point-by-point responses

### C0.1 — Is this research specific to data centers? Should "data center" be in the title?

**Agree; changed.** The physics is general: any open cooling tower evaporates according to the same heat and mass
transfer, and nothing in the models is specific to data centers. What is building-specific is *when* and *how* the
tower operates:
- **When:** data centers reject heat in every hour, including freezing and humid hours; offices mostly in summer.
- **How:** part-load fan control, which sets the air-to-water ratio.

The v5 results show that these operating patterns change the sign of the error of simplified models, so building type
matters as an *operating pattern*, not as a subject.

Changes:
- **Title:** no longer data-center-specific; it names "climates, tower controls and building types".
- **Introduction:** opens with cooling towers in commercial buildings in general, which typically use 20–50 % of a
  facility's water (EPA WaterSense at Work, new reference). Data centers come second, as the case where water use
  matters most and the tower runs all year.
- **Research questions:** framed as physics questions (i)–(iii).
- **Case studies:** the data center is the primary case "because water use matters most there and its towers operate
  in all seasons". An office prototype was added to show generality.
- **Discussion 7.3:** the conclusions carry to hospitals, laboratories, district plants and process cooling.

Reasoning for keeping a data center as the primary case rather than an office: data centers have the year-round
operation that exposes both failure modes of saturated-exit models (cold supersaturated exhaust and hot–dry unsaturated
exhaust). Water use is also a siting and permitting issue for them, so the practical stakes are highest.

### C0.2 — Why not use the LBNL prototype data center models as the core model?

**Agree; done.** The large data center prototype of Sun et al. (2021, Energy and Buildings 231:110603), high IT density,
ASHRAE 90.1-2019, is now the core case study, run in all 14 climates.

How it was obtained:
1. The prototypes exist only as OpenStudio-Standards code (no published EnergyPlus files).
2. Generating them requires the OpenStudio command-line tool. The sandbox on this server would not let me run that
   downloaded program.
3. I therefore used the library's own output for climate zone 3A, archived by the Stor4Build project (ORNL and
   partners, BSD-3).
4. I translated it with the official OpenStudio 3.7 Python package and converted it to EnergyPlus 22.2. For the
   objects in this model, the two input dictionaries differ in one economizer field.
5. The steps are documented in `models/prototypes/README.md` and are reproducible.

The prototype was kept as published except for two changes:
- the tower evaporation mode was set to EnergyPlus' default saturated-exit option (the prototype uses the loss factor;
  this does not change the thermal solution);
- meters were added.

Per site, the location and design days are replaced. The tower is sized by EnergyPlus at fixed rating conditions, so it
is the same everywhere.

**Your decision needed:** the 3A envelope is used at every site, which is negligible against the 3 MW IT load. If you
want the exact prototype per climate zone, I can generate it with the OpenStudio CLI. That needs you to allow running it
here, or to run it yourself. I expect little change because the IT load dominates.

The earlier 1 MW model is kept as a third case: a data center with a **variable-speed** tower. This is the other
EnergyPlus tower model and is common in new large facilities. The operating-point and sensitivity analyses of v4 are
based on it and remain valid. The DOE large office reference building (shipped with EnergyPlus) was added for the
building-type comparison.

### C0.3 — Should I invite Tianzhen Hong as co-author?

This is your decision. The usual authorship criteria (ICMJE / Elsevier CRediT): substantial contribution to conception,
methods, analysis or interpretation; drafting or critical revision; approval; accountability.

**Arguments for inviting him:**
- The core case is now his group's prototype.
- He is a leading EnergyPlus and data-center modelling researcher.
- His critical review, especially of how the prototypes are used and of the EnergyPlus interpretation, would strengthen
  the paper.
- He could also help reach EnergyPlus developers about the water-accounting issues documented in `bugreports/`.

**Arguments against inviting only for use of the models:** the prototypes are public and are properly cited
(Sun et al., 2021). Using them alone does not justify authorship.

**Recommendation:** invite him if he agrees to contribute substantively, for example:
- reviewing the prototype setup and results;
- advising on generating the prototypes per climate zone;
- co-writing the discussion of implications for prototype-based studies and code development.

Otherwise, acknowledge any advice. An affiliation question to consider: the second affiliation you added is National
Laboratory of the Rockies; if a co-author from LBNL is added, check institutional review requirements on both sides.

### C0.4 — Word formatting is unprofessional

**Agree; the converter was rebuilt** (`tools/make_docx.py`, style template `tools/docx/reference.docx`):
- **Numbering:** sections (1, 1.1); tables ("Table N." above) and figures ("Figure N." below) use Word sequence fields
  with stored numbers, so they display in Word for the web.
- **Tables:** every table has full single-line borders, a bold repeating header row, 9 pt text and page width.
- **Headings:** one font family; 16 pt for levels 1 and 2, as in your edit, and 14 pt for level 3.
- **Title block:** authors with superscript affiliation letters, two affiliation lines and the corresponding author.
- **Front matter:** Highlights as bullets; a Keywords heading; a References heading.
- **Citations:** numbered [1], [2,3] with the Elsevier numeric style.
- **Equations:** remain native, editable Word equations, numbered at the right margin.
- **Page:** US Letter with 1-inch margins, continuous line numbers and page numbers.

Limitation: LibreOffice is not installed on the server, so the file was checked structurally (python-docx) rather than
rendered. Please report anything that still looks wrong in Word.

### C1 — Abstract: too little method, too many numbers, findings not summarised, no broader impact

**Agree; rewritten.** The new abstract has four parts:
1. **Method (about half):** eight models from rules of thumb to Poppe and what Poppe resolves; evaluation at the same
   simulated operating point; resolution of fan cycling; the open plugin; verification; three buildings in 14 climates.
2. **One summarised finding:** errors follow the exhaust-air state, and the air-to-water ratio decides the regime.
3. **Four supporting numbers:** −9 to +38 %, 22 points from averaging, 65 % for empirical rules, −16 to +44 % for
   chemistry.
4. **Broader-impact sentence at the end:** design, siting and reporting estimates should resolve the exhaust state and
   part-load operation and state the cycles of concentration.

### C2 — The paper should be about physics, with EnergyPlus as the validation platform

**Agree; changed throughout:**
- **Title and abstract:** about evaporation models in building energy simulation, not about EnergyPlus.
- **Section 2 (new, physics):** explains the three effects and states the mechanism behind every sign seen later.
- **Section 3:** explains the evaluation method in general terms; EnergyPlus appears as one implementation (3.4).
- **Results:** organised by physical question:
  - where models depart (6.2), with the air-to-water mechanism added;
  - building and tower control (6.3);
  - the averaging of fan cycling, a physics-of-averaging result (6.4);
  - mist (6.5).
- **Discussion 7.1:** states the physical principle; 7.3 states that the method applies to any program reporting the
  tower's operating point.
- **Removed:** EnergyPlus-specific material that is not physics (the loss-factor units error and the water-accounting
  appendix).

### C3 — Highlight with "L/G": people won't understand

**Agree.** The highlights were rewritten in plain words; none uses L/G. In the text, L/G is defined in the nomenclature
and explained physically in Section 6.2 ("more air per unit of water").

### C4 — Highlight "LossFactor applied as a fraction": so what?

**Agree; removed.** It is an implementation issue, not a finding about physics. See C49.

### C7 — Abbreviations: use only if needed more than twice; define at first use (WUE used before definition)

**Agree.** I checked every abbreviation:
- **WUE:** now defined at its first use in the Introduction.
- **Defined at first use:** IT, e-NTU, LSI.
- **Defined in the table caption:** LBNL, DOE, COP and CZ appear only in tables.
- **Removed or spelled out** because they appeared once or twice: PUE, CRAH, VSD, CHW, N+1 (now explained), RK4,
  BVP, UA, AFR, WFR, EMS.
- **Kept:** model identifiers (LAT … POPPE1) are names defined in Table 1. ASHRAE and IAPWS are organisation names.

### C8, C11, C16 — Section and table numbers; consistent heading fonts

**Agree; done** (see C0.4). Cross-references now match the visible numbers.

### C12 — Why is "accounting mode" at the beginning? Confusing.

**Agree.** The term "accounting mode" was dropped. The Methods now start with the physics (Section 2). The evaluation
approach follows in Section 3.1, "The same operating point for every model", which explains:
- **why:** the simulation solves the tower's heat transfer, and evaporation does not feed back, so all models can be
  evaluated on the same thermal work and their differences isolate the physics;
- **the cost:** the operating point comes from the simulation's tower model, which Section 6.7 tests.

### C13 — "Plugin" never defined

**Agree.** Section 3.4 defines it: "A plugin is a user-written Python class that EnergyPlus calls at defined points of
every timestep; it can read any output variable and write its own" (EnergyPlus `PythonPlugin` objects). Section 6.1
describes the tool in detail.

### C31 — Tables should have lines

**Agree; done** (all tables bordered in Word; see C0.4).

### C33 — The plugin is the main product and should be introduced in detail in the Results

**Agree.** New Section 6.1, "The open-source plugin", covers:
- architecture, with the new Fig. 2 (workflow);
- installation;
- the three steps to use it on any EnergyPlus model (prepare, run, analyse), with the command line;
- supported towers, including the new single-speed tower;
- the configuration options (water source, treatment, chemistry mode, models);
- the outputs (new Table 6);
- the run-time cost: 7 s → 109 s for an annual run with all eight models; fewer models reduce it;
- documentation and tests.

The GitHub README was updated to match.

### C49 — Loss-factor section: is it necessary? Not our business; too much irrelevant information

**Agree; removed.** The loss factor stays as one of the empirical models (0.2 %/K, the EnergyPlus and prototype
default). The units issue is documented in `bugreports/`, with a pointer in "Data and code availability". Whether to
file it with the EnergyPlus developers is your call. It does not affect the paper, which uses 0.2 %/K as intended.

### C54 — "Limitations" at the wrong heading level

**Agree; fixed.** The Discussion is now four numbered subsections (7.1–7.4); Limitations is 7.4, a level-2 heading.

### C58 — Appendix on other EnergyPlus water-accounting issues: really needed?

**Agree; removed** (see C49). The material remains in `bugreports/README.md` with reproductions.

### C59 — Check all references; use numbered citations

**Done.**
- Citations are numbered (`elsarticle-num`, `\biboptions{numbers,sort&compress}`; numeric Elsevier style in Word).
- All 58 entries were checked against Crossref, DataCite and publisher pages (`docs/REFERENCES_CHECK_v5.md`).
- 10 corrections; the main ones:
  - one wrong DOI (lucas2009experimental);
  - two duplicate keys removed (jaber1989design, kroger2004air);
  - the ASHRAE water-treatment chapter (2023 Handbook, Chapter 50);
  - Hyland–Wexler pages (500–519);
  - ASHRAE addendum year (2022);
  - Evapco bulletin title and location;
  - missing pages and issue numbers.
- New entries (all verified):
  - Sun et al. 2021 (LBNL prototypes);
  - Deru et al. 2011 (DOE reference buildings);
  - Crawley et al. 2001 (EnergyPlus);
  - ASHRAE 90.1-2019;
  - OpenStudio-Standards;
  - Stor4Build;
  - EPA WaterSense at Work 2012 (EPA 832-F-12-034).

**Still for you to confirm (could not be verified online):**
- the edition and page of the Perry's Handbook rule of thumb (7th or 8th edition);
- the CTI ATC-105 edition;
- the year of the BAC Baltibond document;
- Braun et al. 1989 (no DOI; ASHRAE Transactions contents are a scanned image).

### Direct edits in the Word file

| Your edit | Where it is now |
|---|---|
| Second affiliation "National Laboratory of the Rockies, Golden, CO, USA" | `\affiliation[b]` in the .tex; affiliation line b in the Word file |
| Corresponding author line | `\cortext` / `\ead` in the .tex; shown under the affiliations in the Word file |
| Highlights and Keywords headings, bullet highlights | Generated by the converter |
| Numbered headings, 16 pt heading font | Generated for all levels |
| Visible figure captions | All captions are numbered caption paragraphs |
| "Reference" heading before the bibliography | Generated as "References" |
| Left-aligned table columns | All tables are bordered and fit the page width; numeric columns stay right-aligned, the usual journal style. Tell me if you prefer everything left-aligned. |

## Other changes made while revising

- **Plugin:**
  - `CoolingTower:SingleSpeed` support (fan cycling and fluid bypass) with a verified free-convection replica: within
    0.17 K of EnergyPlus;
  - a new `Mist` output;
  - 5 new unit tests (60 in total).
- **Data loading:** `tools/analyze.py` now ignores design-day periods that some models also report. This affected only
  the prototypes and was found during this revision.
- **New analysis scripts:**
  - `tools/building_study.py` (cross-building comparison);
  - `tools/single_speed_check.py` (replica check and the averaging/physics split);
  - `tools/fig_plugin.py` (workflow figure).
- **Reproduction:** `reproduce.sh` includes the prototype runs. The run archive keeps the full timestep series of both
  prototype studies.

## Open items for the author

1. Decide on co-authorship (C0.3).
2. Optionally allow running the OpenStudio CLI to generate the data center prototype for each climate zone (C0.2).
3. Confirm the four references listed under C59.
4. Check the Word file visually in Word for the web; report any remaining formatting issue.
5. Still open from earlier rounds:
   - low-confidence water data at four sites;
   - metered makeup data for validation;
   - whether to file the EnergyPlus issues upstream.
