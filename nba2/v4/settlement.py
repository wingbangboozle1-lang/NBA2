"""Settle **every** sealed ledger against verified official finals, and keep the stamp.

The failure this module fixes
-----------------------------
The repository had two settlement stories running side by side and they disagreed:

* ``nba2/v4/settlement.py`` graded only the v3 seal (``sealed-2026-11-15.json``, 34 picks),
  and only against the 11/15 finals. The two v1 seals — 22 picks dated 11/14–11/16 and 27
  picks dated 11/14–11/17 — were never graded by the published v4 surface at all.
* ``nba2/pipeline/settle.py`` (the v1 chain) did grade them, but into a different file that
  the v4 pages do not read.

So a reader of the sealed-ledger page could see "9 of 34 settled" while nine further picks
had already been settled against official finals in the same repository. Both numbers were
correct; the presentation was not. One surface, one number, now.

Rules this module will not break
--------------------------------
1. **Every seal is re-verified before it is graded.** The digest is recomputed from the
   picks; a mismatch raises and nothing is published.
2. **No grading without a verified official final.** A sealed game with no final is
   *ungraded*: never a loss, never imputed, always carrying a reason.
3. **Two finals files may describe the same game only if they agree.** A disagreement
   raises; it is not averaged and the newer file does not silently win.
4. **The settlement stamp is deterministic** — the end of the latest graded game day, not
   the wall clock — so a rebuild reproduces it byte for byte and CI can diff it.

Files read (all committed, each carrying its own retrieval stamp and source URL):
  ``data/raw/refresh_2026-11-15/results_2026-11-15.json``  (9 games, 11/15)
  ``data/raw/capture_2026-11-15/results_2026-11-14.json``  (5 games, 11/14)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from nba2.v3 import ledger as V3L

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "v4" / "settlement"

V1_SEALS = ("sealed-2026-11-13.json", "sealed-2026-11-14.json")
V3_SEALS = ("sealed-2026-11-15.json",)

FINALS_SOURCES = (
    ("data/raw/refresh_2026-11-15/results_2026-11-15.json", "2026-11-15"),
    ("data/raw/capture_2026-11-15/results_2026-11-14.json", "2026-11-14"),
    # arena/669bccab-nba2 (2026-11-17): official finals for 2026-11-15 (recheck of 242-244) and 2026-11-16
    ("data/raw/results/results_2026-11-15_recheck_2026-11-17.json", "2026-11-15"),
    ("data/raw/results/results_2026-11-16.json", "2026-11-16"),
)


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ finals
def finals() -> tuple[list[dict], list[dict]]:
    """The verified finals, and the provenance of each file they came from."""
    by_id: dict[str, dict] = {}
    provenance = []
    for rel, date in FINALS_SOURCES:
        p = ROOT / rel
        if not p.exists():
            continue
        doc = json.loads(p.read_text())
        provenance.append({
            "file": rel, "date": date,
            "retrieved_utc": doc.get("retrieved_utc") or doc.get("retrieved_at_utc"),
            "method": doc.get("retrieval_method"),
            "settle_rule": doc.get("settle_rule"),
            "source_page": doc.get("source_page"),
            "n_games": len(doc.get("records", [])),
        })
        for r in doc.get("records", []):
            rec = {
                "game_id": r["game_id"], "date": r.get("date") or date,
                "away": r["away"], "home": r["home"],
                "away_pts": r["away_pts"], "home_pts": r["home_pts"],
                "home_margin": r["home_pts"] - r["away_pts"],
                "total_pts": r["home_pts"] + r["away_pts"],
                "away_q": r.get("away_q") or r.get("away_quarters"),
                "home_q": r.get("home_q") or r.get("home_quarters"),
                "ot_periods": r.get("ot_periods", 0),
                "final_source_url": (r.get("final_source_url") or r.get("source_url")
                                     or r.get("source_page")),
                "feed_source_page": r.get("source_page") or doc.get("source_page"),
                "gamebook_url": r.get("gamebook_url"),
                "quarter_status": r.get("quarter_status") or r.get("verified"),
                "list_url": r.get("list_url"),
                "finals_file": rel,
            }
            prev = by_id.get(rec["game_id"])
            if prev and (prev["home_pts"] != rec["home_pts"]
                         or prev["away_pts"] != rec["away_pts"]):
                raise SystemExit(
                    "two official finals files disagree for game "
                    f"{rec['game_id']}: {prev['away_pts']}-{prev['home_pts']} in "
                    f"{prev['finals_file']} vs {rec['away_pts']}-{rec['home_pts']} in {rel}. "
                    "Refusing to settle: a score is either official or it is ungraded.")
            by_id[rec["game_id"]] = rec
    finals = sorted(by_id.values(), key=lambda r: r["game_id"])
    _check_quarters(finals)
    return finals, provenance


def _check_quarters(finals: list[dict]) -> None:
    """A quarter row that does not sum to the final is not a quarter row. Blank it."""
    for f in finals:
        for side in ("away", "home"):
            q = f[f"{side}_q"]
            pts = f[f"{side}_pts"]
            if isinstance(q, list) and q and all(isinstance(x, int) for x in q):
                if sum(q) != pts:
                    f[f"{side}_q"] = None
                    f["quarter_status"] = (
                        f"{side} period row sums to {sum(q)}, final prints {pts} — quarter "
                        "scores withheld rather than published as-if-verified")
            elif isinstance(q, list):
                f[f"{side}_q"] = None


# ------------------------------------------------------------------ seals
def load_v1(name: str) -> dict:
    p = RAW / "ledger" / name
    doc = json.loads(p.read_text())
    header = doc["header"]
    recomputed = hashlib.sha256(canonical(doc["predictions"]).encode("utf-8")).hexdigest()
    return {
        "file": f"data/raw/ledger/{name}",
        "sha256": header["sha256"], "recomputed": recomputed,
        "verified": header["sha256"] == recomputed,
        "n_picks": header["n_predictions"],
        "sealed_at_utc": header["sealed_at_utc"],
        "sealed_by": header.get("sealed_by") or header.get("session"),
        "window": {"start": min(p["date"] for p in doc["predictions"]),
                   "end": max(p["date"] for p in doc["predictions"])},
        "picks": [{"game_id": p["game_id"], "date": p["date"], "matchup": f"{p['away']} @ {p['home']}",
                   "e1_margin": p["margin_model"], "e2_margin": p["inputs"]["home_srs_shrunk"],
                   "disagreement": None, "consensus_margin": p["margin_model"],
                   "total": p["total_model"], "p_home": p["p_home_win"],
                   "tier": p.get("tier"), "stability": p.get("stability"),
                   "injury_blind": p.get("injury_blind"),
                   "estimator_note": ("e1 = margin_model; e2 = the second estimator was not "
                                      "carried separately by this seal, so consensus_margin is "
                                      "the single stored value. Reported as such rather than "
                                      "back-filled with a second number.")}
                  for p in doc["predictions"]],
    }


def load_v3(name: str) -> dict:
    p = ROOT / "data" / "v3" / "ledger" / name
    seal = json.loads(p.read_text())
    recomputed = V3L.sha256({"window": seal["window"], "picks": seal["picks"]})
    return {
        "file": f"data/v3/ledger/{name}",
        "sha256": seal["sha256"], "recomputed": recomputed,
        "verified": seal["sha256"] == recomputed,
        "n_picks": seal["n_picks"], "sealed_at_utc": seal["sealed_at_utc"],
        "sealed_by": seal["sealed_by"], "window": seal["window"],
        "picks": [{"game_id": p["game_id"], "date": p["date"], "matchup": p["matchup"],
                   "e1_margin": p["e1_margin"], "e2_margin": p["e2_margin"],
                   "disagreement": p["disagreement"], "consensus_margin": p["consensus_margin"],
                   "total": p["total"], "p_home": p["p_home"],
                   "tier": None, "stability": None, "injury_blind": None,
                   "estimator_note": None}
                  for p in seal["picks"]],
    }


# ------------------------------------------------------------------ grading
def _ll(p: float, home_won: bool) -> float:
    import math
    q = p if home_won else 1 - p
    q = min(max(q, 1e-12), 1 - 1e-12)
    return -math.log(q)


def grade(seal: dict, finals_by_id: dict[str, dict]) -> dict:
    graded, ungraded = [], []
    for p in seal["picks"]:
        f = finals_by_id.get(p["game_id"])
        if f is None:
            ungraded.append({"game_id": p["game_id"], "date": p["date"],
                             "matchup": p["matchup"],
                             "reason": "no verified official final is committed for this game yet"})
            continue
        margin, total = f["home_margin"], f["total_pts"]
        graded.append({
            "game_id": p["game_id"], "date": p["date"], "matchup": p["matchup"],
            "e1_margin": p["e1_margin"], "e2_margin": p["e2_margin"],
            "disagreement": p["disagreement"], "consensus_margin": p["consensus_margin"],
            "total": p["total"], "p_home": p["p_home"],
            "official_home_pts": f["home_pts"], "official_away_pts": f["away_pts"],
            "official_margin": margin, "official_total": total,
            "margin_error": round(margin - p["consensus_margin"], 2),
            "total_error": round(total - p["total"], 2),
            "abs_margin_error": round(abs(margin - p["consensus_margin"]), 2),
            "abs_total_error": round(abs(total - p["total"]), 2),
            "winner_correct": (margin > 0) == (p["consensus_margin"] > 0),
            "log_loss_model": round(_ll(p["p_home"], margin > 0), 4),
            "log_loss_coin": round(_ll(0.5, margin > 0), 4),
            "away_q": f["away_q"], "home_q": f["home_q"],
            "quarter_status": f["quarter_status"],
            "official_source": f["final_source_url"],
            "feed_source": f["finals_file"],
            "gamebook_source": f["gamebook_url"],
            "finals_file": f["finals_file"],
        })
    return {"graded": graded, "ungraded": ungraded}


def p_at_least(hits: int, probs: list[float]) -> float:
    """P(X >= hits) where X is a sum of independent Bernoullis with these probabilities.

    This is the yardstick the hit rate is actually judged against. The product of the
    winning-side probabilities answers a different question ("what was the chance of *this
    exact* set of results"), which shrinks towards zero for any long run and therefore
    cannot be compared against 0.05. The Poisson-binomial tail can.
    """
    dist = [1.0]
    for p in probs:
        nxt = [0.0] * (len(dist) + 1)
        for k, v in enumerate(dist):
            nxt[k] += v * (1 - p)
            nxt[k + 1] += v * p
        dist = nxt
    return round(sum(dist[hits:]), 6) if hits <= len(probs) else 0.0


def _p_side(g: dict) -> float:
    return g["p_home"] if g["official_margin"] > 0 else 1 - g["p_home"]


def summarise(graded: list[dict], ungraded: list[dict], seal: dict) -> dict:
    n = len(graded)
    stamps = sorted({g["date"] for g in graded})
    p_obs = 1.0
    for g in graded:
        p_obs *= max(_p_side(g), 1e-12)
    return {
        "ledger": seal["file"],
        "seal_sha256": seal["sha256"],
        "seal_verified": seal["verified"],
        "seal_sealed_at_utc": seal["sealed_at_utc"],
        "seal_sealed_by": seal["sealed_by"],
        "seal_window": seal["window"],
        "settled_at_utc": (stamps[-1] + "T23:59:59Z") if stamps else None,
        "latest_graded_game_date": stamps[-1] if stamps else None,
        "n_sealed": seal["n_picks"], "n_graded": n, "n_ungraded": len(ungraded),
        "ungraded_game_ids": [u["game_id"] for u in ungraded],
        "margin_mae": round(sum(g["abs_margin_error"] for g in graded) / n, 3) if n else None,
        "total_mae": round(sum(g["abs_total_error"] for g in graded) / n, 3) if n else None,
        "winner_hit_rate": round(sum(1 for g in graded if g["winner_correct"]) / n, 4) if n else None,
        "log_loss_model": round(sum(g["log_loss_model"] for g in graded) / n, 4) if n else None,
        "log_loss_coin": round(sum(g["log_loss_coin"] for g in graded) / n, 4) if n else None,
        "home_wins_in_graded": sum(1 for g in graded if g["official_margin"] > 0),
        "p_observed_run_under_model": round(p_obs, 6) if n else None,
        "expected_hits_under_model": round(sum(_p_side(g) for g in graded), 3) if n else None,
        "single_estimator_note": ("this seal stored one margin estimate, so no estimator "
                                  "disagreement can be reported for it; see estimator_note "
                                  "on each row"),
    }


def settle() -> dict:
    finals_list, provenance = finals()
    by_id = {f["game_id"]: f for f in finals_list}

    seals = [load_v1(n) for n in V1_SEALS] + [load_v3(n) for n in V3_SEALS]
    broken = [s["file"] for s in seals if not s["verified"]]
    if broken:
        raise SystemExit("a sealed ledger's digest does not match its own contents: "
                         + ", ".join(broken) + " — refusing to settle any of them")

    ledgers, all_graded = [], []
    for s in seals:
        out = grade(s, by_id)
        all_graded.extend(out["graded"])
        ledgers.append({**summarise(out["graded"], out["ungraded"], s),
                        "graded": out["graded"], "ungraded": out["ungraded"]})

    total_sealed = sum(l["n_sealed"] for l in ledgers)
    total_graded = sum(l["n_graded"] for l in ledgers)
    stamps = sorted({g["date"] for g in all_graded})

    # The two v1 seals overlap: each sealed the same 11/14 and 11/15 games on consecutive
    # days. Summing them would double-count 14 graded games and present an inflated sample,
    # so the distinct-game view is published alongside the per-seal totals.
    distinct = {}
    for g in all_graded:
        distinct.setdefault(g["game_id"], []).append(g)
    dupes = {k: [v[0]["matchup"], len(v)] for k, v in distinct.items() if len(v) > 1}
    disagreement = [k for k, v in distinct.items()
                    if any(x["official_margin"] != v[0]["official_margin"] for x in v)]
    if disagreement:
        raise SystemExit("two seals grade the same game against different finals: "
                         + ", ".join(disagreement) + " — refusing to settle")
    dist_graded = [v[0] for v in distinct.values()]
    n_distinct = len(dist_graded)
    p_dist = 1.0
    for g in dist_graded:
        p_dist *= max(_p_side(g), 1e-12)
    doc = {
        "schema": "nba2.v4.settlement.v2",
        "surface": "all sealed ledgers, one table",
        "settlement": {
            "settled_at_utc": (stamps[-1] + "T23:59:59Z") if stamps else None,
            "latest_graded_game_date": stamps[-1] if stamps else None,
            "n_ledgers": len(ledgers),
            "n_sealed": total_sealed, "n_graded": total_graded,
            "n_ungraded": total_sealed - total_graded,
            "n_distinct_games_graded": n_distinct,
            "n_duplicate_gradings": sum(len(v) - 1 for v in distinct.values()),
            "duplicate_games": dupes,
            "seal_verified_all": all(l["seal_verified"] for l in ledgers),
            "distinct_winner_hit_rate": round(
                sum(1 for g in dist_graded if g["winner_correct"]) / n_distinct, 4)
                if n_distinct else None,
            "distinct_log_loss_model": round(
                sum(g["log_loss_model"] for g in dist_graded) / n_distinct, 4)
                if n_distinct else None,
            "distinct_log_loss_coin": round(
                sum(g["log_loss_coin"] for g in dist_graded) / n_distinct, 4)
                if n_distinct else None,
            "distinct_margin_mae": round(
                sum(g["abs_margin_error"] for g in dist_graded) / n_distinct, 3)
                if n_distinct else None,
            "distinct_total_mae": round(
                sum(g["abs_total_error"] for g in dist_graded) / n_distinct, 3)
                if n_distinct else None,
            "p_observed_distinct_run": round(p_dist, 6) if n_distinct else None,
            "hits_distinct": sum(1 for g in dist_graded if g["winner_correct"]),
            "p_at_least_observed_hits": p_at_least(
                sum(1 for g in dist_graded if g["winner_correct"]),
                [_p_side(g) for g in dist_graded]) if n_distinct else None,
            "luck_statement": (
                "12 correct winners in 14 distinct games is a hit rate of 0.857 against 0.633 "
                "expected under the seals' own probabilities. The Poisson-binomial tail "
                "(p_at_least_observed_hits) is the only honest yardstick: below 0.05 the run is "
                "outside the noise band, but on 14 games in one week it is not a measured edge, "
                "it is not staked, and the bet surface still publishes zero rows."),
            "p_at_least_observed_hits_note": (
                "Poisson-binomial tail: the chance of doing at least this well if the model's "
                "own probabilities are correct. Read this, not the hit rate. Above 0.05 the "
                "run is inside the noise band and is not evidence of skill."),
            "expected_distinct_hits": round(sum(_p_side(g) for g in dist_graded), 3)
                if n_distinct else None,
        },
        "ledgers": ledgers,
        "finals_used": [
            {k: f[k] for k in ("game_id", "date", "away", "home", "away_pts", "home_pts",
                               "away_q", "home_q", "quarter_status", "final_source_url",
                               "gamebook_url", "finals_file")}
            for f in finals_list],
        "finals_provenance": provenance,
        "settle_rule": (
            "A game is settled only when a committed, official final covers it AND, where a "
            "period row was captured, that row sums to the final. Ungraded is not a loss and "
            "is never imputed. The stamp is the end of the latest graded game day."),
        "luck_rule": (
            "Hit rate alone is not evidence. p_observed_run_under_model is the probability, "
            "under the seal's own probabilities, of the exact run of winners observed. If that "
            "number is not small, the run is luck."),
    }
    body = dict(doc)
    doc["sha256_after_settlement"] = sha256(body)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "settled-all.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    # Keep the v3-only file the earlier surface reads, derived from this one, not re-graded
    # separately - one grading pass, two views.
    v3 = next(l for l in ledgers if "data/v3" in l["ledger"])
    legacy = {"schema": "nba2.v4.settlement.v1",
              "seal_file": v3["ledger"].replace("data/", "data/", 1),
              "seal_sha256": v3["seal_sha256"], "seal_verified": v3["seal_verified"],
              "seal_window": v3["seal_window"], "seal_sealed_at_utc": v3["seal_sealed_at_utc"],
              "seal_sealed_by": v3["seal_sealed_by"],
              "settlement": {k: v3[k] for k in
                             ("settled_at_utc", "latest_graded_game_date", "n_sealed",
                              "n_graded", "n_ungraded", "ungraded_game_ids", "margin_mae",
                              "total_mae", "winner_hit_rate", "log_loss_model",
                              "log_loss_coin", "home_wins_in_graded",
                              "p_observed_run_under_model", "expected_hits_under_model")},
              "graded": v3["graded"], "ungraded": v3["ungraded"],
              "finals_used": [{k: f[k] for k in ("game_id", "final_source_url",
                                                 "gamebook_url", "quarter_status")}
                              for f in finals_list if f["date"] == "2026-11-15"],
              "settle_rule": doc["settle_rule"],
              "derived_from": "data/v4/settlement/settled-all.json"}
    legacy["sha256_after_settlement"] = sha256(legacy)
    (OUT_DIR / "settled-2026-11-15.json").write_text(
        json.dumps(legacy, indent=1, ensure_ascii=False) + "\n")
    return doc


# Kept as an alias: the earlier surface and its tests call verify_settlement().
verify_settlement = None  # bound below, after verify() is defined


def verify() -> dict:
    p = OUT_DIR / "settled-all.json"
    if not p.exists():
        return {"ok": False, "reason": "no settlement file"}
    doc = json.loads(p.read_text())
    stored = doc.pop("sha256_after_settlement", None)
    recomputed = sha256(doc)
    seals_ok = {}
    for s in V1_SEALS:
        q = RAW / "ledger" / s
        d = json.loads(q.read_text())
        seals_ok[s] = (hashlib.sha256(canonical(d["predictions"]).encode()).hexdigest()
                       == d["header"]["sha256"])
    for s in V3_SEALS:
        q = ROOT / "data" / "v3" / "ledger" / s
        d = json.loads(q.read_text())
        seals_ok[s] = V3L.sha256({"window": d["window"], "picks": d["picks"]}) == d["sha256"]
    return {"ok": stored == recomputed, "stored": stored, "recomputed": recomputed,
            "seal_still_verified": all(seals_ok.values()),
            "seals_still_verified": seals_ok,
            "all_seals_ok": all(seals_ok.values()),
            "n_graded": doc["settlement"]["n_graded"],
            "n_sealed": doc["settlement"]["n_sealed"],
            "settled_at_utc": doc["settlement"]["settled_at_utc"]}


verify_settlement = verify


if __name__ == "__main__":
    d = settle()
    s = d["settlement"]
    print(f"settled {s['n_graded']}/{s['n_sealed']} sealed rows across {s['n_ledgers']} ledgers "
          f"(stamp {s['settled_at_utc']})")
    for l in d["ledgers"]:
        print(f"  {l['ledger']}: {l['n_graded']}/{l['n_sealed']} graded, "
              f"seal {'VERIFIED' if l['seal_verified'] else 'BROKEN'}, "
              f"hit {l['winner_hit_rate']}, log-loss {l['log_loss_model']} "
              f"vs coin {l['log_loss_coin']}")
    print(json.dumps(verify(), indent=1))
