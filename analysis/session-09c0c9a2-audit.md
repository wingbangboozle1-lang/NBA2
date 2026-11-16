# Post-integration audit — `arena/09c0c9a2-nba2`

**Date:** 2026-11-16 UTC  
**Base:** `f943bd1` (merge of PR #97)  
**Purpose:** independently run the current repository's checks and record verified results, with any failures left visible. This is a repository audit, not a new capture or a claim that every NBA value was independently re-read.

## What was checked

- v1 / v2 / v3 / v4 / backtest unit suites.
- v2, v3 and v4 structural/semantic checks; provenance lint; whole-site internal links.
- `tools/crosscheck_site.py` semantic checks.
- Live GitHub Pages `projection.html` and the official NBA standings page.
- The source-capture implementation (`nba2/v4/write_capture.py`, `nba2/v4/capture.py`) and the scheduled workflow (`.github/workflows/refresh.yml`).

## Results

| Check | Result |
|---|---|
| `python3 -m unittest discover -s nba2/tests -t .` | PASS — 79 tests |
| `python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'` | PASS — 146 tests; emitted `ResourceWarning`s for unclosed JSON files in `nba2/v2/model.py:501` and `nba2/v2/travel.py:62,146` |
| `python3 -m unittest discover -s nba2/v3 -t . -p 'test_*.py'` | PASS — 67 tests |
| `python3 -m unittest discover -s nba2/v4 -t . -p 'test_*.py'` | PASS — 53 tests |
| `python3 -m unittest discover -s backtest/tests -t . -p 'test_*.py'` | PASS — 49 tests |
| `python3 -m nba2.v2.check` | PASS structurally/semantically; 7 gates pass / 1 fail, still reported `publishable=True` |
| `python3 -m nba2.v3.check` | PASS structurally/semantically; 7 gates pass / 1 fail. The stored verification identifies G-F3: the used 11/15 06:00 ET injury release was not the newest indexed, 06:15 ET. |
| `python3 -m nba2.v4.check` | PASS — 8/8 gates; no structural, surface-wall, or numeric failures |
| `python3 -m nba2.pipeline.lint` | PASS — 1,427 rows across 50 tables; each row has a source and each blank is explained |
| `python3 tools/check_links_all.py` | PASS — 132 HTML files; 6,378 internal links checked, all resolve |
| `python3 tools/crosscheck_site.py` | 97 checks: 88 pass, 2 fail, 7 info |

The two current semantic-check failures are **not** suppressed in this audit:

1. **CC-DOC-01 — stale README counts:** README says 1,423 rows while the measured artifact count is 1,427; README says 70 tests while the current `nba2/tests` suite runs 79. The same check reports the table count as 50, matching.
2. **CC-FRESH-01 — stale legacy/canonical snapshot:** the checker measures the snapshot as two days old, with four game dates already tipped or tipping inside that published window. The v4 `projection.html` surface is a separate, newer artifact; that does not make the older snapshot current. The live projection page was fetch-checked and shows a 25-game published window, 0 stakes, a measured home-win rate of 0.5204 and pinned home-court value of 0.869 points. The old crosscheck failure should be resolved by making the published-page contract unambiguous and ensuring stale surfaces cannot present as current.

The current v3 G-F3 issue is present in committed `data/v3/verification.json`, and is distinct from v4's 8/8 current-snapshot checks. Do not interpret a successful structural check or the v4 result as clearing that v3 stale-release result.

## Implementation gaps confirmed from code / committed data

- `nba2/v4/write_capture.py` describes and writes a frozen 2026-11-16 capture from constants in `nba2/v4/capture.py`; it is deterministic replay, not a network fetch of today's four official surfaces. `.github/workflows/refresh.yml` does call `nba2.v2.refresh --write`, but the v4 capture step does not itself obtain a fresh release and its reproduction check names `data/raw/refresh_2026-11-16`. This leaves a gap between “scheduled job exists” and “v4 refreshes a rolling current slate.” Do not represent the fixed capture as a daily live read.
- The injury transcript data explicitly says `binary_stored: false`; the official PDF binaries are not archived in the v4 capture. The PDF/index URLs, revision/retrieval times, transcription and diff are recorded, but this does not satisfy the request to store each PDF byte-for-byte.
- The current bet surface has no actual market prices; the projection page explicitly says no odds feed is connected and no stakes are published. No edge/ROI claim should be inferred from the model triggers.
- README contains many dated historical sections and statements. The two measured count discrepancies above are concrete; this audit does not rewrite historical narratives or turn the README into a live generated report.

## Official source references checked / linked by the captures

- [NBA standings](https://www.nba.com/standings) — official live page fetched during this audit. It identifies the 2026–27 regular season and publishes club W-L/home-road records. This audit did not transcribe and reconcile all 30 rows against the stored v4 JSON.
- [NBA schedule](https://www.nba.com/schedule) — official schedule source referenced by the capture.
- [NBA team advanced statistics](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame), [traditional statistics](https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame), and [opponent statistics](https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame) — the three official inputs referenced by v4.
- [NBA injury-report policy/index](https://official.nba.com/nba-injury-report-2026-27-season/) and [official injury-report PDF host](https://ak-static.cms.nba.com/referee/injury/) — source references for report publication and per-release PDFs. The committed v4 transcript states the PDF bytes were not stored.

## Irregularities / requests for final integration

1. Update generated README counts from the same measurements as CI, or stop presenting stale counts as current. Re-run CC-DOC-01.
2. Decide one authoritative published-data surface and a fail-closed freshness policy across it. Keep old v1/v2/v3 pages visibly historical or unpublished; do not let the v2 stale snapshot coexist as if current beside v4.
3. Replace the frozen-only v4 capture workflow with a live, provenance-stamped fetch for each source, preserving the current gates and fail-closed behavior. Archive PDFs as bytes with hashes before claiming PDF storage complete.
4. Fix/refresh v3 G-F3 only from the newest indexed official report; do not change the report timestamp or status by inference.
5. Close the `ResourceWarning`s with context-managed file reads in a separately claimed code task; they did not fail tests but indicate file handles are left open.

## Scope and integrity

No model values, source snapshots, sealed ledger, shared site output, or workflow code were changed. `tools/crosscheck_site.py` caused generated v3 page diffs during execution; those generated files were restored to their pre-audit state. The only intended deliverables are this report and its coordination record.
