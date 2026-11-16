"""Render the v5 pages into ``site/`` and wire them into the shared navigation.

The navigation is *inherited*, not invented: the block is read back out of an
already-rendered published page, so a v5 page can never advertise a page it did not build.
Injection into the other pages is idempotent and marker-guarded, exactly as v3 and v4 do it.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from . import check as CH
from . import model as M
from . import transcript as T

SITE = T.ROOT / "site"
DATA = T.ROOT / "data" / "v5"

V5_NAV = [
    ("result-feed-v5.html", "Result feed (11/14–11/15)"),
    ("playerlogs-full.html", "Player logs (full)"),
    ("rotation-replacement.html", "Minutes &amp; replacement"),
    ("v5-verify.html", "v5 verification"),
]
V5_PAGES = [n for n, _ in V5_NAV]
V5_NAV_MARKER = '<a href="result-feed-v5.html"'

SESSION = T.SESSION
WINDOW = "2026-11-13 → 2026-11-15"

GAMEBOOK = "https://statsdmz.nba.com/pdfs/2026{d}/{d}_{m}_book.pdf"
GB_1114_DETMIA = GAMEBOOK.format(d="1114", m="DETMIA")
GB_1114_CHIMIN = GAMEBOOK.format(d="1114", m="CHIMIN")
GB_1115_DALBOS = GAMEBOOK.format(d="1115", m="DALBOS")
GB_1115_NYKTOR = GAMEBOOK.format(d="1115", m="NYKTOR")
GB_1115_SASUTA = GAMEBOOK.format(d="1115", m="SASUTA")
GB_1115_OKCSAC = GAMEBOOK.format(d="1115", m="OKCSAC")
GB_1113_MEMNOP = GAMEBOOK.format(d="1113", m="MEMNOP")

# (id, severity, where, official URL the flag is about, what is wrong, what is published)
FLAGS = [
    ("F-V5-01", "gap", "Player logs (full)", GB_1114_DETMIA,
     "The official gamebooks are read as text through the platform page-fetch tool; bash "
     "egress to statsdm.nba.com returns HTTP 000 from this environment, so the PDF bytes "
     "cannot be committed.",
     "Committed: the transcript of every gamebook, each row's official URL, and the "
     "retrieval window. The arithmetic gates in nba2/v5/check.py re-derive the official "
     "totals from the transcript on every build, which is what makes a transcription "
     "error visible."),
    ("F-V5-02", "gap", "Player logs (full)", GB_1114_DETMIA,
     "In game 0022600233 (DET@MIA) the extracted visitor table carries a spurious cell in "
     "at least one row: the Detroit players' rebound totals sum to 47 against the club's "
     "published 46, and one row prints TOT=1 with OR=0 and DR=0. No single row can be "
     "identified as the wrong one from the extracted text alone.",
     "Detroit's rebound cells in that game are blank and carry this flag. Minutes, points "
     "and assists for the same game reconcile exactly and are published."),
    ("F-V5-03", "gap", "Player logs (full)", GB_1114_CHIMIN,
     "In game 0022600235 (CHI@MIN) the extracted table drops the TOT rebound cell for "
     "Tre Jones.",
     "The value is recovered as 0 because the club totals (TOT 48, OR 12, DR 36) reconcile "
     "with no other value; the row says so and the arithmetic gate re-checks it."),
    ("F-V5-04", "gap", "Result feed", GB_1115_DALBOS,
     "In game 0022600240 (DAL@BOS) the extracted SCORE BY PERIOD row for Dallas prints the "
     "period header numbers instead of the scores.",
     "Dallas's quarter scores are blank with this flag. The final (94) is confirmed twice "
     "and independently: the club total row and the sum of the twelve Dallas players."),
    ("F-V5-05", "info", "Result feed", GB_1115_NYKTOR,
     "Game 0022600241 (NYK@TOR) went to overtime; the gamebook prints a fifth period and "
     "club minutes of 265:00 rather than 240:00.",
     "The OT quarter scores (17-13) are stored and published. The committed feed for that "
     "game records ot_periods=1 but not the OT scores themselves."),
    ("F-V5-06", "gap", "Minutes & replacement", GB_1115_SASUTA,
     "The official gamebooks disagree on the spelling of four players between dates "
     "(Marcus Sassar/Sasser, Keaton Wagler/Wagner, Julian Champagne/Champagnie, "
     "Stephen/Stephon Castle). Merging them would be an inference about identity.",
     "The pairs are reported on the verification page and excluded from the replacement "
     "table, where a same-player split would fabricate an in/out pair. They remain "
     "distinct rows in the log table."),
    ("F-V5-07", "gap", "Player logs (full)", GB_1113_MEMNOP,
     "The 11/13 capture records only the players who appeared, so it has no DNP/DND rows "
     "and absence cannot be measured from it.",
     "An absence is measured only from the 11/14 and 11/15 gamebooks, which print the full "
     "active list. The 11/13 capture contributes 'played' games, never 'out' games, and "
     "the page says so."),
    ("F-V5-08", "info", "Player logs (full)", M.INJURY_INDEX_URL,
     "Some injury-report rows carry a reversed name (e.g. 'Jr., Ernest Udeh'), an artefact "
     "of the 11/16 report transcript committed by the v4 session.",
     "Left exactly as the report prints it and listed as unmatched. Not corrected, because "
     "correcting it would change a value the official document published."),
    ("F-V5-09", "gap", "Minutes & replacement", GB_1115_OKCSAC,
     "Fourteen clubs have only one game in the window, so a player who missed a game "
     "cannot be distinguished from a player who simply has no second game.",
     "Those clubs publish shares but no replacement row; the row is blank with this reason "
     "rather than filled with a league-average assumption."),
    ("F-V5-10", "gap", "Player logs (full)", GB_1113_MEMNOP,
     "The committed 11/13 capture records Jerami Grant's count line (22 pts, 1 reb, 1 ast) "
     "with no minutes, and no DNP/DND rows at all for that date.",
     "His minutes are blank with this flag rather than back-filled from the box score, and "
     "the 11/13 capture contributes 'played' games only, never 'out' games (F-V5-07)."),
    ("F-V5-11", "gap", "v5 verification", M.INJURY_INDEX_URL,
     "Of the 83 rows on the 11/16 01:00 PM ET release, 11 carry no status in the extracted "
     "text (a layout artefact of the official PDF, carried forward from the v4 session's "
     "F-V4-06). Their status cannot be read.",
     "Those rows are listed with the status cell blank and are never counted as Available "
     "and never folded into the Out/Questionable counts. The counts on this page are of "
     "rows whose status the release actually printed."),
]


def esc(x) -> str:
    return "" if x is None else html.escape(str(x), quote=True)


def link(url: str, label: str = "book", title: str | None = None) -> str:
    t = f' title="{esc(title)}"' if title else ""
    return f'<a href="{esc(url)}"{t}>{esc(label)}</a>'


def blank(reason: str) -> str:
    return f'<span class="blank" title="{esc(reason)}">—</span>'


def kpis(items: list[tuple[str, str]]) -> str:
    return ('<div class="kpis">' +
            "".join(f'<div class="kpi"><b>{esc(v)}</b><small>{esc(l)}</small></div>'
                    for v, l in items) + "</div>")


def table(head: list[str], rows: list[str], caption: str | None = None) -> str:
    th = "".join(f"<th>{h}</th>" for h in head)
    cap = f"<caption>{esc(caption)}</caption>" if caption else ""
    return ('<div class="scroll"><table>' + cap +
            f"<thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")


def _inherited_nav() -> list[tuple[str, str]]:
    src = SITE / "slate.html"
    out: list[tuple[str, str]] = []
    if not src.exists():
        return out
    doc = src.read_text()
    m = re.search(r"<nav>(.*?)</nav>", doc, re.S)
    if not m:
        return out
    seen = set()
    for href, label in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', m.group(1), re.S):
        if href in V5_PAGES or href in seen or href.startswith("result-feed-v5"):
            continue
        seen.add(href)
        out.append((href, label))
    return out


def page(title: str, active: str, body: str, lede: str = "") -> str:
    nav = []
    for href, label in _inherited_nav():
        cls = ' class="on"' if href == active else ""
        nav.append(f'<a href="{esc(href)}"{cls}>{label}</a>')
    nav.append('<a href="result-feed-v5.html" style="margin-top:10px;opacity:.6;'
               'pointer-events:none">— v5 player logs —</a>')
    for href, label in V5_NAV:
        cls = ' class="on"' if href == active else ""
        nav.append(f'<a href="{esc(href)}"{cls}>{label}</a>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · NBA2 Lines Lab v5</title>
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<div class="wrap">
<aside>
  <div class="brand">NBA2 <span>Lines Lab</span></div>
  <p class="tag">v5 · official gamebooks {esc(WINDOW)}</p>
  <nav>
{chr(10).join(nav)}
  </nav>
</aside>
<main>
<p class="crumbs"><a href="index.html">Dashboard</a> · v5 player logs · session <code>{esc(SESSION)}</code></p>
<h1>{esc(title)}</h1>
<p class="lede">{lede}</p>
{body}
<footer>
Built by session <code>{esc(SESSION)}</code> from the official NBA gamebook PDFs at
statsdmz.nba.com, read {esc(_window_text())}. Every row links to the gamebook it was read
from. A blank cell is a value we do not have; it is never a zero and never an estimate.
See <a href="v5-verify.html">v5 verification</a> for the gates, the coverage count and
every flag.
</footer>
</main>
</div>
</body>
</html>
"""


def _window_text() -> str:
    return "2026-11-16 ~18:23–18:36 UTC"


# --------------------------------------------------------------------------- pages
def page_results(res: dict) -> str:
    rows = []
    for r in res["results"]:
        qa = " ".join(str(x) for x in r["away_quarters"]) if r["away_quarters"] else blank(
            r["quarters_blank_reason"] or "not printed")
        qh = " ".join(str(x) for x in r["home_quarters"]) if r["home_quarters"] else blank(
            "not printed")
        ot = ""
        if r["ot_quarters"]:
            ot = (f"{' '.join(str(x) for x in r['ot_quarters']['away'])} / "
                  f"{' '.join(str(x) for x in r['ot_quarters']['home'])}")
        status = r.get("_status") or "—"
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in [
            r["date"], r["matchup"], f"{r['away_pts']}", f"{r['home_pts']}",
            qa, qh, ot or "—", status,
            link(r["source_url"], "book", r["game_id"]),
        ]) + "</tr>")
    body = [
        kpis([
            (str(len(res["results"])), "games captured (11/14 + 11/15)"),
            (str(sum(1 for r in res["results"] if r["away_quarters"] and r["home_quarters"])),
             "games with both quarter rows"),
            (str(sum(1 for r in res["results"] if r.get("_newly_settled"))),
             "newly settled here (were 'not final' in the committed feed)"),
            (str(sum(1 for r in res["results"] if r["ot_periods"])), "games decided in overtime"),
            (str(sum(1 for r in res["results"] if not r["away_quarters"])),
             "games with a blank quarter row (flagged)"),
        ]),
        table(["Date", "Matchup", "Away", "Home", "Away quarters", "Home quarters", "OT",
               "Status in the committed feed", "Source"], rows,
              caption="One row per game: date, teams, final score, quarter scores."),
        '<div class="note"><b>What "newly settled" means.</b> The committed feed '
        '<code>data/raw/results/results_2026-11-15.json</code> was captured at '
        '2026-11-16 ~02:05 UTC, when HOU@WAS, ATL@MIL and OKC@SAC were still in progress; '
        'it records them as "not final at retrieval" with no score. They are final in the '
        'gamebooks read this session, so their scores and quarter rows are committed here '
        'for the first time. Every other game is cross-checked against the committed feed '
        'by gate <code>V5-G6</code>.</div>',
    ]
    return page("Result feed — 2026-11-14 and 2026-11-15", "result-feed-v5.html",
                "\n".join(body),
                "One row per game: date, teams, final score and quarter scores, each read "
                "from that game's official NBA gamebook PDF and checked against the "
                "committed official result feeds.")


def page_logs(res: dict) -> str:
    rows = []
    for r in res["rows"]:
        if r["played"]:
            minutes = (esc(r["min"]) if r["min"] else blank(r["min_blank_reason"] or ""))
            pts = esc(r["pts"]) if r["pts"] is not None else blank("")
            reb = (esc(r["reb"]) if r["reb"] is not None
                   else blank(r["reb_blank_reason"] or ""))
            ast = esc(r["ast"]) if r["ast"] is not None else blank("")
            status = "played"
        else:
            minutes = esc(r["status"] or "not in the book")
            pts = reb = ast = "—"
            status = esc(r["status"] or "")
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in [
            r["date"], r["matchup"], r["team"], r["opp"], r["player"],
            esc(r["pos"] or "—"), minutes, pts, reb, ast, status,
            link(r["source_url"], "book", r["source_url"]),
        ]) + "</tr>")
    inj = res["injury"]
    body = [
        kpis([
            (str(res["n_rows"]), "player rows"),
            (str(res["n_games"]), "team-games"),
            (str(res["n_clubs"]), "clubs covered"),
            (f"{inj['n_matched']}/{inj['n_report_rows']}",
             "11/16 injury-report players with a captured log"),
            (f"{inj['n_matched_played']}/{inj['n_report_rows']}",
             "of those, players with minutes in the window"),
        ]),
        table(["Date", "Matchup", "Team", "Opponent", "Player", "Pos", "MIN", "PTS", "REB",
               "AST", "Status", "Source"], rows,
              caption=f"{res['n_rows']} rows: every player on every club's active list, "
                      f"including the DNP/DND rows, for 2026-11-13 → 2026-11-15."),
        '<div class="note"><b>Why the DNP rows are here.</b> A player printed as '
        '"DNP - Coach\'s Decision" or "DND - Injury/Illness …" was on the active list and '
        'available; only a player <i>absent from the book</i> is treated as out. Keeping '
        'both is what makes the replacement table on '
        '<a href="rotation-replacement.html">the minutes page</a> measurable at all.</div>',
    ]
    return page("Player game logs — full union", "playerlogs-full.html", "\n".join(body),
                "Minutes, points, rebounds and assists for every player on every club's "
                "active list, joined to the opponent, for the three captured dates. The "
                "11/13 rows come from the committed capture by session "
                "arena/f8f8f2b8-nba2; the 11/14 and 11/15 rows are new in this session.")


def page_rotation(res: dict) -> str:
    mins = res["minutes"]
    repl = res["replacement"]
    share_rows = []
    for m in mins:
        top8 = " · ".join(f'{p["player"]} {p["share"]*100:.1f}%' for p in m["top8"])
        dnp = ", ".join(f'{d["player"]} ({d["status"]})' for d in m["dnp"]) or "—"
        share_rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in [
            m["date"], m["matchup"], m["team"], str(m["n_played"]),
            f'{m["top8_share"]*100:.1f}%', top8, dnp,
            link(m["source_url"], "book", m["source_url"]),
        ]) + "</tr>")
    repl_rows = []
    for r in repl:
        reps = ", ".join(f'{x["player"]} +{x["minutes_delta"]}s' for x in r["replacements"][:3]) or "—"
        repl_rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in [
            r["team"], r["player"], f'{r["avg_min_share_when_playing"]*100:.1f}%',
            f'{r["avg_min_when_playing_s"]//60}:{r["avg_min_when_playing_s"]%60:02d}',
            str(r["games_played"]), str(r["games_out"]), reps, esc(r["window_note"]),
            " ".join(link(u, "book", u) for u in r["source_urls"]),
        ]) + "</tr>")
    covered = {r["team"] for r in repl}
    missing = sorted({m["team"] for m in mins} - covered)
    avg_top8 = sum(m["top8_share"] for m in mins) / len(mins) if mins else 0
    body = [
        kpis([
            (str(len(mins)), "club-games with measured shares"),
            (f"{avg_top8*100:.1f}%", "mean top-8 share of club minutes"),
            (str(len(repl)), "measured out/in pairs"),
            (str(len(missing)), "clubs with no measurable pair"),
        ]),
        "<h2>Top-8 minutes shares</h2>",
        table(["Date", "Matchup", "Club", "Players used", "Top-8 share", "Top 8 (minutes share)",
               "Active but did not play", "Source"], share_rows,
              caption="Minutes share = the player's official minutes divided by his club's "
                      "official team minutes in that game."),
        "<h2>Replacement shares when a player is out</h2>",
        table(["Club", "Player out", "Share when playing", "Minutes when playing",
               "Games played", "Games out", "Who absorbed the minutes", "Window note",
               "Sources"], repl_rows,
              caption="Measured, not modelled: for each player who both played and missed a "
                      "game in the window, the average minutes share of every team-mate with "
                      "and without him."),
        '<div class="note"><b>What this table is and is not.</b> Each row is a subtraction '
        'of two measured averages over the window shown — it is not a fitted effect, it is '
        'not adjusted for opponent, and with one game played and one game missed it is a '
        'single paired difference. It is published because the brief asks for the '
        'replacement shares explicitly, and it is labelled with its own sample size so it '
        'is never mistaken for an estimate.</div>',
        '<div class="note"><b>Clubs with no row.</b> ' +
        esc(", ".join(missing) if missing else "none") +
        ". A player can only be seen to have missed a game if the club has two captured "
        "games and he is absent from one of them; these clubs do not, so the field is "
        "blank rather than filled with a league-average assumption (F-V5-09).</div>",
    ]
    return page("Minutes redistribution & replacement shares", "rotation-replacement.html",
                "\n".join(body),
                "Top-8 minutes shares for every club-game in the window, and the measured "
                "reallocation when a player who has a log is out of one.")


def page_verify(res: dict, gates: list[dict]) -> str:
    first_book = res["results"][0]["source_url"] if res["results"] else GB_1114_DETMIA
    gate_rows = []
    for g in gates:
        gate_rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in [
            g["id"], esc(g["name"]),
            '<span class="ok">PASS</span>' if g["ok"] else '<span class="bad">FAIL</span>',
            f'{g["passed"]}/{g["tested"]}', esc(g["detail"]),
            "hard" if g["hard"] else "advisory",
            link(first_book, "official gamebook", "the documents these gates are measured "
                                                 "against; every game's own URL is on the "
                                                 "result feed"),
        ]) + "</tr>")
    flag_rows = []
    for fid, sev, where, url, wrong, published in FLAGS:
        flag_rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in [
            fid, sev, where, esc(wrong), esc(published), link(url, "official source", url),
        ]) + "</tr>")
    inj = res["injury"]
    body = [
        kpis([
            (f'{sum(1 for g in gates if g["ok"])}/{len(gates)}', "gates passing"),
            (str(res["n_rows"]), "player rows"),
            (f"{res['n_clubs']}/30", "clubs covered"),
            (f'{inj["n_matched"]}/{inj["n_report_rows"]}',
             "injury-report players with a log"),
            (str(len(FLAGS)), "flags published"),
        ]),
        "<h2>Gates</h2>",
        table(["ID", "Gate", "Result", "Measured", "Detail", "Class", "Source"], gate_rows,
              caption="A gate that cannot be evaluated reports skipped and is not counted "
                      "as a pass."),
        "<h2>Injury-report coverage</h2>",
        '<div class="note">Of the <b>' + str(inj["n_report_rows"]) + '</b> rows on the '
        "official 11/16 injury report (release " + esc(inj["stamp"]) + "), <b>" +
        str(inj["n_matched"]) + "</b> have a captured game log in this window and <b>" +
        str(inj["n_matched_played"]) + "</b> of those actually played. The remaining <b>" +
        str(inj["n_unmatched"]) + "</b> are absent from the active list of every captured "
        "game of their club — which is exactly what a report row predicting a player is "
        "out would look like, and is not a gap in the capture. The newest committed release "
        "wins (the 09:30 AM filing was superseded by the 01:00 PM one while this session "
        "ran), and 11 of its rows carry no status in the extracted text, so they are listed "
        "with that cell blank rather than counted as Available (F-V5-11). "
        + link(inj["index_url"], "official injury-report index", inj["index_url"]) +
        ".</div>",
        "<h2>Flags</h2>",
        table(["ID", "Severity", "Where", "What is wrong", "What is published",
               "Source"], flag_rows),
        "<h2>Reproduce</h2>",
        '<pre class="code">python -m nba2.v5.check      # the eight gates, fail-closed exit code\n'
        "python -m nba2.v5            # rebuild data/v5/*.json and the four pages\n"
        "python -m unittest nba2.v5.test_v5 -v</pre>",
        '<div class="note">The transcripts in <code>data/v5/gamebooks_*.json</code> are the '
        'official gamebooks read as text; the PDF bytes cannot be stored from this '
        'environment (F-V5-01). Everything downstream of them — the gates, the shares, the '
        'join — is recomputed from those committed files by the code in '
        '<code>nba2/v5/</code>, so any transcription error is reproduced and caught '
        'arithmetically rather than silently absorbed.</div>',
    ]
    return page("v5 verification", "v5-verify.html", "\n".join(body),
                "Every gate this session's transcripts are put through, the coverage they "
                "reach, and every flag raised along the way.")


def inject_nav() -> int:
    n = 0
    for p in sorted(SITE.glob("*.html")):
        if p.name in V5_PAGES:
            continue
        doc = p.read_text()
        if "</nav>" not in doc or V5_NAV_MARKER in doc:
            continue
        block = ('<a href="result-feed-v5.html" style="margin-top:10px;opacity:.6;'
                 'pointer-events:auto">— v5 player logs —</a>\n')
        block += "\n".join(f'<a href="{h}">{l}</a>' for h, l in V5_NAV)
        p.write_text(doc.replace("</nav>", block + "\n</nav>", 1))
        n += 1
    return n


def write_data(res: dict, checks: dict) -> list[str]:
    DATA.mkdir(parents=True, exist_ok=True)
    out = []
    payloads = {
        "results_union.json": {"schema": "nba2.v5.results.v1", "session": SESSION,
                               "window": WINDOW, "records": res["results"]},
        "player_logs_union.json": {"schema": "nba2.v5.player-logs-union.v1",
                                   "session": SESSION, "window": WINDOW,
                                   "n_rows": res["n_rows"], "n_games": res["n_games"],
                                   "n_clubs": res["n_clubs"], "records": res["rows"]},
        "rotation.json": {"schema": "nba2.v5.rotation.v1", "session": SESSION,
                          "minutes_shares": res["minutes"],
                          "replacement_shares": res["replacement"],
                          "suspect_name_pairs": M.suspect_spelling_pairs(res["rows"]),
                          "folded_names": M.folded_names(res["rows"])},
        "injury_join.json": {"schema": "nba2.v5.injury-join.v1", "session": SESSION,
                             **{k: v for k, v in res["injury"].items()}},
        "checks.json": {"schema": "nba2.v5.checks.v1", "session": SESSION, **checks},
    }
    for name, payload in payloads.items():
        (DATA / name).write_text(json.dumps(payload, indent=2, sort_keys=False))
        out.append(f"data/v5/{name}")
    return out


def build(res: dict) -> tuple[list[str], dict]:
    checks = CH.run()
    gates = checks["gates"]
    failed = [g for g in gates if g["hard"] and not g["ok"]]
    if failed:
        for g in failed:
            print(f"GATE FAILED {g['id']}: {g['detail']}")
        raise SystemExit("v5 build aborted: a hard gate failed, nothing rendered")
    committed = CH._committed_finals()
    for r in res["results"]:
        src = committed.get(r["game_id"])
        if not src:
            r["_newly_settled"] = True
            r["_status"] = "newly settled here (was 'not final at retrieval')"
        else:
            r["_newly_settled"] = False
            same_q = src.get("away_quarters") == r["away_quarters"]
            r["_status"] = (f"agrees with {src['file']}"
                            + ("" if same_q else " (quarter rows differ — see F-V5-04)"))
    SITE.mkdir(exist_ok=True)
    pages = {
        "result-feed-v5.html": page_results(res),
        "playerlogs-full.html": page_logs(res),
        "rotation-replacement.html": page_rotation(res),
        "v5-verify.html": page_verify(res, gates),
    }
    for name, doc in pages.items():
        doc = re.sub(r"href='([^']*)'", r'href="\1"', doc)
        (SITE / name).write_text(doc)
    injected = inject_nav()
    data = write_data(res, checks)
    return list(pages), {"injected_nav": injected, "data": data,
                         "n_gates_pass": checks["n_gates_pass"],
                         "n_gates": checks["n_gates"]}
