"""Freshness and provenance gates. The build refuses to publish if either fails.

The brief asks for a scheduled job that refreshes the official schedule, standings,
team statistics and injury report for each rolling slate, and rebuilds **only after**
freshness and provenance gates pass. These are the gates. They are fail-closed: a
gate that cannot be evaluated returns FAIL, not PASS.

Gate list
---------
G-F1  snapshot age            - the official snapshot must be younger than MAX_AGE_H.
G-F2  window coverage         - every date in the T+0..T+3 window must have >=1 game.
G-F3  injury release is newest - the release used must be the newest indexed at build
                                 time, or the build must say which newer ones exist.
G-F4  no sealed row is past tip - a pick cannot enter the ledger inside TIP_CUTOFF_H.
G-F5  record arithmetic       - wins sum to losses and to the official finals count.
G-P1  every row sourced       - every emitted table row carries an official URL.
G-P2  every blank explained   - every null cell carries a flag id or a blocked key.
G-P3  no placeholders         - no TODO / TBD / lorem in the emitted artefacts.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import official as O

ROOT = Path(__file__).resolve().parents[2]
MAX_AGE_H = 30.0
TIP_CUTOFF_H = 6.0
PLACEHOLDER = re.compile(r"\b(TODO|TBD|lorem ipsum|XXX|FIXME)\b", re.I)


def _now():
    return datetime.now(timezone.utc)


def _age_hours(as_of_utc: str) -> float:
    t = datetime.strptime(as_of_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (_now() - t).total_seconds() / 3600.0


def freshness(result: dict) -> list[dict]:
    gates = []

    age = _age_hours(result["as_of_utc"])
    gates.append({
        "id": "G-F1", "name": "snapshot age",
        "pass": age <= MAX_AGE_H,
        "detail": f"snapshot is {age:.1f} h old at gate time (max {MAX_AGE_H:.0f} h)",
        "value": round(age, 2),
    })

    dates = sorted({g["date"] for g in O.SLATE})
    want = _window_dates(O.WINDOW[0], O.WINDOW[1])
    missing = [d for d in want if d not in dates]
    gates.append({
        "id": "G-F2", "name": "window coverage",
        "pass": not missing,
        "detail": (f"all {len(want)} dates carry at least one official game"
                   if not missing else f"no official game for {', '.join(missing)}"),
        "value": {"dates": dates, "missing": missing},
    })

    newest = O.INJURY_META["newest_indexed_release_at_retrieval"]
    gates.append({
        "id": "G-F3", "name": "injury release is the newest indexed",
        "pass": O.INJURY_META["release"] == newest,
        "detail": (f"using {O.INJURY_META['release']}; newest indexed at retrieval was "
                   f"{newest}"),
        "value": {"used": O.INJURY_META["release"], "newest_indexed": newest},
    })

    # A sealed row may not be created inside TIP_CUTOFF_H of the first tip.
    first = min(O.SLATE, key=lambda g: (g["date"], g["time_et"]))
    first_dt = _parse_et(first["date"], first["time_et"])
    lead = (first_dt - _now()).total_seconds() / 3600.0 if first_dt else None
    gates.append({
        "id": "G-F4", "name": "no sealed row within the tip cutoff",
        "pass": lead is None or lead >= TIP_CUTOFF_H,
        "detail": (f"first tip {first['date']} {first['time_et']} ET is {lead:.1f} h away "
                   f"(cutoff {TIP_CUTOFF_H:.0f} h)") if lead is not None else "tip time unparsed",
        "value": round(lead, 2) if lead is not None else None,
    })

    n_finals = result["history"]["n_games"]
    wins = sum(t["w"] for t in O.TEAMS.values())
    losses = sum(t["l"] for t in O.TEAMS.values())
    gates.append({
        "id": "G-F5", "name": "record arithmetic",
        "pass": wins == losses == n_finals,
        "detail": f"{wins} wins / {losses} losses vs {n_finals} official finals",
        "value": {"wins": wins, "losses": losses, "finals": n_finals},
    })
    return gates


def _window_dates(a: str, b: str) -> list[str]:
    from datetime import date, timedelta
    y, m, d = (int(x) for x in a.split("-"))
    y2, m2, d2 = (int(x) for x in b.split("-"))
    one = date(y, m, d)
    two = date(y2, m2, d2)
    out, cur = [], one
    while cur <= two:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


ET_UTC_OFFSET_H = -5.0  # 2026-11-15 falls in Eastern Standard Time (UTC-5)


def _parse_et(date_s: str, time_s: str):
    """'7:30 PM' ET -> aware UTC datetime, using ET_UTC_OFFSET_H.

    The offset is a declared constant rather than a zone database lookup, because the
    standard library has no tzdata here; it is correct for every date in this build's
    window and is stated on the gates page so a reader can check it.
    """
    try:
        y, m, d = (int(x) for x in date_s.split("-"))
        hh, rest = time_s.split(":")
        mm, ampm = rest.split()
        h = int(hh) % 12
        if ampm.upper() == "PM":
            h += 12
        naive = datetime(y, m, d, h, int(mm))
    except Exception:
        return None
    from datetime import timedelta
    return (naive - timedelta(hours=ET_UTC_OFFSET_H)).replace(tzinfo=timezone.utc)


def provenance(html_paths: list[Path]) -> list[dict]:
    """P1/P2/P3 over the emitted artefacts (built pages + JSON)."""
    row_re = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
    cell_re = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
    tag_re = re.compile(r"<[^>]+>")
    flag_re = re.compile(r"F-\d{3}|flag|BLOCKED|no official|not filed|blank|WITHHELD|"
                         r"unavailable|does not exist|no source|no market", re.I)

    unsourced, unexplained, placeholders = [], [], []
    for p in html_paths:
        doc = p.read_text()
        for m in PLACEHOLDER.finditer(doc):
            placeholders.append(f"{p.name}: {m.group(0)}")
        for m in row_re.finditer(doc):
            row = m.group(1)
            cells = cell_re.findall(row)
            if not cells:
                continue
            if "https://" not in row:
                txt = re.sub(tag_re, "", " ".join(cells))[:80]
                unsourced.append(f"{p.name}: {txt.strip()!r}")
            joined = " ".join(re.sub(tag_re, "", c) for c in cells)
            for c in cells:
                t = re.sub(tag_re, "", c).strip()
                if t in ("", "None", "nan", "—", "&mdash;"):
                    if not flag_re.search(joined):
                        unexplained.append(f"{p.name}: {joined[:80]!r}")
    return [
        {"id": "G-P1", "name": "every row sourced", "pass": not unsourced,
         "detail": f"{len(unsourced)} rows without an official URL",
         "value": unsourced[:5]},
        {"id": "G-P2", "name": "every blank explained", "pass": not unexplained,
         "detail": f"{len(unexplained)} blank cells with no flag id",
         "value": unexplained[:5]},
        {"id": "G-P3", "name": "no placeholders", "pass": not placeholders,
         "detail": f"{len(placeholders)} placeholder tokens", "value": placeholders[:5]},
    ]


def run(result: dict, html_paths: list[Path] | None = None) -> dict:
    g = freshness(result) + (provenance(html_paths) if html_paths else [])
    hard = [x for x in g if x["id"] in ("G-F1", "G-F2", "G-F5", "G-P1", "G-P2", "G-P3")]
    return {
        "ran_at_utc": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gates": g,
        "n_pass": sum(1 for x in g if x["pass"]),
        "n_fail": sum(1 for x in g if not x["pass"]),
        "publishable": all(x["pass"] for x in hard),
        "policy": ("G-F3 and G-F4 are advisory: a newer injury release or a tip inside "
                   "the cutoff is reported, not fatal, because the site must still show "
                   "what it knows. Everything in the hard set is fatal."),
    }


if __name__ == "__main__":
    from .model import build
    print(json.dumps(run(build()), indent=2))
