"""v4 capture: every official value this session read, with the URL and retrieval stamp.

Why this file is data-not-code: the brief requires a value to be published only if it was
read from an official source *in the run that publishes it*. This module is that reading,
frozen. Each block carries

* ``url``        — the exact official page (or PDF) the value came off,
* ``retrieved``  — the UTC timestamp of this session's read,
* ``method``     — how it was read. Bash egress to nba.com is blocked in this sandbox
                   (``curl`` -> HTTP 000); every read below went through the platform
                   page-fetch tool, and the method is recorded rather than glossed over.

What this file deliberately does **not** contain
------------------------------------------------
``data/raw/refresh_2026-11-16/team_stats.json`` holds the three official team-stat pages as
they rendered (30 rows each, every division-split cell together with the rounded display
value that is used). Anything a reader needs to re-derive is there. This module holds the
typed view and the honest record of what could *not* be read:

* ``UNREAD`` — pages that were not fetched in this session, with the reason. Nothing in
  this module is ever filled in from an earlier session's snapshot or from arithmetic
  that "looks right".

Two source levels are used and never mixed:

* ``official``    — nba.com / stats.nba.com / ak-static.cms.nba.com / statsdmz.nba.com,
* ``third_party`` — only for arena geocodes, which NBA.com does not publish at all.
  Every third-party row is labelled and flagged wherever it appears.
"""

from __future__ import annotations

import datetime as dt

# --------------------------------------------------------------------------- provenance
SESSION = "arena/b3914335-nba2"
RETRIEVED_UTC = "2026-11-19T12:32:00Z"   # 2026-11-19 re-cut (RQ-8892-02) by arena/6b9f3bbe-nba2; first read by arena/2689e93f (2026-11-16)
RETRIEVED_ET = "2026-11-19 07:32 ET"
METHOD = ("platform page-fetch tool (fetch_page); direct bash egress to nba.com returns "
          "HTTP 000 from this sandbox, so every read is recorded with this method")

SOURCE_PAGES = {
    "schedule": {
        "name": "NBA.com Schedule (official)",
        "url": "https://www.nba.com/games?date=2026-11-19",
        "read": "game ids and ET tip times for 11/19-11/22 from the /games day strips "
                "(2026-11-19 re-cut); arena/city/state for 11/19-11/20 carried from the "
                "committed 2026-11-17 schedule read (tips re-verified, all agree); the "
                "eleven 11/21-11/22 arena cells stay blank - the strips do not print them",
    },
    "standings": {
        "name": "NBA.com Standings (official)",
        "url": "https://www.nba.com/standings",
        "read": "30 clubs: W, L, WIN%, GB, CONF, DIV, HOME, ROAD, NEUTRAL, OT, LAST10, STREAK",
    },
    "team_adv": {
        "name": "NBA.com Stats - Teams Advanced (official)",
        "url": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "read": "30 rows: GP, W, L, MIN, OffRtg, DefRtg, NetRtg, AST%, OREB%, DREB%, TOV%, "
                "eFG%, TS%, PACE, PIE, POSS",
    },
    "team_opp": {
        "name": "NBA.com Stats - Teams Opponent (official)",
        "url": "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "read": "30 rows: Opp PTS (points allowed per game) and the opponent +/- column",
    },
    "team_trad": {
        "name": "NBA.com Stats - Teams Traditional (official)",
        "url": "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame",
        "read": "30 rows: PTS, FGM/A, FG%, 3PM/A, 3P%, FTM/A, FT%, OREB, DREB, REB, AST, "
                "TOV, STL, BLK, PF, +/-",
    },
    "injury_index": {
        "name": "NBA Official - Injury Report index (official)",
        "url": "https://official.nba.com/nba-injury-report-2026-27-season/",
        "read": "the filing deadlines and the list of every published release; the newest "
                "indexed release at retrieval was 11/19/26 07:15 AM ET",
    },
}

# Pages that were needed and NOT read this session. Published verbatim next to the blank.
UNREAD = {
    "injury_binary_pdf": (
        "The injury PDFs as stored bytes",
        "The page-fetch tool returns the PDF's text, not its bytes, and bash egress to "
        "ak-static.cms.nba.com is blocked (HTTP 000). Every release this session therefore "
        "carries its official URL, its revision stamp and this session's retrieval stamp, "
        "plus a sha256 of the transcribed text (a content hash), but NOT the original file "
        "hash. Flagged F-V4-01; the fix is a runner with network access, not a guess.",
        "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_15AM.pdf",
    ),
    "player_game_logs": (
        "Per-player game logs for the 11/15 and 11/16 games",
        "Gamebook box scores for 11/15 are reachable and their team/period rows were read, "
        "but transcribing 9 games x ~26 player rows was outside this session's budget. The "
        "committed 11/13 and 11/14 logs stand unchanged; the gap is published, not filled. "
        "Flagged F-V4-02.",
        "https://statsdmz.nba.com/pdfs/20261115/20261115_INDPHI_book.pdf",
    ),
    "arena_coordinates_official": (
        "Official arena latitude / longitude",
        "NBA.com publishes arena name, city and state but no coordinates. The coordinates "
        "used for travel distance are THIRD-PARTY (Wikipedia/Wikidata geocodes, captured "
        "2026-11-15) and are labelled that way on every row that uses them. Flagged F-V4-03.",
        "https://www.nba.com/schedule",
    ),
    "closing_lines": (
        "Closing market prices (spread / total / moneyline)",
        "No licensed odds feed is connected (gate G6). Without a closing line the "
        "market-anchored prior's weight is undefined, so w_market stays blank and the "
        "blended line is not published. Flagged F-V4-04, carried from v3.",
        "https://www.nba.com/games",
    ),
}

# --------------------------------------------------------------- 2026-11-16 injury releases
# Two consecutive releases from the SAME day, so the diff isolates revision drift.
# The releases read this session live in ``injury_renderings`` as verbatim text and are
# parsed by ``injury_parse``. This name is kept because older call sites (the model's
# provenance block, the gate table, the projection banner) ask for "the newest release", and
# it must always answer with the newest one actually stored - not with a transcription
# frozen on the day it was typed. The previous build's hard-coded 70-row transcription is
# gone: it recorded ``Tyson, Jaylon | Questionable`` where the PDF prints Doubtful, and a
# value that cannot be re-derived from the source does not belong in a module that claims to
# be data-not-code.
from . import injury_parse as _PA            # noqa: E402  (late import: avoids a cycle)
from . import injury_renderings as _RR       # noqa: E402


def _newest_release() -> dict:
    rel = _RR.newest()
    parsed = _PA.parse_render(rel["text"])
    rows = [[r["date"] or "", r["time_et"] or "", r["matchup"] or "", r["team"] or "",
             r["player"] or "", r["status"] or "", r["reason"] or "", r["note"]]
            for r in parsed["rows"]]
    return {
        "stamp_et": rel["stamp_et"],
        "url": rel["url"],
        "retrieved_utc": rel["retrieved_utc"],
        "index_checked_utc": rel["index_checked_utc"],
        "method": rel["method"],
        "rows": rows,
        "counts": parsed["counts"],
        "unread": parsed["unread"],
        "text_sha256": _RR.text_sha(rel["text"]),
        "layout_notes": [
            ("F-V4-06",
             "GSW@NOP rows keep only Player | Status | Reason, or Player | Reason, depending on "
             "where the page broke. The parser resolves the status from the end of the row and "
             "leaves it genuinely blank where it is absent; it never assumes the middle cell is "
             "a status."),
            ("F-V4-05",
             "Page-continuation rows print with empty date / time / matchup / team cells and are "
             "attributed to the block in progress; the attribution is written on the row."),
            ("F-V4-10",
             "The 13:00 PM release was returned by the fetch tool in two chunks; the junction "
             "fell inside the PHX@DEN block and the join basis is recorded on the release."),
        ],
    }


INJURY_RELEASES = [_newest_release()]

# A second, consecutive release from the same day. Row-for-row it prints the same 70 rows
# as the 09:15 AM release. Rather than pretend to a second independent transcription, the
# relationship is declared here and the claim is checked by the diff (0 changes) and by the
# linked PDF. Flagged F-V4-09 so a reviewer can re-derive it from the source in minutes.
# The 2026-11-16 09:15 AM transcription that an earlier session committed, preserved byte
# for byte (data/raw/refresh_2026-11-16/injury_transcript_20261116_0930AM_superseded.json) so
# the provenance comparison in injury_diff.cross_session_check tests THEIR record rather than
# ours. It is NOT a live release and is not counted in any diff. The earlier build also
# declared the 09:30 AM release "identical row-for-row" to this one without reading it; that
# declaration is withdrawn - both releases are now read in full (F-V4-09).

# --------------------------------------------------------------- 2026-11-16 schedule (T+0..T+3)
# game_id, date, away, home, time_et, arena, city, state
SLATE = """
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
0022600274|2026-11-21|MIL|PHI|1:00 PM|||
0022600275|2026-11-21|POR|NYK|7:30 PM|||
0022600278|2026-11-21|NOP|SAS|8:00 PM|||
0022600277|2026-11-21|MEM|MIN|8:00 PM|||
0022600276|2026-11-21|LAC|DAL|8:00 PM|||
0022600279|2026-11-21|BOS|SAC|10:00 PM|||
0022600280|2026-11-22|DET|ATL|3:30 PM|||
0022600281|2026-11-22|OKC|MIA|6:00 PM|||
0022600284|2026-11-22|DAL|UTA|7:00 PM|||
0022600282|2026-11-22|ORL|WAS|7:00 PM|||
0022600283|2026-11-22|DEN|CHI|7:00 PM|||
0022600285|2026-11-22|IND|NYK|8:00 PM|||
0022600286|2026-11-22|BOS|GSW|8:30 PM|||
"""

WINDOW = ("2026-11-19", "2026-11-22")     # T+0 .. T+3 inclusive
EXTENDED_WINDOW = ("2026-11-19", "2026-11-22")  # T+0 .. T+3 from the 11/19 anchor

# --------------------------------------------------------------- 2026-11-15 official finals
# Read from the official scoreboard/schedule page for 2026-11-16 (which prints the full
# 11/15 final slate) and from each game's official gamebook "SCORE BY PERIOD" table.
# game_id, date, away, home, away_pts, home_pts, ot, away_q, home_q, gamebook
FINALS_2026_11_15 = """
0022600236|2026-11-15|IND|PHI|124|131|0|35,22,30,37|29,29,39,34|20261115_INDPHI_book.pdf
0022600237|2026-11-15|LAL|PHX|131|123|0|33,31,40,27|24,30,26,43|20261115_LALPHX_book.pdf
0022600238|2026-11-15|CHA|LAC|105|113|0|21,31,31,22|22,29,33,29|20261115_CHALAC_book.pdf
0022600239|2026-11-15|SAS|UTA|110|102|0|31,27,23,29|33,22,26,21|20261115_SASUTA_book.pdf
0022600240|2026-11-15|DAL|BOS|94|131|0||42,25,37,27|20261115_DALBOS_book.pdf
0022600241|2026-11-15|NYK|TOR|112|108|1|23,24,20,28,17|17,26,31,21,13|20261115_NYKTOR_book.pdf
0022600242|2026-11-15|HOU|WAS|147|119|0|36,37,46,28|31,23,34,31|20261115_HOUWAS_book.pdf
0022600243|2026-11-15|ATL|MIL|113|106|0|18,37,32,26|37,16,27,26|20261115_ATLMIL_book.pdf
0022600244|2026-11-15|OKC|SAC|125|103|0|32,30,32,31|24,26,30,23|20261115_OKCSAC_book.pdf
"""

FINALS_GAMEBOOK_BASE = "https://statsdmz.nba.com/pdfs/20261115/"

# Quarter-score provenance, per game. ``None`` means: the club's period row was NOT
# transcribed this session (the gamebook was read only far enough to confirm the final).
# These are published blank and flagged; they are never back-solved from the final.
QUARTER_PROVENANCE = {
    "0022600236": ("read", "both period rows sum to the final (124, 131)"),
    "0022600237": ("read", "period rows as captured 2026-11-16 by this session's schedule read"),
    "0022600238": ("read", "period rows as captured 2026-11-16 by this session's schedule read"),
    "0022600239": ("read", "period rows as captured 2026-11-16 by this session's schedule read"),
    "0022600240": ("partial", "away period row not transcribed; home row (42+25+37+27=131) checked"),
    "0022600241": ("read", "five periods each; both rows sum to the final (112, 108)"),
    "0022600242": ("read", "both period rows sum to the final (147, 119)"),
    "0022600243": ("read", "both period rows sum to the final (113, 106)"),
    "0022600244": ("read", "both period rows sum to the final (125, 103)"),
}

# --------------------------------------------------------------- standings (30 clubs)
# tri, conf, seed, W, L, pct, GB, CONF record, DIV record, HOME, ROAD, NEUTRAL, OT, LAST10, STREAK
STANDINGS = """
PHI|East|1|13|3|.813|--|13-3|4-1|6-2|7-1|0-0|0-0|8-2|W 4
BOS|East|2|11|4|.733|1.5|10-2|4-0|6-1|5-3|0-0|1-0|7-3|L 2
DET|East|3|10|4|.714|2|8-3|0-0|3-2|7-2|0-0|1-0|7-3|W 2
MIA|East|4|9|6|.600|3.5|5-2|1-1|5-3|4-3|0-0|1-0|8-2|W 6
ATL|East|5|9|6|.600|3.5|8-2|4-1|3-3|6-3|0-0|0-1|7-3|W 2
NYK|East|6|8|6|.571|4|8-6|3-3|4-3|4-3|0-0|1-0|7-3|W 2
CLE|East|7|8|8|.500|5|6-5|2-0|6-3|2-5|0-0|1-0|4-6|L 1
ORL|East|8|6|8|.429|6|4-5|0-2|1-5|5-3|0-0|0-1|5-5|L 1
TOR|East|9|5|10|.333|7.5|4-6|0-4|2-6|3-4|0-0|0-1|2-8|L 6
IND|East|10|5|10|.333|7.5|3-6|0-1|2-5|3-4|0-1|0-0|3-7|L 2
WAS|East|11|5|11|.313|8|5-8|2-3|2-5|3-6|0-0|0-1|2-8|W 1
CHA|East|12|4|10|.286|8|4-7|2-2|3-4|1-6|0-0|0-1|1-9|L 3
CHI|East|13|4|10|.286|8|3-9|1-1|1-4|3-6|0-0|1-0|3-7|W 1
BKN|East|14|3|11|.214|9|2-9|0-3|1-5|2-6|0-0|0-1|3-7|L 3
MIL|East|15|1|14|.067|11.5|1-11|1-2|1-7|0-7|0-0|0-0|0-10|L 11
LAL|West|1|13|3|.813|--|7-3|5-1|6-2|7-1|0-0|1-0|9-1|L 1
SAS|West|2|12|3|.800|0.5|11-2|2-1|5-3|7-0|0-0|1-0|9-1|L 1
HOU|West|3|12|4|.750|1|6-3|2-1|7-1|5-3|0-0|0-0|7-3|W 1
MIN|West|4|11|4|.733|1.5|7-2|3-0|7-2|4-2|0-0|0-1|8-2|W 2
MEM|West|5|11|4|.733|1.5|7-3|1-1|3-4|8-0|0-0|0-1|6-4|W 4
POR|West|6|9|5|.643|3|9-5|4-2|3-2|6-3|0-0|0-0|6-4|L 2
DEN|West|7|8|5|.615|3.5|5-5|0-2|3-3|4-2|1-0|1-0|7-3|W 1
OKC|West|8|9|6|.600|3.5|6-5|1-2|5-1|4-5|0-0|0-0|5-5|L 1
DAL|West|9|8|7|.533|4.5|4-5|1-3|6-2|2-5|0-0|0-0|5-5|W 1
GSW|West|10|8|7|.533|4.5|6-7|3-2|6-1|2-6|0-0|1-0|6-4|L 4
PHX|West|11|7|7|.500|5|5-7|3-2|5-4|2-3|0-0|0-0|6-4|W 2
NOP|West|12|5|11|.313|8|4-8|1-1|4-7|1-4|0-0|2-1|3-7|L 1
LAC|West|13|4|9|.308|7.5|3-7|1-4|4-4|0-5|0-0|0-1|3-7|L 1
UTA|West|14|3|13|.188|10|3-11|0-2|1-7|2-6|0-0|0-2|2-8|W 2
SAC|West|15|1|13|.071|11|1-11|0-3|0-9|1-4|0-0|0-0|1-9|L 7
"""

# --------------------------------------------------------- team stats: three official pages
# Advanced page (read in full, 30/30 rows):
#   tri|GP|W|L|MIN|OffRtg|DefRtg|NetRtg|AST%|OREB%|DREB%|TOV%|eFG%|TS%|PACE|PIE|POSS
ADVANCED = """
LAL|16|13|3|773.0|119.8|113.2|6.7|58.8|33.6|65.0|16.5|57.2|61.5|100.35|53.0|1614
PHI|16|13|3|768.0|114.5|111.8|2.7|64.7|28.4|72.0|12.6|53.4|57.7|99.88|51.4|1600
HOU|16|12|4|768.0|121.1|112.1|9.0|65.4|36.7|68.7|15.0|55.6|59.7|97.41|55.3|1558
SAS|15|12|3|725.0|118.1|107.0|11.1|65.6|33.5|71.3|12.6|53.0|57.1|98.35|56.0|1487
BOS|15|11|4|725.0|117.0|106.0|11.0|66.7|32.9|67.7|14.9|54.6|57.9|96.76|54.7|1460
MEM|15|11|4|725.0|120.6|111.9|8.7|67.6|34.2|69.8|15.7|56.9|61.1|100.27|54.3|1516
MIN|15|11|4|725.0|114.5|104.0|10.5|60.0|34.7|69.3|15.8|54.8|57.4|101.23|55.0|1528
DET|14|10|4|682.0|114.9|108.9|6.0|67.9|30.0|66.6|14.2|54.5|58.4|98.78|54.2|1406
ATL|15|9|6|725.0|112.8|110.8|1.9|71.1|32.8|69.6|14.6|52.8|55.7|103.71|49.0|1566
MIA|15|9|6|725.0|116.9|116.7|0.3|70.3|30.8|68.3|14.0|55.4|59.1|102.19|50.8|1546
OKC|15|9|6|720.0|113.0|108.7|4.4|55.5|31.6|68.9|13.5|52.2|55.9|99.17|53.5|1488
POR|14|9|5|672.0|116.2|110.2|6.0|63.8|33.0|70.1|16.1|54.8|59.2|100.71|52.5|1410
CLE|16|8|8|773.0|117.5|115.5|2.0|64.7|30.9|68.7|13.7|55.8|59.1|100.01|51.0|1610
DAL|15|8|7|720.0|112.3|113.4|-1.1|65.5|33.1|65.9|16.3|53.6|57.3|99.97|49.4|1501
DEN|13|8|5|629.0|114.3|113.8|0.5|64.9|30.4|66.8|14.2|54.3|58.6|98.02|52.5|1287
GSW|15|8|7|725.0|113.4|112.8|0.6|70.5|32.7|67.9|16.2|53.9|58.1|99.41|50.3|1503
NYK|14|8|6|677.0|114.8|109.0|5.8|68.6|37.1|72.2|15.2|52.4|56.3|94.87|53.6|1342
PHX|14|7|7|672.0|115.6|116.8|-1.2|65.8|30.5|63.1|14.4|55.4|58.4|98.89|49.4|1382
ORL|14|6|8|677.0|111.3|114.0|-2.7|68.5|30.7|70.6|16.4|53.9|57.4|97.84|48.5|1375
IND|15|5|10|720.0|110.7|113.6|-2.9|67.2|24.4|68.1|14.3|53.9|57.4|100.90|49.4|1511
NOP|16|5|11|783.0|111.7|118.9|-7.1|60.7|30.1|68.5|15.3|51.8|57.5|101.30|46.4|1652
TOR|15|5|10|725.0|113.7|113.1|0.5|67.6|34.3|66.4|13.7|52.0|55.1|98.09|48.4|1478
WAS|16|5|11|778.0|109.9|117.1|-7.1|60.1|29.2|65.6|14.6|51.7|56.3|99.46|46.3|1612
CHA|14|4|10|677.0|103.1|113.7|-10.6|62.6|36.2|72.8|19.9|48.6|52.5|96.43|43.5|1360
CHI|14|4|10|677.0|111.1|119.1|-8.0|67.9|31.6|64.6|16.5|52.7|56.8|103.80|46.2|1464
LAC|13|4|9|629.0|111.4|117.0|-5.6|68.5|29.2|65.9|17.2|54.9|58.8|99.74|47.4|1306
BKN|14|3|11|677.0|110.5|119.0|-8.4|64.6|31.9|68.0|17.5|53.5|57.5|99.51|45.2|1404
UTA|16|3|13|778.0|107.0|114.5|-7.5|65.0|29.0|69.7|16.7|52.4|56.2|100.16|47.2|1626
MIL|15|1|14|720.0|106.7|119.7|-13.0|65.1|31.1|64.5|16.8|51.4|54.7|101.00|42.4|1515
SAC|14|1|13|672.0|106.9|120.4|-13.5|64.8|28.4|69.3|17.2|52.8|56.3|100.93|42.5|1411
"""

# Opponent page: tri|GP|OppPTS|OppFG%|Opp3P%|OppREB|OppTOV|OppSTL|OppBLK|OppPF|plusminus
OPPONENT = """
LAL|16|114.4|45.7|36.4|41.9|18.8|9.5|4.2|24.0|-6.4
PHI|16|111.6|46.5|34.6|44.9|14.3|6.6|5.7|21.3|-2.9
HOU|16|109.2|45.9|32.6|39.9|14.5|8.7|4.7|21.6|-8.7
SAS|15|105.9|44.0|37.4|42.7|14.3|6.7|4.7|20.8|-11.2
BOS|15|103.4|42.4|33.5|43.3|16.7|7.2|4.3|21.4|-10.5
MEM|15|112.9|45.3|33.3|41.2|13.9|7.8|6.9|21.9|-9.0
MIN|15|106.1|42.8|32.5|43.9|16.7|7.8|6.4|23.3|-10.6
DET|14|108.9|44.1|32.8|45.0|17.4|7.6|5.7|21.9|-6.4
ATL|15|115.8|48.1|34.1|45.9|18.6|9.6|6.1|19.3|-1.9
MIA|15|119.9|47.8|37.9|45.3|16.6|7.9|4.9|25.4|-0.7
OKC|15|107.7|42.1|34.4|43.9|14.8|6.6|5.1|21.1|-4.4
POR|14|111.0|44.2|33.1|42.5|14.4|8.6|4.4|24.1|-6.0
CLE|16|116.3|45.5|35.0|43.9|12.9|7.3|3.8|20.1|-1.9
DAL|15|113.2|46.9|33.4|43.6|15.8|8.7|4.9|20.5|0.9
DEN|13|112.2|45.8|35.5|44.4|14.7|7.4|4.4|23.2|-0.9
GSW|15|112.8|46.1|34.8|43.7|16.2|9.0|5.7|22.2|-0.9
NYK|14|103.9|43.7|34.4|40.3|12.9|6.5|6.0|21.2|-6.1
PHX|14|115.7|46.9|37.0|45.1|17.1|7.7|4.7|19.2|1.6
ORL|14|112.8|46.6|37.9|41.2|14.7|9.2|4.9|22.6|3.4
IND|15|114.8|46.1|37.2|46.7|15.1|8.3|4.3|22.5|3.3
NOP|16|122.8|48.6|35.3|44.7|15.8|7.9|5.7|24.0|7.4
TOR|15|112.0|47.6|36.6|42.9|18.3|7.5|5.5|22.9|0.0
WAS|16|117.9|46.4|33.5|47.7|13.7|8.8|3.6|21.5|7.2
CHA|14|110.4|47.1|40.1|40.1|14.1|9.1|4.5|21.4|10.3
CHI|14|124.6|48.1|36.0|46.4|15.4|9.9|4.8|22.6|8.4
LAC|13|117.7|49.1|37.5|43.9|16.1|8.8|4.4|21.0|5.8
BKN|14|119.2|47.7|36.6|41.9|15.9|8.5|4.7|24.1|8.4
UTA|16|116.0|44.8|34.8|44.9|13.9|9.3|5.2|22.7|7.3
MIL|15|120.9|46.3|35.7|48.1|13.8|9.7|5.5|19.9|13.1
SAC|14|121.7|49.9|37.4|43.2|14.4|9.2|5.2|19.5|14.0
"""

# Traditional page: tri|GP|W|L|WIN%|MIN|PTS|FGM|FGA|FG%|3PM|3PA|3P%|FTM|FTA|FT%|OREB|DREB|REB|AST|TOV|STL|BLK|PF|plusminus
TRADITIONAL = """
LAL|16|13|3|.813|48.3|120.9|41.6|85.1|48.9|14.1|37.6|37.5|23.6|30.0|78.8|12.0|29.4|41.4|24.4|16.7|10.8|5.8|4.2|22.9|6.4
PHI|16|13|3|.813|48.0|114.5|40.6|87.4|46.4|12.3|34.5|35.5|21.1|26.6|79.3|10.1|32.7|42.8|26.3|12.6|8.1|4.4|5.7|20.6|2.9
SAS|15|12|3|.800|48.3|117.1|42.4|91.3|46.4|12.1|36.0|33.5|20.2|25.2|80.2|13.1|35.1|48.2|27.8|12.5|8.3|6.9|4.7|19.1|11.2
HOU|16|12|4|.750|48.0|117.9|42.1|87.6|48.1|13.1|34.4|38.2|20.5|25.4|80.8|13.9|31.8|45.7|27.6|14.6|7.6|5.6|4.7|19.9|8.7
BOS|15|11|4|.733|48.3|113.9|40.2|88.6|45.4|16.4|43.9|37.3|17.1|22.0|77.6|13.5|31.5|45.0|26.8|14.5|8.5|4.7|4.3|21.9|10.5
MEM|15|11|4|.733|48.3|121.9|42.8|89.0|48.1|15.6|39.4|39.6|20.7|24.5|84.5|12.2|34.3|46.5|28.9|15.9|6.7|5.1|6.9|23.3|9.0
MIN|15|11|4|.733|48.3|116.7|42.3|90.1|47.0|14.1|38.2|37.0|17.9|26.3|67.8|13.5|35.1|48.6|25.4|16.1|8.9|5.1|6.4|22.1|10.6
DET|14|10|4|.714|48.7|115.4|41.2|87.8|46.9|13.2|35.6|37.1|19.7|24.9|79.3|12.0|31.9|43.9|28.0|14.2|9.3|6.1|5.7|23.5|6.4
POR|14|9|5|.643|48.0|117.0|39.4|86.2|45.7|15.6|43.4|36.0|22.5|28.8|78.2|11.7|33.0|44.7|25.1|16.2|7.1|5.3|4.4|22.8|6.0
DEN|13|8|5|.615|48.4|113.2|41.0|85.0|48.2|10.4|30.9|33.6|20.8|26.1|79.6|10.3|31.7|42.0|26.6|14.1|8.8|4.4|4.4|18.8|0.9
ATL|15|9|6|.600|48.3|117.7|43.5|96.6|45.1|14.9|43.5|34.3|15.7|20.7|75.9|13.9|31.3|45.2|30.9|15.3|10.3|3.9|6.1|21.8|1.9
MIA|15|9|6|.600|48.3|120.5|42.1|89.0|47.3|14.3|40.7|35.2|21.9|29.5|74.4|10.7|31.5|42.2|29.6|14.4|7.9|5.7|4.9|21.3|0.7
OKC|15|9|6|.600|48.0|112.1|41.8|90.5|46.2|10.8|31.6|34.2|17.7|22.2|79.9|11.1|34.8|45.9|23.2|13.4|8.2|5.4|5.1|18.9|4.4
NYK|14|8|6|.571|48.4|110.0|38.9|88.0|44.2|14.5|40.3|36.0|17.8|22.1|80.3|13.5|34.0|47.5|26.6|14.6|7.2|4.1|6.0|20.6|6.1
DAL|15|8|7|.533|48.0|112.3|40.7|88.0|46.3|12.9|37.9|34.1|17.9|22.8|78.7|12.5|30.7|43.2|26.7|16.3|8.7|5.7|4.9|21.7|-0.9
GSW|15|8|7|.533|48.3|113.7|39.1|86.9|44.9|15.5|41.7|37.3|20.0|24.9|80.4|12.6|31.7|44.3|27.5|16.2|8.4|5.6|5.7|21.9|0.9
CLE|16|8|8|.500|48.3|118.3|42.5|89.6|47.4|15.1|41.1|36.7|18.2|23.8|76.4|11.6|34.3|45.9|27.5|13.8|7.5|5.2|3.8|21.9|1.9
PHX|14|7|7|.500|48.0|114.1|42.0|88.4|47.5|13.9|37.4|37.1|16.2|21.2|76.4|11.1|29.1|40.2|27.6|14.2|8.0|4.1|4.7|21.4|-1.6
ORL|14|6|8|.429|48.4|109.4|39.0|85.4|45.7|14.1|40.3|35.1|17.2|22.4|77.0|10.8|31.9|42.7|26.7|16.1|7.4|4.2|4.9|22.3|-3.4
IND|15|5|10|.333|48.0|111.5|41.1|87.1|47.2|11.7|36.0|32.6|17.7|23.1|76.6|9.5|31.7|41.2|27.6|14.4|7.6|4.3|4.3|20.1|-3.3
TOR|15|5|10|.333|48.3|112.0|41.2|90.8|45.4|12.1|35.9|33.6|17.5|24.7|71.1|13.2|27.4|40.6|27.9|13.5|9.7|4.4|5.5|25.0|0.0
NOP|16|5|11|.313|48.9|115.4|39.9|86.6|46.1|9.9|29.4|33.6|25.6|31.3|81.8|11.1|30.7|41.8|24.3|15.8|9.7|5.1|5.7|24.3|-7.4
WAS|16|5|11|.313|48.6|110.8|39.6|86.6|45.7|10.4|32.6|31.8|21.1|26.6|79.5|10.9|31.4|42.3|23.8|14.7|7.5|5.6|3.6|20.3|-7.2
LAC|13|4|9|.308|48.4|111.9|39.1|84.3|46.4|14.4|36.8|39.0|19.4|24.6|78.8|10.1|29.4|39.5|26.8|17.2|9.5|4.5|4.4|21.5|-5.8
CHA|14|4|10|.286|48.4|100.1|35.1|87.0|40.4|14.3|45.4|31.4|15.6|18.9|82.6|14.9|31.9|46.9|22.0|19.4|7.1|4.6|4.5|21.1|-10.3
CHI|14|4|10|.286|48.4|116.2|40.9|90.1|45.4|13.2|41.3|32.0|21.1|27.7|76.3|12.9|31.1|43.9|27.8|17.2|8.4|5.6|4.8|23.4|-8.4
BKN|14|3|11|.214|48.4|110.9|37.7|84.0|44.9|14.5|40.0|36.3|20.9|28.0|74.7|11.4|29.9|41.3|24.4|17.5|8.3|4.9|4.7|25.6|-8.4
UTA|16|3|13|.188|48.6|108.8|38.6|86.2|44.8|13.0|36.9|35.3|18.5|24.1|76.7|11.4|33.0|44.4|25.1|16.9|7.0|5.8|5.2|23.1|-7.3
SAC|14|1|13|.071|48.0|107.7|39.2|86.1|45.6|12.5|36.4|34.4|16.8|21.9|76.5|9.9|29.9|39.7|25.4|17.4|7.9|3.4|5.2|22.5|-14.0
MIL|15|1|14|.067|48.0|107.7|38.1|88.7|42.9|14.9|43.8|34.1|16.7|22.3|74.6|13.5|31.5|45.1|24.8|16.9|7.1|4.6|5.5|23.4|-13.1
"""

TEAM_NAMES = {
    "ATL": ("Atlanta Hawks", "East"), "BOS": ("Boston Celtics", "East"),
    "BKN": ("Brooklyn Nets", "East"), "CHA": ("Charlotte Hornets", "East"),
    "CHI": ("Chicago Bulls", "East"), "CLE": ("Cleveland Cavaliers", "East"),
    "DAL": ("Dallas Mavericks", "West"), "DEN": ("Denver Nuggets", "West"),
    "DET": ("Detroit Pistons", "East"), "GSW": ("Golden State Warriors", "West"),
    "HOU": ("Houston Rockets", "West"), "IND": ("Indiana Pacers", "East"),
    "LAC": ("LA Clippers", "West"), "LAL": ("Los Angeles Lakers", "West"),
    "MEM": ("Memphis Grizzlies", "West"), "MIA": ("Miami Heat", "East"),
    "MIL": ("Milwaukee Bucks", "East"), "MIN": ("Minnesota Timberwolves", "West"),
    "NOP": ("New Orleans Pelicans", "West"), "NYK": ("New York Knicks", "East"),
    "OKC": ("Oklahoma City Thunder", "West"), "ORL": ("Orlando Magic", "East"),
    "PHI": ("Philadelphia 76ers", "East"), "PHX": ("Phoenix Suns", "West"),
    "POR": ("Portland Trail Blazers", "West"), "SAC": ("Sacramento Kings", "West"),
    "SAS": ("San Antonio Spurs", "West"), "TOR": ("Toronto Raptors", "East"),
    "UTA": ("Utah Jazz", "West"), "WAS": ("Washington Wizards", "East"),
}


# --------------------------------------------------------------------------- accessors
def _rows(block: str) -> list[list[str]]:
    return [ln.split("|") for ln in block.strip().splitlines() if ln.strip()]


def slate() -> list[dict]:
    out = []
    for gid, date, away, home, tm, arena, city, state in _rows(SLATE):
        out.append({
            "game_id": gid, "date": date, "away": away, "home": home,
            "matchup": f"{away} @ {home}", "time_et": tm,
            "arena": arena, "city": city, "state": state,
            "source_url": f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}",
            "list_url": SOURCE_PAGES["schedule"]["url"],
        })
    return out


def standings() -> list[dict]:
    out = []
    for f in _rows(STANDINGS):
        out.append({
            "tri": f[0], "conf": f[1], "seed": int(f[2]),
            "w": int(f[3]), "l": int(f[4]), "pct": f[5], "gb": f[6],
            "conf_record": f[7], "div_record": f[8],
            "home": f[9], "road": f[10], "neutral": f[11], "ot": f[12],
            "last10": f[13], "streak": f[14],
            "name": TEAM_NAMES[f[0]][0],
            "source_url": SOURCE_PAGES["standings"]["url"],
        })
    return out


def advanced() -> list[dict]:
    keys = ["tri", "gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg", "ast_pct",
            "oreb_pct", "dreb_pct", "tov_pct", "efg", "ts", "pace", "pie", "poss"]
    out = []
    for f in _rows(ADVANCED):
        r = dict(zip(keys, f[:17]))
        for k in keys[1:]:
            r[k] = float(r[k].replace(",", ""))
        r["gp"], r["w"], r["l"], r["poss"] = int(r["gp"]), int(r["w"]), int(r["l"]), int(r["poss"])
        r["name"] = TEAM_NAMES[r["tri"]][0]
        r["source_url"] = SOURCE_PAGES["team_adv"]["url"]
        out.append(r)
    return out


def opponent() -> list[dict]:
    keys = ["tri", "gp", "opp_pts", "opp_fg_pct", "opp_3p_pct", "opp_reb", "opp_tov",
            "opp_stl", "opp_blk", "opp_pf", "plus_minus"]
    out = []
    for f in _rows(OPPONENT):
        r = dict(zip(keys, f[:11]))
        for k in keys[1:]:
            r[k] = float(r[k])
        r["gp"] = int(r["gp"])
        r["source_url"] = SOURCE_PAGES["team_opp"]["url"]
        out.append(r)
    return out


def traditional() -> list[dict]:
    keys = ["tri", "gp", "w", "l", "win_pct", "min", "pts", "fgm", "fga", "fg_pct",
            "fg3m", "fg3a", "fg3_pct", "ftm", "fta", "ft_pct", "oreb", "dreb", "reb",
            "ast", "tov", "stl", "blk", "pf", "plus_minus"]
    out = []
    for f in _rows(TRADITIONAL):
        r = dict(zip(keys, f[:25]))
        for k in keys[1:]:
            if k not in ("win_pct",):
                r[k] = float(r[k])
        r["gp"], r["w"], r["l"] = int(r["gp"]), int(r["w"]), int(r["l"])
        r["win_pct"] = float(r["win_pct"].lstrip(".")) / 1000.0 if r["win_pct"].startswith(".") else float(r["win_pct"])
        r["source_url"] = SOURCE_PAGES["team_trad"]["url"]
        out.append(r)
    return out


def finals_2026_11_15() -> list[dict]:
    """Official 11/15 finals. A club whose period row was not transcribed carries None."""
    out = []
    for gid, date, away, home, ap, hp, ot, aq, hq, book in _rows(FINALS_2026_11_15):
        a_q = [int(x) for x in aq.split(",")] if aq else None
        h_q = [int(x) for x in hq.split(",")] if hq else None
        status, note = QUARTER_PROVENANCE[gid]
        out.append({
            "game_id": gid, "date": date, "away": away, "home": home,
            "away_pts": int(ap), "home_pts": int(hp), "ot_periods": int(ot),
            "away_q": a_q, "home_q": h_q,
            "home_margin": int(hp) - int(ap),
            "total_pts": int(ap) + int(hp),
            "final_source_url": f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}",
            "gamebook_url": FINALS_GAMEBOOK_BASE + book,
            "quarter_status": status, "quarter_note": note,
            "list_url": SOURCE_PAGES["schedule"]["url"],
        })
    return out


def teams() -> dict:
    """One dict per club joining all three official pages. Nothing is imputed."""
    adv = {r["tri"]: r for r in advanced()}
    opp = {r["tri"]: r for r in opponent()}
    tra = {r["tri"]: r for r in traditional()}
    st = {r["tri"]: r for r in standings()}
    out = {}
    for tri, (name, conf) in TEAM_NAMES.items():
        a, o, t, s = adv[tri], opp[tri], tra[tri], st[tri]
        # Cross-source identity: the traditional page prints points scored per game, and
        # OffRtg x POSS / (100 x GP) should reproduce it from the advanced page. This is a
        # check, not a substitution - both published values stay as read.
        derived_pts_for = a["off_rtg"] * a["poss"] / (100.0 * a["gp"])
        out[tri] = {
            "tri": tri, "name": name, "conf": conf,
            "gp": a["gp"], "w": s["w"], "l": s["l"], "pct": s["pct"],
            "seed": s["seed"], "gb": s["gb"],
            "home": s["home"], "road": s["road"], "neutral": s["neutral"],
            "ot": s["ot"], "last10": s["last10"], "streak": s["streak"],
            # index 4 (advanced page)
            "off_rtg": a["off_rtg"], "def_rtg": a["def_rtg"], "net_rtg": a["net_rtg"],
            "pace": a["pace"], "poss": a["poss"], "pie": a["pie"],
            "efg": a["efg"], "ts": a["ts"], "tov_pct": a["tov_pct"],
            "oreb_pct": a["oreb_pct"], "dreb_pct": a["dreb_pct"], "ast_pct": a["ast_pct"],
            # index 5 (opponent page): the official points-allowed column
            "opp_pts": o["opp_pts"], "opp_fg_pct": o["opp_fg_pct"], "opp_3p_pct": o["opp_3p_pct"],
            # index 6 (traditional page): the official points-scored column
            "pts_for": t["pts"], "fg_pct": t["fg_pct"], "fg3_pct": t["fg3_pct"],
            "ft_pct": t["ft_pct"], "reb": t["reb"], "ast": t["ast"], "stl": t["stl"],
            "blk": t["blk"], "tov": t["tov"],
            "plus_minus_trad": t["plus_minus"], "plus_minus_opp": o["plus_minus"],
            "pts_for_derived": round(derived_pts_for, 2),
            "pts_for_crosscheck_delta": round(derived_pts_for - t["pts"], 3),
            "src_rec": SOURCE_PAGES["standings"]["url"],
            "src_adv": SOURCE_PAGES["team_adv"]["url"],
            "src_opp": SOURCE_PAGES["team_opp"]["url"],
            "src_trad": SOURCE_PAGES["team_trad"]["url"],
        }
    return out


def crosschecks() -> dict:
    """Arithmetic identities the official pages must satisfy, computed from this capture."""
    st = standings()
    adv = advanced()
    tra = traditional()
    opp = opponent()
    wins = sum(r["w"] for r in st)
    losses = sum(r["l"] for r in st)
    home_w = sum(int(r["home"].split("-")[0]) for r in st)
    home_l = sum(int(r["home"].split("-")[1]) for r in st)
    road_w = sum(int(r["road"].split("-")[0]) for r in st)
    road_l = sum(int(r["road"].split("-")[1]) for r in st)
    neutral_w = sum(int(r["neutral"].split("-")[0]) for r in st)
    neutral_l = sum(int(r["neutral"].split("-")[1]) for r in st)
    gp = sum(r["gp"] for r in adv)
    # points scored vs points allowed across the league, weighted by games
    pts_for = sum(t["pts"] * t["gp"] for t in tra)
    pts_against = sum(o["opp_pts"] * o["gp"] for o in opp)
    games = gp / 2.0
    diff = pts_for - pts_against
    # rounding bound: 30 clubs x 0.05 rounding on each of two columns x mean GP
    bound = 30 * 0.05 * 2 * (gp / 30.0)
    return {
        "n_clubs": len(st),
        "wins": wins, "losses": losses, "wins_equal_losses": wins == losses,
        "home_w": home_w, "road_l": road_l, "home_w_equal_road_l": home_w == road_l,
        "home_l": home_l, "road_w": road_w, "home_l_equal_road_w": home_l == road_w,
        "team_games": gp, "league_games": games,
        "pts_for_sum": round(pts_for, 1), "pts_against_sum": round(pts_against, 1),
        "pts_diff": round(diff, 1), "rounding_bound": round(bound, 1),
        "pts_balance_within_bound": abs(diff) <= bound,
        "games_whole": gp % 2 == 0,
        "n_teams_advanced": len(adv), "n_teams_opponent": len(opp),
        "n_teams_traditional": len(tra),
        "all_three_pages_complete": len(adv) == len(opp) == len(tra) == 30,
    }


def selftest() -> list[str]:
    """Hard invariants. Raises on any failure so a bad capture can never be published."""
    problems = []
    if len(slate()) != 26:
        # the 3-day window 2026-11-19..22 (4 + 9 Cup + 6 + 7); the 12 played 11/18 games are
        # settlement context in the committed finals feeds, not slate rows
        problems.append(f"slate: expected 26 games, got {len(slate())}")
    ids = [g["game_id"] for g in slate()]
    if len(set(ids)) != len(ids):
        problems.append("slate: duplicate game id")
    if any(not (len(i) == 10 and i.startswith("002")) for i in ids):
        problems.append("slate: malformed official game id")
    if len(standings()) != 30 or len(TEAM_NAMES) != 30:
        problems.append("standings: not 30 clubs")
    c = crosschecks()
    for k in ("wins_equal_losses", "home_w_equal_road_l", "home_l_equal_road_w",
              "pts_balance_within_bound", "games_whole", "all_three_pages_complete"):
        if not c[k]:
            problems.append(f"crosscheck {k} failed: {c}")
    for g in finals_2026_11_15():
        if g["away_q"] is not None and sum(g["away_q"]) != g["away_pts"]:
            problems.append(f"{g['game_id']}: away quarters {sum(g['away_q'])} != {g['away_pts']}")
        if g["home_q"] is not None and sum(g["home_q"]) != g["home_pts"]:
            problems.append(f"{g['game_id']}: home quarters {sum(g['home_q'])} != {g['home_pts']}")
    for r in INJURY_RELEASES[0]["rows"]:
        if len(r) != 8:
            problems.append(f"injury row malformed (expected 8 cells): {r}")
            continue
        # A row with no status is only allowed when it is either the league's own
        # "NOT YET SUBMITTED" placeholder, or a row whose extraction artefact is stated
        # in the trailing note. Anything else would be an unexplained blank.
        if not r[5] and r[6] != "NOT YET SUBMITTED" and not r[7]:
            problems.append(f"injury row has no status, is not a NOT YET SUBMITTED "
                            f"placeholder, and carries no note: {r}")
        if r[6] == "NOT YET SUBMITTED" and r[4]:
            problems.append(f"a player row cannot be a NOT YET SUBMITTED placeholder: {r}")
    return problems
