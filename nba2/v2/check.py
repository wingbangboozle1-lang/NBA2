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
    raw = json.loads((ROOT / "data/raw/official_slate_2026-11-14_to_11-17_verified.json").read_text())
    # --- row-level agreement between the model's slate and the committed official snapshot
    snap_rows = {(r["date"], r["time_et"], r["away"], r["home"], r["game_id"]) for r in raw["records"]}
    model_rows = {(d, t, a, h, g) for (d, t, a, h, g, *_rest) in O.SLATE}
    if snap_rows != model_rows:
        problems.append(f"slate snapshot and model disagree: only-in-snapshot={sorted(snap_rows - model_rows)} "
                        f"only-in-model={sorted(model_rows - snap_rows)}")
    if len(O.SLATE) != len(raw["records"]):
        problems.append(f"SLATE has {len(O.SLATE)} games, snapshot has {len(raw['records'])}")
    # --- the 3-day rule is enforced, not merely documented
    from datetime import date
    build = date.fromisoformat(O.AS_OF)
    for (d, *_rest) in O.SLATE:
        if not 0 <= (date.fromisoformat(d) - build).days <= 3:
            problems.append(f"{d} is outside the 3-day window from {O.AS_OF}")
    # --- every priced game must carry a resolvable official source URL
    for (d, t, a, h, g, *_rest) in O.SLATE:
        want = f"https://www.nba.com/game/{a.lower()}-vs-{h.lower()}-{g}"
        row = next((r for r in raw["records"] if r["game_id"] == g), None)
        if row is None or row.get("source_url") != want:
            problems.append(f"{g}: row source_url missing or wrong (want {want})")
    lines = json.loads((ROOT / "data/v2/lines.json").read_text())
    if len(lines["lines"]) != len(O.SLATE):
        problems.append(f"lines.json has {len(lines['lines'])} lines, slate has {len(O.SLATE)}")
    # --- no line may price a game whose final score is already known
    history = set()
    for f in sorted((ROOT / "data/raw/history").glob("games_*.json")):
        for g in json.loads(f.read_text())["games"]:
            if g.get("away_pts") is not None:
                history.add(g["game_id"])
    played = {ln["game_id"] for ln in lines["lines"]} & history
    if played:
        problems.append(f"lines.json prices games already played: {sorted(played)}")
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
    # every team's home+road+neutral games must equal its W+L
    from . import official as O2
    for t in teams["teams"]:
        nw, nl = O2.NEUTRAL.get(t["tricode"], (0, 0))
        split = sum(int(x) for x in t["home"].split("-")) + sum(int(x) for x in t["road"].split("-")) + nw + nl
        if split != t["w"] + t["l"]:
            problems.append(f"{t['tricode']}: home+road+neutral {split} != W+L {t['w'] + t['l']}")
    return problems


if __name__ == "__main__":
    p1 = check()
    p2 = semantic()
    for x in p1 + p2:
        print("PROBLEM:", x)
    print(f"{'FAIL' if (p1 or p2) else 'OK'} — {len(p1)} structural, {len(p2)} semantic")
    raise SystemExit(1 if (p1 or p2) else 0)
