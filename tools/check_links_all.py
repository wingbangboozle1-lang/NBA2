#!/usr/bin/env python3
"""check_links_all.py — whole-site link integrity across ALL sessions' pages.

Integration-session tool: scans every .html file in the repo (root, pages/, verified/, docs/),
extracts href/src attributes, and verifies that internal targets exist (files and same-file
anchors). External http(s) links are listed but not fetched. Exit code 1 on broken links.

This tool is read-only with respect to other sessions' pages — it checks, never edits.
Run: python3 tools/check_links_all.py
"""
import os
import re
import sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ATTR_RE = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
SKIP_SCHEMES = ("http", "https", "mailto", "tel", "javascript", "data")


def page_ids(text):
    ids = set()
    for m in re.finditer(r'\bid\s*=\s*["\']([^"\']+)["\']', text, re.IGNORECASE):
        ids.add(m.group(1))
    for m in re.finditer(r'<a\s+name\s*=\s*["\']([^"\']+)["\']', text, re.IGNORECASE):
        ids.add(m.group(1))
    return ids


def main():
    pages = {}
    for dirpath, _dirs, files in os.walk(ROOT):
        if ".git" in dirpath:
            continue
        for f in files:
            if f.endswith(".html"):
                p = os.path.join(dirpath, f)
                rel = os.path.relpath(p, ROOT)
                with open(p, encoding="utf-8", errors="replace") as fh:
                    pages[rel] = fh.read()

    broken, checked, external = [], 0, 0
    for rel, text in pages.items():
        ids = page_ids(text)
        for m in ATTR_RE.finditer(text):
            target = m.group(1).strip()
            if urlparse(target).scheme in ("http", "https"):
                external += 1
                continue
            if not target or target.startswith(SKIP_SCHEMES) or target == "#":
                continue
            checked += 1
            file_part, _, anchor = target.partition("#")
            if target.startswith("#"):
                if anchor and anchor not in ids:
                    broken.append(f"{rel}: broken anchor -> #{anchor}")
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(rel), file_part))
            if not os.path.exists(os.path.join(ROOT, resolved)):
                broken.append(f"{rel}: broken link -> {target}")
            elif anchor:
                with open(os.path.join(ROOT, resolved), encoding="utf-8", errors="replace") as fh:
                    if anchor not in page_ids(fh.read()):
                        broken.append(f"{rel}: broken anchor in target -> {target}#{anchor}")

    print(f"scanned {len(pages)} HTML files | {checked} internal links checked | {external} external links")
    if broken:
        print(f"BROKEN ({len(broken)}):")
        for b in sorted(set(broken)):
            print("  -", b)
        sys.exit(1)
    print("ALL INTERNAL LINKS OK")


if __name__ == "__main__":
    main()
