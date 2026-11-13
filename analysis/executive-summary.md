# Executive Summary — NBA2 Line Origination & Strategy Platform

**As of:** 2026-11-13 (snapshot: official injury report 5:15 p.m. ET)
**Scope delivered this build:** originated lines for the next 4 slates (31 games,
Nov 13–16 — within the 3-day-forward window), pick engine, correlation framework,
validation gates, luck-removal scoring, injury/rotation/game-flow tracking,
leaderboard + reward framework, suggestions queue, and the public dashboard.

## 1. What we built

1. **Our own lines.** A transparent, deterministic model ([scripts/model.py](scripts/model.py))
   originates a spread and total for all 31 upcoming games from schedule-adjusted
   team efficiency + official injury statuses + verified rest. Every input row
   carries an official source link. Methodology: [analysis/strategy/model.md](analysis/strategy/model.md).
2. **Selective picks.** 38 single picks pass conviction gates (|margin| ≥ 4 / total
   lean ≥ 5 pts vs league mean) — e.g. tonight: **NYK −9.5** (Haliburton out),
   **SAS −8.0** (Curry out), **HOU −23.0** (Utah's frontcourt gone), **ATL −12.5**.
   12 games deliberately get **no pick** — selectivity is the skill filter.
3. **Parlay/prop combos with measured correlation.** Same-game pairs are built
   only from documented correlation bands (game total + team total r +0.40…0.60;
   star stacks only in competitive games r +0.35…0.45; blowout star props banned
   at r −0.20…−0.40). Empirical values (3 seasons, 505k pairs) and industry bands
   are kept in separate tiers with links: [correlation.md](analysis/strategy/correlation.md).
4. **Luck out of the leaderboard.** Primary ranking is a Process Rating
   (shrunk ROI + CLV + gates + drawdown), never raw ROI. A live luck ledger shows
   e.g. **PHI at 10-3 carries +4.2 wins of luck** vs its rating-based expectation —
   exactly the kind of record that funds the public's losses.
5. **Validation gates** G1–G5 (data integrity, sample size, price honesty,
   correlation/risk caps, luck separation) that every strategy must pass before
   rewards: [validation-gates.md](analysis/strategy/validation-gates.md).
6. **Injury → rotation → game flow.** Every official status for tonight's 9 games
   plus partial Nov 14 is tabulated with per-game flow reads:
   [analysis/game-flow.md](analysis/game-flow.md).

## 2. Tonight at a glance (Nov 13 — all 9 are NBA Cup group games)

* **Biggest model numbers:** HOU −23.0 vs a Utah team missing Jackson Jr.,
  Markkanen and Nurkic (and Houston itself is without Adams, Capela and the
  suspended Marcus Smart — [official release](https://official.nba.com/rockets-smart-suspended)).
* **Injury headlines:** Curry (GSW), Haliburton (IND), Banchero (ORL), Mobley (CLE),
  Morant (POR), Caleb Wilson (CHI's leading scorer) all OUT
  ([official report](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf)).
* **Sharpest flow read:** SAS −8.0 — Wembanyama (30.3/11.7) versus a Curry-less
  Warriors offense missing 27.8 PPG of creation.
* **No-pick discipline:** CLE@MIA projects within 1.5 pts — passed.

## 3. Risk register (the honest part)

| Risk | Status | Where tracked |
|---|---|---|
| No market lines reachable → no CLV yet | open (Q-1) | [questions.md](analysis/questions.md), flagged page |
| Model parameters uncalibrated (8 values) | open (Q-3) | suggestions S-3 |
| Nov 14 MIN −28.0 line mispriced Edwards' absence (baseline uncollected) | **raised & resolved in-build**: baselines added, re-run at MIN −25.0; residual Q-4 continues | [game-flow.md](analysis/game-flow.md), flagged page F-3 |
| Nov 15–16 lines injury-unadjusted until game-day reports | by-design PENDING | picks CSV `injury_data_status` |
| Ratings source is trusted-secondary, not NBA.com | flagged per-row | data CSVs |

## 4. Decisions needed from you (before anything is implemented)

The [suggestions queue](analysis/suggestions.md) holds 12 proposals + 5 UX items —
**S-1 (odds feed)** and **S-4 (rotation production table)** are the two that unlock
the most capability; **S-2/S-5/S-10** are pure decisions. Nothing is implemented
without your approval there. Unknowns that block decisions are enumerated in the
[questions register](analysis/questions.md) with discovery plans.

## 5. Bottom line

The platform now *originates* numbers rather than reacting to them, publishes
picks only where the model states a repeatable reason, prices parlay risk with
sourced correlation values, and is structurally honest: every table row is
sourced, every unverified value is blank and flagged, and the leaderboard cannot
be gamed by luck. The immediate edge opportunities (tonight's injury-driven
mismatches) are captured in the slate pages; the strategic moat (CLV-scored,
gated, luck-free rankings) activates the moment a market feed is connected.
