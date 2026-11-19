"""The finals transport, tested against the page the league actually served.

The page bytes come from ``data/raw/page_fixtures/``, captured on a GitHub-hosted runner by
``.github/workflows/capture-fixtures.yml`` — the same environment the nightly job runs in —
with the URL, HTTP status and SHA-256 recorded in ``manifest.json``. Before this change the
finals surface only knew two JSON endpoints, and both of them fail from a runner: cdn.nba.com
answers 403 and stats.nba.com times out (measured, ``transport_probe.json``).
"""

from __future__ import annotations

import gzip
import json
import unittest
import unittest.mock as mock
from datetime import datetime, timezone
from pathlib import Path

from nba2.pipeline import refresh as RF
from nba2.pipeline import settle as ST

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data" / "raw" / "page_fixtures"


def fixture(name: str) -> bytes:
    path = FIXTURES / f"{name}.html.gz"
    if not path.exists():
        raise unittest.SkipTest(f"fixture {name} not committed on this branch")
    return gzip.decompress(path.read_bytes())


class TestFinalsPageParser(unittest.TestCase):
    DATE = "2026-11-16"

    def test_every_final_carries_ids_teams_and_a_quarter_row_that_sums(self):
        recs = RF.final_games_page(fixture(f"games_{self.DATE}"), self.DATE)
        self.assertEqual(len(recs), 8)
        for r in recs:
            self.assertTrue(r["game_id"].startswith("002"), r["game_id"])
            self.assertEqual(len(r["game_id"]), 10)
            self.assertEqual(r["status"], "final")
            self.assertEqual(r["date"], self.DATE)
            self.assertTrue(str(r["final_source_url"]).startswith("https://www.nba.com/game/"))
            self.assertEqual(sum(r["home_q"]), r["home_pts"], r["game_id"])
            self.assertEqual(sum(r["away_q"]), r["away_pts"], r["game_id"])
            self.assertIn("ot_periods", r)

    def test_a_page_that_answers_another_date_is_a_schema_error_not_a_result(self):
        with self.assertRaises(ValueError):
            RF.final_games_page(fixture("games_2026-11-16"), "2026-11-15")

    def test_a_page_without_the_payload_raises(self):
        with self.assertRaises(ValueError):
            RF.final_games_page(b"<html><body>shell</body></html>", "2026-11-16")

    def test_non_regular_season_and_unfinished_games_are_left_out(self):
        payload = {"props": {"pageProps": {"selectedDate": "2026-11-16", "gameCardFeed": {
            "modules": [{"cards": [
                {"cardType": "game", "cardData": {"gameId": "0012600001", "gameStatus": 3,
                                                  "seasonType": "Preseason", "homeTeam": {
                                                      "teamTricode": "BOS", "score": 99,
                                                      "periods": []},
                                                  "awayTeam": {"teamTricode": "NYK", "score": 98,
                                                               "periods": []}}},
                {"cardType": "game", "cardData": {"gameId": "0022600999", "gameStatus": 1,
                                                  "seasonType": "Regular Season", "homeTeam": {
                                                      "teamTricode": "BOS", "score": 0,
                                                      "periods": []},
                                                  "awayTeam": {"teamTricode": "NYK", "score": 0,
                                                               "periods": []}}},
            ]}]}}}}
        html = ('<script id="__NEXT_DATA__" type="application/json">'
                f"{json.dumps(payload)}</script>").encode()
        self.assertEqual(RF.final_games_page(html, "2026-11-16"), [])

    def test_a_quarter_row_that_does_not_add_up_is_not_published(self):
        payload = {"props": {"pageProps": {"selectedDate": "2026-11-16", "gameCardFeed": {
            "modules": [{"cards": [{"cardType": "game", "cardData": {
                "gameId": "0022600999", "gameStatus": 3, "seasonType": "Regular Season",
                "shareUrl": "https://www.nba.com/game/nyk-vs-bos-0022600999",
                "homeTeam": {"teamTricode": "BOS", "score": 100,
                             "periods": [{"period": 1, "score": 10}]},
                "awayTeam": {"teamTricode": "NYK", "score": 98,
                             "periods": [{"period": 1, "score": 98}]}}}]}]}}}}
        html = ('<script id="__NEXT_DATA__" type="application/json">'
                f"{json.dumps(payload)}</script>").encode()
        recs = RF.final_games_page(html, "2026-11-16")
        self.assertEqual(len(recs), 1)
        self.assertNotIn("home_q", recs[0])
        self.assertEqual(recs[0]["home_pts"], 100)


class TestFetchFinalsSourceOrder(unittest.TestCase):
    def test_the_reachable_page_is_tried_before_the_blocked_hosts(self):
        self.assertEqual(RF.FINALS_SOURCES[0][1], "official_page")
        self.assertTrue(RF.FINALS_SOURCES[0][0].startswith("https://www.nba.com/games?date="))

    def test_finals_settle_from_the_official_page(self):
        date = "2026-11-16"
        with mock.patch.object(RF, "_http_get", return_value=fixture(f"games_{date}")) as get:
            snap, url, kind = RF.fetch_finals(date, [])
        self.assertEqual(kind, "ok")
        self.assertEqual(len(snap["records"]), 8)
        self.assertEqual(get.call_count, 1, "the reachable source answered: nothing else is tried")
        self.assertTrue(url.startswith("https://www.nba.com/games?date="))
        for r in snap["records"]:
            self.assertTrue(str(r["source"]).startswith("https://www.nba.com/game/"))

    def test_only_games_of_the_sealed_window_are_kept(self):
        date = "2026-11-16"
        with mock.patch.object(RF, "_http_get", return_value=fixture(f"games_{date}")):
            snap, _, kind = RF.fetch_finals(date, ["0022600245"])
        self.assertEqual(kind, "ok")
        self.assertEqual([r["game_id"] for r in snap["records"]], ["0022600245"])
        self.assertEqual(snap["expected_window_games"], 1)
        self.assertEqual(snap["games_missing_from_payload"], [])

    def test_all_sources_failing_still_reports_unreachable_not_ok(self):
        def boom(url, timeout=30):
            raise OSError("offline")
        with mock.patch.object(RF, "_http_get", side_effect=boom):
            snap, url, kind = RF.fetch_finals("2026-11-16", [])
        self.assertIsNone(snap)
        self.assertEqual(kind, "unreachable")


class TestSettlementTimestamp(unittest.TestCase):
    def test_identical_settlement_content_keeps_its_first_timestamp(self):
        body = {
            "finals_snapshot": "official_finals_union.json",
            "ledgers": [{"ledger": "sealed-2026-11-14.json", "games_settled": 27}],
        }
        previous = {"settled_at_utc": "2026-11-19T06:10:51+00:00", **body}
        now = datetime(2026, 11, 19, 6, 20, tzinfo=timezone.utc)

        self.assertEqual(ST.settlement_document(body, previous, now), previous)

    def test_changed_settlement_content_gets_a_new_timestamp(self):
        body = {
            "finals_snapshot": "official_finals_union.json",
            "ledgers": [{"ledger": "sealed-2026-11-14.json", "games_settled": 28}],
        }
        previous = {
            "settled_at_utc": "2026-11-19T06:10:51+00:00",
            "finals_snapshot": "official_finals_union.json",
            "ledgers": [{"ledger": "sealed-2026-11-14.json", "games_settled": 27}],
        }
        now = datetime(2026, 11, 19, 6, 20, tzinfo=timezone.utc)

        self.assertEqual(ST.settlement_document(body, previous, now), {
            "settled_at_utc": "2026-11-19T06:20:00+00:00", **body,
        })

    def test_invalid_or_naive_prior_timestamp_is_not_reused(self):
        body = {"finals_snapshot": "official_finals_union.json"}
        for stamp in ("not-a-timestamp", "2026-11-19T06:10:51"):
            previous = {"settled_at_utc": stamp, **body}
            now = datetime(2026, 11, 19, 6, 20, tzinfo=timezone.utc)
            self.assertEqual(ST.settlement_document(body, previous, now)["settled_at_utc"],
                             "2026-11-19T06:20:00+00:00")


if __name__ == "__main__":
    unittest.main()
