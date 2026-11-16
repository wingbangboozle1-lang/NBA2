"""Build the 2026-11-14 05:15 AM ET ingestion captures from the verbatim fetch captures.

Run:  python3 audit/3fbd894a/build_captures.py

Writes:
  data/raw/injury_report_2026-11-14_0515AMET.json
  data/raw/official_game_times_2026-11-14_0515AMET.json

Inputs (verbatim platform-fetch captures, committed next to this script):
  raw_injury_2026-11-14_0515AM_chunk0.md   official injury PDF text, fetched 2026-11-14
  games_pages_2026-11-14_to_11-17.md       official nba.com/games?date= pages, fetched 2026-11-14

Every value written is parsed from those two files or, where a cell was lost to the PDF's
page breaks, left blank and flagged. Nothing is inferred. The placeholder reason string
'Team submission outstanding at report time' is the repo's established display convention
for rows the PDF prints as 'NOT YET SUBMITTED' (see data/raw/injury_report_2026-11-14_
daybefore.json); it is labelled as a convention in the output flags, not as PDF text.

Irregularities this ingests (from session arena/e77ce5ad-nba2's handoff):
  I-01  the 05:15 AM ET release was published but not ingested      -> ingested here
  I-02  DET@MIA tip provenance pointed at a PDF whose cell was lost -> game-page source here
  I-03  no explicit AM/PM rule for printed tip cells                -> explicit rule below
  I-05  citations to the JS-only schedule page                      -> games?date= cites here
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"

RETRIEVED = "2026-11-14T10:45:00Z"
PDF_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_15AM.pdf"

TEAM_NAMES = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR", "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}
STATUSES = {"Out", "Doubtful", "Questionable", "Probable", "Available"}
PLACEHOLDER_REASON = "Team submission outstanding at report time"

RE_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
RE_TIME = re.compile(r"^(\d{2}):(\d{2})(?: \(ET\))?$")
RE_MATCHUP = re.compile(r"^[A-Z]{3}@[A-Z]{3}$")
RE_SEP = re.compile(r"^\|[\s\-|]+\|$")


def printed_date_to_iso(cell: str) -> str:
    m = RE_DATE.match(cell)
    if not m:
        raise ValueError(f"not a printed date cell: {cell!r}")
    mm, dd, yyyy = m.groups()
    return f"{yyyy}-{mm}-{dd}"


def printed_time_cell(cell: str) -> str:
    """Store the bare printed 12-hour cell ('07:00'), matching prior captures' schema."""
    m = RE_TIME.match(cell)
    if not m:
        raise ValueError(f"not a printed tip cell: {cell!r}")
    return f"{m.group(1)}:{m.group(2)}"


def printed_game_time_to_24h(cell: str) -> str:
    """The project's explicit printed-tip -> 24h ET rule (irregularity I-03).

    The official referee-ops PDFs print game times on a 12-hour clock with an '(ET)'
    suffix and NO meridiem. NBA tips are afternoon/evening, so a printed hour 1-11 is
    PM (add 12) and printed 12:xx is noon (unchanged). Verified this session against
    nba.com/games?date= pages for every row of 11/15 (1:00 PM ET = 01:00 -> 13:00,
    4:00 PM ET = 04:00 -> 16:00, ... 9:00 PM ET = 09:00 -> 21:00) and 11/14-11/17.
    """
    m = RE_TIME.match(cell)
    if not m:
        raise ValueError(f"not a printed tip cell: {cell!r}")
    h, mm = int(m.group(1)), m.group(2)
    if not (1 <= h <= 12):
        raise ValueError(f"printed hour out of 1..12: {cell!r}")
    return f"{h + 12 if h <= 11 else h:02d}:{mm}"


def classify(cell: str) -> str:
    c = cell.strip()
    if not c:
        return "empty"
    if c == "NOT YET SUBMITTED":
        return "placeholder"
    if RE_DATE.match(c):
        return "date"
    if RE_TIME.match(c):
        return "time"
    if RE_MATCHUP.match(c):
        return "matchup"
    if c in TEAM_NAMES:
        return "team"
    if c in STATUSES:
        return "status"
    if c.startswith("Injury/Illness") or c.startswith("G League") or c.startswith("League"):
        return "reason"
    if "," in c:
        return "player"
    return "unknown"


def parse_injury_md() -> list[list]:
    text = (AUDIT / "raw_injury_2026-11-14_0515AM_chunk0.md").read_text()
    rows: list[list] = []
    last_date = ""          # last date cell printed anywhere (page continuations carry it)
    block = {"matchup": "", "time": "", "team": ""}  # per-game-block context
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or RE_SEP.match(line):
            continue
        if "Game Date" in line and "Game Time" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        kinds = [classify(c) for c in cells]
        vals = dict(zip(kinds, cells))  # first occurrence per kind
        if "date" in kinds:
            last_date = printed_date_to_iso(vals["date"])
        date = last_date
        if "matchup" in kinds:
            if vals["matchup"] != block["matchup"]:
                block = {"matchup": vals["matchup"],
                         "time": printed_time_cell(vals["time"]) if "time" in kinds else "",
                         "team": ""}
        matchup = block["matchup"]
        # time carries WITHIN a game block only if some row of the block printed it;
        # a block whose cells were all lost to page breaks keeps blank (never inferred).
        time = printed_time_cell(vals["time"]) if "time" in kinds else block["time"]
        if "time" in kinds and not block["time"]:
            block["time"] = time
        if "team" in kinds:
            team = vals["team"]
            attr = "E"
        else:
            team = block["team"]
            attr = "C"  # team cell lost to a page break; carried per attribution_key
        player = vals.get("player", "")
        if "placeholder" in kinds:
            status, reason = "NOT YET SUBMITTED", PLACEHOLDER_REASON
            if "player" not in kinds:
                player = ""
        else:
            status = vals.get("status", "")
            reason = vals.get("reason", "")
            if status not in STATUSES or not reason:
                raise SystemExit(f"unclassifiable player row: {cells!r} -> {kinds!r}")
        if not (date and matchup and team):
            raise SystemExit(f"row missing block context: {cells!r}")
        rows.append([date, time, matchup, team, player, status, reason, attr])
        if attr == "E":
            block["team"] = team
    return rows


def parse_games_md() -> list[dict]:
    """The 27-row recheck table from games_pages_2026-11-14_to_11-17.md."""
    text = (AUDIT / "games_pages_2026-11-14_to_11-17.md").read_text()
    out = []
    date = None
    for line in text.splitlines():
        m = re.match(r"^## (20\d{2}-\d{2}-\d{2}) ", line)
        if m:
            date = m.group(1)
            continue
        line = line.strip()
        if not line.startswith("|") or RE_SEP.match(line) or "game_id" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if date == "2026-11-14":
            if len(cells) != 5:
                continue
            gid, matchup, printed, h24, page = cells
        else:
            if len(cells) != 6:
                continue
            gid, matchup, printed, h24, _records, page = cells
        a, h = matchup.split(" @ ")
        # apply the printed-tip rule independently to the printed string
        m2 = re.match(r"^(\d{1,2}):(\d{2})\s*(AM|PM) ET$", printed.replace("pm", "PM").replace("am", "AM"))
        if not m2:
            raise SystemExit(f"bad printed tip {printed!r}")
        hh, mm, ap = int(m2.group(1)), m2.group(2), m2.group(3)
        hh24 = hh % 12 + (12 if ap == "PM" else 0)
        rule_val = f"{hh24:02d}:{mm}"
        if rule_val != h24:
            raise SystemExit(f"rule mismatch for {matchup}: {printed} -> {rule_val} != {h24}")
        out.append({
            "date": date, "matchup": f"{a}@{h}", "game_id": gid.strip(),
            "printed_tip": printed, "time_et": h24,
            "source_url": page.strip(),
        })
    return out


def build_injury_capture(rows: list[list]) -> dict:
    n_1114 = sum(1 for r in rows if r[0] == "2026-11-14")
    n_1115 = sum(1 for r in rows if r[0] == "2026-11-15")
    placeholders = sum(1 for r in rows if r[5] == "NOT YET SUBMITTED")
    c_rows = sum(1 for r in rows if r[7] == "C")

    # revision comparison vs the 19:30 ET release and the window snapshot
    def index(doc):
        out = {}
        for rec in doc["records"]:
            out[(rec[0], rec[2], rec[3], rec[4])] = (rec[5], rec[6])
        return out

    prior = json.loads((RAW / "injury_report_2026-11-13_1930ET.json").read_text())
    win = json.loads((RAW / "injury_report_2026-11-14_daybefore.json").read_text())
    p_idx, w_idx = index(prior), index(win)
    shared = changes = 0
    for r in rows:
        key = (r[0], r[2], r[3], r[4])
        for idx, name in ((p_idx, "19:30 ET release"), (w_idx, "window snapshot")):
            if key in idx:
                shared += 1
                if idx[key] != (r[5], r[6]):
                    changes += 1
                    raise SystemExit(f"status change vs {name} on {key}: {idx[key]} -> {(r[5], r[6])}")
    if shared < 31:
        raise SystemExit(f"only {shared} shared rows vs prior captures — parser regression")

    return {
        "dataset": "official_injury_report",
        "report_stamp_et": "2026-11-14 05:15",
        "retrieved_at_utc": RETRIEVED,
        "provenance": {
            "publisher": "NBA Referee Operations (official NBA injury report, published on the NBA's own CDN)",
            "official_nba_source": True,
            "url": PDF_URL,
            "document_title": "Injury Report: 11/14/26 05:15 AM (multi-page; full text captured verbatim)",
            "index_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
            "cadence_note": (
                "Per the official index (fetched this session): teams file by 5 p.m. local the day "
                "before a game (1 p.m. local game-day for the second night of a back-to-back); a "
                "game-day report is filed between 11 a.m. and 1 p.m. local (8-10 a.m. for early "
                "tips); 'Reports are updated on a continual basis throughout the day' - hence the "
                "15-minute PDF cadence. A probe of the 05:30 AM release at retrieval time returned "
                "S3 AccessDenied (unpublished), so this 05:15 AM release was the freshest published."
            ),
            "supersedes": "data/raw/injury_report_2026-11-13_1930ET.json (19:30 ET 11/13 release) and data/raw/injury_report_2026-11-14_daybefore.json (its 11/14 window subset)",
            "capture_files": ["audit/3fbd894a/raw_injury_2026-11-14_0515AM_chunk0.md"],
            "retrieval_method": "platform page-fetch tool (direct curl to ak-static.cms.nba.com is blocked from the build sandbox)",
        },
        "revision_note": {
            "basis": "Row-level comparison (game_date, matchup, team, player -> status, reason) against the two committed prior captures.",
            "shared_rows_compared": shared,
            "status_changes": changes,
            "result": (
                "No status changed on any row shared with the 19:30 ET release or the window "
                "snapshot. This release adds the 2026-11-15 game blocks (18 placeholder rows for "
                "9 games - day-before designations for 11/15 are not due until 5 p.m. local today)."
            ),
        },
        "attribution_key": {
            "E": "Team cell printed explicitly on the same row as the player (or the placeholder row).",
            "C": "Team cell lost to a page break in the text extraction; team carried from the last team label printed in that game block before the row (established convention). No row in this release needed a cross-release override.",
        },
        "time_convention": {
            "stored_as": "the printed 12-hour cell, verbatim (e.g. '07:00', '01:00'), matching the prior injury captures' column semantics",
            "rule": "printed hour 1-11 -> PM (add 12); printed 12:xx -> noon",
            "examples_verified_this_session": "11/15 '01:00 (ET)' = 1:00 PM ET = 13:00; '04:00 (ET)' = 4:00 PM ET = 16:00 (nba.com/games?date=2026-11-15)",
            "note": "Irregularity I-03 of session arena/e77ce5ad-nba2: prior captures documented only '07:00 (ET) -> 19:00'. The rule above is now explicit and is enforced by nba2.pipeline.refresh.printed_game_time_to_24h (unit-tested).",
        },
        "flags": [
            {
                "id": "FLAG-INJ-10",
                "severity": "low",
                "field": "reason column of placeholder rows",
                "issue": (
                    "'Team submission outstanding at report time' is the repo's established display "
                    "convention for rows the PDF prints as 'NOT YET SUBMITTED' (the PDF prints no "
                    "reason cell for them). It is a labelled convention, not PDF text."
                ),
                "action_required": "None - disclosure only.",
            },
            {
                "id": "FLAG-INJ-11",
                "severity": "medium",
                "field": "time_et of the CHI@MIN and DET@MIA blocks",
                "issue": (
                    "This extraction lost the tip-time cell for both blocks (page breaks), so "
                    "time_et is blank on those 12 rows - blanks stay blank. The tip times "
                    "(both 8:00 PM ET) are verified at the official games page and recorded in "
                    "official_game_times_2026-11-14_0515AMET.json with time_captured=false."
                ),
                "action_required": "None - values live in the times capture with honest provenance.",
            },
            {
                "id": "FLAG-INJ-12",
                "severity": "low",
                "field": "Traore, Nolan (BKN@MEM)",
                "issue": (
                    "Team cell lost to a page break; attributed to Brooklyn Nets (C) per the block "
                    "convention - the row prints inside the BKN@MEM block after the five explicit "
                    "Brooklyn rows and before the Memphis placeholder row."
                ),
                "action_required": "Spot-check the PDF rendering at the source URL if the attribution matters.",
            },
            {
                "id": "FLAG-INJ-13",
                "severity": "info",
                "field": "2026-11-16 and 2026-11-17 games",
                "issue": (
                    "No official release yet lists 11/16-11/17 designations (they appear in the "
                    "releases for their own game days). Those 13 window games have no injury rows "
                    "to show - absence is coverage state, not missing transcription."
                ),
                "action_required": "Re-run the ingest when the game-day releases publish (nightly workflow, .github/workflows/refresh.yml).",
            },
        ],
        "columns": ["game_date", "time_et", "matchup", "team", "player", "status", "reason", "attribution"],
        "records": rows,
        "record_counts": {
            "total_rows": len(rows),
            "rows_2026_11_14": n_1114,
            "rows_2026_11_15": n_1115,
            "rows_with_status": len(rows) - placeholders,
            "not_yet_submitted_placeholders": placeholders,
            "attribution_explicit": len(rows) - c_rows,
            "attribution_continuation": c_rows,
            "note": "counts computed from the records array at write time",
        },
    }


def build_times_capture(rows: list[list], recheck: list[dict]) -> dict:
    # one row per game: the printed time cell if any row of the block carries it
    games: dict[tuple[str, str], tuple[str, bool]] = {}
    for r in rows:
        key = (r[0], r[2])
        if key not in games or (r[1] and not games[key][1]):
            has_cell = bool(r[1])
            games[key] = (printed_game_time_to_24h(r[1]) if has_cell else "", has_cell)

    recs = []
    for (date, matchup), (t24, has_cell) in sorted(games.items()):
        recs.append([date, matchup, t24 if has_cell else "", has_cell])

    # fill lost cells from the game-page recheck (documented, not inferred)
    by_key = {(r["date"], r["matchup"]): r for r in recheck}
    corrections = []
    for rec in recs:
        if not rec[3]:
            src = by_key[(rec[0], rec[1])]
            rec[2] = src["time_et"]
            corrections.append({
                "date": rec[0], "matchup": rec[1], "field": "time_et",
                "resolution": "value taken from the official games page recheck (time_captured stays false)",
                "evidence": src["source_url"],
            })
    # adjudication (irregularity I-02): the 11/13 19:30 ET times capture records DET@MIA as
    # time_captured=true, but its own sibling transcription documents that extraction losing
    # the cell (injury_report_2026-11-14_daybefore.json, record_counts.note + FLAG-INJ-06).
    # No extraction carries a readable DET@MIA time cell, so no earlier capture may claim one.
    corrections.append({
        "date": "2026-11-14", "matchup": "DET@MIA", "field": "older_captured", "to": False,
        "resolution": ("overrules official_game_times_2026-11-14.json's time_captured=true for this game: "
                       "that cell was lost in that extraction too, per its own sibling transcription; "
                       "the tip (8:00 PM ET) stands on the official games-page recheck"),
        "evidence": "data/raw/injury_report_2026-11-14_daybefore.json (record_counts.games_covered_note + FLAG-INJ-06)",
    })

    return {
        "dataset": "official_game_times_and_matchups_from_injury_report",
        "purpose": (
            "Second-official-document corroboration of the slate: the referee-operations injury "
            "report prints Game Date / Game Time / Matchup on every row, independently confirming "
            "which games exist and their ET tip times. The game-page recheck block corroborates "
            "every pick-window row directly against nba.com/games?date= pages."
        ),
        "source": PDF_URL,
        "retrieved_at_utc": RETRIEVED,
        "why_this_matters": (
            "FLAG-SLATE-04 exists because www.nba.com/schedule prints tip times as a loose list "
            "and is a JavaScript shell (I-05). This document attaches the time to the matchup in "
            "the same table row, and the games?date= pages print the tip on the game card - "
            "agreement among them upgrades each tip time beyond a single-source claim."
        ),
        "reading_rules": [
            "A time is recorded as captured only when a printed row of the PDF carries the time cell.",
            "Where the extraction lost the cell (CHI@MIN, DET@MIA blocks of this release), time_captured is false and the value is filled from the official games-page recheck below - never inferred.",
            "Supersedes data/raw/official_game_times_2026-11-14.json for the 2026-11-14 keys: that file recorded DET@MIA as time_captured=true although its own sibling capture (injury_report_2026-11-14_daybefore.json, record_counts.note + FLAG-INJ-06) documents the cell as lost - irregularity I-02. This file corrects the record; the old file stays committed as history.",
        ],
        "time_convention": {
            "stored_as": "24h ET",
            "rule": "printed cells are a 12-hour clock with '(ET)' and no meridiem: hour 1-11 -> add 12 (PM); 12:xx -> noon",
            "worked_examples": "07:00 (ET) -> 19:00; 01:00 (ET) -> 13:00; 04:30 (ET) -> 16:30; 09:00 (ET) -> 21:00; 12:00 (ET) -> 12:00",
            "verified_this_session": "every 11/15 printed cell re-read against https://www.nba.com/games?date=2026-11-15 (1:00 PM ET, 4:00 PM ET, 4:30 PM ET, 5:00 PM ET, 6:00 PM ET x2, 7:00 PM ET, 8:00 PM ET, 9:00 PM ET)",
        },
        "coverage": {
            "games_confirmed_in_document": len(recs),
            "times_confirmed_with_printed_cell": sum(1 for r in recs if r[3]),
            "times_confirmed_via_games_page_only": sum(1 for r in recs if not r[3]),
            "matchups_confirmed_time_lost_to_page_break": sum(1 for r in recs if not r[3]),
            "dates_covered": sorted({r[0] for r in recs}),
            "not_covered": (
                "2026-11-16..17 games are absent from every release published so far; their tips "
                "are re-verified row-by-row in game_page_recheck below and remain FLAG-SLATE-04 "
                "until an injury-report release lists them."
            ),
        },
        "columns": ["date", "matchup", "time_et", "time_captured"],
        "records": recs,
        "corrections": corrections,
        "game_page_recheck": {
            "source_note": (
                "Every pick-window row (2026-11-14..2026-11-17) re-read from the official "
                "nba.com/games?date= pages on 2026-11-14 (~10:35-10:55 UTC) via the platform "
                "page-fetch tool; full transcript in audit/3fbd894a/games_pages_2026-11-14_to_11-17.md. "
                "The bare www.nba.com/schedule URL is a JavaScript shell and is never used alone "
                "as a source (I-05)."
            ),
            "rows": [
                {
                    "date": r["date"], "matchup": r["matchup"], "game_id": r["game_id"],
                    "printed_tip": r["printed_tip"], "time_et": r["time_et"],
                    "source_url": r["source_url"],
                    "verdict": "MATCH — tip time agrees with data/raw/slate_2026-11-14_to_11-17.json",
                }
                for r in recheck
            ],
            "result": "27/27 pick-window rows match the committed slate on matchup, game ID and tip time; 0 mismatches.",
        },
    }


def main() -> None:
    rows = parse_injury_md()
    if len(rows) != 49:
        raise SystemExit(f"expected 49 rows, parsed {len(rows)}")
    recheck = parse_games_md()
    if len(recheck) != 27:
        raise SystemExit(f"expected 27 game-page rows, parsed {len(recheck)}")
    # cross-check the recheck block against the committed slate
    slate = json.loads((RAW / "slate_2026-11-14_to_11-17.json").read_text())
    scols = slate["columns"]
    sidx = {r[4]: dict(zip(scols, r)) for r in slate["records"]}
    for r in recheck:
        g = sidx.get(r["game_id"])
        if g is None:
            raise SystemExit(f"game {r['game_id']} not in slate")
        if (g["date"], f"{g['away']}@{g['home']}", g["time_et"]) != (r["date"], r["matchup"], r["time_et"]):
            raise SystemExit(f"slate mismatch {r}: {g}")
    inj = build_injury_capture(rows)
    times = build_times_capture(rows, recheck)
    (RAW / "injury_report_2026-11-14_0515AMET.json").write_text(json.dumps(inj, indent=1, ensure_ascii=False) + "\n")
    (RAW / "official_game_times_2026-11-14_0515AMET.json").write_text(json.dumps(times, indent=1, ensure_ascii=False) + "\n")
    print("injury rows:", len(rows), "| record_counts:", inj["record_counts"])
    print("times records:", len(times["records"]), "| recheck:", len(recheck), "rows")
    print("OK")


if __name__ == "__main__":
    main()
