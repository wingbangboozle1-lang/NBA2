# Current-State Repository Audit — 2026-11-14

Owner: `arena/3b88f22e-nba2`  
Scope: read-only audit of the integrated repository and official-source spot checks; one stale-count correction in `README.md`. No model input, pick, or published data row was edited.

## Executive result

The repository already contains the requested line-origination research, gates, correlation/parlay analysis, injury/game-flow pages, executive summary, open questions, suggestions queue, Flagged for Review page, and GitHub Pages workflows. The current root site is generated from committed snapshots and labels projections as derived rather than official. This audit verified the committed build/tests and re-opened the NBA schedule and the archived official injury PDF.

**The site is an auditable research prototype, not a live or bettable system.** It does not ingest daily data automatically; its snapshot is dated 2026-11-13. As of the audit date (2026-11-14), the available 11/13 injury report still marks 11/14 rows `NOT YET SUBMITTED`, and a request for the expected 11/14 01:00 PM injury-report PDF returned `AccessDenied` in this environment. No injury update was fabricated or substituted. Without a licensed odds feed there is no observed market price, closing-line value (CLV), realized ROI, or justified stake; the displayed stakes remain 0%. Player props and numerical injury impacts are appropriately blank/blocked where required inputs are absent.

## Verified repository/build facts

| Check | Result | Evidence |
|---|---:|---|
| Python unit tests | **55/55 passed** | `python -m unittest discover -s nba2/tests -t . -v` |
| Main-pipeline provenance lint | **PASS** — 915 rows / 33 tables; each row sourced and each blank explained | `python3 nba2/pipeline/lint.py` |
| Docs-site verifier | **PASS** — 13 pages, 249 rows, all source-linked, internal links resolve | `python3 tools/verify_site.py` |
| Whole-repository link scan | **PASS** — 75 HTML files, 3,233 internal links checked | `python3 tools/check_links_all.py` |
| `dashboard/` checker | **PASS** — 12 pages, 524 rows | `python3 scripts/check_site.py` |
| `originated/` verifier | **PASS** — 24/24 checks | `node originated/engine/compute.js && node originated/engine/build.js && node originated/engine/verify.js`; generated artefacts were restored after the check to keep this audit non-invasive |
| Root site source-of-truth row count | **33 sections / 915 rows** | Counted from `data/site.json`; independently agrees with pipeline lint |
| Root page count | **18 HTML files**: root landing page plus 17 `pages/*.html` subpages | File inventory |

The README had stale counts (`31 tables / 870 rows` and `49 tests`). Those three figures were corrected to the observed `33 / 915` and `55`; the page count was clarified as 18 total (17 subpages plus landing page). These are documentation corrections only. The automated lints check that rows carry source references, flags, and working links; they do not fetch and semantically re-derive all 915 published values. This audit likewise did not repeat a manual source-by-source check of every value. Prior session verification logs describe their own checks, but those are not a substitute for a current full factual re-audit.

## Official-source spot checks

1. **Schedule:** opened the NBA's live [official schedule](https://www.nba.com/schedule) (reviewed 2026-11-14). The rendered page showed the 2026-11-13 through 2026-11-16 day groupings as 9, 5, 9, and 8 games respectively. The committed snapshot `data/raw/slate_2026-11-13_to_11-16.json` carries 31 game records and per-game NBA URLs; the game-count totals agree. The same page rendered matching official matchups and game IDs in the sampled dates. The snapshot is still only as-of 11/13; this check does not claim the committed page has been refreshed.
2. **Injuries:** opened the [official NBA injury report PDF, 2026-11-13 04:15 PM ET](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf). In the inspected rows, the PDF confirms Jimmy Butler III was listed for Golden State with `Out — Right ACL Repair / Surgery`, Ben Simmons for Sacramento with `Out — Right Achilles Tendon Repair / Surgery`, and Maxime Raynaud for Sacramento with `Out — Right Patella Subluxation`. It also explicitly marks the listed 11/14 teams `NOT YET SUBMITTED`. These details agree with the corrected current root injury records and the archived snapshot for the rows inspected. The report cannot be used to assert 11/14 availability.
3. **Fresh 11/14 injury report:** attempted to open [the expected 2026-11-14 01:00 PM ET PDF URL](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_00PM.pdf). The official host returned `AccessDenied`; therefore no 11/14 statuses were verified from that URL in this audit. This is explicitly an access failure, not evidence that no report exists.

## Irregularities and limitations for review

- **Snapshot freshness / automation — open.** The root data manifest is as-of 2026-11-13, although this audit is 2026-11-14. The requirement register says daily ingestion and 13:00 ET injury refresh are not started. The current GitHub Pages workflow deploys repository files but does not acquire fresh NBA inputs. Required next step: add a scheduled, monitored runner that fetches only official NBA schedule/injury/stat sources, timestamps immutable snapshots, fails closed on a missing/stale report, rebuilds, and publishes only after provenance checks pass. Until then, treat the current slate and injury context as a dated snapshot, not a live slate feed.
- **Odds/history/player data — blocked, not guessed.** No licensed market feed or historical market prices exist in the repository; player-level minutes/usage/on-off and multi-season point-in-time results are also absent. Consequently CLV/ROI, trustworthy prop lines, impact minutes, and empirical correlation calibration cannot be claimed. Acquire licensed/official data before enabling stake sizing, leaderboard rewards, or prop recommendations.
- **Official-only sourcing requirement — partly unmet by declared design.** Most raw schedule and injury rows reference NBA sources, but team scoring/rating inputs include a trusted-secondary Basketball-Reference source in `data/raw/team_ratings_2026-11-13.json`. The repository labels that source as non-official and cross-checks win-loss records, but that does **not** make every rating field officially sourced. Keep the affected ratings explicitly third-party/flagged or replace them with a reachable official snapshot; do not describe those fields as NBA-verified.
- **Multiple historical surfaces — usability risk.** The repo retains legacy `docs/`, `dashboard/`, `verified/`, `originated/`, and root pages in addition to the current generated landing + `pages/` site. Their independent models, windows, and claims are preserved and partly reconciled; users should enter through the root site and read its reconciliation/source notes. A future cleanup should designate one canonical surface only after content owners approve it, rather than deleting another session's files.
- **Schedule anomaly already tracked.** The committed raw context file identifies two 2026-11-17 repeat-matchup observations as anomalies and excludes them from the pick window. This audit did not independently resolve them; retain their existing flag and do not infer whether the schedule itself or the extraction is wrong.

## Decision register: questions that remain before action

| Question | Evidence currently available | Missing information / decision needed | Safe next step |
|---|---|---|---|
| What is the allowed odds provider and license? | None in repo | Provider, permitted public display/retention, market coverage, budget | Select a licensed feed and record terms before importing prices |
| Which official source/runner can provide point-in-time player stats and historical finals? | Official schedule and injury snapshots only; some stats endpoints were unreachable in prior captures | Stable endpoint, permissions, retrieval cadence, and point-in-time archive | Test an official NBA data source from the publishing runner; otherwise leave player-dependent outputs blank |
| What constitutes a validated strategy/reward? | 9 strategies and 10 gates are present; no strategy is promoted and rewards are unallocated | Minimum sample, holdout window, vig treatment, drawdown cap, correction for multiple testing, prize policy | Keep reward pool unallocated until an immutable, graded ledger passes the predeclared gates |
| Can this page be considered current? | Data manifest as-of 11/13; schedule independently re-opened 11/14; injury refresh unavailable in this audit | A successful automatic refresh, source timestamps, freshness SLA | Display stale state prominently and suppress action on stale or injury-blind slates |
| Which site surface is canonical? | Root site is the current Pages landing; legacy trees remain | Owner selection and retirement/redirect policy | Keep surfaces intact for now; choose one canonical navigation only after review |

## Source links for manual review

- [NBA official schedule](https://www.nba.com/schedule)
- [NBA official games page](https://www.nba.com/games)
- [NBA official injury report — 2026-11-13 04:15 PM ET](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf)
- [Attempted NBA injury report — 2026-11-14 01:00 PM ET (host response was AccessDenied)](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_00PM.pdf)
- [GitHub Pages workflow](../.github/workflows/pages.yml)
- [Verification/CI workflow](../.github/workflows/ci.yml)
- [Current generated data manifest](../data/site.json)
- [Flagged-for-review page](../pages/flagged-review.html)

**Conclusion:** all local verification commands listed above passed; the two stale README count claims found during inspection are fixed. The remaining blockers are source access, time-sensitive snapshot refresh, market pricing, historical/player data, and owner policies; they are not solvable by inventing values. No additional numeric player-impact, odds, or performance claims were introduced.
