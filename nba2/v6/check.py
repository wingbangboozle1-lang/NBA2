"""Gates over the v6 build. Fail-closed: a hard failure stops the render.

Every gate is a measurement: it returns how many rows it could test, how many passed, and
the rows that failed by name. A gate that cannot be evaluated reports ``skipped`` with a
reason and is **not** counted as a pass — the same contract ``nba2/v5/check.py`` uses.

Nothing here reads the network. A v6 gate that depended on a live endpoint could not be
reproduced by a reader, and an unreproducible gate is decoration.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import inventory as INV
from . import market_prior as MP
from . import player_coverage as PC
from . import results_coverage as RC
from .common import ROOT, SITE, V6

OFFICIAL_HOSTS = ("nba.com", "statsdmz.nba.com", "ak-static.cms.nba.com",
                  "cdn.nba.com", "official.nba.com")


def _g(gid: str, name: str, ok, tested: int, passed: int, detail: str,
       failures: list[str] | None = None, hard: bool = True) -> dict:
    return {"id": gid, "name": name, "ok": ok, "tested": tested, "passed": passed,
            "detail": detail, "failures": failures or [], "hard": hard}


# ------------------------------------------------------------------ K-03 gates
def gate_injury_urls(rels: list[dict]) -> dict:
    bad = [r["filename"] for r in rels if not INV.INJURY_URL_RE.match(r["url"])]
    return _g("G-V6-1", "every injury release in the inventory carries a well-formed "
                        "official CDN URL",
              not bad, len(rels), len(rels) - len(bad),
              f"{len(rels)} releases, {len(bad)} malformed", bad)


def gate_no_orphan_pdfs(rels: list[dict]) -> dict:
    in_inv = {r["filename"] for r in rels}
    on_disk = {p.name for p in INV.PDF_DIR.glob("Injury-Report_*.pdf")}
    orphans = sorted(on_disk - in_inv)
    return _g("G-V6-2", "every archived injury PDF is listed in the inventory",
              not orphans, len(on_disk), len(on_disk) - len(orphans),
              f"{len(on_disk)} PDFs on disk, {len(in_inv)} in the inventory", orphans)


def gate_pdf_digests(rels: list[dict]) -> dict:
    import hashlib
    tested = passed = 0
    bad = []
    for r in rels:
        if not r["bytes_stored"]:
            continue
        tested += 1
        p = ROOT / r["pdf_path"]
        d = hashlib.sha256(p.read_bytes()).hexdigest()
        if d == r["pdf_sha256"] and r["pdf_bytes"] == p.stat().st_size:
            passed += 1
        else:
            bad.append(f"{r['filename']}: recorded {r['pdf_sha256'][:12]}…, "
                       f"recomputed {d[:12]}…")
    # the manifest is a runner artefact; if it is present its digests must agree
    man = INV.maybe_load(INV.BINARY_MANIFEST)
    if man:
        for e in man.get("entries", []):
            if e.get("outcome") == "stored" and e.get("sha256"):
                rel = next((r for r in rels if r["url"] == e["url"]), None)
                if rel and rel["pdf_sha256"] and rel["pdf_sha256"] != e["sha256"]:
                    bad.append(f"{rel['filename']}: manifest digest disagrees with the "
                               "committed file")
    return _g("G-V6-3", "each archived PDF's sha256 and byte length recompute",
              not bad, tested, passed,
              f"{passed}/{tested} archived PDFs verified byte-for-byte", bad)


def gate_revision_stamps(rels: list[dict]) -> dict:
    bad = [r["filename"] for r in rels if not r.get("stamp_et") or not r.get("date")]
    return _g("G-V6-4", "every release's revision stamp parses out of its official filename",
              not bad, len(rels), len(rels) - len(bad),
              f"{len(rels)} releases, {len(bad)} unparseable stamps", bad)


# ------------------------------------------------------------------ K-04 gates
def gate_coverage_arithmetic(doc: dict) -> dict:
    bad = []
    for r in doc["rows"]:
        if r["n_finals_committed"] > r["n_scheduled"]:
            bad.append(f"{r['date']}: {r['n_finals_committed']} finals > "
                       f"{r['n_scheduled']} scheduled")
        if r["n_graded"] > r["n_finals_committed"]:
            bad.append(f"{r['date']}: {r['n_graded']} graded > "
                       f"{r['n_finals_committed']} finals")
        if r["n_missing_final"] + r["n_finals_committed"] != r["n_scheduled"]:
            bad.append(f"{r['date']}: missing+present != scheduled")
    return _g("G-V6-5", "result-feed coverage is arithmetically consistent per date",
              not bad, len(doc["rows"]), len(doc["rows"]) - len(bad),
              f"{len(doc['rows'])} dates, {sum(r['n_scheduled'] for r in doc['rows'])} games",
              bad)


def gate_quarter_sums(games: list[dict]) -> dict:
    tested = passed = 0
    bad = []
    for g in games:
        if g["away_pts"] is None:
            continue
        tested += 1
        v = g["quarter_verdict"]
        if v == "quarters sum to the final":
            passed += 1
        elif v == "no quarter rows committed":
            passed += 1          # an explained blank is a pass, never a silent zero
        else:
            bad.append(f"{g['game_id']} {g['matchup']}: {v} — {g['quarter_detail']}")
    return _g("G-V6-6", "every committed final either has quarter rows that sum to it, or "
                        "says why the quarters are blank",
              not bad, tested, passed,
              f"{passed}/{tested} finals reconcile (quarters or an explained blank)", bad)


def gate_no_score_conflicts(games: list[dict]) -> dict:
    bad = [f"{g['game_id']}: {g['conflicts']}" for g in games if g.get("conflicts")]
    tested = sum(1 for g in games if g["away_pts"] is not None)
    return _g("G-V6-7", "no two committed official feeds disagree about a final score",
              not bad, tested, tested - len(bad),
              f"{tested} finals cross-read against every committed feed", bad)


def gate_coverage_sources(games: list[dict]) -> dict:
    bad = []
    for g in games:
        urls = [u for u in (g.get("source_url"), g.get("gamebook_url")) if u]
        if not urls:
            bad.append(f"{g['game_id']}: no official URL at all")
            continue
        if not any(h in u for u in urls for h in OFFICIAL_HOSTS):
            bad.append(f"{g['game_id']}: no nba.com host among {urls}")
    return _g("G-V6-8", "every game row points at an official nba.com document",
              not bad, len(games), len(games) - len(bad),
              f"{len(games)} game rows, {len(bad)} without an official URL", bad)


# ------------------------------------------------------------------ K-05 gates
def gate_player_arithmetic(doc: dict) -> dict:
    bad = []
    if doc["n_matched"] + doc["n_unmatched"] != doc["n_report_rows"]:
        bad.append(f"{doc['n_matched']} matched + {doc['n_unmatched']} unmatched "
                   f"!= {doc['n_report_rows']} report rows")
    if doc["n_matched_with_minutes"] > doc["n_matched"]:
        bad.append("more matched players with minutes than matched players")
    if doc["coverage"] is not None and not (0.0 <= doc["coverage"] <= 1.0):
        bad.append(f"coverage {doc['coverage']} outside [0,1]")
    return _g("G-V6-9", "the injury-report / player-log join is arithmetically consistent",
              not bad, doc["n_report_rows"], doc["n_report_rows"] - len(bad),
              f"{doc['n_matched']}/{doc['n_report_rows']} named players have a committed "
              f"game log ({doc['coverage']})", bad)


def gate_player_sources(doc: dict) -> dict:
    rows = doc["matched"] + doc["unmatched"]
    bad = [f"{r['player']} ({r['team']})" for r in rows if not r.get("report_url")]
    return _g("G-V6-10", "every injury-report row in the join carries the official PDF it "
                         "was read from",
              not bad, len(rows), len(rows) - len(bad),
              f"{len(rows)} report rows, {len(bad)} unsourced", bad)


# ------------------------------------------------------------------ K-02 gates
def gate_market_prior(doc: dict) -> dict:
    """The weight must be blank, and the rule must behave — checked on a hypothetical model.

    The rule's behaviour is verified against a hypothetical model log-loss of 0.60, not
    against the measured one: the measured model currently shows no skill on the settled
    sample, and a skill share with a zero denominator is undefined by construction. Testing
    the rule on the degenerate case would be testing the wrong thing.
    """
    bad = []
    if doc["w_market"] is not None:
        bad.append("w_market is published, but no closing line exists in any committed "
                   "capture — a weight would have to be invented")
    if doc["market_log_loss"] is not None:
        bad.append("a market log-loss is published, but no market price was ever captured")
    tests = 0
    w = MP.weight(0.60, 0.60)
    tests += 1
    if w is None or abs(w - 0.5) > 1e-9:
        bad.append(f"equal inputs must give w=0.5, got {w}")
    lo, hi = MP.weight(0.60, 0.62), MP.weight(0.60, 0.68)
    tests += 1
    if lo is None or hi is None or not (lo > hi):
        bad.append("the weight is not monotone in the market's log-loss")
    tests += 1
    if MP.weight(0.60, 0.75) != 0.0:
        bad.append("a forecaster worse than a coin flip must receive zero weight")
    tests += 1
    if MP.weight(0.60, None) is not None or MP.weight(None, 0.60) is not None:
        bad.append("an unmeasured input must give an undefined weight, never a default")
    tests += 1
    if MP.weight(0.72, 0.72) is not None:
        bad.append("when neither forecaster beats a coin flip the share has no denominator "
                   "and must be None, not 0.5")
    return _g("G-V6-11", "the market-anchored prior is blank where it must be, and its rule "
                         "is deterministic and monotone",
              not bad, tests, tests - len(bad),
              f"w_market blank ({doc['w_market_reason'][:60]}…); rule verified on "
              f"{tests} cases", bad)


def gate_market_measurements(doc: dict) -> dict:
    bad = []
    for m in doc["measurements"]:
        if m["log_loss"] is None:
            bad.append(f"{m['id']}: no measured log-loss")
        if m["log_loss_baseline"] is None:
            bad.append(f"{m['id']}: no baseline to compare against")
        if m["log_loss"] is not None and m["log_loss_baseline"] is not None:
            want = round(m["log_loss_baseline"] - m["log_loss"], 4)
            if m["skill_vs_baseline"] != want:
                bad.append(f"{m['id']}: skill {m['skill_vs_baseline']} != {want}")
    # A model worse than a coin flip is a FINDING, not a build failure. Suppressing the
    # build because the number moved the wrong way is exactly how a research desk stops
    # being a research desk - so it is measured, printed and flagged (F-F5-08), never
    # gated away.
    worse = [m["id"] for m in doc["measurements"]
             if m["log_loss"] is not None and m["log_loss_baseline"] is not None
             and m["log_loss"] > m["log_loss_baseline"]]
    detail = (f"{len(doc['measurements'])} measured samples, {len(bad)} inconsistent")
    if worse:
        detail += ("; WORSE THAN A COIN FLIP on " + ", ".join(worse) +
                   " — published as flag F-F5-08, not suppressed")
    return _g("G-V6-12", "every published out-of-sample log-loss measurement is internally "
                         "consistent, and its sign is reported either way",
              not bad, len(doc["measurements"]), len(doc["measurements"]) - len(bad),
              detail, bad)


# --------------------------------------------------------------- page gates
def check_pages(pages: list[str]) -> dict:
    """Structural check on the emitted HTML: link, source and blank-reason hygiene."""
    import html as H
    ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
    CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
    TAG = re.compile(r"<[^>]+>")
    LOCAL = re.compile(r'(?:href|src)="([^"#][^"]*)"')
    BLANK_OK = re.compile(r"(FLAG-|F-[A-Z0-9-]+|needs |no source|blocked|BLOCKED|not filed|"
                          r"first in window|does not exist|unavailable|withheld|WITHHELD|"
                          r"no data|no official|not measured|not committed|not reached|"
                          r"never inferred|no quarter rows)")
    TABLE = re.compile(r"<table([^>]*)>(.*?)</table>", re.S)
    tested = passed = 0
    derived_tables = 0
    bad = []
    for name in pages:
        p = SITE / name
        if not p.exists():
            bad.append(f"{name}: not written")
            continue
        doc = p.read_text()
        for link in LOCAL.findall(doc):
            if link.startswith(("http://", "https://", "mailto:", "//", "data:")):
                continue
            if not (SITE / link.split("?")[0]).exists():
                bad.append(f"{name}: broken local link -> {link}")
        for tm in TABLE.finditer(doc):
            attrs, tbody = tm.group(1), tm.group(2)
            is_derived = 'data-derived="1"' in attrs
            if is_derived:
                derived_tables += 1
                if "<caption>" not in tbody:
                    bad.append(f"{name}: a data-derived table carries no caption saying "
                               "what it is")
            for m in ROW.finditer(tbody):
                cells = CELL.findall(m.group(1))
                if not cells:
                    continue
                tested += 1
                row = m.group(1)
                joined = " ".join(H.unescape(TAG.sub("", c)).strip() for c in cells)
                if not is_derived and not re.search(r'href="https?://', row):
                    bad.append(f"{name}: row with no source link -> {joined[:80]!r}")
                    continue
                for c in cells:
                    t = H.unescape(TAG.sub("", c)).strip()
                    if t in ("", "None", "nan", "NaN"):
                        if not BLANK_OK.search(joined):
                            bad.append(f"{name}: blank cell with no reason -> {joined[:80]!r}")
                            break
                else:
                    passed += 1
                    continue
    return _g("G-V6-13", "every v6 table row carries an official source link, and every "
                         "blank carries a reason",
              not bad, tested, passed,
              f"{passed}/{tested} rows clean; {derived_tables} table(s) explicitly marked "
              "data-derived (arithmetic on a stated rule, captioned as such)", bad)


# ---------------------------------------------------------------------- runner
def run(pages: list[str] | None = None) -> dict:
    rels = INV.injury_releases()
    cov = RC.build()
    pc = PC.build()
    mp = MP.build()
    gates = [
        gate_injury_urls(rels),
        gate_no_orphan_pdfs(rels),
        gate_pdf_digests(rels),
        gate_revision_stamps(rels),
        gate_coverage_arithmetic(cov),
        gate_quarter_sums(cov["games"]),
        gate_no_score_conflicts(cov["games"]),
        gate_coverage_sources(cov["games"]),
        gate_player_arithmetic(pc),
        gate_player_sources(pc),
        gate_market_prior(mp),
        gate_market_measurements(mp),
    ]
    if pages:
        gates.append(check_pages(pages))
    hard_fail = [g for g in gates if g["hard"] and not g["ok"]]
    return {
        "schema": "nba2.v6.checks.v1",
        "session": "arena/f5ac4e74-nba2",
        "n_gates": len(gates),
        "n_gates_pass": sum(1 for g in gates if g["ok"]),
        "n_gates_fail": len(hard_fail),
        "publishable": not hard_fail,
        "gates": gates,
        "counts": {
            "injury_releases": len(rels),
            "injury_releases_with_bytes": sum(1 for r in rels if r["bytes_stored"]),
            "injury_releases_with_transcript": sum(1 for r in rels if r["transcripts"]),
            "games_known": cov["n_games_known"],
            "games_with_final": cov["n_games_with_final"],
            "games_graded": cov["n_games_graded"],
            "report_rows": pc["n_report_rows"],
            "players_matched": pc["n_matched"],
        },
    }
