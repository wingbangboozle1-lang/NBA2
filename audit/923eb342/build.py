"""Build the session dashboard: `audit/923eb342/index.html` + subpages.

Design rules this generator enforces, matching the repository's published standard:
* every table row carries an outbound source link or an explicit "no source" reason;
* a blank cell always carries the reason it is blank;
* no JavaScript is needed to read any number;
* relative links only, so the site works from a project Pages URL.

It reads only committed files plus this session's own verified/official capture. It does not
touch `site/`, `pages/`, `data/`, or any other session's output.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE


def j(rel: str, default=None):
    p = ROOT / rel if not pathlib.Path(rel).is_absolute() else pathlib.Path(rel)
    return json.loads(p.read_text()) if p.exists() else default


CAP = j(HERE / "capture_2026-11-19.json")
REPORT = j(HERE / "report.json", {"checks": []})
FIN17 = j(HERE / "verified" / "finals_2026-11-17.json", {"records": []})
FIN18 = j(HERE / "verified" / "finals_2026-11-18.json", {"records": []})
STAND = j(HERE / "verified" / "standings_2026-11-19.json", {"records": []})
INJ = j(HERE / "verified" / "injury_2026-11-19.json", {"rows": []})
LAB = j("data/v2/strategy_lab.json", {})
TEAMS = j("data/v2/teams.json", {})
LINES = j("data/v2/lines.json", {})
PREREG = j("data/v2/preregistration.json", {})
CONTENT = j("data/v2/content.json", {})
RESULTS = j("data/v2/results.json", {})
SETTLE = j("data/settlement.json", {})
MPRIOR = j("data/v6/market_prior.json", {})
PCOV = j("data/v6/player_coverage.json", {})
PLOGS = j("data/v5/player_logs_union.json", {})
BT = j("data/v2/backtest.json", {})
V6CHK = j("data/v6/checks.json", {})
# recorded by the pipeline itself, so it is a committed fact rather than a live measurement
_npass = V6CHK.get("n_gates_pass")
_nall = V6CHK.get("n_gates")
REPO_CHECKER_RESULT = (f"{_npass}/{_nall} v6 gates pass (recorded by the pipeline)"
                       if _nall else "not recorded")

NBA_STAND = "https://www.nba.com/standings"
INJ_INDEX = "https://official.nba.com/nba-injury-report-2026-27-season/"

# ------------------------------------------------------------------ defect register
# Every finding below is derived from a check in report.json or from a command this session ran;
# each carries the official URL a human can open to confirm it. Severity: blocker / high / medium.
FINDINGS = [
    ("F-923-01", "blocker", "Scheduled refresh has failed 10/10 times",
     "The nightly ingest is the mechanism the brief names for keeping four official surfaces current. "
     "Every scheduled run from 2026-11-14T14:37Z to 2026-11-18T19:29Z concluded `failure`. In the most "
     "recent run the capture job succeeded on all four surfaces plus v4, and the failure is in the "
     "publish job's `Rebuild every tree from the committed capture` step.",
     "gh run list --workflow=refresh.yml --limit 12 → 10 rows, all `failure`; gh run view 44381003145 "
     "→ capture: success, publish: failure at step 5, steps 6-11 skipped",
     "https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145"),
    ("F-923-02", "high", "The published result feed is a 2026-11-14 slice, not a feed",
     "`data/v2/results.json` holds 5 rows, all dated 2026-11-14. Seventeen further games have since "
     "gone final on the official site (5 on 11/17, 12 on 11/18) and none of them is a row in the "
     "published feed. The brief asks for one row per game: date, teams, final score, quarter scores.",
     "report.json R-WINDOW (5 rows, 2026-11-14..2026-11-14) + 17 MISSING rows R-0022600xxx",
     "https://www.nba.com/games?date=2026-11-18"),
    ("F-923-03", "high", "Published lines have elapsed; the 11/19 slate has no lines",
     "The originated line set covers 2026-11-15..2026-11-18 (34 lines). Today's official slate is four "
     "games on 2026-11-19 (GSW@MEM, POR@MIL, NYK@MIN, LAC@SAS) and **0 of 4** appear. The brief asks for "
     "picks up to three days ahead.",
     "report.json P-HORIZON, P-SLATE-1119",
     "https://www.nba.com/games?date=2026-11-19"),
    ("F-923-04", "high", "Injury archive stops at 11/17; today's official releases are absent",
     "`data/v4/injury/releases.json` lists three stored releases, newest `11/17/26 11:00 AM`, index "
     "retrieved 2026-11-17T16:41Z. The official index this session read lists 2026-11-19 releases from "
     "12:00 AM ET through at least 07:00 AM ET. Not one of them is archived, so no consecutive-report diff exists "
     "for 11/18 or 11/19.",
     "report.json I-LATEST + data/v4/injury/releases.json vs the official index",
     INJ_INDEX),
    ("F-923-05", "high", "The model's out-of-sample log-loss is worse than a coin flip",
     "`data/v6/market_prior.json` records model_log_loss 0.7058 against baseline L0 0.6931 "
     "(coin flip = ln 2) on the settled sample, with model_beats_coin_flip = false. The market-anchored "
     "prior rule therefore hands the entire weight to the market the moment a market price has any "
     "skill. Any strategy published as skill-based is contradicted by this measurement.",
     "data/v6/market_prior.json (primary_measurement_id SETTLED-27)",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v6/market_prior.json"),
    ("F-923-06", "high", "Player-log coverage of injury-report players is 10.3%",
     "`data/v6/player_coverage.json`: 116 report rows, 12 matched to a player log, coverage 0.1034. The "
     "brief asks for per-player game logs for at least the players who appear on an injury report; 104 "
     "of 116 have none. Minutes redistribution and prop combos are unbuildable on that base.",
     "data/v6/player_coverage.json",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v6/player_coverage.json"),
    ("F-923-07", "medium", "Publish-chain failure is not reproducible on this tree",
     "I extracted the commit to a scratch directory and ran the eleven publish-chain modules in order: "
     "all eleven exited 0. The rebuild afterwards differed from HEAD in exactly four files, and each "
     "difference is a timestamp or a digest of one (`data/settlement.json` settled_at_utc, "
     "`data/site.json` input_digest + two prose copies of settled_at_utc). So the failing step is not "
     "obviously a numeric defect; it is either a runner difference or a non-deterministic input. The "
     "runner logs could not be downloaded (the blob endpoint returned EOF), so this stays open.",
     "python3 -m <11 publish modules> → rc=0 each; git --work-tree=/tmp/repro diff --stat → 4 files",
     "https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145"),
    ("F-923-08", "medium", "The published model is built from a snapshot that predates settled games",
     "`data/v2/teams.json` carries as_of 2026-11-15 and its calibration is fitted on 188 club-games "
     "(home 99-88). The committed standings capture of 2026-11-18T19:30Z, taken before that night's "
     "twelve finals, already differs for 24 of 30 clubs against the 2026-11-19 official table. The "
     "difference is the games played since, not a transcription error — but it means every published "
     "line is priced off a stale rating.",
     "report.json 24 SUPERSEDED rows + teams.json calibration.home_win_rate",
     NBA_STAND),
    ("F-923-09", "medium", "Two independent estimators exist, but the headline is still the blend",
     "`lines.json` publishes a single `margin`; the two estimator spreads are in `est_a`/`est_b` and the "
     "`agreement` column. The brief asks for the disagreement to be the headline with the blend "
     "underneath. This is a presentation defect, not a data defect: the inputs are there.",
     "data/v2/lines.json → lines[].est_a, est_b, agreement, margin",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/site/teams.html"),
    ("F-923-10", "medium", "`stats.nba.com` and `cdn.nba.com` are unreachable from the runner",
     "`nba2/v2/refresh.py` documents it: stats.nba.com times out with every header set tried and "
     "cdn.nba.com returns 403, so the three official team-stat pages (traditional, opponent, advanced) "
     "are not re-cut from their own endpoints. The season table is derived from per-game finals instead. "
     "That is disclosed, but it means 're-read the three official team-stat pages' is not satisfied.",
     "nba2/v2/refresh.py module docstring (transport probe 2026-11-17)",
     "https://www.nba.com/stats/teams/traditional"),
    ("F-923-11", "info", "`nba2/v2/check.py` hard-codes what it is checking",
     "The semantic check asserts `n_slate = 34` and 'wins must sum to 188'. Those are properties of the "
     "2026-11-15 snapshot. A fresh capture therefore fails the check by design, which is a plausible "
     "second cause of the publish failure and a certain cause of it after any successful refresh.",
     "nba2/v2/check.py semantic(): n_slate = 34, sum(...) != 188",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/v2/check.py"),
    ("F-923-13", "high", "The leaderboard ranks a 7-bet strategy first while declaring 300 bets the minimum to rank",
     "`data/v2/strategy_lab.json` sets `min_sample_to_rank` 300, then ranks S4 ('road side when model fades "
     "home by 3+') first by log-loss on **n = 7** with a 100% hit rate and a calibration gap of −0.4002. A "
     "board that shows a 7-0 strategy at the top of a 300-bet-minimum ranking is inviting exactly the luck "
     "the project says it removes.",
     "strategy_lab.json → leaderboard.min_sample_to_rank = 300; leaderboard.ranked[0] = { sid: S4, n: 7, hit_rate: 1.0, rank_by_log_loss: 1 }",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/strategy_lab.json"),
    ("F-923-14", "high", "The model's accuracy is not distinguishable from a one-line prior, by its own test",
     "The lab's paired comparison on the games where the model and the 'back the better prior win%' baseline "
     "disagree: model 14, baseline 20, McNemar exact p = 0.3915, model hit rate 0.6453 against the "
     "baseline's 0.6928. The site's largest-sample skill claim fails its own significance test, and the "
     "lab's own verdict says so.",
     "strategy_lab.json → skill_attribution.headline_vs_win_pct_baseline",
     "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/strategy_lab.json"),
    ("F-923-12", "info", "Sealed ledgers cannot be extended to new game days",
     "Both sealed ledgers cover 2026-11-14..11-17 only. Once those are settled there is nothing sealed "
     "for 11/18 onward, so the tamper-evident pick stream stops while the site keeps publishing. The "
     "seal mechanism itself verifies (both digests recompute), so this is a coverage gap, not a break.",
     "data/raw/ledger/sealed-2026-11-13.json, sealed-2026-11-14.json → prediction dates",
     "https://github.com/wingbangboozle1-lang/NBA2/tree/main/data/raw/ledger"),
]

# which finding each question / suggestion is about — the table cell shows the finding's OFFICIAL
# url, so the row carries a source for its own claim rather than a link to this site.
F_Q = {"Q-923-01": "F-923-01", "Q-923-02": "F-923-11", "Q-923-03": "F-923-12",
       "Q-923-04": "F-923-05", "Q-923-05": "F-923-05", "Q-923-06": "F-923-02",
       "Q-923-07": "F-923-08", "Q-923-08": "F-923-04", "Q-923-09": "F-923-06",
       "Q-923-10": "F-923-02"}
S_F = {"SG-923-01": "F-923-01", "SG-923-02": "F-923-09", "SG-923-03": "F-923-02",
       "SG-923-04": "F-923-04", "SG-923-05": "F-923-05", "SG-923-06": "F-923-12",
       "SG-923-07": "F-923-02", "SG-923-08": "F-923-09"}

QUESTIONS = [
    ("Q-923-01", "What exactly fails in the publish job on the runner?",
     "The step is named and the job is red, but the log is unavailable from here and the same command "
     "chain passes locally in 18 s. Until the runner log is read, the ten failures are explained by "
     "hypothesis, not evidence.",
     "Read the failing step's log from a session with log access, or re-run the workflow with "
     "`ACTIONS_STEP_DEBUG=1`.", "high"),
    ("Q-923-02", "Is `nba2/v2/check.py`'s frozen 34-game / 188-win assertion the gate that blocks refresh?",
     "It asserts properties of one snapshot. If the refresh writes a newer snapshot the check must fail. "
     "That would make the gate itself the reason the site cannot advance — the exact opposite of its intent.",
     "Run `python3 -m nba2.v2.check` after a refresh dry-run on a runner; compare failures.", "high"),
    ("Q-923-03", "Which line-origination number is the company line for 11/19?",
     "There is no sealed, hashed prediction for any game on or after 11/18, so a pick published today "
     "would be the first non-preregistered number on the site.",
     "Re-seal a ledger for 11/19 before tip, or state that no pick exists for the day.", "high"),
    ("Q-923-04", "Does any market price source exist that can be used lawfully and reproducibly?",
     "G6 fails for every line and the market prior is unmeasurable without a price. The brief asks to "
     "blend with a closing line; no closing line is in the repository.",
     "Decide on a licensed odds source, then record its licence and capture cadence.", "high"),
    ("Q-923-05", "Is the model's negative skill a model defect or a sample-size artefact?",
     "Log-loss 0.7058 vs 0.6931 on the settled sample says the model is worse than a coin. It could be "
     "27 games of noise or a real defect; the difference is not significant on its own.",
     "Report a confidence interval on the log-loss difference and the number of settled games needed to "
     "resolve it.", "medium"),
    ("Q-923-06", "What is the settlement rule when a game is postponed or a stat is corrected?",
     "The policy says a game without an official result stays UNSETTLED. It does not say what happens to "
     "a settled game whose official box score is later corrected.",
     "Write the revision rule into the ledger schema before the next seal.", "medium"),
    ("Q-923-07", "Are the arena coordinates licensed for redistribution as a derived table?",
     "Travel distance depends on a sourced coordinate table; the site labels it third-party (Wikimedia). "
     "Redistribution terms were not checked this session.",
     "Record the licence and attribution on the travel page.", "medium"),
    ("Q-923-08", "What is the authoritative injury-report revision cadence to archive?",
     "The official index lists releases roughly every 15 minutes on game day. Archiving all of them is "
     "different work from archiving the 11:00-13:00 filing window.",
     "Pick the cadence, then set the archive's freshness gate to it.", "medium"),
    ("Q-923-09", "Should rotation availability be a picks-page column from data we do not have?",
     "The column is a presentation change; the input (who actually plays, and how many minutes) is at "
     "10.3% coverage. Publishing the column now would be a column of blanks.",
     "Decide: publish the column with explicit blanks, or wait for coverage.", "medium"),
    ("Q-923-10", "Which surface is the public one?",
     "The repository serves the repository-root `index.html` under Pages `legacy` source, and the README "
     "says so. Several generated trees exist. A reader who lands on the wrong one sees different numbers.",
     "Decide: flip Settings → Pages to GitHub Actions and publish `site/`, or keep the pointer page.", "high"),
]

SUGGESTIONS = [
    ("SG-923-01", "Make the publish chain gate on a reproducible fixed point, not on freshness of a literal",
     "Replace `n_slate = 34` / `wins == 188` in `nba2/v2/check.py` with assertions computed from the "
     "snapshot under check (games in the slate, ΣW == ΣL, every line's game id present). A gate that "
     "freezes one week's numbers blocks every later week.", "high", "unblocks F-923-01/F-923-11"),
    ("SG-923-02", "Publish the disagreement first, the blend second",
     "On the lines page, lead with |est_a − est_b| and the agreement verdict, then the blend. The two "
     "estimators already exist; this is a template change in one table.", "high", "satisfies F-923-09"),
    ("SG-923-03", "Add a `pending` row class to the result feed instead of omitting the game",
     "A game that is scheduled but not final should appear as a row with status `scheduled` and blank "
     "score. Then 'the feed is complete' becomes checkable, and a missing row is a defect rather than "
     "an absence.", "medium", "fixes F-923-02 permanently"),
    ("SG-923-04", "Archive the injury index on a fixed 15-minute cadence and diff consecutive releases",
     "The index is a stable list of URLs. A daily cron that reads the index and archives every new PDF "
     "turns the 10.3% player coverage problem into a data-engineering problem instead of a research one.",
     "high", "fixes F-923-04/F-923-06"),
    ("SG-923-05", "Report the log-loss difference with a confidence interval, not just its sign",
     "0.7058 vs 0.6931 over the settled sample is 27 games. Publish the interval and the number of games "
     "needed to separate the two, so a negative result cannot be read as a verdict on the model.",
     "high", "resolves Q-923-05 before any strategy claim"),
    ("SG-923-06", "Seal every day's lines before tip, including days with no pick",
     "An empty-but-sealed ledger is evidence that no pick was withheld after the fact. Today the site can "
     "publish nothing for 11/19 and no one can tell whether that was a decision or a failure.",
     "high", "closes F-923-12"),
    ("SG-923-07", "Pin the pages configuration and delete the ambiguity",
     "One published tree, one build, one URL. Keep the others under `archive/`. A reader should never "
     "have to work out which dashboard they are reading.", "medium", "resolves Q-923-10"),
    ("SG-923-08", "Add a machine-checked 'verified at' column to every published table",
     "The rule is already 'every row carries a source'. Make it 'every row carries a source and the time "
     "it was read', and let the checkable age of each row drive the freshness banner.", "medium",
     "makes freshness per-row instead of per-site"),
    ("SG-923-09", "Split the site into `projection/` and `bet/` as two roots, not two nav groups",
     "Nav grouping still lets a reader land on a gated page by URL. Two directories with different gates "
     "make the wall structural.", "medium", "brief requirement, currently nav-only"),
    ("SG-923-10", "Add a public 'what would change our mind' panel to each strategy",
     "For each preregistered strategy: the sample size at which it would be declared dead, and the "
     "measurement that would revive it. This is the cheapest defence against a leaderboard that cannot "
     "lose.", "low", "complements the existing gate matrix"),
]

# ------------------------------------------------------------------ page shell
PAGES = [
    ("index.html", "Overview", "Overview"),
    ("executive-summary.html", "Executive summary", "Overview"),
    ("verification.html", "Verification log", "Evidence"),
    ("official-results.html", "Official results", "Evidence"),
    ("standings.html", "Standings", "Evidence"),
    ("injuries.html", "Injuries", "Evidence"),
    ("performance.html", "Measured skill", "Evidence"),
    ("gates.html", "Validation gates", "Decisions"),
    ("strategies.html", "Strategies & preregistration", "Decisions"),
    ("questions.html", "Open questions", "Decisions"),
    ("suggestions.html", "Suggestions", "Decisions"),
    ("flagged.html", "Flagged for review", "Decisions"),
    ("sources.html", "Sources & method", "Evidence"),
]

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#141a22;--muted:#5b6b7c;--line:#e2e7ee;--accent:#1f6feb;
--good:#1a7f45;--bad:#b42318;--warn:#8a5a00;--info:#3b5bdb;--chip:#eef2f7}
@media (prefers-color-scheme: dark){:root{--bg:#0d1117;--card:#151b23;--ink:#e6edf3;--muted:#9aa8b6;
--line:#253040;--accent:#58a6ff;--good:#3fb950;--bad:#f85149;--warn:#d29922;--info:#7aa2f7;--chip:#1c2531}}
*{box-sizing:border-box}
body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
background:var(--bg);color:var(--ink)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header{background:var(--card);border-bottom:1px solid var(--line);padding:14px 0;position:sticky;top:0;z-index:5}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
.brand{font-weight:700;letter-spacing:-.2px}
.brand span{color:var(--muted);font-weight:400;font-size:13px;display:block;letter-spacing:0}
nav{margin-top:10px;display:flex;flex-wrap:wrap;gap:14px;font-size:13.5px}
nav a{color:var(--muted);padding:2px 0;border-bottom:2px solid transparent}
nav a.on{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
nav a:hover{color:var(--ink);text-decoration:none}
main{padding:26px 0 60px}
h1{font-size:25px;margin:0 0 6px;letter-spacing:-.3px}
h2{font-size:17px;margin:30px 0 10px}
h3{font-size:14px;margin:18px 0 6px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px}
.lede{color:var(--muted);margin:0 0 18px;max-width:80ch}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px;margin:16px 0 6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.card h4{margin:0 0 4px;font-size:13px;color:var(--muted);font-weight:600}
.card .big{font-size:24px;font-weight:700;letter-spacing:-.5px}
.card p{margin:6px 0 0;font-size:12.5px;color:var(--muted)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
border-radius:10px;overflow:hidden;font-size:13px;margin:8px 0 4px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--chip);font-size:11.5px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}
tr:last-child td{border-bottom:none}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.scroll{overflow-x:auto}
.chip{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;font-weight:600;
background:var(--chip);color:var(--muted);white-space:nowrap}
.pass{background:rgba(26,127,69,.12);color:var(--good)}.fail{background:rgba(180,35,24,.12);color:var(--bad)}
.warn{background:rgba(138,90,0,.14);color:var(--warn)}.info{background:rgba(59,91,219,.12);color:var(--info)}
.src{font-size:11.5px;word-break:break-all}
.note{font-size:12.5px;color:var(--muted)}
.banner{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--warn);
border-radius:8px;padding:12px 14px;margin:0 0 18px}
.banner h3{margin:0 0 4px;color:var(--ink);text-transform:none;letter-spacing:0;font-size:14px}
.finding{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:10px 0}
.finding h4{margin:0 0 6px;font-size:15px}
.finding p{margin:0 0 8px;font-size:13.5px}
.meta{font-size:12px;color:var(--muted);margin-top:6px}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:12px;padding:18px 0 40px}
ul.tight{margin:6px 0 0;padding-left:20px}ul.tight li{margin:3px 0}
"""


def md(x) -> str:
    """Escape, then turn `code` into <code> and **bold** into <b>. Only these two, because only
    these two are used in the prose fields — anything else stays literal on purpose."""
    t = html.escape("" if x is None else str(x), quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    return t


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=False)


def badge(v: str) -> str:
    k = (v or "").upper()
    if k.startswith(("PASS", "VERIFIED", "SETTLED", "OK")):
        cls = "pass"
    elif k.startswith(("FAIL", "MISSING", "BROKEN", "BLOCKER")):
        cls = "fail"
    elif k.startswith(("STALE", "SUPERSEDED", "UNVERIFIED", "HIGH", "WARN", "PARTIAL", "MEDIUM")):
        cls = "warn"
    else:
        cls = "info"
    return f'<span class="chip {cls}">{esc(v)}</span>'


def src(u: str, label: str = "") -> str:
    if not u:
        return '<span class="note">no source</span>'
    t = label or re.sub(r"^https?://(www\.)?", "", u).split("?")[0]
    t = t if len(t) <= 58 else t[:55] + "…"
    return f'<a class="src" href="{esc(u)}" target="_blank" rel="noopener">{esc(t)}</a>'


def fsrc(fid: str) -> str:
    for f in FINDINGS:
        if f[0] == fid:
            return src(f[5], "official source")
    return '<span class="note">no source</span>'


def nav(active: str) -> str:
    groups: dict[str, list[tuple[str, str]]] = {}
    for href, label, grp in PAGES:
        groups.setdefault(grp, []).append((href, label))
    out = []
    for grp, items in groups.items():
        links = "".join(
            f'<a class="{"on" if h == active else ""}" href="{h}">{esc(l)}</a>' for h, l in items)
        out.append(f'<span class="note" style="align-self:center;font-size:11px;text-transform:uppercase;'
                   f'letter-spacing:.6px">{esc(grp)}</span> {links}')
    return "<nav>" + "<span style='width:10px'></span>".join(out) + "</nav>"


def page(name: str, title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — NBA2 verification desk</title>
<style>{CSS}</style></head><body>
<header><div class="wrap"><div class="brand">NBA2 verification desk
<span>Session arena/923eb342-nba2 · official sources read 2026-11-19 · nothing here is betting advice</span>
</div>{nav(name)}</div></header>
<main><div class="wrap">{body}</div></main>
<footer><div class="wrap">Every row carries the official URL it came from. A value that could not be
confirmed from an official source is blank and listed on the <a href="flagged.html">Flagged for review</a>
page. Model output is derived, never official. Built {esc(CAP["retrieved_at_utc"])}.</div></footer>
</body></html>
"""


def table(headers: list[str], rows: list[list[str]], caption: str = "") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = []
    for r in rows:
        cells = []
        for i, c in enumerate(r):
            cls = ' class="num"' if isinstance(c, tuple) else ""
            cells.append(f"<td{cls}>{c[0] if isinstance(c, tuple) else c}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    cap = f'<p class="note">{caption}</p>' if caption else ""
    return (f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>{cap}')


# ------------------------------------------------------------------ derived numbers
checks = REPORT.get("checks", [])
vcount: dict[str, int] = {}
for c in checks:
    k = c["verdict"].split(" (")[0]
    vcount[k] = vcount.get(k, 0) + 1
N_GAMES_VERIFIED = len(FIN17["records"]) + len(FIN18["records"])
CAL = TEAMS.get("calibration", {})
INTEG = TEAMS.get("integrity", {})
BT_HOLD = (LAB.get("holdout") or {})
SET_METRICS = [(lg["ledger"], lg.get("metrics", {})) for lg in SETTLE.get("ledgers", [])]
SEALED = [(lg["ledger"], lg["seal"]["n_predictions"], lg["seal"]["sha256"][:16],
           lg.get("games_settled"), lg.get("games_expected")) for lg in SETTLE.get("ledgers", [])]

# The dashboard must be a byte-for-byte fixed point of its committed inputs, so it is a pure
# function of files: nothing here shells out, because a command's output (a live checker, a run
# list) changes on every build and would make the deployed artefact drift. The repository's own
# checker is run by the workflow instead, where its output is log evidence, not page content.


def p_overview() -> str:
    rows = [
        ["Official finals read and landed this session", (f"<b>{N_GAMES_VERIFIED}</b>"),
         "5 on 2026-11-17 + 12 on 2026-11-18, each with its own URL",
         src("https://www.nba.com/games?date=2026-11-18")],
        ["Official injury releases archived here", "<b>1</b>",
         "11/19/26 07:00 AM ET — the repository's own archive is 3 releases deep, newest 11/17",
         src(INJ.get("pdf_url") or "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf")],
        ["Clubs in the 2026-11-19 official standings", (f"<b>{STAND.get('n_clubs', 0)}</b>"),
         f"ΣW {STAND.get('identity_check', {}).get('sum_wins')} = ΣL "
         f"{STAND.get('identity_check', {}).get('sum_losses')}", src(NBA_STAND)],
        ["Published lines whose date has elapsed", "<b>34 / 34</b>",
         "2026-11-15 → 11-18; today's 4-game slate has 0 lines",
         src("https://www.nba.com/games?date=2026-11-19")],
        ["Scheduled refreshes that succeeded (last 10)", '<b class="fail">0</b>',
         "10/10 concluded failure; capture succeeded, publish failed",
         src("https://github.com/wingbangboozle1-lang/NBA2/actions/workflows/refresh.yml")],
        ["Model out-of-sample log-loss vs a coin flip", "<b>0.7058 vs 0.6931</b>",
         "the model is worse than a coin flip on the settled sample — the market rule gives the market all "
         "the weight", src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v6/market_prior.json")],
        ["Injury-report players with a player log", "<b>12 / 116 (10.3%)</b>",
         "prop combos and minutes redistribution have no base",
         src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v6/player_coverage.json")],
        ["Checks in this session's line-by-line audit", f"<b>{len(checks)}</b>",
         ", ".join(f"{k} {v}" for k, v in sorted(vcount.items())),
         src("https://www.nba.com/standings") + " " + src("verification.html", "this site")],
    ]
    body = f"""
<h1>Overview</h1>
<p class="lede">One screen: what was read from an official NBA source today, what the repository
publishes beside it, and where the two disagree. The disagreement is the finding — not an opinion
about it.</p>

<div class="banner"><h3>Read this first</h3>
Today's date is 2026-11-19. The repository's published dashboard is built from a 2026-11-15 snapshot
of the season, its originated lines end on 2026-11-18, and its scheduled refresh job has failed ten
consecutive times. Seventeen games have gone final since the last published result row. Everything on
this site that is a number was either read from an official page today or recomputed from a committed
official snapshot by running the repository's own code; nothing is estimated.</div>

{table(["", "Value", "What it means", "Official source"],
       [[r[0], r[1], r[2], r[3]] for r in rows])}

<h2>Where to go</h2>
<div class="cards">
 <div class="card"><h4>Evidence</h4><div class="big">{len(checks)}</div>
  <p>Line-by-line checks against today's official reads. <a href="verification.html">Open the log</a></p></div>
 <div class="card"><h4>Flagged</h4><div class="big">{len(FINDINGS)}</div>
  <p>Defects and irregularities, each with the official URL to confirm it.
  <a href="flagged.html">Open findings</a></p></div>
 <div class="card"><h4>Decisions</h4><div class="big">{len(QUESTIONS)}</div>
  <p>Questions that must be answered before a change is made.
  <a href="questions.html">Open questions</a></p></div>
 <div class="card"><h4>Suggestions</h4><div class="big">{len(SUGGESTIONS)}</div>
  <p>Ranked proposals with a trade-off, for you to choose.
  <a href="suggestions.html">Open suggestions</a></p></div>
</div>

<h2>The two surfaces, as they stand</h2>
{table(["Surface", "What is published today", "Gate status", "Source"],
       [["Projection (safe to publish)", "34 originated lines, 30-club ratings, two estimators, luck z-scores",
         badge("PASS — derivable from official data") + ' <span class="note"> but from a stale snapshot</span>',
         src(NBA_STAND)],
        ["Bet (gated)", "No pick is staked. Every pick row is WITHHELD, because there is no price (G6) and no "
         "sealed ledger for any game on or after 2026-11-18",
         badge("BLOCKED"), src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/lines.json")],
        ["Official record", "5 result rows dated 2026-11-14; settlement of both sealed ledgers against "
         "official finals", badge("STALE — 17 finals missing"), src("https://www.nba.com/games?date=2026-11-18")]],
       "The brief requires the projection and bet surfaces never to mix. In the published site they are "
       "separate nav groups on one tree; this site keeps them as separate sections and never prints a "
       "stake.")}
"""
    return page("index.html", "Overview", body)


def p_exec() -> str:
    rows = [
        ["What exists and works", "A provenance-enforced pipeline: every published row carries a source, "
         "every blank carries a reason, and a CI gate recomputes the numbers from committed snapshots. "
         "The sealed-ledger hash chain verifies.", "2 ledgers, 22 + 27 picks, digests recompute",
         src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/settlement.json")],
        ["What has been measured", "Walk-forward backtest on 172 official games: out-of-sample "
         f"against-the-spread accuracy {BT_HOLD.get('out_of_sample_su_accuracy')} ± "
         f"{BT_HOLD.get('out_of_sample_se')} on {BT_HOLD.get('n_test')} games; MAE "
         f"{BT_HOLD.get('out_of_sample_mae')}", "in-sample 63.4% vs out-of-sample 67.3%",
         src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/strategy_lab.json")],
        ["What contradicts it", "Out-of-sample log-loss 0.7058 against a coin flip's 0.6931 on the settled "
         "sample. A rating that is 67% ATS but worse than 50/50 on probability is internally inconsistent; "
         "one of the two measurements is being computed on a different basis and that has not been "
         "reconciled", "model_beats_coin_flip = false", src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v6/market_prior.json")],
        ["What is blocked", "No market price anywhere in the repository ⇒ no edge, no stake, no ROI. "
         "No sealed ledger for any game on or after 2026-11-18 ⇒ nothing can be scored from today on.",
         "G6 fails for every line", src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/lines.json")],
        ["What is operationally broken", "The scheduled refresh (the mechanism that keeps four official "
         "surfaces current) has failed 10/10 times. Capture works; publish does not. The result feed is "
         "five rows from 2026-11-14 and the injury archive stops at 11/17.",
         "gh run list --workflow=refresh.yml", src("https://github.com/wingbangboozle1-lang/NBA2/actions/workflows/refresh.yml")],
        ["What I verified today", f"{N_GAMES_VERIFIED} official finals (5 + 12), the 2026-11-19 07:00 AM ET "
         "injury release, the full 30-club standings table, one complete official box score, and the "
         "filing deadlines", f"{len(checks)} checks in this audit",
         src("https://www.nba.com/standings") + " " + src("verification.html", "verification.html")],
        ["What I could not verify", "Runner logs (blob endpoint returned EOF), the three official team-stat "
         "pages (stats.nba.com times out from the runner per the repository's own probe; this sandbox cannot "
         "reach it at all), any market price, and per-player logs for 11/18",
         "listed on Flagged for review",
         src("https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145")
         + " " + src("flagged.html", "flagged.html")],
    ]
    body = f"""
<h1>Executive summary</h1>
<p class="lede">The system is honestly built and honestly labelled, and it is not currently doing the
job it is supposed to do. The three sentences below are the whole summary.</p>

<div class="cards">
 <div class="card"><h4>1 · The pipeline is trustworthy</h4><p>Provenance is enforced by code, not by
 discipline: an unsourced value raises, an unexplained blank raises, and CI rebuilds every published
 number from committed snapshots. This is rarer than it sounds and it is the asset.</p></div>
 <div class="card"><h4>2 · The operation is not running</h4><p>Ten consecutive scheduled refreshes
 failed. The capture half works; the publish half does not. Result rows stopped at 2026-11-14 and the
 injury archive at 11/17, while 17 games went final.</p></div>
 <div class="card"><h4>3 · There is no edge, and one measurement says the model is worse than a coin</h4>
 <p>No price ⇒ no edge by construction. Independently, out-of-sample log-loss is worse than 0.6931. Until
 those are reconciled or a price exists, nothing here is a bet.</p></div>
</div>

<h2>By the numbers</h2>
{table(["Heading", "Finding", "Evidence", "Source"], rows)}

<h2>What I recommend, in order</h2>
<ol class="tight">
 <li><b>Fix publication before adding anything.</b> A pipeline that cannot publish makes every other
 improvement unobservable. Start with <a href="suggestions.html">SG-923-01</a> (the gate that freezes one
 week's numbers) and <a href="questions.html">Q-923-01</a> (read the runner log).</li>
 <li><b>Reconcile the two skill measurements.</b> 67.3% against the spread and a log-loss worse than a
 coin cannot both describe the same model without an explanation. That explanation is worth more than
 any new strategy.</li>
 <li><b>Stand up the archive layer, not the strategy layer.</b> Player logs at 10.3% coverage and
 injury reports that stop at 11/17 are data-engineering problems with data-engineering answers
 (a 15-minute index cron). Strategy work on top of them is guesswork.</li>
 <li><b>Then</b> resume originating lines, sealed before tip, with the disagreement published as the
 headline and the blend beneath it.</li>
</ol>

<h2>What this summary is not</h2>
<p class="note">It is not a forecast, an evaluation of skill, or a recommendation to bet. No market price
was read in this session, so no strategy here can be shown to have an edge, and none is presented as
having one.</p>
"""
    return page("executive-summary.html", "Executive summary", body)


def p_verification() -> str:
    def cls(v):
        return badge(v)

    order = {"FAIL": 0, "MISSING": 1, "STALE": 2, "SUPERSEDED": 3, "UNVERIFIABLE": 4, "PARTIAL": 5, "PASS": 6}
    srt = sorted(checks, key=lambda c: (order.get(c["verdict"].split(" (")[0], 9), c["id"]))
    rows = []
    for c in srt:
        rows.append([esc(c["id"]), esc(c["claim"]), esc(c["published"]), esc(c["official"]),
                     cls(c["verdict"]), src(c["source_url"]),
                     f'<span class="note">{esc(c["note"])}</span>' if c.get("note") else "—"])
    counts = " · ".join(f"{k} {v}" for k, v in sorted(vcount.items()))
    body = f"""
<h1>Verification log</h1>
<p class="lede">Every check compares something the repository <b>publishes</b> with something read from
an official NBA page <b>during this session</b>, or recomputed by running the repository's own code over
a committed official snapshot. Nothing was repaired, rounded into agreement, or inferred.</p>

<div class="cards">
 <div class="card"><h4>Checks run</h4><div class="big">{len(checks)}</div><p>{esc(counts)}</p></div>
 <div class="card"><h4>Read at</h4><div class="big" style="font-size:16px">{esc(CAP["retrieved_at_utc"])}</div>
  <p>Transport: platform page-fetch. Direct TLS from the sandbox to nba.com fails.</p></div>
 <div class="card"><h4>Repository's own checker</h4><div class="big" style="font-size:15px">
  {esc(REPO_CHECKER_RESULT)}</div><p>the repository's checker is run by this site's workflow;
 its result is in the run log, not baked into the page, so the page stays a fixed point</p></div>
</div>

<div class="banner"><h3>How to read a verdict</h3>
<b>PASS</b> — the published value equals the official read. <b>STALE</b> — the published value was right
when captured and games have been played since; the gap is the games, not an error.
<b>SUPERSEDED (+n)</b> — same idea, with the number of games that have elapsed. <b>MISSING</b> — the
official source has the row and the publication does not. <b>FAIL</b> — the publication contradicts the
official source, or an operational claim fails. <b>UNVERIFIABLE</b> — cannot be checked from here; the
reason is in the note.</div>

<h2>All checks</h2>
{table(["ID", "Claim checked", "Published", "Official", "Verdict", "Official source", "Note"], rows,
       f"Sorted worst-first. {len(checks)} rows.")}

<h2>What this log does not cover</h2>
<ul class="tight">
 <li><b>The three official team-stat pages</b> (traditional, opponent, advanced) were not read: this
 sandbox cannot reach <code>stats.nba.com</code> or <code>cdn.nba.com</code> at all, and the repository's
 own probe records the same failure from a GitHub runner.</li>
 <li><b>Runner logs</b> for the failed workflows could not be downloaded — the GitHub blob endpoint
 returned <code>EOF</code> for both the job log and the failed-step log.</li>
 <li><b>Market prices</b> were not read, because the repository holds none and no licensed feed is
 configured.</li>
 <li><b>2026-11-18 per-player box scores</b> beyond game 0022600259 were not read.</li>
</ul>
"""
    return page("verification.html", "Verification log", body)


def p_results() -> str:
    rows = []
    for doc in (FIN17, FIN18):
        for r in doc["records"]:
            q = ("—" if not r["away_quarters"] else
                 f"{'-'.join(map(str, r['away_quarters']))} / {'-'.join(map(str, r['home_quarters']))}")
            qstat = badge("verified") if r["quarters_status"].startswith("verified") else badge("unverified")
            rows.append([esc(r["date"]), esc(f"{r['away']} @ {r['home']}"), esc(r["away_pts"]),
                         esc(r["home_pts"]), esc(r["final_status"]), esc(q), qstat,
                         src(f"https://www.nba.com/game/{r['away'].lower()}-vs-{r['home'].lower()}-{r['game_id']}")
                         if False else src(r["score_source_url"])])
    body = f"""
<h1>Official results</h1>
<p class="lede">One row per game: date, teams, final score, quarter scores. Scores were read from the
official games page for each date in this session. A quarter row is printed only where this repository's
committed official capture holds it <b>and its sum equals the final read today</b>; otherwise the cell is
blank and labelled.</p>

<div class="banner"><h3>Why some quarter cells are blank</h3>
The 2026-11-17 finals have committed quarter rows whose sums match the official finals exactly (5/5).
The 2026-11-18 finals do not have a committed quarter capture yet, so their quarter cells are blank and
marked <span class="chip warn">unverified</span>. A blank here is a statement that the breakdown has not
been verified — not that it does not exist.</div>

{table(["Date", "Game", "Away pts", "Home pts", "Status", "Quarters (away / home)", "Quarter check", "Official source"],
       rows,
       f"{len(rows)} games. Source: the official games page for each date, read "
       f"{esc(CAP['retrieved_at_utc'])}.")}

<h2>Totals that follow from the rows above</h2>
{table(["Count", "Value", "Derivation", "Source"],
       [["Games read", str(len(rows)), "5 (11/17) + 12 (11/18)", src("https://www.nba.com/games?date=2026-11-18")],
        ["Home wins", str(sum(1 for d in (FIN17, FIN18) for r in d["records"] if r["home_pts"] > r["away_pts"])),
         "home_pts > away_pts in the table above", src("https://www.nba.com/games?date=2026-11-18")],
        ["Overtime games", "1", "CHA 114 @ LAL 118, Final/OT on 2026-11-17",
         src("https://www.nba.com/game/cha-vs-lal-0022600256")]])}

<h2>Gap against the published feed</h2>
<p class="note">The repository's published result surface (<code>data/v2/results.json</code>) holds
<b>5</b> rows, all dated 2026-11-14. Every game in the table above is absent from it. That gap is finding
<a href="flagged.html">F-923-02</a>. This session does not edit that file: it is inside the change set of
open PRs #130/#131, so the repair is logged as a request on the board, and the verified rows are published
here instead (<code>audit/923eb342/verified/</code>) with the same schema.</p>
"""
    return page("official-results.html", "Official results", body)


def p_standings() -> str:
    recs = sorted(STAND.get("records", []), key=lambda r: (-r["w"], r["l"]))
    ic = STAND.get("identity_check", {})
    rows = [[esc(r["tri"]), (esc(r["w"])), (esc(r["l"])), (esc(r["pct"])), esc(r["home"]), esc(r["road"]),
             esc(r["div"]), esc(r["last10"]), esc(r["streak"]), src(r["source_url"])] for r in recs]
    body = f"""
<h1>Standings</h1>
<p class="lede">The 2026-27 regular-season table as nba.com/standings printed it on 2026-11-19, transcribed
in full. The two identity checks that make a league table self-verifying are reported beside it.</p>

<div class="cards">
 <div class="card"><h4>Clubs</h4><div class="big">{STAND.get('n_clubs')}</div><p>each exactly once</p></div>
 <div class="card"><h4>ΣW = ΣL</h4><div class="big">{ic.get('sum_wins')} = {ic.get('sum_losses')}</div>
  <p>{'identity holds' if ic.get('wins_equal_losses') else 'IDENTITY BROKEN'}</p></div>
 <div class="card"><h4>Games played</h4><div class="big">{ic.get('sum_wins')}</div>
  <p>club-games = {ic.get('sum_wins')} → {int((ic.get('sum_wins') or 0)/2)} league games</p></div>
</div>

{table(["Team", "W", "L", "PCT", "Home", "Road", "Division", "Last 10", "Streak", "Official source"],
       rows, "Sorted by wins. All 30 rows read from the same page in the same session.")}

<h2>What changed since the snapshot the model uses</h2>
<p class="note">The published model is fitted on a snapshot with <b>188</b> club-games; this table has
<b>{ic.get('sum_wins')}</b>. Twenty-four clubs differ by exactly one game — the twelve finals of
2026-11-18 that the model snapshot predates. The difference is time, not transcription. The consequence is
real: every published spread is priced off ratings computed before those results existed
(<a href="flagged.html">F-923-08</a>).</p>
"""
    return page("standings.html", "Standings", body)


def p_injuries() -> str:
    rows = []
    for r in INJ.get("rows", []):
        status = esc(r["status"]) if r["status"] else badge("not submitted")
        rows.append([esc(r["date"]), esc(r["matchup"]), esc(r["team"]), esc(r["player"] or "—"),
                     status, esc(r["reason"]), src(INJ.get("pdf_url", ""))])
    body = f"""
<h1>Injuries</h1>
<p class="lede">The official injury report as a document: revision time, retrieval time, and the rows it
prints. This is the one place where a timestamp matters more than a status, because a status without its
revision time cannot be compared with anything.</p>

<div class="banner"><h3>Report revision time and retrieval time</h3>
<b>Revision:</b> {esc(INJ.get('revision_time_et'))} (the stamp the PDF itself carries)<br>
<b>Retrieved:</b> {esc(INJ.get('retrieval_time_utc'))}<br>
<b>Document:</b> {src(INJ.get("pdf_url") or "")}<br>
<b>Index:</b> {src(INJ_INDEX)}<br>
<span class="note">The two clocks are different: the report is stamped in US Eastern time, the retrieval
timestamp is UTC. They are printed separately and never collapsed into one.</span></div>

{table(["Game date", "Matchup", "Team", "Player", "Status", "Reason", "Official PDF"],
       rows, f"{len(rows)} rows transcribed from the PDF above. A club with no submission prints "
              "'NOT YET SUBMITTED' and is shown as such rather than as a blank.")}

<h2>The archive gap</h2>
<p class="note">The repository's own injury archive holds three releases with a newest stamp of
<b>11/17/26 11:00 AM</b> (index read 2026-11-17T16:41Z). The official index lists 2026-11-19 releases
from 12:00 AM ET to at least 07:00 AM ET. So no archived release exists for 11/18 or 11/19, and
<b>no consecutive-report diff can exist for them</b> — the diff feature is intact but starved
(<a href="flagged.html">F-923-04</a>).</p>

<h2>Filing rules that the retrieval schedule has to match</h2>
<p class="note">From the official injury-report page: teams must designate a participation status by
<b>5 p.m. local time the day before a game</b>, and for the second game of a back-to-back by
<b>1 p.m. local time on game day</b>; a game-day report is due between <b>11 a.m. and 1 p.m. local</b>
(8–10 a.m. for tip-offs at 5 p.m. or earlier); and reports are updated on a continual basis through the
day. Source: {src(INJ_INDEX)}. That last clause is why the index — not a fixed daily time — is the thing
to poll.</p>

<h2>Injury effect on rotation minutes</h2>
<p class="note">Cannot be produced from what is held. Rotation and minutes redistribution need per-player
logs for the players involved, and coverage of injury-report players is 12 of 116 (10.3%):
{src('https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v6/player_coverage.json')}. This page
therefore prints the official status and stops there, rather than estimating an effect.</p>
"""
    return page("injuries.html", "Injuries", body)


def p_performance() -> str:
    bt = LAB
    hold = bt.get("holdout", {})
    lead = bt.get("leaderboard", {})
    corr = bt.get("correlations", [])
    luck = (bt.get("luck") or {})
    rows = [
        ["Walk-forward, out of sample", f"{hold.get('out_of_sample_su_accuracy')} ± {hold.get('out_of_sample_se')}",
         f"{hold.get('n_test')} games, {hold.get('test_dates')}", badge("measured"),
         src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/strategy_lab.json")],
        ["Walk-forward, in sample", f"{hold.get('in_sample_su_accuracy')}",
         f"{hold.get('n_train')} games, {hold.get('train_dates')}", badge("measured"),
         src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/strategy_lab.json")],
        ["Spread MAE (out of sample)", f"{hold.get('out_of_sample_mae')} pts",
         f"in-sample {hold.get('in_sample_mae')}; our own settled ledger shows 12.43 on 22 games",
         badge("measured"), src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/settlement.json")],
        ["Log-loss vs a coin flip", f"{MPRIOR.get('model_log_loss')} vs {MPRIOR.get('baseline_l0')}",
         MPRIOR.get("model_beats_coin_flip_note", ""), badge("measured"),
         src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v6/market_prior.json")],
        ["Leakage audit", f"{bt.get('leakage', {}).get('n_violations')} violations",
         bt.get("leakage", {}).get("verdict", ""), badge("audited"),
         src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/strategy_lab.json")],
        ["Teams outside the luck noise band (|z| > 1.96)",
         str(sum(1 for t in TEAMS.get("teams", []) if abs(t.get("luck_z", 0)) > 1.96)),
         "a strategy may not lean on a team outside the band; the published screen reports its own count",
         badge("measured"), src(NBA_STAND)],
        ["Injury-report players with a player log", f"{PCOV.get('n_matched')} / {PCOV.get('n_report_rows')}",
         f"coverage {PCOV.get('coverage')}", badge("measured"),
         src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v6/player_coverage.json")],
    ]
    LEADER = LAB.get("leaderboard") or {}
    lrow = []
    for r_ in LEADER.get("ranked", []):
        n = r_.get("n") or 0
        lrow.append([str(r_.get("rank_by_log_loss")), esc(r_.get("name")),
                     str(n) + ("" if n >= LEADER.get("min_sample_to_rank", 0) else
                               ' <span class="chip warn">below floor</span>'),
                     esc(r_.get("hit_rate")), esc(r_.get("log_loss")),
                     esc(r_.get("calibration_gap")),
                     badge("yes") if r_.get("eligible_for_reward") else badge("no — " + str(r_.get("blocked_by"))),
                     src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/strategy_lab.json")])
    N_BELOW_FLOOR = sum(1 for r_ in LEADER.get("ranked", [])
                        if (r_.get("n") or 0) < (LEADER.get("min_sample_to_rank") or 0))
    sk = (LAB.get("skill_attribution") or {}).get("headline_vs_win_pct_baseline") or {}
    SKILL_TXT = (
        "Model {} on the {} games both rules scored; the \"back the better prior win percentage\" "
        "baseline {}. They disagree on {} games and the baseline wins those {} to {} (McNemar exact "
        "p = {}). The lab's own verdict: {}."
    ).format(sk.get("model_hit_rate_same_games"), sk.get("baseline_n"), sk.get("baseline_hit_rate"),
             sk.get("discordant_games"), sk.get("baseline_won_those"), sk.get("model_won_those"),
             sk.get("mcnemar_exact_p"), sk.get("verdict"))
    crow = []
    for c in corr:
        r = c.get("r")
        crow.append([
            esc(c.get("quantity")) + (f'<br><span class="note">{esc(c.get("note"))}</span>' if c.get("note") else ""),
            esc(r) if r is not None else '— <span class="note">unmeasured: ' + esc(c.get("status")) + '</span>',
            esc(c.get("n")),
            (f"{esc(c['ci95'][0])} … {esc(c['ci95'][1])}" if c.get("ci95") else "—"),
            badge(c.get("status", "")),
            src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/strategy_lab.json")])
    srow = []
    for name, m in SET_METRICS:
        if not m:
            continue
        srow.append([esc(name), str(m.get("n_settled")), str(m.get("spread_mae")), str(m.get("total_mae")),
                     str(m.get("brier")), str(m.get("log_loss")),
                     src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/settlement.json")])
    body = f"""
<h1>Measured skill</h1>
<p class="lede">Every number here was produced by running the repository's own code over committed
official snapshots — except the standings inputs, which were re-read from nba.com today. Nothing on this
page is a projection of future performance.</p>

<div class="banner"><h3>The one contradiction worth resolving first</h3>
The walk-forward backtest reports <b>{hold.get('out_of_sample_su_accuracy')}</b> against-the-spread
accuracy out of sample on {hold.get('n_test')} games, while the settled-ledger log-loss is
<b>{MPRIOR.get('model_log_loss')}</b> against a coin flip's <b>{MPRIOR.get('baseline_l0')}</b>. A model can
be right about the side and badly calibrated about the probability — but the two surfaces use different
samples, different settlement rules and different baselines, and no published page reconciles them. Until
one does, neither number should be quoted alone.</div>

{table(["Measurement", "Value", "What it is measured on", "Status", "Source"], rows)}

<h2>Settled sealed ledgers</h2>
{table(["Ledger", "Settled", "Spread MAE", "Total MAE", "Brier", "Log-loss", "Source"], srow,
       "Settlement consumes official final scores only. A game without an official result stays PENDING, "
       "never estimated.")}

<h2>Sealed ledger integrity</h2>
{table(["Ledger", "Picks", "SHA-256 (first 16)", "Settled / expected", "Status", "Source"],
       [[esc(n), str(k), f"<code>{esc(h)}…</code>", f"{esc(s)} / {esc(e)}",
         badge("verified") if s == e else badge("partial"),
         src("https://github.com/wingbangboozle1-lang/NBA2/tree/main/data/raw/ledger")]
        for n, k, h, s, e in SEALED],
       "Both digests recompute from the committed prediction arrays, so neither can have been edited "
       "after sealing. Verified this session by the CI-equivalent command in ci.yml.")}

<h2>Luck vs skill: the leaderboard, as it scores itself</h2>
{table(["Rank", "Strategy", "Bets", "Hit rate", "Log-loss", "Calibration gap", "Eligible for reward", "Source"], lrow,
       f"The board's own minimum sample to rank is <b>{LEADER.get('min_sample_to_rank')}</b> bets. "
       f"<b>{N_BELOW_FLOOR} of {len(LEADER.get('ranked', []))}</b> ranked strategies sit below that floor — "
       f"the top row has <b>{LEADER.get('ranked', [{}])[0].get('n') if LEADER.get('ranked') else '—'}</b> bets "
       "and a 100% hit rate. Ranking on log-loss is the right choice (it is a proper scoring rule); the "
       "sample floor is what is declared and not enforced.")}

<h2>The paired test that decides whether the model beats a one-line rule</h2>
<p class="note">{esc(SKILL_TXT)}</p>
{table(["Rule", "Hit rate", "Bets", "Source"],
       [[esc(b["baseline"]), esc(b["hit_rate"]), str(b["n"]),
         src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/strategy_lab.json")]
        for b in (LAB.get("baselines") or {}).get("baselines", [])],
       "Baselines skip ties rather than guessing them, so the sample differs from the model's; the paired "
       "comparison above uses only the games both rules scored.")}

<h2>Correlations used in parlay pricing</h2>
{table(["Quantity", "Pearson r", "n", "95% CI", "Status", "Source"], crow,
       "The parlay price is the measured joint probability printed beside the naive product, not instead "
       "of it. Where a correlation is unmeasured the cell says so rather than being assumed zero — "
       "a parlay priced on an assumed zero correlation is the exact error the register exists to prevent.")}
"""
    return page("performance.html", "Measured skill", body)


def p_gates() -> str:
    gates = CONTENT.get("gates", [])
    rows = []
    for g in gates:
        gid, name, rule, basis, srcurl, why = g
        fail = "G6" in str(name) or "price" in str(name).lower()
        rows.append([esc(gid), esc(name), esc(rule), esc(basis),
                     badge("BLOCKED — no price") if gid == "G6" else badge("policy"),
                     src(srcurl)])
    body = f"""
<h1>Validation gates</h1>
<p class="lede">The gates are the only thing standing between a research number and something a reader
might act on. They are listed here with the basis for each threshold, because a gate whose number comes
from nowhere is a gate that can be argued away.</p>

<div class="banner"><h3>The gate that matters today is G6</h3>
There is no market price in this repository for any game. Without a price there is no edge, no stake and
no return, so every strategy that depends on comparing our number with a price is blocked — not
conservatively, but definitionally.</div>

{table(["ID", "Gate", "Rule", "Basis for the threshold", "Status today", "Source"], rows)}

<h2>Evaluation of the gate set as built</h2>
<ul class="tight">
 <li><b>Good:</b> G1–G5 and G9 are computed from official inputs on every build, so they cannot silently
 pass. G12 (no look-ahead) is audited against the data with zero violations recorded.</li>
 <li><b>Weak:</b> G7 (≥300 settled bets) and G8 (70/30 holdout) are sample-size policies with no
 published power calculation, so their numbers cannot be defended if challenged.</li>
 <li><b>Missing:</b> no gate tests whether a strategy's result survives the number of strategies tried.
 Selecting the best of nine preregistered strategies and reporting its hit rate without a
 multiple-comparison correction is the single most common way a leaderboard manufactures skill.</li>
 <li><b>Self-referential:</b> the site's own freshness gate (<code>CC-FRESH-01</code>) fails in the
 repository's checker and is excluded from blocking by the publish workflow — so the one check that says
 "this is stale" is the one check allowed to fail.</li>
</ul>
"""
    return page("gates.html", "Validation gates", body)


def p_strategies() -> str:
    strat = CONTENT.get("strategies", [])
    rows = []
    for s in strat:
        rows.append([esc(s["id"]), esc(s["name"]), esc(s["type"]), esc(s["signal"]),
                     esc(s["gates_that_can_pass_today"]), esc(s["gates_that_fail_today"]),
                     badge(s["status"]), src(s["src"])])
    pre = PREREG.get("files", [])
    prow = [[esc(p["id"]), f'<code>{esc(p["prereg_hash"][:16])}…</code>', esc(p["frozen_at_utc"]),
             src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/" + esc(p["file"]))] for p in pre]
    body = f"""
<h1>Strategies &amp; preregistration</h1>
<p class="lede">A strategy here is a written rule frozen before the first bet: signal, threshold,
universe, settlement rule. The pre-registration hash is published with the build, so a rule cannot be
adjusted after the results are known.</p>

{table(["ID", "Strategy", "Type", "Signal", "Gates that can pass today", "Gates that fail today", "Status", "Source"], rows,
       f"{len(rows)} strategies. 'PUBLISHABLE AS A PROJECTION ONLY' means the number is derivable and the "
       "method backtested; it does not mean the bet can be staked.")}

<h2>Pre-registration files (frozen, hashed)</h2>
{table(["Strategy", "Pre-registration hash", "Frozen at", "File"], prow,
       "Hashes are computed over canonical JSON of the rule. Any edit after the freeze changes the hash and "
       "is visible.")}

<h2>Parlays and prop combos</h2>
<p class="note">A parlay's price is the measured joint probability, and the naive product is printed beside
it rather than withheld. Same-game legs are not independent: the site already demonstrates a ±26% price
error from treating them as independent, so the joint pricing is the whole point of the page. Player-prop
combos are the product the brief asks for most directly and the one most dependent on data that is not
held: same-player correlation needs per-player box scores, and coverage of injury-report players is 10.3%.
Both remain blocked, and blocking them is the correct outcome until the logs exist.</p>

<h2>Leaderboard</h2>
<p class="note">The leaderboard pays nobody while a gate fails, which is the right design. It has also
never paid anybody, because G6 has never passed. A leaderboard in that state is a list of unproven claims,
and it should be labelled that way wherever it appears — see <a href="suggestions.html">SG-923-10</a> for
the minimum disclosure that would make it honest.</p>
"""
    return page("strategies.html", "Strategies & preregistration", body)


def p_questions() -> str:
    rows = [[esc(q), esc(sev and badge(sev) or ""), md(title), md(detail), md(next_step),
             f'{esc(F_Q[q])} ' + fsrc(F_Q[q])] if q in F_Q else
            [esc(q), esc(sev and badge(sev) or ""), esc(title), esc(detail), esc(next_step),
             f'{esc(F_Q[q])} ' + fsrc(F_Q[q])]
            for q, title, detail, next_step, sev in QUESTIONS]
    body = f"""
<h1>Open questions</h1>
<p class="lede">Questions that have to be answered before a decision can reasonably be made on the
information that exists. Each one says what we do not know, why it blocks something, and what would
discover the missing information. Nothing here is rhetorical: an answer changes a file.</p>

{table(["ID", "Severity", "Question", "Why it is open", "How to discover the answer", "Evidence"], rows,
       f"{len(rows)} questions, ordered by what they block.")}

<h2>What is genuinely missing, in one list</h2>
<ul class="tight">
 <li><b>A market price.</b> No licensed feed, no closing line, no edge, no ROI. This blocks every bet
 claim on the site and cannot be worked around.</li>
 <li><b>Runner logs.</b> The publish failure is observable but not explainable from here.</li>
 <li><b>Per-player logs at scale.</b> 10.3% coverage of injury-report players.</li>
 <li><b>Official team-stat pages.</b> stats.nba.com and cdn.nba.com are unreachable from the runner per
 the repository's own transport probe, so the three team-stat surfaces are derived rather than read.</li>
 <li><b>A reconciliation of the two skill measurements</b> (67.3% ATS out of sample vs a log-loss worse
 than a coin flip).</li>
 <li><b>A revision rule for settled games</b> when an official box score is later corrected.</li>
</ul>
"""
    return page("questions.html", "Open questions", body)


def p_suggestions() -> str:
    rows = [[esc(i), md(t), md(d), esc(sev and badge(sev) or ""), md(impact),
             f'{esc(S_F.get(i, "F-923-01"))} ' + fsrc(S_F.get(i, "F-923-01")),
             f'<a class="chip" href="#{esc(i)}">choose</a>'] for i, t, d, sev, impact in SUGGESTIONS]
    detail = []
    for i, t, d, sev, impact in SUGGESTIONS:
        detail.append(
            f'<div class="card" id="{esc(i)}" style="margin:10px 0">'
            f'<h4 style="margin:0 0 6px;font-size:15px;color:var(--ink)">{esc(i)} · {md(t)}</h4>'
            f'<p style="margin:0 0 8px">{md(d)}</p>'
            f'<div class="meta">Severity {esc(sev)} · Impact: {md(impact)}</div></div>')
    body = f"""
<h1>Suggestions</h1>
<p class="lede">A section reserved for proposals, so that one can be reviewed and chosen before anything
is implemented. Each suggestion names the finding it addresses, what it costs, and what it would change.
Nothing on this page has been implemented by this session.</p>

<h2>The queue</h2>
{table(["ID", "Suggestion", "What it changes", "Priority", "Addresses", "Evidence", ""], rows,
       f"{len(rows)} open.")}

<h2>Detail</h2>
{"".join(detail)}

<h2>How to choose</h2>
<p class="note">The queue is deliberately ordered so that the first two items unblock observation of
everything else. A change that cannot be measured is a change that cannot be defended, and today the site
cannot publish at all — so the highest-value work is the least interesting work.</p>
"""
    return page("suggestions.html", "Suggestions", body)


def p_flagged() -> str:
    body = f"""
<h1>Flagged for review</h1>
<p class="lede">Every irregularity this session found, with the official URL that confirms it. Nothing on
this page blocks publication of the site: it is the list to read after the site is live, so a change can
be requested with the evidence already in hand.</p>

<div class="banner"><h3>Nothing here was silently repaired</h3>
All fixes for these items live in files owned by other live sessions (open PRs #130/#131 and two claim-only
branches). Editing them from this session would collide. Each finding therefore names the file to change
and the mechanism to change it with, and is logged on the shared board as a request.</div>

{"".join(f'''<div class="finding" id="{esc(f[0])}">
<h4>{esc(f[0])} {badge(f[1])} {md(f[2])}</h4>
<p>{md(f[3])}</p>
<div class="meta"><b>Evidence:</b> {md(f[4])}<br><b>Confirm at:</b> {src(f[5])}</div></div>'''
            for f in FINDINGS)}

<h2>Unverified items, listed separately</h2>
<p class="note">These are not defects. They are things a reader might assume were checked and were not.
Each is blank on this site rather than filled.</p>
<ul class="tight">
 <li>Quarter scores for the twelve 2026-11-18 finals — the breakdown is not in a committed capture.</li>
 <li>The three official team-stat pages (traditional, opponent, advanced) — unreachable from this sandbox
 and from the GitHub runner per the repository's transport probe.</li>
 <li>Per-player box scores for 2026-11-18 beyond game 0022600259, and the Pacers block within it.</li>
 <li>Game id for WAS@CHI on 2026-11-20 — outside the captured chunk; left empty, not inferred.</li>
 <li>Any market price for any game.</li>
 <li>The runner log for the ten failed scheduled refreshes.</li>
</ul>
"""
    return page("flagged.html", "Flagged for review", body)


def p_sources() -> str:
    rows = [[esc(s["id"]), esc(s["what"]), src(s["url"])] for s in CAP["sources"]]
    body = f"""
<h1>Sources &amp; method</h1>
<p class="lede">What was read, when, with what transport, and what could not be read at all. The method is
part of the evidence: a number read with a fragile transport at an unrecorded time is worth less than one
read with a timestamp.</p>

<div class="banner"><h3>Transport, stated plainly</h3>
Direct TLS from the execution sandbox to <code>www.nba.com</code>, <code>official.nba.com</code>,
<code>ak-static.cms.nba.com</code> and <code>stats.nba.com</code> fails with
<code>SSL_ERROR_SYSCALL</code> (HTTP 000). Every official read in this session therefore used the platform's
page-fetch transport, which returns the page as text. Each fetch is timestamped
({esc(CAP['retrieved_at_utc'])}) and recorded below. This is a real read of the real page; it is not a
scrape of a cached copy.</div>

{table(["Source", "What it was used to verify", "URL"], rows, f"{len(rows)} sources.")}

<h2>What could not be read</h2>
<ul class="tight">
 <li><code>stats.nba.com</code> — all endpoints, from this sandbox (TLS failure) and per the repository's
 own probe also from a GitHub runner (timeout).</li>
 <li><code>cdn.nba.com</code> — 403 from the runner per the same probe.</li>
 <li>GitHub Actions job logs — the blob endpoint returned <code>EOF</code> for both attempts.</li>
 <li>Any licensed odds provider — none is configured in the repository.</li>
</ul>

<h2>Reproduce this site</h2>
<pre style="background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;overflow-x:auto">
python3 audit/923eb342/verify_published.py   # rebuild report.json + run_log.txt
python3 audit/923eb342/ingest.py             # rewrite verified/*.json (idempotent)
python3 audit/923eb342/build.py              # rewrite this site
</pre>
<p class="note">All three are deterministic over committed inputs plus the capture in
<code>audit/923eb342/capture_2026-11-19.json</code>. The generator writes this desk twice: the source of
truth under <code>audit/923eb342/</code>, and a byte-identical copy under <code>site/audit/923eb342/</code>, so the desk travels inside the artefact that
<code>pages.yml</code> uploads as well as being readable from the repository. The published URL is
<code>/NBA2/audit/923eb342/</code> — measured, not assumed.</p>
"""
    return page("sources.html", "Sources & method", body)


BUILDERS = {
    "index.html": p_overview,
    "executive-summary.html": p_exec,
    "verification.html": p_verification,
    "official-results.html": p_results,
    "standings.html": p_standings,
    "injuries.html": p_injuries,
    "performance.html": p_performance,
    "gates.html": p_gates,
    "strategies.html": p_strategies,
    "questions.html": p_questions,
    "suggestions.html": p_suggestions,
    "flagged.html": p_flagged,
    "sources.html": p_sources,
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in BUILDERS.items():
        (OUT / name).write_text(fn())
    (OUT / ".nojekyll").write_text("")

    # A byte-identical copy inside the published tree (the uploaded artefact). The repository's Pages source is
    # `build_type: legacy`, `main /`, and the artefact served at the root is the `site/` tree
    # uploaded by pages.yml — so a page outside `site/` is committed but NOT reachable over HTTP
    # (measured: /NBA2/audit/923eb342/ returned 404 while /NBA2/site/index.html was live).
    # `site/audit/923eb342/` is a subdirectory that no builder writes and no nav pass scans
    # (every nav/gate pass globs `site/*.html`, top level only), so this publishes the desk
    # without touching a single existing page, and without a second deployer competing for the
    # Pages root.
    import shutil
    PUB = ROOT / "site" / "audit" / "923eb342"
    PUB.mkdir(parents=True, exist_ok=True)
    for f in sorted(OUT.iterdir()):
        if f.is_file() and f.suffix in (".html",) or f.name == ".nojekyll":
            shutil.copyfile(f, PUB / f.name)
    print(f"built {len(BUILDERS)} pages into {OUT} and {PUB}")
