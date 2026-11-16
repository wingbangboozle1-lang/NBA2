"""Regression tests for the scheduled v2 refresh gate contract (no network).

Ported from PR #80 (session arena/0429aad7-nba2) by the integration session
(arena/a11505e1-nba2) when that stale branch was taken over. Every scenario and
assertion intent from the original file is preserved; only fixture SHAPES that
targeted PR #80's parallel gate implementations were adapted to the gate
implementations kept on main (session arena/a95e2125-nba2's fail-closed
``gate_finals``/``gate_slate`` use ``games_seen_by_date``/``finals_by_date`` and
``covered_dates``). Message assertions follow the kept implementation's wording.
The one stale snapshot COUNT assertion was rewritten as the invariant it meant
(the committed history rebuilds exactly to the captured standings) so history
growth cannot falsify it — the same lesson as RR-37.
"""

from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from . import refresh as RF


ROOT = Path(__file__).resolve().parents[2]


def final(game_id: str, date: str, home: str, away: str,
          home_pts: int, away_pts: int) -> dict:
    return {
        "game_id": game_id, "date": date, "home": home, "away": away,
        "home_pts": home_pts, "away_pts": away_pts,
        "source_url": f"https://www.nba.com/game/{game_id}",
    }


class TestScoreboardCapture(unittest.TestCase):
    def test_final_rows_and_status_inventory_are_preserved_by_date(self):
        headers = ["gameId", "gameStatus", "gameStatusText", "homeTeamTricode",
                   "awayTeamTricode", "homeTeamScore", "awayTeamScore"]
        yesterday = {"resultSets": [{"headers": headers, "rowSet": [
            ["0022600231", 3, "Final", "NOP", "DEN", 108, 116],
        ]}]}
        today = {"resultSets": [{"headers": headers, "rowSet": [
            ["0022600232", 1, "Scheduled", "CLE", "DAL", 0, 0],
        ]}]}
        with patch.object(RF, "http_json", side_effect=[yesterday, today]):
            result = RF.fetch_finals(["2026-11-14", "2026-11-15"])
        # the per-date inventory is kept so an official off-day (checked, zero games)
        # is distinguishable from an unchecked date
        self.assertEqual(result["games_seen_by_date"],
                         {"2026-11-14": 1, "2026-11-15": 1})
        self.assertEqual(result["finals_by_date"],
                         {"2026-11-14": 1, "2026-11-15": 0})
        self.assertEqual(result["records"], [
            {"date": "2026-11-14", "game_id": "0022600231", "home": "NOP",
             "away": "DEN", "home_pts": 108, "away_pts": 116,
             "source_url": "https://www.nba.com/game/den-vs-nop-0022600231"},
        ])


class TestFinalsGateCoverage(unittest.TestCase):
    def test_prior_finals_pass_with_off_day_and_unfinished_today(self):
        prior = ["2026-11-13", "2026-11-14"]
        today = "2026-11-15"
        docs = {
            # an official scoreboard check with zero games is a valid off-day;
            # today's unfinished game must not block yesterday's completeness
            "games_seen_by_date": {"2026-11-13": 0, "2026-11-14": 1, today: 1},
            "finals_by_date": {"2026-11-13": 0, "2026-11-14": 1, today: 0},
            "records": [final("0022600001", "2026-11-14", "BOS", "NYK", 101, 99)],
        }
        result = RF.gate_finals(prior, docs)
        self.assertTrue(result["ok"], result)

    def test_prior_scheduled_game_without_final_blocks(self):
        docs = {
            "games_seen_by_date": {"2026-11-14": 1},
            "finals_by_date": {"2026-11-14": 0},  # scheduled but not final
            "records": [],
        }
        result = RF.gate_finals(["2026-11-14"], docs)
        self.assertFalse(result["ok"])
        self.assertIn("dates with non-final games", result["detail"])
        self.assertIn("2026-11-14", result["detail"])

    def test_unchecked_calendar_date_is_not_assumed_to_be_an_off_day(self):
        docs = {
            "games_seen_by_date": {"2026-11-13": 0},
            "finals_by_date": {"2026-11-13": 0},
            "records": [],
        }
        result = RF.gate_finals(["2026-11-13", "2026-11-14"], docs)
        self.assertFalse(result["ok"])
        self.assertIn("2026-11-14", result["detail"])

    def test_missing_game_inventory_and_malformed_final_fail_closed(self):
        docs = {
            "games_seen_by_date": {},
            "finals_by_date": {},
            "records": [{"date": "2026-11-14", "game_id": "g1"}],
        }
        result = RF.gate_finals(["2026-11-14"], docs)
        self.assertFalse(result["ok"])
        self.assertIn("dates without scoreboard coverage", result["detail"])
        self.assertIn("invalid official game ids", result["detail"])


class TestSeasonToDateStandingsGate(unittest.TestCase):
    def test_baseline_and_recent_finals_are_deduplicated(self):
        old = final("g1", "2026-11-13", "BOS", "NYK", 101, 99)
        new = final("g2", "2026-11-14", "MIN", "CHI", 90, 95)
        standings = {"rows": [
            {"tri": "BOS", "w": 1, "l": 0},
            {"tri": "NYK", "w": 0, "l": 1},
            {"tri": "MIN", "w": 0, "l": 1},
            {"tri": "CHI", "w": 1, "l": 0},
            {"tri": "DAL", "w": 0, "l": 0},
        ]}
        result = RF.gate_standings(standings, {"records": [old, new]}, [old])
        self.assertTrue(result["ok"], result)
        self.assertIn("2 unique season finals", result["measured"])

    def test_live_refresh_rejects_partial_standings_table(self):
        standings = {"rows": [{"tri": "BOS", "w": 0, "l": 0}]}
        result = RF.gate_standings(standings, {"records": []}, require_all_30=True)
        self.assertFalse(result["ok"])
        self.assertIn("expected 30 unique team standings rows", result["detail"])

    def test_malformed_or_unmapped_final_record_blocks_standings(self):
        standings = {"rows": [{"tri": "BOS", "w": 0, "l": 0},
                              {"tri": "NYK", "w": 0, "l": 0}]}
        malformed = RF.gate_standings(standings, {"records": [{"game_id": "g1"}]}, baseline_records=[])
        self.assertFalse(malformed["ok"])
        self.assertIn("malformed baseline/fresh final records", malformed["detail"])
        unknown = RF.gate_standings(
            standings, {"records": [final("g2", "2026-11-14", "XXX", "YYY", 101, 99)]},
            baseline_records=[],
        )
        self.assertFalse(unknown["ok"])
        self.assertIn("final-feed teams absent from standings", unknown["detail"])

    def test_conflicting_duplicate_game_id_blocks_standings(self):
        old = final("g1", "2026-11-13", "BOS", "NYK", 101, 99)
        changed = final("g1", "2026-11-13", "BOS", "NYK", 102, 99)
        standings = {"rows": [
            {"tri": "BOS", "w": 1, "l": 0},
            {"tri": "NYK", "w": 0, "l": 1},
        ]}
        result = RF.gate_standings(standings, {"records": [changed]}, [old])
        self.assertFalse(result["ok"])
        self.assertIn("conflicting duplicate finals", result["detail"])

    def test_committed_history_rebuilds_to_the_captured_standings(self):
        # The original test asserted a hard-coded 188-game count and the 11-15
        # capture; both went stale as the committed history grew (RR-37). The
        # invariant meant by that test: every committed official final is unique
        # and the season W/L rebuilds exactly to the newest captured standings.
        snapshot = json.loads(
            (ROOT / "data/raw/capture_2026-11-16/standings_2026-11-16.json").read_text()
        )
        standings = {"rows": [
            {"tri": row["team"], "w": row["w"], "l": row["l"]}
            for row in snapshot["rows"]
        ]}
        baseline = RF.load_committed_final_records()
        gids = [r["game_id"] for r in baseline]
        self.assertEqual(len(gids), len(set(gids)), "duplicate finals in the committed history")
        result = RF.gate_standings(standings, {"records": []}, baseline)
        self.assertTrue(result["ok"], result)
        self.assertIn("rebuilds exactly from unique official finals", result["detail"])

    def test_unreadable_committed_result_snapshot_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw"
            history = raw / "history"
            history.mkdir(parents=True)
            (history / "games_broken.json").write_text("{")
            with patch.object(RF, "RAW", raw), patch.object(RF, "HISTORY", history):
                with self.assertRaisesRegex(RuntimeError, "cannot load committed result snapshot"):
                    RF.load_committed_final_records()


class TestIntegratedGateChain(unittest.TestCase):
    def test_current_official_capture_passes_all_refresh_gates(self):
        capture = ROOT / "data/raw/capture_2026-11-16"
        standings_doc = json.loads((capture / "standings_2026-11-16.json").read_text())
        results_doc = json.loads((ROOT / "data/raw/results/results_2026-11-15.json").read_text())
        slate_doc = json.loads((capture / "slate_2026-11-16_to_11-19.json").read_text())
        self.assertEqual({row.get("status") for row in results_doc["records"]}, {"final"})
        standings = {
            "fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "rows": [
                {"tri": row["team"], "w": row["w"], "l": row["l"],
                 "source_url": "https://www.nba.com/standings"}
                for row in standings_doc["rows"]
            ],
        }
        prior = "2026-11-15"
        today = "2026-11-16"
        finals = {
            "games_seen_by_date": {prior: len(results_doc["records"])},
            "finals_by_date": {prior: len(results_doc["records"])},
            "records": results_doc["records"],
        }
        slate = {
            "covered_dates": [today, "2026-11-17", "2026-11-18", "2026-11-19"],
            "games": [{"date": row["date"], "game_id": row["game_id"],
                       "home": row["home"], "away": row["away"],
                       "source_url": f"https://www.nba.com/schedule?date={row['date']}"}
                      for row in slate_doc["games"]],
        }
        team_stats = {
            key: {"source_url": RF.URLS[key].format(season=RF.SEASON), "rows": [[]]}
            for key in ("team_traditional", "team_opponent", "team_advanced")
        }
        docs = {
            "standings": standings,
            "slate": slate,
            "finals": finals,
            "baseline_finals": {"records": RF.load_committed_final_records()},
            "team_stats": team_stats,
            "injuries": {
                "pdf_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_15AM.pdf",
                "revision_time_et": "2026-11-16 09:15 AM ET",
                "retrieval_time_utc": "2026-11-16T14:15:00Z",
            },
        }
        gates = RF.run_gates(docs, [prior], today)
        self.assertTrue(all(gate["ok"] for gate in gates), gates)


class TestOtherRefreshGates(unittest.TestCase):
    def test_slate_requires_all_four_dates_to_be_checked_when_metadata_exists(self):
        today = "2026-11-15"
        dates = ["2026-11-15", "2026-11-16", "2026-11-17", "2026-11-18"]
        slate = {
            "covered_dates": dates,
            # The official feed can return a valid empty list on an off-day.
            "games": [{"date": today, "game_id": "0022600101", "home": "BOS", "away": "NYK",
                       "source_url": "https://www.nba.com/schedule?date=2026-11-15"}],
        }
        self.assertTrue(RF.gate_slate(slate, today)["ok"])
        slate["covered_dates"] = dates[:-1]
        result = RF.gate_slate(slate, today)
        self.assertFalse(result["ok"])
        self.assertIn("2026-11-18", result["detail"])

    def test_team_stats_gate_requires_a_page_level_source(self):
        docs = {"team_stats": {
            "advanced": {"rows": [["BOS", 100.0]]},
            "opponent": {"rows": [["BOS", 99.0]],
                         "source_url": RF.URLS["team_opponent"].format(season=RF.SEASON)},
        }}
        result = RF.gate_provenance(docs)
        self.assertFalse(result["ok"])
        self.assertIn("team_stats.advanced.source_url", result["detail"])

    def test_injury_index_selection_uses_latest_timestamp_not_link_order(self):
        html = """
        <a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_00AM.pdf">older</a>
        <a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_11_45PM.pdf">prior day</a>
        <a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf">new</a>
        """
        selected = RF.newest_release_from_index(html)
        self.assertIsNotNone(selected)
        self.assertTrue(selected["pdf_url"].endswith("2026-11-15_06_15AM.pdf"))
        self.assertEqual(selected["revision_time_et"], "2026-11-15 06:15 AM ET")


if __name__ == "__main__":
    unittest.main()
