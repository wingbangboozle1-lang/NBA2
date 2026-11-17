"""Tests for the v6 tree. Standard library only, no network.

Every test is written against committed files, so a reader can run it and get the same
answer. Nothing here asserts a number that came from the network.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from nba2.v6 import check as CH
from nba2.v6 import flags as FL
from nba2.v6.flags import FLAGS
from nba2.v6 import inventory as INV
from nba2.v6 import market_prior as MP
from nba2.v6 import nav as NAV
from nba2.v6 import player_coverage as PC
from nba2.v6 import publish as PUB
from nba2.v6 import results_coverage as RC
from nba2.v6.common import ROOT, SITE, V6

PDF_URL_RE = re.compile(
    r"^https://ak-static\.cms\.nba\.com/referee/injury/Injury-Report_\d{4}-\d{2}-\d{2}"
    r"_\d{2}_\d{2}(AM|PM)\.pdf$")
BOOK_URL_RE = re.compile(r"^https://statsdmz\.nba\.com/pdfs/(\d{8})/\1_[A-Z]{6}_book\.pdf$")


class TestInventory(unittest.TestCase):
    def setUp(self):
        self.rels = INV.injury_releases()

    def test_every_release_url_is_a_well_formed_official_pdf(self):
        for r in self.rels:
            self.assertRegex(r["url"], PDF_URL_RE, msg=r["filename"])

    def test_every_release_has_a_parsed_revision_stamp(self):
        for r in self.rels:
            self.assertIsNotNone(r["stamp_et"], msg=r["filename"])
            self.assertRegex(r["stamp_et"], r"^\d{2}:\d{2} (AM|PM) ET$")
            self.assertRegex(r["date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_releases_are_unique_by_url(self):
        urls = [r["url"] for r in self.rels]
        self.assertEqual(len(urls), len(set(urls)))

    def test_archived_pdfs_are_in_the_inventory(self):
        on_disk = {p.name for p in INV.PDF_DIR.glob("Injury-Report_*.pdf")}
        in_inv = {r["filename"] for r in self.rels}
        self.assertEqual(on_disk - in_inv, set(), "an archived PDF is not inventoried")

    def test_stored_digests_recompute(self):
        import hashlib
        for r in self.rels:
            if not r["bytes_stored"]:
                continue
            p = ROOT / r["pdf_path"]
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), r["pdf_sha256"])
            self.assertEqual(p.stat().st_size, r["pdf_bytes"])

    def test_no_release_is_invented(self):
        """A release only exists if something committed cites it or its bytes are stored."""
        for r in self.rels:
            self.assertTrue(r["cited_in"] or r["bytes_stored"],
                            msg=f"{r['filename']} has neither a citation nor stored bytes")

    def test_endpoints_register_is_measured_not_assumed(self):
        ep = INV.endpoints()
        self.assertTrue(ep["rows"])
        self.assertIsNotNone(ep["probed_at_utc"])
        for r in ep["rows"]:
            self.assertTrue(r["url"].startswith("https://"))
        # the two scoreboard endpoints are the ones that block settlement; assert the fact
        by_name = {r["name"]: r for r in ep["rows"]}
        self.assertFalse(by_name["scoreboard_cdn"]["ok"])
        self.assertFalse(by_name["scoreboard_stats"]["ok"])
        self.assertTrue(by_name["schedule"]["ok"])
        self.assertTrue(by_name["gamebook_pdf"]["ok"])


class TestResultsCoverage(unittest.TestCase):
    def setUp(self):
        self.doc = RC.build()

    def test_coverage_arithmetic_per_date(self):
        for r in self.doc["rows"]:
            self.assertLessEqual(r["n_finals_committed"], r["n_scheduled"])
            self.assertLessEqual(r["n_graded"], r["n_finals_committed"])
            self.assertEqual(r["n_missing_final"] + r["n_finals_committed"],
                             r["n_scheduled"])

    def test_every_game_row_has_an_official_url(self):
        for g in self.doc["games"]:
            urls = [u for u in (g.get("source_url"), g.get("gamebook_url")) if u]
            self.assertTrue(urls, msg=g["game_id"])
            self.assertTrue(any("nba.com" in u for u in urls), msg=g["game_id"])

    def test_gamebook_urls_are_well_formed(self):
        for g in self.doc["games"]:
            if g.get("gamebook_url"):
                self.assertRegex(g["gamebook_url"], BOOK_URL_RE, msg=g["game_id"])

    def test_a_final_without_quarters_is_blank_not_zero(self):
        for g in self.doc["games"]:
            if g["away_pts"] is None:
                self.assertIsNone(g["away_quarters"])
                self.assertIsNone(g["home_quarters"])

    def test_overtime_periods_are_included_in_the_sum(self):
        ot = [g for g in self.doc["games"] if g.get("ot_periods")]
        self.assertTrue(ot, "expected at least one overtime game in the committed feed")
        for g in ot:
            self.assertEqual(g["quarter_verdict"], "quarters sum to the final",
                             msg=f"{g['game_id']}: {g['quarter_detail']}")

    def test_no_two_committed_feeds_disagree(self):
        conflicts = [g for g in self.doc["games"] if g.get("conflicts")]
        self.assertEqual(conflicts, [])

    def test_the_1116_games_are_now_complete(self):
        """PR #115 (session arena/aa1d3c07-nba2) captured and settled the 11/16 finals."""
        row = next(r for r in self.doc["rows"] if r["date"] == "2026-11-16")
        self.assertEqual(row["n_scheduled"], 8)
        self.assertEqual(row["n_finals_committed"], 8)
        self.assertEqual(row["n_graded"], 8)
        self.assertEqual(row["status"], "complete")

    def test_a_date_that_has_not_ended_is_not_reported_as_a_gap(self):
        for d in ("2026-11-17", "2026-11-18", "2026-11-19"):
            row = next(r for r in self.doc["rows"] if r["date"] == d)
            self.assertEqual(row["status"], "not ended", msg=d)
            self.assertEqual(row["n_finals_committed"], 0)
            self.assertIn("has not ended", row["reason"])

    def test_the_prequest_1113_games_are_reported_as_unsettleable_not_missing(self):
        row = next(r for r in self.doc["rows"] if r["date"] == "2026-11-13")
        self.assertEqual(row["n_finals_committed"], 9)
        self.assertEqual(row["n_graded"], 0)
        self.assertIn("never pre-registered", row["reason"])


class TestPlayerCoverage(unittest.TestCase):
    def setUp(self):
        self.doc = PC.build()

    def test_join_is_arithmetically_closed(self):
        self.assertEqual(self.doc["n_matched"] + self.doc["n_unmatched"],
                         self.doc["n_report_rows"])

    def test_coverage_recomputes_to_the_same_number_v5_published(self):
        self.assertTrue(self.doc["coverage_matches_v5"])

    def test_every_report_row_carries_the_official_pdf(self):
        for r in self.doc["matched"] + self.doc["unmatched"]:
            self.assertRegex(r["report_url"], PDF_URL_RE)

    def test_no_player_appears_in_both_lists(self):
        m = {(r["player"], r["team"]) for r in self.doc["matched"]}
        u = {(r["player"], r["team"]) for r in self.doc["unmatched"]}
        self.assertEqual(m & u, set())

    def test_coverage_is_published_as_measured_not_rounded_up(self):
        self.assertLess(self.doc["coverage"], 1.0,
                        "coverage is partial; claiming 100% would be a fabrication")


class TestMarketPrior(unittest.TestCase):
    def setUp(self):
        self.doc = MP.build()

    def test_weight_is_blank_because_no_closing_line_exists(self):
        self.assertIsNone(self.doc["market_log_loss"])
        self.assertIsNone(self.doc["w_market"])
        self.assertIn("no closing line", self.doc["w_market_reason"])

    def test_no_blended_line_is_published(self):
        self.assertFalse(self.doc["blended_margin_published"])

    def test_weight_is_half_when_both_inputs_are_equal(self):
        self.assertAlmostEqual(MP.weight(0.60, 0.60), 0.5, places=9)

    def test_weight_is_monotone_in_the_markets_log_loss(self):
        prev = None
        for lm in (0.70, 0.68, 0.66, 0.64, 0.62, 0.60, 0.58):
            w = MP.weight(0.61, lm)
            if prev is not None:
                self.assertGreater(w, prev)
            prev = w

    def test_a_forecaster_worse_than_a_coin_flip_gets_no_weight(self):
        self.assertEqual(MP.weight(0.61, 0.75), 0.0)

    def test_weight_is_none_when_either_input_is_unmeasured(self):
        self.assertIsNone(MP.weight(None, 0.60))
        self.assertIsNone(MP.weight(0.60, None))

    def test_the_sign_of_every_measurement_is_published_either_way(self):
        """A measurement worse than a coin flip is a finding, not a build failure."""
        for m in self.doc["measurements"]:
            if m["log_loss"] is None or m["log_loss_baseline"] is None:
                continue
            want = round(m["log_loss_baseline"] - m["log_loss"], 4)
            self.assertEqual(m["skill_vs_baseline"], want, msg=m["id"])
            # whichever way it goes, the page must say so rather than stay silent
            self.assertIsNotNone(m["log_loss"])

    def test_a_worse_than_coin_flip_model_hands_the_rule_to_the_market(self):
        mp = self.doc
        if mp["model_beats_coin_flip"]:
            self.skipTest("the model currently beats a coin flip; this asserts the "
                          "behaviour when it does not")
        self.assertEqual(mp["model_skill_vs_coin"], 0.0)
        self.assertIsNone(mp["w_market"])
        for g in mp["sensitivity_grid"]:
            if g["market_skill_vs_coin"] > 0:
                self.assertEqual(g["w_market"], 1.0,
                                 msg="with no measured model skill, any market skill "
                                     "must take the whole weight")


class TestGates(unittest.TestCase):
    def test_all_gates_pass(self):
        res = CH.run()
        failed = [g for g in res["gates"] if not g["ok"]]
        self.assertEqual(failed, [], msg=json.dumps(failed, indent=1))
        self.assertTrue(res["publishable"])

    def test_gates_are_a_measurement_not_an_assertion(self):
        res = CH.run()
        for g in res["gates"]:
            self.assertIsInstance(g["tested"], int)
            self.assertLessEqual(g["passed"], g["tested"])
            self.assertTrue(g["detail"])


class TestNavigation(unittest.TestCase):
    def test_every_category_page_exists(self):
        for _title, _blurb, names in NAV.CATEGORIES:
            for n in names:
                self.assertTrue((SITE / f"{n}.html").exists(), msg=f"{n}.html missing")

    def test_every_published_page_is_in_some_category(self):
        assigned = {f"{n}.html" for _t, _b, names in NAV.CATEGORIES for n in names}
        missing = sorted(p.name for p in SITE.glob("*.html") if p.name not in assigned)
        self.assertEqual(missing, [], msg=f"pages no category claims: {missing}")

    def test_no_two_categories_claim_the_same_page(self):
        seen = {}
        for title, _b, names in NAV.CATEGORIES:
            for n in names:
                self.assertNotIn(f"{n}.html", seen,
                                 msg=f"{n}.html claimed by {seen.get(n)} and {title}")
                seen[f"{n}.html"] = title

    def test_nav_blurbs_do_not_leak_a_bet_marker_onto_the_projection_surface(self):
        # G-V4-8 scans projection.html for bet vocabulary. The nav is on every page, so a
        # category blurb containing "stake" would mix the two surfaces (brief item 6).
        BET_MARKERS = re.compile(r"(stake|kelly|edge_vs_market|market price|\bedge\b)", re.I)
        for title, blurb, _names in NAV.CATEGORIES:
            for text in (title, blurb):
                self.assertIsNone(BET_MARKERS.search(text),
                                  msg=f"bet vocabulary in nav text: {text!r}")

    def test_projection_and_bet_are_separate_categories(self):
        titles = [t for t, _b, _n in NAV.CATEGORIES]
        self.assertIn("Projection — safe to publish", titles)
        self.assertIn("Bet surface — gated", titles)


class TestPublishedPages(unittest.TestCase):
    PAGES = [n for n, _l in PUB.V6_NAV]

    def test_every_v6_page_is_written_and_well_formed(self):
        for name in self.PAGES:
            p = SITE / name
            self.assertTrue(p.exists(), msg=name)
            doc = p.read_text()
            self.assertIn('<link rel="stylesheet" href="assets/site.css">', doc)
            self.assertIn("<nav>", doc)
            for token in ("TODO", "TBD", "lorem ipsum", "XXX"):
                self.assertNotIn(token, doc, msg=f"{name}: placeholder {token}")

    def test_every_page_links_to_the_others(self):
        for name in self.PAGES:
            doc = (SITE / name).read_text()
            m = re.search(r"<nav>(.*?)</nav>", doc, re.S)
            hrefs = set(re.findall(r'href="([^"]+)"', m.group(1)))
            for other in self.PAGES:
                self.assertIn(other, hrefs, msg=f"{name} does not link to {other}")

    def test_no_broken_local_link(self):
        for name in self.PAGES:
            doc = (SITE / name).read_text()
            for href in re.findall(r'(?:href|src)="([^"#][^"]*)"', doc):
                if href.startswith(("http://", "https://", "mailto:", "//", "data:")):
                    continue
                self.assertTrue((SITE / href.split("?")[0]).exists(),
                                msg=f"{name}: broken local link {href}")

    def test_data_files_are_written(self):
        for name in ("injury_archive.json", "results_coverage.json", "player_coverage.json",
                     "market_prior.json", "endpoints.json", "checks.json"):
            self.assertTrue((V6 / name).exists(), msg=name)
            json.loads((V6 / name).read_text())


if __name__ == "__main__":
    unittest.main()


class TestFlags(unittest.TestCase):
    """The flag prose is computed from data/ so that it cannot go stale."""

    def setUp(self):
        from nba2.v6 import flags as FL
        self.by_id = {f[0]: f for f in FL.FLAGS}
        from nba2.v6 import inventory as INV
        from nba2.v6 import player_coverage as PC
        from nba2.v6 import market_prior as MP
        self.rel = INV.injury_releases()
        self.pc = PC.build()
        self.mp = MP.build()
        self.st = MP.settlement_stats()

    def test_every_flag_id_is_unique_and_well_formed(self):
        ids = [f[0] for f in FLAGS]
        self.assertEqual(len(ids), len(set(ids)))
        for fid in ids:
            self.assertRegex(fid, r"^F-F5-\d\d$", msg=fid)

    def test_the_injury_archive_flag_counts_come_from_the_inventory(self):
        text = self.by_id["F-F5-03"][3]
        self.assertIn(str(len(self.rel)), text)
        self.assertIn(str(sum(1 for r in self.rel if not r.get("bytes_stored"))), text)

    def test_the_player_coverage_flag_counts_come_from_the_join(self):
        text = self.by_id["F-F5-05"][3]
        self.assertIn(str(self.pc["n_report_rows"]), text)
        self.assertIn(str(self.pc["n_matched"]), text)
        self.assertIn(f"{self.pc['coverage']:.1%}", text)

    def test_the_coin_flip_flag_counts_come_from_the_settled_ledger(self):
        text = self.by_id["F-F5-08"][3]
        self.assertIn(str(self.st["n_distinct_games_graded"]), text)
        self.assertIn(str(self.mp["model_log_loss"]), text)
        self.assertIn(str(self.mp["baseline_l0"]), text)

    def test_the_market_prior_flag_quotes_every_measured_log_loss(self):
        text = self.by_id["F-F5-04"][4]
        for m in self.mp["measurements"]:
            if m["log_loss"] is None:
                continue
            self.assertIn(str(m["log_loss"]), text, msg=m["id"])

    def test_every_flag_names_a_place_a_reviewer_can_check_it(self):
        for fid, _sev, url, wrong, instead, where in FLAGS:
            self.assertTrue(wrong.strip(), msg=fid)
            self.assertTrue(instead.strip(), msg=fid)
            self.assertTrue(where.strip(), msg=fid)
            self.assertTrue(url.startswith("https://"), msg=fid)

    def test_no_flag_hardcodes_a_coverage_number_that_the_data_contradicts(self):
        """A transcribed count would silently go wrong the next time data/ moves."""
        stale = {"83 players", "26.5%", "22 of the 83", "0.6088 over 14",
                 "twelve of the sixteen", "thirteen of the seventeen"}
        for fid, _sev, _url, wrong, instead, _where in FLAGS:
            for s in stale:
                self.assertNotIn(s, (wrong + instead).lower(), msg=f"{fid}: {s!r}")
