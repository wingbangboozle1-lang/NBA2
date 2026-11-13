"""Convenience entry point: build the data layer, then the site, then verify.

`python -m nba2.pipeline.build_data` is the one command the README and CI use.
"""

from __future__ import annotations

from pathlib import Path

from . import build_site, build_site_data, lint


def main(check: bool = True) -> int:
    data = build_site_data.main()
    pages = build_site.build()
    print(f"rendered {len(pages)} pages")
    if check:
        problems = lint.lint_all(Path(__file__).resolve().parents[2])
        if problems:
            print(f"\nLINT FAILED — {len(problems)} problem(s):")
            for pr in problems:
                print("  -", pr)
            return 1
        print("lint: all rows sourced, all internal links resolve, no placeholders found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
