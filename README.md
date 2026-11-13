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

## Line-origination data platform & dashboard (`dashboard/`) — session arena-10957a28

A self-contained 12-page dashboard (served at `/NBA2/dashboard/`) plus the verified CSV
datasets, deterministic model, and analysis documents behind it:

| Area | Contents |
|---|---|
| [`dashboard/`](dashboard/) | Slates & Picks (31 games, our lines, picks, combos, props), Injuries & Rotation, Game Flow, Strategies & Gates, Correlation, Leaderboard, Data Tables, Suggestions, Questions, **Flagged for Review**, Sources |
| [`data/`](data/) | `games.csv` (31 games w/ official IDs), `standings-2026-11-13.csv`, `team-ratings-2026-11-13.csv`, `injury-report-2026-11-13.csv` (official PDF), `player-baselines-2026-11-13.csv`, `correlation-matrix.csv`, `our-lines.csv`, `picks.csv`, `parlays.csv`, `prop-lines.csv`, `luck-table.csv`, `leaderboard.csv` — every row source-linked |
| [`scripts/`](scripts/) | `model.py` (line origination v1.0), `build_site.py`, `check_site.py` (link + per-row source checks) |
| [`analysis/`](analysis/) | executive summary, per-game flow notes, questions register (Q-1..Q-10), suggestions queue (S-1..S-12), repo review, verification log, `strategy/` methodology (model, gates G1–G5, luck removal, correlation, leaderboard) |

```bash
python3 scripts/model.py       # recompute lines/picks/combos/props/luck ledger
python3 scripts/build_site.py  # regenerate dashboard/
python3 scripts/check_site.py  # verify links + per-row sources (PASS: 524 rows)
```

Distinct files only — this session's `data/*.csv`, `scripts/`, `analysis/`, `dashboard/`
do not overwrite any earlier session's paths; shared files (`COORDINATION.md`, `README.md`)
merged append-only.

---

## Session `session-aaa8b341` — `originated/` (appended, no shared file modified)

`main` had advanced to `f73b8f1` through PRs #1–#11 by five other sessions, which own the root
`index.html`, `assets/`, `data/*.json`, `pages/*.html` and `research/`. Per `COORDINATION.md`, this
session's build is therefore namespaced and modifies nothing outside it:

```
originated/index.html        14 sub-pages under originated/pages/
originated/data/             verified inputs + derived model output
originated/engine/           compute · build · verify
originated/research/         the prose behind every page
```

**Live:** https://wingbangboozle1-lang.github.io/NBA2/originated/

```bash
cd originated
node engine/compute.js && node engine/build.js && node engine/verify.js   # 24/24 PASS
```

### Corrections raised against shared data (not force-pushed — the files belong to other sessions)

| ID | Claimed | Official source says |
|---|---|---|
| I-01 | Ben Simmons — Golden State Warriors | **Sacramento Kings**, Out, Right Achilles Tendon Repair / Surgery |
| I-02 | Jimmy Butler III — *Right Patella Subluxation* | **Right ACL Repair / Surgery**; "Right Patella Subluxation" is Maxime Raynaud's (SAC) reason |
| I-03 | *"~34 MPG season avg"*, *"-100% scoring output"* | unsourced; removed and replaced with `null` |

Source for I-01/I-02:
[Official NBA Injury Report, 11/13/26 01:00 PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf)

### What `originated/` publishes

23 games (13–15 Nov 2026) with originated spreads, totals and moneylines; 10 strategies against 8
validation gates; model-derived correlations from a seeded 200k-draw Monte-Carlo; a Flagged for
Review page listing every unverified cell and every declared assumption.

Two blockers, both documented with remediation plans: **no market price feed** (so nothing here is a
bettable edge) and **no official per-player feed** (so every player prop threshold is blank).
