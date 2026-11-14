"""Add session arena/ac5fab5c-nba2's decisions to the decision queue (P-09)."""
import json, pathlib

# --------------------------------------------------------------- register
P = pathlib.Path("suggestions/SUGGESTIONS.json")
d = json.loads(P.read_text())
have = {s["id"] for s in d["suggestions"]}
NEW = [
 {"id": "S-29",
  "title": "Schedule a nightly job that appends each night's official finals and asserts the per-date count",
  "problem": ("The results history was incomplete for most of this project's life, and the standings published on "
              "the site drifted a full day behind without anything noticing. Both are the same failure: no job "
              "appends results, and nothing compares a published row against a fresher capture."),
  "proposal": ("Add a scheduled workflow that fetches each completed date from nba.com/games, appends it to "
               "data/raw/history/, and asserts the per-date game count against the nba.com day-strip calendar. "
               "Fail the run if the implied total ever disagrees with the team record implied by the standings."),
  "benefit": ("Makes the window impossible to fall behind silently, and turns the standings into a permanent "
              "cross-check on the results log."),
  "effort": "S",
  "risk": ("Low. Needs a runner with normal internet egress — nba.com is TLS-blocked from this sandbox, which is "
           "why this session could not build it."),
  "recommendation": "Accept — cheapest fix with the largest effect on trust (mirrors v2 suggestion SG-25).",
  "status": "awaiting owner decision"},
 {"id": "S-30",
  "title": "Capture per-player game logs so the last hard blocker can close",
  "problem": ("Every player-level correlation on the site is BLOCKED, the player-props page cannot price anything, "
              "the minutes-and-production half of the injuries page cannot be filled, and strategy S7 has never "
              "generated a bet. All four fail for the same missing input."),
  "proposal": ("Ingest per-player game logs (minutes, points, rebounds, assists, opponent) for at least the players "
               "who appear on an injury report. Start with the injury-report population to bound the cost."),
  "benefit": ("Unblocks the last data dependency in the brief. Everything else on the site can be built, measured "
              "and settled with what is already committed."),
  "effort": "M",
  "risk": "Needs a licensed feed or a scheduled scrape; player-level data is rate-limited more aggressively.",
  "recommendation": "Accept — it is the only remaining hard blocker (mirrors v2 suggestion SG-30).",
  "status": "awaiting owner decision"},
 {"id": "S-31",
  "title": "Decide which tree GitHub Pages serves, and retire the other",
  "problem": ("The repository's Pages setting is build_type 'legacy' (deploy from the main branch root) while the "
              "committed pages.yml workflow publishes the site/ (v2) tree. Whichever is live, the other is a "
              "fully-built site sitting in the repository that a reader can reach by URL, and the two disagree."),
  "proposal": ("Pick the v2 tree as the single published site, point Pages at the pages.yml workflow, and move the "
               "root-level v1 pages under archive/ with a dated note."),
  "benefit": "One site, one set of numbers, no chance of a reader landing on the stale one.",
  "effort": "S",
  "risk": ("Low, but it is a repository setting change that only the owner can make — this session cannot push it "
           "and should not guess."),
  "recommendation": "Accept — one setting, and it decides what every reader sees.",
  "status": "awaiting owner decision"},
 {"id": "S-32",
  "title": "Replace the flat 300-bet gate with a power calculation per strategy",
  "problem": ("Gate G7 applies one round number to all seven strategies. But the parlay strategies have far more "
              "variance per bet than the side strategies, so the same n gives them a much wider interval — the bar "
              "is not equally strict across types, and 300 was chosen before any data existed to check it."),
  "proposal": ("Simulate each strategy's own settled bet stream to get its bet-to-bet correlation, then set the "
               "required n per strategy. The lab already computes every Wilson interval and distance to base rate "
               "needed to do this."),
  "benefit": "Makes the gate a measurement instead of a round number, and tells each strategy how far it has to go.",
  "effort": "S",
  "risk": "Low. Changes when strategies become rank-eligible, so it should be published with its derivation.",
  "recommendation": "Accept (mirrors v2 suggestion SG-26).",
  "status": "awaiting owner decision"},
 {"id": "S-33",
  "title": "Publish the parlay price with its measured correlation, and print the naive product beside it",
  "problem": ("The same-game correlation is now measured (+0.0393, 95% CI -0.113 to +0.190, n=167), but the site "
              "still withholds a parlay price entirely. The honest position is no longer 'we do not know the "
              "correlation' but 'we do not know it precisely' — and withholding the price hides the error bar "
              "rather than showing it."),
  "proposal": ("Price every parlay with the measured rho using the bivariate-normal pricer already implemented and "
               "tested in nba2/v2/strategy_lab.py, and print the naive product on the same row with the interval "
               "between them."),
  "benefit": "Turns an unpriced section into a priced one, with the uncertainty visible instead of implied.",
  "effort": "S",
  "risk": ("The interval is wide, so the price must ship with the interval on the same row or it will be read as "
           "more precise than it is."),
  "recommendation": "Defer until S-29 has grown the sample past ~500 games, then accept (mirrors SG-28).",
  "status": "awaiting owner decision"},
]
added = [s for s in NEW if s["id"] not in have]
d["suggestions"].extend(added)
P.write_text(json.dumps(d, indent=2) + "\n")
print(f"register: +{len(added)} (now {len(d['suggestions'])})")

# --------------------------------------------------------------- live.py wiring
P = pathlib.Path("nba2/v2/live.py")
s = P.read_text()
n = 0


def rep(old, new):
    global s, n
    assert old in s, f"ANCHOR NOT FOUND:\n{old[:200]}"
    s = s.replace(old, new, 1)
    n += 1


rep('''        "S-25": "site", "S-26": "model", "S-27": "governance",
    }
    blocking = {"S-25", "S-26"}''',
    '''        "S-25": "site", "S-26": "model", "S-27": "governance",
        # session arena/ac5fab5c-nba2 (2026-11-14) — written after the results history was completed,
        # so several earlier "blocked, no data" entries now have a cheaper answer.
        "S-29": "data", "S-30": "data", "S-31": "governance", "S-32": "model", "S-33": "parlays",
    }
    blocking = {"S-25", "S-26", "S-29", "S-30", "S-31"}''')

rep('''        "S-27": "The unreachable v1 tree moves under archive/ with dated notes; one generator remains.",
    }''',
    '''        "S-27": "The unreachable v1 tree moves under archive/ with dated notes; one generator remains.",
        "S-29": "Each night's finals are appended automatically, and a mismatch against the standings-implied "
                "game count fails the run instead of silently publishing a stale window.",
        "S-30": "Player-level correlations become measurable, the props page can price, the injuries page can "
                "fill minutes and production, and strategy S7 generates its first bet.",
        "S-31": "One site is live and the other tree is archived with a dated note, so no reader can reach a "
                "second set of numbers.",
        "S-32": "Each strategy gets its own required sample, derived from its own variance instead of one round "
                "number applied to all seven.",
        "S-33": "Every parlay carries a price computed from the measured correlation, with the naive product and "
                "the interval printed on the same row.",
    }''')

rep('''        "S-27": "pages/*.html return 404 on the live site while site/data/teams.json returns 200 — one tree is served",
    }''',
    '''        "S-27": "pages/*.html return 404 on the live site while site/data/teams.json returns 200 — one tree is served",
        "S-29": "the standings were a pre-finals snapshot for a full day and nothing on the site could detect it; "
                "the 183-game log was 28 games short and stayed that way for a day",
        "S-30": "3 of 7 correlations on the lab page are BLOCKED and all three are player-level; S7 has 0 bets",
        "S-31": "the Pages setting is 'legacy' (root of main) while pages.yml publishes site/ — the two trees "
                "disagree and both are reachable",
        "S-32": "G7 holds all seven strategies to the same 300 bets, but their per-bet variances differ sharply: "
                "S1 has 167 settled bets and its interval already excludes chance, while S5 sits at 167 with an "
                "interval that does not",
        "S-33": "rho = +0.0393 with a 95% CI of -0.113 to +0.190; across that band a two-leg price moves by "
                "several percent, which is the whole reason the price is withheld today",
    }''')

rep('''            "source": CAPTURES["standings"] if sid != "S-27" else "https://github.com/wingbangboozle1-lang/NBA2",''',
    '''            "source": (
                "https://github.com/wingbangboozle1-lang/NBA2"
                if sid in ("S-27", "S-31") else
                "https://www.nba.com/stats/players/traditional" if sid == "S-30" else
                "https://www.nba.com/games?date=2026-11-13" if sid == "S-29" else
                CAPTURES["standings"]
            ),''')

P.write_text(s)
print(f"live.py: {n} patches")
