# Session arena/934fce54-nba2 — capture, verification and integration notes (2026-11-17)

Scope claimed in COORDINATION.md: tasks 93-1 … 93-7 — official result feed + settlement
continuity for the 2026-11-16 game day, v3/v4/v5 surfaces only.

## 1. What was captured (93-2, 93-3)

Eight official NBA gamebooks for Monday 2026-11-16, read through the platform page-fetch
tool on 2026-11-17 in the window ~16:05–16:25 UTC (bash egress to statsdmz.nba.com is
blocked in this sandbox — HTTP 000 — so PDFs cannot be archived; provenance = URL +
retrieval window, the established v5 convention):

| game_id | matchup | final | quarters (A / H) | gamebook |
|---|---|---|---|---|
| 0022600245 | ORL@BOS | 115–105 | 20·30·25·40 / 17·24·36·28 | https://statsdmz.nba.com/pdfs/20261116/20261116_ORLBOS_book.pdf |
| 0022600246 | CHI@CLE | 115–126 | 31·17·31·36 / 25·32·31·38 | https://statsdmz.nba.com/pdfs/20261116/20261116_CHICLE_book.pdf |
| 0022600247 | MEM@WAS | 136–120 | 33·26·42·35 / 35·34·18·33 | https://statsdmz.nba.com/pdfs/20261116/20261116_MEMWAS_book.pdf |
| 0022600248 | PHI@BKN | 135–123 | 33·45·27·30 / 26·33·36·28 | https://statsdmz.nba.com/pdfs/20261116/20261116_PHIBKN_book.pdf |
| 0022600249 | HOU@MIA | 110–128 | 15·31·35·29 / 29·33·39·27 (see F-93-01) | https://statsdmz.nba.com/pdfs/20261116/20261116_HOUMIA_book.pdf |
| 0022600250 | POR@MIN | 98–106 | 26·25·22·25 / 26·33·28·19 (see F-93-02) | https://statsdmz.nba.com/pdfs/20261116/20261116_PORMIN_book.pdf |
| 0022600251 | GSW@NOP | 94–115 | 11·25·29·29 / 35·26·32·22 | https://statsdmz.nba.com/pdfs/20261116/20261116_GSWNOP_book.pdf |
| 0022600252 | PHX@DEN | 117–105 | 20·36·34·27 / 24·29·29·23 | https://statsdmz.nba.com/pdfs/20261116/20261116_PHXDEN_book.pdf |

Transcription convention: `analysis/session-f8f8f2b8-gamelogs-a.py` (verbatim cells,
`min_sec` from MM:SS, `reb` from the gamebook TOT column, official DNP/DND/NWT strings,
nothing derived except the documented F-V5-03 recovery). Built and re-checked by
`audit/session-934fce54/build_capture.py`, which asserts before writing anything:
every quarter row sums to the printed final; every club's players' points sum to the
printed final; every club's players' minutes sum to 240:00 within the PDF rounding
tolerance (5 s); every player row satisfies `pts = 2*(FG−3P) + 3*3P + FT`; every
published rebound/assist sum equals the club's published total.

Outputs:
- `data/raw/capture_2026-11-17-934fce54/results_2026-11-16.json` — `nba2.results-feed.v3`
  (schema-identical to the 11/15 feed file; 8 records, `n_verified_quarters: 8`).
- `data/v5/gamebooks_2026-11-16.json` — `nba2.v5.gamebook-transcript.v1` (8 games,
  16 club blocks, 213 player rows incl. DNP/DND/NWT rows).

## 2. What was integrated (93-4, 93-5)

- `nba2/v5/transcript.py`: the 11/16 transcript joins `TRANSCRIPTS`; blank-reason
  plumbing extended to assists (`ast_blank_reason`), mirrored in `nba2/v5/check.py`
  V5-G7. v5 union now 22 games (5 + 9 + 8 for 11/14–11/16), 768 player rows,
  31 team-games. All 8 v5 gates pass.
- `nba2/v4/settlement.py`: `FINALS_SOURCES` gained the 11/16 feed; the hard-coded luck
  statement ("12 correct winners in 14 distinct games…") now derives from the graded
  rows (16/22 distinct, 0.727 vs 0.576 expected, Poisson-binomial tail 0.0779 —
  inside the noise band, correctly stated); the legacy `settled-2026-11-15.json`
  `finals_used` now lists exactly the game days the seal was graded from (17 rows,
  11/15 + 11/16) instead of the hard-coded 11/15. `settle.html` and
  `data/v4/settlement/settled-all.json` now settle 61 of 83 sealed rows (22 distinct
  games graded, 22 rows UNGRADED = the 11/17–11/18 slate, correctly never a loss).
- `nba2/v3/build.py` (CR-V5-3): `page_results` renders the per-game feed from
  `data/v5/results_union.json` (all committed finals 11/13→11/16, quarter rows with
  the quarter-check sentence, gamebook URL per row) instead of the hard-coded 11/14
  slice; the ratings-history roll-up is relabelled and left untouched; `LD.settle` now
  grades the seal against the union of committed finals instead of
  `date < WINDOW[0]` (which could never match a sealed pick). The v3 seal
  (`data/v3/ledger/sealed-2026-11-15.json`) now carries settlement stamp
  `2026-11-16T23:59:59Z` — 17 graded (9×11/15 + 8×11/16), 17 ungraded (11/17–11/18),
  winner hit rate 0.7647 — and the pre-tip digest `34e144c6…` is unchanged (the
  seal's `sha256` is never rewritten; settlement appends `sha256_after_settlement`).

## 3. Verification (93-5)

- Tests: v1 79 / v2 146 / v3 51 / v4 61 / v5 26 — all OK. (v3's suite is 51 tests after
  the `_preserved` guard split the published-page class behaviour, same assertions.)
- `python -m nba2.pipeline.lint` OK — 1436 rows sourced; `nba2.v2.check` 0/0;
  `nba2.v3.check` 0 structural / 0 semantic (gates 7 pass / 1 soft fail G-F3 — the
  frozen 11/15 snapshot discloses it used the 06:00 AM ET injury release while 06:15 AM
  ET was newest at retrieval; soft, pre-existing); `nba2.v4.check` 8/8;
  `nba2.v5.check` 8/8; `tools/check_links_all.py` — 6871 internal links OK.
- `tools/crosscheck_site.py`: 87 pass, 2 fail, 8 info. Both fails pre-date this session
  and are outside this session's file scope: **CC-DOC-01** (README counts stale:
  text 1423 vs measured 1436 rows, text 70 vs measured 79 v1 tests — README.md belongs
  to the integration session arena/a8b7476a-nba2) and **CC-FRESH-01** (frozen v3
  snapshot 3 days old; the scheduled ingest's finals/rolling refresh failed at
  2026-11-17T14:51:04Z — run 44107633323).
- Fixed point: `python -m nba2.v3 && python -m nba2.v4 && python -m nba2.v5` run twice
  consecutively produces byte-identical trees (the seal's `settled` flag settles at
  `true` from the second build on; the committed artefact is that fixed point).

## 4. Flags (published on the Flagged-for-Review surface by the integration session)

- **F-93-01** HOU@MIA: the full-game SCORE BY PERIOD table's Houston row did not extract
  from the PDF text. The four quarter scores (15, 31, 35, 29) are read from the four
  quarter-box team-total rows of the same official gamebook; corroborated by the
  first-half table ("Rockets 15 31 46"), the cumulative line through three (81) and
  the sum matching the full-game team total (110). No value derived from the final.
- **F-93-02** PORMIN: the first extracted SCORE BY PERIOD row for Portland prints
  garbled cells and is not used; the clean table in the same gamebook agrees with the
  plain-text line. (Same extract class as the F-V5-02/03 spurious-cell quirks.)
- **F-93-03** WAS (MEM@WAS): the extracted rows' rebound cells sum to 32 against the
  club's published 31 and the assist cells cannot be reconciled with the club's 25
  under any alignment of the one short row (Ayton). Following the F-V5-02 disposition,
  no Washington rebound or assist is attributed to a player; club totals carried.
- **F-93-04** HOU (HOU@MIA): four rows (Bogdanović, Sheppard, Tate, Thornton) carry
  one cell fewer than the header; rebound cells sum to 53 vs the club's 52 and assists
  cannot be reconciled with the club's 23. No Houston rebound or assist attributed.
- **F-93-05** MEM (MEM@WAS): the extracted full-game box carries two DNP - Coach's
  Decision rows with no attached player names; no name invented; the thirteen listed
  players account for the full 240:00.
- **F-93-06** PHI@BKN: the gamebook prints Brooklyn #12 as "Ryan Rupert" (full-game
  box) and "Rayan Rupert" (period boxes). The full-game spelling is transcribed; the
  pair is flagged, not folded (the suspect-spelling machinery will see both).
- **F-93-07** MEM@WAS: the extracted DNP status cell for Terance Mann prints a garbled
  doubled designation; transcribed once as "DNP - Coach's Decision".
- **F-93-08** MIA (HOU@MIA): the extracted rows' assist cells sum to 27 against the
  club's published 29 and the OR/DR split cells do not reconcile with the club row
  (15/28 vs 13/27) although the TOT rebound column does (40 = 40). No MIA assist
  attributed. Bam Adebayo's rebound (1) IS recovered per the F-V5-03 precedent — the
  club's rebound total reconciles only with 1.
- **F-93-09** repo defect (fixed here): `nba2/v3/test_v3.py::TestPublishedPages` ran
  the full `B.build()` against the published tree with no restore — the same defect
  class as A6-1 (arena/a6d81367-nba2) already fixed in v2 — so a bare test run dropped
  the v4/v5 navigation blocks from the 12 v3 pages and left `site/` dirty. Found while
  integrating; fixed with the same `_preserved` guard v2 uses. Worth a line in the
  integration session's review.
- **CC-DOC-01 / CC-FRESH-01** — see §3; both pre-existing, in other sessions' scope.

## 5. Requests to the integration session (arena/a8b7476a-nba2) — 93-6

1. CR-V5-3 is resolved on the v3/v4/v5 surfaces (this session): results.html and
   settle.html consume `data/v5/results_union.json`; the sealed ledger settles from the
   verified 11/16 finals with a visible stamp. No site/index/nav changes were made here.
2. Please publish F-93-01 … F-93-09 on `flagged.html` (CR-V5-1) and, for F-93-01/02/03/04/08
   (extraction-cell quirks), keep the "unconfirmed ⇒ blank + flagged" wording.
3. CC-DOC-01: README's published counts (1423 rows / 70 tests) are stale against the
   artefacts (1436 / 79). README.md is in your scope; the figures need refreshing or
   the claim narrowing.
4. CC-FRESH-01 and the failed scheduled ingest (run 44107633323 — finals/rolling
   refresh failure) are worth a decision in `decisions-needed.html` (CR-V5-2): the
   snapshot-age SLA cannot hold while the ingest keeps failing at the finals gate.
5. F-93-09 suggests a one-line test-hygiene convention: any test that rebuilds the
   published tree should restore it (v2's `_preserved`).
