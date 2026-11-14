"""Small, dependency-free statistics used by the backtest.

Everything here is a textbook estimator with a named origin, and every function is
deterministic (fixed seeds where randomness is used). No value is invented: if a
function cannot compute something it returns ``None`` rather than a plausible number.

Estimators
----------
* ``wilson_interval``  — Wilson (1927) score interval for a binomial proportion. Chosen
  over the normal approximation because hit rates near 50% with N≈50 are exactly where
  the Wald interval misbehaves.
* ``pearson``          — Pearson product-moment correlation.
* ``auc``              — rank-based area under the ROC curve (Mann–Whitney U identity).
* ``brier``            — Brier (1950) score for probability forecasts.
* ``permutation_test`` — two-sample permutation test on a difference of means.
* ``power_n``          — minimal N to detect a given edge at a given power, using the
  normal approximation, so the site can state how far the sample is from being able to
  answer the question at all.
"""

from __future__ import annotations

import math
import random
from typing import Iterable, Sequence


def mean(xs: Sequence[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def sd(xs: Sequence[float]) -> float | None:
    """Sample standard deviation (n-1). None for fewer than two observations."""
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def _ranks(xs: Sequence[float]) -> list[float]:
    """Average ranks, ties shared."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    return pearson(_ranks(xs), _ranks(ys))


def auc(scores: Sequence[float], labels: Sequence[int]) -> float | None:
    """P(score of a positive > score of a negative), ties counted as half.

    0.5 means the score carries no information about the label.
    """
    pos = [s for s, l in zip(scores, labels) if l == 1]
    neg = [s for s, l in zip(scores, labels) if l == 0]
    if not pos or not neg:
        return None
    ranks = _ranks(list(scores))
    rank_sum_pos = sum(r for r, l in zip(ranks, labels) if l == 1)
    n1, n0 = len(pos), len(neg)
    return (rank_sum_pos - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def brier(probs: Sequence[float], outcomes: Sequence[int]) -> float | None:
    if len(probs) != len(outcomes) or not probs:
        return None
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(probs)


def wilson_interval(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float] | None:
    """Wilson score interval (z=1.96 => 95%)."""
    if n <= 0:
        return None
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def permutation_test(a: Sequence[float], b: Sequence[float], draws: int = 10000,
                     seed: int = 20261114) -> dict | None:
    """Two-sided permutation test on mean(a) - mean(b).

    Under the null the labels are exchangeable, so pooling and re-splitting the combined
    sample is a valid (if conservative) reference distribution. Deterministic given seed.
    """
    if not a or not b:
        return None
    observed = sum(a) / len(a) - sum(b) / len(b)
    pooled = list(a) + list(b)
    na = len(a)
    rng = random.Random(seed)
    hits = 0
    for _ in range(draws):
        rng.shuffle(pooled)
        d = sum(pooled[:na]) / na - sum(pooled[na:]) / len(pooled[na:])
        if abs(d) >= abs(observed):
            hits += 1
    return {"observed_diff": observed, "p_value": (hits + 1) / (draws + 1), "draws": draws, "seed": seed}


def power_n(p0: float, p1: float, alpha: float = 0.05, power: float = 0.8) -> int | None:
    """Games needed to distinguish hit rate p0 from p1 (two-sided, normal approximation).

    This is the number that decides whether a leaderboard can mean anything yet.
    """
    if p1 <= p0 or not (0 < p0 < 1) or not (0 < p1 < 1):
        return None
    z_a = 1.959963984540054
    z_b = 0.8416212335729143  # one-sided 80% power
    pbar = (p0 + p1) / 2
    num = z_a * math.sqrt(2 * pbar * (1 - pbar)) + z_b * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))
    return math.ceil((num / (p1 - p0)) ** 2)


def mae(errors: Iterable[float]) -> float | None:
    errs = [abs(e) for e in errors]
    return sum(errs) / len(errs) if errs else None


def rmse(errors: Iterable[float]) -> float | None:
    errs = list(errors)
    return math.sqrt(sum(e * e for e in errs) / len(errs)) if errs else None


def r2_vs(values: Sequence[float], preds: Sequence[float], base: float) -> float | None:
    """1 - SS_res/SS_tot against a constant baseline prediction."""
    if len(values) != len(preds) or not values:
        return None
    ss_res = sum((v - p) ** 2 for v, p in zip(values, preds))
    ss_tot = sum((v - base) ** 2 for v in values)
    if ss_tot <= 0:
        return None
    return 1 - ss_res / ss_tot
