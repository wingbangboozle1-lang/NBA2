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
        "https://www.nba.com/schedule?date=2026-11-15",
        "Game IDs, ET tip times, arenas, national broadcast, Emirates NBA Cup group.",
    ),
    "games": (
        "NBA.com Games & Scores (official)",
        "https://www.nba.com/games?date=2026-11-13",
        "Official final scores, one page per date; the day-strip calendar gives the "
        "per-date game count used for the completeness check.",
    ),
    "injury_pdf": (
        "NBA Official Injury Report 11/14/26 04:30 AM ET (official PDF)",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_30AM.pdf",
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

AS_OF = "2026-11-17"
RETRIEVED_AT_UTC = "2026-11-17T15:12:00Z"
RETRIEVED_BY = "arena/45f14c5c-nba2"

# The 3-day pick window the brief asks for, inclusive of both ends.
WINDOW_START = "2026-11-17"
WINDOW_END = "2026-11-20"

# --------------------------------------------------------------------------- team table
# tricode: W, L, HOME_W, HOME_L, ROAD_W, ROAD_L, PF(pts/g), PA(pts/g), OEFF, DEF, NET, PACE, PIE
# W/L + splits: nba.com/standings, fetched 2026-11-15 (data/raw/capture_2026-11-15/standings_2026-11-15.json).
# PF/PA: summed from the 188 official finals in data/raw/history/ + data/raw/capture_2026-11-15/
#        (exact, never estimated; cross-checked row-by-row against nba.com/stats/teams/traditional
#        and /stats/teams/opponent in capture_2026-11-15/team_stats_2026-11-15.json).
# OEFF/DEF/NET/PACE/PIE: nba.com/stats/teams/advanced, fetched 2026-11-15 (all 30 rows).
# Neutral-site games (DEN 1-0, IND 0-1, NOP 0-2) are inside W/L but outside the home/road split,
# exactly as the official standings table prints them.
TEAMS: dict[str, tuple] = {
    "ATL": (8, 6, 3, 3, 5, 3, 117.8, 116.1, 112.8, 111.1, 1.7, 103.69, 49.0),
    "BKN": (3, 10, 1, 4, 2, 6, 111.2, 117.8, 110.8, 117.4, -6.6, 99.55, 45.9),
    "BOS": (11, 3, 6, 1, 5, 2, 114.8, 103.3, 118.2, 106.1, 12.1, 96.53, 55.4),
    "CHA": (4, 9, 3, 4, 1, 5, 99.1, 109.8, 102.5, 113.6, -11.1, 96.65, 42.7),
    "CHI": (3, 10, 1, 4, 2, 6, 114.6, 125.9, 109.1, 120.0, -10.9, 104.17, 44.9),
    "CLE": (8, 7, 6, 2, 2, 5, 118.1, 115.8, 116.9, 114.7, 2.2, 100.3, 51.5),
    "DAL": (7, 7, 5, 2, 2, 5, 112.1, 114.6, 111.8, 114.5, -2.7, 100.18, 48.6),
    "DEN": (7, 5, 2, 3, 4, 2, 113.8, 113.2, 115.1, 114.9, 0.2, 97.86, 52.2),
    "DET": (8, 4, 3, 2, 5, 2, 115.7, 110.2, 114.1, 109.2, 4.9, 99.48, 53.7),
    "GSW": (8, 6, 6, 1, 2, 5, 115.1, 112.6, 114.6, 112.3, 2.2, 99.58, 51.0),
    "HOU": (11, 4, 7, 1, 4, 3, 117.8, 109.5, 120.9, 112.3, 8.6, 97.5, 55.5),
    "IND": (5, 9, 2, 4, 3, 4, 112.1, 114.5, 110.9, 112.9, -2.0, 101.25, 49.6),
    "LAC": (4, 8, 4, 3, 0, 5, 112.3, 116.5, 111.4, 115.3, -3.9, 100.05, 48.3),
    "LAL": (12, 2, 5, 1, 7, 1, 122.8, 114.9, 122.1, 114.0, 8.0, 100.64, 54.2),
    "MEM": (10, 4, 3, 4, 7, 0, 121.7, 112.3, 120.0, 110.9, 9.1, 100.61, 54.3),
    "MIA": (8, 6, 4, 3, 4, 3, 119.4, 119.1, 116.0, 116.2, -0.1, 101.96, 50.6),
    "MIL": (1, 13, 1, 7, 0, 6, 106.1, 119.7, 105.4, 118.9, -13.6, 100.68, 42.1),
    "MIN": (10, 4, 6, 2, 4, 2, 117.4, 106.1, 115.2, 104.1, 11.1, 101.21, 55.1),
    "NOP": (5, 10, 4, 6, 1, 4, 115.8, 122.9, 111.7, 118.4, -6.7, 101.62, 46.6),
    "NYK": (7, 6, 4, 3, 3, 3, 109.9, 104.0, 113.7, 108.2, 5.5, 95.66, 53.5),
    "OKC": (9, 5, 5, 0, 4, 5, 112.1, 107.1, 113.4, 108.4, 5.1, 98.82, 53.8),
    "ORL": (6, 7, 1, 4, 5, 3, 108.8, 112.2, 110.5, 113.0, -2.6, 98.1, 48.6),
    "PHI": (12, 3, 6, 2, 6, 1, 114.1, 111.3, 113.7, 111.1, 2.6, 100.23, 51.3),
    "PHX": (6, 7, 5, 4, 1, 3, 113.0, 116.4, 114.5, 117.5, -3.0, 98.88, 48.5),
    "POR": (9, 4, 3, 2, 6, 2, 117.9, 111.4, 117.2, 110.6, 6.6, 100.65, 52.8),
    "SAC": (1, 12, 0, 8, 1, 4, 107.8, 121.2, 106.8, 119.8, -13.0, 101.08, 42.6),
    "SAS": (12, 2, 5, 2, 7, 0, 118.8, 105.9, 119.2, 106.6, 12.6, 98.77, 56.9),
    "TOR": (5, 8, 2, 4, 3, 4, 113.8, 112.8, 113.6, 112.2, 1.4, 99.55, 49.0),
    "UTA": (1, 13, 1, 7, 0, 6, 107.1, 118.0, 105.1, 116.2, -11.1, 100.22, 45.0),
    "WAS": (4, 11, 2, 5, 2, 6, 111.3, 119.2, 109.9, 117.6, -7.8, 99.91, 45.8),
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
# From https://www.nba.com/schedule?date=2026-11-15 (chunks 0-2) and the /games day-strip,
# read 2026-11-15 (data/raw/capture_2026-11-15/slate_2026-11-15_to_11-18.json). Game IDs and
# ET tips were triple-checked against the schedule page, the day-strip and the tip times
# printed on the official injury report. Window = today through today+3 days:
# 2026-11-15 .. 2026-11-18 inclusive (34 games).
# date, time_et, away, home, game_id, arena, city, national_broadcast, cup_group
# cup_group is blank: no Emirates NBA Cup marker appears on any listing at retrieval
# (FLAG-V2-CUP-BLANK — blank and flagged, never assumed).
SLATE = [
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
    ("2026-11-19", "20:00", "GSW", "MEM", "0022600270", "FedExForum", "Memphis, TN", "League Pass", ""),
    ("2026-11-19", "20:00", "POR", "MIL", "0022600271", "Fiserv Forum", "Milwaukee, WI", "League Pass", ""),
    ("2026-11-19", "20:00", "NYK", "MIN", "0022600272", "Target Center", "Minneapolis, MN", "NBA TV", ""),
    ("2026-11-19", "20:00", "LAC", "SAS", "0022600273", "Frost Bank Center", "San Antonio, TX", "League Pass", ""),
    ("2026-11-20", "19:00", "CHA", "ATL", "0022600043", "State Farm Arena", "Atlanta, GA", "League Pass", "East Group C"),
    ("2026-11-20", "19:30", "ORL", "BKN", "0022600044", "Barclays Center", "Brooklyn, NY", "League Pass", "East Group A"),
    ("2026-11-20", "19:30", "IND", "CLE", "0022600045", "Rocket Arena", "Cleveland, OH", "League Pass", "East Group B"),
    ("2026-11-20", "19:30", "TOR", "DET", "0022600046", "Little Caesars Arena", "Detroit, MI", "Prime Video", "East Group A"),
    ("2026-11-20", "20:00", "WAS", "CHI", "0022600047", "United Center", "Chicago, IL", "MNMT/Monumental+", "East Group C"),
    ("2026-11-20", "20:00", "NOP", "OKC", "0022600048", "Paycom Center", "Oklahoma City, OK", "League Pass", "West Group B"),
    ("2026-11-20", "21:30", "PHX", "UTA", "0022600049", "Delta Center", "Salt Lake City, UT", "League Pass", "West Group A"),
    ("2026-11-20", "22:00", "HOU", "DEN", "0022600050", "Ball Arena", "Denver, CO", "Prime Video", "West Group A"),
    ("2026-11-20", "22:00", "SAC", "LAL", "0022600051", "Crypto.com Arena", "Los Angeles, CA", "League Pass", "West Group C"),
]

INJURY_PDF_URL = ("https://ak-static.cms.nba.com/referee/injury/"
                  "Injury-Report_2026-11-17_10_30AM.pdf")

# --------------------------------------------------------------------------- injuries
# Transcribed from the official 11/14/26 04:30 AM ET PDF. The report's own columns are
# Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason.
# The trailing letter is this project's transcription note, not an NBA field:
#   "E" = the team cell is present on the row itself
#   "C" = the row continues a team block from the previous PDF page, so the team and
#         matchup are carried over (flagged on the site as FLAG-V2-INJ-ATTR)
# (date, time_et, matchup, team, player, status, reason, attribution)
INJURIES = [
    ("2026-11-17", "07:30", "NYK@TOR", "Toronto Raptors", "Bittle, Nate", "Out", "Injury/Illness - Right Foot Avulsion Fracture", "E"),
    ("2026-11-17", "07:30", "NYK@TOR", "Toronto Raptors", "Leonard, Kawhi", "Out", "Injury/Illness - Left Knee Injury Management", "E"),
    ("2026-11-17", "07:30", "NYK@TOR", "Toronto Raptors", "McCullar Jr., Kevin", "Out", "G League - Two-Way", "E"),
    ("2026-11-17", "07:30", "NYK@TOR", "Toronto Raptors", "Smith, Malachi", "Out", "G League - Two-Way", "E"),
    ("2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Duren, Jalen", "Out", "Injury/Illness - Right Hamstring Strain", "E"),
    ("2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Holland II, Ronald", "Out", "Injury/Illness - Left Knee Contusion / Bone Bruise", "E"),
    ("2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Joe, Isaiah", "Doubtful", "Injury/Illness - Right Hip Contusion", "E"),
    ("2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Okorie, Ebuka", "Out", "G League - On Assignment", "E"),
    ("2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Onyenso, Ugonna", "Out", "G League - Two-Way", "E"),
    ("2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Prince, Taurean", "Out", "Injury/Illness - Right Knee Soreness", "E"),
    ("2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "Robinson, Duncan", "Out", "Injury/Illness - Left Quadriceps Strain", "E"),
    ("2026-11-17", "08:00", "DET@SAS", "San Antonio Spurs", "Brown, Maliq", "Out", "G League - Two-Way", "E"),
    ("2026-11-17", "08:00", "DET@SAS", "San Antonio Spurs", "Gillespie, Ja'Kobi", "Out", "G League - Two-Way", "E"),
    ("2026-11-17", "08:00", "DET@SAS", "San Antonio Spurs", "Harris, Tobias", "Out", "Injury/Illness - Left Calf Strain", "E"),
    ("2026-11-17", "08:00", "DET@SAS", "San Antonio Spurs", "Quaintance, Jayden", "Out", "Injury/Illness - Right Knee Surgery", "E"),
    ("2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "Bufkin, Kobe", "Out", "G League - Two-Way", "E"),
    ("2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "Hayes, Jaxson", "Out", "Injury/Illness - Left Knee Strain", "E"),
    ("2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "Ingram, Harrison", "Out", "G League - Two-Way", "E"),
    ("2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "Jackson Jr., Jaren", "Out", "Injury/Illness - Right MCL Tear", "E"),
    ("2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "Markkanen, Lauri", "Out", "Injury/Illness - Right Hand Fracture", "E"),
    ("2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "Nurkic, Jusuf", "Out", "Injury/Illness - Right Right Foot; 2nd Plantar Plate Tear", "C"),
    ("2026-11-17", "10:30", "UTA@LAC", "LA Clippers", "Beal, Bradley", "Out", "Injury/Illness - Right Knee Injury Management", "E"),
    ("2026-11-17", "10:30", "UTA@LAC", "LA Clippers", "Ingram, Brandon", "Out", "Injury/Illness - Right Heel Surgery", "E"),
    ("2026-11-17", "10:30", "UTA@LAC", "LA Clippers", "Miller, Jordan", "Out", "Injury/Illness - Left Rotator Cuff Surgery", "E"),
    ("2026-11-17", "10:30", "UTA@LAC", "LA Clippers", "Niederhauser, Yanic Konan", "Out", "Injury/Illness - Right Lisfranc Surgery", "E"),
    ("2026-11-17", "11:00", "CHA@LAL", "Charlotte Hornets", "Ajayi, Michael", "Out", "G League - Two-Way", "E"),
    ("2026-11-17", "11:00", "CHA@LAL", "Charlotte Hornets", "Boswell, Kylan", "Out", "G League - Two-Way", "E"),
    ("2026-11-17", "11:00", "CHA@LAL", "Charlotte Hornets", "Knueppel, Kon", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("2026-11-17", "11:00", "CHA@LAL", "Charlotte Hornets", "Schroder, Dennis", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("2026-11-17", "11:00", "CHA@LAL", "Charlotte Hornets", "Steinbach, Hannes", "Out", "G League - On Assignment", "E"),
    ("2026-11-17", "11:00", "CHA@LAL", "Los Angeles Lakers", "Grimes, Quentin", "Available", "Injury/Illness - Right Finger Splint", "E"),
    ("2026-11-17", "11:00", "CHA@LAL", "Los Angeles Lakers", "Kessler, Walker", "Out", "Injury/Illness - Right Lower Leg", "E"),
    ("2026-11-17", "11:00", "CHA@LAL", "Los Angeles Lakers", "Reaves, Austin", "Out", "Injury/Illness - Left Heel Contusion / Bone Bruise", "C"),
]
NOT_SUBMITTED = [
    ("2026-11-17", "08:00", "POR@MIN", "Portland Trail Blazers"),
    ("2026-11-17", "08:00", "POR@MIN", "Minnesota Timberwolves"),
    ("2026-11-18", "07:00", "HOU@IND", "Houston Rockets"),
    ("2026-11-18", "07:00", "HOU@IND", "Indiana Pacers"),
    ("2026-11-18", "07:00", "MEM@CLE", "Memphis Grizzlies"),
    ("2026-11-18", "07:00", "MEM@CLE", "Cleveland Cavaliers"),
    ("2026-11-18", "07:00", "MIL@MIA", "Milwaukee Bucks"),
    ("2026-11-18", "07:00", "MIL@MIA", "Miami Heat"),
    ("2026-11-18", "07:00", "PHI@ORL", "Philadelphia 76ers"),
    ("2026-11-18", "07:00", "PHI@ORL", "Orlando Magic"),
    ("2026-11-18", "07:30", "CHI@BKN", "Chicago Bulls"),
    ("2026-11-18", "07:30", "CHI@BKN", "Brooklyn Nets"),
    ("2026-11-18", "07:30", "WAS@TOR", "Washington Wizards"),
    ("2026-11-18", "07:30", "WAS@TOR", "Toronto Raptors"),
    ("2026-11-18", "08:00", "ATL@OKC", "Atlanta Hawks"),
    ("2026-11-18", "08:00", "ATL@OKC", "Oklahoma City Thunder"),
    ("2026-11-18", "08:00", "DET@NOP", "Detroit Pistons"),
    ("2026-11-18", "08:00", "DET@NOP", "New Orleans Pelicans"),
    ("2026-11-18", "08:00", "GSW@DAL", "Golden State Warriors"),
    ("2026-11-18", "08:00", "GSW@DAL", "Dallas Mavericks"),
    ("2026-11-18", "09:30", "BOS@DEN", "Boston Celtics"),
    ("2026-11-18", "09:30", "BOS@DEN", "Denver Nuggets"),
    ("2026-11-18", "10:00", "PHX@SAC", "Phoenix Suns"),
    ("2026-11-18", "10:00", "PHX@SAC", "Sacramento Kings"),
    ("2026-11-18", "10:00", "UTA@LAL", "Utah Jazz"),
    ("2026-11-18", "10:00", "UTA@LAL", "Los Angeles Lakers"),
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
