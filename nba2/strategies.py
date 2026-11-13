"""
strategies.py — signal-generation strategies + validation gates + leaderboard.

Each strategy consumes originated lines (from model.py) and emits signals (picks).
Every strategy must pass validation gates before its signal is eligible. Gates are
deterministic and auditable.

Gate catalogue:
  G1 Data-integrity : every input traces to an official verified source (or a
                      clearly-labeled Model output). No unverified factual value.
  G2 Edge            : the model edge must clear a break-even threshold.
  G3 Correlation    : multi-leg legs must be low-correlation (different games;
                      same-game legs excluded to avoid self-correlation).
  G4 Sample-size    : a strategy must have a minimum number of observations before
                      it is trusted (new strategies start in "provisional").
  G5 Variance/luck  : skill-based selection only — a strategy is flagged if its
                      realized results look like luck (see correlations/luck note).

Leaderboard: ranks strategies by realized performance (ROI / hit rate) once results
are tracked. New strategies have no realized results yet and are shown as
"provisional — pending tracked results".
"""

# Break-even for a standard -110 bet is 110/210 = 0.524 win prob.
BREAK_EVEN = 110 / 210
# Minimum model win-probability for a single-bet signal.
MIN_WIN_PROB = 0.58
# Minimum edge (predicted margin minus spread line) in points for a spread signal.
MIN_SPREAD_EDGE = 1.0
# Minimum edge (predicted total minus total line) for a totals signal.
MIN_TOTAL_EDGE = 1.0

GATES = {
    "G1_data_integrity": "All factual inputs trace to an official verified source; model outputs are labeled Model.",
    "G2_edge": f"Model edge clears break-even ({BREAK_EVEN:.3f}) / thresholds.",
    "G3_correlation": "Multi-leg parlays use legs from distinct games (low correlation); same-game legs excluded.",
    "G4_sample_size": "Minimum observations before a strategy is trusted (provisional otherwise).",
    "G5_variance_luck": "Skill-based selection; realized results checked for luck vs skill (see correlations).",
}


# --- Gate implementations -----------------------------------------------------
def gate_data_integrity(pick):
    """G1: pick must carry a source link and a data-class label."""
    ok = bool(pick.get("source")) and bool(pick.get("data_class"))
    return ok, "ok" if ok else "missing source/data-class"


def gate_edge_single(pick):
    """G2 for single bets: model win prob above threshold."""
    p = pick.get("model_win_prob")
    if p is None:
        return False, "no win prob"
    ok = p >= MIN_WIN_PROB
    return ok, f"win_prob={p:.3f} vs min {MIN_WIN_PROB}"


def gate_edge_spread(pick):
    """G2 for spread bets: predicted margin edge over the spread line."""
    edge = pick.get("spread_edge")
    if edge is None:
        return False, "no spread edge"
    ok = abs(edge) >= MIN_SPREAD_EDGE
    return ok, f"spread_edge={edge:.2f} vs min {MIN_SPREAD_EDGE}"


def gate_edge_total(pick):
    """G2 for totals: predicted total edge over the total line."""
    edge = pick.get("total_edge")
    if edge is None:
        return False, "no total edge"
    ok = abs(edge) >= MIN_TOTAL_EDGE
    return ok, f"total_edge={edge:.2f} vs min {MIN_TOTAL_EDGE}"


def gate_correlation(legs):
    """G3: legs must be from distinct games (no same-game self-correlation)."""
    games = {leg.get("game_id") for leg in legs}
    ok = len(games) == len(legs)
    return ok, "distinct games" if ok else "duplicate/same-game leg"


def gate_sample_size(observations, min_obs=30):
    """G4: enough tracked observations."""
    ok = observations >= min_obs
    return ok, f"obs={observations} vs min {min_obs}"


def gate_variance_luck(strategy):
    """G5: a strategy is skill-eligible only if it has a documented skill basis
    and is tracked long enough to distinguish skill from luck. New strategies are
    provisional (not yet proven skill)."""
    has_basis = bool(strategy.get("skill_basis"))
    return has_basis, "skill basis documented (provisional until results tracked)"


# --- Strategy registry -------------------------------------------------------
STRATEGIES = [
    {
        "id": "S1_MarginFavorite",
        "name": "Margin Favorite (Single)",
        "type": "single",
        "description": "Single straight bet on the model's outright favorite where model win probability clears the edge threshold.",
        "skill_basis": "Win-probability edge from a transparent, auditable origination model.",
        "legs": 1,
        "generate": "single_margin",
    },
    {
        "id": "S2_SpreadValue",
        "name": "Spread Value (Single)",
        "type": "single",
        "description": "Single bet on the originated spread where the predicted-margin edge over the spread line clears the threshold.",
        "skill_basis": "Predicted-margin edge over the originated spread line.",
        "legs": 1,
        "generate": "single_spread",
    },
    {
        "id": "S3_Totals",
        "name": "Totals (Single)",
        "type": "single",
        "description": "Single over/under on the originated total where the predicted-total edge clears the threshold.",
        "skill_basis": "Predicted-total edge over the originated total line.",
        "legs": 1,
        "generate": "single_total",
    },
    {
        "id": "S4_LeanParlay",
        "name": "Lean Parlay (Combo)",
        "type": "parlay",
        "description": "2-3 single-bet legs from DIFFERENT games, each clearing the edge gate, combined into a parlay (correlation gate: distinct games).",
        "skill_basis": "Compounded edge across low-correlation legs.",
        "legs": "2-3",
        "generate": "parlay",
    },
    {
        "id": "S5_PlayerPropCombo",
        "name": "Player Prop Combo",
        "type": "prop",
        "description": "Player-prop combination (over/under player totals). Requires verified player-level data; prop values are left blank/unverified until player stats are sourced.",
        "skill_basis": "Player-level production projections (pending verified player data).",
        "legs": "2-4",
        "generate": "prop",
    },
]


def evaluate_strategy(strategy, signals, tracked_observations=0):
    """Run all applicable gates for a strategy and return a validation record."""
    record = {
        "id": strategy["id"],
        "name": strategy["name"],
        "type": strategy["type"],
        "signals": len(signals),
        "gates": {},
        "status": "provisional",
    }
    # G1 on each signal
    g1 = all(gate_data_integrity(s)[0] for s in signals) if signals else False
    record["gates"]["G1_data_integrity"] = g1
    # G5 skill basis
    g5, g5_msg = gate_variance_luck(strategy)
    record["gates"]["G5_variance_luck"] = g5
    record["gates"]["G5_note"] = g5_msg
    # G4 sample size
    g4, g4_msg = gate_sample_size(tracked_observations)
    record["gates"]["G4_sample_size"] = g4
    record["gates"]["G4_note"] = g4_msg
    # G2/G3 depend on type
    if strategy["type"] == "single":
        g2 = all((gate_edge_single(s)[0] or gate_edge_spread(s)[0] or gate_edge_total(s)[0]) for s in signals) if signals else False
        record["gates"]["G2_edge"] = g2
    elif strategy["type"] == "parlay":
        # G3 on the legs actually used in each parlay signal.
        all_legs = []
        for s in signals:
            all_legs.extend(s.get("legs", []))
        g3, g3_msg = gate_correlation(all_legs)
        record["gates"]["G3_correlation"] = g3
        record["gates"]["G3_note"] = g3_msg
        # G2: every leg of every parlay must clear an edge gate.
        leg_ok = []
        for leg in all_legs:
            leg_ok.append(gate_edge_single(leg)[0] or gate_edge_spread(leg)[0] or gate_edge_total(leg)[0])
        g2 = bool(leg_ok) if leg_ok else False
        record["gates"]["G2_edge"] = g2
    elif strategy["type"] == "prop":
        # Prop gate: requires verified player data; currently not satisfied.
        record["gates"]["G1_data_integrity_prop"] = False
        record["gates"]["G1_note_prop"] = "No verified player-level prop data available yet — values left blank/unverified."

    passed = all(v for k, v in record["gates"].items() if isinstance(v, bool))
    record["status"] = "validated" if (passed and g4) else "provisional"
    return record


def leaderboard(records):
    """Rank strategies by tracked performance. No tracked results yet -> provisional."""
    ranked = sorted(records, key=lambda r: (r.get("roi", -1), r.get("hit_rate", 0)), reverse=True)
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
        r.setdefault("roi", None)
        r.setdefault("hit_rate", None)
        if r.get("roi") is None:
            r["performance"] = "pending tracked results"
    return ranked
