"""Walk-forward backtest of the published NBA2 line-origination model.

THE POINT OF THIS FILE
----------------------
Every prior session in this repository published model output but no graded outcome:
`0/90` validation gates passed and the reward pool was unallocated, for one stated reason —
"no game-level results history exists in this repo". This module supplies that history from
official NBA.com final scores and grades the model out-of-sample.

WHAT MAKES THE NUMBER HONEST
----------------------------
1. **Point-in-time.** For a game on date D, ratings are built only from games strictly
   before D. `assert_no_leakage` re-checks this on the emitted rows rather than trusting the
   loop, because a look-ahead bug is silent and flattering.
2. **Seeded.** Nothing starts from a prior belief: before a team has played, its rating is
   the league mean. The model must earn its information.
3. **No fitted constants chosen on the graded set.** sigma and the home-court advantage are
   re-estimated on the training prefix, never taken from the test games.
4. **Skill reference is explicit.** Every hit rate is compared with a defined naive
   baseline on the *same* games, and the difference is tested with a permutation test.
5. **No prices.** There is no odds feed, so nothing here is an ROI. What is measured is
   whether the model predicts better than chance and better than a naive rule. Stake
   sizing is impossible without a price and is therefore not reported.

Terminology
-----------
* cover  — did the team we leant to beat its own originated spread?
* The originated spread is our own number, so "covering" it means the model agreed with
  itself. Every spread row therefore also reports the **market-free** comparison that
  actually matters for a reader: the error of our number against the final margin.
"""

from __future__ import annotations

import json
import math
import pathlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from . import stats

HISTORY_DIR = pathlib.Path("data/raw/history")

# Pre-registered before any outcome was graded (see backtest/data/preregistration.json).
SHRINK_K = 12.0          # games of "prior weight"; a team's edge is shrunk toward 0 by n/(n+K)
RECENT_WINDOW = 8        # games used for the form component
TIER_EDGE = {"A": 3.0, "B": 1.5, "C": 0.0}   # model edge in points required per tier


def load_games(history_dir: pathlib.Path = HISTORY_DIR) -> list[dict]:
    games: list[dict] = []
    for path in sorted(history_dir.glob("games_*.json")):
        doc = json.loads(path.read_text())
        for g in doc["games"]:
            g = dict(g)
            g["_file"] = path.name
            games.append(g)
    games.sort(key=lambda g: (g["date"], g["game_id"]))
    ids = [g["game_id"] for g in games]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SystemExit(f"duplicate game ids in history: {sorted(dupes)}")
    return games


def completed_dates(games: Sequence[dict]) -> list[str]:
    return sorted({g["date"] for g in games})


# --------------------------------------------------------------------------- ratings


@dataclass
class TeamState:
    """Everything we are allowed to know about a team before a given date."""

    played: int = 0
    wins: int = 0
    losses: int = 0
    pts_for: int = 0
    pts_against: int = 0
    margins: list[float] = field(default_factory=list)

    def add(self, scored: int, allowed: int) -> None:
        self.played += 1
        self.pts_for += scored
        self.pts_against += allowed
        self.margins.append(scored - allowed)
        if scored > allowed:
            self.wins += 1
        else:
            self.losses += 1

    @property
    def net(self) -> float | None:
        return (self.pts_for - self.pts_against) / self.played if self.played else None

    @property
    def ppg(self) -> float | None:
        return self.pts_for / self.played if self.played else None

    @property
    def oppg(self) -> float | None:
        return self.pts_against / self.played if self.played else None

    def recent_net(self, window: int = RECENT_WINDOW) -> float | None:
        m = self.margins[-window:]
        return sum(m) / len(m) if m else None


def build_states(games: Iterable[dict]) -> dict[str, TeamState]:
    states: dict[str, TeamState] = defaultdict(TeamState)
    for g in games:
        states[g["away"]].add(g["away_pts"], g["home_pts"])
        states[g["home"]].add(g["home_pts"], g["away_pts"])
    return dict(states)


def league_averages(states: dict[str, TeamState]) -> tuple[float, float]:
    """(mean points, sd of per-game margin) from teams that have played."""
    pts = [s.ppg for s in states.values() if s.ppg is not None]
    margins = [m for s in states.values() for m in s.margins]
    mean_pts = sum(pts) / len(pts) if pts else 112.0
    sd_margin = stats.sd(margins) or 13.0
    return mean_pts, sd_margin


def shrink(edge: float, played: int, k: float = SHRINK_K) -> float:
    """Empirical-Bayes style shrinkage: no evidence => no opinion."""
    return edge * played / (played + k)


@dataclass
class Prediction:
    game_id: str
    date: str
    away: str
    home: str
    away_pts: int
    home_pts: int
    periods: int
    source_url: str
    # point-in-time inputs
    away_games_before: int
    home_games_before: int
    league_mean_pts: float
    sigma: float
    hca: float
    # model output
    pred_margin_home: float | None      # our line for (home - away)
    pred_margin_net_only: float | None  # baseline (b): raw point differential, no shrink, no HCA
    pred_total: float | None
    p_home: float | None
    tier: str
    # outcomes
    actual_margin_home: int = 0
    actual_total: int = 0
    margin_error: float | None = None   # pred - actual (signed)
    total_error: float | None = None

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def predict(models: dict, states: dict[str, TeamState], g: dict, mean_pts: float,
            sigma: float, hca: float) -> Prediction:
    """Originate a line for one game using only `states` (which hold pre-game info)."""
    away, home = g["away"], g["home"]
    a = states.get(away)
    h = states.get(home)

    pred_margin = None
    pred_margin_net_only = None
    pred_total = None
    if a and h and a.played and h.played:
        a_net = shrink(a.net or 0.0, a.played)
        h_net = shrink(h.net or 0.0, h.played)
        # margin for home minus away, plus home court
        pred_margin = (h_net - a_net) + hca
        pred_margin_net_only = (h.net or 0.0) - (a.net or 0.0)
        a_off = a.ppg or mean_pts
        h_off = h.ppg or mean_pts
        a_def = a.oppg or mean_pts
        h_def = h.oppg or mean_pts
        # each team's expected score = own offence average combined with opponent defence
        exp_home = (h_off + a_def) / 2.0
        exp_away = (a_off + h_def) / 2.0
        pred_total = exp_home + exp_away

    p_home = None
    if pred_margin is not None and sigma:
        p_home = 0.5 * (1.0 + math.erf((pred_margin / sigma) / math.sqrt(2.0)))

    # tier from the size of the modelled edge relative to the standard error of a margin
    edge = abs(pred_margin) if pred_margin is not None else 0.0
    if pred_margin is None:
        tier = "BLOCKED"
    elif edge >= TIER_EDGE["A"]:
        tier = "A"
    elif edge >= TIER_EDGE["B"]:
        tier = "B"
    else:
        tier = "C"

    actual_margin = g["home_pts"] - g["away_pts"]
    return Prediction(
        game_id=g["game_id"], date=g["date"], away=away, home=home,
        away_pts=g["away_pts"], home_pts=g["home_pts"],
        periods=g.get("periods", 4), source_url=g["source_url"],
        away_games_before=(a.played if a else 0), home_games_before=(h.played if h else 0),
        league_mean_pts=round(mean_pts, 2), sigma=round(sigma, 3), hca=round(hca, 3),
        pred_margin_home=(round(pred_margin, 2) if pred_margin is not None else None),
        pred_margin_net_only=(round(pred_margin_net_only, 2) if pred_margin_net_only is not None else None),
        pred_total=(round(pred_total, 2) if pred_total is not None else None),
        p_home=(round(p_home, 4) if p_home is not None else None),
        tier=tier,
        actual_margin_home=actual_margin,
        actual_total=g["away_pts"] + g["home_pts"],
        margin_error=(round(pred_margin - actual_margin, 2) if pred_margin is not None else None),
        total_error=(round(pred_total - (g["away_pts"] + g["home_pts"]), 2) if pred_total is not None else None),
    )


def walk_forward(games: Sequence[dict], hca_fixed: float | None = None) -> list[Prediction]:
    """Grade every game that has at least one prior game for both teams.

    Games are processed in date order; all games on date D are predicted from the state
    after date D-1, then applied. That is what prevents same-day leakage.
    """
    by_date: dict[str, list[dict]] = defaultdict(list)
    for g in games:
        by_date[g["date"]].append(g)

    states: dict[str, TeamState] = defaultdict(TeamState)
    home_margins: list[float] = []
    out: list[Prediction] = []
    for date in sorted(by_date):
        day = by_date[date]
        mean_pts, sigma = league_averages(states)
        hca = hca_fixed if hca_fixed is not None else estimate_hca(home_margins)
        for g in day:
            out.append(predict({}, states, g, mean_pts, sigma, hca))
        for g in day:  # apply only after the whole day is predicted
            states[g["away"]].add(g["away_pts"], g["home_pts"])
            states[g["home"]].add(g["home_pts"], g["away_pts"])
            home_margins.append(g["home_pts"] - g["away_pts"])
    return out


def estimate_hca(home_margins: Sequence[float], min_games: int = 40) -> float:
    """Home-court advantage in points, estimated only from games already completed.

    The mean home margin across all games is an unbiased estimate of HCA, because the
    league's mean net rating is zero by construction. It is shrunk toward 0 while the
    sample is small so that the first few games cannot swing every line.

    `home_margins` MUST contain only games strictly before the date being predicted;
    `walk_forward` guarantees that. `min_games` is a sample floor, not a tuning knob.
    """
    n = len(home_margins)
    if n == 0:
        return 0.0
    return sum(home_margins) / n * (n / (n + min_games))


def assert_no_leakage(rows: Sequence[Prediction], games: Sequence[dict]) -> None:
    """Recompute each team's pre-game game count from raw history and compare.

    A mismatch means a game was graded using information from that date or later.
    """
    seen: dict[str, int] = defaultdict(int)
    counters: dict[str, int] = defaultdict(int)
    by_date: dict[str, list[dict]] = defaultdict(list)
    for g in games:
        by_date[g["date"]].append(g)
    index = {r.game_id: r for r in rows}
    for date in sorted(by_date):
        for g in by_date[date]:
            if g["game_id"] in index:
                r = index[g["game_id"]]
                if r.away_games_before != counters[g["away"]]:
                    raise AssertionError(f"leakage: {g['game_id']} away games_before "
                                         f"{r.away_games_before} != {counters[g['away']]}")
                if r.home_games_before != counters[g["home"]]:
                    raise AssertionError(f"leakage: {g['game_id']} home games_before "
                                         f"{r.home_games_before} != {counters[g['home']]}")
        for g in by_date[date]:
            counters[g["away"]] += 1
            counters[g["home"]] += 1
