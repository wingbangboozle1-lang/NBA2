"""Validated status record for the scheduled v1 ingest and published v2 site.

The refresh workflow writes one immutable-per-run record to data/operations/ before
rebuilding the site. The v2 builder publishes that record as machine-readable JSON and
renders it on the dashboard. This status is operational evidence only: the current
refresh workflow does not update the v2 model's NBA inputs, market prices, or player logs.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / "data" / "operations" / "refresh_status.json"
REPOSITORY = "wingbangboozle1-lang/NBA2"
WORKFLOW_PATH = ".github/workflows/refresh.yml"
WORKFLOW_HISTORY_URL = f"https://github.com/{REPOSITORY}/actions/workflows/refresh.yml"
WORKFLOW_MAIN_URL = f"https://github.com/{REPOSITORY}/blob/main/{WORKFLOW_PATH}"
RUN_STATUS_VALUES = {"success", "failure", "cancelled"}
STEP_STATUS_VALUES = {"success", "failure", "cancelled", "skipped", "not-run", "unknown"}
RUN_ID_RE = re.compile(r"^[0-9]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

STEP_ENV = {
    "window_dates": "STEP_WINDOW_DATES",
    "injury_archive": "STEP_INJURY_ARCHIVE",
    "finals_fetch": "STEP_FINALS_FETCH",
    "transcript_check": "STEP_TRANSCRIPT_CHECK",
    "ledger_guard": "STEP_LEDGER_GUARD",
    "settlement": "STEP_SETTLEMENT",
    "verify": "STEP_VERIFY",
    "semantic_crosscheck": "STEP_SEMANTIC_CROSSCHECK",
    "commit_snapshots": "STEP_COMMIT_SNAPSHOTS",
}

SCOPE_NOTE = (
    "This workflow archives official injury reports and fetches/settles finals for the sealed v1 window. "
    "It does not refresh the published v2 team's schedule, standings, ratings, or player inputs, and it "
    "does not provide market prices. A successful run is not a v2 line-freshness or bet-eligibility approval."
)


def _valid_timestamp(value: object, field: str, *, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty ISO-8601 timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} is not an ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a UTC offset")


def _workflow_url(sha: str) -> str:
    if not SHA_RE.fullmatch(sha):
        raise ValueError("head_sha must be a 40-character lowercase commit SHA")
    return f"https://github.com/{REPOSITORY}/blob/{sha}/{WORKFLOW_PATH}"


def _validate_record(record: dict) -> dict:
    if record.get("schema_version") != 1:
        raise ValueError("refresh status schema_version must be 1")
    if record.get("status") not in RUN_STATUS_VALUES:
        raise ValueError(f"refresh status must be one of {sorted(RUN_STATUS_VALUES)}")
    run_id = str(record.get("run_id", ""))
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must contain decimal digits only")
    if record.get("run_url") != f"https://github.com/{REPOSITORY}/actions/runs/{run_id}":
        raise ValueError("run_url does not match the official GitHub Actions run id")
    sha = record.get("head_sha")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ValueError("head_sha must be a 40-character lowercase commit SHA")
    if record.get("workflow_url") != _workflow_url(sha):
        raise ValueError("workflow_url must point to the workflow file at this run's commit")
    _valid_timestamp(record.get("recorded_at_utc"), "recorded_at_utc")
    for key in ("run_created_at_utc", "run_updated_at_utc"):
        if key in record:
            _valid_timestamp(record[key], key, nullable=True)
    if not isinstance(record.get("event"), str) or not record["event"]:
        raise ValueError("event must be a non-empty string")
    if not isinstance(record.get("ref"), str) or not record["ref"]:
        raise ValueError("ref must be a non-empty string")
    if record.get("v2_model_inputs_refreshed") is not False:
        raise ValueError("the scheduled v1 refresh is not evidence of a v2 model-input refresh")
    if record.get("scope_note") != SCOPE_NOTE:
        raise ValueError("scope_note must retain the verified separation between v1 refresh and v2 inputs")
    outcomes = record.get("step_outcomes")
    if not isinstance(outcomes, dict):
        raise ValueError("step_outcomes must be an object")
    unknown = {v for v in outcomes.values() if v not in STEP_STATUS_VALUES}
    if unknown:
        raise ValueError(f"unrecognized step outcomes: {sorted(unknown)}")
    return record


def empty_status() -> dict:
    """A fail-closed display state for a clean checkout without a run record."""
    return {
        "schema_version": 1,
        "status": "unrecorded",
        "run_id": None,
        "run_url": WORKFLOW_HISTORY_URL,
        "workflow_url": WORKFLOW_MAIN_URL,
        "recorded_at_utc": None,
        "run_created_at_utc": None,
        "run_updated_at_utc": None,
        "event": "unknown",
        "ref": "unknown",
        "head_sha": None,
        "step_outcomes": {},
        "v2_model_inputs_refreshed": False,
        "scope_note": SCOPE_NOTE,
        "note": "No automated refresh result has been recorded in this checkout. Check the workflow history before relying on freshness.",
    }


def read_status(path: Path = STATUS_PATH) -> dict:
    """Load and validate the latest committed run record; absence is explicitly unrecorded."""
    if not path.exists():
        return empty_status()
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read refresh status {path}: {exc}") from exc
    if not isinstance(record, dict):
        raise ValueError("refresh status must be a JSON object")
    return _validate_record(record)


def _env_status(env: Mapping[str, str], now: dt.datetime | None = None) -> dict:
    run_id = env.get("RUN_ID", "")
    sha = env.get("RUN_SHA", "")
    recorded = now or dt.datetime.now(dt.timezone.utc)
    if recorded.tzinfo is None:
        raise ValueError("recording time must have a UTC offset")
    record = {
        "schema_version": 1,
        "status": env.get("RUN_STATUS", "").lower(),
        "run_id": run_id,
        "run_url": f"https://github.com/{REPOSITORY}/actions/runs/{run_id}",
        "workflow_url": _workflow_url(sha),
        "recorded_at_utc": recorded.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "event": env.get("RUN_EVENT", ""),
        "ref": env.get("RUN_REF", ""),
        "head_sha": sha,
        "step_outcomes": {
            name: env.get(env_name, "not-run").lower() or "not-run"
            for name, env_name in STEP_ENV.items()
        },
        "v2_model_inputs_refreshed": False,
        "scope_note": SCOPE_NOTE,
    }
    for field, env_name in (("run_created_at_utc", "RUN_CREATED_AT_UTC"),
                            ("run_updated_at_utc", "RUN_UPDATED_AT_UTC")):
        if env.get(env_name):
            record[field] = env[env_name]
    if record["status"] == "failure":
        failed = [name for name, outcome in record["step_outcomes"].items() if outcome == "failure"]
        record["note"] = (
            "One or more refresh/validation steps failed before status publication"
            + (f" ({', '.join(failed)})." if failed else ".")
            + " See the linked run for details; the exact source/API cause is not inferred."
        )
    elif record["status"] == "cancelled":
        record["note"] = "The refresh run was cancelled; no successful completion is implied. See the linked run."
    else:
        record["note"] = (
            "All recorded refresh/validation steps before status publication succeeded. "
            "This does not establish freshness of the published v2 model inputs."
        )
    return _validate_record(record)


def record_run(env: Mapping[str, str] | None = None, path: Path = STATUS_PATH,
               now: dt.datetime | None = None) -> dict:
    """Write the workflow's current result atomically, with a source link for review."""
    record = _env_status(env if env is not None else os.environ, now=now)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    return record


def main() -> int:
    record = record_run()
    print(json.dumps({
        "status": record["status"],
        "run_id": record["run_id"],
        "run_url": record["run_url"],
        "recorded_at_utc": record["recorded_at_utc"],
        "v2_model_inputs_refreshed": record["v2_model_inputs_refreshed"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
