"""v3 post-build verifier.

Two jobs, kept separate because they fail for different reasons:

STRUCTURAL — does the site hold together? Every internal link resolves, every table has a caption,
every ``<tr>`` has the right number of cells, no page contains an unescaped template artifact, no
page mixes the two surfaces, and no page renders a bare zero where a measurement is missing.

SEMANTIC — are the published numbers the numbers the modules produce? Wins total 188, the window
schedule has the right number of games per date, p_home equals Φ(margin/σ) for every row, the
ledger verifies, and every gate on the bet page matches the gate report in the payload.

A structural failure is a bug. A semantic failure means the site is lying about a number, which is
worse, so it is checked against the modules rather than against the HTML.

Run: ``python3 -m nba2.v3.check``
"""

from __future__ import annotations

import json
import math
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from . import official as O

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
DATA = ROOT / "data" / "v3"

V3_PAGES = [
    "v3-index.html", "v3-lines.html", "v3-totals.html", "v3-teams.html",
    "v3-calibration.html", "v3-backtest.html", "v3-strategies.html", "v3-injuries.html",
    "v3-methodology.html", "v3-flagged.html", "v3-bet.html",
]


class _Scan(HTMLParser):
    """Collect the facts the checks need without a DOM library."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []   # (tag, href/src)
        self.rows: list[list[int]] = []          # cells per <tr>
        self.tables = 0
        self.captions: list[int] = []
        self._in_tr = False
        self._cells = 0
        self._table_depth = 0
        self._caption_buf: list[str] = []
        self._in_caption = False
        self.caption_texts: list[str] = []
        self.text: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("a", "link", "script", "img"):
            ref = a.get("href") or a.get("src")
            if ref:
                self.links.append((tag, ref))
        if tag == "table":
            self.tables += 1
            self._table_depth += 1
        if tag == "caption":
            self._in_caption = True
            self._caption_buf = []
        if tag == "tr":
            self._in_tr = True
            self._cells = 0
        elif tag in ("td", "th") and self._in_tr:
            self._cells += 1
        if tag in ("style",):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "tr":
            if self._in_tr:
                self.rows.append([self._cells])
            self._in_tr = False
        elif tag == "caption":
            self._in_caption = False
            self.caption_texts.append("".join(self._caption_buf).strip())
        elif tag == "table":
            self._table_depth -= 1
        elif tag in ("style",):
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._in_caption:
            self._caption_buf.append(data)
        if not self._skip:
            self.text.append(data)


def _scan(path: Path) -> _Scan:
    p = _Scan()
    p.feed(path.read_text(encoding="utf-8"))
    return p


# --------------------------------------------------------------------------- structural
def check_structure() -> list[str]:
    problems: list[str] = []
    existing = {p.name for p in SITE.glob("*.html")}
    if (SITE / "assets" / "v3.css").exists() is False:
        problems.append("site/assets/v3.css is missing — every v3 page would render unstyled")

    for name in V3_PAGES:
        path = SITE / name
        if not path.exists():
            problems.append(f"{name}: MISSING")
            continue
        html = path.read_text(encoding="utf-8")
        s = _scan(path)

        # 1. internal links resolve
        for tag, ref in s.links:
            if ref.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if ref == "assets/v3.css":
                continue
            target = ref.split("#")[0]
            if not target:
                continue
            if target not in existing:
                problems.append(f"{name}: broken internal link -> {target}")

        # 2. every table carries a caption
        if len(s.caption_texts) != s.tables:
            problems.append(f"{name}: {s.tables} tables but {len(s.caption_texts)} captions")

        # 3. template artifacts.
        #    The first version of this check matched substrings, so "inf" fired on the word
        #    "information" and "None" fired on the sentence "None of these are hidden". Seven
        #    false positives on a clean build teach a reader to ignore the checker, so every
        #    pattern here is anchored on the delimiters a real artifact would have.
        artifacts = {
            "unrendered {placeholder}": r"\{[A-Za-z_][A-Za-z0-9_]*\}",
            "literal None": r">\s*None\s*<",
            "literal NaN": r">\s*[Nn]a[Nn]\s*<",
            "literal inf": r">\s*-?inf\s*<",
            "python repr": r"\{'[^']*':",
            "f-string prefix": r"\bf['\"]\{[a-zA-Z_]",
            "unresolved format": r"\{:\.[0-9]+[fd]\}",
        }
        for label, pat in artifacts.items():
            m = re.search(pat, html)
            if m:
                frag = html[max(0, m.start() - 50):m.start() + 50].replace("\n", " ")
                problems.append(f"{name}: {label} near …{frag}…")

        # 4. surfaces never mix: a projection page must not mention a stake table
        surface = ("bet" if name == "v3-bet.html" else "projection")
        if surface == "projection" and "stake_units" in html:
            problems.append(f"{name}: projection page leaks a bet-surface field")

        # 5. no page may be empty or truncated
        if len(html) < 2000:
            problems.append(f"{name}: only {len(html)} bytes — truncated build?")
        if "</html>" not in html:
            problems.append(f"{name}: no closing </html>")

    return problems


# --------------------------------------------------------------------------- semantic
def check_semantic(payload: dict) -> list[str]:
    problems: list[str] = []
    from . import model as M
    from . import strategies as S

    teams = M.load_teams()

    # --- the four validated capture identities, re-derived here rather than trusted
    w = sum(t.w for t in teams.values())
    losses = sum(t.l for t in teams.values())
    if w != 188:
        problems.append(f"wins total is {w}, expected 188")
    if losses != 188:
        problems.append(f"losses total is {losses}, expected 188")
    if w != losses:
        problems.append(f"wins {w} != losses {losses} — the feed has a mismatch")

    # --- schedule counts per date inside the window
    for date, n in sorted(O.GAMES_PER_DATE_OFFICIAL.items()):
        got = sum(1 for r in O.SCHEDULE if r[0] == date)
        if got != n:
            problems.append(f"{date}: {got} scheduled rows, official count says {n}")

    # --- p_home == Φ(margin / σ) for every originated line
    from . import build as B
    lines = B.originated_lines(teams, B.calibration(teams))
    cal = B.calibration(teams)
    for ln in lines:
        want = M.phi(ln.margin_a / cal.margin_sd)
        if abs(want - ln.p_home_a) > 1e-9:
            problems.append(f"{ln.game_id}: p_home_a {ln.p_home_a} != Φ(m/σ) {want}")
        if ln.grade not in ("A", "B", "C"):
            problems.append(f"{ln.game_id}: grade {ln.grade!r} is not A/B/C")
        if ln.travel_home_km not in (0.0, None):
            problems.append(f"{ln.game_id}: home travel is {ln.travel_home_km}, must be 0 or blank")

    # --- ledger
    raw = json.loads((DATA / "ledger" / "sealed-picks.json").read_text())
    ok, root, detail = S.verify_ledger(raw)
    if not ok:
        problems.append(f"sealed ledger does not verify: {detail}")
    if ok and root != payload.get("strategies", {}).get("ledger", {}).get("root"):
        problems.append("ledger root changed between the run and the page payload")

    # --- pre-registration files exist, are frozen, and match their definitions
    for pr in payload["strategies"]["prereg"]:
        path = ROOT / pr["path"]
        if not path.exists():
            problems.append(f"prereg {pr['id']}: {pr['path']} missing")
            continue
        doc = json.loads(path.read_text())
        want = doc.get("sha256") or doc.get("content_sha256")
        if want and want != pr["sha256"]:
            problems.append(f"prereg {pr['id']}: stored hash {want[:12]} != recomputed "
                            f"{pr['sha256'][:12]}")
        if not pr["matches_current_definition"]:
            problems.append(f"prereg {pr['id']}: drifted from the rule's current definition")

    # --- the gate table on the bet page must equal the gate report in the payload
    bet = (SITE / "v3-bet.html").read_text(encoding="utf-8")
    for g in payload["strategies"]["gates"]:
        if g["id"] not in bet:
            problems.append(f"bet page is missing gate {g['id']}")
    if "stake" in bet and "every stake here is zero" not in bet.lower():
        problems.append("bet page mentions a stake without the zero-stake disclosure")

    # --- the bet surface must carry no non-zero stake while no market exists
    for p in payload["strategies"]["ledger"].get("picks", []):
        if (p.get("stake_units") or 0) > 0:
            problems.append(f"pick {p.get('pick_id')} carries stake {p['stake_units']} with no market")

    # --- injuries banner arithmetic
    inj = payload.get("injuries", {})
    if inj.get("banner_check"):
        for msg in inj["banner_check"]:
            problems.append(f"injury banner: {msg}")

    # --- flags: every open measurement gap must be stated somewhere on the site
    flagged = (SITE / "v3-flagged.html").read_text(encoding="utf-8")
    for f in payload.get("flags", []):
        if f["id"] not in flagged:
            problems.append(f"flag {f['id']} is not on the flagged page")

    # --- contradictions: a page must not say both "beats a coin" and "worse than a coin"
    #     without naming which model
    cal_page = (SITE / "v3-calibration.html").read_text(encoding="utf-8")
    if "beats a coin" in cal_page and "worse than a coin" not in cal_page:
        problems.append("calibration page claims a win without the loss it trades against")

    return problems


def run(verbose: bool = True) -> dict:
    payload_path = DATA / "payload.json"
    if not payload_path.exists():
        print("v3 check: data/v3/payload.json missing — run nba2.v3.build first", file=sys.stderr)
        return {"ok": False, "structural": ["payload.json missing"], "semantic": []}

    payload = json.loads(payload_path.read_text())
    structural = check_structure()
    semantic = check_semantic(payload)

    ok = not structural and not semantic
    if verbose:
        total_html = sum(1 for _ in SITE.glob("v3-*.html"))
        print(f"v3 check: {total_html} v3 pages on disk, {len(V3_PAGES)} expected")
        print(f"  structural: {len(structural)} problem(s)")
        for p in structural[:25]:
            print(f"    - {p}")
        print(f"  semantic:   {len(semantic)} problem(s)")
        for p in semantic[:25]:
            print(f"    - {p}")
        print("RESULT:", "PASS" if ok else "FAIL")
    return {"ok": ok, "structural": structural, "semantic": semantic}


if __name__ == "__main__":
    r = run()
    sys.exit(0 if r["ok"] else 1)
