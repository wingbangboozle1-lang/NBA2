"""This session's live official capture, loaded by the published build.

Everything here comes from ``audit/2026-11-14-bc867bff/captures.json`` — a transcript of four
official NBA documents fetched by session ``arena/bc867bff-nba2`` on 2026-11-14 between 18:41 and
18:52 UTC:

* the 11/14/26 **01:30 PM ET** injury report (the freshest release on the league's index at
  capture time), 50 designation rows plus 19 club-rows the league had not received;
* the **live club records** on the game-page scoreboard strip (29 of 30 clubs);
* a **re-read of 20 of the 27 games** in the published window, with ids, dates and ET tips;
* the **official per-club season averages** for three clubs (Denver, Cleveland, Minnesota).

The module is read-only with respect to every other file: it never edits the frozen 04:30 AM
transcription in ``official.py``, it *supersedes* it in a separately labelled section, and it
computes the delta between the two releases at build time so the number cannot drift from the
rows actually stored.

What the capture makes possible that was previously published as blocked: an injury row can now
carry the absent player's own season minutes and points, measured against his club's season
points-per-game. That is the first production-impact number this repository has published from a
verified official input. Coverage is three of thirty clubs; the other twenty-seven stay blank and
flagged, because their per-club table was not fetched.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "audit" / "2026-11-14-bc867bff" / "captures.json"

CLUB_TRI = {"Denver Nuggets": "DEN", "Cleveland Cavaliers": "CLE", "Minnesota Timberwolves": "MIN"}
SIT_OUT = ("Out", "Doubtful")            # will not / probably will not play
SIT_GAME = ("Questionable", "Probable")  # the game-time decision bucket


def _doc() -> dict:
    return json.loads(CAPTURE.read_text())["documents"]


def meta() -> dict:
    raw = json.loads(CAPTURE.read_text())
    return {"session": raw["session"], "captured_utc": raw["captured_utc"], "method": raw["method"]}


# --------------------------------------------------------------------------- latest report
def latest_rows() -> list[dict]:
    """The 50 designation rows of the 1:30 PM ET release, verbatim."""
    return _doc()["injury_report"]["rows"]


def latest_not_submitted() -> list[dict]:
    return _doc()["injury_report"]["not_yet_submitted"]


def pdf_url() -> str:
    return _doc()["injury_report"]["url"]


def notes() -> list[str]:
    return _doc()["injury_report"]["transcription_notes"]


def blocked() -> list[dict]:
    return _doc()["still_blocked"]


# --------------------------------------------------------------------------- delta vs the AM release
def delta_vs_morning(morning: list[tuple]) -> dict:
    """Compare the afternoon release with ``official.INJURIES`` (the 04:30 AM transcription).

    ``morning`` rows are ``(date, time, matchup, team, player, status, reason, attrib)``.
    Returns added rows, changed statuses and rows that disappeared, all recounted rather than
    remembered, so the published delta is a property of the two files and not of this docstring.
    """
    am = {str(r[4]).lower(): r for r in morning}
    pm = {str(r["player"]).lower(): r for r in latest_rows()}
    added = [pm[k] for k in pm if k not in am]
    changed = [{"player": pm[k]["player"], "team": pm[k]["team"], "matchup": pm[k]["matchup"],
                "was": str(am[k][5]), "now": pm[k]["status"], "source_url": pdf_url()}
               for k in pm if k in am and str(am[k][5]) != pm[k]["status"]]
    gone = [am[k] for k in am if k not in pm]
    return {"added": added, "changed": changed, "gone": gone,
            "n_am": len(morning), "n_pm": len(pm)}


# --------------------------------------------------------------------------- rotation + production
def rotation() -> list[dict]:
    """Official season averages for the three captured clubs, re-ordered by minutes.

    The stats page returns its rows sorted by per-game points; the club's *rotation* is a minutes
    question, so the block is re-sorted here and the published table says which ordering it uses.
    ``min_share`` is the player's minutes per game over the minutes of the eight players captured
    for that club — a share of the captured block, not of the club's full roster, and labelled so.
    """
    rows = _doc()["player_rotation"]["rows"]
    status = {str(r["player"]).lower(): r for r in latest_rows()}

    def norm(name: str) -> str:
        parts = [x.strip() for x in name.split(",")]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}"
        if len(parts) >= 3:
            return f"{parts[1]} {parts[0]} {' '.join(parts[2:])}"
        return name

    st = {norm(k): v for k, v in status.items()}
    by_club: dict[str, list[dict]] = {}
    for r in rows:
        by_club.setdefault(r["team"], []).append(r)
    out = []
    for club, blk in sorted(by_club.items()):
        blk = sorted(blk, key=lambda r: -r["mpg"])
        tot_min = sum(r["mpg"] for r in blk)
        for r in blk:
            d = st.get(str(r["player"]).lower())
            r = dict(r)
            r["min_rank_club"] = blk.index(r) + 1
            r["status"] = d["status"] if d else None
            r["reason"] = d["reason"] if d else None
            r["min_share"] = round(100.0 * r["mpg"] / tot_min, 1) if tot_min else None
            out.append(r)
    return out


def production_at_risk(teams: dict) -> list[dict]:
    """One row per captured club: what the report takes out of the rotation, in points.

    ``ppg_at_risk`` is the sum of the official per-game points of the rotation players whose
    status is Out or Doubtful; ``pct_of_club_ppg`` divides it by the club's own season PF/G from
    the official standings-derived team table the site already publishes. No distribution, no
    model, no assumed replacement value — an addition, and a ratio.
    """
    rot = rotation()
    by_club: dict[str, list[dict]] = {}
    for r in rot:
        by_club.setdefault(r["team"], []).append(r)
    out = []
    for club, blk in sorted(by_club.items()):
        tri = CLUB_TRI[club]
        t = teams.get(tri)
        pf = getattr(t, "pf", None) if t is not None else None
        sit = [r for r in blk if r["status"] in SIT_OUT]
        game = [r for r in blk if r["status"] in SIT_GAME]
        av = [r for r in blk if r["status"] not in SIT_OUT + SIT_GAME]
        ppg_sit = round(sum(r["ppg"] for r in sit), 1)
        ppg_game = round(sum(r["ppg"] for r in game), 1)
        out.append({
            "club": club, "tricode": tri, "n_captured": len(blk),
            "n_out_doubtful": len(sit), "n_game_status": len(game),
            "names_sitting": ", ".join(r["player"] for r in sit) or None,
            "names_game_time": ", ".join(f"{r['player']} ({r['status']})" for r in game) or None,
            "mpg_vacated": round(sum(r["mpg"] for r in sit), 1),
            "share_of_captured_minutes": round(100.0 * sum(r["mpg"] for r in sit) / sum(r["mpg"] for r in blk), 1),
            "ppg_at_risk": ppg_sit if sit else 0.0,
            "pct_of_club_ppg": round(100.0 * ppg_sit / pf, 1) if pf and sit else None,
            "ppg_game_time_bucket": ppg_game if game else 0.0,
            "pct_game_time_of_club_ppg": round(100.0 * ppg_game / pf, 1) if pf and game else None,
            "next_man_up": (max(av, key=lambda r: r["mpg"])["player"] + f" ({max(av, key=lambda r: r['mpg'])['mpg']} mpg)"
                            if av else None),
            "club_pf": pf,
            "src": pdf_url(),
            "src_stats": r_src(club),
        })
    return out


def r_src(club: str) -> str:
    """The official per-club stats page a rotation row came from."""
    from .official import NAMES
    tid = {"DEN": "1610612743", "CLE": "1610612739", "MIN": "1610612750"}
    _ = NAMES
    return f"https://www.nba.com/stats/players/traditional?TeamID={tid[CLUB_TRI[club]]}"


def total_line_shift(n_ppg_pct: float | None, base_total: float) -> float | None:
    """A reading aid, not a model output: half of a scoring deficit shows up in the total.

    If one club loses x% of its season scoring rate, the arithmetic midpoint of the two-club total
    moves by ``base_total * x / 200`` points. The factor of two is because a total is two clubs,
    and the league-mean total is taken from the site's own published baseline. It is published so a
    reader can see the size of the effect, with the explicit warning that a season-average shift is
    not a projection of one game's pace, and that no stake can be built on it.
    """
    if n_ppg_pct is None or not base_total:
        return None
    return round(base_total * n_ppg_pct / 200.0, 2)


# --------------------------------------------------------------------------- live re-verification
def club_records() -> dict:
    return _doc()["records_strip"]["records"]


def club_records_url() -> str:
    return _doc()["records_strip"]["url"]


def slate_reread() -> list[list]:
    return _doc()["slate_reread"]["games"]


def slate_url() -> str:
    return _doc()["slate_reread"]["url"]


def checks_summary() -> str:
    """The verifier's own tally, read out of the file it wrote (never retyped)."""
    txt = (ROOT / "audit/2026-11-14-bc867bff/checker_run.txt")
    if not txt.exists():
        return "verify_captures.py has not been run in this checkout"
    tail = [ln for ln in txt.read_text().splitlines() if "checks:" in ln]
    return tail[-1].strip() if tail else "no summary line"


def n_checks() -> tuple[int, int, int]:
    txt = (ROOT / "audit/2026-11-14-bc867bff/checker_run.txt")
    if not txt.exists():
        return (0, 0, 0)
    body = txt.read_text()
    return (body.count("[PASS]"), body.count("[FAIL]"), body.count("[INFO]"))
