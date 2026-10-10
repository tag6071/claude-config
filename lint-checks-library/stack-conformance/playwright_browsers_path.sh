#!/usr/bin/env bash
# playwright_browsers_path — don't install chromium into a blocked default path.
#
# The recurring failure: `playwright install` downloads browsers to
# ~/.cache/ms-playwright and hits a sandbox/permission wall. Fix: pin a fixed,
# writable PLAYWRIGHT_BROWSERS_PATH (or use the shared Docker image) so the
# browser install happens once, in a known place — never per-run into a wall.
# Warns when a repo runs `playwright install` without pinning a browsers path.
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Warns (does not block). Self-skips when Playwright isn't used.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

# Playwright in use?
uses=$(git ls-files 2>/dev/null \
       | grep -E '(playwright\.config\.|(^|/)package\.json$)' \
       | grep -vE '(^|/)node_modules/' || true)
[ -n "$uses" ] || exit 0
echo "$uses" | xargs grep -qE '@playwright/test|playwright install' 2>/dev/null || exit 0

# Is a fixed browsers path pinned anywhere sensible?
scan=$(git ls-files 2>/dev/null \
       | grep -E '(playwright\.config\.|\.env|(^|/)package\.json$|Makefile|\.sh$)' \
       | grep -vE '(^|/)node_modules/' || true)
if [ -n "$scan" ] && echo "$scan" | xargs grep -qE 'PLAYWRIGHT_BROWSERS_PATH|mcr\.microsoft\.com/playwright' 2>/dev/null; then
    exit 0
fi

printf "%s\n" "Playwright present but no fixed PLAYWRIGHT_BROWSERS_PATH (or Docker image) pinned."
printf "%s\n" "↳ set PLAYWRIGHT_BROWSERS_PATH to a writable dir, or use mcr.microsoft.com/playwright,"
printf "%s\n" "  so chromium installs once in a known place — not per-run into a blocked path."
exit 0
