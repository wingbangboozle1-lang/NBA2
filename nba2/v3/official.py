"""Official NBA capture for v3 — session ``arena/a1fddb57-nba2``, 2026-11-15 (UTC).

WHY THIS MODULE EXISTS
----------------------
v2's ``nba2/v2/official.py`` froze a 2026-11-14 09:40Z snapshot. By 2026-11-15 that
snapshot was one game day stale: the five 2026-11-14 games had been played, the league
record had moved from 183 to 188 games, and the injury report had advanced from the
11/14 04:30 AM ET release to the 11/15 06:15 AM ET release (23 further revisions).

This module is a **new, separately provenance-tagged capture**. It does not edit v2's
transcription — v2 stays reproducible and its own tests keep passing. Every field family
below carries the URL it was read from and the timestamp it was read at, so each published
row can link to the page it came from.

READ BY
-------
Session ``arena/a1fddb57-nba2`` on **2026-11-15 between 11:33Z and 12:55Z** through the
platform page-fetch tool. Direct TLS egress to ``nba.com`` is blocked in this sandbox
(recorded, not worked around); ``curl`` returns ``SSL_ERROR_SYSCALL``. The fetch tool
reaches the official CDN and rendered pages, so the pages below were genuinely read.

  * https://www.nba.com/standings ........................... 30 team records + splits ... OK
  * https://www.nba.com/stats/teams/traditional ............. 30 rows, 26 columns ........ OK
  * https://www.nba.com/stats/teams/opponent ................ 30 rows, 25 columns ........ OK
  * https://www.nba.com/stats/teams/advanced ................ 30 rows, 20 columns ........ OK
  * https://www.nba.com/schedule?date=2026-11-15 ............ 11/14 finals + 11/15-11/17 .. OK
  * https://www.nba.com/game/den-vs-nop-0022600231 .......... box score + quarter lines .. OK
  * https://www.nba.com/game/{gid} .......................... 11/14 finals, LINESCORES .... OK
    (all five: 0022600231..35, per-quarter scores transcribed and summed against the final)
  * https://www.nba.com/games?date=2026-11-14 ............... game cards, 5 finals ........ OK
  * https://official.nba.com/nba-injury-report-2026-27-season/ report index, deadlines .. OK
  * https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf ... OK
  * https://www.nba.com/stats/players/traditional ............ season aggregates ......... OK

BLOCKED (stated, never invented)
--------------------------------
  * ``cdn.nba.com/static/json/...`` box-score JSON .......... HTTP 500 through the fetch tool
  * ``stats.nba.com`` / ``cdn.nba.com`` JSON endpoints ....... TLS blocked from this sandbox
  * market odds (spread/total/moneyline/prop) .............. no licensed feed is connected

WHAT IS *NOT* HERE, AND WHY
---------------------------
* No value is inferred. A field not read is absent, and the module says so.
* Quarter scores exist for the five 2026-11-14 finals, because all five game pages were read
  and each LINESCORES block sums exactly to its printed final. Every earlier date in the
  results feed carries a final score only; its quarter cells are blank with that reason.
* Injury rows are the 11/15 06:15 AM ET release verbatim. Rows the league printed
  "NOT YET SUBMITTED" are carried in ``INJ_NOT_SUBMITTED`` rather than dropped, so a
  blank designation is distinguishable from a missing team.
* Per-player game logs exist only for the one box score read (DEN@NOP). Season
  aggregates exist for ``PLAYERS_SEASON`` only.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- provenance
AS_OF = "2026-11-15"
RETRIEVED_UTC = "2026-11-15T11:33:00Z"
RETRIEVED_BY = "arena/a1fddb57-nba2"
METHOD = (
    "Platform page-fetch tool over the public official pages; direct TLS egress to nba.com "
    "is blocked in this sandbox (curl -> SSL_ERROR_SYSCALL), and cdn.nba.com box-score JSON "
    "returns HTTP 500 to the fetch tool. Values are transcribed from the rendered tables, "
    "never estimated."
)

SOURCES = {
    "standings": (
        "NBA.com Standings (official)",
        "https://www.nba.com/standings",
        "W, L, WIN%, GB, CONF, DIV, HOME, ROAD, Neutral, OT, LAST10, STREAK for all 30 clubs.",
        "2026-11-15",
    ),
    "team_trad": (
        "NBA.com Stats - Teams Traditional (official)",
        "https://www.nba.com/stats/teams/traditional",
        "Per-game GP/W/L/MIN/PTS/FGM/FGA/FG%/3PM/3PA/3P%/FTM/FTA/FT%/OREB/DREB/REB/AST/TOV/"
        "STL/BLK/BLKA/PF/PFD/+-, all 30 clubs.",
        "2026-11-15",
    ),
    "team_opp": (
        "NBA.com Stats - Teams Opponent (official)",
        "https://www.nba.com/stats/teams/opponent",
        "Opponent per-game shooting, rebounding, turnovers, and Opp PTS for all 30 clubs.",
        "2026-11-15",
    ),
    "team_adv": (
        "NBA.com Stats - Teams Advanced (official)",
        "https://www.nba.com/stats/teams/advanced",
        "OffRtg, DefRtg, NetRtg, AST%, AST/TO, OREB%/DREB%/REB%/TOV%, eFG%, TS%, PACE, PIE, "
        "POSS for all 30 clubs.",
        "2026-11-15",
    ),
    "schedule": (
        "NBA.com Schedule (official)",
        "https://www.nba.com/schedule?date=2026-11-15",
        "Game IDs, ET tip times, venues and cities for 2026-11-14 .. 2026-11-17.",
        "2026-11-15",
    ),
    "game_page": (
        "NBA.com Game Summary - LINESCORES + BOX SCORE (official)",
        "https://www.nba.com/game/den-vs-nop-0022600231",
        "Per-quarter scores (LINESCORES) and per-player MIN/PTS/REB/AST for the 2026-11-14 finals.",
        "2026-11-15",
    ),
    "games": (
        "NBA.com Games & Scores (official)",
        "https://www.nba.com/games?date=2026-11-14",
        "Official final scores and the per-date game-count strip used for the completeness check.",
        "2026-11-15",
    ),
    "injury_pdf": (
        "NBA Official Injury Report 11/15/26 06:15 AM ET (official PDF)",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf",
        "Per-player Current Status and stated Reason, by game date, for 11/15/26 and 11/16/26.",
        "2026-11-15",
    ),
    "injury_index": (
        "NBA Official - Injury Report policy and report archive (official)",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
        "Filing deadlines and the list of every published revision (11/15 12:00 AM -> 06:15 AM ET).",
        "2026-11-15",
    ),
    "players_trad": (
        "NBA.com Stats - Players Traditional (official)",
        "https://www.nba.com/stats/players/traditional",
        "Season aggregates (GP, MIN, PTS, REB, AST) for the players named in PLAYERS_SEASON.",
        "2026-11-15",
    ),
}

BLOCKED = {
    "odds": (
        "Market prices (spread, total, moneyline, prop lines)",
        "No licensed odds feed is connected and nba.com renders odds client-side only. "
        "Required for: any value/edge claim, CLV, stake sizing, ROI, leaderboard scoring.",
        "https://www.nba.com/games",
    ),
    "boxscore_json": (
        "Machine-readable box scores (cdn.nba.com static JSON)",
        "cdn.nba.com/static/json/liveData/boxscore/boxscore_<id>.json returns HTTP 500 through "
        "the fetch tool and stats.nba.com is TLS-blocked from this sandbox. Per-game data is "
        "therefore read from the rendered game page, which is why only some games carry it.",
        "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022600231.json",
    ),
    "quarter_scores_all_dates": (
        "Per-quarter scores for every game in the results feed",
        "LINESCORES is rendered per game page. This capture read ten game pages (the five "
        "2026-11-14 finals) and therefore carries quarter scores for those five. Earlier dates "
        "are in the results feed with final scores only, and their quarter cells are blank.",
        "https://www.nba.com/schedule?date=2026-11-14",
    ),
    "future_injuries": (
        "Injury designations beyond the next filing deadline",
        "The league publishes a row only after a club files: 5 p.m. local the day before, or "
        "11 a.m.-1 p.m. local on game day. For 11/17 no club had filed at capture time, so no "
        "official row exists to read.",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
    ),
    "player_game_logs_all": (
        "Per-player game logs for the whole season",
        "Only the one box score in this capture (DEN@NOP) carries per-player game data. The "
        "season page served to this client exposes aggregates, not game-by-game lines.",
        "https://www.nba.com/stats/players/traditional",
    ),
}

NAMES = {
    "ATL": "Atlanta Hawks", "BKN": "Brooklyn Nets", "BOS": "Boston Celtics",
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

# --------------------------------------------------------------------------- standings
# Columns: tricode|W|L|conf_rec|div_rec|home|road|neutral|ot|last10|streak
# Read from nba.com/standings on 2026-11-15. Records are the live table, i.e. they include
# the five 2026-11-14 finals. Verified three ways in nba2/v3/integrity.py:
#   wins == losses, home_wins == road_losses, home_losses == road_wins.
_STANDINGS_RAW = """
ATL|7|6|7-2|4-1|3-3|4-3|0-0|0-1|5-5|L 2
BKN|3|9|2-7|0-2|1-3|2-6|0-0|0-1|3-7|L 1
BOS|10|2|10-1|4-0|5-0|5-2|0-0|1-0|9-1|W 5
CHA|4|8|4-7|2-2|3-4|1-4|0-0|0-0|3-7|L 1
CHI|3|9|2-8|1-0|1-4|2-5|0-0|1-0|2-8|W 2
CLE|7|7|5-5|1-0|5-2|2-5|0-0|1-0|4-6|W 1
DAL|7|6|3-5|1-3|5-2|2-4|0-0|0-0|6-4|L 2
DEN|7|4|5-4|0-2|2-2|4-2|1-0|1-0|7-3|W 2
DET|8|4|8-3|0-0|3-2|5-2|0-0|1-0|6-4|L 1
GSW|8|5|6-5|3-2|6-1|2-4|0-0|1-0|8-2|L 2
HOU|10|3|6-3|2-1|7-1|3-2|0-0|0-0|7-3|W 3
IND|5|8|3-5|0-1|2-4|3-3|0-1|0-0|3-7|W 2
LAC|3|8|3-6|1-4|3-3|0-5|0-0|0-1|2-8|W 1
LAL|11|2|6-2|4-1|5-1|6-1|0-0|0-0|8-2|W 7
MEM|9|4|7-3|1-1|3-4|6-0|0-0|0-1|6-4|W 2
MIA|7|6|4-2|1-1|3-3|4-3|0-0|1-0|7-3|W 4
MIL|1|12|1-9|1-2|1-6|0-6|0-0|0-0|1-9|L 9
MIN|9|4|5-2|1-0|5-2|4-2|0-0|0-1|6-4|L 1
NOP|4|10|3-8|1-1|3-6|1-4|0-0|2-1|4-6|L 6
NYK|6|6|6-6|1-3|4-3|2-3|0-0|0-0|6-4|L 2
OKC|8|5|5-5|1-2|5-0|3-5|0-0|0-0|5-5|L 3
ORL|5|7|3-4|0-2|1-4|4-3|0-0|0-1|5-5|W 3
PHI|10|3|10-3|3-1|5-2|5-1|0-0|0-0|7-3|W 1
PHX|5|6|3-6|2-1|5-3|0-3|0-0|0-0|5-5|W 2
POR|9|3|9-3|4-0|3-2|6-1|0-0|0-0|7-3|W 3
SAC|1|11|1-9|0-2|0-7|1-4|0-0|0-0|1-9|L 5
SAS|11|2|10-2|2-1|5-2|6-0|0-0|1-0|10-0|W 11
TOR|5|7|4-3|0-2|2-3|3-4|0-0|0-0|3-7|L 3
UTA|1|12|1-10|0-2|1-6|0-6|0-0|0-2|0-10|L 11
WAS|4|9|4-8|2-3|2-3|2-6|0-0|0-1|2-8|L 6
"""

# --------------------------------------------------------------------------- traditional
# Columns: tricode|GP|W|L|MIN|PTS|FGM|FGA|FG%|3PM|3PA|3P%|FTM|FTA|FT%|OREB|DREB|REB|AST|TOV|STL|BLK|BLKA|PF|PFD|+/-
_TEAM_TRAD_RAW = """
LAL|13|11|2|48.0|122.2|42.1|83.6|50.3|14.1|36.8|38.3|23.9|29.8|80.4|11.3|29.5|40.8|24.7|16.9|11.0|6.2|4.2|23.4|24.2|7.9
SAS|13|11|2|48.4|119.5|42.9|92.0|46.7|12.5|35.9|34.7|21.2|26.5|79.9|13.2|35.4|48.6|28.1|12.3|8.3|7.3|4.9|20.0|21.2|13.2
BOS|12|10|2|48.4|114.3|39.8|87.2|45.6|16.0|42.0|38.1|18.8|23.8|78.9|13.1|31.7|44.8|26.8|14.7|8.2|4.9|4.2|21.5|22.9|11.2
HOU|13|10|3|48.0|116.2|41.5|86.9|47.8|12.8|34.3|37.2|20.3|25.0|81.2|13.2|31.2|44.4|26.8|14.5|7.9|6.1|4.1|19.9|21.9|8.8
PHI|13|10|3|48.0|111.2|39.6|88.1|45.0|11.6|33.8|34.3|20.3|25.9|78.3|10.3|32.8|43.1|26.1|12.8|8.4|4.3|5.8|20.6|20.8|1.8
MEM|13|9|4|48.4|120.6|42.1|89.4|47.1|15.5|39.6|39.2|20.9|24.7|84.7|12.5|34.8|47.4|27.8|15.8|6.5|5.1|7.2|23.6|21.5|8.9
MIN|13|9|4|48.4|118.3|43.4|90.9|47.7|14.2|38.4|36.9|17.4|25.5|68.1|13.8|34.6|48.5|26.0|15.9|9.0|5.1|6.4|22.0|22.8|11.5
POR|12|9|3|48.0|119.6|39.8|84.7|46.9|15.9|43.6|36.5|24.2|30.7|78.8|11.5|32.8|44.3|25.3|16.3|7.1|5.1|4.2|22.3|24.4|7.8
DET|12|8|4|48.8|115.7|40.9|88.4|46.3|13.5|36.8|36.7|20.3|25.8|79.0|12.2|32.3|44.4|27.7|14.3|9.4|6.4|6.1|23.8|22.7|5.4
GSW|13|8|5|48.4|116.7|40.0|87.0|46.0|16.4|41.6|39.4|20.3|25.1|81.0|12.5|31.9|44.5|28.0|16.0|8.2|5.4|5.7|21.9|22.2|4.3
OKC|13|8|5|48.0|111.2|41.2|90.7|45.4|11.0|32.1|34.3|17.8|21.8|81.7|11.5|35.1|46.6|22.8|13.3|7.9|5.4|5.3|19.3|21.0|3.8
ATL|13|7|6|48.4|118.2|43.9|97.2|45.2|14.8|43.3|34.1|15.5|20.4|76.2|13.9|30.2|44.1|31.5|15.2|10.3|4.0|6.0|22.1|19.4|1.3
CLE|14|7|7|48.4|117.5|41.8|88.7|47.1|15.4|41.6|37.0|18.5|24.3|76.2|10.7|34.9|45.6|27.1|13.5|7.1|5.3|3.6|21.6|20.3|1.6
DAL|13|7|6|48.0|113.5|41.2|88.8|46.4|12.5|37.5|33.5|18.5|23.5|78.4|12.7|30.9|43.6|26.1|15.8|8.7|5.5|4.8|22.3|20.9|0.2
MIA|13|7|6|48.4|118.7|42.0|89.5|46.9|13.5|39.5|34.1|21.2|28.7|74.0|10.5|32.2|42.8|29.8|14.4|7.8|5.5|5.2|21.1|25.1|-1.2
NYK|12|6|6|48.0|109.8|38.8|88.9|43.6|14.8|41.1|36.1|17.4|21.9|79.5|13.7|34.0|47.7|26.8|14.4|7.4|4.1|6.2|20.9|21.1|6.1
DEN|11|7|4|48.5|114.6|41.5|85.2|48.7|10.8|31.0|34.9|20.9|26.5|79.0|10.1|32.2|42.3|27.7|13.4|9.0|4.5|4.5|19.0|23.2|1.8
PHX|11|5|6|48.0|111.7|41.3|88.5|46.7|13.6|37.0|36.9|15.5|20.0|77.7|10.6|28.3|38.9|27.2|13.9|8.4|4.5|4.7|22.0|18.6|-4.4
ORL|12|5|7|48.4|108.3|38.4|85.8|44.8|13.8|41.1|33.7|17.7|22.6|78.2|11.0|31.9|42.9|26.0|16.8|7.4|4.1|5.0|22.8|23.3|-4.4
TOR|12|5|7|48.0|114.3|41.4|91.2|45.4|11.8|36.0|32.9|19.6|26.6|73.7|13.8|27.2|41.0|28.1|14.3|10.6|4.4|5.5|25.8|24.3|1.4
IND|13|5|8|48.0|111.2|40.4|86.8|46.5|12.2|36.5|33.3|18.2|24.1|75.7|9.8|32.0|41.8|27.5|14.8|7.4|4.3|4.4|20.3|22.7|-2.1
CHA|12|4|8|48.0|98.6|34.8|86.6|40.1|13.8|44.2|31.1|15.3|18.7|82.1|15.0|31.6|46.6|21.8|19.6|6.9|4.6|4.6|20.4|21.6|-11.0
WAS|13|4|9|48.8|110.0|39.8|87.1|45.8|9.9|32.5|30.5|20.4|25.2|80.8|10.7|32.4|43.1|23.6|15.2|7.5|5.4|3.5|20.5|21.2|-5.8
NOP|14|4|10|49.1|115.9|40.1|86.2|46.5|9.4|28.7|32.8|26.3|32.1|82.0|10.6|30.5|41.1|24.3|16.1|9.9|5.3|5.6|24.6|23.9|-9.1
LAC|11|3|8|48.5|112.3|39.2|85.4|45.9|14.3|37.4|38.2|19.6|24.6|79.7|10.5|29.9|40.5|26.8|17.8|9.6|4.3|4.4|22.1|20.9|-5.3
BKN|12|3|9|48.4|110.2|37.1|83.9|44.2|14.6|40.7|35.9|21.4|28.3|75.8|11.6|31.0|42.6|24.2|17.7|8.6|4.8|4.8|26.1|24.0|-6.3
CHI|12|3|9|48.4|114.6|39.9|89.4|44.6|12.7|40.7|31.1|22.1|29.0|76.1|12.6|31.8|44.3|26.9|17.3|7.8|5.9|4.9|23.7|23.2|-11.3
SAC|12|1|11|48.0|108.2|39.3|86.3|45.5|12.3|35.5|34.5|17.4|22.7|76.8|9.8|30.1|39.9|25.0|17.1|7.8|3.5|5.8|22.8|19.6|-12.8
MIL|13|1|12|48.0|106.2|37.8|88.3|42.8|14.8|43.2|34.2|15.8|21.4|74.1|13.3|31.5|44.8|24.8|16.6|6.5|4.7|5.8|22.5|19.5|-14.1
UTA|13|1|12|48.8|107.5|37.8|86.8|43.5|12.1|36.5|33.1|19.8|25.8|77.0|12.0|32.5|44.5|24.0|16.7|6.7|6.2|5.4|24.0|24.2|-11.2
"""

# --------------------------------------------------------------------------- opponent
# Columns: tricode|GP|W|L|MIN|OppFGM|OppFGA|OppFG%|Opp3PM|Opp3PA|Opp3P%|OppFTM|OppFTA|OppFT%|
#          OppOREB|OppDREB|OppREB|OppAST|OppTOV|OppSTL|OppBLK|OppBLKA|OppPF|OppPFD|OppPTS|+/-
_TEAM_OPP_RAW = """
LAL|13|11|2|48.0|38.9|85.7|45.4|15.2|40.5|37.4|21.2|28.1|75.6|13.5|27.5|41.0|27.4|18.5|9.9|4.2|6.2|24.2|23.4|114.2|-7.9
SAS|13|11|2|48.4|38.7|89.2|43.4|12.5|33.0|37.8|16.4|20.2|81.3|10.9|31.9|42.8|24.9|14.5|6.5|4.9|7.3|21.2|20.0|106.2|-13.2
BOS|12|10|2|48.4|35.6|84.9|41.9|14.6|43.2|33.8|17.3|22.8|75.9|12.8|30.5|43.3|25.1|16.7|7.1|4.2|4.9|22.9|21.5|103.1|-11.2
HOU|13|10|3|48.0|39.6|87.3|45.4|12.3|38.5|31.9|15.8|21.5|73.6|12.1|28.6|40.7|23.4|15.3|8.2|4.1|6.1|21.9|19.9|107.4|-8.8
PHI|13|10|3|48.0|39.5|87.2|45.2|12.3|36.8|33.5|18.2|24.2|75.2|11.2|35.2|46.5|24.8|15.2|6.6|5.8|4.3|20.8|20.6|109.4|-1.8
MEM|13|9|4|48.4|40.5|90.0|45.0|12.4|37.5|33.0|18.2|24.2|75.5|12.0|29.7|41.7|25.0|14.2|7.7|7.2|5.1|21.6|23.7|111.7|-8.9
MIN|13|9|4|48.4|38.6|89.0|43.4|11.5|35.3|32.5|18.1|23.3|77.6|12.3|31.0|43.3|24.6|16.8|7.9|6.4|5.1|22.8|22.0|106.8|-11.5
POR|12|9|3|48.0|38.8|87.1|44.5|11.4|35.3|32.3|22.9|27.6|83.1|11.5|29.8|41.3|23.5|14.0|8.7|4.2|5.1|24.4|22.3|111.8|-7.8
DET|12|8|4|48.8|38.6|87.3|44.2|12.2|36.5|33.3|20.9|26.8|78.0|13.0|32.8|45.8|23.6|17.7|8.0|6.1|6.4|22.7|23.8|110.3|-5.4
GSW|13|8|5|48.4|40.6|88.2|46.1|12.8|37.8|34.0|18.3|23.4|78.3|12.2|30.7|42.8|27.3|16.3|8.7|5.7|5.4|22.2|21.9|112.4|-4.3
OKC|13|8|5|48.0|37.3|89.5|41.7|14.8|43.6|34.0|17.9|22.1|81.2|12.2|31.7|43.9|24.5|14.3|6.3|5.3|5.4|21.0|19.3|107.4|-3.8
ATL|13|7|6|48.4|42.2|86.5|48.7|12.2|35.5|34.2|20.4|25.7|79.3|11.2|34.5|45.6|28.2|18.8|9.8|6.0|4.0|19.4|22.1|116.8|-1.3
CLE|14|7|7|48.4|41.6|92.5|44.9|14.0|39.8|35.2|18.7|23.5|79.6|12.7|32.4|45.1|27.3|12.6|6.7|3.6|5.3|20.3|21.6|115.9|-1.6
DAL|13|7|6|48.0|41.6|88.7|46.9|12.2|36.6|33.2|17.9|23.9|74.9|12.2|31.2|43.5|27.2|15.8|8.2|4.8|5.5|20.9|22.3|113.3|-0.2
DEN|11|7|4|48.5|41.5|90.2|46.0|14.1|39.3|35.9|15.8|19.9|79.5|12.9|30.7|43.6|28.2|14.4|7.1|4.5|4.5|23.2|19.0|112.8|-1.8
MIA|13|7|6|48.4|43.1|89.5|48.1|15.8|40.8|38.9|17.8|23.1|77.3|11.4|33.7|45.1|29.7|16.7|8.1|5.2|5.5|25.1|21.1|119.8|1.2
NYK|12|6|6|48.0|36.9|85.4|43.2|13.6|39.8|34.2|16.3|22.3|72.8|10.5|30.2|40.7|24.8|13.2|6.7|6.2|4.1|21.1|20.9|103.7|-6.1
IND|13|5|8|48.0|40.5|89.6|45.2|13.8|39.0|35.5|18.5|23.6|78.2|11.9|35.3|47.2|26.0|15.1|8.6|4.4|4.3|22.7|20.3|113.2|2.1
ORL|12|5|7|48.4|39.8|85.3|46.6|13.6|35.8|38.0|19.7|25.9|75.9|10.3|31.3|41.6|27.3|15.2|9.4|5.0|4.1|23.3|22.8|112.8|4.4
PHX|11|5|6|48.0|40.4|86.8|46.5|14.4|38.4|37.4|21.0|27.4|76.7|14.2|32.7|46.9|26.2|17.4|7.5|4.7|4.5|18.6|22.0|116.1|4.4
TOR|12|5|7|48.0|38.4|80.5|47.7|12.7|34.3|36.9|23.3|28.8|80.9|10.5|31.0|41.5|25.8|19.0|8.1|5.5|4.4|24.3|25.8|112.8|-1.4
CHA|12|4|8|48.0|39.1|83.2|47.0|14.3|36.1|39.7|17.1|22.0|77.7|8.9|30.6|39.5|25.9|13.9|9.5|4.6|4.6|21.6|20.4|109.6|11.0
NOP|14|4|10|49.1|43.4|87.9|49.3|13.5|38.3|35.3|24.7|31.0|79.7|11.4|33.4|44.8|29.3|15.7|8.1|5.6|5.3|23.9|24.6|124.9|9.1
WAS|13|4|9|48.8|42.5|94.2|45.2|12.2|38.5|31.6|18.5|21.6|85.8|14.0|33.5|47.5|27.6|13.7|9.2|3.5|5.4|21.2|20.5|115.8|5.8
BKN|12|3|9|48.4|39.6|84.6|46.8|14.2|39.7|35.7|23.1|29.2|79.1|10.7|30.4|41.1|27.3|16.3|8.4|4.8|4.8|24.1|26.1|116.4|6.3
CHI|12|3|9|48.4|45.2|94.8|47.7|13.7|37.6|36.4|21.9|28.7|76.5|14.0|33.5|47.5|29.3|14.3|9.8|4.9|5.9|23.2|23.7|125.9|11.3
LAC|11|3|8|48.5|43.3|87.6|49.4|12.7|34.7|36.6|18.3|25.1|72.8|11.6|31.9|43.5|27.0|16.1|9.0|4.4|4.3|20.9|22.1|117.5|5.3
MIL|13|1|12|48.0|42.9|92.8|46.2|14.8|42.1|35.3|19.5|25.0|78.2|14.6|33.8|48.5|28.2|13.1|9.8|5.8|4.7|19.5|22.5|120.2|14.1
SAC|12|1|11|48.0|41.9|85.3|49.1|14.0|37.6|37.3|23.1|29.0|79.6|10.2|33.4|43.6|26.5|14.7|8.8|5.8|3.5|19.7|22.9|120.9|12.8
UTA|13|1|12|48.8|39.7|87.8|45.2|12.6|35.6|35.4|26.6|32.2|82.6|11.3|34.6|45.9|22.8|13.9|8.8|5.4|6.2|24.2|24.0|118.6|11.2
"""

# --------------------------------------------------------------------------- advanced
# Columns: tricode|GP|W|L|MIN|OffRtg|DefRtg|NetRtg|AST%|AST/TO|ASTRatio|OREB%|DREB%|REB%|TOV%|
#          eFG%|TS%|PACE|PIE|POSS
_TEAM_ADV_RAW = """
LAL|13|11|2|624.0|121.6|113.6|8.0|58.7|1.46|17.6|33.2|64.3|49.6|16.8|58.7|63.2|100.50|54.2|1306
SAS|13|11|2|629.0|119.6|106.6|13.0|65.4|2.28|19.4|33.9|71.3|52.7|12.3|53.4|57.6|98.94|56.7|1298
BOS|12|10|2|581.0|117.4|105.6|11.7|67.5|1.83|19.1|32.7|67.5|50.4|15.1|54.8|58.5|96.62|55.9|1168
HOU|13|10|3|624.0|119.3|110.2|9.1|64.4|1.85|19.0|35.2|67.8|52.0|14.8|55.1|59.3|97.42|55.8|1266
PHI|13|10|3|624.0|111.0|109.5|1.5|65.8|2.04|18.6|28.0|70.8|49.3|12.7|51.6|55.9|100.04|50.9|1302
MEM|13|9|4|629.0|119.0|110.4|8.5|66.2|1.76|19.1|34.2|70.6|52.9|15.6|55.8|60.2|100.46|53.9|1318
MIN|13|9|4|629.0|116.0|104.5|11.5|59.9|1.63|17.8|35.4|69.5|52.7|15.6|55.5|57.9|101.27|55.2|1326
POR|12|9|3|576.0|118.8|111.1|7.7|63.7|1.55|17.9|33.3|70.2|52.4|16.2|56.3|60.9|100.67|53.3|1208
DET|12|8|4|586.0|114.1|109.2|4.9|67.6|1.94|19.2|29.8|66.6|48.4|14.1|53.9|58.0|99.48|53.7|1217
GSW|13|8|5|629.0|116.1|112.0|4.1|70.0|1.75|19.4|32.7|68.5|50.7|15.9|55.4|59.5|99.66|51.8|1307
OKC|13|8|5|624.0|112.7|109.0|3.7|55.5|1.72|16.6|31.9|68.5|50.8|13.5|51.4|55.4|98.58|53.3|1282
ATL|13|7|6|629.0|113.3|111.9|1.4|71.6|2.07|20.5|33.2|69.2|49.7|14.6|52.8|55.7|103.55|48.5|1356
CLE|14|7|7|677.0|116.9|115.4|1.6|64.8|2.01|19.1|29.1|68.1|49.4|13.4|55.8|59.1|99.72|51.2|1407
DAL|13|7|6|624.0|112.8|112.8|0.0|63.2|1.65|18.2|33.0|66.5|49.7|15.7|53.5|57.2|100.54|49.7|1308
DEN|11|7|4|533.0|116.0|114.7|1.3|66.9|2.07|19.7|30.2|67.7|49.8|13.5|55.0|59.2|97.67|52.9|1087
MIA|13|7|6|629.0|114.7|116.2|-1.5|70.9|2.07|20.1|30.3|70.1|49.8|13.9|54.5|58.1|102.49|50.0|1345
NYK|12|6|6|576.0|114.5|108.6|5.9|69.2|1.86|18.9|37.3|72.1|54.4|15.0|51.9|55.7|95.63|53.3|1150
IND|13|5|8|624.0|110.1|111.7|-1.5|68.0|1.85|19.5|24.9|67.7|47.0|14.7|53.5|57.1|101.15|49.6|1312
ORL|12|5|7|581.0|109.7|113.4|-3.7|67.7|1.55|18.5|31.7|70.2|50.7|17.0|52.8|56.6|98.23|47.6|1185
PHX|11|5|6|528.0|113.8|117.6|-3.8|65.9|1.95|19.5|29.1|61.3|45.2|14.2|54.4|57.4|98.45|48.1|1080
TOR|12|5|7|576.0|114.5|112.8|1.7|67.8|1.96|19.1|36.2|66.9|50.2|14.4|51.9|55.5|99.88|49.3|1197
CHA|12|4|8|576.0|101.9|113.1|-11.2|62.6|1.11|15.8|35.7|73.7|53.5|20.2|48.1|52.0|96.83|42.9|1161
NOP|14|4|10|687.0|111.3|120.0|-8.6|60.6|1.51|17.0|29.7|68.0|48.6|15.4|51.9|57.7|101.83|45.7|1457
WAS|13|4|9|634.0|108.7|114.3|-5.5|59.3|1.56|17.0|29.0|66.2|48.3|15.0|51.5|56.0|99.63|47.1|1315
BKN|12|3|9|581.0|109.8|116.0|-6.2|65.2|1.37|17.2|32.1|69.9|50.6|17.6|52.9|57.2|99.47|46.1|1204
CHI|12|3|9|581.0|109.4|120.3|-10.9|67.4|1.55|18.2|30.7|65.1|47.9|16.5|51.7|56.1|103.81|44.9|1257
LAC|11|3|8|533.0|110.7|115.8|-5.1|68.4|1.51|18.8|30.4|67.2|48.8|17.6|54.3|58.4|100.55|47.4|1116
MIL|13|1|12|624.0|105.7|120.0|-14.2|65.6|1.49|17.5|30.5|64.3|47.3|16.6|51.1|54.3|100.31|42.0|1305
SAC|12|1|11|576.0|107.3|119.5|-12.2|63.7|1.46|17.9|28.4|69.1|48.1|16.9|52.6|56.2|101.00|42.8|1210
UTA|13|1|12|634.0|105.0|116.4|-11.3|63.5|1.44|17.0|29.5|68.8|48.6|16.3|50.4|54.7|100.50|45.3|1330
"""


def _rows(raw: str, keys: tuple, numeric: tuple):
    out = {}
    for line in raw.strip().splitlines():
        f = line.strip().split("|")
        if len(f) != len(keys) + 1:
            raise ValueError(f"expected {len(keys) + 1} fields, got {len(f)}: {line!r}")
        tri = f[0]
        out[tri] = {k: (float(v) if k in numeric else v) for k, v in zip(keys, f[1:])}
    return out


STANDINGS = _rows(
    _STANDINGS_RAW,
    ("w", "l", "conf", "div", "home", "road", "neutral", "ot", "last10", "streak"),
    ("w", "l"),
)
TRAD = _rows(
    _TEAM_TRAD_RAW,
    ("gp", "w", "l", "min", "pts", "fgm", "fga", "fg_pct", "tpm", "tpa", "tp_pct", "ftm",
     "fta", "ft_pct", "oreb", "dreb", "reb", "ast", "tov", "stl", "blk", "blka", "pf",
     "pfd", "plus_minus"),
    ("gp", "w", "l", "min", "pts", "fgm", "fga", "fg_pct", "tpm", "tpa", "tp_pct", "ftm",
     "fta", "ft_pct", "oreb", "dreb", "reb", "ast", "tov", "stl", "blk", "blka", "pf",
     "pfd", "plus_minus"),
)
OPP = _rows(
    _TEAM_OPP_RAW,
    ("gp", "w", "l", "min", "opp_fgm", "opp_fga", "opp_fg_pct", "opp_tpm", "opp_tpa",
     "opp_tp_pct", "opp_ftm", "opp_fta", "opp_ft_pct", "opp_oreb", "opp_dreb", "opp_reb",
     "opp_ast", "opp_tov", "opp_stl", "opp_blk", "opp_blka", "opp_pf", "opp_pfd", "opp_pts",
     "plus_minus"),
    ("gp", "w", "l", "min", "opp_fgm", "opp_fga", "opp_fg_pct", "opp_tpm", "opp_tpa",
     "opp_tp_pct", "opp_ftm", "opp_fta", "opp_ft_pct", "opp_oreb", "opp_dreb", "opp_reb",
     "opp_ast", "opp_tov", "opp_stl", "opp_blk", "opp_blka", "opp_pf", "opp_pfd", "opp_pts",
     "plus_minus"),
)
ADV = _rows(
    _TEAM_ADV_RAW,
    ("gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg", "ast_pct", "ast_to", "ast_ratio",
     "oreb_pct", "dreb_pct", "reb_pct", "tov_pct", "efg_pct", "ts_pct", "pace", "pie", "poss"),
    ("gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg", "ast_pct", "ast_to", "ast_ratio",
     "oreb_pct", "dreb_pct", "reb_pct", "tov_pct", "efg_pct", "ts_pct", "pace", "pie", "poss"),
)

# --------------------------------------------------------------------------- schedule
# 2026-11-14 .. 2026-11-17 from nba.com/schedule. 2026-11-14 rows are FINAL (they are also in
# FINALS). Order is (date, time_et, away, home, game_id, arena, city).
SCHEDULE = [
    # ---- 2026-11-14 (final)
    ("2026-11-14", "19:00", "DEN", "NOP", "0022600231", "Smoothie King Center", "New Orleans, LA"),
    ("2026-11-14", "19:30", "DAL", "CLE", "0022600232", "Rocket Arena", "Cleveland, OH"),
    ("2026-11-14", "20:00", "DET", "MIA", "0022600233", "Kaseya Center", "Miami, FL"),
    ("2026-11-14", "20:00", "BKN", "MEM", "0022600234", "FedExForum", "Memphis, TN"),
    ("2026-11-14", "20:00", "CHI", "MIN", "0022600235", "Target Center", "Minneapolis, MN"),
    # ---- 2026-11-15
    ("2026-11-15", "13:00", "IND", "PHI", "0022600236", "Xfinity Mobile Arena", "Philadelphia, PA"),
    ("2026-11-15", "16:00", "LAL", "PHX", "0022600237", "Mortgage Matchup Center", "Phoenix, AZ"),
    ("2026-11-15", "16:30", "CHA", "LAC", "0022600238", "Intuit Dome", "Inglewood, CA"),
    ("2026-11-15", "17:00", "SAS", "UTA", "0022600239", "Delta Center", "Salt Lake City, UT"),
    ("2026-11-15", "18:00", "DAL", "BOS", "0022600240", "TD Garden", "Boston, MA"),
    ("2026-11-15", "18:00", "NYK", "TOR", "0022600241", "Scotiabank Arena", "Toronto, ON"),
    ("2026-11-15", "19:00", "HOU", "WAS", "0022600242", "Capital One Arena", "Washington, DC"),
    ("2026-11-15", "20:00", "ATL", "MIL", "0022600243", "Fiserv Forum", "Milwaukee, WI"),
    ("2026-11-15", "21:00", "OKC", "SAC", "0022600244", "Golden 1 Center", "Sacramento, CA"),
    # ---- 2026-11-16
    ("2026-11-16", "19:00", "ORL", "BOS", "0022600245", "TD Garden", "Boston, MA"),
    ("2026-11-16", "19:00", "CHI", "CLE", "0022600246", "Rocket Arena", "Cleveland, OH"),
    ("2026-11-16", "19:00", "MEM", "WAS", "0022600247", "Capital One Arena", "Washington, DC"),
    ("2026-11-16", "19:30", "PHI", "BKN", "0022600248", "Barclays Center", "Brooklyn, NY"),
    ("2026-11-16", "19:30", "HOU", "MIA", "0022600249", "Kaseya Center", "Miami, FL"),
    ("2026-11-16", "20:00", "POR", "MIN", "0022600250", "Target Center", "Minneapolis, MN"),
    ("2026-11-16", "20:00", "GSW", "NOP", "0022600251", "Smoothie King Center", "New Orleans, LA"),
    ("2026-11-16", "21:00", "PHX", "DEN", "0022600252", "Ball Arena", "Denver, CO"),
    # ---- 2026-11-17
    ("2026-11-17", "19:30", "NYK", "TOR", "0022600253", "Scotiabank Arena", "Toronto, ON"),
    ("2026-11-17", "20:00", "POR", "MIN", "0022600254", "Target Center", "Minneapolis, MN"),
    ("2026-11-17", "20:00", "DET", "SAS", "0022600255", "Frost Bank Center", "San Antonio, TX"),
    ("2026-11-17", "22:30", "UTA", "LAC", "0022600257", "Intuit Dome", "Inglewood, CA"),
    ("2026-11-17", "23:00", "CHA", "LAL", "0022600256", "Crypto.com Arena", "Los Angeles, CA"),
]

# Per-date official game counts from the nba.com/games date strip, used as a completeness
# check against SCHEDULE. Read 2026-11-15.
GAMES_PER_DATE_OFFICIAL = {
    "2026-11-14": 5, "2026-11-15": 9, "2026-11-16": 8, "2026-11-17": 5,
}

# --------------------------------------------------------------------------- finals
# The 2026-11-14 finals, with per-quarter scores read from each game page's LINESCORES block.
# (game_id, date, away, home, away_pts, home_pts, away_q, home_q, ot, arena)
# away_q / home_q are [Q1, Q2, Q3, Q4] exactly as printed; they must sum to the final score
# (checked in nba2/v3/integrity.py, which refuses a row that does not add up).
FINALS = [
    ("0022600231", "2026-11-14", "DEN", "NOP", 116, 108, [29, 27, 30, 30], [23, 28, 31, 26], False,
     "Smoothie King Center"),
    ("0022600232", "2026-11-14", "DAL", "CLE", 117, 127, [33, 20, 38, 26], [33, 38, 34, 22], False,
     "Rocket Arena"),
    ("0022600233", "2026-11-14", "DET", "MIA", 117, 137, [39, 21, 26, 31], [37, 31, 35, 34], False,
     "Kaseya Center"),
    ("0022600234", "2026-11-14", "BKN", "MEM", 110, 129, [23, 31, 30, 26], [38, 33, 32, 26], False,
     "FedExForum"),
    ("0022600235", "2026-11-14", "CHI", "MIN", 117, 106, [29, 29, 30, 29], [17, 28, 35, 26], False,
     "Target Center"),
]

# The four finals whose LINESCORES block was NOT read. Blank by policy, with the reason the
# site prints next to the empty cell.
FINALS_QUARTERS_BLOCKED_REASON = (
    "BLOCKED input 'quarter_scores_all_dates': LINESCORES is rendered per game page, and this "
    "capture read all five 2026-11-14 game pages. Earlier dates in the results feed therefore "
    "carry a final score but no quarters; those cells are blank, never estimated."
)

# --------------------------------------------------------------------------- box score
# https://www.nba.com/game/den-vs-nop-0022600231/box-score, read 2026-11-15.
# One game, both teams. (player, team, min_raw, min_dec, pts, reb, ast, starter)
# min_raw is the string exactly as printed (MM:SS); min_dec is MM + SS/60 for arithmetic.
BOXSCORE = {
    "game_id": "0022600231",
    "date": "2026-11-14",
    "away": "DEN",
    "home": "NOP",
    "players": [
        ("Cameron Johnson", "DEN", "30:46", 30.767, 14, 5, 2, True),
        ("Aaron Gordon", "DEN", "32:32", 32.533, 15, 5, 5, True),
        ("Nikola Jokic", "DEN", "37:08", 37.133, 26, 8, 10, True),
        ("Christian Braun", "DEN", "27:46", 27.767, 17, 7, 1, True),
        ("Jamal Murray", "DEN", "37:57", 37.950, 23, 7, 9, True),
        ("Trevon Brazile", "DEN", "15:37", 15.617, 5, 3, 0, False),
        ("Spencer Jones", "DEN", "11:30", 11.500, 4, 2, 0, False),
        ("DeMar DeRozan", "DEN", "23:49", 23.817, 9, 3, 2, False),
        ("Tyus Jones", "DEN", "9:49", 9.817, 2, 0, 0, False),
        ("Marvin Bagley III", "DEN", "13:06", 13.100, 7, 7, 0, False),
        ("Saddiq Bey", "NOP", "40:33", 40.550, 16, 6, 4, True),
        ("Zion Williamson", "NOP", "30:46", 30.767, 24, 6, 2, True),
    ],
    "dnp": [("Alpha Diallo", "DEN"), ("Bryce Hopkins", "DEN"), ("Zeke Nnaji", "DEN")],
    "note": (
        "Only the players above were transcribed from the rendered box score. The rest of the "
        "NOP roster is present on the page but was not transcribed in this capture, so it is "
        "absent here rather than approximated. DNP rows carry no stat line by definition."
    ),
}

# --------------------------------------------------------------------------- players
# nba.com/stats/players/traditional (per-game), read 2026-11-15. Only the rows actually read
# are present; the page is paginated and this capture read the visible first page plus the
# specific players named in the injury report.
# (player, team, gp, min, pts, reb, ast)
PLAYERS_SEASON = [
    ("Nikola Jokic", "DEN", 11, 36.4, 23.7, 10.5, 9.1),
    ("Donovan Mitchell", "CLE", 13, 33.0, 23.0, None, None),
    ("Scottie Barnes", "TOR", 8, 33.3, 23.5, 7.6, 5.1),
    ("Alperen Sengun", "HOU", 11, 35.2, 23.1, 9.6, 7.6),
    ("Deni Avdija", "POR", 12, 32.7, 23.9, 6.1, 6.3),
    ("Cooper Flagg", "DAL", 12, 33.9, 24.1, 7.0, 6.4),
    ("Franz Wagner", "ORL", 12, 36.8, 24.4, 6.8, 8.3),
    ("Paolo Banchero", "ORL", 2, 33.8, 24.5, 6.5, 7.5),
    ("Luka Doncic", "LAL", None, 35.4, 36.8, 3.3, 4.7),
]
PLAYERS_SEASON_SOURCE = "https://www.nba.com/stats/players/traditional"
PLAYERS_SEASON_NOTE = (
    "Per-game season averages as printed on the players/traditional page. Blank cells are "
    "values that were not legible in the fetched chunk; they are blank here, not carried over "
    "from another row."
)

# --------------------------------------------------------------------------- injuries
# Transcribed verbatim from the official 11/15/26 06:15 AM ET PDF. The report's columns are
# Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason.
# The PDF paginates so that a team block can continue onto the next page with the Team cell
# blank; where that happened the team is carried from the block header and the row is marked
# "C" in the last field. "E" = the team cell is printed on the row itself.
# (date, time_et, matchup, team, player, status, reason, attribution)
INJURIES = [
    ("2026-11-15", "13:00", "IND@PHI", "Indiana Pacers", "Furphy, Johnny", "Out", "Injury/Illness - Right ACL Repair / Surgery", "E"),
    ("2026-11-15", "13:00", "IND@PHI", "Indiana Pacers", "Haliburton, Tyrese", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("2026-11-15", "13:00", "IND@PHI", "Indiana Pacers", "McConnell, T.J.", "Probable", "Injury/Illness - Right Hamstring Strain", "E"),
    ("2026-11-15", "13:00", "IND@PHI", "Indiana Pacers", "Nembhard, Andrew", "Questionable", "Injury/Illness - Left Hip Soreness / Tightness", "E"),
    ("2026-11-15", "13:00", "IND@PHI", "Indiana Pacers", "Nesmith, Aaron", "Questionable", "Injury/Illness - Left Hand Sprain", "E"),
    ("2026-11-15", "13:00", "IND@PHI", "Indiana Pacers", "Sheppard, Ben", "Out", "Injury/Illness - Left Meniscus Tear", "E"),
    ("2026-11-15", "13:00", "IND@PHI", "Philadelphia 76ers", "Barlow, Dominick", "Out", "Injury/Illness - Low Back Stress Reaction", "E"),
    ("2026-11-15", "13:00", "IND@PHI", "Philadelphia 76ers", "Bona, Adem", "Out", "Injury/Illness - Cervical Spine Sprain", "E"),
    ("2026-11-15", "13:00", "IND@PHI", "Philadelphia 76ers", "Embid, Joel", "Out", "Injury/Illness - Right Foot Plantar Fascia Injury Management", "E"),
    ("2026-11-15", "13:00", "IND@PHI", "Philadelphia 76ers", "Hukporti, Ariel", "Out", "Injury/Illness - Right Achilles Tendon Rupture / Tear", "E"),
    ("2026-11-15", "16:00", "LAL@PHX", "Los Angeles Lakers", "Carr, Cameron", "Out", "Injury/Illness - Illness", "E"),
    ("2026-11-15", "16:00", "LAL@PHX", "Los Angeles Lakers", "Grimes, Quentin", "Available", "Injury/Illness - Right Finger Splint", "E"),
    ("2026-11-15", "16:00", "LAL@PHX", "Los Angeles Lakers", "James, Bronny", "Questionable", "Injury/Illness - Illness", "E"),
    ("2026-11-15", "16:00", "LAL@PHX", "Los Angeles Lakers", "Reaves, Austin", "Out", "Injury/Illness - Left Heel Contusion / Bone Bruise", "E"),
    ("2026-11-15", "16:00", "LAL@PHX", "Phoenix Suns", "Sexton, Collin", "Questionable", "Injury/Illness - Right Orbital Laceration", "C"),
    ("2026-11-15", "16:00", "LAL@PHX", "Phoenix Suns", "Thiero, Adou", "Questionable", "Injury/Illness - Left Ankle Sprain", "C"),
    ("2026-11-15", "16:00", "LAL@PHX", "Phoenix Suns", "Williams, Mark", "Out", "Injury/Illness - Left Shoulder Surgery", "E"),
    ("2026-11-15", "16:30", "CHA@LAC", "Charlotte Hornets", "Ajayi, Michael", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "16:30", "CHA@LAC", "Charlotte Hornets", "Boswell, Kylan", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "16:30", "CHA@LAC", "Charlotte Hornets", "Knueppel, Kon", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("2026-11-15", "16:30", "CHA@LAC", "Charlotte Hornets", "Schroder, Dennis", "Out", "Injury/Illness - Left Hamstring Strain", "E"),
    ("2026-11-15", "16:30", "CHA@LAC", "Charlotte Hornets", "Steinbach, Hannes", "Out", "G League - On Assignment", "E"),
    ("2026-11-15", "16:30", "CHA@LAC", "LA Clippers", "Beal, Bradley", "Out", "Injury/Illness - Right Knee Injury Management", "E"),
    ("2026-11-15", "16:30", "CHA@LAC", "LA Clippers", "Ingram, Brandon", "Out", "Injury/Illness - Right Heel Surgery", "E"),
    ("2026-11-15", "16:30", "CHA@LAC", "LA Clippers", "Miller, Jordan", "Out", "Injury/Illness - Left Rotator Cuff Surgery", "E"),
    ("2026-11-15", "16:30", "CHA@LAC", "LA Clippers", "Niederhauser, Yanic Konan", "Out", "Injury/Illness - Right Lisfranc Surgery", "E"),
    ("2026-11-15", "17:00", "SAS@UTA", "San Antonio Spurs", "Brown, Maliq", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "17:00", "SAS@UTA", "San Antonio Spurs", "Gillespie, Ja'Kobi", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "17:00", "SAS@UTA", "San Antonio Spurs", "Harris, Tobias", "Out", "Injury/Illness - Left Calf Strain", "E"),
    ("2026-11-15", "17:00", "SAS@UTA", "San Antonio Spurs", "Quaintance, Jayden", "Out", "Injury/Illness - Right Knee Surgery", "E"),
    ("2026-11-15", "17:00", "SAS@UTA", "Utah Jazz", "Alexander, Trey", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "17:00", "SAS@UTA", "Utah Jazz", "Bufkin, Kobe", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "17:00", "SAS@UTA", "Utah Jazz", "Hayes, Jaxson", "Out", "Injury/Illness - Left Knee Strain", "C"),
    ("2026-11-15", "17:00", "SAS@UTA", "Utah Jazz", "Ingram, Harrison", "Out", "G League - Two-Way", "C"),
    ("2026-11-15", "17:00", "SAS@UTA", "Utah Jazz", "Jackson Jr., Jaren", "Out", "Injury/Illness - Right MCL Tear", "C"),
    ("2026-11-15", "17:00", "SAS@UTA", "Utah Jazz", "Markkanen, Lauri", "Out", "Injury/Illness - Right Hand Fracture", "C"),
    ("2026-11-15", "17:00", "SAS@UTA", "Utah Jazz", "Nurkic, Jusuf", "Out", "Injury/Illness - Right 2nd Plantar Plate Tear", "C"),
    ("2026-11-15", "18:00", "DAL@BOS", "Boston Celtics", "Carter, Devin", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-15", "18:00", "DAL@BOS", "Boston Celtics", "Cenac Jr., Christopher", "Questionable", "G League - On Assignment", "E"),
    ("2026-11-15", "18:00", "DAL@BOS", "Boston Celtics", "Mitchell, Dillon", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-15", "18:00", "DAL@BOS", "Boston Celtics", "Williams, Amari", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-15", "18:00", "NYK@TOR", "Toronto Raptors", "Barnes, Scottie", "Questionable", "Injury/Illness - Left Groin Strain", "E"),
    ("2026-11-15", "18:00", "NYK@TOR", "Toronto Raptors", "Bittle, Nate", "Out", "Injury/Illness - Right Foot Avulsion Fracture", "E"),
    ("2026-11-15", "18:00", "NYK@TOR", "Toronto Raptors", "Leonard, Kawhi", "Out", "Injury/Illness - Left Knee Injury Management", "E"),
    ("2026-11-15", "18:00", "NYK@TOR", "Toronto Raptors", "McCullar Jr., Kevin", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "18:00", "NYK@TOR", "Toronto Raptors", "Smith, Malachi", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "19:00", "HOU@WAS", "Houston Rockets", "Adams, Steven", "Probable", "Injury/Illness - Right Soleus Strain", "E"),
    ("2026-11-15", "19:00", "HOU@WAS", "Houston Rockets", "Capela, Clint", "Out", "Injury/Illness - Right Ankle Sprain", "E"),
    ("2026-11-15", "19:00", "HOU@WAS", "Houston Rockets", "Copeland, Quadir", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "19:00", "HOU@WAS", "Houston Rockets", "Phillips, Julian", "Out", "G League - Two-Way", "C"),
    ("2026-11-15", "19:00", "HOU@WAS", "Houston Rockets", "Smart, Marcus", "Out", "League Suspension", "C"),
    ("2026-11-15", "19:00", "HOU@WAS", "Houston Rockets", "VanVleet, Fred", "Out", "Injury/Illness - Right Knee Injury Management", "C"),
    ("2026-11-15", "19:00", "HOU@WAS", "Washington Wizards", "Beekman, Reece", "Out", "Injury/Illness - Right AC Joint Injury", "E"),
    ("2026-11-15", "19:00", "HOU@WAS", "Washington Wizards", "Carrington, Bub", "Questionable", "Injury/Illness - Chest / Sternum Contusion", "E"),
    ("2026-11-15", "19:00", "HOU@WAS", "Washington Wizards", "Champagne, Justin", "Out", "Injury/Illness - Right Foot Surgery", "E"),
    ("2026-11-15", "19:00", "HOU@WAS", "Washington Wizards", "Johnson, Tre", "Questionable", "Injury/Illness - Low Back Soreness", "E"),
    ("2026-11-15", "19:00", "HOU@WAS", "Washington Wizards", "Okpara, Felix", "Questionable", "G League - Two-Way", "E"),
    ("2026-11-15", "19:00", "HOU@WAS", "Washington Wizards", "Sarr, Alex", "Questionable", "Injury/Illness - Illness", "E"),
    ("2026-11-15", "19:00", "HOU@WAS", "Washington Wizards", "Vukcevic, Tristan", "Out", "Injury/Illness - Left Hip Impingement", "E"),
    ("2026-11-15", "19:00", "HOU@WAS", "Washington Wizards", "Watkins, Jamir", "Out", "Injury/Illness - Left ACL Repair / Surgery", "E"),
    ("2026-11-15", "20:00", "ATL@MIL", "Atlanta Hawks", "Flemings, Kingston", "Out", "Injury/Illness - Lumbar Strain", "E"),
    ("2026-11-15", "20:00", "ATL@MIL", "Atlanta Hawks", "Gilbert, Keshon", "Out", "Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure", "E"),
    ("2026-11-15", "20:00", "ATL@MIL", "Atlanta Hawks", "Gueye, Mouhamed", "Out", "Injury/Illness - Left Foot Fracture", "E"),
    ("2026-11-15", "20:00", "ATL@MIL", "Atlanta Hawks", "Landale, Jock", "Available", "Injury/Illness - Face Mask", "E"),
    ("2026-11-15", "20:00", "ATL@MIL", "Atlanta Hawks", "Newell, Asa", "Out", "Injury/Illness - Left Great Toe Hyperextension", "E"),
    ("2026-11-15", "20:00", "ATL@MIL", "Atlanta Hawks", "Veesaar, Henri", "Out", "Injury/Illness - Right ACL Tear", "C"),
    ("2026-11-15", "20:00", "ATL@MIL", "Atlanta Hawks", "Wilson, Jalen", "Doubtful", "G League - Two-Way", "C"),
    ("2026-11-15", "20:00", "ATL@MIL", "Milwaukee Bucks", "Dieng, Ousmane", "Out", "Injury/Illness - Left Finger Sprain", "E"),
    ("2026-11-15", "20:00", "ATL@MIL", "Milwaukee Bucks", "Jones, Kam", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "20:00", "ATL@MIL", "Milwaukee Bucks", "Markovic, Bogoljub", "Out", "G League - On Assignment", "E"),
    ("2026-11-15", "20:00", "ATL@MIL", "Milwaukee Bucks", "Nance, Pete", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "20:00", "ATL@MIL", "Milwaukee Bucks", "Ryan, Cormac", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "21:00", "OKC@SAC", "Oklahoma City Thunder", "Holmgren, Chet", "Out", "Injury/Illness - Right Knee/ Injury Recovery", "E"),
    ("2026-11-15", "21:00", "OKC@SAC", "Oklahoma City Thunder", "Mitchell, Ajay", "Questionable", "Injury/Illness - Left Ankle Sprain", "E"),
    ("2026-11-15", "21:00", "OKC@SAC", "Oklahoma City Thunder", "Sorber, Thomas", "Out", "Injury/Illness - Right Knee Surgery", "C"),
    ("2026-11-15", "21:00", "OKC@SAC", "Oklahoma City Thunder", "Wallace, Cason", "Out", "Injury/Illness - Left Shoulder Surgery", "C"),
    ("2026-11-15", "21:00", "OKC@SAC", "Oklahoma City Thunder", "Williams, Jalen", "Out", "Injury/Illness - Left Ankle Surgery", "C"),
    ("2026-11-15", "21:00", "OKC@SAC", "Oklahoma City Thunder", "Williams, Jaylin", "Out", "Injury/Illness - Low Back Spasms", "C"),
    ("2026-11-15", "21:00", "OKC@SAC", "Sacramento Kings", "Achiuwa, Precious", "Questionable", "Injury/Illness - Left Ankle Soreness", "E"),
    ("2026-11-15", "21:00", "OKC@SAC", "Sacramento Kings", "Mogbo, Jonathan", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "21:00", "OKC@SAC", "Sacramento Kings", "Murray, Keegan", "Questionable", "Injury/Illness - Illness", "E"),
    ("2026-11-15", "21:00", "OKC@SAC", "Sacramento Kings", "Pedulla, Sean", "Out", "G League - Two-Way", "E"),
    ("2026-11-15", "21:00", "OKC@SAC", "Sacramento Kings", "Raynaud, Maxime", "Out", "Injury/Illness - Right Patella Subluxation", "E"),
    ("2026-11-15", "20:00", "ATL@MIL", "Atlanta Hawks", "Simmons, Ben", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery", "C"),
]

# Club-rows the league printed as NOT YET SUBMITTED at the 06:15 AM ET release.
# (date, time_et, matchup, team)
INJ_NOT_SUBMITTED = [
    ("2026-11-15", "18:00", "DAL@BOS", "Dallas Mavericks"),
    # 11/16: every club printed NOT YET SUBMITTED at 06:15 AM ET on 11/15, because the
    # 5 p.m. local day-before deadline for a 11/16 game had not passed.
    ("2026-11-16", "19:00", "CHI@CLE", "Chicago Bulls"),
    ("2026-11-16", "19:00", "CHI@CLE", "Cleveland Cavaliers"),
    ("2026-11-16", "19:00", "MEM@WAS", "Memphis Grizzlies"),
    ("2026-11-16", "19:00", "MEM@WAS", "Washington Wizards"),
    ("2026-11-16", "19:00", "ORL@BOS", "Orlando Magic"),
    ("2026-11-16", "19:00", "ORL@BOS", "Boston Celtics"),
    ("2026-11-16", "19:30", "HOU@MIA", "Houston Rockets"),
    ("2026-11-16", "19:30", "HOU@MIA", "Miami Heat"),
    ("2026-11-16", "19:30", "PHI@BKN", "Philadelphia 76ers"),
    ("2026-11-16", "19:30", "PHI@BKN", "Brooklyn Nets"),
    ("2026-11-16", "20:00", "GSW@NOP", "Golden State Warriors"),
    ("2026-11-16", "20:00", "GSW@NOP", "New Orleans Pelicans"),
    ("2026-11-16", "20:00", "POR@MIN", "Portland Trail Blazers"),
    ("2026-11-16", "20:00", "POR@MIN", "Minnesota Timberwolves"),
    ("2026-11-16", "21:00", "PHX@DEN", "Phoenix Suns"),
    ("2026-11-16", "21:00", "PHX@DEN", "Denver Nuggets"),
]

# Revisions of the 11/15 report listed on the league's official index at capture time.
# The revision timestamp is the time printed in the PDF name; retrieval time is when this
# session read the index. Both are published on the injuries page banner.
INJURY_REVISIONS_2026_11_15 = [
    "00:00", "00:15", "00:30", "00:45", "01:00", "01:15", "01:30", "01:45", "02:00", "02:15",
    "02:30", "02:45", "03:00", "03:15", "03:30", "03:45", "04:00", "04:15", "04:30", "04:45",
    "05:00", "05:15", "05:30", "05:45", "06:00", "06:15",
]
INJURY_REVISION_CAPTURED = "06:15"
INJURY_INDEX_RETRIEVED_UTC = "2026-11-15T11:41:00Z"
INJURY_PDF_RETRIEVED_UTC = "2026-11-15T11:44:00Z"

# Filing deadlines, quoted from official.nba.com (the league's own words, condensed to the
# operative times; the verbatim sentence is published on the injuries page).
FILING_POLICY = {
    "day_before": "5 p.m. local time the day before a game (other than the second of a back-to-back)",
    "back_to_back_second": "1 p.m. local time on the day of the game",
    "game_day": "between 11 a.m. and 1 p.m. local time",
    "early_tip_override": "between 8 and 10 a.m. for tip-offs 5 p.m. or earlier",
    "updates": "Reports are updated on a continual basis throughout the day.",
    "url": "https://official.nba.com/nba-injury-report-2026-27-season/",
}

# --------------------------------------------------------------------------- arena table
# Arena coordinates. NOT an NBA document: coordinates are the published latitude/longitude of
# each arena, taken from the venue itself / the city it sits in, and used only for great-circle
# travel distance. Every row carries its own citation and is flagged on the site as
# third-party (not official). A missing coordinate is blank, and travel distance for that club
# is blank rather than estimated.
# (tricode, arena, city, lat, lon, source_url, source_label)
ARENAS = [
    ("ATL", "State Farm Arena", "Atlanta, GA", 33.7573, -84.3963, "https://www.statefarmarena.com/", "venue site (address)"),
    ("BKN", "Barclays Center", "Brooklyn, NY", 40.6826, -73.9754, "https://www.barclayscenter.com/", "venue site (address)"),
    ("BOS", "TD Garden", "Boston, MA", 42.3662, -71.0621, "https://www.tdgarden.com/", "venue site (address)"),
    ("CHA", "Spectrum Center", "Charlotte, NC", 35.2251, -80.8392, "https://www.spectrumcentercharlotte.com/", "venue site (address)"),
    ("CHI", "United Center", "Chicago, IL", 41.8807, -87.6742, "https://www.unitedcenter.com/", "venue site (address)"),
    ("CLE", "Rocket Arena", "Cleveland, OH", 41.4965, -81.6882, "https://www.rocketarena.com/", "venue site (address)"),
    ("DAL", "American Airlines Center", "Dallas, TX", 32.7905, -96.8103, "https://www.americanairlinescenter.com/", "venue site (address)"),
    ("DEN", "Ball Arena", "Denver, CO", 39.7487, -105.0077, "https://www.ballarena.com/", "venue site (address)"),
    ("DET", "Little Caesars Arena", "Detroit, MI", 42.3411, -83.0553, "https://www.313presents.com/", "venue site (address)"),
    ("GSW", "Chase Center", "San Francisco, CA", 37.7680, -122.3877, "https://www.chasecenter.com/", "venue site (address)"),
    ("HOU", "Toyota Center", "Houston, TX", 29.7508, -95.3621, "https://www.toyotacenter.com/", "venue site (address)"),
    ("IND", "Gainbridge Fieldhouse", "Indianapolis, IN", 39.7640, -86.1555, "https://www.gainbridgefieldhouse.com/", "venue site (address)"),
    ("LAC", "Intuit Dome", "Inglewood, CA", 33.9581, -118.3414, "https://www.intuitdome.com/", "venue site (address)"),
    ("LAL", "Crypto.com Arena", "Los Angeles, CA", 34.0430, -118.2673, "https://www.cryptoarena.com/", "venue site (address)"),
    ("MEM", "FedExForum", "Memphis, TN", 35.1385, -90.0506, "https://www.fedexforum.com/", "venue site (address)"),
    ("MIA", "Kaseya Center", "Miami, FL", 25.7814, -80.1870, "https://www.kaseyacenter.com/", "venue site (address)"),
    ("MIL", "Fiserv Forum", "Milwaukee, WI", 43.0451, -87.9174, "https://www.fiservforum.com/", "venue site (address)"),
    ("MIN", "Target Center", "Minneapolis, MN", 44.9795, -93.2761, "https://www.targetcenter.com/", "venue site (address)"),
    ("NOP", "Smoothie King Center", "New Orleans, LA", 29.9490, -90.0821, "https://www.smoothiekingcenter.com/", "venue site (address)"),
    ("NYK", "Madison Square Garden", "New York, NY", 40.7505, -73.9934, "https://www.msg.com/", "venue site (address)"),
    ("OKC", "Paycom Center", "Oklahoma City, OK", 35.4634, -97.5151, "https://www.paycomcenter.com/", "venue site (address)"),
    ("ORL", "Kia Center", "Orlando, FL", 28.5392, -81.3839, "https://www.kiacenter.com/", "venue site (address)"),
    ("PHI", "Xfinity Mobile Arena", "Philadelphia, PA", 39.9012, -75.1720, "https://www.wellsfargocenterphilly.com/", "venue site (address)"),
    ("PHX", "Mortgage Matchup Center", "Phoenix, AZ", 33.4457, -112.0712, "https://www.footprintcenter.com/", "venue site (address)"),
    ("POR", "Moda Center", "Portland, OR", 45.5316, -122.6668, "https://www.rosequarter.com/", "venue site (address)"),
    ("SAC", "Golden 1 Center", "Sacramento, CA", 38.5802, -121.4996, "https://www.golden1center.com/", "venue site (address)"),
    ("SAS", "Frost Bank Center", "San Antonio, TX", 29.4270, -98.4375, "https://www.frostbankcenter.com/", "venue site (address)"),
    ("TOR", "Scotiabank Arena", "Toronto, ON", 43.6435, -79.3791, "https://www.scotiabankarena.com/", "venue site (address)"),
    ("UTA", "Delta Center", "Salt Lake City, UT", 40.7683, -111.9011, "https://www.deltacenter.com/", "venue site (address)"),
    ("WAS", "Capital One Arena", "Washington, DC", 38.8981, -77.0209, "https://www.capitalonearena.com/", "venue site (address)"),
]
ARENA_SOURCE_NOTE = (
    "Coordinates are the published latitude/longitude of the venue, cited per row to the venue's "
    "own site. This is a third-party input, not an NBA document; the model uses it only for "
    "great-circle travel distance, and every distance row is flagged as third-party."
)

# --------------------------------------------------------------------------- window
WINDOW_START = "2026-11-15"
WINDOW_END = "2026-11-17"   # the brief's 3-day maximum, inclusive
RESULTS_START = "2026-11-14"


def path_game_ids():
    """Game ids for the pick window, in schedule order."""
    return [r[4] for r in SCHEDULE if WINDOW_START <= r[0] <= WINDOW_END]


def by_date():
    out: dict[str, list] = {}
    for r in SCHEDULE:
        out.setdefault(r[0], []).append(r)
    return out
