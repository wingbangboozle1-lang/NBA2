# Independent cross-check of the published site against the committed snapshots

Owner: `arena/5b80b88a-nba2` · run 2026-11-14 01:20 UTC · tool: `tools/crosscheck_site.py` (stdlib only, read-only)

## What this is, in one paragraph

CI proves the HTML is a faithful render of `data/site.json`, and the provenance lint proves every row is labelled. Neither can prove that a label matches what it points at, because the same code produced both. This report re-derives each published claim from the committed snapshot files with its own arithmetic. A **PASS** means the published artefact agrees with the committed snapshot and with the other surfaces in this repository; it is never a claim that the official source was re-read today, because this environment has no route to `nba.com` — measured, not assumed: `python3 tools/ingest_official.py --probe` returns a TLS failure for all four official endpoints from the sandbox that produced this report. A **FAIL** is a defect worth a change request. An **N/A** means the claim's referent is not computable from committed evidence, and no plausible number was substituted for it.

**Result: 72 PASS · 8 FAIL · 8 INFO · 0 N/A over 88 checks.**

## Findings that need a decision

- **CC-SNAP-13** — ratings: the snapshot's own PASS/FAIL labels still describe the data. Observed: recomputed imbalance => PASS; stored labels say FAIL. every close/blowout game is one win and one loss, so the league-wide sums must match; a mismatch means the per-team split columns are not a complete partition of the games
- **CC-DER-05** — the two W-L columns are independent measurements, as the caption claims. Observed: 30/30 rows identical; caption: 'Both W-L columns are printed on purpose: if they ever disagree, the table is wrong.'. FAIL here is a presentation defect, not a wrong number: the column labelled 'W-L (official NBA.com)' is populated from the same third-party field as the other column, so the 'if they ever disagree the table is wrong' guard can never fire. See the CR in COORDINATION.md.
- **CC-DER-11** — no count published anywhere on the site is negative. Observed: 1 negative count(s): ['availability_window/avail-2026-11-14.no_rows_yet = -5']. a negative count is never a measurement; it is two sets subtracted in the wrong order
- **CC-DER-12** — availability coverage recomputes from both official injury snapshots. Observed: 2 problem(s): ['2026-11-14: published no_rows_yet -5, recomputed 0 (slots 10 - filed 5 - not-submitted-only 5)', '2026-11-14: published NOT YET SUBMITTED 10, recomputed 5 teams that have no designation in any release either']. the column is a count of teams, and the sets overlap: 'filed' and 'NOT YET SUBMITTED' are not disjoint when two releases are unioned, so slots - filed - nys can go below zero
- **CC-GATE-02** — each leaderboard row's gate tally equals the gate matrix. Observed: 9 violation(s): ["S-01: claims '0 pass / 0 fail / 10 blocked', matrix says {'PASS': 0, 'FAIL': 0, 'BLOCKED': 8, 'AT-RISK': 2}", "S-02: claims '0 pass / 0 fail / 10 blocked', matrix says {'PASS': 0, 'FAIL': 0, 'BLOCKED': 8, 'AT-RISK': 2}", "S-03: claims '0 pass / 0 fail / 10 blocked', matrix says {'PASS': 0, 'FAIL': 0, 'BLOCKED': 8, 'AT-RISK': 2}"].
- **CC-X-00** — every surface uses the same team key for the same club (joinability). Observed: WAS <- ['WSH (originated/data/teams.json)']. a club written two ways is an invisible row in any join: it silently drops out of the comparison instead of failing it, which is exactly how a '28 of 30' coverage figure can read like a data defect
- **CC-DOC-01** — README's published counts match the artefacts on disk. Observed: 2 stale figure(s): ['README table count: text 33 vs measured 36', 'README row count: text 915 vs measured 964'].
- **CC-HTML-03** — every row in the data file is rendered on some page. Observed: 7 row(s) in the data but not on the site: ['hold-1', 'hold-2', 'hold-3', 'hold-4', 'hold-6', 'xg-0022600235-0022600039']. the brief asks for all entries to be on the site; an unrendered row is an entry nobody can review

## All checks

| ID | Group | Claim checked | How it was recomputed | Verdict | Observed |
|---|---|---|---|---|---|
| CC-SNAP-01 | A. snapshot integrity | every slate record has one cell per declared column | len(cells) == len(columns) for all 31 records in slate_2026-11-13_to_11-16.json | PASS | 31 records x 10 columns |
| CC-SNAP-02 | A. snapshot integrity | official game IDs are unique and well-formed (002 + 7 digits) | regex over the game_id column of the slate snapshot | PASS | 31 unique / 31 rows; bad format: [] |
| CC-SNAP-03 | A. snapshot integrity | every club in the slate is one of the 30 NBA tricodes | set difference against the league's team list | PASS | 30 distinct; unknown: none |
| CC-SNAP-04 | A. snapshot integrity | per-day game counts equal the snapshot's own counts_check | recount records by date and compare with the stored claim | PASS | recomputed {'2026-11-13': 9, '2026-11-14': 5, '2026-11-15': 9, '2026-11-16': 8} vs stored {'2026-11-13': 9, '2026-11-14': 5, '2026-11-15': 9, '2026-11-16': 8} |
| CC-SNAP-05 | A. snapshot integrity | every tip time parses as a 24h ET clock value | HH:MM parse over the slate's time_et column | PASS | unparseable: none |
| CC-SNAP-06 | A. snapshot integrity | the pick window never exceeds as-of + 3 days | max(date) - as_of over slate_2026-11-13_to_11-16.json | PASS | horizon 3 day(s); window 2026-11-13..2026-11-16 |
| CC-SNAP-07 | A. snapshot integrity | the published slate_window string matches the data | compare the meta string's first/last ISO dates with the snapshot's dates | PASS | meta: '2026-11-13 → 2026-11-16 (today + 3 days)' vs data 2026-11-13..2026-11-16 |
| CC-SNAP-08:injury_report_2026-11-14_daybefore | A. snapshot integrity | injury_report_2026-11-14_daybefore.json: its own record_counts equal a recount of its records | recount total / status / placeholder / attribution (and games covered, when claimed) | PASS | stored {'total_rows': 31, 'not_yet_submitted_placeholders': 5, 'attribution_explicit': 21, 'attribution_continuation': 10, 'rows_with_status': 26, 'games_covered': 5} vs recomputed {'total_rows': 31, 'not_yet_submitted_placeholders': 5, 'attribution_explicit': 21, 'attribution_continuation': 10, 'rows_with_status': 26, 'games_covered': 5} |
| CC-SNAP-09:injury_report_2026-11-14_daybefore | A. snapshot integrity | injury_report_2026-11-14_daybefore.json: every status string is one the report can print | set of status values in the snapshot | PASS | statuses: ['Available', 'NOT YET SUBMITTED', 'Out', 'Probable', 'Questionable'] |
| CC-SNAP-10:injury_report_2026-11-14_daybefore | A. snapshot integrity | injury_report_2026-11-14_daybefore.json: attribution is recorded per row (E explicit / C continuation) | column 'attribution' takes only the two documented values | PASS | E=21 C=10 |
| CC-SNAP-08:injury_report_2026-11-13 | A. snapshot integrity | injury_report_2026-11-13.json: its own record_counts equal a recount of its records | recount total / status / placeholder / attribution (and games covered, when claimed) | PASS | stored {'total_rows': 95, 'not_yet_submitted_placeholders': 10, 'attribution_explicit': 84, 'attribution_continuation': 11, 'rows_with_status_for_2026_11_13': 85} vs recomputed {'total_rows': 95, 'not_yet_submitted_placeholders': 10, 'attribution_explicit': 84, 'attribution_continuation': 11, 'rows_with_status_for_2026_11_13': 85} |
| CC-SNAP-09:injury_report_2026-11-13 | A. snapshot integrity | injury_report_2026-11-13.json: every status string is one the report can print | set of status values in the snapshot | PASS | statuses: ['Available', 'Doubtful', 'NOT YET SUBMITTED', 'Out', 'Probable', 'Questionable'] |
| CC-SNAP-10:injury_report_2026-11-13 | A. snapshot integrity | injury_report_2026-11-13.json: attribution is recorded per row (E explicit / C continuation) | column 'attribution' takes only the two documented values | PASS | E=84 C=11 |
| CC-SNAP-11:ratings | A. snapshot integrity | team_ratings_2026-11-13.json states where and when it was retrieved | presence of a provenance url + retrieval stamp inside the file | PASS | url=https://www.basketball-reference.com/leagues/NBA_2027_standings.html; retrieved=2026-11-13T22:35:00Z |
| CC-SNAP-11:times | A. snapshot integrity | official_game_times_2026-11-13.json states where and when it was retrieved | presence of a provenance url + retrieval stamp inside the file | PASS | url=https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf; retrieved=2026-11-13T23:05:00Z |
| CC-SNAP-11:leaders | A. snapshot integrity | team_leaders_2026-11-13.json states where and when it was retrieved | presence of a provenance url + retrieval stamp inside the file | PASS | url=https://www.nba.com/games; retrieved=2026-11-13T22:26:00Z |
| CC-SNAP-11:context | A. snapshot integrity | slate_context_2026-11-17.json states where and when it was retrieved | presence of a provenance url + retrieval stamp inside the file | PASS | url=https://www.nba.com/schedule; retrieved=2026-11-13T22:39:00Z |
| CC-SNAP-12 | A. snapshot integrity | ratings: home+road games reconcile with total games for all 30 clubs | arithmetic identity inside the snapshot | PASS | violations: none |
| CC-SNAP-13 | A. snapshot integrity | ratings: the snapshot's own PASS/FAIL labels still describe the data | sum(close_w)=99 vs sum(close_l)=99; sum(blowout_w)=88 vs sum(blowout_l)=88 | **FAIL** | recomputed imbalance => PASS; stored labels say FAIL |
| CC-SNAP-14 | A. snapshot integrity | ratings: winning percentage equals W/(W+L) to 3 dp | recompute pct from w,l | PASS | violations: none |
| CC-PUB-01 | B. published rows vs the snapshot they cite | every published slate cell equals the snapshot cell | cell-by-cell compare of 31 rows x 7 shared columns | PASS | 0 cell mismatch(es): []; published-not-in-snapshot=[]; snapshot-not-published=[] |
| CC-PUB-03 | B. published rows vs the snapshot they cite | no minute/production/line impact value is published for any injury row | the three columns must be null in every row (the official report carries no such field) | PASS | 95 rows scanned; any non-null would be an invented number |
| CC-PUB-04 | B. published rows vs the snapshot they cite | our P(plays) convention is applied consistently: 'Out' => 0.00 | recount over published injury rows | PASS | 95 rows; Out rows with p_play != 0.00: 0 |
| CC-PUB-05 | B. published rows vs the snapshot they cite | the corroboration table's title counts match its own rows | recompute corroborated / time-lost / outside counts from the two snapshots, compare with the title | PASS | recomputed 11 twice-confirmed, 3 time-lost, 17 outside; title: 'Cross-document corroboration: 11 of 31 games confirmed twice, 3 matchups confirmed with the time cell unreadable, 0 mismatches, 17 outside that report' |
| CC-DER-01 | C. published derived values re-derived by hand-arithmetic | spread string and sign follow from the projected margin | parse all 31 published lines | PASS | 0 violation(s): none |
| CC-DER-02 | C. published derived values re-derived by hand-arithmetic | published total equals the published per-team projections (±0.5) | home+away projected score vs the total column | PASS | 0 violation(s): none |
| CC-DER-03 | C. published derived values re-derived by hand-arithmetic | p(home) equals the implied probability of our own fair price | 1 / decimal fair price vs the published probability, per game | PASS | 0 violation(s): none |
| CC-DER-04 | C. published derived values re-derived by hand-arithmetic | ratings table is internally consistent (net = PS/G - PA/G; shrunk = SRS x lambda; GP = W+L) | recompute from the published cells of all 30 rows | PASS | 0 violation(s): none |
| CC-DER-05 | C. published derived values re-derived by hand-arithmetic | the two W-L columns are independent measurements, as the caption claims | compare the columns' provenance: both are printed by build_ratings_rows from the same model object | **FAIL** | 30/30 rows identical; caption: 'Both W-L columns are printed on purpose: if they ever disagree, the table is wrong.' |
| CC-DER-06 | C. published derived values re-derived by hand-arithmetic | luck table arithmetic (luck = actual - expected; split records fit inside the season) | recompute over 30 rows | PASS | 0 violation(s): none |
| CC-DER-07 | C. published derived values re-derived by hand-arithmetic | parlay table: joint interval ordered, boost = joint / independence | recompute over 10 rows | PASS | 0 violation(s): none |
| CC-DER-11 | C. published derived values re-derived by hand-arithmetic | no count published anywhere on the site is negative | scan every numeric cell of every table whose column name denotes a count | **FAIL** | 1 negative count(s): ['availability_window/avail-2026-11-14.no_rows_yet = -5'] |
| CC-DER-12 | C. published derived values re-derived by hand-arithmetic | availability coverage recomputes from both official injury snapshots | union the team designations across every committed injury snapshot per date, then recount: a team that has since filed must not also be counted as not-yet-submitted | **FAIL** | 2 problem(s): ['2026-11-14: published no_rows_yet -5, recomputed 0 (slots 10 - filed 5 - not-submitted-only 5)', '2026-11-14: published NOT YET SUBMITTED 10, recomputed 5 teams that have no designation in any release either'] |
| CC-DER-08 | C. published derived values re-derived by hand-arithmetic | rotation table: expected-bodies-missing never exceeds the players actually listed, floor inside 0..15 | recompute over 21 teams | PASS | 0 violation(s): none |
| CC-DER-09 | C. published derived values re-derived by hand-arithmetic | rotation counts equal a recount of the published injury rows for the same club | cross-table identity over 21 teams | PASS | 0 violation(s): none |
| CC-GATE-01 | D. gates, leaderboard, rewards | every gate verdict is one of the four defined states | scan of 90 strategy x gate results | PASS | illegal values: none |
| CC-GATE-02 | D. gates, leaderboard, rewards | each leaderboard row's gate tally equals the gate matrix | recount per strategy over 90 rows | **FAIL** | 9 violation(s): ["S-01: claims '0 pass / 0 fail / 10 blocked', matrix says {'PASS': 0, 'FAIL': 0, 'BLOCKED': 8, 'AT-RISK': 2}", "S-02: claims '0 pass / 0 fail / 10 blocked', matrix says {'PASS': 0, 'FAIL': 0, 'BLOCKED': 8, 'AT-RISK': 2}", "S-03: claims '0 pass / 0 fail / 10 blocked', matrix says {'PASS': 0, 'FAIL': 0, 'BLOCKED': 8, 'AT-RISK': 2}"] |
| CC-GATE-03 | D. gates, leaderboard, rewards | no strategy is promoted while it has zero gates passed | promotion must follow evidence, never a model's self-assessment | PASS | 0 violation(s): none — all nine are Blocked |
| CC-GATE-04 | D. gates, leaderboard, rewards | meta.gates_passed / gates_total equal a recount | count PASS rows and total rows in the gate matrix | PASS | recomputed 0/90 vs meta 0/90 |
| CC-GATE-05 | D. gates, leaderboard, rewards | no reward is allocated while no strategy has passed the gates | sum the award amounts and compare with the pool arithmetic | PASS | awards sum 0, meta allocated 0.0, pool 100.0, gates passed 0 |
| CC-GATE-06 | D. gates, leaderboard, rewards | no performance score is published without settled bets behind it | the score column must be blank while the ledger has nothing settled | PASS | rows with a score: none |
| CC-GATE-07 | D. gates, leaderboard, rewards | every gate spec has a threshold and a failure mode stated | check the gate definition table for empty decision rules | PASS | 10 gate definitions |
| CC-SEAL-01 | E. sealed ledger | the seal digest recomputes from the prediction array | sha256 over canonical JSON of 22 predictions in sealed-2026-11-13.json | PASS | stored cf7dedc689597cb8… recomputed cf7dedc689597cb8… |
| CC-SEAL-02 | E. sealed ledger | the number of sealed predictions equals the count in the header and on the site | len(predictions) vs header.n_predictions vs meta.seal.n_predictions | PASS | 22 / 22 / 22 |
| CC-SEAL-03 | E. sealed ledger | the digest printed on every page is the file's own digest | meta.seal.sha256 vs the sealed file header | PASS | site cf7dedc689597cb8… vs file cf7dedc689597cb8… |
| CC-SEAL-04 | E. sealed ledger | every sealed prediction is an official game inside the window, tipped after the snapshot | cross-check the sealed array against the slate snapshot | PASS | 0 problem(s): none |
| CC-SEAL-05 | E. sealed ledger | sealed tip times equal the official tip times they were sealed against | per-game time compare | PASS | 0 problem(s): none |
| CC-SEAL-06 | E. sealed ledger | what was sealed is exactly what the site displays | per-game compare of the published line table against the immutable ledger | PASS | 0 drift(s): none |
| CC-FLAG-01 | F. flags, blanks and provenance discipline | no row cites a flag that does not exist | every one of 1085 flag references resolves to the flags table | PASS | unresolvable: none |
| CC-FLAG-02 | F. flags, blanks and provenance discipline | every flag is attached to at least one published row | a flag nobody references documents nothing | PASS | 0 orphan flag(s): [] |
| CC-FLAG-03 | F. flags, blanks and provenance discipline | every blank cell carries a flag or a note explaining it | independent re-implementation of the site's own blank rule over all rows | PASS | 0 unexplained blank(s): none |
| CC-FLAG-04 | F. flags, blanks and provenance discipline | no value is present on a row whose source is blocked/unavailable | the machine-enforced version of 'leave it blank and flag it' | PASS | 0 violation(s): none |
| CC-FLAG-05 | F. flags, blanks and provenance discipline | an 'official' label only ever points at an NBA-official host | host allow-list check over every row (plus: no third-party row may claim official verification) | PASS | 0 violation(s): none |
| CC-FLAG-06 | F. flags, blanks and provenance discipline | count claims inside flag statements match the data they describe | recompute each numeric claim whose referent is computable: FLAG-SLATE-05 slug-generated URLs 19 vs 19; FLAG-SLATE-05 slate size 31 vs 31 | PASS | 0 stale claim(s): none |
| CC-X-00 | G. cross-surface facts | every surface uses the same team key for the same club (joinability) | normalise the three-letter codes each capture uses and report any club written two ways | **FAIL** | WAS <- ['WSH (originated/data/teams.json)'] |
| CC-X-01 | G. cross-surface facts | a club's W-L is the same number on every surface of this repo | 30 clubs x 5 committed captures: ratings snapshot (Basketball-Reference, 2026-11-13) covers 30/30; nba2/data/records.json (NBA.com/schedule) covers 30/30; originated/data/teams.json (ESPN, cross-checked) covers 30/30; data/standings-2026-11-13.csv covers 30/30; published ratings (site) covers 30/30 | PASS | 0 disagreement(s): none |
| CC-X-02 | G. cross-surface facts | the 28/30 vs 30/30 wording conflict is resolvable from committed evidence | compute, per capture, which clubs are covered; the two figures must name their comparison | INFO | ratings snapshot (Basketball-Reference, 2026-11-13): 30/30; nba2/data/records.json (NBA.com/schedule): 30/30; originated/data/teams.json (ESPN, cross-checked): 30/30; data/standings-2026-11-13.csv: 30/30; published ratings (site): 30/30 |
| CC-X-03 | G. cross-surface facts | clubs the official-capture comparison covers, and the ones it does not | set difference between the published ratings and each official capture | INFO | uncovered by nba2/data/records.json: none |
| CC-X-04 | G. cross-surface facts | the two sessions' independent reads of the official tip times agree | compare site slate times with data/games.csv for the 31 shared game IDs | PASS | 0 mismatch(es): none |
| CC-X-05 | G. cross-surface facts | a third surface's tip times agree with the canonical slate | originated/data/slate.json over 23 shared IDs | PASS | 0 mismatch(es): none |
| CC-X-06 | G. cross-surface facts | the cross-session line-delta column is arithmetically right | recompute our-minus-theirs over 23 rows | PASS | 0 violation(s): none |
| CC-X-07 | G. cross-surface facts | the other session's line file is the actual referent of the comparison table | the xlines rows must correspond to rows that exist in data/our-lines.csv | PASS | 23/23 comparison rows have a source row on disk |
| CC-X-08 | G. cross-surface facts | the cross-session record-agreement claim equals its own table | recount agree rows in xrecords (30/30) vs the title 30/30 agree | PASS | recomputed 30/30 |
| CC-X-09 | G. cross-surface facts | the cross-session comparison does not silently compare a value with itself | the PS/G column of the prior session must be genuinely blank where that session had no source | PASS | 28/30 rows blank on their side |
| CC-BT-01 | K. the measured-skill surface, recomputed | the report's headline counts equal a recount of the committed game rows | 155 unique games across 6 history files, 21 dates 2026-10-20..2026-11-12 | PASS | report says n_games=155, n_dates=21, 2026-10-20..2026-11-12; bad rows: none |
| CC-BT-02 | K. the measured-skill surface, recomputed | a 'final scores' set contains only games that precede the snapshot it is graded against | compare each game date with the slate snapshot as_of (2026-11-13) | PASS | 0 game(s) dated after the snapshot: none |
| CC-BT-03 | K. the measured-skill surface, recomputed | every published rate equals its own numerator over its own denominator | recompute ATS hit rate, the three naive baselines, and the head-to-head difference | PASS | 0 violation(s): none |
| CC-BT-04 | K. the measured-skill surface, recomputed | the tier and calibration breakdowns partition the graded sample, and each bin reports its own range | tiers 139 / calibration 139 / accuracy.n 139 | PASS | 0 problem(s): none |
| CC-BT-05 | K. the measured-skill surface, recomputed | the gate summary is a true index of the per-gate statuses | regroup the 10 gate verdicts by status and compare with the summary lists | PASS | 0 problem(s): none |
| CC-BT-06 | K. the measured-skill surface, recomputed | every gate verdict follows from the numbers printed beside it | parse each 'arithmetic' string and re-check the percentage and the pass/fail direction | PASS | 0 problem(s): none |
| CC-BT-07 | K. the measured-skill surface, recomputed | the provisional leaderboard ranks by the metric it names, and pays nobody while a gate fails | 4 strategies; gate summary failed=['G-01'] blocked=['G-02', 'G-06', 'G-09', 'G-10'] | PASS | 0 problem(s): none |
| CC-BT-08 | K. the measured-skill surface, recomputed | the two surfaces tell one story about what has been measured | root site publishes gates_passed=0 of 90 with the line 'Ledger opens with the 2026-11-13 slate; nothing has settled yet'; the backtest surface reports 2 of 10 gates PASS on 139 graded games | INFO | the two are not contradictory — the site's gates are stated in settled bets against a price, the backtest's in graded games against outcomes — but a reader of the canonical page cannot see that 139 games have been graded at all, and the vocabulary differs (PASS/FAIL/BLOCKED/AT-RISK vs PASS/FAIL/BLOCKED/PARTIAL) |
| CC-DOC-01 | H. documentation claims | README's published counts match the artefacts on disk | measure each figure directly: README table count=36; README row count=964; README test count=62; README page count=18 | **FAIL** | 2 stale figure(s): ['README table count: text 33 vs measured 36', 'README row count: text 915 vs measured 964'] |
| CC-DOC-02 | H. documentation claims | meta.games / meta.teams / meta.injury_rows equal the sections they describe | recount the slate, ratings and injuries tables | PASS | meta 31/30/95 vs 31/30/95 |
| CC-DOC-03 | H. documentation claims | meta.tiers equals a recount of the line table | count tier letters: {'B': 15, 'C': 16} | PASS | meta {'A': 0, 'B': 15, 'C': 16, 'BLOCKED': 0} |
| CC-DOC-04 | H. documentation claims | the site reports which snapshot it is built from | meta.snapshot_as_of must equal the slate snapshot's own as_of | PASS | meta '2026-11-13' vs snapshot '2026-11-13' |
| CC-DOC-05 | H. documentation claims | generated_at_utc is a real timestamp and the build declares itself idempotent | parse the stamp; read build_is_idempotent | PASS | '2026-11-14 01:07 UTC', idempotent=True |
| CC-DOC-06 | H. documentation claims | the verification line quoted on the coordination board matches the current build | board says 915 rows across 33 tables; build says 964/36 | INFO | INFO when a refresh is in flight: the board is a historical record of the run that made it, and this session must not rewrite another session's log |
| CC-DOC-07 | H. documentation claims | the committed inputs are unambiguous (digest over every raw snapshot recorded) | sha256 over 7 raw snapshot files, names included | INFO | this session's input digest 4190ec51a2595320… vs meta.input_digest 244017e3d8ee1314… |
| CC-HTML-01 | I. what the browser is actually served | every rendered table row on the site carries a source cell | regex scan of 1005 rendered <tr id=...> rows across 18 HTML files | PASS | 0 row(s) without a source cell |
| CC-HTML-02 | I. what the browser is actually served | every internal link and every flag anchor resolves to a real target | checked all static hrefs plus the anchor id inside the target file (the repo's own link checker does not verify anchors) | PASS | 0 broken file link(s): none; 0 dead anchor(s): none |
| CC-HTML-03 | I. what the browser is actually served | every row in the data file is rendered on some page | 707 published row keys vs 700 ids present in the HTML; data blanks 844 vs rendered blank markers 837 | **FAIL** | 7 row(s) in the data but not on the site: ['hold-1', 'hold-2', 'hold-3', 'hold-4', 'hold-6', 'xg-0022600235-0022600039'] |
| CC-HTML-03b | I. what the browser is actually served | the literal em-dash is only ever used for “not applicable”, never for “not verified” | count literal em-dash values per table; a withheld value must be null so the renderer marks it blank+flagged | INFO | anomalies: 1; gate_matrix: 9; gates: 3; injuries: 10; injuries_window: 5; params: 8; props: 4; slate: 22; xinjuries: 2 |
| CC-HTML-04 | I. what the browser is actually served | every navigation target on the landing page exists | 17 distinct page links from index.html | PASS | missing: none |
| CC-HTML-05 | I. what the browser is actually served | no published page is unreachable from the landing page | a page nobody can click is a page nobody reviews | PASS | unlinked page(s): none |
| CC-FRESH-01 | J. freshness (the known product blocker) | the snapshot is within one day of the run date (the freshness SLA the brief implies) | as_of 2026-11-13 vs run date 2026-11-14 | PASS | 1 day(s) old; games already tipped or tipping inside the published window: 2 date(s) |
| CC-FRESH-02 | J. freshness (the known product blocker) | a stale snapshot is disclosed, not hidden | grep the emitted landing page for a staleness statement | INFO | the site prints the as-of date on every page |
| CC-FRESH-03 | J. freshness (the known product blocker) | a scheduled ingestion exists, and it has actually run | list the workflows and their triggers; then record whether any ingest run exists yet | INFO | ci.yml: push,pull_request,workflow_dispatch; pages.yml: push,workflow_dispatch; refresh.yml: schedule,workflow_dispatch; ingest runs recorded: unknown (no runs reported or gh unavailable) — not a PASS: the schedule is armed but nothing has run, so the site's freshness still depends on a manual or first-scheduled ingest |

## Evidence links for manual review

- CC-SNAP-04: <https://www.nba.com/schedule>
- CC-SNAP-08:injury_report_2026-11-14_daybefore: <https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf>
- CC-SNAP-08:injury_report_2026-11-13: <https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf>
- CC-PUB-05: <https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_01_00PM.pdf>
- CC-SEAL-01: <https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/raw/ledger/sealed-2026-11-13.json>
- CC-BT-01: <https://www.nba.com/games>
- snapshot provenance recorded by the build: <https://www.basketball-reference.com/leagues/NBA_2027_standings.html>

## Appendix 1 — per-club win-loss evidence across every committed capture (this is what settles the `28/30` vs `30/30` wording conflict)

| Club | ratings snapshot | nba2/data/records.json | originated/data/teams.json | data/standings-2026-11-13.csv | published ratings | All agree? |
|---|---|---|---|---|---|---|
| ATL | 7-5 | 7-5 | 7-5 | 7-5 | 7-5 | yes |
| BKN | 3-8 | 3-8 | 3-8 | 3-8 | 3-8 | yes |
| BOS | 10-2 | 10-2 | 10-2 | 10-2 | 10-2 | yes |
| CHA | 4-8 | 4-8 | 4-8 | 4-8 | 4-8 | yes |
| CHI | 1-9 | 1-9 | 1-9 | 1-9 | 1-9 | yes |
| CLE | 6-6 | 6-6 | 6-6 | 6-6 | 6-6 | yes |
| DAL | 7-5 | 7-5 | 7-5 | 7-5 | 7-5 | yes |
| DEN | 6-4 | 6-4 | 6-4 | 6-4 | 6-4 | yes |
| DET | 8-3 | 8-3 | 8-3 | 8-3 | 8-3 | yes |
| GSW | 8-4 | 8-4 | 8-4 | 8-4 | 8-4 | yes |
| HOU | 9-3 | 9-3 | 9-3 | 9-3 | 9-3 | yes |
| IND | 4-8 | 4-8 | 4-8 | 4-8 | 4-8 | yes |
| LAC | 2-8 | 2-8 | 2-8 | 2-8 | 2-8 | yes |
| LAL | 11-2 | 11-2 | 11-2 | 11-2 | 11-2 | yes |
| MEM | 7-4 | 7-4 | 7-4 | 7-4 | 7-4 | yes |
| MIA | 5-6 | 5-6 | 5-6 | 5-6 | 5-6 | yes |
| MIL | 1-11 | 1-11 | 1-11 | 1-11 | 1-11 | yes |
| MIN | 9-3 | 9-3 | 9-3 | 9-3 | 9-3 | yes |
| NOP | 4-8 | 4-8 | 4-8 | 4-8 | 4-8 | yes |
| NYK | 6-5 | 6-5 | 6-5 | 6-5 | 6-5 | yes |
| OKC | 8-4 | 8-4 | 8-4 | 8-4 | 8-4 | yes |
| ORL | 4-7 | 4-7 | 4-7 | 4-7 | 4-7 | yes |
| PHI | 10-3 | 10-3 | 10-3 | 10-3 | 10-3 | yes |
| PHX | 5-6 | 5-6 | 5-6 | 5-6 | 5-6 | yes |
| POR | 8-3 | 8-3 | 8-3 | 8-3 | 8-3 | yes |
| SAC | 1-10 | 1-10 | 1-10 | 1-10 | 1-10 | yes |
| SAS | 10-2 | 10-2 | 10-2 | 10-2 | 10-2 | yes |
| TOR | 5-7 | 5-7 | 5-7 | 5-7 | 5-7 | yes |
| UTA | 1-11 | 1-11 | 1-11 | 1-11 | 1-11 | yes |
| WAS | 4-9 | 4-9 | 4-9 | 4-9 | 4-9 | yes |

_Reading: each column is one independent capture committed to this repository. `—` means that capture has no row for that club (that is the whole difference between a coverage count and an agreement count). A bold cell means two captures disagree, which is a defect, not a rounding choice._

## Appendix 2 — published rows that never reach a page

| Section (title) | Rows built but rendered on no page |
|---|---|
| parlay_costs — Cost of stacking (pure arithmetic — no data needed to verify) | hold-1, hold-2, hold-3, hold-4, hold-6 |
| parlays_xg — Cross-game parlays, and what stacking costs | xg-0022600235-0022600039, xg-0022600239-0022600246 |

The data file holds them, the lint counts them, CI parity-checks them — no page calls `render_table` on them, so nobody reviews them. `nba2/pipeline/build_site.py` maps page -> sections; `pages/parlays.html` lists only `correlation` and `parlays` even though `build()` also produces `parlays_xg` and `parlay_costs`.

## How to reproduce

```
python3 tools/crosscheck_site.py                      # console summary of every check
python3 tools/crosscheck_site.py --markdown analysis/crosscheck-5b80b88a.md
```

Exit code is non-zero iff a check FAILs, so the run can be wired into CI without changing what the site publishes.

