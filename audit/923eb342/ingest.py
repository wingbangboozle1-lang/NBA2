"""Land officially-verified rows that this session read, into this session's namespace.

Why a separate namespace
------------------------
`data/raw/**`, `data/v4/**`, `data/v6/**` and the generated `site/`/`pages/` trees are inside
other live sessions' change sets (open PRs #130/#131 and two claim-only branches). Editing them
from here would collide. So every row this session verified is written under
`audit/923eb342/verified/` with the exact official URL and retrieval time, and the site page
that renders it is `audit/923eb342/index.html` (published by this session's own workflow).

What is written, and why each row is safe to write
--------------------------------------------------
1. `finals_2026-11-17.json` / `finals_2026-11-18.json` — one row per game: date, teams, final
   score, quarter scores. The FINAL score is read from the official games page for that date
   (captured this session). The QUARTER scores are taken from this repository's committed
   official capture **only when that row exists and its quarters sum to the score this session
   read from the official page**. A game is never given quarters it cannot be shown to have:
   2026-11-18 rows are written with `quarters: null` and `quarters_status: unverified` because
   no committed official capture holds 11/18 yet.
2. `injury_2026-11-19.json` — the 11/19/26 07:00 AM ET release: revision time, retrieval time,
   and every row transcribed from the official PDF, with the PDF URL.
3. `standings_2026-11-19.json` — W-L, home/road, division record, last-10, streak per club,
   transcribed from nba.com/standings this session.
4. `README.md` — what was read, when, with what transport, and what could not be read.

Run: python3 audit/923eb342/ingest.py     (idempotent; rewrites byte-identical output)
"""

from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
CAP = json.loads((HERE / "capture_2026-11-19.json").read_text())
ROOT = HERE.parents[1]
VER = HERE / "verified"
VER.mkdir(exist_ok=True)

READ_AT = CAP["retrieved_at_utc"]
TRANSPORT = CAP["transport"]


def committed_finals(date: str) -> dict[str, dict]:
    """Rows from this repo's committed official captures, keyed by game id."""
    out: dict[str, dict] = {}
    for p in sorted((ROOT / "data" / "raw").glob(f"**/finals_{date}.json")):
        doc = json.loads(p.read_text())
        for r in doc.get("records", doc.get("games", [])):
            gid = str(r.get("game_id"))
            if gid and gid not in out:
                out[gid] = {**r, "_committed_in": str(p.relative_to(ROOT))}
    return out


def write(name: str, doc: dict) -> None:
    (VER / name).write_text(json.dumps(doc, indent=1) + "\n")


# --------------------------------------------------------------- 1. official results, per game
for date, key in (("2026-11-17", "games_2026_11_17"), ("2026-11-18", "games_2026_11_18")):
    committed = committed_finals(date)
    rows = []
    for g in CAP[key]:
        c = committed.get(g["game_id"])
        q_status, hq, aq, ot = "unverified", None, None, None
        if c and c.get("home_q") and c.get("away_q"):
            if sum(c["home_q"]) == g["home_pts"] and sum(c["away_q"]) == g["away_pts"]:
                hq, aq, ot = c["home_q"], c["away_q"], c.get("ot_periods")
                q_status = "verified (committed official capture; quarters sum to the official final)"
            else:
                q_status = "rejected (committed quarters do not sum to the official final)"
        rows.append({
            "game_id": g["game_id"],
            "date": date,
            "away": g["away"], "home": g["home"],
            "away_pts": g["away_pts"], "home_pts": g["home_pts"],
            "final_status": g.get("note") or ("Final/OT" if (ot or 0) > 0 else "Final"),
            "away_quarters": aq, "home_quarters": hq, "ot_periods": ot,
            "quarters_status": q_status,
            "score_source_url": f"https://www.nba.com/games?date={date}",
            "score_read_at_utc": READ_AT,
            "transport": TRANSPORT,
        })
    write(f"finals_{date}.json", {
        "schema": "nba2.verified.official-finals.v1",
        "session": CAP["session"],
        "date": date,
        "n_games": len(rows),
        "retrieved_at_utc": READ_AT,
        "method": "final scores read from the official games page for the date in this session; "
                  "quarter rows only from a committed official capture whose quarters sum to that score",
        "records": rows,
    })

# --------------------------------------------------------------- 2. injury release
inj = CAP["injury_2026_11_19_0700"]
write("injury_2026-11-19.json", {
    "schema": "nba2.verified.injury-release.v1",
    "session": CAP["session"],
    "report_stamp_et": inj["report_stamp"],
    "revision_time_et": inj["report_stamp"],
    "retrieval_time_utc": READ_AT,
    "pdf_url": inj["url"],
    "index_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "n_rows": len(inj["rows"]),
    "rows": inj["rows"],
    "filing_rule_source": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "note": "Rows are exactly what the PDF prints for the games transcribed; the release also covers "
            "11/20 games whose teams had not yet submitted at 07:00 AM ET (the PDF says "
            "NOT YET SUBMITTED for those).",
})

# --------------------------------------------------------------- 3. standings
extra = {
    "PHI": ["4-1", "8-2", "W 4"], "BOS": ["4-0", "7-3", "L 2"], "DET": ["0-0", "7-3", "W 2"],
    "MIA": ["1-1", "8-2", "W 6"], "ATL": ["4-1", "7-3", "W 2"], "NYK": ["3-3", "7-3", "W 2"],
    "CLE": ["2-0", "4-6", "L 1"], "ORL": ["0-2", "5-5", "L 1"], "TOR": ["0-4", "2-8", "L 6"],
    "IND": ["0-1", "3-7", "L 2"], "WAS": ["2-3", "2-8", "W 1"], "CHA": ["2-2", "1-9", "L 3"],
    "CHI": ["1-1", "3-7", "W 1"], "BKN": ["0-3", "3-7", "L 3"], "MIL": ["1-2", "0-10", "L 11"],
    "LAL": ["5-1", "9-1", "L 1"], "SAS": ["2-1", "9-1", "L 1"], "HOU": ["2-1", "7-3", "W 1"],
    "MIN": ["3-0", "8-2", "W 2"], "MEM": ["1-1", "6-4", "W 4"], "POR": ["4-2", "6-4", "L 2"],
    "DEN": ["0-2", "7-3", "W 1"], "OKC": ["1-2", "5-5", "L 1"], "DAL": ["1-3", "5-5", "W 1"],
    "GSW": ["3-2", "6-4", "L 4"], "PHX": ["3-2", "6-4", "W 2"], "NOP": ["1-1", "3-7", "L 1"],
    "LAC": ["1-4", "3-7", "L 1"], "UTA": ["0-2", "2-8", "W 2"], "SAC": ["0-3", "1-9", "L 7"],
}
home_road = {"PHI": ("6-2", "7-1"), "BOS": ("6-1", "5-3"), "DET": ("3-2", "7-2"),
             "MIA": ("5-3", "4-3"), "ATL": ("3-3", "6-3"), "NYK": ("4-3", "4-3"),
             "CLE": ("6-3", "2-5"), "ORL": ("1-5", "5-3"), "TOR": ("2-6", "3-4"),
             "IND": ("2-5", "3-4"), "WAS": ("2-5", "3-6"), "CHA": ("3-4", "1-6"),
             "CHI": ("1-4", "3-6"), "BKN": ("1-5", "2-6"), "MIL": ("1-7", "0-7"),
             "LAL": ("6-2", "7-1"), "SAS": ("5-3", "7-0"), "HOU": ("7-1", "5-3"),
             "MIN": ("7-2", "4-2"), "MEM": ("3-4", "8-0"), "POR": ("3-2", "6-3"),
             "DEN": ("3-3", "4-2"), "OKC": ("5-1", "4-5"), "DAL": ("6-2", "2-5"),
             "GSW": ("6-1", "2-6"), "PHX": ("5-4", "2-3"), "NOP": ("4-7", "1-4"),
             "LAC": ("4-4", "0-5"), "UTA": ("1-7", "2-6"), "SAC": ("0-9", "1-4")}
rows = []
for tri, (w, l) in CAP["standings_2026_11_19"].items():
    div, l10, streak = extra[tri]
    hr = home_road[tri]
    rows.append({"tri": tri, "w": w, "l": l, "pct": round(w / (w + l), 3),
                 "home": hr[0], "road": hr[1], "div": div, "last10": l10, "streak": streak,
                 "source_url": "https://www.nba.com/standings"})
write("standings_2026-11-19.json", {
    "schema": "nba2.verified.standings.v1",
    "session": CAP["session"],
    "as_of": "2026-11-19",
    "retrieved_at_utc": READ_AT,
    "source_url": "https://www.nba.com/standings",
    "transport": TRANSPORT,
    "n_clubs": len(rows),
    "identity_check": {
        "sum_wins": sum(r["w"] for r in rows),
        "sum_losses": sum(r["l"] for r in rows),
        "wins_equal_losses": sum(r["w"] for r in rows) == sum(r["l"] for r in rows),
        "note": "every club appears exactly once; total W must equal total L in a league table",
    },
    "records": rows,
})

# --------------------------------------------------------------- 4. README
(VER / "README.md").write_text(f"""# Verified official rows — session `arena/923eb342-nba2`

Read at **{READ_AT}** with the **{TRANSPORT}**.

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
""")
print("wrote", sorted(p.name for p in VER.iterdir()))
