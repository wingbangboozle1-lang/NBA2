#!/bin/sh
# CR-7 semantic-crosscheck gate (shared by .github/workflows/ci.yml and
# .github/workflows/refresh.yml).
#
# Why this exists (F-050, change request from arena/bc867bff-nba2): the nightly
# workflow used to grep '^\[fail\]' while tools/crosscheck_site.py prints
# '[FAIL]' — the pattern could never match, so a red crosscheck could never
# block a commit. It also ran the checker with '|| true' and no completion
# check, so a checker crash (exit 2) was indistinguishable from a clean run.
#
# Rules enforced here:
#   1. the checker must have produced its summary line (a crash blocks);
#   2. any [FAIL] line blocks, except CC-FRESH-01 (snapshot age) which is
#      excluded BY DESIGN: the bot cannot refresh the third-party ratings
#      snapshot, and blocking settlement on it would freeze the ledger's
#      metrics whenever the ratings capture ages;
#   3. INFO/NA lines never block.
#
# Usage:
#   tools/crosscheck_gate.sh                 run the checker, then gate on it
#   tools/crosscheck_gate.sh --from-log F    gate on an existing log file F
#                                            (used by the regression test)
#
# Exit: 0 = pass, 1 = blocked (annotation printed for the Actions UI).

set -eu

LOG=/tmp/crosscheck_gate.txt

if [ "${1:-}" = "--from-log" ]; then
    [ $# -eq 2 ] || { echo "usage: $0 --from-log FILE" >&2; exit 2; }
    cp "$2" "$LOG"
    rc=0
else
    rc=0
    python3 tools/crosscheck_site.py > "$LOG" 2>&1 || rc=$?
fi

cat "$LOG"

if ! grep -q 'checks:' "$LOG"; then
    echo "::error::crosscheck did not produce its summary line (exit $rc) — refusing to proceed"
    exit 1
fi

if grep '^\[FAIL\]' "$LOG" | grep -v 'CC-FRESH-01' | grep -q .; then
    echo "::error::semantic cross-check failed ([FAIL] lines above) — refusing to proceed (CR-7)"
    exit 1
fi

echo "cross-check gate passed (checker exit $rc). CC-FRESH-01 (snapshot age) is excluded by design."
exit 0
