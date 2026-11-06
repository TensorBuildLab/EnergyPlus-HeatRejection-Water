# Energy and Buildings submission: checklist and file guide

Manuscript: "Evaluating cooling tower evaporation models for data center water use in building energy simulation" (v6 final). Article type: Research Paper. Submit through Elsevier Editorial Manager, which you reach from the journal's Guide for Authors page.

Requirements were checked on 2026-11-06. The official Guide for Authors page (sciencedirect.com/journal/energy-and-buildings/publish/guide-for-authors) blocks automated access, so they come from search excerpts of that page and from Elsevier's standard policies. **Please check the items marked "confirm" once on the live page.**

## Files in this folder

| File | Upload as | Notes |
|---|---|---|
| 01_Cover_letter.docx | Cover letter | Edit the date. |
| 02_Highlights.docx | Highlights | Separate editable file with "highlights" in the name; 5 bullets, longest 77 characters (limit 85). |
| 03_Graphical_abstract.png (.pdf) | Graphical abstract | Required at submission; 3300 x 1320 px (minimum 1328 x 531 px). |
| 04_Manuscript_v6_final.docx | Manuscript | Editable Word file with line and page numbers, numbered sections, figures and tables in the text. |
| 05_Title_page.docx | Title page | Author details, acknowledgements, declaration. |
| 06_Declaration_of_competing_interest.docx | Declaration of interest | Editorial Manager may ask you to use Elsevier's online declaration tool instead; enter the same statement there. |
| 07_Suggested_reviewers.docx | Entered in the system | 7 candidates plus alternates; check them for conflicts. |
| 08_Figures/ | Figures (if requested) | High-resolution PDF and PNG, numbered as in the manuscript (Figure 3 has parts a and b). |
| 09_LaTeX_source/ | Alternative to the Word file | Self-contained elsarticle source with tables inlined, figures renamed and references.bib. Compile with pdflatex and bibtex (elsarticle and lineno are part of TeX Live and Overleaf). |

## Requirements

| Requirement | Status |
|---|---|
| Abstract at most 250 words | Done: 249 words |
| Highlights, 3-5 bullets, at most 85 characters, separate file | Done |
| Graphical abstract at submission | Done |
| Keywords (Elsevier standard: 1-7) | Done: 7 (confirm the limit) |
| Numbered citations, Elsevier reference style | Done |
| Abbreviations defined at first use; nomenclature | Done |
| Declaration of generative AI use (Elsevier policy) | Added in the manuscript. **Check and adjust the wording.** |
| Declaration of competing interest | Done (manuscript, title page and separate file) |
| CRediT author statement | Done |
| Funding statement | Done: NSF Award No. 2623038, in the Acknowledgements |
| Data availability statement | Done. **The GitHub repository is private: make it public, or give reviewers access, before you submit.** |
| Line numbers for review | Done (Word and LaTeX) |
| Editable source file (Word or LaTeX), not PDF | Done (both) |
| Cover letter | Done |
| Suggested reviewers | Drafted: **check for conflicts** |
| Weather data stated (simulation papers) | Done: TMYx 2011-2025, 14 sites |
| Length | Main text (Introduction to Conclusions) about 7,200 words, plus 10 tables, 8 figures and 1 appendix. I found no strict length limit for Energy and Buildings (confirm). |
| Anonymisation | Not required as far as I could confirm (single-anonymised review). The author details are in the manuscript and on the title page (confirm). |

## Before you press Submit

1. Make https://github.com/TensorBuildLab/EnergyPlus-HeatRejection-Water public, or create a reviewer-access link. It is cited in the manuscript and the Data availability statement.
2. Check the generative AI declaration and change it to match your own use.
3. Check the suggested reviewers for co-authorship.
4. Open 04_Manuscript_v6_final.docx in Word and look through it. It was built on a server without Word, so its structure was checked but it was not viewed as rendered pages.
5. Decide on co-authorship (Tianzhen Hong) before submitting, since changing authors after submission needs the editor's approval.
6. Confirm the editions of the Perry's Handbook, CTI ATC-105 and BAC references.
7. Rebuild the folder after any change: `python tools/make_docx.py paper/manuscript_v6_final.tex && python tools/make_submission.py`.
