"""Minutes redistribution.

The brief asks for, per club: the top-8 minutes shares, and the replacement shares
when a player is out. The arithmetic is implemented and tested here. The inputs are
**blank in this build** because no per-player minutes table was captured: the cells
are null and carry flag ``F-307``, and the page says so instead of inventing a
depth chart.

Model
-----
A club plays 240 player-minutes in a regulation game (48 x 5). With a roster of
``(player, minutes_per_game)`` ordered by minutes:

* ``share_i = minutes_i / total_rotation_minutes`` over the top 8, so the eight
  shares sum to the top-8 share of all minutes played.
* When player ``k`` is out, the freed minutes are split: incumbents absorb
  ``1 - NEXT_MAN_SHARE`` of them in proportion to their existing shares, and the
  first player outside the top 8 (the next man) absorbs ``NEXT_MAN_SHARE``. The
  replacement share for player ``i`` is its post-redistribution share.

``NEXT_MAN_SHARE`` is a declared constant, not a fitted one; it is published with
the rows so a reader can see exactly what was assumed.
"""

from __future__ import annotations

NEXT_MAN_SHARE = 0.35  # declared, not fitted: 35% of freed minutes to the 9th man
TOP_N = 8
TEAM_MINUTES = 240.0

# No per-player minutes table was captured this session - see official.BLOCKED.
ROSTERS: dict[str, list[tuple[str, float]]] = {}


def shares(roster: list[tuple[str, float]]) -> dict:
    if not roster:
        return {
            "top_n": TOP_N, "players": [], "total_minutes": None,
            "top8_minutes_share": None, "next_man_share": NEXT_MAN_SHARE,
            "available": False, "flag_id": "F-307",
            "reason": "no official per-player minutes captured",
        }
    top = sorted(roster, key=lambda r: -r[1])[:TOP_N]
    tot = sum(m for _, m in top)
    return {
        "top_n": TOP_N,
        "players": [{"player": p, "minutes": m, "share": round(m / TEAM_MINUTES, 4),
                     "share_of_top8": round(m / tot, 4) if tot else None} for p, m in top],
        "total_minutes": round(tot, 1),
        "top8_minutes_share": round(tot / TEAM_MINUTES, 4),
        "next_man_share": NEXT_MAN_SHARE,
        "next_man": sorted(roster, key=lambda r: -r[1])[TOP_N][0] if len(roster) > TOP_N else None,
        "available": True, "flag_id": None, "reason": None,
    }


def redistribute(roster: list[tuple[str, float]], out_player: str) -> dict:
    """Replacement shares for the remaining rotation when ``out_player`` is out."""
    if not roster:
        return {"out": out_player, "replacements": [], "available": False,
                "flag_id": "F-307", "reason": "no official per-player minutes captured"}
    top = sorted(roster, key=lambda r: -r[1])[:TOP_N]
    names = [p for p, _ in top]
    if out_player not in names:
        return {"out": out_player, "replacements": [], "available": False,
                "flag_id": "F-310", "reason": "player is not in the top-8 rotation"}
    freed = dict(top)[out_player]
    incumbents = [(p, m) for p, m in top if p != out_player]
    base = sum(m for _, m in incumbents)
    rows = []
    for p, m in incumbents:
        add = freed * (1 - NEXT_MAN_SHARE) * (m / base) if base else 0.0
        rows.append({"player": p, "minutes_before": m, "minutes_after": round(m + add, 2),
                     "share_before": round(m / TEAM_MINUTES, 4),
                     "replacement_share": round((m + add) / TEAM_MINUTES, 4),
                     "delta_share": round(add / TEAM_MINUTES, 4)})
    beyond = sorted(roster, key=lambda r: -r[1])[TOP_N:]
    if beyond:
        p, m = beyond[0]
        add = freed * NEXT_MAN_SHARE
        rows.append({"player": p, "minutes_before": m, "minutes_after": round(m + add, 2),
                     "share_before": round(m / TEAM_MINUTES, 4),
                     "replacement_share": round((m + add) / TEAM_MINUTES, 4),
                     "delta_share": round(add / TEAM_MINUTES, 4),
                     "next_man": True})
    return {"out": out_player, "freed_minutes": freed,
            "next_man_share": NEXT_MAN_SHARE, "replacements": rows,
            "available": True, "flag_id": None, "reason": None}


def team_block(team_abbr: str, out_players: list[str] | None = None) -> dict:
    roster = ROSTERS.get(team_abbr, [])
    return {
        "team": team_abbr,
        "shares": shares(roster),
        "out": [redistribute(roster, p) for p in (out_players or [])],
        "n_roster_rows": len(roster),
    }


if __name__ == "__main__":
    demo = [("A", 34.0), ("B", 31.0), ("C", 29.0), ("D", 27.0),
            ("E", 24.0), ("F", 22.0), ("G", 18.0), ("H", 16.0), ("I", 11.0)]
    print(shares(demo)["top8_minutes_share"])
    print(redistribute(demo, "A")["replacements"][0])
