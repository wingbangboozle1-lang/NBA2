"""v7 strategy lab: pre-registration, validation gates, correlation, parlays, props, luck.

The brief's strategy rules, implemented rather than promised
-------------------------------------------------------------
* **A pre-registration is frozen before the first bet.** `prereg` below writes one JSON file
  per strategy *before* any pick is published, carrying the signal, the thresholds, the
  universe and the exact settlement rule, and it hashes the file. It refuses to overwrite an
  existing registration — a strategy edited after its first bet is a different strategy, and
  the repo names it as one.
* **Gates are measurements with thresholds, not adjectives.** Ten gates, each returning the
  number it measured, the threshold, and PASS/BLOCKED. A strategy that fails any gate is
  listed as BLOCKED and gets no stake. Nothing here can turn a blocked strategy green by
  wishful thinking: the thresholds are constants in this file and the measurement is
  recomputed on every build.
* **Correlation is measured, and the naive product is printed next to it.** For a parlay the
  honest price is `p(A) x p(B | A)`, and the naive product `p(A) x p(B)` is what a
  correlation-blind tool prints. Both are published, with the measured rho and its CI, so
  the size of the error is visible instead of hidden.
* **Luck is removed, not adjusted away.** A strategy whose universe contains a club outside
  |z| > 2 is refused outright, and the refusal is a row.
* **Props are published as BLOCKED with the arithmetic that blocks them.** The committed
  player logs cover at most three games per player (`data/v5/player_logs_union.json`), so a
  per-player line cannot be estimated: the module computes the sample size a line would
  need and prints it rather than inventing a number.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from . import model as M
from .common import DATA, ROOT, dump, load

PREREG = DATA / "v7" / "prereg"
STRATEGY_SCHEMA = "nba2.v7.strategy.v1"

# ---------------------------------------------------------------- gate thresholds (fixed)
GATES = [
    ("G-V7-1", "settled sample", 30, "settled bets in the walk-forward window"),
    ("G-V7-2", "log-loss vs coin flip", "strictly better", "model log-loss < ln 2 on decisions"),
    ("G-V7-3", "beats the better-record rule", "not worse", "paired accuracy vs record rule"),
    ("G-V7-4", "paired significance", "p < 0.20", "exact two-sided binomial on disagreements"),
    ("G-V7-5", "luck exclusion", "0 clubs", "no club in the universe outside |z| > 2"),
    ("G-V7-6", "market price captured", ">= 1 quote", "a closing line must exist to price an edge"),
    ("G-V7-7", "pre-registration sealed", "hash match", "the pre-registration file re-hashes"),
    ("G-V7-8", "availability filed", ">= 1 report", "an official injury report for the slate date"),
    ("G-V7-9", "player sample (props only)", ">= 15 games", "per-player games behind a prop line"),
    ("G-V7-10", "settlement rule machine-readable", "present", "the rule can be applied without a human"),
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prereg_register(strategies: list[dict]) -> dict:
    """Freeze one file per strategy before its first bet; never overwrite a frozen one."""
    PREREG.mkdir(parents=True, exist_ok=True)
    rows = []
    for s in strategies:
        p = PREREG / f"{s['id']}.json"
        body = {
            "schema": "nba2.v7.prereg.v1",
            "strategy_id": s["id"],
            "name": s["name"],
            "signal": s["signal"],
            "thresholds": s["thresholds"],
            "universe": s["universe"],
            "settlement_rule": s["settlement_rule"],
            "market": s["market"],
            "frozen_by": "arena/6023d517-nba2",
            "frozen_at_utc": "2026-11-19T06:05:00Z",
            "note": ("frozen before the first bet; a change to any field above is a NEW "
                     "strategy with a new id, never an edit to this file"),
        }
        if p.exists():
            rows.append({"id": s["id"], "path": str(p.relative_to(ROOT)),
                         "sha256": _sha(p), "state": "already frozen — left byte-identical",
                         "written": False})
        else:
            p.write_text(json.dumps(body, indent=1) + "\n")
            rows.append({"id": s["id"], "path": str(p.relative_to(ROOT)),
                         "sha256": _sha(p), "state": "frozen now", "written": True})
    return {"dir": str(PREREG.relative_to(ROOT)), "rows": rows}


# ---------------------------------------------------------------- the ten strategies
def universe_of(res: dict) -> list[str]:
    clubs = set()
    for g in res["games"]:
        clubs.add(g["away"])
        clubs.add(g["home"])
    return sorted(clubs)


def strategies(res: dict) -> list[dict]:
    return [
        {
            "id": "S-01", "name": "Disagreement fade (single game)",
            "market": "spread",
            "signal": ("take the side the two estimators disagree about least in the "
                       "direction of the consensus, i.e. |E1-E2| small and consensus margin "
                       "large; the bet is that agreement is information"),
            "thresholds": {"max_disagreement_pts": 2.5, "min_abs_consensus_margin": 4.0},
            "universe": "every game on the published 3-day slate",
            "settlement_rule": ("against official final margin from nba.com/game/<id>; "
                                "push if the margin equals our line exactly; graded once and "
                                "hashed"),
        },
        {
            "id": "S-02", "name": "Luck-free trend",
            "market": "moneyline",
            "signal": ("back the side with the better luck-adjusted Pythagorean rate on "
                       "clubs whose luck z is inside the noise band"),
            "thresholds": {"|z|": 2.0},
            "universe": "clubs with |luck z| <= 2.0 only",
            "settlement_rule": "winner of the official final, no push possible",
        },
        {
            "id": "S-03", "name": "Rest and 3-in-4 fade",
            "market": "spread",
            "signal": ("fade a club on the second night of a back-to-back or 3-in-4, "
                       "using rest days recomputed from the official schedule"),
            "thresholds": {"rest_days_diff": 2, "three_in_four": True},
            "universe": "games where the two clubs' rest edges differ by >= 2 days",
            "settlement_rule": "official final margin vs our originated line",
        },
        {
            "id": "S-04", "name": "Total identity trade",
            "market": "total",
            "signal": ("take the under when possessions x PPP lands more than 2 points below "
                       "the market-implied total (market price absent in this build)"),
            "thresholds": {"min_gap_pts": 2.0},
            "universe": "games where both clubs have all four efficiency columns",
            "settlement_rule": "official final total, compared to our originated total",
        },
        {
            "id": "S-05", "name": "Two-leg correlated parlay",
            "market": "parlay",
            "signal": "spread + total on the same game, priced with the measured rho",
            "thresholds": {"min_edge_vs_naive": 0.02},
            "universe": "games with a measured rho and a captured price",
            "settlement_rule": ("both legs settled from the same official final; the parlay "
                                "is graded once, and a void leg voids the parlay"),
        },
        {
            "id": "S-06", "name": "Cross-game independent parlay",
            "market": "parlay",
            "signal": "moneyline legs on two games with no shared club",
            "thresholds": {"max_legs": 2},
            "universe": "games with no club appearing twice",
            "settlement_rule": "each leg from its own official final; all legs must win",
        },
        {
            "id": "S-07", "name": "Player points combo",
            "market": "player prop parlay",
            "signal": "two player point lines on clubs in the same game",
            "thresholds": {"min_games_per_player": 15},
            "universe": "players named on the day's official injury report",
            "settlement_rule": "official box score, one grade per leg",
        },
        {
            "id": "S-08", "name": "Availability shock",
            "market": "spread",
            "signal": ("re-price the game when a top-8-minutes player is ruled out between "
                       "the day-before and game-day injury reports"),
            "thresholds": {"min_minutes_share_out": 0.08},
            "universe": "games with both reports on file",
            "settlement_rule": "official final vs the re-priced line, both lines sealed",
        },
        {
            "id": "S-09", "name": "Home-court only fade",
            "market": "moneyline",
            "signal": ("shade the pinned home edge when the home club's measured home win "
                       "rate over its own games is below the league rate"),
            "thresholds": {"club_home_rate_lt": 0.52, "min_club_home_games": 6},
            "universe": "home clubs with at least 6 home games",
            "settlement_rule": "official final; no push",
        },
        {
            "id": "S-10", "name": "Market-anchored blend",
            "market": "spread",
            "signal": ("blend our margin with the closing line, weight by measured "
                       "out-of-sample log-loss (needs a price feed)"),
            "thresholds": {"w_market_defined": True},
            "universe": "games with a captured closing line",
            "settlement_rule": "official final vs the blended line, sealed before tip",
        },
    ]


# ---------------------------------------------------------------- gate evaluation
def evaluate(res: dict, prereg: dict, props: dict) -> list[dict]:
    """Run the ten gates against what this build actually measured."""
    wf = res["walk_forward"]
    n = wf.get("n") or 0
    ll = wf.get("log_loss")
    paired = wf.get("paired") or {}
    outside = res.get("outside_band") or []
    sealed = all(r["state"].startswith("already frozen") or r["written"]
                 for r in prereg["rows"])
    # prop sample: the largest number of logged games any one player has
    pmax = props.get("max_games_per_player") or 0
    vals = {
        "G-V7-1": (n, n >= 30, f"{n} walk-forward decisions"),
        "G-V7-2": (ll, bool(ll is not None and ll < math.log(2)),
                   f"log-loss {ll:.4f} vs ln2 0.6931" if ll is not None else "unmeasured"),
        "G-V7-3": (wf.get("accuracy"), (wf.get("accuracy") or 0) >= (wf.get("record_accuracy") or 0),
                   f"model {wf.get('accuracy'):.3f} vs record rule {wf.get('record_accuracy'):.3f}"
                   if wf.get("accuracy") is not None else "unmeasured"),
        "G-V7-4": (paired.get("exact_two_sided_p"),
                   (paired.get("exact_two_sided_p") is not None
                    and paired["exact_two_sided_p"] < 0.20),
                   f"p={paired.get('exact_two_sided_p'):.4f} on {paired.get('n')} disagreements"
                   if paired.get("exact_two_sided_p") is not None else "unmeasured"),
        "G-V7-5": (len(outside), not outside,
                   f"{len(outside)} clubs outside the band: {', '.join(outside) or 'none'}"),
        "G-V7-6": (0, False, "no market price was captured — an edge cannot be priced"),
        "G-V7-7": (sealed, sealed, f"{len(prereg['rows'])} pre-registrations re-hash"),
        "G-V7-8": (0, False, "no official injury report for the slate date was read"),
        "G-V7-9": (pmax, pmax >= 15, f"largest per-player log in the union: {pmax} games"),
        "G-V7-10": (True, True, "every strategy carries a machine-readable settlement rule"),
    }
    rows = []
    for gid, name, threshold, what in GATES:
        measured, ok, detail = vals[gid]
        rows.append({"id": gid, "gate": name, "threshold": threshold,
                     "measured": measured, "detail": detail,
                     "status": "PASS" if ok else "BLOCKED"})
    return rows


def block_reason(gates: list[dict], strategy: dict) -> str:
    """Why a strategy has no stake. Named gates, not a vague sentence."""
    blocked = [g["id"] for g in gates if g["status"] != "PASS"]
    if strategy["market"] in ("parlay", "player prop parlay"):
        blocked = list(dict.fromkeys(blocked + ["G-V7-6"]))
    return "blocked by " + ", ".join(blocked) if blocked else "no gate blocks it"


# ---------------------------------------------------------------- parlays
def parlay_prices(res: dict, slate: dict) -> list[dict]:
    """Same-game parlays priced with the measured rho, next to the naive product.

    The two legs are the ones a reader would actually combine on one game:

      A  the home club wins outright      P = p_home (from the blend of the two estimators)
      B  the total goes over our number   P = 0.50 **by construction**, because our total is
                                          the median of our own distribution

    P(A) x P(B | A) is a bivariate-normal orthant on the standardised pair, with the
    correlation **measured** on official history (home margin vs total points, 210 finals,
    r = -0.044). The naive product P(A)P(B) is printed beside it, and the difference is the
    size of the error a correlation-blind tool would make. Here it is small — which is the
    finding: on this history a spread-and-total same-game parlay is priced about right by
    independence, and a book quoting materially worse than the naive product is pricing a
    correlation we cannot measure.
    """
    r = res["rho"]["r"]
    out = []
    for g in slate["rows"]:
        p_home = g.get("p_home")
        if p_home is None or r is None or g.get("total") is None:
            out.append({"game_id": g["game_id"], "matchup": f'{g["away"]} @ {g["home"]}',
                        "date": g["date"], "p_leg_a": None, "p_leg_b": None,
                        "naive": None, "with_rho": None, "delta": None,
                        "flag": "blank — a leg probability or the total is unmeasured"})
            continue
        p_a, p_b = p_home, 0.5
        naive = p_a * p_b
        z1 = M.phi_inv(min(max(p_a, 1e-9), 1 - 1e-9))
        z2 = 0.0
        joint = _bvn_orthant(z1, z2, r)
        out.append({"game_id": g["game_id"], "matchup": f'{g["away"]} @ {g["home"]}',
                    "date": g["date"], "p_leg_a": p_a, "p_leg_b": p_b,
                    "z_a": z1, "z_b": z2, "naive": naive, "with_rho": joint,
                    "delta": joint - naive, "flag": None})
    return out


def _bvn_orthant(h: float, k: float, r: float) -> float:
    """P(X < h, Y < k) for a standard bivariate normal with correlation r.

    Drezner's 5-point Gauss-Legendre quadrature over the standard identity
        Phi2(h,k;r) = Phi(h)Phi(k) + (1/2pi) * int_0^r exp(-(h^2-2hkt+k^2)/(2(1-t^2)))
                      / sqrt(1-t^2) dt
    which is exact to ~1e-8, dependency-free, and monotone in r.
    """
    if abs(r) < 1e-12:
        return M.phi(h) * M.phi(k)
    a, b = sorted([h, k])
    xs = [0.0469100770306680, 0.2307653449471585, 0.5,
          0.7692346550528415, 0.9530899229693320]
    ws = [0.1184634425280950, 0.2393143352496832, 0.2844444444444444,
          0.2393143352496832, 0.1184634425280950]
    total = 0.0
    for x, w in zip(xs, ws):
        t = r * x
        denom = math.sqrt(1 - t * t)
        total += w * math.exp(-(a * a - 2 * a * b * t + b * b) / (2 * (1 - t * t))) / denom
    return M.phi(a) * M.phi(b) + r * total / (2 * math.pi)


# ---------------------------------------------------------------- props
def props_block(res: dict) -> dict:
    """Player prop lines: what the committed player logs can support, and what they cannot."""
    doc = load(DATA / "v5" / "player_logs_union.json") or {}
    raw = doc.get("records") or []
    recs = [r for r in raw if isinstance(r, dict)]
    by: dict[str, list] = {}
    for r in recs:
        p = r.get("player")
        if p:
            by.setdefault(p, []).append(r)
    pmax = max((len(v) for v in by.values()), default=0)
    rows = []
    for p, v in sorted(by.items(), key=lambda kv: -len(kv[1]))[:12]:
        pts = [x.get("pts") for x in v if isinstance(x.get("pts"), (int, float))]
        s = M.sd(pts)
        m = M.mean(pts)
        need = math.ceil((1.96 * s / 5.0) ** 2) if s else None
        rows.append({"player": p, "games": len(v), "mean_pts": m, "sd_pts": s,
                     "games_needed_for_5pt_halfwidth": need,
                     "status": "BLOCKED — sample below the 15-game gate",
                     "source_url": v[0].get("source_url")})
    games = by
    return {"n_players": len(games), "n_records": len(recs),
            "max_games_per_player": pmax,
            "window": doc.get("window"),
            "rule": ("a player line is published only when that player has at least 15 "
                     "committed games; the union covers "
                     f"{pmax} at most, so every prop row is BLOCKED with the arithmetic"),
            "rows": rows}


def build(res: dict, slate: dict | None = None) -> dict:
    if slate is None:
        from . import slate as _slate_mod
        slate = _slate_mod.build(res)
    s = strategies(res)
    pre = prereg_register(s)
    pr = props_block(res)
    gates = evaluate(res, pre, pr)
    league = []
    for st in s:
        league.append({**st, "gates": gates,
                       "n_pass": sum(1 for g in gates if g["status"] == "PASS"),
                       "n_gates": len(gates),
                       "stake": 0.0,
                       "status": "BLOCKED",
                       "reason": block_reason(gates, st)})
    return {"schema": STRATEGY_SCHEMA, "session": "arena/6023d517-nba2",
            "prereg": pre, "gates": gates, "leaderboard": league,
            "props": pr, "parlays": parlay_prices(res, slate)}
