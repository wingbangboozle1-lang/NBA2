# Suggestions Queue — Review & Decide Before Implementing

**How this works:** every suggestion below is a *proposal only*. Nothing gets built
until it is reviewed here and marked **Approved** (or **Rejected / Needs edit**).
Status values: `proposed` → `approved` / `rejected` / `needs-edit` → `implemented`.
A reviewer (you) picks the path; the implementing session then executes it and
links the result. This is the decision log — history is never rewritten.

| ID | Suggestion | Why it improves decision-making | Impact | Effort | Status | Decision |
|---|---|---|---|---|---|---|
| S-1 | **Connect a market odds feed** (The Odds API or equivalent) for spreads, totals, ML, and props | unlocks edge measurement, CLV scoring, S5 activation, true parlay pricing — everything currently gated on Q-1/Q-2 | very high | low (API key needed from you) | proposed | — |
| S-2 | **Sign off reward sizing** for the leaderboard (weekly badges / monthly pool / season prize per [leaderboard.md](analysis/strategy/leaderboard.md)) | makes the competition real and motivates strategy iteration | high | low (a decision, not a build) | proposed | — |
| S-3 | **Backtest calibration job** (fit HCA, tier impacts, fatigue, defense scalar on historical logs) | replaces 8 uncalibrated parameters (Q-3) with fitted ones; upgrades trust in every line | high | medium (needs historical data source per Q-3) | proposed | — |
| S-4 | **Full rotation production table** (30 teams × top-8 minutes players: PPG/RPG/APG/MPG) | fixes the single worst model blind spot (Q-4: stars like Edwards mis-tiered); makes injury impact honest | very high | medium | proposed | — |
| S-5 | **Decide NBA Cup weighting** (treat Cup group games as equal, upweight, or track separately) | policy clarity for grading; tonight is 9 Cup games | medium | low (decision) | proposed | — |
| S-6 | **Team-specific HCA table** (altitude/arena) | tighter margins on close games (Q-7) | medium | medium | proposed | — |
| S-7 | **Automation: daily slate job** — pull latest official injury report + re-run model + regenerate site each game-day afternoon | removes manual refresh; keeps lines within the 3-day window fresh (Q-8) | high | medium (scheduler + commit bot) | proposed | — |
| S-8 | **Live "line-move tracker"** — compare our number snapshots over time; flag >2-pt moves | turns line stability into a measurable skill signal (gate G3 context) | medium | low once S-1 lands | proposed | — |
| S-9 | **Player-prop market parser + S4 grading loop** | activates the prop-combo strategy fully | high | medium (depends S-1) | proposed | — |
| S-10 | **Bankroll dashboard** (unit sizing, fractional Kelly calculator, drawdown chart) | executes gate G4 mechanically instead of by hand | medium | low | proposed | — |
| S-11 | **Referee assignment tracking** (crew tendencies: totals/pace) | one more verified signal for totals origination | low | medium | proposed | — |
| S-12 | **Public pick-em integration** (NBA Pick'em page shows public pick %) as a contrarian signal for S5 | crowd bias is a documented edge class; pairs with luck ledger | medium | low | proposed | — |

## Decision workflow (please use this exact order)

1. Read the row. Click through the linked evidence if present.
2. Set **Status** to `approved`, `rejected`, or `needs-edit` (with a note).
3. Approved items are implemented in a future session and marked `implemented`
   with a link to the commit/page. Rejected items stay in the table forever —
   the reasoning trail is part of the product.
4. New ideas: append a row (ID continues S-13…). Never edit history.

## Site improvement suggestions (decision-making UX)

These concern the site itself (also awaiting your call):

| ID | Suggestion | Why | Status |
|---|---|---|---|
| U-1 | Add a **"confidence" column** to pick tables (provisional / validated / re-run-needed) | separates data-quality from pick-quality at a glance | proposed |
| U-2 | Add **before/after snapshot diffing** for our lines (S-8 dependency) | shows how our numbers move as injuries land | proposed |
| U-3 | One-click **CSV download** per table | lets you do your own analysis without leaving the repo | proposed |
| U-4 | **Dark mode + mobile pass** | comfort; the tables are wide on phones | proposed |
| U-5 | **Email/JSON webhook digest** each morning with the day's picks | decisions happen off-site too | proposed |

*(The core tables already carry per-row source links, per your verification policy.
U-1 is the one layout change that most improves triage speed.)*
