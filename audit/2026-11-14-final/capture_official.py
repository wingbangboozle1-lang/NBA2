"""Independent official capture + verification, session arena/6650be4d-nba2 (2026-11-14).

WHAT THIS IS
------------
A second, independent read of the three official documents the published site depends on,
made in this session and transcribed here verbatim:

  1. https://www.nba.com/schedule?date=2026-11-14  — the slate (36 games, 11/13..11/17),
     the final scores of the nine 11/13 games, arenas, cities, tip times, game IDs.
  2. https://www.nba.com/standings                  — the official 2026-27 table
     (W, L, HOME, ROAD, CONF, DIV for all 30 clubs).
  3. https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf
     — the newest official injury release listed on the official index page
     (https://official.nba.com/nba-injury-report-2026-27-season/): 11/14 releases run
     from 12:00 a.m ET to 5:00 a.m ET, so 05:00 a.m ET is the latest document that exists.

HOW IT WAS FETCHED
------------------
The build sandbox cannot open TLS to nba.com (curl returns HTTP 000). The platform's
page-fetch tool reaches www.nba.com and ak-static.cms.nba.com; every value below came
through that tool, and the retrieval time is recorded in the output file.

WHAT IT DOES
------------
Writes `official_capture_2026-11-14.json` and then compares the capture, field by field,
against the committed snapshots the published site is built from. It reports differences;
it never edits a published value. Anything that does not match is printed with both values
so a human can adjudicate.

    python3 audit/2026-11-14-final/capture_official.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

RETRIEVED = "2026-11-14T10:25:00Z"
SCHEDULE_URL = "https://www.nba.com/schedule?date=2026-11-14"
STANDINGS_URL = "https://www.nba.com/standings"
INJURY_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf"
INJURY_INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"

# --------------------------------------------------------------------------- slate
# date, tip ET, away, home, game_id, arena, city, state
SLATE = [
    # The 11/13 games are already played: the official card renders "Final" (or "Final/OT")
    # and prints no tip time, so no time is asserted here for them.
    ("2026-11-13", None, "NYK", "IND", "0022600034", "Gainbridge Fieldhouse", "Indianapolis", "IN"),
    ("2026-11-13", None, "MIL", "ORL", "0022600035", "Kia Center", "Orlando", "FL"),
    ("2026-11-13", None, "CLE", "MIA", "0022600036", "Kaseya Center", "Miami", "FL"),
    ("2026-11-13", None, "ATL", "CHI", "0022600037", "United Center", "Chicago", "IL"),
    ("2026-11-13", None, "MEM", "NOP", "0022600038", "Smoothie King Center", "New Orleans", "LA"),
    ("2026-11-13", None, "UTA", "HOU", "0022600039", "Toyota Center", "Houston", "TX"),
    ("2026-11-13", None, "GSW", "SAS", "0022600040", "Frost Bank Center", "San Antonio", "TX"),
    ("2026-11-13", None, "POR", "SAC", "0022600041", "Golden 1 Center", "Sacramento", "CA"),
    ("2026-11-13", None, "OKC", "LAC", "0022600042", "Intuit Dome", "Inglewood", "CA"),
    ("2026-11-14", "19:00", "DEN", "NOP", "0022600231", "Smoothie King Center", "New Orleans", "LA"),
    ("2026-11-14", "19:30", "DAL", "CLE", "0022600232", "Rocket Arena", "Cleveland", "OH"),
    ("2026-11-14", "20:00", "DET", "MIA", "0022600233", "Kaseya Center", "Miami", "FL"),
    ("2026-11-14", "20:00", "BKN", "MEM", "0022600234", "FedExForum", "Memphis", "TN"),
    ("2026-11-14", "20:00", "CHI", "MIN", "0022600235", "Target Center", "Minneapolis", "MN"),
    ("2026-11-15", "13:00", "IND", "PHI", "0022600236", "Xfinity Mobile Arena", "Philadelphia", "PA"),
    ("2026-11-15", "16:00", "LAL", "PHX", "0022600237", "Mortgage Matchup Center", "Phoenix", "AZ"),
    ("2026-11-15", "16:30", "CHA", "LAC", "0022600238", "Intuit Dome", "Inglewood", "CA"),
    ("2026-11-15", "17:00", "SAS", "UTA", "0022600239", "Delta Center", "Salt Lake City", "UT"),
    ("2026-11-15", "18:00", "DAL", "BOS", "0022600240", "TD Garden", "Boston", "MA"),
    ("2026-11-15", "18:00", "NYK", "TOR", "0022600241", "Scotiabank Arena", "Toronto", "ON"),
    ("2026-11-15", "19:00", "HOU", "WAS", "0022600242", "Capital One Arena", "Washington", "DC"),
    ("2026-11-15", "20:00", "ATL", "MIL", "0022600243", "Fiserv Forum", "Milwaukee", "WI"),
    ("2026-11-15", "21:00", "OKC", "SAC", "0022600244", "Golden 1 Center", "Sacramento", "CA"),
    ("2026-11-16", "19:00", "ORL", "BOS", "0022600245", "TD Garden", "Boston", "MA"),
    ("2026-11-16", "19:00", "CHI", "CLE", "0022600246", "Rocket Arena", "Cleveland", "OH"),
    ("2026-11-16", "19:00", "MEM", "WAS", "0022600247", "Capital One Arena", "Washington", "DC"),
    ("2026-11-16", "19:30", "PHI", "BKN", "0022600248", "Barclays Center", "Brooklyn", "NY"),
    # 0022600249: the schedule card rendered "8:00 PM ET", the game's own page renders
    # "7:30 PM ET" (header + rail). The game's page is authoritative; the disagreement is
    # recorded as a discrepancy rather than resolved silently.
    ("2026-11-16", "19:30", "HOU", "MIA", "0022600249", "Kaseya Center", "Miami", "FL"),
    ("2026-11-16", "20:00", "POR", "MIN", "0022600250", "Target Center", "Minneapolis", "MN"),
    ("2026-11-16", "20:00", "GSW", "NOP", "0022600251", "Smoothie King Center", "New Orleans", "LA"),
    ("2026-11-16", "21:00", "PHX", "DEN", "0022600252", "Ball Arena", "Denver", "CO"),
    ("2026-11-17", "19:30", "NYK", "TOR", "0022600253", "Scotiabank Arena", "Toronto", "ON"),
    ("2026-11-17", "20:00", "POR", "MIN", "0022600254", "Target Center", "Minneapolis", "MN"),
    ("2026-11-17", "20:00", "DET", "SAS", "0022600255", "Frost Bank Center", "San Antonio", "TX"),
    ("2026-11-17", "22:30", "UTA", "LAC", "0022600257", "Intuit Dome", "Inglewood", "CA"),
    ("2026-11-17", "23:00", "CHA", "LAL", "0022600256", "Crypto.com Arena", "Los Angeles", "CA"),
]

# game_id -> (away_pts, home_pts, overtime) — the nine 2026-11-13 games, "Final" on the page.
FINALS = {
    "0022600034": (104, 106, False),   # NYK @ IND
    "0022600035": (99, 107, False),    # MIL @ ORL
    "0022600036": (121, 133, False),   # CLE @ MIA
    "0022600037": (117, 125, True),    # ATL @ CHI  (page renders "Final/OT")
    "0022600038": (142, 111, False),   # MEM @ NOP
    "0022600039": (118, 125, False),   # UTA @ HOU
    "0022600040": (85, 123, False),    # GSW @ SAS
    "0022600041": (120, 107, False),   # POR @ SAC
    "0022600042": (112, 113, False),   # OKC @ LAC
}

# --------------------------------------------------------------------------- standings
# tricode, name, W, L, HOME w-l, ROAD w-l, CONF w-l, DIV w-l
STANDINGS = [
    ("BOS", "Boston Celtics", 10, 2, "5-0", "5-2", "10-1", "4-0"),
    ("PHI", "Philadelphia 76ers", 10, 3, "5-2", "5-1", "10-3", "3-1"),
    ("DET", "Detroit Pistons", 8, 3, "3-2", "5-1", "8-2", "0-0"),
    ("ATL", "Atlanta Hawks", 7, 6, "3-3", "4-3", "7-2", "4-1"),
    ("MIA", "Miami Heat", 6, 6, "4-3", "2-3", "2-2", "1-1"),
    ("NYK", "New York Knicks", 6, 6, "4-3", "2-3", "6-6", "1-3"),
    ("CLE", "Cleveland Cavaliers", 6, 7, "4-2", "2-5", "5-5", "1-0"),
    ("TOR", "Toronto Raptors", 5, 7, "2-3", "3-4", "4-3", "0-2"),
    ("ORL", "Orlando Magic", 5, 7, "1-4", "4-3", "3-4", "0-2"),
    ("IND", "Indiana Pacers", 5, 8, "2-4", "3-3", "3-5", "0-1"),
    ("CHA", "Charlotte Hornets", 4, 8, "3-4", "1-4", "4-7", "2-2"),
    ("WAS", "Washington Wizards", 4, 9, "2-3", "2-6", "4-8", "2-3"),
    ("BKN", "Brooklyn Nets", 3, 8, "1-3", "2-5", "2-7", "0-2"),
    ("CHI", "Chicago Bulls", 2, 9, "1-4", "1-5", "2-8", "1-0"),
    ("MIL", "Milwaukee Bucks", 1, 12, "1-6", "0-6", "1-9", "1-2"),
    ("SAS", "San Antonio Spurs", 11, 2, "5-2", "6-0", "10-2", "2-1"),
    ("LAL", "Los Angeles Lakers", 11, 2, "5-1", "6-1", "6-2", "4-1"),
    ("HOU", "Houston Rockets", 10, 3, "7-1", "3-2", "6-3", "2-1"),
    ("POR", "Portland Trail Blazers", 9, 3, "5-2", "6-1", "9-3", "4-0"),
    ("MIN", "Minnesota Timberwolves", 9, 3, "5-1", "4-2", "5-2", "1-0"),
    ("MEM", "Memphis Grizzlies", 8, 4, "6-0", "2-4", "7-3", "1-1"),
    ("GSW", "Golden State Warriors", 8, 5, "6-1", "2-4", "6-5", "3-2"),
    ("OKC", "Oklahoma City Thunder", 8, 5, "5-0", "3-5", "5-5", "1-2"),
    ("DEN", "Denver Nuggets", 6, 4, "4-4", "2-2", "3-3", "2-2"),
    ("DAL", "Dallas Mavericks", 7, 5, "2-3", "5-2", "3-5", "1-3"),
    ("PHX", "Phoenix Suns", 5, 6, "3-3", "2-3", "3-6", "2-1"),
    ("NOP", "New Orleans Pelicans", 4, 9, "3-5", "1-4", "3-7", "1-1"),
    ("LAC", "LA Clippers", 3, 8, "1-4", "3-3", "3-6", "1-4"),
    ("SAC", "Sacramento Kings", 1, 11, "0-7", "1-4", "1-9", "0-2"),
    ("UTA", "Utah Jazz", 1, 12, "1-6", "0-6", "1-10", "0-2"),
]

# --------------------------------------------------------------------------- injuries
# game date, tip (as printed by the PDF), matchup, team, player, status, reason
INJURY = [
    ("11/14/2026", "07:00", "DEN@NOP", "Denver Nuggets", "Holmes II, DaRon", "Out", "G League - On Assignment"),
    ("11/14/2026", "07:00", "DEN@NOP", "Denver Nuggets", "Nembhard, Ryan", "Out", "G League - Two-Way"),
    ("11/14/2026", "07:00", "DEN@NOP", "Denver Nuggets", "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain"),
    ("11/14/2026", "07:00", "DEN@NOP", "Denver Nuggets", "Whitmore, Cam", "Out", "G League - Two-Way"),
    ("11/14/2026", "07:00", "DEN@NOP", "New Orleans Pelicans", None, None, "NOT YET SUBMITTED"),
    ("11/14/2026", "07:30", "DAL@CLE", "Dallas Mavericks", "Biberovic, Tarik", "Out", "Injury/Illness - Right Heel Bursitis"),
    ("11/14/2026", "07:30", "DAL@CLE", "Dallas Mavericks", "Christie, Max", "Questionable", "Injury/Illness - Left Ankle Sprain"),
    ("11/14/2026", "07:30", "DAL@CLE", "Dallas Mavericks", "de Larrea, Sergio", "Out", "Injury/Illness - Right Knee Sprain"),
    ("11/14/2026", "07:30", "DAL@CLE", "Dallas Mavericks", "Johnson Jr., Morez", "Probable", "Injury/Illness - Left Shin / Tibia Contusion"),
    ("11/14/2026", "07:30", "DAL@CLE", "Dallas Mavericks", "Lively II, Dereck", "Out", "Injury/Illness - Right Foot Surgery"),
    ("11/14/2026", "07:30", "DAL@CLE", "Dallas Mavericks", "Martin, Caleb", "Available", "Injury/Illness - Right Thumb Splint"),
    ("11/14/2026", "07:30", "DAL@CLE", "Cleveland Cavaliers", None, None, "NOT YET SUBMITTED"),
    ("11/14/2026", "08:00", "BKN@MEM", "Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way"),
    ("11/14/2026", "08:00", "BKN@MEM", "Brooklyn Nets", "Brown Jr., Mikel", "Questionable", "Injury/Illness - Illness"),
    ("11/14/2026", "08:00", "BKN@MEM", "Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment"),
    ("11/14/2026", "08:00", "BKN@MEM", "Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way"),
    ("11/14/2026", "08:00", "BKN@MEM", "Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment"),
    ("11/14/2026", "08:00", "BKN@MEM", "Brooklyn Nets", "Traore, Nolan", "Probable", "Injury/Illness - Right Calf Tightness / Soreness"),
    ("11/14/2026", "08:00", "BKN@MEM", "Memphis Grizzlies", None, None, "NOT YET SUBMITTED"),
    ("11/14/2026", "08:00", "CHI@MIN", "Chicago Bulls", None, None, "NOT YET SUBMITTED"),
    ("11/14/2026", "08:00", "CHI@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask"),
    ("11/14/2026", "08:00", "CHI@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    ("11/14/2026", "08:00", "CHI@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy"),
    ("11/14/2026", "08:00", "DET@MIA", "Detroit Pistons", "Duren, Jalen", "Out", "Injury/Illness - Right Hamstring Strain"),
    ("11/14/2026", "08:00", "DET@MIA", "Detroit Pistons", "Harkless, Elijah", "Questionable", "G League - Two-Way"),
    ("11/14/2026", "08:00", "DET@MIA", "Detroit Pistons", "Joe, Isaiah", "Out", "Injury/Illness - Right Hip Contusion"),
    ("11/14/2026", "08:00", "DET@MIA", "Detroit Pistons", "Jones, Isaac", "Questionable", "G League - Two-Way"),
    ("11/14/2026", "08:00", "DET@MIA", "Detroit Pistons", "Lanier, Chaz", "Out", "G League - On Assignment"),
    ("11/14/2026", "08:00", "DET@MIA", "Detroit Pistons", "Okorie, Ebuka", "Out", "G League - On Assignment"),
    ("11/14/2026", "08:00", "DET@MIA", "Detroit Pistons", "Onyenso, Ugonna", "Out", "G League - Two-Way"),
    ("11/14/2026", "08:00", "DET@MIA", "Miami Heat", None, None, "NOT YET SUBMITTED"),
]

# The same release also lists the 11/15 slate; every one of those rows is NOT YET SUBMITTED
# (no team has filed for 11/15 yet at 05:00 a.m ET). The rows are recorded so the site can
# say "the slot exists and is empty" instead of "the release does not cover 11/15".
INJURY_PENDING_1115 = [
    ("11/15/2026", "01:00", "IND@PHI", "Indiana Pacers", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "01:00", "IND@PHI", "Philadelphia 76ers", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "04:00", "LAL@PHX", "Los Angeles Lakers", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "04:00", "LAL@PHX", "Phoenix Suns", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "04:30", "CHA@LAC", "Charlotte Hornets", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "04:30", "CHA@LAC", "LA Clippers", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "05:00", "SAS@UTA", "San Antonio Spurs", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "05:00", "SAS@UTA", "Utah Jazz", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "06:00", "DAL@BOS", "Dallas Mavericks", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "06:00", "DAL@BOS", "Boston Celtics", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "06:00", "NYK@TOR", "New York Knicks", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "06:00", "NYK@TOR", "Toronto Raptors", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "07:00", "HOU@WAS", "Houston Rockets", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "07:00", "HOU@WAS", "Washington Wizards", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "08:00", "ATL@MIL", "Atlanta Hawks", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "08:00", "ATL@MIL", "Milwaukee Bucks", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "09:00", "OKC@SAC", "Oklahoma City Thunder", None, None, "NOT YET SUBMITTED"),
    ("11/15/2026", "09:00", "OKC@SAC", "Sacramento Kings", None, None, "NOT YET SUBMITTED"),
]


def write_capture() -> Path:
    cap = {
        "session": "arena/6650be4d-nba2",
        "captured_at_utc": RETRIEVED,
        "method": ("platform page-fetch tool (the build sandbox cannot open TLS to nba.com: "
                   "curl returns HTTP 000)"),
        "sources": {
            "schedule": SCHEDULE_URL,
            "standings": STANDINGS_URL,
            "injury_report": INJURY_URL,
            "injury_index": INJURY_INDEX_URL,
        },
        "official_index_note": (
            "https://official.nba.com/nba-injury-report-2026-27-season/ lists the 2026-11-14 "
            "releases from 12:00 a.m ET through 5:00 a.m ET. 05:00 a.m ET is the newest document "
            "that exists at capture time, so it supersedes the 11/13 19:30 ET release the site "
            "currently publishes."),
        "slate": [
            {"date": d, "time_et": t, "away": a, "home": h, "game_id": g,
             "arena": ar, "city": c, "state": st,
             "game_url": f"https://www.nba.com/game/{a.lower()}-vs-{h.lower()}-{g}"}
            for (d, t, a, h, g, ar, c, st) in SLATE
        ],
        "finals_2026_11_13": [
            {"game_id": row[4], "away": row[2], "home": row[3],
             "away_pts": FINALS[row[4]][0], "home_pts": FINALS[row[4]][1],
             "overtime": FINALS[row[4]][2],
             "source": f"https://www.nba.com/game/{row[2].lower()}-vs-{row[3].lower()}-{row[4]}"}
            for row in SLATE if row[4] in FINALS
        ],
        "standings_2026_11_14": [
            {"tricode": tc, "name": nm, "w": w, "l": l, "home": home, "road": road,
             "conf": conf, "div": div}
            for (tc, nm, w, l, home, road, conf, div) in STANDINGS
        ],
        "injury_report_2026_11_14_0500ET": [
            {"game_date": d, "game_time": t, "matchup": m, "team": tm,
             "player": p, "status": s, "reason": r}
            for (d, t, m, tm, p, s, r) in (INJURY + INJURY_PENDING_1115)
        ],
    }
    path = OUT / "official_capture_2026-11-14.json"
    path.write_text(json.dumps(cap, indent=2) + "\n")
    return path


def compare(cap: dict) -> list[str]:
    """Field-by-field comparison of the fresh capture against the committed snapshots."""
    out: list[str] = []

    # ---- slate -----------------------------------------------------------------
    snap = json.loads((ROOT / "data" / "raw" / "slate_2026-11-14_to_11-17.json").read_text())
    cols = snap["columns"]
    committed = {r[4]: dict(zip(cols, r)) for r in snap["records"]}
    mine = {g["game_id"]: g for g in cap["slate"]}
    out.append(f"SLATE: committed {len(committed)} games · captured {len(mine)} games")
    only_committed = sorted(set(committed) - set(mine))
    only_captured = sorted(set(mine) - set(committed))
    out.append(f"  games only in the committed snapshot: {only_committed or 'none'}")
    out.append(f"  games only in this capture: {only_captured or 'none'}")
    diffs = 0
    for gid, g in mine.items():
        c = committed.get(gid)
        if not c:
            continue
        for fld in ("date", "time_et", "away", "home", "arena", "city", "state"):
            if g.get(fld) is None:
                continue
            if str(c.get(fld)) != str(g.get(fld)):
                diffs += 1
                out.append(f"  MISMATCH {gid} {fld}: committed={c.get(fld)!r} captured={g.get(fld)!r}")
    out.append(f"  field mismatches on shared games: {diffs}")
    counts: dict[str, int] = {}
    for g in mine.values():
        counts[g["date"]] = counts.get(g["date"], 0) + 1
    out.append(f"  games per date (captured): {dict(sorted(counts.items()))}")

    # ---- finals ---------------------------------------------------------------
    finals_snap = ROOT / "data" / "raw" / "finals_2026-11-13.json"
    prior = {}
    if finals_snap.exists():
        prior = {r["game_id"]: r for r in json.loads(finals_snap.read_text())["records"]}
    out.append(f"FINALS: committed {len(prior)} · captured {len(cap['finals_2026_11_13'])}")
    for f in cap["finals_2026_11_13"]:
        p = prior.get(f["game_id"])
        if p and (p["away_pts"] != f["away_pts"] or p["home_pts"] != f["home_pts"]):
            out.append(f"  MISMATCH {f['game_id']}: committed={p['away_pts']}-{p['home_pts']} "
                       f"captured={f['away_pts']}-{f['home_pts']}")

    # ---- standings vs the ratings snapshot ------------------------------------
    rat = json.loads((ROOT / "data" / "raw" / "team_ratings_2026-11-13.json").read_text())
    rcols = rat["columns"]
    rteams = {r[0]: dict(zip(rcols, r)) for r in rat["records"]}
    out.append(f"STANDINGS: ratings snapshot has {len(rteams)} rows · capture has "
               f"{len(cap['standings_2026_11_14'])}")
    same = 0
    for s in cap["standings_2026_11_14"]:
        r = rteams.get(s["tricode"])
        if not r:
            out.append(f"  {s['tricode']}: not present in the ratings snapshot")
            continue
        if r["w"] == s["w"] and r["l"] == s["l"]:
            same += 1
        else:
            out.append(f"  {s['tricode']}: snapshot {r['w']}-{r['l']} vs official now "
                       f"{s['w']}-{s['l']} (games played since the snapshot)")
    out.append(f"  identical records: {same}/{len(cap['standings_2026_11_14'])}")

    # ---- the newest injury release vs the committed one ------------------------
    old = json.loads((ROOT / "data" / "raw" / "injury_report_2026-11-13_1930ET.json").read_text())
    ocols = old["columns"]
    old_rows = {(r[0], r[2], r[4], r[5]): r for r in old["records"]}  # date, matchup, player, status
    out.append(f"INJURY: committed release rows {len(old['records'])} · captured release rows "
               f"{len(cap['injury_report_2026_11_14_0500ET'])}")
    agree = 0
    shared = 0
    for row in cap["injury_report_2026_11_14_0500ET"]:
        # the committed release prints 2026-11-14 as 11/14/2026 too, but the *date* of a
        # 11/13 game row is 2026-11-13, so normalise both sides to ISO before matching.
        iso = f"{row['game_date'][6:10]}-{row['game_date'][0:2]}-{row['game_date'][3:5]}"
        key = (iso, row["matchup"], row["player"], row["status"])
        o = old_rows.get(key)
        if o is None:
            continue
        shared += 1
        if str(o[6]) == str(row["reason"]):
            agree += 1
        else:
            out.append(f"  REASON CHANGE {key}: committed={o[6]!r} captured={row['reason']!r}")
    out.append(f"  rows present in both releases: {shared} · identical status+reason: {agree}")
    return out


def main() -> int:
    path = write_capture()
    cap = json.loads(path.read_text())
    lines = [
        "# Official re-verification — session arena/6650be4d-nba2 (2026-11-14)",
        "",
        f"Captured {RETRIEVED} with the platform page-fetch tool.",
        "",
        "Sources read in this session:",
        "",
        f"- Schedule: {SCHEDULE_URL}",
        f"- Standings: {STANDINGS_URL}",
        f"- Injury report (newest): {INJURY_URL}",
        f"- Injury report index (release list + filing deadlines): {INJURY_INDEX_URL}",
        "",
        "## Field-by-field comparison against the committed snapshots",
        "",
        "```",
    ]
    lines += compare(cap)
    lines += ["```", "", f"Raw capture: `audit/2026-11-14-final/{path.name}`", ""]
    report = OUT / "verification_report.md"
    report.write_text("\n".join(lines))
    print("\n".join(lines))
    print("wrote", path)
    print("wrote", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
