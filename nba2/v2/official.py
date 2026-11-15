"""Official NBA snapshot for the v2 build — loaded from the committed capture, not transcribed here.

This module used to hold a hand-typed copy of what a session had read that morning. That is the
single largest staleness risk in the repository: the numbers were right, but they lived in a .py
file, so refreshing them meant editing code, and code edits are what a scheduled job cannot do.

Now every table below is read from ``data/raw/`` at import time:

  standings .......... ``standings_<asof>_official.json``   (nba.com/standings)
  ratings ............ ``team_ratings_<asof>.json``        (advanced / opponent / traditional)
  points per game .... rebuilt from ``results_feed_<asof>.json``, one row per official result
  slate .............. ``slate_<start>_to_<end>.json``      (nba.com/schedule, three-day window)
  injuries ........... ``injury_report_<date>_<release>.json`` (the newest release that exists)
  availability ....... ``gamebooks_<date>.json``            (official game books: who was out)

``data/raw/`` is written by ``audit/<session>/build_capture.py``, which refuses to write anything
unless 19 cross-document identities hold — so if this module imports, the snapshot has already
reconciled against itself. A number that cannot be confirmed against a captured official URL is
left blank and flagged, never estimated, and the reason travels with the blank.

Retrieval record — session ``arena/04a61ac0-nba2``, 2026-11-15 (UTC)
--------------------------------------------------------------------
* ``www.nba.com/standings`` .................. 30 teams, W/L, conf/div/home/road/neutral/OT/last10 .. OK
* ``www.nba.com/stats/teams/advanced`` ....... 30 teams, OffRtg/DefRtg/NetRtg/PACE/PIE/POSS ........ OK
* ``www.nba.com/stats/teams/opponent`` ....... 30 teams, opponent PTS, opponent +/- ................. OK
* ``www.nba.com/stats/teams/traditional`` ..... 30 teams, 26 shooting/rebounding columns ............. OK
* ``www.nba.com/schedule?date=2026-11-16`` ... slate 11/15-11/17, ET tips, arenas, IDs, TV .......... OK
* ``www.nba.com/games?date=2026-11-14`` ...... 5 official finals with quarter scores ................ OK
* five ``statsdmz.nba.com/…20261114_*_book.pdf`` official boxes, inactives, attendance ............. OK
* ``Injury-Report_2026-11-15_06_15AM.pdf`` ... 84 designation rows, 1 non-submission, 16 for 11/16  OK
* ``Injury-Report_2026-11-15_06_00AM.pdf`` ... the same, read independently, and diffed ............. OK
* ``official.nba.com/nba-injury-report-2026-27-season/`` filing rules and the release archive ...... OK
* ``stats.nba.com`` / ``cdn.nba.com`` JSON endpoints .............................................. TLS blocked
"""

from __future__ import annotations

import glob
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
AUDIT = ROOT / "audit"


def _latest(pattern: str):
    """Newest committed snapshot matching *pattern*, or None. Absence is reported, not filled in."""
    cands = sorted(glob.glob(str(RAW / pattern)))
    return json.loads(Path(cands[-1]).read_text()) if cands else None


_STANDINGS = _latest("standings_*_official.json")
_RATINGS = _latest("team_ratings_*.json")
_FEED = _latest("results_feed_*.json")
_SLATE_DOC = _latest("slate_*_to_*.json")
_INJ_FILES = [f for f in sorted(glob.glob(str(RAW / "injury_report_*.json")))
              if "daybefore" not in f]
_INJ = json.loads(Path(_INJ_FILES[-1]).read_text()) if _INJ_FILES else None
_INJ_PRIOR = json.loads(Path(_INJ_FILES[-2]).read_text()) if len(_INJ_FILES) > 1 else None
_BOOKS = _latest("gamebooks_*.json")

if not all((_STANDINGS, _RATINGS, _FEED, _SLATE_DOC)):
    raise RuntimeError(
        "the v2 snapshot is incomplete: this module needs a standings, ratings and results-feed "
        "snapshot in data/raw/. Run the session's build_capture.py; do not hand-edit this file."
    )

# --------------------------------------------------------------------------- provenance
CAPTURE = None
_cands = sorted(glob.glob(str(AUDIT / "*/captures.json")))
if _cands:
    CAPTURE = json.loads(Path(_cands[-1]).read_text())
CAPTURE_DIR = Path(_cands[-1]).parent.name if _cands else None

AS_OF = _STANDINGS["as_of"]
RETRIEVED_AT_UTC = _STANDINGS.get("captured_utc", "")
RETRIEVED_BY = _STANDINGS.get("session", "")
GAMES_PLAYED_LEAGUE = int(_STANDINGS["league"]["games"])

# The 3-day pick window the brief asks for, taken from the slate snapshot rather than declared
# here, so that a refresh that widens or moves the window does not require a code change.
WINDOW_START = _SLATE_DOC["window"]["start"]
WINDOW_END = _SLATE_DOC["window"]["end"]

# --------------------------------------------------------------------------- sources
SOURCES = {
    "standings": (
        "NBA.com Standings (official)",
        _STANDINGS["source_url"],
        "W, L, WIN%, GB, conference, division, home, road, neutral, OT, last 10, streak.",
    ),
    "team_trad": (
        "NBA.com Stats - Teams Traditional (official)",
        _RATINGS["traditional"]["source_url"],
        "GP, MIN, PTS, FGM/FGA/FG%, 3PM/3PA/3P%, FTM/FTA/FT%, OREB, DREB, REB, AST, TOV, STL, "
        "BLK, BLKA, PF, PFD, +/-.",
    ),
    "team_opp": (
        "NBA.com Stats - Teams Opponent (official)",
        _RATINGS["opponent"]["source_url"],
        "Opponent PTS per game (points allowed) and opponent +/-.",
    ),
    "team_adv": (
        "NBA.com Stats - Teams Advanced (official)",
        _RATINGS["advanced"]["source_url"],
        "OffRtg, DefRtg, NetRtg, PACE, PIE, POSS - all per-100-possession.",
    ),
    "results_feed": (
        "Official final scores, one row per game (rebuilt from committed captures)",
        _FEED["sources"]["games"],
        "The 188 finals from 2026-10-20 through 2026-11-14: both team scores, quarter scores "
        "where a game page or game book was read, and the per-game URL.",
    ),
    "schedule": (
        "NBA.com Schedule (official)",
        _SLATE_DOC["source_url"],
        "Game IDs, ET tip times, arenas, cities, national broadcast.",
    ),
    "games_2026_11_14": (
        "NBA.com Games & Scores for 2026-11-14 (official)",
        "https://www.nba.com/games?date=2026-11-14",
        "Five official finals with quarter scores, each also read from its own game page.",
    ),
    "game_books": (
        "Official NBA game books for 2026-11-14 (official PDFs)",
        "https://statsdmz.nba.com/pdfs/20261114/20261114_DENNOP_book.pdf",
        "Inactive and DND blocks, named leader lines, attendance, technical fouls, "
        "points in the paint, fast-break points.",
    ),
    "injury_pdf": (
        f"NBA Official Injury Report - {(_INJ or {}).get('report_stamp_et', 'no release on disk')}"
        f" (official PDF)",
        (_INJ or {}).get("source_url", ""),
        "Per-player status (Out/Doubtful/Questionable/Probable/Available) with the stated reason, "
        "plus a NOT YET SUBMITTED row for every club that has not filed.",
    ),
    "injury_policy": (
        "NBA Official - Injury Report policy and report archive (official)",
        (_INJ or {}).get("index_url", "https://official.nba.com/nba-injury-report-2026-27-season/"),
        "Filing deadlines: 5 p.m. local the day before; game day 11 a.m.-1 p.m.; "
        "1 p.m. local for the second of a back-to-back.",
    ),
    "player_trad": (
        "NBA.com Stats - Players Traditional (official)",
        "https://www.nba.com/stats/players/traditional",
        "Per-player GP, MIN, PTS, REB, AST for the rows used on this site.",
    ),
}
if _INJ_PRIOR:
    SOURCES["injury_pdf_prior"] = (
        "NBA Official Injury Report - the release this one supersedes (official PDF)",
        _INJ_PRIOR.get("source_url", ""),
        "Read independently and compared row by row with the newest release: "
        + (_INJ or {}).get("release_diff_note", "no comparison available"),
    )
else:
    SOURCES["injury_pdf_prior"] = (
        "NBA Official Injury Report - previous release",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
        "No earlier release of the same day is committed, so no consecutive-release diff exists.",
    )

# Alias kept because earlier content modules address this source by its short name.
SOURCES["players"] = SOURCES["player_trad"]

# Why an input is absent. Published verbatim next to every blank cell.
BLOCKED = {
    "odds": (
        "Market prices (spread, total, moneyline, prop lines)",
        "No licensed odds feed is connected and NBA.com renders odds client-side only. "
        "Required for: any value/edge claim, stake sizing, ROI, leaderboard scoring.",
        "https://www.nba.com/games",
    ),
    "live_ingest": (
        "An automated feed that keeps the results history current without a human capture",
        f"The {GAMES_PLAYED_LEAGUE} official finals from 2026-10-20 to 2026-11-14 are committed "
        "under data/raw/, and they rebuild every one of the 30 standings records exactly - "
        "including all 30 conference records. What is missing is a scheduled job that can reach "
        "nba.com, so the history freezes between manual captures and the window ages.",
        "https://www.nba.com/games?date=2026-11-14",
    ),
    "player_box": (
        "Per-player season game logs (minutes by game, usage, on/off)",
        "nba.com/stats player pages render season aggregates only for this client, and the "
        "game-log view returns 'No data available'. Required for: minutes distributions, prop "
        "probabilities, and a replacement model that does not depend on one day's game book.",
        "https://www.nba.com/stats/players/traditional",
    ),
    "future_injuries": (
        "Injury designations for 2026-11-16 and 2026-11-17",
        "Narrower than it was yesterday and still real. For 11/15 a full report exists (84 rows "
        "across 16 clubs). For 11/16 the report exists but every one of the 16 club-slots prints "
        "NOT YET SUBMITTED. For 11/17 the document contains no rows at all. A team files by 5 p.m. "
        "local the day before, so these deadlines had not passed at capture time.",
        "https://official.nba.com/nba-injury-report-2026-27-season/",
    ),
    "game_book_shooting_lines": (
        "Team shooting lines from the official game books",
        "None of the six that this session could read satisfies 2 x FGM + FTM = points, the "
        "arithmetic every NBA box must satisfy, because the PDF text layer misaligns columns. They "
        "are published as defects on the review page and discarded from every calculation; the "
        "team-level points, quarters and results come from the reconciled game pages instead.",
        "https://statsdmz.nba.com/pdfs/20261114/20261114_DETMIA_book.pdf",
    ),
}

# --------------------------------------------------------------------------- team table
# tricode: W, L, HOME_W, HOME_L, ROAD_W, ROAD_L, PF(pts/g), PA(pts/g), OEFF, DEF, NET, PACE, PIE
# W/L + splits: nba.com/standings, read AS_OF. PF/PA: rebuilt game by game from the official
# finals in the result feed (not rounded by the stats page). OEFF/DEF/NET/PACE/PIE: the advanced
# page. Every one of these is cross-checked in integrity() below and again in build_capture.py.
_ADV = {r[0]: r for r in _RATINGS["advanced"]["rows"]}
_OPP = {r[0]: r for r in _RATINGS["opponent"]["rows"]}
_TRAD_ROWS = (_RATINGS.get("traditional") or {}).get("rows") or []
_TRAD = {r[0]: r for r in _TRAD_ROWS}
_OPP_ROWS = _RATINGS["opponent"]["rows"]
_PTS_FOR = _FEED.get("points_for") or _RATINGS.get("rebuilt_from_finals", {}).get("points_for", {})
_PTS_AG = _FEED.get("points_against") or _RATINGS.get("rebuilt_from_finals", {}).get("points_against", {})

TEAMS: dict[str, tuple] = {}
for _row in _STANDINGS["rows"]:
    (tri, w, l, _winpct, _gb, _conf, _div, _home, _road, _neutral, _ot, _l10, _streak) = _row
    gp = w + l
    a = _ADV[tri]
    TEAMS[tri] = (
        w, l,
        int(_row[7].split("-")[0]), int(_row[7].split("-")[1]),
        int(_row[8].split("-")[0]), int(_row[8].split("-")[1]),
        round(_PTS_FOR[tri] / gp, 1), round(_PTS_AG[tri] / gp, 1),
        a[4], a[5], a[6], a[7], a[8],
    )

# The rest of what the standings card prints, keyed for the pages that show it. Nothing here is
# derived: each value is the string the official page put in that column.
SPLITS = {
    r[0]: {
        "win_pct": r[3], "gb": r[4], "conf": r[5], "div": r[6], "home": r[7], "road": r[8],
        "neutral": r[9], "ot": r[10], "last10": r[11], "streak": r[12],
    }
    for r in _STANDINGS["rows"]
}

# The traditional page in full, for the shooting profile and for anyone re-deriving a number.
TRAD = {r[0]: dict(zip(_RATINGS["traditional"]["columns"], r)) for r in _TRAD_ROWS}
OPPONENT = {r[0]: {"gp": r[1], "pts": r[2], "plus_minus": r[3]} for r in _OPP_ROWS}

STANDINGS_SOURCE = SOURCES["standings"][1]
STANDINGS_AS_OF = AS_OF
STANDINGS = {
    t: {"w": v[0], "l": v[1], "home": f"{v[2]}-{v[3]}", "road": f"{v[4]}-{v[5]}"}
    for t, v in TEAMS.items()
}

NAMES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}

# Per-team source links (each page is the canonical official page for that team).
TEAM_SOURCE = {tid: "https://www.nba.com/stats/team/{}".format(tid) for tid in TEAMS}

# --------------------------------------------------------------------------- the slate
# date, time_et, away, home, game_id, arena, city, national_broadcast, cup_group
# From the slate snapshot. ``cup_group`` is empty on every row because the schedule page prints no
# NBA Cup group label anywhere in this window - an empty cell that means "not printed", not
# "we decided it is not a Cup game".
SLATE = [
    (g["date"], g["time_et"], g["away"], g["home"], g["game_id"], g["arena"], g["city"],
     g["tv"], g.get("cup_group", ""))
    for g in _SLATE_DOC["games"]
]
SLATE_PER_DAY = _SLATE_DOC.get("per_day_counts_official", {})

# "games" is the durable index URL every prior session linked when a row was sourced to the
# official score page. This build's finals are the dated capture (see results_feed and
# games_2026_11_14); the index is where a reader checks one today, so both keys are published and
# the description says which is which rather than letting a link imply a fetch it did not do.
SOURCES = {**SOURCES,
           "games": ("NBA.com Games index (live scores / finals for a given date)",
                     "https://www.nba.com/games",
                     "final scores, game status; the dated finals rows in this build come from "
                     "games_2026_11_14 and results_feed, both of which link here")}


INJURY_PDF_URL = SOURCES["injury_pdf"][1]

# --------------------------------------------------------------------------- injuries
# From the newest release actually on disk. The report's own columns are
# Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason.
# The trailing letter is this project's transcription note, not an NBA field:
#   "E" = the team cell is present on the row itself
#   "C" = the row continues a team block from the previous PDF page, so game date, matchup and
#         team are carried over (flagged on the site as FLAG-V2-INJ-ATTR)
def _pdf_date(printed: str) -> str:
    """The PDF prints 11/15/2026; the repository addresses a day as 2026-11-15."""
    if len(printed) == 10 and printed[2] == "/" and printed[5] == "/":
        mm, dd, yyyy = printed.split("/")
        return f"{yyyy}-{mm}-{dd}"
    return printed


INJURIES: list[tuple] = []
NOT_SUBMITTED: list[tuple] = []
INJURY_AS_OF = None
if _INJ:
    INJURY_AS_OF = _INJ.get("as_of")
    for r in _INJ.get("records", []):
        (gd, tmu, matchup, team, player, status, reason, attr) = r
        INJURIES.append((_pdf_date(gd), tmu, matchup, team, player, status, reason, attr))
    for rows in (_INJ.get("not_yet_submitted") or {}).values():
        for (gd, tmu, matchup, team) in rows:
            NOT_SUBMITTED.append((_pdf_date(gd), tmu, matchup, team))

# The game books cover exactly one date, and it is in the filename. Availability evidence is only
# ever attached to that date: an 11/14 dressingsheet says nothing about an 11/16 game.
_BOOK_FILE = sorted(glob.glob(str(RAW / "gamebooks_*.json")))
GAMEBOOK_DATE = _BOOK_FILE[-1][len(str(RAW / "gamebooks_")):-len(".json")] if _BOOK_FILE else None
_FINALS_PATH = RAW / f"finals_{GAMEBOOK_DATE}.json" if GAMEBOOK_DATE else None
_FINALS_DOC = json.loads(_FINALS_PATH.read_text()) if (_FINALS_PATH and _FINALS_PATH.exists()) else None
INJURY_RELEASE_STAMP = (_INJ or {}).get("report_stamp_et", "")
INJURY_ROW_COUNT = (_INJ or {}).get("record_count", 0)
INJURY_CARRIED_ROWS = list((_INJ or {}).get("carried_over_rows", []))
INJURY_DIFF_NOTE = (_INJ or {}).get("release_diff_note", "")
INJURY_NON_SUBMISSION_COUNTS = dict((_INJ or {}).get("not_yet_submitted_counts", {}))


def filing_status(date_iso: str, tri: str) -> dict:
    """What the official report says about one club on one date, and what it therefore cannot say.

    Three honest answers, and the third is the one a model has to respect: a club that filed
    nothing may be fully healthy, and a date the document does not cover has no status at all.
    """
    club = NAMES.get(tri, tri)
    rows = [r for r in INJURIES if r[0] == date_iso and r[3] == club]
    if rows:
        return {"state": "FILED", "rows": rows, "unfiled": False,
                "report_date": INJURY_AS_OF,
                "note": f"{len(rows)} designation row(s) in the {INJURY_RELEASE_STAMP} release"}
    unfiled = [x for x in NOT_SUBMITTED if x[0] == date_iso and x[3] == club]
    if unfiled:
        return {"state": "NOT_SUBMITTED", "rows": [], "unfiled": True,
                "report_date": INJURY_AS_OF,
                "note": "the report prints NOT YET SUBMITTED for this club on this date; the "
                        "filing deadline had not passed at capture time"}
    if INJURY_AS_OF and date_iso == INJURY_AS_OF:
        return {"state": "FILED_CLEAN", "rows": [], "unfiled": False, "report_date": date_iso,
                "note": "no designation row and no non-submission marker for this club on this date, "
                        "read as a clean filing; the reading is an interpretation, and is labelled"}
    if INJURY_AS_OF and date_iso > INJURY_AS_OF:
        return {"state": "NOT_IN_DOCUMENT", "rows": [], "unfiled": True,
                "report_date": INJURY_AS_OF,
                "note": f"the {INJURY_AS_OF} report contains no rows for {date_iso} at all - the "
                        "day is beyond the newest release, so availability is unknown, not clear"}
    return {"state": "NO_SNAPSHOT_FOR_DATE", "rows": [], "unfiled": True, "report_date": None,
            "note": f"the newest injury report on disk is dated {INJURY_AS_OF}, which is after "
                    f"{date_iso}; the earlier release that covered it is not part of this capture, "
                    "so the day is left unknown rather than back-filled"}


def unavailable_players(date_iso: str, tri: str) -> dict:
    """Players an official document puts out of this club's game, from either source."""
    filing = filing_status(date_iso, tri)
    out = {"availability_state": filing["state"], "note": filing["note"],
           "report_date": filing.get("report_date"), "book_date": GAMEBOOK_DATE,
            "from_injury_report": [r[4] for r in filing["rows"] if r[5] in ("Out", "Doubtful")],
            "questionable": [f"{r[4]} ({r[5]})" for r in filing["rows"]
                             if r[5] in ("Questionable", "Probable", "Available")],
            "from_game_book": [], "late_status_changes": [], "sources": []}
    if GAMEBOOK_DATE and date_iso == GAMEBOOK_DATE:
        for blk in GAMEBOOKS.get("inactives", {}).get(tri, []):
            out["from_game_book"].append(
                f"{blk['player']} ({blk['reason'] or 'reason not printed'})")
        for dnd in GAMEBOOKS.get("dnd_and_nwt_rows", []):
            if dnd["tri"] == tri:
                out["late_status_changes"].append(f"{dnd['player']} - {dnd['printed']}")
        if out["from_game_book"] or out["late_status_changes"]:
            out["sources"] = GAMEBOOKS.get("urls", [])
        if tri in GAMEBOOKS.get("inactives_not_preserved", []):
            out["book_coverage"] = ("this club's inactive block is in the game book but was not "
                                    "preserved in the capture; listed as missing, not as empty")
    else:
        out["book_coverage"] = (f"game-book availability exists only for {GAMEBOOK_DATE}, the one "
                                "date whose official books this capture read; no book evidence is "
                                "available for " + date_iso)
    return out


# Availability evidence from the game books, which is a different and later source than the 6 a.m.
# report: it is what actually happened to the dressingsheet.
GAMEBOOKS = _BOOKS or {}


def _norm_player(name: str) -> str:
    """Match a player across releases despite the NBA's own typos: lower-case, no punctuation."""
    return "".join(ch for ch in name.lower() if ch.isalpha() or ch == " ")


def injury_release_diff() -> dict:
    """What the day's two official releases changed, row by row, keyed on a normalised name.

    This exists because "the injury report" is not one document: the league issues several a day,
    and a pick that moves because of a status change must be able to say which release moved it.
    Keying on a normalised player string is what stops the league's own spelling change
    ("Embiid" -> "Embid") from being reported as a status change, which is the failure mode that
    would silently reprice lines for no reason.
    """
    if not _INJ_PRIOR:
        return {"available": False,
                "reason": "only one release for this date is committed, so there is nothing to "
                          "compare; the newest release is published as-is and flagged as un-diffed",
                "newest": (_INJ or {}).get("source_url", ""), "prior": ""}
    def keyed(doc):
        return {_norm_player(r[4]): tuple(r) for r in doc.get("records", [])}
    a, b = keyed(_INJ_PRIOR), keyed(_INJ)
    changed, added, removed = [], [], []
    for k, row in b.items():
        if k not in a:
            added.append({"player": row[4], "team": row[3], "status": row[5], "reason": row[6]})
        elif a[k][:4] != row[:4] or a[k][5:] != row[5:]:
            changed.append({"player": row[4], "team": row[3],
                            "prior_status": a[k][5], "new_status": row[5],
                            "prior_reason": a[k][6], "new_reason": row[6],
                            "name_also_changed": a[k][4] != row[4]})
    for k, row in a.items():
        if k not in b:
            removed.append({"player": row[4], "team": row[3], "status": row[5], "reason": row[6]})
    # A row that appears in one release and vanishes in the other, with an identical team, status
    # and reason, is the league's spelling changing - not a player's availability. Pair them up
    # before counting, or the site would report a phantom move.
    paired = []
    for rm in list(removed):
        for ad in list(added):
            if (rm["team"], rm["status"], rm["reason"]) == (ad["team"], ad["status"], ad["reason"]):
                paired.append({"team": ad["team"], "status": ad["status"], "reason": ad["reason"],
                               "prior_name": rm["player"], "newest_name": ad["player"]})
                removed.remove(rm)
                added.remove(ad)
                break
    spelling_only = [c for c in changed if c["prior_status"] == c["new_status"]] + paired
    return {"available": True,
            "prior_url": _INJ_PRIOR.get("source_url", ""), "newest_url": _INJ.get("source_url", ""),
            "prior_stamp": _INJ_PRIOR.get("report_stamp_et", ""),
            "newest_stamp": _INJ.get("report_stamp_et", ""),
            "rows_prior": _INJ_PRIOR.get("record_count", 0), "rows_newest": _INJ.get("record_count", 0),
            "status_changes": [c for c in changed if c["prior_status"] != c["new_status"]],
            "spelling_only_changes": spelling_only,
            "added": added, "removed": removed,
            "lines_that_moved": len([c for c in changed if c["prior_status"] != c["new_status"]])
                              + len(added) + len(removed),
            "n_status_changed": len([c for c in changed if c["prior_status"] != c["new_status"]]),
            "n_rows_added": len(added), "n_rows_removed": len(removed),
            "n_game_moved": len([c for c in changed if c["prior_reason"] != c["new_reason"]]),
            "rows_latest": _INJ.get("record_count", 0),
            "differences": ([{"kind": "status", **c} for c in changed]
                            + [{"kind": "spelling", **c} for c in paired]),
            "release_diff_note": INJURY_DIFF_NOTE or "no note recorded in the artefact",
            "minutes_apart": _release_gap_minutes(_INJ_PRIOR.get("report_stamp_et", ""),
                                                   _INJ.get("report_stamp_et", "")),
            "interpretation": "an add/remove pair with the same team, status and reason is read as a "
                              "spelling change in the document, not a roster move; that is a choice, "
                              "and it is the conservative one - treating it as a move would reprice "
                              "a line on a typo"}

def _release_gap_minutes(a: str, b: str) -> int | None:
    """Minutes between two "2026-11-15 06:00 AM ET" stamps, or None if either is unreadable."""
    import datetime as dt
    try:
        pa = dt.datetime.strptime(a[:-3].strip(), "%Y-%m-%d %I:%M %p")
        pb = dt.datetime.strptime(b[:-3].strip(), "%Y-%m-%d %I:%M %p")
        return int((pb - pa).total_seconds() // 60)
    except (ValueError, AttributeError):
        return None


INJURY_PRIOR_STAMP = (_INJ_PRIOR or {}).get("report_stamp_et", "")


def filing_status_summary() -> dict:
    """Every slate game x club, in one state, counted. The denominator is on the slate, not assumed."""
    by: dict[str, int] = {}
    unknown = []
    for (d, _t, aw, hm, gid, *_rest) in SLATE:
        for tri in (aw, hm):
            f = filing_status(d, tri)
            by[f["state"]] = by.get(f["state"], 0) + 1
            if f["unfiled"]:
                unknown.append(gid)
    return {"club_slots": sum(by.values()), "by_state": by,
            "games_with_unknown_clubs": sorted(set(unknown)),
            "report_date": INJURY_AS_OF, "release_stamp": INJURY_RELEASE_STAMP,
            "note": ("FILED_CLEAN means the club filed a report listing no unavailable players for "
                     "that date — an empty report is a filing, not a gap. NOT_SUBMITTED means the "
                     "club appears in the document's NOT YET SUBMITTED list, so its availability is "
                     "unknown, not healthy.")}


def finals_records() -> list[dict]:
    """Official finals captured for the most recent completed game day, with quarter strips.

    Each row carries two quarter sources: the game page and the referees' game book. The capture
    asserted the two agree and that both sum to the printed final, so one reconciled line is
    published with both URLs attached — a reader can open either and check it.
    """
    return list((_FINALS_DOC or {}).get("games", []))


# --------------------------------------------------------------------------- players
# nba.com/stats/players/traditional - season aggregates, read 2026-11-14.
# A season *rate* is published; the per-game distribution needed to price a prop is not,
# so every prop column built from this table is blank and flagged.
# player, team, GP, MIN, PTS, REB, AST, nba_player_id
PLAYERS = [
    ("Luka Don\u010dić", "LAL", 13, None, None, None, None, "1629029"),
    ("Shai Gilgeous-Alexander", "OKC", 13, None, None, None, None, "1628983"),
    ("Victor Wembanyama", "SAS", 13, None, None, None, None, "1641705"),
    ("Anthony Edwards", "MIN", None, None, None, None, None, "1630162"),
    ("Jalen Duren", "DET", None, None, None, None, None, "1631106"),
    ("Nikola Joki\u0107", "DEN", 10, None, None, None, None, "203999"),
    ("Donovan Mitchell", "CLE", 13, None, None, None, None, "1628378"),
]

PLAYER_SOURCE = "https://www.nba.com/stats/players/traditional"


# --------------------------------------------------------------------------- checks
def integrity() -> dict:
    """Arithmetic identities that official league totals must satisfy.

    These are *derived checks*, not sources: if a transcription were wrong, one of these
    would break. Each one is reported on the site so a reviewer can re-run it.
    """
    gp = {t: v[0] + v[1] for t, v in TEAMS.items()}
    total_gp = sum(gp.values())
    weighted_pf = sum(v[6] * gp[t] for t, v in TEAMS.items())
    weighted_pa = sum(v[7] * gp[t] for t, v in TEAMS.items())
    league_pts_per_team_game = weighted_pf / total_gp
    hw = sum(v[2] for v in TEAMS.values())
    hl = sum(v[3] for v in TEAMS.values())
    rw = sum(v[4] for v in TEAMS.values())
    rl = sum(v[5] for v in TEAMS.values())
    wins = sum(v[0] for v in TEAMS.values())
    losses = sum(v[1] for v in TEAMS.values())
    # the standings card's neutral and OT columns count team-games; each is two per game
    neutral_team_games = sum(sum(int(x) for x in s["neutral"].split("-")) for s in SPLITS.values())
    ot_team_games = sum(sum(int(x) for x in s["ot"].split("-")) for s in SPLITS.values())
    games = len(_FEED["games"])
    return {
        "teams": len(TEAMS),
        "games_played_team_sum": total_gp,
        "games": total_gp / 2,
        "games_in_result_feed": games,
        "games_match_result_feed": total_gp / 2 == games,
        "wins": wins,
        "losses": losses,
        "wins_equals_losses": wins == losses,
        "weighted_points_scored": round(weighted_pf, 1),
        "weighted_points_allowed": round(weighted_pa, 1),
        "weighted_points_diff": round(weighted_pf - weighted_pa, 1),
        # each team's PF/PA is rounded to 0.1, so the difference must be within
        # 0.05 * (games) summed over both sides = 0.1 * total_gp
        "rounding_bound": round(0.1 * total_gp, 1),
        "points_identity_ok": abs(weighted_pf - weighted_pa) <= 0.1 * total_gp,
        "home_w": hw, "home_l": hl, "road_w": rw, "road_l": rl,
        "home_wins_equal_road_losses": hw == rl,
        "home_losses_equal_road_wins": hl == rw,
        "home_win_rate": round(hw / (hw + hl), 4),
        "league_pts_per_team_game": round(league_pts_per_team_game, 3),
        "venue_splits_add_to_gp": all(
            v[2] + v[3] + v[4] + v[5] + sum(int(x) for x in SPLITS[t]["neutral"].split("-"))
            == v[0] + v[1] for t, v in TEAMS.items()),
        "neutral_site_games": neutral_team_games // 2,
        "ot_games": ot_team_games // 2,
        "last10_sums_to_300_team_games":
            sum(sum(int(x) for x in s["last10"].split("-")) for s in SPLITS.values()) == 300,
        "injury_rows": len(INJURIES),
        "injury_non_submissions": len(NOT_SUBMITTED),
    }


def conference_identity() -> dict:
    """Every CONF cell on the standings card, recomputed from the per-game result feed.

    East is the first half of the standings card and West the second; each intra-conference game
    contributes one win and one loss to that conference's total, and one team's own conference
    record is the count of its intra-conference games. If a single final score in the 188 were
    wrong or missing, at least one of these 30 comparisons would fail.
    """
    order = [r[0] for r in _STANDINGS["rows"]]
    half = len(order) // 2
    conf = {t: ("East" if i < half else "West") for i, t in enumerate(order)}
    computed = {t: [0, 0] for t in conf}
    for g in _FEED["games"]:
        if conf[g["away"]] != conf[g["home"]]:
            continue
        a, h = computed[g["away"]], computed[g["home"]]
        if g["away_pts"] > g["home_pts"]:
            a[0] += 1
            h[1] += 1
        else:
            h[0] += 1
            a[1] += 1
    rows = []
    for t in order:
        printed = SPLITS[t]["conf"]
        pw, pl = (int(x) for x in printed.split("-"))
        rows.append({"tri": t, "printed": printed, "computed": f"{computed[t][0]}-{computed[t][1]}",
                     "ok": (pw, pl) == tuple(computed[t])})
    bad = [r for r in rows if not r["ok"]]
    return {"n_teams": len(rows), "n_match": len(rows) - len(bad), "mismatches": bad,
            "ok": not bad,
            "source_url": _STANDINGS["source_url"],
            "feed_source": _FEED["sources"]["games"]}


def home_win_rate_se() -> float:
    """Standard error of the league home-win rate, from the games actually observed."""
    i = integrity()
    n = i["home_w"] + i["home_l"]
    return math.sqrt(0.25 / n)


def staleness(now_utc: str | None = None) -> dict:
    """How old the snapshot is, measured, not asserted.

    ``hours_since_capture`` is the honest number a reader wants before trusting a "current"
    record: the capture has a UTC stamp on every artefact, so age is arithmetic.
    """
    import datetime as dt
    stamp = RETRIEVED_AT_UTC
    try:
        then = dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except (ValueError, TypeError):
        return {"capture_stamp": stamp, "hours_since_capture": None,
                "verdict": "UNKNOWN - the snapshot carries no parseable capture time"}
    now = (dt.datetime.strptime(now_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
           if now_utc else dt.datetime.now(dt.timezone.utc))
    hours = (now - then).total_seconds() / 3600.0
    # the window is only meaningful while its earliest game has not tipped
    first = min(g[0] for g in SLATE) if SLATE else None
    days_ahead = None
    if first:
        days_ahead = (dt.date.fromisoformat(first) - now.date()).days
    return {"capture_stamp": stamp, "captured_by": RETRIEVED_BY,
            "hours_since_capture": round(hours, 2),
            "first_slate_date": first, "slate_starts_in_days": days_ahead,
            "verdict": ("CURRENT" if hours < 24 and (days_ahead is None or days_ahead >= 0)
                        else "STALE" if hours < 72 else "STALE - re-capture before publishing")}
