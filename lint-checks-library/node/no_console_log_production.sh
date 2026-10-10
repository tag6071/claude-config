#!/usr/bin/env bash
# no_console_log_production — `console.log` outside tests / dev tools.
#
# Use a real logger (or remove the debug print). Exempt: tests/, *.spec.*,
# *.test.*, and scripts/ helpers.
#
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Warns (does not block). Exits 0.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

files=$(git ls-files '*.js' '*.mjs' '*.ts' '*.tsx' '*.jsx' 2>/dev/null \
        | grep -vE '(^|/)(tests?|test|spec|scripts|node_modules|dist|build)/' \
        | grep -vE '\.(spec|test)\.(m?js|ts|tsx|jsx)$' \
        || true)

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    found=$(grep -nE '\bconsole\.log\s*\(' "$f" 2>/dev/null \
            || true)
    if [ -n "$found" ]; then
        while IFS= read -r h; do
            hits="$hits$f:$h"$'\n'
        done <<< "$found"
    fi
done <<< "$files"

if [ -n "$hits" ]; then
    printf "%s\n" "console.log in production:"
    printf "%s" "$hits" | head -15
fi
exit 0
