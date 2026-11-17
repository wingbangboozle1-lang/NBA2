"""Regression tests for the nightly refresh's completed-finals and standings gates.

These tests use synthetic values only; they exercise validation logic and do not assert
any live NBA result or standings value.
"""
from __future__ import annotations

import datetime as dt
import unittest
from unittest import mock

from . import refresh as R


class TestFinalsGate(unittest.TestCase):
    def test_off_day_is_valid_but_every_date_must_have_a_scoreboard_response(self):
        dates = ["2026-11-10", "2026-11-11", "2026-11-12"]
        doc = {
            "games_seen_by_date": {dates[0]: 1, dates[1]: 0, dates[2]: 1},
            "finals_by_date": {dates[0]: 1, dates[1]: 0, dates[2]: 1},
            "records": [
                {"date": dates[0], "game_id": "0022600101"},
                {"date": dates[2], "game_id": "0022600102"},
            ],
        }
        result = R.gate_finals(dates, doc)
        self.assertTrue(result["ok"], result["detail"])
        self.assertIn("off-days are valid", result["detail"])

    def test_scheduled_but_unfinished_game_fails(self):
        dates = ["2026-11-10"]
        doc = {
            "games_seen_by_date": {dates[0]: 2},
            "finals_by_date": {dates[0]: 1},
            "records": [{"date": dates[0], "game_id": "0022600101"}],
        }
        self.assertFalse(R.gate_finals(dates, doc)["ok"])

    def test_missing_scoreboard_coverage_fails_closed(self):
        dates = ["2026-11-10", "2026-11-11"]
        doc = {
            "games_seen_by_date": {dates[0]: 1},
            "finals_by_date": {dates[0]: 1},
            "records": [{"date": dates[0], "game_id": "0022600101"}],
        }
        self.assertFalse(R.gate_finals(dates, doc)["ok"])

    def test_duplicate_or_out_of_window_game_fails(self):
        date = "2026-11-10"
        row = {"date": date, "game_id": "0022600101"}
        doc = {
            "games_seen_by_date": {date: 2}, "finals_by_date": {date: 2},
            "records": [row, dict(row)],
        }
        self.assertFalse(R.gate_finals([date], doc)["ok"])
        doc["games_seen_by_date"][date] = 1
        doc["finals_by_date"][date] = 1
        doc["records"] = [dict(row, date="2026-11-09")]
        self.assertFalse(R.gate_finals([date], doc)["ok"])

    def test_run_gates_excludes_current_day_from_completed_finals(self):
        today = "2026-11-15"
        docs = {
            "finals": {
                "games_seen_by_date": {"2026-11-14": 1},
                "finals_by_date": {"2026-11-14": 1},
                "records": [{"date": "2026-11-14", "game_id": "0022600101"}],
            },
            "standings": TestStandingsGate.balanced_snapshot(),
            "injuries": {"pdf_url": "https://official.nba.com/report.pdf",
                         "retrieval_time_utc": "2026-11-15T00:00:00Z",
                         "revision_time_et": "2026-11-15 06:00 AM ET"},
            "slate": {
                "covered_dates": ["2026-11-15", "2026-11-16", "2026-11-17", "2026-11-18"],
                "games": [{"date": today, "game_id": "0022600102", "home": "BOS", "away": "NYK",
                           "source_url": "https://www.nba.com/schedule?date=2026-11-15"}],
            },
            "team_stats": {},
        }
        gates = R.run_gates(docs, ["2026-11-14", today], today)
        self.assertTrue(gates[0]["ok"], gates[0]["detail"])


class TestSlateGate(unittest.TestCase):
    TODAY = "2026-11-15"
    DATES = ["2026-11-15", "2026-11-16", "2026-11-17", "2026-11-18"]

    @classmethod
    def valid_slate(cls):
        return {
            "covered_dates": list(cls.DATES),
            "games": [{
                "date": cls.DATES[0], "game_id": "0022600101", "home": "BOS", "away": "NYK",
                "source_url": f"https://www.nba.com/schedule?date={cls.DATES[0]}",
            }],
        }

    def test_fetch_slate_records_every_successful_date_query(self):
        # Transport rewritten 2026-11-17: the slate is read from the server-rendered
        # www.nba.com/games?date= page, because the stats.nba.com scoreboard JSON this
        # mocked times out from a GitHub-hosted runner (measured, see
        # data/raw/page_fixtures/transport_probe.json). The rule under test is unchanged:
        # a date that was fetched successfully counts as coverage even with no games.
        with mock.patch.object(R, "fetch_day_games", return_value=[]) as get:
            result = R.fetch_slate(self.DATES)
        self.assertEqual(result["covered_dates"], self.DATES)
        self.assertEqual(result["games"], [])
        self.assertEqual(get.call_count, 4)
        self.assertEqual([call.args[0] for call in get.call_args_list], self.DATES)

    def test_requires_all_four_successful_schedule_fetches(self):
        slate = self.valid_slate()
        self.assertTrue(R.gate_slate(slate, self.TODAY)["ok"])
        slate["covered_dates"].remove(self.DATES[2])
        result = R.gate_slate(slate, self.TODAY)
        self.assertFalse(result["ok"])
        self.assertIn(self.DATES[2], result["detail"])

    def test_empty_game_list_only_passes_when_all_dates_were_fetched(self):
        slate = {"covered_dates": list(self.DATES), "games": []}
        self.assertTrue(R.gate_slate(slate, self.TODAY)["ok"])
        result = R.gate_slate({"covered_dates": [], "games": []}, self.TODAY)
        self.assertFalse(result["ok"])

    def test_rejects_out_of_window_rows_invalid_ids_or_missing_teams(self):
        slate = self.valid_slate()
        slate["games"][0]["date"] = "2026-11-19"
        self.assertFalse(R.gate_slate(slate, self.TODAY)["ok"])

        slate = self.valid_slate()
        slate["games"][0]["game_id"] = "unknown"
        self.assertFalse(R.gate_slate(slate, self.TODAY)["ok"])

        slate = self.valid_slate()
        slate["games"][0]["home"] = None
        self.assertFalse(R.gate_slate(slate, self.TODAY)["ok"])

    def test_rejects_duplicate_ids_and_non_nba_or_wrong_date_source_urls(self):
        slate = self.valid_slate()
        duplicate = dict(slate["games"][0], date=self.DATES[1],
                         source_url=f"https://www.nba.com/schedule?date={self.DATES[1]}")
        slate["games"].append(duplicate)
        self.assertFalse(R.gate_slate(slate, self.TODAY)["ok"])

        slate = self.valid_slate()
        slate["games"][0]["source_url"] = "https://example.com/schedule?date=2026-11-15"
        self.assertFalse(R.gate_slate(slate, self.TODAY)["ok"])

        slate = self.valid_slate()
        slate["games"][0]["source_url"] = "https://www.nba.com/schedule?date=2026-11-16"
        self.assertFalse(R.gate_slate(slate, self.TODAY)["ok"])

    def test_malformed_coverage_and_anchor_fail_without_exception(self):
        for covered in ({}, [None], [["2026-11-15"]]):
            with self.subTest(covered=covered):
                result = R.gate_slate({"covered_dates": covered, "games": []}, self.TODAY)
                self.assertFalse(result["ok"])
        self.assertFalse(R.gate_slate(self.valid_slate(), "not-a-date")["ok"])


class TestStandingsGate(unittest.TestCase):
    @staticmethod
    def balanced_snapshot():
        # Balanced synthetic season-to-date records; not real team or standings data.
        rows = [{"tri": f"T{i:02d}", "w": 4, "l": 4} for i in range(30)]
        return {
            "fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "rows": rows,
        }

    def test_accepts_fresh_balanced_cumulative_records_without_partial_feed_match(self):
        standings = self.balanced_snapshot()
        partial_finals = {"records": [{"home": "T00", "away": "T01", "home_pts": 1, "away_pts": 0}]}
        result = R.gate_standings(standings, partial_finals)
        self.assertTrue(result["ok"], result["detail"])
        self.assertIn("internally balanced", result["detail"])

    def test_rejects_unbalanced_or_duplicate_or_stale_snapshot(self):
        standings = self.balanced_snapshot()
        standings["rows"][0]["w"] += 1
        self.assertFalse(R.gate_standings(standings, {})["ok"])

        standings = self.balanced_snapshot()
        standings["rows"][1]["tri"] = standings["rows"][0]["tri"]
        self.assertFalse(R.gate_standings(standings, {})["ok"])

        standings = self.balanced_snapshot()
        old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)
        standings["fetched_at_utc"] = old.isoformat()
        self.assertFalse(R.gate_standings(standings, {})["ok"])


if __name__ == "__main__":
    unittest.main()
