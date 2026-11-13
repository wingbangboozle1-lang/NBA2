"""Validation gates. Every gate is evaluated against a *measurement*; a missing measurement
is reported as BLOCKED, never as PASS and never as 0.

Statistics implemented here use the standard library only (no scipy) so the whole pipeline
is reproducible in a bare environment.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Sequence

from .. import config


# --------------------------------------------------------------------------- normal bits
def inv_norm_cdf(p: float) -> float:
    """Acklam's rational approximation of the inverse standard normal CDF (|err| < 1.15e-9)."""
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
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def stdev(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def skewness(xs: Sequence[float]) -> float:
    n = len(xs)
    if n < 3:
        return float("nan")
    m, s = mean(xs), stdev(xs)
    if not s:
        return 0.0
    return (n / ((n - 1) * (n - 2))) * sum(((x - m) / s) ** 3 for x in xs)


def kurtness(xs: Sequence[float]) -> float:
    """Excess kurtosis (Fisher)."""
    n = len(xs)
    if n < 4:
        return float("nan")
    m, s = mean(xs), stdev(xs)
    if not s:
        return 0.0
    t = sum(((x - m) / s) ** 4 for x in xs) / n
    return t - 3.0


def bootstrap_ci(xs: Sequence[float], n: int = 10000, seed: int = 11, alpha: float = 0.05) -> tuple[float, float, float]:
    """Percentile bootstrap for the mean. Returns (point, lo, hi). Deterministic: fixed seed."""
    if not xs:
        return (float("nan"),) * 3  # type: ignore[return-value]
    rng = random.Random(seed)
    m = len(xs)
    means = []
    for _ in range(n):
        sample = [xs[rng.randrange(m)] for _ in range(m)]
        means.append(sum(sample) / m)
    means.sort()
    lo = means[int((alpha / 2) * n)]
    hi = means[int((1 - alpha / 2) * n) - 1]
    return mean(xs), lo, hi


def t_stat(xs: Sequence[float]) -> float:
    n = len(xs)
    if n < 2:
        return float("nan")
    s = stdev(xs)
    return mean(xs) / (s / math.sqrt(n)) if s else float("nan")


def holm(pvals: Sequence[tuple[str, float]]) -> list[tuple[str, float, bool]]:
    """Holm-Bonferroni. Input [(id, p)], output [(id, adjusted_p, reject_at_alpha)]."""
    alpha = 0.05
    ordered = sorted(pvals, key=lambda kv: kv[1])
    n = len(ordered)
    out, running = [], 0.0
    for i, (k, p) in enumerate(ordered):
        adj = min(1.0, max(p * (n - i), running))
        running = adj
        out.append((k, adj, adj <= alpha))
    return sorted(out, key=lambda r: [k for k, _ in pvals].index(r[0]))


def deflated_sharpe(sr: float, n_trials: int, n_obs: int, xs: Sequence[float] | None = None) -> float:
    """Probability the observed Sharpe beats the best-of-N-trials Sharpe expected under no skill.

    Bailey & Lopez de Prado construction: DSR = Phi( (SR - E[max SR]) * sqrt(T-1) /
    sqrt(1 - gamma3*SR + (gamma4-1)/4 * SR^2) ).
    """
    if n_obs < 3 or not math.isfinite(sr):
        return float("nan")
    gamma = 0.5772156649
    # variance of SR across trials: use supplied distribution, else the normal-theory
    # approximation Var(SR_hat) ~ (1 + SR^2/2)/T
    var_sr = (1.0 + sr * sr / 2.0) / n_obs
    z_hi = inv_norm_cdf(1.0 - 1.0 / max(n_trials, 2))
    z_lo = inv_norm_cdf(1.0 - 1.0 / (math.e * max(n_trials, 2)))
    e_max = math.sqrt(var_sr) * ((1 - gamma) * z_hi + gamma * z_lo)
    g3 = skewness(xs) if xs else 0.0
    g4 = kurtness(xs) + 3.0 if xs else 3.0
    denom = math.sqrt(max(1e-12, 1 - (g3 or 0.0) * sr + ((g4 - 1.0) / 4.0) * sr * sr))
    return 0.5 * (1 + math.erf(((sr - e_max) * math.sqrt(n_obs - 1)) / (denom * math.sqrt(2.0))))


def brier(probs: Sequence[float], outcomes: Sequence[int]) -> float:
    if len(probs) != len(outcomes) or not probs:
        return float("nan")
    return sum((p - y) ** 2 for p, y in zip(probs, outcomes)) / len(probs)


def log_loss(probs: Sequence[float], outcomes: Sequence[int], eps: float = 1e-6) -> float:
    if len(probs) != len(outcomes) or not probs:
        return float("nan")
    tot = 0.0
    for p, y in zip(probs, outcomes):
        p = min(1 - eps, max(eps, p))
        tot += y * math.log(p) + (1 - y) * math.log(1 - p)
    return -tot / len(probs)


def calibration_slope_intercept(probs: Sequence[float], outcomes: Sequence[int], bins: int = 10) -> tuple[float, float]:
    """Regression of realised frequency on predicted probability across equal-count bins."""
    pts = sorted(zip(probs, outcomes))
    n = len(pts)
    if n < bins * 3:
        return (float("nan"), float("nan"))
    xs, ys = [], []
    for i in range(bins):
        chunk = pts[i * n // bins:(i + 1) * n // bins]
        xs.append(mean([p for p, _ in chunk]))
        ys.append(mean([o for _, o in chunk]))
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    slope = num / den if den else float("nan")
    return (slope, my - slope * mx)


# --------------------------------------------------------------------------- gate engine
PASS, FAIL, BLOCKED, AT_RISK = "PASS", "FAIL", "BLOCKED", "AT-RISK"


@dataclass
class GateResult:
    gate_id: str
    name: str
    result: str
    measured: str
    reason: str

    def as_dict(self) -> dict:
        return {"gate_id": self.gate_id, "name": self.name, "result": self.result,
                "measured": self.measured, "reason": self.reason}


def evaluate(m: dict) -> list[GateResult]:
    """Evaluate all gates from a measurement dict.

    `m` keys are optional; absent keys mean the measurement does not exist yet, which is
    BLOCKED - explicitly not a pass and not a zero.
    """
    out: list[GateResult] = []

    n = m.get("settled_bets")
    need = config.GATES[0]["threshold"]
    out.append(GateResult("G-01", "Sample size",
                          PASS if (n is not None and n >= need) else BLOCKED,
                          f"{n if n is not None else 'not measured'} settled bets (need {need})",
                          "Ledger opens with the 2026-11-13 slate; nothing has settled yet."))

    clv = m.get("clv_points")
    clv_ci = m.get("clv_ci")
    if clv is None or clv_ci is None:
        out.append(GateResult("G-02", "Closing line value", BLOCKED, "no market prices captured",
                              "CLV cannot be computed without an odds feed (R-101). This blocks promotion."))
    else:
        out.append(GateResult("G-02", "Closing line value",
                              PASS if (clv > 0 and clv_ci[0] > 0) else FAIL,
                              f"CLV {clv:+.2f} pts, 95% CI [{clv_ci[0]:+.2f}, {clv_ci[1]:+.2f}]", ""))

    br, slope, intercept = m.get("brier"), m.get("calibration_slope"), m.get("calibration_intercept")
    if br is None or slope is None or intercept is None:
        out.append(GateResult("G-03", "Probability calibration", BLOCKED,
                              "; ".join(f"{k}=not measured" for k, v in
                                        (("brier", br), ("slope", slope), ("intercept", intercept)) if v is None),
                              "Needs >= 100 settled games with official outcomes."))
    else:
        ok = br <= 0.245 and 0.85 <= slope <= 1.15 and -0.10 <= intercept <= 0.10
        out.append(GateResult("G-03", "Probability calibration", PASS if ok else FAIL,
                              f"Brier {br:.4f}, slope {slope:.3f}, intercept {intercept:+.3f}", ""))

    mae, mae_base = m.get("line_mae"), m.get("baseline_mae")
    if mae is None or mae_base is None:
        out.append(GateResult("G-04", "Line accuracy vs baselines", BLOCKED, "no settled games",
                              "Requires official final scores for games in the sealed ledger."))
    else:
        ok = mae_base - mae >= 0.30
        out.append(GateResult("G-04", "Line accuracy vs baselines", PASS if ok else FAIL,
                              f"model MAE {mae:.2f} vs baseline {mae_base:.2f} (need >= 0.30 gain)", ""))

    roi_ci, tt = m.get("roi_ci"), m.get("t_stat")
    if roi_ci is None or tt is None:
        out.append(GateResult("G-05", "Luck removal", BLOCKED, "no settled bets",
                              "Bootstrap CI + t-stat on settled PnL; sign must survive luck adjustment."))
    else:
        ok = tt >= 2.0 and roi_ci[0] > 0 and m.get("luck_adjusted_sign_match", False)
        out.append(GateResult("G-05", "Luck removal", PASS if ok else FAIL,
                              f"t={tt:.2f}, ROI 95% CI [{roi_ci[0]:+.3%}, {roi_ci[1]:+.3%}]", ""))

    dsr, n_trials = m.get("deflated_sharpe"), m.get("n_trials")
    if dsr is None or n_trials is None:
        out.append(GateResult("G-06", "Multiple-testing control", BLOCKED, "no trial ledger",
                              "Every evaluation attempt must be counted (S-11 suggestion); "
                              "without the trial count the correction is meaningless."))
    else:
        out.append(GateResult("G-06", "Multiple-testing control", PASS if dsr > 0.95 else FAIL,
                              f"Deflated Sharpe {dsr:.3f} over {n_trials} trials", ""))

    pl, deg = m.get("point_in_time_verified"), m.get("holdout_degradation")
    if pl is False:
        out.append(GateResult("G-07", "Walk-forward, no lookahead", AT_RISK, "snapshot is not point-in-time",
                              "A single as-of standings table leaks future games for teams that play "
                              "early in the window. Only forward predictions are clean."))
    elif deg is None:
        out.append(GateResult("G-07", "Walk-forward, no lookahead", BLOCKED, "no holdout", ""))
    else:
        out.append(GateResult("G-07", "Walk-forward, no lookahead", PASS if deg <= 0.25 else FAIL,
                              f"holdout degradation {deg:.1%}", ""))

    st = m.get("min_stability")
    if st is None:
        out.append(GateResult("G-08", "Parameter robustness", BLOCKED, "not computed", ""))
    else:
        out.append(GateResult("G-08", "Parameter robustness", PASS if st >= 0.90 else FAIL,
                              f"worst published side-stability {st:.0%} (need >= 90%)", ""))

    surv = m.get("survives_costs")
    if surv is None:
        out.append(GateResult("G-09", "Cost and capacity", BLOCKED,
                              f"reference price {config.REFERENCE_PRICE} is a placeholder, not a quote",
                              "Cannot net out vig we have never seen."))
    else:
        out.append(GateResult("G-09", "Cost and capacity", PASS if surv else FAIL,
                              "modelled at -110 with 25% Kelly and 1% cap" if surv else "fails at -110", ""))

    ab = m.get("injury_blind_share")
    if ab is None:
        out.append(GateResult("G-10", "Availability-adjustment guardrail", BLOCKED, "no injury join", ""))
    else:
        out.append(GateResult("G-10", "Availability-adjustment guardrail",
                              PASS if ab < 1.0 else AT_RISK,
                              f"{ab:.0%} of published games are injury-blind",
                              "Every game is injury-blind because player-level minutes data is absent; "
                              "Tier A is therefore suppressed across the whole slate."))
    return out


def tier_for(results: list[GateResult]) -> str:
    if any(r.result == FAIL for r in results):
        return "rejected"
    if any(r.result in (AT_RISK,) for r in results):
        return "research"
    if all(r.result == PASS for r in results):
        return "promoted"
    return "research"
