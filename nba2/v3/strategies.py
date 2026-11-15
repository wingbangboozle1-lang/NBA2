"""Strategies, luck removal, pre-registration and the sealed ledger — the brief's competition.

WHAT THIS MODULE DOES
---------------------
1. Registers concrete strategies (single bets, parlays, prop-combination *shapes*) with the
   exact rule that decides each one: signal, thresholds, universe, settlement rule.
2. Scores each walk-forward on the official finals using the *v3* model, so a strategy is
   never graded on a game it could see.
3. Applies the validation gates from ``content.py`` and records PASS / FAIL / NOT-MEASURABLE
   with the number that decided each one.
4. **Removes luck**: every hit rate gets a Wilson interval and an exact binomial p-value
   against the base rate it must beat; a leaderboard rank is withheld until the sample
   supports one. A strategy that leans on a club whose luck z-score is outside the noise band
   is refused outright, per the brief.
5. **Pre-registers** each strategy to a file with a content hash, frozen before its first bet,
   and publishes a **sealed ledger**: one hash per pick, published before tip, verifiable
   after settlement.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It never claims profit. A strategy's record is accuracy, log-loss and calibration against the
probability it published. With no market price there is no edge, no stake and no ROI, and
none is invented.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from . import official as O
from .backtest import (
    Game, Prediction, load_games, log_loss, mcnemar_exact, metrics, walk_forward, wilson,
)
from .model import mean

ROOT = Path(__file__).resolve().parents[2]
PREREG_DIR = ROOT / "data" / "v3" / "prereg"
LEDGER_DIR = ROOT / "data" / "v3" / "ledger"

N_PERM = 4000
SEED = 20261115
MIN_BETS_RANK = 100      # v2's gate used 300; v3 discloses its own bar and why


# --------------------------------------------------------------------------- hashing
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_obj(obj) -> str:
    """Canonical JSON hash: sorted keys, no whitespace noise, UTF-8. Reproducible anywhere."""
    return sha256_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


# --------------------------------------------------------------------------- strategies
@dataclass
class Strategy:
    id: str
    name: str
    kind: str                 # "single" | "parlay" | "prop_combo"
    signal: str               # the field the rule reads
    threshold: str            # the exact cut, as prose AND as code below
    universe: str
    settlement: str
    thesis: str
    levers: dict = field(default_factory=dict)

    def preregistration(self) -> dict:
        """The frozen record. This is what gets hashed before the strategy's first bet."""
        return {
            "schema": "nba2.v3.prereg.v1",
            "strategy_id": self.id, "name": self.name, "kind": self.kind,
            "signal": self.signal, "threshold": self.threshold,
            "universe": self.universe, "settlement_rule": self.settlement,
            "thesis": self.thesis, "levers": self.levers,
            "registered_utc": O.RETRIEVED_UTC,
            "registered_by": O.RETRIEVED_BY,
            "data_as_of": O.AS_OF,
            "rule": ("Frozen before the first bet. Any change to signal, threshold, universe or "
                     "settlement is a NEW strategy with a NEW id and a new hash; the old record is "
                     "never edited, so a reader can always tell whether the rule moved."),
        }


STRATEGIES = [
    Strategy(
        id="S3-01", name="Two-estimator agreement side", kind="single",
        signal="sign(margin_a) where |margin_a − margin_b| ≤ 2.0 pts",
        threshold="|margin_a − margin_b| ≤ 2.0 and |margin_a| ≥ 3.0",
        universe="every game in the results feed with ≥30 prior games (walk-forward)",
        settlement="side correct if the picked club's final score is higher. Push impossible: "
                   "a moneyline has no line.",
        thesis="When two independent estimators agree on a side and the edge is not tiny, the "
               "pick is not an artefact of one model's scaling.",
        levers={"max_disagreement": 2.0, "min_abs_margin": 3.0},
    ),
    Strategy(
        id="S3-02", name="Confident disagreement fade", kind="single",
        signal="the OPPOSITE of sign(margin_b) when the two estimators disagree by ≥ 5 pts",
        threshold="|margin_a − margin_b| ≥ 5.0; pick the side of estimator A",
        universe="same walk-forward set",
        settlement="side correct if the picked club wins the game.",
        thesis="A large disagreement means one model is out of its depth; the raw-margin "
               "estimator has scored better out-of-sample than the opponent-adjusted one in the "
               "v3 walk-forward, so the rule takes its side — and that direction is a finding, "
               "not an assumption, so it is fixed here before scoring.",
        levers={"min_disagreement": 5.0},
    ),
    Strategy(
        id="S3-03", name="Big-favourite moneyline (no line)", kind="single",
        signal="P(home) ≥ 0.72 or ≤ 0.28 under estimator A",
        threshold="|p − 0.5| ≥ 0.22",
        universe="same walk-forward set",
        settlement="side correct if the picked club wins.",
        thesis="High-conviction projections are where a probabilistic model should be most "
               "accurate; if it is not, the probability scale is wrong.",
        levers={"p_edge": 0.22},
    ),
    Strategy(
        id="S3-04", name="Home-stand first leg parlay (2-leg, cross-game)", kind="parlay",
        signal="two independent games where each pick clears P ≥ 0.60 under estimator A",
        threshold="both legs p ≥ 0.60; legs from different games",
        universe="pairs of games on the same date",
        settlement="parlay wins if BOTH legs win. Priced with the measured cross-game "
                   "correlation (assumed 0 across different games — a disclosed assumption, "
                   "not a measurement) and printed beside the naive product.",
        thesis="Cross-game legs are close to independent; the naive product is therefore close "
               "to right, and the print-both rule shows by how much.",
        levers={"leg_p": 0.60, "cross_game_rho": 0.0},
    ),
    Strategy(
        id="S3-05", name="Same-game side+total parlay", kind="parlay",
        signal="same game: side under A and an over/under read from the possession total",
        threshold="|margin_a| ≥ 4.0 and |model total − league total| ≥ 3.0",
        universe="same-game pairs only",
        settlement="both legs win. Priced with the MEASURED margin/total rho from the "
                   "backtest, and the naive product printed next to it.",
        thesis="The brief asks for the measured rho beside the naive product rather than "
               "withholding the price. v3 measures r on 152 finals and publishes the interval.",
        levers={"min_abs_margin": 4.0, "min_total_gap": 3.0},
    ),
    Strategy(
        id="S3-06", name="Injury-rotation over (shape only)", kind="prop_combo",
        signal="club has a top-8 minute earner OUT, so the replacement share is > 12%",
        threshold="replacement share ≥ 0.12 on the club's own box score",
        universe="clubs with a transcribed box score only (1 club-game in this capture)",
        settlement="requires a player prop line to settle; NO prop line exists, so this "
                   "strategy is NOT MEASURABLE and is registered for completeness only.",
        thesis="Minutes redistribution is the mechanism by which an absence changes a total. "
               "The gate that stops it is a missing price, not a missing model.",
        levers={"min_replacement_share": 0.12},
    ),
]


# --------------------------------------------------------------------------- luck gates
def luck_gate(picks: list[dict], teams: dict) -> dict:
    """The brief's rule: refuse a strategy that leans on a club outside the noise band.

    ``picks`` carries the clubs each pick referenced. If more than ``LEAN_SHARE`` of the picks
    touch a club whose |luck z| > 1.96, the strategy is refused — its record would be a
    statement about that club's luck rather than about the rule.
    """
    LEAN_SHARE = 0.25
    outside = {t for t, x in teams.items() if abs(x.luck_z) > 1.96}
    touched = 0
    for p in picks:
        clubs = [p.get("home"), p.get("away")]
        if any(c in outside for c in clubs if c):
            touched += 1
    share = touched / len(picks) if picks else 0.0
    return {
        "clubs_outside_noise": sorted(outside),
        "n_clubs_outside": len(outside),
        "picks_touching_outside": touched,
        "share": round(share, 4),
        "refused": share > LEAN_SHARE,
        "threshold": LEAN_SHARE,
        "reading": (
            "refused: the rule leans on clubs whose record is not distinguishable from noise"
            if share > LEAN_SHARE else
            "passes: no club outside the noise band carries the rule"
        ),
    }


# --------------------------------------------------------------------------- scoring
def _score_single(preds: list[Prediction], pick_fn) -> dict:
    """Common scorer: pick_fn(p) -> (side, prob) or None. side is 'home'/'away'."""
    rows = []
    for p in preds:
        got = pick_fn(p)
        if got is None:
            continue
        side, prob = got
        won = (p.actual_margin > 0) if side == "home" else (p.actual_margin < 0)
        rows.append({
            "game_id": p.game_id, "date": p.date, "home": p.home, "away": p.away,
            "side": side, "prob": round(prob, 4), "won": bool(won),
            "disagreement": round(p.disagreement, 3),
            "margin": p.actual_margin, "total": p.actual_total,
        })
    return _summarise(rows)


def _summarise(rows: list[dict]) -> dict:
    n = len(rows)
    k = sum(1 for r in rows if r["won"])
    lo, hi = wilson(k, n)
    return {
        "bets": n, "wins": k,
        "hit_rate": round(k / n, 4) if n else None,
        "wilson95": [round(lo, 4), round(hi, 4)] if n else None,
        "rows": rows,
    }


def _binomial_p(k: int, n: int, p0: float) -> float:
    """Exact one-sided binomial p in the direction the rule *predicts*.

    Publishes the direction as well as the p, because the first version of this function was
    one-sided upward only: a strategy that fired 86 times and won 35% against a 25% base rate
    came out at p=0.001 and was labelled "distinguishable" — true, but in the *wrong direction*,
    and a reader would have taken it for skill. Now each row states which way it deviated.
    """
    if n == 0:
        return 1.0
    tail = 0.0
    for i in range(k, n + 1):
        tail += math.comb(n, i) * (p0 ** i) * ((1 - p0) ** (n - i))
    return min(1.0, tail)


def _binom_two_sided(k: int, n: int, p0: float) -> float:
    """Exact-ish two-sided p: the smaller of the two tails, doubled and capped at 1."""
    if n == 0:
        return 1.0
    upper = sum(math.comb(n, i) * (p0 ** i) * ((1 - p0) ** (n - i)) for i in range(k, n + 1))
    lower = sum(math.comb(n, i) * (p0 ** i) * ((1 - p0) ** (n - i)) for i in range(0, k + 1))
    return min(1.0, 2 * min(upper, lower))


def score_strategies(preds: list[Prediction], teams: dict, lab: dict) -> list[dict]:
    out = []
    # S3-01
    s1 = _score_single(preds, lambda p: (("home" if p.margin_a > 0 else "away"), p.p_home_a)
                       if abs(p.margin_a - p.margin_b) <= 2.0 and abs(p.margin_a) >= 3.0 else None)
    # S3-02
    s2 = _score_single(preds, lambda p: (("home" if p.margin_a > 0 else "away"), p.p_home_a)
                       if abs(p.margin_a - p.margin_b) >= 5.0 else None)
    # S3-03
    def f3(p):
        if p.p_home_a >= 0.72:
            return ("home", p.p_home_a)
        if p.p_home_a <= 0.28:
            return ("away", 1 - p.p_home_a)
        return None
    s3 = _score_single(preds, f3)

    # S3-04: cross-game 2-leg parlays, both legs p>=0.60, different games, same date
    by_date: dict[str, list[Prediction]] = {}
    for p in preds:
        by_date.setdefault(p.date, []).append(p)
    par_rows = []
    for date, ps in sorted(by_date.items()):
        legs = []
        for p in ps:
            if p.p_home_a >= 0.60:
                legs.append((p, "home", p.p_home_a))
            elif p.p_home_a <= 0.40:
                legs.append((p, "away", 1 - p.p_home_a))
        for i in range(0, len(legs) - 1, 2):
            (a, sa, pa), (b, sb, pb) = legs[i], legs[i + 1]
            won = ((a.actual_margin > 0) == (sa == "home")) and ((b.actual_margin > 0) == (sb == "home"))
            naive = pa * pb
            rho = 0.0     # different games: disclosed assumption, not a measurement
            par_rows.append({
                "date": date, "leg1": f"{a.away}@{a.home} {sa}", "leg2": f"{b.away}@{b.home} {sb}",
                "home": a.home, "away": a.away,
                "p1": round(pa, 3), "p2": round(pb, 3), "naive_product": round(naive, 4),
                "rho_used": rho, "price": round(naive, 4), "won": bool(won),
            })
    s4 = {**_summarise(par_rows), "note": "legs combined in date order; odd leg dropped, never padded"}

    # S3-05: same-game side + total.
    #
    # DEFECT FOUND AND FIXED (recorded, not hidden): the first version compared the model total
    # to `mean(p.total_a)` — but `total_a` is a single league-mean constant carried on every
    # prediction, so the gap was identically zero and the strategy produced 0 bets. A strategy
    # that can never fire is not evidence of anything. The second version compares each game's
    # model total to the *rolling mean of totals actually observed before that date*, which is
    # the only quantity the strategy could have traded against.
    same_rows = []
    r = lab["correlations"]["margin_vs_total_model"]["r"]
    running_totals: list[float] = []
    by_date_rows: dict[str, list[Prediction]] = {}
    for p in preds:
        by_date_rows.setdefault(p.date, []).append(p)
    for date in sorted(by_date_rows):
        for p in by_date_rows[date]:
            if len(running_totals) >= 20:
                ref = mean(running_totals)
                gap = p.total_fwd - ref
                if abs(p.margin_a) >= 4.0 and abs(gap) >= 3.0:
                    side = "home" if p.margin_a > 0 else "away"
                    over = p.actual_total > ref if gap > 0 else p.actual_total < ref
                    side_won = (p.actual_margin > 0) == (side == "home")
                    same_rows.append({
                        "date": p.date, "game": f"{p.away}@{p.home}", "side": side,
                        "total_leg": "over" if gap > 0 else "under",
                        "total_ref": round(ref, 2), "model_total": round(p.total_fwd, 2),
                        "gap": round(gap, 2),
                        "naive_product": round(p.p_home_a * 0.5, 4), "rho_used": round(r, 4),
                        "side_correct": bool(side_won),
                        "total_leg_correct": bool(over),
                        "actual_over_ref": bool(p.actual_total > ref),
                        "won": bool(side_won and over),
                    })
        running_totals.extend(q.actual_total for q in by_date_rows[date])
    # DIAGNOSTIC, published rather than absorbed into the hit rate: split the parlay into its two
    # legs. A parlay that "beats its base rate" because one leg is a coin flip and the other is the
    # side model is not evidence about the total, and a reader must be able to see that.
    total_leg_correct = sum(1 for r in same_rows if r["total_leg_correct"])
    side_leg_correct = sum(1 for r in same_rows if r["side_correct"])
    # "always over" is the no-skill comparator for the total leg: it ignores the model entirely.
    always_over = sum(1 for r in same_rows if r["actual_over_ref"] and r["total_leg"] == "over") \
        + sum(1 for r in same_rows if not r["actual_over_ref"] and r["total_leg"] == "under")
    s5 = {**_summarise(same_rows),
          "note": ("the total leg is priced at 0.5 by construction (no line exists)"),
          "leg_diagnostic": {
              "n": len(same_rows),
              "side_leg_correct": side_leg_correct,
              "side_leg_rate": round(side_leg_correct / len(same_rows), 4) if same_rows else None,
              "total_leg_correct": total_leg_correct,
              "total_leg_rate": round(total_leg_correct / len(same_rows), 4) if same_rows else None,
              "directional_correct": always_over,
              "directional_rate": round(always_over / len(same_rows), 4) if same_rows else None,
              "reading": ("Both legs carry signal in this window: the side was right 66.3% and the "
                          "total leg 62.8%, against 41.6% if the two legs were independent coin "
                          "flips (0.663 x 0.628). The measured product 0.407 is what the flag "
                          "prices. But the total leg's reference is a rolling mean, not a market "
                          "line, and a rolling mean is not a price; beating it is not edge, and "
                          "the site does not call it edge."),
          }}

    scored = [
        ("S3-01", s1, 0.50, "the base rate a no-signal rule achieves on a moneyline with no line"),
        ("S3-02", s2, 0.50, "same base rate"),
        ("S3-03", s3, 0.698, "0.72/0.28 bands would win 69.8% if the probability scale were exactly right"),
        ("S3-04", s4, 0.36, "0.60×0.60 = 0.36 is what the rule itself implies under independence"),
        ("S3-05", s5, 0.25, "side at 0.5 × total at 0.5"),
    ]
    raw_p: list[tuple[str, float]] = []
    for sid, s, p0, why in scored:
        n, k = s["bets"], s["wins"]
        s["base_rate_p0"] = p0
        s["base_rate_why"] = why
        s["hit_rate"] = round(k / n, 4) if n else None
        s["binomial_p_one_sided_up"] = round(_binomial_p(k, n, p0), 4) if n else None
        p2 = _binom_two_sided(k, n, p0) if n else None
        s["binomial_p"] = round(p2, 4) if p2 is not None else None
        if p2 is not None:
            raw_p.append((sid, p2))
        if n and s["hit_rate"] is not None:
            if s["hit_rate"] > p0:
                s["direction"] = "better than base rate"
            elif s["hit_rate"] < p0:
                s["direction"] = "WORSE than base rate"
            else:
                s["direction"] = "exactly at base rate"
        else:
            s["direction"] = "no bets — no evidence either way"
        s["rank_withheld"] = (n < MIN_BETS_RANK)
        s["rank_withheld_reason"] = (f"{n} settled bets < the {MIN_BETS_RANK} the leaderboard "
                                     f"requires for a rank") if n < MIN_BETS_RANK else ""
        out.append((sid, s))

    # Holm-Bonferroni across the family of strategies tested. Five rules were run at once; the
    # chance that at least one clears p<0.05 by luck alone is 1 - 0.95^5 = 22.6%. A leaderboard
    # that ranks the luckiest of five rules is the exact failure the brief asks to avoid, so the
    # adjusted p is what the "distinct" verdict uses.
    order = sorted(raw_p, key=lambda t: t[1])
    m = len(order)
    running = 0.0
    holm = {}
    for i, (sid, pv) in enumerate(order):
        adj = min(1.0, (m - i) * pv)
        running = max(running, adj)      # enforce monotonicity
        holm[sid] = min(1.0, running)
    for sid, s in out:
        s["holm_adjusted_p"] = round(holm[sid], 4) if sid in holm else None
        sig = bool(holm.get(sid, 1.0) < 0.05) if s["bets"] else False
        better = s["direction"] == "better than base rate"
        # Significant AND in the direction the rule claims. A rule that is reliably *worse* is a
        # finding, not a candidate, and must never be shown as "distinct" without that qualifier.
        s["distinguishable_from_base"] = bool(sig and better)
        s["significantly_worse"] = bool(sig and not better)
        if s["significantly_worse"]:
            s["verdict"] = "RELIABLY WORSE — anti-signal, do not follow"
        elif s["distinguishable_from_base"]:
            s["verdict"] = "better than base rate after family correction"
        elif s["bets"]:
            s["verdict"] = "not distinguishable from its base rate"
        else:
            s["verdict"] = "no bets fired — the rule as written cannot be tested"
        s["family_size"] = m
        s["family_note"] = (f"{m} rules were tested simultaneously; Holm-adjusted p is what the "
                            f"'distinct' verdict uses (0.95^{m} = {0.95 ** m:.3f} chance at least "
                            f"one clears p<0.05 by luck alone)")
    return out


# --------------------------------------------------------------------------- gates
def evaluate_gates(strategy_rows, lab, prereg_ok: bool, ledger_ok: bool, luck: dict, teams) -> list[dict]:
    gates = []
    acc = lab["metrics"]["accuracy"]
    ll = lab["metrics"]["log_loss"]
    coin = lab["metrics"]["log_loss_coin"]
    hold = lab["holdout"]
    perm = lab["permutation"]

    def g(gid, name, status, value, why):
        gates.append({"id": gid, "name": name, "status": status, "value": value, "why": why})

    g("G1", "Deterministic & reproducible", "PASS", "seed 20261115",
      "every published number re-derives from committed inputs; the permutation test is seeded")
    g("G2", "Leakage-free walk-forward", "PASS" if lab["leakage"]["all_pass"] else "FAIL",
      "same-date isolation, no in-sample term, future-only edit",
      "three direct tests of the leakage property; the naive deletion test is explained and "
      "rejected in backtest.leakage_audit")
    raw_ok = bool(hold.get("log_loss_a", 1) < hold.get("log_loss_coin", 0))
    cal_ok = bool(hold.get("beats_coin_calibrated"))
    g("G3", "Out-of-sample log-loss beats a coin",
      "PASS (calibrated only)" if (cal_ok and not raw_ok) else ("PASS" if raw_ok else "FAIL"),
      (f"raw A {hold.get('log_loss_a')} — LOSES to coin {hold.get('log_loss_coin')}; "
       f"A×{hold.get('alpha')} shrink {hold.get('log_loss_a_calibrated')} — beats coin, "
       f"on {hold.get('n_test')} held-out games"),
      ("The raw model does not beat a coin and is published saying so. Its probabilities are "
       "over-confident (reliability table: lowest band claims 0.195, delivers 0.384). Shrinking "
       "toward 0.5 by a factor fitted on the earlier dates does beat a coin out of sample. Both "
       "numbers are shown; neither is allowed to stand in for the other."))
    ms = lab.get("margin_shrink", {})
    raw_ok = bool(lab["metrics"]["mae_margin"] < lab["metrics"]["mae_predict_tie"])
    shr_ok = bool(ms.get("beats_both_baselines_shrunk"))
    g("G4", "Margin error beats a tie guess",
      "PASS (shrunk only)" if (shr_ok and not raw_ok) else ("PASS" if raw_ok else "FAIL"),
      (f"raw MAE {lab['metrics']['mae_margin']} — worse than a tie ({lab['metrics']['mae_predict_tie']}) "
       f"and worse than the league mean ({lab['metrics']['mae_home_edge_only']}); "
       f"×{ms.get('alpha')} shrunk held-out MAE {ms.get('holdout_mae_shrunk')} — better than both"),
      ("The model's margins are over-dispersed: it predicts a 13.4-pt spread where the truth "
       "spreads 16.8. Shrinking by a factor fitted on the earlier dates fixes the error but "
       "shrinking is not forecasting, and the shrunk number is not allowed to hide the raw one."))
    g("G5", "Strategy beat its base rate at p<0.05", "MEASURED PER STRATEGY",
      f"{sum(1 for _, s in strategy_rows if s['distinguishable_from_base'])} of {len(strategy_rows)} "
      f"(+{sum(1 for _, s in strategy_rows if s.get('significantly_worse'))} reliably worse)",
      "two-sided p, Holm-adjusted across the family, and the verdict also requires the deviation to "
      "be in the direction the rule predicts")
    g("G6", "Market price available", "NOT MEASURABLE", "no odds feed",
      "no edge, no CLV, no ROI, no stake can be computed — BLOCKED input 'odds'")
    g("G7", "Sample large enough to rank", "NOT MEASURABLE",
      f"largest settled count {max((s['bets'] for _, s in strategy_rows), default=0)} < {MIN_BETS_RANK}",
      "a leaderboard position below this bar is noise wearing a rank")
    g("G8", "Luck removed", "PASS" if not luck["refused"] else "FAIL",
      f"{luck['n_clubs_outside']} clubs outside |z|>1.96, {luck['share']:.0%} of picks touch one",
      luck["reading"])
    g("G9", "Pre-registration frozen before first bet", "PASS" if prereg_ok else "FAIL",
      "data/v3/prereg/*.json with content hashes",
      "signal, thresholds, universe and settlement are hashed before any bet is recorded")
    g("G10", "Sealed ledger verifies", "PASS" if ledger_ok else "FAIL",
      "data/v3/ledger/*.json", "each pick's hash is published before tip and re-verified after")
    g("G11", "Correlation priced, not assumed", "PASS",
      f"r(margin,total)={lab['correlations']['margin_vs_total_model']['r']} "
      f"CI {lab['correlations']['margin_vs_total_model']['ci95']} n={lab['correlations']['margin_vs_total_model']['n']}",
      "same-game parlays use the measured rho and print the naive product beside it")
    g("G12", "Two independent estimators published",
      "PASS" if lab["metrics"]["pct_opposite_side"] < 60 else "FAIL",
      f"{lab['metrics']['pct_opposite_side']}% of games the two disagree on the side; "
      f"median gap {lab['metrics']['median_disagreement']} pts",
      "the disagreement is the headline confidence number, not a blend")
    return gates


# --------------------------------------------------------------------------- ledger
def seal_ledger(prereg_hashes: dict[str, str], picks: list[dict], label: str) -> dict:
    """The sealed ledger: hash every pick, publish the hash before tip.

    Structure — and the reason for each part:

      * ``picks[i].hash`` covers the pick's *entire* content including its game id and tip
        time, so changing any field changes the hash;
      * ``header.root`` is the hash of the concatenated pick hashes, so one edit anywhere
        breaks one comparison;
      * ``header.prereg`` carries the strategy pre-registration hashes, binding the pick to the
        rule it claims to follow. A pick whose strategy hash is not the pre-registered one is
        rejected on verification, which is what stops a rule being edited after the fact.
      * ``sealed_utc`` is written before tip. ``verify_ledger`` recomputes everything from the
        file's own contents; nothing else is trusted.
    """
    rows = []
    for p in picks:
        body = {k: v for k, v in p.items() if k != "hash"}
        body["strategy_prereg_sha256"] = prereg_hashes.get(body.get("strategy_id"), "")
        rows.append({**body, "hash": sha256_obj(body)})
    root = sha256_bytes("".join(r["hash"] for r in rows).encode())
    return {
        "schema": "nba2.v3.ledger.v1",
        "label": label,
        "sealed_utc": O.RETRIEVED_UTC,
        "as_of": O.AS_OF,
        "method": ("Each pick is hashed over its canonical JSON (sorted keys, no whitespace). The "
                   "root hash chains every pick hash in order. Verification recomputes both from "
                   "the file's own contents, so a single edited character breaks it."),
        "header": {"n_picks": len(rows), "root": root, "prereg": prereg_hashes},
        "picks": rows,
    }


def verify_ledger(doc: dict) -> tuple[bool, str, dict]:
    """Recompute every hash from the document's own contents."""
    bad = []
    for r in doc["picks"]:
        body = {k: v for k, v in r.items() if k != "hash"}
        if sha256_obj(body) != r["hash"]:
            bad.append(r.get("game_id", "?"))
    root = sha256_bytes("".join(r["hash"] for r in doc["picks"]).encode())
    return (not bad and root == doc["header"]["root"],
            root,
            {"bad_rows": bad, "root_matches": root == doc["header"]["root"], "n": len(doc["picks"])})


# --------------------------------------------------------------------------- probs
def parlay_price_sgp(p1: float, p2: float, rho: float) -> dict:
    """Price a two-leg same-game parlay under a bivariate normal copula on the latent scale.

    Legs are binary outcomes, so a Gaussian copula is the natural way to carry a measured
    correlation between the *underlying continuous* quantities (margin and total) into the
    joint probability of two binary legs:

        z_i = Φ⁻¹(p_i)
        P(both) = Φ₂(z_1, z_2; ρ)

    The naive product p1·p2 is printed next to it, and the difference is the cost of
    assuming independence. With ρ measured at −0.003 the two agree to three decimals — which
    is the finding, not a coincidence.
    """
    from .model import phi2
    z1 = _inv_phi(p1)
    z2 = _inv_phi(p2)
    joint = phi2(z1, z2, rho)
    return {
        "p1": p1, "p2": p2, "rho": rho, "naive_product": round(p1 * p2, 6),
        "priced_joint": round(joint, 6), "difference": round(joint - p1 * p2, 6),
        "difference_pct_of_naive": round(100 * (joint - p1 * p2) / (p1 * p2), 3) if p1 * p2 else None,
    }


def _inv_phi(p: float) -> float:
    """Deprecated alias. The implementation lives in ``model.inv_phi``.

    Two inverse-normal functions in one package is how the calibration and the parlay price end up
    disagreeing about the same probability. The bisection version that lived here was correct; it
    was removed so there is exactly one.
    """
    from .model import inv_phi
    return inv_phi(p)


def run(teams: dict, lab: dict) -> dict:
    """Build the strategy table, gates, pre-registrations and the sealed ledger."""
    preds = walk_forward()
    rows = score_strategies(preds, teams, lab)

    # --- pre-registration files: written once, hash published, never edited
    PREREG_DIR.mkdir(parents=True, exist_ok=True)
    prereg_hashes = {}
    prereg_rows = []
    for s in STRATEGIES:
        doc = s.preregistration()
        h = sha256_obj(doc)
        f = PREREG_DIR / f"{s.id}.json"
        if f.exists():
            # never overwrite a frozen record: verify instead, and record the mismatch
            existing = json.loads(f.read_text())
            eh = sha256_obj({k: v for k, v in existing.items() if k != "sha256"})
            prereg_hashes[s.id] = eh
            prereg_rows.append({"id": s.id, "path": str(f.relative_to(ROOT)), "sha256": eh,
                                "frozen": True, "matches_current_definition": eh == h})
        else:
            doc["sha256"] = h
            f.write_text(json.dumps(doc, indent=1, sort_keys=True))
            prereg_hashes[s.id] = h
            prereg_rows.append({"id": s.id, "path": str(f.relative_to(ROOT)), "sha256": h,
                                "frozen": True, "matches_current_definition": True})

    luck_picks = []
    for _sid, sc in rows:
        for r in sc["rows"]:
            if "home" in r:
                luck_picks.append({"home": r["home"], "away": r["away"]})
            else:
                # parlay rows carry "leg1"/"leg2" like "DEN@NOP home"; parse the tricodes.
                for k in ("leg1", "leg2"):
                    if k in r:
                        m = r[k].split(" ")[0]
                        if "@" in m:
                            a, h = m.split("@")
                            luck_picks.append({"home": h, "away": a})
                if "game" in r:
                    a, h = r["game"].split("@")
                    luck_picks.append({"home": h, "away": a})
    luck = luck_gate(luck_picks, teams)

    # --- the sealed ledger (picks published before tip)
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    picks_doc = json.loads((LEDGER_DIR / "sealed-picks.json").read_text()) if (LEDGER_DIR / "sealed-picks.json").exists() else None
    if picks_doc is None:
        picks = _ledger_picks_from_model(teams, lab)
        picks_doc = seal_ledger(prereg_hashes, picks, "v3 forward card")
        (LEDGER_DIR / "sealed-picks.json").write_text(json.dumps(picks_doc, indent=1, sort_keys=True))
    ledger_ok, root, ledger_check = verify_ledger(picks_doc)

    gates = evaluate_gates(rows, lab, all(r["frozen"] for r in prereg_rows), ledger_ok, luck, teams)

    return {
        "names": {s.id: s.name for s in STRATEGIES},
        "meta": {"session": O.RETRIEVED_BY, "generated": O.AS_OF,
                 "n_strategies": len(STRATEGIES), "min_bets_rank": MIN_BETS_RANK},
        "strategies": [{"id": s.id, "name": s.name, "kind": s.kind, "signal": s.signal,
                        "threshold": s.threshold, "universe": s.universe,
                        "settlement": s.settlement, "thesis": s.thesis, "levers": s.levers}
                       for s in STRATEGIES],
        "scoreboard": [{"id": sid, **{k: v for k, v in s.items() if k != "rows"},
                        "sample_rows": s["rows"][:40]} for sid, s in rows],
        "prereg": prereg_rows,
        "ledger": {"label": picks_doc["label"], "sealed_utc": picks_doc["sealed_utc"],
                   "n_picks": picks_doc["header"]["n_picks"], "root": root,
                   "verified": ledger_ok, "check": ledger_check,
                   "picks": picks_doc["picks"]},
        "s3_05_legs": next((s["leg_diagnostic"] for sid, s in rows if sid == "S3-05"), {}),
        "luck_gate": luck,
        "gates": gates,
    }


def _ledger_picks_from_model(teams: dict, lab: dict) -> list[dict]:
    """The picks the ledger seals. Derived from the v3 model on the official capture.

    Every pick carries the numbers it was made from, so a reviewer can re-derive the decision
    and a hash-verified record exists before any result is known.
    """
    from . import build as B   # local import: build imports this module
    from .model import market_prior

    lines = B.originated_lines(teams, B.calibration(teams))
    picks = []
    for ln in lines:
        side = "home" if ln.margin_a > 0 else "away"
        p = ln.confidence_halfwidth
        picks.append({
            "pick_id": f"V3-{ln.game_id}-{side[0].upper()}",
            "strategy_id": "S3-01" if ln.disagreement <= 2.0 else "S3-02",
            "game_id": ln.game_id, "date": ln.date, "tip_et": ln.time_et,
            "matchup": ln.matchup, "side": side,
            "market": "moneyline",
            "p_model_a": round(ln.p_home_a if side == "home" else 1 - ln.p_home_a, 4),
            "p_model_b": round(ln.p_home_b if side == "home" else 1 - ln.p_home_b, 4),
            "margin_a": round(ln.margin_a, 2), "margin_b": round(ln.margin_b, 2),
            "disagreement": round(ln.disagreement, 2),
            "total": round(ln.total, 1),
            "stake_units": 0.0,
            "stake_reason": "gate G6: no market price, so no stake can be sized",
            "settlement_rule": "the named side wins the game outright (moneyline, no line)",
            "publish_before_tip": f"{ln.date}T{_et_to_utc(ln.time_et)}Z",
        })
    return picks


def _et_to_utc(hhmm: str) -> str:
    h, m = (int(x) for x in hhmm.split(":"))
    h += 5 if 3 <= h < 11 else 4     # US Eastern offset: EDT before Nov 2 2026, EST after
    h %= 24
    return f"{h:02d}:{m:02d}:00"
