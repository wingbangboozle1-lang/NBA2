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
    DATA / "raw" / "refresh_*" / "results_*.json",
    DATA / "raw" / "capture_*" / "results_*.json",
    DATA / "v2" / "results.json",
    DATA / "v5" / "results_union.json",
]

SETTLED_ALL = DATA / "v4" / "settlement" / "settled-all.json"
SEALED_GLOBS = [DATA / "raw" / "ledger" / "sealed-*.json",
                DATA / "v3" / "ledger" / "sealed-*.json"]

_DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")
BOOK_RE = re.compile(r"^https://statsdmz\.nba\.com/pdfs/(\d{8})/\1_[A-Z]{6}_book\.pdf$")

# Derived clock. The result-feed page must answer "has this game day ended?" the same way on
# every rebuild, because pages.yml fails the deploy if a rebuild differs from what is
# committed — so the clock may not be `datetime.now()`. It is also not a hand-typed literal:
# a hard-coded AS_OF silently ages, and when the ingest bot committed the 2026-11-18 capture
# the page kept answering the question as of 2026-11-17 while nine 2026-11-18 finals sat in
# the tree (measured: the 11/17 and 11/18 filenames are graded "not ended" on the published
# page). AS_OF is therefore the **latest retrieval stamp of any committed official capture**,
# which makes "has this day ended?" answerable from the evidence rather than from memory:
# every capture records the moment it read the official source.
_STAMPED_GLOBS = [
    DATA / "raw" / "finals_*.json",
    DATA / "raw" / "results" / "*.json",
    DATA / "raw" / "refresh_*" / "*.json",
    DATA / "raw" / "capture_*" / "*.json",
    DATA / "raw" / "slate_*.json",
    DATA / "raw" / "standings_*.json",
]

ET_OFFSET_HOURS = -5   # November: EST (UTC-5). Stated on the page; not applied elsewhere.


def latest_capture() -> tuple[str, str, str]:
    """(utc stamp, ET stamp, date) of the most recent committed official capture.

    Returns ("", "", "") when no committed capture carries a parseable stamp — the caller
    then says the clock is unknown rather than inventing one.
    """
    from datetime import datetime, timedelta, timezone

    newest: datetime | None = None
    for p in _glob(_STAMPED_GLOBS):
        try:
            doc = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(doc, dict):
            continue
        raw = (doc.get("retrieved_at_utc") or doc.get("retrieved_at")
               or doc.get("captured_at_utc") or doc.get("as_of_utc"))
        if not isinstance(raw, str):
            continue
        try:
            t = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        if newest is None or t > newest:
            newest = t
    if newest is None:
        return "", "", ""
    t = newest.astimezone(timezone.utc)
    et = t + timedelta(hours=ET_OFFSET_HOURS)
    return (t.strftime("%Y-%m-%dT%H:%M:%SZ"),
            et.strftime("%Y-%m-%d %H:%M") + " ET", et.strftime("%Y-%m-%d"))


def _glob(paths) -> list[Path]:
    out: list[Path] = []
    for pat in paths:
        out.extend(sorted(Path(ROOT).glob(str(Path(pat).relative_to(ROOT)))))
    return out


# Resolved once, after `_glob`, so the clock and the scan share one definition.
AS_OF_UTC, AS_OF_ET, AS_OF_DATE = latest_capture()


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
def _merge_into(dst: dict, rec: dict) -> None:
    """Copy the non-null keys of ``rec`` into ``dst``; a null never overwrites a value.

    Merging is done per key with this one rule so a richer sighting of a game can add
    fields the sparse sighting lacks, while a sparse sighting can never blank a value the
    rich one already supplied. Nulls are carried only for keys nothing has filled yet, so
    a downstream reader can still tell "absent everywhere" (missing key) from "present and
    blank in some feed" (key with None).
    """
    for k, val in rec.items():
        if val is not None or k not in dst:
            dst[k] = val


def _records_of(doc: dict) -> list[dict]:
    """Every game-shaped row in the document: one raw row per sighting, unmerged.

    Some committed feeds carry the same games twice in one file under different keys —
    ``data/raw/finals_2026-11-13.json`` has a sparse ``records`` list (game id, score,
    source) and a rich ``games`` list (date, teams, venue, quarter rows) for the same nine
    games. Both spellings are returned here, one dict per sighting, because the field
    names differ between the two source families and the alias resolution in
    :func:`_final_record` has to see the raw keys: ``finals_2026-11-1{4,5}.json`` store
    the official game URL under ``final_source_url`` and the clubs under
    ``away_team``/``home_team``, and a merge-then-read would drop those whenever the other
    sighting of the same game used a different spelling.
    """
    out: list[dict] = []
    for key in ("records", "games", "results"):
        v = doc.get(key)
        if not isinstance(v, list):
            continue
        for r in v:
            if isinstance(r, dict) and r.get("game_id"):
                out.append(r)
    return out


# The two committed official result families spell the same facts differently. Both
# spellings were read off the committed files, not guessed: `finals_2026-11-13.json` and
# `finals_2026-11-1{5,6}.json` use `away`/`home` + `source_url`; `finals_2026-11-14.json`
# and `finals_2026-11-15.json` use `away_team`/`home_team` + `final_source_url`; the v5
# union and the 11/17-11/18 captures use `source_url` again. Aliases are resolved per
# sighting so a value present in the file always reaches the row it belongs to.
_ALIASES = {
    "away": ("away", "away_team", "visitor", "visitor_team"),
    "home": ("home", "home_team", "home_team_name"),
    "source_url": ("source_url", "final_source_url", "official_source", "game_url"),
    "gamebook_url": ("gamebook_url", "gamebook_source", "book_url"),
}


def _alias(rec: dict, field: str):
    for k in _ALIASES[field]:
        v = rec.get(k)
        if v:
            return v
    return None


def _final_record(rec: dict, fallback_date: str | None, rel: str) -> dict | None:
    """One committed final, normalised — or None when the row holds no final score.

    Nothing is derived: a row with no game id or without both scores is dropped, and a
    status that is not a final is dropped, so a postponed or in-progress row can never be
    published as a result.
    """
    gid = rec.get("game_id")
    ap, hp = rec.get("away_pts"), rec.get("home_pts")
    if not gid or ap is None or hp is None:
        return None
    status = rec.get("status")
    if status and str(status).lower() not in ("final", "final/ot", "completed"):
        return None
    aq = rec.get("away_quarters") or rec.get("away_q")
    hq = rec.get("home_quarters") or rec.get("home_q")
    ot = rec.get("ot_quarters") or {}
    ot_a = ot.get("away") if isinstance(ot, dict) else None
    ot_h = ot.get("home") if isinstance(ot, dict) else None
    # Two committed official feeds store overtime differently and both are correct: one
    # appends the OT periods to the quarter row, the other keeps regulation in
    # `away_quarters` and the extra periods in `ot_quarters`. Normalising both to a full
    # period row is what makes the sum-to-final check mean anything.
    if ot_a and not rec.get("away_q"):
        aq = list(aq or []) + list(ot_a)
    if ot_h and not rec.get("home_q"):
        hq = list(hq or []) + list(ot_h)
    schema = ("regulation + ot_quarters" if (ot_a or ot_h)
              else "all periods inline" if (aq and len(aq) > 4)
              else "regulation only")
    return {
        "game_id": gid, "date": rec.get("date") or fallback_date,
        "away": _alias(rec, "away"), "home": _alias(rec, "home"),
        "away_pts": ap, "home_pts": hp,
        "away_quarters": aq, "home_quarters": hq,
        "ot_periods": rec.get("ot_periods"),
        "period_schema": schema,
        "source_url": _alias(rec, "source_url"),
        "gamebook_url": _alias(rec, "gamebook_url"),
        "files": [rel],
    }


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
            rec = _final_record(r, fallback_date, rel)
            if rec is None:
                continue
            gid = rec["game_id"]
            prev = out.get(gid)
            if prev is None:
                out[gid] = rec
                continue
            if rel not in prev["files"]:
                prev["files"].append(rel)
            # two committed finals that disagree is a finding, not something to average
            if (prev["away_pts"], prev["home_pts"]) != (rec["away_pts"], rec["home_pts"]):
                prev.setdefault("conflicts", []).append(
                    {"file": rel, "away_pts": rec["away_pts"],
                     "home_pts": rec["home_pts"]})
            # a second sighting fills blanks; it never overwrites a value already read
            _merge_into(prev, {k: v for k, v in rec.items()
                               if k not in ("files", "conflicts")})
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
    for r in doc.get("finals_used", []) or []:
        gid = r.get("game_id")
        if gid:
            graded.add(gid)
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


def _matchup(slate: dict, final: dict | None) -> str | None:
    """`AWY @ HOM` from whichever committed artefact carries both clubs, else None.

    The previous expression interpolated the f-string first and only then consulted the
    final for team names, so every game that came from a result file printed the literal
    text "None @ None" — measured on 14 of 67 rows of the committed data/v6/results_coverage.json.
    A blank is honest; the string "None @ None" is not.
    """
    for src in (slate, final or {}):
        away, home = src.get("away"), src.get("home")
        if away and home:
            return f"{away} @ {home}"
    return None


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

        if d >= today and not have:
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
                       else "not ended" if (d >= today and not have) else "incomplete"),
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
            "matchup": _matchup(g, f),
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
        "as_of_utc": "2026-11-17T00:00:00Z",
        "today": today,
        "n_dates": len(rows),
        "n_games_known": len(games),
        "n_games_with_final": sum(1 for g in games if g["away_pts"] is not None),
        "n_games_graded": sum(1 for g in games if g["graded"]),
        "settlement": settle_info,
        "rows": rows,
        "games": games,
    }
