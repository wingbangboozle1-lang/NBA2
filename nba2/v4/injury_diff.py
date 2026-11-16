"""Store every injury release with both stamps, and diff consecutive releases.

"Store" here means exactly what the sandbox can do, and the limitation is published rather
than papered over (F-V4-01):

* the release's **official URL**, its **revision stamp** (the time in the PDF's own header,
  e.g. ``11/16/26 09:15 AM``), the **time the league index was checked**, and the
  **retrieval timestamp** are all stored;
* the **transcribed text** is stored, with a sha256 over the transcription
  (``content_sha256``) so any later edit is detectable;
* the **original PDF bytes are not stored**, because bash egress to
  ``ak-static.cms.nba.com`` is blocked in this sandbox and the page tool renders the PDF as
  text. The reason is recorded on every release document.

The diff matches rows on ``(date, matchup, team, player)`` and reports status changes,
reason-only changes, additions, removals and placeholder transitions. A blank status is
diffed as blank: it is never coerced to "Unknown" and never treated as equal to a real
status.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import capture as C

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "v4" / "injury"


def release_docs() -> list[dict]:
    today = ROOT / "data" / "raw" / "refresh_2026-11-16"
    docs = []
    for p in sorted(today.glob("injury_transcript_*.json")):
        docs.append(json.loads(p.read_text()))
    return docs


def key(row) -> tuple:
    date, _time, matchup, team, player = row[0], row[1], row[2], row[3], row[4]
    return (date, matchup, team, player)


def _bucket(rows: list[list]) -> dict:
    out = {}
    for r in rows:
        out[key(r)] = {"status": r[5], "reason": r[6], "note": r[7]}
    return out


def diff(a: dict, b: dict) -> dict:
    ka, kb = set(_bucket(a["records"])), set(_bucket(b["records"]))
    A, B = _bucket(a["records"]), _bucket(b["records"])
    changes, reason_only, added, removed, placeholder = [], [], [], [], []
    for k in sorted(ka & kb):
        ra, rb = A[k], B[k]
        if ra["status"] != rb["status"]:
            # a placeholder becoming a real submission is not a "status change"
            if not ra["status"] and not rb["status"]:
                continue
            changes.append({"key": k, "from": ra["status"], "to": rb["status"],
                            "reason_from": ra["reason"], "reason_to": rb["reason"],
                            "kind": "placeholder_resolved" if not ra["status"] else "status"})
        elif ra["reason"] != rb["reason"]:
            reason_only.append({"key": k, "status": ra["status"],
                                "reason_from": ra["reason"], "reason_to": rb["reason"]})
    for k in sorted(kb - ka):
        added.append({"key": k, "status": B[k]["status"], "reason": B[k]["reason"]})
    for k in sorted(ka - kb):
        removed.append({"key": k, "status": A[k]["status"], "reason": A[k]["reason"]})
    for k in sorted(ka & kb):
        if not A[k]["status"] and not B[k]["status"]:
            placeholder.append({"key": k, "reason": A[k]["reason"]})
    return {
        "from": {"stamp_et": a["report_stamp_et"], "url": a["provenance"]["url"],
                 "retrieved_utc": a["retrieved_at_utc"], "rows": len(a["records"])},
        "to": {"stamp_et": b["report_stamp_et"], "url": b["provenance"]["url"],
               "retrieved_utc": b["retrieved_at_utc"], "rows": len(b["records"])},
        "match_key": ["date", "matchup", "team", "player"],
        "counts": {"status_changed": len([c for c in changes if c["kind"] == "status"]),
                   "placeholder_resolved": len([c for c in changes
                                                if c["kind"] == "placeholder_resolved"]),
                   "reason_changed_only": len(reason_only),
                   "added": len(added), "removed": len(removed),
                   "still_placeholder": len(placeholder)},
        "status_changes": changes, "reason_changes": reason_only,
        "added": added, "removed": removed, "still_placeholder": placeholder,
        "note": ("Mechanical diff. 'Added' includes a team replacing a single NOT YET "
                 "SUBMITTED placeholder with a full submission, so an evening release "
                 "legitimately adds many rows. A blank status is diffed as blank and is "
                 "never coerced to a value."),
    }


def release_ledger() -> dict:
    """The stored releases (this session's) plus the historical ones already in the repo."""
    docs = release_docs()
    stored = []
    for d in docs:
        stored.append({
            "report_stamp_et": d["report_stamp_et"],
            "revision_time_et": d["revision_time_et"],
            "retrieved_at_utc": d["retrieved_at_utc"],
            "index_checked_utc": d.get("index_checked_utc"),
            "url": d["provenance"]["url"],
            "rows": len(d["records"]),
            "content_sha256": d["content_sha256"],
            "binary_stored": d["binary_stored"],
            "binary_stored_reason": d["binary_stored_reason"],
            "layout_notes": d["layout_notes"],
        })
    return {
        "n_releases_stored_this_session": len(stored),
        "releases": stored,
        "diffs": [diff(docs[i], docs[i + 1]) for i in range(len(docs) - 1)],
        "consecutive_release_diffs": max(0, len(docs) - 1),
        "gap": ("Where two consecutive releases lie on the same day, the diff isolates "
                "revision drift. A night-to-morning diff mixes drift with the league's "
                "filing deadline, which is why the same-day pair is the one to read."),
        "binary_gap_flag": "F-V4-01",
    }


def comparison_with_committed() -> dict:
    """This session's 11/16 release vs the 11/15 releases already committed.

    Published because it is the only cross-day pair available, and because a reader
    deserves to see that the drift is large and explainable (filing deadlines), not that
    the league changed 60 statuses overnight.
    """
    hist = ROOT / "data" / "raw" / "capture_2026-11-15" / "injury_report_2026-11-15_0615PM.json"
    docs = release_docs()
    if not hist.exists() or not docs:
        return {"available": False}
    old = json.loads(hist.read_text())
    new = docs[0]
    old_rows = [r[:5] + [r[5], r[6], r[7] if len(r) > 7 else ""] for r in old["records"]]
    d = diff({"report_stamp_et": old["report_stamp_et"],
              "retrieved_at_utc": old["retrieved_at_utc"],
              "provenance": old["provenance"], "records": old_rows},
             {"report_stamp_et": new["report_stamp_et"],
              "retrieved_at_utc": new["retrieved_at_utc"],
              "provenance": new["provenance"], "records": new["records"]})
    return {"available": True, "cross_day": True, "diff": d}


def write() -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": "nba2.v4.injury-releases.v1",
        "session": C.SESSION,
        "retrieved_utc": C.RETRIEVED_UTC,
        "ledger": release_ledger(),
        "cross_day_comparison": comparison_with_committed(),
        "policy": {
            "revision_time": "the time printed in the release's own header",
            "retrieval_time": "when this session read it (UTC)",
            "index_checked": "when the official index was checked for a newer release",
            "bytes": "NOT stored - see F-V4-01",
        },
    }
    p = OUT / "releases.json"
    p.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    return [str(p.relative_to(ROOT))]


if __name__ == "__main__":
    for f in write():
        print("wrote", f)
    lg = release_ledger()
    print(f"releases stored: {lg['n_releases_stored_this_session']}, "
          f"consecutive diffs: {lg['consecutive_release_diffs']}")
    for d in lg["diffs"]:
        print("  diff", d["from"]["stamp_et"], "->", d["to"]["stamp_et"], d["counts"])
