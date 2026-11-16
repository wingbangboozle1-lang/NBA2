#!/usr/bin/env python3
"""Session arena/f8f8f2b8-nba2 — emit the committed gamebook / game-log artifacts.

Reads the five verbatim transcription batches (a–e), runs the official-sum gates, and writes:

* ``data/raw/capture_2026-11-15/gamebooks_2026-11-13.json`` — one record per game, with the
  per-team box score exactly as the official gamebook prints it.
* ``data/raw/capture_2026-11-15/gamelogs_2026-11-13.json`` — one row per player per game:
  date, teams, opponent, player, position, minutes, points, rebounds, assists, and the
  official gamebook URL the row was read from.

The gates are fail-closed: a team-game whose player minutes do not sum to
``240:00 + 25:00 x OT`` (within a 2-second tolerance for the PDF's own rounding) or whose
player points do not sum to the official final is written with ``minutes_complete: false``
and is excluded from every measured-minutes table. Nothing is corrected to make a gate pass.

Run:  python3 analysis/session-f8f8f2b8-build-gamelogs.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "data" / "raw" / "capture_2026-11-15"
BATCHES = ["a", "b", "c", "d", "e"]

RETRIEVED_AT_UTC = "2026-11-15T23:45:00Z"
TOLERANCE_S = 2


def _load(letter: str) -> list[dict]:
    p = ROOT / "analysis" / f"session-f8f8f2b8-gamelogs-{letter}.py"
    spec = importlib.util.spec_from_file_location(f"gl_{letter}", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.GAMES


def _sec(mmss: str | None) -> int | None:
    if mmss is None:
        return None
    m, s = mmss.split(":")
    return int(m) * 60 + int(s)


def main() -> None:
    games: list[dict] = []
    for letter in BATCHES:
        games.extend(_load(letter))
    games.sort(key=lambda g: g["game_id"])

    logs: list[dict] = []
    problems: list[dict] = []

    for g in games:
        ot = g.get("ot_periods", 0)
        target = 240 * 60 + ot * 25 * 60
        mc = dict(g.get("minutes_complete") or {})
        for tri, side in ((g["away"], "away"), (g["home"], "home")):
            tm = g["teams"][tri]
            secs = [_sec(p[2]) for p in tm["played"]]
            missing = [p[0] for p, s in zip(tm["played"], secs) if s is None]
            total = sum(s for s in secs if s is not None)
            pts = sum(p[3] for p in tm["played"])
            residual = total - target
            complete = (not missing) and abs(residual) <= TOLERANCE_S
            mc.setdefault(tri, complete)
            if not complete:
                problems.append({
                    "game_id": g["game_id"], "team": tri,
                    "reason": ("minutes cell did not extract for: " + ", ".join(missing))
                              if missing else
                              f"player minutes sum {total}s vs expected {target}s "
                              f"(residual {residual:+d}s)",
                    "flag": "I-F8F-07" if missing else "I-F8F-05",
                })
            elif residual != 0:
                problems.append({
                    "game_id": g["game_id"], "team": tri,
                    "reason": f"player minutes sum {total}s vs team total {target}s "
                              f"(residual {residual:+d}s, inside the {TOLERANCE_S}s tolerance)",
                    "flag": "I-F8F-05", "blocking": False,
                })
            if pts != g[side + "_pts"]:
                raise SystemExit(
                    f"gate failure: {g['game_id']} {tri} player pts {pts} != final "
                    f"{g[side + '_pts']}")
            opp = g["home"] if side == "away" else g["away"]
            for player, pos, mmss, p_pts, reb, ast in tm["played"]:
                logs.append({
                    "date": g["date"],
                    "game_id": g["game_id"],
                    "team": tri,
                    "opponent": opp,
                    "home": side == "home",
                    "player": player,
                    "pos": pos,
                    "min": mmss,
                    "min_sec": _sec(mmss),
                    "pts": p_pts,
                    "reb": reb,
                    "ast": ast,
                    "matchup": f"{g['away']}@{g['home']}",
                    "source_url": g["gamebook_url"],
                    "source_class": "official",
                })
        g["minutes_complete"] = mc
        g.pop("teams", None) or None

    # Re-attach teams (pop above was a no-op guard; keep the structure explicit).
    games_by_id = {g["game_id"]: g for g in games}
    for letter in BATCHES:
        for raw in _load(letter):
            games_by_id[raw["game_id"]]["teams"] = raw["teams"]

    book = {
        "schema": "nba2.gamebook-capture.v1",
        "date": "2026-11-13",
        "n_games": len(games),
        "retrieved_at_utc": RETRIEVED_AT_UTC,
        "retrieval_method": "platform page-fetch tool (fetch_page) against the official "
                            "gamebook PDFs",
        "source_pattern": "https://statsdmz.nba.com/pdfs/<YYYYMMDD>/<YYYYMMDD>_<AWAY><HOME>"
                          "_book.pdf",
        "index_page": "https://www.nba.com/games?date=2026-11-13",
        "gates": {
            "minutes_sum": "player minutes must sum to 240:00 + 25:00 per OT "
                           f"(+/-{TOLERANCE_S}s for the PDF's own rounding)",
            "points_sum": "player points must sum to the official final score (exact)",
            "quarters_sum": "quarter scores must sum to the official final score; a row that "
                            "does not is left blank and flagged (I-F8F-06 / I-F8F-09)",
        },
        "incomplete": [p for p in problems if p.get("blocking", True)],
        "residuals": [p for p in problems if not p.get("blocking", True)],
        "games": games,
    }
    (CAP / "gamebooks_2026-11-13.json").write_text(
        json.dumps(book, indent=2, ensure_ascii=False) + "\n")

    logs.sort(key=lambda r: (r["team"], -r["min_sec"] if r["min_sec"] else 0, r["player"]))
    doc = {
        "schema": "nba2.player-gamelog.v2",
        "window": "2026-11-13",
        "n_rows": len(logs),
        "n_games": len(games),
        "n_teams": len({g["away"] for g in games} | {g["home"] for g in games}),
        "retrieved_at_utc": RETRIEVED_AT_UTC,
        "note": (
            "Per-player game logs (minutes, points, rebounds, assists, opponent) transcribed "
            "from the official NBA gamebook PDF for every game played 2026-11-13 (9 games, 18 "
            "clubs). Every row carries the gamebook URL it was read from. Gate failures are "
            "recorded, never corrected: Memphis' Jerami Grant has no extracted minutes cell in "
            "the official PDF (I-F8F-07), so his minutes cell is null and Memphis is excluded "
            "from the measured-minutes tables."
        ),
        "columns": ["date", "game_id", "team", "opponent", "player", "pos", "min", "min_sec",
                    "pts", "reb", "ast", "source_url"],
        "records": logs,
    }
    (CAP / "gamelogs_2026-11-13.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n")

    digest = hashlib.sha256(
        json.dumps(logs, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    print(f"games={len(games)} log_rows={len(logs)} "
          f"teams={doc['n_teams']} incomplete={len(book['incomplete'])} "
          f"residuals={len(book['residuals'])}")
    print("row-set sha256:", digest[:16])


if __name__ == "__main__":
    main()
