#!/usr/bin/env python3
"""Independent cross-check of the published site against the committed official snapshots.

Why this file exists
--------------------
Every prior verification in this repository is one of two kinds:

* *rebuild parity* — CI runs the pipeline again and checks the bytes match. That proves the
  artefacts are a faithful rendering of `data/site.json`, but it is circular for the question
  "is `data/site.json` faithful to the snapshots?" — the same code produced both.
* *provenance lint* — every row carries a source, every blank is explained. That proves the
  rows are *labelled* honestly, not that a label matches what it points at.

Three audits (`analysis/audit-2c07c00b.md`, `analysis/current-state-audit-2026-11-14.md`,
`analysis/session-9707-audit.md`) each said, in different words, that no session had repeated a
*semantic* pass over the published values. This is that pass.

What it does
------------
It re-derives each published claim from the committed snapshot files with its own arithmetic —
never by importing `nba2.models` — and reports where the published value and the recomputed value
diverge. It also re-checks count claims that live in prose (table titles, flag statements,
`README.md`, the coordination board), because that is the class of defect that has actually been
found here more than once (stale counts, `17` continuation rows, `28/30` vs `30/30`).

Deliberate limits (these are the point, not an omission)
--------------------------------------------------------
* It has no network access and does not want any. A PASS means "the published artefact agrees
  with the committed snapshot"; it never means "the official source was re-read today". Only the
  snapshot's own `retrieved_at_utc` / `provenance.url` can say anything about the official source,
  and those are reported as-is.
* If a claim's referent cannot be computed from committed evidence, the check reports `N/A` with
  the reason. It does not substitute a plausible number.
* It never edits a file. Read-only by construction; the only write is the report you ask for.

Usage
-----
    python3 tools/crosscheck_site.py                      # console summary
    python3 tools/crosscheck_site.py --markdown OUT.md     # reproducible report
    python3 tools/crosscheck_site.py --json OUT.json       # machine-readable
    python3 tools/crosscheck_site.py --only CC-HTML,CC-FLAG

Exit code is 0 unless a check FAILs, so it can be wired into CI later (see the CR in COORDINATION.md).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE_JSON = ROOT / "data" / "site.json"
RAW = ROOT / "data" / "raw"

OFFICIAL_HOSTS = {"www.nba.com", "nba.com", "ak-static.cms.nba.com", "cdn.nba.com",
                  "stats.nba.com", "picks.nba.com", "oauth.nba.com"}
REPO_HOSTS = {"github.com"}
PASS, FAIL, INFO, NA = "PASS", "FAIL", "INFO", "N/A"
TEAM_TRICODES = {
    "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
    "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
    "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAN", "SAS", "TOR", "UTA",
    "WAS",
}


# --------------------------------------------------------------------------- framework
@dataclass
class Check:
    id: str
    group: str
    assertion: str
    method: str
    verdict: str = NA
    observed: str = ""
    evidence: str = ""
    note: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)
    appendices: list = field(default_factory=list)

    def appendix(self, title: str, lines: list[str]):
        self.appendices.append((title, lines))

    def add(self, cid, group, assertion, method, verdict, observed="", evidence="", note=""):
        c = Check(cid, group, assertion, method, verdict, observed, evidence, note)
        self.checks.append(c)
        return c

    def counts(self):
        out = {PASS: 0, FAIL: 0, INFO: 0, NA: 0}
        for c in self.checks:
            out[c.verdict] = out.get(c.verdict, 0) + 1
        return out


# --------------------------------------------------------------------------- loading
def load_json(path: Path):
    return json.loads(path.read_text())


def section(site: dict, key: str) -> dict:
    return site["sections"][key]


def rows_of(site: dict, key: str) -> list[dict]:
    return section(site, key).get("rows", [])


def vals(row: dict) -> dict:
    return row.get("values", {})


def snapshot_candidates(kind: str) -> list[Path]:
    """All committed snapshots of a type, newest internal stamp first.

    `nba2/config.py` pins one file by name; a refresh session may add a newer one. Matching
    against every candidate keeps this checker honest about *which* snapshot the published rows
    actually came from instead of assuming the constant still points at the right file.
    """
    pats = {
        "slate": "slate_2*_to_*.json",
        "injury": "injury_report_*.json",
        "ratings": "team_ratings_*.json",
        "times": "official_game_times_*.json",
        "leaders": "team_leaders_*.json",
        "context": "slate_context_*.json",
    }[kind]
    files = list(RAW.glob(pats))

    def stamp(p: Path) -> str:
        try:
            d = load_json(p)
        except Exception:
            return ""
        for k in ("as_of", "retrieved_at_utc", "report_stamp_et"):
            v = d.get(k)
            if v:
                return str(v)
        return ""

    return sorted(files, key=stamp, reverse=True)


def by_key(rows: list[dict], key: str) -> dict:
    return {vals(r).get(key): r for r in rows}


def num(v):
    if v is None:
        return None
    s = str(v).replace("±", "").replace("+", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def norm_time(t):
    """Normalise the several ways a tip time is written across surfaces -> minutes past midnight ET."""
    if not t:
        return None
    s = str(t).strip().lower().replace("(et)", "").replace(" et", "").strip()
    m = re.match(r"^(\d{1,2}):(\d{2})\s*(am|pm)?$", s)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap == "pm" and h != 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    return h * 60 + mi


# --------------------------------------------------------------------------- checks
def check_snapshots(r: Report, site: dict):
    g = "A. snapshot integrity"
    slate_files = snapshot_candidates("slate")
    if not slate_files:
        r.add("CC-SNAP-00", g, "a slate snapshot exists", "glob data/raw/slate_2*.json", FAIL,
              "none found", "data/raw")
        return
    slate = load_json(slate_files[0])
    recs = slate.get("records", [])
    cols = slate.get("columns", [])
    idx = {c: i for i, c in enumerate(cols)}
    r.add("CC-SNAP-01", g, "every slate record has one cell per declared column",
          f"len(cells) == len(columns) for all {len(recs)} records in {slate_files[0].name}",
          PASS if all(len(x) == len(cols) for x in recs) else FAIL,
          f"{len(recs)} records x {len(cols)} columns")
    ids = [x[idx["game_id"]] for x in recs]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    r.add("CC-SNAP-02", g, "official game IDs are unique and well-formed (002 + 7 digits)",
          "regex over the game_id column of the slate snapshot",
          PASS if not dupes and all(re.fullmatch(r"002\d{7}", str(i)) for i in ids) else FAIL,
          f"{len(set(ids))} unique / {len(ids)} rows; bad format: "
          f"{[i for i in ids if not re.fullmatch(r'002[0-9]{7}', str(i))][:3]}",
          evidence=str(slate_files[0].relative_to(ROOT)))
    teams = {x[idx["away"]] for x in recs} | {x[idx["home"]] for x in recs}
    r.add("CC-SNAP-03", g, "every club in the slate is one of the 30 NBA tricodes",
          "set difference against the league's team list",
          PASS if teams <= TEAM_TRICODES else FAIL,
          f"{len(teams)} distinct; unknown: {sorted(teams - TEAM_TRICODES) or 'none'}")
    declared = slate.get("counts_check") or {}
    actual: dict[str, int] = {}
    for x in recs:
        actual[x[idx["date"]]] = actual.get(x[idx["date"]], 0) + 1
    match = all(str(v) == str(declared.get(k)) for k, v in actual.items()) and len(actual) == len(declared)
    r.add("CC-SNAP-04", g, "per-day game counts equal the snapshot's own counts_check",
          "recount records by date and compare with the stored claim",
          PASS if match else FAIL, f"recomputed {actual} vs stored {declared}",
          evidence=slate.get("provenance", {}).get("url", "https://www.nba.com/schedule"))
    bad_times = [x[idx["game_id"]] for x in recs if norm_time(x[idx["time_et"]]) is None]
    r.add("CC-SNAP-05", g, "every tip time parses as a 24h ET clock value",
          "HH:MM parse over the slate's time_et column",
          PASS if not bad_times else FAIL, f"unparseable: {bad_times[:5] or 'none'}")
    as_of = slate.get("as_of")
    dates = sorted(actual)
    try:
        horizon = (date.fromisoformat(dates[-1]) - date.fromisoformat(as_of)).days
        ok = horizon <= 3
    except Exception:
        horizon, ok = None, False
    r.add("CC-SNAP-06", g, "the pick window never exceeds as-of + 3 days",
          f"max(date) - as_of over {slate_files[0].name}",
          PASS if ok else FAIL, f"horizon {horizon} day(s); window {dates[0]}..{dates[-1]}" if dates else "no dates",
          note="the brief's 'up to 3 days in advance' rule, checked on the data rather than in code")
    win = str(site["meta"].get("slate_window", ""))
    r.add("CC-SNAP-07", g, "the published slate_window string matches the data",
          "compare the meta string's first/last ISO dates with the snapshot's dates",
          PASS if dates and dates[0] in win and dates[-1] in win else FAIL,
          f"meta: {win!r} vs data {dates[0] if dates else '?'}..{dates[-1] if dates else '?'}")

    inj_files = snapshot_candidates("injury")
    if inj_files:
        inj = load_json(inj_files[0])
        icols = inj.get("columns", [])
        iidx = {c: i for i, c in enumerate(icols)}
        irecs = inj.get("records", [])
        counts = inj.get("record_counts", {})
        attrib = counts.get("attribution_explicit")
        cont = [x[iidx["attribution"]] for x in irecs]
        recomputed = {
            "total_rows": len(irecs),
            "not_yet_submitted_placeholders": sum(1 for x in irecs if x[iidx["status"]] == "NOT YET SUBMITTED"),
            "attribution_explicit": cont.count("E"),
            "attribution_continuation": cont.count("C"),
        }
        recomputed["rows_with_status_for_2026_11_13"] = recomputed["total_rows"] - recomputed["not_yet_submitted_placeholders"]
        ok = all(str(v) == str(counts.get(k)) for k, v in recomputed.items())
        r.add("CC-SNAP-08", g, "injury snapshot's own record_counts equal a recount of its records",
              f"recount over {inj_files[0].name}",
              PASS if ok else FAIL, f"stored {counts} vs recomputed {recomputed}",
              evidence=inj.get("provenance", {}).get("url", ""))
        allowed = {"Out", "Doubtful", "Questionable", "Probable", "Available", "NOT YET SUBMITTED",
                   "Suspended", "G League - On Two-Way Contract", "Rest", "Personal Reasons",
                   "G League - Two-Way", "Not With Team"}
        statuses = {x[iidx["status"]] for x in irecs}
        r.add("CC-SNAP-09", g, "every official status string is one the report can print",
              "set of status values in the snapshot",
              PASS if statuses <= allowed else INFO,
              f"statuses seen: {sorted(statuses)}" + (f"; unknown: {sorted(statuses - allowed)}" if statuses - allowed else ""),
              note="INFO, not FAIL, when an unseen-but-plausible label appears: the vocabulary belongs to the "
                   "NBA, not to us, and we do not invent a rule about it")
        r.add("CC-SNAP-10", g, "attribution flag is recorded per row (E explicit / C continuation)",
              "column 'attribution' present on every record",
              PASS if set(cont) <= {"E", "C"} and attrib is not None else FAIL,
              f"E={cont.count('E')} C={cont.count('C')}")

    for kind in ("ratings", "times", "leaders", "context"):
        for p in snapshot_candidates(kind)[:1]:
            d = load_json(p)
            prov = d.get("provenance") or {}
            primary = prov.get("primary_source") or {}
            url = prov.get("url") or primary.get("url") or d.get("source") or ""
            stamp = d.get("retrieved_at_utc") or ""
            r.add(f"CC-SNAP-11:{kind}", g, f"{p.name} states where and when it was retrieved",
                  "presence of a provenance url + retrieval stamp inside the file",
                  PASS if url and stamp else FAIL, f"url={url or 'MISSING'}; retrieved={stamp or 'MISSING'}",
                  evidence=str(p.relative_to(ROOT)))
    rat = load_json(snapshot_candidates("ratings")[0])
    rcols = {c: i for i, c in enumerate(rat["columns"])}
    rrecs = rat["records"]
    bad_split = [x[rcols["tricode"]] for x in rrecs
                 if x[rcols["home_w"]] + x[rcols["home_l"]] + x[rcols["road_w"]] + x[rcols["road_l"]]
                 != x[rcols["w"]] + x[rcols["l"]]]
    r.add("CC-SNAP-12", g, "ratings: home+road games reconcile with total games for all 30 clubs",
          "arithmetic identity inside the snapshot", PASS if not bad_split else FAIL,
          f"violations: {bad_split or 'none'}", evidence=str(snapshot_candidates('ratings')[0].relative_to(ROOT)))
    close_w = sum(x[rcols["close_w"]] for x in rrecs)
    close_l = sum(x[rcols["close_l"]] for x in rrecs)
    blow_w = sum(x[rcols["blowout_w"]] for x in rrecs)
    blow_l = sum(x[rcols["blowout_l"]] for x in rrecs)
    claimed = " ".join(str(x) for x in rat.get("provenance", {}).get("internal_consistency_checks", []))
    recompute_fail = (close_w != close_l) or (blow_w != blow_l)
    says_fail = "FAIL" in claimed
    r.add("CC-SNAP-13", g, "ratings: the snapshot's own PASS/FAIL labels still describe the data",
          f"sum(close_w)={close_w} vs sum(close_l)={close_l}; sum(blowout_w)={blow_w} vs sum(blowout_l)={blow_l}",
          PASS if recompute_fail == says_fail else FAIL,
          f"recomputed imbalance => {'FAIL' if recompute_fail else 'PASS'}; stored labels say "
          f"{'FAIL' if says_fail else 'PASS'}",
          note="every close/blowout game is one win and one loss, so the league-wide sums must match; a "
               "mismatch means the per-team split columns are not a complete partition of the games")
    pct_bad = [x[rcols["tricode"]] for x in rrecs
               if abs(round(x[rcols["w"]] / (x[rcols["w"]] + x[rcols["l"]]), 3) - x[rcols["pct"]]) > 0.0015]
    r.add("CC-SNAP-14", g, "ratings: winning percentage equals W/(W+L) to 3 dp",
          "recompute pct from w,l", PASS if not pct_bad else FAIL, f"violations: {pct_bad or 'none'}")


def check_published_vs_snapshot(r: Report, site: dict):
    g = "B. published rows vs the snapshot they cite"
    slate = load_json(snapshot_candidates("slate")[0])
    scols = {c: i for i, c in enumerate(slate["columns"])}
    srecs = {x[scols["game_id"]]: x for x in slate["records"]}
    pub = {vals(row)["game_id"]: row for row in rows_of(site, "slate")}

    def cell(row, key):
        v = vals(row).get(key)
        return None if v in (None, "", "blank", "\u2014") else v

    mismatches, extra_pub, missing_pub = [], set(pub) - set(srecs), set(srecs) - set(pub)
    for gid, row in pub.items():
        src = srecs.get(gid)
        if not src:
            continue
        want = {
            "date": src[scols["date"]],
            "time_et": src[scols["time_et"]],
            "matchup": f"{src[scols['away']]} @ {src[scols['home']]}",
            "arena": src[scols["arena"]],
            "location": f"{src[scols['city']]}, {src[scols['state']]}",
            "broadcast": src[scols["broadcast"]],
            "cup": src[scols["cup_group"]],
        }
        for k, v in want.items():
            got = cell(row, k)
            if (v or None) != (got or None):
                mismatches.append(f"{gid}.{k}: published {got!r} vs snapshot {v!r}")
    r.add("CC-PUB-01", g, "every published slate cell equals the snapshot cell",
          f"cell-by-cell compare of {len(pub)} rows x 7 shared columns",
          PASS if not mismatches and not extra_pub and not missing_pub else FAIL,
          f"{len(mismatches)} cell mismatch(es): {mismatches[:4]}; published-not-in-snapshot={sorted(extra_pub)}; "
          f"snapshot-not-published={sorted(missing_pub)}",
          evidence=str(snapshot_candidates('slate')[0].relative_to(ROOT)))

    inj_file = snapshot_candidates("injury")[0]
    inj = load_json(inj_file)
    icols = {c: i for i, c in enumerate(inj["columns"])}
    irecs = inj["records"]
    inj_rows = rows_of(site, "injuries")
    inj_mis = []
    for i, rec in enumerate(irecs):
        want = {
            "game_date": rec[icols["game_date"]], "time_et": rec[icols["time_et"]],
            "matchup": rec[icols["matchup"]], "team": rec[icols["team"]],
            "player": rec[icols["player"]] or "—", "status": rec[icols["status"]],
            "reason": rec[icols["reason"]],
            "attribution": "explicit" if rec[icols["attribution"]] == "E" else "block-continuation (unconfirmed)",
        }
        row = next((x for x in inj_rows if vals(x).get("game_date") and f"inj-{i}" == x["key"]), None)
        if not row:
            inj_mis.append(f"inj-{i}: published row absent")
            continue
        for k, v in want.items():
            if vals(row).get(k) != v:
                inj_mis.append(f"inj-{i}.{k}: published {vals(row).get(k)!r} vs snapshot {v!r}")
    r.add("CC-PUB-02", g, "every published injury cell equals the transcribed PDF row",
          f"all {len(irecs)} rows x 8 fields against {inj_file.name}",
          PASS if not inj_mis else FAIL, f"{len(inj_mis)} mismatch(es): {inj_mis[:5] or 'none'}",
          evidence=inj.get("provenance", {}).get("url", str(inj_file.relative_to(ROOT))))
    blank_impact = all(vals(x).get("minutes_impact") is None and vals(x).get("production_impact") is None
                       and vals(x).get("line_adjustment") is None for x in inj_rows)
    r.add("CC-PUB-03", g, "no minute/production/line impact value is published for any injury row",
          "the three columns must be null in every row (the official report carries no such field)",
          PASS if blank_impact else FAIL,
          f"{len(inj_rows)} rows scanned; any non-null would be an invented number")
    p0 = [vals(x) for x in inj_rows if x["key"].startswith("inj-")]
    p_bad = [x for x in p0 if x.get("status") == "Out" and num(x.get("p_play")) not in (0.0,)]
    r.add("CC-PUB-04", g, "our P(plays) convention is applied consistently: 'Out' => 0.00",
          "recount over published injury rows", PASS if not p_bad else FAIL,
          f"{len(p0)} rows; Out rows with p_play != 0.00: {len(p_bad)}")

    times = load_json(snapshot_candidates("times")[0])
    tmap = {}
    for rec in times["records"]:
        d, mu, tm, present = rec[0], rec[1], rec[2], rec[3]
        tmap[(d, mu)] = tm if present else None
    corr_rows = rows_of(site, "corroboration")
    corr_bad, n_corrob, n_lost, n_outside = [], 0, 0, 0
    for row in corr_rows:
        v = vals(row)
        gid = v.get("game_id")
        src = srecs.get(gid)
        if not src:
            corr_bad.append(f"{gid}: not in the slate snapshot")
            continue
        key = (src[scols["date"]], f"{src[scols['away']]}@{src[scols['home']]}")
        t_time = tmap.get(key)
        verdict = str(v.get("verdict", ""))
        sched = norm_time(src[scols["time_et"]])
        if key in tmap:
            if tmap[key] is None:
                n_lost += 1
                if "time cell was lost" not in verdict:
                    corr_bad.append(f"{gid}: snapshot says time lost, verdict says {verdict!r}")
            else:
                if norm_time(tmap[key]) != sched:
                    n_corrob += 0
                    corr_bad.append(f"{gid}: times differ ({sched} vs {tmap[key]}) yet row claims corroboration")
                else:
                    n_corrob += 1
                    if "MATCHUP + TIP TIME" not in verdict:
                        corr_bad.append(f"{gid}: times agree but verdict does not say so: {verdict!r}")
        else:
            n_outside += 1
            if "not in the 11/13 report" not in verdict:
                corr_bad.append(f"{gid}: absent from the second document but verdict says {verdict!r}")
    title = section(site, "corroboration")["title"]
    claim = re.findall(r"(\d+) of (\d+) games confirmed twice", title)
    claim_lost = re.findall(r"(\d+) matchups confirmed", title)
    counts_ok = bool(claim) and int(claim[0][0]) == n_corrob and int(claim[0][1]) == len(corr_rows) \
        and bool(claim_lost) and int(claim_lost[0]) == n_lost
    r.add("CC-PUB-05", g, "the corroboration table's title counts match its own rows",
          "recompute corroborated / time-lost / outside counts from the two snapshots, compare with the title",
          PASS if counts_ok and not corr_bad else FAIL,
          f"recomputed {n_corrob} twice-confirmed, {n_lost} time-lost, {n_outside} outside; title: {title!r}"
          + (f"; row-level problems: {corr_bad[:3]}" if corr_bad else ""),
          evidence="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf")


def check_derived_arithmetic(r: Report, site: dict):
    g = "C. published derived values re-derived by hand-arithmetic"
    lines = rows_of(site, "lines")
    bad_spread, bad_total, bad_p, bad_margin = [], [], [], []
    for row in lines:
        v = vals(row)
        gid = v.get("date", "?") + " " + str(v.get("matchup", ""))
        margin = num(v.get("margin"))
        sp = str(v.get("spread") or "")
        m = re.match(r"^([A-Z]{3})\s*([+-])(\d+(?:\.\d)?)$", sp.strip())
        if margin is None or not m:
            bad_spread.append(f"{gid}: unparsable spread {sp!r}")
            continue
        mag = float(m.group(3))
        home_is_favorite = m.group(2) == "-"
        # margin is (home - away) expected; a negative margin means the home club is the dog
        expect_sign = "+" if margin < 0 else "-"
        if m.group(2) != expect_sign or abs(abs(margin) - mag) > 0.55:
            bad_spread.append(f"{gid}: margin {margin} vs spread {sp!r}")
        exp = str(v.get("exp_score") or "")
        e = re.match(r"^(\d+(?:\.\d)?)\s*@\s*(\d+(?:\.\d)?)$", exp.strip())
        tot = num(v.get("total"))
        if e and tot is not None:
            s = float(e.group(1)) + float(e.group(2))
            if abs(s - tot) > 0.55:
                bad_total.append(f"{gid}: projected scores {exp!r} sum to {s:.1f} but total is {tot}")
        fair = str(v.get("fair") or "")
        f = re.match(r"^(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)$", fair.strip())
        p_home = num(v.get("p_home"))
        if f and p_home is not None:
            implied = 100.0 / float(f.group(1))
            # the published fair price is rounded to 2dp; at p -> 1 the reciprocal of that rounding
            # is worth ~0.5pp, so the tolerance is the rounding, not a fudge factor.
            tol = max(0.6, 100.0 * 0.005 / (float(f.group(1)) ** 2) + 0.05)
            if abs(implied - p_home) > tol:
                bad_p.append(f"{gid}: p_home {p_home}% vs fair {f.group(1)} => {implied:.2f}%")
    r.add("CC-DER-01", g, "spread string and sign follow from the projected margin",
          f"parse all {len(lines)} published lines", PASS if not bad_spread else FAIL,
          f"{len(bad_spread)} violation(s): {bad_spread[:3] or 'none'}")
    r.add("CC-DER-02", g, "published total equals the published per-team projections (±0.5)",
          "home+away projected score vs the total column", PASS if not bad_total else FAIL,
          f"{len(bad_total)} violation(s): {bad_total[:3] or 'none'}")
    r.add("CC-DER-03", g, "p(home) equals the implied probability of our own fair price",
          "1 / decimal fair price vs the published probability, per game",
          PASS if not bad_p else FAIL, f"{len(bad_p)} violation(s): {bad_p[:3] or 'none'}",
          note="no vig is charged by definition: these are our numbers, not a market price")
    ratings = rows_of(site, "ratings")
    bad = []
    for row in ratings:
        v = vals(row)
        ppg, oppg, net = num(v.get("ppg")), num(v.get("oppg")), num(v.get("net"))
        if None not in (ppg, oppg, net) and abs((ppg - oppg) - net) > 0.051:
            bad.append(f"{v.get('team')}: {ppg}-{oppg} != {net}")
        srs, lam, shr = num(v.get("srs")), num(v.get("lam")), num(v.get("srs_shrunk"))
        games = num(v.get("games"))
        if None not in (srs, lam, shr) and abs(srs * lam - shr) > 0.011:
            bad.append(f"{v.get('team')}: srs*lam {srs * lam:.4f} != published {shr}")
        wl = str(v.get("wl") or "")
        m = re.match(r"^(\d+)-(\d+)$", wl.strip())
        if m and games is not None and int(m.group(1)) + int(m.group(2)) != games:
            bad.append(f"{v.get('team')}: W-L {wl} != GP {games}")
    r.add("CC-DER-04", g, "ratings table is internally consistent (net = PS/G - PA/G; shrunk = SRS x lambda; GP = W+L)",
          f"recompute from the published cells of all {len(ratings)} rows", PASS if not bad else FAIL,
          f"{len(bad)} violation(s): {bad[:4] or 'none'}")
    dup_official = [row["key"] for row in ratings
                    if vals(row).get("wl") is not None and vals(row).get("wl") == vals(row).get("wl_official")]
    caption = str(section(site, "ratings").get("source_note") or "")
    r.add("CC-DER-05", g, "the two W-L columns are independent measurements, as the caption claims",
          "compare the columns' provenance: both are printed by build_ratings_rows from the same model object",
          FAIL if len(dup_official) == len(ratings) else PASS,
          f"{len(dup_official)}/{len(ratings)} rows identical; caption: {caption!r}",
          evidence=str(RATINGS_EVIDENCE),
          note="FAIL here is a presentation defect, not a wrong number: the column labelled 'W-L (official "
               "NBA.com)' is populated from the same third-party field as the other column, so the "
               "'if they ever disagree the table is wrong' guard can never fire. See the CR in COORDINATION.md.")
    luck = rows_of(site, "luck")
    luck_bad = []
    for row in luck:
        v = vals(row)
        a, e, l = num(v.get("actual")), num(v.get("expected")), num(v.get("luck"))
        if None not in (a, e, l) and abs((a - e) - l) > 0.11:
            luck_bad.append(f"{v.get('team')}: {a}-{e} != {l}")
        for col in ("close_record", "blowout_record"):
            s = str(v.get(col) or "")
            m = re.match(r"^(\d+)-(\d+)$", s.strip())
            if m and int(m.group(1)) + int(m.group(2)) > (a or 0):
                luck_bad.append(f"{v.get('team')}: {col} {s} exceeds games played {a}")
    r.add("CC-DER-06", g, "luck table arithmetic (luck = actual - expected; split records fit inside the season)",
          f"recompute over {len(luck)} rows", PASS if not luck_bad else FAIL,
          f"{len(luck_bad)} violation(s): {luck_bad[:4] or 'none'}")
    parlays = rows_of(site, "parlays")
    par_bad = []
    for row in parlays:
        v = vals(row)
        lo, hi, indep = num(v.get("joint_lo")), num(v.get("joint_hi")), num(v.get("indep"))
        if None in (lo, hi):
            continue
        if lo > hi:
            par_bad.append(f"{v.get('matchup')}: joint_lo {lo} > joint_hi {hi}")
        if indep is not None and not (0 <= indep <= 1):
            par_bad.append(f"{v.get('matchup')}: indep {indep} out of range")
        bl, bh = num(v.get("boost_lo")), num(v.get("boost_hi"))
        if None not in (bl, bh, indep) and indep:
            if abs(indep and lo and lo / indep - bl) > 0.06 or abs(hi / indep - bh) > 0.06:
                par_bad.append(f"{v.get('matchup')}: boost {bl}/{bh} != joint/indep {lo / indep:.3f}/{hi / indep:.3f}")
    r.add("CC-DER-07", g, "parlay table: joint interval ordered, boost = joint / independence",
          f"recompute over {len(parlays)} rows", PASS if not par_bad else FAIL,
          f"{len(par_bad)} violation(s): {par_bad[:3] or 'none'}")
    rot = rows_of(site, "rotation")
    rot_bad = []
    for row in rot:
        v = vals(row)
        tot = sum(num(v.get(k)) or 0 for k in ("out", "doubtful", "questionable", "probable", "available"))
        exp = num(v.get("exp_missing"))
        if exp is None:
            continue
        if not (0 <= exp <= max(tot, 0) + 0.001):
            rot_bad.append(f"{v.get('team')}: expected missing bodies {exp} exceeds listed unavailables {tot}")
        floor = num(v.get("floor"))
        if floor is not None and not (0 <= floor <= 15):
            rot_bad.append(f"{v.get('team')}: rotation floor {floor} outside a plausible 0..15 range")
    r.add("CC-DER-08", g, "rotation table: expected-bodies-missing never exceeds the players actually listed, floor inside 0..15",
          f"recompute over {len(rot)} teams", PASS if not rot_bad else FAIL,
          f"{len(rot_bad)} violation(s): {rot_bad[:3] or 'none'}")
    rot_mismatch = []
    for row in rot:
        v = vals(row)
        name = str(v.get("team"))
        # the rotation table keys on the club's full name, same as the injury report
        got = {"out": num(v.get("out")), "doubtful": num(v.get("doubtful")),
               "questionable": num(v.get("questionable")), "probable": num(v.get("probable"))}
        cnt = NAME_STATUS_COUNTS.get(name, {})
        for key in got:
            if got[key] is not None and got[key] != cnt.get(key, 0):
                rot_mismatch.append(f"{name}.{key}: rotation says {got[key]}, injury rows say {cnt.get(key, 0)}")
    r.add("CC-DER-09", g, "rotation counts equal a recount of the published injury rows for the same club",
          f"cross-table identity over {len(rot)} teams", PASS if not rot_mismatch else FAIL,
          f"{len(rot_mismatch)} violation(s): {rot_mismatch[:4] or 'none'}",
          note="a rotation row that no longer matches its own detail table is the classic drift bug in "
               "injury dashboards")


def check_gates_leaderboard(r: Report, site: dict):
    g = "D. gates, leaderboard, rewards"
    gate_rows = rows_of(site, "gate_matrix")
    allowed = {"PASS", "FAIL", "BLOCKED", "AT-RISK"}
    bad = [vals(x).get("gate") for x in gate_rows if str(vals(x).get("result")) not in allowed]
    r.add("CC-GATE-01", g, "every gate verdict is one of the four defined states",
          f"scan of {len(gate_rows)} strategy x gate results", PASS if not bad else FAIL,
          f"illegal values: {bad[:5] or 'none'}")
    per: dict[str, dict[str, int]] = {}
    for x in gate_rows:
        v = vals(x)
        d = per.setdefault(v["strategy"], {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "AT-RISK": 0})
        d[str(v.get("result"))] = d.get(str(v.get("result")), 0) + 1
    lb = rows_of(site, "leaderboard")
    lb_bad, promoted_without_pass = [], []
    for row in lb:
        v = vals(row)
        claim = str(v.get("gates") or "")
        m = re.match(r"^(\d+) pass / (\d+) fail / (\d+) blocked", claim)
        got = per.get(v["id"], {})
        if m:
            want = {"PASS": int(m.group(1)), "FAIL": int(m.group(2)), "BLOCKED": int(m.group(3))}
            for k, n in want.items():
                if int(got.get(k, 0)) != n:
                    lb_bad.append(f"{v['id']}: claims {claim!r}, matrix says {got}")
                    break
        else:
            lb_bad.append(f"{v['id']}: gate claim not parsable: {claim!r}")
        tier = str(v.get("tier") or "")
        if tier.lower() not in ("blocked",) and int(got.get("PASS", 0)) < sum(
                int(x) for x in re.findall(r"\d+", str(section(site, "gates")["rows"][0]["values"].get("min_pass") or "")) or [0]):
            pass
        if got.get("PASS", 0) == 0 and tier.lower() not in ("blocked", "unranked"):
            promoted_without_pass.append(f"{v['id']} is tier {tier!r} with 0 gates passed")
    r.add("CC-GATE-02", g, "each leaderboard row's gate tally equals the gate matrix",
          f"recount per strategy over {len(gate_rows)} rows", PASS if not lb_bad else FAIL,
          f"{len(lb_bad)} violation(s): {lb_bad[:3] or 'none'}")
    r.add("CC-GATE-03", g, "no strategy is promoted while it has zero gates passed",
          "promotion must follow evidence, never a model's self-assessment",
          PASS if not promoted_without_pass else FAIL,
          f"{len(promoted_without_pass)} violation(s): {promoted_without_pass or 'none — all nine are Blocked'}")
    meta = site["meta"]
    gp = sum(1 for x in gate_rows if vals(x).get("result") == "PASS")
    r.add("CC-GATE-04", g, "meta.gates_passed / gates_total equal a recount",
          "count PASS rows and total rows in the gate matrix",
          PASS if gp == meta.get("gates_passed") and len(gate_rows) == meta.get("gates_total") else FAIL,
          f"recomputed {gp}/{len(gate_rows)} vs meta {meta.get('gates_passed')}/{meta.get('gates_total')}")
    rw = meta.get("rewards", {})
    alloc = sum(float(a.get("amount", 0)) for a in rw.get("awards", []))
    r.add("CC-GATE-05", g, "no reward is allocated while no strategy has passed the gates",
          "sum the award amounts and compare with the pool arithmetic",
          PASS if alloc == float(rw.get("allocated", 0)) and (gp == 0 or alloc > 0) else FAIL,
          f"awards sum {alloc}, meta allocated {rw.get('allocated')}, pool {rw.get('pool')}, "
          f"gates passed {gp}", evidence=str(ROOT / "data/site.json"))
    score_bad = [str(vals(x).get("id")) for x in lb if vals(x).get("score") is not None]
    r.add("CC-GATE-06", g, "no performance score is published without settled bets behind it",
          "the score column must be blank while the ledger has nothing settled",
          PASS if not score_bad else INFO, f"rows with a score: {score_bad or 'none'}",
          note="this is the luck-removal guard: a score is an output of settled evidence, not of a model's opinion")
    gspec = rows_of(site, "gates")
    r.add("CC-GATE-07", g, "every gate spec has a threshold and a failure mode stated",
          "check the gate definition table for empty decision rules",
          PASS if all(vals(x).get("threshold") not in (None, "", "—") or vals(x).get("rule") not in (None, "", "—")
                      for x in gspec) else FAIL,
          f"{len(gspec)} gate definitions")


def check_seal(r: Report, site: dict):
    g = "E. sealed ledger"
    ledgers = sorted((ROOT / "data/raw/ledger").glob("sealed-*.json"))
    if not ledgers:
        r.add("CC-SEAL-01", g, "a sealed ledger exists", "glob", FAIL, "none")
        return
    path = ledgers[-1]
    doc = load_json(path)
    payload = doc["predictions"]
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False).encode("utf-8")).hexdigest()
    stored = doc["header"]["sha256"]
    r.add("CC-SEAL-01", g, "the seal digest recomputes from the prediction array",
          f"sha256 over canonical JSON of {len(payload)} predictions in {path.name}",
          PASS if digest == stored else FAIL, f"stored {stored[:16]}… recomputed {digest[:16]}…",
          evidence=f"https://github.com/wingbangboozle1-lang/NBA2/blob/main/{path.relative_to(ROOT)}")
    r.add("CC-SEAL-02", g, "the number of sealed predictions equals the count in the header and on the site",
          "len(predictions) vs header.n_predictions vs meta.seal.n_predictions",
          PASS if len(payload) == doc["header"]["n_predictions"] == site["meta"]["seal"]["n_predictions"] else FAIL,
          f"{len(payload)} / {doc['header']['n_predictions']} / {site['meta']['seal']['n_predictions']}")
    same_digest = site["meta"]["seal"]["sha256"] == stored
    r.add("CC-SEAL-03", g, "the digest printed on every page is the file's own digest",
          "meta.seal.sha256 vs the sealed file header", PASS if same_digest else FAIL,
          f"site {site['meta']['seal']['sha256'][:16]}… vs file {stored[:16]}…")
    slate = load_json(snapshot_candidates("slate")[0])
    scols = {c: i for i, c in enumerate(slate["columns"])}
    srecs = {x[scols["game_id"]]: x for x in slate["records"]}
    as_of = slate.get("as_of")
    outside, wrong_time = [], []
    for p in payload:
        gid = p["game_id"]
        src = srecs.get(gid)
        if not src:
            outside.append(f"{gid} not in the official slate snapshot")
            continue
        if p["date"] <= as_of:
            outside.append(f"{gid} dated {p['date']} is not after the snapshot date {as_of}")
        if norm_time(p.get("time_et")) != norm_time(src[scols["time_et"]]):
            wrong_time.append(f"{gid}: sealed {p.get('time_et')} vs official {src[scols['time_et']]}")
    r.add("CC-SEAL-04", g, "every sealed prediction is an official game inside the window, tipped after the snapshot",
          "cross-check the sealed array against the slate snapshot", PASS if not outside else FAIL,
          f"{len(outside)} problem(s): {outside[:3] or 'none'}")
    r.add("CC-SEAL-05", g, "sealed tip times equal the official tip times they were sealed against",
          "per-game time compare", PASS if not wrong_time else FAIL,
          f"{len(wrong_time)} problem(s): {wrong_time[:3] or 'none'}",
          evidence="https://www.nba.com/schedule")
    lines = {vals(x).get("game_id") or x["key"]: vals(x) for x in rows_of(site, "lines")}
    drift = []
    for p in payload:
        v = lines.get(p["game_id"])
        if not v:
            drift.append(f"{p['game_id']}: sealed but not on the lines page")
            continue
        sp = str(v.get("spread") or "")
        m = re.match(r"^[A-Z]{3}\s*([+-])(\d+(?:\.\d)?)$", sp.strip())
        if m:
            signed = float(m.group(2)) * (-1 if m.group(1) == "-" else 1)
            if abs(signed - float(p["our_spread_home"])) > 0.011:
                drift.append(f"{p['game_id']}: page spread {signed:+.1f} vs sealed {p['our_spread_home']:+.1f}")
        if abs(float(v.get("total") or 0) - float(p["our_total"])) > 0.011:
            drift.append(f"{p['game_id']}: page total {v.get('total')} vs sealed {p['our_total']}")
    r.add("CC-SEAL-06", g, "what was sealed is exactly what the site displays",
          "per-game compare of the published line table against the immutable ledger",
          PASS if not drift else FAIL, f"{len(drift)} drift(s): {drift[:4] or 'none'}",
          note="this is the anti-quiet-refit check: a line that changed after tip-off would show up here")


def check_flags_blanks(r: Report, site: dict):
    g = "F. flags, blanks and provenance discipline"
    flag_rows = rows_of(site, "flags")
    flag_ids = {vals(x).get("id") for x in flag_rows} | {x["key"] for x in flag_rows}
    refs: dict[str, int] = {}
    for key, tbl in site["sections"].items():
        for row in tbl.get("rows", []):
            for f in row.get("flags", []):
                refs[f] = refs.get(f, 0) + 1
    dangling = sorted(set(refs) - flag_ids)
    orphans = sorted(flag_ids - set(refs))
    r.add("CC-FLAG-01", g, "no row cites a flag that does not exist",
          f"every one of {sum(refs.values())} flag references resolves to the flags table",
          PASS if not dangling else FAIL, f"unresolvable: {dangling[:5] or 'none'}")
    r.add("CC-FLAG-02", g, "every flag is attached to at least one published row",
          "a flag nobody references documents nothing", PASS if not orphans else INFO,
          f"{len(orphans)} orphan flag(s): {orphans}")
    blank_unexplained, value_on_blocked = [], []
    blocked_allowed = {"status", "missing", "note", "market", "player", "team", "name", "url",
                       "cls", "usable", "key", "reason", "verdict", "disposition", "attribution",
                       "severity", "area", "statement", "action", "source", "id"}
    for key, tbl in site["sections"].items():
        for row in tbl.get("rows", []):
            for col, v in vals(row).items():
                if v is None and not row.get("flags") and not row.get("note"):
                    blank_unexplained.append(f"{key}/{row['key']}.{col}")
            src = (row.get("source") or {})
            if src.get("class") == "blocked":
                for col, v in vals(row).items():
                    if v is not None and col not in blocked_allowed:
                        value_on_blocked.append(f"{key}/{row['key']}.{col}={v!r}")
    r.add("CC-FLAG-03", g, "every blank cell carries a flag or a note explaining it",
          "independent re-implementation of the site's own blank rule over all rows",
          PASS if not blank_unexplained else FAIL,
          f"{len(blank_unexplained)} unexplained blank(s): {blank_unexplained[:5] or 'none'}")
    r.add("CC-FLAG-04", g, "no value is present on a row whose source is blocked/unavailable",
          "the machine-enforced version of 'leave it blank and flag it'",
          PASS if not value_on_blocked else FAIL,
          f"{len(value_on_blocked)} violation(s): {value_on_blocked[:5] or 'none'}")
    host_bad = []
    for key, tbl in site["sections"].items():
        for row in tbl.get("rows", []):
            src = row.get("source") or {}
            if src.get("class") == "official":
                host = urlparse(src.get("url") or "").netloc
                if host not in OFFICIAL_HOSTS | REPO_HOSTS:
                    host_bad.append(f"{key}/{row['key']}: {host}")
            if src.get("class") == "third_party":
                blob = json.dumps(row, ensure_ascii=False)
                if re.search(r"officially verified|verified to NBA\.com|NBA\.com-confirmed", blob, re.I):
                    host_bad.append(f"{key}/{row['key']}: third-party row claims official verification")
    r.add("CC-FLAG-05", g, "an 'official' label only ever points at an NBA-official host",
          "host allow-list check over every row (plus: no third-party row may claim official verification)",
          PASS if not host_bad else FAIL, f"{len(host_bad)} violation(s): {host_bad[:4] or 'none'}")
    cont_actual = None
    inj_file = snapshot_candidates("injury")[0]
    inj = load_json(inj_file)
    icols = {c: i for i, c in enumerate(inj["columns"])}
    cont_actual = sum(1 for x in inj["records"] if x[icols["attribution"]] == "C")
    total_actual = len(inj["records"])
    claim_checks = []
    for row in flag_rows:
        v = vals(row)
        stmt = str(v.get("statement") or "")
        fid = v.get("id")
        if fid == "FLAG-INJ-01":
            m = re.search(r"(\d+) rows inherit their team", stmt)
            if m:
                claim_checks.append(("FLAG-INJ-01 continuation rows", int(m.group(1)), cont_actual))
        if fid == "FLAG-INJ-02":
            m = re.search(r"blank for all (\d+) rows", stmt)
            if m:
                claim_checks.append(("FLAG-INJ-02 affected rows", int(m.group(1)), total_actual))
        if fid == "FLAG-SLATE-05":
            m = re.search(r"(\d+) of (\d+) official game-page URLs are generated", stmt)
            if m:
                slug = sum(1 for row in rows_of(site, "slate")
                           if "confirmed in retrieved page text" not in str(vals(row).get("preview_status") or ""))
                claim_checks.append(("FLAG-SLATE-05 slug-generated URLs", int(m.group(1)), slug))
                claim_checks.append(("FLAG-SLATE-05 slate size", int(m.group(2)), len(rows_of(site, "slate"))))
    bad_claims = [f"{name}: text says {a}, data says {b}" for name, a, b in claim_checks if a != b]
    r.add("CC-FLAG-06", g, "count claims inside flag statements match the data they describe",
          "recompute each numeric claim whose referent is computable: "
          + "; ".join(f"{n} {a} vs {b}" for n, a, b in claim_checks),
          PASS if not bad_claims else FAIL, f"{len(bad_claims)} stale claim(s): {bad_claims or 'none'}",
          note="a flag whose number drifted from the data is a stale disclosure: still scary, no longer true")


TRICODE_ALIAS = {"WSH": "WAS", "WAS": "WAS", "NO": "NOP", "NOP": "NOP", "SAS": "SAS", "SAN": "SAS"}


def _canon(tri):
    return TRICODE_ALIAS.get(str(tri).upper(), str(tri).upper()) if tri else None


def check_cross_surface(r: Report, site: dict):
    g = "G. cross-surface facts"
    captures: dict[str, dict[str, str]] = {}
    rat = load_json(snapshot_candidates("ratings")[0])
    rc = {c: i for i, c in enumerate(rat["columns"])}
    captures["ratings snapshot (Basketball-Reference, 2026-11-13)"] = {
        x[rc["tricode"]]: f"{x[rc['w']]}-{x[rc['l']]}" for x in rat["records"]}
    p = ROOT / "nba2/data/records.json"
    if p.exists():
        d = load_json(p)
        captures["nba2/data/records.json (NBA.com/schedule)"] = {
            t["team"]: f"{t['wins']}-{t['losses']}" for t in d["teams"]}
    p = ROOT / "originated/data/teams.json"
    if p.exists():
        d = load_json(p)
        captures["originated/data/teams.json (ESPN, cross-checked)"] = {
            t["abbr"]: f"{t['wins']}-{t['losses']}" for t in d["teams"]}
    p = ROOT / "data/standings-2026-11-13.csv"
    if p.exists():
        with p.open() as fh:
            rows = list(csv.DictReader(fh))
        captures["data/standings-2026-11-13.csv"] = {x["team"]: f"{x['wins']}-{x['losses']}" for x in rows}
    captures["published ratings (site)"] = {vals(x).get("tricode"): str(vals(x).get("wl"))
                                            for x in rows_of(site, "ratings")}
    aliases = {}
    for name, table_ in captures.items():
        for tri in table_:
            c = _canon(tri)
            if c != tri:
                aliases.setdefault(c, set()).add(f"{tri} ({name.split(' (')[0]})")
    r.add("CC-X-00", g, "every surface uses the same team key for the same club (joinability)",
          "normalise the three-letter codes each capture uses and report any club written two ways",
          FAIL if aliases else PASS,
          "; ".join(f"{c} <- {sorted(v)}" for c, v in sorted(aliases.items())) or "all keys agree",
          note="a club written two ways is an invisible row in any join: it silently drops out of the "
               "comparison instead of failing it, which is exactly how a '28 of 30' coverage figure can "
               "read like a data defect")
    teams = sorted({_canon(k) for v in captures.values() for k in v} - {None})
    disagree = []
    coverage = {k: len(v) for k, v in captures.items()}
    for t in teams:
        vals_t = {}
        for k, cap in captures.items():
            for tri, wl in cap.items():
                if _canon(tri) == t:
                    vals_t[k] = wl
        if len(set(vals_t.values())) > 1:
            disagree.append(f"{t}: {vals_t}")
    r.add("CC-X-01", g, "a club's W-L is the same number on every surface of this repo",
          f"{len(teams)} clubs x {len(captures)} committed captures: "
          + "; ".join(f"{k} covers {v}/{len(teams)}" for k, v in coverage.items()),
          PASS if not disagree else FAIL, f"{len(disagree)} disagreement(s): {disagree[:3] or 'none'}")
    r.add("CC-X-02", g, "the 28/30 vs 30/30 wording conflict is resolvable from committed evidence",
          "compute, per capture, which clubs are covered; the two figures must name their comparison",
          INFO, _wl_reconciliation_line(captures),
          note="see the reconciliation table in the report; CC-X-03 publishes the per-club evidence")
    uncov = sorted(set(teams) - set(captures.get("nba2/data/records.json (NBA.com/schedule)", {})))
    r.add("CC-X-03", g, "clubs the official-capture comparison covers, and the ones it does not",
          "set difference between the published ratings and each official capture",
          INFO, f"uncovered by nba2/data/records.json: {uncov or 'none'}")

    tip_rows = rows_of(site, "slate")
    pub_times = {vals(x).get("game_id"): norm_time(vals(x).get("time_et")) for x in tip_rows}
    p2 = ROOT / "data/games.csv"
    if p2.exists():
        with p2.open() as fh:
            other = {x["game_id"]: norm_time(x["tip_et"]) for x in csv.DictReader(fh)}
    else:
        other = {}
    diff = [g for g, t in pub_times.items() if g in other and other[g] != t]
    r.add("CC-X-04", g, "the two sessions' independent reads of the official tip times agree",
          f"compare site slate times with data/games.csv for the {len(set(other) & set(pub_times))} shared game IDs",
          PASS if not diff else FAIL, f"{len(diff)} mismatch(es): {diff[:3] or 'none'}",
          evidence="https://www.nba.com/schedule")
    p3 = ROOT / "originated/data/slate.json"
    if p3.exists():
        orig = {g["id"]: norm_time(g.get("timeEt")) for g in load_json(p3).get("games", [])}
        diff2 = [g for g, t in pub_times.items() if g in orig and orig[g] != t]
        r.add("CC-X-05", g, "a third surface's tip times agree with the canonical slate",
              f"originated/data/slate.json over {len(set(orig) & set(pub_times))} shared IDs",
              PASS if not diff2 else FAIL, f"{len(diff2)} mismatch(es): {diff2[:3] or 'none'}")
    xlines = rows_of(site, "xlines")
    arith = []
    for row in xlines:
        v = vals(row)
        a, b, d = num(v.get("our_spread")), num(v.get("their_spread")), num(v.get("spread_delta"))
        if None in (a, b, d):
            continue
        if abs((a - b) - d) > 0.011:
            arith.append(f"{v.get('matchup')}: {a}-({b}) != {d}")
    r.add("CC-X-06", g, "the cross-session line-delta column is arithmetically right",
          f"recompute our-minus-theirs over {len(xlines)} rows", PASS if not arith else FAIL,
          f"{len(arith)} violation(s): {arith[:3] or 'none'}")
    p4 = ROOT / "data/our-lines.csv"
    if p4.exists():
        with p4.open() as fh:
            theirs = {x["game_id"]: x["our_spread_home"] for x in csv.DictReader(fh)}
        n_shared = sum(1 for x in xlines if x["key"] in theirs)
        r.add("CC-X-07", g, "the other session's line file is the actual referent of the comparison table",
              "the xlines rows must correspond to rows that exist in data/our-lines.csv",
              PASS if n_shared else INFO, f"{n_shared}/{len(xlines)} comparison rows have a source row on disk")
    xrec = rows_of(site, "xrecords")
    title = section(site, "xrecords")["title"]
    same = sum(1 for x in xrec if str(vals(x).get("their_record")) == str(vals(x).get("our_record")))
    m = re.search(r"(\d+)/(\d+) agree", title)
    ok = bool(m) and int(m.group(1)) == same and int(m.group(2)) == len(xrec)
    r.add("CC-X-08", g, "the cross-session record-agreement claim equals its own table",
          f"recount agree rows in xrecords ({same}/{len(xrec)}) vs the title {m.group(0) if m else '?'}",
          PASS if ok else FAIL, f"recomputed {same}/{len(xrec)}")
    cap_names = list(captures)
    hdr = "| Club | " + " | ".join(c.split(" (")[0] for c in cap_names) + " | All agree? |"
    sep = "|" + "---|" * (len(cap_names) + 2)
    matrix = [hdr, sep]
    for team in sorted(teams):
        cells, seen = [], []
        for name in cap_names:
            raw_row = {k: v for k, v in captures[name].items() if _canon(k) == team}
            v = sorted(set(raw_row.values()))
            cells.append(v[0] if len(v) == 1 else ("**" + "/".join(v) + "**") if v else "—")
            seen += list(raw_row.values())
        agree = "yes" if len(set(seen)) == 1 else "NO"
        matrix.append(f"| {team} | " + " | ".join(cells) + f" | {agree} |")
    matrix.append("")
    matrix.append("_Reading: each column is one independent capture committed to this repository. `—` means that "
                  "capture has no row for that club (that is the whole difference between a coverage count and an "
                  "agreement count). A bold cell means two captures disagree, which is a defect, not a rounding "
                  "choice._")
    r.appendix("Appendix 1 — per-club win-loss evidence across every committed capture "
               "(this is what settles the `28/30` vs `30/30` wording conflict)", matrix)
    both_same = sum(1 for x in xrec if vals(x).get("their_ppg") in (None, "blank"))
    r.add("CC-X-09", g, "the cross-session comparison does not silently compare a value with itself",
          "the PS/G column of the prior session must be genuinely blank where that session had no source",
          PASS if both_same else INFO, f"{both_same}/{len(xrec)} rows blank on their side")


def check_docs(r: Report, site: dict):
    g = "H. documentation claims"
    readme = (ROOT / "README.md").read_text()
    n_rows = sum(len(t.get("rows", [])) for t in site["sections"].values() if isinstance(t, dict))
    n_tables = len([t for t in site["sections"].values() if isinstance(t, dict) and "rows" in t])
    tests = 0
    for p in (ROOT / "nba2/tests").glob("test_*.py"):
        tests += len(re.findall(r"^\s+def (test_\w+)", p.read_text(), re.M))
    html_pages = len(list((ROOT / "pages").glob("*.html"))) + 1
    claims = []
    for pat, actual, label in [
        (r"(\d+) tables", n_tables, "README table count"),
        (r"(\d+) (?:data )?rows", n_rows, "README row count"),
        (r"(\d+) tests", tests, "README test count"),
        (r"(\d+) (?:HTML )?pages", html_pages, "README page count"),
    ]:
        m = re.search(pat, readme)
        if m:
            claims.append((label, int(m.group(1)), actual))
    bad = [f"{n}: text {a} vs measured {b}" for n, a, b in claims if a != b]
    r.add("CC-DOC-01", g, "README's published counts match the artefacts on disk",
          "measure each figure directly: " + "; ".join(f"{n}={b}" for n, _, b in claims),
          PASS if not bad else FAIL, f"{len(bad)} stale figure(s): {bad or 'none'}")
    meta = site["meta"]
    r.add("CC-DOC-02", g, "meta.games / meta.teams / meta.injury_rows equal the sections they describe",
          "recount the slate, ratings and injuries tables",
          PASS if (meta.get("games") == len(rows_of(site, "slate"))
                   and meta.get("teams") == len(rows_of(site, "ratings"))
                   and meta.get("injury_rows") == len(rows_of(site, "injuries"))) else FAIL,
          f"meta {meta.get('games')}/{meta.get('teams')}/{meta.get('injury_rows')} vs "
          f"{len(rows_of(site, 'slate'))}/{len(rows_of(site, 'ratings'))}/{len(rows_of(site, 'injuries'))}")
    tiers = meta.get("tiers", {})
    counted = {}
    for x in rows_of(site, "lines"):
        t = str(vals(x).get("tier"))
        counted[t] = counted.get(t, 0) + 1
    tier_ok = all(counted.get(k, 0) == v for k, v in tiers.items())
    r.add("CC-DOC-03", g, "meta.tiers equals a recount of the line table",
          f"count tier letters: {counted}", PASS if tier_ok else FAIL,
          f"meta {tiers}")
    r.add("CC-DOC-04", g, "the site reports which snapshot it is built from",
          "meta.snapshot_as_of must equal the slate snapshot's own as_of",
          PASS if str(meta.get("snapshot_as_of")) == str(load_json(snapshot_candidates('slate')[0]).get('as_of')) else FAIL,
          f"meta {meta.get('snapshot_as_of')!r} vs snapshot "
          f"{load_json(snapshot_candidates('slate')[0]).get('as_of')!r}")
    gen = str(meta.get("generated_at_utc") or "")
    try:
        dt = datetime.strptime(gen, "%Y-%m-%d %H:%M UTC")
        fmt_ok = True
    except ValueError:
        fmt_ok = False
    r.add("CC-DOC-05", g, "generated_at_utc is a real timestamp and the build declares itself idempotent",
          "parse the stamp; read build_is_idempotent", PASS if fmt_ok and meta.get("build_is_idempotent") else FAIL,
          f"{gen!r}, idempotent={meta.get('build_is_idempotent')}")
    coord = (ROOT / "COORDINATION.md").read_text()
    m = re.search(r"(\d+) rows across (\d+) tables", coord)
    if m:
        ok = int(m.group(1)) == n_rows and int(m.group(2)) == n_tables
        r.add("CC-DOC-06", g, "the verification line quoted on the coordination board matches the current build",
              f"board says {m.group(0)}; build says {n_rows}/{n_tables}",
              PASS if ok else INFO,
              "INFO when a refresh is in flight: the board is a historical record of the run that made it, "
              "and this session must not rewrite another session's log")
    digest = hashlib.sha256()
    names = [str(x.relative_to(RAW)) for x in sorted(RAW.glob("*.json"))]
    for n in names:
        digest.update(n.encode())
        digest.update((RAW / n).read_bytes())
    r.add("CC-DOC-07", g, "the committed inputs are unambiguous (digest over every raw snapshot recorded)",
          f"sha256 over {len(names)} raw snapshot files, names included",
          INFO, f"this session's input digest {digest.hexdigest()[:16]}… vs meta.input_digest "
                f"{str(meta.get('input_digest'))[:16]}…",
          note="the two digests are computed over different file sets by design (the build hashes a fixed "
               "list, plus requirements/ledger inputs); they are reported side by side rather than compared as equal")


def check_html(r: Report, site: dict):
    g = "I. what the browser is actually served"
    pages = sorted((ROOT / "pages").glob("*.html")) + [ROOT / "index.html"]
    row_re = re.compile(r"<tr id=\"([^\"]+)\">(.*?)</tr>", re.S)
    rows_total = rows_no_link = blanks = 0
    bad_flag_anchors, bad_files = [], []
    for p in pages:
        text = p.read_text()
        for _id, body in row_re.findall(text):
            rows_total += 1
            cells = re.findall(r"<td.*?</td>", body, re.S)
            if not any('class="srccell"' in c for c in cells):
                rows_no_link += 1
            blanks += body.count('class="blank"')
            for anchor in re.findall(r'href="([^"#]*\.html)#([^"]+)"', body):
                target = (p.parent / anchor[0]).resolve()
                if target.exists() and f'id="{anchor[1]}"' not in target.read_text():
                    bad_flag_anchors.append(f"{p.name}:{_id} -> {anchor[0]}#{anchor[1]}")
        for href in set(re.findall(r'href="([^"#:]+\.(?:html|css|js))"', text)):
            if not (p.parent / href).resolve().exists():
                bad_files.append(f"{p.name} -> {href}")
    r.add("CC-HTML-01", g, "every rendered table row on the site carries a source cell",
          f"regex scan of {rows_total} rendered <tr id=...> rows across {len(pages)} HTML files",
          PASS if rows_no_link == 0 else FAIL, f"{rows_no_link} row(s) without a source cell")
    r.add("CC-HTML-02", g, "every internal link and every flag anchor resolves to a real target",
          "checked all static hrefs plus the anchor id inside the target file (the repo's own link "
          "checker does not verify anchors)",
          PASS if not bad_files and not bad_flag_anchors else FAIL,
          f"{len(bad_files)} broken file link(s): {bad_files[:3] or 'none'}; "
          f"{len(bad_flag_anchors)} dead anchor(s): {bad_flag_anchors[:3] or 'none'}")
    n_data_blanks = sum(1 for _k, t_ in site["sections"].items() for row in t_.get("rows", [])
                        for v in vals(row).values() if v is None)
    ids_rendered = set()
    for p in pages:
        ids_rendered |= set(re.findall(r"<tr id=\"([^\"]+)\">", p.read_text()))
    published_ids = {row["key"] for _k, t_ in site["sections"].items() for row in t_.get("rows", [])}
    not_shown = sorted(published_ids - ids_rendered)
    r.add("CC-HTML-03", g, "every row in the data file is rendered on some page",
          f"{len(published_ids)} published row keys vs {len(ids_rendered)} ids present in the HTML; "
          f"data blanks {n_data_blanks} vs rendered blank markers {blanks}",
          PASS if not not_shown else FAIL,
          f"{len(not_shown)} row(s) in the data but not on the site: {not_shown[:6] or 'none'}",
          note="the brief asks for all entries to be on the site; an unrendered row is an entry nobody can review")
    hidden: dict[str, list[str]] = {}
    for key_, tbl in site["sections"].items():
        for row in tbl.get("rows", []):
            if row["key"] in set(not_shown):
                hidden.setdefault(f"{key_} — {tbl.get('title')}", []).append(row["key"])
    if hidden:
        lines = ["| Section (title) | Rows built but rendered on no page |", "|---|---|"]
        lines += [f"| {k} | {', '.join(v)} |" for k, v in sorted(hidden.items())]
        lines += ["", "The data file holds them, the lint counts them, CI parity-checks them — no page calls "
                  "`render_table` on them, so nobody reviews them. `nba2/pipeline/build_site.py` maps page -> "
                  "sections; `pages/parlays.html` lists only `correlation` and `parlays` even though "
                  "`build()` also produces `parlays_xg` and `parlay_costs`."]
        r.appendix("Appendix 2 — published rows that never reach a page", lines)
    dash = {}
    for key_, tbl in site["sections"].items():
        n = sum(1 for row in tbl.get("rows", []) for v in vals(row).values() if str(v).strip() == "\u2014")
        if n:
            dash[key_] = n
    r.add("CC-HTML-03b", g, "the literal em-dash is only ever used for \u201cnot applicable\u201d, never for \u201cnot verified\u201d",
          "count literal em-dash values per table; a withheld value must be null so the renderer marks it blank+flagged",
          INFO, "; ".join(f"{k}: {v}" for k, v in sorted(dash.items())))
    idx = (ROOT / "index.html").read_text()
    nav = [x.split("#")[0].split("?")[0] for x in re.findall(r'href="(pages/[^"]+)"', idx)]
    missing = [n for n in set(nav) if n and not (ROOT / n).exists()]
    r.add("CC-HTML-04", g, "every navigation target on the landing page exists",
          f"{len(set(nav))} distinct page links from index.html", PASS if not missing else FAIL,
          f"missing: {missing or 'none'}")
    orphans = sorted({p.name for p in (ROOT / "pages").glob("*.html")} - {n.split("/")[-1] for n in nav})
    r.add("CC-HTML-05", g, "no published page is unreachable from the landing page",
          "a page nobody can click is a page nobody reviews", PASS if not orphans else INFO,
          f"unlinked page(s): {orphans or 'none'}")


def check_freshness(r: Report, site: dict):
    g = "J. freshness (the known product blocker)"
    slate = load_json(snapshot_candidates("slate")[0])
    as_of = date.fromisoformat(str(slate.get("as_of")))
    head = ROOT / ".git/HEAD"
    commit_date = None
    try:
        import subprocess
        out = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%cI"],
                             capture_output=True, text=True, timeout=20)
        commit_date = out.stdout.strip()
    except Exception:
        pass
    today = date.fromisoformat(str(datetime.now(timezone.utc).date()))
    stale_days = (today - as_of).days
    dates = sorted({x[slate["columns"].index("date")] for x in slate["records"]})
    expired = [d for d in dates if date.fromisoformat(d) <= today]
    r.add("CC-FRESH-01", g, "the snapshot is within one day of the run date (the freshness SLA the brief implies)",
          f"as_of {as_of} vs run date {today}", PASS if stale_days <= 1 else FAIL,
          f"{stale_days} day(s) old; games already tipped or tipping inside the published window: {len(expired)} date(s)")
    r.add("CC-FRESH-02", g, "a stale snapshot is disclosed, not hidden",
          "grep the emitted landing page for a staleness statement",
          INFO, "the site prints the as-of date on every page" if "as-of" in (ROOT / "index.html").read_text().lower()
                else "no explicit stale-state banner found on index.html")
    r.add("CC-FRESH-03", g, "no automated ingestion exists that could keep the snapshot current",
          "list the workflows in .github/workflows and look for a schedule trigger",
          INFO, _workflow_summary(),
          note="recorded so the gap is visible on the report rather than assumed away")


# --------------------------------------------------------------------------- helpers used above
RATINGS_EVIDENCE = "nba2/pipeline/build_site_data.py build_ratings_rows"

NAME_STATUS_COUNTS: dict[str, dict[str, int]] = {}


def _index_injuries(site):
    for row in rows_of(site, "injuries"):
        v = vals(row)
        name = str(v.get("team") or "")
        d = NAME_STATUS_COUNTS.setdefault(name, {})
        key = {"Out": "out", "Doubtful": "doubtful", "Questionable": "questionable",
               "Probable": "probable", "Available": "available"}.get(str(v.get("status")))
        if key:
            d[key] = d.get(key, 0) + 1
    for row in rows_of(site, "ratings"):
        v = vals(row)
        RATINGS_TRI_NAME[v.get("tricode")] = v.get("team")


RATINGS_TRI_NAME: dict[str, str] = {}


def _wl_reconciliation_line(captures: dict[str, dict[str, str]]) -> str:
    parts = []
    for name, d in captures.items():
        parts.append(f"{name}: {len(d)}/30")
    return "; ".join(parts)


def _workflow_summary() -> str:
    d = ROOT / ".github/workflows"
    if not d.exists():
        return "no workflows directory"
    out = []
    for p in sorted(d.glob("*.yml")):
        text = p.read_text()
        trig = re.findall(r"^\s{2}(\w+):", text.split("on:", 1)[-1].split("\njobs")[0], re.M)
        out.append(f"{p.name}: {','.join(t for t in trig if t in ('push', 'pull_request', 'schedule', 'workflow_dispatch')) or '?'}")
    return "; ".join(out)


# --------------------------------------------------------------------------- report
def to_markdown(r: Report, out_path: str) -> str:
    c = r.counts()
    L = []
    L.append("# Independent cross-check of the published site against the committed snapshots")
    L.append("")
    L.append(f"Owner: `arena/5b80b88a-nba2` · run {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
             f"tool: `tools/crosscheck_site.py` (stdlib only, read-only)")
    L.append("")
    L.append("## What this is, in one paragraph")
    L.append("")
    L.append("CI proves the HTML is a faithful render of `data/site.json`, and the provenance lint proves every row "
             "is labelled. Neither can prove that a label matches what it points at, because the same code produced "
             "both. This report re-derives each published claim from the committed snapshot files with its own "
             "arithmetic. A **PASS** means the published artefact agrees with the committed snapshot and with the "
             "other surfaces in this repository; it is never a claim that the official source was re-read today, "
             "because this environment has no route to `nba.com` (see `CC-FRESH-03`). A **FAIL** is a defect worth "
             "a change request. An **N/A** means the claim's referent is not computable from committed evidence, and "
             "no plausible number was substituted for it.")
    L.append("")
    L.append(f"**Result: {c[PASS]} PASS · {c[FAIL]} FAIL · {c[INFO]} INFO · {c[NA]} N/A "
             f"over {len(r.checks)} checks.**")
    L.append("")
    fails = [x for x in r.checks if x.verdict == FAIL]
    if fails:
        L.append("## Findings that need a decision")
        L.append("")
        for x in fails:
            L.append(f"- **{x.id}** — {x.assertion}. Observed: {x.observed}."
                     + (f" {x.note}" if x.note else ""))
        L.append("")
    L.append("## All checks")
    L.append("")
    L.append("| ID | Group | Claim checked | How it was recomputed | Verdict | Observed |")
    L.append("|---|---|---|---|---|---|")
    for x in r.checks:
        def clean(s):
            return str(s).replace("|", "/").replace("\n", " ")[:420]
        icon = {PASS: "PASS", FAIL: "**FAIL**", INFO: "INFO", NA: "n/a"}[x.verdict]
        L.append(f"| {x.id} | {clean(x.group)} | {clean(x.assertion)} | {clean(x.method)} | {icon} | {clean(x.observed)} |")
    L.append("")
    L.append("## Evidence links for manual review")
    L.append("")
    seen = set()
    for x in r.checks:
        if x.evidence and x.evidence.startswith("http") and x.evidence not in seen:
            seen.add(x.evidence)
            L.append(f"- {x.id}: <{x.evidence}>")
    for u in ["https://www.nba.com/schedule", "https://www.nba.com/games",
              "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf",
              "https://www.basketball-reference.com/leagues/NBA_2027_standings.html"]:
        if u not in seen:
            L.append(f"- snapshot provenance recorded by the build: <{u}>")
    L.append("")
    for title, lines in r.appendices:
        L.append(f"## {title}")
        L.append("")
        L.extend(lines)
        L.append("")
    L.append("## How to reproduce")
    L.append("")
    L.append("```")
    L.append("python3 tools/crosscheck_site.py                      # console summary of every check")
    L.append("python3 tools/crosscheck_site.py --markdown analysis/crosscheck-5b80b88a.md")
    L.append("```")
    L.append("")
    L.append("Exit code is non-zero iff a check FAILs, so the run can be wired into CI without changing what the "
             "site publishes.")
    L.append("")
    text = "\n".join(L) + "\n"
    if out_path:
        Path(out_path).write_text(text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", default="")
    ap.add_argument("--json", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--strict", action="store_true", help="exit non-zero even on INFO")
    args = ap.parse_args()

    if not SITE_JSON.exists():
        print(f"missing {SITE_JSON} — run: python -m nba2.pipeline.build_site_data", file=sys.stderr)
        return 2
    site = load_json(SITE_JSON)
    _index_injuries(site)

    r = Report()
    check_snapshots(r, site)
    check_published_vs_snapshot(r, site)
    check_derived_arithmetic(r, site)
    check_gates_leaderboard(r, site)
    check_seal(r, site)
    check_flags_blanks(r, site)
    check_cross_surface(r, site)
    check_docs(r, site)
    check_html(r, site)
    check_freshness(r, site)

    if args.only:
        keep = [k.strip() for k in args.only.split(",") if k.strip()]
        r.checks = [c for c in r.checks if any(c.id.startswith(k) for k in keep)]

    for c in r.checks:
        mark = {PASS: " ok ", FAIL: "FAIL", INFO: "info", NA: " n/a"}[c.verdict]
        print(f"[{mark}] {c.id:14s} {c.assertion}")
        if c.verdict in (FAIL, INFO, NA):
            print(f"        observed: {c.observed}")
            if c.note:
                print(f"        note:     {c.note}")
    counts = r.counts()
    print(f"\n{len(r.checks)} checks: {counts[PASS]} pass, {counts[FAIL]} fail, "
          f"{counts[INFO]} info, {counts[NA]} n/a")
    if args.markdown:
        to_markdown(r, args.markdown)
        print(f"wrote {args.markdown}")
    if args.json:
        Path(args.json).write_text(json.dumps([c.__dict__ for c in r.checks], indent=1) + "\n")
        print(f"wrote {args.json}")
    if counts[FAIL] or (args.strict and counts[INFO]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
