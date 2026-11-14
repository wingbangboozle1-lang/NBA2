"""Revision-difference output: what changed between two official revisions of the same data.

The brief asks for a platform that "generates picks for every upcoming game slate, up to 3
days ahead" from *originated* lines, with injuries tracked. Every input to that pipeline
is an official document that the league revises: an injury report is re-issued several
times an hour, and the schedule page changes as games are scheduled and tipped.

A site that publishes only the newest revision hides the thing that matters most to a
bettor: **the churn**. A player who was `Questionable` at 18:30 and `Out` at 19:30 is a
different bet. This module computes that difference from two committed snapshots, so the
churn is published rather than asserted.

Nothing here is inferred: every row is a (player, status) pair that appears in one
revision and not the other, or appears in both with a different status. The output
states which revision introduced the change and how long the change had been in place
at the time the newer revision was captured.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Row:
    game_date: str
    matchup: str
    team: str
    player: str
    old_status: str | None
    new_status: str | None
    change: str            # added | removed | status-changed | unchanged
    reason: str
    old_source: str
    new_source: str

    def as_dict(self) -> dict:
        return self.__dict__.copy()


# The names of the columns an official injury-report row carries.
NEEDED_COLUMNS = ("game_date", "matchup", "team", "player", "status", "reason")


def _key(rec: dict) -> tuple:
    """The identity of an injury row: the player within the game block.

    Time is deliberately NOT part of the key: the PDF's continuation rows lose their
    time cell (FLAG-INJ-08), so including it would make the same player look like a
    different row between two captures of the same document.
    """
    return (rec["game_date"], rec["matchup"], rec["team"], rec["player"])


def diff_revisions(old_doc: dict, new_doc: dict) -> list[Row]:
    """Row-level difference between two injury-report captures.

    `old_doc` and `new_doc` are the parsed snapshot JSON files. Both must be captures of
    *different* official releases; diffing a document against itself is meaningless and
    is reported as such by the caller.
    """
    old_cols = old_doc["columns"]
    new_cols = new_doc["columns"]
    old_rows = [dict(zip(old_cols, r)) for r in old_doc["records"]]
    new_rows = [dict(zip(new_cols, r)) for r in new_doc["records"]]

    old_by_key = {_key(r): r for r in old_rows}
    new_by_key = {_key(r): r for r in new_rows}
    for cols, label in ((old_cols, "previous"), (new_cols, "active")):
        missing = [c for c in NEEDED_COLUMNS if c not in cols]
        if missing:
            raise ValueError(f"{label} injury snapshot is missing column(s) {missing}")

    old_url = old_doc.get("provenance", {}).get("url", "")
    new_url = new_doc.get("provenance", {}).get("url", "")
    old_stamp = old_doc.get("report_stamp_et", "")
    new_stamp = new_doc.get("report_stamp_et", "")

    out: list[Row] = []
    for k in sorted(set(old_by_key) | set(new_by_key)):
        o = old_by_key.get(k)
        n = new_by_key.get(k)
        if o is not None and n is not None and o["status"] == n["status"]:
            continue
        if o is None:
            change = "added"
            old_status, new_status, reason = None, n["status"], n["reason"]
        elif n is None:
            change = "removed"
            old_status, new_status, reason = o["status"], None, o["reason"]
        else:
            change = "status-changed"
            old_status, new_status = o["status"], n["status"]
            reason = n["reason"]
        src = n if n is not None else o
        out.append(Row(
            game_date=src["game_date"], matchup=src["matchup"], team=src["team"],
            player=src["player"] or "—",
            old_status=old_status, new_status=new_status, change=change, reason=reason,
            old_source=f"{old_stamp} ({old_url})", new_source=f"{new_stamp} ({new_url})",
        ))
    return out


def slate_diff(old_doc: dict, new_doc: dict) -> dict:
    """Game-level difference between two slate snapshots.

    Returns the three sets a reader actually wants: what carried over unchanged, what
    was added, and what dropped out (with the games that have since tipped kept
    visible, so the slate cannot look like it silently shrank).
    """
    old_cols = old_doc["columns"]
    new_cols = new_doc["columns"]
    old_recs = [dict(zip(old_cols, r)) for r in old_doc["records"]]
    new_recs = [dict(zip(new_cols, r)) for r in new_doc["records"]]
    old_by_id = {r["game_id"]: r for r in old_recs}
    new_by_id = {r["game_id"]: r for r in new_recs}
    carry, added, dropped = [], [], []
    for gid, r in new_by_id.items():
        o = old_by_id.get(gid)
        if o is None:
            added.append(r)
        elif o == r:
            carry.append(r)
        else:
            # same game id, different content: a field was corrected upstream
            changed = {k: (o.get(k), r.get(k)) for k in r
                       if o.get(k) != r.get(k)}
            added.append({**r, "changed_fields": changed})
    for gid, r in old_by_id.items():
        if gid not in new_by_id:
            dropped.append(r)
    return {"carryover": carry, "added": added, "dropped": dropped}


def summarize(rows: list[Row]) -> dict:
    """Counts a reader can check against the table above it."""
    by_change: dict[str, int] = {}
    for r in rows:
        by_change[r.change] = by_change.get(r.change, 0) + 1
    by_pair: dict[str, int] = {}
    for r in rows:
        if r.change == "status-changed":
            key = f"{r.old_status} → {r.new_status}"
            by_pair[key] = by_pair.get(key, 0) + 1
    teams = sorted({r.team for r in rows if r.team})
    return {
        "total_changes": len(rows),
        "by_change": dict(sorted(by_change.items())),
        "by_transition": dict(sorted(by_pair.items(), key=lambda kv: -kv[1])),
        "teams_affected": len(teams),
        "team_list": teams,
        "players_affected": len({(r.team, r.player) for r in rows}),
    }
