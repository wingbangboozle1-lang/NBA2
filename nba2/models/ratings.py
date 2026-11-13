"""Team ratings, calibration of (sigma, HCA) and the skill/luck decomposition.

Nothing in here is hand-set. Two structural parameters that every NBA line model needs —
per-game margin volatility (sigma) and home-court advantage in points (hca) — are *fitted*
against the verified 30-team standings snapshot by least squares on win totals. Ratings
from a ~12-game sample are then shrunk toward the league mean by a reliability weight that
is itself estimated from the spread of the ratings table (empirical-Bayes / James-Stein).

This module deliberately refuses to invent numbers: if a required input is missing the
corresponding attribute is `None`, and `nba2.pipeline.lint` makes that loud.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .. import config


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _mean(xs: Iterable[float]) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def _var(xs: Iterable[float]) -> float:
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


@dataclass
class Team:
    tricode: str
    name: str
    wins: int
    losses: int
    pct: float
    ppg: float | None
    oppg: float | None
    srs: float | None
    home_w: int
    home_l: int
    road_w: int
    road_l: int
    close_w: int
    close_l: int
    blowout_w: int
    blowout_l: int
    # derived
    games: int = 0
    net_ppg: float | None = None
    reliability: float | None = None
    srs_shrunk: float | None = None
    net_shrunk: float | None = None
    expected_wins: float | None = None
    luck: float | None = None
    luck_z: float | None = None
    injury_blind: bool = True

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Calibration:
    margin_sd: float
    hca_points: float
    rmse_wins: float
    rmse_baseline_wins: float
    league_avg_points: float
    home_win_rate: float
    tau_sq: float
    se_mean: float
    n_teams: int
    grid: list = field(default_factory=list)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["grid"] = self.grid[:12]
        return d


class RatingModel:
    def __init__(self, teams: list[Team], cal: Calibration) -> None:
        self.teams = {t.tricode: t for t in teams}
        self.order = [t.tricode for t in teams]
        self.cal = cal

    # ------------------------------------------------------------------ lookups
    def get(self, tricode: str) -> Team:
        return self.teams[tricode]

    def expected_margin(self, away: str, home: str, use: str = "consensus") -> float | None:
        """Points the home team is expected to win by, before any availability signal."""
        ta, th = self.teams[away], self.teams[home]
        hca = self.cal.hca_points
        if use == "srs":
            if ta.srs_shrunk is None or th.srs_shrunk is None:
                return None
            return th.srs_shrunk - ta.srs_shrunk + hca
        if use == "net":
            if ta.net_shrunk is None or th.net_shrunk is None:
                return None
            return th.net_shrunk - ta.net_shrunk + hca
        srs = self.expected_margin(away, home, "srs")
        net = self.expected_margin(away, home, "net")
        if srs is None or net is None:
            return None
        return 0.5 * (srs + net)

    def expected_total(self, away: str, home: str) -> float | None:
        ta, th = self.teams[away], self.teams[home]
        if None in (ta.ppg, ta.oppg, th.ppg, th.oppg):
            return None
        # four-rate average: (own scoring + opponent's scoring) for both teams / 2
        return 0.5 * (th.ppg + th.oppg + ta.ppg + ta.oppg)

    def disagreement(self, away: str, home: str) -> float | None:
        a = self.expected_margin(away, home, "srs")
        b = self.expected_margin(away, home, "net")
        if a is None or b is None:
            return None
        return abs(a - b)


# --------------------------------------------------------------------------- loading
def load_teams(path: Path) -> list[Team]:
    raw = json.loads(Path(path).read_text())
    cols = raw["columns"]
    out: list[Team] = []
    for rec in raw["records"]:
        d = dict(zip(cols, rec))
        t = Team(
            tricode=d["tricode"],
            name=config.TEAM_NAMES.get(d["tricode"], d["tricode"]),
            wins=int(d["w"]),
            losses=int(d["l"]),
            pct=float(d["pct"]) if d["pct"] is not None else None,  # type: ignore[arg-type]
            ppg=None if d["psg"] is None else float(d["psg"]),
            oppg=None if d["pag"] is None else float(d["pag"]),
            srs=None if d["srs"] is None else float(d["srs"]),
            home_w=int(d["home_w"]), home_l=int(d["home_l"]),
            road_w=int(d["road_w"]), road_l=int(d["road_l"]),
            close_w=int(d["close_w"]), close_l=int(d["close_l"]),
            blowout_w=int(d["blowout_w"]), blowout_l=int(d["blowout_l"]),
        )
        t.games = t.wins + t.losses
        if t.ppg is not None and t.oppg is not None:
            t.net_ppg = round(t.ppg - t.oppg, 4)
        out.append(t)
    return out


# --------------------------------------------------------------------------- calibration
def _expected_wins(t: Team, sigma: float, hca: float, rating: str = "raw") -> float:
    if rating == "raw":
        d = t.srs if t.srs is not None else 0.0
    else:
        d = t.net_ppg if t.net_ppg is not None else 0.0
    half = t.games / 2.0
    return half * norm_cdf((d + hca) / sigma) + half * norm_cdf((d - hca) / sigma)


def calibrate(teams: list[Team]) -> Calibration:
    """Least-squares fit of (margin_sd, hca_points) against observed wins.

    Model: a team's game margin vs. a league-average opponent is Normal(mu, sigma) with
    mu = rating (+ hca at home, - hca on the road). Expected wins is the sum over that
    team's games; because the schedule is not in the snapshot we assume half home / half
    road, which is the league norm over a full season and is flagged as a simplification.
    """
    usable = [t for t in teams if t.srs is not None]

    def sse(sigma: float, hca: float) -> float:
        return sum((t.wins - _expected_wins(t, sigma, hca)) ** 2 for t in usable)

    best = (float("inf"), None, None)
    # coarse pass
    s = 6.0
    while s <= 25.0001:
        h = -1.0
        while h <= 8.0001:
            e = sse(s, h)
            if e < best[0]:
                best = (e, s, h)
            h += 0.25
        s += 0.25
    _, s0, h0 = best
    # refine pass
    sse_min, s_best, h_best = best[0], s0, h0
    s = s0 - 0.5
    while s <= s0 + 0.5001:
        h = h0 - 0.5
        while h <= h0 + 0.5001:
            e = sse(s, h)
            if e < sse_min:
                sse_min, s_best, h_best = e, s, h
            h += 0.01
        s += 0.01

    n = len(usable)
    rmse = math.sqrt(sse_min / n) if n else float("nan")
    baseline = sum((t.wins - t.games * 0.5) ** 2 for t in usable)
    rmse_base = math.sqrt(baseline / n) if n else float("nan")

    lg_avg = round(_mean([t.ppg for t in usable if t.ppg is not None]), 2)
    hw = sum(t.home_w for t in usable)
    hl = sum(t.home_l for t in usable)
    home_rate = hw / (hw + hl) if (hw + hl) else float("nan")

    # reliability machinery
    se = [max(t.games, 1) for t in usable]
    ses = [s_best / math.sqrt(g) for g in se]
    var_obs = _var([t.srs for t in usable])
    tau_sq = max(0.0, var_obs - _mean([e * e for e in ses]))

    grid = []
    for mult in (0.9, 0.95, 1.0, 1.05, 1.1):
        s_alt = round(s_best * mult, 2)
        grid.append({"margin_sd": s_alt, "sse_wins": round(sse(s_alt, h_best), 3),
                     "delta_vs_best_pct": round(100 * (sse(s_alt, h_best) / sse_min - 1), 2)})

    return Calibration(
        margin_sd=round(s_best, 3),
        hca_points=round(h_best, 3),
        rmse_wins=round(rmse, 4),
        rmse_baseline_wins=round(rmse_base, 4),
        league_avg_points=lg_avg,
        home_win_rate=round(home_rate, 4),
        tau_sq=round(tau_sq, 4),
        se_mean=round(_mean(ses), 4),
        n_teams=n,
        grid=grid,
    )


def apply_shrinkage(teams: list[Team], cal: Calibration) -> None:
    """lambda_i = tau^2 / (tau^2 + se_i^2), se_i = margin_sd / sqrt(games_i)."""
    tau_sq = cal.tau_sq
    for t in teams:
        se = cal.margin_sd / math.sqrt(max(t.games, 1))
        lam = (tau_sq / (tau_sq + se * se)) if tau_sq > 0 else 0.0
        t.reliability = round(lam, 4)
        if t.srs is not None:
            t.srs_shrunk = round(lam * t.srs, 4)
        if t.net_ppg is not None:
            t.net_shrunk = round(lam * t.net_ppg, 4)


def skill_and_luck(teams: list[Team], cal: Calibration) -> None:
    """Expected wins from rating; the residual is the luck/execution component.

    Under the fitted normal model, wins ~ Binomial(games, p_i) so the standard error of
    the win residual is sqrt(games * p * (1 - p)). A |z| beyond ~1.96 is a 5%-level
    departure that cannot be called skill on this sample alone — it is reported, not traded.
    """
    for t in teams:
        e = _expected_wins(t, cal.margin_sd, cal.hca_points)
        p = e / t.games if t.games else float("nan")
        t.expected_wins = round(e, 3)
        t.luck = round(t.wins - e, 3)
        var = t.games * p * (1 - p)
        t.luck_z = round(t.luck / math.sqrt(var), 3) if var > 0 else None


def build(root: Path | str = ".") -> RatingModel:
    root = Path(root)
    teams = load_teams(root / config.DATA_DIR / config.SNAPSHOT_RATINGS)
    cal = calibrate(teams)
    apply_shrinkage(teams, cal)
    skill_and_luck(teams, cal)
    return RatingModel(teams, cal)


if __name__ == "__main__":  # pragma: no cover
    m = build(Path(__file__).resolve().parents[2])
    print(json.dumps(m.cal.as_dict(), indent=2))
    for tc in m.order[:5]:
        print(tc, m.get(tc).as_dict())
