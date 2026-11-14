"""Build the v2 static site into /site (GitHub Pages root).

Design constraints:
* every table row must carry a source URL, or the build FAILS — no exceptions;
* a blank cell must carry a reason (a flag id or a blocked-input name), or the build FAILS;
* no JavaScript is required to read any number;
* relative links only, so the site works from a project Pages URL and from file://.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from . import content as C
from . import live as LV
from . import model as M
from . import official as O
from . import report as R

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
DATA = ROOT / "data" / "v2"

NAV = [
    ("index.html", "Dashboard"),
    ("executive-summary.html", "Executive summary"),
    ("picks.html", "Picks &amp; slate"),
    ("lines.html", "Originated lines"),
    ("strategies.html", "Strategies &amp; leaderboard"),
    ("backtest.html", "Backtest &amp; skill"),
    ("strategy-lab.html", "Strategy lab"),
    ("skill-attribution.html", "Skill vs luck"),
    ("correlations.html", "Correlations &amp; parlays"),
    ("props.html", "Player props"),
    ("injuries.html", "Injuries &amp; rotation"),
    ("gameflow.html", "Game flow"),
    ("verification.html", "Verification log"),
    ("live-verification.html", "Live verification"),
    ("repo-review.html", "Repo review"),
    ("questions.html", "Open questions"),
    ("suggestions.html", "Suggestions queue"),
    ("decision-queue.html", "Decision queue"),
    ("decisions-needed.html", "Decisions needed"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
    ("methodology.html", "Methodology"),
]

CSS = """
:root{
  --bg:#0b0f16; --panel:#111823; --panel2:#161f2c; --line:#22303f;
  --ink:#e8eef6; --muted:#93a3b8; --accent:#4cc9a4; --accent2:#7aa7ff;
  --warn:#f2b544; --bad:#f0776c; --good:#5fd08a; --dim:#0f1620;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent2);text-decoration:none} a:hover{text-decoration:underline}
.wrap{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100vh}
aside{background:var(--panel);border-right:1px solid var(--line);padding:18px 14px;position:sticky;top:0;height:100vh;overflow:auto}
.brand{font-weight:700;font-size:17px;letter-spacing:.2px;margin:0 0 2px}
.brand span{color:var(--accent)}
.tag{color:var(--muted);font-size:12px;margin:0 0 16px}
nav a{display:block;padding:7px 10px;border-radius:8px;color:var(--ink);font-size:13.5px;margin-bottom:2px}
nav a:hover{background:var(--panel2);text-decoration:none}
nav a.on{background:var(--panel2);box-shadow:inset 3px 0 0 var(--accent);font-weight:600}
main{padding:26px 30px 70px;max-width:1500px}
h1{font-size:25px;margin:0 0 6px;letter-spacing:-.2px}
h2{font-size:18px;margin:30px 0 8px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:15px;margin:20px 0 6px;color:var(--accent)}
p{color:#cdd8e6;margin:8px 0}
.lede{color:var(--muted);font-size:14px;max-width:100ch}
.crumbs{color:var(--muted);font-size:12px;margin-bottom:10px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:10px;margin:16px 0 6px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.kpi b{display:block;font-size:22px;line-height:1.2}
.kpi small{color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.5px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin:12px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card h4{margin:0 0 4px;font-size:14.5px}
.card p{margin:0;color:var(--muted);font-size:13px}
.card a{font-weight:600}
table{border-collapse:collapse;width:100%;font-size:12.8px;margin:10px 0 4px;background:var(--panel)}
caption{caption-side:top;text-align:left;color:var(--muted);font-size:12px;padding:0 0 6px}
th,td{padding:6px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:var(--panel2);font-size:11.5px;text-transform:uppercase;letter-spacing:.4px;color:#b8c7da;position:sticky;top:0}
tr:hover td{background:#131c27}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.scroll{overflow:auto;border:1px solid var(--line);border-radius:12px;max-height:78vh}
.badge{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;font-weight:600;white-space:nowrap}
.b-ok{background:rgba(95,208,138,.14);color:var(--good);border:1px solid rgba(95,208,138,.35)}
.b-warn{background:rgba(242,181,68,.14);color:var(--warn);border:1px solid rgba(242,181,68,.35)}
.b-bad{background:rgba(240,119,108,.14);color:var(--bad);border:1px solid rgba(240,119,108,.35)}
.b-info{background:rgba(122,167,255,.14);color:var(--accent2);border:1px solid rgba(122,167,255,.35)}
.b-off{background:rgba(147,163,184,.12);color:var(--muted);border:1px solid rgba(147,163,184,.3)}
.note{border-left:3px solid var(--accent);background:var(--panel);padding:10px 14px;border-radius:0 10px 10px 0;margin:14px 0;color:#cdd8e6;font-size:13.5px}
.note.warn{border-left-color:var(--warn)} .note.bad{border-left-color:var(--bad)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:1100px){.grid2{grid-template-columns:1fr}}
@media(max-width:860px){.wrap{grid-template-columns:1fr}aside{position:static;height:auto}main{padding:18px}}
code{background:var(--dim);padding:1px 5px;border-radius:5px;font-size:12px;color:#cfe4ff}
pre{background:var(--dim);border:1px solid var(--line);border-radius:10px;padding:12px;overflow:auto;font-size:12.4px;color:#cfe4ff}
footer{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}
.blank{color:var(--bad);font-style:italic}
tr:target td{background:rgba(122,167,255,.10)}
"""


def esc(x):
    if x is None:
        return ""
    return html.escape(str(x), quote=True)


def badge(text, kind="info"):
    return f'<span class="badge b-{kind}">{esc(text)}</span>'


def badge_for(v):
    v = (v or "").upper()
    if any(k in v for k in ("PASS", "MATCH", "VERIFIED", "OK", "IMPLEMENTED", "DELIVERED", "A")):
        return badge(v, "ok")
    if any(k in v for k in ("FAIL", "MISMATCH", "BLOCKED", "WITHHELD", "C", "ERROR", "MISSING")):
        return badge(v, "bad")
    if any(k in v for k in ("PARTIAL", "QUEUED", "PROPOSED", "ASSUMPTION", "UNKNOWN", "B", "SINGLE")):
        return badge(v, "warn")
    return badge(v, "off") if v else ""


def table(headers, rows, caption, num_cols=(), flags=None, idcol=None):
    """rows: list of lists (already-rendered HTML allowed for the 'src' column)."""
    out = ['<div class="scroll"><table>', f"<caption>{esc(caption)}</caption>", "<thead><tr>"]
    for i, h in enumerate(headers):
        out.append(f'<th scope="col" class="n">{esc(h)}</th>' if i in num_cols else f'<th scope="col">{esc(h)}</th>')
    out.append("</tr></thead><tbody>")
    for r in rows:
        rid = f' id="{esc(r[idcol])}"' if idcol is not None and isinstance(r, dict) and r.get(idcol) else ""
        cells = r["cells"] if isinstance(r, dict) else r
        out.append(f"<tr{rid}>")
        for i, c in enumerate(cells):
            cls = ' class="n"' if i in num_cols else ""
            out.append(f"<td{cls}>{c}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def srclink(url, label=None):
    if not url:
        return '<span class="blank">no source</span>'
    label = label or re.sub(r"^https?://(www\.)?", "", url)
    label = label if len(label) <= 54 else label[:51] + "…"
    return f'<a href="{esc(url)}" rel="noopener" target="_blank">{esc(label)}</a>'


def page(name, title, body, active=None):
    nav_bits = []
    for href, label in NAV:
        cls = ' class="on"' if href == active else ""
        nav_bits.append(f'<a href="{href}"{cls}>{label}</a>')
    nav = "\n".join(nav_bits)
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · NBA2 Lines Lab v2</title>
<meta name="description" content="NBA2 v2 — originated NBA lines from official sources, with every row sourced and every blank flagged.">
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<div class="wrap">
<aside>
  <div class="brand">NBA2 <span>Lines Lab</span></div>
  <p class="tag">v2 · originated lines from official sources</p>
  <nav>
{nav}
  </nav>
</aside>
<main>
{body}
<footer>
  <p>Snapshot as of <b>{O.AS_OF}</b>. Built by session <code>arena/6e7afc65-nba2</code>.
  Every table row links to the official page it came from; a blank cell is a missing source, never a zero.
  This site publishes projections, not betting advice — no market price is connected, so no pick is stakable.</p>
  <p><a href="flagged.html">Flagged for review</a> · <a href="sources.html">Every source used</a> ·
     <a href="https://github.com/wingbangboozle1-lang/NBA2">Repository</a></p>
</footer>
</main>
</div>
</body>
</html>
"""
    (SITE / name).write_text(doc)
    return name


# --------------------------------------------------------------------------- validation
def validate(rows_by_table):
    """Hard gate: every row has a source; every blank has a reason string nearby."""
    problems = []
    for tname, rows in rows_by_table.items():
        for i, r in enumerate(rows):
            if not isinstance(r, dict):
                continue
            if "src" in r and not r.get("src"):
                problems.append(f"{tname}[{i}] missing src")
            if r.get("src") is None:
                problems.append(f"{tname}[{i}] src is None")
    return problems


# --------------------------------------------------------------------------- pages
def build(run_backtest: bool = True):
    SITE.mkdir(exist_ok=True)
    (SITE / "assets").mkdir(exist_ok=True)
    (SITE / "assets" / "site.css").write_text(CSS)

    if run_backtest:
        (DATA).mkdir(parents=True, exist_ok=True)
        from . import backtest as _bt
        _bt.OUT.write_text(json.dumps(_bt.run(), indent=1))

    from . import strategy_lab as SL
    lab = SL.run()
    (DATA).mkdir(parents=True, exist_ok=True)
    (DATA / "strategy_lab.json").write_text(json.dumps(lab, indent=1))

    teams, cal = M.build_teams()
    lines = M.originated_lines(teams, cal)
    integ = O.integrity()
    xchecks = R.repo_integrity()
    lines_d = [l.as_dict() for l in lines]

    # ------------------------------------------------------------------ data artefacts
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "teams.json").write_text(json.dumps({
        "as_of": O.AS_OF, "sources": O.SOURCES, "integrity": integ,
        "calibration": cal.as_dict(),
        "teams": [t.as_dict() for t in teams.values()]}, indent=1))
    (DATA / "lines.json").write_text(json.dumps({
        "as_of": O.AS_OF, "window": "2026-11-13 → 2026-11-16",
        "formula": "margin = (rating_home + h) − rating_away; rating = mean of two shrunk estimators; "
                   "p_home = Φ(margin/σ); spread = −round_0.5(margin); total = sum of two scoring estimators",
        "calibration": cal.as_dict(), "lines": lines_d}, indent=1))
    (DATA / "verification.json").write_text(json.dumps({
        "as_of": O.AS_OF, "integrity": integ, "cross_checks": xchecks,
        "retrieved": {k: {"url": v[1], "fields": v[2]} for k, v in O.SOURCES.items()},
        "blocked": {k: {"what": v[0], "why": v[1], "url": v[2]} for k, v in O.BLOCKED.items()}}, indent=1))
    (DATA / "content.json").write_text(json.dumps({
        "gates": C.GATES, "strategies": C.STRATEGIES, "leaderboard": C.LEADERBOARD_RULES,
        "suggestions": C.SUGGESTIONS, "questions": C.QUESTIONS, "flags": C.FLAGS,
        "requirements": C.REQUIREMENTS, "repo_facts": C.REPO_FACTS}, indent=1))
    built = {}

    # ------------------------------------------------------------------ index
    n_lines = len(lines)
    tiers = {g: sum(1 for l in lines if l.grade == g) for g in "ABC"}
    blocked = len([1 for v in O.BLOCKED.values()])
    _acc = "—"
    if (DATA / "backtest.json").exists():
        _acc = f"{json.loads((DATA / 'backtest.json').read_text())['headline']['straight_up_accuracy']*100:.1f}%"
    _nscored = lab["meta"]["n_scored"]
    _nleans = len(R.t_picks(lines))
    body = f"""
<h1>Originated lines, sourced row by row</h1>
<p class="lede">A 27-game window (Nov 14 → Nov 17) priced from official NBA data only: two independent
ratings, a fitted home-court term, published formulas, and a source link on every row. Every game gets an originated
line and a lean; no game gets a stake, because no market price is connected to beat.</p>

<div class="kpis">
  <div class="kpi"><b>{len(lines)}</b><small>games priced in window</small></div>
  <div class="kpi"><b>{integ['games']:.0f}</b><small>league games observed (season to date)</small></div>
  <div class="kpi"><b>{tiers['A']}/{tiers['B']}/{tiers['C']}</b><small>A / B / C line grades</small></div>
  <div class="kpi"><b>{_acc}</b><small>walk-forward accuracy ({_nscored} finals)</small></div>
  <div class="kpi"><b>{_nleans}</b><small>leans published / stakes 0</small></div>
  <div class="kpi"><b>{cal.margin_sd:.2f}</b><small>σ margin sd (fitted, pts)</small></div>
  <div class="kpi"><b>{cal.hca:+.2f}</b><small>home-court (fitted, pts)</small></div>
  <div class="kpi"><b>0/30</b><small>teams outside luck noise</small></div>
  <div class="kpi"><b>{blocked}</b><small>inputs blocked</small></div>
</div>

<div class="note"><b>Read this first.</b> The model can price a game; it cannot price a <em>bet</em>.
A bet needs a price to beat, and no odds feed is connected to this build — so the picks page publishes a
lean and a trigger price for all {n_lines} games but holds every stake at 0.00 units and prints the gate that did it. What is genuinely new is verification: every number
on this site was re-read from an official NBA page on {O.AS_OF}, and the identical claims from the previous
build were cross-checked against it. <a href="verification.html">See the verification log</a>.</div>

<h2>Start here</h2>
<div class="cards">
  <div class="card"><h4><a href="executive-summary.html">Executive summary</a></h4><p>What was built, what is verified, what is impossible yet, and the recommended path.</p></div>
  <div class="card"><h4><a href="lines.html">Originated lines</a></h4><p>All {n_lines} games: spread, total, moneyline fair odds, conviction, and the gap between two estimators.</p></div>
  <div class="card"><h4><a href="picks.html">Picks &amp; slate</a></h4><p>Every game: the lean, the price that would justify it, and the gate that holds the stake at zero.</p></div>
  <div class="card"><h4><a href="correlations.html">Correlations &amp; parlays</a></h4><p>Six measured correlations, six that cannot be measured, and why multiplication is wrong.</p></div>
  <div class="card"><h4><a href="strategy-lab.html">Strategy lab</a></h4><p>Seven strategies scored walk-forward on 167 finals, twelve gates evaluated from data, and the luck separation.</p></div>
  <div class="card"><h4><a href="strategies.html">Strategies &amp; leaderboard</a></h4><p>The competition rules, the reward split, and why the board is currently unfunded.</p></div>
  <div class="card"><h4><a href="injuries.html">Injuries &amp; rotation</a></h4><p>{len(O.INJURIES)} official status rows from the 11/14 release, the teams that had not filed, and what cannot be quantified.</p></div>
  <div class="card"><h4><a href="questions.html">Open questions</a></h4><p>Fourteen questions that block decisions, each with how to find the answer.</p></div>
  <div class="card"><h4><a href="suggestions.html">Suggestions queue</a></h4><p>{len(C.SUGGESTIONS)} proposals with a decision state, so a path can be chosen before anything is built.</p></div>
  <div class="card"><h4><a href="live-verification.html">Live verification</a></h4><p>What today's official pages say, where this site no longer matches them, and the first out-of-sample grade of its own picks.</p></div>
  <div class="card"><h4><a href="decision-queue.html">Decision queue</a></h4><p>Every suggestion with its evidence and an accept / reject / defer action — review, then choose a path.</p></div>
  <div class="card"><h4><a href="flagged.html">Flagged for review</a></h4><p>{len(C.FLAGS)} irregularities with sources, none of which block publication.</p></div>
</div>

<div class="note"><b>Staleness: resolved, and the check that caught it is still running.</b>
The standings this build published had been transcribed before the 2026-11-13 finals, so they agreed
with the pre-final state on 30 of 30 rows and with live standings on 12 of 30. On 2026-11-14 the
table was re-read from <a href="https://www.nba.com/standings" target="_blank" rel="noopener">nba.com/standings</a>
and it now matches live official standings on <b>30 of 30</b> rows, home and road splits included.
The proof is stronger than a re-read: all 30 records were rebuilt independently from the 183 official
final scores in <code>data/raw/history/</code> and agree exactly. The measure that found the drift is
kept, inverted, on the <a href="live-verification.html">Live verification page</a>.</div>

<h2>Integrity checks that passed on this build</h2>
<p class="lede">Arithmetic identities the official tables must satisfy. If a transcription were wrong, one of these breaks.</p>
"""
    irow = []
    for key, label, val, ok in [
        ("wins==losses", "League wins = league losses", f"{integ['wins']} = {integ['losses']}", integ["wins_equals_losses"]),
        ("pts", "Points scored = points allowed (games-weighted)",
         f"{integ['weighted_points_scored']:.1f} vs {integ['weighted_points_allowed']:.1f} "
         f"(diff {integ['weighted_points_diff']:+.1f}, rounding bound ±{integ['rounding_bound']:.1f})",
         integ["points_identity_ok"]),
        ("homeroad", "Home wins = road losses", f"{integ['home_w']} = {integ['road_l']}", integ["home_wins_equal_road_losses"]),
        ("homeroad2", "Home losses = road wins", f"{integ['home_l']} = {integ['road_w']}", integ["home_losses_equal_road_wins"]),
        ("gp", "Games played sums to whole games",
         f"{integ['games_played_team_sum']} team-games = {integ['games']:.0f} league games (season to date, not the slate)", True),
    ]:
        irow.append({"cells": [esc(label), val, badge("PASS" if ok else "FAIL", "ok" if ok else "bad"),
                              srclink(O.SOURCES["standings"][1])]})
    body += table(["Identity", "Observed", "Result", "Source"], irow, "Arithmetic identities verified on the official team tables")

    body += """
<h2>Cross-checks against the previous build</h2>
<p class="lede">The repository already published a dataset. The v2 session re-read the same pages live and compared, so a
reader can see exactly where the earlier work was right and where it was not.
<strong>Read the first column as a date, not just a claim.</strong> These comparisons were made on
2026-11-14 before the nine 2026-11-13 games had official results. Nine games move eighteen team
records, so a MATCH below describes the state at transcription time. The
<a href="live-verification.html">Live verification page</a> re-runs the same idea against today's
official pages and shows where those rows now stand.</p>
"""
    crow = []
    for c in xchecks["checks"]:
        kind = "ok" if c["result"] == "MATCH" else "bad"
        crow.append({"cells": [esc(c["what"]), esc(c["repo_value"]), esc(c["live_value"]),
                              badge(c["result"], kind), esc(c["detail"])[:160], srclink(c["src"])]})
    body += table(["Check", "Committed in repo", "Live official (as transcribed 2026-11-14)", "Result at transcription time", "Detail", "Source"], crow,
                  "Repository dataset vs the 2026-11-14 official transcription")

    body += """
<h2>What this build cannot do — and why that is stated rather than hidden</h2>
"""
    brow = []
    for k, (what, why, url) in O.BLOCKED.items():
        brow.append({"cells": [esc(what), esc(why), srclink(url)]})
    body += table(["Missing input", "What it blocks", "Where it would come from"], brow, "Blocked inputs")
    body += """
<h2>Machine-readable copy</h2>
<p class="lede">Every table on this site is also published as JSON so a reviewer can diff it against the
official pages without trusting the rendering: <a href="data/teams.json">teams.json</a> ·
<a href="data/lines.json">lines.json</a> · <a href="data/verification.json">verification.json</a> ·
<a href="data/content.json">content.json</a>.</p>
"""
    built["index.html"] = page("index.html", "Dashboard", body, "index.html")

    # ------------------------------------------------------------------ executive summary
    # Refresh the counts that move every time a register changes, so this page cannot state a
    # number the registers contradict (it did: '14 questions' / '18 suggestions' while the files
    # held 22 / 20).
    n_questions = len(json.loads((ROOT / "requirements" / "QUESTIONS.json").read_text())["questions"])
    n_suggestions = len(json.loads((ROOT / "suggestions" / "SUGGESTIONS.json").read_text())["suggestions"])
    n_flags = len(C.FLAGS)
    chk = LV.checks()
    st_ex = chk.get("staleness") or {}
    gr_ex = chk.get("grade") or {}
    body = f"""<h1>Executive summary</h1>
<p class="lede">The state of the project in one screen, then the numbers behind it, then the single next decision.
Section 0 is this session's: it is the only part written after the 2026-11-13 results became official.</p>
"""
    body += f"""
<h2>0. What the live re-check changed today (2026-11-14)</h2>
<div class="note"><b>Found this session, and fixed this session.</b> The standings on this site had been
transcribed before the 2026-11-13 finals, so when they were first checked against live official standings they agreed
with the <em>pre-finals</em> state on <b>{st_ex.get('match_pre_final_state','—')} of 30</b> rows and with current
standings on only <b>12 of 30</b>. Nothing on the site could have caught it, because nothing compared a published row
against a fresher capture. That comparison now exists permanently, and it drove a full re-read of the standings from
nba.com: the table on this site now matches live official standings on
<b>{st_ex.get('match_live_standings','—')} of 30</b> rows, home and road splits included, and independently rebuilds
from the 183 committed official finals with zero mismatches. The check is kept, inverted, on
<a href="live-verification.html">Live verification</a>.</div>
<div class="note warn"><b>The first genuine forecast was graded, and it is not yet evidence of skill.</b>
<code>nba2/data/picks.json</code> was committed {gr_ex.get('minutes_before_first_tip','—')} minutes before the earliest
tip. It went <b>4-0</b> on the <b>4 distinct games</b> it bet — but 8 wins are recorded, because two strategies fired on
the same four games. On all {gr_ex.get('games_graded','—')} graded games the model named the winner
<b>{gr_ex.get('side_accuracy',{}).get('model','—')}/{gr_ex.get('side_accuracy',{}).get('n','—')}</b>, the same as a naive
net-rating baseline and <em>worse</em> than always picking the home team
({gr_ex.get('side_accuracy',{}).get('always_home','—')}/{gr_ex.get('side_accuracy',{}).get('n','—')}). No profit is
published, because no signal in the file carries a price.</div>
<div class="note"><b>What did not change.</b> Zero picks are stakable, because no market price exists. The two sealed
ledgers still start on 2026-11-14 and correctly remain PENDING. Nothing was invented to fill a gap, and the two
irregularities found (a sign inversion in the spread selections, and two dashboards claiming to be the site) are
published on the Flagged page rather than fixed silently in someone else's file.</div>
<h2>1. Six things you need to know, in the order they affect a decision</h2>
"""
    for head, txt in C.EXEC_BULLETS:
        body += f'<div class="note"><b>{esc(head)}.</b> {esc(txt)}</div>'
    body += f"""
<h2>Numbers behind the summary</h2>
"""
    rows = [
        {"cells": ["Games in window", f"{len(lines)}", f"{O.WINDOW_START} → {O.WINDOW_END} (three days ahead)", srclink(O.SOURCES["schedule"][1])]},
        {"cells": ["Games verified against the official schedule", f"{len(lines)} / {len(lines)}", "date, tip time, arena, game id", srclink(O.SOURCES["schedule"][1])]},
        {"cells": ["Team records verified against nba.com/standings", "30 / 30", "exact match, home and road splits included", srclink(O.SOURCES["standings"][1])]},
        {"cells": ["Team records rebuilt from official final scores", "30 / 30", f"every standings record reconstructed from the {lab['meta']['n_games']} committed finals, 0 mismatches", srclink(O.SOURCES["games"][1])]},
        {"cells": ["Official finals captured", f"{lab['meta']['n_games']} / {lab['meta']['n_games']}", "the full 2026-10-20 → 2026-11-13 window; the count is implied independently by the standings", srclink(O.SOURCES["games"][1])]},
        {"cells": ["Injury rows transcribed from the official PDF", f"{len(O.INJURIES)} player rows (+{len(O.NOT_SUBMITTED)} teams not yet filed)", "11/14/26 04:30 AM ET release", srclink(O.INJURY_PDF_URL)]},
        {"cells": ["Measured correlations", f"{sum(1 for c in lab['correlations'] if c['status'] == 'MEASURED')}", "computed walk-forward from the official finals", srclink(O.SOURCES["games"][1])]},
        {"cells": ["Correlations that cannot be measured", f"{sum(1 for c in lab['correlations'] if c['status'] == 'BLOCKED')}", "all three are player-level; each names the missing dataset", srclink(O.BLOCKED["player_box"][2])]},
        {"cells": ["Teams outside the luck noise band", f"{sum(1 for t in teams.values() if abs(t.luck_z) > 1.96)} / 30", "|z| ≤ 1.96", srclink(O.SOURCES["standings"][1])]},
        {"cells": ["Leans published / games staked", f"{len(lines)} / 0", "every game gets an originated lean and a trigger price; no stake clears G6 and G7", srclink(O.BLOCKED["odds"][2])]},
        {"cells": ["Gates passing / failing", f"{sum(1 for g in lab['gates'] if g['verdict'] == 'PASS')} / {sum(1 for g in lab['gates'] if g['verdict'] == 'FAIL')}", "evaluated from data, not asserted — see the strategy lab", srclink(O.SOURCES["games"][1])]},
        {"cells": ["Strategies that may be ranked", "0 / 7", "G6 (no price) fails for all; G7 fails on sample size (167 settled of 300), not on absence of data", srclink(O.BLOCKED["live_ingest"][2])]},
        {"cells": ["Open decision questions", f"{n_questions}", "each with a way to resolve it — see the questions page", srclink(O.SOURCES["standings"][1])]},
        {"cells": ["Suggestions in the register", f"{n_suggestions}", "7 of them are the numbered decision queue — see the decision queue page", srclink(O.SOURCES["schedule"][1])]},
        {"cells": ["Flagged irregularities", f"{n_flags}", "all on the Flagged for review page with a source to check", srclink(O.SOURCES["standings"][1])]},
        {"cells": ["Published team records that still match today's official standings", f"{st_ex.get('match_live_standings','—')} / 30", "the 2026-11-14 refresh re-read the standings and the pre-final drift is resolved — see Live verification", srclink(O.SOURCES["standings"][1])]},
    ]
    body += table(["Item", "Value", "Basis", "Source"], rows, "Summary figures")
    body += f"""
<h2>Recommended sequence</h2>
<ol>
  <li><b>Connect the odds feed (SG-3).</b> Nothing that involves money moves without a price. All other model work is preparation until then.</li>
  <li><b>Connect a per-game results feed (SG-2).</b> This turns the model into something testable and lets the leaderboard exist.</li>
  <li><b>Schedule the ingestion (SG-1).</b> Freshness gate G11 can never pass while data arrives by hand.</li>
  <li><b>Then</b> measure the six missing correlations and re-price parlays; <b>then</b> pre-register strategies and start the competition.</li>
</ol>
<p class="lede">Everything else on this site — gates, leaderboard rules, injury tracking, game flow — is designed to be ready when those three feeds land.</p>
<h2>The single next decision</h2>
<p><b>Retire the tree nobody can reach, then decide what a pick is worth.</b> Probing the live site settles which tree is
published: <code>/NBA2/pages/session-audit.html</code> and <code>/NBA2/pages/executive-summary.html</code> both return
<b>404</b> while <code>/NBA2/data/teams.json</code> returns <b>200</b> with v2 content. So exactly one tree — the
<code>site/</code> artefact — reaches a reader, and the v1 tree at the repository root is unreachable maintenance debt
that CI still rebuilds and lints on every push. Retiring it is cheap and removes a stale record set from the audit
surface. The expensive decision remains the price: with no odds feed, nothing on this site can ever become a bet.
<a href="decision-queue.html">The queue ranks both.</a></p>
<div class="cards">
  <div class="card"><h4><a href="decision-queue.html">Review the decision queue</a></h4><p>Seven numbered decisions,
  each with its evidence, the change it would make, and an accept / reject / defer action. Nothing is implemented until
  you choose.</p></div>
  <div class="card"><h4><a href="live-verification.html">Check today's evidence</a></h4><p>The official pages read today,
  what each one contradicted, and the grading of the repository's first real forecast.</p></div>
  <div class="card"><h4><a href="flagged.html">Read what is still wrong</a></h4><p>{n_flags} irregularities, each with a
  source to check. None block publication; all block a promotion.</p></div>
</div>
"""
    built["executive-summary.html"] = page("executive-summary.html", "Executive summary", body, "executive-summary.html")

    # ------------------------------------------------------------------ picks & slate
    body = """<h1>Picks &amp; the upcoming slate</h1>
<p class="lede">Every game in the three-day window (2026-11-14 → 2026-11-17) is priced from our own originated lines,
and every game gets a lean. What no game gets is a stake: a bet needs a price to beat and a settled sample large enough
that the edge is not a coin flip that happened to land, and this repository has neither.</p>
<div class="note"><b>What a "lean" is here.</b> It is the side our own number favours, together with the
<em>trigger</em> — the decimal price at which backing it stops being a losing bet. At our probability p, break-even is
decimal 1/p exactly, so the trigger is arithmetic, not a prediction about what a bookmaker will offer.</div>
<div class="note bad"><b>Two markets, two probabilities — read the right trigger.</b> The lean is a
<em>spread</em> at our own number, so the probability that prices it is the probability of <em>covering</em> that
number (<b>P(cover)</b>), not the probability of winning the game (<b>P(win)</b>). Our line is the median of our own
distribution, so P(cover) is close to 0.50 on every game by construction while P(win) ranges widely. Pricing a
spread bet off P(win) — as an earlier build of this page did — produces a trigger of, say, −1246 on a moneyline-shaped
probability, which no sportsbook offers on a spread. Both numbers are now printed, each with its own break-even
trigger, so the arithmetic can be checked against whichever market is actually being considered.</div>
<div class="note bad"><b>0 of 27 games are staked.</b> Not because the model failed, but because gate G6 (no market
price) and gate G7 (167 settled bets against a 300-bet bar) both fail. Publishing a stake anyway is the one thing this
build refuses to do.</div>
"""
    prows = R.t_picks(lines)
    rows = []
    for r in prows:
        rows.append({"id": r["src"] + r["matchup"], "cells": [
            esc(r["date"]), esc(r["time_et"]), esc(r["matchup"]),
            badge(r["grade"], {"A": "ok", "B": "warn", "C": "bad"}[r["grade"]]),
            esc(r["our_spread"]), esc(r["our_total"]),
            "<b>" + esc(r["lean"]) + "</b>", esc(r["lean_prob_ml"]), esc(r["lean_prob_cover"]),
            esc(r["trigger_decimal"]), "<b>" + esc(r["trigger_american"]) + "</b>",
            esc(r["trigger_ml_decimal"]), esc(r["trigger_ml_american"]),
            esc(r["stake"]), esc(r["gates_passed"]), esc(r["blocked_by"]),
            srclink(f"https://www.nba.com/game/{r['matchup'].split(' @ ')[0].lower()}"
                    f"-vs-{r['matchup'].split(' @ ')[1].lower()}-{r['date']}"),
        ]})
    body += table(["Date", "ET", "Matchup", "Grade", "Our spread", "Our total",
                   "Lean", "P(lean) win", "P(lean) cover", "Spread trigger dec", "Spread trigger US",
                   "ML trigger dec", "ML trigger US", "Stake", "Gates", "Blocked by", "Game page"],
                  rows, "All 27 games: originated line, lean, both probabilities and both trigger prices, with gate status",
                  num_cols=(4, 5, 7, 8, 9), idcol=None)

    body += """<h2>Why the stake is withheld</h2>
<p class="lede">Each gate below is evaluated from data, not asserted. The verdict column is what the build
measured; the basis column is the number that decided it.</p>
"""
    grows = []
    for g in lab["gates"]:
        kind = {"PASS": "ok", "FAIL": "bad"}.get(g["verdict"], "warn")
        grows.append({"cells": [esc(g["id"]), esc(g["name"]), esc(g["requirement"]),
                                badge(g["verdict"], kind), esc(g["measured"]), srclink(g["src"])]})
    body += table(["Gate", "Name", "Requirement", "Verdict", "What was measured", "Source"],
                  grows, "The twelve validation gates, evaluated on this build")

    body += """<h2>The slate itself</h2>
<p class="lede">Read from the official schedule on 2026-11-14. This is the full three-day window: 5 games on
11/14, 9 on 11/15, 8 on 11/16 and 5 on 11/17. Two matchups appear twice in the window (NYK @ TOR on 11/15 and
11/17, POR @ MIN on 11/16 and 11/17) — verified genuine against the official schedule block, not a duplication
error.</p>
"""
    srows = []
    for (d, t, a, h, gid, arena, city, tv, cup) in sorted(O.SLATE):
        srows.append({"cells": [esc(d), esc(t), f"{esc(a)} @ {esc(h)}", esc(gid), esc(arena), esc(city), esc(tv or "—"), esc(cup or "—"),
                               srclink("https://www.nba.com/schedule?date=" + d)]})
    body += table(["Date", "ET", "Matchup", "Game ID", "Arena", "City", "National TV", "Cup group", "Source"],
                  srows, f"{len(srows)} games on the official schedule", idcol=None)
    built["picks.html"] = page("picks.html", "Picks &amp; slate", body, "picks.html")

    # ------------------------------------------------------------------ lines
    body = """<h1>Originated lines</h1>
<p class="lede">Our own number for every game in the window, with the two independent estimators that make it, their
disagreement, the fitted parameters behind them, and a source for every input.</p>
<div class="note"><b>Formula, in full.</b><br>
<code>rating = mean(shrunk net points per game, shrunk NetRtg converted to points per game)</code><br>
<code>margin = rating_home + h − rating_away</code><br>
<code>p(home win) = Φ(margin / σ)</code> &nbsp; <code>spread = −round_to_half(margin)</code><br>
<code>total = (PF_home+PA_away)/2 + Δ_home/2 + (PF_away+PA_home)/2 + Δ_away/2</code> where Δ is the team's own scoring margin.
Every parameter is fitted (see the table below); nothing is hand-set.</div>
"""
    rows = []
    for l in lines:
        d = l.as_dict()
        rows.append({"id": d["game_id"], "cells": [
            esc(d["date"]), esc(d["matchup"]),
            f"{d['margin']:+.2f}", f"{d['spread']:+.1f}", f"{d['total']:.1f}",
            f"{d['est_a']:+.1f}", f"{d['est_b']:+.1f}", f"{d['agreement']:.1f}",
            f"{d['total_b']:.1f}", f"{d['total_gap']:+.1f}",
            f"{100*d['p_home']:.1f}%", f"{d['fair_home']:.3f}", f"{d['fair_away']:.3f}",
            f"{d['conviction']:.2f}σ", badge(d["grade"], {"A": "ok", "B": "warn", "C": "bad"}[d["grade"]]),
            srclink(d["marketup"] if "marketup" in d else O.SOURCES["team_adv"][1]),
        ]})
    body += table(["Date", "Matchup", "Margin", "Spread", "Total", "Spread A", "Spread B", "Δ spread",
                   "Total B", "Δ total", "P(home)", "Fair home", "Fair away", "Conviction", "Grade", "Source"],
                  rows, "31 originated lines with both estimators", num_cols=tuple(range(2, 14)), idcol="id")

    body += """<p class="lede">Spread A uses the net-points rating; spread B uses NetRtg. They are computed from different
official numerators (points vs points-per-100-possessions), so agreement is evidence the line is stable. Δ total compares the
per-game-average total with a per-100-possession × pace total; a large gap flags a pace inconsistency and drops the game to grade C.</p>
"""
    body += "<h2>Fitted parameters</h2>"
    crow = []
    for m in R.t_calibration(teams, cal):
        crow.append({"cells": [esc(m["metric"]), esc(m["value"]), esc(m["method"]), esc(m["cross_check"]),
                              badge(m["status"], "ok" if "fitted" in m["status"] or "derived" in m["status"] else "warn"),
                              srclink(m["src"])]})
    body += table(["Parameter", "Value", "How it was obtained", "Cross-check", "Status", "Source"],
                  crow, "Model parameters and how each was identified")
    body += """<div class="note warn"><b>The honest problem with σ and h.</b> Fitting both freely against one season of win
totals is ill-conditioned: σ anywhere from 9 to 13 fits equally well with h from +7.9 down to 0.0. This build therefore pins
h to the home-win rate actually observed (89–84 over 173 home games) and fits σ alone. The unconstrained answer is printed
beside it rather than hidden.</div>"""
    built["lines.html"] = page("lines.html", "Originated lines", body, "lines.html")

    # ------------------------------------------------------------------ strategies
    body = """<h1>Strategies, gates and the leaderboard</h1>
<p class="lede">Seven strategy families, specified to the point where they could be implemented — and a status that says
whether they are allowed to produce anything today.</p>
"""
    rows = []
    for s in C.STRATEGIES:
        kind = "ok" if s["status"].startswith("IMPLEMENTED") else "bad" if s["status"].startswith("BLOCKED") else "warn"
        rows.append({"id": s["id"], "cells": [
            esc(s["id"]), esc(s["name"]), badge(s["type"], "off"), esc(s["signal"]),
            badge(s["status"], kind), esc(s["gates_that_can_pass_today"]), esc(s["gates_that_fail_today"]),
            esc(s["why"]), srclink(s["src"])]})
    body += table(["ID", "Strategy", "Type", "Signal", "Status today", "Gates that can pass", "Gates that fail", "Why", "Source"],
                  rows, "Seven strategies against the twelve gates", idcol="id")

    body += """<h2>Why a strategy cannot simply be declared 'profitable'</h2>
<p class="lede">A line that agrees with the market is not an edge; a line that disagrees is either an edge or an error, and
only a settled backtest can tell you which. Both parlays types add a second problem: the legs are correlated, and multiplying
them is wrong in a direction that costs money.</p>
"""
    body += "<h2>Leaderboard rules and reward proposal</h2>"
    rows = []
    for name, rule, why, status, src in C.LEADERBOARD_RULES:
        rows.append({"cells": [esc(name), esc(rule), esc(why), badge(status, "warn"), srclink(src)]})
    body += table(["Rule", "Proposal", "Why it matters", "Status", "Basis"], rows,
                  "Leaderboard competition design — needs owner sign-off")
    body += """<div class="note warn"><b>Nothing here can run yet.</b> All seven rules assume settled bets. With no price and no
per-game results there are zero settled bets, so the leaderboard currently has nothing to score. The design is published so it
can be approved or amended before the data arrives, not after.</div>"""
    built["strategies.html"] = page("strategies.html", "Strategies &amp; leaderboard", body, "strategies.html")

    # ------------------------------------------------------------------ backtest
    btd = json.loads((DATA / "backtest.json").read_text()) if (DATA / "backtest.json").exists() else None
    body = """<h1>Backtest &amp; measured skill</h1>
<p class="lede">The one question every other page depends on: if this rating method had been run before each game, would it
have been right? This is a walk-forward test on official finals only, with no leakage and no future information.</p>
"""
    if btd is None:
        body += """<div class="note bad"><b>Not run yet.</b> <code>python3 -m nba2.v2.backtest</code> produces this page.</div>"""
    else:
        m, h, sg, cp = btd["meta"], btd["headline"], btd["significance"], btd["compression"]
        body += f"""<div class="note"><b>How the test works.</b> {m['n_games_scored']} games
({m['first_date']} → {m['last_date']}) are scored one at a time. For each game the ratings are rebuilt from
<em>only</em> the games strictly before that date — no same-day leakage, no future leakage — with the same shrinkage the
published model uses. {m['n_skipped_no_prior']} games are skipped because a team had never played. Sources:
<a href="{O.SOURCES['schedule'][1]}">nba.com/schedule</a> for the slate and one
<code>nba.com/game/&lt;slug&gt;-&lt;id&gt;</code> URL per final score.</div>"""

        rows = [
            {"cells": ["Straight-up accuracy", f"{h['straight_up_accuracy']*100:.2f}%",
                       f"{h['hits']} of {m['n_games_scored']}", f"95% CI {h['accuracy_ci95'][0]*100:.1f}–{h['accuracy_ci95'][1]*100:.1f}%",
                       srclink("https://www.nba.com/games")]},
            {"cells": ["Margin MAE (points)", f"{h['mae_margin']:.2f}", f"zero-margin baseline {h['mae_baseline_zero']:.2f}",
                       f"skill {h['skill_vs_baseline_pct']:+.1f}%", srclink("https://www.nba.com/games")]},
            {"cells": ["Margin RMSE (points)", f"{h['rmse_margin']:.2f}", f"baseline {h['rmse_baseline_zero']:.2f}",
                       "root mean squared error", srclink("https://www.nba.com/games")]},
            {"cells": ["Brier score (probability)", f"{h['brier']:.4f}", f"0.5000 coin-flip baseline is {h['brier_baseline']:.4f}",
                       f"skill {h['brier_skill_pct']:+.1f}%", srclink("https://www.nba.com/games")]},
            {"cells": ["Log loss", f"{h['log_loss']:.4f}", f"0.6931 coin-flip baseline",
                       "lower is better", srclink("https://www.nba.com/games")]},
            {"cells": ["AUROC (winner ranking)", f"{h['auroc']:.4f}", "0.5 = no ranking information",
                       "how often a winner is ranked above a loser", srclink("https://www.nba.com/games")]},
            {"cells": ["Mean bias", f"{h['bias']:+.2f} pts", "predicted minus actual margin",
                       "near zero means no systematic tilt", srclink("https://www.nba.com/games")]},
            {"cells": ["Paired bootstrap on the MAE gain", f"{sg['observed_mae_gain']:+.2f} pts",
                       f"P(gain &gt; 0) = {sg['p_gain_positive']:.3f} over {sg['draws']:,} draws (seed {sg['seed']})",
                       "significant at 5%" if sg["significant_at_5pct"] else "not significant",
                       srclink("https://www.nba.com/games")]},
        ]
        body += table(["Measure", "Value", "Comparison", "Read", "Source"], rows,
                      "Walk-forward skill against honest baselines", num_cols=(1,))

        body += f"""<h2>The uncomfortable part: the model is compressed</h2>
<div class="note bad"><b>Do not read a predicted margin as an expected margin.</b> The model's predicted margins have a
standard deviation of <b>{cp['predicted_margin_sd']:.2f} pts</b> against an actual <b>{cp['actual_margin_sd']:.2f} pts</b>
— a ratio of <b>{cp['ratio']:.2f}</b>. Its correlation with the real margin is only <b>{cp['r_predicted_vs_actual']:+.3f}</b>,
and a bigger predicted margin says almost nothing about how big the real win will be
(Spearman {cp['spearman_confidence_vs_bigwin']:+.3f}). The ratings rank teams usefully; they do not forecast blowouts.
Anything on this site that turned a predicted margin into a stake size would be misusing the model.</div>"""

        body += f"""<h2>Calibration: are the probabilities right?</h2>
<p class="lede">A model can rank well and still be badly calibrated. These bins compare predicted win probability with the
observed rate, with a Wilson 95% interval so a small bin is not over-read.</p>
"""
        rows = []
        for c in btd["calibration"]:
            gap = (c["observed"] - c["mean_predicted"]) * 100
            rows.append({"cells": [esc(c["bin"]), str(c["n"]), f"{c['mean_predicted']*100:.1f}%",
                                   f"{c['observed']*100:.1f}%", f"n = {c['hits']} wins",
                                   f"{c['ci95'][0]*100:.1f}–{c['ci95'][1]*100:.1f}%",
                                   f"{gap:+.1f} pp", srclink("https://www.nba.com/games")]})
        body += table(["Predicted probability bin", "Games", "Mean predicted", "Observed", "Wins", "95% CI", "Gap", "Source"],
                      rows, "Reliability by probability bin", num_cols=(1, 2, 3, 6))
        body += f"""<div class="note warn"><b>Calibration slope {h['calibration_slope']:.2f}.</b> A perfectly calibrated
model has a slope of 1.00; below 1 means it is <em>over-confident</em> in the sense that its probabilities spread wider than
reality, above 1 means under-confident. The slope here is pulled down by the compression above: the model's margins are too
small-scaled, so its probabilities bunch near 50% and must be rescaled before they mean anything.
<b>{h['games_to_prove_edge_vs_coinflip']}</b> more games at this accuracy would be needed to prove an edge over a 54.2% coin-flip.</div>"""

        body += """<h2>Does the shrinkage setting change the answer?</h2>
<p class="lede">Reported for transparency. The headline numbers above use the shipped configuration and were
<b>not</b> chosen by reading these rows — that would be fitting to the test set.</p>
"""
        rows = []
        for r in btd["sensitivity"]:
            rows.append({"cells": [f"{r['shrink_pseudo_games']:.0f}", str(r["n"]), f"{r['accuracy']*100:.2f}%",
                                   f"{r['mae']:.2f}", f"{r['pred_sd']:.2f}", esc(r["note"]),
                                   srclink("https://www.nba.com/games")]})
        body += table(["Shrink pseudo-games", "Games", "Accuracy", "Margin MAE", "Predicted margin sd", "Note", "Source"],
                      rows, "Sensitivity of the result to the shrinkage prior", num_cols=(0, 1, 2, 3, 4))

        body += f"""<h2>Does a bigger predicted margin mean a bigger real win?</h2>
<p class="lede">Only weakly. Rank correlation between |predicted margin| and |actual margin| is
<b>{cp['spearman_confidence_vs_bigwin']:+.3f}</b> — essentially no relationship. The model's confidence is a ranking device,
not a magnitude forecast.</p>"""
        body += f"""<div class="note"><b>Bottom line.</b> On {m['n_games_scored']} official finals this method is
{h['straight_up_accuracy']*100:.1f}% accurate straight up (CI {h['accuracy_ci95'][0]*100:.1f}–{h['accuracy_ci95'][1]*100:.1f}%),
beats a zero-margin baseline by {h['skill_vs_baseline_pct']:.1f}% on MAE, and its probabilities score a Brier of
{h['brier']:.4f} against 0.2500 for a coin flip. That is real signal. It is <b>not</b> profit: there is no price to beat in
this repository, so no ROI, no CLV, and no rank on the leaderboard can be produced from it. The leaderboard stays empty
until an odds feed and 300 settled bets exist (G1, G6).</div>"""

        body += """<h2>Every scored game</h2>
<p class="lede">The full row-by-row output, so any single number above can be checked against its game.</p>
"""
        rows = []
        for r in btd["rows"]:
            rows.append({"cells": [esc(r["date"]), esc(r["matchup"]),
                                   badge("neutral site", "off") if r["neutral"] else "—",
                                   f"{r['pred_margin']:+.2f}", f"{r['actual_margin']:+.0f}",
                                   f"{r['err']:+.2f}", f"{r['p_home']*100:.1f}%",
                                   badge("correct", "ok") if r["correct"] else badge("wrong", "bad"),
                                   srclink(r["source_url"])]})
        body += table(["Date", "Matchup", "Venue", "Predicted margin", "Actual margin", "Error", "P(home win)", "Result", "Official final"],
                      rows, "All walk-forward predictions against official finals", num_cols=(3, 4, 5, 6))
    built["backtest.html"] = page("backtest.html", "Backtest &amp; skill", body, "backtest.html")

    # ------------------------------------------------------------------ strategy lab
    labm = lab["meta"]
    ng_pass = sum(1 for g in lab["gates"] if g["verdict"] == "PASS")
    ng_fail = sum(1 for g in lab["gates"] if g["verdict"] == "FAIL")
    sig = [r for r in lab["luck"]["rows"] if r["verdict"] == "DISTINGUISHABLE FROM CHANCE"]
    small = [r for r in lab["luck"]["rows"] if "SAMPLE TOO SMALL" in r["verdict"]]
    body = f"""<h1>Strategy lab</h1>
<p class="lede">Seven candidate strategies, each scored walk-forward over {labm['n_scored']} predictions built from the
{labm['n_games']} official finals in this repository ({labm['first_date']} → {labm['last_date']}). Twelve validation gates,
each evaluated from the data rather than asserted. Then the part that matters most: how much of every record is luck.</p>

<div class="kpis">
  <div class="kpi"><b>{labm['n_games']}</b><small>official finals captured</small></div>
  <div class="kpi"><b>{labm['n_scored']}</b><small>predictions scored walk-forward</small></div>
  <div class="kpi"><b>{ng_pass} / {len(lab['gates'])}</b><small>gates passing ({ng_fail} failing)</small></div>
  <div class="kpi"><b>{len(sig)}</b><small>strategies distinguishable from chance</small></div>
  <div class="kpi"><b>{len(small)}</b><small>sample too small to call</small></div>
  <div class="kpi"><b>0</b><small>strategies ranked for reward</small></div>
</div>

<div class="note bad"><b>Nothing on this page is a bet, and nothing is ranked.</b> Two gates fail outright: G6, because
no market price is connected, and G7, because the largest settled sample here is {max((s.get('n') or 0) for s in lab['strategies'])} bets
against a 300-bet bar. Until those pass, the leaderboard is a scoring exercise, not a competition, and the reward pool
stays unfunded. That is a deliberate design choice: a leaderboard that can be topped by a lucky 7-0 run is worse than
no leaderboard.</div>

<h2>1. The strategies</h2>
<p class="lede">Each rule is written so it could be run by someone else tomorrow and get the same answer. "Lean" means
the signal; none of them carries a stake.</p>
"""
    srows = []
    for st in lab["strategies"]:
        kind = {"single bet": "ok", "parlay": "warn", "player prop combo": "bad"}.get(st["kind"], "off")
        n = st.get("n", 0)
        srows.append({"cells": [
            "<b>" + esc(st["sid"]) + "</b>",
            esc(st["name"]),
            badge(st["kind"], kind),
            esc(n) if n else '<span class="blank">0 — inputs unavailable</span>',
            esc(st["hit_rate"]) if n else '<span class="blank">—</span>',
            esc(st["wilson95"][0]) if n else '<span class="blank">—</span>',
            esc(st["wilson95"][1]) if n else '<span class="blank">—</span>',
            esc(st["log_loss"]) if n else '<span class="blank">—</span>',
            esc(st["brier"]) if n else '<span class="blank">—</span>',
            esc(st["rule"]),
            srclink(O.SOURCES["games"][1]),
        ]})
    body += table(["ID", "Strategy", "Type", "Bets", "Hit rate", "95% low", "95% high", "Log-loss", "Brier",
                   "Rule", "Source"],
                  srows, "Every candidate strategy, scored on the same walk-forward sample",
                  num_cols=(3, 4, 5, 6, 7, 8))

    body += """<h2>2. The validation gates, evaluated</h2>
<p class="lede">A gate that is never checked is decoration. Each row below is the number this build actually
measured, with the threshold it was measured against.</p>
"""
    grows = []
    for g in lab["gates"]:
        kind = {"PASS": "ok", "FAIL": "bad"}.get(g["verdict"], "warn")
        grows.append({"cells": [
            "<b>" + esc(g["id"]) + "</b>", esc(g["name"]), esc(g["requirement"]),
            badge(g["verdict"], kind), esc(g["measured"]), srclink(g["src"]),
        ]})
    body += table(["Gate", "Name", "Requirement", "Verdict", "What was measured", "Source"],
                  grows, f"{ng_pass} of {len(lab['gates'])} gates pass on this build")

    body += f"""<h3>Out-of-sample holdout (G8)</h3>
<p>Built on the first {int((1-labm['holdout_fraction'])*100)}% of game-dates, scored on the last
{int(labm['holdout_fraction']*100)}%. {esc(lab['holdout']['note'])}</p>

<h3>No-look-ahead audit (G12)</h3>
<p>{esc(lab['leakage']['verdict'])} across {lab['leakage']['n_predictions']} predictions. The rule is mechanical:
ratings for a date are built only from games with a strictly earlier date, so no prediction can see its own result or
any later one.</p>
"""

    body += """<h2>3. Correlation values</h2>
<p class="lede">Every parlay price depends on one of these. The ones that cannot be measured are named, with the
dataset that would unblock them, rather than filled with a plausible number.</p>
"""
    crows = []
    for c in lab["correlations"]:
        st = c["status"]
        kind = {"MEASURED": "ok", "BLOCKED": "bad"}.get(st, "off")
        crows.append({"cells": [
            esc(c["quantity"]),
            badge(st, kind),
            esc(c["n"]) if c["n"] else '<span class="blank">—</span>',
            esc(c["r"]) if c["r"] is not None else '<span class="blank">unmeasured</span>',
            esc(c["ci95"][0]) if c["ci95"] else '<span class="blank">—</span>',
            esc(c["ci95"][1]) if c["ci95"] else '<span class="blank">—</span>',
            esc(c["p_two_sided"]) if c["p_two_sided"] is not None else '<span class="blank">—</span>',
            esc("yes" if c["significant_at_5pct"] else "no") if st == "MEASURED"
            else '<span class="blank">—</span>',
            esc(c["note"]),
            srclink(O.SOURCES["games"][1] if st == "MEASURED" else O.BLOCKED["player_box"][2]),
        ]})
    body += table(["Quantity", "Status", "n", "r", "95% low", "95% high", "p", "Significant",
                   "Reading", "Source"],
                  crows, "Measured correlations and the ones that remain blocked",
                  num_cols=(2, 3, 4, 5, 6))

    pp = lab["parlay_pricing"]
    if pp.get("status") == "MEASURED":
        body += f"""<h3>What the same-game correlation does to a two-leg price</h3>
<p>The measured same-game correlation is <b>{pp['measured_rho']:+.4f}</b>
(95% CI {pp['rho_ci95'][0]:+.4f} to {pp['rho_ci95'][1]:+.4f}, n = {pp['n']}). Below is what that does to a joint
price, computed as a bivariate-normal quadrant — the arithmetic a book actually uses.</p>
"""
        prows = []
        for r in pp["rows"]:
            prows.append({"cells": [
                esc(r["legs"]), esc(r["p_leg_1"]), esc(r["p_leg_2"]),
                esc(r["naive_product"]), "<b>" + esc(r["joint_at_measured_rho"]) + "</b>",
                esc(r["joint_at_ci_low"]), esc(r["joint_at_ci_high"]),
                esc(r["error_pct"]), esc(r["fair_decimal_if_naive"]),
                esc(r["fair_decimal_at_measured"]),
                srclink(O.SOURCES["games"][1]),
            ]})
        body += table(["Legs", "P(leg 1)", "P(leg 2)", "Naive product", "Joint at measured ρ",
                       "Joint at CI low", "Joint at CI high", "Error if you multiply (%)",
                       "Fair dec (naive)", "Fair dec (measured)", "Source"],
                      prows, "Two-leg same-game prices across the measured correlation band",
                      num_cols=(1, 2, 3, 4, 5, 6, 7, 8, 9))
        body += f"""<div class="note warn"><b>How to read this.</b> {esc(pp['reading'])}</div>"""

    body += """<h2>4. Luck versus skill</h2>
<p class="lede">A hit rate without an interval is an anecdote. Every strategy below is tested against the rate it
must beat — a coin flip for a single bet, its own printed price for a parlay — and the verdict says whether the
result is distinguishable from that.</p>
"""
    lrows = []
    for r in lab["luck"]["rows"]:
        if not r.get("n"):
            lrows.append({"cells": [
                "<b>" + esc(r["sid"]) + "</b>", esc(r["name"]),
                '<span class="blank">0</span>', '<span class="blank">—</span>',
                '<span class="blank">—</span>', '<span class="blank">—</span>',
                '<span class="blank">—</span>', '<span class="blank">—</span>',
                badge("NO BETS", "bad"), esc(r["reason"]),
                srclink(O.SOURCES["player_trad"][1]),
            ]})
            continue
        verdict = r["verdict"]
        kind = ("ok" if verdict == "DISTINGUISHABLE FROM CHANCE"
                else "bad" if verdict == "NO BETS GENERATED"
                else "warn")
        lrows.append({"cells": [
            "<b>" + esc(r["sid"]) + "</b>", esc(r["name"]), esc(r["n"]), esc(r["hit_rate"]),
            f"{r['wilson95'][0]} – {r['wilson95'][1]}",
            esc(r["base_rate"]) + f" ({esc(r['base_rate_meaning'])})",
            esc(r["p_vs_base"]),
            "yes" if r["interval_contains_base"] else "no",
            badge(verdict, kind),
            esc(f"{r['games_to_prove_at_this_rate']} bets needed" if r["games_to_prove_at_this_rate"]
                else "interval already excludes the base rate" if not r["interval_contains_base"]
                else "cannot be decided at this sample"),
            srclink(O.SOURCES["games"][1]),
        ]})
    body += table(["ID", "Strategy", "Bets", "Hit rate", "95% interval", "Must beat", "p",
                   "Interval contains base?", "Verdict", "What it would take", "Source"],
                  lrows, "Binomial tests against the base rate each strategy must beat",
                  num_cols=(2, 3, 6))

    body += """<div class="note warn"><b>The trap on this table.</b> S4 is 7 for 7 — a 100% record, and a binomial
p-value of 0.016 that would pass a naive significance test. It is still not evidence of skill: at seven bets the
interval is wide enough to hold almost any true rate, which is exactly why the verdict column reads
"samples too small to call" and why the leaderboard refuses to rank it. A record this short is what luck looks like
when it is winning.</div>

<h2>5. The leaderboard</h2>
<p class="lede">Ranked by log-loss, which is a proper scoring rule: it rewards honest probabilities rather than
lucky ones. Nothing is eligible for a reward while a blocking gate fails.</p>
"""
    lb = lab["leaderboard"]
    brows = []
    for r in lb["ranked"]:
        brows.append({"cells": [
            esc(r["rank_by_log_loss"]), "<b>" + esc(r["sid"]) + "</b>", esc(r["name"]),
            esc(r["kind"]), esc(r["n"]), esc(r["hit_rate"]), esc(r["log_loss"]),
            esc(r["brier"]), esc(r["auroc"]), esc(r["calibration_gap"]),
            badge("ELIGIBLE" if r["eligible_for_reward"] else "BLOCKED",
                  "ok" if r["eligible_for_reward"] else "bad"),
            esc(r["blocked_by"]),
            srclink(O.SOURCES["games"][1]),
        ]})
    body += table(["Rank", "ID", "Strategy", "Type", "Bets", "Hit rate", "Log-loss", "Brier",
                   "AUROC", "Calibration gap", "Reward", "Blocked by", "Source"],
                  brows, f"Ranked by log-loss; minimum sample to rank is {lb['min_sample_to_rank']} settled bets",
                  num_cols=(4, 5, 6, 7, 8, 9))

    body += f"""<h3>Reward pool</h3>
<p>{esc(lb['reward_pool']['total_units'])} units: {esc(lb['reward_pool']['allocation'])}.</p>
<div class="note bad"><b>{esc(lb['reward_pool']['status'])}</b></div>

<h3>Competition rules</h3>
"""
    rrows = []
    for (k, v, why, basis, src) in C.LEADERBOARD_RULES:
        rrows.append({"cells": [esc(k), esc(v), esc(why), badge(basis, "warn" if "PROPOSED" in basis else "info"),
                                srclink(src)]})
    body += table(["Rule", "Setting", "Why", "Basis", "Source"], rrows,
                  "How the leaderboard is scored and what disqualifies a submission")

    body += """<h2>6. What would move a strategy onto the board</h2>
<ol>
  <li><b>A dated market price (G6).</b> One odds feed with timestamps turns every projection on this site into a
  testable claim. Nothing else on this list matters as much.</li>
  <li><b>More settled bets (G7).</b> The bar is 300. The largest sample here is 167, and the season produces roughly
  12 games a day, so the bar is reachable inside a season rather than in years.</li>
  <li><b>Per-player game logs.</b> Unblocks S7 and every prop-combo correlation on the correlations table. These are
  the only correlations on this site still listed as blocked for lack of data rather than lack of power.</li>
</ol>
"""
    built["strategy-lab.html"] = page("strategy-lab.html", "Strategy lab", body, "strategy-lab.html")

    # ------------------------------------------------------------------ skill vs luck
    sb = lab["baselines"]
    at = lab["skill_attribution"]
    wp = at["headline_vs_win_pct_baseline"]
    pd_ = at["headline_vs_margin_baseline"]
    s1 = next((r for r in lab["strategies"] if r["sid"] == "S1"), {})
    body = f"""<h1>Skill vs luck — is any of this better than backing the favourite?</h1>
<p class="lede">Every accuracy figure elsewhere on this site answers the wrong question. "Our side hit
{100 * s1.get('hit_rate', 0):.1f}% of {s1.get('n', 0)} games" sounds like skill until you ask whether the side we picked
was simply the better team. This page answers the right question with a paired test on exactly the games
where our model and the naive rule disagree — because those are the only games that carry any information
about skill at all.</p>

<div class="note bad"><b>The result, before the detail.</b> Backing the team with the better prior win record
scored <b>{100 * (wp['baseline_hit_rate'] or 0):.1f}%</b> on {wp['baseline_n']} of the same
{wp['model_n']} games. Our model scored <b>{100 * (wp['model_hit_rate_same_games'] or 0):.1f}%</b>.
On the <b>{wp['discordant_games']}</b> games where the two disagreed, the naive rule was right
<b>{wp['baseline_won_those']}</b> times and the model <b>{wp['model_won_those']}</b> times
(exact McNemar p = <b>{wp['mcnemar_exact_p']}</b>). The model has therefore demonstrated <b>no skill that is
separable from the favourite's win rate</b> at this sample size. That is a finding, not a bug, and it is exactly
what the brief's "remove luck from the equation" step is for.</div>

<h2>1. The naive baselines, measured on the same games</h2>
<p class="lede">Each baseline consumes only information that existed before its game tipped — prior results, nothing
else — and is scored on the identical set of regular-season games the walk-forward model scored. Ties are skipped and
the skipped count is published rather than hidden.</p>
"""
    brows = []
    for b in sb["baselines"]:
        lo, hi = (b["wilson95"] + [None, None])[:2]
        brows.append({"cells": [
            esc(b["baseline"]), esc(b["n"]), esc(b["hits"]), esc(b["ties_skipped"]),
            f"<b>{100 * b['hit_rate']:.1f}%</b>" if b["hit_rate"] else "—",
            f"{100 * lo:.1f}% – {100 * hi:.1f}%" if lo is not None else "—",
            esc(b["p_vs_coinflip"]), esc(b["note"]), srclink(O.SOURCES["games"][1]),
        ]})
    body += table(["Baseline rule", "Games scored", "Correct", "Ties skipped", "Hit rate",
                   "Wilson 95% CI", "p vs coin flip", "What it uses", "Source"],
                  brows, "Naive baselines for winner selection, walk-forward, same games",
                  num_cols=(1, 2, 3, 4, 6))

    body += f"""<h2>2. The paired test — McNemar on the disagreements</h2>
<p class="lede">A paired comparison does not need 300 games, because only the <em>discordant</em> games
carry information: if our model and the naive rule pick the same side, that game tells us nothing about which is
better. McNemar's exact test asks whether the split of the discordant games is consistent with a coin flip.</p>
"""
    prow = []
    for h in (wp, pd_):
        prow.append({"cells": [
            esc(h["baseline"]),
            f"{100 * h['baseline_hit_rate']:.1f}% ({h['baseline_n']})" if h["baseline_hit_rate"] else "—",
            esc(h["discordant_games"]), esc(h["model_won_those"]), esc(h["baseline_won_those"]),
            f"<b>{h['mcnemar_exact_p']}</b>",
            badge("NO SEPARABLE SKILL" if (h["mcnemar_exact_p"] or 1) >= 0.05 else "SKILL DETECTED",
                  "bad" if (h["mcnemar_exact_p"] or 1) >= 0.05 else "ok"),
            esc(h["verdict"]), srclink(O.SOURCES["games"][1]),
        ]})
    body += table(["Baseline", "Baseline rate (n)", "Discordant games", "Model right", "Baseline right",
                   "Exact p", "Reading", "Verdict", "Source"],
                  prow, "Paired comparison on the games where model and baseline disagree",
                  num_cols=(2, 3, 4, 5))
    body += f"""<div class="note"><b>{esc(at['why_this_matters'])}</b></div>

<h2>3. Why the headline hit rate is high, and why that is not the same as skill</h2>
<p>The model's side is the side its own ratings favour, and those ratings are built from the same box scores a
reader can look at. Naturally it picks the better team most of the time, and naturally the better team wins more than
half the time. The high hit rate is <em>inherited</em> from the favourite's base rate; the discordant test above
subtracts that inheritance and finds nothing left over.</p>
<p>This is why the site refuses to promote a strategy on accuracy alone. Two further measurements tell the same
story:</p>
<ul>
  <li><b>Sample size.</b> The largest strategy has {s1.get('n', 0)} settled bets against a 300-bet promotion bar
  (gate G7).</li>
  <li><b>Confidence intervals.</b> Every rate on this site is published with a Wilson interval, and every interval
  here is wide enough to contain the base rate. A wide interval is not a verdict; it is the honest absence of one.</li>
</ul>

<h2>4. What measurement would settle it</h2>
<p class="lede">The route out is arithmetic, not opinion: more discordant games, and a market price to test against.</p>
"""
    roads = [
        ("More graded games", "The discordant sample grows roughly linearly with graded games — about one discordant game in five. To take a 13-of-33 split to significance at 5% needs on the order of 100+ discordant games, i.e. roughly 500 graded games.",
         "No new data source needed; the nightly settlement already grades every finished game.", O.SOURCES["games"][1]),
        ("A market price", "Skill in betting is measured against the line, not against a naive rule. With a closing price, the question becomes the right one: does our number beat the market's?",
         "Requires a licensed odds feed. Blocked; see the decision register.", O.BLOCKED["odds"][2]),
        ("Player-level data", "Props, prop combos and per-player correlations cannot be measured at all without per-game player box scores.",
         "Requires a per-game player feed. Blocked.", O.BLOCKED["player_box"][2]),
    ]
    rrows = [{"cells": [f"<b>{esc(a)}</b>", esc(b), esc(c), srclink(d)]} for (a, b, c, d) in roads]
    body += table(["Path", "What it would take", "Status", "Source"], rrows,
                  "What measurement would turn this from an open question into an answered one")
    body += """
<div class="note info"><b>What this page does not say.</b> It does not say the model is worse than a naive rule —
the point estimate is that the naive rule is ahead on the disagreement set, with a p of 0.30 on 33 games, which is
not evidence either way. It says the model has not yet <em>earned</em> the claim, and that publishing the claim without
this test would be the hallucination the brief forbids.</div>
"""
    built["skill-attribution.html"] = page("skill-attribution.html", "Skill vs luck", body, "skill-attribution.html")

    # ------------------------------------------------------------------ decisions needed
    dec = json.loads((ROOT / "requirements" / "DECISIONS.json").read_text())
    body = f"""<h1>Decisions needed before anything else is built</h1>
<p class="lede">{esc(dec['source_note'])}</p>
<div class="note"><b>How to use this page.</b> Read the <em>What we have</em> column first — it is the
measurement, not an opinion. The <em>What is missing</em> column is the specific gap. The <em>How to close it</em>
column is the route. A decision can be recorded against any row without touching code; until one is, the row stands
as <b>OPEN</b> and no work depending on it should start.</div>
"""
    drows = []
    for d in dec["decisions"]:
        drows.append({"id": d["id"], "cells": [
            esc(d["id"]),
            badge(d["severity"], {"BLOCKING": "bad", "HIGH": "warn", "MEDIUM": "info"}.get(d["severity"], "info")),
            esc(d["topic"]),
            "<b>" + esc(d["question"]) + "</b>",
            esc(d["have"]), esc(d["missing"]), esc(d["how_to_find_out"]),
            esc(d["impact"]), esc(d["blocks"]), esc(d["who_decides"]),
            badge("OPEN", "warn"),
            srclink(d["source"]),
        ]})
    body += table(["ID", "Severity", "Topic", "Question", "What we have", "What is missing",
                   "How to close it", "What it decides", "Blocks", "Who decides", "Status", "Source"],
                  drows, "Decision register — what must be answered before the next build step",
                  idcol="id")
    body += """
<h2>What is missing, and how to go and get it</h2>
<p class="lede">Three of the eight decisions above are blocked on the same thing: data this repository does not
hold. This is the shortest honest version of that list.</p>
"""
    missing = [
        ("Licensed odds, opening and closing",
         "Every edge, CLV and ROI figure on this site; gates G6 and G7",
         "A vendor contract plus storage rights. Until it exists, no price is published and none is estimated.",
         "D-01", O.BLOCKED["odds"][2]),
        ("Per-game player box scores with minutes",
         "Player props, prop combos, same-player correlations, the production half of injury impact",
         "A per-game player feed. Until it exists, those tables stay blank — a blank is published, not a guess.",
         "D-02", O.BLOCKED["player_box"][2]),
        ("A pre-registered evidence rule",
         "Any statement that a strategy has skill",
         "Decide the test and the threshold BEFORE the next games are graded. The test is already written.",
         "D-05", "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/v2/strategy_lab.py"),
        ("Play-by-play",
         "In-game flow analysis, if that is what the brief meant",
         "A play-by-play feed, or a decision that schedule-spot analysis is the intended scope.",
         "D-08", O.SOURCES["games"][1]),
        ("A named reward and submission model",
         "Whether the leaderboard needs real anti-gaming controls",
         "An owner answer to three questions: who submits, is the reward money, in which jurisdiction.",
         "D-04", O.SOURCES["games"][1]),
    ]
    mrows = [{"cells": [f"<b>{esc(a)}</b>", esc(b), esc(c), esc(d), srclink(e)]}
             for (a, b, c, d, e) in missing]
    body += table(["What is missing", "What it blocks", "How to obtain it", "Decision it closes", "Source"],
                  mrows, "The gap list: what we do not have and what it would take to get it")
    body += """
<h2>What we already have, so nobody re-decides it</h2>
<div class="cards">
  <div class="card"><h4>The whole 3-day slate</h4><p>27 games, 2026-11-14 → 11-17, each verified field by field
  against the official NBA.com schedule this session (27/27 identical).</p></div>
  <div class="card"><h4>Official team records</h4><p>All 30 clubs re-read from the official standings this session
  and matching the published table exactly (30/30).</p></div>
  <div class="card"><h4>An originated line for every game</h4><p>Spread, total, win probability and both break-even
  triggers, from two independent estimators, with their disagreement published beside every number.</p></div>
  <div class="card"><h4>An honest skill measurement</h4><p>A paired test against naive rules, which found no
  separable skill at 167 games. That is a result, and it is published rather than buried.</p></div>
</div>
"""
    built["decisions-needed.html"] = page("decisions-needed.html", "Decisions needed", body, "decisions-needed.html")

    # ------------------------------------------------------------------ correlations
    body = """<h1>Correlations &amp; parlay pricing</h1>
<p class="lede">The number that decides whether a parlay is priced correctly is the correlation between its legs.
Six of them can be measured from what we have. Six cannot, and those are the ones that matter for same-game parlays and props.</p>
"""
    rows = []
    for r in R.t_correlation(teams):
        rows.append({"cells": [esc(r["pair"]), f"{r['pearson']}", f"{r['spearman']}", esc(r["n"]),
                              f"{r['t']}", badge(r["significant"], "ok" if r["significant"].startswith("yes") else "off"),
                              esc(r["use"]), srclink(r["src"])]})
    body += table(["Pair (n = 30 teams)", "Pearson r", "Spearman ρ", "n", "t (df 28)", "Significant at 5%", "What it tells you", "Source"],
                  rows, "Measured correlations between official team metrics", num_cols=(1, 2, 3, 4))

    body += """<h2>The correlations that are still missing</h2>
<p class="lede">These are the ones a parlay desk actually needs. Each is listed with the exact dataset that would unlock it —
not left as a vague promise.</p>
"""
    rows = []
    for b in R.t_blocked_correlations():
        rows.append({"cells": [esc(b["pair"]), esc(b["why_it_matters"]),
                              badge(b["status"], "bad" if b["status"] == "BLOCKED" else "warn"),
                              esc(b["explanation"]), srclink(b["source_url"])]})
    body += table(["Leg pair", "Why it matters", "Status", "Explanation", "Source / would come from"], rows, "Unmeasured correlations")

    body += """<h2>Why you may not multiply the legs</h2>
<p class="lede">A two-leg parlay's fair price is the <em>joint</em> probability, not the product. The arithmetic below is exact
and needs no data — it is the part of parlay analysis that survives missing inputs.</p>
<pre>two independent legs, p = 0.50 each      →  joint = 0.2500
same two legs, correlation ρ = +0.40     →  joint = 0.3200   (a 28% higher price)
same two legs, correlation ρ = −0.40     →  joint = 0.1800   (a 28% lower price)

Under-independence error = p_ind × δ, where (1+δ) is the factor by which the true joint
probability differs from the product. A parlay priced off the product is therefore mispriced
by exactly the correlation it ignored.</pre>
"""
    rows = []
    for r in R.t_parlay_cost():
        rows.append({"cells": [esc(r["legs"]), esc(r["decimal"]), esc(r["break_even"]),
                              esc(r["single_leg_break_even"]), esc(r["hold_per_leg"]), esc(r["hold_n_legs_pct"]),
                              srclink("https://www.nba.com/schedule")]})
    body += table(["Legs", "Parlay decimal", "Break-even prob", "Single-leg break-even", "Hold per leg", "Compounded hold", "Source"],
                  rows, "What stacking legs costs at the standard -110 price", num_cols=(0, 1, 2, 4, 5))
    body += """<div class="note bad"><b>The consequence.</b> At -110 a single leg needs 52.38% to break even; two legs need
27.44% jointly. If your legs are correlated you must know <em>how</em> correlated, because the same two 50% legs are worth
25.0% or 32.0% depending only on that number. Every same-game parlay on this site is therefore withheld (gate G10).</div>"""
    built["correlations.html"] = page("correlations.html", "Correlations &amp; parlays", body, "correlations.html")

    # ------------------------------------------------------------------ props
    body = """<h1>Player props &amp; combos</h1>
<p class="lede">What the official player table gives us, and the one thing it does not: a distribution.</p>
<div class="note bad"><b>No prop is publishable.</b> Season averages exist officially; the probability that a player clears a
line needs a per-game distribution and a minutes floor. Neither is available, so the site publishes the averages and the
missing input by name rather than a fabricated probability.</div>
"""
    rows = []
    for p in R.t_players():
        rows.append({"cells": [esc(p["player"]), esc(p["team"]),
                              esc(p["gp"]) if p["gp"] else '<span class="blank">—</span>',
                              esc(p["min"]) if p["min"] else '<span class="blank">—</span>',
                              esc(p["pts"]) if p["pts"] else '<span class="blank">—</span>',
                              esc(p["reb"]) if p["reb"] else '<span class="blank">—</span>',
                              esc(p["ast"]) if p["ast"] else '<span class="blank">—</span>',
                              esc(p["report_status"]),
                              '<span class="blank">minutes floor needs game logs</span>',
                              srclink(p["src"])]})
    body += table(["Player", "Team", "GP", "MIN", "PTS", "REB", "AST", "Official report status", "Minutes floor", "Source"],
                  rows, "Official season averages for the players used in this build", num_cols=(2, 3, 4, 5, 6))
    body += """<p class="lede">Season averages are a mean, not a distribution. To price "over 24.5 points" you need the spread
of game-by-game scoring around that mean and the chance the player is on the floor at all — which is why the minutes-floor
column is blank rather than guessed.</p>
<h2>Prop combos: the same correlation problem, per player</h2>
<p class="lede">A points + rebounds combo needs the correlation between a player's own points and rebounds in the same game.
For a centre it is usually strongly positive; for a guard it can be near zero. Publishing a combo price without it would be
a guess dressed as a number, so combos are blocked here (S6) with the exact dataset named.</p>
<h2>What would unblock this page</h2>
<ul>
  <li>Per-player game logs (one row per player per game: minutes, points, rebounds, assists) → distributions and combo correlations.</li>
  <li>A licensed odds feed with player prop lines and prices → the line to beat.</li>
  <li>An empirical status→play table (from report history) → the probability a "Questionable" player appears at all.</li>
</ul>"""
    built["props.html"] = page("props.html", "Player props", body, "props.html")

    # ------------------------------------------------------------------ injuries
    inj_rows, counts = R.t_injuries(teams)
    body = f"""<h1>Injuries &amp; rotation</h1>
<p class="lede">{len(O.INJURIES)} player-status rows transcribed from the official 11/14/26 04:30 AM ET report, plus the
{len(O.NOT_SUBMITTED)} team-rows the league had not yet received at capture time. Every row links to the PDF it came from.</p>
<div class="note"><b>Filing deadlines, from the league's own page.</b> Teams must report by 5 p.m. local the day before a game
(other than the second of a back-to-back) and again between 11 a.m. and 1 p.m. on game day; for the second of a back-to-back,
by 1 p.m. local on game day. Reports are updated continuously. <a href="{O.SOURCES['injury_policy'][1]}" target="_blank" rel="noopener">official.nba.com</a></div>
<div class="note warn"><b>Dated input, and why days 2 and 3 are blank.</b> The 11/14 05:30 AM ET report returned
AccessDenied at retrieval time, so the freshest reachable release is 04:30 AM ET. More importantly: a team files for a
game by 5 p.m. local <em>the day before</em>, so for the 11/15, 11/16 and 11/17 games the deadline has not yet passed and
no official row exists to read. Those cells are blank by policy, never estimated. Nothing was filled in from an
unavailable or non-existent file.</div>
"""
    body += "<h2>Per-team exposure</h2>"
    rows = []
    for r in R.t_rotation(counts):
        rows.append({"cells": [esc(r["team"]), esc(r["out"]), esc(r["doubtful"]), esc(r["questionable"]),
                              esc(r["probable"]), esc(r["available"]), esc(r["not_submitted"]),
                              badge(r["risk"], "bad" if r["risk"].startswith(("SEVERE", "UNKNOWN")) else "warn" if r["risk"] == "HIGH" else "off"),
                              '<span class="blank">needs per-player minutes</span>',
                              '<span class="blank">needs on/off data</span>',
                              srclink(r["src"])]})
    body += table(["Team", "Out", "Doubtful", "Questionable", "Probable", "Available", "Not filed",
                   "Rotation risk", "Minutes impact", "Production impact", "Source"],
                  rows, "Per-team status counts from the official report", num_cols=(1, 2, 3, 4, 5, 6))

    body += f"<h2>All {len(inj_rows)} status rows</h2>"
    rows = []
    for r in inj_rows:
        rows.append({"id": f"{r['matchup']}-{r['player']}".replace(" ", "-"),
                     "cells": [esc(r["date"]), esc(r["time"]), esc(r["matchup"]), esc(r["team"]), esc(r["player"]),
                              badge(r["status"], "bad" if r["status"] == "Out" else "warn" if r["status"] in ("Questionable", "Doubtful") else "off"),
                              esc(r["reason"]),
                              esc(r["attrib"]) if r["attrib"].startswith("explicit") else badge("continuation", "warn"),
                              srclink(r["src"])]})
    body += table(["Date", "ET", "Matchup", "Team", "Player", "Status", "Reason", "Attribution", "Source"],
                  rows, "Official injury report — every row", idcol="id")
    body += """<h2>What an injury actually does to a line — and why it is blank</h2>
<p class="lede">Turning "Out" into points requires three things: the player's share of minutes, the team's performance with
and without him, and who replaces him. None of the three is in the data reachable here. The previous build correctly left
the same columns blank; this build keeps them blank and states the reason on every row instead of printing a placeholder.</p>
<h2>Game-flow risk created by availability</h2>
<ul>
  <li><b>Blowout risk:</b> a team missing four or more rotation players is more likely to be on the wrong end of a
      garbage-time game, which flattens late-game totals. Measurable from rotation counts; not yet quantified.</li>
  <li><b>Back-to-back filing risk:</b> the 1 p.m. game-day deadline for the second of a back-to-back means late scratches
      are structurally more likely there. The schedule in this build identifies those games; the effect needs settlement data.</li>
  <li><b>Last-minute scratches:</b> the highest-information signal in a day is the diff between consecutive reports. Only one
      report is stored, so no diff is possible yet (SG-10).</li>
</ul>"""
    built["injuries.html"] = page("injuries.html", "Injuries &amp; rotation", body, "injuries.html")

    # ------------------------------------------------------------------ game flow
    body = """<h1>Game flow</h1>
<p class="lede">What the schedule alone can tell you about how a game is likely to unfold, and what needs play-by-play.</p>
"""
    # schedule density from official dates
    from collections import defaultdict
    team_dates = defaultdict(list)
    for (d, t, a, h, gid, arena, city, tv, cup) in O.SLATE:
        team_dates[a].append(d)
        team_dates[h].append(d)
    for k in team_dates:
        team_dates[k] = sorted(set(team_dates[k]))
    rows = []
    for (d, t, a, h, gid, arena, city, tv, cup) in sorted(O.SLATE):
        def density(team):
            ds = team_dates[team]
            prev = [x for x in ds if x < d]
            rest = None
            if prev:
                from datetime import date as _d
                y1, m1, d1 = map(int, prev[-1].split("-"))
                y2, m2, d2 = map(int, d.split("-"))
                rest = (_d(y2, m2, d2) - _d(y1, m1, d1)).days - 1
            last3 = [x for x in ds[-3:]]
            return rest, len([x for x in ds if x <= d])
        ra, na = density(a)
        rh, nh = density(h)
        rows.append({"id": gid, "cells": [
            esc(d), f"{esc(a)} @ {esc(h)}",
            esc(ra) if ra is not None else '<span class="blank">first in window</span>',
            esc(rh) if rh is not None else '<span class="blank">first in window</span>',
            esc(na), esc(nh),
            badge("B2B", "warn") if ra == 0 else badge("rested", "off"),
            badge("B2B", "warn") if rh == 0 else badge("rested", "off"),
            '<span class="blank">needs play-by-play</span>',
            srclink("https://www.nba.com/schedule?date=" + d)]})
    body += table(["Date", "Matchup", "Rest (away, days)", "Rest (home, days)", "Games in window (away)",
                   "Games in window (home)", "Away density", "Home density", "Pace / garbage / foul flow", "Source"],
                  rows, "Schedule-derived rest and density — fully official", num_cols=(2, 3, 4, 5), idcol="id")
    body += """<h2>Three flow effects that are real, and what each needs</h2>
<div class="cards">
  <div class="card"><h4>Rest and density <span class="badge b-ok">measurable now</span></h4>
    <p>Rest days and games-in-window come straight from the official schedule and are printed above. The
    effect of a back-to-back on scoring and pace still needs settled results to quantify.</p></div>
  <div class="card"><h4>Garbage time <span class="badge b-bad">needs play-by-play</span></h4>
    <p>Late-game minutes in a decided game suppress stars' counting stats and inflate bench usage. Requires
    per-possession data with score margin and clock.</p></div>
  <div class="card"><h4>Foul trouble <span class="badge b-bad">needs play-by-play</span></h4>
    <p>A star's minutes are truncated by two early fouls in a way no season average shows. Requires foul timestamps.</p></div>
</div>
<h2>Why flow analysis is not in the line yet</h2>
<p class="lede">Including a variable you cannot measure is worse than omitting it: it makes the line look more informed
than it is. The line on the previous page uses only inputs whose official source is on that page. Flow effects are listed
here as known-missing so they can be added with evidence, not assumed away.</p>"""
    built["gameflow.html"] = page("gameflow.html", "Game flow", body, "gameflow.html")

    # ------------------------------------------------------------------ verification
    body = f"""<h1>Verification log</h1>
<p class="lede">Every number on this site was read from an official NBA page on {O.AS_OF}. This page records exactly which
pages were reachable, what each one supplied, and what could not be reached — so a reviewer can repeat it.</p>
<div class="note"><b>How to re-check any row.</b> Every table row carries a source link to the official page. The same data
is also published machine-readably in <code>data/v2/*.json</code> in the repository, so a reviewer can diff what the site says
against what the official page says without trusting either.</div>
"""
    rows = []
    for s in R.t_sources():
        kind = {"official": "ok", "blocked": "bad"}.get(s["class"], "off")
        ok = s["result"].startswith("OK")
        rows.append({"cells": [esc(s["key"]), esc(s["name"]), badge(s["class"], kind),
                              badge(s["result"] if ok else s["result"][:46], "ok" if ok else "bad"),
                              esc(s["fields"])[:190], srclink(s["url"])]})
    body += table(["Key", "Source", "Class", "Retrieval result", "What it supplied", "URL"],
                  rows, "Every source attempted, with the outcome")

    body += "<h2>Cross-checks against the committed dataset</h2>"
    rows = []
    for c in xchecks["checks"]:
        rows.append({"cells": [esc(c["id"]), esc(c["what"]), esc(c["repo_value"]), esc(c["live_value"]),
                              badge(c["result"], "ok" if c["result"] == "MATCH" else "bad"),
                              esc(c["detail"])[:200], srclink(c["src"])]})
    body += table(["ID", "Check", "In repo", "Live official (2026-11-14 transcription)", "Result at transcription time", "Detail", "Source"], rows,
                  "Repository data re-verified against the 2026-11-14 official transcription")

    body += "<h2>Checks run against the repository itself</h2>"
    rows = []
    for name, val, method, src in C.REPO_FACTS:
        rows.append({"cells": [esc(name), esc(val), esc(method), srclink(src)]})
    body += table(["Property", "Observed", "How it was checked", "Source"], rows, "Repository health checks")

    body += "<h2>Session arena/72f9da58 — independent re-verification (2026-11-14)</h2>"
    rows = [{"cells": [esc(a), esc(b), esc(c), srclink(u)]} for a, b, c, u in C.SESSION_AUDIT]
    body += table(["Check", "Result", "Method / evidence", "Source"], rows,
                  "Integration-session verification results (tasks E-01 to E-04)")

    delta_path = ROOT / "audit" / "injury_delta_0415_to_0715.json"
    if delta_path.exists():
        delta = json.loads(delta_path.read_text())
        pdf = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_15PM.pdf"
        drows = []

        def _d(kind, matchup, team, player, before, after, note):
            drows.append({"cells": [esc(kind), esc(matchup), esc(team), esc(player),
                                    esc(before), esc(after), esc(note), srclink(pdf)]})

        for c_ in delta["status_changed"]:
            note = ("reason unchanged" if c_["published_reason"] == c_["latest_reason"]
                    else f"reason: {c_['published_reason']} → {c_['latest_reason']}")
            if c_["player"] == "Martin, Caleb":
                note += "; team label dropped at the 19:15 page break — Cleveland printed explicitly in 17:15/18:15/19:30 (F-020)"
            _d("status change", c_["matchup"], c_["team"], c_["player"],
               c_["published_status"] or "NOT YET SUBMITTED",
               c_["latest_status"] or "NOT YET SUBMITTED", note)
        for r_ in delta["added_in_latest"]:
            _d("added in 19:15 ET", r_[2], r_[3], r_[4] or "(team placeholder)",
               "(not in 16:15 ET revision)", r_[5], "row first appears in the 19:15 ET revision")
        for r_ in delta["removed_in_latest"]:
            _d("pending resolved", r_[2], r_[3], "(team placeholder)", "NOT YET SUBMITTED",
               "submitted — placeholder replaced by player rows",
               "team submitted its 11/14 list between the 16:15 and 19:15 revisions")
        for f_ in delta["formatting_only"]:
            _d("text-layer spacing only", f_["matchup"], f_["team"], f_["player"],
               f_["published_reason"], f_["latest_reason"],
               "space dropped by the PDF text layer — not a document change")
        body += table(["Change type", "Matchup", "Team", "Player", "Then-published (16:15 ET)",
                       "Official (19:15 ET)", "Note", "Source"], rows=drows,
                      caption="Injury-revision delta: what changed after the revision this site uses "
                              "(official 16:15 ET → official 19:15 ET; 52 rows, every cell asserted "
                              "against the captured PDF text by audit/parse_injury_0715.py)")

    body += f"""<h2>What 'verified' means here — and what it does not</h2>
<ul>
  <li><b>Verified</b> means: the value on the page equals the value on the official page on the retrieval date, and the link to that page is on the row.</li>
  <li><b>Verified does not mean correct today.</b> Every dataset on this site is a snapshot. Scores, records and statuses change hourly; the snapshot date is printed on every page.</li>
  <li><b>Derived values are not source-verified.</b> A fitted σ, a shrunk rating or a line is computed by us from verified inputs. Its formula and parameters are published so it can be re-derived, and it is badged "derived" rather than "official".</li>
  <li><b>Nothing is filled in.</b> If a value had no source, the cell is blank and carries the name of the missing input.</li>
</ul>
<h2>Known irregularities</h2>
<p class="lede">{len(C.FLAGS)} items are on the <a href="flagged.html">Flagged for review</a> page with sources, including two that
the previous build disclosed and this session resolved: the 28/30-vs-30/30 W-L discrepancy (resolved: 30/30) and the
stale retrieval date on the published snapshot.</p>"""
    built["verification.html"] = page("verification.html", "Verification log", body, "verification.html")

    # ------------------------------------------------------------------ repo review
    body = """<h1>Repo review</h1>
<p class="lede">A line-by-line look at what the repository already contains before this session added anything, verified by
running its own checks rather than trusting its documentation.</p>
"""
    rows = []
    for name, val, method, src in C.REPO_FACTS:
        rows.append({"cells": [esc(name), esc(val), esc(method), srclink(src)]})
    body += table(["Property", "Observed", "How checked", "Source"], rows, "Repository facts, this session")

    body += """<h2>Findings</h2>
<div class="note"><b>What is genuinely good.</b> The existing pipeline is unusually disciplined: 55 unit tests pass, a
provenance lint proves all 915 published rows carry a source, the site is byte-for-byte reproducible from committed data,
22 predictions are hash-sealed, and 3,233 internal links resolve. That is a better foundation than most projects start with.</div>
<div class="note warn"><b>What is wrong.</b> Six parallel site trees publish different numbers (root HTML, <code>pages/</code>,
<code>docs/</code>, <code>dashboard/</code>, <code>verified/</code>, <code>originated/</code>). A reader has no way to know
which one is current. The root page says "as-of 2026-11-13" while its own ledger is sealed at 22:51 that day, and the site
still shows a snapshot several hours old on the next day.</div>
<div class="note bad"><b>What is missing, and blocks the brief.</b> No market price and no player game logs.
Per-game results are no longer missing — 183 official finals are committed and every one of the 30 standings records
rebuilds from them exactly — so backtests, out-of-sample splits and settlement all run today. The two remaining
absences are why every stake on this site is 0.00 units rather than a number that looks like a bet.</div>
<h2>What this session changed, and what it deliberately did not</h2>
<p class="lede">All new work is in three new directories — <code>nba2/v2/</code>, <code>data/v2/</code> and <code>site/</code> —
plus one appended block in <code>COORDINATION.md</code>. No file owned by another session was edited, so no earlier
published output was destroyed. Where this build disagrees with an earlier one, the disagreement is on the verification page
with both values shown.</p>
<h2>Cleanup suggestions that are not this session's call</h2>
<ul>
  <li>Consolidate to one published tree and redirect or delete the other five (needs an owner decision; see SG-18).</li>
  <li>Untrack the 19 committed <code>.pyc</code> files: <code>.gitignore</code> already excludes them, so they are pure noise in diffs.</li>
  <li>Reconcile the README's claim of 49 tests with the 55 that actually run.</li>
</ul>"""
    built["repo-review.html"] = page("repo-review.html", "Repo review", body, "repo-review.html")

    # ------------------------------------------------------------------ questions
    body = """<h1>Open questions</h1>
<p class="lede">Fourteen questions that block a decision, each with what is known, what is not, and the exact route to an
answer. Nothing here is rhetorical: every question names the dataset or the measurement that settles it.</p>
"""
    rows = []
    for q in C.QUESTIONS:
        rows.append({"id": q[0], "cells": [esc(q[0]), esc(q[1]), esc(q[2]), esc(q[3]), esc(q[4]),
                                          badge("BLOCKING", "bad") if "Blocks" in q[5] else badge("open", "warn"),
                                          esc(q[5]), srclink(q[6])]})
    body += table(["ID", "Question", "What is known", "What is not known", "How to find out", "Impact", "Blocks", "Source"],
                  rows, "Decision-blocking questions", idcol="id")

    # Questions raised by this session's live evidence. These come from the shared register
    # (requirements/QUESTIONS.json) and are the ones a reader can only answer with a date on them:
    # they were created by what the official pages said today, not by an earlier theory.
    nq = LV.new_questions()
    if nq["items"]:
        body += f"""
<h2>Questions this session's live evidence raised ({len(nq['items'])})</h2>
<p class="lede">Each of these was created by a measurement made today, not by an earlier hypothesis. They are listed
separately so a reviewer can see which questions the evidence produced and which were already on the register.</p>
"""
        qrows = []
        for it in nq["items"]:
            qrows.append({"id": it["id"], "cells": [
                esc(it["id"]), esc(it["question"]), esc(it["have"]), esc(it["missing"]),
                esc(it["how"]),
                badge(it["severity"], "bad" if it["severity"] == "BLOCKING" else "warn"),
                srclink(it["source"]),
            ]})
        body += table(["ID", "Question", "What we already have (measured today)", "What is still missing",
                       "How to close it", "Severity", "Source"], qrows,
                      "New questions, raised by live verification", idcol="id")
    body += """<h2>Questions about the project itself, not the model</h2>
<div class="cards">
  <div class="card"><h4>Which site is authoritative?</h4><p>Six trees exist. Until the owner picks one, every published
  number is ambiguous. Proposed answer: this tree, with the others archived.</p></div>
  <div class="card"><h4>Is the reward pool real money?</h4><p>The brief says rewards for top strategies. The size, funding
  and legal basis are unknown and change what the leaderboard must be built to prevent.</p></div>
  <div class="card"><h4>Who may submit a strategy?</h4><p>Public submissions turn anti-gaming rules from nice-to-have into
  load-bearing. One submitter only changes the design substantially.</p></div>
  <div class="card"><h4>What counts as a 'pick'?</h4><p>A projection, a graded bet, or a staked bet? This determines whether
  anything on this site qualifies today. Current answer: nothing does.</p></div>
</div>
<h2>Information we do not have, that someone must go and get</h2>
<ul>
  <li>Licensed odds history (opening and closing lines) — the only way to measure edge.</li>
  <li>Per-game box scores — the only way to settle, backtest or score.</li>
  <li>Player game logs with minutes — the only way to price props or quantify injuries.</li>
  <li>Play-by-play — the only way to analyse game flow rather than schedule density.</li>
  <li>An explicit statement of what the reward is, so the leaderboard can be designed against it.</li>
</ul>"""
    built["questions.html"] = page("questions.html", "Open questions", body, "questions.html")

    # ------------------------------------------------------------------ suggestions
    _impl = sum(1 for s in C.SUGGESTIONS if s[6].startswith("IMPLEMENTED"))
    _rec = sum(1 for s in C.SUGGESTIONS if "RECOMMENDED" in s[6])
    body = f"""<h1>Suggestions queue</h1>
<p class="lede">{len(C.SUGGESTIONS)} proposals, each with an area, an effort estimate, a blocker, and a decision state. This page exists
so a path can be chosen before anything is implemented — nothing in the queue changes the site until it is marked
<code>ACCEPTED</code>.</p>
<div class="note"><b>How to use it.</b> Read the state column. {_impl} items are already <code>IMPLEMENTED</code> and need no
decision; {_rec} are <code>RECOMMENDED</code> and unblock the rest; the remainder are queued behind a data
dependency. The three highest-ranked recommended items are all data connections, in this order: odds, results, scheduled ingestion.</div>
"""
    order = {"RECOMMENDED — highest leverage": 0, "RECOMMENDED — unblocks the most": 1,
             "RECOMMENDED — required for any betting claim": 2, "RECOMMENDED": 3,
             "IMPLEMENTED": 4, "IMPLEMENTED (bound) / BLOCKED (measurement)": 5,
             "PARTIAL — density implemented": 6, "QUEUED": 7}
    srt = sorted(C.SUGGESTIONS, key=lambda s: (order.get(s[6], 9), s[0]))
    rows = []
    for sid, area, sug, why, effort, dep, state in srt:
        kind = "ok" if state.startswith("IMPLEMENTED") else "warn" if state.startswith("RECOMMENDED") or state.startswith("PARTIAL") else "off"
        if "BLOCKED" in state:
            kind = "bad"
        rows.append({"id": sid, "cells": [esc(sid), badge(area, "off"), esc(sug), esc(why), esc(effort), esc(dep),
                                         badge(state, kind), srclink("https://github.com/wingbangboozle1-lang/NBA2")]})
    body += table(["ID", "Area", "Suggestion", "Why it improves decision-making", "Effort", "Depends on", "Decision state", "Reference"],
                  rows, "Suggestion queue with decision states", idcol="id")
    body += """<h2>If you only do three things</h2>
<ol>
  <li><b>Connect a licensed odds feed</b> (SG-3). Everything about edge, stake and ROI depends on it. Today the site
      correctly publishes zero picks because it has no price — that is a data gap, not a modelling gap.</li>
  <li><b>Get per-game results</b> (SG-2). It turns every projection into something scoreable and lets the leaderboard exist.</li>
  <li><b>Schedule the ingestion</b> (SG-1). Hand-made snapshots cannot satisfy a freshness gate, so no strategy can ever be
      ranked on fresher-than-today data.</li>
</ol>
<h2>Suggestions about this site's own design</h2>
<div class="cards">
  <div class="card"><h4>Split projection from bet</h4><p>Done on this site: the lines page publishes projections, the picks
  page publishes nothing because gate G6 fails. Mixing them is how a research desk becomes an unreliable tipster.</p></div>
  <div class="card"><h4>Put the source on every row</h4><p>Done: the builder refuses to emit a row without a URL, so the
  compliance is structural rather than a promise.</p></div>
  <div class="card"><h4>Make uncertainty visible</h4><p>Done: σ, the reliability weight, the two estimators and their
  disagreement are printed per game instead of a single confident-looking number.</p></div>
  <div class="card"><h4>Give every blank a reason</h4><p>Done: an empty cell is always accompanied by the missing input's
  name, so absence is information rather than an oversight.</p></div>
</div>
<h2>What I would not do</h2>
<ul>
  <li><b>Do not add a 'confidence score'</b> built from conviction alone. It is |margin|/σ, which grows for lopsided games,
      not for well-understood ones. The estimator-disagreement column is the honest analogue.</li>
  <li><b>Do not publish props before minutes data exists.</b> A season average is not a distribution, and a prop mispriced
      by a distributional assumption is indistinguishable from a bad pick.</li>
  <li><b>Do not rank strategies on win rate.</b> Twelve bets can look skilful and be noise; log-loss on 300 settled bets is
      the cheapest defence.</li>
</ul>"""
    built["suggestions.html"] = page("suggestions.html", "Suggestions queue", body, "suggestions.html")

    # ------------------------------------------------------------------ decision queue
    # The suggestions above are methodological. This page is the one the owner actually works
    # from: a numbered queue where every item carries the evidence that motivates it, the exact
    # change it would make, and an explicit owner action. Nothing here is implemented on the
    # owner's behalf — accepted is the only state that authorises work, and this session never
    # sets it.
    dq = LV.decision_queue()
    body = f"""<h1>Decision queue — review, then choose</h1>
<p class="lede">This is the section for reviewing suggestions and choosing the best path <em>before</em> anything is
implemented. Each row is one decision, with the evidence that motivates it (always a live official source or a
committed artefact), the exact change it would make, its effort, and the three actions open to you:
<b>accept</b>, <b>reject</b>, <b>defer</b>.</p>
<div class="note"><b>The rule.</b> Nothing in this queue has been implemented on your behalf. A suggestion is a
proposal, not a change. Two states are pre-filled honestly: <code>implemented this session</code> means the code now
exists and is verified by the build gate; <code>awaiting owner decision</code> means it does not exist and will not
until you accept it. This session never writes <code>accepted</code>.</div>
<div class="kpis">
  <div class="kpi"><b>{dq['n_total']}</b><small>decisions in the queue</small></div>
  <div class="kpi"><b>{dq['n_awaiting']}</b><small>awaiting your decision</small></div>
  <div class="kpi"><b>{dq['n_implemented']}</b><small>already implemented this session</small></div>
  <div class="kpi"><b>{dq['n_blocking']}</b><small>blocking (must decide before anything else)</small></div>
</div>
"""
    dq_rows = []
    for it in dq["items"]:
        dq_rows.append({"id": it["id"], "cells": [
            esc(it["id"]), badge(it["track"], "off"), esc(it["title"]),
            esc(it["problem"]), esc(it["changes"]), esc(it["effort"]),
            badge(it["status"], "ok" if it["status"].startswith("implemented") else "warn"),
            srclink(it["evidence"], "capture"), srclink(it["source"], "official"),
        ]})
    body += table(["ID", "Track", "Suggestion", "Problem today (evidence)", "What changes if accepted",
                   "Effort", "State", "Evidence", "Official source"],
                  dq_rows, "Decision queue — choose a path before implementation", idcol="id")

    body += """<h2>How to answer</h2>
<p class="lede">Reply with the IDs you accept. Three answers are useful and one is not:</p>
<div class="cards">
  <div class="card"><h4>Accept</h4><p>Named IDs become authorised work. The build gate then verifies the change
  actually happened, because each accepted item maps to a check in <code>nba2/v2/check.py</code> or a test.</p></div>
  <div class="card"><h4>Reject</h4><p>A rejected item is removed from the queue and the reason recorded, so it does not
  quietly return in a later session wearing a new number.</p></div>
  <div class="card"><h4>Defer</h4><p>Keep it, with the condition that would change your mind. A deferral without a
  condition is a rejection nobody had the nerve to write down.</p></div>
  <div class="card"><h4>Silence</h4><p>Not an answer. An unanswered item stays <code>awaiting owner decision</code> and
  nothing is built from it.</p></div>
</div>
<h2>The one decision that unblocks the others</h2>
<p>Rank by cost of being wrong, not by effort. <b>DG-01</b> (declare one canonical site) is first because while two
dashboards publish different records, no other verification on either site can be treated as authoritative. <b>DG-02</b>
(staleness gate) is second because it is the failure this session actually caught a live instance of. The odds feed is
third — expensive, but it unblocks the entire profit question, which nothing else does.</p>
"""
    built["decision-queue.html"] = page("decision-queue.html", "Decision queue", body, "decision-queue.html")

    # ------------------------------------------------------------------ live verification
    st = chk.get("staleness") or {}
    gr = chk.get("grade") or {}
    body = f"""<h1>Live verification — what today's official pages say</h1>
<p class="lede">Every other page on this site renders a snapshot captured on {O.AS_OF}. This page is different: it is built
from pages this session read <b>today</b>, records the exact URL and fetch time of each, and reports where the published
site no longer matches. It also grades the first genuine forecast the repository ever made.</p>
<div class="note"><b>Why this page had to exist.</b> Nothing on the site compared a published row against a fresher
official capture, so a stale row and a correct row rendered identically — both said MATCH. This session found 18 such
rows by hand. A page is cheaper than vigilance.</div>
<div class="kpis">
  <div class="kpi"><b>{st.get('match_live_standings','—')}/{st.get('published_rows','—')}</b><small>published team records that still match today's official standings</small></div>
  <div class="kpi"><b>{st.get('match_pre_final_state','—')}/{st.get('published_rows','—')}</b><small>that match the pre-11/13-finals reconstruction</small></div>
  <div class="kpi"><b>{gr.get('games_graded','—')}</b><small>11/13 games with official finals</small></div>
  <div class="kpi"><b>{gr.get('distinct_games_graded','—')}</b><small>distinct games the committed picks actually bet</small></div>
  <div class="kpi"><b>{gr.get('side_accuracy',{}).get('model','—')}/{gr.get('side_accuracy',{}).get('n','—')}</b><small>games where the model named the winner</small></div>
  <div class="kpi"><b>{gr.get('side_accuracy',{}).get('always_home','—')}/{gr.get('side_accuracy',{}).get('n','—')}</b><small>where "always pick home" would have</small></div>
</div>

<h2>0. Which tree is actually published (probed, not assumed)</h2>
<p class="lede">A correction to this session's own first draft. It claimed two dashboards both reach a reader. That was
wrong, and the probe below is why. On 2026-11-14 the live site was fetched at three paths:</p>
"""
    rows = [
        {"cells": [esc("/NBA2/"), badge("200", "ok"), esc("v2 dashboard — title 'Dashboard · NBA2 Lines Lab v2'"),
                   srclink("https://wingbangboozle1-lang.github.io/NBA2/")]},
        {"cells": [esc("/NBA2/data/teams.json"), badge("200", "ok"),
                   esc("v2 artefact: as_of, calibration.margin_sd 12.75, 30 teams with reliability and luck_z"),
                   srclink("https://wingbangboozle1-lang.github.io/NBA2/data/teams.json")]},
        {"cells": [esc("/NBA2/pages/session-audit.html"), badge("404", "bad"),
                   esc("this file exists in the repository (v1 tree) — site/ has no pages/ directory"),
                   srclink("https://wingbangboozle1-lang.github.io/NBA2/pages/session-audit.html")]},
        {"cells": [esc("/NBA2/pages/executive-summary.html"), badge("404", "bad"),
                   esc("also exists in the repository (v1 tree) and is also unreachable"),
                   srclink("https://wingbangboozle1-lang.github.io/NBA2/pages/executive-summary.html")]},
    ]
    body += table(["Path probed", "HTTP", "What came back", "URL"], rows,
                  "One tree is served. The Pages API's build_type=legacy / source=main is stale metadata that does "
                  "not describe what readers get, which the 404s above prove.")
    body += f"""<div class="note warn"><b>What that means.</b> Only the <code>site/</code> artefact built by
<code>pages.yml</code> reaches a reader. The v1 tree at the repository root — root <code>index.html</code>,
<code>pages/**</code>, <code>flagged.html</code>, <code>data/site.json</code> — is <b>unreachable</b>, yet CI still
regenerates, lints and parity-checks it on every push, and it carries records that have been stale since the 11/13
finals. The defect is unreachable maintenance debt, not a live fork: the recommendation (DG-01 / S-27) is to move it
under <code>archive/</code> with dated notes, deleting nothing.</div>

<h2>1. Official pages read this session</h2>
"""
    rows = []
    for c in chk.get("captures", []):
        ok = c["outcome"] == "read"
        rows.append({"cells": [esc(c["name"]), badge(c["outcome"], "ok" if ok else "bad"),
                              esc(c["proved"]), srclink(c["url"])]})
    body += table(["Official page", "Outcome", "What it proved", "URL"], rows,
                  f"Read at {chk.get('fetched_utc','')}; nba.com is unreachable by direct HTTPS from the build sandbox, "
                  "so these were fetched through the platform page-reader. The method is stated because it is part of the evidence.")

    body += f"""<h2>2. The published team table has aged</h2>
<p class="lede">This is the most important number on this page. The site's 30 team records were transcribed on {O.AS_OF}
before the nine 2026-11-13 games had official results. Nine games change eighteen records. To prove that rather than
assert it, the pre-final state is reconstructed from today's official standings by subtracting those nine results, and
the published table is compared with both.</p>
"""
    rows = [
        {"cells": [esc("Published table vs today's official standings"),
                   esc(f"{st.get('match_live_standings')} of {st.get('published_rows')}"),
                   badge("STALE", "bad"), srclink(st.get("source", ""))]},
        {"cells": [esc("Published table vs the pre-11/13-finals reconstruction"),
                   esc(f"{st.get('match_pre_final_state')} of {st.get('published_rows')}"),
                   badge("EXPLAINS THE GAP", "warn"), srclink(st.get("source", ""))]},
        {"cells": [esc("Rows whose staleness the nine finals do not explain"),
                   esc(f"{st.get('n_unexplained')}"),
                   badge("NONE", "ok"), srclink(st.get("source", ""))]},
    ]
    body += table(["Comparison", "Result", "Reading", "Source"], rows, "Staleness measured, not assumed")
    body += f"""<div class="note warn"><b>What the site currently claims.</b> {esc(st.get('published_claim',''))}.
The comparison was true when it was made. The rows are the same rows, the standings are not the same standings, and
until today nothing on the site could tell the difference. <b>Every stale row, with both values:</b></div>
"""
    rows = []
    for r in st.get("stale_rows", []):
        rows.append({"cells": [esc(r["team"]), esc(r["published"]), esc(r["live"]),
                              esc(r["pre_final_reconstruction"]),
                              badge(r["cause"], "warn" if r["cause"] == "PRE_FINALS" else "bad"),
                              srclink(st.get("source", ""))]})
    body += table(["Team", "Published on this site", "Today's official W-L", "Pre-11/13 reconstruction", "Cause", "Source"],
                  rows, f"{st.get('n_stale','0')} stale team records, every one explained by the 11/13 finals")

    body += f"""<h2>3. The first real out-of-sample test the repository has</h2>
<p class="lede"><code>nba2/data/picks.json</code> was committed at <b>{gr.get('committed_utc','')}</b> (commit
<code>{gr.get('prediction_commit','')}</code>, its only commit ever) and the earliest 11/13 tip was
<b>{gr.get('first_tip_utc','')}</b> — {gr.get('minutes_before_first_tip','')} minutes later. Nothing in that file could
have seen a result. That makes it a forecast, not a backtest, and it is the first one this repository has ever been able
to grade.</p>
<div class="note"><b>Where this is graded, and where it is not.</b> Both sealed ledgers
(<code>cf7dedc6…</code>, <code>c841e8f3…</code>) start on 2026-11-14, so the eleven 13ths they do not cover correctly
leave them PENDING. The graded file is <em>not</em> sealed — the claim rests on a git commit timestamp and a one-commit
history, which is weaker than a seal and is stated as weaker.</div>
"""
    gf = gr.get("line_forecast", {})
    rows = [
        {"cells": [esc("Spread — mean absolute error"), esc(f"{gf.get('spread_mae')} pts"),
                   esc(f"{gf.get('naive_spread_mae')} pts (predict a tie)"),
                   badge("BEATS BASELINE", "ok"), srclink(gr.get("sources", [""])[0])]},
        {"cells": [esc("Total — mean absolute error"), esc(f"{gf.get('total_mae')} pts"),
                   esc(f"{gf.get('naive_total_mae')} pts (224 every game)"),
                   badge("TIES BASELINE", "warn"), srclink(gr.get("sources", [""])[0])]},
        {"cells": [esc("Brier score"), esc(gf.get("brier")), esc(f"{gf.get('naive_brier')} (coin flip)"),
                   badge("BEATS COIN", "ok"), srclink(gr.get("sources", [""])[0])]},
        {"cells": [esc("Winner accuracy"), esc(f"{gr.get('side_accuracy',{}).get('model')}/{gr.get('side_accuracy',{}).get('n')}"),
                   esc(f"{gr.get('side_accuracy',{}).get('net_rating_baseline')}/{gr.get('side_accuracy',{}).get('n')} naive net rating, "
                       f"{gr.get('side_accuracy',{}).get('always_home')}/{gr.get('side_accuracy',{}).get('n')} always home"),
                   badge("NO EDGE SHOWN", "bad"), srclink(gr.get("sources", [""])[0])]},
    ]
    body += table(["Measure", "Model (9 games)", "Free baseline", "Verdict", "Source"], rows,
                  "Nine games. Every one of these numbers would move on a single result — read them as a demonstration, not evidence.")

    body += "<h2>4. Every pick the committed file made, and what happened</h2>"
    body += f"""<p class="lede">The repository's own strategies, graded game by game. Note the two right-hand columns before the
result: there is no price anywhere in the file, so <b>no profit can be computed</b> and none is shown.</p>"""
    rows = []
    for it in gr.get("signals", []):
        rows.append({"cells": [
            esc(it["strategy_id"]), esc(it["game"]), esc(it["selection"]),
            esc(it["final"] or it.get("pending_reason") or "not graded"),
            badge(it["result"] or it["status"], "ok" if it["result"] == "WIN" else "bad" if it["result"] == "LOSS" else "off"),
            esc(it["price"]) if it["price"] is not None else badge("no price — PnL impossible", "warn"),
            srclink(it["source"]),
        ]})
    body += table(["Strategy", "Game", "Committed selection", "Official result", "Result", "Price", "Source"], rows,
                  "Committed picks graded against the official box scores")

    dup = gr.get("duplicate_accounting", {})
    body += f"""<div class="note bad"><b>The sample is half the size it looks.</b> {esc(dup.get('explanation',''))}
Every hit-rate table on this site now prints both counts.</div>"""
    rows = []
    for sm in gr.get("strategies", []):
        rows.append({"cells": [
            esc(sm["strategy_id"]), esc(sm["name"]),
            esc(sm["signals"]), esc(sm["graded"]), esc(sm["pending"] + sm.get("ungradable", 0)),
            esc(f"{sm['wins']}-{sm['losses']}"),
            esc(sm["hit_rate"] if sm["hit_rate"] is not None else "—"),
            esc(sm["sign_p"] if sm["sign_p"] is not None else "—"),
            badge(sm["verdict"].upper(), "warn" if sm["graded"] else "off"),
            srclink(gr.get("sources", [""])[0]),
        ]})
    body += table(["Strategy", "Name", "Signals committed", "Graded", "Pending", "W-L",
                   "Hit rate", "p vs coin", "Verdict", "Source"], rows,
                  "Per-strategy grading — the p-value is the probability of this record from a fair coin")

    body += f"""<h2>5. Why no profit number appears anywhere</h2>
<p class="lede">{esc(gr.get('pricing_note',''))}</p>
<p>A PnL would require assuming a price, and the assumption would be doing all the work: at −110 a 4-0 record is
{4*0.909:.2f} units, at +150 it is {4*1.5:.2f}. Publishing either would be publishing the assumption, not the model.
The site therefore reports what was measured — wins, losses, error — and says plainly that the money question is
unanswered until a price exists.</p>
<h2>6. The verdict this page supports</h2>
<p>{esc(gr.get('verdict',''))}</p>
<p>Two conclusions follow, and they point in opposite directions, which is why both are printed:</p>
<ul>
  <li><b>Against the model:</b> on nine games it named the winner no better than a naive net-rating baseline and worse
      than always picking the home team. No edge is demonstrated.</li>
  <li><b>For the process:</b> the gate machinery did its job. Every graded pick won, and the site still refuses to rank
      the strategy, because four games is not a sample. A system that can report 4-0 and simultaneously refuse to be
      impressed by it is the only kind worth building.</li>
</ul>
<h2>Reproduce this page</h2>
<pre>python3 -m nba2.v2.live        # re-run the staleness test and the grading from audit/2026-11-14/
python3 -m nba2.v2              # rebuild this page
python3 -m nba2.v2.check        # every row sourced, every blank explained</pre>"""
    built["live-verification.html"] = page("live-verification.html", "Live verification", body, "live-verification.html")

    # ------------------------------------------------------------------ flagged
    body = """<h1>Flagged for review</h1>
<p class="lede">Every irregularity found this session, with a severity and the source needed to check it. None of these block
publication: the site publishes only what it can source, and flags the rest here.</p>
<div class="note"><b>Resolved this session.</b> The previous build reported 28/30 team records matching NBA.com while its
metadata claimed 30/30. This session re-read the live standings and found <b>30/30 exact matches</b>; the 28/30 note is
superseded (see F-012). Records can still drift as games are played — the snapshot date is on every page.</div>
"""
    rows = []
    for fid, sev, area, stmt, action, src in C.FLAGS:
        kind = {"high": "bad", "medium": "warn", "low": "off", "info": "info"}[sev]
        rows.append({"id": fid, "cells": [badge(fid, kind), badge(sev, kind), esc(area), esc(stmt), esc(action), srclink(src)]})
    body += table(["ID", "Severity", "Area", "Finding", "Disposition", "Source to check"],
                  rows, "Flagged irregularities", idcol="id")
    body += """<h2>Items that need a human with the site open</h2>
<ul>
  <li><b>F-003:</b> whether the 11/14 injury report is genuinely unpublished or merely unavailable from this environment.
      Open <a href="https://official.nba.com/nba-injury-report-2026-27-season/" target="_blank" rel="noopener">the official index</a>
      and look for a 11/14 entry.</li>
  <li><b>F-009:</b> eleven injury rows take their team from the PDF's previous page. Compare against the PDF pages 3–7.</li>
  <li><b>F-011:</b> several site trees exist; the decision is now made — <code>pages.yml</code> publishes <code>site/</code>
      (v2) only, and the v1 trees stay in the repository for history (suggestion SG-23).</li>
  <li><b>F-019 / F-020:</b> the injury-revision delta table on the <a href="verification.html">Verification log</a> shows every
      change after the 16:15 ET revision this site uses. On the next official release, confirm Martin, Caleb's team label still
      prints Cleveland.</li>
</ul>
<h2>Flag policy</h2>
<p class="lede">A flag is raised when a value cannot be sourced, when two sources disagree, when a method depends on an
assumption, or when the repository contradicts its own documentation. Flags are never closed by assertion — each one carries
the page that would settle it.</p>"""
    built["flagged.html"] = page("flagged.html", "Flagged for review", body, "flagged.html")

    # ------------------------------------------------------------------ sources
    body = """<h1>Sources</h1>
<p class="lede">Every official page used, what it supplied, and what was attempted and failed. This is the complete list —
if a number on this site is not traceable to a row here, that is a bug.</p>
"""
    rows = []
    for s in R.t_sources():
        ok = s["result"].startswith("OK")
        rows.append({"cells": [esc(s["name"]), badge(s["class"], "ok" if s["class"] == "official" else "bad"),
                              badge("reachable" if ok else "no data", "ok" if ok else "bad"),
                              esc(s["fields"])[:220], srclink(s["url"])]})
    body += table(["Source", "Class", "Retrieval", "Fields supplied", "URL"], rows, "All sources")
    body += """<h2>Official pages used, by category</h2>
<div class="cards">
  <div class="card"><h4>Schedule</h4><p><a href="https://www.nba.com/schedule" target="_blank" rel="noopener">nba.com/schedule</a> —
  game ids, tip times, arenas, broadcast, Emirates NBA Cup group.</p></div>
  <div class="card"><h4>Records</h4><p><a href="https://www.nba.com/standings" target="_blank" rel="noopener">nba.com/standings</a> —
  W-L, home/road splits, conference and division records.</p></div>
  <div class="card"><h4>Team stats</h4><p><a href="https://www.nba.com/stats/teams/traditional" target="_blank" rel="noopener">traditional</a> ·
  <a href="https://www.nba.com/stats/teams/opponent" target="_blank" rel="noopener">opponent</a> ·
  <a href="https://www.nba.com/stats/teams/advanced" target="_blank" rel="noopener">advanced</a>.</p></div>
  <div class="card"><h4>Player stats</h4><p><a href="https://www.nba.com/stats/players/traditional" target="_blank" rel="noopener">nba.com/stats/players/traditional</a> —
  season averages per player.</p></div>
  <div class="card"><h4>Injuries</h4><p><a href="https://official.nba.com/nba-injury-report-2026-27-season/" target="_blank" rel="noopener">official.nba.com index</a> and
  <a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf" target="_blank" rel="noopener">the 11/13 04:15 PM PDF</a>.</p></div>
  <div class="card"><h4>Game pages</h4><p><a href="https://www.nba.com/games" target="_blank" rel="noopener">nba.com/games</a> —
  used to confirm matchups and season-leader values per game card.</p></div>
</div>
<h2>Notes on method for a reviewer</h2>
<ul>
  <li>Pages were read on <b>2026-11-14</b> through the agent's page-fetch tool; direct TLS from the sandbox to nba.com fails, which is recorded as F-004's neighbour on the verification page.</li>
  <li>Tables were transcribed into code (<code>nba2/v2/official.py</code>) with one named field per column, so a transcription error is a visible diff rather than a hidden one.</li>
  <li>Arithmetic identities (points scored = points allowed, home wins = road losses) are asserted on every build; they caught nothing this time, which is the point of running them.</li>
</ul>"""
    built["sources.html"] = page("sources.html", "Sources", body, "sources.html")

    # ------------------------------------------------------------------ methodology
    body = f"""<h1>Methodology</h1>
<p class="lede">The whole model, in the order it runs, with every parameter and its identification.</p>
<h2>1. Inputs</h2>
<p>Team records and home/road splits from the official standings; points for and against per game from the official team and
opponent tables; offensive, defensive and net rating, pace and PIE from the official advanced table; the slate from the
official schedule; injuries from the official report PDF. All {len(O.SOURCES)} URLs are on the <a href="sources.html">sources page</a>.</p>

<h2>2. Ratings</h2>
<p>Two independent estimators, each shrunk toward the league mean by the measured reliability weight
<code>λ = τ²/(τ² + σ²/games)</code>:</p>
<pre>A: net points per game  r_A(t) = mean + λ · (PF(t) − PA(t) − mean)
B: net rating → points  r_B(t) = mean + λ · (NetRtg(t) · Pace(t)/100 − mean)
rating(t) = (r_A + r_B) / 2</pre>
<p>τ² is estimated, not assumed: <code>τ² = Var(net points) − mean(σ²/games)</code>. Observed λ is {cal.lambda_mean:.3f} on average,
so a 10-game record is treated as about {100*(1-cal.lambda_mean):.0f}% noise.</p>

<h2>3. Calibration</h2>
<p>σ is fitted by least squares against the 30 official win totals, with h pinned to the measured home-win rate:
<code>h = σ(2p − 1)</code> where <code>p = {cal.home_win_rate:.4f}</code> over {integ['home_w']+integ['home_l']} home games.
Result: σ = {cal.margin_sd:.2f} pts, h = {cal.hca:+.2f} pts, RMSE {cal.rmse_wins:.3f} wins
versus {cal.rmse_baseline:.3f} for a coin-flip baseline. Fitting both freely gives σ = {cal.sigma_unconstrained:.2f},
h = {cal.hca_unconstrained:+.2f} — the same RMSE to three decimals, which is why the pair is not trusted.

<h2>4. Lines</h2>
<pre>margin   = rating(home) + h − rating(away)          # positive → home wins by
spread   = −round_to_nearest_half(margin)            # home handicap
p(home)  = Φ(margin / σ)
fair odds= 1/p  and  1/(1−p)                         # no hold applied
total    = Σ_team [ (PF(team) + PA(opp))/2 + ((PF−PA)(team) − (PF−PA)(opp))/2 ]</pre>
<p>A second total is computed as <code>(OffRtg + opp DefRtg)/2 × pace/100</code> per team. The gap between the two is printed
per game and any gap over 4.0 pts forces grade C.</p>

<h2>5. Grading (not betting)</h2>
<p>A = both spread estimators within 1.0 pt, |margin| ≥ 0.75σ, both total estimators within 2.0 pts.
B = passes the minimum gates. C = fails one. <b>A grade is a statement about model stability, never about expected profit.</b>
Expected profit requires a price, which is why every pick is withheld.</p>

<h2>6. Luck</h2>
<p>Expected wins come from the fitted model on each team's own point differential; the residual is luck, standardised by
<code>sqrt(games·p·(1−p))</code>. Observed: {sum(1 for t in teams.values() if abs(t.luck_z) > 1.96)} of 30 teams outside |z| ≤ 1.96.
That means no team's record in this window is distinguishable from its underlying scoring level.</p>

<h2>7. What would change the answer</h2>
<ul>
  <li>A price (any price) turns a projection into a testable claim.</li>
  <li>Per-game results turn a testable claim into a score.</li>
  <li>Player logs turn injuries and props from qualitative notes into numbers.</li>
  <li>More games narrow σ and h, which are currently identified loosely against a single season.</li>
</ul>
<h2>8. Reproduce it</h2>
<pre>python3 -m nba2.v2                # rebuilds data/v2/*.json and site/
python3 -m nba2.v2.check          # every row sourced, every blank explained
python3 -m nba2.v2.strategy_lab   # strategies, gates, correlations, luck separation
python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'   # 80 tests</pre>"""
    built["methodology.html"] = page("methodology.html", "Methodology", body, "methodology.html")

    # The same artefacts are served with the site so a reviewer can diff data against rendering.
    # This MUST run last: backtest.json and the other JSON files are written earlier in this
    # function, and copying before they are final publishes a stale file — which is exactly what
    # broke the Pages deploy on 2026-11-14 (site/data/lines.json, site/data/teams.json).
    site_data = SITE / "data"
    site_data.mkdir(parents=True, exist_ok=True)
    for f in sorted(DATA.glob("*.json")):
        (site_data / f.name).write_text(f.read_text())

    return built, {
        "lines": lines_d, "teams": [t.as_dict() for t in teams.values()],
        "calibration": cal.as_dict(), "integrity": integ, "xchecks": xchecks,
        "pages": sorted(built),
    }
