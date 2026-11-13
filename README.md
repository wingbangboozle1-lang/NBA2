# NBA2 — Originated NBA Lines, Signals & Picks Platform

A self-contained system that **originates its own NBA betting lines**, develops
**skill-based signal strategies** (single bets, parlays, player-prop combos), validates
every strategy through gates, measures **correlations**, removes luck, and **generates
picks for every upcoming slate up to 3 days in advance** — with injury-driven rotation
and game-flow analysis.

All factual data (schedule, records, injuries) is verified against **official NBA.com
sources**. Model-originated lines and projections are clearly labeled as model output,
**not** official. Anything that cannot be confirmed from an official source is left blank
and flagged as **unverified** on the [Flagged for Review](flagged.html) page.

## Layout

- `nba2/` — Python system (lines-origination model, strategies, validation gates,
  correlations, injury/game-flow analysis, picks generator) and verified data.
- `site/` — static GitHub Pages site (clean dashboard: landing + category subpages).
- `build_site.py` — regenerates the static site from the verified data.
- `COORDINATION.md` — shared task board (statuses, owners, verification log).

## Run

```bash
pip install -r requirements.txt
python3 nba2/generate.py     # builds data/*.json (picks, strategies, correlations, gameflow)
python3 build_site.py        # renders site/ from the data
```

## Live site

Published on GitHub Pages. See the repository's Pages URL after deploy.

## Verification policy

Every table row on the site carries a source link to an official site. Values that cannot
be confirmed from an official source are left blank and flagged as unverified. Model
outputs (originated lines, projections, picks) are labeled **Model** and are not claimed
to be official.
