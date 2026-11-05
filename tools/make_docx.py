#!/usr/bin/env python3
"""Word (.docx) versions of the manuscripts and the technical reference, for editing in Word / Word for the web.

Manuscripts (elsarticle LaTeX -> pandoc -> post-processing):
  * title block with authors, superscript affiliation letters, affiliation lines and corresponding author;
  * Abstract, Highlights (bullets) and Keywords as headings; numbered sections (1, 1.1, 1.1.1), Appendix A, ...;
    \\paragraph{X} becomes a run-in bold lead "X." (as in the PDF);
  * numbered citations [1], [2,3] (Elsevier numeric CSL, tools/docx/elsevier-with-titles.csl); \\citet{k} -> "Author [n]";
  * "Table N." captions above tables and "Figure N." captions below figures (Word SEQ fields, so Word renumbers);
  * every table with single-line borders, bold repeated header row, full text width, 9 pt;
  * numbered display equations "(n)" (right tab), native editable Word equations (OMML) throughout;
  * Letter page, 1-inch margins, continuous line numbers, page numbers in the footer; "References" heading.
  The style template (tools/docx/reference.docx) is regenerated from pandoc's default by build_reference_doc().

  python tools/make_docx.py                       # -> paper/manuscript.docx, docs/METHODS.docx, paper/hybrid/...docx
  python tools/make_docx.py paper/manuscript.tex  # one manuscript (output next to it, .docx)
  python tools/make_docx.py IN.tex -o OUT.docx [--no-line-numbers] [--author-year]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

import docx
import pypandoc
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
FIGS = ROOT / "results" / "figures"
DOCX_DIR = ROOT / "tools" / "docx"
CSL_NUMERIC = DOCX_DIR / "elsevier-with-titles.csl"
CSL_HARVARD = PAPER / "elsevier-harvard.csl"
REFERENCE_DOC = DOCX_DIR / "reference.docx"

BODY_FONT = "Aptos"            # the author's Word theme fonts (body / headings) and heading colour
HEAD_FONT = "Aptos Display"
HEAD_COLOR = RGBColor(0x0F, 0x47, 0x61)
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
TEXT_WIDTH_TWIPS = 9360        # 6.5 in


# ----------------------------------------------------------------------------------------------------------------
# LaTeX helpers
# ----------------------------------------------------------------------------------------------------------------
def _balanced(s: str, i: int) -> int:
    """Index just past the brace group starting at s[i] == '{'."""
    if s[i] != "{":
        raise ValueError("expected '{' at %r" % s[i:i + 20])
    depth = 0
    for j in range(i, len(s)):
        c = s[j]
        if c in "{}" and j > 0 and s[j - 1] == "\\":
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j + 1
    raise ValueError("unbalanced braces")


def commands(tex: str, name: str):
    """Yield (start, end, optional_arg, argument) for every \\name[opt]{arg} in tex."""
    for m in re.finditer(r"\\%s(?![A-Za-z])\s*(\[[^\]]*\])?\s*(?=\{)" % re.escape(name), tex):
        j = m.end()
        k = _balanced(tex, j)
        yield m.start(), k, (m.group(1) or "")[1:-1], tex[j + 1:k - 1]


def first(tex: str, name: str):
    return next(commands(tex, name), None)


def strip_cmd(tex: str, name: str) -> str:
    out, last = [], 0
    for s, e, _, _ in commands(tex, name):
        out.append(tex[last:s])
        last = e
    return "".join(out) + tex[last:]


_ACCENTS = {"\"": "\u0308", "'": "\u0301", "`": "\u0300", "^": "\u0302", "~": "\u0303", "v": "\u030c",
            "c": "\u0327", "=": "\u0304", ".": "\u0307", "u": "\u0306", "H": "\u030b"}


def latex_to_text(s: str) -> str:
    """Plain text of a short LaTeX string (author names, affiliations)."""
    s = re.sub(r"\\([\"'`^~=.]|[vcuH](?![A-Za-z]))\s*\{?\\?([A-Za-z])\}?",
               lambda m: unicodedata.normalize("NFC", m.group(2) + _ACCENTS[m.group(1)]), s)
    s = s.replace("\\&", "&").replace("~", " ").replace("--", "\u2013").replace("\\,", "\u2009")
    s = re.sub(r"\\(textbf|textit|emph|texttt|mbox|textsc)\{([^{}]*)\}", r"\2", s)
    s = re.sub(r"\\[A-Za-z]+\s*", "", s)
    return re.sub(r"\s+", " ", s.replace("{", "").replace("}", "")).strip()


# ----------------------------------------------------------------------------------------------------------------
# Bibliography names (for \citet with a numeric style: "Kloppers and Kröger [14]")
# ----------------------------------------------------------------------------------------------------------------
def bib_authors(bib: Path) -> dict:
    text = bib.read_text(errors="replace")
    names = {}
    for m in re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,", text):
        key, j = m.group(1), m.end()
        nxt = text.find("\n@", j)
        body = text[j: nxt if nxt > 0 else len(text)]
        a = re.search(r"\b(author|editor)\s*=\s*", body, re.I)
        if not a:
            continue
        k = a.end()
        try:
            val = body[k + 1:_balanced(body, k) - 1] if body[k] == "{" else body[k + 1:body.index('"', k + 1)]
        except ValueError:
            continue
        people = [p.strip() for p in re.split(r"\s+and\s+", val) if p.strip()]

        def last(p):
            if p.startswith("{") and p.endswith("}"):
                return latex_to_text(p)
            if "," in p:
                return latex_to_text(p.split(",")[0])
            return latex_to_text(p.split()[-1])
        ln = [last(p) for p in people]
        if ln:
            names[key] = ln[0] if len(ln) == 1 else (
                "%s and %s" % (ln[0], ln[1]) if len(ln) == 2 else ln[0] + " et al.")
    return names


def citet_to_numeric(tex: str, names: dict) -> str:
    def rep(m):
        keys = [k.strip() for k in m.group(2).split(",")]
        if len(keys) == 1:
            return "%s~\\citep%s{%s}" % (names.get(keys[0], keys[0]), m.group(1) or "", keys[0])
        # as natbib's numeric \citet{a,b}: "Kloppers [2], Braun et al. [3]"
        return ", ".join("%s~\\citep{%s}" % (names.get(k, k), k) for k in keys)
    tex = re.sub(r"\\citet(\[[^\]]*\])?\{([^}]*)\}", rep, tex)
    return re.sub(r"\\citealp(?![A-Za-z])", r"\\citep", tex)


# ----------------------------------------------------------------------------------------------------------------
# Front matter
# ----------------------------------------------------------------------------------------------------------------
def parse_frontmatter(tex: str):
    """Return (tex with the frontmatter turned into Abstract/Highlights/Keywords sections, meta)."""
    meta = {"title": "", "authors": [], "affils": [], "email": "", "corr": ""}
    m = re.search(r"\\begin\{frontmatter\}(.*?)\\end\{frontmatter\}", tex, re.S)
    fm = m.group(1) if m else tex
    t = first(fm, "title")
    meta["title"] = latex_to_text(t[3]) if t else ""
    for cmd in ("affiliation", "address"):
        for _, _, opt, arg in commands(fm, cmd):
            if re.search(r"(organization|city|country)\s*=", arg):
                arg = ", ".join(re.findall(r"\w+\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", arg))
            meta["affils"].append((opt or chr(ord("a") + len(meta["affils"])), latex_to_text(arg)))
    for _, _, opt, arg in commands(fm, "author"):
        corr = "\\corref" in arg
        name = latex_to_text(strip_cmd(strip_cmd(arg, "corref"), "ead"))
        if not meta["affils"] and "," in name:          # old style: "\author{Name, Affiliation}"
            name, aff = [x.strip() for x in name.split(",", 1)]
            meta["affils"].append(("a", aff))
            opt = "a"
        labels = [x.strip() for x in opt.split(",") if x.strip()] or (["a"] if meta["affils"] else [])
        meta["authors"].append({"name": name, "affils": labels, "corr": corr})
    if len(meta["affils"]) == 1 and len(meta["authors"]) == 1 and meta["affils"][0][0] not in meta["authors"][0]["affils"]:
        meta["authors"][0]["affils"] = [meta["affils"][0][0]]
    e = first(fm, "ead")
    if e:
        meta["email"] = latex_to_text(e[3])
    c = first(fm, "cortext")
    if c:
        meta["corr"] = latex_to_text(c[3]).rstrip(".")
    if meta["authors"] and meta["email"] and not any(a["corr"] for a in meta["authors"]):
        meta["authors"][0]["corr"] = True
    parts = []
    a = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", fm, re.S)
    if a:
        parts.append("\\section*{Abstract}\n" + a.group(1).strip() + "\n")
    h = re.search(r"\\begin\{highlights\}(.*?)\\end\{highlights\}", fm, re.S)
    if h:
        parts.append("\\section*{Highlights}\n\\begin{itemize}\n" + h.group(1).strip() + "\n\\end{itemize}\n")
    k = re.search(r"\\begin\{keyword\}(.*?)\\end\{keyword\}", fm, re.S)
    if k:
        kw = [x.strip() for x in re.split(r"\\sep", k.group(1)) if x.strip()]
        parts.append("\\section*{Keywords}\n" + "; ".join(kw) + "\n")
    if m:
        tex = tex[:m.start()] + "\n".join(parts) + tex[m.end():]
    else:
        for cmd in ("title", "author", "address", "affiliation", "ead", "cortext"):
            tex = strip_cmd(tex, cmd)
        tex = tex.replace("\\maketitle", "")
    return tex, meta


# ----------------------------------------------------------------------------------------------------------------
# LaTeX preprocessing for pandoc
# ----------------------------------------------------------------------------------------------------------------
def latex_for_pandoc(tex: str, base: Path = PAPER, numeric: bool = True, bib: Path = PAPER / "references.bib"):
    """Return (pandoc-ready LaTeX, front-matter meta, number of numbered equations)."""
    tex = re.sub(r"(?<!\\)%.*", "", tex)                              # comments
    tex = re.sub(r"\\resizebox\{[^}]*\}\{[^}]*\}\{(\\input\{[^}]+\})\}", r"\1", tex)

    def inc(m):
        p = (base / m.group(1)).resolve()
        if p.suffix == "":
            p = p.with_suffix(".tex")
        return re.sub(r"(?<!\\)%.*", "", p.read_text()) if p.exists() else m.group(0)
    tex = re.sub(r"\\input\{([^}]+)\}", inc, tex)
    tex = re.sub(r"\\includegraphics(\[[^]]*\])?\{([^}]+)\}",
                 lambda m: r"\includegraphics%s{%s}" % (
                     m.group(1) or "", m.group(2) if Path(m.group(2)).suffix else (FIGS / (m.group(2) + ".png")).as_posix()),
                 tex)
    tex = re.sub(r"\\newcommand\{\\tbd\}\[1\]\{[^\n]*\}\n?", "", tex)
    tex = re.sub(r"\\tbd\{((?:[^{}]|\{[^{}]*\})*)\}", r"\\textbf{[TBD: \1]}", tex)
    tex = re.sub(r"\\graphicspath\{.*?\}\n", "", tex)
    tex, meta = parse_frontmatter(tex)
    # \paragraph{X} -> run-in bold lead, as typeset by LaTeX
    tex = re.sub(r"\\paragraph\*?\{([^{}]*)\}\s*", lambda m: "\\textbf{%s.} " % m.group(1).rstrip("."), tex)
    # appendix sections -> "Appendix A. Title"; their \ref -> "A"
    if "\\appendix" in tex:
        head, tail = tex.split("\\appendix", 1)
        letters, n = {}, [0]

        def app(m):
            letter = chr(ord("A") + n[0])
            n[0] += 1
            lab = re.match(r"\s*\\label\{([^}]*)\}", tail[m.end():])
            if lab:
                letters[lab.group(1)] = letter
            return "\\section*{Appendix %s. %s}" % (letter, m.group(1))
        tail = re.sub(r"\\section\{([^{}]*)\}", app, tail)
        tex = head + tail
        for lab, letter in letters.items():
            tex = tex.replace("\\ref{%s}" % lab, letter)
    # numbered equations: \eqref -> (n); a marker paragraph after each, numbered by the post-processor
    eqn, labels = [0], {}

    def eq(m):
        eqn[0] += 1
        body = m.group(1)
        for lab in re.findall(r"\\label\{([^}]*)\}", body):
            labels[lab] = eqn[0]
        body = re.sub(r"\\label\{[^}]*\}", "", body)
        return "\\[%s\\]\n\nEQNUMMARK%d\n\n" % (body.strip(), eqn[0])
    tex = re.sub(r"\\begin\{equation\}(.*?)\\end\{equation\}", eq, tex, flags=re.S)
    for lab, k in labels.items():
        tex = tex.replace("\\eqref{%s}" % lab, "(%d)" % k).replace("\\ref{%s}" % lab, str(k))
    if numeric and bib.exists():
        tex = citet_to_numeric(tex, bib_authors(bib))
    tex = tex.replace("{../references}", "{references}")
    return tex, meta, eqn[0]


# ----------------------------------------------------------------------------------------------------------------
# Style template
# ----------------------------------------------------------------------------------------------------------------
def _set_font(style, name, size=None, bold=None, italic=None, color=None):
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for k in list(rf.attrib):
        if k.endswith("Theme"):
            del rf.attrib[k]
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)
    f = style.font
    if size is not None:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if color is not None:
        f.color.rgb = color


def _para(style, before=None, after=None, line=None, align=None, keep_next=None, indent=None, hanging=None):
    pf = style.paragraph_format
    if before is not None:
        pf.space_before = Pt(before)
    if after is not None:
        pf.space_after = Pt(after)
    if line is not None:
        pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        pf.line_spacing = line
    if align is not None:
        pf.alignment = align
    if keep_next is not None:
        pf.keep_with_next = keep_next
    if indent is not None:
        pf.left_indent = Inches(indent)
    if hanging is not None:
        pf.first_line_indent = Inches(-hanging)


def build_reference_doc(out: Path = REFERENCE_DOC) -> Path:
    """Pandoc's default reference.docx with the manuscript's fonts, sizes and spacing (rebuilt when this script changes)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size > 0 and out.stat().st_mtime >= Path(__file__).stat().st_mtime:
        return out
    with open(out, "wb") as fh:
        subprocess.run([pypandoc.get_pandoc_path(), "--print-default-data-file", "reference.docx"],
                       stdout=fh, check=True)
    d = docx.Document(str(out))
    st = d.styles

    def get(name, base="Normal"):
        try:
            return st[name]
        except KeyError:
            s = st.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            s.base_style = st[base]
            return s
    _set_font(get("Normal"), BODY_FONT, 11)
    _para(get("Normal"), after=0)
    for name in ("Body Text", "First Paragraph"):
        _set_font(get(name), BODY_FONT, 11)
        _para(get(name), before=0, after=6, line=1.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    _set_font(get("Compact"), BODY_FONT, 11)
    _para(get("Compact"), before=0, after=2, line=1.15)
    for lvl, size in ((1, 16), (2, 16), (3, 14), (4, 12), (5, 12)):
        s = get("Heading %d" % lvl)
        _set_font(s, HEAD_FONT, size, bold=True, italic=False, color=HEAD_COLOR)
        _para(s, before=18 if lvl == 1 else 12, after=6, line=1.0, keep_next=True, align=WD_ALIGN_PARAGRAPH.LEFT)
    s = get("Title")
    _set_font(s, HEAD_FONT, 18, bold=True, color=RGBColor(0, 0, 0))
    _para(s, before=0, after=12, line=1.1, align=WD_ALIGN_PARAGRAPH.CENTER)
    for name, size, italic in (("Author", 12, False), ("Affiliation", 10, True), ("Correspondence", 10, False)):
        s = get(name)
        _set_font(s, BODY_FONT, size, bold=False, italic=italic)
        _para(s, before=0, after=4, line=1.0, align=WD_ALIGN_PARAGRAPH.CENTER)
    for name, before, after in (("Table Caption", 10, 4), ("Image Caption", 4, 12)):
        s = get(name, "Caption") if "Caption" in [x.name for x in st] else get(name)
        _set_font(s, BODY_FONT, 10, italic=False)
        _para(s, before=before, after=after, line=1.0, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
              keep_next=(name == "Table Caption"))
    for name in ("Captioned Figure", "Figure"):
        _para(get(name), before=8, after=0, align=WD_ALIGN_PARAGRAPH.CENTER, keep_next=True)
    s = get("Bibliography")
    _set_font(s, BODY_FONT, 10)
    _para(s, before=0, after=3, line=1.0, align=WD_ALIGN_PARAGRAPH.LEFT, indent=0.4, hanging=0.4)
    try:
        h = st["Hyperlink"]
        h.font.color.rgb = HEAD_COLOR
        h.font.underline = False
    except KeyError:
        pass
    # line numbers off in tables, captions, references and the front block
    for name in ("Compact", "Table Caption", "Image Caption", "Bibliography", "Title", "Author", "Affiliation",
                 "Correspondence", "Captioned Figure", "Figure"):
        try:
            ppr = st[name].element.get_or_add_pPr()
        except KeyError:
            continue
        if ppr.find(qn("w:suppressLineNumbers")) is None:
            _insert_ppr(ppr, OxmlElement("w:suppressLineNumbers"))
    d.save(str(out))
    return out


# ----------------------------------------------------------------------------------------------------------------
# Post-processing
# ----------------------------------------------------------------------------------------------------------------
_PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
              "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
              "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid",
              "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
              "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"]
_RPR_ORDER = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline",
              "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing", "w",
              "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign",
              "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath"]


def _insert_ppr(ppr, el):
    """Insert el into a w:pPr at its schema position."""
    rank = {qn("w:" + t): i for i, t in enumerate(_PPR_ORDER)}
    me = rank[el.tag]
    for c in ppr:
        if rank.get(c.tag, 99) > me:
            c.addprevious(el)
            return el
    ppr.append(el)
    return el


def _ppr_child(ppr, tag):
    el = ppr.find(qn(tag))
    return el if el is not None else _insert_ppr(ppr, OxmlElement(tag))


def _order_rpr(root):
    rank = {qn("w:" + t): i for i, t in enumerate(_RPR_ORDER)}
    for rpr in root.iter(qn("w:rPr")):
        kids = list(rpr)
        if all(k.tag in rank for k in kids):
            for k in sorted(kids, key=lambda k: rank[k.tag]):
                rpr.remove(k)
                rpr.append(k)


def _run(text, bold=False, italic=False, superscript=False, size=None):
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    if bold:
        rpr.append(OxmlElement("w:b"))
    if italic:
        rpr.append(OxmlElement("w:i"))
    if size:
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(size * 2)))
        rpr.append(sz)
    if superscript:
        v = OxmlElement("w:vertAlign")
        v.set(qn("w:val"), "superscript")
        rpr.append(v)
    if len(rpr):
        r.append(rpr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def _p(style_id, runs):
    p = OxmlElement("w:p")
    ppr = OxmlElement("w:pPr")
    ps = OxmlElement("w:pStyle")
    ps.set(qn("w:val"), style_id)
    ppr.append(ps)
    p.append(ppr)
    for r in runs:
        p.append(r)
    return p


def _sid(d, name):
    return d.styles[name].style_id


def _pstyle(p):
    ps = p.find(qn("w:pPr") + "/" + qn("w:pStyle"))
    return None if ps is None else ps.get(qn("w:val"))


def front_block(d, meta):
    """Title, authors with superscript affiliation letters, affiliations, corresponding author."""
    els = []
    if meta["title"]:
        els.append(_p(_sid(d, "Title"), [_run(meta["title"])]))
    if meta["authors"]:
        runs = []
        n = len(meta["authors"])
        for i, a in enumerate(meta["authors"]):
            if i:
                runs.append(_run(", " if i < n - 1 else " and "))
            runs.append(_run(a["name"]))
            sup = ",".join(a["affils"]) + ("*" if a["corr"] else "")
            if sup:
                runs.append(_run(sup, superscript=True))
        els.append(_p(_sid(d, "Author"), runs))
    for label, text in meta["affils"]:
        els.append(_p(_sid(d, "Affiliation"), [_run(label, superscript=True), _run(" " + text)]))
    if meta["email"]:
        els.append(_p(_sid(d, "Correspondence"),
                      [_run("*%s: %s" % (meta["corr"] or "Corresponding author", meta["email"]))]))
    anchor = d.element.body[0]
    for e in els:
        anchor.addprevious(e)


def _seq_field(kind: str, n: int):
    f = OxmlElement("w:fldSimple")
    f.set(qn("w:instr"), " SEQ %s \\* ARABIC " % kind)
    f.append(_run(str(n), bold=True))
    return f


def number_captions(d):
    """Prefix 'Table N.' / 'Figure N.' (SEQ fields) to pandoc's caption paragraphs, in document order."""
    kinds = {_sid(d, "Table Caption"): "Table", _sid(d, "Image Caption"): "Figure"}
    counts = {"Table": 0, "Figure": 0}
    for p in d.element.body.iter(qn("w:p")):
        kind = kinds.get(_pstyle(p))
        if not kind:
            continue
        counts[kind] += 1
        ppr = p.find(qn("w:pPr"))
        ppr.addnext(_run(". ", bold=True))
        ppr.addnext(_seq_field(kind, counts[kind]))
        ppr.addnext(_run(kind + " ", bold=True))
    return counts


def _border_set(edges=("top", "left", "bottom", "right", "insideH", "insideV"), sz=4):
    b = OxmlElement("w:tblBorders")
    for e in edges:
        x = OxmlElement("w:" + e)
        x.set(qn("w:val"), "single")
        x.set(qn("w:sz"), str(sz))
        x.set(qn("w:space"), "0")
        x.set(qn("w:color"), "000000")
        b.append(x)
    return b


def format_tables(d, font_pt=9.0):
    """All-lines borders, full width, bold repeated header row, compact 9 pt cells."""
    n = 0
    sz = str(int(round(font_pt * 2)))
    for tbl in d.element.body.iter(qn("w:tbl")):
        n += 1
        tpr = tbl.find(qn("w:tblPr"))
        look = tpr.find(qn("w:tblLook"))
        header = look is not None and look.get(qn("w:firstRow")) == "1"
        # rebuild tblPr in schema order: tblStyle, tblW, jc, tblBorders, tblLayout, tblCellMar, tblLook
        style = tpr.find(qn("w:tblStyle"))
        for c in list(tpr):
            tpr.remove(c)
        if style is not None:
            tpr.append(style)
        tw = OxmlElement("w:tblW")
        tw.set(qn("w:type"), "pct")
        tw.set(qn("w:w"), "5000")
        tpr.append(tw)
        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), "center")
        tpr.append(jc)
        tpr.append(_border_set())
        lay = OxmlElement("w:tblLayout")
        lay.set(qn("w:type"), "autofit")
        tpr.append(lay)
        mar = OxmlElement("w:tblCellMar")
        for e, v in (("left", "70"), ("right", "70")):
            x = OxmlElement("w:" + e)
            x.set(qn("w:w"), v)
            x.set(qn("w:type"), "dxa")
            mar.append(x)
        tpr.append(mar)
        if look is not None:
            tpr.append(look)
        for i, tr in enumerate(tbl.findall(qn("w:tr"))):
            is_head = (header and i == 0) or tr.find(qn("w:trPr") + "/" + qn("w:tblHeader")) is not None
            if is_head:
                trpr = tr.find(qn("w:trPr"))
                if trpr is None:
                    trpr = OxmlElement("w:trPr")
                    tcpr_first = tr.find(qn("w:tc"))
                    tcpr_first.addprevious(trpr)
                if trpr.find(qn("w:tblHeader")) is None:
                    trpr.append(OxmlElement("w:tblHeader"))
            for p in tr.iter(qn("w:p")):
                ppr = p.find(qn("w:pPr"))
                if ppr is None:
                    ppr = OxmlElement("w:pPr")
                    p.insert(0, ppr)
                sp = _ppr_child(ppr, "w:spacing")
                sp.set(qn("w:before"), "20")
                sp.set(qn("w:after"), "20")
                sp.set(qn("w:line"), "240")
                sp.set(qn("w:lineRule"), "auto")
            for r in list(tr.iter(qn("w:r"))) + list(tr.iter("{%s}r" % M_NS)):
                math = r.tag == "{%s}r" % M_NS
                rpr = r.find(qn("w:rPr"))
                if rpr is None:
                    rpr = OxmlElement("w:rPr")
                    if math:      # m:r children: m:rPr?, w:rPr?, m:t
                        mt = r.find("{%s}t" % M_NS)
                        if mt is None:
                            continue
                        mt.addprevious(rpr)
                    else:
                        r.insert(0, rpr)
                if is_head and not math and rpr.find(qn("w:b")) is None:
                    rpr.append(OxmlElement("w:b"))
                for tag in ("w:sz", "w:szCs"):
                    el = rpr.find(qn(tag))
                    if el is None:
                        el = OxmlElement(tag)
                        rpr.append(el)
                    el.set(qn("w:val"), sz)
        _order_rpr(tbl)
    return n


def number_equations(d):
    """'display-math paragraph + EQNUMMARKn paragraph' -> one paragraph: centred equation, '(n)' right-aligned."""
    done = 0
    for p in list(d.element.body.iter(qn("w:p"))):
        txt = "".join(t.text or "" for t in p.iter(qn("w:t")))
        m = re.fullmatch(r"\s*EQNUMMARK(\d+)\s*", txt)
        if not m:
            continue
        prev = p.getprevious()
        omp = prev.find("{%s}oMathPara" % M_NS) if prev is not None else None
        p.getparent().remove(p)
        if omp is None:
            continue
        ppr = prev.find(qn("w:pPr"))
        if ppr is None:
            ppr = OxmlElement("w:pPr")
            prev.insert(0, ppr)
        tabs = _ppr_child(ppr, "w:tabs")
        for val, pos in (("center", TEXT_WIDTH_TWIPS // 2), ("right", TEXT_WIDTH_TWIPS)):
            tb = OxmlElement("w:tab")
            tb.set(qn("w:val"), val)
            tb.set(qn("w:pos"), str(pos))
            tabs.append(tb)
        sp = _ppr_child(ppr, "w:spacing")
        sp.set(qn("w:before"), "60")
        sp.set(qn("w:after"), "60")
        _ppr_child(ppr, "w:jc").set(qn("w:val"), "left")
        tab_run = OxmlElement("w:r")
        tab_run.append(OxmlElement("w:tab"))
        omp.addprevious(tab_run)
        for mth in omp.findall("{%s}oMath" % M_NS):
            omp.addprevious(mth)
        num = OxmlElement("w:r")
        num.append(OxmlElement("w:tab"))
        t = OxmlElement("w:t")
        t.text = "(%s)" % m.group(1)
        num.append(t)
        omp.addprevious(num)
        omp.getparent().remove(omp)
        done += 1
    return done


def tidy_headings(d):
    """Pandoc writes '1<tab>Introduction'; use '1 Introduction' as in the author's edits."""
    ids = set()
    for i in range(1, 7):
        try:
            ids.add(_sid(d, "Heading %d" % i))
        except KeyError:
            pass
    n = 0
    for p in d.element.body.iter(qn("w:p")):
        if _pstyle(p) not in ids:
            continue
        for tab in [t for t in p.iter(qn("w:tab")) if t.getparent().tag == qn("w:r")]:
            t = OxmlElement("w:t")
            t.set(qn("xml:space"), "preserve")
            t.text = " "
            tab.addprevious(t)
            tab.getparent().remove(tab)
            n += 1
    return n


def left_align_after(d, heading_text):
    """Left-align the paragraph that follows a heading (keywords line: no justification gaps)."""
    body = list(d.element.body)
    for i, el in enumerate(body[:-1]):
        if el.tag == qn("w:p") and "".join(t.text or "" for t in el.iter(qn("w:t"))).strip() == heading_text:
            nxt = body[i + 1]
            ppr = nxt.find(qn("w:pPr"))
            if ppr is None:
                ppr = OxmlElement("w:pPr")
                nxt.insert(0, ppr)
            _ppr_child(ppr, "w:jc").set(qn("w:val"), "left")


def page_setup(d, line_numbers=True):
    for s in d.sections:
        s.page_width, s.page_height = Inches(8.5), Inches(11)
        s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(1)
        s.header_distance = s.footer_distance = Inches(0.5)
        s.gutter = Inches(0)          # pgMar requires w:gutter (schema)
        sp = s._sectPr
        for old in sp.findall(qn("w:lnNumType")):
            sp.remove(old)
        if line_numbers:
            ln = OxmlElement("w:lnNumType")
            ln.set(qn("w:countBy"), "1")
            ln.set(qn("w:distance"), "283")
            ln.set(qn("w:restart"), "continuous")
            # schema order: ..., pgSz, pgMar, paperSrc, pgBorders, lnNumType, pgNumType, cols, ...
            after = None
            for tag in ("w:pgBorders", "w:paperSrc", "w:pgMar", "w:pgSz"):
                after = sp.find(qn(tag))
                if after is not None:
                    break
            (after.addnext(ln) if after is not None else sp.insert(0, ln))
        f = s.footer
        f.is_linked_to_previous = False
        p = f.paragraphs[0] if f.paragraphs else f.add_paragraph()
        for r in list(p._p):
            if r.tag != qn("w:pPr"):
                p._p.remove(r)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), " PAGE ")
        fld.append(_run("1", size=10))
        p._p.append(fld)


# ----------------------------------------------------------------------------------------------------------------
# Conversion
# ----------------------------------------------------------------------------------------------------------------
def convert_manuscript(tex: Path = PAPER / "manuscript.tex", out: Path = PAPER / "manuscript.docx",
                       numeric: bool = True, line_numbers: bool = True, number_sections: bool = True) -> Path:
    tex, out = Path(tex).resolve(), Path(out).resolve()
    bib = tex.parent / "references.bib"
    if not bib.exists():
        bib = PAPER / "references.bib"
    src, meta, _ = latex_for_pandoc(tex.read_text(), tex.parent, numeric=numeric, bib=bib)
    ref = build_reference_doc()
    csl = CSL_NUMERIC if numeric else CSL_HARVARD
    args = ["--citeproc", "--bibliography", str(bib), "--resource-path", "%s:%s" % (FIGS, tex.parent),
            "--reference-doc", str(ref), "-M", "reference-section-title=References", "-M", "link-citations=false"]
    if csl.exists():
        args += ["--csl", str(csl)]
    if number_sections:
        args.append("--number-sections")
    with tempfile.NamedTemporaryFile("w", suffix=".tex", dir=tex.parent, delete=False) as fh:
        fh.write(src)
        tmp = Path(fh.name)
    try:
        pypandoc.convert_file(str(tmp), "docx", format="latex", outputfile=str(out), extra_args=args)
    finally:
        tmp.unlink()
    d = docx.Document(str(out))
    front_block(d, meta)
    number_captions(d)
    format_tables(d)
    number_equations(d)
    tidy_headings(d)
    left_align_after(d, "Keywords")
    page_setup(d, line_numbers=line_numbers)
    d.save(str(out))
    return out


def convert_methods(src=None, out=None):
    """Markdown document -> docx with the house style (default: docs/METHODS.md)."""
    src = Path(src or ROOT / "docs" / "METHODS.md")
    out = Path(out or src.with_suffix(".docx"))
    pypandoc.convert_file(str(src), "docx", format="markdown", outputfile=str(out),
                          extra_args=["--resource-path", str(src.parent), "--reference-doc",
                                      str(build_reference_doc())])
    d = docx.Document(str(out))
    format_tables(d)
    page_setup(d, line_numbers=False)
    d.save(str(out))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tex", nargs="?", type=Path, help="one manuscript .tex or markdown .md (default: all documents)")
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--author-year", action="store_true", help="Elsevier Harvard citations instead of numbered")
    ap.add_argument("--no-line-numbers", action="store_true")
    a = ap.parse_args(argv)
    kw = dict(numeric=not a.author_year, line_numbers=not a.no_line_numbers)
    if a.tex and a.tex.suffix == ".md":
        outs = [convert_methods(a.tex, a.out)]
    elif a.tex:
        outs = [convert_manuscript(a.tex, a.out or a.tex.with_suffix(".docx"), **kw)]
    else:
        outs = [convert_manuscript(**kw), convert_methods()]
        resp = PAPER / "RESPONSE_author_comments_v1.md"
        if resp.exists():
            outs.append(convert_methods(resp))
        hyb = PAPER / "hybrid" / "manuscript_hybrid.tex"
        if hyb.exists():
            outs.append(convert_manuscript(hyb, PAPER / "hybrid" / "manuscript_hybrid.docx", **kw))
    for f in outs:
        print("wrote", f, "%.0f kB" % (f.stat().st_size / 1e3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
