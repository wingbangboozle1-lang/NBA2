#!/usr/bin/env python3
"""Regenerate the test-count figures in README.md from the suites themselves.

    python3 audit/2026-11-14-bc867bff/sync_readme_tests.py [--check]

Why a second sync script next to `audit/2026-11-14-3681/sync_readme_counts.py`: that one owns the
page/table/row counts generated from `data/site.json`, and it is right to leave it alone. What it
does not cover is the test counts quoted beside the suite commands in README prose, which go stale
on every build that adds a test — the same class of defect F-033 records for the row counts. This
session corrected those figures, so the correction is scripted rather than typed.

Matching is line-based and deliberately narrow: a number is rewritten only on a line that both
quotes a count AND names the suite whose count it claims to be. A line that names no suite, or that
is written as history ("59 tests (was 43)"), is left alone and reported, because rewriting another
session's changelog line would be editing a record rather than refreshing a measurement.

Rule used for the measurement: count `def test_…` methods per suite directory. Verified in this tree
to equal `python -m unittest discover`'s own "Ran N tests" for all three suites (70 / 89 / 49), so
the README figure, the methodology-page figure and the number `tools/crosscheck_site.py` enforces
(CC-DOC-01) are the same measurement taken three ways.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"

SUITES = {"nba2/tests": "v1", "nba2/v2": "v2", "backtest/tests": "backtest"}
METHOD = re.compile(r"^\s+def (test_\w+)", re.M)
COUNT = re.compile(r"(?<=#\s)(\d+)(?=\s+tests\b)|(?<=\()(\d+)(?=\s+tests\))")
HISTORY = re.compile(r"\(was \d+\)|prior work|unchanged")


def measure() -> dict[str, int]:
    out = {}
    for sub in SUITES:
        d = ROOT / sub
        out[sub] = (sum(len(METHOD.findall(f.read_text(encoding="utf-8")))
                        for f in sorted(d.glob("test_*.py"))) if d.is_dir() else 0)
    return out


def suite_in(line: str) -> str | None:
    """Which suite, if any, does this line claim to be counting?"""
    for sub in SUITES:
        if sub in line:
            return sub
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report drift and exit 1 instead of writing")
    args = ap.parse_args()

    counts = measure()
    lines = README.read_text(encoding="utf-8").split("\n")
    changed, skipped = 0, []
    for i, line in enumerate(lines):
        m = COUNT.search(line)
        if not m or "unittest" not in line and "test suite" not in line.lower():
            continue
        sub = suite_in(line)
        if sub is None:
            skipped.append((i + 1, "names no suite", line.strip()))
            continue
        if HISTORY.search(line):
            skipped.append((i + 1, "written as history", line.strip()))
            continue
        want = counts[sub]
        if int(m.group(0)) != want:
            lines[i] = line[:m.start()] + str(want) + line[m.end():]
            changed += 1

    text = "\n".join(lines)
    original = README.read_text(encoding="utf-8")
    fig = ", ".join(f"{SUITES[k]} {v}" for k, v in counts.items())
    if text == original:
        print(f"README test counts already current ({fig}); nothing to do")
        for ln, why, t in skipped:
            print(f"  left alone, line {ln} ({why}): {t[:96]}")
        return 0
    if args.check:
        print(f"README test counts are stale ({fig}):")
        for a, b in zip(original.split("\n"), text.split("\n")):
            if a != b:
                print(f"  - {a.strip()}\n  + {b.strip()}")
        return 1
    README.write_text(text, encoding="utf-8")
    print(f"README test counts -> {fig} ({changed} figure(s) rewritten)")
    for ln, why, t in skipped:
        print(f"  left alone, line {ln} ({why}): {t[:96]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
