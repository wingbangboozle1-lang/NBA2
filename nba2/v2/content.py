"""Editorial content for the v2 site: strategies, gates, leaderboard rules, suggestions,
open questions, flags. Every row that makes a factual claim carries a source URL;
rows that cannot be sourced say so in a `status` field instead of inventing a reference.
"""

from __future__ import annotations

from . import official as O

S = O.SOURCES

# --------------------------------------------------------------------------- validation gates
# threshold + why it exists + where the basis comes from. "PROPOSED" means no external source
# sets this number: it is this project's policy choice, published so it can be argued with.
GATES = [
    ("G1", "Source class", "Every input field resolves to an official NBA page or the official injury PDF.",
     "PROPOSED — policy", S["standings"][1],
     "A third-party or unreachable source may not silently fill a competitive input."),
    ("G2", "Completeness", "No required input is blank. A blank anywhere fails the strategy for that slate.",
     "PROPOSED — policy", S["team_trad"][1],
     "Blank ≠ zero. The prior build's rule, kept."),
    ("G3", "Sample floor", "≥ 10 official games observed by BOTH teams before a line may be graded above C.",
     "PROPOSED — derived from reliability", S["standings"][1],
     "Below ~10 games the shrink weight λ drops under ~0.75 and the line is mostly league mean."),
    ("G4", "Estimator agreement", "Two independent ratings (net points/game; NetRtg) must imply spreads within 2.0 pts.",
     "COMPUTED this build (observed max 1.0 pts)", S["team_adv"][1],
     "Two estimators that disagree mean the model is unstable, not that there is an edge."),
    ("G5", "Total-estimator agreement", "PF/PA total and per-100×pace total must be within 4.0 pts.",
     "COMPUTED this build (observed max 4.25 pts)", S["team_trad"][1],
     "Large gaps flag pace/defence inconsistencies that would poison a totals bet."),
    ("G6", "Market price present", "A dated, sourced price for the exact line must exist before a pick is staked.",
     "PROPOSED — policy", O.BLOCKED["odds"][2],
     "Without a price there is no edge, no stake size and no ROI. Currently FAILS for every line."),
    ("G7", "Backtest with settlement", "≥ 300 settled bets of the strategy's own signals, settled from official box scores.",
     "PROPOSED — sample-size policy", O.BLOCKED["live_ingest"][2],
     "300 bets is the point at which a 55% hit rate separates from 52.4% at 5% one-sided."),
    ("G8", "Out-of-sample holdout", "Signals fitted on the first 70% of the backtest window must hold on the last 30%.",
     "PROPOSED — policy", O.BLOCKED["live_ingest"][2],
     "Prevents publishing a curve fit."),
    ("G9", "Luck screen", "Every team the strategy relies on must be inside the luck noise band (|z| ≤ 1.96).",
     "COMPUTED this build — 30/30 pass", S["standings"][1],
     "A signal leaning on a lucky record is measuring luck."),
    ("G10", "Correlation honesty", "No parlay priced by multiplying legs unless the leg correlation is measured or bounded.",
     "PROPOSED — policy", S["schedule"][1],
     "Same-game legs are not independent; the error is one-sided and expensive."),
    ("G11", "Freshness", "Inputs must be dated within 24 h of the slate, and the injury report within its filing window.",
     "OFFICIAL (NBA filing deadlines)", S["injury_policy"][1],
     "Teams must file by 5 p.m. local the day before, and 11 a.m.–1 p.m. on game day."),
    ("G12", "No look-ahead", "No input timestamped after the decision time may enter that decision.",
     "PROPOSED — policy", O.BLOCKED["live_ingest"][2],
     "The single most common way a profitable backtest is fake."),
]

# --------------------------------------------------------------------------- strategies
STRATEGIES = [
    {
        "id": "S1", "name": "Consensus-rating side", "type": "single bet",
        "signal": "Bet the side implied by the average of two shrunk ratings when both estimators agree ≤1.0 pt.",
        "gates_that_can_pass_today": "G1,G2,G3,G4,G9",
        "gates_that_fail_today": "G6,G7,G8,G11,G12",
        "status": "PUBLISHABLE AS A PROJECTION ONLY",
        "why": "The line is derivable from official data and the method has been backtested walk-forward; the bet still cannot be staked, because there is no price to beat.",
        "src": S["team_adv"][1],
    },
    {
        "id": "S2", "name": "Total mean-reversion", "type": "single bet",
        "signal": "Compare our total against the market total; act only on a ≥3.0 pt gap.",
        "gates_that_can_pass_today": "G1,G2,G3,G5,G9",
        "gates_that_fail_today": "G6,G7,G8",
        "status": "BLOCKED — no market total",
        "why": "Our total exists (two estimators, ≤4.25 pt gap observed). The half of the comparison that is a price does not.",
        "src": S["team_trad"][1],
    },
    {
        "id": "S3", "name": "Two-leg cross-game parlay", "type": "parlay",
        "signal": "Two independent games, each leg passing S1, both legs at the same price level.",
        "gates_that_can_pass_today": "G1,G2,G3,G4,G10(cross-game part)",
        "gates_that_fail_today": "G6,G7",
        "status": "BLOCKED — legs have no price",
        "why": "Cross-game independence is a stated assumption, not a measurement; and the compounded hold makes it worse than two singles at equal edge.",
        "src": S["schedule"][1],
    },
    {
        "id": "S4", "name": "Same-game spread+total", "type": "parlay",
        "signal": "Home cover and over in the same game, priced with a measured joint distribution.",
        "gates_that_can_pass_today": "G1,G2,G3",
        "gates_that_fail_today": "G6,G7,G10",
        "status": "BLOCKED — correlation unmeasured",
        "why": "The joint probability is not the product. With no per-game data the correlation cannot be estimated, and a ±26% price error was already demonstrated in the prior build.",
        "src": O.BLOCKED["live_ingest"][2],
    },
    {
        "id": "S5", "name": "Player prop (points/rebounds/assists)", "type": "player prop",
        "signal": "Player season rate × expected minutes, compared with a posted line.",
        "gates_that_can_pass_today": "G1(season rates only)",
        "gates_that_fail_today": "G2,G6,G7,G10",
        "status": "BLOCKED — no minutes or game-log data",
        "why": "Season PPG exists officially; a per-game distribution and a minutes floor do not. Without them there is no probability, only an average.",
        "src": S["players"][1],
    },
    {
        "id": "S6", "name": "Prop combo (points+rebounds)", "type": "player prop combo",
        "signal": "Same-player correlation measured, then joint probability computed.",
        "gates_that_can_pass_today": "—",
        "gates_that_fail_today": "G2,G6,G7,G10",
        "status": "BLOCKED — same-player correlation requires box scores",
        "why": "This is the product the brief asks for most directly, and it is the one most dependent on the missing data.",
        "src": O.BLOCKED["player_box"][2],
    },
    {
        "id": "S7", "name": "Injury-availability fade", "type": "single bet",
        "signal": "When a listed starter is Out, re-price with a measured replacement effect.",
        "gates_that_can_pass_today": "G1,G11,G12",
        "gates_that_fail_today": "G2,G7,G9",
        "status": "BLOCKED — no on/off or usage data",
        "why": "Status is official and dated; the size of the effect is not available. The prior build correctly left the impact blank.",
        "src": S["injury_pdf"][1],
    },
]

# --------------------------------------------------------------------------- leaderboard
LEADERBOARD_RULES = [
    ("Scoring metric", "Log-loss on settled bets, not win rate",
     "Win rate rewards luck on small samples; log-loss is a proper scoring rule, so honest probabilities beat lucky ones.",
     "PROPOSED", S["standings"][1]),
    ("Minimum sample to rank", "300 settled bets", "Below that the 95% interval on a 55% hit rate includes 50%.",
     "PROPOSED", O.BLOCKED["live_ingest"][2]),
    ("Trial accounting", "Every submitted strategy counts, including discarded ones",
     "Otherwise a submitter re-rolls variants until one looks good; the family-wise error rate explodes.",
     "PROPOSED", S["standings"][1]),
    ("Closure/verification", "A pick must be published before tip and be sealed with a hash",
     "Prevents back-filling a winning pick after the result is known.",
     "PROPOSED", S["schedule"][1]),
    ("Unit accounting", "Stake in units of bankroll, capped at 1% per bet",
     "Keeps the leaderboard a skill measure rather than a leverage measure.",
     "PROPOSED", O.BLOCKED["odds"][2]),
    ("Reward split", "100 units: 50 to the top log-loss score over a full season, 30 split across the next three, 20 held in escrow for out-of-sample validation",
     "Pays for demonstrated calibration, not a hot streak.",
     "PROPOSED — needs owner sign-off", O.BLOCKED["odds"][2]),
    ("Disqualifiers", "Any pick without a pre-tip timestamp, any settlement not from an official box score, any strategy edited after settlement begins",
     "Removes the three ways a leaderboard is usually gamed.",
     "PROPOSED", O.BLOCKED["live_ingest"][2]),
]

# --------------------------------------------------------------------------- suggestions
# id, area, suggestion, why it improves decisions, effort, blocking dependency, decision state
SUGGESTIONS = [
    ("SG-1", "Data plumbing", "Move ingestion off the agent and onto a scheduled job that pulls the official schedule, standings and injury PDF once per hour, writing a dated snapshot.",
     "Right now every dataset on the site is a hand-made snapshot. Freshness (gate G11) can never pass without automation, so no strategy can ever be ranked.",
     "Medium (one GitHub Action + a parser)", "Sandbox TLS to nba.com is blocked; a GitHub Action runner has normal internet and can fetch it.",
     "RECOMMENDED — highest leverage"),
    ("SG-2", "Data plumbing", "Obtain a per-game result feed (official box score or licensed API) and store one row per game: date, teams, final score, quarter scores.",
     "Unlocks backtests (G7), out-of-sample splits (G8), settlement, ROI, the leaderboard, and every correlation value in the brief.",
     "Medium", "stats.nba.com and cdn.nba.com are unreachable here; a licensed feed or an Action-run scrape is needed.",
     "RECOMMENDED — unblocks the most"),
    ("SG-3", "Data plumbing", "Connect a licensed odds feed with timestamps (opening and closing lines) for spread, total, moneyline and props.",
     "Without a price there is no edge, no stake, no ROI, no luck-adjusted P&L. Every 'pick' on this site is currently withheld for that reason.",
     "Vendor + contract", "No odds source is connected; NBA.com does not expose prices server-side.",
     "RECOMMENDED — required for any betting claim"),
    ("SG-4", "Model", "Keep two independent estimators and publish their disagreement as the primary confidence signal, rather than a single blended rating.",
     "This build shows a 0.999 correlation between the two, and a max 1.0-pt disagreement — which is itself evidence the model is stable. If the two ever diverge, that divergence is the signal.",
     "Low (already implemented)", "none — no dependency",
     "IMPLEMENTED"),
    ("SG-5", "Model", "Pin home-court advantage to the measured home-win rate instead of fitting it freely.",
     "Unconstrained, σ and h trade off almost perfectly (σ 9→13 with h +7.9→0 fits equally well). Pinning h uses a quantity actually measured over 173 games and leaves one free parameter.",
     "Low (implemented)", "Needs a larger home-game sample to shrink the ±0.076 interval.",
     "IMPLEMENTED"),
    ("SG-6", "Model", "Report luck as a z-score per team and refuse to publish a strategy that leans on a team outside the noise band.",
     "This build: 0 of 30 teams are outside |z| ≤ 1.96. So no signal may currently claim a team is 'overperforming its underlying level' — the data does not support it.",
     "Low (implemented)", "none — no dependency", "IMPLEMENTED"),
    ("SG-7", "Model", "Add a market-anchored prior: blend the model line with the closing line, weight by measured out-of-sample log-loss.",
     "A pure model line is usually worse than the market. Blending is the standard way to improve on both — but it needs the price data in SG-3 and the backtest in SG-2.",
     "Medium", "Depends on SG-3 + SG-2", "QUEUED"),
    ("SG-8", "Model", "Model the total as possessions × points-per-possession, not as an average of team scoring averages.",
     "The two total estimators in this build disagree by up to 4.25 pts, mostly on pace outliers. A possession model forces the identity to hold and makes the gap diagnostic.",
     "Medium", "Needs play-by-play or possession-level data (blocked).",
     "QUEUED"),
    ("SG-9", "Parlays", "Never multiply legs. Publish a correlation bound and a worst-case price, or refuse the parlay.",
     "At 0.50/0.50 legs a 0.40 correlation moves the joint from 25.0% to 32.0% (+28%). Two books can differ by more than the edge.",
     "Low (implemented as a rule)", "The bound is currently a sensitivity band, not a measurement — needs SG-2.",
     "IMPLEMENTED (bound) / BLOCKED (measurement)"),
    ("SG-10", "Injuries", "Store every injury PDF with its timestamp and diff consecutive reports to detect status changes.",
     "A status change between the 1 p.m. and 4:15 p.m. reports is the highest-information event in an NBA day. Right now only one report is stored.",
     "Low", "Needs SG-1 (scheduled fetch).", "RECOMMENDED"),
    ("SG-11", "Injuries", "Replace the flat p(play) by status with an empirical table: for each status label, the historical share that actually played.",
     "The current 0.00/0.55 etc. are unratified placeholders. A measured table would be a real edge input and is cheap to build from report history.",
     "Medium", "Needs a season of paired report/box-score data (SG-2).", "QUEUED"),
    ("SG-12", "Injuries", "Model minutes redistribution explicitly: for each team, the top-8 minutes shares and the replacement shares when a player is out.",
     "This is the only way to turn an injury into a line move. Without it, injury analysis stays qualitative.",
     "High", "Needs per-player game logs (blocked).", "QUEUED"),
    ("SG-13", "Game flow", "Compute rest, back-to-back and 3-in-4 from the official schedule (already possible) and add travel distance from a sourced arena-coordinate table.",
     "Schedule density is measurable today and 3-in-4 is a real rotation risk; distance needs a source so it is left out for now.",
     "Low", "Arena coordinates need a citable source.", "PARTIAL — density implemented"),
    ("SG-14", "Site", "Publish a per-row verification badge with the exact URL and retrieval timestamp, and a machine-readable JSON alongside every table.",
     "A reviewer can then re-check any single number without trusting the page. Implemented here: every table row carries `src`, and data/v2/*.json ships with the site.",
     "Low (implemented)", "none — no dependency", "IMPLEMENTED"),
    ("SG-15", "Site", "Make the Suggestions page a decision queue with an explicit state per item and an owner field.",
     "The brief asks for a place to review suggestions and choose a path before anything is implemented. A state machine (proposed → accepted → implemented / rejected) is the minimum for that.",
     "Low (implemented)", "none — states are editable in this file.", "IMPLEMENTED"),
    ("SG-16", "Governance", "Freeze a pre-registration file per strategy before its first bet: signal, thresholds, universe, and the exact settlement rule.",
     "Pre-registration is what separates a tested strategy from a story told afterwards. It also makes the trial-accounting rule enforceable.",
     "Low", "Needs SG-3 to have anything to bet on.", "RECOMMENDED"),
    ("SG-17", "Governance", "Add a tamper-evident ledger: hash each published pick, publish the hash before tip, and verify after settlement.",
     "The prior build already seals 22 predictions this way; extending it to every pick is what makes the leaderboard credible.",
     "Low", "Needs SG-1.", "RECOMMENDED"),
    ("SG-18", "Product", "Split the site into 'projection' (safe to publish now) and 'bet' (gated) surfaces, and never mix them.",
     "Right now the honest answer is that no bet is publishable. Separating the two stops a reader mistaking a projection for a tip.",
     "Low (implemented)", "none — no dependency", "IMPLEMENTED"),
    # --- raised by integration session arena/72f9da58 (2026-11-14) ---
    ("SG-19", "Data plumbing",
     "Re-ingest the injury report at its newest official revision before every pick run, and keep the line-by-line delta between revisions published.",
     "The first published rows (16:15 ET) were superseded three times the same evening — 12 status changes. Lines priced off a stale revision are priced off a superseded designation list.",
     "Low (parser + delta already exist under audit/)", "nightly refresh.yml exists; the remaining gap is the game-day 13:00 ET report",
     "IMPLEMENTED by refresh.yml (nightly); game-day cadence open"),
    ("SG-20", "Product",
     "Make the v1 slate table's verified game-page URLs clickable (<a href> at build time).",
     "Reviewers must copy-paste URLs to open them, which slows the manual click-through that the provenance model depends on.",
     "Very low (one renderer change in nba2/pipeline/build_site.py)", "none — URLs are already verified 36/36",
     "QUEUED"),
    ("SG-21", "Product",
     "Show the injury-report revision time and retrieval time in the Injuries page banner.",
     "A reader could not tell which official revision the rows came from without opening a flag; currency was invisible at a glance.",
     "Low (both fields already in the snapshot)", "none",
     "IMPLEMENTED by refresh.yml (stamps on the Injuries page)"),
    ("SG-22", "Data plumbing",
     "Settle the sealed ledger from official finals as soon as each game day ends, and keep the settlement stamp visible.",
     "Leaderboard, gates and rewards stay blank until finals exist; the 'remove luck' step only becomes data when graded results land.",
     "Low (settle.py runs today and records a pending state)", "official final-score snapshots — fetched nightly by refresh.yml",
     "PARTIAL — settle runs, awaiting first official finals"),
    ("SG-23", "Product",
     "Keep exactly one published site tree; retain the others as history with a banner pointing at the canonical one.",
     "Seven trees shipped from one repo at different times; a reviewer could find different numbers on different trees.",
     "Low — decided: pages.yml publishes site/ (v2) only", "none — v1 trees stay in the repo for audit",
     "IMPLEMENTED — pages.yml publishes site/ only"),
    ("SG-24", "Product",
     "Put data-currency and settlement KPIs on the landing page (e.g. 'injury revision: <stamp>', 'settlement: PENDING/last run').",
     "Games-priced and tier counts are shown, but a reader cannot see whether the inputs are current or when settlement last ran.",
     "Low — both values exist in committed metadata", "SG-22 for the settlement half",
     "QUEUED"),
    ("SG-25", "Data plumbing",
     "Re-read the three official team-stat pages (traditional, opponent, advanced) and re-cut the model inputs.",
     "The scoring averages and advanced ratings this model runs on were read on 2026-11-13, before the nine 2026-11-13 "
     "games. For the 18 clubs that played, the published per-game scoring and NetRtg are one game stale, and the "
     "published lines therefore start from a slightly out-of-date level.",
     "Low — the three pages render for this client; the capture is a transcription plus a diff",
     "none — the pages are reachable through the platform page-reader; a runner can do it unattended (SG-1)",
     "QUEUED — owner decision"),
    ("SG-26", "Data plumbing",
     "Make the nightly refresh rebuild the published v2 tree as well as the v1 tree, and diff both against the commit.",
     "refresh.yml fetches the newest official injury release and the finals, then rebuilds only the v1 tree. The tree a "
     "reader actually sees is the v2 one, so the data the refresh collects never reaches it.",
     "Low — the build commands already exist (python -m nba2.v2, python -m nba2.v2.check)",
     "none", "QUEUED — owner decision"),
    ("SG-27", "Verification",
     "Add a release-to-release injury diff to the build, and fail the build when a status changes.",
     "A report is re-issued several times a day. The 11/14 05:00 a.m ET release moved nothing relative to the 11/13 "
     "19:30 ET release on the 26 shared rows, but the next one might, and a changed status is a different bet.",
     "Low — the diff is computed in the build and published on the Injuries page today",
     "none", "IMPLEMENTED — published as a table on the Injuries page"),
    ("SG-28", "Verification",
     "Move the five unpublished site trees under archive/ with dated notes, and delete nothing.",
     "Six trees still live at the repository root. Only the v2 tree is published, but a maintainer cloning the repo sees "
     "six dashboards and no marker saying which one is live. The published tree also needs a marker saying so.",
     "Low — a move plus one banner per tree", "none", "QUEUED — owner decision"),
]

# --------------------------------------------------------------------------- session
# arena/ac5fab5c-nba2 (2026-11-14). These were written after the results history was completed,
# so several earlier entries that said "blocked, no data" now have a cheaper answer.
SUGGESTIONS += [
    ("SG-31", "Data plumbing", "Make the existing nightly ingest actually fire, and extend it to the v2 results "
     "history in data/raw/history/.",
     "A cron ingest already exists (.github/workflows/refresh.yml) and has never run — its run list is empty, and "
     "the repo's own freshness check CC-FRESH-03 says so in as many words. It also targets the v1 pipeline, not "
     "this history. The cost is visible: the log sat 28 games short for a day and the published standings were a "
     "full day stale with nothing able to detect either. The count is eminently checkable — the standings imply "
     "183 games and the nba.com day-strip calendar gives per-date counts.",
     "Low — the workflow is written and fail-closed; a scheduled workflow also only begins firing after it has "
     "been merged to the default branch once",
     "Confirmation that the cron is enabled on the default branch",
     "RECOMMENDED — cheapest fix with the largest effect on trust"),
    ("SG-32", "Model", "Replace the fixed 300-bet gate bar (G7) with a power calculation per strategy.",
     "300 is a round number chosen so a 55% hit rate separates from 52.4%. But the number that actually matters "
     "depends on the strategy's own correlation between bets: the parlay strategies need a different n than the "
     "side strategies. The lab already computes each strategy's Wilson interval and its distance to the base rate, "
     "so the required n can be derived rather than asserted.",
     "Low — the intervals are already computed in nba2/v2/strategy_lab.py",
     "none — no dependency", "RECOMMENDED"),
    ("SG-33", "Model", "Stop publishing a single blended rating as the headline; publish the disagreement "
     "between the two estimators as the headline and the blend underneath.",
     "The two estimators currently disagree by at most 0.68 pts across 30 teams, so the blend hides almost nothing "
     "today. If they ever diverge, the divergence is the most valuable signal on the site and it is currently "
     "printed as a small diagnostics column.",
     "Low", "none — no dependency", "QUEUED"),
    ("SG-34", "Parlays", "Price every parlay with the measured rho and print the naive product next to it, "
     "instead of withholding the price entirely.",
     "With rho now measured (and its interval published) the honest objection is no longer 'we do not know the "
     "correlation' but 'we do not know it precisely'. Printing both numbers, with the interval between them, is "
     "more useful than printing neither — and it makes the error bar visible instead of implied.",
     "Low — the bivariate-normal pricer is implemented and tested in nba2/v2/strategy_lab.py",
     "None, but it should ship with the interval visible on the same row", "QUEUED"),
    ("SG-35", "Product", "Make the picks page show the trigger price in the reader's preferred format "
     "(decimal, American, or implied probability) rather than decimal only.",
     "The trigger is the one genuinely actionable number the site produces, and it is currently shown in a format "
     "most readers will have to convert. This is a display change with no model consequence.",
     "Low", "none — no dependency", "QUEUED"),
    ("SG-36", "Data plumbing", "Capture per-player game logs (minutes, points, rebounds, assists, and the "
     "opponent) for at least the players who appear on an injury report.",
     "This is the last remaining hard blocker. It unblocks every player-level correlation still listed as BLOCKED, "
     "the whole player-props page, the minutes-and-production half of the injuries page, and strategy S7.",
     "Medium — needs a licensed feed or a scheduled scrape of nba.com/stats/players/boxscores",
     "A runner with normal internet egress", "RECOMMENDED — the last hard blocker"),
]

# --------------------------------------------------------------------------- questions
# Each: id, question, known, unknown, how to find out, blocking?, source
QUESTIONS = [
    ("Q-1", "What is the actual per-game correlation between a team's spread result and the game total?",
     "Nothing measured. Our totals and spreads are computed; their joint behaviour is not.",
     "The covariance of (margin, total) over settled games.",
     "Pull per-game final scores (SG-2) and compute Pearson/Spearman on ≥300 games, per team and league-wide.",
     "Blocks every same-game parlay (S4) and gate G10.",
     S["schedule"][1]),
    ("Q-2", "What is the correlation between a player's points and his rebounds in the same game?",
     "Not measured; no player box scores available.",
     "The joint distribution; likely positive for bigs, near zero or negative for guards.",
     "Box-score feed per player-game (≥200 games per player). Then copula or bivariate-normal fit with a published residual check.",
     "Blocks prop combos (S6).", O.BLOCKED["player_box"][2]),
    ("Q-3", "Do cross-game legs behave like independent events?",
     "Assumed independent. Nothing measured.",
     "Whether shared slate conditions (travel, referee crews, league-wide pace nights) induce any correlation.",
     "Regression of leg A's result on leg B's across ≥1,000 parlays with no shared team.",
     "Blocks S3 pricing being more than an assumption.", S["schedule"][1]),
    ("Q-4", "What share of players listed 'Questionable' actually play?",
     "We hold one report (11/13 04:15 PM) with 24 Questionable rows; the outcome of each is unknown.",
     "The empirical play rate conditional on each status label, and whether it varies by team or by body part.",
     "Join report history to box scores: for each status label, count appearances (SG-11).",
     "Makes the current p(play) column unusable as evidence.", S["injury_pdf"][1]),
    ("Q-5", "How many minutes, and how much production, does a team lose when a listed starter is Out?",
     "Status is official. The size of the effect is not available in this build.",
     "Per-team on/off splits and replacement minutes.",
     "Per-player game logs → on/off per 100, then a shrinkage model like the team ratings here.",
     "Blocks S7 entirely.", O.BLOCKED["player_box"][2]),
    ("Q-6", "Is a 173-game home-win rate of 51.45% different from 50%?",
     "Measured: 89 home wins, 84 home losses, so 51.45% ± 3.8 percentage points (1 s.e.).",
     "Whether the true rate this season differs from 50%; the observed interval easily contains 50%.",
     "More games, or a multi-season prior. Until then h = 0.37 pts is an estimate with wide uncertainty.",
     "Caps the confidence on every home-side line.", S["standings"][1]),
    ("Q-7", "Does the model beat the closing line?",
     "Unanswerable: no price data.",
     "Closing-line value, which is the best single predictor of long-run profit.",
     "Store the closing line for every game (SG-3), then regress model-minus-close on result.",
     "Blocks every 'value' claim and the leaderboard.", O.BLOCKED["odds"][2]),
    ("Q-8", "Which strategy family has the best hit rate at a fixed price after the hold is paid?",
     "Unanswerable without a backtest.",
     "Per-family hit rate, log-loss, and ROI at various thresholds.",
     "Backtest harness on settled results with pre-registered thresholds (SG-16).",
     "Blocks the leaderboard ranking entirely.", O.BLOCKED["live_ingest"][2]),
    ("Q-9", "Are the two ratings estimators really independent, or is one a restatement of the other?",
     "Measured: r = +0.999, max spread disagreement 0.99 pts across 31 lines.",
     "Whether they share an input that makes agreement uninformative. NetRtg is per-possession and PF−PA is per-game, so they are computed from different numerators.",
     "Decompose: regress NetRtg on PF−PA and check whether pace explains the residual. If it does, they are the same number in two units.",
     "If they are not independent, gate G4 is weaker than advertised.", S["team_adv"][1]),
    ("Q-10", "What is the correct price of a line that is inside model noise?",
     "Measured: our own cover probability is 49.3%–50.7% at our own number — i.e. no edge against our own line.",
     "How much of the remaining uncertainty is model error rather than game variance.",
     "Compare model lines with closing lines over ≥500 games; the residual spread is model error.",
     "Without it, conviction (|margin|/σ) is the only confidence measure available.", S["team_adv"][1]),
    ("Q-11", "How do you certify that a data snapshot is what the official page said, later?",
     "Partly answered: this build logs the URL and date per row; the prior build seals a digest of 22 predictions.",
     "Archival storage of the exact page (a hash of the raw bytes), not just the transcription.",
     "Store the raw fetched HTML/PDF bytes as a content-addressed artefact in the pipeline (SG-1 + SG-17).",
     "Needed before any third party trusts a published record.", S["schedule"][1]),
    ("Q-12", "What is the required sample before a strategy can be called skilful?",
     "Policy set at 300 settled bets (G7), chosen so a 55% hit rate separates from 52.4% at 5% one-sided.",
     "The true per-strategy variance, which depends on correlation between bets.",
     "Simulate the strategy's own bet stream once a backtest exists; recompute the required n.",
     "Blocks ranking and rewards.", O.BLOCKED["live_ingest"][2]),
    ("Q-13", "Is the schedule data used here complete for the window?",
     "Yes for 11/14-11/17: 27 games, matching the official schedule's per-day counts (5/9/8/5), and identical to the committed snapshot.",
     "Whether any game is postponed or moved after retrieval.",
     "Re-fetch the schedule before each slate and diff (SG-1).",
     "A moved game would silently invalidate a line.", S["schedule"][1]),
    ("Q-14", "What is the actual reward structure and who approves it?",
     "Proposed: 100 units, 50/30/20 split, log-loss scored, 300-bet minimum.",
     "Owner sign-off; whether rewards are cash, credit, or leaderboard status only.",
     "Owner decision. The proposal is published with its rationale so it can be accepted or rejected item by item.",
     "Blocks running the competition at all.", S["standings"][1]),
    ("Q-15", "Do the scoring averages and advanced ratings this model runs on still describe the teams?",
     "Partly answered: the records can be checked every day, and the league's current table is published beside the "
     "model's inputs. The scoring averages and NetRtg were read on 2026-11-13, before the nine 2026-11-13 games, so "
     "for the 18 clubs that played they are one game stale.",
     "A current read of the three official team-stat pages (traditional, opponent, advanced), and the diff against what "
     "the model used.",
     "Re-fetch nba.com/stats/teams/traditional, /opponent and /advanced, diff GP/PTS/NetRtg/Pace/PIE against the "
     "committed transcription, and publish the delta (suggestion SG-31).",
     "Blocks claiming that the published lines start from current inputs; does not block publishing them.",
     S["team_trad"][1]),
    ("Q-16", "Does an official injury release change a designation between editions?",
     "Answered for the pair this session compared: the 2026-11-14 05:00 a.m ET release and the 2026-11-13 19:30 ET "
     "release share 26 player rows and every one of them has the same status and reason. The delta table is published "
     "on the Injuries page.",
     "Whether the pattern holds for every future pair, and how large the pre-tip churn is in practice.",
     "Diff every new release against the previous one on the keys (date, matchup, player); count the status moves per "
     "release and publish the rate.",
     "Blocks any claim about how stable a designation is; the answer so far is published.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf"),
    ("Q-17", "Why does the third-party ratings snapshot's close/blowout split contradict the games played?",
     "Answered in part: the league-wide sums balance (close 99 = 99, blowout 88 = 88) but the per-team bound "
     "close+blowout <= games played does not hold for 18 of 30 clubs. The cause is the text extraction of the source "
     "table, which has blank/merged cells - not the league's data.",
     "The row-level truth for those 18 clubs.",
     "Re-extract the close and blowout columns from the source table row by row and re-check the per-team bound; until "
     "then the columns stay out of the luck table.",
     "Blocks any per-team luck claim that uses the close/blowout split.",
     "https://www.basketball-reference.com/leagues/NBA_2027_standings.html"),
]

# --------------------------------------------------------------------------- session
# arena/ac5fab5c-nba2 (2026-11-14). Q-1, Q-3, Q-4, Q-5 and Q-11 were answered by completing the
# results history; these are the ones that remain or that the new evidence created.
QUESTIONS += [
    ("Q-20", "Is the measured same-game correlation precise enough to price a two-leg parlay?",
     "Measured at +0.0393 (95% CI -0.1133 to +0.1900, n = 167). It is statistically indistinguishable from zero "
     "AND the interval still spans a range wide enough to move a two-leg price by several percent.",
     "A rho with a much tighter interval, which needs roughly 500+ settled games rather than 167.",
     "Keep appending official finals (SG-31) and recompute; the interval will narrow as 1/sqrt(n).",
     "Decides whether SG-34 (publish the parlay price) is safe to ship.", O.SOURCES["games"][1]),
    ("Q-21", "Is 300 settled bets the right bar for every strategy, or only for single bets?",
     "300 is applied uniformly (G7). But the two parlay strategies have far more variance per bet than the side "
     "strategies, so the same n gives them a much wider interval — the bar is not equally strict across types.",
     "Each strategy's own bet-to-bet correlation, which the lab can now simulate from settled history.",
     "Run a power simulation per strategy on its own settled stream and set n per type (SG-32).",
     "Sets when each strategy becomes rank-eligible on the leaderboard.", O.SOURCES["games"][1]),
    ("Q-22", "How much of S1's 64.7% hit rate survives once the schedule it faced is controlled for?",
     "64.7% over 167 bets, p = 0.0002 against a coin flip, and it holds out of sample (66.7% on the last 30% of "
     "dates). But the sample is one month of one season, and a soft early-season schedule would inflate it.",
     "Strength of schedule per team, computed from the same committed finals.",
     "Add an opponent-adjusted rating (already two estimators deep) and re-run the walk-forward.",
     "Decides whether the signal is real skill or a schedule artefact — the single most important open question "
     "on the site.", O.SOURCES["games"][1]),
    ("Q-23", "Do the two ratings estimators disagree enough for their disagreement to be a usable signal?",
     "They disagree by at most 0.68 pts across 30 teams. That is reassuring for stability and useless for signal: "
     "there is currently no game where the two estimators tell materially different stories.",
     "A season with more heterogeneous teams, or an estimator built on a genuinely different input (e.g. "
     "possession-level efficiency from play-by-play).",
     "Track the max disagreement weekly; promote it to a headline only if it ever exceeds ~2 pts for a game.",
     "Decides whether SG-33 is worth doing.", O.SOURCES["team_adv"][1]),
    ("Q-24", "What fraction of the 11/15-11/17 slate will have an official injury filing before tip?",
     "At capture (11/14 04:30 AM ET) zero teams had filed for 11/15, and no 11/16 or 11/17 rows exist in any "
     "published report, because the filing deadline is 5 p.m. local the day before. This is expected, not a "
     "retrieval failure.",
     "A timestamped capture on the afternoon of 11/14, 11/15 and 11/16.",
     "Re-fetch at 19:00 ET each day and diff (SG-31 covers the mechanism).",
     "Decides how far ahead an injury-driven line can honestly be published.",
     O.SOURCES["injury_policy"][1]),
]

# --------------------------------------------------------------------------- flags
FLAGS = [
    ("F-001", "high", "Data", "No market price exists for any line or pick in this build, so no pick is stakable and no ROI can be computed.",
     "Every line is a projection; the picks page withholds all picks and names the failing gate.",
     O.BLOCKED["odds"][2]),
    ("F-002", "info", "Data", "RESOLVED this session — per-game results now exist for all 183 games played "
    "(2026-10-20 → 2026-11-13); the 19 previously unreachable games were 11-06, 11-11 and 11-13 and were captured "
    "from nba.com/games. Player box scores remain unreachable, so player-level settlement is still impossible.",
     "G8 and G12 now pass. G7 still fails, but on sample size (167 settled bets against a 300 bar), not on absence "
     "of data.", O.BLOCKED["live_ingest"][2]),
    ("F-003", "medium", "Data", "The 2026-11-14 05:30 AM ET official injury report returns AccessDenied, so the "
    "freshest reachable release is 04:30 AM ET. See F-038 for why days 11/15-11/17 have no rows at all.",
     "The site uses the 11/14 04:30 AM ET report and labels every not-yet-filed team explicitly.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_30AM.pdf"),
    ("F-004", "medium", "Data", "The official NBA site's 'Preview' pages could not be used for odds: prices are rendered client-side only.",
     "No workaround was attempted; a licensed feed is required (SG-3).", "https://www.nba.com/games"),
    ("F-005", "medium", "Model", "Home-court advantage and margin volatility are only weakly identified from one season's win totals.",
     "h is pinned to the measured home-win rate; the unconstrained fit is published next to it so the ambiguity is visible.",
     S["standings"][1]),
    ("F-006", "medium", "Model", "The 173-game home-win rate (51.45% ± 3.8 pts) does not statistically exclude 50%.",
     "Home-court advantage is therefore published as a small number with a wide interval, not a confident one.",
     S["standings"][1]),
    ("F-007", "medium", "Model", "Player-level production (minutes, usage, on/off) is unavailable, so no injury impact can be quantified.",
     "Impact columns are blank with a reason; no numeric effect is published.", O.BLOCKED["player_box"][2]),
    ("F-008", "low", "Model", "The two total estimators (per-game averages vs per-100 × pace) disagree by up to 4.25 pts, and the "
    "walk-forward backtest shows the model's margin estimates are compressed to 30% of true dispersion.",
     "Games with a gap over 4.0 pts are graded C automatically, and the gap is printed per row.",
     S["team_trad"][1]),
    ("F-009", "low", "Verification", "Eleven injury rows carry their team from a previous page of the PDF, not from the same row.",
     "Marked 'continuation' in the attribution column. The team labels match the game block they sit in; a human can confirm on the PDF.",
     S["injury_pdf"][1]),
    ("F-010", "low", "Verification", "Team scoring tables are read from a rendered page; a future page redesign would silently change field order.",
     "The transcription is committed as code with named fields, and arithmetic identities (points scored = points allowed; home wins = road losses) are asserted on every build.",
     S["team_trad"][1]),
    ("F-011", "low", "Product", "The repository contains five earlier site trees (root, pages/, docs/, dashboard/, verified/, originated/) with different data.",
     "This build does not edit them; the new tree is self-contained under /site. A consolidation decision is logged on the Suggestions page.",
     S["schedule"][1]),
    ("F-012", "low", "Product", "The prior build's own audit reported 28/30 W-L matches against NBA.com while its metadata said 30/30.",
     "Resolved this session: all 30 team records match live nba.com/standings exactly. The 28/30 note is superseded; see the Verification page.",
     S["standings"][1]),
    ("F-013", "low", "Verification", "The prior build tracked Python bytecode files in git; two audits flagged it.",
     "Out of scope for this session's file scope. Logged for the owner; .gitignore already excludes them going forward.",
     "https://github.com/wingbangboozle1-lang/NBA2"),
    ("F-014", "info", "Model", "A team's line and its cover probability are self-consistent by construction: our cover probability is ~50% at our own number.",
     "This is correct behaviour, not an error — it is why a market price is needed before any edge can exist.",
     S["team_adv"][1]),
    ("F-015", "info", "Model",
     "Walk-forward backtest on 139 official finals: 66.9% straight-up (95% CI 58.7–74.2%), margin MAE 11.91 vs 13.27 for a zero baseline, Brier 0.2184 vs 0.2500, AUROC 0.718.",
     "The first honest skill measurement in the repository. It is accuracy, NOT profit: no price exists, so no ROI is claimed anywhere.",
     "https://www.nba.com/games"),
    ("F-016", "high", "Model",
     "Margin estimates are compressed: predicted margin sd 4.98 pts against an actual 16.43 (ratio 0.30); r(predicted, actual) = +0.390, Spearman on |confidence| vs |win size| = +0.10.",
     "A predicted margin is a RANKING signal, not an expected margin. It must never be read as 'this team wins by 8', and must never size a stake.",
     "https://www.nba.com/games"),
    ("F-017", "info", "Model",
     "Spread↔total correlation is now measured, not assumed: r = +0.018 on 155 final scores, 95% CI [−0.149, +0.184], t = +0.21.",
     "Every same-game parlay price depends on this value and it cannot be distinguished from zero at this sample size. Assuming independence is neither disproven nor confirmed: ~780 games would be needed to detect r = 0.10.",
     "https://www.nba.com/games"),
    ("F-018", "medium", "Model",
     "A win probability is not a cover probability. Our own line already absorbs the model's view, so P(cover) at our own number is ~50% by construction (see F-014).",
     "Any table that presents a cover probability against our own line as an edge has misread the model. Only a third-party price can create an edge.",
     S["team_adv"][1]),
    # --- raised by integration session arena/72f9da58 (2026-11-14 verification round) ---
    ("F-019", "medium", "Verification",
     "Injury-report currency: the first published injury rows (official 16:15 ET / 04_15PM release — the revision this site uses, see F-003) "
     "were superseded three times the same evening — 17:15, 18:15 and 19:15 ET — by 12 status changes, 32 added rows and 5 pending placeholders "
     "resolved. The complete line-by-line delta is tabled on the Verification log page.",
     "Treat every injury-based read off a single revision as dated: the delta table is published with per-row official PDF links, and the "
     "repository's nightly ingest (refresh.yml) archives later releases. Re-check designations against the newest revision before acting.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_15PM.pdf"),
    ("F-020", "low", "Verification",
     "In the 19:15 ET revision the team label for Martin, Caleb is dropped at a page break (his row sits between the Cleveland and Dallas "
     "blocks) and a contradictory 'Cleveland Cavaliers — NOT YET SUBMITTED' placeholder prints in the same document. The 17:15, 18:15 and "
     "19:30 ET releases all print 'Cleveland Cavaliers' explicitly on his row.",
     "Cleveland is attributed only because three official revisions keep printing it; re-check on the next revision and flip the attribution "
     "if the label moves.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_15PM.pdf"),
    ("F-021", "low", "Product",
     "The v1 slate table's 'Official game page' column prints its verified URLs as plain text rather than clickable links (36 rows in that "
     "tree's window), which slows the manual click-through review the brief asks for. No data is affected.",
     "Wrap the cell in an anchor at build time in nba2/pipeline/build_site.py; logged as suggestion SG-20 on the Suggestions page.",
     "https://www.nba.com/schedule"),
    ("F-022", "info", "Data",
     "Settlement, reward allocation and leaderboard scores are PENDING by design: data/settlement.json records settled_at "
     "2026-11-14T00:58Z with finals_snapshot null — no official final-score snapshot covers the sealed games of 11/14–11/17 yet, so every "
     "score, bet count and reward cell is blank.",
     "Correct behaviour: the pipeline refuses to grade unplayed games. The nightly workflow fetches official finals as each game day ends "
     "and re-runs settle; blanks stay until then.",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/raw/ledger/sealed-2026-11-14.json"),
    # ---- session arena/ab8743d8-nba2, live re-verification 2026-11-14 -------------------
    ("F-023", "high", "Verification",
     "The 30 team records published on this site agree with the PRE-11/13-finals state on 30/30 rows "
     "and with today's official standings on only 12/30. The nine 2026-11-13 games became official "
     "after the table was transcribed, and nothing on the site compared a published row against a "
     "fresher capture.",
     "Every stale row is listed with both values on the Live verification page. The fix is a staleness "
     "gate (DG-02 / Q-23), not a silent re-transcription: re-transcribing without a gate reproduces the "
     "same failure on the next slate.",
     S["standings"][1]),
    ("F-024", "high", "Model",
     "The first genuine out-of-sample forecast in the repository (nba2/data/picks.json, committed "
     "2026-11-13 22:36:46Z, 83 minutes before the earliest tip) went 4-0 on the four distinct games it "
     "bet, but recorded 8 wins because S1 and S2 both fired on the same four games. The model named the "
     "winner in 5 of 9 graded games, exactly matching a naive net-rating baseline and below 'always pick "
     "home' (7/9).",
     "Hit rates are published with both counts. No strategy is ranked, promoted or rewarded on n=4. The "
     "4-0 is reported as the false-confidence trap it is.",
     "https://www.nba.com/games"),
    ("F-025", "medium", "Model",
     "S2_SpreadValue selections invert the favourite's sign: nba2/picks.py emits 'POR +6.0' for a game "
     "whose own spread label in the same file reads 'POR -6.0', with POR a 6.07-point favourite. A reader "
     "following the selection takes the wrong side of the model's own number.",
     "Reported, not silently edited (the generator belongs to another session). Assigned as DG-03 / "
     "S-26. The grading on the Live verification page reproduces the committed selection verbatim so the "
     "measurement describes what was published, not what was intended.",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/picks.py"),
    ("F-026", "medium", "Verification",
     "No signal in nba2/data/picks.json carries a price: `american_odds` is absent from all 21 signals. "
     "Win/loss is therefore measurable and profit is not, and any PnL on this site would be an assumed "
     "-110 rather than a measurement.",
     "PnL is null on every row and the reason is printed beside it. Q-28 asks the owner to choose between "
     "a licensed feed, manual entry, or a permanent no-PnL policy.",
     "https://www.nba.com/games"),
    ("F-027", "medium", "Product",
     "Two full dashboards exist in the repository but only one reaches a reader. Probed directly: pages that exist "
     "only in the v1 tree (pages/session-audit.html, pages/executive-summary.html) return HTTP 404 on the live site, "
     "while site/-only artefacts (data/teams.json) return 200 with v2 content. So the site/ artefact built by "
     "pages.yml is the published site, and the root v1 tree is unreachable — yet ci.yml still regenerates, lints and "
     "parity-checks it on every push.",
     "Corrected finding: an earlier draft of this flag claimed both trees publish a dashboard. That was wrong. The "
     "real defect is unreachable maintenance debt, not a live fork — the v1 tree carries stale records (see F-023) "
     "that no reader can see but every build pays for. Recommendation DG-01 stands: retire the v1 tree to archive/.",
     "https://github.com/wingbangboozle1-lang/NBA2"),
    ("F-028", "info", "Verification",
     "The '30/30 identical' W-L cross-check on the dashboard and verification pages was true when it was "
     "made on 2026-11-14 and is no longer true of the same rows (see F-023).",
     "The column is relabelled 'as transcribed 2026-11-14' and the caption now says to read it as a date. "
     "The live state moved to the Live verification page, which is regenerated from dated captures.",
     S["standings"][1]),
    ("F-029", "high", "Verification",
     "The v1 build was not reproducible from a clean checkout. Two published values were state "
     "dependent: build_is_idempotent recorded whether a previous site.json happened to exist (False on "
     "a clone, True on a rebuild of the same inputs), and generated_at_utc reused the previous stamp "
     "only when a previous file existed. A fresh clone therefore could never reproduce the committed "
     "artefact, and every local full-suite run silently rewrote data/site.json.",
     "Fixed: build_is_idempotent now reports the property by construction, and the stamp is derived "
     "from the newest retrieved_at_utc recorded inside the committed snapshots, so it is a function of "
     "the committed bytes rather than of mtime or the clock. Verified by cloning the branch fresh "
     "(as CI does), running the suite, and confirming all four rebuilds are byte-identical.",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/pipeline/build_site_data.py"),
    ("F-030", "high", "Verification",
     "CORRECTION (2026-11-14, session arena/6650be4d-nba2): the 11/13 19:30 ET official injury release was "
     "transcribed with Caleb Martin under the CLEVELAND Cavaliers. The PDF breaks across pages with the Team "
     "column blank on the continuation rows, and Martin's row falls in that gap, immediately before the "
     "'Cleveland Cavaliers | NOT YET SUBMITTED' line - so the team was inferred from the wrong side of the break. "
     "The 11/14 05:00 a.m ET release repeats the team on every row and prints Martin under the DALLAS Mavericks.",
     "The published window rows now come from the 05:00 a.m ET release, so the corrected attribution is what the "
     "site shows, and the release-to-release delta on the Injuries page prints every row that changed.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf"),
    ("F-031", "medium", "Verification",
     "The 2026-11-13 third-party ratings snapshot carries its own internal-consistency labels, and two of them were "
     "wrong. The league-wide close and blowout sums DO balance (close 99 = 99, blowout 88 = 88) although the label "
     "said FAIL, and the per-team bound close+blowout <= games played does NOT hold although the label said PASS: "
     "18 of the 30 clubs show more close and blowout games than they played (ATL 13 in a 12-game record, MEM 12 in 11).",
     "The snapshot's correction block records the original text verbatim; the close/blowout columns are excluded from "
     "the luck table, and the per-team check is now part of the repository's own checker.",
     "https://www.basketball-reference.com/leagues/NBA_2027_standings.html"),
    ("F-032", "low", "Verification",
     "Two official pages disagree on the tip time of one game in the window: the /schedule card for 0022600249 "
     "(HOU @ MIA, 2026-11-16) renders '8:00 PM ET', while the game's own page renders '7:30 PM ET' in both its game "
     "rail and its header line. The other 35 games were re-read in this session and match the committed snapshot exactly.",
     "The published value follows the game's own page. Treat that page as authoritative for its tip time.",
     "https://www.nba.com/game/hou-vs-mia-0022600249"),
    ("F-033", "medium", "Model",
     "The model's team inputs (records, scoring averages, advanced ratings) were read from the official NBA pages on "
     "2026-11-13, before the nine 2026-11-13 games were played, and could not be re-read in this session. They "
     "therefore disagree with the league's current table for 18 of the 30 clubs.",
     "The current official records are published beside them on the Methodology page, and every published page says "
     "which date its numbers carry. Nothing is silently refreshed.",
     S["standings"][1]),
    ("F-034", "info", "Verification",
     "The published pick window now reaches 2026-11-17, which is the build date plus three days: the earlier build "
     "covered 11/13 to 11/16, so it published one already-played game date and omitted the last day of the window. "
     "The nine 2026-11-13 games are kept as day-before context and graded against the official finals.",
     "The window is read from the committed slate snapshot, so it cannot drift from the brief's three-day limit.",
     "https://www.nba.com/schedule"),
]

# --------------------------------------------------------------------------- session
# arena/ac5fab5c-nba2 (2026-11-14).
FLAGS += [
    ("F-036", "info", "Verification", "RESOLVED this session — the committed standings were a pre-finals "
     "snapshot. They agreed with the pre-11/13-finals state on 30 of 30 rows and with live official standings on "
     "only 12 of 30. Re-read from nba.com/standings on 2026-11-14: they now match live official standings on 30 "
     "of 30 rows, home and road splits included, and all 30 records rebuild exactly from the 183 committed "
     "official finals. The staleness measure that caught it is retained and inverted.",
     "Fixed, and the check that found it is now permanent.",
     "https://www.nba.com/standings"),
    ("F-037", "info", "Data", "RESOLVED this session — the official results history was incomplete (155 of 183 "
     "games). The 28 missing finals (2026-11-06, 11-11 and 11-13) were captured from nba.com/games, taking the "
     "window to 183/183. The count is confirmed two independent ways: the standings imply exactly 183 games "
     "played, and all 30 team records now rebuild with zero mismatches.",
     "Fixed. Backtests, out-of-sample splits and settlement run on the full window.",
     "https://www.nba.com/games?date=2026-11-13"),
    ("F-038", "medium", "Data", "No official injury row exists for any 11/16 or 11/17 game in the capture this "
     "site uses, and in that same capture (11/14 04:30 AM ET) no team had filed for 11/15 either. Part of this is "
     "the filing rule working as designed — a team files by 5 p.m. local the day before — but it is NOT only the "
     "calendar: a LATER official release committed to this repository by another session (11/14 05:00 AM ET, "
     "data/raw/injury_report_2026-11-14_0500ET.json) already contains 18 rows for 11/15 that the 04:30 AM capture "
     "lacks. The empty 11/15 cells on this site are therefore partly an artefact of WHEN the snapshot was taken, "
     "not purely of the filing deadline. A 05:30 AM ET fetch attempted in this session returned AccessDenied.",
     "Those cells are blank and labelled with the filing rule and the capture timestamp. No value was inferred or "
     "carried forward, and this page's 04:30 AM capture was not silently swapped for the 05:00 AM one without "
     "re-verifying it against the official PDF.",
     "https://official.nba.com/nba-injury-report-2026-27-season/"),
    ("F-039", "low", "Site", "The GitHub Pages setting on this repository is still build_type 'legacy' (deploy "
     "from the main branch root), while the committed pages.yml workflow publishes the site/ (v2) tree. Whichever "
     "one is live, the other is a fully-built tree sitting in the repository that a reader can reach by URL.",
     "Logged for the owner: this is a one-setting change either way, and it changes what every reader sees.",
     "https://github.com/wingbangboozle1-lang/NBA2/settings/pages"),
    ("F-040", "low", "Model", "Strategy S4 (fade the home team when the model makes them a 3+ point underdog) "
     "went 7 for 7. The binomial p-value is 0.0156, which would pass a naive significance test, but at seven bets "
     "the 95% interval is wide enough to hold almost any true rate.",
     "The luck report records it as SAMPLE TOO SMALL TO CALL and the leaderboard refuses to rank it. It is shown "
     "deliberately, as an example of what luck looks like when it is winning.",
     "https://www.nba.com/games"),
    ("F-041", "info", "Model", "Two matchups appear twice inside the 3-day window: NYK @ TOR (11/15 game "
     "0022600241 and 11/17 game 0022600253) and POR @ MIN (11/16 game 0022600250 and 11/17 game 0022600254).",
     "Verified genuine by reading the official schedule block, not a duplication error in the slate capture. Both "
     "games are priced separately.",
     "https://www.nba.com/schedule?date=2026-11-15"),
    ("F-042", "low", "Site", "A published paragraph on the site cites an open question by the ID 'Q-28', but the "
    "question register only runs to Q-24, so the reference resolves to nothing. The cross-reference was inherited "
    "from the 2026-11-14 refresh on main and is not this session's to edit silently.",
     "Logged, not edited: the sentence is left verbatim and this flag records the defect.",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/v2/content.py"),
]

# --------------------------------------------------------------------------- integration session audit
# Independent re-verification by session arena/72f9da58 on 2026-11-14 (the integration session).
# Each: check, result, method, source URL. Raw artefacts live under audit/ in the repository.
SESSION_AUDIT = [
    ("E-01 checker sweep",
     "PASS — 64/64 nba2 + 49/49 backtest tests; both sealed ledgers VERIFIED (cf7dedc6… over 22 predictions, c841e8f3… over 27); "
     "provenance lint OK over the v1 tree (1124 rows / 39 tables); internal links OK across 88 HTML files; docs, dashboard, "
     "originated and backtest verifiers all PASS",
     "python -m unittest discover (nba2 + backtest); nba2.pipeline.seal_predictions --verify; nba2.pipeline.lint; "
     "tools/check_links_all.py; tools/verify_site.py; scripts/check_site.py; node originated/engine/verify.js; tools/verify_backtest.py",
     "https://github.com/wingbangboozle1-lang/NBA2"),
    ("E-02 slate vs official schedule",
     "36/36 rows of the current v1 slate (11/13 context + 11/14–17 pick window) match nba.com on game ID, date and matchup — "
     "0 mismatches; 30/30 displayed tips match (the six live 11/13 tips were confirmed earlier from the schedule capture plus the "
     "injury report's Game Time column); per-date counts 9/5/9/8/5 match the official day headers",
     "fresh fetch of nba.com/schedule on 2026-11-14 ~01:55 UTC, diffed row-by-row against data/raw/slate_2026-11-14_to_11-17.json "
     "(capture: audit/official_schedule_2026-11-14.json)",
     "https://www.nba.com/schedule"),
    ("E-03 injury-report currency",
     "Latest official revision this session could fetch = 19:15 ET (122 rows, round-trip validated); the v1 tree now publishes the "
     "19:30 ET release; this site uses the 04:15 ET report (F-003). Delta 16:15→19:15: 12 status changes, 32 added rows, "
     "5 pending resolved, 3 text-layer spacing artefacts — full table below",
     "fetch of Injury-Report_2026-11-13_07_15PM.pdf in two chunks; audit/parse_injury_0715.py asserts every parsed cell against the "
     "captured text; audit/injury_delta_0415_to_0715.json",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_15PM.pdf"),
    ("E-04 records vs official standings",
     "30/30 team W-L match the official standings, including Toronto 5-7 and Washington 4-9 that earlier audits could only carry "
     "from a third-party snapshot",
     "nba.com/standings re-read 2026-11-14, diffed against the committed ratings snapshot",
     "https://www.nba.com/standings"),
    ("E-04 game URLs, tips and 11/17 repeats",
     "31/31 slugs of the original window re-read from links nba.com itself prints (schedule previews + game rail); the 11/17 repeat "
     "matchups are genuine — the official game page prints 'Tuesday, November 17th, 2026 7:30 PM ET' for NYK @ TOR (0022600253)",
     "official schedule + game rail on nba.com/game/den-vs-nop-0022600231 + game page nyk-vs-tor-0022600253",
     "https://www.nba.com/game/nyk-vs-tor-0022600253"),
    ("E-04 settlement status",
     "PENDING by design — data/settlement.json records settled_at 2026-11-14T00:58Z with finals_snapshot null; no official final "
     "scores cover the sealed games yet, so metrics stay unmeasured rather than assumed",
     "python -m nba2.pipeline.settle (v1 tree); nightly refresh.yml fetches finals as game days end",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/settlement.json"),
]

# --------------------------------------------------------------------------- executive summary bullets
EXEC_BULLETS = [
    ("What was built",
     "A v2 line-origination model over a 27-game, three-day window (2026-11-14 → 2026-11-17), originated only from official NBA inputs, with two independent ratings estimators, a fitted market-agnostic total model, published formulas, and a per-row source link on every table. A strategy lab scores seven candidate strategies walk-forward, evaluates twelve validation gates from data, and separates luck from skill with binomial tests."),
    ("What is verified",
     "27/27 games match the official schedule; all 30 team records match live nba.com/standings exactly AND rebuild exactly from the 183 committed official final scores, home and road splits included; 26 injury rows are transcribed from the official 11/14 04:30 AM ET PDF; team scoring, opponent scoring and advanced ratings are official nba.com/stats tables."),
    ("What is not possible yet",
     "No price exists, so nothing can be staked. The results history is now complete — 183 official finals, 2026-10-20 → 2026-11-13, with the count independently confirmed by the standings — so backtests, out-of-sample splits and settlement all run. Every game still gets a lean and a trigger price rather than a stake, because a stake needs a price to beat and 167 settled bets against a 300-bet bar."),
    ("The skill finding",
     "A walk-forward test on 167 official finals (2026-10-23 → 2026-11-13, every rating built only from strictly "
     "earlier games) puts this rating method at 67.7% straight-up (95% CI 60.2-74.3%), margin MAE 11.96 against "
     "13.36 for a zero baseline, Brier 0.2170 against 0.2500 for a coin flip. A paired bootstrap over 4,000 draws "
     "puts P(MAE gain > 0) at 0.9998. That is real predictive signal. It is accuracy, NOT profit: there is still "
     "no price to beat, so no ROI exists."),
    ("The compression finding",
     "The same test shows predicted margins are compressed to 32.6% of true dispersion (sd 5.44 vs 16.67) and "
     "correlate with the real margin at only +0.39. The model ranks games; it does not forecast blowouts, and no "
     "stake may ever be sized from a predicted margin."),
    ("The luck finding",
     "Of the seven candidate strategies in the lab, three are distinguishable from chance at 95% and three are "
     "too small to call. The most eye-catching record on the site — S4 going 7 for 7 — is one of the three that "
     "cannot be called, and the leaderboard refuses to rank it. Separating skill from variance is now a gate "
     "(G9), not an opinion."),
    ("The luck finding",
     "Across 30 teams, zero are outside the |z| ≤ 1.96 luck band. No team in this window can honestly be called over- or under-performing its underlying scoring level, so no strategy may lean on that story."),
    ("The correlation finding",
     "Measured on 30 teams: net points vs NetRtg r = +0.999; either vs win% r ≈ +0.93. Measured on 155 finals: spread vs total r = +0.018 (95% CI -0.15 to +0.18), i.e. indistinguishable from zero. Still unmeasurable: every player prop correlation, because no player box scores are reachable."),
    ("The recommended path",
     "Licensed odds remain the only hard blocker for anything involving money. Scheduled ingestion keeps the snapshot fresh; per-game results are now partially available (19 games still missing). With odds plus 300 settled bets the leaderboard becomes computable; until then the honest product is a projection desk that grades its own lines."),
]


# --------------------------------------------------------------------------- repo review
# Verified facts about the repository itself, gathered this session.
REPO_FACTS = [
    ("Files tracked at base commit a09f48e",
     "245 files (excluding .git)", "counted with `find . -path ./.git -prune -o -type f -print | wc -l`",
     "https://github.com/wingbangboozle1-lang/NBA2/tree/main"),
    ("Python unit tests", "64 pass (v1 pipeline) + 59 pass (v2 model) + 49 pass (backtest)",
     "`python3 -m unittest discover -s nba2/tests -t .`; `... -s nba2/v2 -p 'test_*.py'`; `... -s backtest/tests`",
     "https://github.com/wingbangboozle1-lang/NBA2/tree/main/nba2/tests"),
    ("Provenance lint", "1,296 rows across 45 tables, every row sourced",
     "`python3 -m nba2.pipeline.lint`", "https://github.com/wingbangboozle1-lang/NBA2/tree/main/nba2/pipeline"),
    ("Repository cross-checker", "94 checks: 86 pass, 0 fail, 8 informational",
     "`python3 tools/crosscheck_site.py`", "https://github.com/wingbangboozle1-lang/NBA2/blob/main/tools/crosscheck_site.py"),
    ("Sealed prediction ledger", "22 predictions, digest cf7dedc689597cb8… verified",
     "`python3 -m nba2.pipeline.seal_predictions --verify`",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/raw/ledger/sealed-2026-11-13.json"),
    ("Site rebuild determinism", "data/site.json is byte-identical after a rebuild",
     "`python3 -m nba2.pipeline.build_site_data` then `cmp` against the committed file",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/pipeline/build_site_data.py"),
    ("Internal links at base commit", "75 HTML files, 3,233 internal links, all resolve",
     "`python3 tools/check_links_all.py`", "https://github.com/wingbangboozle1-lang/NBA2/blob/main/tools/check_links_all.py"),
    ("Parallel site trees present", "6 root/near-root trees (root *, pages/, docs/, dashboard/, verified/, originated/) — "
     "only this v2 tree is published; the other five are retained for history and are unreachable to a reader",
     "directory listing + live probe (the /pages/ paths answer 404)",
     "https://github.com/wingbangboozle1-lang/NBA2"),
    ("Tracked Python bytecode", "19 .pyc files tracked despite .gitignore",
     "`git ls-files '*.pyc' | wc -l`", "https://github.com/wingbangboozle1-lang/NBA2"),
    ("Internationalisation / accessibility", "No lang-specific copy; tables use <caption> in the prior build; no automated a11y check",
     "grep + inspection of the prior build", "https://github.com/wingbangboozle1-lang/NBA2"),
]


# --------------------------------------------------------------------------- requirements coverage
REQUIREMENTS = [
    ("R-1", "Collect, organise and analyse against a full requirements register",
     "Mapped", "12 requirement rows above and 14 open questions are published with status; each carries the source that advances it."),
    ("R-2", "Originate own NBA lines",
     "Delivered (projection)", "36 lines with spread, total, moneyline fair odds, per game, with the formula and every input sourced."),
    ("R-3", "Research and develop strategies that generate useful signals",
     "Partial", "7 strategies specified with signal, gates and status; none may be ranked until G6/G7 pass."),
    ("R-4", "Leaderboard competition with rewards for top strategies",
     "Designed, not running", "Scoring metric, minimum sample, trial accounting, closure and reward split are published; all need owner sign-off and a data feed."),
    ("R-5", "Single bets, parlays, player prop combos",
     "Blocked", "Single bets are line-complete but price-less; parlays need correlation; props need minutes and box scores."),
    ("R-6", "Every strategy must pass validation gates",
     "Enforced", "12 gates, each evaluated from data with the number that decided it. The picks page publishes a lean and trigger for every game and holds every stake, printing the gates that did it."),
    ("R-7", "Determine correlation values",
     "Delivered for team level; blocked for player level", "4 correlations measured from the 183 official finals with CIs and p-values, including the same-game-parlay correlation a two-leg price needs; 3 player-level correlations remain blocked and each names the dataset that would unblock it."),
    ("R-8", "Remove luck from the equation; build skill-based strategies",
     "Delivered (screening)", "Per-team luck z-scores; 0/30 outside the noise band; a luck gate (G9) that rejects a strategy leaning on luck."),
    ("R-9", "Generate picks for every upcoming slate, max 3 days ahead",
     "Delivered", "27 games, 11/14→11/17 — the full three-day window. Every game gets an originated line, a lean, and the trigger price at which acting would be rational. No game gets a stake: G6 (no price) and G7 (167 settled of 300) both fail, and the page says so per row."),
    ("R-10", "Track how injuries affect rotation minutes and production",
     "Partially blocked", "Statuses are official for 11/14 (26 player rows + 23 teams that had not yet filed, because the filing deadline for 11/15-11/17 has not passed). Minutes and production impact need player logs, so every impact cell is blank with a reason."),
    ("R-11", "Provide game flow analysis",
     "Partial", "Schedule-derived rest, back-to-back and 3-in-4 are computed from official dates; pace/garbage-time/foul-trouble flow needs play-by-play."),
    ("R-12", "Executive summary, suggestions, open questions",
     "Delivered", "One page each, with a decision state on every suggestion and a 'how to find out' on every question."),
    ("R-13", "Every table row has a source link; blanks are flagged, never filled",
     "Enforced in code", "The renderer refuses a row without `src`; blanks carry a `flag` or a `blocked` reason. Verified by a link check over the emitted site."),
    ("R-14", "Coordinate parallel sessions without conflicts",
     "Delivered", "Claim committed and pushed before any edit; the whole session's work is confined to new paths (data/v2, nba2/v2, site/v2) plus one appended COORDINATION.md block."),
]
