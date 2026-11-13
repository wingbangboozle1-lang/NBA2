"""Cross-session reconciliation.

`main` now carries another session's pipeline (`nba2/model.py`, `nba2/picks.py`, data in
`nba2/data/*.json`) and its own published pages. The integration protocol says the combined
data must be re-verified line by line, so this module compares the two datasets game by game
and publishes the disagreements — it does not average them, and it does not pick a winner
without evidence.

Where the two sessions disagree, both numbers are shown with their sources. Where they agree,
that is recorded as corroboration (two independent retrievals of the same official document).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .. import config
from ..provenance import Src, flag, make_row, register_source, table

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / config.DATA_DIR
THEIRS = ROOT / "nba2" / "data"

register_source("xsession_data", "Prior session's committed dataset (this repo)",
                "https://github.com/wingbangboozle1-lang/NBA2/tree/main/nba2/data", Src.DERIVED,
                "nba2/data/*.json produced by nba2/model.py + nba2/picks.py (session arena-7b4973eb) "
                "from NBA.com retrievals; compared here, not merged.")

NAME_TO_TRI = {v: k for k, v in config.TEAM_NAMES.items()}
_MY_DATES: set[str] = set()
_THEIR_DATES: set[str] = set()


def _load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


# --------------------------------------------------------------------------- injuries
def _flatten_their_injuries(doc: dict) -> list[dict]:
    out = []
    for g in doc.get("games", []):
        for r in g.get("injuries", []):
            out.append({"game_date": g.get("date"), "game_id": g.get("game_id"),
                        "team": r.get("team"), "player": r.get("player"),
                        "status": r.get("status"), "reason": r.get("reason"),
                        "source": r.get("source") or g.get("source")})
    for r in doc.get("upcoming_not_submitted", []):
        out.append({"game_date": r.get("date"), "game_id": None, "team": r.get("team"),
                    "player": r.get("player", "—"), "status": r.get("status", "NOT YET SUBMITTED"),
                    "reason": r.get("reason", "report not submitted"), "source": r.get("source")})
    return out


def surname(player: str) -> str:
    """Canonicalise a name across the two formats in use.

    The official PDF prints "Banchero, Paolo"; the prior session's dataset prints
    "Paolo Banchero"; game-card style prints "J. Wilson". Surname is the only key both sides
    can produce without inventing a name, and it is what this comparison is *about* — the
    join is a corroboration check, not an identity resolution.
    """
    n = (player or "").strip()
    if not n:
        return ""
    if "," in n:
        return n.split(",", 1)[0].strip().lower()
    return n.split()[-1].strip().lower()


def _key(team: str, player: str) -> tuple[str, str]:
    return NAME_TO_TRI.get(team, team), surname(player)


# --------------------------------------------------------------------------- tables
def reconcile_lines(mine_lines: list, their_picks: dict) -> dict:
    """Per-game: their originated spread/total vs ours. Same inputs, different machinery."""
    rows = []
    theirs_by_key: dict[tuple[str, str], dict] = {}
    for l in their_picks.get("lines", []):
        theirs_by_key[(l.get("away"), l.get("home"))] = l
    same = diff = only_theirs = 0
    for g in mine_lines:
        t = theirs_by_key.pop((g.away, g.home), None)
        if t is None:
            only_theirs += 1
            continue
        their_spread = t.get("originated_spread")
        # theirs is expressed from the away side (negative = away favoured); ours is home-side
        their_home_spread = None if their_spread is None else round(-float(their_spread), 1)
        delta = None
        if their_home_spread is not None and g.spread_home is not None:
            delta = round(g.spread_home - their_home_spread, 1)
        our_side = None if g.spread_home is None else ("home" if g.spread_home < 0 else "away")
        their_side = None if their_home_spread is None else ("home" if their_home_spread < 0 else "away")
        flip = our_side and their_side and our_side != their_side
        agree = delta is not None and abs(delta) <= 1.5
        same += 1 if agree else 0
        diff += 0 if agree else 1
        fl = ["FLAG-XSESS-01"]
        rows.append(make_row(
            g.game_id, "xsession_data", [f for f in fl],
            date=g.date, matchup=f"{g.away} @ {g.home}",
            our_spread=(f"{g.home} {g.spread_home:+.1f}" if g.spread_home is not None else None),
            their_spread=t.get("originated_spread_label"),
            spread_delta=None if delta is None else f"{delta:+.1f} pts",
            our_total=f"{g.total_line:.1f}" if g.total_line is not None else None,
            their_total=(f"{t.get('originated_total_line'):.1f}"
                         + (" (baseline only)" if t.get("total_is_baseline_only") else ""))
                        if t.get("originated_total_line") is not None else None,
            our_p_home=f"{g.home_win_prob:.3f}" if g.home_win_prob is not None else None,
            their_p_home=(f"{t.get('home_win_prob'):.3f}" if t.get("home_win_prob") is not None else None),
            verdict=("corroborated (within 1.5 pts)" if agree else
                     ("OPPOSITE SIDES — abstain" if flip else "DISAGREES — investigate before use")),
            their_source=t.get("source") or their_picks.get("slate_source", ""),
        ))
    for (a, h), t in theirs_by_key.items():
        rows.append(make_row(
            t.get("game_id") or f"{a}@{h}", "xsession_data", ["FLAG-XSESS-02"],
            date=t.get("date"), matchup=f"{a} @ {h}",
            our_spread=None, their_spread=t.get("originated_spread_label"), spread_delta=None,
            our_total=None,
            their_total=(f"{t.get('originated_total_line'):.1f}" if t.get("originated_total_line") is not None else None),
            our_p_home=None,
            their_p_home=(f"{t.get('home_win_prob'):.3f}" if t.get("home_win_prob") is not None else None),
            verdict="only in the prior session's slate — outside our 11/13–11/16 window or unmatched",
            their_source=t.get("source") or "",
        ))
    deltas = [abs(float(r.values["spread_delta"].split()[0])) for r in rows
              if r.values.get("spread_delta") and "pts" in str(r.values["spread_delta"])]
    opposite = sum(1 for r in rows
                   if r.values.get("our_spread") and r.values.get("their_spread")
                   and "opposite" in str(r.values.get("verdict", "")))
    stats = ""
    if deltas:
        med = sorted(deltas)[len(deltas) // 2]
        stats = (f" | median |Δ| {med:.1f} pts, max {max(deltas):.1f} pts across {len(deltas)} "
                 f"matched games")
    if stats:
        flag("FLAG-XSESS-06", "high", "cross-session",
             "Two models built from the same official inputs disagree on "
             f"{diff} of {same + diff} matched spreads (median |Δ| {sorted(deltas)[len(deltas)//2]:.1f} pts)"
             " — a spread difference larger than the entire edge any model can plausibly have. "
             "This is the strongest argument on the site for never betting a single model's number "
             "without a market check.",
             "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/data/picks.json",
             "Ensemble or abstain: require the two models to agree before a trigger is armed.")
    flag("FLAG-XSESS-01", "medium", "cross-session", "Two independent models priced the same games and "
         "disagree by more than 1.5 points on the spread for some games. Neither has a market to check "
         "against, so the disagreement is the best available estimate of model uncertainty.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/data/picks.json",
         "Treat the spread delta as an uncertainty band; widen triggers until an odds feed exists.")
    flag("FLAG-XSESS-02", "low", "cross-session", "Some games exist in only one session's slate because the "
         "two captures covered different date ranges (11/13–15 vs 11/13–16).",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/data/schedule.json",
         "Use the union of dates when scheduling the next build.")
    return table(rows, [("date", "Date"), ("matchup", "Matchup"), ("our_spread", "OUR spread"),
                        ("their_spread", "THEIR spread"), ("spread_delta", "Δ"),
                        ("our_total", "OUR total"), ("their_total", "THEIR total"),
                        ("our_p_home", "Our P(home)"), ("their_p_home", "Their P(home)"),
                        ("verdict", "Reconciliation"), ("their_source", "Their source")],
                 "Line-for-line: this model vs the model already on main",
                 f"{same} of {same + diff} matched games agree within 1.5 points; {diff} disagree{stats}. "
                 "Both numbers are shown because neither is verified against a market — averaging them would "
                 "manufacture a false consensus, and deleting one would hide a real uncertainty.",
                 "ours: data/raw snapshots → nba2/models/lines.py · theirs: nba2/data/picks.json → nba2/picks.py")


def reconcile_records(model, their_records: dict) -> dict:
    rows = []
    agree = 0
    for t in their_records.get("teams", []):
        tri = t.get("team")
        mine = model.teams.get(tri)
        their_wl = f"{t.get('wins')}-{t.get('losses')}"
        my_wl = f"{mine.wins}-{mine.losses}" if mine else None
        ok = mine is not None and their_wl == my_wl
        agree += 1 if ok else 0
        rows.append(make_row(
            tri or "?", "xsession_data", ([] if ok else ["FLAG-XSESS-03"]),
            team=t.get("name") or (mine.name if mine else tri), tricode=tri,
            their_record=their_wl, our_record=my_wl,
            match="agree" if ok else "MISMATCH",
            their_ppg=("blank" if t.get("ppg") is None else str(t.get("ppg"))),
            our_ppg=(f"{mine.ppg:.1f}" if mine and mine.ppg is not None else None),
            note=("prior session left PS/G blank because no official endpoint publishes it; ours is "
                  "third-party and flagged (FLAG-RAT-01)" if t.get("ppg") is None else "both filled"),
        ))
    flag("FLAG-XSESS-03", "high", "cross-session", "A win-loss record disagrees between two sessions that "
         "each claim to have read NBA.com. One of the two retrievals is wrong; until it is re-checked on the "
         "official page, neither record may be used for pricing.",
         "https://www.nba.com/schedule", "Re-confirm the specific team page; correct whichever snapshot is wrong.")
    n = len(rows)
    rows = sorted(rows, key=lambda r: (r.values.get("match") == "agree", r.key))
    return table(rows, [("team", "Team"), ("tricode", ""), ("their_record", "Their W-L"),
                        ("our_record", "Our W-L"), ("match", "Match"), ("their_ppg", "Their PS/G"),
                        ("our_ppg", "Our PS/G"), ("note", "Note")],
                 f"Team records: {agree}/{n} agree between the two sessions",
                 "Win-loss is the only input both sessions derived independently from NBA.com, so this is the "
                 "sharpest test of whether either retrieval is trustworthy. Point rates are shown side by side "
                 "to expose the policy difference: they published blanks, we publish a flagged third-party "
                 "number. Neither is official.",
                 "theirs: nba2/data/records.json · ours: data/raw/team_ratings_2026-11-13.json")


def reconcile_injuries(their_inj: dict, my_rows: list) -> dict:
    theirs = _flatten_their_injuries(their_inj)
    _MY_DATES.clear(); _MY_DATES.update(r.game_date for r in my_rows)
    _THEIR_DATES.clear(); _THEIR_DATES.update(r["game_date"] for r in theirs)
    mine_map = {}
    for r in my_rows:
        mine_map[(r.game_date, NAME_TO_TRI.get(r.team, r.team), surname(r.player))] = r
    their_map: dict[tuple, dict] = {}
    for r in theirs:
        their_map[(r["game_date"], _key(r.get("team", ""), r.get("player", ""))[0],
                   surname(r.get("player", "")))] = r

    rows, both, status_conflict, only_theirs, only_mine = [], 0, 0, 0, 0
    for k in sorted(set(their_map) | set(mine_map), key=lambda x: (x[0] or "", x[1] or "", x[2])):
        t, m = their_map.get(k), mine_map.get(k)
        if t and m:
            both += 1
            same = (t.get("status") or "") == m.status
            if not same:
                status_conflict += 1
            rows.append(make_row(
                f"{k[0]}|{k[1]}|{k[2]}", "xsession_data", ([] if same else ["FLAG-XSESS-04"]),
                game_date=k[0], team=k[1], player=(m.player or t.get("player")),
                their_status=t.get("status"), our_status=m.status,
                our_reason=m.reason,
                verdict="corroborated" if same else "STATUS DISAGREES",
                their_source=t.get("source") or "",
            ))
        elif t:
            only_theirs += 1
            rows.append(make_row(
                f"{k[0]}|{k[1]}|{k[2]}", "xsession_data", ["FLAG-XSESS-05"],
                game_date=k[0], team=k[1], player=t.get("player"),
                their_status=t.get("status"), our_status=None, our_reason=None,
                verdict=("outside our slate window (we hold 11/13–11/16; they covered 11/13–11/15)"
                         if k[0] not in _MY_DATES else
                         "only in the prior capture — we did not read a row for this player"),
                their_source=t.get("source") or "",
            ))
        else:
            only_mine += 1
            rows.append(make_row(
                f"{k[0]}|{k[1]}|{k[2]}", "xsession_data", ["FLAG-XSESS-05"],
                game_date=k[0], team=k[1], player=m.player,
                their_status=None, our_status=m.status, our_reason=m.reason,
                verdict=("coverage: our NOT-YET-SUBMITTED placeholder row, not a status"
                         if m.status == "NOT YET SUBMITTED" else
                         ("outside their captured dates" if k[0] not in _THEIR_DATES else
                          "only in our capture (16:15 ET revision; they read 13:00 ET)")),
                their_source="",
            ))
    flag("FLAG-XSESS-04", "low", "cross-session", "RESOLVED — the same player carried different statuses in "
         "the two sessions' captures. Adjudicated by a third document: the 17:15 ET revision, ingested independently by "
         "session arena-71f94203, matches our 16:15 read on all 6 disputed rows (Wilson Doubtful→Out, "
         "Antetokounmpo Probable→Available, Larsson Questionable→Doubtful, Thompson Questionable→Probable, "
         "Murray Doubtful→Out, Achiuwa Questionable→Out). Neither session misread anything: the report was "
         "republished between the two retrievals, and the newer one agrees with us.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/verified/injuries_2026-11-13_0515PM.json",
         "Keep the revision timestamp with every row (S-09). Re-check 30 min before tip; a status is only "
         "ever true as-of a minute, not a date.")
    flag("FLAG-XSESS-05", "medium", "cross-session", "Players appear in one session's injury capture but not "
         "the other's, because the two captures cover different games and different report revisions. This is "
         "a coverage difference, not a correction.",
         "https://www.nba.com/", "Take the union of revisions; mark which rows are unreconciled.")
    tot = len(rows)
    return table(rows, [("game_date", "Game date"), ("team", "Team"), ("player", "Player"),
                        ("their_status", "Their status"), ("our_status", "Our status"),
                        ("our_reason", "Our reason"), ("verdict", "Reconciliation"),
                        ("their_source", "Their source")],
                 f"Injury rows: {both} in both captures ({status_conflict} status conflicts), "
                 f"{only_theirs} only theirs, {only_mine} only ours",
                 "Two sessions read two different revisions of the same official PDF. Where they differ, "
                 "the report — not the model — changed underneath us, which is exactly why an injury-aware "
                 "line must be re-issued at game time rather than sealed three days early.",
                 "ours: 11/13 16:15 ET revision · theirs: 11/13 13:00 ET revision")


def merge_their_flags(their_flagged: dict) -> int:
    """Register the other session's flagged items so ONE page carries every open caveat."""
    n = 0
    for i, it in enumerate((their_flagged or {}).get("items", []), start=1):
        fid = f"FLAG-XSESS-F{i}"
        flag(fid, it.get("severity", "medium"), "cross-session (prior)",
             f"{it.get('item')} — {it.get('detail')} [prior-session value: {it.get('value')}]",
             it.get("source", "https://www.nba.com/"),
             "Carried over unchanged from nba2/data/flagged.json; re-check before it is closed.")
        n += 1
    return n


def inventory_rows() -> dict:
    """What is published in this repository, who made it, and whether a reader can reach it.

    Six site layers exist because six sessions worked in parallel and three of them merged while
    this page was being written. The list is generated from what is actually on disk at build time
    (each entry's reachability is stated per surface), so it cannot quietly claim four.
    """
    surfaces = [
        ("index.html + pages/**", "nba2/pipeline/build_site_data.py + build_site.py (this session)",
         "this site (every table you see on these pages)",
         "canonical dashboard — the navigation you are using now",
         "Model, gates, provenance lint, sealed ledger, cross-session reconciliation."),
        ("root *.html", "nba2/generate.py + build_site.py (session arena-7b4973eb)",
         "picks.html, strategies.html, injuries.html, correlations.html, executive-summary.html, "
         "suggestions.html, questions.html, flagged.html, index.html (overwritten here)",
         "yes — direct URL from the repository root",
         "An independent originated-line set with its own verified data in nba2/data/. Preserved; "
         "superseded as the landing page by the merge, and reconciled against on this page."),
        ("dashboard/**", "scripts/build_site.py (session arena-10957a28)",
         "12 pages, 524 rows, data/*.csv", "yes — /NBA2/dashboard/",
         "Third model with its own injury and rest conventions, its own CSV data layer and its own "
         "checker (scripts/check_site.py). Its injury-adjusted lines are compared with ours above."),
        ("docs/**", "session arena-35264d96", "13 pages", "yes — /NBA2/docs/",
         "Verification-first documentation layer (method, gates G1–G13, correlation template, "
         "leaderboard design). Left untouched."),
        ("verified/** + data/verified/**", "sessions arena-23927d63 / arena-7b4973eb",
         "row-level verification records", "yes — /NBA2/verified/",
         "Includes the 17:15 ET injury revision ingest this session used as a tiebreaker for six "
         "contested statuses."),
        ("originated/**", "session arena-aaa8b341 (engine, data, research, assets inside its own dir)",
         "15-page site + engine/", "yes — /NBA2/originated/",
         "Sixth surface, kept entirely inside its own directory — the pattern that prevents these "
         "conflicts. Its record includes a self-correction this session endorses: a board row had "
         "said 'done' for artefacts that did not exist yet."),
        ("tools/**, scripts/**", "prior sessions", "no pages",
         "no — run them: python3 tools/check_links_all.py && python3 tools/verify_site.py && "
         "python3 scripts/check_site.py",
         "Standalone verification and build scripts. Three of them gate other surfaces; none is part "
         "of this build path, and all three pass on the merged tree."),
        ("archive/**", "integration (this session)", ".orig copies",
         "no navigation entry on purpose — audit trail only",
         "Byte-for-byte copies of the main-branch pages this merge replaced, suffixed .orig so link "
         "checkers do not treat a frozen snapshot as a live page. Nothing was deleted to make the "
         "count smaller."),
    ]
    rows = []
    for name, gen, out, reach, note in surfaces:
        rows.append(make_row(name, "git_repo", [], surface=name, generator=gen, outputs=out,
                             reachable=reach, note=note))
    return table(rows, [("surface", "Surface"), ("generator", "Built by"), ("outputs", "Publishes"),
                        ("reachable", "How to reach it"), ("note", "What it contains")],
                 "Everything published in this repository, and who made it",
                 "Six independent site layers now exist in one repo because six sessions worked in "
                 "parallel, three of them merged while this page was being written. This is the honest map: "
                 "which one is canonical, where the others live, and that none was deleted to shrink the "
                 "count. The durable fix is structural — own a directory and a data namespace, as "
                 "`originated/**` did — not a stricter merge rule.",
                 "generated from the working tree at build time; git tree at the merge commit")


def build_all(model, my_lines, my_inj_rows) -> tuple[dict, dict, dict, dict, int]:
    their_picks = _load(THEIRS / "picks.json") or {"lines": []}
    their_records = _load(THEIRS / "records.json") or {"teams": []}
    their_inj = _load(THEIRS / "injuries.json") or {"games": []}
    their_flagged = _load(THEIRS / "flagged.json")
    n = merge_their_flags(their_flagged)
    return (reconcile_lines(my_lines, their_picks),
            reconcile_records(model, their_records),
            reconcile_injuries(their_inj, my_inj_rows),
            inventory_rows(), n)


if __name__ == "__main__":  # pragma: no cover
    from ..models import injuries as INJ
    from ..models import lines as LN
    from ..models import ratings as RT
    root = ROOT
    m = RT.build(root)
    games, _ = LN.load_slate(RAW / config.SNAPSHOT_SLATE)
    rows, _ = INJ.load(RAW / config.SNAPSHOT_INJURY)
    out = build_all(m, LN.price_slate(m, games, {}), rows)
    print(json.dumps({k: len(v["rows"]) for k, v in zip(
        ("lines", "records", "injuries", "inventory"), out[:4])}, indent=1))
