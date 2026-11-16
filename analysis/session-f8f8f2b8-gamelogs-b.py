"""Session arena/f8f8f2b8-nba2 — official per-player box scores, batch B (2026-11-13).

Same source and format as batch A: verbatim transcription of the official gamebook PDF.
`ot_periods` is carried because a team's minutes total is 240:00 + 25:00 per overtime, and the
capture gate asserts the player minutes sum to exactly that.
"""

GAMES = [
    {
        "date": "2026-11-13",
        "game_id": "0022600036",
        "away": "CLE",
        "home": "MIA",
        "away_pts": 121,
        "home_pts": 133,
        "ot_periods": 0,
        "quarters": {"CLE": [27, 30, 34, 30], "MIA": [29, 25, 38, 41]},
        "arena": "Kaseya Center",
        "city": "Miami, FL",
        "attendance": "19646 (Sellout)",
        "officials": "#10 John Goble, #29 Mark Lindsay, #80 JD Ralls",
        "gamebook_url": "https://statsdmz.nba.com/pdfs/20261113/20261113_CLEMIA_book.pdf",
        "game_url": "https://www.nba.com/game/cle-vs-mia-0022600036",
        "teams": {
            "CLE": {
                "played": [
                    ("Jaylon Tyson", "F", "29:52", 16, 3, 1),
                    ("Peyton Watson", "F", "30:25", 4, 4, 2),
                    ("Jarrett Allen", "C", "31:40", 9, 8, 1),
                    ("James Harden", "G", "34:49", 20, 6, 8),
                    ("Donovan Mitchell", "G", "32:51", 25, 4, 7),
                    ("Tyrese Proctor", "", "27:20", 22, 4, 3),
                    ("Meleek Thomas", "", "17:54", 12, 3, 5),
                    ("Thomas Bryant", "", "16:20", 9, 1, 1),
                    ("Mario Hezonja", "", "09:21", 4, 4, 0),
                    ("Craig Porter Jr.", "", "09:28", 0, 2, 2),
                ],
                "dnp": ["Riley Minix", "Norchad Omier"],
                "inactive": ("Diop (G League - On Assignment), Merrill (Injury/Illness - Right "
                             "Elbow Injury Management), Mobley (Injury/Illness - Left Great Toe "
                             "- Sprain), Tomlin (Injury/Illness - Low Back Stress Reaction), "
                             "Udeh, Jr. (G League - Two-Way)"),
            },
            "MIA": {
                "played": [
                    ("Myron Gardner", "F", "19:19", 0, 4, 2),
                    ("Giannis Antetokounmpo", "F", "31:00", 37, 9, 2),
                    ("Bam Adebayo", "C", "38:05", 37, 14, 3),
                    ("Tim Hardaway Jr.", "G", "20:09", 4, 3, 2),
                    ("Davion Mitchell", "G", "38:56", 22, 5, 17),
                    ("Ryan Conwell", "", "32:45", 20, 5, 2),
                    ("Bobby Portis Jr.", "", "15:03", 5, 3, 2),
                    ("Andrew Wiggins", "", "31:33", 8, 3, 4),
                    ("Dru Smith", "", "05:44", 0, 0, 1),
                    ("Simone Fontecchio", "", "07:26", 0, 0, 2),
                ],
                "dnp": ["Tre Donaldson", "Keshad Johnson", "Nikola Jović", "Nick Richards",
                        "Klay Thompson"],
                "inactive": "Goldin (G League - Two-Way), Larsson (Injury/Illness - Illness )",
            },
        },
    },
    {
        "date": "2026-11-13",
        "game_id": "0022600037",
        "away": "ATL",
        "home": "CHI",
        "away_pts": 117,
        "home_pts": 125,
        "ot_periods": 1,
        "quarters": {"ATL": [24, 29, 30, 27, 7], "CHI": [33, 27, 24, 26, 15]},
        "arena": "United Center",
        "city": "Chicago, IL",
        "attendance": "19466",
        "officials": "#25 Tony Brothers, #55 Bill Kennedy, #72 J.T. Orr",
        "gamebook_url": "https://statsdmz.nba.com/pdfs/20261113/20261113_ATLCHI_book.pdf",
        "game_url": "https://www.nba.com/game/atl-vs-chi-0022600037",
        "teams": {
            "ATL": {
                "played": [
                    ("Dyson Daniels", "F", "36:05", 6, 9, 4),
                    ("Jalen Johnson", "F", "40:21", 27, 11, 10),
                    ("Onyeka Okongwu", "C", "34:50", 17, 6, 1),
                    ("Nickeil Alexander-Walker", "G", "41:17", 16, 6, 3),
                    ("Kingston Flemings", "G", "17:22", 0, 1, 1),
                    ("Luguentz Dort", "", "19:33", 10, 1, 2),
                    ("Jock Landale", "", "18:10", 12, 5, 0),
                    ("CJ McCollum", "", "31:52", 20, 5, 5),
                    ("Aaron Wiggins", "", "25:30", 9, 4, 3),
                ],
                "dnp": ["RayJ Dennis", "Zuby Ejiofor", "Dorian Finney-Smith", "Corey Kispert"],
                "inactive": ("Gilbert (Injury/Illness - Left Knee Inflammation; Non-Surgical "
                             "Procedure), Gueye (Injury/Illness - Left Foot Fracture), Newell "
                             "(Injury/Illness - Left Great Toe Hyperextension), Veesaar "
                             "(Injury/Illness - Right ACL Tear), Wilson (G League - Two-Way)"),
            },
            "CHI": {
                "played": [
                    ("Isaac Okoro", "F", "40:53", 15, 3, 2),
                    ("Matas Buzelis", "F", "28:35", 11, 6, 2),
                    ("Jalen Smith", "C", "31:35", 15, 12, 3),
                    ("Norman Powell", "G", "31:06", 33, 5, 2),
                    ("Josh Giddey", "G", "39:01", 15, 10, 14),
                    ("Nic Claxton", "", "21:34", 2, 6, 2),
                    ("Buddy Hield", "", "25:16", 12, 3, 3),
                    ("Patrick Williams", "", "24:25", 13, 4, 2),
                    ("Noa Essengue", "", "07:56", 5, 1, 1),
                    ("Tre Jones", "", "14:38", 4, 1, 3),
                ],
                "dnp": ["Zach Collins", "Jordan Hawkins", "Leonard Miller", "Orlando Robinson"],
                "inactive": ("Awaka (Injury/Illness - Disc Irritation), Sellers (G League - "
                             "Two-Way), Swain (Injury/Illness - Right Disc Irritation), Wilson "
                             "(Injury/Illness - Right Metacarpal Fracture)"),
            },
        },
    },
]
