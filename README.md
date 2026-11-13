# NBA2 — originated NBA lines, gated strategies

Live site: **<https://wingbangboozle1-lang.github.io/NBA2/>**

A research desk that builds its **own** NBA spreads, totals and probabilities from
league-published inputs, grades every strategy through validation gates, and publishes a
leaderboard that cannot be won until it is measured.

> **What this is not.** There is no market-odds feed connected, so nothing here is a "value
> bet": with no price, edge cannot be computed. The site publishes our number and the
> *trigger* at which a market price would make acting rational. Nothing here is betting
> advice, and no bet is ever placed by this repository.

## The one rule

**Every table row carries a source. A value with no source is blank, and the blank is
flagged.** That is not a style choice — it is enforced by
[`nba2/provenance.py`](nba2/provenance.py) (`make_row` raises) and re-checked on the emitted
files by [`nba2/pipeline/lint.py`](nba2/pipeline/lint.py), which CI runs before deploy. A
blank cell is allowed; a plausible-looking invention is not.

Source classes: `official` (nba.com / ak-static.cms.nba.com / cdn.nba.com), `third_party`
(Basketball-Reference — used for PS/G, PA/G, SRS, which have no reachable official endpoint),
`derived` (computed in-repo from a committed snapshot), `blocked` (we know we need it; we do
not have it).

## Layout

| Path | What it is |
|---|---|
| `index.html`, `pages/*.html` | The published dashboard (static, no build needed to read) |
| `data/raw/*.json` | Committed snapshots of official/third-party documents, each with a provenance block |
| `data/raw/ledger/sealed-*.json` | Pre-registered predictions + sha256, committed with the site |
| `data/site.json` | Every published table, one object per page section |
| `nba2/config.py` | Markets, parameters (each with `status` + `source`), 10 gates, 9 strategies, tiers, reward weights |
| `nba2/models/` | `ratings` `lines` `gates` `correlation` `props` `injuries` `gameflow` `leaderboard` `ledger` |
| `nba2/pipeline/` | `build_site_data` → `build_site` → `lint`, plus `seal_predictions` and `settle` |
| `nba2/tests/` | 49 stdlib tests: statistics, invariants, published-artefact checks, determinism |
| `requirements/` | Requirements register, question list, line-by-line repo review (JSON, rendered on the site) |
| `suggestions/SUGGESTIONS.json` | Improvement queue for owner review — **not implemented** |
| `COORDINATION.md` | Multi-session board: claims, scopes, conflicts, completion log |

## Reproduce everything

```bash
python -m unittest discover -s nba2/tests -t .   # statistics + invariants
python -m nba2.pipeline.seal_predictions          # pre-register the window's lines, hash them
python -m nba2.pipeline.build_site_data           # snapshots -> data/site.json
python -m nba2.pipeline.build_site                # data/site.json -> index.html + pages/**
python -m nba2.pipeline.lint                      # provenance + link + staleness gate
python -m nba2.pipeline.settle                    # PENDING until official final scores exist
```

Python 3.11+, standard library only — no `pip install`, so the numbers cannot depend on a
package version nobody pinned.

## How a line is made

1. **Inputs** — committed snapshots: the official slate (31 games, 11/13–11/16, with official
   game IDs), the official injury report (95 rows for 11/13), and a team ratings table
   (30 teams) whose win-loss column is cross-checked against NBA.com game cards.
2. **Calibration** — margin volatility σ and home-court advantage are **fitted** by
   least squares against the 30 verified win totals (σ ≈ 13.58 pts, HCA ≈ 1.53 pts; RMSE
   1.31 wins vs 2.78 for a .500 baseline). Neither is copied from folklore, and where the two
   estimates of HCA disagree the site says so (`FLAG-PARAM-02`).
3. **Shrinkage** — at ~12 games, ratings are noise-heavy, so each is multiplied by a
   reliability weight λ = τ²/(τ²+se²) derived from the table's own dispersion.
4. **Two views, one line** — a schedule-adjusted rating (SRS) and a raw scoring margin are
   carried separately; the line is their average, and their disagreement is published next to
   it. Beyond tolerance the game is Tier C and excluded from action.
5. **Sensitivity** — every line is re-priced across the box of unratified parameters
   (σ ±10%, HCA ±). The fraction of the grid that keeps the same side is published as
   `stability`; a line that flips inside the box is not an opinion, it is a parameterisation.
6. **Markets** — spread/total in half-point increments (nothing pushes), win probability from
   the same normal as the spread (internally consistent), fair decimal odds, and a trigger at
   line ± 1.5 pts.

## What is blocked, and why it stays blocked

| Gap | Consequence |
|---|---|
| No odds feed | no CLV, no ROI, no stake sizing (0% stake is the policy, not a placeholder), gates G-02/G-05/G-09 unevaluable |
| No player-level data (unreachable `stats.nba.com`) | injury **impact**, props, prop combos, same-player correlation: blank |
| No game-level results history | σ/HCA/correlations cannot be re-fit point-in-time; gate G-07 is AT-RISK by construction |
| Injury reports are same-day | a T-3 line is structurally availability-blind, so Tier A is suppressed for the whole slate |
| Owner decisions pending | 11 thresholds are unratified; leaderboard rewards are 100% unallocated until gates pass |

Nine strategies are registered; none is promoted, because promotion requires measurement and
the first bet has not settled. That is the design working, not a missing feature.

## Data window

`as_of 2026-11-13`. Slate `2026-11-13 → 2026-11-16` (31 games: 9 Emirates NBA Cup group games
+22 regular-season). Sealed pick window = `2026-11-14 → 2026-11-16` (22 games); today's games
stay on the site as the calibration set because their injury report was already hours old when
this was built. Snapshots are point-in-time captures, not live feeds — read `meta.as_of` before
trusting any number, and see [the sources page](pages/sources.html) for retrieval timestamps.

## Repo conventions

* Branch per session, work only inside your claimed scope in `COORDINATION.md`; small commits,
  `git pull --rebase` before pushing.
* `data/raw/**` is the source of truth for the site: change the snapshot, then rebuild. Never
  hand-edit `data/site.json` or the HTML — CI fails when they disagree with a rebuild.
* Flagged and unverified items do **not** block a merge; they block a *promotion*.
* Suggestions are a queue, not a to-do list: nothing in `suggestions/SUGGESTIONS.json` is
  implemented until the owner marks it accepted.
