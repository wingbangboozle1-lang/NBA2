"""Tests for the nightly ingest pipeline's pure logic (no network)."""

from __future__ import annotations

import unittest

from nba2.pipeline import refresh as RF


class TestStampParsing(unittest.TestCase):
    def test_pdf_url_regex(self):
        url = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf"
        m = RF.PDF_RE.search(url)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "2026-11-13")
        self.assertEqual(m.group(2), "07")
        self.assertEqual(m.group(3), "30")
        self.assertEqual(m.group(4), "PM")

    def test_newest_release_for_date_picks_latest_stamp(self):
        html = (
            "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf "
            "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf "
            "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_00PM.pdf"
        )
        got = RF.newest_release_for_date(html, "2026-11-13")
        self.assertIsNotNone(got)
        self.assertIn("07_30PM", got[0])
        self.assertEqual(got[1], "2026-11-13T19:30")

    def test_no_release_returns_none(self):
        self.assertIsNone(RF.newest_release_for_date("no links here", "2026-11-13"))


class TestFinalsSchema(unittest.TestCase):
    def test_cdn_payload_only_finals(self):
        payload = {"scoreboard": {"games": [
            {"gameId": "0022600301", "gameStatus": "3",
             "homeTeam": {"teamTrigramCode": "BOS", "score": 118},
             "awayTeam": {"teamTrigramCode": "NYK", "score": 111}},
            {"gameId": "0022600302", "gameStatus": "2",
             "homeTeam": {"teamTrigramCode": "MIA", "score": 55},
             "awayTeam": {"teamTrigramCode": "DET", "score": 51}},
        ]}}
        recs = RF.final_games_cdn(payload, "2026-11-14")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["game_id"], "0022600301")
        self.assertEqual(recs[0]["home_pts"], 118)
        self.assertEqual(recs[0]["away_pts"], 111)

    def test_scoreboardv2_payload_only_finals(self):
        payload = {"resultSets": [{"name": "LineScore", "headers": [
            "GAME_ID", "TEAM_ABBREVIATION", "PTS", "GAME_STATUS_ID"],
            "rowSet": [
                ["0022600301", "BOS", 118, "3"],
                ["0022600301", "NYK", 111, "3"],
                ["0022600302", "MIA", 55, "2"],
            ]}]}
        recs = RF.final_games_scoreboardv2(payload, "2026-11-14")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["home_pts"], 118)
        self.assertEqual(recs[0]["away_pts"], 111)


class TestTranscriptCrossCheck(unittest.TestCase):
    def test_recall_floor_passes_on_full_match(self):
        text = "Banchero, Paolo Out Isaac, Jonathan Out Cain, Jamal Available"
        tr = {"records": [
            ["2026-11-14", "07:00", "X@Y", "Team A", "Banchero, Paolo", "Out", "r", "E"],
            ["2026-11-14", "07:00", "X@Y", "Team A", "Cain, Jamal", "Available", "r", "E"],
        ]}
        res = RF.check_transcript_against_pdf(tr, text)
        self.assertTrue(res["pass"])
        self.assertEqual(res["recall"], 1.0)

    def test_recall_floor_fails_when_statuses_missing(self):
        text = "Totally unrelated text with no pairs"
        tr = {"records": [
            ["2026-11-14", "07:00", "X@Y", "Team A", "Banchero, Paolo", "Out", "r", "E"],
        ]}
        res = RF.check_transcript_against_pdf(tr, text)
        self.assertFalse(res["pass"])


if __name__ == "__main__":
    unittest.main()
