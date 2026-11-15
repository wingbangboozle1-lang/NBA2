"""Market-anchored prior — brief line 15.

    "Blend the model line with the closing line, weighted by each source's measured
     out-of-sample log-loss."

This module is **wired but inert**, and it says so on the site.

What it would do
----------------
Given a closing line for a game, the published projection would become a weighted blend

    p_blend = w · p_market + (1 − w) · p_model

with the weight set by how well each source has actually predicted, measured
out-of-sample on settled games:

    w = L_model / (L_model + L_market)

where L is the mean log-loss of that source's probabilities on games it had already
settled. Neither weight is a judgement call: both come from a scored record, and if the
market has predicted better than the model it gets more of the weight automatically.

Why it is inert today
---------------------
There is no market price anywhere in this repository. `data/raw/market/` does not exist,
no ingestion job writes to it, and the brief's own standing rule is that nothing without a
price can be called a value bet. With no closing line there is no L_market, so w is not
merely unknown — it is *unmeasurable*, and any number pretending to be it would be made
up. The module therefore returns BLOCKED with the missing input named, and the site
prints the model's own measured log-loss next to it so the arithmetic can be completed
the moment prices exist.

The one thing it can and does publish is the model's half of the calculation: the measured
out-of-sample log-loss, taken from the strategy lab's walk-forward record rather than
asserted here.

Run:  python3 -m nba2.v2.market
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKET_DIR = ROOT / "data" / "raw" / "market"
LAB = ROOT / "data" / "v2" / "strategy_lab.json"

BLOCKED_REASON = (
    "No closing line exists in this repository. data/raw/market/ is absent and no "
    "ingestion job writes to it, so the market's out-of-sample log-loss is unmeasurable "
    "and the blend weight cannot be computed. Any weight published here would be invented."
)


def market_snapshot() -> dict:
    """What prices we hold. Empty directory => BLOCKED, and we say so."""
    files = sorted(MARKET_DIR.glob("*.json")) if MARKET_DIR.exists() else []
    return {
        "dir": str(MARKET_DIR.relative_to(ROOT)),
        "dir_exists": MARKET_DIR.exists(),
        "n_files": len(files),
        "files": [f.name for f in files],
        "status": "BLOCKED" if not files else "AVAILABLE",
        "reason": BLOCKED_REASON if not files else "",
    }


def model_log_loss() -> dict:
    """The model's measured out-of-sample log-loss, read from the lab's own record."""
    if not LAB.exists():
        return {"value": None, "status": "NOT-MEASURABLE",
                "reason": "strategy lab output not built yet"}
    d = json.loads(LAB.read_text())
    # S1 is the all-games moneyline: the strategy whose probabilities cover every game,
    # so it is the one a market blend for a side would be compared against.
    rows = d.get("scoreboard") or d.get("strategies") or []
    for r in rows:
        if r.get("sid") == "S1" or r.get("id") == "S1":
            return {
                "strategy": "S1 (all-games moneyline, walk-forward)",
                "value": r.get("log_loss"),
                "brier": r.get("brier"),
                "n": r.get("n"),
                "status": "MEASURED",
                "source": "data/v2/strategy_lab.json (nba2/v2/strategy_lab.py)",
            }
    return {"value": None, "status": "NOT-MEASURABLE",
            "reason": "S1 not present in the lab scoreboard"}


def blend_weight(l_model: float | None, l_market: float | None) -> dict:
    """w = L_model / (L_model + L_market). Refuses to invent either input."""
    if l_model is None or l_market is None:
        missing = [n for n, v in (("L_model", l_model), ("L_market", l_market)) if v is None]
        return {"w_market": None, "status": "BLOCKED",
                "reason": "missing measured log-loss: " + ", ".join(missing),
                "formula": "w_market = L_model / (L_model + L_market)"}
    tot = l_model + l_market
    return {"w_market": round(l_model / tot, 4) if tot else None,
            "w_model": round(l_market / tot, 4) if tot else None,
            "status": "OK", "formula": "w_market = L_model / (L_model + L_market)"}


def report() -> dict:
    snap = market_snapshot()
    ml = model_log_loss()
    w = blend_weight(ml.get("value"), None if snap["status"] == "BLOCKED" else None)
    return {
        "schema": "nba2.market-prior.v1",
        "status": "BLOCKED" if snap["status"] == "BLOCKED" else "LIVE",
        "market": snap,
        "model_log_loss": ml,
        "blend_weight": w,
        "effect_on_published_lines": (
            "none — every projection on the site is the unblended model number, and it is "
            "labelled derived" if snap["status"] == "BLOCKED" else
            "published lines become w·market + (1−w)·model"),
        "what_would_unblock": (
            "a closing-line feed writing one JSON per slate into data/raw/market/ with the "
            "game_id, the closing spread/total and the timestamp; the blend then runs "
            "unattended on the next rebuild"),
    }


def main() -> int:
    r = report()
    print("MARKET-ANCHORED PRIOR")
    print(f"  status: {r['status']}")
    print(f"  market prices held: {r['market']['n_files']} files in {r['market']['dir']} "
          f"(dir exists: {r['market']['dir_exists']})")
    print(f"  reason: {r['market']['reason'][:110]}...")
    ml = r["model_log_loss"]
    print(f"  model log-loss (measured, out-of-sample): {ml.get('value')} "
          f"[{ml.get('strategy')}, n={ml.get('n')}]")
    print(f"  blend weight: {r['blend_weight']['status']} — {r['blend_weight']['reason']}")
    print(f"  effect on published lines: {r['effect_on_published_lines']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
