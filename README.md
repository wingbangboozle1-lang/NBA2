# NBA2 — NBA Line Origination & Strategy Platform

Originate your own NBA lines, generate validated picks for upcoming slates
(up to 3 days ahead), track injury/rotation/game-flow effects, and run a
luck-resistant strategy leaderboard. Every published value carries an official
source link; unverified values are left blank and flagged — never inferred.

**Live dashboard (GitHub Pages):** https://wingbangboozle1-lang.github.io/NBA2/

## Repository map

| Path | What it is |
|---|---|
| [`docs/`](docs/) | the published dashboard (GitHub Pages source) |
| [`data/`](data/) | verified datasets — games, standings, ratings, official injuries, player baselines, correlation matrix, our lines, picks, parlays, prop lines, luck ledger, leaderboard |
| [`scripts/model.py`](scripts/model.py) | deterministic line-origination engine (v1.0) — re-run to refresh outputs |
| [`scripts/build_site.py`](scripts/build_site.py) | generates the dashboard from the data |
| [`scripts/check_site.py`](scripts/check_site.py) | integration checks (links, per-row sources) |
| [`analysis/strategy/`](analysis/strategy/) | methodology: model, validation gates, luck removal, correlation, leaderboard |
| [`analysis/`](analysis/) | executive summary, game-flow analysis, questions register, suggestions queue, repo review, verification log |
| [`COORDINATION.md`](COORDINATION.md) | shared task board (multi-session protocol) |

## Source policy

1. **Official NBA sources preferred:** nba.com game pages, official.nba.com
   (injury reports, releases), ak-static.cms.nba.com (report PDFs).
2. **Trusted secondary sources are labeled per row** (Basketball-Reference, ESPN,
   CBS/AP) and listed on the site's **Flagged for Review** page when they support
   core numbers.
3. **No value is ever inferred or filled in.** If it can't be confirmed, the cell
   stays blank and is flagged `unverified`.

## Quick start

```bash
python3 scripts/model.py       # recompute lines, picks, parlays, props, luck ledger
python3 scripts/build_site.py  # regenerate docs/ (the site)
python3 scripts/check_site.py  # verify links + per-row sources
```

## Decisions wanted

Open the **Suggestions** page on the site (or
[`analysis/suggestions.md`](analysis/suggestions.md)): nothing gets implemented
until proposals there are approved. Blocking unknowns and their discovery plans
are in [`analysis/questions.md`](analysis/questions.md).

## Status (2026-11-13 build)

- 31 games lined for Nov 13–16; 38 picks pass conviction gates; correlated
  combos built only from documented correlation bands.
- All validation gates (G1–G5) seeded; strategies are `provisional` until
  30 graded picks — by design.
- Market line feed not yet connected (Q-1/S-1): picks are "make at our number".
