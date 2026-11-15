"""Injury-report archive: every release stored with its revision stamp, and every
consecutive pair diffed so a status change cannot pass unnoticed.

Brief line 3
------------
    "Store every injury PDF with its timestamp and diff consecutive reports to detect
     status changes."

What is stored
--------------
Each release the project has read is committed under ``data/raw/`` (and, for the earlier
sessions, ``data/raw/history/``) as a row-level transcript carrying:

* ``revision_stamp_et`` — the report's OWN revision time, printed on every page of the PDF
  ("Injury Report: 11/15/26 06:15 AM"). This is the timestamp that matters: it is when the
  league says the information was current, not when we happened to read it.
* ``retrieved_at_utc``  — when this project read it. The gap between the two is published,
  because a report read a day late is a stale report.
* the source PDF URL, and a per-row source link back to it.

The binary PDFs themselves are archived by the nightly ingest job
(``nba2/pipeline/refresh.py --injuries`` writes ``data/raw/pdf/<name>.pdf`` and its
extracted text). This session's sandbox has no outbound network, so it could not commit a
binary; what it commits is the complete transcript plus the two timestamps, and it says so
rather than implying a PDF is on disk when it is not (flag F-K05-PDF).

Diffing
-------
Consecutive releases are compared on ``(team, player, game_date)``. Three things can happen
to a designation between two releases, and all three are published:

* **added**    — a player appears who was not in the previous release (new injury, or a club
  that had not filed now has);
* **dropped**  — a designation disappears (the player was removed from the report: returned,
  or no longer listed);
* **changed**  — the same player, same club, different status (Out -> Doubtful -> ... ).

A dropped row is NOT reported as "healthy". Removal from the report is not the same as
availability, and the module says so in its own output.

Run:  python3 -m nba2.v2.injury_diff
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GLOBS = ["data/raw/injury_report_*.json", "data/raw/history/injury_report_*.json",
         "audit/**/injury_report_*.json"]
OUT = ROOT / "data" / "raw" / "injury_diffs"

# The report prints its own revision stamp; the filename carries it too, and the filename
# is the only place some of the older captures recorded it.
FILE_STAMP = re.compile(r"_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)")


def _stamp_to_iso(date: str, hh: str, mm: str, ampm: str) -> str:
    h = int(hh) % 12 + (12 if ampm.upper() == "PM" else 0)
    return f"{date}T{h:02d}:{int(mm):02d}"


def _norm_status(s) -> str:
    return (s or "").strip()


# The archive spans six sessions and five ways of writing the same timestamp. Every one of
# them is parsed here rather than guessed at; a release whose stamp cannot be parsed is
# dropped from the diff chain rather than slotted in by filename order.
_STAMP_FORMS = (
    re.compile(r"^(\d{4}-\d{2}-\d{2})[ T](\d{1,2}):(\d{2})\s*([AaPp])\.?\s*[Mm]\.?"
               r"(?:\s*(?:ET|E[SD]T))?$"),                       # 2026-11-14 05:00 a.m ET
    re.compile(r"^(\d{4}-\d{2}-\d{2})[ T](\d{1,2}):(\d{2})\s*([AP]M)$", re.I),
    re.compile(r"^(\d{4}-\d{2}-\d{2})[ T](\d{1,2}):(\d{2})$"),   # 2026-11-13 16:15 (24h)
    re.compile(r"^(\d{2})/(\d{2})/(\d{2})\s+(\d{1,2}):(\d{2})\s*([AP]M)\s*(?:ET|E[SD]T)?$",
               re.I),                                                  # 11/14/26 04:30 AM ET
)


def parse_stamp(value) -> str | None:
    """Parse any of the revision-stamp forms the archive has accumulated into 'YYYY-MM-DDTHH:MM'."""
    if isinstance(value, str):
        v = value.strip()
        for rx in _STAMP_FORMS:
            m = rx.match(v)
            if not m:
                continue
            g = m.groups()
            if len(g) == 4 and "-" in g[0]:
                date, hh, mm = g[0], int(g[1]), g[2]
                ap = (g[3] or "")[:1].upper()
                hour = hh % 12 + (12 if ap == "P" else 0) if ap else hh
                return f"{date}T{hour:02d}:{mm}"
            if len(g) == 3:
                return f"{g[0]}T{int(g[1]):02d}:{g[2]}"
            if len(g) == 6:
                mo, dd, yy, hh, mm, ap = g
                hour = int(hh) % 12 + (12 if ap.upper().startswith("P") else 0)
                return f"20{yy}-{mo}-{dd}T{hour:02d}:{mm}"
    return None


def load_release(path: Path) -> dict | None:
    """Read one committed release into a common shape, whatever schema it was written in."""
    try:
        d = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    rows: list[dict] = []
    raw_rows = d.get("records") or d.get("rows") or []
    for r in raw_rows:
        if isinstance(r, dict):
            rows.append({
                "game_date": r.get("game_date") or r.get("date"),
                "team": r.get("team"), "player": r.get("player"),
                "status": _norm_status(r.get("status")),
                "reason": r.get("reason", ""),
                "matchup": r.get("matchup", ""),
            })
        elif isinstance(r, (list, tuple)) and len(r) >= 7:
            # [date, time, matchup, team, player, status, reason, ...]
            rows.append({"game_date": r[0], "team": r[3], "player": r[4],
                         "status": _norm_status(r[5]), "reason": r[6], "matchup": r[2]})
    if not rows:
        return None
    rows = [r for r in rows if r.get("player") and r.get("team")]

    # ---- revision stamp: prefer the report's own field, fall back to the filename
    iso = None
    stamp = None
    for key in ("revision_stamp_et", "report_stamp_et", "release"):
        v = d.get(key) or (d.get("meta", {}) or {}).get(key)
        iso = parse_stamp(v)
        if iso:
            stamp = v
            break
    if iso is None:
        m = FILE_STAMP.search(path.name)
        if m:
            iso = _stamp_to_iso(*m.groups())
    if iso is None:
        return None

    url = ""
    prov = d.get("provenance") or (d.get("meta", {}) or {})
    if isinstance(prov, dict):
        url = prov.get("url") or prov.get("source_url") or ""
        if not url and isinstance(prov.get("primary_source"), dict):
            url = prov["primary_source"].get("url", "")
    retrieved = (d.get("retrieved_at_utc") or (d.get("meta", {}) or {}).get("captured_utc")
                 or "")
    return {
        "file": str(path.relative_to(ROOT)),
        "revision_et": iso,
        "revision_label": stamp or iso,
        "retrieved_at_utc": retrieved,
        "url": url,
        "n_rows": len(rows),
        "rows": rows,
        "not_submitted": d.get("not_submitted") or d.get("not_yet_submitted") or [],
        "no_row_printed": d.get("no_row_printed") or [],
    }


def releases() -> list[dict]:
    out = []
    for g in GLOBS:
        for p in ROOT.glob(g):
            r = load_release(p)
            if r:
                out.append(r)
    out.sort(key=lambda r: r["revision_et"])
    # de-duplicate: two files may hold the same release transcribed by different sessions
    dedup: list[dict] = []
    for r in out:
        if dedup and r["revision_et"] == dedup[-1]["revision_et"]:
            # keep the transcript with the most rows (the more complete transcription)
            if r["n_rows"] > dedup[-1]["n_rows"]:
                dedup[-1] = r
            continue
        dedup.append(r)
    return dedup


def key(row: dict) -> tuple:
    return (row.get("team", ""), row.get("player", ""), row.get("game_date", ""))


def diff(a: dict, b: dict) -> dict:
    """Every difference between release ``a`` (older) and release ``b`` (newer)."""
    A = {key(r): r for r in a["rows"]}
    B = {key(r): r for r in b["rows"]}
    added = [B[k] for k in B if k not in A]
    dropped = [A[k] for k in A if k not in B]
    changed = []
    for k in A:
        if k in B and A[k]["status"] != B[k]["status"]:
            changed.append({"team": k[0], "player": k[1], "game_date": k[2],
                            "from": A[k]["status"], "to": B[k]["status"],
                            "reason_then": A[k].get("reason", ""),
                            "reason_now": B[k].get("reason", "")})
    # a player can also change status within the same report across game dates; those are
    # separate keys, so they surface as added/dropped. Say so rather than mislabelling them.
    added.sort(key=lambda r: (r.get("team", ""), r.get("player", "")))
    dropped.sort(key=lambda r: (r.get("team", ""), r.get("player", "")))
    return {
        "from_revision_et": a["revision_et"], "to_revision_et": b["revision_et"],
        "from_file": a["file"], "to_file": b["file"],
        "source": b["url"] or a["url"],
        "n_before": len(A), "n_after": len(B),
        "n_added": len(added), "n_dropped": len(dropped), "n_changed": len(changed),
        "added": added, "dropped": dropped, "changed": changed,
        "dropped_is_not_healthy": (
            "a designation that disappears from the report is not a clearance: the club may "
            "have stopped listing the player, the game may have passed, or the club may not "
            "have filed. Removal is reported as removal, never as availability."),
    }


def archive() -> dict:
    rel = releases()
    diffs = [diff(rel[i], rel[i + 1]) for i in range(len(rel) - 1)]
    newest = rel[-1] if rel else None
    return {
        "schema": "nba2.injury-archive.v1",
        "n_releases": len(rel),
        "releases": [{k: v for k, v in r.items() if k != "rows"} for r in rel],
        "diffs": diffs,
        "newest": newest,
        "newest_banner": banner(newest) if newest else {},
        "pdf_note": (
            "The binary PDFs are archived by the nightly ingest job at data/raw/pdf/. This "
            "session's environment has no outbound network, so it committed the complete "
            "row-level transcript of the 11/15/26 06:15 AM ET release with both timestamps "
            "instead of the binary, and flags that distinction rather than implying the "
            "binary is on disk (F-K05-PDF)."),
        "total_status_changes": sum(d["n_changed"] for d in diffs),
        "total_added": sum(d["n_added"] for d in diffs),
        "total_dropped": sum(d["n_dropped"] for d in diffs),
    }


def banner(rel: dict | None) -> dict:
    """The injuries-page banner: revision time of the report, and when we read it."""
    if not rel:
        return {}
    return {
        "revision_et": rel["revision_et"],
        "revision_label": rel["revision_label"],
        "retrieved_at_utc": rel["retrieved_at_utc"],
        "url": rel["url"],
        "n_rows": rel["n_rows"],
        "n_not_submitted": len(rel["not_submitted"]),
        "n_no_row": len(rel["no_row_printed"]),
        "source": rel["url"],
    }


def main() -> int:
    a = archive()
    OUT.mkdir(parents=True, exist_ok=True)
    for d in a["diffs"]:
        name = (d["from_revision_et"].replace(":", "") + "__to__"
                + d["to_revision_et"].replace(":", "") + ".json")
        (OUT / name).write_text(json.dumps(d, indent=1) + "\n")
    print(f"{a['n_releases']} committed releases, {len(a['diffs'])} consecutive diffs")
    for r in a["releases"]:
        print(f"  {r['revision_et']}  {r['n_rows']:>3} rows  read {r['retrieved_at_utc']}"
              f"  {r['file']}")
    for d in a["diffs"]:
        print(f"  {d['from_revision_et']} -> {d['to_revision_et']}: "
              f"+{d['n_added']} added, -{d['n_dropped']} dropped, "
              f"{d['n_changed']} status changes")
        for c in d["changed"]:
            print(f"      {c['team']} {c['player']}: {c['from']} -> {c['to']}")
    print(f"wrote {len(a['diffs'])} diff files to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
