"""Minutes and production at risk, and the redistribution that is not yet computable.

The brief asks for the top-8 minutes shares per club and the replacement shares
when a player is out. The rule is already written and tested in
``nba2/v2/minutes.py`` — it is mechanical, nothing is fitted. What it needs is a
captured minutes column for the players who *remain*, and this session captured
the players who are *out*. So this module publishes exactly what the capture
supports and leaves the receiving side blank:

* **minutes vacated** — the official mean minutes of every captured Out player on
  the club, summed. A lower bound, labelled as one, because N of M injured
  players on the release have a captured log.
* **share of team minutes** — the same minutes over 240 team-minutes per game,
  which is what a redistribution has to re-allocate.
* **absorption candidates** — the club's official roster minus the designated
  players, printed with the official roster as the source and their minutes left
  blank, because those logs are not captured yet.

Nothing here is scaled up, prorated, or estimated to a full-slate figure.
"""

from __future__ import annotations

from . import official as O
from . import gamelog as GL
from . import injury as IN

TEAM_MINUTES_PER_GAME = 240.0

RULE_TEXT = (
    "Top-8 shares = mpg / Σ(top-8 mpg). Replacement shares: each out player's mpg is "
    "redistributed to the remaining players proportionally to their own mpg "
    "(new_mpg_j = mpg_j + Σ_out mpg_i × mpg_j / Σ_avail mpg_k). Mechanical rule, no fit. "
    "It runs the moment the remaining players' logs are captured; until then the "
    "receiving column is blank and flagged."
)

CAPTURED_CLUBS = ("GSW", "NOP")


def _baselines_by_team() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for b in GL.baselines():
        out.setdefault(b["team"], []).append(b)
    return out


def release_outs(team: str, date: str = "2026-11-16") -> list[dict]:
    """Out / Doubtful / Questionable rows for one club on one slate date."""
    club = O.team_full(team)          # the PDF prints club names, not abbreviations
    return [r for r in IN.slate_rows(date)
            if r["team"] == club and r["status"] in ("Out", "Doubtful", "Questionable")]


def at_risk(team: str, date: str = "2026-11-16") -> dict:
    """Minutes and production designated out for one club, from captured logs only."""
    rows = release_outs(team, date)
    have = {b["player"]: b for b in _baselines_by_team().get(team, [])}
    out_rows, captured, missing = [], [], []
    for r in rows:
        b = have.get(r["player"])
        if b is None:
            missing.append(r["player"])
            out_rows.append({
                "player": r["player"], "status": r["status"], "reason": r["reason"],
                "mpg": None, "ppg": None, "rpg": None, "apg": None,
                "note": "no captured game log (F-41B-05)",
                "source_url": IN.SOURCE_URL,
            })
        else:
            captured.append(b)
            out_rows.append({
                "player": r["player"], "status": r["status"], "reason": r["reason"],
                "mpg": b["mpg"], "ppg": b["ppg"], "rpg": b["rpg"], "apg": b["apg"],
                "note": f"{b['games']} official games, last {b['last_game']}",
                "source_url": b["source_url"],
            })
    vacated = round(sum(b["mpg"] for b in captured), 1)
    return {
        "team": team,
        "date": date,
        "designated": len(rows),
        "captured": len(captured),
        "missing": missing,
        "rows": out_rows,
        "vacated_mpg": vacated,
        "vacated_ppg": round(sum(b["ppg"] for b in captured), 1),
        "vacated_rpg": round(sum(b["rpg"] for b in captured), 1),
        "vacated_apg": round(sum(b["apg"] for b in captured), 1),
        "share_of_team_minutes": round(vacated / TEAM_MINUTES_PER_GAME, 4) if captured else None,
        "lower_bound": bool(missing),
        "source_url": IN.SOURCE_URL,
    }


def absorption_candidates(team: str, date: str = "2026-11-16") -> list[dict]:
    """The club's official roster minus the designated players; minutes not captured."""
    roster = next((c for c in O.rosters()["clubs"] if c["team"] == team), None)
    if roster is None:
        return []
    out_names = {r["player"] for r in release_outs(team, date)}
    return [{"player": p["player"], "player_id": p["player_id"], "pos": p["pos"],
             "mpg": None, "note": "official roster row; minutes log not captured — blank, not estimated",
             "source_url": roster["source_url"]} for p in roster["players"]
            if p["player"] not in out_names]


def blocks() -> list[dict]:
    return [at_risk(t) for t in CAPTURED_CLUBS]


def redistribution(team: str, date: str = "2026-11-16") -> dict:
    """The v2 rule applied to this club — blank until the remaining logs are captured."""
    a = at_risk(team, date)
    rows = []
    for r in a["rows"]:
        rows.append({**r, "new_mpg": None, "new_share": None, "delta_share": None,
                     "why_blank": "out player — minutes vacated" if r["mpg"] is not None
                     else "no captured log (F-41B-05)"})
    for c in absorption_candidates(team, date):
        rows.append({**c, "status": "available", "new_mpg": None, "new_share": None,
                     "delta_share": None, "why_blank": "captured rotation minutes needed "
                     "(Σ avail mpg is the denominator of the rule and is not captured)"})
    return {"team": team, "vacated_mpg": a["vacated_mpg"], "rows": rows, "rule": RULE_TEXT}
