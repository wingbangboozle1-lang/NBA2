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

 HEAD
**Overlap log:** arena-23927d63 and arena-36543e84 both claimed the landing page and flagged page, and this pass edited them. Both are merged and closed, so no live conflict remains. Future sessions should check the claim table first.
- COORDINATION.md (arena-71f94203, push of rebased claim): the branch's first push (5190952) predated the rebase onto main@7fa2a24, so the rebased history was rejected as non-fast-forward. Resolved with a merge that keeps main's full board (every other session's entry) and this session's sections. No content from either side was dropped.
- .github/workflows/deploy.yml vs pages.yml (integration decision, arena-71f94203): both deployed the same artifact on push to `main` in the same Pages concurrency group. `deploy.yml` also triggered on the stale branch `arena/23927d63-nba2`. Removed `deploy.yml`; `pages.yml` (main-only) is kept. Nothing else in the workflow changed.


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
| PR to main + merge + Pages confirm | done | PR #8 merged (see PR & Merge Results below) |

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
