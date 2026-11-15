"""Re-emit the 2026-11-15 06:15 AM injury snapshot in the schema the repo already validates.

The capture written earlier in this session used a newer, richer shape (dict records,
`revision_stamp_et`, a separate `no_row_printed` list). That broke
`tools/crosscheck_site.py`, which reads `columns` + list-of-list `records` +
`record_counts` from every `data/raw/injury_report_*.json` — a file owned by another
session, so the snapshot is conformed instead of the tool being changed.

Nothing is lost: every field the newer shape carried is preserved alongside the old keys,
because `nba2/v2/injury_diff.py:load_release()` reads either shape. The NOT YET SUBMITTED
placeholders move *into* the records table exactly as the older transcripts store them
(empty player cell, status "NOT YET SUBMITTED"), so `record_counts.total_rows` is the
count of printed PDF rows and `rows_with_status` subtracts the placeholders — the same
arithmetic the older files use.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "raw" / "injury_report_2026-11-15_0615AM.json"
COLUMNS = ["game_date", "time_et", "matchup", "team", "player", "status", "reason",
           "attribution"]
ATTRIBUTION_KEY = {
    "E": "the PDF printed this row's Game Date cell (or the block's first date)",
    "C": "date and time cells were blank on a continuation page; carried down from above",
}


def main() -> None:
    d = json.loads(SRC.read_text())
    records = [[r["game_date"], r["game_time_et"], r["matchup"], r["team"], r["player"],
                r["status"], r["reason"], r["attribution"]] for r in d["records"]]
    for r in d.get("not_yet_submitted", []):
        records.append([r["game_date"], r["game_time_et"], r["matchup"], r["team"], "",
                        "NOT YET SUBMITTED", "NOT YET SUBMITTED", "E"])
    nys = sum(1 for r in records if r[5] == "NOT YET SUBMITTED")
    counts = {
        "total_rows": len(records),
        "rows_with_status": len(records) - nys,
        "not_yet_submitted_placeholders": nys,
        "attribution_explicit": sum(1 for r in records if r[7] == "E"),
        "attribution_continuation": sum(1 for r in records if r[7] == "C"),
        "games_covered": len({r[2] for r in records}),
        "note": "counts computed from the records table in this file",
    }
    out = {
        "dataset": "nba_official_injury_report",
        "report_stamp_et": d["revision_stamp_et"],
        "revision_stamp_et": d["revision_stamp_et"],
        "retrieved_at_utc": d["retrieved_at_utc"],
        "retrieval_method": d.get("session", "session arena/673acec0-nba2"),
        "provenance": {
            "publisher": "NBA (official)",
            "official_nba_source": True,
            "url": d["provenance"]["url"],
            "index_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
            "document_header": f"Injury Report: {d['revision_stamp_et']}",
            "class": "official",
        },
        "attribution_key": ATTRIBUTION_KEY,
        "columns": COLUMNS,
        "record_counts": counts,
        "records": records,
        # richer extras the newer readers use; the old schema is unaffected by their presence
        "no_row_printed": d.get("no_row_printed", []),
        "schema": d.get("schema", "nba2.injury-report.v1"),
        "session": d.get("session", ""),
    }
    SRC.write_text(json.dumps(out, indent=1) + "\n")
    print(f"rewrote {SRC.relative_to(ROOT)}: {len(records)} printed rows "
          f"({counts['rows_with_status']} with a real status, "
          f"{counts['not_yet_submitted_placeholders']} NOT YET SUBMITTED placeholders), "
          f"{counts['games_covered']} games")


if __name__ == "__main__":
    main()
