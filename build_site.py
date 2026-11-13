"""
build_site.py — renders the static GitHub Pages site from the verified data.

Server-side table rendering means every table is present in the HTML (no JS fetch
dependency), every row carries a source link, and model outputs are labeled.

Run:  python3 build_site.py
"""

import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "nba2", "data")
# GitHub Pages for this repo is configured to deploy from the `main` branch root
# (branch-based, path "/"). So the static site is written directly to the repo
# root, with shared assets under <root>/assets/.
SITE = HERE
ASSETS = os.path.join(SITE, "assets")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def esc(s):
    return html.escape("" if s is None else str(s))


NAV = [
    ("index.html", "Dashboard"),
    ("picks.html", "Picks & Lines"),
    ("strategies.html", "Strategies"),
    ("injuries.html", "Injuries & Flow"),
    ("correlations.html", "Correlations"),
    ("executive-summary.html", "Executive Summary"),
    ("suggestions.html", "Suggestions"),
    ("questions.html", "Open Questions"),
    ("flagged.html", "Flagged for Review"),
]


def nav(active):
    items = "".join(
        f'<a href="{href}" class="{"active" if href == active else ""}">{label}</a>'
        for href, label in NAV
    )
    return f'<nav><div class="wrap"><div class="brand">NBA<span>2</span></div>{items}</div></nav>'


def table(headers, rows):
    """Render a table. rows: list of list-of-cells; a cell may be a str or HTML."""
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = ""
    for row in rows:
        cells = "".join(f"<td>{c}</td>" for c in row)
        body += f"<tr>{cells}</tr>"
    return f'<div class="tbl-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def src_link(url, label="source"):
    if not url:
        return '<span class="blank">—</span>'
    return f'<a class="src" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)} ↗</a>'


def model_pill(text="Model"):
    return f'<span class="pill model">{esc(text)}</span>'


def status_pill(ok, ok_text="Pass", bad_text="Fail"):
    cls = "ok" if ok else "bad"
    return f'<span class="pill {cls}">{esc(ok_text if ok else bad_text)}</span>'


def page(active, title, h1, subtitle, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — NBA2</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
{nav(active)}
<div class="wrap">
<header class="page"><h1>{esc(h1)}</h1><p>{subtitle}</p></header>
{body}
</div>
<footer>NBA2 — originated lines, signals &amp; picks. Factual data verified to NBA.com. Model outputs are labeled <em>Model</em> and are not official. Unverified values are left blank and flagged.</footer>
<script src="assets/app.js"></script>
</body>
</html>"""


def write(name, content):
    with open(os.path.join(SITE, name), "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
def build_index(picks, strategies, flagged, schedule):
    lines = picks["lines"]
    total_signals = sum(len(s["signals"]) for s in picks["strategies"])
    n_strat = len(strategies["records"])
    n_flag = len(flagged["items"])

    cards = f"""
<div class="cards">
  <div class="card"><div class="k">Slate (3-day)</div><div class="v">{len(lines)}</div><div class="s">Nov 13–15, 2026</div></div>
  <div class="card"><div class="k">Originated lines</div><div class="v">{len(lines)}</div><div class="s">one per game</div></div>
  <div class="card"><div class="k">Active signals</div><div class="v">{total_signals}</div><div class="s">across {n_strat} strategies</div></div>
  <div class="card"><div class="k">Flagged items</div><div class="v">{n_flag}</div><div class="s">see Flagged for Review</div></div>
</div>"""

    intro = """
<section class="panel">
<h2>About this platform</h2>
<p class="sub">A self-contained system that originates its own NBA lines, develops skill-based
signal strategies, validates every strategy through gates, measures correlations, removes
luck, and generates picks for every upcoming slate up to 3 days in advance — with
injury-driven rotation and game-flow analysis.</p>
<div class="prose">
<p>Every factual value (schedule, records, injuries) is verified against <strong>NBA.com</strong>
official sources and linked per row. Lines, projections, and picks are <strong>model-originated</strong>
and labeled <span class="pill model">Model</span> — they are not official sportsbook lines.
Anything that cannot be confirmed from an official source is left blank and flagged as
unverified on the <a href="flagged.html">Flagged for Review</a> page.</p>
</div>
</section>"""

    rows = []
    for l in lines:
        rows.append([
            f"{esc(l['date'])}",
            f"{esc(l['time_et'])}",
            f"<strong>{esc(l['away'])}</strong> @ {esc(l['home'])}",
            esc(l['group']),
            f"<span class='num'>{l['predicted_margin']:+.2f}</span>",
            esc(l['originated_spread_label']),
            f"<span class='num'>{l['originated_total_line']:.1f}</span>",
            f"{l['home_win_prob']:.2f}",
            model_pill(),
            src_link(l["source"]),
        ])
    slate_tbl = f"""
<section class="panel">
<h2>3-day slate — originated lines</h2>
<p class="sub">Predicted margin (home perspective), originated spread, and total for every game
in the window. All values are <span class="pill model">Model</span>; the game/schedule data is
verified to NBA.com.</p>
{table(["Date", "Time ET", "Matchup", "Group", "Margin", "Spread", "Total", "Home Win%", "Class", "Source"], rows)}
</section>"""

    sections = f"""
<section class="panel">
<h2>Explore</h2>
<div class="prose">
<ul>
  <li><a href="picks.html">Picks &amp; Lines</a> — originated lines and generated picks by strategy (single, parlay, prop).</li>
  <li><a href="strategies.html">Strategies</a> — strategy definitions, validation gates, and the leaderboard.</li>
  <li><a href="injuries.html">Injuries &amp; Flow</a> — verified injury reports, rotation impact, and game-flow analysis.</li>
  <li><a href="correlations.html">Correlations</a> — correlation methodology and parlay correlation gate.</li>
  <li><a href="executive-summary.html">Executive Summary</a> — key details at a glance.</li>
  <li><a href="suggestions.html">Suggestions</a> — proposed improvements to strengthen decision-making.</li>
  <li><a href="questions.html">Open Questions</a> — the questions/answers needed before decisions, and how to discover missing info.</li>
  <li><a href="flagged.html">Flagged for Review</a> — irregularities and unverified items for manual review.</li>
</ul>
</div>
</section>"""

    body = cards + intro + slate_tbl + sections
    return page("index.html", "Dashboard", "NBA2 Dashboard",
                "Originated NBA lines, skill-based signals, and picks for the 3-day slate. "
                "All factual data verified to NBA.com; model outputs labeled Model.",
                body)


# ---------------------------------------------------------------------------
def build_picks(picks):
    lines = picks["lines"]

    line_rows = []
    for l in lines:
        line_rows.append([
            esc(l["date"]), esc(l["time_et"]),
            f"<strong>{esc(l['away'])}</strong> @ {esc(l['home'])}",
            f"<span class='num'>{l['predicted_margin']:+.2f}</span>",
            esc(l["originated_spread_label"]),
            f"<span class='num'>{l['originated_total_line']:.1f}</span>",
            f"{l['home_win_prob']:.2f}",
            esc(l["away_name"]) + " / " + esc(l["home_name"]),
            model_pill(),
            src_link(l["source"]),
        ])

    pick_rows = []
    for s in picks["strategies"]:
        if not s["signals"]:
            pick_rows.append([
                esc(s["name"]), esc(s["type"]), '<span class="blank">no signals this slate</span>',
                "—", model_pill("Model — no signal"), src_link("https://www.nba.com/schedule"),
            ])
            continue
        for sig in s["signals"]:
            edge = ""
            if sig.get("spread_edge") is not None:
                edge = f"<span class='num'>{sig['spread_edge']:.2f}</span>"
            elif sig.get("total_edge") is not None:
                edge = f"<span class='num'>{sig['total_edge']:.2f}</span>"
            elif sig.get("model_win_prob") is not None:
                edge = f"{sig['model_win_prob']:.2f}"
            elif sig.get("legs"):
                edge = f"{len(sig['legs'])}-leg parlay"
            pick_rows.append([
                esc(s["name"]), esc(s["type"]), esc(sig["selection"]),
                esc(sig["game"]), edge, model_pill(), src_link(sig["source"]),
            ])

    body = f"""
<section class="panel">
<h2>Originated lines (all games)</h2>
<p class="sub">The model's own lines for every game in the 3-day window. Margin is from the
home team's perspective. <span class="pill model">Model</span> = originated, not official.</p>
{table(["Date", "Time ET", "Matchup", "Margin", "Spread", "Total", "Home Win%", "Teams", "Class", "Source"], line_rows)}
</section>

<section class="panel">
<h2>Generated picks by strategy</h2>
<p class="sub">Picks produced by each strategy this slate. Single bets show model win-probability or
edge; the parlay shows its leg count. Props are intentionally blank (no verified player-level data).</p>
<input class="filter" data-filter placeholder="Filter picks…" style="margin:0 0 12px;padding:8px 10px;background:var(--panel-2);border:1px solid var(--line);color:var(--text);border-radius:8px;width:100%;">
{table(["Strategy", "Type", "Selection", "Game", "Prob / Edge", "Class", "Source"], pick_rows)}
</section>

<section class="panel">
<h2>Notes on pick generation</h2>
<div class="note blue"><p><strong>Single bets</strong> (Margin Favorite, Spread Value) fire only when the
model edge clears its threshold — selective, skill-based, no bet on coin-flips.</p>
<p><strong>Parlays</strong> combine legs only from <em>distinct games</em> (correlation gate), so legs are
approximately independent.</p>
<p><strong>Totals</strong> are inactive this slate because no verified pace data exists for the teams
(all predicted totals equal the unverified baseline) — see <a href="flagged.html">Flagged for Review</a>.</p>
<p><strong>Player props</strong> are a framework pending verified player-level data; values are left blank,
never inferred.</p></div>
</section>"""
    return page("picks.html", "Picks & Lines", "Picks & Originated Lines",
                "Model-originated lines and the picks generated for the 3-day slate, organized by strategy.",
                body)


# ---------------------------------------------------------------------------
def build_strategies(strategies, picks):
    gate_rows = [[esc(k), esc(v)] for k, v in strategies["gates"].items()]

    rec_rows = []
    for r in strategies["records"]:
        cells = [
            f"<strong>{r['rank']}</strong>",
            esc(r["name"]), esc(r["type"]), f"{r['signals']}",
        ]
        for gkey in ["G1_data_integrity", "G2_edge", "G3_correlation", "G4_sample_size", "G5_variance_luck"]:
            val = r["gates"].get(gkey)
            if val is None:
                cells.append('<span class="blank">—</span>')
            else:
                cells.append(status_pill(val, "Pass", "Fail"))
        cells.append(status_pill(r["status"] == "validated", "Validated", "Provisional"))
        cells.append(src_link("https://www.nba.com/schedule"))
        rec_rows.append(cells)

    defs = {s["id"]: s for s in [
        {"id": "S1_MarginFavorite", "name": "Margin Favorite (Single)", "type": "single",
         "description": "Single straight bet on the model's outright favorite where model win probability clears the edge threshold."},
        {"id": "S2_SpreadValue", "name": "Spread Value (Single)", "type": "single",
         "description": "Single bet on the favorite to cover when the model's predicted margin is strong (clears the strong-margin threshold)."},
        {"id": "S3_Totals", "name": "Totals (Single)", "type": "single",
         "description": "Single over/under on the originated total where the predicted-total edge clears the threshold."},
        {"id": "S4_LeanParlay", "name": "Lean Parlay (Combo)", "type": "parlay",
         "description": "2–3 single-bet legs from different games, each clearing the edge gate, combined into a parlay (correlation gate: distinct games)."},
        {"id": "S5_PlayerPropCombo", "name": "Player Prop Combo", "type": "prop",
         "description": "Player-prop combination (over/under player totals). Requires verified player-level data; values left blank until sourced."},
    ]}
    def_rows = [[esc(d["name"]), esc(d["type"]), esc(d["description"])] for d in defs.values()]

    lb_rows = []
    for r in strategies["records"]:
        lb_rows.append([
            f"<strong>{r['rank']}</strong>", esc(r["name"]),
            esc(r.get("performance", "pending tracked results")),
            esc(r.get("roi") if r.get("roi") is not None else "—"),
            esc(r.get("hit_rate") if r.get("hit_rate") is not None else "—"),
            src_link("https://www.nba.com/schedule"),
        ])

    body = f"""
<section class="panel">
<h2>Strategy definitions</h2>
<p class="sub">Five strategies covering single bets, parlays, and player-prop combos.</p>
{table(["Strategy", "Type", "Description"], def_rows)}
</section>

<section class="panel">
<h2>Validation gates</h2>
<p class="sub">Every strategy must pass these gates before its signal is eligible.</p>
{table(["Gate", "Requirement"], gate_rows)}
</section>

<section class="panel">
<h2>Strategy validation results</h2>
<p class="sub">Gate outcomes for each strategy this slate. G4 (sample size) fails for all because no
results have been tracked yet — strategies are provisional until tracked results prove skill over luck.</p>
{table(["#", "Strategy", "Type", "Signals", "G1", "G2", "G3", "G4", "G5", "Status", "Source"], rec_rows)}
</section>

<section class="panel">
<h2>Leaderboard</h2>
<p class="sub">Ranked by tracked performance (ROI / hit rate). No games tracked to completion yet,
so all strategies are provisional — the leaderboard rewards top performers once results are recorded.</p>
{table(["Rank", "Strategy", "Performance", "ROI", "Hit Rate", "Source"], lb_rows)}
</section>

<section class="panel">
<h2>Removing luck</h2>
<div class="note"><p>{esc(strategies["luck_vs_skill"])}</p></div>
</section>"""
    return page("strategies.html", "Strategies", "Strategies & Validation Gates",
                "Signal-generation strategies, the validation gates each must pass, and the leaderboard.",
                body)


# ---------------------------------------------------------------------------
def build_injuries(injuries, gameflow, records):
    # Per-game injury summary.
    inj_rows = []
    for g in injuries["games"]:
        out = sum(1 for i in g["injuries"] if i["status"] == "Out")
        doubt = sum(1 for i in g["injuries"] if i["status"] == "Doubtful")
        q = sum(1 for i in g["injuries"] if i["status"] == "Questionable")
        inj_rows.append([
            esc(g["date"]), esc(g["matchup"]),
            f"<span class='num'>{out}</span>", f"<span class='num'>{doubt}</span>",
            f"<span class='num'>{q}</span>", f"<span class='num'>{len(g['injuries'])}</span>",
            model_pill("verified statuses"), src_link(g["source"]),
        ])

    # Game-flow table.
    flow_rows = []
    for f in gameflow["rows"]:
        flow_rows.append([
            esc(f["matchup"]),
            esc(f["injury_shifted_lean"]),
            f"<span class='num'>{f['away_injury_impact']:.2f}</span>",
            f"<span class='num'>{f['home_injury_impact']:.2f}</span>",
            esc(f["away_rotation"]),
            esc(f["home_rotation"]),
            esc(f["tempo_proxy"]),
            model_pill("flow estimate"),
            src_link(f["source"]),
        ])

    not_sub = "".join(
        f"<li>{esc(x['date'])} {esc(x['matchup'])} — {esc(x['status'])}</li>"
        for x in injuries["upcoming_not_submitted"]
    )

    body = f"""
<section class="panel">
<h2>Official injury report — 11/13/2026</h2>
<p class="sub">Verified per-game injury status counts from the official NBA.com injury report.
Statuses are verified facts; impact counts are derived from the verified statuses.</p>
<input class="filter" data-filter placeholder="Filter games…" style="margin:0 0 12px;padding:8px 10px;background:var(--panel-2);border:1px solid var(--line);color:var(--text);border-radius:8px;width:100%;">
{table(["Date", "Matchup", "Out", "Doubtful", "Questionable", "Listed", "Class", "Source"], inj_rows)}
</section>

<section class="panel">
<h2>Game-flow analysis</h2>
<p class="sub">How injuries shift each game's balance and projected rotation. Injury-impact points
and the shifted lean are <span class="pill model">Model</span> estimates; tempo proxy is unverified
pending pace data. Statuses verified to NBA.com.</p>
<input class="filter" data-filter placeholder="Filter matchups…" style="margin:0 0 12px;padding:8px 10px;background:var(--panel-2);border:1px solid var(--line);color:var(--text);border-radius:8px;width:100%;">
{table(["Matchup", "Shifted Lean", "Away Inj Impact", "Home Inj Impact", "Away Rotation Note", "Home Rotation Note", "Tempo Proxy", "Class", "Source"], flow_rows)}
</section>

<section class="panel">
<h2>Upcoming games — injury reports not yet submitted</h2>
<p class="sub">The league's official injury report lists these games as <strong>NOT YET SUBMITTED</strong>.
Data will be populated when updated reports are filed closer to tip-off.</p>
<ul>{not_sub}</ul>
</section>"""
    return page("injuries.html", "Injuries & Flow", "Injuries & Game-Flow Analysis",
                "Verified injury reports, rotation-minute/production impact estimates, and game-flow analysis.",
                body)


# ---------------------------------------------------------------------------
def build_correlations(correlations):
    rows = []
    for r in correlations["rows"]:
        val = r["value"]
        if val == "pending":
            val_cell = '<span class="pill warn">pending</span>'
        else:
            val_cell = f"<span class='num'>{val}</span>"
        rows.append([
            esc(r["factor_a"]), esc(r["factor_b"]), val_cell,
            f"<span class='num'>{r['n']}</span>", esc(r["note"]),
            src_link("https://www.nba.com/stats"),
        ])

    body = f"""
<section class="panel">
<h2>Correlation analysis</h2>
<p class="sub">Pearson correlation between verified team-level factors. Values marked
<span class="pill warn">pending</span> require a historical dataset — the current snapshot has win%
for all 30 teams but PPG/OPPG only for 2, which is not enough to compute a meaningful correlation.</p>
{table(["Factor A", "Factor B", "Correlation (r)", "n", "Note", "Source"], rows)}
</section>

<section class="panel">
<h2>Parlay correlation gate</h2>
<div class="note blue"><p>{esc(correlations["parlay_correlation_assumption"])}</p></div>
<p class="sub">This gate (G3) keeps parlay legs independent so the system avoids self-correlated
combos that inflate variance without adding skill.</p>
</section>

<section class="panel">
<h2>Luck vs. skill</h2>
<div class="note"><p>{esc(correlations["luck_vs_skill"])}</p></div>
</section>"""
    return page("correlations.html", "Correlations", "Correlations",
                "Correlation methodology, parlay correlation gate, and how luck is separated from skill.",
                body)


# ---------------------------------------------------------------------------
def build_executive_summary(picks, strategies, flagged, schedule):
    lines = picks["lines"]
    total_signals = sum(len(s["signals"]) for s in picks["strategies"])
    n_flag = len(flagged["items"])
    n_games = len(lines)

    body = f"""
<section class="panel">
<h2>Objective</h2>
<div class="prose"><p>Originate NBA lines, develop selectively skill-based signal strategies (single
bets, parlays, player-prop combos), validate every strategy through gates, measure correlations,
remove luck, and generate picks for every upcoming slate up to 3 days in advance — with
injury-driven rotation and game-flow analysis.</p></div>
</section>

<section class="panel">
<h2>Key details at a glance</h2>
<div class="cards">
  <div class="card"><div class="k">Slate covered</div><div class="v">{n_games}</div><div class="s">Nov 13–15, 2026 (3 days)</div></div>
  <div class="card"><div class="k">Originated lines</div><div class="v">{n_games}</div><div class="s">one per game, all Model</div></div>
  <div class="card"><div class="k">Active signals</div><div class="v">{total_signals}</div><div class="s">single + parlay</div></div>
  <div class="card"><div class="k">Strategies</div><div class="v">{len(strategies['records'])}</div><div class="s">all provisional (no tracked results)</div></div>
  <div class="card"><div class="k">Flagged items</div><div class="v">{n_flag}</div><div class="s">see Flagged for Review</div></div>
</div>
</section>

<section class="panel">
<h2>What the system does</h2>
<div class="prose">
<ul>
<li><strong>Originates lines</strong> from verified inputs (team win-loss records, home/away, official
injury statuses) using a transparent, auditable model. Lines are labeled <span class="pill model">Model</span>.</li>
<li><strong>Generates picks</strong> for the full 3-day slate, up to 3 days ahead, using originated lines.</li>
<li><strong>Validates every strategy</strong> through five gates (data integrity, edge, correlation,
sample size, luck/skill) before a signal is eligible.</li>
<li><strong>Measures correlations</strong> and enforces a parlay correlation gate so combos use
independent legs.</li>
<li><strong>Tracks injuries</strong> and their impact on rotation minutes and production, producing
game-flow analysis.</li>
</ul>
</div>
</section>

<section class="panel">
<h2>Verification posture</h2>
<div class="prose">
<p>All factual data — schedule, records, and injuries — is verified against <strong>NBA.com</strong>
and linked per row. The system deliberately does not infer unverified values: where a value cannot
be confirmed from an official source, it is left blank and flagged (e.g., PPG/OPPG for 28 of 30
teams; player-prop values; historical correlations). Model outputs are never presented as official.</p>
<p>Current limitations (all flagged, none blocking): totals use an unverified league-average baseline;
injury-impact weights are model estimates pending player-level usage data; no games have been tracked
to completion, so all strategies remain provisional.</p>
</div>
</section>

<section class="panel">
<h2>Where to look next</h2>
<div class="prose"><ul>
<li><a href="picks.html">Picks &amp; Lines</a> for the originated lines and current picks.</li>
<li><a href="strategies.html">Strategies</a> for gate results and the leaderboard.</li>
<li><a href="injuries.html">Injuries &amp; Flow</a> for rotation and game-flow detail.</li>
<li><a href="suggestions.html">Suggestions</a> and <a href="questions.html">Open Questions</a> for the
path to strengthen decision-making.</li>
<li><a href="flagged.html">Flagged for Review</a> for every irregularity and unverified item.</li>
</ul></div>
</section>"""
    return page("executive-summary.html", "Executive Summary", "Executive Summary",
                "Key details of the NBA2 lines-origination, signal, and picks platform.",
                body)


# ---------------------------------------------------------------------------
SUGGESTIONS = [
    ("Acquire verified team pace & efficiency data", "Data",
     "Verified PPG/OPPG for all 30 teams would activate the Totals strategy and remove the unverified 224 baseline, sharpening every total line.",
     "Pull team traditional stats (PPG/OPPG/pace) from NBA.com/stats for all teams; verify per row.",
     "High"),
    ("Acquire verified player-level box-score & usage data", "Data",
     "Player-prop combos and real rotation-minute impact require player usage, box-score, and projection data currently left blank.",
     "Pull player traditional + advanced stats and usage from NBA.com/stats; build a player projection layer.",
     "High"),
    ("Build a historical results tracker", "System",
     "The leaderboard rewards top performers, but no games are tracked to completion yet, so all strategies are provisional.",
     "Add a results ledger keyed by game_id/strategy that records hit/miss and computes ROI + hit rate after each slate.",
     "High"),
    ("Compute historical correlations on the full dataset", "Analysis",
     "Correlation values are pending because the snapshot lacks a historical sample; this blocks luck-vs-skill stats.",
     "Once a results tracker exists, compute correlations over accumulated observations and run binomial tests vs .500.",
     "Medium"),
    ("Add a model-version & parameter log", "System",
     "Model parameters (SPREAD_SCALE, HOME_ADV, thresholds) are tunable; documenting versions prevents silent drift.",
     "Log parameter sets per generation run and show the active version on the dashboard.",
     "Medium"),
    ("Add line movement / market comparison (optional)", "Data",
     "Comparing originated lines to market lines would surface true edges, but requires a verified odds source.",
     "Only once a trusted, verifiable odds source is available; never infer odds. Flag if unavailable.",
     "Low"),
    ("Add a suggestions review workflow", "UX",
     "Suggestions need a review step so the best path is chosen before implementation, per the requirement.",
     "Add status (proposed → accepted → implemented) to each suggestion, editable by the reviewer.",
     "Medium"),
]


def build_suggestions():
    rows = []
    for name, cat, rationale, discovery, priority in SUGGESTIONS:
        prio_pill = {"High": "bad", "Medium": "warn", "Low": "ok"}[priority]
        rows.append([
            esc(name), esc(cat), esc(rationale), esc(discovery),
            f'<span class="pill {prio_pill}">{esc(priority)}</span>',
            '<span class="pill muted">Proposed</span>',
            src_link("https://www.nba.com/stats"),
        ])
    body = f"""
<section class="panel">
<h2>Suggestions to improve decision-making</h2>
<p class="sub">Proposed improvements, each with the rationale, the data/action needed to discover or
implement it, and a priority. Reviewers choose the best path here before any change is implemented —
status stays <span class="pill muted">Proposed</span> until accepted.</p>
{table(["Suggestion", "Category", "Rationale", "How to discover / implement", "Priority", "Status", "Reference"], rows)}
</section>

<section class="panel">
<h2>How this section is used</h2>
<div class="note blue"><p>This page is the review queue. A reviewer reads each suggestion, weighs
priority and data needs, and marks the chosen path before implementation. Nothing here is implemented
automatically — suggestions are proposals, not decisions.</p></div>
</section>"""
    return page("suggestions.html", "Suggestions", "Suggestions",
                "Proposed improvements to strengthen decision-making, with a review path before implementation.",
                body)


# ---------------------------------------------------------------------------
QUESTIONS = [
    ("What verified team-level inputs should anchor the model?",
     "Win-loss records for all 30 teams (verified to NBA.com).",
     "Verified PPG/OPPG/pace for all teams to replace the unverified total baseline.",
     "Pull NBA.com/stats team traditional stats for all 30 teams and verify line by line.",
     "Open"),
    ("How should injury impact be quantified?",
     "Official per-game injury statuses (Out/Doubtful/Questionable/Probable/Available), verified to the NBA.com injury report.",
     "Player-level importance (usage, box-score share) to weight each absence's rotation/production impact.",
     "Pull player usage & box-score data from NBA.com/stats; build a weighted impact model.",
     "Open"),
    ("How do we prove a strategy is skill, not luck?",
     "A transparent skill basis and a validation-gate framework for every strategy.",
     "Tracked results over a minimum sample plus a binomial test vs .500 and ROI convergence.",
     "Build the results tracker, then run statistical tests on accumulated hit rates.",
     "Open"),
    ("What correlations must be computed?",
     "A documented methodology (Pearson r) and the parlay correlation gate (distinct-game legs).",
     "Concrete historical correlation values between factors (win%, pace, efficiency, etc.).",
     "Accumulate a historical dataset via the results tracker, then compute correlations over it.",
     "Open"),
    ("Where do player-prop lines come from?",
     "A defined Player Prop Combo strategy (S5) and the requirement to use verified sources only.",
     "Verified player-level production projections for each prop market.",
     "Source player stats/projections from NBA.com/stats; leave props blank until then.",
     "Open"),
    ("How far ahead can picks be generated?",
     "The 3-day slate window (Nov 13–15) is fully covered with originated lines.",
     "Confirm whether 3 days is the hard limit or whether longer horizons are needed.",
     "Confirm scope with the reviewer; the pipeline already supports any slate window from the schedule.",
     "Open"),
    ("What defines a passing validation gate?",
     "Five gates defined: data integrity, edge, correlation, sample size, luck/skill.",
     "Exact thresholds (e.g., minimum win-prob, strong-margin, sample size) and whether they are acceptable.",
     "Review the threshold constants in nba2/model.py and nba2/strategies.py; tune with the reviewer.",
     "Open"),
    ("Which sportsbook/odds source (if any) is trusted?",
     "None currently — the system originates its own lines and never infers odds.",
     "A verified, trusted odds source if market-comparison is desired.",
     "Confirm whether a trusted odds source is available; if not, keep market comparison unflagged/off.",
     "Open"),
]


def build_questions():
    rows = []
    for q, have, need, discover, status in QUESTIONS:
        rows.append([
            esc(q), esc(have), esc(need), esc(discover),
            f'<span class="pill warn">{esc(status)}</span>',
            src_link("https://www.nba.com/stats"),
        ])
    body = f"""
<section class="panel">
<h2>Questions, information &amp; answers to address before decisions</h2>
<p class="sub">A clear list of what must be resolved before a decision can reasonably be made — what
we already have, what we do not have, and a suggestion to discover the missing information.</p>
{table(["Question", "What we already have", "What we still need", "Suggestion to discover", "Status", "Reference"], rows)}
</section>

<section class="panel">
<h2>Decision rule</h2>
<div class="note"><p>No decision is made until the corresponding "what we still need" item is verified
from an official source. Where information is missing, the suggestion column states how to discover it
— never fill gaps by inference.</p></div>
</section>"""
    return page("questions.html", "Open Questions", "Open Questions",
                "The questions, information, and answers needed before decisions, plus how to discover missing info.",
                body)


# ---------------------------------------------------------------------------
def build_flagged(flagged):
    rows = []
    for it in flagged["items"]:
        sev = it["severity"]
        sev_pill = {"High": "bad", "Medium": "warn", "Low": "ok"}.get(sev, "muted")
        rows.append([
            esc(it["item"]), esc(it["detail"]), esc(it["value"]),
            f'<span class="pill {sev_pill}">{esc(sev)}</span>',
            src_link(it["source"]),
        ])
    body = f"""
<section class="panel">
<h2>Flagged for review</h2>
<p class="sub">Irregularities and unverified items for manual review. Each links to the official
source where applicable; unverified values are left blank and never inferred. These do not block the
site — they are published here so a reviewer can request changes after the site is live.</p>
{table(["Item", "Detail", "Value", "Severity", "Source"], rows)}
</section>"""
    return page("flagged.html", "Flagged for Review", "Flagged for Review",
                "Irregularities and unverified items, each with its source link, for manual review.",
                body)


# ---------------------------------------------------------------------------
def main():
    os.makedirs(ASSETS, exist_ok=True)
    picks = load("picks.json")
    strategies = load("strategies.json")
    correlations = load("correlations.json")
    injuries = load("injuries.json")
    gameflow = load("gameflow.json")
    flagged = load("flagged.json")
    schedule = load("schedule.json")

    write("index.html", build_index(picks, strategies, flagged, schedule))
    write("picks.html", build_picks(picks))
    write("strategies.html", build_strategies(strategies, picks))
    write("injuries.html", build_injuries(injuries, gameflow, load("records.json")))
    write("correlations.html", build_correlations(correlations))
    write("executive-summary.html", build_executive_summary(picks, strategies, flagged, schedule))
    write("suggestions.html", build_suggestions())
    write("questions.html", build_questions())
    write("flagged.html", build_flagged(flagged))

    print("Site built: 9 pages written to the repo root (GitHub Pages: main branch, path /)")


if __name__ == "__main__":
    main()
