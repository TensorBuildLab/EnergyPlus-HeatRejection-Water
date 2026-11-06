#!/usr/bin/env python3
"""Assemble the Energy and Buildings submission folder from the v6 manuscript.

  python tools/make_submission.py

Writes into "paper/Energy and Buildings submission files/":
  03_Graphical_abstract.png/.pdf    from results/figures/graphical_abstract (tools/fig_graphical_abstract.py)
  04_Manuscript_v6_final.docx       copy of paper/manuscript_v6_final.docx (tools/make_docx.py)
  08_Figures/Figure_<n>[a|b].pdf/png  figures numbered in manuscript order
  09_LaTeX_source/                  self-contained LaTeX: tables inlined, figures renamed, references.bib
  *.md -> *.docx                    cover letter, highlights, title page, declaration, reviewers, checklist
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
TEX = PAPER / "manuscript_v6_final.tex"
OUT = PAPER / "Energy and Buildings submission files"
FIG = ROOT / "results" / "figures"
sys.path.insert(0, str(ROOT / "tools"))


def figure_order(tex: str):
    """[(figure number, [graphics names])] in the order of the figure environments."""
    figs = re.findall(r"\\begin\{figure\}(.*?)\\end\{figure\}", tex, flags=re.S)
    return [(i + 1, re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", f)) for i, f in enumerate(figs)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tex = TEX.read_text()

    for ext in (".png", ".pdf"):
        shutil.copy(FIG / ("graphical_abstract" + ext), OUT / ("03_Graphical_abstract" + ext))
    docx_src = TEX.with_suffix(".docx")
    shutil.copy(docx_src, OUT / "04_Manuscript_v6_final.docx")

    figdir = OUT / "08_Figures"
    latex = OUT / "09_LaTeX_source"
    for d in (figdir, latex):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir()
    rename = {}
    for n, names in figure_order(tex):
        for k, name in enumerate(names):
            new = "Figure_%d%s" % (n, "abcdefgh"[k] if len(names) > 1 else "")
            rename[name] = new
            for ext in (".pdf", ".png"):
                shutil.copy(FIG / (name + ext), figdir / (new + ext))
                shutil.copy(FIG / (name + ext), latex / (new + ext))

    # self-contained LaTeX: inline tables, local figure names, no graphicspath
    def inline(m):
        return (PAPER / m.group(1)).resolve().read_text().rstrip("\n") if (PAPER / m.group(1)).exists() else m.group(0)
    flat = re.sub(r"\\input\{([^}]+)\}", lambda m: inline(m) if m.group(1).endswith(".tex") else inline(
        re.match(r"(.*)", m.group(1) + ".tex")), tex)
    flat = flat.replace("\\graphicspath{{../results/figures/}}\n", "")
    flat = re.sub(r"(\\includegraphics(?:\[[^\]]*\])?\{)([^}]+)\}", lambda m: m.group(1) + rename.get(m.group(2),
                  m.group(2)) + "}", flat)
    (latex / "manuscript_v6_final.tex").write_text(flat)
    shutil.copy(PAPER / "references.bib", latex / "references.bib")
    left = re.findall(r"\\input\{[^}]+\}", flat)
    if left:
        raise SystemExit("tables not inlined: %s" % left)

    import make_docx
    for md in sorted(OUT.glob("*.md")):
        make_docx.convert_methods(md, md.with_suffix(".docx"))
    print("wrote", OUT)
    for f in sorted(OUT.rglob("*")):
        if f.is_file():
            print("  %-60s %8.0f kB" % (f.relative_to(OUT), f.stat().st_size / 1e3))


if __name__ == "__main__":
    main()
