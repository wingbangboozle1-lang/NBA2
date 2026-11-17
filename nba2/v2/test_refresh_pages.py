"""The refresh's transport, tested against bytes the league actually served.

Every fixture in ``data/raw/page_fixtures/`` was fetched from a GitHub-hosted runner — the
same environment the scheduled job runs in — by ``.github/workflows/capture-fixtures.yml``,
which also records the URL, the HTTP status and the SHA-256 of each response in
``manifest.json``. These tests parse those bytes, so nothing here depends on the network
and nothing here is a guess about a page's shape: if nba.com changes its markup, the parse
either stops returning rows or raises, and this file fails.

Synthetic data appears only where the real season cannot be (a missing game, an
out-of-order injury index, a quarter row that does not add up). Those cases are labelled.
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
import unittest
import unittest.mock as mock
from pathlib import Path

from nba2.v2 import refresh as R

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data" / "raw" / "page_fixtures"


def fixture_html(name: str) -> str:
    """Bytes the runner captured, verified against the manifest on the way in."""
    path = FIXTURES / f"{name}.html.gz"
    if not path.exists():
        raise unittest.SkipTest(f"fixture {name} not committed on this branch")
    return gzip.decompress(path.read_bytes()).decode("utf-8", "replace")


def page(date: str, cards: list[dict]) -> str:
    """A minimal server-rendered games page carrying the official payload shape."""
    payload = {"props": {"pageProps": {
        "selectedDate": date,
        "gameCardFeed": {"modules": [{"moduleType": "list",
                                      "cards": [{"cardType": "game", "cardData": c} for c in cards]}]},
    }}}
    return ('<html><head></head><body><script id="__NEXT_DATA__" '
            f'type="application/json">{json.dumps(payload)}</script></body></html>')


def card(gid: str, home: str, away: str, hp: int | None, ap: int | None,
         status: int = 3, wins_home: int | None = None, losses_home: int | None = None,
         wins_away: int | None = None, losses_away: int | None = None,
         home_q: list[int] | None = None, away_q: list[int] | None = None) -> dict:
    return {
        "gameId": gid, "leagueId": "00", "seasonYear": R.SEASON,
        "seasonType": R.REGULAR_SEASON, "gameStatus": status,
        "gameStatusText": "Final" if status == 3 else "7:30 pm ET",
        "gameTimeEastern": "2026-11-16T19:00:00Z",
        "shareUrl": f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}",
        "homeTeam": {"teamId": "1610612738", "teamTricode": home, "teamName": home,
                     "score": hp, "wins": wins_home, "losses": losses_home,
                     "periods": [{"period": i + 1, "score": v} for i, v in enumerate(home_q or [])]},
        "awayTeam": {"teamId": "1610612753", "teamTricode": away, "teamName": away,
                     "score": ap, "wins": wins_away, "losses": losses_away,
                     "periods": [{"period": i + 1, "score": v} for i, v in enumerate(away_q or [])]},
    }


class TestFixtureProvenance(unittest.TestCase):
    def test_every_committed_fixture_matches_its_recorded_hash(self):
        manifest = FIXTURES / "manifest.json"
        if not manifest.exists():
            raise unittest.SkipTest("no fixture manifest committed on this branch")
        rows = json.loads(manifest.read_text())["rows"]
        checked = 0
        for row in rows:
            if not row.get("file"):
                continue
            path = ROOT / row["file"]
            self.assertTrue(path.exists(), f"fixture missing: {row['file']}")
            import hashlib
            raw = gzip.decompress(path.read_bytes())
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row["sha256"], row["name"])
            self.assertEqual(len(raw), row["bytes"], row["name"])
            checked += 1
        self.assertGreaterEqual(checked, 10)


class TestTeamIndex(unittest.TestCase):
    def test_standings_page_lists_thirty_clubs_with_divisions(self):
        clubs = R.parse_team_index(fixture_html("standings"))
        self.assertEqual(len(clubs), 30, "the official team list must carry 30 clubs")
        for tri, meta in clubs.items():
            self.assertEqual(len(tri), 3)
            self.assertTrue(meta["team_id"].isdigit(), tri)
            self.assertTrue(meta["division"], tri)
            self.assertEqual(meta["source_url"], R.URLS["standings_index"])
        divisions = {}
        for meta in clubs.values():
            divisions.setdefault(meta["division"], []).append(meta["tri"])
        self.assertEqual(sorted(len(v) for v in divisions.values()), [5] * 6)

    def test_a_shell_without_the_team_list_raises(self):
        with mock.patch.object(R, "http_get", return_value=b"<html></html>"):
            with self.assertRaises(RuntimeError):
                R.fetch_teams_index()


class TestDayGames(unittest.TestCase):
    DATE = "2026-11-16"

    def test_the_official_payload_parses_into_game_rows(self):
        with mock.patch.object(R, "http_get",
                               return_value=fixture_html(f"games_{self.DATE}").encode()):
            cards = R.fetch_day_games(self.DATE)
        self.assertEqual(len(cards), 8)
        for c in cards:
            self.assertTrue(c["gameId"].startswith("002"))
            self.assertEqual(len(c["gameId"]), 10)
            self.assertEqual(c["seasonType"], "Regular Season")
            self.assertEqual(c["gameStatus"], 3)
        ids = [c["gameId"] for c in cards]
        self.assertEqual(len(set(ids)), len(ids))

    def test_a_page_answering_another_date_is_refused(self):
        with mock.patch.object(R, "http_get", return_value=page("2026-11-10", []).encode()):
            with self.assertRaises(RuntimeError):
                R.fetch_day_games("2026-11-16")

    def test_a_page_without_a_payload_is_refused_not_guessed(self):
        with mock.patch.object(R, "http_get", return_value=b"<html><body>ok</body></html>"):
            with self.assertRaises(RuntimeError):
                R.fetch_day_games("2026-11-16")


class TestSlate(unittest.TestCase):
    DATES = ["2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"]

    def test_every_successful_date_query_is_recorded_even_when_no_game_is_on(self):
        empty: dict[str, str] = {}
        def fake(url, tries=3):
            date = url.split("date=")[1]
            empty[date] = url
            return page(date, []).encode()
        with mock.patch.object(R, "http_get", side_effect=fake):
            slate = R.fetch_slate(self.DATES)
        self.assertEqual(slate["covered_dates"], self.DATES)
        self.assertEqual(slate["games"], [])
        self.assertEqual(sorted(empty), sorted(self.DATES))

    def test_the_slate_window_parses_with_source_links_and_eastern_tips(self):
        def fake(url, tries=3):
            date = url.split("date=")[1]
            return fixture_html(f"future_games_{date}").encode()
        with mock.patch.object(R, "http_get", side_effect=fake):
            slate = R.fetch_slate(self.DATES)
        self.assertEqual(slate["covered_dates"], self.DATES)
        self.assertGreater(len(slate["games"]), 0)
        for g in slate["games"]:
            self.assertEqual(g["source_url"], R.URLS["games"].format(date=g["date"]))
            self.assertTrue(str(g["game_url"]).startswith("https://www.nba.com/game/"))
            self.assertTrue(g["game_id"].startswith("002"))
            self.assertRegex(g["time_et"] or "", r"^\d{1,2}:\d{2} (am|pm) ET$")
            # the arena is not printed by this page: blank and flagged, never invented
            self.assertIsNone(g["arena"])
            self.assertIn("unverified", g["arena_status"])

    def test_the_eastern_field_is_read_as_a_wall_clock_not_utc(self):
        # gameTimeEastern prints US/Eastern with a Z suffix: 19:00 there is 7:00 pm ET
        self.assertEqual(R._et_clock(card("0022600245", "BOS", "ORL", 105, 115)), "7:00 pm ET")
        self.assertEqual(R._et_clock({"gameStatusText": "7:30 PM ET"}), "7:30 pm ET")
        self.assertIsNone(R._et_clock({}))


class TestSlateGateAcceptsTheFetchedUrl(unittest.TestCase):
    TODAY = "2026-11-17"

    def slate(self, url):
        return {"covered_dates": ["2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"],
                "games": [{"date": "2026-11-17", "game_id": "0022600253",
                           "home": "TOR", "away": "NYK", "source_url": url}]}

    def test_the_games_url_the_slate_is_read_from_passes(self):
        gate = R.gate_slate(self.slate("https://www.nba.com/games?date=2026-11-17"), self.TODAY)
        self.assertTrue(gate["ok"], gate["detail"])

    def test_the_legacy_schedule_url_still_passes(self):
        gate = R.gate_slate(self.slate("https://www.nba.com/schedule?date=2026-11-17"), self.TODAY)
        self.assertTrue(gate["ok"], gate["detail"])

    def test_another_date_another_host_or_no_date_still_fails(self):
        for url in ("https://www.nba.com/games?date=2026-11-18",
                    "https://example.com/games?date=2026-11-17",
                    "https://www.nba.com/games",
                    "https://www.nba.com/standings?date=2026-11-17"):
            gate = R.gate_slate(self.slate(url), self.TODAY)
            self.assertFalse(gate["ok"], url)


class TestFinals(unittest.TestCase):
    def test_finals_carry_quarters_that_sum_to_the_printed_final(self):
        dates = ["2026-11-14", "2026-11-15", "2026-11-16"]
        def fake(url, tries=3):
            return fixture_html(f"games_{url.split('date=')[1]}").encode()
        with mock.patch.object(R, "http_get", side_effect=fake):
            finals = R.fetch_finals(dates)
        self.assertEqual(sum(finals["finals_by_date"].values()), len(finals["records"]))
        for r in finals["records"]:
            self.assertTrue(r["source_url"].startswith("https://www.nba.com/game/"))
            if r["home_q"]:
                self.assertEqual(sum(r["home_q"]), r["home_pts"])
                self.assertEqual(sum(r["away_q"]), r["away_pts"])
            self.assertEqual(r["ot_periods"], max(0, len(r["home_q"] or []) - 4))

    def test_a_quarter_row_that_does_not_add_up_is_refused(self):
        bad = card("0022600245", "BOS", "ORL", 105, 115,
                   home_q=[10, 10, 10, 10], away_q=[10, 10, 10, 10])
        def fake(url, tries=3):
            return page("2026-11-16", [bad]).encode()
        with mock.patch.object(R, "http_get", side_effect=fake):
            with self.assertRaises(RuntimeError):
                R.fetch_finals(["2026-11-16"])


class TestInjuryIndex(unittest.TestCase):
    HTML = """
    <a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_01_00PM.pdf">old</a>
    <a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_11_00AM.pdf">older</a>
    <a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_01_30PM.pdf">newest</a>
    """

    def test_newest_is_chosen_by_the_stamp_in_the_filename_not_by_position(self):
        self.assertEqual(R.newest_release_from_index(self.HTML),
                         "https://ak-static.cms.nba.com/referee/injury/"
                         "Injury-Report_2026-11-17_01_30PM.pdf")

    def test_a_stamped_link_wins_over_an_unstamped_one(self):
        html = self.HTML + '<a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report.pdf"></a>'
        self.assertTrue(R.newest_release_from_index(html).endswith("Injury-Report_2026-11-17_01_30PM.pdf"))

    def test_the_official_index_parses_and_stamps_both_times(self):
        with mock.patch.object(R, "http_get", return_value=fixture_html("injury_index").encode()):
            release = R.fetch_newest_injury_release()
        self.assertTrue(release["pdf_url"].endswith(".pdf"))
        self.assertRegex(release["revision_time_et"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} (AM|PM) ET$")
        self.assertTrue(release["retrieval_time_utc"].endswith("+00:00"))


class TestTeamStatsSurface(unittest.TestCase):
    def test_unreadable_pages_are_recorded_unavailable_without_invented_rows(self):
        def fake(url, tries=3):
            for key in ("team_traditional", "team_advanced", "team_opponent"):
                if url == R.URLS[key].format(season=R.SEASON):
                    return fixture_html(key).encode()
            raise AssertionError(url)
        with mock.patch.object(R, "http_get", side_effect=fake):
            pages = R.fetch_team_stats()
        self.assertEqual(set(pages), {"team_traditional", "team_advanced", "team_opponent"})
        for key, doc in pages.items():
            self.assertEqual(doc["status"], "unavailable", key)
            self.assertTrue(doc["source_url"].startswith("https://www.nba.com/stats/teams/"))
            self.assertNotIn("rows", doc)
            self.assertNotIn("headers", doc)


class TestDerivedStandings(unittest.TestCase):
    """Synthetic season — the derivation is what is under test, not the 2026-27 table."""

    TODAY = "2026-11-21"

    def build(self, rounds: int = 10, lost_dates: set[str] | None = None):
        """A league where every club plays once a round; records printed post-game."""
        clubs = {"ATL": "Southeast", "BOS": "Atlantic", "BKN": "Atlantic", "CHA": "Southeast",
                 "CHI": "Central", "CLE": "Central", "DAL": "Southwest", "DEN": "Northwest",
                 "DET": "Central", "GSW": "Pacific", "HOU": "Southwest", "IND": "Central",
                 "LAC": "Pacific", "LAL": "Pacific", "MEM": "Southwest", "MIA": "Southeast",
                 "MIL": "Central", "MIN": "Northwest", "NOP": "Southwest", "NYK": "Atlantic",
                 "OKC": "Northwest", "ORL": "Southeast", "PHI": "Atlantic", "PHX": "Pacific",
                 "POR": "Northwest", "SAC": "Pacific", "SAS": "Southwest", "TOR": "Atlantic",
                 "UTA": "Northwest", "WAS": "Southeast"}
        tris = sorted(clubs)
        games = []                      # (date, home, away, home_won)
        gid = 226000000
        for r in range(rounds):
            date = (dt.date.fromisoformat(self.TODAY) - dt.timedelta(days=rounds - r)).isoformat()
            home, away = tris[:(len(tris) // 2)], tris[(len(tris) // 2):]
            rotated = tris[r % len(tris):] + tris[:r % len(tris)]
            home, away = rotated[0::2], rotated[1::2]
            for h, a in zip(home, away):
                gid += 1
                games.append((date, h, a, (gid % 3) != 0))

        pages = {}
        for date in {g[0] for g in games} | {
                (dt.date.fromisoformat(self.TODAY) - dt.timedelta(days=i)).isoformat()
                for i in range(1, R.SEASON_SCAN_DAYS + 1)}:
            cards = []
            for d, h, a, home_won in games:
                if d != date:
                    continue
                through = [g for g in games if g[0] <= date and (h in (g[1], g[2]))]
                hw = sum(1 for g in through if (g[3] and g[1] == h) or (not g[3] and g[2] == h))
                through_a = [g for g in games if g[0] <= date and (a in (g[1], g[2]))]
                aw = sum(1 for g in through_a if (g[3] and g[1] == a) or (not g[3] and g[2] == a))
                cards.append(card(f"0022{gid:06d}"[:10], h, a, 101 if home_won else 99,
                                  99 if home_won else 101, wins_home=hw,
                                  losses_home=len(through) - hw, wins_away=aw,
                                  losses_away=len(through_a) - aw))
            pages[date] = page(date, cards).encode()
        for date in lost_dates or ():        # a date whose page came back empty
            pages[date] = page(date, []).encode()

        expected = {}
        for tri in tris:
            played = [g for g in games if tri in (g[1], g[2])]
            w = sum(1 for g in played if (g[3] and g[1] == tri) or (not g[3] and g[2] == tri))
            expected[tri] = (w, len(played) - w)

        index = "".join(
            f'<div class="NavTeamList_ntlDivTitle__x">{div}</div>'
            f'<a data-content="{tri}" data-text="{tri} club">'
            f'<img src="https://cdn.nba.com/logos/nba/1610612738/primary/L/logo.svg"/></a>'
            for tri, div in clubs.items())

        def fake(url, tries=3):
            if url == R.URLS["standings_index"]:
                return index.encode()
            date = url.split("date=")[1]
            return pages.get(date, page(date, []).encode())
        return fake, expected, games

    def test_derived_table_matches_the_records_the_league_prints(self):
        fake, expected, _ = self.build()
        with mock.patch.object(R, "http_get", side_effect=fake):
            standings = R.fetch_standings(self.TODAY)
        rows = {r["tri"]: r for r in standings["rows"]}
        self.assertEqual(len(rows), 30)
        for tri, (w, l) in expected.items():
            self.assertEqual((rows[tri]["w"], rows[tri]["l"]), (w, l), tri)
        self.assertEqual(sum(r["w"] for r in standings["rows"]),
                         sum(r["l"] for r in standings["rows"]))
        self.assertTrue(standings["derived"])
        self.assertEqual(standings["games_counted"], 150)

    def test_splits_last_ten_and_streak_are_computed_from_the_same_finals(self):
        fake, expected, games = self.build(rounds=12)
        with mock.patch.object(R, "http_get", side_effect=fake):
            standings = R.fetch_standings(self.TODAY)
        rows = {r["tri"]: r for r in standings["rows"]}
        for tri, row in rows.items():
            played = [g for g in games if tri in (g[1], g[2])]
            hw = sum(1 for g in played if g[1] == tri and g[3])
            hl = sum(1 for g in played if g[1] == tri and not g[3])
            self.assertEqual(row["home"], f"{hw}-{hl}", tri)
            last10 = [((g[3] and g[1] == tri) or (not g[3] and g[2] == tri)) for g in played][-10:]
            self.assertEqual(row["last10"], f"{sum(last10)}-{len(last10) - sum(last10)}", tri)
            self.assertRegex(row["streak"], r"^(W|L) \d+$")
        # the conference column stays blank: the league prints divisions, not conferences
        self.assertTrue(all(r["conf"] is None for r in standings["rows"]))
        self.assertTrue(all("unverified" in r["conf_status"] for r in standings["rows"]))

    def test_a_game_day_the_scan_lost_is_refused_rather_than_published(self):
        # the league still prints each club's record beside later games, so a date that
        # silently answered empty leaves the derived table short and the check must fail
        fake, _, games = self.build()
        lost = sorted({g[0] for g in games})[3]
        fake2, _, _ = self.build(lost_dates={lost})
        with mock.patch.object(R, "http_get", side_effect=fake2):
            with self.assertRaises(RuntimeError):
                R.fetch_standings(self.TODAY)


if __name__ == "__main__":
    unittest.main()
