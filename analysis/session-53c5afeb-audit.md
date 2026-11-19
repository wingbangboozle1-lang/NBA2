# Independent current-tree audit — 2026-11-19

## Scope and evidence boundary

This is a current-tree engineering and provenance audit of commit `a5380e1e7163578b17700f945a99f2c140e67f2f` plus this session's README count correction. It is not a fresh recertification of all NBA facts. I inspected the current coordination board, source/configuration files, generated metadata, and reproducible checks. I did **not** fetch the NBA website, injury PDFs, schedule, standings, stats pages, or gamebooks during this audit. Official links below are supplied for manual review and identify the source class; repository values are only described as committed/transcribed values, not newly verified live values.

The official endpoints relevant to a complete refresh are: [NBA schedule](https://www.nba.com/schedule), [NBA standings](https://www.nba.com/standings), [team traditional stats](https://www.nba.com/stats/teams/traditional), [opponent stats](https://www.nba.com/stats/teams/opponent), [advanced stats](https://www.nba.com/stats/teams/advanced), [official NBA injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/), the committed 2026-11-17 11:00 AM ET [official injury-report PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_11_00AM.pdf), and official [NBA gamebook PDFs](https://statsdmz.nba.com/pdfs/20261114/20261114_DETMIA_book.pdf) (example file; each game must be checked against its own gamebook).

## Executive finding

The repository contains substantial implementation of the requested dashboard, originated projections, two-estimator disagreement, strategy gates, injury/rotation views, result feeds, sealed ledgers, suggestions, questions, and flagged items. Local arithmetic/provenance checks are mostly green. **The present tree does not establish that current-slate output is fresh or that any strategy is ready to bet.** The independent cross-check still fails its freshness gate, the root v2 data snapshot is dated 2026-11-14, the latest scheduled ingest evidence is a failed Actions run, and no contemporaneous NBA source was read in this session. Do not treat published projections as live betting advice or treat a passing structural checker as freshness certification.

## Reproducible checks run

- `python3 tools/crosscheck_site.py`: initially 86 PASS / 2 FAIL / 9 INFO; after correcting the README count, 87 PASS / 1 FAIL / 9 INFO. The remaining failure is `CC-FRESH-01`: the snapshot it checks is five days old on the 2026-11-19 audit date, with games inside the published window already tipped or tipping. `CC-FRESH-02` reports no explicit stale-state banner on `index.html`. `CC-FRESH-03` reports the latest completed scheduled-ingest run failed: [GitHub Actions run 44381003145](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145).
- The same cross-check reports `CC-HTML-05` as INFO: 19 pages are not reachable from the landing page's navigation, including executive summary, flagged review, game flow, injuries, questions, suggestions, and strategy pages. This is an information-architecture problem, even though `CC-HTML-02`, `CC-HTML-03`, and `CC-HTML-04` pass internal link/row/landing-nav checks.
- `python3 -m nba2.v2.check`: 0 structural and 0 semantic errors.
- `python3 -m nba2.v3.check`: 8/8 gates pass.
- `python3 -m nba2.v4.check`: 8/8 gates pass, including the source/settlement/surface checks recorded by the checker.
- `python3 -m nba2.v5.check`: 8/8 gates pass, including 767 player-log rows' local provenance/reconciliation checks. A gate passing means the committed artifact meets its coded rule; it is not proof that every upstream official document was fetched afresh today.
- `python3 -m nba2.pipeline.lint`: 1,436 rows across 50 tables; every row has a source and every blank is explained.
- `python3 -m unittest discover -s nba2/tests -t .`: 88 tests pass on the final rerun. One earlier invocation emitted a failure before the isolated rerun, but the full immediate rerun succeeded; preserve this as a transient test-run irregularity rather than asserting that it reproduced. (The failed invocation's output tail showed 88 tests and one failure; the subsequent complete command reported `OK`.)

The tests can cause generated timestamps to change (`data/site.json` was modified by a test run and restored because generated products were outside this audit scope). No official feed or sealed ledger was edited.

## Findings requiring review

### 1. Current freshness is not established; publication should remain fail-closed

`tools/crosscheck_site.py` measures the root-model metadata in `data/site.json` as `snapshot_as_of: 2026-11-14`, with a 2026-11-14 to 2026-11-17 pick window. Its fresh-state check fails on 2026-11-19. The committed `data/raw/refresh_verdict.json` says all four surfaces returned `success` at `2026-11-18T19:30:52Z`, but the latest completed scheduled run surfaced by the cross-check is failure, and a capture verdict is not itself proof that a downstream publish completed successfully. The check also finds no stale banner on `index.html`. These are distinct facts: the capture artifact is newer than the root model snapshot; neither should be represented as a successful current publication without confirming a gate-passing build.

Manual source review: compare the upcoming slate against [NBA schedule](https://www.nba.com/schedule), standings against [NBA standings](https://www.nba.com/standings), and team inputs against the three NBA stats pages ([traditional](https://www.nba.com/stats/teams/traditional), [opponent](https://www.nba.com/stats/teams/opponent), [advanced](https://www.nba.com/stats/teams/advanced)). The scheduled run evidence is [run 44381003145](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145). This session made no live source claims.

### 2. Investment/competition readiness is not demonstrated

The committed `data/site.json` metadata records `gates_passed: 0` of `gates_total: 90`, unallocated rewards, and a sealed prediction set with no assertion that a market bet was made. `data/v6/market_prior.json` explicitly has no closing-line log-loss, no market weight, and no published blend because no closing-line capture exists in the committed evidence. It records one settled-sample model log-loss of 0.7141 against a 0.6931 coin-flip baseline; this is negative evidence for that sample, not proof of future performance or of a usable edge. Keep bet publication and rewards disabled until point-in-time odds/closing lines, a sufficiently large walk-forward evaluation, calibrated settlement, and all strategy-specific gates are supported by committed evidence.

Manual review sources for the information missing from the official-source side: official NBA schedule and team-stat pages above are not betting markets. A market price source and its licensing/provenance are **not specified or present in this evidence**, so there is no official NBA link to provide for odds. Do not invent one or label model-only lines as priced bets.

### 3. Injury archive and player-log coverage remain partial

`data/v6/injury_archive.json` is an inventory of 18 releases, but fields in the committed records include missing original PDF bytes, retrieval timestamps, revision metadata, and/or content hashes. The inventory/checker makes those gaps visible; it does not establish that every report PDF has been stored. `data/v6/player_coverage.json` records 12 matched injury-report players out of 116 report rows (10.34%) and 104 unmatched rows. These are coverage measurements from committed artifacts, not a claim that 10.34% is sufficient for a rotation model. The official review points are the [NBA injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/), the [2026-11-17 11:00 AM ET report](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_11_00AM.pdf), and each player's relevant official gamebook; the cited Detroit–Miami [gamebook example](https://statsdmz.nba.com/pdfs/20261114/20261114_DETMIA_book.pdf) must not be substituted for other games.

### 4. Important content is not discoverable from the landing page

The cross-check finds 19 existing pages not linked from the landing page. It confirms those target files and rows exist, but existence is not sufficient for a usable categorized dashboard. The requested organization should put projection, gated bet, results/settlement, injuries/rotation, strategy/leaderboard, executive summary, questions, suggestions, and Flagged for Review within clear navigation. The current site checker does not prove external links are reachable; this audit made no external-link requests.

### 5. Settled records and high-signal model claims need clear as-of scope

The v6 results coverage artifact is stamped `as_of_utc: 2026-11-17T00:00:00Z`, while the repository received later capture commits. Do not present a historical coverage registry as the current official result feed unless it is regenerated and verified from the official schedule/gamebook/result sources for every date. Where available, the reference source is the official [NBA schedule/results](https://www.nba.com/schedule) and the official per-game gamebook PDF, e.g. [DET–MIA, 2026-11-14](https://statsdmz.nba.com/pdfs/20261114/20261114_DETMIA_book.pdf). The settlement check verifies local hashes and arithmetic; it cannot close missing finals or prove a new result feed was refreshed.

## Specific questions / missing evidence before a decision

- What dated, licensed market source supplies opening and closing prices for each exact side/total/prop, and can its historical snapshots be archived before tip? No such source or line sample is present in the audited artifacts.
- Which exact market, settlement convention (including pushes, voids, overtime, player DNPs, and stat corrections), and minimum price edge will define a strategy's preregistration? The strategy file must freeze these before first use.
- What sample size, minimum calibration, uncertainty interval, multiple-testing correction, holdout period, and risk/drawdown limits are required before leaderboard rewards can be allocated?
- Which official API/page or archived response is the source of truth for every rolling schedule/stat refresh, and what successful end-to-end scheduled run proves that the refresh, gates, generated site, and deployment all completed?
- Can all injury-report PDFs be retained with retrieval timestamp, report revision, byte count, and cryptographic digest? Which player-name/team join rule and historical lookback are approved for injury-report player logs?
- What venue coordinate source/licensing and distance convention (great-circle vs route distance, neutral-site handling) will be accepted for travel? Do not publish a distance until source, coordinate version, and calculation rule are recorded.
- How will injury replacement shares be estimated when a player has no comparable prior role, and what confidence threshold makes the output a blank rather than a fabricated minute allocation?
- What form of public ledger hash publication and trusted timestamp is required to prove the digest existed before tip? A local SHA-256 recomputation alone does not prove when a hash was published.

## Actions in this session and status

- Corrected the README's `nba2/tests` count from 79 to 88 after a reproducible local run; `CC-DOC-01` then passed.
- Preserved generated outputs and sealed ledgers; no NBA value was edited or newly certified.
- No site or navigation page was edited because the task board reserves generated/shared site output for an integration pass. The unresolved freshness and navigation findings should be copied to the published Flagged for Review page by that integration pass, with their source/run links and a visible stale-state banner until the fresh capture passes every gate.
- This report is an audit artifact and is not a substitute for the full official-source, deploy, and live Pages verification requested in the project brief.
