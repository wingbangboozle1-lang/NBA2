#!/usr/bin/env python3
"""generate_picks_lab.py — NBA2 slate pick generator (lab edition, session-arena-35264d96) (session-arena-35264d96).

Generates picks for an upcoming slate (up to 3 days ahead) from OUR originated lines.

Hard rules (enforced in code, not just documentation):
  1. No pick is emitted for a strategy whose gates have not passed. In this repo every
     strategy is 'research'/'candidate' until backtests exist, so the tool emits ZERO real
     picks and either exits in demo mode or refuses.
  2. Lines must be originated by us. Market lines are optional context (CLV is measured
     post-hoc); the tool never uses a market line to create an edge.
  3. Every emitted pick carries full provenance: strategy id, gate checks, staking math.
  4. Demo mode uses only *.demo.csv inputs and stamps demo:true on every pick.

Usage:
  python3 tools/generate_picks_lab.py --demo            # run on data/demo/* (synthetic)
  python3 tools/generate_picks.py --slate data/slate.csv --lines data/lines.csv \
         --injuries data/injuries.csv --corr data/correlation.csv --out data/picks/
"""
import argparse
import csv
import json
import math
import os
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- Gate definitions (mirror docs/validation-gates.html G1-G13) -------------
GATE_IDS = [
    "G1_sample", "G2_roi_positive", "G3_clv_positive", "G4_calibration",
    "G5_walk_forward", "G6_drawdown", "G7_significance", "G8_no_cherry_pick",
    "G9_regime_check", "G10_portfolio_cap", "G11_corr_matrix_required",
    "G12_sgp_reprice", "G13_parlay_haircut",
]

# Backtest evidence is required for activation; none exists yet, so nothing is active.
BACKTEST_EVIDENCE = {}  # strategy_id -> {"roi":…, "n":…, "clv_pct":…, "t_stat":…} — empty by design


def american_to_breakeven(odds):
    """Return the win probability needed to break even at American odds."""
    if odds is None or odds == "" or odds == 0:
        return None
    odds = float(odds)
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return (-odds) / (-odds + 100.0)


def american_to_decimal(odds):
    odds = float(odds)
    return 1.0 + (100.0 / odds if odds > 0 else 100.0 / (-odds))


def kelly_fraction(p, odds):
    """Full Kelly for a binary bet at American odds; caller applies fractional cap."""
    b = american_to_decimal(odds) - 1.0
    if b <= 0 or not (0 < p < 1):
        return 0.0
    q = 1.0 - p
    return (p * b - q) / b


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r and not r.get("label", "").startswith("#")]
    return rows


def gate_status(strategy):
    """A strategy may generate REAL picks only if every gate has passing backtest evidence."""
    if strategy["id"] not in BACKTEST_EVIDENCE:
        return "BLOCKED — no backtest evidence on file (G1-G9 require out-of-sample results)"
    return "PASS"


def build_picks(lines, strategies, window_dates, demo):
    picks, rejected = [], []
    strat_by_id = {s["id"]: s for s in strategies}
    for row in lines:
        if demo and not row["game_id"].startswith("DEMO-"):
            continue
        if not demo and row["game_id"].startswith("DEMO-"):
            continue
        # date filter: slate window (today .. today+3) is enforced upstream by the slate file
        strat_id = (row.get("strategy_id") or "-").strip()
        breakeven = american_to_breakeven(row["our_odds_american"])
        try:
            fair = float(row["fair_prob"]) if row.get("fair_prob") else None
        except ValueError:
            fair = None
        our_line = row.get("our_line") or ""
        market_line = (row.get("market_line") or "").strip()
        if strat_id in strat_by_id:
            s = strat_by_id[strat_id]
            status = s["status"]
            if not demo and status != "active":
                rejected.append({
                    "game_id": row["game_id"], "market": row["market"],
                    "side": row.get("side", ""), "strategy_id": strat_id,
                    "reason": f"strategy status='{status}'; real picks require status='active' "
                              f"(all gates passed out-of-sample). {gate_status(s)}",
                })
                continue
            if demo and status == "research":
                rejected.append({
                    "game_id": row["game_id"], "market": row["market"],
                    "side": row.get("side", ""), "strategy_id": strat_id,
                    "reason": "DEMO: strategy is research-only; shown for pipeline illustration only",
                })
                continue
            edge = None
            if fair is not None and breakeven is not None:
                edge = round(fair - breakeven, 4)
            if edge is None or edge < 0.015:
                rejected.append({
                    "game_id": row["game_id"], "market": row["market"],
                    "side": row.get("side", ""), "strategy_id": strat_id,
                    "reason": f"edge {edge} below 1.5% minimum (G-min-edge)",
                })
                continue
            kf = kelly_fraction(fair, row["our_odds_american"])
            stake = round(min(kf * 0.25, 0.02 if row["market"] != "PARLAY" else 0.01), 4)
            picks.append({
                "demo": demo,
                "game_id": row["game_id"],
                "market": row["market"],
                "side": row.get("side", ""),
                "our_line": our_line,
                "our_odds_american": row["our_odds_american"],
                "fair_prob": fair,
                "breakeven_prob": round(breakeven, 4) if breakeven else None,
                "edge": edge,
                "full_kelly": round(kf, 4),
                "stake_fraction_bankroll": stake,
                "strategy_id": strat_id,
                "strategy_status": s["status"],
                "gates": s["gates"],
                "gate_result": "DEMO — gates not backtested; pick is illustrative only" if demo
                               else gate_status(s),
                "market_line_context": market_line or "blank — no odds feed connected",
                "line_status": row.get("line_status", ""),
            })
        else:
            rejected.append({
                "game_id": row["game_id"], "market": row["market"],
                "side": row.get("side", ""), "strategy_id": strat_id or None,
                "reason": "no strategy attached; game lines are context only, not picks",
            })
    return picks, rejected


def main():
    ap = argparse.ArgumentParser(description="NBA2 slate pick generator")
    ap.add_argument("--demo", action="store_true", help="run in DEMO mode on synthetic data")
    ap.add_argument("--slate", default=None)
    ap.add_argument("--lines", default=None)
    ap.add_argument("--injuries", default=None)
    ap.add_argument("--corr", default=None)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "picks"))
    ap.add_argument("--today", default=None, help="ISO date; default = actual today (UTC)")
    args = ap.parse_args()

    demo = args.demo
    today = date.fromisoformat(args.today) if args.today else date.today()
    window = [str(today + timedelta(days=i)) for i in range(0, 4)]  # T+0 .. T+3 max

    with open(os.path.join(ROOT, "data", "strategies_lab.json"), encoding="utf-8") as f:
        catalog = json.load(f)
    strategies = catalog["strategies"]

    if demo:
        base = os.path.join(ROOT, "data", "demo")
        slate_p = os.path.join(base, "slate.demo.csv")
        lines_p = os.path.join(base, "lines.demo.csv")
        inj_p = os.path.join(base, "injuries.demo.csv")
        corr_p = os.path.join(base, "correlation.demo.csv")
    else:
        if not (args.slate and args.lines):
            sys.exit("Real mode requires --slate and --lines (and --injuries/--corr recommended).")
        slate_p, lines_p = args.slate, args.lines
        inj_p = args.injuries
        corr_p = args.corr

    slate = load_csv(slate_p)
    lines = load_csv(lines_p)

    # Enforce the 3-day maximum window on the slate itself.
    outside = [r["game_id"] for r in slate if r["date"] not in window]
    if outside:
        sys.exit(f"REFUSING: slate contains games outside the T+0..T+3 window {window}: {outside}")

    picks, rejected = build_picks(lines, strategies, window, demo)

    result = {
        "generated_utc_note": f"slate window {window[0]} .. {window[-1]} (max 3 days ahead)",
        "mode": "DEMO — synthetic data, not real picks" if demo else "REAL",
        "data_feed_status": "NOT CONNECTED — schedule/injuries/odds feeds must be wired before "
                            "real picks are possible (see docs/picks.html)",
        "active_strategies": [s["id"] for s in strategies if s["status"] == "active"],
        "real_picks_possible": bool([s for s in strategies if s["status"] == "active"]) and not demo,
        "picks": picks,
        "context_lines_not_picks": rejected,
        "staking_policy": catalog["global_rules"]["staking"],
        "portfolio_caps": catalog["global_rules"]["portfolio_caps"],
        "no_market_anchor_rule": catalog["global_rules"]["no_market_anchor"],
    }

    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, ("demo_picks.json" if demo else
                                       f"picks_{today.isoformat()}.json"))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    n = len(picks)
    print(f"[{'DEMO' if demo else 'REAL'}] window {window[0]}..{window[-1]}")
    print(f"  strategies active: {len(result['active_strategies'])} -> "
          f"{'real picks possible' if result['real_picks_possible'] else 'REAL PICKS BLOCKED (no gate-passed strategy)'}")
    print(f"  picks emitted: {n} (demo/illustrative only)" if demo else f"  picks emitted: {n}")
    for p in picks:
        print(f"    - {p['game_id']} {p['market']} {p['side']} {p['our_line']} @ {p['our_odds_american']} "
              f"fair={p['fair_prob']} edge={p['edge']} stake={p['stake_fraction_bankroll']:.2%} "
              f"[{p['strategy_id']} {p['gate_result']}]")
    print(f"  context-only lines (no strategy / below edge / blocked): {len(rejected)}")
    print(f"  written: {out_path}")


if __name__ == "__main__":
    main()
