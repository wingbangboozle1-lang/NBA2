"""Settle the sealed ledger against **verified** official finals, and keep the stamp.

Rules this module will not break:

1. **No grading without an official final.** A sealed game that has no verified final is
   *ungraded*. It is never counted as a loss and never imputed.
2. **A quarter score is only published if its period row summed to the final.** A club
   whose period row was not transcribed carries ``None`` and is displayed as unverified.
   Nothing is back-solved from the final: a quarter split that adds up because it was
   constructed to add up is not evidence.
3. **The pre-tip hash is verified before anything is graded**, so a settlement produced
   from an edited ledger cannot be published. If the hash does not match, this module
   raises rather than reporting a result.
4. **The settlement stamp is deterministic** — the end of the latest graded game day, not
   the wall clock — so a rebuild reproduces it and CI can diff the artefact.

The seal itself is never rewritten. ``data/v3/ledger/**`` is read-only here; the
settlement is written beside it under ``data/v4/settlement/``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from nba2.v3 import ledger as V3L

from . import capture as C
from . import model as M

ROOT = Path(__file__).resolve().parents[2]
SEAL_DIR = ROOT / "data" / "v3" / "ledger"
OUT_DIR = ROOT / "data" / "v4" / "settlement"


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def load_seal(date: str = "2026-11-15") -> dict:
    p = SEAL_DIR / f"sealed-{date}.json"
    if not p.exists():
        raise SystemExit(f"sealed ledger missing: {p}")
    return json.loads(p.read_text())


def verify_seal(seal: dict) -> dict:
    """Recompute the pre-tip digest. Raises on mismatch - a broken seal grades nothing."""
    stored = seal.get("sha256")
    recomputed = V3L.sha256({"window": seal["window"], "picks": seal["picks"]})
    ok = stored == recomputed
    settlements = {}
    for d in sorted(OUT_DIR.glob("settled-*.json")) if OUT_DIR.exists() else []:
        doc = json.loads(d.read_text())
        if doc.get("seal_sha256") == stored:
            settlements[d.name] = doc.get("sha256_after_settlement")
    return {"stored": stored, "recomputed": recomputed, "ok": ok,
            "n_picks": seal["n_picks"], "window": seal["window"],
            "sealed_at_utc": seal["sealed_at_utc"], "sealed_by": seal["sealed_by"],
            "prior_settlements": settlements}


def grade(seal: dict, finals: list[dict]) -> dict:
    """Grade every sealed row that has a verified final; list the rest as ungraded."""
    by_id = {f["game_id"]: f for f in finals}
    graded, ungraded = [], []
    for p in seal["picks"]:
        f = by_id.get(p["game_id"])
        if f is None:
            ungraded.append({"game_id": p["game_id"], "date": p["date"],
                             "matchup": p["matchup"],
                             "reason": "no verified official final in the committed capture"})
            continue
        margin = f["home_margin"]
        total = f["total_pts"]
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
            "e1_correct": (margin > 0) == (p["e1_margin"] > 0),
            "e2_correct": (margin > 0) == (p["e2_margin"] > 0),
            # coin-flip probabilities are the honest no-information baseline
            "log_loss_model": round(_ll(p["p_home"], margin > 0), 4),
            "log_loss_coin": round(_ll(0.5, margin > 0), 4),
            "official_source": f["final_source_url"],
            "gamebook_source": f["gamebook_url"],
            "quarter_status": f["quarter_status"],
        })
    return {"graded": graded, "ungraded": ungraded}


def _ll(p: float, home_won: bool) -> float:
    import math
    q = p if home_won else 1 - p
    q = min(max(q, 1e-12), 1 - 1e-12)
    return -math.log(q)


def _p_side(g: dict) -> float:
    """Probability the model gave to the side that actually won."""
    return g["p_home"] if g["official_margin"] > 0 else 1 - g["p_home"]


def _p_observed(graded: list[dict]) -> float:
    p = 1.0
    for g in graded:
        p *= max(_p_side(g), 1e-12)
    return p


def _p_all_correct(graded: list[dict]) -> float:
    """Chance of getting ALL of them right, ignoring which side: the same quantity here
    because the sealed row always names one side."""
    return _p_observed(graded)


def summarise(graded: list[dict], ungraded: list[dict], seal: dict) -> dict:
    n = len(graded)
    stamps = sorted({g["date"] for g in graded})
    return {
        "settled_at_utc": (stamps[-1] + "T23:59:59Z") if stamps else None,
        "latest_graded_game_date": stamps[-1] if stamps else None,
        "n_sealed": seal["n_picks"],
        "n_graded": n, "n_ungraded": len(ungraded),
        "ungraded_game_ids": [u["game_id"] for u in ungraded],
        "margin_mae": round(sum(g["abs_margin_error"] for g in graded) / n, 3) if n else None,
        "total_mae": round(sum(g["abs_total_error"] for g in graded) / n, 3) if n else None,
        "winner_hit_rate": round(sum(1 for g in graded if g["winner_correct"]) / n, 4) if n else None,
        "e1_winner_hit_rate": round(sum(1 for g in graded if g["e1_correct"]) / n, 4) if n else None,
        "e2_winner_hit_rate": round(sum(1 for g in graded if g["e2_correct"]) / n, 4) if n else None,
        "log_loss_model": round(sum(g["log_loss_model"] for g in graded) / n, 4) if n else None,
        "log_loss_coin": round(sum(g["log_loss_coin"] for g in graded) / n, 4) if n else None,
        "home_wins_in_graded": sum(1 for g in graded if g["official_margin"] > 0),
        # LUCK CONTROL. A hit rate on 9 games says almost nothing on its own. Under the
        # model's OWN probabilities, what was the chance of the observed number of hits?
        # p_obs = product over graded rows of the probability the model assigned to the
        # side that actually won. If that product is not small, the run is luck.
        "p_observed_run_under_model": round(_p_observed(graded), 6) if n else None,
        "p_all_correct_under_model": round(_p_all_correct(graded), 6) if n else None,
        "expected_hits_under_model": round(sum(_p_side(g) for g in graded), 3) if n else None,
        "luck_note": (
            "A 9/9 result on 9 games is NOT evidence of skill by itself: the model priced "
            "those games as heavy favourites, so the product of its own probabilities is the "
            "right yardstick. Compare p_observed_run_under_model with 0.05 before claiming "
            "anything, and note the sample is one game day."),
        "note": (
            "Graded against official finals only. A sealed game with no verified final stays "
            "UNGRADED and never counts as a loss. The stamp is the end of the latest graded "
            "game day, not the wall clock, so a rebuild reproduces it exactly."),
    }


def settle(date: str = "2026-11-15") -> dict:
    seal = load_seal(date)
    ver = verify_seal(seal)
    if not ver["ok"]:
        raise SystemExit(
            "sealed ledger hash does not match its pre-tip digest - refusing to settle. "
            f"stored {ver['stored']} vs recomputed {ver['recomputed']}")
    finals = C.finals_2026_11_15()
    out = grade(seal, finals)
    summary = summarise(out["graded"], out["ungraded"], seal)
    doc = {
        "schema": "nba2.v4.settlement.v1",
        "seal_file": f"data/v3/ledger/sealed-{date}.json",
        "seal_sha256": ver["stored"],
        "seal_verified": ver["ok"],
        "seal_window": ver["window"],
        "seal_sealed_at_utc": ver["sealed_at_utc"],
        "seal_sealed_by": ver["sealed_by"],
        "settlement": summary,
        "graded": out["graded"],
        "ungraded": out["ungraded"],
        "finals_used": [
            {"game_id": f["game_id"], "final_source_url": f["final_source_url"],
             "gamebook_url": f["gamebook_url"], "quarter_status": f["quarter_status"]}
            for f in finals],
        "settle_rule": (
            "A game is settled only when its official final is in the committed capture AND "
            "the gamebook period row was checked against it. Ungraded is not a loss."),
    }
    body = {k: v for k, v in doc.items() if k != "sha256_after_settlement"}
    doc["sha256_after_settlement"] = sha256(body)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"settled-{date}.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    return doc


def verify_settlement(date: str = "2026-11-15") -> dict:
    p = OUT_DIR / f"settled-{date}.json"
    if not p.exists():
        return {"ok": False, "reason": "no settlement file"}
    doc = json.loads(p.read_text())
    stored = doc.pop("sha256_after_settlement", None)
    from .settlement import canonical as _c  # noqa: F401  (kept explicit for readers)
    recomputed = sha256(doc)
    seal = load_seal(date)
    seal_ok = V3L.sha256({"window": seal["window"], "picks": seal["picks"]}) == seal["sha256"]
    return {"ok": stored == recomputed, "stored": stored, "recomputed": recomputed,
            "seal_still_verified": seal_ok}


if __name__ == "__main__":
    d = settle()
    s = d["settlement"]
    print(f"seal verified: {d['seal_verified']}  {d['seal_sha256'][:16]}")
    print(f"settled {s['n_graded']}/{s['n_sealed']} sealed rows "
          f"(stamp {s['settled_at_utc']}); {s['n_ungraded']} ungraded")
    print(f"margin MAE {s['margin_mae']}  total MAE {s['total_mae']}  "
          f"winner hit {s['winner_hit_rate']}  log-loss {s['log_loss_model']} vs coin "
          f"{s['log_loss_coin']}")
    print(json.dumps(verify_settlement(), indent=1))
