# Baseline verification — session `arena/f4a5531f-nba2` (2026-11-19 UTC, tree = main @ 41cfd81)

Chain run: `audit/session-f4a5531f/run_chain.sh` (rebuild order per `.github/workflows/publish-parity.yml`).

| Step | Command | rc | Evidence |
|---|---|---|---|
| 01 | `python -m nba2.pipeline.build_site_data` | 0 | `01_build_site_data.log` |
| 02 | `python -m nba2.pipeline.build_site` | 0 | `02_build_site.log` |
| 03 | `python -m backtest.engine.build` | 0 | `03_backtest_build.log` |
| 04 | `python -m nba2.v2` | 0 | `04_v2_build.log` |
| 05 | `python -m nba2.settlement_page` | 0 | `05_settlement.log` |
| 06 | `python -m nba2.v3` | 0 | `06_v3_build.log` |
| 07 | `python -m nba2.v4` | 0 | `07_v4_build.log` |
| 08 | `python -m nba2.v5` | 0 | `08_v5_build.log` |
| 09 | `python -m nba2.v6` | 0 | `09_v6_build.log` |
| 10 | `python -m nba2.v2.check` | 0 | `10_v2_check.log` |
| 11 | `python -m nba2.v3.check` | 0 | `11_v3_check.log` |
| 12 | `python -m nba2.pipeline.lint` | 0 | LINT OK — 1436 rows / 50 tables, every row sourced, every blank explained |
| 13 | `python3 tools/check_links_all.py` | 0 | 143 HTML files, 7472 internal links, 8982 external — ALL OK |
| 14 | sealed-ledger verify | 0 | 22 predictions cf7dedc689597cb8 VERIFIED; 27 predictions c841e8f396dae6ca VERIFIED |
| 15 | `python -m nba2.v2.live` | 0 | staleness 20/30 today + 7/30 pre-final, 0 unexplained; graded 9 games |
| 16 | `python3 tools/crosscheck_site.py` | 1 | known disclosed FAIL: CC-FRESH-01 only |
| 17 | `python3 tools/verify_site.py` | 0 | 13 pages / 249 rows / 303 links PASS |

Test suites (unittest discover, logs `tests_*.log`):

| Suite | Tests | Result |
|---|---|---|
| `nba2/tests` (v1) | 92 | OK |
| `nba2/v2` | 167 | OK (90.5s) |
| `nba2/v3` | 67 | OK |
| `nba2/v4` | 61 | OK |
| `nba2/v5` | 26 | OK |
| `nba2/v6` | 52 | OK |
| `backtest/tests` | 49 | OK |
| `tools.test_crosscheck_site` | 12 | OK |

`git status` after the full rebuild: clean (only this audit namespace untracked) — the committed tree is a fixed point of the rebuild chain, matching publish-parity's zero-drift gate.
