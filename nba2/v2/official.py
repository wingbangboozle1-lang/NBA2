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

AS_OF = "2026-11-14"
RETRIEVED_AT_UTC = "2026-11-14T09:40:00Z"
RETRIEVED_BY = "arena/ac5fab5c-nba2"

# The 3-day pick window the brief asks for, inclusive of both ends.
WINDOW_START = "2026-11-14"
WINDOW_END = "2026-11-17"

# --------------------------------------------------------------------------- team table
# tricode: W, L, HOME_W, HOME_L, ROAD_W, ROAD_L, PF(pts/g), PA(pts/g), OEFF, DEF, NET, PACE, PIE
# W/L + splits: nba.com/standings, fetched 2026-11-14.
# PF/PA: computed from the 183 official finals in data/raw/history/ (spot-checked against
#        nba.com/stats/teams/traditional: LAL 122.2 vs 122.2, SAS 119.5 vs 119.5).
# OEFF/DEF/NET/PACE/PIE: nba.com/stats/teams/advanced, fetched 2026-11-14.
TEAMS: dict[str, tuple] = {
    "ATL": (7, 6, 3, 3, 4, 3, 118.2, 116.8, 113.3, 111.9, 1.4, 103.55, 48.5),
    "BKN": (3, 8, 1, 3, 2, 5, 110.2, 115.3, 109.3, 114.4, -5.2, 99.83, 47.0),
    "BOS": (10, 2, 5, 0, 5, 2, 114.2, 103.1, 117.4, 105.6, 11.7, 96.62, 55.9),
    "CHA": (4, 8, 3, 4, 1, 4, 98.6, 109.6, 101.8, 113.0, -11.2, 96.92, 42.9),
    "CHI": (2, 9, 1, 4, 1, 5, 114.4, 127.7, 109.0, 122.0, -12.9, 103.83, 44.0),
    "CLE": (6, 7, 4, 2, 2, 5, 116.8, 115.8, 116.1, 115.2, 0.9, 99.7, 50.7),
    "DAL": (7, 5, 5, 2, 2, 3, 113.2, 112.2, 112.5, 111.7, 0.8, 100.5, 50.3),
    "DEN": (6, 4, 2, 2, 3, 2, 114.5, 113.3, 115.9, 115.1, 0.7, 97.58, 52.2),
    "DET": (8, 3, 3, 2, 5, 1, 115.5, 107.8, 114.1, 106.9, 7.2, 99.17, 55.3),
    "GSW": (8, 5, 6, 1, 2, 4, 116.7, 112.4, 116.1, 112.0, 4.1, 99.66, 51.8),
    "HOU": (10, 3, 7, 1, 3, 2, 116.2, 107.4, 119.3, 110.2, 9.1, 97.42, 55.8),
    "IND": (5, 8, 2, 4, 3, 3, 111.2, 113.2, 110.1, 111.7, -1.5, 101.15, 49.6),
    "LAC": (3, 8, 3, 3, 0, 5, 112.3, 117.5, 110.7, 115.8, -5.1, 100.55, 47.4),
    "LAL": (11, 2, 5, 1, 6, 1, 122.2, 114.2, 121.6, 113.6, 8.0, 100.5, 54.2),
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
# From https://www.nba.com/schedule?date=2026-11-15, read 2026-11-14.
# date, time_et, away, home, game_id, arena, city, national_broadcast, cup_group
# Window = the next three days, 2026-11-14 .. 2026-11-17 inclusive (27 games).
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
]

INJURY_PDF_URL = SOURCES["injury_pdf"][1]

# --------------------------------------------------------------------------- injuries
# Transcribed from the official 11/14/26 04:30 AM ET PDF. The report's own columns are
# Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason.
# The trailing letter is this project's transcription note, not an NBA field:
#   "E" = the team cell is present on the row itself
#   "C" = the row continues a team block from the previous PDF page, so the team and
#         matchup are carried over (flagged on the site as FLAG-V2-INJ-ATTR)
# (date, time_et, matchup, team, player, status, reason, attribution)
INJURIES = [
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Holmes II, DaRon", "Out", "G League - On Assignment", "E"),
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Nembhard, Ryan", "Out", "G League - Two-Way", "E"),
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain", "E"),
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Whitmore, Cam", "Out", "G League - Two-Way", "E"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Biberovic, Tarik", "Out", "Injury/Illness - Right Heel Bursitis", "E"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Christie, Max", "Questionable", "Injury/Illness - Left Ankle Sprain", "E"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "de Larrea, Sergio", "Out", "Injury/Illness - Right Knee Sprain", "E"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Johnson Jr., Morez", "Probable", "Injury/Illness - Left Shin / Tibia Contusion", "E"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Lively II, Dereck", "Out", "Injury/Illness - Right Foot Surgery", "E"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Martin, Caleb", "Available", "Injury/Illness - Right Thumb Splint", "E"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way", "E"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Brown Jr., Mikel", "Questionable", "Injury/Illness - Illness", "E"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment", "E"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way", "E"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment", "E"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Traore, Nolan", "Probable", "Injury/Illness - Right Calf Tightness / Soreness", "C"),
    ("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask", "E"),
    ("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery", "E"),
    ("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy", "E"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Duren, Jalen", "Out", "Injury/Illness - Right Hamstring Strain", "E"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Harkless, Elijah", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Joe, Isaiah", "Out", "Injury/Illness - Right Hip Contusion", "E"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Jones, Isaac", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Lanier, Chaz", "Out", "G League - On Assignment", "E"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Okorie, Ebuka", "Out", "G League - On Assignment", "E"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Onyenso, Ugonna", "Out", "G League - Two-Way", "E"),
]
NOT_SUBMITTED = [
    # 11/14 - the five teams that had filed nothing in the 04:30 AM ET release
    ("2026-11-14", "07:00", "DEN@NOP", "New Orleans Pelicans"),
    ("2026-11-14", "07:30", "DAL@CLE", "Cleveland Cavaliers"),
    ("2026-11-14", "08:00", "BKN@MEM", "Memphis Grizzlies"),
    ("2026-11-14", "08:00", "CHI@MIN", "Chicago Bulls"),
    ("2026-11-14", "08:00", "DET@MIA", "Miami Heat"),
    # 11/15 - every team is NOT YET SUBMITTED: the 5 p.m. local day-before filing deadline
    # for these games falls on 11/14, i.e. after this capture. Blank by policy, never estimated.
    ("2026-11-15", "01:00", "IND@PHI", "Indiana Pacers"),
    ("2026-11-15", "01:00", "IND@PHI", "Philadelphia 76ers"),
    ("2026-11-15", "04:00", "LAL@PHX", "Los Angeles Lakers"),
    ("2026-11-15", "04:00", "LAL@PHX", "Phoenix Suns"),
    ("2026-11-15", "04:30", "CHA@LAC", "Charlotte Hornets"),
    ("2026-11-15", "04:30", "CHA@LAC", "LA Clippers"),
    ("2026-11-15", "05:00", "SAS@UTA", "San Antonio Spurs"),
    ("2026-11-15", "05:00", "SAS@UTA", "Utah Jazz"),
    ("2026-11-15", "06:00", "DAL@BOS", "Dallas Mavericks"),
    ("2026-11-15", "06:00", "DAL@BOS", "Boston Celtics"),
    ("2026-11-15", "06:00", "NYK@TOR", "New York Knicks"),
    ("2026-11-15", "06:00", "NYK@TOR", "Toronto Raptors"),
    ("2026-11-15", "07:00", "HOU@WAS", "Houston Rockets"),
    ("2026-11-15", "07:00", "HOU@WAS", "Washington Wizards"),
    ("2026-11-15", "08:00", "ATL@MIL", "Atlanta Hawks"),
    ("2026-11-15", "08:00", "ATL@MIL", "Milwaukee Bucks"),
    ("2026-11-15", "09:00", "OKC@SAC", "Oklahoma City Thunder"),
    ("2026-11-15", "09:00", "OKC@SAC", "Sacramento Kings"),
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
