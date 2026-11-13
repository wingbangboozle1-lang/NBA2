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
