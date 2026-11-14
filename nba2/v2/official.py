"""Official NBA snapshot for the v2 build — transcribed from pages fetched live on 2026-11-14.

Every number here was read off an NBA.com / NBA official-CDN page. Nothing is inferred, nothing
is filled in. The source URL for each field family is declared in ``SOURCES`` so every published
row can carry a link back to the page it came from.

Retrieval record (session ``arena/a7d4a562-nba2``, 2026-11-14 UTC)
-----------------------------------------------------------------
The sandbox that builds this site has **no direct HTTP egress**: ``curl`` to nba.com,
stats.nba.com, cdn.nba.com and basketball-reference.com returns HTTP 000 (TLS handshake
refused). Pages were therefore read through a markdown-rendering fetch client and transcribed
by hand, then machine-checked against arithmetic identities that a mis-transcription would
break (see ``integrity()`` and the site's verification page). This is recorded because "how the
number got here" is part of whether it can be trusted.

* ``www.nba.com/schedule`` ................ full schedule, 11/13 finals → 11/17, times, arenas,
  game IDs, national TV, Cup group ....... fetched OK (the 11/13 slate had already gone Final:
  NYK 104 IND 106, MIL 99 ORL 107, CLE 121 MIA 133, ATL 117 CHI 125 (OT), MEM 142 NOP 111,
  UTA 118 HOU 125, GSW 85 SAS 123, POR 120 SAC 107, OKC 112 LAC 113)
* ``www.nba.com/standings`` ................ W/L, home/road splits ................. fetched OK
* ``www.nba.com/stats/teams/traditional`` .. GP/W/L/PTS, FG/FG3/FT, REB, AST, TOV ..... fetched OK
* ``www.nba.com/stats/teams/opponent`` ..... opponent PTS (points allowed) ..... fetched OK
* ``www.nba.com/stats/teams/advanced`` ..... OffRtg/DefRtg/NetRtg/PACE/PIE ......... fetched OK
* ``ak-static.cms.nba.com/...Injury-Report_2026-11-13_07_30PM.pdf`` ... NOT re-read this session
* ``stats.nba.com`` JSON, ``cdn.nba.com`` JSON, Basketball-Reference 2026-27 game logs ... blocked

Team-level *game-by-game* data is available only for the games committed under
``data/raw/history/**`` (155 official finals); player box scores are not available at all.
Anything that needs them is published as BLOCKED, never guessed.
"""

from __future__ import annotations

import math

# --------------------------------------------------------------------------- sources
SOURCES = {
    "standings": (
        "NBA.com Standings (official)",
        "https://www.nba.com/standings",
        "W, L, WIN%, home/road splits, conference and division records.",
    ),
    "team_trad": (
        "NBA.com Stats — Teams Traditional (official)",
        "https://www.nba.com/stats/teams/traditional",
        "GP, MIN, PTS (points per game), +/- , per-team shooting splits.",
    ),
    "team_opp": (
        "NBA.com Stats — Teams Opponent (official)",
        "https://www.nba.com/stats/teams/opponent",
        "Opponent PTS per game (points allowed), opponent shooting splits.",
    ),
    "team_adv": (
        "NBA.com Stats — Teams Advanced (official)",
        "https://www.nba.com/stats/teams/advanced",
        "OffRtg, DefRtg, NetRtg, PACE, PIE — all per-100-possession.",
    ),
    "schedule": (
        "NBA.com Schedule (official)",
        "https://www.nba.com/schedule",
        "Game IDs, ET tip times, arenas, national broadcast, Emirates NBA Cup group.",
    ),
    "injury_pdf": (
        "NBA Official Injury Report 11/13/26 04:15 PM ET (official PDF)",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf",
        "Per-player status (Out/Doubtful/Questionable/Probable/Available) with the stated reason.",
    ),
    "injury_policy": (
        "NBA Official — Injury Report policy and report archive (official)",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
        "Filing deadlines: 5 p.m. local the day before; game day 11 a.m.–1 p.m.; "
        "1 p.m. local for the second of a back-to-back.",
    ),
    "players": (
        "NBA.com Stats — Players Traditional (official)",
        "https://www.nba.com/stats/players/traditional",
        "Per-player GP, MIN, PTS, REB, AST for the rows used on this site.",
    ),
}

# Why an input is absent. Published verbatim next to every blank cell.
BLOCKED = {
    "game_logs": (
        "Per-game margins and totals",
        "No official per-game result table is reachable from this build. stats.nba.com and "
        "cdn.nba.com return TLS errors and Basketball-Reference has no 2026-27 game log "
        "(HTTP 404). Required for: measured spread/total correlation, backtests, settling bets.",
        "https://www.basketball-reference.com/teams/LAL/2027_gamelog.html",
    ),
    "player_box": (
        "Per-player game logs (minutes, usage, on/off)",
        "nba.com/stats player pages render season aggregates only for this client. Required for: "
        "minutes distributions, prop bet probabilities, injury replacement modelling.",
        "https://www.nba.com/stats/players/traditional",
    ),
    "odds": (
        "Market prices (spread, total, moneyline, prop lines)",
        "No licensed odds feed is connected and NBA.com renders odds client-side only. "
        "Required for: any value/edge claim, stake sizing, ROI, leaderboard scoring.",
        "https://www.nba.com/games",
    ),
}

AS_OF = "2026-11-14"
RETRIEVED_AT_UTC = "2026-11-14T00:00:00Z"  # session date; page fetch time not exposed by the client

# --------------------------------------------------------------------------- team table
# tricode: W, L, HOME_W, HOME_L, ROAD_W, ROAD_L, PF(pts/g), PA(pts/g), OEFF, DEF, NET, PACE, PIE
# PF from /stats/teams/traditional, PA from /stats/teams/opponent, OEFF..PIE from /stats/teams/advanced.
# W/L and home/road splits independently confirmed on /standings (30/30 identical).
TEAMS: dict[str, tuple] = {
    "ATL": (7, 6, 3, 3, 4, 3, 118.2, 116.8, 113.3, 111.9, 1.4, 103.55, 48.5),
    "BOS": (10, 2, 5, 0, 5, 2, 114.3, 103.1, 117.4, 105.6, 11.7, 96.62, 55.9),
    "BKN": (3, 8, 1, 3, 2, 5, 110.2, 115.3, 109.3, 114.4, -5.2, 99.83, 47.0),
    "CHA": (4, 8, 3, 4, 1, 4, 98.6, 109.6, 101.8, 113.0, -11.2, 96.92, 42.9),
    "CHI": (2, 9, 1, 4, 1, 5, 114.4, 127.7, 109.0, 122.0, -12.9, 103.83, 44.0),
    "CLE": (6, 7, 4, 2, 2, 5, 116.8, 115.8, 116.1, 115.2, 0.9, 99.75, 51.0),
    "DAL": (7, 5, 5, 2, 2, 3, 113.2, 112.2, 112.5, 111.7, 0.8, 100.50, 50.3),
    "DEN": (6, 4, 2, 2, 3, 2, 114.5, 113.3, 115.9, 115.1, 0.7, 97.58, 52.2),
    "DET": (8, 3, 3, 2, 5, 1, 115.5, 107.8, 114.1, 106.9, 7.2, 99.17, 55.3),
    "GSW": (8, 5, 6, 1, 2, 4, 116.7, 112.4, 116.1, 112.0, 4.1, 99.66, 51.8),
    "HOU": (10, 3, 7, 1, 3, 2, 116.2, 107.4, 119.3, 110.2, 9.1, 97.42, 55.8),
    "IND": (5, 8, 2, 4, 3, 3, 111.2, 113.2, 110.1, 111.7, -1.5, 101.15, 49.6),
    "LAC": (3, 8, 3, 3, 0, 5, 112.3, 117.5, 110.7, 115.8, -5.1, 100.55, 47.4),
    "LAL": (11, 2, 5, 1, 6, 1, 122.2, 114.2, 121.6, 113.6, 8.0, 100.50, 54.2),
    "MEM": (8, 4, 2, 4, 6, 0, 119.9, 111.8, 117.8, 110.0, 7.8, 100.87, 53.2),
    "MIA": (6, 6, 2, 3, 4, 3, 117.2, 120.1, 113.2, 116.4, -3.2, 102.44, 49.0),
    "MIL": (1, 12, 1, 6, 0, 6, 106.2, 120.2, 105.7, 120.0, -14.2, 100.31, 42.0),
    "MIN": (9, 3, 5, 1, 4, 2, 119.3, 105.9, 117.2, 103.8, 13.4, 101.08, 56.1),
    "NOP": (4, 9, 3, 5, 1, 4, 116.5, 125.6, 111.4, 120.2, -8.8, 102.08, 46.2),
    "NYK": (6, 6, 4, 3, 2, 3, 109.8, 103.7, 114.5, 108.6, 5.9, 95.63, 53.3),
    "OKC": (8, 5, 5, 0, 3, 5, 111.2, 107.4, 112.7, 109.0, 3.7, 98.58, 53.3),
    "ORL": (5, 7, 1, 4, 4, 3, 108.3, 112.8, 109.7, 113.4, -3.7, 98.23, 47.6),
    "PHI": (10, 3, 5, 2, 5, 1, 111.2, 109.4, 111.0, 109.5, 1.5, 100.04, 50.9),
    "PHX": (5, 6, 5, 3, 0, 3, 111.7, 116.1, 113.8, 117.6, -3.8, 98.45, 48.1),
    "POR": (9, 3, 3, 2, 6, 1, 119.6, 111.8, 118.8, 111.1, 7.7, 100.67, 53.3),
    "SAC": (1, 11, 0, 7, 1, 4, 108.2, 120.9, 107.3, 119.5, -12.2, 101.00, 42.8),
    "SAS": (11, 2, 5, 2, 6, 0, 119.5, 106.2, 119.6, 106.6, 13.0, 98.94, 56.7),
    "TOR": (5, 7, 2, 3, 3, 4, 114.3, 112.8, 114.5, 112.8, 1.7, 99.88, 49.3),
    "UTA": (1, 12, 1, 6, 0, 6, 107.5, 118.6, 105.0, 116.4, -11.3, 100.50, 45.3),
    "WAS": (4, 9, 2, 3, 2, 6, 110.0, 115.8, 108.7, 114.3, -5.5, 99.63, 47.1),
}

# Official /standings also carries a NEUTRAL column. Two teams have played one neutral-site
# game each, which is why home+road does not equal GP for them:
#   DEN neutral 1-0, IND neutral 0-1.
# With those two games counted, the identity closes exactly: 182 home + 182 road + 2 neutral
# = 366 team-games = 183 games.
# tricode: (neutral_w, neutral_l)
NEUTRAL = {"DEN": (1, 0), "IND": (0, 1)}

NAMES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}

# Per-team source links (each page is the canonical official page for that team's stats).
# NBA team URLs are keyed by a 10-digit team id, NOT by tricode: https://www.nba.com/stats/team/ATL
# does not exist, so a tricode-based link was a dead source on every team row. The ids below are
# the ones nba.com prints in its own links on /standings and /stats/teams/traditional
# (e.g. .../team/1610612739/cavaliers).
TEAM_ID = {
    "ATL": "1610612737", "BOS": "1610612738", "BKN": "1610612751", "CHA": "1610612766",
    "CHI": "1610612741", "CLE": "1610612739", "DAL": "1610612742", "DEN": "1610612743",
    "DET": "1610612765", "GSW": "1610612744", "HOU": "1610612745", "IND": "1610612754",
    "LAC": "1610612746", "LAL": "1610612747", "MEM": "1610612763", "MIA": "1610612748",
    "MIL": "1610612749", "MIN": "1610612750", "NOP": "1610612740", "NYK": "1610612752",
    "OKC": "1610612760", "ORL": "1610612753", "PHI": "1610612755", "PHX": "1610612756",
    "POR": "1610612757", "SAC": "1610612758", "SAS": "1610612759", "TOR": "1610612761",
    "UTA": "1610612762", "WAS": "1610612764",
}
TEAM_SOURCE = {
    tri: "https://www.nba.com/stats/team/{}/traditional".format(TEAM_ID[tri])
    for tri in TEAMS
}

# --------------------------------------------------------------------------- the slate
# From https://www.nba.com/schedule (date=2026-11-14), read 2026-11-14.
# date, time_et, away, home, game_id, arena, city, national_broadcast, cup_group
SLATE = [
    ("2026-11-14", "19:00", "DEN", "NOP", "0022600231", "Smoothie King Center", "New Orleans, LA", "League Pass", ""),
    ("2026-11-14", "19:30", "DAL", "CLE", "0022600232", "Rocket Arena", "Cleveland, OH", "League Pass", ""),
    ("2026-11-14", "20:00", "DET", "MIA", "0022600233", "Kaseya Center", "Miami, FL", "NBA TV", ""),
    ("2026-11-14", "20:00", "BKN", "MEM", "0022600234", "FedExForum", "Memphis, TN", "League Pass", ""),
    ("2026-11-14", "20:00", "CHI", "MIN", "0022600235", "Target Center", "Minneapolis, MN", "League Pass", ""),
    ("2026-11-15", "13:00", "IND", "PHI", "0022600236", "Xfinity Mobile Arena", "Philadelphia, PA", "League Pass", ""),
    ("2026-11-15", "16:00", "LAL", "PHX", "0022600237", "Mortgage Matchup Center", "Phoenix, AZ", "League Pass", ""),
    ("2026-11-15", "16:30", "CHA", "LAC", "0022600238", "Intuit Dome", "Inglewood, CA", "League Pass", ""),
    ("2026-11-15", "17:00", "SAS", "UTA", "0022600239", "Delta Center", "Salt Lake City, UT", "League Pass", ""),
    ("2026-11-15", "18:00", "DAL", "BOS", "0022600240", "TD Garden", "Boston, MA", "League Pass", ""),
    ("2026-11-15", "18:00", "NYK", "TOR", "0022600241", "Scotiabank Arena", "Toronto, ON", "League Pass", ""),
    ("2026-11-15", "19:00", "HOU", "WAS", "0022600242", "Capital One Arena", "Washington, DC", "MNMT / League Pass", ""),
    ("2026-11-15", "20:00", "ATL", "MIL", "0022600243", "Fiserv Forum", "Milwaukee, WI", "League Pass", ""),
    ("2026-11-15", "21:00", "OKC", "SAC", "0022600244", "Golden 1 Center", "Sacramento, CA", "League Pass", ""),
    ("2026-11-16", "19:00", "ORL", "BOS", "0022600245", "TD Garden", "Boston, MA", "Peacock / NBC Sports Network", ""),
    ("2026-11-16", "19:00", "CHI", "CLE", "0022600246", "Rocket Arena", "Cleveland, OH", "League Pass", ""),
    ("2026-11-16", "19:00", "MEM", "WAS", "0022600247", "Capital One Arena", "Washington, DC", "MNMT / League Pass", ""),
    ("2026-11-16", "19:30", "PHI", "BKN", "0022600248", "Barclays Center", "Brooklyn, NY", "League Pass", ""),
    ("2026-11-16", "19:30", "HOU", "MIA", "0022600249", "Kaseya Center", "Miami, FL", "League Pass", ""),
    ("2026-11-16", "20:00", "POR", "MIN", "0022600250", "Target Center", "Minneapolis, MN", "League Pass", ""),
    ("2026-11-16", "20:00", "GSW", "NOP", "0022600251", "Smoothie King Center", "New Orleans, LA", "League Pass", ""),
    ("2026-11-16", "21:00", "PHX", "DEN", "0022600252", "Ball Arena", "Denver, CO", "League Pass", ""),
    # 11/13 games: kept so a settled-game audit is possible, and because the injury report
    # that IS readable (11/13 04:15 PM) covers them.
    ("2026-11-13", "19:00", "NYK", "IND", "0022600034", "Gainbridge Fieldhouse", "Indianapolis, IN", "Prime Video", "East Group B"),
    ("2026-11-13", "19:00", "MIL", "ORL", "0022600035", "Kia Center", "Orlando, FL", "League Pass", "East Group A"),
    ("2026-11-13", "20:00", "CLE", "MIA", "0022600036", "Kaseya Center", "Miami, FL", "League Pass", "East Group B"),
    ("2026-11-13", "20:00", "ATL", "CHI", "0022600037", "United Center", "Chicago, IL", "League Pass", "East Group C"),
    ("2026-11-13", "20:00", "MEM", "NOP", "0022600038", "Smoothie King Center", "New Orleans, LA", "League Pass", "West Group B"),
    ("2026-11-13", "20:30", "UTA", "HOU", "0022600039", "Toyota Center", "Houston, TX", "League Pass", "West Group A"),
    ("2026-11-13", "21:30", "GSW", "SAS", "0022600040", "Frost Bank Center", "San Antonio, TX", "Prime Video", "West Group C"),
    ("2026-11-13", "22:00", "POR", "SAC", "0022600041", "Golden 1 Center", "Sacramento, CA", "League Pass", "West Group C"),
    ("2026-11-13", "22:30", "OKC", "LAC", "0022600042", "Intuit Dome", "Inglewood, CA", "League Pass", "West Group B"),
]

# The 3-day pick window. Today is 2026-11-14 (UTC), so the window is
# 2026-11-14 → 2026-11-17 (build date + 3 days), read from nba.com/schedule on 2026-11-14.
# The 11/13 slate is deliberately NOT here any more: all nine games had gone Final before this
# session read the schedule (see the retrieval record above), so pricing them "in advance"
# would be pricing games whose results are already known.
SLATE = [
    ("2026-11-14", "19:00", "DEN", "NOP", "0022600231", "Smoothie King Center", "New Orleans, LA", "League Pass", ""),
    ("2026-11-14", "19:30", "DAL", "CLE", "0022600232", "Rocket Arena", "Cleveland, OH", "League Pass", ""),
    ("2026-11-14", "20:00", "DET", "MIA", "0022600233", "Kaseya Center", "Miami, FL", "NBA TV", ""),
    ("2026-11-14", "20:00", "BKN", "MEM", "0022600234", "FedExForum", "Memphis, TN", "League Pass", ""),
    ("2026-11-14", "20:00", "CHI", "MIN", "0022600235", "Target Center", "Minneapolis, MN", "League Pass", ""),
    ("2026-11-15", "13:00", "IND", "PHI", "0022600236", "Xfinity Mobile Arena", "Philadelphia, PA", "League Pass", ""),
    ("2026-11-15", "16:00", "LAL", "PHX", "0022600237", "Mortgage Matchup Center", "Phoenix, AZ", "League Pass", ""),
    ("2026-11-15", "16:30", "CHA", "LAC", "0022600238", "Intuit Dome", "Inglewood, CA", "League Pass", ""),
    ("2026-11-15", "17:00", "SAS", "UTA", "0022600239", "Delta Center", "Salt Lake City, UT", "League Pass", ""),
    ("2026-11-15", "18:00", "DAL", "BOS", "0022600240", "TD Garden", "Boston, MA", "League Pass", ""),
    ("2026-11-15", "18:00", "NYK", "TOR", "0022600241", "Scotiabank Arena", "Toronto, ON", "League Pass", ""),
    ("2026-11-15", "19:00", "HOU", "WAS", "0022600242", "Capital One Arena", "Washington, DC", "MNMT / League Pass", ""),
    ("2026-11-15", "20:00", "ATL", "MIL", "0022600243", "Fiserv Forum", "Milwaukee, WI", "League Pass", ""),
    ("2026-11-15", "21:00", "OKC", "SAC", "0022600244", "Golden 1 Center", "Sacramento, CA", "League Pass", ""),
    ("2026-11-16", "19:00", "ORL", "BOS", "0022600245", "TD Garden", "Boston, MA", "Peacock / NBC Sports Network", ""),
    ("2026-11-16", "19:00", "CHI", "CLE", "0022600246", "Rocket Arena", "Cleveland, OH", "League Pass", ""),
    ("2026-11-16", "19:00", "MEM", "WAS", "0022600247", "Capital One Arena", "Washington, DC", "MNMT / League Pass", ""),
    ("2026-11-16", "19:30", "PHI", "BKN", "0022600248", "Barclays Center", "Brooklyn, NY", "League Pass", ""),
    ("2026-11-16", "19:30", "HOU", "MIA", "0022600249", "Kaseya Center", "Miami, FL", "League Pass", ""),
    ("2026-11-16", "20:00", "POR", "MIN", "0022600250", "Target Center", "Minneapolis, MN", "League Pass", ""),
    ("2026-11-16", "20:00", "GSW", "NOP", "0022600251", "Smoothie King Center", "New Orleans, LA", "League Pass", ""),
    ("2026-11-16", "21:00", "PHX", "DEN", "0022600252", "Ball Arena", "Denver, CO", "League Pass", ""),
    # Tuesday 11/17 — the outer edge of the 3-day window (official day header: "5 Games")
    ("2026-11-17", "19:30", "NYK", "TOR", "0022600253", "Scotiabank Arena", "Toronto, ON", "League Pass", ""),
    ("2026-11-17", "20:00", "POR", "MIN", "0022600254", "Target Center", "Minneapolis, MN", "League Pass", ""),
    ("2026-11-17", "20:00", "DET", "SAS", "0022600255", "Frost Bank Center", "San Antonio, TX", "Peacock / NBC", ""),
    ("2026-11-17", "23:00", "CHA", "LAL", "0022600256", "Crypto.com Arena", "Los Angeles, CA", "Peacock", ""),
    ("2026-11-17", "22:30", "UTA", "LAC", "0022600257", "Intuit Dome", "Inglewood, CA", "League Pass", ""),
]

# --------------------------------------------------------------------------- rest / density
# Every game date each team plays or played within the stretch of the official schedule read on
# 2026-11-14. These are DATES ONLY, transcribed from https://www.nba.com/schedule, and they are
# what "rest" and "back-to-back" are computed from — the priced window alone is not enough,
# because a team can enter the window on the second of a back-to-back and a window-local count
# cannot see it. 11/13 appears because those games were played and finished.
SCHEDULE_DATES_ALL = {
    "ATL": ["2026-11-13", "2026-11-15"],
    "BOS": ["2026-11-15", "2026-11-16"],
    "BKN": ["2026-11-14", "2026-11-16", "2026-11-18"],
    "CHA": ["2026-11-15", "2026-11-17"],
    "CHI": ["2026-11-13", "2026-11-14", "2026-11-16", "2026-11-18"],
    "CLE": ["2026-11-13", "2026-11-14", "2026-11-16", "2026-11-18"],
    "DAL": ["2026-11-14", "2026-11-15"],
    "DEN": ["2026-11-14", "2026-11-16"],
    "DET": ["2026-11-14", "2026-11-17", "2026-11-18"],
    "GSW": ["2026-11-13", "2026-11-16"],
    "HOU": ["2026-11-13", "2026-11-15", "2026-11-16", "2026-11-18"],
    "IND": ["2026-11-13", "2026-11-15", "2026-11-18"],
    "LAC": ["2026-11-13", "2026-11-15", "2026-11-17"],
    "LAL": ["2026-11-13", "2026-11-15", "2026-11-17"],
    "MEM": ["2026-11-13", "2026-11-14", "2026-11-16", "2026-11-18"],
    "MIA": ["2026-11-13", "2026-11-14", "2026-11-16", "2026-11-18"],
    "MIL": ["2026-11-13", "2026-11-15", "2026-11-18"],
    "MIN": ["2026-11-14", "2026-11-16", "2026-11-17"],
    "NOP": ["2026-11-13", "2026-11-14", "2026-11-16", "2026-11-18"],
    "NYK": ["2026-11-13", "2026-11-15", "2026-11-17"],
    "OKC": ["2026-11-13", "2026-11-15"],
    "ORL": ["2026-11-13", "2026-11-16", "2026-11-18"],
    "PHI": ["2026-11-15", "2026-11-16", "2026-11-18"],
    "PHX": ["2026-11-15", "2026-11-16"],
    "POR": ["2026-11-13", "2026-11-16", "2026-11-17"],
    "SAC": ["2026-11-13", "2026-11-15"],
    "SAS": ["2026-11-13", "2026-11-15", "2026-11-17"],
    "TOR": ["2026-11-15", "2026-11-17", "2026-11-18"],
    "UTA": ["2026-11-13", "2026-11-15", "2026-11-17"],
    "WAS": ["2026-11-15", "2026-11-16", "2026-11-18"],
}

# The days immediately before the window that a rest count may look back to. 11/12 is inferred
# as a non-game day ONLY for teams whose next listed game is 11/14 or later and whose count cannot
# otherwise be closed; it is never published as a rest figure on its own.
KNOWN_NO_GAME_DATES = ["2026-11-12"]

# Games published on the official schedule that fall OUTSIDE the 3-day window (day-after
# context only — never priced, never picked). Wednesday 11/18 = "12 Games" on the official day
# header. Only the seven games actually read off the page are transcribed here; the remaining
# five are NOT filled in, because filling them in from the day total would be inference.
OUTSIDE_WINDOW = [
    ("2026-11-18", "19:00", "MEM", "CLE", "0022600258", "Rocket Arena", "Cleveland, OH"),
    ("2026-11-18", "19:00", "HOU", "IND", "0022600259", "Gainbridge Fieldhouse", "Indianapolis, IN"),
    ("2026-11-18", "19:00", "MIL", "MIA", "0022600260", "Kaseya Center", "Miami, FL"),
    ("2026-11-18", "19:00", "PHI", "ORL", "0022600261", "Kia Center", "Orlando, FL"),
    ("2026-11-18", "19:30", "CHI", "BKN", "0022600262", "Barclays Center", "Brooklyn, NY"),
    ("2026-11-18", "19:30", "WAS", "TOR", "0022600263", "Scotiabank Arena", "Toronto, ON"),
    ("2026-11-18", "20:00", "DET", "NOP", "0022600264", "Smoothie King Center", "New Orleans, LA"),
    # the official page continues past this point (11/18 header = "12 Games"); the remaining
    # five are deliberately left untranscribed rather than inferred from the day total.
]

# --------------------------------------------------------------------------- injuries
# Full 95-row transcription of the 11/13/26 04:15 PM ET report — matches the committed
# snapshot data/raw/injury_report_2026-11-13.json row for row (verified 2026-11-14 by the
# session that captured it). NOT re-read by session arena/a7d4a562-nba2: the PDF is served
# from ak-static.cms.nba.com, which this sandbox cannot reach (HTTP 000). The snapshot is
# therefore published as captured, and the site states that its freshness is 2026-11-13
# 16:15 ET rather than implying it was re-verified today.
INJURY_PDF_URL = SOURCES["injury_pdf"][1]

INJURIES = [
    # date, time, matchup, team, player, status, reason, attribution
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Banchero, Paolo", "Out", "Injury/Illness - Right High Ankle Sprain", "E"),
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Cain, Jamal", "Questionable", "Injury/Illness - Left Shoulder Contusion", "E"),
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "da Silva, Tristan", "Questionable", "Injury/Illness - Left Calf Strain", "E"),
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Isaac, Jonathan", "Out", "Injury/Illness - Left Knee Injury Management", "E"),
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Nelson, Izaiyah", "Out", "Injury/Illness - Left Ankle Injury Recovery", "E"),
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Penda, Noah", "Out", "Injury/Illness - Right Partially Torn Hamstring", "E"),
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Suggs, Jalen", "Questionable", "Injury/Illness - Right Knee Contusion/Bone Bruise", "E"),
    ("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Furphy, Johnny", "Out", "Injury/Illness - Right ACL Repair/Surgery", "E"),
    ("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Haliburton, Tyrese", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "McConnell, T.J.", "Probable", "Injury/Illness - Right Hamstring Strain", "E"),
    ("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Nesmith, Aaron", "Questionable", "Injury/Illness - Right Knee Soreness", "E"),
    ("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Sheppard, Ben", "Out", "Injury/Illness - Left Meniscus Surgery", "E"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Dennis, RayJ", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Flemings, Kingston", "Questionable", "Injury/Illness - Lumbar Spasm", "C"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Gilbert, Keshon", "Out", "Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure", "C"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Gueye, Mouhamed", "Out", "Injury/Illness - Left Foot Fracture", "C"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Landale, Jock", "Available", "Injury/Illness - Face Mask", "C"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Newell, Asa", "Out", "Injury/Illness - Left Great Toe Hyperextension", "C"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Veesaar, Henri", "Out", "Injury/Illness - Right ACL Tear", "C"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Wilson, Jalen", "Out", "G League - Two-Way", "C"),
    ("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Awaka, Tobe", "Out", "Injury/Illness - Disc Irritation", "E"),
    ("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Powell, Norman", "Questionable", "Injury/Illness - Low Back Spasms", "E"),
    ("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Sellers, Jaylin", "Out", "G League - Two-Way", "E"),
    ("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Swain, Dailyn", "Questionable", "Injury/Illness - Right Disc Irritation", "E"),
    ("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Wilson, Caleb", "Out", "Injury/Illness - Right Metacarpal Fracture", "E"),
    ("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Diop, Khalifa", "Out", "G League - On Assignment", "E"),
    ("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Merrill, Sam", "Out", "Injury/Illness - Right Elbow Injury Management", "E"),
    ("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Mobley, Evan", "Out", "Injury/Illness - Left Great Toe - Sprain", "E"),
    ("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Tomlin, Nae'Qwan", "Out", "Injury/Illness - Low Back Stress Reaction", "E"),
    ("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Udeh, Jr., Ernest", "Out", "G League - Two-Way", "C"),
    ("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Antetokounmpo, Giannis", "Available", "Injury/Illness - Right Wrist Sprain", "E"),
    ("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Goldin, Vladislav", "Out", "G League - Two-Way", "E"),
    ("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Larsson, Pelle", "Doubtful", "Injury/Illness - Illness", "E"),
    ("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Thompson, Klay", "Probable", "Injury/Illness - Left Ankle Soreness", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Edey, Zach", "Out", "Injury/Illness - Left Ankle Injury Management", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Lopez, Karim", "Out", "G League - On Assignment", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Mashack, Jahmai", "Out", "G League - Two-Way", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Pippen Jr., Scotty", "Out", "Injury/Illness - Lumbar Disc Herniation", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Post, Quinten", "Out", "Injury/Illness - Concussion Protocol", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Saunders, Richie", "Out", "Injury/Illness - Right Knee Surgery", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Dia, Malik", "Available", "G League - Two-Way", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Mathurin, Bennedict", "Questionable", "Injury/Illness - Right Thumb Sprain", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "McGowens, Bryce", "Out", "Injury/Illness - Left Elbow Infection", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Missi, Yves", "Out", "Injury/Illness - Left Knee Contusion / Bone Bruise", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Murphy III, Trey", "Out", "Injury/Illness - Bilateral Patellar Tendinopathy", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Murray, Dejounte", "Out", "Injury/Illness - Left Ankle Sprain", "E"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Pierre Jr., Jaron", "Available", "G League - Two-Way", "C"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Watford, Trendon", "Out", "Injury/Illness - Right Ankle Sprain", "C"),
    ("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Alexander, Trey", "Out", "G League - Two-Way", "E"),
    ("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Bufkin, Kobe", "Out", "G League - Two-Way", "E"),
    ("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Ingram, Harrison", "Out", "G League - Two-Way", "E"),
    ("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Jackson Jr., Jaren", "Out", "Injury/Illness - Right MCL Tear", "E"),
    ("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Markkanen, Lauri", "Out", "Injury/Illness - Right Hand Fracture", "E"),
    ("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Nurkic, Jusuf", "Out", "Injury/Illness - Right 2nd Plantar Plate Tear", "E"),
    ("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Adams, Steven", "Out", "Injury/Illness - Right Soleus Strain", "E"),
    ("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Capela, Clint", "Out", "Injury/Illness - Right Ankle Sprain", "E"),
    ("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Copeland, Quadir", "Out", "G League - Two-Way", "E"),
    ("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Phillips, Julian", "Out", "G League - Two-Way", "E"),
    ("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Smart, Marcus", "Out", "League Suspension", "E"),
    ("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Bassey, Charles", "Probable", "Injury/Illness - Left Toe Soreness", "E"),
    ("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Butler III, Jimmy", "Out", "Injury/Illness - Right ACL Repair / Surgery", "E"),
    ("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Curry, Stephen", "Out", "Injury/Illness - Right Oblique Tear", "E"),
    ("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Moody, Moses", "Out", "Injury/Illness - Left Patellar Tendon Repair / Surgery", "E"),
    ("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Porzingis, Kristaps", "Out", "Not With Team", "E"),
    ("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Williams, Brandon", "Out", "Injury/Illness - Left Hamstring Strain", "C"),
    ("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Fox, De'Aaron", "Questionable", "Injury/Illness - Left Hip Soreness", "E"),
    ("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Harris, Tobias", "Out", "Injury/Illness - Left Calf Strain", "E"),
    ("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Quaintance, Jayden", "Out", "Injury/Illness - Right Knee Surgery", "E"),
    ("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Vassell, Devin", "Questionable", "Injury/Illness - Left Adductor Tightness", "E"),
    ("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Krejci, Vit", "Out", "Injury/Illness - Left Ankle Fracture", "E"),
    ("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Morant, Ja", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Sharpe, Shaedon", "Out", "Injury/Illness - Right Meniscus Surgery", "E"),
    ("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Youngblood, Chris", "Out", "Injury/Illness - Right Bone Bruise", "E"),
    ("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Achiuwa, Precious", "Out", "Injury/Illness - Left Ankle Soreness", "E"),
    ("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Karaban, Alex", "Out", "G League - On Assignment", "E"),
    ("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Mogbo, Jonathan", "Out", "G League - Two-Way", "E"),
    ("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Pedulla, Sean", "Out", "G League - Two-Way", "E"),
    ("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Raynaud, Maxime", "Out", "Injury/Illness - Right Patella Subluxation", "E"),
    ("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Simmons, Ben", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery", "E"),
    ("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Holmgren, Chet", "Out", "Injury/Illness - Right Knee/ Injury Recovery", "E"),
    ("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Beal, Bradley", "Out", "Injury/Illness - Right Knee Injury Management", "E"),
    ("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Ingram, Brandon", "Out", "Injury/Illness - Right Heel Surgery", "E"),
    ("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Martinelli, Nick", "Out", "G League - Two-Way", "E"),
    ("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Miller, Jordan", "Out", "Injury/Illness - Left Rotator Cuff Surgery", "E"),
    ("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Niederhauser, Yanic Konan", "Out", "Injury/Illness - Right Lisfranc Surgery", "E"),
]

# Rows the page printed as NOT YET SUBMITTED (10 team-rows for 11/14 games).
NOT_SUBMITTED = [
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets"),
    ("2026-11-14", "07:00", "DEN@NOP", "New Orleans Pelicans"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks"),
    ("2026-11-14", "07:30", "DAL@CLE", "Cleveland Cavaliers"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets"),
    ("2026-11-14", "08:00", "BKN@MEM", "Memphis Grizzlies"),
    ("2026-11-14", "08:00", "CHI@MIN", "Chicago Bulls"),
    ("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons"),
    ("2026-11-14", "08:00", "DET@MIA", "Miami Heat"),
]

# --------------------------------------------------------------------------- players
# nba.com/stats/players/traditional — season aggregates, read 2026-11-14. Only rows used.
# player, team, GP, MIN, PTS, REB, AST, nba_player_id
PLAYERS = [
    ("Luka Dončić", "LAL", 13, None, None, None, None, "1629029"),   # row present; values not transcribed
    ("Ty Jerome", "MEM", 10, 30.7, 26.2, 3.5, 4.9, "1629660"),
    ("Darius Acuff Jr.", "SAC", 11, 37.3, 26.2, 3.8, 7.3, "1643411"),
    ("Jalen Brunson", "NYK", 11, 33.6, 26.0, 3.1, 5.2, "1628973"),
    ("Anthony Davis", "WAS", 11, 34.1, 25.6, 10.5, 2.0, "203076"),
    ("Devin Booker", "PHX", 11, 34.0, 25.5, 2.5, 5.0, "1626164"),
    ("Cade Cunningham", "DET", 11, 34.5, 25.0, 5.2, 7.9, "1630595"),
    ("Austin Reaves", "LAL", 12, 35.3, 24.7, 3.3, 4.7, "1630559"),
    ("Cooper Flagg", "DAL", 11, 33.5, 24.6, 6.9, 6.5, "1642843"),
    ("Paolo Banchero", "ORL", 2, 33.8, 24.5, 6.5, 7.5, "1631094"),
    ("Nikola Jokić", "DEN", 10, 36.3, 23.5, 10.8, 9.0, "203999"),
    ("Scottie Barnes", "TOR", 8, 33.3, 23.5, 7.6, 5.1, "1630567"),
    ("Franz Wagner", "ORL", 11, 36.9, 23.5, 6.5, 7.9, "1630532"),
    ("Deni Avdija", "POR", 11, 32.5, 23.0, 6.1, 6.5, "1630166"),
    ("Donovan Mitchell", "CLE", 12, 33.0, 22.8, 5.0, 5.5, "1628378"),
    ("Pascal Siakam", "IND", 11, 32.1, 22.7, 6.9, 4.4, "1627783"),
    ("Jamal Murray", "DEN", 10, 36.4, 26.2, 5.0, 5.9, "1627750"),
    ("Stephen Curry", "GSW", None, None, 27.8, 3.7, 3.9, "201939"),      # season-leader widget
    ("Victor Wembanyama", "SAS", None, None, 30.3, 11.7, 2.8, "1641705"),  # season-leader widget
    ("Shai Gilgeous-Alexander", "OKC", None, None, 29.7, 4.3, 4.5, "1628983"),
    ("Alperen Sengun", "HOU", None, None, 21.1, 9.4, 7.9, "1630578"),
]

# Injury rows that name one of the players above (used for the impact table).
# Verified by matching the official report text against the official player table.
PLAYER_SOURCE = "https://www.nba.com/stats/players/traditional"


# --------------------------------------------------------------------------- checks
def integrity() -> dict:
    """Arithmetic identities that official league totals must satisfy.

    These are *derived checks*, not sources: if a transcription were wrong, one of these
    would break. Each one is reported on the site so a reviewer can re-run it.
    """
    gp = {t: v[0] + v[1] for t, v in TEAMS.items()}
    total_gp = sum(gp.values())
    weighted_pf = sum(v[6] * gp[t] for t, v in TEAMS.items())
    weighted_pa = sum(v[7] * gp[t] for t, v in TEAMS.items())
    league_pts_per_team_game = weighted_pf / total_gp
    hw = sum(v[2] for v in TEAMS.values())
    hl = sum(v[3] for v in TEAMS.values())
    rw = sum(v[4] for v in TEAMS.values())
    rl = sum(v[5] for v in TEAMS.values())
    wins = sum(v[0] for v in TEAMS.values())
    losses = sum(v[1] for v in TEAMS.values())
    return {
        "teams": len(TEAMS),
        "games_played_team_sum": total_gp,
        "games": total_gp / 2,
        "wins": wins,
        "losses": losses,
        "wins_equals_losses": wins == losses,
        "weighted_points_scored": round(weighted_pf, 1),
        "weighted_points_allowed": round(weighted_pa, 1),
        "weighted_points_diff": round(weighted_pf - weighted_pa, 1),
        # each team's PF/PA is rounded to 0.1, so the difference must be within
        # 0.05 * (games) summed over both sides = 0.1 * total_gp
        "rounding_bound": round(0.1 * total_gp, 1),
        "points_identity_ok": abs(weighted_pf - weighted_pa) <= 0.1 * total_gp,
        "home_w": hw, "home_l": hl, "road_w": rw, "road_l": rl,
        "home_wins_equal_road_losses": hw == rl,
        "home_losses_equal_road_wins": hl == rw,
        "home_win_rate": round(hw / (hw + hl), 4),
        "league_pts_per_team_game": round(league_pts_per_team_game, 3),
    }


def home_win_rate_se() -> float:
    """Standard error of the league home-win rate, from the games actually observed."""
    i = integrity()
    n = i["home_w"] + i["home_l"]
    return math.sqrt(0.25 / n)
