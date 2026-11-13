"""Injury -> rotation -> production module.

Hard rule: the official NBA injury report contains Game Date, Game Time, Matchup, Team,
Player, Status and Reason. It contains NO minutes, NO usage and NO production data. Any
numeric "impact" therefore cannot be produced from the official source, and this module
returns `None` for those fields rather than a plausible-looking estimate. What it *can*
produce, and does, is a verified structural impact: rotation-body counts, availability
risk tiers, and the effect on our line (which is: none applied, and that is disclosed).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .. import config

STATUS_WEIGHT = {          # availability probability implied by the report label itself
    "Out": 0.0,
    "Doubtful": 0.25,
    "Questionable": 0.55,
    "Probable": 0.85,
    "Available": 1.0,
    "NOT YET SUBMITTED": None,
}
STATUS_WEIGHT_SOURCE = (
    "status labels and their existence: official report. The numeric availability weights are "
    "OUR modelling convention for rotation-body counting and are NOT league-published "
    "probabilities - unratified, see PARAMS."
)


@dataclass
class InjuryRow:
    game_date: str
    time_et: str
    matchup: str
    team: str
    player: str
    status: str
    reason: str
    attribution: str
    p_play: float | None
    minutes_impact: float | None      # always None until player minutes data exists
    production_impact: float | None   # always None until player box-score data exists
    line_adjustment_pts: float | None # always None: we refuse to blind-adjust

    def as_dict(self) -> dict:
        return {
            "game_date": self.game_date, "time_et": self.time_et, "matchup": self.matchup,
            "team": self.team, "player": self.player, "status": self.status, "reason": self.reason,
            "attribution": self.attribution, "p_play": self.p_play,
            "minutes_impact": self.minutes_impact, "production_impact": self.production_impact,
            "line_adjustment_pts": self.line_adjustment_pts,
        }


TEAM_TO_TRI = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}


def load(path: Path) -> tuple[list[InjuryRow], dict]:
    raw = json.loads(Path(path).read_text())
    cols = raw["columns"]
    rows: list[InjuryRow] = []
    for rec in raw["records"]:
        d = dict(zip(cols, rec))
        status = d["status"]
        rows.append(InjuryRow(
            game_date=d["game_date"], time_et=d["time_et"], matchup=d["matchup"],
            team=d["team"], player=d["player"], status=status, reason=d["reason"],
            attribution=d["attribution"],
            p_play=STATUS_WEIGHT.get(status),
            minutes_impact=None, production_impact=None, line_adjustment_pts=None,
        ))
    return rows, raw


def by_team(rows: list[InjuryRow]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        tri = TEAM_TO_TRI.get(r.team)
        if tri is None:
            continue
        out.setdefault(tri, []).append(r.as_dict())
    return out


def rotation_index(rows: list[InjuryRow], min_rot: int = 8, max_rot: int = 10):
    """Structural rotation impact: how many report-listed bodies are removed from a team's
    available pool, plus the 'expected available' count using our own status weights.

    `expected_missing_bodies` is a *count*, not a points figure: it is defensible from the
    report alone. Anything finer needs minutes data.
    """
    per_team: dict[str, dict] = {}
    for r in rows:
        tri = TEAM_TO_TRI.get(r.team)
        if tri is None:
            continue
        d = per_team.setdefault(tri, {
            "team": r.team, "tricode": tri, "rows": 0, "out": 0, "doubtful": 0,
            "questionable": 0, "probable": 0, "available_listed": 0, "gleague_or_suspension": 0,
            "not_yet_submitted": 0, "expected_missing_bodies": 0.0, "games": set(),
        })
        d["rows"] += 1
        d["games"].add(f"{r.game_date} {r.matchup}")
        reason = (r.reason or "")
        if reason.startswith("G League") or reason.startswith("League Suspension") or reason == "Not With Team":
            d["gleague_or_suspension"] += 1
        if r.status == "Out":
            d["out"] += 1
            d["expected_missing_bodies"] += 1.0
        elif r.status == "Doubtful":
            d["doubtful"] += 1
            d["expected_missing_bodies"] += 1 - STATUS_WEIGHT["Doubtful"]
        elif r.status == "Questionable":
            d["questionable"] += 1
            d["expected_missing_bodies"] += 1 - STATUS_WEIGHT["Questionable"]
        elif r.status == "Probable":
            d["probable"] += 1
            d["expected_missing_bodies"] += 1 - STATUS_WEIGHT["Probable"]
        elif r.status == "Available":
            d["available_listed"] += 1
        elif r.status == "NOT YET SUBMITTED":
            d["not_yet_submitted"] += 1
    for d in per_team.values():
        d["games"] = sorted(d["games"])
        d["expected_missing_bodies"] = round(d["expected_missing_bodies"], 2)
        # two-sided risk band on the count: sqrt(sum p(1-p)) over the listed players
        var = 0.0
        for r in rows:
            if TEAM_TO_TRI.get(r.team) != d["tricode"]:
                continue
            p = STATUS_WEIGHT.get(r.status)
            if p is not None and 0 < p < 1:
                var += p * (1 - p)
        d["missing_body_sd"] = round(var ** 0.5, 2)
        d["rotation_floor"] = max_rot - int(d["expected_missing_bodies"] + 1.0 * (d["missing_body_sd"] or 0))
        d["rotation_floor"] = max(min_rot - 2, min(d["rotation_floor"], max_rot))
    return per_team


def risk_tier(d: dict) -> str:
    if d["out"] >= 3:
        return "SEVERE"
    if d["out"] >= 1 or d["expected_missing_bodies"] >= 1.5:
        return "MATERIAL"
    if d["rows"]:
        return "MINOR"
    return "NONE-REPORTED"


def leader_availability(rows: list[InjuryRow], leaders: list[dict]) -> list[dict]:
    """Join the report against the official per-game 'Season Leaders' card shown on NBA.com.

    This is a *coverage* check, not an availability guarantee: a leader missing from the
    report is listed as NOT-LISTED, which is not the same as active.
    """
    flagged = {(r.team, r.player) for r in rows if r.status in ("Out", "Doubtful")}
    partial = {(r.team, r.player) for r in rows if r.status in ("Questionable", "Probable", "Available")}
    out = []
    for lead in leaders:
        team = lead["team"]
        player = lead["leader_player"]
        key = (team, player)
        status = "NOT LISTED ON REPORT"
        for r in rows:
            if r.team == team and r.player.lower().startswith(player.split(",")[0].lower()):
                status = r.status
                break
        out.append({**lead, "report_status": status,
                    "impact_on_line": None,
                    "note": "No numeric impact: player-level production data unavailable."})
    return out
