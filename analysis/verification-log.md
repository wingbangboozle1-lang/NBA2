# Verification Log — line-by-line pass

Performed by session `arena-10957a28` on 2026-11-13 (integration role).
Policy: never mark verified without checking against a source; link the source;
leave blanks and flag otherwise.

## Automated cross-checks (scripts/check_site.py + inline consistency script)

| Check | Scope | Result |
|---|---|---|
| Internal site links resolve | 12 pages, all `href` targets in dashboard/ | PASS |
| Every data-table row carries a source link (or is styled blank+flagged) | 524 rows | PASS |
| Nav + footer present on every page | 12 pages | PASS |
| Standings records == ratings records for all 30 teams | 30 rows | PASS |
| All 31 game rows link nba.com game pages | data/games.csv | PASS |
| Every picks/parlays/lines/props/luck row carries an http source | 5 files | PASS |
| Every injury row cites the official 5:15 p.m. PDF | 100+ rows | PASS |
| Every correlation row cites its study/guide | 21 rows | PASS |

## Hand re-derivations (spot checks of model math)

| Game | Hand calculation | Model output | Verdict |
|---|---|---|---|
| NYK @ IND (post-baseline fix) | (−5.54 − 3.27) + 2.0 − 4.12 injury = −10.89 → NYK −11.0 | NYK −11.0 | ✓ |
| UTA @ HOU | (13.22 −(−7.85)) + 2.0 − 2.4 + 2.4 = +23.07 → HOU −23.0 | HOU −23.0 | ✓ |

## Source-by-source verification highlights

1. **Slate (31 games):** each game ID/time/teams read off the official day page
   ([nba.com/games](https://www.nba.com/games?date=2026-11-13) etc.); records shown
   on those pages cross-checked against the Basketball-Reference ratings table —
   all 30 teams agree.
2. **Injuries:** transcribed from the official PDF; statuses re-read row by row.
   The Marcus Smart "Out — League Suspension" row was independently confirmed by the
   [official release](https://official.nba.com/rockets-smart-suspended).
3. **Player baselines:** NBA.com season-leader rows (28 teams) plus BRef per-game
   ranks 1–25 and the BRef Haliburton page (87 pts / 38 ast / 4 games = 21.8/9.5/4.5
   — arithmetic checked). Cross-checks: NBA.com and BRef agree exactly on Wemby
   30.3/11.7/2.8, SGA 29.7/4.3/4.5, Giannis 27.7/12.6/5.2, KAT 20.9/13.5/3.5 etc.
4. **Correlation values:** each of the 21 rows clicked to its source; the empirical
   study's numbers (teammate r −0.001…+0.074 by margin band; same-team bigs
   rebounds −0.012) were transcribed from the published table.
5. **Rest/B2B flags:** re-derived from the schedule by hand for Nov 13 (no B2B —
   Nov 12 participants are all off today), Nov 14 (5 B2B teams), Nov 15 (DAL 3-in-4
   road), Nov 16 (PHI/HOU/WAS/PHX B2B) — model's flags agree.

## Irregularities found and handled (also on the site's Flagged page)

* **Found:** first model run under-charged 5 key absences (Haliburton, Banchero,
  Edwards, Morant, Mobley) because baselines were missing → lines NYK −9.5,
  ORL −7.5, MIN −28.0 were wrong. **Handled:** verified baselines pulled and
  published with sources; model re-run to NYK −11.0 / ORL −4.0 / MIN −25.0; the
  episode is logged as F-3 (resolved) and shortened Q-4.
* **Standing flags:** F-1 (ratings are trusted-secondary), F-2 (CHA baseline still
  blank), F-4 (Nov 15–16 reports pending), F-5 (correlation priors), F-6 (Nov 12
  scores are CBS/AP), F-7 (uncalibrated parameters), F-8 (no market lines),
  F-9 (PHI luck outlier). All published with links; none block the merge per policy.

## Manual-review links (spot-check any of these)

* Official slate: https://www.nba.com/games?date=2026-11-13
* Official injury PDF: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf
* Smart suspension: https://official.nba.com/rockets-smart-suspended
* Ratings: https://www.basketball-reference.com/leagues/NBA_2027_ratings.html
* Per-game baselines: https://www.basketball-reference.com/leagues/NBA_2027_per_game.html
* Correlation study: https://kindoflost.com/2026/09/nba-dfs-correlation-measured/

**Conclusion:** all automated checks PASS; hand re-derivations agree with the
model; every published row is source-linked or deliberately blank+flagged. The
site is ready for the integration merge.
