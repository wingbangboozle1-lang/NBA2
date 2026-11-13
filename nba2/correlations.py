"""
correlations.py — correlation analysis + parlay correlation gate.

Goal: determine correlation values between factors so the system can (a) avoid
self-correlated parlay legs and (b) distinguish skill from luck.

Honesty note (no hallucinations):
  A robust correlation requires a historical dataset of observations. The current
  verified dataset is a single-slate snapshot: win% for all 30 teams, and PPG/OPPG
  for only 2 teams (TOR, WAS). With n=2, a pairwise correlation is statistically
  meaningless (it degenerates to +/-1). Therefore:
    * We implement the full correlation methodology (Pearson r) and the parlay
      correlation gate (documented assumption: legs from different games are
      near-zero correlated; same-game legs are high-correlation and excluded).
    * Concrete historical correlation VALUES are reported as "pending historical
      dataset" rather than invented. See the Suggestions page for how to acquire
      the data needed to compute them.
"""

import math


def pearson(xs, ys):
    """Pearson correlation coefficient. Returns None if n<2 or zero variance."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def safe_round(v, nd=3):
    return None if v is None else round(v, nd)


def analyze_team_factors(records):
    """
    Analyze correlations among verified team-level factors.

    records: list of {"team","wins","losses","ppg","oppg",...}
    Returns a list of correlation rows with values or 'pending' flags.
    """
    rows = []

    # win% is verified for all teams.
    win_pct = [(t["wins"] / (t["wins"] + t["losses"])) if (t["wins"] + t["losses"]) else 0.5
               for t in records]

    # PPG / OPPG only where verified (TOR, WAS).
    ppg = [t["ppg"] for t in records]
    oppg = [t["oppg"] for t in records]

    n_ppg = sum(1 for v in ppg if v is not None)
    n_oppg = sum(1 for v in oppg if v is not None)

    rows.append({
        "factor_a": "win%", "factor_b": "PPG",
        "value": "pending",
        "n": n_ppg,
        "note": f"PPG verified for only {n_ppg} team(s); n<2 is not statistically meaningful. Historical dataset required.",
    })
    rows.append({
        "factor_a": "win%", "factor_b": "OPPG",
        "value": "pending",
        "n": n_oppg,
        "note": f"OPPG verified for only {n_oppg} team(s); n<2 is not statistically meaningful. Historical dataset required.",
    })
    rows.append({
        "factor_a": "PPG", "factor_b": "OPPG",
        "value": "pending",
        "n": n_ppg,
        "note": "Requires verified PPG/OPPG for all teams + historical sample.",
    })

    # If, in the future, full PPG/OPPG exists, compute win% vs (PPG-OPPG).
    have = [(wp, p, o) for wp, p, o in zip(win_pct, ppg, oppg) if p is not None and o is not None]
    if len(have) >= 3:
        r = pearson([h[0] for h in have], [h[1] - h[2] for h in have])
        rows.append({
            "factor_a": "win%", "factor_b": "PPG-OPPG (point diff)",
            "value": safe_round(r),
            "n": len(have),
            "note": "Computed from verified team-level data.",
        })
    return rows


# --- Parlay correlation gate -------------------------------------------------
# Documented assumption: outcomes of different games are approximately independent
# (near-zero correlation). Legs from the same game share outcomes and are
# high-correlation, so the gate EXCLUDES same-game parlay legs.
PARLAY_CORR_ASSUMPTION = (
    "Different-game outcomes are treated as approximately independent (near-zero "
    "correlation). Same-game legs are high-correlation and are excluded from parlays."
)


def parlay_correlation_gate(legs):
    """G3: legs must come from distinct games. Returns (ok, note, assumed_corr)."""
    games = [leg.get("game_id") for leg in legs]
    distinct = len(set(games)) == len(games)
    # Assumed pairwise correlation among distinct-game legs: ~0.
    assumed_corr = 0.0 if distinct else None
    if distinct:
        note = "All legs from distinct games; assumed pairwise correlation ~0.0 (documented assumption)."
        return True, note, assumed_corr
    note = "Duplicate/same-game leg present -> high self-correlation; excluded."
    return False, note, assumed_corr


def luck_vs_skill_note():
    """
    Document how luck is removed: a strategy is only treated as skill when it has
    (a) a transparent skill basis, (b) enough observations (G4), and (c) realized
    results whose hit-rate/ROI is statistically distinguishable from chance
    (e.g., a binomial test vs .500 and a regression of ROI on sample size).
    Until tracked results exist, every strategy is 'provisional'.
    """
    return (
        "Luck is removed by requiring: a documented skill basis, a minimum sample "
        "size, and realized results statistically distinguishable from chance (binomial "
        "test vs .500, ROI convergence). New strategies are provisional until tracked."
    )
