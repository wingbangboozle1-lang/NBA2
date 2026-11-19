# Independent audit — session `arena/f4a5531f-nba2` (2026-11-19 UTC)

Scope: line-by-line repo review, live official-source verification, live-site verification, and a
fresh official capture of the current slate. This session touched only its own namespace
(`analysis/session-f4a5531f-*.md`, `audit/session-f4a5531f/**`,
`data/raw/capture_2026-11-19_f4a5531f/**`) and the append-only board. Everything below was
performed against the tree at `main @ 41cfd81` (PR #133) plus this session's audit-only commits.

## 1. Baseline checker chain (reproduced, not assumed)

Full rebuild chain in committed CI order → all rc=0, tree clean afterwards (fixed point).
Suites: v1 92, v2 167, v3 67, v4 61, v5 26, v6 52, backtest 49, tools 12 — **526 tests, all OK**.
Lint 1,436 rows / 50 tables, every row sourced, every blank explained. 7,472 internal links OK.
Sealed ledgers: 22 predictions `cf7dedc689597cb8` VERIFIED, 27 predictions `c841e8f396dae6ca`
VERIFIED — no ledger changed during verification. Evidence: `audit/session-f4a5531f/baseline/`
(one log per step, `README.md` summarising rc per command).

The only crosscheck failure is the long-disclosed `CC-FRESH-01` (the v1/v2 model source snapshot
is 2026-11-14/15 era). It is disclosed in the published tree; the re-cut is RQ-8892-02 / ACF-7,
claimed by another session on 2026-11-19.

## 2. Official sources re-read this session (each value quoted from the fetched document)

Capture namespace: `data/raw/capture_2026-11-19_f4a5531f/` (all timestamps minute-level, platform
page-fetch tool, 2026-11-19T12:16Z–12:26Z).

| What | Official source | Result | Cross-checks performed |
|---|---|---|---|
| Standings 2026-11-19 (all 30 clubs: W, L, WIN%, CONF, DIV, HOME, ROAD, LAST10, STREAK) | [nba.com/standings](https://www.nba.com/standings) | 30/30 transcribed (`standings_2026-11-19.json`) | league wins 222 == league losses 222; each club GP = W+L; every record beside a club on the official 11/18 games page agrees |
| Finals 2026-11-18 (12 games: date, teams, final) | [nba.com/games?date=2026-11-18](https://www.nba.com/games?date=2026-11-18) | 12/12 finals captured (`finals_2026-11-18.json`) — **none of these were committed anywhere before this capture** (the last committed finals are 2026-11-17; the 11/18 19:29Z nightly captured before the games ended) | card count == calendar count (12); winners' records match the standings page |
| Quarter scores, HOU@IND (0022600259) | [statsdmz gamebook](https://statsdmz.nba.com/pdfs/20261118/20261118_HOUIND_book.pdf) | SCORE BY PERIOD: HOU 39/23/31/26 = 119 ✓; IND 28/18/30/28 = 104 ✓ | sums == finals on the games page |
| Rolling slate 2026-11-19→22 (26 games: date, tip ET, teams, game id, records) | [games?date=](https://www.nba.com/games?date=2026-11-19) per day | 4+9+6+7 = 26 rows (`slate_2026-11-19_to_11-22.json`) | per-date counts == official calendar; club records == standings page |
| Injury report, 11/19 **07:00 AM ET** release (43 rows) | [official.nba.com injury index](https://official.nba.com/nba-injury-report-2026-27-season/) → [07:00 AM PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf) | transcript `injury_transcript_20261119_0700AM.json`; 18 player rows + 25 NOT-YET-SUBMITTED rows | index listed releases through 07:00 AM ET at check time; the 07:30 AM URL returned AccessDenied (not yet published) — newest release correctly identified |
| Team stats — traditional / opponent / advanced (2026-27) | [traditional](https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season), [opponent](https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season), [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) | sample rows per page (`team_stats_2026-11-19.json`); full 30-row re-cut NOT done here (owned task) | GP == W+L == standings for every visible club; opponent page ± equals traditional PTS−OppPTS (LAL/PHI/SAS); OffRtg recomputes from traditional PTS×GP/POSS (LAL/PHI/SAS) |

**Transport finding (measured, corrects a belief):** the standings page and all three team-stat
pages **render fully through the platform page-fetch tool**. The "client-rendered/unreachable"
measurements in `data/raw/page_fixtures/transport_probe.json` are about GitHub-hosted runners and
remain true there; this is an additional, working capture path for the model re-cut — documented,
not inferred.

## 3. Live-site verification (https://wingbangboozle1-lang.github.io/NBA2/)

The live index was fetched this session; the published tree is byte-identical to a local rebuild
(parity gate + this session's rebuild), so local files are authoritative for row-level checks.

| Brief item | Status | Evidence |
|---|---|---|
| Landing page + category subpages | working | live index shows 6 categories (Start here / Projection / Bet-gated / Official record / Injuries / Verification / Decisions) |
| Projection vs bet separation, never mixed | working | projections page: "The bet surface is separate … every stake is 0.00"; picks page: stakes gated, triggers printed (6 stake / 12 trigger / 14 gate mentions) |
| Two estimators, disagreement as headline | working at team/game level | teams page: "The consensus rating sits underneath it, deliberately not first"; lines page: "the two independent estimators … their disagreement" |
| HCA pinned to measured home-win rate | working | hero "+0.77 home-court (pinned to measured home-win rate, pts)"; methodology language |
| Luck z-score / noise band | working | hero "0/30 teams outside luck noise" |
| Total = possessions × PPP | working | projections page: full formula text; identity present on lines page too |
| Injuries banner: revision + retrieval time | working | "revision time 2026-11-15 06:15 AM ET, retrieved 2026-11-15T12:05:00Z" on injuries.html |
| Rotation availability column on picks | working | "Rotation availability" column header present on picks.html |
| Parlay priced with measured ρ | **partial** | strategy-lab S5 prices the same-game parlay with the measured correlation; the naive product is not printed next to it (correlations page shows only a generic ±0.40 worked example) → **F4A-F4** |
| Pre-registration, tamper-evident ledger, settlement stamps | working | seals re-verified this session; settlement stamps linked from the hero |
| Slate generated up to 3 days ahead | working (stale window) | v3 window is 2026-11-17→11-20 built from the 11/17 capture; today's four games are present with game ids matching the official page exactly; window must roll to 11-19→11-22 → **F4A-F3** |

## 4. Flagged irregularities (for the Flagged for Review page — logged as requests, not edited)

- **F4A-F1** — `CC-FRESH-01` (known): model snapshot 2026-11-14/15 era vs official data now 11/19.
  Fresh inputs for the re-cut are in this session's capture namespace. Owner: RQ-8892-02 claim.
- **F4A-F2** — Nightly ingest `publish` job failed on the last two scheduled runs
  ([44328569212](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44328569212),
  2026-11-18T14:49Z and [44381003145](https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145),
  2026-11-18T19:29Z, step "Rebuild every tree from the committed capture"). Both **pre-date** the
  rebuild-chain repair merged in PR #132/#133 (2026-11-19T07:05Z). The repair is therefore
  **unverified in the scheduled environment**; the 2026-11-19 14:05Z/18:35Z scheduled runs are the
  first test. This session cannot dispatch the workflow (HTTP 403 on `workflow_dispatch` from this
  integration — **F4A-F9**), so no pre-verification was possible.
- **F4A-F3** — published rolling-slate window (11/17→11/20) is stale relative to the 11/19 slate;
  the fresh window is captured and ready for the next rebuild.
- **F4A-F4** — parlay ρ-pricing exists but the naive product is not printed beside it (brief asks
  for both). Site tree owned by the integration sessions.
- **F4A-F5** — index hero leads with walk-forward accuracy (67.7%) and its favourite-bias caveat;
  the disagreement-first structure lives on the teams/lines pages. A hero disagreement metric
  would make the brief's headline literal. Suggestion-level.
- **F4A-F6** — in the 07:00 AM 11/19 release transcript, two rows (Kuminga, Pullin) lost their
  leading columns in text extraction and are recorded **blank/unattributed + flagged** rather than
  inferred; the PDF is the authority. Also recorded verbatim: Ja Morant is listed under the
  Portland Trail Blazers in the official release (unusual but official — not "corrected").
- **F4A-F7** — quarter scores for 11 of 12 finals of 11/18 are blank + flagged (gamebooks not read
  in this audit); the ingest owner can fill them from statsdmz per the existing pipeline rules.
  The finals file is deliberately named `final_scores_2026-11-18.json` and the slate file
  `games_2026-11-19_to_11-22.json` — NOT `finals_*`/`results_*`/`slate_*` — because the committed
  v6 reader globs those names under a frozen as-of clock (`AS_OF_UTC = 2026-11-18T19:30:20Z`,
  `nba2/v6/results_coverage.py`) that would misclassify these verified finals as games that had
  not ended (measured: with the glob-matching name, v6's own
  `test_dates_after_latest_capture_remain_not_ended` fails, `12 != 0`). Ingestion therefore
  requires the v6 owner to bump the frozen clock to this capture's retrieval timestamp
  (`2026-11-19T12:18:30Z`) and move the two files into glob-matching names — exactly the
  handoff pattern used when the 2026-11-18 capture landed. Logged as RQ-F4A-1; v6 files are
  claimed by an active session, so this session did not edit them.
- **F4A-F8** — injury-PDF raw bytes (and sha256) are not stored by this capture: the platform fetch
  returns parsed text only. The PDF URL + revision stamp are recorded; runner-side ingest archives
  bytes.
- **F4A-F9** — `workflow_dispatch` on the capture/ingest workflows returns HTTP 403 for this
  session's token; the evidence-commit channel exists but needs a permitted dispatcher.

## 5. Requests logged (files owned by other sessions — not edited)

- **RQ-F4A-1 → integration sessions** (`arena/585453f5-nba2`, `arena/452034cb-nba2`,
  `arena/503146e4-nba2`): surface F4A-F1..F9 on the published Flagged for Review page, and ingest
  `data/raw/capture_2026-11-19_f4a5531f/` as the input to the RQ-8892-02 re-cut. Ingestion steps
  for the v6 owner: (1) bump `AS_OF_UTC/AS_OF_ET/AS_OF_DATE` in `nba2/v6/results_coverage.py` to
  `2026-11-19T12:18:30Z` / `2026-11-19 07:18 ET` / `2026-11-19` (the retrieval timestamp of
  `final_scores_2026-11-18.json`, not wall-clock time); (2) move that file to a `finals_*` or
  `results_*` name and `games_2026-11-19_to_11-22.json` to a `slate_*` name (per-row
  `source_url`/`gamebook_url` fields are already in the reader's accepted shape); (3) update the
  frozen-clock tests to assert the 11/18 finals are counted (12) and that 11/19+ remains not-ended
  at the new as-of; (4) rebuild v2→v6 and re-run the chain.
- **RQ-F4A-2 → ingest owner**: fill the 11 blank quarter rows of 11/18 from statsdmz gamebooks
  (one per game, e.g. `https://statsdmz.nba.com/pdfs/20261118/20261118_MEMCLE_book.pdf`).
- **RQ-F4A-3 → refresh owner**: after today's 14:05Z/18:35Z scheduled runs, record whether the
  publish step passes in the scheduled environment (first test of the PR #132/#133 repair).

## 6. Source links for manual review

- Standings: https://www.nba.com/standings
- Games/finals 11/18: https://www.nba.com/games?date=2026-11-18
- Slate: https://www.nba.com/games?date=2026-11-19 (and 11-20/21/22)
- Injury index: https://official.nba.com/nba-injury-report-2026-27-season/
- Injury PDF (07:00 AM ET, 11/19): https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf
- Team stats: https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season (+ /opponent, /advanced)
- Gamebook (quarter rows): https://statsdmz.nba.com/pdfs/20261118/20261118_HOUIND_book.pdf
- Live site: https://wingbangboozle1-lang.github.io/NBA2/
- Nightly runs: https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44328569212, https://github.com/wingbangboozle1-lang/NBA2/actions/runs/44381003145
