"""v4 model: two independent estimators, a pinned home-court term, luck z-scores,
possessions x points-per-possession totals, and a hard projection / bet split.

The maths is deliberately the same shape as v3 (there is one right way to pin HCA and to
build a possessions-based total, and v3's is correct), but **every input is re-cut from
this session's own capture**. Nothing is imported from ``nba2/v3/official.py``: that
snapshot is a day older, and a model that silently inherited it would be publishing a
11/15 rating under a 11/16 label.

Surface contract (the brief's "never mix them")
-----------------------------------------------
``SURFACES = ("projection", "bet")``

* **projection** — what we can publish now. A projected margin, a projected total, the
  disagreement between the two estimators, and the trigger price at which acting would
  become rational. It needs *no market price*, and it is the only surface with any rows.
* **bet** — what we are not allowed to publish. A row can only exist here if a measured
  price exists for the market, because a stake without a price is a guess. With no odds
  feed every bet-surface row is refused by ``bet_surface_rows()`` and the refusal is
  counted, not hidden.

``assert_no_mixing()`` is the enforcement: it raises if any published row carries a bet
field on the projection surface or a projection-only field on the bet surface.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from . import capture as C

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "data" / "raw" / "history"
RAW = ROOT / "data" / "raw"

PYTHAG_EXP = 13.91          # Basketball-Reference convention; sensitivity rows published
NOISE_BAND_Z = 2.0          # |z| > 2 is outside the noise band -> strategy refused
HCA_MIN_GAMES = 50          # a home-win rate on fewer games is not a measurement

SURFACES = ("projection", "bet")

PROJECTION_FIELDS = (
    "game_id", "date", "time_et", "matchup", "arena", "city", "state",
    "surface", "possessions", "ppp_home", "ppp_away",
    "proj_home_pts", "proj_away_pts", "proj_total",
    "e1_margin", "e2_margin", "disagreement", "consensus_margin",
    "spread_home", "p_home", "p_home_e1", "p_home_e2",
    "trigger_price", "market_price", "stake_pct", "price_status",
    "luck_gate", "availability", "flow", "sources",
)
BET_FIELDS = ("market_price", "market_book", "edge_vs_market", "stake_pct", "kelly_fraction")


# --------------------------------------------------------------------------- statistics
def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def phi_inv(p: float) -> float:
    """Acklam's approximation, |error| < 1.15e-9."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411411e+00, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    elif p <= ph:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    return x


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def sd(xs):
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = mean(xs), mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


# ------------------------------------------------------------------- played games (history)
def played_games() -> dict:
    """Every official final in the repo, **plus** this session's 11/15 finals.

    The 11/15 finals are appended from this session's capture rather than from v3's
    hard-coded list, because v3's list only carried five 11/14 games. Deduped by game id;
    neutral-site games are kept but excluded from every home-court statistic.
    """
    games, files = {}, []
    for p in sorted(HISTORY.glob("games_*.json")):
        d = json.loads(p.read_text())
        files.append(p.name)
        for g in d.get("games", []):
            if g.get("away_pts") is None or g.get("home_pts") is None:
                continue
            games[g["game_id"]] = {
                "game_id": g["game_id"], "date": g["date"],
                "away": g["away"], "home": g["home"],
                "away_pts": g["away_pts"], "home_pts": g["home_pts"],
                "home_margin": g["home_pts"] - g["away_pts"],
                "total_pts": g["home_pts"] + g["away_pts"],
                "neutral": bool(g.get("neutral_site")),
                "source_url": g.get("source_url") or g.get("list_url"),
                "origin": p.name,
            }
    # The 11/14 finals were captured to data/raw/capture_2026-11-15/results_2026-11-14.json
    # by the session that fetched them. They are read from that committed capture (which
    # records its own retrieval stamp and source page) rather than re-typed here; a game
    # only enters the pool when it is marked final AND carries both final scores.
    p14 = RAW / "capture_2026-11-15" / "results_2026-11-14.json"
    if p14.exists():
        d14 = json.loads(p14.read_text())
        files.append(str(p14.relative_to(ROOT)))
        for g in d14.get("records", []):
            if g.get("status") != "final" or g.get("away_pts") is None or g.get("home_pts") is None:
                continue  # PENDING games never enter the played pool
            games[g["game_id"]] = {
                "game_id": g["game_id"], "date": g["date"],
                "away": g["away"], "home": g["home"],
                "away_pts": g["away_pts"], "home_pts": g["home_pts"],
                "home_margin": g["home_pts"] - g["away_pts"],
                "total_pts": g["home_pts"] + g["away_pts"],
                "neutral": bool(g.get("neutral_site")),
                "source_url": g.get("source_url"),
                "origin": str(p14.relative_to(ROOT)),
            }
    for g in C.finals_2026_11_15():
        games[g["game_id"]] = {
            "game_id": g["game_id"], "date": g["date"], "away": g["away"], "home": g["home"],
            "away_pts": g["away_pts"], "home_pts": g["home_pts"],
            "home_margin": g["home_margin"], "total_pts": g["total_pts"],
            "neutral": False, "source_url": g["final_source_url"],
            "origin": "data/raw/refresh_2026-11-15/results_2026-11-15.json",
        }
    # RQ-8892-02 re-cut (arena/6b9f3bbe-nba2): join the committed official finals feeds
    # through 2026-11-18 so the played pool is the exact 222 the standings card implies.
    for pat in ("finals_2026-11-16.json", "finals_2026-11-17.json", "finals_2026-11-18.json"):
        pf = RAW / pat
        if not pf.exists():
            continue
        df = json.loads(pf.read_text())
        files.append(str(pf.relative_to(ROOT)))
        for g in df.get("records", []):
            if g.get("status") != "final" or g.get("away_pts") is None or g.get("home_pts") is None:
                continue
            a, h = g.get("away_team") or g.get("away"), g.get("home_team") or g.get("home")
            if not (a and h):
                continue  # a row without club cells cannot enter the played pool (never inferred)
            games[g["game_id"]] = {
                "game_id": g["game_id"], "date": g["date"],
                "away": a, "home": h,
                "away_pts": g["away_pts"], "home_pts": g["home_pts"],
                "home_margin": g["home_pts"] - g["away_pts"],
                "total_pts": g["home_pts"] + g["away_pts"],
                "neutral": False, "source_url": g.get("final_source_url") or g.get("source"),
                "origin": str(pf.relative_to(ROOT)),
            }
    return {"files": files, "games": [games[k] for k in sorted(games)]}


def home_court(played: list[dict]) -> dict:
    """Pin HCA to the measured home-win rate; do not fit it."""
    real = [g for g in played if not g["neutral"]]
    n = len(real)
    hw = sum(1 for g in real if g["home_margin"] > 0)
    margins = [g["home_margin"] for g in real]
    p_home = hw / n if n else None
    s = sd(margins)
    h = s * phi_inv(p_home) if (p_home and s) else None
    return {
        "n_games": n, "home_wins": hw,
        "home_win_rate": round(p_home, 4) if p_home is not None else None,
        "neutral_excluded": len(played) - n,
        "margin_sd": round(s, 3) if s else None,
        "margin_mean": round(mean(margins), 3) if margins else None,
        "hca_points": round(h, 3) if h else None,
        "rule": "h = sd(home margin) x Phi^-1(measured home win rate)",
        "measured": n >= HCA_MIN_GAMES,
        "note": ("HCA is a restatement of an official count, not an estimated edge: with "
                 "this h and this sd, two otherwise equal clubs get exactly the measured "
                 "home-win probability. It is never fitted to results."),
    }


# --------------------------------------------------------------------- two estimators
def estimator_efficiency(home: dict, away: dict, hca: float, poss: float) -> float:
    """E1 - the efficiency view. Uses OffRtg and DefRtg only (advanced page)."""
    net_h = home["off_rtg"] - home["def_rtg"]
    net_a = away["off_rtg"] - away["def_rtg"]
    return (net_h - net_a) / 100.0 * poss + hca


def pythagorean(pts_for: float, pts_against: float, exp: float = PYTHAG_EXP) -> float:
    return pts_for ** exp / (pts_for ** exp + pts_against ** exp)


def log5(p_h: float, p_a: float) -> float:
    den = p_h + p_a - 2 * p_h * p_a
    return (p_h - p_h * p_a) / den if den else 0.5


def estimator_scoring(home: dict, away: dict, hca: float, sigma: float) -> float:
    """E2 - the ratio view. Uses the **traditional** page's points scored and the
    **opponent** page's points allowed, so it does not share a column with E1."""
    p_h = pythagorean(home["pts_for"], home["opp_pts"])
    p_a = pythagorean(away["pts_for"], away["opp_pts"])
    p_neutral = log5(p_h, p_a)
    return phi_inv(p_neutral) * sigma + hca


def total_from_possessions(home: dict, away: dict) -> dict:
    """Totals are possessions x points-per-possession - never an average of averages."""
    poss = (home["pace"] + away["pace"]) / 2.0
    ppp_h = ((home["off_rtg"] + away["def_rtg"]) / 2.0) / 100.0
    ppp_a = ((away["off_rtg"] + home["def_rtg"]) / 2.0) / 100.0
    return {"possessions": poss, "ppp_home": ppp_h, "ppp_away": ppp_a,
            "proj_home_pts": poss * ppp_h, "proj_away_pts": poss * ppp_a,
            "proj_total": poss * (ppp_h + ppp_a)}


# ------------------------------------------------------------------------- luck z-scores
def luck_table(teams: dict) -> list[dict]:
    """Pythagorean expected wins, the win residual, and its z-score per club."""
    rows = []
    for ab, t in teams.items():
        pf, pa, gp = t["pts_for"], t["opp_pts"], t["gp"]
        exp_p = pythagorean(pf, pa)
        exp_w = exp_p * gp
        resid = t["w"] - exp_w
        z_sd = math.sqrt(gp * exp_p * (1 - exp_p))
        z = resid / z_sd if z_sd else None
        rows.append({
            "team": ab, "name": t["name"], "gp": gp, "w": t["w"], "l": t["l"],
            "pts_for": pf, "pts_against": pa,
            "pythag_win_pct": round(exp_p, 4),
            "expected_wins": round(exp_w, 2), "actual_wins": t["w"],
            "luck_wins": round(resid, 2),
            "luck_z": round(z, 3) if z is not None else None,
            "in_noise_band": (abs(z) <= NOISE_BAND_Z) if z is not None else None,
            "exponent": PYTHAG_EXP,
            "luck_z_exp13_5": None, "luck_z_exp16_5": None,
        })
    for e, key in ((13.5, "luck_z_exp13_5"), (16.5, "luck_z_exp16_5")):
        for r in rows:
            t = teams[r["team"]]
            p = pythagorean(t["pts_for"], t["opp_pts"], e)
            resid = t["w"] - p * t["gp"]
            zsd = math.sqrt(t["gp"] * p * (1 - p))
            r[key] = round(resid / zsd, 3) if zsd else None
    rows.sort(key=lambda r: (r["luck_z"] is None, -(r["luck_z"] or 0)))
    return rows


def outside_band(luck_rows: list[dict]) -> set:
    return {r["team"] for r in luck_rows if r["in_noise_band"] is False}


# ------------------------------------------------------------------------ schedule flow
def flow_for(game: dict, played: list[dict], slate: list[dict]) -> dict:
    """Rest, back-to-back and 3-in-4 from official dates; travel from sourced coordinates."""
    by_team: dict[str, list[str]] = {}
    for g in played:
        if g["date"] > game["date"]:
            continue
        for t in (g["away"], g["home"]):
            by_team.setdefault(t, []).append(g["date"])
    for g in slate:
        if g["date"] > game["date"] or g["game_id"] == game["game_id"]:
            continue
        for t in (g["away"], g["home"]):
            by_team.setdefault(t, []).append(g["date"])
    out = {}
    for side, tri in (("home", game["home"]), ("away", game["away"])):
        dates = sorted({d for d in by_team.get(tri, []) if d < game["date"]})
        last = dates[-1] if dates else None
        rest = None
        if last:
            y, m, d = (int(x) for x in last.split("-"))
            yy, mm, dd = (int(x) for x in game["date"].split("-"))
            import datetime as _dt
            rest = (_dt.date(yy, mm, dd) - _dt.date(y, m, d)).days - 1
        window = [d for d in dates if d >= _shift(game["date"], -3)]
        out[side] = {
            "team": tri, "last_game": last, "rest_days": rest,
            "back_to_back": rest == 0 if rest is not None else None,
            "games_in_3": len(window),  # games in the 3 days before, inclusive
            "three_in_four": len(window) >= 2,
        }
    return out


def _shift(iso: str, days: int) -> str:
    import datetime as dt
    y, m, d = (int(x) for x in iso.split("-"))
    return (dt.date(y, m, d) + dt.timedelta(days=days)).isoformat()


def travel_miles() -> dict:
    """Great-circle miles between this slate's arena and each club's previous venue.

    Coordinates are THIRD-PARTY (see ``data/raw/capture_2026-11-15/arenas_2026-11-15.json``,
    nba2.arena-coords.v1). They are never mixed with an official value: the arena, city and
    state on the same row are official, the mileage is labelled derived-from-third-party.
    """
    p = RAW / "capture_2026-11-15" / "arenas_2026-11-15.json"
    if not p.exists():
        return {"available": False, "reason": "arena coordinate table not present (F-V4-03)"}
    rows = json.loads(p.read_text())["rows"]
    coords = {r["team"]: (r["lat"], r["lon"]) for r in rows if r.get("lat") is not None}
    return {"available": True, "n_clubs": len(coords), "coords": coords,
            "provenance": "THIRD-PARTY (Wikimedia REST / Wikidata P625), read 2026-11-15",
            "source_file": str(p.relative_to(ROOT))}


def haversine_mi(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 3958.7613 * math.asin(math.sqrt(h))


# ----------------------------------------------------------------------- injury availability
STATUS_WEIGHT = {"Out": 0.0, "Doubtful": 0.25, "Questionable": 0.5, "Probable": 0.75,
                 "Available": 1.0}
TEAM_ABBR = {v[0]: k for k, v in C.TEAM_NAMES.items()}


def injury_rows(date: str = "2026-11-16") -> list[dict]:
    rel = C.INJURY_RELEASES[0]
    out = []
    for r in rel["rows"]:
        if r[0] != date:
            continue
        out.append({"date": r[0], "time_et": r[1], "matchup": r[2], "team": r[3],
                    "player": r[4], "status": r[5], "reason": r[6], "note": r[7],
                    "release": rel["stamp_et"],
                    "source_url": rel["url"]})
    return out


def availability_for(game: dict, rows: list[dict]) -> dict:
    """Counts of official statuses per side. Production impact stays blank by policy."""
    out = {}
    for side, tri in (("home", game["home"]), ("away", game["away"])):
        name = C.TEAM_NAMES[tri][0]
        mine = [r for r in rows if r["team"] == name]
        placeholder = any(r["reason"] == "NOT YET SUBMITTED" for r in mine)
        counted = [r for r in mine if r["reason"] != "NOT YET SUBMITTED"]
        by_status = {}
        blank = 0
        for r in counted:
            if not r["status"]:
                # never invent a status bucket: an unread status is counted separately and
                # flagged, so "unlisted" can never be mistaken for a league status word
                blank += 1
                continue
            by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        listed = sum(1 for r in counted if r["status"] in STATUS_WEIGHT)
        out[side] = {
            "team": tri, "rows": len(counted),
            "not_yet_submitted": placeholder,
            "by_status": by_status,
            "n_status_known": listed,
            "n_status_blank": blank,
            # production delta needs two captured games for the same club -> not computed
            "production_impact": None,
            "impact_flag": "F-V4-08 production impact needs a matched before/after pair "
                           "of captured games; the report states status, not minutes",
        }
    return out


# --------------------------------------------------------------------------- price a game
def price_game(game: dict, teams: dict, hca: float, sigma: float, played: list[dict],
               slate: list[dict], luck_band: set, inj: list[dict], travel: dict) -> dict:
    h, a = teams[game["home"]], teams[game["away"]]
    t = total_from_possessions(h, a)
    e1 = estimator_efficiency(h, a, hca, t["possessions"])
    e2 = estimator_scoring(h, a, hca, sigma)
    consensus = (e1 + e2) / 2.0
    # The "trigger price": the price at which the projection stops being a description
    # and becomes a claim with a positive expected value at fair odds. It is a boundary,
    # NOT a recommendation - no stake is ever published without a measured market price.
    p_home = phi(consensus / sigma)
    row = {
        "game_id": game["game_id"], "date": game["date"], "time_et": game["time_et"],
        "matchup": game["matchup"], "arena": game["arena"], "city": game["city"],
        "state": game["state"],
        "surface": "projection",
        "possessions": round(t["possessions"], 2),
        "ppp_home": round(t["ppp_home"], 4), "ppp_away": round(t["ppp_away"], 4),
        "proj_home_pts": round(t["proj_home_pts"], 1),
        "proj_away_pts": round(t["proj_away_pts"], 1),
        "proj_total": round(t["proj_total"], 1),
        "e1_margin": round(e1, 2), "e2_margin": round(e2, 2),
        "disagreement": round(abs(e1 - e2), 2),
        "consensus_margin": round(consensus, 2),
        "spread_home": round(-consensus, 1),
        "p_home": round(p_home, 4),
        "p_home_e1": round(phi(e1 / sigma), 4),
        "p_home_e2": round(phi(e2 / sigma), 4),
        "trigger_price": {"home_ml_min": round(1.0 / p_home, 3) if p_home > 0 else None,
                          "away_ml_min": round(1.0 / (1 - p_home), 3) if p_home < 1 else None,
                          "note": "fair odds from the projection; a bet needs a BETTER "
                                  "price than this and a measured market to compare it to"},
        "market_price": None,
        "stake_pct": 0.0,
        "price_status": "BLOCKED (gate G6): no licensed odds feed - no edge, no stake",
        "luck_gate": {
            "home": h["tri"], "away": a["tri"],
            "home_outside": game["home"] in luck_band,
            "away_outside": game["away"] in luck_band,
            "blocked": (game["home"] in luck_band) or (game["away"] in luck_band),
            "band_z": NOISE_BAND_Z,
        },
        "availability": availability_for(game, inj),
        "flow": {**flow_for(game, played, slate),
                 "travel": _travel_for(game, played, slate, teams, travel)},
        "sources": {
            "advanced": C.SOURCE_PAGES["team_adv"]["url"],
            "traditional": C.SOURCE_PAGES["team_trad"]["url"],
            "opponent": C.SOURCE_PAGES["team_opp"]["url"],
            "standings": C.SOURCE_PAGES["standings"]["url"],
            "schedule": C.SOURCE_PAGES["schedule"]["url"],
            "injury": C.INJURY_RELEASES[0]["url"],
        },
        "source_url": game["source_url"],
    }
    return row


def _travel_for(game: dict, played: list[dict], slate: list[dict], teams: dict,
                travel: dict) -> dict:
    if not travel.get("available"):
        return {"miles": None, "reason": travel.get("reason")}
    coords = travel["coords"]
    out = {}
    for side, tri in (("home", game["home"]), ("away", game["away"])):
        # previous game for this club strictly before this date
        prev = [g for g in played if g["date"] < game["date"]
                and tri in (g["away"], g["home"])]
        prev += [g for g in slate if g["date"] < game["date"] and g["game_id"] != game["game_id"]
                 and tri in (g["away"], g["home"])]
        prev.sort(key=lambda g: g["date"])
        if not prev:
            out[side] = {"from": None, "miles": None,
                         "reason": "no earlier game in the captured record"}
            continue
        last = prev[-1]
        # venue team = the home club of the previous game
        frm, to = last["home"], game["home"]
        if frm in coords and to in coords:
            out[side] = {"from": frm, "from_date": last["date"],
                         "miles": round(haversine_mi(coords[frm], coords[to]), 1),
                         "provenance": travel["provenance"]}
        else:
            out[side] = {"from": frm, "miles": None, "reason": "coordinate missing"}
    return {"legs": out, "provenance": travel["provenance"]}


# ------------------------------------------------------------------------ surface contract
def bet_surface_rows(projections: list[dict], market_prices: dict | None = None) -> dict:
    """Try to build the bet surface. Refuses every row without a measured price.

    A bet row is only constructible when an actual market price exists for that market.
    With no feed, every row is refused and the refusal reason is per-row, so the page can
    print *why* the surface is empty instead of pretending it is complete.
    """
    prices = market_prices or {}
    rows, refused = [], []
    for p in projections:
        price = prices.get(p["game_id"])
        if not price:
            refused.append({
                "game_id": p["game_id"], "date": p["date"], "matchup": p["matchup"],
                "surface": "bet",
                "refusal": "G6: no measured market price for this game",
                "gate": "G6",
                "detail": "a stake is (model probability x price) - 1; without a price the "
                          "expression has no value, so no row is published",
            })
            continue
        edge = (p["p_home"] * price["home_decimal"]) - 1.0
        rows.append({
            "game_id": p["game_id"], "date": p["date"], "matchup": p["matchup"],
            "surface": "bet", "market_price": price["home_decimal"],
            "market_book": price["book"],
            "edge_vs_market": round(edge, 4),
            "stake_pct": round(max(0.0, edge) * 0.25, 4),
            "kelly_fraction": round(edge / (price["home_decimal"] - 1.0), 4) if edge > 0 else 0.0,
        })
    return {"rows": rows, "refused": refused,
            "n_rows": len(rows), "n_refused": len(refused),
            "publishable": bool(rows)}


def assert_no_mixing(rows: list[dict], surface: str) -> None:
    """Raise if a row on ``surface`` carries a field the other surface owns.

    This is the wall the brief asks for, so it is written to fail loudly rather than to
    pass quietly. A projection row may hold the *keys* price/stake (the templates print
    "never published"), but any of them holding a real number is a leak. A bet row must
    hold a price, because an unpriced recommendation is not a bet.
    """
    if surface not in SURFACES:
        raise ValueError(f"unknown surface {surface!r}")
    for r in rows:
        gid = r.get("game_id", "?")
        if r.get("surface") != surface:
            raise AssertionError(f"{surface} row labelled {r.get('surface')!r}: {gid}")

        if surface == "projection":
            # any of these holding a real number is a market or sizing leak
            leaked = []
            for k in ("market_price", "market_book", "edge_vs_market", "stake_pct",
                      "kelly_fraction"):
                v = r.get(k)
                if isinstance(v, str) or (v not in (None, 0.0, 0, False)):
                    leaked.append(f"{k}={v!r}")
            if leaked:
                raise AssertionError(f"projection row carries bet fields {leaked}: {gid}")
            # a projection row may never claim to be priced
            if r.get("price_status", "").startswith("PRICED"):
                raise AssertionError(f"projection row claims a price: {gid}")
        else:
            if r.get("market_price") in (None, ""):
                raise AssertionError(f"bet row has no market price: {gid}")
            if r.get("edge_vs_market") is None:
                raise AssertionError(f"bet row has no edge: {gid}")
            if r.get("stake_pct") in (None, ""):
                raise AssertionError(f"bet row has no stake: {gid}")


# --------------------------------------------------------------------------------- build
def build(verbose: bool = False) -> dict:
    teams = C.teams()
    played = played_games()["games"]
    hc = home_court(played)
    sigma = hc["margin_sd"]
    hca = hc["hca_points"]
    luck = luck_table(teams)
    band = outside_band(luck)
    slate = C.slate()
    inj = injury_rows("2026-11-16")
    travel = travel_miles()

    projections = [price_game(g, teams, hca, sigma, played, slate, band, inj, travel)
                   for g in slate]
    assert_no_mixing(projections, "projection")
    bet = bet_surface_rows(projections)

    n = len(played)
    real = [g for g in played if not g["neutral"]]
    rho_r = pearson([g["home_margin"] for g in real], [g["total_pts"] for g in real])
    rho_ci = None
    if rho_r is not None and len(real) > 3:
        z = 0.5 * math.log((1 + rho_r) / (1 - rho_r))
        se = 1 / math.sqrt(len(real) - 3)
        rho_ci = [round(math.tanh(z - 1.96 * se), 4), round(math.tanh(z + 1.96 * se), 4)]

    return {
        "session": C.SESSION,
        "as_of_utc": C.RETRIEVED_UTC, "as_of_et": C.RETRIEVED_ET,
        "window": {"start": C.WINDOW[0], "end": C.WINDOW[1],
                   "n_games": sum(1 for g in slate if C.WINDOW[0] <= g["date"] <= C.WINDOW[1]),
                   "n_games_extended": len(slate),
                   "rule": "T+0..T+3 published (2026-11-16..11-18); 11/19 captured but "
                           "outside the 3-day publication cap"},
        "history": {"n_games": n, "files": played_games()["files"],
                    "includes": "data/raw/history/games_*.json + this session's 11/15 finals"},
        "home_court": hc,
        "sigma": sigma, "hca": hca,
        "luck": luck, "luck_band_z": NOISE_BAND_Z,
        "outside_band": sorted(band),
        "rho": {"n": len(real), "r": round(rho_r, 4) if rho_r is not None else None,
                "ci95": rho_ci,
                "definition": "r(home margin, total points) over official finals, "
                              "neutral-site games excluded"},
        "projections": projections,
        "bet_surface": bet,
        "teams": teams,
        "injury": {"release": C.INJURY_RELEASES[0]["stamp_et"],
                   "url": C.INJURY_RELEASES[0]["url"],
                   "retrieved_utc": C.INJURY_RELEASES[0]["retrieved_utc"],
                   "rows": inj,
                   "n_rows": len(inj),
                   "layout_notes": [{"id": a, "finding": b}
                                    for a, b in C.INJURY_RELEASES[0]["layout_notes"]]},
        "travel": {k: v for k, v in travel.items() if k != "coords"},
        "sources": C.SOURCE_PAGES, "unread": C.UNREAD,
        "crosschecks": C.crosschecks(),
    }
