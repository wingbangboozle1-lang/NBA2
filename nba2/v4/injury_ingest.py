"""Archive the injury PDF **bytes** from a runner that can reach the CDN, and record it.

Why this is a separate command
----------------------------
The build cannot download ``ak-static.cms.nba.com``: bash egress from the development
sandbox is TLS-reset, which is why every earlier session published "PDF not stored,
F-V4-01". A GitHub-hosted runner makes outbound HTTPS requests normally, so the archive can
be done there — once per scheduled run, and committed with the rest of the refresh.

Fail-closed, and honest about it
--------------------------------
This never invents a byte count or a hash. If every URL is unreachable it writes a manifest
saying so, with the error, the timestamp and the URL attempted, and exits non-zero so the
scheduled job's log shows the failure. If a PDF is fetched, the manifest records its byte
length and sha256, and the file is committed under ``data/raw/pdf/``; a re-run whose digest
differs from the committed file is reported as **drift**, because an official release whose
bytes changed after publication is a fact a reader needs to see.

Neither path touches a value that appears on the site: the manifest only says *whether the
bytes are stored*, which is the one thing F-V4-01 was about.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

from . import injury_renderings as RR

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "data" / "raw" / "pdf"
MANIFEST = ROOT / "data" / "v4" / "injury" / "binary_manifest.json"

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
    except Exception as e:  # noqa: BLE001 - every failure is recorded, none is swallowed
        return None, f"{type(e).__name__}: {e}"


def archive(write_files: bool = True) -> dict:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    ok = 0
    for r in RR.RENDERS:
        url = r["url"]
        name = url.rsplit("/", 1)[-1]
        blob, why = fetch(url)
        entry = {"url": url, "revision_et": r["revision_et"],
                 "attached_to_release": r["stamp_et"],
                 "attempted_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 "stored_path": None, "bytes": None, "sha256": None,
                 "outcome": "unreachable", "detail": why, "drift": None}
        if blob is not None:
            digest = hashlib.sha256(blob).hexdigest()
            path = PDF_DIR / name
            prev = None
            if path.exists():
                prev = hashlib.sha256(path.read_bytes()).hexdigest()
            if write_files:
                path.write_bytes(blob)
            entry.update({"stored_path": str(path.relative_to(ROOT)), "bytes": len(blob),
                          "sha256": digest, "outcome": "stored", "detail": why})
            if prev and prev != digest:
                entry["drift"] = {"previous_sha256": prev, "note":
                                  "the bytes of this release changed after publication"}
            ok += 1
        entries.append(entry)
        print(f"[pdf] {r['stamp_et']}: {entry['outcome']} — {entry['detail']}")

    doc = {
        "schema": "nba2.v4.injury-binary-manifest.v1",
        "attempted_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "runner": "nba2/v4/injury_ingest.py (called from .github/workflows/refresh.yml)",
        "n_releases": len(RR.RENDERS),
        "n_stored": ok,
        "flag": "F-V4-01",
        "entries": entries,
        "note": ("Closes the storage half of F-V4-01 when n_stored == n_releases. The build "
                 "never reads these bytes as data: the published rows come from the stored "
                 "rendering, and this manifest only states whether the original file is in the "
                 "repository."),
    }
    MANIFEST.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"[pdf] {ok}/{len(RR.RENDERS)} releases archived -> {MANIFEST.relative_to(ROOT)}")
    return doc


def main() -> int:
    doc = archive()
    if doc["n_stored"] == 0:
        print("::error title=injury PDFs unreachable::no official injury PDF could be "
              "fetched from this runner; the manifest records every attempt")
        return 3
    if doc["n_stored"] < doc["n_releases"]:
        print("::warning::some official injury PDFs could not be fetched; see the manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
