"""Invariant tests: the rules that stop this site from lying.

The site's whole claim is "no unsourced value, blanks are explained, numbers are reproducible",
so those are tested directly, including the failure paths (a rule that cannot fail is decoration).
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from nba2 import config
from nba2.provenance import (BLOCKED_ALLOWED_FIELDS, Src, all_flags, flag, make_row,
                             register_source, SOURCES)
from nba2.models import lines as LN
from nba2.models import ratings as RT
from nba2.models import injuries as INJ
from nba2.models import ledger as LD

ROOT = Path(__file__).resolve().parents[2]


class TestProvenanceRules(unittest.TestCase):
    def test_source_is_mandatory(self):
        with self.assertRaises(KeyError):
            make_row("x", "no_such_source", (), a=1)

    def test_blocked_source_rejects_values(self):
        register_source("t_blocked", "test blocked", "", Src.BLOCKED, "test")
        with self.assertRaises(ValueError) as cm:
            make_row("x", "t_blocked", ["FLAG-T-1"], spread=-3.5)
        self.assertIn("BLOCKED", str(cm.exception))

    def test_blocked_source_allows_none_and_meta(self):
        register_source("t_blocked2", "test blocked", "", Src.BLOCKED, "test")
        r = make_row("x", "t_blocked2", ["FLAG-T-2"], spread=None, status="BLOCKED — no feed")
        self.assertIsNone(r.values["spread"])
        self.assertEqual(r.flags, ["FLAG-T-2"])

    def test_third_party_needs_a_flag(self):
        with self.assertRaises(ValueError):
            make_row("x", "bref_standings", [], srs=-4.1)

    def test_blank_cell_must_be_explained(self):
        with self.assertRaises(ValueError):
            make_row("x", "nba_schedule", [], time_et=None, arena="Madison Square Garden")

    def test_verified_flag_matches_class(self):
        register_source("t_off", "test official", "https://www.nba.com/schedule", Src.OFFICIAL, "")
        r = make_row("x", "t_off", [], a=1)
        self.assertTrue(r.as_dict()["verified"])
        self.assertFalse(SOURCES["bref_standings"].cls == Src.OFFICIAL)

    def test_rows_serialise_to_json(self):
        """A row that cannot be written to JSON cannot be published, so this must never raise."""
        register_source("t_json", "test official", "https://www.nba.com/schedule", Src.OFFICIAL, "")
        r = make_row("x", "t_json", ["FLAG-T-JSON"], a=1, b=None, c="text", d=[1, 2], e={"k": 0.5})
        json.dumps(r.as_dict())
        self.assertIsNone(r.values["b"])


class TestRegistry(unittest.TestCase):
    def test_flag_registration_is_idempotent_and_sorted(self):
        before = len(all_flags())
        flag("FLAG-TEST-Z", "low", "test", "x", "https://www.nba.com/", "y")
        flag("FLAG-TEST-Z", "low", "test", "x2", "https://www.nba.com/", "y")
        after = [f.id for f in all_flags()]
        self.assertEqual(after.count("FLAG-TEST-Z"), 1)
        self.assertEqual(after, sorted(after))
        self.assertGreaterEqual(len(after), before)

    def test_every_snapshot_flag_is_registered(self):
        """Nothing in the committed data may reference a flag the site does not publish."""
        ids = {f.id for f in all_flags()}
        for name in (config.SNAPSHOT_SLATE, config.SNAPSHOT_RATINGS, config.SNAPSHOT_INJURY,
                     config.SNAPSHOT_CONTEXT):
            doc = json.loads((ROOT / config.DATA_DIR / name).read_text())
            for f in doc.get("flags", []):
                self.assertIn(f["id"], ids | {"FLAG-SLATE-01", "FLAG-SLATE-02", "FLAG-SLATE-03",
                                              "FLAG-RAT-01", "FLAG-RAT-02", "FLAG-INJ-01",
                                              "FLAG-INJ-02", "FLAG-INJ-03"},
                              f"{name}: flag {f['id']} is not surfaced on the site")


class TestModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = RT.build(ROOT)
        cls.games, _ = LN.load_slate(ROOT / config.DATA_DIR / config.SNAPSHOT_SLATE)
        cls.lines = LN.price_slate(cls.model, cls.games, {})

    def test_calibration_is_sane_and_fitted(self):
        cal = self.model.cal
        self.assertTrue(9.0 < cal.margin_sd < 19.0, cal.margin_sd)
        self.assertTrue(-1.0 < cal.hca_points < 5.0, cal.hca_points)
        self.assertLess(cal.rmse_wins, cal.rmse_baseline_wins,
                        "the fitted model must beat a .500 baseline or it is not a model")
        self.assertGreater(cal.tau_sq, 0.0)

    def test_shrinkage_pulls_toward_zero_monotonically(self):
        for t in self.model.teams.values():
            self.assertIsNotNone(t.reliability)
            self.assertTrue(0.0 < t.reliability <= 1.0, t.tricode)
            if t.srs is not None:
                self.assertLessEqual(abs(t.srs_shrunk), abs(t.srs))
                self.assertEqual(t.srs_shrunk == 0 or (t.srs_shrunk > 0) == (t.srs > 0), True,
                                 "shrinkage must never flip a sign")
        young = min(self.model.teams.values(), key=lambda t: t.games)
        old = max(self.model.teams.values(), key=lambda t: t.games)
        self.assertLessEqual(young.reliability, old.reliability,
                             "fewer games must mean a smaller weight on one's own rating")

    def test_every_game_gets_a_line(self):
        self.assertEqual(len(self.lines), 31)
        priced = [l for l in self.lines if l.spread_home is not None and l.total_line is not None]
        self.assertEqual(len(priced), 31, "R-012: the slate must be complete, no silent drops")

    def test_lines_are_half_point_and_total_is_centred(self):
        for l in self.lines:
            if l.spread_home is not None:
                self.assertAlmostEqual((l.spread_home * 2) % 1, 0.0, places=9)
            if l.total is not None and l.exp_home_pts is not None:
                self.assertAlmostEqual(l.exp_home_pts + l.exp_away_pts, round(l.total, 1), delta=0.25)

    def test_probability_is_consistent_with_the_spread(self):
        for l in self.lines:
            if l.home_win_prob is None or l.margin is None:
                continue
            self.assertEqual(l.home_win_prob > 0.5, l.margin > 0, l.game_id)
            self.assertTrue(0.02 < l.home_win_prob < 0.98, "no certainty claims at 12 games")

    def test_no_tier_a_while_injury_blind(self):
        self.assertEqual(sum(1 for l in self.lines if l.tier == "A"), 0,
                         "G-10: an availability-blind model may not claim its best tier")

    def test_stability_is_a_real_grid_result(self):
        vals = [l.stability for l in self.lines if l.stability is not None]
        self.assertGreater(len(vals), 20)
        self.assertTrue(all(0.0 <= v <= 1.0 for v in vals))
        self.assertIn(1.0, vals, "a heavy favourite should be stable across the box")

    def test_zero_and_one_probabilities_are_clamped(self):
        # a rating gap of 40 points must still not print "100%"
        p = self.model.cal.margin_sd
        from nba2.models.lines import _win_prob
        self.assertLess(_win_prob(40.0, 0, 0, p), 0.999)


class TestInjuries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.raw = INJ.load(ROOT / config.DATA_DIR / config.SNAPSHOT_INJURY)

    def test_no_numeric_impact_is_ever_produced(self):
        for r in self.rows:
            self.assertIsNone(r.minutes_impact, f"{r.player}: invented minutes impact")
            self.assertIsNone(r.production_impact, f"{r.player}: invented production impact")
            self.assertIsNone(r.line_adjustment_pts, f"{r.player}: invented line adjustment")

    def test_counts_match_the_committed_snapshot(self):
        c = self.raw["record_counts"]
        self.assertEqual(len(self.rows), c["total_rows"])
        self.assertEqual(sum(1 for r in self.rows if r.attribution == "C"),
                         c["attribution_continuation"])
        self.assertEqual(sum(1 for r in self.rows if r.status == "NOT YET SUBMITTED"),
                         c["not_yet_submitted_placeholders"])

    def test_rotation_index_is_a_count_not_a_points_claim(self):
        rot = INJ.rotation_index(self.rows)
        self.assertTrue(rot)
        for tri, d in rot.items():
            self.assertGreaterEqual(d["expected_missing_bodies"], 0)
            self.assertTrue(0 <= d["rotation_floor"] <= 12, tri)
            for key in ("psl", "pts_impact"):
                self.assertNotIn(key, d)

    def test_unknown_status_gets_no_probability(self):
        self.assertIsNone(INJ.STATUS_WEIGHT["NOT YET SUBMITTED"])


class TestLedger(unittest.TestCase):
    def test_seal_detects_tampering(self, ):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sealed.json"
            payload = [{"game_id": "1", "our_spread_home": -3.5}, {"game_id": "2", "our_spread_home": 1.5}]
            LD.seal(payload, path)
            ok, _, _ = LD.verify(path)
            self.assertTrue(ok)
            doc = json.loads(path.read_text())
            doc["predictions"][0]["our_spread_home"] = 7.0
            path.write_text(json.dumps(doc))
            ok2, stored, recomp = LD.verify(path)
            self.assertFalse(ok2, "an edited prediction must break the seal")
            self.assertNotEqual(stored, recomp)

    def test_settlement_without_finals_is_pending_not_zero(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sealed.json"
            LD.seal([{"game_id": "1", "our_spread_home": -3.5, "our_total": 220.0,
                      "p_home_win": 0.6}], path)
            s = LD.settle(path, Path(d) / "missing-finals.json")
            self.assertEqual(s.games_settled, 0)
            self.assertIn("PENDING", s.status)
            self.assertEqual(s.metrics, {}, "no invented metrics while nothing has settled")

    def test_settlement_uses_only_provided_finals(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sealed.json"
            LD.seal([
                {"game_id": "1", "our_spread_home": -3.5, "our_total": 220.0, "p_home_win": 0.60,
                 "away": "A", "home": "H"},
                {"game_id": "2", "our_spread_home": 2.5, "our_total": 210.0, "p_home_win": 0.45,
                 "away": "B", "home": "K"},
            ], path)
            finals = Path(d) / "finals.json"
            finals.write_text(json.dumps({"records": [
                {"game_id": "1", "home_pts": 110, "away_pts": 105, "source": "https://www.nba.com/schedule"},
                {"game_id": "2", "home_pts": 99, "away_pts": 104, "source": "https://www.nba.com/schedule"},
            ]}))
            s = LD.settle(path, finals)
            self.assertEqual(s.games_settled, 2)
            self.assertAlmostEqual(s.metrics["spread_mae"], (abs(3.5 - 5) + abs(-2.5 - (-5))) / 2, places=6)
            self.assertIn("brier", s.metrics)
            self.assertEqual(s.metrics["n_settled"], 2)


class TestAdjudication(unittest.TestCase):
    """The cross-session checks must be able to *contradict* us, or they are decoration."""

    def test_surname_join_is_format_agnostic(self):
        from nba2.pipeline.adjudicate import _surname
        self.assertEqual(_surname("Banchero, Paolo"), _surname("Paolo Banchero"))
        self.assertEqual(_surname("J. Wilson"), "wilson")
        self.assertEqual(_surname(""), "")

    def test_conflicts_are_adjudicated_not_assumed(self):
        from nba2.pipeline import adjudicate as AD
        from nba2.models import injuries as INJ
        rows, _ = INJ.load(ROOT / config.DATA_DIR / config.SNAPSHOT_INJURY)
        their = AD.json.loads((ROOT / "nba2" / "data" / "injuries.json").read_text()) \
            if hasattr(AD, "json") else json.loads((ROOT / "nba2" / "data" / "injuries.json").read_text())
        tbl = AD.adjudicate(their, rows)
        # every conflict row must state what the third revision said, or admit it cannot
        for r in tbl["rows"]:
            v = r["values"]
            self.assertIn(v["status_1715"], (None, "Out", "Doubtful", "Questionable", "Probable", "Available"))
            self.assertTrue(v["verdict"], "a conflict with no adjudication verdict is an unexamined conflict")
        self.assertGreaterEqual(len(tbl["rows"]), 6,
                                "the two captures are known to disagree on 6 rows; a join that finds "
                                "fewer is a join bug, not a cleaner dataset")

    def test_three_way_table_shows_stripped_gap(self):
        from nba2.models import lines as LN, ratings as RT
        from nba2.pipeline import adjudicate as AD
        model = RT.build(ROOT)
        games, _ = LN.load_slate(ROOT / config.DATA_DIR / config.SNAPSHOT_SLATE)
        priced = LN.price_slate(model, games, {})
        picks = json.loads((ROOT / "nba2" / "data" / "picks.json").read_text())
        tbl = AD.reconcile_three_way(priced, picks)
        self.assertGreaterEqual(len(tbl["rows"]), 20)
        withboth = [r for r in tbl["rows"]
                    if r["values"].get("gap_raw") and r["values"].get("gap_after_stripping")]
        self.assertGreaterEqual(len(withboth), 10, "the stripping comparison must exist, not be narrated")
        import statistics
        raw = [abs(float(r["values"]["gap_raw"].split()[0])) for r in withboth]
        adj = [abs(float(r["values"]["gap_after_stripping"].split()[0])) for r in withboth]
        self.assertLess(statistics.median(adj), statistics.median(raw),
                        "removing the other model's injury convention must shrink the median gap; "
                        "if it does not, the 'convention not data' claim on the site is false")


class TestPublishedSite(unittest.TestCase):
    """The emitted artefacts, not just the code that makes them."""

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "data" / "site.json").read_text())

    def test_every_row_has_a_source(self):
        for key, tbl in self.data["sections"].items():
            if not isinstance(tbl, dict) or "rows" not in tbl:
                continue
            for r in tbl["rows"]:
                self.assertIn("source", r, f"{key}/{r['key']}")
                self.assertIn(r["source"]["class"],
                              {"official", "third_party", "derived", "blocked"}, f"{key}/{r['key']}")

    def test_official_rows_point_at_nba_domains(self):
        allowed = ("www.nba.com", "ak-static.cms.nba.com", "cdn.nba.com", "stats.nba.com", "github.com")
        for key, tbl in self.data["sections"].items():
            if not isinstance(tbl, dict) or "rows" not in tbl:
                continue
            for r in tbl["rows"]:
                if r["source"]["class"] == "official":
                    url = r["source"]["url"]
                    self.assertTrue(any(h in url for h in allowed), f"{key}/{r['key']}: {url}")

    def test_blank_cells_are_flagged(self):
        for key, tbl in self.data["sections"].items():
            if not isinstance(tbl, dict) or "rows" not in tbl:
                continue
            for r in tbl["rows"]:
                if any(v is None for v in r["values"].values()):
                    self.assertTrue(r["flags"], f"{key}/{r['key']}: blank with no flag")

    def test_slate_is_complete_for_the_window(self):
        rows = self.data["sections"]["slate"]["rows"]
        by_date: dict[str, int] = {}
        for r in rows:
            by_date[r["values"]["date"]] = by_date.get(r["values"]["date"], 0) + 1
        self.assertEqual(by_date, {"2026-11-13": 9, "2026-11-14": 5, "2026-11-15": 9, "2026-11-16": 8})

    def test_no_invented_injury_or_correlation_numbers(self):
        """Values this repository fabricated in an earlier session must never come back as data.
        They may appear only as a quotation in the repo-review table, and only in a row that
        says it is reviewing the prior page."""
        banned = ("~34 MPG", "-100%", "r ≈ 0.82", "r ≈ 0.65", "GAME-20261113-")
        for key, tbl in self.data["sections"].items():
            if not isinstance(tbl, dict) or "rows" not in tbl:
                continue
            blob = json.dumps(tbl)
            if key == "repo_review":
                for r in tbl["rows"]:
                    joined = " ".join(str(v) for v in r["values"].values())
                    if any(b in joined for b in banned):
                        self.assertIn("prior", joined.lower(),
                                      "a quotation of a fabricated value must be labelled as such")
                continue
            for b in banned:
                self.assertNotIn(b, blob, f"{key}: {b!r} is a fabricated value; it must not return")

    def test_seal_is_advertised_and_verifiable(self):
        seal = self.data["meta"].get("seal")
        self.assertIsNotNone(seal, "the site must show the pre-registration seal")
        path = ROOT / config.DATA_DIR / "ledger" / f"sealed-{self.data['meta']['snapshot_as_of']}.json"
        ok, _, _ = LD.verify(path)
        self.assertTrue(ok)
        self.assertEqual(seal["sha256"], json.loads(path.read_text())["header"]["sha256"])
        self.assertEqual(seal["n_predictions"], 22, "T+1..T+3 window only")


class TestReproducibility(unittest.TestCase):
    def test_rebuild_produces_identical_rows(self):
        """Determinism is what makes a published number checkable: rebuild in a subprocess and
        compare everything except the build timestamp."""
        before_raw = (ROOT / "data" / "site.json").read_text()
        subprocess.run([sys.executable, "-m", "nba2.pipeline.build_site_data"], cwd=ROOT,
                       check=True, capture_output=True)
        after_raw = (ROOT / "data" / "site.json").read_text()
        self.assertEqual(before_raw, after_raw,
                         "two builds from the same snapshots must produce identical bytes, "
                         "timestamp included (that is what makes CI's parity check real)")
        after = json.loads(after_raw)
        self.assertTrue(after["meta"]["build_is_idempotent"])
        self.assertEqual(len(after["meta"]["input_digest"]), 64)


# Columns that are blank in every published row. Each entry is `table.column` and each one is
# blank *because the brief requires a blank over an estimate*: no official source exists for the
# value. The list is exact — verified against data/site.json on 2026-11-13 — so a new
# all-empty column (e.g. a field swallowed by a keyword clash) fails this test instead of
# shipping an empty column nobody notices.
EMPTY_OK = {
    "luck.close_record", "luck.blowout_record",                       # split extraction unreliable
    "injuries.minutes_impact", "injuries.production_impact",
    "injuries.line_adjustment",                                        # report has no such fields
    "leaders.impact",                                                  # same reason
    "gameflow.rest_home", "gameflow.rest_away",                       # needs games before the window
    "gameflow.pace", "gameflow.garbage", "gameflow.foul",
    "gameflow.closing",                                                # needs play-by-play
    "leaderboard.score", "leaderboard.bets", "leaderboard.reward",     # nothing has settled
    "props.minutes_floor",                                             # no player-level feed
}


class TestColumnGuard(unittest.TestCase):
    """Two real bugs came from a column header whose value was silently dropped (a keyword
    argument swallowed by make_row, and a key stripped when building values), so the guard
    that catches that class of mistake is itself tested."""

    data = json.loads((ROOT / "data" / "site.json").read_text())

    def test_declared_column_must_exist_on_every_row(self):
        from nba2.provenance import table as mk_table
        rows = [make_row("a", "nba_schedule", [], x=1), make_row("b", "nba_schedule", [], x=2)]
        mk_table(rows, [("x", "X")], "ok table")
        with self.assertRaises(ValueError) as cm:
            mk_table(rows, [("x", "X"), ("y", "Y")], "broken table")
        self.assertIn("absent from", str(cm.exception))

    def test_reserved_names_survive_as_values(self):
        r = make_row("k1", "nba_schedule", [], note="explains the blank", id="ROW-1")
        self.assertEqual(r.values["note"], "explains the blank")
        self.assertEqual(r.values["id"], "ROW-1")

    def test_no_unintended_all_empty_columns(self):
        empty = []
        for key, tbl in self.data["sections"].items():
            if not isinstance(tbl, dict) or "rows" not in tbl or not tbl["rows"]:
                continue
            for c in tbl["columns"]:
                vals = [r["values"].get(c["key"]) for r in tbl["rows"]]
                if all(v is None or v == "" for v in vals) and f"{key}.{c['key']}" not in EMPTY_OK:
                    empty.append(f"{key}.{c['key']}")
        self.assertEqual(empty, [], f"columns blank in every row and not justified: {empty}")
        # and the allow-list must not rot: every entry must still be a real all-blank column
        still = {f"{k}.{c['key']}" for k, tb in self.data["sections"].items()
                 if isinstance(tb, dict) and "rows" in tb and tb["rows"]
                 for c in tb["columns"]
                 if all(r["values"].get(c["key"]) in (None, "") for r in tb["rows"])}
        self.assertEqual(EMPTY_OK - still, set(),
                         "these 'deliberately blank' columns now contain data — publish that fact "
                         "instead of leaving them on the allow-list")


if __name__ == "__main__":
    unittest.main()
