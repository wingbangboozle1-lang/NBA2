#!/usr/bin/env python3
"""Fail-closed ingestion of the official NBA inputs this repository is built from.

Two modes, deliberately separated:

    --probe      Ask each official endpoint whether it answers at all, and record the answer:
                 HTTP status, bytes, sha256, elapsed. Nothing is parsed, nothing is written into
                 the repo. The point is evidence, because the current data model says
                 "unreachable from the build environment" — and "the build environment" has so far
                 only ever meant this sandbox. A probe run on a GitHub-hosted runner tells us
                 whether the blocker is our sandbox or the league's CDN. That single fact decides
                 whether daily automation is worth building at all.

    --capture    Fetch, validate, and store dated snapshots under --out. It is written to fail
                 closed: an endpoint that does not answer, or answers with something whose shape
                 we cannot verify, produces NO file. A partial or guessed snapshot is worse than
                 no snapshot, because the site's whole contract is "a value is only published if
                 it was read from a source".

This tool never edits the repository's committed data and never decides what the site publishes.
Its output is either a dated snapshot with full provenance, or a non-zero exit and a reason.

Network: stdlib urllib only, one request per endpoint per run, an identifying User-Agent, and no
retry storms. Whatever runs this is responsible for respecting the publisher's terms of use; the
call pattern here is a handful of requests a day for the slate and the injury report, which is the
same thing a person clicking the schedule page does.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = "NBA2-research-bot/1.0 (github.com/wingbangboozle1-lang/NBA2; personal research; contact via repo)"
TIMEOUT = 20

# key -> (url, class, what a successful answer must contain to be usable by the pipeline)
ENDPOINTS: dict[str, dict] = {
    "scoreboard": {
        "url": "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
        "kind": "json",
        "official": True,
        "must_have": ["scoreboard", "games"],
        "note": "NBA's own CDN. One document covering the day's games: gameId, team tricode, period, "
                "gameStatus, arena. This is the only official endpoint in this repo's source register "
                "that has never been reachable from anywhere we have tried.",
    },
    "standings": {
        "url": "https://stats.nba.com/stats/leaguestandingsv3?Season=2026-27&LeagueID=00&PerMode=Totals",
        "kind": "json",
        "official": True,
        "must_have": ["resultSet"],
        "note": "The endpoint named in nba2/provenance.py as BLOCKED. Probed so the register can say "
                "what a runner sees, not only what the sandbox saw.",
    },
    "injury_pdf_today": {
        "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_{date}_01_00PM.pdf",
        "kind": "pdf",
        "official": True,
        "must_have": [],
        "note": "The official injury report, on the 13:00 ET cadence. The URL pattern is the one this "
                "repository already cites for 2026-11-13. A PDF is archived and hashed, not parsed: "
                "transcribing it is a separate, reviewable step.",
    },
    "schedule_page": {
        "url": "https://www.nba.com/schedule",
        "kind": "html",
        "official": True,
        "must_have": [],
        "note": "Human-readable schedule. Client-rendered, so a 200 here does not by itself yield game "
                "rows; it is probed because the source register cites it for the slate.",
    },
}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def fetch(url: str) -> tuple[int | None, bytes, str, float]:
    """(status, body, error, elapsed_seconds). Never raises."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read(), "", round(time.time() - t0, 2)
    except urllib.error.HTTPError as e:
        try:
            body = e.read()[:4096]
        except Exception:
            body = b""
        return e.code, body, f"HTTP {e.code} {e.reason}", round(time.time() - t0, 2)
    except Exception as e:  # DNS, TLS, timeout, connection reset
        return None, b"", f"{type(e).__name__}: {e}", round(time.time() - t0, 2)


def path_for(key: str, url: str) -> str:
    return url.replace("{date}", _today()) if "{date}" in url else url


def probe_all() -> dict:
    import platform
    out = {"tool": "tools/ingest_official.py --probe", "run_at_utc": _now(),
           "runner": {"python": sys.version.split()[0], "platform": platform.platform(),
                      "runner_environment": (str(__import__("os").environ.get("CI", "")) or "not a CI runner"),
                      "github_run_id": __import__("os").environ.get("GITHUB_RUN_ID"),
                      "github_runner_name": __import__("os").environ.get("RUNNER_NAME"),
                      "public_ip_geo": "not collected on purpose: this probe answers one question, "
                                      "whether the endpoint answers, and nothing else"},
           "endpoints": {}}
    for key, spec in ENDPOINTS.items():
        url = path_for(key, spec["url"])
        status, body, err, elapsed = fetch(url)
        rec = {"url": url, "official": spec["official"], "class": "official" if spec["official"] else "other",
               "http_status": status, "bytes": len(body), "elapsed_s": elapsed,
               "sha256": hashlib.sha256(body).hexdigest() if body else None,
               "error": err or None}
        if spec["kind"] == "json" and body:
            try:
                doc = json.loads(body.decode("utf-8", "replace"))
                rec["parses_as_json"] = True
                rec["missing_keys"] = [k for k in spec["must_have"] if not _has_path(doc, k)]
                if key == "scoreboard" and _has_path(doc, "scoreboard.games"):
                    games = doc["scoreboard"].get("games") or []
                    rec["games_returned"] = len(games)
                    rec["game_dates"] = sorted({g.get("gameDate", "") for g in games})
            except Exception as e:
                rec["parses_as_json"] = False
                rec["json_error"] = f"{type(e).__name__}: {e}"[:160]
        elif spec["kind"] == "pdf" and body:
            rec["is_pdf"] = body[:5] == b"%PDF-"
        out["endpoints"][key] = rec
    reachable = [k for k, v in out["endpoints"].items() if v["http_status"] == 200]
    out["summary"] = {"endpoints_probed": len(out["endpoints"]), "reachable": reachable,
                      "unreachable": [k for k in out["endpoints"] if k not in reachable]}
    return out


def _has_path(doc, dotted: str) -> bool:
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and all(isinstance(x, dict) and part in x for x in cur):
            cur = [x[part] for x in cur]
        else:
            return False
    return True


def validate_scoreboard(doc: dict) -> tuple[list[dict], list[str]]:
    """Turn the CDN scoreboard document into slate rows, or refuse.

    Only fields the document actually carries are extracted. Anything we cannot read from it is
    left absent, not defaulted.
    """
    problems: list[str] = []
    rows: list[dict] = []
    sb = doc.get("scoreboard") or {}
    games = sb.get("games") or []
    if not games:
        problems.append("no games array")
        return [], problems
    for g in games:
        gid = str(g.get("gameId") or "")
        if not re.fullmatch(r"002\d{7}", gid):
            problems.append(f"gameId {gid!r} is not an official 2026-27 game id")
            continue
        teams = {t.get("teamTricode"): t for t in (g.get("teams") or []) if t.get("teamTricode")}
        if len(teams) != 2:
            problems.append(f"{gid}: expected 2 tricodes, got {sorted(teams)}")
            continue
        away = next((t for t in (g.get("teams") or []) if t.get("isAway")), None)
        home = next((t for t in (g.get("teams") or []) if not t.get("isAway")), None)
        if not (away and home):
            problems.append(f"{gid}: the document does not mark which side is home; refusing to guess")
            continue
        rows.append({
            "game_id": gid,
            "date": (g.get("gameDate") or "")[:10],
            "time_et": _et_hhmm(g.get("gameTimeUTC") or g.get("etDate") or ""),
            "away": away.get("teamTricode"),
            "home": home.get("teamTricode"),
            "arena": (g.get("arena") or {}).get("fullName"),
            "game_status": g.get("gameStatus"),
            "period": g.get("period"),
        })
    dates = sorted({r["date"] for r in rows if r["date"]})
    if dates and len(dates) > 2:
        problems.append(f"one scoreboard document should not span {len(dates)} dates: {dates}")
    return rows, problems


def _et_hhmm(raw: str) -> str | None:
    """2026-11-14T00:00:00Z -> '19:00' (ET), and '2026-11-13 19:00:00' -> '19:00'.

    ET is UTC-5 in November and UTC-4 March–October. The offset is applied explicitly rather than
    guessed from the environment's timezone.
    """
    if not raw:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})", raw)
    if not m:
        return None
    y, mo, d, h, mi = (int(x) for x in m.groups())
    when = dt.datetime(y, mo, d, h, mi, tzinfo=dt.timezone.utc)
    month = when.month
    offset = 4 if 3 <= month <= 10 else 5   # US Eastern DST rule, applied by month of the UTC stamp
    et = when - dt.timedelta(hours=offset)
    return et.strftime("%H:%M")


def capture(out_dir: Path) -> int:
    """Fetch the endpoints we can validate and write dated snapshots + a manifest. Fail closed."""
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d_%H%MZ")
    target = out_dir / stamp
    target.mkdir(parents=True, exist_ok=True)
    manifest = {"tool": "tools/ingest_official.py --capture", "run_at_utc": _now(),
                "snapshot_dir": str(target), "artefacts": [], "refused": []}
    wrote_any = False

    for key, spec in ENDPOINTS.items():
        url = path_for(key, spec["url"])
        status, body, err, elapsed = fetch(url)
        base = {"endpoint": key, "url": url, "http_status": status, "bytes": len(body),
                "elapsed_s": elapsed, "retrieved_at_utc": _now(),
                "sha256": hashlib.sha256(body).hexdigest() if body else None,
                "publisher": "NBA (official)" if spec["official"] else "other",
                "error": err or None}
        if status != 200 or not body:
            manifest["refused"].append({**base, "reason": f"not retrieved ({status or err}); "
                                                          "refusing to write a snapshot from an unread source"})
            continue
        if spec["kind"] == "json":
            try:
                doc = json.loads(body.decode("utf-8"))
            except Exception as e:
                manifest["refused"].append({**base, "reason": f"body is not JSON ({type(e).__name__})"})
                continue
            if not all(_has_path(doc, k) for k in spec["must_have"]):
                manifest["refused"].append({**base, "reason": f"document lacks {spec['must_have']}"})
                continue
            if key == "scoreboard":
                rows, problems = validate_scoreboard(doc)
                if problems or not rows:
                    manifest["refused"].append({**base, "reason": "validation failed", "problems": problems[:8]})
                    continue
                p = target / f"slate_official_{base['retrieved_at_utc'][:10]}.json"
                p.write_text(json.dumps({
                    "dataset": "official_slate_ingested", "as_of": base["retrieved_at_utc"][:10],
                    "retrieved_at_utc": base["retrieved_at_utc"],
                    "provenance": {"publisher": "NBA.com CDN (official)", "url": url,
                                   "http_status": 200, "sha256_of_response_body": base["sha256"],
                                   "retrieved_by": "tools/ingest_official.py --capture"},
                    "columns": ["date", "time_et", "away", "home", "game_id", "arena", "game_status", "period"],
                    "records": [[r["date"], r["time_et"], r["away"], r["home"], r["game_id"],
                                 r["arena"], r["game_status"], r["period"]] for r in rows],
                }, indent=1) + "\n")
                manifest["artefacts"].append({**base, "path": str(p), "rows": len(rows)})
                wrote_any = True
            else:
                p = target / f"{key}_{base['retrieved_at_utc'][:10]}.raw.json"
                p.write_bytes(body)
                manifest["artefacts"].append({**base, "path": str(p),
                                              "note": "stored verbatim and hashed; not transcribed by this tool"})
                wrote_any = True
        elif spec["kind"] == "pdf":
            p = target / f"injury_report_{base['retrieved_at_utc'][:10]}.pdf"
            if body[:5] != b"%PDF-":
                manifest["refused"].append({**base, "reason": "response is not a PDF"})
                continue
            p.write_bytes(body)
            manifest["artefacts"].append({**base, "path": str(p),
                                          "note": "the official document, archived byte-for-byte. "
                                                  "Transcription into rows stays a separate, reviewable step."})
            wrote_any = True
        else:
            manifest["refused"].append({**base, "reason": "kind not supported for capture "
                                                          "(client-rendered HTML needs the JSON API, not this)"})

    (target / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({"artefacts": len(manifest["artefacts"]), "refused": len(manifest["refused"]),
                      "manifest": str(target / "manifest.json")}, indent=1))
    return 0 if wrote_any else 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="record what each official endpoint returns")
    ap.add_argument("--capture", action="store_true", help="fetch, validate, and write dated snapshots")
    ap.add_argument("--out", default="ingest-out", help="where --capture writes (default ./ingest-out)")
    ap.add_argument("--json", default="", help="also write the probe report here")
    ap.add_argument("--strict", action="store_true", help="exit non-zero unless every endpoint answers 200")
    args = ap.parse_args()
    if args.capture:
        return capture(Path(args.out))
    report = probe_all()
    print(json.dumps(report, indent=1))
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=1) + "\n")
    if args.strict and report["summary"]["unreachable"]:
        print("refused: unreachable endpoint(s) " + ", ".join(report["summary"]["unreachable"]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
