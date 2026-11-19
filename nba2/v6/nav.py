"""K-06 — turn the flat 50-link sidebar into a categorised dashboard.

Why this exists
---------------
Every tree (v2, v3, v4, v5) appended its own pages to the shared ``<nav>`` as a flat list,
so the published site grew a single column of ~50 undifferentiated links. Nothing was
wrong with any individual page; the problem is that a reader cannot see what kind of page
they are looking at. The brief asks for subpages **organised by category**, and for the
projection and bet surfaces never to be mixed — so the two are separate groups with
separate headings.

What this module does and does not change
-----------------------------------------
It rewrites only the ``<nav>`` block and inserts one card grid on the landing page. It does
**not** touch a page's body, tables or numbers, and it never removes a link: the set of
hrefs after grouping is verified equal to the set before, and the build fails if it is not.

It runs last in the pipeline, after v5, and is idempotent (marker-guarded), so a rebuild
that runs v2 → v3 → v4 → v5 → v6 lands on exactly the same bytes as what is committed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .common import ROOT, SITE, V6, esc

CSS_MARKER = "/* === v6 nav categories (nba2/v6/nav.py) === */"
NAV_MARKER = '<div class="navgroup">'
V6_NAV_MARKER = '<a href="injury-archive.html"'
LANDING_MARKER = '<div class="cards" id="v6-categories">'

CATEGORIES: list[tuple[str, str, list[str]]] = [
    ("Start here", "What this desk is, what it has measured, and where the numbers come from.",
     ["index", "executive-summary", "methodology", "sources"]),
    ("Projection — safe to publish",
     "Our originated numbers. Nothing here is priced or actionable: what we think, and how "
     "much the two estimators disagree.",
     ["slate", "projections", "projection", "lines", "teams", "market-prior",
      "correlations", "props", "gameflow", "lategame", "travel", "rotation",
      "rotation-replacement", "minutes"]),
    ("Bet surface — gated",
     "Gated: no row here is actionable until its gates pass. The trigger level is the only "
     "number that would make acting rational.",
     ["bet", "picks", "strategies", "strategy-lab", "trials"]),
    ("Official record & settlement",
     "What the league published, what the sealed ledger predicted, and what has been "
     "settled against an official final.",
     ["official-results", "results", "result-feed-v5", "results-coverage", "settle",
      "settlement", "ledger"]),
    ("Injuries, rotation & players",
     "Every official release this repository holds, the diff between consecutive reports, "
     "and the player logs behind the rotation model.",
     ["injuries", "v4-injuries", "injury-diff", "injury-archive", "player-logs",
      "playerlogs-full", "player-coverage"]),
    ("Verification & measured skill",
     "Gates, backtests, luck attribution and the live checks — the part that says whether "
     "any of the above is better than a coin flip.",
     ["verification", "verification-v3", "v4-verify", "v5-verify", "v6-verify",
      "live-verification", "backtest", "skill-attribution", "endpoints",
      "capture-verification"]),
    ("v7 — fresh 2026-11-19 snapshot",
     "Cut from the official pages read on 2026-11-19: the originated three-day slate, the "
     "gated strategy lab with its pre-registrations, and the walk-forward skill test.",
     ["v7-slate", "v7-strategies", "v7-skill", "v7-methodology", "v7-verify"]),
    ("Decisions, questions & flags",
     "What needs an owner decision before it is built, what we do not know, and everything "
     "flagged for review.",
     ["questions", "suggestions", "decision-queue", "decisions-needed", "flagged",
      "repo-review"]),
]

CSS = CSS_MARKER + """
.navgroup{margin:0 0 10px}
.navgroup > span{display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.7px;
  color:var(--muted);margin:10px 0 3px;padding:0 10px;font-weight:700}
.navgroup a{font-size:13px;padding:5px 10px;margin-bottom:1px}
.cards .card h4 a{color:var(--ink)}
.cards .card h4 a:hover{color:var(--accent2)}
.catcount{color:var(--muted);font-size:11px;font-weight:400}
"""


# ------------------------------------------------------------------ nav pass
def _flat_nav(doc: str) -> list[tuple[str, str]]:
    out, seen = [], set()
    m = re.search(r"<nav>(.*?)</nav>", doc, re.S)
    if not m:
        return out
    for href, label in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', m.group(1), re.S):
        if href in seen:
            continue
        seen.add(href)
        out.append((href, label))
    return out


def _group(links: list[tuple[str, str]]) -> list[tuple[str, str, list[tuple[str, str]]]]:
    """Assign every link to exactly one category, in a fixed order; leftovers go last."""
    assigned: dict[str, tuple[str, str]] = {}
    for title, blurb, names in CATEGORIES:
        for n in names:
            assigned[f"{n}.html"] = (title, blurb)
    buckets: dict[str, list[tuple[str, str]]] = {t: [] for t, _, _ in CATEGORIES}
    buckets["Other pages"] = []
    for href, label in links:
        key = assigned.get(href)
        if key and key[0] in buckets:
            buckets[key[0]].append((href, label))
        else:
            buckets["Other pages"].append((href, label))
    out = [(t, b, buckets[t]) for t, b, _ in CATEGORIES]
    if buckets["Other pages"]:
        out.append(("Other pages", "Pages no category claimed — listed so nothing is "
                                   "unreachable.", buckets["Other pages"]))
    return out


def _nav_html(links: list[tuple[str, str]], active_href: str | None) -> str:
    import html as H
    parts = []
    for title, blurb, items in _group(links):
        if not items:
            continue
        on = ' class="on"'
        # Labels arriving from the earlier trees are already entity-escaped ("Teams &amp;
        # estimators"). Re-escaping them for the title attribute would print "&amp;amp;" in
        # the tooltip, so unescape once first.
        inner = "\n".join(
            f'<a href="{esc(h)}" title="{esc(H.unescape(_strip(l)))}"'
            f'{on if h == active_href else ""}>{l}</a>'
            for h, l in items)
        parts.append(f'<div class="navgroup"><span title="{esc(blurb)}">{esc(title)}</span>'
                     f'\n{inner}\n</div>')
    return "\n".join(parts)


def _strip(label: str) -> str:
    return re.sub(r"<[^>]+>", "", label)


def inject_nav() -> int:
    """Append this tree's six pages to every published page's nav, before grouping.

    v3, v4 and v5 each do exactly this, marker-guarded and idempotent. Without it the
    landing page — which v2 owns — would never advertise the v6 pages, and a reader
    following the sidebar could not reach the injury archive.
    """
    from . import publish as PUB
    n = 0
    for p in sorted(SITE.glob("*.html")):
        doc = p.read_text()
        if "</nav>" not in doc or V6_NAV_MARKER in doc:
            continue
        block = "\n".join(f'<a href="{esc(h)}">{l}</a>' for h, l in PUB.V6_NAV)
        p.write_text(doc.replace("</nav>", block + "\n</nav>", 1))
        n += 1
    return n


def rewrite_nav() -> dict:
    """Group the nav on every published page. Returns a report with the href-set check."""
    # The canonical flat order comes from the landing page, which every tree has appended to.
    index = SITE / "index.html"
    if not index.exists():
        return {"n_pages": 0, "n_links": 0, "href_set_preserved": False,
                "problems": ["site/index.html is missing"]}
    links = _flat_nav(index.read_text())
    problems = []
    n_pages = 0
    for p in sorted(SITE.glob("*.html")):
        doc = p.read_text()
        if "<nav>" not in doc or "</nav>" not in doc:
            continue
        current = _flat_nav(doc)
        if not current:
            continue
        before = {h for h, _ in current}
        # A page's own nav is its own list; group it, preserving its href set exactly.
        html = _nav_html(current, p.name)
        new_nav = f"<nav>\n{html}\n</nav>"
        doc = re.sub(r"<nav>.*?</nav>", lambda _m: new_nav, doc, count=1, flags=re.S)
        after = {h for h, _ in _flat_nav(doc)}
        if before != after:
            problems.append(f"{p.name}: grouping changed the set of nav links "
                            f"(lost {sorted(before - after)}, gained {sorted(after - before)})")
            continue
        if "</nav>" in doc and NAV_MARKER not in doc:
            problems.append(f"{p.name}: grouping did not take")
            continue
        p.write_text(doc)
        n_pages += 1
    return {"n_pages": n_pages, "n_links": len(links),
            "nav_targets": sorted(h for h, _ in links),
            "href_set_preserved": not problems, "problems": problems}


# -------------------------------------------------------------- landing cards
def landing_cards() -> bool:
    """Insert the category card grid on the landing page, right after the lede."""
    p = SITE / "index.html"
    if not p.exists():
        return False
    doc = p.read_text()
    if LANDING_MARKER in doc:
        return False
    links = _flat_nav(doc)
    known = {h for h, _ in links}
    cards = []
    for title, blurb, names in CATEGORIES:
        pages = [n for n in names if f"{n}.html" in known]
        if not pages:
            continue
        first = f"{pages[0]}.html"
        more = "".join(f'<a href="{esc(n)}.html">{esc(_pretty(n))}</a> · '
                       for n in pages[1:])
        cards.append(
            f'<div class="card"><h4><a href="{esc(first)}">{esc(title)}</a> '
            f'<span class="catcount">{len(pages)} pages</span></h4>'
            f'<p>{esc(blurb)}</p>'
            f'<p style="margin-top:8px;font-size:12.5px">{more.rstrip(" · ")}</p></div>')
    block = (f'<h2>Browse by category</h2>\n<div class="cards" id="v6-categories">'
             f'{"".join(cards)}</div>')
    anchor = "<h2>Start here</h2>"
    if anchor in doc:
        doc = doc.replace(anchor, block + "\n" + anchor, 1)
    else:
        m = re.search(r"</h1>", doc)
        if not m:
            return False
        doc = doc[:m.end()] + "\n" + block + doc[m.end():]
    p.write_text(doc)
    return True


def _pretty(name: str) -> str:
    return name.replace("-", " ").title()


# ------------------------------------------------------------------------ css
def ensure_css() -> bool:
    css = SITE / "assets" / "site.css"
    if not css.exists():
        return False
    text = css.read_text()
    if CSS_MARKER in text:
        return False
    css.write_text(text.rstrip() + "\n\n" + CSS)
    return True
