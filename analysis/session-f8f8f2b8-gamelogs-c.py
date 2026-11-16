"""Session arena/f8f8f2b8-nba2 — official per-player box scores, batch C (2026-11-13).

Same source and format as batch A.

**I-F8F-07 (flagged, not filled in).** In the MEM@NOP gamebook the MIN cell for Memphis'
Jerami Grant did not extract — the row reads "| 3 Jerami Grant |  |  | 7 | 10 | ..." with the
minutes column empty. His minutes are therefore recorded as ``None`` and the Memphis team-game
is marked ``minutes_complete: False``. The 25:39 that the team total would imply is a residual
computed from other cells and from a team-total row that this session has already observed to be
off by one second on two other games, so it is deliberately NOT substituted. Memphis is
excluded from the measured-minutes tables and the exclusion is published.
"""

GAMES = [
    {
        "date": "2026-11-13",
        "game_id": "0022600038",
        "away": "MEM",
        "home": "NOP",
        "away_pts": 142,
        "home_pts": 111,
        "ot_periods": 0,
        "quarters": {"MEM": [35, 35, 35, 37], "NOP": [28, 30, 28, 25]},
        "arena": "Smoothie King Center",
        "city": "New Orleans, LA",
        "attendance": "16487",
        "officials": "#74 Curtis Blair, #36 Brent Barnaky, #12 CJ Washington",
        "gamebook_url": "https://statsdmz.nba.com/pdfs/20261113/20261113_MEMNOP_book.pdf",
        "game_url": "https://www.nba.com/game/mem-vs-nop-0022600038",
        "minutes_complete": {"MEM": False, "NOP": True},
        "teams": {
            "MEM": {
                "played": [
                    ("Jaylen Wells", "F", "26:47", 11, 2, 1),
                    ("Cameron Boozer", "F", "25:05", 12, 10, 3),
                    ("Isaiah Stewart", "C", "20:21", 12, 5, 0),
                    ("Cedric Coward", "G", "29:50", 14, 7, 6),
                    ("Ty Jerome", "G", "28:35", 17, 2, 9),
                    ("Jerami Grant", "", None, 22, 1, 1),
                    ("Taylor Hendricks", "", "18:43", 10, 12, 2),
                    ("GG Jackson", "", "22:21", 14, 6, 4),
                    ("Javon Small", "", "15:21", 10, 2, 5),
                    ("Cam Spencer", "", "24:12", 14, 2, 5),
                    ("Olivier-Maxence Prosper", "", "02:22", 6, 1, 0),
                    ("Kris Murray", "", "00:44", 0, 1, 0),
                ],
                "dnp": [],
                "inactive": ("Edey (Injury/Illness - Left Ankle Injury Management), López "
                             "(G League - On Assignment - G League - On Assignment), Mashack "
                             "(G League - Two-Way - G League - Two-Way), Pippen Jr. "
                             "(Injury/Illness - Lumbar Disc Herniation), Post (Injury/Illness - "
                             "Concussion Protocol), Saunders (Injury/Illness - Right Knee "
                             "Surgery)"),
            },
            "NOP": {
                "played": [
                    ("Saddiq Bey", "F", "34:51", 30, 10, 0),
                    ("Zion Williamson", "F", "33:23", 22, 5, 4),
                    ("DeAndre Jordan", "C", "17:06", 6, 8, 1),
                    ("Herbert Jones", "G", "32:16", 8, 2, 3),
                    ("Jeremiah Fears", "G", "33:40", 18, 5, 7),
                    ("Karlo Matković", "", "18:44", 1, 3, 0),
                    ("Jordan Poole", "", "20:43", 13, 2, 5),
                    ("Bennedict Mathurin", "", "10:03", 0, 0, 0),
                    ("Derik Queen", "", "22:38", 10, 6, 2),
                    ("Malik Dia", "", "04:09", 2, 0, 1),
                    ("AJ Johnson", "", "04:09", 1, 0, 0),
                    ("Jaron Pierre Jr.", "", "04:09", 0, 0, 0),
                    ("Julian Reese", "", "04:09", 0, 2, 0),
                ],
                "dnp": [],
                "inactive": ("McGowens (Injury/Illness - Left Elbow Infection), Missi "
                             "(Injury/Illness - Left Knee Contusion / Bone Bruise), Murphy III "
                             "(Injury/Illness - Bilateral Patellar Tendinopathy), Murray "
                             "(Injury/Illness - Left Ankle Sprain), Watford (Injury/Illness - "
                             "Right Ankle Sprain)"),
            },
        },
    },
]
