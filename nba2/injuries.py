"""
injuries.py — injury impact + game-flow analysis.

Reads the verified official injury report and produces:
  * Per-team injury counts by status (verified statuses).
  * Rotation-minute / production impact ESTIMATES (model; clearly flagged — these
    are transparent heuristics, NOT verified importance values, which require
    player-level usage/box-score data).
  * Game-flow analysis: balance, tempo proxy, and how injuries shift the projected
    game flow. Tempo proxy is flagged because verified pace data is not yet in hand.

No hallucinations: only verified statuses/reasons are stated as fact. Impact
numbers are labeled as model estimates.
"""

from model import STATUS_WEIGHTS, win_pct  # reuse weights from model


def summarize_team(injuries):
    """Count injuries by status for a team's list."""
    counts = {"Out": 0, "Doubtful": 0, "Questionable": 0, "Probable": 0, "Available": 0}
    for inj in injuries:
        st = inj.get("status")
        if st in counts:
            counts[st] += 1
    return counts


def impact_points(injuries):
    """Model estimate of points-of-strength impact (negative = weakens team)."""
    return -sum(STATUS_WEIGHTS.get(inj.get("status"), 0.0) for inj in injuries)


def rotation_minute_note(injuries):
    """
    Rotation-minute impact note. Out/Doubtful players are modeled as unavailable
    (minutes redistributed to bench); Questionable as reduced/limited; Probable as
    full availability. This is an estimate pending verified usage data.
    """
    out = sum(1 for i in injuries if i.get("status") == "Out")
    doubt = sum(1 for i in injuries if i.get("status") == "Doubtful")
    q = sum(1 for i in injuries if i.get("status") == "Questionable")
    parts = []
    if out:
        parts.append(f"{out} Out (modeled as unavailable; minutes redistributed)")
    if doubt:
        parts.append(f"{doubt} Doubtful (modeled as likely unavailable)")
    if q:
        parts.append(f"{q} Questionable (modeled as reduced/limited minutes)")
    if not parts:
        parts.append("No listed injuries")
    return "; ".join(parts) + ". (model estimate — pending verified usage data)"


def game_flow(away_team, home_team, away_record, home_record, away_inj, home_inj):
    """
    Produce a game-flow analysis for one game.

    Balance: compare win% and estimated strength impact.
    Tempo proxy: flagged as unverified (no verified pace data in hand).
    Injury shift: how the estimated impacts move the balance.
    """
    a_wp = win_pct(away_record["wins"], away_record["losses"])
    h_wp = win_pct(home_record["wins"], home_record["losses"])
    a_imp = impact_points(away_inj)
    h_imp = impact_points(home_inj)

    # Estimated balance after injury (strength proxy).
    a_adj = a_wp + a_imp / 30.0   # fold impact into a comparable scale
    h_adj = h_wp + h_imp / 30.0
    balance = h_adj - a_adj

    if balance > 0.05:
        lean = f"Home ({home_team}) lean"
    elif balance < -0.05:
        lean = f"Away ({away_team}) lean"
    else:
        lean = "Even / pick"

    flow = {
        "away": away_team,
        "home": home_team,
        "away_win_pct": round(a_wp, 3),
        "home_win_pct": round(h_wp, 3),
        "away_injury_impact": round(a_imp, 2),
        "home_injury_impact": round(h_imp, 2),
        "injury_shifted_lean": lean,
        "balance": round(balance, 3),
        "away_rotation": rotation_minute_note(away_inj),
        "home_rotation": rotation_minute_note(home_inj),
        "tempo_proxy": "unverified (requires verified team pace data)",
        "data_class": "Model (impact/flow estimates; statuses verified to NBA.com)",
    }
    return flow
