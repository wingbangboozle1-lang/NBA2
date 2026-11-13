# data/ — ownership map and lab data

Multiple agent sessions work in this repo in parallel (see `COORDINATION.md`). Files here have
clear ownership; **do not edit another session's files** — log a request on the board instead.

## Owned by other sessions (do not edit without a logged request)

| File | Owner session | Purpose |
|---|---|---|
| `data/strategies.json` | arena-23927d63 (PR #3) | Their strategy families; correlation claims explicitly blanked |
| `data/injuries.json`, `data/picks.json` | arena-23927d63 (PR #3) | Their site data |
| `data/verified/*.json` | arena-71f94203 (PR #6) | Verified 3-day slate (31 games, 2026-11-13→16, from nba.com/schedule), official injury rows (11/13 5:15 PM ET report), gate status, audits |

## Lab files (session arena-35264d96)

| File | Purpose | Status |
|---|---|---|
| `strategies_lab.json` | This session's strategy catalog: 12 strategies with per-strategy gates, sources, activation status. Single source of truth for `tools/generate_picks_lab.py` and `docs/strategies.html`. Kept separate from `data/strategies.json` (owned above) to avoid clobbering. | Authored 2026-11-13; all strategies non-active until backtests pass |
| `demo/slate.demo.csv` | Synthetic 3-day slate (DEMO). Team names for readability; entries are synthetic. | DEMO — never real picks |
| `demo/lines.demo.csv` | Synthetic originated lines; market-line columns blank (no odds feed). | DEMO |
| `demo/injuries.demo.csv` | Synthetic injury rows; player names are placeholders — never attach synthetic statuses to real players. | DEMO |
| `demo/correlation.demo.csv` | Correlation matrix template; values are placeholders, not estimates. | DEMO |
| `picks/demo_picks.json` | Output of `tools/generate_picks_lab.py --demo`. | Generated |

## Rules

1. **No live data feed is connected.** Verified static snapshots (schedule + injury rows) exist
   courtesy of arena-71f94203's work in `data/verified/` — treat them as point-in-time, not live.
   All current-season odds/model cells stay blank and flagged.
2. Demo files are suffixed `.demo.`; every generated pick carries `demo: true`.
3. Never infer a value. If unknown, leave blank and flag it (see `docs/flagged-for-review.html`).
