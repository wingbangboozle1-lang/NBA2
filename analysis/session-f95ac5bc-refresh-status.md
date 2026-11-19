# Session `arena/f95ac5bc-nba2` — scheduled-refresh status and v2 freshness disclosure

**Date:** 2026-11-14 UTC

**Scope:** F95-01 only. Record the observed scheduled-ingest outcome, correct stale operational claims, and distinguish workflow execution from freshness of the published v2 model inputs. No NBA model input, line, prediction, grade, stake, or sealed ledger was changed.

## Verified run record

The GitHub Actions API reports run [43605830665](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/43605830665) on `main`, event `schedule`, head SHA `b3ed44d839b77f071592cd10d3dc734bc7958b23`, created `2026-11-14T14:37:25Z`, updated/completed `2026-11-14T14:38:06Z`, conclusion **failure**. The linked workflow source is pinned to the run's code revision: [`.github/workflows/refresh.yml` at `b3ed44d`](https://github.com/wingbangboozle1-lang/NBA2/blob/b3ed44d839b77f071592cd10d3dc734bc7958b23/.github/workflows/refresh.yml).

| Workflow stage | Recorded outcome |
|---|---|
| Window-date selection | success |
| Official injury-report archive | success on the runner |
| Official finals fetch | failure |
| Injury transcript check | skipped |
| Sealed-ledger guard | skipped |
| Settlement | skipped |
| Tests, seal, rebuild, provenance verification | skipped |
| Semantic cross-check | skipped |
| Snapshot commit | skipped |

The failed-run log could not be retrieved by the available GitHub CLI request (it returned EOF from GitHub's log-results host). The exact endpoint, response, and failure cause are therefore **unverified**; this record does not infer them. The archived injury step passed on the runner, but the snapshot-commit step did not complete. The run did **not** refresh the published v2 model inputs (`v2_model_inputs_refreshed: false`).

The validated status record is `data/operations/refresh_status.json`; the builder publishes copies to `data/v2/refresh_status.json` and `site/data/refresh_status.json`. It distinguishes the run's created/updated times from the status capture time (`recorded_at_utc: 2026-11-14T18:50:40Z`). Its links and step outcomes are rendered on the v2 dashboard, executive summary, pick-snapshot page, and decision queue.

## Implementation

- Added `nba2/v2/refresh_status.py`, the shared schema validator, reader, and atomic writer. It validates run IDs, SHA-pinned workflow/run URLs, timestamps, outcomes, and the explicit rule that the scheduled v1 job is not evidence of v2-input freshness.
- Updated `.github/workflows/refresh.yml` with stable IDs for each ingest/validation stage and an `always()` status-publication step restricted to `main`. The step fetches and resets to the **remote** branch before cleaning runner-local files. Resetting to the remote—not local `HEAD`—also discards an unpushed local snapshot commit if the earlier snapshot push failed, so a status-only push cannot accidentally replay runner-local NBA inputs. The status path stages only `data/operations/refresh_status.json`, `data/v2`, and `site`; it never stages `data/raw` or the sealed ledger.
- Updated the v2 builder to publish the machine-readable status and a cautious, dated summary. A successful v1 workflow is explicitly not described as a v2 freshness pass; the static slate is labeled as a dated snapshot, not a live slate.
- Corrected the stale `SG-1`, `SG-2`, and `SG-31` operational descriptions in `nba2/v2/content.py`; the decision-queue evidence for `S-40` now comes from the recorded Actions run, its per-step outcomes, and the workflow source. In `suggestions/SUGGESTIONS.json`, only `S-40` was edited by this scope; other suggestion IDs, including additions integrated from PR #65, were preserved.
- Added regression coverage for status parsing, fail-closed run states, published links, and freshness wording in `nba2/v2/test_v2.py`.
- Regenerated the v1 and v2 outputs from committed inputs. The v2 build includes the independently merged pages and register additions from PR #65; those changes were retained during rebase and the generated tree was rebuilt afterward.

## Validation performed

The full local validation chain passed after PR #65 was integrated and the generated trees were rebuilt:

| Check | Result |
|---|---|
| `python3 -m unittest discover -s nba2/tests -t .` | 64 passed |
| `python3 -m unittest discover -s backtest/tests -t .` | 49 passed |
| `python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'` | 94 passed |
| `python3 -m nba2.pipeline.seal_predictions --verify` | 27 predictions; seal verified |
| v1 build + provenance lint | 50 tables / 1,415 rows; every row sourced and every blank explained |
| `python3 -m nba2.v2` + `python3 -m nba2.v2.check` | 22 pages; 0 structural and 0 semantic issues |
| `python3 tools/verify_site.py` | 13 pages / 249 rows; every table row linked; no broken internal links or placeholders |
| `python3 tools/verify_backtest.py` | 183 sourced game rows; 189 internal links resolved; deterministic rebuild passed |
| `python3 scripts/check_site.py` | 12 pages / 524 rows checked; links, sources, nav and footer passed |
| `python3 tools/check_links_all.py` | 112 HTML files; 5,017 internal links checked, all resolved |
| `python3 tools/crosscheck_site.py` | 97 checks: 90 pass, 0 fail, 7 informational |
| `python3 -m py_compile nba2/v2/*.py` | passed |
| PyYAML parse of all five `.github/workflows/*.yml` files | passed (syntax parse; not a hosted Actions run) |
| Extracted status-step shell script (`bash -n`) | passed |
| Isolated Git safety simulation | unpushed local snapshot discarded; remotely pushed snapshot retained after fetch/reset/clean |
| `git diff --check` | clean |

The seven cross-check informational items remain informational, not failures. They include the existing backtest-versus-gate-sample disclosure, the historic board/build-line comparison, the intentionally different input-digest file sets, and one em-dash interpretation anomaly. No values were inferred to clear them.

## Sources, limits, and handoffs

- Run metadata and step outcomes: [GitHub Actions run 43605830665](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/43605830665) and the [GitHub Actions run API record](https://api.github.com/repos/wingbangboozle1-lang/NBA2/actions/runs/43605830665).
- Executed workflow revision: [`.github/workflows/refresh.yml` at run SHA `b3ed44d`](https://github.com/wingbangboozle1-lang/NBA2/blob/b3ed44d839b77f071592cd10d3dc734bc7958b23/.github/workflows/refresh.yml).
- Manual review links in the published queue: [official NBA schedule](https://www.nba.com/schedule?date=2026-11-15) and [official NBA results page](https://www.nba.com/games?date=2026-11-13). No NBA endpoint was fetched in this F95 status task and no NBA facts were added or changed.
- The workflow change has not yet been exercised by a hosted refresh run. A local YAML parse and unit/build checks do not establish that GitHub Actions successfully publishes the status commit.
- The site deployment after the other sessions' main-branch merges was not confirmed at the time of this report: the latest Pages Actions run was queued, earlier superseded runs were cancelled, and the Pages API was still reporting `errored` while a Pages build reported `building`. This is not evidence of a successful deploy or of broken page content. Recheck the Pages workflow and API after it completes; do not claim a deployment until then.
- PR #50 remained open and unchanged at its old head when rechecked. The pre-documented handoff covers only its stale generated executive-summary status wording and the `S-40` correction; no other PR #50 scope was edited. PR #57's refresh/pipeline and spread-dispatch changes were left intact. PR #65 was merged at `de495fe`; its site/build/register work was retained and regenerated on this branch. PR #66's board-only record was also merged at `d7c19ec` and preserved.
- No v2 modeling inputs, model outputs, originated lines, sealed picks, grades, stakes, or `data/raw/ledger/**` files were modified. The local seal verification passed. No hosted refresh was manually dispatched, so no new runner ingest or settlement was initiated by this task.
- After the F95 implementation was prepared, PR #67 ([freshness and rolling-slate audit](https://github.com/wingbangboozle1-lang/NBA2/pull/67), head `77704a07`) became active and claimed shared `nba2/v2/build.py`, `content.py`, `live.py`, and generated site surfaces. Its rolling-slate/F-043/Q-36 findings are complementary to F95's status-only workflow change, but the rendered outputs overlap. I posted a coordination comment at [#issuecomment-6882997776](https://github.com/wingbangboozle1-lang/NBA2/pull/67#issuecomment-6882997776) and will preserve its changes when rebasing/regenerating; PR #67 was still open with its checks queued at the last check.

The PR, merge, and post-merge Pages result for F95 are recorded in the append-only F95 completion entry in `COORDINATION.md` after those steps are complete.
