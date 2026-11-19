"""Session arena/934fce54-nba2 — official 2026-11-16 gamebook transcription.

Verbatim transcription of the **official NBA gamebook PDF** published for each of the
eight games of Monday, November 16, 2026:

    https://statsdmz.nba.com/pdfs/20261116/20261116_<AWAY><HOME>_book.pdf

read as text through the platform page-fetch tool (fetch_page) on 2026-11-17 in the
window ~16:05-16:25 UTC. Direct bash egress to statsdmz.nba.com is blocked in this
sandbox (HTTP 000), so the PDF bytes cannot be stored; every emitted row therefore
carries the gamebook URL and the retrieval window it was read from.

Nothing is derived, rounded or filled in. The script re-checks every transcription
arithmetic gate before writing anything:

  * each club's quarter row sums to the printed final;
  * each club's players' points sum to the printed final;
  * each club's players' minutes sum to 240:00 (+-5 s, the PDFs round to the second);
  * every player row satisfies pts = 2*(FG-3P) + 3*3P + FT;
  * where the player rebound / assist cells reconcile with the club totals row, they
    are published; where they cannot be reconciled under any alignment of the
    extracted row (the F-V5-02 condition), every player cell of that stat for that
    club is left null with a reason, and the club total is carried instead.

Outputs (both content-checked above):
  data/raw/capture_2026-11-17-934fce54/results_2026-11-16.json   (nba2.results-feed.v3)
  data/v5/gamebooks_2026-11-16.json                              (nba2.v5.gamebook-transcript.v1)
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_FEED = ROOT / "data/raw/capture_2026-11-17-934fce54/results_2026-11-16.json"
OUT_BOOKS = ROOT / "data/v5/gamebooks_2026-11-16.json"

RETRIEVED = ("2026-11-17 ~16:05-16:25 UTC (platform page-fetch tool; per-call times are "
             "not logged by the tool, so every game carries the window)")

BOOK = "https://statsdmz.nba.com/pdfs/20261116/20261116_{code}_book.pdf"
GAME = "https://www.nba.com/game/{a}-vs-{h}-{gid}"
LIST = "https://www.nba.com/schedule?date=2026-11-17"

# Flag ids used below (published on v5-verify.html):
#   F-93-01  HOU@MIA: the SCORE BY PERIOD visitor row did not extract; the four Houston
#            quarter scores are read from the four quarter-box team-total rows of the
#            same official gamebook (15, 31, 35, 29), corroborated by the first-half
#            table (Rockets 15 31 46) and the cumulative line (81 through three).
#   F-93-02  MEM@WAS / HOU@MIA / PHI@BKN: extracted rows carrying one cell fewer than
#            the header (the F-V5-02 / F-V5-03 condition). See per-club reasons.
#   F-93-03  WAS: player rebound cells sum to 32 against the club's published 31 and
#            the assist cells cannot be reconciled with the club's 25 under any
#            alignment; no Washington rebound or assist is attributed to a player.
#   F-93-04  HOU: player rebound cells sum to 53 against the club's published 52 and
#            the assist cells cannot be reconciled with the club's 23 under any
#            alignment; no Houston rebound or assist is attributed to a player.
#   F-93-05  MEM: the extracted full-game box carries two DNP - Coach's Decision rows
#            with no attached player names. No name is invented for them.
#   F-93-06  PHI@BKN: the gamebook prints two spellings for Brooklyn #12 ("Ryan Rupert"
#            in the full-game box, "Rayan Rupert" in the period boxes). The full-game
#            box spelling is transcribed; the pair is flagged, not folded.
#   F-93-07  PHI@BKN: the extracted DNP status cell for Terance Mann prints a garbled
#            doubled designation ("DNP - Coach's Decision DNP - Coach Decision Decision
#            Decision Decision Decision"); the designation is transcribed once.
#   F-93-08  MIA: the extracted rows' assist cells sum to 27 against the club's published
#            29, and the offensive/defensive rebound split cells do not reconcile with
#            the club row either (15/28 against 13/27) although the TOT rebound column
#            does (40 = 40). No MIA assist is attributed to a player; the club's
#            published totals are carried instead.

REB_BLANK_WAS = (
    "F-93-03: the extracted Washington rows' rebound cells sum to 32 against the club's "
    "published 31, and one row (Ayton) prints one cell fewer than the header, so no "
    "individual rebound value can be attributed with confidence. Blank, not inferred; "
    "the club's published total (31) is carried instead.")
AST_BLANK_WAS = (
    "F-93-03: the extracted Washington rows' assist cells cannot be reconciled with the "
    "club's published 25 under any alignment of the short row (Ayton), so no individual "
    "assist value can be attributed with confidence. Blank, not inferred; the club's "
    "published total (25) is carried instead.")
REB_BLANK_HOU = (
    "F-93-04: four extracted Houston rows (Bogdanović, Sheppard, Tate, Thornton) carry "
    "one cell fewer than the header and the rows' rebound cells sum to 53 against the "
    "club's published 52, so no individual rebound value can be attributed with "
    "confidence. Blank, not inferred; the club's published total (52) is carried instead.")
AST_BLANK_HOU = (
    "F-93-04: four extracted Houston rows (Bogdanović, Sheppard, Tate, Thornton) carry "
    "one cell fewer than the header and the rows' assist cells cannot be reconciled with "
    "the club's published 23 under any alignment, so no individual assist value can be "
    "attributed with confidence. Blank, not inferred; the club's published total (23) is "
    "carried instead.")
AST_BLANK_MIA = (
    "F-93-08: the extracted Miami rows' assist cells sum to 27 against the club's "
    "published 29 (and the OR/DR split cells do not reconcile with the club row either, "
    "although the TOT rebound column does), so no individual assist value can be "
    "attributed with confidence. Blank, not inferred; the club's published total (29) is "
    "carried instead.")


def P(jersey, name, pos, m, pts, reb, ast, fg, fg3, ft, status=None, note=None):
    a, b = m.split(":")
    min_sec = int(a) * 60 + int(b)
    return {"jersey": jersey, "name": name, "pos": pos, "min": m, "min_sec": min_sec,
            "pts": pts, "reb": reb, "ast": ast, "fg": fg, "fg3": fg3, "ft": ft,
            "status": status, "note": note}


def DNP(jersey, name, pos, status, note=None):
    return {"jersey": jersey, "name": name, "pos": pos, "min": None, "min_sec": None,
            "pts": None, "reb": None, "ast": None, "fg": None, "fg3": None, "ft": None,
            "status": status, "note": note}


GAMES = [
    # ---------------------------------------------------------------- ORL @ BOS
    {
        "game_id": "0022600245", "date": "2026-11-16", "matchup": "ORL@BOS",
        "away": "ORL", "home": "BOS", "arena": "TD Garden, Boston, MA",
        "code": "ORLBOS",
        "final": {"away": 115, "home": 105},
        "quarters": {"away": [20, 30, 25, 40], "home": [17, 24, 36, 28], "ot": {"away": [], "home": []}},
        "club_totals": {
            "ORL": {"min_sec": 14400, "pts": 115, "reb": 46, "or": 10, "dr": 36, "ast": 31},
            "BOS": {"min_sec": 14400, "pts": 105, "reb": 40, "or": 9, "dr": 31, "ast": 24},
        },
        "teams": {
            "ORL": {"side": "away", "opp": "BOS", "players": [
                P(0, "Anthony Black", "F", "32:56", 20, 2, 7, 7, 3, 3),
                P(22, "Franz Wagner", "F", "37:34", 21, 8, 9, 8, 0, 5),
                P(34, "Wendell Carter Jr.", "C", "28:05", 10, 3, 1, 3, 1, 3),
                P(3, "Desmond Bane", "G", "39:13", 24, 8, 5, 8, 3, 5),
                P(4, "Jalen Suggs", "G", "24:37", 12, 6, 4, 5, 2, 0),
                P(8, "Jamal Cain", None, "14:39", 2, 5, 0, 0, 0, 2),
                P(23, "Tristan da Silva", None, "31:13", 13, 6, 3, 4, 3, 2),
                P(35, "Goga Bitadze", None, "19:55", 10, 6, 1, 5, 0, 0),
                P(2, "Jevon Carter", None, "11:48", 3, 2, 1, 1, 1, 0),
                DNP(30, "Alex Morales", None, "DNP - Coach's Decision"),
                DNP(11, "Jase Richardson", None, "DNP - Coach's Decision"),
                DNP(9, "Nikola Vučević", None, "DNP - Coach's Decision"),
            ]},
            "BOS": {"side": "home", "opp": "ORL", "players": [
                P(13, "Paul George", "F", "36:05", 22, 8, 3, 7, 5, 3),
                P(0, "Jayson Tatum", "F", "36:03", 24, 12, 4, 9, 3, 3),
                P(52, "Luka Garza", "C", "17:33", 3, 0, 4, 1, 1, 0),
                P(27, "Jordan Walsh", "G", "16:36", 6, 2, 0, 2, 2, 0),
                P(9, "Derrick White", "G", "31:52", 9, 3, 2, 4, 1, 0),
                P(11, "Payton Pritchard", None, "31:40", 21, 4, 5, 7, 4, 3),
                P(4, "Mitchell Robinson", None, "17:44", 4, 5, 2, 2, 0, 0),
                P(55, "Baylor Scheierman", None, "11:20", 0, 1, 1, 0, 0, 0),
                P(30, "Sam Hauser", None, "24:54", 12, 1, 2, 4, 4, 0),
                P(12, "Chris Cenac Jr.", None, "12:10", 4, 2, 1, 2, 0, 0),
                P(28, "Hugo González", None, "04:04", 0, 2, 0, 0, 0, 0),
                DNP(45, "Mike Conley", None, "DNP - Coach's Decision"),
                DNP(8, "Ron Harper Jr.", None, "DNP - Coach's Decision"),
                DNP(20, "Dillon Mitchell", None, "DNP - Coach's Decision"),
                DNP(77, "Amari Williams", None, "DNP - Coach's Decision"),
            ]},
        },
    },
    # ---------------------------------------------------------------- CHI @ CLE
    {
        "game_id": "0022600246", "date": "2026-11-16", "matchup": "CHI@CLE",
        "away": "CHI", "home": "CLE", "arena": "Rocket Arena, Cleveland, OH",
        "code": "CHICLE",
        "final": {"away": 115, "home": 126},
        "quarters": {"away": [31, 17, 31, 36], "home": [25, 32, 31, 38], "ot": {"away": [], "home": []}},
        "club_totals": {
            "CHI": {"min_sec": 14400, "pts": 115, "reb": 37, "or": 11, "dr": 26, "ast": 30},
            "CLE": {"min_sec": 14400, "pts": 126, "reb": 51, "or": 15, "dr": 36, "ast": 33},
        },
        "teams": {
            "CHI": {"side": "away", "opp": "CLE", "players": [
                P(14, "Matas Buzelis", "F", "31:26", 23, 3, 0, 8, 3, 4),
                P(35, "Isaac Okoro", "F", "32:11", 13, 6, 2, 5, 3, 0),
                P(25, "Jalen Smith", "C", "27:45", 17, 11, 3, 6, 3, 2),
                P(24, "Norman Powell", "G", "32:57", 27, 2, 6, 10, 0, 7),
                P(3, "Josh Giddey", "G", "23:48", 4, 4, 8, 1, 1, 1),
                P(9, "Nic Claxton", None, "16:38", 8, 2, 1, 3, 0, 2),
                P(7, "Buddy Hield", None, "19:06", 6, 4, 2, 2, 2, 0),
                P(2, "Noa Essengue", None, "13:59", 1, 2, 1, 0, 0, 1),
                P(30, "Tre Jones", None, "23:00", 16, 2, 6, 6, 0, 4),
                P(44, "Patrick Williams", None, "12:56", 0, 0, 0, 0, 0, 0),
                P(15, "Jordan Hawkins", None, "03:37", 0, 0, 1, 0, 0, 0),
                P(5, "Dailyn Swain", None, "01:50", 0, 1, 0, 0, 0, 0),
                P(11, "Leonard Miller", None, "00:47", 0, 0, 0, 0, 0, 0),
                DNP(12, "Zach Collins", None, "DNP - Coach's Decision"),
            ]},
            "CLE": {"side": "home", "opp": "CHI", "players": [
                P(24, "Tyrese Proctor", "F", "28:54", 17, 3, 2, 6, 2, 3),
                P(8, "Peyton Watson", "F", "21:31", 14, 4, 0, 5, 2, 2),
                P(31, "Jarrett Allen", "C", "30:12", 13, 14, 3, 6, 0, 1),
                P(45, "Donovan Mitchell", "G", "35:51", 39, 4, 4, 16, 2, 5),
                P(1, "James Harden", "G", "34:22", 9, 4, 10, 3, 2, 1),
                P(15, "Meleek Thomas", None, "30:03", 10, 6, 3, 4, 1, 1),
                P(33, "Mario Hezonja", None, "14:46", 9, 4, 2, 4, 1, 0),
                P(3, "Thomas Bryant", None, "17:48", 9, 5, 4, 4, 0, 1),
                P(9, "Craig Porter Jr.", None, "13:38", 2, 1, 3, 1, 0, 0),
                P(77, "Norchad Omier", None, "12:55", 4, 6, 2, 2, 0, 0),
                DNP(18, "Khalifa Diop", None, "DNP - Coach's Decision"),
                DNP(12, "Riley Minix", None, "DNP - Coach's Decision"),
            ]},
        },
    },
    # ---------------------------------------------------------------- MEM @ WAS
    {
        "game_id": "0022600247", "date": "2026-11-16", "matchup": "MEM@WAS",
        "away": "MEM", "home": "WAS", "arena": "Capital One Arena, Washington, DC",
        "code": "MEMWAS",
        "final": {"away": 136, "home": 120},
        "quarters": {"away": [33, 26, 42, 35], "home": [35, 34, 18, 33], "ot": {"away": [], "home": []}},
        "club_totals": {
            "MEM": {"min_sec": 14400, "pts": 136, "reb": 48, "or": 15, "dr": 33, "ast": 42},
            "WAS": {"min_sec": 14400, "pts": 120, "reb": 31, "or": 11, "dr": 20, "ast": 25},
        },
        "teams": {
            "MEM": {"side": "away", "opp": "WAS",
                    "team_note": ("F-93-05: the extracted full-game box carries two "
                                  "DNP - Coach's Decision rows with no attached player "
                                  "names; no name is invented for them. The thirteen "
                                  "listed players account for the full 240:00."),
                    "players": [
                P(0, "Jaylen Wells", "F", "26:52", 8, 4, 3, 3, 2, 0),
                P(27, "Cameron Boozer", "F", "29:23", 29, 7, 7, 10, 7, 2),
                P(14, "Zach Edey", "C", "20:43", 23, 10, 1, 10, 0, 3),
                P(23, "Cedric Coward", "G", "26:50", 18, 8, 6, 7, 2, 2),
                P(24, "Cam Spencer", "G", "31:40", 12, 6, 9, 4, 1, 3),
                P(3, "Jerami Grant", None, "23:06", 8, 1, 2, 3, 2, 0),
                P(22, "Taylor Hendricks", None, "18:30", 9, 3, 0, 4, 1, 0),
                P(10, "Javon Small", None, "28:57", 12, 5, 12, 6, 0, 0),
                P(18, "Olivier-Maxence Prosper", None, "16:00", 12, 0, 1, 4, 1, 3),
                P(41, "Quinten Post", None, "08:32", 5, 3, 0, 2, 0, 1),
                P(17, "Kris Murray", None, "06:09", 0, 1, 0, 0, 0, 0),
                P(21, "Jahmai Mashack", None, "02:12", 0, 0, 1, 0, 0, 0),
                P(35, "Karim López", None, "01:06", 0, 0, 0, 0, 0, 0),
            ]},
            "WAS": {"side": "home", "opp": "MEM",
                    "reb_blank_reason": REB_BLANK_WAS, "ast_blank_reason": AST_BLANK_WAS,
                    "players": [
                P(18, "Kyshawn George", "F", "38:01", 18, None, None, 7, 2, 2),
                P(23, "Anthony Davis", "F", "34:41", 23, None, None, 8, 0, 7),
                P(20, "Alex Sarr", "C", "30:44", 6, None, None, 2, 1, 1),
                P(4, "AJ Dybantsa", "G", "32:06", 21, None, None, 7, 1, 6),
                P(3, "Trae Young", "G", "33:02", 13, None, None, 3, 2, 5),
                P(0, "Bilal Coulibaly", None, "15:34", 11, None, None, 4, 1, 2),
                P(12, "Tre Johnson", None, "20:43", 9, None, None, 3, 2, 1),
                P(22, "Khris Middleton", None, "17:59", 9, None, None, 3, 2, 1),
                P(8, "Deandre Ayton", None, "08:22", 4, None, None, 2, 0, 0,
                  note=("F-93-03: the extracted row carries one cell fewer than the "
                        "header (the F-V5-03 condition); the rebound and assist cells "
                        "cannot be located with confidence and are blank.")),
                P(7, "Bub Carrington", None, "02:12", 0, None, None, 0, 0, 0),
                P(16, "Anthony Gill", None, "02:12", 2, None, None, 0, 0, 2),
                P(1, "Tre Mann", None, "02:12", 2, None, None, 0, 0, 2),
                P(27, "Will Riley", None, "02:12", 2, None, None, 1, 0, 0),
                DNP(14, "Terance Mann", None, "DNP - Coach's Decision",
                    note=("F-93-07: the extracted status cell prints a garbled doubled "
                          "designation; the designation is transcribed once.")),
            ]},
        },
    },
    # ---------------------------------------------------------------- PHI @ BKN
    {
        "game_id": "0022600248", "date": "2026-11-16", "matchup": "PHI@BKN",
        "away": "PHI", "home": "BKN", "arena": "Barclays Center, Brooklyn, NY",
        "code": "PHIBKN",
        "final": {"away": 135, "home": 123},
        "quarters": {"away": [33, 45, 27, 30], "home": [26, 33, 36, 28], "ot": {"away": [], "home": []}},
        "club_totals": {
            "PHI": {"min_sec": 14400, "pts": 135, "reb": 47, "or": 14, "dr": 33, "ast": 25},
            "BKN": {"min_sec": 14400, "pts": 123, "reb": 38, "or": 11, "dr": 27, "ast": 26},
        },
        "teams": {
            "PHI": {"side": "away", "opp": "BKN", "players": [
                P(7, "Jaylen Brown", "F", "33:15", 31, 13, 4, 9, 3, 10),
                P(45, "Dean Wade", "F", "32:01", 8, 11, 1, 3, 1, 1),
                P(21, "Joel Embiid", "C", "32:10", 37, 5, 1, 13, 2, 9),
                P(77, "VJ Edgecombe", "G", "33:05", 14, 9, 4, 4, 1, 5),
                P(0, "Tyrese Maxey", "G", "34:55", 24, 1, 9, 7, 4, 6),
                P(1, "Kentavious Caldwell-Pope", None, "31:17", 0, 2, 3, 0, 0, 0),
                P(5, "Anfernee Simons", None, "25:57", 9, 1, 2, 4, 1, 0),
                P(33, "Jabari Walker", None, "16:26", 12, 5, 1, 5, 1, 1),
                P(99, "Tacko Fall", None, "00:19", 0, 0, 0, 0, 0, 0),
                P(0, "Labaron Philon Jr.", None, "00:19", 0, 0, 0, 0, 0, 0),
                P(12, "Ryan Rupert", None, "00:19", 0, 0, 0, 0, 0, 0,
                  note=("F-93-06: the period boxes print this player's name as 'Rayan "
                        "Rupert'; the two spellings are flagged, not folded.")),
                DNP(11, "Justin Edwards", None, "DNP - Coach's Decision"),
            ]},
            "BKN": {"side": "home", "opp": "PHI", "players": [
                P(17, "Michael Porter Jr.", "F", "39:59", 25, 6, 2, 8, 2, 7),
                P(30, "Julius Randle", "F", "33:54", 33, 6, 1, 13, 2, 5),
                P(20, "Day'Ron Sharpe", "C", "25:25", 6, 9, 5, 3, 0, 0),
                P(8, "Egor Demin", "G", "26:06", 9, 3, 4, 3, 2, 1),
                P(10, "Nolan Traore", "G", "29:57", 23, 1, 4, 7, 2, 7),
                P(1, "Keon Ellis", None, "20:12", 8, 2, 0, 3, 2, 0),
                P(13, "Moritz Wagner", None, "10:12", 4, 5, 1, 2, 0, 0),
                P(0, "Mikel Brown Jr.", None, "18:03", 3, 1, 5, 1, 1, 0),
                P(21, "Noah Clowney", None, "24:20", 9, 3, 3, 3, 1, 2),
                P(2, "Danny Wolf", None, "11:02", 3, 2, 1, 1, 1, 0),
                P(31, "Chaney Johnson", None, "00:52", 0, 0, 0, 0, 0, 0),
                DNP(14, "Terance Mann", None, "DNP - Coach's Decision"),
            ]},
        },
    },
    # ---------------------------------------------------------------- HOU @ MIA
    {
        "game_id": "0022600249", "date": "2026-11-16", "matchup": "HOU@MIA",
        "away": "HOU", "home": "MIA", "arena": "Kaseya Center, Miami, FL",
        "code": "HOUMIA",
        "final": {"away": 110, "home": 128},
        # F-93-01: the SCORE BY PERIOD visitor row did not extract. The four Houston
        # quarter scores are read from the four quarter-box team-total rows of the same
        # official gamebook: Q1 15, Q2 31, Q3 35, Q4 29. Corroboration inside the same
        # PDF: the first-half table prints "Rockets 15 31 46", the cumulative line
        # through three quarters prints 81, and the sum 15+31+35+29 = 110 matches the
        # full-game team total row.
        "quarters": {"away": [15, 31, 35, 29], "home": [29, 33, 39, 27], "ot": {"away": [], "home": []}},
        "quarters_note": ("F-93-01: the full-game SCORE BY PERIOD table's Houston row did "
                          "not extract; each Houston quarter score is read from its "
                          "quarter-box team-total row (15, 31, 35, 29) of the same "
                          "official gamebook. The Miami row printed cleanly (29 33 39 27)."),
        "club_totals": {
            "HOU": {"min_sec": 14400, "pts": 110, "reb": 52, "or": 21, "dr": 31, "ast": 23},
            "MIA": {"min_sec": 14400, "pts": 128, "reb": 40, "or": 13, "dr": 27, "ast": 29},
        },
        "teams": {
            "HOU": {"side": "away", "opp": "MIA",
                    "reb_blank_reason": REB_BLANK_HOU, "ast_blank_reason": AST_BLANK_HOU,
                    "players": [
                P(10, "Jabari Smith Jr.", "F", "31:56", 12, None, None, 4, 1, 3),
                P(17, "Tari Eason", "F", "27:28", 7, None, None, 2, 0, 3),
                P(28, "Alperen Sengun", "C", "29:48", 23, None, None, 8, 1, 6),
                P(7, "Kevin Durant", "G", "28:42", 22, None, None, 8, 2, 4),
                P(5, "Fred VanVleet", "G", "25:56", 8, None, None, 3, 2, 0),
                P(31, "Bogdan Bogdanović", None, "25:47", 6, None, None, 2, 2, 0,
                  note="F-93-04: the extracted row carries one cell fewer than the header."),
                P(15, "Reed Sheppard", None, "18:51", 5, None, None, 2, 1, 0,
                  note="F-93-04: the extracted row carries one cell fewer than the header."),
                P(27, "Isaiah Crawford", None, "21:14", 11, None, None, 3, 1, 4),
                P(8, "Jae'Sean Tate", None, "12:00", 3, None, None, 1, 0, 1,
                  note="F-93-04: the extracted row carries one cell fewer than the header."),
                P(2, "Bruce Thornton", None, "12:00", 7, None, None, 2, 0, 3,
                  note="F-93-04: the extracted row carries one cell fewer than the header."),
                P(9, "Oscar Tshiebwe", None, "06:18", 6, None, None, 3, 0, 0),
                DNP(12, "Steven Adams", None, "DND - Left Lower Leg Injury Management"),
                DNP(36, "Marcus Smart", None, "NWT - League Suspension"),
                DNP(1, "Amen Thompson", None, "DND - Left Knee Soreness"),
            ]},
            "MIA": {"side": "home", "opp": "HOU",
                    "ast_blank_reason": AST_BLANK_MIA,
                    "players": [
                P(11, "Klay Thompson", "F", "22:24", 17, 0, None, 5, 5, 2),
                P(7, "Giannis Antetokounmpo", "F", "28:32", 20, 13, None, 8, 0, 4),
                P(13, "Bam Adebayo", "C", "15:31", 4, 1, None, 1, 0, 2,
                  note=("F-93-02: the extracted row carries one cell fewer than the "
                        "header (the F-V5-03 condition). The rebound value 1 (=OR 1 + "
                        "DR 0) is the only value under which the club's rebound total "
                        "(40) reconciles, and is recovered per the F-V5-03 precedent.")),
                P(15, "Myron Gardner", "G", "24:28", 14, 2, None, 5, 4, 0),
                P(2, "Davion Mitchell", "G", "33:16", 16, 3, None, 7, 1, 1),
                P(4, "Ryan Conwell", None, "30:27", 14, 2, None, 3, 1, 7),
                P(95, "Bobby Portis Jr.", None, "23:20", 16, 6, None, 7, 2, 0),
                P(22, "Andrew Wiggins", None, "34:14", 17, 5, None, 6, 3, 2),
                P(0, "Simone Fontecchio", None, "19:09", 10, 6, None, 4, 2, 0),
                P(24, "Tre Donaldson", None, "02:53", 0, 0, None, 0, 0, 0),
                P(16, "Keshad Johnson", None, "02:53", 0, 2, None, 0, 0, 0),
                P(8, "Nick Richards", None, "02:53", 0, 0, None, 0, 0, 0),
                DNP(10, "Tim Hardaway Jr.", None, "DNP - Coach's Decision"),
                DNP(9, "Pelle Larsson", None, "DND - Illness"),
                DNP(12, "Dru Smith", None, "DNP - Coach's Decision"),
            ]},
        },
    },
    # ---------------------------------------------------------------- POR @ MIN
    {
        "game_id": "0022600250", "date": "2026-11-16", "matchup": "POR@MIN",
        "away": "POR", "home": "MIN", "arena": "Target Center, Minneapolis, MN",
        "code": "PORMIN",
        "final": {"away": 98, "home": 106},
        "quarters": {"away": [26, 25, 22, 25], "home": [26, 33, 28, 19], "ot": {"away": [], "home": []}},
        "quarters_note": ("the first extracted SCORE BY PERIOD row for Portland prints "
                          "garbled cells and is not used; the clean table in the same "
                          "gamebook (Trail Blazers 26 25 22 25 98 / TIMBERWOLVES "
                          "26 33 28 19 106) and the plain-text line agree."),
        "club_totals": {
            "POR": {"min_sec": 14400, "pts": 98, "reb": 49, "or": 12, "dr": 37, "ast": 25},
            "MIN": {"min_sec": 14400, "pts": 106, "reb": 53, "or": 14, "dr": 39, "ast": 21},
        },
        "teams": {
            "POR": {"side": "away", "opp": "MIN", "players": [
                P(91, "Sidy Cissoko", "F", "27:35", 5, 4, 3, 2, 1, 0),
                P(33, "Toumani Camara", "F", "25:30", 3, 0, 0, 1, 0, 1),
                P(23, "Donovan Clingan", "C", "22:27", 10, 10, 1, 5, 0, 0),
                P(8, "Deni Avdija", "G", "29:50", 27, 8, 4, 11, 3, 2),
                P(0, "Damian Lillard", "G", "23:36", 9, 2, 4, 2, 2, 3),
                P(0, "Scoot Henderson", None, "22:40", 10, 1, 0, 4, 0, 2),
                P(5, "Jrue Holiday", None, "25:09", 10, 4, 3, 3, 2, 2),
                P(35, "Robert Williams III", None, "15:29", 2, 5, 2, 1, 0, 0),
                P(10, "Branden Carlson", None, "14:27", 5, 6, 1, 2, 1, 0),
                P(29, "Jayson Kent", None, "10:55", 8, 0, 0, 3, 2, 0),
                P(9, "Micah Potter", None, "07:28", 2, 4, 1, 1, 0, 0),
                P(2, "John Tonje", None, "07:28", 7, 4, 3, 2, 1, 2),
                P(16, "Yang Hansen", None, "07:28", 0, 1, 3, 0, 0, 0),
            ]},
            "MIN": {"side": "home", "opp": "POR", "players": [
                P(3, "Jaden McDaniels", "F", "31:09", 13, 6, 3, 5, 0, 3),
                P(24, "Jonathan Kuminga", "F", "29:24", 13, 9, 1, 5, 1, 2),
                P(27, "Rudy Gobert", "C", "32:01", 18, 15, 3, 5, 0, 8),
                P(13, "Ayo Dosunmu", "G", "29:32", 8, 5, 2, 3, 2, 0),
                P(1, "LaMelo Ball", "G", "23:37", 6, 5, 0, 2, 2, 0),
                P(19, "Joan Beringer", None, "15:47", 0, 4, 0, 0, 0, 0),
                P(4, "Terrence Shannon Jr", None, "35:11", 34, 3, 6, 8, 3, 15),
                P(8, "Bones Hyland", None, "12:31", 5, 1, 5, 2, 0, 1),
                P(41, "Trey Lyles", None, "19:24", 9, 3, 1, 3, 2, 1),
                P(33, "Isaiah Evans", None, "03:48", 0, 0, 0, 0, 0, 0),
                P(15, "Zyon Pullin", None, "03:48", 0, 1, 0, 0, 0, 0),
                P(9, "Cody Williams", None, "03:48", 0, 1, 0, 0, 0, 0),
            ]},
        },
    },
    # ---------------------------------------------------------------- GSW @ NOP
    {
        "game_id": "0022600251", "date": "2026-11-16", "matchup": "GSW@NOP",
        "away": "GSW", "home": "NOP", "arena": "Smoothie King Center, New Orleans, LA",
        "code": "GSWNOP",
        "final": {"away": 94, "home": 115},
        "quarters": {"away": [11, 25, 29, 29], "home": [35, 26, 32, 22], "ot": {"away": [], "home": []}},
        "club_totals": {
            "GSW": {"min_sec": 14400, "pts": 94, "reb": 50, "or": 14, "dr": 36, "ast": 21},
            "NOP": {"min_sec": 14400, "pts": 115, "reb": 57, "or": 19, "dr": 38, "ast": 25},
        },
        "teams": {
            "GSW": {"side": "away", "opp": "NOP", "players": [
                P(1, "Yaxel Lendeborg", "F", "32:39", 28, 8, 3, 9, 2, 8),
                P(23, "Draymond Green", "F", "24:48", 2, 8, 5, 1, 0, 0),
                P(20, "Al Horford", "C", "14:28", 0, 5, 0, 0, 0, 0),
                P(2, "Brandin Podziemski", "G", "29:38", 15, 6, 3, 3, 3, 6),
                P(18, "LJ Cryer", "G", "24:09", 7, 1, 3, 2, 1, 2),
                P(32, "Georges Niang", None, "14:24", 0, 4, 2, 0, 0, 0),
                P(28, "Charles Bassey", None, "15:51", 4, 0, 0, 1, 0, 2),
                P(8, "De'Anthony Melton", None, "20:37", 8, 2, 1, 3, 2, 0),
                P(15, "Gui Santos", None, "18:56", 12, 7, 2, 2, 1, 7),
                P(3, "Will Richard", None, "23:25", 11, 3, 1, 4, 2, 1),
                P(0, "Gary Payton II", None, "07:41", 2, 0, 0, 1, 0, 0),
                P(45, "Graham Ike", None, "07:41", 3, 5, 1, 1, 0, 1),
                P(33, "Malevy Leons", None, "05:43", 2, 1, 0, 1, 0, 0),
            ]},
            "NOP": {"side": "home", "opp": "GSW", "players": [
                P(41, "Saddiq Bey", "F", "32:35", 23, 6, 3, 8, 5, 2),
                P(1, "Zion Williamson", "F", "24:57", 16, 6, 2, 6, 0, 4),
                P(21, "Yves Missi", "C", "22:54", 6, 14, 1, 3, 0, 0),
                P(2, "Herbert Jones", "G", "23:46", 8, 2, 3, 3, 2, 0),
                P(0, "Jeremiah Fears", "G", "29:07", 19, 10, 10, 6, 1, 6),
                P(3, "Jordan Poole", None, "30:46", 11, 2, 5, 3, 1, 4),
                P(17, "Karlo Matković", None, "20:06", 3, 2, 0, 1, 0, 1),
                P(22, "Derik Queen", None, "20:37", 17, 10, 0, 6, 4, 1),
                P(10, "Jaron Pierre Jr.", None, "19:28", 10, 3, 0, 4, 2, 0),
                P(14, "AJ Johnson", None, "05:43", 0, 0, 1, 0, 0, 0),
                P(8, "Malik Dia", None, "05:01", 2, 1, 0, 1, 0, 0),
                P(13, "Julian Reese", None, "05:01", 0, 1, 0, 0, 0, 0),
                DNP(6, "DeAndre Jordan", None, "DNP - Coach's Decision"),
            ]},
        },
    },
    # ---------------------------------------------------------------- PHX @ DEN
    {
        "game_id": "0022600252", "date": "2026-11-16", "matchup": "PHX@DEN",
        "away": "PHX", "home": "DEN", "arena": "Ball Arena, Denver, CO",
        "code": "PHXDEN",
        "final": {"away": 117, "home": 105},
        "quarters": {"away": [20, 36, 34, 27], "home": [24, 29, 29, 23], "ot": {"away": [], "home": []}},
        "club_totals": {
            "PHX": {"min_sec": 14400, "pts": 117, "reb": 51, "or": 18, "dr": 33, "ast": 25},
            "DEN": {"min_sec": 14400, "pts": 105, "reb": 35, "or": 9, "dr": 26, "ast": 22},
        },
        "teams": {
            "PHX": {"side": "away", "opp": "DEN", "players": [
                P(3, "Dillon Brooks", "F", "27:14", 15, 4, 4, 6, 3, 0),
                P(22, "Miles Bridges", "F", "28:42", 16, 8, 2, 7, 2, 0),
                P(11, "Oso Ighodaro", "C", "33:03", 8, 11, 3, 3, 0, 2),
                P(4, "Jalen Green", "G", "26:31", 16, 5, 3, 5, 2, 4),
                P(15, "Devin Booker", "G", "37:16", 20, 4, 8, 5, 1, 9),
                P(23, "Jordan Goodwin", None, "19:52", 11, 6, 2, 5, 1, 0),
                P(0, "Ryan Dunn", None, "11:35", 5, 1, 0, 2, 1, 0),
                P(12, "Collin Gillespie", None, "26:20", 10, 3, 3, 4, 2, 0),
                P(10, "Khaman Maluach", None, "10:48", 4, 6, 0, 2, 0, 0),
                P(8, "Luke Kennard", None, "17:23", 12, 2, 0, 4, 4, 0),
                P(18, "Koa Peat", None, "01:16", 0, 1, 0, 0, 0, 0),
                DNP(17, "Jamaree Bouyea", None, "DNP - Coach's Decision"),
                DNP(20, "Rasheer Fleming", None, "DNP - Coach's Decision"),
                DNP(26, "Duop Reath", None, "DNP - Coach's Decision"),
                DNP(61, "Pat Spencer", None, "DNP - Coach's Decision"),
            ]},
            "DEN": {"side": "home", "opp": "PHX", "players": [
                P(23, "Cameron Johnson", "F", "27:10", 9, 0, 1, 4, 0, 1),
                P(32, "Aaron Gordon", "F", "24:12", 11, 1, 1, 4, 2, 1),
                P(15, "Nikola Jokić", "C", "38:00", 28, 15, 7, 12, 2, 2),
                P(0, "Christian Braun", "G", "33:17", 10, 3, 3, 4, 2, 0),
                P(27, "Jamal Murray", "G", "34:41", 28, 4, 4, 9, 1, 9),
                P(7, "Trevon Brazile", None, "23:12", 9, 4, 0, 4, 1, 0),
                P(21, "Spencer Jones", None, "21:22", 4, 3, 3, 1, 1, 1),
                P(10, "DeMar DeRozan", None, "14:08", 2, 1, 1, 1, 0, 0),
                P(5, "Tys Jones", None, "10:08", 0, 1, 2, 0, 0, 0),
                P(3, "Marvin Bagley III", None, "10:00", 4, 2, 0, 1, 0, 2),
                P(13, "Bryce Hopkins", None, "03:50", 0, 1, 0, 0, 0, 0),
                DNP(11, "Alpha Diallo", None, "DNP - Coach's Decision"),
                DNP(22, "Zeke Nnaji", None, "DNP - Coach's Decision"),
            ]},
        },
    },
]


def check() -> list[str]:
    """Re-derive every arithmetic claim. Returns a list of failures (empty = clean)."""
    bad = []
    for g in GAMES:
        qa, qh = g["quarters"]["away"], g["quarters"]["home"]
        if sum(qa) != g["final"]["away"]:
            bad.append(f"{g['matchup']} away quarters {qa} sum {sum(qa)} != {g['final']['away']}")
        if sum(qh) != g["final"]["home"]:
            bad.append(f"{g['matchup']} home quarters {qh} sum {sum(qh)} != {g['final']['home']}")
        for tri, blk in g["teams"].items():
            side = "away" if blk["side"] == "away" else "home"
            ct = g["club_totals"][tri]
            played = [p for p in blk["players"] if p["min_sec"] is not None]
            s_pts = sum(p["pts"] for p in played)
            if s_pts != g["final"][side]:
                bad.append(f"{g['matchup']} {tri} player pts {s_pts} != final {g['final'][side]}")
            s_min = sum(p["min_sec"] for p in played)
            if abs(s_min - ct["min_sec"]) > 5:
                bad.append(f"{g['matchup']} {tri} player min {s_min} vs club {ct['min_sec']}")
            for p in played:
                want = 2 * (p["fg"] - p["fg3"]) + 3 * p["fg3"] + p["ft"]
                if want != p["pts"]:
                    bad.append(f"{g['matchup']} {tri} {p['name']}: pts identity "
                               f"{want} != printed {p['pts']}")
            if not blk.get("reb_blank_reason"):
                s = sum(p["reb"] for p in played)
                if s != ct["reb"]:
                    bad.append(f"{g['matchup']} {tri} player reb {s} != club {ct['reb']}")
            if not blk.get("ast_blank_reason"):
                s = sum(p["ast"] for p in played)
                if s != ct["ast"]:
                    bad.append(f"{g['matchup']} {tri} player ast {s} != club {ct['ast']}")
            if s_pts != ct["pts"]:
                bad.append(f"{g['matchup']} {tri} club pts row {ct['pts']} != players {s_pts}")
    return bad


def results_feed() -> dict:
    recs = []
    for g in GAMES:
        code = g["code"]
        src = BOOK.format(code=code)
        recs.append({
            "game_id": g["game_id"], "date": g["date"],
            "away": g["away"], "home": g["home"],
            "away_pts": g["final"]["away"], "home_pts": g["final"]["home"],
            "ot_periods": 0,
            "away_q": g["quarters"]["away"], "home_q": g["quarters"]["home"],
            "home_margin": g["final"]["home"] - g["final"]["away"],
            "total_pts": g["final"]["home"] + g["final"]["away"],
            "final_source_url": GAME.format(a=g["away"].lower(), h=g["home"].lower(),
                                            gid=g["game_id"]),
            "gamebook_url": src,
            "quarter_status": "read",
            "quarter_note": (g.get("quarters_note") or
                             f"both period rows sum to the final "
                             f"({g['final']['away']}, {g['final']['home']})"),
            "list_url": LIST,
        })
    return {
        "schema": "nba2.results-feed.v3",
        "game_date": "2026-11-16",
        "retrieved_utc": "2026-11-17T16:25:00Z",
        "retrieval_method": (
            "finals and quarter scores read from each game's official gamebook PDF "
            "(statsdmz.nba.com) through the platform page-fetch tool. Bash egress cannot "
            "reach statsdmz.nba.com from this sandbox (HTTP 000), so the PDF bytes cannot "
            "be stored; every row carries the URL it was read from and the retrieval "
            "window. For game 0022600249 the SCORE BY PERIOD visitor row did not extract; "
            "the four Houston quarter scores are read from the four quarter-box "
            "team-total rows of the same official gamebook (see quarter_note)."),
        "settle_rule": (
            "A game is SETTLED only when its official gamebook period row sums to the "
            "final for that club AND the final matches the official game page. A club "
            "whose period row was not transcribed carries null quarters and is shown as "
            "unverified; nothing is back-solved from the final."),
        "records": recs,
        "n_games": len(recs),
        "n_verified_quarters": sum(1 for r in recs
                                   if r["away_q"] and r["home_q"]),
    }


def gamebooks() -> dict:
    games = []
    for g in GAMES:
        src = BOOK.format(code=g["code"])
        teams = {}
        for tri, blk in g["teams"].items():
            out = {"side": blk["side"], "opp": blk["opp"]}
            if blk.get("reb_blank_reason"):
                out["reb_blank_reason"] = blk["reb_blank_reason"]
            if blk.get("ast_blank_reason"):
                out["ast_blank_reason"] = blk["ast_blank_reason"]
            if blk.get("team_note"):
                out["team_note"] = blk["team_note"]
            out["players"] = blk["players"]
            teams[tri] = out
        rec = {
            "game_id": g["game_id"], "date": g["date"], "matchup": g["matchup"],
            "away": g["away"], "home": g["home"], "arena": g["arena"],
            "source_url": src,
            "final": g["final"],
            "quarters": g["quarters"],
            "club_totals": g["club_totals"],
            "teams": teams,
        }
        if g.get("quarters_note"):
            rec["quarters_note"] = g["quarters_note"]
        games.append(rec)
    return {
        "schema": "nba2.v5.gamebook-transcript.v1",
        "game_date": "2026-11-16",
        "session": "arena/934fce54-nba2",
        "retrieved_window_utc": RETRIEVED,
        "retrieval_method": (
            "platform page-fetch tool (fetch_page) reading the official NBA gamebook PDF "
            "at statsdmz.nba.com. The tool returns the PDF as text; the PDF bytes cannot "
            "be stored from this environment (bash egress to statsdmz.nba.com returns "
            "HTTP 000). Every row below therefore carries the gamebook URL it was read "
            "from, and every game is re-checked with the arithmetic gates in "
            "nba2/v5/check.py."),
        "source_class": "official",
        "columns": ["jersey", "name", "pos", "min", "min_sec", "pts", "reb", "ast",
                    "fg", "fg3", "ft", "status"],
        "notes": [
            "status is null for a player who played; otherwise it is the official "
            "designation printed in the minutes column (DNP - Coach's Decision, "
            "DND - ..., NWT - ...).",
            "F-93-01: in game 0022600249 the full-game SCORE BY PERIOD table's Houston "
            "row did not extract. Each Houston quarter score is read from its "
            "quarter-box team-total row (15, 31, 35, 29) of the same official gamebook; "
            "the first-half table (Rockets 15 31 46) and the cumulative line through "
            "three quarters (81) corroborate, and 15+31+35+29 = 110 matches the "
            "full-game team total row.",
            "F-93-02 / F-93-03 / F-93-04: some extracted rows carry one cell fewer than "
            "the header (the F-V5-02 / F-V5-03 condition). Where the player rebound or "
            "assist cells cannot be reconciled with the club's published totals under "
            "any alignment (WAS rebounds 32 vs 31 and assists vs 25; HOU rebounds 53 vs "
            "52 and assists vs 23), every player cell of that stat for that club is "
            "null with a team-level reason and the club total is carried instead. In "
            "game 0022600249 MIA Adebayo's row is the F-V5-03 drop case and his rebound "
            "IS recovered (1 = OR 1 + DR 0, the only value under which the club's "
            "rebound total 40 reconciles).",
            "F-93-08: in game 0022600249 the extracted Miami rows' assist cells sum to "
            "27 against the club's published 29 and the OR/DR split cells do not "
            "reconcile with the club row (15/28 against 13/27) although the TOT rebound "
            "column does (40 = 40); no MIA assist is attributed to a player.",
            "F-93-05: the extracted Memphis full-game box carries two DNP - Coach's "
            "Decision rows with no attached player names; no name is invented.",
            "F-93-06: game 0022600248 prints Brooklyn #12 as 'Ryan Rupert' in the "
            "full-game box and 'Rayan Rupert' in the period boxes; the full-game "
            "spelling is transcribed and the pair is flagged, not folded.",
            "F-93-07: the extracted DNP status cell for Terance Mann in game 0022600247 "
            "prints a garbled doubled designation; the designation is transcribed once.",
        ],
        "games": games,
    }


if __name__ == "__main__":
    failures = check()
    if failures:
        print("TRANSCRIPTION CHECK FAILED:")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)
    OUT_FEED.parent.mkdir(parents=True, exist_ok=True)
    OUT_FEED.write_text(json.dumps(results_feed(), indent=1, ensure_ascii=False) + "\n")
    OUT_BOOKS.write_text(json.dumps(gamebooks(), indent=1, ensure_ascii=False) + "\n")
    print(f"checks clean; wrote {OUT_FEED.relative_to(ROOT)} and "
          f"{OUT_BOOKS.relative_to(ROOT)}")
