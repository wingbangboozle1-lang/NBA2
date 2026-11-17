"""K-05 — how much of the injury report we can actually see play.

The brief asks for per-player game logs (minutes, points, rebounds, assists, opponent) for
**at least** the players who appear on an injury report. ``nba2/v5/injury_join.json`` already
performs that join; this module measures it and publishes the measurement, because "we have
player logs" and "we have player logs for 26.5% of the injury report" are very different
claims and only the second one is true.

The join is deliberately literal: a player matches only when the name string on the official
injury report equals the name string in the official gamebook. Near-misses are listed as
unmatched with the reason, never merged — merging ``Marcus Sassar`` with ``Marcus Sasser``
is an inference about identity, and this repository does not publish inferences.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .common import DATA, ROOT, maybe_load

JOIN = DATA / "v5" / "injury_join.json"
LOGS = DATA / "v5" / "player_logs_union.json"

# A reversed-name artefact the official report itself prints ("Jr., Ernest Udeh"). It is a
# property of the source document, so it is reported, not silently repaired.
REVERSED_NAME_RE = re.compile(r"^(?:Jr\.|Sr\.|II|III|IV|V), ")


def build() -> dict:
    join = maybe_load(JOIN) or {}
    logs = maybe_load(LOGS) or {}

    matched = list(join.get("matched") or [])
    unmatched = list(join.get("unmatched") or [])

    # --- the log side, recounted independently of v5's own counters
    log_rows = logs.get("records") or []
    by_player: dict[str, list[dict]] = {}
    for r in log_rows:
        by_player.setdefault(str(r.get("player") or "").strip(), []).append(r)

    def enrich(m: dict) -> dict:
        name = str(m.get("player") or "").strip()
        rows = by_player.get(name, [])
        played = [r for r in rows if r.get("played")]
        return {
            "player": name,
            "team": m.get("team"),
            "status": m.get("status"),
            "reason": m.get("reason"),
            "report_stamp_et": m.get("report_stamp_et"),
            "report_url": m.get("source_url"),
            "n_logs": m.get("n_logs", len(rows)),
            "n_logs_recounted": len(rows),
            "n_games_played": len(played),
            "last_game_date": m.get("last_game_date"),
            "last_matchup": m.get("last_matchup"),
            "last_min": m.get("last_min"),
            "last_pts": m.get("last_pts"),
            "last_reb": m.get("last_reb"),
            "last_ast": m.get("last_ast"),
            "last_min_blank_reason": (played[-1].get("min_blank_reason") if played else None),
            "last_reb_blank_reason": (played[-1].get("reb_blank_reason") if played else None),
            "log_source_url": (played[-1].get("source_url") if played
                               else (rows[-1].get("source_url") if rows else None)),
            "opponents": sorted({str(r.get("opp")) for r in rows if r.get("opp")}),
            "name_artefact": bool(REVERSED_NAME_RE.match(name)),
        }

    matched_rows = [enrich(m) for m in matched]
    matched_rows.sort(key=lambda r: (r["team"] or "", r["player"]))

    unmatched_rows = []
    for u in unmatched:
        name = str(u.get("player") or "").strip()
        unmatched_rows.append({
            "player": name,
            "team": u.get("team"),
            "status": u.get("status"),
            "reason": u.get("reason"),
            "report_stamp_et": u.get("report_stamp_et"),
            "report_url": u.get("source_url"),
            "not_matched_because": u.get("reason_not_matched"),
            "name_artefact": bool(REVERSED_NAME_RE.match(name)),
            "games_held_for_club": None,
        })
    unmatched_rows.sort(key=lambda r: (r["team"] or "", r["player"]))

    n_report = join.get("n_report_rows", len(matched) + len(unmatched))
    n_matched = len(matched_rows)
    n_played = sum(1 for r in matched_rows if r["n_games_played"])
    artefacts = [r["player"] for r in matched_rows + unmatched_rows if r["name_artefact"]]

    # --- which clubs an unmatched player's club has logs for, so the gap is attributable
    club_games: dict[str, set] = {}
    for r in log_rows:
        club_games.setdefault(str(r.get("team")), set()).add(r.get("date"))
    for r in unmatched_rows:
        dates = club_games.get(r["team"] or "", set())
        r["games_held_for_club"] = len(dates)

    return {
        "schema": "nba2.v6.player-coverage.v1",
        "session": "arena/f5ac4e74-nba2",
        "join_source": "data/v5/injury_join.json",
        "logs_source": "data/v5/player_logs_union.json",
        "report_stamp_et": join.get("stamp"),
        "report_retrieved_at_utc": (matched[0].get("retrieved_at_utc") if matched else None),
        "index_url": join.get("index_url"),
        "n_report_rows": n_report,
        "n_matched": n_matched,
        "n_matched_with_minutes": n_played,
        "n_unmatched": len(unmatched_rows),
        "coverage": round(n_matched / n_report, 4) if n_report else None,
        "coverage_played": round(n_played / n_report, 4) if n_report else None,
        "coverage_recomputed": round(n_matched / n_report, 4) if n_report else None,
        "coverage_matches_v5": (round(n_matched / n_report, 4) == join.get("coverage"))
                               if n_report else None,
        "name_artefacts": sorted(set(artefacts)),
        "n_log_rows": len(log_rows),
        "n_log_games": len({r.get("game_id") for r in log_rows}),
        "n_log_clubs": len({r.get("team") for r in log_rows}),
        "log_window": logs.get("window"),
        "matched": matched_rows,
        "unmatched": unmatched_rows,
    }
