"""v7 render: the originated slate, the strategy lab, and the skill measurement, as pages.

Pages written (all into the published ``site/`` tree):

    v7-slate.html          every game in the 3-day window: both estimators, their
                           disagreement, our spread and total, rest, availability, verdict
    v7-strategies.html     ten strategies x ten gates, pre-registration hashes, and the
                           parlay table with the measured rho next to the naive product
    v7-skill.html          the walk-forward measurement, the luck z-scores, the corroboration
                           of the transcribed page against the results, and the props block
    v7-methodology.html    every constant, the source of every input, and the clock caveat
    v7-verify.html         the gates over this layer, with what each one measured

Every row carries a source link. A blank carries a reason. Nothing on these pages is
fetched at render time: the inputs are the committed JSON under ``data/v7``.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from . import official as O
from . import strategies as S
from .common import ROOT, SITE, V7, dump, esc, load

PAGES = {
    "v7-slate.html": "Originated slate (3 days)",
    "v7-strategies.html": "Strategy lab & parlays",
    "v7-skill.html": "Measured skill & luck",
    "v7-methodology.html": "v7 methodology",
    "v7-verify.html": "v7 verification",
}


# ------------------------------------------------------------------ shell
def _nav() -> list[tuple[str, str]]:
    """Reuse the nav v2..v6 already wrote, minus this layer's own pages."""
    for name in ("index.html", "picks.html", "sources.html"):
        p = SITE / name
        if not p.exists():
            continue
        m = re.search(r"<nav>(.*?)</nav>", p.read_text(), re.S)
        if not m:
            continue
        out = []
        for href, label in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', m.group(1), re.S):
            if href in PAGES:
                continue
            out.append((href, label))
        if out:
            return out
    return []


def page(title: str, active: str, body: str, lede: str = "") -> str:
    def _a(href: str, label: str) -> str:
        cls = ' class="on"' if href == active else ""
        return f'<a href="{esc(href)}"{cls}>{label}</a>'
    nav = "".join(_a(h, l) for h, l in _nav())
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · NBA2 Lines Lab v7</title>
<link rel="stylesheet" href="assets/site.css"></head>
<body><div class="wrap">
<aside><div class="brand">NBA2 <span>Lines Lab</span></div>
<p class="tag">v7 · originated from the 2026-11-19 official snapshot</p>
<nav>{nav}</nav>
</aside>
<main>
<div class="crumbs"><a href="index.html">Dashboard</a> / {esc(title)}</div>
<h1>{esc(title)}</h1>
{f'<p class="lede">{lede}</p>' if lede else ''}
{body}
</main></div></body></html>
"""


def tbl(head: list[str], rows: list[list[str]], cls: str = "") -> str:
    h = "".join(f"<th>{x}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="scroll"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def blank(why: str) -> str:
    return f'<span class="blank">— {esc(why)}</span>'


def src(url: str, label: str = "SRC") -> str:
    if not url:
        return blank("no official source")
    return f'<a href="{esc(url)}" rel="noopener" target="_blank">{esc(label)}</a>'


def n(v, nd=2, why="not measured"):
    if v is None:
        return blank(why)
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return esc(v)


def kpi(label: str, value: str, sub: str = "") -> str:
    tail = '<div class="ks">' + esc(sub) + "</div>" if sub else ""
    return (f'<div class="kpi"><div class="kl">{esc(label)}</div>'
            f'<div class="kv">{value}</div>{tail}</div>')


# ------------------------------------------------------------------ slate page
def page_slate(res: dict, slate: dict) -> str:
    w = slate["window"]
    rows = []
    for g in slate["rows"]:
        dis = g["disagreement_pts"]
        _r = res["cut"].ratings
        ratings_src = (f'https://www.nba.com/game/{g["away"].lower()}-vs-'
                       f'{g["home"].lower()}-0022600{g["game_id"][-3:]}'
                       if False else g["source_url"])
        adv = (res["teams"].get(g["away"], {}).get("stats_url") or O.SOURCES["advanced"])
        dis_cell = (f'<b>{n(dis, 2)}</b>' if dis is not None else blank("unmeasured"))
        rows.append([
            esc(g["date"]), esc(g["tip_et"] or ""),
            f'<a href="{esc(g["source_url"])}" target="_blank" rel="noopener">'
            f'{esc(g["away"])} @ {esc(g["home"])}</a>',
            f'{n(g["e1_margin_home"], 1)}',
            f'{n(g["e2_margin_home"], 1)}',
            dis_cell,
            f'{n(g["spread_home"], 1)}',
            f'{n(g["total"], 1)}',
            n(g["p_home"], 3),
            esc(g["lean"] or ""),
            _rest(g["rest"]),
            _avail(g["availability"]),
            _luck(g["luck_gate"]),
            '<span class="badge b-off">0.00 u</span>',
            src(g["source_url"], "game"),
            src(adv, "team stats"),
        ])
    body = f"""
<p class="note"><b>The window rule.</b> Every game on the official schedule up to three days ahead of the snapshot date is priced (2026-11-19 + 3 = 2026-11-21); no game beyond that window is published, and no game inside it is skipped.</p>
<div class="cards">{kpi("Games in window", str(w["n_games"]), f'{w["start"]} → {w["end"]}')}
{kpi("Days ahead", str(w["max_days_ahead"]), "the brief's maximum")}
{kpi("Staked", "0.00 u", "every strategy is gated shut")}
{kpi("Headline", "disagreement", "not the blend")}</div>

<h2>Every game, both estimators, and the disagreement</h2>
<p><b>Read the two margins first.</b> E1 is the opponent-adjusted rating solved from official
finals (a margin, in points). E2 is the unadjusted points-per-game differential. They answer
different questions, and the number between them — <b>disagreement</b> — is the confidence
signal this page is built around: a large gap means the two views of the same clubs do not
agree, and a bet that leans on the blend alone is leaning on an average of a disagreement
nobody resolved. The blend is not shown as a headline anywhere on this site.</p>
{tbl(["Date", "Tip (ET)", "Game", "E1 margin<br>(adj.)", "E2 margin<br>(unadj.)",
      "<b>Disagree</b>", "Our spread<br>(home)", "Our total", "P(home win)", "Lean",
      "Rest (a / h)", "Availability", "Luck gate", "Stake", "Source<br>(game)",
      "Source<br>(team stats)"], rows)}
<p class="note">Totals are <code>possessions × points-per-possession</code>, from the official
PACE, OffRtg and DefRtg columns — not an average of two scoring averages. The availability
column is published <b>empty and flagged</b>: no official injury report for these dates was
read in this build, so there is nothing honest to put in it. The stake column is 0.00 on
every row for the reason printed on <a href="v7-strategies.html">Strategy lab</a>.</p>

<h2>What each row's source is</h2>
<p>Clubs, dates, tips and game ids: <a href="{esc(O.SOURCES['games'].format(date='2026-11-19'))}"
target="_blank" rel="noopener">nba.com/games</a> for each date. Ratings: the committed
official finals captures (linked per game above). Pace, OffRtg and DefRtg: the
<a href="{esc(O.SOURCES['advanced'])}" target="_blank" rel="noopener">advanced team page</a>.
Points and opponent points: the
<a href="{esc(O.SOURCES['traditional'])}" target="_blank" rel="noopener">traditional</a> and
<a href="{esc(O.SOURCES['opponent'])}" target="_blank" rel="noopener">opponent</a> pages.
Standings: <a href="{esc(O.SOURCES['standings'])}" target="_blank" rel="noopener">nba.com/standings</a>.</p>
"""
    return body


def _rest(rest: dict) -> str:
    a, h = rest["away"], rest["home"]
    def one(x):
        if x["rest_days"] is None:
            return blank(x["flag"] or "no prior game")
        flags = []
        if x["back_to_back"]:
            flags.append("B2B")
        if x["three_in_four"]:
            flags.append("3-in-4")
        return f'{x["rest_days"]}d' + (f' <span class="badge b-warn">{"/".join(flags)}</span>' if flags else "")
    return f"{one(a)} / {one(h)}"


def _avail(av: dict) -> str:
    if av["status"] == "BLANK":
        return blank("no official injury report was read for this date (F-V7-AVAIL)")
    return esc(av["status"])


def _luck(lg: dict) -> str:
    if lg.get("blocks"):
        return f'<span class="badge b-bad">out of band: {esc(", ".join(lg["outside_band"]))}</span>'
    return '<span class="badge b-ok">both inside band</span>'


# ------------------------------------------------------------------ strategy page
def page_strategies(st: dict, slate: dict, res: dict) -> str:
    gates = st["gates"]
    grows = []
    for g in gates:
        kind = "b-ok" if g["status"] == "PASS" else "b-bad"
        grows.append([esc(g["id"]), esc(g["gate"]), esc(str(g["threshold"])),
                      esc(g["detail"]), f'<span class="badge {kind}">{esc(g["status"])}</span>',
                      src(O.SOURCES["advanced"] if g["id"] in ("G-V7-1", "G-V7-2", "G-V7-3",
                                                              "G-V7-4", "G-V7-5")
                          else O.SOURCES["standings"], "src")])
    lrows = []
    for s in st["leaderboard"]:
        lrows.append([
            esc(s["id"]), esc(s["name"]), esc(s["market"]),
            esc(s["signal"]),
            f'{s["n_pass"]}/{s["n_gates"]}',
            '<span class="badge b-bad">BLOCKED</span>',
            esc(s["reason"]),
            '<span class="badge b-off">0.00 u</span>',
            f'<a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v7/prereg/'
            f'{esc(s["id"])}.json" target="_blank" rel="noopener">prereg</a>',
        ])
    prows = []
    for r in st["prereg"]["rows"]:
        prows.append([esc(r["id"]), f'<code>{esc(r["sha256"][:16])}…</code>',
                      esc(r["state"]),
                      f'<a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/'
                      f'{esc(r["path"])}" target="_blank" rel="noopener">{esc(r["path"])}</a>'])
        par = []
    for p in st["parlays"]:
        gid, mu = p.get("game_id"), p.get("matchup") or ""
        game_url = next((r["source_url"] for r in slate["rows"] if r["game_id"] == gid), None)
        if p.get("flag"):
            par.append([esc(mu), blank(p["flag"]), blank(p["flag"]),
                        blank(p["flag"]), blank(p["flag"]), src(game_url, "game")])
            continue
        par.append([esc(mu),
                    n(p["p_leg_a"], 3), n(p["p_leg_b"], 3),
                    n(p["naive"], 4),
                    f'{n(p["with_rho"], 4)} <span class="badge b-info">{p["delta"]:+.4f}</span>',
                    src(game_url, "game")])
    body = f"""
<div class="cards">{kpi("Strategies", str(len(st["leaderboard"])), "all pre-registered")}
{kpi("Gates", f'{sum(1 for g in gates if g["status"]=="PASS")}/{len(gates)}', "PASS on this build")}
{kpi("Measured rho", n(res["rho"]["r"], 4), "margin vs total")}
{kpi("Stakes published", "0.00 u", "no gate is faked green")}</div>

<p class="note">Snapshot: the official pages were read on <b>2026-11-19</b>
({esc(O.RETRIEVED_AT_UTC)}). Every measurement below is recomputed from the committed
official finals and the transcribed snapshot, so a reader can re-derive it.</p>

<h2>The ten gates, and the number each one measured</h2>
{grows and tbl(["Gate", "What it tests", "Threshold", "Measured", "Status", "Source"], grows)}
<p class="note">A gate is a measurement, not an adjective. G-V7-6 blocks every strategy that
needs a price, because <b>no market price was captured</b> and an edge without a price is a
number with no denominator. G-V7-8 blocks the availability strategies because no injury
report for this slate was read. G-V7-4 blocks the paired-significance test: on 29
disagreements the model was right 16 times to the record rule's 13, exact p = 0.71 — that is
noise, and it is reported as noise.</p>

<h2>Strategies, and why none of them has a stake</h2>
{tbl(["ID", "Strategy", "Market", "Signal", "Gates", "Status", "Why it is blocked", "Stake",
      "Source"], lrows)}

<h2>Pre-registration: frozen before the first bet</h2>
<p>Each file below was written before any pick was published and carries the signal, the
thresholds, the universe and the exact settlement rule. Re-running the build re-hashes it; a
field that changed would change the hash, and the check fails. A strategy edited after its
first bet is a different strategy, and the id must change with it.</p>
{tbl(["ID", "sha256 (first 16)", "State", "File"], prows)}

<h2>Parlays: the measured rho, printed next to the naive product</h2>
<p>Two legs on one game are not independent. The price of the pair is
P(A) × P(B | A); a correlation-blind tool prints P(A) × P(B). Both are below, with the
difference in a badge. The measured correlation between home margin and total points over
{res["rho"]["n"]} official finals is <b>r = {n(res["rho"]["r"], 4)}</b>
(95% CI {n(res["rho"]["ci95"][0], 3)} … {n(res["rho"]["ci95"][1], 3)}) — statistically
indistinguishable from zero, which is itself the useful finding: <i>stacking a spread and a
total on the same game costs about what independence says it costs, and any book pricing a
same-game parlay materially worse than the naive product is pricing something we cannot
see.</i></p>
{tbl(["Game", "Leg A: P(win)", "Leg B: P(over)", "Naive product",
      "With measured rho", "Source"], par)}
<p class="note">A parlay row carries no stake either: the legs are our own numbers, not
market prices, so the "price" here is the probability our own model assigns, not a quote
anyone offered. It is published because the arithmetic is the deliverable, and withholding
it — as an earlier build did — leaves a reader unable to see the size of the error.</p>
"""
    return body


# ------------------------------------------------------------------ skill page
def page_skill(res: dict, st: dict) -> str:
    wf = res["walk_forward"]
    luck = res["luck"]
    lrows = []
    for tri, v in sorted(luck.items(), key=lambda kv: -(kv[1].get("z") or -9)):
        if v.get("z") is None:
            lrows.append([esc(tri), blank(v.get("flag") or "unmeasured"),
                          blank("blank"), blank("blank"), blank("blank"),
                          blank("blank"), blank("blank")])
            continue
        kind = "b-bad" if v["outside"] else "b-ok"
        t = res["teams"].get(tri, {})
        lrows.append([f'<a href="{esc(t.get("standings_url") or O.SOURCES["standings"])}" '
                      f'target="_blank" rel="noopener">{esc(tri)}</a>',
                      str(v["n"]), n(v["exp_wins"], 2), str(v["actual_wins"]),
                      n(v["z"], 2), f'<span class="badge {kind}">{"outside" if v["outside"] else "inside"}</span>',
                      esc(str(v.get("w_gap_vs_standings")) if v.get("w_gap_vs_standings") else "0")])
    props = st["props"]
    prows = []
    for r in props["rows"][:10]:
        prows.append([esc(r["player"]), str(r["games"]), n(r["mean_pts"], 1),
                      n(r["sd_pts"], 1), esc(str(r["games_needed_for_5pt_halfwidth"])),
                      src(r["source_url"], "box score")])
    w = wf
    body = f"""
<div class="cards">{kpi("Walk-forward games", str(w.get("n")), w.get("train_rule", ""))}
{kpi("Accuracy", n(w.get("accuracy"), 3), f'better-record rule {n(w.get("record_accuracy"),3)}')}
{kpi("Log-loss", n(w.get("log_loss"), 4), "coin flip = 0.6931")}
{kpi("Paired p", n((w.get("paired") or {}).get("exact_two_sided_p"), 4),
      f'{(w.get("paired") or {}).get("n")} disagreements')}</div>

<h2>Does either estimator beat the obvious rule?</h2>
<p>Every game below is predicted by a cut that trained <b>only on strictly earlier dates</b> —
no rating in a 2026-10 game uses a 2026-11 result. The measurement is on the <i>decision</i>
(which side, did it win), not on margin error, because margin error does not tell a reader
whether to act.</p>
{tbl(["Measure", "Value", "Baseline", "Verdict", "Source"], [
    ["Accuracy", n(w.get("accuracy"), 3), n(w.get("record_accuracy"), 3) + " (better record)",
     '<span class="badge b-ok">better</span>' if (w.get("accuracy") or 0) > (w.get("record_accuracy") or 0)
     else '<span class="badge b-bad">no better</span>', src(O.SOURCES["games"].format(date="2026-11-13"), "finals")],
    ["Log-loss", n(w.get("log_loss"), 4), f'{n(w.get("coin_log_loss"),4)} (coin flip)',
     '<span class="badge b-ok">better</span>' if w.get("beats_coin_log_loss")
     else '<span class="badge b-bad">worse than a coin</span>', src(O.SOURCES["games"].format(date="2026-11-13"), "finals")],
    ["Brier", n(w.get("brier"), 4), "0.25 (a constant 0.5 forecast)", "no baseline to clear",
     src(O.SOURCES["games"].format(date="2026-11-13"), "finals")],
    ["MAE, E1 margin", n(w.get("mae_e1"), 2) + " pts", "—", "margin error, not a decision",
     src(O.SOURCES["games"].format(date="2026-11-13"), "finals")],
    ["MAE, E2 margin", n(w.get("mae_e2"), 2) + " pts", "—", "margin error, not a decision",
     src(O.SOURCES["games"].format(date="2026-11-13"), "finals")],
    ["Paired test on disagreements", f'{(w.get("paired") or {}).get("model_right")} vs '
     f'{(w.get("paired") or {}).get("record_right")}',
     f'exact p = {n((w.get("paired") or {}).get("exact_two_sided_p"), 4)}',
     '<span class="badge b-bad">indistinguishable</span>',
     src(O.SOURCES["games"].format(date="2026-11-13"), "finals")],
])}
<p class="note">Training data for every row above: the committed official finals captures
(two sources of truth, both linked on <a href="v7-slate.html">the slate page</a>), scored
against the league's own game pages.</p>
<p><b>The honest reading.</b> The model beats a coin flip on log-loss and matches the
better-record rule, but the paired test — the only test that asks whether the model adds
information the record does not already carry — comes back at
p = {n((w.get("paired") or {}).get("exact_two_sided_p"), 3)}. That is not evidence of skill.
It is the reason every stake on this site is 0.00, and it is published at the top of the
brief rather than in a footnote.</p>

<h2>Luck, as a z-score per club</h2>
<p>Expected wins come from the club's own Pythagorean rate over its official games; the
residual is divided by the binomial sd of that club's own game count. A club outside
|z| &gt; 2 is a club whose record is mostly outcome noise, and a strategy that leans on one
is <b>refused</b>, not adjusted.</p>
{tbl(["Club", "GP", "Exp W", "Actual W", "Luck z", "Band", "W gap vs standings"], lrows)}
<p class="note">{len(res["outside_band"])} club(s) outside the band:
{esc(", ".join(res["outside_band"]) or "none")}. The last column is the one-date clock
difference between the team-stat pages (through 2026-11-17) and the standings page (through
2026-11-18), published rather than blended.</p>

<h2>The transcribed page, checked against the results</h2>
<p>The 2026-11-19 advanced page was transcribed by hand. Two independent routes to the same
ranking are compared here — a margin rating solved from the committed finals, and the
league's own per-100 NetRtg — and the Pearson correlation between them is
<b>r = {n(res["corroboration"]["pearson_r"], 3)}</b> over {res["corroboration"]["n"]} clubs.
A transcription error in one club's row would drop that number; three arithmetic identities
in <code>test_v7</code> check the rest.</p>

<h2>Player props: blocked, with the arithmetic that blocks them</h2>
<p>A prop line needs a per-player sample. The largest committed per-player log in
<code>data/v5/player_logs_union.json</code> covers <b>{props["max_games_per_player"]} games</b>;
the gate requires 15. So every prop row is blocked, and the table shows why — including the
sample a ±5-point estimate would actually need.</p>
{tbl(["Player", "Games logged", "Mean pts", "SD pts", "Games needed for ±5", "Source"], prows)}
<p class="note">This is the honest version of "publish nothing": the reason is arithmetic, it
is on the page, and it is the same reason a same-game player combo (S-07) cannot be priced.</p>
"""
    return body


# ------------------------------------------------------------------ methodology page
def page_methodology(res: dict) -> str:
    hc = res["home_court"]
    finals_src = src(O.SOURCES["games"].format(date="2026-11-13"), "finals")
    rows = [
        ["Y", "Pythagorean exponent", "13.91", "no",
         f'Basketball-Reference convention; stated, not fitted · {src("https://www.basketball-reference.com/about/glossary.html", "glossary")}'],
        ["Y", "Noise band |z|", "2.00", "no",
         f'a strategy leaning on a club outside it is refused · {src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/v7/model.py", "model.py")}'],
        ["Y", "Ridge λ (E1 solver)", "4.00", "no",
         f'shrinks a 3-game club toward the mean · {src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/v7/model.py", "model.py")}'],
        ["Y", "Min training finals", "40", "no",
         f'floor before the walk-forward starts · {src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/v7/model.py", "model.py")}'],
        ["F", "Home-court h", n(hc.get("hca_points"), 3), "pinned",
         f'h = sd(margin) × Φ⁻¹(home-win rate) = {n(hc.get("margin_sd"),3)} × '
         f'Φ⁻¹({n(hc.get("home_win_rate"),4)}) · {finals_src}'],
        ["F", "Margin σ", n(hc.get("margin_sd"), 3), "measured",
         f'sd of home margin over {hc.get("n")} official finals · {finals_src}'],
        ["F", "ρ (margin, total)", n(res["rho"]["r"], 4), "measured",
         f'over {res["rho"]["n"]} official finals · {finals_src}'],
    ]
    body = f"""
<div class="cards">{kpi("Home-win rate", n(hc.get("home_win_rate"), 4), f'{hc.get("n")} finals')}
{kpi("Pinned h", n(hc.get("hca_points"), 3) + " pts", "reproduces the rate by construction")}
{kpi("σ margin", n(hc.get("margin_sd"), 3) + " pts", "fitted to nothing")}
{kpi("ρ", n(res["rho"]["r"], 4), "margin vs total")}</div>

<h2>Every constant, and whether it was fitted</h2>
<p>A parameter that is fitted to the data it is judged on is not a parameter, it is a
self-fulfilling prophecy. The column that matters is the third one.</p>
{tbl(["Set in code?", "Parameter", "Value", "Fitted?", "Where it comes from"], rows)}
<p class="note">Every input these constants act on is linked in the table at the foot of this
page; the two that are measured rather than set (h and σ) are measured on the committed
official finals, whose game pages are linked from
<a href="v7-slate.html">the slate page</a>.</p>

<h2>The two clocks on the league's own site</h2>
<p>Measured this session: the three <code>/stats/teams/*</code> pages report games through
<b>{O.GAMES_PLAYED_AS_OF}</b>, and <code>/standings</code> includes the games of
<b>{O.STANDINGS_AS_OF}</b>. They are one date apart. This build uses the stats-page W for the
luck calculation (so the win column matches the games-played column) and publishes the gap,
rather than silently mixing the two.</p>

<h2>How each input was read</h2>
<p>{esc(O.TRANSPORT)}. This is recorded because it is a limitation: a reader cannot reproduce
the read from this sandbox, only from an environment with page-fetch access. Everything
described has a URL, and the three arithmetic identities in <code>nba2/v7/test_v7.py</code>
are what make the transcription checkable.</p>
{tbl(["Surface", "URL"], [[esc(k), src(v if not v.startswith("https://www.nba.com/games")
                              else v.format(date="2026-11-19"), v)] for k, v in O.SOURCES.items()])}
"""
    return body


# ------------------------------------------------------------------ verify page
def page_verify(res: dict, gates: list[dict], checks: list[dict]) -> str:
    grows = [[esc(g["id"]), esc(g["gate"]), esc(g["detail"]),
              f'<span class="badge {"b-ok" if g["status"]=="PASS" else "b-bad"}">'
              f'{esc(g["status"])}</span>',
              src(O.SOURCES["advanced"] if g["id"] in ("G-V7-1", "G-V7-2", "G-V7-3",
                                                       "G-V7-4", "G-V7-5")
                  else O.SOURCES["standings"], "src")] for g in gates]
    crows = [[esc(c["id"]), esc(c["what"]), esc(c["result"]),
              f'<span class="badge {"b-ok" if c["ok"] else "b-bad"}">'
              f'{"OK" if c["ok"] else "FAIL"}</span>',
              src("https://github.com/wingbangboozle1-lang/NBA2/blob/main/nba2/v7/check.py",
                  "check.py")] for c in checks]
    from . import verification as VER
    v = VER.build()
    vrows = []
    for r in v["rows"]:
        status = ('<span class="blank">not read</span>' if r["not_read"]
                  else f'<span class="badge {"b-ok" if r["ok"] else "b-bad"}">'
                       f'{esc(str(r["matched"]))}/{esc(str(r["n"]))}</span>')
        vrows.append([f'<b>{esc(r["id"])}</b>', esc(r["claim"]), esc(r["compared"]),
                      esc(str(r["n"])) if not r["not_read"] else "0",
                      status, esc(r["method"]),
                      src(r["source"], "official page")])
    body = f"""
<div class="cards">{kpi("Publishable", "yes" if all(c["ok"] for c in checks) else "no", "fail-closed")}
{kpi("Verification", f'{v["n_matched"]}/{v["n_compared"]}', "items matched")}
{kpi("Claims checked", f'{v["n_claims"] - v["n_not_read"]}/{v["n_claims"]}', "against an official page")}
{kpi("Not read", f'{v["n_not_read"]}', "blank + flagged")}</div>

<h2>Line-by-line verification against the official pages</h2>
<p class="note">One row per claim this layer rests on, the page it was checked against, how many
items were compared, and how many matched. A row where nothing could be read is printed as a
blank in the status column and carries its flag, rather than being counted as a match. The
identities in the method column are the reason the check is re-runnable: they are encoded in
<code>nba2/v7/test_v7.py</code>, so drift breaks the build.</p>
{tbl(["ID", "Claim", "What was compared", "N", "Matched", "Method", "Source"], vrows)}

{kpi("Gates", f'{sum(1 for g in gates if g["status"]=="PASS")}/{len(gates)}', "on this build")}
{kpi("Structural checks", f'{sum(1 for c in checks if c["ok"])}/{len(checks)}', "on the emitted tree")}
{kpi("Snapshot", esc(O.RETRIEVED_AT_UTC), "official pages read")}</div>

<h2>Structural checks over the emitted pages</h2>
{tbl(["ID", "What", "Result", "Status", "Source"], crows)}

<h2>The ten strategy gates</h2>
{tbl(["Gate", "Test", "Measured", "Status", "Source"], grows)}

<h2>What this layer does not verify</h2>
<p>It cannot verify a market price (none was captured), an injury status for these dates (no
report was read), or a per-player prop line (the sample is three games). Each of those is a
blank on the page it belongs to, with the reason printed, and each is listed on
<a href="flagged.html">Flagged for review</a>.</p>
"""
    return body


# ------------------------------------------------------------------ build
def build(write: bool = True) -> dict:
    from . import model as M

    res = M.resolve()
    slate = __import__("nba2.v7.slate", fromlist=["build"]).build(res)
    st = S.build(res, slate)
    st["gates"] = S.evaluate(res, st["prereg"], st["props"])

    pages = {
        "v7-slate.html": page_slate(res, slate),
        "v7-strategies.html": page_strategies(st, slate, res),
        "v7-skill.html": page_skill(res, st),
        "v7-methodology.html": page_methodology(res),
    }
    from . import check as CH
    checks = CH.structural(pages)
    pages["v7-verify.html"] = page_verify(res, st["gates"], checks)

    titles = {k: v for k, v in PAGES.items()}
    if write:
        SITE.mkdir(parents=True, exist_ok=True)
        for name, body in pages.items():
            (SITE / name).write_text(page(titles[name], name, body))
        dump(V7 / "slate.json", slate)
        dump(V7 / "strategies.json", {k: v for k, v in st.items()})
        dump(V7 / "model.json", M.build())
        dump(V7 / "checks.json", {"checks": checks,
                                  "gates": st["gates"],
                                  "ok": all(c["ok"] for c in checks)})
    return {"pages": sorted(pages), "checks": checks, "gates": st["gates"]}
