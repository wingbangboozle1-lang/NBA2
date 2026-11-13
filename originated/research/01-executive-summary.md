# Executive Summary

**Build date:** 2026-11-13 · **Season:** 2026-27 · **Window:** Fri 13 Nov – Sun 15 Nov 2026 (23 games) · **Session:** `session-aaa8b341`

---

## 1. What this system is

NBA2 originates its **own** NBA betting lines rather than consuming a sportsbook's. It reads
official NBA data, turns it into team power ratings, projects a margin and a total for every
game on the slate, and converts those into a fair spread, total and moneyline. On top of that
fair line sits a catalog of **strategies**, each of which is allowed to claim an edge only if it
uses information that is **not** already baked into the line.

Slates are produced up to **3 days ahead**, which is the horizon the official NBA schedule and
the official NBA injury report jointly support.

## 2. The three-day board

| Date | Games | Competition | Injury report state |
|---|---|---|---|
| Fri 2026-11-13 | 9 | Emirates NBA Cup group play | filed (7 pages) |
| Sat 2026-11-14 | 5 | Regular season | `NOT YET SUBMITTED` |
| Sun 2026-11-15 | 9 | Regular season | not yet published |

All 23 games, with tip times, venues, broadcasters and Cup groups, are transcribed from
[nba.com/schedule](https://www.nba.com/schedule).

## 3. What is verified vs. what is modelled

This is the single most important distinction on the site, and it is enforced in the data files.

| Category | Count | Source |
|---|---|---|
| Verified rows (transcribed, official) | 23 games · 91 injury rows · 30 team records | [nba.com](https://www.nba.com/schedule), [official injury report PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf) |
| Verified against a **non-official** source, cross-checked against official | team scoring splits (PPG / OPP PPG / DIFF / splits / streaks) | [ESPN standings](https://www.espn.com/nba/standings), W‑L re-checked 30/30 against nba.com |
| Model output (ours, formula published) | originated spreads, totals, moneylines, correlations, strategy edges | `engine/model.js` |
| **Unverifiable — left blank** | every individual player prop threshold | no official per-player feed reachable |

## 4. Headline findings

1. **The league's home-court advantage this season is tiny.** Derived from the home/away splits
   across all 30 teams: **89‑84 (.5145)**, which implies only **+0.53 points** of home court.
   The multi-season NBA norm is usually quoted far higher. With 173 split games the standard
   error is about ±3.8 percentage points, so this estimate is **unstable**, and it is the single
   largest source of error in the originated spreads. The sensitivity panel re-prices the whole
   board at +0.5 / +1.5 / +2.5 points so the effect is visible rather than hidden.

2. **Two teams are extreme outliers and dominate the board.** Chicago (1‑9, −15.5 PPG) and
   Milwaukee (1‑11, −14.5) are more than 8 points per game worse than the next-worst team.
   Sacramento (1‑10, −12.7) and Utah (1‑11, −11.5) are close behind in the West. Four teams this
   bad is unusual and it makes several originated spreads very large (largest on the board:
   CHI @ MIN, MIN −16).

3. **The official injury report is the richest verified signal on the board, but most of it is
   noise for betting purposes.** Of the 91 player rows, a large share are **G League two-way**
   and **G League assignment** entries — players who were not in the NBA rotation anyway. The
   index that actually carries information is the **rotation-availability index**, which
   excludes them. Counting G League rows as rotation losses (the obvious mistake, and one this
   build initially made) changes the picture materially: for example it made Oklahoma City look
   healthier than the Clippers when the reverse is true once G League rows are stripped out.

4. **Same-game parlays on winner × total are priced essentially fairly by independence.**
   Measured across 23 games with 200,000 simulations each, the largest binary correlation
   (φ) between a moneyline leg and a totals leg is **0.0136**. The independence assumption a
   book uses to price those parlays is off by well under a percentage point. The dangerous
   correlation is the one books already restrict: **moneyline × spread-cover, φ ≈ 0.80**.

5. **Parlays compound the vig, and that is arithmetic, not opinion.** At the 4.77% overround
   implied by a −110/−110 two-way market, a k‑leg parlay built from *fair* legs loses
   **4.55% (1 leg) → 8.90% (2) → 13.05% (3) → 17.00% (4)**. A parlay is only rational if each
   leg clears its own break-even by roughly the overround.

6. **No strategy clears every validation gate.** Eight of ten pass 6–7 of 8 gates. **Gate G6
   (out-of-sample validation) fails for all ten**, because this repository contains no graded
   historical bet log. That is the honest state of the project, and it is the reason the
   leaderboard is labelled **model-expected, not realised**.

## 5. The two blockers

Everything else on this site is usable today. These two are not, and they are the highest-value
things to unblock:

- **Q‑01 — no market price feed.** We originate fair lines, but "edge" only exists relative to a
  price someone will actually give you. Without a market feed the system cannot compute a
  bettable edge, only a fair price. See Open Questions.
- **Q‑02 — no official per-player feed.** `stats.nba.com` and `cdn.nba.com` are unreachable from
  this build environment, so **no player prop threshold is published anywhere on this site.**
  Every prop cell is deliberately blank and flagged, rather than filled with an estimate.

## 6. Irregularities carried over from previous sessions

Two earlier agent sessions published a version of this site and marked every task `done`. Their
data contained factual errors, which are itemised on the **Flagged for Review** page with the
correcting official source. Nothing they built was deleted — it was moved to
`archive/prior-sessions/`.

## 7. What to read next

- **Slates & Picks** — the 23 originated lines and the signals attached to them.
- **Flagged for Review** — every unverified cell and every assumption, in one place.
- **Open Questions** — what we know, what we do not, and how to find out.
- **Suggestions** — ranked improvements, each with a decision that needs making first.
