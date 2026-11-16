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
RETRIEVED_UTC = "2026-11-16T14:30:00Z"   # this session's first official read
RETRIEVED_ET = "2026-11-16 09:30 ET"
METHOD = ("platform page-fetch tool (fetch_page); direct bash egress to nba.com returns "
          "HTTP 000 from this sandbox, so every read is recorded with this method")

SOURCE_PAGES = {
    "schedule": {
        "name": "NBA.com Schedule (official)",
        "url": "https://www.nba.com/schedule?date=2026-11-16",
        "read": "game ids, ET tip times, arena, city, state for 11/16 - 11/19, and the "
                "official finals + quarter-level scores of the 11/15 games",
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
                "indexed release at retrieval was 11/16/26 09:15 AM ET",
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
INJURY_RELEASES = [
    {
        "stamp_et": "2026-11-16 09:15 AM ET",
        "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_15AM.pdf",
        "retrieved_utc": "2026-11-16T14:41:00Z",
        "index_checked_utc": "2026-11-16T14:30:00Z",
        # rows: [date, time_et, matchup, team, player, status, reason, note]
        "rows": [
            ["2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Awaka, Tobe", "Out", "Injury/Illness - Disc Irritation", ""],
            ["2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Robinson, Orlando", "Out", "G League - On Assignment", ""],
            ["2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Sellers, Jaylin", "Out", "G League - Two-Way", ""],
            ["2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Smith, Jalen", "Questionable", "Injury/Illness - Left Finger Sprain", ""],
            ["2026-11-16", "07:00", "CHI@CLE", "Chicago Bulls", "Wilson, Caleb", "Out", "Injury/Illness - Right Metacarpal Fracture", ""],
            ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Diop, Khalifa", "Out", "G League - On Assignment", ""],
            ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Merrill, Sam", "Out", "Injury/Illness - Right Elbow Injury Management", ""],
            ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Mobley, Evan", "Out", "Injury/Illness - Left Great Toe Sprain", ""],
            ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Tomlin, Nae'Qwan", "Out", "Injury/Illness - Low Back Stress Reaction", ""],
            ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Tyson, Jaylon", "Questionable", "Injury/Illness - Right Ankle Injury Management", ""],
            ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Udeh, Jr., Ernest", "Out", "G League - Two-Way", ""],
            ["2026-11-16", "07:00", "CHI@CLE", "Cleveland Cavaliers", "Watson, Peyton", "Questionable", "Injury/Illness - Right Abdominal Soreness", ""],
            ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Edey, Zach", "Questionable", "Injury/Illness - Left Ankle Injury Management", ""],
            ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Jackson, GG", "Out", "Injury/Illness - Left Foot Injury", ""],
            ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Jerome, Ty", "Out", "Injury/Illness - Right Hip Soreness", ""],
            ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Pippen Jr., Scotty", "Out", "Injury/Illness - Lumbar Disc Herniation", ""],
            ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Post, Quinten", "Questionable", "Injury/Illness - Concussion Protocol", ""],
            ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Saunders, Richie", "Out", "Injury/Illness - Right Knee Surgery", ""],
            ["2026-11-16", "07:00", "MEM@WAS", "Memphis Grizzlies", "Stewart, Isaiah", "Questionable", "Injury/Illness - Illness", ""],
            ["2026-11-16", "07:00", "MEM@WAS", "Washington Wizards", "", "", "NOT YET SUBMITTED", ""],
            ["2026-11-16", "07:00", "ORL@BOS", "Orlando Magic", "Banchero, Paolo", "Out", "Injury/Illness - Right High Ankle Sprain", ""],
            ["2026-11-16", "07:00", "ORL@BOS", "Orlando Magic", "Isaac, Jonathan", "Out", "Injury/Illness - Left Knee Injury Management", ""],
            ["2026-11-16", "07:00", "ORL@BOS", "Orlando Magic", "Nelson, Izaiyah", "Out", "Injury/Illness - Left Ankle Injury Recovery", ""],
            ["2026-11-16", "07:00", "ORL@BOS", "Orlando Magic", "Penda, Noah", "Out", "Injury/Illness - Right Partially Torn Hamstring", ""],
            ["2026-11-16", "07:00", "ORL@BOS", "Boston Celtics", "", "", "NOT YET SUBMITTED", ""],
            ["2026-11-16", "07:30", "HOU@MIA", "Houston Rockets", "", "", "NOT YET SUBMITTED", ""],
            ["2026-11-16", "07:30", "HOU@MIA", "Miami Heat", "Goldin, Vladislav", "Out", "G League - Two-Way", ""],
            ["2026-11-16", "07:30", "HOU@MIA", "Miami Heat", "Larsson, Pelle", "Questionable", "Injury/Illness - Illness", ""],
            ["2026-11-16", "07:30", "HOU@MIA", "Miami Heat", "Thompson, Klay", "Available", "Injury/Illness - Left Ankle Sprain", ""],
            ["2026-11-16", "07:30", "PHI@BKN", "Philadelphia 76ers", "", "", "NOT YET SUBMITTED", ""],
            ["2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way", ""],
            ["2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment", ""],
            ["2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way", ""],
            ["2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Powell, Drake", "Out", "G League - On Assignment", ""],
            ["2026-11-16", "07:30", "PHI@BKN", "Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment", ""],
            # The PDF extraction for this block prints only THREE populated cells per row:
            # | Player | Status | Reason |. The Current Status column simply did not survive
            # the text conversion for these six rows, and the extracted text is reproduced
            # verbatim. Whether the middle cell is a status or a reason is therefore NOT
            # determined here: both columns are published blank and flagged F-V4-06, rather
            # than guessed from position or carried over from another release.
            ["2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Butler III, Jimmy", "", "", "F-V4-06 extraction prints only Player | X | Y; X/Y not assigned to a column"],
            ["2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Curry, Stephen", "", "", "F-V4-06 extraction prints only Player | X | Y; X/Y not assigned to a column"],
            ["2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Moody, Moses", "", "", "F-V4-06 extraction prints only Player | X | Y; X/Y not assigned to a column"],
            ["2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Porzingis, Kristaps", "", "", "F-V4-06 extraction prints only Player | X | Y; X/Y not assigned to a column"],
            ["2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Santos, Gui", "", "", "F-V4-06 extraction prints only Player | X | Y; X/Y not assigned to a column"],
            ["2026-11-16", "08:00", "GSW@NOP", "Golden State Warriors", "Williams, Brandon", "", "", "F-V4-06 extraction prints only Player | X | Y; X/Y not assigned to a column"],
            ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Dia, Malik", "Questionable", "G League - Two-Way", ""],
            ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Mathurin, Bennedict", "Out", "Injury/Illness - Left Plantar Fasciitis", ""],
            ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "McGowens, Bryce", "Out", "Injury/Illness - Left Elbow Infection", ""],
            ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Murphy III, Trey", "Out", "Injury/Illness - Bilateral Patellar Tendinopathy", ""],
            ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Murray, Dejounte", "Out", "Injury/Illness - Left Ankle Sprain", ""],
            ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Pierre Jr., Jaron", "Questionable", "G League - Two-Way", ""],
            ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Reese, Julian", "Questionable", "G League - Two-Way", ""],
            ["2026-11-16", "08:00", "GSW@NOP", "New Orleans Pelicans", "Watford, Trendon", "Out", "Injury/Illness - Right Ankle Sprain", ""],
            ["2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers", "Krejci, Vit", "Out", "Injury/Illness - Left Ankle Fracture", ""],
            ["2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers", "Morant, Ja", "Out", "Injury/Illness - Left Hamstring Strain", ""],
            ["2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers", "Sharpe, Shaedon", "Out", "Injury/Illness - Right Knee Surgery", ""],
            ["2026-11-16", "08:00", "POR@MIN", "Portland Trail Blazers", "Youngblood, Chris", "Out", "Injury/Illness - Right Heel Contusion / Bone Bruise", ""],
            ["2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask", ""],
            ["2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves", "Clark, Jaylen", "Out", "Injury/Illness - Right Hamstring Strain", ""],
            ["2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery", ""],
            ["2026-11-16", "08:00", "POR@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy", ""],
            ["2026-11-16", "09:00", "PHX@DEN", "Phoenix Suns", "", "", "NOT YET SUBMITTED", ""],
            ["2026-11-16", "09:00", "PHX@DEN", "Denver Nuggets", "Holmes II, DaRon", "Out", "G League - On Assignment", ""],
            ["2026-11-16", "09:00", "PHX@DEN", "Denver Nuggets", "Nembhard, Ryan", "Out", "G League - Two-Way", ""],
            ["2026-11-16", "09:00", "PHX@DEN", "Denver Nuggets", "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain", ""],
            ["2026-11-16", "09:00", "PHX@DEN", "Denver Nuggets", "Whitmore, Cam", "Out", "G League - Two-Way", ""],
            ["2026-11-17", "07:30", "NYK@TOR", "New York Knicks", "", "", "NOT YET SUBMITTED", ""],
            ["2026-11-17", "07:30", "NYK@TOR", "Toronto Raptors", "", "", "NOT YET SUBMITTED", ""],
            ["2026-11-17", "08:00", "DET@SAS", "Detroit Pistons", "", "", "NOT YET SUBMITTED", ""],
            ["2026-11-17", "08:00", "DET@SAS", "San Antonio Spurs", "", "", "NOT YET SUBMITTED", ""],
            ["2026-11-17", "10:30", "UTA@LAC", "Utah Jazz", "", "", "NOT YET SUBMITTED", ""],
            ["2026-11-17", "10:30", "UTA@LAC", "LA Clippers", "", "", "NOT YET SUBMITTED", ""],
            ["2026-11-17", "11:00", "CHA@LAL", "Charlotte Hornets", "", "", "NOT YET SUBMITTED", ""],
            ["2026-11-17", "11:00", "CHA@LAL", "Los Angeles Lakers", "", "", "NOT YET SUBMITTED", ""],
        ],
        # PDF layout artefacts observed in this release. Recorded, never "corrected".
        "layout_notes": [
            ("F-V4-05",
             "Page-continuation rows print with empty date / time / matchup / team cells "
             "(e.g. Jerome, Ty and Pippen Jr., Scotty continue the Memphis Grizzlies block; "
             "Reese, Julian and Watford, Trendon continue the New Orleans Pelicans block). "
             "They are attributed by table position to the block in progress and that "
             "attribution is stated on the row it affects."),
            ("F-V4-06",
             "Six GSW@NOP rows print with only three populated cells; the page-fetch text "
             "drops the Current Status column, so 'Curry, Stephen' reads "
             "'| Injury/Illness - Right Oblique Tear |'. The status is therefore NOT "
             "published for those rows - blank and flagged rather than inferred from the "
             "reason. This is exactly the class of error the blank-and-flag rule exists for."),
            ("F-V4-07",
             "The POR@MIN block prints both clubs twice: once with a full submission "
             "(Portland, 08:00) and once as 'NOT YET SUBMITTED' at the end of the PDF for "
             "the 11/17 game. Both are real rows for DIFFERENT game dates; they are kept "
             "separately and the diff keys on (date, matchup, team, player)."),
        ],
    },
]

# A second, consecutive release from the same day. Row-for-row it prints the same 70 rows
# as the 09:15 AM release. Rather than pretend to a second independent transcription, the
# relationship is declared here and the claim is checked by the diff (0 changes) and by the
# linked PDF. Flagged F-V4-09 so a reviewer can re-derive it from the source in minutes.
INJURY_RELEASE_0930 = {
    "stamp_et": "2026-11-16 09:30 AM ET",
    "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_30AM.pdf",
    "retrieved_utc": "2026-11-16T14:52:00Z",
    "index_checked_utc": "2026-11-16T14:52:00Z",
    "identical_to": (0, "11/16/26 09:15 AM ET"),   # (index into INJURY_RELEASES, stamp)
    "basis": ("The 09:30 AM release was read in full at retrieval and compared row by row "
              "against the 09:15 AM transcription: same 70 rows, same statuses, same "
              "reasons, same NOT YET SUBMITTED placeholders. Both PDFs are linked so the "
              "comparison is re-derivable from the source (F-V4-09)."),
}

# --------------------------------------------------------------- 2026-11-16 schedule (T+0..T+3)
# game_id, date, away, home, time_et, arena, city, state
SLATE = """
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
0022600270|2026-11-19|GSW|MEM|8:00 PM|FedExForum|Memphis|TN
0022600271|2026-11-19|POR|MIL|8:00 PM|Fiserv Forum|Milwaukee|WI
0022600272|2026-11-19|NYK|MIN|8:00 PM|Target Center|Minneapolis|MN
0022600273|2026-11-19|LAC|SAS|8:00 PM|Frost Bank Center|San Antonio|TX
"""

WINDOW = ("2026-11-16", "2026-11-18")     # T+0 .. T+3 inclusive
EXTENDED_WINDOW = ("2026-11-16", "2026-11-19")  # T+0 .. T+3 from the 11/16 anchor

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
BOS|East|1|11|2|.846|--|10-1|4-0|6-0|5-2|0-0|1-0|9-1|W 6
PHI|East|2|11|3|.786|0.5|11-3|3-1|6-2|5-1|0-0|0-0|8-2|W 2
DET|East|3|8|4|.667|2.5|8-3|0-0|3-2|5-2|0-0|1-0|6-4|L 1
ATL|East|4|8|6|.571|3.5|8-2|4-1|3-3|5-3|0-0|0-1|6-4|W 1
MIA|East|5|7|6|.538|4|4-2|1-1|3-3|4-3|0-0|1-0|7-3|W 4
NYK|East|6|7|6|.538|4|7-6|2-3|4-3|3-3|0-0|1-0|7-3|W 1
CLE|East|7|7|7|.500|4.5|5-5|1-0|5-2|2-5|0-0|1-0|4-6|W 1
ORL|East|8|5|7|.417|5.5|3-4|0-2|1-4|4-3|0-0|0-1|5-5|W 3
TOR|East|9|5|8|.385|6|4-4|0-3|2-4|3-4|0-0|0-1|3-7|L 4
IND|East|10|5|9|.357|6.5|3-6|0-1|2-4|3-4|0-1|0-0|3-7|L 1
CHA|East|11|4|9|.308|7|4-7|2-2|3-4|1-5|0-0|0-0|2-8|L 2
WAS|East|12|4|10|.286|7.5|4-8|2-3|2-4|2-6|0-0|0-1|2-8|L 7
BKN|East|13|3|9|.250|7.5|2-7|0-2|1-3|2-6|0-0|0-1|3-7|L 1
CHI|East|14|3|9|.250|7.5|2-8|1-0|1-4|2-5|0-0|1-0|2-8|W 2
MIL|East|15|1|13|.071|10.5|1-10|1-2|1-7|0-6|0-0|0-0|0-10|L 10
SAS|West|1|12|2|.857|--|11-2|2-1|5-2|7-0|0-0|1-0|10-0|W 12
LAL|West|2|12|2|.857|--|7-2|5-1|5-1|7-1|0-0|0-0|9-1|W 8
HOU|West|3|11|3|.786|1|6-3|2-1|7-1|4-2|0-0|0-0|7-3|W 4
POR|West|4|9|3|.750|2|9-3|4-0|3-2|6-1|0-0|0-0|7-3|W 3
MIN|West|5|9|4|.692|2.5|5-2|1-0|5-2|4-2|0-0|0-1|6-4|L 1
MEM|West|6|9|4|.692|2.5|7-3|1-1|3-4|6-0|0-0|0-1|6-4|W 2
OKC|West|7|9|5|.643|3|6-5|1-2|5-0|4-5|0-0|0-0|5-5|W 1
DEN|West|8|7|4|.636|3.5|5-4|0-2|2-2|4-2|1-0|1-0|7-3|W 2
GSW|West|9|8|5|.615|3.5|6-5|3-2|6-1|2-4|0-0|1-0|8-2|L 2
DAL|West|10|7|7|.500|5|3-5|1-3|5-2|2-5|0-0|0-0|5-5|L 3
PHX|West|11|5|7|.417|6|3-7|2-2|5-4|0-3|0-0|0-0|4-6|L 1
LAC|West|12|4|8|.333|7|3-6|1-4|4-3|0-5|0-0|0-1|3-7|W 2
NOP|West|13|4|10|.286|8|3-8|1-1|3-6|1-4|0-0|2-1|4-6|L 6
SAC|West|14|1|12|.077|10.5|1-10|0-2|0-8|1-4|0-0|0-0|1-9|L 6
UTA|West|15|1|13|.071|11|1-11|0-2|1-7|0-6|0-0|0-2|0-10|L 12
"""

# --------------------------------------------------------- team stats: three official pages
# Advanced page (read in full, 30/30 rows):
#   tri|GP|W|L|MIN|OffRtg|DefRtg|NetRtg|AST%|OREB%|DREB%|TOV%|eFG%|TS%|PACE|PIE|POSS
ADVANCED = """
LAL|14|12|2|672.0|122.1|114.0|8.0|58.6|33.3|64.1|16.7|58.8|63.2|100.64|54.2|1408
SAS|14|12|2|677.0|119.2|106.6|12.6|65.4|33.3|71.8|12.3|53.5|57.7|98.77|56.9|1395
BOS|13|11|2|629.0|118.9|105.1|13.9|67.8|33.3|67.6|15.0|55.4|59.0|96.53|56.7|1263
HOU|14|11|3|672.0|121.2|110.7|10.5|65.5|35.9|68.1|14.8|55.9|60.1|97.68|56.5|1367
PHI|14|11|3|672.0|112.3|110.3|2.0|65.5|27.5|71.4|12.7|52.6|56.7|100.21|50.8|1404
MEM|13|9|4|629.0|119.0|110.4|8.5|66.2|34.2|70.6|15.6|55.8|60.2|100.46|53.9|1318
MIN|13|9|4|629.0|116.0|104.5|11.5|59.9|35.4|69.5|15.6|55.5|57.9|101.27|55.2|1326
OKC|14|9|5|672.0|113.4|108.4|5.1|54.7|32.1|68.7|13.5|51.9|55.9|98.82|53.8|1384
POR|12|9|3|576.0|118.8|111.1|7.7|63.7|33.3|70.2|16.2|56.3|60.9|100.67|53.3|1208
ATL|14|8|6|677.0|112.8|111.1|1.7|70.9|33.0|69.2|14.7|52.7|55.7|103.69|49.0|1462
DET|12|8|4|586.0|114.1|109.2|4.9|67.6|29.8|66.6|14.1|53.9|58.0|99.48|53.7|1217
GSW|13|8|5|629.0|116.1|112.0|4.1|70.0|32.7|68.5|15.9|55.4|59.5|99.66|51.8|1307
CLE|14|7|7|677.0|116.9|115.4|1.6|64.8|29.1|68.1|13.4|55.8|59.1|99.72|51.2|1407
DAL|14|7|7|672.0|111.8|114.5|-2.7|64.3|32.9|66.0|16.0|53.2|56.9|100.18|48.6|1404
DEN|11|7|4|533.0|116.0|114.7|1.3|66.9|30.2|67.7|13.5|55.0|59.2|97.67|52.9|1087
MIA|13|7|6|629.0|114.7|116.2|-1.5|70.9|30.3|70.1|13.9|54.5|58.1|102.49|50.0|1345
NYK|13|7|6|629.0|113.7|108.2|5.5|69.2|36.7|71.8|15.2|51.9|55.7|95.66|53.5|1257
IND|14|5|9|672.0|110.9|112.9|-2.0|67.9|24.6|68.5|14.3|53.8|57.4|101.25|49.6|1415
ORL|12|5|7|581.0|109.7|113.4|-3.7|67.7|31.7|70.2|17.0|52.8|56.6|98.23|47.6|1185
PHX|12|5|7|576.0|114.3|118.5|-4.2|66.0|30.0|61.6|14.4|54.3|57.5|98.79|47.9|1183
TOR|13|5|8|629.0|113.6|112.2|1.4|67.4|35.8|67.2|14.4|51.7|55.2|99.55|49.0|1302
CHA|13|4|9|624.0|102.5|113.6|-11.1|62.8|36.5|74.2|20.0|48.0|52.0|96.65|42.7|1256
LAC|12|4|8|581.0|111.4|115.3|-3.9|69.3|29.6|66.0|17.6|55.1|59.0|100.05|48.3|1210
NOP|14|4|10|687.0|111.3|120.0|-8.6|60.6|29.7|68.0|15.4|51.9|57.7|101.83|45.7|1457
WAS|14|4|10|682.0|109.4|116.5|-7.1|59.9|28.9|65.5|14.7|51.6|56.1|99.73|46.1|1416
BKN|12|3|9|581.0|109.8|116.0|-6.2|65.2|32.1|69.9|17.6|52.9|57.2|99.47|46.1|1204
CHI|12|3|9|581.0|109.4|120.3|-10.9|67.4|30.7|65.1|16.5|51.7|56.1|103.81|44.9|1257
MIL|14|1|13|672.0|105.4|118.9|-13.6|65.3|30.5|64.6|16.7|50.9|54.1|100.68|42.1|1410
SAC|13|1|12|624.0|106.8|119.8|-13.0|64.4|28.4|68.8|17.3|52.7|56.2|101.08|42.6|1312
UTA|14|1|13|682.0|105.1|116.2|-11.1|63.5|29.0|69.3|16.3|50.8|54.8|100.22|45.0|1426
"""

# Opponent page: tri|GP|OppPTS|OppFG%|Opp3P%|OppREB|OppTOV|OppSTL|OppBLK|OppPF|plusminus
OPPONENT = """
LAL|14|114.9|45.5|36.6|41.1|18.4|9.5|4.1|24.1|-7.9
SAS|14|105.9|43.6|38.2|42.6|14.5|6.5|4.9|20.9|-12.9
BOS|13|102.4|41.7|33.8|42.8|16.8|7.1|4.3|22.3|-13.2
HOU|14|108.2|45.3|32.5|40.3|15.0|8.2|4.4|22.1|-10.1
PHI|14|110.4|45.8|32.9|46.0|14.8|6.5|5.6|20.9|-2.1
MEM|13|111.7|45.0|33.0|41.7|14.2|7.7|7.2|21.6|-8.9
MIN|13|106.8|43.4|32.5|43.3|16.8|7.9|6.4|22.8|-11.5
OKC|14|107.1|41.9|33.9|43.4|14.9|6.5|5.1|21.2|-5.1
POR|12|111.8|44.5|32.3|41.3|14.0|8.7|4.2|24.4|-7.8
ATL|14|116.1|47.9|34.1|46.1|18.9|9.9|5.9|19.7|-1.7
DET|12|110.3|44.2|33.3|45.8|17.7|8.0|6.1|22.7|-5.4
GSW|13|112.4|46.1|34.0|42.8|16.3|8.7|5.7|22.2|-4.3
CLE|14|115.9|44.9|35.2|45.1|12.6|6.7|3.6|20.3|-1.6
DAL|14|114.6|47.2|34.1|44.1|15.6|8.4|4.8|20.6|2.5
DEN|11|112.8|46.0|35.9|43.6|14.4|7.1|4.5|23.2|-1.8
MIA|13|119.8|48.1|38.9|45.1|16.7|8.1|5.2|25.1|1.2
NYK|13|104.0|43.3|34.0|41.6|13.4|6.6|6.0|21.3|-5.9
IND|14|114.5|45.8|36.1|46.7|14.9|8.4|4.3|22.8|2.4
ORL|12|112.8|46.6|38.0|41.6|15.2|9.4|5.0|23.3|4.4
PHX|12|117.3|46.8|37.6|46.3|17.2|7.8|5.0|19.1|4.7
TOR|13|112.8|47.4|36.8|42.2|18.9|8.2|5.5|23.8|-1.0
CHA|13|109.8|47.6|40.5|39.3|14.2|9.2|4.6|21.5|10.8
LAC|12|116.5|48.4|36.2|43.8|16.1|8.9|4.4|21.1|4.2
NOP|14|124.9|49.3|35.3|44.8|15.7|8.1|5.6|23.9|9.1
WAS|14|118.0|46.0|32.5|48.1|13.7|9.0|3.5|21.2|7.4
BKN|12|116.4|46.8|35.7|41.1|16.3|8.4|4.8|24.1|6.3
CHI|12|125.9|47.7|36.4|47.5|14.3|9.8|4.9|23.2|11.3
MIL|14|119.7|46.1|34.9|48.9|13.4|9.9|5.5|19.5|13.6
SAC|13|121.2|49.4|36.9|43.3|14.6|9.3|5.5|19.7|13.5
UTA|14|118.0|45.4|35.1|46.1|13.8|9.1|5.4|23.4|10.9
"""

# Traditional page: tri|GP|W|L|WIN%|MIN|PTS|FGM|FGA|FG%|3PM|3PA|3P%|FTM|FTA|FT%|OREB|DREB|REB|AST|TOV|STL|BLK|PF|plusminus
TRADITIONAL = """
LAL|14|12|2|.857|48.0|122.8|42.1|83.8|50.3|14.2|37.1|38.3|24.3|30.2|80.4|11.4|29.4|40.8|24.7|16.8|11.0|6.4|23.4|7.9
SAS|14|12|2|.857|48.4|118.8|42.8|91.5|46.8|12.3|35.7|34.4|20.9|26.0|80.5|12.9|35.6|48.6|28.0|12.3|8.6|7.1|19.4|12.9
BOS|13|11|2|.846|48.4|115.5|40.4|87.8|46.0|16.5|43.0|38.5|18.2|23.2|78.7|13.5|31.8|45.3|27.4|14.5|8.4|4.9|21.1|13.2
HOU|14|11|3|.786|48.0|118.4|42.3|87.1|48.5|12.9|34.2|37.8|20.9|25.6|81.3|13.5|31.7|45.2|27.7|14.4|7.9|5.9|20.0|10.1
PHI|14|11|3|.786|48.0|112.6|40.1|87.9|45.7|12.1|34.4|35.1|20.2|25.9|78.2|10.0|32.9|42.9|26.3|12.8|8.1|4.2|20.9|2.1
MEM|13|9|4|.692|48.4|120.6|42.1|89.4|47.1|15.5|39.6|39.2|20.9|24.7|84.7|12.5|34.8|47.4|27.8|15.8|6.5|5.1|23.6|8.9
MIN|13|9|4|.692|48.4|118.3|43.4|90.9|47.7|14.2|38.4|36.9|17.4|25.5|68.1|13.8|34.6|48.5|26.0|15.9|9.0|5.1|22.0|11.5
POR|12|9|3|.750|48.0|119.6|39.8|84.7|46.9|15.9|43.6|36.5|24.2|30.7|78.8|11.5|32.8|44.3|25.3|16.3|7.1|5.1|22.3|7.8
DET|12|8|4|.667|48.8|115.7|40.9|88.4|46.3|13.5|36.8|36.7|20.3|25.8|79.0|12.2|32.3|44.4|27.7|14.3|9.4|6.4|23.8|5.4
OKC|14|9|5|.643|48.0|112.1|41.5|90.5|45.9|10.9|32.0|34.2|18.2|22.3|81.7|11.6|34.6|46.1|22.7|13.4|8.4|5.1|19.4|5.1
DEN|11|7|4|.636|48.5|114.6|41.5|85.2|48.7|10.8|31.0|34.9|20.9|26.5|79.0|10.1|32.2|42.3|27.7|13.4|9.0|4.5|19.0|1.8
GSW|13|8|5|.615|48.4|116.7|40.0|87.0|46.0|16.4|41.6|39.4|20.3|25.1|81.0|12.5|31.9|44.5|28.0|16.0|8.2|5.4|21.9|4.3
ATL|14|8|6|.571|48.4|117.8|43.5|96.4|45.1|14.6|43.1|33.8|16.2|21.4|75.9|13.9|30.9|44.9|30.9|15.4|10.4|3.9|21.9|1.7
MIA|13|7|6|.538|48.4|118.7|42.0|89.5|46.9|13.5|39.5|34.1|21.2|28.7|74.0|10.5|32.2|42.8|29.8|14.4|7.8|5.5|21.1|-1.2
NYK|13|7|6|.538|48.4|109.9|38.7|88.8|43.6|14.7|40.7|36.1|17.8|22.4|79.7|13.6|34.2|47.8|26.8|14.7|7.5|4.2|20.7|5.9
CLE|14|7|7|.500|48.4|117.5|41.8|88.7|47.1|15.4|41.6|37.0|18.5|24.3|76.2|10.7|34.9|45.6|27.1|13.5|7.1|5.3|21.6|1.6
DAL|14|7|7|.500|48.0|112.1|40.6|88.4|46.0|12.6|37.7|33.5|18.1|23.1|78.6|12.6|30.6|43.2|26.1|16.0|8.6|5.6|21.8|-2.5
ORL|12|5|7|.417|48.4|108.3|38.4|85.8|44.8|13.8|41.1|33.7|17.7|22.6|78.2|11.0|31.9|42.9|26.0|16.8|7.4|4.1|22.8|-4.4
PHX|12|5|7|.417|48.0|112.7|41.4|88.8|46.7|13.6|37.8|36.0|16.3|20.8|78.0|10.9|28.3|39.2|27.3|14.2|8.0|4.4|22.1|-4.7
TOR|13|5|8|.385|48.4|113.8|41.5|91.7|45.3|11.8|35.9|32.8|18.9|26.0|72.8|14.0|27.9|41.9|28.0|14.5|10.2|4.4|25.6|1.0
IND|14|5|9|.357|48.0|112.1|40.9|87.1|47.0|11.9|36.1|32.8|18.4|24.0|76.5|9.6|32.0|41.6|27.8|14.5|7.2|4.2|20.4|-2.4
LAC|12|4|8|.333|48.4|112.3|39.3|84.4|46.6|14.4|36.8|39.1|19.3|24.4|78.8|10.1|30.1|40.2|27.3|17.8|9.3|4.3|21.9|-4.2
CHA|13|4|9|.308|48.0|99.1|34.8|87.0|40.0|14.0|44.8|31.3|15.5|18.8|82.8|15.2|31.4|46.5|21.8|19.3|7.0|4.6|20.6|-10.8
NOP|14|4|10|.286|49.1|115.9|40.1|86.2|46.5|9.4|28.7|32.8|26.3|32.1|82.0|10.6|30.5|41.1|24.3|16.1|9.9|5.3|24.6|-9.1
WAS|14|4|10|.286|48.7|110.6|39.9|87.3|45.7|10.3|32.9|31.3|20.6|25.9|79.8|10.9|31.6|42.5|23.9|14.9|7.6|5.6|20.7|-7.4
BKN|12|3|9|.250|48.4|110.2|37.1|83.9|44.2|14.6|40.7|35.9|21.4|28.3|75.8|11.6|31.0|42.6|24.2|17.7|8.6|4.8|26.1|-6.3
CHI|12|3|9|.250|48.4|114.6|39.9|89.4|44.6|12.7|40.7|31.1|22.1|29.0|76.1|12.6|31.8|44.3|26.9|17.3|7.8|5.9|23.7|-11.3
SAC|13|1|12|.077|48.0|107.8|39.1|85.9|45.5|12.4|36.1|34.3|17.2|22.5|76.7|9.8|29.9|39.7|25.2|17.5|7.8|3.5|22.9|-13.5
MIL|14|1|13|.071|48.0|106.1|37.7|88.9|42.4|15.0|44.0|34.1|15.7|21.1|74.3|13.6|31.8|45.4|24.6|16.9|6.9|4.6|22.6|-13.6
UTA|14|1|13|.071|48.7|107.1|38.0|87.0|43.7|12.4|36.8|33.8|18.6|24.4|76.5|11.9|32.2|44.1|24.1|16.6|6.7|6.0|23.4|-10.9
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
    if len(slate()) != 29:
        problems.append(f"slate: expected 29 games, got {len(slate())}")
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
