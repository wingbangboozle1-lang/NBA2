"""Parse an official injury-release *rendering* into rows, without guessing a column.

The rendering is a set of markdown tables. Its cell counts vary, because the PDF's own
layout changes across a page break and the text converter keeps only the cells that
survived. Positional parsing therefore fails — and it fails *silently*, which is exactly
how a real status change ("Questionable" → "Doubtful") went undetected in the previous
build.

So every cell is assigned by **content type**, never by position:

===============  =============================================================
time             ``07:30 (ET)``
matchup          ``CHI@CLE``
status           one of the league's status words (``Out``, ``Doubtful``, ...)
placeholder      ``NOT YET SUBMITTED``
player           contains a comma — the league prints ``Last, First``
team             any other non-empty text (club names carry no comma)
reason           whatever remains at the end, once status is resolved
===============  =============================================================

The status/reason pair is resolved from the **end** of the row, because that end is stable
even when the left-hand cells were dropped:

* last cell is a status word        → status read, **reason blank** (it is absent, not empty);
* last cell is not, second-to-last is → status + reason both read;
* neither is a status               → **status blank**; a trailing cell that reads as a
  reason (``Injury/Illness …`` / ``G League …`` / ``League …``) is still published as the
  reason, and the row is flagged, because a blank status must never be inferred.

A cell whose type is not recognisable is left unassigned. The row is still published with
a note saying what was unread, and the release publishes a count of unread rows. Nothing is
coerced to a plausible value.
"""

from __future__ import annotations

import re

from .injury_renderings import STATUS_WORDS

_PIPE = re.compile(r"^\|(.*)\|\s*$")
_SEP = re.compile(r"^\|[\s\-|:]+\|\s*$")
_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_TIME = re.compile(r"^(\d{1,2}):(\d{2}) \(ET\)$")
_MATCHUP = re.compile(r"^[A-Z]{2,3}@[A-Z]{2,3}$")
_REASON = re.compile(r"^(Injury/Illness|G League|League|Illness|Rest|Personal|Trade|"
                     r"Not With Team|Suspension)\b")


def _cells(line: str) -> list[str] | None:
    if not _PIPE.match(line):
        return None
    if _SEP.match(line):
        return []
    return [c.strip() for c in _PIPE.match(line).group(1).split("|")]


def _iso(mm_dd_yyyy: str) -> str:
    mm, dd, yy = _DATE.match(mm_dd_yyyy).groups()
    return f"{yy}-{mm}-{dd}"


def _h24(cell: str) -> str | None:
    m = _TIME.match(cell)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None


def _is_status(cell: str) -> bool:
    return cell in STATUS_WORDS


def _is_reason(cell: str) -> bool:
    return bool(_REASON.match(cell))


def _is_player(cell: str) -> bool:
    return "," in cell


def parse_render(text: str) -> dict:
    """Return {rows, unread, counts} for one stored rendering.

    Row keys: date, time_et, matchup, team, player, status, reason, placeholder, note.
    ``None`` means *not read from the source*. It never means *empty*.
    """
    rows: list[dict] = []
    unread: list[dict] = []
    ctx = {"date": None, "time_et": None, "matchup": None}
    block_team: str | None = None
    in_table = False

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("**Injury Report:"):
            in_table = False
            continue
        cells = _cells(line)
        if cells is None:
            in_table = False
            continue
        if cells == []:
            in_table = True
            continue
        if not in_table:
            continue
        if cells and cells[0] == "Game Date":
            continue

        core = [c for c in cells]
        while core and core[0] == "":
            core.pop(0)
        if not any(core):
            continue

        notes: list[str] = []
        row_ctx = dict(ctx)          # what this row itself carried, before it updates ctx
        team: str | None = None
        player: str | None = None
        status: str | None = None
        reason: str | None = None
        placeholder = False

        # ---------------- placeholder rows ----------------
        if "NOT YET SUBMITTED" in core:
            placeholder = True
            for c in core:
                if _DATE.match(c):
                    ctx["date"] = row_ctx["date"] = _iso(c)
                elif _TIME.match(c):
                    ctx["time_et"] = row_ctx["time_et"] = _h24(c)
                elif _MATCHUP.match(c):
                    ctx["matchup"] = row_ctx["matchup"] = c
                elif c and not _is_status(c) and not _is_reason(c):
                    team = team or c
            if not team:
                team = block_team
                notes.append("team carried from the block in progress")
            reason = "NOT YET SUBMITTED"

        else:
            # ---------------- left-hand typed cells ----------------
            rest: list[str] = []
            for c in core:
                if _DATE.match(c):
                    ctx["date"] = row_ctx["date"] = _iso(c)
                elif _TIME.match(c):
                    ctx["time_et"] = row_ctx["time_et"] = _h24(c)
                elif _MATCHUP.match(c):
                    ctx["matchup"] = row_ctx["matchup"] = c
                else:
                    rest.append(c)

            # ---------------- status / reason, resolved from the end --------
            tail: list[str] = []
            while rest and rest[-1] == "":
                rest.pop()
            if rest and _is_status(rest[-1]):
                status = rest.pop()
            elif len(rest) >= 2 and _is_status(rest[-2]):
                status = rest.pop(-2)
                tail = [rest.pop()]
            elif rest and _is_reason(rest[-1]):
                tail = [rest.pop()]
                notes.append("F-V4-06 status not present in the rendering; blank, not inferred")
            elif rest and not _is_player(rest[-1]) and len(rest) >= 3:
                unread.append({"raw": line, "why": "trailing cell is neither status nor reason"})

            # ---------------- team and player ----------------
            leftovers: list[str] = []
            for c in rest:
                if not c:
                    continue
                if _is_player(c) and player is None:
                    player = c
                elif _is_player(c) and player is not None:
                    leftovers.append(c)
                elif team is None:
                    team = c
                elif not _is_player(c) and team is not None:
                    leftovers.append(c)
            if tail:
                reason = tail[0]
            if leftovers:
                notes.append("unplaced cell(s) left unassigned: " + "; ".join(leftovers))
            if team is None:
                team = block_team
                notes.append("team carried from the block in progress")
            if player is None:
                notes.append("no player cell in this row")

        if team:
            block_team = team
        if not row_ctx["date"] and not placeholder:
            notes.append("date carried from the block in progress")

        # An empty *reason* is not a reason: report it, do not invent one.
        if not placeholder and reason is None and status is not None:
            notes.append("reason absent from the rendering")

        rows.append({"date": row_ctx["date"], "time_et": row_ctx["time_et"],
                     "matchup": row_ctx["matchup"], "team": team, "player": player,
                     "status": status, "reason": reason, "placeholder": placeholder,
                     "note": "; ".join(dict.fromkeys(notes)), "cells": len(core)})

    return {"rows": rows, "unread": unread,
            "counts": {"rows": len(rows),
                       "with_status": sum(1 for r in rows if r["status"]),
                       "blank_status": sum(1 for r in rows
                                           if r["status"] is None and not r["placeholder"]),
                       "placeholders": sum(1 for r in rows if r["placeholder"]),
                       "unread": len(unread)}}


def key(row: dict) -> tuple:
    """Identity of a row across releases: a player, on a team, in a game."""
    ident = row["player"] or "<placeholder>"
    return (row["date"], row["matchup"], row["team"], ident)
