"""Settle sealed predictions against official final scores and publish the result.

    python -m nba2.pipeline.settle

Expects a finals snapshot at data/raw/finals_<as_of>.json of the shape:

    {"source": "https://www.nba.com/games", "records":
        [{"game_id": "0022600231", "home_pts": 112, "away_pts": 105,
          "source": "https://www.nba.com/game/den-vs-nop-0022600231"}]}

If that file does not exist the command reports PENDING and exits 0: games that have not
been played are not an error, they are Tuesday. What is forbidden is quietly inventing the
missing scores — so `nba2.models.ledger.settle` will not accept partial games as if they
were complete, and the metrics dict stays empty until real finals arrive.
"""

from __future__ import annotations

import glob
import json
from datetime import datetime, timezone
from pathlib import Path

from .. import config
from ..models import gates as G
from ..models import ledger as LD
from .. import provenance as PV

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / config.DATA_DIR


def find_finals() -> Path | None:
    """Newest finals snapshot, if one has been committed. Absence is normal, not an error."""
    cands = sorted(glob.glob(str(RAW / "finals_*.json")))
    return Path(cands[-1]) if cands else None


def main() -> int:
    sealed = RAW / "ledger" / "sealed-2026-11-13.json"
    if not sealed.exists():
        print("no sealed ledger found — run:  python -m nba2.pipeline.seal_predictions")
        return 1
    ok, stored, recomp = LD.verify(sealed)
    if not ok:
        print(f"SEAL BROKEN: header says {stored}, file hashes to {recomp}")
        print("A sealed prediction set was edited after the fact. Do not publish any metric from it.")
        return 1
    print(f"seal verified: {stored[:16]}… ({json.loads(sealed.read_text())['header']['n_predictions']} predictions)")

    finals = find_finals()
    s = LD.settle(sealed, finals)
    print(f"status: {s.status}  ({s.games_settled}/{s.games_expected} games)")
    if s.games_settled == 0:
        print("nothing to score yet; the gate results stay BLOCKED — that is the correct answer")
        out = ROOT / "data" / "settlement.json"
        out.write_text(json.dumps({
            "settled_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "seal": {"sha256": stored, "n_predictions": s.games_expected},
            "result": s.as_dict(),
            "gate_measurements": {},
            "note": "PENDING: no official final-score snapshot in data/raw/. Metrics stay unmeasured "
                    "rather than assumed.",
        }, indent=2) + "\n")
        print(f"wrote {out.relative_to(ROOT)}")
        return 0

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
    (ROOT / "data" / "settlement.json").write_text(json.dumps({
        "settled_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seal": {"sha256": stored, "n_predictions": s.games_expected},
        "result": s.as_dict(),
        "gate_measurements": measurements,
        "gates": [r.as_dict() for r in results],
    }, indent=2) + "\n")
    print("wrote data/settlement.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
