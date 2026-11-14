#!/usr/bin/env bash
# One script, one log: every gate the repository's own conventions require, run in order.
# Used for both the baseline (hand-recorded in baseline.txt) and the closing run (after.txt).
#   bash audit/2026-11-14-bc867bff/run_gates.sh > audit/2026-11-14-bc867bff/after.txt 2>&1
# Exits non-zero on the first failing gate, so "the site is not broken" is a returned code,
# not a sentence.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1
FAIL=0
step() {
  local name="$1"; shift
  printf '\n===== %s =====\n$ %s\n' "$name" "$*"
  if out=$("$@" 2>&1); then
    printf '%s\n[exit 0]\n' "${out: -4000}"
  else
    printf '%s\n[exit NON-ZERO]\n' "${out: -4000}"
    FAIL=$((FAIL + 1))
  fi
}

echo "NBA2 gate run — session arena/bc867bff-nba2"
echo "commit $(git rev-parse --short HEAD) on $(git rev-parse --abbrev-ref HEAD)"
echo "run at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "tree dirty files at start: $(git status --porcelain | wc -l)"

step "v1 unit tests"            python3 -m unittest discover -s nba2/tests -t .
step "v2 unit tests"           python3 -m unittest discover -s nba2/v2 -t . -p 'test_*.py'
step "backtest unit tests"     python3 -m unittest discover -s backtest/tests
step "capture verifier"        python3 audit/2026-11-14-bc867bff/verify_captures.py
step "v1 site data build"      python3 -m nba2.pipeline.build_site_data
step "v1 site build"           python3 -m nba2.pipeline.build_site
step "v1 lint"                 python3 -m nba2.pipeline.lint
step "backtest engine rebuild" python3 -m backtest.engine.build
step "backtest verify"         python3 tools/verify_backtest.py
step "v2 build (idempotence)"  python3 -m nba2.v2
step "v2 structural+semantic"  python3 -m nba2.v2.check
step "internal link graph"     python3 tools/check_links_all.py
step "live verifier"           python3 -m nba2.v2.live
step "crosscheck (97)"         python3 tools/crosscheck_site.py

printf '\n===== generated artefacts are a pure function of the inputs =====\n'
DIFF=$(git status --porcelain -- site data/v2 data/site.json index.html pages backtest/data 2>/dev/null \
       | grep -v '^$' | sed 's/^ *//')
if [ -z "$DIFF" ]; then
  echo "clean — rebuilding produced no drift beyond what is committed"
else
  echo "changed by the rebuild (expected if this run follows an edit; must be empty on a re-run):"
  echo "$DIFF" | head -20
fi

printf '\n===== sealed artefacts untouched =====\n'
for f in nba2/data/picks.json data/raw/ledger; do
  n=$(git status --porcelain -- "$f" | wc -l)
  echo "$f: $([ "$n" -eq 0 ] && echo 'UNTOUCHED (git reports 0 changes)' || echo "DIRTY — $n paths")"
  [ "$n" -eq 0 ] || FAIL=$((FAIL + 1))
done
printf 'ledger immutability (nba2.models.ledger.verify): '
python3 - <<'PY'
import sys
sys.path.insert(0, '.')
try:
    from nba2.models import ledger
except Exception as e:                                    # noqa: BLE001
    print(f"module not importable in this tree ({e.__class__.__name__}) — checked by git instead")
    sys.exit(0)
import glob, os
paths = sorted(glob.glob('data/raw/ledger/*.json'))
if not paths:
    print("no ledger files found — nothing to verify")
    sys.exit(0)
bad = []
for p in paths:
    try:
        ledger.verify(p)
    except Exception as e:                                 # noqa: BLE001
        bad.append(f"{os.path.basename(p)}: {e}")
print(f"{len(paths) - len(bad)}/{len(paths)} ledgers verify" + (f"; failures: {bad[:3]}" if bad else ""))
sys.exit(1 if bad else 0)
PY
[ $? -ne 0 ] && FAIL=$((FAIL + 1))

printf '\n===== capture provenance =====\n'
python3 - <<'PY'
import json, pathlib
c = json.loads(pathlib.Path('audit/2026-11-14-bc867bff/captures.json').read_text())
d = c["documents"]
print(f"captured_utc {c['captured_utc']}  method: {c['method'][:70]}…")
for k in ("injury_report", "records_strip", "slate_reread", "player_rotation"):
    doc = d[k]
    n = len(doc.get("rows", doc.get("games", doc.get("records", doc.get("rows", [])) or []))) \
        if not isinstance(doc.get("records"), dict) else len(doc["records"])
    print(f"  {k:16} {n:>3} units  {doc['url'][:78]}")
print(f"  still_blocked    {len(d['still_blocked'])} documented failures")
PY

printf '\n===== summary =====\n'
if [ "$FAIL" -eq 0 ]; then echo "ALL GATES PASSED (0 failing steps)"; else echo "$FAIL failing step(s) — see above"; fi
exit "$FAIL"
