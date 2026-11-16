"""Session arena/f8f8f2b8-nba2 — official per-player box scores, batch E (2026-11-13).

Completes the 2026-11-13 slate (9 games, 18 clubs). Same source and format as batch A.

**I-F8F-09 also applies to POR@SAC.** The SCORE BY PERIOD table row for Sacramento extracted
as ``25 28 25 20`` (sums to 98) while the gamebook's footer line reads ``KINGS 25 28 25 29 107``
(sums to 107, the printed final). The footer reading is carried and the conflict is recorded in
``quarters_source``.

**I-F8F-10 (flagged).** In the OKC@LAC gamebook the Clippers guard is printed "Keaton Wagner"
in the full-game table and "Keaton Wagler" in the period-1 table. Both spellings are recorded.
"""

GAMES = [
    {
        "date": "2026-11-13",
        "game_id": "0022600041",
        "away": "POR",
        "home": "SAC",
        "away_pts": 120,
        "home_pts": 107,
        "ot_periods": 0,
        "quarters": {"POR": [34, 30, 29, 27], "SAC": [25, 28, 25, 29]},
        "quarters_source": (
            "POR from the SCORE BY PERIOD table (34/30/29/27 = 120, reconciles). SAC from the "
            "gamebook's repeated footer line (25/28/25/29 = 107, reconciles); the SCORE BY "
            "PERIOD table row for SAC extracted as 25/28/25/20 (sums to 98, contradicts the "
            "printed final 107) — see I-F8F-09."
        ),
        "arena": "Golden 1 Center",
        "city": "Sacramento, CA",
        "attendance": None,
        "officials": "#8 Marc Davis, #18 Andy Nagy, #94 Biniam Maru",
        "gamebook_url": "https://statsdmz.nba.com/pdfs/20261113/20261113_PORSAC_book.pdf",
        "game_url": "https://www.nba.com/game/por-vs-sac-0022600041",
        "teams": {
            "POR": {
                "played": [
                    ("Sidy Cissoko", "F", "25:39", 3, 4, 1),
                    ("Toumani Camara", "F", "35:39", 14, 2, 1),
                    ("Donovan Clingan", "C", "26:33", 13, 11, 2),
                    ("Deni Avdija", "G", "34:34", 34, 6, 4),
                    ("Damian Lillard", "G", "33:00", 29, 2, 6),
                    ("Branden Carlson", "", "07:35", 5, 3, 0),
                    ("Jrue Holiday", "", "26:37", 6, 5, 5),
                    ("Robert Williams III", "", "16:39", 2, 7, 1),
                    ("Scoot Henderson", "", "23:00", 11, 0, 1),
                    ("Jayson Kent", "", "10:44", 3, 1, 0),
                ],
                "dnp": ["Micah Potter", "John Tonje", "Yang Hansen"],
                "inactive": ("Krejčí (Injury/Illness - Left Ankle Fracture), Morant "
                             "(Injury/Illness - Left Hamstring Strain), Sharpe (Injury/Illness "
                             "- Right Meniscus Surgery), Youngblood (Injury/Illness - Right Bone "
                             "Bruise)"),
            },
            "SAC": {
                "played": [
                    ("Keegan Murray", "F", "39:39", 16, 7, 4),
                    ("De'Andre Hunter", "F", "41:31", 24, 5, 2),
                    ("Domantas Sabonis", "C", "35:28", 21, 12, 5),
                    ("Zach LaVine", "G", "36:22", 12, 3, 6),
                    ("Darius Acuff Jr.", "G", "35:10", 17, 4, 6),
                    ("Leaky Black", "", "11:47", 0, 0, 0),
                    ("Malik Monk", "", "18:15", 7, 4, 3),
                    ("Emanuel Sharp", "", "06:58", 4, 0, 0),
                    ("Dylan Cardwell", "", "12:32", 6, 3, 3),
                    ("Daeqwon Plowden", "", "02:17", 0, 0, 0),
                ],
                "dnp": ["Mason Plumlee"],
                "inactive": ("Achiuwa (Injury/Illness - Left Ankle Soreness), Karaban (G League "
                             "- On Assignment), Mogbo (G League - Two-Way), Pedulla (G League - "
                             "Two-Way), Raynaud (Injury/Illness - Right Patella Subluxation), "
                             "Simmons (Injury/Illness - Right Achilles Tendon Repair / Surgery)"),
            },
        },
    },
    {
        "date": "2026-11-13",
        "game_id": "0022600042",
        "away": "OKC",
        "home": "LAC",
        "away_pts": 112,
        "home_pts": 113,
        "ot_periods": 0,
        "quarters": {"OKC": [27, 17, 40, 28], "LAC": [33, 24, 25, 31]},
        "arena": "Intuit Dome",
        "city": "Inglewood, CA",
        "attendance": "17927 (Sellout)",
        "officials": "#48 Scott Foster, #9 Natalie Sago, #67 Brandon Adair",
        "gamebook_url": "https://statsdmz.nba.com/pdfs/20261113/20261113_OKCLAC_book.pdf",
        "game_url": "https://www.nba.com/game/okc-vs-lac-0022600042",
        "teams": {
            "OKC": {
                "played": [
                    ("Kenrich Williams", "F", "35:15", 8, 8, 4),
                    ("Aday Mara", "F", "21:23", 10, 3, 0),
                    ("Isaiah Hartenstein", "C", "30:21", 21, 16, 6),
                    ("Jared McCain", "G", "30:37", 23, 4, 2),
                    ("Shai Gilgeous-Alexander", "G", "38:30", 40, 4, 5),
                    ("Alex Caruso", "", "27:28", 5, 1, 4),
                    ("Nikola Topić", "", "15:30", 0, 4, 3),
                    ("Nique Clifford", "", "11:41", 0, 0, 0),
                    ("Bennett Stirtz", "", "11:51", 5, 1, 0),
                    ("Josh Dix", "", "17:25", 0, 4, 3),
                ],
                "dnp": ["Brooks Barnhizer"],
                "inactive": ("Holmgren (Injury/Illness - Right Knee/ Injury Recovery ), Mitchell "
                             "(Injury/Illness - Left Ankle Sprain), Peavy (G League - Two-Way), "
                             "Sorber (Injury/Illness - Right Knee Surgery ), Wallace "
                             "(Injury/Illness - Left Shoulder Surgery ), Williams (Injury/Illness "
                             "- Left Ankle Surgery ), Williams (Injury/Illness - Low Back Spasms)"),
            },
            "LAC": {
                "played": [
                    ("Derrick Jones Jr.", "F", "29:11", 14, 5, 0),
                    ("Rui Hachimura", "F", "31:43", 7, 11, 3),
                    ("Brook Lopez", "C", "30:44", 26, 7, 4),
                    ("Kris Dunn", "G", "19:59", 2, 3, 6),
                    ("Darius Garland", "G", "37:03", 24, 4, 7),
                    ("Max Strus", "", "22:34", 3, 2, 3),
                    ("Gradey Dick", "", "18:34", 13, 3, 0),
                    ("Isaiah Jackson", "", "17:16", 5, 3, 1),
                    ("Kobe Sanders", "", "14:36", 5, 0, 1),
                    ("Keaton Wagner", "", "18:21", 14, 2, 1),
                ],
                "dnp": ["Cam Christie", "Baba Miller", "Jalen Pickett"],
                "inactive": ("Beal (Injury/Illness - Right Knee Injury Management), Ingram "
                             "(Injury/Illness - Right Heel Surgery ), Martinelli (G League - "
                             "Two-Way), Miller (Injury/Illness - Left Rotator Cuff Surgery ), "
                             "Niederhäuser (Injury/Illness - Right Lisfranc Surgery )"),
            },
        },
    },
]
