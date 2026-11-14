# Independent post-integration audit — `arena/2c07c00b-nba2`

**Audit date:** 2026-11-14 (UTC)  
**Base:** `60399a6` (PR #14 merge)  
**Scope:** independent operational verification of the integrated pipeline and its documented data freshness/provenance limits. This is not a claim that every historical source row in every legacy site surface was re-transcribed in this pass.

## Result summary

The main generated surface passes its automated checks in this checkout. The safeguards work as intended: missing measurements are blocked rather than imputed, the sealed prediction file verifies, and the main site lint reports 915 rows across 33 tables with sourced rows and explained blanks. The independent legacy surface checks and originated-site verifier also pass.

**The project is not yet an unattended live pick service.** Its inputs are committed snapshots with `as_of: 2026-11-13`; the workflows build/test/deploy committed files but do not fetch a fresh schedule, injury report, player data, results, or odds. Do not present the existing slate as current after its documented snapshot window. This is a material product gap for the request to generate every upcoming slate without owner data entry.

## Checks performed

| Area | Command / inspection | Result |
|---|---|---|
| Model and pipeline tests | `python -m unittest discover -s nba2/tests -t . -v` | **55 tests passed** |
| Prediction seal | `python -m nba2.pipeline.seal_predictions --verify` | **Verified**, 22 sealed predictions; printed digest matches the recomputed digest |
| Main generated-site provenance/link lint | `python -m nba2.pipeline.lint` | **PASS**, 915 rows / 33 tables |
| Verification-first docs surface | `python3 tools/verify_site.py` | **PASS**, 13 pages / 249 data rows / 303 links; row-source and internal-link checks pass |
| Repository-wide internal links | `python3 tools/check_links_all.py` | **PASS**, 75 HTML files / 3,233 internal links |
| CSV dashboard | `python3 scripts/check_site.py` | **PASS**, 12 pages / 524 rows |
| `originated/` independent verifier | `node originated/engine/compute.js && node originated/engine/build.js && node originated/engine/verify.js` | **24/24 checks passed**; generated outputs were restored after the test because the build stamps the current time |
| Current official schedule spot-check | [NBA.com Schedule, Nov 14 2026](https://www.nba.com/schedule?date=2026-11-14) | Page shows **5 Games** for Saturday, Nov 14, 2026. This spot-check confirms the official schedule page is available; it does not refresh or validate all repository snapshots. |
| Injury-report spot-check | [Official NBA injury report PDF, Nov 13 2026 1:00 PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf) | PDF extraction exposes official status/reason rows (for example, Paolo Banchero listed Out and Tyrese Haliburton listed Out in the 11/13 report). This report is a dated snapshot, not a live injury feed. |

Commands used: `nba2/pipeline/lint.py`, `.github/workflows/ci.yml`, `tools/verify_site.py`, `tools/check_links_all.py`, `scripts/check_site.py`, `originated/engine/verify.js`. Results are from local execution on the stated base, not inferred from prior task-board claims.

## Findings and actions

### A-01 — No unattended source refresh; rolling slate requirement is unmet (**high**, known blocker)

`README.md` says the data are committed point-in-time snapshots, with `as_of 2026-11-13`. The CI and Pages workflows rebuild and publish the committed snapshots; neither workflow ingests a new schedule, injury report, player statistics, game results, nor market prices. The official NBA schedule currently shows the Nov 14 slate, but that does not make the committed inputs a live feed.

**Decision/use implication:** the system can reproduce its committed window, but cannot truthfully promise fresh picks for every upcoming slate up to three days out without someone or some authorized service refreshing inputs. Without odds, it also cannot call a signal value or compute realized CLV/ROI. Current gates correctly prevent deployment/rewards when their measurements are absent.

**Suggested discovery path:** (1) inventory the exact required fields and freshness deadlines; (2) verify NBA data access, terms, endpoints, stable IDs, revision behavior and rate limits from official documentation; (3) if official automated access is not available, compare licensed data vendors and record cost/coverage/redistribution terms; (4) build a scheduled ingestion job with immutable raw captures, retrieval timestamps, schema checks, source links, duplicate/revision handling and fail-closed staleness gates; (5) only publish picks when all required inputs meet the freshness SLA. Keep manual owner decisions limited to choosing/approving a source, not copying daily data.

Sources for manual review: [NBA schedule](https://www.nba.com/schedule?date=2026-11-14), [NBA injury report index](https://official.nba.com/nba-injury-report-2026-27-season/), and the [dated official PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf). The last two links are references, not proof that a public automated API or redistribution right exists.

### A-02 — README documents 49 tests, checkout runs 55 (**low**, documentation drift)

`README.md` says “49 standard-library tests” in two places; the current `unittest` discovery ran 55 tests successfully. This appears to be a stale test count, not a failing test suite. I did not edit the shared README in this audit scope; update both mentions when the README owner next revises it, or replace the fixed count with a command-only reference.

### A-03 — 19 compiled Python bytecode files are tracked (**low**, repository hygiene)

`git ls-files '*__pycache__*'` returns 19 tracked `.pyc` files. Running the test suite rewrote these binaries in the worktree, despite ignore rules; the local changes were restored and are not included in this audit's output. Tracked bytecode makes clean verification noisy and can vary by Python version. A future scoped cleanup should remove tracked `__pycache__` artifacts from version control (ignore rules alone do not untrack files), then verify tests still pass.

### A-04 — Automated external-link checks do not establish live source availability (**medium**, verification boundary)

The commands report thousands of **internal** links and verify row-source fields/allowed domains. The main lint checks the source URL's scheme/host for official classification; the repo-wide link checker skips URLs beginning with `http`. Therefore a passing build proves source attribution and local link integrity, not that every external official URL still resolves or that every cited value has been independently re-read today. This audit spot-checked the official schedule and injury PDF above; it did not recertify all historic rows.

**Suggestion:** keep a separate, rate-limited external-link/source freshness check (or scheduled verifier) that records timestamp, HTTP result, redirect target and captured document hash. Do not turn a transient network failure into a failed data claim; mark it as unreachable and retain the last verified snapshot.

### A-05 — Team-record corroboration is described at two levels (**needs clarification**)

The published ratings rows label their source as Basketball-Reference and say NBA.com W-L cross-checks agree for 28/30 clubs. `README.md` separately reports 30/30 team records matching a prior session's independent read. These may describe different comparisons (the current rows' NBA cross-check versus cross-session snapshots), so this audit does **not** call it a factual error. The displayed methodology should distinguish the comparisons and identify the two records that were not visible in the cited NBA capture; avoid a blanket 30/30 label unless the underlying row-level evidence is present.

Manual-review references: [NBA standings](https://www.nba.com/standings) and the repo's [ratings table](../index.html#ratings). No unobserved record values are asserted here.

## Boundaries and disposition

- No fabricated injury-minute impact, player-prop line or realized ROI was endorsed in this audit; the automated tests explicitly check that some such values remain absent/blocked.
- Official links cited above were checked by fetching the NBA schedule page and the official report PDF during this audit. Other sources remain as their committed provenance records and are **not** newly verified by this report.
- Findings A-01, A-02, A-03 and A-05 are published here for review; they do not invalidate passing build checks. A-01 remains a release/product limitation until ingestion and freshness controls exist.
- The root dashboard and Pages workflow already exist; no second competing landing page or data set was introduced.
- PR [#15](https://github.com/wingbangboozle1-lang/NBA2/pull/15) merged at 2026-11-14 00:39:46 UTC (`ec0c5182f4b3dad75c4dd2cfd3952adf0887ac8f`); pull-request verification passed. Pages deploy [run 43535687818](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/43535687818) completed successfully. A direct `curl` attempt to the public Pages host failed during TLS connection from this sandbox, so live HTML was not independently fetched in this pass.
