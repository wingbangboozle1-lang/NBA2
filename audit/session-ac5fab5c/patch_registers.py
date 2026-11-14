"""Append session arena/ac5fab5c-nba2 entries to the SUGGESTIONS / QUESTIONS / FLAGS registers."""
import pathlib

P = pathlib.Path("nba2/v2/content.py")
s = P.read_text()

# ---------------------------------------------------------------- suggestions
SUGGESTIONS = '''
# --------------------------------------------------------------------------- session
# arena/ac5fab5c-nba2 (2026-11-14). These were written after the results history was completed,
# so several earlier entries that said "blocked, no data" now have a cheaper answer.
SUGGESTIONS += [
    ("SG-25", "Data plumbing", "Schedule a nightly job that appends each night's official finals to "
     "data/raw/history/ and asserts the per-date game count against the nba.com day-strip calendar.",
     "The history is complete today (183/183) precisely because the count is checkable: the standings imply 183 "
     "games and the calendar gives per-date counts. Automating the append with that assertion means the window "
     "can never silently fall behind again, which is the failure the pre-finals standings drift was.",
     "Low — the shape already exists in .github/workflows/refresh.yml",
     "A runner with normal internet egress (nba.com is TLS-blocked from this sandbox)",
     "RECOMMENDED — cheapest fix with the largest effect on trust"),
    ("SG-26", "Model", "Replace the fixed 300-bet gate bar (G7) with a power calculation per strategy.",
     "300 is a round number chosen so a 55% hit rate separates from 52.4%. But the number that actually matters "
     "depends on the strategy's own correlation between bets: the parlay strategies need a different n than the "
     "side strategies. The lab already computes each strategy's Wilson interval and its distance to the base rate, "
     "so the required n can be derived rather than asserted.",
     "Low — the intervals are already computed in nba2/v2/strategy_lab.py",
     "None", "RECOMMENDED"),
    ("SG-27", "Model", "Stop publishing a single blended rating as the headline; publish the disagreement "
     "between the two estimators as the headline and the blend underneath.",
     "The two estimators currently disagree by at most 0.68 pts across 30 teams, so the blend hides almost nothing "
     "today. If they ever diverge, the divergence is the most valuable signal on the site and it is currently "
     "printed as a small diagnostics column.",
     "Low", "None", "QUEUED"),
    ("SG-28", "Parlays", "Price every parlay with the measured rho and print the naive product next to it, "
     "instead of withholding the price entirely.",
     "With rho now measured (and its interval published) the honest objection is no longer 'we do not know the "
     "correlation' but 'we do not know it precisely'. Printing both numbers, with the interval between them, is "
     "more useful than printing neither — and it makes the error bar visible instead of implied.",
     "Low — the bivariate-normal pricer is implemented and tested in nba2/v2/strategy_lab.py",
     "None, but it should ship with the interval visible on the same row", "QUEUED"),
    ("SG-29", "Product", "Make the picks page show the trigger price in the reader's preferred format "
     "(decimal, American, or implied probability) rather than decimal only.",
     "The trigger is the one genuinely actionable number the site produces, and it is currently shown in a format "
     "most readers will have to convert. This is a display change with no model consequence.",
     "Low", "None", "QUEUED"),
    ("SG-30", "Data plumbing", "Capture per-player game logs (minutes, points, rebounds, assists, and the "
     "opponent) for at least the players who appear on an injury report.",
     "This is the last remaining hard blocker. It unblocks every player-level correlation still listed as BLOCKED, "
     "the whole player-props page, the minutes-and-production half of the injuries page, and strategy S7.",
     "Medium — needs a licensed feed or a scheduled scrape of nba.com/stats/players/boxscores",
     "A runner with normal internet egress", "RECOMMENDED — the last hard blocker"),
]
'''

# ---------------------------------------------------------------- questions
QUESTIONS = '''
# --------------------------------------------------------------------------- session
# arena/ac5fab5c-nba2 (2026-11-14). Q-1, Q-3, Q-4, Q-5 and Q-11 were answered by completing the
# results history; these are the ones that remain or that the new evidence created.
QUESTIONS += [
    ("Q-15", "Is the measured same-game correlation precise enough to price a two-leg parlay?",
     "Measured at +0.0393 (95% CI -0.1133 to +0.1900, n = 167). It is statistically indistinguishable from zero "
     "AND the interval still spans a range wide enough to move a two-leg price by several percent.",
     "A rho with a much tighter interval, which needs roughly 500+ settled games rather than 167.",
     "Keep appending official finals (SG-25) and recompute; the interval will narrow as 1/sqrt(n).",
     "Decides whether SG-28 (publish the parlay price) is safe to ship.", O.SOURCES["games"][1]),
    ("Q-16", "Is 300 settled bets the right bar for every strategy, or only for single bets?",
     "300 is applied uniformly (G7). But the two parlay strategies have far more variance per bet than the side "
     "strategies, so the same n gives them a much wider interval — the bar is not equally strict across types.",
     "Each strategy's own bet-to-bet correlation, which the lab can now simulate from settled history.",
     "Run a power simulation per strategy on its own settled stream and set n per type (SG-26).",
     "Sets when each strategy becomes rank-eligible on the leaderboard.", O.SOURCES["games"][1]),
    ("Q-17", "How much of S1's 64.7% hit rate survives once the schedule it faced is controlled for?",
     "64.7% over 167 bets, p = 0.0002 against a coin flip, and it holds out of sample (66.7% on the last 30% of "
     "dates). But the sample is one month of one season, and a soft early-season schedule would inflate it.",
     "Strength of schedule per team, computed from the same committed finals.",
     "Add an opponent-adjusted rating (already two estimators deep) and re-run the walk-forward.",
     "Decides whether the signal is real skill or a schedule artefact — the single most important open question "
     "on the site.", O.SOURCES["games"][1]),
    ("Q-18", "Do the two ratings estimators disagree enough for their disagreement to be a usable signal?",
     "They disagree by at most 0.68 pts across 30 teams. That is reassuring for stability and useless for signal: "
     "there is currently no game where the two estimators tell materially different stories.",
     "A season with more heterogeneous teams, or an estimator built on a genuinely different input (e.g. "
     "possession-level efficiency from play-by-play).",
     "Track the max disagreement weekly; promote it to a headline only if it ever exceeds ~2 pts for a game.",
     "Decides whether SG-27 is worth doing.", O.SOURCES["team_adv"][1]),
    ("Q-19", "What fraction of the 11/15-11/17 slate will have an official injury filing before tip?",
     "At capture (11/14 04:30 AM ET) zero teams had filed for 11/15, and no 11/16 or 11/17 rows exist in any "
     "published report, because the filing deadline is 5 p.m. local the day before. This is expected, not a "
     "retrieval failure.",
     "A timestamped capture on the afternoon of 11/14, 11/15 and 11/16.",
     "Re-fetch at 19:00 ET each day and diff (SG-25 covers the mechanism).",
     "Decides how far ahead an injury-driven line can honestly be published.",
     O.SOURCES["injury_policy"][1]),
]
'''

# ---------------------------------------------------------------- flags
FLAGS = '''
# --------------------------------------------------------------------------- session
# arena/ac5fab5c-nba2 (2026-11-14).
FLAGS += [
    ("F-030", "info", "Verification", "RESOLVED this session — the committed standings were a pre-finals "
     "snapshot. They agreed with the pre-11/13-finals state on 30 of 30 rows and with live official standings on "
     "only 12 of 30. Re-read from nba.com/standings on 2026-11-14: they now match live official standings on 30 "
     "of 30 rows, home and road splits included, and all 30 records rebuild exactly from the 183 committed "
     "official finals. The staleness measure that caught it is retained and inverted.",
     "Fixed, and the check that found it is now permanent.",
     "https://www.nba.com/standings"),
    ("F-031", "info", "Data", "RESOLVED this session — the official results history was incomplete (155 of 183 "
     "games). The 28 missing finals (2026-11-06, 11-11 and 11-13) were captured from nba.com/games, taking the "
     "window to 183/183. The count is confirmed two independent ways: the standings imply exactly 183 games "
     "played, and all 30 team records now rebuild with zero mismatches.",
     "Fixed. Backtests, out-of-sample splits and settlement run on the full window.",
     "https://www.nba.com/games?date=2026-11-13"),
    ("F-032", "medium", "Data", "No official injury row exists for any 11/16 or 11/17 game, and at capture time "
     "(11/14 04:30 AM ET) no team had filed for 11/15 either. This is the filing rule working as designed — a team "
     "files by 5 p.m. local the day before — so it is a property of the calendar, not a retrieval failure. The "
     "05:30 AM ET 11/14 report returned AccessDenied, so 04:30 AM is the freshest reachable release.",
     "Those cells are blank and labelled with the filing rule. No value was inferred or carried forward.",
     "https://official.nba.com/nba-injury-report-2026-27-season/"),
    ("F-033", "low", "Site", "The GitHub Pages setting on this repository is still build_type 'legacy' (deploy "
     "from the main branch root), while the committed pages.yml workflow publishes the site/ (v2) tree. Whichever "
     "one is live, the other is a fully-built tree sitting in the repository that a reader can reach by URL.",
     "Logged for the owner: this is a one-setting change either way, and it changes what every reader sees.",
     "https://github.com/wingbangboozle1-lang/NBA2/settings/pages"),
    ("F-034", "low", "Model", "Strategy S4 (fade the home team when the model makes them a 3+ point underdog) "
     "went 7 for 7. The binomial p-value is 0.0156, which would pass a naive significance test, but at seven bets "
     "the 95% interval is wide enough to hold almost any true rate.",
     "The luck report records it as SAMPLE TOO SMALL TO CALL and the leaderboard refuses to rank it. It is shown "
     "deliberately, as an example of what luck looks like when it is winning.",
     "https://www.nba.com/games"),
    ("F-035", "info", "Model", "Two matchups appear twice inside the 3-day window: NYK @ TOR (11/15 game "
     "0022600241 and 11/17 game 0022600253) and POR @ MIN (11/16 game 0022600250 and 11/17 game 0022600254).",
     "Verified genuine by reading the official schedule block, not a duplication error in the slate capture. Both "
     "games are priced separately.",
     "https://www.nba.com/schedule?date=2026-11-15"),
]
'''

# insert each block right after its list definition closes
for name, block in (("SUGGESTIONS", SUGGESTIONS), ("QUESTIONS", QUESTIONS), ("FLAGS", FLAGS)):
    marker = f"\n# --------------------------------------------------------------------------- leaderboard" if name == "SUGGESTIONS" else None
    # find the end of the list: the line following the closing "]" of that list
    import re
    m = re.search(rf"\n{name} = \[.*?\n\]\n", s, re.S)
    assert m, f"could not locate {name} list"
    s = s[:m.end()] + block + s[m.end():]

# ---------------------------------------------------------------- stale flags
old = '''    ("F-002", "high", "Data", "Per-game results now exist for 155 of 174 games (2026-10-20 → 11-12), captured from nba.com by a "
    "parallel session; 19 games (11-06, 11-11) have no reachable score. Player box scores remain "
    "unreachable, so player-level settlement is still impossible.",
     "Gates G7, G8, G12 and the whole leaderboard are blocked.", O.BLOCKED["live_ingest"][2]),'''
new = '''    ("F-002", "info", "Data", "RESOLVED this session — per-game results now exist for all 183 games played "
    "(2026-10-20 → 2026-11-13); the 19 previously unreachable games were 11-06, 11-11 and 11-13 and were captured "
    "from nba.com/games. Player box scores remain unreachable, so player-level settlement is still impossible.",
     "G8 and G12 now pass. G7 still fails, but on sample size (167 settled bets against a 300 bar), not on absence "
     "of data.", O.BLOCKED["live_ingest"][2]),'''
assert old in s; s = s.replace(old, new, 1)

old = '''    ("F-003", "medium", "Data", "The 2026-11-14 01:00 PM ET official injury report returns AccessDenied, so today's game statuses could not be re-filed.",
     "The site uses the 11/13 04:15 PM ET report, which is dated one day before the 11/14 slate, and says so.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_00PM.pdf"),'''
new = '''    ("F-003", "medium", "Data", "The 2026-11-14 05:30 AM ET official injury report returns AccessDenied, so the "
    "freshest reachable release is 04:30 AM ET. See F-032 for why days 11/15-11/17 have no rows at all.",
     "The site uses the 11/14 04:30 AM ET report and labels every not-yet-filed team explicitly.",
     "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_30AM.pdf"),'''
assert old in s; s = s.replace(old, new, 1)

P.write_text(s)
print("content.py registers updated")
