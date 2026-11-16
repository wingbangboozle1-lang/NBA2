# Session `arena/a11505e1-nba2` — brief audit register (2026-11-16)

Every line of the project brief mapped to where it is implemented on the combined tree, what
official sources it rests on, and what is still missing. **Rule:** no published value without
an official source link; gaps are blank + flagged, never inferred. Status vocabulary:
IMPLEMENTED (measured and green), PARTIAL (built but incomplete, with what is missing),
BLOCKED (cannot proceed without an external input — registered as a question).

## A. Ingestion, freshness and provenance

| # | Brief line | Where implemented | Official sources | Status |
|---|---|---|---|---|
| 1 | Scheduled job refreshes schedule, standings, team stats, injuries per rolling slate; rebuild only after freshness + provenance gates pass | `.github/workflows/refresh.yml` (nightly) → `nba2/v2/refresh.py` (`--write` fail-closed gates: finals/standings/injuries/slate/provenance) + the v4 capture chain | stats.nba.com scoreboard/standings/team tables; official.nba.com injury index | IMPLEMENTED — gate defects fixed in this session's PR takeovers (CR-7 dead gate; standings reconciliation; newest-release picker) |
| 2 | Injury PDFs stored with revision + retrieval timestamps; consecutive reports diffed | `data/raw/capture_*/injury*`, `nba2/v2/injury.py`, `nba2/v4/injury_diff.py`, Injuries banner + v4-injuries page | official.nba.com injury index; ak-static.cms.nba.com PDFs | PARTIAL — transcripts + stamps + content hashes + diffs published; **original PDF bytes not archived** (sandbox egress, F-V4-01/Q-42) |
| 3 | Per-game result feed: date, teams, final score, quarter scores; settle only on verified finals | `data/raw/results/results_*.json` (+ `official_finals_union.json`), `nba2.pipeline.settle`, `site/official-results.html` | nba.com game pages; statsdmz gamebooks | IMPLEMENTED — 197 finals 10-20→11-15; I-FE0-02 (DAL@BOS quarters) closed this session from the gamebook's own score tables |

## B. Pre-registration and tamper evidence

| # | Brief line | Where implemented | Sources | Status |
|---|---|---|---|---|
| 4 | Freeze pre-registration per strategy: signal, thresholds, universe, exact settlement rule | `data/v2/prereg/*.json` (first-freeze-wins, RR-30), `data/v3/prereg/`, `backtest/data/preregistration.json` | — (process artefact) | IMPLEMENTED |
| 5 | Tamper-evident ledger: hash picks before tip, verify after settlement | `nba2/v3/ledger.py` (write-once seals, RR-29), `data/raw/ledger/sealed-*.json` + divergence log, settle re-hashes | official finals at settlement | IMPLEMENTED — seals verify (34e144c6…); divergence log made idempotent this session (D-A115-01) |

## C. Model and pricing

| # | Brief line | Where implemented | Sources | Status |
|---|---|---|---|---|
| 6 | Two independent estimators; published disagreement as headline; blend underneath | `nba2/v2/model.py` (e1 = net-rating, e2 = off/def PPP; disagreement column), `site/lines.html` | team stat pages + finals | IMPLEMENTED |
| 7 | Pin HCA to the measured home-win rate | `nba2/v2/calibration.py` (0.869 pts = 16.987 × Φ⁻¹(0.5204) over 196), `nba2/tests/test_hca_pinned.py` | nba.com/standings-derived finals | IMPLEMENTED — pinned, fitted value published beside it |
| 8 | Luck as z-score; refuse strategies leaning on teams outside the noise band | `nba2/v2/luck.py`, luck gate rows on picks/strategy pages | finals history | IMPLEMENTED (0/30 outside band; gates refuse) |
| 9 | Rest, B2B, 3-in-4 from the official schedule; travel distance from a sourced arena-coordinate table | `nba2/v2/travel.py`, `nba2/v3/gameflow.py`, Schedule-flow columns | nba.com/schedule | IMPLEMENTED — coordinates THIRD-PARTY (Wikidata P625) and labelled (F-V4-03) |
| 10 | Explicit minutes redistribution: top-8 shares + replacement shares | `nba2/v3/rotation.py`, rotation/minutes pages | injury reports + season averages | IMPLEMENTED for captured clubs; replacement shares mechanical and published |
| 11 | Price parlays with measured ρ; print the naive product next to it | `nba2/v2/parlay.py`, `nba2/v3/parlay.py`, correlations page | measured game pairs | IMPLEMENTED |
| 12 | Rotation availability column on the picks page | picks page availability column (newest release) | injury reports | IMPLEMENTED |
| 13 | Market-anchored prior: blend with the closing line weighted by measured OOS log-loss | `market_prior()` framework; w_market blank | — | BLOCKED — no licensed odds feed (G6/Q-46); framework frozen and labelled |
| 14 | Total = possessions × PPP | total estimators in the model; Total A/B published | team stats | IMPLEMENTED |
| 15 | Originate lines; strategy signals; leaderboard with validation gates, correlation values, luck-removed skill; singles/parlays/prop combos | `site/lines.html`, `strategies.html`, `strategy-lab.html`, `skill-attribution.html`, `props.html`, `backtest/` | finals history | IMPLEMENTED — leaderboard unfunded until G6; sample-size gates (G-01) refuse ranking at 172 graded games |

## D. Surfaces, settlement and publishing

| # | Brief line | Where implemented | Sources | Status |
|---|---|---|---|---|
| 16 | Split projection vs bet surfaces; never mix | v4 `projection.html` / `bet.html` + surface-wall check (G-V4-8) | — | IMPLEMENTED — 0 bet rows, 29 explicit G6 refusals |
| 17 | Injury revision + retrieval times in the Injuries banner | v2/v4 injuries banners | injury index | IMPLEMENTED |
| 18 | Settle sealed ledger from official finals with a visible stamp | `site/settle.html` (stamp 2026-11-15T23:59:59Z, seal 34e144c635b83b89), `data/settlement.json` | verified finals | IMPLEMENTED |
| 19 | Re-read the three official team-stat pages; re-cut inputs | v4 capture (traditional/opponent/advanced, 21 cross-checks); v2 `official.py` sums PF/PA from finals and says so | stats.nba.com team pages | PARTIAL-disclosed (I-FE0-03a) — v2's derivation differs from v3/v4's page reads; both labelled |
| 20 | Per-player game logs (min/pts/reb/ast/opponent) for injury-report players | `nba2/v3/playerlogs.py`, player-logs page | statsdmz gamebooks | PARTIAL — 11/13+11/14 committed; 11/15–11/16 not transcribed (F-V4-02; budget, not data) |
| 21 | Picks up to 3 days ahead | v2 window 11/16→11/19 (29 captured), v4 published 11/16→11/18 (25) | schedule | IMPLEMENTED |
| 22 | Injury impact on rotation minutes + game-flow analysis | rotation/minutes/gameflow pages | injury + schedule | PARTIAL — status counts published; production impact blank + flagged where no matched before/after pair exists (F-V4-08) |
| 23 | Executive summary | `site/executive-summary.html` | — | IMPLEMENTED |
| 24 | Suggestions section with review workflow | `site/suggestions.html`, `decision-queue.html`, `suggestions/SUGGESTIONS.json` | — | IMPLEMENTED (S-01..S-63) |
| 25 | Questions/answers register + missing-information discovery | `site/questions.html`, `requirements/QUESTIONS.json`, `analysis/questions.md` | — | IMPLEMENTED (Q-01..Q-43) |
| 26 | GitHub Pages dashboard: landing + category subpages, per-row source links | `site/**` (published tree), lint + link checks | all rows | IMPLEMENTED — lint 1,441 rows/50 tables sourced; live host serves the v2 tree (verified this session) |
| 27 | Line-by-line verification with official links; blank + flag unverified; never infer | `nba2/v2/check.py`, `pipeline.lint`, `tools/crosscheck_site.py`, `tools/check_links_all.py` | — | IMPLEMENTED |
| 28 | Parallel-session coordination protocol | `COORDINATION.md` (claims, takeovers, preserved records) | — | IMPLEMENTED |
| 29 | Final integration: PR → merge → Pages confirmed → record | this session's PR + `COORDINATION.md` completion record | — | see the completion record |
| 30 | Flagged irregularities published, not blocking | `site/flagged.html` (69 flags incl. F-V4-01..09 now) | per flag | IMPLEMENTED |

## Open decisions / missing information (registered)

See `requirements/QUESTIONS.json` Q-44..Q-46 (this session; ids re-keyed after collision
with the parallel v5 session's Q-40..43 — its byte-archive question Q-43 and suggestion
S-57 cover PDF bytes) and `analysis/questions.md`: Pages source of truth (owner), frozen-v1
grading policy (owner), licensed closing-lines feed (procurement). These are the four decisions the repo cannot make for
itself; everything else is either implemented or flagged with a mechanical route forward.
