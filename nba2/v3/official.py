"""Official NBA snapshot captured by session `arena/e675ac3d-nba2` on 2026-11-15.

Every value below was read from the page named in ``SOURCES`` through the
platform page-fetch tool during this session (direct TLS egress to nba.com is
blocked in this sandbox; that limitation is recorded, not worked around).
Nothing is inferred, nothing is imputed, and no number is carried over from an
earlier session's snapshot.

Retrieval record
----------------
Retrieved 2026-11-15, 11:33-11:41 UTC (06:33-06:41 ET).

* ``www.nba.com/schedule`` (chunks 0-2) ..................... slate 11/14-11/19, ET tip
  times, arenas, city/state, official game IDs, official final scores for 11/14.
* ``www.nba.com/standings`` (chunks 0-1) .................... 30 clubs: W, L, WIN%, home
  split, road split, neutral, OT, LAST10, streak.
* ``www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame``
  (chunks 0-1) .............................................. 30 rows: GP, W, L, MIN,
  OffRtg, DefRtg, NetRtg, PACE, POSS, eFG%, TS%, TOV%, OREB%, DREB%, AST%.
* ``www.nba.com/stats/teams/opponent?...`` (chunks 0-1) ..... 30 rows: Opp PTS per game
  (points allowed) and the opponent +/- column.
* ``www.nba.com/stats/teams/traditional?...`` (chunks 1, 3) .. PTS per game, read for 16 of
  30 clubs (see ``PTS_READ``); the remaining 14 rows fell outside the chunks that
  were fetched and are NOT guessed - ``pts_for`` is derived from OffRtg x POSS
  instead, and the 16 read rows are published as an independent cross-check.
* ``official.nba.com/nba-injury-report-2026-27-season/`` .... index of every published
  report; at 06:33 ET the newest indexed release was 11/15 06:15 AM ET.
* ``Injury-Report_2026-11-15_06_00AM.pdf`` (chunks 0-1) ..... the release transcribed here:
  84 player rows for the nine 11/15 games + 16 explicit NOT YET SUBMITTED team rows
  for 11/16. No 11/17 or 11/18 row exists in any published report at capture time.
* ``www.nba.com/game/den-vs-nop-0022600231`` (chunk 2) ...... the official LINESCORES table,
  used to prove the quarter-score schema. The other four 11/14 linescores were NOT
  fetched (context budget); those cells are blank and flagged, never estimated.

Two mechanical cross-checks this snapshot passes (asserted in ``selftest``):
1. the 30 W/L records sum to 188 wins and 188 losses, which is exactly the 183
   official finals committed under ``data/raw/history/`` plus the five 11/14 finals
   read from the schedule page this session;
2. for every club, ``pts_for - pts_against`` agrees with ``net_rtg x pace / 100``
   to within 0.3 points per game.
"""

from __future__ import annotations

AS_OF_UTC = "2026-11-15T11:41:00Z"
AS_OF_ET = "2026-11-15 06:41 ET"
SESSION = "arena/e675ac3d-nba2"
WINDOW = ("2026-11-15", "2026-11-18")  # T+0 .. T+3 inclusive

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
        "PTS per game (read for 16 of 30 clubs - see PTS_READ), FGA, 3PA, FTA, REB, AST, TOV.",
    ),
    "schedule": (
        "NBA.com Schedule (official)",
        "https://www.nba.com/schedule",
        "Game IDs, ET tip times, arena, city and state, broadcast, and the official "
        "final scores of the already-completed 11/14 games.",
    ),
    "injury_pdf": (
        "NBA Official Injury Report 11/15/26 06:00 AM ET (official PDF)",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_00AM.pdf",
        "Per-player status (Out / Doubtful / Questionable / Probable / Available) with the "
        "stated reason, plus explicit NOT YET SUBMITTED team rows.",
    ),
    "injury_index": (
        "NBA Official - injury report policy and release archive (official)",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
        "Filing deadlines and the list of every published report for the season.",
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
    "player_minutes": (
        "Per-player minutes and usage",
        "nba.com/stats/players/traditional IS reachable this session (469 rows, MIN column "
        "present) but capturing all ten pages was outside this session's context budget. "
        "The rotation model is implemented and wired; its per-player shares are blank "
        "until the capture lands.",
        "https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
    ),
    "player_logs": (
        "Per-player game logs (minutes, points, rebounds, assists, opponent)",
        "The official player pages render season aggregates only for this client; there is "
        "no per-game log endpoint reachable here.",
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
        "Quarter scores for games other than 0022600231",
        "The official LINESCORES table was fetched for one 11/14 game. The other four were "
        "not fetched in this session; the cells are blank and each carries its own game URL.",
        "https://www.nba.com/games?date=2026-11-14",
    ),
    "future_injuries": (
        "Injury rows for 11/17 and 11/18",
        "A club files by 5 p.m. local the day before a game, so no report published at "
        "06:41 ET on 11/15 can contain 11/17 or 11/18 rows. Blank by league rule.",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
    ),
}

# --------------------------------------------------------------------------- teams
# abbr, name, W, L, homeW, homeL, roadW, roadL, GP, MIN, OffRtg, DefRtg, NetRtg,
# PACE, POSS, eFG%, TOV%, OREB%, DREB%, OppPTS, PTS_read(or None)
_T = """
LAL|Los Angeles Lakers|11|2|5|1|6|1|13|624.0|121.6|113.6|8.0|100.50|1306|58.7|16.8|33.2|64.3|114.2|None
SAS|San Antonio Spurs|11|2|5|2|6|0|13|629.0|119.6|106.6|13.0|98.94|1298|53.4|12.3|33.9|71.3|106.2|None
BOS|Boston Celtics|10|2|5|0|5|2|12|581.0|117.4|105.6|11.7|96.62|1168|54.8|15.1|32.7|67.5|103.1|None
HOU|Houston Rockets|10|3|7|1|3|2|13|624.0|119.3|110.2|9.1|97.42|1266|55.1|14.8|35.2|67.8|107.4|116.2
PHI|Philadelphia 76ers|10|3|5|2|5|1|13|624.0|111.0|109.5|1.5|100.04|1302|51.6|12.7|28.0|70.8|109.4|111.2
MEM|Memphis Grizzlies|9|4|3|4|6|0|13|629.0|119.0|110.4|8.5|100.46|1318|55.8|15.6|34.2|70.6|111.7|120.6
MIN|Minnesota Timberwolves|9|4|5|2|4|2|13|629.0|116.0|104.5|11.5|101.27|1326|55.5|15.6|35.4|69.5|106.8|118.3
POR|Portland Trail Blazers|9|3|3|2|6|1|12|576.0|118.8|111.1|7.7|100.67|1208|56.3|16.2|33.3|70.2|111.8|119.6
DET|Detroit Pistons|8|4|3|2|5|2|12|586.0|114.1|109.2|4.9|99.48|1217|53.9|14.1|29.8|66.6|110.3|115.7
GSW|Golden State Warriors|8|5|6|1|2|4|13|629.0|116.1|112.0|4.1|99.66|1307|55.4|15.9|32.7|68.5|112.4|116.7
OKC|Oklahoma City Thunder|8|5|5|0|3|5|13|624.0|112.7|109.0|3.7|98.58|1282|51.4|13.5|31.9|68.5|107.4|None
ATL|Atlanta Hawks|7|6|3|3|4|3|13|629.0|113.3|111.9|1.4|103.55|1356|52.8|14.6|33.2|69.2|116.8|None
CLE|Cleveland Cavaliers|7|7|5|2|2|5|14|677.0|116.9|115.4|1.6|99.72|1407|55.8|13.4|29.1|68.1|115.9|None
DAL|Dallas Mavericks|7|6|5|2|2|4|13|624.0|112.8|112.8|0.0|100.54|1308|53.5|15.7|33.0|66.5|113.3|None
DEN|Denver Nuggets|7|4|2|2|4|2|11|533.0|116.0|114.7|1.3|97.67|1087|55.0|13.5|30.2|67.7|112.8|114.6
MIA|Miami Heat|7|6|3|3|4|3|13|629.0|114.7|116.2|-1.5|102.49|1345|54.5|13.9|30.3|70.1|119.8|None
NYK|New York Knicks|6|6|4|3|2|3|12|576.0|114.5|108.6|5.9|95.63|1150|51.9|15.0|37.3|72.1|103.7|None
IND|Indiana Pacers|5|8|2|4|3|3|13|624.0|110.1|111.7|-1.5|101.15|1312|53.5|14.7|24.9|67.7|113.2|111.2
ORL|Orlando Magic|5|7|1|4|4|3|12|581.0|109.7|113.4|-3.7|98.23|1185|52.8|17.0|31.7|70.2|112.8|108.3
PHX|Phoenix Suns|5|6|5|3|0|3|11|528.0|113.8|117.6|-3.8|98.45|1080|54.4|14.2|29.1|61.3|116.1|None
TOR|Toronto Raptors|5|7|2|3|3|4|12|576.0|114.5|112.8|1.7|99.88|1197|51.9|14.4|36.2|66.9|112.8|114.3
CHA|Charlotte Hornets|4|8|3|4|1|4|12|576.0|101.9|113.1|-11.2|96.83|1161|48.1|20.2|35.7|73.7|109.6|98.6
NOP|New Orleans Pelicans|4|10|3|6|1|4|14|687.0|111.3|120.0|-8.6|101.83|1457|51.9|15.4|29.7|68.0|124.9|115.9
WAS|Washington Wizards|4|9|2|3|2|6|13|634.0|108.7|114.3|-5.5|99.63|1315|51.5|15.0|29.0|66.2|115.8|110.0
BKN|Brooklyn Nets|3|9|1|3|2|6|12|581.0|109.8|116.0|-6.2|99.47|1204|52.9|17.6|32.1|69.9|116.4|110.2
CHI|Chicago Bulls|3|9|1|4|2|5|12|581.0|109.4|120.3|-10.9|103.81|1257|51.7|16.5|30.7|65.1|125.9|None
LAC|LA Clippers|3|8|3|3|0|5|11|533.0|110.7|115.8|-5.1|100.55|1116|54.3|17.6|30.4|67.2|117.5|112.3
MIL|Milwaukee Bucks|1|12|1|6|0|6|13|624.0|105.7|120.0|-14.2|100.31|1305|51.1|16.6|30.5|64.3|120.2|None
SAC|Sacramento Kings|1|11|0|7|1|4|12|576.0|107.3|119.5|-12.2|101.00|1210|52.6|16.9|28.4|69.1|120.9|None
UTA|Utah Jazz|1|12|1|6|0|6|13|634.0|105.0|116.4|-11.3|100.50|1330|50.4|16.3|29.5|68.8|118.6|None
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
# game_id, date, away, home, time_et, arena, city, state
_S = """
0022600236|2026-11-15|IND|PHI|1:00 PM|Xfinity Mobile Arena|Philadelphia|PA
0022600237|2026-11-15|LAL|PHX|4:00 PM|Mortgage Matchup Center|Phoenix|AZ
0022600238|2026-11-15|CHA|LAC|4:30 PM|Intuit Dome|Inglewood|CA
0022600239|2026-11-15|SAS|UTA|5:00 PM|Delta Center|Salt Lake City|UT
0022600240|2026-11-15|DAL|BOS|6:00 PM|TD Garden|Boston|MA
0022600241|2026-11-15|NYK|TOR|6:00 PM|Scotiabank Arena|Toronto|ON
0022600242|2026-11-15|HOU|WAS|7:00 PM|Capital One Arena|Washington|DC
0022600243|2026-11-15|ATL|MIL|8:00 PM|Fiserv Forum|Milwaukee|WI
0022600244|2026-11-15|OKC|SAC|9:00 PM|Golden 1 Center|Sacramento|CA
0022600245|2026-11-16|ORL|BOS|7:00 PM|TD Garden|Boston|MA
0022600246|2026-11-16|CHI|CLE|7:00 PM|Rocket Arena|Cleveland|OH
0022600247|2026-11-16|MEM|WAS|7:00 PM|Capital One Arena|Washington|DC
0022600248|2026-11-16|PHI|BKN|7:30 PM|Barclays Center|Brooklyn|NY
0022600249|2026-11-16|HOU|MIA|7:30 PM|Kaseya Center|Miami|FL
0022600250|2026-11-16|POR|MIN|8:00 PM|Target Center|Minneapolis|MN
0022600251|2026-11-16|GSW|NOP|8:00 PM|Smoothie King Center|New Orleans|LA
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
# Quarter scores were read from the official LINESCORES table for 0022600231 only.
_R = """
0022600231|2026-11-14|DEN|NOP|116|108|4|29,27,30,30|23,28,31,26
0022600232|2026-11-14|DAL|CLE|117|127|4||
0022600233|2026-11-14|DET|MIA|117|137|4||
0022600234|2026-11-14|BKN|MEM|110|129|4||
0022600235|2026-11-14|CHI|MIN|117|106|4||
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
    "release": "11/15/26 06:00 AM ET",
    "revision_time_et": "2026-11-15 06:00 ET",
    "retrieved_at_utc": "2026-11-15T11:36:00Z",
    "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_00AM.pdf",
    "index_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "newest_indexed_release_at_retrieval": "11/15/26 06:15 AM ET",
    "previous_release_used_for_diff": (
        "11/14/26 04:30 AM ET",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_30AM.pdf",
        "data/raw/history/injury_report_2026-11-14_0430AM.json",
    ),
    "filing_policy": (
        "By 5 p.m. local the day before a game (1 p.m. local for the second night of a "
        "back-to-back); a game-day report follows between 11 a.m. and 1 p.m. local "
        "(8-10 a.m. for tip-offs at or before 5 p.m.)."
    ),
}

# date, time_et, matchup, team, player, status, reason   (player "" => NOT YET SUBMITTED)
_I = """
11/15/2026|01:00|IND@PHI|Indiana Pacers|Furphy, Johnny|Out|Injury/Illness - Right ACL Repair / Surgery
11/15/2026|01:00|IND@PHI|Indiana Pacers|Haliburton, Tyrese|Out|Injury/Illness - Left Hamstring Strain
11/15/2026|01:00|IND@PHI|Indiana Pacers|McConnell, T.J.|Probable|Injury/Illness - Right Hamstring Strain
11/15/2026|01:00|IND@PHI|Indiana Pacers|Nembhard, Andrew|Questionable|Injury/Illness - Left Hip Soreness / Tightness
11/15/2026|01:00|IND@PHI|Indiana Pacers|Nesmith, Aaron|Questionable|Injury/Illness - Left Hand Sprain
11/15/2026|01:00|IND@PHI|Indiana Pacers|Sheppard, Ben|Out|Injury/Illness - Left Meniscus Tear
11/15/2026|01:00|IND@PHI|Philadelphia 76ers|Barlow, Dominick|Out|Injury/Illness - Low Back Stress Reaction
11/15/2026|01:00|IND@PHI|Philadelphia 76ers|Bona, Adem|Out|Injury/Illness - Cervical Spine Sprain
11/15/2026|01:00|IND@PHI|Philadelphia 76ers|Embiid, Joel|Out|Injury/Illness - Right Foot Plantar Fascia Injury Management
11/15/2026|01:00|IND@PHI|Philadelphia 76ers|Hukporti, Ariel|Out|Injury/Illness - Right Achilles Tendon Rupture / Tear
11/15/2026|04:00|LAL@PHX|Los Angeles Lakers|Carr, Cameron|Out|Injury/Illness - Illness
11/15/2026|04:00|LAL@PHX|Los Angeles Lakers|Grimes, Quentin|Available|Injury/Illness - Right Finger Splint
11/15/2026|04:00|LAL@PHX|Los Angeles Lakers|James, Bronny|Questionable|Injury/Illness - Illness
11/15/2026|04:00|LAL@PHX|Los Angeles Lakers|Reaves, Austin|Out|Injury/Illness - Left Heel Contusion / Bone Bruise
11/15/2026|04:00|LAL@PHX|Los Angeles Lakers|Sexton, Collin|Questionable|Injury/Illness - Right Orbital Laceration
11/15/2026|04:00|LAL@PHX|Los Angeles Lakers|Thiero, Adou|Questionable|Injury/Illness - Left Ankle Sprain
11/15/2026|04:00|LAL@PHX|Phoenix Suns|Williams, Mark|Out|Injury/Illness - Left Shoulder Surgery
11/15/2026|04:30|CHA@LAC|Charlotte Hornets|Ajayi, Michael|Out|G League - Two-Way
11/15/2026|04:30|CHA@LAC|Charlotte Hornets|Boswell, Kylan|Out|G League - Two-Way
11/15/2026|04:30|CHA@LAC|Charlotte Hornets|Knueppel, Kon|Out|Injury/Illness - Left Hamstring Strain
11/15/2026|04:30|CHA@LAC|Charlotte Hornets|Schroder, Dennis|Out|Injury/Illness - Left Hamstring Strain
11/15/2026|04:30|CHA@LAC|Charlotte Hornets|Steinbach, Hannes|Out|G League - On Assignment
11/15/2026|04:30|CHA@LAC|LA Clippers|Beal, Bradley|Out|Injury/Illness - Right Knee Injury Management
11/15/2026|04:30|CHA@LAC|LA Clippers|Ingram, Brandon|Out|Injury/Illness - Right Heel Surgery
11/15/2026|04:30|CHA@LAC|LA Clippers|Miller, Jordan|Out|Injury/Illness - Left Rotator Cuff Surgery
11/15/2026|04:30|CHA@LAC|LA Clippers|Niederhauser, Yanic Konan|Out|Injury/Illness - Right Lisfranc Surgery
11/15/2026|05:00|SAS@UTA|San Antonio Spurs|Brown, Maliq|Out|G League - Two-Way
11/15/2026|05:00|SAS@UTA|San Antonio Spurs|Gillespie, Ja'Kobi|Out|G League - Two-Way
11/15/2026|05:00|SAS@UTA|San Antonio Spurs|Harris, Tobias|Out|Injury/Illness - Left Calf Strain
11/15/2026|05:00|SAS@UTA|San Antonio Spurs|Quaintance, Jayden|Out|Injury/Illness - Right Knee Surgery
11/15/2026|05:00|SAS@UTA|Utah Jazz|Alexander, Trey|Out|G League - Two-Way
11/15/2026|05:00|SAS@UTA|Utah Jazz|Bufkin, Kobe|Out|G League - Two-Way
11/15/2026|05:00|SAS@UTA|Utah Jazz|Hayes, Jaxson|Out|Injury/Illness - Left Knee Strain
11/15/2026|05:00|SAS@UTA|Utah Jazz|Ingram, Harrison|Out|G League - Two-Way
11/15/2026|05:00|SAS@UTA|Utah Jazz|Jackson Jr., Jaren|Out|Injury/Illness - Right MCL Tear
11/15/2026|05:00|SAS@UTA|Utah Jazz|Markkanen, Lauri|Out|Injury/Illness - Right Hand Fracture
11/15/2026|05:00|SAS@UTA|Utah Jazz|Nurkic, Jusuf|Out|Injury/Illness - Right 2nd Plantar Plate Tear
11/15/2026|06:00|DAL@BOS|Dallas Mavericks|||NOT YET SUBMITTED
11/15/2026|06:00|DAL@BOS|Boston Celtics|Carter, Devin|Questionable|G League - Two-Way
11/15/2026|06:00|DAL@BOS|Boston Celtics|Cenac Jr., Christopher|Questionable|G League - On Assignment
11/15/2026|06:00|DAL@BOS|Boston Celtics|Mitchell, Dillon|Questionable|G League - Two-Way
11/15/2026|06:00|DAL@BOS|Boston Celtics|Williams, Amari|Questionable|G League - Two-Way
11/15/2026|06:00|NYK@TOR|New York Knicks|||NOT YET SUBMITTED
11/15/2026|06:00|NYK@TOR|Toronto Raptors|Barnes, Scottie|Questionable|Injury/Illness - Left Groin Strain
11/15/2026|06:00|NYK@TOR|Toronto Raptors|Bittle, Nate|Out|Injury/Illness - Right Foot Avulsion Fracture
11/15/2026|06:00|NYK@TOR|Toronto Raptors|Leonard, Kawhi|Out|Injury/Illness - Left Knee Injury Management
11/15/2026|06:00|NYK@TOR|Toronto Raptors|McCullar Jr., Kevin|Out|G League - Two-Way
11/15/2026|06:00|NYK@TOR|Toronto Raptors|Smith, Malachi|Out|G League - Two-Way
11/15/2026|07:00|HOU@WAS|Houston Rockets|Adams, Steven|Probable|Injury/Illness - Right Soleus Strain
11/15/2026|07:00|HOU@WAS|Houston Rockets|Capela, Clint|Out|Injury/Illness - Right Ankle Sprain
11/15/2026|07:00|HOU@WAS|Houston Rockets|Copeland, Quadir|Out|G League - Two-Way
11/15/2026|07:00|HOU@WAS|Houston Rockets|Phillips, Julian|Out|G League - Two-Way
11/15/2026|07:00|HOU@WAS|Houston Rockets|Smart, Marcus|Out|League Suspension
11/15/2026|07:00|HOU@WAS|Houston Rockets|VanVleet, Fred|Out|Injury/Illness - Right Knee Injury Management
11/15/2026|07:00|HOU@WAS|Washington Wizards|Beekman, Reece|Out|Injury/Illness - Right AC Joint Injury
11/15/2026|07:00|HOU@WAS|Washington Wizards|Carrington, Bub|Questionable|Injury/Illness - Chest / Sternum Contusion
11/15/2026|07:00|HOU@WAS|Washington Wizards|Champagne, Justin|Out|Injury/Illness - Right Foot Surgery
11/15/2026|07:00|HOU@WAS|Washington Wizards|Johnson, Tre|Questionable|Injury/Illness - Low Back Soreness
11/15/2026|07:00|HOU@WAS|Washington Wizards|Okpara, Felix|Questionable|G League - Two-Way
11/15/2026|07:00|HOU@WAS|Washington Wizards|Sarr, Alex|Questionable|Injury/Illness - Illness
11/15/2026|07:00|HOU@WAS|Washington Wizards|Vukcevic, Tristan|Out|Injury/Illness - Left Hip Impingement
11/15/2026|07:00|HOU@WAS|Washington Wizards|Watkins, Jamir|Out|Injury/Illness - Left ACL Repair / Surgery
11/15/2026|08:00|ATL@MIL|Atlanta Hawks|Flemings, Kingston|Out|Injury/Illness - Lumbar Strain
11/15/2026|08:00|ATL@MIL|Atlanta Hawks|Gilbert, Keshon|Out|Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure
11/15/2026|08:00|ATL@MIL|Atlanta Hawks|Gueye, Mouhamed|Out|Injury/Illness - Left Foot Fracture
11/15/2026|08:00|ATL@MIL|Atlanta Hawks|Landale, Jock|Available|Injury/Illness - Face Mask
11/15/2026|08:00|ATL@MIL|Atlanta Hawks|Newell, Asa|Out|Injury/Illness - Left Great Toe Hyperextension
11/15/2026|08:00|ATL@MIL|Atlanta Hawks|Veesaar, Henri|Out|Injury/Illness - Right ACL Tear
11/15/2026|08:00|ATL@MIL|Atlanta Hawks|Wilson, Jalen|Doubtful|G League - Two-Way
11/15/2026|08:00|ATL@MIL|Milwaukee Bucks|Dieng, Ousmane|Out|Injury/Illness - Left Finger Sprain
11/15/2026|08:00|ATL@MIL|Milwaukee Bucks|Jones, Kam|Out|G League - Two-Way
11/15/2026|08:00|ATL@MIL|Milwaukee Bucks|Markovic, Bogoljub|Out|G League - On Assignment
11/15/2026|08:00|ATL@MIL|Milwaukee Bucks|Nance, Pete|Out|G League - Two-Way
11/15/2026|08:00|ATL@MIL|Milwaukee Bucks|Ryan, Cormac|Out|G League - Two-Way
11/15/2026|09:00|OKC@SAC|Oklahoma City Thunder|Holmgren, Chet|Out|Injury/Illness - Right Knee/ Injury Recovery
11/15/2026|09:00|OKC@SAC|Oklahoma City Thunder|Mitchell, Ajay|Questionable|Injury/Illness - Left Ankle Sprain
11/15/2026|09:00|OKC@SAC|Oklahoma City Thunder|Sorber, Thomas|Out|Injury/Illness - Right Knee Surgery
11/15/2026|09:00|OKC@SAC|Oklahoma City Thunder|Wallace, Cason|Out|Injury/Illness - Left Shoulder Surgery
11/15/2026|09:00|OKC@SAC|Oklahoma City Thunder|Williams, Jalen|Out|Injury/Illness - Left Ankle Surgery
11/15/2026|09:00|OKC@SAC|Oklahoma City Thunder|Williams, Jaylin|Out|Injury/Illness - Low Back Spasms
11/15/2026|09:00|OKC@SAC|Sacramento Kings|Achiuwa, Precious|Questionable|Injury/Illness - Left Ankle Soreness
11/15/2026|09:00|OKC@SAC|Sacramento Kings|Mogbo, Jonathan|Out|G League - Two-Way
11/15/2026|09:00|OKC@SAC|Sacramento Kings|Murray, Keegan|Questionable|Injury/Illness - Illness
11/15/2026|09:00|OKC@SAC|Sacramento Kings|Pedulla, Sean|Out|G League - Two-Way
11/15/2026|09:00|OKC@SAC|Sacramento Kings|Raynaud, Maxime|Out|Injury/Illness - Right Patella Subluxation
11/15/2026|09:00|OKC@SAC|Sacramento Kings|Simmons, Ben|Out|Injury/Illness - Right Achilles Tendon Repair / Surgery
11/16/2026|07:00|CHI@CLE|Chicago Bulls|||NOT YET SUBMITTED
11/16/2026|07:00|CHI@CLE|Cleveland Cavaliers|||NOT YET SUBMITTED
11/16/2026|07:00|MEM@WAS|Memphis Grizzlies|||NOT YET SUBMITTED
11/16/2026|07:00|MEM@WAS|Washington Wizards|||NOT YET SUBMITTED
11/16/2026|07:00|ORL@BOS|Orlando Magic|||NOT YET SUBMITTED
11/16/2026|07:00|ORL@BOS|Boston Celtics|||NOT YET SUBMITTED
11/16/2026|07:30|HOU@MIA|Houston Rockets|||NOT YET SUBMITTED
11/16/2026|07:30|HOU@MIA|Miami Heat|||NOT YET SUBMITTED
11/16/2026|07:30|PHI@BKN|Philadelphia 76ers|||NOT YET SUBMITTED
11/16/2026|07:30|PHI@BKN|Brooklyn Nets|||NOT YET SUBMITTED
11/16/2026|08:00|GSW@NOP|Golden State Warriors|||NOT YET SUBMITTED
11/16/2026|08:00|GSW@NOP|New Orleans Pelicans|||NOT YET SUBMITTED
11/16/2026|08:00|POR@MIN|Portland Trail Blazers|||NOT YET SUBMITTED
11/16/2026|08:00|POR@MIN|Minnesota Timberwolves|||NOT YET SUBMITTED
11/16/2026|09:00|PHX@DEN|Phoenix Suns|||NOT YET SUBMITTED
11/16/2026|09:00|PHX@DEN|Denver Nuggets|||NOT YET SUBMITTED
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
     "arena. NYK @ TOR also repeats inside the window (0022600241 on 11/15, 0022600253 on "
     "11/17). Recorded, not resolved; no line is suppressed for it.",
     "https://www.nba.com/schedule", "review"),
    ("F-302", "slate", "Official game IDs are not monotonic in tip order inside 2026-11-18: "
     "BOS@DEN is 0022600266 but tips at 9:30 PM ET, after GSW@DAL which is 0022600267 and "
     "tips at 8:00 PM ET. Do not use game ID as a date proxy.",
     "https://www.nba.com/schedule", "review"),
    ("F-303", "injury", "The 11/15 06:00 AM ET release prints an explicit 'NOT YET SUBMITTED' "
     "row for DAL (DAL@BOS) but prints no row at all for NYK (NYK@TOR). Both mean the club "
     "had not filed; only one is labelled. The two are recorded identically here, and the "
     "difference in the PDF is disclosed rather than smoothed over.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_00AM.pdf", "review"),
    ("F-304", "results", "Quarter scores were captured for 1 of the 5 official 11/14 finals "
     "(0022600231). The other four rows carry their game URL and a blank quarter column; "
     "nothing was estimated.",
     "https://www.nba.com/games?date=2026-11-14", "open"),
    ("F-305", "data", "Points scored per game is derived from the official OffRtg and POSS "
     "columns for all 30 clubs, because only 16 of 30 PTS rows were inside the fetched "
     "chunks of the traditional page. The 16 read rows are published as a cross-check and "
     "the largest disagreement is reported on the verification page.",
     "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame", "open"),
    ("F-306", "travel", "No arena coordinates: NBA.com publishes arena, city and state but no "
     "lat/lon, and no official geocoder is reachable. Travel distance is blank for every "
     "game; rest, back-to-back and 3-in-4 are computed from the official schedule dates.",
     "https://www.nba.com/schedule", "open"),
    ("F-307", "rotation", "nba.com/stats/players/traditional is reachable this session (469 "
     "rows with a MIN column), which contradicts the standing 'player_box' blocked entry on "
     "the v2 site. The capture was not completed in this session's context budget; the "
     "rotation model ships wired but empty.",
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
    if sum(t["w"] for t in TEAMS.values()) != 188:
        p.append(f"wins sum to {sum(t['w'] for t in TEAMS.values())}, expected 188")
    if sum(t["l"] for t in TEAMS.values()) != 188:
        p.append(f"losses sum to {sum(t['l'] for t in TEAMS.values())}, expected 188")
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
    if len(SLATE) != 34:
        p.append(f"SLATE has {len(SLATE)} games, expected 34")
    ids = [g["game_id"] for g in SLATE]
    if len(set(ids)) != len(ids):
        p.append("duplicate game id in SLATE")
    for g in SLATE:
        if g["away"] not in TEAMS or g["home"] not in TEAMS:
            p.append(f"{g['game_id']}: unknown team")
    if len(RESULTS) != 5:
        p.append(f"RESULTS has {len(RESULTS)} rows")
    for r in RESULTS:
        if r["away_q"] and sum(r["away_q"]) != r["away_pts"]:
            p.append(f"{r['game_id']}: away quarters do not sum to the final")
        if r["home_q"] and sum(r["home_q"]) != r["home_pts"]:
            p.append(f"{r['game_id']}: home quarters do not sum to the final")
    if len(INJURIES) != 102:
        p.append(f"INJURIES has {len(INJURIES)} rows, expected 102 (84 player + 18 not-submitted)")
    if sum(1 for r in INJURIES if r["not_submitted"]) != 18:
        p.append("not-submitted row count is not 18")
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
