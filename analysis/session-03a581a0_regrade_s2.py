"""Regrade the committed S2_SpreadValue signals on the *model's own* side.

Why this exists
---------------
`nba2/data/picks.json` publishes nine S2 selections whose sign is inverted
(suggestion S-26): the strategy is documented as "bet the model's favourite to
cover", but the emitted label named the underdog side in all nine games
(`POR +6.0` where the same file's line reads `POR -6.0`).

`audit/2026-11-14/grade_picks.py` grades the selections **exactly as published**
(it says so itself), so its S2 hit rate is a measurement of the wrong side of
the line. This script grades the same games on the side the model actually
named, using the same official finals, and prints both.

Read-only: writes nothing, changes nothing. Run:

    python3 analysis/session-03a581a0_regrade_s2.py
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "gp", ROOT / "audit/2026-11-14/grade_picks.py")
gp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gp)


def grade_side(team: str, pts: float, g: dict) -> str | None:
    """Same rule as grade_picks.grade_spread, applied to an explicit side."""
    if team == g["home"]:
        m = g["home_margin"] + pts
    elif team == g["away"]:
        m = -g["home_margin"] + pts
    else:
        return None
    return "WIN" if m > 0 else "LOSS" if m < 0 else "PUSH"


def main() -> int:
    picks = json.loads((ROOT / "nba2/data/picks.json").read_text())
    lines = {ln["game_id"]: ln for ln in picks["lines"]}
    strat = [s for s in picks["strategies"] if s["id"] == "S2_SpreadValue"][0]

    rows, w_pub, w_corr, n = [], 0, 0, 0
    for sig in strat["signals"]:
        gid = sig["game_id"]
        f = gp.FINALS.get(gid)
        if f is None:
            rows.append((sig["game"], sig["selection"], "PENDING", "-", "-"))
            continue
        L = lines[gid]
        g = {"home": f["home"], "away": f["away"],
             "home_margin": f["home_pts"] - f["away_pts"]}
        team, pts = sig["selection"].split()
        pub = grade_side(team, float(pts), g)

        fav = L["home"] if L["predicted_margin"] > 0 else L["away"]
        fav_spread = -abs(L["originated_spread"])
        corr = grade_side(fav, fav_spread, g)

        n += 1
        w_pub += pub == "WIN"
        w_corr += corr == "WIN"
        rows.append((sig["game"], sig["selection"], pub,
                     f"{fav} {fav_spread:+.1f}", corr))

    hdr = ("game", "published selection", "published result",
           "model's own side", "corrected result")
    widths = [max(len(str(r[i])) for r in rows + [hdr]) for i in range(5)]
    for r in [hdr] + rows:
        print("  ".join(str(v).ljust(widths[i]) for i, v in enumerate(r)))

    print(f"\ngraded n={n}   as published: {w_pub}/{n} wins"
          f"   on the model's own side: {w_corr}/{n} wins")
    print("NOTE: n<30 in both cases — neither figure supports a promotion; "
          "the point is that the published figure measures the wrong side.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
