"""Read-only official-source reachability probe (session arena/d09f8d1e-nba2, F-043).

Requests each official URL the nightly ingest depends on and records, per URL and
per User-Agent: HTTP status, byte length, sha256, content type, elapsed time and a
short content sniff. Full response bodies are written to the output directory (up
to CAP bytes each) so a schema question can be answered from the captured document
rather than from memory.

This script NEVER writes to the repository's data/ tree, never commits, and never
invents a value: it is evidence collection for the F-043 diagnosis ("the exact
failure cause is unverified").

Usage:
    python3 tools/probe_official.py [--out DIR] [--full-for LABEL ...]

Exit code 0 always (a failed fetch is a result, not an error); the report is the
output. Run it from a GitHub-hosted runner for egress that the build sandbox does
not have — see .github/workflows/probe.yml and the failure-time job in
.github/workflows/refresh.yml.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

PIPELINE_UA = ("NBA2-research-desk/1.0 (repository ingestion; contact: repo owner)")
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

# First sealed-window game id (data/raw/ledger/sealed-2026-11-14.json, NOP vs DEN
# 2026-11-14) — the boxscore/play-by-play endpoints are keyed by game id.
SEALED_WINDOW_GAME_ID = "0022600231"

URLS = [
    ("injury_index", "https://official.nba.com/nba-injury-report-2026-27-season/"),
    ("cdn_todays_scoreboard",
     "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"),
    ("stats_scoreboardv2_1114",
     "https://stats.nba.com/stats/scoreboardv2?LeagueID=00&GameDate=2026-11-14&DayOffset=0"),
    ("stats_scoreboardv2_1113",
     "https://stats.nba.com/stats/scoreboardv2?LeagueID=00&GameDate=2026-11-13&DayOffset=0"),
    ("cdn_game_boxscore",
     f"https://cdn.nba.com/static/json/liveData/game/{SEALED_WINDOW_GAME_ID}_boxscore.json"),
    ("cdn_game_pbp",
     f"https://cdn.nba.com/static/json/liveData/playbyplay/{SEALED_WINDOW_GAME_ID}_full.json"),
    ("nba_com_game_page", "https://www.nba.com/game/nyk-vs-ind-0022600034"),
    ("stats_team_traditional",
     "https://stats.nba.com/stats/teamyearyearstatsmeasure?LeagueID=00&Season=2026-27"
     "&SeasonType=Regular%20Season&TeamID=1610612743&MeasureType=Base&PerMode=PerGame"),
    ("stats_league_leaders",
     "https://stats.nba.com/stats/leagueleaders?LeagueID=00&Season=2026-27"
     "&SeasonType=Regular%20Season&PerMode=PerGame"),
]

CAP = 2_000_000  # bytes of any single body kept on disk


def fetch(url: str, ua: str, timeout: int = 30) -> tuple[dict, bytes]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": ua,
            "Accept": "*/*",
            "Referer": "https://www.nba.com/",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(CAP)
            return (
                {
                    "status": resp.status,
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "ctype": resp.headers.get("Content-Type", ""),
                    "sniff": body[:200].decode("utf-8", "replace").replace("\n", " "),
                    "elapsed_s": round(time.time() - t0, 2),
                    "error": "",
                },
                body,
            )
    except urllib.error.HTTPError as e:
        try:
            body = e.read(CAP)
        except Exception:  # noqa: BLE001
            body = b""
        return (
            {
                "status": e.code,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest() if body else "",
                "ctype": (e.headers.get("Content-Type", "") if e.headers else ""),
                "sniff": body[:200].decode("utf-8", "replace").replace("\n", " ") if body else "",
                "elapsed_s": round(time.time() - t0, 2),
                "error": f"HTTPError {e.code}",
            },
            body,
        )
    except Exception as e:  # noqa: BLE001
        return (
            {
                "status": None,
                "bytes": 0,
                "sha256": "",
                "ctype": "",
                "sniff": "",
                "elapsed_s": round(time.time() - t0, 2),
                "error": f"{type(e).__name__}: {e}",
            },
            b"",
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="probe_out", help="directory for report + bodies")
    ap.add_argument("--full-for", action="append", default=[], metavar="LABEL",
                    help="also keep the full body of this label (repeatable); "
                         "default: keep bodies for every 2xx JSON response")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "probed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "runner": "see the workflow run this was invoked from",
        "note": "Read-only evidence for F-043. sha256 is over the full body as "
                "received (bodies capped at %d bytes)." % CAP,
        "results": [],
    }
    for label, url in URLS:
        for ua_name, ua in (("pipeline_ua", PIPELINE_UA), ("browser_ua", BROWSER_UA)):
            res, body = fetch(url, ua)
            row = {"label": label, "url": url, "ua": ua_name, **res}
            keep = (
                label in args.full_for
                or (res["status"] == 200 and "json" in (res["ctype"] or "")
                    and not args.full_for)
            )
            if keep and body:
                fn = f"{label}__{ua_name}.body"
                (out / fn).write_bytes(body)
                row["body_file"] = fn
            report["results"].append(row)
            print(
                f"[{res['status']}] {label:24s} {ua_name:11s} "
                f"bytes={res['bytes']:<8} sha256={res['sha256'][:16]:<16} "
                f"{res['elapsed_s']}s {res['error']}"
            )
            if res["sniff"]:
                print(f"        sniff: {res['sniff'][:160]}")
            # Also emit an annotation: this sandbox cannot download Actions console
            # logs or artifacts (the results blob host is outside its egress
            # allowlist — the EOF the F-043 audit hit), but annotations ARE readable
            # via api.github.com. One line per probe keeps the evidence fetchable.
            print(
                f"::notice title=probe {label} ({ua_name})::"
                f"status={res['status']} bytes={res['bytes']} "
                f"sha256={res['sha256'][:16]} {res['elapsed_s']}s "
                f"ctype={res['ctype'][:60]} err={res['error'][:120]} "
                f"sniff={res['sniff'][:120]}"
            )

    (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(f"wrote {out / 'report.json'} ({len(report['results'])} probes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
