"""Regression tests for the nightly refresh's completed-finals and standings gates.

These tests use synthetic values only; they exercise validation logic and do not assert
any live NBA result or standings value.
"""
from __future__ import annotations

import datetime as dt
import unittest

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
            "slate": {"games": [{"date": today, "game_id": "0022600102",
                                  "source_url": "https://www.nba.com/schedule"}]},
            "team_stats": {},
        }
        gates = R.run_gates(docs, ["2026-11-14", today], today)
        self.assertTrue(gates[0]["ok"], gates[0]["detail"])


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
