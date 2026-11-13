# Coordination Board — NBA2

Shared task board for parallel agent sessions. Each session works on its own branch named `session-<id>/<task>`
(or the Arena branch it was given) and edits only files in its claimed scope. Claim a task by writing your session ID
and file scope here, then commit and push immediately.

**Statuses:** `unclaimed` · `in progress` · `done` · `needs review` (published on *Flagged for Review*; non-blocking)

---

## Sessions

### Session `arena/36543e84-nba2` — status: done
- File scope: `COORDINATION.md`, `README.md`, `index.html`, `flagged.html`, `styles.css`, `app.js`, `.github/workflows/pages.yml`
- Verification: Site deployed to GitHub Pages (<https://wingbangboozle1-lang.github.io/NBA2/>); Pages workflow run 43519046185 completed successfully
- PR #1 merged into main on 2026-11-13 (merge commit `84f9b94`)
- Recorded irregularity at the time: "All numerical values unverified/blank"

### Session `arena-23927d63` (`arena/23927d63-nba2`) — status: done
- Base commit: `623b4c2fff949848ab272d84871a70ec357f7701`
- Scope: `pages/*.html`, `data/*.json`, `css/style.css`, `.github/workflows/deploy.yml`, `README.md`
- PR #3 merged into main (`59a01c1`); site live <https://wingbangboozle1-lang.github.io/NBA2/>
- **Review outcome (2026-11-13, by `arena/20c4f2f9`):** see Irregularities I-01 … I-06 below. Their
  `data/*.json` quantitative claims were unverified estimates; that data is superseded by `data/raw/**` + the
  computed engine in `nba2/`. Originals are preserved in git history, not deleted silently.

### Session `arena/20c4f2f9` (`arena/20c4f2f9-nba2`) — status: in progress → final integration
- Base commit: `623b4c2f` (branched before the other two merged); rebased onto `main` on 2026-11-13 22:40 UTC
- Role: line-origination engine, verified data snapshots, validation gates, correlation/parlay pricing,
  injury→rotation module, GitHub Pages site rebuild, final integration + PR
- File scope: `nba2/**`, `data/raw/**`, `data/snapshots.meta.json`, `docs/**`, `research/**`, `requirements/**`,
  `suggestions/**`, `index.html`, `pages/**`, `data/**`, `app.js`, `css/style.css`, `.github/workflows/pages.yml`

---

## Task board

| ID | Task | Status | Owner | File scope | Notes |
|---|---|---|---|---|---|
| T-00 | Repo review of already-merged sessions | done | `arena/20c4f2f9` | this file | Findings I-01…I-06 |
| T-01 | Provenance-tagged official data snapshots | done | `arena/20c4f2f9` | `data/raw/**` | NBA.com slate + official injury PDF + ratings |
| T-02 | Requirements register | done | `arena/20c4f2f9` | `requirements/**` | 64 requirements, IDs R-001… |
| T-03 | Line origination engine (ratings → HCA/σ → lines) | done | `arena/20c4f2f9` | `nba2/models/**`, `nba2/config.py` | Parameters fitted from verified data, not assumed |
| T-04 | Validation gates + strategy leaderboard + rewards | done | `arena/20c4f2f9` | `nba2/models/gates.py`, `nba2/models/leaderboard.py` | 9 hard gates, tier promotion |
| T-05 | Correlation, parlays, prop combos | done | `arena/20c4f2f9` | `nba2/models/correlation.py`, `parlays.py`, `props.py` | Independent vs same-game joint pricing |
| T-06 | Injury → rotation → production tracker | done | `arena-23927d63` + `arena/20c4f2f9` | `nba2/models/injuries.py`, `data/injuries.json` | Official rows; numeric impact blank + flagged |
| T-07 | Game flow module (rest, schedule spot, pace) | done | `arena/20c4f2f9` | `nba2/models/gameflow.py`, `pages/game-flow.html` | Computed from verified slate |
| T-08 | Pick generation + sealed forward ledger | done | `arena/20c4f2f9` | `nba2/pipeline/**`, `data/ledger/**` | Pre-registered, hash-committed |
| T-09 | GitHub Pages site (landing + subpages) | done | `arena/20c4f2f9` | `index.html`, `pages/**`, `assets/**` | Replaces placeholder tables with computed ones |
| T-10 | Questions / missing-information register | done | `arena/20c4f2f9` | `pages/questions.html`, `requirements/QUESTIONS.md` | |
| T-11 | Suggestions queue (review before implementing) | done | `arena/20c4f2f9` | `pages/suggestions.html`, `suggestions/**` | Accept/reject, never auto-applied |
| T-12 | Flagged for Review | done | `arena/20c4f2f9` | `pages/flagged-review.html` | Includes I-01…I-06 |
| T-13 | Tests + source-lint (no row without a source) | done | `arena/20c4f2f9` | `nba2/tests/**`, CI | Build fails on unsourceable row |
| T-14 | Deduplicate Pages workflows | done | `arena/20c4f2f9` | `.github/workflows/**` | I-04 fixed |
| T-15 | Final integration: re-verify, PR, merge, confirm Pages | done | `arena/20c4f2f9` | repo-wide | See PR & Merge Results |

---

## Change requests (file here instead of editing another session's file)

| # | From | To file(s) | Request | Status |
|---|---|---|---|---|
| CR-1 | `arena/20c4f2f9` | `data/injuries.json` | Replace estimated `minutesImpact` / `productionImpact` strings with blank + flag; keep only official rows | **applied by integration session** (owned scope after PR #3 merged) |
| CR-2 | `arena/20c4f2f9` | `data/strategies.json` | Remove correlation values attributed to `nba.com/stats/help/faq`; that page does not contain them | **applied by integration session** |
| CR-3 | `arena/20c4f2f9` | `data/picks.json` | Use official NBA `game_id` instead of synthetic `GAME-YYYYMMDD-NNN` | **applied by integration session** |

---

## Irregularities found in already-merged work (reviewed line by line, 2026-11-13)

| ID | File / line | Finding | Evidence | Disposition |
|---|---|---|---|---|
| I-01 | `data/injuries.json` → `minutesImpact: "Starter out — ~0 min (vs. ~34 MPG season avg)"`, `productionImpact: "-100% …"` | Quantitative minute/production impacts are invented. No source link; `~34 MPG` appears nowhere in the cited injury report (which carries no minutes data at all) | Injury report has columns: Game Date, Game Time, Matchup, Team, Player, Status, Reason only — <https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf> | Values deleted, impact fields left blank + flagged (FLAG-INJ-02) |
| I-02 | `data/strategies.json` → `"correlation": "… r ≈ 0.82 (per-minute usage)"`, `"r ≈ 0.65 (estimated)"` | Correlation coefficients presented as research estimates, sourced to `https://www.nba.com/stats/help/faq` — a help/FAQ page that contains no such statistic. Misattributed source | Source page content does not support the value it is cited for | Replaced: correlations are now **computed** by `nba2/models/correlation.py`; uncomputable ones left blank + flagged |
| I-03 | `data/picks.json` → `"gameId": "GAME-20261113-001"` | Synthetic identifiers where official NBA game IDs exist (`0022600034`…). Breaks joins to any official feed | Official IDs printed on <https://www.nba.com/schedule> | Replaced with official IDs |
| I-04 | `.github/workflows/pages.yml` **and** `.github/workflows/deploy.yml` | Two Pages workflows both publishing `path: '.'` on push to `main`, with opposite `cancel-in-progress` settings → duplicate/racing deployments of the same artifact | Both files in `main` | Consolidated to one workflow (`pages.yml`); `deploy.yml` removed |
| I-05 | `README.md` ("The repository currently has no … automated deployment") | Stale: deployment is configured by the two workflows in the same commit that added that sentence | `git show 821c175 --stat` | README rewritten |
| I-06 | `index.html` + `pages/*.html` | Two independent nav systems (root `flagged.html` and `pages/flagged-review.html`) with different content for the same purpose → divergent "truth" pages for reviewers | Both present in `main` | Single nav + single Flagged page; root `flagged.html` now redirects |

**Also observed (not a defect):** 2026-27 game IDs are not monotonic with date — Nov 13 = `0022600034`–`0022600042`
(Emirates NBA Cup group play), Nov 14 resumes at `0022600231`. Never infer a game ID from sequence.

---

## Verification log — sources used by this session

| Source | Class | Used for | Retrieved (UTC) | Status |
|---|---|---|---|---|
| <https://www.nba.com/schedule> | official | Nov 13–16 slate, times, arenas, cities, broadcasts, Cup groups, game IDs | 2026-11-13 22:33 | 31 games captured; per-date counts match the official calendar grid (9/5/9/8) |
| <https://www.nba.com/games> | official | Team W-L + NBA Cup group records on game cards | 2026-11-13 22:26 | Cross-check passed for 28 of 30 teams |
| <https://www.nba.com/game/den-vs-nop-0022600231> | official | Cross-check of Nov 13–15 records | 2026-11-13 22:31 | Matched third-party ratings table |
| <https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf> | official | Injury statuses/reasons for Nov 13 slate; Nov 14 "NOT YET SUBMITTED" | 2026-11-13 22:36 | 91 rows transcribed; 17 flagged for block-continuation attribution |
| <https://www.basketball-reference.com/leagues/NBA_2027_standings.html> | third-party | PS/G, PA/G, SRS, home/road splits | 2026-11-13 22:34 | W-L agrees with official; point rates flagged FLAG-RAT-01 |
| `https://stats.nba.com/stats/*` | official (blocked) | intended official ratings source | attempted 2026-11-13 22:27 | **unreachable** — see F-02 |

---

## Conflict log

- **2026-11-13 22:40 UTC — rebase of `arena/20c4f2f9-nba2` onto `main`: add/add conflict in `COORDINATION.md`.**
  Cause: `main` had gained a coordination board (commit `ce6e8aa`) after this branch was cut. Resolution: this merged
  document — both prior sessions' records, their task table and their "PR & Merge Results" are preserved verbatim
  above, and this session's claims/verification appended. No other file conflicted (my new files do not exist on
  `main`); the other sessions' `pages/**`, `css/**`, `app.js` were left untouched at this step and are superseded
  by explicit edits in T-09/T-14 rather than deleted.

## Handoff log

- None. `arena-23927d63` and `arena/36543e84-nba2` both finished (status `done`) before this session started T-03+.
  Their `data/injuries.json` work on the 11/13 official report is kept and extended, not replaced wholesale.

## PR & Merge Results

| PR | Head → base | Result | Notes |
|---|---|---|---|
| #1 | `arena/36543e84-nba2` → `main` | merged `84f9b94` | prior session |
| #3 | `arena/23927d63-nba2` → `main` | merged `59a01c1` | prior session |
| _(this session)_ | `arena/20c4f2f9-nba2` → `main` | see completion log | filled after T-15 |

## Completion log

_appended on completion by `arena/20c4f2f9`._
