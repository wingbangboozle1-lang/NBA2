"""The v4 pages: player game logs, rotation impact, and the injury release diff.

The same body HTML is published twice on purpose:

* into ``site/`` — the canonical v2/v3/v4 tree, with the v2/v3 navigation copied
  from an already-published page so this generator cannot drift from it;
* into ``pages/`` — the tree GitHub Pages is actually serving today (the Pages
  source is ``main /``, not the Actions artefact; see F-033 / FLAG-PAGES-01).

Every row of every table carries an outbound official link, and every cell that
is blank carries the reason it is blank. Both properties are enforced by
``nba2/v2/check.py`` and by this module's own tests.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from . import official as O
from . import gamelog as GL
from . import injury as IN
from . import minutes as MN

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"

V4_PAGES = [
    ("player-logs.html", "Player game logs"),
    ("rotation-impact.html", "Rotation impact"),
    ("injury-diff.html", "Injury release diff"),
]
V4_NAMES = [n for n, _ in V4_PAGES]
MARKER = '<a href="player-logs.html"'


_ENTITY_RE = re.compile(r"&(?:[a-zA-Z][a-zA-Z0-9]*|#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6});")


def esc(x) -> str:
    text = "" if x is None else str(x)
    # idempotent: an already-escaped fragment (&amp; / &#x27;) is unescaped first, so a cell
    # that is escaped twice by accident still prints one character, never "&amp;#x27;".
    if "&" in text and _ENTITY_RE.search(text):
        text = html.unescape(text)
    return html.escape(text, quote=True)


def blank(reason: str) -> str:
    return f'<span class="blank">— {esc(reason)}</span>'


def cell(v, reason: str = "no data captured") -> str:
    return blank(reason) if v is None else f"<td>{esc(v)}</td>"


def table(head: list[str], rows: list[str], blurb: str = "", title: str = "",
          anchor: str = "") -> str:
    th = "".join(f"<th>{esc(h)}</th>" for h in head)
    ident = f' id="{esc(anchor)}"' if anchor else ""
    out = [f'<section class="card"{ident}>']
    if title:
        out.append(f"<h2>{esc(title)}</h2>")
    if blurb:
        out.append(f'<p class="blurb">{esc(blurb)}</p>')
    out.append(f'<div class="scroll"><table class="data"><thead><tr>{th}</tr></thead>'
               f'<tbody>{"".join(rows)}</tbody></table></div>')
    out.append("</section>")
    return "".join(out)


def src(url: str, label: str = "SRC") -> str:
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'


# --------------------------------------------------------------------------- bodies
def body_player_logs() -> str:
    d = O.gamelogs()
    gl = GL.gates()
    rows = GL.rows()
    base = GL.baselines()
    n_pass = sum(1 for g in gl if g["status"] == "PASS")
    out = [
        '<h1>Player game logs (official, captured per player)</h1>',
        '<p class="lede">The brief asks for per-player game logs — minutes, points, '
        'rebounds, assists and the opponent — for at least the players who appear on an '
        'injury report. Until this session the repository had one game (gid 0022600231) '
        f'and no per-player season baselines at all. This page publishes {len(base)} players '
        f'and {len(rows)} official player-games, every row read from the player\'s own '
        'nba.com game-log page on 2026-11-15.</p>',
        '<p class="lede"><strong>Capture rule.</strong> ' + esc(d["capture_rule"]) + '</p>',
    ]
    summary = [
        "<tr><td>Players with a captured log</td><td>" + str(len(base)) + "</td><td>"
        + src(O.SOURCES["gamelog"][1], "nba.com/stats/player") + "</td></tr>",
        "<tr><td>Official player-games captured</td><td>" + str(len(rows)) + "</td><td>"
        + src(O.SOURCES["gamelog"][1], "nba.com/stats/player") + "</td></tr>",
        "<tr><td>Gates measured</td><td>" + f"{n_pass} pass / {len(gl) - n_pass} fail"
        + "</td><td>" + src(O.SOURCES["gamelog"][1], "nba.com/stats/player") + "</td></tr>",
        "<tr><td>Players on the release with no log</td><td>"
        + str(len(d["not_captured"]) + len(d["capture_failures"])) + "</td><td>"
        + src(O.SOURCES["injury_pdf"][1], "injury PDF 06:15 PM ET") + "</td></tr>",
        "<tr><td>Clubs captured</td><td>" + ", ".join(sorted({b["team"] for b in base}))
        + "</td><td>" + src(O.SOURCES["roster"][1], "nba.com/team") + "</td></tr>",
    ]
    out.append(table(["Measure", "Value", "Source"], summary,
                     title="What this capture contains", anchor="v4-summary"))

    gaterows = [
        f'<tr><td>{esc(g["id"])}</td><td>{esc(g["player"])}</td><td>{esc(g["name"])}</td>'
        f'<td>{esc(g["measurement"])}</td>'
        f'<td><span class="badge b-{"ok" if g["status"] == "PASS" else "bad"}">'
        f'{esc(g["status"])}</span></td><td>{src(g["source"], "official")}</td></tr>'
        for g in gl
    ]
    out.append(table(["Gate", "Player", "Check", "Measurement", "Status", "Source"], gaterows,
                     blurb="G-41-02 is the one that can fail: the mean of the captured rows "
                           "must equal the PPG / RPG / APG the same page prints in the player "
                           "header. A missed row or a mistyped digit moves the first decimal.",
                     title="Capture gates — measured, not asserted", anchor="v4-gates"))

    brows = []
    for b in sorted(base, key=lambda x: (-x["mpg"])):
        h = b["official_header"]
        brows.append(
            f'<tr><td>{src(b["source_url"], b["player"])}</td><td>{esc(b["team"])}</td>'
            f'<td>{esc(b["injury_status"])}</td><td>{esc(b["games"])}</td>'
            f'<td>{esc(b["mpg"])}</td><td>{esc(b["ppg"])}</td><td>{esc(b["rpg"])}</td>'
            f'<td>{esc(b["apg"])}</td><td>{esc(b["l5_mpg"])}</td><td>{esc(b["l5_ppg"])}</td>'
            f'<td>{esc(h["ppg"])} / {esc(h["rpg"])} / {esc(h["apg"])}</td>'
            f'<td>{esc(b["last_game"])}</td></tr>')
    out.append(table(
        ["Player", "Club", "Release status", "G", "MPG", "PPG", "RPG", "APG",
         "L5 MPG", "L5 PPG", "Official header PPG/RPG/APG", "Last game"],
        brows,
        blurb="MPG/PPG/RPG/APG are means over the captured official games; the last two "
              "columns are the identifiers that let a reviewer re-derive them by hand.",
        title="Per-player baselines from the captured logs", anchor="v4-baselines"))

    grows = []
    for r in rows:
        grows.append(
            f'<tr><td>{esc(r["date"])}</td><td>{esc(r["player"])}</td><td>{esc(r["team"])}</td>'
            f'<td>{esc(r["matchup"])}</td><td>{esc(r["opponent"])}</td>'
            f'<td>{esc(r["home_away"])}</td><td>{esc(r["result"])}</td>'
            f'<td>{esc(r["minutes"])}</td><td>{esc(r["points"])}</td>'
            f'<td>{esc(r["rebounds"])}</td><td>{esc(r["assists"])}</td>'
            f'<td>{esc(r["plus_minus"])}</td>'
            f'<td>{src(r["game_url"], r["game_id"])}</td>'
            f'<td>{src(r["source_url"], "log")}</td></tr>')
    out.append(table(
        ["Date", "Player", "Club", "Match up", "Opponent", "H/A", "W/L", "MIN",
         "PTS", "REB", "AST", "+/-", "Official game", "Source"],
        grows,
        blurb="One row per official player-game, newest first. The game id links to the "
              "official game page; the last column links to the player's own game-log page.",
        title="Every captured game row", anchor="v4-rows"))

    frows = []
    for f in d["capture_failures"]:
        frows.append(
            f'<tr><td>{esc(f["player"])}</td><td>{esc(f["team"])}</td>'
            f'<td>{esc(f["injury_status"])}</td><td>{esc(f["injury_reason"])}</td>'
            f'<td>the official page prints "No data available" where the game-log table '
            f'should be ({esc(f["attempts"])} attempt(s)); the header rates are not a game '
            f'log and are not published as one</td>'
            f'<td>{src(f["source_url"], "official page")}</td></tr>')
    for n in d["not_captured"]:
        frows.append(
            f'<tr><td>{esc(n["player"])}</td><td>{esc(n["team"])}</td>'
            f'<td>{esc(n["injury_status"])}</td><td>{esc(n["injury_reason"])}</td>'
            f'<td>{esc(n["why"])} — no data captured, left blank by policy</td>'
            f'<td>{src(O.SOURCES["injury_pdf"][1], "injury PDF 06:15 PM ET")}</td></tr>')
    out.append(table(["Player", "Club", "Status", "Reason", "Why nothing is published", "Source"],
                     frows,
                     blurb="Every player on the 2026-11-16 release with Out/Questionable/Doubtful "
                           "status and no captured log. None of them is estimated.",
                     title="On the release, but not captured", anchor="v4-missing"))

    unreach = "".join(
        f'<tr><td>{esc(name)}</td><td>{src(url, url)}</td><td>{esc(why)}</td></tr>'
        for name, url, why in O.UNREACHABLE)
    out.append(table(["Endpoint", "URL", "What happened"], [unreach],
                     blurb="Measured this session so the next session does not spend its "
                           "budget rediscovering it. Coverage of player data scales with "
                           "pages read, and these are the pages that do not exist.",
                     title="Endpoints that do not work", anchor="v4-unreachable"))
    return "".join(out)


def body_rotation_impact() -> str:
    out = [
        '<h1>Rotation impact — minutes and production at risk</h1>',
        '<p class="lede">What an injury report is actually worth to a line: the minutes and '
        'the production that leave the floor. Everything below is the official mean over '
        "the player's captured official games. Nothing is modelled, and where a log is not "
        'captured the column is blank and flagged rather than prorated.</p>',
    ]
    blocks = MN.blocks()
    srows = []
    for b in blocks:
        share = f'{b["share_of_team_minutes"]:.1%}' if b["share_of_team_minutes"] is not None else "—"
        srows.append(
            f'<tr><td>{esc(b["team"])}</td><td>{esc(b["date"])}</td>'
            f'<td>{esc(b["designated"])}</td><td>{esc(b["captured"])}</td>'
            f'<td>{esc(b["vacated_mpg"])}</td><td>{esc(share)}</td>'
            f'<td>{esc(b["vacated_ppg"])}</td><td>{esc(b["vacated_rpg"])}</td>'
            f'<td>{esc(b["vacated_apg"])}</td>'
            f'<td>{"lower bound — " + str(len(b["missing"])) + " designated player(s) have no captured log" if b["lower_bound"] else "complete"}</td>'
            f'<td>{src(b["source_url"], "injury PDF 06:15 PM ET")}</td></tr>')
    out.append(table(
        ["Club", "Game date", "Designated out", "Captured", "Vacated MPG",
         "Share of 240 team-minutes", "Vacated PPG", "Vacated RPG", "Vacated APG",
         "Coverage", "Source"],
        srows,
        blurb="A lower bound, not an estimate: only the designated players whose log was "
              "captured contribute. It is never scaled up to the players who were not captured.",
        title="Minutes and production designated out", anchor="v4-atrisk"))

    for b in blocks:
        rows = []
        for r in b["rows"]:
            mpg = f"<td>{esc(r['mpg'])}</td>" if r["mpg"] is not None else \
                "<td>" + blank("no data captured (F-41B-05)") + "</td>"
            rest = ("".join(f"<td>{esc(r[k])}</td>" for k in ("ppg", "rpg", "apg"))
                    if r["mpg"] is not None else
                    "".join("<td>" + blank("no data captured (F-41B-05)") + "</td>" for _ in range(3)))
            rows.append(f'<tr><td>{esc(r["player"])}</td><td>{esc(r["status"])}</td>'
                        f'<td>{esc(r["reason"])}</td>{mpg}{rest}'
                        f'<td>{esc(r["note"])}</td>'
                        f'<td>{src(r["source_url"], "official")}</td></tr>')
        out.append(table(["Player", "Status", "Reason", "MPG", "PPG", "RPG", "APG",
                          "Note", "Source"], rows,
                         title=f'{b["team"]} — designated players on {b["date"]}',
                         anchor=f'v4-{b["team"].lower()}'))

        cand = MN.absorption_candidates(b["team"])
        crows = [f'<tr><td>{src(c["source_url"], c["player"])}</td><td>{esc(c["pos"])}</td>'
                 f'<td>{blank("minutes log not captured — no data (F-41B-05)")}</td>'
                 f'<td>{blank("no data — redistribution needs Σ available mpg")}</td>'
                 f'<td>{esc(c["note"])}</td></tr>' for c in cand]
        out.append(table(["Player", "Pos", "MPG (captured)", "Minutes after redistribution", "Note"],
                         crows,
                         blurb="The club's official roster minus the designated players. Their "
                               "minutes are exactly what the redistribution rule needs as a "
                               "denominator, and they are not captured yet — so the column is "
                               "blank, not guessed.",
                         title=f'{b["team"]} — who would have to absorb it',
                         anchor=f'v4-{b["team"].lower()}-absorb'))

    out.append('<section class="card" id="v4-rule"><h2>The redistribution rule</h2>'
               f'<p class="blurb">{esc(MN.RULE_TEXT)}</p>'
               '<p class="blurb">This session captured the players who are <em>out</em>. The '
               'receiving side needs the players who are <em>in</em>, so the rule is published '
               'with its denominator empty rather than filled with a proxy. '
               '<code>nba2/v4/minutes.py::redistribution()</code> runs it the moment those logs '
               'land.</p></section>')
    return "".join(out)


def body_injury_diff() -> str:
    d = IN.diff()
    pm, am = O.injury(True), O.injury(False)
    counts = IN.status_counts(True)
    ns = IN.not_submitted(True)
    out = [
        '<h1>Injury release — stored, timestamped and diffed</h1>',
        f'<p class="lede"><strong>Current release</strong> {esc(pm["report_stamp_et"])} '
        f'(revision time as printed on the PDF), retrieved {esc(pm["retrieved_at_utc"])} '
        f'via {esc(pm["retrieval_method"])}. '
        f'<strong>Prior release compared:</strong> {esc(am["report_stamp_et"])}, retrieved '
        f'{esc(am["retrieved_at_utc"])}. Both PDFs are addressed by their own timestamped URL, '
        'and the diff below is computed from those two files, not from memory.</p>',
    ]
    srows = [
        f'<tr><td>Newest release indexed</td><td>{esc(pm["report_stamp_et"])}</td>'
        f'<td>{src(O.SOURCES["injury_index"][1], "official index")}</td></tr>',
        f'<tr><td>Rows with a named player (prior → current)</td>'
        f'<td>{esc(d["prior_rows"])} → {esc(d["current_rows"])}</td>'
        f'<td>{src(O.SOURCES["injury_pdf"][1], "injury PDF 06:15 PM ET")}</td></tr>',
        f'<tr><td>Status changes between the two releases</td><td>{esc(len(d["changes"]))}</td>'
        f'<td>{src(O.SOURCES["injury_pdf"][1], "injury PDF 06:15 PM ET")}</td></tr>',
        f'<tr><td>Rows only in the current release</td><td>{esc(len(d["added"]))}</td>'
        f'<td>{src(O.SOURCES["injury_pdf"][1], "injury PDF 06:15 PM ET")}</td></tr>',
        f'<tr><td>Rows only in the prior release</td><td>{esc(len(d["removed"]))}</td>'
        f'<td>{src(O.SOURCES["injury_prior"][1], "injury PDF 06:15 AM ET")}</td></tr>',
        f'<tr><td>Club-slots not yet filed on the current release</td><td>{esc(len(ns))}</td>'
        f'<td>{src(O.SOURCES["injury_pdf"][1], "injury PDF 06:15 PM ET")}</td></tr>',
    ]
    out.append(table(["Measure", "Value", "Source"], srows,
                     title="Freshness and coverage", anchor="v4-inj-summary"))

    crows = "".join(
        f'<tr><td>{esc(k)}</td><td>{esc(v)}</td>'
        f'<td>{src(O.SOURCES["injury_pdf"][1], "injury PDF 06:15 PM ET")}</td></tr>'
        for k, v in counts.items())
    out.append(table(["Status", "Rows", "Source"], [crows],
                     title="Status distribution on the current release",
                     anchor="v4-inj-status"))

    if d["changes"]:
        chrows = "".join(
            f'<tr><td>{esc(c["team"])}</td><td>{esc(c["player"])}</td>'
            f'<td>{esc(c["from_status"])}</td><td>{esc(c["to_status"])}</td>'
            f'<td>{esc(c["direction"])}</td><td>{esc(c["matchup"])}</td>'
            f'<td>{esc(c["current_reason"])}</td>'
            f'<td>{src(c["source_url"], "injury PDF 06:15 PM ET")}</td></tr>'
            for c in d["changes"])
    else:
        chrows = (f'<tr><td>{blank("no status change between these two releases")}</td>'
                  f'<td>{blank("no data changed")}</td><td>{blank("no data changed")}</td>'
                  f'<td>{blank("no data changed")}</td><td>{blank("no data changed")}</td>'
                  f'<td>{blank("no data changed")}</td><td>{blank("no data changed")}</td>'
                  f'<td>{src(O.SOURCES["injury_pdf"][1], "injury PDF 06:15 PM ET")}</td></tr>')
    out.append(table(["Club", "Player", "Prior status", "Current status", "Direction",
                      "Game", "Reason on the current release", "Source"], [chrows],
                     blurb="Computed by nba2/v4/injury.py::diff() over the two stored files, "
                           "keyed on (club, player) as the PDF prints them.",
                     title="Status changes, prior release → current release",
                     anchor="v4-inj-changes"))

    nsrows = "".join(
        f'<tr><td>{esc(r["game_date"])}</td><td>{esc(r["matchup"])}</td><td>{esc(r["team"])}</td>'
        f'<td>{blank("not filed — no data submitted for this club slot")}</td>'
        f'<td>{src(O.SOURCES["injury_pdf"][1], "injury PDF 06:15 PM ET")}</td></tr>'
        for r in ns)
    out.append(table(["Game date", "Matchup", "Club", "Status", "Source"], [nsrows],
                     blurb="A club that has not filed is priced availability-blind: the report "
                           "says nothing, so the model is told nothing.",
                     title="Club-slots with nothing filed", anchor="v4-inj-notfiled"))

    srows2 = "".join(
        f'<tr><td>{esc(r["game_date"])}</td><td>{esc(r["matchup"])}</td><td>{esc(r["team"])}</td>'
        f'<td>{(esc(r["player"]) if r["player"] else blank("not filed — no data submitted for this club slot"))}</td>'
        f'<td>{(esc(r["status"]) if r["status"] else blank("not filed — no data submitted"))}</td>'
        f'<td>{esc(r["reason"])}</td>'
        f'<td>{"club cell blank on the PDF — attributed by table-block position" if r["attributed_team"] else "printed"}</td>'
        f'<td>{src(O.SOURCES["injury_pdf"][1], "injury PDF 06:15 PM ET")}</td></tr>'
        for r in IN.slate_rows("2026-11-16"))
    out.append(table(["Game date", "Matchup", "Club", "Player", "Status", "Reason",
                      "Team cell", "Source"], [srows2],
                     blurb="Every row of the 2026-11-16 slate block, transcribed verbatim.",
                     title="The 2026-11-16 slate in the current release",
                     anchor="v4-inj-slate"))

    frows = "".join(
        f'<tr><td>{esc(f["id"])}</td><td>{esc(f["area"])}</td><td>{esc(f["finding"])}</td>'
        f'<td>{src(f["source"], "official source")}</td></tr>'
        for f in O.injury(True)["flags"] + O.gamelogs()["flags"])
    out.append(table(["Flag", "Area", "Finding", "Source"], [frows],
                     title="Flags raised by this capture", anchor="v4-inj-flags"))
    return "".join(out)


BODIES = {
    "player-logs.html": body_player_logs,
    "rotation-impact.html": body_rotation_impact,
    "injury-diff.html": body_injury_diff,
}


# --------------------------------------------------------------------------- chrome
def _published_navs() -> list[str]:
    """Every ``<nav>`` inner HTML in the published tree, richest first."""
    found = []
    for p in sorted(SITE.glob("*.html")):
        m = re.search(r"<nav[^>]*>(.*?)</nav>", p.read_text(), re.S)
        if m:
            found.append(m.group(1))
    return sorted(found, key=lambda n: -len(re.findall(r"<a ", n)))


def nav_block(active: str) -> str:
    """Copy the navigation from the published tree and mark this one active.

    Copying rather than restating is deliberate: the v2 and v3 generators own the
    nav, and a copy cannot drift from it silently. The copy is taken from the
    *richest* nav in the tree, not from index.html specifically, because a v2-only
    rebuild rewrites index.html without the v3 links — taking the richest one means
    a stale index shrinks nothing, and the repair in :func:`inject_nav` can then
    hand the full nav back to the pages that lost it.
    """
    navs = _published_navs()
    inner = navs[0] if navs else ""
    if not navs:
        print("WARNING: no <nav> found in site/*.html — run `python -m nba2.v2` first",
              file=sys.stderr)
    inner = re.sub(r'\s*class="on"', "", inner)

    def mark(mm: re.Match) -> str:
        href = mm.group(1)
        cls = ' class="on"' if href == active else ""
        # no closing ">" here: the pattern stops at the closing quote, so the tag's own
        # ">" is still in the text. Adding one grew the label by a ">" on every build
        # (">Dashboard" -> ">>Dashboard" -> ...), which is how it was caught.
        return f'<a href="{href}"{cls}'

    inner = re.sub(r'<a href="([^"]+)"', mark, inner)
    return f"<nav>{inner}</nav>"


def page(title: str, active: str, body: str) -> str:
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
  <p class="tag">v4 · player-level capture {esc(O.injury(True)["report_stamp_et"])}</p>
  {nav_block(active)}
</aside>
<main>
{body}
</main>
</div>
</body>
</html>
"""


def inject_nav() -> int:
    """Add the v4 links to every published page that has a nav, idempotently.

    Idempotency is "already present", not "skip": a page whose nav is missing any v4
    link, or whose nav is poorer than the richest nav in the tree (the v2-only-rebuild
    case), still gets the block — and gets it rebuilt from the richest nav so a page
    that lost the v3 links regains them.
    """
    block = "\n".join(f'<a href="{n}">{esc(l)}</a>' for n, l in V4_PAGES)
    navs = _published_navs()
    best = navs[0] if navs else ""
    best_links = set(re.findall(r'href="([^"]+)"', best))
    n = 0
    for p in sorted(SITE.glob("*.html")):
        if p.name in V4_NAMES:
            continue
        doc = p.read_text()
        m = re.search(r"<nav[^>]*>(.*?)</nav>", doc, re.S)
        if m is None:
            continue
        inner = m.group(1)
        have = set(re.findall(r'href="([^"]+)"', inner))
        if all(name in have for name in V4_NAMES) and not (best_links - have):
            continue
        inner = re.sub(
            r'\s*<a href="(?:%s)"[^>]*>[^<]*</a>' % "|".join(re.escape(x) for x in V4_NAMES),
            "", inner)
        if best_links - have:
            # restore the richer nav (v3 links and any v2 links this page lost)
            inner = best
        p.write_text(doc[:m.start(1)] + inner.rstrip() + "\n" + block + doc[m.end(1):])
        n += 1
    return n


def build() -> list[str]:
    SITE.mkdir(exist_ok=True)
    written = []
    for name, title in V4_PAGES:
        doc = BODIES[name]()
        doc = re.sub(r"href='([^']*)'", r'href="\1"', doc)
        (SITE / name).write_text(page(title, name, doc))
        written.append(name)
    inject_nav()
    return written


# --------------------------------------------------------------------------- v1 tree
def v1_sections() -> dict[str, str]:
    """{rel path in pages/: body html} for the v1 tree (what GitHub Pages serves today)."""
    return {f"pages/{name}": BODIES[name]() for name, _ in V4_PAGES}
