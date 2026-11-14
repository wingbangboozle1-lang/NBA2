#!/usr/bin/env python3
"""Build the NBA2 dashboard into docs/ (GitHub Pages root).
Every data-table row must carry a source link - checked by scripts/check_site.py.
Deterministic; stdlib only. Run: python3 scripts/build_site.py"""
import csv, html, os
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "dashboard")

NAV = [
    ("index.html", "Dashboard"), ("slates.html", "Slates & Picks"),
    ("injuries.html", "Injuries & Rotation"), ("game-flow.html", "Game Flow"),
    ("strategies.html", "Strategies & Gates"), ("correlation.html", "Correlation"),
    ("leaderboard.html", "Leaderboard"), ("data.html", "Data Tables"),
    ("suggestions.html", "Suggestions"), ("questions.html", "Questions"),
    ("flagged.html", "Flagged for Review"), ("sources.html", "Sources"),
]


def read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def link(url, text=None):
    if not url:
        return '<span class="flag">unverified</span>'
    return f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(text or url)}</a>'


def cell(v):
    """Blank cells carry the dashboard's blank marker — never an empty <td> (CR-4)."""
    return v if str(v).strip() else '<span class="flag">—</span>'


def src_label(p):
    """Label a Source cell for what it actually links to (V-05)."""
    if p["source_type"] == "official":
        return "nba.com player page"
    host = urlparse(p["source_url"]).netloc
    return host or "source link"


def page(fname, title, body):
    nav_html = "".join(
        f'<a href="{f}" class="{"active" if f == fname else ""}">{t}</a>' for f, t in NAV
    )
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · NBA2</title>
<link rel="stylesheet" href="styles.css"></head>
<body>
<header><div class="wrap"><h1>NBA2 <span class="sub">line origination &amp; strategy platform</span></h1>
<p class="snap">Snapshot 2026-11-13 · official injury report 5:15 p.m. ET · model v1.0 · every row source-linked · unverified values blank + flagged</p>
<nav>{nav_html}</nav></div></header>
<main class="wrap">{body}</main>
<footer class="wrap"><p>NBA2 · built 2026-11-13 by session arena-10957a28 · sources: official NBA (nba.com, official.nba.com, ak-static.cms.nba.com) + labeled trusted-secondary · <a href="https://github.com/wingbangboozle1-lang/NBA2">repository</a> · Unverified values are never inferred — see <a href="flagged.html">Flagged for Review</a>.</p></footer>
</body></html>"""
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        f.write(doc)


def table(headers, rows, caption=None):
    """rows: list of lists of cell HTML. Source cells must contain <a href>."""
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    cap = f"<caption>{caption}</caption>" if caption else ""
    return f'<div class="tblwrap"><table>{cap}<thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


def short(url, t):
    return link(url, t)


def main():
    os.makedirs(OUT, exist_ok=True)
    games = read("games.csv")
    stand = {r["team"]: r for r in read("standings-2026-11-13.csv")}
    lines = {r["game_id"]: r for r in read("our-lines.csv")}
    picks = read("picks.csv")
    parlays = read("parlays.csv")
    props = read("prop-lines.csv")
    injuries = read("injury-report-2026-11-13.csv")
    corr = read("correlation-matrix.csv")
    luck = read("luck-table.csv")
    lb = read("leaderboard.csv")
    ratings = read("team-ratings-2026-11-13.csv")

    def rec(t):
        r = stand.get(t)
        return f"{r['wins']}-{r['losses']}" if t in stand else ""

    picks_by = {}
    for p in picks:
        picks_by.setdefault((p["date"], p["game_id"]), []).append(p)
    parlays_by = {}
    for p in parlays:
        parlays_by.setdefault((p["date"], p["game_id"]), []).append(p)

    # ---------------- index ----------------
    n_games, n_picks = len(games), len(picks)
    out_tonight = sum(1 for r in injuries if r["game_date"] == "2026-11-13" and r["status"] == "Out" and not r["reason"].startswith("G League"))
    luck_sorted = sorted(luck, key=lambda r: float(r["luck_component_wins"]), reverse=True)
    today_rows = []
    for g in games:
        if g["date"] != "2026-11-13":
            continue
        ln = lines[g["game_id"]]
        pk = "; ".join(p["pick"] for p in picks_by.get((g["date"], g["game_id"]), [])) or "<em>no pick (selectivity gate)</em>"
        today_rows.append([
            short(g["source_url"], f"{g['away']} @{g['home']}"), g["tip_et"],
            f"{rec(g['away'])} / {rec(g['home'])}",
            f"{ln['our_spread_home']} (home)", ln["our_total"], pk, short(g["source_url"], "nba.com"),
        ])
    body = f"""
<section class="cards">
<div class="card"><b>{n_games}</b><span>games lined (Nov 13–16)</span></div>
<div class="card"><b>{n_picks}</b><span>single picks pass conviction gates</span></div>
<div class="card"><b>{out_tonight}</b><span>players OUT tonight (excl. two-way)</span></div>
<div class="card"><b>{len(parlays)}</b><span>correlated combo entries</span></div>
<div class="card warn"><b>PHI +4.2</b><span>luckiest record vs rating (10-3, exp 5.8)</span></div>
</section>
<h2>Tonight's slate — Friday 2026-11-13 <small>(all 9 games are Emirates NBA Cup group games)</small></h2>
{table(["Matchup", "Tip ET", "W-L (A/H)", "Our spread", "Our total", "Picks (make at our number)", "Source"], today_rows)}
<p class="note">Picks are conditional: bet only at <b>our number or better</b>. Market lines are not yet connected
(<a href="questions.html">Q-1</a>), so edge-vs-market and CLV scoring are pending. Full slates incl. Nov 14–16:
<a href="slates.html">Slates &amp; Picks</a>. Nov 15–16 lines are injury-unadjusted until game-day reports
(<code>PENDING</code> in the picks table).</p>
<h2>What this platform is</h2>
<p>Every number here is <b>originated by our model</b> from source-verified inputs (official injury report,
official schedule, labeled trusted-secondary efficiency ratings) — see <a href="strategies.html">Strategies &amp; Gates</a>.
Strategies must pass validation gates G1–G5 and are ranked by a luck-free Process Rating, never raw ROI
(<a href="leaderboard.html">Leaderboard</a>). Unknowns and discovery plans live in the
<a href="questions.html">Questions register</a>; proposed changes wait for your decision in the
<a href="suggestions.html">Suggestions queue</a>.</p>
<h2>Luck ledger leaders (record vs rating-based expectation)</h2>
{table(["Team", "Record", "Adj. net rating", "Expected wins", "Luck component", "Source"],
       [[r["team"], f"{r['wins']}-{r['losses']}", r["nrtg_adj"], r["expected_wins"], r["luck_component_wins"],
         short(r["source_url"], "ratings source")] for r in luck_sorted[:6]])}
<p class="note">Full 30-team ledger on <a href="data.html">Data Tables</a>. Method: expected wins from the
logistic of adjusted net rating (see Strategies page).</p>
"""
    page("index.html", "Dashboard", body)

    # ---------------- slates ----------------
    sections = []
    for d in ["2026-11-13", "2026-11-14", "2026-11-15", "2026-11-16"]:
        rows = []
        for g in games:
            if g["date"] != d:
                continue
            ln = lines[g["game_id"]]
            pk = picks_by.get((g["date"], g["game_id"]), [])
            pick_txt = "<br>".join(f"<b>{p['strategy'].split()[0]}</b> {p['pick']} <span class='tiny'>{p['injury_data_status']}</span>" for p in pk) or "<em>no pick — selectivity gate</em>"
            pl = parlays_by.get((g["date"], g["game_id"]), [])
            pl_txt = "<br>".join(f"<span class='tiny'>{p['strategy'].split()[0]}: {p['legs']}</span>" for p in pl[:2]) or "<em>—</em>"
            inj = f"<span class='tiny'>{ln['away_injury_names']}</span>" if ln["away_injury_names"] else "<span class='tiny'>no listed absences</span>"
            injh = f"<span class='tiny'>{ln['home_injury_names']}</span>" if ln["home_injury_names"] else "<span class='tiny'>no listed absences</span>"
            rows.append([
                short(g["source_url"], f"{g['away']} @{g['home']}") + f"<br><span class='tiny'>{g['game_id']}" + (f" · Cup {g['nba_cup_group']}</span>" if g["nba_cup_group"] else "</span>"),
                g["tip_et"], f"{rec(g['away'])} / {rec(g['home'])}",
                f"{ln['our_spread_home']}", ln["our_total"], pick_txt, pl_txt,
                f"<b>{g['away']}</b>: {inj}<br><b>{g['home']}</b>: {injh}",
                f"{ln['away_rest']} / {ln['home_rest']}",
                short(g["source_url"], "game page"),
            ])
        note = ""
        if d == "2026-11-15":
            note = "<p class='note'>Injury-unadjusted (official reports publish game-day) — picks carry PENDING status. DAL plays 3rd game in 4 days (road B2B at BOS).</p>"
        if d == "2026-11-16":
            note = "<p class='note'>Injury-unadjusted. B2B: PHI (road), HOU (road + 3-in-4), WAS (home), PHX (travel). PHI carries +4.2 wins of luck vs its rating.</p>"
        if d == "2026-11-14":
            note = "<p class='note'>Partial official report at snapshot (see Injuries page). CHI@MIN: MIN −25.0 re-run after verified baselines priced Edwards' absence at star tier (was −28.0 pre-fix; see <a href='flagged.html'>F-3</a>).</p>"
        sections.append(f"<h2>{d} ({sum(1 for g in games if g['date']==d)} games)</h2>{note}"
                        + table(["Game", "Tip ET", "W-L (A/H)", "Our spread (home)", "Our total", "Picks", "Correlated combos", "Injury names (official)", "Rest", "Source"], rows))
    body = f"""
<p class="note">Our spreads are home-relative (e.g. <code>+9.5</code> = home side +9.5). Pick text names the side
to bet at our number. Combos max 2 same-game legs (gate G4) and use only documented correlation directions
(<a href="correlation.html">Correlation</a>).</p>
{"".join(sections)}
<h2>Player-prop projections (S4)</h2>
{table(["Date", "Player", "Team", "Prop", "Our line", "Baseline", "Opp def adj", "Flow lean", "Make at", "Availability", "Sources"],
       [[p["date"], p["player"], p["team"], p["prop"], p["our_line"], p["baseline_ppg"], p["opp_def_adj"], p["flow_lean"],
         p["make_at"], p["availability"], short(p["source_url"], "game") + " " + short(p["baseline_source"], "baseline")] for p in props],
       caption=f"{len(props)} projections from verified NBA.com season baselines (28 teams; LAL/CHA/TOR flagged blank)")}
"""
    page("slates.html", "Slates & Picks", body)

    # ---------------- injuries ----------------
    inj_rows = []
    for r in injuries:
        cls = ' class="flag"' if r["status"] in ("Out", "Doubtful") else ""
        inj_rows.append([
            r["game_date"], r["matchup"], r["team"], r["player"] or "—",
            f"<span{cls}>{r['status']}</span>", r["reason"],
            r["report_timestamp"], short(r["source_url"], "official PDF"),
        ])
    body = f"""
<h2>Official NBA injury report — snapshot 2026-11-13 5:15 p.m. ET</h2>
<p>Source of record: <a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf" target="_blank" rel="noopener">Injury-Report_2026-11-13_05_15PM.pdf</a>
via the <a href="https://official.nba.com/nba-injury-report-2026-27-season/" target="_blank" rel="noopener">official NBA injury report index</a>
(reports refresh every 15 minutes on game days — snapshot may drift; Q-8). Teams must file statuses by 5 p.m. local the day before a game
and update on game days ([official rules text](https://official.nba.com/nba-injury-report-2026-27-season/)).</p>
<p class="note">Impact tiers used by the model: Out 1.0 / Doubtful 0.9 / Questionable 0.5 / Probable 0.1 ×
star 4.0 / starter 2.0 / rotation 0.8 margin points (cap 8.0). Two-way and G-League rows are excluded from impact.
Suspension note: Marcus Smart (HOU) — 3 games, official release
<a href="https://official.nba.com/rockets-smart-suspended" target="_blank" rel="noopener">here</a>.</p>
{table(["Game date", "Matchup", "Team", "Player", "Status", "Reason", "Report", "Source"], inj_rows)}
<h2>Rotation-minutes implications (method)</h2>
<ol>
<li>Star Out → production redistributes to the team's next verified options; our impact tier charges 4.0 margin points (parameter, Q-3).</li>
<li>Questionable players are priced at half impact; re-run when game-day reports flip statuses (S-7 automation).</li>
<li>Minutes limits are not published on official reports (Q-6) — team PR notes are tracked separately and flagged secondary.</li>
<li>Blowout risk (large our-spread) suppresses star minutes — the correlation matrix bans favorite-star prop stacks at |margin| ≥ 11.</li>
</ol>
"""
    page("injuries.html", "Injuries & Rotation", body)

    # ---------------- game flow ----------------
    gf_rows = []
    for g in games:
        ln = lines[g["game_id"]]
        flow = []
        if ln["pred_margin_home"] and abs(float(ln["pred_margin_home"])) >= 12:
            flow.append("blowout profile — star props risky, teammate corr rises")
        if ln["away_rest"] != "rested" or ln["home_rest"] != "rested":
            flow.append(f"rest: away {ln['away_rest']}, home {ln['home_rest']}")
        if float(ln["our_total"]) >= 232:
            flow.append("up-tempo / high-total lean")
        elif float(ln["our_total"]) <= 224:
            flow.append("grind / low-total lean")
        if ln["away_injury_names"] or ln["home_injury_names"]:
            flow.append("rotation stress from official absences")
        gf_rows.append([
            g["date"], short(g["source_url"], f"{g['away']} @{g['home']}"),
            ln["pred_margin_home"], ln["our_total"],
            "; ".join(flow) or "balanced profile",
            short(g["source_url"], "nba.com"),
        ])
    body = f"""
<p class="note">Flow reads are analytical judgments built on verified inputs (ratings, official injury
statuses, verified rest). Analyst narrative for each game is in the repo:
<a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/game-flow.md">analysis/game-flow.md</a>.
Derived flags below are computed from the data itself.</p>
{table(["Date", "Game", "Pred. home margin", "Our total", "Flow profile (derived)", "Source"], gf_rows)}
<h2>Cross-cutting verified context</h2>
<ul>
<li><b>Nov 13:</b> no team on a back-to-back (the four Nov 12 games —
{short("https://www.cbssports.com/nba/gametracker/boxscore/NBA_20261112_TOR@PHI/", "TOR@PHI")},
{short("https://nba-grid.com/nba-today/", "DET@WAS")},
{short("https://www.cbssports.com/nba/gametracker/boxscore/NBA_20261112_DAL@MIN/", "DAL@MIN")},
{short("https://nba-grid.com/nba-today/", "CHA@PHX")} — involve only teams resting today).</li>
<li><b>Nov 14:</b> B2B for CLE, MIA, MEM, NOP, CHI. DAL arrives off a 94-133 loss at MIN
{short("https://www.cbssports.com/nba/gametracker/boxscore/NBA_20261112_DAL@MIN/", "(box)")}.</li>
<li><b>Nov 15:</b> DAL road B2B + 3rd game in 4 days (at CLE → at BOS).</li>
<li><b>Nov 16:</b> B2B for PHI (road), HOU (road + 3-in-4), WAS (home), PHX (travel). NOP 3rd game in 4 days.</li>
<li><b>Suspension:</b> Marcus Smart (HOU) serves game 1 of 3 tonight —
{short("https://official.nba.com/rockets-smart-suspended", "official release")}.</li>
</ul>
"""
    page("game-flow.html", "Game Flow", body)

    # ---------------- strategies ----------------
    body = """
<p class="note">Full methodology with derivations and citations:
<a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/strategy/model.md">model.md</a> ·
<a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/strategy/validation-gates.md">validation-gates.md</a> ·
<a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/strategy/correlation.md">correlation.md</a> ·
<a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/strategy/leaderboard.md">leaderboard.md</a>.</p>
<h2>Line origination (v1.0)</h2>
<pre>predicted home margin = (NRtg/A_home − NRtg/A_away) + HCA − injury_home + injury_away + fatigue terms
predicted total       = league mean + scoring-lean terms − 0.35 × combined injury impact</pre>
<p>Inputs: schedule-adjusted net ratings
(<a href="https://www.basketball-reference.com/leagues/NBA_2027_ratings.html" target="_blank" rel="noopener">Basketball-Reference</a>, trusted secondary — flagged per row),
official injury statuses
(<a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf" target="_blank" rel="noopener">official PDF</a>),
verified rest. Parameters (HCA 2.0, tiers 4.0/2.0/0.8, fatigue −0.6/−1.1…) are documented assumptions pending calibration (Q-3).</p>
<h2>Validation gates — every strategy must pass all five</h2>
<table><thead><tr><th>Gate</th><th>Rule</th><th>Blocks</th></tr></thead><tbody>
<tr><td>G1 Data integrity</td><td>≥95% picks with verified source links; unverified inputs void the pick</td><td>silent fabrication</td></tr>
<tr><td>G2 Sample size</td><td>≥30 graded picks to rank; ≥100 to pay rewards</td><td>small-sample luck</td></tr>
<tr><td>G3 Price honesty</td><td>graded at our recorded number; CLV logged when market feed exists</td><td>bad-price wins counted as skill</td></tr>
<tr><td>G4 Risk &amp; correlation caps</td><td>≤2 same-game legs; banned combos enforced; ≤0.25 Kelly; no chase doubling</td><td>variance death, fake parlays</td></tr>
<tr><td>G5 Luck separation</td><td>raw record must beat expected record (model win prob) for performance points</td><td>rewarding luck</td></tr>
</tbody></table>
<h2>Removing luck — three mechanisms</h2>
<ol>
<li><b>Expected-record ledger:</b> luck component = actual wins − Σ model win probability.
Current extreme: PHI 10-3 with expected 5.8 → <b>+4.2 luck</b>.</li>
<li><b>Process Rating</b> = 0.40·z(shrunk ROI) + 0.35·z(CLV) + 0.15·z(gates) − 0.10·z(drawdown);
raw ROI is displayed but labeled luck-contaminated. CLV is the accepted skill measure —
"closing line value accumulates with skill"
(<a href="https://onlinenbabetting.com/spreads/" target="_blank" rel="noopener">source</a>).</li>
<li><b>Conviction gating:</b> play only where |our margin| ≥ 4 or total lean ≥ 5 pts —
selectively skill-based by construction.</li>
</ol>
<h2>Prop-combo rules</h2>
<ul>
<li>Projection = verified season baseline + 0.35 × opponent defense adjustment; bet-able at ±1.5-pt buffer around our line.</li>
<li>Combos must follow documented correlation direction; big-favorite star props banned (blowout minutes); game-under + props banned.</li>
<li>See <a href="correlation.html">Correlation</a> for every value and its source.</li>
</ul>
"""
    page("strategies.html", "Strategies & Gates", body)

    # ---------------- correlation ----------------
    corr_rows = []
    for r in corr:
        kind = "empirical" if r["basis"].startswith("empirical") else "industry estimate"
        cls = "ok" if kind == "empirical" else ""
        corr_rows.append([
            r["leg_1"], r["leg_2"], f"{r['r_low']} … {r['r_high']}",
            f"<span class='{cls}'>{kind}</span>", r["context"],
            short(r["source_url"], "source"), r["note"],
        ])
    body = f"""
<p class="note">Two evidence tiers — measured (3-season study of 505,721 player pairs:
<a href="https://kindoflost.com/2026/09/nba-dfs-correlation-measured/" target="_blank" rel="noopener">kindoflost.com</a>)
and industry range estimates (treated as priors). Nothing is inferred: values without a source are absent.
Method + pricing formula: <a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/strategy/correlation.md">correlation.md</a>.</p>
{table(["Leg 1", "Leg 2", "r range", "Basis", "Context", "Source", "Note"], corr_rows)}
"""
    page("correlation.html", "Correlation", body)

    # ---------------- leaderboard ----------------
    lb_rows = [[r["strategy"], r["focus"], r["picks_logged"], r["record"], r["raw_roi"] or "—",
                r["process_rating"], r["gate_status"], r["reward_points"],
                short("https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/strategy/leaderboard.md", "rules")]
               for r in lb]
    body = f"""
<p class="note">Competition design + reward proposal:
<a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/strategy/leaderboard.md">leaderboard.md</a>.
Primary sort is the <b>Process Rating</b> (luck-free). Raw ROI is secondary and labeled luck-contaminated.
Reward payouts are locked until (a) market feed exists for CLV and (b) sizing is approved in the
<a href="suggestions.html">suggestions queue</a> (S-2).</p>
{table(["Strategy", "Focus", "Picks logged", "Record", "Raw ROI", "Process Rating", "Gate status", "Reward pts", "Rules"], lb_rows)}
<p class="note">Slate picks for Nov 13–16 begin grading tonight and count toward G2 samples
(30 picks min). Any strategy revision spawns a new versioned entry — no sample resets.</p>
"""
    page("leaderboard.html", "Leaderboard", body)

    # ---------------- data ----------------
    st_rows = [[r["team"], r["conf"], r["wins"], r["losses"], r["as_of"],
                short(r["source_url"], "source"), r["source_type"], r["verified"]] for r in read("standings-2026-11-13.csv")]
    rt_rows = [[r["team"], r["wins"] + "-" + r["losses"], r["ortg"], r["drtg"], r["nrtg"],
                r["ortg_adj"], r["drtg_adj"], r["nrtg_adj"], short(r["source_url"], "source")] for r in ratings]
    lk_rows = [[r["team"], f"{r['wins']}-{r['losses']}", r["nrtg_adj"], r["expected_wins"],
                r["luck_component_wins"], short(r["source_url"], "source")] for r in luck_sorted]
    body = f"""
<h2>Standings (through games of 2026-11-12)</h2>
{table(["Team", "Conf", "W", "L", "As of", "Source", "Source type", "Verification note"], st_rows)}
<h2>Team ratings (2026-27, schedule-adjusted where suffixed /A)</h2>
{table(["Team", "W-L", "ORtg", "DRtg", "NRtg", "ORtg/A", "DRtg/A", "NRtg/A", "Source"], rt_rows,
       caption="Source: Basketball-Reference 2026-27 Team Ratings (trusted secondary — flagged; Q-1/S-3 covers upgrading to official feeds)")}
<h2>Luck ledger (expected wins from adjusted net rating, logistic /6.8)</h2>
{table(["Team", "Record", "NRtg/A", "Expected wins", "Luck component", "Source"], lk_rows)}
<h2>Season production baselines (verified NBA.com rows)</h2>
{table(["Team", "Player", "PPG", "RPG", "APG", "As of", "Source", "Status"],
       [[p["team"], cell(p["player"]), cell(p["ppg"]), cell(p["rpg"]), cell(p["apg"]),
         cell(p["as_of"]), short(p["source_url"], src_label(p)), p["verified"]]
        for p in read("player-baselines-2026-11-13.csv")])}
"""
    page("data.html", "Data Tables", body)

    # ---------------- suggestions ----------------
    body = """
<h2>Suggestions queue — review and decide before anything is implemented</h2>
<p class="note">Nothing on this list is built until you mark it <b>approved</b>. The full decision table
(with impact/effort columns and the decision log) lives in
<a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/suggestions.md">analysis/suggestions.md</a>
and is mirrored here for review.</p>
<div class="tblwrap"><table>
<caption>Strategy &amp; data suggestions</caption>
<thead><tr><th>ID</th><th>Suggestion</th><th>Why it improves decisions</th><th>Impact</th><th>Effort</th><th>Status</th><th>Decision</th></tr></thead><tbody>
<tr><td>S-1</td><td>Connect a market odds feed (spreads/totals/ML/props)</td><td>unlocks edge, CLV scoring, S5, parlay pricing (Q-1/Q-2)</td><td>very high</td><td>low</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>S-2</td><td>Sign off reward sizing (weekly/monthly/season per leaderboard.md)</td><td>makes the competition real</td><td>high</td><td>decision only</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>S-3</td><td>Backtest calibration of 8 model parameters</td><td>fitted values replace assumptions (Q-3)</td><td>high</td><td>medium</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>S-4</td><td>Full rotation production table (30 teams × top-8)</td><td>fixes worst blind spot (Q-4, e.g. Edwards tiering)</td><td>very high</td><td>medium</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>S-5</td><td>Decide NBA Cup game weighting</td><td>grading policy clarity (9 Cup games tonight)</td><td>medium</td><td>decision only</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>S-6</td><td>Team-specific HCA table</td><td>tighter close-game margins (Q-7)</td><td>medium</td><td>medium</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>S-7</td><td>Daily automation: injury pull + model re-run + site regen</td><td>keeps 3-day window fresh (Q-8)</td><td>high</td><td>medium</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>S-8</td><td>Line-move tracker (snapshot diffs, &gt;2-pt flags)</td><td>line stability as a skill signal</td><td>medium</td><td>low (after S-1)</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>S-9</td><td>Prop market parser + S4 grading loop</td><td>activates prop-combo strategy</td><td>high</td><td>medium (after S-1)</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>S-10</td><td>Bankroll dashboard (Kelly calc, drawdown)</td><td>executes gate G4 mechanically</td><td>medium</td><td>low</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>S-11</td><td>Referee crew tendency tracking</td><td>extra totals signal</td><td>low</td><td>medium</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>S-12</td><td>Public pick-% contrarian signal (S5 input)</td><td>crowd bias pairs with luck ledger</td><td>medium</td><td>low</td><td>proposed</td><td class="dec">awaiting review</td></tr>
</tbody></table></div>
<div class="tblwrap"><table>
<caption>Site UX suggestions</caption>
<thead><tr><th>ID</th><th>Suggestion</th><th>Why</th><th>Status</th><th>Decision</th></tr></thead><tbody>
<tr><td>U-1</td><td>Confidence column on pick tables (provisional / validated / re-run-needed)</td><td>triage speed</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>U-2</td><td>Line snapshot diffs</td><td>see numbers move as injuries land</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>U-3</td><td>CSV download per table</td><td>own analysis off-site</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>U-4</td><td>Dark mode + mobile pass</td><td>comfort</td><td>proposed</td><td class="dec">awaiting review</td></tr>
<tr><td>U-5</td><td>Morning digest (email/JSON webhook)</td><td>decisions happen off-site</td><td>proposed</td><td class="dec">awaiting review</td></tr>
</tbody></table></div>
<h2>Decision workflow</h2>
<ol><li>Read the row and its evidence links.</li>
<li>Set status: <code>approved</code> / <code>rejected</code> / <code>needs-edit</code> (with note).</li>
<li>Approved items are implemented in a later session and linked here; rejected items stay forever — the reasoning trail is part of the product.</li>
<li>New ideas: append S-13… in <a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/suggestions.md">analysis/suggestions.md</a>.</li></ol>
"""
    page("suggestions.html", "Suggestions", body)

    # ---------------- questions ----------------
    body = """
<h2>Questions &amp; missing-information register</h2>
<p class="note">Decision rule: a decision may only rest on <b>known &amp; verified</b> facts.
Unknowns below each carry a discovery plan. Full register:
<a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/questions.md">analysis/questions.md</a>.</p>
<div class="tblwrap"><table>
<thead><tr><th>ID</th><th>Question</th><th>Known today</th><th>Missing</th><th>Discovery plan</th><th>Blocks</th></tr></thead><tbody>
<tr><td>Q-1</td><td>Market lines at pick time &amp; close?</td><td>NBA.com odds toggle exists but numbers are JS-hidden from our tools</td><td>any odds feed</td><td>connect odds API (S-1; needs your key decision) or manual capture</td><td>edge, CLV, S5, parlay pricing</td></tr>
<tr><td>Q-2</td><td>Market player-prop lines?</td><td>our own prop projections exist from verified baselines</td><td>book prop boards</td><td>same feed as Q-1</td><td>S4 grading</td></tr>
<tr><td>Q-3</td><td>Calibrated model parameters?</td><td>formula + assumed values documented</td><td>fitted values</td><td>backtest on historical logs (S-3)</td><td>line confidence</td></tr>
<tr><td>Q-4</td><td>Full rotation production?</td><td>27 verified team leaders</td><td>every rotation player's production</td><td>NBA.com/stats pull or nba_api (S-4)</td><td>injury tiers (Edwards case), prop coverage</td></tr>
<tr><td>Q-5</td><td>Player-specific correlations?</td><td>generic bands + empirical DFS-pair study</td><td>per-player correlations</td><td>play-by-play → rolling pairwise</td><td>prop-combo pricing</td></tr>
<tr><td>Q-6</td><td>Minutes limits / returns?</td><td>official statuses only</td><td>minutes restrictions</td><td>team PR notes at report time (flagged secondary)</td><td>rotation precision</td></tr>
<tr><td>Q-7</td><td>Team-specific HCA?</td><td>league HCA ≈ 2.0 (secondary)</td><td>per-team values</td><td>home/away splits from game logs (S-6)</td><td>close-game margins</td></tr>
<tr><td>Q-8</td><td>Nov 15–16 injury reports?</td><td>through Nov 14 partial only</td><td>game-day reports</td><td>refresh from official index on game days (S-7)</td><td>final Sun/Mon lines (marked PENDING)</td></tr>
<tr><td>Q-9</td><td>NBA Cup weighting policy?</td><td>tonight = 9 Cup games</td><td>your policy</td><td>decision via suggestions (S-5)</td><td>grading only</td></tr>
<tr><td>Q-10</td><td>Bankroll &amp; reward sizing?</td><td>framework drafted</td><td>pool sizes, unit</td><td>your sign-off (S-2)</td><td>payouts</td></tr>
</tbody></table></div>
<h2>Known &amp; verified (foundation)</h2>
<ul>
<li>31-game slate Nov 13–16 with official game IDs —
<a href="https://www.nba.com/games?date=2026-11-13" target="_blank" rel="noopener">nba.com/games</a> per day.</li>
<li>All 30 records cross-checked (NBA.com pages vs
<a href="https://www.basketball-reference.com/leagues/NBA_2027_ratings.html" target="_blank" rel="noopener">Basketball-Reference</a> — agree).</li>
<li>Official injury statuses for all 9 tonight + partial Nov 14 —
<a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf" target="_blank" rel="noopener">official PDF</a>.</li>
<li>Smart suspension — <a href="https://official.nba.com/rockets-smart-suspended" target="_blank" rel="noopener">official release</a>.</li>
<li>Empirical correlation study —
<a href="https://kindoflost.com/2026/09/nba-dfs-correlation-measured/" target="_blank" rel="noopener">505,721 pairs</a>.</li>
</ul>
<h2>Standing unknowns (never silently filled)</h2>
<ul><li>LAL / CHA / TOR season-leader baselines (blank + flagged in data).</li>
<li>Preseason priors / futures market.</li>
<li>Referee assignments.</li>
<li>Historical closing lines (CLV backfill).</li></ul>
"""
    page("questions.html", "Questions", body)

    # ---------------- flagged ----------------
    body = """
<h2>Flagged for Review</h2>
<p class="note">These items are published, linked, and deliberately unresolved. Per policy they
<b>do not block</b> anything. Review and request changes whenever you like — each item maps to a
register entry (Q-n) or suggestion (S-n).</p>
<div class="tblwrap"><table>
<thead><tr><th>#</th><th>Flag</th><th>Detail</th><th>Evidence / source</th><th>Register</th></tr></thead><tbody>
<tr><td>F-1</td><td>Ratings provenance</td><td>Team efficiency values are Basketball-Reference (trusted secondary), not official NBA — sandbox cannot reach NBA stats APIs. Every row labeled.</td><td><a href="https://www.basketball-reference.com/leagues/NBA_2027_ratings.html" target="_blank" rel="noopener">bball-ref ratings</a></td><td>Q-3 / S-3</td></tr>
<tr><td>F-2</td><td>Blank baselines</td><td>LAL, CHA, TOR season-leader rows left blank and flagged (not collected from official source this session).</td><td><a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/player-baselines-2026-11-13.csv">player-baselines CSV</a></td><td>Q-4</td></tr>
<tr><td>F-3</td><td>Key-absence tiering (raised &amp; resolved during build)</td><td>First model run under-charged Haliburton/Banchero/Edwards/Morant/Mobley absences (uncollected baselines). Verified baselines added (Edwards 33.3, Banchero 24.5, Haliburton 21.8 PPG etc.) and lines re-run (NYK −9.5→−11.0, ORL −7.5→−4.0, MIN −28.0→−25.0). Residual: non-star rotation players still tiered as unknown (Q-4 continues).</td><td><a href="https://www.basketball-reference.com/leagues/NBA_2027_per_game.html" target="_blank" rel="noopener">BRef per-game</a> · <a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf" target="_blank" rel="noopener">official report</a></td><td>Q-4 (partially resolved)</td></tr>
<tr><td>F-4</td><td>Nov 15–16 picks PENDING</td><td>Official injury reports for Sun/Mon not yet published at snapshot; those lines are injury-unadjusted by design.</td><td><a href="https://official.nba.com/nba-injury-report-2026-27-season/" target="_blank" rel="noopener">official injury index</a></td><td>Q-8</td></tr>
<tr><td>F-5</td><td>Correlation evidence mix</td><td>15 of 21 matrix rows are industry range estimates; only 6 are empirical. Treated as priors pending our own history.</td><td><a href="https://kindoflost.com/2026/09/nba-dfs-correlation-measured/" target="_blank" rel="noopener">empirical study</a></td><td>Q-5</td></tr>
<tr><td>F-6</td><td>Secondary rest-context sources</td><td>Nov 12 scores (used only for rest/B2B flags) come from CBS/AP and nba-grid, not NBA.com.</td><td><a href="https://www.cbssports.com/nba/gametracker/boxscore/NBA_20261112_TOR@PHI/" target="_blank" rel="noopener">CBS/AP</a></td><td>—</td></tr>
<tr><td>F-7</td><td>Model parameters uncalibrated</td><td>HCA 2.0, impact tiers 4.0/2.0/0.8, fatigue values, defense scalar 0.35, logistic divisor 6.8 are documented assumptions.</td><td><a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/strategy/model.md">model.md</a></td><td>Q-3</td></tr>
<tr><td>F-8</td><td>No market lines</td><td>Edge vs market, CLV, and reward payouts cannot activate until a feed exists. Picks are "make at our number" only.</td><td><a href="https://github.com/wingbangboozle1-lang/NBA2/blob/main/analysis/questions.md">questions.md Q-1</a></td><td>Q-1 / S-1</td></tr>
<tr><td>F-9</td><td>PHI luck outlier (context flag)</td><td>PHI 10-3 vs 5.8 expected wins (+4.2 luck). Not an error — a caution against trusting records blindly.</td><td><a href="https://www.basketball-reference.com/leagues/NBA_2027_ratings.html" target="_blank" rel="noopener">ratings source</a></td><td>luck ledger</td></tr>
</tbody></table></div>
"""
    page("flagged.html", "Flagged for Review", body)

    # ---------------- sources ----------------
    srcs = {}
    for fname, rows in [("games.csv", games), ("standings-2026-11-13.csv", read("standings-2026-11-13.csv")),
                        ("team-ratings-2026-11-13.csv", ratings), ("injury-report-2026-11-13.csv", injuries),
                        ("player-baselines-2026-11-13.csv", read("player-baselines-2026-11-13.csv")),
                        ("correlation-matrix.csv", corr), ("recent-games.csv", read("recent-games.csv")),
                        ("our-lines.csv", read("our-lines.csv")), ("picks.csv", picks),
                        ("luck-table.csv", luck)]:
        for r in rows:
            u = r.get("source_url") or r.get("baseline_source") or ""
            if u:
                srcs.setdefault(u, {"type": r.get("source_type", ""), "files": set()})["files"].add(fname)
    type_map = {
        "official": "official (NBA)", "trusted secondary": "trusted secondary",
    }
    srows = []
    for u in sorted(srcs):
        info = srcs[u]
        t = info["type"] or ("official (NBA)" if ("nba.com" in u) else "trusted secondary")
        srows.append([link(u), type_map.get(t, t), ", ".join(sorted(info["files"]))])
    body = f"""
<h2>Source registry</h2>
<p class="note">Every URL below is cited by at least one data row in the repository.
Policy: official NBA sources preferred; trusted-secondary sources are labeled in-place and
listed on the <a href="flagged.html">Flagged page</a> where used for core numbers.</p>
{table(["URL", "Type", "Used by data files"], srows)}
"""
    page("sources.html", "Sources", body)

    # css
    with open(os.path.join(OUT, "styles.css"), "w", encoding="utf-8") as f:
        f.write(CSS)
    print(f"built {len(NAV)} pages + styles.css into dashboard/")


CSS = """
:root{--bg:#0f1420;--panel:#171e2e;--ink:#e8ecf4;--mut:#9aa7bd;--acc:#4da3ff;--ok:#37c978;--warn:#ffb84d;--bad:#ff6b6b;--line:#263149}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:0 18px}header{background:var(--panel);border-bottom:1px solid var(--line);padding:18px 0 0}
header h1{margin:0 0 4px;font-size:22px;letter-spacing:.2px}header .sub{color:var(--mut);font-size:13px;font-weight:400}
.snap{color:var(--mut);font-size:12px;margin:2px 0 12px}nav{display:flex;flex-wrap:wrap;gap:2px}
nav a{color:var(--ink);text-decoration:none;padding:8px 12px;border-radius:8px 8px 0 0;font-size:13.5px}
nav a:hover{background:#1f2a40}nav a.active{background:var(--acc);color:#06121f;font-weight:600}
main{padding:22px 0 40px}h2{font-size:18px;margin:28px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
h2 small{color:var(--mut);font-weight:400;font-size:12.5px}p,li{color:var(--ink)}a{color:var(--acc)}
code,pre{background:#111827;border:1px solid var(--line);border-radius:6px}code{padding:1px 5px;font-size:12.5px}
pre{padding:12px;overflow-x:auto;font-size:12.5px}
.note{background:var(--panel);border-left:3px solid var(--acc);padding:10px 14px;border-radius:0 8px 8px 0;font-size:13.5px;color:var(--mut)}
.note b,.note strong{color:var(--ink)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:6px 0 10px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.card b{display:block;font-size:26px;color:var(--acc)}.card.warn b{color:var(--warn)}.card span{color:var(--mut);font-size:12.5px}
.tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:10px 0 18px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:13px}caption{caption-side:top;text-align:left;padding:10px 12px;color:var(--mut);font-size:12.5px}
th{background:#1c2539;color:var(--mut);text-align:left;font-weight:600;padding:9px 10px;position:sticky;top:0}
td{padding:8px 10px;border-top:1px solid var(--line);vertical-align:top}tr:hover td{background:#1b2436}
.tiny{color:var(--mut);font-size:11.5px}.flag{color:var(--bad)}.ok{color:var(--ok)}em{color:var(--mut)}
.dec{color:var(--warn);font-style:italic}footer{border-top:1px solid var(--line);color:var(--mut);font-size:12px;padding:16px 0 26px}
footer a{color:var(--mut)}ol,ul{padding-left:20px}
"""


if __name__ == "__main__":
    main()
