"""Fix stale verification rows and executive-summary claims (session arena/ac5fab5c-nba2)."""
import pathlib

# ------------------------------------------------------------------ build.py
P = pathlib.Path("nba2/v2/build.py")
s = P.read_text()
n = 0


def rep(old, new):
    global s, n
    assert old in s, f"ANCHOR NOT FOUND:\n{old[:200]}"
    s = s.replace(old, new, 1)
    n += 1


rep('''        {"cells": ["Games in window", f"{len(lines)}", "2026-11-13 → 2026-11-16", srclink(O.SOURCES["schedule"][1])]},
        {"cells": ["Games verified against the official schedule", "31 / 31", "date, tip time, arena, game id", srclink(O.SOURCES["schedule"][1])]},
        {"cells": ["Team records verified against nba.com/standings", "30 / 30", "exact match", srclink(O.SOURCES["standings"][1])]},
        {"cells": ["Injury rows verified against the official PDF", "85 / 85 (+10 not-yet-submitted)", "11/13/26 04:15 PM ET", srclink(O.INJURY_PDF_URL)]},
        {"cells": ["Measured correlations", "6", "computed from the official team, opponent and advanced tables", srclink(O.SOURCES["team_adv"][1])]},
        {"cells": ["Correlations that cannot be measured", "6", "each names the missing dataset on the correlations page", srclink(O.BLOCKED["live_ingest"][2])]},''',
    '''        {"cells": ["Games in window", f"{len(lines)}", f"{O.WINDOW_START} → {O.WINDOW_END} (three days ahead)", srclink(O.SOURCES["schedule"][1])]},
        {"cells": ["Games verified against the official schedule", f"{len(lines)} / {len(lines)}", "date, tip time, arena, game id", srclink(O.SOURCES["schedule"][1])]},
        {"cells": ["Team records verified against nba.com/standings", "30 / 30", "exact match, home and road splits included", srclink(O.SOURCES["standings"][1])]},
        {"cells": ["Team records rebuilt from official final scores", "30 / 30", f"every standings record reconstructed from the {lab['meta']['n_games']} committed finals, 0 mismatches", srclink(O.SOURCES["games"][1])]},
        {"cells": ["Official finals captured", f"{lab['meta']['n_games']} / {lab['meta']['n_games']}", "the full 2026-10-20 → 2026-11-13 window; the count is implied independently by the standings", srclink(O.SOURCES["games"][1])]},
        {"cells": ["Injury rows transcribed from the official PDF", f"{len(O.INJURIES)} player rows (+{len(O.NOT_SUBMITTED)} teams not yet filed)", "11/14/26 04:30 AM ET release", srclink(O.INJURY_PDF_URL)]},
        {"cells": ["Measured correlations", f"{sum(1 for c in lab['correlations'] if c['status'] == 'MEASURED')}", "computed walk-forward from the official finals", srclink(O.SOURCES["games"][1])]},
        {"cells": ["Correlations that cannot be measured", f"{sum(1 for c in lab['correlations'] if c['status'] == 'BLOCKED')}", "all three are player-level; each names the missing dataset", srclink(O.BLOCKED["player_box"][2])]},''')

rep('''        {"cells": ["Picks published", "0 / 31", "every pick fails G6 (no market price exists to bet against)", srclink(O.BLOCKED["odds"][2])]},
        {"cells": ["Strategies that may be ranked", "0 / 7", "all fail G6 (no price) and G7 (no settled results)", srclink(O.BLOCKED["live_ingest"][2])]},''',
    '''        {"cells": ["Leans published / games staked", f"{len(lines)} / 0", "every game gets an originated lean and a trigger price; no stake clears G6 and G7", srclink(O.BLOCKED["odds"][2])]},
        {"cells": ["Gates passing / failing", f"{sum(1 for g in lab['gates'] if g['verdict'] == 'PASS')} / {sum(1 for g in lab['gates'] if g['verdict'] == 'FAIL')}", "evaluated from data, not asserted — see the strategy lab", srclink(O.SOURCES["games"][1])]},
        {"cells": ["Strategies that may be ranked", "0 / 7", "G6 (no price) fails for all; G7 fails on sample size (167 settled of 300), not on absence of data", srclink(O.BLOCKED["live_ingest"][2])]},''')

rep('''        {"cells": ["Published team records that still match today's official standings", f"{st_ex.get('match_live_standings','—')} / 30", "the rest are explained by the nine 11/13 finals — see Live verification", srclink(O.SOURCES["standings"][1])]},''',
    '''        {"cells": ["Published team records that still match today's official standings", f"{st_ex.get('match_live_standings','—')} / 30", "the 2026-11-14 refresh re-read the standings and the pre-final drift is resolved — see Live verification", srclink(O.SOURCES["standings"][1])]},''')

rep('''                  srows, "31 games on the official schedule", idcol=None)''',
    '''                  srows, f"{len(srows)} games on the official schedule", idcol=None)''')

P.write_text(s)
print(f"build.py: {n} patches")

# ------------------------------------------------------------------ content.py
P = pathlib.Path("nba2/v2/content.py")
s = P.read_text()
n = 0

rep('''        "why": "The line itself is derivable from official data; the bet cannot be, because there is no price and no backtest.",''',
    '''        "why": "The line is derivable from official data and the method has been backtested walk-forward; the bet still cannot be staked, because there is no price to beat.",''')

rep('''     "Yes for 11/13–11/16: 31 games, matching the official schedule's per-day counts (9/5/9/8), and identical to the committed snapshot.",''',
    '''     "Yes for 11/14-11/17: 27 games, matching the official schedule's per-day counts (5/9/8/5), and identical to the committed snapshot.",''')

rep('''    ("What was built",
     "A v2 line-origination model over a 31-game, three-day window (2026-11-13 → 2026-11-16), originated only from official NBA inputs, with two independent ratings estimators, a fitted market-agnostic total model, published formulas, and a per-row source link on every table."),
    ("What is verified",
     "31/31 games match the official schedule; all 30 team records match live nba.com/standings exactly; 85 injury rows match the official 11/13 04:15 PM ET PDF row for row; team scoring, opponent scoring and advanced ratings are official nba.com/stats tables."),
    ("What is not possible yet",
     "No price exists, so no pick can be staked. Official per-game finals now exist for 155 of 174 games (captured from nba.com by a parallel session, with 19 games unreachable), so the method CAN be backtested — and it has been. All 31 picks remain withheld because a pick needs a price, not because the method is unknown."),''',
    '''    ("What was built",
     "A v2 line-origination model over a 27-game, three-day window (2026-11-14 → 2026-11-17), originated only from official NBA inputs, with two independent ratings estimators, a fitted market-agnostic total model, published formulas, and a per-row source link on every table. A strategy lab scores seven candidate strategies walk-forward, evaluates twelve validation gates from data, and separates luck from skill with binomial tests."),
    ("What is verified",
     "27/27 games match the official schedule; all 30 team records match live nba.com/standings exactly AND rebuild exactly from the 183 committed official final scores, home and road splits included; 26 injury rows are transcribed from the official 11/14 04:30 AM ET PDF; team scoring, opponent scoring and advanced ratings are official nba.com/stats tables."),
    ("What is not possible yet",
     "No price exists, so nothing can be staked. The results history is now complete — 183 official finals, 2026-10-20 → 2026-11-13, with the count independently confirmed by the standings — so backtests, out-of-sample splits and settlement all run. Every game still gets a lean and a trigger price rather than a stake, because a stake needs a price to beat and 167 settled bets against a 300-bet bar."),''')

rep('''     "Enforced", "12 gates, and the picks page mechanically withholds any pick whose gates do not all pass (currently 31/31 withheld)."),''',
    '''     "Enforced", "12 gates, each evaluated from data with the number that decided it. The picks page publishes a lean and trigger for every game and holds every stake, printing the gates that did it."),''')

rep('''     "Partial", "6 correlations measured (all ≥0.93 where meaningful); 5 blocked with the exact missing dataset named; 1 stated as an assumption."),''',
    '''     "Delivered for team level; blocked for player level", "4 correlations measured from the 183 official finals with CIs and p-values, including the same-game-parlay correlation a two-leg price needs; 3 player-level correlations remain blocked and each names the dataset that would unblock it."),''')

rep('''     "Delivered (withheld)", "31 games, 11/13→11/16, every game covered; picks are computed and then withheld with the failing gate printed."),''',
    '''     "Delivered", "27 games, 11/14→11/17 — the full three-day window. Every game gets an originated line, a lean, and the trigger price at which acting would be rational. No game gets a stake: G6 (no price) and G7 (167 settled of 300) both fail, and the page says so per row."),''')

rep('''     "Blocked", "Statuses are official and complete for 11/13; minutes and production impact need player logs. Every impact cell is blank with a reason."),''',
    '''     "Partially blocked", "Statuses are official for 11/14 (26 player rows + 23 teams that had not yet filed, because the filing deadline for 11/15-11/17 has not passed). Minutes and production impact need player logs, so every impact cell is blank with a reason."),''')

P.write_text(s)
print(f"content.py: {n} patches")
