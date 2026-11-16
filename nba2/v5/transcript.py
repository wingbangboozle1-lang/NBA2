"""Load and normalise the v5 official gamebook transcripts.

The transcripts in ``data/v5/gamebooks_*.json`` are the official NBA gamebook PDFs
(statsdmz.nba.com) read as text through the platform page-fetch tool. This module does
not fetch anything: it reads what is committed and turns it into one row per player per
game, plus one row per game for the result feed.

Two rules are enforced here rather than downstream:

* nothing is inferred — a value the PDF did not print stays ``None`` and carries a reason;
* every emitted row carries the URL it was read from and the retrieval window of the file
  it lives in.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
V5 = DATA / "v5"

SESSION = "arena/6e46dbf2-nba2"

TRANSCRIPTS = [
    V5 / "gamebooks_2026-11-14.json",
    V5 / "gamebooks_2026-11-15.json",
]

# The committed 11/13 player logs (session arena/f8f8f2b8-nba2) use schema
# nba2.player-gamelog.v2 and are folded into the union read-only.
LEGACY_1113 = DATA / "raw" / "capture_2026-11-15" / "gamelogs_2026-11-13.json"

TEAM_NAME = {
    "Atlanta Hawks": "ATL", "Brooklyn Nets": "BKN", "Boston Celtics": "BOS",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}

# Minutes tolerance for the sum-of-players gate. The official PDFs round each player's
# minutes to the second, so a whole team can legitimately sum to 240:01 or 239:59.
MIN_TOLERANCE_S = 5


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def player_rows() -> list[dict]:
    """One row per player per game, newest transcripts first, then the 11/13 legacy rows."""
    rows: list[dict] = []
    for path in TRANSCRIPTS:
        doc = _load(path)
        window = doc["retrieved_window_utc"]
        for g in doc["games"]:
            for tri, blk in g["teams"].items():
                reb_reason = blk.get("reb_blank_reason")
                for p in blk["players"]:
                    rows.append({
                        "date": g["date"],
                        "game_id": g["game_id"],
                        "matchup": g["matchup"],
                        "team": tri,
                        "opp": blk["opp"],
                        "home": blk["side"] == "home",
                        "player": p["name"],
                        "jersey": p.get("jersey"),
                        "pos": p.get("pos"),
                        "min": p.get("min"),
                        "min_sec": p.get("min_sec"),
                        "pts": p.get("pts"),
                        "reb": p.get("reb"),
                        "ast": p.get("ast"),
                        "fg": p.get("fg"),
                        "fg3": p.get("fg3"),
                        "ft": p.get("ft"),
                        "status": p.get("status"),
                        "played": p.get("min_sec") is not None or p.get("pts") is not None,
                        "reb_blank_reason": (reb_reason if p.get("reb") is None
                                             and p.get("min_sec") is not None else None),
                        "min_blank_reason": (
                            "F-V5-10: the 11/13 capture records this player's count line "
                            "but not his minutes; the minutes are blank here rather than "
                            "back-filled from the box score"
                            if p.get("min_sec") is None and p.get("pts") is not None else None),
                        "note": p.get("note"),
                        "source_url": g["source_url"],
                        "source_class": "official",
                        "retrieved_window_utc": window,
                        "transcript": path.name,
                    })
    rows.extend(_legacy_rows())
    rows.sort(key=lambda r: (r["date"], r["matchup"], r["team"],
                             0 if r["played"] else 1, -(r["min_sec"] or 0)))
    return rows


def _legacy_rows() -> list[dict]:
    if not LEGACY_1113.exists():
        return []
    doc = _load(LEGACY_1113)
    out = []
    for r in doc.get("records", []):
        out.append({
            "date": r["date"],
            "game_id": r.get("game_id"),
            "matchup": r.get("matchup", f"{r['team']}@{r['opponent']}"),
            "team": r["team"],
            "opp": r["opponent"],
            "home": bool(r.get("home")),
            "player": r["player"],
            "jersey": None,
            "pos": r.get("pos"),
            "min": r.get("min"),
            "min_sec": r.get("min_sec"),
            "pts": r.get("pts"),
            "reb": r.get("reb"),
            "ast": r.get("ast"),
            "fg": None,
            "fg3": None,
            "ft": None,
            "status": None,
            "played": r.get("min_sec") is not None or r.get("pts") is not None,
            "reb_blank_reason": None,
            "min_blank_reason": (
                "F-V5-10: the 11/13 capture records this player's count line but not his "
                "minutes; the minutes are blank here rather than back-filled"
                if r.get("min_sec") is None and r.get("pts") is not None else None),
            "note": "11/13 capture (session arena/f8f8f2b8-nba2): the file records only the "
                    "players who played, so no DNP/DND row exists for this date and "
                    "'out' cannot be measured from it.",
            "source_url": r.get("source_url"),
            "source_class": r.get("source_class", "official"),
            "retrieved_window_utc": doc.get("retrieved_at_utc"),
            "transcript": "gamelogs_2026-11-13.json",
        })
    return out


def games() -> list[dict]:
    """One record per game in the v5 transcripts (final + quarter rows + club totals)."""
    out = []
    for path in TRANSCRIPTS:
        doc = _load(path)
        for g in doc["games"]:
            rec = dict(g)
            rec["retrieved_window_utc"] = doc["retrieved_window_utc"]
            rec["transcript"] = path.name
            out.append(rec)
    return out


def team_games(rows: list[dict]) -> dict[tuple[str, str], list[dict]]:
    """(team, game_id) -> that club's rows in that game, sorted by minutes played."""
    out: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        out.setdefault((r["team"], r["game_id"]), []).append(r)
    for v in out.values():
        v.sort(key=lambda r: (-(r["min_sec"] or 0), r["player"]))
    return out
