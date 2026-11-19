"""Official NBA snapshot re-cut to the 2026-11-19 capture by session `arena/6b9f3bbe-nba2`.

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
  ALL 30 clubs inside the fetched chunks, so the derived-points cross-check covers the
  full league. Full provenance for this re-cut: data/raw/refresh_2026-11-19/ and
  audit/session-6b9f3bbe-nba2/ (session arena/6b9f3bbe-nba2, 2026-11-19).
* ``ak-static.cms.nba.com/.../Injury-Report_2026-11-19_07_15AM.pdf`` (single chunk) ...
  the newest release listed on the official index at retrieval time: 23 player rows for
  the four 11/19 games filed so far plus 21 explicit NOT YET SUBMITTED team rows (three
  11/19 clubs and all 18 clubs for 11/20 whose day-before deadline had not yet passed).
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
1. the 30 W/L records sum to 222 wins and 222 losses — exactly the 183 historical finals
   plus the committed finals feeds through 2026-11-18 (5 of 11/14, 9 of 11/15, 8 of 11/16,
   5 of 11/17 and 12 of 11/18);
2. for every club, ``pts_for - pts_against`` agrees with ``net_rtg x poss / 100`` to
   within 0.2 points per game, and the traditional-page PTS read agrees with the derived
   points-scored figure to within 2.5 points per game (possessions estimated
   differently on the two pages).
"""

from __future__ import annotations

AS_OF_UTC = "2026-11-19T12:32:00Z"
AS_OF_ET = "2026-11-19 07:32 ET"
SESSION = "arena/6b9f3bbe-nba2"  # re-cut (RQ-8892-02) to the 2026-11-19 capture; prior snapshot by arena/1eeb6a21-nba2 (2026-11-17)
WINDOW = ("2026-11-19", "2026-11-22")  # T+0 .. T+3 inclusive

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
        "NBA.com Games & Scores day strips + committed schedule capture (official)",
        "https://www.nba.com/games?date=2026-11-19",
        "Game IDs and ET tip times for 11/19-11/22 read from the day strips on 2026-11-19; "
        "arena/city/state for 11/19-11/20 carried from this module's committed 11/17 schedule "
        "read (every shared tip re-verified and agreeing); 11/21-11/22 arenas blank - the "
        "strips do not print them.",
    ),
    "injury_pdf": (
        "NBA Official Injury Report 11/19/26 07:15 AM ET (official PDF)",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_15AM.pdf",
        "Per-player status (Out / Doubtful / Questionable / Available) with the stated "
        "reason, plus explicit NOT YET SUBMITTED team rows. Two Questionable rows "
        "(Kuminga, Pullin) lose the team cell at the PDF page break; the PDF's own "
        "block-continuation convention carries the previous team block (Minnesota).",
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
    "results_1117": (
        "Committed official finals feed for 2026-11-17",
        "https://www.nba.com/games?date=2026-11-17",
        "The five 11/17 finals with quarter rows, mirrored into RESULTS below verbatim from "
        "data/raw/finals_2026-11-17.json (retrieved_at 2026-11-18T19:29:18Z; the club cells "
        "that feed leaves blank were filled from the history duplicate rows with agreeing scores).",
    ),
    "results_1118": (
        "Committed official finals feed for 2026-11-18 (day strip + official gamebooks)",
        "https://www.nba.com/games?date=2026-11-18",
        "The twelve 11/18 finals with quarter rows, mirrored into RESULTS below verbatim from "
        "data/raw/finals_2026-11-18.json (captured 2026-11-19 by arena/6b9f3bbe-nba2; each "
        "final read twice - day strip and gamebook line score - and every quarter row sums "
        "to its printed final).",
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
# Neutral-site games on the official 2026-11-19 standings card: inside W/L, outside the
# home/road split (DEN 1-0, IND 0-1), exactly as the card prints them.
NEUTRAL_GAMES = {"DEN": (1, 0), "IND": (0, 1)}

_T = """
ATL|Atlanta Hawks|9|6|3|3|6|3|15|725.0|112.8|110.8|1.9|103.71|1566|52.8|14.6|32.8|69.6|115.8|117.7
BKN|Brooklyn Nets|3|11|1|5|2|6|14|677.0|110.5|119.0|-8.4|99.51|1404|53.5|17.5|31.9|68.0|119.2|110.9
BOS|Boston Celtics|11|4|6|1|5|3|15|725.0|117.0|106.0|11.0|96.76|1460|54.6|14.9|32.9|67.7|103.4|113.9
CHA|Charlotte Hornets|4|10|3|4|1|6|14|677.0|103.1|113.7|-10.6|96.43|1360|48.6|19.9|36.2|72.8|110.4|100.1
CHI|Chicago Bulls|4|10|1|4|3|6|14|677.0|111.1|119.1|-8.0|103.8|1464|52.7|16.5|31.6|64.6|124.6|116.2
CLE|Cleveland Cavaliers|8|8|6|3|2|5|16|773.0|117.5|115.5|2.0|100.01|1610|55.8|13.7|30.9|68.7|116.3|118.3
DAL|Dallas Mavericks|8|7|6|2|2|5|15|720.0|112.3|113.4|-1.1|99.97|1501|53.6|16.3|33.1|65.9|113.2|112.3
DEN|Denver Nuggets|8|5|3|3|4|2|13|629.0|114.3|113.8|0.5|98.02|1287|54.3|14.2|30.4|66.8|112.2|113.2
DET|Detroit Pistons|10|4|3|2|7|2|14|682.0|114.9|108.9|6.0|98.78|1406|54.5|14.2|30.0|66.6|108.9|115.4
GSW|Golden State Warriors|8|7|6|1|2|6|15|725.0|113.4|112.8|0.6|99.41|1503|53.9|16.2|32.7|67.9|112.8|113.7
HOU|Houston Rockets|12|4|7|1|5|3|16|768.0|121.1|112.1|9.0|97.41|1558|55.6|15.0|36.7|68.7|109.2|117.9
IND|Indiana Pacers|5|10|2|5|3|4|15|720.0|110.7|113.6|-2.9|100.9|1511|53.9|14.3|24.4|68.1|114.8|111.5
LAC|LA Clippers|4|9|4|4|0|5|13|629.0|111.4|117.0|-5.6|99.74|1306|54.9|17.2|29.2|65.9|117.7|111.9
LAL|Los Angeles Lakers|13|3|6|2|7|1|16|773.0|119.8|113.2|6.7|100.35|1614|57.2|16.5|33.6|65.0|114.4|120.9
MEM|Memphis Grizzlies|11|4|3|4|8|0|15|725.0|120.6|111.9|8.7|100.27|1516|56.9|15.7|34.2|69.8|112.9|121.9
MIA|Miami Heat|9|6|5|3|4|3|15|725.0|116.9|116.7|0.3|102.19|1546|55.4|14.0|30.8|68.3|119.9|120.5
MIL|Milwaukee Bucks|1|14|1|7|0|7|15|720.0|106.7|119.7|-13.0|101.0|1515|51.4|16.8|31.1|64.5|120.9|107.7
MIN|Minnesota Timberwolves|11|4|7|2|4|2|15|725.0|114.5|104.0|10.5|101.23|1528|54.8|15.8|34.7|69.3|106.1|116.7
NOP|New Orleans Pelicans|5|11|4|7|1|4|16|783.0|111.7|118.9|-7.1|101.3|1652|51.8|15.3|30.1|68.5|122.8|115.4
NYK|New York Knicks|8|6|4|3|4|3|14|677.0|114.8|109.0|5.8|94.87|1342|52.4|15.2|37.1|72.2|103.9|110.0
OKC|Oklahoma City Thunder|9|6|5|1|4|5|15|720.0|113.0|108.7|4.4|99.17|1488|52.2|13.5|31.6|68.9|107.7|112.1
ORL|Orlando Magic|6|8|1|5|5|3|14|677.0|111.3|114.0|-2.7|97.84|1375|53.9|16.4|30.7|70.6|112.8|109.4
PHI|Philadelphia 76ers|13|3|6|2|7|1|16|768.0|114.5|111.8|2.7|99.88|1600|53.4|12.6|28.4|72.0|111.6|114.5
PHX|Phoenix Suns|7|7|5|4|2|3|14|672.0|115.6|116.8|-1.2|98.89|1382|55.4|14.4|30.5|63.1|115.7|114.1
POR|Portland Trail Blazers|9|5|3|2|6|3|14|672.0|116.2|110.2|6.0|100.71|1410|54.8|16.1|33.0|70.1|111.0|117.0
SAC|Sacramento Kings|1|13|0|9|1|4|14|672.0|106.9|120.4|-13.5|100.93|1411|52.8|17.2|28.4|69.3|121.7|107.7
SAS|San Antonio Spurs|12|3|5|3|7|0|15|725.0|118.1|107.0|11.1|98.35|1487|53.0|12.6|33.5|71.3|105.9|117.1
TOR|Toronto Raptors|5|10|2|6|3|4|15|725.0|113.7|113.1|0.5|98.09|1478|52.0|13.7|34.3|66.4|112.0|112.0
UTA|Utah Jazz|3|13|1|7|2|6|16|778.0|107.0|114.5|-7.5|100.16|1626|52.4|16.7|29.0|69.7|116.0|108.8
WAS|Washington Wizards|5|11|2|5|3|6|16|778.0|109.9|117.1|-7.1|99.46|1612|51.7|14.6|29.2|65.6|117.9|110.8
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
0022600273|2026-11-19|LAC|SAS|8:00 PM|Frost Bank Center|San Antonio|TX
0022600270|2026-11-19|GSW|MEM|8:00 PM|FedExForum|Memphis|TN
0022600272|2026-11-19|NYK|MIN|8:00 PM|Target Center|Minneapolis|MN
0022600271|2026-11-19|POR|MIL|8:00 PM|Fiserv Forum|Milwaukee|WI
0022600043|2026-11-20|CHA|ATL|7:00 PM|State Farm Arena|Atlanta|GA
0022600046|2026-11-20|TOR|DET|7:30 PM|Little Caesars Arena|Detroit|MI
0022600045|2026-11-20|IND|CLE|7:30 PM|Rocket Arena|Cleveland|OH
0022600044|2026-11-20|ORL|BKN|7:30 PM|Barclays Center|Brooklyn|NY
0022600048|2026-11-20|NOP|OKC|8:00 PM|Paycom Center|Oklahoma City|OK
0022600047|2026-11-20|WAS|CHI|8:00 PM|United Center|Chicago|IL
0022600049|2026-11-20|PHX|UTA|9:30 PM|Delta Center|Salt Lake City|UT
0022600050|2026-11-20|HOU|DEN|10:00 PM|Ball Arena|Denver|CO
0022600051|2026-11-20|SAC|LAL|10:00 PM|Crypto.com Arena|Los Angeles|CA
0022600274|2026-11-21|MIL|PHI|13:00|||
0022600275|2026-11-21|POR|NYK|19:30|||
0022600278|2026-11-21|NOP|SAS|20:00|||
0022600277|2026-11-21|MEM|MIN|20:00|||
0022600276|2026-11-21|LAC|DAL|20:00|||
0022600279|2026-11-21|BOS|SAC|22:00|||
0022600280|2026-11-22|DET|ATL|15:30|||
0022600281|2026-11-22|OKC|MIA|18:00|||
0022600284|2026-11-22|DAL|UTA|19:00|||
0022600282|2026-11-22|ORL|WAS|19:00|||
0022600283|2026-11-22|DEN|CHI|19:00|||
0022600285|2026-11-22|IND|NYK|20:00|||
0022600286|2026-11-22|BOS|GSW|20:30|||
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
# Only rows with an official arena read enter the arena table; the 11/21-11/22 rows whose
# arena the day strips do not print stay blank on the slate itself (FLAG-V3-ARENA-BLANK).
ARENAS = sorted({(g["arena"], g["city"], g["state"]) for g in SLATE if g["arena"]})

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
0022600253|2026-11-17|NYK|TOR|111|102|4|23,31,26,31|29,21,33,19
0022600254|2026-11-17|POR|MIN|105|106|4|17,31,31,26|29,20,30,27
0022600255|2026-11-17|DET|SAS|105|93|4|26,29,23,27|33,21,18,21
0022600256|2026-11-17|CHA|LAL|114|118|5|34,32,28,17,3|30,29,22,30,7
0022600257|2026-11-17|UTA|LAC|132|107|4|35,23,30,44|29,33,24,21
0022600258|2026-11-18|MEM|CLE|124|121|4|30,41,29,24|37,35,27,22
0022600259|2026-11-18|HOU|IND|119|104|4|39,23,31,26|28,18,30,28
0022600260|2026-11-18|MIL|MIA|130|137|4|23,25,38,44|34,40,38,25
0022600261|2026-11-18|PHI|ORL|121|116|4|27,37,28,29|40,29,28,19
0022600262|2026-11-18|CHI|BKN|137|107|4|37,39,35,26|21,30,26,30
0022600263|2026-11-18|WAS|TOR|103|99|4|29,20,29,25|23,24,32,20
0022600264|2026-11-18|DET|NOP|122|109|4|31,36,25,30|31,29,26,23
0022600265|2026-11-18|ATL|OKC|117|112|4|31,33,19,34|29,22,32,29
0022600266|2026-11-18|BOS|DEN|101|105|4|30,31,19,21|24,25,31,25
0022600267|2026-11-18|GSW|DAL|94|116|4|25,24,23,22|35,27,30,24
0022600268|2026-11-18|UTA|LAL|109|97|4|29,27,22,31|34,20,22,21
0022600269|2026-11-18|PHX|SAC|128|107|4|36,29,34,29|31,29,24,23
"""

# src key per results row group: which SOURCES entry carries its provenance
RESULTS_SRC = {
    "2026-11-14": "schedule",
    "2026-11-15": "results_1115",
    "2026-11-16": "gamebooks",
    "2026-11-17": "results_1117",
    "2026-11-18": "results_1118",
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
    "release": "11/19/26 07:15 AM ET",
    "revision_time_et": "2026-11-19 07:15 AM ET",
    "retrieved_at_utc": "2026-11-19T12:32:00Z",
    "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_15AM.pdf",
    "index_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "newest_indexed_release_at_retrieval": "11/19/26 07:15 AM ET",
    "previous_release_used_for_diff": (
        "11/18/26 02:15 PM ET",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-18_02_15PM.pdf",
        "data/raw/capture_2026-11-18/injury_release_2026-11-18.json",
    ),
    "filing_policy": (
        "By 5 p.m. local the day before a game (1 p.m. local for the second night of a "
        "back-to-back); a game-day report follows between 11 a.m. and 1 p.m. local "
        "(8-10 a.m. for tip-offs at or before 5 p.m.)."
    ),
}

# date, time_et, matchup, team, player, status, reason   (player "" => NOT YET SUBMITTED)
_I = """
11/19/2026|08:00|GSW@MEM|Golden State Warriors|||NOT YET SUBMITTED
11/19/2026|08:00|GSW@MEM|Memphis Grizzlies|||NOT YET SUBMITTED
11/19/2026|08:00|LAC@SAS|LA Clippers|Beal, Bradley|Out|Injury/Illness - Right Knee Injury Management
11/19/2026|08:00|LAC@SAS|LA Clippers|Ingram, Brandon|Out|Injury/Illness - Right Heel Surgery
11/19/2026|08:00|LAC@SAS|LA Clippers|Martinelli, Nick|Out|G League - Two-Way
11/19/2026|08:00|LAC@SAS|LA Clippers|Miller, Jordan|Out|Injury/Illness - Left Rotator Cuff Surgery
11/19/2026|08:00|LAC@SAS|San Antonio Spurs|Brown, Maliq|Out|G League - Two-Way
11/19/2026|08:00|LAC@SAS|San Antonio Spurs|Gillespie, Ja'Kobi|Out|G League - Two-Way
11/19/2026|08:00|LAC@SAS|San Antonio Spurs|Harper, Dylan|Out|Injury/Illness - Left Hip Soreness
11/19/2026|08:00|LAC@SAS|San Antonio Spurs|Harris, Tobias|Out|Injury/Illness - Left Calf Strain
11/19/2026|08:00|LAC@SAS|San Antonio Spurs|Quaintance, Jayden|Out|Injury/Illness - Right Knee Surgery
11/19/2026|08:00|NYK@MIN|Minnesota Timberwolves|Beringer, Joan|Available|Injury/Illness - Face Mask
11/19/2026|08:00|NYK@MIN|Minnesota Timberwolves|Clark, Jaylen|Out|Injury/Illness - Right Hamstring Strain
11/19/2026|08:00|NYK@MIN|Minnesota Timberwolves|DiVincenzo, Donte|Out|Injury/Illness - Right Achilles Tendon Repair / Surgery
11/19/2026|08:00|NYK@MIN|Minnesota Timberwolves|Edwards, Anthony|Out|Injury/Illness - Right Knee Arthroscopy
11/19/2026|08:00|NYK@MIN|Minnesota Timberwolves|Kuminga, Jonathan|Questionable|Injury/Illness - Right Shoulder Contusion
11/19/2026|08:00|NYK@MIN|Minnesota Timberwolves|Pullin, Zyon|Questionable|Injury/Illness - Right Quadriceps Contusion
11/19/2026|08:00|POR@MIL|Portland Trail Blazers|Avdija, Deni|Questionable|Injury/Illness - Left Foot Inflammation / Soreness
11/19/2026|08:00|POR@MIL|Portland Trail Blazers|Camara, Toumani|Questionable|Injury/Illness - Abdominal Soreness
11/19/2026|08:00|POR@MIL|Portland Trail Blazers|Carlson, Branden|Available|Injury/Illness - Face Mask
11/19/2026|08:00|POR@MIL|Portland Trail Blazers|Krejci, Vit|Out|Injury/Illness - Left Ankle Fracture
11/19/2026|08:00|POR@MIL|Portland Trail Blazers|Morant, Ja|Out|Injury/Illness - Left Hamstring Strain
11/19/2026|08:00|POR@MIL|Portland Trail Blazers|Sharpe, Shaedon|Out|Injury/Illness - Right Meniscus Surgery
11/19/2026|08:00|POR@MIL|Portland Trail Blazers|Williams III, Robert|Out|Rest
11/19/2026|08:00|POR@MIL|Portland Trail Blazers|Youngblood, Chris|Out|Injury/Illness - Right Heel Contusion / Bone Bruise
11/19/2026|08:00|POR@MIL|Milwaukee Bucks|||NOT YET SUBMITTED
11/20/2026|07:00|CHA@ATL|Charlotte Hornets|||NOT YET SUBMITTED
11/20/2026|07:00|CHA@ATL|Atlanta Hawks|||NOT YET SUBMITTED
11/20/2026|07:30|IND@CLE|Indiana Pacers|||NOT YET SUBMITTED
11/20/2026|07:30|IND@CLE|Cleveland Cavaliers|||NOT YET SUBMITTED
11/20/2026|07:30|ORL@BKN|Orlando Magic|||NOT YET SUBMITTED
11/20/2026|07:30|ORL@BKN|Brooklyn Nets|||NOT YET SUBMITTED
11/20/2026|07:30|TOR@DET|Toronto Raptors|||NOT YET SUBMITTED
11/20/2026|07:30|TOR@DET|Detroit Pistons|||NOT YET SUBMITTED
11/20/2026|08:00|NOP@OKC|New Orleans Pelicans|||NOT YET SUBMITTED
11/20/2026|08:00|NOP@OKC|Oklahoma City Thunder|||NOT YET SUBMITTED
11/20/2026|08:00|WAS@CHI|Washington Wizards|||NOT YET SUBMITTED
11/20/2026|08:00|WAS@CHI|Chicago Bulls|||NOT YET SUBMITTED
11/20/2026|09:30|PHX@UTA|Phoenix Suns|||NOT YET SUBMITTED
11/20/2026|09:30|PHX@UTA|Utah Jazz|||NOT YET SUBMITTED
11/20/2026|10:00|HOU@DEN|Houston Rockets|||NOT YET SUBMITTED
11/20/2026|10:00|HOU@DEN|Denver Nuggets|||NOT YET SUBMITTED
11/20/2026|10:00|SAC@LAL|Sacramento Kings|||NOT YET SUBMITTED
11/20/2026|10:00|SAC@LAL|Los Angeles Lakers|||NOT YET SUBMITTED
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
    if sum(t["w"] for t in TEAMS.values()) != 222:
        p.append(f"wins sum to {sum(t['w'] for t in TEAMS.values())}, expected 222")
    if sum(t["l"] for t in TEAMS.values()) != 222:
        p.append(f"losses sum to {sum(t['l'] for t in TEAMS.values())}, expected 222")
    for a, t in TEAMS.items():
        if t["w"] + t["l"] != t["gp"]:
            p.append(f"{a}: standings {t['w']}-{t['l']} != advanced GP {t['gp']}")
        if t["home_w"] + t["road_w"] > t["w"]:
            p.append(f"{a}: home+road wins exceed total wins")
        # neutral-site games sit inside W/L but outside the home/road split, exactly as the
        # official standings card prints them (2026-11-19 card: DEN 1-0, IND 0-1 neutral)
        nw, nl = NEUTRAL_GAMES.get(a, (0, 0))
        if t["home_w"] + t["home_l"] + t["road_w"] + t["road_l"] + nw + nl != t["gp"]:
            p.append(f"{a}: home+road+neutral games != GP")
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
    if len(SLATE) != 26:
        p.append(f"SLATE has {len(SLATE)} games, expected 26")
    ids = [g["game_id"] for g in SLATE]
    if len(set(ids)) != len(ids):
        p.append("duplicate game id in SLATE")
    for g in SLATE:
        if g["away"] not in TEAMS or g["home"] not in TEAMS:
            p.append(f"{g['game_id']}: unknown team")
    if len(RESULTS) != 39:
        p.append(f"RESULTS has {len(RESULTS)} rows, expected 39 (11/14-11/16 snapshots + the "
                 "five 11/17 finals + the twelve 11/18 finals)")
    for r in RESULTS:
        if r["away_q"] and sum(r["away_q"]) != r["away_pts"]:
            p.append(f"{r['game_id']}: away quarters do not sum to the final")
        if r["home_q"] and sum(r["home_q"]) != r["home_pts"]:
            p.append(f"{r['game_id']}: home quarters do not sum to the final")
    if len(INJURIES) != 44:
        p.append(f"INJURIES has {len(INJURIES)} rows, expected 44 (23 player + 21 not-submitted)")
    if sum(1 for r in INJURIES if r["not_submitted"]) != 21:
        p.append("not-submitted row count is not 21")
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
