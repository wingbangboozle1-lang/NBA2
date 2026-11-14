# Independent current-tree verification and integration audit

**Session:** `arena/954443e1-nba2`
**Snapshot reviewed:** main at `de495fe` (PR #65, after PRs #63/#64) plus this branch's audit integration
**Scope:** repeatable local checks, workflow status, current site copy, question-register coverage, and source/provenance limits. This audit does not claim a fresh NBA-site re-fetch.

## Executive finding

The repository already contains the requested dashboard, originated lines, strategy lab, validation gates, correlations, luck screening, injury and game-flow sections, executive summary, decision queue, questions register and Flagged for Review page. The published v2 snapshot is reproducible and well-covered by tests. It is **not yet an unattended rolling-slate service**: the 27-game slate is a dated snapshot through three days after its as-of date; the scheduled workflow handles dates already present in sealed ledgers, does not originate the next slate, and its latest observed run failed before settlement/rebuild. The workflow failure's underlying cause could not be established because the Actions log download returned EOF.

Nothing here supports a stake, profit, ROI or CLV claim: no timestamped market-odds feed is connected. Player game logs are absent, so player props, player-level correlations and injury-related minute/production effects remain blocked. The current historical sample is 167 graded games versus the published 300-sample gate.

## Verification performed

| Check | Result |
|---|---|
| v1 pipeline tests | 64 passed |
| v2 model/site tests | 89 passed |
| Backtest tests | 49 passed |
| Provenance lint | **1,416 rows / 50 tables**, every row sourced and every blank explained |
| v2 site checker | **0 structural / 0 semantic** issues |
| Cross-checker | **97 checks: 90 pass, 0 fail, 7 info** |
| Backtest verifier | **12 pages, 183 game rows with NBA game links, 189 internal links**; deterministic rebuild passed |
| Whole-repository link scan | **112 HTML files; 5,020 internal links resolve**; external links are listed but not fetched by this check |
| Rebuild parity | v1, backtest, and v2 builders ran twice; second run produced no additional tracked-file changes |
| JSON parsing | All committed JSON files parsed successfully |
| Prediction ledgers | 22-prediction seal `cf7dedc689597cb8…` and 27-prediction seal `c841e8f396dae6ca…` both verified |
| Working diff hygiene | `git diff --check` clean |

The seven informational checks are disclosure/reconciliation notes, not blocking failures. PR #65 corrected the CC-BT-03 denominator issue and added newer audit/research surfaces. This branch then corrected the README row count to the latest generated 1,416 rows. The cross-checker finishes at 97 checks: 90 pass, 0 fail, 7 info.

## Confirmed irregularities and actions

1. **Scheduled ingest failed — F-043 (published on Flagged for Review).** GitHub run [43605830665](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/43605830665) shows the injury-archive step succeeded and **Fetch official finals** failed. Settlement, verification, rebuild and commit were skipped. `gh run view --log-failed` could not retrieve the log (EOF), so the root cause is explicitly left unknown. Do not represent this run as a successful refresh. Retry with runner logs retained and alert on failure.
2. **The rolling-slate requirement is only partly met.** The committed snapshot has 27 games, 2026-11-14 through 2026-11-17 (the final date is +3 days from the snapshot date). The existing [`refresh.yml`](../.github/workflows/refresh.yml) derives dates from sealed ledgers and updates injury/finals inputs; it does not discover a new schedule, refresh team inputs, or generate the next rolling slate. Requirement R-9 is now marked partial, and Q-36 records the missing unattended workflow. **No claim is made that future slates will appear without a new implementation.**
3. **Questions-register mismatch — F-044 (published for review).** The v2 questions page combines a hard-coded core list with selected shared-register IDs. It now renders 27 unique questions (22 core + five supplemental, including Q-36); other source-register entries and overlapping wording are not yet reconciled. The site flags this rather than silently treating old snapshot-dependent answers as current. Q-28 is present in the supplemental list, so the former F-042 warning that Q-28 was missing was a false positive and was removed.
4. **Executive summary and site copy corrected.** Stale text implying 19 results were missing and that a results feed still had to be obtained was replaced with the verified state: 183 historical finals are committed, but live freshness is not assured after the failed ingest. The summary now distinguishes a dated snapshot from automatic future-slate generation, separates 167 graded games from the 300-sample gate, and keeps no-price/no-stake and missing player-data limitations explicit. The README's v1 row count is now 1,416.

## What is verified—and what is not

Local checks establish structural provenance (source URLs on rows, blanks explained, permitted official-source host labels), internal links, arithmetic checks and reproducible output. They do **not** prove that every NBA URL is reachable today or that a source page still contains the captured value. The environment's outbound access does not include NBA domains, so I did not perform a fresh line-by-line NBA fetch. The committed snapshots retain retrieval metadata and source URLs; the previous verification records are historical evidence, not a substitute for a new fetch.

Useful official-source links for manual review:

- [NBA schedule](https://www.nba.com/schedule)
- [NBA standings](https://www.nba.com/standings)
- [NBA team traditional statistics](https://www.nba.com/stats/teams/traditional), [opponent statistics](https://www.nba.com/stats/teams/opponent), and [advanced statistics](https://www.nba.com/stats/teams/advanced)
- [NBA player traditional statistics](https://www.nba.com/stats/players/traditional)
- [Official injury report archive/policy](https://official.nba.com/nba-injury-report-2026-27-season/)
- Captured injury report used by the snapshot: [2026-11-14 04:30 AM ET PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_30AM.pdf)

For implementation/source claims, the primary records are the repository's [`refresh.yml`](../.github/workflows/refresh.yml), the failed [Actions job](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/43605830665/job/132480138083), and the shared [questions register](../requirements/QUESTIONS.json).

## Deployment and next steps

The PR #64 Pages run was canceled when a newer main update superseded it. PR #65's subsequent main runs were still queued when checked. This branch still requires its own PR checks and Pages deployment before these audit changes are live; do not infer a successful deploy from the earlier main build.

Recommended order: (1) investigate/alert on the failed official-finals fetch; (2) implement a separately gated rolling-slate job using timestamped official schedule and team inputs; (3) connect licensed odds before any edge/ROI/stake/reward claim; (4) acquire sourced player logs before populating props or injury-impact fields. Continue to leave unavailable values blank and flagged.