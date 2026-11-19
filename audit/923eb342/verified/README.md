# Verified official rows — session `arena/923eb342-nba2`

Read at **2026-11-19T12:20Z** with the **platform page-fetch tool (primary) — direct TLS from the sandbox to nba.com returned SSL_ERROR_SYSCALL / HTTP 000, so no urllib capture is possible here**.

Direct TLS from the execution sandbox to `www.nba.com`, `official.nba.com`,
`ak-static.cms.nba.com` and `stats.nba.com` fails (`SSL_ERROR_SYSCALL`, HTTP 000), so every row
below was read through the platform page-fetch transport. That is a real transport with a real
retrieval timestamp — it is recorded rather than hidden, because "how was this read" is part of
whether a number can be trusted.

| File | Contents | Official source | Rows verified |
|---|---|---|---|
| `finals_2026-11-17.json` | date, teams, final, quarter scores | <https://www.nba.com/games?date=2026-11-17> | 5 finals; quarters re-checked against the committed official capture |
| `finals_2026-11-18.json` | date, teams, final, quarter scores | <https://www.nba.com/games?date=2026-11-18> | 12 finals; **quarters blank + flagged** — no committed official capture holds 11/18 |
| `injury_2026-11-19.json` | revision time, retrieval time, every row | <https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_07_00AM.pdf> | 8 transcribed rows (incl. two `NOT YET SUBMITTED` clubs) |
| `standings_2026-11-19.json` | W-L, home/road, division, last-10, streak | <https://www.nba.com/standings> | 30 clubs; ΣW = ΣL identity checked |

## What is deliberately blank

* **Quarter scores for 2026-11-18.** The final scores are official and read this session; the
  quarter-by-quarter breakdown is not in a committed capture yet, so it is `null` with
  `quarters_status: unverified`. It is not reconstructed from the final.
* **Pacers box-score rows for 0022600259.** Only the Houston rows were transcribed; the rest of
  that page was not read. A partial transcription is published as partial.
* **`was-vs-chi` on 2026-11-20.** The game id fell outside the captured chunk of the games page,
  so it is left empty rather than inferred from the sequence of neighbouring ids.

## Rules this ingest keeps

1. A row exists only if an official page printed it this session.
2. A quarter row is accepted only when its own sum equals the official final.
3. A missing value is `null` + a status string, never a plausible number.
