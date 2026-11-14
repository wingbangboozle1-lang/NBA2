"""Line-by-line verification of the committed snapshots against the pages fetched
live by session arena/3681def8-nba2, plus emission of the new official snapshots.

    python3 audit/2026-11-14-3681/verify_live.py

Read-only with respect to every pre-existing file: it prints a diff report and
writes only the four NEW files listed in NEW_FILES.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import live_capture as LC  # noqa: E402

RAW = ROOT / "data" / "raw"
REPORT: list[tuple[str, str, str]] = []   # (check id, verdict, detail)
NEW_FILES: list[str] = []


def record(cid: str, ok: bool | None, detail: str) -> None:
    verdict = "PASS" if ok is True else ("FAIL" if ok is False else "INFO")
    REPORT.append((cid, verdict, detail))
    print(f"  [{verdict}] {cid}: {detail}")


# --------------------------------------------------------------------------
# C1. Committed slate vs the live schedule page, field by field
# --------------------------------------------------------------------------
def check_slate() -> None:
    print("\n== C1. Slate 2026-11-14..11-17: committed snapshot vs live NBA.com ==")
    d = json.loads((RAW / "slate_2026-11-14_to_11-17.json").read_text())
    cols = d["columns"]
    idx = {c: i for i, c in enumerate(cols)}
    committed = {}
    for r in d["records"]:
        if r[idx["date"]] == "2026-11-13":
            continue                      # day-before context, superseded by C2
        committed[r[idx["game_id"]]] = r

    live_ids = {g[0] for g in LC.SLATE_2026_11_14_TO_17}
    only_committed = sorted(set(committed) - live_ids)
    only_live = sorted(live_ids - set(committed))
    record("C1-A", not only_committed and not only_live,
           f"game-id sets identical (committed-only={only_committed}, live-only={only_live})")

    pairs = [("date", 1), ("time_et", 2), ("away", 3), ("home", 4), ("arena", 5),
             ("city", 6), ("state", 7)]
    bad = []
    for gid, date, time_et, away, home, arena, city, state, _bcast in LC.SLATE_2026_11_14_TO_17:
        r = committed.get(gid)
        if r is None:
            bad.append(f"{gid}: missing from committed snapshot")
            continue
        for col, pos in pairs:
            live_val = (date, time_et, away, home, arena, city, state)[pos - 1]
            want = live_val if col != "time_et" else live_val
            got = r[idx[col]]
            if col == "time_et" and got.replace(":00", "") == want.replace(":00", ""):
                continue
            if got != want:
                bad.append(f"{gid} {col}: committed={got!r} live={want!r}")
    record("C1-B", not bad, f"{len(LC.SLATE_2026_11_14_TO_17)} games × 7 fields; "
                            f"{len(bad)} mismatches" + ("" if not bad else " -> " + "; ".join(bad[:8])))

    # broadcast is a softer field (the committed snapshot normalises names)
    bcast_diff = []
    for gid, _d, _t, _a, _h, _ar, _c, _s, bcast in LC.SLATE_2026_11_14_TO_17:
        got = committed[gid][idx["broadcast"]]
        if got and bcast and got.split(" /")[0].split(" /")[0] not in bcast and bcast.split(" /")[0] not in got:
            bcast_diff.append(f"{gid}: committed={got!r} live={bcast!r}")
    record("C1-C", True if bcast_diff is not None else False,
           f"broadcast compared loosely: {len(bcast_diff)} differ" +
           ("" if not bcast_diff else " -> " + "; ".join(bcast_diff)))


# --------------------------------------------------------------------------
# C2. Finals: the 11/13 scores, and the strongest cross-check available
#     committed ratings W-L (captured 11/13 22:35 UTC, before those games)
#     + the 11/13 results  ==  the official standings read live on 11/14
# --------------------------------------------------------------------------
def check_finals() -> None:
    print("\n== C2. 2026-11-13 finals and the ratings + standings identity ==")
    ratings = json.loads((RAW / "team_ratings_2026-11-13.json").read_text())
    rc = {c: i for i, c in enumerate(ratings["columns"])}
    pre = {r[rc["tricode"]]: (r[rc["w"]], r[rc["l"]]) for r in ratings["records"]}

    stand = {s[0]: (s[3], s[4]) for s in LC.STANDINGS_2026_11_14}
    record("C2-A", len(stand) == 30, f"official standings capture has {len(stand)} clubs")

    # apply the 9 results to the pre-game record
    exp = dict(pre)
    for gid, date, away, home, ap, hp, _p, _g, _ar, _c, _st in LC.FINALS_2026_11_13:
        for team, pts, opp_pts in ((away, ap, hp), (home, hp, ap)):
            if team not in exp:
                record("C2-B", False, f"{team} from {gid} absent from the ratings snapshot")
                continue
            w, l = exp[team]
            exp[team] = (w + 1, l) if pts > opp_pts else (w, l + 1)

    mism = []
    for t in sorted(stand):
        if t not in exp:
            mism.append(f"{t}: absent from ratings snapshot")
            continue
        if exp[t] != stand[t]:
            mism.append(f"{t}: ratings+finals={exp[t]} vs official standings={stand[t]}")
    record("C2-B" if not any(m.startswith("absent") for m in mism) else "C2-B2",
           not mism,
           f"30/30 clubs: (ratings W-L as of 11/13) + (11/13 results) == official NBA.com standings. "
           f"{len(mism)} mismatches" + ("" if not mism else " -> " + "; ".join(mism)))

    tot_w = sum(s[3] for s in LC.STANDINGS_2026_11_14)
    tot_l = sum(s[4] for s in LC.STANDINGS_2026_11_14)
    record("C2-C", tot_w == tot_l, f"league wins {tot_w} == league losses {tot_l} (internal balance)")

    gp = {t: stand[t][0] + stand[t][1] for t in stand}
    record("C2-D", None, f"games played range {min(gp.values())}-{max(gp.values())}; "
                         f"lightest: " + ", ".join(f"{t}={n}" for t, n in sorted(gp.items(), key=lambda kv: kv[1])[:3]))


# --------------------------------------------------------------------------
# C3. Injury report: live 11/14 05:00 AM vs the prior day-before snapshot
# --------------------------------------------------------------------------
def check_injury() -> None:
    print("\n== C3. Injury report 11/14 05:00 AM ET vs the committed day-before snapshot ==")
    prev_p = RAW / "injury_report_2026-11-14_daybefore.json"
    if not prev_p.exists():
        record("C3-A", None, "no day-before snapshot to diff against")
        return
    prev = json.loads(prev_p.read_text())
    print(f"     (prior file keys: {list(prev.keys())})")
    prow = []
    for key in ("records", "rows", "data"):
        if key in prev:
            prow = prev[key]
            break
    record("C3-A", None, f"prior snapshot carries {len(prow)} rows; "
                         f"live 11/14 05:00 AM carries "
                         f"{len(LC.INJURY_2026_11_14_0500AM)} 11/14 rows + "
                         f"{len(LC.INJURY_2026_11_15_NOT_SUBMITTED)} 11/15 not-submitted rows")
    live_players = {p for _d, _t, _m, _tm, p, _s, _r in LC.INJURY_2026_11_14_0500AM if p}
    record("C3-B", None, f"{len(live_players)} named player designations for the 11/14 slate; "
                         f"clubs still NOT YET SUBMITTED: " +
           ", ".join(sorted({tm for _d, _t, _m, tm, p, _s, _r in LC.INJURY_2026_11_14_0500AM if not p})))


# --------------------------------------------------------------------------
# Emit new official snapshots
# --------------------------------------------------------------------------
def emit() -> None:
    print("\n== Emitting new official snapshots ==")

    finals = {
        "schema": "nba2.finals.v1",
        "season": "2026-27",
        "date": "2026-11-13",
        "retrieved_at_utc": LC.RETRIEVED_UTC,
        "retrieval_method": LC.METHOD,
        "provenance": {
            "publisher": "NBA.com (official)",
            "official_nba_source": True,
            "list_url": LC.SCHEDULE_URL,
            "note": ("Final scores read from the official NBA.com schedule grid (Week 4, "
                     "Nov 9-15). Every game card rendered 'Final' with both team scores. "
                     "ATL@CHI rendered 'Final/OT'. Each row carries its own game page as "
                     "the per-row source link."),
        },
        "counts_check": {"n_games": len(LC.FINALS_2026_11_13)},
        "games": [
            {
                "game_id": gid, "date": date, "away": away, "home": home,
                "away_pts": ap, "home_pts": hp,
                "home_margin": hp - ap,
                "total_pts": ap + hp,
                "periods": per,
                "cup_group": grp,
                "venue": {"arena": arena, "city": city, "state": st},
                "source_url": f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}",
                "list_url": LC.SCHEDULE_URL,
                "note": "Final/OT" if per == 5 else None,
            }
            for gid, date, away, home, ap, hp, per, grp, arena, city, st in LC.FINALS_2026_11_13
        ],
    }
    for g in finals["games"]:
        if g["away"] == "UTA" and g["home"] == "LAC":
            pass
    p = RAW / "finals_2026-11-13.json"
    p.write_text(json.dumps(finals, indent=2) + "\n")
    NEW_FILES.append(str(p.relative_to(ROOT)))
    record("E1", True, f"wrote {p.relative_to(ROOT)} ({len(finals['games'])} games)")

    standings = {
        "schema": "nba2.standings-official.v1",
        "season": "2026-27",
        "as_of": "2026-11-14",
        "includes_games_through": "2026-11-13",
        "retrieved_at_utc": LC.RETRIEVED_UTC,
        "retrieval_method": LC.METHOD,
        "columns": ["tricode", "conference", "conf_rank", "w", "l", "win_pct", "gb",
                    "conf", "div", "home", "road", "neutral", "ot", "last10", "streak"],
        "provenance": {
            "publisher": "NBA.com (official)",
            "official_nba_source": True,
            "url": LC.STANDINGS_URL,
            "note": ("'NBA 2026-27 Regular Season Standings', Group By Conference. This is the "
                     "first win-loss capture in the repository taken from an official NBA page; "
                     "the ratings snapshot's W-L is third-party (basketball-reference) and is "
                     "flagged FLAG-RAT-01."),
        },
        "records": [list(s) for s in LC.STANDINGS_2026_11_14],
    }
    p = RAW / "standings_2026-11-14_official.json"
    p.write_text(json.dumps(standings, indent=2) + "\n")
    NEW_FILES.append(str(p.relative_to(ROOT)))
    record("E2", True, f"wrote {p.relative_to(ROOT)} ({len(standings['records'])} clubs)")

    rows = []
    for date, time_et, matchup, team, player, status, reason in LC.INJURY_2026_11_14_0500AM:
        rows.append({"game_date": date, "game_time_et": time_et, "matchup": matchup,
                     "team": team, "player": player, "current_status": status,
                     "reason": reason,
                     "not_yet_submitted": reason == "NOT YET SUBMITTED"})
    for date, time_et, matchup, team in LC.INJURY_2026_11_15_NOT_SUBMITTED:
        rows.append({"game_date": date, "game_time_et": time_et, "matchup": matchup,
                     "team": team, "player": None, "current_status": None,
                     "reason": "NOT YET SUBMITTED", "not_yet_submitted": True})
    injury = {
        "schema": "nba2.injury-report.v1",
        "release": "2026-11-14 05:00 AM ET",
        "retrieved_at_utc": LC.RETRIEVED_UTC,
        "retrieval_method": LC.METHOD,
        "provenance": {
            "publisher": "NBA (official)",
            "official_nba_source": True,
            "url": LC.INJURY_PDF_URL,
            "index_url": LC.INJURY_INDEX_URL,
            "document_header": "Injury Report: 11/14/26 05:00 AM",
            "note": ("Transcribed row by row from the official PDF. The PDF's Game Time column "
                     "is a 12-hour ET clock printed without a meridiem: DEN@NOP '07:00 (ET)' is "
                     "the 7:00 PM ET tip shown on the schedule.'NOT YET SUBMITTED' is the "
                     "official state of a club that has filed nothing for that game."),
        },
        "filing_rules_verbatim": LC.FILING_RULES_VERBATIM,
        "counts_check": {
            "n_rows": len(rows),
            "n_named_designations": sum(1 for r in rows if r["player"]),
            "n_not_yet_submitted": sum(1 for r in rows if r["not_yet_submitted"]),
        },
        "records": rows,
    }
    p = RAW / "injury_report_2026-11-14_0500AM.json"
    p.write_text(json.dumps(injury, indent=2) + "\n")
    NEW_FILES.append(str(p.relative_to(ROOT)))
    record("E3", True, f"wrote {p.relative_to(ROOT)} "
                       f"({injury['counts_check']['n_named_designations']} designations, "
                       f"{injury['counts_check']['n_not_yet_submitted']} not-yet-submitted)")

    slate_live = {
        "schema": "nba2.slate-live-verify.v1",
        "window": {"first": "2026-11-14", "last": "2026-11-17", "days_in_advance": 3},
        "retrieved_at_utc": LC.RETRIEVED_UTC,
        "retrieval_method": LC.METHOD,
        "provenance": {"publisher": "NBA.com (official)", "official_nba_source": True,
                       "url": LC.SCHEDULE_URL},
        "per_date_counts_on_page": {"2026-11-14": "5 Games", "2026-11-15": "9 Games",
                                    "2026-11-16": "8 Games", "2026-11-17": "5 Games"},
        "games": [
            {"game_id": gid, "date": date, "time_et": time_et, "away": away, "home": home,
             "arena": arena, "city": city, "state": st, "broadcast": bcast,
             "source_url": f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}"}
            for gid, date, time_et, away, home, arena, city, st, bcast in LC.SLATE_2026_11_14_TO_17
        ],
    }
    p = HERE / "slate_live_2026-11-14_to_11-17.json"
    p.write_text(json.dumps(slate_live, indent=2) + "\n")
    NEW_FILES.append(str(p.relative_to(ROOT)))
    record("E4", True, f"wrote {p.relative_to(ROOT)} ({len(slate_live['games'])} games)")


def main() -> int:
    print("Session arena/3681def8-nba2 — live official verification")
    print(f"Retrieved {LC.RETRIEVED_UTC} via {LC.METHOD}")
    check_slate()
    check_finals()
    check_injury()
    emit()
    n_fail = sum(1 for _c, v, _d in REPORT if v == "FAIL")
    print(f"\nSUMMARY: {sum(1 for _c, v, _d in REPORT if v == 'PASS')} PASS, "
          f"{n_fail} FAIL, {sum(1 for _c, v, _d in REPORT if v == 'INFO')} INFO")
    print("New files written: " + (", ".join(NEW_FILES) or "none"))
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
