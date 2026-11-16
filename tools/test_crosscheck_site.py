"""Regression tests for the ingest-status evidence used by CC-FRESH-03.

These tests use synthetic GitHub Actions payloads only; they do not assert any NBA data.
"""
from __future__ import annotations

import unittest

from tools import crosscheck_site as CC


def run(run_id: int, created_at: str, status: str, conclusion: str | None,
        url: str = "https://github.com/example/repo/actions/runs/1",
        branch: str = "main", event: str = "schedule") -> dict:
    return {
        "databaseId": run_id,
        "createdAt": created_at,
        "status": status,
        "conclusion": conclusion,
        "url": url,
        "headBranch": branch,
        "event": event,
    }


class TestRefreshRunSummary(unittest.TestCase):
    def test_latest_completed_failure_is_not_hidden_by_an_older_success(self):
        result = CC._summarize_refresh_runs([
            run(1, "2026-11-15T14:00:00Z", "completed", "success"),
            run(2, "2026-11-16T14:00:00Z", "completed", "failure"),
        ])
        self.assertTrue(result["available"])
        self.assertEqual(result["n_runs"], 2)
        self.assertEqual(result["latest"]["conclusion"], "failure")
        self.assertEqual(result["latest"]["created_at"], "2026-11-16T14:00:00Z")

    def test_latest_success_is_reported_with_its_url(self):
        result = CC._summarize_refresh_runs([
            run(3, "2026-11-16T14:00:00Z", "completed", "success",
                "https://github.com/example/repo/actions/runs/3"),
            run(2, "2026-11-15T14:00:00Z", "completed", "failure"),
        ])
        self.assertEqual(result["latest"]["conclusion"], "success")
        self.assertEqual(result["latest"]["url"],
                         "https://github.com/example/repo/actions/runs/3")

    def test_in_progress_current_run_is_excluded(self):
        result = CC._summarize_refresh_runs([
            run(11, "2026-11-16T18:35:00Z", "in_progress", None),
            run(10, "2026-11-16T14:05:00Z", "completed", "failure"),
        ], current_run_id="11")
        self.assertEqual(result["n_runs"], 1)
        self.assertEqual(result["latest"]["conclusion"], "failure")

    def test_no_completed_runs_stays_unknown_not_success(self):
        result = CC._summarize_refresh_runs([
            run(12, "2026-11-16T18:35:00Z", "in_progress", None),
        ])
        self.assertTrue(result["available"])
        self.assertIsNone(result["latest"])

    def test_non_main_and_non_schedule_runs_do_not_set_published_freshness(self):
        result = CC._summarize_refresh_runs([
            run(14, "2026-11-16T18:36:00Z", "completed", "success", branch="feature"),
            run(13, "2026-11-16T18:35:00Z", "completed", "success", event="pull_request"),
        ])
        self.assertEqual(result["n_runs"], 0)
        self.assertIsNone(result["latest"])

    def test_empty_run_list_is_distinct_from_unavailable_api(self):
        result = CC._summarize_refresh_runs([])
        self.assertTrue(result["available"])
        self.assertEqual(result["n_runs"], 0)
        self.assertIsNone(result["latest"])

    def test_non_list_payload_is_reported_unavailable(self):
        result = CC._summarize_refresh_runs({"error": "not a list"})
        self.assertFalse(result["available"])
        self.assertIsNone(result["latest"])


class TestFreshnessVerdict(unittest.TestCase):
    def test_latest_completed_success_is_the_only_pass_case(self):
        verdict, _, _ = CC._refresh_status_check({
            "available": True,
            "n_runs": 4,
            "latest": {"conclusion": "success", "created_at": "2026-11-16T14:00:00Z"},
        }, has_ingest=True)
        self.assertEqual(verdict, CC.PASS)

    def test_latest_completed_failure_is_not_a_pass(self):
        verdict, run_text, _ = CC._refresh_status_check({
            "available": True,
            "n_runs": 4,
            "latest": {"conclusion": "failure", "created_at": "2026-11-16T14:00:00Z"},
        }, has_ingest=True)
        self.assertEqual(verdict, CC.INFO)
        self.assertIn("concluded failure", run_text)

    def test_in_progress_run_is_not_a_completed_refresh(self):
        verdict, run_text, _ = CC._refresh_status_check({
            "available": True, "n_runs": 1, "latest": None,
        }, has_ingest=True)
        self.assertEqual(verdict, CC.INFO)
        self.assertIn("no completed run", run_text)

    def test_unavailable_run_api_is_unknown_not_success(self):
        verdict, run_text, _ = CC._refresh_status_check({
            "available": False, "n_runs": None, "latest": None,
            "detail": "API unavailable",
        }, has_ingest=True)
        self.assertEqual(verdict, CC.INFO)
        self.assertEqual(run_text, "API unavailable")

    def test_missing_schedule_cannot_pass_even_after_a_successful_run(self):
        verdict, _, note = CC._refresh_status_check({
            "available": True,
            "n_runs": 1,
            "latest": {"conclusion": "success"},
        }, has_ingest=False)
        self.assertEqual(verdict, CC.INFO)
        self.assertIn("no scheduled trigger", note)


if __name__ == "__main__":
    unittest.main()
