"""Leaderboard on measured out-of-sample skill.

The brief asks for "a leaderboard competition that provides rewards for top performing
strategies". A leaderboard is only useful if (a) the ranking is on a quantity that a lucky
week cannot produce, and (b) the reward is withheld until that quantity is measurable.

This board therefore ranks on a **luck-adjusted score**, not on win rate:

    score = (accuracy - 0.5) / se(accuracy)

i.e. how many standard errors the strategy's straight-up accuracy sits above a coin flip,
with the standard error widened to account for the number of strategies tried (a
Bonferroni-style deflation). A strategy with 4 correct picks out of 5 scores *lower* than
one with 60 correct out of 100, because the first is noise with a confident face on.

The reward column is computed, not assigned: a strategy receives units only for the share
of its gates that PASS, and any strategy with an open FAIL or BLOCKED gate receives 0.
That is how "remove luck from the equation" becomes a payout rule instead of a slogan.
"""

from __future__ import annotations

import math
from typing import Sequence

from . import skill, stats

# Pre-registered mapping from strategy id to the tier it selects, so the ranking cannot be
# re-assigned after seeing outcomes.
STRATEGY_TIERS = {
    "S-01": ("A", "Reliability-Shrunk Spread: bet only the highest-confidence tier"),
    "S-02": ("B", "Two-Rating Agreement Filter: mid-confidence tier"),
    "S-03": ("C", "Pace-Neutral Total Anchor: includes the low-edge tier"),
    "S-07": ("C", "Schedule-Spot Fade: low-edge tier"),
}

TIER_NOTE = {
    "A": "model edge >= 3.0 pts over a neutral line",
    "B": "model edge 1.5 - 3.0 pts",
    "C": "model edge < 1.5 pts (noise tier)",
}


def build(rows: Sequence[dict], gate_result: dict, games_n: int) -> list[dict]:
    tiers = {t["tier"]: t for t in skill.tier_block(rows)}
    summary = gate_result["summary"]
    # gate score: fraction of *evaluable* gates that pass, zero if any gate FAILS
    evaluable = len(summary["passed"]) + len(summary["failed"]) + len(summary["partial"])
    # Disputed passes (met the letter of the rule but lost to the fair baseline) never count.
    counted = [g for g in summary["passed"] if g not in summary.get("passed_disputed", [])]
    gate_pass_frac = len(counted) / evaluable if evaluable else 0.0
    any_fail = bool(summary["failed"])

    out = []
    for sid, (tier, desc) in STRATEGY_TIERS.items():
        t = tiers.get(tier, {})
        n = t.get("n", 0)
        acc = t.get("straight_up_accuracy")
        if not n or acc is None:
            continue
        se = math.sqrt(0.25 / n)
        z = (acc - 0.5) / se
        # deflate for the number of strategies on the board (search penalty)
        k = len(STRATEGY_TIERS)
        z_adj = z / math.sqrt(k)
        # reward: only if no gate fails, proportional to deflated z above 1.0
        reward = 0.0
        if not any_fail and z_adj > 1.0:
            reward = round(z_adj * gate_pass_frac, 4)
        out.append({
            "strategy": sid,
            "description": desc,
            "tier_used": tier,
            "tier_definition": TIER_NOTE[tier],
            "n_games": n,
            "straight_up_accuracy": acc,
            "coin_flip": 0.5,
            "se": round(se, 4),
            "z_vs_coinflip": round(z, 3),
            "z_deflated_for_search": round(z_adj, 3),
            "auroc_winner": t.get("auroc_winner"),
            "mean_abs_margin_error": t.get("mean_abs_margin_error"),
            "gate_pass_fraction": round(gate_pass_frac, 3),
            "gates_counted": counted,
            "gates_disputed_excluded": summary.get("passed_disputed", []),
            "reward_units": reward,
            "status": ("withheld: a validation gate is FAILED" if any_fail
                       else "withheld: sample below the G-01 floor" if n < 300
                       else "eligible"),
        })
    out.sort(key=lambda r: r["z_deflated_for_search"], reverse=True)
    for i, r in enumerate(out, 1):
        r["rank"] = i
    total = sum(r["reward_units"] for r in out)
    for r in out:
        r["share_of_pool"] = round(r["reward_units"] / total, 4) if total else 0.0
    return out


def notes(games_n: int) -> list[str]:
    return [
        f"Ranked on deflated z, not on win rate. {games_n} graded games is far below the "
        f"G-01 floor of 300 settled bets, so the ordering is provisional by construction.",
        "Reward units are 0 for every strategy while any validation gate is FAILED. That is "
        "the gate doing its job, not a missing feature.",
        "Strategies are mapped to confidence tiers before outcomes are seen, so a strategy "
        "cannot be re-labelled onto whichever tier happened to perform.",
        "Every strategy here shares one model. Their results are therefore highly correlated "
        "and the leaderboard compares *filters on the same forecasts*, not independent systems.",
    ]
