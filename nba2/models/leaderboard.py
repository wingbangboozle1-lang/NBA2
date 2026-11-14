"""Strategy leaderboard: registration, scoring, tiers, rewards, clustering.

The competition design is deliberately anti-luck:

* the score is built from CLV and line-accuracy/calibration, NOT from recent PnL, so a
  variance spike cannot buy a prize;
* every metric is `None` until it is measured. A blocked strategy sits in an untiered
  "Blocked" bucket and cannot win;
* strategies whose bet sets overlap past a Jaccard threshold are reported as one cluster,
  so one signal cannot be awarded three times;
* the number of evaluation attempts is part of the score input (Deflated Sharpe), so
  silent fishing makes your own rank worse.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .. import config
from . import gates
from .correlation import overlap_jaccard


@dataclass
class Entry:
    strategy_id: str
    name: str
    family: str
    measurements: dict = field(default_factory=dict)
    results: list = field(default_factory=list)
    tier: str = "blocked"
    score: float | None = None
    components: dict = field(default_factory=dict)
    cluster: str | None = None
    blocking_reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id, "name": self.name, "family": self.family,
            "tier": self.tier, "score": self.score, "components": self.components,
            "cluster": self.cluster,
            "blocking_reasons": self.blocking_reasons,
            "gates": [r.as_dict() for r in self.results],
            "measurements": {k: v for k, v in self.measurements.items()},
        }


def score_components(m: dict) -> tuple[float | None, dict]:
    """Weighted 0-100 score from ratified weights. Any missing input -> no score at all."""
    w = config.REWARD_WEIGHTS
    parts: dict[str, float] = {}

    clv = m.get("clv_points")
    if clv is not None:
        # 1 point of CLV ~ a full-strength edge at NBA vig; cap at 1.5 pts
        parts["clv"] = max(0.0, min(1.0, clv / 1.5))
    mae, mae_base = m.get("line_mae"), m.get("baseline_mae")
    if mae is not None and mae_base is not None and mae_base > 0:
        parts["line_mae_improvement"] = max(0.0, min(1.0, (mae_base - mae) / 1.0))
    brier, brier_base = m.get("brier"), m.get("baseline_brier", 0.25)
    if brier is not None and brier_base > 0:
        parts["brier_improvement"] = max(0.0, min(1.0, (brier_base - brier) / 0.010))
    slope = m.get("calibration_slope")
    if slope is not None and math.isfinite(slope):
        parts["calibration_slope_proximity"] = max(0.0, 1.0 - abs(1.0 - slope) / 0.15)
    stab = m.get("min_stability")
    if stab is not None:
        parts["robustness"] = max(0.0, min(1.0, (stab - 0.5) / 0.5))

    have = set(parts)
    if have != set(w):
        return None, parts
    total = sum(w[k] * parts[k] for k in w) * 100.0
    return round(total, 2), parts


def build(strategies: list[dict], measurements: dict[str, dict],
          bet_sets: dict[str, set[str]] | None = None) -> list[Entry]:
    bet_sets = bet_sets or {}
    entries: list[Entry] = []
    for s in strategies:
        m = measurements.get(s["id"], {})
        e = Entry(s["id"], s["name"], s["family"], m)
        e.results = gates.evaluate(m)
        e.tier = gates.tier_for(e.results)
        if m.get("n_games_predicted") is None:
            e.blocking_reasons.append("no predictions sealed for this strategy yet")
        blocked = [r for r in e.results if r.result == gates.BLOCKED]
        e.blocking_reasons.extend(f"{r.gate_id}: {r.reason}" for r in blocked if r.reason)
        e.score, e.components = score_components(m)
        if e.score is None and e.tier != "rejected":
            e.tier = "blocked" if s.get("inputs_blocked", True) else "research"
        entries.append(e)

    # cluster overlapping strategies so one signal cannot take several prizes
    clustered: dict[str, str] = {}
    for i, a in enumerate(entries):
        if a.strategy_id in clustered:
            continue
        for b in entries[i + 1:]:
            if b.strategy_id in clustered:
                continue
            sa, sb = bet_sets.get(a.strategy_id, set()), bet_sets.get(b.strategy_id, set())
            if sa and sb and overlap_jaccard(sa, sb) >= 0.70:
                clustered[b.strategy_id] = a.strategy_id
                b.cluster = a.strategy_id
        clustered.setdefault(a.strategy_id, a.strategy_id)
        a.cluster = a.cluster or a.strategy_id

    ranked = sorted([e for e in entries if e.score is not None], key=lambda e: -e.score)  # type: ignore[arg-type]
    for rank, e in enumerate(ranked, start=1):
        e.components["rank"] = rank
    return entries


def reward_allocation(entries: list[Entry], prize_pool_units: float = 100.0) -> dict:
    """Distribute the prize pool by tier share, then by score inside the tier.

    With no measured entries, the whole pool is unallocated - it is never split just to look
    busy, and no strategy is paid for having a hypothesis.
    """
    eligible = [e for e in entries if e.tier in config.TIERS and e.score is not None
                and e.cluster == e.strategy_id]
    if not eligible:
        return {"pool": prize_pool_units, "allocated": 0.0, "unallocated": prize_pool_units,
                "awards": [], "reason": "no strategy has passed the gates on measured data yet"}
    shares: dict[str, float] = {}
    for e in eligible:
        share = config.TIERS[e.tier]["reward_share"]
        peers = [o for o in eligible if o.tier == e.tier]
        tot = sum(o.score or 0 for o in peers) or 1.0
        shares[e.strategy_id] = share * ((e.score or 0) / tot)
    allocated = prize_pool_units * sum(shares.values())
    return {
        "pool": prize_pool_units,
        "allocated": round(allocated, 2),
        "unallocated": round(prize_pool_units - allocated, 2),
        "awards": [{"strategy_id": k, "amount": round(prize_pool_units * v, 2)} for k, v in shares.items()],
        "reason": "weights: " + ", ".join(f"{k}={v}" for k, v in config.REWARD_WEIGHTS.items()),
    }


def table_rows(entries: list[Entry]) -> list[dict]:
    rows = []
    for e in entries:
        passed = sum(1 for r in e.results if r.result == "PASS")
        failed = sum(1 for r in e.results if r.result == "FAIL")
        # BLOCKED and AT-RISK are different states and must not be merged into one count: a
        # blocked gate is unmeasurable (no price, no data), an at-risk gate is measurable but
        # currently failing. Collapsing them printed '10 blocked' next to a matrix that said
        # 8 blocked + 2 at-risk, which is what crosscheck CC-GATE-02 caught.
        blocked = sum(1 for r in e.results if r.result == "BLOCKED")
        at_risk = sum(1 for r in e.results if r.result == "AT-RISK")
        rows.append({
            "strategy_id": e.strategy_id, "name": e.name, "family": e.family,
            "score": e.score, "tier": config.TIERS.get(e.tier, {}).get("label", e.tier),
            "gates_passed": passed, "gates_failed": failed, "gates_blocked": blocked,
            "gates_at_risk": at_risk,
            "cluster": e.cluster, "n_bets": e.measurements.get("settled_bets"),
            "blocking": "; ".join(e.blocking_reasons[:2]) if e.blocking_reasons else "—",
        })
    return rows
