"""Official NBA snapshot for the v2 build — transcribed from pages fetched live on 2026-11-14.

Every number here was read off an NBA.com / NBA official-CDN page by session
``arena/6e7afc65-nba2`` on 2026-11-14 (UTC). Nothing is inferred, nothing is filled in.
The source URL for each field family is declared in ``SOURCES`` so every published row
can carry a link back to the page it came from.

Consolidation note (session ``arena/6650be4d-nba2``, 2026-11-14)
------------------------------------------------------------------
The slate, the standings, the newest injury release and the 2026-11-13 finals are no
longer transcribed twice: they are READ from the committed official snapshots in
``data/raw/`` so that the published tree and the repository's audit trail cannot drift
apart. What remains transcribed here is the part of the official tables that is dated
2026-11-13 (the scoring averages and the advanced ratings) — those pages were read
before the nine 2026-11-13 games were played and could not be re-read in this session
without re-fetching three more pages; they are labelled as 2026-11-13 everywhere they
are published, and the current official records are published beside them from
``data/raw/official_standings_2026-11-14.json``.

Retrieval record
----------------
* ``www.nba.com/standings`` ............. 30 teams, W/L, home/road splits  → fetched OK
* ``www.nba.com/stats/teams/traditional`` 30 teams, GP/W/L/MIN/PTS          → fetched OK
* ``www.nba.com/stats/teams/opponent`` .... 30 teams, opponent PTS          → fetched OK
* ``www.nba.com/stats/teams/advanced`` .... 30 teams, OffRtg/DefRtg/NetRtg/Pace/PIE → fetched OK
* ``www.nba.com/schedule`` ................ slate 11/13→11/16, times, arenas, IDs → fetched OK
* ``ak-static.cms.nba.com/...Injury-Report_2026-11-13_04_15PM.pdf`` 95 rows  → fetched OK
* ``official.nba.com/nba-injury-report-2026-27-season/``  index of report PDFs → fetched OK
* ``www.nba.com/stats/players/traditional`` per-player PPG/RPG/APG (top rows) → fetched OK
* 2026-11-14 01:00 PM ET injury report PDF ............................ AccessDenied
* ``stats.nba.com`` JSON endpoints, ``cdn.nba.com`` JSON ................ TLS blocked
* Basketball-Reference 2026-27 *team game logs* ........................ 404 (no game log published)

Team-level *game-by-game* data (margins, totals per game, player box scores) is therefore
NOT available to this build. Anything that needs it is published as BLOCKED, never guessed.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"

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
    "ATL": (7, 5, 3, 3, 4, 2, 118.3, 116.2, 114.3, 112.2, 2.1, 103.46, 48.9),
    "BOS": (10, 2, 5, 0, 5, 2, 114.3, 103.1, 117.4, 105.6, 11.7, 96.62, 55.9),
    "BKN": (3, 8, 1, 3, 2, 5, 110.2, 115.3, 109.3, 114.4, -5.2, 99.83, 47.0),
    "CHA": (4, 8, 3, 4, 1, 4, 98.6, 109.6, 101.8, 113.0, -11.2, 96.92, 42.9),
    "CHI": (1, 9, 0, 4, 1, 5, 113.3, 128.8, 109.2, 124.2, -15.1, 103.75, 42.7),
    "CLE": (6, 6, 4, 2, 2, 4, 116.4, 114.3, 115.6, 113.6, 2.1, 99.80, 51.4),
    "DAL": (7, 5, 5, 2, 2, 3, 113.2, 112.2, 112.5, 111.7, 0.8, 100.50, 50.3),
    "DEN": (6, 4, 2, 2, 3, 2, 114.5, 113.3, 115.9, 115.1, 0.7, 97.58, 52.2),
    "DET": (8, 3, 3, 2, 5, 1, 115.5, 107.8, 114.1, 106.9, 7.2, 99.17, 55.3),
    "GSW": (8, 4, 6, 1, 2, 3, 119.3, 111.5, 118.4, 110.9, 7.5, 99.76, 53.8),
    "HOU": (9, 3, 6, 1, 3, 2, 115.4, 106.5, 118.5, 109.3, 9.2, 97.42, 55.8),
    "IND": (4, 8, 1, 4, 3, 3, 111.6, 114.0, 110.6, 112.5, -1.9, 101.13, 49.6),
    "LAC": (2, 8, 2, 3, 0, 5, 112.2, 118.1, 110.0, 115.8, -5.8, 100.95, 47.1),
    "LAL": (11, 2, 5, 1, 6, 1, 122.2, 114.2, 121.6, 113.6, 8.0, 100.50, 54.2),
    "MEM": (7, 4, 2, 4, 5, 0, 117.9, 111.9, 116.4, 110.6, 5.8, 100.28, 52.1),
    "MIA": (5, 6, 1, 3, 4, 3, 115.7, 120.0, 111.3, 115.9, -4.6, 102.80, 48.2),
    "MIL": (1, 11, 1, 6, 0, 5, 106.8, 121.3, 106.2, 120.7, -14.5, 100.50, 42.1),
    "MIN": (9, 3, 5, 1, 4, 2, 119.3, 105.9, 117.2, 103.8, 13.4, 101.08, 56.1),
    "NOP": (4, 8, 3, 4, 1, 4, 116.9, 124.3, 112.1, 119.2, -7.1, 101.64, 47.1),
    "NYK": (6, 5, 4, 3, 2, 2, 110.3, 103.5, 115.7, 109.0, 6.7, 95.09, 53.6),
    "OKC": (8, 4, 5, 0, 3, 4, 111.1, 106.9, 112.5, 108.3, 4.2, 98.75, 53.6),
    "ORL": (4, 7, 0, 4, 4, 3, 108.5, 114.0, 109.7, 114.6, -5.0, 98.25, 46.7),
    "PHI": (10, 3, 5, 2, 5, 1, 111.2, 109.4, 111.0, 109.5, 1.5, 100.04, 50.9),
    "PHX": (5, 6, 5, 3, 0, 3, 111.7, 116.1, 113.8, 117.6, -3.8, 98.45, 48.1),
    "POR": (8, 3, 3, 2, 5, 1, 119.5, 112.3, 118.5, 111.4, 7.1, 100.86, 53.3),
    "SAC": (1, 10, 0, 6, 1, 4, 108.3, 121.0, 107.2, 119.3, -12.1, 101.23, 42.5),
    "SAS": (10, 2, 4, 2, 6, 0, 119.2, 108.0, 119.3, 108.3, 11.0, 98.97, 55.4),
    "TOR": (5, 7, 2, 3, 3, 4, 114.3, 112.8, 114.5, 112.8, 1.7, 99.88, 49.3),
    "UTA": (1, 11, 1, 6, 0, 5, 106.6, 118.1, 103.8, 115.4, -11.6, 100.75, 45.4),
    "WAS": (4, 9, 2, 3, 2, 6, 110.0, 115.8, 108.7, 114.3, -5.5, 99.63, 47.1),
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

# Per-team source links (each page is the canonical official page for that team's stats).
TEAM_SOURCE = {
    tid: "https://www.nba.com/stats/team/{}".format(tid) for tid in TEAMS
}

# --------------------------------------------------------------------------- the slate
# The slate is no longer transcribed here: it is READ from the committed official snapshot
# data/raw/slate_2026-11-14_to_11-17.json (36 games: 9 day-before context games on
# 2026-11-13 plus the 27-game pick window 2026-11-14 .. 2026-11-17, which is the build
# date + 3 days). See the loaders at the foot of this module.

# --------------------------------------------------------------------------- injuries
# Full 95-row transcription of the 11/13/26 04:15 PM ET report — matches the committed
# snapshot data/raw/injury_report_2026-11-13.json row for row (verified this session).
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


# --------------------------------------------------------------------------- committed official snapshots
# Session arena/6650be4d-nba2 (2026-11-14). The published tree reads the slate, the current
# standings, the newest injury release and the played finals from the committed snapshots so
# that the site and the repository's audit trail are the same numbers.

def _load(name: str) -> dict:
    return json.loads((RAW / name).read_text())


def _rows(doc: dict) -> list[dict]:
    return [dict(zip(doc["columns"], r)) for r in doc["records"]]


# ---- the slate: 36 games, 2026-11-13 (day-before context) .. 2026-11-17 (T+3)
_SLATE_DOC = _load("slate_2026-11-14_to_11-17.json")
SLATE = [(r["date"], r["time_et"], r["away"], r["home"], r["game_id"], r["arena"],
          f"{r['city']}, {r['state']}", r["broadcast"], r["cup_group"])
         for r in _rows(_SLATE_DOC)]
CONTEXT_DATE = "2026-11-13"
WINDOW_DATES = sorted({r[0] for r in SLATE if r[0] > CONTEXT_DATE})
SLATE_SOURCE = "https://www.nba.com/schedule"


def slate_by_date(date: str) -> list[tuple]:
    return [r for r in SLATE if r[0] == date]


# ---- the official standings, read from nba.com/standings on 2026-11-14
_STANDINGS_DOC = _load("official_standings_2026-11-14.json")
STANDINGS = {r["tricode"]: r for r in _rows(_STANDINGS_DOC)}
STANDINGS_SOURCE = "https://www.nba.com/standings"
STANDINGS_AS_OF = _STANDINGS_DOC.get("as_of", "2026-11-14")


def standings_rows() -> list[dict]:
    out = []
    for tri in sorted(STANDINGS):
        d = STANDINGS[tri]
        g = d["w"] + d["l"]
        out.append({"tricode": tri, "name": d["name"], "w": d["w"], "l": d["l"],
                    "pct": round(d["w"] / g, 3) if g else None,
                    "home": d["home"], "road": d["road"], "conf": d["conf"], "div": d["div"]})
    return out


# ---- the newest official injury release (2026-11-14 05:00 a.m ET)
_INJ_DOC = _load("injury_report_2026-11-14_0500ET.json")
INJURIES_LATEST = [(r["game_date"], r["time_et"], r["matchup"], r["team"], r["player"],
                    r["status"], r["reason"], r["attribution"]) for r in _rows(_INJ_DOC)]
INJURIES_LATEST_RELEASE = _INJ_DOC.get("release", "2026-11-14 05:00 a.m ET")
INJURIES_LATEST_SOURCE = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf"

# ---- the official finals for the nine 2026-11-13 games
_FINALS_DOC = _load("finals_2026-11-13.json")
FINALS = {r["game_id"]: r for r in _FINALS_DOC["records"]}
FINALS_SOURCE = "https://www.nba.com/schedule?date=2026-11-14"
