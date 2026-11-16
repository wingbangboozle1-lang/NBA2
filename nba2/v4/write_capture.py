"""Write the frozen official snapshot for the 2026-11-16 anchor into ``data/raw/refresh_*``.

Two directories, on purpose:

``data/raw/refresh_2026-11-16/``
    What this session read *today*: the 11/16 standings, the three team-stat pages, the
    11/16 - 11/19 schedule, and the 11/16 09:15 AM ET injury release.

``data/raw/refresh_2026-11-15/``
    The 11/15 official finals and their gamebooks. The finals happened on 11/15 and were
    *read* on 11/16; the capture is filed under the game date so the settlement ledger and
    the result feed share one key, and the retrieval stamp says 11/16.

Everything written here is either an official value read this session or an explicitly
labelled gap. ``write()`` is deterministic: running it twice produces byte-identical files,
which is what lets CI diff a rebuild against the committed capture.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import capture as C

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"


def _dump(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write() -> list[str]:
    problems = C.selftest()
    if problems:
        raise SystemExit("capture selftest failed, refusing to write:\n  " + "\n  ".join(problems))

    today = RAW / "refresh_2026-11-16"
    prior = RAW / "refresh_2026-11-15"
    written = []

    stamp = {"retrieved_utc": C.RETRIEVED_UTC, "retrieved_et": C.RETRIEVED_ET,
             "session": C.SESSION, "method": C.METHOD}

    # ------------------------------------------------------------------ today: standings
    st = C.standings()
    _dump(today / "standings_2026-11-16.json", {
        "schema": "nba2.standings-official.v3",
        "as_of": "2026-11-16",
        **stamp,
        "source": C.SOURCE_PAGES["standings"],
        "rows": st,
        "checks": {"n_clubs": len(st),
                   "wins": sum(r["w"] for r in st),
                   "losses": sum(r["l"] for r in st)},
    })
    written.append(str((today / "standings_2026-11-16.json").relative_to(ROOT)))

    # ------------------------------------------------------- today: three team-stat pages
    adv, opp, tra = C.advanced(), C.opponent(), C.traditional()
    _dump(today / "team_stats_2026-11-16.json", {
        "schema": "nba2.team-stats-3page.v2",
        "as_of": "2026-11-16",
        **stamp,
        "pages": {
            "advanced": {"source": C.SOURCE_PAGES["team_adv"], "rows": adv},
            "opponent": {"source": C.SOURCE_PAGES["team_opp"], "rows": opp},
            "traditional": {"source": C.SOURCE_PAGES["team_trad"], "rows": tra},
        },
        "re_cut": {
            "note": ("The v3 model re-cut its inputs from a 2026-11-15 snapshot. This file is "
                     "the 2026-11-16 re-read of the same three official pages; v4 recomputes "
                     "every model input from it. No value is carried across from v3."),
            "advanced_rows": len(adv), "opponent_rows": len(opp), "traditional_rows": len(tra),
        },
        "checks": C.crosschecks(),
    })
    written.append(str((today / "team_stats_2026-11-16.json").relative_to(ROOT)))

    # ---------------------------------------------------------------- today: the slate
    sl = C.slate()
    _dump(today / "slate_2026-11-16_to_11-19.json", {
        "schema": "nba2.slate.v3",
        "window": {"start": C.EXTENDED_WINDOW[0], "end": C.EXTENDED_WINDOW[1],
                   "n_games": len(sl),
                   "rule": "T+0 .. T+3 from the 11/16 anchor; the brief caps published picks "
                           "at 3 days ahead, so 11/19 is the outer edge and 11/16-11/18 is "
                           "the published window"},
        **stamp,
        "source": C.SOURCE_PAGES["schedule"],
        "games": sl,
        "by_date": {d: sum(1 for g in sl if g["date"] == d)
                    for d in sorted({g["date"] for g in sl})},
    })
    written.append(str((today / "slate_2026-11-16_to_11-19.json").relative_to(ROOT)))

    # ------------------------------------------------------------ today: injury releases
    # A release may be declared identical to an earlier one; none currently is.
    # The declaration is materialised into the written file as an explicit field, never
    # silently expanded, so the artefact says exactly what was done.
    def _materialise(rel):
        if "identical_to" not in rel:
            return rel["rows"], None
        idx, stamp = rel["identical_to"]
        return C.INJURY_RELEASES[idx]["rows"], {
            "identical_to_stamp_et": stamp,
            "identical_to_url": C.INJURY_RELEASES[idx]["url"],
            "basis": rel["basis"],
            "flagged": "F-V4-09",
        }

    for rel in C.INJURY_RELEASES:
        rows, replication = _materialise(rel)
        doc = {
            "schema": "nba2.injury-transcript.v3",
            "report_stamp_et": rel["stamp_et"],
            "revision_time_et": rel["stamp_et"],
            "retrieved_at_utc": rel["retrieved_utc"],
            "index_checked_utc": rel["index_checked_utc"],
            "retrieval_method": rel["method"],
            "provenance": {
                "publisher": "NBA Official Injury Report (official)",
                "url": rel["url"],
                "index_url": C.SOURCE_PAGES["injury_index"]["url"],
                "note": ("Rows transcribed from the release's own text. Where the text "
                         "extraction lost a column, the cell is blank and the reason is in "
                         "the row's note - never reconstructed. See F-V4-05/06/07."),
            },
            "columns": ["date", "time_et", "matchup", "team", "player", "status",
                        "reason", "note"],
            "records": rows,
            "layout_notes": [{"id": a, "finding": b}
                             for a, b in C.INJURY_RELEASES[0]["layout_notes"]],
            "content_sha256": _sha(json.dumps(rows, ensure_ascii=False, sort_keys=True)),
            "replication": replication,
            "binary_stored": False,
            "binary_stored_reason": C.UNREAD["injury_binary_pdf"][1],
        }
        name = (rel["stamp_et"].replace(":", "").replace(" ", "_").replace("-", "")
                .replace("AM", "AM").replace("ET", "ET"))
        p = today / f"injury_transcript_{name.replace('_AM_ET', 'AM').replace('_PM_ET', 'PM')}.json"
        _dump(p, doc)
        written.append(str(p.relative_to(ROOT)))

    # ------------------------------------------------------- 11/15: official finals feed
    fin = C.finals_2026_11_15()
    _dump(prior / "results_2026-11-15.json", {
        "schema": "nba2.results-feed.v3",
        "game_date": "2026-11-15",
        "retrieved_utc": C.RETRIEVED_UTC,
        "retrieval_method": (
            "finals and quarter scores read from each game's official gamebook PDF "
            "'SCORE BY PERIOD' table (statsdmz.nba.com) and cross-read against the final "
            "printed on nba.com/schedule for 2026-11-16, via the platform page-fetch tool. "
            "Bash egress cannot reach nba.com; the PDFs were read as text, not archived as "
            "binaries (F-V4-01)."),
        "settle_rule": (
            "A game is SETTLED only when its official gamebook period row sums to the final "
            "for that club AND the final matches the official schedule/scoreboard. A club "
            "whose period row was not transcribed carries null quarters and is shown as "
            "unverified; nothing is back-solved from the final."),
        "records": fin,
        "n_games": len(fin),
        "n_verified_quarters": sum(1 for g in fin if g["quarter_status"] == "read"),
    })
    written.append(str((prior / "results_2026-11-15.json").relative_to(ROOT)))

    # --------------------------------------------------------- the index of both captures
    _dump(today / "capture_index.json", {
        "schema": "nba2.capture-index.v1",
        **stamp,
        "source_pages": C.SOURCE_PAGES,
        "unread": {k: {"what": v[0], "why": v[1], "attempted_url": v[2]}
                   for k, v in C.UNREAD.items()},
        "files": sorted(written + [str((today / "capture_index.json").relative_to(ROOT))]),
        "crosschecks": C.crosschecks(),
    })
    written.append(str((today / "capture_index.json").relative_to(ROOT)))
    return written


if __name__ == "__main__":
    for f in write():
        print("wrote", f)
