"""Tamper-evidence and pre-registration audit (session arena/9fef54cf-nba2).

Read-only. Recomputes every stored hash in the repository with the hash rule
each file declares (or, where no rule is declared, with the candidate rules
tested here), and rebuilds a timeline from git history. Writes
audit/9fef54cf/prereg_audit.json. It never edits a frozen file, a sealed
ledger, or a published page.

Run from the repository root:  python3 audit/9fef54cf/prereg_audit.py
"""
import glob
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone

ROOT = os.getcwd()
REPO_URL = "https://github.com/wingbangboozle1-lang/NBA2"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


_MAIN_CACHE = {}


def on_main(sha):
    """True when `sha` is an ancestor of origin/main (the published branch)."""
    if sha not in _MAIN_CACHE:
        _MAIN_CACHE[sha] = subprocess.run(["git", "merge-base", "--is-ancestor", sha, "origin/main"],
                                          cwd=ROOT, capture_output=True).returncode == 0
    return _MAIN_CACHE[sha]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def history(path):
    """All commits that touched `path`, oldest first, with each version's content hash."""
    shas = git("log", "--all", "--full-history", "--reverse", "--format=%H", "--", path).split()
    rows = []
    for sha in shas:
        when = git("show", "-s", "--format=%cI", sha).strip()
        try:
            blob = subprocess.run(["git", "show", f"{sha}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout
            content = sha256_bytes(blob)
        except subprocess.CalledProcessError:
            content = None  # deleted in this commit
        rows.append({"commit": sha, "url": f"{REPO_URL}/commit/{sha}", "committed_at": when, "content_sha256": content, "on_main": on_main(sha)})
    versions = []
    for r in rows:
        if not versions or versions[-1] != r["content_sha256"]:
            versions.append(r["content_sha256"])
    return {"commits": len(rows), "distinct_versions": len(versions), "first": rows[0] if rows else None,
            "last": rows[-1] if rows else None, "history": rows}


def parse_iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def candidate_hashes(doc, raw, hash_key):
    body = {k: v for k, v in doc.items() if k != hash_key}
    body_no_frozen = {k: v for k, v in body.items() if k not in ("frozen_at_utc",)}
    return {
        "raw_file_bytes": sha256_bytes(raw),
        "canonical_body_excluding_hash_field": sha256_bytes(canon(body)),
        "canonical_full_doc_including_hash_field": sha256_bytes(canon(doc)),
        "canonical_body_excluding_hash_and_frozen_at": sha256_bytes(canon(body_no_frozen)),
    }


def declared_vs_commit(path, time_key, extra_keys):
    """Each committed version of `path`: its declared time field vs the commit that introduced it."""
    rows = []
    prev = None
    for sha in git("log", "--all", "--full-history", "--reverse", "--format=%H", "--", path).split():
        try:
            doc = json.loads(subprocess.run(["git", "show", f"{sha}:{path}"], cwd=ROOT,
                                            capture_output=True, check=True).stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue
        committed = parse_iso(git("show", "-s", "--format=%cI", sha).strip())
        declared = doc.get(time_key)
        snap = {k: doc.get(k) for k in extra_keys}
        if snap == prev:
            continue
        prev = snap
        dec = parse_iso(declared) if declared else None
        rows.append({"commit": sha, "url": f"{REPO_URL}/commit/{sha}", "committed_at": committed.isoformat(), "on_main": on_main(sha),
                     time_key: declared, **snap,
                     "declared_later_than_commit_minutes": round((dec - committed).total_seconds() / 60, 1) if dec else None})
    return rows


def audit_prereg_v2():
    manifest = json.load(open("data/v2/preregistration.json"))
    out = []
    for entry in manifest["files"]:
        path = entry["file"]
        raw = open(path, "rb").read()
        doc = json.loads(raw)
        stored = entry["prereg_hash"]
        cands = candidate_hashes(doc, raw, "prereg_hash")
        matched = [k for k, v in cands.items() if v == stored]
        hist = history(path)
        first_commit = parse_iso(hist["first"]["committed_at"]) if hist["first"] else None
        frozen = parse_iso(doc["frozen_at_utc"])
        out.append({
            "id": entry["id"], "file": path, "stored_hash": stored,
            "stored_hash_matches": matched or None,
            "candidates_tested": cands,
            "frozen_at_utc_claimed": doc["frozen_at_utc"],
            "first_commit": hist["first"], "commits": hist["commits"],
            "distinct_versions": hist["distinct_versions"],
            "frozen_claim_precedes_first_commit": (frozen <= first_commit) if first_commit else None,
            "hours_between_claim_and_first_commit": round((first_commit - frozen).total_seconds() / 3600, 2) if first_commit else None,
            "versions_by_commit": declared_vs_commit(path, "frozen_at_utc", ["frozen_at_utc", "frozen_by", "prereg_hash"]),
        })
    return {"manifest": "data/v2/preregistration.json", "files": out}


def audit_prereg_v3():
    out = []
    for path in sorted(glob.glob("data/v3/prereg/*.json")):
        raw = open(path, "rb").read()
        doc = json.loads(raw)
        stored = doc.get("sha256")
        cands = candidate_hashes(doc, raw, "sha256")
        matched = [k for k, v in cands.items() if v == stored]
        hist = history(path)
        reg = doc.get("registered_at_utc")
        first_commit = parse_iso(hist["first"]["committed_at"]) if hist["first"] else None
        # Content of the first committed version, for the change summary.
        first_doc = None
        if hist["first"]:
            first_doc = json.loads(subprocess.run(["git", "show", f"{hist['first']['commit']}:{path}"],
                                                  cwd=ROOT, capture_output=True, check=True).stdout)
        changed = sorted(k for k in set(doc) | set(first_doc or {})
                         if (first_doc or {}).get(k) != doc.get(k)) if first_doc else []
        out.append({
            "id": doc.get("id"), "name": doc.get("name"), "file": path,
            "stored_sha256": stored, "stored_hash_matches": matched or None,
            "candidates_tested": cands,
            "registered_at_utc_current": reg,
            "registered_by_current": doc.get("registered_by"),
            "window_current": doc.get("window"),
            "first_commit": hist["first"], "commits": hist["commits"],
            "distinct_versions": hist["distinct_versions"],
            "fields_changed_since_first_commit": changed,
            "first_version_registered_at_utc": (first_doc or {}).get("registered_at_utc"),
            "first_version_window": (first_doc or {}).get("window"),
            "first_version_sha256": (first_doc or {}).get("sha256"),
            "first_version_sha256_matches": (
                [k for k, v in candidate_hashes(first_doc, subprocess.run(
                    ["git", "show", f"{hist['first']['commit']}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout,
                    "sha256").items() if v == first_doc.get("sha256")] or None) if first_doc else None,
            "edited_after_first_commit": hist["distinct_versions"] > 1,
            "versions_by_commit": declared_vs_commit(path, "registered_at_utc", ["registered_at_utc", "registered_by", "window", "sha256"]),
        })
    return {"directory": "data/v3/prereg", "files": out}


def audit_sealed():
    out = []
    for path in sorted(glob.glob("data/raw/ledger/sealed-*.json")):
        doc = json.load(open(path))
        h = doc["header"]
        digest = sha256_bytes(canon(doc["predictions"]))
        hist = history(path)
        first_commit = parse_iso(hist["first"]["committed_at"]) if hist["first"] else None
        sealed = parse_iso(h["sealed_at_utc"])
        out.append({
            "file": path, "n_predictions": len(doc["predictions"]), "header_n_predictions": h["n_predictions"],
            "hash_rule": h["hash_rule"], "stored_sha256": h["sha256"], "recomputed_sha256": digest,
            "digest_matches": digest == h["sha256"], "sealed_at_utc": h["sealed_at_utc"],
            "first_commit": hist["first"], "commits": hist["commits"], "distinct_versions": hist["distinct_versions"],
            "minutes_sealed_before_first_commit": round((first_commit - sealed).total_seconds() / 60, 1) if first_commit else None,
            "game_dates": sorted({p["date"] for p in doc["predictions"]}),
        })
    return {"directory": "data/raw/ledger", "files": out}


def audit_published_before_tip():
    """For each sealed game: was the ledger's first commit earlier than the game's tip time (ET -> UTC)?"""
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    out = []
    for path in sorted(glob.glob("data/raw/ledger/sealed-*.json")):
        doc = json.load(open(path))
        hist = history(path)
        first_commit = parse_iso(hist["first"]["committed_at"])
        checked = before = 0
        late = []
        for p_ in doc["predictions"]:
            tip = datetime.strptime(f"{p_['date']} {p_['time_et']}", "%Y-%m-%d %H:%M").replace(tzinfo=et)
            checked += 1
            if first_commit < tip.astimezone(timezone.utc):
                before += 1
            else:
                late.append(p_["game_id"])
        out.append({"file": path, "games_checked": checked, "published_before_tip": before,
                    "published_after_tip_game_ids": late, "first_commit_utc": first_commit.isoformat()})
    return out


def audit_finals_timeline():
    out = {}
    for path in sorted(glob.glob("data/raw/finals_*.json")):
        hist = history(path)
        out[path] = {"first_commit": hist["first"]["committed_at"] if hist["first"] else None,
                     "first_commit_url": hist["first"]["url"] if hist["first"] else None}
    return out


def main():
    result = {
        "generated_by": "audit/9fef54cf/prereg_audit.py",
        "head": git("rev-parse", "HEAD").strip(),
        "origin_main": git("rev-parse", "origin/main").strip(),
        "origin_main_commits": int(git("rev-list", "--count", "origin/main").strip()),
        "clone_is_shallow": git("rev-parse", "--is-shallow-repository").strip() == "true",
        "prereg_v2": audit_prereg_v2(),
        "prereg_v3": audit_prereg_v3(),
        "sealed_ledgers": audit_sealed(),
        "finals_first_commits": audit_finals_timeline(),
        "published_before_tip": audit_published_before_tip(),
    }
    with open("audit/9fef54cf/prereg_audit.json", "w") as f:
        json.dump(result, f, indent=1, sort_keys=True)
        f.write("\n")
    print("v2 prereg:", [(x["id"], x["stored_hash_matches"]) for x in result["prereg_v2"]["files"]])
    print("v3 prereg:", [(x["file"].split("/")[-1][:12], x["stored_hash_matches"], x["distinct_versions"]) for x in result["prereg_v3"]["files"]])
    print("sealed:", [(x["file"].split("/")[-1], x["digest_matches"]) for x in result["sealed_ledgers"]["files"]])


if __name__ == "__main__":
    main()
