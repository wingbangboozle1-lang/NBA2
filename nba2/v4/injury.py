"""The official injury release: rows, filing coverage, and the release-to-release diff.

The brief asks for two things here that are easy to fake and hard to do: store
every PDF with its timestamp, and diff consecutive reports so a status change is
detected rather than noticed. The diff is keyed on (club, player) exactly as the
PDF prints them; where a row's club cell is blank on the PDF the capture carries
``attributed_team=True`` and the key uses the attributed club, so a reviewer can
tell an inferred cell from a printed one.
"""

from __future__ import annotations

from . import official as O

PM_COLS = ["game_date", "time_et", "matchup", "team", "player", "status", "reason", "attributed_team"]
AM_COLS = ["game_date", "time_et", "matchup", "team", "player", "status", "reason"]

SOURCE_URL = O.SOURCES["injury_pdf"][1]
INDEX_URL = O.SOURCES["injury_index"][1]
PRIOR_URL = O.SOURCES["injury_prior"][1]

STATUS_ORDER = {"Out": 0, "Doubtful": 1, "Questionable": 2, "Probable": 3, "Available": 4}


def release(pm: bool = True) -> dict:
    return O.injury(pm)


def records(pm: bool = True) -> list[dict]:
    d = release(pm)
    cols = d["columns"]
    out = []
    for r in d["records"]:
        rec = dict(zip(cols, r))
        rec.setdefault("attributed_team", False)
        rec["source_url"] = SOURCE_URL if pm else PRIOR_URL
        out.append(rec)
    return out


def player_rows(pm: bool = True) -> list[dict]:
    return [r for r in records(pm) if r["player"]]


def not_submitted(pm: bool = True) -> list[dict]:
    return [r for r in records(pm) if not r["player"] and "NOT YET SUBMITTED" in (r["reason"] or r["status"])]


def status_counts(pm: bool = True) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in player_rows(pm):
        out[r["status"]] = out.get(r["status"], 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def diff() -> dict:
    """Compare the 06:15 AM ET release with the 06:15 PM ET release of the same day."""
    def key(r: dict) -> tuple[str, str]:
        return (r["team"], r["player"])

    prior = {key(r): r for r in player_rows(False)}
    cur = {key(r): r for r in player_rows(True)}
    changes, added, removed = [], [], []
    for k in sorted(set(prior) | set(cur)):
        a, b = prior.get(k), cur.get(k)
        if a is None:
            added.append(cur[k])
            continue
        if b is None:
            removed.append(a)
            continue
        if a["status"] != b["status"]:
            changes.append({
                "team": k[0], "player": k[1],
                "from_status": a["status"], "to_status": b["status"],
                "prior_reason": a["reason"], "current_reason": b["reason"],
                "matchup": b["matchup"],
                "direction": ("more available" if STATUS_ORDER.get(b["status"], 9) >
                              STATUS_ORDER.get(a["status"], 9) else "less available"),
                "source_url": SOURCE_URL,
            })
    return {
        "prior_stamp": release(False)["report_stamp_et"],
        "current_stamp": release(True)["report_stamp_et"],
        "prior_rows": len(player_rows(False)),
        "current_rows": len(player_rows(True)),
        "changes": changes,
        "added": added,
        "removed": removed,
        "unchanged": len(prior) - len(removed) - len(changes),
    }


def slate_rows(date: str = "2026-11-16") -> list[dict]:
    """Every release row for one game date, in PDF order."""
    return [r for r in records(True) if r["game_date"] == date]
