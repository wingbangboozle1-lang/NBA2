"""Per-strategy pre-registration: freeze the rule before the first bet, and prove it has
not been edited afterwards.

Brief line 4
------------
    "Freeze a pre-registration file per strategy before its first bet: signal, thresholds,
     universe, and the exact settlement rule."

Why this exists
---------------
A strategy that is only written down after you know how it did is not a strategy, it is a
story. Every strategy in this repository therefore gets a file, written before it can fire a
single bet, containing the four things that determine its record:

* **signal**    — what makes the strategy act, in one sentence, as implemented;
* **thresholds**— every tunable number, with the value and where it comes from;
* **universe**  — exactly which games are eligible, and which are excluded and why;
* **settlement**— how a win, a loss and a push are decided, per market type, before any
  result exists to argue about.

The file is hashed. ``verify()`` re-derives the spec from the code that produced it and
compares the hash, so a parameter quietly changed after a good month shows up as a broken
pre-registration rather than as a track record.

Status model
------------
``FROZEN (pre-first-bet)`` — written, hashed, no bet has ever fired. This is where every
strategy in this repository sits today, because gate G6 (market price) fails, so nothing can
be staked.
``LOCKED``                  — the strategy has fired at least one settled bet; the file is
now immutable and any change to the spec is a defect, not a revision.

Run:  python3 -m nba2.v2.prereg
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "prereg"
LAB = ROOT / "nba2" / "v2" / "strategy_lab.py"

# --------------------------------------------------------------------------- the rules
# Adopted once, before any bet, and applied to every strategy until an owner changes the
# policy file itself. A settlement rule must not be negotiable after the result is known.
SETTLEMENT = {
    "moneyline": {
        "win": "the selected club has more points in the official final score",
        "loss": "the other club has more points in the official final score",
        "push": "impossible; an official final score is never tied (games go to overtime)",
        "source": "official final score, nba.com/game/<slug>",
    },
    "spread": {
        "win": "selected side's margin plus its handicap is strictly greater than zero",
        "loss": "selected side's margin plus its handicap is strictly less than zero",
        "push": "the result lands exactly on the handicap; the bet is void and removed "
                "from both the numerator and the denominator of every rate",
        "source": "official final score, nba.com/game/<slug>",
    },
    "total": {
        "win": "the official combined score is strictly on the side taken (over or under) "
               "of the reference total named in the bet record",
        "loss": "the official combined score is strictly on the other side",
        "push": "the official combined score equals the reference exactly; void and removed",
        "source": "official final score, nba.com/game/<slug>",
    },
    "parlay": {
        "win": "every leg wins; the parlay pays as one bet",
        "loss": "any leg loses; the parlay loses as one bet regardless of the other legs",
        "push": "one or more legs push and none lose: the parlay is REDUCED (pushed legs "
                "are removed and the price is recomputed on the remainder) and is recorded "
                "as a reduced bet, never as a win",
        "source": "the official final score of every game named by a leg",
    },
    "player_prop": {
        "win": "the player's official box-score figure is strictly on the side taken",
        "loss": "the figure is strictly on the other side",
        "push": "the figure equals the line exactly, OR the player does not appear in the "
                "official box score for that game (a non-appearance voids the bet)",
        "source": "official box score, nba.com/game/<slug>/box-score",
    },
    "grading_time": ("a bet is graded after the game's official status is FINAL and the "
                     "result has been read off two official surfaces; a game with only one "
                     "captured surface is not settled"),
}

# Which market each strategy settles under. Written explicitly so the mapping is frozen
# rather than inferred at grading time.
MARKET = {
    "S1": "moneyline", "S2": "total", "S3": "moneyline", "S4": "moneyline",
    "S5": "parlay", "S6": "parlay", "S7": "player_prop",
}


def _sha(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _code_sha() -> str:
    return hashlib.sha256(LAB.read_bytes()).hexdigest()


def spec_for(strategy, lab_module, n_games: int, first_date: str, last_date: str) -> dict:
    """The pre-registration record for one strategy, derived from the code that runs it."""
    sid = strategy.sid
    thresholds = {
        "K_SHRINK_pseudo_games": lab_module.K_SHRINK,
        "HCA_points": lab_module.HCA,
        "CONFIDENT_PTS": lab_module.CONFIDENT_PTS,
        "FADE_HOME_PTS": lab_module.FADE_HOME_PTS,
        "MIN_BETS_RANK (gate G7)": lab_module.MIN_BETS_RANK,
        "HOLDOUT_FRAC (gate G8)": lab_module.HOLDOUT_FRAC,
        "PERMUTATION_SEED": lab_module.SEED,
    }
    # only the thresholds this strategy actually uses belong in its pre-registration
    used = {
        "S1": ["K_SHRINK_pseudo_games", "HCA_points"],
        "S2": ["K_SHRINK_pseudo_games", "HCA_points"],
        "S3": ["K_SHRINK_pseudo_games", "HCA_points", "CONFIDENT_PTS"],
        "S4": ["K_SHRINK_pseudo_games", "HCA_points", "FADE_HOME_PTS"],
        "S5": ["K_SHRINK_pseudo_games", "HCA_points"],
        "S6": ["K_SHRINK_pseudo_games", "HCA_points"],
        "S7": [],
    }.get(sid, [])
    if sid in ("S3", "S4", "S5", "S6"):
        thresholds_used = {k: thresholds[k] for k in used}
    else:
        thresholds_used = {k: thresholds[k] for k in used}
    thresholds_used["MIN_BETS_RANK (gate G7)"] = thresholds["MIN_BETS_RANK (gate G7)"]
    thresholds_used["HOLDOUT_FRAC (gate G8)"] = thresholds["HOLDOUT_FRAC (gate G8)"]
    thresholds_used["PERMUTATION_SEED"] = thresholds["PERMUTATION_SEED"]

    universe = {
        "games": "every official regular-season game in the committed results feed",
        "window": ("every official regular-season game in the committed results feed. The "
                   "feed grows as results are ingested; the rule does not change with it."),
        "eligibility": "a game is eligible once BOTH clubs have appeared in a strictly "
                       "earlier game, so every rating is built only from prior results",
        "exclusions": {
            "no_prior_data": "games on the first date of the feed (no rating exists yet)",
            "neutral_site": ("excluded from S4 only, where the home-fade signal is "
                             "meaningless without a home team"),
            "S3": f"games whose |predicted margin| is below {lab_module.CONFIDENT_PTS:.0f} pts",
            "S4": f"games the model does not make the home side an underdog of "
                  f"{lab_module.FADE_HOME_PTS:.0f}+ pts, and neutral-site games",
            "S6": "dates with fewer than two eligible games (a parlay needs two legs)",
            "S7": "every game: no per-player data exists, so no bet is ever generated",
        },
        "no_cherry_picking": "the universe is defined by the rule, not by the results; no "
                             "game is added or removed after its outcome is known",
    }
    spec = {
        "schema": "nba2.prereg.v1",
        # The context block describes the feed at freeze time. It is deliberately outside
        # the hash: a pre-registration that breaks every time a night of results lands is
        # noise, and the rule it freezes has not changed.
        "context": {"n_games_in_feed_at_freeze": n_games,
                    "feed_first_date": first_date, "feed_last_date": last_date},
        "sid": sid,
        "name": strategy.name,
        "kind": strategy.kind,
        "signal": strategy.rule,
        "thresholds": thresholds_used,
        "thresholds_note": ("every value is a module constant in nba2/v2/strategy_lab.py, "
                            "not a fitted-on-the-test-set number; the file's own sha256 is "
                            "recorded below so a change to any of them breaks this hash"),
        "universe": universe,
        "settlement": {
            "market": MARKET.get(sid, "moneyline"),
            "rules": SETTLEMENT[MARKET.get(sid, "moneyline")],
            "grading_time": SETTLEMENT["grading_time"],
        },
        "code_sha256": _code_sha(),
        "first_bet_date": None,
        "status": "FROZEN (pre-first-bet)",
    }
    hashed = {k: v for k, v in spec.items() if k not in ("sha256", "context")}
    spec["sha256"] = _sha(hashed)
    return spec


def freeze(write: bool = True) -> dict:
    """Build every spec, write the ones that do not exist, and verify the ones that do."""
    from . import strategy_lab as SL
    games = SL.load_games()
    preds = SL.walk_forward(games)
    strategies = SL.build_strategies(preds)
    dates = sorted({g["date"] for g in games})
    OUT.mkdir(parents=True, exist_ok=True)

    items, problems = [], []
    for s in strategies:
        spec = spec_for(s, SL, len(games), dates[0], dates[-1])
        path = OUT / f"{s.sid}.json"
        if path.exists():
            stored = json.loads(path.read_text())
            if stored.get("sha256") != spec["sha256"]:
                problems.append(
                    f"{s.sid}: the frozen pre-registration no longer matches the code "
                    f"(stored {stored.get('sha256', '')[:12]}… vs recomputed "
                    f"{spec['sha256'][:12]}…). A pre-registration that changes after the "
                    f"fact is not a pre-registration — re-freeze deliberately, with the "
                    f"reason recorded, or revert the code.")
                spec["stored_sha256"] = stored.get("sha256")
                spec["status"] = "DRIFTED — frozen spec does not match the code"
            else:
                spec["status"] = stored.get("status", spec["status"])
                spec["first_bet_date"] = stored.get("first_bet_date")
        elif write:
            path.write_text(json.dumps(spec, indent=1) + "\n")
        items.append(spec)

    manifest = {
        "schema": "nba2.prereg-manifest.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session": "arena/673acec0-nba2",
        "n_strategies": len(items),
        "code_sha256": _code_sha(),
        "manifest_sha256": _sha([{k: v for k, v in i.items() if k != "sha256"} for i in items]),
        "items": items,
        "problems": problems,
        "settlement_policy_version": "1.0 (adopted 2026-11-15, before any bet)",
    }
    if write:
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
        (OUT / "SETTLEMENT.md").write_text(_settlement_md())
    manifest["settlement_policy"] = SETTLEMENT
    return manifest


def _settlement_md() -> str:
    out = ["# Settlement rules (adopted before any bet is placed)", "",
           "This file is policy, not code output. It exists so that how a bet is graded is",
           "decided before there is a result to argue about. Changing it is an owner decision,",
           "and any change applies only to bets placed after the change.", ""]
    for market, rules in SETTLEMENT.items():
        if market == "grading_time":
            continue
        out.append(f"## {market}")
        for k in ("win", "loss", "push", "source"):
            out.append(f"- **{k}** — {rules[k]}")
        out.append("")
    out.append("## When a bet is graded")
    out.append(f"- {SETTLEMENT['grading_time']}")
    out.append("")
    return "\n".join(out)


def verify() -> list[str]:
    """Fail if any frozen pre-registration has drifted from the code that produced it."""
    m = freeze(write=False)
    return list(m["problems"])


def main() -> int:
    m = freeze()
    print(f"{m['n_strategies']} strategies pre-registered in data/prereg/ "
          f"(code sha256 {m['code_sha256'][:12]}…)")
    for i in m["items"]:
        print(f"  {i['sid']} {i['name'][:46]:<46} {i['status']:<24} "
              f"{i['sha256'][:12]}…")
    for p in m["problems"]:
        print("PROBLEM:", p)
    print("settlement policy: data/prereg/SETTLEMENT.md (version "
          f"{m['settlement_policy_version']})")
    return 1 if m["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
