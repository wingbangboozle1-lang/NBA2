"""Post-build verification of the v2 site.

Checks, in order of strictness:
1. every local link resolves to a file that exists;
2. every table row contains at least one outbound source link;
3. every blank cell is accompanied by a reason (a flag id, a "needs ..." phrase, or a blocked note);
4. no placeholder tokens (TODO, TBD, lorem, XXX) in the HTML;
5. the published numbers agree with an independent recomputation from the raw snapshot.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"

LOCAL_LINK = re.compile(r'(?:href|src)="([^"#][^"]*)"')
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
TAG = re.compile(r"<[^>]+>")
BLANK_OK = re.compile(r"(FLAG-|F-\d{3}|needs |no source|blocked|BLOCKED|not filed|first in window|"
                      r"does not exist|unavailable|withheld|WITHHELD|no data)", re.I)


def text_of(cell_html: str) -> str:
    return html.unescape(TAG.sub("", cell_html)).strip()


def check() -> list[str]:
    problems: list[str] = []
    pages = sorted(SITE.glob("*.html"))
    if not pages:
        return ["no pages built"]
    for p in pages:
        doc = p.read_text()
        for link in LOCAL_LINK.findall(doc):
            if link.startswith(("http://", "https://", "mailto:", "//")) or link.startswith("data:"):
                continue
            target = (p.parent / link.split("?")[0]).resolve()
            if not target.exists():
                problems.append(f"{p.name}: broken local link -> {link}")
        for token in ("TODO", "TBD", "lorem ipsum", "XXX", "{{", "}}"):
            if token in doc:
                problems.append(f"{p.name}: placeholder token {token!r}")
        # row-level source check
        for m in ROW.finditer(doc):
            row = m.group(1)
            cells = CELL.findall(row)
            if not cells:
                continue  # header row
            if not re.search(r'href="https?://', row):
                snippet = text_of(" ".join(cells))[:90]
                problems.append(f"{p.name}: table row without any source link -> {snippet!r}")
            # blank cell needs a reason somewhere in the row
            joined = " ".join(text_of(c) for c in cells)
            if not joined.strip():
                problems.append(f"{p.name}: fully empty row")
            for c in cells:
                t = text_of(c)
                if t in ("", "None", "nan", "NaN"):
                    if not BLANK_OK.search(joined):
                        problems.append(f"{p.name}: blank cell with no reason -> {joined[:90]!r}")
    return problems


def semantic() -> list[str]:
    """Independently recompute the headline numbers straight from the committed raw snapshot."""
    import json

    problems = []
    raw = json.loads((ROOT / "data/raw/capture_2026-11-19/slate_2026-11-19.json").read_text())
    from . import official as O
    n_slate = 26          # the 3-day window 2026-11-19 -> 2026-11-22
    # and the raw capture must agree with the league's own per-day headings
    from collections import Counter
    counts = Counter(g["date"] for g in raw["games"])
    if dict(counts) != raw.get("games_expected"):
        problems.append(f"slate capture rows {dict(counts)} disagree with the game counts the "
                        f"official page printed ({raw.get('games_expected')})")
    if counts != Counter(g[0] for g in O.SLATE):
        problems.append("official.SLATE per-day counts differ from the raw slate capture")
    if len(O.SLATE) != n_slate:
        problems.append(f"SLATE has {len(O.SLATE)} games, expected {n_slate}")
    if len(raw["games"]) != n_slate:
        problems.append(f"committed raw snapshot has {len(raw['games'])} games, expected {n_slate}")
    lines = json.loads((ROOT / "data/v2/lines.json").read_text())
    if len(lines["lines"]) != n_slate:
        problems.append(f"lines.json has {len(lines['lines'])} lines, expected {n_slate}")
    # every published line must be a game in the committed slate, with the same game id
    by_id = {r["game_id"]: r for r in raw["games"]}
    for ln in lines["lines"]:
        gid = ln.get("game_id")
        if gid not in by_id:
            problems.append(f"lines.json game {gid} is not in the committed slate snapshot")
        elif ln["matchup"] != f"{by_id[gid]['away']} @ {by_id[gid]['home']}":
            problems.append(f"lines.json matchup {ln['matchup']} disagrees with the slate snapshot")
    # published W/L must equal the official standings totals (222 games played through 11/18), and
    # that number must equal an independent recount of every official final committed in this repo
    from . import official as O2
    if sum(v[0] for v in O2.TEAMS.values()) != 222:
        problems.append("official team table no longer sums to 222 wins")
    finals = {}
    for pat in ("data/raw/history/*.json", "data/raw/results/*.json", "data/raw/finals_*.json",
                "data/raw/capture_*/finals_*.json"):
        for f in sorted(ROOT.glob(pat)):
            doc = json.loads(f.read_text())
            recs = doc.get("records") or doc.get("games") or []
            for r in recs if isinstance(recs, list) else []:
                if not isinstance(r, dict):
                    continue
                gid, ap, hp = r.get("game_id"), r.get("away_pts"), r.get("home_pts")
                a, h, d = r.get("away"), r.get("home"), r.get("date")
                if gid and ap is not None and hp is not None and d and a and h:
                    finals[gid] = (a, h, int(hp), int(ap))
    if len(finals) != 222:
        problems.append(f"{len(finals)} committed official finals, expected 222 for the standings to be current")
    else:
        w = Counter()
        for a, h, hp, ap in finals.values():
            w[h if hp > ap else a] += 1
        stale = [t for t, v in O2.TEAMS.items() if v[0] != w[t]]
        if stale:
            problems.append(f"standings W-L disagrees with a recount of the finals for {stale}")
    # p_home must equal Φ(margin/σ)
    import math
    s = lines["calibration"]["margin_sd"]
    for ln in lines["lines"]:
        want = 0.5 * (1 + math.erf((ln["margin"] / s) / math.sqrt(2)))
        if abs(want - ln["p_home"]) > 1e-3:
            problems.append(f"{ln['matchup']}: p_home {ln['p_home']} != Φ(margin/σ) {want:.4f}")
    teams = json.loads((ROOT / "data/v2/teams.json").read_text())
    if len(teams["teams"]) != 30:
        problems.append("teams.json does not have 30 teams")
    # wins == losses from the published team table
    w = sum(t["w"] for t in teams["teams"])
    l = sum(t["l"] for t in teams["teams"])
    if w != l:
        problems.append(f"published team table has wins {w} != losses {l}")
    return problems


if __name__ == "__main__":
    p1 = check()
    p2 = semantic()
    for x in p1 + p2:
        print("PROBLEM:", x)
    print(f"{'FAIL' if (p1 or p2) else 'OK'} — {len(p1)} structural, {len(p2)} semantic")
    raise SystemExit(1 if (p1 or p2) else 0)
