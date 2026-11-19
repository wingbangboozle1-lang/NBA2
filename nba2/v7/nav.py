"""v7 nav: add the layer's five pages to the shared sidebar without removing a link.

The site's sidebar is written by v2, then v3/v4/v5/v6 append to it, and v6 groups it into
categories and inserts a card grid on the landing page. v7 runs *after* v6 (v6 groups the
whole tree, so a page written after it would never be grouped), which means v7 has to do
three things and check all three:

  1. insert its five links into the sidebar, inside the projection/bet groups they belong to;
  2. add its category cards to the landing page's card grid;
  3. verify the set of hrefs afterwards is a superset of the set before — a link that
     disappears from the sidebar is a page a reader can no longer reach, and that is a build
     failure, not a cosmetic change.
"""

from __future__ import annotations

import re
from pathlib import Path

from .common import SITE

MARKER = '<!-- v7-link-block -->'

SLATE_GROUP = ["v7-slate.html"]
BET_GROUP = ["v7-strategies.html"]
SKILL_GROUP = ["v7-skill.html"]
DOCS_GROUP = ["v7-methodology.html", "v7-verify.html"]

LABELS = {
    "v7-slate.html": "Originated slate (v7)",
    "v7-strategies.html": "Strategy lab &amp; parlays (v7)",
    "v7-skill.html": "Measured skill &amp; luck (v7)",
    "v7-methodology.html": "v7 methodology",
    "v7-verify.html": "v7 verification",
}


def _link(href: str, active: str | None = None) -> str:
    cls = ' class="on"' if href == active else ""
    return f'<a href="{href}"{cls}>{LABELS[href]}</a>'


def _links(active: str | None = None) -> str:
    return "".join(_link(h, active) for h in LABELS)


def _hrefs(doc: str) -> set[str]:
    m = re.search(r"<nav>(.*?)</nav>", doc, re.S)
    if not m:
        return set()
    return set(re.findall(r'<a href="([^"]+)"', m.group(1)))


def _inject(doc: str, active: str | None) -> str:
    """Ensure the v7 links are in the sidebar.

    v6 owns the grouping and now carries a "v7 — fresh 2026-11-19 snapshot" category, so on a
    normal rebuild the five links are already grouped when v7 runs. This pass only adds a link
    that is *missing* (the first build after a fresh clone of a branch that has the pages but
    not yet the nav), and it re-marks the active page. Adding a duplicate is what a naive
    append would do, and a duplicated link is how a sidebar becomes unreadable.
    """
    if MARKER in doc:
        doc = re.sub(re.escape(MARKER) + r".*?" + re.escape(MARKER), "", doc, flags=re.S)
    # Only the sidebar counts. The landing page also carries v7 links inside its category card,
    # and scanning the whole document would let that card masquerade as a sidebar entry — which
    # is exactly how the first version of this function deleted the sidebar links and reported
    # href_set_preserved=False on index.html.
    present = _hrefs(doc)
    need = [h for h in LABELS if h not in present]
    if not need:
        return doc
    block = MARKER + "".join(_link(h, active) for h in need) + MARKER
    return doc.replace("</nav>", block + "</nav>", 1)


CARDS = (
    '<div class="card"><h4><a href="v7-slate.html">v7 — fresh snapshot</a> '
    '<span class="catcount">5 pages</span></h4>'
    '<p>Re-cut from the official pages read on 2026-11-19: the originated 3-day slate, the '
    'strategy lab with its pre-registrations, the walk-forward skill measurement, and the '
    'methodology behind both.</p>'
    '<p style="margin-top:8px;font-size:12.5px">'
    '<a href="v7-strategies.html">Strategy lab</a> · '
    '<a href="v7-skill.html">Measured skill</a> · '
    '<a href="v7-methodology.html">Methodology</a> · '
    '<a href="v7-verify.html">Verification</a></p></div>'
)
CARD_GRID_MARKER = 'id="v6-categories"'


def run() -> dict:
    pages = sorted(p for p in SITE.glob("*.html"))
    before: dict[str, set[str]] = {}
    changed = 0
    lost: list[str] = []
    for p in pages:
        if p.name in LABELS:
            continue
        doc = p.read_text()
        if "<nav>" not in doc:
            continue
        before[p.name] = _hrefs(doc)
        new = _inject(doc, p.name)
        if new != doc:
            changed += 1
        if before[p.name] - _hrefs(new):
            lost.append(p.name)
        p.write_text(new)

    # the landing page gets its own card, appended inside the v6 card grid
    cards_added = False
    idx = SITE / "index.html"
    if idx.exists():
        doc = idx.read_text()
        if CARDS not in doc:
            start = doc.find(CARD_GRID_MARKER)
            if start >= 0:
                # the grid's closing tag is the last </div> before the next <h2>
                nxt = doc.find("<h2", start)
                seg = doc[start:nxt] if nxt > 0 else doc[start:]
                close = seg.rfind("</div>")
                if close > 0:
                    pos = start + close
                    doc = doc[:pos] + CARDS + doc[pos:]
                    idx.write_text(doc)
                    cards_added = CARDS in idx.read_text()

    card_present = idx.exists() and CARDS in idx.read_text()
    return {"pages_touched": changed, "links": len(LABELS),
            "links_lost": lost, "landing_card_present": card_present,
            "landing_card_added_this_run": cards_added,
            "href_set_preserved": not lost}
