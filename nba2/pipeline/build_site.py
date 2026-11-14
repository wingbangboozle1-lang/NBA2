"""Render the static site from data/site.json.

Tables are rendered into the HTML at build time (not fetched by JS) so that:
* the site works with scripting disabled and there is no fetch/CORS surface on Pages;
* the lint can prove from the emitted HTML that every row carries a source link;
* a reviewer who views source sees exactly what the pipeline asserted.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA: dict = {}


def _load_data() -> dict:
    """Load data/site.json. Called at build time so a freshly generated file is always used."""
    global DATA
    path = ROOT / "data" / "site.json"
    if not path.exists():
        raise SystemExit(f"missing {path} — run:  python -m nba2.pipeline.build_site_data")
    DATA = json.loads(path.read_text())
    return DATA


if (ROOT / "data" / "site.json").exists():
    _load_data()

NAV = [
    ("index.html", "Dashboard"),
    ("pages/executive-summary.html", "Executive Summary"),
    ("pages/picks.html", "Picks (3-day slate)"),
    ("pages/lines.html", "Originated Lines"),
    ("pages/strategies.html", "Strategy Leaderboard"),
    ("backtest/index.html", "Measured-Skill Backtest"),
    ("pages/parlays.html", "Correlation & Parlays"),
    ("pages/props.html", "Player Props & Combos"),
    ("pages/injuries.html", "Injuries & Rotation"),
    ("pages/game-flow.html", "Game Flow"),
    ("pages/live-verification.html", "Live Verification"),
    ("pages/ratings-staleness.html", "Ratings Staleness"),
    ("pages/research-scaffold.html", "Research Blueprint (session 1)"),
    ("pages/methodology.html", "Methodology & Parameters"),
    ("pages/requirements.html", "Requirements"),
    ("pages/repo-review.html", "Repo Review"),
    ("pages/questions.html", "Open Questions"),
    ("pages/suggestions.html", "Suggestions Queue"),
    ("pages/reconciliation.html", "Cross-session Reconciliation"),
    ("pages/session-audit.html", "Session Audit"),
    ("pages/verification-report.html", "Verification Report"),
    ("pages/flagged-review.html", "Flagged for Review"),
    ("pages/sources.html", "Sources & Verification"),
]

BADGE = {
    "official": ("badge-official", "official"),
    "third_party": ("badge-third", "third party"),
    "derived": ("badge-derived", "derived"),
    "blocked": ("badge-blocked", "no source"),
}

INTROS = {
    "pages/executive-summary.html": "<p>One page for a decision-maker: what exists, what is proven, what is blocked, and the single next decision.</p>",
    "pages/picks.html": "<p>Every game in the window gets a lean, a trigger and a stake of 0% — 0% is the policy, not a placeholder.</p>",
    "pages/lines.html": "<p>Our numbers, one row per game, with the disagreement between the two base ratings printed next to the line.</p>",
    "pages/strategies.html": "<p>Hypotheses, gates and scores. Empty scores are the honest state of a project that has settled nothing.</p>",
    "pages/parlays.html": "<p>Joint probabilities under an explicit correlation sweep, and what changes when legs are not independent.</p>",
    "pages/props.html": "<p>The pricing code is real; the inputs are not available. That asymmetry is the whole page.</p>",
    "pages/injuries.html": "<p>Official report rows, rotation-body arithmetic, and the impact columns left blank on purpose.</p>",
    "pages/game-flow.html": "<p>Schedule-spot facts from the official slate, and the in-game columns we refuse to narrate.</p>",
    "pages/live-verification.html":
        "<p>An official-source re-check run on 2026-11-14 at 10:15 UTC: the schedule and the "
        "standings were read again from NBA.com and diffed against every committed snapshot, "
        "field by field. Every difference is listed; so is every field the page does not render.</p>",
    "pages/ratings-staleness.html":
        "<p>How far the published lines would move if the ratings snapshot were re-anchored to "
        "the live official standings — measured, published, and deliberately <em>not</em> applied, "
        "because the sealed pre-registrations must keep matching what is published.</p>",
    "pages/methodology.html": "<p>How a line gets made here, which parameters are fitted, and which are still someone's opinion.</p>",
    "pages/requirements.html": "<p>The full requirements list from the brief, with a status you can argue with.</p>",
    "pages/repo-review.html": "<p>Line-by-line review of the repository, including work already merged by other sessions.</p>",
    "pages/reconciliation.html": "<p>Same official documents, two sessions, two answers. Every disagreement "
                                 "is listed rather than averaged.</p>",
    "pages/session-audit.html":
        "<p>What the 2026-11-14 verification session re-checked and found: the whole "
        "checker suite re-run end to end, the slate re-diffed against the official "
        "schedule, team records re-read from the official standings, the injury-report "
        "currency delta line by line, and six suggestions put up for review before "
        "implementation. Nothing on this page is an implemented change.</p>",
    "pages/verification-report.html":
        "<p>A fresh, independent verification pass by session arena/fc58f84f-nba2: the "
        "checker chain re-run from a clean state, the live GitHub Pages site re-fetched, "
        "and the current window re-read against live official NBA.com sources. Every "
        "result is this session's own; unconfirmed values stay blank and flagged.</p>",
    "pages/questions.html": "<p>What must be known before a reasonable decision can be made — and how to go find out.</p>",
    "pages/suggestions.html": "<p>Improvement queue for owner review. Nothing here has been implemented on your behalf.</p>",
    "pages/flagged-review.html": "<p>Every unverified value, every caveat, every action. If a number is neither here nor blank, it was checked.</p>",
    "pages/sources.html": "<p>What we read, when, and what we could not read at all.</p>",
}


def esc(v) -> str:
    if v is None:
        return '<span class="blank">—</span>'
    return html.escape(str(v))


def _href(target: str, sub: bool) -> str:
    """Rewrite a repo-root-relative target for the page it is being written into."""
    if not sub:
        return target
    if target == "index.html":
        return "../index.html"
    if target.startswith("pages/"):
        return target[len("pages/"):]
    return "../" + target


def render_table(sec: dict, sub: bool = False) -> str:
    if not sec:
        return ""
    anchor = html.escape(sec.get("anchor") or "t")
    out = [f'<section class="card table-card" id="{anchor}" data-rows="{len(sec["rows"])}">']
    out.append(f"<h2>{esc(sec['title'])}</h2>")
    if sec.get("blurb"):
        out.append(f'<p class="blurb">{esc(sec["blurb"])}</p>')
    out.append('<div class="table-wrap"><table class="data"><caption class="sr-only">'
               + esc(sec["title"]) + "</caption><thead><tr>")
    for c in sec["columns"]:
        out.append(f'<th scope="col">{esc(c["label"])}</th>')
    out.append('<th scope="col">Source</th><th scope="col">Flags</th></tr></thead><tbody>')
    flink = _href('pages/flagged-review.html', sub)
    for r in sec["rows"]:
        cls = r["source"]["class"]
        badge, blabel = BADGE[cls]
        out.append(f'<tr id="{html.escape(r["key"])}">')
        for c in sec["columns"]:
            v = r["values"].get(c["key"])
            if v is None:
                why = "blank because: " + " ".join(r["flags"]) if r["flags"] else "no source"
                out.append(f'<td><span class="blank" title="{html.escape(why)}">— '
                           f'<a class="flaglink" href="{flink}">flagged</a></span></td>')
                continue
            out.append(f"<td>{esc(v)}</td>")
        url = r["source"]["url"]
        if url:
            src_cell = (f'<a class="source-link" href="{html.escape(url)}" target="_blank" '
                        f'rel="noopener">{esc(r["source"]["name"])}</a>')
        else:
            src_cell = f'<span class="nosrc">{esc(r["source"]["name"])}</span>'
        out.append(f'<td class="srccell"><span class="badge {badge}">{blabel}</span>{src_cell}</td>')
        chips = " ".join(f'<a class="flagchip" href="{flink}#{html.escape(f)}">{html.escape(f)}</a>'
                         for f in r["flags"]) or "—"
        out.append(f"<td class='flagcell'>{chips}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    out.append(f'<p class="tablenote">{esc(sec.get("source_note") or "")}</p>')
    out.append("</section>")
    return "\n".join(out)


def kpis() -> str:
    m = DATA["meta"]
    cal = m["calibration"]
    cards = [
        (str(m["games"]), "games priced in window"),
        (str(m["tiers"].get("A", 0)), "Tier A lines"),
        (str(m["tiers"].get("B", 0)), "Tier B lines"),
        (str(m["tiers"].get("C", 0)), "Tier C (do-not-bet)"),
        (str(m["injury_rows"]), "official injury rows ("
         + str(m["injury_status_rows"]) + " status + " + str(m["injury_placeholder_rows"]) + " pending)"),
        (f'{cal["margin_sd"]:.2f}', "σ margin (fitted, pts)"),
        (f'{cal["hca_points"]:.2f}', "home-court adv (fitted, pts)"),
        (str(m["gates_passed"]) + "/" + str(m["gates_total"]), "gates passed"),
        (f'{m["rewards"]["unallocated"]:.0f}', "reward units unallocated"),
        (str(len(DATA["sections"]["flags"]["rows"])), "open flags"),
    ]
    parts = ['<div class="kpi-grid">']
    for v, l in cards:
        parts.append(f'<div class="kpi"><div class="kpi-v">{html.escape(v)}</div>'
                     f'<div class="kpi-l">{html.escape(l)}</div></div>')
    parts.append("</div>")
    return "".join(parts)


def policy_strip(sub: bool = False) -> str:
    m = DATA["meta"]
    seal = m.get("seal") or {}
    if seal:
        n = seal.get("n_predictions")
        digest = str(seal.get("sha256"))[:16]
        seal_txt = f"sealed ledger: {n} predictions, sha256 <code>{html.escape(digest)}…</code>"
    else:
        seal_txt = "no sealed ledger committed"
    link = _href("pages/flagged-review.html", sub)
    return ('<div class="policy">'
            f'<span>as-of <strong>{html.escape(m["snapshot_as_of"])}</strong></span>'
            f'<span>built <strong>{html.escape(m["generated_at_utc"])}</strong></span>'
            f'<span>window <strong>{html.escape(m["slate_window"])}</strong></span>'
            f"<span>{seal_txt}</span></div>"
            '<div class="notice notice-warning"><strong>Read this first:</strong> no market price is available '
            "to this build, so nothing here is a &ldquo;value bet&rdquo; — lines are projections and picks are "
            "triggers. Team point rates come from a third-party table (win-loss is cross-checked against "
            f'NBA.com). Blank means <em>no source</em>, never zero. <a href="{link}">See every open flag</a>.</div>')


def page(title: str, sections: list[str], body_intro: str = "", sub: bool = False,
         active: str = "") -> str:
    active_name = active.split("/")[-1]
    items = []
    for href, label in NAV:
        cls = ' class="active"' if href.split("/")[-1] == active_name else ""
        items.append(f'<li><a href="{_href(href, sub)}"{cls}>{html.escape(label)}</a></li>')
    nav = "".join(items)
    base = "../" if sub else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} · NBA2</title>
<meta name="description" content="Originated NBA lines, validation gates and verified slate data. Research dashboard, not betting advice.">
<link rel="stylesheet" href="{base}css/style.css">
</head>
<body>
<div class="app">
  <header class="header">
    <h1><a class="homelink" href="{base}index.html">NBA2 · Lines Lab</a></h1>
    <div class="subtitle">Originated lines · gated strategies · verified slate data · nothing invented</div>
  </header>
  <aside class="sidebar"><nav aria-label="Sections"><ul>{nav}</ul></nav>
    <div class="side-note">Rebuilt from committed snapshots only.<br>Reproduce:<br>
      <code>python -m nba2.pipeline.build_site_data &amp;&amp; python -m nba2.pipeline.build_site</code>
    </div>
  </aside>
  <main class="main">
    <section class="hero"><h2>{html.escape(title)}</h2>{body_intro}</section>
    {policy_strip(sub)}
    {''.join(sections)}
    <footer class="footer">
      <p>Research and specification artefacts, not betting advice. No market price was available to this build;
      lines are model projections. If you or someone you know has a gambling problem, call the National Problem
      Gambling Helpline (1-800-522-4700, US, 24/7) or your local service. 21+ where legal.</p>
      <p>Snapshots: <code>data/raw/</code> · Engine: <code>nba2/</code> ·
      Board: <a href="{base}COORDINATION.md">COORDINATION.md</a> ·
      <a href="https://github.com/wingbangboozle1-lang/NBA2">repository</a></p>
    </footer>
  </main>
</div>
<script src="{base}app.js" defer></script>
</body>
</html>
"""


def sec(key: str) -> dict:
    return {**DATA["sections"][key], "anchor": key}


def _pages() -> dict[str, list[str]]:
    L = True
    return {
        "pages/executive-summary.html": [
            '<div class="card">' + kpis() + "</div>",
            render_table({**sec("lines"),
                          "title": "Snapshot of the priced slate (first 8 rows)",
                          "rows": sec("lines")["rows"][:8],
                          "anchor": "summary-lines",
                          "blurb": "Full table on the Originated Lines page; truncated here so the summary fits one screen."}, L),
            render_table({**sec("flags"),
                          "title": "The five things a reviewer must know first",
                          "rows": sec("flags")["rows"][:5],
                          "anchor": "summary-flags"}, L),
        ],
        "pages/picks.html": [render_table(sec("picks"), L)],
        "pages/lines.html": [render_table(sec("lines"), L), render_table(sec("slate"), L),
                             render_table(sec("corroboration"), L)],
        "pages/strategies.html": [render_table(sec("leaderboard"), L), render_table(sec("gates"), L),
                                  render_table(sec("gate_matrix"), L)],
        "pages/parlays.html": [render_table(sec("correlation"), L), render_table(sec("parlays"), L),
                               render_table(sec("parlays_xg"), L), render_table(sec("parlay_costs"), L)],
        "pages/props.html": [render_table(sec("props"), L)],
        "pages/injuries.html": [render_table(sec("rotation"), L), render_table(sec("rotation_window"), L),
                                render_table(sec("availability_window"), L),
                                render_table(sec("leaders"), L),
                                render_table(sec("injuries"), L), render_table(sec("injuries_window"), L)],
        "pages/game-flow.html": [render_table(sec("gameflow"), L), render_table(sec("anomalies"), L)],
        "pages/live-verification.html": [render_table(sec("live_capture_check"), L),
                                         render_table(sec("live_slate_diff"), L),
                                         render_table(sec("live_records_diff"), L),
                                         render_table(sec("live_finals"), L)],
        "pages/ratings-staleness.html": [render_table(sec("staleness_summary"), L),
                                         render_table(sec("staleness_games"), L)],
        "pages/methodology.html": [render_table(sec("calibration"), L), render_table(sec("params"), L),
                                   render_table(sec("ratings"), L), render_table(sec("luck"), L)],
        "pages/requirements.html": [render_table(sec("requirements"), L)],
        "pages/repo-review.html": [render_table(sec("repo_review"), L)],
        "pages/questions.html": [render_table(sec("questions"), L)],
        "pages/suggestions.html": [render_table(sec("suggestions"), L)],
        "pages/reconciliation.html": [render_table(sec("surfaces"), L), render_table(sec("xrecords"), L),
                                        render_table(sec("x3way"), L), render_table(sec("xlines"), L),
                                        render_table(sec("xadjudicate"), L),
                                        render_table(sec("xinjuries"), L)],
        "pages/session-audit.html": [render_table(sec("audit"), L),
                                     render_table(sec("injury_delta"), L),
                                     render_table(sec("audit_suggestions"), L)],
        "pages/verification-report.html": [render_table(sec("verification"), L)],
        "pages/flagged-review.html": [render_table(sec("flags"), L)],
        "pages/sources.html": [render_table(sec("sources"), L)],
    }


def build() -> list[str]:
    _load_data()
    written: list[str] = []

    def write(rel: str, text: str) -> None:
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        written.append(rel)

    home_sections = [
        '<div class="card">' + kpis() + "</div>",
        '<section class="card"><h2>Which build is this?</h2><p class="blurb">One dashboard, one window, '
        "one set of numbers — and every other page in this repository is either a page of this "
        "dashboard, the measured-skill backtest, or a build kept for the record and linked from the "
        "reconciliation page.</p><div class=\"cat-grid\">"
        '<a class="cat-card" href="pages/live-verification.html"><h3>This build, re-checked against '
        'NBA.com</h3></a>'
        '<a class="cat-card" href="backtest/index.html"><h3>Measured-Skill Backtest (separate tree)</h3></a>'
        '<a class="cat-card" href="pages/reconciliation.html"><h3>Every other build in this repository, '
        'and its status</h3></a>'
        '<a class="cat-card" href="pages/flagged-review.html"><h3>Everything still unverified</h3></a>'
        "</div></section>",
        '<section class="card"><h2>Sections</h2><p class="blurb">Ordered so a reader meets the data before the '
        "opinion: what we know, what we price, what is blocked.</p><div class=\"cat-grid\">"
        + "".join(f'<a class="cat-card" href="{href}"><h3>{html.escape(label)}</h3></a>'
                  for href, label in NAV[1:])
        + "</div></section>",
        render_table(sec("anomalies"), False),
        render_table(sec("slate"), False),
    ]
    write("index.html", page("NBA2 — originated lines & gated strategies", home_sections,
                             "<p>A line-origination desk that publishes what it can prove and flags what it cannot.</p>",
                             False, "index.html"))

    for rel, secs in _pages().items():
        title = rel.split("/")[-1].replace(".html", "").replace("-", " ").title()
        write(rel, page(title, secs, INTROS.get(rel, ""), True, rel))

    write("flagged.html", '<!DOCTYPE html>\n<html lang="en"><head><meta charset="UTF-8">\n'
                          "<title>Flagged for review — moved</title>\n"
                          '<meta http-equiv="refresh" content="0; url=pages/flagged-review.html">\n'
                          '<link rel="canonical" href="pages/flagged-review.html"></head>\n'
                          '<body><p>This page was merged into the single '
                          '<a href="pages/flagged-review.html">Flagged for Review</a> page '
                          "(duplicate review pages = finding I-06 in COORDINATION.md).</p></body></html>\n")

    # stamped from the data's own build time, not the wall clock: the manifest must be a
    # deterministic function of the inputs or it breaks the CI parity check it is meant to support
    (ROOT / "data" / "site-built.json").write_text(json.dumps(
        {"built_from_data_generated_at": DATA["meta"]["generated_at_utc"],
         "pages": sorted(written)}, indent=2) + "\n")
    return sorted(written)


if __name__ == "__main__":
    for pth in build():
        print("wrote", pth)
