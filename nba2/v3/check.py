"""Post-build verification of the v3 pages. Fails the build on any finding.

1. every local link resolves to a file that exists;
2. every table row carries an outbound source link;
3. every blank cell is accompanied by a reason (a flag id or a blocked-input phrase);
4. no placeholder tokens;
5. the published numbers re-derive from the committed snapshot.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from .build import V3_PAGES
from . import official as O
from . import model as M
from . import gates as G

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"

LOCAL = re.compile(r'(?:href|src)="([^"#][^"]*)"')
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
TAG = re.compile(r"<[^>]+>")
PLACEHOLDER = re.compile(r"\b(TODO|TBD|lorem ipsum|XXX|FIXME)\b", re.I)
BLANK_OK = re.compile(r"(F-\d{3}|no official|not filed|blocked|BLOCKED|no minutes|"
                      r"no arena coordinates|no market price|linescore not captured|"
                      r"unknown|no source)", re.I)


def text_of(c: str) -> str:
    return html.unescape(TAG.sub("", c)).strip()


def structural() -> list[str]:
    problems = []
    for name in V3_PAGES:
        p = SITE / name
        if not p.exists():
            problems.append(f"{name}: missing")
            continue
        doc = p.read_text()
        for link in LOCAL.findall(doc):
            if link.startswith(("http://", "https://", "mailto:", "//", "data:")):
                continue
            if not (p.parent / link.split("?")[0]).exists():
                problems.append(f"{name}: broken local link -> {link}")
        for m in PLACEHOLDER.finditer(doc):
            problems.append(f"{name}: placeholder {m.group(0)!r}")
        for m in ROW.finditer(doc):
            row = m.group(1)
            cells = CELL.findall(row)
            if not cells:
                continue
            if "https://" not in row:
                problems.append(f"{name}: row without a source link -> "
                                f"{text_of(' '.join(cells))[:80]!r}")
            joined = " ".join(text_of(c) for c in cells)
            for c in cells:
                if text_of(c) in ("", "None", "nan"):
                    if not BLANK_OK.search(joined):
                        problems.append(f"{name}: blank cell with no reason -> "
                                        f"{joined[:80]!r}")
    return problems


def semantic() -> list[str]:
    problems = []
    res = M.build()
    hc = res["home_court"]
    played = M.load_played_games()["games"]
    if len(played) != 188:
        problems.append(f"history has {len(played)} finals, expected 188")
    if sum(1 for g in played if not g["neutral"] and g["home_margin"] > 0) != hc["home_wins"]:
        problems.append("home-win count disagrees with a fresh recomputation")
    if abs(hc["hca_points"] - hc["margin_sd"] * M.phi_inv(hc["home_win_rate"])) > 5e-4:
        problems.append("pinned HCA is not sd x Phi^-1(home win rate)")
    for ln in res["lines"]:
        if abs(ln["e1_margin"] - M.estimator_efficiency(
                O.TEAMS[ln["home"]], O.TEAMS[ln["away"]], hc["hca_points"],
                ln["possessions"])) > 0.011:
            problems.append(f"{ln['matchup']}: E1 does not re-derive")
        if abs(ln["total"] - (ln["proj_home_pts"] + ln["proj_away_pts"])) > 0.15:
            problems.append(f"{ln['matchup']}: total does not equal home+away projections")
        if ln["disagreement"] < 0:
            problems.append(f"{ln['matchup']}: negative disagreement")
    # every sealed pick must be a real slate game
    from . import ledger as LD
    ids = {g["game_id"] for g in O.SLATE}
    for p in LD.build_picks(res):
        if p["game_id"] not in ids:
            problems.append(f"sealed pick {p['game_id']} is not in the slate")
        if p["stake_pct"] != 0.0:
            problems.append(f"sealed pick {p['game_id']} has a non-zero stake")
    return problems


def main() -> int:
    s, m = structural(), semantic()
    for x in s + m:
        print("PROBLEM:", x)
    gates = G.run(M.build(), [SITE / n for n in V3_PAGES])
    print(f"gates: {gates['n_pass']} pass / {gates['n_fail']} fail, "
          f"publishable={gates['publishable']}")
    print(f"{'FAIL' if (s or m) else 'OK'} - {len(s)} structural, {len(m)} semantic")
    return 1 if (s or m) else 0


if __name__ == "__main__":
    raise SystemExit(main())
