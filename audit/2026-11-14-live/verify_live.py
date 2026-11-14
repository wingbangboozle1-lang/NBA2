"""Line-by-line re-verification of the committed snapshots against a live official capture.

    python3 audit/2026-11-14-live/verify_live.py

What this does, in order:

1. **Validates the capture itself.** The capture in ``data/raw/official_capture_2026-11-14T1015Z.json``
   was transcribed from two official NBA.com pages read in this session. Before it is used to
   check anything else, it is checked against arithmetic the pages themselves imply:
   ``home + road + neutral == (w, l)`` for every team, and the league totals must balance
   (183 wins / 183 losses / 366 team-games = 174 completed games through 2026-11-12 plus the
   9 games of 2026-11-13).

2. **Diffs the slate.** Every field of every one of the 36 committed games is compared with the
   live capture: date, tip time, teams, game ID, arena, city, state, broadcast, cup group.

3. **Diffs the team records.** The committed ratings snapshot (W-L, home split, road split) is
   compared with the live official standings, team by team.

4. **Cross-checks the 2026-11-13 finals** against the earlier session's independent capture.

5. **Quantifies the staleness impact.** The committed ratings snapshot was taken while the
   2026-11-13 slate was still in progress, so several teams' records are one game behind the
   live official standings. This step re-anchors W-L and the home/road splits to the live
   standings, re-derives every line, and reports how far the lines would move.

   **The sealed ledgers are not touched.** They are immutable by design, the published lines
   stay exactly as sealed, and the delta is published as a disclosure instead.

   **What the re-anchor does NOT change:** SRS, points-per-game, points-allowed-per-game and
   the close/blowout splits stay at their committed third-party values, because the official
   standings do not publish them. The movement reported here is therefore a **lower bound**
   on the true staleness effect — the SRS term would also move in a full re-anchor.

Read-only over the repository except for the two files it writes next to itself.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from nba2.models import injuries as INJ  # noqa: E402
from nba2.models import lines as LN  # noqa: E402
from nba2.models import ratings as RT  # noqa: E402

CAPTURE = ROOT / "data" / "raw" / "official_capture_2026-11-14T1015Z.json"
SLATE = ROOT / "data" / "raw" / "slate_2026-11-14_to_11-17.json"
RATINGS = ROOT / "data" / "raw" / "team_ratings_2026-11-13.json"
PRIOR_CAPTURE = ROOT / "audit" / "2026-11-14" / "official_inputs_2026-11-14.json"

report: dict = {
    "session": "arena/9ee870ea-nba2",
    "generated_from": {
        "capture": str(CAPTURE.relative_to(ROOT)),
        "capture_captured_at_utc": None,
        "slate": str(SLATE.relative_to(ROOT)),
        "ratings": str(RATINGS.relative_to(ROOT)),
    },
    "capture_validation": {},
    "slate_diff": {},
    "records_diff": {},
    "finals_cross_check": {},
    "staleness_impact": {},
    "flags_raised": [],
}


def rec_split(v) -> tuple[int, int] | None:
    if not isinstance(v, str) or "-" not in v:
        return None
    a, b = v.split("-", 1)
    try:
        return int(a), int(b)
    except ValueError:
        return None


# --------------------------------------------------------------------------- 1. capture validation
cap = json.loads(CAPTURE.read_text())
report["generated_from"]["capture_captured_at_utc"] = cap["captured_at_utc"]

st_cols = cap["standings"]["columns"]
st_rows = [dict(zip(st_cols, r)) for r in cap["standings"]["records"]]

split_errors = []
for row in st_rows:
    w, l = row["w"], row["l"]
    home, road, neu = rec_split(row["home"]), rec_split(row["road"]), rec_split(row["neutral"])
    if None in (home, road, neu):
        split_errors.append({"team": row["tricode"], "error": "split not readable"})
        continue
    if (home[0] + road[0] + neu[0], home[1] + road[1] + neu[1]) != (w, l):
        split_errors.append({
            "team": row["tricode"],
            "error": "home+road+neutral != (w,l)",
            "splits": [row["home"], row["road"], row["neutral"]],
            "record": f"{w}-{l}",
        })

tot_w = sum(r["w"] for r in st_rows)
tot_l = sum(r["l"] for r in st_rows)
tot_gp = sum(r["w"] + r["l"] for r in st_rows)

sched_cols = cap["schedule"]["columns"]
sched_rows = [dict(zip(sched_cols, r)) for r in cap["schedule"]["records"]]
out_cols = sched_cols
out_rows = [dict(zip(out_cols, r)) for r in cap["schedule"]["outside_pick_window"]]

per_date: dict[str, int] = {}
for g in sched_rows:
    per_date[g["date"]] = per_date.get(g["date"], 0) + 1

report["capture_validation"] = {
    "teams": len(st_rows),
    "split_arithmetic_failures": split_errors,
    "split_arithmetic_failures_count": len(split_errors),
    "league_totals": {"wins": tot_w, "losses": tot_l, "team_games": tot_gp,
                      "implied_games": tot_gp / 2, "balanced": tot_w == tot_l},
    "slate_games_captured": len(sched_rows),
    "per_date_counts_captured": per_date,
    "per_date_counts_read_from_day_headers": cap["schedule"]["counts_read_from_day_headers"],
    "per_date_counts_match": per_date == cap["schedule"]["counts_read_from_day_headers"],
    "games_outside_pick_window_captured": len(out_rows),
    "last10_left_blank_because_two_reads_disagreed":
        sorted(r["tricode"] for r in st_rows if r["last10"] is None),
}

# --------------------------------------------------------------------------- 2. slate diff
slate = json.loads(SLATE.read_text())
s_cols = slate["columns"]
committed = {r[4]: dict(zip(s_cols, r)) for r in slate["records"]}
live = {g["game_id"]: g for g in sched_rows}

def broadcast_marks(label) -> set[str]:
    """Normalise a broadcaster label (or a list of marks) to a set of comparable marks."""
    if not label:
        return set()
    if isinstance(label, list):
        return set(label)
    out: set[str] = set()
    for part in str(label).replace(",", "/").split("/"):
        p = part.strip()
        if not p:
            continue
        pl = p.lower()
        if pl in ("league pass", "league_pass", "lp"):
            out.add("LEAGUE PASS")
        elif pl == "nba tv":
            out.add("NBA TV")
        elif pl in ("mnmt", "mnmt/monumental+", "monumental+"):
            out.add("TV: MNMT/Monumental+")
        elif pl == "peacock":
            out.add("Peacock")
        elif pl in ("nbc sports network", "nbcsn"):
            out.add("NBC Sports Network")
        elif pl == "nbc":
            out.add("NBC")
        elif pl == "espn":
            out.add("ESPN")
        elif pl == "prime video":
            out.add("Prime Video")
        else:
            out.add(p)
    return out


mismatches = []
not_rendered = []
missing = sorted(set(committed) ^ set(live))
field_map = [("date", "date"), ("time_et", "time_et"), ("away", "away"), ("home", "home"),
             ("game_id", "game_id"), ("arena", "arena"), ("city", "city"), ("state", "state"),
             ("broadcast", "broadcast"), ("cup_group", "cup_group")]
compared_fields = 0
for gid, c in committed.items():
    l = live.get(gid)
    if l is None:
        mismatches.append({"game_id": gid, "field": "*", "committed": c, "live": None,
                           "kind": "missing from the live capture"})
        continue
    for cf, lf in field_map:
        cv = c.get(cf)
        lv = l.get(lf)
        if lv is None:
            if cv is None:
                # not applicable in either capture (e.g. no Emirates NBA Cup group on this date)
                continue
            # the official page does not render this field for this row, so this capture cannot
            # confirm or contradict the committed value. Recorded, not counted as a mismatch.
            not_rendered.append({"game_id": gid, "field": cf, "committed": cv,
                                 "reason": "field not rendered by the official page for this row"})
            continue
        compared_fields += 1
        if cf == "broadcast":
            cm, lm = broadcast_marks(cv), broadcast_marks(lv)
            if cm == lm:
                continue
            mismatches.append({
                "game_id": gid, "field": "broadcast", "kind": "broadcaster marks differ",
                "committed": sorted(cm), "live": sorted(lm),
                "only_in_committed": sorted(cm - lm), "only_in_live": sorted(lm - cm),
            })
            continue
        if cv != lv:
            mismatches.append({"game_id": gid, "field": cf, "kind": "value differs",
                               "committed": cv, "live": lv})

report["slate_diff"] = {
    "committed_games": len(committed),
    "live_games_in_pick_window": len(live),
    "games_only_in_one_capture": missing,
    "field_values_compared": compared_fields,
    "fields_not_rendered_by_the_page": not_rendered,
    "fields_not_rendered_count": len(not_rendered),
    "mismatches": mismatches,
    "mismatch_count": len(mismatches),
    "result": "IDENTICAL" if not mismatches and not missing else "DIFFERENCES FOUND",
    "pick_window_identical": not [m for m in mismatches
                                  if m["game_id"] >= "0022600231"],
}

# --------------------------------------------------------------------------- 3. records diff
RATINGS_DOC = json.loads(RATINGS.read_text())
r_cols = RATINGS_DOC["columns"]
committed_recs = {r[0]: dict(zip(r_cols, r)) for r in RATINGS_DOC["records"]}
live_recs = {r["tricode"]: r for r in st_rows}

rec_diff = []
for tc in sorted(set(committed_recs) | set(live_recs)):
    c, l = committed_recs.get(tc), live_recs.get(tc)
    if c is None or l is None:
        rec_diff.append({"tricode": tc, "issue": "team present in only one capture"})
        continue
    hw, hl = rec_split(c["home_w"] + "-" + c["home_l"]) if False else (c["home_w"], c["home_l"])
    l_home = rec_split(l["home"])
    l_road = rec_split(l["road"])
    row = {
        "tricode": tc,
        "committed_wl": f"{c['w']}-{c['l']}",
        "live_wl": f"{l['w']}-{l['l']}",
        "wins_delta": l["w"] - c["w"],
        "losses_delta": l["l"] - c["l"],
        "committed_home": f"{c['home_w']}-{c['home_l']}",
        "live_home": f"{l_home[0]}-{l_home[1]}",
        "committed_road": f"{c['road_w']}-{c['road_l']}",
        "live_road": f"{l_road[0]}-{l_road[1]}",
    }
    changed = (row["wins_delta"] or row["losses_delta"]
               or row["committed_home"] != row["live_home"]
               or row["committed_road"] != row["live_road"])
    row["changed"] = bool(changed)
    rec_diff.append(row)

changed_rows = [r for r in rec_diff if r["changed"]]
report["records_diff"] = {
    "teams_compared": len(rec_diff),
    "teams_whose_record_moved": len(changed_rows),
    "teams_whose_record_moved_list": [r["tricode"] for r in changed_rows],
    "rows": rec_diff,
}

# --------------------------------------------------------------------------- 4. finals cross-check
f_cols = cap["finals_2026_11_13"]["columns"]
live_finals = [dict(zip(f_cols, r)) for r in cap["finals_2026_11_13"]["records"]]
prior = json.loads(PRIOR_CAPTURE.read_text())
prior_finals = {f["game_id"]: f for f in prior.get("finals_2026_11_13", [])}
final_mismatch = []
for f in live_finals:
    p = prior_finals.get(f["game_id"])
    if p is None:
        final_mismatch.append({"game_id": f["game_id"], "issue": "not in the prior capture"})
        continue
    for k_live, k_prior in (("away_score", "away_pts"), ("home_score", "home_pts")):
        if f[k_live] != p[k_prior]:
            final_mismatch.append({"game_id": f["game_id"], "field": k_live,
                                   "live": f[k_live], "prior": p[k_prior]})
    if f["away"] != p.get("away") or f["home"] != p.get("home"):
        final_mismatch.append({"game_id": f["game_id"], "field": "teams",
                               "live": [f["away"], f["home"]],
                               "prior": [p.get("away"), p.get("home")]})
    if bool(f["ot"]) != bool(p.get("ot")):
        final_mismatch.append({"game_id": f["game_id"], "field": "ot",
                               "live": f["ot"], "prior": p.get("ot")})
report["finals_cross_check"] = {
    "live_finals": len(live_finals),
    "prior_capture_finals": len(prior_finals),
    "mismatches": final_mismatch,
    "mismatch_count": len(final_mismatch),
    "result": "IDENTICAL" if not final_mismatch else "DIFFERENCES FOUND",
}

# --------------------------------------------------------------------------- 5. staleness impact
# Re-anchor W-L and the home/road splits to the live official standings and re-derive every line.
# SRS / points / close-split stay at their committed third-party values (the official standings
# do not publish them), so the movement below is a LOWER BOUND on the true staleness effect.
import copy  # noqa: E402

what_if = copy.deepcopy(RATINGS_DOC)
for rec in what_if["records"]:
    d = dict(zip(what_if["columns"], rec))
    live_r = live_recs.get(d["tricode"])
    if not live_r:
        continue
    home, road = rec_split(live_r["home"]), rec_split(live_r["road"])
    idx = {c: i for i, c in enumerate(what_if["columns"])}
    rec[idx["w"]] = live_r["w"]
    rec[idx["l"]] = live_r["l"]
    gp = live_r["w"] + live_r["l"]
    rec[idx["pct"]] = round(live_r["w"] / gp, 3)
    rec[idx["home_w"]], rec[idx["home_l"]] = home
    rec[idx["road_w"]], rec[idx["road_l"]] = road

tmp = HERE / "_what_if_ratings.json"
tmp.write_text(json.dumps(what_if, indent=1))

teams = RT.load_teams(tmp)
cal = RT.calibrate(teams)
RT.apply_shrinkage(teams, cal)
RT.skill_and_luck(teams, cal)
what_if_model = RT.RatingModel(teams, cal)

games, _ = LN.load_slate(SLATE)
inj_rows, _ = INJ.load(ROOT / "data" / "raw" / "injury_report_2026-11-13_1930ET.json")
by_team = INJ.by_team(inj_rows)
what_if_lines = {l.game_id: l for l in LN.price_slate(what_if_model, games, by_team)}

published_model = RT.build(ROOT)
published_lines = {l.game_id: l for l in LN.price_slate(published_model, games, by_team)}

rows = []
for gid in sorted(published_lines):
    p, w = published_lines[gid], what_if_lines[gid]
    d_spread = (w.spread_home - p.spread_home) if (w.spread_home is not None and p.spread_home is not None) else None
    d_total = (w.total_line - p.total_line) if (w.total_line is not None and p.total_line is not None) else None
    d_margin = (w.margin - p.margin) if (w.margin is not None and p.margin is not None) else None
    rows.append({
        "game_id": gid, "date": p.date, "matchup": f"{p.away} @ {p.home}",
        "published_spread_home": p.spread_home, "reanchored_spread_home": w.spread_home,
        "spread_move_pts": round(d_spread, 2) if d_spread is not None else None,
        "published_total": p.total_line, "reanchored_total": w.total_line,
        "total_move_pts": round(d_total, 2) if d_total is not None else None,
        "published_margin": p.margin, "reanchored_margin": w.margin,
        "margin_move_pts": round(d_margin, 2) if d_margin is not None else None,
        "published_tier": p.tier, "reanchored_tier": w.tier,
        "published_lean": p.lean, "reanchored_lean": w.lean,
        "lean_changed": p.lean != w.lean,
        "in_pick_window": p.date >= "2026-11-14",
    })

moves = [abs(r["spread_move_pts"]) for r in rows if r["spread_move_pts"] is not None]
tmoves = [abs(r["total_move_pts"]) for r in rows if r["total_move_pts"] is not None]
win_rows = [r for r in rows if r["in_pick_window"]]
win_moves = [abs(r["spread_move_pts"]) for r in win_rows if r["spread_move_pts"] is not None]
lean_changes = [r for r in rows if r["lean_changed"]]

report["staleness_impact"] = {
    "what_was_re_anchored": "W-L and the home/road splits, from the live official standings.",
    "what_was_not_re_anchored": ("SRS, points per game, points allowed per game and the close/blowout "
                                 "splits stay at their committed third-party values, because the official "
                                 "standings do not publish them. The movement below is therefore a LOWER "
                                 "BOUND on the true staleness effect."),
    "published_lines_unchanged": True,
    "sealed_ledgers_untouched": True,
    "calibration_published": {"margin_sd": round(published_model.cal.margin_sd, 4),
                              "hca_points": round(published_model.cal.hca_points, 4),
                              "rmse_wins": round(published_model.cal.rmse_wins, 4)},
    "calibration_reanchored": {"margin_sd": round(what_if_model.cal.margin_sd, 4),
                               "hca_points": round(what_if_model.cal.hca_points, 4),
                               "rmse_wins": round(what_if_model.cal.rmse_wins, 4)},
    "all_games": {
        "n": len(rows),
        "max_abs_spread_move_pts": round(max(moves), 2) if moves else None,
        "mean_abs_spread_move_pts": round(sum(moves) / len(moves), 3) if moves else None,
        "max_abs_total_move_pts": round(max(tmoves), 2) if tmoves else None,
        "mean_abs_total_move_pts": round(sum(tmoves) / len(tmoves), 3) if tmoves else None,
        "leans_that_change": len(lean_changes),
    },
    "pick_window_only": {
        "n": len(win_rows),
        "max_abs_spread_move_pts": round(max(win_moves), 2) if win_moves else None,
        "mean_abs_spread_move_pts": round(sum(win_moves) / len(win_moves), 3) if win_moves else None,
        "leans_that_change": len([r for r in win_rows if r["lean_changed"]]),
    },
    "rows": rows,
}
tmp.unlink(missing_ok=True)

# --------------------------------------------------------------------------- flags
if changed_rows:
    report["flags_raised"].append({
        "id": "FLAG-LIVE-01",
        "severity": "high",
        "field": "team records (W-L, home/road splits)",
        "issue": (f"The committed ratings snapshot (data/raw/team_ratings_2026-11-13.json, retrieved "
                  f"2026-11-13 22:35 UTC while the 2026-11-13 slate was still in progress) is one slate "
                  f"behind the live official standings read on 2026-11-14 10:15 UTC. "
                  f"{len(changed_rows)} of 30 teams moved: "
                  f"{', '.join(r['tricode'] for r in changed_rows)}."),
        "action_required": ("Re-anchor the ratings snapshot to a post-slate standings read before the next "
                            "window is sealed. The current window's lines and sealed ledgers stay as they "
                            "are — the seal is immutable — and the measured impact is published on the "
                            "Ratings Staleness page."),
        "source": "https://www.nba.com/standings",
    })
report["flags_raised"].append({
    "id": "FLAG-LIVE-02",
    "severity": "medium",
    "field": "game_id ordering",
    "issue": ("Within 2026-11-17 the official game IDs are not monotonic with tip time: 0022600257 "
              "(UTA @ LAC, 10:30 PM ET) is listed before 0022600256 (CHA @ LAL, 11:00 PM ET). A pipeline "
              "that orders games by game ID will order those two wrongly."),
    "action_required": "Order by (date, tip time), never by game ID.",
    "source": "https://www.nba.com/schedule",
})
report["flags_raised"].append({
    "id": "FLAG-LIVE-03",
    "severity": "low",
    "field": "standings LAST10",
    "issue": ("Two reads of the same official standings page in the same session disagreed on the LAST10 "
              "column for GSW, DAL, PHX and SAC. Those four cells are left blank rather than guessed. "
              "LAST10 is not a model input."),
    "action_required": "Re-read LAST10 in a later capture; it feeds no line.",
    "source": "https://www.nba.com/standings",
})
report["flags_raised"].append({
    "id": "FLAG-LIVE-04",
    "severity": "info",
    "field": "pick window",
    "issue": ("The official schedule publishes 12 games on 2026-11-18 and 4 more on 2026-11-19. The brief's "
              "maximum is 3 days ahead of the build date (2026-11-14), so 11-18 and 11-19 are deliberately "
              "outside the pick window; they are listed so the omission is visible rather than silent."),
    "action_required": "None. Revisit when the build date advances.",
    "source": "https://www.nba.com/schedule",
})
report["flags_raised"].append({
    "id": "FLAG-LIVE-05",
    "severity": "info",
    "field": "tip times for completed games",
    "issue": ("For the nine completed 2026-11-13 games the official schedule page renders the score and the "
              "venue but not the tip time, so those times are carried from the committed capture and are not "
              "re-verified by this capture. All 27 pick-window games were re-verified with tip time."),
    "action_required": "None for the pick window; the 11-13 times are context only.",
    "source": "https://www.nba.com/schedule",
})

_cup_gaps = [m["game_id"] for m in report["slate_diff"]["mismatches"] if m["field"] == "cup_group"]
if _cup_gaps:
    report["flags_raised"].append({
        "id": "FLAG-LIVE-06",
        "severity": "medium",
        "field": "slate.cup_group",
        "issue": (f"The committed 2026-11-13 capture left the Emirates NBA Cup group empty for all nine "
                  f"2026-11-13 group games ({', '.join(_cup_gaps)}). The official schedule page renders the "
                  f"group label for every one of them, and this capture read all nine. The published slate "
                  f"table therefore shows an empty Cup cell for nine games that do have a group."),
        "action_required": ("Carry the officially-read group labels into the published slate table, or leave "
                            "the cells blank and say why. The published table currently shows the empty cell "
                            "without an explanation."),
        "source": "https://www.nba.com/schedule",
    })

_bcast = [m for m in report["slate_diff"]["mismatches"] if m["field"] == "broadcast"]
if _bcast:
    _detail = "; ".join(
        f"{m['game_id']} committed {m['only_in_committed'] or '(none extra)'} / "
        f"page renders {m['only_in_live'] or '(none extra)'}" for m in _bcast)
    report["flags_raised"].append({
        "id": "FLAG-LIVE-07",
        "severity": "low",
        "field": "slate.broadcast",
        "issue": (f"The broadcaster label stored in the committed capture does not match the marks the "
                  f"official page renders, for {len(_bcast)} games: {_detail}. One committed label names a "
                  f"feed the page does not render; one committed label omits a feed the page does render. "
                  f"Broadcast is a display field and feeds no line."),
        "action_required": "Store the broadcaster marks the page renders, as a list, rather than a prose label.",
        "source": "https://www.nba.com/schedule",
    })

out_json = HERE / "report.json"
out_json.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")

# --------------------------------------------------------------------------- console summary
v = report["capture_validation"]
print("CAPTURE VALIDATION")
print(f"  teams={v['teams']}  split arithmetic failures={v['split_arithmetic_failures_count']}")
print(f"  league totals: {v['league_totals']['wins']}W/{v['league_totals']['losses']}L "
      f"= {v['league_totals']['implied_games']} games, balanced={v['league_totals']['balanced']}")
print(f"  slate games={v['slate_games_captured']}  per-date counts match day headers="
      f"{v['per_date_counts_match']}  outside window={v['games_outside_pick_window_captured']}")
print()
print("SLATE DIFF")
print(f"  {report['slate_diff']['field_values_compared']} field values compared across "
      f"{report['slate_diff']['committed_games']} games -> {report['slate_diff']['result']}")
print(f"  fields the page does not render (cannot be re-verified): "
      f"{report['slate_diff']['fields_not_rendered_count']}")
for m in report["slate_diff"]["mismatches"][:20]:
    print(f"    {m['game_id']} {m['field']} [{m['kind']}]: committed={m['committed']!r} live={m['live']!r}")
print()
print("RECORDS DIFF")
print(f"  {report['records_diff']['teams_compared']} teams compared, "
      f"{report['records_diff']['teams_whose_record_moved']} moved: "
      f"{', '.join(report['records_diff']['teams_whose_record_moved_list'])}")
for r in changed_rows:
    print(f"    {r['tricode']}: {r['committed_wl']} -> {r['live_wl']}  "
          f"home {r['committed_home']}->{r['live_home']}  road {r['committed_road']}->{r['live_road']}")
print()
print("FINALS CROSS-CHECK")
print(f"  {report['finals_cross_check']['live_finals']} finals vs the prior session's capture -> "
      f"{report['finals_cross_check']['result']}")
print()
si = report["staleness_impact"]
print("STALENESS IMPACT (published lines unchanged; seals untouched)")
print(f"  calibration published  : sigma={si['calibration_published']['margin_sd']} "
      f"hca={si['calibration_published']['hca_points']} rmse={si['calibration_published']['rmse_wins']}")
print(f"  calibration re-anchored: sigma={si['calibration_reanchored']['margin_sd']} "
      f"hca={si['calibration_reanchored']['hca_points']} rmse={si['calibration_reanchored']['rmse_wins']}")
print(f"  all {si['all_games']['n']} games: max |spread move|="
      f"{si['all_games']['max_abs_spread_move_pts']} pts, mean={si['all_games']['mean_abs_spread_move_pts']}, "
      f"leans changed={si['all_games']['leans_that_change']}")
print(f"  pick window {si['pick_window_only']['n']} games: max |spread move|="
      f"{si['pick_window_only']['max_abs_spread_move_pts']} pts, "
      f"mean={si['pick_window_only']['mean_abs_spread_move_pts']}, "
      f"leans changed={si['pick_window_only']['leans_that_change']}")
print()
print(f"wrote {out_json.relative_to(ROOT)}")
