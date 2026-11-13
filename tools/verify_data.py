#!/usr/bin/env python3
"""Line-by-line validator for data/verified/*.json and verified/*.html.

Stdlib only. Exit code 0 only when every check passes.

Rules enforced (see README and COORDINATION.md):
  * every data row carries an https source URL on an official NBA host;
  * game IDs are NBA game IDs (10 digits, 0022600xxx);
  * injury rows must match the schedule: matchup exists, date and tip time match,
    and the player's team is one of the two teams in that matchup;
  * numeric / modelled fields (minutes impact, odds, correlations) stay null
    unless a source is attached;
  * declared counts equal the actual row counts;
  * generated HTML has no broken local links or fragment anchors.
"""
import html.parser
import json
import pathlib
import re
import sys
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "verified"
SITE = ROOT / "verified"

OFFICIAL_HOSTS = {"www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com", "cdn.nba.com", "stats.nba.com"}
ALLOWED_STATUS = {"Out", "Questionable", "Doubtful", "Probable", "Available", "NOT YET SUBMITTED"}

errors = []
checks = 0


def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        errors.append(msg)


def is_official(url, extra=()):
    if not isinstance(url, str):
        return False
    p = urlparse(url)
    return p.scheme == "https" and (p.hostname or "") in (set(OFFICIAL_HOSTS) | set(extra))


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def validate_schedule(sched):
    rows = sched["rows"]
    abbr = sched["team_abbreviations"]
    start, end = sched["window"]["start"], sched["window"]["end"]
    check(len(rows) == sched["counts"]["total"] == 31, f"schedule: expected 31 rows, found {len(rows)}")
    per_day = {}
    for r in rows:
        per_day[r["date"]] = per_day.get(r["date"], 0) + 1
    for d, n in per_day.items():
        check(sched["counts"].get(d) == n, f"schedule: day {d} count {n} != declared {sched['counts'].get(d)}")
    ids = [r["game_id"] for r in rows]
    check(len(set(ids)) == len(ids), "schedule: duplicate game_id")
    for r in rows:
        gid = r["game_id"]
        check(re.fullmatch(r"0022600\d{3}", gid) is not None, f"schedule {gid}: not an NBA game id")
        check(start <= r["date"] <= end, f"schedule {gid}: date {r['date']} outside window")
        check(is_official(r["source_url"]), f"schedule {gid}: source_url not official")
        check(is_official(r["preview_url"]), f"schedule {gid}: preview_url not official")
        m = re.fullmatch(r"https://www\.nba\.com/game/([a-z]{3})-vs-([a-z]{3})-(\d{10})", r["preview_url"])
        check(m is not None, f"schedule {gid}: preview_url pattern")
        if m:
            a, h, pid = m.group(1).upper(), m.group(2).upper(), m.group(3)
            check(pid == gid, f"schedule {gid}: preview id {pid} differs")
            check(r["matchup"] == f"{a}@{h}", f"schedule {gid}: matchup {r['matchup']} != slug {a}@{h}")
        check(abbr.get(r["away"]) and abbr.get(r["home"]), f"schedule {gid}: unknown team name")
        check(r["matchup"] == f"{abbr.get(r['away'])}@{abbr.get(r['home'])}", f"schedule {gid}: matchup/team mismatch")
    return {r["matchup"]: r for r in rows}, abbr


def validate_injuries(inj, sched_by_matchup):
    pdf = inj["report"]["pdf_url"]
    check(is_official(pdf), "injuries: report pdf_url not official")
    keys = set()
    for r in inj["rows"]:
        s = sched_by_matchup.get(r["matchup"])
        check(s is not None, f"injury {r['player']}: matchup {r['matchup']} not in window")
        if s is None:
            continue
        check(r["game_date"] == s["date"] and r["tip_et"] == s["tip_et"], f"injury {r['player']}: date/time differs from schedule")
        check(r["team"] in (s["away"], s["home"]), f"injury {r['player']}: team {r['team']} not in {r['matchup']}")
        check(r["status"] in ALLOWED_STATUS, f"injury {r['player']}: status {r['status']} not allowed")
        check(is_official(r["source_url"]), f"injury {r['player']}: source_url not official")
        check(r["minutes_impact"] is None, f"injury {r['player']}: minutes_impact set without source")
        k = (r["matchup"], r["player"])
        check(k not in keys, f"injury duplicate {k}")
        keys.add(k)
    for r in inj["team_status_rows"]:
        s = sched_by_matchup.get(r["matchup"])
        check(s is not None and r["team"] in (s["away"], s["home"]), f"status row {r['matchup']} {r['team']} invalid")
        check(is_official(r["source_url"]), "status row: source not official")
    full_names = set()
    for s in sched_by_matchup.values():
        full_names.add(s["away"])
        full_names.add(s["home"])
    for r in inj["unattributed_rows"]:
        check(r["team"] is None or r["team"] in full_names, f"unattributed {r['player']}: unknown team {r['team']}")
        check(bool(r["why_unattributed"]), f"unattributed {r['player']}: missing reason")
        check(is_official(r["source_url"]), f"unattributed {r['player']}: source not official")
    c = inj["counts"]
    check(c["rows_attributed"] == len(inj["rows"]), "injuries: rows_attributed count mismatch")
    check(c["team_status_rows_attributed"] == len(inj["team_status_rows"]), "injuries: status count mismatch")
    check(c["unattributed_rows"] == len(inj["unattributed_rows"]), "injuries: unattributed count mismatch")


def validate_audit(aud):
    for f in aud["findings"]:
        check(bool(f.get("id")) and bool(f.get("result")), f"audit {f.get('id')}: missing id/result")
        src = f.get("source_url")
        if f["result"].startswith("Match") or "Mismatch" in f["result"]:
            check(is_official(src), f"audit {f['id']}: {f['result']} requires an official source")
        if src is not None:
            check(is_official(src), f"audit {f['id']}: source_url not official")
    check(len(aud["findings"]) > 0, "audit: no findings")


def validate_picks(picks, sched_ids):
    for p in picks["rows"]:
        check(p["game_id"] in sched_ids, f"pick {p['game_id']}: not in schedule")
        if p["status"] == "PICK":
            check(is_official(p["schedule_source"]), f"pick {p['game_id']}: schedule source missing")
            check(bool(p.get("validated_strategy_id")), f"pick {p['game_id']}: no validated strategy")
            check(bool(p.get("price_source")), f"pick {p['game_id']}: no timestamped price source")
            check(bool(p.get("line_source")), f"pick {p['game_id']}: no originated line source")
        else:
            check(p["status"] == "NO PICK", f"pick {p['game_id']}: unknown status {p['status']}")
            check(len(p["blockers"]) > 0, f"pick {p['game_id']}: NO PICK without blockers")


class LinkParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            self.ids.add(d["id"])
        if tag == "a" and "href" in d:
            self.links.append(d["href"])
        if tag == "link" and "href" in d:
            self.links.append(d["href"])


def validate_html():
    pages = {}
    for p in list(SITE.glob("*.html")) + [ROOT / "index.html", ROOT / "flagged.html"]:
        if p.exists():
            parser = LinkParser()
            parser.feed(p.read_text(encoding="utf-8"))
            pages[p.resolve()] = parser
    for path, parser in pages.items():
        for href in parser.links:
            if href.startswith(("http://", "https://", "mailto:", "tel:")):
                continue
            target, _, frag = href.partition("#")
            tpath = path if target == "" else (path.parent / target).resolve()
            check(tpath.exists(), f"{path.relative_to(ROOT)}: broken link {href}")
            if frag and tpath.exists() and tpath.suffix == ".html":
                other = pages.get(tpath)
                if other is None:
                    other = LinkParser()
                    other.feed(tpath.read_text(encoding="utf-8"))
                check(frag in other.ids, f"{path.relative_to(ROOT)}: missing anchor #{frag} in {tpath.name}")
    return len(pages)


def main():
    sched = load("schedule_2026-11-13_to_16.json")
    inj = load("injuries_2026-11-13_0515PM.json")
    aud = load("audit_arena-23927d63.json")
    sched_by_matchup, _ = validate_schedule(sched)
    validate_injuries(inj, sched_by_matchup)
    validate_audit(aud)
    picks_path = DATA / "picks_gate_status.json"
    if picks_path.exists():
        picks = json.loads(picks_path.read_text(encoding="utf-8"))
        validate_picks(picks, {r["game_id"] for r in sched["rows"]})
    flagged = load("flagged.json")
    for f in flagged["rows"]:
        check(is_official(f["source_url"], extra={"kansspelautoriteit.nl", "gokstop.nl", "github.com"}), f"flagged {f['id']}: source not official")
        check(bool(f["status"]), f"flagged {f['id']}: missing status")
    n_pages = validate_html() if SITE.exists() else 0
    print(f"checks run: {checks}; html pages scanned: {n_pages}; errors: {len(errors)}")
    for e in errors:
        print("ERROR:", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
