"""Explicit minutes redistribution when a player is out.

The brief's rule, made explicit and mechanical (nothing here is fit or estimated):

1. **Top-8 minutes shares** — the rotation is the club's top-8 by minutes per game from
   the official per-club stats table (nba.com/stats/players/traditional?TeamID=…).
   ``share_i = mpg_i / Σ_{top8} mpg``.
2. **Replacement shares** — when players are designated Out/Doubtful (the injury report
   decides *who* is missing; this module only prices the *minutes*), each missing
   player's minutes are redistributed to the remaining available rotation players
   **proportionally to their own minutes**:

   ``new_mpg_j = mpg_j + Σ_{i out} mpg_i · mpg_j / Σ_{k available} mpg_k``

   If no captured rotation player remains available the block is flagged VACANT and the
   shares stay blank (a blank is published, never an invented distribution).
3. Both before-shares and after-shares are published together so the redistribution can
   be re-derived by hand.

Coverage today is the three clubs with captured official per-club tables (DEN, CLE, MIN,
captured 2026-11-14). The other 27 clubs stay blank + flagged for capture, per the
brief's rule. The scheduled job (nba2/v2/refresh.py) captures the rest.
"""

from __future__ import annotations

from . import capture as CP

# status rows the injury report uses to mean "will not play"
SIT = ("Out", "Doubtful")
# status rows that mean "may not play" — reported but NOT removed from the redistribution
MAYBE = ("Questionable",)


def top8_blocks() -> dict[str, list[dict]]:
    """{club_full_name: [rotation rows ordered by minutes]} from the captured tables."""
    rows = CP._doc()["player_rotation"]["rows"] if hasattr(CP, "_doc") else []
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["team"], []).append(r)
    for t in out:
        out[t].sort(key=lambda r: -float(r["mpg"]))
    return out


def top8_shares() -> dict[str, list[dict]]:
    """Published before-shares: player, mpg, share of the captured top-8 minutes."""
    out = {}
    for club, rows in top8_blocks().items():
        tot = sum(float(r["mpg"]) for r in rows) or 1.0
        out[club] = [{"player": r["player"], "mpg": r["mpg"],
                      "min_share": round(float(r["mpg"]) / tot, 4),
                      "source_url": r["source_url"]} for r in rows]
    return out


def replacement_shares(club: str, missing_players: list[str]) -> dict:
    """Mechanical redistribution for one club. ``missing_players`` are names exactly as
    the injury report prints them (``"Murray, Jamal"`` style is normalized)."""
    rows = top8_blocks().get(club, [])
    if not rows:
        return {"club": club, "rows": [], "flag": "no captured rotation block for this club",
                "coverage": "NOT CAPTURED — blank, not estimated"}

    def norm(n: str) -> str:
        n = n.strip().lower()
        if "," in n:
            last, _, first = n.partition(",")
            n = f"{first.strip()} {last.strip()}"
        return " ".join(n.split())

    missing = {norm(m) for m in missing_players}
    avail = [r for r in rows if norm(r["player"]) not in missing]
    out_rows = [r for r in rows if norm(r["player"]) in missing]
    if not out_rows:
        return {"club": club, "missing": [], "rows": [
            {"player": r["player"], "mpg": r["mpg"], "min_share": round(float(r["mpg"]) / sum(float(x["mpg"]) for x in rows), 4),
             "new_mpg": r["mpg"], "new_share": round(float(r["mpg"]) / sum(float(x["mpg"]) for x in rows), 4),
             "delta_share": 0.0, "status": "available — nobody designated OUT on the current release"} for r in rows],
            "rule": RULE_TEXT}
    if not avail:
        return {"club": club, "missing": [r["player"] for r in out_rows], "rows": [],
                "flag": "VACANT — every captured rotation player is out; redistribution left blank"}
    vacated = sum(float(r["mpg"]) for r in out_rows)
    avail_tot = sum(float(r["mpg"]) for r in avail)
    rows_out = []
    for r in rows:
        mpg = float(r["mpg"])
        base = mpg / sum(float(x["mpg"]) for x in rows)
        if norm(r["player"]) in missing:
            rows_out.append({"player": r["player"], "mpg": r["mpg"], "min_share": round(base, 4),
                             "new_mpg": None, "new_share": None, "delta_share": None,
                             "status": "OUT/DNP — minutes vacated"})
        else:
            new_mpg = mpg + vacated * (mpg / avail_tot)
            rows_out.append({"player": r["player"], "mpg": r["mpg"], "min_share": round(base, 4),
                             "new_mpg": round(new_mpg, 1),
                             "new_share": round(new_mpg / sum(float(x["mpg"]) for x in rows), 4),
                             "delta_share": round(new_mpg / sum(float(x["mpg"]) for x in rows) - base, 4),
                             "status": "available"})
    return {"club": club, "missing": [r["player"] for r in out_rows], "rows": rows_out,
            "vacated_mpg": round(vacated, 1), "rule": RULE_TEXT}


RULE_TEXT = ("Top-8 shares = mpg / Σ(top-8 mpg). Replacement shares: each out player's mpg is "
             "redistributed to the remaining players proportionally to their own mpg "
             "(new_mpg_j = mpg_j + Σ_out mpg_i × mpg_j / Σ_avail mpg_k). Mechanical rule, no fit.")
