"""Gates over the v5 transcripts. Fail-closed: the build does not render on a hard failure.

Every gate is a measurement, not an assertion of intent: each one returns the number of
rows it could test, the number that passed, and the rows that failed by name. Gates that
cannot be evaluated (a quarter row the PDF did not print) report ``skipped`` with a reason
and are **not** counted as passes.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import transcript as T

ROOT = T.ROOT
DATA = T.DATA

# Committed official result feeds this session's finals must agree with.
CROSS_SOURCES = [
    DATA / "raw" / "capture_2026-11-15" / "results_2026-11-14.json",
    DATA / "raw" / "results" / "results_2026-11-15.json",
    # 1eeb6a21: the 11/16 feed committed this session cross-checks its own transcript
    DATA / "raw" / "results" / "results_2026-11-16.json",
]


def _committed_finals() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in CROSS_SOURCES:
        if not path.exists():
            continue
        doc = json.loads(path.read_text())
        for r in doc.get("records", []):
            gid = r.get("game_id")
            if not gid or r.get("status") != "final":
                continue
            out[gid] = {"away_pts": r.get("away_pts"), "home_pts": r.get("home_pts"),
                        "away_club": r.get("away"), "home_club": r.get("home"),
                        "away_quarters": r.get("away_quarters"),
                        "home_quarters": r.get("home_quarters"),
                        "file": path.name}
    return out


def _q(gid: str, name: str, ok: bool | None, tested: int, passed: int,
       detail: str, failures: list[str] | None = None, hard: bool = True) -> dict:
    return {"id": gid, "name": name, "ok": ok, "tested": tested, "passed": passed,
            "detail": detail, "failures": failures or [], "hard": hard}


def gate_quarters(games: list[dict]) -> dict:
    tested = passed = 0
    failures, skipped = [], []
    for g in games:
        for side in ("away", "home"):
            q = (g["quarters"].get(side) or []) + (g["quarters"].get("ot", {}).get(side) or [])
            if not q:
                skipped.append(f"{g['matchup']} {side}: {g.get('quarters_blank_reason', 'no quarter row')}")
                continue
            tested += 1
            if sum(q) == g["final"][side]:
                passed += 1
            else:
                failures.append(f"{g['matchup']} {side}: {q} sums to {sum(q)}, final {g['final'][side]}")
    ok = not failures
    detail = (f"{passed}/{tested} club quarter rows sum to their final"
              + (f"; {len(skipped)} skipped (blank by policy)" if skipped else ""))
    return _q("V5-G1", "Quarter scores sum to the final", ok, tested, passed, detail,
              failures)


def gate_player_points(rows: list[dict], games: list[dict]) -> dict:
    by_game = {(g["game_id"], g["home"]): g for g in games}
    by_game.update({(g["game_id"], g["away"]): g for g in games})
    totals: dict[tuple[str, str], int] = {}
    for r in rows:
        if r["transcript"].startswith("gamebooks_") and r["pts"] is not None:
            totals[(r["game_id"], r["team"])] = totals.get((r["game_id"], r["team"]), 0) + r["pts"]
    tested = passed = 0
    failures = []
    for (gid, tri), s in sorted(totals.items()):
        g = by_game.get((gid, tri))
        if not g:
            continue
        home = "home" if g["home"] == tri else "away"
        tested += 1
        if s == g["final"][home]:
            passed += 1
        else:
            failures.append(f"{g['matchup']} {tri}: players sum to {s}, final {g['final'][home]}")
    return _q("V5-G2", "Player points sum to the club final", not failures, tested, passed,
              f"{passed}/{tested} clubs: the sum of the individual points equals the final "
              f"printed in the gamebook", failures)


def gate_minutes(rows: list[dict], games: list[dict]) -> dict:
    by_game = {(g["game_id"], g["home"]): g for g in games}
    by_game.update({(g["game_id"], g["away"]): g for g in games})
    totals: dict[tuple[str, str], int] = {}
    for r in rows:
        if r["transcript"].startswith("gamebooks_") and r["min_sec"]:
            totals[(r["game_id"], r["team"])] = totals.get((r["game_id"], r["team"]), 0) + r["min_sec"]
    tested = passed = 0
    failures = []
    for (gid, tri), s in sorted(totals.items()):
        g = by_game.get((gid, tri))
        if not g:
            continue
        want = g["club_totals"][tri]["min_sec"]
        tested += 1
        if abs(s - want) <= T.MIN_TOLERANCE_S:
            passed += 1
        else:
            failures.append(f"{g['matchup']} {tri}: players sum to {s}s, gamebook {want}s "
                            f"(delta {s - want}s)")
    return _q("V5-G3", "Player minutes sum to the club total", not failures, tested, passed,
              f"{passed}/{tested} clubs within {T.MIN_TOLERANCE_S}s of the gamebook team "
              f"minutes (the PDFs round each player to the second)", failures)


def gate_rebounds(rows: list[dict], games: list[dict]) -> dict:
    by_game = {(g["game_id"], g["home"]): g for g in games}
    by_game.update({(g["game_id"], g["away"]): g for g in games})
    totals: dict[tuple[str, str], int] = {}
    blanks: set[tuple[str, str]] = set()
    for r in rows:
        if not r["transcript"].startswith("gamebooks_"):
            continue
        key = (r["game_id"], r["team"])
        if r["reb"] is None:
            if r["played"]:
                blanks.add(key)
            continue
        totals[key] = totals.get(key, 0) + r["reb"]
    tested = passed = 0
    failures = []
    for (gid, tri), s in sorted(totals.items()):
        g = by_game.get((gid, tri))
        if not g:
            continue
        if (gid, tri) in blanks:
            continue
        tested += 1
        want = g["club_totals"][tri]["reb"]
        if s == want:
            passed += 1
        else:
            failures.append(f"{g['matchup']} {tri}: players sum to {s}, gamebook {want}")
    skipped = []
    for (gid, tri) in sorted(blanks):
        g = by_game.get((gid, tri))
        label = g["matchup"] if g else gid
        skipped.append(f"{label} {tri}: rebound cells blank by policy (F-V5-02), not summed")
    return _q("V5-G4", "Player rebounds sum to the club total", not failures, tested, passed,
              f"{passed}/{tested} clubs; {len(skipped)} club(s) skipped because their "
              f"rebound cells are blank by policy (F-V5-02)", failures)


def gate_points_identity(rows: list[dict]) -> dict:
    """pts must equal 2*(FG - 3P) + 3*3P + FT. Catches a column mis-read in any row."""
    tested = passed = 0
    failures = []
    for r in rows:
        if not r["transcript"].startswith("gamebooks_") or not r["played"]:
            continue
        if None in (r["pts"], r["fg"], r["fg3"], r["ft"]):
            continue
        tested += 1
        want = 2 * (r["fg"] - r["fg3"]) + 3 * r["fg3"] + r["ft"]
        if want == r["pts"]:
            passed += 1
        else:
            failures.append(f"{r['matchup']} {r['player']}: printed {r['pts']}, "
                            f"FG/3P/FT imply {want}")
    return _q("V5-G5", "Points identity on every row", not failures, tested, passed,
              f"{passed}/{tested} player rows satisfy pts = 2*(FG-3P) + 3*3P + FT", failures)


def gate_cross_source(games: list[dict]) -> dict:
    committed = _committed_finals()
    tested = passed = 0
    failures, new_rows = [], []
    for g in games:
        src = committed.get(g["game_id"])
        if not src:
            new_rows.append(f"{g['matchup']} ({g['game_id']})")
            continue
        tested += 1
        if src["away_pts"] == g["final"]["away"] and src["home_pts"] == g["final"]["home"]:
            passed += 1
        else:
            failures.append(f"{g['matchup']}: this session {g['final']['away']}-"
                            f"{g['final']['home']}, {src['file']} "
                            f"{src['away_pts']}-{src['home_pts']}")
    detail = (f"{passed}/{tested} finals in the committed official feeds agree with this "
              f"session's reading" + (f"; {len(new_rows)} game(s) are newly settled here: "
                                      f"{', '.join(new_rows)}" if new_rows else ""))
    return _q("V5-G6", "Agreement with the committed official result feeds",
              not failures, tested, passed, detail, failures)


def gate_provenance(rows: list[dict]) -> dict:
    tested = passed = 0
    failures = []
    for r in rows:
        tested += 1
        if not r.get("source_url"):
            failures.append(f"{r['date']} {r['matchup']} {r['player']}: no source URL")
            continue
        if not r.get("retrieved_window_utc"):
            failures.append(f"{r['date']} {r['matchup']} {r['player']}: no retrieval stamp")
            continue
        if not r["played"]:
            # A player who did not appear is expected to have no count line at all; the
            # official designation printed in the minutes column is itself the reason.
            if not r.get("status"):
                failures.append(f"{r['matchup']} {r['player']}: no appearance and no "
                                f"official designation")
                continue
        else:
            reasons = {"reb": r.get("reb_blank_reason"), "min": r.get("min_blank_reason")}
            missing = [c for c in ("min", "pts", "reb", "ast") if r.get(c) is None]
            unreasoned = [c for c in missing if not reasons.get(c)]
            if unreasoned:
                failures.append(f"{r['matchup']} {r['player']}: blank {unreasoned} "
                                f"with no stated reason")
                continue
        passed += 1
    return _q("V5-G7", "Provenance on every row", not failures, tested, passed,
              f"{passed}/{tested} rows carry a source URL, a retrieval stamp, and a reason "
              f"for any blank cell", failures)


def gate_coverage(rows: list[dict]) -> dict:
    clubs = sorted({r["team"] for r in rows})
    games_ = sorted({(r["date"], r["game_id"]) for r in rows})
    ok = len(clubs) == 30
    return _q("V5-G8", "Club coverage of the union", ok, 30, len(clubs),
              f"{len(clubs)}/30 clubs and {len(games_)} team-games in the union "
              f"({', '.join(c for c in clubs)})" if not ok else
              f"all 30 clubs present across {len(games_)} team-games",
              [] if ok else [f"missing: {sorted(set(_all_clubs()) - set(clubs))}"],
              hard=False)


def _all_clubs() -> list[str]:
    return sorted(T.TEAM_NAME.values())


def gates(rows: list[dict], games: list[dict]) -> list[dict]:
    return [
        gate_quarters(games),
        gate_player_points(rows, games),
        gate_minutes(rows, games),
        gate_rebounds(rows, games),
        gate_points_identity(rows),
        gate_cross_source(games),
        gate_provenance(rows),
        gate_coverage(rows),
    ]


def run() -> dict:
    rows = T.player_rows()
    gs = T.games()
    result = gates(rows, gs)
    hard_failures = [g for g in result if g["hard"] and not g["ok"]]
    return {"gates": result,
            "n_gates": len(result),
            "n_gates_pass": sum(1 for g in result if g["ok"]),
            "n_gates_fail": sum(1 for g in result if not g["ok"]),
            "n_hard_fail": len(hard_failures),
            "publishable": not hard_failures,
            "n_rows": len(rows),
            "n_games": len({(r["date"], r["game_id"]) for r in rows})}


if __name__ == "__main__":
    res = run()
    for g in res["gates"]:
        print(f"{g['id']} {'PASS' if g['ok'] else 'FAIL'}  {g['name']}: {g['detail']}")
        for f in g["failures"][:6]:
            print(f"      - {f}")
    print(f"\n{res['n_gates_pass']}/{res['n_gates']} gates pass; "
          f"publishable={res['publishable']}; {res['n_rows']} player rows")
    raise SystemExit(0 if res["publishable"] else 1)
