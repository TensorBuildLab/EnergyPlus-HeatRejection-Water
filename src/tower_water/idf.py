"""Minimal IDF reader/writer (no comments kept). Enough to inspect and patch models."""
from __future__ import annotations

from typing import List


def parse(text: str) -> List[List[str]]:
    """Return objects as lists of fields; field 0 is the class name."""
    lines = [ln.split("!", 1)[0] for ln in text.splitlines()]
    body = "\n".join(lines)
    objs = []
    for chunk in body.split(";"):
        fields = [f.strip() for f in chunk.split(",")]
        if fields and fields[0]:
            objs.append(fields)
    return objs


def dump(objs: List[List[str]]) -> str:
    out = []
    for o in objs:
        out.append(o[0] + ",\n" + ",\n".join("    " + f for f in o[1:]) + ";\n")
    return "\n".join(out)


def obj(cls: str, *fields) -> List[str]:
    return [cls] + [str(f) for f in fields]


def find(objs, cls: str):
    c = cls.lower()
    return [o for o in objs if o[0].lower() == c]


def field(o: List[str], i: int, default: str = "") -> str:
    """Field i (0 = Name) of an object."""
    return o[i + 1] if len(o) > i + 1 and o[i + 1] != "" else default
