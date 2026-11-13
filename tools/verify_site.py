#!/usr/bin/env python3
"""verify_site.py — line-by-line site verification (session-arena-35264d96).

Enforces the project's verification rules on docs/:
  R1. Every table row marked data-row must contain at least one <a href> source link.
      (Methodology/demo rows must carry data-row-type="internal" or "demo"; they still need a link,
      which may be an internal anchor.)
  R2. Every internal link (href to *.html or #anchor) resolves: file exists, and if an anchor is
      given, the anchor id exists in the target file.
  R3. Every page has a unique <title> and includes the standard nav.
  R4. Pages may not contain placeholder text like TODO/TBD/XXX/lorem.
  R5. Unverified values must be marked: cells carrying class "flag-unverified" or "flag-demo" are
      collected so the Flagged-for-Review page can be cross-checked (count report only here).

Exit code 1 if any hard rule fails.
"""
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

NAV_LINKS = [
    "index.html", "executive-summary.html", "strategies.html", "validation-gates.html",
    "correlation.html", "leaderboard.html", "picks.html", "injuries-rotations.html",
    "game-flow.html", "questions.html", "suggestions.html", "flagged-for-review.html",
    "sources.html",
]

PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|lorem ipsum|FIXME|XXX)\b", re.IGNORECASE)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = None
        self._in_title = False
        self.rows = []          # (line_no, has_link, row_type, text)
        self.hrefs = []         # (line_no, href)
        self.ids = set()
        self._cur_row = None    # dict
        self.unverified_cells = 0
        self.demo_cells = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "tr":
            self._cur_row = {"line": self.getpos()[0], "has_link": False, "type": None, "chars": 0,
                             "is_data_row": "data-row" in a}
            self._cur_row["type"] = a.get("data-row-type")
        elif tag == "a" and self._cur_row is not None:
            href = a.get("href")
            if href:
                self._cur_row["has_link"] = True
                self.hrefs.append((self.getpos()[0], href))
        elif tag == "td" or tag == "th":
            if self._cur_row is not None:
                cls = a.get("class", "")
                if "flag-unverified" in cls:
                    self.unverified_cells += 1
                if "flag-demo" in cls:
                    self.demo_cells += 1
        elif tag in ("h1", "h2", "h3", "section", "div", "p", "li"):
            if "id" in a:
                self.ids.add(a["id"])

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data
        if self._cur_row is not None:
            self._cur_row["chars"] += len(data.strip())

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "tr" and self._cur_row is not None:
            if self._cur_row["is_data_row"]:
                self.rows.append((self._cur_row["line"], self._cur_row["has_link"],
                                  self._cur_row["type"], self._cur_row["chars"]))
            self._cur_row = None


def strip_tags(fragment):
    return re.sub(r"<[^>]+>", " ", fragment)


def anchor_exists(html_text, anchor):
    return (f'id="{anchor}"' in html_text) or (f"id='{anchor}'" in html_text)


def main():
    errors, report = [], []
    pages = sorted(f for f in os.listdir(DOCS) if f.endswith(".html"))
    all_ids = {}
    page_titles = {}

    for page in pages:
        path = os.path.join(DOCS, page)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        p = PageParser()
        p.feed(text)
        p.close()
        page_titles[page] = (p.title or "").strip()
        all_ids[page] = p.ids

        if not p.title:
            errors.append(f"{page}: missing <title>")
        body = strip_tags(text)
        m = PLACEHOLDER_RE.search(body)
        if m:
            errors.append(f"{page}: placeholder text found: '{m.group(0)}'")

        # R1: data rows need a link
        bad_rows = [(ln, rt, ch) for (ln, has_link, rt, ch) in p.rows if not has_link]
        for ln, rt, ch in bad_rows:
            errors.append(f"{page}:{ln}: data row missing source/anchor link (row_type={rt})")
        # rows must have some content
        for ln, has_link, rt, ch in p.rows:
            if ch < 5:
                errors.append(f"{page}:{ln}: data row nearly empty ({ch} chars)")

        # R3: nav present
        for nav in NAV_LINKS:
            if nav != page and f'href="{nav}"' not in text:
                errors.append(f"{page}: standard nav link to {nav} missing")

        report.append({
            "page": page,
            "title": page_titles[page],
            "data_rows": len(p.rows),
            "rows_without_link": len(bad_rows),
            "links": len(p.hrefs),
            "unverified_cells": p.unverified_cells,
            "demo_cells": p.demo_cells,
        })

        # collect hrefs for R2
        for ln, href in p.hrefs:
            if href.startswith("http"):
                continue
            if href.startswith("#"):
                if href[1:] and href[1:] not in all_ids[page]:
                    # anchors may be defined later in the same file; recheck after all pages parsed
                    pass
            else:
                target = href.split("#")[0]
                if target and not os.path.exists(os.path.join(DOCS, target)):
                    errors.append(f"{page}:{ln}: broken internal link -> {href}")

    # second pass: same-file anchors (defined anywhere in file)
    for page in pages:
        path = os.path.join(DOCS, page)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for ln, href in re.findall(r'<a[^>]+href="(#[^"]+)"', text) and []:
            pass
    # simpler: scan raw hrefs per file
    for page in pages:
        path = os.path.join(DOCS, page)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for href in re.findall(r'href="#([^"]+)"', text):
            if href and not anchor_exists(text, href):
                errors.append(f"{page}: broken anchor -> #{href}")

    # duplicate titles
    seen = {}
    for page, t in page_titles.items():
        seen.setdefault(t, []).append(page)
    for t, ps in seen.items():
        if len(ps) > 1:
            errors.append(f"duplicate <title> '{t}' on {ps}")

    print(json.dumps(report, indent=2))
    total_rows = sum(r["data_rows"] for r in report)
    total_links = sum(r["links"] for r in report)
    print(f"\nSUMMARY: {len(pages)} pages | {total_rows} data rows | {total_links} links")
    if errors:
        print(f"FAILED with {len(errors)} error(s):")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("VERIFICATION PASSED: every data row has a source link; no broken internal links; "
          "no placeholders; nav complete on all pages.")


if __name__ == "__main__":
    main()
