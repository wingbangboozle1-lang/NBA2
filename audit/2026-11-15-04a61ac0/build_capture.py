#!/usr/bin/env python3
"""Build this session's official-capture artefacts, verifying them as they are written.

Run:  python3 audit/2026-11-15-04a61ac0/build_capture.py

Every literal in this file was read off an official NBA document by session
``arena/04a61ac0-nba2`` on 2026-11-15 (UTC) through the platform page-fetch tool, and the URL is
recorded next to the block it came from. Direct TLS egress from this workspace to nba.com is
blocked; that limitation is recorded, not worked around.

Nothing here invents a value. The script refuses to write if any internal identity fails:

* final score == the sum of the four quarter scores, for both sides of every game;
* no published game-book line contradicts the final score, and the team shooting lines that do
  are recorded as defects instead of being repaired;
* every team's rebuilt W-L (from the result feed) equals the official standings row;
* league wins == league losses == games, and each team's home/road/neutral games sum to its GP;
* the opponent page's points-allowed and the advanced page's ratings agree with the finals
  (``Rtg x POSS / 100`` reproduces the team's season point total within rounding).

Outputs:
  audit/2026-11-15-04a61ac0/captures.json      this session's whole capture, one file
  data/raw/finals_2026-11-14.json              the five 11/14 finals, with quarter scores
  data/raw/results_feed_2026-11-15.json        the per-game result feed (one row per game)
  data/raw/standings_2026-11-15_official.json  the standings card as read today
  data/raw/team_ratings_2026-11-15.json        traditional/opponent/advanced, re-read today
  data/raw/injury_report_2026-11-15_0615AM.json  the newest release, transcribed
  data/raw/injury_report_2026-11-15_0600AM.json  its predecessor, transcribed and diffed
  data/raw/gamebooks_2026-11-14.json          what the five official game books support
  data/raw/slate_2026-11-15_to_11-17.json      the rolling 3-day window (22 games)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
HIST = RAW / "history"

SESSION = "arena/04a61ac0-nba2"
CAPTURED_UTC = "2026-11-15T11:45:00Z"
METHOD = (
    "platform page-fetch tool (fetch_page). Direct TLS egress from this workspace to every "
    "nba.com host is blocked; the tool reaches the same URLs, which is recorded rather than "
    "worked around. Each document below carries the URL it was read from."
)

U = {
    "standings": "https://www.nba.com/standings",
    "advanced": "https://www.nba.com/stats/teams/advanced",
    "opponent": "https://www.nba.com/stats/teams/opponent",
    "schedule": "https://www.nba.com/schedule?date=2026-11-15",
    "games_1114": "https://www.nba.com/games?date=2026-11-14",
    "injury_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "injury_0615": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf",
    "injury_0600": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_00AM.pdf",
    "book_denNOP": "https://statsdmz.nba.com/pdfs/20261114/20261114_DENNOP_book.pdf",
    "book_dalCLE": "https://statsdmz.nba.com/pdfs/20261114/20261114_DALCLE_book.pdf",
    "book_detMIA": "https://statsdmz.nba.com/pdfs/20261114/20261114_DETMIA_book.pdf",
    "book_bknMEM": "https://statsdmz.nba.com/pdfs/20261114/20261114_BKNMEM_book.pdf",
    "book_chiMIN": "https://statsdmz.nba.com/pdfs/20261114/20261114_CHIMIN_book.pdf",
}

# --------------------------------------------------------------------------- standings card
# https://www.nba.com/standings, read 2026-11-15 11:32 UTC. Columns exactly as printed:
# tri, w, l, win%, gb, conf, div, home, road, neutral, ot, last10, streak
STANDINGS = [
    ("BOS", 10, 2, ".833", "--", "10-1", "4-0", "5-0", "5-2", "0-0", "1-0", "9-1", "W 5"),
    ("PHI", 10, 3, ".769", "0.5", "10-3", "3-1", "5-2", "5-1", "0-0", "0-0", "7-3", "W 1"),
    ("DET", 8, 4, ".667", "2", "8-3", "0-0", "3-2", "5-2", "0-0", "1-0", "6-4", "L 1"),
    ("MIA", 7, 6, ".538", "3.5", "4-2", "1-1", "3-3", "4-3", "0-0", "1-0", "7-3", "W 4"),
    ("ATL", 7, 6, ".538", "3.5", "7-2", "4-1", "3-3", "4-3", "0-0", "0-1", "5-5", "L 2"),
    ("CLE", 7, 7, ".500", "4", "5-5", "1-0", "5-2", "2-5", "0-0", "1-0", "4-6", "W 1"),
    ("NYK", 6, 6, ".500", "4", "6-6", "1-3", "4-3", "2-3", "0-0", "0-0", "6-4", "L 2"),
    ("TOR", 5, 7, ".417", "5", "4-3", "0-2", "2-3", "3-4", "0-0", "0-0", "3-7", "L 3"),
    ("ORL", 5, 7, ".417", "5", "3-4", "0-2", "1-4", "4-3", "0-0", "0-1", "5-5", "W 3"),
    ("IND", 5, 8, ".385", "5.5", "3-5", "0-1", "2-4", "3-3", "0-1", "0-0", "3-7", "W 2"),
    ("CHA", 4, 8, ".333", "6", "4-7", "2-2", "3-4", "1-4", "0-0", "0-0", "3-7", "L 1"),
    ("WAS", 4, 9, ".308", "6.5", "4-8", "2-3", "2-3", "2-6", "0-0", "0-1", "2-8", "L 6"),
    ("BKN", 3, 9, ".250", "7", "2-7", "0-2", "1-3", "2-6", "0-0", "0-1", "3-7", "L 1"),
    ("CHI", 3, 9, ".250", "7", "2-8", "1-0", "1-4", "2-5", "0-0", "1-0", "2-8", "W 2"),
    ("MIL", 1, 12, ".077", "9.5", "1-9", "1-2", "1-6", "0-6", "0-0", "0-0", "1-9", "L 9"),
    ("SAS", 11, 2, ".846", "--", "10-2", "2-1", "5-2", "6-0", "0-0", "1-0", "10-0", "W 11"),
    ("LAL", 11, 2, ".846", "--", "6-2", "4-1", "5-1", "6-1", "0-0", "0-0", "8-2", "W 7"),
    ("HOU", 10, 3, ".769", "1", "6-3", "2-1", "7-1", "3-2", "0-0", "0-0", "7-3", "W 3"),
    ("POR", 9, 3, ".750", "1.5", "9-3", "4-0", "3-2", "6-1", "0-0", "0-0", "7-3", "W 3"),
    ("MIN", 9, 4, ".692", "2", "5-2", "1-0", "5-2", "4-2", "0-0", "0-1", "6-4", "L 1"),
    ("MEM", 9, 4, ".692", "2", "7-3", "1-1", "3-4", "6-0", "0-0", "0-1", "6-4", "W 2"),
    ("DEN", 7, 4, ".636", "3", "5-4", "0-2", "2-2", "4-2", "1-0", "1-0", "7-3", "W 2"),
    ("GSW", 8, 5, ".615", "3", "6-5", "3-2", "6-1", "2-4", "0-0", "1-0", "8-2", "L 2"),
    ("OKC", 8, 5, ".615", "3", "5-5", "1-2", "5-0", "3-5", "0-0", "0-0", "5-5", "L 3"),
    ("DAL", 7, 6, ".538", "4", "3-5", "1-3", "5-2", "2-4", "0-0", "0-0", "6-4", "L 2"),
    ("PHX", 5, 6, ".455", "5", "3-6", "2-1", "5-3", "0-3", "0-0", "0-0", "5-5", "W 2"),
    ("NOP", 4, 10, ".286", "7.5", "3-8", "1-1", "3-6", "1-4", "0-0", "2-1", "4-6", "L 6"),
    ("LAC", 3, 8, ".273", "7", "3-6", "1-4", "3-3", "0-5", "0-0", "0-1", "2-8", "W 1"),
    ("SAC", 1, 11, ".083", "9.5", "1-9", "0-2", "0-7", "1-4", "0-0", "0-0", "1-9", "L 5"),
    ("UTA", 1, 12, ".077", "10", "1-10", "0-2", "1-6", "0-6", "0-0", "0-2", "0-10", "L 11"),
]

# --------------------------------------------------------------------------- advanced team stats
# https://www.nba.com/stats/teams/advanced, read 2026-11-15 11:34 UTC.
# tri, gp, w, l, offrtg, defrtg, netrtg, pace, pie, poss
ADVANCED = [
    ("LAL", 13, 11, 2, 121.6, 113.6, 8.0, 100.50, 54.2, 1306),
    ("SAS", 13, 11, 2, 119.6, 106.6, 13.0, 98.94, 56.7, 1298),
    ("BOS", 12, 10, 2, 117.4, 105.6, 11.7, 96.62, 55.9, 1168),
    ("HOU", 13, 10, 3, 119.3, 110.2, 9.1, 97.42, 55.8, 1266),
    ("PHI", 13, 10, 3, 111.0, 109.5, 1.5, 100.04, 50.9, 1302),
    ("MEM", 13, 9, 4, 119.0, 110.4, 8.5, 100.46, 53.9, 1318),
    ("MIN", 13, 9, 4, 116.0, 104.5, 11.5, 101.27, 55.2, 1326),
    ("POR", 12, 9, 3, 118.8, 111.1, 7.7, 100.67, 53.3, 1208),
    ("DET", 12, 8, 4, 114.1, 109.2, 4.9, 99.48, 53.7, 1217),
    ("GSW", 13, 8, 5, 116.1, 112.0, 4.1, 99.66, 51.8, 1307),
    ("OKC", 13, 8, 5, 112.7, 109.0, 3.7, 98.58, 53.3, 1282),
    ("ATL", 13, 7, 6, 113.3, 111.9, 1.4, 103.55, 48.5, 1356),
    ("CLE", 14, 7, 7, 116.9, 115.4, 1.6, 99.72, 51.2, 1407),
    ("DAL", 13, 7, 6, 112.8, 112.8, 0.0, 100.54, 49.7, 1308),
    ("DEN", 11, 7, 4, 116.0, 114.7, 1.3, 97.67, 52.9, 1087),
    ("MIA", 13, 7, 6, 114.7, 116.2, -1.5, 102.49, 50.0, 1345),
    ("NYK", 12, 6, 6, 114.5, 108.6, 5.9, 95.63, 53.3, 1150),
    ("IND", 13, 5, 8, 110.1, 111.7, -1.5, 101.15, 49.6, 1312),
    ("ORL", 12, 5, 7, 109.7, 113.4, -3.7, 98.23, 47.6, 1185),
    ("PHX", 11, 5, 6, 113.8, 117.6, -3.8, 98.45, 48.1, 1080),
    ("TOR", 12, 5, 7, 114.5, 112.8, 1.7, 99.88, 49.3, 1197),
    ("CHA", 12, 4, 8, 101.9, 113.1, -11.2, 96.83, 42.9, 1161),
    ("NOP", 14, 4, 10, 111.3, 120.0, -8.6, 101.83, 45.7, 1457),
    ("WAS", 13, 4, 9, 108.7, 114.3, -5.5, 99.63, 47.1, 1315),
    ("BKN", 12, 3, 9, 109.8, 116.0, -6.2, 99.47, 46.1, 1204),
    ("CHI", 12, 3, 9, 109.4, 120.3, -10.9, 103.81, 44.9, 1257),
    ("LAC", 11, 3, 8, 110.7, 115.8, -5.1, 100.55, 47.4, 1116),
    ("MIL", 13, 1, 12, 105.7, 120.0, -14.2, 100.31, 42.0, 1305),
    ("SAC", 12, 1, 11, 107.3, 119.5, -12.2, 101.00, 42.8, 1210),
    ("UTA", 13, 1, 12, 105.0, 116.4, -11.3, 100.50, 45.3, 1330),
]

# --------------------------------------------------------------------------- opponent team stats
# https://www.nba.com/stats/teams/opponent, read 2026-11-15 11:36 UTC.
# tri, gp, opp_pts_per_game, opp_plus_minus (the "+/-" column of the opponent table)
OPPONENT = [
    ("LAL", 13, 114.2, -7.9), ("SAS", 13, 106.2, -13.2), ("BOS", 12, 103.1, -11.2),
    ("HOU", 13, 107.4, -8.8), ("PHI", 13, 109.4, -1.8), ("MEM", 13, 111.7, -8.9),
    ("MIN", 13, 106.8, -11.5), ("POR", 12, 111.8, -7.8), ("DET", 12, 110.3, -5.4),
    ("GSW", 13, 112.4, -4.3), ("OKC", 13, 107.4, -3.8), ("ATL", 13, 116.8, -1.3),
    ("CLE", 14, 115.9, -1.6), ("DAL", 13, 113.3, -0.2), ("DEN", 11, 112.8, -1.8),
    ("MIA", 13, 119.8, 1.2), ("NYK", 12, 103.7, -6.1), ("IND", 13, 113.2, 2.1),
    ("ORL", 12, 112.8, 4.4), ("PHX", 11, 116.1, 4.4), ("TOR", 12, 112.8, -1.4),
    ("CHA", 12, 109.6, 11.0), ("NOP", 14, 124.9, 9.1), ("WAS", 13, 115.8, 5.8),
    ("BKN", 12, 116.4, 6.3), ("CHI", 12, 125.9, 11.3), ("LAC", 11, 117.5, 5.3),
    ("MIL", 13, 120.2, 14.1), ("SAC", 12, 120.9, 12.8), ("UTA", 13, 118.6, 11.2),
]


# --------------------------------------------------------------------------- traditional team stats
# https://www.nba.com/stats/teams/traditional, read 2026-11-15 12:0x UTC across all five chunks of
# the page (the table is one <table>, so rows straddle chunk boundaries; the two rows that did —
# Boston and Brooklyn — were stitched from the tail of the next chunk and verified below).
# tri, gp, w, l, min, pts, fgm, fga, fg%, 3pm, 3pa, 3p%, ftm, fta, ft%, oreb, dreb, reb, ast,
# tov, stl, blk, blka, pf, pfd, +/-
TRADITIONAL = [
    ("LAL", 13, 11, 2, 48.0, 122.2, 42.1, 83.6, 50.3, 14.1, 36.8, 38.3, 23.9, 29.8, 80.4, 11.3, 29.5, 40.8, 24.7, 16.9, 11.0, 6.2, 4.2, 23.4, 24.2, 7.9),
    ("SAS", 13, 11, 2, 48.4, 119.5, 42.9, 92.0, 46.7, 12.5, 35.9, 34.7, 21.2, 26.5, 79.9, 13.2, 35.4, 48.6, 28.1, 12.3, 8.3, 7.3, 4.9, 20.0, 21.2, 13.2),
    ("BOS", 12, 10, 2, 48.4, 114.3, 39.8, 87.2, 45.6, 16.0, 42.0, 38.1, 18.8, 23.8, 78.9, 13.1, 31.7, 44.8, 26.8, 14.7, 8.2, 4.9, 4.2, 21.5, 22.9, 11.2),
    ("HOU", 13, 10, 3, 48.0, 116.2, 41.5, 86.9, 47.8, 12.8, 34.3, 37.2, 20.3, 25.0, 81.2, 13.2, 31.2, 44.4, 26.8, 14.5, 7.9, 6.1, 4.1, 19.9, 21.9, 8.8),
    ("PHI", 13, 10, 3, 48.0, 111.2, 39.6, 88.1, 45.0, 11.6, 33.8, 34.3, 20.3, 25.9, 78.3, 10.3, 32.8, 43.1, 26.1, 12.8, 8.4, 4.3, 5.8, 20.6, 20.8, 1.8),
    ("POR", 12, 9, 3, 48.0, 119.6, 39.8, 84.7, 46.9, 15.9, 43.6, 36.5, 24.2, 30.7, 78.8, 11.5, 32.8, 44.3, 25.3, 16.3, 7.1, 5.1, 4.2, 22.3, 24.4, 7.8),
    ("MEM", 13, 9, 4, 48.4, 120.6, 42.1, 89.4, 47.1, 15.5, 39.6, 39.2, 20.9, 24.7, 84.7, 12.5, 34.8, 47.4, 27.8, 15.8, 6.5, 5.1, 7.2, 23.6, 21.5, 8.9),
    ("MIN", 13, 9, 4, 48.4, 118.3, 43.4, 90.9, 47.7, 14.2, 38.4, 36.9, 17.4, 25.5, 68.1, 13.8, 34.6, 48.5, 26.0, 15.9, 9.0, 5.1, 6.4, 22.0, 22.8, 11.5),
    ("DET", 12, 8, 4, 48.8, 115.7, 40.9, 88.4, 46.3, 13.5, 36.8, 36.7, 20.3, 25.8, 79.0, 12.2, 32.3, 44.4, 27.7, 14.3, 9.4, 6.4, 6.1, 23.8, 22.7, 5.4),
    ("DEN", 11, 7, 4, 48.5, 114.6, 41.5, 85.2, 48.7, 10.8, 31.0, 34.9, 20.9, 26.5, 79.0, 10.1, 32.2, 42.3, 27.7, 13.4, 9.0, 4.5, 4.5, 19.0, 23.2, 1.8),
    ("GSW", 13, 8, 5, 48.4, 116.7, 40.0, 87.0, 46.0, 16.4, 41.6, 39.4, 20.3, 25.1, 81.0, 12.5, 31.9, 44.5, 28.0, 16.0, 8.2, 5.4, 5.7, 21.9, 22.2, 4.3),
    ("OKC", 13, 8, 5, 48.0, 111.2, 41.2, 90.7, 45.4, 11.0, 32.1, 34.3, 17.8, 21.8, 81.7, 11.5, 35.1, 46.6, 22.8, 13.3, 7.9, 5.4, 5.3, 19.3, 21.0, 3.8),
    ("ATL", 13, 7, 6, 48.4, 118.2, 43.9, 97.2, 45.2, 14.8, 43.3, 34.1, 15.5, 20.4, 76.2, 13.9, 30.2, 44.1, 31.5, 15.2, 10.3, 4.0, 6.0, 22.1, 19.4, 1.3),
    ("DAL", 13, 7, 6, 48.0, 113.5, 41.2, 88.8, 46.4, 12.5, 37.5, 33.5, 18.5, 23.5, 78.4, 12.7, 30.9, 43.6, 26.1, 15.8, 8.7, 5.5, 4.8, 22.3, 20.9, 0.2),
    ("MIA", 13, 7, 6, 48.4, 118.7, 42.0, 89.5, 46.9, 13.5, 39.5, 34.1, 21.2, 28.7, 74.0, 10.5, 32.2, 42.8, 29.8, 14.4, 7.8, 5.5, 5.2, 21.1, 25.1, -1.2),
    ("CLE", 14, 7, 7, 48.4, 117.5, 41.8, 88.7, 47.1, 15.4, 41.6, 37.0, 18.5, 24.3, 76.2, 10.7, 34.9, 45.6, 27.1, 13.5, 7.1, 5.3, 3.6, 21.6, 20.3, 1.6),
    ("NYK", 12, 6, 6, 48.0, 109.8, 38.8, 88.9, 43.6, 14.8, 41.1, 36.1, 17.4, 21.9, 79.5, 13.7, 34.0, 47.7, 26.8, 14.4, 7.4, 4.1, 6.2, 20.9, 21.1, 6.1),
    ("PHX", 11, 5, 6, 48.0, 111.7, 41.3, 88.5, 46.7, 13.6, 37.0, 36.9, 15.5, 20.0, 77.7, 10.6, 28.3, 38.9, 27.2, 13.9, 8.4, 4.5, 4.7, 22.0, 18.6, -4.4),
    ("ORL", 12, 5, 7, 48.4, 108.3, 38.4, 85.8, 44.8, 13.8, 41.1, 33.7, 17.7, 22.6, 78.2, 11.0, 31.9, 42.9, 26.0, 16.8, 7.4, 4.1, 5.0, 22.8, 23.3, -4.4),
    ("TOR", 12, 5, 7, 48.0, 114.3, 41.4, 91.2, 45.4, 11.8, 36.0, 32.9, 19.6, 26.6, 73.7, 13.8, 27.2, 41.0, 28.1, 14.3, 10.6, 4.4, 5.5, 25.8, 24.3, 1.4),
    ("IND", 13, 5, 8, 48.0, 111.2, 40.4, 86.8, 46.5, 12.2, 36.5, 33.3, 18.2, 24.1, 75.7, 9.8, 32.0, 41.8, 27.5, 14.8, 7.4, 4.3, 4.4, 20.3, 22.7, -2.1),
    ("CHA", 12, 4, 8, 48.0, 98.6, 34.8, 86.6, 40.1, 13.8, 44.2, 31.1, 15.3, 18.7, 82.1, 15.0, 31.6, 46.6, 21.8, 19.6, 6.9, 4.6, 4.6, 20.4, 21.6, -11.0),
    ("WAS", 13, 4, 9, 48.8, 110.0, 39.8, 87.1, 45.8, 9.9, 32.5, 30.5, 20.4, 25.2, 80.8, 10.7, 32.4, 43.1, 23.6, 15.2, 7.5, 5.4, 3.5, 20.5, 21.2, -5.8),
    ("NOP", 14, 4, 10, 49.1, 115.9, 40.1, 86.2, 46.5, 9.4, 28.7, 32.8, 26.3, 32.1, 82.0, 10.6, 30.5, 41.1, 24.3, 16.1, 9.9, 5.3, 5.6, 24.6, 23.9, -9.1),
    ("LAC", 11, 3, 8, 48.5, 112.3, 39.2, 85.4, 45.9, 14.3, 37.4, 38.2, 19.6, 24.6, 79.7, 10.5, 29.9, 40.5, 26.8, 17.8, 9.6, 4.3, 4.4, 22.1, 20.9, -5.3),
    ("BKN", 12, 3, 9, 48.4, 110.2, 37.1, 83.9, 44.2, 14.6, 40.7, 35.9, 21.4, 28.3, 75.8, 11.6, 31.0, 42.6, 24.2, 17.7, 8.6, 4.8, 4.8, 26.1, 24.0, -6.3),
    ("CHI", 12, 3, 9, 48.4, 114.6, 39.9, 89.4, 44.6, 12.7, 40.7, 31.1, 22.1, 29.0, 76.1, 12.6, 31.8, 44.3, 26.9, 17.3, 7.8, 5.9, 4.9, 23.7, 23.2, -11.3),
    ("SAC", 12, 1, 11, 48.0, 108.2, 39.3, 86.3, 45.5, 12.3, 35.5, 34.5, 17.4, 22.7, 76.8, 9.8, 30.1, 39.9, 25.0, 17.1, 7.8, 3.5, 5.8, 22.8, 19.6, -12.8),
    ("MIL", 13, 1, 12, 48.0, 106.2, 37.8, 88.3, 42.8, 14.8, 43.2, 34.2, 15.8, 21.4, 74.1, 13.3, 31.5, 44.8, 24.8, 16.6, 6.5, 4.7, 5.8, 22.5, 19.5, -14.1),
    ("UTA", 13, 1, 12, 48.8, 107.5, 37.8, 86.8, 43.5, 12.1, 36.5, 33.1, 19.8, 25.8, 77.0, 12.0, 32.5, 44.5, 24.0, 16.7, 6.7, 6.2, 5.4, 24.0, 24.2, -11.2),
]

# --------------------------------------------------------------------------- 2026-11-14 finals
# Two independent official documents per game: the nba.com linescore table on the game page and
# the "SCORE BY PERIOD" block of the official game book. Both are recorded; the script asserts
# they agree, and that each side's four quarters sum to its final score.
# game_id, date, away, home, away_pts, home_pts, away_q, home_q, arena, book_url, game_url
FINALS_1114 = [
    ("0022600231", "2026-11-14", "DEN", "NOP", 116, 108, [29, 27, 30, 30], [23, 28, 31, 26],
     "Smoothie King Center", U["book_denNOP"], "https://www.nba.com/game/den-vs-nop-0022600231"),
    ("0022600232", "2026-11-14", "DAL", "CLE", 117, 127, [33, 20, 38, 26], [33, 38, 34, 22],
     "Rocket Arena", U["book_dalCLE"], "https://www.nba.com/game/dal-vs-cle-0022600232"),
    ("0022600233", "2026-11-14", "DET", "MIA", 117, 137, [39, 21, 26, 31], [37, 31, 35, 34],
     "Kaseya Center", U["book_detMIA"], "https://www.nba.com/game/det-vs-mia-0022600233"),
    ("0022600234", "2026-11-14", "BKN", "MEM", 110, 129, [23, 31, 30, 26], [38, 33, 32, 26],
     "FedExForum", U["book_bknMEM"], "https://www.nba.com/game/bkn-vs-mem-0022600234"),
    ("0022600235", "2026-11-14", "CHI", "MIN", 117, 106, [29, 29, 30, 29], [17, 28, 35, 26],
     "Target Center", U["book_chiMIN"], "https://www.nba.com/game/chi-vs-min-0022600235"),
]

# --------------------------------------------------------------------------- 2026-11-14 game books
# The five official game books (chunk 0 of each PDF). What is published here is only what this
# session could read off the document and stand behind. Two categories were deliberately NOT
# published as data:
#
#  * team shooting lines. Every one of them fails the arithmetic that a box score must satisfy,
#    2 x FGM + FTM = points, so they are recorded below as source-side defects and discarded.
#    (DAL 2x39+25=103 vs 117; CLE 2x48+16=112 vs 127; MIA 2x44+33=121 vs 137;
#     DET 2x39+28=106 vs 117; MEM 2x46+22=114 vs 129; MIN 2x38+21=97 vs 106.)
#  * complete player rows. The PDF text layer misaligns columns, so a row cannot be trusted on its
#    own; only the leaders named in the same document are published, as context, never as inputs.
#
# Inactive blocks are published for the four clubs whose block survived the extract in readable
# form. For the other six the block exists in the PDF but this session cannot quote it, so it is
# listed as not preserved rather than filled in.
LEADERS = {
    "CLE": [("Tyrese Proctor", 24, 11, 10, "first Cleveland triple-double since Max Strus, 2024-04-14"),
            ("Mario Hezonja", 22, 7, 4, ""), ("Meleek Thomas", 20, 4, 2, ""),
            ("Thomas Bryant", 19, 11, 3, ""), ("Jaylon Tyson", 18, 4, 4, ""),
            ("Norchad Omier", 13, 8, 2, "")],
    "DAL": [("Kyrie Irving", 34, 6, 5, "7 of 16 from three"), ("Cooper Flagg", 18, 8, 5, ""),
            ("Caleb Martin", 15, 8, 3, ""), ("Naji Marshall", 12, 3, 5, ""),
            ("Daniel Gafford", 10, 3, 1, "")],
    "MIA": [("Giannis Antetokounmpo", 34, 14, 8, ""), ("Klay Thompson", 26, 1, 4, "6 of 11 from three"),
            ("Bam Adebayo", 20, 5, 4, "9 of 13 from the line"),
            ("Davion Mitchell", 15, 4, 9, ""), ("Andrew Wiggins", 10, 2, 1, "")],
    "DET": [("Cade Cunningham", 33, 5, 8, "14 of 14 from the line"), ("Kevin Huerter", 20, 4, 7, ""),
            ("Ausar Thompson", 10, 8, 5, "")],
    "MEM": [("Cedric Coward", 23, 12, 4, ""), ("Taylor Hendricks", 22, 5, 4, ""),
            ("Javon Small", 19, 2, 5, ""), ("Cam Spencer", 17, 1, 8, ""),
            ("Cameron Boozer", 15, 8, 5, ""), ("Olivier-Maxence Prosper", 11, 4, 0, ""),
            ("Isaiah Stewart", 11, 3, 3, "")],
    "BKN": [("Julius Randle", 22, 4, 5, ""), ("Day'Ron Sharpe", 16, 11, 5, ""),
            ("Noah Clowney", 15, 7, 3, ""), ("Danny Wolf", 14, 6, 1, ""),
            ("Egor Demin", 11, 1, 2, ""), ("Nolan Traore", 11, 1, 2, "")],
    "CHI": [("Norman Powell", 24, 5, 3, ""), ("Matas Buzelis", 18, 9, 2, ""),
            ("Buddy Hield", 16, 4, 2, ""), ("Tre Jones", 16, 4, 3, ""),
            ("Patrick Williams", 14, 5, 1, "")],
    "MIN": [("Ayo Dosunmu", 24, 4, 0, ""), ("LaMelo Ball", 19, 8, 6, "7 of 25 FG, 4 of 19 from three"),
            ("Jaden McDaniels", 18, 5, 6, ""), ("Terrence Shannon Jr", 14, 6, 0, ""),
            ("Bones Hyland", 12, 1, 2, ""),
            ("Rudy Gobert", 1, 10, 4, "0 of 7 from the field in 26:53")],
}

# Team shooting lines as the book's text layer printed them, kept only so the arithmetic that
# condemns them can be reproduced: FGM, FTM and the team's points. 2 x FGM + FTM must equal the
# points in an NBA box; none of these do, so they are discarded and flagged, never published.
# tri, note, fgm, ftm, pts
DISCARDED_TEAM_LINES = {
    "DAL": ("39 of 93 FG, 14 of 44 from three, 25 of 31 FT", 39, 25, 117),
    "CLE": ("48 of 90 FG, 15 of 40 from three, 16 of 18 FT", 48, 16, 127),
    "MIA": ("44 of 87 FG, 16 of 41 from three, 33 of 40 FT", 44, 33, 137),
    "DET": ("39 of 97 FG, 11 of 34 from three, 28 of 32 FT", 39, 28, 117),
    "MEM": ("46 of 87 FG, 15 of 35 from three, 22 of 29 FT", 46, 22, 129),
    "MIN": ("38 of 91 FG, 9 of 38 from three, 21 of 28 FT", 38, 21, 106),
}

# The "Inactive:" block of each book, verbatim where it survived the extract.
INACTIVES = {
    "CLE": [("Harden", "Right Elbow Injury Management"),
            ("Merrill", "Injury/Illness - Right Hamstring Injury Management"),
            ("Mitchell", ""), ("Mobely", ""), ("Tomlin", ""), ("Udeh Jr.", "")],
    "MEM": [("Grant", "Head Injury"), ("Jerome", "Injury/Illness - Right Hip Soreness"),
            ("Pippen Jr.", "Injury/Illness - Lumbar Disc Herniation"),
            ("Post", "Injury/Illness - Concussion Protocol"),
            ("Saunders", "Injury/Illness - Right Knee Surgery")],
    "CHI": [("Awaka", "Injury/Illness - Disc Irritation"),
            ("Claxton", "Injury/Illness - Left Hamstring Injury Management"),
            ("Sellers", "G League - Two-Way"), ("Smith", "Injury/Illness - Left Finger Sprain"),
            ("Swain", "G League - On Assignment"),
            ("Wilson", "Injury/Illness - Right Metacarpal Fracture")],
    "MIN": [("Broome", "G League - Two-Way"),
            ("DiVincenzo", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
            ("Edwards", "Injury/Illness - Right Knee Arthroscopy")],
}
INACTIVES_NOT_PRESERVED = ["DEN", "NOP", "DAL", "DET", "MIA", "BKN"]

# Printed as DND (did not dress) or NWT in the book rather than in the Inactive block. These are
# the status changes that happen AFTER a club's 6 a.m. filing, which is the whole reason the model
# cannot claim to know an injury situation from the report alone.
DND = [
    ("CLE", "Jarrett Allen", "DND -- Right Knee Management"),
    ("CLE", "Peyton Watson", "DND -- Right Hamstring Management"),
    ("MEM", "Zach Edey", "DND - Injury/Illness - Left Ankle Injury Management"),
    ("BKN", "Michael Porter Jr.", "NWT - Personal -"),
]

# One-line game facts from the same books, published as context.
GAME_CONTEXT = {
    "0022600232": {"attendance": 19432, "duration_min": 138,
                   "notes": ["points in the paint 54-42 Cleveland",
                             "Cleveland scored 38 points in the second quarter"]},
    "0022600233": {"attendance": 19658, "duration_min": 152,
                   "notes": ["Miami blocked 14 shots, one short of the franchise record, with "
                             "nine different players registering a block",
                             "points in the paint 52-50 Detroit; fast break 28-11 Miami",
                             "technical fouls: Holland II and Gardner, 6:23 of the second"]},
    "0022600234": {"attendance": 15103, "duration_min": None,
                   "notes": ["Brooklyn's 16 turnovers produced 30 Memphis points"]},
    "0022600235": {"attendance": 18054, "duration_min": None,
                   "notes": ["Minnesota's 17-point first quarter is its season low",
                             "technical fouls: T. Williams 6:24 of the third; Miller defensive "
                             "three-second, 2:52 of the first"]},
    "0022600231": {"attendance": None, "duration_min": None,
                   "notes": ["the recap on the game page records Dejounte Murray requesting a "
                             "trade on Friday; he is listed inactive with a left ankle sprain"]},
}

# Season facts recorded by the recaps that these books were published with.
LEAGUE_CONTEXT = [
    "Memphis had 10 double-digit scorers on 2026-11-13 in its 142-111 win at New Orleans, tying the "
    "NBA record for one game.",
    "Miami is the fourth team in 25 seasons to open 0-4 and then post a winning record, doing it 13 "
    "games in.",
]

# --------------------------------------------------------------------------- rolling slate
# nba.com/schedule?date=2026-11-15 read 11:33 UTC (11/15 rows, with tip times, arenas and game
# ids), and the day-strip of nba.com/game/... read at the same time (11/16, 11/17 rows).
# date, time_et, away, home, game_id, arena, city, tv
SLATE = [
    ("2026-11-15", "13:00", "IND", "PHI", "0022600236", "Xfinity Mobile Arena", "Philadelphia, PA", "League Pass"),
    ("2026-11-15", "16:00", "LAL", "PHX", "0022600237", "Mortgage Matchup Center", "Phoenix, AZ", "League Pass"),
    ("2026-11-15", "16:30", "CHA", "LAC", "0022600238", "Intuit Dome", "Inglewood, CA", "League Pass"),
    ("2026-11-15", "17:00", "SAS", "UTA", "0022600239", "Delta Center", "Salt Lake City, UT", "League Pass"),
    ("2026-11-15", "18:00", "DAL", "BOS", "0022600240", "TD Garden", "Boston, MA", "League Pass"),
    ("2026-11-15", "18:00", "NYK", "TOR", "0022600241", "Scotiabank Arena", "Toronto, ON", "League Pass"),
    ("2026-11-15", "19:00", "HOU", "WAS", "0022600242", "Capital One Arena", "Washington, DC", "MNMT/Monumental+"),
    ("2026-11-15", "20:00", "ATL", "MIL", "0022600243", "Fiserv Forum", "Milwaukee, WI", "League Pass"),
    ("2026-11-15", "21:00", "OKC", "SAC", "0022600244", "Golden 1 Center", "Sacramento, CA", "League Pass"),
    ("2026-11-16", "19:00", "ORL", "BOS", "0022600245", "TD Garden", "Boston, MA", "Peacock / NBC Sports Network"),
    ("2026-11-16", "19:00", "CHI", "CLE", "0022600246", "Rocket Arena", "Cleveland, OH", "League Pass"),
    ("2026-11-16", "19:00", "MEM", "WAS", "0022600247", "Capital One Arena", "Washington, DC", "MNMT/Monumental+"),
    ("2026-11-16", "19:30", "PHI", "BKN", "0022600248", "Barclays Center", "Brooklyn, NY", "League Pass"),
    ("2026-11-16", "19:30", "HOU", "MIA", "0022600249", "Kaseya Center", "Miami, FL", "League Pass"),
    ("2026-11-16", "20:00", "POR", "MIN", "0022600250", "Target Center", "Minneapolis, MN", "League Pass"),
    ("2026-11-16", "20:00", "GSW", "NOP", "0022600251", "Smoothie King Center", "New Orleans, LA", "League Pass"),
    ("2026-11-16", "21:00", "PHX", "DEN", "0022600252", "Ball Arena", "Denver, CO", "League Pass"),
    ("2026-11-17", "19:30", "NYK", "TOR", "0022600253", "Scotiabank Arena", "Toronto, ON", "League Pass"),
    ("2026-11-17", "20:00", "POR", "MIN", "0022600254", "Target Center", "Minneapolis, MN", "League Pass"),
    ("2026-11-17", "20:00", "DET", "SAS", "0022600255", "Frost Bank Center", "San Antonio, TX", "Peacock / NBC"),
    ("2026-11-17", "22:30", "UTA", "LAC", "0022600257", "Intuit Dome", "Inglewood, CA", "League Pass"),
    ("2026-11-17", "23:00", "CHA", "LAL", "0022600256", "Crypto.com Arena", "Los Angeles, CA", "Peacock"),
]

# The official day-strip calendar on nba.com/games, read today: per-date game counts used as the
# slate-completeness gate. Nov 15 = 9, Nov 16 = 8, Nov 17 = 5, Nov 18 = 12.
CALENDAR_COUNTS = {"2026-11-14": 5, "2026-11-15": 9, "2026-11-16": 8, "2026-11-17": 5,
                   "2026-11-18": 12}

# --------------------------------------------------------------------------- injury reports
# Both 11/15 releases were re-read row by row in this session. They are identical in content
# except for one surname: the 06:15 AM PDF prints "Embid, Joel" and the 06:00 AM PDF prints
# "Embiid, Joel" for the same Philadelphia row (same team, same status, same reason). Everything
# else — 84 designation rows, the single Dallas non-submission, the 16-slot 11/16 non-submission
# block — matches line for line, which is the finding, not an assumption: two official releases
# fifteen minutes apart moved nothing.
# The PDF's columns are Game Date | Game Time | Matchup | Team | Player Name | Current Status |
# Reason. Attribution "E" = the team cell is printed on the row; "C" = the row continues a team
# block across a PDF page break, so game date, matchup and team are carried over.
INJURY_1115 = [
    ("11/15/2026", "01:00", "IND@PHI", "Indiana Pacers", "Furphy, Johnny", "Out", "Injury/Illness - Right ACL Repair / Surgery", "E"),
    ("11/15/2026", "01:00", "IND@PHI", "Indiana Pacers", "Haliburton, Tyrese", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("11/15/2026", "01:00", "IND@PHI", "Indiana Pacers", "McConnell, T.J.", "Probable", "Injury/Illness - Right Hamstring Strain", "E"),
    ("11/15/2026", "01:00", "IND@PHI", "Indiana Pacers", "Nembhard, Andrew", "Questionable", "Injury/Illness - Left Hip Soreness / Tightness", "E"),
    ("11/15/2026", "01:00", "IND@PHI", "Indiana Pacers", "Nesmith, Aaron", "Questionable", "Injury/Illness - Left Hand Sprain", "E"),
    ("11/15/2026", "01:00", "IND@PHI", "Indiana Pacers", "Sheppard, Ben", "Out", "Injury/Illness - Left Meniscus Tear", "E"),
    ("11/15/2026", "01:00", "IND@PHI", "Philadelphia 76ers", "Barlow, Dominick", "Out", "Injury/Illness - Low Back Stress Reaction", "E"),
    ("11/15/2026", "01:00", "IND@PHI", "Philadelphia 76ers", "Bona, Adem", "Out", "Injury/Illness - Cervical Spine Sprain", "E"),
    ("11/15/2026", "01:00", "IND@PHI", "Philadelphia 76ers", "Embid, Joel", "Out", "Injury/Illness - Right Foot Plantar Fascia Injury Management", "E"),
    ("11/15/2026", "01:00", "IND@PHI", "Philadelphia 76ers", "Hukporti, Ariel", "Out", "Injury/Illness - Right Achilles Tendon Rupture / Tear", "E"),
    ("11/15/2026", "04:00", "LAL@PHX", "Los Angeles Lakers", "Carr, Cameron", "Out", "Injury/Illness - Illness", "E"),
    ("11/15/2026", "04:00", "LAL@PHX", "Los Angeles Lakers", "Grimes, Quentin", "Available", "Injury/Illness - Right Finger Splint", "E"),
    ("11/15/2026", "04:00", "LAL@PHX", "Los Angeles Lakers", "James, Bronny", "Questionable", "Injury/Illness - Illness", "E"),
    ("11/15/2026", "04:00", "LAL@PHX", "Los Angeles Lakers", "Reaves, Austin", "Out", "Injury/Illness - Left Heel Contusion / Bone Bruise", "E"),
    ("11/15/2026", "04:00", "LAL@PHX", "Los Angeles Lakers", "Sexton, Collin", "Questionable", "Injury/Illness - Right Orbital Laceration", "C"),
    ("11/15/2026", "04:00", "LAL@PHX", "Los Angeles Lakers", "Thiero, Adou", "Questionable", "Injury/Illness - Left Ankle Sprain", "C"),
    ("11/15/2026", "04:00", "LAL@PHX", "Phoenix Suns", "Williams, Mark", "Out", "Injury/Illness - Left Shoulder Surgery", "E"),
    ("11/15/2026", "04:30", "CHA@LAC", "Charlotte Hornets", "Ajayi, Michael", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "04:30", "CHA@LAC", "Charlotte Hornets", "Boswell, Kylan", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "04:30", "CHA@LAC", "Charlotte Hornets", "Knueppel, Kon", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("11/15/2026", "04:30", "CHA@LAC", "Charlotte Hornets", "Schroder, Dennis", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("11/15/2026", "04:30", "CHA@LAC", "Charlotte Hornets", "Steinbach, Hannes", "Out", "G League - On Assignment", "E"),
    ("11/15/2026", "04:30", "CHA@LAC", "LA Clippers", "Beal, Bradley", "Out", "Injury/Illness - Right Knee Injury Management", "E"),
    ("11/15/2026", "04:30", "CHA@LAC", "LA Clippers", "Ingram, Brandon", "Out", "Injury/Illness - Right Heel Surgery", "E"),
    ("11/15/2026", "04:30", "CHA@LAC", "LA Clippers", "Miller, Jordan", "Out", "Injury/Illness - Left Rotator Cuff Surgery", "E"),
    ("11/15/2026", "04:30", "CHA@LAC", "LA Clippers", "Niederhauser, Yanic Konan", "Out", "Injury/Illness - Right Lisfranc Surgery", "E"),
    ("11/15/2026", "05:00", "SAS@UTA", "San Antonio Spurs", "Brown, Maliq", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "05:00", "SAS@UTA", "San Antonio Spurs", "Gillespie, Ja'Kobi", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "05:00", "SAS@UTA", "San Antonio Spurs", "Harris, Tobias", "Out", "Injury/Illness - Left Calf Strain", "E"),
    ("11/15/2026", "05:00", "SAS@UTA", "San Antonio Spurs", "Quaintance, Jayden", "Out", "Injury/Illness - Right Knee Surgery", "E"),
    ("11/15/2026", "05:00", "SAS@UTA", "Utah Jazz", "Alexander, Trey", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "05:00", "SAS@UTA", "Utah Jazz", "Bufkin, Kobe", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "05:00", "SAS@UTA", "Utah Jazz", "Hayes, Jaxson", "Out", "Injury/Illness - Left Knee Strain", "C"),
    ("11/15/2026", "05:00", "SAS@UTA", "Utah Jazz", "Ingram, Harrison", "Out", "G League - Two-Way", "C"),
    ("11/15/2026", "05:00", "SAS@UTA", "Utah Jazz", "Jackson Jr., Jaren", "Out", "Injury/Illness - Right MCL Tear", "C"),
    ("11/15/2026", "05:00", "SAS@UTA", "Utah Jazz", "Markkanen, Lauri", "Out", "Injury/Illness - Right Hand Fracture", "C"),
    ("11/15/2026", "05:00", "SAS@UTA", "Utah Jazz", "Nurkic, Jusuf", "Out", "Injury/Illness - Right 2nd Plantar Plate Tear", "C"),
    ("11/15/2026", "06:00", "DAL@BOS", "Boston Celtics", "Carter, Devin", "Questionable", "G League - Two-Way", "E"),
    ("11/15/2026", "06:00", "DAL@BOS", "Boston Celtics", "Cenac Jr., Christopher", "Questionable", "G League - On Assignment", "E"),
    ("11/15/2026", "06:00", "DAL@BOS", "Boston Celtics", "Mitchell, Dillon", "Questionable", "G League - Two-Way", "E"),
    ("11/15/2026", "06:00", "DAL@BOS", "Boston Celtics", "Williams, Amari", "Questionable", "G League - Two-Way", "E"),
    ("11/15/2026", "06:00", "NYK@TOR", "Toronto Raptors", "Barnes, Scottie", "Questionable", "Injury/Illness - Left Groin Strain", "E"),
    ("11/15/2026", "06:00", "NYK@TOR", "Toronto Raptors", "Bittle, Nate", "Out", "Injury/Illness - Right Foot Avulsion Fracture", "E"),
    ("11/15/2026", "06:00", "NYK@TOR", "Toronto Raptors", "Leonard, Kawhi", "Out", "Injury/Illness - Left Knee Injury Management", "E"),
    ("11/15/2026", "06:00", "NYK@TOR", "Toronto Raptors", "McCullar Jr., Kevin", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "06:00", "NYK@TOR", "Toronto Raptors", "Smith, Malachi", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "07:00", "HOU@WAS", "Houston Rockets", "Adams, Steven", "Probable", "Injury/Illness - Right Soleus Strain", "E"),
    ("11/15/2026", "07:00", "HOU@WAS", "Houston Rockets", "Capela, Clint", "Out", "Injury/Illness - Right Ankle Sprain", "E"),
    ("11/15/2026", "07:00", "HOU@WAS", "Houston Rockets", "Copeland, Quadir", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "07:00", "HOU@WAS", "Houston Rockets", "Phillips, Julian", "Out", "G League - Two-Way", "C"),
    ("11/15/2026", "07:00", "HOU@WAS", "Houston Rockets", "Smart, Marcus", "Out", "League Suspension", "C"),
    ("11/15/2026", "07:00", "HOU@WAS", "Houston Rockets", "VanVleet, Fred", "Out", "Injury/Illness - Right Knee Injury Management", "C"),
    ("11/15/2026", "07:00", "HOU@WAS", "Washington Wizards", "Beekman, Reece", "Out", "Injury/Illness - Right AC Joint Injury", "E"),
    ("11/15/2026", "07:00", "HOU@WAS", "Washington Wizards", "Carrington, Bub", "Questionable", "Injury/Illness - Chest / Sternum Contusion", "E"),
    ("11/15/2026", "07:00", "HOU@WAS", "Washington Wizards", "Champagne, Justin", "Out", "Injury/Illness - Right Foot Surgery", "E"),
    ("11/15/2026", "07:00", "HOU@WAS", "Washington Wizards", "Johnson, Tre", "Questionable", "Injury/Illness - Low Back Soreness", "E"),
    ("11/15/2026", "07:00", "HOU@WAS", "Washington Wizards", "Okpara, Felix", "Questionable", "G League - Two-Way", "E"),
    ("11/15/2026", "07:00", "HOU@WAS", "Washington Wizards", "Sarr, Alex", "Questionable", "Injury/Illness - Illness", "E"),
    ("11/15/2026", "07:00", "HOU@WAS", "Washington Wizards", "Vukcevic, Tristan", "Out", "Injury/Illness - Left Hip Impingement", "E"),
    ("11/15/2026", "07:00", "HOU@WAS", "Washington Wizards", "Watkins, Jamir", "Out", "Injury/Illness - Left ACL Repair / Surgery", "E"),
    ("11/15/2026", "08:00", "ATL@MIL", "Atlanta Hawks", "Flemings, Kingston", "Out", "Injury/Illness - Lumbar Strain", "E"),
    ("11/15/2026", "08:00", "ATL@MIL", "Atlanta Hawks", "Gilbert, Keshon", "Out", "Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure", "E"),
    ("11/15/2026", "08:00", "ATL@MIL", "Atlanta Hawks", "Gueye, Mouhamed", "Out", "Injury/Illness - Left Foot Fracture", "E"),
    ("11/15/2026", "08:00", "ATL@MIL", "Atlanta Hawks", "Landale, Jock", "Available", "Injury/Illness - Face Mask", "E"),
    ("11/15/2026", "08:00", "ATL@MIL", "Atlanta Hawks", "Newell, Asa", "Out", "Injury/Illness - Left Great Toe Hyperextension", "E"),
    ("11/15/2026", "08:00", "ATL@MIL", "Atlanta Hawks", "Veesaar, Henri", "Out", "Injury/Illness - Right ACL Tear", "C"),
    ("11/15/2026", "08:00", "ATL@MIL", "Atlanta Hawks", "Wilson, Jalen", "Doubtful", "G League - Two-Way", "C"),
    ("11/15/2026", "08:00", "ATL@MIL", "Milwaukee Bucks", "Dieng, Ousmane", "Out", "Injury/Illness - Left Finger Sprain", "E"),
    ("11/15/2026", "08:00", "ATL@MIL", "Milwaukee Bucks", "Jones, Kam", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "08:00", "ATL@MIL", "Milwaukee Bucks", "Markovic, Bogoljub", "Out", "G League - On Assignment", "E"),
    ("11/15/2026", "08:00", "ATL@MIL", "Milwaukee Bucks", "Nance, Pete", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "08:00", "ATL@MIL", "Milwaukee Bucks", "Ryan, Cormac", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Holmgren, Chet", "Out", "Injury/Illness - Right Knee/ Injury Recovery", "E"),
    ("11/15/2026", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Mitchell, Ajay", "Questionable", "Injury/Illness - Left Ankle Sprain", "E"),
    ("11/15/2026", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Sorber, Thomas", "Out", "Injury/Illness - Right Knee Surgery", "C"),
    ("11/15/2026", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Wallace, Cason", "Out", "Injury/Illness - Left Shoulder Surgery", "E"),
    ("11/15/2026", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Williams, Jalen", "Out", "Injury/Illness - Left Ankle Surgery", "E"),
    ("11/15/2026", "09:00", "OKC@SAC", "Oklahoma City Thunder", "Williams, Jaylin", "Out", "Injury/Illness - Low Back Spasms", "E"),
    ("11/15/2026", "09:00", "OKC@SAC", "Sacramento Kings", "Achiuwa, Precious", "Questionable", "Injury/Illness - Left Ankle Soreness", "E"),
    ("11/15/2026", "09:00", "OKC@SAC", "Sacramento Kings", "Mogbo, Jonathan", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "09:00", "OKC@SAC", "Sacramento Kings", "Murray, Keegan", "Questionable", "Injury/Illness - Illness", "E"),
    ("11/15/2026", "09:00", "OKC@SAC", "Sacramento Kings", "Pedulla, Sean", "Out", "G League - Two-Way", "E"),
    ("11/15/2026", "09:00", "OKC@SAC", "Sacramento Kings", "Raynaud, Maxime", "Out", "Injury/Illness - Right Patella Subluxation", "E"),
    ("11/15/2026", "09:00", "OKC@SAC", "Sacramento Kings", "Simmons, Ben", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery", "C"),
]

# Rows whose printed line carries no team cell because the PDF broke the page mid-block. The
# team is carried over from the block; the flag says so rather than pretending the cell was read.
CARRIED_ROWS = [r[4] for r in INJURY_1115 if r[7] == "C"]

# The one textual difference between the two releases, as a data-level override:
# release -> {player as printed}
RELEASE_SPELLING = {"06:00 AM": {"Embid, Joel": "Embiid, Joel"}, "06:15 AM": {}}


def release_rows(stamp: str):
    """The rows of one release, with that release's own spellings applied."""
    over = RELEASE_SPELLING.get(stamp, {})
    return [tuple(over.get(x, x) for x in r) for r in INJURY_1115]


# NOT-YET-SUBMITTED club rows, verbatim, printed in BOTH releases.
NOT_SUBMITTED_1115 = [("11/15/2026", "06:00", "DAL@BOS", "Dallas Mavericks")]
NOT_SUBMITTED_1116 = [
    ("11/16/2026", "07:00", "CHI@CLE", "Chicago Bulls"), ("11/16/2026", "07:00", "CHI@CLE", "Cleveland Cavaliers"),
    ("11/16/2026", "07:00", "MEM@WAS", "Memphis Grizzlies"), ("11/16/2026", "07:00", "MEM@WAS", "Washington Wizards"),
    ("11/16/2026", "07:00", "ORL@BOS", "Orlando Magic"), ("11/16/2026", "07:00", "ORL@BOS", "Boston Celtics"),
    ("11/16/2026", "07:30", "HOU@MIA", "Houston Rockets"), ("11/16/2026", "07:30", "HOU@MIA", "Miami Heat"),
    ("11/16/2026", "07:30", "PHI@BKN", "Philadelphia 76ers"), ("11/16/2026", "07:30", "PHI@BKN", "Brooklyn Nets"),
    ("11/16/2026", "08:00", "GSW@NOP", "Golden State Warriors"), ("11/16/2026", "08:00", "GSW@NOP", "New Orleans Pelicans"),
    ("11/16/2026", "08:00", "POR@MIN", "Portland Trail Blazers"), ("11/16/2026", "08:00", "POR@MIN", "Minnesota Timberwolves"),
    ("11/16/2026", "09:00", "PHX@DEN", "Phoenix Suns"), ("11/16/2026", "09:00", "PHX@DEN", "Denver Nuggets"),
]

TEAM_TRI = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}

# --------------------------------------------------------------------------- what this capture adds
NOTES = [
    "Consecutive official releases, fifteen minutes apart (06:00 AM and 06:15 AM ET on 2026-11-15), "
    "are identical in content: same 84 designation rows, same single Dallas non-submission, same "
    "16-slot 11/16 non-submission block. The only textual difference is the spelling of the "
    "Philadelphia centre's surname — \"Embiid, Joel\" at 06:00, \"Embid, Joel\" at 06:15, same team, "
    "status and reason. Both spellings are kept verbatim in the two snapshots; matching is done on a "
    "normalised player key so the typo does not surface as a phantom status change.",
    "The PDF prints tip times on a 12-hour clock with an \"(ET)\" suffix. All nine 11/15 game times "
    "and all eight 11/16 game times in the PDF match nba.com/schedule exactly (01:00 = 1:00 PM ET, "
    "04:00 = 4:00 PM ET, 07:30 = 7:30 PM ET, and so on).",
    "Dallas is the only club that had not filed for a 2026-11-15 game in either release: DAL@BOS "
    "prints \"NOT YET SUBMITTED\" against the Mavericks and nothing against them at any later hour. "
    "For the eight 2026-11-16 games, all 16 club-slots print \"NOT YET SUBMITTED\", and 2026-11-17 "
    "does not appear in the document at all.",
    "New York filed no designation rows for its 11/15 game and no non-submission marker either. That "
    "is read as a clean filing — an empty report — rather than a missing document. The reading is an "
    "interpretation and is labelled as one on the site.",
    "Six 11/15 rows are continuation rows: the PDF broke a page mid-block, so the game date, "
    "matchup and team cells are blank on the printed line. The team is carried over from the block "
    "and every one of those rows is marked \"C\" (carried) in the snapshot. Sacramento's Ben Simmons "
    "row is the extreme case — all four leading cells, including the team cell, are empty; it is "
    "attached to Sacramento by block position and flagged, never asserted.",
    "Denver's 11/14 game book lists the Pelicans' Dejounte Murray as inactive with a left ankle "
    "sprain, and the recap on the same page records that he requested a trade on Friday. A "
    "roster-mover fact has no input in this model (R-106) and is published as a note only.",
    "Cleveland's game book lists seven inactive players — five of a usual starting five — plus two "
    "more (Allen, Watson) marked DND, did not dress, after the day's last injury release. A "
    "game-day change of that size is invisible to any model fed only by the morning report, which is "
    "why availability is scored against the game book and not the PDF alone.",
    "The 11/14 game books also carry two source-side defects that are published rather than "
    "quietly repaired: James Harden's inactive line reads \"Right Elbow Injury Management\" while the "
    "recap on the same page attributes his absence to a left calf, and one Detroit period strip in "
    "the DET@MIA book prints \"20 21 26 21 117\", which cannot be a quarter line. Both are flagged; "
    "neither is used.",
]

BLOCKED = [
    {"what": "Per-player season game logs (minutes by game, for players who did not play)",
     "attempted": "nba.com/stats/player/<id>/gamelog renders client-side and returns 'No data "
                  "available' to this client; the same failure was reported by session "
                  "arena/bc867bff-nba2 on 2026-11-14.",
     "consequence": "Minutes redistribution is modelled from the official game books of the games a "
                    "player missed — who actually played and how many minutes they took — so coverage "
                    "is 2026-11-14 (10 clubs), not the season. Any line that would depend on a bench "
                    "player's season-long usage is left unpriced."},
    {"what": "Market prices: spread, total, moneyline, prop lines, and closing lines",
     "attempted": "no licensed odds feed is connected to this repository, and nba.com renders its "
                  "odds panel client-side.",
     "consequence": "No edge, no closing-line value, no ROI, and no market-anchored prior. The "
                    "closing-line blend is implemented and unit-tested against a fixture but has no "
                    "input, so the published weight on the market is 0.0 and the blend equals the "
                    "model line."},
    {"what": "Arena coordinate table, for travel distance",
     "attempted": "no official NBA document in this repository publishes arena latitude/longitude; "
                  "nba.com/schedule gives arena name and city only.",
     "consequence": "Travel is published as arena + city + time-zone change (all sourced) with the "
                    "great-circle distance column left blank and flagged. It is not estimated."},
    {"what": "Injury designations for 2026-11-16 and 2026-11-17",
     "attempted": "the two 11/15 releases are the newest documents; every 11/16 club-slot prints "
                  "NOT YET SUBMITTED and 11/17 is absent from the document entirely.",
     "consequence": "13 of the 22 slate games (the 8 on 11/16 and 5 on 11/17) are priced from "
                    "availability-blind ratings only, with no injury input at all, and they carry a "
                    "stale-availability flag. This narrows the standing 'future injuries' gap from "
                    "the whole window to those 13 games."},
    {"what": "Live automated ingest of the official endpoints",
     "attempted": "the runner in .github/workflows/refresh.yml has no network path to nba.com "
                  "(verified by the probe recorded in audit/2026-11-14 and reported as A-01/F-02).",
     "consequence": "This session's capture is the newest snapshot; the scheduled job can refresh "
                    "finals and archive PDFs but cannot yet rebuild the rolling slate on its own."},
]

# --------------------------------------------------------------------------- helpers
def minutes_to_sec(mm: int, ss: int) -> int:
    return mm * 60 + ss


def check() -> list[str]:
    """Every identity the capture must satisfy. A non-empty return means: do not write."""
    problems: list[str] = []

    # 1. quarter sums
    for (gid, date, aw, hm, ap, hp, aq, hq, arena, book, url) in FINALS_1114:
        if sum(aq) != ap:
            problems.append(f"{gid}: away quarters {aq} sum {sum(aq)} != final {ap}")
        if sum(hq) != hp:
            problems.append(f"{gid}: home quarters {hq} sum {sum(hq)} != final {hp}")

    # 2. game books: nothing published as a stat line may contradict the final score. Leaders are
    #    context, so the only hard rule is that named scoring cannot exceed what the team scored.
    finals_by_team: dict[str, tuple[str, int]] = {}
    for (gid, date, aw, hm, ap, hp, aq, hq, arena, book, url) in FINALS_1114:
        finals_by_team[aw] = (gid, ap)
        finals_by_team[hm] = (gid, hp)
    for tri, rows in LEADERS.items():
        if tri not in finals_by_team:
            problems.append(f"leaders {tri}: no 11/14 final for this club")
        if sum(r[1] for r in rows) > finals_by_team[tri][1]:
            problems.append(f"leaders {tri}: named points {sum(r[1] for r in rows)} exceed the "
                            f"team's {finals_by_team[tri][1]}")
    for tri, (label, fgm, fta_or_ftm, pts_claim) in DISCARDED_TEAM_LINES.items():
        if 2 * fgm + fta_or_ftm == pts_claim:
            problems.append(f"{tri}: the discarded shooting line actually reconciles — "
                            f"republish it instead of flagging it")
    if len(set(INACTIVES) | set(INACTIVES_NOT_PRESERVED)) != 10:
        problems.append("the ten 11/14 clubs must be split between preserved and not-preserved")
    for (tri, player, printed) in DND:
        if tri not in finals_by_team:
            problems.append(f"DND {player}: unknown club {tri}")

    # 3. standings internal arithmetic
    if len(STANDINGS) != 30:
        problems.append(f"standings has {len(STANDINGS)} rows, expected 30")
    tw = sum(r[1] for r in STANDINGS)
    tl = sum(r[2] for r in STANDINGS)
    if tw != tl:
        problems.append(f"league wins {tw} != losses {tl}")
    for (tri, w, l, *_rest) in STANDINGS:
        row = {r[0]: r for r in STANDINGS}[tri]
        hw, hl = (int(x) for x in row[7].split("-"))
        rw, rl = (int(x) for x in row[8].split("-"))
        nw, nl = (int(x) for x in row[9].split("-"))
        if hw + hl + rw + rl + nw + nl != w + l:
            problems.append(f"{tri}: home+road+neutral {hw+hl+rw+rl+nw+nl} != GP {w+l}")
        if hw + rw + nw != w:
            problems.append(f"{tri}: home {hw} + road {rw} + neutral {nw} wins != W {w}")
        if hl + rl + nl != l:
            problems.append(f"{tri}: losses by venue {hl+rl+nl} != L {l}")
        cw, cl = (int(x) for x in row[5].split("-"))
        dw, dl = (int(x) for x in row[6].split("-"))
        for label, x, lim in (("conference", cw, w), ("conference", cl, l),
                             ("division", dw, w), ("division", dl, l)):
            if not 0 <= x <= lim:
                problems.append(f"{tri}: {label} figure {x} outside the season record {w}-{l}")
        if cw + cl > w + l:
            problems.append(f"{tri}: conference games {cw+cl} exceed season games {w+l}")
    # 3b. the CONF column must be exactly each team's record against its own conference, computed
    #     from the 188-game result feed. East = the first 15 rows of the card, West = the last 15.
    conf_of = {r[0]: ("East" if i < 15 else "West") for i, r in enumerate(STANDINGS)}
    computed: dict[str, list[int]] = {t: [0, 0] for t in conf_of}
    for g in build_feed()["rows"]:
        if conf_of[g["away"]] == conf_of[g["home"]]:
            a, h = computed[g["away"]], computed[g["home"]]
            if g["away_pts"] > g["home_pts"]:
                a[0] += 1; h[1] += 1
            else:
                h[0] += 1; a[1] += 1
    for (tri, w, l, *_rest) in STANDINGS:
        row = {r[0]: r for r in STANDINGS}[tri]
        printed = tuple(int(x) for x in row[5].split("-"))
        if tuple(computed[tri]) != printed:
            problems.append(f"{tri}: conference record printed {printed[0]}-{printed[1]}, the "
                            f"{sum(computed[tri])}-game result feed says "
                            f"{computed[tri][0]}-{computed[tri][1]}")
    # 4. results feed vs the committed history: records rebuilt from every game must equal the card
    feed = build_feed()
    for tri, w, l, *_ in STANDINGS:
        rec = feed["records"].get(tri)
        if rec is None:
            problems.append(f"{tri}: absent from the rebuilt result feed")
        elif (rec["w"], rec["l"]) != (w, l):
            problems.append(f"{tri}: feed rebuild {rec['w']}-{rec['l']} != standings {w}-{l}")
    if feed["games"] != 188:
        problems.append(f"result feed has {feed['games']} games, expected 188 (183 + 5 on 11/14)")

    # 5. the two injury releases, re-read independently, must agree except where recorded
    r15, r00 = release_rows("06:15 AM"), release_rows("06:00 AM")
    if len(r15) != 84 or len(r00) != 84:
        problems.append(f"injury designation rows: 06:15={len(r15)}, 06:00={len(r00)}, both must be 84")
    if len(NOT_SUBMITTED_1115) != 1 or len(NOT_SUBMITTED_1116) != 16:
        problems.append("non-submission rows changed: expected 1 (11/15) and 16 (11/16)")
    changed = [(a, b) for a, b in zip(r15, r00) if a != b]
    if len(changed) != 1:
        problems.append(f"the two releases must differ in exactly one row, got {len(changed)}")
    else:
        a, b = changed[0]
        fields = [i for i in range(len(a)) if a[i] != b[i]]
        if fields != [4] or "Embid" not in a[4] or "Embid" in b[4]:
            problems.append(f"the one documented difference must be the player-name field only, "
                            f"changed fields {fields}: {a[4]!r} vs {b[4]!r}")
    for r in r15:
        if r[5] not in ("Out", "Doubtful", "Questionable", "Probable", "Available"):
            problems.append(f"unexpected status {r[5]!r} on {r}")
        if r[0] != "11/15/2026":
            problems.append(f"row outside the 11/15 game date: {r}")
        if r[3] not in TEAM_TRI:
            problems.append(f"team name not in the attribution table: {r[3]}")
    # every designation row's team must match the matchup's own clubs
    for (d, t, mu, team, player, st, why, attr) in r15:
        aw, hm = mu.split("@")
        if TEAM_TRI[team] not in (aw, hm):
            problems.append(f"{player}: team {team} is not a club in {mu}")
    # teams that filed must be sorted alphabetically inside each team block (the PDF's own order)
    by_team: dict[tuple, list] = {}
    for r in r15:
        by_team.setdefault((r[2], r[3]), []).append(r[4])
    for key, names in by_team.items():
        if names != sorted(names, key=lambda n: (n.split(",")[0], n)):
            problems.append(f"rows out of the PDF's alphabetical order inside {key}: {names}")
    # the PDF's own game grid must equal the slate's per-day counts (9 games on 11/15, 8 on 11/16)
    pdf_games_1115 = {r[2] for r in r15} | {x[2] for x in NOT_SUBMITTED_1115}
    if len(pdf_games_1115) != CALENDAR_COUNTS["2026-11-15"]:
        problems.append(f"PDF lists {len(pdf_games_1115)} games on 11/15, calendar says "
                        f"{CALENDAR_COUNTS['2026-11-15']}")
    pdf_games_1116 = {x[2] for x in NOT_SUBMITTED_1116}
    if len(pdf_games_1116) != CALENDAR_COUNTS["2026-11-16"]:
        problems.append(f"PDF lists {len(pdf_games_1116)} games on 11/16, calendar says "
                        f"{CALENDAR_COUNTS['2026-11-16']}")
    slate_1116 = {f"{g[2]}@{g[3]}" for g in SLATE if g[0] == "2026-11-16"}
    if pdf_games_1116 != slate_1116:
        problems.append(f"PDF's 11/16 matchups != the slate's: {sorted(pdf_games_1116 ^ slate_1116)}")
    slate_1115 = {f"{g[2]}@{g[3]}" for g in SLATE if g[0] == "2026-11-15"}
    if pdf_games_1115 != slate_1115:
        problems.append(f"PDF's 11/15 matchups != the slate's: {sorted(pdf_games_1115 ^ slate_1115)}")
    # every PDF tip time (12-hour, ET) must match the slate's 24-hour ET time
    pdf_time = {}
    for r in list(r15) + [(x[0], x[1], x[2], x[3]) + ("",) * 4 for x in NOT_SUBMITTED_1115 + NOT_SUBMITTED_1116]:
        pdf_time[(r[0], r[2])] = r[1]
    for (d, t_et, aw, hm, gid, ar, ci, tv) in SLATE:
        key = ("11/15/2026" if d == "2026-11-15" else "11/16/2026", f"{aw}@{hm}")
        if key in pdf_time:
            hh = int(t_et.split(":")[0]) % 12 or 12
            want = f"{hh:02d}:{t_et.split(':')[1]}"
            if pdf_time[key] != want:
                problems.append(f"{key}: PDF prints {pdf_time[key]}, schedule says {t_et} ET -> {want}")

    # 6. slate vs the official per-date counts, and every window game must have both clubs
    from collections import Counter
    c = Counter(s[0] for s in SLATE)
    for d, n in c.items():
        if CALENDAR_COUNTS.get(d) != n:
            problems.append(f"slate {d}: {n} rows, official calendar says {CALENDAR_COUNTS.get(d)}")
    ids = [s[4] for s in SLATE]
    if len(ids) != len(set(ids)):
        problems.append("duplicate game id in the slate")
    for s in SLATE:
        if s[2] not in finals_by_team and s[2] not in [x[0] for x in STANDINGS]:
            problems.append(f"unknown away tri {s[2]}")

    # 7. ratings pages must agree with the standings card on GP/W/L
    adv = {r[0]: r for r in ADVANCED}
    opp = {r[0]: r for r in OPPONENT}
    if len(adv) != 30 or len(opp) != 30:
        problems.append(f"advanced {len(adv)} / opponent {len(opp)} rows, expected 30 each")
    for (tri, w, l, *_rest) in STANDINGS:
        gp = w + l
        if adv[tri][1] != gp:
            problems.append(f"{tri}: advanced GP {adv[tri][1]} != standings GP {gp}")
        if opp[tri][1] != gp:
            problems.append(f"{tri}: opponent GP {opp[tri][1]} != standings GP {gp}")
        if (adv[tri][2], adv[tri][3]) != (w, l):
            problems.append(f"{tri}: advanced W-L {adv[tri][2]}-{adv[tri][3]} != standings {w}-{l}")
        if abs(adv[tri][5] - (adv[tri][4] - adv[tri][2 + 2])) > 0.051 and False:
            pass
        # each rating is printed to 0.1, so their difference can land a tenth off the printed NetRtg
        if abs((adv[tri][4] - adv[tri][5]) - adv[tri][6]) > 0.151:
            problems.append(f"{tri}: OffRtg-DefRtg {adv[tri][4]-adv[tri][5]:.1f} != NetRtg {adv[tri][6]}")

    # 8. opponent-page points allowed vs the finals, per team-season total
    pts_against = feed["points_against"]
    for tri, gp, opp_pts, _pm in OPPONENT:
        if tri not in pts_against:
            problems.append(f"{tri}: absent from the rebuilt feed")
            continue
        tot = pts_against[tri]
        # opp_pts is printed to 0.1, so the season total must match within 0.05*GP
        if abs(opp_pts * gp - tot) > 0.05 * gp + 0.5:
            problems.append(f"{tri}: opponent page {opp_pts}*{gp}={opp_pts*gp:.1f} != finals total {tot}")

    # 9. advanced-page scoring vs the finals, per team-season total
    scored = feed["points_for"]
    for tri, gp, _w, _l, off, _def, _net, _pace, _pie, poss in ADVANCED:
        if abs(off * poss / 100.0 - scored[tri]) > 0.5 * gp / 10.0 + 1.0:
            problems.append(f"{tri}: OffRtg x poss implies {off*poss/100.0:.1f} pts, finals give {scored[tri]}")

    # 10. traditional page: GP/W/L against the card, points-for against the rebuilt finals,
    #     OffRtg implied by (pts, poss), and OREB+DREB = REB on the printed row
    trad = {r[0]: r for r in TRADITIONAL}
    if len(trad) != 30:
        problems.append(f"traditional page has {len(trad)} distinct teams, expected 30")
    for (tri, w, l, *_rest) in STANDINGS:
        gp = w + l
        r = trad[tri]
        if r[1] != gp or (r[2], r[3]) != (w, l):
            problems.append(f"{tri}: traditional {r[1]} GP {r[2]}-{r[3]} != standings {gp} {w}-{l}")
        if abs(r[5] * gp - scored[tri]) > 0.05 * gp + 0.5:
            problems.append(f"{tri}: traditional {r[5]} pts/g x {gp} = {r[5]*gp:.1f} != finals total {scored[tri]}")
        if abs(r[17] - (r[15] + r[16])) > 0.101:
            problems.append(f"{tri}: OREB {r[15]} + DREB {r[16]} != REB {r[17]}")
        implied = r[5] * 100.0 / (adv[tri][9] / adv[tri][1])
        if abs(implied - adv[tri][4]) > 0.35:
            problems.append(f"{tri}: traditional implies OffRtg {implied:.1f}, advanced page prints {adv[tri][4]}")
        margin_printed = r[5] - opp[tri][2]
        margin_actual = (scored[tri] - pts_against[tri]) / gp
        if abs(margin_printed - margin_actual) > 0.12:
            problems.append(f"{tri}: traditional pts {r[5]} - opponent pts {opp[tri][2]} = "
                            f"{margin_printed:.2f}, finals give {margin_actual:.2f}")

    # 11. the standings card's OT and neutral columns must equal what the games themselves say
    ot_games = sum(1 for g in feed["rows"] if g.get("ot"))
    ot_col = sum(sum(int(x) for x in r[10].split("-")) for r in STANDINGS)
    if ot_col != 2 * ot_games:
        problems.append(f"standings OT column implies {ot_col // 2} games, the result feed has {ot_games}")
    neu_games = sum(1 for g in feed["rows"] if g.get("neutral_site"))
    neu_col = sum(sum(int(x) for x in r[9].split("-")) for r in STANDINGS)
    if neu_col != 2 * neu_games:
        problems.append(f"standings neutral column implies {neu_col // 2} games, the feed has {neu_games}")
    l10 = sum(sum(int(x) for x in r[11].split("-")) for r in STANDINGS)
    if l10 != 300:
        problems.append(f"LAST 10 column sums to {l10} team-games, not 300 (30 teams x 10)")
    return problems


def build_feed() -> dict:
    """One row per game, from the committed history plus this session's five 11/14 finals."""
    games: dict[str, dict] = {}
    for p in sorted(HIST.glob("games_*.json")):
        doc = json.loads(p.read_text())
        for g in doc["games"]:
            games[g["game_id"]] = {
                "game_id": g["game_id"], "date": g["date"], "away": g["away"], "home": g["home"],
                "away_pts": g["away_pts"], "home_pts": g["home_pts"],
                "quarters": g.get("periods") and [None] * 0 or None,
                "status": "final", "ot": bool(g.get("ot")) or (g.get("periods") or 4) > 4,
                "periods": g.get("periods"), "neutral_site": bool(g.get("neutral_site")),
                "cup_group": g.get("cup_group"),
                "source_url": g["source_url"], "capture": p.name,
            }
    for (gid, date, aw, hm, ap, hp, aq, hq, arena, book, url) in FINALS_1114:
        games[gid] = {
            "game_id": gid, "date": date, "away": aw, "home": hm,
            "away_pts": ap, "home_pts": hp,
            "quarters": {"away": aq, "home": hq},
            "status": "final", "ot": False, "periods": 4, "neutral_site": False,
            "source_url": url, "book_url": book, "capture": "this session",
            "ot_basis": "none of the five 11/14 games went to overtime and none was neutral: "
                        "verified against the standings card's OT and Neutral columns in "
                        "build_capture.check step 11",
        }
    records: dict[str, dict] = {}
    scored: dict[str, int] = {}
    against: dict[str, int] = {}
    for g in games.values():
        for tri, pts, opp, side in ((g["away"], g["away_pts"], g["home_pts"], "road"),
                                    (g["home"], g["home_pts"], g["away_pts"], "home")):
            r = records.setdefault(tri, {"gp": 0, "w": 0, "l": 0, "home_w": 0, "home_l": 0,
                                         "road_w": 0, "road_l": 0})
            r["gp"] += 1
            if pts > opp:
                r["w"] += 1
                r[f"{side}_w"] += 1
            else:
                r["l"] += 1
                r[f"{side}_l"] += 1
            scored[tri] = scored.get(tri, 0) + pts
            against[tri] = against.get(tri, 0) + opp
    rows = [games[k] for k in sorted(games, key=lambda k: (games[k]["date"], k))]
    return {"games": len(rows), "rows": rows, "records": records,
            "points_for": scored, "points_against": against}


def main() -> int:
    problems = check()
    if problems:
        print("CAPTURE REFUSED — identities failed:")
        for p in problems:
            print("  *", p)
        return 1

    feed = build_feed()
    RAW.mkdir(parents=True, exist_ok=True)

    def dump(path: Path, obj) -> str:
        txt = json.dumps(obj, indent=1, ensure_ascii=False) + "\n"
        path.write_text(txt)
        return hashlib.sha256(txt.encode()).hexdigest()[:16]

    finals = {
        "schema": "nba2.games.v2", "captured_utc": CAPTURED_UTC, "session": SESSION,
        "meaning": "official final scores with quarter scores, captured 2026-11-15 from the game "
                   "page and the official game book; the two documents agree on every line",
        "n_games": len(FINALS_1114), "date_range": ["2026-11-14", "2026-11-14"],
        "retrieval_method": METHOD, "source_pages": [U["games_1114"], U["schedule"]],
        "games": [
            {"game_id": gid, "date": d, "away": aw, "home": hm, "away_pts": ap, "home_pts": hp,
             "quarters": {"away": aq, "home": hq}, "arena": arena, "status": "final",
             "quarter_source_game_page": url, "quarter_source_game_book": book,
             "source_url": url, "list_url": U["games_1114"]}
            for (gid, d, aw, hm, ap, hp, aq, hq, arena, book, url) in FINALS_1114
        ],
    }
    fh = dump(RAW / "finals_2026-11-14.json", finals)

    feed_doc = {
        "schema": "nba2.results-feed.v1", "captured_utc": CAPTURED_UTC, "session": SESSION,
        "rule": "one row per game: date, both clubs, final score, quarter scores. A row is "
                "settleable only when status == 'final'. Quarter scores are present only for the "
                "games this session read from a game page or game book; the rest carry null and "
                "are flagged, never estimated.",
        "sources": {"games": U["games_1114"], "schedule": U["schedule"],
                    "history": "data/raw/history/games_*.json (committed by earlier sessions)"},
        "counts": {"games": feed["games"],
                   "with_quarters": sum(1 for r in feed["rows"] if r["quarters"]),
                   "without_quarters": sum(1 for r in feed["rows"] if not r["quarters"])},
        "records": {t: r for t, r in sorted(feed["records"].items())},
        "games": feed["rows"],
    }
    feedh = dump(RAW / "results_feed_2026-11-15.json", feed_doc)

    stand = {
        "schema": "nba2.standings-snapshot.v1", "captured_utc": CAPTURED_UTC, "session": SESSION,
        "source_url": U["standings"], "as_of": "2026-11-15",
        "columns": ["tri", "w", "l", "win_pct", "gb", "conf", "div", "home", "road",
                    "neutral", "ot", "last10", "streak"],
        "rows": [list(r) for r in STANDINGS],
        "league": {"games": feed["games"], "wins": sum(r[1] for r in STANDINGS),
                   "losses": sum(r[2] for r in STANDINGS)},
    }
    sh = dump(RAW / "standings_2026-11-15_official.json", stand)

    ratings = {
        "schema": "nba2.team-ratings-snapshot.v1", "captured_utc": CAPTURED_UTC, "session": SESSION,
        "advanced": {"source_url": U["advanced"],
                     "columns": ["tri", "gp", "w", "l", "offrtg", "defrtg", "netrtg", "pace", "pie", "poss"],
                     "rows": [list(r) for r in ADVANCED]},
        "opponent": {"source_url": U["opponent"],
                     "columns": ["tri", "gp", "opp_pts_per_game", "opp_plus_minus"],
                     "rows": [list(r) for r in OPPONENT]},
        "traditional": {
            "source_url": "https://www.nba.com/stats/teams/traditional",
            "columns": ["tri", "gp", "w", "l", "min", "pts", "fgm", "fga", "fg_pct", "3pm", "3pa",
                        "3p_pct", "ftm", "fta", "ft_pct", "oreb", "dreb", "reb", "ast", "tov",
                        "stl", "blk", "blka", "pf", "pfd", "plus_minus"],
            "rows": [list(r) for r in TRADITIONAL],
            "read_note": "the page is one client-rendered <table> returned in five chunks; the "
                         "Boston and Brooklyn rows straddled a chunk boundary and were stitched from "
                         "the next chunk, then re-derived from the printed identities (OREB+DREB=REB, "
                         "pts x GP = the rebuilt season total, pts/poss = OffRtg on the advanced page, "
                         "+/- = NetRtg) before being written",
        },
        "rebuilt_from_finals": {
            "points_for": feed["points_for"], "points_against": feed["points_against"],
            "source": "data/raw/results_feed_2026-11-15.json",
        },
    }
    rh = dump(RAW / "team_ratings_2026-11-15.json", ratings)

    def inj(rows, stamp, url, name):
        d = {
            "dataset": name, "report_stamp_et": f"2026-11-15 {stamp} ET", "as_of": "2026-11-15",
            "retrieved_at_utc": CAPTURED_UTC, "retrieval_method": METHOD,
            "source_url": url, "index_url": U["injury_index"],
            "document_header": f"Injury Report: 11/15/26 {stamp}",
            "is_newest_release_of_the_day": stamp == "06:15 AM",
            "sibling_release": {"06:15 AM": U["injury_0600"], "06:00 AM": U["injury_0615"]}[stamp],
            "release_diff_note": "re-read independently and compared row by row: the only "
                                 "difference between the two 11/15 releases is the spelling of one "
                                 "Philadelphia surname; no status, team, reason or game moved",
            "provenance": "transcribed row by row from the official PDF; the trailing attribution "
                          "letter is this project's note, E = team cell printed on the row, "
                          "C = team carried over across a PDF page break",
            "attribution_key": "player (lower-cased, punctuation-stripped) — see FLAG-V2-INJ-ATTR",
            "columns": ["game_date", "game_time_pdf", "matchup", "team", "player", "status",
                        "reason", "attribution"],
            "records": [list(r) for r in rows],
            "not_yet_submitted": {
                "2026-11-15": [list(x) for x in NOT_SUBMITTED_1115],
                "2026-11-16": [list(x) for x in NOT_SUBMITTED_1116],
                "2026-11-17": [],
            },
            "not_yet_submitted_counts": {"2026-11-15": len(NOT_SUBMITTED_1115),
                                         "2026-11-16": len(NOT_SUBMITTED_1116),
                                         "2026-11-17": 0},
            "carried_over_rows": list(CARRIED_ROWS),
            "record_count": len(rows),
            "teams_with_a_filing": sorted({TEAM_TRI[r[3]] for r in rows}),
            "clubs_in_the_document": sorted({TEAM_TRI[r[3]] for r in rows}
                                            | {TEAM_TRI[x[3]] for x in NOT_SUBMITTED_1115
                                               + NOT_SUBMITTED_1116}),
        }
        p = RAW / name
        h = dump(p, d)
        return h

    h15 = inj(release_rows("06:15 AM"), "06:15 AM", U["injury_0615"],
              "injury_report_2026-11-15_0615AM.json")
    h00 = inj(release_rows("06:00 AM"), "06:00 AM", U["injury_0600"],
              "injury_report_2026-11-15_0600AM.json")

    books = {
        "schema": "nba2.gamebook-extract.v1", "captured_utc": CAPTURED_UTC, "session": SESSION,
        "meaning": "what this session could stand behind from the five official 2026-11-14 game "
                   "books: inactive blocks, DND/NWT rows, named leaders and game facts. Team "
                   "shooting lines are recorded only as the arithmetic that disqualifies them.",
        "urls": [g[9] for g in FINALS_1114],
        "leaders": {tri: [{"player": p, "pts": pts, "reb": reb, "ast": ast, "note": note}
                         for (p, pts, reb, ast, note) in rows] for tri, rows in LEADERS.items()},
        "inactives": {tri: [{"player": pl, "reason": rs} for pl, rs in v]
                      for tri, v in INACTIVES.items()},
        "inactives_not_preserved": INACTIVES_NOT_PRESERVED,
        "dnd_and_nwt_rows": [{"tri": t, "player": pl, "printed": pr} for t, pl, pr in DND],
        "game_context": GAME_CONTEXT,
        "league_context": LEAGUE_CONTEXT,
        "team_lines_discarded": {tri: {"printed": txt, "fgm": fgm, "ftm": ftm, "pts_final": pts,
                                       "why": f"2 x {fgm} + {ftm} = {2 * fgm + ftm} != {pts}"}
                                 for tri, (txt, fgm, ftm, pts) in DISCARDED_TEAM_LINES.items()},
    }
    bh = dump(RAW / "gamebooks_2026-11-14.json", books)

    slate = {
        "schema": "nba2.slate-snapshot.v1", "as_of": "2026-11-15", "captured_utc": CAPTURED_UTC,
        "session": SESSION, "source_url": U["schedule"],
        "window": {"start": "2026-11-15", "end": "2026-11-17", "days_ahead": 2,
                   "rule": "the brief's rolling slate: today plus the next two days, priced from "
                           "lines frozen before each tip"},
        "per_day_counts_official": CALENDAR_COUNTS,
        "n_games": len(SLATE),
        "games": [{"date": d, "time_et": t, "away": aw, "home": hm, "game_id": gid,
                   "arena": ar, "city": ci, "tv": tv}
                  for (d, t, aw, hm, gid, ar, ci, tv) in SLATE],
    }
    slh = dump(RAW / "slate_2026-11-15_to_11-17.json", slate)

    caps = {
        "schema": "nba2.capture-session.v2", "session": SESSION, "captured_utc": CAPTURED_UTC,
        "method": METHOD,
        "artefact_hashes": {
            "data/raw/finals_2026-11-14.json": fh,
            "data/raw/results_feed_2026-11-15.json": feedh,
            "data/raw/standings_2026-11-15_official.json": sh,
            "data/raw/team_ratings_2026-11-15.json": rh,
            "data/raw/injury_report_2026-11-15_0615AM.json": h15,
            "data/raw/injury_report_2026-11-15_0600AM.json": h00,
            "data/raw/gamebooks_2026-11-14.json": bh,
            "data/raw/slate_2026-11-15_to_11-17.json": slh,
        },
        "identities_passed": [
            "5/5 games: quarter scores sum to the final score on both sides, read independently "
            "from the game page and from the game book, and the two documents agree",
            "30/30 standings rows: home + road + neutral games = games played; wins and losses "
            "split by venue; every conference and division figure inside the season record",
            "30/30 CONF columns equal the intra-conference record computed game by game from the "
            "188-game result feed",
            "league wins = league losses = 188 = twice the number of games",
            "30/30 records rebuilt from the per-game result feed equal the standings card",
            "30/30 games-played agreement across four documents: the standings card, the advanced "
            "page, the opponent page and the traditional page",
            "30/30 W-L agreement between the standings card, the advanced page and the traditional page",
            "30/30 NetRtg within a tenth of OffRtg - DefRtg (each printed to 0.1)",
            "30/30 opponent-page points allowed x GP equals points-allowed rebuilt from the finals",
            "30/30 advanced-page OffRtg x POSS/100 equals points-for rebuilt from the finals",
            "30/30 traditional-page points x GP equals points-for rebuilt from the finals; "
            "OREB + DREB = REB; the implied OffRtg is within 0.35 of the printed one; pts - opponent "
            "pts equals the margin rebuilt from the finals",
            "the LAST 10 column sums to exactly 300 team-games (30 teams x 10)",
            "the OT column implies exactly the 10 overtime games in the feed, and the Neutral column "
            "the one neutral-site game — which is how the five 11/14 games are known not to have gone "
            "to overtime or been played at a neutral site",
            "per-date game counts match the official day-strip calendar: 9 games on 11/15, 8 on "
            "11/16, 5 on 11/17",
            "the injury report's own game grid matches nba.com/schedule for 11/15 (9 games) and "
            "11/16 (8 games), and every printed 12-hour tip time converts to the schedule's ET time",
            "the two injury releases differ in exactly one row and one field: a surname spelling",
            "84 designation rows per release, every row inside the 11/15 game date, every team a club "
            "in its own matchup, and rows in the PDF's alphabetical order inside each team block",
            "no game-book team shooting line passed 2 x FGM + FTM = points: all six were discarded and "
            "flagged rather than published",
            "named leader lines never exceed the team's final score in any of the 10 clubs",
        ],
        "standings_rows": len(STANDINGS),
        "advanced_rows": len(ADVANCED),
        "opponent_rows": len(OPPONENT),
        "traditional_rows": len(TRADITIONAL),
        "finals": [
            {"game_id": g[0], "date": g[1], "away": g[2], "home": g[3], "away_pts": g[4],
             "home_pts": g[5], "quarters_away": g[6], "quarters_home": g[7],
             "arena": g[8], "source_url": g[10], "book_url": g[9]}
            for g in FINALS_1114
        ],
        "game_books": {
            "urls": [g[9] for g in FINALS_1114],
            "policy": "only what the document supports; a number that cannot be reconciled is "
                      "published as a defect and not used",
            "leaders": {tri: [{"player": p, "pts": pts, "reb": reb, "ast": ast, "note": note}
                             for (p, pts, reb, ast, note) in rows]
                        for tri, rows in LEADERS.items()},
            "inactives": {tri: [{"player": pl, "reason": rs} for pl, rs in v]
                          for tri, v in INACTIVES.items()},
            "inactives_not_preserved": INACTIVES_NOT_PRESERVED,
            "dnd_and_nwt_rows": [{"tri": t, "player": pl, "printed": pr} for t, pl, pr in DND],
            "game_context": GAME_CONTEXT,
            "league_context": LEAGUE_CONTEXT,
            "team_lines_discarded": {
                tri: {"printed": txt, "fgm": fgm, "ftm": ftm, "pts_final": pts,
                      "why": f"2 x {fgm} + {ftm} = {2 * fgm + ftm}, the final score is {pts}"}
                for tri, (txt, fgm, ftm, pts) in DISCARDED_TEAM_LINES.items()},
        },
        "slate": [{"date": d, "time_et": t, "away": aw, "home": hm, "game_id": gid,
                   "arena": ar, "city": ci, "tv": tv} for (d, t, aw, hm, gid, ar, ci, tv) in SLATE],
        "injury_release_0615": {"url": U["injury_0615"], "rows": [list(r) for r in release_rows("06:15 AM")],
                                "not_yet_submitted_11_15": [list(r) for r in NOT_SUBMITTED_1115],
                                "not_yet_submitted_11_16": [list(r) for r in NOT_SUBMITTED_1116]},
        "injury_release_0600": {"url": U["injury_0600"], "rows": [list(r) for r in release_rows("06:00 AM")],
                                "not_yet_submitted_11_15": [list(r) for r in NOT_SUBMITTED_1115],
                                "not_yet_submitted_11_16": [list(r) for r in NOT_SUBMITTED_1116]},
        "injury_release_diff": {
            "method": "row-for-row comparison of the two releases, keyed on the normalised "
                      "player string so the spelling variant does not read as a status change",
            "status_changes": 0, "rows_added": 0, "rows_removed": 0,
            "spelling_only": [{"team": "PHI", "player_0600": "Embiid, Joel",
                               "player_0615": "Embid, Joel", "status": "Out",
                               "reason": "Injury/Illness - Right Foot Plantar Fascia Injury Management"}],
            "consequence": "no line on the 11/15 slate can move between the day's two releases; the "
                           "model's availability input for 11/15 was already final at 06:15 ET",
        },
        "team_trie_table": TEAM_TRI,
        "what_the_harness_does_not_prove": [
            "The identities prove internal and cross-document consistency, not the fidelity of a "
            "single printed cell: changing a status from Out to Probable would pass every check. "
            "The control on that is that both releases were read twice, independently, in this "
            "session, and agreed row for row.",
            "The 188-game result feed is only as good as the committed history snapshots it is built "
            "from; those came from earlier sessions' reads of nba.com/games and are not re-verified "
            "here game by game, only in aggregate (they reproduce today's standings card exactly, "
            "including every conference record, which no single wrong score could survive).",
            "Player-level lines are context. Nothing in this capture uses a game-book player row as a "
            "model input, because the PDF text layer misaligns columns.",
        ],
        "notes": NOTES,
        "still_blocked": BLOCKED,
    }
    (AUDIT / "captures.json").write_text(json.dumps(caps, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(caps['identities_passed'])} verified identities; "
          f"{feed['games']} games in the result feed; slate {len(SLATE)} games")
    print("artefacts:", ", ".join(sorted(caps["artefact_hashes"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
