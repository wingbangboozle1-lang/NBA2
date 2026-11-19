"""Check the session site: no broken internal link, every table row carries a source, no placeholders.

Same standard the repository applies to its own published tree (`nba2/v2/check.py`), applied to this
session's pages so a reader gets the same guarantee here.

Run: python3 audit/923eb342/check.py
"""

from __future__ import annotations

import html
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
LOCAL = re.compile(r'(?:href|src)="([^"#][^"]*)"')
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
TAG = re.compile(r"<[^>]+>")
BLANK_OK = re.compile(r"(no source|not submitted|unverified|—|blank|FLAG|F-923|Q-923|SG-923)", re.I)


def text(c: str) -> str:
    return html.unescape(TAG.sub("", c)).strip()


problems: list[str] = []
pages = sorted(HERE.glob("*.html"))
if not pages:
    problems.append("no pages built")
STYLE = re.compile(r"<style>.*?</style>", re.S)
SCRIPT = re.compile(r"<script>.*?</script>", re.S)

for p in pages:
    doc = p.read_text()
    prose = SCRIPT.sub("", STYLE.sub("", doc))
    for link in LOCAL.findall(doc):
        if link.startswith(("http://", "https://", "mailto:", "//", "data:")) or link.startswith("#"):
            continue
        target = (p.parent / link.split("#")[0].split("?")[0]).resolve()
        if not target.exists():
            problems.append(f"{p.name}: broken local link -> {link}")
    for token in ("TODO", "TBD", "lorem", "XXX", "{{", "}}"):
        if token in prose:
            problems.append(f"{p.name}: placeholder token {token!r}")
    for token in ("None", "nan", "NaN"):
        if re.search(rf"(?<![A-Za-z]){token}(?![A-Za-z])", prose):
            problems.append(f"{p.name}: placeholder token {token!r}")
    for m in ROW.finditer(doc):
        row = m.group(1)
        cells = CELL.findall(row)
        if not cells:
            continue
        if not re.search(r'href="https?://', row):
            problems.append(f"{p.name}: table row with no source link -> {text(' '.join(cells))[:80]!r}")
        joined = " ".join(text(c) for c in cells)
        if not joined.strip():
            problems.append(f"{p.name}: fully empty row")
        for c in cells:
            t = text(c)
            if t in ("", "None", "nan", "NaN") and not BLANK_OK.search(joined):
                problems.append(f"{p.name}: blank cell with no reason -> {joined[:80]!r}")

# every page in PAGES must exist and every page must be reachable from index.html
idx = (HERE / "index.html").read_text() if (HERE / "index.html").exists() else ""
for p in pages:
    if p.name != "index.html" and f'href="{p.name}"' not in idx and \
            not any(f'href="{p.name}"' in q.read_text() for q in pages):
        problems.append(f"{p.name}: unreachable from every page")

for x in problems:
    print("PROBLEM:", x)
print(f"{'FAIL' if problems else 'OK'} — {len(problems)} problem(s) across {len(pages)} pages")
sys.exit(1 if problems else 0)
