"""Insert the strategy-lab page into nba2/v2/build.py (session arena/ac5fab5c-nba2)."""
import pathlib

P = pathlib.Path("nba2/v2/build.py")
s = P.read_text()

ANCHOR = '    built["backtest.html"] = page("backtest.html", "Backtest &amp; skill", body, "backtest.html")\n'
assert ANCHOR in s

PAGE = ANCHOR + '''
    # ------------------------------------------------------------------ strategy lab
    labm = lab["meta"]
    ng_pass = sum(1 for g in lab["gates"] if g["verdict"] == "PASS")
    ng_fail = sum(1 for g in lab["gates"] if g["verdict"] == "FAIL")
    sig = [r for r in lab["luck"]["rows"] if r["verdict"] == "DISTINGUISHABLE FROM CHANCE"]
    small = [r for r in lab["luck"]["rows"] if "SAMPLE TOO SMALL" in r["verdict"]]
    body = f""\"<h1>Strategy lab</h1>
<p class="lede">Seven candidate strategies, each scored walk-forward over {labm['n_scored']} predictions built from the
{labm['n_games']} official finals in this repository ({labm['first_date']} → {labm['last_date']}). Twelve validation gates,
each evaluated from the data rather than asserted. Then the part that matters most: how much of every record is luck.</p>

<div class="kpis">
  <div class="kpi"><b>{labm['n_games']}</b><small>official finals captured</small></div>
  <div class="kpi"><b>{labm['n_scored']}</b><small>predictions scored walk-forward</small></div>
  <div class="kpi"><b>{ng_pass} / {len(lab['gates'])}</b><small>gates passing ({ng_fail} failing)</small></div>
  <div class="kpi"><b>{len(sig)}</b><small>strategies distinguishable from chance</small></div>
  <div class="kpi"><b>{len(small)}</b><small>sample too small to call</small></div>
  <div class="kpi"><b>0</b><small>strategies ranked for reward</small></div>
</div>

<div class="note bad"><b>Nothing on this page is a bet, and nothing is ranked.</b> Two gates fail outright: G6, because
no market price is connected, and G7, because the largest settled sample here is {max((s.get('n') or 0) for s in lab['strategies'])} bets
against a 300-bet bar. Until those pass, the leaderboard is a scoring exercise, not a competition, and the reward pool
stays unfunded. That is a deliberate design choice: a leaderboard that can be topped by a lucky 7-0 run is worse than
no leaderboard.</div>

<h2>1. The strategies</h2>
<p class="lede">Each rule is written so it could be run by someone else tomorrow and get the same answer. "Lean" means
the signal; none of them carries a stake.</p>
""\"
    srows = []
    for st in lab["strategies"]:
        kind = {"single bet": "ok", "parlay": "warn", "player prop combo": "bad"}.get(st["kind"], "off")
        n = st.get("n", 0)
        srows.append({"cells": [
            "<b>" + esc(st["sid"]) + "</b>",
            esc(st["name"]),
            badge(st["kind"], kind),
            esc(n) if n else '<span class="blank">0 — inputs unavailable</span>',
            esc(st["hit_rate"]) if n else '<span class="blank">—</span>',
            esc(st["wilson95"][0]) if n else '<span class="blank">—</span>',
            esc(st["wilson95"][1]) if n else '<span class="blank">—</span>',
            esc(st["log_loss"]) if n else '<span class="blank">—</span>',
            esc(st["brier"]) if n else '<span class="blank">—</span>',
            esc(st["rule"]),
        ]})
    body += table(["ID", "Strategy", "Type", "Bets", "Hit rate", "95% low", "95% high", "Log-loss", "Brier", "Rule"],
                  srows, "Every candidate strategy, scored on the same walk-forward sample",
                  num_cols=(3, 4, 5, 6, 7, 8))

    body += ""\"<h2>2. The validation gates, evaluated</h2>
<p class="lede">A gate that is never checked is decoration. Each row below is the number this build actually
measured, with the threshold it was measured against.</p>
""\"
    grows = []
    for g in lab["gates"]:
        kind = {"PASS": "ok", "FAIL": "bad"}.get(g["verdict"], "warn")
        grows.append({"cells": [
            "<b>" + esc(g["id"]) + "</b>", esc(g["name"]), esc(g["requirement"]),
            badge(g["verdict"], kind), esc(g["measured"]), srclink(g["src"]),
        ]})
    body += table(["Gate", "Name", "Requirement", "Verdict", "What was measured", "Source"],
                  grows, f"{ng_pass} of {len(lab['gates'])} gates pass on this build")

    body += f""\"<h3>Out-of-sample holdout (G8)</h3>
<p>Built on the first {int((1-labm['holdout_fraction'])*100)}% of game-dates, scored on the last
{int(labm['holdout_fraction']*100)}%. {esc(lab['holdout']['note'])}</p>

<h3>No-look-ahead audit (G12)</h3>
<p>{esc(lab['leakage']['verdict'])} across {lab['leakage']['n_predictions']} predictions. The rule is mechanical:
ratings for a date are built only from games with a strictly earlier date, so no prediction can see its own result or
any later one.</p>
""\"

    body += ""\"<h2>3. Correlation values</h2>
<p class="lede">Every parlay price depends on one of these. The ones that cannot be measured are named, with the
dataset that would unblock them, rather than filled with a plausible number.</p>
""\"
    crows = []
    for c in lab["correlations"]:
        st = c["status"]
        kind = {"MEASURED": "ok", "BLOCKED": "bad"}.get(st, "off")
        crows.append({"cells": [
            esc(c["quantity"]),
            badge(st, kind),
            esc(c["n"]) if c["n"] else '<span class="blank">—</span>',
            esc(c["r"]) if c["r"] is not None else '<span class="blank">unmeasured</span>',
            esc(c["ci95"][0]) if c["ci95"] else '<span class="blank">—</span>',
            esc(c["ci95"][1]) if c["ci95"] else '<span class="blank">—</span>',
            esc(c["p_two_sided"]) if c["p_two_sided"] is not None else '<span class="blank">—</span>',
            esc("yes" if c["significant_at_5pct"] else "no") if st == "MEASURED"
            else '<span class="blank">—</span>',
            esc(c["note"]),
        ]})
    body += table(["Quantity", "Status", "n", "r", "95% low", "95% high", "p", "Significant", "Reading"],
                  crows, "Measured correlations and the ones that remain blocked",
                  num_cols=(2, 3, 4, 5, 6))

    pp = lab["parlay_pricing"]
    if pp.get("status") == "MEASURED":
        body += f""\"<h3>What the same-game correlation does to a two-leg price</h3>
<p>The measured same-game correlation is <b>{pp['measured_rho']:+.4f}</b>
(95% CI {pp['rho_ci95'][0]:+.4f} to {pp['rho_ci95'][1]:+.4f}, n = {pp['n']}). Below is what that does to a joint
price, computed as a bivariate-normal quadrant — the arithmetic a book actually uses.</p>
""\"
        prows = []
        for r in pp["rows"]:
            prows.append({"cells": [
                esc(r["legs"]), esc(r["p_leg_1"]), esc(r["p_leg_2"]),
                esc(r["naive_product"]), "<b>" + esc(r["joint_at_measured_rho"]) + "</b>",
                esc(r["joint_at_ci_low"]), esc(r["joint_at_ci_high"]),
                esc(r["error_pct"]), esc(r["fair_decimal_if_naive"]),
                esc(r["fair_decimal_at_measured"]),
            ]})
        body += table(["Legs", "P(leg 1)", "P(leg 2)", "Naive product", "Joint at measured ρ",
                       "Joint at CI low", "Joint at CI high", "Error if you multiply (%)",
                       "Fair dec (naive)", "Fair dec (measured)"],
                      prows, "Two-leg same-game prices across the measured correlation band",
                      num_cols=(1, 2, 3, 4, 5, 6, 7, 8, 9))
        body += f""\"<div class="note warn"><b>How to read this.</b> {esc(pp['reading'])}</div>""\"

    body += ""\"<h2>4. Luck versus skill</h2>
<p class="lede">A hit rate without an interval is an anecdote. Every strategy below is tested against the rate it
must beat — a coin flip for a single bet, its own printed price for a parlay — and the verdict says whether the
result is distinguishable from that.</p>
""\"
    lrows = []
    for r in lab["luck"]["rows"]:
        if not r.get("n"):
            lrows.append({"cells": [
                "<b>" + esc(r["sid"]) + "</b>", esc(r["name"]),
                '<span class="blank">0</span>', '<span class="blank">—</span>',
                '<span class="blank">—</span>', '<span class="blank">—</span>',
                '<span class="blank">—</span>', '<span class="blank">—</span>',
                badge("NO BETS", "bad"), esc(r["reason"]),
            ]})
            continue
        verdict = r["verdict"]
        kind = ("ok" if verdict == "DISTINGUISHABLE FROM CHANCE"
                else "bad" if verdict == "NO BETS GENERATED"
                else "warn")
        lrows.append({"cells": [
            "<b>" + esc(r["sid"]) + "</b>", esc(r["name"]), esc(r["n"]), esc(r["hit_rate"]),
            f"{r['wilson95'][0]} – {r['wilson95'][1]}",
            esc(r["base_rate"]) + f" ({esc(r['base_rate_meaning'])})",
            esc(r["p_vs_base"]),
            "yes" if r["interval_contains_base"] else "no",
            badge(verdict, kind),
            esc(f"{r['games_to_prove_at_this_rate']} bets needed" if r["games_to_prove_at_this_rate"]
                else "interval already excludes the base rate" if not r["interval_contains_base"]
                else "cannot be decided at this sample"),
        ]})
    body += table(["ID", "Strategy", "Bets", "Hit rate", "95% interval", "Must beat", "p",
                   "Interval contains base?", "Verdict", "What it would take"],
                  lrows, "Binomial tests against the base rate each strategy must beat",
                  num_cols=(2, 3, 6))

    body += ""\"<div class="note warn"><b>The trap on this table.</b> S4 is 7 for 7 — a 100% record, and a binomial
p-value of 0.016 that would pass a naive significance test. It is still not evidence of skill: at seven bets the
interval is wide enough to hold almost any true rate, which is exactly why the verdict column reads
"samples too small to call" and why the leaderboard refuses to rank it. A record this short is what luck looks like
when it is winning.</div>

<h2>5. The leaderboard</h2>
<p class="lede">Ranked by log-loss, which is a proper scoring rule: it rewards honest probabilities rather than
lucky ones. Nothing is eligible for a reward while a blocking gate fails.</p>
""\"
    lb = lab["leaderboard"]
    brows = []
    for r in lb["ranked"]:
        brows.append({"cells": [
            esc(r["rank_by_log_loss"]), "<b>" + esc(r["sid"]) + "</b>", esc(r["name"]),
            esc(r["kind"]), esc(r["n"]), esc(r["hit_rate"]), esc(r["log_loss"]),
            esc(r["brier"]), esc(r["auroc"]), esc(r["calibration_gap"]),
            badge("ELIGIBLE" if r["eligible_for_reward"] else "BLOCKED",
                  "ok" if r["eligible_for_reward"] else "bad"),
            esc(r["blocked_by"]),
        ]})
    body += table(["Rank", "ID", "Strategy", "Type", "Bets", "Hit rate", "Log-loss", "Brier",
                   "AUROC", "Calibration gap", "Reward", "Blocked by"],
                  brows, f"Ranked by log-loss; minimum sample to rank is {lb['min_sample_to_rank']} settled bets",
                  num_cols=(4, 5, 6, 7, 8, 9))

    body += f""\"<h3>Reward pool</h3>
<p>{esc(lb['reward_pool']['total_units'])} units: {esc(lb['reward_pool']['allocation'])}.</p>
<div class="note bad"><b>{esc(lb['reward_pool']['status'])}</b></div>

<h3>Competition rules</h3>
""\"
    rrows = []
    for (k, v, why, basis, src) in C.LEADERBOARD_RULES:
        rrows.append({"cells": [esc(k), esc(v), esc(why), badge(basis, "warn" if "PROPOSED" in basis else "info"),
                                srclink(src)]})
    body += table(["Rule", "Setting", "Why", "Basis", "Source"], rrows,
                  "How the leaderboard is scored and what disqualifies a submission")

    body += ""\"<h2>6. What would move a strategy onto the board</h2>
<ol>
  <li><b>A dated market price (G6).</b> One odds feed with timestamps turns every projection on this site into a
  testable claim. Nothing else on this list matters as much.</li>
  <li><b>More settled bets (G7).</b> The bar is 300. The largest sample here is 167, and the season produces roughly
  12 games a day, so the bar is reachable inside a season rather than in years.</li>
  <li><b>Per-player game logs.</b> Unblocks S7 and every prop-combo correlation on the correlations table. These are
  the only correlations on this site still listed as blocked for lack of data rather than lack of power.</li>
</ol>
""\"
    built["strategy-lab.html"] = page("strategy-lab.html", "Strategy lab", body, "strategy-lab.html")
'''

s = s.replace(ANCHOR, PAGE, 1)
P.write_text(s)
print("inserted strategy-lab page")
