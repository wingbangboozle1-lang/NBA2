# Suggestions & Decision Register

How to improve the site and the decision-making it supports.

**This page is a decision queue, not a task list.** Nothing here has been implemented. Each item
states the problem, the realistic paths, what each path costs and buys, and — where a human
judgement is genuinely required — the **decision that must be made before any code is written**.
Items marked *no decision needed* are safe to pick up by any session once a higher-priority item
unblocks them.

---

## Priority 1 — unblocks the core product

### SG-01 · Add a market price feed
- **Problem:** the system originates fair lines but cannot compute an edge, because edge needs a
  price. Every EV figure today is computed against an assumed −110.
- **Path A — odds API (recommended).** Paid key, per-call budget. Fastest, gives closing prices for
  every game, and closing prices are exactly what a backtest needs. *Cost:* money. *Buys:* real
  edges, CLV measurement, a runnable G6.
- **Path B — manual capture.** Record the slate's prices by hand into `data/market/`. *Cost:* your
  time, every day. *Buys:* real edges today, zero setup. Not sustainable past a few weeks.
- **Path C — scrape a sportsbook.** *Cost:* legal and ToS risk, brittle. **Not recommended.**
- **Decision needed:** ✅ **A, B or neither?** And if A, what monthly budget?
- **Blocks:** Q-01. **Unblocks:** G5, G6, the leaderboard's credibility, every EV number.

### SG-02 · Build the historical game log and start grading bets
- **Problem:** no box scores, no graded bets → G6 fails for all ten strategies and no parameter can
  be calibrated.
- **Path A — backfill + daily grading (recommended).** Pull 2–3 prior seasons from
  `stats.nba.com/stats/leaguegamelog` (one request per season), then have the pipeline write every
  signal it emits into a ledger with an empty result column that gets filled after each game.
- **Path B — backfill only.** Enables calibration and G6, but no forward-looking record.
- **Path C — forward logging only.** Simplest, but you wait a full season before G6 can run.
- **Decision needed:** ✅ how many seasons, and who owns the daily grading step?
- **Blocks:** Q-03. **Unblocks:** G6, `injuryK`, `restB2B`, `tzPerHour`, Q-04, Q-05, Q-07.

### SG-03 · Get an official per-player feed
- **Problem:** the entire player-prop module is empty because no official per-player source is
  reachable.
- **Path A — restore `stats.nba.com` access (recommended).** One network change; unlocks the whole
  prop module and the injuries→production model.
- **Path B — official NBA Stats API key.** Same result, may cost money, cleaner terms.
- **Path C — per-team official roster pages.** 30 fetches, gives minutes only, no usage. Partial.
- **Decision needed:** ✅ is a paid NBA data licence in scope?
- **Blocks:** Q-02. **Unblocks:** Props page, S10, rotation-minutes tracking.

---

## Priority 2 — makes the numbers trustworthy

### SG-04 · Widen the schedule collection window to 10 days
- **Problem:** we cannot tell whether a 13 Nov team is on a back-to-back, because the 12 Nov slate
  was never collected. Rest is silently set to zero for nine games.
- **Path A (recommended).** Collect 10 days of schedule instead of 3. Costs one extra fetch, and
  every game in the 3-day window then has proper rest context.
- **Path B.** Keep 3 days and accept the gap, flagged.
- **Decision needed:** none. **Recommend A.** *Blocks:* Q-08.

### SG-05 · Publish a sourced prior for home-court advantage, or commit to the season-derived value
- **Problem:** the derived HCA is **+0.53 points**, far below the multi-season norm, and it comes
  from only 173 split games. It is the largest single source of spread error; two games flip
  favourite across the plausible range.
- **Path A — publish the season-derived value (current behaviour).** Fully data-faithful, honest,
  unstable, and visibly flagged with a sensitivity panel.
- **Path B — blend with a multi-season prior.** More accurate in expectation, but the prior must be
  **sourced**, not recalled from memory, or it violates the project's own rule.
- **Path C — shrink toward the prior as the season progresses.** Best of both, most work.
- **Decision needed:** ✅ **A, B or C?** This is a real judgement call about how much to trust 12
  games of data. *Blocks:* Q-09.

### SG-06 · Re-pull the injury report three times on slate days
- **Problem:** the report is a point-in-time snapshot. Teams commonly re-file at 05:00 PM and again
  in the evening. The 14 Nov rows currently say `NOT YET SUBMITTED` and 15 Nov has nothing.
- **Path A (recommended).** Scheduled pulls at 13:00, 17:00 and 20:00 ET on slate days, keeping each
  edition so the site can show how a team's status changed.
- **Path B.** Pull once, on demand.
- **Decision needed:** none. **Recommend A.** *Blocks:* Q-10.

### SG-07 · Verify the Emirates NBA Cup tiebreaker — one page of reading
- **Problem:** strategy S05 assumes the Cup group tiebreaker is point differential. Unverified, so
  S05 is held at G2 = FAIL.
- **Path A (recommended).** Read and cite [nba.com/nba-cup/2026](https://www.nba.com/nba-cup/2026),
  then flip `rule_verified` to true in `engine/strategies.js`.
- **Decision needed:** none — it is a verification task and it is the cheapest item on this page.
  *Blocks:* Q-06.

---

## Priority 3 — improves the site itself

### SG-08 · Separate "verified" and "model output" visually, everywhere
- The distinction already exists in the data. On the page it is currently a label and a tooltip.
  **Suggestion:** a persistent colour-coded left border (green = official source linked, amber =
  trusted-but-not-official, grey = our computation) and a site-wide toggle that **hides all model
  output**, leaving only verified data. That toggle is the single clearest way to let you audit the
  facts without the model's opinion in the way.
- **Decision needed:** none. *Depends on:* nothing.

### SG-09 · Make every table exportable and every line copyable
- CSV download on every table, and a "copy as text" button on each originated line so a number can
  be pasted straight into a bet slip. Low effort, high daily utility.
- **Decision needed:** none.

### SG-10 · Add a results ledger and a calibration chart
- Once SG-02 lands: a page showing every signal ever emitted versus what happened, plus a
  reliability diagram (predicted probability bucketed against observed frequency). A model that is
  well calibrated is worth more than a model that is merely confident.
- **Decision needed:** none, but it is **blocked by SG-02**.

### SG-11 · Show the movement of a line, not just its value
- The site currently shows one line per game. Once SG-06 is pulling multiple injury editions and
  SG-01 is capturing prices, the interesting view is **how each number moved** and why. Requires
  storing a timestamped series rather than a single snapshot.
- **Decision needed:** ✅ is line-movement history worth the storage?

### SG-12 · Add a stake-sizing panel
- The system currently emits signals and probabilities but says nothing about **how much** to bet.
  A Kelly / fractional-Kelly panel is a small amount of code once real prices exist.
- **Decision needed:** ✅ full Kelly, fractional Kelly (recommended — full Kelly is brutally
  volatile and assumes the probabilities are exactly right), or flat staking?
- **Blocked by:** SG-01.

---

## Priority 4 — hygiene

### SG-13 · Deduplicate the two Pages workflows
- `.github/workflows/pages.yml` and `deploy.yml` both upload the repo root to GitHub Pages on a push
  to `main`. They are redundant and they race each other. **Recommendation:** keep `pages.yml`
  (it is the one using `actions/configure-pages` + `deploy-pages` correctly), delete `deploy.yml`.
- **Decision needed:** ⚠️ must confirm neither workflow is being relied on by another session before
  deleting.

### SG-14 · Do not publish the whole repository to Pages
- The Pages artifact is currently the entire repo, so `archive/`, `engine/`, `research/` and the
  data files are all served publicly. **Recommendation:** publish only a build output directory
  (e.g. `docs/`) so internal workings are not on the public site.
- **Decision needed:** ✅ do you want the engine and raw data publicly readable, or site-only?
- **Note:** deliberately deferred for now — the current setup is simpler and the repo is public
  anyway.

### SG-15 · Record model version and data timestamp on every page
- Every page should carry the data timestamp and a build hash, so a screenshot can always be traced
  back to the exact inputs that produced it. Partly done (footer); **suggestion:** promote it into
  the page header.
- **Decision needed:** none.

---

## Decision summary — the five calls only you can make

| # | Decision | Options | Blocks |
|---|---|---|---|
| 1 | Market price feed | odds API / manual / none | Q-01, all EV numbers, G5, G6 |
| 2 | History backfill + grading | 2–3 seasons / forward-only / none | Q-03, G6, all calibration |
| 3 | Paid NBA player data? | yes / no | Q-02, entire props module |
| 4 | Home-court handling | season-derived / sourced prior / blended | Q-09, spread accuracy |
| 5 | Stake sizing | Kelly / fractional / flat | SG-12 |

Everything else on this page is a straight implementation task once one of the above unblocks it.
