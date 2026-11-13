#!/usr/bin/env python3
"""Generate the static pages in verified/ from data/verified/*.json.

Stdlib only. Every table row gets a source link; the build refuses to write a row without one.
Run: python3 tools/generate_picks.py && python3 tools/build_verified.py && python3 tools/verify_data.py
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "verified"
OUT = ROOT / "verified"
OUT.mkdir(exist_ok=True)


def j(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def e(x):
    return html.escape("" if x is None else str(x), quote=True)


def link(url, label):
    if not url:
        raise ValueError("row without source link: " + label)
    return f'<a href="{e(url)}" rel="noopener">{e(label)} ↗</a>'


def table(headers, rows):
    head = "".join(f"<th>{e(h)}</th>" for h in headers)
    body = []
    for r in rows:
        body.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


NAV = ('<header class="top"><a class="brand" href="../index.html">NBA <span>LINES LAB</span></a>'
       '<nav aria-label="Verified section">'
       '<a href="index.html">Verified home</a><a href="schedule.html">Schedule</a>'
       '<a href="injuries.html">Injuries</a><a href="picks.html">Picks gate</a>'
       '<a href="strategy-gates.html">Strategy gates</a><a href="audit.html">Audit</a>'
       '<a href="flagged-review.html">Flagged for Review</a></nav></header>')


def page(title, eyebrow, intro, body, note=""):
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{e(title)} — every row links to an official source; unverified values are blank and flagged.">
  <title>{e(title)} — NBA Lines Lab</title>
  <link rel="stylesheet" href="../styles.css">
</head>
<body>
{NAV}
<main class="section">
  <p class="eyebrow">{e(eyebrow)}</p>
  <h1>{e(title)}</h1>
  <p class="intro">{e(intro)}</p>
  {('<p class="note">' + note + '</p>') if note else ''}
  {body}
</main>
<footer>NBA Lines Lab · verified section · Generated from data/verified/*.json · Not betting advice</footer>
</body>
</html>
"""


def write(name, text):
    (OUT / name).write_text(text, encoding="utf-8")


sched = j("schedule_2026-11-13_to_16.json")
inj = j("injuries_2026-11-13_0515PM.json")
picks = j("picks_gate_status.json")
gates = j("strategy_gates.json")
aud = j("audit_arena-23927d63.json")
flag = j("flagged.json")
INJ_PDF = inj["report"]["pdf_url"]
INJ_PAGE = inj["report"]["page_url"]
SCH = "https://www.nba.com/schedule"

# ---- schedule
rows = []
for g in sched["rows"]:
    rows.append([e(g["date"]), e(g["tip_et"] + " ET"), f'<b>{e(g["matchup"])}</b>', e(g["away"]), e(g["home"]),
                 e(f'{g["arena"]} · {g["city"]}'), e(g["game_id"]),
                 link(g["source_url"], "Schedule") + " · " + link(g["preview_url"], "Preview")])
write("schedule.html", page(
    "Schedule — 3-day window", "VERIFIED · OFFICIAL SCHEDULE",
    f'{sched["counts"]["total"]} games from {sched["window"]["start"]} to {sched["window"]["end"]} (today + 3 days). '
    "Times are ET as printed by NBA.com. Source: NBA Schedule page.",
    table(["Date", "Tip", "Matchup (away@home)", "Away", "Home", "Arena · city", "NBA game ID", "Source"], rows)))

# ---- injuries
prow = []
for r in inj["rows"]:
    prow.append([e(r["game_date"]), e(r["tip_et"] + " ET"), e(r["matchup"]), e(r["team"]), f'<b>{e(r["player"])}</b>',
                 e(r["status"]), e(r["reason"]) + (f' <span class="tag">note</span> {e(r["note"])}' if r.get("note") else ''),
                 '<span class="tag">blank · unverified</span>', link(r["source_url"], "PDF")])
srow = [[e(r["game_date"]), e(r["tip_et"] + " ET"), e(r["matchup"]), e(r["team"]), e(r["status"]), link(r["source_url"], "PDF")]
        for r in inj["team_status_rows"]]
urow = [[e(r["team"] or "not printed"), e(r["player"] or "—"), e(r["status"]), e(r["reason"] or "—"), e(r["why_unattributed"]),
         link(r["source_url"], "PDF")] for r in inj["unattributed_rows"]]
body = (f'<h2>A. Player rows with matchup printed ({len(inj["rows"])})</h2>'
        + table(["Date", "Tip", "Matchup", "Team", "Player", "Status", "Reason (as printed)", "Minutes impact", "Source"], prow)
        + f'<h2>B. Team status rows: NOT YET SUBMITTED ({len(inj["team_status_rows"])})</h2>'
        + table(["Date", "Tip", "Matchup", "Team", "Status", "Source"], srow)
        + f'<h2>C. Rows not attached to a game ({len(inj["unattributed_rows"])})</h2>'
          '<p class="sub">These rows have no matchup printed, so game attachment is not verified. They are listed here and not counted above.</p>'
        + table(["Team (as printed)", "Player", "Status", "Reason", "Why not attached", "Source"], urow))
write("injuries.html", page(
    "Injury report — 11/13/26 5:15 PM ET snapshot", "VERIFIED · OFFICIAL INJURY REPORT",
    "Rows are copied from the official PDF. Minutes impact is intentionally blank: no official minutes baseline was retrieved, "
    "so no rotation-minute value is stated. The PDF includes 19 rows for 11/14 games; reports after this snapshot are not included.",
    body,
    note=f'Snapshot: {e(inj["report"]["label"])}. Reporting rules: {link(INJ_PAGE, "NBA injury reporting page")}. '
         "Latest report listed on the page at check time: 5:15 PM ET for 11/13."))

# ---- picks gate
prk = []
for p in picks["rows"]:
    blk = "<ul>" + "".join(f"<li>{e(b)}</li>" for b in p["blockers"]) + "</ul>"
    tag = '<span class="tag">NO PICK</span>' if p["status"] == "NO PICK" else '<b>PICK</b>'
    prk.append([e(p["date"]), e(p["tip_et"] + " ET"), f'<b>{e(p["matchup"])}</b>', tag, blk, link(p["schedule_source"], "Schedule")])
write("picks.html", page(
    "Picks gate — 3-day window", "GATED · NO PICKS ISSUED",
    f'{picks["picks_issued"]} picks issued out of {picks["games"]} games. A pick requires a validated strategy, an originated line, and a timestamped price from a permitted source. None exists in this repository yet, so each game is blocked and the blockers are listed.',
    table(["Date", "Tip", "Matchup", "Status", "Blockers", "Source"], prk)))

# ---- strategy gates
grk = [[e(f["family"]), '<span class="tag">' + e(f["gate_status"]) + '</span>', e(f["evaluated_strategies"]),
        "<ul>" + "".join(f"<li>{e(b)}</li>" for b in f["blockers"]) + "</ul>", link(f["source_url"], "Reference")]
       for f in gates["families"]]
write("strategy-gates.html", page(
    "Strategy families and validation gates", "GATES · NOT EVALUATED",
    "No strategy family has been evaluated against historical results or timestamped prices, so none has passed a gate. "
    "The reference links are for definitions only; no value was taken from them.",
    table(["Family", "Gate status", "Strategies evaluated", "Blockers", "Reference"], grk),
    note=f'{e(gates["gate_reference"])}'))

# ---- audit
ark = []
for f in aud["findings"]:
    src = link(f["source_url"], "Official check") if f.get("source_url") else "—"
    if f.get("non_official_source_cited"):
        src += f' · cited (non-official): <a href="{e(f["non_official_source_cited"])}" rel="noopener">{e(f["non_official_source_cited"].split("/")[2])}</a>'
    ark.append([e(f["id"]), e(f["file"]), e(f["record"]), e(f["claim"]), e(f["official"]), f'<b>{e(f["result"])}</b>', src])
write("audit.html", page(
    "Audit of PR #3 data (arena/23927d63-nba2)", "AUDIT · OTHER SESSION'S DATA",
    f'{len(aud["findings"])} findings from checking {aud["audited_files"][0]}, {aud["audited_files"][1]} and {aud["audited_files"][2]} against official sources. '
    "Nothing in that branch was edited; the findings are for its owner to resolve.",
    table(["ID", "File", "Record", "Claim in PR #3", "Official check", "Result", "Source"], ark),
    note=f'Audited commit {e(aud["audited_commit"][:12])}. Policy: "{e(aud["policy"])}"'))

# ---- flagged
frk = [[e(f["id"]), e(f["category"]), e(f["item"]), e(f["why"]), e(f["action"]), link(f["source_url"], f["source_label"]), f'<span class="tag">{e(f["status"])}</span>']
       for f in flag["rows"]]
write("flagged-review.html", page(
    "Flagged for Review", "OPEN ITEMS · NOT VERIFIED",
    "Flagged items do not block the merge. They are listed for owner review. Each links to the source that was checked.",
    table(["ID", "Category", "Item", "Why it matters", "Action", "Source", "Status"], frk)))

# ---- index
cards = [
    ("Games in 3-day window", f'{sched["counts"]["total"]}', "Official schedule rows, 11/13–11/16"),
    ("Injury player rows (matchup printed)", f'{len(inj["rows"])}', "11/13 5:15 PM ET PDF; plus 11/14 rows already submitted"),
    ("Rows not attached to a game", f'{len(inj["unattributed_rows"])}', "Listed, not counted as verified attachments"),
    ("Picks issued", f'{picks["picks_issued"]}', "Gate requires a validated strategy and a permitted price"),
    ("Audit findings on PR #3 data", f'{len(aud["findings"])}', "Mismatches, unsupported values, and data-rights note"),
    ("Flagged for review", f'{len(flag["rows"])}', "Open owner decisions and unverified items"),
]
cardhtml = "".join(f'<article class="card"><strong>{e(a)}</strong><p><span style="font-size:24px;font-weight:800">{e(b)}</span><br>{e(c)}</p></article>' for a, b, c in cards)
links = [
    ("schedule.html", "Schedule — 3-day window", "31 official games with game IDs, tip times and source links."),
    ("injuries.html", "Injury report — 11/13 5:15 PM ET", "Official rows with the matchup printed; unattributed rows listed separately; minutes blank."),
    ("picks.html", "Picks gate", "No picks issued; each game lists its blockers."),
    ("strategy-gates.html", "Strategy gates", "Four families, all not evaluated, with blockers."),
    ("audit.html", "Audit of PR #3 data", "Mismatches and unsupported values in another session's branch."),
    ("flagged-review.html", "Flagged for Review", "Owner decisions, legal review and unverified items."),
]
linkhtml = "".join(f'<article class="card"><strong><a href="{h}">{e(t)}</a></strong><p>{e(d)}</p></article>' for h, t, d in links)
index_body = (f'<section class="cards">{cardhtml}</section>'
              f'<h2>Pages</h2><section class="cards">{linkhtml}</section>'
              '<p class="note"><b>Method:</b> values were copied from official NBA pages and PDFs and checked by '
              '<code>tools/verify_data.py</code> (official-domain source on every row, team-to-matchup consistency, declared counts, '
              'no broken local links). Anything the checks cannot confirm is blank and flagged.</p>'
              '<p class="sub">Responsible play: if gambling is causing you harm, the Dutch self-exclusion register is '
              '<a href="https://gokstop.nl/" rel="noopener">Gokstop ↗</a>.</p>')
write("index.html", page(
    "Verified data — overview", "VERIFIED SECTION · OFFICIAL SOURCES ONLY",
    "Source-linked tables for the 3-day window (11/13–11/16/2026): schedule, injury snapshot, pick gate, strategy gates, an audit of another branch, and flagged items.",
    index_body))
print("pages written:", sorted(p.name for p in OUT.glob("*.html")))
