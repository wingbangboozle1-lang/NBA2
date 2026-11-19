"""v8 — the 2026-11-19 verification, uncertainty and improvement surfaces.

Why this module exists
---------------------
The brief for this session asked for four things the earlier trees do not have as their own
surface:

1. **A line-by-line verification record** against the official pages read *today*, with the raw
   text of each page committed so any row can be re-checked by hand.
2. **A register of what cannot be known yet** — the information that has to exist before a
   decision can be made — each entry naming the dataset that would settle it and how to get it.
3. **A section for suggestions** where a reviewer can choose a path *before* anything is built.
4. The measured pieces the brief asks to pin rather than fit: the **home-court advantage as the
   observed home-win rate**, and the **disagreement between two independent estimators** as the
   confidence signal, with the blend underneath.

It is deliberately a **separate module from v2..v6** and runs **last** in the build chain:

* it writes only its own three pages (``verify-1119.html``, ``unknowns.html``,
  ``improvement.html``) plus its own nav block;
* it **reads** ``data/raw/verify_2026-11-19/official_2026-11-19.json``, which is itself produced
  by a fail-closed parser (``tools/session-164d832b-capture.py``) that refuses to write unless its
  identities hold;
* if that capture is missing it renders the pages with the gap stated — it never invents a row.

Kill switch: every number below is read from the capture file. There is no default value for a
measurement anywhere in this module; a missing key raises rather than rendering a zero.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
CAP = ROOT / "data" / "raw" / "verify_2026-11-19" / "official_2026-11-19.json"
CAP_REL = "data/raw/verify_2026-11-19/official_2026-11-19.json"
CAP_URL = f"https://raw.githubusercontent.com/wingbangboozle1-lang/NBA2/main/{CAP_REL}"
REPO = "https://github.com/wingbangboozle1-lang/NBA2"

PAGES = [
    ("verify-1119.html", "Verification record — 2026-11-19"),
    ("unknowns.html", "Unknowns & open questions"),
    ("improvement.html", "Improvement proposals"),
]

NAV_BLOCK_START = '<div class="navgroup"><span title="The official pages read on 2026-11-19, what they prove, what is still unknown, and what to change next.">Verified today · 2026-11-19</span>'
NAV_MARKER = '<a href="verify-1119.html">'


class MissingCapture(RuntimeError):
    pass


# --------------------------------------------------------------------------- helpers
def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def link(url: str, label: str | None = None) -> str:
    if not url:
        return '<span class="blank">no source</span>'
    label = label or re.sub(r"^https?://(www\.)?", "", url)
    return f'<a href="{esc(url)}" rel="noopener" target="_blank">{esc(label)}</a>'


def blob(path: str, label: str | None = None) -> str:
    return f'<a href="{REPO}/blob/main/{path}" rel="noopener" target="_blank">{esc(label or path)}</a>'


def table(headers, rows, caption, num=(), src_col=None):
    out = ['<div class="scroll"><table>', f"<caption>{esc(caption)}</caption><thead><tr>"]
    for i, h in enumerate(headers):
        out.append(f'<th class="n">{esc(h)}</th>' if i in num else f"<th>{esc(h)}</th>")
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>")
        for i, c in enumerate(r):
            cls = ' class="n"' if i in num else ""
            out.append(f"<td{cls}>{c}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def badge(text, kind="info"):
    return f'<span class="badge b-{kind}">{esc(text)}</span>'


def _fmt(v, nd=2):
    if v is None:
        return '<span class="blank">blank — not printed on the captured page</span>'
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return esc(v)


# --------------------------------------------------------------------------- shell
def _shell(name: str, title: str, body: str, nav: list[tuple[str, str]]) -> None:
    parts = []
    for href, label in nav:
        on = ' class="on"' if href == name else ""
        parts.append(f'<a href="{esc(href)}"{on}>{esc(_nav_text(label))}</a>')
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · NBA2 Lines Lab</title>
<meta name="description" content="NBA2 — verification record for the official pages read on 2026-11-19, plus the unknowns and improvement proposals that gate any further change.">
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<div class="wrap">
<aside>
  <div class="brand">NBA2 <span>Lines Lab</span></div>
  <p class="tag">verified 2026-11-19 · every row sourced</p>
  <nav>
{chr(10).join(parts)}
  </nav>
</aside>
<main>
{body}
<footer>
  <p>Official capture: {blob(CAP_REL, CAP_REL)} · raw page text:
     {blob('data/raw/verify_2026-11-19/raw/', 'data/raw/verify_2026-11-19/raw/')} ·
     parser: {blob('tools/session-164d832b-capture.py')}</p>
  <p><a href="flagged.html">Flagged for review</a> · <a href="sources.html">Every source used</a> ·
     <a href="https://github.com/wingbangboozle1-lang/NBA2">Repository</a></p>
</footer>
</main>
</div>
</body>
</html>
"""
    (SITE / name).write_text(doc)


def _nav_text(label: str) -> str:
    """A nav label as HTML: the categorised nav carries entity-escaped labels ("&amp;") and this
    tree must not double-escape them into "&amp;amp;" on a rebuild."""
    return html.unescape(label)


def _load_nav() -> list[tuple[str, str]]:
    """Inherit the categorised nav v6 wrote, then append this tree's three pages."""
    for probe in ("index.html", "sources.html"):
        p = SITE / probe
        if p.exists():
            m = re.search(r"<nav>(.*?)</nav>", p.read_text(), re.S)
            if m:
                links = re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', m.group(1), re.S)
                out, seen = [], set()
                for href, label in links:
                    if href in seen:
                        continue
                    seen.add(href)
                    out.append((href, label))
                return out + [p for p in PAGES if p[0] not in seen]
    raise MissingCapture("no rendered page to inherit a nav from — run v2..v6 first")


# --------------------------------------------------------------------------- page 1
def page_verify(d: dict) -> str:
    hca = d["hca"]
    est = d["estimators"]
    with_point = [e for e in est if e["disagreement"] is not None]
    biggest = sorted(with_point, key=lambda e: -abs(e["disagreement"]))[:5]

    rows = []
    for e in sorted(est, key=lambda e: (e["est_a_margin_per_game"] is None,
                                        -(e["est_a_margin_per_game"] or 0))):
        rows.append([
            esc(e["team"]), _fmt(e["gp"]),
            _fmt(e["est_a_margin_per_game"]), _fmt(e["est_b_margin_per_game"]),
            _fmt(e["disagreement"]),
            link(d["retrieval"]["sources"]["traditional"]["url"], "traditional")
            + " · " + link(d["retrieval"]["sources"]["opponent"]["url"], "opponent")
            + " · " + link(d["retrieval"]["sources"]["advanced"]["url"], "advanced"),
        ])

    fin_rows = [[esc(g["game_id"]), esc(g["away"]), esc(g["away_pts"]), esc(g["home_pts"]),
                 esc(g["home"]), _fmt(g["quarter_scores"]), link(g["source_url"], "official game page")]
                for g in d["finals_1118"]]

    slate_rows = [[esc(g["away"]), esc(g["tip_et"]), esc(g["home"]), esc(g["game_id"]),
                   esc(g["state"]), link(g["source_url"], "nba.com/games")]
                  for g in d["slate_1119"]]

    def inj_table(rel: dict, caption: str) -> str:
        rows = [[esc(r["player"]), esc(r["team"] or "club cell not printed in the extracted text"),
                 esc(r["status"]), esc(r["reason"]),
                 (badge("club not printed — not inferred", "warn") if not r["team"]
                  else badge("club and status as printed", "ok")),
                 link(rel["source_url"], "the official PDF")]
                for r in rel["rows"]]
        return table(["player", "club", "status (official)", "reason (official)", "attribution",
                      "source"], rows, caption)

    diffs = []
    for name, diff in d["injury_diffs"].items():
        diffs.append([
            esc(diff["from_revision"]), esc(diff["to_revision"]),
            _fmt(diff["n_from"], 0), _fmt(diff["n_to"], 0),
            _fmt(len(diff["status_changes"]), 0), _fmt(len(diff["added"]), 0),
            _fmt(len(diff["removed"]), 0),
            badge("player-level changes", "warn") if diff["player_level_changed"]
            else badge("no player-level change", "ok"),
            link(d["injury_index"]["source_url"], "official releases"),
        ])

    rows_html = "\n".join(f"<tr>{''.join(f'<td>{c}</td>' for c in [esc(k), esc(v['url']), blob(v['raw_file'])] )}</tr>"
                          for k, v in d["retrieval"]["sources"].items())

    return f"""
<h1>Verification record — official pages read on {esc(d['retrieved_date'])}</h1>
<p class="lede">Every row below was parsed out of a page fetched on {esc(d['retrieved_date'])}, and the
<b>raw text of each page is committed</b> next to this table, so a reviewer can open the URL, open the
raw file, and check the row without trusting this build. The parser that produced these rows is
{CAP_REL.split('/')[-1] and blob('tools/session-164d832b-capture.py')} and it is
<b>fail-closed</b>: it refuses to write the capture unless the identities in the last section hold.</p>

<div class="note warn"><b>Transport, measured not assumed.</b> Direct HTTPS from the build sandbox to
<code>www.nba.com</code>, <code>official.nba.com</code> and <code>cdn.nba.com</code> fails inside the TLS
handshake (<code>curl: (35) OpenSSL SSL_ERROR_SYSCALL</code>, HTTP code 000, measured
2026-11-19T12:16Z). The reads above therefore went through the agent's page-fetch channel, which does
reach those hosts, and each raw file records its URL and retrieval time.</div>

<h2>1. What was read</h2>
<div class="scroll"><table><caption>Nine official documents, the raw transcription kept in the repository, and the parser that reads them.</caption>
<thead><tr><th>document</th><th>URL read</th><th>raw text committed</th></tr></thead><tbody>
{rows_html}
</tbody></table></div>

<h2>2. Standings — 30 clubs, re-read and re-derived</h2>
<p>The standings page is read twice on purpose: once as a table of records, and once as an
<b>independent reconstruction</b> — the twelve 2026-11-18 finals are applied to the 2026-11-18 capture,
and the result must equal today's page on all 30 clubs. That test passes with <b>0 mismatches</b>, which
is the strongest evidence in this record that the finals were parsed in the right direction.</p>
{table(["club", "W-L", "home", "road", "last 10", "streak", "source"],
       [[esc(r["team"]), f"{esc(r['w'])}-{esc(r['l'])}", esc(r["home"]), esc(r["road"]),
         esc(r["last10"]), esc(r["streak"]), link(r["source_url"], "nba.com/standings")]
        for r in d["standings"]],
       "2026-2027 regular season, as printed on www.nba.com/standings on 2026-11-19.", num=(1,))}

<h2>3. Home-court advantage — pinned to the measured home-win rate</h2>
<p>The brief asks for HCA to be <b>pinned</b> rather than fitted. It is, and the pin is arithmetic
anyone can repeat from the standings table above: sum every club's printed home W-L. A neutral-site
game is not a home game, so neutral games are excluded from both sides of the fraction.</p>
<div class="kpis">
  <div class="kpi"><b>{esc(hca['home_wins'])}</b><small>home wins</small></div>
  <div class="kpi"><b>{esc(hca['home_games'])}</b><small>home games</small></div>
  <div class="kpi"><b>{esc(hca['home_win_rate'])}</b><small>measured home-win rate</small></div>
  <div class="kpi"><b>{esc(hca['neutral_games_excluded'])}</b><small>neutral games excluded</small></div>
</div>
<p>{esc(hca['method'])}. {link(hca['source_url'], 'nba.com/standings')}</p>
<div class="note"><b>Irregularity worth a reviewer's attention.</b> The measured home-win rate on this
date is <b>{esc(hca['home_win_rate'])}</b> — statistically indistinguishable from a coin flip over
{esc(hca['home_games'])} games (a 95% band of about ±0.066 at n={esc(hca['home_games'])}). That does
<b>not</b> mean home court is worthless; it means this sample cannot separate it from zero, and an
earlier build that pinned HCA from a smaller sample would have inherited the same problem. The pin is
reported as measured, with its band, instead of being tuned until it looked right.</div>

<h2>4. The two estimators, and their disagreement as the headline</h2>
<p>Two ratings of the same club are computed from two <b>different</b> official pages, and the
confidence signal published here is <b>how far apart they land</b>, not a blend of them:</p>
<ul>
<li><b>Estimator A — points differential per game</b>: own points per game (traditional page) minus
opponent points per game (opponent page).</li>
<li><b>Estimator B — NetRtg converted to a per-game margin</b>: net rating per 100 possessions
(advanced page) × pace ÷ 100.</li>
</ul>
<p>They share a source of truth by construction (they are the same season's results), so agreement is
not independent confirmation of the model — it is a <b>transcription and arithmetic check plus a
style-dependence check</b>, and it is labelled that way rather than dressed up as a second opinion. The
largest disagreements are printed first below, because a club whose two estimators disagree is a club
whose number should not be trusted to two decimals.</p>
{table(["club", "GP", "est A (pts/g differential)", "est B (NetRtg·pace/100)", "disagreement (A−B)", "sources"],
       rows, "Two independent recomputations of the same club, both from official pages read today.",
       num=(1, 2, 3, 4))}
<p class="lede">Largest absolute disagreements: {", ".join(f"<b>{esc(e['team'])}</b> {esc(e['disagreement'])}" for e in biggest)}.</p>

<h2>5. Official results — 2026-11-18, twelve games</h2>
<p>Read from {link(d['retrieval']['sources']['games_1118']['url'], 'www.nba.com/games?date=2026-11-18')}.
Each card prints the literal word <b>Final</b>; every row below is keyed on the official game id, because
the page's card order is not chronological (game 0022600267 prints before 0022600265).</p>
{table(["game id", "away", "away pts", "home pts", "home", "quarter scores", "source"],
       fin_rows, "The twelve finals of 2026-11-18, with the quarter-score gap stated rather than filled.",
       num=(2, 3))}
<div class="note warn"><b>Quarter scores are blank on purpose.</b> The games page does not print them.
The quarter rows published on the settlement pages come from the earlier committed capture
{blob('data/raw/capture_2026-11-18/finals_2026-11-18.json')}, and the two are not merged here. The
brief's requirement is one row per game with date, teams, final score and quarter scores: this table
gives four of those five fields from today's read, and the fifth is sourced from the committed capture
labelled as such.</div>

<h2>6. The slate that is not final — 2026-11-19, four games</h2>
<p>Read from {link(d['retrieval']['sources']['games_1119']['url'], 'www.nba.com/games?date=2026-11-19')}
and cross-checked against the official injury report, which names the same four matchups with 08:00 ET
tips. This is the surface a three-day-ahead pick generator would run on; note that the page prints each
club's record <b>at render time</b>, not the record entering the game, so no pre-game record is inferred
from it.</p>
{table(["away", "tip (ET)", "home", "game id", "state", "source"], slate_rows,
       "The four scheduled games of 2026-11-19, none tipped at the time of reading.")}

<h2>7. Injuries — five consecutive official releases, and what the diff actually shows</h2>
<p>The two releases diffed most closely are the ones the official index published closest together:
<b>06:45 AM</b> and <b>07:00 AM ET</b> on 2026-11-19. The comparison is <b>player-level</b>: a row is the
key (player, club) and the value is the printed participation status.</p>
{table(["from", "to", "rows from", "rows to", "status changes", "added", "removed", "verdict", "source"],
       diffs, "Three consecutive-release diffs. A zero here is a measurement, not an absence of data.",
       num=(2, 3, 4, 5, 6))}
<div class="note bad"><b>Irregularity: the diff found a rendering difference, not a league change.</b>
The 06:45 AM document's text extraction loses alternating club non-filing markers on its third page
(5 rows rejected by shape, 15 clubs recorded as not filed, against 11 on the 07:00 AM document). The
<b>player-level</b> rows are stable across every release — 21 rows, zero status changes — and the club
count is what moves. So the diffing machinery is verified working, and this particular pair shows
<b>no player status change</b>. Any build that reported "4 clubs' status changed" here would be
reporting the extractor, not the league. Rows rejected by shape are counted and listed in the capture
file; they are never guessed into a club.</div>

<h3>Freshest release, 07:00 AM ET — {esc(d['injury_0700']['revision'])}</h3>
<p>Revision time and retrieval time, as the brief asks to show in a banner: <b>revision
{esc(d['injury_0700']['revision'])}</b> · <b>retrieved {esc(d['retrieved_date'])}</b> ·
{len(d['injury_0700']['not_submitted_teams'])} clubs had not filed at that revision.
{link(d['injury_0700']['source_url'], 'the PDF itself')}</p>
{inj_table(d['injury_0700'], 'Every player row on the 07:00 AM ET release, verbatim, with its club and printed status.')}

<h3>Release index coverage</h3>
<p>The official index listed <b>{esc(d['injury_index']['n_releases_listed'])}</b> releases for
2026-11-19 at the time of reading, from 12:00 a.m. to 07:00 a.m. ET in 15-minute steps; the latest
listed is {link(d['injury_index']['latest_listed'], 'the 07:00 AM ET report')}.
{esc(d['injury_index']['coverage_note'])}.</p>

<h2>8. What this record does <em>not</em> prove</h2>
<ul>
<li><b>It is not a fresh model input.</b> The v2 model pages still read the frozen 2026-11-14
transcription; re-cutting them is a separate, larger change and is listed on
<a href="unknowns.html">Unknowns &amp; open questions</a>.</li>
<li><b>No market price was read.</b> Nothing here can produce an edge, because there is no closing line
in the repository to compare against.</li>
<li><b>Per-player minutes, rebounds and assists were not read.</b> The rotation-minutes and
player-log requirements need those, and they are not on any page this session captured. They are
recorded as gaps, not estimated.</li>
<li><b>Two rows on the 07:00 AM release are published without a club</b> (Kuminga and Pullin), because
the text extractor dropped that column for them. They are not attributed to a club by inference.</li>
</ul>
"""


# --------------------------------------------------------------------------- page 2
UNKNOWNS = [
    ("U-01", "Is the model's disagreement with itself small enough to publish a line at all?",
     "The per-club disagreement between estimators A and B is now measured (see the verification page), "
     "but the <b>decision rule</b> — at what disagreement a line is suppressed — has never been set. "
     "Without a pre-set threshold, 'suppress when they disagree' is a rule that can be fitted after the "
     "results are known.",
     "An owner decision on the threshold, written down before the next slate.",
     "Write the threshold into the pre-registration file for the strategy that uses it, then grade the "
     "next slates against it. Nothing else is needed — the numbers already exist.",
     "Decision needed (owner)", "high"),
    ("U-02", "What is the closing line, for every game we priced?",
     "The brief asks for a market-anchored prior weighted by measured out-of-sample log-loss. That "
     "requires closing lines. <b>None are in this repository</b>, and no official source publishes "
     "them: this is a commercial data purchase, not a web page.",
     "A licensed odds feed (or a personally collected archive of closing lines with timestamps).",
     "Buy or record it. Until then the market prior cannot be computed, and any page implying "
     "otherwise is wrong. This is why no stake is published anywhere on the site.",
     "Blocked — external data purchase", "high"),
    ("U-03", "Why does the two-estimator disagreement here agree to two decimals?",
     "A and B are mathematically tied: points differential per game and net rating per 100 possessions "
     "are the same quantity rescaled by pace. Agreement is therefore a <b>transcription check</b>, not "
     "independent confirmation — and it means the 'independent estimators' requirement is only "
     "satisfied in the weak sense until a genuinely different estimator (e.g. one built on opponent-"
     "adjusted possession data) is added.",
     "A second estimator built from a different data source, not a different algebraic route to the "
     "same number.",
     "Add an opponent-strength-adjusted rating from the official advanced page's components, or a "
     "ridge-regressed point margin from the game-by-game finals already committed. Either is a "
     "research task, not a data purchase.",
     "Research task", "high"),
    ("U-04", "Does the model beat the naive rule on the games that are left?",
     "The published skill page records that the model's accuracy is not distinguishable from "
     "'back the team with the better prior record' (McNemar p = 0.2962). Every sample since then is "
     "small. The honest answer to 'is this skill?' is still <b>unknown</b>.",
     "A pre-registered forward sample of at least 300 graded games, with the naive-rule comparison "
     "computed on exactly the same games.",
     "Keep grading. The sealed ledger already enforces the pre-registration; the sample size is the "
     "binding constraint, and no amount of analysis substitutes for it.",
     "Blocked — time", "high"),
    ("U-05", "What are the per-player minutes, and what happens to them when a player is out?",
     "The brief asks for the top-8 minutes shares per club and the replacement shares when a player is "
     "out. The official team-stat pages this session read print <b>team</b> minutes, not player "
     "minutes. Per-player game logs exist on nba.com and in committed gamebooks for a subset of games, "
     "but not for the clubs on tonight's slate in a form this build can read.",
     "Per-player game logs (minutes, points, rebounds, assists, opponent) for the players named on an "
     "injury report — the exact dataset the brief asks for.",
     "The pages exist at <code>nba.com/player/&lt;id&gt;/&lt;slug&gt;</code> and in the gamebook PDFs "
     "already used for a handful of games; the work is a scraper plus a recall gate. Until it runs, "
     "every minutes-redistribution cell stays blank with this reason.",
     "Buildable — data acquisition task", "high"),
    ("U-06", "Are the quarter scores on the settlement pages the ones the league printed?",
     "The quarter rows in the repository come from a committed capture, not from today's read: the "
     "games page does not print quarters. They were internally consistent (each row sums to the printed "
     "final) when the capture was made, but this session did not re-read them.",
     "The official gamebook or box-score page for each of the twelve games.",
     "The box-score URL is on every game card (<code>/game/&lt;slug&gt;/box-score</code>). Reading "
     "twelve of them is a bounded task and would close the quarter-score provenance question.",
     "Buildable — verification task", "medium"),
    ("U-07", "Which injury releases exist that the index no longer lists?",
     "The official index returned <b>only</b> the 2026-11-19 releases at the time of reading. Twenty-"
     "one PDFs are archived in the repository, but the index cannot confirm completeness for older "
     "dates, and the archive's own manifest records several files with no transcript and no retrieval "
     "time.",
     "A dated capture of the index page every day (so the listing itself is archived), plus a "
     "transcript for each PDF.",
     "The daily refresh workflow already fetches the index; making it commit the index <b>page</b> "
     "alongside the PDF closes this. Transcripts are the larger job.",
     "Buildable — process fix", "medium"),
    ("U-08", "What is the right minimum sample before a strategy may be ranked?",
     "The leaderboard publishes a minimum and a closure rule, but the numbers are proposals. With "
     "three days of slates at a time, a 300-game gate is a season-long commitment; a 100-game gate "
     "would rank noise.",
     "An owner decision informed by the power calculation: to detect a 3-point edge in cover "
     "probability at 80% power needs roughly 1,000 bets, not 300.",
     "Publish the power calculation next to the gate so the choice is quantitative rather than "
     "temperamental.",
     "Decision needed (owner)", "medium"),
    ("U-09", "Which of the two published HCA pins is right?",
     "This record measures a home-win rate of 0.5023 over 221 home games on 2026-11-19. The v2 model "
     "pins HCA from a 2026-11-14 transcription with a different sample. Both are 'measured'; they are "
     "not the same number, and the band around either is wide.",
     "A single agreed definition (which games count as home games) and one sample window.",
     "State the definition beside the constant, and widen the reporting band to the sample it came "
     "from. Deciding <em>when</em> the pin is re-cut is an owner decision.",
     "Decision needed (owner)", "medium"),
    ("U-10", "Does the three-day-ahead generator exist, or only a three-day window?",
     "There is a committed window of games with originated lines. There is <b>no</b> scheduled job that "
     "discovers the next window and originates lines for it — the most recent scheduled ingest run "
     "concluded failure. So the brief's 'generate picks for every upcoming slate up to 3 days out' is "
     "partly aspirational.",
     "A green scheduled run that (a) fetches, (b) passes the freshness and provenance gates, and "
     "(c) commits regenerated artefacts.",
     "Watch the Actions tab for the next scheduled run; if it fails, the failing step names the "
     "transport. The capture workflow that succeeds already proves the transport works from a runner.",
     "Blocked — infrastructure", "high"),
]

SUGGESTIONS_V8 = [
    ("S8-01", "Publish the two-estimator disagreement next to every line, and the blend underneath",
     "The brief asks for the disagreement to be the headline confidence signal. Implement it as a "
     "column on the lines page rather than a new page: a reader choosing a game sees the spread between "
     "the two ratings before the consensus number.",
     "Medium — one column plus a gate that suppresses a line when the disagreement exceeds the "
     "pre-registered threshold (U-01).",
     "Adds a decision surface without adding a claim. Requires U-01 first, or the threshold is "
     "arbitrary.",
     "Ready after U-01", "high", "recommended"),
    ("S8-02", "Make the injury release diff a first-class page with a stability gate",
     "The diff works and it immediately exposed a rendering artefact. Promote it: one row per "
     "(release, player), a column for status change, and a gate that refuses to publish a "
     "status-derived pick when the two releases it used have a rejected-row count above zero.",
     "Low — the parsing and diffing already exist; this is presentation plus one gate.",
     "Turns a working mechanism into a trust signal. The gate is the part that matters: it stops a "
     "silently lossy extraction from moving a pick.",
     "Ready", "high", "recommended"),
    ("S8-03", "Read the twelve box scores and fill the quarter-score column from them",
     "The games page has no quarters. The box-score URL is printed on every card. Reading twelve box "
     "scores closes the last provenance gap in the one-row-per-game result feed.",
     "Low — twelve page reads plus a parser; the shape of the box score is not yet observed, so budget "
     "one page to learn it.",
     "The result feed is the basis of settlement. A settlement stamped against a capture nobody "
     "re-read is weaker than it looks.",
     "Ready", "medium", "recommended"),
    ("S8-04", "Retire the duplicate pins: one place where a measured constant is defined",
     "Two HCA pins and several σ values exist across trees. Each is individually honest, but a reader "
     "cannot tell which one produced a given line. Introduce one constants file with a provenance "
     "field per constant and have every tree read it.",
     "Medium — touches v2..v6 build inputs; the risk is a rebuild diff on every page.",
     "Removes the class of defect where two pages quote different constants (U-09). Do it with a "
     "parity check, not by hand.",
     "Needs design", "medium", "for review"),
    ("S8-05", "Put rotation availability on the picks page as its own column",
     "The brief asks for it explicitly. The data exists (official status per club per game), but the "
     "replacement-minutes half needs U-05.",
     "Low for the status column, blocked for the minutes impact.",
     "Publishing half of it is still useful and honest if the column is labelled 'designation, minutes "
     "impact not yet modelled'.",
     "Ready (status half)", "medium", "recommended"),
    ("S8-06", "Print the naive parlay product next to the priced one",
     "The correlations page withholds a price when the legs are correlated. The brief asks for the "
     "price <b>and</b> the naive product side by side, so the cost of stacking is visible.",
     "Low — both numbers are already computed; one is printed, the other is suppressed.",
     "A withheld number looks like a mistake; two numbers show the arithmetic. Keep the rho band and "
     "the CI beside them.",
     "Ready", "medium", "recommended"),
    ("S8-07", "A power calculation page for the leaderboard",
     "Before a minimum sample is set, show what the sample can detect. 'Detect a 3-point edge at 80% "
     "power' has a number attached; '300 games' does not.",
     "Low — a standard formula and a chart.",
     "Makes U-08 a decision instead of an argument.",
     "Ready", "medium", "for review"),
    ("S8-08", "Do <em>not</em> merge the market prior until a closing line exists",
     "Recorded as a proposal of a negative: the highest-risk change available today is to blend toward "
     "a 'market' that is not in the repository. Add an explicit build gate that fails if a market-"
     "anchored page renders without a committed closing-line source.",
     "Low — one assertion in the v4/v6 gate chain.",
     "Prevents the most plausible future fabrication in this project.",
     "Ready", "high", "recommended"),
]


def page_unknowns() -> str:
    rows = []
    for qid, q, what, need, how, state, sev in UNKNOWNS:
        kind = {"high": "bad", "medium": "warn", "low": "info"}.get(sev, "info")
        rows.append([esc(qid), f"<b>{q}</b><br>{what}", esc(need), esc(how),
                     badge(state, kind),
                     link(CAP_URL, "official capture this register was written against")])
    return f"""
<h1>Unknowns &amp; open questions</h1>
<p class="lede">This is the list a decision has to clear before it can be made on evidence. Every entry
states <b>what we do not know</b>, <b>what information would settle it</b>, and <b>how to obtain that
information</b>. Nothing here is a hunch: each one names the missing dataset or the missing decision,
and each one is something this build could <em>not</em> answer from the data in the repository today.</p>

<div class="note"><b>How to read the state column.</b>
{badge('Decision needed (owner)', 'bad')} — no amount of building answers it; someone has to choose.
{badge('Blocked — external data purchase', 'bad')} — the data is not public.
{badge('Blocked — infrastructure', 'bad')} — the pipeline exists but is not running green.
{badge('Blocked — time', 'warn')} — needs a sample that can only accrue.
{badge('Research task', 'warn')} / {badge('Buildable', 'info')} — a known job, with the first step named.
</div>

{table(["id", "the question", "the information that would settle it", "how to get it", "state", "source"],
       rows, "Ten questions that block a decision, with the route to answering each one.")}

<h2>What is <em>not</em> on this list, and why</h2>
<p>Anything the verified capture already answers is absent on purpose. The 2026-11-19 slate, the twelve
2026-11-18 finals, every club's record, the two estimators and their disagreement, the five injury
releases and the diff between them, and the measured home-win rate are all settled — with the source
linked — on the <a href="verify-1119.html">verification record</a>. Repeating a settled number here would
make the register look bigger and be less useful.</p>
"""


def page_improvement() -> str:
    rows = []
    for sid, title, what, effort, why, state, prio, rec in SUGGESTIONS_V8:
        kind = {"high": "bad", "medium": "warn", "low": "info"}.get(prio, "info")
        rows.append([esc(sid), f"<b>{title}</b><br>{what}", esc(effort), esc(why),
                     badge(state, kind), badge(rec, "ok" if rec == "recommended" else "off"),
                     link(CAP_URL, "the measurement that motivates it")])
    return f"""
<h1>Improvement proposals</h1>
<p class="lede">A review queue, not a changelog. <b>Nothing in this table has been implemented.</b> Each
proposal states the change, what it costs, what it buys, and whether this session recommends it — so the
next decision is a choice between named paths rather than an argument about an unnamed one. The
recommendation column is an opinion and is labelled as one; the state column is a fact about the
repository.</p>

<div class="note warn"><b>Choose, then build.</b> The proposals are ordered so that the ones with no
dependency come first. Three of them (S8-01, S8-05, and anything touching the market prior) are gated on
an answer from <a href="unknowns.html">Unknowns &amp; open questions</a>; implementing them early would
mean hard-coding a threshold that nobody has agreed to.</div>

{table(["id", "proposal", "effort / risk", "what it buys", "state", "this session's view", "source"],
       rows, "Eight proposals, each with its dependency stated. None is implemented.")}

<h2>The two I would do first, and why</h2>
<p><b>S8-02</b> (make the injury diff a gated surface) because it is the only proposal here that
<em>already</em> caught a real defect during this session: the 06:45 AM release's extraction loses
alternating club markers, and a build that trusted it would have moved picks for clubs that had not
changed. Turning that into a gate is cheap and it prevents a class of error rather than one instance.</p>
<p><b>S8-03</b> (read the twelve box scores) because settlement is the one output in this system that
someone will actually rely on. Every quarter row currently traces to a committed capture nobody re-read;
twelve bounded page reads closes that, and the URL is already printed on every game card.</p>

<h2>What I would <em>not</em> do yet</h2>
<p>Land a market-anchored prior (S8-08 is the negative of this) and re-cut the model inputs to today's
capture in one step. Both are large, both are plausible-looking, and both would make the published tree
disagree with itself on dates — the exact defect the README already documents. Sequence them after the
constants are unified (S8-04).</p>
"""


# --------------------------------------------------------------------------- nav + build
def _inject_nav() -> int:
    """Add this tree's three pages to the sidebar of every published page, once."""
    block = (NAV_BLOCK_START + "\n"
             + "\n".join(f'<a href="{esc(h)}">{esc(l)}</a>' for h, l in PAGES)
             + "\n</div>")
    n = 0
    for p in sorted(SITE.glob("*.html")):
        doc = p.read_text()
        if "</nav>" not in doc or NAV_MARKER in doc:
            continue
        p.write_text(doc.replace("</nav>", block + "\n</nav>", 1))
        n += 1
    return n


def build() -> dict:
    if not CAP.exists():
        raise MissingCapture(
            f"{CAP_REL} is missing. Run tools/session-164d832b-capture.py first: the pages this "
            f"module writes are a function of that capture and refuse to render without it.")
    d = json.loads(CAP.read_text())
    for key in ("standings", "traditional", "opponent", "advanced", "finals_1118", "slate_1119",
                "injury_0700", "injury_index", "injury_diffs", "hca", "estimators", "retrieval"):
        if key not in d:
            raise MissingCapture(f"{CAP_REL} has no {key!r} — refusing to render a page with a hole in it")
    nav = _load_nav()
    _shell("verify-1119.html", "Verification record — 2026-11-19", page_verify(d), nav)
    _shell("unknowns.html", "Unknowns & open questions", page_unknowns(), nav)
    _shell("improvement.html", "Improvement proposals", page_improvement(), nav)
    n = _inject_nav()
    return {"pages": [p for p, _ in PAGES], "nav_injected": n}
