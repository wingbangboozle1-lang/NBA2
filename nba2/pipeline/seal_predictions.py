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
    """Games strictly after the snapshot date, through as_of + days_in_advance.

    Today's games are excluded from the sealed set: their injury report is already hours old, so
    a line published for them now is not a forecast, it is a recap. They stay on the site as the
    calibration slate.
    """
    as_of = slate["as_of"]
    days = slate["window"].get("days_in_advance", 3)
    start = (datetime.strptime(as_of, "%Y-%m-%d").date() + timedelta(days=1)).isoformat()
    end = (datetime.strptime(as_of, "%Y-%m-%d").date() + timedelta(days=days)).isoformat()
    return start, min(end, slate["window"]["last_game_date"])


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
    main()
