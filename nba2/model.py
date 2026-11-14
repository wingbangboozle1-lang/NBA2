"""
model.py — NBA2 lines-origination model.

This module ORIGINATES the project's own NBA lines. The lines produced here are
**model output**, not official sportsbook lines. They are generated from verified
factual inputs (team win-loss records, home/away, official injury statuses) using a
transparent, documented methodology. Every model output is labeled as "Model".

Methodology (deliberately simple and auditable — no hidden data):
  * Team strength is derived from win percentage:  strength = (win_pct - 0.5) * SPREAD_SCALE
  * Home-court advantage is a documented constant HOME_ADV.
  * Injury impact is a transparent per-status adjustment applied to each team's
    strength, computed from the official injury report. Statuses -> adjustment:
        Out     : INJURY_OUT
        Doubtful: INJURY_DOUBTFUL
        Questionable: INJURY_QUESTIONABLE
        Probable/Available: 0
    NOTE: these per-player weights are a documented model estimate of rotation/
    production impact. They are NOT verified importance values (which would require
    player-level usage/box-score data). They are flagged as model estimates.
  * Predicted margin = home_strength - away_strength + HOME_ADV + injury_adj
  * Predicted total = TOTAL_BASELINE + pace/efficiency adjustment (only where
    verified PPG/OPPG exist; otherwise TOTAL_BASELINE, flagged as model baseline).
  * Win probability = sigmoid(margin / PROB_SCALE).

All parameters are module-level constants so the model is fully auditable and tunable.
"""

import math

# --- Documented, tunable model parameters ------------------------------------
SPREAD_SCALE = 13.0      # maps win% deviation from .500 to points of margin
HOME_ADV = 3.5           # average NBA home-court advantage in points
PROB_SCALE = 8.5         # margin -> win probability scale (sigmoid)
TOTAL_BASELINE = 224.0   # model baseline total; FLAGGED as unverified league avg

# Injury impact weights (points of strength subtracted per listed player).
# Model estimates of rotation-minute / production impact. NOT verified importance.
INJURY_OUT = 1.0
INJURY_DOUBTFUL = 0.6
INJURY_QUESTIONABLE = 0.3
INJURY_PROBABLE = 0.0
INJURY_AVAILABLE = 0.0

# Strong-margin threshold (points) for the spread-value strategy: a favorite is
# bet to cover only when the model's predicted margin clears this cushion.
STRONG_MARGIN = 4.0

STATUS_WEIGHTS = {
    "Out": INJURY_OUT,
    "Doubtful": INJURY_DOUBTFUL,
    "Questionable": INJURY_QUESTIONABLE,
    "Probable": INJURY_PROBABLE,
    "Available": INJURY_AVAILABLE,
}


def win_pct(wins, losses):
    games = wins + losses
    return (wins / games) if games else 0.5


def team_strength(wins, losses):
    return (win_pct(wins, losses) - 0.5) * SPREAD_SCALE


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def injury_adjustment(injuries_for_team):
    """Sum per-player weight for a team's listed injuries (model estimate)."""
    total = 0.0
    for inj in injuries_for_team:
        total += STATUS_WEIGHTS.get(inj.get("status"), 0.0)
    return -total  # negative = weakens the team


def pace_adjustment(away_ppg, home_ppg, away_oppg, home_oppg):
    """
    Adjust the total for verified scoring pace/efficiency.
    Only applied when verified PPG/OPPG exist for BOTH teams; otherwise 0
    (total stays at the flagged baseline). Never infers missing values.
    """
    if None in (away_ppg, home_ppg, away_oppg, home_oppg):
        return 0.0
    # Estimate combined scoring pace relative to baseline.
    combined = (away_ppg + home_oppg + home_ppg + away_oppg) / 4.0
    return combined - TOTAL_BASELINE


def originate_line(away_team, home_team, away_injuries, home_injuries, records):
    """
    Produce an originated line for one game.

    Injuries are GAME-SPECIFIC (the official report lists each player's status for
    a particular game), so we pass the per-team injury lists for THIS game only.

    Args:
      away_team, home_team: team abbreviations.
      away_injuries, home_injuries: lists of {player,status,reason} for THIS game.
      records: dict {team_abbr: {"wins":int,"losses":int,"ppg":float|None,"oppg":float|None}}

    Returns a dict with the originated line (all values labeled Model).
    """
    a = records[away_team]
    h = records[home_team]

    away_str = team_strength(a["wins"], a["losses"])
    home_str = team_strength(h["wins"], h["losses"])

    adj_away = injury_adjustment(away_injuries)
    adj_home = injury_adjustment(home_injuries)

    margin = (home_str + adj_home) - (away_str + adj_away) + HOME_ADV

    # Total: baseline + verified pace adjustment (0 if not fully verified).
    pace = pace_adjustment(a["ppg"], h["ppg"], a["oppg"], h["oppg"])
    total = TOTAL_BASELINE + pace

    prob_home = sigmoid(margin / PROB_SCALE)

    # Originated spread line (negative = favors the team it belongs to).
    # Round to half-points for a clean originated line.
    spread = round(margin * 2) / 2.0
    total_line = round(total * 2) / 2.0

    return {
        "away": away_team,
        "home": home_team,
        "model": "NBA2 originator",
        "predicted_margin": round(margin, 2),
        "originated_spread": spread,          # AWAY team's spread: - = away favored
        # The label is built from the AWAY abbreviation, so it reads as the away
        # line ("NYK -2.5" = NYK, the away team, favored by 2.5).  The away spread
        # equals the home margin, so a positive value means the HOME team is favored
        # (MIL @ ORL: margin +2.24, spread +2.0, label "MIL +2.0", favorite = home).
        # NOTE: this comment previously said "home team perspective", which was
        # false and is what let strategy S2 emit the wrong side of the line (S-26).
        "originated_spread_label": f"{away_team} {spread:+.1f}",  # e.g. "NYK -2.5" if away favored
        "predicted_total": round(total, 2),
        "originated_total_line": total_line,
        "home_win_prob": round(prob_home, 3),
        "away_win_prob": round(1 - prob_home, 3),
        "injury_adj_away": round(adj_away, 2),
        "injury_adj_home": round(adj_home, 2),
        "total_is_baseline_only": pace == 0.0,
        "data_class": "Model (originated; inputs verified to NBA.com)",
    }


def favorite_label(line):
    """Return 'home'/'away'/'pick' for who the model favors."""
    if line["predicted_margin"] > 0.15:
        return "home"
    if line["predicted_margin"] < -0.15:
        return "away"
    return "pick"
