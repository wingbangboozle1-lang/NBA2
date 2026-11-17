#!/usr/bin/env python3
"""Reduce a captured ingest console to one publishable sentence.

Why this exists
---------------
The nightly ingest failed on the rolling surface for three consecutive scheduled runs
(2026-11-16T16:06Z, 2026-11-17T14:5xZ among them) and the *cause* could not be read
afterwards from two different agent sandboxes: GitHub serves job logs from
``*.blob.core.windows.net``, which is outside the egress allowlist those sandboxes run
under, so ``gh api .../jobs/<id>/logs`` returns ``EOF``. The failure itself was already
recorded (``data/raw/refresh_verdict.json``); the reason was not.

This tool turns a console log into a short, deterministic statement of *why* a surface
failed, so the reason can be committed next to the capture and read from the tree.

Rules
-----
* It never guesses. If no recognised failure line exists it says so and prints the last
  few non-empty lines instead — evidence, not a diagnosis.
* It is a pure function of the log text, so it is unit-tested offline
  (``tools/test_surface_reason.py``).
* It quotes the failing line rather than paraphrasing it: a paraphrase is how a real
  cause ("HTTP 403 from stats.nba.com") becomes a wrong one ("endpoint unreachable").

Usage
-----
    python3 tools/surface_reason.py <log-file> [--max-chars 400]
    python3 tools/surface_reason.py -            # read stdin
"""

from __future__ import annotations

import argparse
import re
import sys

# Ordered most-specific first: the first pattern that matches anywhere in the log wins.
# Each pattern is anchored on text this repository's own tools actually print.
PATTERNS: tuple[tuple[str, str], ...] = (
    # nba2.v2.refresh prints "  [FAIL] freshness/standings: ... — ..." or "REFRESH ABORTED"
    (r"^REFRESH ABORTED:.*$", "gate refused the refresh"),
    (r"^\s*\[FAIL\]\s*(?P<gate>[^:]+):(?P<rest>.*)$", "freshness/provenance gate failed"),
    # urllib / our own http_get wrapper
    (r"^.*fetch failed after \d+ tries: (?P<url>\S+): (?P<err>.*)$", "official endpoint unreachable"),
    (r"^.*HTTP (?P<code>\d{3}) for (?P<url>\S+).*$", "official endpoint answered with an error"),
    # python tracebacks: the last "Foo: message" line is the exception
    (r"^(?P<exc>[A-Za-z_][\w.]*(?:Error|Exception|Timeout)): (?P<msg>.*)$", "unhandled exception"),
)

COMPILED = tuple((re.compile(p), label) for p, label in PATTERNS)


def _clean(line: str) -> str:
    """Strip CI decorations and collapse whitespace, so the reason is publishable."""
    line = re.sub(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s*", "", line)   # GitHub's timestamp prefix
    line = re.sub(r"^::(?:error|warning)(?: title=[^:]*)?::", "", line)
    line = re.sub(r"\x1b\[[0-9;]*m", "", line)                    # ANSI colour
    return re.sub(r"\s+", " ", line).strip()


def reason(log_text: str, max_chars: int = 400) -> str:
    """One sentence: what failed and the line that says so. Never empty."""
    lines = log_text.splitlines()
    for pattern, label in COMPILED:
        for raw in lines:
            m = pattern.match(raw.strip()) or pattern.match(_clean(raw))
            if not m:
                continue
            quoted = _clean(raw)
            groups = {k: _clean(v) for k, v in m.groupdict().items() if v is not None}
            if label == "freshness/provenance gate failed":
                quoted = f"[FAIL] {groups.get('gate', '').strip()}: {groups.get('rest', '').strip()}"
            elif label == "official endpoint unreachable":
                quoted = f"{groups.get('url', '?')} -> {groups.get('err', '')}"
            elif label == "official endpoint answered with an error":
                quoted = f"HTTP {groups.get('code', '?')} for {groups.get('url', '?')}"
            elif label == "unhandled exception":
                quoted = f"{groups.get('exc', '?')}: {groups.get('msg', '')}"
            text = f"{label} — {quoted}"
            return text[:max_chars] if len(text) > max_chars else text
    # No recognised failure line: quote the tail rather than invent a cause.
    tail = [_clean(x) for x in lines if _clean(x)][-4:]
    if not tail:
        return "no console output was captured — the reason is not recorded, only the failure"
    text = "no recognised failure line; last output: " + " | ".join(tail)
    return text[:max_chars] if len(text) > max_chars else text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Reduce an ingest console to one reason sentence.")
    ap.add_argument("log", help="path to the captured console, or - for stdin")
    ap.add_argument("--max-chars", type=int, default=400)
    args = ap.parse_args(argv)
    text = sys.stdin.read() if args.log == "-" else open(args.log, encoding="utf-8", errors="replace").read()
    out = reason(text, args.max_chars)
    # GITHUB_OUTPUT wants a single line.
    print(out.replace("\n", " "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
