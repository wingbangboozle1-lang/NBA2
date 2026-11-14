#!/usr/bin/env python3
"""Parse the official NBA injury report 11/13/26 07:15 PM (verbatim fetch captures)
into structured rows, validate round-trip against the source text, and diff against the
repo's published 04:15 PM snapshot.

Source files (verbatim captures of fetch_page output, 2026-11-14 UTC):
  audit/raw_injury_2026-11-13_0715PM_chunk0.md
  audit/raw_injury_2026-11-13_0715PM_chunk1.md
Official URL: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_15PM.pdf

No value is invented: every parsed cell must be found verbatim in the source text.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
SRC_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_15PM.pdf"

TEAMS = {
    "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
    "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
    "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
    "LA Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat",
    "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans",
    "New York Knicks", "Oklahoma City Thunder", "Orlando Magic",
    "Philadelphia 76ers", "Phoenix Suns", "Portland Trail Blazers",
    "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors", "Utah Jazz",
    "Washington Wizards",
}
STATUSES = {"Out", "Available", "Questionable", "Probable", "Doubtful"}
RE_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
RE_TIME = re.compile(r"^\d{2}:\d{2} \(ET\)$")
RE_MATCHUP = re.compile(r"^[A-Z]{3}@[A-Z]{3}$")


def load_source() -> str:
    c0 = (AUDIT / "raw_injury_2026-11-13_0715PM_chunk0.md").read_text()
    c1 = (AUDIT / "raw_injury_2026-11-13_0715PM_chunk1.md").read_text()
    # chunk0 ends mid-word ("...Subl"), chunk1 resumes ("uxation |...")
    if not c0.rstrip().endswith("Subl"):
        raise SystemExit("chunk0 tail does not end at the expected split point")
    if not c1.startswith("uxation |"):
        raise SystemExit("chunk1 head does not start at the expected split point")
    return c0.rstrip("\n") + c1  # mid-word split: no newline at the join


def split_cells(line: str) -> list[str]:
    parts = line.split("|")
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return [p.strip() for p in parts[1:]]


def parse(src: str) -> list[dict]:
    rows: list[dict] = []
    date = time = matchup = team = None
    n_raw = 0
    for line in src.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if set(line.replace("|", "").replace(" ", "")) <= {"-", ":"}:
            continue  # separator row
        if "Game Date" in line and "Player Name" in line:
            continue  # header
        n_raw += 1
        cells = split_cells(line)
        # classify
        e_date = next((c for c in cells if RE_DATE.match(c)), None)
        e_time = next((c for c in cells if RE_TIME.match(c)), None)
        e_match = next((c for c in cells if RE_MATCHUP.match(c)), None)
        e_team = next((c for c in cells if c in TEAMS), None)
        if e_date:
            date = e_date
        if e_time:
            time = e_time[:5]
        if e_match:
            matchup = e_match
        if e_team:
            team = e_team

        if "NOT YET SUBMITTED" in cells:
            rows.append({
                "game_date": date, "time_et": time, "matchup": matchup, "team": team,
                "player": "", "status": "", "reason": "NOT YET SUBMITTED",
                "attribution": "E" if e_team else "C",
            })
            continue

        s_idx = next((i for i, c in enumerate(cells) if c in STATUSES), None)
        if s_idx is None:
            raise SystemExit(f"no status cell in row: {line!r}")
        player = cells[s_idx - 1] if s_idx >= 1 else ""
        if not player or player in TEAMS or RE_MATCHUP.match(player) or RE_TIME.match(player) or RE_DATE.match(player):
            raise SystemExit(f"cannot identify player in row: {line!r}")
        reason_cells = [c for c in cells[s_idx + 1:] if c != ""]
        reason = " | ".join(reason_cells)
        if not reason:
            raise SystemExit(f"no reason in row: {line!r}")
        rows.append({
            "game_date": date, "time_et": time, "matchup": matchup, "team": team,
            "player": player, "status": cells[s_idx], "reason": reason,
            "attribution": "E" if e_team else "C",
        })

    # ---- validation -------------------------------------------------------
    # 1) every data line parsed
    data_lines = [ln.strip() for ln in src.splitlines()
                  if ln.strip().startswith("|")
                  and "Game Date" not in ln
                  and not set(ln.strip().replace("|", "").replace(" ", "")) <= {"-", ":"}]
    if len(data_lines) != n_raw:
        raise SystemExit(f"line count mismatch: {len(data_lines)} vs {n_raw}")
    # 2) round-trip: every player/status/reason appears verbatim in source
    for r in rows:
        if r["player"] and r["player"] not in src:
            raise SystemExit(f"player not found in source: {r}")
        if r["status"] and r["status"] not in src:
            raise SystemExit(f"status not found in source: {r}")
        if r["reason"] and r["reason"] not in src:
            raise SystemExit(f"reason not found in source: {r}")
        if r["matchup"] and r["matchup"] not in src:
            raise SystemExit(f"matchup not found in source: {r}")
        if r["team"] and r["team"] not in src:
            raise SystemExit(f"team not found in source: {r}")
    # 3) structural sanity
    dates = {r["game_date"] for r in rows}
    if dates - {"11/13/2026", "11/14/2026"}:
        raise SystemExit(f"unexpected dates: {dates}")
    return rows


def norm_date(d: str) -> str:
    mm, dd, yy = d.split("/")
    return f"{yy}-{mm}-{dd}"


# Documented attribution override: in the 07:15 PM text extraction, Martin Caleb's row
# carries no team cell at a page break. The official 05:15 PM and 06:15 PM revisions print
# "Cleveland Cavaliers" on his row (06:15 fetched directly this session; 05:15 corroborated by
# two independent committed transcriptions: data/injury-report-2026-11-13.csv row 100 and
# data/verified/injuries_2026-11-13_0515PM.json). Block order alone would misattribute him
# to Dallas. Attribution stays "C" (continuation) with this note.
OVERRIDES = {
    ("DAL@CLE", "Martin, Caleb"): {
        "team": "Cleveland Cavaliers",
        "note": "team label dropped by text extraction at page break; Cleveland printed "
                "explicitly on this row in official 05:15 PM and 06:15 PM revisions",
    },
}


def is_pending(rec: list) -> bool:
    return rec[5] == "NOT YET SUBMITTED" or rec[6] == "NOT YET SUBMITTED" \
        or "NOT YET SUBMITTED" in (rec[5] or "") + (rec[6] or "")


def ws(s: str) -> str:
    """Whitespace-normalised comparison form (the PDF text layer drops some spaces)."""
    return " ".join((s or "").split())


def main() -> None:
    src = load_source()
    rows = parse(src)
    out = {
        "dataset": "official NBA injury report transcription",
        "report_stamp_et": "2026-11-13 19:15",
        "retrieved_at_utc": "2026-11-14T01:20:00Z",
        "source_url": SRC_URL,
        "verification": "row-by-row verbatim capture via official PDF; every cell round-trip "
                        "checked against the captured source text (audit/parser asserts "
                        "player/status/reason/matchup/team substrings exist in source)",
        "columns": ["game_date", "time_et", "matchup", "team", "player", "status", "reason", "attribution"],
        "records": [
            [norm_date(r["game_date"]), r["time_et"], r["matchup"], r["team"],
             r["player"], r["status"], r["reason"], r["attribution"]]
            for r in rows
        ],
    }
    p = AUDIT / "injury_report_2026-11-13_0715PM.json"
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    n13 = sum(1 for r in out["records"] if r[0] == "2026-11-13")
    n14 = sum(1 for r in out["records"] if r[0] == "2026-11-14")
    pend = sum(1 for r in out["records"] if r[6] == "NOT YET SUBMITTED")
    print(f"wrote {p.relative_to(ROOT)}: {len(out['records'])} rows "
          f"(11/13: {n13}, 11/14: {n14}, pending: {pend})")

    # ---------------- delta vs published 04:15 snapshot --------------------
    pub = json.loads((ROOT / "data" / "raw" / "injury_report_2026-11-13.json").read_text())
    pub_stamp = pub["report_stamp_et"]
    pub_recs = pub["records"]  # [game_date, time_et, matchup, team, player, status, reason, attribution]

    # apply documented overrides to the latest capture
    for r in out["records"]:
        ov = OVERRIDES.get((r[2], r[4]))
        if ov:
            r[3] = ov["team"]
            r[7] = "C"  # continuation attribution, override documented above

    def key(r):
        # player rows keyed by (matchup, player) so team re-attribution across revisions
        # cannot orphan a row; pending placeholders (no player) keyed by team as well
        return (r[2], r[4]) if r[4] else (r[2], r[3], r[4])

    new_by = {key(r): r for r in out["records"]}
    old_by = {key(r): r for r in pub_recs}
    added = [new_by[k] for k in new_by if k not in old_by]
    removed = [old_by[k] for k in old_by if k not in new_by]
    changed, formatting = [], []
    for k in new_by:
        if k in old_by:
            n, o = new_by[k], old_by[k]
            n_pend, o_pend = is_pending(n), is_pending(o)
            if n_pend and o_pend:
                continue  # still pending in both revisions: not a change
            if n_pend != o_pend or n[5] != o[5]:
                changed.append({
                    "matchup": n[2], "team": n[3], "player": n[4],
                    "published_status": o[5], "published_reason": o[6],
                    "latest_status": n[5], "latest_reason": n[6],
                    "game_date": n[0],
                })
            elif ws(n[6]) != ws(o[6]):
                # different words, or the same words with spaces dropped by the text layer
                if "".join((n[6] or "").split()) == "".join((o[6] or "").split()):
                    formatting.append({
                        "matchup": n[2], "team": n[3], "player": n[4],
                        "published_reason": o[6], "latest_reason": n[6],
                        "note": "space dropped by the PDF text layer; not a document change",
                    })
                else:
                    changed.append({
                        "matchup": n[2], "team": n[3], "player": n[4],
                        "published_status": o[5], "published_reason": o[6],
                        "latest_status": n[5], "latest_reason": n[6],
                        "game_date": n[0],
                    })
            elif (n[6] or "") != (o[6] or ""):
                formatting.append({
                    "matchup": n[2], "team": n[3], "player": n[4],
                    "published_reason": o[6], "latest_reason": n[6],
                    "note": "whitespace-only difference in the PDF text layer; "
                            "not a document change",
                })
    delta = {
        "published_snapshot": {"report_stamp_et": pub_stamp,
                               "url": pub["provenance"]["url"],
                               "n_rows": len(pub_recs)},
        "latest_official": {"report_stamp_et": "2026-11-13 19:15", "url": SRC_URL,
                            "n_rows": len(out["records"])},
        "counts": {"status_or_reason_changed": len(changed),
                   "formatting_only": len(formatting),
                   "added_in_latest": len(added),
                   "removed_in_latest": len(removed)},
        "status_changed": changed,
        "formatting_only": formatting,
        "added_in_latest": added,
        "removed_in_latest": removed,
    }
    dp = AUDIT / "injury_delta_0415_to_0715.json"
    dp.write_text(json.dumps(delta, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {dp.relative_to(ROOT)}: {delta['counts']}")
    for c in changed:
        print(f"  CHANGED {c['matchup']} {c['team']} {c['player']}: "
              f"{c['published_status']} -> {c['latest_status']} | "
              f"{c['published_reason']!r} -> {c['latest_reason']!r}")
    for f_ in formatting:
        print(f"  FORMAT  {f_['matchup']} {f_['player']}: {f_['published_reason']!r} -> {f_['latest_reason']!r}")
    for a in added:
        print(f"  ADDED   {a[2]} {a[3]} {a[4] or '(team pending)'}: {a[5] or 'PENDING'}")
    for r in removed:
        print(f"  REMOVED {r[2]} {r[3]} {r[4]}: {r[5]}")


if __name__ == "__main__":
    main()
