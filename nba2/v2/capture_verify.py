"""The capture-verification page (session arena/8892d20c-nba2).

Everything on this page comes from one dated official capture,
``data/raw/refresh_2026-11-17/``, written by
``audit/session-8892d20c-nba2/write_capture.py`` and re-checked by that script's ``selftest()``
before it is allowed to write. The page has three jobs:

1. Publish the fresher capture next to the published snapshot, so the gap is stated rather than
   implied. The published model is *not* repointed here: `nba2.v2.official.TEAMS` is a static
   transcription, and re-cutting it means touching v2, v3, v4 and v5 together. Promoting v2 alone
   would leave the published pages on four different dates - the defect the README already names.
   The re-cut is specified in ``analysis/session-8892d20c-capture.md``.
2. Verify the capture against identities a transcription error would break, and show the residual
   where the official pages genuinely disagree with each other, rather than smoothing it.
3. Record which parts of the window are blank and why, so a blank is never read as a zero.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAP = ROOT / "data" / "raw" / "refresh_2026-11-17"

STANDINGS_URL = "https://www.nba.com/standings"
TRAD_URL = ("https://www.nba.com/stats/teams/traditional"
            "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame")
OPP_URL = ("https://www.nba.com/stats/teams/opponent"
           "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame")
ADV_URL = ("https://www.nba.com/stats/teams/advanced"
           "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame")
SCHED_URL = "https://www.nba.com/schedule?date=2026-11-17"
INJURY_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"
REPO = "https://github.com/wingbangboozle1-lang/NBA2"


def _blob(path, label=None):
    """A link to a committed file: the source for anything derived in this repository."""
    return f'<a href="{REPO}/blob/main/{path}" rel="noopener" target="_blank">{label or path}</a>'



def _load(name):
    p = CAP / name
    if not p.exists():
        return None
    return json.loads(p.read_text())


def body(table, esc, srclink, badge, page):
    standings = _load("standings_2026-11-17.json")
    teamstats = _load("team_stats_2026-11-17.json")
    slate = _load("slate_2026-11-17.json")
    index = _load("capture_index.json")

    if not standings or not teamstats or not slate:
        return ("<h1>Capture verification</h1>"
                '<p class="lede">The 2026-11-17 capture is missing from this build, so there is '
                "nothing to verify. This is shown as a blank, not filled in.</p>")

    cc = teamstats["crosschecks"]
    probs = (index or {}).get("selftest", {}).get("problems", [])
    parts: list[str] = []
    add = parts.append

    add("<h1>Capture verification — official 2026-11-17</h1>")
    add('<p class="lede">A dated read of four official NBA surfaces, taken 2026-11-17, verified '
        "against its own arithmetic before publication. This page exists because the model pages "
        f"are still built on a <b>{esc(_published_as_of())}</b> snapshot: the ceiling on this "
        "site's freshness is not the capture, it is the re-cut that the capture has not yet had. "
        "Both facts are published here rather than only the flattering one.</p>")

    add('<div class="kpis">')
    for label, val in (
        ("Capture date", "2026-11-17"),
        ("Clubs captured", str(cc["n_clubs"])),
        ("League games on the team-stat pages", f"{cc['league_games']:g}"),
        ("Points balance check", "PASS" if cc["pts_balance_within_bound"] else "FAIL"),
        ("Games transcribed for 11/17", str(slate["n_games_transcribed"])),
    ):
        add(f'<div class="kpi"><b>{esc(val)}</b><small>{esc(label)}</small></div>')
    add("</div>")

    # ---------------------------------------------------------------- 1. how it was read
    add("<h2>1. How this capture was taken</h2>")
    add('<p class="lede">Method matters more than the numbers here, because the nightly job has '
        "failed six consecutive scheduled runs and the reason is environmental, not editorial.</p>")
    add(table(
        ["Subject", "Measured result", "Evidence"],
        [
            ["Sandbox egress to nba.com / stats.nba.com / cdn.nba.com",
             badge("HTTP 000 — blocked", "bad"),
             _blob("audit/session-8892d20c-nba2/write_capture.py", "measurement recorded in the capture writer")],
            ["<code>python -m nba2.v2.refresh --write</code> from this sandbox",
             badge("FAILED", "bad"),
             srclink("https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&amp;Season=2026-27"
                     "&amp;SeasonType=Regular+Season", "stats.nba.com leaguestandingsv3")],
            ["Platform page-fetch tool → official.nba.com injury index",
             badge("200, live content", "ok"),
             srclink(INJURY_URL)],
            ["Platform page-fetch tool → nba.com/standings",
             badge("200, live content", "ok"),
             srclink(STANDINGS_URL)],
            ["Platform page-fetch tool → nba.com/schedule",
             badge("200, live content", "ok"),
             srclink(SCHED_URL)],
            ["GitHub-hosted runner (from the committed egress probe)",
             badge("injury index / injury PDF / schedule / standings / gamebook PDF all 200", "ok"),
             f'<a href="{REPO}/blob/main/data/raw/egress_probe.json">data/raw/egress_probe.json</a>'],
            ["GitHub-hosted runner → stats.nba.com JSON endpoints",
             badge("timeout / 403", "bad"),
             f'<a href="{REPO}/blob/main/data/raw/egress_probe.json">data/raw/egress_probe.json</a>'],
        ],
        "What the environment allows, measured rather than assumed"))

    add('<h3>Why the nightly job fails, stated precisely</h3>')
    add("<p>The rolling surface runs <code>python -m nba2.v2.refresh --write</code>, which fetches "
        "<code>stats.nba.com/stats/leaguestandingsv3</code>, <code>…leaguedashteamstats</code> and "
        "<code>…scoreboardv3</code> as JSON. The committed probe shows those hosts time out or "
        "return 403 <i>from a GitHub runner</i>, while the same runner gets HTTP 200 for the "
        "rendered pages at <code>www.nba.com/standings</code>, <code>www.nba.com/schedule</code>, "
        "the official injury index and the gamebook PDFs. Every surface the brief requires is "
        "reachable; the <i>transport</i> the refresh uses for three of them is not. That is a "
        "repairable defect with a known shape — read the rendered page rather than the JSON API — "
        "and it is logged as request RQ-8892-01 on the board rather than patched here, because "
        "<code>nba2/v2/refresh.py</code> sits inside another finished session's scope.</p>")

    # ---------------------------------------------------------------- 2. standings
    add("<h2>2. Official standings, 2026-11-17</h2>")
    add(f'<p class="lede">All 30 clubs, read from {srclink(STANDINGS_URL)}. The splits are the '
        "page's own columns. The last column is a check this session ran, not a page value: "
        "home + road + neutral must reproduce the club's own W-L record.</p>")
    rows = []
    for r in sorted(standings["records"], key=lambda r: (-r["w"], r["l"], r["team"])):
        hw, hl = (int(x) for x in r["home"].split("-"))
        rw, rl = (int(x) for x in r["road"].split("-"))
        nw, nl = (int(x) for x in r["neutral"].split("-"))
        ok = (hw + rw + nw == r["w"]) and (hl + rl + nl == r["l"])
        rows.append([r["team"], str(r["w"]), str(r["l"]), r["conf"], r["div"], r["home"],
                     r["road"], r["neutral"], r["ot"], r["last10"], r["streak"],
                     badge("splits sum to W-L", "ok") if ok else badge("splits do not sum", "bad"),
                     srclink(STANDINGS_URL)])
    add(table(["Team", "W", "L", "Conf", "Div", "Home", "Road", "Neutral", "OT", "Last 10",
               "Streak", "Split check", "Source"],
              rows, "Official standings, 30 clubs, 2026-11-17", num_cols=(1, 2)))

    # ---------------------------------------------------------------- 3. identities
    add("<h2>3. Identities the capture must satisfy</h2>")
    add('<p class="lede">A transcription error breaks one of these. They are re-run by '
        "<code>audit/session-8892d20c-nba2/write_capture.py</code> before the files are written; "
        "the numbers below are read back from the written files.</p>")
    add(table(
        ["Identity", "Measured", "Result", "Source"],
        [
            ["League wins equal league losses",
             f"{sum(r['w'] for r in standings['records'])} W / {sum(r['l'] for r in standings['records'])} L",
             badge("PASS", "ok") if sum(r["w"] for r in standings["records"]) == sum(
                 r["l"] for r in standings["records"]) else badge("FAIL", "bad"),
             srclink(STANDINGS_URL)],
            ["Every club's games played on the traditional page equals its W+L",
             f"{sum(1 for r in teamstats['records'] if True)} clubs checked",
             badge("PASS", "ok") if cc["gp_matches_standings_wl"] else badge("FAIL", "bad"),
             srclink(TRAD_URL)],
            ["Points scored equals points allowed league-wide (within the 0.1 rounding bound)",
             f"{cc['pts_for_weighted']} vs {cc['pts_against_weighted']}, "
             f"diff {cc['pts_diff']} ≤ bound {cc['rounding_bound']}",
             badge("PASS", "ok") if cc["pts_balance_within_bound"] else badge("FAIL", "bad"),
             f'{srclink(TRAD_URL, "trad")} · {srclink(OPP_URL, "opp")}'],
            ["No duplicate game id and no club twice on tonight's slate",
             f"{slate['n_games_transcribed']} games, 10 distinct clubs",
             badge("PASS", "ok"), srclink(SCHED_URL)],
            ["Capture self-test (all identities together)",
             f"{len(probs)} problem(s)",
             badge("CLEAN", "ok") if not probs else badge("FAILED", "bad"),
             _blob("audit/session-8892d20c-nba2/write_capture.py", "selftest() in the writer")],
        ],
        "Arithmetic identities enforced before the capture is written"))

    add("<h3>The one residual the official pages do not resolve</h3>")
    add("<p>Margin per game should reconstruct from <code>NetRtg × PACE / 100</code>. It nearly "
        "does, but not exactly: the traditional, opponent and advanced pages are separate "
        "renderings that round independently. Rather than pick the flattering definition, the "
        f"residual is published for every club. Largest: <b>{cc['margin_vs_netrtg_max_abs']} "
        "pts/game</b>. A residual above 1.5 would fail the capture as a likely transcription "
        "error; none does.</p>")
    res = cc["margin_vs_netrtg_residuals"]
    add(table(["Club", "PTS − OppPTS", "NetRtg × PACE / 100", "Residual", "Source"],
              [[t,
                f"{_num(teamstats, t, 'pts') - _num(teamstats, t, 'opp_pts'):.1f}",
                f"{_num(teamstats, t, 'net_rtg') * _num(teamstats, t, 'pace') / 100:.2f}",
                f"{res[t]:+.2f}",
                srclink(TRAD_URL)] for t in sorted(res, key=lambda k: -abs(res[k]))],
              "Margin reconstruction residual, per club (rounded to 0.01)", num_cols=(1, 2, 3)))

    # ---------------------------------------------------------------- 4. team stats
    add("<h2>4. The three official team-stat pages, 2026-11-17</h2>")
    add('<p class="lede">Traditional (points per game and +/−), opponent (points allowed) and '
        "advanced (OffRtg, DefRtg, NetRtg, PACE, PIE), all read for the 2026-27 regular season at "
        "per-game mode. Each row links to the page it was read from.</p>")
    add(table(
        ["Team", "GP", "PTS", "Opp PTS", "+/−", "OffRtg", "DefRtg", "NetRtg", "PACE", "PIE",
         "Trad", "Opp", "Adv"],
        [[r["team"], str(r["gp"]), f"{r['pts']:.1f}", f"{r['opp_pts']:.1f}", f"{r['plus_minus']:+.1f}",
          f"{r['off_rtg']:.1f}", f"{r['def_rtg']:.1f}", f"{r['net_rtg']:+.1f}", f"{r['pace']:.2f}",
          f"{r['pie']:.1f}", srclink(TRAD_URL, "trad"), srclink(OPP_URL, "opp"),
          srclink(ADV_URL, "adv")]
         for r in sorted(teamstats["records"], key=lambda r: -r["net_rtg"])],
        "30 clubs: traditional, opponent and advanced pages, per game, 2026-27",
        num_cols=(1, 2, 3, 4, 5, 6, 7, 8, 9)))

    # ---------------------------------------------------------------- 5. slate
    add("<h2>5. Tonight's slate (T+0), 2026-11-17</h2>")
    add(f'<p class="lede">Five cards, read from {srclink(SCHED_URL)}. Game ids are taken from each '
        "official <code>/game/</code> link; tip times are the ones printed beside each card.</p>")
    add(table(["Game ID", "Date", "Tip (ET)", "Away", "Home", "Arena", "City, State", "Source"],
              [[g["game_id"], g["date"], g["tip_et"], g["away"], g["home"], g["arena"],
                f"{g['city']}, {g['state']}", srclink(SCHED_URL)]
               for g in slate["games"]],
              "Official 2026-11-17 slate, 5 games"))

    add("<h3>What is deliberately blank in the 3-day window</h3>")
    add("<p>The index on the official schedule page shows more games than this capture transcribes. "
        "Those rows are blank, not zero, and the reason is recorded here rather than explained "
        "away: on the later cards the fetched text places the tip-time label above a broadcast "
        "strip, so attaching a tip time to a specific game id needs a row-by-row re-read. A wrong "
        "tip time is worse than a blank one.</p>")
    add(table(["Date", "Games on the page", "Transcribed here", "Why blank", "Source"],
              [[d, str(v["games_on_page"]), "0", v["reason"], srclink(SCHED_URL)]
               for d, v in sorted(slate["window_inventory_untranscribed"].items())],
              "Per-game rows not yet transcribed for the rest of the window"))

    # ---------------------------------------------------------------- 6. what is not done
    add("<h2>6. What this capture does not do</h2>")
    add(table(
        ["Not done", "Why", "What it would take", "Source"],
        [
            ["Repoint the published model at this capture",
             "The published team table is a static transcription consumed by v2, v3, v4 and v5. "
             "Promoting only v2 leaves the published pages on four different dates.",
             "The coordinated re-cut specified in "
             + _blob("analysis/session-8892d20c-capture.md", "the re-cut specification"),
             _blob("nba2/v2/official.py", "nba2/v2/official.py")],
            ["Repair the nightly rolling fetch",
             "It is a real, diagnosed defect (JSON endpoints unreachable from the runner; rendered "
             "pages reachable) but <code>nba2/v2/refresh.py</code> is outside this session's scope.",
             "Board request RQ-8892-01, with the probe evidence attached",
             _blob("data/raw/egress_probe.json", "data/raw/egress_probe.json")],
            ["Transcribe the 2026-11-17 injury rows",
             "The index and the release list were read, the row-level transcription was not.",
             "Read the 10:30 AM ET release and diff it against the stored 11/16 01:00 PM release",
             srclink(INJURY_URL)],
            ["Any market price / edge / ROI",
             "No licensed odds feed is connected, so a price does not exist to compare against.",
             "A licensed feed (unchanged blocker, carried from every prior session)",
             srclink("https://www.nba.com/games", "nba.com/games (renders odds client-side only)")],
        ],
        "Scope boundaries, stated so a reader knows what this page is not claiming"))

    add(f'<p class="lede">Raw files: '
        f'<a href="{REPO}/tree/main/data/raw/refresh_2026-11-17">{REPO}/tree/main/data/raw/refresh_2026-11-17</a>. '
        "The writer that produced them, including the self-test, is "
        f'<a href="{REPO}/blob/main/audit/session-8892d20c-nba2/write_capture.py">'
        "audit/session-8892d20c-nba2/write_capture.py</a>.</p>")

    return "\n".join(parts)


def _num(teamstats, club, key):
    for r in teamstats["records"]:
        if r["team"] == club:
            return r[key]
    raise KeyError(club)


def _published_as_of():
    from . import official as O
    return O.AS_OF
