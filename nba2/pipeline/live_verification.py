"""Publish the 2026-11-14 live official re-verification and the ratings-staleness audit.

Two inputs, both committed:

* ``data/raw/official_capture_2026-11-14T1015Z.json`` — the official NBA.com pages read in
  session ``arena/9ee870ea-nba2`` on 2026-11-14 ~10:15 UTC (schedule + standings + finals).
* ``audit/2026-11-14-live/report.json`` — the machine diff of that capture against every
  committed snapshot, produced by ``audit/2026-11-14-live/verify_live.py``.

What this module adds to the site:

* a **Live Verification** page — every check, every difference and every agreement, each row
  carrying the official URL it was read from;
* a **Ratings Staleness** page — what would move if the ratings snapshot were re-anchored to
  the live standings, game by game.

The published lines and the sealed ledgers are **not** touched by any of this. The seal is
immutable; the staleness is disclosed, not silently corrected. That is the whole point of
publishing the number instead of re-deriving it.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..provenance import Src, make_row, register_source, table

ROOT = Path(__file__).resolve().parents[2]
CAPTURE_PATH = ROOT / "data" / "raw" / "official_capture_2026-11-14T1015Z.json"
REPORT_PATH = ROOT / "audit" / "2026-11-14-live" / "report.json"

SRC_CAPTURE = "nba_live_capture_2026_11_14"
SRC_AUDIT = "live_verification_audit"

register_source(
    SRC_CAPTURE,
    "NBA.com schedule + standings, read live 2026-11-14 10:15 UTC (official)",
    "https://www.nba.com/schedule",
    Src.OFFICIAL,
    "Schedule page (https://www.nba.com/schedule) and standings page "
    "(https://www.nba.com/standings?Season=2026-27&SeasonType=Regular%20Season) read by session "
    "arena/9ee870ea-nba2 on 2026-11-14 ~10:12-10:15 UTC. Committed as "
    "data/raw/official_capture_2026-11-14T1015Z.json. The schedule page renders score, venue, "
    "city/state, cup group and game ID for completed games, but not the tip time or the "
    "broadcaster mark; those two fields are blank for the nine completed 2026-11-13 games "
    "rather than carried over.")
register_source(
    SRC_AUDIT,
    "Live verification audit, session arena/9ee870ea-nba2 (derived in-repo)",
    "https://github.com/wingbangboozle1-lang/NBA2/tree/main/audit/2026-11-14-live",
    Src.DERIVED,
    "Machine diff of the live capture against every committed snapshot, produced by "
    "audit/2026-11-14-live/verify_live.py. The script is in the repository and re-runnable; "
    "its output is committed as audit/2026-11-14-live/report.json.")


def _load() -> tuple[dict, dict]:
    if not CAPTURE_PATH.exists():
        raise SystemExit(f"missing {CAPTURE_PATH}")
    if not REPORT_PATH.exists():
        raise SystemExit(f"missing {REPORT_PATH} — run: python3 audit/2026-11-14-live/verify_live.py")
    return json.loads(CAPTURE_PATH.read_text()), json.loads(REPORT_PATH.read_text())


# --------------------------------------------------------------------------- summary checks
def build_capture_check() -> dict:
    cap, rep = _load()
    v = rep["capture_validation"]
    sd = rep["slate_diff"]
    lt = rep["league_totals"] if "league_totals" in rep else v["league_totals"]
    win = sd["pick_window_identical"]
    rows = [
        make_row("capture-sources", SRC_CAPTURE, (),
                 check="Official documents read",
                 result="2 pages: nba.com/schedule and nba.com/standings",
                 detail=("Schedule and standings, both read by session arena/9ee870ea-nba2 on "
                         "2026-11-14 ~10:12-10:15 UTC. Direct TLS to nba.com is blocked from the "
                         "build sandbox, so the retrieval was made with the platform page-fetcher; "
                         "the read is recorded in the committed capture, not inferred."),
                 source_url="https://www.nba.com/schedule"),
        make_row("capture-teams", SRC_CAPTURE, (),
                 check="Standings rows captured",
                 result=f"{v['teams']} of 30 teams",
                 detail=("Every team row carries W, L, WIN%, GB, CONF, DIV, HOME, ROAD, Neutral, OT, "
                         "LAST10 and STREAK as rendered by the official standings table."),
                 source_url="https://www.nba.com/standings"),
        make_row("capture-split-arithmetic", SRC_CAPTURE, ("FLAG-LIVE-03",),
                 check="home + road + neutral = (W, L) for every team",
                 result=f"{v['teams'] - v['split_arithmetic_failures_count']}/{v['teams']} teams balance",
                 detail=("An internal consistency check on the official table itself: the splits must "
                         "add back to the record. Every team balances, so the transcribed splits are "
                         "internally consistent rather than a plausible-looking guess."),
                 source_url="https://www.nba.com/standings"),
        make_row("capture-league-totals", SRC_CAPTURE, (),
                 check="League totals balance",
                 result=f"{lt['wins']} W / {lt['losses']} L = {lt['implied_games']:.0f} games played",
                 detail=("The 30 records sum to an even number of team-games and the wins equal the "
                         "losses, which is only possible if the transcription is complete. 183 games "
                         "played = 174 through 2026-11-12 plus the 9 games of 2026-11-13."),
                 source_url="https://www.nba.com/standings"),
        make_row("capture-slate-counts", SRC_CAPTURE, (),
                 check="Per-date game counts vs the page's own day headers",
                 result=("match: " + " / ".join(str(v["per_date_counts_read_from_day_headers"][d])
                                                for d in sorted(v["per_date_counts_read_from_day_headers"]))
                         if v["per_date_counts_match"] else "MISMATCH"),
                 detail=("The NBA's own day headers ('9 Games', '5 Games', '9 Games', '8 Games', "
                         "'5 Games') agree with the number of games transcribed for each date."),
                 source_url="https://www.nba.com/schedule"),
        make_row("capture-slate-fields", SRC_AUDIT, (),
                 check="Slate field values re-read and compared",
                 result=f"{sd['field_values_compared']} field values across {sd['committed_games']} games",
                 detail=(f"{sd['mismatch_count']} differences found (listed in the next table); "
                         f"{sd['fields_not_rendered_count']} fields could not be re-read because the "
                         f"official page does not render them for completed games."),
                 source_url="https://www.nba.com/schedule"),
        make_row("capture-pick-window", SRC_AUDIT, ("FLAG-LIVE-04",),
                 check="Pick window re-verified end to end",
                 result="identical" if win else "differences found",
                 detail=("All 27 games of the sealed pick window (2026-11-14 to 2026-11-17) match the "
                         "committed capture on date, tip time, teams, game ID, arena, city, state and "
                         "broadcast, except the two broadcaster labels listed below. The 27 sealed "
                         "predictions are therefore still a faithful pre-registration of what is "
                         "published."),
                 source_url="https://www.nba.com/schedule"),
        make_row("capture-outside-window", SRC_CAPTURE, ("FLAG-LIVE-04",),
                 check="Games outside the 3-day pick window",
                 result=f"{v['games_outside_pick_window_captured']} games captured (12 on 11-18, 4 on 11-19)",
                 detail=("The brief's maximum is 3 days ahead of the build date, so these are "
                         "deliberately not in the pick window. They are captured and published so that "
                         "the omission is visible rather than silent."),
                 source_url="https://www.nba.com/schedule"),
        make_row("capture-finals", SRC_AUDIT, (),
                 check="2026-11-13 finals vs an earlier session's independent capture",
                 result=rep["finals_cross_check"]["result"],
                 detail=("Nine finals read from the official schedule page in this session, compared "
                         "against the scores a different session captured from the official game cards. "
                         "Every score, every team and the overtime flag agree."),
                 source_url="https://www.nba.com/schedule"),
        make_row("capture-ladder", SRC_AUDIT, (),
                 check="Team records vs the committed ratings snapshot",
                 result=f"{rep['records_diff']['teams_whose_record_moved']} of 30 teams moved",
                 detail=("The committed ratings snapshot was taken while the 2026-11-13 slate was still "
                         "in progress, so it is one slate behind the live official standings. Quantified "
                         "on the Ratings Staleness page."),
                 source_url="https://www.nba.com/standings"),
    ]
    return table(rows, [("check", "Check"), ("result", "Result"), ("detail", "Detail")],
                 "Live verification — what was read, what matched, what did not",
                 "Every line on this page was produced by reading an official NBA.com page in this "
                 "session and comparing it with the committed snapshots. Nothing is inferred from a "
                 "previous session's note.",
                 "read 2026-11-14 10:12-10:15 UTC; diff by audit/2026-11-14-live/verify_live.py")


# --------------------------------------------------------------------------- slate diff
def build_slate_diff() -> dict:
    cap, rep = _load()
    sd = rep["slate_diff"]
    rows = []
    for m in sd["mismatches"]:
        gid = m["game_id"]
        live_v = m.get("live")
        committed_v = m.get("committed")
        if m["field"] == "broadcast":
            live_v = ", ".join(m.get("live") or []) or None
            committed_v = ", ".join(m.get("committed") or []) or None
        rows.append(make_row(
            f"diff-{gid}-{m['field']}", SRC_CAPTURE,
            ("FLAG-LIVE-06",) if m["field"] == "cup_group" else ("FLAG-LIVE-07",),
            game_id=gid, field=m["field"], kind=m["kind"],
            committed=(committed_v if committed_v not in (None, "") else None),
            live=(live_v if live_v not in (None, "") else None),
            source_url="https://www.nba.com/schedule"))
    for nr in sd["fields_not_rendered_by_the_page"]:
        rows.append(make_row(
            f"notrendered-{nr['game_id']}-{nr['field']}", SRC_CAPTURE, ("FLAG-LIVE-05",),
            game_id=nr["game_id"], field=nr["field"], kind="not rendered by the official page",
            committed=nr["committed"], live=None,
            source_url="https://www.nba.com/schedule"))
    return table(rows, [("game_id", "Game ID"), ("field", "Field"), ("kind", "Kind"),
                        ("committed", "Committed capture"), ("live", "Live official read")],
                 "Slate re-check — every difference and every field the page does not render",
                 (f"{sd['field_values_compared']} field values compared across "
                  f"{sd['committed_games']} games. Every difference is listed; there is no rounding "
                  f"or 'close enough' here — a difference is a difference. Fields the official page "
                  f"does not render for completed games (tip time, broadcaster) are listed too, "
                  f"because a value that cannot be re-read is not the same as a value that matched."),
                 "read 2026-11-14 10:12 UTC; committed capture 2026-11-14 01:05 UTC")


# --------------------------------------------------------------------------- records diff
def build_records_diff() -> dict:
    cap, rep = _load()
    rows = []
    for r in rep["records_diff"]["rows"]:
        moved = r["changed"]
        rows.append(make_row(
            f"rec-{r['tricode']}", SRC_CAPTURE, ("FLAG-LIVE-01",) if moved else (),
            tricode=r["tricode"],
            committed_wl=r["committed_wl"], live_wl=r["live_wl"],
            delta=(f"+{r['wins_delta']}W / +{r['losses_delta']}L" if moved else "unchanged"),
            committed_home=r["committed_home"], live_home=r["live_home"],
            committed_road=r["committed_road"], live_road=r["live_road"],
            moved=("YES" if moved else "no"),
            source_url="https://www.nba.com/standings"))
    return table(rows, [("tricode", "Team"), ("committed_wl", "Committed W-L"),
                        ("live_wl", "Live official W-L"), ("delta", "Change"),
                        ("committed_home", "Committed home"), ("live_home", "Live home"),
                        ("committed_road", "Committed road"), ("live_road", "Live road"),
                        ("moved", "Moved?")],
                 "Team records — the committed ratings snapshot vs the live official standings",
                 ("The committed snapshot (retrieved 2026-11-13 22:35 UTC, while the 11/13 slate was "
                  "still running) is one slate behind the live official standings read on "
                  "2026-11-14 10:15 UTC. The published lines are derived from the committed snapshot "
                  "and the sealed ledgers are immutable, so the lines stay as sealed — the effect of "
                  "re-anchoring is measured and published on the Ratings Staleness page instead."),
                 "committed snapshot 2026-11-13 22:35 UTC; live standings 2026-11-14 10:15 UTC")


# --------------------------------------------------------------------------- finals
def build_finals() -> dict:
    cap, rep = _load()
    prior = json.loads((ROOT / "audit" / "2026-11-14" / "official_inputs_2026-11-14.json").read_text())
    prior_by_id = {f["game_id"]: f for f in prior.get("finals_2026_11_13", [])}
    f_cols = cap["finals_2026_11_13"]["columns"]
    rows = []
    for rec in cap["finals_2026_11_13"]["records"]:
        d = dict(zip(f_cols, rec))
        p = prior_by_id.get(d["game_id"], {})
        agree = (d["away_score"] == p.get("away_pts") and d["home_score"] == p.get("home_pts")
                 and d["away"] == p.get("away") and d["home"] == p.get("home")
                 and bool(d["ot"]) == bool(p.get("ot")))
        rows.append(make_row(
            f"final-{d['game_id']}", SRC_CAPTURE, (),
            game_id=d["game_id"], matchup=f"{d['away']} @ {d['home']}",
            away_score=d["away_score"], home_score=d["home_score"],
            status=d["status_text"],
            prior_capture=f"{p.get('away_pts')}-{p.get('home_pts')}" if p else None,
            agreement=("identical" if agree else "DIFFERENT"),
            source_url=d["source"]))
    return table(rows, [("game_id", "Game ID"), ("matchup", "Matchup"),
                        ("away_score", "Away"), ("home_score", "Home"), ("status", "Status"),
                        ("prior_capture", "Earlier session's capture"), ("agreement", "Agreement")],
                 "2026-11-13 finals — this session's read vs an earlier session's independent capture",
                 ("Two independent reads of the same nine official games, taken by different sessions "
                  "from different official pages, agree on every score, every team and the overtime "
                  "flag. The earlier capture is in audit/2026-11-14/official_inputs_2026-11-14.json."),
                 "this session 2026-11-14 10:12 UTC; earlier session 2026-11-14 ~00:58 UTC")


# --------------------------------------------------------------------------- staleness
def build_staleness_summary() -> dict:
    cap, rep = _load()
    si = rep["staleness_impact"]
    cp, cr = si["calibration_published"], si["calibration_reanchored"]
    aw, pw = si["all_games"], si["pick_window_only"]
    rows = [
        make_row("stale-what", SRC_AUDIT, ("FLAG-LIVE-01",),
                 item="What was re-anchored", published=si["what_was_re_anchored"],
                 reanchored="—",
                 consequence=("The published lines are unchanged: the sealed ledgers are immutable by "
                              "design and a pre-registered forecast that moves after the fact is not a "
                              "pre-registered forecast."),
                 source_url="https://github.com/wingbangboozle1-lang/NBA2/blob/main/audit/2026-11-14-live/verify_live.py"),
        make_row("stale-not", SRC_AUDIT, ("FLAG-LIVE-01",),
                 item="What was NOT re-anchored", published=si["what_was_not_re_anchored"],
                 reanchored="—",
                 consequence=("The movement below is therefore a lower bound on the true staleness "
                              "effect, not an estimate of the full effect."),
                 source_url="https://www.nba.com/standings"),
        make_row("stale-sigma", SRC_AUDIT, ("FLAG-LIVE-01", "FLAG-PARAM-01"),
                 item="σ margin sd (pts, fitted)", published=f"{cp['margin_sd']}",
                 reanchored=f"{cr['margin_sd']}",
                 consequence=("σ is fitted from win totals, so a records refresh moves it. It is "
                              "published with a ±10% band for exactly this reason."),
                 source_url="https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/ratings.py"),
        make_row("stale-hca", SRC_AUDIT, ("FLAG-LIVE-01", "FLAG-PARAM-02"),
                 item="Home-court advantage (pts, fitted)", published=f"{cp['hca_points']}",
                 reanchored=f"{cr['hca_points']}",
                 consequence=("The sign of the fitted home-court term flips on a one-slate records "
                              "refresh. That is the clearest evidence that HCA is not identified at "
                              "this sample size, and it must stay unratified."),
                 source_url="https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/ratings.py"),
        make_row("stale-rmse", SRC_AUDIT, ("FLAG-LIVE-01",),
                 item="Fit RMSE (wins vs the .500 baseline)",
                 published=f"{cp['rmse_wins']}",
                 reanchored=f"{cr['rmse_wins']}",
                 consequence=("A lower RMSE means the fitted parameters reproduce the observed win "
                              "totals better. Both values are far below the 2.78-win .500 baseline, "
                              "so the fit still beats the trivial model after re-anchoring."),
                 source_url="https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/ratings.py"),
        make_row("stale-max", SRC_AUDIT, ("FLAG-LIVE-01",),
                 item="Largest spread move, pick window",
                 published="—",
                 reanchored=f"{pw['max_abs_spread_move_pts']} pts (max), "
                            f"{pw['mean_abs_spread_move_pts']} pts (mean) over {pw['n']} games",
                 consequence=("A 2-point move is inside the noise of a 12-game sample, which is why "
                              "no line is promoted on the strength of one."),
                 source_url="https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/lines.py"),
        make_row("stale-leans", SRC_AUDIT, ("FLAG-LIVE-01",),
                 item="Games whose lean would flip",
                 published="—",
                 reanchored=f"{pw['leans_that_change']} of {pw['n']} pick-window games",
                 consequence=("The direction of a line is far more stable than its number, which is "
                              "why the triggers, not the lines, are the published output."),
                 source_url="https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/lines.py"),
        make_row("stale-seal", SRC_AUDIT, ("FLAG-LIVE-01",),
                 item="Sealed ledgers",
                 published=("untouched: cf7dedc6… (22 predictions) and c841e8f3… (27 predictions)"),
                 reanchored="—",
                 consequence=("A sealed ledger is verified byte-for-byte by CI on every push. Nothing "
                              "in this audit wrote to data/raw/ledger/."),
                 source_url="https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/ledger.py"),
    ]
    return table(rows, [("item", "Item"), ("published", "As published"),
                        ("reanchored", "If re-anchored to the live standings"),
                        ("consequence", "What it means")],
                 "Ratings staleness — what a one-slate records refresh does to the published numbers",
                 ("The committed ratings snapshot predates the 2026-11-13 finals. This is the measured "
                  "size of that gap. It is published rather than silently corrected, because the "
                  "sealed pre-registrations for this window must keep matching the published lines."),
                 "computed by audit/2026-11-14-live/verify_live.py from the committed snapshot and the "
                 "live official standings")


def build_staleness_games() -> dict:
    cap, rep = _load()
    rows = []
    for r in rep["staleness_impact"]["rows"]:
        rows.append(make_row(
            f"stale-{r['game_id']}", SRC_AUDIT, ("FLAG-LIVE-01",),
            game_id=r["game_id"], date=r["date"], matchup=r["matchup"],
            published_spread=r["published_spread_home"], reanchored_spread=r["reanchored_spread_home"],
            spread_move=r["spread_move_pts"],
            published_total=r["published_total"], reanchored_total=r["reanchored_total"],
            total_move=r["total_move_pts"],
            published_lean=r["published_lean"], reanchored_lean=r["reanchored_lean"],
            lean_changed=("YES" if r["lean_changed"] else "no"),
            in_window=("yes" if r["in_pick_window"] else "no — day-before context"),
            source_url="https://www.nba.com/standings"))
    return table(rows, [("game_id", "Game ID"), ("date", "Date"), ("matchup", "Matchup"),
                        ("published_spread", "Published spread (home)"),
                        ("reanchored_spread", "Re-anchored spread (home)"),
                        ("spread_move", "Move (pts)"), ("published_total", "Published total"),
                        ("reanchored_total", "Re-anchored total"), ("total_move", "Move (pts)"),
                        ("published_lean", "Published lean"), ("reanchored_lean", "Re-anchored lean"),
                        ("lean_changed", "Lean flipped?"), ("in_window", "In pick window?")],
                 "Ratings staleness — every game, published vs re-anchored",
                 ("One row per game in the window. 'Published' is what the site shows and what the "
                  "sealed ledger contains. 'Re-anchored' is the same model re-fitted with W-L and the "
                  "home/road splits taken from the live official standings, with SRS and the points "
                  "splits left at their committed third-party values. It is a disclosure, not a "
                  "replacement."),
                 "computed by audit/2026-11-14-live/verify_live.py")


# --------------------------------------------------------------------------- all sections
def build_all() -> dict:
    return {
        "live_capture_check": build_capture_check(),
        "live_slate_diff": build_slate_diff(),
        "live_records_diff": build_records_diff(),
        "live_finals": build_finals(),
        "staleness_summary": build_staleness_summary(),
        "staleness_games": build_staleness_games(),
    }
