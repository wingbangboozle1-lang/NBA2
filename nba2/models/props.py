"""Player-prop and prop-combo pricing.

The pricing math is complete and tested. The *inputs* are not available from an official
source in this repository, so nothing here produces a number for the site: `project()`
returns blank values plus the exact field list that unblocks it. This is intentional —
a prop model driven by invented usage rates is the single easiest way to lose money while
believing you did the work.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def factorial(n: int) -> int:
    return math.factorial(n)


def log_choose(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def negbinom_pmf(k: int, mean: float, var: float) -> float:
    """Negative binomial in mean/variance parameterisation (r, p) with var >= mean.

    Count stats (points, rebounds, assists) are over-dispersed relative to Poisson; using a
    Poisson understates the tails and therefore mis-prices every prop away from the line.
    """
    if var < mean or mean <= 0:
        var = max(var, mean * 1.0001)
    r = mean * mean / (var - mean)
    p = r / (r + mean)
    logp = log_choose(k + int(round(r)) - 1, k) if r == int(r) else (
        math.lgamma(k + r) - math.lgamma(r) - math.lgamma(k + 1))
    return math.exp(logp + r * math.log(p) + k * math.log1p(-p))


def p_over(line: float, mean: float, var: float, max_k: int = 200) -> float:
    """P(count > line). Half-point lines make this exact; integer lines push on the number."""
    lo = int(math.floor(line)) + 1
    return min(1.0, max(0.0, sum(negbinom_pmf(k, mean, var) for k in range(lo, max_k + 1))))


def implied_minutes(line: float, rate_per_min: float) -> float | None:
    """Minutes a player must play to hit the line at a given per-minute rate."""
    if not rate_per_min:
        return None
    return line / rate_per_min


@dataclass
class PropQuote:
    player: str
    team: str
    market: str
    line: float | None
    projection: float | None
    projection_var: float | None
    p_over: float | None
    minutes_floor: float | None
    status: str
    missing_inputs: list[str]

    def as_dict(self) -> dict:
        return self.__dict__.copy()


MISSING_PROP_INPUTS = [
    "official per-player minutes, usage and on/off per 100 (stats.nba.com boxedgamelog/boxscoring)",
    "bookmaker prop lines and prices (no licensed odds feed connected)",
    "rotation depth charts per game (no official source publishes them pre-tip)",
    "per-minute production rates by opponent (requires the game-level join above)",
]


def blocked_quote(player: str, team: str, market: str) -> PropQuote:
    """The only quote this session can honestly produce."""
    return PropQuote(
        player=player, team=team, market=market, line=None, projection=None,
        projection_var=None, p_over=None, minutes_floor=None,
        status="BLOCKED — no official player-level input",
        missing_inputs=list(MISSING_PROP_INPUTS),
    )


def combo_correlation_effect(p_a: float, p_b: float, rho: float,
                             sd_a: float = 0.5, sd_b: float = 0.5) -> dict:
    """How a same-player combo's true joint probability departs from p_a * p_b.

    Uses the normal-copula approximation so the only free parameter is rho, which we sweep.
    Returns the naive price, the correlated price and the multiplicative error a bettor eats
    by treating the legs as independent.
    """
    from .correlation import _ncdf

    za, zb = -_inv_ncdf(p_a) if p_a < 1 else 0.0, -_inv_ncdf(p_b) if p_b < 1 else 0.0
    rho = max(-0.99, min(0.99, rho))
    sd_cond = math.sqrt(max(1e-9, 1.0 - rho * rho))
    # P(Za > za, Zb > zb) for standard bivariate normal with correlation rho
    n = 1201
    lo, hi = za, za + 12.0
    h = (hi - lo) / (n - 1)
    total = 0.0
    for i in range(n):
        z = lo + i * h
        w = 1.0 if 0 < i < n - 1 else 0.5
        cond_mean = rho * z
        tail = 1.0 - _ncdf((zb - cond_mean) / sd_cond)
        total += w * math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi) * tail
    joint = total * h
    indep = p_a * p_b
    return {
        "rho": rho,
        "p_a": p_a, "p_b": p_b,
        "independent_product": round(indep, 6),
        "correlated_joint": round(joint, 6),
        "error_factor": round(joint / indep, 4) if indep else None,
        "fair_decimal_independent": round(1 / indep, 4) if indep else None,
        "fair_decimal_correlated": round(1 / joint, 4) if joint else None,
    }


def _inv_ncdf(p: float) -> float:
    from .gates import inv_norm_cdf
    return inv_norm_cdf(p)


def parlay_pnl_table(legs: list[dict], joint_prob: float, price: float) -> dict:
    """Economic bottom line for a parlay priced as if legs were independent.

    `legs` must each carry {name, p}. `price` is the decimal price actually offered.
    """
    indep = 1.0
    for l in legs:
        indep *= l["p"]
    ev_true = joint_prob * price - 1.0
    ev_naive = indep * price - 1.0
    return {
        "legs": len(legs),
        "independent_prob": round(indep, 5),
        "true_prob": round(joint_prob, 5),
        "price": price,
        "ev_if_priced_naively": round(ev_naive, 5),
        "ev_honest": round(ev_true, 5),
        "verdict": ("PARLAY IS OVER-PRICED TO US (value)" if ev_true > 0 else
                    "no value at this price"),
    }
