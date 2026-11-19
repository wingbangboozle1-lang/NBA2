"""Publish the v7 session's findings on the Flagged for Review page.

Same contract as :mod:`nba2.v6.flags`: ``site/flagged.html`` is built by v2, and this module
**appends** one clearly-marked section after it, idempotently. Nothing of v2's or v6's content
is removed or reordered.

Each flag carries the official document it is about, what is wrong, what is published
instead, and the file a reviewer would open to check it. The rule the whole project follows
applies here too: a flag never blocks a merge, and a value that cannot be confirmed is left
blank with its reason rather than filled in.
"""

from __future__ import annotations

import json
from pathlib import Path

from nba2.v6.common import SITE, badge, esc, link, note, table

MARKER = '<section id="v7-flags">'
DATA = Path("data/v7")

ADV = ("https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season")
TRAD = ("https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season")
OPP = ("https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season")
STAND = "https://www.nba.com/standings"
GAMES_1119 = "https://www.nba.com/games?date=2026-11-19"
INJURY_INDEX = "https://official.nba.com/nba-injury-report-2026-27-season/"

# (id, severity, official document, what is wrong, what is published instead, where to check)
FLAGS = [
    ("F-V7-AVAIL", "gap", INJURY_INDEX,
     "The 2026-11-19 official injury report was <b>not read</b> in this session, so the "
     "availability column on the slate has nothing to put in it. An availability number "
     "invented from a stale report would be worse than no number, because the whole point of "
     "the column is that it is current.",
     "Every slate row prints the column as a blank with <code>F-V7-AVAIL</code> as the reason, "
     "and gate <b>G-V7-8</b> fails while it is blank. Rotation-availability strategies are "
     "therefore blocked rather than quietly dropped.",
     "nba2/v7/official.py (INJURY_REPORT_READ=False)"),

    ("F-V7-CLOCK", "info", STAND,
     "The league's own pages disagree by one date: the three team-stat pages run through "
     "<b>2026-11-17</b>, while <code>/standings</code> includes <b>2026-11-18</b>. Measured on "
     "Utah, whose stat-page games played (15) is one short of its standings record (3-13 = 16), "
     "the extra game being the 11/18 win over the Lakers.",
     "Both clocks are published side by side with the size of the gap, instead of being "
     "blended into a single as-of date that is true of neither page.",
     "site/v7-skill.html · site/v7-methodology.html"),

    ("F-V7-TRANSPORT", "info", ADV,
     "The transcription cannot be reproduced from this sandbox — <code>nba.com</code> resets "
     "the TLS handshake (curl exit 000), so no number could be re-read by script — and it "
     "cannot be reproduced from a GitHub runner either, where <code>stats.nba.com</code> times "
     "out and <code>cdn.nba.com</code> returns 403.",
     "The numbers were read page by page and committed to <code>nba2/v7/official.py</code>, and "
     "three arithmetic identities are tested over all 30 clubs so a transcription slip fails "
     "the build instead of reaching a reader: NetRtg = OffRtg − DefRtg (30/30), "
     "PTS − OppPTS = +/− (30/30), and every club's W equals its wins in the committed finals "
     "(30/30 over 222 games).",
     "nba2/v7/test_v7.py · data/raw/egress_probe.json"),

    ("F-V7-MARKET", "gap", GAMES_1119,
     "No market price exists anywhere in this repository — no closing line, no opening line, "
     "no spread or total quote — so <b>no edge is computable</b> and the blend weight against "
     "the closing line is undefined.",
     "Every stake on the slate is <b>0.00</b>. Gate G-V7-6 blocks every price-dependent "
     "strategy. The strategies are written and published in the blocked state rather than "
     "deleted, so the gate's arithmetic is visible.",
     "site/v7-strategies.html · site/v7-slate.html"),

    ("F-V7-PROPS", "gap", "https://www.nba.com/stats/players/traditional",
     "Player props cannot be priced: the largest committed per-player log set holds <b>3 "
     "games</b> for the best-covered player (421 players, max 3 games each), while a ±5-point "
     "line needs about 15 games before a residual standard deviation means anything.",
     "The props section prints the arithmetic — the sample it has against the sample it needs "
     "— instead of a probability. Player-prop combos are blocked on that basis.",
     "data/v5/player_logs_union.json · site/v7-strategies.html"),

    ("F-V7-PREREG", "info", "https://github.com/wingbangboozle1-lang/NBA2",
     "Pre-registration hashes are committed in the same commit as the strategy definitions "
     "they freeze. That makes them tamper-evident against <i>later</i> edits, but not against "
     "a rewrite of the commit that introduced both — a hash stored beside its own input "
     "proves only ordering, not authorship.",
     "Ten pre-registration files are written and the build refuses to overwrite an existing "
     "one, so any change to a strategy's signal, thresholds, universe or settlement rule after "
     "freezing fails the build. The stronger fix is a suggestion, not a silent claim.",
     "data/v7/prereg/ · SG-V7-04"),

    ("F-V7-PAGES", "info", "https://wingbangboozle1-lang.github.io/NBA2/",
     "GitHub Pages is configured with <code>build_type: legacy</code>, source branch "
     "<code>main</code>, path <code>/</code>. Under legacy mode the uploaded <code>site/</code> "
     "artefact is not what gets served from the root, and a push alone does not trigger a "
     "redeploy — the deploy must be dispatched explicitly.",
     "The Pages API still reports <code>build_type=legacy</code> with source <code>main /</code>. "
     "This session has not independently verified that the v7 pages under <code>site/</code> "
     "are served from the live root, so deployment is not claimed complete from a successful "
     "workflow alone. Verify the Pages routing and live page after integration.",
     "COORDINATION.md · SG-V7-12"),

    ("F-V7-LEAK", "info", ADV,
     "The first draft of the v7 model cut its team ratings from the 2026-11-19 pages and then "
     "used those same ratings to 'test' October games — a leak of future information into "
     "every historical prediction.",
     "<b>Fixed before publication.</b> The measured symptom was a 34.1% walk-forward accuracy, "
     "which is the signature of a sign or leak bug rather than a bad model; the fix restricts "
     "every historical cut to <code>ratings_as_of(cutoff)</code>, and a test now fails if a "
     "future rating is used. Corrected walk-forward: 67.1% accuracy, log-loss 0.6349.",
     "nba2/v7/model.py · nba2/v7/test_v7.py"),

    ("F-V7-STALE-UPSTREAM", "info", STAND,
     "The v3/v4/v5 trees are measurably stale on the inputs that matter: v3 prices Atlanta at "
     "<b>8-6</b> while the live standings page prints <b>9-6</b>, and no tree in the repository "
     "contained the twelve 2026-11-18 finals. They were not edited in place — that is another "
     "session's scope — a new layer was cut instead.",
     "The v7 slate is cut entirely from the 2026-11-19 snapshot and reconciles 30/30 against "
     "the committed finals. The older surfaces keep their published numbers and their own "
     "as-of dates, and the discrepancy is stated here rather than quietly patched.",
     "site/v7-verify.html · COORDINATION.md"),
]

SEVERITY_BADGE = {"gap": "bad", "info": "info", "blocker": "warn"}


def _src(url: str) -> str:
    host = url.split("/")[2].replace("www.", "")
    return link(url, host, url)


def _where(where: str) -> str:
    """A flag's 'where to check' is sometimes a URL and sometimes a path in this repo."""
    if where.startswith("http"):
        return _src(where)
    return f"<code>{esc(where)}</code>"


def build_section() -> str:
    rows = []
    for fid, sev, url, wrong, instead, where in sorted(FLAGS):
        rows.append([
            f'<b id="{esc(fid)}">{esc(fid)}</b>',
            badge(sev, SEVERITY_BADGE.get(sev, "info")),
            _src(url),
            wrong,
            instead,
            _where(where),
        ])
    body = note(
        "Added 2026-11-19 by session <code>arena/6023d517-nba2</code>. Appended below v2's own "
        "register and v6's findings; nothing above was removed or reordered. None of these "
        "blocks the merge — that is what a flag is for — and each names the official document "
        "a reviewer would open to check it.", "warn")
    body += table(
        ["ID", "Severity", "Official source", "What is wrong",
         "What is published instead", "Where to check"],
        rows,
        caption=f"{len(FLAGS)} findings from the 2026-11-19 line-by-line pass.")
    return (f'\n<section id="v7-flags">\n<h2>Flagged by the 2026-11-19 snapshot pass '
            f'(v7)</h2>\n{body}\n</section>\n')


def append_to_flagged() -> bool:
    p = SITE / "flagged.html"
    if not p.exists():
        return False
    doc = p.read_text()
    if MARKER in doc:
        return False
    section = build_section()
    if "</main>" in doc:
        doc = doc.replace("</main>", section + "</main>", 1)
    else:
        doc = doc.replace("</body>", section + "</body>", 1)
    p.write_text(doc)
    return True


def write_data() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "flags.json").write_text(json.dumps({
        "schema": "nba2.v7.flags.v1",
        "session": "arena/6023d517-nba2",
        "n_flags": len(FLAGS),
        "published_on": "site/flagged.html (appended after v2's register and v6's findings)",
        "flags": [{"id": f[0], "severity": f[1], "official_source": f[2],
                   "what_is_wrong": f[3], "what_is_published": f[4], "where_to_check": f[5]}
                  for f in FLAGS],
    }, indent=1, ensure_ascii=False) + "\n")


def run() -> dict:
    added = append_to_flagged()
    write_data()
    return {"section_added": added, "n_flags": len(FLAGS),
            "section_present": MARKER in (SITE / "flagged.html").read_text()}
