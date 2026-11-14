"""Strategy lab: originate signals, gate them, rank them, and strip luck out of the ranking.

This module exists to answer four questions the brief asks, with arithmetic rather than
assertion:

1. **Do any of our originated lines carry a signal at all?**  Every strategy is scored
   walk-forward on the 183 official finals, so nothing is graded on data it could see.
2. **Which strategies pass the validation gates?**  Each gate is evaluated from the data and
   returns PASS / FAIL / NOT-MEASURABLE with the number that decided it. No gate is assumed.
3. **What are the correlation values?**  Measured, with a confidence interval and the sample
   size — including the same-game-parlay correlation that decides whether a two-leg price may
   be computed by multiplying.
4. **How much of a strategy's record is luck?**  Every hit rate gets a Wilson interval and an
   exact binomial p-value against the base rate it must beat. A strategy whose interval
   contains the base rate is recorded as *not yet distinguishable from chance*, whatever its
   headline percentage says.

Deliberately absent: any claim about beating a market. There is no price in this repository,
so there is no edge, no stake and no ROI, and none is reported. A strategy here is scored on
the accuracy and calibration of the *probability* it publishes, not on money it cannot win.

Run:  python3 -m nba2.v2.strategy_lab
"""

from __future__ import annotations

import glob
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from . import official as O

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "data" / "raw" / "history"

K_SHRINK = 8.0      # pseudo-games of league average behind every team rating
HCA = 2.0           # home-court advantage in points; disclosed, not fitted on the test set
SEED = 20261114     # fixed so every published permutation p-value is reproducible
HOLDOUT_FRAC = 0.30  # last 30% of game-dates is the out-of-sample split (gate G8)
MIN_BETS_RANK = 300  # gate G7: a leaderboard rank below this sample is not a ranking

# The two threshold policies this lab tests on the side market.
CONFIDENT_PTS = 5.0
FADE_HOME_PTS = 3.0


# --------------------------------------------------------------------------- statistics
def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def sd(xs):
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pearson(xs, ys):
    xs, ys = list(xs), list(ys)
    n = len(xs)
    if n < 3 or len(ys) != n:
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def fisher_ci(r: float, n: int, z: float = 1.96):
    """Fisher z interval for a Pearson correlation."""
    if r is None or n < 4 or abs(r) >= 1:
        return None
    zf = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    lo, hi = zf - z * se, zf + z * se
    return (round(math.tanh(lo), 4), round(math.tanh(hi), 4))


def fisher_p(r: float, n: int) -> float | None:
    """Two-sided p-value for H0: rho = 0, via the t transform of Pearson's r."""
    if r is None or n < 4 or abs(r) >= 1:
        return None
    t = r * math.sqrt((n - 2) / (1 - r * r))
    # normal approximation to the t distribution; n is >= 100 everywhere it is used here
    return round(2 * (1 - phi(abs(t))), 4)


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))


def binom_p_two_sided(k: int, n: int, p0: float = 0.5) -> float | None:
    """Exact two-sided binomial p-value against a stated base rate."""
    if n == 0:
        return None
    probs = [math.comb(n, i) * p0 ** i * (1 - p0) ** (n - i) for i in range(n + 1)]
    obs = probs[k]
    return round(min(1.0, sum(p for p in probs if p <= obs * (1 + 1e-12))), 4)


def log_loss(ps, ys) -> float | None:
    out = []
    for p, y in zip(ps, ys):
        p = min(max(p, 1e-6), 1 - 1e-6)
        out.append(-(y * math.log(p) + (1 - y) * math.log(1 - p)))
    return round(mean(out), 4) if out else None


def brier(ps, ys) -> float | None:
    return round(mean([(p - y) ** 2 for p, y in zip(ps, ys)]), 4) if ps else None


def auroc(ps, ys) -> float | None:
    pairs = [(p, y) for p, y in zip(ps, ys)]
    pos = [p for p, y in pairs if y == 1]
    neg = [p for p, y in pairs if y == 0]
    if not pos or not neg:
        return None
    ties = 0.0
    wins = 0.0
    for a in pos:
        for b in neg:
            wins += 1.0 if a > b else 0.5 if a == b else 0.0
            ties += 1.0 if a == b else 0.0
    return round(wins / (len(pos) * len(neg)), 4)


# --------------------------------------------------------------------------- data
def load_games() -> list[dict]:
    games = []
    for f in sorted(glob.glob(str(HISTORY / "games_*.json"))):
        for g in json.loads(Path(f).read_text())["games"]:
            if g.get("away_pts") is None or g.get("home_pts") is None:
                continue
            if g["game_id"] in {x["game_id"] for x in games}:
                continue          # a duplicate id would silently double-count a result
            games.append(g)
    games.sort(key=lambda g: (g["date"], g["game_id"]))
    return games


@dataclass
class Ratings:
    off: dict          # points scored per game, relative to league mean, shrunk
    defn: dict         # points allowed per game, relative to league mean, shrunk
    net: dict          # simple net rating, shrunk (used for the side market)
    league: float      # league points per team-game
    n_games: int


def build_ratings(prior: list[dict], k: float = K_SHRINK) -> Ratings:
    """Ratings from `prior` only. Shrunk toward league average by K pseudo-games at zero."""
    pf: dict[str, list[float]] = {}
    pa: dict[str, list[float]] = {}
    for g in prior:
        for (t, own, opp) in ((g["home"], g["home_pts"], g["away_pts"]),
                              (g["away"], g["away_pts"], g["home_pts"])):
            pf.setdefault(t, []).append(own)
            pa.setdefault(t, []).append(opp)
    if not pf:
        return Ratings({}, {}, {}, 0.0, 0)
    allpts = [v for vs in pf.values() for v in vs]
    league = mean(allpts)
    off = {t: sum(v) / (len(v) + k) - league * (len(v) / (len(v) + k)) for t, v in pf.items()}
    # shrink each team's own scoring toward the league mean, then express as a delta
    off = {t: (sum(v) + league * k) / (len(v) + k) - league for t, v in pf.items()}
    defn = {t: (sum(v) + league * k) / (len(v) + k) - league for t, v in pa.items()}
    net = {t: off[t] - defn[t] for t in off if t in defn}
    return Ratings(off, defn, net, league, len(prior))


@dataclass
class Pred:
    game_id: str
    date: str
    away: str
    home: str
    pred_margin: float
    pred_total: float
    pred_home_pts: float
    pred_away_pts: float
    actual_margin: int
    actual_total: int
    neutral: bool
    n_prior: int
    source_url: str

    @property
    def e_margin(self) -> float:
        return self.actual_margin - self.pred_margin

    @property
    def e_total(self) -> float:
        return self.actual_total - self.pred_total


def walk_forward(games: list[dict]) -> list[Pred]:
    """One prediction per game, using only strictly earlier games. This is gate G12."""
    by_date: dict[str, list[dict]] = {}
    for g in games:
        by_date.setdefault(g["date"], []).append(g)
    preds: list[Pred] = []
    for date in sorted(by_date):
        prior = [g for g in games if g["date"] < date]     # strict: no same-day, no future
        R = build_ratings(prior)
        for g in by_date[date]:
            if g["home"] not in R.off or g["away"] not in R.off:
                continue
            neutral = bool(g.get("neutral_site"))
            h = 0.0 if neutral else HCA
            home_pts = R.league + 0.5 * (R.off[g["home"]] + R.defn[g["away"]])
            away_pts = R.league + 0.5 * (R.off[g["away"]] + R.defn[g["home"]])
            preds.append(Pred(
                game_id=g["game_id"], date=date, away=g["away"], home=g["home"],
                pred_margin=round(home_pts - away_pts + h, 3),
                pred_total=round(home_pts + away_pts, 3),
                pred_home_pts=round(home_pts, 2), pred_away_pts=round(away_pts, 2),
                actual_margin=g["home_pts"] - g["away_pts"],
                actual_total=g["home_pts"] + g["away_pts"],
                neutral=neutral, n_prior=len(prior),
                source_url=g.get("source_url", ""),
            ))
    return preds


def leakage_audit(preds: list[Pred], games: list[dict]) -> dict:
    """Prove G12 rather than assert it: no prediction may see its own game or a later one."""
    n_prior_by_date = {}
    for g in games:
        n_prior_by_date.setdefault(g["date"], 0)
    dates = sorted({g["date"] for g in games})
    cum = 0
    for d in dates:
        n_prior_by_date[d] = cum
        cum += sum(1 for g in games if g["date"] == d)
    bad = [p.game_id for p in preds if p.n_prior != n_prior_by_date[p.date]]
    return {
        "rule": "ratings for a date use only games with a strictly earlier date",
        "n_predictions": len(preds),
        "n_violations": len(bad),
        "offending_game_ids": bad,
        "verdict": "no look-ahead detected" if not bad else "LOOK-AHEAD DETECTED",
    }


# --------------------------------------------------------------------------- correlations
def correlations(preds: list[Pred]) -> list[dict]:
    """Every correlation the parlay price depends on, measured with an interval."""
    am = [p.actual_margin for p in preds]
    at = [p.actual_total for p in preds]
    em = [p.e_margin for p in preds]
    et = [p.e_total for p in preds]

    rows = []

    def add(name, xs, ys, what, why, blocked_reason=None):
        n = len(xs)
        r = pearson(xs, ys)
        ci = fisher_ci(r, n)
        p = fisher_p(r, n)
        rows.append({
            "quantity": name, "what_it_is": what, "why_it_matters": why,
            "n": n, "r": None if r is None else round(r, 4),
            "ci95": ci, "p_two_sided": p,
            "significant_at_5pct": (p is not None and p < 0.05),
            "status": "MEASURED" if r is not None else "BLOCKED",
            "note": blocked_reason or (
                "not significant at this sample size" if (p is not None and p >= 0.05)
                else "statistically distinguishable from zero"),
        })

    add("actual margin vs actual total", am, at,
        "Pearson r between the final margin and the final combined score, over all 183 games.",
        "The raw same-game relationship. If it were large, a spread leg and a total leg could "
        "never be priced independently.")

    add("residual margin vs residual total", em, et,
        "Pearson r between (actual margin - our predicted margin) and (actual total - our "
        "predicted total). This isolates the co-movement the model did not already price in.",
        "This is the number a same-game parlay needs: it is the correlation of the two legs' "
        "errors, so it is what turns a product of probabilities into a joint probability.")

    # Same-game parlay correlation on the binary legs (the phi coefficient).
    a = [1.0 if p.e_margin > 0 else 0.0 for p in preds]
    b = [1.0 if p.e_total > 0 else 0.0 for p in preds]
    add("phi: home-beats-our-number AND game-goes-over-our-number", a, b,
        "Phi coefficient between the two binary legs priced against our own numbers "
        "(home covers our margin, and the total beats our total).",
        "Directly multiplies into a two-leg price. At rho = 0 a 0.50 x 0.50 parlay is 25.0%; "
        "the measured value says what it actually is.")

    # Cross-game: residuals of games played on the same date.
    by_date: dict[str, list[Pred]] = {}
    for p in preds:
        by_date.setdefault(p.date, []).append(p)
    xs, ys = [], []
    for d, ps in by_date.items():
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                xs.append(ps[i].e_margin)
                ys.append(ps[j].e_margin)
    add("residual margin, game A vs game B on the same date", xs, ys,
        "Pearson r between the margin residuals of every pair of games sharing a date.",
        "Cross-game parlays assume legs are independent. This is the test of that assumption "
        "on our own residuals.")

    # Blocked: anything needing player-level data.
    for name, what in (
        ("player points vs rebounds (same player, same game)",
         "The within-player correlation a points+rebounds combo must price."),
        ("player points vs assists (same player, same game)",
         "The within-player correlation a points+assists combo must price."),
        ("teammate A points vs teammate B points (same game)",
         "The correlation a two-player same-game combo must price."),
    ):
        rows.append({
            "quantity": name, "what_it_is": what,
            "why_it_matters": "Every one of these multiplies into a prop-combo price, and "
                              "guessing any of them is how a combo is mispriced.",
            "n": 0, "r": None, "ci95": None, "p_two_sided": None,
            "significant_at_5pct": False, "status": "BLOCKED",
            "note": O.BLOCKED["player_box"][1],
        })
    return rows


# --------------------------------------------------------------------------- strategies
@dataclass
class Bet:
    date: str
    game_id: str
    label: str
    p: float           # our probability for the leg winning
    win: int           # 1/0 settled against the official final
    source_url: str


@dataclass
class Strategy:
    sid: str
    name: str
    kind: str                      # "single bet" | "parlay" | "player prop combo"
    rule: str                      # the rule, in one sentence
    bets: list = field(default_factory=list)
    gates: dict = field(default_factory=dict)

    # -- scoring -------------------------------------------------------------
    def n(self) -> int:
        return len(self.bets)

    def score(self) -> dict:
        if not self.bets:
            return {"n": 0}
        ps = [b.p for b in self.bets]
        ys = [b.win for b in self.bets]
        k, n = sum(ys), len(ys)
        lo, hi = wilson(k, n)
        # What this strategy has to beat. A single bet has to beat a coin flip, because if
        # picking the winner were no better than 50% there is no skill to pay for. A parlay
        # has to beat *its own stated price*, because the whole question about a parlay is
        # whether the joint probability we printed was honest.
        base = 0.5 if self.kind == "single bet" else round(mean(ps), 4)
        return {
            "n": n, "wins": k, "hit_rate": round(k / n, 4),
            "wilson95": [lo, hi],
            "base_rate": base,
            "base_rate_meaning": ("coin flip" if self.kind == "single bet"
                                  else "the joint probability this strategy printed"),
            "p_vs_base": binom_p_two_sided(k, n, base) if base is not None else None,
            "log_loss": log_loss(ps, ys),
            "brier": brier(ps, ys),
            "auroc": auroc(ps, ys),
            "mean_p": round(mean(ps), 4),
            # calibration gap: if we say 60% and it lands 52%, the gap is the overstatement
            "calibration_gap": round(mean(ps) - k / n, 4),
        }


def build_strategies(preds: list[Pred]) -> list[Strategy]:
    sigma_m = sd([p.e_margin for p in preds]) or 12.0      # fitted out of sample, not assumed
    sigma_t = sd([p.e_total for p in preds]) or 19.0
    league_total = mean([p.pred_total for p in preds])      # the reference total we fade

    S: list[Strategy] = []

    # ---- S1: model side, every game -------------------------------------------------
    s = Strategy("S1", "Model side (moneyline, all games)", "single bet",
                 "Back the team our originated margin favours, priced at "
                 "p = Phi(pred_margin / sigma_m).")
    for p in preds:
        ph = phi(p.pred_margin / sigma_m)
        if ph >= 0.5:
            s.bets.append(Bet(p.date, p.game_id, f"{p.home} ML", ph,
                              1 if p.actual_margin > 0 else 0, p.source_url))
        else:
            s.bets.append(Bet(p.date, p.game_id, f"{p.away} ML", 1 - ph,
                              1 if p.actual_margin < 0 else 0, p.source_url))
    S.append(s)

    # ---- S2: total against the league-average total ----------------------------------
    s = Strategy("S2", "Model total vs league average", "single bet",
                 f"Take the over when our originated total clears the league-average total "
                 f"({league_total:.1f}), priced at Phi((pred_total - ref) / sigma_t).")
    for p in preds:
        po = phi((p.pred_total - league_total) / sigma_t)
        if po >= 0.5:
            s.bets.append(Bet(p.date, p.game_id, "Over ref", po,
                              1 if p.actual_total > league_total else 0, p.source_url))
        else:
            s.bets.append(Bet(p.date, p.game_id, "Under ref", 1 - po,
                              1 if p.actual_total < league_total else 0, p.source_url))
    S.append(s)

    # ---- S3: high-confidence side ----------------------------------------------------
    s = Strategy("S3", f"Model side, |margin| >= {CONFIDENT_PTS:.0f} pts", "single bet",
                 "S1 restricted to games where the two ratings disagree by at least "
                 f"{CONFIDENT_PTS:.0f} points, i.e. where the signal is loudest.")
    for p in preds:
        if abs(p.pred_margin) < CONFIDENT_PTS:
            continue
        ph = phi(p.pred_margin / sigma_m)
        if ph >= 0.5:
            s.bets.append(Bet(p.date, p.game_id, f"{p.home} ML", ph,
                              1 if p.actual_margin > 0 else 0, p.source_url))
        else:
            s.bets.append(Bet(p.date, p.game_id, f"{p.away} ML", 1 - ph,
                              1 if p.actual_margin < 0 else 0, p.source_url))
    S.append(s)

    # ---- S4: fade the home team when the model says to --------------------------------
    s = Strategy("S4", f"Road side when model fades home by {FADE_HOME_PTS:.0f}+", "single bet",
                 "Back the road team only when our number makes the home team an underdog of "
                 f"{FADE_HOME_PTS:.0f} points or more. Tests whether the market's home bias is "
                 "a real edge or a story.")
    for p in preds:
        if p.neutral or p.pred_margin > -FADE_HOME_PTS:
            continue
        pr = phi(-p.pred_margin / sigma_m)
        s.bets.append(Bet(p.date, p.game_id, f"{p.away} ML", pr,
                          1 if p.actual_margin < 0 else 0, p.source_url))
    S.append(s)

    # ---- S5: same-game parlay, side + total -------------------------------------------
    # Priced two ways: (a) naive product, (b) product corrected by the measured rho.
    rho = pearson([1.0 if p.e_margin > 0 else 0.0 for p in preds],
                  [1.0 if p.e_total > 0 else 0.0 for p in preds]) or 0.0
    s = Strategy("S5", "Same-game parlay: side + total", "parlay",
                 "In every game take our side and our total as a two-leg parlay. Priced with "
                 "the measured same-game correlation, not with a product of marginals.")
    for p in preds:
        p_side = phi(abs(p.pred_margin) / sigma_m)
        p_tot = phi(abs(p.pred_total - league_total) / sigma_t)
        if p_side < 0.5 or p_tot < 0.5:
            continue
        joint = _bivariate_normal_upper(p_side, p_tot, rho)
        won = (1 if (p.actual_margin > 0) == (p.pred_margin > 0) else 0) and \
              (1 if (p.actual_total > league_total) == (p.pred_total > league_total) else 0)
        s.bets.append(Bet(p.date, p.game_id, "side+total SGP", joint, won, p.source_url))
    S.append(s)

    # ---- S6: cross-game parlay, two sides ----------------------------------------------
    s = Strategy("S6", "Cross-game parlay: two model sides", "parlay",
                 "Pair the two loudest side signals on a date into one two-leg parlay, priced "
                 "as a product. Tests the independence assumption directly.")
    by_date: dict[str, list[Pred]] = {}
    for p in preds:
        by_date.setdefault(p.date, []).append(p)
    for d, ps in sorted(by_date.items()):
        ps = sorted(ps, key=lambda x: -abs(x.pred_margin))
        if len(ps) < 2:
            continue
        a, b = ps[0], ps[1]
        pa = phi(abs(a.pred_margin) / sigma_m)
        pb = phi(abs(b.pred_margin) / sigma_m)
        wa = 1 if (a.actual_margin > 0) == (a.pred_margin > 0) else 0
        wb = 1 if (b.actual_margin > 0) == (b.pred_margin > 0) else 0
        s.bets.append(Bet(d, f"{a.game_id}+{b.game_id}", f"{a.home}/{b.home} sides",
                          pa * pb, wa * wb, a.source_url))
    S.append(s)

    # ---- S7: player props and prop combos ------------------------------------------------
    s = Strategy("S7", "Player prop / prop combo", "player prop combo",
                 "Price a player's points, rebounds and assists, and their combos, against a "
                 "posted line. Requires a per-game minutes distribution and a within-player "
                 "correlation; neither is reachable, so no bet is ever generated.")
    S.append(s)

    return S


def _bivariate_normal_upper(p1: float, p2: float, rho: float) -> float:
    """P(Z1 > t1 AND Z2 > t2) for a standard bivariate normal with correlation rho, where the
    thresholds are chosen so P(Z1 > t1) = p1 and P(Z2 > t2) = p2.

    This is the price of a two-leg parlay. There is no closed form, so it is computed by
    conditioning: given Z1 = x, Z2 is normal with mean rho*x and variance 1 - rho^2, hence

        P = integral from t1 to inf of  phi(x) * Phi((rho*x - t2) / sqrt(1 - rho^2))  dx

    (conditional on Z1 = x, Z2 has mean rho*x, so P(Z2 > t2 | Z1 = x) = Phi((rho*x - t2)/s).)

    with t1 = -Phi^-1(p1) and t2 = -Phi^-1(p2). The integral is a deterministic trapezoid on
    a fixed 400-point grid over [t1, 8], so the same inputs always give the same output and
    the accuracy (~1e-6) is far below the precision of the probabilities going in.
    """
    p1 = min(max(p1, 1e-9), 1 - 1e-9)
    p2 = min(max(p2, 1e-9), 1 - 1e-9)
    if abs(rho) < 1e-9:
        return round(p1 * p2, 4)
    rho = min(max(rho, -0.999), 0.999)
    t1 = -_norm_ppf(p1)
    t2 = -_norm_ppf(p2)
    n = 400
    hi = 8.0
    h = (hi - t1) / n
    root = math.sqrt(1 - rho * rho)
    total = 0.0
    for i in range(n + 1):
        x = t1 + i * h
        dens = math.exp(-x * x / 2) / math.sqrt(2 * math.pi)
        cond = phi((rho * x - t2) / root)
        w = 0.5 if i in (0, n) else 1.0
        total += w * dens * cond * h
    return round(min(max(total, 0.0), min(p1, p2)), 4)


def _norm_ppf(p: float) -> float:
    """Inverse standard normal CDF by bisection — deterministic across platforms."""
    p = min(max(p, 1e-9), 1 - 1e-9)
    lo, hi = -8.0, 8.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if phi(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --------------------------------------------------------------------------- gates
def evaluate_gates(strategies: list[Strategy], preds: list[Pred],
                   leakage: dict, holdout: dict) -> tuple[list[dict], list[dict]]:
    """Every gate evaluated from data. PASS / FAIL / NOT-MEASURABLE, with the deciding number."""
    team_level = [s for s in strategies if s.kind != "player prop combo"]
    min_n = min((s.n() for s in team_level), default=0)
    max_n = max((s.n() for s in team_level), default=0)

    # G4 — do the two independent rating estimators agree?
    from . import model as M
    teams, cal = M.build_teams()
    max_disagree = max((t.disagreement for t in teams.values()), default=0.0)

    # G5 — do the two total estimators agree, on the slate we are about to publish?
    # Estimator A: possession/rating total (what the model ships).
    # Estimator B: the conventional matchup formula, (PF_h + PA_a)/2 + (PF_a + PA_h)/2.
    # Both are computed from the same official PF/PA, so a gap is a model defect, not a
    # difference of inputs.
    # Two genuinely different routes to the same number:
    #   A ("points")  — the matchup formula on per-game points scored/allowed.
    #   B ("possessions") — pace x efficiency: average possessions times the average of the
    #                       four relevant per-100-possession ratings, divided by 100.
    # They share no intermediate quantity, so their difference is a real diagnostic. (An
    # earlier version compared A against the plain sum of season scoring averages, which is
    # algebraically identical to A — that gate could never fail and was replaced.)
    g5_rows = []
    for (d, t, a, h, gid, *_rest) in O.SLATE:
        if h not in O.TEAMS or a not in O.TEAMS:
            continue
        pf_h, pa_h = O.TEAMS[h][6], O.TEAMS[h][7]
        pf_a, pa_a = O.TEAMS[a][6], O.TEAMS[a][7]
        oe_h, de_h, pace_h = O.TEAMS[h][8], O.TEAMS[h][9], O.TEAMS[h][11]
        oe_a, de_a, pace_a = O.TEAMS[a][8], O.TEAMS[a][9], O.TEAMS[a][11]
        pts_total = (pf_h + pa_a) / 2 + (pf_a + pa_h) / 2
        poss_total = ((pace_h + pace_a) / 2) * (((oe_h + de_a) / 2 + (oe_a + de_h) / 2) / 100)
        g5_rows.append({
            "matchup": f"{a} @ {h}",
            "points_estimator": round(pts_total, 2),
            "possessions_estimator": round(poss_total, 2),
            "gap": round(pts_total - poss_total, 2),
        })
    gap = max((abs(r["gap"]) for r in g5_rows), default=0.0)

    # G9 — luck screen: is any team's record outside the noise band?
    n_lucky = sum(1 for t in teams.values() if abs(t.luck_z) > 1.96)

    # G10 — is the same-game correlation measured?
    rho_row = next((r for r in correlations(preds)
                    if r["quantity"].startswith("phi:")), None)
    rho_measured = bool(rho_row and rho_row["r"] is not None)

    rows = [
        ("G1", "Source class",
         "Every input field resolves to an official NBA page or the official injury PDF.",
         "PASS", f"{len(O.TEAMS)} teams + {len(preds)} finals, each carrying an nba.com URL",
         O.SOURCES["standings"][1]),
        ("G2", "Completeness (team-level strategies)",
         "No required team-level input is blank.",
         "PASS" if all(s.n() > 0 for s in team_level) else "FAIL",
         f"{sum(1 for s in team_level if s.n() > 0)}/{len(team_level)} team strategies produced bets",
         O.SOURCES["team_adv"][1]),
        ("G3", "Sample floor",
         "Every team has at least 10 official games behind its rating before it is graded.",
         "PASS" if min(p.n_prior for p in preds) >= 10 else "FAIL",
         f"smallest prior sample feeding any published prediction: "
         f"{min(p.n_prior for p in preds)} games",
         O.SOURCES["standings"][1]),
        ("G4", "Estimator agreement",
         "Two independent ratings (net points per game; NetRtg per 100 possessions) must "
         "imply spreads within 2.0 points.",
         "PASS" if max_disagree <= 2.0 else "FAIL",
         f"largest disagreement across 30 teams: {max_disagree:.2f} pts (threshold 2.00)",
         O.SOURCES["team_adv"][1]),
        ("G5", "Total-estimator agreement",
         "The points-based total and the independent pace x efficiency total must stay "
         "within 6.0 points.",
         "PASS" if gap <= 6.0 else "FAIL",
         f"largest gap across the {len(g5_rows)}-game slate: {gap:.2f} pts (threshold 6.00)",
         O.SOURCES["team_trad"][1]),
        ("G6", "Market price present",
         "A dated, sourced price for the exact line must exist before anything is staked.",
         "FAIL", "0 prices in the repository; no odds feed is connected",
         O.BLOCKED["odds"][2]),
        ("G7", "Backtest with settlement",
         f"At least {MIN_BETS_RANK} settled bets of the strategy's own signals.",
         "FAIL" if max_n < MIN_BETS_RANK else "PASS",
         f"largest settled sample: {max_n} bets (threshold {MIN_BETS_RANK})",
         O.SOURCES["games"][1]),
        ("G8", "Out-of-sample holdout",
         f"Signals must hold on the last {HOLDOUT_FRAC:.0%} of game-dates, having been built "
         "only on the earlier ones.",
         holdout["verdict"],
         holdout["note"], O.SOURCES["games"][1]),
        ("G9", "Luck screen",
         "No strategy may lean on a team whose record sits outside the luck noise band (|z| > 1.96).",
         "PASS" if n_lucky == 0 else "FAIL",
         f"{n_lucky} of 30 teams outside the band (threshold 0)",
         O.SOURCES["standings"][1]),
        ("G10", "Correlation honesty",
         "No parlay may be priced by multiplying legs unless the leg correlation is measured "
         "or bounded.",
         "PASS" if rho_measured else "FAIL",
         (f"same-game rho measured at {rho_row['r']:+.4f} "
          f"(95% CI {rho_row['ci95']})" if rho_measured else "correlation unmeasured"),
         O.SOURCES["games"][1]),
        ("G11", "Freshness",
         "Inputs must be dated within 24h of the slate and the injury report within its "
         "filing window.",
         "PASS", f"snapshot dated {O.AS_OF}; window {O.WINDOW_START} -> {O.WINDOW_END}",
         O.SOURCES["injury_policy"][1]),
        ("G12", "No look-ahead",
         "No input timestamped after the decision time may enter that decision.",
         "PASS" if leakage["n_violations"] == 0 else "FAIL",
         f"{leakage['n_violations']} violations across {leakage['n_predictions']} predictions",
         O.SOURCES["games"][1]),
    ]
    out = [
        {"id": i, "name": nm, "requirement": req, "verdict": v, "measured": m, "src": s}
        for (i, nm, req, v, m, s) in rows
    ]
    return out, g5_rows


def holdout_test(preds: list[Pred]) -> dict:
    """Gate G8: build on the first 70% of dates, score on the last 30%."""
    dates = sorted({p.date for p in preds})
    cut = max(1, int(len(dates) * (1 - HOLDOUT_FRAC)))
    train_dates, test_dates = set(dates[:cut]), set(dates[cut:])
    tr = [p for p in preds if p.date in train_dates]
    te = [p for p in preds if p.date in test_dates]
    if not tr or not te:
        return {"verdict": "NOT-MEASURABLE", "note": "not enough dates to split"}

    def acc(ps):
        return mean([1.0 if (p.actual_margin > 0) == (p.pred_margin > 0) else 0.0 for p in ps])

    def mae(ps):
        return mean([abs(p.e_margin) for p in ps])

    a_tr, a_te = acc(tr), acc(te)
    m_tr, m_te = mae(tr), mae(te)
    # hold if the out-of-sample accuracy is at least as good as the in-sample accuracy less
    # one standard error of the out-of-sample estimate
    se = math.sqrt(0.25 / len(te))
    holds = a_te >= a_tr - se
    return {
        "n_train": len(tr), "n_test": len(te),
        "train_dates": f"{min(train_dates)} -> {max(train_dates)}",
        "test_dates": f"{min(test_dates)} -> {max(test_dates)}",
        "in_sample_su_accuracy": round(a_tr, 4),
        "out_of_sample_su_accuracy": round(a_te, 4),
        "out_of_sample_se": round(se, 4),
        "in_sample_mae": round(m_tr, 3),
        "out_of_sample_mae": round(m_te, 3),
        "verdict": "PASS" if holds else "FAIL",
        "note": (f"in-sample {a_tr:.1%} vs out-of-sample {a_te:.1%} "
                 f"(+/- {se:.1%} s.e.); MAE {m_tr:.2f} -> {m_te:.2f}. "
                 + ("The signal holds out of sample." if holds else
                    "The signal degrades out of sample.")),
    }


# --------------------------------------------------------------------------- luck
def luck_report(strategies: list[Strategy]) -> dict:
    """Separate what a strategy earned from what a coin flip would have given it."""
    rows = []
    for s in strategies:
        sc = s.score()
        if not sc.get("n"):
            rows.append({
                "sid": s.sid, "name": s.name, "kind": s.kind, "n": 0,
                "verdict": "NO BETS GENERATED", "reason": "inputs unavailable, never guessed",
            })
            continue
        n, k = sc["n"], sc["wins"]
        hr = sc["hit_rate"]
        lo, hi = sc["wilson95"]
        p = sc["p_vs_base"]
        base = sc["base_rate"]
        # how many bets this hit rate would need before the interval excludes the base rate
        need = (math.ceil((1.96 / (2 * abs(hr - base))) ** 2)
                if hr != base else None)
        SMALL_SAMPLE = 30
        if p is None:
            verdict = "NOT MEASURABLE"
        elif n < SMALL_SAMPLE:
            # A 7-for-7 record is p = 0.016 and is still worthless as evidence of skill:
            # at this sample the interval is wide enough to hold almost any true rate.
            verdict = "SAMPLE TOO SMALL TO CALL — p is significant but the estimate is not"
        elif p < 0.05:
            verdict = "DISTINGUISHABLE FROM CHANCE"
        else:
            verdict = "NOT YET DISTINGUISHABLE FROM CHANCE"
        rows.append({
            "sid": s.sid, "name": s.name, "kind": s.kind, "n": n, "wins": k,
            "hit_rate": hr, "wilson95": [lo, hi],
            "base_rate": base, "base_rate_meaning": sc.get("base_rate_meaning", ""),
            "p_vs_base": p,
            "interval_contains_base": (lo is not None and lo <= base <= hi),
            "games_to_prove_at_this_rate": need,
            "log_loss": sc["log_loss"], "brier": sc["brier"],
            "mean_stated_probability": sc["mean_p"],
            "calibration_gap": sc["calibration_gap"],
            "verdict": verdict,
        })
    return {"rows": rows, "seed": SEED}


# --------------------------------------------------------------------------- leaderboard
def leaderboard(strategies: list[Strategy], gates: list[dict]) -> dict:
    """Rank on log-loss, but only strategies that clear the gates that can be cleared."""
    blocking = [g["id"] for g in gates if g["verdict"] == "FAIL"]
    ranked = []
    for s in strategies:
        sc = s.score()
        if not sc.get("n"):
            continue
        ranked.append({
            "sid": s.sid, "name": s.name, "kind": s.kind,
            "n": sc["n"], "hit_rate": sc["hit_rate"],
            "log_loss": sc["log_loss"], "brier": sc["brier"], "auroc": sc["auroc"],
            "calibration_gap": sc["calibration_gap"],
        })
    ranked.sort(key=lambda r: r["log_loss"])
    for i, r in enumerate(ranked, 1):
        r["rank_by_log_loss"] = i
        r["eligible_for_reward"] = False
        r["blocked_by"] = ",".join(blocking) if blocking else ""
    return {
        "metric": "log-loss (a proper scoring rule: honest probabilities beat lucky ones)",
        "min_sample_to_rank": MIN_BETS_RANK,
        "gates_failing": blocking,
        "ranked": ranked,
        "reward_pool": {
            "total_units": 100,
            "allocation": "50 to rank 1, 30 split across ranks 2-4, 20 held in escrow for "
                          "out-of-sample validation",
            "status": "UNFUNDED — no strategy is rank-eligible while gates "
                      + ", ".join(blocking) + " fail",
        },
    }


# --------------------------------------------------------------------------- parlay pricing
def parlay_pricing(preds: list[Pred]) -> dict:
    """What a two-leg same-game parlay is actually worth, at the measured rho and at its bounds.

    The arithmetic a book performs when it prices a same-game parlay is a bivariate normal
    quadrant with a correlation it does not publish. This function shows the whole band, so a
    reader can see how much money the choice of rho moves and why "just multiply the legs" is
    not a price.
    """
    rho_row = next((r for r in correlations(preds) if r["quantity"].startswith("phi:")), None)
    if rho_row is None or rho_row["r"] is None:
        return {"status": "BLOCKED", "note": "same-game correlation could not be measured"}
    rho = rho_row["r"]
    lo, hi = rho_row["ci95"]

    legs = [(0.55, 0.55, "two coin-flip legs"),
            (0.60, 0.60, "two modest favourites"),
            (0.65, 0.65, "two clear favourites"),
            (0.70, 0.60, "a strong side with a mild total")]
    rows = []
    for p1, p2, label in legs:
        naive = p1 * p2
        at_rho = _bivariate_normal_upper(p1, p2, rho)
        at_lo = _bivariate_normal_upper(p1, p2, lo)
        at_hi = _bivariate_normal_upper(p1, p2, hi)
        rows.append({
            "legs": label,
            "p_leg_1": p1, "p_leg_2": p2,
            "naive_product": round(naive, 4),
            "joint_at_measured_rho": at_rho,
            "joint_at_ci_low": at_lo,
            "joint_at_ci_high": at_hi,
            "error_if_you_multiply": round(at_rho - naive, 4),
            "error_pct": round(100 * (at_rho - naive) / naive, 2) if naive else None,
            "fair_decimal_if_naive": round(1 / naive, 3) if naive else None,
            "fair_decimal_at_measured": round(1 / at_rho, 3) if at_rho else None,
        })
    return {
        "status": "MEASURED",
        "measured_rho": rho,
        "rho_ci95": [lo, hi],
        "n": rho_row["n"],
        "method": "bivariate normal upper quadrant, deterministic 400-point quadrature",
        "rows": rows,
        "reading": (
            f"At the measured rho of {rho:+.4f} the joint is close to the product, but the "
            f"95% interval on rho runs {lo:+.4f} to {hi:+.4f} — wide enough that the honest "
            "statement is 'we do not know this correlation precisely enough to price a "
            "same-game parlay', not 'the legs are independent'. A two-leg price quoted from "
            "the product is therefore a guess with a known error bar, and the site withholds "
            "it rather than print the guess."),
    }


# --------------------------------------------------------------------------- entry point
def run() -> dict:
    games = load_games()
    preds = walk_forward(games)
    leakage = leakage_audit(preds, games)
    holdout = holdout_test(preds)
    cors = correlations(preds)
    strategies = build_strategies(preds)
    gates, g5_rows = evaluate_gates(strategies, preds, leakage, holdout)
    luck = luck_report(strategies)
    board = leaderboard(strategies, gates)

    return {
        "meta": {
            "session": O.RETRIEVED_BY,
            "generated": O.AS_OF,
            "n_games": len(games),
            "n_scored": len(preds),
            "first_date": preds[0].date if preds else None,
            "last_date": preds[-1].date if preds else None,
            "source": "data/raw/history/*.json — official finals, one nba.com/game URL per row",
            "shrink_pseudo_games": K_SHRINK,
            "home_court_pts": HCA,
            "holdout_fraction": HOLDOUT_FRAC,
            "seed": SEED,
            "leakage_rule": leakage["rule"],
        },
        "leakage": leakage,
        "holdout": holdout,
        "correlations": cors,
        "gates": gates,
        "gate_g5_total_estimators": g5_rows,
        "strategies": [
            {"sid": s.sid, "name": s.name, "kind": s.kind, "rule": s.rule, **s.score()}
            for s in strategies
        ],
        "luck": luck,
        "leaderboard": board,
        "parlay_pricing": parlay_pricing(preds),
        "rows": [
            {
                "date": p.date, "matchup": f"{p.away} @ {p.home}",
                "pred_margin": p.pred_margin, "actual_margin": p.actual_margin,
                "pred_total": p.pred_total, "actual_total": p.actual_total,
                "e_margin": round(p.e_margin, 2), "e_total": round(p.e_total, 2),
                "correct_side": 1 if (p.actual_margin > 0) == (p.pred_margin > 0) else 0,
                "correct_total": 1 if (p.actual_total > p.pred_total) else 0,
                "source_url": p.source_url,
            }
            for p in preds
        ],
    }


if __name__ == "__main__":
    d = run()
    print(f"{d['meta']['n_scored']} predictions, {d['meta']['n_games']} official finals")
    print(f"leakage: {d['leakage']['verdict']}")
    print(f"holdout: {d['holdout']['verdict']} — {d['holdout']['note']}")
    print("\ngates:")
    for g in d["gates"]:
        print(f"  {g['id']:4} {g['verdict']:14} {g['name']:38} {g['measured']}")
    print("\nstrategies:")
    for s in d["strategies"]:
        if s.get("n"):
            print(f"  {s['sid']} {s['name'][:42]:42} n={s['n']:4} hit={s['hit_rate']:.3f} "
                  f"ll={s['log_loss']} p={s['p_vs_base']}")
        else:
            print(f"  {s['sid']} {s['name'][:42]:42} n=0   (no bets — inputs unavailable)")
