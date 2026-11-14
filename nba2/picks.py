"""
picks.py — orchestrates line origination, strategy signal generation, gate
evaluation, and writes all output JSON consumed by the site.

Run via:  python3 nba2/generate.py
"""

import json
import os

from model import originate_line, favorite_label, STRONG_MARGIN
from strategies import (
    STRATEGIES, evaluate_strategy, leaderboard,
    MIN_WIN_PROB, MIN_SPREAD_EDGE, MIN_TOTAL_EDGE,
)
from correlations import analyze_team_factors, parlay_correlation_gate, luck_vs_skill_note, PARLAY_CORR_ASSUMPTION
from injuries import game_flow, summarize_team, impact_points

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def write(name, obj):
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def s2_selection(line):
    """The S2 selection string for one line, and the model win prob of the named side.

    Convention (F-025, fixed 2026-11-14): `predicted_margin` is the expected HOME margin
    and `originated_spread` is the home-perspective handicap (negative = home favored).
    A selection names the model's favorite carrying that side's OWN line — the favorite
    gives points, so the number is always negative: "MIA -6.5" or "NYK -2.5", never
    "MIA +6.5" (that is the dog) and never a flipped sign on the right side.
    """
    margin = line["predicted_margin"]
    if margin > 0:
        # home favorite: home's own line is the negation of the home-perspective spread
        return f"{line['home']} {-line['originated_spread']:+.1f}", line["home_win_prob"]
    # away favorite: the home-perspective spread is already the away side's line
    return f"{line['away']} {line['originated_spread']:+.1f}", line["away_win_prob"]


def main():
    schedule = load("schedule.json")
    records_doc = load("records.json")
    injuries_doc = load("injuries.json")

    records = {t["team"]: t for t in records_doc["teams"]}

    # Build injuries_by_game (game-specific; the official report lists each
    # player's status for a PARTICULAR game, so we must not carry a team's
    # injuries across different games).
    injuries_by_game = {}
    for g in injuries_doc["games"]:
        injuries_by_game[g["game_id"]] = g["injuries"]

    games = schedule["games"]
    schedule_source = schedule["source"]

    # --- Originate lines for every game ------------------------------------
    lines = []
    for g in games:
        gid = g["game_id"]
        all_inj = injuries_by_game.get(gid, [])
        away_inj = [i for i in all_inj if i["team"] == g["away"]]
        home_inj = [i for i in all_inj if i["team"] == g["home"]]
        line = originate_line(g["away"], g["home"], away_inj, home_inj, records)
        line.update({
            "date": g["date"], "time_et": g["time_et"],
            "away_name": g["away_name"], "home_name": g["home_name"],
            "group": g["group"], "venue": g["venue"], "city": g["city"],
            "game_id": gid, "source": g["source"],
        })
        line["favorite"] = favorite_label(line)
        lines.append(line)

    # --- Generate signals per strategy ------------------------------------
    signals_by_strategy = {s["id"]: [] for s in STRATEGIES}

    # S1 Margin Favorite (single)
    for line in lines:
        if line["home_win_prob"] >= MIN_WIN_PROB:
            signals_by_strategy["S1_MarginFavorite"].append({
                "strategy_id": "S1_MarginFavorite", "game_id": line["game_id"],
                "game": f"{line['away']} @ {line['home']}", "source": line["source"],
                "data_class": line["data_class"], "bet_type": "single",
                "selection": f"{line['home']} ML", "model_win_prob": line["home_win_prob"],
                "leg": {"game_id": line["game_id"], "selection": f"{line['home']} ML"},
            })
        elif line["away_win_prob"] >= MIN_WIN_PROB:
            signals_by_strategy["S1_MarginFavorite"].append({
                "strategy_id": "S1_MarginFavorite", "game_id": line["game_id"],
                "game": f"{line['away']} @ {line['home']}", "source": line["source"],
                "data_class": line["data_class"], "bet_type": "single",
                "selection": f"{line['away']} ML", "model_win_prob": line["away_win_prob"],
                "leg": {"game_id": line["game_id"], "selection": f"{line['away']} ML"},
            })

    # S2 Spread Value (single)
    # Bet the model's favorite to cover when the predicted margin is strong
    # (>= STRONG_MARGIN). The edge is the model's expected cover cushion
    # (predicted margin), i.e. how far the favorite is expected to win by.
    for line in lines:
        margin = line["predicted_margin"]
        if abs(margin) >= STRONG_MARGIN:
            sel, prob = s2_selection(line)
            signals_by_strategy["S2_SpreadValue"].append({
                "strategy_id": "S2_SpreadValue", "game_id": line["game_id"],
                "game": f"{line['away']} @ {line['home']}", "source": line["source"],
                "data_class": line["data_class"], "bet_type": "single",
                "selection": sel, "model_win_prob": prob, "spread_edge": round(abs(margin), 2),
                "leg": {"game_id": line["game_id"], "selection": sel},
            })

    # S3 Totals (single)
    for line in lines:
        edge = line["predicted_total"] - line["originated_total_line"]
        if abs(edge) >= MIN_TOTAL_EDGE:
            sel = "Over" if edge > 0 else "Under"
            signals_by_strategy["S3_Totals"].append({
                "strategy_id": "S3_Totals", "game_id": line["game_id"],
                "game": f"{line['away']} @ {line['home']}", "source": line["source"],
                "data_class": line["data_class"], "bet_type": "single",
                "selection": f"{sel} {line['originated_total_line']}",
                "model_win_prob": None, "total_edge": round(edge, 2),
                "leg": {"game_id": line["game_id"], "selection": f"{sel} {line['originated_total_line']}"},
            })

    # S4 Lean Parlay: strongest 2-3 single signals from DISTINCT games.
    # Rank S1/S2/S3 single signals by model_win_prob, pick top legs from distinct games.
    pool = []
    for sid in ["S1_MarginFavorite", "S2_SpreadValue", "S3_Totals"]:
        for s in signals_by_strategy[sid]:
            p = s.get("model_win_prob") or 0.55
            pool.append((p, s))
    pool.sort(key=lambda x: x[0], reverse=True)
    parlay_legs = []
    used_games = set()
    for p, s in pool:
        if s["game_id"] in used_games:
            continue
        used_games.add(s["game_id"])
        parlay_legs.append(s)
        if len(parlay_legs) == 3:
            break
    if parlay_legs:
        ok, note, assumed = parlay_correlation_gate(parlay_legs)
        sel = " + ".join(leg["leg"]["selection"] for leg in parlay_legs)
        # Carry each leg's edge info so the parlay G2 gate can validate the legs.
        legs = [{"game_id": leg["game_id"], "selection": leg["leg"]["selection"],
                 "model_win_prob": leg.get("model_win_prob"),
                 "spread_edge": leg.get("spread_edge"), "total_edge": leg.get("total_edge")}
                for leg in parlay_legs]
        signals_by_strategy["S4_LeanParlay"].append({
            "strategy_id": "S4_LeanParlay", "game_id": "; ".join(sorted({l["game_id"] for l in parlay_legs})),
            "game": "Parlay (" + ", ".join(f"{l['leg']['game_id']}" for l in parlay_legs) + ")",
            "source": schedule_source, "data_class": "Model (originated)",
            "bet_type": "parlay", "selection": sel, "model_win_prob": None,
            "correlation_gate": ok, "correlation_note": note, "assumed_corr": assumed,
            "legs": legs,
            "leg": {"game_id": parlay_legs[0]["game_id"], "selection": sel},
        })

    # S5 Player Prop Combo: framework only (no verified player-level prop data).
    signals_by_strategy["S5_PlayerPropCombo"] = []

    # --- Evaluate strategies + leaderboard -------------------------------
    records_eval = []
    for s in STRATEGIES:
        sigs = signals_by_strategy[s["id"]]
        rec = evaluate_strategy(s, sigs, tracked_observations=0)
        records_eval.append(rec)
    ranked = leaderboard(records_eval)

    # --- Correlations ------------------------------------------------------
    corr_rows = analyze_team_factors(records_doc["teams"])

    # --- Game flow ---------------------------------------------------------
    gameflow = []
    for g in games:
        gid = g["game_id"]
        away_inj = injuries_by_game.get(gid, [])
        # Injuries are listed per team within a game block; filter by team.
        all_inj = injuries_by_game.get(gid, [])
        away_inj = [i for i in all_inj if i["team"] == g["away"]]
        home_inj = [i for i in all_inj if i["team"] == g["home"]]
        flow = game_flow(g["away"], g["home"], records[g["away"]], records[g["home"]], away_inj, home_inj)
        flow.update({"date": g["date"], "time_et": g["time_et"], "matchup": f"{g['away']}@{g['home']}",
                     "game_id": gid, "source": g["source"]})
        gameflow.append(flow)

    # --- Flagged / unverified --------------------------------------------
    flagged = build_flagged(lines, corr_rows, records_eval, injuries_doc, records_doc)

    # --- Write outputs -----------------------------------------------------
    write("picks.json", {
        "description": "Generated picks for the 3-day slate (Nov 13-15, 2026), organized by strategy. All picks are MODEL-originated; underlying game/injury data verified to NBA.com.",
        "generated_utc": "2026-11-13T22:30:00Z",
        "slate_source": schedule_source,
        "strategies": [
            {"id": s["id"], "name": s["name"], "type": s["type"], "description": s["description"],
             "signals": signals_by_strategy[s["id"]]}
            for s in STRATEGIES
        ],
        "lines": lines,
    })

    write("strategies.json", {
        "description": "Strategy validation gates and leaderboard.",
        "gates": __import__("strategies").GATES,
        "parlay_correlation_assumption": PARLAY_CORR_ASSUMPTION,
        "luck_vs_skill": luck_vs_skill_note(),
        "records": ranked,
    })

    write("correlations.json", {
        "description": "Correlation analysis. Values marked 'pending' require a historical dataset (n insufficient in current snapshot).",
        "rows": corr_rows,
        "parlay_correlation_assumption": PARLAY_CORR_ASSUMPTION,
        "luck_vs_skill": luck_vs_skill_note(),
    })

    write("gameflow.json", {
        "description": "Injury-driven game-flow analysis. Impact/flow are model estimates; statuses verified to NBA.com.",
        "rows": gameflow,
    })

    write("flagged.json", flagged)

    print(f"Generated {len(lines)} lines, {sum(len(v) for v in signals_by_strategy.values())} signals.")
    print(f"Strategies: {len(ranked)} evaluated. Flagged items: {len(flagged['items'])}.")


def build_flagged(lines, corr_rows, records_eval, injuries_doc, records_doc):
    items = []

    # 1. Totals using baseline only (unverified league-average baseline) — consolidated.
    baseline_games = [f"{l['away']} @ {l['home']}" for l in lines if l.get("total_is_baseline_only")]
    if baseline_games:
        items.append({
            "item": f"Predicted totals use an unverified league-average baseline for {len(baseline_games)} of 23 games",
            "detail": "Predicted totals equal the model baseline (224.0) with no verified pace adjustment because verified PPG/OPPG were not available for both teams in those games. Game-level detail is on the Picks page; each row there links to its official NBA.com game page.",
            "value": "unverified baseline (224.0)",
            "source": "https://www.nba.com/stats",
            "severity": "medium",
        })

    # 2. Injury impact weights are model estimates (not verified importance).
    items.append({
        "item": "Injury impact weights (Out/Doubtful/Questionable -> points)",
        "detail": "Per-player impact weights are transparent model estimates of rotation-minute/production impact, not verified importance values (which require player-level usage/box-score data).",
        "value": "model estimate (unverified importance)",
        "source": injuries_doc["source"],
        "severity": "medium",
    })

    # 3. Player prop values unavailable (no verified player-level data).
    items.append({
        "item": "Player prop values (S5_PlayerPropCombo)",
        "detail": "No verified player-level production data available; prop values are intentionally left blank/unverified rather than inferred.",
        "value": "blank / unverified",
        "source": "https://www.nba.com/stats",
        "severity": "high",
    })

    # 4. PPG/OPPG unverified for 28 of 30 teams.
    unverified_ppg = [t["team"] for t in records_doc["teams"] if t["ppg"] is None]
    items.append({
        "item": f"PPG/OPPG unverified for {len(unverified_ppg)} of 30 teams",
        "detail": "PPG/OPPG verified only for TOR and WAS (official team pages). Left blank (unverified) for all other teams; never inferred.",
        "value": f"{len(unverified_ppg)} teams unverified",
        "source": "https://www.nba.com/stats",
        "severity": "medium",
    })

    # 5. Historical correlations pending.
    for row in corr_rows:
        if row["value"] == "pending":
            items.append({
                "item": f"Correlation {row['factor_a']} vs {row['factor_b']}",
                "detail": row["note"],
                "value": "pending historical dataset",
                "source": "https://www.nba.com/stats",
                "severity": "low",
            })

    # 6. Injury reports for 11/14 & 11/15 not yet submitted.
    items.append({
        "item": "Injury reports for 11/14 and 11/15 games not yet submitted",
        "detail": "The league's official injury report lists these games as 'NOT YET SUBMITTED'. Injury data for those games will be populated when the league publishes updated reports.",
        "value": "not yet submitted",
        "source": injuries_doc["source"],
        "severity": "low",
    })

    # 7. Strategies are provisional (no tracked results yet).
    provisional = [r["name"] for r in records_eval if r["status"] == "provisional"]
    if provisional:
        items.append({
            "item": "All strategies are provisional (no tracked results)",
            "detail": "The leaderboard rewards top-performing strategies, but no games have been tracked to completion yet. Strategies remain provisional until results are recorded.",
            "value": "provisional",
            "source": "https://www.nba.com/schedule",
            "severity": "low",
        })

    return {"description": "Items flagged for manual review. Each links to the official source where applicable; unverified values are left blank and never inferred.", "items": items}


if __name__ == "__main__":
    main()
