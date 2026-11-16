"""Sources and loaders for the player-level capture.

Every source in :data:`SOURCES` was read live on 2026-11-15 with the platform
page-fetch tool. Two endpoints were tried and do **not** work; they are recorded
under :data:`UNREACHABLE` so nobody re-spends a session discovering it again.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "data" / "raw" / "capture_2026-11-15-41bd6ce8"
PRIOR_CAPTURE = ROOT / "data" / "raw" / "capture_2026-11-15"

GAMELOGS = CAPTURE / "player_gamelogs.json"
ROSTERS = CAPTURE / "rosters.json"
INJURY_PM = CAPTURE / "injury_report_2026-11-15_0615PM.json"
INJURY_AM = PRIOR_CAPTURE / "injury_report_2026-11-15_0615AM.json"

SOURCES = {
    "gamelog": (
        "NBA official player game log (nba.com/stats/player/{id}/boxscores-traditional)",
        "https://www.nba.com/stats/player/201939/boxscores-traditional?Season=2026-27&SeasonType=Regular+Season",
        "official",
    ),
    "roster": (
        "NBA official club roster (nba.com/team/{id}/{slug})",
        "https://www.nba.com/team/1610612744/warriors",
        "official",
    ),
    "injury_pdf": (
        "NBA Official Injury Report, release 2026-11-15 06:15 PM ET (PDF)",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf",
        "official",
    ),
    "injury_index": (
        "NBA Official Injury Report index — the release list the freshness gate reads",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
        "official",
    ),
    "injury_prior": (
        "NBA Official Injury Report, release 2026-11-15 06:15 AM ET (PDF) — the prior release this session diffs against",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf",
        "official",
    ),
    "game": (
        "NBA official game page (nba.com/game/{id})",
        "https://www.nba.com/game/0022600210/",
        "official",
    ),
    "schedule": (
        "NBA official schedule (nba.com/schedule)",
        "https://www.nba.com/schedule",
        "official",
    ),
}

UNREACHABLE = [
    ("cdn.nba.com static JSON (liveData boxscore / scoreboard)",
     "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022600231.json",
     "HTTP 500 on every request — the JSON endpoints the site itself calls are not reachable from the build environment"),
    ("nba.com/stats/players/traditional (league-wide player table)",
     "https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=Per+Game",
     "page renders but the table prints 'No data available' — it is built by a second request the reader cannot see, so there is no one-shot league-wide player table"),
    ("nba.com/stats/team/{id}/traditional (per-club season table)",
     "https://www.nba.com/stats/team/1610612755/traditional?Season=2026-27&SeasonType=Regular+Season",
     "reachable, but it publishes club splits (overall / home / road / wins / losses), not per-player rows — S-51's 'per-club season table' is not this page"),
    ("sandbox network egress (curl / urllib)",
     "https://www.nba.com/",
     "blocked in this environment (TLS connect fails); captures are possible only through the platform page-fetch tool, which is why coverage scales with pages read"),
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def gamelogs() -> dict:
    return _load(GAMELOGS)


def rosters() -> dict:
    return _load(ROSTERS)


def injury(pm: bool = True) -> dict:
    return _load(INJURY_PM if pm else INJURY_AM)


def game_url(game_id: str) -> str:
    return f"https://www.nba.com/game/{game_id}/"


def player_url(player_id: str) -> str:
    return (f"https://www.nba.com/stats/player/{player_id}/boxscores-traditional"
            "?Season=2026-27&SeasonType=Regular+Season")


def roster_index() -> dict[str, str]:
    """{team abbr: official club page url} for the clubs whose roster was read."""
    return {c["team"]: c["source_url"] for c in rosters()["clubs"]}


def roster_ids() -> dict[str, str]:
    """{'Last, First' style name -> nba player id} for every captured club."""
    out: dict[str, str] = {}
    for c in rosters()["clubs"]:
        for p in c["players"]:
            out[p["player"]] = p["player_id"]
    return out


def team_full(team: str) -> str:
    """GSW -> 'Golden State Warriors', as the injury PDF prints club names."""
    for c in rosters()["clubs"]:
        if c["team"] == team:
            return c["team_full"]
    return team


def rules_text() -> str:
    return (
        "Capture rule: every player listed Out / Questionable / Doubtful on the official "
        "injury release whose club plays on 2026-11-16, excluding rows whose official reason "
        "begins 'G League'. Minutes are the official MM:SS; means are arithmetic on the "
        "official rows; nothing is modelled, fitted or carried forward."
    )
