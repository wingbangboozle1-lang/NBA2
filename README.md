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

## The published site — one tree, named

The live site is built from **one named tree**, listed explicitly in
[`nba2/pipeline/build_public.py`](nba2/pipeline/build_public.py):

```
index.html + flagged.html        the canonical dashboard
pages/**                         its 21 category subpages
backtest/**                      the measured-skill backtest the dashboard links to
css/ assets/ styles.css app.js   the styles and behaviour
COORDINATION.md README.md        the board and the map of the repository
```

`.github/workflows/pages.yml` is what publishes: it rebuilds the tree from the committed
snapshots, fails if the committed files differ from that rebuild, stages the publish list, and
**fails the deploy if any internal link in the staged tree does not resolve**.

> **One repository setting could not be changed from this session.** The Pages setting is still
> `build_type: legacy` (deploy from the branch root): the GitHub API answers **403 — "Resource
> not accessible by integration"** for `PUT /repos/{owner}/{repo}/pages` from the token this
> session has (independently confirmed by two earlier sessions). In practice the **Actions
> deployment wins** — the classic branch build is cancelled when a newer deployment is created —
> and the live site serves the named tree. The one-click fix is recorded as **S-32** and
> **FLAG-LIVE-08**: *Settings → Pages → Build and deployment → Source → GitHub Actions*. No code
> change is required, and nothing on the site changes if it is not done.

Everything else that is in this repository (`site/`, `docs/`, `dashboard/`, `originated/`,
`verified/`, `archive/`, the code, the data) stays in the repository as history and is linked
as *source*. It is not shipped as a second dashboard — see
[the reconciliation page](pages/reconciliation.html) for the status of each tree.

> **Why this changed.** Until 2026-11-14 the committed `pages.yml` published the `site/` tree
> while the Pages setting published the repository root, so a reader received a different
> dashboard from the one CI built — and the two answered "what are the picks?" differently
> (27 sealed picks vs 0 published). One publish target, one window, one answer.

## The dashboard this session generates

`index.html` + `pages/**` (21 pages, 46 tables, 1290 rows) are rendered from
[`data/site.json`](data/site.json), which is itself generated only from committed snapshots:

| Page | Contents |
|---|---|
| Dashboard | KPIs, slate, slate irregularities, and which build is canonical |
| Executive Summary | one screen: what exists, what is proven, what blocks it |
| Picks (3-day slate) | lean + trigger + 0% stake per game, for 2026-11-14 → 11-17 |
| Originated Lines | every game: both base ratings, consensus margin, spread, total, P(win), fair odds, sensitivity stability, tier — plus the cross-document corroboration table |
| Strategy Leaderboard | 9 strategies × 10 gates, tiers, reward allocation |
| Correlation & Parlays | correlation register; same-game parlays priced over a swept ρ band; cost-of-stacking arithmetic |
| Player Props & Combos | pricing model present, inputs absent — every row blank by policy |
| Injuries & Rotation | 122 official report rows (11/13 19:30 ET release, incl. first 11/14 statuses), rotation-body arithmetic, leader cross-check |
| Game Flow | schedule-spot load from official dates; in-game columns blank |
| **Live Verification** | the 2026-11-14 10:15 UTC official re-read: every check, every difference, every field the page does not render |
| **Ratings Staleness** | what a one-slate records refresh does to the published lines, measured and deliberately not applied |
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
| `nba2/pipeline/` | `build_site_data` → `build_site` → `lint`, plus `build_public` (the named publish list + its link check), `seal_predictions`, `settle`, `reconcile` |
| `nba2/tests/` | 62 standard-library tests (verified 2026-11-14): statistics, invariants, published-artefact checks, determinism |
| `requirements/`, `suggestions/` | registers rendered on the site (requirements, questions, repo review, suggestions) |
| `COORDINATION.md` | shared board: sessions, claims, conflicts, completion log |

## Site surfaces that already existed (preserved, not discarded)

Several sessions worked in parallel, so the repository contains more than one site tree. This is
the honest map rather than a claim that there is one generator — and, since 2026-11-14, only
one of them is published:

| Surface | Built by | Published? | Notes |
|---|---|---|---|
| root `*.html` + `pages/**` | `nba2/pipeline/build_site.py` from `data/site.json` | **yes — this is the live site** | the canonical dashboard; 21 pages, 46 tables, 1290 rows, every row sourced |
| `backtest/**` | session arena-f7477d5e | **yes** | the measured-skill backtest the dashboard links to; 155 official finals, leakage-tested |
| `site/**` (v2 "Lines Lab") | session arena-6e7afc65 | no — repository only | a second dashboard built one window earlier (31 games, 11-13 → 11-16) that publishes no picks; kept for the record, reconciled on [the reconciliation page](pages/reconciliation.html) |
| root `picks.html`, `strategies.html`, … (the arena-7b4973eb set) | `build_site.py` + `nba2/generate.py` | no — superseded | its own originated lines; reconciled against ours on the reconciliation page |
| `docs/**` | session arena-35264d96 | no — repository only | 13-page verification-first documentation layer, left untouched |
| `dashboard/**` | session arena-10957a28 | no — repository only | 12-page CSV-driven dashboard with its own checker (`scripts/check_site.py`), still passing |
| `verified/**`, `data/verified/**` | sessions arena-23927d63 / arena-7b4973eb | no — repository only | row-level verification records for schedule, injuries and gates |
| `archive/**` | integration | no — repository only | byte-for-byte copies of the `main` pages this merge replaced |
| `tools/**` | prior sessions | no — repository only | `generate_picks_lab.py`, `verify_site.py`, `check_links_all.py` — independent link and source checks; still pass |

## Reproduce everything

```bash
python -m unittest discover -s nba2/tests -t .   # statistics + invariants (64 tests)
python -m nba2.pipeline.seal_predictions          # pre-register the window's lines, hash them
python -m nba2.pipeline.build_site_data           # snapshots -> data/site.json
python -m nba2.pipeline.build_site                 # data/site.json -> index.html + pages/**
python -m nba2.pipeline.lint                       # provenance + links + staleness gate
python -m nba2.pipeline.build_public --out _site  # the named publish list + its link check
python -m nba2.pipeline.settle                      # PENDING until official final scores exist

python3 audit/2026-11-14-live/verify_live.py       # the 2026-11-14 official re-verification
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
(`nba2/pipeline/refresh.py`, covered by the 64-test suite): an unreachable official endpoint or a
schema drift aborts the
job before anything is committed, and a missing future-date release or a not-yet-final scoreboard is
reported as the expected pre-deadline state, not an error. What it never does: rewrite sealed
predictions, originate picks, or size stakes — those stay gated behind owner decisions.
Transcripts of injury PDFs remain human-verified inputs; the machine can only cross-check them.


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

### The ratings snapshot is one slate behind (measured 2026-11-14 10:15 UTC)

The committed ratings snapshot (`data/raw/team_ratings_2026-11-13.json`) was retrieved
2026-11-13 22:35 UTC, while the 2026-11-13 slate was still running, so it reflects games through
**2026-11-12**. A live re-read of the official standings on 2026-11-14 10:15 UTC found that
**19 of 30 teams** had moved.

The published lines are derived from the committed snapshot and the sealed ledgers are
immutable, so **the lines were not silently re-derived**. Instead the effect is measured and
published on [the Ratings Staleness page](pages/ratings-staleness.html):

| Quantity | As published | Re-anchored to the live standings |
|---|---|---|
| σ margin sd (pts, fitted) | 13.58 | 14.27 |
| Home-court advantage (pts, fitted) | **+1.53** | **−0.29** |
| Fit RMSE (wins) | 1.31 | 1.40 |
| Largest spread move, pick window | — | 2.0 pts (mean 1.78) |
| Games whose lean would flip | — | 1 of 27 |

Two things follow. The movement is bounded — 2 points of spread on a 12-game sample is noise, and
it does not justify rewriting a seal. But the **sign of the fitted home-court term flips on a
one-slate refresh**, which is the clearest evidence yet that HCA is not identified at this sample
size and must stay unratified (`FLAG-PARAM-02`). The policy question — how stale may a snapshot
be before a line is published — is open as **Q-30**, and the fix is proposed as **S-29**.

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

---

## v2 — verified rebuild and the live site (session `arena/6e7afc65-nba2`, 2026-11-14)

> **Superseded on the publish target (2026-11-14, session `arena/9ee870ea-nba2`).** This session
> intended the published site to become **`site/`**, built by `nba2/v2`. It did not happen, and the
> reason is worth recording: the repository's Pages setting stayed on the classic branch build
> (`build_type: legacy`), so the live site kept serving the root tree while the committed workflow
> published `site/` — and the `site/` tree is one data window behind (31 games, 11-13 → 11-16) and
> publishes no picks, because it withholds every pick for want of a market price. The publish
> target has now been reconciled in the other direction: **one named tree** (see
> [the published site section](#the-published-site--one-tree-named)), with `site/` kept in the
> repository as a historical build. The tree itself is unchanged and still builds and verifies.

The published GitHub Pages site is now **`site/`**, built by `nba2/v2` from official NBA pages that were
fetched live during that session. The earlier trees (root `*.html`, `pages/`, `docs/`, `dashboard/`,
`verified/`, `originated/`) remain in the repository unchanged but are **no longer published** — six
dashboards with different numbers is worse than one, and the reconciliation of all six is an owner
decision logged on the new site's Flagged page (F-011).

```bash
python3 -m nba2.v2            # rebuild data/v2/*.json and site/  (17 pages, includes the backtest)
python3 -m nba2.v2.backtest   # walk-forward backtest only
python3 -m nba2.v2.check      # every row has an official source link; every blank has a reason
python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'   # 42 tests
python3 -m unittest discover -s nba2/tests -t .                # 62 tests (prior work, unchanged)
```

What the v2 build changed, in one paragraph: lines are originated from **official** inputs only
(standings, team/opponent/advanced stats, schedule, injury PDF); two independent ratings estimators are
computed and their disagreement is published per game; σ and h are fitted with h pinned to the measured
home-win rate because the unconstrained pair is only weakly identified; expected wins are forced to sum
to actual wins so luck residuals sum to zero; and **every pick is withheld** because a bet needs a
market price (gate G6) and a settled history (G7), neither of which exists in this environment.

Verified this session: **31/31** games match the official schedule, **30/30** team records match live
`nba.com/standings`, and **85/85** injury rows match the official `11/13/26 04:15 PM ET` PDF. That
resolves the earlier 28/30-vs-30/30 W-L discrepancy in favour of 30/30. Full report:
`analysis/verify-2026-11-14.md`.

### The measured result (the part that matters)

A parallel session captured **155 official final scores**; this session used them to walk-forward test
the rating method — rebuilding ratings before each game from only the games already played.

| Measure | Result | Baseline |
|---|---|---|
| Straight-up accuracy | **66.9%** (93/139), 95% CI 58.7–74.2% | always-home 51.8% |
| Margin MAE | **11.91 pts** | zero-margin 13.27 pts (−10.2%) |
| Brier score | **0.2184** | coin flip 0.2500 (−12.6%) |
| AUROC | **0.718** | 0.5 = no information |

Two findings are published against the model's own interest:

* **The margins are compressed.** Predicted-margin sd is 4.98 pts against an actual 16.43 (ratio 0.30),
  and r(predicted, actual) is only +0.39, so a predicted margin is a *ranking* signal, never an expected
  margin or a stake size.
* **Spread↔total correlation is +0.018** (95% CI −0.149 to +0.184, t = 0.21) on 155 finals. Independence
  is neither proven nor rejected; ~780 games would be needed to detect r = 0.10.

None of this is profit. There is no odds feed, so no ROI, no CLV, and no leaderboard rank can exist.

---

## v2.1 — live re-verification and the first graded forecast (session `arena/ab8743d8-nba2`, 2026-11-14)

This session re-read the official pages **today** instead of trusting the transcription, and published what it
found. Two new pages on the canonical site:

* **[Live verification](https://wingbangboozle1-lang.github.io/NBA2/live-verification.html)** — the official pages
  read this session with fetch times, where the published site no longer matches them, and the grading of the
  repository's first genuine forecast.
* **[Decision queue](https://wingbangboozle1-lang.github.io/NBA2/decision-queue.html)** — every suggestion with its
  evidence, the change it would make, and an accept / reject / defer action. Nothing is implemented until the owner
  chooses; this session never writes `accepted`.

```bash
python3 -m nba2.v2.live     # staleness test + grading, re-derived from audit/2026-11-14/
python3 -m nba2.v2          # rebuild site/ (19 pages, was 17)
python3 -m nba2.v2.check    # every row sourced, every blank explained
python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'   # 59 tests (was 43)
```

### What it found, with the numbers

| Finding | Evidence | Source |
|---|---|---|
| The 30 published team records are a **pre-11/13-finals snapshot** | they match the pre-final reconstruction **30/30** and today's official standings **12/30**; 0 rows unexplained | [nba.com/standings](https://www.nba.com/standings) |
| The site's "30/30 identical" cross-check was true when made and is no longer true of the same rows | relabelled *as transcribed 2026-11-14* (F-028) | [nba.com/standings](https://www.nba.com/standings) |
| `nba2/data/picks.json` is the **first genuine out-of-sample forecast** in the repo | committed `d04bdc3` at 22:36:46 UTC, **83 min** before the earliest 11/13 tip; one commit ever | [nba.com/games](https://www.nba.com/games) |
| It went **4-0** — on **4 distinct games**, not 8 | 8 recorded wins because S1 (ML) and S2 (spread) fired on the same four games | [nba.com/games](https://www.nba.com/games) |
| The model shows **no winner-picking edge yet** | model **5/9**, naive net-rating baseline **5/9**, always-home **7/9** | [nba.com/games](https://www.nba.com/games) |
| Margin MAE 11.46 vs 13.33 (predict a tie); **total MAE ties** the flat-224 baseline exactly at 16.44 | n = 9 — one result moves any of these | [nba.com/games](https://www.nba.com/games) |
| **No profit is published anywhere** | `american_odds` is absent from all 21 signals; a PnL would be an assumed −110 | F-026 / Q-28 |

Nine 11/13 finals were confirmed **identically on two official surfaces** ([schedule](https://www.nba.com/schedule)
and [games](https://www.nba.com/games)). The `11/14 11:00 AM ET` injury report returned **AccessDenied**, so no newer
official revision existed at fetch time — recorded, not worked around.

### Why this mattered

Every page printed an `as-of` date and no build failed when the date was old. A stale row and a correct row rendered
identically, both saying MATCH. That is the silent failure mode this project exists to avoid, and it was live on the
site. The fix is not a re-transcription (which reproduces the same failure on the next slate) but a **staleness gate**,
now proposed as DG-02 / Q-23 and enforced ahead of merge by
[`.github/workflows/publish-parity.yml`](.github/workflows/publish-parity.yml), which also closes a deploy hole: no
workflow previously compared the committed `site/` tree against a rebuild, so the published artefact could drift from
its own inputs and only break at deploy time on `main`.

Nothing was invented, and one of this session's own findings was **corrected before publication**: a first draft claimed
two dashboards both reach a reader. Probing the live site disproved it — `/NBA2/pages/session-audit.html` and
`/NBA2/pages/executive-summary.html` return **404**, `/NBA2/data/teams.json` returns **200**. Exactly one tree (the
`site/` artefact) is published; the v1 tree is unreachable debt that CI still rebuilds (F-027, corrected). Two
irregularities in another session's files — a spread-sign inversion in the S2 selections (F-025) and that unreachable
tree (F-027) — are **published, not silently fixed**.

---

## Integration session `arena/9ee870ea-nba2` — one published tree, and a live re-verification (2026-11-14)

### What was wrong, and what was done about it

The repository's Pages setting said `build_type: legacy` (publish the branch root) while the
committed `pages.yml` uploaded the `site/` tree. Both ran on every push to `main`, and the
**most recent deployment wins** — so which dashboard a reader got depended on which build
finished last. (The setting could not be changed from a token: the Pages API answers **403 —
"Resource not accessible by integration"**, independently confirmed by two earlier sessions.
The named-tree workflow wins in practice because the classic build is cancelled once a newer
deployment exists; **S-32** records the one-click admin fix.) Probing the live site with a cache-busting query settled it:

| URL | Result |
|---|---|
| `/NBA2/?probe=1` | **200** — the v2 "Lines Lab" artefact, served at the root |
| `/NBA2/site/?probe=1` | 404 — the artefact's contents are served at the root, not under `site/` |
| `/NBA2/pages/session-audit.html?probe=2` | 404 — the v1 tree was **not** reachable |
| `/NBA2/backtest/index.html?probe=2` | 404 — the v1 tree was **not** reachable |

(An earlier plain-URL fetch in this session returned the *v1* landing page: the GitHub Pages CDN
still had the previous deployment cached. That is why the probe above is cache-busted and why the
first read of the live site was corrected rather than trusted.)

Two trees, two windows, two answers to "what are the picks?" — 27 sealed picks in one, 0 in the
other, because the v2 build withholds every pick for want of a market price. The brief asks for
picks for every slate up to three days out, so the v1 tree is the better product; but it was not
the one being served.

**The fix:**

1. `nba2/pipeline/build_public.py` names the published tree explicitly — dashboard, its 20
   subpages, the measured-skill backtest, the styles, the board, and the machine-readable mirror
   `data/site.json`. A new top-level directory cannot become public by accident.
2. It **stages** that list into `_site/` and **fails** if any internal link in the staged tree does
   not resolve — so a broken link is a build failure, not a support ticket.
3. `.github/workflows/pages.yml` publishes the staged tree; `ci.yml` and `publish-parity.yml` both
   stage it and check it before anything is deployed.
4. The classic branch build stops racing the workflow: the Actions deployment is created last
   and the classic build is cancelled once a newer deployment exists, so the named tree wins in
   practice. The repository's Pages *setting* is still `build_type: legacy` and could not be
   changed from a token (the API answers 403) — see **S-32 / FLAG-LIVE-08** for the one-click
   admin fix. The last successful deployment stays live if a build fails, so the exposure is a
   stale site rather than a down one.

### The re-verification (this is the part that is new)

Official NBA.com pages were read again at **2026-11-14 10:15 UTC** — the schedule and the
standings — and diffed field by field against every committed snapshot. The capture is committed
as `data/raw/official_capture_2026-11-14T1015Z.json`; the diff is
`audit/2026-11-14-live/verify_live.py` → `report.json`; both are published on the
**Live Verification** page.

| Check | Result |
|---|---|
| Capture validated before use | 30/30 teams satisfy `home + road + neutral = (W, L)`; the league balances at 183 W / 183 L = 183 games (174 through 11-12 + the 9 games of 11-13) |
| Slate re-read | 315 field values compared across 36 games |
| The 27 pick-window games | **identical** to the committed capture on date, tip time, teams, game ID, arena, city and state — so the 27 sealed predictions still match what is published |
| 2026-11-13 finals | **identical** to an earlier session's independent capture, all 9 games, including the overtime flag |
| Fields the page does not render | 18 (tip time and broadcaster for the 9 completed games) — listed as *not re-verifiable*, not as matches |
| Differences found | 11: 9 empty Cup-group cells in the committed capture (the official page publishes the group for all nine) and 2 broadcaster labels that do not match the marks the page renders |
| Team records | **19 of 30** moved since the committed snapshot — see the staleness table above |

### New flags

`FLAG-LIVE-01` … `FLAG-LIVE-07` — the ratings snapshot is one slate behind (high), the game IDs
are not monotonic within 2026-11-17 (medium), the Cup group was never captured (medium), two
broadcaster labels do not match the page (low), and three informational notes. All seven are on
the Flagged for Review page with their source links.

### What was deliberately not done

* **No line was re-derived.** The sealed ledgers (`cf7dedc6…`, `c841e8f3…`) are immutable and the
  published lines must keep matching them, so the staleness is *disclosed* (Ratings Staleness
  page) instead of silently corrected.
* **No file owned by another session was edited.** `site/`, `docs/`, `dashboard/`, `originated/`,
  `verified/`, `archive/`, `backtest/` and `nba2/v2/**` are byte-identical to `main`.
* **No pick, ROI, CLV or leaderboard rank was published.** There is still no market price, and a
  forecast without a price is not an edge.
