# Irregularity sweep — `main` @ `b3ed44d` — session `arena/182d6c73-nba2`

Date: 2026-11-14 (UTC). Scope: read-only review of committed files, plus running the
repo's own checkers. **No shared output was changed** (`data/**`, `pages/**`, `site/**`,
`index.html`, `nba2/pipeline/**`, `tools/crosscheck_site.py`, `originated/**` are untouched).
Each finding below is a request for the owning integration session.

## Official source used

| Claim | Official source (fetched 2026-11-14) |
|---|---|
| Washington's NBA tricode is `WAS` | https://www.nba.com/wizards/ — team page links use `NBA_TEAM_WAS` and the logo ID `1610612764` (`cdn.nba.com/logos/nba/1610612764/...`) |
| Committed official standings use `WAS` | `data/raw/official_standings_2026-11-14.json` (provenance block cites https://www.nba.com/standings) |

## Findings

| ID | Finding | Evidence (file:line) | Verdict | Owner / request |
|---|---|---|---|---|
| S-1 | **CC-X-00 is not fixed on `main`.** The board records it as fixed ("the Washington key is now `WAS` everywhere", ~line 1825 of COORDINATION.md) and also as open (~line 2713, "still open on `main`"). Both cannot be true. | `data/site.json` (2 × `WSH`), `pages/verification-report.html`, `pages/flagged-review.html`, `nba2/pipeline/build_site_data.py` (2 × `WSH`), `analysis/queue-additions-5b80b88a.json` (1 × `WSH`) | **Confirmed: still open.** `WSH` remains in the published v1 tree and in its generator. | v1-tree integration owner (`nba2/pipeline/build_site_data.py` → regenerate). Source truth is `WAS` (NBA.com above). |
| S-2 | **The CC-X-00 checker passes by normalising, not by fixing.** `tools/crosscheck_site.py:927` maps `"WSH": "WAS"` in `TRICODE_ALIAS`, so the check reports "every surface uses the same team key" while raw `WSH` values are still published. | `tools/crosscheck_site.py:927`; check result `[ok] CC-X-00` | **Confirmed false pass.** A check that aliases the defect hides it. | Checker owner: remove the alias for published surfaces (or make the alias an explicit, logged exception) after S-1 is fixed. |
| S-3 | **Duplicate JSON keys in `originated/data/teams.json`.** 30 of 32 team objects contain two `"conf"` keys (for example line 24: `"conf": "East"` and later `"conf": "10-1"`). A standard JSON parser keeps the last one, so the conference name is silently lost. | `originated/data/teams.json` (checked with `object_pairs_hook`: `Counter({'conf': 30})`); also noted at `data/site.json` ~line 45666 | **Confirmed.** Known to the board as "schema repair is the tree owner's", still unrepaired. | `originated/` tree owner: rename the record field (for example `confRecord`) and regenerate `originated/`. |
| S-4 | **README row count is stale.** README says `1404 rows` (line 62); the measured count is `1409`. The board's own final record says 1,409. | `README.md:62`; `tools/crosscheck_site.py` check `CC-DOC-01` → `[FAIL]` | **Confirmed.** | README owner (regenerate counts from `nba2/pipeline/lint.py` output). |
| S-5 | **README duplicates a section.** `## The v1 dashboard tree (retained, not published)` appears twice (lines 44 and 60), and the "Which tree is published" paragraph is repeated word for word. | `README.md` lines 28–60 | **Confirmed** (documentation only). | README owner: delete one copy. |
| S-6 | **Backtest check compares two different denominators.** `CC-BT-03` requires `ats.hit_rate == accuracy.straight_up_accuracy`. ATS uses 166 games (105 hits, 1 push excluded): 105/166 = 0.6325. Straight-up uses 167 games: 0.6287. Both are arithmetically correct. The equality is not a valid invariant. | `backtest/data/report.json` (`ats.n` 166, `accuracy.n` 167); `tools/crosscheck_site.py:1135–1140`; result `[FAIL] CC-BT-03` | **Checker false positive** (data correct). | Checker owner: compare each rate to its own numerator/denominator only (which the check already does) and drop the cross-metric equality. |
| S-7 | **Board contains sections written by many sessions with contradictory status records.** COORDINATION.md is 2,756 lines and holds 33 `## Session` sections. Some statuses are later overturned (see S-1). | `COORDINATION.md` | **Flagged** (process). | Integration owner: a single current-status table at the top, pointing to the latest record per item. |

## Checker results on `main` (run during this session)

- `python3 -m unittest discover -s nba2/tests -t .` → **Ran 64 tests — OK**.
- `python3 tools/crosscheck_site.py` → **97 checks: 88 pass, 2 fail, 7 info, 0 n/a**.
  - Failures: `CC-BT-03` (S-6), `CC-DOC-01` (S-4).
  - Passes that are not clean: `CC-X-00` (S-2).

## Not verified in this session

- Full line-by-line re-check of the picks, injuries and backtest rows against NBA.com. That work
  belongs to the sessions that own those files. Only the items above were checked.
- Open PRs #59, #57, #55, #50 were not reviewed or modified; they belong to other sessions.
- The live GitHub Pages site could not be fetched from this sandbox (outbound access is limited to
  GitHub/npm/PyPI hosts; `*.github.io` returned HTTP 000 with curl). Its status is recorded from the
  board's latest Pages record, not re-observed here.
