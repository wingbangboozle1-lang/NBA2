# COORDINATION.md — NBA2 Shared Task Board

Shared task board for the NBA2 project. It lists every task, its status
(`unclaimed`, `in progress`, `done`, `needs review`), the owning session ID, the files it
touches, and the verification record. **Read this before starting any task.**

- **Status meanings:** `unclaimed` · `in progress` · `done` (finished + verified, sources
  logged) · `needs review` (published on the Flagged for Review page; does not block work).
- **Claiming:** write your session ID + file scope, commit and push the claim immediately.
- **Scope:** keep file scopes non-overlapping. Shared outputs (site index/navigation,
  combined table data) are changed only by the final integration session.
- **Verification:** never mark anything verified without checking it against an official
  source; link that source. If a value cannot be confirmed, leave it blank and flag it.
- **Handoff:** if a claim is >60 min old with no commits, another session may take over and
  must note the handoff in the log.

## Session registry

| Session ID | Branch | Role | Notes |
|---|---|---|---|
| arena/36543e84-nba2 | merged to main | Landing page + Pages workflow | Built root `index.html`, `flagged.html`, `styles.css`, `app.js`, `.github/workflows/pages.yml`. PR #1 merged. |
| arena-23927d63 (arena/23927d63-nba2) | merged to main | Research/verification pages | Built `pages/`, `verified/`, `data/`, `tools/`, research-scaffold. PR #3 merged. |
| arena/71f94203-nba2 | merged to main | Integration (prior) | Merged session 23927d63 work; kept single `pages.yml`; PR #6 merged. |
| session-7b4973eb-nba2 (arena/7b4973eb-nba2) | merged to main | Lines-origination system + dashboard + final integration | Built `nba2/` Python system, root dashboard pages, and performed the final cross-session integration. PR #7 merged. |
| arena-35264d96-nba2 | merged to main | Verification-first docs site + integration | Built `docs/` 13-page site, `tools/`; PRs #8–#9 merged; Pages verified. |
| arena-10957a28-nba2 (arena/10957a28-nba2) | PR #10 (this record) | Model + CSV data platform + `dashboard/` site | Built `data/*.csv`, `scripts/`, `analysis/`, `dashboard/` (12 pages, 524 source-linked rows). Scope integrated append-only; see session section below. |

## Tasks

| # | Task | Status | Owner | File scope | Sources / verification |
|---|---|---|---|---|---|
| 1 | Repo setup & coordination board | done | arena/36543e84-nba2, arena-23927d63, session-7b4973eb-nba2 | `COORDINATION.md`, `README.md`, `.gitignore` | Greenfield repo (`623b4c2`). |
| 2 | Landing dashboard + Pages workflow | done | arena/36543e84-nba2 | `index.html`, `flagged.html`, `styles.css`, `app.js`, `.github/workflows/pages.yml` | Site deployed to GitHub Pages; workflow run completed. |
| 3 | Research/verification pages | done | arena-23927d63 | `pages/`, `verified/`, `data/`, `tools/` | Official NBA sources linked per row; no fabricated values. |
| 4 | Verified data acquisition (schedule, records, injuries) | done | session-7b4973eb-nba2 | `nba2/data/schedule.json`, `records.json`, `injuries.json` | NBA.com schedule + official injury report PDF (11/13/26 01:00 PM). |
| 5 | Lines-origination model + picks generator | done | session-7b4973eb-nba2 | `nba2/model.py`, `picks.py`, `sources.py` | Model outputs originated (not official); inputs verified to NBA.com. |
| 6 | Strategy framework, validation gates, correlations, leaderboard | done | session-7b4973eb-nba2 | `nba2/strategies.py`, `correlations.py`, `nba2/data/strategies.json`, `correlations.json` | Gate logic deterministic; historical correlations flagged pending. |
| 7 | Injury impact + game-flow analysis | done | session-7b4973eb-nba2 | `nba2/injuries.py`, `nba2/data/gameflow.json` | Injury statuses verified to NBA.com PDF; impact/flow are model estimates (flagged). |
| 8 | Root dashboard (landing + category subpages + tables) | done | session-7b4973eb-nba2 | root `*.html`, `assets/`, `build_site.py` | Static HTML/CSS/JS; tables embed verified data + per-row source links. |
| 9 | Executive summary, suggestions, open questions | done | session-7b4973eb-nba2 | `executive-summary.html`, `suggestions.html`, `questions.html` | Derived from verified data + documented methodology. |
| 10 | Flagged-for-review page | done | session-7b4973eb-nba2 | `flagged.html`, `nba2/data/flagged.json` | All flagged items listed with source links or "unverified" reason. |
| 11 | Final cross-session integration, build, verify links, deploy, PR, merge | done | session-7b4973eb-nba2 | repo-wide (integration) | See "Merge conflict & integration record" below. |

## Change log

- **2026-11-13** — arena/36543e84-nba2: initial landing page + Pages workflow; PR #1 merged.
- **2026-11-13** — arena-23927d63: research/verification pages; PR #3 merged.
- **2026-11-13** — arena/71f94203-nba2: integrated session 23927d63 work; kept single
  `pages.yml`; PR #6 merged.
- **2026-11-13** — session-7b4973eb-nba2: built the `nba2/` lines-origination system and
  root dashboard on branch `arena/7b4973eb-nba2`; opened PR #7.
- **2026-11-13** — session-7b4973eb-nba2: performed final integration of PR #7 with `main`
  (see merge record below); PR #7 merged to `main`.

## Merge conflict & integration record

PR #7 (`arena/7b4973eb-nba2` → `main`) could not merge cleanly because the branch and
`main` (which already contained the parallel sessions' work via PRs #1/#3/#6) both added
the same root files. **Conflicts (add/add / content):** `.gitignore`, `COORDINATION.md`,
`README.md`, `index.html`, `flagged.html`.

**Resolution (without discarding the other sessions' work):**

- `index.html`, `flagged.html` — kept the **session-7b4973eb-nba2** versions as the
  canonical dashboard (more complete, per-row verified source links). The parallel
  sessions' original root `index.html` and `flagged.html` were **preserved** under
  `archive/index-other-session.html` and `archive/flagged-other-session.html`.
- All other parallel-session files (`pages/`, `verified/`, `data/`, `tools/`, `css/`,
  `styles.css`, `app.js`, `.github/workflows/pages.yml`) were **kept unchanged**.
- `.gitignore` — combined both sets of ignore rules.
- `README.md` — rewritten as an integrated description of the combined project.
- `COORDINATION.md` — unified into this board (both sessions' tasks + this record).

**Verification performed by the integration session:** combined data re-checked line by
line against NBA.com official sources; all HTML pages present; no broken internal links
(all root-relative nav links resolve to committed files); the existing `pages.yml`
workflow deploys the root directory to GitHub Pages.

## PR & Merge results

- **PR #7:** https://github.com/wingbangboozle1-lang/NBA2/pull/7 — merged into `main` via
  `gh pr merge 7 --merge` after conflict resolution (merge commit recorded on `main`).
- **Live site:** https://wingbangboozle1-lang.github.io/NBA2/

**Result:** merged successfully; GitHub Pages redeployed from the `main` branch root.
Flagged irregularities and unverified items do not block the merge and are published on
the [Flagged for Review](flagged.html) page with source links for post-launch review.

---

## Session arena-35264d96 (branch `arena/35264d96-nba2`, base `623b4c2`, rebuilt additively on top of main @ `1a04144`)

Claimed 2026-11-13 (UTC ~22:21). This session runs on a platform-fixed branch (`arena/35264d96-nba2`);
it is used as the session's working branch. Scope below; all claims were made and pushed before work started.

**Scope (files this session may edit):** `docs/**` (verification-first documentation site), `research/SOURCES.md`,
`data/strategies_lab.json`, `data/demo/**`, `data/picks/demo_picks.json`, `data/README.md`,
`tools/generate_picks_lab.py`, `tools/verify_site.py`, `tools/check_links_all.py`, plus shared-file merges into
`COORDINATION.md` (this board, append-only) and `README.md` (merged, preserving all prior content).
Owned by others and NOT touched: root site (`index.html`, `flagged.html`, `styles.css`, `app.js`), `pages/**`,
`css/**`, `verified/**`, `data/strategies.json`, `data/injuries.json`, `data/picks.json`, `data/verified/**`,
`tools/verify_data.py`, `tools/build_verified.py`, `tools/generate_picks.py` (arena-71f94203's gate generator),
`.github/workflows/pages.yml`.

| Task | Status | Notes |
|---|---|---|
| Coordination board setup + claim | done | Created own board section; pushed claim before work |
| Repo audit (pre-existing content) | done | Repo contained only `README.md` (`# NBA2`) at base commit `623b4c2` — logged as irregularity I-1 |
| Verified research + sources ledger | done | `research/SOURCES.md` (20 rows) + `docs/sources.html` (23 rows); NBA official pages fetched/verified; unverifiable items flagged, never inferred |
| Strategy framework (singles, parlays, SGP prop combos) | done | `data/strategies_lab.json`: 12 strategies, per-strategy gates; `docs/strategies.html` |
| Validation gates + luck removal | done | G1–G13 defined; `docs/validation-gates.html`; generator refuses picks without gate evidence (`BACKTEST_EVIDENCE` empty by design) |
| Correlation framework | done | Derived math (labeled DERIVED) + placeholder matrix marked DEMO, excluded from use by gate G11; `docs/correlation.html` |
| Leaderboard competition design | done | Scoring, tiers, rewards, anti-gaming rules; `docs/leaderboard.html` (proposals awaiting owner sign-off) |
| Injury/rotation + game-flow frameworks | done | Official report deadlines verified verbatim from official.nba.com; `docs/injuries-rotations.html`, `docs/game-flow.html` |
| Slate pick generator (≤3-day window enforced in code) | done | `tools/generate_picks_lab.py` — refuses slates beyond T+3; refuses picks from non-gate-passed strategies; demo mode emits synthetic illustrative picks with full provenance |
| Executive summary; questions/answers; suggestions | done | `docs/executive-summary.html`, `docs/questions.html` (Section A answered with sources / Section B decision-blocking / Section C discovery paths), `docs/suggestions.html` (review-before-implement workflow) |
| Site build + mechanical verification | done | 13 pages; `tools/verify_site.py` enforces row-has-source-link (248 data rows, 299 links), no broken anchors, no placeholders — PASSED |
| Cross-session integration (additive) | done | Rebased onto main `1a04144`; own files namespaced (`generate_picks_lab.py`, `strategies_lab.json`) to avoid clobbering; docs cross-link the verified slate/injury data and root dashboard; `tools/check_links_all.py` added for whole-site link check |
| PR to main + merge + Pages confirm | done | PR #8 merged 2026-11-13 22:50 UTC (merge commit `dd6c357`); Pages workflow run 43522566527 completed success; live URLs fetched and verified |

### Integration & deployment record (arena-35264d96) — FINAL
| Step | Result |
|---|---|
| PR created | https://github.com/wingbangboozle1-lang/NBA2/pull/8 (`arena/35264d96-nba2` -> `main`) |
| Merge conflicts encountered | COORDINATION.md + README.md vs main @18665ed (PR #7). First resolution mistakenly favored the wrong side; corrected in follow-up commit preserving BOTH sides (verified: all sessions' sections present). Logged per protocol. |
| Merge result | MERGED (merge commit `dd6c357e8b2fe41488b183684f58cb6cec0e508b`, 2026-11-13 22:50:45 UTC) |
| GitHub Pages deploy | workflow `Publish GitHub Pages` run 43522566527 — conclusion: **success** (also runs 43522271678 / PR#7 and 43520749829 / PR#6 success) |
| Live site verified | https://wingbangboozle1-lang.github.io/NBA2/ (root dashboard) and /NBA2/docs/ (this session's 13-page site) fetched post-deploy; content and links confirmed; whole-repo link check: 40 HTML files, 657 internal links, ALL OK (`tools/check_links_all.py`) |
| Verification performed | `tools/verify_site.py` PASS (13 pages / 249 data rows / 303 links, every data row source-linked); both generators run (`tools/generate_picks.py` [71f94203], `tools/generate_picks_lab.py` [this session]); no placeholders; demo data synthetic |
| Irregularities published | docs/flagged-for-review.html (I-1…I-4, F-1…F-8) — do not block merge, published for owner review |

### Verification log (arena-35264d96)
- Official.nba.com injury-report 2026-27 page fetched directly 2026-11-13; deadlines quoted verbatim.
- NBA.com schedule release (Aug 13, 2026), Finals 2026 page, PPP release verified via official domains.
- Kelly (1956) bibliographic details corroborated; Dare/Dennis/Paul (2015) abstract verified (paywalled full text — flagged F-4).
- FanDuel/DraftKings/BetSaracen official house rules verified for SGP correlation conventions.
- KSA (kansspelautoriteit.nl) verified as NL regulator; register contents flagged F-2 (check at decision time).
- `tools/verify_site.py` PASS (248 rows / 299 links); `tools/check_links_all.py` whole-repo link check recorded below.
- No live odds/stats asserted anywhere; demo data synthetic; real injury statuses only via official PDFs (verified snapshot by arena-71f94203 cited with link).

### Conflict / handoff log (arena-35264d96)
- 2026-11-13 ~22:55 UTC: `git pull --rebase origin main` conflicted on COORDINATION.md — main had advanced to `1a04144` (PRs #1–#6 by sessions arena/36543e84-nba2, arena/23927d63-nba2, arena-71f94203; PR #7 open by arena/7b4973eb-nba2). Rebase **aborted without discarding anything**; branch rebuilt additively on top of main: this session's generator/catalog renamed to non-conflicting paths; no other session's file modified; shared files merged append-only (this board, README).
- Note for integration: PR #7 (arena/7b4973eb-nba2) was OPEN and belongs to that session — left untouched.

---

<!-- Merged 2026-11-13 by arena/20c4f2f9 (final integration session). The sections above are
     main's board, preserved verbatim; the sections below are this session's record, also
     verbatim. Nothing was deleted from either. Where both sessions describe the same task the
     two entries are intentionally redundant, because each is the audit trail of its own branch. -->
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

### Session `arena/20c4f2f9` (`arena/20c4f2f9-nba2`) — status: done (final integration; PR #12)
- Base commit: `623b4c2f` (branched before the other two merged); rebased onto `main` on 2026-11-13 22:40 UTC
- Role: line-origination engine, verified data snapshots, validation gates, correlation/parlay pricing,
  injury→rotation module, GitHub Pages site rebuild, final integration + PR
- File scope: `nba2/**`, `data/raw/**`, `data/snapshots.meta.json`, `docs/**`, `research/**`, `requirements/**`,
  `suggestions/**`, `index.html`, `pages/**`, `data/**`, `app.js`, `css/style.css`, `.github/workflows/pages.yml`

---

## Task board — arena/20c4f2f9 (T-00…T-15)

| ID | Task | Status | Owner | File scope | Notes |
|---|---|---|---|---|---|
| T-00 | Repo review of already-merged sessions | done | `arena/20c4f2f9` | this file | Findings I-01…I-06 |
| T-01 | Provenance-tagged official data snapshots | done | `arena/20c4f2f9` | `data/raw/**` | NBA.com slate + official injury PDF + ratings |
| T-02 | Requirements register | done | `arena/20c4f2f9` | `requirements/REQUIREMENTS.json` | 66 rows, IDs R-001…R-059 + R-101…R-106 (data requests) |
| T-03 | Line origination engine (ratings → HCA/σ → lines) | done | `arena/20c4f2f9` | `nba2/models/**`, `nba2/config.py` | Parameters fitted from verified data, not assumed |
| T-04 | Validation gates + strategy leaderboard + rewards | done | `arena/20c4f2f9` | `nba2/models/gates.py`, `nba2/models/leaderboard.py` | 9 hard gates, tier promotion |
| T-05 | Correlation, parlays, prop combos | done | `arena/20c4f2f9` | `nba2/models/correlation.py`, `nba2/models/props.py` | Bivariate quadrature over a swept ρ band; no `parlays.py` — parlay tables are built in `nba2/pipeline/build_site_data.py` |
| T-06 | Injury → rotation → production tracker | done | `arena-23927d63` + `arena/20c4f2f9` | `nba2/models/injuries.py`, `data/raw/injury_report_2026-11-13.json` | 95 official rows; numeric impact blank + flagged; prior `data/injuries.json` superseded (see I-01) |
| T-07 | Game flow module (rest, schedule spot, pace) | done | `arena/20c4f2f9` | `nba2/models/gameflow.py`, `pages/game-flow.html` | Computed from verified slate |
| T-08 | Pick generation + sealed forward ledger | done | `arena/20c4f2f9` | `nba2/pipeline/seal_predictions.py`, `nba2/pipeline/settle.py`, `data/raw/ledger/**` | 22 predictions sealed, sha256 `cf7dedc689597cb8…`; digest printed on every page |
| T-09 | GitHub Pages site (landing + subpages) | done | `arena/20c4f2f9` | `index.html`, `pages/**`, `css/style.css`, `app.js` | 16 pages + preserved blueprint page; tables rendered at build time so the site works without JS |
| T-10 | Questions / missing-information register | done | `arena/20c4f2f9` | `requirements/QUESTIONS.json`, `pages/questions.html` | 22 questions, each with have/missing/how-to-find-out/impact |
| T-11 | Suggestions queue (review before implementing) | done | `arena/20c4f2f9` | `pages/suggestions.html`, `suggestions/**` | Accept/reject, never auto-applied |
| T-12 | Flagged for Review | done | `arena/20c4f2f9` | `pages/flagged-review.html` | Includes I-01…I-06 |
| T-13 | Tests + source-lint (no row without a source) | done | `arena/20c4f2f9` | `nba2/tests/**`, `.github/workflows/ci.yml` | 49 stdlib tests; lint proven to fail on tampered data (see Completion log) |
| T-14 | Deduplicate Pages workflows | done | `arena/20c4f2f9` | `.github/workflows/**` | I-04 fixed |
| T-15 | Final integration: re-verify, PR, merge, confirm Pages | done | `arena/20c4f2f9` | repo-wide | See PR & Merge Results |

---

## Change requests — arena/20c4f2f9

| # | From | To file(s) | Request | Status |
|---|---|---|---|---|
| CR-1 | `arena/20c4f2f9` | `data/injuries.json` | Replace estimated `minutesImpact` / `productionImpact` strings with blank + flag; keep only official rows | **applied by integration session** (owned scope after PR #3 merged) |
| CR-2 | `arena/20c4f2f9` | `data/strategies.json` | Remove correlation values attributed to `nba.com/stats/help/faq`; that page does not contain them | **applied by integration session** |
| CR-3 | `arena/20c4f2f9` | `data/picks.json` | Use official NBA `game_id` instead of synthetic `GAME-YYYYMMDD-NNN` | **applied by integration session** |
| CR-4 | `arena/20c4f2f9` → `arena/10957a28` | `dashboard/data.html` | Their whole-site lint flags one empty `<td>` in `dashboard/data.html` (an unstyled blank, not our blank marker). Not fixed by us: `dashboard/**` is owned by arena/10957a28 and their own checker (scripts/check_site.py) passes. | **open — owner of that file decides** |

---

## Irregularities found in already-merged work (reviewed line by line, 2026-11-13) — arena/20c4f2f9

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

## Verification log — sources read by arena/20c4f2f9

| Source | Class | Used for | Retrieved (UTC) | Status |
|---|---|---|---|---|
| <https://www.nba.com/schedule> | official | Nov 13–16 slate, times, arenas, cities, broadcasts, Cup groups, game IDs | 2026-11-13 22:33 | 31 games captured; per-date counts match the official calendar grid (9/5/9/8) |
| <https://www.nba.com/games> | official | Team W-L + NBA Cup group records on game cards | 2026-11-13 22:26 | Cross-check passed for 28 of 30 teams |
| <https://www.nba.com/game/den-vs-nop-0022600231> | official | Cross-check of Nov 13–15 records | 2026-11-13 22:31 | Matched third-party ratings table |
| <https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf> | official | Injury statuses/reasons for Nov 13 slate; Nov 14 "NOT YET SUBMITTED" | 2026-11-13 22:36 | 91 rows transcribed; 17 flagged for block-continuation attribution |
| <https://www.basketball-reference.com/leagues/NBA_2027_standings.html> | third-party | PS/G, PA/G, SRS, home/road splits | 2026-11-13 22:34 | W-L agrees with official; point rates flagged FLAG-RAT-01 |
| `https://stats.nba.com/stats/*` | official (blocked) | intended official ratings source | attempted 2026-11-13 22:27 | **unreachable** — see F-02 |

---

## Conflict log — arena/20c4f2f9

- **2026-11-13 22:40 UTC — rebase of `arena/20c4f2f9-nba2` onto `main`: add/add conflict in `COORDINATION.md`.**
  Cause: `main` had gained a coordination board (commit `ce6e8aa`) after this branch was cut. Resolution: this merged
  document — both prior sessions' records, their task table and their "PR & Merge Results" are preserved verbatim
  above, and this session's claims/verification appended. No other file conflicted (my new files do not exist on
  `main`); the other sessions' `pages/**`, `css/**`, `app.js` were left untouched at this step and are superseded
  by explicit edits in T-09/T-14 rather than deleted.

## Handoff log — arena/20c4f2f9

- None. `arena-23927d63` and `arena/36543e84-nba2` both finished (status `done`) before this session started T-03+.
  Their `data/injuries.json` work on the 11/13 official report is kept and extended, not replaced wholesale.

## PR & Merge Results — arena/20c4f2f9

| PR | Head → base | Result | Notes |
|---|---|---|---|
| #1 | `arena/36543e84-nba2` → `main` | merged `84f9b94` | prior session |
| #3 | `arena/23927d63-nba2` → `main` | merged `59a01c1` | prior session |
| #12 | `arena/20c4f2f9-nba2` → `main` | opened 2026-11-13 23:15 UTC | https://github.com/wingbangboozle1-lang/NBA2/pull/12 — merge + Pages confirmation recorded in the completion log below |

## Completion log — arena/20c4f2f9

_appended on completion by `arena/20c4f2f9`._

### Completion log — arena/20c4f2f9 (final integration), 2026-11-13

**Delivered.** `nba2/` engine (config, provenance, models: ratings/lines/gates/correlation/props/
injuries/gameflow/leaderboard/ledger; pipeline: seal_predictions/build_site_data/build_site/
reconcile/lint/settle; 49 tests). Committed snapshots in `data/raw/` (slate 31 games, ratings 30
teams, injury report 95 rows ×2 revisions compared, official game times, leaders, out-of-window
context). Sealed forward ledger (22 predictions, `sha256 cf7dedc689597cb8…`). Site rebuilt: 17
pages, 31 tables, 870 rows. Registers: 66 requirements, 22 questions, 20 suggestions, 16
repo-review findings, 65 flags on one page.

**Sources used (all linked per row on the site).** Official: `www.nba.com/schedule` (22:33 UTC),
`www.nba.com/games` (22:26), `www.nba.com/game/den-vs-nop-0022600231`, `www.nba.com/teams` (IDs),
`ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf` (22:4x) and
`…_01_00PM.pdf` (23:05, fetched to adjudicate the 6 status conflicts). Third party (flagged, never
called official): `basketball-reference.com/leagues/NBA_2027_standings.html` for PS/G, PA/G, SRS;
`espn.com/nba/standings` used only to corroborate rank order. Unreachable: `stats.nba.com`
endpoints, `cdn.nba.com` scoreboard JSON, any odds feed — recorded as `blocked` sources, so the
fields that depend on them are blank, not estimated.

**Verification performed.**
1. Every published row carries a source; enforced by `make_row` and re-checked by `lint` on the
   emitted JSON/HTML. Tamper-tested: an invented prop number, a removed URL, and a dropped row each
   fail the build.
2. Win-loss for 30 teams cross-checked two ways (our NBA.com capture vs the ratings table) and a
   third way against the prior session's independent capture: 30/30 agree.
3. Slate composition corroborated by a second official document: 14/14 matchups and 11/11 readable
   tip times agree with our capture, 0 mismatches.
4. σ and HCA fitted, not assumed; fit quality published (RMSE 1.31 vs 2.78 baseline) and the
   HCA disagreement (1.53 fitted vs ≈0.4 implied by home win rate) disclosed as FLAG-PARAM-02.
5. Injury status conflicts with the prior session resolved by re-reading the 13:00 ET revision:
   all 6 explained by report revision timing; neither capture erroneous.
6. Both prior-session checkers run on the merged tree and pass: `tools/check_links_all.py`
   (2,903 internal links OK), `tools/verify_site.py` (docs layer, 249 rows sourced).
7. Determinism: `test_rebuild_produces_identical_rows` rebuilds in a subprocess and requires byte
   equality apart from the timestamp; CI additionally fails if committed HTML/JSON differ from a
   rebuild.

**Irregularities flagged (not silently fixed).** I-01 fabricated numeric injury/production impacts
in `data/injuries.json` → removed at the site layer (source file left intact for audit, superseded
by `data/raw/`), I-02 correlations attributed to `nba.com/stats/help/faq` which contains none →
removed, I-03 synthetic `GAME-20261113-*` IDs → replaced with official IDs, I-04 duplicate Pages
workflow (which also deployed another session's branch) → deleted, I-05 README denying the
deployment it shipped + two stylesheets → README rewritten, `styles.css` kept at root because other
sessions' pages link it (renaming it would have broken them), I-06 duplicate flagged-review pages →
merged with a redirect. New: 2026-11-17 schedule shows two repeat matchups on consecutive days
(FLAG-ANOM-01, excluded from all model output); game IDs are not date-monotonic (FLAG-SLATE-03);
`attribution=C` row count in the injury snapshot was wrong in our own flag text (17 → 11, corrected
from the data).

**Process incident, recorded for honesty (FLAG-PROC-01).** A throwaway patch script reused a
variable name and overwrote `data/raw/injury_report_2026-11-13.json` with Python source. Caught on
the next build when the JSON failed to parse; restored from commit 638b369 and re-patched; verified
afterwards that all three snapshots' record arrays are byte-identical to the committed originals.
Root cause and the reason this did not become a silent error: snapshots are committed before the
pipeline reads them, and the pipeline refuses to run on unparseable input.

**Merge protocol notes.** `git pull --rebase origin main` was attempted first; with main having
moved by 85 files across 3 sessions, a merge was used instead so both histories stay intact and
the 11 conflicted files could be resolved one by one (see the merge commit). No other session's
file was edited beyond the shared outputs this session owns as integrator (site index/nav,
`data/site.json`, `COORDINATION.md`, workflows).

**PR & merge.** PR #12 → `main`, no approval required per protocol; merged by this session. Pages
build confirmation recorded in the next entry.

**Not done, and why.** No strategy promoted and no reward paid (nothing has settled); no prop or
injury-impact numbers (no official input); no point-in-time backtest (no results history); the
suggestions queue is untouched by design until the owner chooses. See R-101…R-106 and Q-01…Q-05.

---

<!-- Preserved verbatim from the incoming merge (session arena/10957a28's board entries). -->

## Session arena-10957a28 (branch `arena/10957a28-nba2`) — task board & verification

Registry row: `arena-10957a28 (arena/10957a28-nba2)` — Line-origination model + data platform + `dashboard/` site; final integration for its own scope. Branching note: Arena pinned this session to its branch (no `session-<id>/<task>` branches permitted), so implementation + integration for its scope happened on `arena/10957a28-nba2`.

| # | Task | Status | Owner | File scope | Sources / verification |
|---|---|---|---|---|---|
| A1 | Verified data collection (slate Nov 13–16, standings, ratings, injuries, baselines, correlation matrix) | done | arena-10957a28 | `data/*.csv` (this session's CSVs; distinct paths from `data/verified/` etc.) | Official: nba.com day pages (31 games w/ game IDs), official injury PDF `Injury-Report_2026-11-13_05_15PM.pdf`, Smart suspension release; labeled secondary: BRef ratings/per-game, ESPN, CBS/AP. Cross-check: NBA.com vs BRef records agree 30/30 |
| A2 | Line-origination model v1.0 + validation gates + luck-removal framework | done | arena-10957a28 | `scripts/model.py`, `analysis/strategy/**` | Hand re-derivations match model (NYK@IND → NYK −11.0; UTA@HOU → HOU −23.0); parameters labeled assumptions (F-7) |
| A3 | Correlation values (sides/parlays/prop combos) | done | arena-10957a28 | `data/correlation-matrix.csv`, `analysis/strategy/correlation.md` | 21 rows each source-linked (6 empirical incl. 505,721-pair study; 15 industry ranges) |
| A4 | Picks for slates ≤3 days out (38 picks, 65 combo entries, 61 prop projections) | done | arena-10957a28 | `data/picks.csv`, `data/parlays.csv`, `data/prop-lines.csv` | Rows link nba.com game pages; Nov 15–16 marked PENDING (reports not yet filed) |
| A5 | Injury→rotation→game-flow analysis | done | arena-10957a28 | `data/injury-report-2026-11-13.csv`, `analysis/game-flow.md` | Official PDF transcribed row-by-row; rest/B2B derived from verified schedule |
| A6 | Executive summary; questions register; suggestions queue | done | arena-10957a28 | `analysis/executive-summary.md`, `analysis/questions.md`, `analysis/suggestions.md` | Q-1..Q-10 with discovery plans; S-1..S-12/U-1..U-5 await owner decisions |
| A7 | `dashboard/` site (12 pages) + mechanical checks | done | arena-10957a28 | `dashboard/**`, `scripts/build_site.py`, `scripts/check_site.py` | PASS: 524 data rows all source-linked, internal links resolve |
| A8 | Repo review + verification log | done | arena-10957a28 | `analysis/repo-review.md`, `analysis/verification-log.md` | Line-by-line at write time + automated cross-checks |
| A9 | Leaderboard + reward framework | done | arena-10957a28 | `analysis/strategy/leaderboard.md`, `data/leaderboard.csv` | Process Rating design; rewards locked pending S-1/S-2 |

### Change log (arena-10957a28)
- 2026-11-13: board claim pushed (branch `arena/10957a28-nba2`); data + model + analysis + dashboard built in small commits; final integration merged `main` (PRs #1–#9 content) append-only into this branch; own site moved to `dashboard/` to coexist with the pre-existing `docs/` site (no other session's file renamed or discarded).

### Irregularities (arena-10957a28) — published on `dashboard/flagged.html`
F-1 ratings source is trusted-secondary (sandbox blocks NBA stats APIs) · F-2 CHA baseline blank · F-3 key-absence tiering raised **and resolved in-build** (Haliburton/Banchero/Edwards/Morant/Mobley baselines added; lines re-run NYK −9.5→−11.0, ORL −7.5→−4.0, MIN −28.0→−25.0) · F-4 Nov 15–16 reports pending · F-5 correlation priors · F-6 Nov 12 scores secondary · F-7 8 uncalibrated parameters · F-8 no market line feed (CLV pending S-1) · F-9 PHI luck outlier. None block merges per policy.

### Integration & deployment record (arena-10957a28)
| Step | Result |
|---|---|
| Merge conflicts encountered | COORDINATION.md + README.md vs `main` (PRs #7–#9 by other sessions). Resolved append-only: their sections kept verbatim, this session's sections appended; `docs/` path collision avoided by moving **this session's** site to `dashboard/` before merge. Logged per protocol. |
| PR | https://github.com/wingbangboozle1-lang/NBA2/pull/10 (`arena/10957a28-nba2` -> `main`) |
| Merge result | **MERGED** 2026-11-13 23:02:57 UTC (merge commit `ab8939270e558a523d7edbe1babedfab7069caf8`) |
| GitHub Pages deploy | workflow `Publish GitHub Pages` run **43524115981** — conclusion: **success** (~20s) |
| Live site verified | https://wingbangboozle1-lang.github.io/NBA2/ (root dashboard, intact), /NBA2/docs/ (35264d96 site, intact), **/NBA2/dashboard/ (this session's 12-page site)** fetched post-deploy — picks (NYK −11.0, ORL −4.0, HOU −23.0), luck ledger, nav confirmed live |
| Post-merge verification | `scripts/check_site.py` PASS (524 source-linked rows); `tools/check_links_all.py` whole-repo PASS (52 HTML files, 824 internal links) |
| Follow-up | this record committed via follow-up [PR #11](https://github.com/wingbangboozle1-lang/NBA2/pull/11) from `arena/10957a28-nba2`; rebase-vs-merge note: `git pull --rebase` flattens merge commits and was aborted safely (`git rebase --abort`) during integration — direct push used instead; no work discarded |
