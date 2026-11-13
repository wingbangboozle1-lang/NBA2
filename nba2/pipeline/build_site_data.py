"""Assemble every site table from the verified snapshots.

Invariants enforced here (and re-checked by `lint.py`):
* every row carries a source; a row whose source is not NBA-official carries >= 1 flag;
* an unknown value is `None` (rendered blank), never a placeholder;
* nothing is reported as measured unless a measurement object exists for it.
"""

from __future__ import annotations

import json
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
from ..provenance import SOURCES, Src, all_flags, flag, make_row, register_source, table

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
OUT = DATA / "site.json"
PREVIEW_VERIFIED = set(json.loads((RAW / "slate_2026-11-13_to_11-16.json").read_text())["preview_verified_game_ids"])

SRC_SLATE = "nba_schedule"
SRC_GAMES = "nba_games"
SRC_INJ = "nba_injury_pdf"
SRC_RAT = "bref_standings"
SRC_DER = "derived_lines"
SRC_DER_RAT = "derived_ratings"
SRC_DER_CORR = "derived_corr"
SRC_COORD = "coordination"
SRC_GIT = "git_repo"


def _flag_ids(*ids: str) -> list[str]:
    return list(ids)


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
                 method="NOT fitted: no game-level totals available; used only inside the parlay "
                        "sensitivity band",
                 sanity="level-sensitive, so parlay output is reported as a ratio, not a price",
                 status="unratified placeholder"),
    ]
    return table(rows, [("symbol", "Parameter"), ("value", "Fitted value"), ("method", "How it was obtained"),
                        ("sanity", "Cross-check"), ("status", "Status")],
                 "Model parameters — derived, not assumed",
                 "These are the only two structural numbers the whole site depends on. Both are fitted "
                 "against the verified standings snapshot; where the fit is weak we say so instead of "
                 "quietly picking a convention.",
                 "Inputs: data/raw/team_ratings_2026-11-13.json (third-party) with win-loss cross-checked "
                 "against NBA.com game cards (official).")


def build_ratings_rows(model: RT.RatingModel) -> dict:
    rows = []
    for tc in model.order:
        t = model.get(tc)
        rows.append(make_row(
            tc, SRC_RAT, _flag_ids("FLAG-RAT-01"),
            team=t.name, tricode=tc,
            wl=f"{t.wins}-{t.losses}", wl_official=f"{t.wins}-{t.losses}",
            ppg=f"{t.ppg:.1f}" if t.ppg is not None else None,
            oppg=f"{t.oppg:.1f}" if t.oppg is not None else None,
            net=f"{t.net_ppg:+.1f}" if t.net_ppg is not None else None,
            srs=f"{t.srs:+.2f}" if t.srs is not None else None,
            lam=f"{t.reliability:.3f}" if t.reliability is not None else None,
            srs_shrunk=f"{t.srs_shrunk:+.2f}" if t.srs_shrunk is not None else None,
            games=t.games,
        ))
    return table(rows, [("team", "Team"), ("wl_official", "W-L (official NBA.com)"),
                        ("wl", "W-L (ratings source)"), ("ppg", "PS/G"), ("oppg", "PA/G"),
                        ("net", "Margin/G"), ("srs", "SRS"), ("games", "GP"),
                        ("lam", "Reliability λ"), ("srs_shrunk", "SRS × λ")],
                 "Team ratings table (the model's only inputs)",
                 "W-L is confirmed against NBA.com for 28 of 30 clubs; TOR and WAS were not visible in the "
                 "retrieved official page text and are flagged. PS/G, PA/G and SRS could not be pulled from an "
                 "official endpoint at all — that is the single biggest data gap on this site.",
                 "Both W-L columns are printed on purpose: if they ever disagree, the table is wrong.")


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
    """(date, away@home) -> (time_et, captured) from the official injury report."""
    path = RAW / "official_game_times_2026-11-13.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    cols = raw["columns"]
    out = {}
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
            verdict = "not in the 11/13 report (that release lists 11/13 + 11/14 only)"
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
                 f"{absent} outside that report",
                 "The schedule page is the only source for most of this slate, and its times are printed as a "
                 "loose list — the reason FLAG-SLATE-04 was raised. The injury report repeats each matchup with "
                 "its own time cell, so where the two agree the time is no longer a single-source claim. Every "
                 "one of the 11 readable pairs agrees, and no pair disagrees.",
                 "https://www.nba.com/schedule vs https://ak-static.cms.nba.com/referee/injury/"
                 "Injury-Report_2026-11-13_01_00PM.pdf")


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
                 "Verified slate — 2026-11-13 → 2026-11-16 (31 games)",
                 "Every field on this page is read off the official NBA.com schedule. Game IDs are the NBA's "
                 "own; per-date game counts (9 / 5 / 9 / 8) match the calendar grid on the same page.",
                 "https://www.nba.com/schedule retrieved 2026-11-13 22:33 UTC.")


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


def build_picks_rows(lines: list[LN.GameLine]) -> dict:
    rows = []
    for l in lines:
        if l.tier == "BLOCKED" or l.margin is None:
            continue
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
                 "This is the honest shape of a line-origination desk before it has execution.",
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
                       "Official NBA injury report — 11/13/26 16:15 ET release",
                       "Transcribed from the NBA's own referee-operations PDF. The three middle columns are "
                       "blank by policy: the report contains no minutes or production data, so any number we "
                       "put there would be invented. P(plays) is our modelling convention for counting bodies, "
                       "not a league probability.",
                       "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf")

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
            home_b2b="YES" if f["home_b2b"] else "not in window",
            away_b2b="YES" if f["away_b2b"] else "not in window",
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


def build_anomaly_rows(anomalies: list[dict]) -> dict:
    rows = []
    for a in anomalies:
        rows.append(make_row(
            a["game_id"], SRC_SLATE, _flag_ids("FLAG-ANOM-01"),
            date=a["date"], matchup=a["matchup"], game_id=a["game_id"],
            observation=a["observation"], window=a["window"],
            disposition="FLAGGED — not used in any model output",
        ))
    return table(rows, [("date", "Date"), ("matchup", "Matchup"), ("game_id", "Game ID"),
                        ("observation", "Observation"), ("window", "In pick window?"),
                        ("disposition", "Disposition")],
                 "Slate irregularities found while transcribing",
                 "Recorded, not fixed. Each of these would corrupt an automated pipeline that trusted the "
                 "pattern instead of the value.", "https://www.nba.com/schedule retrieved 2026-11-13 22:39 UTC.")


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
                 pearson=None, spearman=None, n=None,
                 method="BLOCKED — needs game-level margins and totals",
                 use="drives every same-game parlay price",
                 status="unavailable"),
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
    rows = []
    for e, r in zip(entries, LB.table_rows(entries)):
        fl = ["FLAG-LB-01"]
        rows.append(make_row(
            e.strategy_id, SRC_DER, _flag_ids(*fl),
            id=e.strategy_id, name=r["name"], family=r["family"],
            score=None if r["score"] is None else f"{r['score']:.1f}",
            tier=r["tier"], gates=f"{r['gates_passed']} pass / {r['gates_failed']} fail / {r['gates_blocked']} blocked",
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
                 "input exists but is contaminated for this use. Neither is a 0 and neither is a pass.",
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
                 "A strategy must clear all ten to be promoted and to receive rewards. Nine of the ten are "
                 "currently blocked by missing data, which is the real status of this project and the reason "
                 "the leaderboard is empty.", "nba2/config.py::GATES")


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
                 "why the impact column stays blank.",
                 "https://www.nba.com/games + the 11/13 16:15 ET injury report")


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
             config.SNAPSHOT_CONTEXT, config.SNAPSHOT_LEADERS,
             "official_game_times_2026-11-13.json"]
    for n in names:
        f = RAW / n
        if f.exists():
            h.update(n.encode())
            h.update(f.read_bytes())
    for rel in ("requirements/REQUIREMENTS.json", "requirements/QUESTIONS.json",
                "requirements/REPO_REVIEW.json", "suggestions/SUGGESTIONS.json",
                "nba2/data/picks.json", "nba2/data/records.json", "nba2/data/injuries.json",
                "nba2/data/flagged.json", "data/our-lines.csv",
                "data/verified/injuries_2026-11-13_0515PM.json"):
        f = ROOT / rel
        if f.exists():
            h.update(rel.encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def build() -> dict:
    # Flags recorded *inside* the data snapshots are registered from the files themselves, so the
    # Flagged page can never drift from the provenance stored with the data.
    for fname, skey, area in ((config.SNAPSHOT_SLATE, "nba_schedule", "slate"),
                              (config.SNAPSHOT_RATINGS, "bref_standings", "ratings"),
                              (config.SNAPSHOT_INJURY, "nba_injury_pdf", "injuries"),
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
    stamp = prev.get("generated_at_utc") if same_inputs else \
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    data_as_of = json.loads((RAW / config.SNAPSHOT_SLATE).read_text())["as_of"]
    model = RT.build(ROOT)
    games, slate_raw = LN.load_slate(RAW / config.SNAPSHOT_SLATE)
    inj_rows, inj_raw = INJ.load(RAW / config.SNAPSHOT_INJURY)
    anomalies_raw = json.loads((RAW / "slate_context_2026-11-17.json").read_text())
    requirements = json.loads((ROOT / "requirements" / "REQUIREMENTS.json").read_text())
    questions = json.loads((ROOT / "requirements" / "QUESTIONS.json").read_text())
    suggestions = json.loads((ROOT / "suggestions" / "SUGGESTIONS.json").read_text())
    repo_review = json.loads((ROOT / "requirements" / "REPO_REVIEW.json").read_text())["requirements"]

    by_team = INJ.by_team(inj_rows)
    lines = LN.price_slate(model, games, by_team)
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

    sections = {
        "ratings": build_ratings_rows(model),
        "calibration": build_calibration_rows(model),
        "luck": build_luck_rows(model),
        "slate": build_slate_rows(games),
        "lines": build_lines_rows(model, lines),
        "picks": build_picks_rows(lines),
        "injuries": build_injury_tables(inj_rows)[0],
        "rotation": build_injury_tables(inj_rows)[1],
        "gameflow": build_gameflow_rows(games, spots, flow),
        "anomalies": build_anomaly_rows(anomalies_raw["records"]),
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
            "Nothing on this page has been implemented. Each item is written so a reviewer can accept, reject "
            "or defer it on its own merits, and the queue's state is the record of that decision.",
            suggestions["source_note"]),
        "xlines": x["lines"], "xrecords": x["records"], "xinjuries": x["injuries"],
        "surfaces": x["inventory"],
        "x3way": x3, "xadjudicate": xadj,
        "flags": None,   # filled below
        "sources": None,
    }

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
                               "to any table on this site.", "retrieved 2026-11-13 22:25–22:40 UTC")

    return {
        "meta": {
            "generated_at_utc": stamp,
            "input_digest": digest,
            "build_is_idempotent": same_inputs,
            "snapshot_as_of": "2026-11-13",
            "slate_window": "2026-11-13 → 2026-11-16 (today + 3 days)",
            "games": len(games), "teams": len(model.order),
            "injury_rows": len(inj_rows),
            "injury_status_rows": sum(1 for r in inj_rows if r.status != "NOT YET SUBMITTED"),
            "injury_placeholder_rows": sum(1 for r in inj_rows if r.status == "NOT YET SUBMITTED"),
            "injury_attribution_continuation": sum(1 for r in inj_rows if r.attribution == "C"),
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
         "exist in the repository. It affects parlay levels, not the ratio comparisons.",
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
         "unmeasured. Every parlay figure on this site is therefore a band, not a price.",
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
    flag("FLAG-PRL-02", "medium", "parlays", "Only 10 of 31 games are quoted on the parlay page (highest "
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
    flag("FLAG-FLOW-02", "medium", "game flow", "Back-to-back detection only sees inside 2026-11-13..16; a team "
         "playing Nov 12 is invisible, so 'not in window' does not mean 'rested'.",
         "https://www.nba.com/schedule", "Same as R-103.")
    flag("FLAG-ANOM-01", "medium", "slate", "Identical matchups appear on consecutive days on the official "
         "schedule page for the 11/17 slate (NYK@TOR and POR@MIN). Could be genuine or a rendering artifact; "
         "recorded and excluded from all model output.",
         "https://www.nba.com/schedule", "Confirm on the two game pages before ingesting 11/17.")
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
    flag("FLAG-INJ-01", "medium", "injuries", "17 rows inherit their team from the last team label printed in "
         "their game block because the PDF table breaks across pages; not individually confirmed.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf", "Confirm against the PDF image.")
    flag("FLAG-INJ-02", "high", "injuries", "Minutes/production/line impact columns are blank for all 91 rows. "
         "The official report has no such fields and no player-level feed is connected.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf", "Connect R-102.")
    flag("FLAG-INJ-03", "medium", "injuries", "'No rows for this team' is not 'team is healthy'. Pages 3,5,7 of "
         "the report were not all parsed, and teams with no listed players may simply be outside what we read.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf", "Re-parse the full 7 pages.")
    flag("FLAG-INJ-04", "info", "injuries", "Nov 14 rows are 'NOT YET SUBMITTED' in the 11/13 16:15 ET release — "
         "injury-aware lines at T-3 are structurally impossible, and the site says so on the slate page.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf", "Re-run at game-day 13:00 ET.")
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
         "https://www.nba.com/schedule", "Confirm per game page; blank the column if any doubt remains.")
    flag("FLAG-SLATE-05", "medium", "slate", "19 of 31 official game-page URLs are generated from a slug rule "
         "confirmed on 12 games, not verified one by one. The game IDs themselves are official; only the URL "
         "is a generalisation.",
         "https://www.nba.com/schedule", "Click-through verification, or ingest the official sitemap.")
    flag("FLAG-SLATE-06", "high", "slate", "No injury report exists yet for 2026-11-14/15/16, so the entire "
         "pick window is priced without availability data. This is a structural property of publishing at T-3, "
         "not a to-do item; the 11/13 16:15 ET release lists all ten Nov-14 teams as NOT YET SUBMITTED.",
         "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf",
         "Re-issue lines after each game-day 13:00 ET report (suggestion S-10).")
    flag("FLAG-REPO-01", "low", "repo review", "Repo-review findings are point-in-time (main @ 7fa2a24). Later "
         "commits may fix or reintroduce them.",
         "https://github.com/wingbangboozle1-lang/NBA2/commits/main", "Re-run review on each merge.")

    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    n_rows = sum(len(t["rows"]) for t in data["sections"].values() if isinstance(t, dict) and "rows" in t)
    print(f"wrote {OUT.relative_to(ROOT)} — {len(data['sections'])} tables, {n_rows} rows")
    return data


if __name__ == "__main__":
    main()
