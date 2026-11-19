# Session `arena/af5df7a7-nba2` — nightly publish repair (2026-11-19)

## What was broken (reproduced before any edit, on the pristine `a5380e1` tree)

The scheduled job `Nightly ingest + settlement` has two jobs. `capture` has been green
(all four surfaces success) since the transport repair (PR #121); `publish` failed at
**"Rebuild every tree from the committed capture"** on every scheduled run:

- run [44328569212](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44328569212) (2026-11-18T14:51Z capture)
- run [44381003145](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145) (2026-11-18T19:30Z capture) — `data/raw/refresh_verdict.json` shows
  `injuries=success, finals=success, rolling=success, v4=success`, publish exit 1.

Local reproduction (Python 3.11, same tree):

```
python3 -m nba2.pipeline.settle ...   -> writes the union; nothing in CI ran it
python3 -m nba2.settlement_page       -> exit 1  "data/raw/official_finals_union.json is stale — run: python -m nba2.pipeline.settle"
python3 -m nba2.v6                     -> exit 1  G-V6-8: games 0022600231-0022600240 "no official URL at all"
```

## Root causes and fixes (each fix is a reader or a wiring change; no gate moved)

### 1. The finals union was never rebuilt by CI
`data/raw/official_finals_union.json` is written only by `nba2.pipeline.settle`, which the
rebuild chain never ran. Every capture that added official finals sources
(`raw/finals_*.json`, `capture_*/results_*.json`, `data/v2/results.json`) left the union
stale, and `nba2.settlement_page` — fail-closed by design — refused to render.
Measured at claim time: fresh `build_union()` = 36 records vs 31 on disk; the five 11/17
finals (0022600253–257) were missing.

**Fix:** `.github/workflows/refresh.yml` runs `python3 -m nba2.pipeline.settle` and
`python3 -m nba2.v4.settlement` in the rebuild, **only when the finals leg succeeded**
(when finals are unavailable the settlement files must stay byte-identical to HEAD — the
existing guard step checks exactly that, and the job still ends red with the visible
settlement notice). The "Commit the rebuild" add-list now matches `publish-parity.yml`'s
drift surfaces (`site`, the v1 tree incl. `data/site-built.json` + root `*.html`) and adds
what the merge writes (`data/settlement.json`, `data/raw/official_finals_union.json`), so
the committed tree is a fixed point of the rebuild.

### 2. Three finals readers were blind to the aliases the committed feeds literally use
- `nba2/v6/results_coverage.py::finals_committed` was first-file-wins across files and read
  only `source_url`/`official_source`, so the sparse `data/raw/finals_2026-11-1x.json` rows
  (keys `source`, `final_source_url`, `away_team`/`home_team`) shadowed the URL-carrying
  `capture_*/results_*.json` rows for the same games. G-V6-8 (every game row must point at
  an official nba.com document — a **correct**, fail-closed gate) failed on 14 games whose
  URLs are committed. Fixed: cross-file merge fills blanks (score disagreements still flag
  as conflicts; a non-null value never overwrites another committed value), aliases
  normalised exactly as `nba2/pipeline/settle.py::normalise_source` reads them, `rows` key
  added to `_records_of` (v2/results.json uses it), and the `matchup` fallback no longer
  prints `"None @ None"` (f-strings are always truthy).
- `nba2/pipeline/settle.py::normalise_source` read `away`/`home`/`away_quarters` only, so
  union rows for 0022600253–257 carried **no teams and no quarter rows** although both are
  in the committed official file — and the quarter-sum rejection rule was silently skipped
  for them. Fixed: alias keys (`away_team`/`home_team`, `away_q`/`home_q`,
  `final_source_url`, and the gamebook captures' team-keyed `quarters` map), and
  `_records_of` returns every game-shaped row (`records`/`rows`/`games`/`results`) as its
  own candidate so a within-file disagreement is caught by the same conflict rule as a
  cross-file one. Union after the fix: 36 records, 0 conflicts, 0 rejected rows, teams +
  quarters on 35/36 (0022600035's quarters are blank-and-flagged at capture time — never
  inferred).
- `nba2/v4/settlement.py::FINALS_SOURCES` is a hand-maintained list that ended at 11/16, so
  the **five sealed 11/17 picks stayed ungraded** although both independent official feeds
  are committed (`data/raw/finals_2026-11-17.json`, `capture_2026-11-18/finals_2026-11-18.json`).
  Fixed: both sources added (rule 3 cross-checks them against each other and the 11/16
  overlap; a disagreement raises and nothing settles), team aliases in `finals()`, and the
  provenance table's `method` cell falls back to an explained blank when the capture file
  does not file one. Settlement now: **71/83 graded** (was 61/83), all three seals
  re-verified before grading, stamp `2026-11-17T23:59:59Z` (end of the latest graded game
  day — deterministic).

### 3. The v6 coverage clock was a hand-pinned constant that went stale behind the ingest bot
`AS_OF_DATE = "2026-11-17"` froze "has this date ended?" — but the committed captures kept
advancing, and `test_a_date_that_has_not_ended_is_not_reported_as_a_gap` began asserting
the impossible (11/17 has no finals while five are committed). Fixed: the clock is derived
from `data/raw/refresh_verdict.json`'s `attempted_at_utc` (pure function of committed files
— a rebuild of the same commit answers the same way, so the deploy-parity rule still
holds), with a documented fallback constant. Also fixed the `graded` definition in
`graded_ids()`: the settlement's `finals_used` list includes every final it *read*; a game
with a final but no sealed pick was never pre-registered and cannot be graded — counting
`finals_used` reported the 11/13 games as graded. They now report 0 graded with the
"never pre-registered" reason the test pins.

### 4. The v3 test suite rebuilt the published tree in-suite (A6-1's failure mode, v3 side)
`nba2/v3/test_v3.py::TestPublishedPages` called `B.build()` unguarded: a test run flattened
the v4/v5/v6 nav grouping on v3's 12 pages, so any commit made after running tests captured
**test output instead of pipeline output** and the zero-tolerance `publish-parity` diff
would fail. (This is how an earlier rebuild attempt of this session's went astray; the
mechanism is documented in `nba2/v2/test_v2.py`'s A6-1 comment but was never applied to
v3.) Fixed: the same `_preserved()` snapshot/restore context A6-1 uses, around both
build-calling tests. Verified: after a full chain + gates + all suites, `git status` is
byte-identical to the chain output.

## Verification performed (exact commands, 2026-11-19)

```
chain (workflow order): nba2.pipeline.settle, nba2.v4.settlement,
  nba2.pipeline.build_site_data, nba2.pipeline.build_site, backtest.engine.build,
  nba2.v2, nba2.settlement_page, nba2.v3, nba2.v4, nba2.v5, nba2.v6   -> 11/11 rc=0
gates: nba2.v2.check, nba2.v3.check, nba2.v4.check, nba2.pipeline.lint -> 4/4 rc=0
  (lint: 1436 rows across 50 tables, every row sourced, every blank explained)
tests: nba2/tests, nba2/v2 (167), nba2/v3, nba2/v4, nba2/v5, nba2/v6 (54, incl. 8 new
  regression tests in nba2/v6/test_results_merge.py)                   -> 6/6 OK
python3 -m nba2.pipeline.seal_predictions --verify                      -> VERIFIED
tools/check_links_all.py -> 143 HTML files, 7304 internal links, ALL OK
tools/crosscheck_site.py  -> 97 checks: 86 pass, 2 fail, 9 info —
  CC-DOC-01 (README counts vs artefacts): non-gating in refresh.yml by design; the README
  is owned by the concurrent docs-audit session arena/53c5afeb-nba2 (its commit
  "docs: correct verified test count" is in flight). Not touched by this session.
  CC-FRESH-01 (snapshot age): non-gating by design; the v2 legacy snapshot is 2026-11-14/15
  era and re-cutting the model to the newest capture is the deferred ACF-7/RQ-8892-02 task
  (7-step spec in analysis/session-8892d20c-capture.md §4). Not touched by this session.
fixed point: the exact publish-parity rebuild chain (no settle) reproduces the committed
  tree byte-for-byte (git status = 0). Re-running settle moves only data/settlement.json's
  stamp and the 3 renders that embed it — by design (the stamp must be visible).
```

## AF-6 — disposition of the two stale PRs (never silent)

- **PR #125** (`arena/934fce54-nba2`, last commit 2026-11-17 17:02): closed; disposition
  comment posted ([link](https://github.com/wingbangboozle1-lang/NBA2/pull/125#issuecomment-7001702683)).
  Superseded by PR #123 (fde5a90) — evidence in the comment: `data/v5/gamebooks_2026-11-16.json`
  and the `gamebooks_2026-11-16.json` TRANSCRIPTS entry are already on main; merging the
  branch now would revert regenerated state rebuilt from the 11/18 captures. Salvage list
  (RQ-AF6-1): the `ast_blank_reason` plumbing in `nba2/v5/transcript.py`, and parts of its
  `nba2/v3/build.py` diff not independently re-done. (The PR was already closed at
  2026-11-19T06:05:01Z by another actor before this session ran `gh pr close`; the
  disposition comment stands.)
- **PR #112** (`arena/a11505e1-nba2`, last commit 2026-11-16 19:24, checks backtest=FAIL
  parity=FAIL at its tip): closed; disposition comment posted
  ([link](https://github.com/wingbangboozle1-lang/NBA2/pull/112#issuecomment-7001707150)).
  Superseded-stale: PRs #113–#123 performed its assembly (repo-review final integration,
  11/16 settlement, fail-closed finals fallback, v6 measurement pages); merging 72
  regenerated 2026-11-16-era files would revert the current tree. Salvage list (RQ-AF6-2):
  `nba2/v2/test_refresh_gate_audit.py` (274 new lines), the v3 G-F5 dated-snapshot gate
  redefinition, ~180 lines across `nba2/v3/{build,check,ledger}.py`, `nba2/v5/publish.py`
  tweaks, cosmetic `travel.py` cleanup. (Also already closed at 06:05Z by another actor;
  the disposition comment stands.)

## Rules this session held

Values published only from committed official captures or committed code; unconfirmed ⇒
blank + flagged, never inferred; sealed ledgers never rewritten (`seal_predictions --verify`
re-run before every commit — VERIFIED); every gate kept fail-closed (G-V6-8's wording and
standard unchanged — it now *passes* because the reader finally surfaces the provenance the
gate demands; the union's quarter-sum rejection now runs on *more* rows); small commits;
`git pull --rebase` before every push.

---

## Integration addendum (same session, 2026-11-19)

`main` moved underneath this work: PRs **#126–#129** (sessions `0b91edfc`, `be1ea6bf`,
`53c5afeb`) independently fixed parts of the same breakage and merged before this session's
PR. Per the board's reconciliation precedent ("keep the CI-verified fixed point; keep only
what is unique"), the integration merge (`d787919`, logged conflict-by-conflict in its
commit message) took main's versions of the doubly-fixed v6 files and kept this session's
unique deltas: the refresh.yml settle-in-rebuild wiring + full commit add-list, the
`pipeline/settle.py` gamebook/`_records_of`/team-keyed-quarters reader extensions, the
`v4/settlement.py` 11/17 finals gap (61/83 → **71/83 graded**), the `v3/test_v3.py`
`_preserved()` fix, and the `graded_ids()` `finals_used` removal (which the merged
combination had turned into a false "9 graded" for the never-registered 11/13 games —
reproduced in CI-equivalent tests before the fix).

- **PR #132** (nightly publish repair + integration) — merged; all required checks green
  including the zero-tolerance publish-parity. https://github.com/wingbangboozle1-lang/NBA2/pull/132
- **PR #133** (coverage-page `None @ None` matchups + stale schedule-link dates, found
  while verifying the live deploy) — merged. https://github.com/wingbangboozle1-lang/NBA2/pull/133
- **Pages**: `pages build and deployment` green on both merges (legacy Jekyll from
  `main /`); live fetches of the root landing, `settle.html` and `results-coverage.html`
  show the merged tree (71/83 graded, deterministic stamp `2026-11-17T23:59:59Z`, quarter
  sums per row, never-pre-registered 11/13 games reported as 0 graded, per-date schedule
  links, resolved matchups). GitHub's edge caches pages for minutes after a deploy — a
  `?v=` query bypasses it (verified against the GitHub contents API first).
- **Parallel PRs**: #131 (stable settlement stamp — welcome as a focused PR on current
  main; its workflow band-aid superseded by `_preserved()`) and #130 (v7 layer — left open
  with explicit status: needs rebase + line-by-line re-verification, takeover-able past the
  60-minute rule). Status comments posted on both.
