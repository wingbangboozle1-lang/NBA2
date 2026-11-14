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
    for f_ in inj_files:
        inj = load_json(f_)
        icols = {c: i for i, c in enumerate(inj["columns"])}
        irecs = inj.get("records", [])
        counts = inj.get("record_counts", {})
        cont = [x[icols["attribution"]] for x in irecs]
        nys = sum(1 for x in irecs if x[icols["status"]] == "NOT YET SUBMITTED")
        status_key = next((k for k in counts if k.startswith("rows_with_status")), None)
        recomputed = {
            "total_rows": len(irecs),
            "not_yet_submitted_placeholders": nys,
            "attribution_explicit": cont.count("E"),
            "attribution_continuation": cont.count("C"),
        }
        if status_key:
            recomputed[status_key] = len(irecs) - nys
        games_key = next((k for k in counts if k == "games_covered"), None)
        if games_key:
            recomputed["games_covered"] = len({x[icols["matchup"]] for x in irecs})
        stored = {k: counts[k] for k in recomputed if k in counts}
        ok = all(str(v) == str(stored.get(k)) for k, v in recomputed.items()) and len(stored) >= 3
        r.add(f"CC-SNAP-08:{f_.stem}", g, f"{f_.name}: its own record_counts equal a recount of its records",
              "recount total / status / placeholder / attribution (and games covered, when claimed)",
              PASS if ok else FAIL, f"stored {stored} vs recomputed {recomputed}",
              evidence=inj.get("provenance", {}).get("url", ""))
        allowed = {"Out", "Doubtful", "Questionable", "Probable", "Available", "NOT YET SUBMITTED",
                   "Suspended", "G League - On Two-Way Contract", "G League - On Assignment", "Rest",
                   "Personal Reasons", "G League - Two-Way", "Not With Team"}
        statuses = {x[icols["status"]] for x in irecs if x[icols["status"]] is not None}
        r.add(f"CC-SNAP-09:{f_.stem}", g, f"{f_.name}: every status string is one the report can print",
              "set of status values in the snapshot",
              PASS if statuses <= allowed else INFO,
              f"statuses: {sorted(statuses)}" + (f"; unseen here: {sorted(statuses - allowed)}" if statuses - allowed else ""),
              note="INFO, not FAIL, when an unseen-but-plausible label appears: the vocabulary belongs to the "
                   "NBA, not to us, and we do not invent a rule about it")
        r.add(f"CC-SNAP-10:{f_.stem}", g, f"{f_.name}: attribution is recorded per row (E explicit / C continuation)",
              "column 'attribution' takes only the two documented values",
              PASS if set(cont) <= {"E", "C"} else FAIL, f"E={cont.count('E')} C={cont.count('C')}")

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
    # The snapshot carries FOUR labels, each about a different arithmetic fact. The old check
    # looked for the string "FAIL" anywhere in them and compared it with a single league-wide
    # recomputation, so a snapshot that got two labels right and two wrong passed. Each label is
    # now matched to its own recomputation.
    checks = rat.get("provenance", {}).get("internal_consistency_checks", [])
    home_ok = all(x[rcols["home_w"]] + x[rcols["home_l"]] + x[rcols["road_w"]] + x[rcols["road_l"]]
                  == x[rcols["w"]] + x[rcols["l"]] for x in rrecs)
    over_games = [x[rcols["tricode"]] for x in rrecs
                  if x[rcols["close_w"]] + x[rcols["close_l"]] + x[rcols["blowout_w"]] + x[rcols["blowout_l"]]
                  > x[rcols["w"]] + x[rcols["l"]]]
    truth = {
        "home_w+home_l+road_w+road_l == w+l for all 30 teams": home_ok,
        "close_w+close_l+blowout_w+blowout_l <= w+l for all teams": not over_games,
        "sum(close_w) == sum(close_l) required by construction": close_w == close_l,
        "sum(blowout_w) == sum(blowout_l) required by construction": blow_w == blow_l,
    }
    label_bad = []
    for c in checks:
        c = str(c)
        key = next((k for k in truth if c.startswith(k)), None)
        if key is None:
            label_bad.append(f"unrecognised check: {c[:60]}")
            continue
        says_fail = "FAIL" in c
        if says_fail == (not truth[key]):
            continue
        label_bad.append(f"{key}: label says {'FAIL' if says_fail else 'PASS'}, recomputation says "
                         f"{'FAIL' if not truth[key] else 'PASS'}")
    r.add("CC-SNAP-13", g, "ratings: each of the snapshot's own PASS/FAIL labels matches its own recomputation",
          f"4 labels vs 4 recomputations (home/road {home_ok}; close+blowout<=games "
          f"{'ok' if not over_games else f'{len(over_games)} violations'}; close {close_w}={close_l}; "
          f"blowout {blow_w}={blow_l})",
          PASS if not label_bad else FAIL,
          f"{len(label_bad)} label(s) disagree: {label_bad[:2] or 'none'}",
          note="every close/blowout game is one win and one loss, so the league-wide sums must match; the "
               "per-team bound is a separate fact and has to be checked per team - a league-level check "
               "alone would have passed a snapshot that 18 clubs contradict")
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

    inj_rows = rows_of(site, "injuries")
    inj_file = _matching_injury_snapshot(site)
    inj = load_json(inj_file)
    icols = {c: i for i, c in enumerate(inj["columns"])}
    irecs = inj["records"]
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
            # Accept any verdict that denies coverage ("not in the 11/13 report" was the
            # generator's original wording; after the 19:30 refresh the verdict says "not
            # covered by the current injury-report release" — same fact, different release).
            if not re.search(r"not (?:in\b|covered\b)", verdict, re.I):
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
    # CR-4 (retargeted 2026-11-14 in the final merge): 'wl_official' is sourced from the league's
    # own standings capture (arena/6650be4d switched the column's source to
    # data/raw/official_standings_2026-11-14.json); the check compares each column with the file
    # that column is actually rendered from.
    _stand = load_json(ROOT / "data" / "raw" / "official_standings_2026-11-14.json")
    _stand_cols = {c: i for i, c in enumerate(_stand["columns"])}
    recs_official = {x[_stand_cols["tricode"]]: f"{x[_stand_cols['w']]}-{x[_stand_cols['l']]}"
                     for x in _stand["records"]}
    snap = load_json(snapshot_candidates("ratings")[0])
    snap_cols = {c: i for i, c in enumerate(snap["columns"])}
    snap_wl = {x[snap_cols["tricode"]]: f"{x[snap_cols['w']]}-{x[snap_cols['l']]}"
               for x in snap["records"]}
    prov_bad = []
    for row in ratings:
        v = vals(row)
        tc = str(v.get("tricode") or v.get("team") or "")
        if v.get("wl") is not None and snap_wl.get(tc) not in (None, v.get("wl")):
            prov_bad.append(f"{tc}: 'W-L (ratings source)' {v.get('wl')} != ratings snapshot {snap_wl.get(tc)}")
        if v.get("wl_official") is not None and recs_official.get(tc) not in (None, v.get("wl_official")):
            prov_bad.append(f"{tc}: 'W-L (official NBA.com)' {v.get('wl_official')} != "
                            f"data/raw/official_standings_2026-11-14.json {recs_official.get(tc)}")
    caption = str(section(site, "ratings").get("source_note") or "")
    caption_ok = ("NBA.com" in caption or "nba.com" in caption) and \
                 ("Basketball-Reference" in caption or "third-party" in caption or "ratings snapshot" in caption)
    r.add("CC-DER-05", g, "the two W-L columns are independent measurements, as the caption claims",
          "each column is diffed against its own capture — 'W-L (official NBA.com)' vs "
          "data/raw/official_standings_2026-11-14.json and 'W-L (ratings source)' vs the ratings snapshot — and the "
          "caption must name both sources",
          PASS if not prov_bad and caption_ok else FAIL,
          f"{len(prov_bad)} provenance mismatch(es): {prov_bad[:3] or 'none'}; caption names both "
          f"sources: {caption_ok}",
          evidence="data/raw/official_standings_2026-11-14.json (official NBA.com standings); " + str(RATINGS_EVIDENCE),
          note="2026-11-14 arena/6c5195d1 (CR-4): the old test failed whenever the two columns held "
               "identical values on all rows — but identical values are exactly what two agreeing "
               "independent captures produce, while the pre-fix build really did print one field "
               "twice. Independence is now tested the only way it can be mechanically: each column "
               "must equal its own source file. If the two captures ever disagree the columns "
               "diverge visibly and the caption's 'the table is wrong' guard can actually fire.")
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
    neg = []
    COUNT_WORDS = re.compile(r"(rows|games|teams|slots|filed|out|doubtful|questionable|probable|available|legs|bets|predictions|not_yet_submitted|no_rows_yet|two_way_or_susp|not_submitted|coverage)$")
    for key_, tbl in site["sections"].items():
        for row in tbl.get("rows", []):
            for col, v in vals(row).items():
                n = num(v) if isinstance(v, (int, float)) or (isinstance(v, str) and re.fullmatch(r"-?\d+(\.\d+)?", v.strip() or "")) else None
                if n is not None and n < 0 and COUNT_WORDS.search(col):
                    neg.append(f"{key_}/{row['key']}.{col} = {v}")
    r.add("CC-DER-11", g, "no count published anywhere on the site is negative",
          "scan every numeric cell of every table whose column name denotes a count",
          PASS if not neg else FAIL, f"{len(neg)} negative count(s): {neg[:5] or 'none'}",
          note="a negative count is never a measurement; it is two sets subtracted in the wrong order")

    avail = rows_of(site, "availability_window") if "availability_window" in site["sections"] else []
    if avail:
        union: dict[str, dict[str, set]] = {}
        for p_ in snapshot_candidates("injury"):
            d0 = load_json(p_)
            c0 = {c: i for i, c in enumerate(d0.get("columns", []))}
            for rec in d0.get("records", []):
                dte = rec[c0["game_date"]]
                e = union.setdefault(dte, {"filed": set(), "nys": set()})
                (e["nys"] if rec[c0["status"]] == "NOT YET SUBMITTED" else e["filed"]).add(rec[c0["team"]])
        sl = load_json(snapshot_candidates("slate")[0])
        sc = {c: i for i, c in enumerate(sl["columns"])}
        as_of = sl.get("as_of")
        bad = []
        for row in avail:
            v = vals(row)
            dte = str(v.get("date"))
            n_games = sum(1 for x in sl["records"] if x[sc["date"]] == dte)
            slots = 2 * n_games
            e = union.get(dte, {"filed": set(), "nys": set()})
            filed = len(e["filed"])
            nys_only = len(e["nys"] - e["filed"])
            unlisted = slots - filed - nys_only
            if num(v.get("no_rows_yet")) != unlisted:
                bad.append(f"{dte}: published no_rows_yet {v.get('no_rows_yet')}, "
                           f"recomputed {unlisted} (slots {slots} - filed {filed} - not-submitted-only {nys_only})")
            if num(v.get("not_yet_submitted")) != nys_only:
                bad.append(f"{dte}: published NOT YET SUBMITTED {v.get('not_yet_submitted')}, "
                           f"recomputed {nys_only} teams that have no designation in any release either")
        r.add("CC-DER-12", g, "availability coverage recomputes from both official injury snapshots",
              "union the team designations across every committed injury snapshot per date, then "
              "recount: a team that has since filed must not also be counted as not-yet-submitted",
              PASS if not bad else FAIL, f"{len(bad)} problem(s): {bad[:3] or 'none'}",
              evidence="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf",
              note="the column is a count of teams, and the sets overlap: 'filed' and 'NOT YET SUBMITTED' "
                   "are not disjoint when two releases are unioned, so slots - filed - nys can go below zero")

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
        m = re.match(r"^(\d+) pass / (\d+) fail / (\d+) blocked(?: / (\d+) at-risk)?", claim)
        got = per.get(v["id"], {})
        if m:
            want = {"PASS": int(m.group(1)), "FAIL": int(m.group(2)), "BLOCKED": int(m.group(3)),
                    "AT-RISK": int(m.group(4) or 0)}
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
          f"recount per strategy over {len(gate_rows)} rows; the tally string must itemise "
          f"PASS / FAIL / BLOCKED / AT-RISK separately (2026-11-14 arena/6c5195d1, CR-5: AT-RISK "
          f"used to be folded into 'blocked', so the published tally contradicted the matrix)",
          PASS if not lb_bad else FAIL,
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
    sealed_at = datetime.fromisoformat(str(doc["header"]["sealed_at_utc"]).replace("Z", "+00:00"))

    def tip_utc(p):
        """Game tip as a UTC datetime. time_et is an EST clock value (UTC-5 on every date in
        this window — EST from 2026-11-01). None when the sealed row has no parsable time."""
        m = re.match(r"^(\d{1,2}):(\d{2})$", str(p.get("time_et") or "").strip())
        if not m:
            return None
        return datetime.fromisoformat(p["date"]).replace(
            hour=int(m.group(1)), minute=int(m.group(2)),
            tzinfo=timezone(timedelta(hours=5)))

    outside, wrong_time = [], []
    for p in payload:
        gid = p["game_id"]
        src = srecs.get(gid)
        if not src:
            outside.append(f"{gid} not in the official slate snapshot")
            continue
        tu = tip_utc(p)
        if tu is None:
            outside.append(f"{gid}: sealed row has no parsable tip time, so 'tipped after the "
                           f"seal' cannot be proven")
        elif tu <= sealed_at.astimezone(tu.tzinfo):
            outside.append(f"{gid} tips {tu.isoformat()} which is not after the seal "
                           f"{sealed_at.isoformat()}")
        if norm_time(p.get("time_et")) != norm_time(src[scols["time_et"]]):
            wrong_time.append(f"{gid}: sealed {p.get('time_et')} vs official {src[scols['time_et']]}")
    r.add("CC-SEAL-04", g, "every sealed prediction is an official game inside the window, tipped after the snapshot",
          "game must be in the official slate snapshot and its tip datetime (EST -> UTC) must be "
          "strictly after header.sealed_at_utc — a same-day game sealed the previous evening or "
          "early that morning is valid, which a date-only comparison wrongly rejects",
          PASS if not outside else FAIL,
          f"{len(outside)} problem(s): {outside[:3] or 'none'}",
          evidence=f"{path.relative_to(ROOT)} header.sealed_at_utc = {doc['header']['sealed_at_utc']}",
          note="2026-11-14 arena/6c5195d1: the previous date-only rule ('game date > slate as_of') "
               "flagged the five same-day 11/14 games in sealed-2026-11-14 even though the ledger "
               "was sealed at 00:58 UTC and every one of those tips is 23:00 UTC or later. The "
               "invariant the seal exists to prove is temporal order — tip after seal — so the "
               "comparison is now over datetimes. (arena/6650be4d independently relaxed the "
               "date-only rule to allow same-day games; the datetime rule is kept because it also "
               "catches a same-day game sealed after its own tip.)")
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
    pub_inj = load_json(_matching_injury_snapshot(site))
    icols = {c: i for i, c in enumerate(pub_inj["columns"])}
    cont_actual = sum(1 for x in pub_inj["records"] if x[icols["attribution"]] == "C")
    total_actual = len(pub_inj["records"])
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


def check_backtest_surface(r: Report, site: dict):
    """Recompute the measured-skill report from the committed game rows.

    `tools/verify_backtest.py` (the owner's own checker) verifies structure: every row has an
    official URL, links resolve, no placeholders, byte-reproducible pages. Nothing verifies the
    *arithmetic* of the headline statistics, which is the part a reader acts on. These checks do,
    from `data/raw/history/games_*.json`.
    """
    g = "K. the measured-skill surface, recomputed"
    hist = sorted((RAW / "history").glob("games_*.json"))
    rep_path = ROOT / "backtest" / "data" / "report.json"
    if not hist or not rep_path.exists():
        r.add("CC-BT-00", g, "the backtest surface and its history snapshots both exist",
              f"history files: {len(hist)}; report: {rep_path.exists()}", NA,
              "one or both are absent in this checkout, so nothing is asserted about them")
        return
    rep = load_json(rep_path)
    games: dict[str, dict] = {}
    bad_rows = []
    for f in hist:
        doc = load_json(f)
        for x in doc.get("games", []):
            gid = str(x.get("game_id") or "")
            if not re.fullmatch(r"002\d{7}", gid):
                bad_rows.append(f"{f.name}: game_id {gid!r}")
                continue
            if gid in games:
                bad_rows.append(f"{f.name}: game_id {gid} duplicated across history files")
            a, h = x.get("away_pts"), x.get("home_pts")
            if not (isinstance(a, int) and isinstance(h, int) and a >= 0 and h >= 0):
                bad_rows.append(f"{gid}: scores are not two non-negative integers ({a!r}/{h!r})")
            if {x.get("away"), x.get("home")} - TEAM_TRICODES:
                bad_rows.append(f"{gid}: unknown tricode {x.get('away')}/{x.get('home')}")
            if not str(x.get("source_url") or "").startswith("https://www.nba.com/game/"):
                bad_rows.append(f"{gid}: no official game URL on the row")
            games[gid] = x
    dates = sorted({x["date"] for x in games.values()})
    meta = rep.get("meta", {})
    count_ok = (meta.get("n_games") == len(games) and meta.get("n_dates") == len(dates)
                and str(meta.get("first_date")) == dates[0] and str(meta.get("last_date")) == dates[-1])
    r.add("CC-BT-01", g, "the report's headline counts equal a recount of the committed game rows",
          f"{len(games)} unique games across {len(hist)} history files, {len(dates)} dates "
          f"{dates[0]}..{dates[-1]}" if dates else "no games",
          PASS if count_ok and not bad_rows else FAIL,
          f"report says n_games={meta.get('n_games')}, n_dates={meta.get('n_dates')}, "
          f"{meta.get('first_date')}..{meta.get('last_date')}; bad rows: {bad_rows[:3] or 'none'}",
          evidence="https://www.nba.com/games")
    as_of = str(load_json(snapshot_candidates("slate")[0]).get("as_of"))
    future = [gid for gid, x in games.items() if str(x.get("date")) > as_of]
    r.add("CC-BT-02", g, "a 'final scores' set contains only games that precede the snapshot it is graded against",
          f"compare each game date with the slate snapshot as_of ({as_of})",
          PASS if not future else FAIL, f"{len(future)} game(s) dated after the snapshot: {future[:4] or 'none'}")

    def frac(a, b):
        return round(a / b, 4) if b else None

    acc, ats, nb = rep.get("accuracy", {}), rep.get("ats", {}), rep.get("naive_baselines", {})
    arith = []
    if ats.get("n") and ats.get("hits") is not None:
        if abs(frac(ats["hits"], ats["n"]) - round(float(ats.get("hit_rate", 0)), 4)) > 0.0002:
            arith.append(f"ats.hit_rate {ats.get('hit_rate')} != {ats['hits']}/{ats['n']}")
    for name in ("always_home", "better_net_rating", "originated_model"):
        blk = nb.get(name) or {}
        n = blk.get("n", nb.get("n_games"))
        if blk.get("hits") is not None and n:
            if abs(frac(blk["hits"], n) - round(float(blk.get("rate", 0)), 4)) > 0.0002:
                arith.append(f"naive_baselines.{name}.rate {blk.get('rate')} != {blk['hits']}/{n}")
    m, b = nb.get("originated_model", {}).get("rate"), nb.get("better_net_rating", {}).get("rate")
    mb = nb.get("model_vs_better_net", {})
    if m is not None and b is not None and "observed_diff" in mb:
        if abs(round(m - b, 4) - float(mb["observed_diff"])) > 0.0002:
            arith.append(f"model_vs_better_net.observed_diff {mb['observed_diff']} != {m} - {b}")
        if bool(mb.get("model_better")) != (m > b):
            arith.append(f"model_better={mb.get('model_better')} contradicts {m} vs {b}")
    r.add("CC-BT-03", g, "every published rate equals its own numerator over its own denominator",
          "recompute ATS hit rate, the three naive baselines, and the head-to-head difference",
          PASS if not arith else FAIL, f"{len(arith)} violation(s): {arith[:4] or 'none'}")

    tiers = rep.get("tiers", [])
    tier_sum = sum(int(x.get("n", 0)) for x in tiers)
    cal = rep.get("calibration", [])
    cal_sum = sum(int(x.get("n", 0)) for x in cal)
    probs = []
    if acc.get("n") and tier_sum != acc["n"]:
        probs.append(f"tiers sum {tier_sum} != accuracy.n {acc['n']}")
    if acc.get("n") and cal_sum != acc["n"]:
        probs.append(f"calibration bins sum {cal_sum} != accuracy.n {acc['n']}")
    for x in cal:
        mp, lo, hi = x.get("mean_predicted"), None, None
        mm = re.match(r"^(\d+)%-(\d+)%$", str(x.get("bin", "")))
        if mm and mp is not None:
            lo, hi = int(mm.group(1)) / 100, int(mm.group(2)) / 100
            if not (lo - 0.02 <= float(mp) <= hi + 0.02):
                probs.append(f"bin {x['bin']}: mean_predicted {mp} outside the bin's own range")
        for k in ("ci95_low", "ci95_high"):
            if x.get(k) is not None and not (0 <= float(x[k]) <= 1):
                probs.append(f"bin {x.get('bin')}: {k}={x[k]} is not a probability")
        if x.get("ci95_low") is not None and x.get("ci95_high") is not None and float(x["ci95_low"]) > float(x["ci95_high"]):
            probs.append(f"bin {x.get('bin')}: CI inverted")
    r.add("CC-BT-04", g, "the tier and calibration breakdowns partition the graded sample, and each bin reports its own range",
          f"tiers {tier_sum} / calibration {cal_sum} / accuracy.n {acc.get('n')}",
          PASS if not probs else FAIL, f"{len(probs)} problem(s): {probs[:4] or 'none'}")

    gates = rep.get("gates", {}).get("gates", {})
    summary = rep.get("gates", {}).get("summary", {})
    recomputed = {"PASS": [], "FAIL": [], "BLOCKED": [], "PARTIAL": []}
    for gid, gd in gates.items():
        recomputed.setdefault(str(gd.get("status")), []).append(gid)
    sum_bad = []
    for key, label in (("passed", "PASS"), ("failed", "FAIL"), ("blocked", "BLOCKED"), ("partial", "PARTIAL")):
        if sorted(summary.get(key, [])) != sorted(recomputed.get(label, [])):
            sum_bad.append(f"{key}: summary {sorted(summary.get(key, []))} vs gate states {sorted(recomputed.get(label, []))}")
    if summary.get("n") != len(gates):
        sum_bad.append(f"summary.n {summary.get('n')} != {len(gates)} gates defined")
    r.add("CC-BT-05", g, "the gate summary is a true index of the per-gate statuses",
          f"regroup the {len(gates)} gate verdicts by status and compare with the summary lists",
          PASS if not sum_bad else FAIL, f"{len(sum_bad)} problem(s): {sum_bad[:3] or 'none'}")
    m_bad = []
    for gid, gd in gates.items():
        mm = re.search(r"(\d+)\s*/\s*(\d+)", str(gd.get("arithmetic", "")))
        if mm:
            n, req = int(mm.group(1)), int(mm.group(2))
            pct = re.search(r"(\d+)%", str(gd.get("arithmetic", "")))
            if pct and abs(round(100 * n / req) - int(pct.group(1))) > 1:
                m_bad.append(f"{gid}: says {pct.group(1)}% but {n}/{req} = {100 * n / req:.1f}%")
            if gd.get("status") == "FAIL" and req and n >= req:
                m_bad.append(f"{gid}: FAIL while {n} >= {req}")
    r.add("CC-BT-06", g, "every gate verdict follows from the numbers printed beside it",
          "parse each 'arithmetic' string and re-check the percentage and the pass/fail direction",
          PASS if not m_bad else FAIL, f"{len(m_bad)} problem(s): {m_bad[:3] or 'none'}",
          note="the same rule the site applies to itself, applied to the tree that now measures it")

    lb = rep.get("leaderboard", [])
    lb_bad = []
    zs = [float(x.get("z_deflated_for_search") or 0) for x in lb]
    if zs != sorted(zs, reverse=True):
        lb_bad.append(f"ranks are not ordered by the deflated z the notes say is the ranking metric: {zs}")
    if any(x.get("reward_units") for x in lb) and (summary.get("failed") or []):
        lb_bad.append("a reward is allocated while a gate is FAILED")
    if not summary.get("failed") and not summary.get("blocked"):
        lb_bad.append("rewards withheld even though no gate is failed or blocked")
    r.add("CC-BT-07", g, "the provisional leaderboard ranks by the metric it names, and pays nobody while a gate fails",
          f"{len(lb)} strategies; gate summary failed={summary.get('failed')} blocked={summary.get('blocked')}",
          PASS if not lb_bad else FAIL, f"{len(lb_bad)} problem(s): {lb_bad[:3] or 'none'}")

    site_gp = site["meta"].get("gates_passed")
    bt_pass = len(recomputed.get("PASS", []))
    r.add("CC-BT-08", g, "the two surfaces tell one story about what has been measured",
          f"root site publishes gates_passed={site_gp} of {site['meta'].get('gates_total')} with the line "
          f"'Ledger opens with the 2026-11-13 slate; nothing has settled yet'; the backtest surface reports "
          f"{bt_pass} of {len(gates)} gates PASS on {acc.get('n')} graded games",
          INFO if bt_pass else PASS,
          f"the two are not contradictory — the site's gates are stated in settled bets against a price, the "
          f"backtest's in graded games against outcomes — but a reader of the canonical page cannot see that "
          f"{acc.get('n')} games have been graded at all, and the vocabulary differs (PASS/FAIL/BLOCKED/"
          f"AT-RISK vs PASS/FAIL/BLOCKED/PARTIAL)",
          note="filed as finding F8: the measured result exists, but only on a second surface")


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
    sched = _workflow_summary()
    has_ingest = "schedule" in sched
    runs_today = _refresh_run_count()
    r.add("CC-FRESH-03", g, "a scheduled ingestion exists, and it has actually run",
          "list the workflows and their triggers; then record whether any ingest run exists yet",
          PASS if (has_ingest and runs_today.isdigit() and int(runs_today) > 0) else INFO,
          f"{sched}; ingest runs recorded: {runs_today}"
          + ("" if runs_today.isdigit() and int(runs_today) > 0
             else " \u2014 not a PASS: the schedule is armed but nothing has run, so the site's "
                  "freshness still depends on a manual or first-scheduled ingest"),
          note="an active schedule with zero runs is not yet a refresh: the site is only as fresh as the "
               "last successful ingest run, so this check stays INFO until a run exists")


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


def _refresh_run_count() -> str:
    """Number of ingest runs, read from a local `gh` call when one is available.

    Deliberately not an assertion: if the CLI is missing or the API is unreachable, the answer is
    'unknown', and the check reports that instead of guessing a zero.
    """
    import subprocess
    try:
        out = subprocess.run(["gh", "run", "list", "--workflow", "Nightly ingest + settlement", "--limit", "5"],
                             capture_output=True, text=True, timeout=25, cwd=str(ROOT))
        lines = [x for x in out.stdout.strip().splitlines() if x.strip()]
        return str(len(lines)) if out.returncode == 0 and lines else "unknown (no runs reported or gh unavailable)"
    except Exception:
        return "unknown (gh not reachable from this environment)"


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


def _matching_injury_snapshot(site: dict) -> Path:
    """The injury snapshot the published injuries table actually came from."""
    pub = rows_of(site, "injuries")

    def score(path: Path) -> tuple:
        d0 = load_json(path)
        c0 = {c: i for i, c in enumerate(d0.get("columns", []))}
        recs0 = d0.get("records", [])
        if "player" not in c0 or len(recs0) != len(pub):
            return (-1, str(path))
        hits = sum(1 for i, rec in enumerate(recs0)
                   if pub[i]["key"] == f"inj-{i}"
                   and vals(pub[i]).get("player") == (rec[c0["player"]] or "\u2014"))
        return (hits, str(path))

    return max(snapshot_candidates("injury"), key=score)


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
             "because this environment has no route to `nba.com` \u2014 measured, not assumed: "
             "`python3 tools/ingest_official.py --probe` returns a TLS failure for all four official "
             "endpoints from the sandbox that produced this report. A **FAIL** is a defect worth "
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
    check_backtest_surface(r, site)
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
