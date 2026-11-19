# Refresh disclosure correction — session `arena/3a5c7c75-nba2`

**Date:** 2026-11-19 UTC

**Scope:** correct the landing-page distinction between a successful data capture and a failed site rebuild. No NBA values, raw snapshots, models, ledgers, or navigation were changed.

## Evidence checked

| Claim | Evidence | Result |
|---|---|---|
| The committed capture verdict is for run `44381003145`, scheduled at `2026-11-18T19:29:04Z`. | [`data/raw/refresh_verdict.json`](../data/raw/refresh_verdict.json) | Confirmed. |
| Four capture surfaces are recorded as successful. | `surfaces` in the committed verdict: `injuries`, `finals`, `rolling`, and `v4` all equal `success`. | Confirmed from the committed artifact; this is a capture verdict, not evidence that the site was rebuilt. |
| The overall Actions run failed. | [GitHub Actions run 44381003145](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145), read using `gh run view 44381003145 --json conclusion,createdAt,url,jobs` on 2026-11-19 UTC. | Confirmed: `capture` job succeeded; `publish` job failed. The failing step was “Rebuild every tree from the committed capture”; later gate/test/commit steps were skipped. |
| The v2 model snapshot date is 2026-11-15. | `data/v2/lines.json` and `data/v2/teams.json`, `meta.as_of`; same source is exposed in `nba2/v2/official.py` as `O.AS_OF`. | Confirmed from committed repository artifacts; not a new official NBA fetch. |

## Change made

The dashboard banner now states the v2 `O.AS_OF` date and distinguishes the recorded success of the four capture surfaces from the failed publish/rebuild job. It links directly to the Actions run for manual review. The warning remains explicit that the snapshot is not live. A regression assertion was added inside the existing rendered-site test, so the test-method count does not change.

## Verification

- `python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'` — **167 tests passed**.
- `python3 -m nba2.v2.check` — **0 structural, 0 semantic**.
- `python3 tools/check_links_all.py` — **143 HTML files; 7,472 internal links passed** (8,983 external links inventoried, not all fetched/validated).
- `git diff --check` — passed.

The v2 suite emitted existing `ResourceWarning`s for unclosed game-history files in `nba2/v2/model.py` and `nba2/v2/travel.py`; they did not fail tests and are outside this claim's scope.

## Limits and flagged item

This was a repository/workflow evidence check, not an official NBA live-source verification. It does **not** make the 2026-11-15 model current, and it does not fix the failed publish job or assert a successful Pages deployment. The last successful capture run still did not publish a refreshed model; until a later successful scheduled capture-and-publish is verified, the dashboard should be treated as stale and non-actionable.
