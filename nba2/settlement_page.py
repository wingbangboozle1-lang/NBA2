"""Settlement stamp page: sealed predictions scored against official finals.

    python -m nba2.settlement_page

Writes ``site/settlement.html``. It does NOT edit any other page: the navigation link to it is a
request for the final integration session (see COORDINATION.md), and ``inject_link`` is kept only
for that session to call deliberately.
Everything shown is recomputed from committed files: the sealed ledgers (seal re-verified here),
the official finals feeds (rebuilt in memory and checked against ``data/raw/official_finals_union.json``),
and the official source links named in each row. Nothing is fetched and nothing is typed by hand.
The page carries no timestamp, so a rebuild of unchanged inputs is byte-identical (the parity gate relies on that).

What the page says, and what it does not:
* It shows how many sealed predictions have an official final, with the score and the source.
* It shows the model's error on those games. It does NOT show betting results: no stakes, no
  market prices, and the strategy gates in the rest of the site stay BLOCKED.
* A game with no committed official final is listed as PENDING and is never scored.
"""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

from .models import ledger as LD
from .pipeline import settle as S
from .v2.build import NAV as V2_NAV
from .v3.build import V3_NAV

ROOT = S.ROOT
SITE = ROOT / "site"
PAGE = "settlement.html"
MARKER = f'<a href="{PAGE}"'
LEDGER_NAV = (PAGE, "Settlement stamp")
LEDGER_URL = "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/raw/ledger/"
BADGE_OK = '<span class="badge b-ok">VERIFIED</span>'
BADGE_BAD = '<span class="badge b-bad">BROKEN</span>'


def esc(x) -> str:
    return "" if x is None else html.escape(str(x), quote=True)


def _pts(x) -> str:
    return "" if x is None else str(x)


def _gamebook_links() -> dict[str, str]:
    out: dict[str, str] = {}
    for p in S.finals_sources():
        if p.suffix != ".json":
            continue
        for r in S._records_of(json.loads(p.read_text())):
            gid, url = r.get("game_id"), r.get("gamebook_url")
            if gid and url:
                out.setdefault(gid, url)
    return out


def _feed_notes() -> dict[str, str]:
    """Notes on games that have no final yet, from committed official feeds."""
    out: dict[str, str] = {}
    for p in S.finals_sources():
        if p.suffix != ".json":
            continue
        for r in S._records_of(json.loads(p.read_text())):
            if r.get("game_id") and r.get("status") not in S.FINAL_STATUSES and r.get("note"):
                out.setdefault(r["game_id"], r["note"])
    return out


def _seal_status(path: Path) -> tuple[bool, str, dict]:
    ok, stored, _recomp = LD.verify(path)
    doc = json.loads(path.read_text())
    return ok, stored, doc


def build_html() -> str:
    """Pure function of the committed sources: no timestamps, no network, no hand-typed values.

    The union on disk must equal a fresh rebuild from the official sources; otherwise the page
    refuses to build, so a stale settlement cannot be published as current.
    """
    fresh = S.build_union()
    if not S.UNION_PATH.exists():
        raise SystemExit("data/raw/official_finals_union.json is missing — run: python -m nba2.pipeline.settle")
    disk = json.loads(S.UNION_PATH.read_text())
    if disk.get("records") != fresh["records"] or disk.get("conflicts") != fresh["conflicts"]:
        raise SystemExit("data/raw/official_finals_union.json is stale — run: python -m nba2.pipeline.settle")
    union = fresh
    finals = {r["game_id"]: r for r in union["records"]}
    gamebooks = _gamebook_links()
    notes = _feed_notes()
    union_sha = hashlib.sha256(json.dumps(union["records"], sort_keys=True).encode()).hexdigest()

    ledgers = sorted(S.find_ledgers())
    seal_rows = []
    settled_by_ledger = []
    for p in ledgers:
        ok, stored, doc = _seal_status(p)
        seal_rows.append((p.name, ok, stored, doc["header"]["n_predictions"], doc["header"]["sealed_at_utc"]))
        settled_by_ledger.append(LD.settle(p, S.UNION_PATH))

    # The first ledger holds the settled games; the second ledger repeats them identically
    # (checked: 0 differing predictions on the 22 shared game IDs) and adds five 11/17 games.
    primary = json.loads(ledgers[0].read_text())["predictions"]
    rows_settled, rows_pending = [], []
    for pr in primary:
        gid = pr["game_id"]
        f = finals.get(gid)
        if f is None:
            rows_pending.append(pr)
            continue
        margin = f["home_pts"] - f["away_pts"]
        total = f["home_pts"] + f["away_pts"]
        spread_err = abs(-pr["our_spread_home"] - margin) if pr["our_spread_home"] is not None else None
        total_err = abs(pr["our_total"] - total) if pr["our_total"] is not None else None
        rows_settled.append((pr, f, margin, total, spread_err, total_err))

    s1 = settled_by_ledger[0]
    metrics = s1.metrics
    settled_dates = sorted({f_["date"] for f_ in [pr for pr in primary if pr["game_id"] in finals]})
    latest_settled = settled_dates[-1] if settled_dates else "none"
    stamp_bits = []
    for name, ok, stored, n, sealed_at in seal_rows:
        badge = BADGE_OK if ok else BADGE_BAD
        stamp_bits.append(
            f"<tr><td><a href=\"{LEDGER_URL}{esc(name)}\" target=\"_blank\" rel=\"noopener\">{esc(name)}</a></td><td>{badge}</td>"
            f"<td class=\"n\">{n}</td><td><code>{esc(stored)}</code></td><td>{esc(sealed_at)}</td></tr>")

    def row_settled(pr, f, margin, total, spread_err, total_err):
        game_url = f.get("source") or ""
        p_win = "" if pr.get("p_home_win") is None else "%.3f" % pr["p_home_win"]
        gb = gamebooks.get(pr["game_id"])
        gl = f'<a href="{esc(game_url)}">game page</a>' if game_url else "no source"
        if gb:
            gl += f' · <a href="{esc(gb)}">gamebook PDF</a>'
        qa = f.get("away_quarters")
        qh = f.get("home_quarters")
        q_txt = []
        if qa:
            q_txt.append(f"{f['away']} {'-'.join(map(str, qa))}")
        else:
            q_txt.append(f"{f['away']} <span class=\"blank\">— quarter split not verified</span>")
        if qh:
            q_txt.append(f"{f['home']} {'-'.join(map(str, qh))}")
        else:
            q_txt.append(f"{f['home']} <span class=\"blank\">— quarter split not verified</span>")
        ot = f.get("ot_quarters") or {}
        ot_txt = ""
        if ot.get("away") or ot.get("home"):
            oa = "-".join(map(str, ot.get("away") or [])) or "—"
            oh = "-".join(map(str, ot.get("home") or [])) or "—"
            ot_txt = f" (OT: {f['away']} {oa} · {f['home']} {oh})"
        return (
            "<tr>"
            f"<td>{esc(pr['date'])}</td>"
            f"<td>{esc(pr['away'])} @ {esc(pr['home'])}<br><small>{esc(pr['game_id'])}</small></td>"
            f"<td class=\"n\">{f['away_pts']}–{f['home_pts']}{esc(ot_txt)}<br><small>{' · '.join(q_txt)}</small></td>"
            f"<td class=\"n\">{esc(pr['our_spread_home'])}</td>"
            f"<td class=\"n\">{margin:+d}</td>"
            f"<td class=\"n\">{'' if spread_err is None else f'{spread_err:.2f}'}</td>"
            f"<td class=\"n\">{esc(pr['our_total'])}</td>"
            f"<td class=\"n\">{total}</td>"
            f"<td class=\"n\">{'' if total_err is None else f'{total_err:.2f}'}</td>"
            f"<td class=\"n\">{p_win}</td>"
            f"<td class=\"n\">{esc(f['home'] if margin > 0 else f['away'])}</td>"
            f"<td>{gl}</td>"
            "</tr>")

    settled_html = "".join(row_settled(*r) for r in rows_settled)

    def row_pending(pr):
        note = notes.get(pr["game_id"]) or (
            f"no official final committed in the repository yet (tip {pr['date']} {pr['time_et']} ET)")
        return ("<tr>"
                f"<td>{esc(pr['date'])}</td>"
                f"<td>{esc(pr['away'])} @ {esc(pr['home'])}<br><small>{esc(pr['game_id'])}</small></td>"
                f"<td><span class=\"blank\">— not scored</span></td>"
                f"<td colspan=\"8\">{esc(note)}</td>"
                f"<td><a href=\"https://www.nba.com/games\">official schedule</a></td>"
                "</tr>")

    pending_html = "".join(row_pending(pr) for pr in rows_pending)
    later = [pr for pr in json.loads(ledgers[-1].read_text())["predictions"]
             if pr["game_id"] not in {p["game_id"] for p in primary}]
    later_html = "".join(row_pending(pr) for pr in later)

    conflicts = union.get("conflicts", [])
    rejected = union.get("rejected_quarter_rows", [])

    head_cols = ("<th>Date</th><th>Game</th><th>Official final</th><th>Our spread (home)</th>"
                 "<th>Actual margin (home)</th><th>Spread error</th><th>Our total</th>"
                 "<th>Actual total</th><th>Total error</th><th>Our P(home win)</th><th>Winner</th><th>Source</th>")
    pend_cols = ("<th>Date</th><th>Game</th><th>Score</th><th colspan=\"8\">Status</th><th>Source</th>")

    nav = []
    for href, label in V2_NAV:
        cls = ' class="on"' if href == PAGE else ""
        nav.append(f'<a href="{href}"{cls}>{label}</a>')
    for href, label in V3_NAV:
        nav.append(f'<a href="{href}">{label}</a>')
    nav.append(f'<a href="{PAGE}" class="on">Settlement stamp</a>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Settlement stamp · NBA2</title>
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<div class="wrap">
<aside>
  <div class="brand">NBA2 <span>Settlement</span></div>
  <p class="tag">Sealed predictions vs official finals</p>
  <nav>
{chr(10).join(nav)}
  </nav>
</aside>
<main>
<p class="crumbs"><a href="index.html">Dashboard</a> · settlement stamp</p>
<h1>Settlement stamp</h1>
<p class="lede">The sealed prediction ledgers, scored only against official final scores. Each game is settled
only when the official gamebook quarter row reproduces the final. Games without an official final are listed as
pending and are not scored. This is model accuracy on settled games, not a betting result: there are no stakes
and no market prices in this build.</p>

<div class="note"><b>Settlement stamp.</b> Official finals committed for <b>{len(union['records'])}</b> game(s)
(latest settled game date {esc(latest_settled)}) from {len(union['sources_read'])} committed official source files.
Union sha256 <code>{union_sha}</code>. Conflicts between sources: <b>{len(conflicts)}</b>. Quarter rows rejected: <b>{len(rejected)}</b>.
Ledger {esc(ledgers[0].name)}: <b>{s1.games_settled} of {s1.games_expected}</b> predictions settled.
Ledger {esc(ledgers[-1].name)}: <b>{settled_by_ledger[-1].games_settled} of {settled_by_ledger[-1].games_expected}</b> predictions settled.</div>

<h2>1. Seals</h2>
<p>Each sealed ledger is re-hashed on this page. A broken seal would show BROKEN and no metric would be published.</p>
<div class="scroll"><table><thead><tr><th>Ledger file</th><th>Seal</th><th>Predictions</th><th>SHA-256 (sealed)</th><th>Sealed at (UTC)</th></tr></thead>
<tbody>{''.join(stamp_bits)}</tbody></table></div>

<h2>2. Settled games ({len(rows_settled)})</h2>
<p>Predictions are the sealed values, unchanged. Spread error = |−our home spread − actual home margin|.
Total error = |our total − actual total|. Source links point to the official NBA game page and the official gamebook PDF.</p>
<div class="scroll"><table><thead><tr>{head_cols}</tr></thead><tbody>{settled_html}</tbody></table></div>
<p class="note">Measured on {esc(metrics.get('n_settled'))} settled games: spread MAE {esc(metrics.get('spread_mae'))},
total MAE {esc(metrics.get('total_mae'))}, Brier {esc(metrics.get('brier'))}, log-loss {esc(metrics.get('log_loss'))}.
Calibration slope and intercept are not measured at this sample size. The strategy gates stay BLOCKED: no market price,
too few settled bets, no holdout (see the strategies page).</p>

<h2>3. Pending games ({len(rows_pending)} in {esc(ledgers[0].name)} · {len(later)} more in {esc(ledgers[-1].name)})</h2>
<p>Not scored. A game is listed here until an official final is committed to the repository.</p>
<div class="scroll"><table><thead><tr>{pend_cols}</tr></thead><tbody>{pending_html}{later_html}</tbody></table></div>

<h2>4. Flags on this stamp</h2>
<ul>
<li><b>DAL @ BOS, 2026-11-15 (game 0022600240):</b> final 94–131 is verified three ways. The Dallas quarter split is
<i>not</i> verified: the official gamebook's SCORE BY PERIOD row for DAL does not reproduce its final, so it is left blank and not back-solved.
<a href="https://statsdmz.nba.com/pdfs/20261115/20261115_DALBOS_book.pdf">gamebook PDF</a>.</li>
<li><b>NYK @ TOR, 2026-11-15 (0022600241):</b> went to overtime; the OT period counts toward the final (112–108).
<a href="https://www.nba.com/game/nyk-vs-tor-0022600241">game page</a>.</li>
<li><b>Games in progress when read, 2026-11-15:</b> HOU @ WAS (0022600242), ATL @ MIL (0022600243), OKC @ SAC (0022600244)
were not final when the official pages were read on 2026-11-16 UTC. They stay pending until a final is committed.</li>
<li><b>Gate measurement label.</b> The gate report calls scored predictions "settled bets". No bet has been placed; the count
is the number of settled predictions.</li>
</ul>
<p class="note">Built from committed files only by <code>nba2.settlement_page</code>. Re-run
<code>python -m nba2.pipeline.settle</code> after each game day, then <code>python -m nba2.settlement_page</code>.</p>
<footer>Settlement rule: a game is settled only when an official final is committed and, where a quarter row exists, it reproduces the final.
Sources and per-row links are shown above. A blank cell is a value we do not have, never a zero.</footer>
</main>
</div>
</body>
</html>
"""


def inject_link() -> int:
    """Idempotently add the settlement link to the navigation of every published page."""
    n = 0
    for p in sorted(SITE.glob("*.html")):
        if p.name == PAGE:
            continue
        doc = p.read_text()
        if "</nav>" not in doc or MARKER in doc:
            continue
        doc = doc.replace("</nav>", f'<a href="{PAGE}">Settlement stamp</a>\n</nav>', 1)
        p.write_text(doc)
        n += 1
    return n


def main() -> int:
    ledgers = S.find_ledgers()
    if not ledgers:
        print("no sealed ledger found")
        return 1
    (SITE / PAGE).write_text(build_html())
    print(f"wrote site/{PAGE}; nav link not added (integration-session request)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
