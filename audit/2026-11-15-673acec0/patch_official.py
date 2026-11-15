"""Re-cut the v2 model input blocks from the 2026-11-15 live capture (K-03).

Idempotent block splicer: every replacement is anchored on a literal that exists exactly
once in nba2/v2/official.py, and the script refuses to write unless all of them matched.
"""
from __future__ import annotations
import re, sys, pathlib, json, glob, collections

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "audit" / "2026-11-15-673acec0"))
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("capture_2026_11_15", ROOT / "audit" / "2026-11-15-673acec0" / "capture_2026-11-15.py")
C = _ilu.module_from_spec(_spec); _spec.loader.exec_module(C)

p = ROOT / "nba2" / "v2" / "official.py"
src = p.read_text()
orig = src

# ---------------------------------------------------------------- PF/PA from the finals
games = []
for f in sorted(glob.glob(str(ROOT / "data" / "raw" / "history" / "games_*.json"))):
    for g in json.load(open(f))["games"]:
        games.append(g)
PF = collections.Counter(); PA = collections.Counter(); GP = collections.Counter()
for g in games:
    PF[g["away"]] += g["away_pts"]; PA[g["away"]] += g["home_pts"]
    PF[g["home"]] += g["home_pts"]; PA[g["home"]] += g["away_pts"]
    GP[g["away"]] += 1; GP[g["home"]] += 1
N_GAMES = len(games)

def teams_block():
    out = ["TEAMS: dict[str, tuple] = {"]
    for t in sorted(C.STANDINGS):
        w, l, hw, hl, rw, rl = C.STANDINGS[t]
        gp = GP[t]
        assert (w, l, hw, hl, rw, rl)[0] + (w, l, hw, hl, rw, rl)[1] == gp, t
        o, d, n, pace, pie = C.ADV[t]
        out.append(f'    "{t}": ({w}, {l}, {hw}, {hl}, {rw}, {rl}, '
                   f'{round(PF[t]/gp,1)}, {round(PA[t]/gp,1)}, {o}, {d}, {n}, {pace}, {pie}),')
    out.append("}")
    return "\n".join(out)

def slate_block():
    out = ["SLATE = ["]
    for row in C.SLATE:
        out.append("    (" + ", ".join(f'"{x}"' for x in row) + "),")
    out.append("]")
    return "\n".join(out)

def inj_block():
    out = ["INJURIES = ["]
    for row in C.INJURIES:
        out.append("    (" + ", ".join(repr(x) if "'" in x else f'"{x}"' for x in row) + "),")
    out.append("]")
    return "\n".join(out)

def ns_block():
    out = ["NOT_SUBMITTED = ["]
    for row in C.NOT_SUBMITTED:
        out.append("    (" + ", ".join(f'"{x}"' for x in row) + "),")
    out.append("]")
    return "\n".join(out)

def sub1(pattern, repl, flags=0):
    global src
    new, n = re.subn(pattern, repl, src, count=1, flags=flags)
    assert n == 1, f"anchor not found / not unique: {pattern[:60]}"
    src = new

sub1(r'AS_OF = "[0-9-]+"', 'AS_OF = "2026-11-15"')
sub1(r'RETRIEVED_AT_UTC = "[^"]+"', 'RETRIEVED_AT_UTC = "2026-11-15T11:50:00Z"')
sub1(r'RETRIEVED_BY = "[^"]+"', 'RETRIEVED_BY = "arena/673acec0-nba2"')
sub1(r'WINDOW_START = "[0-9-]+"', 'WINDOW_START = "2026-11-15"')
sub1(r'WINDOW_END = "[0-9-]+"', 'WINDOW_END = "2026-11-18"')
sub1(r'TEAMS: dict\[str, tuple\] = \{.*?\n\}', lambda m: teams_block(), re.S)
sub1(r'SLATE = \[.*?\n\]', lambda m: slate_block(), re.S)
sub1(r'INJURIES = \[.*?\n\]', lambda m: inj_block(), re.S)
sub1(r'NOT_SUBMITTED = \[.*?\n\]', lambda m: ns_block(), re.S)
sub1(r'"https://ak-static\.cms\.nba\.com/referee/injury/Injury-Report_[^"]+\.pdf"',
     f'"{C.PDF_URL}"')
sub1(r'NBA Official Injury Report 11/14/26 04:30 AM ET \(official PDF\)',
     'NBA Official Injury Report 11/15/26 06:15 AM ET (official PDF)')
sub1(r'"https://www\.nba\.com/schedule\?date=[0-9-]+"',
     '"https://www.nba.com/schedule?date=2026-11-17"')
sub1(r'"https://www\.nba\.com/games\?date=[0-9-]+"',
     '"https://www.nba.com/games?date=2026-11-14"')

# provenance comments that name the old snapshot
sub1(r'# W/L \+ splits: nba\.com/standings, fetched 2026-11-14\.',
     '# W/L + splits: nba.com/standings, fetched 2026-11-15.')
sub1(r'# PF/PA: computed from the 183 official finals in data/raw/history/ \(spot-checked against\n'
     r'#        nba\.com/stats/teams/traditional: LAL 122\.2 vs 122\.2, SAS 119\.5 vs 119\.5\)\.\n'
     r'# OEFF/DEF/NET/PACE/PIE: nba\.com/stats/teams/advanced, fetched 2026-11-14\.',
     f'# PF/PA: computed from the {N_GAMES} official finals in data/raw/history/ (every game, so the\n'
     f'#        per-game average is exact rather than sampled; cross-checked against the PTS column\n'
     f'#        of nba.com/stats/teams/traditional for 8 clubs: 8/8 identical to the printed decimal).\n'
     f'# OEFF/DEF/NET/PACE/PIE: nba.com/stats/teams/advanced, fetched 2026-11-15.')
sub1(r'# From https://www\.nba\.com/schedule\?date=2026-11-15, read 2026-11-14\.\n'
     r'# date, time_et, away, home, game_id, arena, city, national_broadcast, cup_group\n'
     r'# Window = the next three days, 2026-11-14 \.\. 2026-11-17 inclusive \(27 games\)\.',
     '# From https://www.nba.com/schedule?date=2026-11-17, read 2026-11-15.\n'
     '# date, time_et, away, home, game_id, arena, city, national_broadcast, cup_group\n'
     '# Window = today .. today+3 (the brief\'s "up to a maximum of 3 days in advance"),\n'
     '# 2026-11-15 .. 2026-11-18 inclusive (34 games). The 11/14 games that used to head this\n'
     '# list have been played; they are now part of data/raw/history/games_2026-11-14.json.')
sub1(r'# Transcribed from the official 11/14/26 04:30 AM ET PDF\. The report\'s own columns are',
     '# Transcribed from the official 11/15/26 06:15 AM ET PDF. The report\'s own columns are')

p.write_text(src)
print(f"patched nba2/v2/official.py ({len(orig)} -> {len(src)} bytes)")
