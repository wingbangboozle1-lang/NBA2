"""Archive the **bytes** of every official injury report this repository knows about.

Why a second ingester, instead of editing ``nba2/v4/injury_ingest.py``
---------------------------------------------------------------------
``nba2/v4/injury_ingest.py`` archives exactly the releases listed in
``nba2/v4/injury_renderings.py`` — two of them, the two that were transcribed by hand. The
brief asks for **every** injury PDF, and the repository cites sixteen distinct releases
(transcripts, cross-references inside other captures, and PDFs already sitting in
``data/raw/pdf/`` that no inventory had ever listed). Editing v4's file scope would have
meant changing another session's module, so this ingester is additive: it archives the union
and writes its own manifest. It shares v4's contract exactly — never invent a byte count,
never invent a hash, record every attempt, and report drift if an official file's bytes
change after publication.

It runs from a GitHub-hosted runner, where ``ak-static.cms.nba.com`` is reachable (measured:
HTTP 200 in ``data/raw/egress_probe.json``). From this workspace the same request is
TLS-reset, which is why ``--dry-run`` exists and is what a build uses.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from . import inventory as INV
from .common import ROOT, V6

MANIFEST = V6 / "injury_binary_manifest.json"

UA = {"User-Agent": "NBA2-research-desk/1.0 (repository ingestion)",
      "Accept": "application/pdf,*/*", "Referer": "https://official.nba.com/"}


def fetch(url: str, timeout: int = 30) -> tuple[bytes | None, str]:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            blob = resp.read()
        if not blob.startswith(b"%PDF"):
            return None, f"answered but the body is not a PDF ({len(blob)} bytes)"
        return blob, "ok"
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001 - every failure is recorded, none swallowed
        return None, f"{type(e).__name__}: {e}"


def archive(write_files: bool = True) -> dict:
    INV.PDF_DIR.mkdir(parents=True, exist_ok=True)
    V6.mkdir(parents=True, exist_ok=True)
    entries, stored, already = [], 0, 0
    for rel in INV.injury_releases():
        url = rel["url"]
        name = rel["filename"]
        path = INV.PDF_DIR / name
        attempted = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        entry = {"url": url, "revision_et": rel["stamp_et"], "date": rel["date"],
                 "attempted_at_utc": attempted, "stored_path": None, "bytes": None,
                 "sha256": None, "outcome": "unreachable", "detail": None, "drift": None,
                 "was_already_committed": rel["bytes_stored"]}

        if rel["bytes_stored"]:
            # Already in the repository. Re-fetch only to detect drift, never to overwrite
            # a committed official file with a different one.
            blob, why = fetch(url)
            if blob is None:
                entry.update({"outcome": "already_committed_not_rechecked",
                              "detail": f"committed copy kept; re-check failed: {why}",
                              "bytes": rel["pdf_bytes"], "sha256": rel["pdf_sha256"],
                              "stored_path": rel["pdf_path"]})
                already += 1
            else:
                digest = hashlib.sha256(blob).hexdigest()
                entry.update({"bytes": rel["pdf_bytes"], "sha256": rel["pdf_sha256"],
                              "stored_path": rel["pdf_path"],
                              "outcome": "already_committed",
                              "detail": "committed bytes verified against the official file"})
                if digest != rel["pdf_sha256"]:
                    entry["drift"] = {"official_sha256_now": digest,
                                      "committed_sha256": rel["pdf_sha256"],
                                      "note": "the official file changed after it was archived"}
                already += 1
            entries.append(entry)
            print(f"[pdf] {rel['stamp_et']}: {entry['outcome']}")
            continue

        blob, why = fetch(url)
        entry["detail"] = why
        if blob is not None:
            digest = hashlib.sha256(blob).hexdigest()
            if write_files:
                path.write_bytes(blob)
                txt = path.with_suffix(".txt")
                if not txt.exists():
                    txt.write_text("", encoding="utf-8")
            entry.update({"stored_path": str(path.relative_to(ROOT)), "bytes": len(blob),
                          "sha256": digest, "outcome": "stored"})
            stored += 1
        entries.append(entry)
        print(f"[pdf] {rel['stamp_et']}: {entry['outcome']} — {entry['detail']}")

    doc = {
        "schema": "nba2.v6.injury-binary-manifest.v1",
        "session": "arena/f5ac4e74-nba2",
        "attempted_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "runner": "nba2/v6/injury_backfill.py (called from .github/workflows/refresh.yml)",
        "n_releases": len(entries),
        "n_stored": stored,
        "n_already_committed": already,
        "flag": "F-V4-01 / F-F5-03",
        "entries": entries,
        "note": ("Superset of nba2/v4/injury_ingest.py: every release cited anywhere under "
                 "data/, plus every PDF already in data/raw/pdf/. A release the league has "
                 "taken off the CDN is recorded as unreachable with the HTTP status — the "
                 "gap is the evidence, and no substitute file is ever written."),
    }
    MANIFEST.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"[pdf] {stored} newly stored, {already} already committed, "
          f"of {len(entries)} releases -> {MANIFEST.relative_to(ROOT)}")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="never fetch and never write; print the release list only")
    ap.add_argument("--no-write", action="store_true",
                    help="fetch and report, but do not write PDF bytes")
    a = ap.parse_args(argv)
    if a.dry_run:
        rel = INV.injury_releases()
        for r in rel:
            print(f"{r['stamp_et']:<16} bytes={'yes' if r['bytes_stored'] else 'no ':>3}  "
                  f"rows={r['transcript_rows']}  {r['url']}")
        print(f"{len(rel)} releases in the inventory")
        return 0
    doc = archive(write_files=not a.no_write)
    if doc["n_stored"] + doc["n_already_committed"] == 0:
        print("::error title=injury PDFs unreachable::no official injury PDF could be "
              "fetched from this runner; the manifest records every attempt")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
