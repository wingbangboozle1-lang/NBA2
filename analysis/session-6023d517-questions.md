# Open questions that must be answered before any decision is made from this site

Each row is a question a decision-maker would actually ask, what we **have**, what we **do
not have**, and how to get it. A row with no "have" is listed first: those are the ones that
block everything downstream.

## Blocking — no decision of consequence is possible without these

| # | Question | What we have | What we do not have | How to get it | Cost / risk |
|---|---|---|---|---|---|
| Q1 | *Is our number better than the price?* | Our own probability for every game | **Any market price at all** | A closing-line feed (sportsbook API or a licensed odds vendor). Nothing in the repo can substitute for it. | Money, or a licensing agreement; until then every edge is uncomputable and the stake stays 0.00 |
| Q2 | *Does the model add information the record does not already carry?* | A paired test on 29 disagreements: 16 vs 13, p = 0.711 | A sample large enough to separate them | ~100+ disagreements, i.e. ~2 more months at this schedule density | Time only. The gate is written (G-V7-4); it will fire on its own |
| Q3 | *Is the transcription of the league's pages correct?* | Three arithmetic identities (NetRtg, point differential, wins-vs-finals) that all 30 clubs satisfy | An automated re-read in CI | The runner cannot reach `stats.nba.com` (measured); the pages are reachable by page fetch only | Needs an egress path from CI, or a daily manual capture. Flagged F-V7-CLOCK |
| Q4 | *Who is actually available tonight?* | The injury-report index format and 21 archived releases | **The 2026-11-19 report** | Read `official.nba.com/nba-injury-report-2026-27-season/` each day and archive the PDF with its stamp | Automatable; currently manual |

## Important — changes what a reader should believe

| # | Question | Have | Do not have | How to get it |
|---|---|---|---|---|
| Q5 | *Which clock is "current"?* | Measured: `/stats/teams/*` runs through 11/17, `/standings` through 11/18 | A single official as-of stamp | The league prints no "as of" on the stats pages. We publish the gap instead of guessing a blend |
| Q6 | *Are rest and 3-in-4 computed from the full schedule?* | Yes — from the 210 committed official finals | Games before 2026-10-20 in the earlier history files | Extend the committed finals window backward |
| Q7 | *What does travel cost a club?* | Arena coordinates exist (`data/v2/arenas.json`), **third-party** (Wikipedia/Wikidata), flagged | Official coordinates — the league publishes none | No official route exists. Keep the flag, or drop the column |
| Q8 | *Does a same-game parlay really cost less than the naive product?* | ρ = −0.044 [−0.178, +0.092] over 210 finals | A larger sample and a per-market ρ (spread×total is not the only pair) | Recompute per market pair as the finals window grows |
| Q9 | *Is "luck" real or is it a mis-specified Pythagorean exponent?* | z at exponent 13.91, and 0 clubs outside ±2 | Sensitivity at 13.5 and 16.5 on this snapshot | Cheap: recompute the same table at three exponents and publish the band |
| Q10 | *How do injuries move minutes?* | A per-team top-8 share model exists in v3/v4 (`rotation-replacement`) | An official minutes source that is not a gamebook PDF; those exist for 31 games only | Keep transcribing gamebooks, or find a reachable official per-player endpoint |

## Not answerable from this repository, and it should say so

| # | Question | Why not |
|---|---|---|
| Q11 | *What will the line be at tip?* | No odds feed. Also unknowable in principle: the closing line is a market outcome, not a fact about the teams |
| Q12 | *Is this legal where the reader lives?* | Not a data question. The site publishes no stake and no advice; a reader acting on any of it acts alone |
| Q13 | *Would a different model do better?* | Possibly. None has been tested here, and testing one without a price feed would only re-measure log-loss, which is not the payout question |

## The one-line version

**We can price a game. We cannot price a bet.** Q1 is the whole difference, and everything
else on this list is downstream of it or of sample size.
