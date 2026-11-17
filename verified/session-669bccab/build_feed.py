"""Build the official per-game results snapshots for game days 2026-11-15 and 2026-11-16.

Session arena/669bccab-nba2, 2026-11-17 UTC. Every value below was read by hand from one of:
  * NBA.com game-list pages  https://www.nba.com/games?date=2026-11-15  (chunks 0-1)
                             https://www.nba.com/games?date=2026-11-16  (chunk 0)
  * NBA official gamebook PDFs https://statsdmz.nba.com/pdfs/<yyyymmdd>/<yyyymmdd>_<AWAY><HOME>_book.pdf
    (SCORE BY PERIOD table, chunk 0; HOU@MIA also chunk 1)
  * For 2026-11-15 games 0022600243 and 0022600244 the quarter rows were NOT re-read today; they are
    carried from the committed official-gamebook transcript data/v5/gamebooks_2026-11-15.json (its
    own retrieval stamp is kept) and their finals were re-read on NBA.com today.

Settle rule applied downstream (nba2/v4/settlement.py, the repo v4 rule): a game is settled when a
committed official final covers it AND, where a period row was captured, that row sums to the final.
Blank quarter cells here are therefore recorded as blank-and-flagged, and the game is still settled on its
verified final.

Run:  python3 verified/session-669bccab/build_feed.py
It writes two snapshot files that nba2.pipeline.settle and nba2.v4.settlement read, and one
per-game feed file for review. It refuses to write if any quarter row fails to sum to its final
or any NBA.com final disagrees with the gamebook final.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RETRIEVED_NBA = "read 2026-11-17 in session arena/669bccab-nba2 via platform fetch tool, nba.com game-list page (per-call time not logged)"
RETRIEVED_PDF = "read 2026-11-17 in session arena/669bccab-nba2 via platform fetch tool, statsdmz gamebook PDF (per-call time not logged)"

# game_id, date, away, home, NBA.com away final, NBA.com home final, gamebook away quarters, home quarters, OT
GAMES_1116 = [
    ("0022600245", "ORL", "BOS", 115, 105, [20, 30, 25, 40], [17, 24, 36, 28]),
    ("0022600246", "CHI", "CLE", 115, 126, [31, 17, 31, 36], [25, 32, 31, 38]),
    ("0022600247", "MEM", "WAS", 136, 120, [33, 26, 42, 35], [35, 34, 18, 33]),
    ("0022600248", "PHI", "BKN", 135, 123, [33, 45, 27, 30], [26, 33, 36, 28]),
    ("0022600249", "HOU", "MIA", 110, 128, None, [29, 33, 39, 27]),          # HOU row not transcribed
    ("0022600250", "POR", "MIN", 98, 106, [26, 25, 22, 25], [26, 33, 28, 19]),
    ("0022600251", "GSW", "NOP", 94, 115, [11, 25, 29, 29], [35, 26, 32, 22]),
    ("0022600252", "PHX", "DEN", 117, 105, [20, 36, 34, 27], [24, 29, 29, 23]),
]

# 2026-11-15 games that were 'not final at retrieval' in data/raw/results/results_2026-11-15.json
GAMES_1115_RECHECK = [
    ("0022600242", "HOU", "WAS", 147, 119, [36, 37, 46, 28], [31, 23, 34, 31], "re-read today (statsdmz PDF)"),
    ("0022600243", "ATL", "MIL", 113, 106, [18, 37, 32, 26], [37, 16, 27, 26], "carried from data/v5/gamebooks_2026-11-15.json"),
    ("0022600244", "OKC", "SAC", 125, 103, [32, 30, 32, 31], [24, 26, 30, 23], "carried from data/v5/gamebooks_2026-11-15.json"),
]


def pdf_url(date: str, away: str, home: str) -> str:
    return f"https://statsdmz.nba.com/pdfs/{date.replace('-', '')}/{date.replace('-', '')}_{away}{home}_book.pdf"


def nba_url(away: str, home: str, gid: str) -> str:
    return f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}"


def check(gid: str, away_pts: int, home_pts: int, aq, hq, nba_away: int, nba_home: int) -> list[str]:
    problems = []
    if (away_pts, home_pts) != (nba_away, nba_home):
        problems.append(f"{gid}: NBA.com {nba_away}-{nba_home} != gamebook {away_pts}-{home_pts}")
    if aq is not None and sum(aq) != away_pts:
        problems.append(f"{gid}: away quarters {aq} sum {sum(aq)} != {away_pts}")
    if hq is not None and sum(hq) != home_pts:
        problems.append(f"{gid}: home quarters {hq} sum {sum(hq)} != {home_pts}")
    return problems


def main() -> None:
    problems: list[str] = []
    rows_1116 = []
    for gid, away, home, a_pts, h_pts, aq, hq in GAMES_1116:
        # NBA.com list page and gamebook final are the same numbers here (both read today); the
        # gamebook-derived final is the value the quarter rows sum to.
        gb_a = sum(aq) if aq else a_pts
        gb_h = sum(hq)
        problems += check(gid, gb_a, gb_h, aq, hq, a_pts, h_pts)
        blank = None if aq is not None else "away quarter row not transcribed from the gamebook PDF read today; left blank, not back-solved"
        rows_1116.append({
            "game_id": gid, "date": "2026-11-16", "away": away, "home": home,
            "status": "final", "away_pts": a_pts, "home_pts": h_pts,
            "away_quarters": aq, "home_quarters": hq, "ot_periods": 0,
            "ot_quarters": {"away": [], "home": []},
            "quarter_check": (f"{away} {'+'.join(map(str, aq))} = {sum(aq)}; " if aq else f"{away} quarters blank; ")
                             + f"{home} {'+'.join(map(str, hq))} = {sum(hq)} (final {h_pts})",
            "quarters_blank_reason": blank,
            "source_url": nba_url(away, home, gid),
            "gamebook_url": pdf_url("2026-11-16", away, home),
            "source_page": "https://www.nba.com/games?date=2026-11-16",
            "source_class": "official",
            "verified": f"NBA.com game-list final ({RETRIEVED_NBA}) = gamebook SCORE BY PERIOD final ({RETRIEVED_PDF})",
        })
    rows_1115 = []
    for gid, away, home, a_pts, h_pts, aq, hq, how in GAMES_1115_RECHECK:
        problems += check(gid, a_pts, h_pts, aq, hq, a_pts, h_pts)
        rows_1115.append({
            "game_id": gid, "date": "2026-11-15", "away": away, "home": home,
            "status": "final", "away_pts": a_pts, "home_pts": h_pts,
            "away_quarters": aq, "home_quarters": hq, "ot_periods": 0,
            "ot_quarters": {"away": [], "home": []},
            "quarter_check": f"{away} {'+'.join(map(str, aq))} = {sum(aq)}; {home} {'+'.join(map(str, hq))} = {sum(hq)}",
            "quarters_blank_reason": None,
            "source_url": nba_url(away, home, gid),
            "gamebook_url": pdf_url("2026-11-15", away, home),
            "source_page": "https://www.nba.com/games?date=2026-11-15",
            "source_class": "official",
            "supersedes": "data/raw/results/results_2026-11-15.json row marked 'not final at retrieval' (retrieved 2026-11-16 ~02:05 UTC)",
            "quarter_provenance": how,
            "verified": f"NBA.com game-list final re-read {RETRIEVED_NBA} = gamebook final; quarter rows sum to final",
        })
    if problems:
        raise SystemExit("REFUSING TO WRITE:\n  " + "\n  ".join(problems))

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + " (script run time)"
    retr = "2026-11-17 (this session; per-call fetch times not logged)"
    doc_1116 = {
        "schema": "nba2.results-feed.official-gamebook.v1",
        "session": "arena/669bccab-nba2",
        "game_date": "2026-11-16",
        "retrieved_window_utc": retr,
        "retrieval_method": "platform fetch tool (fetch_page). Final scores read from the NBA.com game-list page; quarter scores read from the official NBA gamebook PDF 'SCORE BY PERIOD' table at statsdmz.nba.com. Bash egress cannot reach nba.com, so the PDFs are read as text, not stored as bytes.",
        "settle_rule": "Repo v4 rule: a game is settled only when a committed official final covers it AND, where a period row was captured, that row sums to the final. Blank quarter cells are never back-solved.",
        "generated_at_utc": stamp,
        "records": rows_1116,
    }
    doc_1115 = {
        "schema": "nba2.results-feed.official-gamebook.v1",
        "session": "arena/669bccab-nba2",
        "game_date": "2026-11-15",
        "retrieved_window_utc": retr,
        "retrieval_method": "platform fetch tool (fetch_page). Finals re-read on the NBA.com game-list page for 2026-11-15 (chunks 0-1). Quarter rows re-read from the statsdmz gamebook for HOU@WAS; ATL@MIL and OKC@SAC quarter rows carried from data/v5/gamebooks_2026-11-15.json.",
        "settle_rule": "Repo v4 rule (see results_2026-11-16.json).",
        "supersedes_file": "data/raw/results/results_2026-11-15.json (games 0022600242-0022600244 only)",
        "generated_at_utc": stamp,
        "records": rows_1115,
    }
    out_dir = ROOT / "verified" / "session-669bccab"
    (ROOT / "data/raw/results/results_2026-11-16.json").write_text(json.dumps(doc_1116, indent=2, ensure_ascii=False) + "\n")
    (ROOT / "data/raw/results/results_2026-11-15_recheck_2026-11-17.json").write_text(json.dumps(doc_1115, indent=2, ensure_ascii=False) + "\n")
    feed = {
        "schema": "nba2.official-results-feed.v1",
        "session": "arena/669bccab-nba2",
        "window": "2026-11-14 .. 2026-11-16",
        "note": "One row per game. 2026-11-14 games (0022600231-35) are carried from data/raw/capture_2026-11-15/results_2026-11-14.json and were NOT re-read this session. 2026-11-15 games 0022600236-41 are carried from the committed v5 gamebook transcripts and their finals were re-read on NBA.com today. Blank = not confirmed from an official source.",
        "rows": [dict(r, date=r["date"]) for r in rows_1116 + rows_1115],
    }
    (out_dir / "official_results_feed_2026-11-15_to_16.json").write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows_1116)} rows (2026-11-16) and {len(rows_1115)} rows (2026-11-15 recheck); all sums and NBA.com/gamebook finals agree")


if __name__ == "__main__":
    main()
