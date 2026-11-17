"""Store every injury release with its stamps, and diff consecutive releases.

What changed from the previous build (and why)
----------------------------------------------
The previous version diffed a *hand transcription* of one release against a second release
that was **declared identical** to the first without being read. The test that guarded it
therefore proved that a hard-coded string equalled itself. Two consequences were published
as if they were findings: "0 status changes between 09:15 and 09:30", and six GSW@NOP rows
with a blank status.

Both are now checkable and both were wrong:

* the 09:30 PDF prints ``Doubtful`` for ``Tyson, Jaylon`` where the 09:15 transcription
  recorded ``Questionable``;
* the 09:30 PDF *does* carry ``Out``/``Questionable`` for the six GSW@NOP rows — the earlier
  reading lost the column, it was not missing from the release.

So this module reads the stored **rendering** (``injury_renderings``) and derives every row
by code (``injury_parse``). Nothing between the PDF and the published diff is hand-typed.

Diff semantics
--------------
Rows are matched on ``(date, matchup, team, player)`` — a player, on a club, in a game. A
club that has not filed is one placeholder row, so a filing replaces a placeholder with a
set of real rows; that is reported as ``placeholder_resolved`` (clubs) *and* ``added``
(players), never conflated.

A blank status is diffed as blank and is never coerced to a word. If a status goes from
read to unread, that is reported as ``became_unread`` rather than as a disappearance.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import injury_parse as PA
from . import injury_renderings as RR

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "v4" / "injury"


def parsed() -> list[dict]:
    """Every stored rendering, parsed, in revision order."""
    out = []
    for r in sorted(RR.RENDERS, key=lambda x: RR._revision_key(x["revision_et"])):
        p = PA.parse_render(r["text"])
        out.append({**{k: v for k, v in r.items() if k != "text"},
                    "text_sha256": RR.text_sha(r["text"]),
                    "text_lines": len(r["text"].splitlines()),
                    "parsed": p})
    return out


def _bucket(rows: list[dict]) -> dict:
    out = {}
    for r in rows:
        out[PA.key(r)] = {"status": r["status"], "reason": r["reason"],
                          "placeholder": r["placeholder"], "note": r["note"]}
    return out


def diff(a: dict, b: dict) -> dict:
    """Mechanical diff of two parsed releases."""
    A_raw, B_raw = a["parsed"]["rows"], b["parsed"]["rows"]
    A, B = _bucket(A_raw), _bucket(B_raw)
    ka, kb = set(A), set(B)
    status_changes, reason_only, added, removed, became_unread, resolved = [], [], [], [], [], []

    for k in sorted(ka & kb):
        ra, rb = A[k], B[k]
        if ra["status"] != rb["status"]:
            if ra["status"] and not rb["status"]:
                became_unread.append({"key": k, "from": ra["status"], "to": None})
            else:
                status_changes.append({"key": k, "from": ra["status"], "to": rb["status"],
                                       "reason_from": ra["reason"], "reason_to": rb["reason"]})
        elif ra["reason"] != rb["reason"]:
            reason_only.append({"key": k, "status": ra["status"],
                                "reason_from": ra["reason"], "reason_to": rb["reason"]})

    for k in sorted(kb - ka):
        added.append({"key": k, "status": B[k]["status"], "reason": B[k]["reason"]})
    for k in sorted(ka - kb):
        removed.append({"key": k, "status": A[k]["status"], "reason": A[k]["reason"]})

    # Clubs that moved from "NOT YET SUBMITTED" to a real filing.
    #
    # THE BUG THIS REPLACES (found 2026-11-17, session arena/45f14c5c-nba2)
    # ---------------------------------------------------------------------
    # The loop used to intersect the two key sets. A placeholder's key ends in the
    # sentinel "<placeholder>", while every real row's key ends in a player name, so a
    # club's placeholder and that club's filing can never share a key. The intersection
    # was therefore empty by construction and ``placeholder_resolved`` could only ever be
    # 0 - it was never a measurement. The published injury page showed "0 clubs resolved"
    # beside "33 rows added", which is the same event described two contradictory ways.
    #
    # A club is identified by (date, matchup, team); its filing status is that club's
    # placeholder flag, so the comparison is done at club granularity and each resolution
    # reports how many player rows replaced the placeholder.
    club_a = {(r["date"], r["matchup"], r["team"]): r for r in A_raw}
    club_b = {(r["date"], r["matchup"], r["team"]): r for r in B_raw}
    for k in sorted(set(club_a) & set(club_b)):
        if club_a[k]["placeholder"] and not club_b[k]["placeholder"]:
            resolved.append({"key": k, "players_filed": sum(
                1 for kk in B if kk[0] == k[0] and kk[1] == k[1] and kk[2] == k[2]
                and kk[3] != "<placeholder>")})

    return {
        "from": {"stamp_et": a["stamp_et"], "url": a["url"],
                 "retrieved_utc": a["retrieved_utc"], "rows": a["parsed"]["counts"]["rows"]},
        "to": {"stamp_et": b["stamp_et"], "url": b["url"],
               "retrieved_utc": b["retrieved_utc"], "rows": b["parsed"]["counts"]["rows"]},
        "match_key": ["date", "matchup", "team", "player"],
        "counts": {"status_changed": len(status_changes),
                   "reason_changed_only": len(reason_only),
                   "added": len(added), "removed": len(removed),
                   "became_unread": len(became_unread),
                   "reason_changed_only": len(reason_only),
                   "placeholder_resolved": len(resolved),
                   "still_placeholder": sum(
                       1 for k in set(club_a) & set(club_b)
                       if club_a[k]["placeholder"] and club_b[k]["placeholder"])},
        "status_changes": status_changes,
        "reason_changes": reason_only,
        "added": added,
        "removed": removed,
        "became_unread": became_unread,
        "placeholder_resolved": resolved,
        "note": ("Matched on (date, matchup, team, player). A club's first filing replaces "
                 "its NOT YET SUBMITTED placeholder, so one morning-to-afternoon pair "
                 "legitimately adds many player rows: that is a filing, not instability. "
                 "A blank status is diffed as blank and is never coerced to a value."),
    }


def release_ledger() -> dict:
    rels = parsed()
    stored = []
    for r in rels:
        c = r["parsed"]["counts"]
        stored.append({
            "report_stamp_et": r["stamp_et"],
            "revision_time_et": r["revision_et"],
            "retrieved_at_utc": r["retrieved_utc"],
            "index_checked_utc": r["index_checked_utc"],
            "url": r["url"],
            "rows": c["rows"],
            "rows_with_status": c["with_status"],
            "rows_blank_status": c["blank_status"],
            "placeholders": c["placeholders"],
            "unread": c["unread"],
            "text_sha256": r["text_sha256"],
            "content_sha256": r["text_sha256"],   # kept: the published page prints this
            "text_lines": r["text_lines"],
            "method": r["method"],
            "chunk_junction": r.get("chunk_junction"),
            "binary_stored": False,
            "binary_stored_reason": (
                "the PDF bytes cannot be downloaded from this sandbox: bash egress to "
                "ak-static.cms.nba.com is TLS-reset. nba2/v4/injury_ingest.py attempts the "
                "byte archive from a GitHub runner and records the result; see "
                "data/v4/injury/binary_manifest.json (F-V4-01)."),
            "layout_notes": [
                ("F-V4-06",
                 "GSW@NOP rows in this release keep only Player | Status | Reason, or "
                 "Player | Reason, depending on where the page broke. The parser resolves the "
                 "status from the end of the row and leaves it blank where it is genuinely "
                 "absent; it never assumes the middle cell is a status."),
                ("F-V4-05",
                 "Page-continuation rows print with empty date / time / matchup / team cells. "
                 "They are attributed to the block in progress, and the attribution is written "
                 "on the row."),
                ("F-V4-10",
                 "The 13:00 PM release was returned by the fetch tool in two chunks; the "
                 "junction fell inside the PHX@DEN block. The join basis is recorded on the "
                 "release and can be re-checked against the PDF."),
            ],
        })
    diffs = [diff(rels[i], rels[i + 1]) for i in range(len(rels) - 1)]
    return {
        "n_releases_stored_this_session": len(stored),
        "releases": stored,
        "diffs": diffs,
        "consecutive_release_diffs": len(diffs),
        "gap": ("Where two consecutive releases lie on the same day, the diff isolates "
                "revision drift. A night-to-morning diff mixes drift with the league's filing "
                "deadline, which is why the same-day pair is the one to read."),
        "binary_gap_flag": "F-V4-01",
    }


def cross_session_check() -> dict:
    """Our 09:30 reading vs the 09:15 *transcription* committed by an earlier session.

    This is the check the earlier build could not run, because it never read a second
    release. It answers a narrow, useful question: was the hand transcription faithful?
    Differences are reported per row and are **not** called status changes, because the two
    documents are 15 minutes apart and either explanation (a real revision, or a
    transcription error) is possible. Each row is linked so it can be settled by eye.
    """
    # The 70-row transcription committed by session arena/b3914335-nba2, preserved byte for
    # byte as ``*_superseded.json`` when this session replaced it. Comparing against the
    # *regenerated* file would be comparing this session's reading with itself, which proves
    # nothing; the point of the check is to test the earlier session's record.
    hist = (ROOT / "data" / "raw" / "refresh_2026-11-16"
            / "injury_transcript_20261116_0930AM_superseded.json")
    if not hist.exists():
        hist = (ROOT / "data" / "raw" / "refresh_2026-11-16"
                / "injury_transcript_20261116_0100PM.json")
    rels = parsed()
    if not hist.exists() or not rels:
        return {"available": False}
    old = json.loads(hist.read_text())
    # Compare like with like: the transcript is of the 09:15 AM release, so the right
    # comparison is our 09:30 AM read (the nearest later release), NOT the newest one. An
    # earlier version of this function used rels[0] blindly and silently became a 3.5-hour
    # comparison as soon as a newer release was stored - which would have published genuine
    # afternoon revisions as "transcription errors".
    stamp = (old.get("report_stamp_et") or "").replace(" ET", "").strip()
    first = rels[0]
    for r in rels:
        if r["stamp_et"].replace(" ET", "").strip() >= stamp:
            first = r
            break
    old_rows = []
    for r in old.get("records", []):
        old_rows.append({"date": r[0], "matchup": r[2], "team": r[3], "player": r[4] or None,
                         "status": r[5] or None, "reason": r[6] or None,
                         "placeholder": (r[6] == "NOT YET SUBMITTED"),
                         "note": r[7] if len(r) > 7 else ""})
    old_doc = {"stamp_et": old.get("report_stamp_et"), "url": old["provenance"]["url"],
               "retrieved_utc": old.get("retrieved_at_utc"),
               "parsed": {"rows": old_rows, "counts": {"rows": len(old_rows)}}}
    d = diff(old_doc, first)
    d["compared_against"] = first["stamp_et"]
    d["transcript_stamp"] = old.get("report_stamp_et")
    d["note"] = ("The earlier session's 09:15 AM transcription vs this session's read of the "
                 "09:30 AM PDF. A row that appears here is either a real revision in those 15 "
                 "minutes or a transcription error in the earlier capture; both rows are "
                 "linked to a PDF so the reader can settle it. This is a provenance check, "
                 "not a claim about the league.")
    return {"available": True, "cross_session": True, "diff": d}


def write() -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    problems = RR.selftest()
    if problems:
        raise SystemExit("injury renderings selftest failed:\n  " + "\n  ".join(problems))
    doc = {
        "schema": "nba2.v4.injury-releases.v2",
        "session": "arena/4f780342-nba2",
        "index_url": RR.INDEX_URL,
        "retrieved_utc": RR.newest()["retrieved_utc"],
        "ledger": release_ledger(),
        "cross_session_check": cross_session_check(),
        "policy": {
            "revision_time": "the time printed in the release's own header",
            "retrieval_time": "when this session read it (UTC)",
            "index_checked": "when the official index was last checked for a newer release",
            "rows": ("every cell is assigned by content type, never by position; a cell whose "
                     "type cannot be determined is left blank and flagged"),
            "hash": "sha256 over the stored rendering text, so an edit is detectable",
            "bytes": "the PDF bytes are archived by nba2/v4/injury_ingest.py, not by this build",
        },
    }
    p = OUT / "releases.json"
    p.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    lg = doc["ledger"]
    print(f"releases stored: {lg['n_releases_stored_this_session']}, "
          f"consecutive diffs: {lg['consecutive_release_diffs']}")
    for d in lg["diffs"]:
        print(f"  diff {d['from']['stamp_et']} -> {d['to']['stamp_et']} {d['counts']}")
    return [str(p.relative_to(ROOT))]


if __name__ == "__main__":
    write()
