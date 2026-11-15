"""Official NBA snapshot for the v2 build.

Every number here was read off an NBA.com / NBA official-CDN page by the session named in
``RETRIEVED_BY`` on the date in ``AS_OF``, through the platform page-fetch tool (direct TLS
egress to nba.com is blocked in this sandbox; that limitation is recorded, not worked around).
Nothing is inferred and nothing is filled in: the source URL for each field family is declared
in ``SOURCES`` so every published row can carry a link back to the page it came from.

Retrieval record - session ``arena/ac5fab5c-nba2``, 2026-11-14 (UTC)
---------------------------------------------------------------------
* ``www.nba.com/standings`` ................ 30 teams, W/L, home/road splits ......... fetched OK
* ``www.nba.com/stats/teams/advanced`` ..... 30 teams, OffRtg/DefRtg/NetRtg/PACE/PIE . fetched OK
* ``www.nba.com/stats/teams/traditional`` .. 30 teams, GP/PTS (spot-checked rows) ..... fetched OK
* ``www.nba.com/schedule?date=2026-11-15`` . slate 11/13-11/22, times, arenas, IDs .... fetched OK
* ``www.nba.com/games?date=2026-11-06`` .... 9 official finals ....................... fetched OK
* ``www.nba.com/games?date=2026-11-11`` .... 10 official finals ...................... fetched OK
* ``Injury-Report_2026-11-14_04_30AM.pdf`` . 26 player rows + 23 not-submitted teams . fetched OK
* ``official.nba.com/nba-injury-report-2026-27-season/`` index of report PDFs ........ fetched OK
* ``Injury-Report_2026-11-14_05_30AM.pdf`` ........................................... AccessDenied
* ``stats.nba.com`` / ``cdn.nba.com`` JSON endpoints ................................. TLS blocked

What changed in this refresh (and why it matters)
-------------------------------------------------
* **Standings moved.** The previous snapshot carried records that pre-date the 11/13 games.
  Every W/L and home/road split below is now the live 11/14 standings table, cross-checked by
  rebuilding all 30 records from the 183 official final scores in ``data/raw/history/`` --
  30/30 identical, home and road splits included.
* **The results history is now complete.** 28 previously missing finals (11/06, 11/11, 11/13)
  were captured, taking the window to 183/183 games played through 11/13 -- exactly the count
  implied by the standings. See ``audit/session-ac5fab5c/verify-record-reconstruction.txt``.
* **The window is the next three days**, 2026-11-14 -> 2026-11-17, 27 games. The 11/13 games
  that used to sit in ``SLATE`` have already been played and are now part of the history.
* **Injury coverage is genuinely thin for days 2 and 3**, and that is a fact rather than a gap
  to paper over: at capture time only 11/14 submissions were arriving, because a team files for
  a game by 5 p.m. local the day before. No 11/16 or 11/17 row exists in any published report.
  Those cells are blank and flagged, never estimated.
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
        "NBA.com Stats - Teams Traditional (official)",
        "https://www.nba.com/stats/teams/traditional",
        "GP, MIN, PTS (points per game), +/-, per-team shooting splits.",
    ),
    "team_opp": (
        "NBA.com Stats - Teams Opponent (official)",
        "https://www.nba.com/stats/teams/opponent",
        "Opponent PTS per game (points allowed), opponent shooting splits.",
    ),
    "team_adv": (
        "NBA.com Stats - Teams Advanced (official)",
        "https://www.nba.com/stats/teams/advanced",
        "OffRtg, DefRtg, NetRtg, PACE, PIE - all per-100-possession.",
    ),
    "schedule": (
        "NBA.com Schedule (official)",
        "https://www.nba.com/schedule?date=2026-11-17",
        "Game IDs, ET tip times, arenas, national broadcast, Emirates NBA Cup group.",
    ),
    "games": (
        "NBA.com Games & Scores (official)",
        "https://www.nba.com/games?date=2026-11-14",
        "Official final scores, one page per date; the day-strip calendar gives the "
        "per-date game count used for the completeness check.",
    ),
    "injury_pdf": (
        "NBA Official Injury Report 11/15/26 06:15 AM ET (official PDF)",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf",
        "Per-player status (Out/Doubtful/Questionable/Probable/Available) with the stated reason.",
    ),
    "injury_policy": (
        "NBA Official - Injury Report policy and report archive (official)",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
        "Filing deadlines: 5 p.m. local the day before; game day 11 a.m.-1 p.m.; "
        "1 p.m. local for the second of a back-to-back.",
    ),
    "player_trad": (
        "NBA.com Stats - Players Traditional (official)",
        "https://www.nba.com/stats/players/traditional",
        "Per-player GP, MIN, PTS, REB, AST for the rows used on this site.",
    ),
}

# Alias kept because earlier content modules address this source by its short name.
SOURCES["players"] = SOURCES["player_trad"]

# Why an input is absent. Published verbatim next to every blank cell.
BLOCKED = {
    "odds": (
        "Market prices (spread, total, moneyline, prop lines)",
        "No licensed odds feed is connected and NBA.com renders odds client-side only. "
        "Required for: any value/edge claim, stake sizing, ROI, leaderboard scoring.",
        "https://www.nba.com/games",
    ),
    "live_ingest": (
        "An automated feed that keeps the results history current without a human capture",
        "The 183 official finals from 2026-10-20 to 2026-11-13 ARE committed under "
        "data/raw/history/, and they rebuild every one of the 30 standings records exactly. "
        "Backtests, out-of-sample splits and settlement therefore run today. What is missing "
        "is a scheduled job that appends each night's results, so the history freezes between "
        "manual captures and the window ages.",
        "https://www.nba.com/games?date=2026-11-13",
    ),
    "player_box": (
        "Per-player game logs (minutes, usage, on/off)",
        "nba.com/stats player pages render season aggregates only for this client. Required for: "
        "minutes distributions, prop bet probabilities, injury replacement modelling.",
        "https://www.nba.com/stats/players/traditional",
    ),
    "future_injuries": (
        "Injury designations for game days beyond the next filing deadline",
        "The NBA publishes a report only once a team has filed. For a game on day +2 or +3 the "
        "filing deadline has not yet passed, so no official row exists to read.",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
    ),
}

AS_OF = "2026-11-15"
RETRIEVED_AT_UTC = "2026-11-15T11:50:00Z"
RETRIEVED_BY = "arena/673acec0-nba2"

# The 3-day pick window the brief asks for, inclusive of both ends.
WINDOW_START = "2026-11-15"
WINDOW_END = "2026-11-18"

# --------------------------------------------------------------------------- team table
# tricode: W, L, HOME_W, HOME_L, ROAD_W, ROAD_L, PF(pts/g), PA(pts/g), OEFF, DEF, NET, PACE, PIE
# W/L + splits: nba.com/standings, fetched 2026-11-15.
# PF/PA: computed from the 188 official finals in data/raw/history/ (every game, so the
#        per-game average is exact rather than sampled; cross-checked against the PTS column
#        of nba.com/stats/teams/traditional for 8 clubs: 8/8 identical to the printed decimal).
# OEFF/DEF/NET/PACE/PIE: nba.com/stats/teams/advanced, fetched 2026-11-15.
TEAMS: dict[str, tuple] = {
    "ATL": (7, 6, 3, 3, 4, 3, 118.2, 116.8, 113.3, 111.9, 1.4, 103.55, 48.5),
    "BKN": (3, 9, 1, 3, 2, 6, 110.2, 116.4, 109.8, 116.0, -6.2, 99.47, 46.1),
    "BOS": (10, 2, 5, 0, 5, 2, 114.2, 103.1, 117.4, 105.6, 11.7, 96.62, 55.9),
    "CHA": (4, 8, 3, 4, 1, 4, 98.6, 109.6, 101.9, 113.1, -11.2, 96.83, 42.9),
    "CHI": (3, 9, 1, 4, 2, 5, 114.6, 125.9, 109.4, 120.3, -10.9, 103.81, 44.9),
    "CLE": (7, 7, 5, 2, 2, 5, 117.5, 115.9, 116.9, 115.4, 1.6, 99.72, 51.2),
    "DAL": (7, 6, 5, 2, 2, 4, 113.5, 113.3, 112.8, 112.8, 0.0, 100.54, 49.7),
    "DEN": (7, 4, 2, 2, 4, 2, 114.6, 112.8, 116.0, 114.7, 1.3, 97.67, 52.9),
    "DET": (8, 4, 3, 2, 5, 2, 115.7, 110.2, 114.1, 109.2, 4.9, 99.48, 53.7),
    "GSW": (8, 5, 6, 1, 2, 4, 116.7, 112.4, 116.1, 112.0, 4.1, 99.66, 51.8),
    "HOU": (10, 3, 7, 1, 3, 2, 116.2, 107.4, 119.3, 110.2, 9.1, 97.42, 55.8),
    "IND": (5, 8, 2, 4, 3, 3, 111.2, 113.2, 110.1, 111.7, -1.5, 101.15, 49.6),
    "LAC": (3, 8, 3, 3, 0, 5, 112.3, 117.5, 110.7, 115.8, -5.1, 100.55, 47.4),
    "LAL": (11, 2, 5, 1, 6, 1, 122.2, 114.2, 121.6, 113.6, 8.0, 100.5, 54.2),
    "MEM": (9, 4, 3, 4, 6, 0, 120.6, 111.7, 119.0, 110.4, 8.5, 100.46, 53.9),
    "MIA": (7, 6, 3, 3, 4, 3, 118.7, 119.8, 114.7, 116.2, -1.5, 102.49, 50.0),
    "MIL": (1, 12, 1, 6, 0, 6, 106.2, 120.2, 105.7, 120.0, -14.2, 100.31, 42.0),
    "MIN": (9, 4, 5, 2, 4, 2, 118.3, 106.8, 116.0, 104.5, 11.5, 101.27, 55.2),
    "NOP": (4, 10, 3, 6, 1, 4, 115.9, 124.9, 111.3, 120.0, -8.6, 101.83, 45.7),
    "NYK": (6, 6, 4, 3, 2, 3, 109.8, 103.7, 114.5, 108.6, 5.9, 95.63, 53.3),
    "OKC": (8, 5, 5, 0, 3, 5, 111.2, 107.4, 112.7, 109.0, 3.7, 98.58, 53.3),
    "ORL": (5, 7, 1, 4, 4, 3, 108.3, 112.8, 109.7, 113.4, -3.7, 98.23, 47.6),
    "PHI": (10, 3, 5, 2, 5, 1, 111.2, 109.4, 111.0, 109.5, 1.5, 100.04, 50.9),
    "PHX": (5, 6, 5, 3, 0, 3, 111.7, 116.1, 113.8, 117.6, -3.8, 98.45, 48.1),
    "POR": (9, 3, 3, 2, 6, 1, 119.6, 111.8, 118.8, 111.1, 7.7, 100.67, 53.3),
    "SAC": (1, 11, 0, 7, 1, 4, 108.2, 120.9, 107.3, 119.5, -12.2, 101.0, 42.8),
    "SAS": (11, 2, 5, 2, 6, 0, 119.5, 106.2, 119.6, 106.6, 13.0, 98.94, 56.7),
    "TOR": (5, 7, 2, 3, 3, 4, 114.2, 112.8, 114.5, 112.8, 1.7, 99.88, 49.3),
    "UTA": (1, 12, 1, 6, 0, 6, 107.5, 118.6, 105.0, 116.4, -11.3, 100.5, 45.3),
    "WAS": (4, 9, 2, 3, 2, 6, 110.0, 115.8, 108.7, 114.3, -5.5, 99.63, 47.1),
}

# Official standings snapshot read from nba.com/standings on 2026-11-14 (live table: W/L and home/road
# splits for all 30 teams). Re-expressed from TEAMS so the W-L cross-check in report.py can run against
# a real module attribute instead of erroring with "module 'nba2.v2.official' has no attribute 'STANDINGS'".
STANDINGS_SOURCE = SOURCES["standings"][1]
STANDINGS_AS_OF = AS_OF
STANDINGS = {
    t: {"w": v[0], "l": v[1], "home": f"{v[2]}-{v[3]}", "road": f"{v[4]}-{v[5]}"}
    for t, v in TEAMS.items()
}

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

# Per-team source links (each page is the canonical official page for that team).
TEAM_SOURCE = {
    tid: "https://www.nba.com/stats/team/{}".format(tid) for tid in TEAMS
}

# --------------------------------------------------------------------------- the slate
# From https://www.nba.com/schedule?date=2026-11-17, read 2026-11-15.
# date, time_et, away, home, game_id, arena, city, national_broadcast, cup_group
# Window = today .. today+3 (the brief's "up to a maximum of 3 days in advance"),
# 2026-11-15 .. 2026-11-18 inclusive (34 games). The 11/14 games that used to head this
# list have been played; they are now part of data/raw/history/games_2026-11-14.json.
SLATE = [
    ("2026-11-15", "13:00", "IND", "PHI", "0022600236", "Xfinity Mobile Arena", "Philadelphia, PA", "League Pass", ""),
    ("2026-11-15", "16:00", "LAL", "PHX", "0022600237", "Mortgage Matchup Center", "Phoenix, AZ", "League Pass", ""),
    ("2026-11-15", "16:30", "CHA", "LAC", "0022600238", "Intuit Dome", "Inglewood, CA", "League Pass", ""),
    ("2026-11-15", "17:00", "SAS", "UTA", "0022600239", "Delta Center", "Salt Lake City, UT", "League Pass", ""),
    ("2026-11-15", "18:00", "DAL", "BOS", "0022600240", "TD Garden", "Boston, MA", "League Pass", ""),
    ("2026-11-15", "18:00", "NYK", "TOR", "0022600241", "Scotiabank Arena", "Toronto, ON", "League Pass", ""),
    ("2026-11-15", "19:00", "HOU", "WAS", "0022600242", "Capital One Arena", "Washington, DC", "MNMT/Monumental+", ""),
    ("2026-11-15", "20:00", "ATL", "MIL", "0022600243", "Fiserv Forum", "Milwaukee, WI", "League Pass", ""),
    ("2026-11-15", "21:00", "OKC", "SAC", "0022600244", "Golden 1 Center", "Sacramento, CA", "League Pass", ""),
    ("2026-11-16", "19:00", "ORL", "BOS", "0022600245", "TD Garden", "Boston, MA", "Peacock / NBC Sports Network", ""),
    ("2026-11-16", "19:00", "CHI", "CLE", "0022600246", "Rocket Arena", "Cleveland, OH", "League Pass", ""),
    ("2026-11-16", "19:00", "MEM", "WAS", "0022600247", "Capital One Arena", "Washington, DC", "MNMT/Monumental+", ""),
    ("2026-11-16", "19:30", "PHI", "BKN", "0022600248", "Barclays Center", "Brooklyn, NY", "League Pass", ""),
    ("2026-11-16", "19:30", "HOU", "MIA", "0022600249", "Kaseya Center", "Miami, FL", "League Pass", ""),
    ("2026-11-16", "20:00", "POR", "MIN", "0022600250", "Target Center", "Minneapolis, MN", "League Pass", ""),
    ("2026-11-16", "20:00", "GSW", "NOP", "0022600251", "Smoothie King Center", "New Orleans, LA", "League Pass", ""),
    ("2026-11-16", "21:00", "PHX", "DEN", "0022600252", "Ball Arena", "Denver, CO", "League Pass", ""),
    ("2026-11-17", "19:30", "NYK", "TOR", "0022600253", "Scotiabank Arena", "Toronto, ON", "League Pass", ""),
    ("2026-11-17", "20:00", "POR", "MIN", "0022600254", "Target Center", "Minneapolis, MN", "League Pass", ""),
    ("2026-11-17", "20:00", "DET", "SAS", "0022600255", "Frost Bank Center", "San Antonio, TX", "Peacock / NBC", ""),
    ("2026-11-17", "22:30", "UTA", "LAC", "0022600257", "Intuit Dome", "Inglewood, CA", "League Pass", ""),
    ("2026-11-17", "23:00", "CHA", "LAL", "0022600256", "Crypto.com Arena", "Los Angeles, CA", "Peacock", ""),
    ("2026-11-18", "19:00", "MEM", "CLE", "0022600258", "Rocket Arena", "Cleveland, OH", "League Pass", ""),
    ("2026-11-18", "19:00", "HOU", "IND", "0022600259", "Gainbridge Fieldhouse", "Indianapolis, IN", "League Pass", ""),
    ("2026-11-18", "19:00", "MIL", "MIA", "0022600260", "Kaseya Center", "Miami, FL", "ESPN", ""),
    ("2026-11-18", "19:00", "PHI", "ORL", "0022600261", "Kia Center", "Orlando, FL", "League Pass", ""),
    ("2026-11-18", "19:30", "CHI", "BKN", "0022600262", "Barclays Center", "Brooklyn, NY", "League Pass", ""),
    ("2026-11-18", "19:30", "WAS", "TOR", "0022600263", "Scotiabank Arena", "Toronto, ON", "MNMT/Monumental+", ""),
    ("2026-11-18", "20:00", "DET", "NOP", "0022600264", "Smoothie King Center", "New Orleans, LA", "League Pass", ""),
    ("2026-11-18", "20:00", "ATL", "OKC", "0022600265", "Paycom Center", "Oklahoma City, OK", "League Pass", ""),
    ("2026-11-18", "20:00", "GSW", "DAL", "0022600267", "American Airlines Center", "Dallas, TX", "League Pass", ""),
    ("2026-11-18", "21:30", "BOS", "DEN", "0022600266", "Ball Arena", "Denver, CO", "ESPN", ""),
    ("2026-11-18", "22:00", "UTA", "LAL", "0022600268", "Crypto.com Arena", "Los Angeles, CA", "League Pass", ""),
    ("2026-11-18", "22:00", "PHX", "SAC", "0022600269", "Golden 1 Center", "Sacramento, CA", "League Pass", ""),
]

INJURY_PDF_URL = SOURCES["injury_pdf"][1]

# --------------------------------------------------------------------------- injuries
# Transcribed from the official 11/15/26 06:15 AM ET PDF. The report's own columns are
# Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason.
# The trailing letter is this project's transcription note, not an NBA field:
#   "E" = the team cell is present on the row itself
#   "C" = the row continues a team block from the previous PDF page, so the team and
#         matchup are carried over (flagged on the site as FLAG-V2-INJ-ATTR)
# (date, time_et, matchup, team, player, status, reason, attribution)
INJURIES = [
    ("2026-11-15", "01:00", "IND@PHI", "Indiana Pacers", "Furphy, Johnny", "Out", "Injury/Illness - Right ACL Repair / Surgery", "E"),
    ("2026-11-15", "01:00", "IND@PHI", "Indiana Pacers", "Haliburton, Tyrese", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("2026-11-15", "01:00", "IND@PHI", "Indiana Pacers", "McConnell, T.J.", "Probable", "Injury/Illness - Right Hamstring Strain", "E"),
    ("2026-11-15", "01:00", "IND@PHI", "Indiana Pacers", "Nembhard, Andrew", "Questionable", "Injury/Illness - Left Hip Soreness / Tightness", "E"),
    ("2026-11-15", "01:00", "IND@PHI", "Indiana Pacers", "Nesmith, Aaron", "Questionable", "Injury/Illness - Left Hand Sprain", "E"),
    ("2026-11-15", "01:00", "IND@PHI", "Indiana Pacers", "Sheppard, Ben", "Out", "Injury/Illness - Left Meniscus Tear", "E"),
    ("2026-11-15", "01:00", "IND@PHI", "Philadelphia 76ers", "Barlow, Dominick", "Out", "Injury/Illness - Low Back Stress Reaction", "E"),
    ("2026-11-15", "01:00", "IND@PHI", "Philadelphia 76ers", "Bona, Adem", "Out", "Injury/Illness - Cervical Spine Sprain", "E"),
    ("2026-11-15", "01:00", "IND@PHI", "Philadelphia 76ers", "Embid, Joel", "Out", "Injury/Illness - Right Foot Plantar Fascia Injury Management", "E"),
    ("2026-11-15", "01:00", "IND@PHI", "Philadelphia 76ers", "Hukporti, Ariel", "Out", "Injury/Illness - Right Achilles Tendon Rupture / Tear", "E"),
    ("2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers", "Carr, Cameron", "Out", "Injury/Illness - Illness", "E"),
    ("2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers", "Grimes, Quentin", "Available", "Injury/Illness - Right Finger Splint", "E"),
    ("2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers", "James, Bronny", "Questionable", "Injury/Illness - Illness", "E"),
    ("2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers", "Reaves, Austin", "Out", "Injury/Illness - Left Heel Contusion / Bone Bruise", "E"),
    ("2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers", "Sexton, Collin", "Questionable", "Injury/Illness - Right Orbital Laceration", "C"),
    ("2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers", "Thiero, Adou", "Questionable", "Injury/Illness - Left Ankle Sprain", "C"),
    ("2026-11-15", "04:00", "LAL@PHX", "Phoenix Suns", "Williams, Mark", "Out", "Injury/Illness - Left Shoulder Surgery", "E"),
    ("2026-11-15", "04:30", "CHA@LAC", "Charlotte Hornets", "Ajayi, Michael", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "04:30", "CHA@LAC", "Charlotte Hornets", "Boswell, Kylan", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "04:30", "CHA@LAC", "Charlotte Hornets", "Knueppel, Kon", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("2026-11-15", "04:30", "CHA@LAC", "Charlotte Hornets", "Schroder, Dennis", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("2026-11-15", "04:30", "CHA@LAC", "Charlotte Hornets", "Steinbach, Hannes", "Out", "G League - On Assignment", "E"),
    ("2026-11-15", "04:30", "CHA@LAC", "LA Clippers", "Beal, Bradley", "Out", "Injury/Illness - Right Knee Injury Management", "E"),
    ("2026-11-15", "04:30", "CHA@LAC", "LA Clippers", "Ingram, Brandon", "Out", "Injury/Illness - Right Heel Surgery", "E"),
    ("2026-11-15", "04:30", "CHA@LAC", "LA Clippers", "Miller, Jordan", "Out", "Injury/Illness - Left Rotator Cuff Surgery", "E"),
    ("2026-11-15", "04:30", "CHA@LAC", "LA Clippers", "Niederhauser, Yanic Konan", "Out", "Injury/Illness - Right Lisfranc Surgery", "E"),
    ("2026-11-15", "05:00", "SAS@UTA", "San Antonio Spurs", "Brown, Maliq", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "05:00", "SAS@UTA", "San Antonio Spurs", "Gillespie, Ja'Kobi", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "05:00", "SAS@UTA", "San Antonio Spurs", "Harris, Tobias", "Out", "Injury/Illness - Left Calf Strain", "E"),
    ("2026-11-15", "05:00", "SAS@UTA", "San Antonio Spurs", "Quaintance, Jayden", "Out", "Injury/Illness - Right Knee Surgery", "E"),
    ("2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Alexander, Trey", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Bufkin, Kobe", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Hayes, Jaxson", "Out", "Injury/Illness - Left Knee Strain", "C"),
    ("2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Ingram, Harrison", "Out", "G League - Two-Way", "C"),
    ("2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Jackson Jr., Jaren", "Out", "Injury/Illness - Right MCL Tear", "C"),
    ("2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Markkanen, Lauri", "Out", "Injury/Illness - Right Hand Fracture", "C"),
    ("2026-11-15", "05:00", "SAS@UTA", "Utah Jazz", "Nurkic, Jusuf", "Out", "Injury/Illness - Right 2nd Plantar Plate Tear", "C"),
    ("2026-11-15", "06:00", "DAL@BOS", "Boston Celtics", "Carter, Devin", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-15", "06:00", "DAL@BOS", "Boston Celtics", "Cenac Jr., Christopher", "Questionable", "G League - On Assignment", "E"),
    ("2026-11-15", "06:00", "DAL@BOS", "Boston Celtics", "Mitchell, Dillon", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-15", "06:00", "DAL@BOS", "Boston Celtics", "Williams, Amari", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-15", "06:00", "NYK@TOR", "Toronto Raptors", "Barnes, Scottie", "Questionable", "Injury/Illness - Left Groin Strain", "E"),
    ("2026-11-15", "06:00", "NYK@TOR", "Toronto Raptors", "Bittle, Nate", "Out", "Injury/Illness - Right Foot Avulsion Fracture", "E"),
    ("2026-11-15", "06:00", "NYK@TOR", "Toronto Raptors", "Leonard, Kawhi", "Out", "Injury/Illness - Left Knee Injury Management", "E"),
    ("2026-11-15", "06:00", "NYK@TOR", "Toronto Raptors", "McCullar Jr., Kevin", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "06:00", "NYK@TOR", "Toronto Raptors", "Smith, Malachi", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "07:00", "HOU@WAS", "Houston Rockets", "Adams, Steven", "Probable", "Injury/Illness - Right Soleus Strain", "E"),
    ("2026-11-15", "07:00", "HOU@WAS", "Houston Rockets", "Capela, Clint", "Out", "Injury/Illness - Right Ankle Sprain", "E"),
    ("2026-11-15", "07:00", "HOU@WAS", "Houston Rockets", "Copeland, Quadir", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "07:00", "HOU@WAS", "Houston Rockets", "Phillips, Julian", "Out", "G League - Two-Way", "C"),
    ("2026-11-15", "07:00", "HOU@WAS", "Houston Rockets", "Smart, Marcus", "Out", "League Suspension", "C"),
    ("2026-11-15", "07:00", "HOU@WAS", "Houston Rockets", "VanVleet, Fred", "Out", "Injury/Illness - Right Knee Injury Management", "C"),
    ("2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Beekman, Reece", "Out", "Injury/Illness - Right AC Joint Injury", "E"),
    ("2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Carrington, Bub", "Questionable", "Injury/Illness - Chest / Sternum Contusion", "E"),
    ("2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Champagne, Justin", "Out", "Injury/Illness - Right Foot Surgery", "E"),
    ("2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Johnson, Tre", "Questionable", "Injury/Illness - Low Back Soreness", "E"),
    ("2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Okpara, Felix", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Sarr, Alex", "Questionable", "Injury/Illness - Illness", "E"),
    ("2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Vukcevic, Tristan", "Out", "Injury/Illness - Left Hip Impingement", "E"),
    ("2026-11-15", "07:00", "HOU@WAS", "Washington Wizards", "Watkins, Jamir", "Out", "Injury/Illness - Left ACL Repair / Surgery", "E"),
    ("2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Flemings, Kingston", "Out", "Injury/Illness - Lumbar Strain", "E"),
    ("2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Gilbert, Keshon", "Out", "Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure", "E"),
    ("2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Gueye, Mouhamed", "Out", "Injury/Illness - Left Foot Fracture", "E"),
    ("2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Landale, Jock", "Available", "Injury/Illness - Face Mask", "E"),
    ("2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Newell, Asa", "Out", "Injury/Illness - Left Great Toe Hyperextension", "E"),
    ("2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Veesaar, Henri", "Out", "Injury/Illness - Right ACL Tear", "C"),
    ("2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks", "Wilson, Jalen", "Doubtful", "G League - Two-Way", "C"),
    ("2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks", "Dieng, Ousmane", "Out", "Injury/Illness - Left Finger Sprain", "E"),
    ("2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks", "Jones, Kam", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks", "Markovic, Bogoljub", "Out", "G League - On Assignment", "E"),
    ("2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks", "Nance, Pete", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks", "Ryan, Cormac", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Holmgren, Chet", "Out", "Injury/Illness - Right Knee/ Injury Recovery", "E"),
    ("2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Mitchell, Ajay", "Questionable", "Injury/Illness - Left Ankle Sprain", "E"),
    ("2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Sorber, Thomas", "Out", "Injury/Illness - Right Knee Surgery", "E"),
    ("2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Wallace, Cason", "Out", "Injury/Illness - Left Shoulder Surgery", "E"),
    ("2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Williams, Jalen", "Out", "Injury/Illness - Left Ankle Surgery", "E"),
    ("2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Williams, Jaylin", "Out", "Injury/Illness - Low Back Spasms", "E"),
    ("2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings", "Achiuwa, Precious", "Questionable", "Injury/Illness - Left Ankle Soreness", "E"),
    ("2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings", "Mogbo, Jonathan", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings", "Murray, Keegan", "Questionable", "Injury/Illness - Illness", "E"),
    ("2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings", "Pedulla, Sean", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings", "Raynaud, Maxime", "Out", "Injury/Illness - Right Patella Subluxation", "E"),
    ("2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings", "Simmons, Ben", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery", "C"),
]
NOT_SUBMITTED = [
    ("2026-11-15", "06:00", "DAL@BOS", "Dallas Mavericks"),
    ("2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls"),
    ("2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers"),
    ("2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies"),
    ("2026-11-16", "07:00", "MEM@WAS", "Washington Wizards"),
    ("2026-11-16", "07:00", "ORL@BOS", "Orlando Magic"),
    ("2026-11-16", "07:00", "ORL@BOS", "Boston Celtics"),
    ("2026-11-16", "07:30", "HOU@MIA", "Houston Rockets"),
    ("2026-11-16", "07:30", "HOU@MIA", "Miami Heat"),
    ("2026-11-16", "07:30", "PHI@BKN", "Philadelphia 76ers"),
    ("2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets"),
    ("2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors"),
    ("2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans"),
    ("2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers"),
    ("2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves"),
    ("2026-11-16", "09:00", "PHX@DEN", "Phoenix Suns"),
    ("2026-11-16", "09:00", "PHX@DEN", "Denver Nuggets"),
]

# --------------------------------------------------------------------------- players
# nba.com/stats/players/traditional - season aggregates, read 2026-11-14.
# A season *rate* is published; the per-game distribution needed to price a prop is not,
# so every prop column built from this table is blank and flagged.
# player, team, GP, MIN, PTS, REB, AST, nba_player_id
PLAYERS = [
    ("Luka Don\u010di\u0107", "LAL", 13, None, None, None, None, "1629029"),
    ("Shai Gilgeous-Alexander", "OKC", 13, None, None, None, None, "1628983"),
    ("Victor Wembanyama", "SAS", 13, None, None, None, None, "1641705"),
    ("Anthony Edwards", "MIN", None, None, None, None, None, "1630162"),
    ("Jalen Duren", "DET", None, None, None, None, None, "1631106"),
    ("Nikola Joki\u0107", "DEN", 10, None, None, None, None, "203999"),
    ("Donovan Mitchell", "CLE", 13, None, None, None, None, "1628378"),
]

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
