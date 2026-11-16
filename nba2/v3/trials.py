"""Trial-count registry and multiple-testing correction (R-049, brief "remove luck").

A leaderboard that tries N strategies and rewards the best will produce a "winner" by pure
search, not by skill. The only defence is to charge the winner for the number of tries. That
charge is the **Deflated Sharpe Ratio** (Bailey & Lopez de Prado, 2014): the probability that
the observed Sharpe beats the best-of-N-trials Sharpe expected under no skill. It is a
function of three things — the observed Sharpe, the number of observations, and **the number
of trials** — and the third is exactly what was missing (G-06 sat at BLOCKED "no trial
ledger").

This module makes the trial count *real*:

* ``registry()`` returns the append-only list of every evaluation attempt in this window —
  one per registered strategy plus the model's own walk-forward backtest. It is built
  deterministically from ``nba2/config.py::STRATEGIES`` and the committed sealed ledger, so
  it re-derives exactly and can be re-checked line by line.
* ``deflated_sharpe()`` is the Bailey & Lopez de Prado construction (mirror of
  ``nba2/models/gates.py``; a test asserts the two agree).
* ``breakeven_sharpe()`` solves for the Sharpe a strategy must reach for its Deflated Sharpe
  to clear a threshold (0.95) given a trial count and an observation count. This is the
  number that turns "remove luck" into a concrete bar: with 9 trials over 139 observations,
  a strategy must show a Sharpe above X to pass G-06.

What is deliberately **blank**: the observed Sharpe itself. Sharpe is a function of settled
PnL, and there is no market price (gate G6) and no settled bet, so no return exists. The
registry and the bar are published; the observed SR / DSR per strategy is left blank and
flagged rather than invented.
"""

from __future__ import annotations

import math
from pathlib import Path

from . import official as O

ROOT = Path(__file__).resolve().parents[2]

# G-06 pass threshold on the Deflated Sharpe (matches nba2/config.py G-06 rule).
DSR_THRESHOLD = 0.95
# The walk-forward backtest's observation count (official finals used, point-in-time).
# Mirrors the measured skill run (README: 93/139 straight-up over 139 walk-forward games).
BACKTEST_N_OBS = 139


# --------------------------------------------------------------------------- normal bits
def _inv_norm_cdf(p: float) -> float:
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700400e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _skew(xs):
    if len(xs) < 3:
        return 0.0
    m = sum(xs) / len(xs)
    s = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    if not s:
        return 0.0
    return sum(((x - m) / s) ** 3 for x in xs) / len(xs)


def _kurt(xs):
    if len(xs) < 3:
        return 3.0
    m = sum(xs) / len(xs)
    s = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    if not s:
        return 3.0
    return sum(((x - m) / s) ** 4 for x in xs) / len(xs)


# --------------------------------------------------------------------------- DSR
def deflated_sharpe(sr: float, n_trials: int, n_obs: int, xs=None) -> float:
    """Bailey & Lopez de Prado Deflated Sharpe Ratio.

    DSR = Phi( (SR - E[max SR]) * sqrt(T-1) / sqrt(1 - g3*SR + (g4-1)/4 * SR^2) ).
    Mirrors nba2/models/gates.py::deflated_sharpe (a test asserts equality).
    """
    if n_obs < 3 or not math.isfinite(sr):
        return float("nan")
    gamma = 0.5772156649
    var_sr = (1.0 + sr * sr / 2.0) / n_obs
    z_hi = _inv_norm_cdf(1.0 - 1.0 / max(n_trials, 2))
    z_lo = _inv_norm_cdf(1.0 - 1.0 / (math.e * max(n_trials, 2)))
    e_max = math.sqrt(var_sr) * ((1 - gamma) * z_hi + gamma * z_lo)
    g3 = _skew(xs) if xs else 0.0
    g4 = _kurt(xs) if xs else 3.0
    denom = math.sqrt(max(1e-12, 1 - g3 * sr + ((g4 - 1.0) / 4.0) * sr * sr))
    return 0.5 * (1 + math.erf(((sr - e_max) * math.sqrt(n_obs - 1)) / (denom * math.sqrt(2.0))))


def breakeven_sharpe(n_trials: int, n_obs: int, target: float = DSR_THRESHOLD) -> float:
    """The Sharpe a strategy must reach for its DSR to clear ``target``.

    Solved by bisection on the (monotonic) DSR. This is the concrete bar G-06 imposes: it
    depends only on the trial count and the observation count, both of which are counted,
    not assumed.
    """
    lo, hi = -5.0, 5.0
    if deflated_sharpe(hi, n_trials, n_obs) < target:
        return float("nan")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if deflated_sharpe(mid, n_trials, n_obs) < target:
            lo = mid
        else:
            hi = mid
    return round(0.5 * (lo + hi), 4)


# --------------------------------------------------------------------------- registry
def registry() -> list[dict]:
    """Append-only list of every evaluation attempt in this window.

    One trial per registered strategy (its gate evaluation on the current slate) plus the
    model's own walk-forward backtest (a separate trial on the same prediction task). The
    registry is deterministic: it re-derives from ``nba2/config.py::STRATEGIES`` and the
    sealed-window metadata, so two builds produce identical rows.
    """
    from .. import config

    window = f"{O.WINDOW[0]}..{O.WINDOW[1]}"
    rows = []
    for s in config.STRATEGIES:
        rows.append({
            "trial_id": f"T-{s['id']}",
            "strategy_id": s["id"],
            "name": s["name"],
            "family": s["family"],
            "evaluation": "gate-score (this window)",
            "window": window,
            "as_of_utc": O.AS_OF_UTC,
            "n_predictions": None,  # filled from the sealed ledger where a pick exists
            "source": (s["sources"][0] if s.get("sources") else "derived: nba2/config.py"),
        })
    rows.append({
        "trial_id": "T-BACKTEST",
        "strategy_id": "MODEL",
        "name": "Walk-forward model backtest",
        "family": "meta",
        "evaluation": "walk-forward backtest (point-in-time)",
        "window": window,
        "as_of_utc": O.AS_OF_UTC,
        "n_predictions": BACKTEST_N_OBS,
        "source": "https://www.nba.com/games (official finals, committed in data/raw/history/)",
    })
    return rows


def n_trials() -> int:
    """The number of trials charged to the multiple-testing correction (G-06)."""
    return len(registry())


def summary() -> dict:
    """Aggregate for the page: the registry, the trial count, and the G-06 bar."""
    reg = registry()
    n = len(reg)
    # the bar G-06 imposes at the backtest's observation count
    bar = breakeven_sharpe(n, BACKTEST_N_OBS)
    # how the bar moves with sample size (the "how much history do we need" curve)
    curve = [{"n_obs": obs, "breakeven_sharpe": breakeven_sharpe(n, obs)}
             for obs in (30, 60, 139, 300, 600)]
    return {
        "n_trials": n,
        "n_strategies": n - 1,
        "backtest_n_obs": BACKTEST_N_OBS,
        "dsr_threshold": DSR_THRESHOLD,
        "breakeven_sharpe_139": bar,
        "sample_curve": curve,
        "observed_sharpe": None,
        "deflated_sharpe": None,
        "blank_reason": ("observed Sharpe is a function of settled PnL; there is no market "
                         "price (gate G6) and no settled bet, so no return exists. The bar is "
                         "published; the observed SR/DSR are blank and flagged, never invented."),
        "rule": ("DSR = Phi((SR - E[max SR under no skill]) * sqrt(T-1) / "
                 "sqrt(1 - g3*SR + (g4-1)/4 * SR^2)); E[max SR] grows with the trial count, "
                 "so more tries raise the bar. G-06 passes when DSR > 0.95."),
        "src": "nba2/config.py::STRATEGIES; data/raw/history/games_*.json (official finals)",
        "registry": reg,
    }
