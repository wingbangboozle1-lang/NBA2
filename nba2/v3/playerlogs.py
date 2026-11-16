"""Session ``arena/f8f8f2b8-nba2`` — per-player game logs and *measured* minutes shares.

Everything here is read from two committed official artifacts:

* ``data/raw/capture_2026-11-15/gamebooks_2026-11-13.json`` — the official NBA gamebook PDFs
  for all nine games played 2026-11-13 (18 clubs).
* ``data/raw/capture_2026-11-15/gamelogs_2026-11-13.json`` — one row per player per game.

and joined to the newest official injury release,
``data/raw/capture_2026-11-15/injury_report_2026-11-15_0615PM.json``.

Three things are deliberately *not* produced:

1. **No inferred minutes.** Memphis' Jerami Grant has no minutes cell in the official PDF; the
   value stays null and Memphis is excluded from the share tables (``I-F8F-07``).
2. **No observed injury-replacement delta.** Measuring "who actually absorbed the minutes when
   player X was out" needs at least two captured games per club with X in one and out of the
   other. This window has exactly one captured game per club, so that column is blank and
   flagged rather than back-solved from a single game.
3. **No blended rating.** This module reports minutes, not quality.

The replacement *pool* is measured: for each club, the players ranked outside the top eight by
minutes, with their measured shares. That is who is available to absorb a missing rotation
player's minutes, and it is read straight off the official box score.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAP = ROOT / "data" / "raw" / "capture_2026-11-15"
CAP16 = ROOT / "data" / "raw" / "capture_2026-11-16"

GAMEBOOKS = CAP / "gamebooks_2026-11-13.json"
GAMELOGS = CAP / "gamelogs_2026-11-13.json"
# Second captured window (session arena/f7186ace-nba2): the six 2026-11-15 games that were
# Final at capture. Unioned into the game-log page so the coverage scoreboard counts every
# captured game, not just the first window's nine.
GAMELOGS_1115 = CAP16 / "gamelogs_2026-11-15.json"

GAMELOG_FILES = [GAMELOGS, GAMELOGS_1115]
INJURY_PM = CAP / "injury_report_2026-11-15_0615PM.json"
INJURY_AM = CAP / "injury_report_2026-11-15_0615AM.json"
DELTA = CAP / "injury_delta_0615AM_to_0615PM.json"
# This session's newest release and its diff (brief: store every injury PDF with its
# timestamp and diff consecutive reports). The NEWEST pointer is what the coverage join and
# the banner read; the older pair above stays on disk and stays referenced by the 11-13
# capture's own record.
INJURY_NEWEST = CAP16 / "injury_report_2026-11-15_0900PM.json"
INJURY_PREV = CAP / "injury_report_2026-11-15_0615PM.json"
DELTA_NEWEST = CAP16 / "injury_delta_0615PM_to_0900PM.json"

ROTATION_SIZE = 8

# Official club name -> tri-code, as printed in the injury report's Team column.
TEAM_NAMES = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR", "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"official capture missing: {path}")
    return json.loads(path.read_text())


def _norm(name: str) -> str:
    """Normalise a player name for joining: 'Furphy, Johnny' == 'Johnny Furphy'."""
    n = re.sub(r"\s+", " ", (name or "")).strip().lower()
    n = n.replace("'", "").replace(".", "")
    if "," in n:
        last, first = n.split(",", 1)
        n = f"{first.strip()} {last.strip()}"
    return re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", n).strip()


def _mmss(sec: int | None) -> str:
    if sec is None:
        return ""
    return f"{sec // 60}:{sec % 60:02d}"


# ----------------------------------------------------------------------------- game logs
def game_logs() -> list[dict]:
    """Every captured per-player row, oldest window first, newest window last."""
    out = []
    for f in GAMELOG_FILES:
        out.extend(_load(f)["records"])
    return out


def game_log_meta() -> dict:
    metas = [{k: v for k, v in _load(f).items() if k != "records"} for f in GAMELOG_FILES]
    return {
        "windows": [m["window"] for m in metas],
        "n_windows": len(metas),
        "n_rows": sum(m["n_rows"] for m in metas),
        "n_games": sum(m["n_games"] for m in metas),
        "n_clubs": len({r["team"] for r in game_logs()}),
        "retrieved_at_utc": [m.get("retrieved_at_utc") for m in metas],
        "per_window": metas,
        "note": ("Two captured windows are unioned here. The measured-minutes page stays on the "
                 "single 2026-11-13 window (all nine games, eighteen clubs) because that is what "
                 "its shares are computed from; the game-log page below shows every captured "
                 "row from both windows."),
    }


def gamebooks() -> list[dict]:
    return _load(GAMEBOOKS)["games"]


def gamebook_meta() -> dict:
    d = _load(GAMEBOOKS)
    return {k: v for k, v in d.items() if k != "games"}


# ------------------------------------------------------------------- measured minutes shares
def minutes_table() -> list[dict]:
    """One row per club: the measured top-8 minutes shares and the measured bench pool.

    A club is only present if its captured team-game passed the minutes gate; the row carries
    ``n_games`` (1 for every club in this window) so a reader can see the sample size instead
    of having to trust it.
    """
    out: list[dict] = []
    for g in gamebooks():
        ot = g.get("ot_periods", 0)
        denom = 240 * 60 + ot * 25 * 60
        for tri, side in ((g["away"], "away"), (g["home"], "home")):
            if not g.get("minutes_complete", {}).get(tri, False):
                continue
            tm = g["teams"][tri]
            players = []
            for player, pos, mmss, pts, reb, ast in tm["played"]:
                if mmss is None:
                    continue
                m, s = mmss.split(":")
                sec = int(m) * 60 + int(s)
                players.append({"player": player, "pos": pos, "min": mmss, "min_sec": sec,
                                "share": sec / denom, "pts": pts, "reb": reb, "ast": ast})
            players.sort(key=lambda p: -p["min_sec"])
            top = players[:ROTATION_SIZE]
            bench = players[ROTATION_SIZE:]
            bench_share = sum(p["share"] for p in bench)
            out.append({
                "team": tri,
                "opponent": g["home"] if side == "away" else g["away"],
                "date": g["date"],
                "game_id": g["game_id"],
                "n_games": 1,
                "ot_periods": ot,
                "top8": top,
                "top8_share": sum(p["share"] for p in top),
                "bench": bench,
                "bench_share": bench_share,
                "n_bench": len(bench),
                "hhi_top8": sum(p["share"] ** 2 for p in top),
                "max_share": top[0]["share"] if top else None,
                "source_url": g["gamebook_url"],
            })
    out.sort(key=lambda r: r["team"])
    return out


def excluded_teams() -> list[dict]:
    meta = gamebook_meta()
    rows = []
    for p in meta.get("incomplete", []):
        g = next((x for x in gamebooks() if x["game_id"] == p["game_id"]), None)
        rows.append({
            "team": p["team"],
            "game_id": p["game_id"],
            "reason": p["reason"],
            "flag": p["flag"],
            "source_url": g["gamebook_url"] if g else None,
        })
    return rows


# ------------------------------------------------------------------ injury-report join
def injured_players(release: str = "newest") -> list[dict]:
    """Players named on the newest official injury release, normalised for joining."""
    path = {"newest": INJURY_NEWEST, "prev": INJURY_PREV,
            "PM": INJURY_PM, "AM": INJURY_AM}[release]
    rows = _load(path)["records"]
    out = []
    for r in rows:
        date, time_et, matchup, team, player, status, reason = r[:7]
        if not player:
            continue  # a "NOT YET SUBMITTED" placeholder names no player
        out.append({"date": date, "time_et": time_et, "matchup": matchup,
                    "team_name": team, "team": TEAM_NAMES.get(team), "player": player,
                    "key": _norm(player), "status": status, "reason": reason,
                    "source_url": _load(path)["provenance"]["url"]})
    return out


def injury_coverage() -> dict:
    """Join the injury report to the captured logs.

    The brief asks for game logs "for at least the players who appear on an injury report".
    This is the honest scoreboard for that: how many of the named players have a captured
    log row, and which clubs have no captured game at all in this window.
    """
    logs = game_logs()
    by_key: dict[tuple[str, str], dict] = {}
    for r in logs:
        by_key.setdefault((r["team"], _norm(r["player"])), r)

    covered_teams = {r["team"] for r in minutes_table()} | {r["team"] for r in logs}
    injured = injured_players()

    matched, missing_capture, missing_club = [], [], []
    for p in injured:
        row = by_key.get((p["team"], p["key"]))
        if row is not None:
            matched.append({**p, **{k: row[k] for k in
                                    ("game_id", "opponent", "min", "min_sec", "pts", "reb",
                                     "ast")},
                            "log_source": row["source_url"]})
        elif p["team"] not in covered_teams:
            missing_club.append(p)
        else:
            missing_capture.append(p)

    return {
        "n_injured_named": len(injured),
        "n_matched": len(matched),
        "n_no_row_in_captured_game": len(missing_capture),
        "n_club_not_captured": len(missing_club),
        "matched": matched,
        "no_row_in_captured_game": missing_capture,
        "club_not_captured": missing_club,
        "clubs_captured": sorted(covered_teams),
        "clubs_not_captured": sorted({p["team"] for p in missing_club if p["team"]}),
    }


# ----------------------------------------------------------------------------- injury diff
def injury_release_diff() -> dict:
    d = _load(DELTA_NEWEST)
    pm = _load(INJURY_NEWEST)
    am = _load(INJURY_PREV)
    return {
        "delta": d,
        "pm_provenance": pm["provenance"],
        "am_provenance": am["provenance"],
        "pm_rows": len(pm["records"]),
        "am_rows": len(am["records"]),
    }


def release_stamps() -> dict:
    """Revision time and retrieval time of the two newest releases, computed not typed."""
    pm = _load(INJURY_NEWEST)
    am = _load(INJURY_PREV)

    def _hms(a: str, b: str) -> str:
        import datetime as _dt
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        d = _dt.datetime.strptime(a, fmt) - _dt.datetime.strptime(b, fmt)
        return f"{d.days * 24 + d.seconds // 3600}h{(d.seconds % 3600) // 60:02d}m"

    return {
        "revision_time_et": pm["revision_time_et"],
        "retrieved_at_utc": pm["retrieved_at_utc"],
        "retrieved_at_et": pm.get("retrieved_at_et"),
        "report_url": pm["provenance"]["url"],
        "index_url": pm["provenance"]["index_url"],
        "prior_revision_time_et": am["revision_time_et"],
        "prior_retrieved_at_utc": am["retrieved_at_utc"],
        "prior_report_url": am["provenance"]["url"],
        "elapsed": _hms(pm["retrieved_at_utc"], am["retrieved_at_utc"]),
        "rows": len(pm["records"]),
        "prior_rows": len(am["records"]),
    }


def all_teams() -> list[str]:
    return sorted({t for g in gamebooks() for t in (g["away"], g["home"])})
