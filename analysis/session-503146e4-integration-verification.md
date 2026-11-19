# Session `arena/503146e4-nba2` — final integration + stale-claim takeover (2026-11-19)

Role taken per the board protocol: **final integration**, plus the sanctioned **stale-claim
takeover** of the two open PR branches (>60 min idle with no commits). Full write-up of what
was merged, how conflicts were resolved, what was re-verified, and what remains flagged.

## 1. State read at claim time (2026-11-19 12:18 UTC, measured)

| Fact | Evidence |
|---|---|
| Branch base | `41cfd81` = `main` (merge of PR #133) |
| PR #131 `arena/8c7c8828-nba2` | all 6 checks pass (`backtest`, `capture`, `parity`, `refresh-dry-run`, `v2`, `verify`), open, last commit 06:28Z — **>5 h idle** |
| PR #130 `arena/6023d517-nba2` | **3 checks failing** (`parity` "The v1 tree must equal a rebuild", `v2` "Existing pipeline still passes", `verify` "Model + pipeline tests"), open, last commit 06:16Z — **>5 h idle** |
| Pages config | `build_type: legacy`, source `main /` — the published artefact is the generated root `index.html` pointer to `site/` (README F-062) |
| Handoff rule | COORDINATION.md: a claim >60 min old with no commits may be taken over and the handoff noted |

## 2. What was integrated (nothing discarded)

1. **PR #131 branch merged first** (`e4a5e87`): settlement-rebuild determinism
   (`nba2/pipeline/settle.py`), the finals-transport regression tests
   (`nba2/tests/test_finals_pages.py`, `test_refresh_workflow.py`), the date-scoped v6
   coverage reader (`nba2/v6/results_coverage.py`), the derived as-of clock, and the
   refresh/Pages/parity workflow ordering (settle before any render).
2. **PR #130 branch merged second** (`b01c935`): the v7 layer cut from the official pages
   read on 2026-11-19 (`nba2/v7/**`, `data/v7/**`, `site/v7-*.html`), the G-V6-8 reader
   repair (alias resolution for `away_team`/`final_source_url` spellings), the v7 nav
   category, and their nine v7 flags.

### Conflict resolutions (each documented inline in the code)

| File | Resolution | Why |
|---|---|---|
| `nba2/v6/results_coverage.py` — as-of clock | kept **both** clock derivations: `latest_capture()` (6023d517: broad scan of every committed capture, call-time paths) unioned into `_as_of()` (8c7c8828: a **failed** finals verdict never advances the clock), typed fallback = the committed `capture_2026-11-18` stamp 2026-11-18T19:30:20Z (af5df7a7) | both sessions independently derived the clock from committed evidence; the union is strictly more evidence, and the two pinned test families both pass |
| `results_coverage.py` — reader | kept 6023d517's `_records_of` / `_ALIASES` / `_final_record` normalisation (fixes the 14 URL-less rows as a reader defect) + af5df7a7's **team-conflict refusal** + a `_merge_into` corrected to its own call-site contract (fill blanks only; never overwrite) | 6023d517's `_merge_into` as first shipped overwrote non-null values despite its call-site comment saying "fills blanks; never overwrites" — the fill-only rule is the board policy and both comments' intent |
| `results_coverage.py` — source links | `_https_url()` filter: an explicit HTTPS URL is required before any value is published as a link (af5df7a7's "a prose label is never promoted into a link") | provenance rule |
| `results_coverage.py` — `graded_ids()` | graded = v4 ledgers' graded rows ∪ nightly `settled_rows` (8c7c8828's coverage); `finals_used` ids surfaced in `info["finals_used_ids"]` as **provenance only**, never counted as graded (af5df7a7's rule) | counting `finals_used` would print the never-pre-registered 11/13 games as graded — contradicted by both branches' own `test_the_prequest_1113…` (n_graded=0) |
| `nba2/v6/test_v6.py` | kept every unique test from both sides; **replaced** the two typed-date "not ended" tests with 6023d517's clock-dynamic pair (K-07 rule: stale test logic is updated, never used to suppress committed captures); 8c7c8828's synthetic `graded_ids` test expectation aligned with the resolution above | typed dates break the moment an ingest commits new finals — exactly the defect class both sessions documented |
| `.github/workflows/refresh.yml` | 8c7c8828's test-pinned gate (`CAPTURE_FINALS` env, "Official finals unavailable…" message, settle before `build_site_data`) **plus** af5df7a7's `python3 -m nba2.v4.settlement` step and superset commit list | both PRs' wiring kept; `test_refresh_workflow.py` passes |
| `COORDINATION.md` | append-only concatenation of every session record from both sides | board rule |
| generated (`data/**`, `site/**`, `pages/**`) | resolved only by regenerating through the committed builders (`settle` → `v4.settlement` → `build_site_data` → `build_site` → `backtest` → `v2` → `settlement_page` → `v3` → `v4` → `v5` → `v6` → `v7`) | repo rule: generated files are never hand-edited |

### Root cause of PR #130's three failing checks (measured)

`git diff origin/arena/6023d517-nba2 HEAD -- nba2/pipeline/settle.py` shows their branch
predates both the multi-key `_records_of` reader and the settlement-rebuild determinism
work: each rebuild re-stamped `data/settlement.json`, so **"the v1 tree must equal a
rebuild" could never pass** and the fixed-point/idempotence root tests failed with it.
On the integrated tree (8c7c8828's determinism fix + regenerated fixed point) the same
suites pass. No gate was lowered.

## 3. Verification performed on the integrated tree (all re-run after the merge)

| Check | Result |
|---|---|
| `nba2/tests` (model + pipeline) | **99 tests OK** |
| `nba2/v2` tests | 167 OK |
| `nba2/v3` tests | 67 OK |
| `nba2/v4` tests | 61 OK |
| `nba2/v5` tests | 26 OK |
| `nba2/v6` tests | 65 OK |
| `nba2/v7` tests | 37 OK |
| `python -m nba2.v2.check` / `v3.check` / `v4.check` | 0 structural / 8-of-8 gates / 8-of-8 gates (incl. settlement hash `6a624740bcd0fd52` + projection/bet wall) |
| `python -m nba2.v6 --check-only` | 13/13 gates (in the build), check-only clean |
| provenance lint | **1,436 rows / 50 tables — every row sourced, every blank explained** |
| `tools/check_links_all.py` | 148 files, **8,021 internal links OK** |
| `tools/verify_site.py` | 13 pages / 249 data rows / 303 links — every row has a source link |
| `python -m nba2.pipeline.seal_predictions --verify` | both seals VERIFIED (`cf7dedc6…`, `c841e8f3…`), site prints the recomputed digest |
| fixed point | full ordered chain re-run → `git diff` **byte-identical** |
| `tools/crosscheck_site.py` | 97 checks: **87 pass / 1 fail / 9 info** — the one fail is `CC-FRESH-01` (see §5) |

### Live re-read of official sources (2026-11-19, ~12:20–12:40 UTC, independent of any session transcript)

Read directly from the league's own pages and compared row-by-row against the committed
transcription in `nba2/v7/official.py`:

| Official source | Compared | Matched | Mismatched |
|---|---|---|---|
| [nba.com/standings](https://www.nba.com/standings) | 30 clubs (W–L) | **30** | **0** |
| [nba.com/games?date=2026-11-18](https://www.nba.com/games?date=2026-11-18) — 12 finals (ids, clubs, scores) | 12 games | **12** | **0** |
| [nba.com/games?date=2026-11-19](https://www.nba.com/games?date=2026-11-19) — 4 games (ids, clubs, 8:00 PM ET tips) | 4 games | **4** | **0** |
| [official.nba.com injury report index](https://official.nba.com/nba-injury-report-2026-27-season/) | 11/19 revision family present (12:00 a.m → 7:45 a.m ET so far, 15-min revisions) | yes | — |

Example verified rows (manual review links): [HOU 119–104 IND](https://www.nba.com/game/hou-vs-ind-0022600259),
[PHI 121–116 ORL](https://www.nba.com/game/phi-vs-orl-0022600261),
[MIL 130–137 MIA](https://www.nba.com/game/mil-vs-mia-0022600260),
[MEM 124–121 CLE](https://www.nba.com/game/mem-vs-cle-0022600258),
[CHI 137–107 BKN](https://www.nba.com/game/chi-vs-bkn-0022600262),
[WAS 103–99 TOR](https://www.nba.com/game/was-vs-tor-0022600263),
[GSW 94–116 DAL](https://www.nba.com/game/gsw-vs-dal-0022600267),
[ATL 117–112 OKC](https://www.nba.com/game/atl-vs-okc-0022600265),
[DET 122–109 NOP](https://www.nba.com/game/det-vs-nop-0022600264),
[BOS 101–105 DEN](https://www.nba.com/game/bos-vs-den-0022600266),
[PHX 128–107 SAC](https://www.nba.com/game/phx-vs-sac-0022600269),
[UTA 109–97 LAL](https://www.nba.com/game/uta-vs-lal-0022600268).
Slate tips: [GSW@MEM](https://www.nba.com/game/gsw-vs-mem-0022600270),
[POR@MIL](https://www.nba.com/game/por-vs-mil-0022600271),
[NYK@MIN](https://www.nba.com/game/nyk-vs-min-0022600272),
[LAC@SAS](https://www.nba.com/game/lac-vs-sas-0022600273) — all 8:00 PM ET.

The v7 window arithmetic also re-checked against the official calendar strip
(11/19 → 4, 11/20 → 9 incl. Cup groups, 11/21 → 6 = 19 rows in `data/v7/slate.json`).

## 4. Irregularities flagged for owner review (none blocks anything)

1. **`CC-FRESH-01` — legacy v1/v2 model snapshot is 2026-11-14-era** while the v7 layer is
   cut from the 2026-11-19 official pages. The freshness cross-check stays visible and
   non-gating; `site/index.html` discloses the non-live snapshot. Re-cutting the *legacy*
   inputs remains the deferred ACF-7 / RQ-8892-02 task. The brief's "re-read the three
   team-stat pages and re-cut the model inputs" is satisfied in the v7 layer (30/30 on
   traditional/opponent/advanced, both estimator identities hold).
2. **`F-V7-AVAIL` — the 11/19 injury report is not read into the availability column.**
   Verified this session that the official revision family exists
   ([index](https://official.nba.com/nba-injury-report-2026-27-season/)); the column is
   published **blank with its reason** per the never-infer policy. The nightly ingest
   archives the PDFs under `data/raw/pdf/` with timestamps and diffs.
3. **Verdict-vs-run disagreement** (raised by session 6023d517): scheduled run
   [44381003145](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145)
   concluded **failure** while its committed `refresh_verdict.json` records all four
   surfaces `success`. The verdict file is capture evidence; the run conclusion is the
   pipeline's. Cause not yet measured — left visible for review.
4. **`CC-DOC-01` was repaired this session** (K-01 documentation-drift class, counts only):
   README claimed 62/92/64/40 tests where the artefacts hold 99/99/67/65. Historical
   narrative counts ("59 tests (was 43)") were left untouched — a record of the past is
   not a current claim.
5. **Two typed-date v6 tests were superseded** by clock-dynamic equivalents (K-07 rule),
   with the rationale recorded in the test docstring and above. No assertion about
   committed data was loosened.

## 5. Follow-up requests left on the board (unclaimed)

- **RQ-AF6-1** — port the `ast_blank_reason` plumbing from closed PR #125 (`nba2/v5/transcript.py`).
- **RQ-AF6-2** — salvage `nba2/v2/test_refresh_gate_audit.py` and the G-F5 dated-snapshot
  gate redefinition from closed PR #112.
- **ACF-7 / RQ-8892-02** — the legacy model re-cut (see §4.1).
