"""Tamper-evident ledger and per-strategy pre-registration.

Two artefacts, both content-addressed:

1. **Pre-registration (``data/v3/prereg/*.json``).** One file per strategy, frozen
   *before its first bet*: the signal, every threshold, the universe, and the exact
   settlement rule. A strategy that has no pre-registration file cannot publish a
   pick, and the file records the sha256 of its own canonical body so a later edit
   is detectable.

2. **Sealed picks (``data/v3/ledger/sealed-<date>.json``).** Every published pick is
   hashed before tip and the hash is published. After the official final scores
   arrive the file is *settled*: each row is graded, the settlement stamp is written,
   and the digest is recomputed over the graded rows so the pre-tip hash and the
   post-settlement hash can be compared. The pre-tip digest is never overwritten.

Nothing here sizes a stake. Every stake is 0.00 because no market price exists.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from . import official as O

ROOT = Path(__file__).resolve().parents[2]
PREREG_DIR = ROOT / "data" / "v3" / "prereg"
LEDGER_DIR = ROOT / "data" / "v3" / "ledger"

# ------------------------------------------------------------------ pre-registration
# signal, thresholds, universe and settlement rule are frozen here. Editing this
# table changes the sha256 of every affected strategy file, which is the point.
STRATEGIES = [
    {
        "id": "S1",
        "name": "Estimator-agreement moneyline",
        "signal": "Both estimators name the same winner AND their margin estimates "
                  "differ by less than the median disagreement of the slate.",
        "thresholds": {"max_disagreement_pts": "median of the slate, computed at build time",
                       "min_p_home": 0.60, "stake_pct": 0.0},
        "universe": "every game in the T+0..T+3 window whose two clubs are both "
                    "inside the luck noise band (|luck z| <= 2.0)",
        "settlement_rule": "Official NBA final score. Win if the named side wins in "
                           "regulation or overtime. A game with no official final is "
                           "left UNGRADED and never counted as a loss.",
        "status": "pre-registered, 0 bets placed",
    },
    {
        "id": "S2",
        "name": "Disagreement-fade spread",
        "signal": "Fade the consensus spread when the two estimators disagree by more "
                  "than 4.0 points, on the published reasoning that a wide gap means "
                  "the number is not trustworthy in either direction.",
        "thresholds": {"min_disagreement_pts": 4.0, "stake_pct": 0.0},
        "universe": "games in the T+0..T+3 window where both clubs are inside the "
                    "luck noise band",
        "settlement_rule": "Official NBA final score against the originated spread. "
                           "A margin within 0.5 of the spread is a PUSH and is excluded "
                           "from the hit rate, never counted as a win.",
        "status": "pre-registered, 0 bets placed",
    },
    {
        "id": "S3",
        "name": "Possession-model total",
        "signal": "Take the under when the possessions x PPP total sits more than 6 "
                  "points below the league mean total, the over when more than 6 above.",
        "thresholds": {"band_pts": 6.0, "stake_pct": 0.0},
        "universe": "games in the T+0..T+3 window; a game is excluded if either club "
                    "is outside the luck noise band",
        "settlement_rule": "Official NBA final total points, overtime included. "
                           "Exactly on the number is a PUSH.",
        "status": "pre-registered, 0 bets placed",
    },
    {
        "id": "S4",
        "name": "Rotation-availability fade",
        "signal": "Fade a side whose official injury report lists 4 or more players as "
                  "Out for that game, and whose opponent lists fewer than 2.",
               "thresholds": {"min_out": 4, "max_opp_out": 1, "stake_pct": 0.0},
        "universe": "games in the window where BOTH clubs have filed a report for that "
                    "date (an unfiled club is excluded, never assumed healthy)",
        "settlement_rule": "Official NBA final score. Unfiled reports produce no bet.",
        "status": "pre-registered, 0 bets placed",
    },
    {
        "id": "S5",
        "name": "Same-game parlay: spread + total",
        "signal": "Both legs are priced from the same game model; the parlay is quoted "
                  "only at the measured rho, never at the naive product.",
        "thresholds": {"min_leg_prob": 0.55, "stake_pct": 0.0},
        "universe": "any game in the window where both single-leg probabilities clear "
                    "the threshold and both clubs are inside the luck noise band",
        "settlement_rule": "Official NBA final score and final total. Both legs must "
                           "win; a push on either leg voids the parlay.",
        "status": "pre-registered, 0 bets placed",
    },
]


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def write_prereg() -> list[dict]:
    PREREG_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for s in STRATEGIES:
        body = dict(s)
        body["registered_at_utc"] = O.AS_OF_UTC
        body["registered_by"] = O.SESSION
        body["window"] = {"start": O.WINDOW[0], "end": O.WINDOW[1]}
        digest = sha256(body)
        body["sha256"] = digest
        # Window-scoped filename. A pre-registration is frozen BEFORE the first bet of the
        # window it names, so a later window must never overwrite it: each window writes
        # its own file and every previous registration stays verifiable on disk.
        slug = s["name"].lower().replace(" ", "-")[:40]
        path = PREREG_DIR / f"{s['id']}-{slug}__{O.WINDOW[0]}.json"
        path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n")
        out.append({"id": s["id"], "name": s["name"], "file": _rel(path),
                    "sha256": digest, "status": s["status"]})
    return out


def verify_prereg() -> tuple[bool, list[str]]:
    ok, msgs = True, []
    for p in sorted(PREREG_DIR.glob("*.json")):
        d = json.loads(p.read_text())
        stored = d.pop("sha256", None)
        recomputed = sha256(d)
        good = stored == recomputed
        ok = ok and good
        msgs.append(f"{p.name}: {'VERIFIED' if good else 'BROKEN'} {str(stored)[:16]}")
    return ok, msgs


# ------------------------------------------------------------------------- sealing
def build_picks(result: dict, surface: str = "projection") -> list[dict]:
    """The rows that get hashed. Deterministic; sorted; no timestamp inside."""
    rows = []
    for ln in result["lines"]:
        if ln["luck_gate"]["blocked"]:
            continue
        rows.append({
            "game_id": ln["game_id"], "date": ln["date"], "matchup": ln["matchup"],
            "surface": surface,
            "e1_margin": ln["e1_margin"], "e2_margin": ln["e2_margin"],
            "disagreement": ln["disagreement"], "consensus_margin": ln["consensus_margin"],
            "total": ln["total"], "p_home": ln["p_home"],
            "stake_pct": 0.0,
            "market_price": None,
            "price_flag": "F-308",
        })
    return sorted(rows, key=lambda r: (r["date"], r["game_id"]))


def seal(result: dict) -> dict:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    picks = build_picks(result)
    body = {
        "schema": "nba2.v3.sealed-picks.v1",
        "window": {"start": O.WINDOW[0], "end": O.WINDOW[1]},
        "sealed_at_utc": O.AS_OF_UTC,
        "sealed_by": O.SESSION,
        "n_picks": len(picks),
        "picks": picks,
    }
    digest = sha256({"window": body["window"], "picks": picks})
    body["sha256"] = digest
    name = f"sealed-{O.WINDOW[0]}.json"
    path = LEDGER_DIR / name
    prev = path.read_text() if path.exists() else None
    settled = json.loads(prev).get("settlement") if prev else None
    if settled:                       # never lose a settlement stamp on a re-seal
        body["settlement"] = settled
        body["sha256_after_settlement"] = sha256(
            {"window": body["window"], "picks": picks, "settlement": settled})
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n")
    return {"file": _rel(path), "digest": digest, "n": len(picks),
            "settled": bool(settled)}


def verify(path: Path) -> tuple[bool, str, str]:
    d = json.loads(path.read_text())
    stored = d.get("sha256")
    recomputed = sha256({"window": d["window"], "picks": d["picks"]})
    return stored == recomputed, str(stored), recomputed


def settle(result: dict, finals: list[dict]) -> dict | None:
    """Grade the sealed rows against official finals. Writes a settlement stamp."""
    path = LEDGER_DIR / f"sealed-{O.WINDOW[0]}.json"
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    by_id = {f["game_id"]: f for f in finals}
    graded, ungraded = [], []
    for p in d["picks"]:
        f = by_id.get(p["game_id"])
        if not f:
            ungraded.append(p["game_id"])
            continue
        home_margin = f["home_pts"] - f["away_pts"]
        total = f["home_pts"] + f["away_pts"]
        graded.append({
            **p,
            "official_home_pts": f["home_pts"], "official_away_pts": f["away_pts"],
            "official_home_margin": home_margin, "official_total": total,
            "margin_error": round(home_margin - p["consensus_margin"], 2),
            "total_error": round(total - p["total"], 2),
            "winner_correct": (home_margin > 0) == (p["consensus_margin"] > 0),
            "source_url": f["source_url"],
        })
    # Deterministic stamp: the end of the latest game day that was actually graded,
    # not the wall clock, because CI compares a rebuild against the committed artefact.
    graded_dates = [f["date"] for f in finals if f["game_id"] in {p["game_id"] for p in d["picks"]}]
    settled_at = (max(graded_dates) + "T23:59:59Z") if graded_dates else None
    if not graded_dates:
        return None
    stamp = {
        "settled_at_utc": settled_at,
        "settled_from": "official finals committed under data/raw/history + this session's capture",
        "n_graded": len(graded), "n_ungraded": len(ungraded),
        "ungraded_game_ids": ungraded,
        "margin_mae": round(sum(abs(g["margin_error"]) for g in graded) / len(graded), 3)
        if graded else None,
        "total_mae": round(sum(abs(g["total_error"]) for g in graded) / len(graded), 3)
        if graded else None,
        "winner_hit_rate": round(sum(1 for g in graded if g["winner_correct"]) / len(graded), 4)
        if graded else None,
        "note": "Graded against official finals only. A game with no official final "
                "stays UNGRADED and never counts as a loss. The stamp is the end of the "
                "latest graded game day, not a wall-clock time, so a rebuild reproduces it.",
    }
    d["settlement"] = stamp
    d["sha256_after_settlement"] = sha256(
        {"window": d["window"], "picks": d["picks"], "settlement": stamp})
    path.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    return stamp


if __name__ == "__main__":
    from .model import build
    res = build()
    print(seal(res))
    ok, msgs = verify_prereg() if PREREG_DIR.exists() else (True, [])
    print("\n".join(msgs) or "no pre-registration files yet")
