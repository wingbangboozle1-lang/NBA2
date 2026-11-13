# NBA2 — Originated NBA Lines, Signals & Picks Platform

A source-linked NBA forecasting platform that **originates its own betting lines**,
develops **skill-based signal strategies** (single bets, parlays, player-prop combos),
validates every strategy through gates, measures **correlations**, removes luck, and
**generates picks for every upcoming slate up to 3 days in advance** — with
injury-driven rotation and game-flow analysis.

All factual data (schedule, records, injuries) is verified against **official NBA.com
sources** and linked per row. Model-originated lines, projections, and picks are labeled
**Model** — they are not official sportsbook lines. Anything that cannot be confirmed
from an official source is left blank and flagged as **unverified** on the
[Flagged for Review](flagged.html) page.

## Layout

- `nba2/` — Python system: lines-origination model, strategy framework with validation
  gates, correlation engine, injury/game-flow analysis, picks generator, and verified data
  (`nba2/data/`).
- Root HTML pages — the live dashboard (clean landing page + category subpages), served
  by GitHub Pages from the `main` branch root:
  `index.html`, `picks.html`, `strategies.html`, `injuries.html`, `correlations.html`,
  `executive-summary.html`, `suggestions.html`, `questions.html`, `flagged.html`.
- `assets/` — shared site CSS/JS for the root dashboard.
- `pages/`, `verified/`, `data/`, `tools/` — supplementary research/verification pages and
  data contributed by a parallel integration session (preserved, not discarded).
- `archive/` — the parallel session's original landing/flagged pages, preserved on merge.
- `build_site.py` — regenerates the root dashboard from the verified data.
- `COORDINATION.md` — shared task board (statuses, owners, verification log, merge record).

## Run

```bash
python3 nba2/generate.py     # builds nba2/data/*.json (picks, strategies, correlations, gameflow)
python3 build_site.py        # renders the root dashboard from the data
```

No third-party dependencies required (Python standard library only).

## Live site

Published on GitHub Pages: https://wingbangboozle1-lang.github.io/NBA2/

## Verification policy

Every table row carries a source link to an official site. Values that cannot be
confirmed from an official source are left blank and flagged as unverified. Model
outputs (originated lines, projections, picks) are labeled **Model** and are not claimed
to be official.
