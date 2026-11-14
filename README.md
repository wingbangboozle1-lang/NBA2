# NBA2 — originated NBA lines, gated strategies, verified data

Live site: **<https://wingbangboozle1-lang.github.io/NBA2/>**

A research desk that **originates its own** NBA spreads, totals and probabilities from
league-published inputs, grades every strategy through validation gates, publishes a leaderboard
that cannot be won until it is measured, and tracks injuries, rotation and game flow against the
official record.

> **What this is not.** There is no market-odds feed connected, so nothing here is a "value bet":
> with no price, edge cannot be computed. The site publishes our number and the **trigger** at which
> a market price would make acting rational. Model output is labelled *derived*, never *official*.
> Nothing here is betting advice, and no bet is ever placed by this repository.

## The one rule

**Every table row carries a source. A value with no source is blank, and the blank is flagged.**
Not a style choice — it is enforced by [`nba2/provenance.py`](nba2/provenance.py) (`make_row`
raises on an unsourced value, on a value attached to a blocked source, and on an unexplained
blank) and re-checked on the emitted files by [`nba2/pipeline/lint.py`](nba2/pipeline/lint.py),
which CI runs before deploy. A blank cell is allowed; a plausible-looking invention is not.

Source classes: `official` (nba.com / ak-static.cms.nba.com / cdn.nba.com), `third_party`
(Basketball-Reference — used for PS/G, PA/G and SRS, which have no reachable official endpoint;
every such row is flagged), `derived` (computed in-repo from a committed snapshot), `blocked`
(we know we need it; we do not have it).

## The dashboard this session generates

`index.html` + `pages/**` (17 pages, 33 tables, 992 rows) are rendered from
[`data/site.json`](data/site.json), which is itself generated only from committed snapshots:

| Page | Contents |
|---|---|
| Dashboard | KPIs, slate, slate irregularities |
| Executive Summary | one screen: what exists, what is proven, what blocks it |
| Picks (3-day slate) | lean + trigger + 0% stake per game, for 2026-11-14 → 11-17 |
| Originated Lines | every game: both base ratings, consensus margin, spread, total, P(win), fair odds, sensitivity stability, tier — plus the cross-document corroboration table |
| Strategy Leaderboard | 9 strategies × 10 gates, tiers, reward allocation |
| Correlation & Parlays | correlation register; same-game parlays priced over a swept ρ band; cost-of-stacking arithmetic |
| Player Props & Combos | pricing model present, inputs absent — every row blank by policy |
| Injuries & Rotation | 122 official report rows (11/13 19:30 ET release, incl. first 11/14 statuses), rotation-body arithmetic, leader cross-check |
| Game Flow | schedule-spot load from official dates; in-game columns blank |
| Methodology & Parameters | fitted σ/HCA, every tunable number with its status and band, ratings, skill/luck |
| Requirements · Repo Review · Open Questions · Suggestions Queue | the registers, kept as JSON in the repo |
| Cross-session Reconciliation | this model vs the model already on `main`, and this session's injury capture vs the prior one |
| Flagged for Review | every open caveat, with the source to check |
| Sources & Verification | what was read, when, and what was unreachable |

## Layout

| Path | What it is |
|---|---|
| `index.html`, `pages/**`, `css/style.css`, `app.js` | the generated dashboard (static; readable with JS off) |
| `data/raw/**` | committed snapshots of official/third-party documents, each with a provenance block |
| `data/raw/ledger/sealed-*.json` | pre-registered predictions + sha256, committed with the site |
| `data/site.json` | every published table, one object per section |
| `nba2/config.py` | markets, parameters (each with `status` + `source`), 10 gates, 9 strategies, tiers, reward weights |
| `nba2/models/` | `ratings` `lines` `gates` `correlation` `props` `injuries` `gameflow` `leaderboard` `ledger` |
| `nba2/pipeline/` | `build_site_data` → `build_site` → `lint`, plus `seal_predictions`, `settle`, `reconcile` |
| `nba2/tests/` | 62 standard-library tests (verified 2026-11-14): statistics, invariants, published-artefact checks, determinism |
| `requirements/`, `suggestions/` | registers rendered on the site (requirements, questions, repo review, suggestions) |
| `COORDINATION.md` | shared board: sessions, claims, conflicts, completion log |

## Site surfaces that already existed (preserved, not discarded)

Four sessions worked in parallel, so the repository publishes more than one surface. This is the
honest map rather than a claim that there is one generator:

| Surface | Built by | Notes |
|---|---|---|
| root `*.html` (`picks`, `strategies`, `injuries`, `correlations`, `executive-summary`, `suggestions`, `questions`, `flagged`) | `build_site.py` + `nba2/generate.py` from `nba2/data/*.json` (session arena-7b4973eb) | its own originated lines; superseded as the landing page, still served, and reconciled against ours on [the reconciliation page](pages/reconciliation.html) |
| `docs/**` | session arena-35264d96 | 13-page verification-first documentation layer, left untouched |
| `verified/**`, `data/verified/**` | sessions arena-23927d63 / arena-7b4973eb | row-level verification records for schedule, injuries and gates |
| `archive/**` | integration | byte-for-byte copies of the `main` pages this merge replaced, plus the earlier session's landing pages |
| `tools/**` | prior sessions | `generate_picks_lab.py`, `verify_site.py`, `check_links_all.py` — independent link and source checks; still pass |

## Reproduce everything

```bash
python -m unittest discover -s nba2/tests -t .   # statistics + invariants (62 tests)
python -m nba2.pipeline.seal_predictions          # pre-register the window's lines, hash them
python -m nba2.pipeline.build_site_data           # snapshots -> data/site.json
python -m nba2.pipeline.build_site                 # data/site.json -> index.html + pages/**
python -m nba2.pipeline.lint                       # provenance + links + staleness gate
python -m nba2.pipeline.settle                      # PENDING until official final scores exist

python3 nba2/generate.py && python3 build_site.py   # the prior session's root dashboard
python3 tools/verify_site.py                        # docs-layer source check
python3 tools/check_links_all.py                    # whole-site link check
```

## Nightly ingest (audit A-01 remediation, v1)

`.github/workflows/refresh.yml` runs at 09:05/13:35 ET: it archives the newest official
injury-report PDFs for the window dates under `data/raw/pdf/`, fetches official final scores for
arrived window dates into `data/raw/finals_*.json`, merges them into the settlement input, settles
the sealed ledger, and rebuilds the site — **only if** the full verify chain (unit tests, seal
verification, provenance lint) passes and `data/raw/ledger/` is byte-identical. It is fail-closed
(`nba2/pipeline/refresh.py`, 62 tests): an unreachable official endpoint or a schema drift aborts the
job before anything is committed, and a missing future-date release or a not-yet-final scoreboard is
reported as the expected pre-deadline state, not an error. What it never does: rewrite sealed
predictions, originate picks, or size stakes — those stay gated behind owner decisions. Transcripts
of injury PDFs remain human-verified inputs; the machine can only cross-check them.


Python 3.11+, standard library only — no `pip install`, so no published number depends on a
package version nobody pinned.

## How a line is made

1. **Inputs** — committed snapshots (refreshed 2026-11-14 by session `arena/1ec4f9bd-nba2`): the
   official slate (36 games, 11/13 context + pick window 11/14–11/17, official game IDs; every field of
   the 31 carried-forward games re-checked against a fresh retrieval, 0 mismatches), the official
   injury report (122 rows from the freshest release at build time, 11/13 19:30 ET, which now carries
   the first real 11/14 statuses; three revisions of 11/13 releases compared across sessions), and a
   team ratings table whose win-loss column is cross-checked three ways: against NBA.com game cards
   (28/30 visible in that capture — TOR/WAS flagged FLAG-SLATE-02), against the prior session's
   independent read (30/30), and re-read from the upstream standings page on 2026-11-14 (30/30 identical,
   `data/raw/ratings_recheck_2026-11-14.json`).
2. **Calibration** — margin volatility σ and home-court advantage are **fitted** by least squares to
   the committed win totals (σ ≈ 13.58 pts, HCA ≈ 1.53 pts; RMSE 1.31 wins vs 2.78 for a .500
   baseline). These are fitted from the committed snapshot, not from a separately described
   multi-season point-in-time history; do not interpret this as out-of-sample validation. Where two
   ways of estimating HCA disagree, the site says so (`FLAG-PARAM-02`).
3. **Shrinkage** — at ~12 games ratings are noise-heavy, so each is multiplied by a reliability
   weight λ = τ²/(τ²+se²) derived from the table's own dispersion.
4. **Two views, one line** — schedule-adjusted SRS and raw scoring margin are carried separately; the
   line is their average and their disagreement is printed beside it. Past tolerance the game is
   Tier C and excluded from action.
5. **Sensitivity** — every line is re-priced across the box of unratified parameters; the fraction of
   the grid that keeps the same side is published as `stability`.
6. **Markets** — spread/total in half-point increments (nothing pushes), win probability from the
   same normal as the spread, fair decimal odds, and a trigger at line ± 1.5 pts.

## What is blocked, and why it stays blocked

| Gap | Consequence |
|---|---|
| No odds feed | no CLV, no ROI, no stake sizing (0% stake is policy, not a placeholder); gates G-02/G-05/G-09 unevaluable |
| No player-level data (`stats.nba.com` unreachable here) | injury **impact**, props, prop combos, same-player correlation: blank |
| Game-level results history — **resolved in the backtest tree** (2026-11-14) | 155 official final scores (2026-10-20 → 11-12) now back a leakage-tested walk-forward ([backtest/](backtest/)); G-04 measured FAIL, G-07 measured PASS; the root site's σ/HCA/correlations are still snapshot-fitted pending owner ratification (S-04) |
| Injury reports are same-day | a T-3 line is structurally availability-blind, so Tier A is suppressed for the whole slate |
| Two models, one slate | 21 of 23 matched games disagree by >1.5 pts (3 favour opposite sides) — published, not averaged |
| Owner decisions pending | 11 thresholds unratified; the reward pool is 100% unallocated until gates pass |

Nine strategies are registered; none is promoted, because promotion requires measurement and no bet
has settled. That is the design working, not a missing feature.

## Data window

`as_of 2026-11-14` (build ran the evening of 2026-11-13 ET, ~01:05 UTC). Slate
`2026-11-13 → 2026-11-17` (36 games: the 9 Emirates NBA Cup group games on 11/13 are day-before
context — already live or completed at retrieval — plus 27 pick-window games). Sealed pick window =
`2026-11-14 → 2026-11-17` (27 games): every upcoming slate within the brief's 3-day maximum gets a
pick. The seal refuses to run if any sealed game is within 6 hours of tip, so a recap can never enter
the pre-registration ledger. Availability data refreshes around the frozen seal: the 11/13 19:30 ET
official release ([PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf))
carries the first day-before designations for the 11/14 slate (5 of 10 team-slots filed; 11/15-17 still
NOT YET SUBMITTED) and is published on [the injuries page](pages/injuries.html) with per-date coverage;
the nightly ingest workflow archives later releases without touching the sealed ledger.
Snapshots are point-in-time captures, not live feeds — read `meta.as_of`
before trusting any number, and see [the sources page](pages/sources.html) for retrieval timestamps.

## Repo conventions

* Branch per session; work only inside the scope claimed in `COORDINATION.md`; small commits,
  `git pull --rebase` before pushing; conflicts resolved without discarding another session's work.
* `data/raw/**` is the source of truth for the site: change the snapshot, then rebuild. Never
  hand-edit `data/site.json` or the HTML — CI fails when they disagree with a rebuild.
* Flagged and unverified items do **not** block a merge; they block a *promotion*.
* Suggestions are a queue, not a to-do list: nothing in
  [`suggestions/SUGGESTIONS.json`](suggestions/SUGGESTIONS.json) is implemented until the owner
  marks it accepted.

---

## The `dashboard/` site — this section is the other session's own text, preserved verbatim

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
