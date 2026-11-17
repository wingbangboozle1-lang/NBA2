"""Render the v6 pages into ``site/``.

Every table row carries the URL of the official document the value came from, or is blank
with the reason printed in the cell. Nothing on these pages is fetched: the inputs are the
files already committed under ``data/``, and each page names them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import check as CH
from . import inventory as INV
from . import market_prior as MP
from . import player_coverage as PC
from . import results_coverage as RC
from .common import (DATA, ROOT, SITE, V6, badge, blank, cell, esc, gh, kpis, link,
                     ncell, note, table)

V6_NAV = [
    ("injury-archive.html", "Injury PDF archive"),
    ("results-coverage.html", "Result-feed coverage"),
    ("player-coverage.html", "Player-log coverage"),
    ("market-prior.html", "Market-anchored prior"),
    ("endpoints.html", "Official endpoints"),
    ("v6-verify.html", "v6 verification"),
]
V6_PAGES = [n for n, _ in V6_NAV]
V6_NAV_MARKER = '<a href="injury-archive.html"'

INJURY_INDEX_URL = INV.INJURY_INDEX_URL


# ------------------------------------------------------------------ page shell
def _inherited_nav() -> list[tuple[str, str]]:
    """Read the nav block back out of an already-rendered page (v5's convention)."""
    for name in ("index.html", "picks.html", "sources.html"):
        p = SITE / name
        if not p.exists():
            continue
        m = re.search(r"<nav>(.*?)</nav>", p.read_text(), re.S)
        if not m:
            continue
        out = []
        for href, label in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', m.group(1), re.S):
            if href in V6_PAGES:
                continue
            out.append((href, label))
        if out:
            return out
    return []


def page(title: str, active: str, body: str, lede: str = "", crumbs: str = "") -> str:
    nav = []
    for href, label in _inherited_nav():
        cls = ' class="on"' if href == active else ""
        nav.append(f'<a href="{esc(href)}"{cls}>{label}</a>')
    nav.append('<hr style="border:0;border-top:1px solid var(--line);margin:12px 0">')
    for href, label in V6_NAV:
        cls = ' class="on"' if href == active else ""
        nav.append(f'<a href="{esc(href)}"{cls}>{label}</a>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — NBA2</title>
<link rel="stylesheet" href="assets/site.css"></head>
<body><div class="wrap">
<aside>
  <p class="brand">NBA2 <span>research desk</span></p>
  <p class="tag">originated lines · sourced row by row</p>
  <nav>
{chr(10).join(nav)}
  </nav>
</aside>
<main>
  <div class="crumbs">{esc(crumbs or 'Dashboard')}</div>
  <h1>{esc(title)}</h1>
  <p class="lede">{lede}</p>
{body}
  <footer>
    Built by <code>nba2/v6</code> · session <code>arena/f5ac4e74-nba2</code> ·
    no value on this page was fetched live; every row links to the official document it was
    read from. Site: <a href="https://wingbangboozle1-lang.github.io/NBA2/">NBA2 on GitHub
    Pages</a>.
  </footer>
</main></div></body></html>
"""


# ------------------------------------------------------- K-03 injury archive
def _full(r: dict) -> str:
    return f"{r.get('date')} {r.get('stamp_et')}"


def _earliest(rels: list[dict]) -> str:
    rows = [r for r in rels if r.get("date") and r.get("stamp_et")]
    return _full(min(rows, key=lambda r: (r["date"], r["stamp_et"]))) if rows else "—"


def _newest(rels: list[dict]) -> str:
    rows = [r for r in rels if r.get("date") and r.get("stamp_et")]
    return _full(max(rows, key=lambda r: (r["date"], r["stamp_et"]))) if rows else "—"


def page_injury_archive(rels: list[dict]) -> str:
    n_bytes = sum(1 for r in rels if r["bytes_stored"])
    n_tr = sum(1 for r in rels if r["transcripts"])
    body = kpis([
        ("official releases in the inventory", str(len(rels))),
        ("PDF bytes archived", f"{n_bytes} / {len(rels)}"),
        ("with a committed transcript", f"{n_tr} / {len(rels)}"),
        ("earliest release", _earliest(rels)),
        ("newest release", _newest(rels)),
    ])
    body += note(
        "The brief asks for <b>every</b> injury PDF, stored with its timestamp. This table is "
        "the inventory that makes that claim checkable: a release counts as known if a "
        "committed document cites its official URL or its bytes are in "
        "<code>data/raw/pdf/</code>. Twelve of the sixteen are <b>not</b> archived as bytes — "
        f"flag {badge('F-F5-03', 'bad')}. The ingester that closes that gap exists "
        f"(<code>{gh('nba2/v6/injury_backfill.py')}</code>) and runs from a GitHub runner, "
        "where <code>ak-static.cms.nba.com</code> answers HTTP 200; it cannot run from a "
        "build sandbox, where the same request is TLS-reset. A release the league has since "
        "taken off the CDN will be recorded as unreachable with its HTTP status — the gap is "
        "the evidence, and no substitute file is ever written.")

    rows = []
    for r in rels:
        rows.append([
            cell(r["stamp_et"]),
            link(r["url"], "PDF", r["url"]),
            (f'<code>{esc(r["pdf_path"])}</code><br>{r["pdf_bytes"]:,} bytes<br>'
             f'<span style="color:var(--muted);font-size:11px">'
             f'sha256 {esc((r["pdf_sha256"] or "")[:16])}…</span>')
            if r["bytes_stored"] else
            blank("not archived — no runner with CDN access has fetched this release yet "
                  "(F-F5-03)"),
            (", ".join(gh(t) for t in r["transcripts"]) if r["transcripts"]
             else blank("no transcript of this release is committed")),
            cell(r["transcript_rows"],
                 reason="the committed transcript does not state a row count"),
            cell(r["retrieved_at_utc"],
                 reason="no retrieval timestamp is recorded for this release"),
            cell(r["index_checked_utc"],
                 reason="the index check time was not recorded for this release"),
            badge("archived", "ok") if r["bytes_stored"] else badge("bytes missing", "bad"),
        ])
    body += table(
        ["Revision (ET)", "Official PDF", "Archived bytes", "Transcript committed", "Rows",
         "Retrieved (UTC)", "Index checked (UTC)", "Status"],
        rows,
        caption="One row per official injury release this repository knows about. "
                f"Index page: {link(INJURY_INDEX_URL, 'official.nba.com injury report', INJURY_INDEX_URL)}")

    body += "<h2>Where each release is referenced</h2>"
    cit = []
    for r in rels:
        if not r["cited_in"]:
            continue
        cit.append([cell(r["stamp_et"]),
                    "<br>".join(gh(c) for c in r["cited_in"][:8])
                    + (f"<br><span style='color:var(--muted)'>+{len(r['cited_in']) - 8} more</span>"
                       if len(r["cited_in"]) > 8 else "")])
    body += table(["Release", "Committed files that cite this official URL"], cit,
                  caption="How the inventory was built — every committed document under "
                          "data/ was scanned for the official CDN URL pattern.")
    return body


# --------------------------------------------------- K-04 result feed coverage
def page_results_coverage(doc: dict) -> str:
    body = kpis([
        ("game dates covered", str(doc["n_dates"])),
        ("games known", str(doc["n_games_known"])),
        ("with an official final", str(doc["n_games_with_final"])),
        ("graded against a seal", str(doc["n_games_graded"])),
        ("last graded game date", str((doc["settlement"] or {}).get("latest_graded_game_date") or "—")),
    ])
    body += note(
        f"As-of <b>{esc(RC.AS_OF_UTC)}</b> ({esc(RC.AS_OF_ET)}). This page is a coverage "
        "measurement, not a refresh: it says how much of the official result feed is "
        "<i>committed</i>, which is the only kind of currency this repository can prove. "
        f"The {doc['n_games_known'] - doc['n_games_with_final']} games without a final are "
        "named on the game table below with the reason, and not one of them has a score "
        "filled in by inference.", "warn")

    rows = []
    for r in doc["rows"]:
        kind = {"complete": "ok", "not ended": "info"}.get(r["status"], "bad")
        rows.append([
            link(r["list_url"], r["date"], "official schedule for this date"),
            str(r["n_scheduled"]), str(r["n_finals_committed"]), str(r["n_graded"]),
            badge(r["status"], kind),
            esc(r["reason"]),
        ])
    body += table(["Date (ET)", "Games", "Official finals committed", "Graded vs a seal",
                   "Status", "Why"],
                  rows,
                  caption="One row per game date. 'Games' is the union of every committed "
                          "official slate snapshot, every sealed ledger and every result "
                          "feed, keyed by official game id.")

    body += "<h2>Per-game result feed</h2>"
    g_rows = []
    for g in doc["games"]:
        aq = g["away_quarters"]
        hq = g["home_quarters"]
        g_rows.append([
            cell(g["date"]),
            esc(g["matchup"]),
            link(g["source_url"], "game", g["source_url"]) if g["source_url"] else blank("no official game URL committed"),
            (f"{g['away_pts']}–{g['home_pts']}" if g["away_pts"] is not None
             else blank("no official final is committed for this game (F-F5-02)")),
            (" ".join(map(str, aq)) if aq else blank("no quarter row committed — the score "
                                                     "is blank, not zero")),
            (" ".join(map(str, hq)) if hq else blank("no quarter row committed — the score "
                                                     "is blank, not zero")),
            cell(g["period_schema"]),
            (badge("sums", "ok") if g["quarter_verdict"] == "quarters sum to the final"
             else badge("no quarters", "off") if g["quarter_verdict"] == "no quarter rows committed"
             else badge(g["quarter_verdict"], "bad")),
            badge("graded", "ok") if g["graded"] else badge("ungraded", "off"),
            link(g["gamebook_url"], "book", g["gamebook_url"]) if g["gamebook_url"] else blank("no gamebook committed"),
        ])
    body += table(["Date", "Matchup", "Official", "Final", "Away periods", "Home periods",
                   "Period schema", "Quarter check", "Settlement", "Gamebook"],
                  g_rows,
                  caption="One row per game — date, teams, final score, quarter scores, exactly "
                          "as the brief specifies. A blank final means the official score was "
                          "never captured, not that the game did not happen.")
    return body


# --------------------------------------------------- K-05 player-log coverage
def page_player_coverage(doc: dict) -> str:
    body = kpis([
        ("injury-report rows", str(doc["n_report_rows"])),
        ("matched to a game log", f"{doc['n_matched']} ({doc['coverage']})"),
        ("…and actually played", str(doc["n_matched_with_minutes"])),
        ("not matched", str(doc["n_unmatched"])),
        ("log rows / games / clubs",
         f"{doc['n_log_rows']} / {doc['n_log_games']} / {doc['n_log_clubs']}"),
    ])
    body += note(
        "The brief asks for per-player game logs for <b>at least</b> the players who appear on "
        f"an injury report. Measured: <b>{doc['n_matched']} of {doc['n_report_rows']}</b> "
        f"named players ({doc['coverage']}) have a committed game log, and "
        f"{doc['n_matched_with_minutes']} of them actually played in the window. "
        f"That is {badge('partial', 'warn')} against the requirement and it is the honest "
        "number, not a rounded one. The gap is a capture gap — the gamebooks for 11/16 and "
        "later were never transcribed (F-V4-02) — and it is not filled by estimating a "
        "replacement from a league average.", "warn")
    body += note(
        f"Report revision <b>{esc(doc['report_stamp_et'])}</b>, retrieved "
        f"<b>{esc(doc['report_retrieved_at_utc'])}</b>, from "
        f"{link(doc['index_url'], 'the official injury index', doc['index_url'])}. "
        f"Log window: {esc(doc['log_window'])}.")

    m_rows = []
    for r in doc["matched"]:
        m_rows.append([
            cell(r["player"], reason="the official report prints no player name on this "
                                     "row (a page-continuation row in the PDF)")
            + (' ' + badge("reversed name on the report", "warn") if r["name_artefact"] else ""),
            cell(r["team"], reason="the official report prints no team on this row"),
            cell(r["status"], reason="the official report prints no status on this row"),
            cell(r["reason"], reason="the official report prints no reason on this row"),
            str(r["n_logs_recounted"]), str(r["n_games_played"]),
            cell(r["last_min"], reason="the gamebook printed no minutes for this player"),
            cell(r["last_pts"], reason="blank on the official gamebook row"),
            cell(r["last_reb"], reason=(r["last_reb_blank_reason"]
                                        or "blank on the official gamebook row")),
            cell(r["last_ast"], reason="blank on the official gamebook row"),
            cell(", ".join(r["opponents"]) or None, reason="no opponent recorded in a committed log"),
            link(r["log_source_url"], "book", r["log_source_url"]) if r["log_source_url"]
            else blank("no gamebook row committed"),
            link(r["report_url"], "report", r["report_url"]),
        ])
    body += table(["Player (as the report prints it)", "Team", "Status", "Reason", "Logs",
                   "Played", "Last MIN", "PTS", "REB", "AST", "Opponent(s)", "Gamebook",
                   "Injury report"],
                  m_rows,
                  caption="Every injury-report player who was matched to a committed official "
                          "game log. Minutes, points, rebounds, assists and opponent are "
                          "exactly what the gamebook printed.")

    body += "<h2>Named on the report, no committed game log</h2>"
    u_rows = []
    for r in doc["unmatched"]:
        u_rows.append([
            cell(r["player"], reason="the official report prints no player name on this "
                                     "row (a page-continuation row in the PDF)")
            + (' ' + badge("reversed name on the report", "warn") if r["name_artefact"] else ""),
            cell(r["team"], reason="the official report prints no team on this row"),
            cell(r["status"], reason="the official report prints no status on this row"),
            cell(r["reason"], reason="the official report prints no reason on this row"),
            cell(r["games_held_for_club"], reason="no game log is committed for this club"),
            cell(r["not_matched_because"], reason="the join recorded no reason for this row"),
            link(r["report_url"], "report", r["report_url"]),
        ])
    body += table(["Player", "Team", "Status", "Reason", "Games held for this club",
                   "Why it did not match", "Injury report"],
                  u_rows,
                  caption="The join is literal: a name matches only when the injury report's "
                          "string equals the gamebook's string. Near-misses are listed, never "
                          "merged — merging them would be an inference about identity.")
    return body


# ------------------------------------------------------ K-02 market prior
def page_market_prior(doc: dict) -> str:
    body = kpis([
        ("w_market", "blank"),
        ("model out-of-sample log-loss", str(doc["model_log_loss"])),
        ("coin-flip baseline L₀", str(doc["baseline_l0"])),
        ("market log-loss", "not measured"),
        ("blended line published", "no"),
    ])
    body += note(
        "The brief asks to blend the model line with the closing line, weighted by measured "
        "out-of-sample log-loss. <b>Only one of the two inputs exists.</b> No closing price "
        f"has ever been captured (R-043 / R-101, {badge('F-V4-04', 'bad')}), so the market's "
        "log-loss cannot be measured, so the weight is undefined. It is published as a blank "
        "with that reason — not as 0, not as 0.5, and not as a plausible guess.", "bad")

    body += "<h2>The rule, pre-registered before any price exists</h2>"
    body += f"<pre>{esc(doc['rule'])}\n\nL0 = ln 2 = {doc['baseline_l0']} nats  (a coin flip on a binary outcome)\ns = L0 − L, floored at 0   (a forecaster worse than a coin flip gets no weight,\n                            never negative weight)</pre>"
    body += note("Pre-registering the rule now is the point: it fixes the weight function "
                 "before there is a market number to fit it to, so the blend cannot later be "
                 "reverse-engineered from a result.")

    body += "<h2>What has actually been measured</h2>"
    m_rows = []
    for m in doc["measurements"]:
        m_rows.append([
            esc(m["id"]), esc(m["sample"]), cell(m["n_games"]), esc(m["window"]),
            ncell(m["log_loss"], 4), ncell(m["log_loss_baseline"], 4),
            ncell(m["skill_vs_baseline"], 4),
            ncell(m["brier"], 3, reason="not computed for this sample"),
            ncell(m["auroc"], 3, reason="not computed for this sample"),
            esc(m["leakage_rule"]),
            gh(m["source_file"]),
        ])
    body += table(["Sample", "What it is", "Games", "Window", "Log-loss", "Baseline",
                   "Skill vs baseline", "Brier", "AUROC", "Leakage rule", "Source"],
                  m_rows,
                  caption="Two independent out-of-sample measurements of the model, scored "
                          "against the same coin-flip baseline.")

    body += "<h2>What the rule would return, for every plausible market log-loss</h2>"
    body += note(esc(doc["grid_note"]))
    g_rows = []
    for g in doc["sensitivity_grid"]:
        g_rows.append([
            ncell(g["hypothetical_market_log_loss"], 4),
            ncell(g["market_skill_vs_coin"], 4),
            ncell(g["w_market"], 4), ncell(g["w_model"], 4),
            gh("nba2/v6/market_prior.py", "rule"),
        ])
    body += table(["IF the market's log-loss were", "market skill vs a coin flip",
                   "THEN w_market", "w_model", "Rule"], g_rows, derived=True,
                  caption=f"Arithmetic on the rule above at L_model = {doc['model_log_loss']} "
                          "(the sealed-ledger measurement). Not a measurement, and not a "
                          "value read from any official document: this is the only table on "
                          "the site whose rows are deliberately unsourced, and it says so.")

    body += "<h2>What would unblock it</h2><ol>"
    for item in doc["what_would_unblock_it"]:
        body += f"<li>{esc(item)}</li>"
    body += "</ol>"
    return body


# ---------------------------------------------------- K-09 endpoint register
def page_endpoints(doc: dict, verdict: dict | None) -> str:
    rows = []
    for r in doc["rows"]:
        rows.append([
            esc(r["name"]),
            link(r["url"], esc(r["url"])[:78], r["url"]),
            cell(r["http_status"], reason="no HTTP status — the request never completed"),
            cell(r["bytes"], reason="no body was returned"),
            cell(r["elapsed_ms"], reason="not measured"),
            badge("reachable", "ok") if r["ok"] else badge("UNREACHABLE", "bad"),
            esc(r["error"] or "—"),
        ])
    body = kpis([
        ("probed at (UTC)", str(doc["probed_at_utc"] or "—")),
        ("endpoints probed", str(len(doc["rows"]))),
        ("reachable", str(sum(1 for r in doc["rows"] if r["ok"]))),
        ("unreachable", str(len(doc["rows"]) - sum(1 for r in doc["rows"] if r["ok"]))),
    ])
    body += note(
        "This table is measured, not assumed: <code>probe-egress.yml</code> runs on a "
        "GitHub-hosted runner and writes "
        f"{gh('data/raw/egress_probe.json')}. It is the evidence behind every \"we could not "
        "read that\" statement on this site, and it is why the nightly settlement is stale.",
        "warn")
    body += table(["Endpoint", "URL", "HTTP", "Bytes", "ms", "Reachable", "Error"], rows,
                  caption="Official endpoint reachability as measured from a runner.")

    if verdict:
        body += "<h2>The last scheduled ingest, surface by surface</h2>"
        s = verdict.get("surfaces", {})
        run_url = verdict.get("run_url")
        v_rows = []
        for k, v in s.items():
            v_rows.append([esc(k), badge(str(v), "ok" if v == "success" else "bad"),
                           link(run_url, "Actions run", run_url) if run_url
                           else blank("no run URL recorded in the verdict file")])
        v_rows.append(["run id",
                       cell(verdict.get("run_id"), reason="the verdict file records no run id"),
                       link(run_url, str(verdict.get("run_id")), run_url) if run_url
                       else blank("no run URL recorded")])
        v_rows.append(["attempted (UTC)",
                       cell(verdict.get("attempted_at_utc"),
                            reason="the verdict file records no attempt timestamp"),
                       link(run_url, "Actions run", run_url) if run_url
                       else blank("no run URL recorded")])
        body += table(["Surface", "Outcome", "Evidence"], v_rows,
                      caption="The four official surfaces of the nightly job, as recorded in "
                              + gh("data/raw/refresh_verdict.json")
                              + " — this is a record of this repository's own build, not a "
                                "value read from an official document.")
        body += note(esc(str(verdict.get("note", ""))))

    body += "<h2>What the two dead endpoints block</h2>"
    body += table(
        ["Blocked capability", "Brief item", "Dead endpoint", "Reachable official alternative"],
        [
            ["Settling the sealed ledger for 2026-11-16", "items 2 and 18",
             "cdn.nba.com live scoreboard (403); stats.nba.com scoreboardv2 (timeout)",
             f"{link('https://www.nba.com/schedule', 'www.nba.com/schedule?date=', 'https://www.nba.com/schedule')} "
             f"(200) and {link('https://statsdmz.nba.com/pdfs/20261115/20261115_INDPHI_book.pdf', 'the official gamebook PDFs', 'https://statsdmz.nba.com/pdfs/20261115/20261115_INDPHI_book.pdf')} "
             "(200) — both reachable, neither wired into the finals fetch"],
        ],
        caption="The repair is a parser against a reachable official endpoint, not a new data "
                "source. It is filed as F-F5-02 and as a suggestion on the Decision queue; "
                "this session did not ship an untested parser, because a parser that returns "
                "a wrong official score is worse than a coverage gap that says so.")
    return body


# ---------------------------------------------------------- K-07 verify page
def page_verify(checks: dict, doc: dict) -> str:
    n_pass = checks["n_gates_pass"]
    n_all = checks["n_gates"]
    body = kpis([
        ("gates", f"{n_pass} / {n_all}"),
        ("publishable", "yes" if checks["publishable"] else "NO"),
        ("injury releases", f"{checks['counts']['injury_releases_with_bytes']} / "
                            f"{checks['counts']['injury_releases']} archived"),
        ("games with a final", f"{checks['counts']['games_with_final']} / "
                               f"{checks['counts']['games_known']}"),
        ("injury-report players with logs",
         f"{checks['counts']['players_matched']} / {checks['counts']['report_rows']}"),
    ])
    rows = []
    for g in checks["gates"]:
        rows.append([
            esc(g["id"]), esc(g["name"]),
            badge("PASS" if g["ok"] else "FAIL", "ok" if g["ok"] else "bad"),
            f"{g['passed']}/{g['tested']}", esc(g["detail"]),
            gh("nba2/v6/check.py"),
        ])
    body += table(["Gate", "What it measures", "Verdict", "Passed", "Measured", "Code"],
                  rows, caption="Every gate is a count over committed rows. A gate that "
                                "cannot be evaluated reports skipped with a reason and is "
                                "never counted as a pass.")
    for g in checks["gates"]:
        if g["failures"]:
            body += f"<h3>{esc(g['id'])} failures</h3><ul>"
            for f in g["failures"][:20]:
                body += f"<li><code>{esc(f)}</code></li>"
            body += "</ul>"
    return body
