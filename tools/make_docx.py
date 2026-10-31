#!/usr/bin/env python3
"""Word (.docx) versions of the manuscript and the technical reference, for editing in Word / Word for the web.

Equations become native Word equations (OMML, editable), citations are resolved into a reference list
(Elsevier Harvard style when paper/elsevier-harvard.csl exists, otherwise pandoc's default author-date),
figures are embedded as PNG, and \\tbd{...} markers become highlighted "[TBD: ...]" text.

  python tools/make_docx.py            # -> paper/manuscript.docx, docs/METHODS.docx
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

import pypandoc

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
FIGS = ROOT / "results" / "figures"


def latex_for_pandoc(tex: str, base: Path = PAPER) -> str:
    tex = re.sub(r"\\resizebox\{[^}]*\}\{[^}]*\}\{(\\input\{[^}]+\})\}", r"\1", tex)
    # inline the results table (pandoc resolves \input relative to cwd; do it explicitly)
    def inc(m):
        p = (base / m.group(1)).resolve()
        if p.suffix == "":
            p = p.with_suffix(".tex")
        return p.read_text() if p.exists() else m.group(0)
    tex = re.sub(r"\\input\{([^}]+)\}", inc, tex)
    tex = re.sub(r"\\includegraphics(\[[^]]*\])?\{([^}]+)\}",
                 lambda m: r"\includegraphics%s{%s}" % (m.group(1) or "", (FIGS / (m.group(2) + ".png")).as_posix()), tex)
    tex = tex.replace(r"\newcommand{\tbd}[1]{\textcolor{red}{[#1]}}", "")
    tex = re.sub(r"\\tbd\{((?:[^{}]|\{[^{}]*\})*)\}", r"\\textbf{[TBD: \1]}", tex)
    tex = re.sub(r"\\graphicspath\{.*?\}\n", "", tex)
    # elsarticle front matter that pandoc drops or mangles
    m = re.search(r"\\author\{([^}]*)\}\s*\\address\{((?:[^{}]|\{[^{}]*\})*)\}", tex)
    if m:
        tex = tex.replace(m.group(0), "\\author{%s, %s}" % (m.group(1), m.group(2)))
    tex = re.sub(r"\\begin\{keyword\}(.*?)\\end\{keyword\}",
                 lambda k: "\\textbf{Keywords:} " + "; ".join(x.strip() for x in k.group(1).split("\\sep")),
                 tex, flags=re.S)
    return tex


def convert_manuscript(tex: Path = PAPER / "manuscript.tex", out: Path = PAPER / "manuscript.docx"):
    src = latex_for_pandoc(tex.read_text(), tex.parent)
    src = src.replace("{../references}", "{references}")
    args = ["--citeproc", "--bibliography", str(PAPER / "references.bib"), "--resource-path", str(FIGS),
            "--metadata", "link-citations=true"]
    csl = PAPER / "elsevier-harvard.csl"
    if csl.exists():
        args += ["--csl", str(csl)]
    ref = PAPER / "reference.docx"
    if ref.exists():
        args += ["--reference-doc", str(ref)]
    with tempfile.NamedTemporaryFile("w", suffix=".tex", dir=PAPER, delete=False) as fh:
        fh.write(src)
        tmp = Path(fh.name)
    try:
        pypandoc.convert_file(str(tmp), "docx", format="latex", outputfile=str(out), extra_args=args)
    finally:
        tmp.unlink()
    return out


def convert_methods():
    out = ROOT / "docs" / "METHODS.docx"
    pypandoc.convert_file(str(ROOT / "docs" / "METHODS.md"), "docx", format="markdown",
                          outputfile=str(out), extra_args=["--resource-path", str(ROOT / "docs")])
    return out


if __name__ == "__main__":
    outs = [convert_manuscript(), convert_methods()]
    hyb = PAPER / "hybrid" / "manuscript_hybrid.tex"
    if hyb.exists():
        outs.append(convert_manuscript(hyb, PAPER / "hybrid" / "manuscript_hybrid.docx"))
    for f in outs:
        print("wrote", f, "%.0f kB" % (f.stat().st_size / 1e3))
    sys.exit(0)
