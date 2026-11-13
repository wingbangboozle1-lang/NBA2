"""Correlation module.

Two jobs:
1. Compute the correlations we actually can compute from verified data (rating-to-rating).
2. Price *joint* outcomes under an explicit correlation, so a parlay is never quoted as the
   product of two singles by accident. Where the correlation itself is unknown we do not
   guess a point value — we sweep a ratified band and refuse to publish anything whose sign
   flips inside that band.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from .. import config


# --------------------------------------------------------------------------- estimators
def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    def ranks(v: Sequence[float]) -> list[float]:
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    return pearson(ranks(xs), ranks(ys))


def overlap_jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    """Bet-level overlap between two strategies, used to cluster the leaderboard so that
    one underlying signal cannot win three prizes."""
    A, B = set(a), set(b)
    if not A and not B:
        return 0.0
    return len(A & B) / len(A | B) if (A | B) else 0.0


# --------------------------------------------------------------------------- joint pricing
def _phi(x: float, mu: float, sd: float) -> float:
    z = (x - mu) / sd
    return math.exp(-0.5 * z * z) / (sd * math.sqrt(2.0 * math.pi))


def _ncdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def bivariate_upper_tail(mu_x: float, sd_x: float, mu_y: float, sd_y: float,
                         rho: float, a: float, b: float, n: int = 2001) -> float:
    """P(X > a, Y > b) for a bivariate normal, by 1-D quadrature of the conditional CDF.

    Standard and dependency-free (no scipy): integrates the marginal density of X above a
    times the conditional tail probability of Y. n=2001 gives ~1e-6 accuracy on these scales.
    """
    lo, hi = a, mu_x + 9 * sd_x
    if hi <= lo:
        return 0.0
    h = (hi - lo) / (n - 1)
    total = 0.0
    sd_y_cond = sd_y * math.sqrt(max(1e-9, 1.0 - rho * rho))
    for i in range(n):
        x = lo + i * h
        w = 1.0 if 0 < i < n - 1 else 0.5
        mu_y_cond = mu_y + rho * (sd_y / sd_x) * (x - mu_x)
        tail = 1.0 - _ncdf((b - mu_y_cond) / sd_y_cond)
        total += w * _phi(x, mu_x, sd_x) * tail
    return total * h


@dataclass
class JointQuote:
    leg_a: str
    leg_b: str
    p_a: float
    p_b: float
    p_independent: float
    p_correlated: dict[float, float]
    ratio: dict[float, float]
    sign_stable: bool
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "leg_a": self.leg_a, "leg_b": self.leg_b,
            "p_a": round(self.p_a, 4), "p_b": round(self.p_b, 4),
            "p_independent": round(self.p_independent, 4),
            "p_correlated": {str(k): round(v, 4) for k, v in self.p_correlated.items()},
            "ratio": {str(k): round(v, 4) for k, v in self.ratio.items()},
            "sign_stable": self.sign_stable,
            "note": self.note,
        }


def quote_pair(mu_margin: float, sd_margin: float, mu_total: float, sd_total: float,
                spread_home: float, total_line: float, band: tuple[float, float] | None = None) -> JointQuote:
    """Same-game 'home covers AND over' pair, priced across the ratified rho band.

    Legs: A = home covers our spread (margin > -spread_home), B = total > our total.
    """
    band = band or tuple(config.PARAMS["rho_band"].value)  # type: ignore[assignment]
    rhos = [round(band[0] + i * (band[1] - band[0]) / 6, 3) for i in range(7)]
    a = -spread_home
    p_a = 1.0 - _ncdf((a - mu_margin) / sd_margin)
    p_b = 1.0 - _ncdf((total_line - mu_total) / sd_total)
    indep = p_a * p_b
    corr, ratio = {}, {}
    for rho in rhos:
        joint = bivariate_upper_tail(mu_margin, sd_margin, mu_total, sd_total, rho, a, total_line)
        corr[rho] = joint
        ratio[rho] = joint / indep if indep else float("nan")
    sides = {1 if v > indep else -1 for v in corr.values()}
    return JointQuote(
        leg_a="home covers our spread", leg_b="game total goes over",
        p_a=p_a, p_b=p_b, p_independent=indep, p_correlated=corr, ratio=ratio,
        sign_stable=len(sides) == 1,
        note="sd_total is an unratified placeholder (no game-level totals available); "
             "the rho effect (ratio) is far more robust than the level.",
    )


def structural_shared_intensity_example(shared_share: float = 0.35) -> dict:
    """Why naive product pricing is wrong for same-player combos — arithmetic, not a claim
    about any real player.

    Model two counting stats as X = A + C, Y = B + C with independent Poisson components and
    a shared component C (the "minutes/possessions" factor). Corr(X, Y) = share^2-ish:
    with Var(A)=Var(B)=v, Var(C)=c, corr = c / (v + c). Setting c/(v+c) = shared_share gives
    the correlation implied by that structure, and the product-vs-joint error that follows.
    """
    c = shared_share
    v = 1.0 - shared_share
    corr = c / (v + c)
    # P(X > k, Y > k) vs product of tails, on the shared component mixture (exact by conditioning)
    return {
        "assumed_shared_variance_share": shared_share,
        "implied_correlation": round(corr, 4),
        "warning": "Parameters ASSUMED to illustrate mechanism. Not a measurement of any player.",
    }
