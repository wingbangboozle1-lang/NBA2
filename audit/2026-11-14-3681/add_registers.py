"""Append session arena/3681def8-nba2's questions and suggestions to the shared registers.

Both files feed data/site.json and the generated Questions / Suggestions pages, so the new
rows appear on the site with the same columns, the same review-before-implement rule and the
same "nothing here is implemented" status as every row already there.

Read-modify-write with an explicit duplicate guard on the id, so re-running is a no-op.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

NEW_QUESTIONS = [
    {
        "id": "Q-30",
        "question": "Is the model any good? We now have nine games graded against official "
                    "results — is that an answer?",
        "have": "A graded card for 2026-11-13 (data/graded_2026-11-13.json): margin MAE 12.97 "
                "vs 13.33 for a no-information baseline, total MAE 12.90 vs 16.20, winner calls "
                "5/9, AUROC 0.93. The inputs are strictly point-in-time, proven by the identity "
                "(committed ratings W-L) + (the nine results) = official NBA.com standings, 30/30.",
        "missing": "Statistical significance. Permutation p = 0.95 (margin) and p = 0.40 (total); "
                   "the Wilson 95% CI on the hit rate is 26.7%-81.1%. About 1,565 graded games are "
                   "needed to detect a 55% hit rate at 5% significance with 80% power.",
        "how": "Keep grading every completed slate with the same script and re-test when the sample "
               "supports it. Do not promote a strategy or pay a reward before then — gate G-01 "
               "requires 300 settled bets and nothing changes that.",
        "impact": "Decides whether the originated lines are worth the effort at all. The honest "
                  "answer today is: unproven, directionally mildly positive on totals, untested on margins.",
        "severity": "BLOCKING",
    },
    {
        "id": "Q-31",
        "question": "Should every slate be sealed before its first tip, automatically, from now on?",
        "have": "Two ledgers (22 and 27 predictions) covering 2026-11-14..11-17, both verified. "
                "A nightly refresh workflow (refresh.yml) already exists but does not seal.",
        "missing": "Any sealed ledger for 2026-11-13. That slate was already live when the project "
                   "started, so its nine games — the only ones with official results — can only ever "
                   "be graded as a backtest, never as a forward test. That gap is permanent for 11/13.",
        "how": "Add a seal step to the nightly workflow so each day's card is committed before the "
               "first tip, and assert the seal date strictly precedes the earliest tip in the set.",
        "impact": "High. Without pre-registration every future result is a backtest, and a backtest "
                  "can be tuned after the fact. This is the difference between evidence and a story.",
        "severity": "BLOCKING",
    },
    {
        "id": "Q-32",
        "question": "The 2026-11-17 slate repeats two matchups from the two days before "
                    "(NYK@TOR also on 11/15, POR@MIN also on 11/16). Is that real, and what does "
                    "it do to the model?",
        "have": "Confirmed real: the official game page for 0022600253 reads 'Tuesday, November 17th, "
                "2026 7:30 PM ET' for NYK@TOR. Both pairs appear in the official schedule with "
                "distinct game IDs.",
        "missing": "Whether the model should treat the second meeting differently (rest, preparation, "
                   "confidence) — we have no evidence either way and no settled games to test it on.",
        "how": "Leave the games priced normally and flag them (FLAG-ANOM-01 already does); revisit "
               "when there is a sample of repeat-matchup results.",
        "impact": "Two of the five 11/17 games are affected. If repeat matchups behave differently, "
                  "our lines for them are wrong in a systematic, correctable way.",
        "severity": "MEDIUM",
    },
    {
        "id": "Q-33",
        "question": "Do we trust the totals more than the margins? The graded card says the totals "
                    "improvement is nine times larger.",
        "have": "On nine games: totals beat the league-mean baseline by 3.30 pts/game, margins beat "
                "a zero baseline by 0.36 pts/game. Two >20-point margin misses (GSW@SAS predicted "
                "SAS +3.2, actual +38; MEM@NOP predicted MEM by 8.3, actual by 31) drive most of "
                "the margin error.",
        "missing": "Any statistical support (p = 0.40 and p = 0.95), and any idea whether the early-"
                   "season shrinkage is over-compressing large true team gaps.",
        "how": "Grade more slates; separately, test the shrinkage weight by re-running the card with "
               "lambda swept and see whether the two big misses shrink.",
        "impact": "If the totals edge is real it is the single most valuable thing found so far, "
                  "because a total is a market we can price without a win-probability model.",
        "severity": "MEDIUM",
    },
    {
        "id": "Q-34",
        "question": "Which site tree is the product? Six are published from one origin and the "
                    "Pages setting picks one.",
        "have": "GitHub Pages is set to build_type 'legacy' from main /, so visitors get the root "
                "v1 tree (index.html + pages/). The v2 tree (site/), docs/, dashboard/, "
                "originated/, backtest/ and verified/ are all served from the same origin as "
                "secondary trees with overlapping content.",
        "missing": "An owner decision on which is canonical. Prior sessions logged this rather than "
                   "deciding it, because switching changes every page a reader sees.",
        "how": "One setting: flip Pages to 'GitHub Actions' to publish the v2 artifact, or keep "
               "legacy and retire the others into an archive folder with an index.",
        "impact": "Until it is decided, a reviewer cannot tell which numbers are current. The root "
                  "tree now carries every table added this session.",
        "severity": "BLOCKING",
    },
    {
        "id": "Q-35",
        "question": "Official NBA.com standings are now reachable through the page fetcher. Should "
                    "the third-party ratings source be retired?",
        "have": "All 30 clubs' W-L read live from nba.com/standings on 2026-11-14, matching the "
                "committed snapshot exactly once the 11/13 results are applied. Snapshot: "
                "data/raw/standings_2026-11-14_official.json.",
        "missing": "Official per-game point rates (PS/G, PA/G). nba.com/standings renders the "
                   "'Margins & Stats' section, but stats.nba.com endpoints remain unreachable, so "
                   "the SRS column still comes from basketball-reference and stays flagged "
                   "FLAG-RAT-01.",
        "how": "Point the ratings loader at the official standings for W-L (done) and keep the "
               "third-party column only for point rates, labelled.",
        "impact": "Removes the last unverified W-L in the model input. Does not remove FLAG-RAT-01, "
                  "which is about point rates, not records.",
        "severity": "MEDIUM",
    },
]

NEW_SUGGESTIONS = [
    {
        "id": "S-29",
        "title": "Put the graded-results card on the landing page, above the category grid",
        "problem": "The landing page opened with model parameters (sigma, HCA) and tier counts, "
                   "which are the least decision-relevant numbers on the site. The one measurement "
                   "against real outcomes was buried.",
        "proposal": "Render a 'Graded against official results' block at the top of the dashboard "
                    "with the four numbers that matter (margin MAE, total MAE, winner calls, games "
                    "needed for power) and a link to the full card.",
        "benefit": "A reader learns in five seconds what the model has been proven to do, and what "
                   "the sample can support, before meeting any parameter.",
        "effort": "S — one build-time section",
        "risk": "None; the block is generated from the same graded JSON.",
        "recommendation": "Accept — implemented this session (session arena/3681def8-nba2).",
        "status": "implemented 2026-11-14 by arena/3681def8-nba2",
    },
    {
        "id": "S-30",
        "title": "Render every URL-valued table cell as a clickable link",
        "problem": "The slate table's official-game-page column and the graded card's source column "
                   "printed verified URLs as plain text, so a reviewer had to copy-paste them. "
                   "Raised earlier as FLAG-AUD-01 and left open.",
        "proposal": "In the table renderer, detect a cell whose entire value is an http(s) URL and "
                    "emit an anchor. The value, the provenance badge and the row's own source column "
                    "are unchanged.",
        "benefit": "Manual verification becomes one click. 89 cells across the slate and graded "
                   "tables become clickable without touching a single value.",
        "effort": "S — one helper in build_site.py",
        "risk": "None to data; external links already open with rel=noopener.",
        "recommendation": "Accept — implemented this session; FLAG-AUD-01 can now be closed.",
        "status": "implemented 2026-11-14 by arena/3681def8-nba2",
    },
    {
        "id": "S-31",
        "title": "Seal every slate before its first tip, in the nightly job",
        "problem": "Nothing was sealed for 2026-11-13, the only slate with official results, so the "
                   "first graded card is a backtest and can never become a forward test "
                   "(FLAG-GRADE-01, Q-31).",
        "proposal": "Add a seal step to .github/workflows/refresh.yml that commits a ledger for the "
                    "next slate, and make seal_predictions assert that the seal timestamp strictly "
                    "precedes the earliest tip in the set.",
        "benefit": "Every future result becomes pre-registered evidence instead of a story that can "
                   "be revised after the fact. This is the cheapest real improvement available.",
        "effort": "M — workflow step + assertion",
        "risk": "Low; fails closed (no seal, no published picks) which is the correct behaviour.",
        "recommendation": "Accept first among the open items — it is the only one that makes future "
                          "evidence trustworthy.",
        "status": "awaiting owner decision",
    },
    {
        "id": "S-32",
        "title": "Decide on one canonical site tree and archive the other five",
        "problem": "Six trees (root/pages, site/, docs/, dashboard/, originated/, backtest/) publish "
                   "from one origin with overlapping and sometimes conflicting numbers. A reviewer "
                   "cannot tell which is current (Q-34).",
        "proposal": "Keep the root v1 tree, move the others under a single /archive/ path with an "
                    "index that states each tree's as-of date and why it was kept, and link them "
                    "from one place on the dashboard.",
        "benefit": "One current answer per question, with the history one click away instead of "
                   "mixed into the navigation.",
        "effort": "M — moves plus an index page",
        "risk": "Breaks inbound links to the moved trees; needs redirects or a clear index.",
        "recommendation": "Accept, but as an owner decision — it changes what every visitor sees.",
        "status": "awaiting owner decision",
    },
    {
        "id": "S-33",
        "title": "Investigate rating shrinkage after two >20-point margin misses",
        "problem": "GSW@SAS (predicted SAS +3.2, actual +38) and MEM@NOP (predicted MEM by 8.3, "
                   "actual by 31) contributed 57 of the 117 total margin error on nine games.",
        "proposal": "Re-run the 2026-11-13 card with the shrinkage weight swept across a grid and "
                    "publish the resulting MAE curve, so the choice is measured rather than assumed.",
        "benefit": "Either confirms the current weight or finds a cheap accuracy gain; either way it "
                   "retires one of the unratified parameters.",
        "effort": "S — the grading script already exists; add a sweep",
        "risk": "Fitting shrinkage on the same nine games would be overfitting; report the curve, "
                "do not pick the minimum from it.",
        "recommendation": "Accept, with the explicit rule that no parameter is chosen from these "
                          "nine games.",
        "status": "awaiting owner decision",
    },
    {
        "id": "S-34",
        "title": "Make the nightly refresh ingest official standings and final scores",
        "problem": "The refresh workflow fetches the slate and injury report but not the official "
                   "standings or completed-game scores, so ratings and settlement stay manual.",
        "proposal": "Add two steps: nba.com/standings -> data/raw/standings_<date>_official.json, "
                    "and nba.com/schedule finals -> data/raw/finals_<date>.json, then run settle.",
        "benefit": "Closes the loop unattended: official records in, graded cards out, every morning.",
        "effort": "M — two ingest functions plus the settle step",
        "risk": "The page fetcher is the only working retrieval path in this environment; the "
                "workflow runner may reach the same hosts directly, which should be probed first.",
        "recommendation": "Accept after the reachability probe in CC-FRESH-03 confirms the runner "
                          "can reach nba.com.",
        "status": "awaiting owner decision",
    },
    {
        "id": "S-35",
        "title": "Group the navigation by the decision each page supports",
        "problem": "Twenty flat sidebar links in file order gave no signal about what to read first.",
        "proposal": "Group into Decide / Measure / Inputs / Governance / Project, with a one-line "
                    "description per category, and mirror the grouping on the dashboard.",
        "benefit": "The site reads as a dashboard with an order of operations rather than a listing.",
        "effort": "S — data structure in the builder plus CSS",
        "risk": "None; every existing page keeps its URL.",
        "recommendation": "Accept — implemented this session.",
        "status": "implemented 2026-11-14 by arena/3681def8-nba2",
    },
]


def merge(path: Path, key: str, new: list[dict]) -> int:
    doc = json.loads(path.read_text())
    existing = {q["id"] for q in doc[key]}
    added = [q for q in new if q["id"] not in existing]
    doc[key].extend(added)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return len(added)


def main() -> None:
    nq = merge(ROOT / "requirements" / "QUESTIONS.json", "questions", NEW_QUESTIONS)
    ns = merge(ROOT / "suggestions" / "SUGGESTIONS.json", "suggestions", NEW_SUGGESTIONS)
    print(f"questions: +{nq} (now {len(json.loads((ROOT / 'requirements/QUESTIONS.json').read_text())['questions'])})")
    print(f"suggestions: +{ns} (now {len(json.loads((ROOT / 'suggestions/SUGGESTIONS.json').read_text())['suggestions'])})")


if __name__ == "__main__":
    main()
