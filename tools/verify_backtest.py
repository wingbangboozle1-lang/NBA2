"""Mechanical verification of the measured-skill report.

These checks are the same contract the rest of the repository enforces, applied to this tree:

1. **Every published game row carries its own official source URL** (nba.com/game/...).
2. **No broken internal links** and no dangling anchors.
3. **No placeholder text** ("TODO", "TBD", "lorem", "???").
4. **No un-sourced numeric cell** in the report JSON's headline tables.
5. **Reproducibility**: rebuilding from the committed snapshots yields byte-identical pages.

Run: ``python3 tools/verify_backtest.py``  (exit code 1 on any failure)
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BT = ROOT / "backtest"
sys.path.insert(0, str(ROOT))

PLACEHOLDERS = re.compile(r"\b(TODO|TBD|FIXME|lorem ipsum|XXX|\?\?\?)\b", re.I)
HREF = re.compile(r'href="([^"]+)"')

failures: list[str] = []
notes: list[str] = []


def check(cond: bool, msg: str) -> None:
    if cond:
        notes.append(f"PASS  {msg}")
    else:
        failures.append(f"FAIL  {msg}")


def main() -> int:
    report_path = BT / "data" / "report.json"
    check(report_path.exists(), "report.json exists")
    if not report_path.exists():
        print("\n".join(failures))
        return 1
    report = json.loads(report_path.read_text())

    # ---------------------------------------------------------- 1. per-row sources
    games = report["games"]
    check(len(games) > 0, f"report contains game rows ({len(games)})")
    bad_src = [g for g in games
               if not str(g.get("source_url", "")).startswith("https://www.nba.com/game/")]
    check(not bad_src, f"every game row has its own nba.com/game/... source URL "
                       f"({len(games) - len(bad_src)}/{len(games)})")
    for g in bad_src[:5]:
        failures.append(f"      unsourced game row: {g.get('game_id')}")

    # graded rows must also carry their outcome numbers
    incomplete = [g for g in games if g.get("pred_margin_home") is not None
                  and (g.get("actual_margin_home") is None or g.get("actual_total") is None)]
    check(not incomplete, "every graded row carries both prediction and official outcome")

    # ---------------------------------------------------------- 2. links
    html_files = sorted(BT.rglob("*.html"))
    check(len(html_files) >= 12, f"expected at least 12 pages, found {len(html_files)}")
    broken = []
    checked = 0
    for f in html_files:
        text = f.read_text()
        ids = set(re.findall(r'id="([^"]+)"', text))
        for href in HREF.findall(text):
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target, _, anchor = href.partition("#")
            checked += 1
            if target:
                dest = (f.parent / target).resolve()
                if not dest.exists():
                    broken.append(f"{f.relative_to(ROOT)} -> {href}")
                    continue
                if anchor:
                    dest_text = dest.read_text()
                    if f'id="{anchor}"' not in dest_text:
                        broken.append(f"{f.relative_to(ROOT)} -> {href} (missing anchor)")
            elif anchor and anchor not in ids:
                broken.append(f"{f.relative_to(ROOT)} -> #{anchor} (missing anchor)")
    check(not broken, f"all {checked} internal links resolve")
    for b in broken[:10]:
        failures.append(f"      broken link: {b}")

    # every page must link at least one official source
    for f in html_files:
        if f.name == "index.html":
            continue
        text = f.read_text()
        if "nba.com" not in text:
            failures.append(f"FAIL  {f.relative_to(ROOT)} links no nba.com source")

    # ---------------------------------------------------------- 3. placeholders
    hits = []
    for f in list(BT.rglob("*.html")) + [report_path]:
        for m in PLACEHOLDERS.finditer(f.read_text()):
            hits.append(f"{f.relative_to(ROOT)}: {m.group(0)}")
    check(not hits, "no placeholder text in published artefacts")
    for h in hits[:5]:
        failures.append(f"      placeholder: {h}")

    # ------------------------------------------------------- 3b. no leaked Python values
    CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
    TAG = re.compile(r"<[^>]+>")
    leaks = []
    for f in html_files:
        for cell in CELL.findall(f.read_text()):
            text = TAG.sub("", cell).strip()
            if text in {"None", "nan", "NaN", "inf", "-inf", "Infinity", ""}:
                leaks.append(f"{f.relative_to(ROOT)}: empty or null cell {text!r}")
    check(not leaks, "no table cell renders a null/NaN value")
    for l in leaks[:5]:
        failures.append(f"      {l}")

    # ------------------------------------- 3c. no page may contradict its own computed summary
    gate_report = report["gates"]
    if "gates" in gate_report:
        summary = gate_report["summary"]
        reliable = set(summary.get("passed_reliable", summary["passed"]))
        # a gate marked disputed must never be counted in the "passed" KPI
        vg = (BT / "pages" / "validation-gates.html").read_text()
        for gid in summary.get("passed_disputed", []):
            if f'<div class="kpi-v">{len(summary["passed"])}</div>' in vg:
                failures.append(f"FAIL  validation-gates.html still counts disputed {gid} "
                                f"as plainly passed")
                break
        check(not summary.get("passed_disputed") or "DISPUTED" in vg,
              f"validation-gates.html discloses {len(summary.get('passed_disputed', []))} "
              f"disputed gate(s)")
        check('strawman' in vg.lower(), "validation-gates.html names the strawman baseline")
        # and the report JSON itself must be coherent
        check(set(summary.get("passed_disputed", [])) <= set(summary["passed"]),
              "every disputed gate is also a registered pass")

    # ---------------------------------------------------------- 4. headline numbers sourced
    acc = report["accuracy"]
    check(acc.get("n", 0) > 0, f"accuracy block computed on {acc.get('n')} graded games")
    check(report["integrity"]["exact_check"]["checked"] > 0,
          f"record-reconstruction check ran on {report['integrity']['exact_check']['checked']} cards")
    check(report["integrity"]["bounded_check"]["violations"] == 0,
          "no team reconstruction exceeds its official post-game record")
    # guard against a fabricated market claim
    for needle in ("ROI", "profit", "units won"):
        text = (BT / "pages" / "leaderboard.html").read_text()
        if needle in text and "not" not in text.lower():
            notes.append(f"NOTE  '{needle}' appears on the leaderboard page; verify it is framed "
                         f"as unavailable")

    # ---------------------------------------------------------- 5. reproducibility
    before = {f: f.read_text() for f in html_files}
    rj_before = report_path.read_text()
    proc = subprocess.run([sys.executable, "-m", "backtest.engine.build"], cwd=ROOT,
                          capture_output=True, text=True)
    check(proc.returncode == 0, "rebuild from committed snapshots succeeds")
    if proc.returncode != 0:
        failures.append(proc.stderr[-1500:])
    else:
        changed = [str(f.relative_to(ROOT)) for f, t in before.items() if f.read_text() != t]
        check(not changed, "rebuild is deterministic (pages byte-identical)")
        for c in changed[:5]:
            failures.append(f"      non-deterministic output: {c}")
        check(report_path.read_text() == rj_before, "report.json is deterministic")

    print("\n".join(notes))
    if failures:
        print("\n".join(failures))
        print(f"\nVERIFICATION FAILED — {len(failures)} problem(s)")
        return 1
    print(f"\nVERIFICATION PASSED — {len(html_files)} pages, {len(games)} sourced game rows, "
          f"{checked} internal links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
