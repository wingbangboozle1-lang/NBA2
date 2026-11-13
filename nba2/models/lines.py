"""Line origination: ratings -> expected margin/total -> priced markets + triggers.

Design notes
------------
* We originate a *line*, not a bet. A bet needs a price to beat. With no odds feed the only
  honest actionable output is a **trigger**: the number at which the market would have to
  cross our line for us to act. `trigger_*` fields encode that.
* Two independent base ratings are used (schedule-adjusted SRS, and raw scoring margin).
  Their disagreement is a first-class output: where they disagree beyond the tolerance the
  game is excluded from the top tier rather than averaged into a false consensus.
* Every line is re-priced across the full sensitivity box of the unratified parameters; the
  fraction of the grid that keeps the same side is `stability`. A line at 62% stability is a
  parameterisation, not an opinion.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .. import config
from .ratings import RatingModel, norm_cdf


@dataclass
class GameLine:
    game_id: str
    date: str
    time_et: str
    away: str
    home: str
    arena: str
    city: str
    state: str
    broadcast: str
    cup_group: str | None
    margin_srs: float | None
    margin_net: float | None
    margin: float | None
    total: float | None
    exp_home_pts: float | None
    exp_away_pts: float | None
    home_win_prob: float | None
    spread_home: float | None          # our line for the home team (negative = home fav)
    total_line: float | None
    fair_home_decimal: float | None
    fair_away_decimal: float | None
    lean: str                          # "home" | "away" | "no-lean"
    conviction: float | None           # |margin| / margin_sd
    agreement: float | None            # |margin_srs - margin_net|
    stability: float | None            # 0..1 fraction of sensitivity grid holding the side
    tier: str                          # A | B | C | BLOCKED
    injury_blind: bool = True
    triggers: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def _r(x: float | None, nd: int = 1) -> float | None:
    if x is None:
        return None
    return round(x, nd)


def _round_increment(x: float, inc: float) -> float:
    return math.floor(x / inc + 0.5) * inc


def _win_prob(margin: float, home_points: float, total_points: float, sigma: float) -> float:
    """Home win probability.

    Margin drives the spread market directly; the same normal is used for the moneyline so
    the two markets are internally consistent (a book that prices ML off a different
    distribution than the spread is inconsistent, and we refuse to be).
    """
    return norm_cdf(margin / sigma)


def price_game(model: RatingModel, game: dict, injury_by_team: dict[str, list[dict]]) -> GameLine:
    away, home = game["away"], game["home"]
    cal = model.cal
    sigma = cal.margin_sd
    hca = cal.hca_points

    m_srs = model.expected_margin(away, home, "srs")
    m_net = model.expected_margin(away, home, "net")
    margin = model.expected_margin(away, home, "consensus")
    total = model.expected_total(away, home)
    agree = model.disagreement(away, home)

    # expected team scores: centre the total, push the margin into it
    exp_home = exp_away = None
    if margin is not None and total is not None:
        exp_home = (total + margin) / 2.0
        exp_away = (total - margin) / 2.0

    spread_home = total_line = None
    if margin is not None:
        # our line, expressed as the home team's spread. Favourable home margin -> minus.
        spread_home = _round_increment(-margin, config.SPREAD_INCREMENT)
    if total is not None:
        total_line = _round_increment(total, config.TOTAL_INCREMENT)

    p_home = _win_prob(margin, exp_home or 0.0, total or 0.0, sigma) if margin is not None else None
    fair_home = round(1.0 / p_home, 4) if p_home not in (None, 0.0) else None
    fair_away = round(1.0 / (1.0 - p_home), 4) if p_home not in (None, 1.0) else None

    lean = "no-lean"
    if margin is not None:
        lean = "home" if margin > 0 else "away" if margin < 0 else "no-lean"

    conviction = abs(margin) / sigma if margin is not None else None

    # triggers: the market number at which we would act, i.e. our line plus a hurdle
    hurdle = 1.5
    triggers: dict[str, float] = {}
    if spread_home is not None:
        # we take home if the market gives us >= hurdle points more than our own line
        triggers["take_home_if_market_at_least"] = _r(spread_home + hurdle)
        triggers["take_away_if_market_at_most"] = _r(spread_home - hurdle)
    if total_line is not None:
        triggers["take_over_if_market_at_most"] = _r(total_line - hurdle)
        triggers["take_under_if_market_at_least"] = _r(total_line + hurdle)

    stability = _stability(model, away, home, lean)

    inj_home = [r for r in injury_by_team.get(home, []) if r.get("status") in ("Out", "Doubtful")]
    inj_away = [r for r in injury_by_team.get(away, []) if r.get("status") in ("Out", "Doubtful")]
    injury_blind = True  # numeric impact is unavailable, so *every* game is availability-blind
    notes: list[str] = []
    if inj_home or inj_away:
        notes.append(
            f"Official report lists {len(inj_home)} Out/Doubtful for {home}, "
            f"{len(inj_away)} for {away}. No numeric minutes impact is applied (see FLAG-INJ-02)."
        )
    else:
        notes.append("No Out/Doubtful rows retrieved for either team in the snapshot on hand.")

    tol = config.PARAMS["model_disagreement_tolerance"].value
    min_conv = config.PARAMS["tier_a_min_conviction"].value
    if margin is None or total is None:
        tier = "BLOCKED"
    elif conviction is not None and conviction >= min_conv and agree is not None and agree <= tol and stability >= 0.9:
        tier = "A"
    elif agree is not None and agree <= tol:
        tier = "B"
    else:
        tier = "C"
    if tier in ("A", "B") and injury_blind:
        tier = "B" if tier == "A" else tier  # G-10: no Tier A while availability-blind

    return GameLine(
        game_id=game["game_id"], date=game["date"], time_et=game["time_et"],
        away=away, home=home, arena=game["arena"], city=game["city"], state=game["state"],
        broadcast=game["broadcast"], cup_group=game.get("cup_group"),
        margin_srs=_r(m_srs, 2), margin_net=_r(m_net, 2), margin=_r(margin, 2),
        total=_r(total, 2), exp_home_pts=_r(exp_home, 1), exp_away_pts=_r(exp_away, 1),
        home_win_prob=_r(p_home, 4), spread_home=_r(spread_home), total_line=_r(total_line),
        fair_home_decimal=_r(fair_home, 3), fair_away_decimal=_r(fair_away, 3),
        lean=lean, conviction=_r(conviction, 3), agreement=_r(agree, 2),
        stability=_r(stability, 3) if stability is not None else None,
        tier=tier, injury_blind=injury_blind, triggers=triggers, notes=notes,
    )


def _stability(model: RatingModel, away: str, home: str, base_lean: str) -> float | None:
    """Fraction of the parameter box where the favoured side does not change."""
    if base_lean == "no-lean":
        return None
    cal = model.cal
    ta, th = model.get(away), model.get(home)
    if None in (ta.srs_shrunk, th.srs_shrunk, ta.net_shrunk, th.net_shrunk):
        return None
    tol_par = config.PARAMS["margin_sd"].sensitivity or (0.9, 1.1)
    hca_box = config.PARAMS["hca_points"].sensitivity or (0.5, 2.0)
    hits = total = 0
    for sm in (tol_par[0], 1.0, tol_par[1]):
        for dh in (-hca_box[0], 0.0, hca_box[1]):
            sigma = cal.margin_sd * sm
            hca = cal.hca_points + dh
            for rating in ("srs", "net"):
                a = ta.srs_shrunk if rating == "srs" else ta.net_shrunk
                h = th.srs_shrunk if rating == "srs" else th.net_shrunk
                m = (h - a) + hca
                side = "home" if m > 0 else "away" if m < 0 else "no-lean"
                total += 1
                hits += 1 if side == base_lean else 0
    return hits / total if total else None


# --------------------------------------------------------------------------- slate io
def load_slate(path: Path) -> tuple[list[dict], dict]:
    raw = json_load(path)
    cols = raw["columns"]
    games = [dict(zip(cols, rec)) for rec in raw["records"]]
    for g in games:
        g["preview_url"] = f"https://www.nba.com/game/{g['away'].lower()}-vs-{g['home'].lower()}-{g['game_id']}"
    return games, raw


def json_load(path: Path) -> dict:
    import json
    return json.loads(Path(path).read_text())


def price_slate(model: RatingModel, games: list[dict], injury_by_team: dict[str, list[dict]]) -> list[GameLine]:
    return [price_game(model, g, injury_by_team) for g in games]


def market_summary(lines: list[GameLine]) -> dict[str, Any]:
    n = len(lines)
    tiers = {t: sum(1 for l in lines if l.tier == t) for t in ("A", "B", "C", "BLOCKED")}
    favs = sum(1 for l in lines if l.margin is not None and abs(l.margin) >= 5.0)
    return {
        "games": n,
        "tiers": tiers,
        "games_favoured_by_5plus": favs,
        "mean_abs_margin": _r(sum(abs(l.margin or 0) for l in lines) / n, 2) if n else None,
        "mean_stability": _r(sum(l.stability or 0 for l in lines) / n, 3) if n else None,
        "max_total": max((l.total_line or 0) for l in lines) if n else None,
        "min_total": min((l.total_line for l in lines if l.total_line is not None), default=None),
    }


if __name__ == "__main__":  # pragma: no cover
    root = Path(__file__).resolve().parents[2]
    from .ratings import build
    m = build(root)
    games, _ = load_slate(root / config.DATA_DIR / config.SNAPSHOT_SLATE)
    out = price_slate(m, games, {})
    print(json.dumps({"calibration": m.cal.as_dict(),
                      "games": [g.as_dict() for g in out[:3]]}, indent=2, default=str))
