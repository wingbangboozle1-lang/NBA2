# Session `arena/e73ca9d5-nba2` — settlement verification record (2026-11-16 UTC)

Scope and claim: `COORDINATION.md` (claim `3d6d207`, scope revision appended in this session).
Base: `main` @ `1c48226` (PR #81 merge).

## 1. What was wrong (IR-1)

`nba2/pipeline/settle.py` read one file by name (the newest `finals_*.json`), which was
`data/raw/finals_all.json`, holding only nine 2026-11-13 games. Neither sealed ledger
(`sealed-2026-11-13.json`, `sealed-2026-11-14.json`) covers those games, so the settlement
reported 0 settled. The official finals for 11/14 and 11/15 were committed elsewhere, but the
settler never read them.

## 2. What changed

| Path | Change |
|---|---|
| `nba2/pipeline/settle.py` | Finals are the keyed union (by `game_id`) of every committed official source. A game with conflicting scores is excluded, never averaged. A quarter row is rejected unless its sum equals the final (OT periods counted). Each game keeps its source list. Out-of-repo paths are labelled, not made relative. |
| `nba2/tests/test_settle.py` (new) | 9 tests: union, conflict exclusion, quarter check with OT, pending handling. All pass. |
| `data/raw/results/results_2026-11-15.json` (new) | Six official finals for 11/15 with quarter scores; three games still in progress are listed as not scored. |
| `data/raw/results/gamebook_recheck_2026-11-14.json` (new) | Independent re-read of the five 11/14 finals from the official gamebook PDFs. |
| `data/raw/official_finals_union.json` (new, generated) | 20 games from 5 committed official source files; 0 conflicts; 0 rejected quarter rows. |
| `nba2/settlement_page.py` (new) | Writes `site/settlement.html`. Pure function of committed files. Refuses to build if the union on disk is stale. No timestamps. It does not edit any other page. |
| `site/settlement.html` (new) | Generated settlement stamp page. |

## 3. Result

- Ledger `sealed-2026-11-13.json` (seal `cf7dedc6…`, 22 predictions): **11 of 22 settled**.
- Ledger `sealed-2026-11-14.json` (seal `c841e8f3…`, 27 predictions): **11 of 27 settled**.
- Both seals re-verified before and after the settlement run. Ledger files were not changed.
- Settled rows, by the ledger's own `date` field:
  - 2026-11-14: 0022600231 DEN@NOP, 0022600232 DAL@CLE, 0022600233 DET@MIA, 0022600234 BKN@MEM, 0022600235 CHI@MIN
  - 2026-11-15: 0022600236 IND@PHI, 0022600237 LAL@PHX, 0022600238 CHA@LAC, 0022600239 SAS@UTA, 0022600240 DAL@BOS, 0022600241 NYK@TOR (OT)
- Not settled (no official final committed): 0022600242 HOU@WAS, 0022600243 ATL@MIL, 0022600244 OKC@SAC (in progress when read), and every 11/16 and 11/17 game.

## 4. Source checks

Each of the five 11/14 finals was re-read from its official gamebook PDF (`statsdmz.nba.com/pdfs/20261114/…`). Each quarter row sums to its final, and the finals match the committed values.

| Game | Gamebook final | Gamebook quarters | Match |
|---|---|---|---|
| DEN@NOP | 116–108 | 29-27-30-30 / 23-28-31-26 | yes |
| DAL@CLE | 117–127 | 33-20-38-26 / 33-38-34-22 | yes |
| DET@MIA | 117–137 | 39-21-26-31 / 37-31-35-34 | yes (see flag F-2) |
| BKN@MEM | 110–129 | 23-31-30-26 / 38-33-32-26 | yes |
| CHI@MIN | 117–106 | 29-29-30-29 / 17-28-35-26 | yes |

The 11/15 finals were read in the earlier capture from the gamebooks (`statsdmz.nba.com/pdfs/20261115/…`) and the game pages. The DAL@BOS quarter row in that gamebook is garbled and is not used.

## 5. Flags (for review; none blocks the merge)

- **F-1 DAL@BOS quarter split is not verified.** The gamebook's quarter row is internally inconsistent (it sums to 11, not 94). The row is stored with null quarters and shown as "quarter split not verified". Not back-solved.
- **F-2 DET@MIA gamebook has two SCORE BY PERIOD tables.** The first reads DET 20-21-26-21 (sums to 88, not 117) and is not used. The second reproduces both finals and is the one used.
- **F-3 Ledger file names do not match their contents.** `sealed-2026-11-13.json` holds predictions dated 11/14–11/16, and `sealed-2026-11-14.json` holds 11/14–11/17. Filed as an observation only; the ledger files were not edited.
- **F-4 Stray writes during testing.** Running `python -m unittest discover` rewrites `data/site.json` and renders `pages/*.html` (through `test_rebuild_produces_identical_rows`). Those changes were reverted. They were not part of the deliverable.
- **F-5 Coupling between settlement and site build.** `data/site.json` embeds the state of `data/settlement.json`. Regenerating the settlement file changes the site build's input digest, and the committed `site.json` then fails the reproducibility test. See request R-2.

## 6. Requests for the final integration session (not done here)

- **R-1 Settlement nav link.** Add a "Settlement stamp" link to `site/settlement.html` in the shared navigation. This session did not edit any other page. `nba2/settlement_page.py: inject_link()` exists for that session to call deliberately.
- **R-2 Regenerate the settlement outputs together.** Run `python -m nba2.pipeline.settle`, then `python -m nba2.pipeline.build_site_data`, then `python -m nba2.settlement_page`. Commit `data/settlement.json`, `data/site.json` and the affected `pages/*.html` in one change. Doing it separately breaks the reproducibility test on main. Committing `data/settlement.json` alone was rejected for that reason.
- **R-3 CI wiring.** Add `python -m nba2.settlement_page` to the Pages workflow (or the parity job) so the page is regenerated and diffed. Not added here because `.github/workflows/pages.yml` and `publish-parity.yml` are shared.
- **R-4 Overlap with PR #72.** PR #72 also touches `data/settlement.json`, `data/site.json`, `pages/*.html`, and `nba2/pipeline/build_site_data.py`. Whichever merges second needs R-2 re-run against the merged state.
- **R-5 Remaining settlements.** Once HOU@WAS, ATL@MIL and OKC@SAC have official finals committed (with a gamebook re-read), the settler should be re-run. The ledgers' 11/16 and 11/17 games settle the same way.

## 7. Verification run (this branch, before commit)

- `python3 -m unittest discover -s nba2/tests -t .` — 79 tests, OK (run with the committed `data/settlement.json`).
- `python3 -m nba2.v2.check` — OK, 0 structural, 0 semantic.
- `python3 -m nba2.v3.check` — OK, 0 structural, 0 semantic (gates: 7 pass, 1 advisory fail, as before).
- `python3 tools/check_links_all.py` — 125 HTML files, 5,796 internal links, ALL INTERNAL LINKS OK.
- Settlement page: byte-identical on a rebuild of unchanged inputs.
- A v2 structural check first flagged the seal rows as having no source link. That is fixed (each row links to the committed ledger file).
