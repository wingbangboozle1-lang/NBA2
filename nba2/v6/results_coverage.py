"""K-04 — one row per game date: scheduled, finals committed, graded, and the gap.

The brief asks for an official per-game result feed that stays current, and for the sealed
ledger to be settled from official finals as soon as each game day ends. This module does
not fetch anything; it **measures the coverage of what is committed**, so the gap is a number
with a date on it instead of a sentence in a commit message.

Three sets are built from committed files only:

* **scheduled** — the union of every committed official slate snapshot, keyed by official
  game id (a game seen by two snapshots is one game, and the second sighting is a
  corroboration, not a second row);
* **finals committed** — the union of every committed official result file, plus the v4
  settlement's own ``finals_used`` list. A game counts only when a final score is present;
* **graded** — the distinct game ids the v4 settlement actually scored.

The difference between those three numbers is the settlement backlog, and each row says
which of the three is missing and why.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .common import DATA, RAW, ROOT, maybe_load

SLATE_GLOBS = [
    DATA / "raw" / "slate_*.json",
    DATA / "raw" / "refresh_*" / "slate_*.json",
    DATA / "raw" / "capture_*" / "slate_*.json",
    DATA / "raw" / "history" / "slate_*.json",
]

RESULT_GLOBS = [
    DATA / "raw" / "finals_*.json",
    DATA / "raw" / "results" / "*.json",
    DATA / "raw" / "refresh_*" / "finals_*.json",
    DATA / "raw" / "refresh_*" / "results_*.json",
    DATA / "raw" / "capture_*" / "finals_*.json",
    DATA / "raw" / "capture_*" / "results_*.json",
    DATA / "v2" / "results.json",
    DATA / "v5" / "results_union.json",
]

SETTLED_ALL = DATA / "v4" / "settlement" / "settled-all.json"
SEALED_GLOBS = [DATA / "raw" / "ledger" / "sealed-*.json",
                DATA / "v3" / "ledger" / "sealed-*.json"]

_DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")
BOOK_RE = re.compile(r"^https://statsdmz\.nba\.com/pdfs/(\d{8})/\1_[A-Z]{6}_book\.pdf$")

# Frozen clock: the capture in `data/raw/capture_2026-11-18/finals_2026-11-18.json`
# records retrieved_at_utc=2026-11-18T19:30:20+00:00. Using the committed source time
# keeps the game-day classification reproducible and prevents a later wall-clock rebuild
# from claiming that unobserved games are final. November is UTC-5 in US Eastern.
AS_OF_UTC = "2026-11-18T19:30:20Z"
AS_OF_ET = "2026-11-18 14:30 ET"
AS_OF_DATE = "2026-11-18"


def _glob(paths) -> list[Path]:
    out: list[Path] = []
    for pat in paths:
        out.extend(sorted(Path(ROOT).glob(str(Path(pat).relative_to(ROOT)))))
    return out


# ------------------------------------------------------------------- scheduled
def scheduled() -> dict[str, dict]:
    """Official game id -> the game, from every committed slate snapshot."""
    out: dict[str, dict] = {}
    for p in _glob(SLATE_GLOBS):
        try:
            doc = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        games = doc.get("games") or []
        if not isinstance(games, list):
            continue
        list_url = doc.get("source") if isinstance(doc.get("source"), str) else None
        for g in games:
            gid = g.get("game_id")
            if not gid:
                continue
            row = out.setdefault(gid, {
                "game_id": gid, "date": g.get("date"),
                "away": g.get("away"), "home": g.get("home"),
                "matchup": g.get("matchup") or f"{g.get('away')} @ {g.get('home')}",
                "source_url": g.get("source_url"),
                "snapshots": [],
            })
            rel = str(p.relative_to(ROOT))
            if rel not in row["snapshots"]:
                row["snapshots"].append(rel)
            for key in ("source_url", "list_url"):
                if not row.get(key) and g.get(key):
                    row[key] = g[key]
            if not row.get("list_url") and list_url:
                row["list_url"] = list_url
    return out


# -------------------------------------------------------------- finals on disk
def _records_of(doc: dict) -> list[dict]:
    """Every game-shaped row in the document, merged by game id.

    Some committed feeds carry the same games twice in one file under different keys —
    ``data/raw/finals_2026-11-13.json`` has a sparse ``records`` list (game id, score,
    source) and a rich ``games`` list (date, teams, venue, quarter rows) for the same nine
    games. Picking the first key silently threw away the dates, so both are merged and a
    non-null value always wins over a null one.
    """
    merged: dict[str, dict] = {}
    order: list[str] = []
    for key in ("records", "games", "results"):
        v = doc.get(key)
        if not isinstance(v, list):
            continue
        for r in v:
            if not isinstance(r, dict):
                continue
            gid = r.get("game_id")
            if not gid:
                continue
            if gid not in merged:
                merged[gid] = {}
                order.append(gid)
            for k, val in r.items():
                if val is not None or k not in merged[gid]:
                    if val is not None or merged[gid].get(k) is None:
                        merged[gid][k] = val
    return [merged[g] for g in order]


def finals_committed() -> dict[str, dict]:
    """Official game id -> the committed official final, quarter rows included."""
    out: dict[str, dict] = {}
    for p in _glob(RESULT_GLOBS):
        try:
            doc = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        rel = str(p.relative_to(ROOT))
        doc_date = doc.get("date") or doc.get("game_date")
        fname_date = _DATE_IN_NAME.search(p.name)
        fallback_date = doc_date or (fname_date.group(1) if fname_date else None)
        for r in _records_of(doc):
            gid = r.get("game_id")
            ap, hp = r.get("away_pts"), r.get("home_pts")
            if not gid or ap is None or hp is None:
                continue
            status = r.get("status")
            if status and str(status).lower() not in ("final", "final/ot", "completed"):
                continue
            aq = r.get("away_quarters") or r.get("away_q")
            hq = r.get("home_quarters") or r.get("home_q")
            ot = r.get("ot_quarters") or {}
            ot_a = ot.get("away") if isinstance(ot, dict) else None
            ot_h = ot.get("home") if isinstance(ot, dict) else None
            # Two committed official feeds store overtime differently and both are correct:
            # one appends the OT periods to the quarter row, the other keeps regulation in
            # `away_quarters` and the extra periods in `ot_quarters`. Normalising both to a
            # full period row is what makes the sum-to-final check mean anything.
            if ot_a and r.get("away_q") is not aq:
                aq = list(aq or []) + list(ot_a)
            if ot_h and r.get("home_q") is not hq:
                hq = list(hq or []) + list(ot_h)
            schema = ("regulation + ot_quarters" if (ot_a or ot_h)
                      else "all periods inline" if (aq and len(aq) > 4)
                      else "regulation only")
            rec = {
                "game_id": gid, "date": r.get("date") or fallback_date,
                "away": r.get("away") or r.get("away_team"),
                "home": r.get("home") or r.get("home_team"),
                "away_pts": ap, "home_pts": hp,
                "away_quarters": aq, "home_quarters": hq,
                "ot_periods": r.get("ot_periods"),
                "period_schema": schema,
                # Each committed feed names its URL field differently. Accept the feed's
                # own HTTPS URL only; a prose source label is never promoted into a link.
                "source_url": (r.get("source_url") or r.get("final_source_url")
                               or r.get("official_source")
                               or (r.get("source") if str(r.get("source") or "").startswith("https://") else None)),
                "gamebook_url": r.get("gamebook_url") or r.get("gamebook_source"),
                "files": [rel],
            }
            prev = out.get(gid)
            if prev is None:
                out[gid] = rec
                continue

            if rel not in prev["files"]:
                prev["files"].append(rel)
            # Conflicting finals are a finding, not something to average or enrich from.
            if (prev["away_pts"], prev["home_pts"]) != (ap, hp):
                prev.setdefault("conflicts", []).append(
                    {"file": rel, "away_pts": ap, "home_pts": hp})
                continue

            # Several independent official captures can describe the same game. Earlier
            # score-only rows often lack team names or document links; preserve those blanks
            # until a later row with the SAME official game ID and matching final supplies
            # the metadata. Never construct a URL from a date or matchup.
            team_conflict = any(
                prev.get(k) and rec.get(k) and prev[k] != rec[k]
                for k in ("away", "home"))
            if team_conflict:
                prev.setdefault("conflicts", []).append({
                    "file": rel, "reason": "sources disagree on the clubs",
                    "previous_teams": [prev.get("away"), prev.get("home")],
                    "new_teams": [rec.get("away"), rec.get("home")],
                })
                continue

            for key in ("date", "away", "home", "away_quarters", "home_quarters",
                        "ot_periods", "period_schema", "source_url", "gamebook_url"):
                if prev.get(key) in (None, "") and rec.get(key) not in (None, ""):
                    prev[key] = rec[key]
    return out


def sealed_ids() -> dict[str, set]:
    """date -> the official game ids any sealed ledger predicted for that date."""
    out: dict[str, set] = {}
    for p in _glob(SEALED_GLOBS):
        try:
            doc = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        preds = doc.get("predictions") or doc.get("picks") or []
        for pr in preds:
            gid, d = pr.get("game_id"), pr.get("date")
            if gid and d:
                out.setdefault(d, set()).add(gid)
    return out


def graded_ids() -> tuple[set, dict]:
    """The distinct game ids a sealed pick was actually scored against.

    Only the ledgers' graded rows count. ``finals_used`` is provenance for which
    finals the settlement *read* — its 2026-11-18 capture file spans 2026-11-13→17,
    so counting it here would report the pre-request 11/13 games as graded although
    no sealed pick ever existed for them (session arena/af5df7a7-nba2, 2026-11-19:
    the same rule the test below pins — a game that was never pre-registered can be
    settled, but it can never be *graded*).
    """
    doc = maybe_load(SETTLED_ALL) or {}
    graded: set = set()
    per_ledger = []
    for L in doc.get("ledgers", []) or []:
        rows = L.get("graded") or []
        ids = {r.get("game_id") for r in rows if isinstance(r, dict) and r.get("game_id")}
        graded |= ids
        per_ledger.append({"ledger": L.get("ledger"), "n_graded": len(rows),
                           "n_ungraded": len(L.get("ungraded") or []),
                           "latest_graded_game_date": L.get("latest_graded_game_date")})
    return graded, {"per_ledger": per_ledger,
                    "settled_at_utc": (doc.get("settlement") or {}).get("settled_at_utc"),
                    "latest_graded_game_date": (doc.get("settlement") or {}).get("latest_graded_game_date")}


# ------------------------------------------------------------------- the table
def quarter_check(rec: dict) -> tuple[str, str]:
    """(verdict, detail) — do the committed quarter rows sum to the committed final?"""
    aq, hq = rec.get("away_quarters"), rec.get("home_quarters")
    if not aq or not hq:
        return "no quarter rows committed", (
            "the committed official capture for this game carries the final score but no "
            "period row; the quarters are blank, not zero")
    try:
        sa, sh = sum(aq), sum(hq)
    except TypeError:
        return "unreadable quarter row", "a period cell in the committed capture is not a number"
    ok = (sa == rec["away_pts"]) and (sh == rec["home_pts"])
    return ("quarters sum to the final" if ok else "quarter rows DO NOT sum to the final",
            f"away {'+'.join(map(str, aq))}={sa} vs {rec['away_pts']}; "
            f"home {'+'.join(map(str, hq))}={sh} vs {rec['home_pts']}")


def build(today: str = AS_OF_DATE) -> dict:
    sched = scheduled()
    fin = finals_committed()
    graded, settle_info = graded_ids()
    sealed = sealed_ids()

    dates = sorted({g["date"] for g in sched.values() if g.get("date")}
                   | {g["date"] for g in fin.values() if g.get("date")}
                   | set(sealed))
    rows = []
    for d in dates:
        gs = [g for g in sched.values() if g.get("date") == d]
        gids = sorted({g["game_id"] for g in gs} | sealed.get(d, set())
                      | {gid for gid, r in fin.items() if r.get("date") == d})
        have = [gid for gid in gids if gid in fin]
        done = [gid for gid in gids if gid in graded]
        missing_final = [gid for gid in gids if gid not in fin]
        missing_grade = [gid for gid in gids if gid in fin and gid not in graded]

        if d >= today:
            # The published tree must not depend on the wall clock: pages.yml rebuilds the
            # site and fails if it differs from what is committed, so "has this date ended"
            # is answered from the frozen AS_OF constant, not from datetime.now().
            reason = (f"this date has not ended yet (as-of {AS_OF_UTC} = "
                      f"{AS_OF_ET}) — no official final is claimed for a game that "
                      "has not finished")
        elif not gids:
            reason = "no game is scheduled for this date in any committed official slate"
        elif missing_final and not have:
            reason = ("no official final is committed for any game on this date: the "
                      "scoreboard endpoints the nightly job reads are unreachable "
                      "(see the endpoint register, F-F5-02)")
        elif missing_final:
            reason = f"{len(missing_final)} of {len(gids)} games have no committed official final"
        elif missing_grade:
            reason = (f"finals are committed for all {len(gids)} games but {len(missing_grade)} "
                      "are not scored against a sealed ledger — a game that was never "
                      "pre-registered cannot be settled, so nothing is inferred for it")
        else:
            reason = "complete — every scheduled game has an official final and is graded"

        rows.append({
            "date": d,
            "n_scheduled": len(gids),
            "n_finals_committed": len(have),
            "n_graded": len(done),
            "n_missing_final": len(missing_final),
            "n_missing_grade": len(missing_grade),
            "status": ("complete" if gids and not missing_final and not missing_grade
                       else "not ended" if d >= today else "incomplete"),
            "reason": reason,
            "game_ids": gids,
            "missing_final_ids": missing_final,
            "list_url": next((g.get("list_url") for g in gs if g.get("list_url")), None)
                        or f"https://www.nba.com/schedule?date={d}",
        })

    games = []
    for gid in sorted(set(sched) | set(fin)):
        g = sched.get(gid, {})
        f = fin.get(gid)
        verdict, detail = ("no official final is committed", "blank, never inferred") \
            if not f else quarter_check(f)
        schema = (f or {}).get("period_schema")
        if schema == "regulation + ot_quarters":
            schema = "regulation quarters + a separate ot_quarters row (both committed feeds)"
        if not f:
            schema = "no final committed — no period row to hold"
        games.append({
            "game_id": gid, "date": g.get("date") or (f or {}).get("date"),
            "matchup": g.get("matchup") or f"{g.get('away')} @ {g.get('home')}"
                       or f"{(f or {}).get('away')} @ {(f or {}).get('home')}",
            "away": g.get("away") or (f or {}).get("away"),
            "home": g.get("home") or (f or {}).get("home"),
            "away_pts": (f or {}).get("away_pts"), "home_pts": (f or {}).get("home_pts"),
            "away_quarters": (f or {}).get("away_quarters"),
            "home_quarters": (f or {}).get("home_quarters"),
            "ot_periods": (f or {}).get("ot_periods"),
            "period_schema": schema,
            "quarter_verdict": verdict, "quarter_detail": detail,
            "graded": gid in graded,
            "source_url": (f or {}).get("source_url") or g.get("source_url"),
            "gamebook_url": (f or {}).get("gamebook_url"),
            "finals_files": (f or {}).get("files", []),
            "slate_files": g.get("snapshots", []),
            "conflicts": (f or {}).get("conflicts"),
        })

    return {
        "schema": "nba2.v6.results-coverage.v1",
        "session": "arena/f5ac4e74-nba2",
        "as_of_utc": AS_OF_UTC,
        "today": today,
        "n_dates": len(rows),
        "n_games_known": len(games),
        "n_games_with_final": sum(1 for g in games if g["away_pts"] is not None),
        "n_games_graded": sum(1 for g in games if g["graded"]),
        "settlement": settle_info,
        "rows": rows,
        "games": games,
    }
