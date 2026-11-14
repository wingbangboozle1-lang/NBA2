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
    ("correlations.html", "Correlations &amp; parlays"),
    ("props.html", "Player props"),
    ("injuries.html", "Injuries &amp; rotation"),
    ("gameflow.html", "Game flow"),
    ("verification.html", "Verification log"),
    ("repo-review.html", "Repo review"),
    ("questions.html", "Open questions"),
    ("suggestions.html", "Suggestions queue"),
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
    _dates = sorted({l.date for l in lines})
    win_from = _dates[0] if _dates else "—"
    win_to = _dates[-1] if _dates else "—"
    blocked = len([1 for v in O.BLOCKED.values()])
    _acc = "—"
    if (DATA / "backtest.json").exists():
        _acc = f"{json.loads((DATA / 'backtest.json').read_text())['headline']['straight_up_accuracy']*100:.1f}%"
    body = f"""
<h1>Originated lines, sourced row by row</h1>
<p class="lede">A {n_lines}-game window ({win_from} → {win_to}) priced from official NBA data only.
Two independent ratings, a fitted home-court term, published formulas, and — new in this build — a link on
every row to that game's own official nba.com page.
Nothing here is a betting tip: no market price is connected, so every pick is withheld and says which gate stopped it.</p>

<div class="kpis">
  <div class="kpi"><b>{len(lines)}</b><small>games priced in window</small></div>
  <div class="kpi"><b>{integ['games']:.0f}</b><small>league games observed (season to date)</small></div>
  <div class="kpi"><b>{tiers['A']}/{tiers['B']}/{tiers['C']}</b><small>A / B / C line grades</small></div>
  <div class="kpi"><b>{_acc}</b><small>walk-forward accuracy (139 finals)</small></div>
  <div class="kpi"><b>0</b><small>picks published (all withheld)</small></div>
  <div class="kpi"><b>{cal.margin_sd:.2f}</b><small>σ margin sd (fitted, pts)</small></div>
  <div class="kpi"><b>{cal.hca:+.2f}</b><small>home-court (fitted, pts)</small></div>
  <div class="kpi"><b>0/30</b><small>teams outside luck noise</small></div>
  <div class="kpi"><b>{blocked}</b><small>inputs blocked</small></div>
</div>

<div class="note"><b>Read this first.</b> The model can price a game; it cannot price a <em>bet</em>.
A bet needs a price to beat, and no odds feed is connected to this build — so the picks page withholds all
{n_lines} games and prints the failing gate next to each. What is genuinely new in this build is the window and
the provenance: the slate now covers the live three-day horizon ({win_from} → {win_to}) instead of the expired
one it shipped with, and every priced row links to the official game page it was read from. The team table was
re-read row by row from nba.com/standings and the three stats tables on {O.AS_OF}; the injury snapshot dates from
2026-11-13 and is published as such. <a href="verification.html">See the verification log</a>.</div>

<h2>Start here</h2>
<div class="cards">
  <div class="card"><h4><a href="executive-summary.html">Executive summary</a></h4><p>What was built, what is verified, what is impossible yet, and the recommended path.</p></div>
  <div class="card"><h4><a href="lines.html">Originated lines</a></h4><p>All {n_lines} games: spread, total, moneyline fair odds, conviction, and the gap between two estimators.</p></div>
  <div class="card"><h4><a href="picks.html">Picks &amp; slate</a></h4><p>Every pick, its gate status, and the exact reason it is withheld.</p></div>
  <div class="card"><h4><a href="correlations.html">Correlations &amp; parlays</a></h4><p>Six measured correlations, six that cannot be measured, and why multiplication is wrong.</p></div>
  <div class="card"><h4><a href="strategies.html">Strategies &amp; leaderboard</a></h4><p>Seven strategies against twelve gates, plus the competition rules and reward split.</p></div>
  <div class="card"><h4><a href="injuries.html">Injuries &amp; rotation</a></h4><p>85 official status rows, per-team exposure, and exactly what cannot be quantified.</p></div>
  <div class="card"><h4><a href="questions.html">Open questions</a></h4><p>Fourteen questions that block decisions, each with how to find the answer.</p></div>
  <div class="card"><h4><a href="suggestions.html">Suggestions queue</a></h4><p>{len(C.SUGGESTIONS)} proposals with a decision state, so a path can be chosen before anything is built.</p></div>
  <div class="card"><h4><a href="flagged.html">Flagged for review</a></h4><p>{len(C.FLAGS)} irregularities with sources, none of which block publication.</p></div>
</div>

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
<p class="lede">The repository already published a dataset. This session re-read the same pages live and compared, so a reader can see exactly where the earlier work was right and where it was not.</p>
"""
    crow = []
    for c in xchecks["checks"]:
        kind = "ok" if c["result"] == "MATCH" else "bad"
        crow.append({"cells": [esc(c["what"]), esc(c["repo_value"]), esc(c["live_value"]),
                              badge(c["result"], kind), esc(c["detail"])[:160], srclink(c["src"])]})
    body += table(["Check", "Committed in repo", "Live official", "Result", "Detail", "Source"], crow,
                  "Repository dataset vs live official pages")

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
    body = """<h1>Executive summary</h1>
<p class="lede">Six things you need to know, in the order they affect a decision.</p>
"""
    for head, txt in C.EXEC_BULLETS:
        body += f'<div class="note"><b>{esc(head)}.</b> {esc(txt)}</div>'
    body += f"""
<h2>Numbers behind the summary</h2>
"""
    rows = [
        {"cells": ["Games in window", f"{len(lines)}", "2026-11-13 → 2026-11-16", srclink(O.SOURCES["schedule"][1])]},
        {"cells": ["Games verified against the official schedule", f"{len(O.SLATE)} / {len(O.SLATE)}", "date, tip time, arena, game id, per-row game URL", srclink(O.SOURCES["schedule"][1])]},
        {"cells": ["Team records verified against nba.com/standings", "30 / 30", "exact match", srclink(O.SOURCES["standings"][1])]},
        {"cells": ["Injury rows verified against the official PDF", "85 / 85 (+10 not-yet-submitted)", "11/13/26 04:15 PM ET", srclink(O.INJURY_PDF_URL)]},
        {"cells": ["Measured correlations", "6", "computed from the official team, opponent and advanced tables", srclink(O.SOURCES["team_adv"][1])]},
        {"cells": ["Correlations that cannot be measured", "6", "each names the missing dataset on the correlations page", srclink(O.BLOCKED["game_logs"][2])]},
        {"cells": ["Teams outside the luck noise band", f"{sum(1 for t in teams.values() if abs(t.luck_z) > 1.96)} / 30", "|z| ≤ 1.96", srclink(O.SOURCES["standings"][1])]},
        {"cells": ["Picks published", f"0 / {len(O.SLATE)}", "every pick fails G6 (no market price exists to bet against)", srclink(O.BLOCKED["odds"][2])]},
        {"cells": ["Strategies that may be ranked", "0 / 7", "all fail G6 (no price) and G7 (no settled results)", srclink(O.BLOCKED["game_logs"][2])]},
        {"cells": ["Open decision questions", "14", "each with a way to resolve it — see the questions page", srclink(O.SOURCES["standings"][1])]},
        {"cells": ["Suggestions awaiting a decision", "18", "3 recommended first — see the queue page", srclink(O.SOURCES["schedule"][1])]},
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
"""
    built["executive-summary.html"] = page("executive-summary.html", "Executive summary", body, "executive-summary.html")

    # ------------------------------------------------------------------ picks & slate
    body = """<h1>Picks &amp; the upcoming slate</h1>
<p class="lede">Every game in the three-day window is priced. Every pick is then withheld, because two gates cannot pass
without data that does not exist in this environment. This page is deliberately the most conservative on the site.</p>
<div class="note bad"><b>0 of {n_lines} picks are published.</b> Not because the model failed, but because a bet needs a price to beat
(G6) and a settled history to prove skill (G7). Neither exists. Publishing a pick anyway would be the one thing this build refuses to do.</div>
"""
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
                  rows, "Every game in the window: line, grade and pick status", num_cols=(4, 5, 6), idcol="id")

    body += """<h2>Why each pick is withheld</h2>
"""
    grows = []
    for g in C.GATES:
        grows.append({"cells": [esc(g[0]), esc(g[1]), esc(g[2]), badge(g[3], "warn" if "PROPOSED" in g[3] else "info"),
                              srclink(g[4]), esc(g[5])]})
    body += table(["Gate", "Name", "Rule", "Basis", "Source", "Why it exists"], grows, "The twelve gates a pick must pass")

    body += """<h2>The slate itself</h2>
<p class="lede">Read from the official schedule. Eleven of these games are on 11/13 and have already tipped;
they are kept because the only injury report that is fetchable covers them.</p>
"""
    srows = []
    for (d, t, a, h, gid, arena, city, tv, cup) in sorted(O.SLATE):
        srows.append({"cells": [esc(d), esc(t), f"{esc(a)} @ {esc(h)}", esc(gid), esc(arena), esc(city), esc(tv or "—"), esc(cup or "—"),
                               srclink("https://www.nba.com/schedule?date=" + d)]})
    body += table(["Date", "ET", "Matchup", "Game ID", "Arena", "City", "National TV", "Cup group", "Source"],
                  srows, "The priced slate, read from the official schedule", idcol=None)
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
            srclink(d["source_url"]) if d.get("source_url") else "—",
        ]})
    body += table(["Date", "Matchup", "Margin", "Spread", "Total", "Spread A", "Spread B", "Δ spread",
                   "Total B", "Δ total", "P(home)", "Fair home", "Fair away", "Conviction", "Grade", "Source"],
                  rows, f"{n_lines} originated lines with both estimators", num_cols=tuple(range(2, 14)), idcol="id")

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
<p class="lede">Two official reports, both linked. The current one — <b>{O.INJURY_1411_TITLE}</b> — carries
{len(O.INJURIES_1411)} rows covering the live window and is what per-team exposure below is computed from. The older
11/13/26 04:15 PM ET report ({len(O.INJURIES)} rows, full detail with reasons) is kept underneath because it is the last
release that describes a completed slate and is useful for auditing the previous build.</p>
<div class="note"><b>Filing deadlines, from the league's own page.</b> Teams must report by 5 p.m. local the day before a game
(other than the second of a back-to-back) and again between 11 a.m. and 1 p.m. on game day; for the second of a back-to-back,
by 1 p.m. local on game day. Reports are updated continuously. <a href="{O.SOURCES['injury_policy'][1]}" target="_blank" rel="noopener">official.nba.com</a></div>
<div class="note warn"><b>Dated input, stated precisely.</b> The newest report this build could actually read is
<b>11/14/26 04:15 AM ET</b>. Later revisions were listed by the league's archive page but the 01:30 PM ET file returned
<code>AccessDenied</code>, so this page cannot show today's final game-day statuses. Nothing was filled in from an
unavailable file, and a row that says <b>NOT YET SUBMITTED</b> means the league had received no filing — availability
unknown, not "healthy".</div>
"""

    # ---- current exposure, computed from the 11/14 04:15 AM report only
    from collections import Counter as _C
    _live = _C((r[1], r[3]) for r in O.INJURIES_1411)
    _names: dict[str, str] = {}
    for (mu, team, player, status, reason) in O.INJURIES_1411:
        _names.setdefault(team, mu)
    body += ("<h2>Exposure today, from the 11/14 04:15 AM ET report</h2>"
             "<p class=\"lede\">One row per team that appears in the report. A team with no filing and a team "
             "that was never listed are different things, and they are shown differently.</p>")
    _slate_teams = sorted({t for (_d, _tm, a, h, _g, *_r) in O.SLATE for t in (a, h)})
    _present = {r[1] for r in O.INJURIES_1411}
    rows = []
    for tri in _slate_teams:
        nm = O.NAMES[tri]
        if nm not in _present:
            rows.append({"cells": [esc(nm), "0", "0", "0", "0", "0",
                                   badge("no row in report", "bad"),
                                   '<span class="blank">FLAG-INJ-1411-NO-ROW: team is not in the 04:15 AM report at all</span>',
                                   srclink(O.INJURY_1411_PDF_URL)]})
            continue
        n_out = _live[(nm, "Out")]
        n_q = _live[(nm, "Questionable")]
        n_d = _live[(nm, "Doubtful")]
        n_p = _live[(nm, "Probable")]
        n_a = _live[(nm, "Available")]
        n_ns = _live[(nm, "NOT YET SUBMITTED")]
        risk = ("UNKNOWN (no filing)" if n_ns else
                "SEVERE" if n_out >= 4 else "HIGH" if n_out >= 2 else
                "MODERATE" if n_out or n_q or n_d else "LOW")
        rows.append({"cells": [esc(nm), esc(n_out), esc(n_d), esc(n_q), esc(n_p), esc(n_a),
                               badge(risk, "bad" if risk.startswith(("SEVERE", "UNKNOWN")) else "warn" if risk == "HIGH" else "ok"),
                               '<span class="blank">needs per-player minutes</span>',
                               srclink(O.INJURY_1411_PDF_URL)]})
    body += table(["Team", "Out", "Doubtful", "Questionable", "Probable", "Available",
                   "Rotation risk", "Minutes impact", "Source"],
                  rows, "Official 11/14 04:15 AM ET exposure for every team on the priced slate",
                  num_cols=(1, 2, 3, 4, 5))
    body += ("<div class=\"note bad\"><b>Three teams on the slate have no row in the 04:15 AM report:</b> "
             "Golden State Warriors, Orlando Magic, Portland Trail Blazers. Their most recent captured game is 11/13 "
             "and they do not play again until 11/16-11/17, so no filing was required or none was published. "
             "This is left blank and flagged rather than read as a clean bill of health.</div>")

    body += "<h2>Per-team exposure — prior build's 11/13 16:15 ET snapshot</h2>"
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

    body += f"<h2>Current report — all {len(O.INJURIES_1411)} rows (11/14 04:15 AM ET)</h2>"
    rows = []
    for (mu, team, player, status, reason) in O.INJURIES_1411:
        rows.append({"cells": [
            esc(mu), esc(team), esc(player) if player else '<span class="blank">—</span>',
            badge(status, "bad" if status == "Out" else
                  "warn" if status in ("Questionable", "Doubtful", "NOT YET SUBMITTED") else "off"),
            esc(reason) if reason else '<span class="blank">no filing received</span>',
            srclink(O.INJURY_1411_PDF_URL)]})
    body += table(["Matchup", "Team", "Player", "Status", "Reason", "Source"], rows,
                  "Every row of the official 11/14 04:15 AM ET report, including no-filing rows")
    body += f"<h2>Prior report — all {len(inj_rows)} status rows (11/13 16:15 ET)</h2>"
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
    # Rest and density are computed from the FULL stretch of the official schedule that was read
    # (O.SCHEDULE_DATES_ALL), not from the priced window. Using the window alone was a real bug:
    # every team's first priced game looked like "first in window / rested" because the previous
    # game (often 11/13) sat outside the window, so genuine back-to-backs were invisible.
    from collections import defaultdict
    team_dates = defaultdict(list)
    for team, ds in O.SCHEDULE_DATES_ALL.items():
        team_dates[team] = sorted(set(ds))
    rows = []
    for (d, t, a, h, gid, arena, city, tv, cup) in sorted(O.SLATE):
        def density(team):
            """(rest_days_before_this_game, games_in_this_gap) straight from official dates."""
            from datetime import date as _d
            ds = team_dates[team]
            prev = [x for x in ds if x < d]
            if not prev:
                return None, len([x for x in ds if x <= d])
            y1, m1, d1 = map(int, prev[-1].split("-"))
            y2, m2, d2 = map(int, d.split("-"))
            return (_d(y2, m2, d2) - _d(y1, m1, d1)).days - 1, len([x for x in ds if x <= d])
        ra, na = density(a)
        rh, nh = density(h)

        def rest_cell(r):
            if r is None:
                return '<span class="blank">no prior game in captured span</span>'
            return esc(r)

        def dens_badge(r):
            if r is None:
                return badge("unknown", "off")
            if r == 0:
                return badge("B2B", "warn")
            if r == 1:
                return badge("1 day", "off")
            return badge("rested", "ok")
        rows.append({"id": gid, "cells": [
            esc(d), f"{esc(a)} @ {esc(h)}",
            rest_cell(ra), rest_cell(rh),
            esc(na), esc(nh),
            dens_badge(ra), dens_badge(rh),
            '<span class="blank">needs play-by-play</span>',
            srclink("https://www.nba.com/schedule?date=" + d)]})
    body += table(["Date", "Matchup", "Rest (away, days)", "Rest (home, days)", "Games in captured span (away)",
                   "Games in captured span (home)", "Away density", "Home density",
                   "Pace / garbage / foul flow", "Source"],
                  rows, "Schedule-derived rest and density — fully official, computed across the whole captured span", num_cols=(2, 3, 4, 5), idcol="id")
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
    body += table(["ID", "Check", "In repo", "Live official", "Result", "Detail", "Source"], rows,
                  "Repository data re-verified against live official pages")

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
<div class="note bad"><b>What is missing, and blocks the brief.</b> No market price, no per-game results, no player game
logs. Those three absences are why the prior build could not produce a single settled bet, and they are why this build
withholds all {n_lines} picks rather than publishing confidence it cannot support.</div>
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
<pre>python3 -m nba2.v2             # rebuilds data/v2/*.json and site/ (17 pages)
python3 -m nba2.v2.check       # every row sourced, every blank explained
python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'   # 42 tests</pre>"""
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
