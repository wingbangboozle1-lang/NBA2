"""Does the originated model beat a naive baseline, and is any of it luck?

Three questions, kept separate because conflating them is how sports models fool people:

Q1  Is the model's *number* closer to the truth than a naive rule?
    Measured with mean absolute error (MAE) and RMSE on the final margin and total,
    against a constant baseline (league-average margin / total) and a
    team-net-rating baseline with no home-court term. No prices, no vig, no ROI.

Q2  Is the *ranking* informative?
    AUC of the model's predicted margin on the actual winner. 0.5 = coin flip.
    AUC is used because it is invariant to scale and bias, so it cannot be inflated by
    tuning a constant.

Q3  Could the observed edge be luck?
    Wilson confidence interval on the hit rate, a permutation test against the baseline,
    and the N required for 80% power. A leaderboard with 8 games per strategy cannot
    rank strategies; this module says so numerically instead of asserting it.

Every function returns `None` rather than a fabricated value when the sample is empty.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from . import stats


def _outcome_winner(r) -> int:
    """1 if the home team won (regulation or overtime), else 0."""
    return 1 if r.actual_margin_home > 0 else 0


def accuracy_block(rows: Sequence[dict]) -> dict:
    graded = [r for r in rows if r["pred_margin_home"] is not None]
    if not graded:
        return {"n": 0, "note": "no gradeable games"}

    margin_errors = [r["margin_error"] for r in graded if r["margin_error"] is not None]
    total_errors = [r["total_error"] for r in graded if r["total_error"] is not None]
    actual_margins = [r["actual_margin_home"] for r in graded]
    actual_totals = [r["actual_total"] for r in graded]
    mean_total = sum(actual_totals) / len(actual_totals)

    # Baseline 1: constant zero margin (the naive "home wins by nothing" rule)
    base_zero_err = [0 - m for m in actual_margins]
    # Baseline 2: league-mean total, no team information
    base_total_err = [mean_total - t for t in actual_totals]

    labels = [1 if m > 0 else 0 for m in actual_margins]
    probs = [r["p_home"] for r in graded]

    straight_win = sum(1 for r, l in zip(graded, labels)
                       if (r["pred_margin_home"] > 0) == (l == 1))
    return {
        "n": len(graded),
        "margin_mae_model": round(stats.mae(margin_errors), 3),
        "margin_rmse_model": round(stats.rmse(margin_errors), 3),
        "margin_mae_baseline_zero": round(stats.mae(base_zero_err), 3),
        "margin_rmse_baseline_zero": round(stats.rmse(base_zero_err), 3),
        "margin_bias": round(sum(margin_errors) / len(margin_errors), 3),
        "total_mae_model": round(stats.mae(total_errors), 3),
        "total_rmse_model": round(stats.rmse(total_errors), 3),
        "total_mae_baseline_mean": round(stats.mae(base_total_err), 3),
        "total_bias": round(sum(total_errors) / len(total_errors), 3),
        "auroc_winner": round(stats.auc([r["pred_margin_home"] for r in graded], labels), 4),
        "brier": round(stats.brier(probs, labels), 4),
        "brier_baseline_50pct": round(stats.brier([0.5] * len(labels), labels), 4),
        "straight_up_accuracy": round(straight_win / len(graded), 4),
        "straight_up_ci95": [round(x, 4) for x in stats.wilson_interval(straight_win, len(graded))],
    }


def ats_block(rows: Sequence[dict]) -> dict:
    """Against-the-spread behaviour of our own line, plus the honest caveat.

    Because we originate the number, "covering our own line" only measures
    self-consistency. The market-free statistics in `accuracy_block` are the ones that
    answer whether the number is any good.
    """
    graded = [r for r in rows if r["pred_margin_home"] is not None]
    if not graded:
        return {"n": 0}
    hits = 0
    graded_n = 0
    pushes = 0
    for r in graded:
        line = r["pred_margin_home"]
        if line == 0:
            pushes += 1
            continue
        graded_n += 1
        lean_home = line > 0
        actual = r["actual_margin_home"]
        if actual == 0:
            pushes += 1
            continue
        if lean_home == (actual > 0):
            hits += 1
    ci = stats.wilson_interval(hits, graded_n) if graded_n else None
    return {
        "n": graded_n, "hits": hits, "pushes_reported": pushes,
        "hit_rate": round(hits / graded_n, 4) if graded_n else None,
        "ci95": [round(x, 4) for x in ci] if ci else None,
        "note": ("Self-consistency only: the line is ours, so this is not a market test. "
                 "No odds feed exists, so no ROI or CLV can be computed and none is shown."),
    }


def baseline_gap(rows: Sequence[dict]) -> dict:
    """Is the model's margin error smaller than the naive baseline's, by chance?"""
    a = [abs(r["margin_error"]) for r in rows if r["margin_error"] is not None]
    b = [abs(r["actual_margin_home"]) for r in rows if r["margin_error"] is not None]
    if len(a) < 10:
        return {"n": len(a), "note": "too few games for a meaningful test"}
    test = stats.permutation_test(a, b)
    # positive diff means the model's absolute error is LARGER than the baseline's
    better = test["observed_diff"] < 0
    return {
        "n": len(a),
        "mean_abs_error_model": round(sum(a) / len(a), 3),
        "mean_abs_error_baseline": round(sum(b) / len(b), 3),
        "observed_diff": round(test["observed_diff"], 3),
        "p_value": round(test["p_value"], 4),
        "draws": test["draws"],
        "seed": test["seed"],
        "model_better": better,
        "significant_at_5pct": test["p_value"] < 0.05,
    }


def tier_block(rows: Sequence[dict]) -> list[dict]:
    """Per-tier measured performance. Tiers must earn their names."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["pred_margin_home"] is not None:
            buckets[r["tier"]].append(r)
    out = []
    for tier in ("A", "B", "C", "BLOCKED"):
        b = buckets.get(tier, [])
        if not b:
            out.append({"tier": tier, "n": 0, "note": "no games in this tier in the sample"})
            continue
        errs = [abs(r["margin_error"]) for r in b]
        labels = [1 if r["actual_margin_home"] > 0 else 0 for r in b]
        correct = sum(1 for r in b if (r["pred_margin_home"] > 0) == (r["actual_margin_home"] > 0))
        ci = stats.wilson_interval(correct, len(b))
        out.append({
            "tier": tier, "n": len(b),
            "mean_abs_margin_error": round(sum(errs) / len(errs), 3),
            "auroc_winner": round(stats.auc([r["pred_margin_home"] for r in b], labels), 4),
            "straight_up_accuracy": round(correct / len(b), 4),
            "ci95": [round(x, 4) for x in ci],
        })
    return out


def power_block(edge_points: float = 1.0) -> list[dict]:
    """Games needed to detect a real edge, so 'not enough data' is a number."""
    baseline_hit = 0.5
    sigma_margin = 13.58  # the repo's fitted margin SD, used only to convert points to a rate
    from math import erf, sqrt
    p_edge = 0.5 * (1 + erf((edge_points / sigma_margin) / sqrt(2)))
    rows = []
    for e in (0.5, 1.0, 1.5, 2.0, 3.0):
        p = 0.5 * (1 + erf((e / sigma_margin) / sqrt(2)))
        n = stats.power_n(baseline_hit, p)
        rows.append({"edge_points": e, "implied_hit_rate": round(p, 4),
                     "games_needed_80pct_power": n})
    return rows


def naive_baselines(rows: Sequence[dict], games: Sequence[dict]) -> dict:
    """Grade the obvious rules on exactly the same games as the model.

    Without this, a 63% hit rate looks like skill when it may be nothing more than
    "the home team usually wins" (a real ~55% edge) plus "the better team usually wins".
    Every baseline here is point-in-time: it uses only results before the game's date.
    """
    by_date_net: dict[str, dict[str, float]] = {}
    running: dict[str, list[float]] = defaultdict(list)
    for date in sorted({g["date"] for g in games}):
        by_date_net[date] = {t: (sum(v) / len(v) if v else 0.0) for t, v in running.items()}
        for g in games:
            if g["date"] != date:
                continue
            running[g["away"]].append(g["away_pts"] - g["home_pts"])
            running[g["home"]].append(g["home_pts"] - g["away_pts"])

    graded = [r for r in rows if r["pred_margin_home"] is not None]
    home_win = sum(1 for r in graded if r["actual_margin_home"] > 0)
    # better pre-game net rating, ties -> home team
    net_correct = 0
    net_n = 0
    for r in graded:
        nets = by_date_net.get(r["date"], {})
        a, h = nets.get(r["away"]), nets.get(r["home"])
        if a is None or h is None:
            continue
        net_n += 1
        pick_home = h >= a
        if pick_home == (r["actual_margin_home"] > 0):
            net_correct += 1
    model_correct = sum(1 for r in graded if (r["pred_margin_home"] > 0) == (r["actual_margin_home"] > 0))
    n = len(graded)
    out = {
        "n_games": n,
        "always_home": {"hits": home_win, "rate": round(home_win / n, 4),
                        "ci95": [round(x, 4) for x in stats.wilson_interval(home_win, n)]},
        "better_net_rating": {"n": net_n, "hits": net_correct, "rate": round(net_correct / net_n, 4),
                              "ci95": [round(x, 4) for x in stats.wilson_interval(net_correct, net_n)]},
        "originated_model": {"n": n, "hits": model_correct, "rate": round(model_correct / n, 4),
                             "ci95": [round(x, 4) for x in stats.wilson_interval(model_correct, n)]},
    }
    # paired comparison: model vs better-net on games both cover
    pairs = []
    for r in graded:
        nets = by_date_net.get(r["date"], {})
        a, h = nets.get(r["away"]), nets.get(r["home"])
        if a is None or h is None:
            continue
        m = (r["pred_margin_home"] > 0) == (r["actual_margin_home"] > 0)
        b = (h >= a) == (r["actual_margin_home"] > 0)
        pairs.append((1.0 if m else 0.0, 1.0 if b else 0.0))
    if pairs:
        t = stats.permutation_test([p[0] for p in pairs], [p[1] for p in pairs])
        out["model_vs_better_net"] = {
            "observed_diff": round(t["observed_diff"], 4), "p_value": round(t["p_value"], 4),
            "model_better": t["observed_diff"] > 0, "significant_at_5pct": t["p_value"] < 0.05,
            "note": "difference in hit rate on the same games; paired values are not independent, so treat p as indicative",
        }
    return out


def calibration_table(rows: Sequence[dict], bins: int = 10) -> list[dict]:
    """Reliability table: when we said 70%, how often did it happen?

    An uncalibrated probability is not a probability; it is a ranking wearing a costume.
    """
    graded = [r for r in rows if r["p_home"] is not None]
    if not graded:
        return []
    out = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        b = [r for r in graded if lo <= r["p_home"] < hi or (i == bins - 1 and r["p_home"] == 1.0)]
        if not b:
            continue
        mean_p = sum(r["p_home"] for r in b) / len(b)
        hits = sum(1 for r in b if r["actual_margin_home"] > 0)
        ci = stats.wilson_interval(hits, len(b))
        out.append({"bin": f"{lo:.0%}-{hi:.0%}", "n": len(b),
                    "mean_predicted": round(mean_p, 4),
                    "observed_home_win_rate": round(hits / len(b), 4),
                    "ci95_low": round(ci[0], 4), "ci95_high": round(ci[1], 4),
                    "gap_pp": round((hits / len(b) - mean_p) * 100, 2)})
    return out
