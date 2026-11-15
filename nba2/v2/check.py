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
    from . import official as O

    # The slate snapshot the check compares against is the newest committed one, and the
    # expected game count is read from that file rather than remembered: a hard-coded 27
    # silently failed the whole gate the moment the rolling window moved to 11/15 -> 11/18
    # (session arena/673acec0-nba2). Deriving both from the artefact is what makes the
    # check survive the next refresh.
    slate_files = sorted((ROOT / "data" / "raw").glob("official_schedule_*.json"))
    if not slate_files:
        return ["no committed official slate snapshot under data/raw/"]
    raw = json.loads(slate_files[-1].read_text())
    n_slate = len(raw["games"])
    if raw["window"] != [O.WINDOW_START, O.WINDOW_END]:
        problems.append(f"slate snapshot window {raw['window']} != official.py window "
                        f"{[O.WINDOW_START, O.WINDOW_END]}")
    if len(O.SLATE) != n_slate:
        problems.append(f"SLATE has {len(O.SLATE)} games, expected {n_slate}")
    if n_slate == 0:
        problems.append("committed raw slate snapshot has no games")
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
    # Published W/L must equal the league win total implied by the committed official finals.
    # The count is reconstructed from data/raw/history (so it moves when results are added),
    # and the standings capture is checked against it as a second, independent document.
    n_finals = 0
    for hp in (ROOT / "data" / "raw" / "history").glob("games_*.json"):
        n_finals += len(json.loads(hp.read_text())["games"])
    wins = sum(v[0] for v in O.TEAMS.values())
    if wins != n_finals:
        problems.append(f"official team table sums to {wins} wins but {n_finals} official "
                        f"finals are committed")
    std_files = sorted((ROOT / "data" / "raw").glob("official_standings_*.json"))
    if std_files:
        std = json.loads(std_files[-1].read_text())
        if {r["tricode"]: (r["w"], r["l"]) for r in std["records"]} != \
           {t: (v[0], v[1]) for t, v in O.TEAMS.items()}:
            problems.append(f"official.py TEAMS disagrees with the newest committed standings "
                            f"capture {std_files[-1].name}")
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
