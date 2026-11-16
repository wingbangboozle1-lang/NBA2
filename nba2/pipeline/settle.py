"""Settle sealed predictions against official final scores and publish the result.

    python -m nba2.pipeline.settle

Finals are read from EVERY committed official final-score capture, not from one file picked by
name (the pre-2026-11-16 behaviour read only the newest `finals_*.json` by filename, so official
captures such as `data/raw/capture_*/results_*.json` were silently ignored):

    data/raw/finals_*.json                 (records or games arrays, see below)
    data/raw/capture_*/results_*.json      (records array)

Each final is accepted only if
  * it has an integer `game_id`, integer `home_pts` and `away_pts`;
  * its source is an https URL on an official NBA host (www.nba.com, nba.com, official.nba.com);
  * if its status is present it is `final`;
  * if quarter scores are present they are integers whose sum equals the official final on each
    side (a LINESCORE that does not add up is rejected, never corrected).
Records without quarter scores are accepted on the final score alone and flagged
`quarters_verified: false` — the final score is what settles a bet, the quarters are a feed field.

Two sources that give the same `game_id` different scores are a FINALS CONFLICT. Settlement is
then refused for the whole run: data/settlement.json is not rewritten and the command exits 3.

Since the 2026-11-14 refresh there can be more than one sealed ledger (the pre-registration
history is never rewritten), so every data/raw/ledger/sealed-*.json is verified and settled
independently. If no final exists the command reports PENDING and exits 0: games that have not
been played are not an error. What is forbidden is quietly inventing a missing score, so
`nba2.models.ledger` never scores a game that has no verified final.
"""

from __future__ import annotations

import glob
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .. import config
from ..models import gates as G
from ..models import ledger as LD

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / config.DATA_DIR

OFFICIAL_HOSTS = {"www.nba.com", "nba.com", "official.nba.com"}


class FinalsConflict(Exception):
    """Two official sources disagree on a game's final score. Settlement must not proceed."""


def finals_snapshot_paths() -> list[Path]:
    """Every committed official final-score capture, sorted for a deterministic run."""
    paths = [Path(p) for p in glob.glob(str(RAW / "finals_*.json"))]
    paths += [Path(p) for p in glob.glob(str(RAW / "capture_*" / "results_*.json"))]
    return sorted(paths)


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_official_url(u) -> bool:
    if not isinstance(u, str) or not u:
        return False
    parts = urlsplit(u)
    return parts.scheme == "https" and parts.hostname in OFFICIAL_HOSTS


def _check_record(r: dict) -> tuple[dict | None, str | None]:
    """Return (normalised record, None) if accepted, else (None, reason)."""
    gid = r.get("game_id")
    if not isinstance(gid, str) or not gid:
        return None, "missing game_id"
    if not (_is_int(r.get("home_pts")) and _is_int(r.get("away_pts"))):
        return None, "final score is not two integers"
    if r.get("status") not in (None, "final", "Final"):
        return None, f"status {r.get('status')!r} is not final"
    source = r.get("source") or r.get("source_url")
    if not _is_official_url(source):
        return None, f"source is not an official NBA https URL ({source!r})"
    aq, hq = r.get("away_quarters"), r.get("home_quarters")
    quarters_verified = False
    if aq is not None or hq is not None:
        if not (isinstance(aq, list) and isinstance(hq, list) and aq and hq
                and all(_is_int(x) for x in aq + hq)):
            return None, "quarter scores present but not integer lists"
        if sum(aq) != r["away_pts"] or sum(hq) != r["home_pts"]:
            return None, (f"quarter scores do not sum to the final ({sum(aq)}-{sum(hq)} vs "
                          f"{r['away_pts']}-{r['home_pts']})")
        quarters_verified = True
    return {
        "game_id": gid,
        "date": r.get("date"),
        "away": r.get("away"),
        "home": r.get("home"),
        "away_pts": r["away_pts"],
        "home_pts": r["home_pts"],
        "away_quarters": aq,
        "home_quarters": hq,
        "quarters_verified": quarters_verified,
        "source": source,
    }, None


def load_official_finals(paths: list[Path] | None = None) -> tuple[list[dict], dict]:
    """Union of all official finals, keyed by game_id. Raises FinalsConflict on disagreement."""
    paths = finals_snapshot_paths() if paths is None else paths
    by_id: dict[str, dict] = {}
    rejected: list[dict] = []
    snapshots: list[str] = []
    for path in paths:
        doc = json.loads(path.read_text())
        try:
            snapshots.append(path.relative_to(ROOT).as_posix())
        except ValueError:          # a snapshot outside the repository (tests, scratch dirs)
            snapshots.append(path.name)
        for r in doc.get("records") or doc.get("games") or []:
            rec, why = _check_record(r)
            if rec is None:
                rejected.append({"snapshot": path.name, "game_id": r.get("game_id"), "reason": why})
                continue
            prev = by_id.get(rec["game_id"])
            if prev is None:
                by_id[rec["game_id"]] = rec
                continue
            if (prev["away_pts"], prev["home_pts"]) != (rec["away_pts"], rec["home_pts"]):
                raise FinalsConflict(
                    f"{rec['game_id']}: {prev['source']} says {prev['away_pts']}-{prev['home_pts']}, "
                    f"{rec['source']} says {rec['away_pts']}-{rec['home_pts']}")
            # Same score from another official source: keep the first, and quarters-verified wins.
            if rec["quarters_verified"] and not prev["quarters_verified"]:
                by_id[rec["game_id"]] = rec
    records = [by_id[k] for k in sorted(by_id)]
    report = {
        "snapshots": snapshots,
        "records": len(records),
        "quarters_verified": sum(1 for r in records if r["quarters_verified"]),
        "rejected": rejected,
    }
    return records, report


def find_ledgers() -> list[Path]:
    return sorted(RAW.glob("ledger/sealed-*.json"))


def settle_one(sealed: Path, finals: list[dict]) -> dict:
    ok, stored, recomp = LD.verify(sealed)
    if not ok:
        print(f"SEAL BROKEN for {sealed.name}: header says {stored}, file hashes to {recomp}")
        print("A sealed prediction set was edited after the fact. Do not publish any metric from it.")
        return {"ledger": sealed.name, "seal": {"sha256": stored, "n_predictions": None},
                "status": "SEAL_BROKEN"}
    n = json.loads(sealed.read_text())["header"]["n_predictions"]
    print(f"{sealed.name}: seal verified {stored[:16]}… ({n} predictions)")
    s = LD.settle_records(sealed, finals)
    print(f"  status: {s.status}  ({s.games_settled}/{s.games_expected} games)")
    if s.games_settled == 0:
        print("  nothing to score yet; gates stay BLOCKED — that is the correct answer")
        return {"ledger": sealed.name,
                "seal": {"sha256": stored, "n_predictions": n},
                "status": s.status, "games_settled": s.games_settled,
                "games_expected": s.games_expected, "metrics": {}, "gate_measurements": {},
                "per_game": []}
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
            "gates": [r.as_dict() for r in results],
            "per_game": s.per_game}


def main() -> int:
    ledgers = find_ledgers()
    if not ledgers:
        print("no sealed ledger found — run:  python -m nba2.pipeline.seal_predictions")
        return 1
    try:
        records, report = load_official_finals()
    except FinalsConflict as e:
        print(f"FINALS CONFLICT — settlement refused, data/settlement.json NOT rewritten: {e}")
        return 3
    print(f"official final-score snapshots: {len(report['snapshots'])} file(s), "
          f"{report['records']} verified final(s), {report['quarters_verified']} with verified quarters, "
          f"{len(report['rejected'])} rejected")
    for rj in report["rejected"]:
        print(f"  rejected {rj['snapshot']} {rj['game_id']}: {rj['reason']}")
    results = [settle_one(p, records) for p in ledgers]
    (ROOT / "data" / "settlement.json").write_text(json.dumps({
        "settled_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "finals_snapshot": ", ".join(Path(s).name for s in report["snapshots"]) or None,
        "finals_snapshots": report["snapshots"],
        "finals_verified_records": report["records"],
        "finals_quarters_verified": report["quarters_verified"],
        "finals_rejected": report["rejected"],
        "ledgers": results,
        "note": ("PENDING where no verified official final score covers the ledger's games. "
                 "Finals are the union of every committed official capture, keyed by game_id; "
                 "a conflict between sources refuses settlement. Metrics stay unmeasured rather "
                 "than assumed."),
    }, indent=2) + "\n")
    print("wrote data/settlement.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
