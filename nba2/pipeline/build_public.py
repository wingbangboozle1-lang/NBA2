"""Assemble the exact tree that GitHub Pages publishes, and prove it has no broken links.

    python -m nba2.pipeline.build_public --out _site

Why this exists
---------------
The repository grew several site trees in parallel (the root dashboard, ``site/``,
``docs/``, ``dashboard/``, ``backtest/``, ``originated/``), and for a while the committed
``pages.yml`` published one tree while the repository's Pages setting published another.
A reader got a different dashboard from the one the workflow built, and nothing in CI
compared the two.

This module removes that ambiguity:

* it names the **one** published tree, as an explicit list of paths — not as "the repo root",
  so a new top-level directory can never silently become part of the public site;
* it **copies** that tree into the artifact directory the workflow uploads, so what is
  published is a build output rather than a source directory;
* it **checks every internal link in the copied tree** and fails loudly if one does not
  resolve. A broken link in the published site is a build failure, not a support ticket.

The published set is deliberately small and explicit:

* ``index.html`` + ``flagged.html`` — the canonical dashboard entry points;
* ``pages/**`` — the category subpages of that dashboard;
* ``backtest/**`` — the measured-skill backtest, linked from the dashboard (its own pages);
* ``css/**``, ``assets/**``, ``styles.css``, ``app.js`` — the styles and behaviour;
* ``COORDINATION.md``, ``README.md`` — the board and the map of the repository.

Everything else in the repository (``site/``, ``docs/``, ``dashboard/``, ``originated/``,
``verified/``, ``archive/``, the code and the data) stays in the repository and is linked as
source, not shipped as a second dashboard.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# (path, is_directory, excluded sub-paths) — the complete published surface.
# Nothing else is published, and a new top-level directory can never become public by accident.
PUBLISH_TREE: list[tuple[str, bool, tuple[str, ...]]] = [
    ("index.html", False, ()),
    ("flagged.html", False, ()),
    ("pages", True, ()),
    ("backtest", True, ("engine", "tests", "__pycache__")),
    ("css", True, ()),
    ("assets", True, ()),
    ("styles.css", False, ()),
    ("app.js", False, ()),
    ("COORDINATION.md", False, ()),
    ("README.md", False, ()),
]

# Never copied, even if they appear inside a published directory.
EXCLUDE_DIRS = {"__pycache__", ".git", ".github", ".pytest_cache", ".ruff_cache"}
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".py"}

_LINK = re.compile(r'(?:href|src)\s*=\s*"([^"]*)"', re.IGNORECASE)


def _skip(path: Path) -> bool:
    if path.suffix in EXCLUDE_SUFFIX:
        return True
    return any(part in EXCLUDE_DIRS for part in path.parts)


def copy_tree(out: Path) -> list[str]:
    """Copy PUBLISH_TREE into `out`. Returns the list of published files, repo-relative."""
    copied: list[str] = []
    for rel, is_dir, skip_dirs in PUBLISH_TREE:
        src = ROOT / rel
        if not src.exists():
            raise SystemExit(f"publish set lists {rel!r}, which does not exist in the repository")
        dst = out / rel
        if is_dir:
            for p in sorted(src.rglob("*")):
                if p.is_dir() or _skip(p.relative_to(src)):
                    continue
                if any(part in skip_dirs for part in p.relative_to(src).parts):
                    continue
                target = dst / p.relative_to(src)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, target)
                copied.append(str((out / p.relative_to(src)).relative_to(out)))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            copied.append(rel)
    # GitHub Pages must not run Jekyll over the artifact.
    (out / ".nojekyll").write_text("")
    return sorted(copied)


def check_links(out: Path) -> list[str]:
    """Every internal link in the published tree must resolve inside the published tree."""
    broken: list[str] = []
    for page in sorted(out.rglob("*.html")):
        text = page.read_text(errors="ignore")
        for raw in _LINK.findall(text):
            target = html.unescape(raw.strip())
            if not target or target.startswith(("#", "http://", "https://", "mailto:", "data:", "//")):
                continue
            target = target.split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue
            if target.startswith("/"):
                # site-root absolute path: GitHub Pages serves it under the project base
                rel = target.lstrip("/")
                candidates = [out / rel]
                if rel.startswith("NBA2/"):
                    candidates = [out / rel[len("NBA2/"):]]
            else:
                candidates = [(page.parent / target).resolve()]
            if not any(c.exists() for c in candidates):
                broken.append(f"{page.relative_to(out)} -> {raw}")
    return broken


def build(out_dir: str = "_site") -> dict:
    out = (ROOT / out_dir).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    files = copy_tree(out)
    broken = check_links(out)
    if broken:
        print("BROKEN INTERNAL LINKS IN THE PUBLISHED TREE:", file=sys.stderr)
        for b in broken:
            print(f"  {b}", file=sys.stderr)
        raise SystemExit(f"publish tree has {len(broken)} broken internal link(s)")
    return {"out": str(out.relative_to(ROOT)), "files": len(files), "broken_links": 0}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="_site", help="output directory (default: _site)")
    args = ap.parse_args()
    res = build(args.out)
    print(f"published tree staged in {res['out']}/ — {res['files']} files, "
          f"{res['broken_links']} broken internal links")


if __name__ == "__main__":
    main()
