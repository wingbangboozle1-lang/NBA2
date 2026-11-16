# Session A429 audit and refresh-gate remediation

- **Session:** `arena/0429aad7-nba2`
- **Audit date:** 2026-11-15 official-source observation/capture date; final post-rebase checks rerun 2026-11-16T00:19Z UTC
- **Scope:** independent verification plus the explicitly approved A429-05 changes in `nba2/v2/refresh.py` and the new fixture-only `nba2/v2/test_refresh_gate_audit.py`. The workflow, generated site, snapshots, and other sessions' files were not edited.

## Executive result

The original v2 refresh could not pass its gates on an ordinary rolling window: it required a final for the anchor date even though that day was not yet complete, and compared a one-week finals slice with season-to-date standings. PR #77's first-stage gate correction merged while this branch was being rebased; the final implementation builds on it by retaining detailed per-game status inventory, accepting only checked off-days, and rebuilding season records from the 188 unique committed finals plus fresh results (including any already-final games today). The baseline loader fails closed on unreadable or malformed authoritative result snapshots. Fifteen offline A429 regression tests and 151 tests in the full v2 suite pass.

The source audit also confirmed live-site discrepancies that are outside this session's file scope. They are recorded below with official links and change requests; `site/` and `flagged.html` were deliberately not changed. The live `freshness/injuries` gate still checks only for report/timestamp presence, not whether the revision meets a game-date freshness threshold. This limitation is now stated accurately in `refresh.py` and raised for the owning session.

## Reproducible refresh-gate findings

| Finding | Reproduction from committed inputs | Result and change | Official reference |
|---|---|---|---|
| Finals gate included an unfinished anchor date | The old call required finals for 2026-11-15 while the requested prior-date range was 2026-11-14 through 2026-11-08. The committed rolling finals contained 49 rows; the gate did not establish that games on the anchor date were already final before requiring that date. | The new fetch records each successfully checked date and the scoreboard's game/status inventory. `gate_finals()` requires a valid final for each scoreboard-listed game only on caller-supplied completed dates; checked off-days pass, unchecked dates and malformed/missing results fail. `main()` still fetches today's results for standings reconciliation but does not require today's games to be final. | [NBA schedule, 2026-11-15](https://www.nba.com/schedule?date=2026-11-15) |
| Standings gate compared unlike scopes | The old gate compared 30 season-to-date W/L rows with only the 49 recent finals and failed every team. | The new gate merges the committed official game history and fresh scoreboard finals by game ID, detects duplicate-ID conflicts and malformed records, checks all 30 live rows, and fails on missing/duplicate tricodes or feed teams absent from standings. `load_committed_final_records()` reconstructs 188 unique finals from the committed history/captures, fails closed on unreadable or malformed authoritative snapshots, and a fixture test rebuilds the committed standings exactly from those 188 games. | [NBA standings](https://www.nba.com/standings) |
| Injury-release selection depended on HTML order | The previous implementation took the first matching PDF link and assumed the index was newest-first. The official archive renders the day's timestamped releases in ascending time order. | `newest_release_from_index()` parses the timestamp in each matching filename and selects the maximum, independent of link order. A fixture places older releases before the newest link (the order that made the old first-link rule fail) and verifies the newest timestamp is selected. | [Official NBA injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/); [2026-11-15 06:15 AM PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) |

The selected official capture files in `data/raw/capture_2026-11-15/` record retrieval times of `2026-11-15T12:00:00Z` for the standings, schedule, results and team-stat captures, and `2026-11-15T12:05:00Z` for the injury transcript. The official NBA page-reader did not expose HTTP retrieval timestamps for the later live-page checks; those values are treated as observations from this audit session, not as timestamped source captures.

## Current-source discrepancies requiring owner action

The published NBA2 team table is the dated 188-game snapshot. It remains internally reproducible for that capture, but it is no longer current against the official standings after two 2026-11-15 finals. Each row below links to the official standings page; the official schedule provides a second source for the game results. A post-rebase crosscheck rerun at 2026-11-16T00:19Z also measured the published snapshot as two days old and found four dates in the published window with games already tipped or tipping (CC-FRESH-01). The site discloses its as-of date, but a current official refresh is still required.

| Team | NBA2 `teams.html` snapshot | Official standings at audit read | Context | Official source |
|---|---:|---:|---|---|
| PHI | 10-3 | 11-3 | IND lost to PHI, 124-131, on 2026-11-15. | [NBA2 team table](https://wingbangboozle1-lang.github.io/NBA2/teams.html) · [NBA standings](https://www.nba.com/standings) · [official game page](https://www.nba.com/game/ind-vs-phi-0022600236) |
| IND | 5-8 | 5-9 | Same official final. | [NBA2 team table](https://wingbangboozle1-lang.github.io/NBA2/teams.html) · [NBA standings](https://www.nba.com/standings) · [official game page](https://www.nba.com/game/ind-vs-phi-0022600236) |
| LAL | 11-2 | 12-2 | LAL beat PHX, 131-123, on 2026-11-15. | [NBA2 team table](https://wingbangboozle1-lang.github.io/NBA2/teams.html) · [NBA standings](https://www.nba.com/standings) · [official game page](https://www.nba.com/game/lal-vs-phx-0022600237) |
| PHX | 5-6 | 5-7 | Same official final. | [NBA2 team table](https://wingbangboozle1-lang.github.io/NBA2/teams.html) · [NBA standings](https://www.nba.com/standings) · [official game page](https://www.nba.com/game/lal-vs-phx-0022600237) |
| NYK–TOR game link on `picks.html` | 2026-11-15 row links to game ID `0022600253` | Official 2026-11-15 schedule identifies game ID `0022600241`. | `projections`/ledger use `0022600241`; only the picks-page link disagrees. | [NBA2 picks page](https://wingbangboozle1-lang.github.io/NBA2/picks.html) · [NBA schedule, 2026-11-15](https://www.nba.com/schedule?date=2026-11-15) · [official game page for 0022600241](https://www.nba.com/game/nyk-vs-tor-0022600241) |
| Injury-report ceiling stated by the older snapshot | NBA2 injury capture: 2026-11-15 06:15 AM ET, retrieved 12:05Z | The official index later displayed 11/15 releases through 6:45 PM ET when re-read in this audit. | The captured 06:15 AM release is a dated snapshot, not the latest report at this later read. The new v2 parser selects by timestamp; no fresh PDF was archived or transcribed in this session. | [NBA2 injury page](https://wingbangboozle1-lang.github.io/NBA2/injuries.html) · [Official NBA injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/) · [06:15 AM PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) · [06:45 PM PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_45PM.pdf) |

The current `flagged.html` already documents older staleness and injury issues, but did not contain a dedicated entry for the four new W/L differences or the NYK–TOR picks-link mismatch. Those are **needs-owner-review** items, not assertions of an error in the dated historical snapshot. They must be added to the published Flagged for Review page by its owner. This session did not edit that page because it is outside the A429-05 claim and the standing instruction is to log cross-scope requests rather than change another session's files.

### Scoped change requests

1. **Site owner — add review flags and repair the NYK–TOR link.** Publish the four current W/L differences and the 2026-11-15 game-ID discrepancy on Flagged for Review, each with the official links above; correct the picks-page link from `0022600253` to the verified 2026-11-15 game ID `0022600241` without rewriting the sealed ledger.
2. **Refresh-gate owner — make injury freshness measurable.** `gate_injuries()` currently verifies only that a PDF URL, revision stamp and retrieval stamp exist; it does not compare the revision to the most recent completed game's reporting window. Implement and fixture-test that threshold in the owning scope, or keep the limitation plainly documented. This A429 change corrects report selection order but does not broaden into this separate policy gate.
3. **Workflow owner — investigate the existing failed refresh check.** [PR #72's run `43714472051`](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/43714472051) (job `132812900286`) failed at “v2 model + source-completeness tests”; rebuild/check were skipped. The failing assertion/log was not available during this audit, so the cause remains unverified. No workflow change was made here.
4. **v3 owner — re-check the 06:00/06:15 AM selection.** The earlier v3 audit recorded that the 06:00 AM report was used although the official index included a 06:15 AM release. The source index now lists later timestamps as well. This session does not edit `nba2/v3/**`; the file-order defect in the scoped v2 fetcher is covered by the new timestamp-selection helper and fixture.
5. **Refresh/site owner — publish a current snapshot.** The 2026-11-16T00:19Z post-rebase `tools/crosscheck_site.py` run fails CC-FRESH-01: the published snapshot is measured two days old and four dates in its window have already tipped or are tipping. The stale as-of date is disclosed, but a fresh official ingest/build is needed; this session did not run a live refresh or edit generated site/data files.

## Verification performed

- `python -m unittest nba2.v2.test_refresh_gate_audit -v` — **15 passed**, no network.
- `python -m unittest discover -s nba2/v2 -t . -p 'test_*.py' -v` — **151 passed** after rebasing onto `origin/main` `996e92e`. Existing `ResourceWarning`s remain in `nba2/v2/model.py:501` and `nba2/v2/travel.py:62,146`; those files are outside scope.
- `python -m unittest discover -s nba2/tests -t . -p 'test_*.py' -v` — **70 passed**.
- `python -m unittest discover -s nba2/v3 -t . -p 'test_*.py' -v` — **33 passed**.
- `python -m nba2.v2.check` — **0 structural, 0 semantic issues**.
- `python -m nba2.v3.check` — **7 gates pass / 1 fail, `publishable=True`; 0 structural, 0 semantic issues**. The existing v3 gate result is not changed by this patch.
- `python tools/check_links_all.py` — **121 HTML files; 5,547 internal links; all internal links OK** (6,355 external links scanned).
- `python -m nba2.pipeline.lint` — **1,423 rows across 50 tables; every row sourced and every blank explained**.
- `python -m nba2.pipeline.seal_predictions --verify` — **27 predictions verified**, digest prefix `c841e8f396dae6ca`.
- `python tools/crosscheck_site.py` — initial 2026-11-15 run: **97 checks, 90 pass / 0 fail / 7 info**; post-rebase rerun at `2026-11-16T00:19Z`: **97 checks, 89 pass / 1 fail / 7 info**. The sole current failure is CC-FRESH-01 (snapshot measured two days old; four game dates already tipped or tipping), an owner refresh follow-up.
- `python tools/verify_backtest.py` — **passed**, 12 pages and 183 sourced result rows.
- `python -m py_compile nba2/v2/refresh.py nba2/v2/test_refresh_gate_audit.py` and `git diff --check` — passed.

A live `nba2.v2.refresh --check-only` was not run: direct shell access to NBA hosts is blocked in this environment. Source review used the platform page-reader and the committed official captures; the new refresh-gate tests are intentionally offline. No claim is made here that a new production refresh or Pages deployment has run. PR/merge/deployment status is to be confirmed after the code and checks are integrated.
