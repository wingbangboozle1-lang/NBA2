"""Global configuration for the NBA2 line-origination pipeline.

Every number that can be *derived* from the verified snapshots is derived at runtime and
is NOT stored here. Values that cannot be derived from available data are declared here
with `status="unratified"` and surface on the site's Parameters + Flagged pages.

Policy (enforced by nba2.pipeline.lint):
  * no model output may reference an input whose `verified` flag is False without a flag;
  * no table row may exist without a `source`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Parameter:
    """A model parameter with explicit provenance.

    `value=None` means "not yet known" — it is never guessed. `derived=True` means the
    value is overwritten at runtime from the snapshots and the literal here is only a
    search bound / placeholder.
    """

    key: str
    value: Any
    unit: str
    status: str  # "verified" | "derived-from-snapshot" | "unratified" | "unknown"
    rationale: str
    source: str
    derived: bool = False
    sensitivity: tuple[float, float] | None = None

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "rationale": self.rationale,
            "source": self.source,
            "derived": self.derived,
            "sensitivity": list(self.sensitivity) if self.sensitivity else None,
        }


# ----------------------------------------------------------------------------- markets
MARKETS = ("spread", "total", "moneyline")

# NBA spreads/totals are quoted in half-point increments for .5 lines; spreads in quarter-
# point increments exist off .5 numbers. We quote halves so that no leg of a parlay pushes.
SPREAD_INCREMENT = 0.5
TOTAL_INCREMENT = 0.5

# Reference price used ONLY to translate probabilities into a stake/ROI illustration.
# This is NOT a live quote: no odds feed is connected (see FLAG-SLATE-01). It is the
# standard -110 point-spread price, kept in one place so it cannot leak into a "market"
# comparison by accident.
REFERENCE_PRICE = 1.9091  # decimal odds equivalent of -110
REFERENCE_PRICE_STATUS = "unratified-placeholder"

# ----------------------------------------------------------------------------- staking
MAX_STAKE_FRACTION = 0.01  # 1% of bankroll hard cap
KELLY_MULTIPLIER = 0.25  # quarter-Kelly: model uncertainty is unquantified
MIN_EDGE_TO_BET = 0.0  # with no market price there is no edge; see gates G-02

# ----------------------------------------------------------------------------- model
PARAMS: dict[str, Parameter] = {
    # Per-game margin volatility. Derived, not assumed: solved together with HCA by
    # least-squares on the 30 verified team win totals (see nba2.models.ratings.calibrate).
    "margin_sd": Parameter(
        key="margin_sd",
        value=None,
        unit="points per game",
        status="derived-from-snapshot",
        rationale=(
            "SD of a team's per-game margin. Searched over [6, 25]; the value used is the "
            "least-squares optimum against observed wins, so it is a fitted quantity, not "
            "an assumption."
        ),
        source="derived: data/raw/team_ratings_2026-11-13.json",
        derived=True,
        sensitivity=(0.9, 1.1),
    ),
    # Home-court advantage in points. Same fit. Cross-checked against the league home win
    # rate computed from the verified home/road split columns.
    "hca_points": Parameter(
        key="hca_points",
        value=None,
        unit="points",
        status="derived-from-snapshot",
        rationale="Added to the home team's expected margin; fitted jointly with margin_sd.",
        source="derived: data/raw/team_ratings_2026-11-13.json",
        derived=True,
        sensitivity=(0.5, 2.0),
    ),
    # Reliability shrinkage on a ratings table that only has ~12 games behind it.
    "shrinkage": Parameter(
        key="shrinkage",
        value=None,
        unit="multiplier in [0,1]",
        status="derived-from-snapshot",
        rationale=(
            "Per-team James-Stein style reliability lambda = tau^2 / (tau^2 + se^2), where "
            "se = margin_sd / sqrt(games) and tau^2 = max(0, Var(rating) - mean(se^2))."
        ),
        source="derived: data/raw/team_ratings_2026-11-13.json",
        derived=True,
    ),
    # Total scoring line centre.
    "league_avg_points": Parameter(
        key="league_avg_points",
        value=None,
        unit="points per team per game",
        status="derived-from-snapshot",
        rationale="Unweighted mean of the 30 teams' points-per-game (schedule effects ignored).",
        source="derived: data/raw/team_ratings_2026-11-13.json",
        derived=True,
    ),
    # How far apart our two base ratings must be before we call the game ambiguous.
    "model_disagreement_tolerance": Parameter(
        key="model_disagreement_tolerance",
        value=2.0,
        unit="points",
        status="unratified",
        rationale=(
            "If |SRS line - raw-margin line| exceeds this, the game is marked DISAGREE and "
            "is excluded from Tier A. Chosen as ~1/6 of margin_sd; must be ratified by the "
            "owner and re-checked on the first 30 days of sealed predictions."
        ),
        source="proposed by nba2.models.ratings — no external source",
        sensitivity=(1.0, 3.0),
    ),
    # Margin-of-victory used for the "we only bet what we can explain" rule.
    "tier_a_min_conviction": Parameter(
        key="tier_a_min_conviction",
        value=0.20,
        unit="margin_sd units",
        status="unratified",
        rationale=(
            "Tier A requires |expected margin| >= 0.20 * margin_sd AND agreement between the "
            "two base models AND no material availability gap. Arbitrary until ratified."
        ),
        source="proposed by nba2.models.lines — no external source",
        sensitivity=(0.10, 0.35),
    ),
    # SD of the game total. No game-level totals exist in this repo, so this is NOT fitted;
    # it is used only inside the parlay sensitivity band and never quoted as a price.
    "total_sd": Parameter(
        key="total_sd",
        value=20.0,
        unit="points",
        status="unratified",
        rationale=(
            "Placeholder so bivariate parlay pricing can run at all. Levels derived with this "
            "number are not publishable; only the ratio between independent and correlated "
            "pricing is reported, because that ratio is nearly insensitive to it."
        ),
        source="BLOCKED: requires game-level totals (requirements R-103)",
        sensitivity=(17.0, 23.0),
    ),
    # Parlay correlation handling.
    "parlay_rho_spread_total": Parameter(
        key="parlay_rho_spread_total",
        value=None,
        unit="correlation",
        status="unknown",
        rationale=(
            "Correlation between game margin and game total. Must be estimated from "
            "game-level box scores (unavailable); instead we price a sensitivity band and "
            "only publish parlays whose edge survives the whole band."
        ),
        source="BLOCKED: requires game-level results feed (requirements R-101/R-103)",
        sensitivity=(-0.20, 0.40),
    ),
    "rho_band": Parameter(
        key="rho_band",
        value=(-0.20, 0.40),
        unit="correlation",
        status="unratified",
        rationale="Sensitivity band used for every correlation-adjusted joint price.",
        source="proposed by nba2.models.correlation — no external source",
    ),
}

# ----------------------------------------------------------------------------- validation gates
# Thresholds are PROPOSED. Each one carries the reason and the number of sealed
# observations needed before the gate can even be evaluated. No gate is ever marked
# "passed" without the measurement existing.
GATES: list[dict[str, Any]] = [
    {
        "id": "G-01",
        "name": "Sample size",
        "rule": ">= 300 settled bets for team markets; >= 500 for player props.",
        "threshold": 300,
        "unit": "settled bets",
        "why": (
            "At -110 a 55% bettor needs roughly 300 bets before the standard error "
            "(sqrt(p(1-p)/n) ~ 2.9%) stops swamping a 5-point edge. Below this the leaderboard "
            "is ranking noise."
        ),
        "source": "derived from the binomial standard error at p=0.55 — see research/05-skill-vs-luck.md",
        "status": "blocked",
        "blocking_reason": "No settled bets yet. Ledger opens with the 2026-11-13 slate.",
    },
    {
        "id": "G-02",
        "name": "Closing line value (CLV)",
        "rule": "Mean CLV vs. closing number > 0 with a bootstrap 95% CI excluding 0.",
        "threshold": None,
        "unit": "points",
        "why": "CLV is the single least-luck-dependent measure of whether a line beats the market.",
        "source": "BLOCKED: requires a licensed odds feed (requirements R-101)",
        "status": "blocked",
        "blocking_reason": "No market prices captured. Our lines are published, but nothing to beat them yet.",
    },
    {
        "id": "G-03",
        "name": "Probability calibration",
        "rule": "Brier score <= 0.245 on settled games AND calibration slope in [0.85, 1.15] AND intercept in [-0.10, 0.10].",
        "threshold": 0.245,
        "unit": "brier",
        "why": "0.25 is the Brier score of always forecasting 50%; a line-originator must beat that and be calibrated, otherwise the stake sizing is fiction.",
        "source": "derived: Brier (1950) definition; threshold is our own proposal (unratified)",
        "status": "blocked",
        "blocking_reason": "Needs >= 100 settled games.",
    },
    {
        "id": "G-04",
        "name": "Line accuracy vs. naive baselines",
        "rule": "Mean absolute error of our spread must beat BOTH baselines: (a) 0.0 spread, (b) raw point-differential-per-game, by >= 0.30 points.",
        "threshold": 0.30,
        "unit": "points MAE",
        "why": "A line that only reproduces the standings' scoring margin adds no work; if shrinkage and schedule adjustment do not reduce error, delete the model.",
        "source": "derived from the snapshot baselines in nba2.models.gates",
        "status": "blocked",
        "blocking_reason": "Needs settled games with official final scores.",
    },
    {
        "id": "G-05",
        "name": "Luck removal",
        "rule": "Bootstrap (10,000 resamples, fixed seed) 95% CI of ROI excludes 0; t-stat >= 2.0; and the luck-adjusted PnL (each bet replaced by its model-expected PnL, variance kept) must not reverse the sign.",
        "threshold": 2.0,
        "unit": "t-stat",
        "why": "Separates 'won' from 'right'. A strategy whose PnL is explained by a few lucky bad beats fails here even if the record is positive.",
        "source": "derived: standard bootstrap / t-test; see research/05-skill-vs-luck.md",
        "status": "blocked",
        "blocking_reason": "Needs settled bets.",
    },
    {
        "id": "G-06",
        "name": "Multiple-testing control",
        "rule": "Across every strategy ever evaluated in the same window, apply Holm-Bonferroni to the CLV t-tests and require the Deflated Sharpe Ratio > 0.",
        "threshold": 0.05,
        "unit": "family-wise alpha",
        "why": "A leaderboard with N trials will produce a 'best' strategy by pure search. Punishing the number of tries is the only defence.",
        "source": "derived: Holm (1979); Deflated Sharpe = Bailey & Lopez de Prado (2014) formulation",
        "status": "blocked",
        "blocking_reason": "Requires G-02 inputs and a complete trial ledger (see S-11).",
    },
    {
        "id": "G-07",
        "name": "Walk-forward, no lookahead",
        "rule": "Every feature timestamped at or before tip-off; train on the first 70% of the window, test on the final 30%; test MAE must not exceed full-window MAE by more than 25%.",
        "threshold": 0.25,
        "unit": "relative degradation",
        "why": "Ratings built from a standings snapshot include future games for the teams that played earlier; that leak is silent and fatal.",
        "source": "derived from our own ingest design (see research/01-line-origination.md 'point-in-time')",
        "status": "at risk",
        "blocking_reason": (
            "The current snapshot is a single as-of standings table, which is NOT point-in-time "
            "for games inside the week it covers. Backtests from this table would leak; only the "
            "forward ledger is clean."
        ),
    },
    {
        "id": "G-08",
        "name": "Parameter robustness",
        "rule": "Re-price the slate over the full sensitivity box of every unratified parameter; a pick is only published if its side is unchanged in >= 90% of the grid.",
        "threshold": 0.90,
        "unit": "fraction of grid",
        "why": "If a 10% change in sigma flips the pick, the pick is a parameter, not a signal.",
        "source": "derived: implemented in nba2.models.gates.sensitivity_stability",
        "status": "evaluated",
        "blocking_reason": None,
    },
    {
        "id": "G-09",
        "name": "Cost and capacity",
        "rule": "Survive -110 vig, 1% hard-cap stake, 25% Kelly, and a re-quote of the model at the reference price minus 0.25 points of expected slippage.",
        "threshold": 0.01,
        "unit": "fraction of bankroll",
        "why": "Lines that only win before the vig, or before you move size, are not tradeable.",
        "source": "derived: REFERENCE_PRICE + staking config",
        "status": "evaluated",
        "blocking_reason": None,
    },
    {
        "id": "G-10",
        "name": "Availability-adjustment guardrail",
        "rule": "If a player on the official report with an Out/Doubtful status cannot be mapped to a quantified minutes delta, the line is published availability-blind and the game is marked INJURY-BLIND. No bet may be Tier A on an injury-blind game after the 13:00 ET report on game day.",
        "threshold": None,
        "unit": "flag",
        "why": "Otherwise the model silently assumes injuries do not matter, which is exactly when a naive line is most wrong.",
        "source": "official report structure: https://ak-static.cms.nba.com/referee/injury/ (no minutes fields)",
        "status": "evaluated",
        "blocking_reason": None,
    },
]

# ----------------------------------------------------------------------------- strategy families
# Registered, scored strategies. `evaluations` are filled by the leaderboard module;
# `None` means "not measured", never "zero".
STRATEGIES: list[dict[str, Any]] = [
    {
        "id": "S-01",
        "name": "Reliability-Shrunk Spread (RSS)",
        "family": "single",
        "markets": ["spread"],
        "hypothesis": "Standings-based ratings after 12 games are mostly noise; shrinking them toward league average and re-pricing beats the same rating unshrunk.",
        "edge_origin": "over-reaction of naive models (and of the public) to early-season results",
        "inputs": ["team.srs", "team.games", "calibrated.margin_sd", "calibrated.hca"],
        "correlation_note": "Single bet: no leg correlation. Cross-game correlation only matters when several legs of a same-night parlay share a total.",
        "sources": [
            "https://www.basketball-reference.com/leagues/NBA_2027_standings.html",
            "https://www.nba.com/games",
        ],
    },
    {
        "id": "S-02",
        "name": "Two-Rating Agreement Filter (TRAF)",
        "family": "single",
        "markets": ["spread", "moneyline"],
        "hypothesis": "Only bet when the schedule-adjusted rating (SRS) and the raw scoring-margin rating agree within a tolerance; disagreement is where a 12-game sample says nothing.",
        "edge_origin": "selective abstention — trading fewer, better-informed games",
        "inputs": ["model.line_srs", "model.line_net", "param.model_disagreement_tolerance"],
        "correlation_note": "Same-game ML + spread legs are ~perfectly correlated; treated as one bet, not a parlay.",
        "sources": ["derived from S-01 inputs"],
    },
    {
        "id": "S-03",
        "name": "Pace-Neutral Total Anchor (PNTA)",
        "family": "single",
        "markets": ["total"],
        "hypothesis": "A four-rate average total (own+opponent, both sides) is unbiased on average but mispriced when one team's pace is extreme; anchoring to league pace removes part of that.",
        "edge_origin": "pace differences not fully reflected in per-game scoring",
        "inputs": ["team.psg", "team.pag", "league_avg_points"],
        "correlation_note": "Total legs correlate with same-game margin legs; see G-02 and correlation module.",
        "sources": ["https://www.basketball-reference.com/leagues/NBA_2027_standings.html"],
    },
    {
        "id": "S-04",
        "name": "Correlation-Hedged Two-Leg Parlay (CHP2)",
        "family": "parlay",
        "markets": ["spread", "total"],
        "hypothesis": "Same-game spread+total parlays are priced by books assuming independence; the true joint probability of (favourite covers AND over) is materially above the product of the singles.",
        "edge_origin": "mispriced dependence, not better single-game forecasting",
        "inputs": ["model.margin_dist", "model.total_dist", "corr.rho_band"],
        "correlation_note": "THE strategy for correlation; priced on a bivariate normal with rho swept over the ratified band [-0.20, +0.40]; publish only if sign of edge is stable across the band.",
        "sources": ["derived: nba2.models.correlation"],
    },
    {
        "id": "S-05",
        "name": "Cross-Slate Correlated Parlay (XSCP)",
        "family": "parlay",
        "markets": ["spread"],
        "hypothesis": "Legs from different games are near-independent; the parlay edge is therefore only the vig compounding, so a correlated pair (same game, or same-pace style) beats a random parlay on variance-adjusted value even at worse headline odds.",
        "edge_origin": "variance/reduction of vig drag, not win rate",
        "inputs": ["per-game lines", "corr.estimate_cross_game"],
        "correlation_note": "Cross-game correlation is estimated empirically once a bet ledger exists; published value stays blank until then.",
        "sources": ["derived: nba2.models.parlays"],
    },
    {
        "id": "S-06",
        "name": "Availability-Blind Guardrail Fade (ABGF)",
        "family": "single",
        "markets": ["spread"],
        "hypothesis": "Between the 16:15 ET report the previous day and the game-day 13:00 ET report, our line has no availability signal; markets that already moved on a star's status are the only place a blind model loses, so abstain or fade only our own conviction.",
        "edge_origin": "avoiding a known blind spot rather than predicting better",
        "inputs": ["injury rows by game", "report cadence"],
        "correlation_note": "n/a",
        "sources": ["https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf"],
    },
    {
        "id": "S-07",
        "name": "Schedule-Spot Fade (SSF)",
        "family": "single",
        "markets": ["spread", "total"],
        "hypothesis": "3-in-4 and 2-in-2 nights inside a known window depress home-team production; on a 12-game sample this is one of the few structural signals that is measurable without a full season.",
        "edge_origin": "fatigue/travel, a real effect with a low information share",
        "inputs": ["slate dates per team"],
        "correlation_note": "Same-team legs across consecutive games are dependent by construction — never parlay a team's two games.",
        "sources": ["https://www.nba.com/schedule"],
    },
    {
        "id": "S-08",
        "name": "Player-Prop Minutes Model (PPMM)",
        "family": "prop",
        "markets": ["player_points", "player_rebounds", "player_assists", "combos"],
        "hypothesis": "Prop lines are minutes-driven more than skill-driven; a minutes-floor projection plus a negative-binomial count model prices them, and combo legs inherit the minutes correlation.",
        "edge_origin": "bookmakers shade prop lines toward action, not toward projection",
        "inputs": ["BLOCKED: player box scores", "BLOCKED: official minutes", "BLOCKED: prop lines"],
        "correlation_note": "Points-rebounds for the same player are strongly positively correlated; naive product pricing overstates the parlay price by a large factor. Requires an empirical estimate we do not yet have.",
        "sources": ["BLOCKED — see pages/questions.html Q-05"],
    },
    {
        "id": "S-09",
        "name": "Ledger-Only Champion (LOC)",
        "family": "meta",
        "markets": ["all"],
        "hypothesis": "The leaderboard champion is the strategy with the best luck-adjusted line accuracy over sealed, pre-tip predictions — not the best recent record.",
        "edge_origin": "evaluation design",
        "inputs": ["sealed ledger", "official final scores"],
        "correlation_note": "Used to decorrelate leaderboard scores: strategies sharing >0.7 bet-level overlap are reported as one cluster.",
        "sources": ["derived: nba2.models.leaderboard"],
    },
]

# ----------------------------------------------------------------------------- rewards / tiers
TIERS = {
    "promoted": {
        "label": "Promoted",
        "criteria": "all of G-01..G-05 pass; G-06..G-09 pass; G-07 not 'at risk'.",
        "reward_share": 0.60,
        "stake_cap_fraction": 0.01,
    },
    "research": {
        "label": "Research",
        "criteria": "hypothesis implemented, one or more gates blocked only by sample size.",
        "reward_share": 0.25,
        "stake_cap_fraction": 0.005,
    },
    "blocked": {
        "label": "Blocked",
        "criteria": "a required input does not exist in the repository.",
        "reward_share": 0.0,
        "stake_cap_fraction": 0.0,
    },
    "rejected": {
        "label": "Rejected",
        "criteria": "a gate failed on measured data (not merely blocked).",
        "reward_share": 0.0,
        "stake_cap_fraction": 0.0,
    },
}

# Prize pool design: paid on accuracy/CLV rank, never on last-7-day PnL, so that a
# variance spike cannot buy a reward.
REWARD_WEIGHTS = {
    "clv": 0.40,
    "line_mae_improvement": 0.25,
    "brier_improvement": 0.20,
    "calibration_slope_proximity": 0.10,
    "robustness": 0.05,
}

DATA_DIR = "data/raw"
ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / DATA_DIR

SNAPSHOT_CONTEXT = "slate_context_2026-11-14.json"
SNAPSHOT_LEADERS = "team_leaders_2026-11-13.json"
SNAPSHOT_RATINGS = "team_ratings_2026-11-13.json"


_STAMP_RE = __import__("re").compile(r"(\d{4}-\d{2}-\d{2})[ T](\d{1,2}):(\d{2})")


def _stamp_key(stamp: str) -> tuple:
    """Sortable key for an official report stamp such as '2026-11-13 19:30 ET'.

    Two captures of the same release may write the stamp with or without the ' ET'
    suffix, so the stamp is parsed rather than compared as a string: string ordering
    would rank '2026-11-13 19:30' and '2026-11-13 19:30 ET' differently for no reason.
    """
    m = _STAMP_RE.search(stamp or "")
    if not m:
        return (0, 0, 0)
    return (int(m.group(1).replace("-", "")), int(m.group(2)), int(m.group(3)))


def _snapshot_ranking(kind: str) -> list[tuple[tuple, str]]:
    """Rank the committed snapshots of one kind, newest first.

    The window has to roll forward without anyone editing a constant, but the choice must
    still be *deterministic* - a build that silently picked a random file would not be
    reproducible. So the ranking key is read out of the snapshot itself:

      * slate  -> (window.first_game_date, retrieved_at_utc)
      * injury -> (report_stamp_et, number of game dates covered, retrieved_at_utc)

    The injury tiebreak matters: two captures can read the *same* official release, one
    of them transcribing every game date in it and one only the day-before rows. The
    fuller capture is the primary snapshot; the narrower one stays available as a
    dedicated view of the same release. Everything else is broken by file name, so the
    order never depends on directory order.
    """
    out: list[tuple[tuple, str]] = []
    pattern = "slate_*.json" if kind == "slate" else "injury_report_*.json"
    for p in sorted(RAW_DIR.glob(pattern)):
        if kind == "slate" and p.name.startswith("slate_context_"):
            continue
        try:
            doc = json.loads(p.read_text())
            if kind == "slate":
                key = (doc["window"]["first_game_date"], doc.get("retrieved_at_utc", ""), p.name)
            else:
                dates = {r[0] for r in doc.get("records", []) if r}
                key = (_stamp_key(doc.get("report_stamp_et", "")),
                       len(dates),
                       doc.get("retrieved_at_utc", ""), p.name)
        except Exception:
            continue
        out.append((key, p.name))
    out.sort(reverse=True)
    return out


_S = _snapshot_ranking("slate")
_I = _snapshot_ranking("injury")

# The live window. The previous revision is kept so the site can publish the difference
# between two official revisions instead of only the latest one.
SNAPSHOT_SLATE = _S[0][1] if _S else "slate_2026-11-13_to_11-16.json"
SNAPSHOT_PREVIOUS_SLATE = _S[1][1] if len(_S) > 1 else None


def _full_release_injury() -> tuple[str | None, str | None]:
    """The active injury snapshot, and the previous *full release* to diff it against.

    A snapshot qualifies as a full release when it covers more than one game date - that
    is, when it transcribed the whole official document rather than only one day's rows
    out of it. Two captures can read the same release (one transcribing every date, one
    only the day-before rows); the narrower one is a useful dedicated view of that
    release, but it is not a revision to diff against.

    The previous revision is therefore the newest full release with a *strictly earlier*
    stamp, so a diff always compares two different official releases rather than two
    transcriptions of the same one.
    """
    if not _I:
        return "injury_report_2026-11-13.json", None
    active_key, active_name = _I[0]
    active_stamp, active_dates = active_key[0], active_key[1]
    full = [(k, n) for k, n in _I if k[1] >= 2]
    if not full:
        return active_name, (_I[1][1] if len(_I) > 1 else None)
    previous = next((n for k, n in full if k[0] < active_stamp), None)
    return active_name, previous


SNAPSHOT_INJURY, SNAPSHOT_PREVIOUS_INJURY = _full_release_injury()

TEAM_NAMES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}

TEAM_ID = {  # official NBA team IDs, as printed in NBA.com /team/<id>/<slug> URLs
    "ATL": 1610612737, "BOS": 1610612738, "CLE": 1610612739, "NOP": 1610612740,
    "CHI": 1610612741, "DAL": 1610612742, "DEN": 1610612743, "GSW": 1610612744,
    "HOU": 1610612745, "LAC": 1610612746, "LAL": 1610612747, "MIA": 1610612748,
    "MIL": 1610612749, "MIN": 1610612750, "BKN": 1610612751, "NYK": 1610612752,
    "ORL": 1610612753, "IND": 1610612754, "PHI": 1610612755, "PHX": 1610612756,
    "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759, "OKC": 1610612760,
    "TOR": 1610612761, "UTA": 1610612762, "MEM": 1610612763, "WAS": 1610612764,
    "DET": 1610612765, "CHA": 1610612766,
}

TEAM_PROFILE_URL = "https://www.nba.com/team/{team_id}/{slug}"


def team_stats_url(tricode: str) -> str:
    """Official NBA.com team-stats URL. Slug taken from the pattern printed on
    https://www.nba.com/teams (verified 2026-11-13); unknown slugs are omitted."""
    slug = {
        "ATL": "hawks", "BOS": "celtics", "CLE": "cavaliers", "NOP": "pelicans",
        "CHI": "bulls", "DAL": "mavericks", "DEN": "nuggets", "GSW": "warriors",
        "HOU": "rockets", "LAC": "clippers", "LAL": "lakers", "MIA": "heat",
        "MIL": "bucks", "MIN": "timberwolves", "BKN": "nets", "NYK": "knicks",
        "ORL": "magic", "IND": "pacers", "PHI": "sixers", "PHX": "suns",
        "POR": "blazers", "SAC": "kings", "SAS": "spurs", "OKC": "thunder",
        "TOR": "raptors", "UTA": "jazz", "MEM": "grizzlies", "WAS": "wizards",
        "DET": "pistons", "CHA": "hornets",
    }.get(tricode)
    if slug is None or tricode not in TEAM_ID:
        return ""
    return TEAM_PROFILE_URL.format(team_id=TEAM_ID[tricode], slug=slug)
