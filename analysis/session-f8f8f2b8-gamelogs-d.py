"""Session arena/f8f8f2b8-nba2 — official per-player box scores, batch D (2026-11-13).

Same source and format as batch A.

**I-F8F-09 (flagged, disclosed, not silently resolved).** In the UTA@HOU gamebook the
SCORE BY PERIOD table row for Houston extracted as ``27 26 30 22`` (sums to 105) while the
gamebook's repeated footer line reads ``ROCKETS 27 36 29 33 125`` (sums to 125, the printed
final). The table row is internally inconsistent with its own final, so the footer reading is
the one carried, and ``quarters_source`` records both readings and the conflict for review.
"""

GAMES = [
    {
        "date": "2026-11-13",
        "game_id": "0022600039",
        "away": "UTA",
        "home": "HOU",
        "away_pts": 118,
        "home_pts": 125,
        "ot_periods": 0,
        "quarters": {"UTA": [27, 26, 36, 29], "HOU": [27, 36, 29, 33]},
        "quarters_source": (
            "UTA from the SCORE BY PERIOD table (27/26/36/29 = 118, reconciles). HOU from the "
            "gamebook's repeated footer line (27/36/29/33 = 125, reconciles); the SCORE BY "
            "PERIOD table row for HOU extracted as 27/26/30/22 (sums to 105, contradicts the "
            "printed final 125) — see I-F8F-09."
        ),
        "arena": "Toyota Center",
        "city": "Houston, TX",
        "attendance": "18055 (Sellout)",
        "officials": "#4 Sean Wright, #34 Kevin Cutler, #93 Jenna Reneau",
        "gamebook_url": "https://statsdmz.nba.com/pdfs/20261113/20261113_UTAHOU_book.pdf",
        "game_url": "https://www.nba.com/game/uta-vs-hou-0022600039",
        "teams": {
            "UTA": {
                "played": [
                    ("Josh Okogie", "F", "21:43", 7, 2, 1),
                    ("Ace Bailey", "F", "34:32", 21, 3, 1),
                    ("Jaxson Hayes", "C", "13:27", 12, 5, 1),
                    ("Darryn Peterson", "G", "33:58", 28, 7, 2),
                    ("Keyonte George", "G", "37:32", 27, 4, 7),
                    ("Mo Bamba", "", "19:53", 9, 9, 1),
                    ("Brice Sensabaugh", "", "26:59", 7, 3, 1),
                    ("Isaiah Collier", "", "15:59", 3, 2, 5),
                    ("Josh Green", "", "14:21", 2, 0, 0),
                    ("Svi Mykhailiuk", "", "07:01", 0, 1, 0),
                    ("Tony Bradley", "", "12:28", 0, 5, 1),
                    ("Kyle Filipowski", "", "02:07", 2, 0, 0),
                ],
                "dnp": [],
                "inactive": ("Alexander (G League - Two-Way), Bufkin (G League - Two-Way), "
                             "Ingram (G League - Two-Way), Jackson Jr. (Injury/Illness - Right "
                             "MCL Tear), Markkanen (Injury/Illness - Right Hand Fracture), "
                             "Nurkić (Injury/Illness - Right 2nd Plantar Plate Tear)"),
            },
            "HOU": {
                "played": [
                    ("Kevin Durant", "F", "33:25", 22, 3, 6),
                    ("Jabari Smith Jr.", "F", "24:03", 6, 3, 0),
                    ("Alperen Sengun", "C", "37:05", 43, 12, 5),
                    ("Amen Thompson", "G", "40:53", 12, 10, 3),
                    ("Fred VanVleet", "G", "33:47", 17, 2, 3),
                    ("Tari Eason", "", "33:20", 14, 11, 2),
                    ("Reed Sheppard", "", "19:09", 0, 0, 3),
                    ("Oscar Tshiebwe", "", "05:57", 0, 5, 0),
                    ("Bogdan Bogdanović", "", "12:21", 11, 1, 3),
                ],
                "dnp": ["Steven Adams (DND - - Right Soleus Strain)",
                        "Clint Capela (DND - - Right Ankle Sprain)",
                        "Isaiah Crawford (DNP - Coach's Decision)",
                        "Marcus Smart (NWT - - League Suspension)",
                        "Jae'Sean Tate (DNP - Coach's Decision)",
                        "Bruce Thornton (DNP - Coach's Decision)"],
                "inactive": "Copeland (G League - Two-Way), Phillips (G League - Two-Way)",
            },
        },
    },
    {
        "date": "2026-11-13",
        "game_id": "0022600040",
        "away": "GSW",
        "home": "SAS",
        "away_pts": 85,
        "home_pts": 123,
        "ot_periods": 0,
        "quarters": {"GSW": [14, 19, 27, 25], "SAS": [38, 25, 34, 26]},
        "arena": "Frost Bank Center",
        "city": "San Antonio, TX",
        "attendance": "18849 (Sellout)",
        "officials": "#60 James Williams, #37 Eric Dalen, #78 Evan Scott",
        "gamebook_url": "https://statsdmz.nba.com/pdfs/20261113/20261113_GSWSAS_book.pdf",
        "game_url": "https://www.nba.com/game/gsw-vs-sas-0022600040",
        "teams": {
            "GSW": {
                "played": [
                    ("De'Anthony Melton", "F", "18:21", 8, 4, 3),
                    ("Yaxel Lendeborg", "F", "23:40", 3, 7, 1),
                    ("Draymond Green", "C", "15:44", 4, 3, 3),
                    ("Brandin Podziemski", "G", "22:03", 8, 3, 0),
                    ("Will Richard", "G", "30:19", 7, 4, 1),
                    ("LJ Cryer", "", "23:57", 20, 2, 6),
                    ("Al Horford", "", "09:51", 0, 3, 1),
                    ("Georges Niang", "", "15:14", 5, 3, 2),
                    ("Gui Santos", "", "21:10", 7, 4, 1),
                    ("Charles Bassey", "", "20:10", 11, 5, 2),
                    ("Gary Payton II", "", "12:32", 2, 2, 0),
                    ("Graham Ike", "", "13:01", 5, 2, 3),
                    ("Malevy Leons", "", "13:58", 5, 1, 0),
                ],
                "dnp": [],
                "inactive": ("Butler III (Injury/Illness - Right ACL Repair / Surgery), Curry "
                             "(Injury/Illness - Right Oblique Tear), Moody (Injury/Illness - "
                             "Left Patellar Tendon Repair / Surgery), Porziņģis (Not With Team), "
                             "Williams (Injury/Illness - Left Hamstring Strain)"),
            },
            "SAS": {
                "played": [
                    ("Stephon Castle", "F", "25:07", 32, 5, 6),
                    ("Devin Vassell", "F", "22:52", 7, 2, 2),
                    ("Victor Wembanyama", "C", "20:54", 12, 12, 6),
                    ("Dylan Harper", "G", "25:10", 9, 3, 4),
                    ("De'Aaron Fox", "G", "16:49", 7, 5, 1),
                    ("Julian Champagnie", "", "22:43", 7, 8, 3),
                    ("Luke Kornet", "", "16:12", 6, 7, 2),
                    ("Keldon Johnson", "", "24:56", 18, 4, 4),
                    ("Harrison Barnes", "", "21:19", 11, 1, 1),
                    ("Carter Bryant", "", "19:06", 8, 3, 2),
                    ("Jordan McLaughlin", "", "13:58", 4, 6, 2),
                    ("Tarris Reed Jr.", "", "10:54", 2, 4, 1),
                ],
                "dnp": [],
                "inactive": ("Brown (G League - Two-Way), Gillespie (G League - Two-Way), "
                             "Harris (Injury/Illness - Left Calf Strain), Jones Garcia "
                             "(G League - Two-Way), Quaintance (Injury/Illness - Right Knee "
                             "Surgery)"),
            },
        },
    },
]
