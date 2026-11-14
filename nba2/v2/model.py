"""v2 line-origination model — official inputs only, every parameter fitted and cross-checked.

Design rules
------------
1. **No hand-set competitive parameter.** Margin volatility (σ), home-court advantage (h)
   and per-team rating variance (τ²) are fitted, not assumed.
2. **Two independent estimators for rating.** (a) official *point differential* per game and
   (b) official *NetRtg* per 100 possessions. They are computed separately and then their
   agreement is measured — if they disagree, conviction is low (published as such).
3. **Shrink toward the mean by measured reliability**, using the empirical-Bayes weight
   λ = τ²/(τ²+se²) with se² = σ²/games.
4. **A line is a projection, not a price.** No market price exists in this build, so no
   output is a "value bet" and stake is always zero.
5. **Anything needing per-game data is BLOCKED**, not estimated.

Formulas (published on the site so they can be re-derived)
----------------------------------------------------------
pre-shot margin  = (rating_home + h) − rating_away
p(home win)      = Φ(margin/σ)                      [normal approximation]
p(home covers L) = Φ((margin − L)/σ)                [home spread L, negative = home favoured]
total            = PF_home_exp + PF_away_exp
PF_team_exp      = (PF_team + PA_opp)/2 + ((PF_team − PA_team) − (PF_opp − PA_opp))/2
                 = league-scoring level preserved on average
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import official as O


def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _var(xs):
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


# --------------------------------------------------------------------------- ratings
@dataclass
class Team:
    tri: str
    name: str
    w: int
    l: int
    gp: int
    pf: float
    pa: float
    netrtg: float
    netrtg_off: float
    netrtg_def: float
    pace: float
    pie: float
    home_w: int
    home_l: int
    road_w: int
    road_l: int
    net_pts: float = 0.0        # raw points per game differential (official PF−PA)
    rating: float = 0.0         # shrunk consensus rating, points per game
    r_diff: float = 0.0         # shrunk points-differential-only rating
    r_rtg: float = 0.0          # shrunk NetRtg-only rating (rescaled to points)
    disagreement: float = 0.0   # |r_diff − r_rtg| in points
    reliability: float = 0.0
    se: float = 0.0
    expected_wins: float = 0.0
    luck: float = 0.0
    luck_z: float = 0.0
    src: str = ""

    def as_dict(self):
        return {
            "tricode": self.tri, "name": self.name,
            "w": self.w, "l": self.l, "gp": self.gp, "wl": f"{self.w}-{self.l}",
            "pf": self.pf, "pa": self.pa, "net_pts": round(self.net_pts, 2),
            "netrtg": self.netrtg, "oeff": self.netrtg_off, "deff": self.netrtg_def,
            "pace": self.pace, "pie": self.pie,
            "rating": round(self.rating, 2),
            "r_diff": round(self.r_diff, 2), "r_rtg": round(self.r_rtg, 2),
            "disagreement": round(self.disagreement, 2),
            "reliability": round(self.reliability, 3), "se": round(self.se, 3),
            "expected_wins": round(self.expected_wins, 2),
            "luck": round(self.luck, 2), "luck_z": round(self.luck_z, 2),
            "home": f"{self.home_w}-{self.home_l}", "road": f"{self.road_w}-{self.road_l}",
            "src": self.src,
        }


@dataclass
class Calibration:
    margin_sd: float
    hca: float
    league_offset: float
    rmse_wins: float
    rmse_baseline: float
    tau_sq: float
    rmse_unconstrained: float
    sigma_unconstrained: float
    hca_unconstrained: float
    se_mean: float
    lambda_mean: float
    home_win_rate: float
    home_rate_se: float
    impl_hca_from_win_rate: float
    tied: bool
    search_grid: str

    def as_dict(self):
        d = self.__dict__.copy()
        # Published to 6 dp for byte-stable serialisation: mu comes from a 200-step bisection
        # over math.erf, whose last ulp differs across libm builds (arena sandbox vs GitHub
        # runners), and the resulting 17-digit repr made the Pages parity check fail on every
        # environment change (Publish runs for PRs #34/#39/#40). The computation keeps full
        # precision — this rounding touches only the published artefact, and 6 dp is far below
        # the 2 dp at which any downstream value is displayed or compared.
        d["league_offset"] = round(d["league_offset"], 6)
        return d


def _fit_sigma_hca(ratings: dict, gp: dict, wins: dict):
    """Least-squares (σ, h) on official win totals, using official point differentials as ratings.

    h is allowed to go negative so the optimum identifies itself; the grid is published.
    """
    best = None
    s = 8.00
    while s <= 20.00 + 1e-9:
        h = -2.00
        while h <= 6.00 + 1e-9:
            err = 0.0
            for t, r in ratings.items():
                p = 0.5 * (phi((r + h) / s) + phi((r - h) / s))
                err += (gp[t] * p - wins[t]) ** 2
            if best is None or err < best[0] - 1e-12:
                best = (err, round(s, 2), round(h, 2))
            h = round(h + 0.01, 2)
        s = round(s + 0.01, 2)
    return best


def _fit_constrained(ratings, gp, wins, p_home):
    """Fit σ with h *pinned* by the directly observed league home-win rate.

    Unconstrained, (σ, h) is only weakly identified: σ from 9 to 13 fits the win totals
    equally well with h from +7.9 down to 0.0. Pinning h = σ·(2p−1) uses a quantity we
    actually measured (home W-L over 173 games) and leaves one free parameter.
    """
    best = None
    s = 10.00
    while s <= 16.00 + 1e-9:
        h = s * (2.0 * p_home - 1.0)
        err = 0.0
        for t, r in ratings.items():
            ph = 0.5 * (phi((r + h) / s) + phi((r - h) / s))
            err += (gp[t] * ph - wins[t]) ** 2
        if best is None or err < best[0] - 1e-12:
            best = (err, round(s, 2), round(h, 4))
        s = round(s + 0.01, 2)
    return best


def calibrate(teams: dict[str, Team]) -> Calibration:
    gp = {t: x.gp for t, x in teams.items()}
    wins = {t: x.w for t, x in teams.items()}
    raw = {t: x.net_pts for t, x in teams.items()}
    i0 = O.integrity()
    err, s, h = _fit_constrained(raw, gp, wins, i0["home_win_rate"])

    # A least-squares fit does not force Σ(expected wins) = Σ(wins). Without that identity the
    # per-team luck residuals do not sum to zero, so a "lucky" team would be offset by nobody.
    # Solve for the league intercept mu that makes the identity exact (bisection, monotone).
    target = float(sum(wins.values()))

    def total_wins(mu):
        return sum(gp[t] * 0.5 * (phi((raw[t] + mu + h) / s) + phi((raw[t] + mu - h) / s)) for t in teams)

    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if total_wins(mid) < target:
            lo = mid
        else:
            hi = mid
    mu = (lo + hi) / 2.0          # deliberately not rounded: the identity must hold exactly
    err = sum((gp[t] * 0.5 * (phi((raw[t] + mu + h) / s) + phi((raw[t] + mu - h) / s)) - wins[t]) ** 2
              for t in teams)
    rmse = math.sqrt(err / len(teams))
    # baseline: ignore the ratings entirely and predict 50% for every game
    base = sum((0.5 * gp[t] - wins[t]) ** 2 for t in teams)
    rmse_base = math.sqrt(base / len(teams))

    game_sd = math.sqrt(_var(list(raw.values())))
    se = {t: s / math.sqrt(gp[t]) for t in teams}
    se_mean = sum(se.values()) / len(se)
    tau_sq = max(0.0, _var(list(raw.values())) - sum(v * v for v in se.values()) / len(se))

    i = O.integrity()
    hwr = i["home_win_rate"]
    n_home = i["home_w"] + i["home_l"]
    se_hwr = math.sqrt(0.25 / n_home)
    impl_h = s * (2.0 * hwr - 1.0)          # Φ(k)=p  →  k = 2p−1 for the average matchup

    def lam(t):
        return tau_sq / (tau_sq + se[t] ** 2) if tau_sq > 0 else 1.0

    un_err, un_s, un_h = _fit_sigma_hca(raw, gp, wins)
    return Calibration(
        league_offset=mu,
        margin_sd=s, hca=h, rmse_wins=round(rmse, 4), rmse_baseline=round(rmse_base, 4),
        rmse_unconstrained=round(math.sqrt(un_err / len(teams)), 4),
        sigma_unconstrained=un_s, hca_unconstrained=un_h,
        tau_sq=round(tau_sq, 3), se_mean=round(se_mean, 3),
        lambda_mean=round(sum(lam(t) for t in teams) / len(teams), 3),
        home_win_rate=hwr, home_rate_se=round(se_hwr, 4),
        impl_hca_from_win_rate=round(impl_h, 2),
        tied=False,
        search_grid="σ 10.00–16.00 step 0.01 with h = σ(2p−1) pinned by the observed home win rate; "
                    "the unconstrained (σ, h) grid 8–20 / −2…+6 is also reported to show the identification problem",
    )


def build_teams() -> tuple[dict[str, Team], Calibration]:
    teams: dict[str, Team] = {}
    for tri, v in O.TEAMS.items():
        w, l, hw, hl, rw, rl, pf, pa, oeff, deff, net, pace, pie = v
        t = Team(tri=tri, name=O.NAMES[tri], w=w, l=l, gp=w + l, pf=pf, pa=pa,
                 netrtg=net, netrtg_off=oeff, netrtg_def=deff, pace=pace, pie=pie,
                 home_w=hw, home_l=hl, road_w=rw, road_l=rl,
                 net_pts=pf - pa, src=O.TEAM_SOURCE[tri])
        teams[tri] = t
    cal = calibrate(teams)

    # --- ratings: two independent estimators, each shrunk by its own reliability
    for t in teams.values():
        se = cal.margin_sd / math.sqrt(t.gp)
        tau2 = cal.tau_sq
        lam = tau2 / (tau2 + se ** 2) if tau2 > 0 else 1.0
        t.se = se
        t.reliability = lam
        # (a) points-differential estimator, shrunk toward the league mean
        mean_pts = sum(x.net_pts for x in teams.values()) / len(teams)
        t.r_diff = mean_pts + cal.league_offset + lam * (t.net_pts - mean_pts)
        # (b) NetRtg estimator: NetRtg is per-100-possession; convert to points per game
        #     with each team's own pace (possessions per 48 min ≈ pace).
        per_game_rtg = t.netrtg * t.pace / 100.0
        mean_rtg_pg = sum(x.netrtg * x.pace / 100.0 for x in teams.values()) / len(teams)
        t.r_rtg = mean_rtg_pg + cal.league_offset + lam * (per_game_rtg - mean_rtg_pg)
        t.disagreement = abs(t.r_diff - t.r_rtg)
        t.rating = 0.5 * (t.r_diff + t.r_rtg)      # consensus of the two estimators
        # expected wins & luck under the fitted league model
        p = 0.5 * (phi((t.net_pts + cal.league_offset + cal.hca) / cal.margin_sd)
                   + phi((t.net_pts + cal.league_offset - cal.hca) / cal.margin_sd))
        t.expected_wins = t.gp * p
        t.luck = t.w - t.expected_wins
        var = t.gp * p * (1 - p)
        t.luck_z = t.luck / math.sqrt(var) if var > 0 else 0.0
    return teams, cal


# --------------------------------------------------------------------------- lines
@dataclass
class Line:
    """One originated line. Sign convention: ``margin`` > 0 means the HOME team wins by that many.
    ``spread`` is the HOME team's handicap (negative = home favoured), quoted to the nearest 0.5.
    """
    date: str
    time_et: str
    game_id: str
    away: str
    home: str
    arena: str
    city: str
    tv: str
    cup: str
    margin: float = 0.0
    spread: float = 0.0
    p_home: float = 0.0
    p_home_cover: float = 0.0
    fair_home: float = 0.0
    fair_away: float = 0.0
    total: float = 0.0
    pts_home: float = 0.0
    pts_away: float = 0.0
    total_b: float = 0.0
    pts_home_b: float = 0.0
    pts_away_b: float = 0.0
    total_gap: float = 0.0
    sigma_used: float = 0.0
    conviction: float = 0.0
    est_a: float = 0.0          # home spread implied by the points-differential rating
    est_b: float = 0.0          # home spread implied by the NetRtg rating
    agreement: float = 0.0
    grade: str = "C"
    grade_reason: str = ""
    pick_status: str = "WITHHELD"
    flags: list = field(default_factory=list)
    source_url: str = ""        # official nba.com game page for THIS row

    @property
    def matchup(self):
        return f"{self.away} @ {self.home}"

    def as_dict(self):
        return {
            "date": self.date, "time_et": self.time_et, "game_id": self.game_id,
            "matchup": self.matchup, "arena": self.arena, "city": self.city,
            "tv": self.tv, "cup": self.cup,
            "margin": round(self.margin, 2),
            "spread": self.spread,
            "p_home": round(self.p_home, 4),
            "p_home_cover": round(self.p_home_cover, 4),
            "fair_home": round(self.fair_home, 3), "fair_away": round(self.fair_away, 3),
            "total": round(self.total, 1),
            "pts_home": round(self.pts_home, 1), "pts_away": round(self.pts_away, 1),
            "total_b": round(self.total_b, 1),
            "pts_home_b": round(self.pts_home_b, 1), "pts_away_b": round(self.pts_away_b, 1),
            "total_gap": round(self.total_gap, 2),
            "sigma": round(self.sigma_used, 2), "conviction": round(self.conviction, 2),
            "est_a": round(self.est_a, 1), "est_b": round(self.est_b, 1),
            "agreement": round(self.agreement, 2),
            "grade": self.grade, "grade_reason": self.grade_reason,
            "source_url": self.source_url,
            "pick_status": self.pick_status, "flags": self.flags,
        }


def _half(x: float) -> float:
    """Round to the nearest 0.5 (how lines are actually quoted)."""
    return round(x * 2.0) / 2.0


def originated_lines(teams, cal) -> list[Line]:
    out = []
    lg = O.integrity()["league_pts_per_team_game"]
    for (date, time_et, away, home, gid, arena, city, tv, cup) in sorted(O.SLATE):
        a, h = teams[away], teams[home]
        ln = Line(date=date, time_et=time_et, game_id=gid, away=away, home=home,
                  arena=arena, city=city, tv=tv, cup=cup,
                  source_url=f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}")
        # ---- estimator A: consensus of the two shrunk ratings
        ln.margin = (h.rating + cal.hca) - a.rating
        ln.spread = -_half(ln.margin)                       # home handicap
        ln.p_home = phi(ln.margin / cal.margin_sd)
        ln.p_home_cover = phi((ln.margin + ln.spread) / cal.margin_sd)   # covers our own number
        ln.fair_home = 1.0 / ln.p_home if ln.p_home > 1e-9 else float("inf")
        ln.fair_away = 1.0 / (1.0 - ln.p_home) if ln.p_home < 1 else float("inf")
        ln.sigma_used = cal.margin_sd
        ln.conviction = abs(ln.margin) / cal.margin_sd
        ln.est_a = -_half((h.r_diff + cal.hca) - a.r_diff)
        ln.est_b = -_half((h.r_rtg + cal.hca) - a.r_rtg)
        ln.agreement = abs(ln.est_a - ln.est_b)
        # ---- total, estimator A: per-game scoring averages, league level preserved
        ln.pts_home = (h.pf + a.pa) / 2.0 + ((h.pf - h.pa) - (a.pf - a.pa)) / 2.0
        ln.pts_away = (a.pf + h.pa) / 2.0 + ((a.pf - a.pa) - (h.pf - h.pa)) / 2.0
        ln.total = ln.pts_home + ln.pts_away
        # ---- total, estimator B: official per-100 ratings × official pace
        poss = (h.pace + a.pace) / 2.0
        ln.pts_home_b = (h.netrtg_off + a.netrtg_def) / 2.0 * poss / 100.0
        ln.pts_away_b = (a.netrtg_off + h.netrtg_def) / 2.0 * poss / 100.0
        ln.total_b = ln.pts_home_b + ln.pts_away_b
        # Both estimators are calibrated to the league level only if they reproduce it; report the gap.
        ln.total_gap = ln.total - ln.total_b

        reasons = []
        if a.gp < 10 or h.gp < 10:
            reasons.append("fewer than 10 official games")
        if ln.agreement > 2.0:
            reasons.append(f"spread estimators differ by {ln.agreement:.1f} pts")
        if abs(ln.total_gap) > 4.0:
            reasons.append(f"total estimators differ by {ln.total_gap:+.1f} pts")
        if reasons:
            ln.grade, ln.grade_reason = "C", "; ".join(reasons)
        elif ln.agreement <= 1.0 and ln.conviction >= 0.75 and abs(ln.total_gap) <= 2.0:
            ln.grade = "A"
            ln.grade_reason = "estimators agree ≤1.0 pts, |margin| ≥ 0.75σ, totals agree ≤2.0 pts"
        else:
            ln.grade = "B"
            ln.grade_reason = "passes minimum gates; below the A bar"
        # A projection grade is NOT a bet grade. G6 (market price) and G7 (backtest) cannot pass.
        ln.pick_status = "WITHHELD (gate G6 no market price, G7 no settlement data)"
        ln.flags = ["FLAG-V2-NO-MARKET-PRICE", "FLAG-V2-NO-BACKTEST"]
        out.append(ln)
    return out


# --------------------------------------------------------------------------- parlays
def parlay_math(p_legs, n_legs, price=-110.0):
    """What a parlay must beat. Pure arithmetic — reproducible with a calculator."""
    dec_leg = 1.0 + 100.0 / abs(price)          # 1.9091 at -110
    fair_leg = abs(price) / (abs(price) + 100.0)  # 0.5238 at -110 (break-even prob of one leg)
    true_leg = 0.5                              # a fair coin would be 0.50 at even money
    dec_parlay = dec_leg ** n_legs
    break_even = 1.0 / dec_parlay
    fair_parlay_dec = (1.0 / true_leg) ** n_legs
    hold_leg = 1.0 - dec_leg / (1.0 / true_leg)   # 0.9545 at -110 → 4.55% hold per leg
    return {
        "n_legs": n_legs,
        "decimal_leg": round(dec_leg, 4),
        "decimal_parlay": round(dec_parlay, 3),
        "break_even_prob": round(break_even, 6),
        "fair_parlay_decimal": round(fair_parlay_dec, 3),
        "hold_per_leg_pct": round(100 * hold_leg, 3),
        "hold_n_legs_pct": round(100 * (1.0 - (1.0 - hold_leg) ** n_legs), 3),
    }


def swing_cost(delta_p):
    """Probability error from treating correlated legs as independent.

    If the true joint probability differs from the product by a factor (1+δ), the
    probability error is p_ind·δ. We publish the mapping from δ to required extra edge.
    """
    return delta_p
