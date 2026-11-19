# Session `arena/a11505e1-nba2` — final-integration verification record (2026-11-16)

Role: **final integration + brief backlog closure** for the 2026-11-16 round (claim A1–A7
in `COORDINATION.md`). This record reports what was measured on the combined tree, what was
integrated from stale branches, which defects this session found and fixed, and what remains
flagged. Nothing here is claimed verified without a command output or an official source link.

---

## 1. What was integrated (A2), branch by branch

| PR / branch | State found | Disposition | Evidence |
|---|---|---|---|
| **#98** `arena/fe0ffa49-nba2` (e36359f, 3807dc8) | claim said "PR merged" but PR was still OPEN (session died pre-merge); stale >60 min | **merged** (commit 99a05cb): 2026-11-16 capture, results feed, RR-29..38 fixes (write-once v3 seal, prereg freeze, σ de-dup), v2 refresh to 11-16, v1 rebuild. Conflicts resolved as semantic unions (kept PR #89's pinned-HCA wording + measured counts; PR #91's settlement nav + honest "frozen snapshot" label; both sides' COORDINATION records) | `git log 99a05cb`; merge diff |
| **#80** `arena/0429aad7-nba2` | stale (last commit 00:44 UTC) | **essence ported** (commit 68acb20): `newest_release_from_index()` (the `links[0]` picker selected the OLDEST injury release), strict `team_stats.<page>.source_url` provenance, season-record standings reconciliation with committed-baseline merge. 15 tests adapted with every assertion intent preserved (see `nba2/v2/test_refresh_gate_audit.py` docstring); its parallel gate_finals/gate_slate variants were laterally equivalent to main's fail-closed versions and were superseded, not merged | v2 suite 161 OK |
| **#70** `arena/d09f8d1e-nba2` | stale | **essence ported** (commit 4d7342c): the CR-7 crosscheck gate was DEAD on main (`grep '^\[fail\]'` vs the checker's `[FAIL]`, plus `|| true` crash-swallowing) — now `tools/crosscheck_gate.sh` in refresh.yml **and** ci.yml; hardened `tools/crosscheck_site.py` (row-count-anchored snapshot selection); `tools/probe_official.py` + `probe.yml` (F-043 evidence). 12 tests pass | `nba2.tests` 91 OK |
| **#72** `arena/04a61ac0-nba2` (draft) | stale, superseded | outcomes delivered by later merged sessions; unique 2026-11-15 official readings preserved in `audit/2026-11-15-04a61ac0/` (moved out of `data/raw/` — their row shapes fail the strict fail-closed loaders and would hijack snapshot selection); code not ported | commit 2888922 |
| **#78 / #82** | COORDINATION-only | records preserved verbatim in the board (56b96bf0's completion; f8f8f2b8's deploy-status + Pages irregularity) | commit 2888922 |

## 2. Defects found and fixed by this session

| ID | Defect | Fix | Test |
|---|---|---|---|
| D-A115-01 | `nba2/v3/ledger.py` appended an **identical** seal-divergence record on every rebuild (13 duplicates accumulated) — unbounded growth and a fixed-point breaker | the append is now idempotent per distinct (seal, recomputed) state; existing rows kept (append-only) | `test_divergence_log_records_each_distinct_state_once` (v3 suite 67→68) |
| D-A115-02 | crosscheck CC-BT-01/02 proxied the graded set through the whole history pool, so the frozen v1 surface failed as the (legitimately) growing history advanced | checks now recount the report's **declared grading cut** (`meta.grading_as_of`) and verify no graded row outdates the published snapshot; the backtest build declares its cut and grades only through it (188 games / 172 graded to 2026-11-14). Verdicts unchanged on old report shapes | crosscheck 92/1/7 |
| CR-7 dead gate | refresh.yml grepped lowercase `[fail]` while the checker prints `[FAIL]` — a red crosscheck could never block a commit; `|| true` hid crashes | `tools/crosscheck_gate.sh` wired into refresh.yml + ci.yml (from PR #70) | `test_crosscheck_gate.py` (6 tests) |
| links[0] | `fetch_newest_injury_release` assumed the injury index lists newest first; it lists **ascending** — the live path selected the oldest release | `newest_release_from_index()` parses filename stamps and takes the max (from PR #80) | `test_injury_index_selection_uses_latest_timestamp_not_link_order` |
| CR-V4-1 | `nba2/v2/check.py` resolved `page.html#section` to a file literally named "page.html#section" | fragment stripped on resolve + the anchor is verified to exist; pure `#anchor`s checked (A3) | `nba2/v2/test_check_links.py` (7 tests) |
| CR-V4-2 | F-V4-01..09 not visible on the shared Flagged page | all nine published there, transcribed from `nba2/v4/publish.py`, linked to v4-verify.html (A4) | `site/flagged.html` renders 19 F-V4 rows |
| I-32C-04 | "Verified against the live official pages this session (2026-11-15)" hard-coded | dated from `O.AS_OF` (the 2026-11-16 capture) | v2 check 0/0 |
| I-FE0-02 | DAL@BOS (0022600240) `away_quarters: null` — the gamebook's full-game row extracts garbled | quarters read from the gamebook's own cumulative SCORE BY PERIOD tables + period boxes: DAL [9,28,34,23] (sum 94). Closed 2026-11-16 | see §4 |

## 3. Verification of the combined tree (all commands run 2026-11-16 ~19:2x–19:5x UTC)

| Command | Result |
|---|---|
| `python3 -m unittest discover -s nba2/tests -t .` | **91 tests OK** (79 base + 12 crosscheck) |
| `python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'` | **168 tests OK** |
| `python3 -m unittest discover -s nba2/v3 -t . -p 'test_*.py'` | **68 tests OK** |
| `python3 -m unittest discover -s nba2/v4 -t . -p 'test_*.py'` | **53 tests OK** |
| `python3 -m unittest discover -s backtest/tests -t .` | **49 tests OK** |
| `python3 -m nba2.v2.check` | OK — 0 structural, 0 semantic (incl. new anchor verification) |
| `python3 -m nba2.v3.check` | 7 gates pass / 1 fail (G-F3 advisory), `publishable=True` |
| `python3 -m nba2.v4.check` | 8 gates pass / 0 fail; 0 structural/surface-wall/numeric; `publishable=True` |
| `python3 -m nba2.pipeline.lint` | LINT OK — 1,441 rows across 50 tables, every row sourced, every blank explained |
| `python3 tools/check_links_all.py` | ALL INTERNAL LINKS OK (132 files) |
| `python3 tools/crosscheck_site.py` | 100 checks: **92 pass, 1 fail, 7 info** — the single fail is CC-FRESH-01 (v1 snapshot age), excluded from the gate by design and disclosed |
| `tools/crosscheck_gate.sh` | GATE PASS |
| sealed ledgers | `sealed-2026-11-13.json` 34e144c6… VERIFIED; `sealed-2026-11-15.json` 34 rows 34e144c635b83b89 VERIFIED (write-once preserved) |
| build-twice (parity rebuild list) | **fixed point** (identical trees across consecutive rebuilds) |

## 4. Live probes (fetched, not assumed)

- **Pages host (settles I-FE0-01 at 2026-11-16 ~19:0x UTC):** fetching
  `https://wingbangboozle1-lang.github.io/NBA2/` returns the **v2 dashboard** ("Dashboard ·
  NBA2 Lines Lab v2", originated-lines landing). The Pages API still reports
  `build_type: legacy, source: main /`. **The API field and the served tree disagree** —
  re-confirmed from both sides this session (F-039's conclusion stands). The owner decision
  on the Pages source is FLAG-PAGES-01 / F-033 and is registered as Q-40; this session did
  not flip the setting.
- **DAL@BOS gamebook (I-FE0-02 closure):** `statsdmz.nba.com/pdfs/20261115/20261115_DALBOS_book.pdf`
  IS readable through the platform page-fetch tool. The full-game SCORE BY PERIOD row for DAL
  extracts garbled (2|3|4|2 — the reason the capture left it blank), but the gamebook's own
  cumulative tables are clean: halftime `9|28|37`, through three `9|28|34|71`, Q4 box
  `23|27`, final row `42|25|37|27|131`. DAL quarters **[9, 28, 34, 23]** sum to 94 = the
  final; cross-checked against every period box team total. Written to the results feed and
  `data/raw/history/games_2026-11-15.json` (`quarter_scores`), and the chain re-derived
  `official_finals_union.json`. All checks green after the change.

## 5. Remaining flagged items (published, not blocking)

| Flag | Status |
|---|---|
| CC-FRESH-01 | the v1 tree is a frozen 2026-11-14 snapshot (labelled "retained, not published"); its age is disclosed (CC-FRESH-02) and excluded from the blocking gate. The current surfaces are the v2 tree (2026-11-16 window, nightly-refreshed) and the v4 gated surfaces. Registered as Q-41 |
| FLAG-PAGES-01 / F-033 / F-039 | Pages source config vs served tree disagree; owner decision (Q-40) |
| I-FE0-07 / F-V4-01 | injury PDF **bytes** not archived (sandbox egress HTTP 000 to ak-static); transcripts + content hashes + official URLs published; probe.yml records reachability. Registered as Q-42 |
| I-FE0-03a | v2 `official.py` still states PF/PA are summed from finals rather than read from the three stat pages; the v4 capture HAS all three pages re-read. Disclosed on both surfaces |
| F-043 | nightly ingest's official-finals fetch failure cause still unverified; `tools/probe_official.py` + `probe.yml` now gather the evidence on demand |
| G6 / F-V4-04 | no licensed odds feed — all staking blocked, w_market blank. Registered as Q-43 |
| G-F3 (v3 advisory) | the v3 build still points at the 2026-11-15 06:00ET release rather than the newest indexed 06:15ET one (per PR #99 audit ④); the v3 tree is a frozen pre-tip snapshot and this is disclosed on its pages. The fix belongs to the v3 owner scope; the newest-release picker in `refresh.py` (PR #80 port) prevents recurrence in the live path |

## 6. Scope discipline

Every integrated artefact was re-verified on the combined tree before commit. No sealed
ledger was rewritten (both seals verify byte-identical). No claim from another session's
record was edited — takeover notes were appended alongside the preserved records. Generated
trees were regenerated only through the CI-order rebuild chain and commit as a fixed point.
