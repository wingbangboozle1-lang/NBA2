"""Seal the current predictions into data/ledger/ and print the digest.

Run this immediately before build_site_data so the seal header (count + sha256) is embedded in
the published site, making the pre-registration visible on the page a reviewer reads first.

The window comes from the slate snapshot itself, never from a constant, so the sealed set can
never drift from the games we actually verified.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .. import config
from ..models import ledger as LD
from ..models import lines as LN
from ..models import ratings as RT

ROOT = Path(__file__).resolve().parents[2]


def pick_window(slate: dict) -> tuple[str, str]:
    """Games from the snapshot's as-of date through as_of + days_in_advance.

    The 2026-11-14 refresh moved this window's start forward by one day relative to the
    original rule ('strictly after the snapshot date'). Rationale, in plain terms: the
    original rule assumed the build ran on game day with an hours-old injury report, so
    publishing that day's games would be recap, not forecast. This build runs the evening
    before the first pick-window game tips (freshest input = the 5 p.m. ET day-before
    filing; first sealed tip is 19:00 ET the next day), so every game from the as-of date
    forward is a genuine forecast and every upcoming slate inside the 3-day cap gets picks.

    The guard below is the safety net: if the seal is ever re-run when a sealed game is
    closer than 6 hours to tip (or already started), it refuses. A recap must never enter
    the pre-registration ledger.
    """
    as_of = slate["as_of"]
    days = slate["window"].get("days_in_advance", 3)
    start = as_of
    end = (datetime.strptime(as_of, "%Y-%m-%d").date() + timedelta(days=days)).isoformat()
    return start, min(end, slate["window"]["last_game_date"])


MIN_HOURS_TO_TIP = 6.0


def assert_games_in_future(window: list[dict], now_utc: datetime) -> None:
    """Refuse to seal any game whose ET tip is closer than MIN_HOURS_TO_TIP."""
    problems = []
    for g in window:
        tip = datetime.strptime(f"{g['date']} {g['time_et']}", "%Y-%m-%d %H:%M")
        tip_utc = tip.replace(tzinfo=timezone(timedelta(hours=-5)))  # EST = UTC-5 (November)
        hours = (tip_utc - now_utc).total_seconds() / 3600.0
        if hours < MIN_HOURS_TO_TIP:
            problems.append(f"{g['game_id']} tips {hours:.1f}h from now (< {MIN_HOURS_TO_TIP}h)")
    if problems:
        raise SystemExit(
            "refusing to seal: " + "; ".join(problems) +
            " — a prediction sealed this close to tip is a recap, not a forecast.")


def verify_existing() -> int:
    """Check the committed seal WITHOUT rewriting it. A verification job must never regenerate a
    sealed artefact — that is the one thing a seal exists to prevent — and a fresh `sealed_at_utc`
    would also make the published site differ from its own rebuild for no reason."""
    slate = json.loads((ROOT / config.DATA_DIR / config.SNAPSHOT_SLATE).read_text())
    path = ROOT / config.DATA_DIR / "ledger" / f"sealed-{slate['as_of']}.json"
    if not path.exists():
        print(f"no sealed ledger at {path.relative_to(ROOT)}")
        return 1
    ok, stored, recomp = LD.verify(path)
    doc = json.loads(path.read_text())
    print(f"seal {str(stored)[:16]}… over {doc['header']['n_predictions']} predictions: "
          f"{'VERIFIED' if ok else 'BROKEN'}")
    if not ok:
        print(f"  header says {stored}\n  file hashes to {recomp}")
        return 1
    site = ROOT / "data" / "site.json"
    if site.exists():
        published = json.loads(site.read_text())["meta"].get("seal") or {}
        if published.get("sha256") != stored:
            print(f"  site publishes a different digest ({published.get('sha256')}) than the ledger holds")
            return 1
        print(f"  site page prints the same digest the ledger recomputes")
    return 0 if ok else 1


def main() -> dict:
    model = RT.build(ROOT)
    games, slate = LN.load_slate(ROOT / config.DATA_DIR / config.SNAPSHOT_SLATE)
    start, end = pick_window(slate)
    window = [g for g in games if start <= g["date"] <= end]
    assert_games_in_future(window, datetime.now(timezone.utc))
    preds = LD.predictions_from_lines(LN.price_slate(model, window, {}), model)
    path = ROOT / config.DATA_DIR / "ledger" / f"sealed-{slate['as_of']}.json"
    hdr = LD.seal(preds, path, note=(
        f"Pre-registered {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} for {len(preds)} games "
        f"({start}..{end}) from the {slate['as_of']} snapshot. Spread/total are model projections in "
        "half-point increments; no market price was available to this build, so no bet is asserted — "
        "only our number and the trigger level. These predictions must not be edited after tip-off: "
        "settle them with nba2.pipeline.settle. Verify the digest with "
        "`python -c \"from nba2.models import ledger; print(ledger.verify(r'...'))\"`."
    ))
    ok, stored, recomputed = LD.verify(path)
    print(f"sealed {hdr['n_predictions']} predictions -> {path.relative_to(ROOT)}")
    print(f"sha256 {hdr['sha256']}")
    if not ok:
        raise SystemExit(f"seal mismatch: stored {stored} != recomputed {recomputed}")
    print("verify: digest recomputed from the file matches the header")
    return hdr


if __name__ == "__main__":
    import sys
    if "--verify" in sys.argv:
        raise SystemExit(verify_existing())
    main()
