"""Write this session's official-source captures to captures.json.

Run:  python3 audit/2026-11-14-bc867bff/make_captures.py
Then: python3 audit/2026-11-14-bc867bff/verify_captures.py

Every value below was read off an official NBA document by session arena/bc867bff-nba2 on
2026-11-14 between 18:41 and 18:52 UTC, through the platform page-fetch tool (direct TLS egress
from this workspace to nba.com is blocked; the fetch tool reaches it). Nothing here is inferred:
each row carries the URL it came from, and the two documents that could not be read are recorded
as failures in ``still_blocked`` rather than filled in.
"""

from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
CAPTURED_UTC = "2026-11-14T18:52:00Z"
INJ_PDF = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf"

TEAMID = {"Denver Nuggets": "1610612743",
          "Cleveland Cavaliers": "1610612739",
          "Minnesota Timberwolves": "1610612750"}


def inj(date, t, mu, team, pl, st, reason):
    return {"game_date": date, "game_time_et": t, "matchup": mu, "team": team,
            "player": pl, "status": st, "reason": reason, "source_url": INJ_PDF}


def rot(rank, name, pid, team, age, gp, w, l, mpg, pts):
    return {"rank": rank, "player": name, "player_id": pid, "team": team, "age": age, "gp": gp,
            "team_w": w, "team_l": l, "mpg": mpg, "ppg": pts,
            "source_url": "https://www.nba.com/stats/players/traditional?TeamID=" + TEAMID[team]}


DEN, NOP = "Denver Nuggets", "New Orleans Pelicans"
DAL, CLE = "Dallas Mavericks", "Cleveland Cavaliers"
BKN, MEM = "Brooklyn Nets", "Memphis Grizzlies"
CHI, MIN = "Chicago Bulls", "Minnesota Timberwolves"
DET, MIA = "Detroit Pistons", "Miami Heat"
D14, D15 = "2026-11-14", "2026-11-15"

INJURY_ROWS = [
    inj(D14, "07:00", "DEN@NOP", DEN, "Holmes II, DaRon", "Out", "G League - On Assignment"),
    inj(D14, "07:00", "DEN@NOP", DEN, "Nembhard, Ryan", "Out", "G League - Two-Way"),
    inj(D14, "07:00", "DEN@NOP", DEN, "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain"),
    inj(D14, "07:00", "DEN@NOP", DEN, "Whitmore, Cam", "Out", "G League - Two-Way"),
    inj(D14, "07:00", "DEN@NOP", NOP, "McGowens, Bryce", "Out", "Injury/Illness - Left Elbow Infection"),
    inj(D14, "07:00", "DEN@NOP", NOP, "Missi, Yves", "Probable",
        "Injury/Illness - Left Knee Contusion / Bone Bruise"),
    inj(D14, "07:00", "DEN@NOP", NOP, "Murphy III, Trey", "Out",
        "Injury/Illness - Bilateral Patellar Tendinopathy"),
    inj(D14, "07:00", "DEN@NOP", NOP, "Murray, Dejounte", "Out", "Injury/Illness - Left Ankle Sprain"),
    inj(D14, "07:00", "DEN@NOP", NOP, "Watford, Trendon", "Out", "Injury/Illness - Right Ankle Sprain"),
    inj(D14, "07:30", "DAL@CLE", DAL, "Biberovic, Tarik", "Out", "Injury/Illness - Right Heel Bursitis"),
    inj(D14, "07:30", "DAL@CLE", DAL, "Christie, Max", "Doubtful", "Injury/Illness - Left Ankle Sprain"),
    inj(D14, "07:30", "DAL@CLE", DAL, "de Larrea, Sergio", "Out", "Injury/Illness - Right Knee Sprain"),
    inj(D14, "07:30", "DAL@CLE", DAL, "Johnson Jr., Morez", "Probable",
        "Injury/Illness - Left Shin / Tibia Contusion"),
    inj(D14, "07:30", "DAL@CLE", DAL, "Lively II, Dereck", "Out", "Injury/Illness - Right Foot Surgery"),
    inj(D14, "07:30", "DAL@CLE", DAL, "Martin, Caleb", "Available", "Injury/Illness - Right Thumb Splint"),
    inj(D14, "07:30", "DAL@CLE", CLE, "Allen, Jarrett", "Questionable",
        "Injury/Illness - Right Knee Injury Management"),
    inj(D14, "07:30", "DAL@CLE", CLE, "Harden, James", "Questionable",
        "Injury/Illness - Left Lower Leg/Calf Tightness"),
    inj(D14, "07:30", "DAL@CLE", CLE, "Merrill, Sam", "Out", "Injury/Illness - Right Elbow Injury Management"),
    inj(D14, "07:30", "DAL@CLE", CLE, "Mitchell, Donovan", "Questionable",
        "Injury/Illness - Left Knee Contusion/Injury Management"),
    inj(D14, "07:30", "DAL@CLE", CLE, "Mobley, Evan", "Out", "Injury/Illness - Left Great Toe Sprain"),
    inj(D14, "07:30", "DAL@CLE", CLE, "Tomlin, Nae'Qwan", "Out", "Injury/Illness - Low Back Stress Reaction"),
    inj(D14, "07:30", "DAL@CLE", CLE, "Udeh, Jr., Ernest", "Out", "G League - Two-Way"),
    inj(D14, "07:30", "DAL@CLE", CLE, "Watson, Peyton", "Questionable",
        "Injury/Illness - Right Hamstring Injury Management"),
    inj(D14, "08:00", "BKN@MEM", BKN, "Bilodeau, Tyler", "Out", "G League - Two-Way"),
    inj(D14, "08:00", "BKN@MEM", BKN, "Brown Jr., Mikel", "Probable", "Injury/Illness - Illness"),
    inj(D14, "08:00", "BKN@MEM", BKN, "Jefferson, Joshua", "Out", "G League - On Assignment"),
    inj(D14, "08:00", "BKN@MEM", BKN, "Nelson, Grant", "Out", "G League - Two-Way"),
    inj(D14, "08:00", "BKN@MEM", BKN, "Saraf, Ben", "Out", "G League - On Assignment"),
    inj(D14, "08:00", "BKN@MEM", BKN, "Traore, Nolan", "Probable",
        "Injury/Illness - Right Calf Tightness / Soreness"),
    inj(D14, "08:00", "CHI@MIN", CHI, "Awaka, Tobe", "Out", "Injury/Illness - Disc Irritation"),
    inj(D14, "08:00", "CHI@MIN", CHI, "Claxton, Nic", "Questionable",
        "Injury/Illness - Left Hamstring Injury Management"),
    inj(D14, "08:00", "CHI@MIN", CHI, "Powell, Norman", "Questionable",
        "Injury/Illness - Low Back Injury Management"),
    inj(D14, "08:00", "CHI@MIN", CHI, "Sellers, Jaylin", "Out", "G League - Two-Way"),
    inj(D14, "08:00", "CHI@MIN", CHI, "Smith, Jalen", "Questionable", "Injury/Illness - Left Finger Sprain"),
    inj(D14, "08:00", "CHI@MIN", CHI, "Swain, Dailyn", "Out", "G League - On Assignment"),
    inj(D14, "08:00", "CHI@MIN", CHI, "Wilson, Caleb", "Out", "Injury/Illness - Right Metacarpal Fracture"),
    inj(D14, "08:00", "CHI@MIN", MIN, "Beringer, Joan", "Available", "Injury/Illness - Face Mask"),
    inj(D14, "08:00", "CHI@MIN", MIN, "DiVincenzo, Donte", "Out",
        "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    inj(D14, "08:00", "CHI@MIN", MIN, "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy"),
    inj(D14, "08:00", "DET@MIA", DET, "Duren, Jalen", "Out", "Injury/Illness - Right Hamstring Strain"),
    inj(D14, "08:00", "DET@MIA", DET, "Harkless, Elijah", "Available", "G League - Two-Way"),
    inj(D14, "08:00", "DET@MIA", DET, "Joe, Isaiah", "Out", "Injury/Illness - Right Hip Contusion"),
    inj(D14, "08:00", "DET@MIA", DET, "Jones, Isaac", "Available", "G League - Two-Way"),
    inj(D14, "08:00", "DET@MIA", DET, "Lanier, Chaz", "Out", "G League - On Assignment"),
    inj(D14, "08:00", "DET@MIA", DET, "Okorie, Ebuka", "Out", "G League - On Assignment"),
    inj(D14, "08:00", "DET@MIA", DET, "Onyenso, Ugonna", "Out", "G League - Two-Way"),
    inj(D14, "08:00", "DET@MIA", MIA, "Antetokounmpo, Giannis", "Probable",
        "Injury/Illness - Right Wrist Sprain"),
    inj(D14, "08:00", "DET@MIA", MIA, "Goldin, Vladislav", "Out", "G League - Two-Way"),
    inj(D14, "08:00", "DET@MIA", MIA, "Larsson, Pelle", "Doubtful", "Injury/Illness - Illness"),
    inj(D14, "08:00", "DET@MIA", MIA, "Thompson, Klay", "Probable", "Injury/Illness - Left Ankle Sprain"),
]

NOT_YET_SUBMITTED = [
    {"game_date": D14, "game_time_et": "08:00", "matchup": "BKN@MEM", "team": MEM,
     "reason": "NOT YET SUBMITTED", "source_url": INJ_PDF},
]
for t, mu, a, b in [
    ("01:00", "IND@PHI", "Indiana Pacers", "Philadelphia 76ers"),
    ("04:00", "LAL@PHX", "Los Angeles Lakers", "Phoenix Suns"),
    ("04:30", "CHA@LAC", "Charlotte Hornets", "LA Clippers"),
    ("05:00", "SAS@UTA", "San Antonio Spurs", "Utah Jazz"),
    ("06:00", "DAL@BOS", "Dallas Mavericks", "Boston Celtics"),
    ("06:00", "NYK@TOR", "New York Knicks", "Toronto Raptors"),
    ("07:00", "HOU@WAS", "Houston Rockets", "Washington Wizards"),
    ("08:00", "ATL@MIL", "Atlanta Hawks", "Milwaukee Bucks"),
    ("09:00", "OKC@SAC", "Oklahoma City Thunder", "Sacramento Kings"),
]:
    for team in (a, b):
        NOT_YET_SUBMITTED.append({"game_date": D15, "game_time_et": t, "matchup": mu, "team": team,
                                  "reason": "NOT YET SUBMITTED", "source_url": INJ_PDF})

RECORDS_STRIP = {
    "DEN": [6, 4], "NOP": [4, 9], "DAL": [7, 5], "CLE": [6, 7], "BKN": [3, 8], "MEM": [8, 4],
    "DET": [8, 3], "MIA": [6, 6], "CHI": [2, 9], "MIN": [9, 3], "IND": [5, 8], "PHI": [10, 3],
    "LAL": [11, 2], "PHX": [5, 6], "CHA": [4, 8], "LAC": [3, 8], "SAS": [11, 2], "UTA": [1, 12],
    "BOS": [10, 2], "NYK": [6, 6], "TOR": [5, 7], "HOU": [10, 3], "WAS": [4, 9], "ATL": [7, 6],
    "MIL": [1, 12], "OKC": [8, 5], "SAC": [1, 11], "ORL": [5, 7], "POR": [9, 3],
}

SLATE_REREAD = [
    [D14, "19:00", "DEN", "NOP", "0022600231", "Smoothie King Center", "New Orleans, LA"],
    [D14, "19:30", "DAL", "CLE", "0022600232", "Rocket Arena", "Cleveland, OH"],
    [D14, "20:00", "DET", "MIA", "0022600233", "Kaseya Center", "Miami, FL"],
    [D14, "20:00", "BKN", "MEM", "0022600234", "FedExForum", "Memphis, TN"],
    [D14, "20:00", "CHI", "MIN", "0022600235", "Target Center", "Minneapolis, MN"],
    [D15, "13:00", "IND", "PHI", "0022600236", "Xfinity Mobile Arena", "Philadelphia, PA"],
    [D15, "16:00", "LAL", "PHX", "0022600237", "Mortgage Matchup Center", "Phoenix, AZ"],
    [D15, "16:30", "CHA", "LAC", "0022600238", "Intuit Dome", "Inglewood, CA"],
    [D15, "17:00", "SAS", "UTA", "0022600239", "Delta Center", "Salt Lake City, UT"],
    [D15, "18:00", "DAL", "BOS", "0022600240", "TD Garden", "Boston, MA"],
    [D15, "18:00", "NYK", "TOR", "0022600241", "Scotiabank Arena", "Toronto, ON"],
    [D15, "19:00", "HOU", "WAS", "0022600242", "", ""],
    [D15, "20:00", "ATL", "MIL", "0022600243", "", ""],
    [D15, "21:00", "OKC", "SAC", "0022600244", "", ""],
    ["2026-11-16", "19:00", "ORL", "BOS", "0022600245", "", ""],
    ["2026-11-16", "19:00", "CHI", "CLE", "0022600246", "", ""],
    ["2026-11-16", "19:00", "MEM", "WAS", "0022600247", "", ""],
    ["2026-11-16", "19:30", "PHI", "BKN", "0022600248", "", ""],
    ["2026-11-16", "19:30", "HOU", "MIA", "0022600249", "", ""],
    ["2026-11-16", "20:00", "POR", "MIN", "0022600250", "", ""],
]

ROTATION = [
    rot(1, "Jamal Murray", "1627750", DEN, 29, 10, 6, 4, 36.4, 26.2),
    rot(2, "Nikola Jokic", "203999", DEN, 31, 10, 6, 4, 36.3, 23.5),
    rot(3, "Christian Braun", "1631128", DEN, 25, 10, 6, 4, 34.4, 12.4),
    rot(4, "Cameron Johnson", "1629661", DEN, 30, 7, 4, 3, 28.2, 12.1),
    rot(5, "Aaron Gordon", "203932", DEN, 31, 10, 6, 4, 29.1, 11.0),
    rot(6, "DeMar DeRozan", "201942", DEN, 37, 9, 5, 4, 23.5, 10.0),
    rot(7, "Trevon Brazile", "1642350", DEN, 23, 10, 6, 4, 19.5, 7.1),
    rot(8, "Marvin Bagley III", "1628963", DEN, 27, 10, 6, 4, 12.3, 5.8),
    rot(1, "Donovan Mitchell", "1628378", CLE, 30, 13, 6, 7, 33.0, 23.0),
    rot(2, "James Harden", "201935", CLE, 37, 13, 6, 7, 32.8, 16.9),
    rot(3, "Evan Mobley", "1630596", CLE, 25, 12, 6, 6, 32.0, 16.9),
    rot(4, "Meleek Thomas", "1643509", CLE, 20, 10, 5, 5, 22.5, 13.0),
    rot(5, "Jarrett Allen", "1628386", CLE, 28, 11, 5, 6, 26.0, 12.5),
    rot(6, "Peyton Watson", "1631212", CLE, 24, 11, 6, 5, 28.2, 10.4),
    rot(7, "Thomas Bryant", "1628418", CLE, 29, 7, 2, 5, 13.0, 8.7),
    rot(8, "Jaylon Tyson", "1642281", CLE, 23, 7, 4, 3, 22.4, 8.3),
    rot(1, "Anthony Edwards", "1630162", MIN, 25, 4, 3, 1, 33.7, 33.3),
    rot(2, "LaMelo Ball", "1630163", MIN, 25, 12, 9, 3, 27.5, 18.6),
    rot(3, "Ayo Dosunmu", "1630245", MIN, 26, 12, 9, 3, 31.0, 18.1),
    rot(4, "Jaden McDaniels", "1630183", MIN, 26, 12, 9, 3, 33.1, 16.9),
    rot(5, "Jonathan Kuminga", "1630228", MIN, 24, 12, 9, 3, 30.2, 12.4),
    rot(6, "Terrence Shannon Jr", "1630545", MIN, 26, 9, 6, 3, 21.5, 10.6),
    rot(7, "Bones Hyland", "1630538", MIN, 26, 12, 9, 3, 13.1, 9.8),
    rot(8, "Rudy Gobert", "203497", MIN, 34, 11, 9, 2, 29.3, 7.9),
]

DOC = {
    "injury_report": {
        "url": INJ_PDF,
        "header_verbatim": "Injury Report: 11/14/26 01:30 PM",
        "index_page": "https://official.nba.com/nba-injury-report-2026-27-season/",
        "rows": INJURY_ROWS,
        "not_yet_submitted": NOT_YET_SUBMITTED,
        "transcription_notes": [
            "This is the freshest published release at capture time: the official index lists quarter-hourly "
            "releases for 11/14 and the last one present is the 1:30 p.m. ET report.",
            "Jarrett Allen's Reason cell wraps across the PDF page break - 'Right Knee Injury' ends page 1 and "
            "'Management' heads page 2. The two fragments are joined into one value here and nowhere split.",
            "The continuation pages drop the Game Date / Time / Matchup / Team cells. Club attribution is read "
            "from the alphabetical run of each club's block ('Last, First'), which is unambiguous per game.",
            "No 11/15 club had filed as of this capture. The day-before deadline is 5 p.m. local on 11/14, i.e. "
            "21:00-23:00 UTC tonight - after this capture, so those cells are blank by rule, not by omission.",
            "Memphis is recorded NOT YET SUBMITTED for its own 8:00 p.m. ET game. At 1:30 p.m. ET the local "
            "game-day window (11 a.m.-1 p.m. Central) is still open, so this is not a missed deadline.",
        ],
    },
    "records_strip": {
        "url": "https://www.nba.com/game/okc-vs-lac-0022600042/box-score",
        "what": ("The scoreboard strip on the game pages renders each club's live W-L. 29 of 30 clubs appear on "
                 "the 11/14-11/16 dates shown; GSW's first game in the window is 11/17 so it is absent from the "
                 "strip and is not claimed here."),
        "records": RECORDS_STRIP,
        "n_clubs": len(RECORDS_STRIP),
    },
    "slate_reread": {
        "url": "https://www.nba.com/schedule?date=2026-11-14",
        "what": ("20 of the 27 games in the published window re-read from the official schedule: all five 11/14 "
                 "games with times, arenas and ids; all nine 11/15 games; six of eight 11/16 games before the "
                 "render truncated. 11/17 was not re-read in this session and is not claimed."),
        "times_note": ("Times are Eastern on a 24-hour clock, the convention the published window uses (the page "
                       "prints '7:00 PM ET' -> 19:00). The official injury report prints the same tips as '07:00 "
                       "(ET)' on a 12-hour dial without a meridiem; V9 reconciles the two printings."),
        "games": SLATE_REREAD,
    },
    "player_rotation": {
        "url": "https://www.nba.com/stats/players/traditional?TeamID=<club id>",
        "what": ("Season traditional averages per club, from the official stats table, in the page's own order - "
                 "which is PER-GAME POINTS descending, not minutes (found by re-deriving the sort from the "
                 "captured values: PTS is monotone in rank, MIN is not). The site's rotation table therefore "
                 "re-orders by minutes and says so. This endpoint was recorded as unreachable by earlier "
                 "sessions; it is reachable and renders server-side, which is what unblocks the "
                 "production-impact numbers on the site."),
        "columns": "age, gp, wins, losses (in those games), MIN, PTS - all per game except age/gp/wins/losses",
        "row_count_claim_on_page": "Denver's page header prints '16 Rows' for the club.",
        "rows": ROTATION,
    },
    "still_blocked": [
        {"what": "per-game player logs (minutes floor, prop medians, player-level correlation)",
         "attempted": "https://www.nba.com/stats/player/1630162/gamelog",
         "result": ("the page answers but prints 'No data available' - the game-log tab is rendered client-side, "
                    "so no per-game rows are obtainable from it in this environment"),
         "consequence": ("minutes FLOOR and prop MEDIAN stay blank by policy; season averages are now available "
                         "and are used for what they can support")},
        {"what": "market prices", "attempted": "no licensed odds feed is connected to this repository",
         "result": "unchanged", "consequence": "no ROI, no CLV, no stake; gate G6 stays open"},
    ],
}

PAYLOAD = {
    "schema": "nba2.capture-session.v1",
    "session": "arena/bc867bff-nba2",
    "captured_utc": CAPTURED_UTC,
    "method": ("platform page-fetch tool (fetch_page). Direct TLS egress from this workspace to every nba.com "
               "host is blocked; the tool reaches the same URLs, which is recorded rather than worked around."),
    "documents": DOC,
}

if __name__ == "__main__":
    out = HERE / "captures.json"
    out.write_text(json.dumps(PAYLOAD, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {out.name}: {len(INJURY_ROWS)} designation rows, {len(NOT_YET_SUBMITTED)} not-submitted clubs, "
          f"{len(RECORDS_STRIP)} club records, {len(SLATE_REREAD)} games re-read, {len(ROTATION)} rotation rows")
