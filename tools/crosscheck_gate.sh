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

# Optional extra check ids to exclude from gating (beyond CC-FRESH-01, excluded by
# design): the nightly bot passes CC-DOC-01 because the README is not part of its
# rebuild. Usage: tools/crosscheck_gate.sh [EXCLUDE_ID ...] [--from-log FILE]
EXCLUDE='CC-FRESH-01'
for arg in "$@"; do
    case "$arg" in
        --from-log) ;;
        CC-*) EXCLUDE="$EXCLUDE|$arg" ;;
    esac
done

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
    # This sandbox cannot download Actions console logs (the results blob host is
    # outside its egress allowlist — the same EOF the F-043 audit hit), so surface
    # the captured log through annotations, which ARE readable via `gh run view`.
    # One annotation, chunked to stay inside GitHub's annotation size limit.
    python3 - "$LOG" <<'PYEOF'
import pathlib, sys
text = pathlib.Path(sys.argv[1]).read_text(errors="replace")
lines = text.splitlines()
tail = lines[-60:] if len(lines) > 60 else lines
blob = " ⏎ ".join(tail)
while blob:
    print(f"::error::crosscheck log: {blob[:3500]}")
    blob = blob[3500:]
PYEOF
    exit 1
fi

if grep '^\[FAIL\]' "$LOG" | grep -vE "$EXCLUDE" | grep -q .; then
    echo "::error::semantic cross-check failed ([FAIL] lines above) — refusing to proceed (CR-7)"
    exit 1
fi

echo "cross-check gate passed (checker exit $rc). Excluded by design/policy: $EXCLUDE."
exit 0
