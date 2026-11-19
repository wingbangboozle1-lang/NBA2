"""What was compared, line by line, against which official page — and the result.

The brief asks for verification against official sources with links, and for anything that
cannot be confirmed to be left blank and flagged. This module is the ledger of that work: one
row per claim, the official page it was checked against, how many items were compared, and
whether all of them matched.

Only rows actually checked in this session appear. A row whose source was not reachable is not
in this table — it is on the Flagged for Review page instead, because a verification table that
lists unverified things as verified is worse than no table.

Each row also carries the arithmetic identity that makes the check re-runnable rather than a
claim of good faith: identities live in :mod:`nba2.v7.test_v7`, and if a transcription drifts
the test fails and the build stops.
"""

from __future__ import annotations

from . import official as O

# (id, claim, what was compared, n compared, matched, official page, method)
CHECKS = [
    ("V-01", "2026-11-18 finals",
     "date, both clubs and both final scores, game by game",
     12, 12, "https://www.nba.com/games?date=2026-11-18",
     "read each game page linked from the date's game list"),
    ("V-02", "2026-11-19 slate",
     "clubs, game id and tip time for all four games",
     4, 4, O.SOURCES["games_1119"],
     "date filter on the official game list"),
    ("V-03", "2026-11-20 slate and NBA Cup groups",
     "clubs, game ids, tip times and the Cup group label where one is shown",
     6, 6, O.SOURCES["games_1120"],
     "date filter; six games were in the fetched span, the rest were not reached"),
    ("V-04", "standings, both conferences",
     "wins and losses for 15 clubs spanning the table",
     15, 15, O.SOURCES["standings"],
     "spot check across East and West, not a full 30-club re-read"),
    ("V-05", "advanced team stats",
     "OffRtg, DefRtg, NetRtg and PACE for every club",
     30, 30, O.SOURCES["advanced"],
     "NetRtg = OffRtg - DefRtg holds on all 30 to +/-0.15 (rounding)"),
    ("V-06", "traditional team stats",
     "points per game and the plus/minus column for every club",
     30, 30, O.SOURCES["traditional"],
     "PTS - OppPTS = +/- holds on all 30 to +/-0.20 (rounding)"),
    ("V-07", "opponent team stats",
     "opponent points per game for every club",
     30, 30, O.SOURCES["opponent"],
     "cross-checked against the traditional page's plus/minus identity"),
    ("V-08", "results reconcile to the standings",
     "each club's win total in the committed finals against its standings record",
     30, 30, O.SOURCES["standings"],
     "222 committed finals grouped by club; no club disagrees"),
    ("V-09", "measured constants",
     "home-win rate, margin sd, points-per-possession inputs re-derived from the finals",
     210, 210, "https://www.nba.com/games?date=2026-10-20",
     "the 210-game window 2026-10-20 to 2026-11-17, recomputed from raw finals only"),
    ("V-10", "injury report",
     "the 2026-11-19 report and its revision time",
     0, 0, O.SOURCES["injury"],
     "NOT READ - published as a blank with F-V7-AVAIL, not as a verified value"),
    # ---------------------------------------------------------------------------------
    # Independent re-read by the integration session (arena/585453f5-nba2) on
    # 2026-11-19, after this transcription was committed. These rows test the committed
    # numbers against the official pages again, rather than against themselves.
    ("V-11", "advanced team stats, re-read",
     "GP, W, L, OffRtg, DefRtg, NetRtg and PACE for 27 of 30 clubs, compared against the "
     "transcription in nba2/v7/official.py",
     27, 27, O.SOURCES["advanced"],
     "integrated re-read 2026-11-19T12:20Z: every one of the 27 rows matched to the printed "
     "decimal; the three clubs absent from the fetched pages (MIN, SAC, and the 30th row cut "
     "off by pagination) were not re-compared and are therefore not counted"),
    ("V-12", "standings, re-read",
     "wins and losses for 26 clubs, cross-checked against the transcription",
     26, 26, O.SOURCES["standings"],
     "integrated re-read 2026-11-19T12:18Z: 26/26 matched, including the two-conference split"),
    ("V-13", "2026-11-19 and 2026-11-20 slates, re-read",
     "clubs, game ids and tip times for the 4 games on 11/19 and 9 games on 11/20",
     13, 13, O.SOURCES["games_1120"],
     "integrated re-read 2026-11-19T12:22Z: all 13 game ids and tip times matched; the 11/20 "
     "page also confirms the Cup-group labels used in the slate"),
]


def build() -> dict:
    rows = []
    for cid, claim, what, n, matched, url, method in CHECKS:
        rows.append({"id": cid, "claim": claim, "compared": what, "n": n,
                     "matched": matched, "ok": n == matched and n > 0,
                     "not_read": n == 0, "source": url, "method": method})
    total = sum(r["n"] for r in rows)
    matched = sum(r["matched"] for r in rows)
    return {"rows": rows, "n_compared": total, "n_matched": matched,
            "n_claims": len(rows),
            "n_not_read": sum(1 for r in rows if r["not_read"]),
            "all_matched": all(r["ok"] for r in rows if not r["not_read"])}
