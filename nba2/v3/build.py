"""Build the v3 pages into /site and the v3 JSON into /data/v3.

Every table row carries an official source URL. A value that could not be confirmed
is rendered blank with the flag id that explains it — never a dash pretending to be
data, never an estimate dressed as a measurement.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from . import official as O
from . import model as M
from . import ledger as LD
from . import rotation as ROT
from . import gates as G

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
DATA = ROOT / "data" / "v3"

# The v2 nav is reproduced so the two trees read as one site; v3 links are appended.
V2_NAV = [
    ("index.html", "Dashboard"),
    ("executive-summary.html", "Executive summary"),
    ("picks.html", "Picks &amp; slate"),
    ("lines.html", "Originated lines"),
    ("teams.html", "Teams &amp; estimators"),
    ("official-results.html", "Official results"),
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

V3_NAV = [
    ("slate.html", "Slate &amp; disagreement"),
    ("projections.html", "Projection surface"),
    ("rotation.html", "Rotation &amp; minutes"),
    ("travel.html", "Rest &amp; travel"),
    ("results.html", "Result feed"),
    ("ledger.html", "Sealed ledger"),
    ("player-logs.html", "Player game logs"),
    ("minutes.html", "Measured minutes"),
    ("injury-diff.html", "Injury release diff"),
    ("verification-v3.html", "v3 verification"),
]

V3_PAGES = [n for n, _ in V3_NAV]


def esc(x):
    return "" if x is None else html.escape(str(x), quote=True)


def src(key: str, label: str | None = None) -> str:
    name, url, _ = O.SOURCES[key]
    return f'<a href="{url}" title="{esc(name)}">{esc(label or "SRC")}</a>'


def _abbr_for_arena(arena: str):
    """Arena name -> team tri-code, from the coordinate table. None if not present."""
    for t, c in O.ARENA_COORDS.items():
        if len(c) > 2 and c[2] == arena:
            return t
    return None


def badge(text, kind="info"):
    return f'<span class="badge b-{kind}">{esc(text)}</span>'


def blank(reason: str) -> str:
    return f'<span class="blank">— {esc(reason)}</span>'


def cell(v, fmt=None, reason="no official source"):
    if v is None:
        return f"<td>{blank(reason)}</td>"
    return f'<td class="n">{esc(fmt(v) if fmt else v)}</td>'


def table(head: list[str], rows: list[str], caption: str | None = None,
          scroll: bool = True) -> str:
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "".join(rows)
    cap = f"<caption>{caption}</caption>" if caption else ""
    inner = f"<table>{cap}<thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"
    return f'<div class="scroll">{inner}</div>' if scroll else inner


def page(title: str, active: str, body: str, lede: str = "") -> str:
    nav = []
    for href, label in V2_NAV:
        cls = ' class="on"' if href == active else ""
        nav.append(f'<a href="{href}"{cls}>{label}</a>')
    nav.append('<a href="slate.html" style="margin-top:10px;opacity:.6;pointer-events:none">'
               '— v3 rolling slate —</a>')
    for href, label in V3_NAV:
        cls = ' class="on"' if href == active else ""
        nav.append(f'<a href="{href}"{cls}>{label}</a>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · NBA2 Lines Lab v3</title>
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<div class="wrap">
<aside>
  <div class="brand">NBA2 <span>Lines Lab</span></div>
  <p class="tag">v3 · rolling slate {esc(O.WINDOW[0])} → {esc(O.WINDOW[1])}</p>
  <nav>
{chr(10).join(nav)}
  </nav>
</aside>
<main>
<p class="crumbs"><a href="index.html">Dashboard</a> · v3 rolling slate · session {esc(O.SESSION)}</p>
<h1>{esc(title)}</h1>
<p class="lede">{lede}</p>
{body}
<footer>
Built {esc(O.AS_OF_UTC)} by session <code>{esc(O.SESSION)}</code> from the pages listed on
<a href="verification-v3.html">the v3 verification page</a>. Every row links to the official
document it was read from; a blank cell is a value we do not have, never a zero.
</footer>
</main>
</div>
</body>
</html>
"""


# --------------------------------------------------------------------------- slate
def page_slate(res: dict) -> str:
    hc = res["home_court"]
    lines = res["lines"]
    med = sorted(l["disagreement"] for l in lines)[len(lines) // 2]
    disagree = sorted(lines, key=lambda l: -l["disagreement"])
    kpis = f"""<div class="kpis">
<div class="kpi"><b>{len(lines)}</b><small>games T+0..T+3</small></div>
<div class="kpi"><b>{hc['home_win_rate']}</b><small>measured home win rate (n={hc['n_games']})</small></div>
<div class="kpi"><b>{hc['hca_points']} pts</b><small>pinned HCA</small></div>
<div class="kpi"><b>{med:.2f}</b><small>median estimator disagreement (pts)</small></div>
<div class="kpi"><b>{res['rho']['r']}</b><small>measured rho (margin, total)</small></div>
<div class="kpi"><b>{len(res['outside_band'])}</b><small>clubs outside the luck band</small></div>
</div>"""
    rows = []
    for l in lines:
        gate = "blocked by the luck gate" if l["luck_gate"]["blocked"] else "clear"
        rows.append(
            "<tr>"
            f"<td>{esc(l['date'])}</td><td>{esc(l['time_et'])}</td>"
            f"<td>{esc(l['matchup'])}</td>"
            f"<td>{src('schedule', l['game_id'])}</td>"
            f"<td class='n'>{l['e1_margin']:+.2f}</td>"
            f"<td class='n'>{l['e2_margin']:+.2f}</td>"
            f"<td class='n'><b>{l['disagreement']:.2f}</b></td>"
            f"<td class='n'>{l['consensus_margin']:+.2f}</td>"
            f"<td class='n'>{l['spread_home']:+.1f}</td>"
            f"<td class='n'>{l['total']:.1f}</td>"
            f"<td class='n'>{l['p_home']:.3f}</td>"
            f"<td>{badge(gate, 'bad' if l['luck_gate']['blocked'] else 'ok')}</td>"
            f"<td>{src('team_adv')}</td></tr>")
    body = kpis + f"""
<div class="note"><b>The headline is the disagreement, not the blend.</b> E1 is the efficiency
view (net rating per 100 possessions scaled by the game's expected possessions). E2 is the ratio
view (Pythagorean win probability combined with log5, mapped back through the measured game sd).
Where they disagree by more than the slate median the number is not trustworthy in either
direction, so the disagreement is printed first and the average underneath it.</div>
<h2>Every game in the window</h2>
{table(['Date', 'ET', 'Matchup', 'Game', 'E1 margin', 'E2 margin', 'Disagreement',
        'Consensus (under)', 'Spread (home)', 'Total', 'P(home)', 'Luck gate', 'Src'],
       rows,
       caption="Spread is the home-team spread: negative means the home side is favoured. "
               "Totals are possessions x points-per-possession.")}
<h2>Widest disagreement</h2>
{table(['Matchup', 'E1', 'E2', 'Disagreement', 'Why it matters'],
       ["<tr>" + f"<td>{esc(l['matchup'])}</td><td class='n'>{l['e1_margin']:+.2f}</td>"
        f"<td class='n'>{l['e2_margin']:+.2f}</td><td class='n'><b>{l['disagreement']:.2f}</b></td>"
        f"<td>{'Estimators name opposite sides' if l['e1_margin'] * l['e2_margin'] < 0 else 'Same side, different size'}"
        f"</td><td>{src('team_adv')}</td></tr>" for l in disagree[:8]],
       caption="Sorted by disagreement, descending.")}
<h2>How home court was pinned</h2>
<p>{esc(hc['rule'])}. Over {hc['n_games']} official finals ({hc['neutral_excluded']} neutral-site
game excluded) the home side won {hc['home_wins']}, a rate of {hc['home_win_rate']}; the sd of the
home margin is {hc['margin_sd']}. That gives <b>h = {hc['hca_points']} points</b> — not a fitted
parameter and not folklore: it is the home-win rate restated in points.
<a href="https://www.nba.com/games">Official source</a>.</p>"""
    return page("Slate &amp; estimator disagreement", "slate.html", body,
                f"Every game from {O.WINDOW[0]} to {O.WINDOW[1]} (T+0 to T+3), priced from the "
                f"official snapshot captured {O.AS_OF_ET}. The first number on each row is how far "
                f"apart the two estimators are.")


# ------------------------------------------------------------------- projections
def page_projections(res: dict) -> str:
    rows = []
    for l in res["lines"]:
        av = l["availability"]
        rot = []
        for side in ("away", "home"):
            a = av[side]
            rot.append(f"{a['team']}: " + (
                f"{a['n_out']} Out / {a['n_doubtful']} D / {a['n_questionable']} Q"
                if a.get("filed") else "not filed"))
        rows.append(
            "<tr>"
            f"<td>{esc(l['date'])}</td><td>{esc(l['matchup'])}</td>"
            f"<td>{src('schedule', l['game_id'])}</td>"
            f"<td class='n'>{l['possessions']:.1f}</td>"
            f"<td class='n'>{l['ppp_home']:.3f}</td><td class='n'>{l['ppp_away']:.3f}</td>"
            f"<td class='n'>{l['proj_home_pts']:.1f}</td>"
            f"<td class='n'>{l['proj_away_pts']:.1f}</td>"
            f"<td class='n'><b>{l['total']:.1f}</b></td>"
            f"<td>{esc(' · '.join(rot))}</td>"
            f"<td>{badge('not filed', 'off') if not (av['away'].get('filed') and av['home'].get('filed')) else badge('filed', 'ok')}</td>"
            f"<td>{src('injury_pdf', 'PDF')}</td>"
            f"<td>{src('team_adv')}</td></tr>")
    body = f"""
<div class="note"><b>Projection surface — safe to publish.</b> Everything here is a projection
from official inputs. It contains no stake, no price and no claim of edge. The bet surface is
separate and is emitted only when a market price exists; it does not, so every stake is 0.00 and
the bet surface is empty by construction (<a href="verification-v3.html">F-308</a>).</div>
<h2>Totals as possessions x points-per-possession</h2>
<p>Expected possessions are the mean of the two clubs' official PACE columns. Each side's points
per possession is the mean of its own OffRtg and the opponent's DefRtg, divided by 100. The total
is then <code>possessions x (ppp_home + ppp_away)</code> — not the average of two scoring
averages, which would ignore what each defence does.</p>
{table(['Date', 'Matchup', 'Game', 'Possessions', 'PPP home', 'PPP away', 'Proj home',
        'Proj away', 'Total', 'Rotation availability', 'Report', 'Injury src', 'Stats src'],
       rows,
       caption="Rotation availability is read straight from the official injury report: counts of "
               "Out / Doubtful / Questionable. Minutes impact is blank by policy (F-307).")}
<h2>Why the two surfaces are separate</h2>
<p>A projection says what the model believes. A bet says what to risk. Mixing them is how a
projection acquires authority it has not earned. The projection surface above is complete and
published; the bet surface below it is deliberately empty.</p>
{table(['Surface', 'Contents', 'State', 'Src'],
       ["<tr><td>projection</td><td>spreads, totals, probabilities, rotation availability, "
        "estimator disagreement</td><td>" + badge('published', 'ok') + "</td><td>"
        + src('team_adv') + " " + src('injury_pdf') + "</td></tr>"
        "<tr><td>bet</td><td>stake, price, trigger, settlement</td><td>"
        + badge('empty — no market price (F-308)', 'bad') + "</td>"
        "<td><a href='https://www.nba.com/games'>games</a></td></tr>"],
       scroll=False)}"""
    return page("Projection surface", "projections.html", body,
                "What the model believes about each game, from official inputs only. No stake, "
                "no price, no edge claim — that lives on the bet surface, which is empty.")


# ---------------------------------------------------------------------- rotation
def page_rotation(res: dict) -> str:
    rows = []
    seen = set()
    for l in res["lines"]:
        for side in ("away", "home"):
            ab = l[side]
            key = (ab, l["date"])
            if key in seen:
                continue
            seen.add(key)
            a = l["availability"][side]
            block = ROT.team_block(ab)
            sh = block["shares"]
            filed = a.get("filed")
            rows.append(
                "<tr>"
                f"<td>{esc(l['date'])}</td><td>{esc(l['matchup'])}</td><td>{esc(ab)}</td>"
                f"<td>{src('injury_pdf', 'PDF')}</td>"
                f"<td>{badge('filed', 'ok') if filed else badge('not filed', 'off')}</td>"
                f"<td class='n'>{esc(a['n_out'])}</td><td class='n'>{esc(a['n_doubtful'])}</td>"
                f"<td class='n'>{esc(a['n_questionable'])}</td>"
                f"<td class='n'>{esc(a['n_probable'])}</td>"
                f"<td class='n'>{esc(a['n_available'])}</td>"
                + cell(sh["top8_minutes_share"], reason="F-307 no minutes captured")
                + cell(None, reason="F-307 no minutes captured")
                + f"<td>{src('team_adv')}</td></tr>")
    out_rows = []
    for r in O.INJURIES:
        if r["not_submitted"]:
            continue
        if r["status"] not in ("Out", "Doubtful"):
            continue
        blk = ROT.redistribute([], r["player"])
        out_rows.append(
            "<tr>"
            f"<td>{esc(r['game_date'])}</td><td>{esc(r['matchup'])}</td>"
            f"<td>{esc(r['team_abbr'])}</td><td>{esc(r['player'])}</td>"
            f"<td>{badge(r['status'], 'bad' if r['status'] == 'Out' else 'warn')}</td>"
            f"<td>{esc(r['reason'])}</td>"
            f"<td>{src('injury_pdf', 'PDF')}</td>"
            + cell(blk["replacements"][0]["replacement_share"] if blk.get("replacements") else None,
                   reason="F-307 no minutes captured")
            + f"<td>{src('standings')}</td></tr>")
    body = f"""
<div class="note warn"><b>The minutes model is implemented and wired, but its inputs are blank.</b>
<code>nba.com/stats/players/traditional</code> was reachable this session (469 rows, MIN column
present), which contradicts the standing "player_box" blocked entry on the v2 site. Capturing all
ten pages did not fit this session's budget, so every minutes cell is blank and carries
<a href="verification-v3.html">F-307</a>. Nothing is estimated.</div>
<h2>Rotation availability by game and club</h2>
{table(['Date', 'Matchup', 'Club', 'Report', 'Filed', 'Out', 'Doubtful', 'Questionable',
        'Probable', 'Available', 'Top-8 minutes share', 'Minutes at risk', 'Src'],
       rows,
       caption="Counts are official. 'Not filed' means the club had not submitted for that date "
               "at the report's revision time — never assumed healthy.")}
<h2>Out and doubtful: what the redistribution would need</h2>
{table(['Date', 'Matchup', 'Club', 'Player', 'Status', 'Reason', 'Report',
        'Replacement share', 'Src'], out_rows,
       caption=f"Redistribution rule: {ROT.NEXT_MAN_SHARE:.0%} of the freed minutes go to the "
               f"first man outside the top {ROT.TOP_N}, the rest to incumbents in proportion to "
               f"their existing shares. Declared, not fitted.")}
<h2>The redistribution arithmetic</h2>
<p>A club plays {ROT.TEAM_MINUTES:.0f} player-minutes in a regulation game. With the top
{ROT.TOP_N} by minutes per game, <code>share_i = minutes_i / {ROT.TEAM_MINUTES:.0f}</code>. When
player <code>k</code> is out, incumbents absorb <code>{1 - ROT.NEXT_MAN_SHARE:.0%}</code> of the
freed minutes in proportion to their existing shares and the next man absorbs
<code>{ROT.NEXT_MAN_SHARE:.0%}</code>. The model is in
<code>nba2/v3/rotation.py</code> and is exercised by the test suite on a synthetic roster; it
produces no number for a real club until the minutes capture lands.</p>"""
    return page("Rotation &amp; minutes redistribution", "rotation.html", body,
                "Official injury statuses joined to the rotation model, with the minutes "
                "arithmetic published even where its inputs are still missing.")


# ------------------------------------------------------------------------ travel
def page_travel(res: dict) -> str:
    rows = []
    for l in res["lines"]:
        f = l["flow"]
        def b2b(side):
            v = f[side]["back_to_back"]
            return badge("B2B", "bad") if v else (badge("rested", "ok") if v is False else blank("unknown"))
        rows.append(
            "<tr>"
            f"<td>{esc(l['date'])}</td><td>{esc(l['matchup'])}</td>"
            f"<td>{src('schedule', l['game_id'])}</td>"
            f"<td class='n'>{esc(f['away']['rest_days'])}</td><td class='n'>{esc(f['home']['rest_days'])}</td>"
            f"<td class='n'>{esc(f['rest_edge'])}</td>"
            f"<td>{b2b('away')} {b2b('home')}</td>"
            f"<td class='n'>{esc(f['away']['games_last_4_days'])} / {esc(f['home']['games_last_4_days'])}</td>"
            f"<td>{badge('3-in-4', 'warn') if f['away']['three_in_four'] or f['home']['three_in_four'] else badge('no', 'off')}</td>"
            f"<td>{esc(f['away']['last_game_date'])} / {esc(f['home']['last_game_date'])}</td>"
            + cell(f["away"]["travel_km"], reason="F-306 previous game unknown")
            + cell(f["home"]["travel_km"], reason="F-306 previous game unknown")
            + f"<td>{esc(f['away']['previous_game_arena'])} / "
            f"{esc(f['home']['previous_game_arena'])}</td>"
            f"<td>{esc(l['arena'])}, {esc(l['city'])}, {esc(l['state'])}</td>"
            f"<td>{src('schedule')}</td></tr>")
    arenas = "".join(
        f"<tr><td>{esc(a)}</td><td>{esc(c)}</td><td>{esc(s)}</td>"
        + (f'<td class="n">{esc(O.ARENA_COORDS.get(_t, (None,))[0])}</td>'
           f'<td class="n">{esc(O.ARENA_COORDS.get(_t, (None, None))[1])}</td>'
           if _t else cell(None, reason="F-306 not in the coordinate table")
           + cell(None, reason="F-306 not in the coordinate table"))
        + f"<td>{src('schedule')}</td><td>{src('arena_coords')}</td></tr>"
        for a, c, s in O.ARENAS for _t in [_abbr_for_arena(a)])
    body = f"""
<div class="note"><b>Rest is official; travel is derived from a third-party coordinate
table.</b> Rest days, back-to-backs and 3-in-4 come straight from the official schedule dates plus
the {res['history']['n_games']} official finals committed under <code>data/raw/history/</code>.
Travel distance is great-circle km between the arena of each club's previous game and the arena of
this game, computed with haversine over the committed arena-coordinate table. <b>The arena name,
city and state are official; the coordinates are not</b> — NBA.com publishes none and no official
geocoder is reachable, so they come from Wikipedia/Wikidata and every distance below carries
<a href="verification-v3.html">F-306</a> and is labelled derived, never official.</div>
<h2>Schedule load for every game in the window</h2>
{table(['Date', 'Matchup', 'Game', 'Rest (away)', 'Rest (home)', 'Rest edge (home)',
        'Back-to-back', 'Games in last 4 days (A/H)', '3-in-4', 'Previous game (A/H)',
        'Travel km (away)', 'Travel km (home)', 'Previous arena (A/H)', 'This game arena',
        'Src'],
       rows,
       caption="Rest days = calendar days since that club's previous official game. "
               "3-in-4 = three or more games in the last four calendar days. Travel km = "
               "great-circle distance from the arena of that club's previous game to this "
               "game's arena; derived from third-party coordinates (F-306).")}
<h2>Arena coordinate table (the source of every distance above)</h2>
{table(['Arena', 'City', 'State', 'Latitude', 'Longitude', 'Arena src', 'Coord src'], arenas,
       caption="Arena, city and state are official (nba.com). Latitude and longitude are "
               "THIRD-PARTY (Wikipedia/Wikidata via the Wikimedia REST summary endpoint, "
               "captured 2026-11-15) because NBA.com publishes no coordinates — F-306.")}"""
    return page("Rest &amp; travel", "travel.html", body,
                "Schedule load computed from official dates. Travel distance is withheld until "
                "arena coordinates have an official source.")


# ----------------------------------------------------------------------- results
def page_results(res: dict, stamp: dict | None) -> str:
    rows = []
    hist = M.load_played_games()["games"]
    feed = [g for g in hist if g["date"] == "2026-11-14"]
    played_map = {r["game_id"]: r for r in O.RESULTS}
    for g in feed:
        r = played_map.get(g["game_id"])
        aq = r["away_q"] if r else None
        hq = r["home_q"] if r else None
        def qs(q):
            if not q:
                return cell(None, reason="F-304 linescore not captured")
            return f"<td class='n'>{' · '.join(str(x) for x in q)}</td>"
        rows.append(
            "<tr>"
            f"<td>{esc(g['date'])}</td><td>{esc(g['away'])} @ {esc(g['home'])}</td>"
            f"<td>{src('schedule', g['game_id'])}</td>"
            f"<td class='n'>{esc(g['away_pts'])}</td><td class='n'>{esc(g['home_pts'])}</td>"
            f"<td class='n'>{esc(g['home_margin'])}</td>"
            f"<td class='n'>{esc(g['total_pts'])}</td>"
            + qs(aq) + qs(hq)
            + f"<td>{src('linescore', 'Q')}</td>"
            f"<td><a href='{esc(g['source_url'])}'>game</a></td></tr>")
    # history roll-up by date
    by_date: dict[str, list] = {}
    for g in hist:
        by_date.setdefault(g["date"], []).append(g)
    roll = []
    for d in sorted(by_date):
        gs = by_date[d]
        roll.append(
            f"<tr><td>{esc(d)}</td><td class='n'>{len(gs)}</td>"
            f"<td class='n'>{round(M.mean([g['total_pts'] for g in gs]), 1)}</td>"
            f"<td class='n'>{round(M.mean([g['home_margin'] for g in gs]), 2)}</td>"
            f"<td class='n'>{sum(1 for g in gs if g['home_margin'] > 0)}</td>"
            f"<td><a href='https://www.nba.com/games?date={esc(d)}'>games</a></td></tr>")
    stamp_html = "<p>No settlement stamp yet: no sealed game in this window has an official final.</p>"
    if stamp:
        stamp_html = (f"<div class='note'><b>Settlement stamp {esc(stamp['settled_at_utc'])}</b> — "
                      f"{stamp['n_graded']} graded, {stamp['n_ungraded']} ungraded; "
                      f"margin MAE {stamp['margin_mae']}, total MAE {stamp['total_mae']}, "
                      f"winner hit rate {stamp['winner_hit_rate']}.</div>")
    body = f"""
<div class="note"><b>One row per game: date, teams, final score, quarter scores.</b> The final
scores are official. Quarter scores were captured from the official LINESCORES table for one game;
the other four are blank and flagged <a href="verification-v3.html">F-304</a> rather than
estimated.</div>
<h2>{esc(O.WINDOW[0])} window — the day that just finished</h2>
{table(['Date', 'Matchup', 'Game', 'Away pts', 'Home pts', 'Home margin', 'Total',
        'Away quarters', 'Home quarters', 'Linescore src', 'Game page'], rows,
       caption="Quarter scores come from the official LINESCORES table on the game page.")}
<h2>Official result feed — every date in the committed history</h2>
{table(['Date', 'Games', 'Mean total', 'Mean home margin', 'Home wins', 'Source'], roll,
       caption=f"{len(hist)} official finals committed in this repository, deduplicated by "
               f"official game id.")}
<h2>Settlement</h2>
{stamp_html}
<p>Settlement runs only after the official final scores exist. A game with no official final stays
UNGRADED and is never counted as a loss. The stamp is written next to the pre-tip hash on
<a href="ledger.html">the ledger page</a> and the pre-tip digest is never overwritten.</p>"""
    return page("Result feed &amp; settlement", "results.html", body,
                "Official final scores and quarter scores, one row per game, with the settlement "
                "stamp for the sealed window.")


# ------------------------------------------------------------------------ ledger
def page_ledger(res: dict, seal_info: dict, prereg: list[dict]) -> str:
    ok, stored_digest, recomputed = LD.verify(LD.LEDGER_DIR / Path(seal_info["file"]).name)
    rows = []
    for p in LD.build_picks(res):
        rows.append(
            "<tr>"
            f"<td>{esc(p['date'])}</td><td>{esc(p['matchup'])}</td>"
            f"<td>{src('schedule', p['game_id'])}</td>"
            f"<td class='n'>{p['e1_margin']:+.2f}</td><td class='n'>{p['e2_margin']:+.2f}</td>"
            f"<td class='n'>{p['disagreement']:.2f}</td><td class='n'>{p['total']:.1f}</td>"
            f"<td class='n'>{p['p_home']:.3f}</td>"
            f"<td class='n'>{p['stake_pct']:.2f}%</td>"
            + cell(p["market_price"], reason="F-308 no market price feed")
            + f"<td>{src('team_adv')}</td></tr>")
    pre = "".join(
        f"<tr><td><b>{esc(p['id'])}</b></td><td>{esc(p['name'])}</td>"
        f"<td><code>{esc(p['file'])}</code></td>"
        f"<td><code>{esc(p['sha256'][:32])}…</code></td>"
        f"<td>{badge(p['status'], 'info')}</td>"
        f"<td><a href='https://github.com/wingbangboozle1-lang/NBA2/blob/main/{esc(p['file'])}'>"
        f"file</a></td></tr>" for p in prereg)
    detail = "".join(
        f"<tr><td><b>{esc(s['id'])}</b></td><td>{esc(s['name'])}</td><td>{esc(s['signal'])}</td>"
        f"<td><code>{esc(json.dumps(s['thresholds']))}</code></td><td>{esc(s['universe'])}</td>"
        f"<td>{esc(s['settlement_rule'])}</td>"
        f"<td><a href='https://github.com/wingbangboozle1-lang/NBA2/blob/main/"
        f"data/v3/prereg'>dir</a></td></tr>" for s in LD.STRATEGIES)
    body = f"""
<div class="note"><b>Hash before tip, verify after settlement.</b> The {seal_info['n']} rows below
were hashed at {esc(O.AS_OF_UTC)}, before the earliest tip in the window. The digest is
<code>{esc(seal_info['digest'])}</code>; recomputed at build time it is
<code>{esc(recomputed)}</code> — {'identical' if ok else 'MISMATCH'}. The pre-tip value is never
overwritten: settlement appends a second digest computed over the graded rows instead.</div>
<div class="kpis">
<div class="kpi"><b>{'VERIFIED' if ok else 'BROKEN'}</b><small>seal recomputed at build</small></div>
<div class="kpi"><b>{seal_info['n']}</b><small>sealed rows</small></div>
<div class="kpi"><b>0.00%</b><small>stake on every row (no price)</small></div>
<div class="kpi"><b>{len(prereg)}</b><small>pre-registered strategies</small></div>
</div>
<h2>Sealed picks</h2>
{table(['Date', 'Matchup', 'Game', 'E1', 'E2', 'Disagreement', 'Total', 'P(home)',
        'Stake', 'Market price', 'Src'], rows,
       caption="A row is excluded from the seal when either club is outside the luck noise "
               "band (|z| > 2.0).")}
<h2>Pre-registration files</h2>
<p>Each strategy is frozen in its own file before its first bet: the signal, every threshold, the
universe and the exact settlement rule. The file carries the sha256 of its own body, so a later
edit is detectable.</p>
{table(['ID', 'Strategy', 'File', 'sha256', 'Status', 'Link'], pre, scroll=False)}
<h2>What each strategy commits to</h2>
{table(['ID', 'Strategy', 'Signal', 'Thresholds', 'Universe', 'Settlement rule', 'Link'], detail,
       caption="Thresholds are declared, not fitted. No strategy has placed a bet.")}"""
    return page("Sealed ledger &amp; pre-registration", "ledger.html", body,
                "Content-addressed pre-registration and a pre-tip hash over every published "
                "pick, with settlement stamps appended after the official finals arrive.")


# ------------------------------------------------------------------ verification
def page_verification(res: dict, gates_out: dict, seal_info: dict) -> str:
    cc = res["crosschecks"]
    src_rows = "".join(
        f"<tr><td><code>{esc(k)}</code></td><td>{esc(v[0])}</td>"
        f"<td><a href='{esc(v[1])}'>{esc(v[1][:70])}…</a></td><td>{esc(v[2])}</td></tr>"
        for k, v in O.SOURCES.items())
    blocked_rows = "".join(
        f"<tr><td><b>{esc(k)}</b></td><td>{esc(v[0])}</td><td>{esc(v[1])}</td>"
        f"<td><a href='{esc(v[2])}'>source</a></td></tr>"
        for k, v in O.BLOCKED.items())
    flag_rows = "".join(
        f"<tr id='{esc(f[0])}'><td><b>{esc(f[0])}</b></td><td>{esc(f[1])}</td><td>{esc(f[2])}</td>"
        f"<td><a href='{esc(f[3])}'>check</a></td>"
        f"<td>{badge(f[4], 'bad' if f[4] == 'blocking' else ('warn' if f[4] == 'open' else 'off'))}</td></tr>"
        for f in O.FLAGS)
    gate_src = {"G-F1": "schedule", "G-F2": "schedule", "G-F3": "injury_index",
                "G-F4": "schedule", "G-F5": "standings",
                "G-P1": "schedule", "G-P2": "schedule", "G-P3": "schedule"}
    gate_rows = "".join(
        f"<tr><td><b>{esc(g['id'])}</b></td><td>{esc(g['name'])}</td>"
        f"<td>{badge('PASS' if g['pass'] else 'FAIL', 'ok' if g['pass'] else 'bad')}</td>"
        f"<td>{esc(g['detail'])}</td>"
        f"<td>{src(gate_src.get(g['id'], 'schedule'))}</td></tr>"
        for g in gates_out["gates"])
    luck_rows = "".join(
        f"<tr><td>{esc(r['team'])}</td><td>{esc(r['name'])}</td><td class='n'>{r['gp']}</td>"
        f"<td class='n'>{r['actual_wins']}</td><td class='n'>{r['expected_wins']}</td>"
        f"<td class='n'>{r['luck_wins']:+.2f}</td>"
        f"<td class='n'><b>{r['luck_z']:+.2f}</b></td>"
        f"<td class='n'>{r['luck_z_exp13.5']:+.2f}</td><td class='n'>{r['luck_z_exp16.5']:+.2f}</td>"
        f"<td>{badge('inside' if r['in_noise_band'] else 'OUTSIDE', 'ok' if r['in_noise_band'] else 'bad')}</td>"
        f"<td>{src('team_adv')} {src('standings')}</td></tr>" for r in res["luck"])
    worst = cc["pts_against_vs_opponent_page"]["worst"]
    body = f"""
<div class="note"><b>Verification is mechanical, not narrative.</b> The transcription carries its
own selftest (<code>python -m nba2.v3.official</code>), the emitted pages are re-checked for a
source on every row and a reason on every blank
(<code>python -m nba2.v3.check</code>), and the freshness gates below decide whether a rebuild may
publish at all.</div>
<div class="kpis">
<div class="kpi"><b>{gates_out['n_pass']} / {gates_out['n_pass'] + gates_out['n_fail']}</b><small>gates passing</small></div>
<div class="kpi"><b>{res['history']['n_games']}</b><small>official finals</small></div>
<div class="kpi"><b>{cc['pts_for_vs_traditional_page']['max_abs_diff']}</b><small>max pts-for disagreement</small></div>
<div class="kpi"><b>{cc['pts_against_vs_opponent_page']['max_abs_diff']}</b><small>max pts-against disagreement</small></div>
</div>
<h2>Freshness and provenance gates</h2>
<p>{esc(gates_out['policy'])}</p>
{table(['ID', 'Gate', 'Result', 'Detail', 'Src'], gate_rows, scroll=False)}
<h2>Official sources read this session</h2>
{table(['Key', 'Source', 'URL', 'What was taken from it'], src_rows)}
<h2>Inputs we do not have</h2>
{table(['Key', 'Input', 'Why it is missing', 'Where to check'], blocked_rows)}
<h2>Luck, as a z-score per club</h2>
<p>Pythagorean expected wins (exponent {M.PYTHAG_EXP}) from officially-sourced points for and
against, standardised by each club's own binomial sd. The band is |z| &le; {M.NOISE_BAND_Z}; a
strategy that leans on a club outside it is refused, not downgraded. Two further exponents are
published so a reader can see whether band membership is an artefact of the exponent.</p>
{table(['Club', 'Name', 'GP', 'Wins', 'Expected', 'Luck (wins)', 'z', 'z @13.5', 'z @16.5',
        'Band', 'Src'], luck_rows,
       caption=f"Clubs outside the band: {', '.join(res['outside_band']) or 'none'}.")}
<h2>Cross-checks published rather than reconciled</h2>
<p>{esc(cc['note'])}</p>
{table(['Club', 'Derived points against', 'Official Opp PTS', 'Difference'],
       ["<tr>" + f"<td>{esc(w['team'])}</td><td class='n'>{w['derived']}</td>"
        f"<td class='n'>{w['official']}</td>"
        f"<td class='n'>{round(w['derived'] - w['official'], 2):+.2f}</td>"
        f"<td>{src('team_opp')}</td><td>{src('team_adv')}</td></tr>" for w in worst])}
<h2>Measured rho for same-game parlays</h2>
<p>r(home margin, total points) = <b>{res['rho']['r']}</b> on n = {res['rho']['n']} official
finals, 95% CI {res['rho']['ci95']}. Independence is neither proven nor rejected at this sample
size. Parlays are priced at this measured rho and the naive product is printed beside it, never
instead of it.</p>
<h2>Flags raised this session</h2>
{table(['ID', 'Area', 'Finding', 'Source to check', 'Severity'], flag_rows)}
<h2>Seal</h2>
<p>{esc(seal_info['file'])} — {seal_info['n']} rows, sha256 <code>{esc(seal_info['digest'])}</code>.</p>"""
    return page("v3 verification", "verification-v3.html", body,
                "What was read, when, what it disagrees with, and which gates decide whether "
                "the rebuild may publish.")


# -------------------------------------------------------------------------- build
def link(url: str, label: str = "SRC") -> str:
    return f'<a href="{esc(url)}" title="{esc(url)}">{esc(label)}</a>'


# ------------------------------------------------- session arena/f8f8f2b8: player game logs
def page_player_logs() -> str:
    from . import playerlogs as PL

    meta = PL.game_log_meta()
    logs = PL.game_logs()
    cov = PL.injury_coverage()
    rows = "".join(
        "<tr>"
        f"<td>{esc(r['date'])}</td>"
        f"<td>{esc(r['matchup'])}</td>"
        f"<td>{esc(r['team'])}</td>"
        f"<td>{esc(r['opponent'])}</td>"
        f"<td>{esc(r['player'])}</td>"
        f"<td>{esc(r['pos']) or blank('FLAGGED I-F8F-14: no source for this cell - the box score prints no POS')}</td>"
        f"<td class='n'>{esc(r['min']) if r['min'] else blank('I-F8F-07')}</td>"
        f"<td class='n'>{esc(r['pts'])}</td>"
        f"<td class='n'>{esc(r['reb'])}</td>"
        f"<td class='n'>{esc(r['ast'])}</td>"
        f"<td>{link(r['source_url'], 'gamebook')}</td>"
        "</tr>"
        for r in logs)
    mrows = "".join(
        "<tr>"
        f"<td>{esc(p['team'])}</td><td>{esc(p['player'])}</td>"
        f"<td>{badge(p['status'], 'bad' if p['status'] == 'Out' else ('warn' if p['status'] == 'Questionable' else 'ok'))}</td>"
        f"<td>{esc(p['matchup'])}</td>"
        f"<td class='n'>{esc(m['min'])}</td><td class='n'>{esc(m['pts'])}</td>"
        f"<td class='n'>{esc(m['reb'])}</td><td class='n'>{esc(m['ast'])}</td>"
        f"<td>{link(m['log_source'], 'gamebook')}</td>"
        "</tr>"
        for p, m in ((p, next((x for x in cov["matched"]
                               if x["player"] == p["player"] and x["team"] == p["team"]), None))
                     for p in PL.injured_players())
        if m is not None)
    no_row = "".join(
        f"<tr><td>{esc(p['team'])}</td><td>{esc(p['player'])}</td>"
        f"<td>{esc(p['status'])}</td><td>{esc(p['reason'])}</td>"
        f"<td>{link(p['source_url'], 'injury PDF')}</td></tr>"
        for p in cov["no_row_in_captured_game"])
    no_club = "".join(
        f"<tr><td>{esc(p['team'])}</td><td>{esc(p['player'])}</td>"
        f"<td>{esc(p['status'])}</td><td>{esc(p['reason'])}</td>"
        f"<td>{link(p['source_url'], 'injury PDF')}</td></tr>"
        for p in cov["club_not_captured"])

    t_logs = table(["Date", "Matchup", "Team", "Opponent", "Player", "Pos", "MIN", "PTS",
                    "REB", "AST", "Source"], _rows(rows),
                   caption=f"{meta['n_rows']} rows, each linked to the official gamebook it "
                           f"was read from")
    t_matched = table(["Club", "Player", "Report status", "Next game", "MIN", "PTS", "REB",
                       "AST", "Source"], _rows(mrows))
    t_norow = table(["Club", "Player", "Status", "Reason", "Source"], _rows(no_row))
    t_noclub = table(["Club", "Player", "Status", "Reason", "Source"], _rows(no_club))
    clubs_not = esc(", ".join(cov["clubs_not_captured"]))
    clubs_yes = esc(", ".join(cov["clubs_captured"]))

    body = f"""
<div class="cards">
  <div class="card"><span class="k">Games captured</span><span class="v">{meta['n_games']}</span>
    <span class="s">every game played 2026-11-13</span></div>
  <div class="card"><span class="k">Clubs covered</span><span class="v">{meta['n_teams']} / 30</span>
    <span class="s">{clubs_yes}</span></div>
  <div class="card"><span class="k">Player log rows</span><span class="v">{meta['n_rows']}</span>
    <span class="s">minutes, points, rebounds, assists, opponent</span></div>
  <div class="card"><span class="k">Injured players matched</span>
    <span class="v">{cov['n_matched']} / {cov['n_injured_named']}</span>
    <span class="s">join to the 06:15 PM ET release</span></div>
</div>

<h2>Per-player game log</h2>
<p>One row per player per game, transcribed from the official NBA gamebook PDF. The minutes
column is the only one that can be blank: Memphis' Jerami Grant has no extracted minutes cell
in the official document, and the 25:39 the team total would imply is a residual, not a
published number, so it is left empty and flagged I-F8F-07.</p>
{t_logs}

<h2>Injured players who have a captured log row</h2>
<p>The brief asks for game logs for at least the players who appear on an injury report. These
are the named players on the newest official release who also appear in a captured box score.</p>
{t_matched}

<h2>Named on the injury report, but no row in a captured game</h2>
<p>These players' clubs <i>are</i> captured, so the absence is real: they did not play (or did
not dress) in the 2026-11-13 game, which is exactly what an "Out" designation predicts. A player
who did not play has no minutes to report, so there is nothing to put in the cell.</p>
{t_norow}

<h2>Clubs with no captured game in this window</h2>
<p>{clubs_not} did not play on 2026-11-13, so the players below have no game log here. Their
rows are blank and flagged &mdash; extending the capture to a second game day is the open action
for the next session.</p>
{t_noclub}
"""
    return page("Player game logs", "player-logs.html", body,
                "Per-player minutes, points, rebounds and assists from the official gamebook "
                "PDFs, joined to the official injury report.")


def _rows(html_rows: str) -> list[str]:
    """Split a concatenated ``<tr>…</tr>`` blob back into a list for :func:`table`."""
    return [f"{r}</tr>" for r in html_rows.split("</tr>") if r.strip()]


# ------------------------------------------- session arena/f8f8f2b8: measured minutes shares
def page_minutes() -> str:
    from . import playerlogs as PL

    tab = PL.minutes_table()
    exc = PL.excluded_teams()
    meta = PL.gamebook_meta()

    def pct(x):
        return "" if x is None else f"{x * 100:.1f}%"

    srows = "".join(
        "<tr>"
        f"<td>{esc(r['team'])}</td><td>{esc(r['opponent'])}</td>"
        f"<td class='n'>{esc(r['n_games'])}</td>"
        f"<td class='n'>{esc(pct(r['top8_share']))}</td>"
        f"<td class='n'>{esc(pct(r['max_share']))}</td>"
        f"<td class='n'>{esc(pct(r['bench_share']))}</td>"
        f"<td class='n'>{esc(r['n_bench'])}</td>"
        f"<td class='n'>{esc('' if r['hhi_top8'] is None else format(r['hhi_top8'], '.3f'))}</td>"
        f"<td>{link(r['source_url'], 'gamebook')}</td>"
        "</tr>"
        for r in tab)
    drows = "".join(
        "<tr>"
        f"<td>{esc(r['team'])}</td><td class='n'>{esc(i + 1)}</td>"
        f"<td>{esc(p['player'])}</td><td>{esc(p['pos']) or blank('FLAGGED I-F8F-14: no source for this cell - the box score prints no POS')}</td>"
        f"<td class='n'>{esc(p['min'])}</td>"
        f"<td class='n'>{esc(pct(p['share']))}</td>"
        f"<td class='n'>{esc(p['pts'])}</td><td class='n'>{esc(p['reb'])}</td>"
        f"<td class='n'>{esc(p['ast'])}</td>"
        f"<td>{link(r['source_url'], 'gamebook')}</td>"
        "</tr>"
        for r in tab for i, p in enumerate(r["top8"]))
    prows = "".join(
        "<tr>"
        f"<td>{esc(r['team'])}</td><td>{esc(p['player'])}</td>"
        f"<td class='n'>{esc(p['min'])}</td>"
        f"<td class='n'>{esc(pct(p['share']))}</td>"
        f"<td class='n'>{esc(p['pts'])}</td><td class='n'>{esc(p['reb'])}</td>"
        f"<td class='n'>{esc(p['ast'])}</td>"
        f"<td>{link(r['source_url'], 'gamebook')}</td>"
        "</tr>"
        for r in tab for p in r["bench"])
    erows = "".join(
        f"<tr><td>{esc(e['team'])}</td><td>{esc(e['game_id'])}</td>"
        f"<td>{esc(e['reason'])}</td>"
        f"<td><b>{esc(e['flag'])}</b></td>"
        f"<td>{link(e['source_url'], 'gamebook') if e['source_url'] else ''}</td></tr>"
        for e in exc)

    t_sum = table(["Club", "Opponent", "Games", "Top-8 share", "Largest share", "Bench share",
                   "Bench players", "Top-8 HHI", "Source"], _rows(srows),
                  caption="Minutes shares measured from the official gamebook PDFs for "
                          "2026-11-13")
    t_top = table(["Club", "#", "Player", "Pos", "MIN", "Share", "PTS", "REB", "AST",
                   "Source"], _rows(drows))
    t_pool = table(["Club", "Player", "MIN", "Share", "PTS", "REB", "AST", "Source"],
                   _rows(prows))
    t_exc = table(["Club", "Game", "Reason", "Flag", "Source"], _rows(erows))
    exc_names = esc(", ".join(e["team"] for e in exc)) or "none"
    gate_list = "".join(f"<li><b>{esc(k)}</b> &mdash; {esc(v)}</li>"
                        for k, v in meta["gates"].items())
    no_delta = blank("needs 2 games")

    body = f"""
<div class="cards">
  <div class="card"><span class="k">Clubs measured</span><span class="v">{len(tab)} / 30</span>
    <span class="s">one captured game each, 2026-11-13</span></div>
  <div class="card"><span class="k">Excluded by a gate</span><span class="v">{len(exc)}</span>
    <span class="s">{exc_names}</span></div>
  <div class="card"><span class="k">Rotation size</span><span class="v">top 8</span>
    <span class="s">minutes shares, not a fitted rating</span></div>
  <div class="card"><span class="k">Observed in/out delta</span>
    <span class="v">{no_delta}</span>
    <span class="s">blank by design &mdash; see the note below</span></div>
</div>

<h2>Measured top-8 minutes shares</h2>
<p>Every share is <code>player minutes / (240:00 + 25:00 &times; OT)</code> read straight off
the official box score. This replaces the mechanical rule the site used to publish with a
measurement, which is what the brief asks for. <b>HHI</b> is the Herfindahl index of the top-8
shares: higher means the club leans harder on fewer players, so an injury to a high-share
player is more disruptive.</p>
{t_sum}

<h2>Top-8 detail</h2>
<p>Eight rows per club, ordered by minutes played.</p>
{t_top}

<h2>Replacement pool &mdash; who is behind the top eight</h2>
<p>These are the players ranked ninth and below by minutes in the same official box score.
Their measured shares are the minutes available to absorb a missing rotation player's load.
This is a measured <i>pool</i>, not an observed <i>delta</i>.</p>
{t_pool}

<h2>Why there is no observed injury-replacement delta</h2>
<p>Measuring <i>who actually absorbed the minutes when player X was out</i> needs at least two
captured games for the same club, one with X and one without. This window contains exactly one
captured game per club, so that column would have to be back-solved from a single game and is
left {blank("blank")} instead. The mechanical rule the site published before this session stays
in place as the labelled fallback until a second game day is captured.</p>

<h2>Clubs excluded by the minutes gate</h2>
<p>A club is excluded when its captured team-game fails the official-sum gate. The gate is
fail-closed: the club is dropped from the tables above rather than repaired.</p>
{t_exc}

<h2>Gates applied to every team-game</h2>
<ul>
{gate_list}
</ul>
"""
    return page("Measured minutes", "minutes.html", body,
                "Rotation minutes measured from the official gamebook PDFs, with the "
                "replacement pool behind each top eight.")


# ------------------------------------------- session arena/f8f8f2b8: injury release diff
def page_injury_diff() -> str:
    from . import playerlogs as PL

    d = PL.injury_release_diff()
    delta, st = d["delta"], PL.release_stamps()
    changes = delta["status_changes"]
    added, removed = delta["added"], delta["removed"]

    crows = "".join(
        "<tr>"
        f"<td>{esc(c['date'])}</td><td>{esc(c['matchup'])}</td><td>{esc(c['team'])}</td>"
        f"<td>{esc(c['player'])}</td>"
        f"<td>{badge(c['from_status'], 'warn')}</td>"
        f"<td>{badge(c['to_status'], 'ok' if c['to_status'] == 'Available' else ('bad' if c['to_status'] == 'Out' else 'warn'))}</td>"
        f"<td>{esc(c['reason_to'])}</td>"
        f"<td>{esc('yes' if c['reason_changed'] else 'no')}</td>"
        f"<td>{link(st['report_url'], 'new')} &middot; {link(st['prior_report_url'], 'old')}</td>"
        "</tr>"
        for c in changes)
    arows = "".join(
        f"<tr><td>{esc(a['date'])}</td><td>{esc(a['matchup'])}</td><td>{esc(a['team'])}</td>"
        f"<td>{esc(a['player']) or blank('FLAGGED I-F8F-13: no source for this cell - the release prints no player')}</td>"
        f"<td>{esc(a['status'])}</td><td>{esc(a['reason'])}</td>"
        f"<td>{link(st['report_url'], 'PDF')}</td></tr>"
        for a in added)
    rrows = "".join(
        f"<tr><td>{esc(a['date'])}</td><td>{esc(a['matchup'])}</td><td>{esc(a['team'])}</td>"
        f"<td>{esc(a['player']) or blank('FLAGGED I-F8F-13: no source for this cell - the release prints no player')}</td>"
        f"<td>{esc(a['status'])}</td><td>{esc(a['reason'])}</td>"
        f"<td>{link(st['prior_report_url'], 'PDF')}</td></tr>"
        for a in removed)
    QUIRKS = [
        ("I-F8F-01", "Page-continuation rows print with an empty team / date / time / matchup "
                     "cell; the value has to be inherited from the block in progress.",
         "warn", st["report_url"], "PDF"),
        ("I-F8F-02", 'The ORL@BOS block prints a second "Penda, Noah" row under the '
                     "<i>Boston Celtics</i> team cell with the reason NOT YET SUBMITTED.",
         "warn", st["report_url"], "PDF"),
        ("I-F8F-03", "The NYK@TOR block contains no New York Knicks rows at all in this "
                     "release &mdash; not even a placeholder.",
         "warn", st["report_url"], "PDF"),
        ("I-F8F-04", 'Game times are printed in 12-hour form with no AM/PM marker (IND@PHI '
                     'shows "01:00 (ET)" for a 13:00 ET tip). The 24-hour clock on '
                     + link("slate.html", "the slate page") + " is authoritative.",
         "warn", st["report_url"], "PDF"),
        ("I-F8F-05", "Player minutes occasionally sum to one second above or below the printed "
                     "240:00 team total (5 of 18 club-games here).", "off",
         "https://statsdmz.nba.com/pdfs/20261113/20261113_MILORL_book.pdf", "MIL@ORL book"),
        ("I-F8F-06", "MIL@ORL: the SCORE BY PERIOD row for Orlando did not extract (it reads "
                     '"33 33 33 33", summing to 132 against a final of 107). Quarter scores for '
                     "that game are left blank.", "warn",
         "https://statsdmz.nba.com/pdfs/20261113/20261113_MILORL_book.pdf", "MIL@ORL book"),
        ("I-F8F-07", "MEM@NOP: the MIN cell for Memphis' Jerami Grant did not extract. His "
                     "minutes are recorded as null and Memphis is excluded from the measured "
                     "shares rather than back-solved from the team total.", "warn",
         "https://statsdmz.nba.com/pdfs/20261113/20261113_MEMNOP_book.pdf", "MEM@NOP book"),
        ("I-F8F-09", "UTA@HOU and POR@SAC: the SCORE BY PERIOD table row and the gamebook's "
                     "repeated footer line disagree for the home club; only the footer "
                     "reconciles to the printed final. Both readings are recorded in the "
                     "capture file.", "warn",
         "https://statsdmz.nba.com/pdfs/20261113/20261113_UTAHOU_book.pdf", "UTA@HOU book"),
        ("I-F8F-11", "nba2/v3/official.py carries the injury release as 11/15/26 06:00 AM ET "
                     'with "newest indexed 06:15 AM ET". The official index now lists releases '
                     "through <b>06:15 PM ET</b>, twelve hours later. Logged as a cross-scope "
                     "request; that file is not edited here.", "warn",
         st["index_url"], "official index"),
        ("I-F8F-12", "DEN@NOP (2026-11-14) and OKC@LAC: the PDF prints the same surname twice "
                     "in one club's inactive list (two distinct Williams entries for OKC), so a "
                     "last-name-only join would over-count.", "off",
         "https://statsdmz.nba.com/pdfs/20261113/20261113_OKCLAC_book.pdf", "OKC@LAC book"),
    ]
    qrows = "".join(
        f'<tr id="{esc(fid)}"><td><b>{esc(fid)}</b></td><td>{desc}</td>'
        f'<td>{badge("open", "warn") if sev == "warn" else badge("informational", "off")}</td>'
        f"<td>{link(u, lab)}</td></tr>"
        for fid, desc, sev, u, lab in QUIRKS)
    t_quirks = table(["Flag", "What the official document does", "Severity",
                      "Source to check"], _rows(qrows))

    t_changes = table(["Game date", "Matchup", "Team", "Player", "From", "To", "Reason (new)",
                       "Reason changed?", "Source"], _rows(crows))
    t_added = table(["Game date", "Matchup", "Team", "Player", "Status", "Reason", "Source"],
                    _rows(arows))
    t_removed = table(["Game date", "Matchup", "Team", "Player", "Status", "Reason", "Source"],
                      _rows(rrows))

    body = f"""
<div class="banner">
  <div><span class="k">Report revision time</span><span class="v">{esc(st['revision_time_et'])}</span>
    <span class="s">the stamp printed on the PDF</span></div>
  <div><span class="k">Retrieved</span><span class="v">{esc(st['retrieved_at_utc'])}</span>
    <span class="s">when this session fetched it</span></div>
  <div><span class="k">Compared against</span><span class="v">{esc(st['prior_revision_time_et'])}</span>
    <span class="s">{esc(st['elapsed'])} earlier, same day</span></div>
  <div><span class="k">Source</span>
    <span class="v">{link(st['report_url'], '06:15 PM PDF')}</span>
    <span class="s">{link(st['index_url'], 'official index')} · {link(st['prior_report_url'], '06:15 AM PDF')}</span></div>
</div>

<h2>Release-to-release movement</h2>
<div class="cards">
  <div class="card"><span class="k">Rows in the 06:15 AM release</span>
    <span class="v">{d['am_rows']}</span></div>
  <div class="card"><span class="k">Rows in the 06:15 PM release</span>
    <span class="v">{d['pm_rows']}</span></div>
  <div class="card"><span class="k">Status changes</span>
    <span class="v">{len(changes)}</span>
    <span class="s">same player, different designation</span></div>
  <div class="card"><span class="k">Unchanged</span><span class="v">{delta['counts']['unchanged']}</span></div>
  <div class="card"><span class="k">Added</span><span class="v">{len(added)}</span>
    <span class="s">includes clubs replacing a placeholder with a full submission</span></div>
  <div class="card"><span class="k">Removed</span><span class="v">{len(removed)}</span></div>
</div>

<h2>Status changes</h2>
<p>These are real designation movements between two consecutive official releases, detected by
a mechanical diff on (date, matchup, team, player). A change from <i>Questionable</i> to
<i>Available</i> moves a rotation decision; a change to <i>Out</i> removes minutes that the
{link('minutes.html', 'measured minutes page')} shows have to be reallocated.</p>
{t_changes}

<h2>Added in the 06:15 PM release</h2>
<p>A large added count between a morning and an evening release is expected, not an error: clubs
playing the following day replace a single "NOT YET SUBMITTED" placeholder with their full
submission as the 5 p.m. local deadline passes.</p>
{t_added}

<h2>Present in 06:15 AM, absent from 06:15 PM</h2>
{t_removed}

<h2>Irregularities in the official PDF itself</h2>
<p>Found while transcribing. None of these is corrected in the data — each is reproduced exactly
as the league published it and flagged so a reviewer can check the source document.</p>
{t_quirks}
"""
    return page("Injury release diff", "injury-diff.html", body,
                "Two consecutive official injury releases, diffed mechanically, with the "
                "revision and retrieval stamps shown side by side.")


def build(verbose: bool = False) -> tuple[list[str], dict]:
    SITE.mkdir(exist_ok=True)
    (SITE / "assets").mkdir(exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    res = M.build()
    prereg = LD.write_prereg()
    seal_info = LD.seal(res)
    stamp = LD.settle(res, [g for g in M.load_played_games()["games"] if g["date"] < O.WINDOW[0]])
    res["settlement"] = stamp

    pages = {
        "slate.html": page_slate(res),
        "projections.html": page_projections(res),
        "rotation.html": page_rotation(res),
        "travel.html": page_travel(res),
        "results.html": page_results(res, stamp),
        "ledger.html": page_ledger(res, seal_info, prereg),
        "player-logs.html": page_player_logs(),
        "minutes.html": page_minutes(),
        "injury-diff.html": page_injury_diff(),
        "verification-v3.html": page_verification(res, G.run(res), seal_info),
    }
    for name, doc in pages.items():
        # Normalise every href to double quotes: the whole-repository checkers
        # (nba2/v2/check.py and tools/check_links_all.py) match on href="...", and a
        # single-quoted attribute would read as an unsourced row.
        doc = re.sub(r"href='([^']*)'", r'href="\1"', doc)
        (SITE / name).write_text(doc)

    inject_nav()
    gates_out = G.run(res, [SITE / n for n in V3_PAGES])

    (DATA / "model.json").write_text(json.dumps({
        "as_of_utc": res["as_of_utc"], "window": res["window"],
        "home_court": res["home_court"], "rho": res["rho"],
        "luck": res["luck"], "outside_band": res["outside_band"],
        "lines": res["lines"], "history": res["history"],
    }, indent=2))
    (DATA / "verification.json").write_text(json.dumps({
        "as_of_utc": res["as_of_utc"],
        "gates": gates_out,
        "crosschecks": res["crosschecks"],
        "flags": [{"id": f[0], "area": f[1], "finding": f[2], "source": f[3], "severity": f[4]}
                  for f in O.FLAGS],
        "sources": O.SOURCES, "blocked": O.BLOCKED,
        "seal": seal_info, "settlement": stamp,
        "prereg": prereg,
    }, indent=2))
    return V3_PAGES, {"gates": gates_out, "seal": seal_info, "settlement": stamp,
                      "n_lines": len(res["lines"])}


def inject_nav() -> int:
    """Idempotently add the v3 links to every generated page that has a <nav>."""
    marker = '<a href="slate.html"'
    n = 0
    for p in sorted(SITE.glob("*.html")):
        if p.name in V3_PAGES:
            continue
        doc = p.read_text()
        if "</nav>" not in doc or marker in doc:
            continue
        block = ("\n".join(f'<a href="{h}">{l}</a>' for h, l in V3_NAV))
        doc = doc.replace("</nav>", block + "\n</nav>", 1)
        p.write_text(doc)
        n += 1
    return n


if __name__ == "__main__":
    pages, summary = build()
    print(f"built {len(pages)} pages: {', '.join(pages)}")
    print(json.dumps(summary["gates"], indent=2)[:800])
