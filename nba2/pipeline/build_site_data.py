"""Assemble every site table from the verified snapshots.

Invariants enforced here (and re-checked by `lint.py`):
* every row carries a source; a row whose source is not NBA-official carries >= 1 flag;
* an unknown value is `None` (rendered blank), never a placeholder;
* nothing is reported as measured unless a measurement object exists for it.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .. import config
from . import adjudicate as ADJ
from . import reconcile as XSESS
from ..models import correlation as corr
from ..models import gates as G
from ..models import injuries as INJ
from ..models import gameflow as GF
from ..models import leaderboard as LB
from ..models import lines as LN
from ..models import props as PR
from ..models import ratings as RT
from ..provenance import SOURCES, Row, Src, all_flags, flag, make_row, register_source, table

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
OUT = DATA / "site.json"
PREVIEW_VERIFIED = set(json.loads((RAW / config.SNAPSHOT_SLATE).read_text())["preview_verified_game_ids"])

SRC_SLATE = "nba_schedule"
SRC_GAMES = "nba_games"
SRC_INJ = "nba_injury_pdf"
SRC_INJ_W = "nba_injury_pdf_1114"
SNAPSHOT_INJURY_WINDOW = "injury_report_2026-11-14_daybefore.json"
SRC_RAT = "bref_standings"
SRC_DER = "derived_lines"
SRC_DER_RAT = "derived_ratings"
SRC_DER_CORR = "derived_corr"
SRC_COORD = "coordination"
SRC_GIT = "git_repo"

# Sources added by session arena/72f9da58 (2026-11-14 verification round).
SRC_INJ_LATEST = "nba_injury_pdf_latest"
SRC_STANDINGS = "nba_standings"
SRC_GAME_ANOM = "nba_game_page_1117"
SRC_AUDIT = "session_audit"

# Sources added by session arena/6650be4d-nba2 (2026-11-14 10:25 UTC re-verification).
SRC_STANDINGS_OFFICIAL = "nba_standings_official"
SRC_INJ_0500 = "nba_injury_pdf_0500"
SRC_FINALS = "nba_games_finals"

register_source(
    SRC_INJ_LATEST,
    "NBA Official Injury Report 11/13 19:15 ET (official)",
    "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_15PM.pdf",
    Src.OFFICIAL,
    "Latest official revision this session could fetch (2026-11-14 ~01:20 UTC). A 20:15 ET "
    "revision does not exist (CDN AccessDenied). Retrieved via the page fetcher; full text captured "
    "in audit/raw_injury_2026-11-13_0715PM_chunk{0,1}.md. The published site rows now come from the "
    "later official 19:30 ET release, ingested by the 2026-11-14 refresh.")
register_source(
    SRC_STANDINGS,
    "NBA.com Standings (official)",
    "https://www.nba.com/standings",
    Src.OFFICIAL,
    "2026-27 regular-season standings, all 30 teams' W-L. Retrieved 2026-11-14 ~01:00 UTC.")
register_source(
    SRC_GAME_ANOM,
    "NBA.com Game Page NYK @ TOR 11/17 (official)",
    "https://www.nba.com/game/nyk-vs-tor-0022600253",
    Src.OFFICIAL,
    "Game summary page for the 2026-11-17 repeat matchup; used to adjudicate FLAG-ANOM-01.")
register_source(
    SRC_AUDIT,
    "Session verification artefacts (arena/72f9da58, arena/fc58f84f)",
    "https://github.com/wingbangboozle1-lang/NBA2/tree/main/audit",
    Src.DERIVED,
    "Checker outputs, official-source re-verification and the injury-revision delta, "
    "computed 2026-11-14 on branches arena/72f9da58-nba2 and arena/fc58f84f-nba2.")

SRC_VERIFY = "session_verify"
register_source(
    SRC_VERIFY,
    "Session arena/fc58f84f-nba2 independent verification artefacts",
    "https://github.com/wingbangboozle1-lang/NBA2/tree/main/audit/2026-11-14-fc58f84f",
    Src.DERIVED,
    "Fresh checker sweep, live-site fetches and official-source re-reads performed "
    "2026-11-14 by session arena/fc58f84f-nba2. Every value on the Verification Report "
    "page was produced in that session; official URLs are cited in the row text.")

# --- Sources added by session arena/3681def8-nba2 (2026-11-14, first graded card) -------
SRC_FINALS = "nba_finals_1113"
SRC_STANDINGS_LIVE = "nba_standings_1114"
SRC_INJ_1114_AM = "nba_injury_pdf_1114_0500"
SRC_DER_GRADED = "derived_graded"

register_source(
    SRC_FINALS,
    "NBA.com Schedule — 2026-11-13 final scores (official)",
    "https://www.nba.com/schedule?date=2026-11-14",
    Src.OFFICIAL,
    "Final scores for the nine 2026-11-13 games, read from the Week 4 (Nov 9-15) grid of the "
    "official schedule on 2026-11-14 ~10:20 UTC; each game card rendered 'Final' with both team "
    "scores (ATL@CHI 'Final/OT'). Every row also carries its own nba.com/game/<slug>-<id> URL. "
    "Snapshot: data/raw/finals_2026-11-13.json. Verified by the identity in check C2-B: "
    "(committed ratings W-L) + (these nine results) = the official NBA.com standings, 30/30 clubs.")
register_source(
    SRC_STANDINGS_LIVE,
    "NBA.com Standings 2026-11-14 (official)",
    "https://www.nba.com/standings",
    Src.OFFICIAL,
    "'NBA 2026-27 Regular Season Standings', Group By Conference, retrieved 2026-11-14 ~10:29 UTC "
    "and including the completed 2026-11-13 games. This is the first win-loss capture in the "
    "repository taken from an official NBA page — the ratings snapshot's W-L is third-party "
    "(basketball-reference) and remains flagged FLAG-RAT-01. Snapshot: "
    "data/raw/standings_2026-11-14_official.json.")
register_source(
    SRC_INJ_1114_AM,
    "NBA Official Injury Report 11/14 05:00 AM ET (official)",
    "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf",
    Src.OFFICIAL,
    "Freshest release listed on https://official.nba.com/nba-injury-report-2026-27-season/ at "
    "retrieval (2026-11-14 ~10:29 UTC); document header reads 'Injury Report: 11/14/26 05:00 AM'. "
    "26 named designations across the five 11/14 games, five clubs still NOT YET SUBMITTED, and "
    "all eighteen 11/15 club entries NOT YET SUBMITTED. The PDF's Game Time column is a 12-hour "
    "ET clock printed without a meridiem. Snapshot: data/raw/injury_report_2026-11-14_0500AM.json.")
register_source(
    SRC_DER_GRADED,
    "Derived: the 2026-11-13 graded card (nba2 model vs official finals)",
    "https://github.com/wingbangboozle1-lang/NBA2/blob/main/audit/2026-11-14-3681/grade_1113.py",
    Src.DERIVED,
    "Our originated lines for the nine 2026-11-13 games, produced from the committed ratings "
    "snapshot that predates every tip, compared with the official final scores. Reproduce with "
    "`python3 audit/2026-11-14-3681/grade_1113.py`. Output: data/graded_2026-11-13.json.")


def _flag_ids(*ids: str) -> list[str]:
    return list(ids)


def _settlement_state_sentence() -> str:
    """One sentence describing data/settlement.json as it is right now.

    The settlement record is rewritten by every `python -m nba2.pipeline.settle` run (human
    or nightly bot), so anything published about it must be read at build time — a hard-coded
    timestamp here would be stale by the next ingest (it was: FLAG-SET-01 used to quote
    settled_at 2026-11-14T00:58Z with finals_snapshot null).
    """
    p = ROOT / "data" / "settlement.json"
    if not p.exists():
        return ("data/settlement.json does not exist yet — run python -m nba2.pipeline.settle "
                "to create the settlement record.")
    d = json.loads(p.read_text())
    parts = [f"data/settlement.json records settled_at {d.get('settled_at_utc', 'unknown')} "
             f"with finals_snapshot {d.get('finals_snapshot')}"]
    for l in d.get("ledgers", []):
        parts.append(f"{l.get('ledger')}: {l.get('games_settled', 0)}/{l.get('games_expected', '?')} "
                     f"games settled ({l.get('status', 'unknown')})")
    return "; ".join(parts)


# --------------------------------------------------------------------------- builders
def build_calibration_rows(model: RT.RatingModel) -> dict:
    cal = model.cal
    rows = [
        make_row("margin_sd", SRC_DER_RAT, _flag_ids("FLAG-PARAM-01"),
                 symbol="σ (margin sd)",
                 value=f"{cal.margin_sd:.2f} pts",
                 method="least-squares fit of (sigma, hca) to the 30 verified win totals, "
                        "grid 6.00-25.00 step 0.25 then refine step 0.01",
                 sanity="NBA game margins are widely reported near 13-14 pts; our fit is independent of that",
                 status="derived from snapshot"),
        make_row("hca", SRC_DER_RAT, _flag_ids("FLAG-PARAM-02"),
                 symbol="h (home-court advantage)",
                 value=f"{cal.hca_points:.2f} pts",
                 method="same joint fit",
                 sanity=f"league home win rate implied by verified home/road splits = {cal.home_win_rate:.1%}; "
                        "that rate alone implies a smaller h than the joint fit",
                 status="derived from snapshot — WEAKLY IDENTIFIED"),
        make_row("league_avg_points", SRC_DER_RAT, _flag_ids("FLAG-RAT-01"),
                 symbol="LG (league average team points)",
                 value=f"{cal.league_avg_points:.2f} pts",
                 method="unweighted mean of the 30 teams' PS/G",
                 sanity="schedule effects ignored",
                 status="derived from snapshot"),
        make_row("reliability", SRC_DER_RAT, _flag_ids("FLAG-PARAM-03"),
                 symbol="τ² (true rating variance)",
                 value=f"{cal.tau_sq:.2f}",
                 method="tau^2 = max(0, Var(SRS) - mean(se^2)), se = sigma/sqrt(games)",
                 sanity=f"mean se = {cal.se_mean:.2f}; shrinkage lambda therefore ~0.74-0.78 per team",
                 status="derived from snapshot"),
        make_row("fit_quality", SRC_DER_RAT, (),
                 symbol="RMSE(wins)",
                 value=f"{cal.rmse_wins:.3f} wins",
                 method="model win total error at the optimum",
                 sanity=f"vs {cal.rmse_baseline_wins:.3f} for a .500 baseline; "
                        f"improvement {100*(1-cal.rmse_wins/cal.rmse_baseline_wins):.0f}%",
                 status="derived from snapshot"),
        make_row("total_sd", "derived_lines", _flag_ids("FLAG-PARAM-04"),
                 symbol="τ (total-line sd)",
                 value=f"{config.PARAMS['total_sd'].value:.1f} pts",
                 method="NOT fitted: set before any game-level totals existed (official finals history "
                        "now sits in the backtest tree; re-fitting is an owner decision, S-04); used only "
                        "inside the parlay sensitivity band",
                 sanity="level-sensitive, so parlay output is reported as a ratio, not a price",
                 status="unratified placeholder"),
    ]
    return table(rows, [("symbol", "Parameter"), ("value", "Fitted value"), ("method", "How it was obtained"),
                        ("sanity", "Cross-check"), ("status", "Status")],
                 "Model parameters — derived, not assumed",
                 "These are the only two structural numbers the whole site depends on. Both are fitted "
                 "against the verified standings snapshot; where the fit is weak we say so instead of "
                 "quietly picking a convention.",
                 "Inputs: data/raw/team_ratings_2026-11-13.json (third-party). Win-loss verified three ways: "
                 "NBA.com game cards (28/30 visible in that capture; TOR/WAS = FLAG-SLATE-02), the prior "
                 "session's independent read (30/30), and a fresh upstream re-read on 2026-11-14 "
                 "(30/30 identical — data/raw/ratings_recheck_2026-11-14.json).")


def load_official_standings() -> dict[str, dict]:
    """The league's own standings table, read from nba.com/standings on 2026-11-14."""
    raw = json.loads((RAW / config.SNAPSHOT_STANDINGS_OFFICIAL).read_text())
    cols = raw["columns"]
    return {d["tricode"]: d for d in (dict(zip(cols, r)) for r in raw["records"])}


def build_ratings_rows(model: RT.RatingModel, official: dict[str, dict] | None = None) -> dict:
    official = official or {}
    rows = []
    for tc in model.order:
        t = model.get(tc)
        o = official.get(tc)
        rows.append(make_row(
            tc, SRC_RAT, _flag_ids("FLAG-RAT-01"),
            team=t.name, tricode=tc,
            wl=f"{t.wins}-{t.losses}",
            wl_official=(f"{o['w']}-{o['l']}" if o else None),
            games_official=(f"{o['w'] + o['l']}" if o else None),
            games_snapshot=f"{t.games}",
            ppg=f"{t.ppg:.1f}" if t.ppg is not None else None,
            oppg=f"{t.oppg:.1f}" if t.oppg is not None else None,
            net=f"{t.net_ppg:+.1f}" if t.net_ppg is not None else None,
            srs=f"{t.srs:+.2f}" if t.srs is not None else None,
            lam=f"{t.reliability:.3f}" if t.reliability is not None else None,
            srs_shrunk=f"{t.srs_shrunk:+.2f}" if t.srs_shrunk is not None else None,
            games=t.games,
        ))
    return table(rows, [("team", "Team"),
                        ("wl_official", "W-L (official NBA.com, 11/14)"),
                        ("wl", "W-L (ratings snapshot, 11/13)"),
                        ("games_official", "GP (official)"),
                        ("games_snapshot", "GP (snapshot)"),
                        ("ppg", "PS/G"), ("oppg", "PA/G"),
                        ("net", "Margin/G"), ("srs", "SRS"), ("games", "GP (model)"),
                        ("lam", "Reliability λ"), ("srs_shrunk", "SRS × λ")],
                 "Team ratings table (the model's only inputs)",
                 "The two win-loss columns are INDEPENDENT measurements and they are printed side by side "
                 "for exactly that reason: the model runs on the 2026-11-13 third-party snapshot (the "
                 "left-hand pair), while the right-hand pair is the league's own table read on "
                 "2026-11-14 — NBA.com/standings. They differ for 18 clubs because the nine 2026-11-13 games were played in "
                 "between — an aged snapshot, not a transcription error. PS/G, PA/G and SRS could still "
                 "not be pulled from an official endpoint (FLAG-RAT-01); the 'Margins & Stats' section of "
                 "nba.com/standings does not render them for a non-browser client.",
                 "Left column: data/raw/team_ratings_2026-11-13.json (third-party Basketball-Reference snapshot). "
                 "Right column: data/raw/official_standings_2026-11-14.json (official NBA.com).")


def build_luck_rows(model: RT.RatingModel) -> dict:
    rows = []
    for tc in model.order:
        t = model.get(tc)
        z = t.luck_z
        verdict = "within noise (|z| < 1.96)" if z is not None and abs(z) < 1.96 else \
                  ("outside 5% band — investigate" if z is not None else "not computable")
        rows.append(make_row(
            tc, SRC_DER_RAT, _flag_ids("FLAG-RAT-01"),
            team=t.name, actual=f"{t.wins}-{t.losses}",
            expected=f"{t.expected_wins:.2f}" if t.expected_wins is not None else None,
            luck=f"{t.luck:+.2f}" if t.luck is not None else None,
            z=f"{z:+.2f}" if z is not None else None,
            verdict=verdict,
            close_record=None, blowout_record=None,
            note="close/blowout split columns are unusable this build (see FLAG-RAT-02)",
        ))
    return table(rows, [("team", "Team"), ("actual", "Actual W-L"), ("expected", "Rating-implied wins"),
                        ("luck", "Win luck"), ("z", "z"), ("close_record", "≤3-pt games"),
                        ("blowout_record", "≥10-pt games"), ("verdict", "Verdict"), ("note", "Note")],
                 "Skill / luck decomposition",
                 "Luck here means: wins beyond what a normal-margin model fitted to this same table implies, "
                 "scaled by the binomial noise of that team's schedule size. The two right-hand columns are "
                 "deliberately blank — the close/blowout split we fetched does not balance league-wide, so we "
                 "refuse to use it for a luck claim.",
                 "Derived from the same verified table; no external source for the decomposition.")


def load_time_corroboration() -> dict:
    """(date, away@home) -> (time_et, captured) from the official injury reports.

    Two committed captures exist (the 2026-11-13 1:00 PM release and the 2026-11-13 7:30 PM
    release this refresh added). The fresher file wins on any key it covers; the older one
    fills the rest, so nothing verified before is silently dropped.
    """
    out: dict = {}
    for fname in (config.SNAPSHOT_TIMES_PRIOR, config.SNAPSHOT_TIMES):
        path = RAW / fname
        if not path.exists():
            continue
        raw = json.loads(path.read_text())
        cols = raw["columns"]
        for rec in raw["records"]:
            d = dict(zip(cols, rec))
            a, h = d["matchup"].split("@")
            out[(d["date"], f"{a} @ {h}")] = (d["time_et"], bool(d["time_captured"]))
    return out


def build_corroboration_rows(games: list[dict], corrob: dict) -> dict:
    """Second-official-document check of the slate itself: do the game, the time and the
    matchup agree across NBA.com/schedule and the referee-operations injury report?"""
    rows = []
    agree_time = lost = absent = mismatch = 0
    for g in games:
        key = (g["date"], f"{g['away']} @ {g['home']}")
        got = corrob.get(key)
        if got is None:
            absent += 1
            verdict = ("not in the 11/13 report — the latest official release lists 11/14 + 11/15 "
                       "only, and this game's date is outside both")
            fl = ["FLAG-SLATE-04"]
        else:
            their_time, captured = got
            verdict_ = None
            if captured and their_time == g["time_et"]:
                agree_time += 1
                verdict, fl = "MATCHUP + TIP TIME corroborated by a second official document", []
            elif captured:
                mismatch += 1
                verdict, fl = f"TIME MISMATCH — schedule says {g['time_et']}, report says {their_time}", ["FLAG-SLATE-04"]
            else:
                lost += 1
                verdict, fl = "matchup corroborated; the report's time cell was lost to a page break", ["FLAG-SLATE-04"]
        rows.append(make_row(
            g["game_id"], "nba_injury_pdf", _flag_ids(*fl) if fl else (),
            date=g["date"], matchup=f"{g['away']} @ {g['home']}", game_id=g["game_id"],
            schedule_time=g["time_et"], report_time_cell=(got[0] if got and got[0] else None),
            verdict=verdict,
        ))
    n = len(games)
    return table(rows, [("date", "Date"), ("matchup", "Matchup"), ("game_id", "Official game ID"),
                        ("schedule_time", "Time from /schedule"), ("report_time_cell", "Time from injury report"),
                        ("verdict", "Cross-document result")],
                 f"Cross-document corroboration: {agree_time} of {n} games confirmed twice, "
                 f"{lost} matchups confirmed with the time cell unreadable, {mismatch} mismatches, "
                 f"{absent} not covered by the second document",
                 "The schedule page is the only source for most of this slate, and its times are printed as a "
                 "loose list — the reason FLAG-SLATE-04 was raised. The injury report repeats each matchup with "
                 "its own time cell, so where the two agree the time is no longer a single-source claim. The "
                 "2026-11-14 refresh supersedes the earlier capture: all 14 games the 11/13 19:30 ET release "
                 "covers (11/13 + 11/14) now corroborate with readable time cells and zero conflicts.",
                 "https://www.nba.com/schedule vs https://ak-static.cms.nba.com/referee/injury/"
                 "Injury-Report_2026-11-13_07_30PM.pdf")


def build_slate_rows(games: list[dict]) -> dict:
    rows = []
    corrob = load_time_corroboration()
    for g in games:
        key = (g["date"], f"{g['away']} @ {g['home']}")
        got = corrob.get(key)
        if got and got[1] and got[0] == g["time_et"]:
            tstatus = "corroborated (injury report, official)"
            fl = []
        elif got and not got[1]:
            tstatus = "matchup confirmed, time cell unreadable — single-source"
            fl = ["FLAG-SLATE-04"]
        elif got:
            tstatus = f"CONFLICT: report says {got[0]}"
            fl = ["FLAG-SLATE-04"]
        else:
            tstatus = "outside the second document's coverage — single-source"
            fl = ["FLAG-SLATE-04"]
        if g["game_id"] not in PREVIEW_VERIFIED:
            fl.append("FLAG-SLATE-05")
        rows.append(make_row(
            g["game_id"], SRC_SLATE, _flag_ids(*fl),
            date=g["date"], time_et=g["time_et"],
            matchup=f"{g['away']} @ {g['home']}",
            game_id=g["game_id"], arena=g["arena"],
            location=f"{g['city']}, {g['state']}",
            broadcast=g["broadcast"],
            cup=g["cup_group"] or "—",
            preview=g["preview_url"],
            time_status=tstatus,
            preview_status="confirmed in retrieved page text" if g["game_id"] in PREVIEW_VERIFIED
                          else "rule-generated, URL not verified — open it to check",
        ))
    return table(rows, [("date", "Date"), ("time_et", "Tip (ET)"), ("matchup", "Matchup (away @ home)"),
                        ("game_id", "Official game ID"), ("arena", "Arena"), ("location", "City"),
                        ("broadcast", "Broadcast"), ("cup", "Emirates NBA Cup"),
                        ("time_status", "Tip-time provenance"),
                        ("preview", "Official game page"), ("preview_status", "Link status")],
                 "Verified slate — 2026-11-13 → 2026-11-17 (36 games; pick window 11/14 → 11/17)",
                 "Every field on this page is read off the official NBA.com schedule. Game IDs are the NBA's "
                 "own; per-date game counts (9 / 5 / 9 / 8 / 5) match the day headers on the same page. The "
                 "2026-11-14 refresh re-checked all 31 games carried forward from the previous capture against "
                 "a fresh retrieval — 0 field mismatches — and added the 11/17 games. The nine 11/13 games are "
                 "day-before context (live or completed at retrieval time); they are priced for calibration "
                 "and are never part of the sealed pick set.",
                 "https://www.nba.com/schedule?date=2026-11-14 retrieved 2026-11-14 ~01:05 UTC "
                 "(prior capture: 2026-11-13 22:33 UTC).")


def build_lines_rows(model: RT.RatingModel, lines: list[LN.GameLine]) -> dict:
    rows = []
    for l in lines:
        fl = ["FLAG-LINE-01", "FLAG-SLATE-01"]
        if l.tier == "C":
            fl.append("FLAG-LINE-02")
        rows.append(make_row(
            l.game_id, SRC_DER, _flag_ids(*fl),
            date=l.date, time_et=l.time_et, matchup=f"{l.away} @ {l.home}",
            m_srs=f"{l.margin_srs:+.2f}" if l.margin_srs is not None else None,
            m_net=f"{l.margin_net:+.2f}" if l.margin_net is not None else None,
            margin=f"{l.margin:+.2f}" if l.margin is not None else None,
            spread=f"{l.home} {l.spread_home:+.1f}" if l.spread_home is not None else None,
            total=f"{l.total_line:.1f}" if l.total_line is not None else None,
            exp_score=f"{l.exp_away_pts:.1f} @ {l.exp_home_pts:.1f}" if l.exp_home_pts is not None else None,
            p_home=f"{l.home_win_prob:.1%}" if l.home_win_prob is not None else None,
            fair=f"{l.fair_home_decimal:.2f} / {l.fair_away_decimal:.2f}" if l.fair_home_decimal else None,
            conviction=f"{l.conviction:.2f}σ" if l.conviction is not None else None,
            agree=f"{l.agreement:.2f} pts" if l.agreement is not None else None,
            stability=f"{l.stability:.0%}" if l.stability is not None else None,
            tier=l.tier,
        ))
    return table(rows, [("date", "Date"), ("time_et", "ET"), ("matchup", "Matchup"),
                        ("m_srs", "Margin (SRS)"), ("m_net", "Margin (raw net)"),
                        ("margin", "Consensus margin"), ("spread", "OUR SPREAD"),
                        ("total", "OUR TOTAL"), ("exp_score", "Expected score"),
                        ("p_home", "P(home win)"), ("fair", "Fair ML (home/away)"),
                        ("conviction", "Conviction"), ("agree", "Model disagreement"),
                        ("stability", "Sensitivity stability"), ("tier", "Tier")],
                 "Originated lines for every game in the window",
                 "Spread/total are our numbers, quoted in half-point increments so nothing pushes. Positive "
                 "consensus margin = home team favoured. No column here is a market price: with no odds feed "
                 "these lines cannot be compared to a book, and we do not pretend otherwise.",
                 "Reproduce: python -m nba2.pipeline.build_site_data")


def build_picks_rows(lines: list[LN.GameLine], as_of: str) -> dict:
    rows = []
    for l in lines:
        if l.tier == "BLOCKED" or l.margin is None:
            continue
        if l.date < as_of:
            continue  # day-before context games: already live/completed, never a pick
        trg = l.triggers
        side = f"{l.home} {l.spread_home:+.1f}" if l.lean == "home" and l.spread_home is not None else \
               (f"{l.away} {-l.spread_home:+.1f}" if l.spread_home is not None else "—")
        act = ("act on %s only if a book is at or worse than our number by %.1f pts" %
               (side, 1.5)) if trg else "no trigger available"
        rows.append(make_row(
            l.game_id, SRC_DER, _flag_ids("FLAG-LINE-01", "FLAG-SLATE-01", "FLAG-LINE-03"),
            date=l.date, matchup=f"{l.away} @ {l.home}",
            lean="BACK " + (l.home if l.lean == "home" else l.away),
            our_line=f"{l.spread_home:+.1f} (home)" if l.spread_home is not None else None,
            our_total=f"{l.total_line:.1f}" if l.total_line is not None else None,
            p=f"{l.home_win_prob:.1%}" if l.home_win_prob is not None else None,
            tier=l.tier,
            trigger=(f"home spread ≥ {trg.get('take_home_if_market_at_least'):+.1f} → take home; "
                     f"home spread ≤ {trg.get('take_away_if_market_at_most'):+.1f} → take away") if trg else None,
            total_trigger=(f"market total ≤ {trg.get('take_over_if_market_at_most'):.1f} → OVER; "
                           f"market total ≥ {trg.get('take_under_if_market_at_least'):.1f} → UNDER") if trg else None,
            stake="0.00% — no price to size against",
            status="PENDING A MARKET PRICE",
        ))
    return table(rows, [("date", "Date"), ("matchup", "Matchup"), ("lean", "Lean"),
                        ("our_line", "Our spread"), ("our_total", "Our total"), ("p", "P(home)"),
                        ("tier", "Tier"), ("trigger", "Spread trigger (act only past this)"),
                        ("total_trigger", "Total trigger"), ("stake", "Stake"), ("status", "Status")],
                 "Picks — expressed as triggers, not as 'bets'",
                 "A pick with no price is a guess. So each row states the number the market would have to "
                 "show before our line justifies action, and the stake stays 0% until an odds feed exists. "
                 "This is the honest shape of a line-origination desk before it has execution. The table "
                 "covers the pick window from the snapshot's as-of date forward (today + 3 days max); the "
                 "day-before context games are priced on the Lines page for calibration only.",
                 "Triggers = our line ± 1.5 pts (unratified hurdle, see FLAG-LINE-03).")


def build_injury_tables(rows: list[INJ.InjuryRow]) -> tuple[dict, dict]:
    detail = []
    for i, r in enumerate(rows):
        fl = []
        if r.attribution == "C":
            fl.append("FLAG-INJ-01")
        fl.append("FLAG-INJ-02")
        if r.status == "NOT YET SUBMITTED":
            fl.append("FLAG-INJ-04")
        detail.append(make_row(
            f"inj-{i}", SRC_INJ, _flag_ids(*fl),
            game_date=r.game_date, time_et=r.time_et, matchup=r.matchup, team=r.team,
            player=r.player or "—", status=r.status, reason=r.reason,
            p_play=f"{r.p_play:.2f}" if r.p_play is not None else None,
            minutes_impact=None, production_impact=None, line_adjustment=None,
            attribution="explicit" if r.attribution == "E" else "block-continuation (unconfirmed)",
        ))
    detail_tbl = table(detail, [("game_date", "Game date"), ("time_et", "Tip (ET)"), ("matchup", "Matchup"),
                                ("team", "Team"), ("player", "Player"), ("status", "Official status"),
                                ("reason", "Reason"), ("p_play", "Our P(plays)"),
                                ("minutes_impact", "Minutes impact"), ("production_impact", "Production impact"),
                                ("line_adjustment", "Line adjustment"), ("attribution", "Row attribution")],
                       "Official NBA injury report — 11/13/26 19:30 ET release (freshest at build time; supersedes the 16:15 capture)",
                       "Transcribed from the NBA's own referee-operations PDF. The three middle columns are "
                       "blank by policy: the report contains no minutes or production data, so any number we "
                       "put there would be invented. P(plays) is our modelling convention for counting bodies, "
                       "not a league probability. Covers 11/13 games plus the first official statuses for the "
                       "11/14 slate (five teams had still not submitted at this release).",
                       "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf")

    rot = INJ.rotation_index(rows)
    rrows = []
    for tri in sorted(rot):
        d = rot[tri]
        rrows.append(make_row(
            f"rot-{tri}", SRC_INJ, _flag_ids("FLAG-INJ-02", "FLAG-INJ-03"),
            team=d["team"], out=d["out"], doubtful=d["doubtful"], questionable=d["questionable"],
            probable=d["probable"], available=d["available_listed"],
            two_way_or_susp=d["gleague_or_suspension"], not_submitted=d["not_yet_submitted"],
            exp_missing=f"{d['expected_missing_bodies']:.2f}",
            sd=f"±{d['missing_body_sd']:.2f}" if d["missing_body_sd"] else "±0.00",
            floor=d["rotation_floor"], risk=INJ.risk_tier(d),
            games=", ".join(d["games"]),
        ))
    rot_tbl = table(rrows, [("team", "Team"), ("out", "Out"), ("doubtful", "Doubtful"),
                            ("questionable", "Questionable"), ("probable", "Probable"),
                            ("available", "Available"), ("two_way_or_susp", "G-League/suspension"),
                            ("not_submitted", "Not yet submitted"), ("exp_missing", "Expected bodies missing"),
                            ("sd", "Band"), ("floor", "Rotation floor"), ("risk", "Risk tier"),
                            ("games", "Games affected")],
                   "Rotation-body impact (the part that IS computable)",
                   "Counting bodies is defensible from the report alone. 'Rotation floor' is the deepest "
                   "available lineup assuming a 10-man rotation, ±1 band from the variance of the status "
                   "weights. It is a depth statement, not a points statement.",
                   "Derived in nba2/models/injuries.py from the official PDF.")
    return detail_tbl, rot_tbl


def build_window_injury_tables() -> tuple[dict, dict]:
    """2026-11-14 day-before designations from the 11/13/26 19:30 ET official release.

    Kept in separate tables from the 16:15 ET capture: different release, different source
    URL, so mixing them under one title would misstate what a reviewer is looking at. The
    impact columns stay blank for the same reason as the 16:15 table: the official report
    carries no minutes, usage or production data (FLAG-INJ-02).
    """
    rows_w, _raw_w = INJ.load(RAW / SNAPSHOT_INJURY_WINDOW)
    detail = []
    for i, r in enumerate(rows_w):
        fl = ["FLAG-INJ-02"]
        if r.attribution == "C":
            fl.append("FLAG-INJ-05")
        if not r.time_et:
            fl.append("FLAG-INJ-06")
        if r.status == "NOT YET SUBMITTED":
            fl.append("FLAG-INJ-04")
        detail.append(make_row(
            f"injw-{i}", SRC_INJ_W, _flag_ids(*fl),
            game_date=r.game_date, time_et=r.time_et or None, matchup=r.matchup, team=r.team,
            player=r.player or "—", status=r.status, reason=r.reason,
            p_play=f"{r.p_play:.2f}" if r.p_play is not None else None,
            minutes_impact=None, production_impact=None, line_adjustment=None,
            attribution="explicit" if r.attribution == "E" else "block-continuation (unconfirmed)",
        ))
    detail_tbl = table(detail, [("game_date", "Game date"), ("time_et", "Tip (ET)"), ("matchup", "Matchup"),
                                ("team", "Team"), ("player", "Player"), ("status", "Official status"),
                                ("reason", "Reason"), ("p_play", "Our P(plays)"),
                                ("minutes_impact", "Minutes impact"), ("production_impact", "Production impact"),
                                ("line_adjustment", "Line adjustment"), ("attribution", "Row attribution")],
                       "Official NBA injury report — 2026-11-14 day-before designations (11/13/26 19:30 ET release)",
                       "First official designations for the 2026-11-14 slate: five teams had filed by the 5 p.m. ET "
                       "day-before deadline, five had not (NOT YET SUBMITTED). Game-day reports on 11/14 (11 a.m.-1 p.m. "
                       "local) can still change these statuses. The three impact columns are blank by policy — the "
                       "report contains no minutes or production data, so any number there would be invented. "
                       "P(plays) is our modelling convention for counting bodies, not a league probability.",
                       "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf")

    rot = INJ.rotation_index(rows_w)
    rrows = []
    for tri in sorted(rot):
        d = rot[tri]
        rrows.append(make_row(
            f"rotw-{tri}", SRC_INJ_W, _flag_ids("FLAG-INJ-02", "FLAG-INJ-07"),
            team=d["team"], out=d["out"], doubtful=d["doubtful"], questionable=d["questionable"],
            probable=d["probable"], available=d["available_listed"],
            two_way_or_susp=d["gleague_or_suspension"], not_submitted=d["not_yet_submitted"],
            exp_missing=f"{d['expected_missing_bodies']:.2f}",
            sd=f"±{d['missing_body_sd']:.2f}" if d["missing_body_sd"] else "±0.00",
            floor=d["rotation_floor"], risk=INJ.risk_tier(d),
            games=", ".join(d["games"]),
        ))
    rot_tbl = table(rrows, [("team", "Team"), ("out", "Out"), ("doubtful", "Doubtful"),
                            ("questionable", "Questionable"), ("probable", "Probable"),
                            ("available", "Available"), ("two_way_or_susp", "G-League/suspension"),
                            ("not_submitted", "Not yet submitted"), ("exp_missing", "Expected bodies missing"),
                            ("sd", "Band"), ("floor", "Rotation floor"), ("risk", "Risk tier"),
                            ("games", "Games affected")],
                   "Rotation-body impact — 2026-11-14 slate (day-before designations)",
                   "Same body-counting arithmetic as the 16:15 table, applied to the day-before designations. "
                   "A team whose report row is NOT YET SUBMITTED contributes a placeholder, not a body count: "
                   "their designations simply have not been filed yet (FLAG-INJ-07).",
                   "Derived in nba2/models/injuries.py from the 11/13 19:30 ET official release.")
    return detail_tbl, rot_tbl


def build_availability_window_rows(games: list[dict]) -> dict:
    """How much of the sealed pick window is availability-blind, per window date.

    Counts are derived by unioning the team designations across both official injury
    snapshots (16:15 ET and 19:30 ET of 11/13). A date with no rows at all in either
    document is reported as such — absence of a row is a fact about the release, not a
    guess about availability.
    """
    rows_w, _ = INJ.load(RAW / SNAPSHOT_INJURY_WINDOW)
    rows_base, _ = INJ.load(RAW / config.SNAPSHOT_INJURY)
    rows_new, _ = INJ.load(RAW / config.SNAPSHOT_INJURY_LATEST)
    per_date: dict[str, dict] = {}
    for r in rows_base + rows_w + rows_new:
        d = per_date.setdefault(r.game_date, {"filed": set(), "nys": set()})
        if r.status == "NOT YET SUBMITTED":
            d["nys"].add(r.team)
        else:
            d["filed"].add(r.team)
    as_of = json.loads((RAW / config.SNAPSHOT_SLATE).read_text())["as_of"]
    sealed_dates = sorted({g["date"] for g in games if g["date"] > as_of})
    rows = []
    for date in sealed_dates:
        n_games = sum(1 for g in games if g["date"] == date)
        slots = 2 * n_games
        d = per_date.get(date, {"filed": set(), "nys": set()})
        filed, nys = len(d["filed"]), len(d["nys"])
        unlisted = slots - filed - nys
        coverage = f"{filed / slots:.0%}" if slots else None
        rows.append(make_row(
            f"avail-{date}", SRC_INJ_W, _flag_ids("FLAG-INJ-07", "FLAG-SLATE-06"),
            date=date, games=n_games, slots=slots, filed=filed,
            not_yet_submitted=nys, no_rows_yet=unlisted,
            coverage=coverage,
            note=("day-before designations captured (11/14 05:00 a.m ET release is the newest "
                  "official source)" if filed else
                  "no designations in any official release yet"),
        ))
    return table(rows, [("date", "Window date"), ("games", "Games"), ("slots", "Team-slots"),
                        ("filed", "Team-slots with a designation"), ("not_yet_submitted", "NOT YET SUBMITTED"),
                        ("no_rows_yet", "No row in any release yet"), ("coverage", "Designation coverage"),
                        ("note", "Note")],
                "Availability coverage of the sealed pick window (2026-11-14 → 11-17)",
                "Computed from every official injury release this repository holds (11/13 16:15 ET, "
                "11/13 19:30 ET and 11/14 05:00 a.m ET), never inferred. 'Coverage' is the share of "
                "team-slots carrying any official participation designation at capture time; it rises as "
                "later releases are ingested. The lines for this window were originated from the 2026-11-13 "
                "snapshot and sealed; availability data refreshes around them. A team that appears as "
                "NOT YET SUBMITTED in one release and files designations in a later one is counted once, "
                "as filed.",
                "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf")


def build_gameflow_rows(games: list[dict], spots: dict, flow: list[dict]) -> dict:
    rows = []
    for f in flow:
        hs = spots.get(f["matchup"].split(" @ ")[1])
        as_ = spots.get(f["matchup"].split(" @ ")[0])
        flags = ["FLAG-FLOW-01", "FLAG-FLOW-02"]
        rows.append(make_row(
            f["game_id"], SRC_SLATE, _flag_ids(*flags),
            date=f["date"], matchup=f["matchup"],
            home_games_window=f"{hs.games_in_window} ({hs.home_games}H/{hs.away_games}A)" if hs else None,
            away_games_window=f"{as_.games_in_window} ({as_.home_games}H/{as_.away_games}A)" if as_ else None,
            home_b2b="YES" if f["home_b2b"] else "no",
            away_b2b="YES" if f["away_b2b"] else "no",
            home_3_in_4="YES" if f["home_3_in_4"] else "no",
            away_3_in_4="YES" if f["away_3_in_4"] else "no",
            rest_home=None, rest_away=None,
            pace=None, garbage=None, foul=None, closing=None,
        ))
    return table(rows, [("date", "Date"), ("matchup", "Matchup"), ("home_games_window", "Home load (window)"),
                        ("away_games_window", "Away load (window)"), ("home_b2b", "Home B2B"),
                        ("away_b2b", "Away B2B"), ("home_3_in_4", "Home 3-in-4"), ("away_3_in_4", "Away 3-in-4"),
                        ("rest_home", "Rest days (home)"), ("rest_away", "Rest days (away)"),
                        ("pace", "Pace flow"), ("garbage", "Garbage-time risk"), ("foul", "Foul trouble"),
                        ("closing", "Closing lineup")],
                 "Game flow — what the slate tells us, and everything it does not",
                 "Left of the divider: computed from official schedule dates. Right of the divider: blank, "
                 "because in-game flow needs play-by-play, lineups and foul data that this repository does "
                 "not have. A 'game flow analysis' that narrates those four columns without the data is "
                 "storytelling, and it is how books get paid.",
                 "https://www.nba.com/schedule")


def build_anomaly_rows(anomalies: list[dict], window_game_ids: set[str]) -> dict:
    rows = []
    for a in anomalies:
        in_window = a["game_id"] in window_game_ids
        if a.get("window") == "ingest hazard":
            disposition = "DOCUMENTED HAZARD — no data claim depends on the ignored parameter"
        elif in_window:
            disposition = ("RESOLVED BY THE 2026-11-14 CAPTURE — the official page renders both games as "
                           "distinct entries with distinct official game IDs, so this is a genuine schedule "
                           "entry, not a duplicate card. Now inside the pick window; the rest/B2B "
                           "consequences are priced by game flow and flagged.")
        else:
            disposition = "FLAGGED — not used in any model output"
        rows.append(make_row(
            a["game_id"], SRC_SLATE, _flag_ids("FLAG-ANOM-01"),
            date=a["date"], matchup=a["matchup"], game_id=a["game_id"],
            observation=a["observation"], window=a.get("window", "—"),
            disposition=disposition,
        ))
    return table(rows, [("date", "Date"), ("matchup", "Matchup"), ("game_id", "Game ID"),
                        ("observation", "Observation"), ("window", "In pick window?"),
                        ("disposition", "Disposition")],
                 "Slate irregularities found while transcribing",
                 "Recorded, not fixed. Each of these would corrupt an automated pipeline that trusted the "
                 "pattern instead of the value.",
                 "First recorded from https://www.nba.com/schedule retrieved 2026-11-13 22:39 UTC; "
                 "dispositions updated where the 2026-11-14 capture resolves the question.")


def build_correlation_rows(model: RT.RatingModel, lines: list[LN.GameLine]) -> dict:
    pairs = [(t.srs, t.net_ppg) for t in model.teams.values() if t.srs is not None and t.net_ppg is not None]
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    r = corr.pearson(xs, ys)
    rho = corr.spearman(xs, ys)
    rows = [
        make_row("srs_vs_net", SRC_DER_CORR, _flag_ids("FLAG-CORR-01"),
                 pair="SRS vs raw scoring margin (30 teams)",
                 pearson=f"{r:+.3f}" if r is not None else None,
                 spearman=f"{rho:+.3f}" if rho is not None else None,
                 n=len(xs), method="computed on the verified ratings table",
                 use="tells us how much the schedule adjustment actually adds; if r were ~1 the two models "
                     "are one model and the 'agreement filter' buys nothing",
                 status="computed"),
        make_row("margin_vs_total", SRC_DER_CORR, _flag_ids("FLAG-CORR-02"),
                 pair="game margin vs game total (for spread+over parlays)",
                 pearson="-0.009 (95% CI -0.17 to 0.15)", spearman=None, n=139,
                 method="measured on 139 official finals in the backtest tree (point-in-time, "
                        "leakage-asserted); root-site parlay pricing still uses the unmeasured assumption",
                 use="drives every same-game parlay price — measured r near 0 does not support the parlay premise",
                 status="measured (backtest tree)"),
        make_row("player_points_rebounds", SRC_DER_CORR, _flag_ids("FLAG-CORR-03"),
                 pair="same-player points vs rebounds",
                 pearson=None, spearman=None, n=None,
                 method="BLOCKED — needs player box scores",
                 use="combo/prop parlay pricing", status="unavailable"),
        make_row("same_team_two_games", SRC_DER_CORR, _flag_ids("FLAG-CORR-04"),
                 pair="a team's line on consecutive nights",
                 pearson=None, spearman=None, n=None,
                 method="structurally dependent by construction; never parlay two games of one team",
                 use="exclusion rule", status="rule, not measurement"),
        make_row("cross_game", SRC_DER_CORR, _flag_ids("FLAG-CORR-05"),
                 pair="leg A in game 1 vs leg B in game 2",
                 pearson="≈0 assumed", spearman=None, n=None,
                 method="near-independence is the standard assumption and is testable only with a bet ledger",
                 use="cross-game parlay pricing", status="assumption — test when ledger has 300 bets"),
    ]
    return table(rows, [("pair", "Correlation"), ("pearson", "Pearson r"), ("spearman", "Spearman ρ"),
                        ("n", "n"), ("method", "Method / block"), ("use", "What it feeds"), ("status", "Status")],
                 "Correlation register",
                 "One of these five is measurable today. The other four are the difference between a parlay "
                 "desk and a parlay hobby, and all four need the same thing: game-level and player-level data. "
                 "Any site that prints correlation numbers for those pairs without that data made them up.",
                 "Derived in nba2/models/correlation.py; inputs from the verified ratings snapshot.")


def build_parlay_rows(model: RT.RatingModel, lines: list[LN.GameLine]) -> dict:
    rows = []
    sd_total = float(config.PARAMS["total_sd"].value)
    band = tuple(config.PARAMS["rho_band"].value)
    ranked = [l for l in lines if l.margin is not None and l.spread_home is not None and l.total_line is not None]
    ranked.sort(key=lambda l: -abs(l.margin))
    for l in ranked[:10]:
        q = corr.quote_pair(l.margin, model.cal.margin_sd,
                            l.total, sd_total, l.spread_home, l.total_line, band)
        ratios = list(q.ratio.values())
        rows.append(make_row(
            f"prl-{l.game_id}", SRC_DER_CORR, _flag_ids("FLAG-PRL-01", "FLAG-PRL-02"),
            matchup=f"{l.away} @ {l.home}",
            legs=f"{l.home} {l.spread_home:+.1f} + OVER {l.total_line:.1f}",
            p_home_cover=f"{q.p_a:.3f}", p_over=f"{q.p_b:.3f}",
            indep=f"{q.p_independent:.4f}",
            joint_lo=f"{q.p_correlated[band[0]]:.4f}", joint_hi=f"{q.p_correlated[band[1]]:.4f}",
            boost_lo=f"{min(ratios):.3f}×", boost_hi=f"{max(ratios):.3f}×",
            sign_stable="yes" if q.sign_stable else "no",
            verdict=("structure says over-priced legs exist" if q.sign_stable and max(ratios) > 1.05
                     else "not publishable"),
        ))
    return table(rows, [("matchup", "Game"), ("legs", "Legs (our numbers)"), ("p_home_cover", "P(leg A)"),
                        ("p_over", "P(leg B)"), ("indep", "Independent joint"), ("joint_lo", "Joint @ ρ=-0.20"),
                        ("joint_hi", "Joint @ ρ=+0.40"), ("boost_lo", "ratio low"), ("boost_hi", "ratio high"),
                        ("sign_stable", "Sign stable?"), ("verdict", "Verdict")],
                 "Same-game parlay pricing under a correlation sweep",
                 "Priced on a bivariate normal with ρ swept across the ratified band because the true "
                 "margin/total correlation is unknown. The ratio column is the point: how much a book that "
                 "multiplies single-leg probabilities is off, which is far more robust than the absolute price.",
                 "nba2/models/correlation.py::quote_pair; ρ band unratified (FLAG-PRL-01).")


def build_cross_game_rows(lines: list[LN.GameLine]) -> dict:
    """Cross-game parlays (assumed near-independent) vs same-game, plus the cost of stacking.

    The contrast is the actionable part: two legs from different games are priced by the
    product rule to within a percent or two, while two legs from the same game are off by
    double-digit percent even before any model error. And every added leg multiplies hold.
    """
    ranked = sorted([l for l in lines if l.home_win_prob is not None],
                    key=lambda l: -abs(l.margin or 0))
    rows = []
    used: set[str] = set()
    for i, a in enumerate(ranked):
        if a.date in used or len(used) >= 3:
            continue
        b = next((x for x in ranked[i + 1:] if x.date != a.date and x.away != a.away
                  and x.home != a.away and x.away != a.home), None)
        if b is None:
            continue
        used.update({a.date, b.date})
        pa = a.home_win_prob if a.lean == "home" else 1 - a.home_win_prob
        pb = b.home_win_prob if b.lean == "home" else 1 - b.home_win_prob
        e0 = PR.combo_correlation_effect(pa, pb, 0.0)
        em = PR.combo_correlation_effect(pa, pb, -0.05)
        ep = PR.combo_correlation_effect(pa, pb, 0.05)
        rows.append(make_row(
            f"xg-{a.game_id}-{b.game_id}", SRC_DER_CORR, _flag_ids("FLAG-CORR-05", "FLAG-PRL-01"),
            structure="cross-game (2 legs, different dates, no shared team)",
            legs=f"{(a.home if a.lean=='home' else a.away)} ML  +  {(b.home if b.lean=='home' else b.away)} ML",
            p_a=f"{pa:.3f}", p_b=f"{pb:.3f}",
            joint_product=f"{e0['independent_product']:.4f}",
            joint_corr=f"{em['correlated_joint']:.4f} … {ep['correlated_joint']:.4f}",
            error_band=f"×{em['error_factor']:.3f} … ×{ep['error_factor']:.3f}",
            publishable="product rule is within ~2% — usable once prices exist",
        ))
    return table(rows, [("structure", "Structure"), ("legs", "Legs"), ("p_a", "P(leg A)"),
                        ("p_b", "P(leg B)"), ("joint_product", "Product of legs"),
                        ("joint_corr", "Joint under ρ band"), ("error_band", "Error band"),
                        ("publishable", "Verdict")],
                 "Cross-game parlays, and what stacking costs",
                 "Two different games: the product rule is nearly right, so cross-game parlays are the safe "
                 "place to express multiple views. Same game: the product rule is off by 13–26% on the ten "
                 "quoted games above, which is larger than the entire edge a good model earns. And every leg "
                 "you add multiplies the book's hold — arithmetic that needs no data to check.",
                 "ρ = 0 assumed for cross-game (FLAG-CORR-05); -110 is a labelled placeholder price, not a quote.")


def build_cost_rows() -> dict:
    """Hold and the edge a parlay must find, from the vig arithmetic alone."""
    price = 1.909
    rows = []
    for n in (1, 2, 3, 4, 6):
        par_price = price ** n
        need = 1.0 / par_price
        fair_joint = 0.524 ** n
        rows.append(make_row(
            f"hold-{n}", SRC_DER, _flag_ids("FLAG-PRL-03"),
            legs=n, price=f"{par_price:.2f}", break_even_p=f"{need:.4f}",
            product_of_fair=f"{fair_joint:.4f}",
            edge_needed=f"{100 * (need / fair_joint - 1):+.2f}%",
            note=("at a symmetric -110 reference price, a same-game 2-leg parlay must beat the product "
                  "rule by 13–26% AND clear this hold" if n == 2 else
                  "the price a book would quote if it simply multiplied our fair odds"),
        ))
    return table(rows, [("legs", "Legs"), ("price", "Decimal price"), ("break_even_p", "Break-even P"),
                        ("product_of_fair", "Product of fair legs"), ("edge_needed", "Extra edge needed"),
                        ("note", "Note")],
                 "Cost of stacking (pure arithmetic — no data needed to verify)",
                 "Every column here is reproducible with a calculator: price = 1.909^n, break-even = 1/price. "
                 "This is why 'parlays are more fun' and 'parlays are worse' are both true at once.",
                 "REFERENCE_PRICE −110 is a placeholder; recompute against a real feed when one exists.")


def build_strategy_rows(entries: list[LB.Entry]) -> dict:
    """The leaderboard. AT-RISK is reported separately from BLOCKED (see leaderboard.py)."""
    rows = []
    for e, r in zip(entries, LB.table_rows(entries)):
        fl = ["FLAG-LB-01"]
        rows.append(make_row(
            e.strategy_id, SRC_DER, _flag_ids(*fl),
            id=e.strategy_id, name=r["name"], family=r["family"],
            score=None if r["score"] is None else f"{r['score']:.1f}",
            tier=r["tier"],
            gates=(f"{r['gates_passed']} pass / {r['gates_failed']} fail / "
                   f"{r['gates_blocked']} blocked / {r['gates_at_risk']} at-risk"),
            bets=r["n_bets"], cluster=r["cluster"], reward=None,
            blocking=r["blocking"][:220],
        ))
    return table(rows, [("id", "ID"), ("name", "Strategy"), ("family", "Family"), ("score", "Score /100"),
                        ("tier", "Tier"), ("gates", "Gates"), ("bets", "Settled bets"),
                        ("cluster", "Cluster"), ("reward", "Reward"), ("blocking", "Why it cannot win yet")],
                 "Strategy leaderboard",
                 "Nothing is ranked, because nothing has been measured yet — and an early-season leaderboard "
                 "built on 12 games of standings is a noise leaderboard by construction. Every row is scored "
                 "the moment its gates have data; until then the honest entry is blank.",
                 "nba2/models/leaderboard.py; weights in nba2/config.py::REWARD_WEIGHTS")


def build_gate_rows(results_by_strategy: dict[str, list[G.GateResult]]) -> dict:
    rows = []
    for sid, rs in results_by_strategy.items():
        for r in rs:
            fl = ["FLAG-GATE-01"] if r.result != G.PASS else []
            rows.append(make_row(
                f"{sid}-{r.gate_id}", SRC_DER, _flag_ids(*fl),
                strategy=sid, gate=r.gate_id, name=r.name, result=r.result,
                measured=r.measured, reason=r.reason or "—",
            ))
    return table(rows, [("strategy", "Strategy"), ("gate", "Gate"), ("name", "Gate name"),
                        ("result", "Result"), ("measured", "Measurement"), ("reason", "Reason / block")],
                 "Gate-by-gate results (9 strategies × 10 gates)",
                 "PASS requires a measurement. BLOCKED means the input does not exist; AT-RISK means the "
                 "input exists but is contaminated for this use. Neither is a 0 and neither is a pass. "
                 "The measured-skill backtest tree (backtest/) now grades G-04 (measured FAIL) and G-07 "
                 "(measured PASS) on 139 official finals.",
                 "Thresholds in nba2/config.py::GATES are PROPOSED and require owner ratification.")


def build_gate_spec_rows() -> dict:
    rows = []
    for g in config.GATES:
        rows.append(make_row(
            g["id"], SRC_DER, _flag_ids("FLAG-GATE-01"),
            gate=g["id"], name=g["name"], rule=g["rule"], why=g["why"],
            threshold=None if g["threshold"] is None else f"{g['threshold']} {g['unit']}",
            source=g["source"], status=g["status"],
            blocked=g["blocking_reason"] or "—",
        ))
    return table(rows, [("gate", "Gate"), ("name", "Name"), ("rule", "Rule"),
                        ("threshold", "Threshold"), ("why", "Why it exists"), ("source", "Basis"),
                        ("status", "Status"), ("blocked", "Blocking reason")],
                 "Validation gates — specification",
                 "A strategy must clear all ten to be promoted and to receive rewards. Most are still "
                 "blocked by missing data; G-04 now has measured evidence and FAILS it, G-07 is measured "
                 "PASS in the backtest tree — which is the real status of this project and the reason "
                 "the leaderboard pays nothing.", "nba2/config.py::GATES")


def build_param_rows() -> dict:
    rows = []
    for k, p in config.PARAMS.items():
        fl = [] if p.status == "verified" else [f"FLAG-PARAM-{k.upper()}"]
        rows.append(make_row(
            k, SRC_DER, _flag_ids(*(fl or ["FLAG-PARAM-05"])),
            param=k, value="—" if p.value is None else str(p.value), unit=p.unit,
            status=p.status, rationale=p.rationale, source=p.source,
            sensitivity="—" if not p.sensitivity else f"{p.sensitivity[0]} … {p.sensitivity[1]}",
        ))
    return table(rows, [("param", "Parameter"), ("value", "Value"), ("unit", "Unit"), ("status", "Status"),
                        ("sensitivity", "Sensitivity band"), ("rationale", "Rationale"), ("source", "Source")],
                 "Every tunable number in the system, and whether anyone has justified it",
                 "This is the anti-overfitting page: any value whose status is not 'derived' or 'verified' is "
                 "a place where a human could have cheated, so they are listed with their bands.",
                 "nba2/config.py::PARAMS")


def build_props_rows() -> dict:
    rows = []
    for market in ("points", "rebounds", "assists", "3PM", "points+rebounds combo", "points+assists combo"):
        q = PR.blocked_quote("(awaiting roster-level feed)", "—", market)
        rows.append(make_row(
            f"prop-{market}", "odds_blocked", _flag_ids("FLAG-PROP-01"),
            player=None, team=None, market=market, line=None, projection=None,
            p_over=None, minutes_floor=None, status=q.status,
            missing="; ".join(q.missing_inputs[:2]),
        ))
    mech = PR.combo_correlation_effect(0.55, 0.55, 0.40)
    rows.append(make_row(
        "prop-mechanism", SRC_DER_CORR, _flag_ids("FLAG-PROP-02"),
        player="—", team="—", market="mechanism demo: two legs at p=0.55 with ρ=0.40",
        line="—", projection="—",
        p_over=f"joint {mech['correlated_joint']:.4f} vs product {mech['independent_product']:.4f}",
        minutes_floor=None,
        status=f"arithmetic illustration (×{mech['error_factor']} error), NOT a prediction",
        missing="shows why combo legs cannot be multiplied",
    ))
    return table(rows, [("market", "Prop market"), ("player", "Player"), ("line", "Book line"),
                        ("projection", "Projection"), ("p_over", "P(over)"), ("minutes_floor", "Minutes floor"),
                        ("status", "Status"), ("missing", "Missing input")],
                 "Player props and prop combos",
                 "The pricing code exists and is unit-tested (negative-binomial tails, minutes-implied lines, "
                 "copula combos). What does not exist is a single official player-level input in this "
                 "repository, so every row is blank. The last row is the one number we can give: treating "
                 "combo legs as independent mis-states the price by a factor, and that is a math fact, not an "
                 "estimate.", "nba2/models/props.py")


def build_leader_rows(inj_rows: list[INJ.InjuryRow], leaders_path: Path) -> dict:
    raw = json.loads(Path(leaders_path).read_text())
    cols = raw["columns"]
    leaders = [dict(zip(cols, rec)) for rec in raw["records"]]
    joined = INJ.leader_availability(inj_rows, leaders)
    rows = []
    for j in joined:
        rows.append(make_row(
            f"lead-{j['tricode']}", SRC_INJ, _flag_ids("FLAG-INJ-03", "FLAG-INJ-02"),
            team=j["team"], leader=j["leader_player"],
            ppg=f"{j['ppg']:.1f}" if j["ppg"] is not None else None,
            rpg=f"{j['rpg']:.1f}" if j["rpg"] is not None else None,
            apg=f"{j['apg']:.1f}" if j["apg"] is not None else None,
            report_status=j["report_status"],
            impact=None, note=j["note"],
        ))
    return table(rows, [("team", "Team"), ("leader", "Leader shown on official game card"),
                        ("ppg", "PPG (card)"), ("rpg", "RPG (card)"), ("apg", "APG (card)"),
                        ("report_status", "Status on the official injury report"),
                        ("impact", "Line impact"), ("note", "Note")],
                 "Leader-availability cross-check (official report vs official game card)",
                 "Two official documents joined on team+player. 'NOT LISTED ON REPORT' means the report we "
                 "retrieved contains no row for that player — it is not a guarantee of availability, which is "
                 "why the impact column stays blank. Leaders were captured from the 2026-11-13 game cards; "
                 "injury statuses come from the 2026-11-13 19:30 ET release.",
                 "https://www.nba.com/games + the 11/13 19:30 ET injury report")


def build_repo_review_rows(review: list[dict]) -> dict:
    rows = [make_row(r["id"], r["source_key"], _flag_ids(*(r.get("flags") or ["FLAG-REPO-01"])),
                     id=r["id"],
                     **{k: v for k, v in r.items() if k not in ("id", "source_key", "flags")})
            for r in review]
    return table(rows, [("id", "#"), ("area", "Area"), ("finding", "Finding (line-by-line)"),
                        ("evidence", "Evidence"), ("action", "Action taken")],
                 "Repository review",
                 "Reviewed from the git history and the working tree, not from a summary of it.",
                 "All findings also recorded in COORDINATION.md")


def build_generic(name: str, items: list[dict], columns: list[tuple[str, str]],
                  source_key: str, flags: list[str], title: str, blurb: str, note: str) -> dict:
    rows = [make_row(str(it.get("id", i)), source_key, _flag_ids(*flags) if flags else (),
                     id=it.get("id", i),
                     **{k: v for k, v in it.items() if k != "id"})
            for i, it in enumerate(items)]
    return table(rows, columns, title, blurb, note)


# --------------------------------------------------------------------------- main
def build_audit_rows() -> dict:
    """Session arena/72f9da58 verification results (tasks E-01…E-04), run 2026-11-14 UTC.

    Every result below was produced by running the named command or reading the named
    official page during this session; nothing here is carried over from another session's
    claims. Row counts for the checkers are the values printed by the run itself.
    """
    rows = [
        make_row("E-01-tests", SRC_AUDIT, (),
                 check="E-01 model + pipeline tests",
                 result="PASS — 64/64 nba2 tests and 49/49 backtest tests (re-run after the "
                        "2026-11-14 refresh merge)",
                 method="python -m unittest discover -s nba2/tests -t . and -s backtest/tests -t ."),
        make_row("E-01-seal", SRC_AUDIT, (),
                 check="E-01 sealed-ledger verification",
                 result="VERIFIED — cf7dedc689597cb8… over 22 predictions; site prints the same digest",
                 method="python -m nba2.pipeline.seal_predictions --verify (ledger never rewritten)"),
        make_row("E-01-lint", SRC_AUDIT, (),
                 check="E-01 provenance lint",
                 result="PASS — every published row sourced, every blank explained",
                 method="python -m nba2.pipeline.lint"),
        make_row("E-01-links", SRC_AUDIT, (),
                 check="E-01 whole-repo internal link check",
                 result="PASS — all internal links OK across every HTML file in the repo",
                 method="python3 tools/check_links_all.py (counts recorded in COORDINATION.md)"),
        make_row("E-01-docs", SRC_AUDIT, (),
                 check="E-01 docs/ site verifier",
                 result="PASS — 13 pages, 249 data rows, every row source-linked",
                 method="python3 tools/verify_site.py"),
        make_row("E-01-dashboard", SRC_AUDIT, (),
                 check="E-01 dashboard/ site checker",
                 result="PASS — 12 pages, 524 rows, internal links resolve",
                 method="python3 scripts/check_site.py"),
        make_row("E-01-originated", SRC_AUDIT, (),
                 check="E-01 originated/ engine verifier",
                 result="PASS — 24/24 checks",
                 method="node originated/engine/verify.js"),
        make_row("E-02-slate", SRC_SLATE, (),
                 check="E-02 slate vs official schedule",
                 result="36/36 rows of the current slate (11/13 context + 11/14–17 pick window) "
                        "match the official page on game ID, date and matchup — 0 mismatches; "
                        "per-date counts 9/5/9/8/5 match the official day headers",
                 method="nba.com/schedule fetched 2026-11-14 ~01:55 UTC (capture: "
                        "audit/official_schedule_2026-11-14.json), diffed row-by-row against "
                        "data/raw/slate_2026-11-14_to_11-17.json"),
        make_row("E-02-tips", SRC_SLATE, (),
                 check="E-02 tip times",
                 result="30/30 displayed tips match (the six 11/13 games were already live at "
                        "retrieval, so the page showed scores instead of times — their tips were "
                        "confirmed earlier in this session from the schedule capture plus the "
                        "official injury report's Game Time column, i.e. 36/36 with two sources each)",
                 method="official schedule page text vs slate snapshot; injury PDF Game Time column "
                        "for the live games"),
        make_row("E-02-urls", SRC_SLATE, (),
                 check="E-02 game-page URLs",
                 result="36/36 game IDs appear as links nba.com itself prints (schedule previews + "
                        "game rail); the original 31-row window was additionally re-read slug by "
                        "slug — upgrades FLAG-SLATE-05 from 'rule-generated' to verified",
                 method="every https://www.nba.com/game/… link observed on official pages compared "
                        "to the published slate table"),
        make_row("E-03-rev", SRC_INJ_LATEST, (),
                 check="E-03 latest official injury revision",
                 result="This session fetched the 19:15 ET revision in full (a 20:15 ET revision "
                        "does not exist — CDN AccessDenied); the 2026-11-14 refresh subsequently "
                        "ingested the official 19:30 ET release, which the site now publishes",
                 method="fetch of Injury-Report_2026-11-13_07_15PM.pdf (2 chunks, 122 rows parsed "
                        "with round-trip validation); published rows sourced to the _07_30PM release"),
        make_row("E-03-delta", SRC_INJ_LATEST, (),
                 check="E-03 delta vs the published 16:15 ET snapshot",
                 result="12 status changes, 32 added rows, 5 pending placeholders resolved, 3 text-layer spacing artefacts",
                 method="audit/parse_injury_0715.py — every parsed cell asserted present in the captured source text"),
        make_row("E-03-sub", SRC_INJ_LATEST, (),
                 check="E-03 11/14 submission state at 19:15 ET",
                 result="Submitted: DEN, DAL, CLE, BKN, MIN, DET. Pending: NOP, MEM, CHI, MIA. No 11/15–16 rows exist yet (structurally unavailable at T-2/T-3)",
                 method="rows of the official 19:15 ET revision, read directly"),
        make_row("E-04-records", SRC_STANDINGS, (),
                 check="E-04 team records vs official standings",
                 result="30/30 W-L match the snapshot; Toronto 5-7 and Washington 4-9 are now official — resolves FLAG-SLATE-02",
                 method="nba.com/standings fetched 2026-11-14, diffed against data/raw/team_ratings_2026-11-13.json"),
        make_row("E-04-anom", SRC_GAME_ANOM, (),
                 check="E-04 11/17 repeat matchups (FLAG-ANOM-01)",
                 result="Genuine, not a rendering artefact — the official game page shows 'Tuesday, November 17th, 2026 7:30 PM ET' for NYK @ TOR (0022600253); the official rail also lists POR @ MIN (0022600254)",
                 method="direct read of the official game page and the nba.com game rail"),
        make_row("E-04-settle", SRC_FINALS,
                 check="E-04 sealed-ledger settlement status",
                 result="PARTIAL, and that is the correct answer — the settlement path was exercised "
                        "on 2026-11-14 against real official finals captures (data/raw/finals_2026-11-13.json "
                        "+ data/raw/finals_all.json, nine games, captured independently by two sessions). "
                        + _settlement_state_sentence() +
                        " The nine played games are day-before context that neither sealed ledger covers, "
                        "so metrics stay unmeasured rather than assumed, and a partial settlement is "
                        "refused rather than published",
                 method="python -m nba2.pipeline.settle with the committed finals captures; the nightly "
                        "ingest job fetches and settles the sealed games per game day"),
    ]
    return table(
        rows,
        [("check", "Check"), ("result", "Result"), ("method", "Method / evidence")],
        "Session audit — line-by-line verification (2026-11-14, session arena/72f9da58)",
        "Every checker in the repository re-run, and every published slate/records/injury "
        "claim re-read against the official source, during this session. Results are what "
        "the commands printed and what the official pages contained — not what a previous "
        "session recorded.",
        "Commands re-run and official pages re-fetched 2026-11-14 UTC on branch "
        "arena/72f9da58-nba2; artefacts in audit/.")


def build_injury_delta_rows() -> dict:
    """Published 16:15 ET injury snapshot vs the official 19:15 ET revision (E-03).

    Source of truth for both sides is the official NBA PDF; the delta file is produced by
    audit/parse_injury_0715.py, which asserts every cell against the captured document text.
    """
    import json as _json
    delta = _json.loads((ROOT / "audit" / "injury_delta_0415_to_0715.json").read_text())
    rows = []
    n = 0
    for c in delta["status_changed"]:
        n += 1
        note = "reason unchanged" if c["published_reason"] == c["latest_reason"] else \
            f"reason: {c['published_reason']} → {c['latest_reason']}"
        flags = ()
        if c["player"] == "Martin, Caleb":
            flags = _flag_ids("FLAG-CUR-02")
            note += "; team label dropped at the page break in the 19:15 extraction — " \
                    "Cleveland printed explicitly on this row in the 17:15 and 18:15 revisions"
        rows.append(make_row(f"delta-status-{n:03d}", SRC_INJ_LATEST, flags,
                             kind="status change", matchup=c["matchup"], team=c["team"],
                             player=c["player"],
                             before=c["published_status"] or "NOT YET SUBMITTED",
                             after=c["latest_status"] or "NOT YET SUBMITTED",
                             note=note))
    n = 0
    for r in delta["added_in_latest"]:
        n += 1
        flags = ()
        note = "row first appears in the 19:15 ET revision"
        if r[4] == "Martin, Caleb":
            flags = _flag_ids("FLAG-CUR-02")
            note = "first appearance; 19:15 extraction drops his team label at a page break"
        elif r[3] in ("Denver Nuggets", "Dallas Mavericks", "Brooklyn Nets",
                      "Minnesota Timberwolves", "Detroit Pistons"):
            note = "team's first submission for 11/14, printed between the 16:15 and 19:15 revisions"
        elif r[2] == "OKC@LAC":
            note = "OKC rows added to the 11/13 block between revisions"
        rows.append(make_row(f"delta-added-{n:03d}", SRC_INJ_LATEST, flags,
                             kind="added in 19:15 ET", matchup=r[2], team=r[3],
                             player=r[4] or "(team placeholder)",
                             before="(not in 16:15 ET revision)",
                             after=r[5], note=note))
    n = 0
    for r in delta["removed_in_latest"]:
        n += 1
        rows.append(make_row(f"delta-removed-{n:03d}", SRC_INJ_LATEST, (),
                             kind="pending resolved", matchup=r[2], team=r[3],
                             player="(team placeholder)",
                             before="NOT YET SUBMITTED",
                             after="submitted — placeholder replaced by player rows",
                             note="team submitted its 11/14 list between the 16:15 and 19:15 revisions"))
    n = 0
    for f_ in delta["formatting_only"]:
        n += 1
        rows.append(make_row(f"delta-format-{n:03d}", SRC_INJ_LATEST, (),
                             kind="text-layer spacing only", matchup=f_["matchup"],
                             team=f_["team"], player=f_["player"],
                             before=f_["published_reason"], after=f_["latest_reason"],
                             note="space dropped by the PDF text layer — not a document change"))
    return table(
        rows,
        [("kind", "Change type"), ("matchup", "Matchup"), ("team", "Team"),
         ("player", "Player"), ("before", "Then-published (16:15 ET)"),
         ("after", "Official (19:15 ET)"), ("note", "Note")],
        "Injury-report currency delta: first published 16:15 ET vs official 19:15 ET",
        "What changed between the injury rows this site first published (the adjudicated 16:15 ET "
        "snapshot) and the official 19:15 ET revision. The site now publishes the official 19:30 ET "
        "release (2026-11-14 refresh), so this table is the audit trail of the evening's "
        "supersessions — every row sourced to the official PDFs.",
        "Then-published side: Injury-Report_2026-11-13_04_15PM.pdf (data/raw). Official side: "
        "Injury-Report_2026-11-13_07_15PM.pdf, captured 2026-11-14; delta computed by "
        "audit/parse_injury_0715.py with round-trip validation. The currently published rows come "
        "from the 19:30 ET release (data/raw/injury_report_2026-11-13_1930ET.json).")


def build_audit_suggestions_rows() -> dict:
    """Site-improvement suggestions from session arena/72f9da58 — review before implementing."""
    items = [
        dict(id="S-A01", title="Re-ingest the injury report at its latest official revision",
             problem="The published injury rows are the 16:15 ET revision; three newer official revisions existed the same evening (17:15, 18:15, 19:15) with 12 status changes and 32 added rows.",
             proposal="Before each pick run, fetch the newest official PDF revision, re-run the capture→delta→build cycle, and stamp the revision time on the Injuries page.",
             benefit="Lines and rotation notes stop being priced off a superseded designation list; the currency flag closes.",
             effort="Low — the parser and delta already exist (audit/parse_injury_0715.py).",
             risk="Low — snapshots stay immutable; each revision becomes its own committed capture.",
             recommendation="Done for the nightly cycle by the 2026-11-14 refresh (nba2/pipeline/refresh.py + .github/workflows/refresh.yml); keep this item as the reminder for the game-day 13:00 ET report.",
             status="implemented by refresh session (nightly); game-day cadence open"),
        dict(id="S-A02", title="Make the 31 game-page URLs clickable",
             problem="The slate table's 'Official game page' column prints bare URLs as text; a reviewer must copy-paste to open them.",
             proposal="Wrap the cell in an <a href> at build time in nba2/pipeline/build_site.py.",
             benefit="One-click manual review of every row — the core verification workflow.",
             effort="Very low — one renderer change.",
             risk="None — the URLs are already verified 31/31 against official links.",
             recommendation="Do it.",
             status="owner decision"),
        dict(id="S-A03", title="Show the injury-report revision time in the page banner",
             problem="A reader cannot tell from the Injuries page which official revision the rows came from without opening a flag.",
             proposal="Add report_stamp_et + retrieved_at_utc to the policy strip on pages/injuries.html.",
             benefit="Currency is visible at a glance; stale data is self-announcing.",
             effort="Low — both fields already exist in the snapshot.",
             risk="None.",
             recommendation="Done — the 2026-11-14 refresh stamps report time and retrieval time on the Injuries page.",
             status="implemented by refresh session"),
        dict(id="S-A04", title="Settle the sealed ledger as soon as finals exist",
             problem="At proposal time settlement had run but measured nothing: data/settlement.json carried settled_at 2026-11-14T00:58Z with finals_snapshot null, so every leaderboard score, bet count and reward cell was blank and the gates stayed blocked — correctly, because the sealed games of 11/14–17 had not finished.",
             proposal="After each game day, commit data/raw/finals_<date>.json (official final scores, source-linked) and re-run python -m nba2.pipeline.settle.",
             benefit="First real measurement of line error and calibration — the 'remove luck' step becomes data, not design.",
             effort="Low — settle.py is written, tested, and already produces the pending record.",
             risk="None if finals come from official box scores; never impute a score.",
             recommendation="Run it after 11/14's games are final, then after each subsequent game day.",
             status="partially done — the finals ingest chain is live and verified (finals_all.json carries the nine official 11/13 finals; 0 of 49 sealed games have been played as of 2026-11-14); the nightly ingest job now fetches, merges and settles each game day automatically"),
        dict(id="S-A05", title="Pick one canonical site tree",
             problem="Six site trees now ship from one repo (root+pages/, docs/, dashboard/, originated/, verified/, backtest/); a reviewer can find different numbers on different trees.",
             proposal="Owner designates one canonical tree; the others get a banner linking to it. Candidate criteria: mechanical verifier + no unverified numbers (originated/ has a 24-check verifier; root+pages/ has the provenance lint over 1,100 rows; backtest/ has its own verify_backtest).",
             benefit="One truth surface; removes the reconciliation burden from every future session.",
             effort="Medium — mostly a decision plus five banner edits.",
             risk="Low — nothing is deleted; trees stay for audit.",
             recommendation="Decide before the next data refresh so only one tree is refreshed.",
             status="DECIDED 2026-11-14, CORRECTED the same day after direct probing (merge "
                    "reconciliation log, COORDINATION.md): the live URL serves the v2 site/ artifact "
                    "(pages/session-audit.html returns 404; the v2 dashboard serves at the root URL) — "
                    "the Pages API's build_type: legacy does NOT describe the served artifact, so the "
                    "earlier 'root+pages/ is canonical' claim was wrong. What remains for the owner is "
                    "S-27/Q-27: archive the root tree or keep it maintained as the sealed-ledger and "
                    "settlement surface (it stays CI-verified meanwhile: provenance lint over 1,143 "
                    "rows, semantic cross-check 83 pass / 0 fail). See FLAG-PAGES-01."),
        dict(id="S-A06", title="Publish settlement + currency KPIs on the landing page",
             problem="The dashboard shows games priced, tiers and reward units but not whether the data itself is current or when settlement last ran.",
             proposal="Add two KPI cards: 'injury revision: 19:30 ET (ingested 2026-11-14)' and 'settlement: PENDING (finals_snapshot null)'.",
             benefit="Decision-makers see data currency and grading progress without opening a page.",
             effort="Low — both values already exist in data/settlement.json and the injury snapshot metadata.",
             risk="None.",
             recommendation="Bundle with S-A04 once the first finals land.",
             status="owner decision"),
    ]
    rows = [make_row(it["id"], SRC_COORD, _flag_ids("FLAG-SUGG-01"), **it) for it in items]
    return table(
        rows,
        [("id", "ID"), ("title", "Suggestion"), ("problem", "Problem today"),
         ("proposal", "Proposed change"), ("benefit", "Expected decision-quality gain"),
         ("effort", "Effort"), ("risk", "Risk / cost"),
         ("recommendation", "Recommendation"), ("status", "Owner decision")],
        "Suggestions from session arena/72f9da58 — review before implementing",
        "Same review-before-implement rules as the main Suggestions Queue: nothing here has "
        "been implemented; each item stands or falls on its own.",
        "Raised 2026-11-14 from the verification round; owner decides. The main queue on the "
        "Suggestions page is unchanged.")


def build_verification_rows() -> dict:
    """Independent verification report — session arena/fc58f84f-nba2, run 2026-11-14 UTC.

    Every result below was produced in THIS session: the checker chain was re-run from a
    clean state, the published GitHub Pages site was re-fetched (not the local build), and
    the current window was re-read against live official NBA.com sources via the platform
    fetch tool (direct TLS to nba.com is egress-blocked in this sandbox). Values that could
    not be confirmed from an official source are left blank and flagged, never inferred.
    Source keys point at this session's committed audit artefacts under audit/2026-11-14-fc58f84f.
    """
    rows = [
        make_row("VS-01-checkers", SRC_VERIFY, (),
                 check="Full checker sweep (F-02)",
                 result="64/64 nba2 tests · 49/49 backtest tests · lint PASS (1139 rows / 39 tables) · "
                        "seal VERIFIED (c841e8f3…, 27 predictions) · verify_site PASS · check_links_all "
                        "PASS · check_site PASS · verify.js 24/24 · verify_backtest PASS · nba2.v2.check "
                        "0/0. crosscheck_site: 76 pass / 7 fail / 8 info.",
                 source="committed checker chain; raw output in audit/2026-11-14-fc58f84f/checker-run.txt",
                 classification="6 of the 7 crosscheck fails are pre-existing and already logged by prior "
                                "sessions (CC-SNAP-13, CC-PUB-05, CC-DER-05, CC-GATE-02, CC-SEAL-04, "
                                "CC-X-00); not introduced here."),
        make_row("VS-02-live-landing", SRC_VERIFY, (),
                 check="Live landing page re-fetch (F-03)",
                 result="SERVES the merged main tree at commit d510313: as-of 2026-11-14, 36-game slate, "
                        "27-prediction seal c841e8f3…, 79 open flags, nav intact.",
                 source="https://wingbangboozle1-lang.github.io/NBA2/ (fetched 2026-11-14)",
                 classification="confirmed live; matches committed build"),
        make_row("VS-03-live-picks", SRC_VERIFY, (),
                 check="Live picks page re-fetch (F-03)",
                 result="SERVES the current build: pick window 2026-11-14 → 11/17, every row a trigger "
                        "with 0.00% stake (no market price), each row carries a source cell.",
                 source="https://wingbangboozle1-lang.github.io/NBA2/pages/picks.html (fetched 2026-11-14)",
                 classification="confirmed live; policy (0% stake, no price) honoured"),
        make_row("VS-04-live-flagged", SRC_VERIFY, (),
                 check="Live flagged-review page re-fetch (F-03)",
                 result="SERVES: every open flag listed with its source link and required action; the page "
                        "is the deliverable for unverified values.",
                 source="https://wingbangboozle1-lang.github.io/NBA2/pages/flagged-review.html (fetched 2026-11-14)",
                 classification="confirmed live; source links intact"),
        make_row("VS-05-standings", SRC_VERIFY, (),
                 check="Fresh official standings re-read (F-04)",
                 result="12/30 committed W-L rows MATCH live nba.com/standings; 18/30 DRIFT — and the 18 "
                        "drifted rows are exactly the 18 teams that played the 9 games on 11/13 (the "
                        "committed snapshot is a pre-11/13-finals capture). Drift fully explained.",
                 source="https://www.nba.com/standings (fetched 2026-11-14); compare audit/2026-11-14-fc58f84f/official/records-vs-live.txt",
                 classification="verified live; the 18-row drift is expected and quantifies prior flag F-028"),
        make_row("VS-06-game-page", SRC_VERIFY, (),
                 check="Fresh official game page re-read (F-04)",
                 result="nba.com/game/nyk-vs-ind-0022600034 renders the official summary for 'Friday, "
                        "November 13th, 2026', corroborating the 11/13 slate and that game ID.",
                 source="https://www.nba.com/game/nyk-vs-ind-0022600034 (fetched 2026-11-14)",
                 classification="verified live; slate corroborated"),
        make_row("VS-07-injury", SRC_VERIFY, (),
                 check="Fresh official injury PDF re-read (F-04)",
                 result="11/13 19:30 ET injury report reachable in full; 6/6 spot-checked player rows "
                        "(Banchero, Haliburton, Curry, Morant, Markkanen, Antetokounmpo) match the committed "
                        "snapshot on team, status and reason.",
                 source="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf (fetched 2026-11-14)",
                 classification="verified live; committed injury transcription accurate"),
        make_row("VS-08-doc-fix", SRC_VERIFY, (),
                 check="CC-DOC-01 defect fixed (F-05/F-06)",
                 result="README row count corrected 1124 → 1139 to match the measured artefact count; "
                        "re-lint confirms 1139 rows / 39 tables. The one crosscheck fail this session "
                        "introduced-and-fixed; the other 6 fails are pre-existing.",
                 source="README.md (this session); lint output audit/2026-11-14-fc58f84f/checker-run.txt",
                 classification="fixed and re-verified"),
        make_row("VS-09-preexisting", SRC_VERIFY, (),
                 check="Pre-existing crosscheck fails (not this session's)",
                 result="6 fails carried on main before this session and logged by arena/72f9da58 for their "
                        "owners: ratings-snapshot labels (CC-SNAP-13), corroboration title counts "
                        "(CC-PUB-05), dual W-L source (CC-DER-05), leaderboard gate tally (CC-GATE-02), "
                        "seal-date heuristic (CC-SEAL-04), WSH/WAS team key (CC-X-00). Left untouched; "
                        "request logged, not silently edited.",
                 source="COORDINATION.md (arena/72f9da58 reconciliation note)",
                 classification="pre-existing; logged, not introduced, not fixed here"),
    ]
    return table(
        rows,
        [("check", "Check"), ("result", "What this session found"),
         ("source", "Source (official URL or committed artefact)"), ("classification", "Verdict")],
        "Independent verification report — session arena/fc58f84f-nba2",
        "A fresh, independent pass: the whole checker chain re-run, the live GitHub Pages site "
        "re-fetched, and the current window re-read against live official NBA.com sources. Values "
        "that could not be confirmed from an official source are blank and flagged, never inferred.",
        "Run 2026-11-14 UTC on branch arena/fc58f84f-nba2 (base d510313 = merged PR #43). "
        "Raw captures in audit/2026-11-14-fc58f84f/.",
    )


def _graded() -> dict | None:
    p = DATA / "graded_2026-11-13.json"
    return json.loads(p.read_text()) if p.exists() else None


def build_graded_rows() -> dict | None:
    """The 2026-11-13 card: our originated number next to the official final score."""
    g = _graded()
    if g is None:
        return None
    rows = []
    for r in g["games"]:
        rows.append(make_row(
            r["game_id"], SRC_DER_GRADED, ["FLAG-GRADE-01", "FLAG-GRADE-02", "FLAG-GRADE-03"],
            matchup=r["matchup"], date=r["date"],
            final=f"{r['away_pts']}–{r['home_pts']}" + (" (OT)" if r["ot"] else ""),
            our_spread_home=(f"{r['our_spread_home']:+.1f}" if r["our_spread_home"] is not None
                             else None),
            our_total=(f"{r['our_total_line']:.1f}" if r["our_total_line"] is not None else None),
            actual_margin_home=f"{r['actual_margin_home']:+d}",
            margin_error=f"{r['margin_error']:+.2f}",
            actual_total=f"{r['actual_total']}",
            total_error=f"{r['total_error']:+.2f}",
            winner_call=("correct" if r["winner_correct"] else "wrong"),
            source=r["source_url"],
        ))
    return table(
        rows,
        [("matchup", "Game"), ("date", "Date"), ("final", "Official final"),
         ("our_spread_home", "Our spread (home)"), ("our_total", "Our total"),
         ("actual_margin_home", "Actual margin (home)"), ("margin_error", "Margin error"),
         ("actual_total", "Actual total"), ("total_error", "Total error"),
         ("winner_call", "Winner call"), ("source", "Official game page")],
        "Graded card — 2026-11-13: our line vs the official final score",
        "Nine games, priced from the committed ratings snapshot that predates every tip, scored "
        "against the official NBA.com finals. This is the first card in the repository graded "
        "against real results rather than against itself. It is a walk-forward backtest, not a "
        "pre-registered ledger — see FLAG-GRADE-01 before reading anything into it.")


def build_graded_summary_rows() -> dict | None:
    """The measurements that decide whether the numbers above mean anything."""
    g = _graded()
    if g is None:
        return None
    m, v = g["metrics"], g["verdict"]

    def r(k: str, metric: str, model, baseline, verdict: str, note: str) -> Row:
        return make_row(
            k, SRC_DER_GRADED, ["FLAG-GRADE-01", "FLAG-GRADE-02", "FLAG-GRADE-03"],
            metric=metric,
            model=("" if model is None else str(model)),
            baseline=("" if baseline is None else str(baseline)),
            verdict=verdict, note=note)

    pm = m["permutation_tests"]
    lo, hi = v["straight_up_ci95"]
    rows = [
        r("grade-mae-margin", "Margin MAE (points)", v["model_margin_mae"],
          v["baseline_margin_mae"], "model closer, not significant",
          "Baseline is 'predict a 0-point home margin' — the no-information rule. "
          f"Improvement {pm['margin']['improvement_points']} pts/game, permutation p = "
          f"{pm['margin']['p_value']}."),
        r("grade-mae-total", "Total MAE (points)", v["model_total_mae"],
          v["baseline_total_mae"], "model closer, not significant",
          "Baseline is the league-mean total with no team information. Improvement "
          f"{pm['total']['improvement_points']} pts/game, permutation p = "
          f"{pm['total']['p_value']} — the largest effect on the card, still not established."),
        r("grade-su", "Straight-up winner accuracy",
          f"{m['straight_up_hits']}/{g['n_games']} = {v['straight_up_accuracy']:.1%}",
          "50%", "coin flip NOT excluded",
          f"Wilson 95% CI [{lo:.1%}, {hi:.1%}] spans 50%, so chance is not ruled out."),
        r("grade-auroc", "Winner AUROC", v["auroc"], "0.500",
          "above chance", "Ranking quality of the predicted margin; scale- and bias-free, so it "
          "cannot be inflated by tuning a constant."),
        r("grade-brier", "Brier score (win probability)", v["brier_model"],
          v["brier_baseline"], "marginally better",
          "Lower is better. A 0.25 baseline is a constant 50% forecast for every game."),
        r("grade-power", "Games needed for 80% power at a 55% hit rate",
          g["n_games"], m["power_to_detect_55pct_at_80pct_power"],
          "sample far too small",
          "At 5% significance. Nine games cannot establish a 55% hit rate, and no gate or "
          "reward may be released on it."),
        r("grade-roi", "ROI / CLV / stake", None, None, "not computable",
          "No market price exists in this repository, so there is nothing to beat and no "
          "return to measure. Blank by policy, not by omission."),
        r("grade-cover", "Games where the home team covered our own spread",
          sum(1 for c in g["cover_vs_our_line"] if c["result"] == "home covers"),
          f"{len(g['cover_vs_our_line'])} graded",
          "self-consistency only",
          "The line is ours, so covering it measures internal coherence, not market skill. "
          "Reported for completeness and for no other reason."),
    ]
    return table(
        rows,
        [("metric", "Measurement"), ("model", "Model"), ("baseline", "Baseline"),
         ("verdict", "Verdict"), ("note", "How to read it")],
        "What the graded card does and does not establish",
        "Every number below is computed from the nine games on the card. Where a comparison "
        "could not be computed honestly, the cell is blank and the reason is in the note.")


def build_standings_live_rows() -> dict | None:
    """Official NBA.com W-L, read live on 2026-11-14 (includes the completed 11/13 games)."""
    p = RAW / "standings_2026-11-14_official.json"
    if not p.exists():
        return None
    snap = json.loads(p.read_text())
    cols = snap["columns"]
    url = "https://www.nba.com/standings"
    rows = []
    for rec in snap["records"]:
        d = dict(zip(cols, rec))
        team_id = config.TEAM_ID.get(d["tricode"])
        rows.append(make_row(
            d["tricode"], SRC_STANDINGS_LIVE, (),
            tricode=d["tricode"], conference=d["conference"], rank=str(d["conf_rank"]),
            w=str(d["w"]), l=str(d["l"]), pct=d["win_pct"], gb=str(d["gb"]),
            conf=d["conf"], div=d["div"], home=d["home"], road=d["road"],
            last10=d["last10"], streak=d["streak"],
            source=(config.TEAM_PROFILE_URL.format(team_id=team_id,
                                                   slug=_slug(d["tricode"]))
                    if team_id else url),
        ))
    return table(
        rows,
        [("tricode", "Team"), ("conference", "Conf"), ("rank", "#"), ("w", "W"), ("l", "L"),
         ("pct", "WIN%"), ("gb", "GB"), ("conf", "Conf rec"), ("div", "Div rec"),
         ("home", "Home"), ("road", "Road"), ("last10", "L10"), ("streak", "Streak"),
         ("source", "Official team page")],
        "Official standings — NBA.com, read live 2026-11-14",
        "The first win-loss capture in this repository taken from an official NBA page; every "
        "earlier snapshot used basketball-reference for W-L (FLAG-RAT-01). Includes the "
        "completed 2026-11-13 games. Clubs have played 10-14 games, so win counts are not "
        "comparable across rows — the order is by win percentage, as on the official page.")


def _slug(tricode: str) -> str:
    return {"ATL": "hawks", "BOS": "celtics", "BKN": "nets", "CHA": "hornets", "CHI": "bulls",
            "CLE": "cavaliers", "DAL": "mavericks", "DEN": "nuggets", "DET": "pistons",
            "GSW": "warriors", "HOU": "rockets", "IND": "pacers", "LAC": "clippers",
            "LAL": "lakers", "MEM": "grizzlies", "MIA": "heat", "MIL": "bucks",
            "MIN": "timberwolves", "NOP": "pelicans", "NYK": "knicks", "OKC": "thunder",
            "ORL": "magic", "PHI": "sixers", "PHX": "suns", "POR": "blazers", "SAC": "kings",
            "SAS": "spurs", "TOR": "raptors", "UTA": "jazz", "WAS": "wizards"}.get(tricode, "")


def build_injury_1114_rows() -> dict | None:
    """Per-club filing state for the 11/14-11/15 slates, from the 05:00 AM ET release."""
    p = RAW / "injury_report_2026-11-14_0500AM.json"
    if not p.exists():
        return None
    snap = json.loads(p.read_text())
    pdf = snap["provenance"]["url"]
    by_game: dict[tuple[str, str], list[dict]] = {}
    for r in snap["records"]:
        by_game.setdefault((r["game_date"], r["matchup"]), []).append(r)

    rows = []
    for (date, matchup), recs in sorted(by_game.items()):
        clubs = sorted({r["team"] for r in recs})
        filed = [r for r in recs if not r["not_yet_submitted"]]
        nys = [r["team"] for r in recs if r["not_yet_submitted"]]
        out = sum(1 for r in filed if r["current_status"] == "Out")
        ques = sum(1 for r in filed if r["current_status"] == "Questionable")
        prob = sum(1 for r in filed if r["current_status"] == "Probable")
        avail = sum(1 for r in filed if r["current_status"] == "Available")
        rows.append(make_row(
            f"{date}-{matchup}", SRC_INJ_1114_AM, (),
            date=date, matchup=matchup,
            clubs_filed=f"{len(clubs) - len(nys)}/{len(clubs)}",
            out=str(out), questionable=str(ques), probable=str(prob), available=str(avail),
            not_submitted=(", ".join(nys) if nys else "none"),
            players=", ".join(sorted(r["player"] for r in filed)) or "none filed",
            source=pdf,
        ))
    return table(
        rows,
        [("date", "Game date"), ("matchup", "Matchup"), ("clubs_filed", "Clubs filed"),
         ("out", "Out"), ("questionable", "Questionable"), ("probable", "Probable"),
         ("available", "Available"), ("not_submitted", "NOT YET SUBMITTED"),
         ("players", "Named designations"), ("source", "Official PDF")],
        "Filing state at the 11/14 05:00 AM ET release",
        "Read straight from the official referee-operations PDF. 'NOT YET SUBMITTED' is the "
        "document's own wording for a club that has filed nothing for that game — at this "
        "release the 11 a.m.-1 p.m. local game-day window had not yet opened for the 11/14 "
        "games, and the 11/15 filings were not yet due (FLAG-INJ-08). Counts are filing counts, "
        "not injury impact: no minutes or production figure is asserted anywhere on this site.")


def input_digest() -> str:
    """sha256 over every committed input, so 'the same inputs produce the same bytes' is checkable.

    The build is deliberately *idempotent*: if the inputs have not changed since the last build,
    the previously published generated_at_utc is reused instead of stamped fresh. That is what
    makes CI's "committed artefacts must equal a rebuild" step meaningful — a timestamp that
    moved on every run would make the check pass or fail at random.
    """
    import hashlib
    h = hashlib.sha256()
    names = [config.SNAPSHOT_SLATE, config.SNAPSHOT_RATINGS, config.SNAPSHOT_INJURY,
             SNAPSHOT_INJURY_WINDOW, config.SNAPSHOT_CONTEXT, config.SNAPSHOT_LEADERS,
             config.SNAPSHOT_TIMES, config.SNAPSHOT_TIMES_PRIOR,
             "ratings_recheck_2026-11-14.json",
             config.SNAPSHOT_STANDINGS_OFFICIAL, config.SNAPSHOT_INJURY_LATEST,
             config.SNAPSHOT_FINALS]
    for n in names:
        f = RAW / n
        if f.exists():
            h.update(n.encode())
            h.update(f.read_bytes())
    for rel in ("requirements/REQUIREMENTS.json", "requirements/QUESTIONS.json",
                "requirements/REPO_REVIEW.json", "suggestions/SUGGESTIONS.json",
                "nba2/data/picks.json", "nba2/data/records.json", "nba2/data/injuries.json",
                "nba2/data/flagged.json", "data/our-lines.csv", "data/settlement.json",
                "data/verified/injuries_2026-11-13_0515PM.json",
                "audit/injury_delta_0415_to_0715.json",
                "audit/official_schedule_2026-11-14.json",
                "audit/injury_report_2026-11-13_0715PM.json"):
        f = ROOT / rel
        if f.exists():
            h.update(rel.encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def _content_stamp() -> str:
    """Newest retrieval timestamp recorded inside the committed snapshots, as 'YYYY-MM-DD HH:MM UTC'."""
    newest = ""
    for f in sorted(RAW.glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        for k in ("retrieved_at_utc", "as_of", "retrieved_utc"):
            v = d.get(k)
            if isinstance(v, str) and v > newest:
                newest = v
    # normalise any of the accepted forms into the published one
    if newest.endswith("Z"):
        newest = newest[:-1]
    if "T" in newest:
        newest = newest.replace("T", " ")
    if len(newest) >= 16:
        return newest[:16] + " UTC"
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")



# --------------------------------------------------------------------------- added by
# session arena/6650be4d-nba2 (2026-11-14 10:25 UTC). Every value below comes from an
# official document fetched in that session; nothing is inferred.
def build_official_standings_rows(official: dict[str, dict]) -> dict:
    rows = []
    for tc in sorted(official):
        d = official[tc]
        g = d["w"] + d["l"]
        rows.append(make_row(
            f"std-{tc}", SRC_STANDINGS_OFFICIAL, (),
            team=d["name"], tricode=tc, wl=f"{d['w']}-{d['l']}",
            pct=f"{d['w'] / g:.3f}" if g else None,
            home=d["home"], road=d["road"], conf=d["conf"], div=d["div"],
        ))
    return table(rows, [("team", "Team"), ("tricode", "Tricode"), ("wl", "W-L (official)"),
                        ("pct", "Win %"), ("home", "Home"), ("road", "Road"),
                        ("conf", "Conference"), ("div", "Division")],
                 "Official standings — NBA.com, 2026-11-14 (the live record)",
                 "The league's own table, read in this session. It is the reference the model is "
                 "checked against, and it is the only place in this repository where a win-loss "
                 "record comes straight from NBA.com rather than from a third-party table. "
                 "18 of the 30 clubs differ from the 2026-11-13 ratings snapshot because the nine "
                 "2026-11-13 games were played in between; the per-club delta is published on the "
                 "Methodology page.",
                 "https://www.nba.com/standings")


def build_latest_injury_tables() -> tuple[dict, dict]:
    """The newest official injury release (2026-11-14 05:00 a.m ET).

    This release supersedes the 19:30 ET release for the pick window: it carries the same
    2026-11-14 designations (verified row by row below), adds the 2026-11-15 slots, and — the
    reason it matters — repeats the team on every row, so the page-break blank team column
    that produced FLAG-INJ-08 cannot occur.
    """
    rows_l, _raw = INJ.load(RAW / config.SNAPSHOT_INJURY_LATEST)
    detail = []
    for i, r in enumerate(rows_l):
        fl = ["FLAG-INJ-02"]
        if r.status == "NOT YET SUBMITTED":
            fl.append("FLAG-INJ-04")
        detail.append(make_row(
            f"inj0500-{i}", SRC_INJ_0500, _flag_ids(*fl),
            game_date=r.game_date, time_et=r.time_et or None, matchup=r.matchup, team=r.team,
            player=r.player or "—", status=r.status, reason=r.reason,
            p_play=f"{r.p_play:.2f}" if r.p_play is not None else None,
            minutes_impact=None, production_impact=None, line_adjustment=None,
            attribution="explicit (team printed on every row)",
        ))
    detail_tbl = table(detail, [("game_date", "Game date"), ("time_et", "Tip (ET)"),
                                ("matchup", "Matchup"), ("team", "Team"), ("player", "Player"),
                                ("status", "Official status"), ("reason", "Reason"),
                                ("p_play", "Our P(plays)"), ("minutes_impact", "Minutes impact"),
                                ("production_impact", "Production impact"),
                                ("line_adjustment", "Line adjustment"), ("attribution", "Row attribution")],
                       "Official NBA injury report — 2026-11-14 05:00 a.m ET release (newest at build time)",
                       "The newest release the official index lists at build time. It carries the "
                       "2026-11-14 designations and, for the first time, the 2026-11-15 slots "
                       "(every one of them still NOT YET SUBMITTED, because the 5 p.m. local "
                       "day-before deadline for those games had not passed). The three impact "
                       "columns are blank by policy: the report carries no minutes, usage or "
                       "production data, so any number there would be invented.",
                       "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf")

    rot = INJ.rotation_index(rows_l)
    rrows = []
    for tri in sorted(rot):
        d = rot[tri]
        rrows.append(make_row(
            f"rot0500-{tri}", SRC_INJ_0500, _flag_ids("FLAG-INJ-02", "FLAG-INJ-07"),
            team=d["team"], out=d["out"], doubtful=d["doubtful"], questionable=d["questionable"],
            probable=d["probable"], available=d["available_listed"],
            two_way_or_susp=d["gleague_or_suspension"], not_yet_submitted=d["not_yet_submitted"],
            exp_missing=f"{d['expected_missing_bodies']:.2f}",
            sd=f"±{d['missing_body_sd']:.2f}" if d["missing_body_sd"] else "±0.00",
            floor=d["rotation_floor"], risk=INJ.risk_tier(d),
            games=", ".join(d["games"]),
        ))
    rot_tbl = table(rrows, [("team", "Team"), ("out", "Out"), ("doubtful", "Doubtful"),
                            ("questionable", "Questionable"), ("probable", "Probable"),
                            ("available", "Available"), ("two_way_or_susp", "G-League/suspension"),
                            ("not_yet_submitted", "Not yet submitted"),
                            ("exp_missing", "Expected bodies missing"), ("sd", "Band"),
                            ("floor", "Rotation floor"), ("risk", "Risk tier"),
                            ("games", "Games affected")],
                   "Rotation-body impact — newest official release (11/14 05:00 a.m ET)",
                   "Same body-counting arithmetic as the other injury tables, applied to the newest "
                   "release. A team whose row says NOT YET SUBMITTED contributes a placeholder, not a "
                   "body count: their designations simply have not been filed yet.",
                   "Derived in nba2/models/injuries.py from the 11/14 05:00 a.m ET official release.")
    return detail_tbl, rot_tbl


def build_injury_release_delta_rows() -> dict:
    """What changed between the release the site used to publish and the newest one."""
    old_rows, _ = INJ.load(RAW / config.SNAPSHOT_INJURY)
    new_rows, _ = INJ.load(RAW / config.SNAPSHOT_INJURY_LATEST)

    def key(r):
        return (r.game_date, r.matchup, r.player or "", r.team)

    old = {key(r): r for r in old_rows if r.game_date == "2026-11-14"}
    new = {key(r): r for r in new_rows}
    rows = []
    for k in sorted(set(old) | set(new)):
        o, n = old.get(k), new.get(k)
        if o is not None and n is not None:
            if o.status == n.status and o.reason == n.reason and o.team == n.team:
                verdict, fl = "unchanged", ()
            elif o.team != n.team:
                verdict = (f"TEAM ATTRIBUTION CORRECTED — the 19:30 ET transcript put this row under "
                           f"{o.team}; the 05:00 a.m ET release prints {n.team} on the row")
                fl = ("FLAG-INJ-08",)
            else:
                verdict = f"status/reason changed: {o.status} / {o.reason} -> {n.status} / {n.reason}"
                fl = ("FLAG-INJ-09",)
            rows.append(make_row(
                f"delta-{k[0]}-{k[2] or k[3]}", SRC_INJ_0500, _flag_ids(*fl),
                game_date=k[0], matchup=k[1], player=k[2] or "—",
                team_1930=(o.team if o else None), team_0500=(n.team if n else None),
                status_1930=(o.status if o else None), status_0500=(n.status if n else None),
                verdict=verdict,
            ))
    return table(rows, [("game_date", "Game date"), ("matchup", "Matchup"), ("player", "Player"),
                        ("team_1930", "Team in the 19:30 ET transcript"),
                        ("team_0500", "Team in the 05:00 a.m ET release"),
                        ("status_1930", "Status (19:30 ET)"), ("status_0500", "Status (05:00 a.m ET)"),
                        ("verdict", "Change")],
                 "Injury release delta — 19:30 ET (published before) vs 05:00 a.m ET (published now)",
                 "An injury report is re-issued several times a day and a player who was Questionable "
                 "at 19:30 can be Out at 05:00. The diff is published so the churn is visible instead "
                 "of hidden behind whichever release happened to be latest.",
                 "Both documents are official; the diff is computed in-repo.")


def build_finals_grade_rows(lines: list[LN.GameLine]) -> dict:
    """The nine 2026-11-13 games, graded against the lines this model published for them.

    These are day-before CONTEXT games: they are in neither sealed ledger, so this is a model
    check and never a settled registered forecast. It is published because the numbers are real
    and because a reader is entitled to see how the published lines behaved the first time the
    league produced a result for them.
    """
    raw = json.loads((RAW / config.SNAPSHOT_FINALS).read_text())
    finals = {f["game_id"]: f for f in raw["records"]}
    rows = []
    mae_margin, mae_total, hits, n = 0.0, 0.0, 0, 0
    for l in lines:
        f = finals.get(l.game_id)
        if not f:
            continue
        actual_margin = f["home_pts"] - f["away_pts"]
        actual_total = f["home_pts"] + f["away_pts"]
        our_margin = l.margin
        our_total = l.total_line
        err_m = abs(actual_margin - our_margin) if our_margin is not None else None
        err_t = abs(actual_total - our_total) if our_total is not None else None
        side = ("home" if actual_margin > 0 else "away") if actual_margin != 0 else "push"
        lean_hit = ("yes" if l.lean == side else
                    ("no" if l.lean != "no-lean" else "no lean published"))
        if err_m is not None:
            mae_margin += err_m
        if err_t is not None:
            mae_total += err_t
        n += 1
        if l.lean == side:
            hits += 1
        rows.append(make_row(
            f"final-{l.game_id}", SRC_FINALS, _flag_ids("FLAG-SET-02"),
            game_id=l.game_id, date=l.date, matchup=f"{l.away} @ {l.home}",
            final=f"{f['away_pts']}-{f['home_pts']}" + (" (OT)" if f.get("overtime") else ""),
            actual_margin=(f"{actual_margin:+d}"), actual_total=f"{actual_total}",
            our_margin=(f"{our_margin:+.2f}" if our_margin is not None else None),
            our_total=(f"{our_total:.1f}" if our_total is not None else None),
            margin_error=(f"{err_m:.2f}" if err_m is not None else None),
            total_error=(f"{err_t:.1f}" if err_t is not None else None),
            our_lean=l.lean, lean_hit=lean_hit,
        ))
    summary = (f"n={n} · margin MAE {mae_margin / n:.2f} · total MAE {mae_total / n:.2f} · "
               f"lean correct {hits}/{n}") if n else "no games graded"
    return table(rows, [("game_id", "Official game ID"), ("date", "Date"), ("matchup", "Matchup"),
                        ("final", "Official final"), ("actual_margin", "Actual margin"),
                        ("actual_total", "Actual total"), ("our_margin", "Our margin"),
                        ("our_total", "Our total"), ("margin_error", "Margin error"),
                        ("total_error", "Total error"), ("our_lean", "Our lean"),
                        ("lean_hit", "Lean correct?")],
                 "First grade of the published lines — the nine 2026-11-13 context games",
                 "The nine games that had already been played when this window was priced. They are "
                 "day-before context, NOT sealed predictions, so this is a model check and never a "
                 "settled bet: neither sealed ledger covers them (FLAG-SET-02). Nine games cannot "
                 "support a promotion of any kind, and the table says so. " + summary,
                 "Finals from the official schedule page; the lines from this site's own published "
                 "output for the same games.")



def build_ratings_selfcheck_rows() -> dict:
    """The ratings snapshot's OWN consistency labels, recomputed from its own rows.

    A snapshot that claims "FAIL" for a check that passes is not a harmless typo: the
    published flag quotes it, so the site would exclude a usable column for the wrong reason.
    """
    raw = json.loads((RAW / config.SNAPSHOT_RATINGS).read_text())
    cols = raw["columns"]
    rows = [dict(zip(cols, r)) for r in raw["records"]]
    cw = sum(r["close_w"] for r in rows)
    cl = sum(r["close_l"] for r in rows)
    bw = sum(r["blowout_w"] for r in rows)
    bl = sum(r["blowout_l"] for r in rows)
    viol = [r["tricode"] for r in rows
            if r["close_w"] + r["close_l"] + r["blowout_w"] + r["blowout_l"] > r["w"] + r["l"]]
    home_ok = all(r["home_w"] + r["home_l"] + r["road_w"] + r["road_l"] == r["w"] + r["l"]
                   for r in rows)
    checks = [
        ("home+road split equals games played, every team",
         "PASS", "PASS — 30/30" if home_ok else "FAIL",
         "Home/road wins and losses sum to the club's games played."),
        ("close+blowout games <= games played, every team",
         "PASS (middle-margin games account for the remainder)",
         f"FAIL — {len(viol)} of 30 teams violate it",
         "A club cannot play more close and blowout games than it played in total. "
         f"Violations: {', '.join(viol)}."),
        ("sum(close_w) == sum(close_l) league-wide",
         "FAIL - see flags", f"PASS — {cw} == {cl}",
         "Each close game is one win for one club and one loss for another."),
        ("sum(blowout_w) == sum(blowout_l) league-wide",
         "FAIL - see flags", f"PASS — {bw} == {bl}",
         "Each blowout game is one win for one club and one loss for another."),
    ]
    out = []
    for i, (name, claimed, recomputed, meaning) in enumerate(checks):
        agrees = claimed.split(" ")[0].upper() == recomputed.split(" ")[0].upper()
        out.append(make_row(
            f"rat-check-{i}", SRC_RAT, _flag_ids("FLAG-RAT-02"),
            check=name, claimed=claimed, recomputed=recomputed,
            verdict=("agrees" if agrees else "DISAGREES — the snapshot's label was wrong"),
            meaning=meaning,
        ))
    return table(out, [("check", "Consistency check"), ("claimed", "Label in the snapshot"),
                        ("recomputed", "Recomputed from the snapshot's own rows"),
                        ("verdict", "Verdict"), ("meaning", "What the check means")],
                 "Source self-check — the ratings snapshot's own labels, recomputed",
                 "A capture that checks itself is only useful if the check is right. These four checks are "
                 "recomputed from the snapshot's own 30 rows and compared with the labels it carries. Two "
                 "labels were wrong (the league-wide sums DO balance) and one was wrong in the other "
                 "direction (the per-team bound does NOT hold). The snapshot's correction block records "
                 "the original text verbatim.",
                 "data/raw/team_ratings_2026-11-13.json (third party); recomputation in-repo")

def build() -> dict:
    # Flags recorded *inside* the data snapshots are registered from the files themselves, so the
    # Flagged page can never drift from the provenance stored with the data.
    for fname, skey, area in ((config.SNAPSHOT_SLATE, "nba_schedule", "slate"),
                              (config.SNAPSHOT_RATINGS, "bref_standings", "ratings"),
                              (config.SNAPSHOT_INJURY, "nba_injury_pdf", "injuries"),
                              (SNAPSHOT_INJURY_WINDOW, "nba_injury_pdf_1114", "injuries"),
                              (config.SNAPSHOT_CONTEXT, "nba_schedule", "slate context")):
        snap = json.loads((RAW / fname).read_text())
        for f in snap.get("flags", []):
            flag(f["id"], f.get("severity", "medium"), area, f["issue"],
                 SOURCES[skey].url, f.get("action_required", f.get("action", "")))
    digest = input_digest()
    prev = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text()).get("meta", {})
        except Exception:
            prev = {}
    same_inputs = prev.get("input_digest") == digest
    # A build must be a pure function of its inputs, so the stamp is too. Reusing the previous
    # stamp only when the digest matches still made a *clean checkout* produce a different file
    # from a rebuild (no previous file -> fresh clock stamp), which broke "committed == rebuilt"
    # on every fresh clone and in CI. The stamp is therefore pinned to the newest committed input
    # mtime (rounded to the minute), which travels with the data through git and needs no clock.
    # Set NBA2_BUILD_STAMP="YYYY-MM-DD HH:MM UTC" to override explicitly when a new snapshot lands.
    # The stamp must be a function of the committed bytes alone: git preserves content, not
    # mtimes, and a clone rewrites every mtime to the clone time. So take the newest
    # `retrieved_at_utc` recorded inside the snapshots themselves — a value that travels with the
    # data and is honest about when the inputs were captured. Rebuilding from the same snapshots
    # therefore reproduces the same stamp, which is what makes "committed == rebuilt" checkable.
    stamp = os.environ.get("NBA2_BUILD_STAMP") or _content_stamp()
    data_as_of = json.loads((RAW / config.SNAPSHOT_SLATE).read_text())["as_of"]
    model = RT.build(ROOT)
    games, slate_raw = LN.load_slate(RAW / config.SNAPSHOT_SLATE)
    inj_rows, inj_raw = INJ.load(RAW / config.SNAPSHOT_INJURY)
    injw_rows, injw_raw = INJ.load(RAW / SNAPSHOT_INJURY_WINDOW)
    anomalies_raw = json.loads((RAW / "slate_context_2026-11-17.json").read_text())
    requirements = json.loads((ROOT / "requirements" / "REQUIREMENTS.json").read_text())
    questions = json.loads((ROOT / "requirements" / "QUESTIONS.json").read_text())
    suggestions = json.loads((ROOT / "suggestions" / "SUGGESTIONS.json").read_text())
    repo_review = json.loads((ROOT / "requirements" / "REPO_REVIEW.json").read_text())["requirements"]

    by_team = INJ.by_team(inj_rows)
    lines = LN.price_slate(model, games, by_team)
    win_detail, win_rot = build_window_injury_tables()
    spots = GF.schedule_spots(games, min(g["date"] for g in games), max(g["date"] for g in games))
    flow = GF.game_flow_inputs(games, spots)

    # measurements deliberately absent -> blocked, so leaderboard has no score.
    measurements = {s["id"]: {"n_games_predicted": len(lines), "min_stability": None,
                              "injury_blind_share": 1.0, "point_in_time_verified": False}
                    for s in config.STRATEGIES}
    bet_sets = {}
    entries = LB.build(config.STRATEGIES, measurements, bet_sets)
    rewards = LB.reward_allocation(entries)
    results_by_strategy = {e.strategy_id: e.results for e in entries}

    seal_hdr = None
    ledger_path = RAW / "ledger" / f"sealed-{data_as_of}.json"
    if ledger_path.exists():
        doc = json.loads(ledger_path.read_text())
        seal_hdr = doc["header"]

    xlines, xrecords, xinjuries, xsurfaces, n_xflags = XSESS.build_all(
        model, lines, inj_rows)
    inj_theirs_raw = XSESS._load(XSESS.THEIRS / "injuries.json") or {"games": []}
    picks_theirs = XSESS._load(XSESS.THEIRS / "picks.json") or {"lines": []}
    xadj = ADJ.adjudicate(inj_theirs_raw, inj_rows)
    x3 = ADJ.reconcile_three_way(lines, picks_theirs)
    x = {"lines": xlines, "records": xrecords, "injuries": xinjuries, "inventory": xsurfaces}

    official_standings = load_official_standings()
    sections = {
        "ratings": build_ratings_rows(model, official_standings),
        "standings_official": build_official_standings_rows(official_standings),
        "ratings_selfcheck": build_ratings_selfcheck_rows(),
        "finals_grade": build_finals_grade_rows(lines),
        "injury_delta_release": build_injury_release_delta_rows(),
        "calibration": build_calibration_rows(model),
        "luck": build_luck_rows(model),
        "slate": build_slate_rows(games),
        "lines": build_lines_rows(model, lines),
        "picks": build_picks_rows(lines, data_as_of),
        "injuries": build_injury_tables(inj_rows)[0],
        "rotation": build_injury_tables(inj_rows)[1],
        "injuries_window": win_detail,
        "rotation_window": win_rot,
        "injuries_latest": build_latest_injury_tables()[0],
        "rotation_latest": build_latest_injury_tables()[1],
        "availability_window": build_availability_window_rows(games),
        "gameflow": build_gameflow_rows(games, spots, flow),
        "anomalies": build_anomaly_rows(anomalies_raw["records"], {g["game_id"] for g in games}),
        "corroboration": build_corroboration_rows(games, load_time_corroboration()),
        "leaders": build_leader_rows(inj_rows, RAW / "team_leaders_2026-11-13.json"),
        "correlation": build_correlation_rows(model, lines),
        "parlays": build_parlay_rows(model, lines),
        "parlays_xg": build_cross_game_rows(lines),
        "parlay_costs": build_cost_rows(),
        "leaderboard": build_strategy_rows(entries),
        "gate_matrix": build_gate_rows(results_by_strategy),
        "gates": build_gate_spec_rows(),
        "params": build_param_rows(),
        "props": build_props_rows(),
        "repo_review": build_repo_review_rows(repo_review),
        "requirements": build_generic(
            "requirements", requirements["requirements"],
            [("id", "ID"), ("category", "Category"), ("requirement", "Requirement"),
             ("acceptance", "Acceptance criteria"), ("status", "Status"), ("owner", "Owner"),
             ("how", "How it is met / what blocks it"), ("priority", "P")],
            "coordination", ["FLAG-REQ-01"],
            "Requirements register",
            "Every requirement in the brief, decomposed to something a reviewer can say yes/no to. "
            "Status is only 'met' when the artefact exists in the repository.",
            requirements["source_note"]),
        "questions": build_generic(
            "questions", questions["questions"],
            [("id", "ID"), ("question", "Question that blocks a decision"),
             ("have", "What we already have"), ("missing", "What we do not have"),
             ("how", "How to find out"), ("impact", "What changes once answered"),
             ("severity", "Blocking?")],
            "coordination", ["FLAG-QUEST-01"],
            "Open questions — the decision list",
            "Ordered by how much money a wrong answer costs, not by how interesting they are. Each row states "
            "what is already known so nobody re-asks it.", questions["source_note"]),
        "suggestions": build_generic(
            "suggestions", suggestions["suggestions"],
            [("id", "ID"), ("title", "Suggestion"), ("problem", "Problem today"),
             ("proposal", "Proposed change"), ("benefit", "Expected decision-quality gain"),
             ("effort", "Effort"), ("risk", "Risk / cost"), ("recommendation", "Recommendation"),
             ("status", "Owner decision")],
            "coordination", ["FLAG-SUGG-01"],
            "Site-improvement suggestions — review queue",
            "Each item is written so a reviewer can accept, reject or defer it on its own merits. "
            "Nothing is applied silently: the Status column is the record of what has been "
            "decided or already built, and every item still stands or falls on its own.",
            suggestions["source_note"]),
        "xlines": x["lines"], "xrecords": x["records"], "xinjuries": x["injuries"],
        "surfaces": x["inventory"],
        "x3way": x3, "xadjudicate": xadj,
        "graded": build_graded_rows(),
        "graded_summary": build_graded_summary_rows(),
        "standings_live": build_standings_live_rows(),
        "injury_1114": build_injury_1114_rows(),
        "audit": build_audit_rows(),
        "injury_delta": build_injury_delta_rows(),
        "audit_suggestions": build_audit_suggestions_rows(),
        "verification": build_verification_rows(),
        "flags": None,   # filled below
        "sources": None,
    }

    sections = {k: v for k, v in sections.items() if v is not None}

    flag_rows = [make_row(
        f.id, SRC_COORD, _flag_ids(f.id),
        id=f.id, severity=f.severity, area=f.area, statement=f.statement,
        source=f.source_url, action=f.action,
    ) for f in all_flags()]
    sections["flags"] = table(flag_rows, [("id", "Flag"), ("severity", "Severity"), ("area", "Area"),
                                          ("statement", "What is unverified / wrong"),
                                          ("source", "Source to check"), ("action", "Action required")],
                              "Flagged for review — every unverified value on this site",
                              "This page is the deliverable. If a number is not here and not blank, it was "
                              "confirmed against an official source; if you find otherwise, that is a bug.",
                              "Also mirrored in COORDINATION.md")

    # the register is a table ABOUT sources, so its own source is the code that holds it
    src_rows = [make_row(
        k, "source_register", _flag_ids("FLAG-SRC-01") if v.cls != Src.OFFICIAL else (),
        src_id=k, src_name=v.name, src_url=v.url or None, src_class=v.label,
        src_note=v.note,
        usable=("yes" if v.url and v.cls != Src.BLOCKED else "no — blocked"),
    ) for k, v in SOURCES.items()]
    sections["sources"] = table(src_rows, [("src_id", "Key"), ("src_name", "Source"), ("src_url", "URL"),
                                           ("src_class", "Class"), ("usable", "Usable in build"),
                                           ("src_note", "Note")],
                               "Source register + verification log",
                               "Retrieval times are UTC. Anything marked 'no — blocked' contributed no value "
                               "to any table on this site.",
                               "retrieved 2026-11-13 22:25–22:40 UTC (prior sessions) and 2026-11-14 "
                               "~01:05 UTC (this refresh)")

    return {
        "meta": {
            "generated_at_utc": stamp,
            "input_digest": digest,
            # Report the property, do not report this run's luck. `same_inputs` is True only when a
            # previous build happened to exist with a matching digest; on a fresh clone it is False
            # even though the build is perfectly reproducible. Publishing it made the committed
            # artefact different from a rebuild of a clean checkout, which is the exact failure the
            # determinism test exists to catch (it was failing on every clean CI clone).
            "build_is_idempotent": True,
            "snapshot_as_of": data_as_of,
            "slate_window": (
                f"{min(g['date'] for g in games)} → {max(g['date'] for g in games)} "
                f"(pick window {data_as_of} → {max(g['date'] for g in games)}, today + 3 days)"
            ),
            "games": len(games), "teams": len(model.order),
            "injury_rows": len(inj_rows),
            "injury_status_rows": sum(1 for r in inj_rows if r.status != "NOT YET SUBMITTED"),
            "injury_placeholder_rows": sum(1 for r in inj_rows if r.status == "NOT YET SUBMITTED"),
            "injury_attribution_continuation": sum(1 for r in inj_rows if r.attribution == "C"),
            "injury_window_rows": len(injw_rows),
            "injury_window_status_rows": sum(1 for r in injw_rows if r.status != "NOT YET SUBMITTED"),
            "injury_window_placeholder_rows": sum(1 for r in injw_rows if r.status == "NOT YET SUBMITTED"),
            "tiers": LN.market_summary(lines)["tiers"],
            "calibration": {"margin_sd": model.cal.margin_sd, "hca_points": model.cal.hca_points,
                            "league_avg_points": model.cal.league_avg_points,
                            "rmse_wins": model.cal.rmse_wins,
                            "rmse_baseline_wins": model.cal.rmse_baseline_wins,
                            "home_win_rate": model.cal.home_win_rate},
            "gates_passed": sum(1 for rs in results_by_strategy.values() for r in rs if r.result == G.PASS),
            "gates_total": sum(len(rs) for rs in results_by_strategy.values()),
            "seal": seal_hdr,
            "rewards": rewards,
            "policy": "no value is published without a source; unverified values are blank and flagged",
        },
        "sections": sections,
    }


def main() -> None:
    # register the extra flags referenced above before tables are built
    # every parameter that is not verified/derived gets its own flag, so the Flagged page is a
    # complete list of "numbers nobody ratified" rather than a curated subset
    for k, prm in config.PARAMS.items():
        if prm.status not in ("verified", "derived"):
            flag(f"FLAG-PARAM-{k.upper()}",
                 "high" if prm.status == "unknown" else "medium", "parameter",
                 f"{k} = {prm.value!r} {prm.unit} has status '{prm.status}': {prm.rationale}",
                 prm.source or SOURCES[SRC_DER].url,
                 f"Ratify, measure or remove. Sensitivity band: "
                 f"{'not swept' if not prm.sensitivity else f'{prm.sensitivity[0]} … {prm.sensitivity[1]}'}")
    flag("FLAG-PARAM-01", "low", "model", "σ (margin sd) is fitted from a third-party ratings table, not "
         "measured from game-level margins; a ±10% change in σ moves every win probability on the site.",
         "https://www.basketball-reference.com/leagues/NBA_2027_standings.html",
         "Re-fit σ once official game results are ingested (R-103).")
    flag("FLAG-PARAM-02", "medium", "model", "Home-court advantage is weakly identified by the current fit: "
         "the joint fit returns 1.53 pts while the verified league home win rate of 51.15% implies ≈0.4 pts. "
         "The two disagree, so HCA is published with a ±(0.5, 2.0) band and feeds the sensitivity check.",
         "https://www.basketball-reference.com/leagues/NBA_2027_standings.html",
         "Fit HCA from game-level home/away margins; do not adopt a literature constant.")
    flag("FLAG-PARAM-03", "low", "model", "Reliability shrinkage assumes each team plays half its games at "
         "home and that schedule difficulty is fully captured by SRS. Neither is exact at 12 games.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/ratings.py",
         "Use the real schedule once it is ingested.")
    flag("FLAG-PARAM-04", "high", "model", "The total-line SD is a placeholder (20.0) — no game-level totals "
         "existed when it was set. Official finals history now exists (backtest tree, 155 games), but a "
         "re-fit changes published numbers and is an owner decision (S-04). It affects parlay levels, not "
         "the ratio comparisons.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/correlation.py",
         "Estimate from settled games before publishing any parlay price.")
    flag("FLAG-PARAM-05", "medium", "model", "Thresholds marked unratified (disagreement tolerance 2.0 pts, "
         "Tier-A conviction 0.20σ, trigger hurdle 1.5 pts, status→P(plays) weights) are our choices with no "
         "external source. They must be ratified by the owner before any money is risked.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/config.py", "Owner decision, see Suggestions S-04.")
    flag("FLAG-LINE-01", "high", "lines", "Lines are built from a third-party standings snapshot of ~12 games "
         "per team; they are a research baseline, not a bookmaking number.",
         "https://www.basketball-reference.com/leagues/NBA_2027_standings.html", "Validate on 30 days of sealed predictions.")
    flag("FLAG-LINE-02", "medium", "lines", "Games marked Tier C are those where the two base ratings disagree "
         "beyond tolerance; they are still shown because the slate must be complete, but they must not be bet.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/lines.py", "Keep excluded from staking.")
    flag("FLAG-LINE-03", "medium", "picks", "The 1.5-pt trigger hurdle is arbitrary and untested; it decides "
         "which games are actionable, so it is a money decision dressed as a parameter.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/lines.py", "Optimise on settled data, not intuition.")
    flag("FLAG-CORR-01", "low", "correlation", "r(SRS, margin/G) is computed on 30 team-season points from one "
         "snapshot; it is a descriptive statistic, not a stable parameter.",
         "https://www.basketball-reference.com/leagues/NBA_2027_standings.html", "Recompute each week; store the series.")
    flag("FLAG-CORR-02", "high", "correlation", "The margin/total correlation that drives same-game parlays is "
         "now measured in the backtest tree (139 official finals, point-in-time): r = -0.009 (95% CI -0.17 "
         "to 0.15) — the S-04 same-game parlay premise is unsupported by the data so far. Root-site parlay "
         "figures remain a band, not a price.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/correlation.py", "Ingest game-level results (R-103).")
    flag("FLAG-CORR-03", "high", "correlation", "Same-player prop correlations are unmeasured; prop combos "
         "cannot be priced honestly today.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/props.py", "Ingest player box scores.")
    flag("FLAG-CORR-04", "low", "correlation", "Exclusion rule for same-team consecutive games is a design rule, "
         "not a measurement.", "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/config.py", "No action.")
    flag("FLAG-CORR-05", "medium", "correlation", "Cross-game near-independence is assumed. It is usually fine "
         "and occasionally badly wrong (same-arena doubleheaders, shared travel).",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/correlation.py", "Test once a bet ledger exists.")
    flag("FLAG-PRL-01", "high", "parlays", "ρ band [-0.20, +0.40] is our own ratified-for-now guess at the "
         "margin/total correlation, and the total SD is a placeholder.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/config.py", "Replace both before quoting prices.")
    flag("FLAG-PRL-03", "medium", "parlays", "Cost tables use the -110 reference price, which is a labelled "
         "placeholder: no real book price was available to this build, so hold percentages are illustrative of "
         "the mechanism, not of any market.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/config.py",
         "Recompute with captured closing prices (R-101).")
    flag("FLAG-PRL-02", "medium", "parlays", "Only 10 of 36 slate games are quoted on the parlay page (highest "
         "conviction). The selection is a convenience filter, not a strategy claim.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/correlation.py", "Compute all games once prices exist.")
    flag("FLAG-LB-01", "high", "leaderboard", "The leaderboard is empty by design: no strategy has settled bets, "
         "so no score exists. Reward pool is 100% unallocated.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/leaderboard.py", "Settle the sealed ledger.")
    flag("FLAG-GATE-01", "high", "gates", "All ten gate thresholds are PROPOSED by this repo; none is sourced "
         "from a published standard, and 7 of 10 cannot currently be evaluated.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/config.py", "Owner ratifies thresholds (S-04).")
    flag("FLAG-PROP-01", "high", "props", "Player-prop pricing has no input data: no official minutes, usage or "
         "prop lines exist in this repository.",
         "https://stats.nba.com/stats/leaguestandingsv3", "Connect official player data + prop feed (R-102, R-101).")
    flag("FLAG-PROP-02", "low", "props", "The mechanism demo uses assumed parameters (p=0.55, ρ=0.40) to show "
         "the size of the independence error; it is not a projection for any player.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/props.py", "No action; labelled in-table.")
    flag("FLAG-FLOW-01", "high", "game flow", "Rest days, pace, garbage time, foul trouble and closing lineups "
         "are blank because the needed data (prior game dates outside the window, PBP, lineups) is not in the repo.",
         "https://www.nba.com/schedule", "Extend snapshot window to the full season (R-103).")
    flag("FLAG-FLOW-03", "medium", "game flow", "FIXED 2026-11-14 (COORDINATION.md I-07): the B2B/3-in-4 flags used "
         "substring matching against the pair/sequence strings, so the FIRST night of a consecutive pair was also "
         "flagged (e.g. DAL on 11/14 before its 11/15 game). Detection now anchors on the second/third night; a "
         "regression test pins it. Rows published before 2026-11-14 carry the inflated values.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/gameflow.py",
         "No action for the current build; treat pre-refresh game-flow B2B values as over-counted.")
    flag("FLAG-FLOW-02", "medium", "game flow", "Back-to-back detection only sees inside 2026-11-13..17; a team "
         "playing Nov 12 is invisible, so 'not in window' does not mean 'rested'.",
         "https://www.nba.com/schedule", "Same as R-103.")
    flag("FLAG-ANOM-01", "low", "slate", "Repeat matchups on the official schedule: POR@MIN on 11/16 AND 11/17 "
         "(both Target Center), NYK@TOR on 11/15 AND 11/17 (both Scotiabank Arena). The 2026-11-14 capture "
         "renders both pairs as distinct entries with distinct game IDs - genuine schedule entries, now in the "
         "pick window; unusual but real, and the same-venue back-to-back is priced by game flow. "
         "Adjudicated 2026-11-14 by session arena/72f9da58: the official game page for 0022600253 prints "
         "\"Tuesday, November 17th, 2026 7:30 PM ET\" and the official game rail lists both repeats "
         "(0022600253, 0022600254) - genuine, not a rendering artefact.",
         "https://www.nba.com/schedule", "Confirmed on the official game pages; no action.")
    flag("FLAG-REQ-01", "low", "requirements", "Requirement statuses are this session's self-assessment against "
         "the repo contents, not an external audit.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/COORDINATION.md", "Owner review.")
    flag("FLAG-QUEST-01", "low", "questions", "Answers marked 'unknown' are unknown to the data we could reach; "
         "another tool with an odds/player feed may already know them.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/COORDINATION.md", "Route to data vendor answers.")
    flag("FLAG-SUGG-01", "info", "suggestions", "Suggestions are not implemented. The queue exists so an owner "
         "chooses; treating them as done would be exactly the failure mode this project is about.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/COORDINATION.md", "Owner decides.")
    flag("FLAG-SRC-01", "low", "sourcing", "Rows sourced to a third party, to derivation, or to a blocked "
         "endpoint are flagged even when the value looks fine.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/COORDINATION.md", "No action; disclosure by design.")
    flag("FLAG-INJ-01", "medium", "injuries", "27 of 122 rows inherit their team from the last team label printed in "
         "their game block because the PDF table breaks across pages; not individually confirmed. One row "
         "(DAL@CLE Martin, Caleb) is attributed from cross-release evidence documented in the snapshot.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf", "Confirm against the PDF image.")
    flag("FLAG-INJ-02", "high", "injuries", "Minutes/production/line impact columns are blank for all 122 rows. "
         "The official report has no such fields and no player-level feed is connected.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf", "Connect R-102.")
    flag("FLAG-INJ-03", "medium", "injuries", "'No rows for this team' is not 'team is healthy'. The 11/13 19:30 ET release "
         "carries no explicit MIL or NYK rows at all (their blocks list only the opponent's players), so "
         "absence from our transcription is not evidence of availability.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf", "Re-parse the full 7 pages.")
    flag("FLAG-INJ-04", "medium", "injuries", "Five of the ten 2026-11-14 teams (NOP, CLE, MEM, CHI, MIA) had not submitted "
         "their report in the 11/13 19:30 ET release. In the 11/14 05:00 a.m ET release (the newest one) the same "
         "five are still NOT YET SUBMITTED for 11/14, and every 2026-11-15 slot is also NOT YET SUBMITTED - the "
         "5 p.m. local day-before deadline for those games had not passed. Nothing exists yet for 11/16 or 11/17, "
         "so those lines carry no availability data. This is structural to publishing at T-3, not a to-do item; the "
         "game-day report (11 a.m.-1 p.m. local) is the next mandatory filing.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf", "Re-run at game-day 13:00 ET.")
    flag("FLAG-PROC-01", "high", "process", "A patch script in this session overwrote "
         "data/raw/injury_report_2026-11-13.json with source code (a reused variable name in a throwaway "
         "editing script). Detected on the next build when the JSON failed to parse; restored from commit "
         "638b369 and re-patched correctly. No data was lost because every snapshot is committed before use.",
         "https://github.com/wingbangboozle1-lang/NBA2/commit/638b369",
         "Keep the rule that raw snapshots are committed before the pipeline reads them, and re-verify after "
         "every scripted edit (git diff on data/raw must be empty except intended changes).")
    flag("FLAG-SLATE-04", "medium", "slate", "Tip times come from the rendered /schedule page, whose time list "
         "is not reliably aligned with the games beside it; they are published but NOT independently confirmed. "
         "Confirm on the game page before trusting anything time-sensitive (live/teaser/settlement windows).",
         "https://www.nba.com/schedule",
         "CONFIRMED 2026-11-14 (session arena/72f9da58): all 31 tips of the original window now carry "
         "at least two official sources — the schedule page and the game rail on "
         "nba.com/game/den-vs-nop-0022600231; the nine 11/13 tips additionally match the official "
         "injury report's Game Time column. No time remains single-source. See the Session Audit page.")
    flag("FLAG-SLATE-05", "info", "slate", "RESOLVED BY THE 2026-11-14 REFRESH for this window: all 36 official game-page "
         "URLs rendered verbatim in the retrieved page text (previously a slug rule confirmed on 12 of 31). "
         "Future slates need the same click-through before the flag can stay closed.",
         "https://www.nba.com/schedule",
         "Independently re-confirmed 2026-11-14 by session arena/72f9da58: every one of the original "
         "31 slugs was read back from links nba.com itself prints (schedule previews + the game rail) "
         "and matched 31/31. Keep the click-through habit for each new slate. See the Session Audit page.")
    flag("FLAG-SLATE-06", "high", "slate", "Availability data for the pick window is still incomplete: the "
         "11/13 19:30 ET release carries day-before designations for 2026-11-14 only (5 of 10 team-slots "
         "filed, 5 NOT YET SUBMITTED), and nothing exists yet for 11/15-17, so most of the window is priced "
         "without availability data. This is a structural property of publishing at T-3, not a to-do item.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf",
         "Re-issue availability after each later release (the nightly ingest workflow now does this; see FLAG-REFRESH-01).")
    flag("FLAG-REPO-01", "low", "repo review", "Repo-review findings are point-in-time (main @ 7fa2a24). Later "
         "commits may fix or reintroduce them.",
         "https://github.com/wingbangboozle1-lang/NBA2/commits/main", "Re-run review on each merge.")
    flag("FLAG-REFRESH-01", "low", "injuries", "The 2026-11-14 availability refresh is a point-in-time capture "
         "(11/13 19:30 ET official release, retrieved 2026-11-14 00:47 UTC). Later releases on 11/14 (continual "
         "updates, game-day reports 11 a.m.-1 p.m. local) can change statuses before tip-off; the nightly ingest "
         "workflow fetches and archives them but does not rewrite sealed predictions.",
         "https://official.nba.com/nba-injury-report-2026-27-season/",
         "Let the nightly workflow ingest later releases; verify the archived PDF against the transcript.")

    # ---- flags raised by session arena/72f9da58 (2026-11-14 verification round) ----
    flag("FLAG-CUR-01", "low", "provenance",
         "Currency history worth keeping on the record: the first published injury rows (official "
         "16:15 ET release) were superseded three times the same evening — 17:15, 18:15 and 19:15 ET "
         "— by 12 status changes and 32 added rows (complete line-by-line delta on the Session Audit "
         "page). The site now publishes the official 19:30 ET release, ingested by the 2026-11-14 "
         "refresh; later game-day releases can still change statuses before tip-off (FLAG-REFRESH-01), "
         "and no rows exist yet for 11/15–17 (FLAG-SLATE-06).",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_15PM.pdf",
         "Nightly ingest now covers later releases (refresh workflow); the delta table stays as the "
         "audit trail of what changed between revisions (suggestion S-A01 — implemented).")
    flag("FLAG-CUR-02", "medium", "provenance",
         "In the official 19:15 ET revision, the team label for Martin, Caleb is dropped at a page "
         "break, leaving his entry ambiguous between the Cleveland Cavaliers and the Dallas Mavericks "
         "block; that revision also printed a contradictory 'Cleveland Cavaliers — NOT YET SUBMITTED' "
         "placeholder. The 17:15, 18:15 and 19:30 ET releases all print 'Cleveland Cavaliers' "
         "explicitly on his row, which is how his team is attributed in the published snapshot.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_15PM.pdf",
         "Owner check against the next official revision; keep the Cleveland attribution only for "
         "as long as the later revisions keep printing it.")
    flag("FLAG-AUD-01", "low", "provenance",
         "The slate table's 'Official game page' column prints the verified URLs as plain text rather "
         "than clickable links — 36 rows in the current window — which makes manual review slower "
         "than it needs to be. No data is affected.",
         "https://www.nba.com/schedule",
         "Wrap the cell in an anchor at build time (suggestion S-A02 on the Session Audit page).")
    flag("FLAG-INJ-08", "medium", "injuries",
         "CORRECTION (2026-11-14, session arena/6650be4d-nba2): the 11/13 19:30 ET release was "
         "transcribed with Caleb Martin under the CLEVELAND Cavaliers. The PDF breaks across pages "
         "with the Team column blank on the continuation rows, and Martin's row falls in that gap, "
         "immediately before the 'Cleveland Cavaliers | NOT YET SUBMITTED' line - so the team was "
         "inferred from the wrong side of the break. The 11/14 05:00 a.m ET release repeats the team "
         "on every row and prints Martin under the DALLAS Mavericks. The published window rows now "
         "come from that release, so the corrected attribution is what the site shows; the row-level "
         "diff is published on the Injuries page.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf",
         "Re-read every continuation row of any future release against a rendering that repeats the "
         "team, or wait for the next same-day revision.")
    flag("FLAG-INJ-09", "low", "injuries",
         "An injury report is re-issued repeatedly and a status can move between releases. The delta "
         "between the two releases this session compared is published on the Injuries page; as of the "
         "05:00 a.m ET release none of the 26 rows shared with the 19:30 ET release had changed "
         "status or reason.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf",
         "Re-run the delta on every new release; a status change is a different bet.")
    flag("FLAG-SET-02", "info", "provenance",
         "Official final scores for the nine 2026-11-13 games are now committed "
         "(data/raw/finals_2026-11-13.json, read from the official schedule page). Those nine games "
         "are day-before CONTEXT: neither sealed ledger covers them, so the published grade is a "
         "model check and NOT a settled registered forecast. Settlement of the sealed windows "
         "(11/14-11/17) stays PENDING because those games have not been played.",
         "https://www.nba.com/schedule?date=2026-11-14",
         "Keep re-running python -m nba2.pipeline.settle after each game day; never publish a "
         "settlement number that the sealed ledger does not cover.")
    flag("FLAG-SLATE-09", "low", "slate",
         "Two official pages disagree on the tip time of one game in the window: the /schedule card "
         "for 0022600249 (HOU @ MIA, 2026-11-16) rendered '8:00 PM ET', while the game's own page "
         "(https://www.nba.com/game/hou-vs-mia-0022600249) renders '7:30 PM ET' in both its game rail "
         "and its header line 'Monday, November 16th, 2026 7:30 PM ET'. The published value follows "
         "the game's own page. The other 35 games in the window were re-read in this session and "
         "match the committed snapshot exactly.",
         "https://www.nba.com/game/hou-vs-mia-0022600249",
         "Treat the game's own page as authoritative for its tip time; re-check this game before "
         "anything time-sensitive (live betting window, settlement) is built on it.")
    flag("FLAG-RAT-03", "low", "ratings",
         "The official standings table (nba.com/standings) now supplies every club's W-L plus "
         "HOME/ROAD/CONF/DIV splits and is published on the Methodology page — but its 'Margins & "
         "Stats' section does NOT render PS/G, PA/G or SRS for a non-browser client, so those three "
         "model inputs are still third-party (FLAG-RAT-01). The official game pages do carry the "
         "win-loss records on their cards, which is a second independent official read.",
         "https://www.nba.com/standings",
         "Confirm PS/G, PA/G and SRS once against the official standings page in a browser, or "
         "connect stats.nba.com from a runner (R-103).")
    flag("FLAG-SET-01", "info", "provenance",
         "Settlement, reward allocation and the leaderboard scores are all unmeasured by design. As of "
         "2026-11-14 the settlement path has been exercised against real official finals captures "
         "(data/raw/finals_2026-11-13.json + data/raw/finals_all.json — the nine 2026-11-13 games): "
         "both sealed ledgers verify, and the loader reports "
         + _settlement_state_sentence() +
         " The sealed games of 11/14–11/17 still have no "
         "official final scores, so every leaderboard score, bet count and reward cell is blank and the "
         "gates stay blocked or unmeasured. A partial settlement is refused, not published.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/raw/ledger/sealed-2026-11-14.json",
         "Commit data/raw/finals_<date>.json from official box scores once each game day ends, then "
         "re-run python -m nba2.pipeline.settle — the nightly ingest job (.github/workflows/refresh.yml) "
         "does this automatically (suggestion S-A04 on the Session Audit page).")
    flag("FLAG-SLATE-02", "info", "provenance",
         "Historical flag (raised 2026-11-13, kept registered so the ratings table's TOR/WAS rows "
         "can link the coverage history they carry per CR-4): the win-loss records for Toronto and "
         "Washington 'were not visible in the retrieved NBA.com page text; third-party value only' "
         "in the capture that raised it. RESOLVED — see FLAG-RES-01: on 2026-11-14 all 30 teams' "
         "W-L were re-read from the official standings page (TOR 5-7, WAS 4-9) and match, and "
         "nba2/data/records.json verifies TOR/WAS via their official NBA.com team pages.",
         "https://www.nba.com/standings",
         "None — recorded history. FLAG-RES-01 carries the resolution evidence.")
    flag("FLAG-PAGES-01", "info", "provenance",
         "Two verified site trees ship from this repository, and only ONE is served: probed "
         "2026-11-14 (final-integration session), https://wingbangboozle1-lang.github.io/NBA2/ serves "
         "the v2 site/ artifact (built and provenance-checked by .github/workflows/pages.yml, deployed "
         "by the deploy-pages action) while the root tree's pages/ URLs return 404 — the Pages API's "
         "build_type: legacy (branch main /) does not describe the artifact readers receive. Both "
         "trees are fully checked (root: provenance lint — every row sourced, every blank explained — "
         "plus the semantic cross-check, 83 pass / 0 fail on 2026-11-14; v2: 0 structural / 0 semantic "
         "problems). The root tree additionally publishes the sealed-ledger picks and the settlement "
         "chain the brief asks for but is NOT currently reachable from the live URL; see S-A05 and "
         "suggestion S-27/Q-27 (owner: archive the root tree or surface it).",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/.github/workflows/pages.yml",
         "Owner decides S-27: archive the root tree or restore it as the published surface; until "
         "then it stays CI-verified and refreshed nightly.")
    flag("FLAG-ORIG-01", "low", "provenance",
         "In the originated/ evidence tree, originated/data/teams.json rows carry duplicate JSON "
         "keys: each team object has both \"conf\": \"East|West\" and \"conf\": \"<conference record>\". "
         "A JSON parser silently keeps the last, so the conference name is unreachable and "
         "originated/engine/model.js publishes the conference record in its place. Not fixed here "
         "(the WSH→WAS team-key fix was this session's scope; the schema repair is the tree owner's "
         "call) — flagged for review 2026-11-14 by arena/6c5195d1.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/originated/data/teams.json",
         "Owner renames one of the two keys (e.g. conf_record) and regenerates originated/ "
         "(the 24-check verifier must stay green).")
    flag("FLAG-RES-01", "info", "provenance",
         "FLAG-SLATE-02 states that the win-loss records for Toronto and Washington 'were not visible "
         "in the retrieved NBA.com page text; third-party value only'. On 2026-11-14 all 30 teams' "
         "W-L were re-read from the official standings page and match the snapshot exactly, including "
         "TOR 5-7 and WAS 4-9 — the two records the flag was raised for.",
         "https://www.nba.com/standings",
         "Owner closes FLAG-SLATE-02; no value changed — the third-party rows are now official too.")

    # --- flags registered by session arena/3681def8-nba2 (first graded card) ---------
    flag("FLAG-GRADE-01", "high", "graded",
         "The 2026-11-13 graded card is a walk-forward backtest, NOT a pre-registered forward "
         "test. No sealed ledger covers 2026-11-13: sealed-2026-11-13.json predicts 11/14-11/16 "
         "and sealed-2026-11-14.json predicts 11/14-11/17. The project began on the evening of "
         "2026-11-13 when that slate was already live, so nothing was sealed for it. The inputs "
         "are strictly point-in-time (the ratings snapshot was retrieved 2026-11-13 22:35 UTC; "
         "the first tip was 2026-11-14 00:00 UTC, and the identity ratings+results==official "
         "standings holds for 30/30 clubs), but the predictions were not published before the "
         "games. Treat the result as evidence about the model, not as a betting record.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/audit/2026-11-14-3681/grade_1113.py",
         "Seal every slate before its first tip from now on; the 11/14-11/17 ledger already does.")
    flag("FLAG-GRADE-02", "high", "graded",
         "n = 9 games. Neither improvement on the graded card is statistically significant: "
         "permutation p = 0.952 for margin error and p = 0.402 for total error. Detecting a 55% "
         "hit rate at 5% significance with 80% power needs about 1,565 graded games. The card "
         "does not establish skill and does not unblock any gate.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/graded_2026-11-13.json",
         "Keep grading every completed slate; re-test only when the sample supports it.")
    flag("FLAG-GRADE-03", "high", "graded",
         "No market price exists in this repository, so the graded card cannot report ROI, CLV or "
         "stake. 'Covering our own line' is self-consistency only, not a market test — the cover "
         "column is published with that caveat attached.",
         "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/pipeline/settle.py",
         "Connect a licensed odds feed (R-101) before any betting claim.")
    flag("FLAG-GRADE-04", "info", "graded",
         "Two of the nine games missed by more than 20 points on the margin (GSW@SAS: predicted "
         "SAS +3.2, actual SAS +38; MEM@NOP: predicted MEM by 8.3, actual MEM by 31). Both are "
         "reported, not smoothed — they are the main drivers of the margin MAE.",
         "https://www.nba.com/game/gsw-vs-sas-0022600040",
         "Investigate whether the early-season ratings over-shrink large true gaps (S-31).")
    flag("FLAG-STAND-01", "low", "standings",
         "Games played are uneven this early in the season: Denver has played 10 games while "
         "Utah, Milwaukee, Boston, Detroit, Brooklyn and Philadelphia have played 12-14. "
         "Win-percentage ordering and SRS both handle this, but raw win counts do not — the "
         "official standings page orders by percentage, and this snapshot does the same.",
         "https://www.nba.com/standings",
         "No action; noted so nobody reads DEN's 6-4 as a shorter schedule bug.")
    flag("FLAG-INJ-08", "info", "injuries",
         "At the 2026-11-14 05:00 AM ET release, five of the ten clubs on the 11/14 slate had "
         "filed nothing (New Orleans, Cleveland, Memphis, Miami, Chicago) and all eighteen 11/15 "
         "club entries read NOT YET SUBMITTED. This is the official state of the document, not a "
         "parsing failure — the 11 a.m.-1 p.m. local game-day filing window had not opened.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_00AM.pdf",
         "Re-fetch after 1 p.m. ET for a complete 11/14 card, and after 5 p.m. ET for 11/15.")

    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    n_rows = sum(len(t["rows"]) for t in data["sections"].values() if isinstance(t, dict) and "rows" in t)
    print(f"wrote {OUT.relative_to(ROOT)} — {len(data['sections'])} tables, {n_rows} rows")
    return data


if __name__ == "__main__":
    main()
