"""Session arena/1eeb6a21-nba2 — official 2026-11-16 capture (results feed + v5 gamebook transcript).

Every value below was read from an official NBA source this session:
  * finals + quarter rows: official gamebook PDFs at statsdmz.nba.com (one row per club,
    "SCORE BY PERIOD" table), cross-checked against https://www.nba.com/schedule?date=2026-11-16
    (all eight games print "Final" with the same scores);
  * per-player rows: the same gamebook PDFs; the three Houston bench rows whose PDF-to-text
    rendering dropped one cell (Bogdanovic, Sheppard, Tate) and the two Miami rows with the
    same defect (Keshad Johnson, Tre Donaldson) were confirmed against the official box-score
    page https://www.nba.com/game/hou-vs-mia-0022600249/box-score (columns MIN|FGM|FGA|FG%|
    3PM|3PA|3P%|FTM|FTA|FT%|OREB|DREB|REB|AST|STL|BLK|TO|PF|PTS|+/-);
  * standings + slate: https://www.nba.com/standings and the schedule/box-score pages.

Validation performed by this script (fail-closed, mirrors the v5 gates):
  * per-player points identity: pts == 2*(fg-fg3) + 3*fg3 + ft;
  * club sums: player pts/reb/ast sum to the club totals row the gamebook prints;
  * minutes: player minutes sum to 240:00 (OT games would print more; none here);
  * quarter rows: each club's period row sums to its final.

Nothing is inferred: a value that could not be read is None with a reason.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-11-16"
LIST_URL = "https://www.nba.com/schedule?date=2026-11-16"
RETRIEVED = "2026-11-17T16:30:00Z"
SESSION = "arena/1eeb6a21-nba2"
METHOD = (
    "platform page-fetch tool (fetch_page) reading each official gamebook PDF at "
    "statsdmz.nba.com plus the official schedule page; the tool returns the PDF as text. "
    "Rows whose PDF-to-text rendering dropped a cell were confirmed against the official "
    "box-score page for that game before being committed. Bash egress cannot reach nba.com."
)

GB = "https://statsdmz.nba.com/pdfs/20261116/20261116_{m}_book.pdf"
GAME_URL = "https://www.nba.com/game/{a}-vs-{h}-{gid}"


def sec(min_str: str) -> int:
    m, s = min_str.split(":")
    return int(m) * 60 + int(s)


# (jersey, name, pos, min, pts, reb, ast, fg, fg3, ft, status)  — status None if played
GAMES: dict[str, dict] = {
    "0022600245": {
        "matchup": "ORL@BOS", "away": "ORL", "home": "BOS", "arena": "TD Garden, Boston, MA",
        "away_pts": 115, "home_pts": 105,
        "away_q": [20, 30, 25, 40], "home_q": [17, 24, 36, 28],
        "teams": {
            "ORL": [
                (0, "Anthony Black", "F", "32:56", 20, 2, 7, 7, 3, 3, None),
                (22, "Franz Wagner", "F", "37:34", 21, 8, 9, 8, 0, 5, None),
                (34, "Wendell Carter Jr.", "C", "28:05", 10, 3, 1, 3, 1, 3, None),
                (3, "Desmond Bane", "G", "39:13", 24, 8, 5, 8, 3, 5, None),
                (4, "Jalen Suggs", "G", "24:37", 12, 6, 4, 5, 2, 0, None),
                (8, "Jamal Cain", None, "14:39", 2, 5, 0, 0, 0, 2, None),
                (23, "Tristan da Silva", None, "31:13", 13, 6, 3, 4, 3, 2, None),
                (35, "Goga Bitadze", None, "19:55", 10, 6, 1, 5, 0, 0, None),
                (2, "Jevon Carter", None, "11:48", 3, 2, 1, 1, 1, 0, None),
                (30, "Alex Morales", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
                (11, "Jase Richardson", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
                (9, "Nikola Vucevic", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
            ],
            "BOS": [
                (13, "Paul George", "F", "36:05", 22, 8, 3, 7, 5, 3, None),
                (0, "Jayson Tatum", "F", "36:03", 24, 12, 4, 9, 3, 3, None),
                (52, "Luka Garza", "C", "17:33", 3, 0, 4, 1, 1, 0, None),
                (27, "Jordan Walsh", "G", "16:36", 6, 2, 0, 2, 2, 0, None),
                (9, "Derrick White", "G", "31:52", 9, 3, 2, 4, 1, 0, None),
                (11, "Payton Pritchard", None, "31:40", 21, 4, 5, 7, 4, 3, None),
                (4, "Mitchell Robinson", None, "17:44", 4, 5, 2, 2, 0, 0, None),
                (55, "Baylor Scheierman", None, "11:20", 0, 1, 1, 0, 0, 0, None),
                (30, "Sam Hauser", None, "24:54", 12, 1, 2, 4, 4, 0, None),
                (12, "Chris Cenac Jr.", None, "12:10", 4, 2, 1, 2, 0, 0, None),
                (28, "Hugo Gonzalez", None, "04:04", 0, 2, 0, 0, 0, 0, None),
                (45, "Mike Conley", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
                (8, "Ron Harper Jr.", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
                (20, "Dillon Mitchell", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
                (77, "Amari Williams", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
            ],
        },
        "club_totals": {
            "ORL": {"pts": 115, "reb": 46, "or": 10, "dr": 36, "ast": 31, "fg": 41, "fg3": 13, "ft": 20},
            "BOS": {"pts": 105, "reb": 40, "or": 9, "dr": 31, "ast": 24, "fg": 38, "fg3": 20, "ft": 9},
        },
        "inactives": {
            "ORL": ["Banchero (Injury/Illness - Right High Ankle Sprain)", "Castleton",
                    "Isaac (Injury/Illness - Left Knee Injury Management)",
                    "Nelson (Injury/Illness - Left Ankle Injury Recovery)",
                    "Penda (Injury/Illness - Right Partially Torn Hamstring)"],
            "BOS": ["Carter", "Queta (Rest)"],
        },
        "notes": ["The PDF-to-text rendering duplicated the Magic SCORE BY PERIOD row with a "
                  "mangled label ('PERIO'); the clean Trail-Blazers-style table printed both "
                  "clubs and both rows were used only after summing to the finals."],
    },
    "0022600246": {
        "matchup": "CHI@CLE", "away": "CHI", "home": "CLE", "arena": "Rocket Arena, Cleveland, OH",
        "away_pts": 115, "home_pts": 126,
        "away_q": [31, 17, 31, 36], "home_q": [25, 32, 31, 38],
        "teams": {
            "CHI": [
                (14, "Matas Buzelis", "F", "31:26", 23, 3, 0, 8, 3, 4, None),
                (35, "Isaac Okoro", "F", "32:11", 13, 6, 2, 5, 3, 0, None),
                (25, "Jalen Smith", "C", "27:45", 17, 11, 3, 6, 3, 2, None),
                (24, "Norman Powell", "G", "32:57", 27, 2, 6, 10, 0, 7, None),
                (3, "Josh Giddey", "G", "23:48", 4, 4, 8, 1, 1, 1, None),
                (9, "Nic Claxton", None, "16:38", 8, 2, 1, 3, 0, 2, None),
                (7, "Buddy Hield", None, "19:06", 6, 4, 2, 2, 2, 0, None),
                (2, "Noa Essengue", None, "13:59", 1, 2, 1, 0, 0, 1, None),
                (30, "Tre Jones", None, "23:00", 16, 2, 6, 6, 0, 4, None),
                (44, "Patrick Williams", None, "12:56", 0, 0, 0, 0, 0, 0, None),
                (15, "Jordan Hawkins", None, "03:37", 0, 0, 1, 0, 0, 0, None),
                (5, "Dailyn Swain", None, "01:50", 0, 1, 0, 0, 0, 0, None),
                (11, "Leonard Miller", None, "00:47", 0, 0, 0, 0, 0, 0, None),
                (12, "Zach Collins", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
            ],
            "CLE": [
                (24, "Tyrese Proctor", "F", "28:54", 17, 3, 2, 6, 2, 3, None),
                (8, "Peyton Watson", "F", "21:31", 14, 4, 0, 5, 2, 2, None),
                (31, "Jarrett Allen", "C", "30:12", 13, 14, 3, 6, 0, 1, None),
                (45, "Donovan Mitchell", "G", "35:51", 39, 4, 4, 16, 2, 5, None),
                (1, "James Harden", "G", "34:22", 9, 4, 10, 3, 2, 1, None),
                (15, "Meleek Thomas", None, "30:03", 10, 6, 3, 4, 1, 1, None),
                (33, "Mario Hezonja", None, "14:46", 9, 4, 2, 4, 1, 0, None),
                (3, "Thomas Bryant", None, "17:48", 9, 5, 4, 4, 0, 1, None),
                (9, "Craig Porter Jr.", None, "13:38", 2, 1, 3, 1, 0, 0, None),
                (77, "Norchad Omier", None, "12:55", 4, 6, 2, 2, 0, 0, None),
                (18, "Khalifa Diop", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
                (12, "Riley Minix", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
            ],
        },
        "club_totals": {
            "CHI": {"pts": 115, "reb": 37, "or": 11, "dr": 26, "ast": 30, "fg": 41, "fg3": 12, "ft": 21},
            "CLE": {"pts": 126, "reb": 51, "or": 15, "dr": 36, "ast": 33, "fg": 51, "fg3": 10, "ft": 14},
        },
        "inactives": {
            "CHI": ["Awaka (Injury/Illness - Disc Irritation)", "Robinson (G League - On Assignment)",
                    "Sellers (G League - Two-Way)", "Wilson (Injury/Illness - Right Metacarpal Fracture)"],
            "CLE": ["Merrill (Injury/Illness - Right Elbow Injury Management)",
                    "Mobley (Injury/Illness - Left Great Toe Sprain)",
                    "Tomlin (Injury/Illness - Low Back Stress Reaction)",
                    "Tyson (Injury/Illness - Right Ankle Injury Management)",
                    "Udeh, Jr. (G League - Two-Way)"],
        },
    },
    "0022600247": {
        "matchup": "MEM@WAS", "away": "MEM", "home": "WAS", "arena": "Capital One Arena, Washington, DC",
        "away_pts": 136, "home_pts": 120,
        "away_q": [33, 26, 42, 35], "home_q": [35, 34, 18, 33],
        "teams": {
            "MEM": [
                (0, "Jaylen Wells", "F", "26:52", 8, 4, 3, 3, 2, 0, None),
                (27, "Cameron Boozer", "F", "29:23", 29, 7, 7, 10, 7, 2, None),
                (14, "Zach Edey", "C", "20:43", 23, 10, 1, 10, 0, 3, None),
                (23, "Cedric Coward", "G", "26:50", 18, 8, 6, 7, 2, 2, None),
                (24, "Cam Spencer", "G", "31:40", 12, 6, 9, 4, 1, 3, None),
                (3, "Jerami Grant", None, "23:06", 8, 1, 2, 3, 2, 0, None),
                (22, "Taylor Hendricks", None, "18:30", 9, 3, 0, 4, 1, 0, None),
                (10, "Javon Small", None, "28:57", 12, 5, 12, 6, 0, 0, None),
                (18, "Olivier-Maxence Prosper", None, "16:00", 12, 0, 1, 4, 1, 3, None),
                (41, "Quinten Post", None, "08:32", 5, 3, 0, 2, 0, 1, None),
                (17, "Kris Murray", None, "06:09", 0, 1, 0, 0, 0, 0, None),
                (21, "Jahmai Mashack", None, "02:12", 0, 0, 1, 0, 0, 0, None),
                (35, "Karim Lopez", None, "01:06", 0, 0, 0, 0, 0, 0, None),
            ],
            "WAS": [
                (18, "Kyshawn George", "F", "38:01", 18, 6, 1, 7, 2, 2, None),
                (23, "Anthony Davis", "F", "34:41", 23, 4, 0, 8, 0, 7, None),
                (20, "Alex Sarr", "C", "30:44", 6, 4, 1, 2, 1, 1, None),
                (4, "AJ Dybantsa", "G", "32:06", 21, 5, 3, 7, 1, 6, None),
                (3, "Trae Young", "G", "33:02", 13, 2, 12, 3, 2, 5, None),
                (0, "Bilal Coulibaly", None, "15:34", 11, 5, 0, 4, 1, 2, None),
                (12, "Tre Johnson", None, "20:43", 9, 1, 3, 3, 2, 1, None),
                (22, "Khris Middleton", None, "17:59", 9, 3, 3, 3, 2, 1, None),
                (8, "Deandre Ayton", None, "08:22", 4, 0, 1, 2, 0, 0, None),
                (7, "Bub Carrington", None, "02:12", 0, 0, 0, 0, 0, 0, None),
                (16, "Anthony Gill", None, "02:12", 2, 0, 0, 0, 0, 2, None),
                (1, "Tre Mann", None, "02:12", 2, 0, 1, 0, 0, 2, None),
                (27, "Will Riley", None, "02:12", 2, 1, 0, 1, 0, 0, None),
            ],
        },
        "club_totals": {
            "MEM": {"pts": 136, "reb": 48, "or": 15, "dr": 33, "ast": 42, "fg": 53, "fg3": 16, "ft": 14},
            "WAS": {"pts": 120, "reb": 31, "or": 11, "dr": 20, "ast": 25, "fg": 40, "fg3": 11, "ft": 29},
        },
        "inactives": {
            "MEM": ["Jackson (Injury/Illness - Left 5th Metatarsal Fracture)",
                    "Jerome (Injury/Illness - Right Hip Soreness)",
                    "Pippen Jr. (Injury/Illness - Lumbar Disc Herniation)",
                    "Saunders (Injury/Illness - Right Knee Surgery)",
                    "Stewart (Injury/Illness - Illness)"],
            "WAS": ["Beekman (Injury/Illness - Right AC Joint Injury)",
                    "Champagnie (Injury/Illness - Right Foot Surgery)", "Okpara (G League - Two-Way)",
                    "Vukcevic (Injury/Illness - Left Hip Impingement)",
                    "Watkins (Injury/Illness - Left ACL Repair / Surgery)"],
        },
        "notes": ["The gamebook prints a MEMO: 'MEM: C. Boozer Career High Points (Prev. 27)'."],
    },
    "0022600248": {
        "matchup": "PHI@BKN", "away": "PHI", "home": "BKN", "arena": "Barclays Center, Brooklyn, NY",
        "away_pts": 135, "home_pts": 123,
        "away_q": [33, 45, 27, 30], "home_q": [26, 33, 36, 28],
        "teams": {
            "PHI": [
                (7, "Jaylen Brown", "F", "33:15", 31, 13, 4, 9, 3, 10, None),
                (45, "Dean Wade", "F", "32:01", 8, 11, 1, 3, 1, 1, None),
                (21, "Joel Embiid", "C", "32:10", 37, 5, 1, 13, 2, 9, None),
                (77, "VJ Edgecombe", "G", "33:05", 14, 9, 4, 4, 1, 5, None),
                (0, "Tyrese Maxey", "G", "34:55", 24, 1, 9, 7, 4, 6, None),
                (1, "Kentavious Caldwell-Pope", None, "31:17", 0, 2, 3, 0, 0, 0, None),
                (5, "Anfernee Simons", None, "25:57", 9, 1, 2, 4, 1, 0, None),
                (33, "Jabari Walker", None, "16:26", 12, 5, 1, 5, 1, 1, None),
                (99, "Tacko Fall", None, "00:19", 0, 0, 0, 0, 0, 0, None),
                (0, "Labaron Philon Jr.", None, "00:19", 0, 0, 0, 0, 0, 0, None),
                (12, "Rayan Rupert", None, "00:19", 0, 0, 0, 0, 0, 0, None),
                (11, "Justin Edwards", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
            ],
            "BKN": [
                (17, "Michael Porter Jr.", "F", "39:59", 25, 6, 2, 8, 2, 7, None),
                (30, "Julius Randle", "F", "33:54", 33, 6, 1, 13, 2, 5, None),
                (20, "Day'Ron Sharpe", "C", "25:25", 6, 9, 5, 3, 0, 0, None),
                (8, "Egor Demin", "G", "26:06", 9, 3, 4, 3, 2, 1, None),
                (10, "Nolan Traore", "G", "29:57", 23, 1, 4, 7, 2, 7, None),
                (1, "Keon Ellis", None, "20:12", 8, 2, 0, 3, 2, 0, None),
                (13, "Moritz Wagner", None, "10:12", 4, 5, 1, 2, 0, 0, None),
                (0, "Mikel Brown Jr.", None, "18:03", 3, 1, 5, 1, 1, 0, None),
                (21, "Noah Clowney", None, "24:20", 9, 3, 3, 3, 1, 2, None),
                (2, "Danny Wolf", None, "11:02", 3, 2, 1, 1, 1, 0, None),
                (31, "Chaney Johnson", None, "00:52", 0, 0, 0, 0, 0, 0, None),
                (14, "Terance Mann", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
            ],
        },
        "club_totals": {
            "PHI": {"pts": 135, "reb": 47, "or": 14, "dr": 33, "ast": 25, "fg": 45, "fg3": 13, "ft": 32},
            "BKN": {"pts": 123, "reb": 38, "or": 11, "dr": 27, "ast": 26, "fg": 44, "fg3": 13, "ft": 22},
        },
        "inactives": {
            "PHI": ["Barlow (Injury/Illness - Low Back Stress Reaction)",
                    "Bona (Injury/Illness - Cervical Spine Sprain)",
                    "Hukporti (Injury/Illness - Right Achilles Tendon Rupture / Tear)",
                    "James (Injury/Illness - Low Back/Sciatica Management)", "Love"],
            "BKN": ["Bilodeau (G League - Two-Way)", "Jefferson (G League - On Assignment)",
                    "Nelson (G League - Two-Way)", "Powell (G League - On Assignment)",
                    "Saraf (G League - On Assignment)"],
        },
        "notes": ["The gamebook prints jersey #7 as 'Jaylen Brown' on Philadelphia and lists "
                  "'Ryan Rupert' in one table and 'Rayan Rupert' in another for the same "
                  "#12 player; the majority official spelling (Rayan Rupert) is recorded and "
                  "the inconsistency is flagged, not folded silently."],
    },
    "0022600249": {
        "matchup": "HOU@MIA", "away": "HOU", "home": "MIA", "arena": "Kaseya Center, Miami, FL",
        "away_pts": 110, "home_pts": 128,
        "away_q": [15, 31, 35, 29], "home_q": [29, 33, 39, 27],
        "teams": {
            "HOU": [
                (10, "Jabari Smith Jr.", "F", "31:56", 12, 10, 1, 4, 1, 3, None),
                (17, "Tari Eason", "F", "27:28", 7, 7, 3, 2, 0, 3, None),
                (28, "Alperen Sengun", "C", "29:48", 23, 7, 2, 8, 1, 6, None),
                (7, "Kevin Durant", "G", "28:42", 22, 2, 3, 8, 2, 4, None),
                (5, "Fred VanVleet", "G", "25:56", 8, 5, 6, 3, 2, 0, None),
                (31, "Bogdan Bogdanovic", None, "25:47", 6, 0, 1, 2, 2, 0, None),
                (15, "Reed Sheppard", None, "18:51", 5, 2, 2, 2, 1, 0, None),
                (27, "Isaiah Crawford", None, "21:14", 11, 10, 3, 3, 1, 4, None),
                (8, "Jae'Sean Tate", None, "12:00", 3, 3, 2, 1, 0, 1, None),
                (2, "Bruce Thornton", None, "12:00", 7, 0, 0, 2, 0, 3, None),
                (9, "Oscar Tshiebwe", None, "06:18", 6, 6, 0, 3, 0, 0, None),
                (12, "Steven Adams", None, None, None, None, None, None, None, None, "DND - Left Lower Leg Injury Management"),
                (36, "Marcus Smart", None, None, None, None, None, None, None, None, "NWT - League Suspension"),
                (1, "Amen Thompson", None, None, None, None, None, None, None, None, "DND - Left Knee Soreness"),
            ],
            "MIA": [
                (11, "Klay Thompson", "F", "22:24", 17, 0, 2, 5, 5, 2, None),
                (7, "Giannis Antetokounmpo", "F", "28:32", 20, 13, 6, 8, 0, 4, None),
                (13, "Bam Adebayo", "C", "15:31", 4, 1, 2, 1, 0, 2, None),
                (15, "Myron Gardner", "G", "24:28", 14, 2, 3, 5, 4, 0, None),
                (2, "Davion Mitchell", "G", "33:16", 16, 3, 10, 7, 1, 1, None),
                (4, "Ryan Conwell", None, "30:27", 14, 2, 3, 3, 1, 7, None),
                (95, "Bobby Portis Jr.", None, "23:20", 16, 6, 0, 7, 2, 0, None),
                (22, "Andrew Wiggins", None, "34:14", 17, 5, 1, 6, 3, 2, None),
                (0, "Simone Fontecchio", None, "19:09", 10, 6, 2, 4, 2, 0, None),
                (24, "Tre Donaldson", None, "02:53", 0, 0, 0, 0, 0, 0, None),
                (16, "Keshad Johnson", None, "02:53", 0, 2, 0, 0, 0, 0, None),
                (8, "Nick Richards", None, "02:53", 0, 0, 0, 0, 0, 0, None),
                (10, "Tim Hardaway Jr.", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
                (9, "Pelle Larsson", None, None, None, None, None, None, None, None, "DND - Illness"),
                (12, "Dru Smith", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
            ],
        },
        "club_totals": {
            "HOU": {"pts": 110, "reb": 52, "or": 21, "dr": 31, "ast": 23, "fg": 38, "fg3": 10, "ft": 24},
            "MIA": {"pts": 128, "reb": 40, "or": 13, "dr": 27, "ast": 29, "fg": 46, "fg3": 18, "ft": 18},
        },
        "inactives": {
            "HOU": ["Capela (Injury/Illness - Right Ankle Sprain)", "Copeland (G League - Two-Way)",
                    "Phillips (G League - Two-Way)"],
            "MIA": ["Goldin (G League - Two-Way)", "Jovic (Injury/Illness - Illness)"],
        },
        "notes": [
            "The gamebook's single SCORE BY PERIOD extraction dropped the Rockets period row; "
            "the four Houston period scores were read from the official per-period team totals "
            "rows of the same gamebook (Q1 15, Q2 31, Q3 35, Q4 29; each row's printed points "
            "identity 2*(FG-3P)+3*3P+FT was checked; the period rows sum to the final 110). "
            "Miami's period row read directly: 29 33 39 27.",
            "Houston bench rows for Bogdanovic, Sheppard and Tate, and Miami rows for Keshad "
            "Johnson and Tre Donaldson, had one cell dropped by PDF-to-text rendering; each was "
            "confirmed against the official box-score page for this game before commit.",
        ],
    },
    "0022600250": {
        "matchup": "POR@MIN", "away": "POR", "home": "MIN", "arena": "Target Center, Minneapolis, MN",
        "away_pts": 98, "home_pts": 106,
        "away_q": [26, 25, 22, 25], "home_q": [26, 33, 28, 19],
        "teams": {
            "POR": [
                (91, "Sidy Cissoko", "F", "27:35", 5, 4, 3, 2, 1, 0, None),
                (33, "Toumani Camara", "F", "25:30", 3, 0, 0, 1, 0, 1, None),
                (23, "Donovan Clingan", "C", "22:27", 10, 10, 1, 5, 0, 0, None),
                (8, "Deni Avdija", "G", "29:50", 27, 8, 4, 11, 3, 2, None),
                (0, "Damian Lillard", "G", "23:36", 9, 2, 4, 2, 2, 3, None),
                (0, "Scoot Henderson", None, "22:40", 10, 1, 0, 4, 0, 2, None),
                (5, "Jrue Holiday", None, "25:09", 10, 4, 3, 3, 2, 2, None),
                (35, "Robert Williams III", None, "15:29", 2, 5, 2, 1, 0, 0, None),
                (10, "Branden Carlson", None, "14:27", 5, 6, 1, 2, 1, 0, None),
                (29, "Jayson Kent", None, "10:55", 8, 0, 0, 3, 2, 0, None),
                (9, "Micah Potter", None, "07:28", 2, 4, 1, 1, 0, 0, None),
                (2, "John Tonje", None, "07:28", 7, 4, 3, 2, 1, 2, None),
                (16, "Yang Hansen", None, "07:28", 0, 1, 3, 0, 0, 0, None),
            ],
            "MIN": [
                (3, "Jaden McDaniels", "F", "31:09", 13, 6, 3, 5, 0, 3, None),
                (24, "Jonathan Kuminga", "F", "29:24", 13, 9, 1, 5, 1, 2, None),
                (27, "Rudy Gobert", "C", "32:01", 18, 15, 3, 5, 0, 8, None),
                (13, "Ayo Dosunmu", "G", "29:32", 8, 5, 2, 3, 2, 0, None),
                (1, "LaMelo Ball", "G", "23:37", 6, 5, 0, 2, 2, 0, None),
                (19, "Joan Beringer", None, "15:47", 0, 4, 0, 0, 0, 0, None),
                (4, "Terrence Shannon Jr", None, "35:11", 34, 3, 6, 8, 3, 15, None),
                (8, "Bones Hyland", None, "12:31", 5, 1, 5, 2, 0, 1, None),
                (41, "Trey Lyles", None, "19:24", 9, 3, 1, 3, 2, 1, None),
                (33, "Isaiah Evans", None, "03:48", 0, 0, 0, 0, 0, 0, None),
                (15, "Zyon Pullin", None, "03:48", 0, 1, 0, 0, 0, 0, None),
                (9, "Cody Williams", None, "03:48", 0, 1, 0, 0, 0, 0, None),
            ],
        },
        "club_totals": {
            "POR": {"pts": 98, "reb": 49, "or": 12, "dr": 37, "ast": 25, "fg": 37, "fg3": 12, "ft": 12},
            "MIN": {"pts": 106, "reb": 53, "or": 14, "dr": 39, "ast": 21, "fg": 33, "fg3": 10, "ft": 30},
        },
        "inactives": {
            "POR": ["Krejci (Injury/Illness - Left Ankle Fracture)",
                    "Morant (Injury/Illness - Left Hamstring Strain)",
                    "Sharpe (Injury/Illness - Right Knee Surgery)",
                    "Youngblood (Injury/Illness - Right Heel Contusion / Bone Bruise)"],
            "MIN": ["Broome (G League - Two-Way)", "Clark (Injury/Illness - Right Hamstring Strain)",
                    "DiVincenzo (Injury/Illness - Right Achilles Tendon Repair / Surgery)",
                    "Edwards (Injury/Illness - Right Knee Arthroscopy)",
                    "Zikarsky (G League - Two-Way)"],
        },
        "notes": ["The extraction printed a garbled duplicate SCORE BY PERIOD block ('T | 21 | 25 "
                  "| 22 | 25 | 22') before the clean table; only the clean table (Trail Blazers "
                  "26 25 22 25 98 / Timberwolves 26 33 28 19 106) was used, after both rows "
                  "summed to the finals."],
    },
    "0022600251": {
        "matchup": "GSW@NOP", "away": "GSW", "home": "NOP", "arena": "Smoothie King Center, New Orleans, LA",
        "away_pts": 94, "home_pts": 115,
        "away_q": [11, 25, 29, 29], "home_q": [35, 26, 32, 22],
        "teams": {
            "GSW": [
                (1, "Yaxel Lendeborg", "F", "32:39", 28, 8, 3, 9, 2, 8, None),
                (23, "Draymond Green", "F", "24:48", 2, 8, 5, 1, 0, 0, None),
                (20, "Al Horford", "C", "14:28", 0, 5, 0, 0, 0, 0, None),
                (2, "Brandin Podziemski", "G", "29:38", 15, 6, 3, 3, 3, 6, None),
                (18, "LJ Cryer", "G", "24:09", 7, 1, 3, 2, 1, 2, None),
                (32, "Georges Niang", None, "14:24", 0, 4, 2, 0, 0, 0, None),
                (28, "Charles Bassey", None, "15:51", 4, 0, 0, 1, 0, 2, None),
                (8, "De'Anthony Melton", None, "20:37", 8, 2, 1, 3, 2, 0, None),
                (15, "Gui Santos", None, "18:56", 12, 7, 2, 2, 1, 7, None),
                (3, "Will Richard", None, "23:25", 11, 3, 1, 4, 2, 1, None),
                (0, "Gary Payton II", None, "07:41", 2, 0, 0, 1, 0, 0, None),
                (45, "Graham Ike", None, "07:41", 3, 5, 1, 1, 0, 1, None),
                (33, "Malevy Leons", None, "05:43", 2, 1, 0, 1, 0, 0, None),
            ],
            "NOP": [
                (41, "Saddiq Bey", "F", "32:35", 23, 6, 3, 8, 5, 2, None),
                (1, "Zion Williamson", "F", "24:57", 16, 6, 2, 6, 0, 4, None),
                (21, "Yves Missi", "C", "22:54", 6, 14, 1, 3, 0, 0, None),
                (2, "Herbert Jones", "G", "23:46", 8, 2, 3, 3, 2, 0, None),
                (0, "Jeremiah Fears", "G", "29:07", 19, 10, 10, 6, 1, 6, None),
                (3, "Jordan Poole", None, "30:46", 11, 2, 5, 3, 1, 4, None),
                (17, "Karlo Matkovic", None, "20:06", 3, 2, 0, 1, 0, 1, None),
                (22, "Derik Queen", None, "20:37", 17, 10, 0, 6, 4, 1, None),
                (10, "Jaron Pierre Jr.", None, "19:28", 10, 3, 0, 4, 2, 0, None),
                (14, "AJ Johnson", None, "05:43", 0, 0, 1, 0, 0, 0, None),
                (8, "Malik Dia", None, "05:01", 2, 1, 0, 1, 0, 0, None),
                (13, "Julian Reese", None, "05:01", 0, 1, 0, 0, 0, 0, None),
                (6, "DeAndre Jordan", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
            ],
        },
        "club_totals": {
            "GSW": {"pts": 94, "reb": 50, "or": 14, "dr": 36, "ast": 21, "fg": 28, "fg3": 11, "ft": 27},
            "NOP": {"pts": 115, "reb": 57, "or": 19, "dr": 38, "ast": 25, "fg": 41, "fg3": 15, "ft": 18},
        },
        "inactives": {
            "GSW": ["Butler III (Injury/Illness - Right ACL Repair / Surgery)",
                    "Curry (Injury/Illness - Right Oblique Tear)",
                    "Moody (Injury/Illness - Left Patellar Tendon Repair / Surgery)",
                    "Porzingis", "Williams (Injury/Illness - Left Hamstring Strain)"],
            "NOP": ["Mathurin (Injury/Illness - Left Plantar Fasciitis)",
                    "McGowens (Injury/Illness - Left Elbow Infection)",
                    "Murphy III (Injury/Illness - Bilateral Patellar Tendinopathy)",
                    "Murray (Injury/Illness - Left Ankle Sprain)",
                    "Watford (Injury/Illness - Right Ankle Sprain)"],
        },
        "notes": ["The gamebook inactive line prints 'Porzingis' with no designation text before "
                  "the line breaks to 'Williams'; the designation for Porzingis is not readable "
                  "in the extraction and is left without one rather than guessed."],
    },
    "0022600252": {
        "matchup": "PHX@DEN", "away": "PHX", "home": "DEN", "arena": "Ball Arena, Denver, CO",
        "away_pts": 117, "home_pts": 105,
        "away_q": [20, 36, 34, 27], "home_q": [24, 29, 29, 23],
        "teams": {
            "PHX": [
                (3, "Dillon Brooks", "F", "27:14", 15, 4, 4, 6, 3, 0, None),
                (22, "Miles Bridges", "F", "28:42", 16, 8, 2, 7, 2, 0, None),
                (11, "Oso Ighodaro", "C", "33:03", 8, 11, 3, 3, 0, 2, None),
                (4, "Jalen Green", "G", "26:31", 16, 5, 3, 5, 2, 4, None),
                (15, "Devin Booker", "G", "37:16", 20, 4, 8, 5, 1, 9, None),
                (23, "Jordan Goodwin", None, "19:52", 11, 6, 2, 5, 1, 0, None),
                (0, "Ryan Dunn", None, "11:35", 5, 1, 0, 2, 1, 0, None),
                (12, "Collin Gillespie", None, "26:20", 10, 3, 3, 4, 2, 0, None),
                (10, "Khaman Maluach", None, "10:48", 4, 6, 0, 2, 0, 0, None),
                (8, "Luke Kennard", None, "17:23", 12, 2, 0, 4, 4, 0, None),
                (18, "Koa Peat", None, "01:16", 0, 1, 0, 0, 0, 0, None),
                (17, "Jamaree Bouyea", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
                (20, "Rasheer Fleming", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
                (26, "Duop Reath", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
                (61, "Pat Spencer", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
            ],
            "DEN": [
                (23, "Cameron Johnson", "F", "27:10", 9, 0, 1, 4, 0, 1, None),
                (32, "Aaron Gordon", "F", "24:12", 11, 1, 1, 4, 2, 1, None),
                (15, "Nikola Jokic", "C", "38:00", 28, 15, 7, 12, 2, 2, None),
                (0, "Christian Braun", "G", "33:17", 10, 3, 3, 4, 2, 0, None),
                (27, "Jamal Murray", "G", "34:41", 28, 4, 4, 9, 1, 9, None),
                (7, "Trevon Brazile", None, "23:12", 9, 4, 0, 4, 1, 0, None),
                (21, "Spencer Jones", None, "21:22", 4, 3, 3, 1, 1, 1, None),
                (10, "DeMar DeRozan", None, "14:08", 2, 1, 1, 1, 0, 0, None),
                (5, "Tyus Jones", None, "10:08", 0, 1, 2, 0, 0, 0, None),
                (3, "Marvin Bagley III", None, "10:00", 4, 2, 0, 1, 0, 2, None),
                (13, "Bryce Hopkins", None, "03:50", 0, 1, 0, 0, 0, 0, None),
                (11, "Alpha Diallo", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
                (22, "Zeke Nnaji", None, None, None, None, None, None, None, None, "DNP - Coach's Decision"),
            ],
        },
        "club_totals": {
            "PHX": {"pts": 117, "reb": 51, "or": 18, "dr": 33, "ast": 25, "fg": 43, "fg3": 16, "ft": 15},
            "DEN": {"pts": 105, "reb": 35, "or": 9, "dr": 26, "ast": 22, "fg": 40, "fg3": 9, "ft": 16},
        },
        "inactives": {
            "PHX": ["Timme (G League - Two-Way)", "Williams (Injury/Illness - Left Shoulder Surgery)"],
            "DEN": ["Holmes II (G League - On Assignment)", "Nembhard (G League - Two-Way)",
                    "Strawther (Injury/Illness - Left Knee Sprain)", "Whitmore (G League - Two-Way)"],
        },
        "notes": ["The gamebook prints the #5 Denver player as 'Tys Jones' in one rendering; the "
                  "official box score spells the player 'Tyus Jones'. The box-score spelling is "
                  "recorded and the gamebook inconsistency is flagged, not folded silently."],
    },
}


def validate() -> list[str]:
    errs = []
    for gid, g in GAMES.items():
        for tri, rows in g["teams"].items():
            ct = g["club_totals"][tri]
            s_pts = s_reb = s_ast = s_fg = s_fg3 = s_ft = s_min = 0
            for (j, name, pos, mins, pts, reb, ast, fg, fg3, ft, status) in rows:
                if mins is None:
                    if status is None:
                        errs.append(f"{gid} {tri} {name}: no minutes but no status")
                    continue
                s_min += sec(mins)
                if pts is None:
                    errs.append(f"{gid} {tri} {name}: played but pts unread")
                    continue
                s_pts += pts
                if 2 * (fg - fg3) + 3 * fg3 + ft != pts:
                    errs.append(f"{gid} {tri} {name}: identity {pts} != 2*({fg}-{fg3})+3*{fg3}+{ft}")
                s_fg += fg
                s_fg3 += fg3
                s_ft += ft
                if reb is not None:
                    s_reb += reb
                if ast is not None:
                    s_ast += ast
            if s_pts != ct["pts"]:
                errs.append(f"{gid} {tri}: player points {s_pts} != club total {ct['pts']}")
            if s_reb != ct["reb"]:
                errs.append(f"{gid} {tri}: player rebounds {s_reb} != club total {ct['reb']}")
            if s_ast != ct["ast"]:
                errs.append(f"{gid} {tri}: player assists {s_ast} != club total {ct['ast']}")
            if s_fg != ct["fg"] or s_fg3 != ct["fg3"] or s_ft != ct["ft"]:
                errs.append(f"{gid} {tri}: shooting sums ({s_fg}/{s_fg3}/{s_ft}) != club "
                            f"({ct['fg']}/{ct['fg3']}/{ct['ft']})")
            if abs(s_min - 14400) > 3:
                errs.append(f"{gid} {tri}: minutes {s_min}s != 240:00")
        for side, pts in (("away", g["away_pts"]), ("home", g["home_pts"])):
            q = g[f"{side}_q"]
            if sum(q) != pts:
                errs.append(f"{gid} {side} quarters {q} sum {sum(q)} != final {pts}")
    return errs


def build_transcript() -> dict:
    games = []
    for gid in sorted(GAMES):
        g = GAMES[gid]
        rec = {
            "game_id": gid, "date": DATE, "matchup": g["matchup"],
            "away": g["away"], "home": g["home"], "arena": g["arena"],
            "source_url": GB.format(m=g["matchup"].replace("@", "")),
            "box_score_url": GAME_URL.format(a=g["away"].lower(), h=g["home"].lower(), gid=gid),
            "final": {"away": g["away_pts"], "home": g["home_pts"]},
            "quarters": {"away": g["away_q"], "home": g["home_q"], "ot": {"away": [], "home": []}},
            "inactives": g["inactives"],
            "club_totals": {tri: {"min_sec": 14400, "pts": ct["pts"], "reb": ct["reb"],
                                  "or": ct["or"], "dr": ct["dr"], "ast": ct["ast"],
                                  "fg": ct["fg"], "fg3": ct["fg3"], "ft": ct["ft"]}
                            for tri, ct in g["club_totals"].items()},
            "teams": {},
        }
        for tri, rows in g["teams"].items():
            players = []
            for (j, name, pos, mins, pts, reb, ast, fg, fg3, ft, status) in rows:
                players.append({
                    "jersey": j, "name": name, "pos": pos,
                    "min": mins, "min_sec": sec(mins) if mins else None,
                    "pts": pts, "reb": reb, "ast": ast, "fg": fg, "fg3": fg3, "ft": ft,
                    "status": status,
                })
            rec["teams"][tri] = {"side": "away" if tri == g["away"] else "home",
                                 "opp": g["home"] if tri == g["away"] else g["away"],
                                 "players": players}
        games.append(rec)
    return {
        "schema": "nba2.v5.gamebook-transcript.v1",
        "game_date": DATE,
        "session": SESSION,
        "retrieved_window_utc": RETRIEVED,
        "retrieval_method": METHOD,
        "source_class": "official",
        "columns": ["jersey", "name", "pos", "min", "min_sec", "pts", "reb", "ast", "fg", "fg3", "ft", "status"],
        "notes": [n for gid in sorted(GAMES) for n in GAMES[gid].get("notes", [])] + [
            "All eight finals match the official schedule page for 2026-11-16 (list_url in the "
            "results feed); every club's period row sums to its final; every player row passes "
            "the points identity and the club sums (pts/reb/ast/FG/3P/FT) and minutes sum to "
            "240:00 within the 3-second rounding tolerance.",
            "No game went to overtime on this date; OT arrays are empty.",
        ],
        "games": games,
    }


def build_results_feed() -> dict:
    records = []
    for gid in sorted(GAMES):
        g = GAMES[gid]
        records.append({
            "game_id": gid, "date": DATE, "away": g["away"], "home": g["home"],
            "away_pts": g["away_pts"], "home_pts": g["home_pts"], "ot_periods": 0,
            "status": "final",
            "away_q": g["away_q"], "home_q": g["home_q"],
            "away_quarters": g["away_q"], "home_quarters": g["home_q"],
            "home_margin": g["home_pts"] - g["away_pts"],
            "total_pts": g["home_pts"] + g["away_pts"],
            "final_source_url": GAME_URL.format(a=g["away"].lower(), h=g["home"].lower(), gid=gid),
            "source_url": GAME_URL.format(a=g["away"].lower(), h=g["home"].lower(), gid=gid),
            "gamebook_url": GB.format(m=g["matchup"].replace("@", "")),
            "quarter_status": "read",
            "quarter_note": (f"{g['away']} {'+'.join(map(str, g['away_q']))} = {g['away_pts']}; "
                             f"{g['home']} {'+'.join(map(str, g['home_q']))} = {g['home_pts']}"),
            "list_url": LIST_URL,
        })
    return {
        "schema": "nba2.results-feed.v3",
        "game_date": DATE,
        "retrieved_utc": RETRIEVED,
        "retrieval_method": METHOD,
        "settle_rule": (
            "A game is SETTLED only when its official gamebook period row sums to the final for "
            "that club AND the final matches the official schedule listing. A club whose period "
            "row was not transcribed carries null quarters and is shown as unverified; nothing "
            "is back-solved from the final."),
        "source_page": LIST_URL,
        "records": records,
    }


def main() -> int:
    errs = validate()
    if errs:
        for e in errs:
            print("VALIDATION FAIL:", e)
        return 1
    out_results = ROOT / "data" / "raw" / "results" / f"results_{DATE}.json"
    out_transcript = ROOT / "data" / "v5" / f"gamebooks_{DATE}.json"
    out_results.write_text(json.dumps(build_results_feed(), indent=1) + "\n", encoding="utf-8")
    out_transcript.write_text(json.dumps(build_transcript(), indent=1) + "\n", encoding="utf-8")
    n_rows = sum(len(r["players"]) for g in build_transcript()["games"] for r in g["teams"].values())
    print(f"OK: {out_results.name} ({len(build_results_feed()['records'])} games), "
          f"{out_transcript.name} ({len(GAMES)} games, {n_rows} player rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
