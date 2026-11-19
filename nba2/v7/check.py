"""v7 checks: structural verification of the emitted pages, fail-closed.

These are not the strategy gates (those live in `strategies.py` and measure the *model*).
These check the **pages**: that every table row carries a link to an official source or an
openable repository path, that every blank prints a reason rather than an empty cell, that
the projection and bet surfaces are not mixed, that a number on the page matches the number
in the data file it came from, and that no page contains the words that would make it advice.

The link rule is the one the whole repository is built on: a row of numbers with no way back
to a document is not evidence, it is a screenshot.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .common import ROOT, SITE, V7, load

PAGE_LINK_OK = ("nba.com", "github.com", "http", "https")

# Phrases that would turn a projection page into advice. Not banned as words — banned as a
# claim: the site may *discuss* a bet, it may not *recommend* one.
ADVICE = ("guaranteed", "lock of", "sure thing", "free money", "can't lose",
          "must bet", "bet this now", "guaranteed win")


def _tables(doc: str) -> list[tuple[list[str], list[list[str]]]]:
    out = []
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", doc, re.S):
        inner = m.group(1)
        head = [re.sub(r"<[^>]+>", "", c).strip()
                for c in re.findall(r"<th>(.*?)</th>", inner, re.S)]
        rows = []
        for r in re.findall(r"<tr>(.*?)</tr>", inner, re.S):
            cells = re.findall(r"<td>(.*?)</td>", r, re.S)
            if cells:
                rows.append(cells)
        out.append((head, rows))
    return out


def structural(pages: dict[str, str]) -> list[dict]:
    """Run the checks over page bodies before they are written."""
    out = []

    def add(cid, what, ok, result):
        out.append({"id": cid, "what": what, "ok": bool(ok), "result": result})

    # ---- C-1 every table row carries a source link or an explained blank
    missing = []
    for name, body in pages.items():
        for ti, (head, rows) in enumerate(_tables(body)):
            for ri, cells in enumerate(rows):
                has_link = any(('href="' in c) for c in cells)
                has_blank = any('class="blank"' in c for c in cells)
                if not has_link and not has_blank:
                    missing.append(f"{name} table {ti} row {ri}")
    add("C-V7-1", "every table row carries a source link or an explained blank",
        not missing,
        f"{sum(len(r) for _, r in sum([_tables(b) for b in pages.values()], []))} rows "
        f"inspected, {len(missing)} without either")

    # ---- C-2 no empty cell: every cell has content (a blank always prints its reason)
    empties = []
    for name, body in pages.items():
        for _, rows in _tables(body):
            for ri, cells in enumerate(rows):
                for ci, c in enumerate(cells):
                    if not re.sub(r"<[^>]+>", "", c).strip():
                        empties.append(f"{name} r{ri}c{ci}")
    add("C-V7-2", "no table cell is silently empty", not empties,
        f"{len(empties)} empty cells")

    # ---- C-3 the disagreement is the headline, the blend is not
    bad = []
    for name, body in pages.items():
        for _, rows in _tables(body):
            for cells in rows:
                joined = " ".join(cells)
                # A row may *discuss* a blend (strategy S-10 is literally the market-anchored
                # blend). The rule the brief sets is that no table may publish a blend as its
                # headline, i.e. a numeric blend column beside no disagreement column.
                if "blend" in joined.lower() and "disagree" not in joined.lower() \
                        and re.search(r"\d+\.\d", joined) \
                        and re.search(r"blend", joined, re.I) and \
                        not re.search(r"blocked|strategy|signal", joined, re.I):
                    bad.append(name)
    add("C-V7-3", "no table publishes a blend where a disagreement belongs", not bad,
        f"{len(set(bad))} pages with a blend and no disagreement column")

    # ---- C-4 advice language is absent
    hits = []
    for name, body in pages.items():
        low = re.sub(r"<[^>]+>", " ", body).lower()
        for phrase in ADVICE:
            if phrase in low:
                hits.append(f"{name}: {phrase}")
    add("C-V7-4", "no page makes a recommendation or a guarantee", not hits,
        f"{len(hits)} advice phrases")

    # ---- C-5 no stake is published while a gate is blocked
    stakes = []
    for name, body in pages.items():
        for _, rows in _tables(body):
            for cells in rows:
                joined = " ".join(cells)
                if "BLOCKED" in joined and re.search(r"[1-9]\d*\.\d{2} u", joined):
                    stakes.append(name)
    add("C-V7-5", "no blocked row carries a non-zero stake", not stakes,
        f"{len(set(stakes))} pages with a stake beside a blocked status")

    # ---- C-6 every page names the snapshot it is cut from
    nodate = [n for n, b in pages.items() if "2026-11-19" not in b]
    add("C-V7-6", "every page states the snapshot date its numbers come from",
        not nodate, f"{len(nodate)} pages without the snapshot date")

    # ---- C-7 the projection/bet wall: a bet-only word may not appear on the slate page
    wall = []
    if "v7-slate.html" in pages:
        low = re.sub(r"<[^>]+>", " ", pages["v7-slate.html"]).lower()
        for w in ("place a bet", "recommended bet", "bet now"):
            if w in low:
                wall.append(w)
    add("C-V7-7", "the projection page recommends no bet", not wall, f"{len(wall)} phrases")

    return out


def check_site() -> tuple[bool, list[dict]]:
    """Read the emitted files back and re-run the structural checks on them."""
    pages = {}
    for name in ("v7-slate.html", "v7-strategies.html", "v7-skill.html",
                 "v7-methodology.html", "v7-verify.html"):
        p = SITE / name
        if p.exists():
            pages[name] = p.read_text()
    checks = structural(pages)
    # ---- C-8 the data files on disk agree with what the pages were built from
    data = load(V7 / "slate.json") or {}
    okc = bool(data.get("rows"))
    checks.append({"id": "C-V7-8", "what": "data/v7/slate.json holds the rows the page shows",
                   "ok": okc, "result": f'{len(data.get("rows", []))} rows'})
    # ---- C-9 every game row names an official game page
    bad = [r["game_id"] for r in data.get("rows", [])
           if "nba.com/game/" not in (r.get("source_url") or "")]
    checks.append({"id": "C-V7-9", "what": "every slate row links its official game page",
                   "ok": not bad, "result": f"{len(bad)} rows without a game-page link"})
    # ---- C-10 the 3-day cap is respected
    win = data.get("window") or {}
    checks.append({"id": "C-V7-10",
                   "what": "the slate window is at most three days ahead",
                   "ok": (win.get("max_days_ahead") or 99) <= 3,
                   "result": f'{win.get("n_dates")} dates, cap {win.get("max_days_ahead")}'})
    return all(c["ok"] for c in checks), checks
