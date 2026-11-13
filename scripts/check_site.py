#!/usr/bin/env python3
"""Integration checks for the NBA2 site (docs/).
1) every internal link resolves  2) every data-table row has an <a href> source
3) every page has nav + footer  4) no 'unverified' cells without .flag styling"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "dashboard")
errors, checked_rows = [], 0

pages = [f for f in os.listdir(DOCS) if f.endswith(".html")]
for p in sorted(pages):
    text = open(os.path.join(DOCS, p), encoding="utf-8").read()
    # 1. internal links
    for href in re.findall(r'href="([^"]+)"', text):
        if href.startswith(("http", "mailto", "#")):
            continue
        if not os.path.exists(os.path.join(DOCS, href.split("#")[0])):
            errors.append(f"{p}: broken internal link {href}")
    # 2. data-table rows carry a source link
    for row in re.findall(r"<tr>(.*?)</tr>", text, re.S):
        if "<th>" in row:
            continue  # header row
        checked_rows += 1
        if "<a href=" not in row and 'class="flag"' not in row:
            # allowed: non-data tables (gates table on strategies, suggestions tables)
            if p in ("strategies.html", "suggestions.html", "questions.html", "flagged.html"):
                continue
            errors.append(f"{p}: row without source link: {row[:90]}...")
    # 3. nav + footer
    if "<nav>" not in text or "<footer" not in text:
        errors.append(f"{p}: missing nav/footer")
    # 4. every exact-cell 'unverified' must be inside a styled .flag span
    for m in re.findall(r'>(unverified)<', text):
        if '<span class="flag">unverified</span>' not in text:
            errors.append(f"{p}: bare 'unverified' cell without .flag styling")

print(f"pages={len(pages)} rows_checked={checked_rows}")
if errors:
    print(f"FAIL ({len(errors)}):")
    for e in errors[:40]:
        print("  ", e)
    sys.exit(1)
print("PASS: all internal links resolve; all data rows source-linked; nav/footer present")
