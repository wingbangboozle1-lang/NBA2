"""Settle sealed predictions against official final scores and publish the result.

    python -m nba2.pipeline.settle

Official final scores can live in several committed captures, each written at a different
time and in a different shape. Until 2026-11-16 this module read only the lexicographically
newest ``data/raw/finals_*.json`` (which is ``finals_all.json``, nine 2026-11-13 games).
That silently ignored every later official feed, so the sealed ledgers showed 0 settled
games even though official finals were committed (audit item IR-1, brief-gap map).

This version reads EVERY committed official finals source, keys the result by ``game_id``,
and fails closed:

* a game is used only if at least one source gives a final score for it;
* a quarter row that does not sum to the final is rejected (that source is ignored);
* two sources that disagree on the score, or on the clubs, make the game a CONFLICT:
  it is excluded and listed, never averaged, never picked by file name;
* a game with no final (not played, or still in progress when read) stays PENDING.

The merged result is written to ``data/raw/official_finals_union.json`` (one record per
settled game, with every contributing source listed). Sealed ledgers are read only and
verified before and after settlement.

Sources read (all committed; nothing is fetched by this module):

    data/raw/finals_*.json                       {"records": [{game_id, home_pts, away_pts, source}]}
    data/raw/capture_*/results_*.json            {"records": [{game_id, away, home, away_pts, home_pts,
                                                              status, away_quarters, home_quarters, ...}]}
    data/raw/results/results_*.json              same shape as the capture feeds (one row per game)
    data/v2/results.json                         {"rows": [{game_id, away, home, away_pts, home_pts, ...}]}

If no finals source covers a ledger's games the command reports PENDING and exits 0: games
that have not been played are not an error. What is forbidden is inventing the missing scores.
"""

from __future__ import annotations

import glob
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import config
from ..models import gates as G
from ..models import ledger as LD

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / config.DATA_DIR
UNION_PATH = RAW / "official_finals_union.json"
FINAL_STATUSES = (None, "final", "Final", "FINAL")


# --------------------------------------------------------------------------- source discovery
def finals_sources() -> list[Path]:
    """Every committed official finals capture this module reads, in a stable order."""
    paths: list[Path] = []
    paths += [Path(p) for p in sorted(glob.glob(str(RAW / "finals_*.json")))]
    paths += [Path(p) for p in sorted(glob.glob(str(RAW / "capture_*" / "results_*.json")))]
    paths += [Path(p) for p in sorted(glob.glob(str(RAW / "results" / "results_*.json")))]
    v2 = ROOT / "data" / "v2" / "results.json"
    if v2.exists():
        paths.append(v2)
    return paths


def find_finals() -> Path | None:
    """Kept for callers that still ask for 'the finals file'. Returns the union, if built."""
    return UNION_PATH if UNION_PATH.exists() else None


def find_ledgers() -> list[Path]:
    return sorted(RAW.glob("ledger/sealed-*.json"))


# --------------------------------------------------------------------------- normalisation
def _label(path: Path) -> str:
    """Repo-relative label for a source file (absolute if it lives outside the repo)."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _records_of(doc: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(doc.get("records"), list):
        return doc["records"]
    if isinstance(doc.get("rows"), list):
        return doc["rows"]
    return []


def _as_int(x: Any) -> int | None:
    return x if isinstance(x, int) and not isinstance(x, bool) else None


def _quarters_ok(pts: int, quarters: Any, overtime: Any = ()) -> bool | None:
    """True/False if the quarter row is present and checkable, None if absent.

    Overtime periods, when listed, count toward the final: 4 quarters + OT must equal the score.
    """
    if not isinstance(quarters, list) or not quarters or any(not isinstance(q, int) for q in quarters):
        return None
    if any(not isinstance(q, int) for q in overtime):
        return False
    return sum(quarters) + sum(overtime) == pts


def normalise_source(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Return (candidate final scores, rejections) for one committed source file."""
    doc = json.loads(path.read_text())
    name = _label(path)
    out: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for r in _records_of(doc):
        gid = r.get("game_id")
        if not isinstance(gid, str) or not gid:
            continue
        status = r.get("status")
        if status not in FINAL_STATUSES:
            # e.g. "not final at retrieval": carries no score, so it is simply not a final.
            continue
        a, h = _as_int(r.get("away_pts")), _as_int(r.get("home_pts"))
        if a is None or h is None:
            continue
        # Quarter check: a quarter row that does not reproduce the final is not trusted.
        #
        # Same schema problem as the source link below: the v4 gamebook feed spells the
        # period rows ``away_q`` / ``home_q``. Reading only the old spelling meant the
        # quarters were dropped from the union, so the published results page showed a final
        # score with no period breakdown even though the gamebook had supplied one. Both
        # spellings are accepted and the sum check still gates trust.
        aq = r.get("away_quarters", r.get("away_q"))
        hq = r.get("home_quarters", r.get("home_q"))
        ot = r.get("ot_quarters") if isinstance(r.get("ot_quarters"), dict) else {}
        qa = _quarters_ok(a, aq, ot.get("away") or [])
        qh = _quarters_ok(h, hq, ot.get("home") or [])
        if qa is False or qh is False:
            rejected.append({"game_id": gid, "source": name,
                             "reason": "quarter row does not sum to the final score; source ignored for this game"})
            continue
        out.append({
            "game_id": gid,
            "away": r.get("away"), "home": r.get("home"),
            "away_pts": a, "home_pts": h,
            # A results feed may name its link several ways depending on its schema
            # version. The v4 gamebook feed (nba2.results-feed.official-gamebook.v1) carries
            # ``final_source_url`` (the nba.com game page) and ``gamebook_url`` (the PDF), and
            # names no ``source_url`` at all — so before this fallback existed its eight 11/16
            # records reached the union with an EMPTY source and no link back to the league.
            # Preference order: the score's own page, then the gamebook it was read from.
            "source": (r.get("source_url") or r.get("source")
                       or r.get("final_source_url") or r.get("gamebook_url") or ""),
            "origin": name,
            "away_quarters": aq if qa else None,
            "home_quarters": hq if qh else None,
            "ot_periods": r.get("ot_periods"),
            "ot_quarters": {"away": ot.get("away"), "home": ot.get("home")} if ot else None,
        })
    return out, rejected


# --------------------------------------------------------------------------- union
def build_union(paths: list[Path] | None = None) -> dict[str, Any]:
    """Pure function over the committed sources: keyed union with conflict detection."""
    paths = finals_sources() if paths is None else paths
    candidates: dict[str, list[dict[str, Any]]] = {}
    rejections: list[dict[str, str]] = []
    for p in paths:
        cands, rej = normalise_source(p)
        rejections += rej
        for c in cands:
            candidates.setdefault(c["game_id"], []).append(c)

    records: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for gid in sorted(candidates):
        cs = candidates[gid]
        scores = {(c["away_pts"], c["home_pts"]) for c in cs}
        teams = {(c["away"], c["home"]) for c in cs if c["away"] and c["home"]}
        if len(scores) > 1:
            conflicts.append({"game_id": gid, "reason": "sources disagree on the final score",
                              "readings": sorted([{"score_away_home": list(s)} for s in scores],
                                                 key=lambda d: d["score_away_home"]),
                              "origins": sorted({c["origin"] for c in cs})})
            continue
        if len(teams) > 1:
            conflicts.append({"game_id": gid, "reason": "sources disagree on the clubs",
                              "readings": sorted(list(teams)), "origins": sorted({c["origin"] for c in cs})})
            continue
        best = next((c for c in cs if c["away_quarters"] and c["home_quarters"]), cs[0])
        away, home = (teams.pop() if teams else (best["away"], best["home"]))
        records.append({
            "game_id": gid, "away": away, "home": home,
            "away_pts": best["away_pts"], "home_pts": best["home_pts"],
            "source": best["source"] or next((c["source"] for c in cs if c["source"]), ""),
            "sources": sorted({c["origin"] for c in cs}),
            "away_quarters": best["away_quarters"], "home_quarters": best["home_quarters"],
            "ot_periods": best["ot_periods"],
            "ot_quarters": best.get("ot_quarters"),
        })
    return {
        "schema": "nba2.official-finals-union.v1",
        "rule": ("one record per game_id that at least one committed official source gives a final for; "
                 "game excluded if sources conflict on score or clubs; source ignored if its quarter row does "
                 "not sum to the final"),
        "sources_read": [_label(p) for p in paths],
        "records": records,
        "conflicts": conflicts,
        "rejected_quarter_rows": rejections,
    }


def write_union(doc: dict[str, Any], path: Path = UNION_PATH) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- settlement
def settle_one(sealed: Path, finals: Path | None, union: dict[str, Any] | None = None) -> dict:
    ok, stored, recomp = LD.verify(sealed)
    if not ok:
        print(f"SEAL BROKEN for {sealed.name}: header says {stored}, file hashes to {recomp}")
        print("A sealed prediction set was edited after the fact. Do not publish any metric from it.")
        return {"ledger": sealed.name, "seal": {"sha256": stored, "n_predictions": None},
                "status": "SEAL_BROKEN"}
    doc = json.loads(sealed.read_text())
    n = doc["header"]["n_predictions"]
    print(f"{sealed.name}: seal verified {stored[:16]}… ({n} predictions)")

    # Games in conflict were already removed from the union, so they cannot be scored here.
    conflict_ids = {c["game_id"] for c in (union or {}).get("conflicts", [])}
    s = LD.settle(sealed, finals)

    print(f"  status: {s.status}  ({s.games_settled}/{s.games_expected} games)")
    if s.games_settled == 0:
        print("  nothing to score yet; gates stay BLOCKED — that is the correct answer")
        return {"ledger": sealed.name,
                "seal": {"sha256": stored, "n_predictions": n},
                "status": s.status, "games_settled": s.games_settled,
                "games_expected": s.games_expected, "metrics": {}, "gate_measurements": {},
                "games_in_conflict": sorted(conflict_ids & {p["game_id"] for p in doc["predictions"]})}
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
            "settled_rows": s.per_game,
            "games_in_conflict": sorted(conflict_ids & {p["game_id"] for p in doc["predictions"]}),
            "gate_measurements": measurements,
            "gates": [r.as_dict() for r in results]}


def main() -> int:
    ledgers = find_ledgers()
    if not ledgers:
        print("no sealed ledger found — run:  python -m nba2.pipeline.seal_predictions")
        return 1
    union = build_union()
    write_union(union)
    print(f"official finals: {len(union['records'])} settled game(s) from "
          f"{len(union['sources_read'])} committed source file(s); "
          f"{len(union['conflicts'])} conflict(s); {len(union['rejected_quarter_rows'])} rejected quarter row(s)")
    for c in union["conflicts"]:
        print(f"  CONFLICT {c['game_id']}: {c['reason']}")
    finals = UNION_PATH if union["records"] else None
    print(f"finals snapshot: {UNION_PATH.name if finals else 'none committed (PENDING by design)'}")
    results = [settle_one(p, finals, union) for p in ledgers]
    (ROOT / "data" / "settlement.json").write_text(json.dumps({
        "settled_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "finals_snapshot": UNION_PATH.name if finals else None,
        "finals_sources_read": union["sources_read"],
        "finals_conflicts": union["conflicts"],
        "finals_rejected_quarter_rows": union["rejected_quarter_rows"],
        "ledgers": results,
        "note": ("PENDING where no official final-score snapshot covers the ledger's games. "
                 "Metrics stay unmeasured rather than assumed. Finals are the keyed union of every "
                 "committed official source (data/raw/official_finals_union.json); conflicting "
                 "games are excluded, never averaged."),
    }, indent=2) + "\n")
    print("wrote data/settlement.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
