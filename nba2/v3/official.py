"""Official NBA snapshot captured by session `arena/f7186ace-nba2` on 2026-11-16 UTC.

Every value below was read from the page named in ``SOURCES`` through the platform
page-fetch tool during this session (direct TLS egress to nba.com is blocked in this
sandbox; that limitation is recorded, not worked around). Nothing is inferred, nothing
is imputed, and no number is carried over from an earlier session's snapshot.

Retrieval record
----------------
Retrieved 2026-11-16, 02:20-02:45 UTC (2026-11-15 21:20-21:45 ET), which is *during*
the 11-15 evening slate. That timing is the whole point of this snapshot and it is
stated plainly because it shapes every number below:

* ``official.nba.com/nba-injury-report-2026-27-season/`` ..... the index rendered links
  through the **11/15 09:00 PM ET** release and no 11/16 release existed yet, so that is
  the newest release indexed at retrieval and the one transcribed here. It carries the
  **11/16 designations** (clubs file by 5 p.m. local the day before), which is why the
  window priced below starts on 11-16.
* ``Injury-Report_2026-11-15_09_00PM.pdf`` (chunks 0-2) ........ 160 rows: 98 for the
  nine 11/15 games and 62 for the eight 11/16 games.
* ``www.nba.com/games?date=2026-11-15`` (chunks 0-1) .......... nine games; six were
  marked **Final** at retrieval and three were still in progress. **Only the six Final
  rows enter the result feed**; the three live rows are committed under
  ``data/raw/capture_2026-11-16/results_2026-11-15.json`` for provenance and are used in
  no statistic anywhere in this repository.
* ``www.nba.com/standings`` (chunks 0-1) ..................... 30 clubs: W, L, WIN%, GB,
  conference record, home split, road split, neutral, OT, LAST10, streak.
* ``www.nba.com/stats/teams/advanced?...`` (chunks 0-1) ...... 30 rows: GP, W, L, MIN,
  OffRtg, DefRtg, NetRtg, PACE, POSS, eFG%, TS%, TOV%, OREB%, DREB%, AST%.
* ``www.nba.com/stats/teams/opponent?...`` (chunks 0-1) ...... 30 rows; Opp PTS (points
  allowed per game) and the opponent +/- column transcribed for all 30.
* ``www.nba.com/stats/teams/traditional?...`` (chunks 0-1) ... PTS per game read for the
  **11 highest-scoring clubs** (the table was fetched sorted by PTS descending and rows
  12-30 fell outside the chunks read). The other 19 are NOT guessed: ``pts_for`` is
  derived from OffRtg x POSS, and the 11 read rows are published as a cross-check.
* ``www.nba.com/games?date=2026-11-19`` (chunk 0) ............ the four 11/19 games with
  their official game IDs and ET tip times, completing the T+0..T+3 window.
* ``data/raw/capture_2026-11-15/slate_2026-11-15_to_11-18.json`` .... the 11-16/17/18
  game IDs, 24-hour ET tip times and arenas captured by session ``arena/f8f8f2b8-nba2``
  from ``www.nba.com/schedule``. Re-used rather than re-fetched; the source is committed.

Three mechanical cross-checks this snapshot passes (asserted in ``selftest``):
1. the 30 W/L records on the standings page agree **30/30** with the 30 W/L rows on the
   advanced page, read independently in the same session;
2. those records sum to 194 wins and 194 losses, which is exactly the 188 official finals
   committed under ``data/raw/history/`` (183 through 11/13 + the five 11/14 finals)
   plus the six 11/15 finals read from the games page this session;
3. for every club, ``pts_for - pts_against`` agrees with ``net_rtg x poss / (100 x gp)``.

A fourth cross-check is published, not reconciled: the points-allowed figure implied by
DefRtg x POSS and the Opp PTS figure printed on the opponent page disagree by at most
0.82 points (Orlando). Both are official; nothing is averaged away (see ``crosschecks``).
"""

from __future__ import annotations

AS_OF_UTC = "2026-11-16T02:45:00Z"
AS_OF_ET = "2026-11-15 21:45 ET"
SESSION = "arena/f7186ace-nba2"
WINDOW = ("2026-11-16", "2026-11-19")  # T+0 .. T+3 inclusive


SOURCES = {
    "standings": (
        "NBA.com Standings (official)",
        "https://www.nba.com/standings",
        "W, L, WIN%, GB, conference record, home/road/neutral splits, OT record, LAST10, "
        "streak. Read live 2026-11-16 02:38 UTC.",
    ),
    "team_adv": (
        "NBA.com Stats - Teams Advanced (official)",
        "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "GP, W, L, MIN, OffRtg, DefRtg, NetRtg, PACE, POSS, eFG%, TS%, TOV%, OREB%, DREB%, "
        "AST%. Read live 2026-11-16 02:25 UTC; all 30 rows.",
    ),
    "team_opp": (
        "NBA.com Stats - Teams Opponent (official)",
        "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "Opponent points per game (points allowed) and the opponent +/- column. Read live "
        "2026-11-16 02:28 UTC; all 30 rows.",
    ),
    "team_trad": (
        "NBA.com Stats - Teams Traditional (official)",
        "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame&dir=-1&sort=PTS",
        "PTS per game, read for 11 of 30 clubs (the 11 highest scorers - see PTS_READ). The "
        "remaining 19 rows fell outside the chunks fetched and are NOT guessed.",
    ),
    "schedule": (
        "NBA.com Schedule / Games (official)",
        "https://www.nba.com/games?date=2026-11-19",
        "The four 2026-11-19 games with official game IDs and ET tip times, read live "
        "2026-11-16 02:34 UTC. The 11-16/17/18 game IDs, tip times and arenas come from "
        "data/raw/capture_2026-11-15/slate_2026-11-15_to_11-18.json (session "
        "arena/f8f8f2b8-nba2, read from https://www.nba.com/schedule).",
    ),
    "results_1115": (
        "NBA.com Games - 2026-11-15 (official)",
        "https://www.nba.com/games?date=2026-11-15",
        "Final scores and game status for all nine 11/15 games, read live 2026-11-16 02:36 "
        "UTC. Six were Final; three were in progress and are excluded from every statistic.",
    ),
    "injury_pdf": (
        "NBA Official Injury Report 11/15/26 09:00 PM ET (official PDF)",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf",
        "Per-player status (Out / Doubtful / Questionable / Probable / Available) with the "
        "stated reason, plus explicit NOT YET SUBMITTED team rows. 160 rows; the 62 that "
        "carry an 11/16 game date are the ones this snapshot prices.",
    ),
    "injury_index": (
        "NBA Official - injury report policy and release archive (official)",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
        "Filing deadlines and the list of every published report for the season. At "
        "retrieval the index rendered links through 11/15 09:00 PM ET.",
    ),
    "injury_prior": (
        "NBA Official Injury Report 11/15/26 06:15 PM ET (official PDF)",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf",
        "The release immediately before the one transcribed here. Diffed mechanically "
        "(data/raw/capture_2026-11-16/injury_delta_0615PM_to_0900PM.json): 2 status "
        "changes, 7 rows added, 2 removed, 151 unchanged.",
    ),
    "arena_coords": (
        "Arena latitude / longitude (THIRD-PARTY - Wikipedia/Wikidata geocode)",
        "https://en.wikipedia.org/api/rest_v1/page/summary/State_Farm_Arena",
        "Arena name, city and state are official (nba.com schedule). The coordinates are "
        "NOT: NBA.com publishes none and no official geocoder is reachable, so they come "
        "from the Wikimedia REST summary endpoint captured by session "
        "arena/f8f8f2b8-nba2 in data/raw/capture_2026-11-15/arenas_2026-11-15.json. "
        "Every distance derived from them is flagged third-party.",
    ),
    "linescore": (
        "NBA.com game page - LINESCORES table (official)",
        "https://www.nba.com/game/den-vs-nop-0022600231",
        "Quarter-by-quarter scoring for one row of the result feed.",
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
    "quarters": (
        "Quarter scores for 10 of the 11 official finals in the result feed",
        "The official LINESCORES table was fetched for one game (0022600231). The other ten "
        "finals carry their game URL and a blank quarter column; nothing is estimated.",
        "https://www.nba.com/games?date=2026-11-15",
    ),
    "future_injuries": (
        "Injury rows for 11/17, 11/18 and 11/19",
        "A club files by 5 p.m. local the day before a game, so no report published at "
        "21:45 ET on 11/15 can contain 11/17, 11/18 or 11/19 rows. Blank by league rule.",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
    ),
    "in_progress": (
        "Finals for the three 11/15 games still in progress at retrieval",
        "HOU@WAS, ATL@MIL and OKC@SAC had not finished. Their partial scores are committed "
        "for provenance and enter no statistic; they will be captured by the next roll.",
        "https://www.nba.com/games?date=2026-11-15",
    ),
    "player_minutes": (
        "Per-player minutes and usage for the CURRENT window",
        "Measured minutes shares exist for the 11/13 window (see the Measured minutes page, "
        "built from the official gamebook PDFs of all nine 11/13 games). No gamebook for an "
        "11/16-11/19 game can exist yet, so this window's rotation column is a labelled "
        "mechanical rule over the last measured window, not a fresh measurement.",
        "https://statsdmz.nba.com/pdfs/",
    ),
    "arena_coords_official": (
        "Arena latitude / longitude from an OFFICIAL source",
        "NBA.com publishes the arena name, city and state but no coordinates, and no "
        "official geocoder is reachable. Coordinates are therefore taken from Wikipedia / "
        "Wikidata (third-party) and every distance derived from them is published with that "
        "flag rather than silently treated as official.",
        "https://www.nba.com/schedule",
    ),
}

# --------------------------------------------------------------------------- teams
# abbr, name, W, L, homeW, homeL, roadW, roadL, GP, MIN, OffRtg, DefRtg, NetRtg,
# PACE, POSS, eFG%, TOV%, OREB%, DREB%, OppPTS, PTS_read(or None)
_T = """
LAL|Los Angeles Lakers|12|2|5|1|7|1|14|672.0|122.1|114.0|8.0|100.64|1408|58.8|16.7|33.3|64.1|114.9|122.8
SAS|San Antonio Spurs|12|2|5|2|7|0|14|677.0|119.2|106.6|12.6|98.77|1395|53.5|12.3|33.3|71.8|105.9|118.8
BOS|Boston Celtics|11|2|6|0|5|2|13|629.0|118.9|105.1|13.9|96.53|1263|55.4|15.0|33.3|67.6|102.4|None
PHI|Philadelphia 76ers|11|3|6|2|5|1|14|672.0|112.3|110.3|2.0|100.21|1404|52.6|12.7|27.5|71.4|110.4|None
HOU|Houston Rockets|10|3|7|1|3|2|13|624.0|119.3|110.2|9.1|97.42|1266|55.1|14.8|35.2|67.8|107.4|116.2
MEM|Memphis Grizzlies|9|4|3|4|6|0|13|629.0|119.0|110.4|8.5|100.46|1318|55.8|15.6|34.2|70.6|111.7|120.6
MIN|Minnesota Timberwolves|9|4|5|2|4|2|13|629.0|116.0|104.5|11.5|101.27|1326|55.5|15.6|35.4|69.5|106.8|118.3
POR|Portland Trail Blazers|9|3|3|2|6|1|12|576.0|118.8|111.1|7.7|100.67|1208|56.3|16.2|33.3|70.2|111.8|119.6
DET|Detroit Pistons|8|4|3|2|5|2|12|586.0|114.1|109.2|4.9|99.48|1217|53.9|14.1|29.8|66.6|110.3|None
GSW|Golden State Warriors|8|5|6|1|2|4|13|629.0|116.1|112.0|4.1|99.66|1307|55.4|15.9|32.7|68.5|112.4|116.7
OKC|Oklahoma City Thunder|8|5|5|0|3|5|13|624.0|112.7|109.0|3.7|98.58|1282|51.4|13.5|31.9|68.5|107.4|None
ATL|Atlanta Hawks|7|6|3|3|4|3|13|629.0|113.3|111.9|1.4|103.55|1356|52.8|14.6|33.2|69.2|116.8|118.2
CLE|Cleveland Cavaliers|7|7|5|2|2|5|14|677.0|116.9|115.4|1.6|99.72|1407|55.8|13.4|29.1|68.1|115.9|117.5
DAL|Dallas Mavericks|7|7|5|2|2|5|14|672.0|111.8|114.5|-2.7|100.18|1404|53.2|16.0|32.9|66.0|114.6|None
DEN|Denver Nuggets|7|4|2|2|4|2|11|533.0|116.0|114.7|1.3|97.67|1087|55.0|13.5|30.2|67.7|112.8|None
MIA|Miami Heat|7|6|3|3|4|3|13|629.0|114.7|116.2|-1.5|102.49|1345|54.5|13.9|30.3|70.1|119.8|118.7
NYK|New York Knicks|7|6|4|3|3|3|13|629.0|113.7|108.2|5.5|95.66|1257|51.9|15.2|36.7|71.8|104.0|None
IND|Indiana Pacers|5|9|2|4|3|4|14|672.0|110.9|112.9|-2.0|101.25|1415|53.8|14.3|24.6|68.5|114.5|None
ORL|Orlando Magic|5|7|1|4|4|3|12|581.0|109.7|113.4|-3.7|98.23|1185|52.8|17.0|31.7|70.2|112.8|None
PHX|Phoenix Suns|5|7|5|4|0|3|12|576.0|114.3|118.5|-4.2|98.79|1183|54.3|14.4|30.0|61.6|117.3|None
TOR|Toronto Raptors|5|8|2|4|3|4|13|629.0|113.6|112.2|1.4|99.55|1302|51.7|14.4|35.8|67.2|112.8|None
CHA|Charlotte Hornets|4|9|3|4|1|5|13|624.0|102.5|113.6|-11.1|96.65|1256|48.0|20.0|36.5|74.2|109.8|None
LAC|LA Clippers|4|8|4|3|0|5|12|581.0|111.4|115.3|-3.9|100.05|1210|55.1|17.6|29.6|66.0|116.5|None
NOP|New Orleans Pelicans|4|10|3|6|1|4|14|687.0|111.3|120.0|-8.6|101.83|1457|51.9|15.4|29.7|68.0|124.9|115.9
WAS|Washington Wizards|4|9|2|3|2|6|13|634.0|108.7|114.3|-5.5|99.63|1315|51.5|15.0|29.0|66.2|115.8|None
BKN|Brooklyn Nets|3|9|1|3|2|6|12|581.0|109.8|116.0|-6.2|99.47|1204|52.9|17.6|32.1|69.9|116.4|None
CHI|Chicago Bulls|3|9|1|4|2|5|12|581.0|109.4|120.3|-10.9|103.81|1257|51.7|16.5|30.7|65.1|125.9|None
MIL|Milwaukee Bucks|1|12|1|6|0|6|13|624.0|105.7|120.0|-14.2|100.31|1305|51.1|16.6|30.5|64.3|120.2|None
SAC|Sacramento Kings|1|11|0|7|1|4|12|576.0|107.3|119.5|-12.2|101.00|1210|52.6|16.9|28.4|69.1|120.9|None
UTA|Utah Jazz|1|13|1|7|0|6|14|682.0|105.1|116.2|-11.1|100.22|1426|50.8|16.3|29.0|69.3|118.0|None
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
            "pts_read": read,                  # official: points scored per game (16 clubs)
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

# Arena coordinates. The arena NAME, CITY and STATE are official (nba.com schedule).
# The LAT/LON are NOT: NBA.com publishes no coordinates and no official geocoder is
# reachable, so they are read from Wikidata via the Wikimedia REST summary endpoint and
# committed in data/raw/capture_2026-11-15/arenas_2026-11-15.json (session
# arena/f8f8f2b8-nba2). Every quantity derived from them - travel distance above all -
# is published carrying that third-party flag, never as an official number.
ARENA_COORDS = {
    "ATL": (33.75722222, -84.39638889, "State Farm Arena", "Atlanta, GA"),
    "BKN": (40.68266111, -73.975225, "Barclays Center", "Brooklyn, NY"),
    "BOS": (42.36638889, -71.06222222, "TD Garden", "Boston, MA"),
    "CHA": (35.225, -80.83916667, "Spectrum Center", "Charlotte, NC"),
    "CHI": (41.88055556, -87.67416667, "United Center", "Chicago, IL"),
    "CLE": (41.49638889, -81.68805556, "Rocket Arena", "Cleveland, OH"),
    "DAL": (32.79055556, -96.81027778, "American Airlines Center", "Dallas, TX"),
    "DEN": (39.74861111, -105.0075, "Ball Arena", "Denver, CO"),
    "DET": (42.34111111, -83.055, "Little Caesars Arena", "Detroit, MI"),
    "GSW": (37.76805556, -122.3875, "Chase Center", "San Francisco, CA"),
    "HOU": (29.75083333, -95.36222222, "Toyota Center", "Houston, TX"),
    "IND": (39.76388889, -86.15555556, "Gainbridge Fieldhouse", "Indianapolis, IN"),
    "LAC": (33.9451, -118.3431, "Intuit Dome", "Inglewood, CA"),
    "LAL": (34.04305556, -118.26722222, "Crypto.com Arena", "Los Angeles, CA"),
    "MEM": (35.13833333, -90.05055556, "FedExForum", "Memphis, TN"),
    "MIA": (25.78138889, -80.18805556, "Kaseya Center", "Miami, FL"),
    "MIL": (43.04502778, -87.91816667, "Fiserv Forum", "Milwaukee, WI"),
    "MIN": (44.97944444, -93.27611111, "Target Center", "Minneapolis, MN"),
    "NOP": (29.94888889, -90.08194444, "Smoothie King Center", "New Orleans, LA"),
    "NYK": (40.75055556, -73.99361111, "Madison Square Garden", "New York, NY"),
    "OKC": (35.46333333, -97.515, "Paycom Center", "Oklahoma City, OK"),
    "ORL": (28.53916667, -81.38361111, "Kia Center", "Orlando, FL"),
    "PHI": (39.90111111, -75.17194444, "Xfinity Mobile Arena", "Philadelphia, PA"),
    "PHX": (33.44583333, -112.07138889, "Mortgage Matchup Center", "Phoenix, AZ"),
    "POR": (45.53166667, -122.66666667, "Moda Center", "Portland, OR"),
    "SAC": (38.58036111, -121.49961111, "Golden 1 Center", "Sacramento, CA"),
    "SAS": (29.42694444, -98.4375, "Frost Bank Center", "San Antonio, TX"),
    "TOR": (43.64333333, -79.37916667, "Scotiabank Arena", "Toronto, ON"),
    "UTA": (40.76833333, -111.90111111, "Delta Center", "Salt Lake City, UT"),
    "WAS": (38.89805556, -77.02083333, "Capital One Arena", "Washington, DC"),
}
ARENA_COORDS_SOURCE = (
    "https://en.wikipedia.org/api/rest_v1/page/summary/<Arena>",
    "THIRD-PARTY - Wikipedia / Wikidata geocode read through the Wikimedia REST summary "
    "endpoint on 2026-11-15 by session arena/f8f8f2b8-nba2.",
    "data/raw/capture_2026-11-15/arenas_2026-11-15.json",
)

# game_id, date, away, home, time_et, arena, city, state
_S = """
0022600245|2026-11-16|ORL|BOS|7:00 PM|TD Garden|Boston|MA
0022600246|2026-11-16|CHI|CLE|7:00 PM|Rocket Arena|Cleveland|OH
0022600247|2026-11-16|MEM|WAS|7:00 PM|Capital One Arena|Washington|DC
0022600248|2026-11-16|PHI|BKN|7:30 PM|Barclays Center|Brooklyn|NY
0022600249|2026-11-16|HOU|MIA|7:30 PM|Kaseya Center|Miami|FL
0022600250|2026-11-16|POR|MIN|8:00 PM|Target Center|Minneapolis|MN
0022600251|2026-11-16|GSW|NOP|9:00 PM|Smoothie King Center|New Orleans|LA
0022600252|2026-11-16|PHX|DEN|9:00 PM|Ball Arena|Denver|CO
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
        c = ARENA_COORDS.get(home)
        out.append({
            "game_id": gid, "date": date, "away": away, "home": home,
            "matchup": f"{away} @ {home}", "time_et": tm,
            "arena": arena, "city": city, "state": st,
            "lat": c[0] if c else None, "lon": c[1] if c else None,
            "source_url": f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}",
            "src": "schedule",
        })
    return out


SLATE = _slate()

# Arena table: name/city/state official, coordinates third-party (see ARENA_COORDS and
# BLOCKED["arena_coords_official"]).
ARENAS = sorted({(g["arena"], g["city"], g["state"]) for g in SLATE})

# --------------------------------------------------------------------------- results
# game_id, date, away, home, away_pts, home_pts, periods, away_q, home_q
# Quarter scores were read from the official LINESCORES table for 0022600231 only.
_R = """
0022600231|2026-11-14|DEN|NOP|116|108|4|29,27,30,30|23,28,31,26
0022600232|2026-11-14|DAL|CLE|117|127|4||
0022600233|2026-11-14|DET|MIA|117|137|4||
0022600234|2026-11-14|BKN|MEM|110|129|4||
0022600235|2026-11-14|CHI|MIN|117|106|4||
0022600236|2026-11-15|IND|PHI|124|131|4||
0022600237|2026-11-15|LAL|PHX|131|123|4||
0022600238|2026-11-15|CHA|LAC|105|113|4||
0022600239|2026-11-15|SAS|UTA|110|102|4||
0022600240|2026-11-15|DAL|BOS|94|131|4||
0022600241|2026-11-15|NYK|TOR|112|108|5||
"""


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
            "src": "schedule", "src_q": "linescore",
        })
    return out


RESULTS = _results()

# --------------------------------------------------------------------------- injuries
INJURY_META = {
    "release": "11/15/26 09:00 PM ET",
    "revision_time_et": "2026-11-15 21:00 ET",
    "retrieved_at_utc": "2026-11-16T02:20:00Z",
    "retrieved_at_et": "2026-11-15 21:20 ET",
    "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf",
    "index_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "newest_indexed_release_at_retrieval": "11/15/26 09:00 PM ET",
    "full_release_rows": 160,
    "rows_in_window": 62,
    "committed_transcript": "data/raw/capture_2026-11-16/injury_report_2026-11-15_0900PM.json",
    "previous_release_used_for_diff": (
        "11/15/26 06:15 PM ET",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf",
        "data/raw/capture_2026-11-15/injury_report_2026-11-15_0615PM.json",
        "data/raw/capture_2026-11-16/injury_delta_0615PM_to_0900PM.json",
    ),
    "delta_summary": {"status_changes": 2, "added": 7, "removed": 2, "unchanged": 151},
    "filing_policy": (
        "By 5 p.m. local the day before a game (1 p.m. local for the second night of a "
        "back-to-back); a game-day report follows between 11 a.m. and 1 p.m. local "
        "(8-10 a.m. for tip-offs at or before 5 p.m.)."
    ),
}

# date, time_et, matchup, team, player, status, reason   (player "" => NOT YET SUBMITTED)
_I = """
11/16/2026|07:00|CHI@CLE|Chicago Bulls|Awaka, Tobe|Out|Injury/Illness - Disc Irritation
11/16/2026|07:00|CHI@CLE|Chicago Bulls|Robinson, Orlando|Out|G League - On Assignment
11/16/2026|07:00|CHI@CLE|Chicago Bulls|Sellers, Jaylin|Out|G League - Two-Way
11/16/2026|07:00|CHI@CLE|Chicago Bulls|Smith, Jalen|Questionable|Injury/Illness - Left Finger Sprain
11/16/2026|07:00|CHI@CLE|Chicago Bulls|Wilson, Caleb|Out|Injury/Illness - Right Metacarpal Fracture
11/16/2026|07:00|CHI@CLE|Cleveland Cavaliers|Diop, Khalifa|Out|G League - On Assignment
11/16/2026|07:00|CHI@CLE|Cleveland Cavaliers|Merrill, Sam|Out|Injury/Illness - Right Elbow Injury Management
11/16/2026|07:00|CHI@CLE|Cleveland Cavaliers|Mobley, Evan|Out|Injury/Illness - Left Great Toe Sprain
11/16/2026|07:00|CHI@CLE|Cleveland Cavaliers|Tomlin, Nae'Qwan|Out|Injury/Illness - Low Back Stress Reaction
11/16/2026|07:00|CHI@CLE|Cleveland Cavaliers|Tyson, Jaylon|Questionable|Injury/Illness - Right Ankle Injury Management
11/16/2026|07:00|CHI@CLE|Cleveland Cavaliers|Udeh, Jr., Ernest|Out|G League - Two-Way
11/16/2026|07:00|CHI@CLE|Cleveland Cavaliers|Watson, Peyton|Questionable|Injury/Illness - Right Abdominal Soreness
11/16/2026|07:00|MEM@WAS|Memphis Grizzlies|Edey, Zach|Questionable|Injury/Illness - Left Ankle Injury Management
11/16/2026|07:00|MEM@WAS|Memphis Grizzlies|Jackson, GG|Out|Injury/Illness - Left Foot Injury
11/16/2026|07:00|MEM@WAS|Memphis Grizzlies|Jerome, Ty|Out|Injury/Illness - Right Hip Soreness
11/16/2026|07:00|MEM@WAS|Memphis Grizzlies|Pippen Jr., Scotty|Out|Injury/Illness - Lumbar Disc Herniation
11/16/2026|07:00|MEM@WAS|Memphis Grizzlies|Post, Quinten|Questionable|Injury/Illness - Concussion Protocol
11/16/2026|07:00|MEM@WAS|Memphis Grizzlies|Saunders, Richie|Out|Injury/Illness - Right Knee Surgery
11/16/2026|07:00|MEM@WAS|Memphis Grizzlies|Stewart, Isaiah|Questionable|Injury/Illness - Illness
11/16/2026|07:00|MEM@WAS|Washington Wizards|||NOT YET SUBMITTED
11/16/2026|07:00|ORL@BOS|Orlando Magic|Banchero, Paolo|Out|Injury/Illness - Right High Ankle Sprain
11/16/2026|07:00|ORL@BOS|Orlando Magic|Isaac, Jonathan|Out|Injury/Illness - Left Knee Injury Management
11/16/2026|07:00|ORL@BOS|Orlando Magic|Nelson, Izaiyah|Out|Injury/Illness - Left Ankle Injury Recovery
11/16/2026|07:00|ORL@BOS|Orlando Magic|Penda, Noah|Out|Injury/Illness - Right Partially Torn Hamstring
11/16/2026|07:00|ORL@BOS|Boston Celtics|||NOT YET SUBMITTED
11/16/2026|07:30|HOU@MIA|Houston Rockets|||NOT YET SUBMITTED
11/16/2026|07:30|HOU@MIA|Miami Heat|Goldin, Vladislav|Out|G League - Two-Way
11/16/2026|07:30|HOU@MIA|Miami Heat|Larsson, Pelle|Questionable|Injury/Illness - Illness
11/16/2026|07:30|HOU@MIA|Miami Heat|Thompson, Klay|Available|Injury/Illness - Left Ankle Sprain
11/16/2026|07:30|PHI@BKN|Philadelphia 76ers|||NOT YET SUBMITTED
11/16/2026|07:30|PHI@BKN|Brooklyn Nets|Bilodeau, Tyler|Out|G League - Two-Way
11/16/2026|07:30|PHI@BKN|Brooklyn Nets|Jefferson, Joshua|Out|G League - On Assignment
11/16/2026|07:30|PHI@BKN|Brooklyn Nets|Nelson, Grant|Out|G League - Two-Way
11/16/2026|07:30|PHI@BKN|Brooklyn Nets|Powell, Drake|Out|G League - On Assignment
11/16/2026|07:30|PHI@BKN|Brooklyn Nets|Saraf, Ben|Out|G League - On Assignment
11/16/2026|08:00|GSW@NOP|Golden State Warriors|Butler III, Jimmy|Out|Injury/Illness - Right ACL Repair / Surgery
11/16/2026|08:00|GSW@NOP|Golden State Warriors|Curry, Stephen|Out|Injury/Illness - Right Oblique Tear
11/16/2026|08:00|GSW@NOP|Golden State Warriors|Moody, Moses|Out|Injury/Illness - Left Patellar Tendon Repair / Surgery
11/16/2026|08:00|GSW@NOP|Golden State Warriors|Porzingis, Kristaps|Out|Not With Team
11/16/2026|08:00|GSW@NOP|Golden State Warriors|Santos, Gui|Questionable|Injury/Illness - Right Ankle Inflammation
11/16/2026|08:00|GSW@NOP|Golden State Warriors|Williams, Brandon|Out|Injury/Illness - Left Hamstring Strain
11/16/2026|08:00|GSW@NOP|New Orleans Pelicans|Dia, Malik|Questionable|G League - Two-Way
11/16/2026|08:00|GSW@NOP|New Orleans Pelicans|Mathurin, Bennedict|Out|Injury/Illness - Left Plantar Fasciitis
11/16/2026|08:00|GSW@NOP|New Orleans Pelicans|McGowens, Bryce|Out|Injury/Illness - Left Elbow Infection
11/16/2026|08:00|GSW@NOP|New Orleans Pelicans|Murphy III, Trey|Out|Injury/Illness - Bilateral Patellar Tendinopathy
11/16/2026|08:00|GSW@NOP|New Orleans Pelicans|Murray, Dejounte|Out|Injury/Illness - Left Ankle Sprain
11/16/2026|08:00|GSW@NOP|New Orleans Pelicans|Pierre Jr., Jaron|Questionable|G League - Two-Way
11/16/2026|08:00|GSW@NOP|New Orleans Pelicans|Reese, Julian|Questionable|G League - Two-Way
11/16/2026|08:00|GSW@NOP|New Orleans Pelicans|Watford, Trendon|Out|Injury/Illness - Right Ankle Sprain
11/16/2026|08:00|POR@MIN|Portland Trail Blazers|Krejci, Vit|Out|Injury/Illness - Left Ankle Fracture
11/16/2026|08:00|POR@MIN|Portland Trail Blazers|Morant, Ja|Out|Injury/Illness - Left Hamstring Strain
11/16/2026|08:00|POR@MIN|Portland Trail Blazers|Sharpe, Shaedon|Out|Injury/Illness - Right Knee Surgery
11/16/2026|08:00|POR@MIN|Portland Trail Blazers|Youngblood, Chris|Out|Injury/Illness - Right Heel Contusion / Bone Bruise
11/16/2026|08:00|POR@MIN|Minnesota Timberwolves|Beringer, Joan|Available|Injury/Illness - Face Mask
11/16/2026|08:00|POR@MIN|Minnesota Timberwolves|Clark, Jaylen|Out|Injury/Illness - Right Hamstring Strain
11/16/2026|08:00|POR@MIN|Minnesota Timberwolves|DiVincenzo, Donte|Out|Injury/Illness - Right Achilles Tendon Repair / Surgery
11/16/2026|08:00|POR@MIN|Minnesota Timberwolves|Edwards, Anthony|Out|Injury/Illness - Right Knee Arthroscopy
11/16/2026|09:00|PHX@DEN|Phoenix Suns|||NOT YET SUBMITTED
11/16/2026|09:00|PHX@DEN|Denver Nuggets|Holmes II, DaRon|Out|
11/16/2026|09:00|PHX@DEN|Denver Nuggets|Nembhard, Ryan|Out|
11/16/2026|09:00|PHX@DEN|Denver Nuggets|Strawther, Julian|Out|
11/16/2026|09:00|PHX@DEN|Denver Nuggets|Whitmore, Cam|Out|
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
    ("F-301", "window", "Slate contains a repeat matchup on consecutive days: POR @ MIN is "
     "scheduled on both 2026-11-16 (0022600250) and 2026-11-17 (0022600254), in the same "
     "arena. Recorded, not resolved; no line is suppressed for it.",
     "https://www.nba.com/games?date=2026-11-19", "review"),
    ("F-302", "slate", "Official game IDs are not monotonic in tip order inside 2026-11-18: "
     "BOS@DEN is 0022600266 but tips at 9:30 PM ET, after GSW@DAL which is 0022600267 and "
     "tips at 8:00 PM ET. Do not use game ID as a date proxy.",
     "https://www.nba.com/games?date=2026-11-19", "review"),
    ("F-303", "injury", "The 11/15 09:00 PM ET release is inconsistent about how it marks an "
     "unfiled club: PHX@DEN prints an explicit 'NOT YET SUBMITTED' row for Phoenix, while "
     "the NYK@TOR block on 11/15 prints no New York rows at all. Both mean the club had not "
     "filed; only one is labelled. Both are recorded identically here and the difference is "
     "disclosed rather than smoothed over.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf", "review"),
    ("F-304", "results", "Quarter scores were captured for 1 of the 11 official finals in "
     "the result feed (0022600231). The other ten rows carry their game URL and a blank "
     "quarter column; nothing was estimated.",
     "https://www.nba.com/games?date=2026-11-15", "open"),
    ("F-305", "data", "Points scored per game is derived from the official OffRtg and POSS "
     "columns for all 30 clubs, because only 11 of 30 PTS rows were inside the fetched "
     "chunks of the traditional page (the table was read sorted by PTS descending). The 11 "
     "read rows are published as a cross-check and the largest disagreement is reported on "
     "the verification page.",
     "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame&dir=-1&sort=PTS", "open"),
    ("F-306", "travel", "Arena coordinates are THIRD-PARTY. NBA.com publishes arena, city "
     "and state but no lat/lon, and no official geocoder is reachable, so the coordinates "
     "come from Wikipedia/Wikidata (Wikimedia REST summary endpoint, captured 2026-11-15). "
     "Rest, back-to-back and 3-in-4 are computed from official schedule dates and are "
     "official. Every travel distance derived from the coordinates is published carrying "
     "this flag and is labelled derived, never official.",
     "https://www.nba.com/schedule", "open"),
    ("F-307", "rotation", "Measured minutes shares exist for the 2026-11-13 window (all nine "
     "games, from the official gamebook PDFs) but not for this window: no gamebook for an "
     "11/16-11/19 game can exist yet. The rotation column therefore applies a labelled "
     "mechanical rule over the last measured window instead of a fresh measurement.",
     "https://statsdmz.nba.com/pdfs/", "open"),
    ("F-308", "market", "No market price feed, so nothing on the bet surface is a bettable "
     "edge and every stake is 0.00. The bet surface is emitted only when the projection "
     "surface is complete and the owner has accepted the trigger policy.",
     "https://www.nba.com/games", "blocking"),
    ("F-401", "snapshot", "This snapshot was captured DURING the 2026-11-15 evening slate "
     "(2026-11-16 02:20-02:45 UTC = 21:20-21:45 ET). Three of the nine 11/15 games were "
     "still in progress: HOU@WAS (Q4 5:24), ATL@MIL (Q3 12:00) and OKC@SAC (Q1 7:59). Only "
     "the six games NBA.com marked Final entered the result feed; the three live scores are "
     "committed for provenance and are used in no statistic anywhere in this repository.",
     "https://www.nba.com/games?date=2026-11-15", "review"),
    ("F-402", "slate", "Tip-time disagreement for GSW@NOP on 2026-11-16: the official injury "
     "report prints '08:00 (ET)' while the official schedule (captured by session "
     "arena/f8f8f2b8-nba2) prints 21:00 ET. The schedule clock is used, because the PDF "
     "prints 12-hour times with no AM/PM marker; the disagreement is recorded, not resolved.",
     "https://www.nba.com/games?date=2026-11-16", "review"),
    ("F-403", "injury", "Two 11/16 blocks in the PDF (MEM@WAS and ORL@BOS) print NO tip time "
     "at all, in a column where the same page prints times for six other games. The time "
     "shown for those rows comes from the official schedule, not from the PDF.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf", "review"),
    ("F-404", "injury", "In the 11/16 MEM@WAS block the PDF prints 'Saunders, Richie' and "
     "'Stewart, Isaiah' between the last Memphis row and the Washington 'NOT YET SUBMITTED' "
     "row with no team cell of their own. Table position attributes them to Memphis; that is "
     "a position read, not a roster fact, and it is the only attribution available from the "
     "document.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf", "review"),
    ("F-405", "injury", "The four Denver Nuggets rows in the 11/16 PHX@DEN block (Holmes II, "
     "Nembhard, Strawther, Whitmore) print an Out status with an EMPTY reason cell. The "
     "reason is unknown from this document and is published blank, not filled in.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf", "review"),
    ("F-406", "slate", "All four 2026-11-19 games render the same 8:00 PM ET tip on "
     "nba.com/games. That is what the page printed and it is transcribed as read; it is "
     "plausible (all four are 7:00 p.m. Central local) but a single shared value across four "
     "games is worth a second look on the next roll.",
     "https://www.nba.com/games?date=2026-11-19", "review"),
    ("F-407", "injury", "The window is priced from the 11/15 09:00 PM ET release because the "
     "11/16 designations are filed the day before and no 11/16-dated release existed at "
     "retrieval. By league rule no report published on 11/15 can contain 11/17, 11/18 or "
     "11/19 rows, so three of the four window dates have no injury data at all and are "
     "published blank rather than carried forward.",
     "https://official.nba.com/nba-injury-report-2026-27-season/", "review"),
    ("F-408", "data", "The 11/15 09:00 PM release carries 160 rows; only the 62 with an "
     "11/16 game date are transcribed into this snapshot. The full 160-row transcript is "
     "committed at data/raw/capture_2026-11-16/injury_report_2026-11-15_0900PM.json and the "
     "mechanical diff against the previous release is at "
     "data/raw/capture_2026-11-16/injury_delta_0615PM_to_0900PM.json (2 status changes, 7 "
     "added, 2 removed, 151 unchanged).",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf", "review"),
]


def selftest() -> list[str]:
    """Mechanical checks on the transcription itself. Empty list == clean."""
    p: list[str] = []
    if len(TEAMS) != 30:
        p.append(f"TEAMS has {len(TEAMS)} clubs")
    if sum(t["w"] for t in TEAMS.values()) != 194:
        p.append(f"wins sum to {sum(t['w'] for t in TEAMS.values())}, expected 194")
    if sum(t["l"] for t in TEAMS.values()) != 194:
        p.append(f"losses sum to {sum(t['l'] for t in TEAMS.values())}, expected 194")
    for a, t in TEAMS.items():
        if t["w"] + t["l"] != t["gp"]:
            p.append(f"{a}: standings {t['w']}-{t['l']} != advanced GP {t['gp']}")
        if t["home_w"] + t["road_w"] > t["w"]:
            p.append(f"{a}: home+road wins exceed total wins")
        # The official NetRtg column is rounded independently of OffRtg and DefRtg, so it
        # can sit 0.1 away from their difference. Tolerated, disclosed, never "fixed".
        if abs((t["off_rtg"] - t["def_rtg"]) - t["net_rtg"]) > 0.15:
            p.append(f"{a}: NetRtg {t['net_rtg']} != OffRtg-DefRtg {t['off_rtg'] - t['def_rtg']:.1f}")
        # margin must equal NetRtg scaled by this club's own possessions per game
        want = t["net_rtg"] * t["poss"] / (100.0 * t["gp"])
        got = t["pts_for"] - t["pts_against"]
        if abs(want - got) > 0.20:
            p.append(f"{a}: derived margin {got:.2f} != NetRtg x POSS/(100xGP) {want:.3f}")
    if len(SLATE) != 29:
        p.append(f"SLATE has {len(SLATE)} games, expected 29")
    ids = [g["game_id"] for g in SLATE]
    if len(set(ids)) != len(ids):
        p.append("duplicate game id in SLATE")
    for g in SLATE:
        if g["away"] not in TEAMS or g["home"] not in TEAMS:
            p.append(f"{g['game_id']}: unknown team")
    if len(RESULTS) != 11:
        p.append(f"RESULTS has {len(RESULTS)} rows, expected 11")
    for r in RESULTS:
        if r["away_q"] and sum(r["away_q"]) != r["away_pts"]:
            p.append(f"{r['game_id']}: away quarters do not sum to the final")
        if r["home_q"] and sum(r["home_q"]) != r["home_pts"]:
            p.append(f"{r['game_id']}: home quarters do not sum to the final")
    if len(INJURIES) != 62:
        p.append(f"INJURIES has {len(INJURIES)} rows, expected 62 (57 player + 5 not-submitted)")
    if sum(1 for r in INJURIES if r["not_submitted"]) != 5:
        p.append("not-submitted row count is not 5")
    for g in SLATE:
        if g["home"] not in ARENA_COORDS:
            p.append(f'{g["game_id"]}: no arena coordinates for {g["home"]}')
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
    for x in selftest():
        print("PROBLEM:", x)
    print(f"snapshot {AS_OF_UTC}: {len(TEAMS)} clubs, {len(SLATE)} games, "
          f"{len(RESULTS)} finals, {len(INJURIES)} injury rows, {len(ARENAS)} arenas")
    raise SystemExit(1 if selftest() else 0)
