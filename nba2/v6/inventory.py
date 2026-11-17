"""The official-endpoint and official-document inventory the v6 pages are built from.

Two rules, both enforced by :mod:`nba2.v6.check`:

* **Nothing is fetched.** Every entry comes from a file already committed under ``data/``.
  This session's workspace cannot reach ``nba.com`` (the TLS handshake is reset), so any
  value this module produced by reading the network would be unverifiable — and this
  repository's one rule is that an unverifiable value is a blank, not a number.
* **Every entry names the official document it came from.** A release with no URL is not an
  entry; it is an error.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .common import DATA, RAW, ROOT, V6, maybe_load, load

INJURY_URL_RE = re.compile(
    r"https://ak-static\.cms\.nba\.com/referee/injury/Injury-Report_\d{4}-\d{2}-\d{2}_\d{2}_\d{2}(AM|PM)\.pdf")
FNAME_STAMP_RE = re.compile(r"^Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)$")

PDF_DIR = RAW / "pdf"
BINARY_MANIFEST = DATA / "v4" / "injury" / "binary_manifest.json"
V4_RELEASES = DATA / "v4" / "injury" / "releases.json"
EGRESS_PROBE = RAW / "egress_probe.json"
REFRESH_VERDICT = RAW / "refresh_verdict.json"
INJURY_INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"

SKIP_DIRS = {"node_modules", ".git", "__pycache__"}


# --------------------------------------------------------------------- helpers
def _iter_data_json() -> list[Path]:
    out = []
    for p in sorted(DATA.rglob("*.json")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        out.append(p)
    return out


def _stamp_from_url(url: str) -> tuple[str, str] | None:
    """(date, 'hh:mm AM/PM ET') parsed out of an official injury-report filename."""
    name = url.rsplit("/", 1)[-1]
    m = FNAME_STAMP_RE.match(name[:-4] if name.endswith(".pdf") else name)
    if not m:
        return None
    d, hh, mm, ap = m.groups()
    return d, f"{hh}:{mm} {ap} ET"


def _sort_key(row: dict) -> tuple:
    return (row.get("date") or "", row.get("stamp_et") or "")


# ------------------------------------------------------- K-03: injury releases
def injury_releases() -> list[dict]:
    """One row per official injury release this repository knows about.

    A release is "known" if any committed JSON cites its official URL **or** its PDF sits in
    ``data/raw/pdf/``. Both halves are covered, because the brief asks for *every* report:
    the two v4 releases that were transcribed by hand and the five that only ever reached
    the repository as archived bytes or as a citation inside another document.
    """
    by_url: dict[str, dict] = {}

    def entry(url: str) -> dict:
        row = by_url.get(url)
        if row is None:
            date, stamp = _stamp_from_url(url) or (None, None)
            row = by_url[url] = {
                "url": url,
                "filename": url.rsplit("/", 1)[-1],
                "date": date,
                "stamp_et": stamp,
                "cited_in": [],
                "transcripts": [],
                "transcript_rows": None,
                "text_sha256": None,
                "retrieved_at_utc": None,
                "index_checked_utc": None,
                "revision_time_et": None,
                "method": None,
                "bytes_stored": False,
                "pdf_path": None,
                "pdf_bytes": None,
                "pdf_sha256": None,
                "text_extracted_path": None,
                "manifest_outcome": None,
                "manifest_detail": None,
            }
        return row

    # ---- 1. every URL cited anywhere under data/
    for p in _iter_data_json():
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        if "Injury-Report_" not in text:
            continue
        for m in INJURY_URL_RE.finditer(text):
            entry(m.group(0))["cited_in"].append(str(p.relative_to(ROOT)))

    # ---- 2. every PDF / extracted-text pair already archived
    for pdf in sorted(PDF_DIR.glob("Injury-Report_*.pdf")):
        m = FNAME_STAMP_RE.match(pdf.stem)
        if not m:
            continue
        d, hh, mm, ap = m.groups()
        url = (f"https://ak-static.cms.nba.com/referee/injury/"
               f"Injury-Report_{d}_{hh}_{mm}{ap}.pdf")
        row = entry(url)
        row["bytes_stored"] = True
        row["pdf_path"] = str(pdf.relative_to(ROOT))
        row["pdf_bytes"] = pdf.stat().st_size
        row["pdf_sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
        txt = pdf.with_suffix(".txt")
        if txt.exists():
            row["text_extracted_path"] = str(txt.relative_to(ROOT))

    # ---- 3. v4's own transcript metadata (stamps, retrieval times, text hashes)
    v4 = maybe_load(V4_RELEASES)
    if v4:
        for rel in v4.get("ledger", {}).get("releases", []):
            row = entry(rel["url"])
            row["transcripts"].append(str(V4_RELEASES.relative_to(ROOT)))
            row["transcript_rows"] = rel.get("rows")
            row["text_sha256"] = rel.get("text_sha256")
            row["retrieved_at_utc"] = rel.get("retrieved_at_utc")
            row["index_checked_utc"] = rel.get("index_checked_utc")
            row["revision_time_et"] = rel.get("revision_time_et")
            row["method"] = rel.get("method")

    # ---- 4. every other transcript file: attach rows / retrieval / method
    for p in _iter_data_json():
        if not (p.name.startswith("injury_report_") or p.name.startswith("injury_transcript_")
                or "injury_delta_" in p.name):
            continue
        try:
            doc = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        url = (doc.get("provenance") or {}).get("url")
        if not url or not INJURY_URL_RE.match(url):
            continue
        row = entry(url)
        rel = str(p.relative_to(ROOT))
        if rel not in row["transcripts"]:
            row["transcripts"].append(rel)
        for key in ("records", "rows"):
            v = doc.get(key)
            if isinstance(v, list) and row["transcript_rows"] in (None, 0):
                row["transcript_rows"] = len(v)
                break
        if not row["retrieved_at_utc"] and doc.get("retrieved_at_utc"):
            row["retrieved_at_utc"] = doc["retrieved_at_utc"]
        if not row["index_checked_utc"] and doc.get("index_checked_utc"):
            row["index_checked_utc"] = doc["index_checked_utc"]
        if not row["revision_time_et"] and doc.get("revision_time_et"):
            row["revision_time_et"] = doc["revision_time_et"]
        if not row["method"] and doc.get("retrieval_method"):
            row["method"] = doc["retrieval_method"]
        if not row["text_sha256"] and doc.get("content_sha256"):
            row["text_sha256"] = doc["content_sha256"]

    # ---- 5. the byte-level manifest: did the runner succeed, and what did it record?
    man = maybe_load(BINARY_MANIFEST)
    if man:
        for e in man.get("entries", []):
            row = entry(e["url"])
            row["manifest_outcome"] = e.get("outcome")
            row["manifest_detail"] = e.get("detail")
            if e.get("sha256"):
                row["manifest_sha256"] = e["sha256"]
            if e.get("outcome") == "stored" and e.get("sha256") and row["pdf_sha256"]:
                row["sha256_matches_manifest"] = (e["sha256"] == row["pdf_sha256"])

    rows = sorted(by_url.values(), key=_sort_key)
    for r in rows:
        r["cited_in"] = sorted(set(r["cited_in"]))
        r["transcripts"] = sorted(set(r["transcripts"]))
        r["text_sha256_matches_extracted"] = None
        if r["text_extracted_path"] and r["text_sha256"]:
            tp = ROOT / r["text_extracted_path"]
            digest = hashlib.sha256(tp.read_bytes()).hexdigest()
            r["text_sha256_matches_extracted"] = (digest == r["text_sha256"])
    return rows


# ------------------------------------------------- K-09: endpoint reachability
def endpoints() -> dict:
    """Official-endpoint reachability, measured from a runner, not assumed."""
    probe = maybe_load(EGRESS_PROBE) or {}
    rows = []
    for r in probe.get("rows", []):
        rows.append({
            "name": r.get("name"),
            "url": r.get("url"),
            "http_status": r.get("http_status"),
            "bytes": r.get("bytes"),
            "elapsed_ms": r.get("elapsed_ms"),
            "ok": r.get("ok"),
            "error": r.get("error"),
            "is_pdf": r.get("is_pdf"),
        })
    return {
        "schema": "nba2.v6.endpoints.v1",
        "probed_at_utc": probe.get("probed_at_utc"),
        "runner": probe.get("runner"),
        "source_file": "data/raw/egress_probe.json",
        "source_url": "https://github.com/wingbangboozle1-lang/NBA2/blob/main/.github/workflows/probe-egress.yml",
        "rows": rows,
        "summary": probe.get("summary", {}),
    }


def refresh_verdict() -> dict | None:
    return maybe_load(REFRESH_VERDICT)
