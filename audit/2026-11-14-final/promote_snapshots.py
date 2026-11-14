"""Promote this session's official capture into the repository's raw snapshots.

    python3 audit/2026-11-14-final/promote_snapshots.py

Three new files are written, each carrying its own provenance block:

  data/raw/official_standings_2026-11-14.json  — the official 2026-27 standings table
      (W, L, HOME, ROAD, CONF, DIV for all 30 clubs) read from nba.com/standings.
  data/raw/injury_report_2026-11-14_0500ET.json — the newest official injury release
      (11/14 05:00 a.m ET), which is the first release to carry the 11/15 designations
      (all still NOT YET SUBMITTED) and the first to label every row's team explicitly.
  data/raw/finals_2026-11-13.json — the nine official final scores of the 11/13 games,
      in the shape nba2.pipeline.settle expects.

Nothing is deleted and no existing snapshot is edited: the 11/13 19:30 ET release stays
committed as the historical capture of the 11/13 games.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAP = json.loads((Path(__file__).resolve().parent /
                  "official_capture_2026-11-14.json").read_text())
RAW = ROOT / "data" / "raw"
RETRIEVED = CAP["captured_at_utc"]


def write_standings() -> Path:
    doc = {
        "dataset": "official_standings",
        "season": "2026-27",
        "as_of": "2026-11-14",
        "retrieved_at_utc": RETRIEVED,
        "method": CAP["method"],
        "provenance": {
            "primary_source": {
                "publisher": "NBA.com — Official standings (official)",
                "source_class": "official",
                "official_nba_source": True,
                "url": CAP["sources"]["standings"],
                "fields": ["tricode", "name", "w", "l", "home", "road", "conf", "div"],
                "note": ("Rendered table of the NBA 2026-27 Regular Season standings. The "
                         "'Margins & Stats' section of the same page did NOT render "
                         "PS/G, PA/G or SRS for this client, so those fields remain "
                         "third-party (FLAG-RAT-01). Every club's win-loss record on this "
                         "page is printed next to the club's own team page link."),
            },
            "comparison_note": (
                "12 of 30 clubs are identical to the 2026-11-13 ratings snapshot; the other 18 "
                "changed because the nine 2026-11-13 games were played. That is an aged snapshot, "
                "not a transcription error — the exact per-club deltas are listed in "
                "audit/2026-11-14-final/verification_report.md."),
        },
        "columns": ["tricode", "name", "w", "l", "home", "road", "conf", "div"],
        "records": [[s["tricode"], s["name"], s["w"], s["l"], s["home"], s["road"], s["conf"],
                     s["div"]] for s in CAP["standings_2026_11_14"]],
    }
    path = RAW / "official_standings_2026-11-14.json"
    path.write_text(json.dumps(doc, indent=2) + "\n")
    return path


def write_injury() -> Path:
    rows = CAP["injury_report_2026_11_14_0500ET"]
    recs = []
    for r in rows:
        # The PDF prints "NOT YET SUBMITTED" in the Reason column with the Current Status
        # column blank. The earlier snapshots in this repository normalise that to
        # status="NOT YET SUBMITTED" / reason="Team submission outstanding at report time",
        # so the pipeline treats the two releases identically.
        pending = not r["player"]
        recs.append([
            f"{r['game_date'][6:10]}-{r['game_date'][0:2]}-{r['game_date'][3:5]}",
            r["game_time"], r["matchup"], r["team"], r["player"],
            "NOT YET SUBMITTED" if pending else r["status"],
            "Team submission outstanding at report time" if pending else r["reason"],
            "E",
        ])
    doc = {
        "dataset": "official_injury_report",
        "release": "2026-11-14 05:00 a.m ET",
        "as_of": "2026-11-14",
        "retrieved_at_utc": RETRIEVED,
        "method": CAP["method"],
        "provenance": {
            "primary_source": {
                "publisher": "NBA Official Injury Report (official)",
                "source_class": "official",
                "official_nba_source": True,
                "url": CAP["sources"]["injury_report"],
                "release_index": CAP["sources"]["injury_index"],
                "fields": ["game_date", "time_et", "matchup", "team", "player", "status",
                           "reason"],
                "note": ("The newest release listed on the official injury-report index at "
                         "capture time. The index lists the 2026-11-14 releases from 12:00 a.m "
                         "ET through 5:00 a.m ET, so this supersedes the 11/13 19:30 ET release "
                         "the site published until this refresh. It is the first release that "
                         "carries the 2026-11-15 slots (all still NOT YET SUBMITTED) and the "
                         "first in which every row repeats its team, so the page-break blank "
                         "team column that produced the Martin/Cleveland mis-attribution in "
                         "the 19:30 ET transcript cannot recur here. Every row therefore carries "
                         "attribution='E' (explicit team), including the NOT YET SUBMITTED "
                         "placeholders - the team is printed on those rows too."),
            },
            "supersedes": "data/raw/injury_report_2026-11-13_1930ET.json (kept committed: it is "
                          "the only source for the 2026-11-13 game rows)",
        },
        "columns": ["game_date", "time_et", "matchup", "team", "player", "status", "reason",
                    "attribution"],
        "records": recs,
        "record_counts": {
            "total_rows": len(recs),
            "rows_2026_11_14": sum(1 for r in recs if r[0] == "2026-11-14"),
            "rows_2026_11_15": sum(1 for r in recs if r[0] == "2026-11-15"),
            "not_yet_submitted_placeholders": sum(1 for r in recs if r[5] == "NOT YET SUBMITTED"),
            "attribution_explicit": sum(1 for r in recs if r[7] == "E"),
            "attribution_continuation": sum(1 for r in recs if r[7] == "C"),
            "note": "counts computed from the records array at write time",
        },
        "transcription_note": (
            "The PDF prints the Game Time in a 12-hour clock with no meridian marker: the 19:00 ET "
            "game is printed '07:00 (ET)'. Times are transcribed exactly as printed. 'NOT YET "
            "SUBMITTED' is printed in the Reason column with the Current Status column blank; this "
            "transcript normalises it to status='NOT YET SUBMITTED' / reason='Team submission "
            "outstanding at report time', exactly as the earlier committed snapshots do, so both "
            "releases are processed identically."),
        "time_column_note": (
            "The PDF prints the Game Time in a 12-hour clock with no meridian marker: the "
            "19:00 ET game is printed '07:00 (ET)'. Times here are transcribed exactly as "
            "printed; the 24-hour value used by the model is derived elsewhere."),
    }
    path = RAW / "injury_report_2026-11-14_0500ET.json"
    path.write_text(json.dumps(doc, indent=2) + "\n")
    return path


def write_finals() -> Path:
    doc = {
        "dataset": "official_final_scores",
        "as_of": "2026-11-13",
        "retrieved_at_utc": RETRIEVED,
        "method": CAP["method"],
        "source": CAP["sources"]["schedule"],
        "records": [
            {"game_id": f["game_id"], "away_pts": f["away_pts"], "home_pts": f["home_pts"],
             "overtime": f["overtime"], "source": f["source"]}
            for f in CAP["finals_2026_11_13"]
        ],
        "note": ("The nine 2026-11-13 games, read as 'Final' / 'Final/OT' on the official "
                 "schedule page. These games are the day-before context the model priced; they "
                 "are NOT in either sealed ledger, so settling against them must never be "
                 "reported as a settled registered forecast."),
    }
    path = RAW / "finals_2026-11-13.json"
    path.write_text(json.dumps(doc, indent=2) + "\n")
    return path


if __name__ == "__main__":
    for fn in (write_standings, write_injury, write_finals):
        p = fn()
        print("wrote", p.relative_to(ROOT))
