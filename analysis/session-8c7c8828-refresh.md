# Session `arena/8c7c8828-nba2` — refresh and settlement integration

**Date:** 2026-11-19 UTC
**Branch:** `arena/8c7c8828-nba2`
**Current base:** `7b16b6d` (merge of PR #129; branch rebased onto this `main` before final verification).
**Status:** code, generated-output, full local test and parity checks complete; PR / Pages deployment verification pending.

## Summary

The scheduled publish failure was a build-order defect, not a demonstrated NBA transport defect. The committed official finals union was stale relative to other committed feeds; the settlement page correctly refused to build from it. The refresh, Pages and parity paths now build the union and settlement before rendering. The refresh path settles only after a successful finals capture, preserving the existing failure behavior.

The rebuilt settlement contains 36 official finals from 11 committed source files, with zero score conflicts and zero rejected quarter rows. The 11/13 ledger settled 22/22 and the 11/14 ledger 27/27. The four sealed-ledger file hashes recorded before rebuild are unchanged afterward.

The v6 coverage page now uses a date-matching NBA schedule link. The previous generated 2026-11-17 row pointed at `date=2026-11-16`, inherited from a multi-day snapshot. The current committed 2026-11-17 capture itself records `source_url=https://www.nba.com/schedule?date=2026-11-17`; per-game `list_url` fields are null. The aggregator now accepts only an official NBA `/schedule` or `/games` URL whose `date` query equals the row's game date, and ignores stale links from multi-day snapshots.

A separate parity defect was found during repeated builds: `data/settlement.json` used to receive a new wall-clock timestamp even when its report content was unchanged. Because the v1 builder includes that file in its input digest and rendered settlement note, rebuilds drifted. The settlement builder now preserves the prior `settled_at_utc` only when the rest of the report is unchanged; changed report content receives a new UTC stamp. This changes no score selection or gate semantics and does not touch sealed ledgers.

## Source basis and verification limits

- Committed schedule capture: [`data/raw/refresh_2026-11-17/slate_2026-11-17.json`](../data/raw/refresh_2026-11-17/slate_2026-11-17.json), recorded source URL [`NBA.com schedule for 2026-11-17`](https://www.nba.com/schedule?date=2026-11-17), retrieved `2026-11-17T15:52:00Z`. The capture has five game IDs and per-game NBA game-page URLs.
- Committed finals capture metadata: `data/raw/finals_2026-11-17.json`, retrieved `2026-11-18T19:29:18Z`. The successful committed results-capture metadata advances v6's as-of cutoff to `2026-11-18T19:30:52Z` (`2026-11-18 14:30 ET`).
- The NBA schedule page was not fetched live in this session; the official URL and its date were verified against the committed capture metadata. No official-source transport defect was demonstrated. The previously recorded transport diagnosis remains pending a runner/live-source reproduction.
- The 2026-11-18 row remains `not ended` at the committed cutoff: 12 scheduled, zero finals and zero graded. No score is inferred.

## Generated results

- `data/raw/official_finals_union.json`: 36 finals from 11 sources; 0 conflicts; 0 rejected quarter rows.
- `data/settlement.json`: `settled_at_utc=2026-11-19T05:49:58+00:00`; the timestamp is preserved on identical rebuilds. The 11/13 ledger is SETTLED 22/22; the 11/14 ledger is SETTLED 27/27. The model error summaries are not a betting edge or a market comparison.
- `data/v6/results_coverage.json`: 67 known games, 36 with finals, 27 graded; as-of `2026-11-18T19:30:52Z`. 2026-11-17 is complete (5/5 finals, 5/5 graded) with `https://www.nba.com/schedule?date=2026-11-17`; 2026-11-18 is not ended (12 scheduled, 0 finals). The 11/19 and later links are likewise date-specific.
- `site/results-coverage.html` publishes the corrected links and the same measured counts. Every blank remains blank and reasoned; no score was inferred.

The settlement builder continues to report other model/betting gates as BLOCKED, including insufficient sample size, no market prices, no trial/holdout, placeholder reference price, and missing injury join. These are not passes and are not presented as actionable bets.

## Verification performed

Ordered committed rebuild:

```text
python3 -m nba2.pipeline.settle
python3 -m nba2.pipeline.build_site_data
python3 -m nba2.pipeline.build_site
python3 -m backtest.engine.build
python3 -m nba2.v2
python3 -m nba2.settlement_page
python3 -m nba2.v3
python3 -m nba2.v4
python3 -m nba2.v5
python3 -m nba2.v6
```

After fetching and rebasing onto `main` at `7b16b6d` (PR #129), I reran the ordered builder/test chain and all local checks listed here. The rebuild left no generated tracked files dirty. The merged PR added board/audit records only; no code in the rebuilt paths changed from the previously verified base.

The full unit suites passed after rebasing onto current `main`:

| Suite | Result |
|---|---:|
| `nba2/tests` | 99 passed |
| `nba2/v2` | 167 passed |
| `nba2/v3` | 67 passed |
| `nba2/v4` | 61 passed |
| `nba2/v5` | 26 passed |
| `nba2/v6` | 56 passed |

The v2 test run emits existing `ResourceWarning`s about unclosed history-file handles; it exits successfully. Workflow-order tests passed 4/4; settlement-stamp regressions passed 3/3; v6 coverage regressions passed 17/17.

Additional checks:

- `nba2.v2.check`: 0 structural, 0 semantic.
- `nba2.v3.check`: 8/8 gates pass; publishable.
- `nba2.v4.check`: 8/8 gates pass; publishable.
- `nba2.v5`: 8/8 gates pass.
- `nba2.v6`: 13/13 gates pass; publishable. `nba2.v6 --check-only`: 12/12 gates pass, no files written.
- `nba2.pipeline.lint`: 1,436 rows across 50 tables; every row sourced and every blank explained.
- `tools/check_links_all.py`: 143 HTML files, 7,472 internal links checked; all internal links resolve.
- Repeated full builder runs produced the same aggregate generated-output digest: `6259086d4ea25919a4d1f38c19e397f6a32527cb571ca5a65be0f8b43dab853c`.
- The local `publish-parity` rebuild checks passed: `site/` and the v1 generated tree exactly matched their ordered rebuilds. Raw sealed-ledger files were unchanged.
- `nba2.v2.live` re-derived its legacy 9-game report (model 5/9; net-rating 5/9; always-home 7/9) with 0 unexplained staleness discrepancies.

`tools/crosscheck_site.py` reports 97 checks: 86 pass, 9 info, 2 known non-gating failures. `CC-DOC-01` is the README's stale test count after adding tests; `CC-FRESH-01` is the five-day-old legacy snapshot. The refresh workflow explicitly treats those two checks as visible/non-blocking; all other cross-checks pass. The stale legacy snapshot is not represented as current; v6's as-of is tied to the newer committed capture.

## Changes and remaining steps

This branch contains settlement-before-render ordering in `refresh.yml`, `pages.yml`, and `publish-parity.yml`; refresh failure behavior and derived-output staging are preserved. It also contains the date-checked v6 schedule aggregation, repeatable settlement timestamp behavior, regression tests, and regenerated outputs from committed builders.

**PR and deployment:** pending. This section will be updated with the PR URL, merge result, and Pages run/deployed URL after those checks finish.
