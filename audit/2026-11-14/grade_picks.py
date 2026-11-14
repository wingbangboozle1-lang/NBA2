"""Score the committed pre-tip picks against the official 11/13 finals captured 2026-11-14.

    python3 audit/2026-11-14/grade_picks.py

Why this is out-of-sample rather than a backtest: nba2/data/picks.json was committed
2026-11-13 22:36:46 UTC (commit d04bdc3, its only commit) and the earliest 11/13 tip was
00:00 UTC 2026-11-14, so the file existed 83 minutes before any game it picks had started.
Nothing in it could have seen a result.

What is measured: win/loss per strategy, hit rate, a Wilson interval, and a one-sided
binomial test against a fair coin. What is NOT measured: profit. No signal in the file
carries a price (there is no `american_odds` field anywhere in it), and a PnL number would
have to assume -110 for every leg — that is an invention, so the field stays null.

Writes audit/2026-11-14/graded_picks.json. Read-only over the repository.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
CAP = json.loads((HERE / "official_inputs_2026-11-14.json").read_text())
FINALS = {f["game_id"]: f for f in CAP["finals_2026_11_13"]}


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))


def sign_test_p(k: int, n: int):
    """P(X >= k) under a fair coin, one-sided: the test for 'skill or luck'."""
    if n == 0:
        return None
    return round(sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n, 4)


def grade_ml(sel: str, g: dict):
    side = sel.replace("ML", "").strip().upper()
    if side == g["home"]:
        return "WIN" if g["home_margin"] > 0 else "LOSS"
    if side == g["away"]:
        return "WIN" if g["home_margin"] < 0 else "LOSS"
    return None


def grade_spread(sel: str, g: dict):
    """'MIA +6.5' / 'HOU +13.0' — side takes the points."""
    try:
        side, pts = sel.rsplit(" ", 1)
        pts = float(pts)
    except ValueError:
        return None
    side = side.strip().upper()
    if side == g["home"]:
        margin = g["home_margin"] + pts
    elif side == g["away"]:
        margin = -g["home_margin"] + pts
    else:
        return None
    return "WIN" if margin > 0 else "LOSS" if margin < 0 else "PUSH"


def main() -> int:
    picks = json.loads((ROOT / "nba2/data/picks.json").read_text())
    lines = {l["game_id"]: l for l in picks["lines"]}

    games = {}
    for gid, f in FINALS.items():
        L = lines.get(gid)
        g = {
            "game_id": gid, "date": "2026-11-13", "away": f["away"], "home": f["home"],
            "status": "GRADED", "final_away": f["away_pts"], "final_home": f["home_pts"],
            "ot": f["ot"], "home_margin": f["home_pts"] - f["away_pts"],
            "total_points": f["home_pts"] + f["away_pts"],
            "source": f["source"], "second_source": f["second_source"],
        }
        if L:
            g.update({
                "originated_spread_home": L["originated_spread"],
                "originated_total": L["originated_total_line"],
                "predicted_margin": L["predicted_margin"],
                "predicted_total": L["predicted_total"],
                "home_win_prob": L["home_win_prob"],
                "favorite": L["favorite"],
                "spread_abs_error": round(abs(L["predicted_margin"] - g["home_margin"]), 3),
                "total_abs_error": round(abs(L["originated_total_line"] - g["total_points"]), 3),
                "brier": round((L["home_win_prob"] - (1.0 if g["home_margin"] > 0 else 0.0)) ** 2, 6),
                "spread_side_result": ("home" if g["home_margin"] + L["originated_spread"] > 0
                                       else "away" if g["home_margin"] + L["originated_spread"] < 0
                                       else "push"),
            })
        games[gid] = g

    graded = [g for g in games.values() if "originated_spread_home" in g]
    n = len(graded)
    line_stats = {
        "n": n,
        "spread_mae": round(sum(g["spread_abs_error"] for g in graded) / n, 3),
        "total_mae": round(sum(g["total_abs_error"] for g in graded) / n, 3),
        "brier": round(sum(g["brier"] for g in graded) / n, 6),
        "naive_spread_mae_predict_zero_margin": round(sum(abs(g["home_margin"]) for g in graded) / n, 3),
        "naive_total_mae_predict_224": round(sum(abs(224.0 - g["total_points"]) for g in graded) / n, 3),
        "naive_brier_coinflip": round(sum((0.5 - (1.0 if g["home_margin"] > 0 else 0.0)) ** 2
                                          for g in graded) / n, 6),
        "spread_side_hits_vs_originated_closing_side": sum(
            1 for g in graded if g["spread_side_result"] == "home"),
        "interpretation": (
            "n=9. These are nine games, not a sample; every one of these numbers would move "
            "materially on a single result. They are published because they are real, and "
            "labelled as a demonstration because they cannot support a promotion."),
    }

    rows, summary = [], []
    seen_games = {}
    for s in picks["strategies"]:
        for sig in s["signals"]:
            gid_field = sig["game_id"]
            gids = [x.strip() for x in gid_field.split(";")]
            res, detail = None, []
            if sig.get("bet_type") == "parlay" or len(gids) > 1:
                legs = []
                for gid, leg in zip(gids, sig["selection"].split("+")):
                    g = games.get(gid)
                    if g is None:
                        legs.append({"game_id": gid, "result": "PENDING"})
                        continue
                    legs.append({"game_id": gid, "leg": leg.strip(),
                                 "result": grade_ml(leg.strip(), g)})
                pending = any(l["result"] == "PENDING" for l in legs)
                res = "PENDING" if pending else ("WIN" if all(l["result"] == "WIN" for l in legs) else "LOSS")
                detail = legs
                g = None
            else:
                g = games.get(gids[0])
                if g is not None and g["status"] == "GRADED":
                    sel = sig["selection"]
                    res = grade_spread(sel, g) if sig.get("bet_type") == "spread" or "+" in sel and not sel.endswith("ML") else grade_ml(sel, g)
            if g is not None:
                for gid in gids:
                    seen_games.setdefault(gid, set()).add(s["id"])
            rows.append({
                "strategy_id": s["id"], "strategy_type": s["type"], "bet_type": sig.get("bet_type"),
                "game_id": gid_field, "game": sig.get("game"), "selection": sig.get("selection"),
                "model_win_prob": sig.get("model_win_prob"),
                "spread_edge": sig.get("spread_edge"),
                "american_odds": sig.get("american_odds"),   # absent everywhere: no price was ever committed
                "status": "GRADED" if res in ("WIN", "LOSS", "PUSH") else ("PENDING" if res == "PENDING" else "UNGRADABLE"),
                "result": res,
                "legs": detail or None,
                "final": (f'{g["away"]} {g["final_away"]} @ {g["home"]} {g["final_home"]}' if g else None),
                "official_source": (g["source"] if g else "https://www.nba.com/schedule"),
                "profit_units": None,
                "profit_note": "null by policy: no price is committed in the file, so profit would require assuming -110",
            })
        mine = [r for r in rows if r["strategy_id"] == s["id"]]
        gd = [r for r in mine if r["status"] == "GRADED" and r["result"] in ("WIN", "LOSS")]
        w = sum(1 for r in gd if r["result"] == "WIN")
        summary.append({
            "strategy_id": s["id"], "name": s["name"], "type": s["type"],
            "signals_committed": len(mine), "graded": len(gd),
            "pending": sum(1 for r in mine if r["status"] == "PENDING"),
            "wins": w, "losses": len(gd) - w,
            "hit_rate": round(w / len(gd), 4) if gd else None,
            "wilson_low": wilson(w, len(gd))[0], "wilson_high": wilson(w, len(gd))[1],
            "sign_test_p_vs_coin": sign_test_p(w, len(gd)),
            "distinguishable_from_luck_at_5pct": (sign_test_p(w, len(gd)) or 1.0) < 0.05,
            "sample_adequate": len(gd) >= 30,
            "verdict": ("insufficient evidence — sample below the 30-settlement minimum"
                        if 0 < len(gd) < 30 else
                        "no settled games yet" if len(gd) == 0 else None),
        })

    overlaps = {gid: sorted(s) for gid, s in seen_games.items() if len(s) > 1}
    out = {
        "session": "arena/ab8743d8-nba2",
        "prediction_file": "nba2/data/picks.json",
        "prediction_commit": "d04bdc3",
        "prediction_committed_utc": "2026-11-13T22:36:46Z",
        "first_tip_utc": "2026-11-14T00:00:00Z",
        "minutes_existed_before_first_tip": 83,
        "official_sources": ["https://www.nba.com/games", "https://www.nba.com/schedule"],
        "seal_note": ("Not a sealed-ledger settlement: this file is not under data/raw/ledger. The claim "
                      "rests on the git commit timestamp and a one-commit history. Both sealed ledgers "
                      "start 2026-11-14 and correctly remain PENDING."),
        "pricing_note": ("No signal carries a price; `american_odds` is absent from every row. Win/loss "
                         "is measurable without a price, profit is not. PnL is therefore null everywhere."),
        "line_forecast": line_stats,
        "games": sorted(games.values(), key=lambda g: g["game_id"]),
        "strategies": summary,
        "signal_rows": rows,
        "same_game_picked_by_multiple_strategies": overlaps,
        "correlation_finding": (
            f"{len(overlaps)} of the 9 graded games were bet by more than one strategy at once. A "
            "leaderboard that sums per-strategy results therefore counts those games more than once; "
            "per-strategy hit rates are still valid, a portfolio return would not be."),
    }
    (HERE / "graded_picks.json").write_text(json.dumps(out, indent=2) + "\n")

    print(f"{n} graded games · spread MAE {line_stats['spread_mae']} vs "
          f"{line_stats['naive_spread_mae_predict_zero_margin']} for 'predict a tie' · "
          f"total MAE {line_stats['total_mae']} vs {line_stats['naive_total_mae_predict_224']} for '224 every time'")
    print(f"{'strategy':24s}{'graded':>7s}{'W-L':>8s}{'hit':>7s}{'p(coin)':>9s}  verdict")
    for s in summary:
        hit = f'{s["hit_rate"]:.3f}' if s["hit_rate"] is not None else "--"
        p = f'{s["sign_test_p_vs_coin"]:.3f}' if s["sign_test_p_vs_coin"] is not None else "--"
        wl = str(s["wins"]) + "-" + str(s["losses"])
        print(f'{s["strategy_id"]:24s}{s["graded"]:7d}{wl:>8s}{hit:>7s}{p:>9s}  {s["verdict"]}')
    print(f"games bet by >1 strategy: {len(overlaps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
