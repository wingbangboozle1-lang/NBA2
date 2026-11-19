"""Shared paths, escaping and the one provenance rule for the v7 slate-origination layer."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
V7 = DATA / "v7"
SITE = ROOT / "site"
CACHE = RAW / "v7_fetch"

OFFICIAL_HOSTS = ("nba.com", "ak-static.cms.nba.com", "cdn.nba.com",
                  "official.nba.com", "statsdmz.nba.com")


def esc(x) -> str:
    return "" if x is None else html.escape(str(x), quote=True)


def load(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return default


def dump(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=False) + "\n")
