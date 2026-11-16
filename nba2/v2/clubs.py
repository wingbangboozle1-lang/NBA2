"""Official per-club season tables — the SG-37 capture, loaded by the published build.

SG-37 split the player-data problem in two: (a) the 30 per-club season tables
(nba.com/stats/players/traditional?TeamID=…) that feed the minutes-redistribution
and production-at-risk surfaces, and (b) per-game logs through box-score pages.
This module covers (a).

The capture is written by the scheduled job (``nba2/v2/refresh.py``) from the
league's official stats API — ``stats.nba.com/stats/leaguedashplayerstats`` —
which is the same dataset the per-club stats pages render, returned as one row
per player with a TeamAbbreviation column (one request covers all 30 clubs).
The snapshot lands as ``data/raw/capture_<date>/player_season_<date>.json``
(schema ``nba2.player-season.v1``).

Provenance rule (unchanged): every row carries the official source URL; a row
that cannot be confirmed stays blank and flagged. If the snapshot is missing,
this module reports ``coverage: 0/30`` and everything downstream stays blank —
nothing is estimated from a name or a hunch.

Three clubs (DEN, CLE, MIN) were first captured by hand on 2026-11-14 by session
``arena/bc867bff-nba2`` (audit/2026-11-14-bc867bff/captures.json) from the
per-club pages themselves; that capture remains the provenance record for those
rows. This module is the 30-club completion.
"""

from __future__ import annotations

from pathlib import Path

from . import official as O

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
SCHEMA = "nba2.player-season.v1"
SOURCE_PAGE = "https://www.nba.com/stats/players/traditional?TeamID={team_id}"
SOURCE_API = ("https://stats.nba.com/stats/leaguedashplayerstats?MeasureType=Base&PerMode=PerGame"
              "&Season=2026-27&SeasonType=Regular%20Season")


def _doc() -> dict | None:
    """The newest committed per-player season snapshot, or None."""
    return O._latest("player_season_*.json")


def _doc_path() -> str | None:
    """Path of the snapshot :func:`_doc` selected (the newest by embedded date)."""
    import glob
    cands = sorted(glob.glob(str(RAW / "player_season_*.json"))
                   + glob.glob(str(RAW / "capture_*" / "player_season_*.json")),
                   key=O._date_key)
    return cands[-1] if cands else None


def snapshot_meta() -> dict:
    """What exists, stamped — the honest answer even when the answer is 'nothing'."""
    doc = _doc()
    if not doc:
        return {"schema": SCHEMA, "snapshot": None,
                "coverage_clubs": 0,
                "note": "no committed per-player season snapshot — blank + flagged, never estimated"}
    clubs = sorted({r["team_abbrev"] for r in doc["rows"]})
    return {"schema": SCHEMA,
            "snapshot": _doc_path() or "",
            "as_of": doc.get("as_of"),
            "retrieved_at_utc": doc.get("retrieved_at_utc"),
            "retrieval_method": doc.get("retrieval_method", ""),
            "rows": len(doc["rows"]),
            "coverage_clubs": len(clubs),
            "clubs": clubs,
            "source_url": doc.get("source_url", SOURCE_API)}


def _rows_by_club() -> dict[str, list[dict]]:
    doc = _doc()
    if not doc:
        return {}
    out: dict[str, list[dict]] = {}
    for r in doc["rows"]:
        out.setdefault(r["team_abbrev"], []).append(r)
    for tri in out:
        out[tri].sort(key=lambda r: (-float(r["mpg"] or 0), -float(r["ppg"] or 0)))
    return out


def club_rows(tri: str) -> list[dict]:
    """One club's official season rows, ordered by minutes (the page orders by points;
    the rotation tables re-order by minutes and say so — same rule as the 2026-11-14 capture)."""
    rows = _rows_by_club().get(tri.upper(), [])
    return [{
        "rank_by_minutes": i + 1,
        "player": r["player"], "player_id": r["player_id"], "team": r["team_abbrev"],
        "age": r.get("age"), "gp": r.get("gp"), "team_w": r.get("team_w"), "team_l": r.get("team_l"),
        "mpg": r["mpg"], "ppg": r["ppg"],
        "source_url": r.get("source_url") or SOURCE_PAGE.format(team_id=r.get("team_id", "")),
    } for i, r in enumerate(rows)]


def coverage() -> dict:
    """{tri: row_count} for every club the snapshot covers; absent clubs are absent, not zero-filled."""
    return {tri: len(rows) for tri, rows in sorted(_rows_by_club().items())}


def top8_blocks() -> dict[str, list[dict]]:
    """{tri: [top-8 rows by minutes]} — the rotation, straight from the official table."""
    return {tri: rows[:8] for tri, rows in _rows_by_club().items() if len(rows) >= 8}


def top8_shares() -> dict[str, list[dict]]:
    """Published before-shares per club: share_i = mpg_i / Σ_{top8} mpg."""
    out = {}
    for tri, rows in top8_blocks().items():
        tot = sum(float(r["mpg"] or 0) for r in rows)
        if tot <= 0:
            continue
        out[tri] = [{"player": r["player"], "mpg": r["mpg"],
                     "min_share": round(float(r["mpg"]) / tot, 4),
                     "source_url": r.get("source_url") or SOURCE_PAGE.format(team_id=r.get("team_id", ""))}
                    for r in rows]
    return out
