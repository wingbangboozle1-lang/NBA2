"""Unit tests for nba2.v5: the gates, the arithmetic and the no-inference rules.

Run with ``python -m unittest nba2.v5.test_v5 -v``.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from . import check as CH
from . import model as M
from . import transcript as T

V5 = T.V5


def _games() -> list[dict]:
    return T.games()


def _rows() -> list[dict]:
    return T.player_rows()


class TestTranscripts(unittest.TestCase):
    def test_transcripts_exist(self):
        for p in T.TRANSCRIPTS:
            with self.subTest(p=p.name):
                self.assertTrue(p.exists(), f"missing transcript {p}")
                doc = json.loads(p.read_text())
                self.assertEqual(doc["schema"], "nba2.v5.gamebook-transcript.v1")
                self.assertEqual(doc["source_class"], "official")
                self.assertTrue(doc["retrieved_window_utc"])

    def test_every_game_has_a_url_and_a_final(self):
        for g in _games():
            with self.subTest(g=g["matchup"]):
                self.assertTrue(g["source_url"].startswith("https://statsdmz.nba.com/pdfs/"))
                self.assertIsInstance(g["final"]["away"], int)
                self.assertIsInstance(g["final"]["home"], int)
                self.assertIn(g["away"], g["teams"])
                self.assertIn(g["home"], g["teams"])

    def test_every_player_row_carries_a_source(self):
        for r in _rows():
            with self.subTest(f'{r["matchup"]} {r["player"]}'):
                self.assertTrue(r["source_url"])
                self.assertTrue(r["retrieved_window_utc"])
                self.assertIn(r["team"], T.TEAM_NAME.values())

    def test_no_row_invents_a_value(self):
        """A row with no minutes and no stats must say why; nothing is back-filled."""
        for r in _rows():
            with self.subTest(f'{r["matchup"]} {r["player"]}'):
                if not r["played"]:
                    self.assertTrue(r["status"], "a non-playing row must state why")
                    for c in ("min_sec", "pts", "reb", "ast"):
                        self.assertIsNone(r[c], f"{c} must be blank for a non-playing row")
                if r["min"] is None and r["played"]:
                    self.assertTrue(r["min_blank_reason"],
                                    "a playing row with blank minutes needs a reason")
                if r["reb"] is None and r["played"]:
                    self.assertTrue(r["reb_blank_reason"],
                                    "a playing row with blank rebounds needs a reason")


class TestGates(unittest.TestCase):
    def setUp(self):
        self.rows = _rows()
        self.games = _games()

    def test_all_hard_gates_pass(self):
        res = CH.run()
        self.assertTrue(res["publishable"],
                        f"hard gate failures: "
                        f"{[g['id'] for g in res['gates'] if g['hard'] and not g['ok']]}")

    def test_quarters_sum(self):
        g = CH.gate_quarters(self.games)
        self.assertTrue(g["ok"], g["failures"])
        self.assertEqual(g["tested"], 27)   # 28 club rows, one blank by policy (F-V5-04)
        self.assertEqual(g["passed"], 27)

    def test_player_points_sum(self):
        g = CH.gate_player_points(self.rows, self.games)
        self.assertTrue(g["ok"], g["failures"])
        self.assertEqual(g["tested"], 28)

    def test_points_identity_holds_for_every_row(self):
        g = CH.gate_points_identity(self.rows)
        self.assertTrue(g["ok"], g["failures"])
        self.assertGreater(g["tested"], 250)

    def test_cross_source_agreement(self):
        g = CH.gate_cross_source(self.games)
        self.assertTrue(g["ok"], g["failures"])
        self.assertEqual(g["tested"], 11)   # 14 games, 3 were 'not final' in the feed

    def test_blank_cells_always_carry_a_reason(self):
        g = CH.gate_provenance(self.rows)
        self.assertTrue(g["ok"], g["failures"])

    def test_coverage_is_all_thirty_clubs(self):
        g = CH.gate_coverage(self.rows)
        self.assertTrue(g["ok"], g["failures"])
        self.assertEqual(g["passed"], 30)

    def test_gate_detects_a_deliberate_corruption(self):
        """A one-point edit to a transcript must fail the points-sum gate."""
        rows = _rows()
        victim = next(r for r in rows if r["transcript"].startswith("gamebooks_")
                      and r["played"] and r["pts"])
        victim["pts"] += 1
        g = CH.gate_player_points(rows, _games())
        self.assertFalse(g["ok"])
        self.assertTrue(any(victim["matchup"] in f and victim["team"] in f
                            for f in g["failures"]), g["failures"])

    def test_gate_detects_a_dropped_row(self):
        rows = _rows()
        keep = [r for r in rows if not (r["transcript"].startswith("gamebooks_")
                                        and r["player"] == "Shai Gilgeous-Alexander")]
        self.assertEqual(len(rows) - len(keep), 1)
        g = CH.gate_player_points(keep, _games())
        self.assertFalse(g["ok"])


class TestModel(unittest.TestCase):
    def setUp(self):
        self.res = M.build()

    def test_result_rows_match_the_games(self):
        self.assertEqual(len(self.res["results"]), 14)
        for r in self.res["results"]:
            self.assertIn(r["matchup"], {f"{r['away']}@{r['home']}"})

    def test_overtime_game_is_recorded(self):
        ot = [r for r in self.res["results"] if r["ot_periods"]]
        self.assertEqual(len(ot), 1)
        self.assertEqual(ot[0]["matchup"], "NYK@TOR")
        self.assertEqual(ot[0]["ot_quarters"], {"away": [17], "home": [13]})
        self.assertEqual(sum(ot[0]["away_quarters"]) + 17, ot[0]["away_pts"])

    def test_blank_quarters_are_not_filled(self):
        dal = next(r for r in self.res["results"] if r["matchup"] == "DAL@BOS")
        self.assertIsNone(dal["away_quarters"])
        self.assertIn("F-V5-04", dal["quarters_blank_reason"])
        self.assertEqual(dal["away_pts"], 94)
        self.assertEqual(sum(r["pts"] or 0 for r in self.res["rows"]
                             if r["game_id"] == dal["game_id"] and r["team"] == "DAL"), 94)

    def test_minutes_shares_sum_to_at_most_one(self):
        for m in self.res["minutes"]:
            with self.subTest(f'{m["matchup"]} {m["team"]}'):
                self.assertLessEqual(m["top8_share"], 1.0)
                for p in m["top8"]:
                    self.assertGreater(p["share"], 0)

    def test_replacement_requires_both_a_played_and_a_missed_game(self):
        for r in self.res["replacement"]:
            with self.subTest(f'{r["team"]} {r["player"]}'):
                self.assertGreaterEqual(r["games_played"], 1)
                self.assertGreaterEqual(r["games_out"], 1)
                self.assertTrue(r["source_urls"])

    def test_spelling_disagreements_are_flagged_not_merged(self):
        pairs = M.suspect_spelling_pairs(self.res["rows"])
        names = {p["name_a"] for p in pairs} | {p["name_b"] for p in pairs}
        self.assertIn("Marcus Sassar", names)
        self.assertIn("Marcus Sasser", names)
        # … and they stay out of the replacement table.
        for r in self.res["replacement"]:
            self.assertNotIn(r["player"], names)

    def test_suffix_fold_is_declared(self):
        self.assertEqual(M.norm("P.J. Washington Jr."), M.norm("P.J. Washington"))
        self.assertEqual(M.norm("Dončić"), M.norm("Doncic"))
        folded = {f["key"] for f in M.folded_names(self.res["rows"])}
        self.assertIn("pj washington", folded)

    def test_injury_join_reports_its_own_coverage(self):
        inj = self.res["injury"]
        # The count is whatever the newest committed release holds, not a hardcoded 70:
        # another session superseded the 09:30 AM filing with the 01:00 PM one (83 rows).
        self.assertGreaterEqual(inj["n_report_rows"], 70)
        self.assertEqual(inj["stamp"], max(
            m["report_stamp_et"] for m in M.injury_rows()))
        self.assertEqual(inj["n_matched"] + inj["n_unmatched"], inj["n_report_rows"])
        self.assertTrue(inj["index_url"].startswith("https://official.nba.com"))
        for u in inj["unmatched"]:
            self.assertTrue(u["reason_not_matched"])
        for m in inj["matched"]:
            self.assertTrue(m["logs"])
            self.assertTrue(m["last_source_url"])

    def test_an_out_player_is_never_given_minutes(self):
        for m in self.res["injury"]["matched"]:
            if m["last_played"]:
                continue
            self.assertIsNone(m["last_min"])
            self.assertIsNone(m["last_pts"])

    def test_dnp_rows_are_not_counted_as_absences(self):
        """A player printed as DNP must not appear as 'out' in the replacement table."""
        dnp = {(r["team"], M.norm(r["player"])) for r in self.res["rows"]
               if r["status"] and r["status"].startswith(("DNP", "DND", "NWT"))
               and r["transcript"].startswith("gamebooks_")}
        out = {(r["team"], M.norm(r["player"])) for r in self.res["replacement"]}
        self.assertFalse(dnp & out, f"{sorted(dnp & out)} printed a DNP row yet is listed out")


class TestPublished(unittest.TestCase):
    def test_flag_source_urls_are_well_formed(self):
        """A flag row links to a real gamebook path: /pdfs/<YYYYMMDD>/<YYYYMMDD>_<M>_book.pdf."""
        from . import publish as P
        pat = re.compile(r"^https://statsdmz\.nba\.com/pdfs/(\d{8})/\1_[A-Z]{6}_book\.pdf$")
        for fid, sev, where, url, wrong, published in P.FLAGS:
            with self.subTest(flag=fid):
                # Two flags are about the injury report, so they legitimately point at the
                # official injury index rather than a gamebook.
                if url == M.INJURY_INDEX_URL:
                    continue
                self.assertTrue(pat.match(url), f"{fid} links to {url!r}")

    def test_pages_exist_and_are_wired(self):
        site = T.ROOT / "site"
        for name in ("result-feed-v5.html", "playerlogs-full.html",
                     "rotation-replacement.html", "v5-verify.html"):
            with self.subTest(page=name):
                doc = (site / name).read_text()
                self.assertIn("</nav>", doc)
                self.assertIn("assets/site.css", doc)

    def test_data_files_exist_and_parse(self):
        for name in ("results_union.json", "player_logs_union.json", "rotation.json",
                     "injury_join.json", "checks.json"):
            with self.subTest(f=name):
                doc = json.loads((V5 / name).read_text())
                self.assertIn("schema", doc)
                self.assertIn("session", doc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
