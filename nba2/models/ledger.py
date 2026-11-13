"""Sealed prediction ledger + settlement.

Why this exists: the only evaluation a brand-new line-origination system can honestly run is
a *pre-registered* one. So every published line is written to a canonical JSON, hashed, and
the hash is committed to git in the same commit as the site. Nothing can be quietly re-fitted
after the games, and the leaderboard can only be scored against predictions that existed
before tip-off.

Settlement consumes official final scores. When those do not exist yet, `settle()` returns a
pending report instead of a fake number.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CANON = dict(sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, **CANON).encode("utf-8")


def sha256_of(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def seal(payload: list[dict], path: Path, note: str = "") -> dict:
    """Write payload + digest. Returns the seal header (also embedded in the file)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256_of(payload)
    header = {
        "schema": "nba2.sealed-predictions.v1",
        "sealed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_predictions": len(payload),
        "sha256": digest,
        "hash_rule": "sha256 over canonical JSON (sorted keys, no whitespace) of the predictions array",
        "note": note,
    }
    path.write_text(json.dumps({"header": header, "predictions": payload}, indent=2, ensure_ascii=False) + "\n")
    return header


def verify(path: Path) -> tuple[bool, str, str]:
    """Recompute the digest of a sealed file. (ok, stored, recomputed)"""
    doc = json.loads(Path(path).read_text())
    recomputed = sha256_of(doc["predictions"])
    stored = doc["header"]["sha256"]
    return recomputed == stored, stored, recomputed


def predictions_from_lines(lines, model) -> list[dict]:
    out = []
    for l in lines:
        out.append({
            "game_id": l.game_id,
            "date": l.date,
            "time_et": l.time_et,
            "away": l.away,
            "home": l.home,
            "our_spread_home": l.spread_home,
            "our_total": l.total_line,
            "p_home_win": l.home_win_prob,
            "margin_model": l.margin,
            "total_model": l.total,
            "tier": l.tier,
            "stability": l.stability,
            "injury_blind": l.injury_blind,
            "inputs": {
                "away_srs": model.get(l.away).srs, "home_srs": model.get(l.home).srs,
                "away_srs_shrunk": model.get(l.away).srs_shrunk,
                "home_srs_shrunk": model.get(l.home).srs_shrunk,
                "margin_sd": model.cal.margin_sd, "hca_points": model.cal.hca_points,
            },
            "sealed_before_tip": True,
        })
    return out


# --------------------------------------------------------------------------- settlement
@dataclass
class Settlement:
    games_expected: int
    games_settled: int
    metrics: dict
    per_game: list[dict]
    status: str

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def score_margin(actual_home_minus_away: float) -> dict:
    return {"home_margin": actual_home_minus_away}


def settle(sealed_path: Path, finals_path: Path | None) -> Settlement:
    """Compare sealed lines with official final scores.

    `finals_path` must contain records of the form
    {"game_id": ..., "home_pts": int, "away_pts": int, "source": url}.
    Missing games are listed, never imputed.
    """
    doc = json.loads(Path(sealed_path).read_text())
    preds = doc["predictions"]
    expected = {p["game_id"] for p in preds}
    if finals_path is None or not Path(finals_path).exists():
        return Settlement(len(preds), 0, {}, [], "PENDING — no official final scores in the repository")

    finals = json.loads(Path(finals_path).read_text())["records"]
    by_id = {f["game_id"]: f for f in finals}
    missing = sorted(expected - set(by_id))
    rows, margins_err, totals_err, probs, outcomes, push = [], [], [], [], [], 0
    for p in preds:
        f = by_id.get(p["game_id"])
        if not f:
            continue
        actual_margin = f["home_pts"] - f["away_pts"]
        actual_total = f["home_pts"] + f["away_pts"]
        if p["our_spread_home"] is not None:
            margins_err.append(abs(-p["our_spread_home"] - actual_margin))
        if p["our_total"] is not None:
            err = abs(p["our_total"] - actual_total)
            if err == 0:
                push += 1
            totals_err.append(err)
        if p["p_home_win"] is not None:
            probs.append(p["p_home_win"])
            outcomes.append(1 if actual_margin > 0 else 0)
        rows.append({
            "game_id": p["game_id"], "matchup": f"{p['away']} @ {p['home']}",
            "final": f"{f['away_pts']}-{f['home_pts']}",
            "our_spread_home": p["our_spread_home"],
            "spread_err": round(abs(-p["our_spread_home"] - actual_margin), 2) if p["our_spread_home"] is not None else None,
            "our_total": p["our_total"],
            "total_err": round(abs(p["our_total"] - actual_total), 2) if p["our_total"] is not None else None,
            "source": f.get("source", ""),
        })

    from .gates import brier, log_loss, mean, calibration_slope_intercept, bootstrap_ci, t_stat
    metrics: dict[str, Any] = {"n_settled": len(rows), "missing_games": len(missing)}
    if margins_err:
        metrics["spread_mae"] = round(mean(margins_err), 3)
    if totals_err:
        metrics["total_mae"] = round(mean(totals_err), 3)
        metrics["total_pushes"] = push
    if probs:
        metrics["brier"] = round(brier(probs, outcomes), 4)
        metrics["log_loss"] = round(log_loss(probs, outcomes), 4)
        slope, inter = calibration_slope_intercept(probs, outcomes)
        metrics["calibration_slope"] = None if slope != slope else round(slope, 3)
        metrics["calibration_intercept"] = None if inter != inter else round(inter, 3)
    status = "SETTLED" if not missing else f"PARTIAL — {len(missing)} game(s) have no official final score"
    return Settlement(len(preds), len(rows), metrics, rows, status)
