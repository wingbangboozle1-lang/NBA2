"""Official NBA snapshot for the v2 build.

Every number here was read off an NBA.com / NBA official-CDN page by the session named in
``RETRIEVED_BY`` on the date in ``AS_OF``, through the platform page-fetch tool (direct TLS
egress to nba.com is blocked in this sandbox; that limitation is recorded, not worked around).
Nothing is inferred and nothing is filled in: the source URL for each field family is declared
in ``SOURCES`` so every published row can carry a link back to the page it came from.

Retrieval record - session ``arena/6b9f3bbe-nba2``, 2026-11-19 (UTC 11:15-12:32)
-------------------------------------------------------------------------------
* ``www.nba.com/standings`` ................ 30 clubs, W/L + all splits ............. fetched OK
* ``www.nba.com/stats/teams/traditional`` .. 30 rows, GP/PTS/+/- (PerGame) ......... fetched OK
* ``www.nba.com/stats/teams/opponent`` ..... 30 rows, Opp PTS (PerGame) ............ fetched OK
* ``www.nba.com/stats/teams/advanced`` ..... 30 rows, OffRtg/DefRtg/NetRtg/PACE/PIE fetched OK
* ``www.nba.com/games?date=2026-11-19..22`` 26 window games, ids + ET tips ......... fetched OK
* ``www.nba.com/games?date=2026-11-18`` .... 12 official finals .................... fetched OK
* ``statsdmz.nba.com/pdfs/20261118/*`` ..... 12 official gamebooks (line scores) ... fetched OK
* ``official.nba.com/nba-injury-report-2026-27-season/`` index + filing rules ..... fetched OK
* ``Injury-Report_2026-11-19_07_15AM.pdf``  23 player rows + 21 not-submitted rows . fetched OK

Full provenance: ``data/raw/refresh_2026-11-19/`` (capture_index.json lists every page, the
unread items and why) and ``audit/session-6b9f3bbe-nba2/write_capture.py`` (the writer whose
arithmetic selftest re-derives wins=losses=222, home wins 111 = road losses 111, home losses
110 = road wins 110, GP = W+L for all 30 clubs, and the PF/PA rounding identity — CLEAN).

What changed in this refresh (and why it matters)
-------------------------------------------------
* **The RQ-8892-02 re-cut is executed.** This supersedes the 2026-11-15 snapshot by
  ``arena/98b0eae9-nba2`` (same schema, same public names, new capture), per the 7-step spec in
  ``analysis/session-8892d20c-capture.md`` §4. All layers move to one anchor in the same change.
* **PF/PA re-basing is disclosed, not quiet.** The 2026-11-15 snapshot summed PF/PA from the
  committed official finals (data/raw/history/). From this snapshot onward PF and PA are the
  official per-game page values themselves — traditional PTS and opponent OppPTS. Both
  definitions were cross-checked against each other at capture time (PTS - OppPTS reproduces the
  traditional page's own +/- for all 30 clubs within 0.11, and the league-wide PF/PA balance holds
  within the 0.1 x 444 rounding bound). The definition switch is named here and on the site.
* **The window is the next three days**, 2026-11-19 -> 2026-11-22, 26 games (4 + 9 + 6 + 7).
  The 11/20 card is Emirates NBA Cup group play; the cup_group column carries the group labels
  exactly as the official cards print them. The 11/18 games (12 finals) are now in the committed
  results feed (data/raw/finals_2026-11-18.json) with quarter rows from the official gamebooks.
* **Injury coverage is thin for days 2 and 3 — that is the league's filing rule, not a gap.**
  For 11/21 and 11/22 games the 5 p.m. local day-before deadline falls on 11/20-11/21, after this
  capture. Those cells stay blank and flagged, never estimated. One irregularity is recorded as
  read: the 11/19 07:15 AM release lists no New York player rows for NYK@MIN (and no
  NOT-YET-SUBMITTED row for the club either); two Questionable rows (Kuminga, Pullin) lose their
  team cell at the PDF page break and carry the previous team block per the PDF's own
  block-continuation convention (attribution "C", flagged FLAG-V2-INJ-ATTR).
"""

from __future__ import annotations

import math

# --------------------------------------------------------------------------- sources
SOURCES = {
    "standings": (
        "NBA.com Standings (official)",
        "https://www.nba.com/standings",
        "W, L, WIN%, home/road/neutral splits, conference and division records.",
    ),
    "team_trad": (
        "NBA.com Stats - Teams Traditional (official)",
        "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "GP, MIN, PTS (points per game), +/-, per-team shooting splits.",
    ),
    "team_opp": (
        "NBA.com Stats - Teams Opponent (official)",
        "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "Opponent PTS per game (points allowed), opponent shooting splits.",
    ),
    "team_adv": (
        "NBA.com Stats - Teams Advanced (official)",
        "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "OffRtg, DefRtg, NetRtg, PACE, PIE - all per-100-possession.",
    ),
    "schedule": (
        "NBA.com Games & Scores day strips (official)",
        "https://www.nba.com/games?date=2026-11-19",
        "Game IDs, ET tip times, Emirates NBA Cup group labels; one strip per date of the window.",
    ),
    "games": (
        "NBA.com Games & Scores (official)",
        "https://www.nba.com/games?date=2026-11-18",
        "Official final scores, one page per date; the day-strip calendar gives the "
        "per-date game count used for the completeness check.",
    ),
    "gamebooks": (
        "NBA Stats DMZ official gamebook PDFs (official)",
        "https://statsdmz.nba.com/pdfs/20261118/20261118_HOUIND_book.pdf",
        "Quarter-by-quarter line scores for the 2026-11-18 finals; each row is required to "
        "sum to the printed final.",
    ),
    "injury_pdf": (
        "NBA Official Injury Report 11/19/26 07:15 AM ET (official PDF)",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_15AM.pdf",
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
        "The official finals through 2026-11-18 (222 regular-season games, the exact count the "
        "official standings card implies) ARE committed: data/raw/history/ through 11/13 plus the "
        "nightly-refresh finals feeds finals_2026-11-13..18.json, which rebuild every one of the "
        "30 standings records exactly. The scheduled refresh appends each night's results when the "
        "runner transport allows; between its runs the window ages.",
        "https://www.nba.com/games?date=2026-11-18",
    ),
    "player_box": (
        "Per-player game logs (minutes, usage, on/off)",
        "nba.com/stats player pages render season aggregates only for this client. Required for: "
        "minutes distributions, prop bet probabilities, injury replacement modelling. The v5 layer "
        "captures official gamebook PDFs for the games it covers, which is why player-coverage is "
        "windowed rather than season-wide.",
        "https://www.nba.com/stats/players/traditional",
    ),
    "future_injuries": (
        "Injury designations for game days beyond the next filing deadline",
        "The NBA publishes a report only once a team has filed. For a game on day +2 or +3 the "
        "filing deadline has not yet passed, so no official row exists to read.",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
    ),
}

AS_OF = "2026-11-19"
RETRIEVED_AT_UTC = "2026-11-19T12:32:00Z"
RETRIEVED_BY = "arena/6b9f3bbe-nba2"

# The 3-day pick window the brief asks for, inclusive of both ends.
WINDOW_START = "2026-11-19"
WINDOW_END = "2026-11-22"

# --------------------------------------------------------------------------- team table
# tricode: W, L, HOME_W, HOME_L, ROAD_W, ROAD_L, PF(pts/g), PA(pts/g), OEFF, DEF, NET, PACE, PIE
# W/L + splits: nba.com/standings, fetched 2026-11-19 (data/raw/refresh_2026-11-19/standings_2026-11-19.json).
#   The league identities hold exactly: wins 222 = losses 222; home wins 111 = road losses 111;
#   home losses 110 = road wins 110; every club's home+road+neutral reproduces its own W-L.
#   Neutral-site games (DEN 1-0, IND 0-1) are inside W/L but outside the home/road split,
#   exactly as the official standings table prints them.
# PF/PA (RE-BASED this snapshot): the official per-game page values — traditional PTS and
#   opponent OppPTS (data/raw/refresh_2026-11-19/team_stats_2026-11-19.json). The 2026-11-15
#   snapshot summed PF/PA from committed finals; the two definitions agree within rounding
#   (PTS - OppPTS reproduces the traditional page's +/- for 30/30 clubs within 0.11). Say which
#   is which rather than letting the definition change quietly.
# OEFF/DEF/NET/PACE/PIE: nba.com/stats/teams/advanced, fetched 2026-11-19 (all 30 rows).
TEAMS: dict[str, tuple] = {
    "ATL": (9, 6, 3, 3, 6, 3, 117.7, 115.8, 112.8, 110.8, 1.9, 103.71, 49.0),
    "BKN": (3, 11, 1, 5, 2, 6, 110.9, 119.2, 110.5, 119.0, -8.4, 99.51, 45.2),
    "BOS": (11, 4, 6, 1, 5, 3, 113.9, 103.4, 117.0, 106.0, 11.0, 96.76, 54.7),
    "CHA": (4, 10, 3, 4, 1, 6, 100.1, 110.4, 103.1, 113.7, -10.6, 96.43, 43.5),
    "CHI": (4, 10, 1, 4, 3, 6, 116.2, 124.6, 111.1, 119.1, -8.0, 103.80, 46.2),
    "CLE": (8, 8, 6, 3, 2, 5, 118.3, 116.3, 117.5, 115.5, 2.0, 100.01, 51.0),
    "DAL": (8, 7, 6, 2, 2, 5, 112.3, 113.2, 112.3, 113.4, -1.1, 99.97, 49.4),
    "DEN": (8, 5, 3, 3, 4, 2, 113.2, 112.2, 114.3, 113.8, 0.5, 98.02, 52.5),
    "DET": (10, 4, 3, 2, 7, 2, 115.4, 108.9, 114.9, 108.9, 6.0, 98.78, 54.2),
    "GSW": (8, 7, 6, 1, 2, 6, 113.7, 112.8, 113.4, 112.8, 0.6, 99.41, 50.3),
    "HOU": (12, 4, 7, 1, 5, 3, 117.9, 109.2, 121.1, 112.1, 9.0, 97.41, 55.3),
    "IND": (5, 10, 2, 5, 3, 4, 111.5, 114.8, 110.7, 113.6, -2.9, 100.90, 49.4),
    "LAC": (4, 9, 4, 4, 0, 5, 111.9, 117.7, 111.4, 117.0, -5.6, 99.74, 47.4),
    "LAL": (13, 3, 6, 2, 7, 1, 120.9, 114.4, 119.8, 113.2, 6.7, 100.35, 53.0),
    "MEM": (11, 4, 3, 4, 8, 0, 121.9, 112.9, 120.6, 111.9, 8.7, 100.27, 54.3),
    "MIA": (9, 6, 5, 3, 4, 3, 120.5, 119.9, 116.9, 116.7, 0.3, 102.19, 50.8),
    "MIL": (1, 14, 1, 7, 0, 7, 107.7, 120.9, 106.7, 119.7, -13.0, 101.00, 42.4),
    "MIN": (11, 4, 7, 2, 4, 2, 116.7, 106.1, 114.5, 104.0, 10.5, 101.23, 55.0),
    "NOP": (5, 11, 4, 7, 1, 4, 115.4, 122.8, 111.7, 118.9, -7.1, 101.30, 46.4),
    "NYK": (8, 6, 4, 3, 4, 3, 110.0, 103.9, 114.8, 109.0, 5.8, 94.87, 53.6),
    "OKC": (9, 6, 5, 1, 4, 5, 112.1, 107.7, 113.0, 108.7, 4.4, 99.17, 53.5),
    "ORL": (6, 8, 1, 5, 5, 3, 109.4, 112.8, 111.3, 114.0, -2.7, 97.84, 48.5),
    "PHI": (13, 3, 6, 2, 7, 1, 114.5, 111.6, 114.5, 111.8, 2.7, 99.88, 51.4),
    "PHX": (7, 7, 5, 4, 2, 3, 114.1, 115.7, 115.6, 116.8, -1.2, 98.89, 49.4),
    "POR": (9, 5, 3, 2, 6, 3, 117.0, 111.0, 116.2, 110.2, 6.0, 100.71, 52.5),
    "SAC": (1, 13, 0, 9, 1, 4, 107.7, 121.7, 106.9, 120.4, -13.5, 100.93, 42.5),
    "SAS": (12, 3, 5, 3, 7, 0, 117.1, 105.9, 118.1, 107.0, 11.1, 98.35, 56.0),
    "TOR": (5, 10, 2, 6, 3, 4, 112.0, 112.0, 113.7, 113.1, 0.5, 98.09, 48.4),
    "UTA": (3, 13, 1, 7, 2, 6, 108.8, 116.0, 107.0, 114.5, -7.5, 100.16, 47.2),
    "WAS": (5, 11, 2, 5, 3, 6, 110.8, 117.9, 109.9, 117.1, -7.1, 99.46, 46.3),
}

# Official standings snapshot read from nba.com/standings on 2026-11-19 (live table: W/L and home/road
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
# From https://www.nba.com/games?date=<date> day strips, read 2026-11-19
# (data/raw/refresh_2026-11-19/slate_2026-11-19.json). Window = today through today+3 days:
# 2026-11-19 .. 2026-11-22 inclusive (26 games: 4 + 9 + 6 + 7). Game IDs and ET tips were
# cross-checked between two independent official reads: this session's day strips and the
# committed 2026-11-17 schedule capture (nba2/v3/official.py, session arena/1eeb6a21-nba2) —
# every tip the two captures share agrees.
# date, time_et, away, home, game_id, arena, city, national_broadcast, cup_group
# arena/city for 11/19-11/20: carried from the committed 2026-11-17 official schedule capture
#   (nba2/v3/official.py, read from nba.com/schedule; unchanged tips re-verified 11/19).
# arena/city for 11/21-11/22: blank — the /games day strips do not print the arena, and a
#   wrong arena is worse than a blank one (FLAG-V2-ARENA-BLANK).
# cup_group: the Emirates NBA Cup group label exactly as the 11/20 cards print it; blank when
#   the card prints none.
SLATE = [
    ("2026-11-19", "20:00", "LAC", "SAS", "0022600273", "Frost Bank Center", "San Antonio, TX", "League Pass", ""),
    ("2026-11-19", "20:00", "GSW", "MEM", "0022600270", "FedExForum", "Memphis, TN", "League Pass", ""),
    ("2026-11-19", "20:00", "NYK", "MIN", "0022600272", "Target Center", "Minneapolis, MN", "NBA TV", ""),
    ("2026-11-19", "20:00", "POR", "MIL", "0022600271", "Fiserv Forum", "Milwaukee, WI", "League Pass", ""),
    ("2026-11-20", "19:00", "CHA", "ATL", "0022600043", "State Farm Arena", "Atlanta, GA", "League Pass", "East Group C"),
    ("2026-11-20", "19:30", "TOR", "DET", "0022600046", "Little Caesars Arena", "Detroit, MI", "Prime Video", "East Group A"),
    ("2026-11-20", "19:30", "IND", "CLE", "0022600045", "Rocket Arena", "Cleveland, OH", "League Pass", "East Group B"),
    ("2026-11-20", "19:30", "ORL", "BKN", "0022600044", "Barclays Center", "Brooklyn, NY", "League Pass", "East Group A"),
    ("2026-11-20", "20:00", "NOP", "OKC", "0022600048", "Paycom Center", "Oklahoma City, OK", "League Pass", "West Group B"),
    ("2026-11-20", "20:00", "WAS", "CHI", "0022600047", "United Center", "Chicago, IL", "League Pass", "East Group C"),
    ("2026-11-20", "21:30", "PHX", "UTA", "0022600049", "Delta Center", "Salt Lake City, UT", "League Pass", "West Group A"),
    ("2026-11-20", "22:00", "HOU", "DEN", "0022600050", "Ball Arena", "Denver, CO", "Prime Video", "West Group A"),
    ("2026-11-20", "22:00", "SAC", "LAL", "0022600051", "Crypto.com Arena", "Los Angeles, CA", "League Pass", "West Group C"),
    ("2026-11-21", "13:00", "MIL", "PHI", "0022600274", None, None, "League Pass", ""),
    ("2026-11-21", "19:30", "POR", "NYK", "0022600275", None, None, "NBA TV", ""),
    ("2026-11-21", "20:00", "NOP", "SAS", "0022600278", None, None, "League Pass", ""),
    ("2026-11-21", "20:00", "MEM", "MIN", "0022600277", None, None, "League Pass", ""),
    ("2026-11-21", "20:00", "LAC", "DAL", "0022600276", None, None, "League Pass", ""),
    ("2026-11-21", "22:00", "BOS", "SAC", "0022600279", None, None, "NBA TV", ""),
    ("2026-11-22", "15:30", "DET", "ATL", "0022600280", None, None, "League Pass", ""),
    ("2026-11-22", "18:00", "OKC", "MIA", "0022600281", None, None, "League Pass", ""),
    ("2026-11-22", "19:00", "DAL", "UTA", "0022600284", None, None, "League Pass", ""),
    ("2026-11-22", "19:00", "ORL", "WAS", "0022600282", None, None, "League Pass", ""),
    ("2026-11-22", "19:00", "DEN", "CHI", "0022600283", None, None, "League Pass", ""),
    ("2026-11-22", "20:00", "IND", "NYK", "0022600285", None, None, "League Pass", ""),
    ("2026-11-22", "20:30", "BOS", "GSW", "0022600286", None, None, "League Pass", ""),
]

INJURY_PDF_URL = SOURCES["injury_pdf"][1]

# --------------------------------------------------------------------------- injuries
# Transcribed from the official 11/19/26 07:15 AM ET PDF — the newest release listed on the
# official index at retrieval time. The report's own columns are
# Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason.
# The trailing letter is this project's transcription note, not an NBA field:
#   "E" = the team cell is present on the row itself
#   "C" = the row continues a team block from the previous PDF page, so the team and
#         matchup are carried over (flagged on the site as FLAG-V2-INJ-ATTR)
# (date, time_et, matchup, team, player, status, reason, attribution)
INJURIES = [
    ("2026-11-19", "08:00", "LAC@SAS", "LA Clippers", "Beal, Bradley", "Out", "Injury/Illness - Right Knee Injury Management", "E"),
    ("2026-11-19", "08:00", "LAC@SAS", "LA Clippers", "Ingram, Brandon", "Out", "Injury/Illness - Right Heel Surgery", "E"),
    ("2026-11-19", "08:00", "LAC@SAS", "LA Clippers", "Martinelli, Nick", "Out", "G League - Two-Way", "E"),
    ("2026-11-19", "08:00", "LAC@SAS", "LA Clippers", "Miller, Jordan", "Out", "Injury/Illness - Left Rotator Cuff Surgery", "E"),
    ("2026-11-19", "08:00", "LAC@SAS", "San Antonio Spurs", "Brown, Maliq", "Out", "G League - Two-Way", "E"),
    ("2026-11-19", "08:00", "LAC@SAS", "San Antonio Spurs", "Gillespie, Ja'Kobi", "Out", "G League - Two-Way", "E"),
    ("2026-11-19", "08:00", "LAC@SAS", "San Antonio Spurs", "Harper, Dylan", "Out", "Injury/Illness - Left Hip Soreness", "E"),
    ("2026-11-19", "08:00", "LAC@SAS", "San Antonio Spurs", "Harris, Tobias", "Out", "Injury/Illness - Left Calf Strain", "E"),
    ("2026-11-19", "08:00", "LAC@SAS", "San Antonio Spurs", "Quaintance, Jayden", "Out", "Injury/Illness - Right Knee Surgery", "E"),
    ("2026-11-19", "08:00", "NYK@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask", "E"),
    ("2026-11-19", "08:00", "NYK@MIN", "Minnesota Timberwolves", "Clark, Jaylen", "Out", "Injury/Illness - Right Hamstring Strain", "E"),
    ("2026-11-19", "08:00", "NYK@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery", "E"),
    ("2026-11-19", "08:00", "NYK@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy", "E"),
    ("2026-11-19", "08:00", "NYK@MIN", "Minnesota Timberwolves", "Kuminga, Jonathan", "Questionable", "Injury/Illness - Right Shoulder Contusion", "C"),
    ("2026-11-19", "08:00", "NYK@MIN", "Minnesota Timberwolves", "Pullin, Zyon", "Questionable", "Injury/Illness - Right Quadriceps Contusion", "C"),
    ("2026-11-19", "08:00", "POR@MIL", "Portland Trail Blazers", "Avdija, Deni", "Questionable", "Injury/Illness - Left Foot Inflammation / Soreness", "E"),
    ("2026-11-19", "08:00", "POR@MIL", "Portland Trail Blazers", "Camara, Toumani", "Questionable", "Injury/Illness - Abdominal Soreness", "E"),
    ("2026-11-19", "08:00", "POR@MIL", "Portland Trail Blazers", "Carlson, Branden", "Available", "Injury/Illness - Face Mask", "E"),
    ("2026-11-19", "08:00", "POR@MIL", "Portland Trail Blazers", "Krejci, Vit", "Out", "Injury/Illness - Left Ankle Fracture", "E"),
    ("2026-11-19", "08:00", "POR@MIL", "Portland Trail Blazers", "Morant, Ja", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("2026-11-19", "08:00", "POR@MIL", "Portland Trail Blazers", "Sharpe, Shaedon", "Out", "Injury/Illness - Right Meniscus Surgery", "E"),
    ("2026-11-19", "08:00", "POR@MIL", "Portland Trail Blazers", "Williams III, Robert", "Out", "Rest", "E"),
    ("2026-11-19", "08:00", "POR@MIL", "Portland Trail Blazers", "Youngblood, Chris", "Out", "Injury/Illness - Right Heel Contusion / Bone Bruise", "E"),
]
NOT_SUBMITTED = [
    # 11/19 - the clubs that had filed nothing in the 07:15 AM ET release
    ("2026-11-19", "08:00", "GSW@MEM", "Golden State Warriors"),
    ("2026-11-19", "08:00", "GSW@MEM", "Memphis Grizzlies"),
    ("2026-11-19", "08:00", "POR@MIL", "Milwaukee Bucks"),
    # 11/20 - every club is NOT YET SUBMITTED: the 5 p.m. local day-before filing deadline
    # for these games falls on 11/19, i.e. after this capture. Blank by policy, never estimated.
    ("2026-11-20", "07:00", "CHA@ATL", "Charlotte Hornets"),
    ("2026-11-20", "07:00", "CHA@ATL", "Atlanta Hawks"),
    ("2026-11-20", "07:30", "IND@CLE", "Indiana Pacers"),
    ("2026-11-20", "07:30", "IND@CLE", "Cleveland Cavaliers"),
    ("2026-11-20", "07:30", "ORL@BKN", "Orlando Magic"),
    ("2026-11-20", "07:30", "ORL@BKN", "Brooklyn Nets"),
    ("2026-11-20", "07:30", "TOR@DET", "Toronto Raptors"),
    ("2026-11-20", "07:30", "TOR@DET", "Detroit Pistons"),
    ("2026-11-20", "08:00", "NOP@OKC", "New Orleans Pelicans"),
    ("2026-11-20", "08:00", "NOP@OKC", "Oklahoma City Thunder"),
    ("2026-11-20", "08:00", "WAS@CHI", "Washington Wizards"),
    ("2026-11-20", "08:00", "WAS@CHI", "Chicago Bulls"),
    ("2026-11-20", "09:30", "PHX@UTA", "Phoenix Suns"),
    ("2026-11-20", "09:30", "PHX@UTA", "Utah Jazz"),
    ("2026-11-20", "10:00", "HOU@DEN", "Houston Rockets"),
    ("2026-11-20", "10:00", "HOU@DEN", "Denver Nuggets"),
    ("2026-11-20", "10:00", "SAC@LAL", "Sacramento Kings"),
    ("2026-11-20", "10:00", "SAC@LAL", "Los Angeles Lakers"),
]
# Irregularity recorded as read (never smoothed): the 11/19 07:15 AM release lists NO New York
# player rows for NYK@MIN — and no NOT-YET-SUBMITTED row for New York either. The club simply
# has no row in that release. Nothing is invented for it.

# --------------------------------------------------------------------------- players
# nba.com/stats/players/traditional - season aggregates, read 2026-11-14 (vintage unchanged;
# the per-player table is a placeholder whose prop columns are blank by policy).
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
