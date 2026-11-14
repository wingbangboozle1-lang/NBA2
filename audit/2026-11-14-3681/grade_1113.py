"""Grade the originated-line model out-of-sample on the 2026-11-13 slate.

    python3 audit/2026-11-14-3681/grade_1113.py

This is the first graded card in the repository that is scored against **official**
final scores rather than against itself or against a synthetic draw.

Why this is a legitimate out-of-sample test
-------------------------------------------
* The only rating input is `data/raw/team_ratings_2026-11-13.json`, committed by an
  earlier session and retrieved 2026-11-13 22:35 UTC. The first 2026-11-13 tip was
  2026-11-14 00:00 UTC (7:00 PM ET). **Every one of the nine games is strictly after
  the snapshot.**
* That is not an assertion, it is checked: `verify_live.py` check C2-B proves
  `(ratings W-L) + (the nine results) == the official NBA.com standings read live on
  2026-11-14`, for 30/30 clubs. If the snapshot had contained any 11/13 game the
  identity would fail.
* No parameter is fitted on these nine games. sigma and HCA are re-fitted from the
  same committed snapshot by `nba2.models.ratings.calibrate`, exactly as the published
  build does.

What this is NOT
----------------
* It is **not** a pre-registered forward test. No sealed ledger covers 2026-11-13:
  `sealed-2026-11-13.json` holds predictions for 2026-11-14..11-16 and
  `sealed-2026-11-14.json` for 2026-11-14..11-17. The project began on the evening of
  2026-11-13 and the 11/13 slate was already live, so nothing was sealed for it.
  This is a walk-forward **backtest** on nine games, and it is labelled as one.
* It is **not** a betting result. No odds feed exists in this repository, so there is
  no price to beat, no ROI, no CLV and no stake. Only the accuracy of the number is
  measured.

The file it writes (`data/graded_2026-11-13.json`) is new; nothing pre-existing is
modified. The sealed ledgers are read for the record and never written.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backtest"))

from nba2 import config                       # noqa: E402
from nba2.models import lines as LN           # noqa: E402
from nba2.models import ratings as RT         # noqa: E402
from engine import skill, stats               # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "graded_2026-11-13.json"

FINALS = json.loads((RAW / "finals_2026-11-13.json").read_text())["games"]
SLATE = json.loads((RAW / "slate_2026-11-14_to_11-17.json").read_text())


def game_meta(gid: str) -> dict:
    cols = SLATE["columns"]
    for r in SLATE["records"]:
        if r[cols.index("game_id")] == gid:
            return dict(zip(cols, r))
    return {}


def main() -> int:
    model = RT.build(ROOT)
    cal = model.cal
    print(f"Calibration re-fitted from the committed snapshot: "
          f"sigma={cal.margin_sd:.4f}  hca={cal.hca_points:.4f}  "
          f"rmse_wins={cal.rmse_wins:.3f} (baseline {cal.rmse_baseline_wins:.3f})")

    rows = []
    for g in FINALS:
        meta = game_meta(g["game_id"])
        game = {
            "game_id": g["game_id"], "date": g["date"],
            "time_et": meta.get("time_et"),
            "away": g["away"], "home": g["home"],
            "arena": meta.get("arena"), "city": meta.get("city"), "state": meta.get("state"),
            "broadcast": meta.get("broadcast"), "cup_group": meta.get("cup_group"),
        }
        line = LN.price_game(model, game, {})   # injury-blind, as every published pick is

        actual_margin = g["home_margin"]        # home - away
        actual_total = g["total_pts"]
        pred_margin = line.margin               # raw expected home margin
        pred_total = line.total

        rows.append({
            "game_id": g["game_id"],
            "date": g["date"],
            "matchup": f"{g['away']} @ {g['home']}",
            "away": g["away"], "home": g["home"],
            "away_pts": g["away_pts"], "home_pts": g["home_pts"],
            "ot": g["note"] == "Final/OT",
            # our published number (half-point grid) and the raw model value behind it
            "our_spread_home": line.spread_home,
            "our_total_line": line.total_line,
            "pred_margin_home": None if pred_margin is None else round(pred_margin, 2),
            "pred_total": None if pred_total is None else round(pred_total, 2),
            "p_home": line.home_win_prob,
            "tier": line.tier,
            "stability": line.stability,
            # the truth
            "actual_margin_home": actual_margin,
            "actual_total": actual_total,
            "margin_error": None if pred_margin is None else round(pred_margin - actual_margin, 2),
            "total_error": None if pred_total is None else round(pred_total - actual_total, 2),
            "winner_correct": None if pred_margin is None else bool(
                (pred_margin > 0) == (actual_margin > 0)),
            "source_url": g["source_url"],
        })

    rows.sort(key=lambda r: r["game_id"])
    for r in rows:
        print(f"  {r['matchup']:12s} our spread {r['our_spread_home']:+.1f} "
              f"(pred {r['pred_margin_home']:+.2f})  actual {r['actual_margin_home']:+4d}   "
              f"err {r['margin_error']:+6.2f} | total our {r['our_total_line']} "
              f"actual {r['actual_total']:3d}  err {r['total_error']:+.2f}  "
              f"{'HIT' if r['winner_correct'] else 'MISS'}")

    acc = skill.accuracy_block(rows)
    ats = skill.ats_block(rows)
    gap = skill.baseline_gap(rows)

    # `skill.baseline_gap` requires n >= 10 and only tests the margin. The totals result is
    # the interesting one on this card, so run the same paired test on both, with the same
    # fixed seed and the same two-sided permutation logic.
    perms = {}
    for name, errs, base in (
        ("margin", [abs(r["margin_error"]) for r in rows],
         [abs(r["actual_margin_home"]) for r in rows]),
        ("total", [abs(r["total_error"]) for r in rows],
         [abs(r["actual_total"] - (sum(r2["actual_total"] for r2 in rows) / len(rows)))
          for r in rows]),
    ):
        t = stats.permutation_test(errs, base)
        perms[name] = {
            "n": len(errs),
            "mean_abs_error_model": round(sum(errs) / len(errs), 3),
            "mean_abs_error_baseline": round(sum(base) / len(base), 3),
            "improvement_points": round(sum(base) / len(base) - sum(errs) / len(errs), 3),
            "observed_diff": round(t["observed_diff"], 3),
            "p_value": round(t["p_value"], 4),
            "draws": t["draws"],
            "seed": t["seed"],
            "model_better": t["observed_diff"] < 0,
            "significant_at_5pct": t["p_value"] < 0.05,
            "note": ("Paired permutation of the sign of (model error - baseline error). "
                     "With n=%d the smallest attainable two-sided p is about %.4f, so a "
                     "null result here means 'not enough games', not 'no effect'."
                     % (len(errs), 2.0 / (2 ** len(errs)))),
        }

    # Luck separation: could a coin flip have done this? Wilson CI already answers the
    # hit-rate half; the permutation test answers the margin-error half.
    labels = [1 if r["actual_margin_home"] > 0 else 0 for r in rows]
    probs = [r["p_home"] for r in rows]
    n = len(rows)
    su_hits = sum(1 for r in rows if r["winner_correct"])

    # Sample size needed to call a 5-point edge real at 80% power.
    n_needed = stats.power_n(0.5, 0.55, 0.05, 0.8)

    # Would our own published spread have "covered" against the official result?
    cover = []
    for r in rows:
        line_home = r["our_spread_home"]
        if line_home is None:
            continue
        # home covers when actual home margin beats the (negative-when-favoured) line
        home_margin_vs_line = r["actual_margin_home"] - line_home
        cover.append({
            "game_id": r["game_id"], "matchup": r["matchup"],
            "our_spread_home": line_home,
            "actual_margin_home": r["actual_margin_home"],
            "home_margin_vs_line": round(home_margin_vs_line, 2),
            "result": "home covers" if home_margin_vs_line > 0 else (
                      "away covers" if home_margin_vs_line < 0 else "push"),
        })

    totals = [r["actual_total"] for r in rows]
    out = {
        "schema": "nba2.graded-card.v1",
        "slate_date": "2026-11-13",
        "n_games": n,
        "graded_at_utc": "2026-11-14T10:40:00Z",
        "kind": "walk-forward backtest (NOT a pre-registered ledger)",
        "point_in_time": {
            "ratings_snapshot": config.SNAPSHOT_RATINGS,
            "snapshot_retrieved_utc": "2026-11-13T22:35:00Z",
            "first_tip_utc": "2026-11-14T00:00:00Z",
            "lookahead": "none — the snapshot predates every tip; proven by the "
                         "ratings + results = official standings identity (30/30 clubs)",
            "why_not_sealed": "no sealed ledger contains 2026-11-13 games: sealed-2026-11-13.json "
                              "covers 11-14..11-16 and sealed-2026-11-14.json covers 11-14..11-17",
        },
        "calibration_used": {
            "margin_sd": round(cal.margin_sd, 4),
            "hca_points": round(cal.hca_points, 4),
            "rmse_wins": round(cal.rmse_wins, 3),
            "rmse_baseline_wins": round(cal.rmse_baseline_wins, 3),
            "note": "re-fitted from the committed snapshot by nba2.models.ratings.calibrate; "
                    "no parameter is fitted on the nine graded games",
        },
        "sources": {
            "finals": "https://www.nba.com/schedule?date=2026-11-14 (Week 4 grid, cards read Final)",
            "per_game": "one nba.com/game/<slug>-<id> URL per row",
            "ratings": str(ROOT / "data" / "raw" / config.SNAPSHOT_RATINGS),
        },
        "games": rows,
        "cover_vs_our_line": cover,
        "metrics": {
            **acc,
            "ats_self_consistency": ats,
            "margin_error_permutation_vs_zero_baseline": gap,
            "permutation_tests": perms,
            "n_games": n,
            "straight_up_hits": su_hits,
            "straight_up_note": ("Wilson 95 percent CI is the honest summary: with n="
                                 + str(n) + " the interval spans 50 percent, so a coin flip "
                                 "is not excluded."),
            "power_to_detect_55pct_at_80pct_power": n_needed,
            "power_note": ("N = " + str(n_needed) + " graded games are required before a 55 "
                           "percent hit rate could be distinguished from chance at 5 percent "
                           "significance with 80 percent power. This card has " + str(n) + "."),
            "mean_actual_total": round(sum(totals) / len(totals), 2),
            "home_win_rate_actual": round(sum(labels) / len(labels), 4),
        },
        "verdict": None,   # filled in below
    }

    beats_margin = acc.get("margin_mae_model", 1e9) < acc.get("margin_mae_baseline_zero", 0)
    beats_total = acc.get("total_mae_model", 1e9) < acc.get("total_mae_baseline_mean", 0)
    lo, hi = acc.get("straight_up_ci95", [0, 1])
    out["verdict"] = {
        "model_margin_mae": acc.get("margin_mae_model"),
        "baseline_margin_mae": acc.get("margin_mae_baseline_zero"),
        "model_beats_zero_margin_baseline": beats_margin,
        "model_total_mae": acc.get("total_mae_model"),
        "baseline_total_mae": acc.get("total_mae_baseline_mean"),
        "model_beats_mean_total_baseline": beats_total,
        "straight_up_accuracy": acc.get("straight_up_accuracy"),
        "straight_up_ci95": acc.get("straight_up_ci95"),
        "coin_flip_excluded": bool(lo > 0.5 or hi < 0.5),
        "auroc": acc.get("auroc_winner"),
        "brier_model": acc.get("brier"),
        "brier_baseline": acc.get("brier_baseline_50pct"),
        "permutation_tests": perms,
        "sample_sufficient_for_gates": False,
        "sample_note": ("n = " + str(n) + ". Gate G-01 requires 300 settled bets. No "
                        "strategy may be promoted and no reward may be paid on this sample, "
                        "and this card does not attempt to change that."),
    }

    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    print(json.dumps(out["verdict"], indent=2))
    print(f"margin MAE model {acc.get('margin_mae_model')} vs baseline "
          f"{acc.get('margin_mae_baseline_zero')}; total MAE model "
          f"{acc.get('total_mae_model')} vs baseline {acc.get('total_mae_baseline_mean')}")
    print(f"SU {su_hits}/{n} = {acc.get('straight_up_accuracy')} "
          f"(95% CI {acc.get('straight_up_ci95')}); AUROC {acc.get('auroc_winner')}; "
          f"Brier {acc.get('brier')} vs {acc.get('brier_baseline_50pct')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
