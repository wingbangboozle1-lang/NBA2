"""Provenance primitives: every table row on the site is built here so that a missing
source is a crash, not an oversight.

Row contract
------------
`make_row()` raises if a row is created without a source, or if a value is present while
its source is class BLOCKED/OFFICIAL_UNREACHABLE. Unverified values must be passed as
`None` and the row is then rendered blank + flagged. This is the machine-enforced version
of "if a value can't be confirmed, leave it blank and flag it".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


# --------------------------------------------------------------------------- sources
class Src:
    OFFICIAL = "official"            # nba.com / ak-static.cms.nba.com / cdn.nba.com
    THIRD_PARTY = "third_party"      # reputable aggregator, not the league
    DERIVED = "derived"              # computed by this repo from a snapshot
    BLOCKED = "blocked"              # we know we need it; we do not have it

    _LABEL = {
        OFFICIAL: "Official NBA.com / NBA CDN",
        THIRD_PARTY: "Third-party (not NBA-official)",
        DERIVED: "Derived in-repo from a verified snapshot",
        BLOCKED: "Unavailable — blocked / not connected",
    }

    _BADGE = {OFFICIAL: "verified", THIRD_PARTY: "warning", DERIVED: "derived", BLOCKED: "unverified"}

    def __init__(self, name: str, url: str, cls: str, note: str = "") -> None:
        self.name, self.url, self.cls, self.note = name, url, cls, note

    @property
    def label(self) -> str:
        return self._LABEL[self.cls]

    @property
    def badge(self) -> str:
        return self._BADGE[self.cls]

    def as_dict(self) -> dict:
        return {"name": self.name, "url": self.url, "class": self.cls,
                "class_label": self.label, "note": self.note}


SOURCES: dict[str, Src] = {}


def register_source(key: str, name: str, url: str, cls: str, note: str = "") -> Src:
    src = Src(name, url, cls, note)
    SOURCES[key] = src
    return src


register_source("nba_schedule", "NBA.com Schedule (official)", "https://www.nba.com/schedule", Src.OFFICIAL,
                "Week 4 / Week 5 sections; game IDs, times ET, arenas, broadcasts. 2026-11-13 capture 22:33 UTC; re-verified 2026-11-14 ~01:05 UTC with 0 field mismatches across the 31 carried-forward games.")
register_source("nba_games", "NBA.com Games & Scores (official)", "https://www.nba.com/games", Src.OFFICIAL,
                "Game cards with W-L and Emirates NBA Cup group records. Retrieved 2026-11-13 22:26 UTC.")
register_source("nba_game_card", "NBA.com Game Preview (official)", "https://www.nba.com/game/den-vs-nop-0022600231",
                Src.OFFICIAL, "Cross-check of Nov 13-15 win-loss records.")
register_source("nba_injury_pdf", "NBA Official Injury Report 11/13 19:30 ET (official)",
                "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf", Src.OFFICIAL,
                "Freshest release at build time (supersedes the 16:15 capture, which stays committed). Columns: Game Date, Game Time, Matchup, Team, Player, Status, Reason. 122 rows transcribed.")
register_source("bref_standings", "Basketball-Reference 2026-27 Standings", "https://www.basketball-reference.com/leagues/NBA_2027_standings.html",
                Src.THIRD_PARTY, "Conference + Expanded standings. W-L cross-checked against NBA.com for 28/30 teams in the original capture (TOR/WAS not visible there); re-read 2026-11-14: all 30 W-L identical (ratings_recheck_2026-11-14.json).")
register_source("nba_stats_blocked", "stats.nba.com JSON endpoints", "https://stats.nba.com/stats/leaguestandingsv3",
                Src.BLOCKED, "Unreachable from this environment; nba.com/stats tables are client-rendered.")
register_source("odds_blocked", "Market odds feed", "", Src.BLOCKED,
                "No licensed odds source connected. NBA.com renders odds client-side only; picks.nba.com exposes no lines.")
register_source("derived_ratings", "Derived: nba2.models.ratings", "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/ratings.py",
                Src.DERIVED, "Calibration + shrinkage computed from the verified snapshot at build time.")
register_source("derived_lines", "Derived: nba2.models.lines", "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/lines.py",
                Src.DERIVED, "Lines are arithmetic on the calibrated ratings; reproduce with `python -m nba2.pipeline.build_site_data`.")
register_source("derived_corr", "Derived: nba2.models.correlation", "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/models/correlation.py",
                Src.DERIVED, "Empirical correlation where inputs exist; sensitivity band otherwise.")
register_source("git_repo", "This repository (git history)", "https://github.com/wingbangboozle1-lang/NBA2", Src.OFFICIAL,
                "Repo review facts: commit list, file tree.")
register_source("source_register", "nba2/provenance.py SOURCES registry",
                "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/provenance.py", Src.DERIVED,
                "Meta-table: which sources were used, and which were attempted and unreachable.")
register_source("coordination", "COORDINATION.md", "https://github.com/wingbangboozle1-lang/NBA2/blob/main/COORDINATION.md",
                Src.DERIVED, "Session claims, conflict log, irregularity findings.")


# --------------------------------------------------------------------------- flags
@dataclass
class Flag:
    id: str
    severity: str          # info | low | medium | high
    area: str
    statement: str
    source_url: str
    action: str

    def as_dict(self) -> dict:
        return {"id": self.id, "severity": self.severity, "area": self.area,
                "statement": self.statement, "source_url": self.source_url, "action": self.action}


_FLAGS: dict[str, Flag] = {}


def flag(id: str, severity: str, area: str, statement: str, source_url: str, action: str) -> Flag:  # noqa: A002
    """Register a review flag. Idempotent: re-registering an id overwrites with the latest text."""
    f = Flag(id, severity, area, statement, source_url, action)
    if id in _FLAGS:
        _FLAGS[id] = f
    else:
        _FLAGS[id] = f
    return f


def all_flags() -> list[Flag]:
    return [_FLAGS[k] for k in sorted(_FLAGS)]


# --------------------------------------------------------------------------- rows
@dataclass
class Row:
    """One table row. `values` may contain None -> rendered blank + flagged."""

    key: str
    values: dict[str, Any]
    source_key: str
    note: str = ""
    flags: list[str] = field(default_factory=list)

    @property
    def source(self) -> Src:
        return SOURCES[self.source_key]

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "values": self.values,
            "source": self.source.as_dict(),
            "note": self.note,
            "flags": self.flags,
            "verified": self.source.cls == Src.OFFICIAL,
        }


_MISSING = object()

# Fields that may legally carry text on a BLOCKED row: they describe the block itself and
# are not data. Any other value on a blocked source is a hard error.
BLOCKED_ALLOWED_FIELDS = frozenset({
    # fields that describe the block itself, or identify the row:
    "status", "missing", "note", "market", "player", "team", "name", "url", "cls",
    "usable", "key", "reason", "verdict", "disposition", "attribution", "severity",
    "area", "statement", "action", "source", "id",
})


def make_row(key: str, source_key: str, flag_ids: Iterable[str] = (), /, **values: Any) -> Row:
    """Build one published row. `key`, `source_key` and `flag_ids` are positional-only so that
    `note`, `key` and `source_key` can be used as *column names* — three names this table set
    genuinely needs, and which a keyword signature would silently swallow (it did)."""
    if source_key not in SOURCES:
        raise KeyError(f"row {key!r}: unknown source key {source_key!r}")
    src = SOURCES[source_key]
    flag_ids = list(flag_ids)
    for name, value in values.items():
        if isinstance(value, str) and not value.strip():
            # an empty string looks like a value but carries nothing: force it to blank so the
            # "every blank must be flagged" rule sees it (and the table renders the blank marker)
            values[name] = None
            value = None
        if value is _MISSING:
            raise ValueError(f"row {key!r} field {name!r}: use None for unknown, never a placeholder")
        if value is not None and src.cls == Src.BLOCKED and name not in BLOCKED_ALLOWED_FIELDS:
            raise ValueError(
                f"row {key!r} field {name!r} carries a value but its source is BLOCKED. "
                "Values with no source must be None (blank) and flagged."
            )
        if value is not None and src.cls in (Src.THIRD_PARTY, Src.BLOCKED) and not flag_ids:
            raise ValueError(
                f"row {key!r} field {name!r}: non-official source requires at least one flag id"
            )
        if value is None and not flag_ids:
            raise ValueError(
                f"row {key!r} field {name!r} is blank with no flag: a blank cell must say why. "
                "Pass a flag id that explains the missing value."
            )
    return Row(key=key, values=values, source_key=source_key, flags=flag_ids)


def table(rows: list[Row], columns: list[tuple[str, str]], title: str, blurb: str = "",
          source_note: str = "") -> dict:
    """Serialise a table for the site renderer.

    Refuses to publish a column that no row carries: a header with nothing under it is how a
    swallowed keyword argument becomes an invisible data loss instead of a build failure.
    """
    if not columns:
        raise ValueError(f"table {title!r}: no columns")
    for key, label in columns:
        missing = [r.key for r in rows if key not in r.values]
        if missing:
            raise ValueError(
                f"table {title!r}: column {key!r} ({label!r}) is absent from "
                f"{len(missing)} row(s), e.g. {missing[:3]} — every declared column must be "
                f"set on every row (use None for 'no source'), and reserved argument names "
                f"cannot be passed as keywords")
    return {
        "title": title,
        "blurb": blurb,
        "source_note": source_note,
        "columns": [{"key": k, "label": lbl} for k, lbl in columns],
        "rows": [r.as_dict() for r in rows],
        "sources": [SOURCES[r.source_key].as_dict() for r in rows],
    }
