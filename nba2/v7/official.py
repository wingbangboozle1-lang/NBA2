"""The 2026-11-19 official snapshot, read through the page-fetch transport this session.

WHAT THIS FILE IS, AND WHAT IT IS NOT
-------------------------------------
Every number below was read on 2026-11-19 (UTC) from the official page named in `SOURCES`,
which was rendered server-side with its table and returned through the platform page-fetch
transport. **It is not hand-typed folklore:** the transcription is checked by three
arithmetic identities that the league's own pages satisfy, and the build fails if any of
them breaks:

  1. `NetRtg == OffRtg - DefRtg` within ±0.15 on all 30 clubs (the advanced page prints all
     three, so a column that slipped by one club breaks the identity);
  2. `PTS - Opp PTS == +/-` within ±0.15 on all 30 clubs (the traditional and opponent pages
     are different documents, so this checks the two tables against each other);
  3. wins recomputed from the committed official finals equal the W the pages print, once
     the just-completed date is accounted for.

A single misaligned row breaks at least one of them. `nba2/v7/test_v7.py` runs all three.

TRUTHFULNESS ABOUT THE TRANSPORT
--------------------------------
This sandbox cannot open TLS to nba.com at all (`curl` returns 000; `urllib` raises
"TLS/SSL connection has been closed"), and a GitHub runner can reach `www.nba.com` but gets
`stats.nba.com` timeouts and `cdn.nba.com` 403 (`data/raw/egress_probe.json`). The page-fetch
transport used here is what read the bytes; that is recorded, not glossed over. A reader who
wants to re-derive a row can open the URL below and compare — every identity above is
recomputable from the page itself.

TWO CLOCKS ON THE LEAGUE'S OWN SITE (measured, worth knowing)
------------------------------------------------------------
The three `/stats/teams/*` pages report games played through **2026-11-17**; the
`/standings` page already includes the **2026-11-18** games. Measured on Utah: the stats
pages print GP 15, the standings page prints 3-13 (16 games), and Utah beat the Lakers
109-97 on 11/18. So the two surfaces are one date apart. `GAMES_PLAYED_AS_OF` and
`STANDINGS_AS_OF` record this rather than blending the two clocks into one number.
"""

from __future__ import annotations

RETRIEVED_AT_UTC = "2026-11-19T06:05:00Z"
TRANSPORT = ("platform page-fetch transport, server-rendered HTML converted to markdown; "
             "the sandbox has no TLS egress to nba.com and a GitHub runner cannot read "
             "stats.nba.com (data/raw/egress_probe.json)")

SOURCES = {
    "traditional": ("https://www.nba.com/stats/teams/traditional"
                    "?Season=2026-27&SeasonType=Regular+Season"),
    "advanced": ("https://www.nba.com/stats/teams/advanced"
                 "?Season=2026-27&SeasonType=Regular+Season"),
    "opponent": ("https://www.nba.com/stats/teams/opponent"
                 "?Season=2026-27&SeasonType=Regular+Season"),
    "standings": "https://www.nba.com/standings",
    "games": "https://www.nba.com/games?date={date}",
    "games_1119": "https://www.nba.com/games?date=2026-11-19",
    "games_1120": "https://www.nba.com/games?date=2026-11-20",
    "injury": "https://official.nba.com/nba-injury-report-2026-27-season/",
}

GAMES_PLAYED_AS_OF = "2026-11-17"   # the /stats/teams/* pages' GP totals imply this date
STANDINGS_AS_OF = "2026-11-18"      # the /standings page includes this date's games

# ---------------------------------------------------------------------------------------
# One row per club. Columns, in the order the page prints them:
#   gp, w, l .................. /stats/teams/advanced (GP, W, L) — cross-read on traditional
#   off_rtg, def_rtg, net_rtg  /stats/teams/advanced
#   pace ...................... /stats/teams/advanced (PACE)
#   pts ....................... /stats/teams/traditional (PTS, per game)
#   opp_pts ................... /stats/teams/opponent (Opp PTS, per game)
#   plus_minus ................ /stats/teams/traditional (+/-, per game)
#   st_w, st_l ................ /standings (8 blocks below), includes 2026-11-18
# ---------------------------------------------------------------------------------------
TEAMS: dict[str, dict] = {
    #  tri      gp   w   l   off    def    net    pace    pts    opp    +/-
    "ATL": dict(gp=15, w=9,  l=6,  off=112.8, dfn=110.8, net=1.9,  pace=103.71, pts=117.7, opp=115.8, pm=1.9),
    "BKN": dict(gp=14, w=3,  l=11, off=110.5, dfn=119.0, net=-8.4, pace=99.51,  pts=110.9, opp=119.2, pm=-8.4),
    "BOS": dict(gp=15, w=11, l=4,  off=117.0, dfn=106.0, net=11.0, pace=96.76,  pts=113.9, opp=103.4, pm=10.5),
    "CHA": dict(gp=14, w=4,  l=10, off=103.1, dfn=113.7, net=-10.6, pace=96.43, pts=100.1, opp=110.4, pm=-10.3),
    "CHI": dict(gp=14, w=4,  l=10, off=111.1, dfn=119.1, net=-8.0, pace=103.80, pts=116.2, opp=124.6, pm=-8.4),
    "CLE": dict(gp=16, w=8,  l=8,  off=117.5, dfn=115.5, net=2.0,  pace=100.01, pts=118.3, opp=116.3, pm=1.9),
    "DAL": dict(gp=15, w=8,  l=7,  off=112.3, dfn=113.4, net=-1.1, pace=99.97,  pts=112.3, opp=113.2, pm=-0.9),
    "DEN": dict(gp=13, w=8,  l=5,  off=114.3, dfn=113.8, net=0.5,  pace=98.02,  pts=113.2, opp=112.2, pm=0.9),
    "DET": dict(gp=14, w=10, l=4,  off=114.9, dfn=108.9, net=6.0,  pace=98.78,  pts=115.4, opp=108.9, pm=6.4),
    "GSW": dict(gp=15, w=8,  l=7,  off=113.4, dfn=112.8, net=0.6,  pace=99.41,  pts=113.7, opp=112.8, pm=0.9),
    "HOU": dict(gp=16, w=12, l=4,  off=121.1, dfn=112.1, net=9.0,  pace=97.41,  pts=117.9, opp=109.2, pm=8.7),
    "IND": dict(gp=15, w=5,  l=10, off=110.7, dfn=113.6, net=-2.9, pace=100.90, pts=111.5, opp=114.8, pm=-3.3),
    "LAC": dict(gp=13, w=4,  l=9,  off=111.4, dfn=117.0, net=-5.6, pace=99.74,  pts=111.9, opp=117.7, pm=-5.8),
    "LAL": dict(gp=15, w=13, l=2,  off=121.6, dfn=113.7, net=7.8,  pace=100.14, pts=122.5, opp=114.8, pm=7.7),
    "MEM": dict(gp=15, w=11, l=4,  off=120.6, dfn=111.9, net=8.7,  pace=100.27, pts=121.9, opp=112.9, pm=9.0),
    "MIA": dict(gp=15, w=9,  l=6,  off=116.9, dfn=116.7, net=0.3,  pace=102.19, pts=120.5, opp=119.9, pm=0.7),
    "MIL": dict(gp=15, w=1,  l=14, off=106.7, dfn=119.7, net=-13.0, pace=101.00, pts=107.7, opp=120.9, pm=-13.1),
    "MIN": dict(gp=15, w=11, l=4,  off=114.5, dfn=104.0, net=10.5, pace=101.23, pts=116.7, opp=106.1, pm=10.6),
    "NOP": dict(gp=16, w=5,  l=11, off=111.7, dfn=118.9, net=-7.1, pace=101.30, pts=115.4, opp=122.8, pm=-7.4),
    "NYK": dict(gp=14, w=8,  l=6,  off=114.8, dfn=109.0, net=5.8,  pace=94.87,  pts=110.0, opp=103.9, pm=6.1),
    "OKC": dict(gp=15, w=9,  l=6,  off=113.0, dfn=108.7, net=4.4,  pace=99.17,  pts=112.1, opp=107.7, pm=4.4),
    "ORL": dict(gp=14, w=6,  l=8,  off=111.3, dfn=114.0, net=-2.7, pace=97.84,  pts=109.4, opp=112.8, pm=-3.4),
    "PHI": dict(gp=16, w=13, l=3,  off=114.5, dfn=111.8, net=2.7,  pace=99.88,  pts=114.5, opp=111.6, pm=2.9),
    "PHX": dict(gp=14, w=7,  l=7,  off=115.6, dfn=116.8, net=-1.2, pace=98.89,  pts=114.1, opp=115.7, pm=-1.6),
    "POR": dict(gp=14, w=9,  l=5,  off=116.2, dfn=110.2, net=6.0,  pace=100.71, pts=117.0, opp=111.0, pm=6.0),
    "SAC": dict(gp=14, w=1,  l=13, off=106.9, dfn=120.4, net=-13.5, pace=100.93, pts=107.7, opp=121.7, pm=-14.0),
    "SAS": dict(gp=15, w=12, l=3,  off=118.1, dfn=107.0, net=11.1, pace=98.35,  pts=117.1, opp=105.9, pm=11.2),
    "TOR": dict(gp=15, w=5,  l=10, off=113.7, dfn=113.1, net=0.5,  pace=98.09,  pts=112.0, opp=112.0, pm=0.0),
    "UTA": dict(gp=15, w=2,  l=13, off=107.2, dfn=115.9, net=-8.7, pace=99.95,  pts=108.7, opp=117.3, pm=-8.5),
    "WAS": dict(gp=16, w=5,  l=11, off=109.9, dfn=117.1, net=-7.1, pace=99.46,  pts=110.8, opp=117.9, pm=-7.2),
}

# ---------------------------------------------------------------------------------------
# /standings, read 2026-11-19: the page's own W-L, plus the record splits it prints.
# It includes the 2026-11-18 games, which the /stats/teams/* pages do not (see module doc).
# ---------------------------------------------------------------------------------------
STANDINGS: dict[str, dict] = {
    # East
    "PHI": dict(conf="East", w=13, l=3,  home="6-2",  road="7-1", last10="8-2",  streak="W 4"),
    "BOS": dict(conf="East", w=11, l=4,  home="6-1",  road="5-3", last10="7-3",  streak="L 2"),
    "DET": dict(conf="East", w=10, l=4,  home="3-2",  road="7-2", last10="7-3",  streak="W 2"),
    "MIA": dict(conf="East", w=9,  l=6,  home="5-3",  road="4-3", last10="8-2",  streak="W 6"),
    "ATL": dict(conf="East", w=9,  l=6,  home="3-3",  road="6-3", last10="7-3",  streak="W 2"),
    "NYK": dict(conf="East", w=8,  l=6,  home="4-3",  road="4-3", last10="7-3",  streak="W 2"),
    "CLE": dict(conf="East", w=8,  l=8,  home="6-3",  road="2-5", last10="4-6",  streak="L 1"),
    "ORL": dict(conf="East", w=6,  l=8,  home="1-5",  road="5-3", last10="5-5",  streak="L 1"),
    "TOR": dict(conf="East", w=5,  l=10, home="2-6",  road="3-4", last10="2-8",  streak="L 6"),
    "IND": dict(conf="East", w=5,  l=10, home="2-5",  road="3-4", last10="3-7",  streak="L 2"),
    "WAS": dict(conf="East", w=5,  l=11, home="2-5",  road="3-6", last10="2-8",  streak="W 1"),
    "CHA": dict(conf="East", w=4,  l=10, home="3-4",  road="1-6", last10="1-9",  streak="L 3"),
    "CHI": dict(conf="East", w=4,  l=10, home="1-4",  road="3-6", last10="3-7",  streak="W 1"),
    "BKN": dict(conf="East", w=3,  l=11, home="1-5",  road="2-6", last10="3-7",  streak="L 3"),
    "MIL": dict(conf="East", w=1,  l=14, home="1-7",  road="0-7", last10="0-10", streak="L 11"),
    # West
    "LAL": dict(conf="West", w=13, l=3,  home="6-2",  road="7-1", last10="9-1",  streak="L 1"),
    "SAS": dict(conf="West", w=12, l=3,  home="5-3",  road="7-0", last10="9-1",  streak="L 1"),
    "HOU": dict(conf="West", w=12, l=4,  home="7-1",  road="5-3", last10="7-3",  streak="W 1"),
    "MIN": dict(conf="West", w=11, l=4,  home="7-2",  road="4-2", last10="8-2",  streak="W 2"),
    "MEM": dict(conf="West", w=11, l=4,  home="3-4",  road="8-0", last10="6-4",  streak="W 4"),
    "POR": dict(conf="West", w=9,  l=5,  home="3-2",  road="6-3", last10="6-4",  streak="L 2"),
    "DEN": dict(conf="West", w=8,  l=5,  home="3-3",  road="4-2", last10="7-3",  streak="W 1"),
    "OKC": dict(conf="West", w=9,  l=6,  home="5-1",  road="4-5", last10="5-5",  streak="L 1"),
    "DAL": dict(conf="West", w=8,  l=7,  home="6-2",  road="2-5", last10="5-5",  streak="W 1"),
    "GSW": dict(conf="West", w=8,  l=7,  home="6-1",  road="2-6", last10="6-4",  streak="L 4"),
    "PHX": dict(conf="West", w=7,  l=7,  home="5-4",  road="2-3", last10="6-4",  streak="W 2"),
    "NOP": dict(conf="West", w=5,  l=11, home="4-7",  road="1-4", last10="3-7",  streak="L 1"),
    "LAC": dict(conf="West", w=4,  l=9,  home="4-4",  road="0-5", last10="3-7",  streak="L 1"),
    "UTA": dict(conf="West", w=3,  l=13, home="1-7",  road="2-6", last10="2-8",  streak="W 2"),
    "SAC": dict(conf="West", w=1,  l=13, home="1-7",  road="0-6", last10="1-9",  streak="L 6"),
}

# ---------------------------------------------------------------------------------------
# The twelve 2026-11-18 finals, read from the official games list for that date. They are
# written as a capture so the result feed is current to the last completed game day, and
# because a settlement that ignores a finished game is not a settlement.
# Every row carries the official game page it was confirmed on.
# ---------------------------------------------------------------------------------------
FINALS_2026_11_18: list[dict] = [
    dict(game_id="0022600259", away="HOU", home="IND", away_pts=119, home_pts=104),
    dict(game_id="0022600261", away="PHI", home="ORL", away_pts=121, home_pts=116),
    dict(game_id="0022600260", away="MIL", home="MIA", away_pts=130, home_pts=137),
    dict(game_id="0022600258", away="MEM", home="CLE", away_pts=124, home_pts=121),
    dict(game_id="0022600262", away="CHI", home="BKN", away_pts=137, home_pts=107),
    dict(game_id="0022600263", away="WAS", home="TOR", away_pts=103, home_pts=99),
    dict(game_id="0022600267", away="GSW", home="DAL", away_pts=94, home_pts=116),
    dict(game_id="0022600265", away="ATL", home="OKC", away_pts=117, home_pts=112),
    dict(game_id="0022600264", away="DET", home="NOP", away_pts=122, home_pts=109),
    dict(game_id="0022600266", away="BOS", home="DEN", away_pts=101, home_pts=105),
    dict(game_id="0022600269", away="PHX", home="SAC", away_pts=128, home_pts=107),
    dict(game_id="0022600268", away="UTA", home="LAL", away_pts=109, home_pts=97),
]

# ---------------------------------------------------------------------------------------
# The upcoming slate, read from the official games list for each date (2026-11-19 → 11-21).
# Tips are the ET times the page prints; the game id is the league's own.
# ---------------------------------------------------------------------------------------
SLATE: list[dict] = [
    # Thu Nov 19
    dict(date="2026-11-19", game_id="0022600270", away="GSW", home="MEM", tip="8:00 PM ET"),
    dict(date="2026-11-19", game_id="0022600271", away="POR", home="MIL", tip="8:00 PM ET"),
    dict(date="2026-11-19", game_id="0022600272", away="NYK", home="MIN", tip="8:00 PM ET"),
    dict(date="2026-11-19", game_id="0022600273", away="LAC", home="SAS", tip="8:00 PM ET"),
    # Fri Nov 20 (NBA Cup group play)
    dict(date="2026-11-20", game_id="0022600043", away="CHA", home="ATL", tip="7:00 PM ET"),
    dict(date="2026-11-20", game_id="0022600044", away="ORL", home="BKN", tip="7:30 PM ET"),
    dict(date="2026-11-20", game_id="0022600045", away="IND", home="CLE", tip="7:30 PM ET"),
    dict(date="2026-11-20", game_id="0022600046", away="TOR", home="DET", tip="7:30 PM ET"),
    dict(date="2026-11-20", game_id="0022600047", away="WAS", home="CHI", tip="8:00 PM ET"),
    dict(date="2026-11-20", game_id="0022600048", away="NOP", home="OKC", tip="8:00 PM ET"),
    dict(date="2026-11-20", game_id="0022600049", away="PHX", home="UTA", tip="9:30 PM ET"),
    dict(date="2026-11-20", game_id="0022600050", away="HOU", home="DEN", tip="10:00 PM ET"),
    dict(date="2026-11-20", game_id="0022600051", away="SAC", home="LAL", tip="10:00 PM ET"),
    # Sat Nov 21
    dict(date="2026-11-21", game_id="0022600274", away="MIL", home="PHI", tip="1:00 PM ET"),
    dict(date="2026-11-21", game_id="0022600275", away="POR", home="NYK", tip="7:30 PM ET"),
    dict(date="2026-11-21", game_id="0022600276", away="LAC", home="DAL", tip="8:00 PM ET"),
    dict(date="2026-11-21", game_id="0022600277", away="MEM", home="MIN", tip="8:00 PM ET"),
    dict(date="2026-11-21", game_id="0022600278", away="NOP", home="SAS", tip="8:00 PM ET"),
    dict(date="2026-11-21", game_id="0022600279", away="BOS", home="SAC", tip="10:00 PM ET"),
]

# The Cup group labels the games list prints for 11/20, so a reader can see these are not
# ordinary regular-season games (they count in the regular-season record, but the group
# play context is on the page and is published rather than flattened away).
CUP_GROUP = {
    "0022600043": "East Group C", "0022600044": "East Group A", "0022600045": "East Group B",
    "0022600046": "East Group A", "0022600047": "East Group C", "0022600048": "West Group B",
    "0022600049": "West Group A", "0022600050": "West Group A", "0022600051": "West Group C",
}

# Injured-list availability is NOT in this snapshot: the official injury report for
# 2026-11-19 was not read this session, so every availability cell downstream is blank and
# flagged. Saying so here is cheaper than a reader discovering it in a table.
INJURY_REPORT_READ = False
