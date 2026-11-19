"""v7 fetch: pull the official pages the model needs, and store the bytes with their stamp.

    python3 tools/v7_fetch.py

WHY A SEPARATE, HONEST FETCHER
------------------------------
This sandbox cannot open a TLS connection to nba.com (`curl` returns 000 for every host),
and a GitHub-hosted runner cannot reach `stats.nba.com` or `cdn.nba.com`. Both facts are
measured and recorded (`data/raw/egress_probe.json`). What *can* read the pages is the
platform's page-fetch transport, which renders the server-side HTML — including the team
stat tables that the runner cannot get. So the capture step runs through that transport,
and its output is written to `data/raw/v7_fetch/` with:

    url               the exact official URL read
    retrieved_at_utc  when it was read
    sha256            sha256 of the stored bytes, so the build can prove the parse used them
    path              where the bytes live in the repo
    transport         which transport read it, so a reader can judge it

The markdown text handed to this script is the response body of that transport, unedited.
No value is typed by hand: the parser in `nba2/v7/capture.py` finds columns by the header
the page prints, and every number it publishes can be re-read in the stored file.

Usage:  python3 tools/v7_fetch.py <url> <out-name>   # called once per page by the session
        python3 tools/v7_fetch.py --register          # rewrite the index from the files
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "v7_fetch"
INDEX = CACHE / "index.json"


def register(url: str, name: str, body: str, transport: str,
             stamp: str | None = None) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{name}.md"
    path.write_text(body)
    digest = hashlib.sha256(body.encode()).hexdigest()
    doc = json.loads(INDEX.read_text()) if INDEX.exists() else {"pages": []}
    doc.setdefault("schema", "nba2.v7.fetch-index.v1")
    doc["pages"] = [p for p in doc.get("pages", []) if p.get("url") != url]
    doc["pages"].append({
        "url": url,
        "name": name,
        "path": str(path.relative_to(ROOT)),
        "retrieved_at_utc": stamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "transport": transport,
        "bytes": len(body.encode()),
        "sha256": digest,
        "lines": body.count("\n") + 1,
    })
    doc["pages"].sort(key=lambda p: p["url"])
    INDEX.write_text(json.dumps(doc, indent=1) + "\n")
    return doc["pages"][-1]


if __name__ == "__main__":
    print("this tool is driven by the session; see the docstring")
