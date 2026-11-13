# NBA Lines Lab

A source-linked research dashboard and specification for an auditable NBA forecasting/strategy leaderboard. The repository currently has no model, historical dataset, odds feed, injury ingestion, or automated deployment. Consequently it does **not** publish picks, lines, correlations, or claimed returns. The dashboard makes those gaps explicit rather than inventing values.

## Local preview

Open `index.html` in a browser. The site is dependency-free and designed for GitHub Pages. Enable Pages in repository settings (deploy from `main` / root, or configure the official Pages workflow) before expecting a public URL; deployment is not configured or confirmed by this repository.

## What is included

- Executive summary, research design, candidate strategy families and hard validation gates.
- Operational data requirements for slate generation up to 72 hours ahead, injury/rotation and game-flow analysis.
- A decision register and a **Flagged for Review** page with explicit missing inputs and official source links.
- A strict policy: no populated pick/market/model statistic unless it is supported by a source, timestamp, and reproducible calculation.

See the dashboard for links and limitations. Injury reports are time-sensitive; always consult the latest NBA report and do not treat a status label as a guaranteed minutes forecast.


---

## Verification-first documentation site (`docs/`) — session arena-35264d96

A 13-page verification-first documentation layer (served at `/NBA2/docs/`), complementing the dashboards above:

| Page | Contents |
|---|---|
| [Executive Summary](docs/executive-summary.html) | The project on one page |
| [Strategies](docs/strategies.html) | Origination pipeline + 12-strategy catalog (`data/strategies_lab.json`) |
| [Validation Gates](docs/validation-gates.html) | G1–G13 gates; luck-removal methods; staking |
| [Correlation](docs/correlation.html) | Parlay/SGP math; correlation matrix template; portfolio caps |
| [Leaderboard](docs/leaderboard.html) | Competition scoring, tiers, rewards, anti-gaming |
| [Slate Picks](docs/picks.html) | T+3 pick pipeline, daily runbook on the official report clock, demo output |
| [Injuries & Rotations](docs/injuries-rotations.html) | Official injury-report policy (verified verbatim); minutes framework |
| [Game Flow](docs/game-flow.html) | Pace, clutch, blowouts, late fouling, rest |
| [Questions & Answers](docs/questions.html) | Decision-readiness: answered (with sources) / blocking / discovery paths |
| [Suggestions](docs/suggestions.html) | Review-before-implementing improvement backlog |
| [Flagged for Review](docs/flagged-for-review.html) | Every irregularity and unverified item |
| [Sources](docs/sources.html) | Master source ledger |

Lab tools (stdlib only): `tools/generate_picks_lab.py` (slate pick generator; refuses slates beyond
today+3 days and refuses picks from strategies whose gates lack backtest evidence),
`tools/verify_site.py` (docs site: every data row must carry a source link; no broken links),
`tools/check_links_all.py` (whole-site link check across all sessions' pages).

```bash
python3 tools/generate_picks_lab.py --demo   # synthetic demo of the pick pipeline
python3 tools/verify_site.py                 # verify docs tables are fully sourced
python3 tools/check_links_all.py             # link check across root/, pages/, verified/, docs/
```
