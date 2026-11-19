# Session `arena/585453f5-nba2` — repo review, official re-verification, and final integration

Written 2026-11-19 (UTC). Every claim below is tied to a command that was run in this tree or
to an official URL that was read in this session. Where something could not be confirmed it
says so and is flagged; nothing is filled in.

---

## 1. What the repository already was (measured, not assumed)

`origin/main` at the claim commit `41cfd812` was already a nine-layer build chain
(v1 → backtest → v2 → settlement → v3 → v4 → v5 → v6) with a Pages deploy that last succeeded
on 2026-11-19T07:05Z (run [44476981781](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44476981781),
`build` and `deploy` both `success`).

Reproduced here before changing anything:

| Check | Command | Result |
|---|---|---|
| root pipeline tests | `python3 -m unittest discover -s nba2/tests -t .` | **92 OK** |
| v2 / v3 / v4 / v5 / v6 suites | `-s nba2/vN -p 'test_*.py'` | **167 / 67 / 61 / 26 / 52 OK** |
| provenance lint | `python3 -m nba2.pipeline.lint` | `1436 rows across 50 tables`, every row sourced |
| v2 / v3 / v4 / v5 structural checks | `python3 -m nba2.vN.check` | 0 structural, 0 semantic; 8/8 gates (v3), 8/8 (v4), 8/8 (v5) |
| sealed ledgers | `nba2.models.ledger.verify` | `cf7dedc6…` 22 picks **VERIFIED**; `c841e8f3…` 27 picks **VERIFIED** |
| full ordered rebuild | the 9 modules in pipeline order | **0 files drifted** — the tree is a fixed point of its own builders |

So the starting point was sound. Nothing in this session "fixed" a broken main; it integrated
work that was finished on a branch but never landed, and repaired the two defects that
integration exposed.

## 2. The two open pull requests (both were stale branches, measured)

`git merge-base` after `git fetch --unshallow`:

| PR | Branch | Merge base | Verdict |
|---|---|---|---|
| #131 | `arena/8c7c8828-nba2` | `7b16b6d` (PR #129) — **before** #132/#133 | superseded, and a **regression** (below) |
| #130 | `arena/6023d517-nba2` | `1a9c2f2` (PR #128) — **before** #129/#132/#133 | superseded, but its v7 layer was **not** on main |

**PR #131 is a measured regression, not a stale duplicate.** Its own diff against its merge
base (`git diff 7b16b6d origin/arena/8c7c8828-nba2 -- nba2/pipeline/settle.py`) **deletes**:

* the `capture_*/gamebooks_*.json` source glob — the comment removed with it names games
  `0022600231–240` as having no quarter row anywhere else;
* the `{quarters: {away, home}}` fallback, so the quarter-sum rejection rule is silently
  skipped for gamebook rows;
* the multi-key `_records_of` reader (`records`/`rows`/`games`/`results`), reverting to
  one-key-if-present, which is the exact shape that lost teams and quarters before;
* `nba2/tests/test_finals_pages.py` and `nba2/tests/test_refresh_workflow.py` — 105 lines of
  regression tests.

Main's `nba2/pipeline/settle.py` carries all of those (added by PR #132 /
`arena/af5df7a7-nba2`), so merging #131 would have re-broken the settlement union and deleted
the tests that guard it. It was **not** merged. Its green CI ran on a tree that predates the
code it would have replaced.

**PR #130 carries one thing main does not have:** the v7 layer. Its own diff
(`git diff 1a9c2f2 origin/arena/6023d517-nba2`) is 105 files, and **39 of them are new**
(`nba2/v7/**`, `data/v7/**`, `tools/v7_fetch.py`) inside a namespace nothing else touches.
Those 39 files were carried over; everything else in that branch was already on main in a
newer form (`nba2/v6/results_coverage.py` on main is strictly newer — it reads nested
`capture_*`/`refresh_*` finals and rejects unknown IDs, with a test file the branch lacks).

## 3. What the integration changed

1. **Carried the v7 layer** (`nba2/v7/`, `data/v7/`, `tools/v7_fetch.py`, its four analysis
   write-ups) onto the current tree. No file outside the v7 namespace was taken from the
   branch.
2. **Wired v7 into all three build chains.** This was a real gap: the branch's v7 pages were
   not part of `pages.yml`, `publish-parity.yml` or `refresh.yml`, so the next rebuild would
   have reported five v7 pages plus every nav edit as drift, and the deploy would have
   failed. v7 now runs last in all three (it inserts links into the sidebar v6 grouped and
   re-appends its section to `flagged.html`, which v2 regenerates). Verified by running the
   whole chain and getting **0 files of drift**.
3. **Registered the five v7 pages in v6's category map.** v6's own test
   (`test_every_published_page_is_in_some_category`) failed on the new pages — the gate was
   working. The five pages were added to the groups they belong to (the slate and the skill
   page to *Projection*, the strategy lab to *Bet surface — gated*, the verification and
   methodology pages to *Verification*), keeping the projection/bet wall intact.
4. **Added independent re-verification rows** V-11…V-13 to `nba2/v7/verification.py`.
5. **Published a measured freshness finding**, flag F-V7-FRESH (see §4).
6. **Named the v7 slate from the v1 root builder.** GitHub Pages is `build_type: legacy`,
   source `main /`, so `/NBA2/` is served from the repo root and a link to
   `site/v7-slate.html` would otherwise 404 while the reader is on the front door. The link
   is emitted by `nba2/pipeline/build_site.py::_root_pointer`, not hand-edited into
   `index.html`, because the v1 builder regenerates that file (measured: a hand edit was
   reverted by the next `python -m nba2.pipeline.build_site`).

## 4. Official sources read in this session, and what matched

Read through the platform page-fetch transport on 2026-11-19 (the sandbox has no TLS egress to
nba.com; this is the same transport constraint recorded in `data/raw/egress_probe.json`).

| Official page | Compared | Result |
|---|---|---|
| [standings](https://www.nba.com/standings) | W-L for 26 clubs, both conferences | **26/26 match** the v7 transcription |
| [teams/advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) | GP, W, L, OffRtg, DefRtg, NetRtg, PACE for 27 clubs | **27/27 match** to the printed decimal |
| [teams/traditional](https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season) | PTS per game / +- for the clubs reached | match; the page paginates into 5 chunks and not every row was reached |
| [teams/opponent](https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season) | Opp PTS per game | match on every row that was reached |
| [games?date=2026-11-19](https://www.nba.com/games?date=2026-11-19) | 4 games: ids, clubs, tip times | **4/4 match** (`0022600270`–`0022600273`, all 8:00 PM ET) |
| [games?date=2026-11-20](https://www.nba.com/games?date=2026-11-20) | 9 games: ids, clubs, tips, Cup groups | **9/9 match** (`0022600043`–`0022600048` + the three on 11/19 page) |

Three clubs (MIN, SAC and the 30th advanced row) were **not** re-compared because they did not
fall inside the fetched page chunks. They are not counted as matches.

### The freshness finding (flag F-V7-FRESH)

The v7 snapshot is stamped `2026-11-19T06:05Z`. The same pages, read again in this session,
print a later cut for two clubs:

| Club | v7 snapshot | 2026-11-19 re-read |
|---|---|---|
| LAL | GP 15, 13-2 | **GP 16, 13-3** |
| NOP | GP 15, 5-11 | **16 GP** (standings: 5-11, i.e. a loss) |

Two clubs, one game each. The inputs were **not** silently re-cut. The slate, ratings and every
derived number stay pinned to the stamped snapshot; the later reading is published in the flag
ledger, and a re-cut is a new snapshot with a new retrieval stamp. This is the brief's
freshness rule applied to the one surface that is a hand transcription.

## 5. Repo review — irregularities found, by severity

| ID | Severity | What | Evidence | Disposition |
|---|---|---|---|---|
| F-5854-01 | **high** | PR #131 would have re-broken the settlement union and deleted 105 lines of regression tests | `git diff 7b16b6d origin/arena/8c7c8828-nba2 -- nba2/pipeline/settle.py nba2/tests/` | not merged; this record is the reason |
| F-5854-02 | medium | v7 was not in any build chain, so it could never have deployed and would have failed the next parity run | `grep -n 'nba2.v7' .github/workflows/*.yml` returned nothing on main | fixed: added to pages / parity / refresh |
| F-5854-03 | medium | v7's docstrings cite `data/raw/v7_fetch/` as the captured page bytes; **that directory is not committed**, so `nba2/v7/capture.py` cannot parse them | `git ls-tree -r HEAD -- data/raw \| grep v7` → nothing | published as flag; the numbers are held by the three identities instead, and re-verified externally this session (V-11…V-13) |
| F-5854-04 | medium | Every one of the 10 strategies is BLOCKED (G-V7-4 sample size, G-V7-6 no market price, G-V7-8 no injury report read, G-V7-9), so no stake is actionable — the dashboard must not read as if it were | `data/v7/strategies.json` | published as-is with every gate printed; see §6 |
| F-5854-05 | info | Live site could not be fetched from the sandbox: the platform fetch returned GitHub's outage page and `curl` has no egress | page-fetch result 2026-11-19 | deploy verified from the Actions API instead (`build`+`deploy` success, head `41cfd81`); re-checked after this merge in COORDINATION.md |
| F-5854-06 | info | **CORRECTED 2026-11-19 after measuring the live URLs — the first version of this row was wrong.** `gh api …/pages` reports `build_type: legacy`, source `main /`, which reads as "the repo root is served". It is not. The `github-pages` artefact uploaded by `pages.yml` is the **`site/` directory**, so the deployed root IS the v2/v7 dashboard. Measured on the live host through the page-fetch transport: `/NBA2/` and `/NBA2/index.html` return the dashboard; `/NBA2/v7-slate.html`, `/NBA2/v7-verify.html`, `/NBA2/flagged.html`, `/NBA2/audit/923eb342/…` all return 200; `/NBA2/site/index.html` returns **404** (that path does not exist inside the artefact). The repo-root `index.html` pointer is therefore never what a reader sees — it matters only when browsing the raw repository on github.com. | live URLs above + `gh api …/pages/builds/latest` → `status: built` | no action; the earlier "front door is the root pointer" claim is withdrawn here rather than left standing |
| F-5854-07 | info | The v7 standalone `data/raw/v7_fetch/` gap also means the branch's claim "cut from the stored bytes" is only true of the session that made it | same as F-5854-03 | recorded in the methodology page's source statement |

## 6. What a reader should understand before acting on any number here

* The **headline is the disagreement** between the two estimators, not the blend. The blend is
  published underneath it.
* Home-court advantage is **pinned** to the measured home-win rate (108/210 = 0.5143 →
  `h = 16.808 × Φ⁻¹(0.5143) = 0.602`), not fitted.
* Luck is a **z-score per club**; no club is outside |z| > 2 in this snapshot
  (`data/v7/model.json:outside_band` is empty), so the luck gate does not currently refuse
  anything — that is a measurement, not a licence.
* The walk-forward skill is **167 decisions, 67.1% accuracy, log-loss 0.6349 against the coin
  flip's 0.6931** and 0.653 for the better-record rule. It beats both. It is a 167-game
  sample, and the strategies remain blocked because a market price does not exist.
* Every parlay is priced **twice**, with the measured ρ = -0.0440 (95% CI -0.178…+0.092) next
  to the naive product, so the reader can see the correlation adjustment is small and
  uncertain.
* Nothing here is a claim of profitability. There is no market price in this repository, so
  there is no edge, and every stake is 0.00.

## 7. Verification run after the integration

```
python3 -m nba2.v7                                   -> rc 0, 7/7 structural checks, 6/10 gates PASS (4 published BLOCKED)
python3 -m unittest discover -s nba2/tests -t .       -> 92 OK
python3 -m unittest discover -s nba2/v2 … v7          -> 167 / 67 / 61 / 26 / 52 / 37 OK  (410)
python3 -m nba2.v2.check / v3 / v4 / v5 / v6          -> 0 structural, 0 semantic; 8/8, 8/8, 8/8
python3 -m nba2.pipeline.lint                          -> 1436 rows / 50 tables, all sourced
python3 tools/check_links_all.py                       -> 148 files, 8024 internal links OK
full ordered rebuild (10 modules)                      -> 0 files of drift (fixed point)
sealed ledgers                                         -> 22 and 27 picks VERIFIED, unmodified
```

## 8. Not verified, and therefore not claimed

* The **2026-11-19 injury report** was not read (the branch did not read it either, and this
  session did not). The availability column is blank with `F-V7-AVAIL` on every row and gate
  G-V7-8 blocks the strategies that need it.
* **No market price** — closing line, opening line, spread or total — exists in this
  repository. The market-anchored prior is written and blocked (G-V7-6), not demonstrated.
* **Player props cannot be priced**: the largest committed per-player log covers 3 games,
  against the ~15 a ±5-point line needs.
* The **live site HTML** could not be fetched (F-5854-05).
* Arena coordinates remain third-party and are flagged from an earlier session
  (FLAG-V2-ARENA-COORDS); v7 does not publish travel distance.

---

## 9. The nightly refresh failure, measured and repaired (follow-up, same session)

After the integration merged (`30d67f8`, PR #139, Pages deploy `44527199288` success) the
brief's core requirement — *refresh the four official surfaces on a rolling slate, then rebuild
only after the freshness and provenance gates pass* — was still not working in production.
`gh run list --workflow=refresh.yml --limit 12` shows **10/10 scheduled runs concluded
`failure`**, the newest at 2026-11-18T19:29Z, and every one of them failed in the same job:

```
capture  success   (all four official surfaces read)
publish  failure   failed step: "Rebuild every tree from the committed capture"
```

The Actions job log is not retrievable from this sandbox
(`results-receiver.actions.githubusercontent.com` is outside the reachable set), so the failure
was **reproduced** instead of guessed. Replaying the publish job's exact module sequence in a
worktree pinned at the capture commit the last run acted on (`a5380e1`,
`ingest(bot): official capture — 2026-11-18T19:30:52Z`) reproduces it:

```
python3 -m nba2.v6   ->  HARD GATE FAILURE — nothing is rendered
    G-V6-8: every game row points at an official nba.com document
        ! 0022600231: no official URL at all          (… through 0022600240)
```

### Root cause (two defects, both in the reader — the data was fine)

`G-V6-8` says those ten rows have no official URL. They do. The URL is in
`data/raw/official_finals_union.json`, the file `nba2.pipeline.settle` writes moments earlier,
under the key **`source`**:

```json
{"game_id": "0022600231", "away": "DEN", "home": "NOP", "away_pts": 116, "home_pts": 108,
 "source": "https://www.nba.com/game/den-vs-nop-0022600231", …}
```

1. **`_records_of` merged rows wrongly.** Its null-guard was nested inside a second null-guard,
   so the *last* row for a game id could overwrite a non-null value from an earlier row with an
   explicit `null`. Fixed: a non-null always wins; a `null` only fills a key that is absent.
2. **The extractor did not accept every key the feeds actually use**, and its `source`
   fallback was applied inconsistently. Replaced with `_official_url()`, which takes the first
   value among `source_url`, `final_source_url`, `official_source`, `source` **only if it is
   an `https://` URL on an `nba.com` host**. A prose label, a relative path or a third-party
   URL is treated as absent, so no link is ever invented.

### Why the gate was not lowered

A fix that made `G-V6-8` pass unconditionally would be worse than the bug. The new
`nba2/v6/test_results_union_source.py` (7 tests) pins **both** directions: the URL is
surfaced when the file carries it, and a row with no official URL still has to fail. Two of
the seven read the *committed* union and every row `finals_committed()` publishes, so a future
regression breaks the build rather than the deploy.

### Proof

The same eleven-module sequence that failed, run at `a5380e1` with only the two patched files
copied in:

```
nba2.pipeline.settle 0 · nba2.v4.settlement 0 · build_site_data 0 · build_site 0 ·
backtest.engine.build 0 · nba2.v2 0 · settlement_page 0 · nba2.v3 0 · nba2.v4 0 ·
nba2.v5 0 · nba2.v6 0        <-- the step that failed ten times now exits 0
```

On the merged tree: the full 10-module rebuild is still a **fixed point (0 drift)**, 92/59/37
root+v6+v7 tests pass, `nba2.v6.check` exits 0, 8024 internal links OK, 1436 sourced rows.

**Still open and flagged:** whether the *production* run now succeeds will only be known at the
next scheduled fire (or after a manual dispatch). This session can prove the sequence is
reproducible from the committed inputs — which is exactly what the publish job does — but it
cannot observe the next cron run.

### Follow-through: the dual-deploy race was found and fixed

While checking the deploy, this session noticed that **two** workflows declared the
`github-pages` environment — `pages.yml` and `verification-desk.yml` — and that the desk
workflow uploaded `audit/923eb342/` as the *entire* Pages artefact. Whichever run finished
second would replace the site root, so the front door could silently become a 25 KB audit page
instead of the dashboard. It was recorded here and, before this branch merged, session
`arena/923eb342-nba2` landed the fix on `main` in PR #149 (`2ae9ee2`, "stop deploying a second
Pages artefact — it replaced the canonical site root").

Measured outcome on `main` after that fix: `grep -rn 'deploy-pages' .github/workflows/` resolves
to `pages.yml` only, and the live root `/NBA2/index.html` is the dashboard (verified through the
page-fetch transport after the merge of PR #146).
