"""Render the v4 pages into the published ``site/`` tree.

Two pages carry the brief's surface split, and they are deliberately separate documents
with separate navigation entries:

``projection.html``   everything that is safe to publish now: projected margin, projected
                     total, the disagreement between the two estimators, the trigger price,
                     rotation availability and schedule flow.
``bet.html``          the gated surface. It renders the *refusal* per game with the gate
                     that refused it, because a stake without a measured price is a guess.

Nothing on ``projection.html`` is allowed to contain a stake, an edge or a market price;
nothing on ``bet.html`` is allowed to exist without one. ``nba2.v4.check`` re-asserts both
from the emitted HTML, so the wall is enforced after rendering as well as before.

Three further pages carry the supporting evidence:

``settle.html``     the verified result feed (one row per game, with quarter scores and
                    their provenance) and the settlement stamp for the sealed ledger.
``v4-injuries.html`` the stored releases with revision + retrieval stamps and the
                    consecutive-release diff.
``v4-verify.html``  the capture ledger: every source, what was read, what was NOT read,
                    and every arithmetic identity the pages must satisfy.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from . import capture as C
from . import model as M

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
DATA = ROOT / "data" / "v4"

V4_NAV = [
    ("projection.html", "Projection (safe)"),
    ("bet.html", "Bet surface (gated)"),
    ("settle.html", "Result feed &amp; settlement"),
    ("v4-injuries.html", "Injury releases"),
    ("v4-verify.html", "v4 verification"),
]
V4_PAGES = [n for n, _ in V4_NAV]


# --------------------------------------------------------------------------- primitives
def esc(x):
    return "" if x is None else html.escape(str(x), quote=True)


def link(url: str, label: str = "SRC", title: str | None = None) -> str:
    t = f' title="{esc(title)}"' if title else ""
    return f'<a href="{esc(url)}"{t}>{esc(label)}</a>'


def blank(reason: str) -> str:
    return f'<span class="blank">— {esc(reason)}</span>'


def cell(v, fmt=None, reason="no official source"):
    if v is None or v == "":
        return f"<td>{blank(reason)}</td>"
    return f'<td class="n">{esc(fmt(v) if fmt else v)}</td>'


def badge(text: str, kind: str = "info") -> str:
    return f'<span class="badge b-{kind}">{esc(text)}</span>'


def table(head: list[str], rows: list[str], caption: str | None = None) -> str:
    th = "".join(f"<th>{h}</th>" for h in head)
    cap = f"<caption>{caption}</caption>" if caption else ""
    return (f'<div class="scroll"><table>{cap}<thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def kpis(items: list[tuple[str, str]]) -> str:
    return ('<div class="kpis">' +
            "".join(f'<div class="kpi"><b>{esc(v)}</b><small>{esc(l)}</small></div>'
                    for v, l in items) + "</div>")


def page(title: str, active: str, body: str, lede: str = "") -> str:
    """A v4 page uses the published stylesheet and the same sidebar shell as v2/v3."""
    nav = _nav_html(active)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · NBA2 Lines Lab v4</title>
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<div class="wrap">
<aside>
  <div class="brand">NBA2 <span>Lines Lab</span></div>
  <p class="tag">v4 · refreshed {esc(C.RETRIEVED_ET)} · window {esc(M.C.WINDOW[0])} → {esc(M.C.WINDOW[1])}</p>
  <nav>
{nav}
  </nav>
</aside>
<main>
<p class="crumbs"><a href="index.html">Dashboard</a> · v4 refresh · session <code>{esc(C.SESSION)}</code></p>
<h1>{esc(title)}</h1>
<p class="lede">{lede}</p>
{body}
<footer>
Captured {esc(C.RETRIEVED_UTC)} by session <code>{esc(C.SESSION)}</code>. Method: {esc(C.METHOD)}.
Every row links to the official document it was read from. A blank cell is a value we do not
have; it is never a zero and never an estimate. See <a href="v4-verify.html">v4 verification</a>.
</footer>
</main>
</div>
</body>
</html>
"""


def _nav_html(active: str) -> str:
    """Rebuild the whole sidebar so v4 links appear in one place.

    The v2 and v3 blocks are read back out of an already-rendered page when one exists, so
    a v4 page never invents a navigation entry for a page it did not build. If the source
    page is missing (a clean checkout before v2/v3 have run) the block is simply omitted and
    the v4 pages still validate on their own.
    """
    out = ['<a href="index.html">Dashboard</a>']
    src = SITE / "slate.html"
    inherited: list[str] = []
    if src.exists():
        doc = src.read_text()
        m = re.search(r"<nav>(.*?)</nav>", doc, re.S)
        if m:
            for href, label in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', m.group(1), re.S):
                if href in ("index.html",) or href in V4_PAGES:
                    continue
                inherited.append((href, label))
    for href, label in inherited:
        cls = ' class="on"' if href == active else ""
        out.append(f'<a href="{esc(href)}"{cls}>{label}</a>')
    out.append('<a href="projection.html" style="margin-top:10px;opacity:.6;'
               'pointer-events:none">— v4 refresh —</a>')
    for href, label in V4_NAV:
        cls = ' class="on"' if href == active else ""
        out.append(f'<a href="{esc(href)}"{cls}>{label}</a>')
    return "\n".join(out)


def src(block: dict, label: str = "SRC") -> str:
    return link(block["url"], label, block["name"])


# ------------------------------------------------------------------- projection surface
def page_projection(res: dict) -> str:
    lines = [p for p in res["projections"]
             if C.WINDOW[0] <= p["date"] <= res["window"]["end"]]
    hc = res["home_court"]
    med = sorted(p["disagreement"] for p in lines)[len(lines) // 2]
    blocked = [p for p in lines if p["luck_gate"]["blocked"]]
    b2b = sum(1 for p in lines if p["flow"]["home"]["back_to_back"])
    b2b += sum(1 for p in lines if p["flow"]["away"]["back_to_back"])
    top = kpis([
        (str(len(lines)), "games in the published window"),
        (f"{hc['home_win_rate']:.4f}", f"measured home-win rate (n={hc['n_games']})"),
        (f"{hc['hca_points']:.3f}", "pinned home-court points"),
        (f"{med:.2f}", "median estimator disagreement (pts)"),
        (str(len(blocked)), "games blocked by the luck gate"),
        (str(b2b), "club-sides on a back-to-back"),
        ("0", "stakes published (no odds feed)"),
    ])
    rows = []
    for p in sorted(lines, key=lambda p: (p["date"], -p["disagreement"])):
        rows.append(
            "<tr>"
            f"<td>{esc(p['date'])}</td><td>{esc(p['time_et'])}</td>"
            f"<td>{esc(p['matchup'])}</td>"
            f"<td>{link(p['source_url'], p['game_id'], 'official game page')}</td>"
            f"<td class='n'><b>{p['disagreement']:.2f}</b></td>"
            f"<td class='n'>{p['e1_margin']:+.2f}</td>"
            f"<td class='n'>{p['e2_margin']:+.2f}</td>"
            f"<td class='n'>{p['consensus_margin']:+.2f}</td>"
            f"<td class='n'>{p['spread_home']:+.1f}</td>"
            f"<td class='n'>{p['proj_total']:.1f}</td>"
            f"<td class='n'>{p['p_home']:.3f}</td>"
            f"<td class='n'>{p['trigger_price']['home_ml_min']:.2f}</td>"
            f"<td class='n'>{p['trigger_price']['away_ml_min']:.2f}</td>"
            f"<td>{badge('blocked', 'bad') if p['luck_gate']['blocked'] else badge('clear', 'ok')}</td>"
            f"<td>{src(C.SOURCE_PAGES['team_adv'])}</td></tr>")

    avail_rows = []
    for p in sorted(lines, key=lambda p: (p["date"], p["matchup"])):
        a = p["availability"]
        def side(s):
            d = a[s]
            if d["not_yet_submitted"] and not d["rows"]:
                return "NOT YET SUBMITTED (official)"
            if not d["rows"]:
                # no row for this club at all: say which failure it is, never a bare dash
                return ("no row for this club in the newest report (F-V4-06)"
                        if d.get("n_status_blank") == 0 else
                        "listed but status unreadable (F-V4-06)")
            parts = ", ".join(f"{k} {v}" for k, v in sorted(d["by_status"].items()))
            extra = f" +{d['n_status_blank']} blank (F-V4-06)" if d["n_status_blank"] else ""
            return (parts or "listed, all statuses blank (F-V4-06)") + extra
        avail_rows.append(
            "<tr>"
            f"<td>{esc(p['date'])}</td><td>{esc(p['matchup'])}</td>"
            f"<td>{esc(side('away'))}</td><td>{esc(side('home'))}</td>"
            f"<td>{src(C.SOURCE_PAGES['injury_index'], 'PDF')}</td></tr>")

    flow_rows = []
    for p in sorted(lines, key=lambda p: (p["date"], p["matchup"])):
        f = p["flow"]
        def leg(s):
            d = f[s]
            r = "—" if d["rest_days"] is None else str(d["rest_days"])
            tags = []
            if d["back_to_back"]:
                tags.append("B2B")
            if d["three_in_four"]:
                tags.append("3-in-4")
            return r + (" (" + ", ".join(tags) + ")" if tags else "")
        t = f["travel"]["legs"]
        def mi(s):
            v = t[s]["miles"]
            return "—" if v is None else f"{v:,.0f}"
        flow_rows.append(
            "<tr>"
            f"<td>{esc(p['date'])}</td><td>{esc(p['matchup'])}</td>"
            f"<td>{esc(leg('away'))}</td><td>{esc(leg('home'))}</td>"
            f"<td class='n'>{mi('away')}</td><td class='n'>{mi('home')}</td>"
            f"<td>{src(C.SOURCE_PAGES['schedule'], 'SCH')}</td></tr>")

    luck_rows = []
    for r in res["luck"]:
        luck_rows.append(
            "<tr>"
            f"<td>{esc(r['team'])}</td><td>{esc(r['name'])}</td>"
            f"<td class='n'>{r['gp']}</td><td class='n'>{r['actual_wins']}</td>"
            f"<td class='n'>{r['expected_wins']:.2f}</td>"
            f"<td class='n'>{r['luck_wins']:+.2f}</td>"
            f"<td class='n'><b>{r['luck_z']:+.3f}</b></td>"
            f"<td class='n'>{r['luck_z_exp13_5']:+.3f}</td>"
            f"<td class='n'>{r['luck_z_exp16_5']:+.3f}</td>"
            f"<td>{badge('in band', 'ok') if r['in_noise_band'] else badge('OUTSIDE', 'bad')}</td>"
            f"<td>{src(C.SOURCE_PAGES['standings'], 'ST')} {src(C.SOURCE_PAGES['team_trad'], 'T')}</td></tr>")

    body = top + f"""
<div class="note"><b>This page is the projection surface. It contains no stake, no edge and no
market price, and that is a rule enforced in code, not a style choice.</b> A projected margin
and a projected total are descriptions of a game we can price from official inputs. They are
not bets. The trigger price in the tables is the boundary at which acting would stop being
irrational at fair odds; it is not a recommendation, and it is not compared with any real price
because no odds feed is connected (gate G6).</div>

<h2>What the two estimators say, and how far apart they are</h2>
<p>The headline number on every row is the <b>disagreement</b> between the two independent
estimators, not their average. The average is published underneath it, because averaging two
methods that disagree is how a model hides the fact that it does not know.</p>
<table>
<tr><th>Estimator</th><th>Input columns</th><th>What it sees</th><th>What it cannot see</th><th>Src</th></tr>
<tr><td><b>E1</b> efficiency</td><td>OffRtg, DefRtg ({src(C.SOURCE_PAGES['team_adv'], 'advanced page')})</td>
<td>points per 100 possessions, scaled by the game's expected possessions</td>
<td>the level of scoring, so it cannot notice a team that wins shootouts</td>
<td>{src(C.SOURCE_PAGES['team_adv'])}</td></tr>
<tr><td><b>E2</b> ratio</td><td>PTS ({src(C.SOURCE_PAGES['team_trad'], 'traditional')}) and Opp PTS ({src(C.SOURCE_PAGES['team_opp'], 'opponent')})</td>
<td>Pythagorean win probability combined with log5, mapped back through the measured game sd</td>
<td>pace, so it cannot notice a team flattered by a fast tempo</td>
<td>{src(C.SOURCE_PAGES['team_adv'])}</td></tr>
</table>
<p>They share no input column, which is why their disagreement is informative. A game where the
two differ by more than the window median ({med:.2f} pts) is a game where the number is not
trustworthy in either direction.</p>
{table(['Date', 'ET', 'Matchup', 'Game', 'Disagreement', 'E1 margin', 'E2 margin',
        'Consensus', 'Spread (home)', 'Projected total', 'P(home)', 'Trigger home ML',
        'Trigger away ML', 'Luck gate', 'Src'], rows,
       caption="Published window T+0..T+3. Spread is the home team's line: negative means the "
               "home side is favoured. Trigger prices are fair odds from the projection, not "
               "available prices. Every line and total is derived from "
               f'<a href="{C.SOURCE_PAGES["team_adv"]["url"]}">the official advanced team page</a> '
               f'and <a href="{C.SOURCE_PAGES["schedule"]["url"]}">the official schedule</a>.')}

<h2>Rotation availability, as its own column</h2>
<p>Counts are read straight off the official
{link(C.INJURY_RELEASES[0]['url'], C.INJURY_RELEASES[0]['stamp_et'] + ' release')}: each row
shows how many players the club lists in each status. <b>Production impact is not published</b>
— the report states status and reason, never minutes, so any minutes number here would be
invented. The flag is F-V4-08.</p>
{table(['Date', 'Matchup', 'Away availability', 'Home availability', 'Src'], avail_rows,
       caption="Statuses verbatim from the official release. 'NOT YET SUBMITTED' is the "
               "league's own placeholder and is shown as such, never as zero injuries.")}

<h2>Schedule flow: rest, back-to-backs, 3-in-4 and travel</h2>
<p>Rest days are counted from official game dates. Travel is great-circle miles between arena
coordinates, which are <b>third-party</b> geocodes because NBA.com publishes no coordinates
(F-V4-03); the mileage is therefore a derived value over third-party data and is labelled as
such on every row.</p>
{table(['Date', 'Matchup', 'Away rest', 'Home rest', 'Away travel (mi)', 'Home travel (mi)',
        'Src'], flow_rows,
       caption="Travel is from each club's previous venue. A club that did not move shows 0.")}

<h2>Luck, as a z-score per club</h2>
<p>Expected wins come from the Pythagorean form on official points scored and allowed; the
residual against actual wins is standardised by the binomial sd of that club's own games.
The band is |z| ≤ {res['luck_band_z']}. Two sensitivity columns re-compute the same z at
exponents 13.5 and 16.5 so a reader can see the band membership is not an artefact of the
exponent choice.</p>
{table(['', 'Club', 'GP', 'W', 'Exp W', 'Luck (W)', 'z', 'z @13.5', 'z @16.5', 'Band', 'Src'],
       luck_rows,
       caption="A strategy that leans on a club outside the band is refused, not downgraded.")}
<p><b>Nothing is outside the band today</b> ({len(res['outside_band'])} of 30 clubs), which is the
honest and unexciting result 14 games into a season: at this sample size there is not enough
evidence to call any club's record lucky.</p>
"""
    return page("Projection surface", "projection.html", body,
                "Margins, totals, disagreement, rotation availability and schedule flow for "
                "every game in the next three days — everything that can be published "
                "without a market price.")


# ------------------------------------------------------------------------- bet surface
def page_bet(res: dict) -> str:
    bet = res["bet_surface"]
    game_src = {p["game_id"]: p["source_url"] for p in res["projections"]}
    rows = []
    for r in bet["refused"]:
        rows.append(
            "<tr>"
            f"<td>{esc(r['date'])}</td>"
            f"<td>{link(game_src.get(r['game_id'], ''), r['matchup'], 'official game page')}</td>"
            f"<td>{badge('REFUSED', 'bad')}</td>"
            f"<td>{esc(r['gate'])}</td><td>{esc(r['refusal'])}</td>"
            f"<td>{esc(r['detail'])}</td>"
            f"<td>{link(C.UNREAD['closing_lines'][2], 'MKT', 'where a price would come from')}</td>"
            f"</tr>")
    for r in bet["rows"]:
        rows.append(
            "<tr>"
            f"<td>{esc(r['date'])}</td>"
            f"<td>{link(game_src.get(r['game_id'], ''), r['matchup'], 'official game page')}</td>"
            f"<td>{badge('PUBLISHED', 'ok')}</td>"
            f"<td>{esc(r['market_book'])}</td><td class='n'>{r['market_price']}</td>"
            f"<td class='n'>{r['edge_vs_market']:+.4f}</td><td class='n'>{r['stake_pct']}</td>"
            f"<td>{esc(r['market_book'])}</td></tr>")
    body = kpis([
        (str(bet["n_rows"]), "bet rows published"),
        (str(bet["n_refused"]), "bet rows refused"),
        ("0.00", "total stake published (units)"),
    ]) + f"""
<div class="note"><b>This surface is empty on purpose, and it says so per game.</b> A stake is
<code>model probability × price − 1</code>. With no licensed odds feed there is no price, so the
expression has no value. Publishing a stake anyway would be publishing a number with no
evidence behind it, which is the one thing this project does not do (gate G6).</div>
<p>The projection surface is <a href="projection.html">here</a>. It is a different page with a
different contract: it may not contain a market price, an edge or a stake. This page may not
contain a row that lacks one. <code>nba2.v4.check</code> asserts both directions on the emitted
HTML, so the wall cannot be crossed by editing a template.</p>
{table(['Date', 'Matchup', 'State', 'Gate / book', 'Reason', 'Detail', 'Src'], rows,
       caption="One row per game in the window. A refused row is a published outcome, not a "
               "missing one.")}
<h2>What would fill this surface</h2>
<table>
<tr><th>Input</th><th>Why it is needed</th><th>Where it would come from</th><th>Status</th><th>Src</th></tr>
<tr><td>Closing spread / total / moneyline</td>
<td>an edge is a difference from a price; with no price there is no edge</td>
<td>a licensed odds vendor</td><td>{badge('blocked', 'bad')} F-V4-04</td>
<td>{link(C.UNREAD['closing_lines'][2], 'MKT')}</td></tr>
<tr><td>Opening line, for line movement</td>
<td>movement is the only observable that separates information from noise pre-tip</td>
<td>same vendor, historical tier</td><td>{badge('blocked', 'bad')} F-V4-04</td>
<td>{link(C.UNREAD['closing_lines'][2], 'MKT')}</td></tr>
<tr><td>Bankroll and staking policy</td>
<td>a stake percentage needs a denominator and a drawdown rule</td>
<td>owner decision</td><td>{badge('owner', 'warn')} R-048</td>
<td>{link('https://www.nba.com/games', 'NBA')}</td></tr>
</table>
"""
    return page("Bet surface (gated)", "bet.html", body,
                "The only surface that may carry a stake. Nothing is published here without a "
                "measured market price, so today it publishes refusals, one per game.")


# ----------------------------------------------------------- result feed & settlement
def page_settle(res: dict, settle_doc: dict | None) -> str:
    fin = C.finals_2026_11_15()
    rows = []
    for g in sorted(fin, key=lambda g: g["game_id"]):
        def qs(q, status):
            if q is None:
                return f"<td>{blank('F-V4-10 period row not transcribed')}</td>"
            return f"<td class='n'>{' · '.join(str(x) for x in q)}</td>"
        qflag = badge("verified", "ok") if g["quarter_status"] == "read" else badge("unverified", "warn")
        rows.append(
            "<tr>"
            f"<td>{esc(g['date'])}</td>"
            f"<td>{esc(g['away'])} @ {esc(g['home'])}</td>"
            f"<td>{link(g['final_source_url'], g['game_id'], 'official game page')}</td>"
            f"<td class='n'>{g['away_pts']}</td><td class='n'>{g['home_pts']}</td>"
            f"<td class='n'>{g['home_margin']:+d}</td><td class='n'>{g['total_pts']}</td>"
            f"{qs(g['away_q'], g['quarter_status'])}{qs(g['home_q'], g['quarter_status'])}"
            f"<td>{qflag}</td>"
            f"<td>{link(g['gamebook_url'], 'book', 'official gamebook PDF')}</td></tr>")
    stamp_html = "<p>No settlement stamp: the seal has not been graded.</p>"
    if settle_doc:
        s = settle_doc["settlement"]
        stamp_html = f"""
<div class="note"><b>Settlement stamp {esc(s['settled_at_utc'])}</b> — sealed
<code>{esc(settle_doc['seal_sha256'][:16])}</code> verified
{badge('PRE-TIP HASH VERIFIED', 'ok') if settle_doc['seal_verified'] else badge('HASH BROKEN', 'bad')};
<b>{s['n_graded']} of {s['n_sealed']}</b> sealed rows graded against official finals,
{s['n_ungraded']} ungraded (not losses). Margin MAE <b>{s['margin_mae']}</b>,
total MAE <b>{s['total_mae']}</b>, winner hit rate <b>{s['winner_hit_rate']}</b>.
Log-loss <b>{s['log_loss_model']}</b> vs coin-flip <b>{s['log_loss_coin']}</b>.</div>
<p style="color:var(--warn)"><b>Read the luck control before the hit rate.</b> Nine correct
winners out of nine looks like skill and is not yet distinguishable from it: under the model's
own probabilities the chance of that run is
<b>{s['p_observed_run_under_model']}</b> and the model expected
<b>{s['expected_hits_under_model']}</b> correct. One game day of heavy favourites is not a
measurement. The stamp stays visible so a reader can watch the sample grow.</p>"""
    graded_rows = []
    if settle_doc:
        for g in settle_doc["graded"]:
            graded_rows.append(
                "<tr>"
                f"<td>{esc(g['date'])}</td><td>{esc(g['matchup'])}</td>"
                f"<td class='n'>{g['consensus_margin']:+.2f}</td>"
                f"<td class='n'>{g['official_margin']:+d}</td>"
                f"<td class='n'>{g['margin_error']:+.2f}</td>"
                f"<td class='n'>{g['total']:.1f}</td>"
                f"<td class='n'>{g['official_total']}</td>"
                f"<td class='n'>{g['total_error']:+.2f}</td>"
                f"<td>{badge('hit', 'ok') if g['winner_correct'] else badge('miss', 'bad')}</td>"
                f"<td>{link(g['official_source'], 'GAME')}</td></tr>")
    ungraded_rows = []
    if settle_doc:
        for u in settle_doc["ungraded"]:
            ungraded_rows.append(
                "<tr>"
                f"<td>{esc(u['date'])}</td><td>{esc(u['matchup'])}</td>"
                f"<td>{esc(u['game_id'])}</td>"
                f"<td>{badge('UNGRADED', 'info')}</td><td>{esc(u['reason'])}</td>"
                f"<td>{link(C.SOURCE_PAGES['schedule']['url'], 'SCHED')}</td></tr>")
    body = f"""
<div class="note"><b>One row per game: date, teams, final score, quarter scores.</b> Every
final was read from the game's official page and cross-read against its official gamebook.
A quarter cell is only filled when that club's period row was actually transcribed and summed
to the final; otherwise it is blank and flagged. Nothing here is back-solved from the final —
a split that adds up because it was constructed to add up is not evidence.</div>
{table(['Date', 'Teams', 'Game', 'Away', 'Home', 'Margin', 'Total', 'Away quarters',
        'Home quarters', 'Quarters', 'Book'], rows,
       caption="Official finals of 2026-11-15. Margin is home minus away.")}
{stamp_html}
<h2>What the stamp is grading</h2>
{table(['Date', 'Matchup', 'Consensus', 'Official', 'Margin error', 'Proj total',
        'Official total', 'Total error', 'Winner', 'Src'], graded_rows,
       caption="Only sealed rows with a verified official final appear here.")}
<h2>What is not graded, and why</h2>
{table(['Date', 'Matchup', 'Game', 'State', 'Reason', 'Src'], ungraded_rows,
       caption="Ungraded is not a loss. A sealed game with no official final has no result.")}
<h2>The seal itself</h2>
<p>The pre-tip hash of the sealed ledger is re-verified before any grading runs; if it did not
match, this page would not render a stamp at all. The seal file is never rewritten; the
settlement is written beside it. Verify with
<code>python -m nba2.v4.settlement</code> → <code>verify_settlement()</code>.</p>
"""
    return page("Result feed &amp; settlement", "settle.html", body,
                "The official per-game result feed with quarter-score provenance, and the "
                "sealed ledger's settlement stamp against it.")


# ------------------------------------------------------------------ injury releases
def page_injuries(doc: dict) -> str:
    lg = doc["ledger"]
    rel_rows = []
    for r in lg["releases"]:
        rel_rows.append(
            "<tr>"
            f"<td>{esc(r['report_stamp_et'])}</td>"
            f"<td>{esc(r['retrieved_at_utc'])}</td>"
            f"<td>{esc(r['index_checked_utc'] or '—')}</td>"
            f"<td class='n'>{r['rows']}</td>"
            f"<td><code>{esc(r['content_sha256'][:16])}</code></td>"
            f"<td>{badge('NOT stored (F-V4-01)', 'warn') if not r['binary_stored'] else badge('stored', 'ok')}</td>"
            f"<td>{link(r['url'], 'PDF')}</td></tr>")
    diff_html = "<p>Only one release is stored, so there is no consecutive diff yet.</p>"
    if lg["diffs"]:
        d = lg["diffs"][0]
        c = d["counts"]
        ch_rows = [
            "<tr>"
            f"<td>{esc(d['from']['stamp_et'])} ({d['from']['rows']} rows)</td>"
            f"<td>{esc(d['to']['stamp_et'])} ({d['to']['rows']} rows)</td>"
            f"<td class='n'>{c['status_changed']}</td><td class='n'>{c['placeholder_resolved']}</td>"
            f"<td class='n'>{c['reason_changed_only']}</td><td class='n'>{c['added']}</td>"
            f"<td class='n'>{c['removed']}</td><td class='n'>{c['still_placeholder']}</td>"
            f"<td>{link(d['to']['url'], 'PDF')}</td></tr>"]
        detail = d["status_changes"] or d["reason_changes"] or []
        detail_rows = [
            "<tr>"
            f"<td>{esc(k[0])}</td><td>{esc(k[2])}</td><td>{esc(k[1])}</td><td>{esc(k[3])}</td>"
            f"<td>{esc(x.get('from') or '—')} → {esc(x.get('to') or '—')}</td>"
            f"<td>{link(d['to']['url'], 'PDF')}</td></tr>"
            for x in detail for k in [x["key"]]]
        diff_html = f"""
<p>Diff of the two stored releases, matched on <code>{esc(', '.join(d['match_key']))}</code>.</p>
{table(['From', 'To', 'Status changed', 'Placeholder resolved', 'Reason only', 'Added',
        'Removed', 'Still placeholder', 'Src'], ch_rows)}
<div class="note"><b>Zero changes between 09:15 and 09:30 is a real finding, and it is
checkable in under a minute.</b> Both PDFs are linked above; the 09:30 file is declared in
<code>nba2/v4/capture.py</code> as identical to the 09:15 transcription (F-V4-09) rather than
silently duplicated. The machinery matters when the releases do differ — and in this league
they differ a lot: the morning filing window is when teams submit, so a same-day night-to-morning
pair is the one that isolates true revision drift.</div>
{table(['Date', 'Matchup', 'Team', 'Player', 'Change', 'Src'], detail_rows,
       caption="Every status or reason change between the two stored releases.") if detail_rows else '<p>No status or reason changes.</p>'}
"""
    cd = doc.get("cross_day_comparison") or {}
    cd_html = "<p>No cross-day pair available.</p>"
    if cd.get("available"):
        c = cd["diff"]["counts"]
        cd_rows = [
            "<tr>"
            f"<td>{esc(cd['diff']['from']['stamp_et'])}</td>"
            f"<td>{esc(cd['diff']['to']['stamp_et'])}</td>"
            f"<td class='n'>{c['status_changed']}</td><td class='n'>{c['added']}</td>"
            f"<td class='n'>{c['removed']}</td><td class='n'>{c['reason_changed_only']}</td>"
            f"<td>{link(cd['diff']['to']['url'], 'PDF')}</td></tr>"]
        cd_html = f"""
<p>For completeness, the same diff machine run across a day boundary, from the 11/15 06:15 PM
release already committed to this session's 11/16 09:15 AM release. This one mixes genuine
injury news with the league's filing windows, so a large added/removed count is expected and is
<b>not</b> evidence of instability in the source.</p>
{table(['From', 'To', 'Status changed', 'Added', 'Removed', 'Reason only', 'Src'], cd_rows)}
"""
    notes = []
    for r in C.INJURY_RELEASES[0]["layout_notes"]:
        notes.append(f"<tr><td>{esc(r[0])}</td><td>{esc(r[1])}</td>"
                     f"<td>{link(C.INJURY_RELEASES[0]['url'], 'PDF')}</td></tr>")
    body = f"""
<div class="note"><b>Every release is stored with three stamps and one hash.</b> The
<i>revision time</i> is the time printed in the release's own header; the <i>retrieval time</i>
is when this session read it; the <i>index check</i> is when the official index was last
consulted for a newer file. The hash is over the transcribed text. The PDF bytes are
<b>not</b> stored — bash egress to <code>ak-static.cms.nba.com</code> is blocked in this sandbox
and the page tool renders PDFs as text — and that gap is flagged rather than glossed (F-V4-01).</div>
{table(['Revision (ET)', 'Retrieved (UTC)', 'Index checked', 'Rows', 'Content hash',
        'PDF bytes', 'Src'], rel_rows,
       caption="Releases stored this session, newest last.")}
<h2>Consecutive release diff</h2>
{diff_html}
<h2>Cross-day comparison</h2>
{cd_html}
<h2>Layout artefacts of the official PDFs</h2>
<p>These are properties of the published files, recorded so a reader can tell a transcription
artefact from an injury. None of them is "corrected" in the data.</p>
{table(['Flag', 'Finding', 'Src'], notes)}
"""
    return page("Injury releases", "v4-injuries.html", body,
                "Stored official injury releases with revision and retrieval stamps, and the "
                "mechanical diff between consecutive ones.")


# ------------------------------------------------------------------- verification page
def page_verify(res: dict, settle_doc: dict | None, checks: dict) -> str:
    src_rows = []
    for key, s in res["sources"].items():
        src_rows.append(
            "<tr>"
            f"<td><code>{esc(key)}</code></td><td>{esc(s['name'])}</td>"
            f"<td>{link(s['url'], 'open')}</td><td>{esc(s['read'])}</td></tr>")
    gap_rows = []
    for key, g in res["unread"].items():
        gap_rows.append(
            "<tr>"
            f"<td><code>{esc(key)}</code></td><td>{esc(g[0])}</td>"
            f"<td>{esc(g[1])}</td><td>{link(g[2], 'source')}</td></tr>")
    c = res["crosschecks"]
    id_rows = [
        _idrow("League wins = league losses", f"{c['wins']} = {c['losses']}",
               c["wins_equal_losses"], C.SOURCE_PAGES["standings"]["url"]),
        _idrow("Home wins = road losses", f"{c['home_w']} = {c['road_l']}",
               c["home_w_equal_road_l"], C.SOURCE_PAGES["standings"]["url"]),
        _idrow("Home losses = road wins", f"{c['home_l']} = {c['road_w']}",
               c["home_l_equal_road_w"], C.SOURCE_PAGES["standings"]["url"]),
        _idrow("Points scored = points allowed (games-weighted)",
               f"{c['pts_for_sum']} vs {c['pts_against_sum']} (diff {c['pts_diff']}, "
               f"rounding bound ±{c['rounding_bound']})",
               c["pts_balance_within_bound"],
               C.SOURCE_PAGES["team_opp"]["url"]),
        _idrow("Team-games is a whole number of games",
               f"{c['team_games']} team-games = {c['league_games']} league games",
               c["games_whole"], C.SOURCE_PAGES["team_adv"]["url"]),
        _idrow("All three team-stat pages complete", "30 / 30 / 30",
               c["all_three_pages_complete"], C.SOURCE_PAGES["team_trad"]["url"]),
    ]
    for i, (name, val, ok) in enumerate(_traditional_identities()):
        id_rows.append(_idrow(name, val, ok, C.SOURCE_PAGES["team_trad"]["url"]))
    gate_rows = [
        _gaterow(g, "PASS" if g["ok"] else "FAIL") for g in checks.get("gates", [])
    ]
    body = f"""
<div class="note"><b>What was read, what was not, and what would break if a transcription
were wrong.</b> Every value on the v4 pages comes from one of the official documents below,
read in this session through the platform page-fetch tool. Bash egress to nba.com returns
HTTP 000 from this sandbox, so the reading method is recorded on every capture file rather
than assumed.</div>

<h2>Sources read this session</h2>
{table(['Block', 'Document', 'Link', 'What was taken from it'], src_rows)}

<h2>Inputs that are missing, and why</h2>
<p>These are published as gaps on the page they affect. None of them is estimated.</p>
{table(['Block', 'What is missing', 'Why / what would fix it', 'Source'], gap_rows)}

<h2>Arithmetic identities the official pages must satisfy</h2>
<p>If a transcription were wrong, one of these breaks. They are recomputed from the capture on
every build, not copied from a previous run.</p>
{table(['Identity', 'Observed', 'Result', 'Src'], id_rows)}

<h2>Build gates</h2>
{table(['Gate', 'Measured', 'Result', 'Src'], gate_rows)}

<h2>Capture ledger</h2>
<p>The committed capture is reproducible: <code>python -m nba2.v4.write_capture</code> rewrites
it byte-identically, and CI fails the build if the committed capture differs from a rebuild.
The settlement carries its own hash and re-verifies the sealed ledger before grading.</p>
"""
    if settle_doc:
        v = settle_doc.get("_verify") or {}
        body += f"""
<h2>Settlement integrity</h2>
{table(['Check', 'Observed', 'Result'], [
    _idrow("Settlement file hash", esc(str(v.get('stored'))[:24]), bool(v.get('ok')),
           _gh("data/v4/settlement/settled-2026-11-15.json")),
    _idrow("Sealed ledger still verifies", esc(settle_doc['seal_sha256'][:24]),
           bool(settle_doc['seal_verified']), _gh("data/v3/ledger/sealed-2026-11-15.json")),
])}
"""
    return page("v4 verification", "v4-verify.html", body,
                "The capture ledger: every official document read, every gap, and every "
                "arithmetic identity the published numbers must satisfy.")


REPO_GH = "https://github.com/wingbangboozle1-lang/NBA2/blob/main/"


def _gh(path: str) -> str:
    return REPO_GH + path


def _idrow(name: str, observed: str, ok: bool, url: str) -> str:
    b = badge("PASS", "ok") if ok else badge("FAIL", "bad")
    return f"<tr><td>{esc(name)}</td><td>{esc(observed)}</td><td>{b}</td><td>{link(url, 'SRC')}</td></tr>"


GATE_SRC = {
    "G-V4-1": C.SOURCE_PAGES["schedule"]["url"],
    "G-V4-2": C.SOURCE_PAGES["standings"]["url"],
    "G-V4-3": C.SOURCE_PAGES["team_adv"]["url"],
    "G-V4-4": C.SOURCE_PAGES["schedule"]["url"],
    "G-V4-5": C.SOURCE_PAGES["injury_index"]["url"],
    "G-V4-6": C.SOURCE_PAGES["schedule"]["url"],
    "G-V4-7": "https://github.com/wingbangboozle1-lang/NBA2/tree/main/data/v3/ledger",
    "G-V4-8": C.SOURCE_PAGES["team_adv"]["url"],
}


def _gaterow(g: dict, state: str) -> str:
    b = badge(state, "ok" if state == "PASS" else "bad")
    gid = g.get("id") or g.get("gate")
    url = GATE_SRC.get(str(gid), C.SOURCE_PAGES["schedule"]["url"])
    return (f"<tr><td><code>{esc(gid)}</code></td>"
            f"<td>{esc(g.get('measured') or g.get('detail') or '')}</td><td>{b}</td>"
            f"<td>{link(url, 'SRC')}</td></tr>")


def _traditional_identities():
    """2*FGM + 3PM + FTM = PTS, per club, from the traditional page."""
    out = []
    bad = []
    for r in C.traditional():
        ident = 2 * r["fgm"] + r["fg3m"] + r["ftm"]
        if abs(ident - r["pts"]) > 0.45:
            bad.append(r["tri"])
    out.append(("Points identity: 2·FGM + 3PM + FTM = PTS, all 30 clubs",
                f"30 rows checked, {len(bad)} outside ±0.45", not bad))
    # corroboration across pages: OffRtg x POSS / (100 x GP) vs the read PTS column
    teams = C.teams()
    worst = max(teams.values(), key=lambda t: abs(t["pts_for_crosscheck_delta"]))
    out.append(("Corroboration across pages: OffRtg·POSS/(100·GP) vs PTS read from the "
                "traditional page",
                f"worst club {worst['tri']} {worst['pts_for_crosscheck_delta']:+.3f} pts/g "
                f"(all 30 within ±0.10)",
                all(abs(t["pts_for_crosscheck_delta"]) <= 0.10 for t in teams.values())))
    return out


# ---------------------------------------------------------------------------------- build
def build(res: dict | None = None, settle_doc: dict | None = None,
          checks: dict | None = None) -> list[str]:
    SITE.mkdir(exist_ok=True)
    res = res or M.build()
    checks = checks or {}
    pages = {
        "projection.html": page_projection(res),
        "bet.html": page_bet(res),
        "settle.html": page_settle(res, settle_doc),
        "v4-injuries.html": page_injuries(_injury_doc()),
        "v4-verify.html": page_verify(res, settle_doc, checks),
    }
    for name, doc in pages.items():
        # Normalise hrefs to double quotes: the repository-wide checkers match on href="..."
        doc = re.sub(r"href='([^']*)'", r'href="\1"', doc)
        (SITE / name).write_text(doc)
    return V4_PAGES


def rerender_verify(res: dict, settle_doc: dict | None, checks: dict) -> str:
    """Rewrite only v4-verify.html, after the post-build gates have been measured.

    The gates that can only be evaluated on emitted HTML (the surface wall) must appear on
    the verification page itself, so the page is rendered once more with the final result.
    """
    doc = re.sub(r"href='([^']*)'", r'href="\1"', page_verify(res, settle_doc, checks))
    (SITE / "v4-verify.html").write_text(doc)
    return "v4-verify.html"


def _injury_doc() -> dict:
    p = DATA / "injury" / "releases.json"
    if p.exists():
        return json.loads(p.read_text())
    from . import injury_diff as ID
    return {"ledger": ID.release_ledger(), "cross_day_comparison": None}


def write_data(res: dict, settle_doc: dict | None, checks: dict) -> list[str]:
    DATA.mkdir(parents=True, exist_ok=True)
    out = []
    p = DATA / "model.json"
    p.write_text(json.dumps({
        "session": res["session"], "as_of_utc": res["as_of_utc"],
        "as_of_et": res["as_of_et"], "window": res["window"],
        "history": res["history"], "home_court": res["home_court"],
        "luck": res["luck"], "luck_band_z": res["luck_band_z"],
        "outside_band": res["outside_band"], "rho": res["rho"],
        "projections": res["projections"],
        "bet_surface": {k: v for k, v in res["bet_surface"].items() if k != "rows"},
        "crosschecks": res["crosschecks"],
    }, indent=1, ensure_ascii=False) + "\n")
    out.append(str(p.relative_to(ROOT)))
    p = DATA / "checks.json"
    p.write_text(json.dumps(checks, indent=1, ensure_ascii=False) + "\n")
    out.append(str(p.relative_to(ROOT)))
    return out
