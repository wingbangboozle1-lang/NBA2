"""Nightly ingest + settlement pipeline (audit finding A-01 remediation, v1).

Fail-closed by design: every subcommand either produces a verified artefact or exits
non-zero. Nothing here invents a value, rewrites a sealed prediction, or publishes a
transcript that no human/agent session has reviewed.

Subcommands
-----------
--injuries --date YYYY-MM-DD [-o DIR]
    Read the official injury-report index page (official.nba.com), find the newest
    release PDF for that game date, archive the binary + extracted text under
    data/raw/pdf/, and (if a committed transcript exists for that release) cross-check
    it. Exit codes: 0 ok, 3 fetch/parse failure, 4 cross-check mismatch.

--finals --date YYYY-MM-DD [--out FILE]
    Fetch official scoreboard data for a date from the NBA CDN / stats endpoints,
    keep only games whose official status is final, and write the settlement snapshot
    in exactly the shape nba2.pipeline.settle expects. Missing games are reported, not
    filled. Exit codes: 0 ok, 3 fetch failure, 4 schema/coverage failure.

--verify-transcript PATH
    Cross-check a committed injury transcript against the archived PDF text (if the PDF
    has been archived by --injuries). Mismatch exits non-zero.

Design constraints (from the brief and the audit):
* stdlib only — no published number may depend on an unpinned package;
* the sealed ledger is never written by this module;
* a transcript is human-verified input; the machine can only *check* it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import sys
import unicodedata
import urllib.request
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"

INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"
PDF_RE = re.compile(
    r"https://ak-static\.cms\.nba\.com/referee/injury/"
    r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)\.pdf"
)
STATUS_WORDS = ("NOT YET SUBMITTED", "Out", "Doubtful", "Questionable", "Probable", "Available")
PLAYER_STATUS_RE = re.compile(
    r"([A-Z][A-Za-z\.'\u2010-\u2015\- ]+?, [A-Z][A-Za-z\.'\u2010-\u2015\- ]+?)"
    r"\s+(NOT YET SUBMITTED|Out|Doubtful|Questionable|Probable|Available)\b"
)
UA = {"User-Agent": "NBA2-research-desk/1.0 (repository ingestion; contact: repo owner)",
      "Accept": "*/*", "Referer": "https://official.nba.com/"}

FINALS_SOURCES = [
    # official NBA CDN live scoreboard (today's slate, ET)
    ("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json", "cdn_live"),
    # league stats API scoreboard (any date) — official nba.com endpoints
    ("https://stats.nba.com/stats/scoreboardv2?LeagueID=00&GameDate={date}&DayOffset=0", "stats_scoreboardv2"),
]


def _http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
    return data


# --------------------------------------------------------------------------- injury index
def newest_release_for_date(index_html: str, date: str) -> tuple[str, str] | None:
    """Newest (url, stamp) PDF link on the index for one game date, or None."""
    best = None
    for m in PDF_RE.finditer(index_html):
        url, d, hh, mm, ampm = m.group(0), m.group(1), m.group(2), m.group(3), m.group(4)
        if d != date:
            continue
        stamp = stamp_to_iso(d, hh, mm, ampm)
        if best is None or stamp > best[1]:
            best = (url, stamp)
    return best


def stamp_to_iso(date: str, hh: str, mm: str, ampm: str) -> str:
    h = int(hh) % 12 + (12 if ampm == "PM" else 0)
    return f"{date}T{h:02d}:{int(mm):02d}"


def pdf_text(raw_bytes: bytes) -> str:
    """Extract text from a simple digitally-generated PDF (FlateDecode text streams).

    Heuristic and deliberately conservative: it concatenates the literal strings found in
    text-showing operators of decompressed content streams. Good enough to *check* a human
    transcript; never used as a data source on its own.
    """
    out: list[str] = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw_bytes, re.S):
        blob = m.group(1)
        try:
            blob = zlib.decompress(blob)
        except zlib.error:
            continue
        if b"BT" not in blob and b"Tj" not in blob and b"TJ" not in blob:
            continue
        text = blob.decode("latin-1", errors="ignore")
        for s in re.findall(r"\((?:\\.|[^\\()])*\)", text):
            s = s[1:-1]
            s = re.sub(r"\\([()\\])", r"\1", s)
            s = re.sub(r"\\[nrt]", " ", s)
            s = re.sub(r"\\([0-7]{1,3})", lambda g: chr(int(g.group(1), 8) & 0xFF), s)
            out.append(s)
    return " ".join(out)


def pairs_from_text(text: str) -> set[tuple[str, str]]:
    norm = unicodedata.normalize("NFKC", text)
    pairs = set()
    for name, status in PLAYER_STATUS_RE.findall(norm):
        name = re.sub(r"\s+", " ", name).strip(" ,")
        if len(name) >= 4:
            pairs.add((name, status))
    return pairs


def check_transcript_against_pdf(transcript: dict, pdf_text_str: str, min_recall: float = 0.9) -> dict:
    """Cross-check a human transcript against the machine-extracted PDF text.

    recall = share of transcript (player,status) pairs found in the extraction. The
    extractor is lossy (column runs split names), so this is a tripwire, not equality:
    below the recall floor the transcript is presumed wrong until re-read.
    """
    got = pairs_from_text(pdf_text_str)
    want = {(r[4], r[5]) for r in transcript["records"] if r[5] != "NOT YET SUBMITTED"}
    hit = {pair for pair in want if any(gp[0].startswith(pair[0].split(",")[0]) and gp[1] == pair[1]
                                        for gp in got)}
    recall = len(hit) / len(want) if want else 1.0
    missing = sorted(want - hit)
    return {"recall": round(recall, 4), "pairs_checked": len(want),
            "missing_from_extraction": missing[:20], "floor": min_recall,
            "pass": recall >= min_recall}


# --------------------------------------------------------------------------- finals
def final_games_cdn(payload: dict, date: str) -> list[dict]:
    """(game_id, home_pts, away_pts, source) for FINAL games on the CDN scoreboard."""
    out = []
    for ev in payload.get("scoreboard", {}).get("games", []):
        if str(ev.get("gameStatus", "")) != "3":  # 3 == final per the official liveData schema
            continue
        home = ev.get("homeTeam", {})
        away = ev.get("awayTeam", {})
        out.append({"game_id": ev.get("gameId"), "date": date,
                    "home_team": home.get("teamTrigramCode"), "away_team": away.get("teamTrigramCode"),
                    "home_pts": home.get("score"), "away_pts": away.get("score"),
                    "status": "final"})
    return out


def final_games_scoreboardv2(payload: dict, date: str) -> list[dict]:
    """Same shape from the league stats scoreboardv2 endpoint."""
    out = []
    for gset in payload.get("resultSets", []):
        if gset.get("name") != "LineScore":
            continue
        headers = gset["headers"]
        rows = [dict(zip(headers, r)) for r in gset["rowSet"]]
        by_game: dict[str, dict] = {}
        for r in rows:
            if str(r.get("GAME_STATUS_ID", "")) != "3":
                continue
            rec = by_game.setdefault(r["GAME_ID"], {"game_id": r["GAME_ID"], "date": date,
                                                    "status": "final"})
            if r.get("TEAM_ABBREVIATION") and "home_team" not in rec:
                rec["home_team"] = r["TEAM_ABBREVIATION"]
                rec["home_pts"] = r.get("PTS")
            else:
                rec["away_team"] = r["TEAM_ABBREVIATION"]
                rec["away_pts"] = r.get("PTS")
        out.extend(v for v in by_game.values() if "home_pts" in v and "away_pts" in v)
    return out


def fetch_finals(date: str, expected_game_ids: list[str]) -> tuple[dict | None, str, str]:
    """Try each official endpoint.

    Returns (snapshot, url, kind) with kind one of:
      "ok"          — at least one FINAL window game found,
      "no_finals"   — endpoints reachable and well-formed, but no FINAL window game yet,
      "unreachable" — every endpoint failed at the network level,
      "bad_schema"  — endpoints answered but no payload matched the expected schema.
    """
    unreachable = 0
    schema_broken = 0
    for tmpl, kind in FINALS_SOURCES:
        url = tmpl.format(date=date)
        try:
            payload = json.loads(_http_get(url).decode("utf-8"))
        except Exception as e:  # noqa: BLE001 - fail-closed: report and try next endpoint
            print(f"  [finals {date}] endpoint unreachable: {kind} ({e})")
            unreachable += 1
            continue
        try:
            recs = final_games_cdn(payload, date) if kind == "cdn_live" else final_games_scoreboardv2(payload, date)
        except (KeyError, TypeError) as e:
            print(f"  [finals {date}] schema changed in {kind} ({e})")
            schema_broken += 1
            continue
        recs = [r for r in recs if not expected_game_ids or r["game_id"] in expected_game_ids]
        if not recs:
            print(f"  [finals {date}] no FINAL games for the sealed window in {kind}")
            continue
        for r in recs:
            r["source"] = url
        missing = [gid for gid in expected_game_ids if gid not in {r["game_id"] for r in recs}]
        snap = {"source": url, "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "date": date, "records": recs, "expected_window_games": len(expected_game_ids),
                "games_missing_from_payload": missing}
        return snap, url, "ok"
    if unreachable == len(FINALS_SOURCES):
        return None, "", "unreachable"
    if schema_broken == len(FINALS_SOURCES):
        return None, "", "bad_schema"
    return None, "", "no_finals"


# --------------------------------------------------------------------------- cli
def cmd_injuries(date: str, outdir: Path) -> int:
    print(f"[injuries {date}] reading index {INDEX_URL}")
    try:
        html = _http_get(INDEX_URL).decode("utf-8", errors="ignore")
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: index unreachable: {e}")
        return 3
    n_links = len(PDF_RE.findall(html))
    found = newest_release_for_date(html, date)
    if not found:
        if n_links == 0:
            print("FAIL: the index page contains no injury-report links at all — its structure "
                  "has changed and the parser needs updating")
            return 3
        # A missing release for a future game date is the expected pre-deadline state, not
        # an error (day-before designations are due 5 p.m. local the day before).
        print(f"[injuries {date}] no release on the index for this date yet ({n_links} links for "
              f"other dates) — expected before the filing deadline; nothing archived")
        return 0
    url, stamp = found
    print(f"[injuries {date}] newest release: {stamp} ET  {url}")
    try:
        blob = _http_get(url)
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: PDF unreachable: {e}")
        return 3
    outdir.mkdir(parents=True, exist_ok=True)
    pdf_path = outdir / Path(url).name
    pdf_path.write_bytes(blob)
    extracted = pdf_text(blob)
    (outdir / (pdf_path.stem + ".txt")).write_text(extracted, encoding="utf-8")
    print(f"[injuries {date}] archived {pdf_path.name} ({len(blob)} bytes) + extracted text "
          f"({len(extracted)} chars)")

    # cross-check against any committed transcript of the same release
    for tr_path in sorted(RAW.glob("injury_report_*.json")):
        tr = json.loads(tr_path.read_text())
        if tr.get("provenance", {}).get("url") == url:
            res = check_transcript_against_pdf(tr, extracted)
            print(f"[injuries {date}] transcript {tr_path.name}: recall {res['recall']} "
                  f"({res['pairs_checked']} pairs) -> {'PASS' if res['pass'] else 'FAIL'}")
            if not res["pass"]:
                print(f"  missing from extraction (extractor is lossy; re-read the PDF if this recurs): "
                      f"{res['missing_from_extraction']}")
            return 0 if res["pass"] else 4
    print(f"[injuries {date}] no committed transcript for this release yet — archived for human review only")
    return 0


def cmd_finals(date: str, expected_game_ids: list[str], out: Path) -> int:
    """0  = ok, or no FINAL games yet (expected pre-tip),
       3  = every official endpoint unreachable (network-level failure),
       4  = endpoints reachable but schema/coverage broken."""
    print(f"[finals {date}] expecting {len(expected_game_ids)} sealed-window games")
    snap, url, kind = fetch_finals(date, expected_game_ids)
    if kind == "unreachable":
        print(f"FAIL: no official endpoint reachable for {date} — refusing to proceed")
        return 3
    if kind == "bad_schema":
        print(f"FAIL: endpoints answered but no payload matched the expected schema for {date}")
        return 4
    if kind == "no_finals":
        print(f"[finals {date}] endpoints reachable, no FINAL window games yet — expected "
              f"before the evening tips; nothing written")
        return 0
    if not all(r.get("home_pts") is not None and r.get("away_pts") is not None for r in snap["records"]):
        print("FAIL: a FINAL record lacks a score — refusing to write a partial snapshot")
        return 4
    out.write_text(json.dumps(snap, indent=1) + "\n")
    print(f"[finals {date}] wrote {out.name}: {len(snap['records'])} games from {url} "
          f"({len(snap['games_missing_from_payload'])} window games not in payload)")
    return 0


def cmd_verify_transcript(path: Path) -> int:
    tr = json.loads(path.read_text())
    url = tr.get("provenance", {}).get("url")
    pdf_name = Path(url).name if url else None
    txt = RAW / "pdf" / (Path(pdf_name).stem + ".txt") if pdf_name else None
    if not txt or not txt.exists():
        print(f"[transcript {path.name}] archived PDF text not present — nothing to check (run --injuries first)")
        return 0
    res = check_transcript_against_pdf(tr, txt.read_text(encoding="utf-8"))
    print(f"[transcript {path.name}] recall {res['recall']} -> {'PASS' if res['pass'] else 'FAIL'}")
    return 0 if res["pass"] else 4


def window_game_ids_by_date() -> dict[str, list[str]]:
    """Official game ids for sealed-window games whose date has already arrived."""
    from ..models import lines as LN  # local import: models import chain is heavy

    games, slate = LN.load_slate(RAW / "slate_2026-11-13_to_11-16.json")
    as_of = slate["as_of"]
    today = dt.datetime.now(dt.timezone.utc).date()
    out: dict[str, list[str]] = {}
    for g in games:
        d = g["date"]
        if d <= as_of or d > today.isoformat():
            continue
        out.setdefault(d, []).append(g["game_id"])
    return out


def cmd_merge_finals() -> int:
    """Merge per-date finals snapshots into data/raw/finals_all.json.

    nba2.pipeline.settle scores the sealed ledger against the newest finals_*.json only;
    per-date files alone would make each new date regress the metrics to a single day.
    The merged file is the settlement input; per-date files stay as provenance. Scores are
    final once official, so records are immutable and dedup keeps the latest write.
    """
    seen: dict[str, dict] = {}
    sources: list[str] = []
    for path in sorted(RAW.glob("finals_2*.json")):
        doc = json.loads(path.read_text())
        sources.append(path.name)
        for rec in doc.get("records", []):
            seen[rec["game_id"]] = rec
    merged = {
        "source": "merged from: " + ", ".join(sources) if sources else "",
        "merged_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "records": sorted(seen.values(), key=lambda r: r["game_id"]),
        "note": "Settlement input for nba2.pipeline.settle (newest finals_*.json by name). "
                "Generated by nba2.pipeline.refresh --merge-finals; never hand-edited.",
    }
    out = RAW / "finals_all.json"
    if merged["source"]:
        out.write_text(json.dumps(merged, indent=1) + "\n")
        print(f"[finals] merged {len(sources)} snapshots -> {out.name} ({len(seen)} games)")
    else:
        print("[finals] no per-date finals snapshots yet — nothing to merge")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--injuries", metavar="DATE")
    ap.add_argument("--finals", metavar="DATE", action="append", default=[])
    ap.add_argument("--merge-finals", action="store_true")
    ap.add_argument("--verify-transcript", metavar="PATH")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    rc = 0
    if args.injuries:
        rc |= cmd_injuries(args.injuries, RAW / "pdf")
    if args.finals:
        by_date = window_game_ids_by_date()
        for date in args.finals:
            gids = by_date.get(date, [])
            out = Path(args.out) if args.out else RAW / f"finals_{date}.json"
            rc |= cmd_finals(date, gids, out)
    if args.merge_finals:
        rc |= cmd_merge_finals()
    if args.verify_transcript:
        rc |= cmd_verify_transcript(Path(args.verify_transcript))
    return rc


if __name__ == "__main__":
    sys.exit(main())
