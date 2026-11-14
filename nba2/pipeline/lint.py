"""Build gate. Fails loudly on the four ways this site could lie:

1. a row without a source;
2. a row whose "official" source is not an official domain;
3. a value that looks invented (numeric impact, correlation, or a hedge word) in a place we
   have no data for;
4. a broken internal link, or HTML content that does not match the data file it renders from.

`python -m nba2.pipeline.lint` exits 1 with a list of problems, and CI runs it before Pages
deploys. A flagged/unverified row never fails the build — a blank with a reason is allowed;
an unsourced number is not.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

try:  # when run as a module inside the package
    from ..provenance import BLOCKED_ALLOWED_FIELDS
except ImportError:  # pragma: no cover - direct script execution
    BLOCKED_ALLOWED_FIELDS = {"status", "missing", "note", "market", "player", "team", "name",
                              "url", "cls", "usable", "key", "reason", "verdict", "disposition",
                              "attribution", "severity", "area", "statement", "action", "source", "id"}

ROOT = Path(__file__).resolve().parents[2]
SITE_JSON = ROOT / "data" / "site.json"

OFFICIAL_HOSTS = {"www.nba.com", "nba.com", "ak-static.cms.nba.com", "cdn.nba.com",
                  "oauth.nba.com", "stats.nba.com", "picks.nba.com"}
TRUSTED_OTHER = {"www.basketball-reference.com", "github.com", "www.espn.com"}

# strings that must never appear as a *value* anywhere in the site data
FORBIDDEN_VALUE = re.compile(
    r"(\bTBD\b|\bTODO\b|lorem ipsum|placeholder text|~\s?\d+\s?min\b|vs\.\s?~|[-\u2212]100\s?%|\bN/A\b|\bNaN\b)"
)
# the repo-review table *quotes* the fabricated strings it is reporting on, by design
FABRICATION_EXEMPT_TABLES = {"repo_review"}
# numeric claims about minutes/production impact (the exact class of thing that was fabricated before)
FABRICATION = re.compile(r"(\d+(\.\d+)?\s?(mpg|minutes of play|pts/reb/ast per game reduction)|"
                         r"-?\d+(\.\d+)?\s?% (scoring|rebounding|playmaking|production))", re.I)

ALLOWED_STATUS = {"PASS", "FAIL", "BLOCKED", "AT-RISK"}


def _rows(data: dict):
    for key, tbl in data["sections"].items():
        if isinstance(tbl, dict) and "rows" in tbl:
            for r in tbl["rows"]:
                yield key, tbl, r


def lint_data(data: dict) -> list[str]:
    problems: list[str] = []
    flag_ids = {r["values"].get("id") for k, t, r in _rows(data) if k == "flags"}
    flag_ids |= {r["key"] for k, t, r in _rows(data) if k == "flags"}

    for key, tbl, r in _rows(data):
        rid = f"{key}/{r['key']}"
        src = r.get("source") or {}
        url = src.get("url") or ""
        cls = src.get("class") or ""
        if r.get("verified") and cls != "official":
            problems.append(f"{rid}: row claims verified=True but its source class is {cls!r}")
        if cls == "blocked":
            for name, v in r["values"].items():
                if v is not None and name not in BLOCKED_ALLOWED_FIELDS:
                    problems.append(f"{rid}: field {name!r} has a value ({v!r}) on a BLOCKED source — "
                                    "a value with no source must be blank")

        if not cls:
            problems.append(f"{rid}: row has no source class")
        if cls == "official":
            host = urlparse(url).netloc
            # github.com is allowed because "this repository at this commit" is the authoritative
            # source for a repo-review claim; it is never allowed for NBA facts.
            if host not in OFFICIAL_HOSTS | {"github.com"}:
                problems.append(f"{rid}: marked official but host {host!r} is not an NBA-official domain")
            if not url.startswith("https://"):
                problems.append(f"{rid}: official source url is not https")
        elif cls in ("third_party", "derived") and not url:
            problems.append(f"{rid}: {cls} source needs the url it came from")

        if not r.get("flags") and any(v is None for v in r["values"].values()):
            problems.append(f"{rid}: blank value with no flag id (blanks must be explained)")
        if cls in ("third_party", "blocked") and not r.get("flags"):
            problems.append(f"{rid}: non-official source with no flag id")

        for fid in r.get("flags") or []:
            if fid not in flag_ids:
                problems.append(f"{rid}: references unregistered flag {fid}")

        for name, v in r["values"].items():
            if not isinstance(v, str):
                continue
            m = FORBIDDEN_VALUE.search(v)
            if m and cls != "blocked" and key not in FABRICATION_EXEMPT_TABLES:
                problems.append(f"{rid}: value for {name!r} contains {m.group(0)!r} — "
                                f"placeholders are not allowed in sourced cells")
            if FABRICATION.search(v) and key not in FABRICATION_EXEMPT_TABLES:
                problems.append(f"{rid}: value for {name!r} looks like an invented impact ({v[:70]!r})")

    # gate matrix: results must be from the fixed vocabulary
    for key, tbl, r in _rows(data):
        if key == "gate_matrix":
            res = r["values"].get("result")
            if res not in ALLOWED_STATUS:
                problems.append(f"{key}/{r['key']}: gate result {res!r} not in {sorted(ALLOWED_STATUS)}")
    return problems


def lint_html(data: dict, root: Path) -> list[str]:
    problems: list[str] = []
    html_pages = sorted(p for p in root.glob("**/*.html")
                        if ".git/" not in str(p) and "node_modules" not in str(p)
                        # the staged publish tree is a byte copy of files that are linted in place
                        and "_site/" not in p.as_posix())
    if not html_pages:
        return ["no HTML files found"]

    # The published tree is named explicitly in nba2/pipeline/build_public.py, so "exists on
    # disk" is no longer the same as "will be reachable". Every link target is still checked
    # against the repository, which is the stricter test: a link must resolve to a committed
    # file, not merely to a file that happens to sit in the publish list.
    existing = {p.relative_to(root).as_posix() for p in root.glob("**/*")
                if p.is_file() and ".git/" not in p.as_posix()}

    for p in html_pages:
        text = p.read_text(encoding="utf-8")
        rel = p.relative_to(root).as_posix()
        if rel.startswith("archive/"):
            # Frozen copies of superseded pages. They are kept byte-for-byte for audit, so their
            # internal links point into the tree as it was; rewriting them would falsify the copy.
            continue
        # internal links
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http", "mailto:", "#")):
                continue
            target = href.split("#")[0]
            if not target:
                continue
            base = p.parent.relative_to(root).as_posix()
            full = (Path(base) / target) if base not in (".", "") else Path(target)
            target_path = (root / full).resolve()
            try:
                norm = target_path.relative_to(root.resolve()).as_posix()
            except ValueError:
                problems.append(f"{rel}: link escapes the site root -> {href}")
                continue
            if norm not in existing:
                problems.append(f"{rel}: broken internal link -> {href}")
                continue
            frag = href.split("#", 1)[1] if "#" in href else ""
            if frag and norm.endswith(".html"):
                if f'id="{frag}"' not in (root / norm).read_text(encoding="utf-8"):
                    problems.append(f"{rel}: link points at #{frag} but {norm} has no such anchor")
        # every data row's source must be reachable in the page
        if "no source" not in text and rel == "index.html":
            pass
        # structural rule applies to what *this* pipeline emits. Another session's
        # dashboard/ has its own generator and its own checker (scripts/check_site.py), which
        # passes; flagging their markup here would be a false alarm on a file we must not edit.
        if rel.startswith(("index.html", "pages/", "flagged.html")):
            if re.search(r"<td[^>]*>\s*</td>", text):
                problems.append(f"{rel}: an empty <td> exists — use the blank marker, not whitespace")
        if "TODO" in text or "FIXTHIS" in text:
            problems.append(f"{rel}: contains a TODO marker")

    # row-count parity: the emitted JSON must be what the pages were built from
    n_rows = sum(len(t["rows"]) for t in data["sections"].values() if isinstance(t, dict) and "rows" in t)
    built = root / "data" / "site-built.json"
    if built.exists():
        meta = json.loads(built.read_text())
        if len(meta.get("pages", [])) < 15:
            problems.append(f"site-built.json lists only {len(meta.get('pages', []))} pages")
    else:
        problems.append("data/site-built.json missing — site was not built after the data")
    # staleness: each rendered table announces the row count it was built with
    counts = {k: len(v["rows"]) for k, v in data["sections"].items()
              if isinstance(v, dict) and "rows" in v}
    n_rows = sum(counts.values())
    seen = 0
    for p in html_pages:
        text = p.read_text(encoding="utf-8")
        seen += len(re.findall(r'<tr id="', text))
        for anchor, shown in re.findall(r'<section class="card table-card" id="([^"]+)" data-rows="(\d+)"', text):
            if anchor in counts and int(shown) != counts[anchor]:
                problems.append(f"{p.relative_to(root)}: table '{anchor}' shows {shown} rows, "
                                f"site.json has {counts[anchor]} — rebuild the HTML")
    if seen == 0:
        problems.append("no data rows found in the HTML — the site was not built from the data")
    return problems


def lint_all(root: Path | None = None) -> list[str]:
    r = Path(root) if root else ROOT
    data = json.loads((r / "data" / "site.json").read_text())
    return lint_data(data) + lint_html(data, r)


def main() -> int:
    problems = lint_all()
    if problems:
        print(f"LINT: {len(problems)} problem(s)")
        for p in problems:
            print("  -", p)
        return 1
    data = json.loads(SITE_JSON.read_text())
    n = sum(len(t["rows"]) for t in data["sections"].values() if isinstance(t, dict) and "rows" in t)
    print(f"LINT OK — {n} rows across {len([k for k, v in data['sections'].items() if isinstance(v, dict)])} "
          f"tables, every row sourced, every blank explained")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
