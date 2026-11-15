"""v3 build: assemble the model's outputs and publish them as pages.

The brief's separation rule is enforced here, structurally:

  * every page belongs to exactly one surface, ``projection`` or ``bet``;
  * a ``bet`` page can only render a stake if a market price exists, and none does, so the
    bet surface publishes a gate report and zero stakes;
  * no page mixes the two — the surface is a field on the page record and the navigation
    groups by it, so a reader always knows which one they are on.

Nothing here writes HTML by hand-drawn string templates with numbers typed into them: every
figure on a page comes from a function in ``model``/``backtest``/``strategies``/``travel``.
"""

from __future__ import annotations

import html
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from . import official as O
from . import model as M

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "v3"
SITE = ROOT / "site"

SURFACES = {
    "projection": ("Projection", "Safe to publish now: inputs, formulas, originated numbers, "
                                 "and the confidence gap. No stake is implied by anything here."),
    "bet": ("Bet (gated)", "Gated surface: records a stake only after the gates pass. Every "
                           "gate that is open is listed with the reason it is open."),
}


def calibration(teams: dict) -> M.Calibration:
    return M.calibrate(teams)


def originated_lines(teams: dict, cal: M.Calibration) -> list[M.Line]:
    """One line per game in the 3-day window, from official inputs only."""
    ppp = M.league_ppp(teams)
    history = M.load_history_dates()
    window_all = [(r[0], r[3]) for r in O.SCHEDULE]
    inj_by_team = injuries_by_team()

    out: list[M.Line] = []
    for (date, time_et, away, home, gid, arena, city) in O.SCHEDULE:
        if not (O.WINDOW_START <= date <= O.WINDOW_END):
            continue
        h, a = teams[home], teams[away]
        ln = M.Line(date=date, time_et=time_et, game_id=gid, away=away, home=home,
                    arena=arena, city=city)
        # ---- two estimators, kept apart; disagreement is the headline
        ln.margin_a = (h.r_diff + cal.hca) - a.r_diff
        ln.margin_b = (h.r_rtg + cal.hca) - a.r_rtg
        ln.margin = 0.5 * (ln.margin_a + ln.margin_b)      # fallback ONLY; labelled as such
        ln.disagreement = abs(ln.margin_a - ln.margin_b)
        ln.spread_a = -M._half(ln.margin_a)
        ln.spread_b = -M._half(ln.margin_b)
        ln.p_home_a = M.phi(ln.margin_a / cal.margin_sd)
        ln.p_home_b = M.phi(ln.margin_b / cal.margin_sd)
        ln.p_home_lo = min(ln.p_home_a, ln.p_home_b)
        ln.p_home_hi = max(ln.p_home_a, ln.p_home_b)
        ln.confidence_halfwidth = 0.5 * ln.disagreement
        # ---- totals: possessions x points-per-possession
        t = M.total_from_possessions(h, a, ppp)
        ln.poss_game = t["poss"]
        ln.ppp_home = t["ppp_home"]
        ln.ppp_away = t["ppp_away"]
        ln.pts_home = t["pts_home"]
        ln.pts_away = t["pts_away"]
        ln.total = t["total"]
        # The formula this replaces, printed beside it: an average of the two clubs' scoring
        # averages. It cannot express a game between two above-average offences, because it is
        # anchored to the league mean by construction.
        ln.total_naive = h.pts + a.pts
        ln.total_gap = ln.total - ln.total_naive
        # ---- market-anchored prior: no market input, so withheld
        mp = M.market_prior(ln.p_home_a, None, 0.5)
        ln.blended_margin = mp["blended"]
        ln.model_weight = mp["w_model"]
        # ---- conditions
        rh = M.rest_travel(home, date, home, history, window_all)
        ra = M.rest_travel(away, date, home, history, window_all)
        # TRAVEL, defined once so it cannot mean two things:
        #   * the HOME club is at its own arena, so its travel to this game is 0 km — not
        #     "distance from its last road game", which is a different quantity;
        #   * the AWAY club travels from the venue of its previous game to this venue.
        # A club on the road for four straight games has accumulated travel that this per-game
        # number does not carry; the site says so rather than quietly mixing the two.
        ln.rest_home, ln.rest_away = rh["rest"], ra["rest"]
        ln.b2b_home, ln.b2b_away = rh["b2b"], ra["b2b"]
        ln.three_in_four_home, ln.three_in_four_away = rh["three_in_four"], ra["three_in_four"]
        ln.travel_home_km = 0.0
        ln.travel_away_km = (M.travel_km(ra["prev_home"], home)
                             if ra["prev_home"] else None)
        # ---- availability
        ho = inj_by_team.get(O.NAMES[home], [])
        ao = inj_by_team.get(O.NAMES[away], [])
        ln.home_out = sum(1 for r in ho if r["status"] in ("Out", "Doubtful"))
        ln.away_out = sum(1 for r in ao if r["status"] in ("Out", "Doubtful"))
        ln.home_rotation = rotation_label(ho)
        ln.away_rotation = rotation_label(ao)
        # ---- grade
        reasons = []
        if a.gp < 10 or h.gp < 10:
            reasons.append(f"fewer than 10 official games ({a.gp}/{h.gp})")
        if ln.disagreement > 2.0:
            reasons.append(f"estimators differ by {ln.disagreement:.1f} pts")
        # Rotation availability is a WARNING, not a grade input. The model is availability-blind
        # (it prices the season-average club), so an absence is disclosed in the column and on
        # the injuries page, and the grade continues to describe estimator stability only.
        if ln.home_rotation in ("no report", "not filed") or ln.away_rotation in ("no report", "not filed"):
            ln.flags.append("FLAG-V3-ROTATION-UNFILED")
        if reasons:
            ln.grade, ln.grade_reason = "C", "; ".join(reasons)
        elif ln.disagreement <= 1.0 and abs(ln.margin_a) >= 0.75 * cal.margin_sd and abs(ln.total_gap) <= 6.0:
            ln.grade = "A"
            ln.grade_reason = ("estimators agree ≤1.0 pts, |margin| ≥ 0.75σ, possession total within "
                               "6 pts of the scoring-average total")
        else:
            ln.grade = "B"
            ln.grade_reason = "passes the minimum bars; below the A bar"
        ln.flags = sort_flags(ln)
        out.append(ln)
    return out


def sort_flags(ln: M.Line) -> list[str]:
    f = ["FLAG-V3-NO-MARKET-PRICE", "FLAG-V3-NO-PROP-LINES"]
    if ln.disagreement > 2.0:
        f.append("FLAG-V3-ESTIMATOR-GAP")
    if ln.travel_away_km is None or ln.travel_home_km is None:
        f.append("FLAG-V3-TRAVEL-BLANK")
    return f


def injuries_by_team() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for (date, time_et, matchup, team, player, status, reason, attr) in O.INJURIES:
        out.setdefault(team, []).append({
            "date": date, "time_et": time_et, "matchup": matchup, "team": team,
            "player": player, "status": status, "reason": reason, "attribution": attr,
        })
    return out


def rotation_label(rows: list[dict]) -> str:
    """The 'rotation availability' column: a one-line, honest summary per club.

    Definitions, fixed here and used identically on every row:
      * 'all cleared'      — the club filed rows and none is Out/Doubtful;
      * 'N out/doubtful'   — the club filed rows and N players are Out or Doubtful;
      * 'not filed'        — the league printed NOT YET SUBMITTED for this club;
      * 'no report'        — the club is not in this revision at all (e.g. day +2).
    A club can never be 'all cleared' on the strength of a report it does not appear in.
    """
    if not rows:
        return "no report"
    out = sum(1 for r in rows if r["status"] in ("Out", "Doubtful"))
    game = sum(1 for r in rows if r["status"] in ("Questionable", "Probable"))
    if out == 0 and game == 0:
        return "all cleared"
    parts = []
    if out:
        parts.append(f"{out} out/doubtful")
    if game:
        parts.append(f"{game} game-time decision")
    return ", ".join(parts)


def not_submitted_set() -> set[str]:
    return {(r[0], r[3]) for r in O.INJ_NOT_SUBMITTED}


# --------------------------------------------------------------------------- publish
NAV_GROUPS = (
    ("projection", "Projection surface", [
        ("v3-index.html", "Dashboard"),
        ("v3-lines.html", "Originated lines"),
        ("v3-totals.html", "Totals"),
        ("v3-teams.html", "Teams &amp; luck"),
        ("v3-calibration.html", "Calibration"),
        ("v3-backtest.html", "Backtest &amp; skill"),
        ("v3-strategies.html", "Strategies"),
        ("v3-injuries.html", "Injuries"),
        ("v3-methodology.html", "Methodology"),
        ("v3-flagged.html", "Flagged for review"),
    ]),
    ("bet", "Bet surface (gated)", [
        ("v3-bet.html", "Gate report"),
    ]),
)


def nav_html(active: str) -> str:
    """Navigation grouped by surface, so a reader always knows which one they are on."""
    out = []
    for surface, label, entries in NAV_GROUPS:
        out.append(f'<p class="navgrp {("proj" if surface == "projection" else "bet")}">'
                   f'{label}</p>')
        for href, text in entries:
            cls = ' class="on"' if href == active else ""
            out.append(f'<a href="{href}"{cls}>{text}</a>')
    out.append('<p class="navgrp">Elsewhere</p>')
    out.append('<a href="index.html">v2 site</a>')
    out.append('<a href="flagged.html">v2 flags</a>')
    return "\n".join(out)


def build_pages(verbose: bool = True) -> tuple:
    """Render every v3 page. Returns ``(built, payload)``.

    The surface rule is enforced here rather than trusted: each builder declares its surface, the
    registry in SURFACES must contain that surface, and a bet-surface page is refused if any gate
    reports PASS with a stake that no market price could justify. That last check cannot trigger
    today because no price exists, which is the point — it is a lock, not a policy note.
    """
    from . import pages as P
    from . import render as R
    from . import strategies as S
    from . import backtest as BT
    from . import injuries as I

    teams = M.load_teams()
    cal = calibration(teams)
    teams = M.two_estimators(teams, cal)
    lines = originated_lines(teams, cal)
    lab = BT.run()
    strat = S.run(teams, lab)
    inj = I.run()

    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "assets").mkdir(exist_ok=True)
    (SITE / "assets" / "v3.css").write_text(R.CSS)

    flags = collect_flags(lab, strat, inj)
    built = []

    builders = [
        ("projection", lambda: P.dashboard(teams, cal, lines, lab, strat)),
        ("projection", lambda: P.lines_page(teams, cal, lines)),
        ("projection", lambda: P.totals_page(teams, lines, lab)),
        ("projection", lambda: P.teams_page(teams, cal)),
        ("projection", lambda: P.calibration_page(cal, lab)),
        ("projection", lambda: P.backtest_page(lab)),
        ("projection", lambda: P.strategies_page(strat, lab)),
        ("projection", lambda: P.injuries_page(inj)),
        ("projection", lambda: P.methodology_page(cal, lab, strat)),
        ("projection", lambda: P.flagged_page(flags)),
        ("bet", lambda: P.bet_page(strat, lines)),
    ]

    surface_of = {}
    for declared, fn in builders:
        name, title, surface, body = fn()
        if declared not in SURFACES:
            raise SystemExit(f"v3 build: {name} declares unknown surface {declared!r}")
        if surface != declared:
            raise SystemExit(f"v3 build: {name} rendered as {surface!r} but was scheduled as "
                             f"{declared!r} — the two surfaces must never be mixed")
        banner = R.surface_banner(surface, SURFACES)
        doc = R.page(title, banner + body, nav_html(name), name, "")
        (SITE / name).write_text(doc)
        built.append(name)
        surface_of[name] = surface
        if verbose:
            print(f"  v3 {name:<26} {surface:<10} {len(doc):>7,} bytes")

    # A bet page carrying a non-zero stake with no market price is a build failure, not a warning.
    mkt = M.market_prior(0.5, None, 0.5)
    if not mkt.get("market_line") and any(
            (p.get("stake_units") or 0) > 0 for p in strat["ledger"].get("picks", [])):
        raise SystemExit("v3 build: a bet-surface pick carries a stake but no market price exists")

    payload = {
        "meta": {"session": O.RETRIEVED_BY, "as_of": O.AS_OF,
                 "retrieved_utc": O.RETRIEVED_UTC, "pages": len(built),
                 "surfaces": {s: sum(1 for v in surface_of.values() if v == s)
                              for s in SURFACES}},
        "pages": [{"file": n, "surface": surface_of[n]} for n in built],
        "calibration": cal.as_dict(),
        "lines": [ln.as_dict() if hasattr(ln, "as_dict") else ln.__dict__ for ln in lines],
        "backtest": {k: v for k, v in lab.items() if k != "predictions"},
        "strategies": strat,   # prereg included: check.py verifies those hashes against the files
        "injuries": {k: v for k, v in inj.items()
                     if k not in ("archive", "rows", "clubs")},
        "flags": flags,
        "counts": {
            "lines": len(lines), "grades": {g: sum(1 for ln in lines if ln.grade == g)
                                            for g in ("A", "B", "C")},
            "gates_pass": sum(1 for g in strat["gates"] if g["status"].startswith("PASS")),
            "gates_fail": sum(1 for g in strat["gates"] if g["status"].startswith("FAIL")),
            "gates_not_measurable": sum(1 for g in strat["gates"]
                                        if "NOT" in g["status"]),
            "injury_rows": len(inj["rows"]),
            "flags": len(flags),
        },
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "payload.json").write_text(json.dumps(payload, indent=1, sort_keys=True, default=str))
    (DATA / "reliability.json").write_text(json.dumps(lab["reliability"], indent=1, sort_keys=True))
    (DATA / "pages.json").write_text(json.dumps(
        {"built": built, "surface_of": surface_of}, indent=1, sort_keys=True))
    return built, payload


def collect_flags(lab: dict, strat: dict, inj: dict) -> list[dict]:
    """Every open item this build knows about, with a source where one exists."""
    m = lab["metrics"]
    h = lab["holdout"]
    f = []

    def add(fid, kind, what, why, source=None, status="OPEN"):
        f.append({"id": fid, "kind": kind, "what": what, "why": why,
                  "source": source, "status": status})

    add("FLAG-V3-LOGLOSS", "measured-negative",
        f"Raw model log-loss {m['log_loss']} is worse than a coin ({m['log_loss_coin']}).",
        "Published on the calibration page with the reliability table that explains it, and the "
        "measured shrink correction that fixes it.",
        None, "DISCLOSED")
    add("FLAG-V3-TOTAL-CONSTANT", "measured-negative",
        f"Forward total MAE {m['mae_total_fwd']} is worse than a constant "
        f"({m['mae_total_best_constant']}).",
        "The possession formula is the brief's; its forecast is not useful for a total. Printed "
        "beside the formula, not instead of it.", None, "DISCLOSED")
    add("FLAG-V3-ROTATION-UNFILED", "blocked-input",
        "No club's minutes redistribution is computed.",
        "Per-player game logs are not in the repository, so top-eight shares and replacement "
        "shares cannot be measured. No estimate is substituted.", None, "BLOCKED")
    add("FLAG-V3-ODDS-BLOCKED", "blocked-input",
        "No market price, so no edge, no CLV, no ROI and no stake.",
        "G6 is NOT MEASURABLE. The market-weight formula is published with illustrative inputs "
        "labelled as illustrations.", None, "BLOCKED")
    add("FLAG-V3-WITHIN-DAY", "not-measured",
        "Within-day injury diff is NOT MEASURED.",
        f"{inj['within_day_diff']['revisions_fetched']} of "
        f"{inj['within_day_diff']['revisions_listed']} revisions fetched.",
        inj["meta"]["source_index"], "OPEN")
    add("FLAG-V3-SLATE-TURNOVER", "method-caveat",
        "The two captured injury releases share zero players.",
        "Their diff measures slate turnover, not status change. 0 status changes must not be read "
        "as 'nothing changed today'.", inj["meta"]["source_pdf"], "DISCLOSED")
    add("FLAG-V3-RANK-WITHHELD", "sample-size",
        f"Largest settled count {max((s['bets'] for s in strat['scoreboard']), default=0)} is below "
        f"the {strat['meta']['min_bets_rank']}-bet ranking bar.",
        "No rule receives a leaderboard position. A rank from this many bets would be noise.",
        None, "DISCLOSED")
    add("FLAG-V3-MULTIPLICITY", "method-caveat",
        f"{len(strat['scoreboard'])} rules were tested simultaneously.",
        f"Holm-adjusted p is used for the verdict; the unadjusted p is also shown so a reader can "
        f"disagree with the correction.", None, "DISCLOSED")
    add("FLAG-V3-ALPHA-FITTED", "method-caveat",
        f"The calibration shrink α={h['alpha']} is a fitted parameter.",
        "It is fitted on one slice and scored on another, which makes the gain evidence rather "
        "than a derivation. A second season would test whether it is stable.", None, "DISCLOSED")
    add("FLAG-V3-TRAVEL-UNDERSTATE", "method-caveat",
        "Per-game travel understates multi-game road trips.",
        "The away figure is distance from the previous venue only. Accumulated trip distance is "
        "not carried, and a dash means unknown rather than zero.", None, "DISCLOSED")
    add("FLAG-V3-QUARTERS", "blocked-input",
        "Quarter scores exist for the five 2026-11-14 finals only.",
        "Earlier dates in the results feed carry a final score without quarters. Every block that "
        "was read sums to its printed final; the rest are blank with a reason rather than filled.",
        O.SOURCES["results_feed"][1] if "results_feed" in O.SOURCES else None, "PARTIAL")
    add("FLAG-V3-FREE-HCA", "method-caveat",
        f"The unconstrained HCA fit returns h={lab['meta'].get('hca_free', 'n/a')}.",
        "It is reported and not used: a free home term absorbs rating error and calls it home "
        "court. The pinned value is what the model publishes.", None, "DISCLOSED")
    add("FLAG-V3-CDN-500", "source-defect",
        "The NBA CDN box-score JSON endpoint returned HTTP 500.",
        "No JSON API is available, so every number is scraped from a rendered page. That is slower "
        "and more fragile and it is why each capture names the exact URL.", None, "OPEN")
    add("FLAG-V3-V2-INHERITED", "pre-existing",
        "Two defects carried over from v2, untouched because they are outside this session's scope.",
        "README has a duplicated 'Which tree is published' block, and refresh.yml greps '^[fail]' "
        "where the tool prints '[FAIL]'. Both are flagged, not fixed.",
        "https://github.com/wingbangboozle1-lang/NBA2/blob/main/.github/workflows/refresh.yml",
        "OPEN")
    return f
