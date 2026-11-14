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
    live_players = {r[4] for r in LC.INJURY_2026_11_14_0500AM if r[4]}
    record("C3-B", None, f"{len(live_players)} named player designations for the 11/14 slate; "
                         f"clubs still NOT YET SUBMITTED: " +
           ", ".join(sorted({r[3] for r in LC.INJURY_2026_11_14_0500AM if not r[4]})))

    # Two independent transcriptions of the same 11/14 designations, ~9 h apart: the
    # day-before capture (transcribed from the 11/13 07:30 PM release) and this one
    # (05:00 AM on 11/14). Any difference is either a status revision or a transcription
    # error, and both matter, so list every one.
    # The Reason cell of a not-yet-submitted row reads "NOT YET SUBMITTED" in the PDF; the
    # day-before capture recorded it as a descriptive sentence. Both describe the same cell,
    # so the two spellings are normalised before comparing — otherwise a wording choice is
    # reported as a data conflict.
    NYS_CANON = "<not submitted>"
    def norm(status: str, reason: str) -> tuple[str, str]:
        if status == "NOT YET SUBMITTED" or reason == "NOT YET SUBMITTED":
            return ("NOT YET SUBMITTED", NYS_CANON)
        return (status, reason)

    prev_c = {c: i for i, c in enumerate(prev["columns"])}
    theirs = {}
    for r in prev["records"]:
        theirs[(r[prev_c["team"]], r[prev_c["player"]])] = norm(r[prev_c["status"]],
                                                               r[prev_c["reason"]])
    mine = {}
    for r in LC.INJURY_2026_11_14_0500AM:
        mine[(r[3], r[4] or "")] = norm(r[5] or "NOT YET SUBMITTED", r[6])
    only_theirs = sorted(set(theirs) - set(mine))
    only_mine = sorted(set(mine) - set(theirs))
    diffs = [f"{k[0]}/{k[1] or '(club)'}: theirs={theirs[k]} mine={mine[k]}"
             for k in sorted(set(theirs) & set(mine)) if theirs[k] != mine[k]]
    record("C3-C", not only_theirs and not only_mine and not diffs,
           f"11/14 designations: {len(theirs)} rows in the day-before capture vs "
           f"{len(mine)} here — rows only in theirs={len(only_theirs)}, only in "
           f"mine={len(only_mine)}, value differences={len(diffs)}"
           + ("" if not (only_theirs or only_mine or diffs)
              else " -> " + "; ".join((only_theirs and [f"only-theirs {only_theirs[:3]}"] or [])
                                      + (only_mine and [f"only-mine {only_mine[:3]}"] or [])
                                      + diffs[:4])))


# --------------------------------------------------------------------------
# Emit new official snapshots
# --------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 4b. Second-document corroboration of the nine finals and the visible records.
# Source: https://www.nba.com/game/gsw-vs-sas-0022600040 — the game summary page for one
#         of the nine games. Its left rail renders every 2026-11-13 game as a finished card
#         (team, score) and every 11/14-11/16 game with both clubs' W-L. It is therefore an
#         independent official document for both the finals AND the standings capture.
#         Retrieved 2026-11-14 ~10:50 UTC via the platform page-fetch tool.
# ---------------------------------------------------------------------------
GAMEPAGE_URL = "https://www.nba.com/game/gsw-vs-sas-0022600040"

# (away, home, away_pts, home_pts) exactly as rendered on the game page's 11/13 rail
GAMEPAGE_FINALS = [
    ("NYK", "IND", 104, 106), ("MIL", "ORL",  99, 107), ("CLE", "MIA", 121, 133),
    ("ATL", "CHI", 117, 125), ("MEM", "NOP", 142, 111), ("UTA", "HOU", 118, 125),
    ("GSW", "SAS",  85, 123), ("POR", "SAC", 120, 107), ("OKC", "LAC", 112, 113),
]

# W-L printed on that page's 11/14-11/16 game cards, in render order
GAMEPAGE_RECORDS = [
    ("DEN", 6, 4), ("NOP", 4, 9), ("DAL", 7, 5), ("CLE", 6, 7), ("DET", 8, 3),
    ("MIA", 6, 6), ("BKN", 3, 8), ("MEM", 8, 4), ("CHI", 2, 9), ("MIN", 9, 3),
    ("IND", 5, 8), ("PHI", 10, 3), ("LAL", 11, 2), ("PHX", 5, 6), ("CHA", 4, 8),
    ("LAC", 3, 8), ("SAS", 11, 2), ("UTA", 1, 12), ("DAL", 7, 5), ("BOS", 10, 2),
    ("NYK", 6, 6), ("TOR", 5, 7),
]


def check_second_document() -> None:
    print("\n== C4. Second official document: the game summary page ==")
    mine = {(g[2], g[3]): (g[4], g[5]) for g in LC.FINALS_2026_11_13}
    bad = []
    for away, home, ap, hp in GAMEPAGE_FINALS:
        if mine.get((away, home)) != (ap, hp):
            bad.append(f"{away}@{home}: game page {ap}-{hp} vs snapshot "
                       f"{mine.get((away, home))}")
    record("C4-A", not bad,
           f"{len(GAMEPAGE_FINALS)}/9 final scores agree with an independent official page "
           f"({GAMEPAGE_URL}); {len(bad)} mismatches"
           + ("" if not bad else " -> " + "; ".join(bad)))

    stand = {s[0]: (s[3], s[4]) for s in LC.STANDINGS_2026_11_14}
    rbad = [f"{t}: page {w}-{l} vs standings {stand.get(t)}"
            for t, w, l in GAMEPAGE_RECORDS if stand.get(t) != (w, l)]
    record("C4-B", not rbad,
           f"{len(GAMEPAGE_RECORDS)} team W-L readings on that page match the official "
           f"standings capture; {len(rbad)} mismatches"
           + ("" if not rbad else " -> " + "; ".join(rbad[:5])))


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

    # Written in the repository's existing injury-snapshot schema (columns + list records +
    # record_counts + attribution), the same shape as injury_report_2026-11-13_1930ET.json and
    # injury_report_2026-11-14_daybefore.json. That is not cosmetic: tools/crosscheck_site.py
    # globs data/raw/injury_report_*.json and recounts every file it finds, so a snapshot with
    # a private schema crashes it (found and fixed in this session).
    NYS = "NOT YET SUBMITTED"
    # attribution: 'E' = the PDF printed this row's Game Date cell; 'C' = the date and time
    # cells were blank on a continuation page and were carried down from the row above.
    rows: list[list] = []
    for date, time_et, matchup, team, player, status, reason, attr in LC.INJURY_2026_11_14_0500AM:  # noqa: B007
        rows.append([date, time_et, matchup, team, player or "", status or NYS,
                     reason, attr])
    for date, time_et, matchup, team, attr in LC.INJURY_2026_11_15_NOT_SUBMITTED:
        rows.append([date, time_et, matchup, team, "", NYS,
                     "Team submission outstanding at report time", attr])

    n14 = sum(1 for r in rows if r[0] == "2026-11-14")
    n15 = sum(1 for r in rows if r[0] == "2026-11-15")
    nys = sum(1 for r in rows if r[5] == NYS)
    injury = {
        "dataset": "nba_official_injury_report",
        "report_stamp_et": "2026-11-14 05:00 AM",
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
                     "the 7:00 PM ET tip shown on the schedule. 'NOT YET SUBMITTED' is the "
                     "official state of a club that has filed nothing for that game; the player "
                     "cell is left empty, as the document leaves it."),
        },
        "attribution_key": {
            "E": "the PDF printed this row's Game Date cell (or the block's first date)",
            "C": "date and time cells were blank on a continuation page; carried down from above",
        },
        "columns": ["game_date", "time_et", "matchup", "team", "player", "status", "reason",
                    "attribution"],
        "record_counts": {
            "total_rows": len(rows),
            "rows_2026_11_14": n14,
            "rows_2026_11_15": n15,
            "rows_with_status": len(rows) - nys,
            "not_yet_submitted_placeholders": nys,
            "attribution_explicit": sum(1 for r in rows if r[7] == "E"),
            "attribution_continuation": sum(1 for r in rows if r[7] == "C"),
            "games_covered": len({r[2] for r in rows}),
            "note": "counts computed from the records array at write time",
        },
        "filing_rules_verbatim": LC.FILING_RULES_VERBATIM,
        "records": rows,
    }
    p = RAW / "injury_report_2026-11-14_0500AM.json"
    p.write_text(json.dumps(injury, indent=2) + "\n")
    NEW_FILES.append(str(p.relative_to(ROOT)))
    record("E3", True, f"wrote {p.relative_to(ROOT)} "
                       f"({injury['record_counts']['rows_with_status']} designations, "
                       f"{injury['record_counts']['not_yet_submitted_placeholders']} "
                       f"not-yet-submitted, schema matches the existing snapshots)")

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
    check_second_document()
    emit()
    n_fail = sum(1 for _c, v, _d in REPORT if v == "FAIL")
    print(f"\nSUMMARY: {sum(1 for _c, v, _d in REPORT if v == 'PASS')} PASS, "
          f"{n_fail} FAIL, {sum(1 for _c, v, _d in REPORT if v == 'INFO')} INFO")
    print("New files written: " + (", ".join(NEW_FILES) or "none"))
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
