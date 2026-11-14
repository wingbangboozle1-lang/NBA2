"""One-shot patch to nba2/v2/build.py for session arena/ac5fab5c-nba2.

Applied as a script rather than by hand so every change is reviewable as a diff and
re-runnable after a rebase. Each replacement asserts on its anchor, so a rebase that
changes the surrounding prose fails loudly instead of silently half-patching.
"""
import pathlib

P = pathlib.Path("nba2/v2/build.py")
s = P.read_text()
n = 0


def rep(old, new, count=1):
    global s, n
    assert old in s, f"ANCHOR NOT FOUND:\n{old[:200]}"
    s = s.replace(old, new, count)
    n += 1


# --------------------------------------------------------------------------- nav
rep('''    ("backtest.html", "Backtest &amp; skill"),''',
    '''    ("backtest.html", "Backtest &amp; skill"),
    ("strategy-lab.html", "Strategy lab"),''')

# ------------------------------------------------------------------ index lede
rep('''<p class="lede">A 31-game window (Nov 13 → Nov 16) priced from official NBA data only.
Two independent ratings, a fitted home-court term, published formulas, and a source link on every row.
Nothing here is a betting tip: no market price is connected, so every pick is withheld and says which gate stopped it.</p>''',
    '''<p class="lede">A 27-game window (Nov 14 → Nov 17) priced from official NBA data only: two independent
ratings, a fitted home-court term, published formulas, and a source link on every row. Every game gets an originated
line and a lean; no game gets a stake, because no market price is connected to beat.</p>''')

rep('''  <div class="kpi"><b>{_acc}</b><small>walk-forward accuracy (139 finals)</small></div>
  <div class="kpi"><b>0</b><small>picks published (all withheld)</small></div>''',
    '''  <div class="kpi"><b>{_acc}</b><small>walk-forward accuracy ({_nscored} finals)</small></div>
  <div class="kpi"><b>{_nleans}</b><small>leans published / stakes 0</small></div>''')

# the pre-final warning is resolved: replace with the resolved finding
rep('''<div class="note warn"><b>The team records on this site are a pre-final snapshot.</b>
The nine 2026-11-13 games have since been played and are official. Reconstructed against today's
standings, this site's 30 team records agree with the <em>pre-final</em> state on <b>30 of 30</b> rows
and with current official standings on <b>12 of 30</b>. That is not a transcription error — it is a
snapshot that has aged. The <a href="live-verification.html">Live verification page</a> lists every
stale row and re-grades the repository's first real forecast.</div>''',
    '''<div class="note"><b>Staleness: resolved, and the check that caught it is still running.</b>
The standings this build published had been transcribed before the 2026-11-13 finals, so they agreed
with the pre-final state on 30 of 30 rows and with live standings on 12 of 30. On 2026-11-14 the
table was re-read from <a href="https://www.nba.com/standings" target="_blank" rel="noopener">nba.com/standings</a>
and it now matches live official standings on <b>30 of 30</b> rows, home and road splits included.
The proof is stronger than a re-read: all 30 records were rebuilt independently from the 183 official
final scores in <code>data/raw/history/</code> and agree exactly. The measure that found the drift is
kept, inverted, on the <a href="live-verification.html">Live verification page</a>.</div>''')

rep('''  <div class="card"><h4><a href="picks.html">Picks &amp; slate</a></h4><p>Every pick, its gate status, and the exact reason it is withheld.</p></div>''',
    '''  <div class="card"><h4><a href="picks.html">Picks &amp; slate</a></h4><p>Every game: the lean, the price that would justify it, and the gate that holds the stake at zero.</p></div>''')

rep('''  <div class="card"><h4><a href="strategies.html">Strategies &amp; leaderboard</a></h4><p>Seven strategies against twelve gates, plus the competition rules and reward split.</p></div>''',
    '''  <div class="card"><h4><a href="strategy-lab.html">Strategy lab</a></h4><p>Seven strategies scored walk-forward on 167 finals, twelve gates evaluated from data, and the luck separation.</p></div>
  <div class="card"><h4><a href="strategies.html">Strategies &amp; leaderboard</a></h4><p>The competition rules, the reward split, and why the board is currently unfunded.</p></div>''')

rep('''  <div class="card"><h4><a href="injuries.html">Injuries &amp; rotation</a></h4><p>85 official status rows, per-team exposure, and exactly what cannot be quantified.</p></div>''',
    '''  <div class="card"><h4><a href="injuries.html">Injuries &amp; rotation</a></h4><p>{len(O.INJURIES)} official status rows from the 11/14 release, the teams that had not filed, and what cannot be quantified.</p></div>''')

# ------------------------------------------------- executive summary: the blocker
rep('''<div class="note bad"><b>What is missing, and blocks the brief.</b> No market price, no per-game results, no player game
logs. Those three absences are why the prior build could not produce a single settled bet, and they are why this build
withholds all 31 picks rather than publishing confidence it cannot support.</div>''',
    '''<div class="note bad"><b>What is missing, and blocks the brief.</b> No market price and no player game logs.
Per-game results are no longer missing — 183 official finals are committed and every one of the 30 standings records
rebuilds from them exactly — so backtests, out-of-sample splits and settlement all run today. The two remaining
absences are why every stake on this site is 0.00 units rather than a number that looks like a bet.</div>''')

# ---------------------------------------------------------------- picks page
rep('''    body = ""\"<h1>Picks &amp; the upcoming slate</h1>
<p class="lede">Every game in the three-day window is priced. Every pick is then withheld, because two gates cannot pass
without data that does not exist in this environment. This page is deliberately the most conservative on the site.</p>
<div class="note bad"><b>0 of 31 picks are published.</b> Not because the model failed, but because a bet needs a price to beat
(G6) and a settled history to prove skill (G7). Neither exists. Publishing a pick anyway would be the one thing this build refuses to do.</div>
""\"
    rows = []
    for l in lines:
        d = l.as_dict()
        rows.append({"id": d["game_id"], "cells": [
            esc(d["date"]), esc(d["time_et"]), esc(d["matchup"]),
            badge(d["grade"], {"A": "ok", "B": "warn", "C": "bad"}[d["grade"]]),
            f"{d['spread']:+.1f}", f"{d['total']:.1f}", f"{100*d['p_home']:.0f}%",
            esc(d["pick_status"]), srclink(f"https://www.nba.com/game/{d['matchup'].split(' @ ')[0].lower()}-vs-{d['matchup'].split(' @ ')[1].lower()}-{d['game_id']}"),
        ]})
    body += table(["Date", "ET", "Matchup", "Grade", "Our spread", "Our total", "P(home win)", "Status", "Source"],
                  rows, "All 31 games: line, grade and pick status", num_cols=(4, 5, 6), idcol="id")

    body += ""\"<h2>Why each pick is withheld</h2>
""\"
    grows = []
    for g in C.GATES:
        grows.append({"cells": [esc(g[0]), esc(g[1]), esc(g[2]), badge(g[3], "warn" if "PROPOSED" in g[3] else "info"),
                              srclink(g[4]), esc(g[5])]})
    body += table(["Gate", "Name", "Rule", "Basis", "Source", "Why it exists"], grows, "The twelve gates a pick must pass")''',
    '''    body = ""\"<h1>Picks &amp; the upcoming slate</h1>
<p class="lede">Every game in the three-day window (2026-11-14 → 2026-11-17) is priced from our own originated lines,
and every game gets a lean. What no game gets is a stake: a bet needs a price to beat and a settled sample large enough
that the edge is not a coin flip that happened to land, and this repository has neither.</p>
<div class="note"><b>What a "lean" is here.</b> It is the side our own number favours, together with the
<em>trigger</em> — the decimal price at which backing it stops being a losing bet. At our probability p, break-even is
decimal 1/p exactly, so the trigger is arithmetic, not a prediction about what a bookmaker will offer.</div>
<div class="note bad"><b>0 of 27 games are staked.</b> Not because the model failed, but because gate G6 (no market
price) and gate G7 (167 settled bets against a 300-bet bar) both fail. Publishing a stake anyway is the one thing this
build refuses to do.</div>
""\"
    prows = R.t_picks(lines)
    rows = []
    for r in prows:
        rows.append({"id": r["src"] + r["matchup"], "cells": [
            esc(r["date"]), esc(r["time_et"]), esc(r["matchup"]),
            badge(r["grade"], {"A": "ok", "B": "warn", "C": "bad"}[r["grade"]]),
            esc(r["our_spread"]), esc(r["our_total"]), esc(r["p_home"]),
            "<b>" + esc(r["lean"]) + "</b>", esc(r["lean_prob"]),
            esc(r["trigger_decimal"]), "<b>" + esc(r["trigger_american"]) + "</b>",
            esc(r["stake"]), esc(r["gates_passed"]), esc(r["blocked_by"]),
            srclink(f"https://www.nba.com/game/{r['matchup'].split(' @ ')[0].lower()}"
                    f"-vs-{r['matchup'].split(' @ ')[1].lower()}-{r['date']}"),
        ]})
    body += table(["Date", "ET", "Matchup", "Grade", "Our spread", "Our total", "P(home)",
                   "Lean", "P(lean)", "Trigger dec", "Trigger US", "Stake", "Gates", "Blocked by", "Game page"],
                  rows, "All 27 games: originated line, lean, trigger price and gate status",
                  num_cols=(4, 5, 6, 8, 9), idcol=None)

    body += ""\"<h2>Why the stake is withheld</h2>
<p class="lede">Each gate below is evaluated from data, not asserted. The verdict column is what the build
measured; the basis column is the number that decided it.</p>
""\"
    grows = []
    for g in lab["gates"]:
        kind = {"PASS": "ok", "FAIL": "bad"}.get(g["verdict"], "warn")
        grows.append({"cells": [esc(g["id"]), esc(g["name"]), esc(g["requirement"]),
                                badge(g["verdict"], kind), esc(g["measured"]), srclink(g["src"])]})
    body += table(["Gate", "Name", "Requirement", "Verdict", "What was measured", "Source"],
                  grows, "The twelve validation gates, evaluated on this build")''')

rep('''    body += ""\"<h2>The slate itself</h2>
<p class="lede">Read from the official schedule. Eleven of these games are on 11/13 and have already tipped;
they are kept because the only injury report that is fetchable covers them.</p>
""\"''',
    '''    body += ""\"<h2>The slate itself</h2>
<p class="lede">Read from the official schedule on 2026-11-14. This is the full three-day window: 5 games on
11/14, 9 on 11/15, 8 on 11/16 and 5 on 11/17. Two matchups appear twice in the window (NYK @ TOR on 11/15 and
11/17, POR @ MIN on 11/16 and 11/17) — verified genuine against the official schedule block, not a duplication
error.</p>
""\"''')

# ------------------------------------------------------------ injuries page lede
rep('''<p class="lede">{len(O.INJURIES)} player-status rows transcribed from the official 11/13/26 04:15 PM ET report, plus the ten
team-rows the league had not yet received. Every row links to the PDF it came from.</p>''',
    '''<p class="lede">{len(O.INJURIES)} player-status rows transcribed from the official 11/14/26 04:30 AM ET report, plus the
{len(O.NOT_SUBMITTED)} team-rows the league had not yet received at capture time. Every row links to the PDF it came from.</p>''')

rep('''<div class="note warn"><b>Dated input.</b> The 11/14 01:00 PM ET report returned AccessDenied at retrieval time, so this page
cannot show today's final statuses. Nothing was filled in from an unavailable file.</div>''',
    '''<div class="note warn"><b>Dated input, and why days 2 and 3 are blank.</b> The 11/14 05:30 AM ET report returned
AccessDenied at retrieval time, so the freshest reachable release is 04:30 AM ET. More importantly: a team files for a
game by 5 p.m. local <em>the day before</em>, so for the 11/15, 11/16 and 11/17 games the deadline has not yet passed and
no official row exists to read. Those cells are blank by policy, never estimated. Nothing was filled in from an
unavailable or non-existent file.</div>''')

# ------------------------------------------------------------- methodology tail
rep('''<pre>python3 -m nba2.v2             # rebuilds data/v2/*.json and site/ (17 pages)
python3 -m nba2.v2.check       # every row sourced, every blank explained
python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'   # 42 tests</pre>''',
    '''<pre>python3 -m nba2.v2                # rebuilds data/v2/*.json and site/
python3 -m nba2.v2.check          # every row sourced, every blank explained
python3 -m nba2.v2.strategy_lab   # strategies, gates, correlations, luck separation
python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'   # 80 tests</pre>''')

# ------------------------------------------------- the lab must exist for the picks page
rep('''    teams, cal = M.build_teams()
    lines = M.originated_lines(teams, cal)''',
    '''    from . import strategy_lab as SL
    lab = SL.run()
    (DATA).mkdir(parents=True, exist_ok=True)
    (DATA / "strategy_lab.json").write_text(json.dumps(lab, indent=1))

    teams, cal = M.build_teams()
    lines = M.originated_lines(teams, cal)''')

# and the _nscored / _nleans / _acc placeholders on the index
rep('''    _acc = "—"
    if (DATA / "backtest.json").exists():
        _acc = f"{json.loads((DATA / 'backtest.json').read_text())['headline']['straight_up_accuracy']*100:.1f}%"''',
    '''    _acc = "—"
    if (DATA / "backtest.json").exists():
        _acc = f"{json.loads((DATA / 'backtest.json').read_text())['headline']['straight_up_accuracy']*100:.1f}%"
    _nscored = lab["meta"]["n_scored"]
    _nleans = len(R.t_picks(lines))''')

P.write_text(s)
print(f"applied {n} patches to nba2/v2/build.py")
