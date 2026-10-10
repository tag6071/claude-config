#!/usr/bin/env bash
# no_wait_timeout — ban `await page.waitForTimeout(N)` in Playwright specs.
#
# Hardcoded sleeps are the #1 flake source under parallel load. Use an
# auto-retrying `await expect(locator).toX(...)` on the actual post-state
# instead.
#
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Exits 1 on violation.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

hits=$(grep -rnE 'await[[:space:]]+page\.waitForTimeout\(' tests/ \
        --include='*.spec.mjs' --include='*.spec.ts' --include='*.spec.js' \
        2>/dev/null || true)

if [ -n "$hits" ]; then
    printf "%s\n" "waitForTimeout(N) in spec files:"
    printf "%s\n" "$hits"
    exit 1
fi
exit 0
