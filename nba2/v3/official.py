"""Official NBA snapshot captured by session `arena/1eeb6a21-nba2` on 2026-11-17.

This file supersedes the 2026-11-15 snapshot by `arena/e675ac3d-nba2` (same schema, same
public names, new capture). The 2026-11-15 module had gone stale: its pick window ended
11/18 and its team-stat rows predates the eight 11/16 finals. Every value below was read
from the page named in ``SOURCES`` through the platform page-fetch tool during this
session (direct TLS egress to nba.com is blocked in this sandbox; that limitation is
recorded, not worked around). Nothing is inferred, nothing is imputed, and no number is
carried over from an earlier session's snapshot except the five 11/14 finals rows, which
are kept verbatim from the previous snapshot (their provenance is unchanged).

Retrieval record
----------------
Retrieved 2026-11-17, 15:20-17:10 UTC (10:20-12:10 ET).

* ``www.nba.com/schedule`` (several chunks, dates 11/16 and 11/20) ... full slate
  11/17-11/20 with official game IDs, ET tips, arenas, city/state; the eight official
  11/16 finals with "Final" badges; the 11/17/18/19/20 game pages used to confirm tips.
* ``www.nba.com/standings`` (chunks 0-1) ..................... 30 clubs: W, L, WIN%, GB,
  conference/division records, HOME, ROAD, NEUTRAL, OT, LAST10, streak.
* ``www.nba.com/stats/teams/advanced?...PerGame`` (chunks 0-1)  30 rows: GP, W, L, MIN,
  OffRtg, DefRtg, NetRtg, TOV%, OREB%, DREB%, PACE, POSS, eFG%.
* ``www.nba.com/stats/teams/opponent?...`` (chunks 0-1) ..... 30 rows: Opp PTS per game.
* ``www.nba.com/stats/teams/traditional?...`` (chunks 0-4) .. 30 rows: PTS per game —
  ALL 30 clubs were inside the fetched chunks this time, so the derived-points
  cross-check of the previous snapshot (which had read only 16 of 30) now covers the
  full league.
* ``ak-static.cms.nba.com/.../Injury-Report_2026-11-17_11_00AM.pdf`` (single chunk) ...
  today's game-day release: 33 player rows for the five 11/17 games filed so far plus
  26 explicit NOT YET SUBMITTED team rows (POR@MIN at 11:00 AM, and all 16 clubs for
  11/18 whose day-before deadline had not yet passed).
* Gamebook PDFs ``statsdmz.nba.com/pdfs/20261116/20261116_*_book.pdf`` (8 documents) ..
  the eight 11/16 finals with quarter rows and per-club totals. These are transcribed in
  ``data/raw/results/results_2026-11-16.json`` and ``data/v5/gamebooks_2026-11-16.json``
  by this session; the finals rows are mirrored into ``RESULTS`` here.
* ``data/raw/refresh_2026-11-15/results_2026-11-15.json`` (committed capture of
  2026-11-15) ................................................ the nine 11/15 finals with
  quarter rows. These are committed repo data already verified by the v4 settlement
  (digest-checked seals) and the v5 gates; they are mirrored here with their provenance
  so the rolling model's rest/back-to-back calculations see every game since 11/14.

Two mechanical cross-checks this snapshot passes (asserted in ``selftest``):
1. the 30 W/L records sum to 205 wins and 205 losses — exactly the 183 historical finals
   plus the 5 finals of 11/14, the 9 finals of 11/15 and the 8 finals of 11/16;
2. for every club, ``pts_for - pts_against`` agrees with ``net_rtg x poss / 100`` to
   within 0.2 points per game, and the traditional-page PTS read agrees with the derived
   points-scored figure to within 2.5 points per game (possessions estimated
   differently on the two pages).
"""

from __future__ import annotations

AS_OF_UTC = "2026-11-17T17:05:00Z"
AS_OF_ET = "2026-11-17 12:05 ET"
SESSION = "arena/1eeb6a21-nba2"
WINDOW = ("2026-11-17", "2026-11-20")  # T+0 .. T+3 inclusive

SOURCES = {
    "standings": (
        "NBA.com Standings (official)",
        "https://www.nba.com/standings",
        "W, L, WIN%, GB, conference and division records, home/road/neutral splits, "
        "OT record, LAST10, streak.",
    ),
    "team_adv": (
        "NBA.com Stats - Teams Advanced (official)",
        "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "GP, MIN, OffRtg, DefRtg, NetRtg, PACE, POSS, eFG%, TS%, TOV%, OREB%, DREB%, AST%.",
    ),
    "team_opp": (
        "NBA.com Stats - Teams Opponent (official)",
        "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "Opponent points per game (points allowed) and the opponent +/- column.",
    ),
    "team_trad": (
        "NBA.com Stats - Teams Traditional (official)",
        "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "PTS per game, read for ALL 30 clubs this session (see PTS_READ), FGA, 3PA, FTA, "
        "REB, AST, TOV.",
    ),
    "schedule": (
        "NBA.com Schedule (official)",
        "https://www.nba.com/schedule",
        "Game IDs, ET tip times, arena, city and state for 11/17-11/20, and the official "
        "final scores of the completed 11/16 games.",
    ),
    "injury_pdf": (
        "NBA Official Injury Report 11/17/26 11:00 AM ET (official PDF)",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_11_00AM.pdf",
        "Per-player status (Out / Doubtful / Available) with the stated reason, plus "
        "explicit NOT YET SUBMITTED team rows.",
    ),
    "injury_index": (
        "NBA Official - injury report policy and release archive (official)",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
        "Filing deadlines and the list of every published report for the season.",
    ),
    "linescore": (
        "Official NBA gamebook PDFs (statsdmz.nba.com)",
        "https://statsdmz.nba.com/pdfs/20261115/20261115_INDPHI_book.pdf",
        "Quarter-by-quarter scoring for the results feed (kept as a key for the results "
        "table's source column; the 11/14 linescore provenance is unchanged, 11/15-11/16 "
        "quarters come from the official gamebook PDFs).",
    ),
    "gamebooks": (
        "Official NBA gamebook PDFs (statsdmz.nba.com)",
        "https://statsdmz.nba.com/pdfs/20261116/20261116_PHIBKN_book.pdf",
        "Final scores, quarter rows and club totals for the eight 11/16 games; the "
        "transcription lives in data/raw/results/results_2026-11-16.json.",
    ),
    "results_1115": (
        "NBA.com Schedule 2026-11-15 + committed results feed (official gamebook PDFs)",
        "https://www.nba.com/schedule?date=2026-11-15",
        "The nine 11/15 finals with quarter rows, mirrored into RESULTS below from the "
        "committed feed data/raw/refresh_2026-11-15/results_2026-11-15.json (official "
        "gamebook PDFs, verified by the v4 settlement digest check).",
    ),
}

# Why an input is absent. Published verbatim next to every blank cell.
BLOCKED = {
    "odds": (
        "Market prices (spread, total, moneyline, prop lines)",
        "No licensed odds feed is connected and NBA.com renders odds client-side only. "
        "Without a price there is no edge, no CLV, no ROI and no stake sizing, so every "
        "bet-surface stake is held at 0.00 and only a trigger price is published.",
        "https://www.nba.com/games",
    ),
    "player_minutes": (
        "Per-player minutes and usage (v3 surface)",
        "nba.com/stats/players/traditional is reachable but the ten-page capture was "
        "outside this session's context budget. The per-game book for 11/14-11/16 now "
        "exists on the v5 surface (data/v5/gamebooks_*.json); the v3 rotation model "
        "keeps its own capture requirement and its per-player shares stay blank here.",
        "https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
    ),
    "player_logs": (
        "Per-player game logs (minutes, points, rebounds, assists, opponent)",
        "The official player pages render season aggregates only for this client; there "
        "is no per-game log endpoint reachable here. The v5 gamebook transcripts "
        "(data/v5/gamebooks_2026-11-14/15/16.json) now carry min/pts/reb/ast/opponent "
        "for every player of those dates.",
        "https://www.nba.com/stats/players/traditional",
    ),
    "arena_coords": (
        "Arena latitude / longitude",
        "NBA.com publishes the arena name, city and state (captured below) but no "
        "coordinates, and no official geocoder is reachable from this environment. "
        "Travel distance is therefore blank rather than estimated.",
        "https://www.nba.com/schedule",
    ),
    "quarters": (
        "Quarter scores for four of the five 11/14 finals",
        "The official LINESCORES table was fetched for 0022600231 only in the 2026-11-15 "
        "session; the other four 11/14 rows keep their game URL and a blank quarter "
        "column. Quarters ARE present for all 9 finals of 11/15 (except the DAL away row, "
        "blank in the committed feed) and all 8 finals of 11/16 (gamebook PDFs).",
        "https://www.nba.com/games?date=2026-11-14",
    ),
    "future_injuries": (
        "Injury rows for 11/19 and 11/20",
        "A club files by 5 p.m. local the day before a game, so no report published at "
        "12:05 ET on 11/17 can contain filed 11/19 or 11/20 rows. The 11/18 clubs print "
        "NOT YET SUBMITTED in the 11:00 AM release. Blank by league rule.",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
    ),
}

# --------------------------------------------------------------------------- teams
# abbr, name, W, L, homeW, homeL, roadW, roadL, GP, MIN, OffRtg, DefRtg, NetRtg,
# PACE, POSS, eFG%, TOV%, OREB%, DREB%, OppPTS, PTS_read
_T = """
LAL|Los Angeles Lakers|12|2|7|0|5|2|14|672.0|122.1|114.0|8.0|100.64|1408|58.8|16.7|33.3|64.1|114.9|122.8
SAS|San Antonio Spurs|12|2|6|1|6|1|14|677.0|119.2|106.6|12.6|98.77|1395|53.5|12.3|33.3|71.8|105.9|118.8
PHI|Philadelphia 76ers|12|3|6|2|6|1|15|720.0|113.7|111.1|2.6|100.23|1505|53.0|12.6|28.4|71.6|111.3|114.1
BOS|Boston Celtics|11|3|7|1|4|2|14|677.0|118.2|106.1|12.1|96.53|1360|55.3|14.8|32.7|68.0|103.3|114.8
HOU|Houston Rockets|11|4|4|3|7|1|15|720.0|120.9|112.3|8.6|97.50|1462|55.3|14.8|36.7|68.1|109.5|117.8
MEM|Memphis Grizzlies|10|4|5|3|5|1|14|677.0|120.0|110.9|9.1|100.61|1420|56.4|15.8|34.7|70.7|112.3|121.7
MIN|Minnesota Timberwolves|10|4|5|2|5|2|14|677.0|115.2|104.1|11.1|101.21|1427|54.7|15.4|35.2|69.8|106.1|117.4
POR|Portland Trail Blazers|9|4|5|1|4|3|13|624.0|117.2|110.6|6.6|100.65|1308|55.4|16.1|32.6|69.8|111.4|117.9
OKC|Oklahoma City Thunder|9|5|4|3|5|2|14|672.0|113.4|108.4|5.1|98.82|1384|51.9|13.5|32.1|68.7|107.1|112.1
ATL|Atlanta Hawks|8|6|4|3|4|3|14|677.0|112.8|111.1|1.7|103.69|1462|52.7|14.7|33.0|69.2|116.1|117.8
CLE|Cleveland Cavaliers|8|7|4|4|4|3|15|725.0|116.9|114.7|2.2|100.30|1515|55.9|13.9|30.0|68.4|115.8|118.1
DET|Detroit Pistons|8|4|5|1|3|3|12|586.0|114.1|109.2|4.9|99.48|1217|53.9|14.1|29.8|66.6|110.3|115.7
GSW|Golden State Warriors|8|6|3|4|5|2|14|677.0|114.6|112.3|2.2|99.58|1406|54.3|15.9|32.4|68.2|112.6|115.1
MIA|Miami Heat|8|6|6|1|2|5|14|677.0|116.0|116.2|-0.1|101.96|1440|54.9|13.6|30.4|68.8|119.1|119.4
DAL|Dallas Mavericks|7|7|2|5|5|2|14|672.0|111.8|114.5|-2.7|100.18|1404|53.2|16.0|32.9|66.0|114.6|112.1
DEN|Denver Nuggets|7|5|4|1|3|4|12|581.0|115.1|114.9|0.2|97.86|1187|54.9|13.9|29.9|66.9|113.2|113.8
NYK|New York Knicks|7|6|3|4|4|2|13|629.0|113.7|108.2|5.5|95.66|1257|51.9|15.2|36.7|71.8|104.0|109.9
ORL|Orlando Magic|6|7|3|3|3|4|13|629.0|110.5|113.0|-2.6|98.10|1281|53.2|16.8|31.4|70.6|112.2|108.8
PHX|Phoenix Suns|6|7|3|3|3|4|13|624.0|114.5|117.5|-3.0|98.88|1283|54.6|14.6|30.9|62.5|116.4|113.0
IND|Indiana Pacers|5|9|4|4|1|5|14|672.0|110.9|112.9|-2.0|101.25|1415|53.8|14.3|24.6|68.5|114.5|112.1
NOP|New Orleans Pelicans|5|10|0|8|5|2|15|735.0|111.7|118.4|-6.7|101.62|1555|51.8|15.2|30.1|68.2|122.9|115.8
TOR|Toronto Raptors|5|8|2|5|3|3|13|629.0|113.6|112.2|1.4|99.55|1302|51.7|14.4|35.8|67.2|112.8|113.8
CHA|Charlotte Hornets|4|9|2|5|2|4|13|624.0|102.5|113.6|-11.1|96.65|1256|48.0|20.0|36.5|74.2|109.8|99.1
LAC|LA Clippers|4|8|3|3|1|5|12|581.0|111.4|115.3|-3.9|100.05|1210|55.1|17.6|29.6|66.0|116.5|112.3
WAS|Washington Wizards|4|11|1|7|3|4|15|730.0|109.9|117.6|-7.8|99.91|1519|51.7|14.5|28.8|65.1|119.2|111.3
BKN|Brooklyn Nets|3|10|1|6|2|4|13|629.0|110.8|117.4|-6.6|99.55|1304|53.2|17.1|31.6|69.1|117.8|111.2
CHI|Chicago Bulls|3|10|2|5|1|5|13|629.0|109.1|120.0|-10.9|104.17|1366|51.8|16.5|30.6|64.6|125.9|114.6
MIL|Milwaukee Bucks|1|13|1|6|0|7|14|672.0|105.4|118.9|-13.6|100.68|1410|50.9|16.7|30.5|64.6|119.7|106.1
SAC|Sacramento Kings|1|12|1|6|0|6|13|624.0|106.8|119.8|-13.0|101.08|1312|52.7|17.3|28.4|68.8|121.2|107.8
UTA|Utah Jazz|1|13|1|7|0|6|14|682.0|105.1|116.2|-11.1|100.22|1426|50.8|16.3|29.0|69.3|118.0|107.1
"""

CONF = {t: ("East" if t in {
    "BOS", "PHI", "DET", "MIA", "ATL", "CLE", "NYK", "TOR", "ORL", "IND",
    "CHA", "WAS", "BKN", "CHI", "MIL"} else "West") for t in
    ["LAL", "SAS", "BOS", "HOU", "PHI", "MEM", "MIN", "POR", "DET", "GSW", "OKC",
     "ATL", "CLE", "DAL", "DEN", "MIA", "NYK", "IND", "ORL", "PHX", "TOR", "CHA",
     "NOP", "WAS", "BKN", "CHI", "LAC", "MIL", "SAC", "UTA"]}


def _teams():
    out = {}
    for line in _T.strip().splitlines():
        f = line.split("|")
        ab = f[0]
        read = None if f[20] == "None" else float(f[20])
        gp = int(f[8])
        poss = int(f[14].replace(",", ""))
        out[ab] = {
            "abbr": ab, "name": f[1], "conf": CONF[ab],
            "w": int(f[2]), "l": int(f[3]),
            "home_w": int(f[4]), "home_l": int(f[5]),
            "road_w": int(f[6]), "road_l": int(f[7]),
            "gp": int(f[8]), "min": float(f[9]),
            "off_rtg": float(f[10]), "def_rtg": float(f[11]), "net_rtg": float(f[12]),
            "pace": float(f[13]), "poss": int(f[14].replace(",", "")),
            "efg": float(f[15]), "tov_pct": float(f[16]),
            "oreb_pct": float(f[17]), "dreb_pct": float(f[18]),
            "opp_pts": float(f[19]),           # official: points allowed per game (opponent page)
            "pts_read": read,                  # official: points scored per game (all 30 clubs)
            # Both scoring columns are DERIVED from the same official row (OffRtg, DefRtg,
            # POSS, GP) so that margin is internally consistent with NetRtg. The two
            # official reads above are kept as independent cross-checks, never blended.
            "pts_for": round(float(f[10]) * poss / (100.0 * gp), 2),
            "pts_against": round(float(f[11]) * poss / (100.0 * gp), 2),
            "src": "team_adv",
            "src_opp": "team_opp",
            "src_rec": "standings",
        }
    return out


TEAMS = _teams()
PTS_READ = {a: t["pts_read"] for a, t in TEAMS.items() if t["pts_read"] is not None}

# --------------------------------------------------------------------------- slate
# game_id, date, away, home, time_et, arena, city, state
_S = """
0022600253|2026-11-17|NYK|TOR|7:30 PM|Scotiabank Arena|Toronto|ON
0022600254|2026-11-17|POR|MIN|8:00 PM|Target Center|Minneapolis|MN
0022600255|2026-11-17|DET|SAS|8:00 PM|Frost Bank Center|San Antonio|TX
0022600256|2026-11-17|CHA|LAL|11:00 PM|Crypto.com Arena|Los Angeles|CA
0022600257|2026-11-17|UTA|LAC|10:30 PM|Intuit Dome|Inglewood|CA
0022600258|2026-11-18|MEM|CLE|7:00 PM|Rocket Arena|Cleveland|OH
0022600259|2026-11-18|HOU|IND|7:00 PM|Gainbridge Fieldhouse|Indianapolis|IN
0022600260|2026-11-18|MIL|MIA|7:00 PM|Kaseya Center|Miami|FL
0022600261|2026-11-18|PHI|ORL|7:00 PM|Kia Center|Orlando|FL
0022600262|2026-11-18|CHI|BKN|7:30 PM|Barclays Center|Brooklyn|NY
0022600263|2026-11-18|WAS|TOR|7:30 PM|Scotiabank Arena|Toronto|ON
0022600264|2026-11-18|DET|NOP|8:00 PM|Smoothie King Center|New Orleans|LA
0022600265|2026-11-18|ATL|OKC|8:00 PM|Paycom Center|Oklahoma City|OK
0022600266|2026-11-18|BOS|DEN|9:30 PM|Ball Arena|Denver|CO
0022600267|2026-11-18|GSW|DAL|8:00 PM|American Airlines Center|Dallas|TX
0022600268|2026-11-18|UTA|LAL|10:00 PM|Crypto.com Arena|Los Angeles|CA
0022600269|2026-11-18|PHX|SAC|10:00 PM|Golden 1 Center|Sacramento|CA
0022600270|2026-11-19|GSW|MEM|8:00 PM|FedExForum|Memphis|TN
0022600271|2026-11-19|POR|MIL|8:00 PM|Fiserv Forum|Milwaukee|WI
0022600272|2026-11-19|NYK|MIN|8:00 PM|Target Center|Minneapolis|MN
0022600273|2026-11-19|LAC|SAS|8:00 PM|Frost Bank Center|San Antonio|TX
0022600043|2026-11-20|CHA|ATL|7:00 PM|State Farm Arena|Atlanta|GA
0022600044|2026-11-20|ORL|BKN|7:30 PM|Barclays Center|Brooklyn|NY
0022600045|2026-11-20|IND|CLE|7:30 PM|Rocket Arena|Cleveland|OH
0022600046|2026-11-20|TOR|DET|7:30 PM|Little Caesars Arena|Detroit|MI
0022600047|2026-11-20|WAS|CHI|8:00 PM|United Center|Chicago|IL
0022600048|2026-11-20|NOP|OKC|8:00 PM|Paycom Center|Oklahoma City|OK
0022600049|2026-11-20|PHX|UTA|9:30 PM|Delta Center|Salt Lake City|UT
0022600050|2026-11-20|HOU|DEN|10:00 PM|Ball Arena|Denver|CO
0022600051|2026-11-20|SAC|LAL|10:00 PM|Crypto.com Arena|Los Angeles|CA
"""

SLUG = {
    "ATL": "hawks", "BOS": "celtics", "BKN": "nets", "CHA": "hornets", "CHI": "bulls",
    "CLE": "cavaliers", "DAL": "mavericks", "DEN": "nuggets", "DET": "pistons",
    "GSW": "warriors", "HOU": "rockets", "IND": "pacers", "LAC": "clippers",
    "LAL": "lakers", "MEM": "grizzlies", "MIA": "heat", "MIL": "bucks",
    "MIN": "timberwolves", "NOP": "pelicans", "NYK": "knicks", "OKC": "thunder",
    "ORL": "magic", "PHI": "sixers", "PHX": "suns", "POR": "blazers", "SAC": "kings",
    "SAS": "spurs", "TOR": "raptors", "UTA": "jazz", "WAS": "wizards",
}


def _slate():
    out = []
    for line in _S.strip().splitlines():
        gid, date, away, home, tm, arena, city, st = line.split("|")
        out.append({
            "game_id": gid, "date": date, "away": away, "home": home,
            "matchup": f"{away} @ {home}", "time_et": tm,
            "arena": arena, "city": city, "state": st,
            "lat": None, "lon": None,
            "source_url": f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}",
            "src": "schedule",
        })
    return out


SLATE = _slate()

# Arena table, published with the arena/city/state read from the official schedule.
# Coordinates are deliberately absent - see BLOCKED["arena_coords"].
ARENAS = sorted({(g["arena"], g["city"], g["state"]) for g in SLATE})

# --------------------------------------------------------------------------- results
# game_id, date, away, home, away_pts, home_pts, periods, away_q, home_q
# The five 11/14 rows are verbatim from the 2026-11-15 snapshot (provenance unchanged:
# quarter scores were read from the official LINESCORES table for 0022600231 only).
# The nine 11/15 rows mirror the committed feed data/raw/refresh_2026-11-15/
# results_2026-11-15.json (official gamebook PDFs, verified by the v4 settlement).
# The eight 11/16 rows were transcribed this session from the official gamebook PDFs
# (see data/raw/results/results_2026-11-16.json for the full provenance).
_R = """
0022600231|2026-11-14|DEN|NOP|116|108|4|29,27,30,30|23,28,31,26
0022600232|2026-11-14|DAL|CLE|117|127|4||
0022600233|2026-11-14|DET|MIA|117|137|4||
0022600234|2026-11-14|BKN|MEM|110|129|4||
0022600235|2026-11-14|CHI|MIN|117|106|4||
0022600236|2026-11-15|IND|PHI|124|131|4|35,22,30,37|29,29,39,34
0022600237|2026-11-15|LAL|PHX|131|123|4|33,31,40,27|24,30,26,43
0022600238|2026-11-15|CHA|LAC|105|113|4|21,31,31,22|22,29,33,29
0022600239|2026-11-15|SAS|UTA|110|102|4|31,27,23,29|33,22,26,21
0022600240|2026-11-15|DAL|BOS|94|131|4||42,25,37,27
0022600241|2026-11-15|NYK|TOR|112|108|5|23,24,20,28,17|17,26,31,21,13
0022600242|2026-11-15|HOU|WAS|147|119|4|36,37,46,28|31,23,34,31
0022600243|2026-11-15|ATL|MIL|113|106|4|18,37,32,26|37,16,27,26
0022600244|2026-11-15|OKC|SAC|125|103|4|32,30,32,31|24,26,30,23
0022600245|2026-11-16|ORL|BOS|115|105|4|20,30,25,40|17,24,36,28
0022600246|2026-11-16|CHI|CLE|115|126|4|31,17,31,36|25,32,31,38
0022600247|2026-11-16|MEM|WAS|136|120|4|33,26,42,35|35,34,18,33
0022600248|2026-11-16|PHI|BKN|135|123|4|33,45,27,30|26,33,36,28
0022600249|2026-11-16|HOU|MIA|110|128|4|15,31,35,29|29,33,39,27
0022600250|2026-11-16|POR|MIN|98|106|4|26,25,22,25|26,33,28,19
0022600251|2026-11-16|GSW|NOP|94|115|4|11,25,29,29|35,26,32,22
0022600252|2026-11-16|PHX|DEN|117|105|4|20,36,34,27|24,29,29,23
"""

# src key per results row group: which SOURCES entry carries its provenance
RESULTS_SRC = {
    "2026-11-14": "schedule",
    "2026-11-15": "results_1115",
    "2026-11-16": "gamebooks",
}


def _results():
    out = []
    for line in _R.strip().splitlines():
        f = line.split("|")
        aq = [int(x) for x in f[7].split(",")] if f[7] else None
        hq = [int(x) for x in f[8].split(",")] if f[8] else None
        out.append({
            "game_id": f[0], "date": f[1], "away": f[2], "home": f[3],
            "away_pts": int(f[4]), "home_pts": int(f[5]), "periods": int(f[6]),
            "away_q": aq, "home_q": hq,
            "home_margin": int(f[5]) - int(f[4]),
            "total_pts": int(f[4]) + int(f[5]),
            "source_url": f"https://www.nba.com/game/{f[2].lower()}-vs-{f[3].lower()}-{f[0]}",
            "src": RESULTS_SRC[f[1]], "src_q": "linescore" if f[1] == "2026-11-14" else "gamebook",
        })
    return out


RESULTS = _results()

# --------------------------------------------------------------------------- injuries
INJURY_META = {
    "release": "11/17/26 11:00 AM ET",
    "revision_time_et": "2026-11-17 11:00 ET",
    "retrieved_at_utc": "2026-11-17T16:41:00Z",
    "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_11_00AM.pdf",
    "index_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "newest_indexed_release_at_retrieval": "11/17/26 11:00 AM ET",
    "previous_release_used_for_diff": (
        "11/16/26 01:00 PM ET",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf",
        "data/raw/refresh_2026-11-16/injury_transcript_20261116_0100PM.json",
    ),
    "filing_policy": (
        "By 5 p.m. local the day before a game (1 p.m. local for the second night of a "
        "back-to-back); a game-day report follows between 11 a.m. and 1 p.m. local "
        "(8-10 a.m. for tip-offs at or before 5 p.m.)."
    ),
}

# date, time_et, matchup, team, player, status, reason   (player "" => NOT YET SUBMITTED)
_I = """
11/17/2026|07:30|NYK@TOR|Toronto Raptors|Bittle, Nate|Out|Injury/Illness - Right Foot Avulsion Fracture
11/17/2026|07:30|NYK@TOR|Toronto Raptors|Leonard, Kawhi|Out|Injury/Illness - Left Knee Injury Management
11/17/2026|07:30|NYK@TOR|Toronto Raptors|McCullar Jr., Kevin|Out|G League - Two-Way
11/17/2026|07:30|NYK@TOR|Toronto Raptors|Smith, Malachi|Out|G League - Two-Way
11/17/2026|08:00|DET@SAS|Detroit Pistons|Duren, Jalen|Out|Injury/Illness - Right Hamstring Strain
11/17/2026|08:00|DET@SAS|Detroit Pistons|Holland II, Ronald|Out|Injury/Illness - Left Knee Contusion / Bone Bruise
11/17/2026|08:00|DET@SAS|Detroit Pistons|Joe, Isaiah|Doubtful|Injury/Illness - Right Hip Contusion
11/17/2026|08:00|DET@SAS|Detroit Pistons|Okorie, Ebuka|Out|G League - On Assignment
11/17/2026|08:00|DET@SAS|Detroit Pistons|Onyenso, Ugonna|Out|G League - Two-Way
11/17/2026|08:00|DET@SAS|Detroit Pistons|Prince, Taurean|Out|Injury/Illness - Right Knee Soreness
11/17/2026|08:00|DET@SAS|Detroit Pistons|Robinson, Duncan|Out|Injury/Illness - Left Quadriceps Strain
11/17/2026|08:00|DET@SAS|San Antonio Spurs|Brown, Maliq|Out|G League - Two-Way
11/17/2026|08:00|DET@SAS|San Antonio Spurs|Gillespie, Ja'Kobi|Out|G League - Two-Way
11/17/2026|08:00|DET@SAS|San Antonio Spurs|Harris, Tobias|Out|Injury/Illness - Left Calf Strain
11/17/2026|08:00|DET@SAS|San Antonio Spurs|Quaintance, Jayden|Out|Injury/Illness - Right Knee Surgery
11/17/2026|08:00|POR@MIN|Portland Trail Blazers|||NOT YET SUBMITTED
11/17/2026|08:00|POR@MIN|Minnesota Timberwolves|||NOT YET SUBMITTED
11/17/2026|10:30|UTA@LAC|Utah Jazz|Bufkin, Kobe|Out|G League - Two-Way
11/17/2026|10:30|UTA@LAC|Utah Jazz|Hayes, Jaxson|Out|Injury/Illness - Left Knee Strain
11/17/2026|10:30|UTA@LAC|Utah Jazz|Ingram, Harrison|Out|G League - Two-Way
11/17/2026|10:30|UTA@LAC|Utah Jazz|Jackson Jr., Jaren|Out|Injury/Illness - Right MCL Tear
11/17/2026|10:30|UTA@LAC|Utah Jazz|Markkanen, Lauri|Out|Injury/Illness - Right Hand Fracture
11/17/2026|10:30|UTA@LAC|Utah Jazz|Nurkic, Jusuf|Out|Injury/Illness - Right Right Foot; 2nd Plantar Plate Tear
11/17/2026|10:30|UTA@LAC|LA Clippers|Beal, Bradley|Out|Injury/Illness - Right Knee Injury Management
11/17/2026|10:30|UTA@LAC|LA Clippers|Ingram, Brandon|Out|Injury/Illness - Right Heel Surgery
11/17/2026|10:30|UTA@LAC|LA Clippers|Miller, Jordan|Out|Injury/Illness - Left Rotator Cuff Surgery
11/17/2026|10:30|UTA@LAC|LA Clippers|Niederhauser, Yanic Konan|Out|Injury/Illness - Right Lisfranc Surgery
11/17/2026|11:00|CHA@LAL|Charlotte Hornets|Ajayi, Michael|Out|G League - Two-Way
11/17/2026|11:00|CHA@LAL|Charlotte Hornets|Boswell, Kylan|Out|G League - Two-Way
11/17/2026|11:00|CHA@LAL|Charlotte Hornets|Knueppel, Kon|Out|Injury/Illness - Left Hamstring Strain
11/17/2026|11:00|CHA@LAL|Charlotte Hornets|Schroder, Dennis|Out|Injury/Illness - Left Hamstring Strain
11/17/2026|11:00|CHA@LAL|Charlotte Hornets|Steinbach, Hannes|Out|G League - On Assignment
11/17/2026|11:00|CHA@LAL|Los Angeles Lakers|Grimes, Quentin|Available|Injury/Illness - Right Finger Splint
11/17/2026|11:00|CHA@LAL|Los Angeles Lakers|Kessler, Walker|Out|Injury/Illness - Right Lower Leg
11/17/2026|11:00|CHA@LAL|Los Angeles Lakers|Reaves, Austin|Out|Injury/Illness - Left Heel Contusion / Bone Bruise
11/18/2026|07:00|HOU@IND|Houston Rockets|||NOT YET SUBMITTED
11/18/2026|07:00|HOU@IND|Indiana Pacers|||NOT YET SUBMITTED
11/18/2026|07:00|MEM@CLE|Memphis Grizzlies|||NOT YET SUBMITTED
11/18/2026|07:00|MEM@CLE|Cleveland Cavaliers|||NOT YET SUBMITTED
11/18/2026|07:00|MIL@MIA|Milwaukee Bucks|||NOT YET SUBMITTED
11/18/2026|07:00|MIL@MIA|Miami Heat|||NOT YET SUBMITTED
11/18/2026|07:00|PHI@ORL|Philadelphia 76ers|||NOT YET SUBMITTED
11/18/2026|07:00|PHI@ORL|Orlando Magic|||NOT YET SUBMITTED
11/18/2026|07:30|CHI@BKN|Chicago Bulls|||NOT YET SUBMITTED
11/18/2026|07:30|CHI@BKN|Brooklyn Nets|||NOT YET SUBMITTED
11/18/2026|07:30|WAS@TOR|Washington Wizards|||NOT YET SUBMITTED
11/18/2026|07:30|WAS@TOR|Toronto Raptors|||NOT YET SUBMITTED
11/18/2026|08:00|ATL@OKC|Atlanta Hawks|||NOT YET SUBMITTED
11/18/2026|08:00|ATL@OKC|Oklahoma City Thunder|||NOT YET SUBMITTED
11/18/2026|08:00|DET@NOP|Detroit Pistons|||NOT YET SUBMITTED
11/18/2026|08:00|DET@NOP|New Orleans Pelicans|||NOT YET SUBMITTED
11/18/2026|08:00|GSW@DAL|Golden State Warriors|||NOT YET SUBMITTED
11/18/2026|08:00|GSW@DAL|Dallas Mavericks|||NOT YET SUBMITTED
11/18/2026|09:30|BOS@DEN|Boston Celtics|||NOT YET SUBMITTED
11/18/2026|09:30|BOS@DEN|Denver Nuggets|||NOT YET SUBMITTED
11/18/2026|10:00|PHX@SAC|Phoenix Suns|||NOT YET SUBMITTED
11/18/2026|10:00|PHX@SAC|Sacramento Kings|||NOT YET SUBMITTED
11/18/2026|10:00|UTA@LAL|Utah Jazz|||NOT YET SUBMITTED
11/18/2026|10:00|UTA@LAL|Los Angeles Lakers|||NOT YET SUBMITTED
"""

TEAM_OF = {
    "Indiana Pacers": "IND", "Philadelphia 76ers": "PHI", "Los Angeles Lakers": "LAL",
    "Phoenix Suns": "PHX", "Charlotte Hornets": "CHA", "LA Clippers": "LAC",
    "San Antonio Spurs": "SAS", "Utah Jazz": "UTA", "Dallas Mavericks": "DAL",
    "Boston Celtics": "BOS", "New York Knicks": "NYK", "Toronto Raptors": "TOR",
    "Houston Rockets": "HOU", "Washington Wizards": "WAS", "Atlanta Hawks": "ATL",
    "Milwaukee Bucks": "MIL", "Oklahoma City Thunder": "OKC", "Sacramento Kings": "SAC",
    "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE", "Memphis Grizzlies": "MEM",
    "Orlando Magic": "ORL", "Miami Heat": "MIA", "Brooklyn Nets": "BKN",
    "Golden State Warriors": "GSW", "New Orleans Pelicans": "NOP",
    "Portland Trail Blazers": "POR", "Minnesota Timberwolves": "MIN",
    "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
}


def _injuries():
    out = []
    for line in _I.strip().splitlines():
        # columns: game date, tip time, matchup, team, player, status, reason
        # an unfiled team prints an empty player/status and "NOT YET SUBMITTED" in reason
        d, tm, mu, team, player, status, reason = line.split("|")
        mm, dd, yy = d.split("/")
        notsub = reason.strip() == "NOT YET SUBMITTED"
        out.append({
            "game_date": f"{yy}-{mm.zfill(2)}-{dd.zfill(2)}",
            "game_time_et": tm, "matchup": mu, "team": team,
            "team_abbr": TEAM_OF.get(team),
            "player": None if notsub else player,
            "status": None if notsub else status,
            "reason": None if notsub else reason,
            "not_submitted": notsub,
            "src": "injury_pdf",
        })
    return out


INJURIES = _injuries()

# --------------------------------------------------------------------------- flags
FLAGS = [
    ("F-301", "window", "The repeat matchups the previous snapshot flagged as a possible "
     "page artifact are CONFIRMED genuine on the official schedule rendered this session: "
     "POR @ MIN plays on both 2026-11-16 (0022600250, final 98-106) and 2026-11-17 "
     "(0022600254), and NYK @ TOR on both 2026-11-15 (0022600241, 112-108 OT) and "
     "2026-11-17 (0022600253), each pair in the same arena. The 2026-11-13 "
     "slate_context anomaly note is thereby resolved.",
     "https://www.nba.com/schedule", "resolved"),
    ("F-302", "slate", "Official game IDs are not monotonic in tip order inside 2026-11-18: "
     "BOS@DEN is 0022600266 but tips at 9:30 PM ET, after GSW@DAL which is 0022600267 and "
     "tips at 8:00 PM ET. Do not use game ID as a date proxy.",
     "https://www.nba.com/schedule", "review"),
    ("F-303", "injury", "The 11/17 11:00 AM ET release prints an explicit NOT YET SUBMITTED "
     "row for both POR@MIN clubs while the day-before deadline for the 11/18 games had not "
     "yet passed, so those 16 club rows are absent-by-rule rather than late. Also in this "
     "release: Walker Kessler's reason ends at 'Right Lower Leg' where the page-continuation "
     "renders a stray 'Soreness' cell; the join basis is recorded in the committed "
     "transcript rather than merged silently, and the later 11:15+ releases supersede it.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_11_00AM.pdf", "review"),
    ("F-304", "results", "Quarter scores are captured for 8 of 9 finals on 11/15 (the DAL "
     "away row is blank in the committed feed) and all 8 finals on 11/16 (official gamebook "
     "PDFs). Four of the five 11/14 finals still carry blank quarter columns with their "
     "game URL; nothing was estimated.",
     "https://www.nba.com/games?date=2026-11-14", "open"),
    ("F-305", "data", "RESOLVED this session: the previous snapshot had only 16 of 30 PTS "
     "rows inside its fetched chunks and derived the rest. The traditional page was re-read "
     "in five chunks and PTS was read for all 30 clubs; pts_for stays derived from "
     "OffRtg x POSS for internal consistency and the official read is published beside it "
     "in the cross-checks.",
     "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame", "resolved"),
    ("F-306", "travel", "No arena coordinates: NBA.com publishes arena, city and state but no "
     "lat/lon, and no official geocoder is reachable. Travel distance is blank for every "
     "game; rest, back-to-back and 3-in-4 are computed from the official schedule dates.",
     "https://www.nba.com/schedule", "open"),
    ("F-307", "rotation", "nba.com/stats/players/traditional is reachable this session (469 "
     "rows with a MIN column), which contradicts the standing 'player_box' blocked entry on "
     "the v2 site. The per-game book for 11/14-11/16 now lives on the v5 surface "
     "(data/v5/gamebooks_*.json); the v3 rotation model stays wired but empty pending its "
     "own season-aggregate capture.",
     "https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame", "open"),
    ("F-308", "market", "No market price feed, so nothing on the bet surface is a bettable "
     "edge and every stake is 0.00. The bet surface is emitted only when the projection "
     "surface is complete and the owner has accepted the trigger policy.",
     "https://www.nba.com/games", "blocking"),
]


def selftest() -> list[str]:
    """Mechanical checks on the transcription itself. Empty list == clean."""
    p: list[str] = []
    if len(TEAMS) != 30:
        p.append(f"TEAMS has {len(TEAMS)} clubs")
    if sum(t["w"] for t in TEAMS.values()) != 205:
        p.append(f"wins sum to {sum(t['w'] for t in TEAMS.values())}, expected 205")
    if sum(t["l"] for t in TEAMS.values()) != 205:
        p.append(f"losses sum to {sum(t['l'] for t in TEAMS.values())}, expected 205")
    for a, t in TEAMS.items():
        if t["w"] + t["l"] != t["gp"]:
            p.append(f"{a}: standings {t['w']}-{t['l']} != advanced GP {t['gp']}")
        if t["home_w"] + t["road_w"] > t["w"]:
            p.append(f"{a}: home+road wins exceed total wins")
        if t["home_w"] + t["home_l"] + t["road_w"] + t["road_l"] != t["gp"]:
            p.append(f"{a}: home+road games != GP")
        # The official NetRtg column is rounded independently of OffRtg and DefRtg, so it
        # can sit 0.1 away from their difference. Tolerated, disclosed, never "fixed".
        if abs((t["off_rtg"] - t["def_rtg"]) - t["net_rtg"]) > 0.15:
            p.append(f"{a}: NetRtg {t['net_rtg']} != OffRtg-DefRtg {t['off_rtg'] - t['def_rtg']:.1f}")
        # margin must equal NetRtg scaled by this club's own possessions per game
        want = t["net_rtg"] * t["poss"] / (100.0 * t["gp"])
        got = t["pts_for"] - t["pts_against"]
        if abs(want - got) > 0.20:
            p.append(f"{a}: derived margin {got:.2f} != NetRtg x POSS/(100xGP) {want:.3f}")
        # the traditional-page read must agree with the derived figure (the two pages
        # estimate possessions differently; 2.5 ppg is the observed worst-case band)
        if t["pts_read"] is not None and abs(t["pts_read"] - t["pts_for"]) > 2.5:
            p.append(f"{a}: traditional PTS {t['pts_read']} vs derived {t['pts_for']} differs "
                     "by more than the 2.5 ppg band")
    if len(SLATE) != 30:
        p.append(f"SLATE has {len(SLATE)} games, expected 30")
    ids = [g["game_id"] for g in SLATE]
    if len(set(ids)) != len(ids):
        p.append("duplicate game id in SLATE")
    for g in SLATE:
        if g["away"] not in TEAMS or g["home"] not in TEAMS:
            p.append(f"{g['game_id']}: unknown team")
    if len(RESULTS) != 22:
        p.append(f"RESULTS has {len(RESULTS)} rows, expected 22")
    for r in RESULTS:
        if r["away_q"] and sum(r["away_q"]) != r["away_pts"]:
            p.append(f"{r['game_id']}: away quarters do not sum to the final")
        if r["home_q"] and sum(r["home_q"]) != r["home_pts"]:
            p.append(f"{r['game_id']}: home quarters do not sum to the final")
    if len(INJURIES) != 59:
        p.append(f"INJURIES has {len(INJURIES)} rows, expected 59 (33 player + 26 not-submitted)")
    if sum(1 for r in INJURIES if r["not_submitted"]) != 26:
        p.append("not-submitted row count is not 26")
    return p


def crosschecks() -> dict:
    """Official-vs-derived disagreements, published rather than reconciled away."""
    d_opp, d_pts = [], []
    for a, t in TEAMS.items():
        d_opp.append((abs(t["pts_against"] - t["opp_pts"]), a,
                      t["pts_against"], t["opp_pts"]))
        if t["pts_read"] is not None:
            d_pts.append((abs(t["pts_read"] - t["pts_for"]), a,
                          t["pts_for"], t["pts_read"]))
    d_opp.sort(reverse=True)
    d_pts.sort(reverse=True)
    return {
        "note": (
            "Both columns are official. The advanced page implies a points-allowed figure "
            "from DefRtg x POSS; the opponent page prints Opp PTS directly. They disagree "
            "by up to the amount shown because the two pages estimate team possessions "
            "differently (offensive and defensive possession counts are not identical). "
            "Nothing is averaged: the model uses the advanced-page pair for internal "
            "consistency and prints the opponent-page figure beside it."
        ),
        "pts_against_vs_opponent_page": {
            "n": len(d_opp),
            "max_abs_diff": round(d_opp[0][0], 2),
            "worst": [{"team": a, "derived": d, "official": o} for _, a, d, o in d_opp[:5]],
            "mean_abs_diff": round(sum(x[0] for x in d_opp) / len(d_opp), 3),
        },
        "pts_for_vs_traditional_page": {
            "n": len(d_pts),
            "max_abs_diff": round(d_pts[0][0], 2),
            "worst": [{"team": a, "derived": d, "official": o} for _, a, d, o in d_pts[:5]],
            "mean_abs_diff": round(sum(x[0] for x in d_pts) / len(d_pts), 3),
        },
    }


if __name__ == "__main__":
    problems = selftest()
    for x in problems:
        print("PROBLEM:", x)
    print(f"snapshot {AS_OF_UTC}: {len(TEAMS)} clubs, {len(SLATE)} games, "
          f"{len(RESULTS)} finals, {len(INJURIES)} injury rows, {len(ARENAS)} arenas")
    raise SystemExit(1 if problems else 0)
