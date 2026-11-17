"""Build the official injury-report archive: per-release rows, provenance, checks, consecutive diffs.

Run:  python -m nba2.injury_archive            (writes data/injuries/archive/*.json)
      python -m nba2.injury_archive --check    (rebuilds in memory and fails if files differ)

Inputs are only files already in the repository:
  * data/raw/pdf/Injury-Report_<date>_<time>.pdf    official PDF bytes (sha256 recorded)
  * data/raw/pdf/*.txt                               independent flat-text extraction (where present)
  * data/raw/refresh_2026-11-16/injury_transcript_*.json  recorded retrieval stamps (where present)
Nothing is fetched over the network.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .parse import NOT_SUBMITTED, STATUSES, parse_pdf

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "data" / "raw" / "pdf"
OUT_DIR = ROOT / "data" / "injuries" / "archive"
INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"
PDF_URL = "https://ak-static.cms.nba.com/referee/injury/{name}.pdf"
ET = dt.timezone(dt.timedelta(hours=-5))  # ET is UTC-5 on 2026-11-16 and 2026-11-17 (after DST ended 2026-11-01)

# Recorded retrieval stamps. Only values written into a repo file are used; None = not recorded.
RETRIEVAL = {
    "2026-11-16_0930AM": ("data/raw/refresh_2026-11-16/injury_transcript_20261116_0930AM_superseded.json", "2026-11-16T14:52:00Z"),
    "2026-11-16_0100PM": ("data/raw/refresh_2026-11-16/injury_transcript_20261116_0100PM.json", "2026-11-16T18:38:00Z"),
    "2026-11-16_0215PM": None,
    "2026-11-17_0945AM": None,
}

FILES = {
    "2026-11-16_0930AM": "Injury-Report_2026-11-16_09_30AM",
    "2026-11-16_0100PM": "Injury-Report_2026-11-16_01_00PM",
    "2026-11-16_0215PM": "Injury-Report_2026-11-16_02_15PM",
    "2026-11-17_0945AM": "Injury-Report_2026-11-17_09_45AM",
}
ORDER = list(FILES)  # revision order (verified below against the PDF header stamps)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _pdf_creation(p: Path) -> str | None:
    import pypdf  # optional dependency (regeneration only)

    raw = pypdf.PdfReader(str(p)).metadata.get("/CreationDate")  # e.g. D:20261116093003-05'00'
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})([+-])(\d{2})'(\d{2})", raw or "")
    if not m:
        return None
    y, mo, d, h, mi, s, sg, oh, om = m.groups()
    off = dt.timedelta(hours=int(oh), minutes=int(om)) * (1 if sg == "+" else -1)
    return dt.datetime(int(y), int(mo), int(d), int(h), int(mi), int(s), tzinfo=dt.timezone(off)).isoformat()


def _plain_text(p: Path) -> str:
    import pypdf  # optional dependency (regeneration only)

    return _norm(" ".join(pg.extract_text() or "" for pg in pypdf.PdfReader(str(p)).pages))


def _release_checks(rid: str, pdf: Path, parsed: dict, creation_iso: str | None) -> dict:
    plain = _plain_text(pdf)
    status_plain = len(re.findall(r"\b(Out|Questionable|Doubtful|Probable|Available)\b", plain))
    nys_plain = plain.count(NOT_SUBMITTED)
    rows = parsed["rows"]
    checks = {
        "parse_problems": len(parsed["problems"]),
        "status_words_plain_text": status_plain,
        "status_rows_parsed": len(rows),
        "status_count_matches_plain_text": status_plain == len(rows),
        "not_yet_submitted_plain_text": nys_plain,
        "not_yet_submitted_parsed": len(parsed["team_not_submitted"]),
        "not_yet_submitted_matches_plain_text": nys_plain == len(parsed["team_not_submitted"]),
        # strict: the full printed name (as parsed) must occur verbatim in the normalised plain text
        "every_player_name_in_plain_text": all(_norm(r["player"]) in plain for r in rows),
        "every_row_has_date_matchup_team": all(r["game_date"] and r["matchup"] and r["team"] for r in rows)
                                           and all(r["game_date"] and r["matchup"] and r["team"]
                                                   for r in parsed["team_not_submitted"]),
        # The PDF prints a start time once per time group; some blocks carry none. Those stay blank (never borrowed).
        "blocks_without_printed_time": sorted({r["matchup"] for r in rows + parsed["team_not_submitted"]
                                               if not r["time_et"]}),
        "page_count": parsed["page_count"],
        "header_stamp": parsed["header_stamp"],
    }
    stamp = parsed["header_stamp"]
    if stamp:
        hdr_iso = dt.datetime.strptime(f"{stamp[0]} {stamp[1]}", "%m/%d/%y %I:%M %p").replace(tzinfo=ET).isoformat()
    else:
        hdr_iso = None
    checks["header_revision_et"] = hdr_iso
    checks["pdf_creation_utc_matches_header"] = bool(
        creation_iso and hdr_iso and abs(dt.datetime.fromisoformat(creation_iso) - dt.datetime.fromisoformat(hdr_iso))
        <= dt.timedelta(minutes=1))
    # independent flat-text extraction (the stored .txt), where one was captured
    txt = PDF_DIR / (FILES[rid] + ".txt")
    if txt.exists():
        t = _norm(txt.read_text())
        checks["stored_txt_present"] = True
        checks["stored_txt_not_yet_submitted"] = t.count(NOT_SUBMITTED)
        checks["stored_txt_status_words"] = len(re.findall(r"\b(Out|Questionable|Doubtful|Probable|Available)\b", t))
        checks["stored_txt_matches_parsed"] = (
            checks["stored_txt_not_yet_submitted"] == len(parsed["team_not_submitted"])
            and checks["stored_txt_status_words"] == len(rows))
    else:
        checks["stored_txt_present"] = False
    # teams absent from a game (neither a player row nor a NOT YET SUBMITTED line)
    seen = defaultdict(set)
    for r in rows + parsed["team_not_submitted"]:
        seen[r["matchup"]].add(r["team"])
    checks["games_with_one_team_only"] = sorted(m for m, ts in seen.items() if len(ts) < 2)
    checks["games_with_one_team_only_detail"] = {
        m: sorted(ts) for m, ts in seen.items() if len(ts) < 2}
    return checks


def build_release(rid: str) -> dict:
    pdf = PDF_DIR / (FILES[rid] + ".pdf")
    parsed = parse_pdf(pdf)
    creation = _pdf_creation(pdf)
    checks = _release_checks(rid, pdf, parsed, creation)
    ret = RETRIEVAL.get(rid)
    rel = {
        "release_id": rid,
        "report_stamp_et": " ".join(parsed["header_stamp"]) if parsed["header_stamp"] else None,
        "revision_time_et": checks["header_revision_et"],
        "pdf_creation_time": creation,
        "retrieved_at_utc": ret[1] if ret else None,
        "retrieval_record": ret[0] if ret else "not recorded in the repository",
        "pdf_file": f"data/raw/pdf/{FILES[rid]}.pdf",
        "pdf_url": PDF_URL.format(name=FILES[rid]),
        "pdf_bytes": pdf.stat().st_size,
        "pdf_sha256": _sha256(pdf),
        "index_url": INDEX_URL,
        "rows": parsed["rows"],
        "team_not_submitted": parsed["team_not_submitted"],
        "checks": checks,
        "problems": parsed["problems"],
    }
    return rel


def _key(r: dict) -> tuple:
    return (r["game_date"], r["matchup"], r["team"], r["player"])


def diff(old: dict, new: dict) -> dict:
    """Consecutive-report diff keyed by (game date, matchup, team, player)."""
    o = {_key(r): r for r in old["rows"]}
    n = {_key(r): r for r in new["rows"]}
    dup_old = [k for k, c in Counter(_key(r) for r in old["rows"]).items() if c > 1]
    dup_new = [k for k, c in Counter(_key(r) for r in new["rows"]).items() if c > 1]
    added = [{"key": list(k), "status": n[k]["status"], "reason": n[k]["reason"]} for k in sorted(n.keys() - o.keys(), key=str)]
    removed = [{"key": list(k), "status": o[k]["status"], "reason": o[k]["reason"]} for k in sorted(o.keys() - n.keys(), key=str)]
    status_changed = []
    reason_changed = []
    for k in sorted(o.keys() & n.keys(), key=str):
        if o[k]["status"] != n[k]["status"]:
            status_changed.append({"key": list(k), "from": o[k]["status"], "to": n[k]["status"],
                                   "reason_from": o[k]["reason"], "reason_to": n[k]["reason"]})
        elif o[k]["reason"] != n[k]["reason"]:
            reason_changed.append({"key": list(k), "status": n[k]["status"], "from": o[k]["reason"], "to": n[k]["reason"]})
    # team-level transitions: NOT YET SUBMITTED <-> player rows
    old_nys = {(r["game_date"], r["matchup"], r["team"]) for r in old["team_not_submitted"]}
    new_nys = {(r["game_date"], r["matchup"], r["team"]) for r in new["team_not_submitted"]}
    return {
        "from": old["release_id"],
        "to": new["release_id"],
        "from_revision_et": old["revision_time_et"],
        "to_revision_et": new["revision_time_et"],
        "counts": {"added": len(added), "removed": len(removed), "status_changed": len(status_changed),
                   "reason_changed": len(reason_changed),
                   "team_newly_not_submitted": len(new_nys - old_nys),
                   "team_newly_submitted": len(old_nys - new_nys)},
        "duplicate_keys": {"old": [list(k) for k in dup_old], "new": [list(k) for k in dup_new]},
        "added": added,
        "removed": removed,
        "status_changed": status_changed,
        "reason_changed": reason_changed,
        "team_newly_submitted": [list(k) for k in sorted(old_nys - new_nys, key=str)],
        "team_newly_not_submitted": [list(k) for k in sorted(new_nys - old_nys, key=str)],
        "note": ("'removed' means the player is absent from the later release. The report does not print a reason; "
                 "for a game dated before the later release, absence reflects the game date passing, not a cleared status."),
    }


def build_all() -> dict:
    releases = [build_release(rid) for rid in ORDER]
    # the stored order must be the revision order printed in each header
    for a, b in zip(releases, releases[1:]):
        ta = dt.datetime.fromisoformat(a["revision_time_et"])
        tb = dt.datetime.fromisoformat(b["revision_time_et"])
        if not ta < tb:
            raise SystemExit(f"revision order violated: {a['release_id']} !< {b['release_id']}")
    diffs = [diff(a, b) for a, b in zip(releases, releases[1:])]
    return {
        "schema": "nba2.injury-archive.v1",
        "built_by": "nba2.injury_archive (session arena/3a56251c-nba2, task 3A-03)",
        "method": ("Each official PDF in data/raw/pdf is parsed by page coordinates (pypdf visitor, flipped CTM applied). "
                   "Every player row is checked against the PDF's plain text extraction and, where a stored .txt exists, against it. "
                   "A cell that cannot be placed is listed in problems, never guessed."),
        "index_url": INDEX_URL,
        "latest_stored_release": releases[-1]["release_id"],
        "latest_release_gap": ("The 2026-11-17 capture index (data/raw/refresh_2026-11-17/capture_index.json, retrieved "
                               "2026-11-17T15:52:00Z) names an official release Injury-Report_2026-11-17_10_30AM.pdf. "
                               "That PDF is not stored in the repository and cannot be fetched from this sandbox. Not inferred."),
        "releases": releases,
        "diffs": diffs,
    }


def write(doc: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "archive.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


def main(argv: list[str]) -> int:
    try:
        doc = build_all()
    except ImportError as exc:
        print(f"regeneration needs the optional pypdf package ({exc}); install it with: pip install pypdf")
        return 2
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    if "--check" in argv:
        path = OUT_DIR / "archive.json"
        if not path.exists() or path.read_text() != text:
            print("archive.json is out of date; run: python -m nba2.injury_archive")
            return 1
        print("archive.json is up to date")
        return 0
    write(doc)
    print(f"wrote {OUT_DIR / 'archive.json'}: {len(doc['releases'])} releases, {len(doc['diffs'])} consecutive diffs")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
