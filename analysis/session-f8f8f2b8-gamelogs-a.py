"""Session arena/f8f8f2b8-nba2 — official per-player box scores, batch A (2026-11-13).

Verbatim transcription of the **official gamebook PDF** published by the NBA for each game:

    https://statsdmz.nba.com/pdfs/<YYYYMMDD>/<YYYYMMDD>_<AWAY><HOME>_book.pdf

Only the fields the brief asks for are carried: minutes, points, rebounds, assists, opponent
(plus the player's position and the DNP / inactive lists, both of which the PDF prints and both
of which matter for rotation work). Nothing is derived, rounded or filled in.

`played` tuples are (player, POS, MIN as printed, PTS, REB, AST).
`quarters` is None where the PDF's SCORE BY PERIOD table did not extract cleanly — that cell is
left blank and flagged, never guessed.
"""

GAMES = [
    {
        "date": "2026-11-13",
        "game_id": "0022600034",
        "away": "NYK",
        "home": "IND",
        "away_pts": 104,
        "home_pts": 106,
        "quarters": {"NYK": [27, 22, 35, 20], "IND": [26, 32, 27, 21]},
        "arena": "Gainbridge Fieldhouse",
        "city": "Indianapolis, IN",
        "attendance": "17274 (Sellout)",
        "officials": "#64 Justin Van Duyne, #7 Ed Malloy, #73 Intae Hwang",
        "gamebook_url": "https://statsdmz.nba.com/pdfs/20261113/20261113_NYKIND_book.pdf",
        "game_url": "https://www.nba.com/game/nyk-vs-ind-0022600034",
        "teams": {
            "NYK": {
                "played": [
                    ("Josh Hart", "F", "23:13", 0, 5, 4),
                    ("OG Anunoby", "F", "33:20", 11, 2, 1),
                    ("Karl-Anthony Towns", "C", "33:53", 23, 15, 5),
                    ("Mikal Bridges", "G", "28:40", 18, 3, 3),
                    ("Jalen Brunson", "G", "35:57", 33, 1, 11),
                    ("Andre Drummond", "", "13:47", 0, 6, 0),
                    ("Tyler Kolek", "", "18:30", 5, 6, 2),
                    ("Miles McBride", "", "21:49", 9, 1, 1),
                    ("Landry Shamet", "", "21:02", 5, 3, 1),
                    ("Jordan Clarkson", "", "08:40", 0, 1, 0),
                    ("Pacôme Dadiet", "", "01:09", 0, 0, 0),
                ],
                "dnp": ["Jose Alvarado", "Mohamed Diawara", "James Wiseman"],
                "inactive": "Akins, Knecht, Nickel",
            },
            "IND": {
                "played": [
                    ("Aaron Nesmith", "F", "32:31", 18, 7, 1),
                    ("Pascal Siakam", "F", "31:58", 19, 3, 2),
                    ("Ivica Zubac", "C", "25:46", 12, 13, 1),
                    ("Kelly Oubre Jr.", "G", "29:52", 16, 5, 0),
                    ("Andrew Nembhard", "G", "33:42", 12, 4, 6),
                    ("Jay Huff", "", "08:17", 8, 1, 0),
                    ("Quenton Jackson", "", "20:18", 3, 5, 4),
                    ("T.J. McConnell", "", "17:20", 6, 3, 7),
                    ("Obi Toppin", "", "16:02", 9, 3, 1),
                    ("Larry Nance Jr.", "", "13:57", 2, 2, 1),
                    ("Jalen Slawson", "", "10:17", 1, 4, 0),
                ],
                "dnp": ["Jarace Walker"],
                "inactive": ("Brown, Furphy (Injury/Illness - Right ACL Repair / Surgery), "
                             "Haliburton (Injury/Illness - Left Hamstring Strain), "
                             "Sheppard (Injury/Illness - Left Meniscus Surgery), Smith"),
            },
        },
    },
    {
        "date": "2026-11-13",
        "game_id": "0022600035",
        "away": "MIL",
        "home": "ORL",
        "away_pts": 99,
        "home_pts": 107,
        # The PDF's SCORE BY PERIOD row for Orlando extracted as "33 33 33 33" (sums to 132,
        # not 107) with a stray "MAGIC 23 29" fragment on the following line. The quarter
        # scores are therefore NOT confirmed for this game: left blank and flagged (I-F8F-06)
        # rather than reconstructed.
        "quarters": None,
        "arena": "Kia Center",
        "city": "Orlando, FL",
        "attendance": None,
        "officials": "#27 Mitchell Ervin, #68 Jacyn Goble, #70 Phenizee Ransom",
        "gamebook_url": "https://statsdmz.nba.com/pdfs/20261113/20261113_MILORL_book.pdf",
        "game_url": "https://www.nba.com/game/mil-vs-orl-0022600035",
        "teams": {
            "MIL": {
                "played": [
                    ("Ousmane Dieng", "F", "04:47", 0, 0, 0),
                    ("Kyle Kuzma", "F", "30:36", 14, 4, 2),
                    ("Myles Turner", "C", "30:43", 14, 11, 3),
                    ("Tyler Herro", "G", "33:46", 18, 1, 2),
                    ("Brayden Burries", "G", "19:04", 3, 4, 3),
                    ("Nate Ament", "", "22:23", 9, 3, 1),
                    ("Jaime Jaquez Jr.", "", "28:16", 22, 6, 4),
                    ("Kel'el Ware", "", "17:17", 10, 6, 1),
                    ("Ryan Rollins", "", "28:56", 8, 10, 2),
                    ("Gary Trent Jr.", "", "16:02", 1, 0, 0),
                    ("AJ Green", "", "08:10", 0, 0, 2),
                ],
                "dnp": ["Kasparas Jakučionis", "Caris LeVert", "Bogoljub Marković",
                        "Jericho Sims"],
                "inactive": "Jones, Nance, Ryan",
            },
            "ORL": {
                "played": [
                    ("Tristan da Silva", "F", "31:10", 12, 6, 2),
                    ("Franz Wagner", "F", "36:05", 35, 9, 12),
                    ("Wendell Carter Jr.", "C", "30:07", 12, 8, 0),
                    ("Desmond Bane", "G", "34:41", 21, 5, 3),
                    ("Anthony Black", "G", "36:35", 5, 2, 5),
                    ("Jalen Suggs", "", "20:54", 3, 2, 3),
                    ("Nikola Vučević", "", "11:10", 2, 3, 0),
                    ("Jevon Carter", "", "17:19", 5, 2, 2),
                    ("Goga Bitadze", "", "17:53", 12, 4, 1),
                    ("Jamal Cain", "", "04:07", 0, 4, 1),
                ],
                "dnp": ["Colin Castleton", "Alex Morales", "Jase Richardson"],
                "inactive": ("Banchero (Injury/Illness - Right High Ankle Sprain), "
                             "Isaac (Injury/Illness - Left Knee Injury Management), "
                             "Nelson (Injury/Illness - Left Ankle Injury Recovery), "
                             "Penda (Injury/Illness - Right Partially Torn Hamstring )"),
            },
        },
    },
]
