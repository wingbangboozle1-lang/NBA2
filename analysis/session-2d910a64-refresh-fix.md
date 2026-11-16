# Session `arena/2d910a64-nba2` — refresh failure isolation and ingest-run check

**Date:** 2026-11-16 UTC
**Scope:** `.github/workflows/refresh.yml`, `.github/workflows/ci.yml`,
`tools/crosscheck_site.py`, new `tools/test_crosscheck_site.py`, this focused note, and
append-only `COORDINATION.md`. This session did not edit NBA values or frozen ledgers; the
branch's main synchronization retains PR #103's already-merged data and code unchanged. No PR
#98 / PR #100 audit files were edited. The shared coordination file was only appended under
the board protocol; their branch-specific product and report files remain untouched.

## Implementation

### Finals failure is isolated from fresh rolling inputs

PR #103 (`arena/4f780342-nba2`) merged a new capture/publish workflow while this work was in
progress. The implementation was adapted to that current architecture rather than replacing
it. The capture job still attempts the independent injury, finals, rolling, and v4 surfaces;
its `continue-on-error` steps preserve the failure outcome while allowing later surfaces to
run. The finals step now returns a failing outcome when the official endpoint is unreachable
or its response is unusable, after recording the gap. No score is inferred.

The separate publish precheck now permits **only** a finals failure. Injury, rolling, and v4
surface outcomes must all be `success`; a missing/unknown outcome is fail-closed. The verdict
file must match the current Actions run ID and the capture job outputs, preventing a stale
verdict from authorizing a rebuild. The normal v2/v3/v4 freshness and provenance checks,
seal verification, tests, and provenance lint still run before a site commit.

When the finals leg fails, the capture job restores `data/settlement.json` and
`data/v4/settlement/**` to the checked-out commit and removes any untracked generated
settlement files before committing capture evidence. It also refuses to commit if settlement
files remain changed. The publish job independently refuses to commit if its rebuild changes
any prior settlement data. Thus, if rolling inputs and their gates pass, they can still be
published while the previous settlement remains intact. A final workflow step marks the
overall Actions run failed after that permitted rolling publication, so monitoring does not
report a complete settlement refresh as success.

The semantic cross-check now matches the checker's uppercase `[FAIL]` output. It blocks on
other failures while leaving the known legacy snapshot age (`CC-FRESH-01`) and README count
drift (`CC-DOC-01`) visible as explicitly named, non-gating checks. These exceptions do not
weaken the direct rolling freshness/provenance gates.

### CC-FRESH-03 reports the latest completed run conclusion

`tools/crosscheck_site.py` requests JSON status and conclusion data for the latest main-branch
`Nightly ingest + settlement` Actions runs, retaining scheduled/manual runs only. It excludes
the current run, selects the latest completed run by creation time, and includes its URL in the
evidence. Only a latest completed `success` can yield `PASS`. A failed, cancelled, missing,
in-progress-only, or API-unavailable result is `INFO`, never a presumed successful refresh;
`INFO` ensures a prior failed settlement attempt cannot block the next gated refresh.

`tools/test_crosscheck_site.py` adds offline regression coverage for run selection and verdict
mapping. `.github/workflows/ci.yml` runs it with
`python -m unittest tools.test_crosscheck_site -v`.

## Verification

- `python3 -m unittest tools.test_crosscheck_site -v` — **12 tests passed**.
- `python3 -m py_compile tools/crosscheck_site.py tools/test_crosscheck_site.py` — passed.
- Parsed both workflow files with PyYAML installed temporarily under `/tmp/nba2-pyyaml`;
  `bash -n` passed for every workflow `run` block, and all five embedded Python heredocs in
  `refresh.yml` compiled successfully.
- Offline execution of the publish precheck against temporary verdict files: finals-only
  failure was allowed; injury failure, rolling failure, unknown finals outcome, and a stale
  run ID all failed closed as expected.
- Offline execution in a temporary Git repository confirmed the settlement-preservation step
  restores both tracked settlement surfaces and removes a newly generated untracked settlement
  file. The publish guard rejected a changed settlement output.
- `git diff --check` — passed.
- `python3 tools/crosscheck_site.py` — **97 checks: 87 pass, 2 fail, 8 info** (exit 1).
  The existing failures remain `CC-DOC-01` (stale README counts) and `CC-FRESH-01` (the
  committed legacy snapshot is two days old). `CC-FRESH-03` reports the latest completed
  scheduled-ingest run as a failure, with evidence link:
  [run 43903704042](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/43903704042),
  created `2026-11-16T16:06:01Z`. It no longer passes merely because runs exist.
- GitHub CLI run-list inspection confirmed that live result. No official NBA endpoint was
  fetched during this task, and the changed scheduled workflow has not been run against a fresh
  official-source response here.

## Remaining limitations

- The latest observed scheduled-ingest run is still failed; its logs were unavailable in the
  earlier audit (`results-receiver.actions.githubusercontent.com` returned EOF). This change
  records and isolates the failure but does not establish a successful live refresh.
- No fresh NBA data was read or promoted. Local/static checks verify code and workflow control
  paths, not the availability or correctness of a future official-source response.
- `CC-DOC-01` and `CC-FRESH-01` remain disclosed failures, as documented in the existing
  post-PR-97 audit. This session did not edit README counts, NBA values, or snapshots; it
  retained PR #103's already-merged capture files unchanged.

## Integration and deployment result

- PR #106 merged to `main` with `--merge` at `2026-11-16T19:01:10Z`; merge commit
  `24dcd6c1bc8e129fa1909a2e9952a65546d13d4e`.
- Required PR checks passed on head `f4ba89f23e07610d50fbf7b59a20c28425c84cab`: `verify`,
  `parity`, `v2`, and `backtest`. Post-merge `verify`, `parity`/Pages, and v2 workflows also
  passed on the merged main commit.
- GitHub Pages deployment succeeded: `Publish GitHub Pages` run
  [43934908546](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/43934908546) and
  `pages build and deployment` run
  [43934907052](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/43934907052).
  Live fetches returned the root page and the deployed `site/settle.html` and
  `site/v4-injuries.html` pages. The root still displays `as-of 2026-11-14`; it is a stale
  legacy snapshot, not evidence of a fresh NBA refresh. The v4 pages show PR #103's committed
  captures. No fresh NBA source was fetched by this session.
