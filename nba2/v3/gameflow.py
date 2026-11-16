"""Late-game / garbage-time decomposition from **official quarter scores**.

The brief asks for game-flow analysis. Schedule-derived rest / B2B / 3-in-4 and travel are
already published; the part that was explicitly *not* built is the late-game (garbage-time)
decomposition, because true pace / garbage-time needs play-by-play (blocked, R-047).

This module closes the part of that gap that is measurable **without** play-by-play: the
official LINESCORE / gamebook quarter scores. Garbage time inflates 4th-quarter scoring, so
the decomposition is built from the one thing the official quarter table *does* give us —
how the two teams split their points across the four quarters.

Definitions (all re-derivable from the committed quarter scores, no fitted parameter):

* ``early_total``  = combined points scored in Q1+Q2+Q3 (both teams).
* ``late_total``   = combined points scored in Q4 (both teams).
* ``early_rate``   = early_total / 3 — the average combined points per quarter over the
  first three quarters. A quarter is 12 minutes, so this is a per-quarter rate.
* ``inflation``    = late_total - early_rate. Positive means Q4 scored *more* than the
  average of the first three quarters — the signature of late-game inflation (resting
  starters, widened gap, more possessions at the rim in a blowout).
* ``inflation_z``  = inflation standardised against the **league** sd of inflation across
  the games in this window. |z| above the noise band flags a game as late-game inflated.
* ``adj_total``    = early_total + early_rate — the total with the late-game inflation
  removed: it answers "what would this game's total have been if Q4 scored at the same
  rate as Q1–Q3?". This is a *derived* control total, never a forecast.

Nothing is imputed. A game whose official quarter table did not extract (or was not
captured) is published with blank decomposition cells and the flag that explains it.

Sources are the official gamebook PDFs (``statsdmz.nba.com/pdfs/...``) for the 2026-11-13
games and the official game-summary LINESCORE for the 2026-11-14 game.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from . import official as O

ROOT = Path(__file__).resolve().parents[2]
CAP = ROOT / "data" / "raw" / "capture_2026-11-15"
GAMEBOOKS = CAP / "gamebooks_2026-11-13.json"

# |z| above this is outside the noise band -> the game is flagged late-game inflated.
# Matches the project's NOISE_BAND_Z convention (model.py).
NOISE_BAND_Z = 2.0


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def _sd(xs):
    if len(xs) < 2:
        return None
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def quarter_games() -> list[dict]:
    """Every game with a usable official quarter table, plus flagged near-misses.

    Returns one dict per game. Games whose quarters are missing/unextractable are kept
    (with ``quarters=None`` and a flag) so coverage is explicit rather than silent.
    """
    out: dict[str, dict] = {}

    # --- 2026-11-13 games: official gamebook PDFs -------------------------------
    gb = _load(GAMEBOOKS)
    for g in gb.get("games", []):
        gid = g["game_id"]
        q = g.get("quarters")
        out[gid] = {
            "date": g["date"], "game_id": gid,
            "away": g["away"], "home": g["home"],
            "away_pts": g["away_pts"], "home_pts": g["home_pts"],
            "quarters": q,
            "source_url": g.get("gamebook_url") or g.get("game_url"),
            "source_label": "gamebook PDF",
            "flag": None if q else "I-F8F-06 quarter scores did not extract",
        }

    # --- 2026-11-14 games: official game-summary LINESCORE ---------------------
    for r in O.RESULTS:
        gid = r["game_id"]
        if gid in out:
            continue
        aq, hq = r.get("away_q"), r.get("home_q")
        q = (aq, hq) if (aq and hq) else None
        out[gid] = {
            "date": r["date"], "game_id": gid,
            "away": r["away"], "home": r["home"],
            "away_pts": r["away_pts"], "home_pts": r["home_pts"],
            "quarters": q,
            "source_url": r.get("source_url"),
            "source_label": "LINESCORE",
            "flag": None if q else "F-304 linescore not captured",
        }

    return [out[k] for k in sorted(out)]


def _norm_quarters(q) -> tuple[list, list] | None:
    """Normalise either capture shape to (away_q, home_q).

    Gamebooks store ``{"AWAY": [...], "HOME": [...]}``; the LINESCORE feed stores a
    2-tuple ``(away_q, home_q)``. Both are official; both are accepted. Overtime games
    carry a 5th period — it is kept (for the printed line) but the decomposition uses the
    four regulation quarters only, because OT is a distinct phenomenon from regulation
    late-game inflation.
    """
    if not q:
        return None
    if isinstance(q, dict):
        if len(q) != 2:
            return None
        vals = list(q.values())
        if not all(isinstance(v, list) and len(v) >= 4 for v in vals):
            return None
        return (vals[0], vals[1])
    if isinstance(q, (list, tuple)) and len(q) == 2:
        if all(isinstance(v, list) and len(v) >= 4 for v in q):
            return (q[0], q[1])
    return None


def _combined(aq, hq) -> list[int]:
    return [aq[i] + hq[i] for i in range(4)]


def _decompose(game: dict, inflation_sd: float | None) -> dict:
    """Add the decomposition fields to one game dict (in place copy)."""
    q = _norm_quarters(game["quarters"])
    base = {
        "date": game["date"], "game_id": game["game_id"],
        "matchup": f"{game['away']} @ {game['home']}",
        "away": game["away"], "home": game["home"],
        "away_pts": game["away_pts"], "home_pts": game["home_pts"],
        "total_pts": game["away_pts"] + game["home_pts"],
        "source_url": game["source_url"], "source_label": game["source_label"],
        "flag": game["flag"],
    }
    if not q:
        base.update({
            "quarters_txt": None, "early_total": None, "late_total": None,
            "early_rate": None, "inflation": None, "inflation_z": None,
            "adj_total": None, "late_inflated": None, "late_deflated": None, "ot": None,
        })
        return base

    aq, hq = q
    ot = (aq[4] + hq[4]) if (len(aq) > 4 or len(hq) > 4) else None
    base["ot"] = ot
    base["quarters_txt"] = ("/".join(str(x) for x in aq) + " / " +
                            "/".join(str(x) for x in hq))
    # combined points per regulation quarter, both teams
    comb = _combined(aq, hq)
    early_total = sum(comb[:3])
    late_total = comb[3]
    early_rate = early_total / 3.0
    inflation = late_total - early_rate
    z = (inflation - _mean(_inflations())) / inflation_sd if inflation_sd else None
    base.update({
        "early_total": round(early_total, 1),
        "late_total": round(late_total, 1),
        "early_rate": round(early_rate, 2),
        "inflation": round(inflation, 2),
        "inflation_z": round(z, 3) if z is not None else None,
        "adj_total": round(early_total + early_rate, 1),
        # garbage-time inflation is a *positive* Q4 excess; a large negative z is a
        # late-game tightening (defensive grind), a different phenomenon — both are
        # published, labelled distinctly, never conflated.
        "late_inflated": (z > NOISE_BAND_Z) if z is not None else None,
        "late_deflated": (z < -NOISE_BAND_Z) if z is not None else None,
    })
    return base


def _inflations() -> list[float]:
    out = []
    for g in quarter_games():
        q = _norm_quarters(g["quarters"])
        if not q:
            continue
        comb = _combined(*q)
        out.append(comb[3] - sum(comb[:3]) / 3.0)
    return out


def decomposition() -> dict:
    """The full late-game decomposition: per-game rows + the league summary."""
    games = quarter_games()
    infls = _inflations()
    sd = _sd(infls)
    rows = [_decompose(g, sd) for g in games]
    n_with = len(infls)
    early_rates = [r["early_rate"] for r in rows if r["early_rate"] is not None]
    summary = {
        "n_games_total": len(rows),
        "n_games_with_quarters": n_with,
        "n_games_missing_quarters": len(rows) - n_with,
        "n_overtime": sum(1 for r in rows if r.get("ot")),
        "mean_early_rate": round(_mean(early_rates), 2) if early_rates else None,
        "inflation_mean": round(_mean(infls), 3) if infls else None,
        "inflation_sd": round(sd, 3) if sd else None,
        "n_late_inflated": sum(1 for r in rows if r["late_inflated"] is True),
        "n_late_deflated": sum(1 for r in rows if r["late_deflated"] is True),
        "noise_band_z": NOISE_BAND_Z,
        "rule": ("inflation = Q4 combined − mean(Q1,Q2,Q3 combined); z standardised against the "
                 "window's own sd; |z|>2 flags late-game inflation; adj_total = early_total + "
                 "early_rate (late-game inflation removed)"),
        "src": ("data/raw/capture_2026-11-15/gamebooks_2026-11-13.json (official gamebook PDFs) "
                "+ nba2/v3/official.py RESULTS (official LINESCORE)"),
    }
    return {"summary": summary, "rows": rows}


def source_for(game_id: str) -> str:
    for g in quarter_games():
        if g["game_id"] == game_id:
            return g["source_url"]
    return ""
