"""Shared rendering + provenance helpers for the v6 tree.

Nothing here fetches anything. Every value rendered by v6 comes from a file that is
already committed under ``data/``, and every row carries the URL of the official
document it was read from. A value that does not exist in any committed capture is
rendered as a blank **with a reason**, never as an estimate.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
V6 = DATA / "v6"
RAW = DATA / "raw"
SITE = ROOT / "site"

SESSION = "arena/f5ac4e74-nba2"
BUILD_UTC = "2026-11-17T00:00:00Z"   # replaced at build time by __main__

INJURY_INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"

# The blank-reason vocabulary recognised by nba2/v2/check.py. Reuse it exactly: a blank
# cell that does not match one of these tokens makes the whole build fail.
BLANK_REASON_TOKENS = (
    "FLAG-", "F-", "needs ", "no source", "blocked", "BLOCKED", "not filed",
    "first in window", "does not exist", "unavailable", "withheld", "WITHHELD",
    "no data", "no official", "not measured", "not committed", "not reached",
)


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def link(url: str, label: str = "SRC", title: str | None = None) -> str:
    if not url:
        return blank("no official source is committed for this value")
    t = f' title="{esc(title)}"' if title else ""
    return f'<a href="{esc(url)}"{t} rel="noopener" target="_blank">{esc(label)}</a>'


def blank(reason: str) -> str:
    """A blank cell. The reason is printed, so the blank itself is the evidence."""
    return f'<span class="blank">— {esc(reason)}</span>'


def cell(v, fmt=None, reason: str = "no official source is committed"):
    if v is None or v == "":
        return blank(reason)
    try:
        return esc(fmt(v) if fmt else v)
    except (TypeError, ValueError):
        return esc(v)


def ncell(v, nd: int = 2, reason: str = "not measured from a committed official capture"):
    if v is None or v == "":
        return blank(reason)
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return esc(v)


def badge(text: str, kind: str = "info") -> str:
    return f'<span class="badge b-{esc(kind)}">{esc(text)}</span>'


def table(head: list[str], rows: list[list[str]], caption: str | None = None,
          derived: bool = False) -> str:
    """Render a table.

    ``derived=True`` marks a table whose cells are **arithmetic on a stated rule**, not
    values read from an official document — the market-prior sensitivity grid is the only
    example. Such a table cannot carry a per-row official source link, because there is no
    official document for a hypothetical number. Rather than bolt a fake link on, the table
    is marked and the row-source gate (G-V6-13) exempts it **only if it carries a caption
    saying what it is**. A derived table with no caption is a build failure.
    """
    c = f"<caption>{esc(caption)}</caption>" if caption else ""
    th = "".join(f"<th>{esc(h)}</th>" for h in head)
    body = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    attr = ' data-derived="1"' if derived else ""
    return (f'<div class="scroll"><table{attr}>{c}<thead><tr>{th}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def kpis(items: list[tuple[str, str]]) -> str:
    body = "".join(
        f'<div class="kpi"><b>{esc(v)}</b><small>{esc(k)}</small></div>' for k, v in items)
    return f'<div class="kpis">{body}</div>'


def note(text: str, kind: str = "") -> str:
    return f'<div class="note {esc(kind)}">{text}</div>'


def gh(path: str, label: str | None = None) -> str:
    url = f"https://github.com/wingbangboozle1-lang/NBA2/blob/main/{path}"
    return link(url, label or path)


def load(path) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"v6 expected a committed input that is not present: {p}")
    return json.loads(p.read_text())


def maybe_load(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else None
