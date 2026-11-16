# Session audit — arena/3fbd894a (Z-01…Z-09 integration), 2026-11-14

Scope: the 05:15 AM ET refresh wiring, the I-02/I-03/I-04/I-05/I-06 adjudication, F-025,
the crosscheck CC-PUB-05/CC-DOC-01 repairs, and the register updates. Nothing outside the
claimed file scope was edited except `nba2/v2/live.py` (one dispatch line, see F-025 below)
and `tools/crosscheck_site.py` (CC-PUB-05 only) — both disclosed on the coordination board.

## Captures (Z-02/Z-03/Z-04)

- `data/raw/injury_report_2026-11-14_0515AMET.json` — 49 rows (31 for 11/14 with 26
  designations, 18 NOT-YET-SUBMITTED placeholders for 11/15). Verbatim text:
  `raw_injury_2026-11-14_0515AM_chunk0.md`. Parser: `build_captures.py` (re-runnable).
- `data/raw/official_game_times_2026-11-14_0515AMET.json` — 14 time records +
  `game_page_recheck` 27 rows (11/14–11/17), every row citing its own
  `https://www.nba.com/game/{away}-vs-{home}-00226002NN` URL. All 27 MATCH the slate.
- All 36 window tips re-verified against the official games pages (0 mismatches). Full
  per-row transcript: `games_pages_2026-11-14_to_11-17.md`.

## Irregularities — status after this session

- **I-02 (DET@MIA lost-cell overclaim)** — adjudicated: the 11/13 19:30 ET times capture's
  `time_captured=true` for DET@MIA is an overclaim its own sibling transcription disproves
  (`injury_report_2026-11-14_daybefore.json`, `record_counts.games_covered_note` +
  FLAG-INJ-06). Recorded as a `corrections` adjudication (`field: older_captured, to: false`)
  in the 05:15 AM capture and honoured by the merge; the published verdict is now "the time
  cell is unreadable in every extraction — tip re-verified at the official games page". The
  8:00 PM ET tip stands on the games-page recheck. CHI@MIN keeps the earlier release's
  genuine cell.
- **I-03 (AM/PM ambiguity)** — resolved by the explicit printed-tip rule (hour 1–11 → +12,
  12:xx → noon), declared in the capture's `time_convention` and the corroboration blurb.
- **I-04 (as stated by PR #44: "11/15 slate absent")** — factually wrong: 11/15 exists in
  slate/picks/site. The real gap is documented as FLAG-SURF-01: the five 11/17 games are
  absent from `data/{picks,our-lines,prop-lines,parlays}.csv` and `nba2/data/schedule.json`
  stops at 11/15 (legacy session-3 surfaces; not backfilled behind their owners' backs).
- **I-05** — CONFIRMED FIXED: all 31 original tips carry ≥2 official sources; 27/27
  pick-window rechecks MATCH.
- **I-06 (ledger chain)** — superseded by PR #43's ledger work; both seals verify
  (cf7dedc6… 22 preds, c841e8f3… 27 preds, byte-identical through this session).

## F-025 — the S2 spread-sign inversion (fixed)

`nba2/picks.py` now labels a selection with the model's favorite carrying that side's own
line (favorite gives points): "MIA -6.5", "NYK -2.5". Before: the same side with the flipped
sign ("MIA +6.5"). The rule lives in `picks.s2_selection()` and is regression-tested
(`test_s2_selection_matches_its_own_label`, `test_s2_selection_synthetic_conventions`).

**Corrected historical grades.** `audit/2026-11-14/graded_picks.json` (session
arena/ab8743d8) graded the published strings exactly as committed and flagged the defect
itself (F-LIVE-02). Re-graded with the corrected labels, the same four settled S2 rows are
**3-1, not 4-0** (HOU -13.0, final UTA 118 @ HOU 125 = HOU by 7, does not cover): S2 rows
CLE@MIA "MIA -6.5" WIN, UTA@HOU "HOU -13.0" LOSS, GSW@SAS "SAS -8.0" WIN, POR@SAC "POR -6.0"
WIN. S1 (moneyline) 4-0 is unaffected by the sign bug. The regenerated `site/live-verification.html`
publishes the corrected grades (the old dispatch in `nba2/v2/live.py` routed "-N.N" labels to
the ML grader and printed UNGRADABLE; dispatch now keys on the number's shape).

## Checker chain (final run, 2026-11-14)

- `python -m unittest discover -s nba2/tests -t .` — 66 OK (64 + 2 new S2 regressions).
- Seals: both VERIFIED via `nba2.models.ledger.verify`.
- `python -m nba2.pipeline.build_site_data` → 39 tables / 1131 rows; `build_site`; `lint` OK.
- `python -m backtest.engine.build` + `tools/verify_backtest.py` — PASS (155 games, 139 graded).
- `python -m nba2.v2` + `v2.check` (0 structural, 0 semantic) + `v2.live` (0 unexplained stale).
- `tools/check_links_all.py` — 107 files, all internal links OK.
- `tools/verify_site.py` + `scripts/check_site.py` — PASS.
- `tools/crosscheck_site.py` — 94 checks: 81 pass, 5 fail, 8 info. The 5 fails are the
  pre-existing product issues CC-SNAP-13, CC-DER-05, CC-GATE-02, CC-SEAL-04, CC-X-00 (owned
  by earlier sessions, logged on the board). CC-PUB-05 (pre-existing) is now FIXED: the
  corroboration table, its verdict classes and the checker's re-derivation agree.
- Ledgers byte-identical (`git diff data/raw/ledger` empty).

## Registers (Z-08)

- `suggestions/SUGGESTIONS.json`: S-26 marked applied (this fix), S-29…S-36 added (one per
  crosscheck INFO observation, per protocol).
- `requirements/QUESTIONS.json`: Q-30…Q-32 added (instrument-level ATS signal, the earliest
  trustworthy tail, the 05:15 AM release-cadence policy).
