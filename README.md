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

---

## Verification-first documentation site (`docs/`) — session arena-35264d96

A 13-page verification-first documentation layer (served at `/NBA2/docs/`), complementing the dashboards above:

| Page | Contents |
|---|---|
| [Executive Summary](docs/executive-summary.html) | The project on one page |
| [Strategies](docs/strategies.html) | Origination pipeline + 12-strategy catalog (`data/strategies_lab.json`) |
| [Validation Gates](docs/validation-gates.html) | G1–G13 gates; luck-removal methods; staking |
| [Correlation](docs/correlation.html) | Parlay/SGP math; correlation matrix template; portfolio caps |
| [Leaderboard](docs/leaderboard.html) | Competition scoring, tiers, rewards, anti-gaming |
| [Slate Picks](docs/picks.html) | T+3 pick pipeline, daily runbook on the official report clock, demo output |
| [Injuries & Rotations](docs/injuries-rotations.html) | Official injury-report policy (verified verbatim); minutes framework |
| [Game Flow](docs/game-flow.html) | Pace, clutch, blowouts, late fouling, rest |
| [Questions & Answers](docs/questions.html) | Decision-readiness: answered (with sources) / blocking / discovery paths |
| [Suggestions](docs/suggestions.html) | Review-before-implementing improvement backlog |
| [Flagged for Review](docs/flagged-for-review.html) | Every irregularity and unverified item |
| [Sources](docs/sources.html) | Master source ledger |

Lab tools (stdlib only): `tools/generate_picks_lab.py` (slate pick generator; refuses slates beyond
today+3 days and refuses picks from strategies whose gates lack backtest evidence),
`tools/verify_site.py` (docs site: every data row must carry a source link; no broken links),
`tools/check_links_all.py` (whole-site link check across all sessions' pages).

```bash
python3 tools/generate_picks_lab.py --demo   # synthetic demo of the pick pipeline
python3 tools/verify_site.py                 # verify docs tables are fully sourced
python3 tools/check_links_all.py             # link check across root/, pages/, verified/, docs/
```
