"""Results, game flow and the settlement join — read from the committed result feed.

Three jobs, none of which the rest of ``nba2/v2`` could do before this module:

1. **Settlement from real scores.** ``data/raw/results_feed_*.json`` holds one row per official
   result. Joining it to the sealed prediction ledgers turns "we expect this to work" into "our
   lines have been scored, here is the error". Every row of the join is a comparison against an
   official final score with its own URL; nothing is imputed, and games with no final are listed as
   missing rather than skipped quietly.
2. **Game flow.** Quarter scores exist for the games this project read a game page or game book
   for. From them: the largest lead each side held, when the lead changed hands, and whether the
   result was decided after regulation. That is what an in-game strategy would need, and its
   absence on the other 183 games is reported as an absence.
3. **A rebuilt league roll.** The standings card, the games played, the home-win rate and the
   league scoring rate, all recomputed from the per-game rows. If a single final were transcribed
   wrong, the roll would stop matching the card the capture was checked against.

Determinism: nothing here reads a clock. The published artefacts carry the capture's own stamp, so
a rebuild reproduces the committed bytes exactly, which is what the parity workflow demands.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

from . import official as O

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data" / "v2"

FEED_PATH = sorted(glob.glob(str(RAW / "results_feed_*.json")))[-1]
FEED = json.loads(Path(FEED_PATH).read_text())
GAMES = sorted(FEED["games"], key=lambda g: (g["date"], g["game_id"]))
BY_ID = {g["game_id"]: g for g in GAMES}


# --------------------------------------------------------------------------- game flow
def game_flow(g: dict) -> dict:
    """Lead history from quarter scores, or an explicit statement that the data does not exist."""
    q = g.get("quarters")
    if not q:
        return {"available": False,
                 "reason": "no quarter strip was captured for this game; the feed stores the final "
                           "score only, and a quarter line is never reconstructed from the total",
                 "source": g.get("source_url", "")}
    aq, hq = q["away"], q["home"]
    aw = hw = 0
    lead_home, lead_away, changes, trail_then_lead = 0, 0, 0, None
    prev_sign = 0
    per_quarter = []
    for i, (a, h) in enumerate(zip(aq, hq), start=1):
        aw += a
        hw += h
        margin = hw - aw
        per_quarter.append({"quarter": i, "away": a, "home": h, "cum_margin_home": margin})
        lead_home = max(lead_home, margin)
        lead_away = min(lead_away, margin)
        sign = (margin > 0) - (margin < 0)
        if prev_sign and sign and sign != prev_sign:
            changes += 1
            if trail_then_lead is None and prev_sign < 0 < sign:
                trail_then_lead = i
        if sign:
            prev_sign = sign
    final_margin = g["home_pts"] - g["away_pts"]
    return {"available": True, "periods": len(aq), "per_quarter": per_quarter,
            "home_max_lead": lead_home, "away_max_lead": -lead_away,
            "lead_changes": changes,
            "overtime": len(aq) > 4 or final_margin == 0,
            "decided_in_last_period_margin": abs(per_quarter[-1]["cum_margin_home"]
                                                 - per_quarter[-2]["cum_margin_home"])
            if len(aq) >= 2 else None,
            "came_from_behind_to_win_quarter": trail_then_lead,
            "source_quarters": [g.get("quarter_source_game_page"), g.get("quarter_source_game_book")],
            }


# --------------------------------------------------------------------------- settlement join
def ledger_rows() -> list[dict]:
    """Every sealed prediction in the repository, joined to its official result."""
    rows = []
    for p in sorted(glob.glob(str(RAW / "ledger" / "sealed-*.json"))):
        doc = json.loads(Path(p).read_text())
        seal = doc.get("header", {})
        for pr in doc.get("predictions", []):
            g = BY_ID.get(pr["game_id"])
            row = {"ledger": Path(p).name, "seal_sha256": seal.get("sha256", ""),
                   "sealed_at": seal.get("sealed_at_utc", ""),
                   "game_id": pr["game_id"], "date": pr.get("date"),
                   "matchup": f"{pr.get('away')} @ {pr.get('home')}",
                   "our_spread_home": pr.get("our_spread_home"),
                   "our_total": pr.get("our_total"),
                   "p_home_win": pr.get("p_home_win"),
                   "tier": pr.get("tier"), "grade": pr.get("tier"),
                   "injury_blind": pr.get("injury_blind"),
                   "sealed_before_tip": pr.get("sealed_before_tip")}
            if g is None:
                row.update({"settled": False,
                            "why_not": "no official final score for this game id is committed"})
            else:
                actual_margin = g["home_pts"] - g["away_pts"]
                actual_total = g["home_pts"] + g["away_pts"]
                our_margin = (None if pr.get("our_spread_home") is None
                              else -pr["our_spread_home"])
                phw = pr.get("p_home_win")
                row.update({
                    "settled": True, "final": f"{g['away_pts']}-{g['home_pts']}",
                    "actual_margin_home": actual_margin, "actual_total": actual_total,
                    "our_margin_home": our_margin,
                    "spread_err": (None if our_margin is None
                                   else round(abs(our_margin - actual_margin), 2)),
                    "total_err": (None if pr.get("our_total") is None
                                  else round(abs(pr["our_total"] - actual_total), 2)),
                    "side_correct": (None if our_margin is None
                                     else (our_margin > 0) == (actual_margin > 0)),
                    "home_won": actual_margin > 0,
                    "prob_err": None if phw is None else round(abs(phw - (1.0 if actual_margin > 0 else 0.0)), 4),
                    "result_source": g.get("source_url", ""),
                })
            rows.append(row)
    return rows


def aggregate(rows: list[dict]) -> dict:
    settled = [r for r in rows if r.get("settled")]

    def _mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    sides = [r for r in settled if r.get("side_correct") is not None]
    probs = [(r["p_home_win"], 1.0 if r["home_won"] else 0.0) for r in settled
             if r.get("p_home_win") is not None]
    brier = (round(sum((p - y) ** 2 for p, y in probs) / len(probs), 4) if probs else None)
    # reliability, in three buckets, from the same rows
    buckets = []
    for lo, hi in ((0.0, 0.4), (0.4, 0.6), (0.6, 1.0)):
        sel = [(p, y) for p, y in probs if lo <= p < hi or (hi == 1.0 and p == 1.0)]
        if sel:
            buckets.append({"p_range": f"{lo:.1f}-{hi:.1f}", "n": len(sel),
                            "mean_p": round(sum(p for p, _ in sel) / len(sel), 4),
                            "actual": round(sum(y for _, y in sel) / len(sel), 4)})
    asof = O.AS_OF
    unset = [r for r in rows if not r.get("settled")]
    unplayed = sum(1 for r in unset if str(r.get("date")) > asof)
    missing = [r for r in unset if str(r.get("date")) <= asof]
    return {
        "predictions": len(rows), "settled": len(settled),
        "unsettled": len(unset),
        "unsettled_unplayed": unplayed,
        "unsettled_no_final_on_disk": [
            {"game_id": r["game_id"], "date": r.get("date"), "matchup": r["matchup"],
             "why_not": r.get("why_not")} for r in missing],
        "ledgers": sorted({r["ledger"] for r in rows}),
        "spread_mae": _mean([r.get("spread_err") for r in settled]),
        "total_mae": _mean([r.get("total_err") for r in settled]),
        "side_hit_rate": (round(sum(1 for r in sides if r["side_correct"]) / len(sides), 4)
                          if sides else None),
        "side_n": len(sides),
        "brier": brier, "brier_n": len(probs),
        "reliability_buckets": buckets,
        "mean_prob_error": _mean([r.get("prob_err") for r in settled]),
        "note": ("settled means an official final score with its own URL exists for that game id. "
                 "A projection with no result is listed as unsettled, never as a push, and no "
                 "cover figure is published because no market price exists to cover. "
                 f"{unplayed} of the {len(unset)} unsettled are simply unplayed (scheduled after "
                 f"{asof}); {len(missing)} sit on or before the capture date with no final on disk."),
    }


# --------------------------------------------------------------------------- league roll
def league_roll() -> dict:
    """The standings card, rebuilt from the per-game rows, with the differences spelled out."""
    rec: dict[str, dict] = {}
    for g in GAMES:
        for tri, pts, opp, side in ((g["away"], g["away_pts"], g["home_pts"], "road"),
                                    (g["home"], g["home_pts"], g["away_pts"], "home")):
            r = rec.setdefault(tri, {"gp": 0, "w": 0, "l": 0, "pf": 0, "pa": 0,
                                     "home_w": 0, "home_l": 0, "road_w": 0, "road_l": 0})
            r["gp"] += 1
            r["pf"] += pts
            r["pa"] += opp
            if pts > opp:
                r["w"] += 1
                r[f"{side}_w"] += 1
            else:
                r["l"] += 1
                r[f"{side}_l"] += 1
    diffs, rows = [], []
    for tri, (w, l, *_rest) in sorted(((t, (v[0], v[1]) + tuple(v[2:8]))
                                       for t, v in O.TEAMS.items())):
        r = rec.get(tri, {"gp": 0, "w": 0, "l": 0, "pf": 0, "pa": 0,
                          "home_w": 0, "home_l": 0, "road_w": 0, "road_l": 0})
        ok = (r["w"], r["l"]) == (w, l)
        rows.append({"tri": tri, "official": f"{w}-{l}", "rebuilt": f"{r['w']}-{r['l']}",
                     "gp_official": w + l, "gp_rebuilt": r["gp"],
                     "pts_per_game_rebuilt": round(r["pf"] / r["gp"], 1) if r["gp"] else None,
                     "allowed_per_game_rebuilt": round(r["pa"] / r["gp"], 1) if r["gp"] else None,
                     "match": ok})
        if not ok:
            diffs.append(tri)
    home_w = sum(r["home_w"] for r in rec.values())
    home_l = sum(r["home_l"] for r in rec.values())
    total_pts = sum(r["pf"] for r in rec.values())
    return {"games": len(GAMES), "teams": len(rec),
            "records_matching_the_standings_card": len(rows) - len(diffs),
            "records_of_30": len(rows), "mismatches": diffs,
            "home_wins": home_w, "home_losses": home_l,
            "home_win_rate": round(home_w / (home_w + home_l), 4) if (home_w + home_l) else None,
            "league_pts_per_team_game": round(total_pts / (2 * len(GAMES)), 3),
            "total_points": total_pts,
            "games_with_quarters": sum(1 for g in GAMES if g.get("quarters")),
            "games_without_quarters": sum(1 for g in GAMES if not g.get("quarters")),
            "rows": rows,
            "source_feed": Path(FEED_PATH).name,
            "source_urls": [FEED["sources"][k] for k in FEED["sources"]]}


def results_doc() -> dict:
    rows = ledger_rows()
    return {
        "generated_from_capture": O.AS_OF, "session": O.RETRIEVED_BY,
        "source_feed": Path(FEED_PATH).name, "feed_captured_utc": FEED.get("captured_utc"),
        "league": league_roll(),
        "settlement": aggregate(rows),
        "predictions": rows,
        "game_flow": {g["game_id"]: game_flow(g) for g in GAMES if g.get("quarters")}
                      | {"_coverage": {"with_quarters": sum(1 for g in GAMES if g.get("quarters")),
                                       "of_games": len(GAMES),
                                       "why": "quarter strips exist only for games this project read "
                                              "a game page or game book for; the feed's other rows "
                                              "carry the final score alone"}},
        "note": "rebuilt from data/raw/results_feed_*.json; no score in this file is estimated",
    }


def write_results(path: Path | None = None) -> Path:
    path = path or (DATA / "results.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results_doc(), indent=1) + "\n")
    return path


# --------------------------------------------------------------------------- settlement input
def write_finals_snapshot(path: Path | None = None) -> dict:
    """Emit the settlement-ready finals file from the result feed.

    ``nba2.pipeline.settle`` scores the sealed ledgers against ``data/raw/finals_all.json``, which
    is merged from every ``data/raw/finals_2*.json``. Before this session the merge had nine records
    and covered none of the ledger's games, so every gate reported zero measured — not because the
    games were unplayed but because the finals were never handed over. This writes the whole
    reconciled feed in the shape that merge expects, with each row keeping its own nba.com/game URL.
    """
    recs = [{"game_id": g["game_id"], "home_pts": g["home_pts"], "away_pts": g["away_pts"],
             "source": g.get("source_url", "")}
            for g in GAMES if g.get("status") == "final"]
    out = path or (RAW / f"finals_{O.AS_OF}_from_feed.json")
    out.write_text(json.dumps({
        "source": f"data/raw/{Path(FEED_PATH).name} (official finals, one URL per game)",
        "captured_utc": FEED.get("captured_utc"),
        "as_of": O.AS_OF,
        "meaning": "settlement input: every official final score this project has captured and "
                   "reconciled against the standings card, not only the newest day's games",
        "records": sorted(recs, key=lambda r: r["game_id"]),
        "note": "Generated by nba2.v2.results.write_finals_snapshot; never hand-edited. "
                "Merge with python -m nba2.pipeline.refresh --merge-finals, then score with "
                "python -m nba2.pipeline.settle.",
    }, indent=1) + "\n")
    return {"path": out.name, "records": len(recs),
            "already_there": len(recs) - len({r["game_id"] for r in json.loads(
                (RAW / "finals_all.json").read_text()).get("records", [])}
                & {r["game_id"] for r in recs}) if (RAW / "finals_all.json").exists() else len(recs)}


if __name__ == "__main__":  # pragma: no cover - inspector
    roll = league_roll()
    print(f"games {roll['games']}  records matching the card {roll['records_matching_the_standings_card']}"
          f"/{roll['records_of_30']}  mismatches {roll['mismatches']}")
    print(f"home win rate {roll['home_win_rate']}  league pts/team/game {roll['league_pts_per_team_game']}")
    agg = aggregate(ledger_rows())
    print({k: agg[k] for k in ("predictions", "settled", "unsettled", "spread_mae", "total_mae",
                               "side_hit_rate", "side_n", "brier", "brier_n", "mean_prob_error")})
    print("reliability:", agg["reliability_buckets"])
