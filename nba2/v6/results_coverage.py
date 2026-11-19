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
* **graded** — the distinct game ids scored by either the v4 settlement or the nightly
  sealed-ledger settlement in ``data/settlement.json``.

The difference between those three numbers is the settlement backlog, and each row says
which of the three is missing and why.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

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
PIPELINE_SETTLEMENT = DATA / "settlement.json"
SEALED_GLOBS = [DATA / "raw" / "ledger" / "sealed-*.json",
                DATA / "v3" / "ledger" / "sealed-*.json"]

_DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")
BOOK_RE = re.compile(r"^https://statsdmz\.nba\.com/pdfs/(\d{8})/\1_[A-Z]{6}_book\.pdf$")

# The result-feed page's "has this game day ended?" cutoff comes from committed capture
# metadata, so rebuilds are deterministic and the displayed as-of stamp advances with the
# scheduled ingest. A failed finals attempt never advances the clock; we fall back to the
# newest committed official finals/result capture. The final fallback is the committed
# capture in `data/raw/capture_2026-11-18/finals_2026-11-18.json`, which records
# retrieved_at_utc=2026-11-18T19:30:20+00:00 (session arena/af5df7a7-nba2: using the
# committed source time — never wall-clock — keeps the game-day classification
# reproducible). November is UTC-5 in US Eastern.
_FALLBACK_AS_OF_UTC = "2026-11-18T19:30:20Z"
_EASTERN = ZoneInfo("America/New_York")


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        stamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        return None
    return stamp.astimezone(timezone.utc).replace(microsecond=0)


def _as_of() -> tuple[str, str, str]:
    """Latest successful official results capture as UTC stamp, ET stamp, ET date."""
    raw = DATA / "raw"
    candidates: list[datetime] = []

    verdict_path = raw / "refresh_verdict.json"
    try:
        verdict = json.loads(verdict_path.read_text())
    except (OSError, json.JSONDecodeError):
        verdict = {}
    if (verdict.get("surfaces") or {}).get("finals") == "success":
        stamp = _parse_utc(verdict.get("attempted_at_utc"))
        if stamp is not None:
            candidates.append(stamp)

    capture_paths = set(raw.glob("finals_*.json"))
    for pattern in ("results/*.json", "refresh_*/results_*.json",
                    "capture_*/results_*.json"):
        capture_paths.update(raw.glob(pattern))
    capture_paths.update(raw.glob("refresh_*/capture_index.json"))
    capture_paths.update(raw.glob("capture_*/capture_index.json"))
    for path in sorted(capture_paths):
        try:
            doc = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for key in ("retrieved_at_utc", "retrieved_utc"):
            stamp = _parse_utc(doc.get(key))
            if stamp is not None:
                candidates.append(stamp)

    latest = max(candidates) if candidates else _parse_utc(_FALLBACK_AS_OF_UTC)
    assert latest is not None  # the committed fallback above is a valid UTC timestamp
    et = latest.astimezone(_EASTERN)
    return (latest.isoformat(timespec="seconds").replace("+00:00", "Z"),
            et.strftime("%Y-%m-%d %H:%M ET"), et.date().isoformat())


AS_OF_UTC, AS_OF_ET, AS_OF_DATE = _as_of()


def _glob(paths) -> list[Path]:
    out: list[Path] = []
    for pat in paths:
        out.extend(sorted(Path(ROOT).glob(str(Path(pat).relative_to(ROOT)))))
    return out


def _schedule_url_for_date(url: object, date: object) -> str | None:
    """Accept only an official NBA schedule URL whose query names this exact date."""
    if not isinstance(url, str) or not isinstance(date, str):
        return None
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.netloc.lower() not in {"nba.com", "www.nba.com"}
            or parsed.path not in {"/schedule", "/games"}):
        return None
    return url if parse_qs(parsed.query).get("date") == [date] else None


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
        source = doc.get("source")
        list_urls = [doc.get("source_url")]
        if isinstance(source, str):
            list_urls.append(source)
        elif isinstance(source, dict):
            list_urls.append(source.get("url"))
        for g in games:
            gid = g.get("game_id")
            if not gid:
                continue
            row = out.setdefault(gid, {
                "game_id": gid, "date": g.get("date"),
                "away": g.get("away") or g.get("away_team"),
                "home": g.get("home") or g.get("home_team"),
                "matchup": g.get("matchup"),
                "source_url": g.get("source_url"),
                "snapshots": [],
            })
            rel = str(p.relative_to(ROOT))
            if rel not in row["snapshots"]:
                row["snapshots"].append(rel)
            if not row.get("source_url") and g.get("source_url"):
                row["source_url"] = g["source_url"]
            game_date = g.get("date") or row.get("date")
            for candidate in (g.get("list_url"), *list_urls):
                date_url = _schedule_url_for_date(candidate, game_date)
                if date_url:
                    if not row.get("list_url"):
                        row["list_url"] = date_url
                    break
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
            # Two committed finals that disagree is a finding, not something to average.
            # Do not use metadata from a conflicting score row to complete the selected
            # record: the game is conflicted and its detail must remain reviewable.
            if (prev["away_pts"], prev["home_pts"]) != (ap, hp):
                prev.setdefault("conflicts", []).append(
                    {"file": rel, "away_pts": ap, "home_pts": hp})
                continue

            # Several independent official captures can describe the same game. Earlier
            # score-only rows often lack team names or document links; preserve those blanks
            # until a later row with the SAME official game ID and matching final supplies
            # the metadata. Never construct a URL from a date or matchup. Two rows that
            # name different clubs for the same game id are a conflict, not enrichment.
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

            # Sparse official score feeds are often followed by richer gamebook captures.
            # Keep the first consistent final, but fill only absent metadata from another
            # committed row for that same game id. In particular, preserve official
            # source/gamebook URLs instead of losing them because the score-only file was
            # enumerated first. No score, team, or non-blank field is overwritten here.
            for field in ("date", "away", "home", "away_quarters", "home_quarters",
                          "ot_periods", "period_schema", "source_url", "gamebook_url"):
                existing, candidate = prev.get(field), rec.get(field)
                if existing in (None, "", []) and candidate not in (None, "", []):
                    prev[field] = candidate
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

    Only the ledgers' graded rows count — the v4 settlement's per-ledger graded rows
    and the nightly sealed-ledger settlement's ``settled_rows`` in ``data/settlement.json``
    (session arena/8c7c8828-nba2). ``finals_used`` is provenance for which finals the
    settlement *read* — its 2026-11-18 capture file spans 2026-11-13→17, so counting it
    here would report the pre-request 11/13 games as graded although no sealed pick ever
    existed for them (session arena/af5df7a7-nba2, 2026-11-19: the same rule the test
    below pins — a game that was never pre-registered can be settled, but it can never
    be *graded*). The ``finals_used`` ids are surfaced in the info dict as provenance,
    never merged into the graded set.
    """
    doc = maybe_load(SETTLED_ALL) or {}
    pipeline = maybe_load(PIPELINE_SETTLEMENT) or {}
    graded: set = set()
    per_ledger = []
    for ledger in doc.get("ledgers", []) or []:
        rows = ledger.get("graded") or []
        ids = {r.get("game_id") for r in rows if isinstance(r, dict) and r.get("game_id")}
        graded |= ids
        per_ledger.append({"ledger": ledger.get("ledger"), "n_graded": len(rows),
                           "n_ungraded": len(ledger.get("ungraded") or []),
                           "latest_graded_game_date": ledger.get("latest_graded_game_date"),
                           "settlement_source": "data/v4/settlement/settled-all.json"})

    # Provenance only: the finals the settlement read. These ids are NOT graded unless a
    # ledger above (or the nightly feed below) actually scored a sealed pick against them.
    finals_used_ids = sorted({row.get("game_id")
                              for row in doc.get("finals_used", []) or []
                              if isinstance(row, dict) and row.get("game_id")})

    pipeline_ledgers = []
    for ledger in pipeline.get("ledgers", []) or []:
        rows = ledger.get("settled_rows") or []
        ids = {r.get("game_id") for r in rows if isinstance(r, dict) and r.get("game_id")}
        graded |= ids
        pipeline_ledgers.append({"ledger": ledger.get("ledger"),
                                 "n_graded": len(ids),
                                 "games_settled": ledger.get("games_settled"),
                                 "games_expected": ledger.get("games_expected"),
                                 "status": ledger.get("status"),
                                 "settlement_source": "data/settlement.json"})

    v4_settled = (doc.get("settlement") or {}).get("settled_at_utc")
    pipeline_settled = pipeline.get("settled_at_utc")
    stamps = [stamp for stamp in (v4_settled, pipeline_settled)
              if _parse_utc(stamp) is not None]
    latest_stamp = max(stamps, key=lambda stamp: _parse_utc(stamp)) if stamps else None
    return graded, {"per_ledger": per_ledger,
                    "pipeline_ledgers": pipeline_ledgers,
                    "finals_used_ids": finals_used_ids,
                    "settled_at_utc": latest_stamp,
                    "v4_settled_at_utc": v4_settled,
                    "pipeline_settled_at_utc": pipeline_settled,
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
    graded_dates = [fin[gid].get("date") for gid in graded
                    if gid in fin and fin[gid].get("date")]
    known_graded_dates = [d for d in [settle_info.get("latest_graded_game_date"),
                                      *graded_dates] if d]
    settle_info["latest_graded_game_date"] = max(known_graded_dates) if known_graded_dates else None
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
            # is answered from the latest committed successful results capture, not now().
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
            "list_url": next((_schedule_url_for_date(g.get("list_url"), d)
                               for g in gs if _schedule_url_for_date(g.get("list_url"), d)), None)
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
        # Committed feeds name the clubs their own way (away vs away_team); read every
        # known name, and when no committed row carries the clubs the matchup cell stays
        # BLANK — never the string "None @ None" (session arena/af5df7a7-nba2, 2026-11-19).
        a_name = (g.get("away") or g.get("away_team")
                  or (f or {}).get("away") or (f or {}).get("away_team"))
        h_name = (g.get("home") or g.get("home_team")
                  or (f or {}).get("home") or (f or {}).get("home_team"))
        games.append({
            "game_id": gid, "date": g.get("date") or (f or {}).get("date"),
            "matchup": g.get("matchup")
                       or (f"{a_name} @ {h_name}" if a_name and h_name else ""),
            "away": a_name,
            "home": h_name,
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
