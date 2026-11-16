# S-26 remediation and out-of-sample regrade — session `arena/03a581a0-nba2`

**Date:** 2026-11-14 UTC  
**Scope:** fix the S2 spread-selection generator and its regression test; preserve the historical forecast; correct its interpretation and publish the discrepancy for review.

## Finding

`nba2/model.py` defines `originated_spread` as the away team's spread, with the display label built from the away-team code. The previous inline comment called it the home-team perspective. In `nba2/picks.py`, S2 applied the away-side sign to whichever team it had selected, thereby selecting the underdog side in all nine strong-margin games. Example: game `0022600041` has Portland as a 6.07-point model favourite, the originated label `POR -6.0`, but the stored S2 selection was `POR +6.0`.

The generator now uses `spread_selection(line)` to name the model favourite and assign it `-abs(originated_spread)`. The regression suite in `nba2/tests/test_picks_sign.py` checks away and home favourites, all nine strong-margin rows, the former defective expression, and the immutable historical file's timestamp and row count. Mutation check: reverting the helper's body to the former sign logic causes four of six tests to fail; restored implementation passes all six.

## Historical forecast: do not rewrite

`nba2/data/picks.json` remains byte-identical. It was generated at `2026-11-13T22:30:00Z`, before the relevant games tipped. Regenerating it would replace that forecast with a post-event artifact and invalidate the out-of-sample test. Its S2 labels therefore remain as originally published, with this correction attached rather than silently rewriting history.

A read-only regrade uses the original labels and the official final-score captures already recorded in `audit/2026-11-14/grade_picks.py`. For the four settled S2 signals:

| Game | Published S2 label/result | Model-favourite label/result | Official game |
|---|---|---|---|
| CLE @ MIA | MIA +6.5 — WIN | MIA -6.5 — WIN | [NBA.com game page](https://www.nba.com/game/cle-vs-mia-0022600036) |
| UTA @ HOU | HOU +13.0 — WIN | HOU -13.0 — LOSS | [NBA.com game page](https://www.nba.com/game/uta-vs-hou-0022600039) |
| GSW @ SAS | SAS +8.0 — WIN | SAS -8.0 — WIN | [NBA.com game page](https://www.nba.com/game/gsw-vs-sas-0022600040) |
| POR @ SAC | POR +6.0 — WIN | POR -6.0 — WIN | [NBA.com game page](https://www.nba.com/game/por-vs-sac-0022600041) |

**Result:** as-published S2 = 4/4; on the model's intended favourite side = 3/4. Five additional S2 signals were pending at the time of the regrade. The sample is only four settled signals, below the 30-settlement promotion gate; neither number supports a strategy promotion, reward, or stake. These are results for one strategy/market, not eight independent game outcomes. The four official NBA.com game pages above were fetched in this session on 2026-11-14 and their final scores match the committed official finals capture. The full read-only command is `python3 analysis/session-03a581a0_regrade_s2.py`.

## Other checks and limitations

- `nba2/data/picks.json` has no diff; the historical generated timestamp remains intact.
- `nba2` unit tests: 70 passed (64 baseline plus six new regression tests); backtest tests: 49 passed.
- `nba2.pipeline.lint`: PASS, 1,306 rows / 46 tables after the PR #54 integration rebase.
- Current `tools/crosscheck_site.py`: 94 checks, 85 pass / 1 fail / 8 info. The sole failure is CC-DOC-01: README still says 64 v1 tests while this branch now runs 70 (the six new regression tests). The README is in the active PR #50 owner's scope; the count correction is requested in `COORDINATION.md` rather than competing with that edit.
- The official-game links above identify the NBA games used for final-score checks. The regrade procedure and score inputs are also inspectable in the committed local audit capture; the four NBA.com game pages were fetched in this session, and no outcome is inferred from an unverified source.
- CC-SNAP-13 and CC-X-00 are now resolved by the merged PR #54; they are not claimed as this session's fixes.
- The canonical `site/live-verification.html` still says “every graded pick won.” `nba2/v2/live.py` and `site/**` remain outside this session's scope; correcting that verdict and publishing the corrected S-26 disclosure are requested from the active site integration owner in `COORDINATION.md`. The historical pick file remains unchanged.
