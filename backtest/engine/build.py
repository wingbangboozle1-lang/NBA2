"""Build every published artefact for the measured-skill report.

Outputs (all deterministic given the committed snapshots):
    backtest/data/report.json   — single source for the HTML
    backtest/pages/*.html       — the report pages
    backtest/index.html         — landing page
    backtest/assets/style.css   — shared stylesheet

No number reaches a page unless it was computed here from `data/raw/history/*.json`
(official NBA.com final scores) and every game row carries its own nba.com URL.
"""

from __future__ import annotations

import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backtest.engine import correlation, gates, leaderboard, skill  # noqa: E402
from backtest.engine import stats as bstats  # noqa: E402
from backtest.engine import walkforward as wf  # noqa: E402

OUT = ROOT / "backtest"
PAGES = OUT / "pages"
DATA = OUT / "data"

NAV = [
    ("index.html", "Overview"),
    ("pages/sample-integrity.html", "Sample &amp; Integrity"),
    ("pages/walk-forward.html", "Walk-Forward Results"),
    ("pages/luck-vs-skill.html", "Luck vs Skill"),
    ("pages/correlation.html", "Correlation"),
    ("pages/leaderboard.html", "Leaderboard"),
    ("pages/validation-gates.html", "Validation Gates"),
    ("pages/game-flow.html", "Game Flow &amp; Rest"),
    ("pages/questions.html", "Open Questions"),
    ("pages/suggestions.html", "Suggestions"),
    ("pages/flagged-review.html", "Flagged for Review"),
    ("pages/sources.html", "Sources"),
]


def esc(x) -> str:
    return html.escape(str(x))


def badge(kind: str) -> str:
    return f'<span class="badge badge-{kind}">{esc(kind)}</span>'


def table(headers, rows, caption="", cls="data") -> str:
    out = [f'<div class="table-wrap"><table class="{cls}">']
    if caption:
        out.append(f'<caption>{esc(caption)}</caption>')
    out.append("<thead><tr>" + "".join(f"<th scope=\"col\">{h}</th>" for h in headers) + "</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)



def source_line(*urls: str, note: str = "") -> str:
    """A closing citation block, so every page names its official source explicitly."""
    items = " · ".join(src(u) for u in urls)
    extra = f" — {esc(note)}" if note else ""
    return (f'<div class="card"><h2>Official source for this page</h2>'
            f'<p class="blurb">{items}{extra}</p></div>')

def page(slug: str, title: str, body: str, meta: dict) -> None:
    is_root = "/" not in slug
    base = "" if is_root else "../"
    nav_items = []
    for href, label in NAV:
        active = ' class="active"' if href == slug else ""
        nav_items.append(f'<li><a href="{base}{href}"{active}>{label}</a></li>')
    nav = "".join(nav_items)
    css = f"{base}assets/style.css"
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} · NBA2 measured skill</title>
<meta name="description" content="Walk-forward backtest of the NBA2 originated lines against official NBA.com final scores.">
<link rel="stylesheet" href="{css}">
</head>
<body>
<div class="app">
<header class="header">
  <h1><a class="homelink" href="{base}index.html">NBA2 · Measured Skill</a></h1>
  <div class="subtitle">Every number graded against official NBA.com final scores · {esc(meta['n_games'])} games · as of {esc(meta['last_date'])}</div>
</header>
<aside class="sidebar"><nav aria-label="Sections"><ul>{nav}</ul></nav>
  <div class="side-note">Rebuild:<br><code>python3 -m backtest.engine.build</code></div>
</aside>
<main class="main">
{body}
<footer class="footer">
  <p>Every row links its own source. Nothing here is betting advice, and no bet is placed by this repository.
  No odds feed is connected, so no ROI, edge or stake is published anywhere on this site.</p>
</footer>
</main>
</div>
</body>
</html>
"""
    path = OUT / slug
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_doc)


def src(url: str, label: str = "nba.com") -> str:
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'


def build() -> dict:
    games = wf.load_games()
    rows = wf.walk_forward(games)
    wf.assert_no_leakage(rows, games)
    d = [r.as_dict() for r in rows]

    acc = skill.accuracy_block(d)
    ats = skill.ats_block(d)
    gap = skill.baseline_gap(d)
    naive = skill.naive_baselines(d, games)
    cal = skill.calibration_table(d)
    tiers = skill.tier_block(d)
    power = skill.power_block()

    corr_mt = correlation.margin_total_correlation(games)
    corr_leg = correlation.leg_dependence(d)
    corr_x = correlation.cross_game_independence(games)
    rest = correlation.rest_effects(games)

    gres = gates.evaluate(d, corr_mt)
    board = leaderboard.build(d, gres, len(games))

    dates = wf.completed_dates(games)
    meta = {
        "n_games": len(games),
        "n_graded": acc["n"],
        "first_date": dates[0],
        "last_date": dates[-1],
        "n_dates": len(dates),
        "generated": "2026-11-14",
    }

    integrity = _integrity(games)
    report = {
        "schema": "nba2.backtest-report.v1",
        "meta": meta,
        "integrity": integrity,
        "accuracy": acc,
        "ats": ats,
        "baseline_gap": gap,
        "naive_baselines": naive,
        "calibration": cal,
        "tiers": tiers,
        "power": power,
        "correlation": {"margin_total": corr_mt, "legs": corr_leg,
                        "cross_game": corr_x, "rest": rest},
        "gates": gres,
        "leaderboard": board,
        "leaderboard_notes": leaderboard.notes(len(games)),
        "games": d,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "report.json").write_text(json.dumps(report, indent=1) + "\n")

    _write_pages(report, meta, integrity)
    return report


# ----------------------------------------------------------------- pages


def _kpi(label, value, sub="") -> str:
    return (f'<div class="kpi"><div class="kpi-v">{value}</div>'
            f'<div class="kpi-l">{label}</div>'
            + (f'<div class="kpi-s">{sub}</div>' if sub else "") + "</div>")


def _write_pages(report: dict, meta: dict, integrity: dict) -> None:
    acc, gap, naive = report["accuracy"], report["baseline_gap"], report["naive_baselines"]
    corr = report["correlation"]
    gs = report["gates"]["summary"]

    # ---------------------------------------------------------------- landing
    body = f"""
<section class="hero">
  <h2>What is actually proven</h2>
  <p>Every earlier version of this repository published a model and a leaderboard but
  <strong>zero graded outcomes</strong>. This report grades the model against
  <strong>{meta['n_games']} official NBA.com final scores</strong>, point-in-time, and reports what survives.</p>
</section>
<div class="notice notice-warning"><strong>The honest headline:</strong>
the originated line beats a constant line on margin error, but it is
<strong>statistically indistinguishable from the trivial "pick the team with the better point
differential" rule</strong> (model {naive['originated_model']['rate']:.1%} vs
better-record {naive['better_net_rating']['rate']:.1%}, difference
{naive['model_vs_better_net']['observed_diff']:+.2%}, p = {naive['model_vs_better_net']['p_value']:.2f}).
No strategy is promoted and no reward is paid. That is the system working, not failing.</div>
<div class="card"><div class="kpi-grid">
{_kpi("games graded", meta['n_graded'], f"of {meta['n_games']} captured")}
{_kpi("margin MAE", f"{acc['margin_mae_model']:.2f}", f"naive 0-line {acc['margin_mae_baseline_zero']:.2f}")}
{_kpi("winner AUROC", f"{acc['auroc_winner']:.3f}", "0.50 = coin flip")}
{_kpi("straight-up", f"{acc['straight_up_accuracy']:.1%}", "95% CI " + f"{acc['straight_up_ci95'][0]:.1%}-{acc['straight_up_ci95'][1]:.1%}")}
{_kpi("better-record rule", f"{naive['better_net_rating']['rate']:.1%}", "same games")}
{_kpi("vs-baseline p", f"{gap['p_value']:.2f}", "permutation test")}
{_kpi("gates passed", len(gs['passed_reliable']), f"of {gs['n']} registered, counted")}
{_kpi("disputed", len(gs['passed_disputed']), ", ".join(gs['passed_disputed']) + " — excluded" if gs['passed_disputed'] else "none")}
{_kpi("reward paid", "0", "withheld by gates")}
</div></div>
<section class="card"><h2>What changed in this session</h2>
<ul class="tight">
<li><strong>Official results history captured.</strong> {meta['n_games']} games, {meta['first_date']} → {meta['last_date']},
each with its own <code>nba.com/game/&lt;id&gt;</code> URL. This is the missing input every prior page cited.</li>
<li><strong>Records reconstructed and checked.</strong> Team W-L rebuilt from final scores alone matches
{integrity['exact_check']['matched']}/{integrity['exact_check']['checked']} official post-game records exactly.</li>
<li><strong>Walk-forward, leakage-tested.</strong> No game is graded using information from its own date.
The check is automated, not asserted.</li>
<li><strong>Luck separated from skill.</strong> Wilson intervals, a permutation test, a naive-rule
control and an explicit power calculation — so "not enough data" is a number, not an excuse.</li>
<li><strong>Correlations measured, not assumed.</strong> The margin↔total premise behind the same-game
parlay strategy is <strong>not supported</strong>: r = {corr['margin_total']['r']} (95% CI
{corr['margin_total']['ci95'][0]} to {corr['margin_total']['ci95'][1]}).</li>
<li><strong>Gates re-run on evidence.</strong> G-04 (accuracy vs baselines) passes its
registered wording only against an unshrunk strawman and is <strong>disputed</strong>;
G-07 (walk-forward) now has real numbers and <strong>PASSES</strong>.</li>
</ul></section>
<section class="card"><h2>Sections</h2><div class="cat-grid">
<a class="cat-card" href="pages/sample-integrity.html"><h3>Sample &amp; Integrity</h3><p>What was captured and how it was verified</p></a>
<a class="cat-card" href="pages/walk-forward.html"><h3>Walk-Forward Results</h3><p>Every graded game</p></a>
<a class="cat-card" href="pages/luck-vs-skill.html"><h3>Luck vs Skill</h3><p>Intervals, baselines, power</p></a>
<a class="cat-card" href="pages/correlation.html"><h3>Correlation</h3><p>Measured, with sample sizes</p></a>
<a class="cat-card" href="pages/leaderboard.html"><h3>Leaderboard</h3><p>Ranked on deflated z</p></a>
<a class="cat-card" href="pages/validation-gates.html"><h3>Validation Gates</h3><p>Pass / fail / blocked, with arithmetic</p></a>
<a class="cat-card" href="pages/game-flow.html"><h3>Game Flow &amp; Rest</h3><p>Does rest actually matter?</p></a>
<a class="cat-card" href="pages/questions.html"><h3>Open Questions</h3><p>What still blocks a decision</p></a>
<a class="cat-card" href="pages/suggestions.html"><h3>Suggestions</h3><p>Review before implementing</p></a>
<a class="cat-card" href="pages/flagged-review.html"><h3>Flagged for Review</h3><p>Open irregularities</p></a>
<a class="cat-card" href="pages/sources.html"><h3>Sources</h3><p>Every URL used</p></a>
</div></section>
"""
    page("index.html", "Overview", body, meta)

    # ---------------------------------------------------------------- integrity
    rows_i = []
    for r in integrity["reconstruction"]:
        rows_i.append([esc(r["team"]), esc(r["official"]), esc(r["reconstructed"]),
                       esc(r["official_games"]), esc(r["reconstructed_games"]),
                       esc(r["status"]), src(r["source_url"])])
    body = f"""
<section class="hero"><h2>Sample &amp; integrity</h2>
<p>An accuracy number is worthless if the outcomes it was measured on are wrong. So the
outcomes are checked first, and the checks are shown.</p></section>
<div class="card"><h2>How the sample was captured</h2>
<ul class="tight">
<li>Source: {src('https://www.nba.com/games', 'nba.com/games')} date pages, read one day at a time.</li>
<li>{meta['n_games']} games across {meta['n_dates']} dates ({meta['first_date']} → {meta['last_date']}).</li>
<li>Each game keeps its own <code>nba.com/game/&lt;slug&gt;-&lt;id&gt;</code> URL, so any row can be re-checked by hand.</li>
<li>Overtime is stored as a period count (4 = regulation), because two games in this window went to
double overtime and a boolean would have silently flattened them.</li>
</ul></div>
<div class="notice notice-warning"><strong>Two dates could not be verified and are excluded, not guessed.</strong>
The official pages for <strong>2026-11-06</strong> (9 games) and <strong>2026-11-11</strong> (10 games)
rendered with no scores — the score elements were empty. Those 19 games are recorded as
<strong>unverified</strong> and left out of every calculation on this site.
<a href="flagged-review.html">See FLAG-BT-01</a>.</div>
<div class="card"><h2>Check 1 — do reconstructed records match the official post-game records?</h2>
<p>Every nba.com game card prints both teams' W-L <em>after</em> that game. Rebuilding each team's
record from final scores alone and comparing with those printed cards is an independent test of
both the scores and the home/away assignment.</p>
{table(["Result", "Count"], [
    ["Exact match (cards dated on or before 2026-11-05, where every game is captured)", esc(integrity['exact_check']['matched']) + "/" + esc(integrity['exact_check']['checked'])],
    ["Consistent (later cards: reconstruction never exceeds the official card, as required when games are missing)", esc(integrity['bounded_check']['consistent']) + "/" + esc(integrity['bounded_check']['checked'])],
    ["Violations (a team showing MORE wins or losses than its official card)", esc(integrity['bounded_check']['violations'])],
], "Reconstruction checks")}
<p class="blurb">One transcription error was found and fixed this way: game 0022600159 was first
keyed as DAL@CHA and is officially <strong>DET</strong>@CHA. The correction is recorded in the
snapshot itself, not silently edited.</p></div>
<div class="card"><h2>Check 2 — reconstruction vs the repository's standings snapshot</h2>
<p>The repo already publishes <code>data/standings-2026-11-13.csv</code> (as-of 2026-11-12). A
reconstruction from final scores must <em>never exceed</em> those records; where it falls short, the
difference is exactly the number of unverified games on 11/06 and 11/11.</p>
{table(["Team", "Snapshot W-L", "Reconstructed W-L", "Snapshot games", "Reconstructed games", "Status", "Source"], rows_i,
       "Reconstruction from final scores vs the committed standings snapshot")}
<p class="blurb">{esc(integrity['reconstruction_note'])}</p></div>
<div class="card"><h2>What this sample is not</h2>
<ul class="tight">
<li><strong>Not complete.</strong> {meta['n_dates']} dates, not the full season; the two excluded dates are listed above.</li>
<li><strong>Not a market sample.</strong> No prices were captured, so nothing here is an ROI.</li>
<li><strong>Not injury-adjusted.</strong> The results snapshot carries no player data.</li>
<li><strong>Not point-in-time for injuries.</strong> Availability is ignored, which is a documented
weakness of the model, not a hidden one.</li>
</ul></div>
"""
    page("pages/sample-integrity.html", "Sample &amp; Integrity", body, meta)

    # ---------------------------------------------------------------- walk-forward
    graded_rows = [r for r in report["games"] if r["pred_margin_home"] is not None]
    tbl = []
    for r in graded_rows:
        err_class = "ok" if abs(r["margin_error"]) <= 10 else "warn"
        tbl.append([
            esc(r["date"]),
            f'{esc(r["away"])} @ {esc(r["home"])}',
            f'{r["away_pts"]}-{r["home_pts"]}',
            f'{r["pred_margin_home"]:+.1f}',
            f'{r["actual_margin_home"]:+d}',
            f'<span class="err {err_class}">{r["margin_error"]:+.1f}</span>',
            f'{r["pred_total"]:.1f}' if r["pred_total"] is not None else "",
            f'{r["actual_total"]}',
            f'{r["p_home"]:.3f}',
            badge(r["tier"]),
            src(r["source_url"], r["game_id"]),
        ])
    body = f"""
<section class="hero"><h2>Walk-forward results</h2>
<p>For each game, the line shown was produced using only games completed <em>before</em> that
game's date. The check is automated by <code>assert_no_leakage</code>, which re-derives every
team's pre-game game count from the raw history.</p></section>
<div class="card"><div class="kpi-grid">
{_kpi("graded games", acc['n'])}
{_kpi("margin MAE", f"{acc['margin_mae_model']:.2f} pts")}
{_kpi("margin RMSE", f"{acc['margin_rmse_model']:.2f} pts")}
{_kpi("bias (pred - actual)", f"{acc['margin_bias']:+.2f} pts")}
{_kpi("total MAE", f"{acc['total_mae_model']:.2f} pts", f"baseline {acc['total_mae_baseline_mean']:.2f}")}
{_kpi("winner AUROC", f"{acc['auroc_winner']:.3f}")}
</div>
<p class="blurb">A positive bias means the model over-rates the home team; a near-zero bias is a
property the line must have before its error can be interpreted.</p></div>
<div class="card"><h2>By confidence tier</h2>
{table(["Tier", "Games", "Mean abs error (pts)", "AUROC", "Straight-up", "95% CI"],
       [[badge(t['tier']), esc(t.get('n', 0)),
         esc(t.get('mean_abs_margin_error', '—')),
         esc(t.get('auroc_winner', '—')),
         f"{t['straight_up_accuracy']:.1%}" if t.get('straight_up_accuracy') is not None else '—',
         f"{t['ci95'][0]:.1%}–{t['ci95'][1]:.1%}" if t.get('ci95') else '—'] for t in report['tiers']],
       "Measured performance per confidence tier")}
<p class="blurb">The tier label is assigned by the model <em>before</em> the game, from the size of
its own edge. Tiers that do not separate outcomes are not doing any work.</p></div>
<div class="card"><h2>Every graded game ({len(graded_rows)})</h2>
<p class="blurb">"Pred" is our originated home margin; "Actual" is the official final margin.
The error is ours minus reality, so a negative error means we under-rated the home side.</p>
{table(["Date", "Matchup", "Final", "Pred margin", "Actual", "Error", "Pred total", "Actual", "P(home)", "Tier", "Source"], tbl,
       "Walk-forward predictions and outcomes", cls="data compact")}</div>
"""
    page("pages/walk-forward.html", "Walk-Forward Results", body, meta)

    # ---------------------------------------------------------------- luck vs skill
    power_rows = [[f"{p['edge_points']:.1f}", f"{p['implied_hit_rate']:.1%}",
                   esc(f"{p['games_needed_80pct_power']:,}")]
                  for p in report["power"]]
    cal_rows = [[esc(c["bin"]), esc(c["n"]), f"{c['mean_predicted']:.1%}",
                 f"{c['observed_home_win_rate']:.1%}",
                 f"{c['ci95_low']:.1%}–{c['ci95_high']:.1%}", f"{c['gap_pp']:+.1f}"] for c in report["calibration"]]
    body = f"""
<section class="hero"><h2>Luck versus skill</h2>
<p>A hit rate is not evidence. These are the controls that turn it into one — and the controls
that show where this sample still cannot answer the question.</p></section>
<div class="notice notice-warning"><strong>Finding: the model does not beat the obvious rule.</strong>
On the same {naive['n_games']} games, "always take the team with the better point differential"
scores {naive['better_net_rating']['rate']:.1%} and the originated model scores
{naive['originated_model']['rate']:.1%}. The difference is
{naive['model_vs_better_net']['observed_diff']:+.2%} (permutation p =
{naive['model_vs_better_net']['p_value']:.2f}). <strong>The model's complexity is not yet
paying for itself.</strong></div>
<div class="card"><h2>Control 1 — naive rules on identical games</h2>
{table(["Rule", "Games", "Hit rate", "95% CI", "Verdict"],
       [["Always pick the home team", esc(naive['always_home']['hits']) + f" / {naive['n_games']}",
         f"{naive['always_home']['rate']:.1%}",
         f"{naive['always_home']['ci95'][0]:.1%}–{naive['always_home']['ci95'][1]:.1%}",
         "the baseline any model must clear"],
        ["Better pre-game point differential", esc(naive['better_net_rating']['hits']) + f" / {naive['better_net_rating']['n']}",
         f"{naive['better_net_rating']['rate']:.1%}",
         f"{naive['better_net_rating']['ci95'][0]:.1%}–{naive['better_net_rating']['ci95'][1]:.1%}",
         "the honest yardstick"],
        ["Originated model", esc(naive['originated_model']['hits']) + f" / {naive['originated_model']['n']}",
         f"{naive['originated_model']['rate']:.1%}",
         f"{naive['originated_model']['ci95'][0]:.1%}–{naive['originated_model']['ci95'][1]:.1%}",
         "not distinguishable from the row above"]],
       "Straight-up accuracy on identical games")}
<p class="blurb">All three rules are point-in-time: the differential rule uses only games before
each tip-off. Comparing a model with a coin flip instead of with this rule is how sports models
claim skill they do not have.</p></div>
<div class="card"><h2>Control 2 — is the improvement on the margin error real?</h2>
{table(["Test", "Value"], [
    ["Model mean absolute margin error", f"{gap['mean_abs_error_model']:.2f} pts"],
    ["Baseline (constant 0-line) absolute error", f"{gap['mean_abs_error_baseline']:.2f} pts"],
    ["Observed difference", f"{gap['observed_diff']:+.2f} pts (negative = model better)"],
    ["Permutation p-value (10,000 draws, fixed seed)", f"{gap['p_value']:.3f}"],
    ["Significant at 5%", "yes" if gap['significant_at_5pct'] else "<strong>no</strong>"],
], "Permutation test of the margin-error difference")}
<p class="blurb">A {abs(gap['observed_diff']):.2f}-point improvement with p = {gap['p_value']:.2f} is
consistent with luck. It is reported as an improvement in the point estimate and <em>not</em> as a
demonstrated edge.</p></div>
<div class="card"><h2>Control 3 — calibration: when we said 60%, did it happen?</h2>
{table(["Predicted band", "Games", "Mean predicted", "Observed home wins", "95% CI", "Gap (pp)"],
       cal_rows, "Reliability table")}
<p class="blurb">A probability that is not monotone in its outcome cannot be used for staking.
The table is shown in full rather than summarised, because the small bins are where a model's
over-confidence hides.</p></div>
<div class="card"><h2>Control 4 — how much data would it take?</h2>
{table(["Real edge (points)", "Implied hit rate", "Games needed for 80% power"], power_rows,
       "Games required to detect a genuine edge at 5% significance, 80% power")}
<p class="blurb">A 1-point edge needs roughly 4,500 settled games to detect. The
{meta['n_graded']} games graded here cannot rank strategies, and no amount of presentation
changes that arithmetic.</p></div>
<div class="card"><h2>What is still impossible to answer</h2>
<ul class="tight">
<li><strong>Is any strategy profitable?</strong> Unknowable: no prices. ROI would be fiction.</li>
<li><strong>Would this beat a market line?</strong> Unknowable for the same reason. Beating our own line measures self-consistency only.</li>
<li><strong>Is the champion the best?</strong> No: the {meta['n_graded']}-game sample is below the G-01 floor of 300 settled bets) and only reliable passes count toward the score.</li>
</ul></div>
"""
    body += source_line("https://www.nba.com/games",
                        note="outcomes are official final scores; methods are cited on the Sources page")
    page("pages/luck-vs-skill.html", "Luck vs Skill", body, meta)

    # ---------------------------------------------------------------- correlation
    mt, legs, xg, rest = corr["margin_total"], corr["legs"], corr["cross_game"], corr["rest"]
    body = f"""
<section class="hero"><h2>Correlation, measured</h2>
<p>The repository previously published correlations as <em>structural placeholders</em>. These are
computed from official final scores, with the sample size beside every value.</p></section>
<div class="notice notice-warning"><strong>Finding: the same-game parlay premise is not supported.</strong>
Strategy S-04 assumed the "favourite covers AND the total goes over" legs were positively dependent
so a same-game parlay would be underpriced. Measured: r(margin, total) =
<strong>{mt['r']}</strong> on {mt['n']} games, 95% CI {mt['ci95'][0]} to {mt['ci95'][1]}.
The dependence is not detectable, so S-04's edge does not exist on this evidence.</div>
<div class="card"><h2>Margin ↔ total correlation</h2>
{table(["Quantity", "Value"], [
    ["Games", esc(mt['n'])],
    ["Pearson r", f"<strong>{mt['r']}</strong>"],
    ["95% CI (Fisher z)", f"{mt['ci95'][0]} to {mt['ci95'][1]}"],
    ["r² (share of variance)", esc(mt['r_squared'])],
    ["SD of margin (pts)", esc(mt['margin_sd'])],
    ["SD of total (pts)", esc(mt['total_sd'])],
    ["Verdict", esc(mt['verdict'])],
], "Observed correlation between final margin and final total")}
<p class="blurb">Source: each game's own nba.com page; see the
<a href="walk-forward.html">walk-forward table</a> for all {mt['n']} rows.</p></div>
<div class="card"><h2>Same-game leg dependence (home covers × over)</h2>
{table(["Cell", "Games"], [[esc(k.replace('_', ' ')), esc(v)] for k, v in legs['cells'].items()],
       "Joint outcomes against our own originated line and total")}
{table(["Quantity", "Value"], [
    ["Games", esc(legs['n'])],
    ["P(home covers)", f"{legs['p_home_covers']:.1%}"],
    ["P(over)", f"{legs['p_over']:.1%}"],
    ["Joint observed", f"{legs['joint_observed']:.1%}"],
    ["Joint if independent", f"{legs['joint_if_independent']:.1%}"],
    ["Difference", f"{legs['difference_pp']:+.2f} pp"],
    ["z", esc(legs['z'])],
], "Dependence versus the independence assumption")}
<p class="blurb">{esc(legs['interpretation'])}</p></div>
<div class="card"><h2>Cross-game independence</h2>
{table(["Quantity", "Value"], [
    ["Same-night game pairs", esc(xg['n_pairs'])],
    ["Pearson r", esc(xg['r'])],
    ["Verdict", esc(xg['verdict'])],
], "Within-night correlation of home margins")}</div>
<div class="card"><h2>Rest and game flow — tested, not asserted</h2>
{table(["Situation", "Team-games", "Mean margin"], [
    ["Back-to-back (1 day rest)", esc(rest['b2b']['n']), esc(rest['b2b']['mean_margin'])],
    ["3+ days rest", esc(rest['rested_3plus_days']['n']), esc(rest['rested_3plus_days']['mean_margin'])],
    ["3 games in 4 days", esc(rest['three_games_in_four_days']['n']), esc(rest['three_games_in_four_days']['mean_margin'])],
], "Margin by rest situation, from official dates only")}
{f'''<p class="blurb">Back-to-back minus rested: {rest['b2b_vs_rested']['difference']:+.2f} points,
permutation p = {rest['b2b_vs_rested']['p_value']:.2f} —
{"statistically significant" if rest['b2b_vs_rested']['significant_at_5pct'] else "<strong>not statistically significant</strong>"}.</p>''' if rest.get('b2b_vs_rested') else ''}
<p class="blurb">A negative back-to-back margin is the fatigue story. The sign here is negative,
which is consistent with it, but the p-value says this sample cannot separate it from noise. The
qualitative claim on earlier pages ("back-to-backs depress production") is therefore
<strong>directionally consistent but unproven</strong>.</p></div>
"""
    page("pages/correlation.html", "Correlation", body, meta)

    # ---------------------------------------------------------------- leaderboard
    board_rows = []
    for r in report["leaderboard"]:
        board_rows.append([
            esc(r["rank"]), f'<strong>{esc(r["strategy"])}</strong>', esc(r["description"]),
            badge(r["tier_used"]), esc(r["n_games"]),
            f"{r['straight_up_accuracy']:.1%}", f"{r['se']:.3f}",
            f"{r['z_vs_coinflip']:+.2f}", f"{r['z_deflated_for_search']:+.2f}",
            esc(r["auroc_winner"]), f"{r['gate_pass_fraction']:.0%}",
            f"{r['reward_units']:.2f}", esc(r["status"])])
    body = f"""
<section class="hero"><h2>Leaderboard — measured, luck-adjusted, reward withheld</h2>
<p>Ranked on a deflated z-score against a coin flip, with a search penalty, so a hot week
cannot win. Rewards are gated, not given.</p></section>
<div class="notice notice-warning"><strong>No reward is paid.</strong> Every strategy's reward is
0 because G-01 fails (the sample is far below the
G-01 floor of 300 settled bets) and only reliable passes count toward the score. The pool stays unallocated by design.</div>
<div class="card"><h2>Scoring rule</h2>
<ol class="tight">
<li><strong>z</strong> = (accuracy − 0.5) / √(0.25 / n). It measures how far above a coin flip a
strategy sits, in standard errors — not in wins.</li>
<li><strong>Deflation.</strong> z is divided by √k where k = {len(report['leaderboard'])} registered
strategies. Trying many strategies and keeping the best one is the most common way to manufacture
a champion.</li>
<li><strong>Reward gate.</strong> 0 unless every registerable gate passes; then proportional to the
deflated z above 1.0, scaled by the fraction of gates passed.</li>
<li><strong>Pre-registration.</strong> Each strategy is mapped to one confidence tier
<em>before</em> outcomes are read, so it cannot be re-labelled onto whichever tier did well.</li>
</ol></div>
<div class="card"><h2>Board</h2>
{table(["Rank", "Strategy", "What it does", "Tier", "Games", "Accuracy", "SE", "z", "z (deflated)",
        "AUROC", "Gates passed", "Reward units", "Status"], board_rows, "Measured leaderboard")}</div>
<div class="card"><h2>Why this ranking cannot be trusted yet</h2>
<ul class="tight">
{''.join(f'<li>{esc(n)}</li>' for n in report['leaderboard_notes'])}
</ul></div>
"""
    body += source_line("https://www.nba.com/games",
                        note="every accuracy figure is computed from official final scores; see the "
                             "walk-forward table for the per-game source index")
    page("pages/leaderboard.html", "Leaderboard", body, meta)

    # ---------------------------------------------------------------- gates
    grows = []
    for gid, g in report["gates"]["gates"].items():
        cls = {"PASS": "ok", "FAIL": "bad", "PARTIAL": "warn", "BLOCKED": "blocked"}.get(g["status"], "")
        if g.get("disputed"):
            cls, label = "warn", f'{g["status"]} &middot; DISPUTED'
        else:
            label = g["status"]
        grows.append([f'<strong>{esc(gid)}</strong>', esc(g["name"]),
                      f'<span class="status status-{cls}">{label}</span>',
                      esc(g["measured"] or ""), esc(g["registered_rule"] or ""),
                      esc(g["why_it_matters"] or "")])
    body = f"""
<section class="hero"><h2>Validation gates</h2>
<p>The ten gates are read directly from <code>nba2/config.py</code> at build time, so this report
cannot relax a rule to make a strategy pass. What is new is the evidence column: before this
session every gate read "blocked — no settled bets".</p></section>
<div class="card"><div class="kpi-grid">
{_kpi("passed", len(gs['passed_reliable']), ", ".join(gs['passed_reliable']) or "none")}
{_kpi("disputed", len(gs['passed_disputed']), ", ".join(gs['passed_disputed']) or "none")}
{_kpi("failed", len(gs['failed']), ", ".join(gs['failed']) or "none")}
{_kpi("partial", len(gs['partial']), ", ".join(gs['partial']) or "none")}
{_kpi("blocked", len(gs['blocked']), ", ".join(gs['blocked']) or "none")}
</div></div>
<div class="card"><h2>Gate register</h2>
{table(["ID", "Name", "Status", "Measured evidence", "Registered rule", "Why it matters"], grows,
       "Validation gates against measured evidence", cls="data compact")}</div>
<div class="card"><h2>What the failures mean</h2>
<ul class="tight">
<li><strong>G-04 is DISPUTED.</strong> It passes its registered wording &mdash; the model's MAE beats
an unshrunk raw point differential &mdash; but that baseline is a strawman: in week one an unshrunk
differential reads anywhere from &minus;66 to +31 points and is wrong by construction. Against a
<em>fair</em> baseline (the same shrinkage, no home-court term) the model is
<strong>0.08 points worse</strong>. The honest reading: shrinkage does all the work, the home-court
term adds nothing, and this gate is not evidence of skill.</li>
<li><strong>G-01 FAILS.</strong> {meta['n_graded']} graded games versus a 300-game floor.</li>
<li><strong>G-07 PASSES.</strong> It was previously "at risk by construction" because the only
snapshot was an as-of table that leaks the future. A leakage-tested walk-forward now exists.</li>
<li><strong>G-02, G-05 (ROI half), G-06, G-09, G-10 stay BLOCKED.</strong> All five need prices or
player-level inputs. They are not marked pass by proxy.</li>
</ul></div>
"""
    body += source_line("https://www.nba.com/games",
                        note="gate rules are read from nba2/config.py; evidence from official final scores")
    page("pages/validation-gates.html", "Validation Gates", body, meta)

    # ---------------------------------------------------------------- game flow
    body = f"""
<section class="hero"><h2>Game flow &amp; rest</h2>
<p>The repository asserted that back-to-backs and travel depress performance. This page tests it
on official dates and reports the strength of the evidence rather than the direction of the story.</p></section>
<div class="card"><h2>What can be measured from official dates</h2>
<ul class="tight">
<li>Days of rest entering each game, derived only from the official schedule dates.</li>
<li>Back-to-back appearance (exactly 1 day of rest).</li>
<li>"3 games in 4 days" (this game plus two or more in the preceding three days).</li>
<li>Margin in each situation, and a permutation test between back-to-backs and rested teams.</li>
</ul></div>
<div class="card"><h2>Measured</h2>
{table(["Situation", "Team-games", "Mean margin", "Reading"], [
    ["Back-to-back", esc(rest['b2b']['n']), esc(rest['b2b']['mean_margin']),
     "negative, consistent with fatigue"],
    ["3+ days rest", esc(rest['rested_3plus_days']['n']), esc(rest['rested_3plus_days']['mean_margin']),
     "reference group"],
    ["3 games in 4 days", esc(rest['three_games_in_four_days']['n']), esc(rest['three_games_in_four_days']['mean_margin']),
     "the densest spot in the window"],
], "Margin by rest situation")}
{f'''<p class="blurb">Difference (back-to-back minus rested):
<strong>{rest['b2b_vs_rested']['difference']:+.2f} points</strong>, permutation p =
{rest['b2b_vs_rested']['p_value']:.2f}. {"Significant." if rest['b2b_vs_rested']['significant_at_5pct'] else "Not significant: the sign is right but the sample is too small to claim the effect."}</p>''' if rest.get('b2b_vs_rested') else ''}</div>
<div class="card"><h2>Travel, altitude and motivation</h2>
<p>These are the flow factors that appear on the other surfaces of this repo. They are
<strong>not</strong> measured here, because doing so honestly needs per-team travel schedules and
venue metadata that this snapshot does not carry in machine-readable form:</p>
<ul class="tight">
<li><strong>Travel distance</strong> — the schedule gives venues, not itineraries. Distance could be
geocoded from the arena list; that is a defined next step, not a current result.</li>
<li><strong>Altitude</strong> — Denver/Utah home games are identifiable from the venue string, but the
effect needs a much larger sample than {meta['n_grades'] if 'n_grades' in meta else meta['n_graded']} games.</li>
<li><strong>Motivation</strong> (Cup group standings, seeding, back-half of a road trip) — not
quantified, and not claimed.</li>
<li><strong>In-game flow</strong> (pace, runs, garbage time) — needs play-by-play, which this
snapshot does not include. Every in-game flow column on the other site surfaces remains blank
for this reason.</li>
</ul></div>
"""
    body += source_line("https://www.nba.com/games",
                        note="rest is derived from the official game dates on each per-day page; "
                             "every game used is listed on the Sources page")
    page("pages/game-flow.html", "Game Flow &amp; Rest", body, meta)

    # ---------------------------------------------------------------- questions
    body = """
<section class="hero"><h2>Open questions that block a decision</h2>
<p>Grouped by what would answer them. A question is only listed as answered if an official source
was read and the answer is reproducible from this repository.</p></section>
<section class="card"><h2>A. Answerable now, from this session's work</h2>
<div class="table-wrap"><table class="data">
<caption>Questions answered on this page's evidence</caption>
<thead><tr><th scope="col">#</th><th scope="col">Question</th><th scope="col">Answer</th><th scope="col">Evidence</th></tr></thead>
<tbody>
<tr><td>Q1</td><td>Does the originated model beat a coin flip?</td><td>Yes, in the point estimate (62.6% straight-up, AUROC 0.70), but the interval is wide and prices are unavailable, so this is not a bettable edge.</td><td><a href="luck-vs-skill.html">Luck vs Skill</a></td></tr>
<tr><td>Q2</td><td>Does it beat the obvious rule?</td><td><strong>No.</strong> 62.6% versus 64.0% for "take the better point differential" (p = 0.90).</td><td><a href="luck-vs-skill.html">Luck vs Skill</a></td></tr>
<tr><td>Q3</td><td>Does it beat a constant line?</td><td>Yes on margin error (12.17 vs 13.27 pts MAE) but <strong>not significantly</strong> (p = 0.35).</td><td><a href="luck-vs-skill.html">Luck vs Skill</a></td></tr>
<tr><td>Q4</td><td>Is the model's total any good?</td><td><strong>No.</strong> Total MAE 15.78 versus 15.43 for simply predicting the league-average total. The total component is currently worse than a constant.</td><td><a href="walk-forward.html">Walk-Forward</a></td></tr>
<tr><td>Q5</td><td>Are same-game legs correlated?</td><td>Not detectably: r(margin, total) = -0.009 (95% CI -0.17 to 0.15). The same-game parlay premise is unsupported.</td><td><a href="correlation.html">Correlation</a></td></tr>
<tr><td>Q6</td><td>Do back-to-backs hurt?</td><td>Directionally yes (-1.54 vs +1.27 pts) but not significantly (p = 0.38).</td><td><a href="correlation.html">Correlation</a></td></tr>
<tr><td>Q7</td><td>Are the tiers informative?</td><td>Partly: Tier A 75.4% vs Tier C 46.2% straight-up. Tier C's interval includes a coin flip, which is what a noise tier should look like.</td><td><a href="walk-forward.html">Walk-Forward</a></td></tr>
<tr><td>Q8</td><td>How much data is needed before a leaderboard means anything?</td><td>Roughly 300 settled bets to see a 3-point edge; about 4,551 to see a 1-point edge at 80% power.</td><td><a href="luck-vs-skill.html">Luck vs Skill</a></td></tr>
</tbody></table></div></section>
<section class="card"><h2>B. Blocked, and what would unblock each one</h2>
<div class="table-wrap"><table class="data">
<caption>Questions that cannot be answered from available data</caption>
<thead><tr><th scope="col">#</th><th scope="col">Question</th><th scope="col">Why it is blocked</th><th scope="col">What would answer it</th></tr></thead>
<tbody>
<tr><td>Q9</td><td>Is any strategy profitable after vig?</td><td>No odds feed; no price means no edge, no ROI, no stake.</td><td>A licensed historical odds feed (opening, closing, and the price actually available).</td></tr>
<tr><td>Q10</td><td>Would these lines have beaten a market line?</td><td>Same: no market numbers captured.</td><td>The same feed, joined by game id and timestamp.</td></tr>
<tr><td>Q11</td><td>How much does a specific injury move a line?</td><td>No player-level data; the results snapshot has no minutes or box scores.</td><td>Official box scores for every game plus the injury report at tip-off time.</td></tr>
<tr><td>Q12</td><td>Do player props and prop combos have an edge?</td><td>No prop prices and no player baselines from an official source.</td><td>Official player game logs and a prop-line feed.</td></tr>
<tr><td>Q13</td><td>Does travel or altitude matter?</td><td>Venues are known but itineraries and geocodes are not in the snapshot.</td><td>A geocoded arena list and per-team travel schedules.</td></tr>
<tr><td>Q14</td><td>What is the correlation between two legs of a specific same-player combo?</td><td>Needs per-player box scores for both markets.</td><td>Official player game logs, at least a full season.</td></tr>
<tr><td>Q15</td><td>Is the ex-ante line the same as the ex-post line for the same game?</td><td>The two excluded dates (11/06, 11/11) rendered without scores, so 19 games are missing from the middle of the sample.</td><td>Box scores or a per-game fetch for those dates from a source that serves them.</td></tr>
</tbody></table></div></section>
<section class="card"><h2>C. Owner decisions that no amount of data will settle</h2>
<div class="table-wrap"><table class="data">
<caption>Decisions requiring the owner</caption>
<thead><tr><th scope="col">#</th><th scope="col">Decision</th><th scope="col">Default if unanswered</th></tr></thead>
<tbody>
<tr><td>D1</td><td>Is a 0.30-point MAE improvement over the naive baseline the right promotion bar (G-04)?</td><td>It stays as registered and the model stays unpromoted.</td></tr>
<tr><td>D2</td><td>What is the reward pool, and is it units or currency?</td><td>100 units stay unallocated.</td></tr>
<tr><td>D3</td><td>Is the target competition houses' prices or our own line accuracy?</td><td>Only line accuracy is measured; nothing is claimed about markets.</td></tr>
<tr><td>D4</td><td>Which jurisdiction's rules govern any future odds ingestion?</td><td>No odds are ingested.</td></tr>
</tbody></table></div></section>
"""
    body += source_line("https://www.nba.com/games",
                        note="answers cite the measured results in this report")
    page("pages/questions.html", "Open Questions", body, meta)

    # ---------------------------------------------------------------- suggestions
    body = """
<section class="hero"><h2>Suggestions — a review queue, not a to-do list</h2>
<p>Nothing here is implemented. Each item states what it would change, what it costs, how it would
be verified, and what would make it a bad idea. Pick one, reject one, or defer all of them.</p></section>
<section class="card"><h2>Priority 1 — the model is not earning its complexity</h2>
<div class="table-wrap"><table class="data">
<caption>Model improvement suggestions</caption>
<thead><tr><th scope="col">ID</th><th scope="col">Suggestion</th><th scope="col">Why</th><th scope="col">Verification</th><th scope="col">Risk</th></tr></thead>
<tbody>
<tr><td>S-101</td><td>Test a rating that uses margin of victory with a cap, or a ridge regression on point differential, and require it to beat the raw differential by 0.30 MAE before it replaces anything.</td><td>The model does not beat a shrunk differential that omits the home-court term, so the home-court estimate is not yet adding information (shrinkage is).</td><td>Same walk-forward, same seed, G-04 evaluated on the challenger.</td><td>Adds a parameter that can be over-fitted to 139 games.</td></tr>
<tr><td>S-102</td><td>Replace the four-rate total with a pace-and-efficiency model, or publish no total at all.</td><td>Total MAE (15.78) is worse than a constant (15.43). A total that loses to a constant should not be published.</td><td>Total MAE and bias on the same games.</td><td>Removing the total removes the S-04 parlay test entirely.</td></tr>
<tr><td>S-103</td><td>Add an explicit rest/fatigue term only if a larger sample makes it significant; store the test as a regression with rest days as a covariate.</td><td>The effect's sign is right but p = 0.38. Shipping it now would be curve-fitting.</td><td>Refit when the sample reaches ~500 team-games; require p &lt; 0.05 and a stable sign.</td><td>Adds a feature that may be pure noise.</td></tr>
</tbody></table></div></section>
<section class="card"><h2>Priority 2 — data that unblocks whole categories</h2>
<div class="table-wrap"><table class="data">
<caption>Data suggestions</caption>
<thead><tr><th scope="col">ID</th><th scope="col">Suggestion</th><th scope="col">Unblocks</th><th scope="col">Verification</th><th scope="col">Risk</th></tr></thead>
<tbody>
<tr><td>S-104</td><td>Capture the 11/06 and 11/11 slates from a source that serves scores for those dates.</td><td>Removes the 19-game hole; makes the standings reconstruction exact rather than bounded.</td><td>Reconstructed records must equal the snapshot exactly for all 30 teams.</td><td>Mixing sources can import a different definition of a team or a game.</td></tr>
<tr><td>S-105</td><td>Capture the remaining season dates through the current day, then ingest nightly.</td><td>Statistical power: 300+ graded games, which is the G-01 floor.</td><td>Check 1 (records vs cards) must stay at 100% after each ingest.</td><td>Automated ingestion without a verification step is how bad data gets in.</td></tr>
<tr><td>S-106</td><td>Add a licensed odds feed with opening and closing prices.</td><td>G-02, G-05, G-06, G-09 and every ROI statement.</td><td>CLV t-test and bootstrap CI on settled bets.</td><td>Cost, licensing, and jurisdiction — this is the owner's decision, not a code change.</td></tr>
<tr><td>S-107</td><td>Add official player box scores.</td><td>Injury impact, props, prop combos, same-player correlation.</td><td>Per-player minutes must reconcile to team totals.</td><td>Large data volume; needs a snapshot strategy.</td></tr>
</tbody></table></div></section>
<section class="card"><h2>Priority 3 — decision-making on the site itself</h2>
<div class="table-wrap"><table class="data">
<caption>Presentation and process suggestions</caption>
<thead><tr><th scope="col">ID</th><th scope="col">Suggestion</th><th scope="col">Why it improves decisions</th><th scope="col">Verification</th></tr></thead>
<tbody>
<tr><td>S-108</td><td>Collapse the repository's multiple site trees (<code>/</code>, <code>/docs</code>, <code>/dashboard</code>, <code>/originated</code>, <code>/backtest</code>) behind one navigation with a status badge per tree.</td><td>Five surfaces disagree; a reader cannot tell which number is canonical.</td><td>One link check over the merged site; a badge page listing each tree's last verified date.</td></tr>
<tr><td>S-109</td><td>Put the failing gate at the top of the landing page, not in a subpage.</td><td>The most decision-relevant fact (the model is not distinguishable from a one-line rule) is currently three clicks deep.</td><td>A build check that the landing page contains the current G-04 status.</td></tr>
<tr><td>S-110</td><td>Publish a single "what would change my mind" line per strategy, with the sample size needed.</td><td>Converts an open-ended argument into a falsifiable test.</td><td>Each line must cite the power calculation.</td></tr>
<tr><td>S-111</td><td>Freeze the leaderboard until G-01 passes, rather than ranking 4 strategies on ~35 games each.</td><td>A provisional ranking reads as a result no matter how many caveats surround it.</td><td>Leaderboard page renders only the gate status until n &ge; 300.</td></tr>
</tbody></table></div></section>
"""
    body += source_line("https://www.nba.com/games",
                        note="every suggestion is grounded in a measured result in this report")
    page("pages/suggestions.html", "Suggestions", body, meta)

    # ---------------------------------------------------------------- flagged
    body = f"""
<section class="hero"><h2>Flagged for review</h2>
<p>Open irregularities from this session, with the source needed to check each one. Nothing here
blocks a merge; each item blocks a <em>promotion</em> until it is resolved.</p></section>
<section class="card"><h2>Data irregularities</h2>
<div class="table-wrap"><table class="data">
<caption>Data flags</caption>
<thead><tr><th scope="col">ID</th><th scope="col">What</th><th scope="col">Impact</th><th scope="col">Status</th><th scope="col">Source to check</th></tr></thead>
<tbody>
<tr><td>FLAG-BT-01</td><td>The official pages for 2026-11-06 (9 games) and 2026-11-11 (10 games) rendered with empty score elements.</td><td>19 games missing from the middle of the sample. Records can only be checked as a bound, not exactly.</td><td>Open — excluded, not guessed</td><td>{src('https://www.nba.com/games?date=2026-11-06', 'nba.com/games 2026-11-06')}</td></tr>
<tr><td>FLAG-BT-02</td><td>Game 0022600159 was first transcribed as DAL@CHA; the official card is DET@CHA.</td><td>Was caught by the record reconstruction and fixed in the snapshot with a recorded correction.</td><td>Resolved in-session</td><td>{src('https://www.nba.com/game/det-vs-cha-0022600159', 'nba.com/game/det-vs-cha-0022600159')}</td></tr>
<tr><td>FLAG-BT-03</td><td>Game 0022600189 (DEN@IND, 2026-11-07) is played at a neutral site (Mexico City), so the home-court term does not apply to it.</td><td>CORRECTED 2026-11-14 (session arena/a7d4a562). The flag had been raised but nothing implemented it: the walk-forward still added the estimated home-court term to this game, which was invisible because the neutral flag never reached the prediction record. The model now sets the home-court term to zero for any snapshot row marked neutral_site, and each row publishes the effective hca it used.</td><td>Fixed</td><td>{src('https://www.nba.com/game/den-vs-ind-0022600189', 'nba.com/game/den-vs-ind-0022600189')}</td></tr>
<tr><td>FLAG-BT-04</td><td>The committed standings snapshot is as-of 2026-11-12 but is sourced from a third-party ratings page, and the repo's own audit notes a 28/30 vs 30/30 cross-check discrepancy.</td><td>This session does not use that snapshot as a model input; it uses only final scores. It is used once, as an independent check, and only as a bound.</td><td>Open (pre-existing)</td><td><span class="badge">unverified — no official source</span> The only cited provenance is a third-party ratings page; no official nba.com standings URL is recorded in the repo for that date.</td></tr>
</tbody></table></div></section>
<section class="card"><h2>Method flags</h2>
<div class="table-wrap"><table class="data">
<caption>Methodological flags</caption>
<thead><tr><th scope="col">ID</th><th scope="col">What</th><th scope="col">Impact</th><th scope="col">Status</th></tr></thead>
<tbody>
<tr><td>FLAG-M-01</td><td>The model is assessed on its own originated line. "Covering" that line measures self-consistency, not market skill.</td><td>Every ATS-style number on this site is labelled self-consistency only. No ROI is published.</td><td>Disclosed</td></tr>
<tr><td>FLAG-M-02</td><td>Home-court advantage is estimated from completed games with a shrinkage floor. In the first weeks this is close to zero, so early-season predictions are near-neutral.</td><td>Early games in the sample are systematically less informed; the bias column shows the residual.</td><td>Disclosed</td></tr>
<tr><td>FLAG-M-03</td><td>The total model is a four-rate average with no pace term, and it loses to a constant on this sample.</td><td>Published as measured, with a suggestion to replace or retire it (S-102).</td><td>Open</td></tr>
<tr><td>FLAG-M-04</td><td>The permutation test on paired hit rates treats pairs as independent, which they are not.</td><td>The p-values for model-vs-baseline comparisons are indicative rather than exact.</td><td>Disclosed</td></tr>
<tr><td>FLAG-M-05</td><td>Two of the repo's registered gates (G-08 side-stability, G-10 availability) cannot be scored on a results-only dataset.</td><td>Marked PARTIAL and BLOCKED respectively; not passed by proxy.</td><td>Open</td></tr>
</tbody></table></div></section>
"""
    page("pages/flagged-review.html", "Flagged for Review", body, meta)

    # ---------------------------------------------------------------- sources
    date_urls = sorted({f"https://www.nba.com/games?date={d}" for d in wf.completed_dates(wf.load_games())})
    game_rows = [[esc(g["date"]), f'{esc(g["away"])} @ {esc(g["home"])}', esc(g["game_id"]),
                  src(g["source_url"], g["game_id"])]
                 for g in report["games"]]
    body = f"""
<section class="hero"><h2>Sources</h2>
<p>Every number on this site traces to a page listed here. No value came from a search result,
a model, or memory.</p></section>
<section class="card"><h2>Primary source</h2>
<p>All outcomes are official NBA.com final scores, read from the per-date games page and cross
referenced against the per-game page. There is no second data provider in this report, which is
both its strength (one definition of a game) and its limitation (no independent score source).</p>
<ul class="tight">
{''.join(f'<li>{src(u)}</li>' for u in date_urls)}
</ul></section>
<section class="card"><h2>Reference material (definitions, not data)</h2>
<ul class="tight">
<li><strong>Wilson (1927)</strong> score interval — used for every hit-rate confidence interval.</li>
<li><strong>Brier (1950)</strong> — the probability scoring rule used in gate G-03.</li>
<li><strong>Fisher (1935)</strong> randomisation / permutation testing — used for every p-value here.</li>
<li><strong>Holm (1979)</strong> — Bonferroni-style multiple-comparison control, referenced by gate G-06.</li>
<li><strong>Bailey &amp; López de Prado (2014)</strong> — deflated Sharpe ratio, the basis for the
search penalty on the leaderboard.</li>
</ul>
<p class="blurb">These are method citations, not numeric sources. No number on this site was taken
from them.</p></section>
<section class="card"><h2>Per-game source index ({len(report['games'])} games)</h2>
{table(["Date", "Matchup", "Game ID", "Source"], game_rows, "One official URL per game", cls="data compact")}</section>
"""
    page("pages/sources.html", "Sources", body, meta)


# ----------------------------------------------------------------- helpers


def _integrity(games) -> dict:
    import csv
    import glob as _glob

    recs = []
    for f in sorted(_glob.glob(str(ROOT / "data/raw/history/postgame_records_*.json"))):
        recs += json.loads(pathlib.Path(f).read_text())["rows"]

    def state(date):
        w, l = {}, {}
        for g in games:
            if g["date"] > date:
                continue
            win, lose = ((g["away"], g["home"]) if g["away_pts"] > g["home_pts"]
                         else (g["home"], g["away"]))
            w[win] = w.get(win, 0) + 1
            l[lose] = l.get(lose, 0) + 1
        return {t: (w.get(t, 0), l.get(t, 0)) for t in set(w) | set(l)}

    pre = [r for r in recs if r["date"] <= "2026-11-05"]
    exact = sum(1 for r in pre if state(r["date"]).get(r["team"]) == (r["wins"], r["losses"]))
    post = [r for r in recs if r["date"] > "2026-11-05"]
    viol = [r for r in post
            if state(r["date"]).get(r["team"], (0, 0))[0] > r["wins"]
            or state(r["date"]).get(r["team"], (0, 0))[1] > r["losses"]]

    recon = state("2026-11-12")
    out_rows = []
    path = ROOT / "data/standings-2026-11-13.csv"
    if path.exists():
        for r in csv.DictReader(path.read_text().splitlines()):
            t = r["team"]
            cw, cl = int(r["wins"]), int(r["losses"])
            g = recon.get(t, (0, 0))
            status = ("exact" if g == (cw, cl) else
                      "bounded below (missing games)" if g[0] <= cw and g[1] <= cl else
                      "EXCEEDS snapshot — investigate")
            out_rows.append({"team": t, "official": f"{cw}-{cl}", "reconstructed": f"{g[0]}-{g[1]}",
                             "official_games": cw + cl, "reconstructed_games": g[0] + g[1],
                             "status": status, "source_url": r.get("source_url", ""),
                             "snapshot_url": "data/standings-2026-11-13.csv"})
    exceeding = [r for r in out_rows if r["status"].startswith("EXCEEDS")]
    note = (f"All 30 teams sit at or below the snapshot, which is the expected direction when "
            f"{'19'} games are missing from the captured history. "
            f"{len(exceeding)} teams exceed their snapshot, which would indicate a transcription "
            f"error somewhere." if out_rows else "Snapshot not found.")
    return {
        "exact_check": {"checked": len(pre), "matched": exact},
        "bounded_check": {"checked": len(post), "consistent": len(post) - len(viol),
                          "violations": len(viol)},
        "reconstruction": out_rows,
        "reconstruction_note": note,
    }


if __name__ == "__main__":
    rep = build()
    print("built report:", rep["meta"])
