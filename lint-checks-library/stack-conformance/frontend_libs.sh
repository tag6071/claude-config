#!/usr/bin/env bash
# frontend_libs — a React app should ship TanStack Query + react-router.
#
# Stack contract: @tanstack/react-query (data) + react-router-dom (routing).
# Warns when a React project is missing either (small apps may legitimately
# omit routing — hence warn, not block).
# Warns (does not block). Self-skips when not a React project.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

pkgs=$(git ls-files 2>/dev/null | grep -E '(^|/)package\.json$' | grep -vE '(^|/)node_modules/' || true)
[ -n "$pkgs" ] || exit 0
echo "$pkgs" | xargs grep -lE '"react"[[:space:]]*:' 2>/dev/null | grep -q . || exit 0

missing=""
echo "$pkgs" | xargs grep -qE '"@tanstack/react-query"[[:space:]]*:' 2>/dev/null \
    || missing="$missing  - @tanstack/react-query (data fetching)"$'\n'
echo "$pkgs" | xargs grep -qE '"react-router(-dom)?"[[:space:]]*:' 2>/dev/null \
    || missing="$missing  - react-router-dom (routing)"$'\n'

if [ -n "$missing" ]; then
    printf "%s\n" "React app missing stack libraries:"
    printf "%s" "$missing"
fi
exit 0
