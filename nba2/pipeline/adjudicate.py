"""Adjudicate cross-session disagreements against the third document we now have.

After this session merged, `main` also carried session arena-71f94203's ingest of the **17:15 ET**
injury report (`data/verified/injuries_2026-11-13_0515PM.json`). That gives three independent
reads of the same official document family:

    13:00 ET  -> the prior session's snapshot
    16:15 ET  -> our snapshot
    17:15 ET  -> a third session's snapshot

so a 13:00-vs-16:15 status conflict is no longer a two-way dispute: the 17:15 value decides which
capture reflects the latest official state, and it is a fact about documents, not a modelling
opinion. This module also removes one session's *own* injury convention from its spread so the
remaining gap between models can be compared honestly.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .. import config
from ..provenance import Src, flag, make_row, register_source, table

ROOT = Path(__file__).resolve().parents[2]
VERIFIED = ROOT / "data" / "verified"
CSV_LINES = ROOT / "data" / "our-lines.csv"

register_source("third_revision", "Third session's ingest of the 17:15 ET official report",
                "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/verified/injuries_2026-11-13_0515PM.json",
                Src.DERIVED,
                "Underlying document is official (ak-static.cms.nba.com, Injury-Report_2026-11-13_05_15PM.pdf); "
                "the JSON is another session's transcription of it, ingested here for comparison.")
register_source("third_model_csv", "Third session's originated lines (data/our-lines.csv)",
                "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/our-lines.csv", Src.DERIVED,
                "Produced by scripts/model.py from basketball-reference ratings + its own injury/rest "
                "conventions; documented assumptions, per that session's own header comment.")


def _surname(p: str) -> str:
    n = (p or "").strip()
    return n.split(",", 1)[0].strip().lower() if "," in n else (n.split()[-1].strip().lower() if n else "")


def load_third_revision() -> tuple[dict, dict]:
    """Index the 17:15 ET ingest two ways: by (team, surname) and by surname alone.

    The surname-only index keeps a *set* of statuses so an ambiguous surname cannot silently
    pick one row: if the set has more than one element the caller must treat it as unresolved.
    """
    path = VERIFIED / "injuries_2026-11-13_0515PM.json"
    if not path.exists():
        return {}, {}
    doc = json.loads(path.read_text())
    by_team: dict[tuple[str, str], str] = {}
    by_name: dict[str, set] = {}
    # that ingest splits its rows into the cleanly attributed list, whole-team status rows, and
    # rows whose team cell was lost to a page break. All three are evidence; ignoring the last
    # two would "adjudicate" 2 of 6 conflicts and call the other 4 unresolvable.
    allrows = list(doc.get("rows", [])) + list(doc.get("unattributed_rows", []))
    for r in doc.get("team_status_rows", []) or []:
        if isinstance(r, dict):
            allrows.append(r)
    for r in allrows:
        sn = _surname(r.get("player", ""))
        team = (r.get("team") or "").strip()
        st = r.get("status", "")
        if team:
            by_team[(team, sn)] = st
        by_name.setdefault(sn, set()).add(st)
    return by_team, by_name


def adjudicate(their_inj: dict, my_rows: list) -> dict:
    """For every status the two earlier captures disagree on, ask the 17:15 revision."""
    from .reconcile import _flatten_their_injuries, surname  # same join rules, one implementation

    third_by_team, third_by_name = load_third_revision()
    theirs = {}
    for r in _flatten_their_injuries(their_inj or {"games": []}):
        theirs[(r["game_date"], r["team"], surname(r.get("player", "")))] = r
    full_to_tri = {v: k for k, v in config.TEAM_NAMES.items()}
    mine = {}
    for r in my_rows:
        # our snapshot stores full team names, theirs stores tricode: normalise to tricode so the
        # join is on the league's own identifier rather than a string that can drift
        mine[(r.game_date, full_to_tri.get(r.team, r.team), surname(r.player))] = r

    rows = []
    resolved = 0
    for k, t in sorted(theirs.items(), key=lambda kv: str(kv[0])):
        m = mine.get(k)
        if m is None or (t.get("status") or "") == m.status:
            continue  # not a conflict
        sn = k[2]
        third_status = third_by_team.get((m.team, sn))
        if third_status is None:
            ambiguous = third_by_name.get(sn, set())
            third_status = next(iter(ambiguous)) if len(ambiguous) == 1 else None
        agrees_with_us = third_status == m.status
        agrees_with_them = third_status == t.get("status")
        if agrees_with_us:
            verdict = "17:15 ET revision matches OUR capture — the later official state supersedes the 13:00 read"
            resolved += 1
            fl = []
        elif agrees_with_them:
            verdict = "17:15 ET revision matches the PRIOR capture — our 16:15 read should be re-checked"
            fl = ["FLAG-XADJ-01"]
        elif third_status is None:
            verdict = "player absent from the 17:15 ingest — cannot adjudicate"
            fl = ["FLAG-XADJ-02"]
        else:
            verdict = f"17:15 revision says {third_status!r}, matching neither — three-way discrepancy"
            fl = ["FLAG-XADJ-01"]
        rows.append(make_row(
            f"{k[0]}|{k[1]}|{k[2]}", "third_revision", fl or ["FLAG-XADJ-03"],
            game_date=k[0], team=m.team, player=m.player,
            status_1300=t.get("status"), status_1615=m.status, status_1715=third_status,
            our_reason=m.reason, verdict=verdict,
        ))
    flag("FLAG-XADJ-01", "high", "cross-session",
         "A status conflict where the latest official revision agrees with neither capture, or with the "
         "older one: our snapshot would be stale or wrong. Each such row is listed and must be re-read from "
         "the PDF before it influences anything.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf",
         "Re-parse the newest revision; do not trust any cached snapshot past tip-off.")
    flag("FLAG-XADJ-02", "medium", "cross-session",
         "The third session's ingest does not contain a row for a disputed player, so the conflict cannot be "
         "adjudicated from it. Absence in that file is not absence from the report — their parse is partial "
         "by their own note.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/verified/injuries_2026-11-13_0515PM.json",
         "Read the 17:15 PDF directly for these rows.")
    flag("FLAG-XADJ-03", "low", "cross-session",
         "Rows where the 17:15 ET revision corroborates our 16:15 capture. Recorded so the corroboration is "
         "auditable rather than asserted in prose.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/verified/injuries_2026-11-13_0515PM.json",
         "None; keep the three timestamps side by side when the next revision lands.")
    n = len(rows)
    return table(rows, [("game_date", "Game date"), ("team", "Team"), ("player", "Player"),
                        ("status_1300", "13:00 ET (prior session)"), ("status_1615", "16:15 ET (ours)"),
                        ("status_1715", "17:15 ET (third session)"), ("our_reason", "Official reason"),
                        ("verdict", "Adjudication")],
                 f"Status conflicts, adjudicated against a third official revision — {resolved} of {n} resolved in favour of the latest read",
                 "Two sessions disagreed on six statuses and both believed they had read the same document "
                 "correctly. A third session had ingested the 17:15 ET revision, which is later than ours, so "
                 "the disagreement is now testable instead of a matter of trust. This is what 'verify against "
                 "official sources' is actually worth: not a claim of care, but a second and third copy to "
                 "compare against.",
                 "Injury-Report_2026-11-13_01_00PM.pdf / _04_15PM.pdf / _05_15PM.pdf")


def load_csv_lines() -> dict:
    if not CSV_LINES.exists():
        return {}
    out = {}
    with CSV_LINES.open(newline="") as fh:
        for r in csv.DictReader(fh):
            out[r["game_id"]] = r
    return out


def reconcile_three_way(mine_lines, their_picks: dict) -> dict:
    """Our line vs session-2's label vs session-3's line — and how much of the last gap is convention."""
    s2 = {}
    for l in their_picks.get("lines", []):
        s2[(l.get("away"), l.get("home"))] = l
    s3 = load_csv_lines()
    rows = []
    gaps_raw, gaps_adj = [], []
    for g in mine_lines:
        c = s3.get(g.game_id)
        b = s2.get((g.away, g.home))
        if c is None and b is None:
            continue
        theirs2 = None
        if b is not None and b.get("originated_spread") is not None:
            theirs2 = round(-float(b["originated_spread"]), 1)
        s3_spread = float(c["our_spread_home"]) if c else None
        inj_h = float(c.get("home_injury_impact") or 0) if c else 0.0
        inj_a = float(c.get("away_injury_impact") or 0) if c else 0.0
        # their spread embeds their injury convention; strip it with their own published fields
        s3_ex = round(s3_spread - inj_h + inj_a, 1) if s3_spread is not None else None
        d_raw = d_adj = None
        if s3_spread is not None and g.spread_home is not None:
            d_raw = round(s3_spread - g.spread_home, 1)
            gaps_raw.append(abs(d_raw))
            if s3_ex is not None:
                d_adj = round(s3_ex - g.spread_home, 1)
                gaps_adj.append(abs(d_adj))
        fl = ["FLAG-XSESS-07"]
        rows.append(make_row(
            g.game_id, "third_model_csv", fl,
            date=g.date, matchup=f"{g.away} @ {g.home}",
            ours=f"{g.spread_home:+.1f}" if g.spread_home is not None else None,
            session2=f"{theirs2:+.1f}" if theirs2 is not None else None,
            session3=f"{s3_spread:+.1f} (inj {inj_h:+.1f}/{inj_a:+.1f})" if s3_spread is not None else None,
            session3_ex_injury=f"{s3_ex:+.1f}" if s3_ex is not None else None,
            gap_raw=None if d_raw is None else f"{d_raw:+.1f} pts",
            gap_after_stripping=None if d_adj is None else f"{d_adj:+.1f} pts",
            note=("session 3 prices with a documented injury convention (4.0/2.0/0.8 pts per missing "
                  "player by PPG tier, ×status multiplier, capped at 8.0) and applies rest "
                  "adjustments; we apply neither, because no official source rates them"),
        ))
    mean_raw = sum(gaps_raw) / len(gaps_raw) if gaps_raw else float("nan")
    mean_adj = sum(gaps_adj) / len(gaps_adj) if gaps_adj else float("nan")
    # Rows where the earlier model actually embedded a convention: only those can move when the
    # convention is stripped. Reporting one number over all rows would hide which is which.
    moved = [(r, a) for r, a in zip(gaps_raw, gaps_adj) if abs(r - a) > 1e-9]
    if moved:
        m_raw = sum(r for r, _ in moved) / len(moved)
        m_adj = sum(a for _, a in moved) / len(moved)
        if m_adj < m_raw:
            direction = (f"removing that convention shrinks the mean gap from {m_raw:.1f} to {m_adj:.1f} pts "
                         f"on those {len(moved)} games — so most of the disagreement there is a parameter, "
                         "not a difference in the evidence")
        else:
            direction = (f"removing that convention does NOT shrink the gap: it moves the mean from {m_raw:.1f} "
                         f"to {m_adj:.1f} pts on those {len(moved)} games. The earlier claim that most "
                         "disagreement is an unratified convention does not replicate on the current "
                         "comparison set and is therefore not repeated here")
    else:
        m_raw = m_adj = float("nan")
        direction = ("no game in this comparison carries a non-zero convention in the earlier model, so "
                     "stripping changes nothing and there is nothing to conclude about conventions here")
    flag("FLAG-XSESS-07", "high", "cross-session",
         f"Three models, one slate: mean absolute spread disagreement is {mean_raw:.1f} pts over "
         f"{len(gaps_raw)} comparable games, and {mean_adj:.1f} pts after removing session 3's own injury "
         f"adjustment from its line. {direction.capitalize()}.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/scripts/model.py",
         "Ratify one injury/rest convention (or none) before any trigger is armed; see S-04.")
    return table(rows, [("date", "Date"), ("matchup", "Matchup"), ("ours", "Ours"),
                        ("session2", "Session 2"), ("session3", "Session 3 (with its injury adj.)"),
                        ("session3_ex_injury", "Session 3 minus that adjustment"),
                        ("gap_raw", "Gap"), ("gap_after_stripping", "Gap after stripping"),
                        ("note", "Why they differ")],
                 "Three originated lines for the same games — and how much of the gap is convention",
                 f"Mean |gap| across {len(gaps_raw)} comparable games: {mean_raw:.1f} pts as published, "
                 f"{mean_adj:.1f} pts once session 3's own injury adjustment is stripped out using the "
                 f"fields it published. {direction.capitalize()}. The comparison set moves with the window: "
                 "when the window rolled forward the comparable set changed, so this sentence is recomputed "
                 "from the data on every build and never asserts a direction the measurement does not show.",
                 "ours: data/site.json · session 2: nba2/data/picks.json · session 3: data/our-lines.csv "
                 "(scripts/model.py)")
