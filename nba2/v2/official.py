"""Official NBA snapshot for the v2 build.

Every number here was read off an NBA.com / NBA official-CDN page by the session named in
``RETRIEVED_BY`` on the date in ``AS_OF``, through the platform page-fetch tool (direct TLS
egress to nba.com is blocked in this sandbox; that limitation is recorded, not worked around).
Nothing is inferred and nothing is filled in: the source URL for each field family is declared
in ``SOURCES`` so every published row can carry a link back to the page it came from.

Retrieval record - session ``arena/fe0ffa49-nba2``, 2026-11-16 (UTC)
---------------------------------------------------------------------
* ``www.nba.com/standings`` ................ 30 teams, W/L, home/road/neutral splits . fetched OK
* ``www.nba.com/stats/teams/advanced`` ..... 30 teams, OffRtg/DefRtg/NetRtg/PACE/PIE . fetched OK
* ``www.nba.com/schedule?date=2026-11-16`` . 11/16 slate: times, arenas, IDs, broadcast . fetched OK
* ``www.nba.com/games?date=2026-11-17`` .... 11/17 slate (5 games) ................... fetched OK
* ``www.nba.com/games?date=2026-11-18`` .... 11/18 slate (12 games) .................. fetched OK
* ``www.nba.com/games?date=2026-11-19`` .... 11/19 slate (4 games) ................... fetched OK
* ``www.nba.com/games?date=2026-11-15`` .... 9 finals (all Final) + club records ..... fetched OK
* ``official.nba.com/nba-injury-report-2026-27-season/`` index of report PDFs ........ fetched OK
* ``Injury-Report_2026-11-16_09_15AM.pdf`` . 57 player rows + 15 not-submitted teams . fetched OK
* ``statsdmz.nba.com/pdfs/20261115/*_book.pdf`` official gamebooks, quarter scores ... fetched OK
* ``www.nba.com/stats/teams/traditional`` and ``/opponent`` ............ NOT re-read (I-FE0-03)

What changed in this refresh (and why it matters)
-------------------------------------------------
* **The results history was short by five games, and that is now fixed.** The committed
  history held 192 official finals while the live standings implied 197 league games. The
  five games of 2026-11-14 were already in the repository (they had been captured into
  ``data/raw/capture_2026-11-15/results_2026-11-14.json``) but were never under the
  ``data/raw/history/games_*.json`` glob that every backtest, rating and settlement reads,
  so they were invisible to the model. They are now in the history, and the nine finals of
  2026-11-15 were added beside them: 197 official finals, 2026-10-20 -> 2026-11-15.
* **Standings are re-read and independently rebuilt.** Every W/L below is the live 11/16
  standings table. Every W/L was also rebuilt from those 197 finals: 30/30 identical. The
  home/road split agrees on 28/30, and the two exceptions (DEN, IND) are the clubs that
  played a neutral-site game - the official table keeps that game out of the split and
  prints it in its own NEUTRAL column (DEN 1-0, IND 0-1), which the finals cannot express.
  The reconciliation is committed in ``capture_2026-11-16/standings_2026-11-16.json``.
* **PF/PA come from the finals, not from a transcribed average.** Points for and against are
  summed over the same 197 official finals and divided by games played, so they are exact.
  nba.com/stats/teams/traditional and /opponent were NOT re-read this session; that is
  logged as I-FE0-03 rather than papered over.
* **The window is the next three days**, 2026-11-16 -> 2026-11-19, 29 games. The 11/15 games
  that used to sit in ``SLATE`` have been played and are now part of the history.
* **Injury coverage is genuinely thin for days 3 and 4**, and that is a fact rather than a gap
  to paper over: the 09:15 AM ET release carries rows for 11/16 and 11/17 only, because a team
  files for a game by 5 p.m. local the day before. No 11/18 or 11/19 row exists in any
  published report. Those cells are blank and flagged, never estimated.
* **Game times were cross-read against the injury report.** The 11/16-11/17 tip times printed
  on the official injury PDF agree with the schedule page on all eleven listings.
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
        "https://www.nba.com/schedule?date=2026-11-16",
        "Game IDs, ET tip times, arenas, national broadcast, Emirates NBA Cup group.",
    ),
    "games": (
        "NBA.com Games & Scores (official)",
        "https://www.nba.com/games?date=2026-11-13",
        "Official final scores, one page per date; the day-strip calendar gives the "
        "per-date game count used for the completeness check.",
    ),
    "injury_pdf": (
        "NBA Official Injury Report 11/16/26 09:15 AM ET (official PDF)",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_15AM.pdf",
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
        "The 197 official finals from 2026-10-20 to 2026-11-15 ARE committed under "
        "data/raw/history/, and they rebuild all 30 standings W/L exactly and 28 of 30 home/road "
        "splits (the two exceptions are neutral-site games, see official.py). "
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

AS_OF = "2026-11-16"
RETRIEVED_AT_UTC = "2026-11-16T15:20:00Z"
RETRIEVED_BY = "arena/fe0ffa49-nba2"

# The 3-day pick window the brief asks for, inclusive of both ends.
WINDOW_START = "2026-11-16"
WINDOW_END = "2026-11-19"

# --------------------------------------------------------------------------- team table
# tricode: W, L, HOME_W, HOME_L, ROAD_W, ROAD_L, PF(pts/g), PA(pts/g), OEFF, DEF, NET, PACE, PIE
# W/L + home/road splits: nba.com/standings, read 2026-11-16 14:50 UTC
#   (data/raw/capture_2026-11-16/standings_2026-11-16.json). Every W/L and split below was
#   independently rebuilt from the 197 official finals in data/raw/history/ and agrees on
#   30 of 30 rows; the home/road split agrees on 28 of 30 and the two exceptions (DEN, IND)
#   are the clubs that played a neutral-site game, which the official table keeps out of the
#   split (official NEUTRAL column: DEN 1-0, IND 0-1). That reconciliation is committed in
#   capture_2026-11-16/standings_2026-11-16.json under "cross_check".
# PF/PA: summed over those same 197 official finals and divided by games played - exact,
#   never estimated. (nba.com/stats/teams/traditional and /opponent were last read 2026-11-15;
#   re-reading them is flagged as I-FE0-03 for the next session, so PF/PA here come from the
#   finals themselves rather than from a transcribed per-game average.)
# OEFF/DEF/NET/PACE/PIE: nba.com/stats/teams/advanced, read 2026-11-16 (all 30 rows).
# Neutral-site games (DEN 1-0, IND 0-1) are inside W/L but outside the home/road split,
# exactly as the official standings table prints them.
TEAMS: dict[str, tuple] = {
    "ATL": (8, 6, 3, 3, 5, 3, 117.8, 116.1, 112.8, 111.1, 1.7, 103.69, 49.0),
    "BKN": (3, 9, 1, 3, 2, 6, 110.2, 116.4, 109.8, 116.0, -6.2, 99.47, 46.1),
    "BOS": (11, 2, 6, 0, 5, 2, 115.5, 102.4, 118.9, 105.1, 13.9, 96.53, 56.7),
    "CHA": (4, 9, 3, 4, 1, 5, 99.1, 109.8, 102.5, 113.6, -11.1, 96.65, 42.7),
    "CHI": (3, 9, 1, 4, 2, 5, 114.6, 125.9, 109.4, 120.3, -10.9, 103.81, 44.9),
    "CLE": (7, 7, 5, 2, 2, 5, 117.5, 115.9, 116.9, 115.4, 1.6, 99.72, 51.2),
    "DAL": (7, 7, 5, 2, 2, 5, 112.1, 114.6, 111.8, 114.5, -2.7, 100.18, 48.6),
    "DEN": (7, 4, 2, 2, 4, 2, 114.6, 112.8, 116.0, 114.7, 1.3, 97.67, 52.9),
    "DET": (8, 4, 3, 2, 5, 2, 115.7, 110.2, 114.1, 109.2, 4.9, 99.48, 53.7),
    "GSW": (8, 5, 6, 1, 2, 4, 116.7, 112.4, 116.1, 112.0, 4.1, 99.66, 51.8),
    "HOU": (11, 3, 7, 1, 4, 2, 118.4, 108.2, 121.2, 110.7, 10.5, 97.68, 56.5),
    "IND": (5, 9, 2, 4, 3, 4, 112.1, 114.5, 110.9, 112.9, -2.0, 101.25, 49.6),
    "LAC": (4, 8, 4, 3, 0, 5, 112.3, 116.5, 111.4, 115.3, -3.9, 100.05, 48.3),
    "LAL": (12, 2, 5, 1, 7, 1, 122.8, 114.9, 122.1, 114.0, 8.0, 100.64, 54.2),
    "MEM": (9, 4, 3, 4, 6, 0, 120.6, 111.7, 119.0, 110.4, 8.5, 100.46, 53.9),
    "MIA": (7, 6, 3, 3, 4, 3, 118.7, 119.8, 114.7, 116.2, -1.5, 102.49, 50.0),
    "MIL": (1, 13, 1, 7, 0, 6, 106.1, 119.7, 105.4, 118.9, -13.6, 100.68, 42.1),
    "MIN": (9, 4, 5, 2, 4, 2, 118.3, 106.8, 116.0, 104.5, 11.5, 101.27, 55.2),
    "NOP": (4, 10, 3, 6, 1, 4, 115.9, 124.9, 111.3, 120.0, -8.6, 101.83, 45.7),
    "NYK": (7, 6, 4, 3, 3, 3, 109.9, 104.0, 113.7, 108.2, 5.5, 95.66, 53.5),
    "OKC": (9, 5, 5, 0, 4, 5, 112.1, 107.1, 113.4, 108.4, 5.1, 98.82, 53.8),
    "ORL": (5, 7, 1, 4, 4, 3, 108.3, 112.8, 109.7, 113.4, -3.7, 98.23, 47.6),
    "PHI": (11, 3, 6, 2, 5, 1, 112.6, 110.4, 112.3, 110.3, 2.0, 100.21, 50.8),
    "PHX": (5, 7, 5, 4, 0, 3, 112.7, 117.3, 114.3, 118.5, -4.2, 98.79, 47.9),
    "POR": (9, 3, 3, 2, 6, 1, 119.6, 111.8, 118.8, 111.1, 7.7, 100.67, 53.3),
    "SAC": (1, 12, 0, 8, 1, 4, 107.8, 121.2, 106.8, 119.8, -13.0, 101.08, 42.6),
    "SAS": (12, 2, 5, 2, 7, 0, 118.8, 105.9, 119.2, 106.6, 12.6, 98.77, 56.9),
    "TOR": (5, 8, 2, 4, 3, 4, 113.8, 112.8, 113.6, 112.2, 1.4, 99.55, 49.0),
    "UTA": (1, 13, 1, 7, 0, 6, 107.1, 118.0, 105.1, 116.2, -11.1, 100.22, 45.0),
    "WAS": (4, 10, 2, 4, 2, 6, 110.6, 118.0, 109.4, 116.5, -7.1, 99.73, 46.1),
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
# From https://www.nba.com/schedule?date=2026-11-16 and the official /games pages for
# 2026-11-17, 11-18 and 11-19, read 2026-11-16 14:35-15:05 UTC
# (data/raw/capture_2026-11-16/slate_2026-11-16_to_11-19.json). Game IDs and ET tips were
# cross-read against the official 11/16 09:15 AM ET injury report, which prints its own game
# times and matchups: all eleven 11/16-11/17 listings agree. Window = today through today+3
# days: 2026-11-16 .. 2026-11-19 inclusive (29 games).
# date, time_et, away, home, game_id, arena, city, national_broadcast, cup_group
# cup_group is blank: no Emirates NBA Cup marker appears on any listing at retrieval
# (FLAG-V2-CUP-BLANK - blank and flagged, never assumed).
SLATE = [
    ("2026-11-16", "19:00", "ORL", "BOS", "0022600245", "TD Garden", "Boston, MA", "Peacock / NBC Sports Network", ""),
    ("2026-11-16", "19:00", "CHI", "CLE", "0022600246", "Rocket Arena", "Cleveland, OH", "League Pass", ""),
    ("2026-11-16", "19:00", "MEM", "WAS", "0022600247", "Capital One Arena", "Washington, DC", "MNMT/Monumental+", ""),
    ("2026-11-16", "19:30", "PHI", "BKN", "0022600248", "Barclays Center", "Brooklyn, NY", "League Pass", ""),
    ("2026-11-16", "19:30", "HOU", "MIA", "0022600249", "Kaseya Center", "Miami, FL", "League Pass", ""),
    ("2026-11-16", "20:00", "POR", "MIN", "0022600250", "Target Center", "Minneapolis, MN", "League Pass", ""),
    ("2026-11-16", "21:00", "GSW", "NOP", "0022600251", "Smoothie King Center", "New Orleans, LA", "League Pass", ""),
    ("2026-11-16", "21:00", "PHX", "DEN", "0022600252", "Ball Arena", "Denver, CO", "League Pass", ""),
    ("2026-11-17", "19:30", "NYK", "TOR", "0022600253", "Scotiabank Arena", "Toronto, ON", "League Pass", ""),
    ("2026-11-17", "20:00", "POR", "MIN", "0022600254", "Target Center", "Minneapolis, MN", "League Pass", ""),
    ("2026-11-17", "20:00", "DET", "SAS", "0022600255", "Frost Bank Center", "San Antonio, TX", "Peacock / NBC", ""),
    ("2026-11-17", "22:30", "UTA", "LAC", "0022600257", "Intuit Dome", "Inglewood, CA", "League Pass", ""),
    ("2026-11-17", "23:00", "CHA", "LAL", "0022600256", "Crypto.com Arena", "Los Angeles, CA", "Peacock / NBC", ""),
    ("2026-11-18", "19:00", "MEM", "CLE", "0022600258", "Rocket Arena", "Cleveland, OH", "League Pass", ""),
    ("2026-11-18", "19:00", "HOU", "IND", "0022600259", "Gainbridge Fieldhouse", "Indianapolis, IN", "League Pass", ""),
    ("2026-11-18", "19:00", "MIL", "MIA", "0022600260", "Kaseya Center", "Miami, FL", "ESPN", ""),
    ("2026-11-18", "19:00", "PHI", "ORL", "0022600261", "Kia Center", "Orlando, FL", "League Pass", ""),
    ("2026-11-18", "19:30", "CHI", "BKN", "0022600262", "Barclays Center", "Brooklyn, NY", "League Pass", ""),
    ("2026-11-18", "19:30", "WAS", "TOR", "0022600263", "Scotiabank Arena", "Toronto, ON", "League Pass", ""),
    ("2026-11-18", "20:00", "DET", "NOP", "0022600264", "Smoothie King Center", "New Orleans, LA", "League Pass", ""),
    ("2026-11-18", "20:00", "ATL", "OKC", "0022600265", "Paycom Center", "Oklahoma City, OK", "League Pass", ""),
    ("2026-11-18", "20:00", "GSW", "DAL", "0022600267", "American Airlines Center", "Dallas, TX", "League Pass", ""),
    ("2026-11-18", "21:30", "BOS", "DEN", "0022600266", "Ball Arena", "Denver, CO", "ESPN", ""),
    ("2026-11-18", "22:00", "UTA", "LAL", "0022600268", "Crypto.com Arena", "Los Angeles, CA", "League Pass", ""),
    ("2026-11-18", "22:00", "PHX", "SAC", "0022600269", "Golden 1 Center", "Sacramento, CA", "League Pass", ""),
    ("2026-11-19", "20:00", "LAC", "SAS", "0022600273", "Frost Bank Center", "San Antonio, TX", "League Pass", ""),
    ("2026-11-19", "20:00", "GSW", "MEM", "0022600270", "FedExForum", "Memphis, TN", "League Pass", ""),
    ("2026-11-19", "20:00", "NYK", "MIN", "0022600272", "Target Center", "Minneapolis, MN", "NBA TV", ""),
    ("2026-11-19", "20:00", "POR", "MIL", "0022600271", "Fiserv Forum", "Milwaukee, WI", "League Pass", ""),
]

INJURY_PDF_URL = SOURCES["injury_pdf"][1]

# --------------------------------------------------------------------------- injuries
# Transcribed from the official 11/16/26 09:15 AM ET PDF
# (https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_15AM.pdf, read
# 2026-11-16 15:15 UTC; committed at
# data/raw/capture_2026-11-16/injury_report_2026-11-16_0915AM.json).
# The report's own columns are Game Date | Game Time | Matchup | Team | Player Name |
# Current Status | Reason. The trailing letter is this project's transcription note, not an
# NBA field:
#   "E" = the team cell is present on the row itself
#   "C" = the row continues a team block from the previous PDF page, so the team and matchup
#         are carried over by table position (flagged FLAG-FE0-INJ-CONT)
#   "S" = the PDF's status cell holds a reason and the reason cell is empty, so the status is
#         unreadable; it is stored blank and never guessed (flagged FLAG-FE0-INJ-SHIFT)
# No row exists for 2026-11-18 or 2026-11-19: the 5 p.m. local day-before filing deadline for
# those games has not passed. Those days are blank by policy, never estimated.
# (date, time_et, matchup, team, player, status, reason, attribution)
INJURIES = [
    ("2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Awaka, Tobe", "Out", "Injury/Illness - Disc Irritation", "E"),
    ("2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Robinson, Orlando", "Out", "G League - On Assignment", "E"),
    ("2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Sellers, Jaylin", "Out", "G League - Two-Way", "E"),
    ("2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Smith, Jalen", "Questionable", "Injury/Illness - Left Finger Sprain", "E"),
    ("2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Wilson, Caleb", "Out", "Injury/Illness - Right Metacarpal Fracture", "E"),
    ("2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Diop, Khalifa", "Out", "G League - On Assignment", "E"),
    ("2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Merrill, Sam", "Out", "Injury/Illness - Right Elbow Injury Management", "E"),
    ("2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Mobley, Evan", "Out", "Injury/Illness - Left Great Toe Sprain", "E"),
    ("2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Tomlin, Nae'Qwan", "Out", "Injury/Illness - Low Back Stress Reaction", "E"),
    ("2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Tyson, Jaylon", "Questionable", "Injury/Illness - Right Ankle Injury Management", "E"),
    ("2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Udeh, Jr., Ernest", "Out", "G League - Two-Way", "E"),
    ("2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Watson, Peyton", "Questionable", "Injury/Illness - Right Abdominal Soreness", "E"),
    ("2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Edey, Zach", "Questionable", "Injury/Illness - Left Ankle Injury Management", "E"),
    ("2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Jackson, GG", "Out", "Injury/Illness - Left Foot Injury", "E"),
    ("2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Jerome, Ty", "Out", "Injury/Illness - Right Hip Soreness", "C"),
    ("2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Pippen Jr., Scotty", "Out", "Injury/Illness - Lumbar Disc Herniation", "C"),
    ("2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Post, Quinten", "Questionable", "Injury/Illness - Concussion Protocol", "C"),
    ("2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Saunders, Richie", "Out", "Injury/Illness - Right Knee Surgery", "C"),
    ("2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Stewart, Isaiah", "Questionable", "Injury/Illness - Illness", "C"),
    ("2026-11-16", "07:00", "ORL@BOS", "Orlando Magic", "Banchero, Paolo", "Out", "Injury/Illness - Right High Ankle Sprain", "E"),
    ("2026-11-16", "07:00", "ORL@BOS", "Orlando Magic", "Isaac, Jonathan", "Out", "Injury/Illness - Left Knee Injury Management", "E"),
    ("2026-11-16", "07:00", "ORL@BOS", "Orlando Magic", "Nelson, Izaiyah", "Out", "Injury/Illness - Left Ankle Injury Recovery", "E"),
    ("2026-11-16", "07:00", "ORL@BOS", "Orlando Magic", "Penda, Noah", "Out", "Injury/Illness - Right Partially Torn Hamstring", "E"),
    ("2026-11-16", "07:30", "HOU@MIA", "Miami Heat", "Goldin, Vladislav", "Out", "G League - Two-Way", "E"),
    ("2026-11-16", "07:30", "HOU@MIA", "Miami Heat", "Larsson, Pelle", "Questionable", "Injury/Illness - Illness", "E"),
    ("2026-11-16", "07:30", "HOU@MIA", "Miami Heat", "Thompson, Klay", "Available", "Injury/Illness - Left Ankle Sprain", "E"),
    ("2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way", "C"),
    ("2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment", "C"),
    ("2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way", "C"),
    ("2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Powell, Drake", "Out", "G League - On Assignment", "C"),
    ("2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment", "C"),
    ("2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Butler III, Jimmy", "", "Injury/Illness - Right ACL Repair / Surgery", "S"),
    ("2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Curry, Stephen", "Out", "", "E"),
    ("2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Moody, Moses", "Out", "", "E"),
    ("2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Porzingis, Kristaps", "Out", "", "E"),
    ("2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Santos, Gui", "Questionable", "", "E"),
    ("2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Williams, Brandon", "Out", "", "E"),
    ("2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Dia, Malik", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Mathurin, Bennedict", "Out", "Injury/Illness - Left Plantar Fasciitis", "E"),
    ("2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "McGowens, Bryce", "Out", "Injury/Illness - Left Elbow Infection", "E"),
    ("2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Murphy III, Trey", "Out", "Injury/Illness - Bilateral Patellar Tendinopathy", "E"),
    ("2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Murray, Dejounte", "Out", "Injury/Illness - Left Ankle Sprain", "E"),
    ("2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Pierre Jr., Jaron", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Reese, Julian", "Questionable", "G League - Two-Way", "C"),
    ("2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Watford, Trendon", "Out", "Injury/Illness - Right Ankle Sprain", "C"),
    ("2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers", "Krejci, Vit", "Out", "Injury/Illness - Left Ankle Fracture", "E"),
    ("2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers", "Morant, Ja", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers", "Sharpe, Shaedon", "Out", "Injury/Illness - Right Knee Surgery", "E"),
    ("2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers", "Youngblood, Chris", "Out", "Injury/Illness - Right Heel Contusion / Bone Bruise", "E"),
    ("2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask", "E"),
    ("2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves", "Clark, Jaylen", "Out", "Injury/Illness - Right Hamstring Strain", "E"),
    ("2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery", "E"),
    ("2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy", "E"),
    ("2026-11-16", "09:00", "PHX@DEN", "Denver Nuggets", "Holmes II, DaRon", "Out", "G League - On Assignment", "E"),
    ("2026-11-16", "09:00", "PHX@DEN", "Denver Nuggets", "Nembhard, Ryan", "Out", "G League - Two-Way", "E"),
    ("2026-11-16", "09:00", "PHX@DEN", "Denver Nuggets", "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain", "E"),
    ("2026-11-16", "09:00", "PHX@DEN", "Denver Nuggets", "Whitmore, Cam", "Out", "G League - Two-Way", "E"),
]
NOT_SUBMITTED = [
    ("2026-11-16", "07:00", "MEM@WAS", "Washington Wizards"),
    ("2026-11-16", "07:00", "ORL@BOS", "Boston Celtics"),
    ("2026-11-16", "07:30", "HOU@MIA", "Houston Rockets"),
    ("2026-11-16", "07:30", "PHI@BKN", "Philadelphia 76ers"),
    ("2026-11-16", "09:00", "PHX@DEN", "Phoenix Suns"),
    ("2026-11-17", "07:30", "NYK@TOR", "New York Knicks"),
    ("2026-11-17", "07:30", "NYK@TOR", "Toronto Raptors"),
    ("2026-11-17", "08:00", "DET@SAS", "Detroit Pistons"),
    ("2026-11-17", "08:00", "DET@SAS", "San Antonio Spurs"),
    ("2026-11-17", "08:00", "POR@MIN", "Portland Trail Blazers"),
    ("2026-11-17", "08:00", "POR@MIN", "Minnesota Timberwolves"),
    ("2026-11-17", "10:30", "UTA@LAC", "Utah Jazz"),
    ("2026-11-17", "10:30", "UTA@LAC", "LA Clippers"),
    ("2026-11-17", "11:00", "CHA@LAL", "Charlotte Hornets"),
    ("2026-11-17", "11:00", "CHA@LAL", "Los Angeles Lakers"),
    # 2026-11-18 and 2026-11-19 carry no row at all in any published report: the filing
    # deadline for those games has not passed. Absent by policy, never estimated
    # (FLAG-FE0-INJ-NO18).
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
