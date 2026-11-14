"""Settle sealed predictions against official final scores and publish the result.

    python -m nba2.pipeline.settle

Expects a finals snapshot at data/raw/finals_<as_of>.json of the shape:

    {"source": "https://www.nba.com/games", "records":
        [{"game_id": "0022600231", "home_pts": 112, "away_pts": 105,
          "source": "https://www.nba.com/game/den-vs-nop-0022600231"}]}

Since the 2026-11-14 refresh there can be more than one sealed ledger (the pre-registration
history is never rewritten), so every data/raw/ledger/sealed-*.json is verified and settled
independently. If no finals snapshot exists the command reports PENDING and exits 0: games
that have not been played are not an error, they are Tuesday. What is forbidden is quietly
inventing the missing scores — so `nba2.models.ledger.settle` will not accept partial games
as if they were complete, and the metrics dict stays empty until real finals arrive.
"""

from __future__ import annotations

import glob
import json
from datetime import datetime, timezone
from pathlib import Path

from .. import config
from ..models import gates as G
from ..models import ledger as LD

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / config.DATA_DIR


def find_finals() -> Path | None:
    """Newest finals snapshot, if one has been committed. Absence is normal, not an error."""
    cands = sorted(glob.glob(str(RAW / "finals_*.json")))
    return Path(cands[-1]) if cands else None


def find_ledgers() -> list[Path]:
    return sorted(RAW.glob("ledger/sealed-*.json"))


def settle_one(sealed: Path, finals: Path | None) -> dict:
    ok, stored, recomp = LD.verify(sealed)
    if not ok:
        print(f"SEAL BROKEN for {sealed.name}: header says {stored}, file hashes to {recomp}")
        print("A sealed prediction set was edited after the fact. Do not publish any metric from it.")
        return {"ledger": sealed.name, "seal": {"sha256": stored, "n_predictions": None},
                "status": "SEAL_BROKEN"}
    n = json.loads(sealed.read_text())["header"]["n_predictions"]
    print(f"{sealed.name}: seal verified {stored[:16]}… ({n} predictions)")
    s = LD.settle(sealed, finals)
    print(f"  status: {s.status}  ({s.games_settled}/{s.games_expected} games)")
    if s.games_settled == 0:
        print("  nothing to score yet; gates stay BLOCKED — that is the correct answer")
        return {"ledger": sealed.name,
                "seal": {"sha256": stored, "n_predictions": n},
                "status": s.status, "games_settled": s.games_settled,
                "games_expected": s.games_expected, "metrics": {}, "gate_measurements": {}}
    print(json.dumps(s.metrics, indent=2))
    measurements = {
        "settled_bets": s.metrics.get("n_settled", 0),
        "line_mae": s.metrics.get("spread_mae"),
        "baseline_mae": None,          # must be measured against a real market, not assumed
        "brier": s.metrics.get("brier"),
        "calibration_slope": s.metrics.get("calibration_slope"),
        "calibration_intercept": s.metrics.get("calibration_intercept"),
    }
    results = G.evaluate(measurements)
    for r in results:
        print(f"  {r.gate_id} {r.result:8s} {r.measured}")
    return {"ledger": sealed.name,
            "seal": {"sha256": stored, "n_predictions": n},
            "status": s.status, "games_settled": s.games_settled,
            "games_expected": s.games_expected, "metrics": s.metrics,
            "gate_measurements": measurements,
            "gates": [r.as_dict() for r in results]}


def main() -> int:
    ledgers = find_ledgers()
    if not ledgers:
        print("no sealed ledger found — run:  python -m nba2.pipeline.seal_predictions")
        return 1
    finals = find_finals()
    print(f"finals snapshot: {finals.name if finals else 'none committed (PENDING by design)'}")
    results = [settle_one(p, finals) for p in ledgers]
    (ROOT / "data" / "settlement.json").write_text(json.dumps({
        "settled_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "finals_snapshot": finals.name if finals else None,
        "ledgers": results,
        "note": ("PENDING where no official final-score snapshot covers the ledger's games. "
                 "Metrics stay unmeasured rather than assumed."),
    }, indent=2) + "\n")
    print("wrote data/settlement.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
