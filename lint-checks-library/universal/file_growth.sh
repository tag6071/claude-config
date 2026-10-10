#!/usr/bin/env bash
# file_growth — flag any source file that grew >250 lines in this commit.
#
# Reads `git diff --cached` against HEAD. Targets sane source patterns
# (Python, JS/TS, Go, Rust, Ruby, shell). Skips test fixtures + vendored
# dirs. Bypass: GROWTH_APPROVED=1 env var.
#
# Exits 1 on violation.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

[ "${GROWTH_APPROVED:-}" = "1" ] && exit 0
git rev-parse --verify HEAD >/dev/null 2>&1 || exit 0

PATTERNS='\.(py|js|mjs|ts|tsx|jsx|go|rs|rb|sh|bash)$'
MAX_GROWTH=250

violations=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    # Skip obvious vendored / test-data / node_modules dirs
    case "$f" in
        */node_modules/*|*/vendor/*|*/.venv/*|*/__pycache__/*|*/test-results/*) continue ;;
    esac
    after=$(git show ":$f" 2>/dev/null | wc -l | tr -d ' ')
    before=$(git show "HEAD:$f" 2>/dev/null | wc -l | tr -d ' ' || echo 0)
    [ -z "$before" ] && before=0
    diff=$((after - before))
    if [ "$diff" -gt "$MAX_GROWTH" ]; then
        violations="${violations}${f}: +${diff} lines (${before} → ${after})"$'\n'
    fi
done < <(git diff --cached --name-only 2>/dev/null | grep -E "$PATTERNS" || true)

if [ -n "$violations" ]; then
    printf "files grew by >%d lines in one commit (split or document; bypass: GROWTH_APPROVED=1):\n" "$MAX_GROWTH"
    printf "%s" "$violations"
    exit 1
fi
exit 0
