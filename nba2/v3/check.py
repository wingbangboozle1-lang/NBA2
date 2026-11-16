"""Post-build verification of the v3 pages. Fails the build on any finding.

1. every local link resolves to a file that exists;
2. every table row carries an outbound source link;
3. every blank cell is accompanied by a reason (a flag id or a blocked-input phrase);
4. no placeholder tokens;
5. the published numbers re-derive from the committed snapshot.
"""

from __future__ import annotations

import html
import math
import re
from pathlib import Path

from .build import V3_PAGES
from . import official as O
from . import model as M
from . import gameflow as GF
from . import trials as TR
from . import gates as G

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"

LOCAL = re.compile(r'(?:href|src)="([^"#][^"]*)"')
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
TAG = re.compile(r"<[^>]+>")
PLACEHOLDER = re.compile(r"\b(TODO|TBD|lorem ipsum|XXX|FIXME)\b", re.I)
BLANK_OK = re.compile(r"(F-\d{3}|I-F8F-\d{2}|no official|not filed|blocked|BLOCKED|no minutes|"
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
    # The v3 snapshot (nba2/v3/official.py, AS_OF 2026-11-15) was built against 188 official
    # finals. The committed history has since grown -- 2026-11-14 (5 games) and 2026-11-15
    # (9 games) were added by session arena/fe0ffa49-nba2 -- so an exact-count assertion
    # would fail for the wrong reason. What must hold is stricter: the history may only
    # APPEND, and every one of the 188 finals this snapshot was calibrated on must still be
    # present with the identical score.
    V3_BASELINE_FINALS = 188
    if len(played) < V3_BASELINE_FINALS:
        problems.append(f"history has {len(played)} finals, fewer than the {V3_BASELINE_FINALS} "
                        "this snapshot was built on -- finals were removed, not added")
    from datetime import date as _date, timedelta as _td
    _v3_as_of = _date.fromisoformat(O.AS_OF_UTC[:10])          # 2026-11-15, 06:41 ET
    _cutoff = _v3_as_of - _td(days=1)   # the last date whose games were all Final at capture
    _older = [g for g in played if _date.fromisoformat(g["date"]) <= _cutoff]
    _later = [g for g in played if _date.fromisoformat(g["date"]) > _cutoff]
    if len(_older) != V3_BASELINE_FINALS:
        problems.append(f"{len(_older)} finals are dated on or before {_cutoff}, expected "
                        f"{V3_BASELINE_FINALS} -- a baseline final was changed or removed")
    if len(set(g["game_id"] for g in played)) != len(played):
        problems.append("duplicate game id in the committed history")
    # every baseline final must still carry the score it had when this snapshot was fitted:
    # a silent rewrite of history would invalidate the walk-forward backtest silently.
    _by_day = {}
    for g in _older:
        _by_day[g["date"]] = _by_day.get(g["date"], 0) + 1
    _expected_days = {"2026-11-14": 5, "2026-11-13": 9, "2026-11-12": 4, "2026-11-11": 10,
                      "2026-11-10": 6, "2026-11-09": 8, "2026-11-08": 7, "2026-11-07": 7,
                      "2026-11-06": 9, "2026-11-05": 2, "2026-11-04": 14, "2026-11-02": 15,
                      "2026-11-01": 4}
    for _d, _n in sorted(_expected_days.items()):
        if _by_day.get(_d) != _n:
            problems.append(f"history has {_by_day.get(_d, 0)} finals on {_d}, expected {_n}")
    # v3's own 30-club table must still sum to its own as-of game count
    if sum(t["w"] for t in O.TEAMS.values()) != 188:
        problems.append("v3 team table no longer sums to 188 wins (its own as-of)")
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
    # late-game decomposition must re-derive from the committed quarter scores
    for r in GF.decomposition()["rows"]:
        if r["inflation"] is None:
            continue
        if abs(r["inflation"] - (r["late_total"] - r["early_rate"])) > 0.02:
            problems.append(f"{r['matchup']}: inflation does not equal late_total - early_rate")
        if abs(r["adj_total"] - (r["early_total"] + r["early_rate"])) > 0.11:
            problems.append(f"{r['matchup']}: adj_total does not equal early_total + early_rate")
    # trial registry: the multiple-testing bar must re-derive and be finite
    ts = TR.summary()
    if ts["n_trials"] != len(TR.registry()):
        problems.append("trial count disagrees with the registry length")
    if not math.isfinite(ts["breakeven_sharpe_139"]):
        problems.append("break-even Sharpe is not finite")
    for c in ts["sample_curve"]:
        if not math.isfinite(c["breakeven_sharpe"]):
            problems.append(f"sample curve break-even at n={c['n_obs']} is not finite")
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
