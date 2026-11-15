"""v3 model: the brief's arithmetic, implemented once and published.

Every function here answers one line of the brief. Each is deliberately small enough to be
re-derived by hand from the tables on the site.

  * ``calibrate``          — σ fitted by least squares with **h pinned** to the measured
                             home-win rate (never fitted freely).
  * ``two_estimators``     — two *independent* ratings, kept separate; their disagreement is
                             the published confidence number. No blend is the headline.
  * ``luck_z``             — a per-team z-score for wins above/below the fitted expectation.
  * ``total_from_possessions`` — total = possessions × points-per-possession, from the
                             official POSS and OffRtg/DefRtg columns. NOT an average of
                             scoring averages; the average-of-averages total is printed
                             beside it as the thing that was replaced.
  * ``market_prior``       — blend the model with a market line, weighted by the measured
                             out-of-sample log-loss of each. With no market feed the market
                             input is absent, so the blended line is withheld and the weight
                             that *would* apply is published.
  * ``rest_travel``        — rest, back-to-back and 3-in-4 from the official schedule, plus
                             great-circle travel from the cited arena table.
  * ``minutes_shares``     — top-8 minute shares and the replacement share when a player is
                             out, from an official box score.

Nothing here reads v2's frozen snapshot: the inputs are ``nba2.v3.official``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import official as O

# --------------------------------------------------------------------------- helpers


def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def inv_phi(p: float) -> float:
    """Inverse standard normal CDF — Acklam's rational approximation, refined once by Newton.

    Needed because pinning home advantage to a measured home-win rate is p -> h = σ·Φ⁻¹(p), and
    the linear shortcut σ(2p−1) is only a first-order approximation. At p = 0.529 the shortcut
    is off by 0.006 in probability, which is enough to make the published h fail to reproduce
    the rate it claims to be pinned to.
    """
    if p <= 0.0:
        return float("-inf")
    if p >= 1.0:
        return float("inf")
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    elif p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    else:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    # one Newton step against the exact CDF
    e = phi(x) - p
    u = e * math.sqrt(2 * math.pi) * math.exp(x * x / 2)
    return x - u / (1 + x * u / 2)


def phi2(h: float, k: float, rho: float) -> float:
    """Standard bivariate normal CDF by Simpson quadrature on the conditional form.

    P(X<h, Y<k) = ∫_{-∞}^{h} φ(x) Φ((k − rho·x)/sqrt(1−rho²)) dx
    Deterministic and reproducible; accuracy checked against known closed forms in the tests.
    """
    if not -0.999 < rho < 0.999:
        raise ValueError("rho must be inside (-0.999, 0.999); use the degenerate forms instead")
    if h == float("inf"):
        return phi(k)
    lo, hi = -9.0, h
    n = 4000
    if n % 2:
        n += 1
    dx = (hi - lo) / n
    s = 0.0
    for i in range(n + 1):
        x = lo + i * dx
        w = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
        s += w * math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi) * phi((k - rho * x) / math.sqrt(1 - rho * rho))
    return s * dx / 3.0


def var(xs) -> float:
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def pearson(xs, ys) -> tuple[float, int]:
    """Return (r, n). Written out so the published r can be recomputed by hand."""
    xs, ys = list(xs), list(ys)
    n = min(len(xs), len(ys))
    if n < 3:
        return 0.0, n
    mx, my = mean(xs[:n]), mean(ys[:n])
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    sxx = sum((xs[i] - mx) ** 2 for i in range(n))
    syy = sum((ys[i] - my) ** 2 for i in range(n))
    if sxx <= 0 or syy <= 0:
        return 0.0, n
    return sxy / math.sqrt(sxx * syy), n


def rho_ci(r: float, n: int) -> tuple[float, float]:
    """Fisher z 95% interval. Published beside every measured correlation."""
    if n < 4:
        return (float("nan"), float("nan"))
    z = math.atanh(max(-0.999999, min(0.999999, r)))
    se = 1.0 / math.sqrt(n - 3)
    return (math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se))


# --------------------------------------------------------------------------- team table
@dataclass
class Team:
    tri: str
    name: str
    w: int
    l: int
    gp: int
    home: str
    road: str
    streak: str
    last10: str
    # traditional (per game)
    pts: float
    opp_pts: float
    tpm: float
    tpa: float
    tov: float
    # advanced
    off_rtg: float
    def_rtg: float
    net_rtg: float
    pace: float
    poss: float
    pie: float
    # derived
    net_pts: float = 0.0
    poss_pg: float = 0.0
    ppp_off: float = 0.0        # points scored per possession
    ppp_def: float = 0.0        # points allowed per possession
    r_diff: float = 0.0
    r_rtg: float = 0.0
    disagreement: float = 0.0
    reliability: float = 0.0
    se: float = 0.0
    expected_wins: float = 0.0
    luck: float = 0.0
    luck_z: float = 0.0
    luck_band: str = ""

    def as_dict(self):
        return {
            "tricode": self.tri, "name": self.name, "w": self.w, "l": self.l, "gp": self.gp,
            "wl": f"{self.w}-{self.l}", "home": self.home, "road": self.road,
            "streak": self.streak, "last10": self.last10,
            "pts": self.pts, "opp_pts": self.opp_pts, "net_pts": round(self.net_pts, 2),
            "off_rtg": self.off_rtg, "def_rtg": self.def_rtg, "net_rtg": self.net_rtg,
            "pace": self.pace, "poss": self.poss, "pie": self.pie,
            "poss_pg": round(self.poss_pg, 2),
            "ppp_off": round(self.ppp_off, 4), "ppp_def": round(self.ppp_def, 4),
            "r_diff": round(self.r_diff, 3), "r_rtg": round(self.r_rtg, 3),
            "disagreement": round(self.disagreement, 3),
            "reliability": round(self.reliability, 4), "se": round(self.se, 3),
            "expected_wins": round(self.expected_wins, 2), "luck": round(self.luck, 2),
            "luck_z": round(self.luck_z, 2), "luck_band": self.luck_band,
        }


@dataclass
class Calibration:
    margin_sd: float
    hca: float
    home_win_rate: float
    home_rate_se: float
    home_games: int
    rmse_wins: float
    rmse_baseline: float
    tau_sq: float
    lambda_mean: float
    sigma_unconstrained: float
    hca_unconstrained: float
    rmse_unconstrained: float
    league_offset: float
    grid: str
    free_fit_note: str = ""      # why the unconstrained fit is reported but not used

    def as_dict(self):
        return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


def load_teams() -> dict[str, Team]:
    out = {}
    for tri, s in O.STANDINGS.items():
        t = O.TRAD[tri]
        a = O.ADV[tri]
        o = O.OPP[tri]
        gp = int(t["gp"])
        te = Team(
            tri=tri, name=O.NAMES[tri], w=int(s["w"]), l=int(s["l"]), gp=gp,
            home=s["home"], road=s["road"], streak=s["streak"], last10=s["last10"],
            pts=t["pts"], opp_pts=o["opp_pts"], tpm=t["tpm"], tpa=t["tpa"], tov=t["tov"],
            off_rtg=a["off_rtg"], def_rtg=a["def_rtg"], net_rtg=a["net_rtg"],
            pace=a["pace"], poss=a["poss"], pie=a["pie"],
        )
        te.net_pts = t["pts"] - o["opp_pts"]
        te.poss_pg = a["poss"] / gp                  # official season POSS / games played
        te.ppp_off = t["pts"] / te.poss_pg           # points per possession scored
        te.ppp_def = o["opp_pts"] / te.poss_pg       # points per possession allowed
        out[tri] = te
    return out


# --------------------------------------------------------------------------- calibration
def _fit_sigma_pinned(net_pts: dict, gp: dict, wins: dict, p_home: float):
    """One free parameter (σ) with h = σ·Φ⁻¹(p_home) pinned by the measured home-win rate.

    This used the first-order shortcut h = σ(2p−1) until a test showed the published h
    reproduced a 0.5234 home rate against the 0.5294 it was pinned to. The shortcut is the
    tangent line at p = 0.5; it is exact there and stale everywhere else. Φ⁻¹ is used instead so
    that "pinned to the measured rate" is literally true and checkable in one line.
    """
    best = None
    z_pin = inv_phi(p_home)
    s = 8.00
    while s <= 22.00 + 1e-9:
        h = s * z_pin
        err = 0.0
        for t, r in net_pts.items():
            ph = 0.5 * (phi((r + h) / s) + phi((r - h) / s))
            err += (gp[t] * ph - wins[t]) ** 2
        if best is None or err < best[0] - 1e-12:
            best = (err, round(s, 2), round(h, 4))
        s = round(s + 0.01, 2)
    return best


def _fit_sigma_hca_free(net_pts: dict, gp: dict, wins: dict):
    """The unconstrained fit, published only to *show* that the pair is weakly identified."""
    best = None
    s = 6.00
    while s <= 26.00 + 1e-9:
        h = -6.00
        while h <= 12.00 + 1e-9:
            err = 0.0
            for t, r in net_pts.items():
                ph = 0.5 * (phi((r + h) / s) + phi((r - h) / s))
                err += (gp[t] * ph - wins[t]) ** 2
            if best is None or err < best[0] - 1e-12:
                best = (err, round(s, 2), round(h, 2))
            h = round(h + 0.02, 2)
        s = round(s + 0.02, 2)
    return best


def calibrate(teams: dict[str, Team]) -> Calibration:
    i = integrity()
    p_home = i["home_win_rate"]
    n_home = i["home_games"]
    se = math.sqrt(0.25 / n_home)

    net = {t: x.net_pts for t, x in teams.items()}
    gp = {t: x.gp for t, x in teams.items()}
    wins = {t: x.w for t, x in teams.items()}

    # --- HCA is PINNED. This is the brief's requirement, not a convenience: the free fit
    #     trades σ against h almost flatly (see sigma_unconstrained below), so a freely fitted
    #     h is a number the data cannot defend.
    _, s, h = _fit_sigma_pinned(net, gp, wins, p_home)

    # League intercept μ makes Σ expected wins == Σ actual wins exactly, so luck sums to zero.
    target = float(sum(wins.values()))

    def total_wins(mu):
        return sum(gp[t] * 0.5 * (phi((net[t] + mu + h) / s) + phi((net[t] + mu - h) / s)) for t in teams)

    lo, hi = -12.0, 12.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if total_wins(mid) < target:
            lo = mid
        else:
            hi = mid
    mu = (lo + hi) / 2

    err = sum((gp[t] * 0.5 * (phi((net[t] + mu + h) / s) + phi((net[t] + mu - h) / s)) - wins[t]) ** 2
              for t in teams)
    rmse = math.sqrt(err / len(teams))
    base = sum((0.5 * gp[t] - wins[t]) ** 2 for t in teams)
    rmse_base = math.sqrt(base / len(teams))

    se_t = {t: s / math.sqrt(gp[t]) for t in teams}
    tau_sq = max(0.0, var(list(net.values())) - sum(v * v for v in se_t.values()) / len(se_t))
    lam = {t: (tau_sq / (tau_sq + se_t[t] ** 2) if tau_sq > 0 else 1.0) for t in teams}

    err_u, s_u, h_u = _fit_sigma_hca_free(net, gp, wins)
    rmse_unconstrained = math.sqrt(err_u / len(teams))
    free_home_rate = phi(h_u / s_u)
    free_note = (
        f"The unconstrained fit buys an RMSE of {round(rmse_unconstrained, 4)} against the pinned "
        f"{round(rmse, 4)} — a gain of {round(rmse - rmse_unconstrained, 4)} — by claiming "
        f"a home-win rate of {free_home_rate:.4f} against the measured {p_home:.4f}. That is "
        f"the whole argument for pinning: the free parameter spends its freedom on a home rate no "
        f"season has ever produced, and the RMSE gain is too small to distinguish from noise."
    )
    return Calibration(
        margin_sd=s, hca=h, home_win_rate=p_home, home_rate_se=round(se, 4), home_games=n_home,
        rmse_wins=round(rmse, 4), rmse_baseline=round(rmse_base, 4),
        tau_sq=round(tau_sq, 3), lambda_mean=round(mean(lam.values()), 4),
        sigma_unconstrained=s_u, hca_unconstrained=h_u,
        rmse_unconstrained=round(rmse_unconstrained, 4),
        league_offset=mu, free_fit_note=free_note,
        grid=("σ searched 8.00→22.00 step 0.01 with h = σ·Φ⁻¹(p) pinned at p = the measured "
              "home-win rate; the free (σ,h) grid 6→26 / −6…+12 is reported only to show the "
              "identification problem"),
    )


# --------------------------------------------------------------------------- integrity
def integrity() -> dict:
    """Arithmetic identities the official tables must satisfy. If a transcription were
    wrong, one of these breaks. Published with the build, checked by the CI gate."""
    w = sum(int(v["w"]) for v in O.STANDINGS.values())
    l = sum(int(v["l"]) for v in O.STANDINGS.values())
    hw = sum(int(v["home"].split("-")[0]) for v in O.STANDINGS.values())
    hl = sum(int(v["home"].split("-")[1]) for v in O.STANDINGS.values())
    rw = sum(int(v["road"].split("-")[0]) for v in O.STANDINGS.values())
    rl = sum(int(v["road"].split("-")[1]) for v in O.STANDINGS.values())
    gp = sum(int(O.TRAD[t]["gp"]) for t in O.TRAD)
    pts_mass = sum(O.TRAD[t]["pts"] * O.TRAD[t]["gp"] for t in O.TRAD)
    opp_mass = sum(O.OPP[t]["opp_pts"] * O.OPP[t]["gp"] for t in O.TRAD)
    poss = sum(O.ADV[t]["poss"] for t in O.ADV)
    return {
        "teams": len(O.STANDINGS),
        "wins": w, "losses": l, "wins_equals_losses": w == l,
        "home_w": hw, "home_l": hl, "road_w": rw, "road_l": rl,
        "home_games": hw + hl,
        "home_wins_equal_road_losses": hw == rl,
        "home_losses_equal_road_wins": hl == rw,
        "home_win_rate": round(hw / (hw + hl), 4),
        "home_win_rate_se": round(math.sqrt(0.25 / (hw + hl)), 4),
        "team_games": gp, "games": gp / 2,
        "points_scored_mass": round(pts_mass, 1),
        "points_allowed_mass": round(opp_mass, 1),
        "points_identity_gap": round(pts_mass - opp_mass, 1),
        "points_rounding_bound": round(0.1 * gp, 1),
        "possessions_total": round(poss, 1),
        "possessions_implied_games": round(poss / 2 / 100, 2),
    }


# --------------------------------------------------------------------------- ratings
def two_estimators(teams: dict[str, Team], cal: Calibration) -> dict[str, Team]:
    """Two independent ratings, each shrunk by its own measured reliability.

    (A) points-per-game differential, from the official PTS and Opp PTS columns;
    (B) NetRtg × pace ÷ 100, i.e. the per-100-possession rating converted to points per game
        with the club's own official PACE.

    They are *not* averaged into a headline. ``disagreement`` is the headline; the consensus
    is kept only as a documented fallback and is labelled as such.
    """
    a_vals = {t: x.net_pts for t, x in teams.items()}
    b_vals = {t: x.net_rtg * x.pace / 100.0 for t, x in teams.items()}
    ma, mb = mean(a_vals.values()), mean(b_vals.values())
    for t in teams.values():
        se = cal.margin_sd / math.sqrt(t.gp)
        lam = cal.tau_sq / (cal.tau_sq + se ** 2) if cal.tau_sq > 0 else 1.0
        t.se = se
        t.reliability = lam
        t.r_diff = ma + cal.league_offset + lam * (a_vals[t.tri] - ma)
        t.r_rtg = mb + cal.league_offset + lam * (b_vals[t.tri] - mb)
        t.disagreement = abs(t.r_diff - t.r_rtg)
        p = 0.5 * (phi((t.net_pts + cal.league_offset + cal.hca) / cal.margin_sd)
                   + phi((t.net_pts + cal.league_offset - cal.hca) / cal.margin_sd))
        t.expected_wins = t.gp * p
        t.luck = t.w - t.expected_wins
        v = t.gp * p * (1 - p)
        t.luck_z = t.luck / math.sqrt(v) if v > 0 else 0.0
        # Noise band: |z| <= 1.96 is "inside noise". A strategy leaning on a club outside it
        # is refused by nba2/v3/strategies.py — see the brief's luck rule.
        t.luck_band = "inside noise" if abs(t.luck_z) <= 1.96 else "OUTSIDE noise band"
    return teams


# --------------------------------------------------------------------------- lines
@dataclass
class Line:
    date: str
    time_et: str
    game_id: str
    away: str
    home: str
    arena: str
    city: str
    # spread
    margin_a: float = 0.0        # home margin, estimator A
    margin_b: float = 0.0        # home margin, estimator B
    margin: float = 0.0          # fallback consensus (blend), labelled as such
    disagreement: float = 0.0
    spread_a: float = 0.0
    spread_b: float = 0.0
    p_home_a: float = 0.0
    p_home_b: float = 0.0
    p_home_lo: float = 0.0
    p_home_hi: float = 0.0
    confidence_halfwidth: float = 0.0
    # totals: possessions × points-per-possession
    poss_game: float = 0.0
    ppp_home: float = 0.0
    ppp_away: float = 0.0
    pts_home: float = 0.0
    pts_away: float = 0.0
    total: float = 0.0
    total_naive: float = 0.0     # average of the two scoring averages, printed for contrast
    total_gap: float = 0.0
    # market-anchored prior
    market_line: float | None = None
    blended_margin: float | None = None
    model_weight: float = 0.0
    # conditions
    rest_home: int | None = None
    rest_away: int | None = None
    b2b_home: bool = False
    b2b_away: bool = False
    three_in_four_home: bool = False
    three_in_four_away: bool = False
    travel_home_km: float | None = None
    travel_away_km: float | None = None
    # availability
    home_rotation: str = ""
    away_rotation: str = ""
    home_out: int = 0
    away_out: int = 0
    grade: str = "C"
    grade_reason: str = ""
    flags: list = field(default_factory=list)

    @property
    def matchup(self):
        return f"{self.away} @ {self.home}"

    def as_dict(self):
        d = {}
        for k, v in self.__dict__.items():
            if isinstance(v, float):
                d[k] = round(v, 4)
            else:
                d[k] = v
        d["matchup"] = self.matchup
        return d


def _half(x: float) -> float:
    return round(x * 2.0) / 2.0


def total_from_possessions(h: Team, a: Team, ppp_league: float) -> dict:
    """Total = possessions × points-per-possession — the brief's formulation.

    possessions for the game = mean of the two clubs' official season POSS per game
        (a game has one possession count, shared by both teams);
    points per possession for each side = mean of (that side's offensive PPP, the
        opponent's defensive PPP). A club that scores 1.12 PPP against a defence that
        allows 1.10 PPP is projected at 1.11 PPP.

    The result is *not* normalised back to the league mean: if both clubs are above-average
    scoring, the projection says so, which an average-of-averages total cannot express.
    """
    poss = (h.poss_pg + a.poss_pg) / 2.0
    home_ppp = (h.ppp_off + a.ppp_def) / 2.0
    away_ppp = (a.ppp_off + h.ppp_def) / 2.0
    return {
        "poss": poss, "ppp_home": home_ppp, "ppp_away": away_ppp,
        "pts_home": poss * home_ppp, "pts_away": poss * away_ppp,
        "total": poss * (home_ppp + away_ppp),
        "league_ppp": ppp_league,
    }


def league_ppp(teams: dict[str, Team]) -> float:
    """League points per possession, mass-weighted by official possessions."""
    scored = sum(t.pts * t.gp for t in teams.values())
    poss = sum(t.poss_pg * t.gp for t in teams.values())
    return scored / poss


def market_prior(p_model: float, p_market: float | None, w_model: float) -> dict:
    """Blend on the *probability* scale, with the weight measured, never chosen.

    w_model comes from measured out-of-sample log-loss (see ``log_loss_weights``):
        w_model = L_market / (L_model + L_market)
    so a model whose log-loss is twice the market's gets one third of the weight. If the
    market probability is absent the blend is withheld — not faked with 0.5/0.5.
    """
    if p_market is None:
        return {"blended": None, "w_model": w_model, "w_market": 1 - w_model,
                "reason": "BLOCKED input 'odds': no market price exists, so no blend is published"}
    return {"blended": w_model * p_model + (1 - w_model) * p_market,
            "w_model": w_model, "w_market": 1 - w_model, "reason": ""}


def log_loss_weights(l_model: float, l_market: float) -> dict:
    """Inverse-log-loss weights. Published with their arithmetic so the ratio is auditable."""
    if l_model <= 0 and l_market <= 0:
        return {"w_model": 0.5, "w_market": 0.5, "reason": "both losses zero"}
    denom = l_model + l_market
    if denom <= 0:
        return {"w_model": 0.5, "w_market": 0.5, "reason": "degenerate"}
    return {"w_model": l_market / denom, "w_market": l_model / denom,
            "w_model_if_ci_zero": l_market / denom, "ratio": (l_model / l_market) if l_market else None}


# --------------------------------------------------------------------------- conditions
def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


ARENA_BY_TRI = {r[0]: r for r in O.ARENAS}


def _venue(tri: str):
    r = ARENA_BY_TRI.get(tri)
    return (r[3], r[4]) if r else None


def travel_km(prev_home: str | None, this_home: str) -> float | None:
    """Great-circle distance from the previous game's venue to this game's venue.

    The venue is the home club's arena (the schedule gives one venue per game). A neutral-site
    game would break that assumption, and none of the games in this window is neutral. If
    either coordinate is missing the distance is None — blank, never estimated.
    """
    if prev_home is None:
        return None
    a, b = _venue(prev_home), _venue(this_home)
    if not a or not b:
        return None
    return round(haversine_km(a[0], a[1], b[0], b[1]), 1)


def load_history_dates() -> dict[str, list[tuple[str, str]]]:
    """(date, home) for every team from the committed official history feed.

    Read from ``data/raw/history/*.json`` — official finals captured by earlier sessions,
    each row carrying its own nba.com game URL. Used only for rest/travel lookback, never
    for a published score.
    """
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    out: dict[str, list[tuple[str, str]]] = {}
    for f in sorted((root / "data" / "raw" / "history").glob("*.json")):
        doc = json.loads(f.read_text())
        for g in doc.get("games", []):
            out.setdefault(g["away"], []).append((g["date"], g["home"]))
            out.setdefault(g["home"], []).append((g["date"], g["home"]))
    for k in out:
        out[k].sort()
    return out


def rest_travel(team: str, date: str, venue_home: str,
                history: dict[str, list[tuple[str, str]]], window: list[tuple[str, str]]) -> dict:
    """rest, back-to-back, 3-in-4 and travel for one club before one game.

    ``history`` holds committed results strictly before the window; ``window`` holds
    (date, home) for every game in the window so a club's second game in three nights is
    counted even though its result is not yet in the feed.
    """
    from datetime import date as D
    prior = [(d, hh) for (d, hh) in history.get(team, [])]
    prior += [(d, hh) for (d, hh) in window if d < date]
    prior.sort()
    if not prior:
        return {"rest": None, "b2b": False, "three_in_four": False, "travel": None,
                "prev_date": None, "prev_home": None, "n_in_4": 0}
    prev_date, prev_home = prior[-1]
    d0 = D.fromisoformat(date)
    rest = (d0 - D.fromisoformat(prev_date)).days
    dates_in_4 = [dd for dd, _ in prior if 0 < (d0 - D.fromisoformat(dd)).days <= 3] + [date]
    return {
        "rest": rest, "b2b": rest == 1, "three_in_four": len(dates_in_4) >= 3,
        "travel": travel_km(prev_home, venue_home), "prev_date": prev_date,
        "prev_home": prev_home, "n_in_4": len(dates_in_4),
    }


# --------------------------------------------------------------------------- minutes
def minutes_shares(box: dict, team: str) -> dict:
    """Top-8 minute shares from an official box score, plus what a replacement absorbs.

    A club plays 240 regulation minutes. ``top8`` is the sum of the eight largest minute
    totals divided by 240. The replacement share is that same 240-minus-top8 rate, so the
    arithmetic is: shares sum to 1.000 and the ninth man's share is exactly what is left.
    """
    rows = [p for p in box["players"] if p[1] == team]
    if len(rows) < 8:
        return {"ok": False, "reason": f"only {len(rows)} players transcribed for {team}", "top8_share": None}
    mins = sorted((p[3] for p in rows), reverse=True)
    total = sum(mins)
    top8 = sum(mins[:8])
    return {
        "ok": True, "team": team, "players": rows, "minutes_total": round(total, 1),
        "top8": round(top8, 1), "top8_share": round(top8 / total, 4) if total else None,
        "replacement_share": round((total - top8) / total, 4) if total else None,
        "top8_pct_of_240": round(top8 / 240.0, 4),
        "unused_pct_of_240": round((240.0 - total) / 240.0, 4),
    }
