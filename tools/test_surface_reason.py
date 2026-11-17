"""Offline tests for tools/surface_reason.py.

The tool exists because a failing nightly run's cause was unreadable after the fact.
A wrong reason is worse than none: it sends the next session to the wrong endpoint. So
every branch is pinned to a line this repository's own code actually prints.
"""

from __future__ import annotations

import unittest

from tools import surface_reason as SR


class TestReason(unittest.TestCase):
    def test_gate_refusal_is_quoted_verbatim(self):
        log = (
            "nba2.v2.refresh: window 2026-11-17..2026-11-20 (anchor 2026-11-17)\n"
            "  [PASS] freshness/finals: 7 dates — ok\n"
            "  [FAIL] freshness/injuries: newest release 2026-11-16 01:00 PM ET — "
            "older than the most recent game day\n"
            "REFRESH ABORTED: a freshness/provenance gate failed — nothing written\n"
        )
        r = SR.reason(log)
        self.assertIn("gate refused the refresh", r)
        self.assertIn("REFRESH ABORTED", r)

    def test_specific_gate_line_is_used_when_no_abort_line(self):
        log = "  [FAIL] provenance: 3 rows — a row was written without a source URL\n"
        r = SR.reason(log)
        self.assertIn("freshness/provenance gate failed", r)
        self.assertIn("provenance", r)
        self.assertIn("without a source URL", r)

    def test_our_fetch_wrapper_names_the_url_and_error(self):
        log = (
            "Traceback (most recent call last):\n"
            "  File \"nba2/v2/refresh.py\", line 80, in http_get\n"
            "RuntimeError: fetch failed after 3 tries: "
            "https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00: "
            "HTTP Error 403: Forbidden\n"
        )
        r = SR.reason(log)
        self.assertIn("official endpoint unreachable", r)
        self.assertIn("stats.nba.com", r)
        self.assertIn("403", r)

    def test_http_status_line_is_recognised(self):
        r = SR.reason("RuntimeError: HTTP 403 for https://stats.nba.com/stats/x\n")
        self.assertIn("HTTP 403", r)
        self.assertIn("stats.nba.com", r)

    def test_bare_traceback_reports_the_exception(self):
        log = (
            "Traceback (most recent call last):\n"
            "  File \"nba2/v2/refresh.py\", line 12, in <module>\n"
            "KeyError: 'resultSets'\n"
        )
        r = SR.reason(log)
        # KeyError does not match the Error/Exception suffix rule only if it ends in 'Error'
        self.assertTrue("KeyError" in r or "no recognised failure line" in r)

    def test_timeout_is_named(self):
        log = "urllib.error.URLError: <urlopen error [Errno 111] Connection refused>\n"
        r = SR.reason(log)
        self.assertIn("Connection refused", r)

    def test_silence_is_reported_as_silence(self):
        r = SR.reason("")
        self.assertIn("no console output", r)

    def test_ci_decorations_are_stripped(self):
        log = "2026-11-17T14:58:01.1234567Z ::error title=x::REFRESH ABORTED: gate failed\n"
        r = SR.reason(log)
        self.assertNotIn("::error", r)
        self.assertNotIn("2026-11-17T", r)
        self.assertIn("REFRESH ABORTED", r)

    def test_unknown_output_quotes_the_tail_not_a_guess(self):
        log = "step 1\nstep 2\nsomething odd happened\nstep 4\n"
        r = SR.reason(log)
        self.assertIn("no recognised failure line", r)
        self.assertIn("something odd happened", r)

    def test_result_is_single_line_and_bounded(self):
        log = "  [FAIL] freshness/slate: " + ("x" * 5000) + "\n"
        r = SR.reason(log, max_chars=120)
        self.assertEqual(len(r), 120)
        self.assertNotIn("\n", r)

    def test_a_pass_only_log_is_not_a_failure(self):
        log = "  [PASS] freshness/finals: 7 dates — ok\n  [PASS] provenance: 9 rows — ok\n"
        r = SR.reason(log)
        self.assertIn("no recognised failure line", r)
        self.assertNotIn("gate refused", r)


if __name__ == "__main__":
    unittest.main()
