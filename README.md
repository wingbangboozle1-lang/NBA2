 HEAD
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
