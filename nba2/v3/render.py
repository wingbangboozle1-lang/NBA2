"""v3 page renderer.

One rule, enforced by construction: a page belongs to exactly one surface, and the surface is a
field on the page record. ``build_pages`` renders a page only after checking its declared surface
against the registry in ``build.SURFACES``, so a bet-page table cannot be pasted onto a
projection page without the check failing.

Every number is passed in from a module that computed it. Nothing here invents a value, and a
missing value renders as a dash with the reason string attached rather than as a zero.
"""

from __future__ import annotations

import html
import re

# --------------------------------------------------------------------------- primitives
CSS = """
:root{
  --bg:#0b0f16; --panel:#111823; --panel2:#161f2c; --line:#22303f;
  --ink:#e8eef6; --muted:#93a3b8; --accent:#4cc9a4; --accent2:#7aa7ff;
  --warn:#f2b544; --bad:#f0776c; --good:#5fd08a; --dim:#0f1620;
  --proj:#4cc9a4; --bet:#f2b544;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{display:flex;min-height:100vh;align-items:flex-start}
aside{width:250px;flex:0 0 250px;background:var(--panel);border-right:1px solid var(--line);
 padding:18px 14px;position:sticky;top:0;height:100vh;overflow-y:auto}
.brand{font-size:19px;font-weight:700;letter-spacing:.2px}
.brand span{color:var(--accent);font-weight:600}
.tag{color:var(--muted);font-size:12px;margin:4px 0 14px}
aside nav{display:flex;flex-direction:column;gap:1px}
aside nav a{display:block;padding:6px 9px;border-radius:6px;color:#c8d5e4;text-decoration:none;font-size:13.5px}
aside nav a:hover{background:var(--panel2);color:#fff}
aside nav a.on{background:#1b2a3a;color:#fff;box-shadow:inset 3px 0 0 var(--accent)}
.navgrp{margin:12px 0 3px;padding:0 9px;font-size:10.5px;letter-spacing:.11em;
 text-transform:uppercase;color:#6f8096;font-weight:700}
.navgrp.proj{color:var(--proj)}
.navgrp.bet{color:var(--bet)}
main{flex:1;min-width:0;padding:26px 30px 60px;max-width:1500px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.2px}
.sub{color:var(--muted);margin:0 0 22px;font-size:14px}
h2{font-size:18px;margin:30px 0 8px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:15px;margin:20px 0 6px}
p{margin:9px 0}
a{color:var(--accent2)}
code{background:var(--dim);padding:1px 5px;border-radius:4px;font-size:12.5px;
 font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.scroll{overflow-x:auto;margin:12px 0 18px;border:1px solid var(--line);border-radius:9px}
table{border-collapse:collapse;width:100%;font-size:13px;background:var(--panel)}
caption{caption-side:top;text-align:left;padding:9px 12px;color:var(--muted);font-size:12.5px;
 border-bottom:1px solid var(--line);background:var(--panel2)}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--panel2);font-size:11px;letter-spacing:.05em;text-transform:uppercase;
 color:#a9b8ca;font-weight:700;position:sticky;top:0}
tbody tr:hover{background:#141d29}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.badge{display:inline-block;padding:1px 7px;border-radius:99px;font-size:10.5px;font-weight:700;
 letter-spacing:.04em;text-transform:uppercase;white-space:nowrap}
.b-ok{background:#123526;color:#6fe0a5;border:1px solid #1d5c3f}
.b-bad{background:#3a1a1a;color:#ff8f83;border:1px solid #6b2b26}
.b-warn{background:#3a2f14;color:#f5c563;border:1px solid #6b5520}
.b-off{background:#1a2431;color:#9aabbd;border:1px solid #2b3a4c}
.b-info{background:#152a3d;color:#87c0ff;border:1px solid #234a6b}
.b-proj{background:#10322a;color:#5fe0b0;border:1px solid #1d5c47}
.b-bet{background:#3a2f14;color:#f5c563;border:1px solid #6b5520}
.blank{color:#7b8b9e;font-style:italic;font-size:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
.card.proj{border-left:3px solid var(--proj)}
.card.bet{border-left:3px solid var(--bet)}
.card.bad{border-left:3px solid var(--bad)}
.card.warn{border-left:3px solid var(--warn)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:14px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:13px 15px}
.kpi .l{color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.06em}
.kpi .v{font-size:23px;font-weight:700;margin-top:3px;font-variant-numeric:tabular-nums}
.kpi .n{color:var(--muted);font-size:12px;margin-top:2px}
.kpi.bad .v{color:var(--bad)} .kpi.ok .v{color:var(--good)} .kpi.warn .v{color:var(--warn)}
.note{color:var(--muted);font-size:12.5px;margin:8px 0}
.lede{font-size:15.5px;color:#cfdcea}
footer{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:12.5px}
footer a{color:var(--accent2)}
ul,ol{margin:8px 0;padding-left:22px}
li{margin:4px 0}
@media (max-width:900px){
  .wrap{flex-direction:column}
  aside{width:100%;flex:none;height:auto;position:static;border-right:0;border-bottom:1px solid var(--line)}
  aside nav{flex-direction:row;flex-wrap:wrap;gap:4px}
  .navgrp{width:100%;margin:8px 0 2px}
  main{padding:18px 16px 50px}
}
"""


def esc(x):
    if x is None:
        return ""
    return html.escape(str(x), quote=True)


def dash(reason):
    """A blank cell that carries its reason. Never render a 0 for an unknown."""
    return f'<span class="blank" title="{esc(reason)}">{esc(reason)}</span>'


def badge(text, kind="info"):
    return f'<span class="badge b-{kind}">{esc(text)}</span>'


def badge_status(v):
    v_up = (v or "").upper()
    if v_up.startswith("PASS"):
        return badge(v, "ok")
    if v_up.startswith("FAIL"):
        return badge(v, "bad")
    if "NOT MEASURABLE" in v_up or "NOT MEASURED" in v_up or "WITHHELD" in v_up or "BLOCKED" in v_up:
        return badge(v, "warn")
    if "MEASURED" in v_up or "PER STRATEGY" in v_up:
        return badge(v, "info")
    return badge(v, "off")


def badge_surface(surface):
    return badge(surface, "proj" if surface == "projection" else "bet")


def badge_grade(g):
    return badge(g, {"A": "ok", "B": "info", "C": "warn"}.get((g or "").upper(), "off"))


def src(url, label=None):
    if not url:
        return dash("no source")
    label = label or re.sub(r"^https?://(www\.)?", "", url)
    label = label if len(label) <= 52 else label[:49] + "…"
    return f'<a href="{esc(url)}" rel="noopener" target="_blank">{esc(label)}</a>'


def table(headers, rows, caption, num_cols=(), idcol=None):
    out = ['<div class="scroll"><table>', f"<caption>{esc(caption)}</caption>",
           "<thead><tr>"]
    for i, h in enumerate(headers):
        cls = ' class="n"' if i in num_cols else ""
        out.append(f'<th scope="col"{cls}>{esc(h)}</th>')
    out.append("</tr></thead><tbody>")
    for r in rows:
        rid = ""
        if idcol is not None and isinstance(r, dict) and r.get(idcol):
            rid = f' id="{esc(r[idcol])}"'
        cells = r["cells"] if isinstance(r, dict) else r
        out.append(f"<tr{rid}>")
        for i, c in enumerate(cells):
            cls = ' class="n"' if i in num_cols else ""
            out.append(f"<td{cls}>{c}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def kpi(label, value, note="", kind=""):
    k = f" {kind}" if kind else ""
    return (f'<div class="kpi{k}"><div class="l">{esc(label)}</div>'
            f'<div class="v">{value}</div>'
            f'<div class="n">{esc(note)}</div></div>')


def kpis(items):
    return '<div class="grid">' + "\n".join(kpi(*it) for it in items) + "</div>"


def page(title, body, nav_html, active, top_note):
    """Assemble a document. ``nav_html`` comes from the caller so the grouping stays in one place."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · NBA2 v3</title>
<meta name="description" content="NBA2 v3 — two independent estimators, disagreement as the confidence signal, projection and bet surfaces kept apart.">
<link rel="stylesheet" href="assets/v3.css">
</head>
<body>
<div class="wrap">
<aside>
  <div class="brand">NBA2 <span>v3</span></div>
  <p class="tag">disagreement is the confidence signal</p>
  <nav>
{nav_html}
  </nav>
</aside>
<main>
{top_note}
{body}
<footer>
  <p>Snapshot as of <b>{esc(__import__("nba2.v3.official", fromlist=["AS_OF"]).AS_OF)}</b>,
  retrieved <code>{esc(__import__("nba2.v3.official", fromlist=["RETRIEVED_UTC"]).RETRIEVED_UTC)}</code>.
  Built by session <code>arena/a1fddb57-nba2</code>.
  Every table row links to the official page it came from; a blank cell is a missing measurement,
  never a zero.</p>
  <p>This site publishes projections, not betting advice. No market price is connected, so no pick
  on the bet surface carries a stake: every stake there is <b>0</b> by gate, not by judgement.</p>
  <p><a href="v3-flagged.html">Flagged for review</a> ·
     <a href="v3-methodology.html">Methodology &amp; formulas</a> ·
     <a href="v3-injuries.html">Injury archive</a> ·
     <a href="index.html">v2 site</a> ·
     <a href="https://github.com/wingbangboozle1-lang/NBA2">Repository</a></p>
</footer>
</main>
</div>
</body>
</html>
"""


def note(text, kind=""):
    k = f" {kind}" if kind else ""
    return f'<div class="card{k}">{text}</div>'


def surface_banner(surface, surfaces):
    name, desc = surfaces[surface]
    cls = "proj" if surface == "projection" else "bet"
    return (f'<div class="card {cls}"><b>{esc(name)} surface.</b> {esc(desc)} '
            f'{badge_surface(surface)}</div>')
