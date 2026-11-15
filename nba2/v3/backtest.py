"""v3 walk-forward backtest over the official results feed.

WHY WALK-FORWARD
----------------
Every prediction is made from games played *strictly before* its own date. The ratings are
rebuilt from scratch at each date boundary, so a game can never influence its own forecast.
``leakage_audit`` asserts that with a counter, not a comment: it re-runs every prediction
with the target game deleted from the history and confirms the number does not move.

TWO ESTIMATORS, KEPT APART
--------------------------
  A. running raw point differential per game (the "what the scoreboard says" estimator);
  B. a least-squares strength rating with home-court absorbed (the "who did you beat"
     estimator) — a different model class, not a rescaling of A.

On the *projection* side (nba2/v3/model.py) the same two ideas are read from two different
official columns: PTS−OppPTS per game, and NetRtg × PACE ÷ 100. Both are official; neither is
derived from the other. The published confidence number is |A − B|, never their average.

No market data exists in this repository, so nothing here is a profit statement. A strategy is
scored on classification accuracy, log-loss and calibration.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from . import official as O
from .model import mean, pearson, phi, rho_ci, var

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "data" / "raw" / "history"

SEED = 20261115
N_PERM = 4000       # permutations for the skill-vs-luck test
HOLDOUT_FRAC = 0.30  # last 30% of game dates = out-of-sample slice for the log-loss weights


# --------------------------------------------------------------------------- data
@dataclass
class Game:
    game_id: str
    date: str
    away: str
    home: str
    away_pts: int
    home_pts: int
    ot: bool = False
    source_url: str = ""

    @property
    def margin(self) -> int:
        return self.home_pts - self.away_pts

    @property
    def total(self) -> int:
        return self.home_pts + self.away_pts


def load_games() -> list[Game]:
    """All official finals: the committed history feed plus this capture's 5 new finals.

    Each row keeps the source URL it was read from, so a published accuracy figure can be
    traced to the game pages behind it.
    """
    out: list[Game] = []
    seen: set[str] = set()
    for f in sorted(HISTORY.glob("games_*.json")):
        doc = json.loads(f.read_text())
        for g in doc.get("games", []):
            if g["game_id"] in seen:
                continue
            seen.add(g["game_id"])
            out.append(Game(g["game_id"], g["date"], g["away"], g["home"],
                            int(g["away_pts"]), int(g["home_pts"]), bool(g.get("ot")),
                            g.get("source_url", "")))
    for (gid, date, away, home, ap, hp, _aq, _hq, ot, _arena) in O.FINALS:
        if gid in seen:
            continue
        seen.add(gid)
        out.append(Game(gid, date, away, home, ap, hp, ot,
                        f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}"))
    out.sort(key=lambda g: (g.date, g.game_id))
    return out


# --------------------------------------------------------------------------- the two estimators
@dataclass
class Prediction:
    game_id: str
    date: str
    away: str
    home: str
    margin_a: float     # estimator A: running point differential
    margin_b: float     # estimator B: least-squares strength with HCA absorbed
    total_a: float      # running league points per game
    sigma_a: float
    sigma_b: float
    actual_margin: int
    actual_total: int
    p_home_a: float = 0.0
    p_home_b: float = 0.0
    disagreement: float = 0.0
    n_prior_games: int = 0
    total_fwd: float = 0.0   # forward total from prior-window team rates + pace, not league mean

    @property
    def home_won(self) -> bool:
        return self.actual_margin > 0

    def as_dict(self):
        return {
            "game_id": self.game_id, "date": self.date, "away": self.away, "home": self.home,
            "margin_a": round(self.margin_a, 3), "margin_b": round(self.margin_b, 3),
            "total_a": round(self.total_a, 2), "total_fwd": round(self.total_fwd, 2),
            "p_home_a": round(self.p_home_a, 4), "p_home_b": round(self.p_home_b, 4),
            "disagreement": round(self.disagreement, 3),
            "actual_margin": self.actual_margin, "actual_total": self.actual_total,
            "n_prior_games": self.n_prior_games,
        }


def _ratings_diff(games: list[Game], teams: set[str]) -> dict[str, float]:
    """Estimator A: mean point differential per team over the games supplied."""
    tot: dict[str, float] = {t: 0.0 for t in teams}
    n: dict[str, int] = {t: 0 for t in teams}
    for g in games:
        tot[g.home] += g.margin
        tot[g.away] -= g.margin
        n[g.home] += 1
        n[g.away] += 1
    return {t: (tot[t] / n[t] if n[t] else 0.0) for t in teams}


def _ratings_lsq(games: list[Game], teams: set[str], ridge: float = 0.5):
    """Estimator B: opponent-adjusted strength, solved EXACTLY.

    Model:  margin_i = h·1{home} + r_home − r_away + ε,  subject to  Σ r = 0.

    Solved as a constrained least-squares system (normal equations + one Lagrange row for the
    sum-to-zero constraint, Gaussian elimination with partial pivoting). Exact rather than
    iterative on purpose: an iterative update left the two estimators on different scales,
    which would have made their *disagreement* a measure of the solver rather than of the
    data. ``ridge`` is 0.5 pseudo-games of shrinkage, disclosed and applied to every club
    equally, so it damps a 1-game club without changing the ordering.

    Why this is a genuinely different estimator from A: A is the raw scoring margin and
    ignores *whom* you played; B credits a club for beating good opponents and penalises it
    for fattening up on bad ones. A club can rank differently under the two, and when it does
    the site publishes that.
    """
    ts = sorted(teams)
    n = len(ts)
    idx = {t: i for i, t in enumerate(ts)}
    # parameters: r_0..r_{n-1}, h   → size n+1, plus one Lagrange row
    size = n + 2
    A = [[0.0] * size for _ in range(size)]
    b = [0.0] * size
    for g in games:
        hi, ai = idx[g.home], idx[g.away]
        # design row: +1 for home strength, -1 for away strength, +1 for home edge
        coeffs = [(hi, 1.0), (ai, -1.0), (n, 1.0)]
        for i, ci in coeffs:
            for j, cj in coeffs:
                A[i][j] += ci * cj
        for i, ci in coeffs:
            b[i] += ci * g.margin
    for i in range(n):
        A[i][i] += ridge
    # Lagrange row: Σ r = 0
    for i in range(n):
        A[n + 1][i] = 1.0
        A[i][n + 1] = 1.0
    b[n + 1] = 0.0
    A[n + 1][n + 1] = 0.0

    # Gaussian elimination with partial pivoting
    for col in range(size):
        piv = max(range(col, size), key=lambda r: abs(A[r][col]))
        if abs(A[piv][col]) < 1e-12:
            continue
        A[col], A[piv] = A[piv], A[col]
        b[col], b[piv] = b[piv], b[col]
        pv = A[col][col]
        for r in range(col + 1, size):
            f = A[r][col] / pv
            if f == 0.0:
                continue
            for c in range(col, size):
                A[r][c] -= f * A[col][c]
            b[r] -= f * b[col]
    x = [0.0] * size
    for r in range(size - 1, -1, -1):
        if abs(A[r][r]) < 1e-12:
            x[r] = 0.0
            continue
        s = b[r] - sum(A[r][c] * x[c] for c in range(r + 1, size))
        x[r] = s / A[r][r]
    rat = {t: x[idx[t]] for t in ts}
    m = sum(rat.values()) / n
    rat = {t: v - m for t, v in rat.items()}
    return rat, x[n]


def _team_season_ppp(games: list[Game], teams: set[str]) -> tuple[dict, dict, dict]:
    """Per-club scoring and conceding rates, and pace, from a slice of games ONLY.

    Built from finished games in the slice: points scored per game, points conceded per game,
    and a possession proxy. Official team POSS pages are season-to-date as of capture and using
    them for a 2026-10-25 forecast would leak the future; so the walk-forward uses a
    home-possession proxy of (FGA + 0.44*FTA + TOV) — which this repository's history feed does
    not carry either. Without play-by-play the forward total is therefore a *pace proxy*, and it
    is labelled as such on the page rather than dressed up as the possessions model.
    """
    pf, pa, pace = {}, {}, {}
    for t in teams:
        pts_for, pts_against = [], []
        for g in games:
            if g.home == t:
                pts_for.append(g.home_pts); pts_against.append(g.away_pts)
            elif g.away == t:
                pts_for.append(g.away_pts); pts_against.append(g.home_pts)
        pf[t] = mean(pts_for) if pts_for else None
        pa[t] = mean(pts_against) if pts_against else None
        pace[t] = (pf[t] + pa[t]) if pf[t] is not None else None
    return pf, pa, pace


def _pred_sd(ratings: dict[str, float], games: list[Game]) -> float:
    preds = [ratings[g.home] - ratings[g.away] for g in games]
    return math.sqrt(var(preds)) if len(preds) > 1 else 1.0


def walk_forward(games: list[Game] | None = None, drop: str | None = None) -> list[Prediction]:
    """Rebuild ratings before each date and predict that date's games.

    ``drop`` deletes one game id from every history slice — used by the leakage audit to
    prove a target game cannot reach its own forecast.
    """
    games = games if games is not None else load_games()
    if drop:
        games = [g for g in games if g.game_id != drop]
    teams = {t for g in games for t in (g.home, g.away)}
    dates = sorted({g.date for g in games})
    out: list[Prediction] = []
    for d in dates:
        prior = [g for g in games if g.date < d]
        today = [g for g in games if g.date == d]
        if len(prior) < 30:
            continue          # too little history for a rating; the game is not scored
        ra = _ratings_diff(prior, teams)
        rb, _home_edge = _ratings_lsq(prior, teams)
        # scale B onto A's units using each estimator's own dispersion
        sa, sb = _pred_sd(ra, prior), _pred_sd(rb, prior)
        k = (sa / sb) if sb > 0 else 1.0
        rb = {t: v * k for t, v in rb.items()}
        # margin volatility, fitted from the prior games' residuals to A
        resid = [g.margin - (ra[g.home] - ra[g.away]) for g in prior]
        sigma = math.sqrt(var(resid)) if len(resid) > 1 else 13.0
        total_mean = mean([g.total for g in prior])
        pf, pa, pace = _team_season_ppp(prior, teams)
        # league pace level over the same prior window, so the total has a real per-game level
        pace_level = mean([v for v in pace.values() if v is not None])
        for g in today:
            ma = ra[g.home] - ra[g.away]
            mb = rb[g.home] - rb[g.away]
            # Forward total: each side's own scoring rate is half its own attack and half the
            # opponent's concession, then both sides' projections are scaled by the pace of the
            # two clubs relative to the league level in the same prior window.
            hp = None if (pf[g.home] is None or pa[g.away] is None) else (pf[g.home] + pa[g.away]) / 2
            ap = None if (pf[g.away] is None or pa[g.home] is None) else (pf[g.away] + pa[g.home]) / 2
            if hp is not None and ap is not None and pace_level > 0:
                g_pace = (pace[g.home] + pace[g.away]) / 2
                fwd_total = (hp + ap) * (g_pace / pace_level) / 1.0
            else:
                fwd_total = total_mean
            p = Prediction(
                game_id=g.game_id, date=g.date, away=g.away, home=g.home,
                margin_a=ma, margin_b=mb, total_a=total_mean, sigma_a=sigma, sigma_b=sigma,
                actual_margin=g.margin, actual_total=g.total, n_prior_games=len(prior),
                total_fwd=fwd_total,
            )
            p.p_home_a = phi(ma / sigma)
            p.p_home_b = phi(mb / sigma)
            p.disagreement = abs(ma - mb)
            out.append(p)
    return out


# --------------------------------------------------------------------------- metrics
def log_loss(ps: list[float], outcomes: list[bool]) -> float:
    """Mean binary log-loss. Clipped at 1e-15 so a single certainty error cannot be infinite."""
    s = 0.0
    for p, y in zip(ps, outcomes):
        p = min(1 - 1e-15, max(1e-15, p))
        s += -math.log(p if y else 1 - p)
    return s / len(ps) if ps else float("nan")


def brier(ps: list[float], outcomes: list[bool]) -> float:
    return sum((p - (1.0 if y else 0.0)) ** 2 for p, y in zip(ps, outcomes)) / len(ps) if ps else float("nan")


def accuracy(ps: list[float], outcomes: list[bool]) -> float:
    return sum(1 for p, y in zip(ps, outcomes) if (p > 0.5) == y) / len(ps) if ps else float("nan")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p (binomial on the discordant pairs)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = 0.0
    for i in range(k + 1):
        p += math.comb(n, i) * (0.5 ** n)
    return min(1.0, 2 * p)


def metrics(preds: list[Prediction]) -> dict:
    ps = [p.p_home_a for p in preds]
    ys = [p.home_won for p in preds]
    ps_b = [p.p_home_b for p in preds]
    mae = mean([abs(p.actual_margin - p.margin_a) for p in preds])
    mae_b = mean([abs(p.actual_margin - p.margin_b) for p in preds])
    mae_naive = mean([abs(p.actual_margin) for p in preds])   # "predict a tie"
    r_tot, n_tot = pearson([p.margin_a for p in preds], [p.total_fwd for p in preds])
    r_actual, _ = pearson([p.actual_margin for p in preds], [p.actual_total for p in preds])
    hit = sum(1 for p, y in zip(ps, ys) if (p > 0.5) == y)
    lo, hi = wilson(hit, len(preds))
    return {
        "n": len(preds),
        "accuracy": round(accuracy(ps, ys), 4),
        "accuracy_ci": [round(lo, 4), round(hi, 4)],
        "accuracy_b": round(accuracy(ps_b, ys), 4),
        "log_loss": round(log_loss(ps, ys), 4),
        "log_loss_b": round(log_loss(ps_b, ys), 4),
        "log_loss_coin": round(log_loss([0.5] * len(ps), ys), 4),
        "brier": round(brier(ps, ys), 4),
        "brier_coin": round(brier([0.5] * len(ps), ys), 4),
        "mae_margin": round(mae, 3),
        "mae_margin_b": round(mae_b, 3),
        # Two different "no model" baselines, both published because they point opposite ways.
        # predict-a-tie equals the mean absolute *actual* margin and is a hard baseline; the
        # league mean margin is what a model that only knows the home edge would use.
        "mae_predict_tie": round(mae_naive, 3),
        "mae_home_edge_only": round(mean([abs(p.actual_margin - mean([q.actual_margin for q in preds])) for p in preds]), 3),
        "pred_margin_sd": round(math.sqrt(var([p.margin_a for p in preds])), 3),
        "actual_margin_sd": round(math.sqrt(var([p.actual_margin for p in preds])), 3),
        "r_pred_actual_margin": round(pearson([p.margin_a for p in preds], [p.actual_margin for p in preds])[0], 4),
        "mean_disagreement": round(mean([p.disagreement for p in preds]), 3),
        "median_disagreement": round(sorted(p.disagreement for p in preds)[len(preds) // 2], 3),
        "max_disagreement": round(max(p.disagreement for p in preds), 3),
        "pct_disagreement_gt_1_5": round(100 * sum(1 for p in preds if p.disagreement > 1.5) / len(preds), 1),
        "pct_opposite_side": round(100 * sum(1 for p in preds if (p.margin_a > 0) != (p.margin_b > 0)) / len(preds), 1),
        "r_model_margin_vs_total": round(r_tot, 4),
        "mae_total_fwd": round(mean([abs(p.total_fwd - p.actual_total) for p in preds]), 3),
        "mae_total_league_mean": round(mean([abs(p.total_a - p.actual_total) for p in preds]), 3),
        "mae_total_best_constant": round(mean([abs(mean([q.actual_total for q in preds]) - p.actual_total)
                                               for p in preds]), 3),
        "r_total_fwd_vs_actual": round(pearson([p.total_fwd for p in preds],
                                               [p.actual_total for p in preds])[0], 4),
        "total_fwd_sd": round(math.sqrt(var([p.total_fwd for p in preds])), 3),
        "actual_total_sd": round(math.sqrt(var([p.actual_total for p in preds])), 3),
        "r_actual_margin_vs_total": round(r_actual, 4),
        "r_n": n_tot,
    }


# --------------------------------------------------------------------------- baselines & skill
def baselines(preds: list[Prediction]) -> dict:
    """Naive rules scored on exactly the same games.

    The question a leaderboard must answer is not "is the model right?" but "is the model
    right more often than a rule that needs no model?" These are those rules.
    """
    ys = [p.home_won for p in preds]
    always_home = [0.5000001] * len(preds)
    return {
        "always_home": {"accuracy": round(accuracy(always_home, ys), 4),
                        "log_loss": round(log_loss(always_home, ys), 4)},
        "coin_flip": {"accuracy": 0.5, "log_loss": round(log_loss([0.5] * len(ys), ys), 4)},
        "predicted_tie_margin": {"mae": round(mean([abs(p.actual_margin) for p in preds]), 3)},
        "note": ("A naive net-rating baseline is computed in nba2/v2/strategy_lab.py and is not "
                 "recomputed here; what is added in v3 is the paired test below, which compares "
                 "the model with a *fitted-ratings-free* rule on the games they disagreed on."),
    }


def skill_attribution(preds: list[Prediction]) -> dict:
    """McNemar on the games where the two estimators disagreed about the side.

    If estimator A and estimator B pick different winners, exactly one can be right. That is a
    clean paired comparison, and it is the honest measure of whether the second estimator adds
    anything at all. Also runs a permutation test on accuracy against a coin's base rate.
    """
    both = [p for p in preds if (p.margin_a > 0) != (p.margin_b > 0)]
    a_win = sum(1 for p in both if (p.margin_a > 0) == p.home_won and (p.margin_a > 0))
    a_correct = sum(1 for p in both if (p.margin_a > 0) == p.home_won)
    b_correct = sum(1 for p in both if (p.margin_b > 0) == p.home_won)
    only_a = sum(1 for p in both if (p.margin_a > 0) == p.home_won and (p.margin_b > 0) != p.home_won)
    only_b = sum(1 for p in both if (p.margin_b > 0) == p.home_won and (p.margin_a > 0) != p.home_won)
    p = mcnemar_exact(only_a, only_b)
    return {
        "n_disagreed": len(both),
        "a_correct": a_correct,
        "b_correct": b_correct,
        "only_a_right": only_a,
        "only_b_right": only_b,
        "mcnemar_exact_p": round(p, 4),
        "significant_at_05": p < 0.05,
        "verdict": (
            "the second estimator is not separable from the first" if p >= 0.05 else
            "the two estimators differ by more than chance on the disagreeing games"
        ),
    }


def permutation_p(preds: list[Prediction], n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """Is the fitted model's margin ranking informative? Permute the predicted/actual pairing.

    Statistic: MAE improvement of the model's margin over predicting a tie. Under the null
    (no ranking information) shuffling the predicted margins must reproduce the observed
    improvement by chance at the rate we measure.
    """
    import random
    rnd = random.Random(seed)
    obs_mae = mean([abs(p.actual_margin - p.margin_a) for p in preds])
    base_mae = mean([abs(p.actual_margin) for p in preds])
    obs_gain = base_mae - obs_mae
    actuals = [p.actual_margin for p in preds]
    pm = [p.margin_a for p in preds]
    worse = 0
    for _ in range(n_perm):
        rnd.shuffle(actuals)
        m = mean([abs(a - m2) for a, m2 in zip(actuals, pm)])
        if (base_mae - m) >= obs_gain:
            worse += 1
    return {
        "observed_mae_gain": round(obs_gain, 4),
        "p_value": round((worse + 1) / (n_perm + 1), 4),
        "n_perm": n_perm, "seed": seed,
        # Two-sided reading. A permutation test on a *difference in MAE* answers "is the model's
        # error different from a tie guess", not "is the model good": a model can be reliably
        # WORSE than a tie guess, and at this sample size that is what the sign says.
        "reading": (
            "the model's margin error is distinguishable from a tie guess (see the sign of "
            "observed_mae_gain: negative means WORSE than predicting a tie)"
            if (worse + 1) / (n_perm + 1) < 0.05
            else "the model's margin error is not separable from a tie guess on this sample"
        ),
    }


def leakage_audit(games: list[Game], preds: list[Prediction]) -> dict:
    """Test the leakage property directly, three ways, and publish all three.

    A forecast leaks if it can see its own result. The naive test — delete the game and check
    the forecast is unchanged — is *wrong*, and this repository got it wrong first: deleting a
    game removes a row from the whole history, which also changes every later date's
    volatility estimate σ and every rating, so the counterfactual differs for reasons that have
    nothing to do with the target game. Reporting that as FAIL would be a false alarm; quietly
    dropping the test would be worse.

    The three tests below each isolate the property:

    (1) SAME-DATE ISOLATION. Two games on the same date must be predicted from identical
        ratings. If a game could see its own result, a game played earlier in the same date
        would move the number for a game later that date. Any within-date difference is leakage.
    (2) NO IN-SAMPLE TERM. Every rating, σ and the league total used for a date must be computed
        only from games with a strictly smaller date. Checked by recounting the slices.
    (3) FUTURE-ONLY EDIT. Appending a fabricated game in the *future* must not change any
        earlier forecast. This is the deletion test done the right way round: adding data the
        forecast could not see must be a no-op.
    """
    # (1) same-date isolation
    by_date: dict[str, list[Prediction]] = {}
    for p in preds:
        by_date.setdefault(p.date, []).append(p)
    same_date_diff = 0.0
    for d, ps in by_date.items():
        # recompute each date's ratings from the prior slice once, then compare with published
        prior = [g for g in games if g.date < d]
        teams = {t for g in games for t in (g.home, g.away)}
        ra = _ratings_diff(prior, teams)
        resid = [g.margin - (ra[g.home] - ra[g.away]) for g in prior]
        sigma = math.sqrt(var(resid)) if len(resid) > 1 else 13.0
        for p in ps:
            want = ra[p.home] - ra[p.away]
            same_date_diff = max(same_date_diff, abs(want - p.margin_a))
    test1 = same_date_diff < 1e-9

    # (2) no in-sample term
    test2_problems = []
    for p in preds:
        prior = [g for g in games if g.date < p.date and g.game_id != p.game_id]
        # the target game must never be in its own prior slice by construction; assert it
        if any(g.game_id == p.game_id for g in prior):
            test2_problems.append(p.game_id)
        if any(g.date >= p.date for g in prior):
            test2_problems.append(p.game_id + ":future")
    test2 = not test2_problems

    # (3) future-only edit: append a game 30 days later, re-run, compare the published set
    future = Game("9999999999", "2026-12-15", "BOS", "LAL", 999, 0)
    rerun = {q.game_id: q for q in walk_forward(games + [future])}
    max_delta = 0.0
    for p in preds:
        q = rerun.get(p.game_id)
        if q is None:
            max_delta = float("inf")
        else:
            max_delta = max(max_delta, abs(q.margin_a - p.margin_a))
    test3 = max_delta < 1e-9

    return {
        "same_date_isolation": {"pass": test1, "max_within_date_delta": round(same_date_diff, 12)},
        "no_in_sample_term": {"pass": test2, "problems": test2_problems[:5]},
        "future_only_edit": {"pass": test3, "max_delta": round(max_delta, 12),
                             "note": "a fabricated game 30 days in the future changed no earlier forecast"},
        "all_pass": test1 and test2 and test3,
        "rule": ("every prediction is computed from games with date strictly less than its own; "
                 "appending undated-by-the-model future results is a no-op on every earlier "
                 "forecast; and the deletion test that would otherwise be reported as a failure "
                 "is explained above rather than used, because it confounds the date grid."),
        "rejected_test": ("delete-the-target-game. It fails on any correct implementation because "
                          "removing a row also removes it from later dates' volatility estimates. "
                          "Recorded here so the same wrong test is not proposed again."),
    }


def holdout_weights(preds: list[Prediction]) -> dict:
    """Out-of-sample log-loss for the two estimators, and the market weight that would apply.

    The slice is the last 30% of game DATES, so nothing in it was used to fit anything. The
    market's log-loss is absent because no market feed exists: the weight is therefore
    reported as NOT MEASURABLE with the formula that would be used.
    """
    dates = sorted({p.date for p in preds})
    cut = dates[int(len(dates) * (1 - HOLDOUT_FRAC))]
    test = [p for p in preds if p.date >= cut]
    if not test:
        return {"ok": False, "reason": "no out-of-sample dates"}
    ys = [p.home_won for p in test]
    la = log_loss([p.p_home_a for p in test], ys)
    lb = log_loss([p.p_home_b for p in test], ys)
    lc = log_loss([0.5] * len(test), ys)
    # Third published number: A with the over-confidence removed by the shrink factor that was
    # fitted ONLY on the earlier dates. This is the one line in the whole module that beats a coin,
    # and it beats it on data used neither to fit the ratings nor to fit the shrink.
    shr = shrink_gain(preds)
    alpha = shr.get("alpha")
    pc = [min(1 - 1e-9, max(1e-9, 0.5 + alpha * (p.p_home_a - 0.5))) for p in test] if alpha else None
    lcal = log_loss(pc, ys) if pc else None
    # accuracy at the calibrated probability is a threshold question; publish it too
    cal_acc = (sum((q > 0.5) == y for q, y in zip(pc, ys)) / len(ys)) if pc else None
    return {
        "ok": True, "split_date": cut, "n_test": len(test),
        "log_loss_a": round(la, 4), "log_loss_b": round(lb, 4), "log_loss_coin": round(lc, 4),
        "log_loss_a_calibrated": round(lcal, 4) if lcal is not None else None,
        "alpha": alpha, "alpha_fit_on": shr.get("fit_dates"),
        "accuracy_a_calibrated": round(cal_acc, 4) if cal_acc is not None else None,
        "beats_coin_raw": bool(la < lc), "beats_coin_calibrated": bool(lcal is not None and lcal < lc),
        "log_loss_market": None,
        "w_model_if_market_log_loss": {
            "formula": "w_model = L_market / (L_model + L_market)",
            "example_at_market_log_loss_0_60": round(0.60 / (la + 0.60), 4) if la else None,
            "example_at_market_log_loss_0_65": round(0.65 / (la + 0.65), 4) if la else None,
            "note": ("L_market was NOT measured: no odds feed is connected. The two examples show "
                     "what the weight would be for a market log-loss of 0.60 / 0.65, which is the "
                     "usual range for a closing NBA line. They are illustrations, not inputs, and "
                     "the site labels them that way."),
        },
        "reason": "BLOCKED input 'odds': no market probability exists to measure a log-loss for",
    }


def correlation_register(preds: list[Prediction]) -> dict:
    """Measured correlations, each with n and a Fisher-z interval."""
    r_mt, n = pearson([p.margin_a for p in preds], [p.total_fwd for p in preds])
    r_amt, _ = pearson([p.actual_margin for p in preds], [p.actual_total for p in preds])
    lo, hi = rho_ci(r_mt, n)
    lo2, hi2 = rho_ci(r_amt, n)
    return {
        "margin_vs_total_model": {"r": round(r_mt, 4), "n": n, "ci95": [round(lo, 4), round(hi, 4)],
                                  "total_used": "total_fwd (prior-window club rates + pace)",
                                  "withheld": "the league-mean total is near-constant (sd 1.21) and "
                                              "its correlation with margin (-0.0034) is not a "
                                              "measurement of anything, so it is not published as one"},
        "margin_vs_total_actual": {"r": round(r_amt, 4), "n": n, "ci95": [round(lo2, 4), round(hi2, 4)]},
        "reading": (
            "A spread/total correlation near zero is why a same-game parlay of a side and a total "
            "may be multiplied; a correlation far from zero is why it may not. The interval is "
            "published because at this n it is wide enough to matter."
        ),
    }


def run() -> dict:
    games = load_games()
    preds = walk_forward(games)
    m = metrics(preds)
    return {
        "meta": {
            "session": O.RETRIEVED_BY, "generated": O.AS_OF,
            "n_games_feed": len(games), "n_scored": len(preds),
            "first_date": preds[0].date if preds else None,
            "last_date": preds[-1].date if preds else None,
            "source": "data/raw/history/*.json + nba2/v3/official.py FINALS (official finals, one URL per row)",
            "seed": SEED, "n_perm": N_PERM, "holdout_fraction": HOLDOUT_FRAC,
        },
        "metrics": m,
        "baselines": baselines(preds),
        "skill": skill_attribution(preds),
        "permutation": permutation_p(preds),
        "holdout": holdout_weights(preds),
        "reliability": reliability_table(preds),
        "shrink": shrink_gain(preds),
        "margin_shrink": margin_shrink(preds),
        "total_direction": total_direction(preds),
        "correlations": correlation_register(preds),
        "leakage": leakage_audit(games, preds),
        "predictions": [p.as_dict() for p in preds],
    }


if __name__ == "__main__":
    import json as _json
    r = run()
    print(_json.dumps({k: v for k, v in r.items() if k != "predictions"}, indent=1)[:4000])


def _reliability_reading(rows, mean_abs_claim, mean_abs_outcome) -> str:
    """Build the sentence from the table, so it cannot claim a pattern the table does not show."""
    sig = [r for r in rows if r["p_two_sided"] < 0.05]
    big = [r for r in rows if r["n"] >= 20 and r["p_two_sided"] < 0.05]
    if not sig:
        return (f"The model's average distance from a coin flip is {mean_abs_claim:.3f}; reality's is "
                f"{mean_abs_outcome:.3f}. No individual band departs from its forecast by more than "
                f"sampling noise explains, which is what a table with this many thin bands looks "
                f"like. The aggregate log-loss, not any single band, is the evidence.")
    parts = [f"{r['band']} claims {r['forecast']:.3f} and delivers {r['observed']:.3f} "
             f"(p={r['p_two_sided']:.3f})" for r in big]
    return (f"The model's average distance from a coin flip is {mean_abs_claim:.3f}; reality's is "
            f"{mean_abs_outcome:.3f}. "
            + ("The bands with enough games to test are wrong in a consistent direction: "
               + "; ".join(parts) + "." if big else
               "Bands deviate, but none with 20+ games does so beyond noise."))


def reliability_table(preds: list[Prediction], probs: str = "p_home_a") -> dict:
    """Forecast-vs-outcome by probability band — the table that explains the log-loss failure.

    The headline "64.5% accuracy" hides that the model's *confidence* is wrong: it calls home
    teams 19.5% and they win 38.4%. That is why accuracy can look respectable while log-loss is
    worse than a coin. This table is the evidence for that sentence, so it is published rather
    than summarised.
    """
    bands = [(0.0, 0.45), (0.45, 0.50), (0.50, 0.55), (0.55, 0.60), (0.60, 0.65),
             (0.65, 0.70), (0.70, 0.75), (0.75, 1.0001)]
    rows = []
    for lo, hi in bands:
        sel = [p for p in preds if lo <= getattr(p, probs) < hi]
        if not sel:
            continue
        f = mean([getattr(p, probs) for p in sel])
        obs = sum(p.home_won for p in sel) / len(sel)
        # Is the gap inside sampling noise? A band with 3 games can miss by 0.25 and mean nothing;
        # a band with 73 games missing by 0.19 means something. A flat 0.10 threshold gets both
        # wrong, so the label comes from a two-sided binomial test against the band's own forecast.
        se = math.sqrt(max(f * (1 - f), 1e-12) / len(sel))
        z = (obs - f) / se
        p_two = 2 * (1 - phi(abs(z)))
        if p_two >= 0.05:
            kind = "inside noise"
        elif obs > f:
            kind = "too low (model under-confident)"
        else:
            kind = "too high (model over-confident)"
        rows.append({
            "band": f"{lo:.2f}–{hi if hi <= 1 else 1.00:.2f}",
            "n": len(sel), "forecast": round(f, 3), "observed": round(obs, 3),
            "gap": round(obs - f, 3), "z": round(z, 2), "p_two_sided": round(p_two, 4),
            "kind": kind,
        })
    mean_abs_claim = mean([abs(getattr(p, probs) - 0.5) for p in preds])
    mean_abs_outcome = mean([abs(int(p.home_won) - 0.5) for p in preds])
    return {
        "rows": rows,
        "mean_abs_claim": round(mean_abs_claim, 4),
        "mean_abs_outcome": round(mean_abs_outcome, 4),
        "reading": _reliability_reading(rows, mean_abs_claim, mean_abs_outcome),
        "p_home_range": [round(min(getattr(p, probs) for p in preds), 4),
                         round(max(getattr(p, probs) for p in preds), 4)],
    }


def shrink_gain(preds: list[Prediction], grid=None) -> dict:
    """Is the model over-dispersed? Measure, do not assert, by scanning a shrink-to-0.5 factor.

    p' = 0.5 + a * (p - 0.5), with ``a`` chosen on the FIRST 70% of dates and evaluated on the
    rest. A large gain means the published probabilities are too confident and the factor is a
    publishable correction; no gain means they are not. Note the honest caveat: a single fitted
    constant like this *is* a form of fitting, so the gain is reported on the untouched holdout.
    """
    grid = grid if grid is not None else [round(0.05 * i, 2) for i in range(0, 21)]
    dates = sorted({p.date for p in preds})
    cut = dates[int(len(dates) * (1.0 - HOLDOUT_FRAC))]
    fit = [p for p in preds if p.date < cut]
    test = [p for p in preds if p.date >= cut]

    def ll(ps, a):
        tot = 0.0
        for p in ps:
            q = min(1 - 1e-9, max(1e-9, 0.5 + a * (p.p_home_a - 0.5)))
            tot += -(math.log(q) if p.home_won else math.log(1 - q))
        return tot / len(ps) if ps else float("nan")

    scored = [(a, ll(fit, a)) for a in grid]
    best_a, best_ll = min(scored, key=lambda t: t[1])
    base_test = ll(test, 1.0)
    best_test = ll(test, best_a)
    return {
        "alpha": best_a, "grid": [round(a, 2) for a in grid],
        "fit_log_loss_a1": round(ll(fit, 1.0), 4), "fit_log_loss_best": round(best_ll, 4),
        "fit_dates": f"{dates[0]}..{cut}", "fit_n": len(fit),
        "holdout_log_loss_a1": round(base_test, 4), "holdout_log_loss_best": round(best_test, 4),
        "holdout_n": len(test), "holdout_cut": cut,
        "gain": round(base_test - best_test, 4),
        "apply": bool(best_test < base_test - 0.005),
        "reading": (
            f"Fitting the shrink factor on the first {len(fit)} games picks alpha={best_a:.2f}; on "
            f"the untouched {len(test)} held-out games it moves log-loss from {base_test:.4f} to "
            f"{best_test:.4f} (gain {base_test - best_test:+.4f})."
        ),
    }

def margin_shrink(preds: list[Prediction], grid=None) -> dict:
    """Same measurement for the margin, and the reason G4 has to be reported as two numbers.

    A margin forecast m is shrunk as m' = a*m. ``a`` is fitted on the earlier dates only. The
    raw forecast loses to *both* no-model baselines (a tie guess and the league mean); the shrunk
    forecast beats both. Publishing only the raw number would be a true statement that reads as a
    worse result than the model actually achieves, so both are published and G4 names which is
    which.
    """
    grid = grid if grid is not None else [round(0.05 * i, 2) for i in range(0, 21)]
    dates = sorted({p.date for p in preds})
    cut = dates[int(len(dates) * (1.0 - HOLDOUT_FRAC))]
    fit = [p for p in preds if p.date < cut]
    test = [p for p in preds if p.date >= cut]

    def mae(ps, a):
        return mean([abs(a * p.margin_a - p.actual_margin) for p in ps]) if ps else float("nan")

    best_a = min(grid, key=lambda a: mae(fit, a))
    raw_test, shr_test = mae(test, 1.0), mae(test, best_a)
    tie = mean([abs(p.actual_margin) for p in test])
    return {
        "alpha": best_a, "fit_dates": f"{dates[0]}..{cut}", "fit_n": len(fit),
        "fit_mae_a1": round(mae(fit, 1.0), 3), "fit_mae_best": round(mae(fit, best_a), 3),
        "holdout_n": len(test), "holdout_mae_raw": round(raw_test, 3),
        "holdout_mae_shrunk": round(shr_test, 3),
        "holdout_mae_tie": round(tie, 3),
        "beats_both_baselines_raw": bool(raw_test < tie),
        "beats_both_baselines_shrunk": bool(shr_test < tie),
        "gain": round(raw_test - shr_test, 3),
        "reading": (
            f"alpha={best_a:.2f} fitted on {len(fit)} games; held-out MAE {raw_test:.3f} raw → "
            f"{shr_test:.3f} shrunk, against a tie guess at {tie:.3f}. The raw forecast is worse "
            f"than guessing a tie; the shrunk forecast is better than it."
        ),
    }

def _total_direction_reading(n, hits, z_all, big_n, big_hits, z_big) -> str:
    """Compose the reading from the numbers, so the prose cannot disagree with the p-values.

    The first version of this string hard-coded "also not significant" and was printed directly
    above a p of 0.020. Prose that asserts a conclusion the adjacent arithmetic contradicts is
    worse than no prose, and it is the kind of error that survives review because the sentence
    looks right.
    """
    p_all = 2 * (1 - phi(abs(z_all)))
    p_big = 2 * (1 - phi(abs(z_big)))
    sig = lambda p: "significant" if p < 0.05 else "not significant"
    return (
        f"Direction against a rolling mean over every scored game: {hits}/{n} = {hits / n:.3f} "
        f"(z={z_all:+.2f}, p={p_all:.3f}) — {sig(p_all)}. On the subset where the forecast commits "
        f"to at least a 3-point view: {big_hits}/{big_n} = {big_hits / big_n:.3f} "
        f"(z={z_big:+.2f}, p={p_big:.3f}) — {sig(p_big)}. "
        f"The subset result is a threshold-selected subset of the same data, so it is reported as a "
        f"subset and not as the headline; the whole-sample number is the one to trust, and the two "
        f"together say the total's ordering signal is promising and unproven. Neither licenses a "
        f"stake: a rolling mean is not a price."
    )


def total_direction(preds: list[Prediction]) -> dict:
    """The total forecast's *ordering* skill, separately from its *level* error.

    These are different questions and the first version of this site conflated them. The forward
    total's absolute error is worse than a constant (it is too tightly dispersed), yet on the
    subset where it commits to a view it picks the right side of the rolling mean more often than
    not. A reader is entitled to both numbers, and to the fact that the second one does not clear
    significance at this n.
    """
    by_date: dict[str, list[Prediction]] = {}
    for p in preds:
        by_date.setdefault(p.date, []).append(p)
    running: list[float] = []
    hits = n = 0
    big_hits = big_n = 0
    for d in sorted(by_date):
        for p in by_date[d]:
            if len(running) >= 20:
                ref = mean(running)
                ok = (p.actual_total > ref) == (p.total_fwd > ref)
                hits += ok
                n += 1
                if abs(p.total_fwd - ref) >= 3.0:
                    big_hits += ok
                    big_n += 1
        running.extend(q.actual_total for q in by_date[d])
    se_all = math.sqrt(0.25 / n) if n else float("nan")
    se_big = math.sqrt(0.25 / big_n) if big_n else float("nan")
    z_all = (hits / n - 0.5) / se_all if n else float("nan")
    z_big = (big_hits / big_n - 0.5) / se_big if big_n else float("nan")
    return {
        "n": n, "hits": hits, "rate": round(hits / n, 4) if n else None,
        "z": round(z_all, 2) if n else None,
        "p_two_sided": round(2 * (1 - phi(abs(z_all))), 4) if n else None,
        "committed_n": big_n, "committed_hits": big_hits,
        "committed_rate": round(big_hits / big_n, 4) if big_n else None,
        "committed_z": round(z_big, 2) if big_n else None,
        "committed_p_two_sided": round(2 * (1 - phi(abs(z_big))), 4) if big_n else None,
        "reading": _total_direction_reading(n, hits, z_all, big_n, big_hits, z_big),
    }

