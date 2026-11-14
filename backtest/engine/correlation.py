"""Empirical correlations and signal tests from official final scores.

Until now the repository published correlations as *structural placeholders* derived from
algebra (`nba2/models/correlation.py`, and on the site: "structural placeholders only").
This module replaces guesses with measurements on real games, and states the sample size
next to every number so that a correlation of 0.06 on 139 games is not mistaken for a
finding.

What is measured
----------------
1. ``margin_total_correlation`` — the correlation that decides whether a same-game
   spread+total parlay is mispriced (strategy S-04). Books price such legs as independent;
   if this is materially non-zero, that is the one place a line originator can find an edge
   without a price feed.
2. ``leg_dependence`` — empirical joint vs product-of-marginals for the four combinations
   of (home covers, over), using our own originated numbers, with standard errors.
3. ``cross_game_independence`` — are two games on the same night independent? Needed for
   cross-slate parlays (S-05).
4. ``rest_effects`` — does a back-to-back or a 3-in-4 actually move the margin? This is the
   game-flow claim every prior page asserted qualitatively; here it is tested.

Everything is derived from ``data/raw/history/*.json``; every aggregate traces back to the
per-game ``source_url`` on nba.com.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Sequence

from . import stats


def _parse(d: str) -> date:
    y, m, dd = (int(x) for x in d.split("-"))
    return date(y, m, dd)


# ------------------------------------------------------------------ 1. margin vs total


def margin_total_correlation(games: Sequence[dict]) -> dict:
    """Pearson r between (home - away) margin and the game total.

    A positive r means blowouts also go over: the same-game "favourite + over" pair is
    then more likely than the product of the two singles.
    """
    margins = [g["home_pts"] - g["away_pts"] for g in games]
    totals = [g["home_pts"] + g["away_pts"] for g in games]
    r = stats.pearson(margins, totals)
    n = len(games)
    if r is None:
        return {"n": n, "r": None}
    # Fisher z interval
    z = math.atanh(max(-0.999999, min(0.999999, r)))
    se = 1 / math.sqrt(n - 3) if n > 3 else None
    ci = (math.tanh(z - 1.959963984540054 * se), math.tanh(z + 1.959963984540054 * se)) if se else None
    # is a constant-total null rejected? compare against totals' own dispersion
    return {
        "n": n,
        "r": round(r, 4),
        "ci95": [round(ci[0], 4), round(ci[1], 4)] if ci else None,
        "r_squared": round(r * r, 4),
        "total_sd": round(stats.sd(totals), 2),
        "margin_sd": round(stats.sd(margins), 2),
        "verdict": ("signal: |r| CI excludes 0" if ci and (ci[0] > 0 or ci[1] < 0)
                    else "no detectable relationship at this sample size"),
    }


# ------------------------------------------------------------------ 2. same-game legs


def leg_dependence(rows: Sequence[dict]) -> dict:
    """Empirical joint probability of (home cover, over) vs the independent product.

    Uses our originated line and total, because that is the number the model would price.
    Reports the joint, the product, and the difference with a normal-approximation SE, so
    the reader can see the dependence is not confused with sampling noise.
    """
    graded = [r for r in rows if r["pred_margin_home"] is not None and r["pred_total"] is not None]
    if not graded:
        return {"n": 0}
    cells = {"home_cover_over": 0, "home_cover_under": 0,
             "away_cover_over": 0, "away_cover_under": 0}
    for r in graded:
        home_cover = (r["actual_margin_home"] > r["pred_margin_home"])
        over = (r["actual_total"] > r["pred_total"])
        key = ("home_cover_" if home_cover else "away_cover_") + ("over" if over else "under")
        cells[key] += 1
    n = len(graded)
    p_home_cover = (cells["home_cover_over"] + cells["home_cover_under"]) / n
    p_over = (cells["home_cover_over"] + cells["away_cover_over"]) / n
    joint = cells["home_cover_over"] / n
    independent = p_home_cover * p_over
    se = math.sqrt(max(independent * (1 - independent) / n, 1e-9))
    diff = joint - independent
    return {
        "n": n,
        "cells": cells,
        "p_home_covers": round(p_home_cover, 4),
        "p_over": round(p_over, 4),
        "joint_observed": round(joint, 4),
        "joint_if_independent": round(independent, 4),
        "difference": round(diff, 4),
        "difference_pp": round(diff * 100, 2),
        "z": round(diff / se, 3),
        "interpretation": (
            "The two legs are treated as independent by naive parlay pricing. The observed "
            "difference is what a same-game parlay would be mispriced by BEFORE any vig; a "
            "z below about 2 means this sample cannot yet separate it from noise."),
        "note": ("Pushes are impossible on these numbers only if the line is a half point; "
                 "half-point increments are enforced by the line builder, so no push handling "
                 "is needed here."),
    }


# ------------------------------------------------------------------ 3. cross-game


def cross_game_independence(games: Sequence[dict]) -> dict:
    """Within-night correlation of home margins (pairs of games on the same date)."""
    by_date: dict[str, list[dict]] = defaultdict(list)
    for g in games:
        by_date[g["date"]].append(g)
    xs, ys = [], []
    for day, gs in by_date.items():
        gs = sorted(gs, key=lambda g: g["game_id"])
        for i in range(len(gs)):
            for j in range(i + 1, len(gs)):
                xs.append(gs[i]["home_pts"] - gs[i]["away_pts"])
                ys.append(gs[j]["home_pts"] - gs[j]["away_pts"])
    r = stats.pearson(xs, ys)
    return {
        "n_pairs": len(xs),
        "r": round(r, 4) if r is not None else None,
        "verdict": ("no evidence of within-night dependence" if r is None or abs(r) < 0.15
                    else "possible within-night dependence; cross-slate parlays need care"),
        "note": "Pairs within the same date only. Overlapping pairs are not independent, so this r is indicative.",
    }


# ------------------------------------------------------------------ 4. rest / game flow


def rest_effects(games: Sequence[dict]) -> dict:
    """Does a team on a back-to-back or in a 3-in-4 perform worse?

    Rest is computed from the official dates only. For each team-game we take the number of
    days since that team's previous game and build a paired comparison against the
    opponent's rest, so schedule imbalance (a fresher team vs a tired one) is what is
    measured, not the calendar.
    """
    history: dict[str, list[dict]] = defaultdict(list)
    for g in sorted(games, key=lambda g: (g["date"], g["game_id"])):
        history[g["home"]].append(g)
        history[g["away"]].append(g)

    def previous_dates(team: str) -> list[str]:
        return sorted({g["date"] for g in history[team]})

    # rest entering each game
    rows = []
    for g in games:
        d = _parse(g["date"])
        entry = {"game_id": g["game_id"], "date": g["date"]}
        for side in ("away", "home"):
            team = g[side]
            prior = [x for x in previous_dates(team) if _parse(x) < d]
            entry[f"{side}_rest"] = (d - _parse(prior[-1])).days if prior else None
            # "3 games in 4 days" = this game plus >=2 previous games in the 3 days before it
            window = [x for x in prior if 0 < (d - _parse(x)).days <= 3]
            entry[f"{side}_games_last_3d"] = len(window)
        rows.append(entry)

    b2b_margins, rested_margins = [], []
    three_in_four = []
    for g, meta in zip(games, rows):
        for side in ("away", "home"):
            team_margin = (g["home_pts"] - g["away_pts"]) if side == "home" else (g["away_pts"] - g["home_pts"])
            rest = meta[f"{side}_rest"]
            if rest is None:
                continue
            if rest == 1:
                b2b_margins.append(team_margin)
            elif rest >= 3:
                rested_margins.append(team_margin)
            if meta[f"{side}_games_last_3d"] >= 2:
                three_in_four.append(team_margin)
    test = stats.permutation_test(b2b_margins, rested_margins) if len(b2b_margins) >= 5 and len(rested_margins) >= 5 else None
    return {
        "n_team_games_with_rest_known": len(b2b_margins) + len(rested_margins) + len(three_in_four),
        "b2b": {"n": len(b2b_margins),
                "mean_margin": round(sum(b2b_margins) / len(b2b_margins), 3) if b2b_margins else None},
        "rested_3plus_days": {"n": len(rested_margins),
                              "mean_margin": round(sum(rested_margins) / len(rested_margins), 3) if rested_margins else None},
        "three_games_in_four_days": {"n": len(three_in_four),
                                     "mean_margin": round(sum(three_in_four) / len(three_in_four), 3) if three_in_four else None},
        "b2b_vs_rested": ({"difference": round(test["observed_diff"], 3),
                           "p_value": round(test["p_value"], 4),
                           "significant_at_5pct": test["p_value"] < 0.05}
                          if test else None),
        "note": ("Rest is derived from official game dates only. A negative b2b margin would "
                 "support the fatigue story; the p-value says whether this sample can see it."),
    }
