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
    """The games that are still ahead of us when the snapshot was taken.

    The snapshot may state its pick window explicitly (`pick_window` in the snapshot JSON).
    That is the authoritative answer and it is committed, so sealing stays deterministic.
    Without it we fall back to the date rule: games strictly after the snapshot date, through
    as_of + days_in_advance. Today's games are excluded under that rule because their injury
    report is already hours old, so a line published for them is a recap, not a forecast; they
    stay on the site as the calibration slate.
    """
    explicit = slate.get("pick_window")
    if explicit:
        return explicit["first_game_date"], explicit["last_game_date"]
    as_of = slate["as_of"]
    days = slate["window"].get("days_in_advance", 3)
    start = (datetime.strptime(as_of, "%Y-%m-%d").date() + timedelta(days=1)).isoformat()
    end = (datetime.strptime(as_of, "%Y-%m-%d").date() + timedelta(days=days)).isoformat()
    return start, min(end, slate["window"]["last_game_date"])


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
