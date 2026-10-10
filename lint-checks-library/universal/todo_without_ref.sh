#!/usr/bin/env bash
# todo_without_ref — flag TODO/FIXME/XXX comments without a ticket
# reference. A reference is any of:
#   - `#NNN`           — GitHub-style issue number
#   - `JIRA-NNN`       — JIRA-style ticket
#   - `https://...`    — link
#   - `LINEAR-...`     — Linear
#   - `@username`      — owner attribution
#
# Bare `// TODO: fix this` rots forever. Tagged `// TODO #123` is trackable.
#
# Warns (does not block). Exits 0.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

PATTERNS='\.(py|js|mjs|ts|tsx|jsx|go|rs|rb|sh|bash|md|html|css|scss)$'

# Tracked source files only (skip vendored / generated / node_modules).
files=$(git ls-files 2>/dev/null | grep -E "$PATTERNS" \
        | grep -vE '(^|/)(node_modules|vendor|\.venv|__pycache__|test-results|dist|build)/' \
        || true)

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    # Match TODO/FIXME/XXX only when they appear as a comment marker
    # (i.e. at start of line, or right after //, #, /*, or *) — NOT
    # when they appear inside identifiers like IMG_OXXXX or as plain
    # text inside markdown. Require the token to be word-bounded on
    # both sides (no _ allowed).
    found=$(grep -nE '(^|//|#|/\*|^\s*\*)\s*(TODO|FIXME|XXX)([[:space:]]*[:.]|\b)' "$f" 2>/dev/null \
            | grep -vE '#[0-9]+|[A-Z]{2,}-[0-9]+|https?://|@[A-Za-z0-9_-]+' \
            | grep -vE '[A-Za-z_](TODO|FIXME|XXX)|(TODO|FIXME|XXX)[A-Za-z_]' \
            || true)
    if [ -n "$found" ]; then
        while IFS= read -r h; do
            hits="$hits$f:$h"$'\n'
        done <<< "$found"
    fi
done <<< "$files"

if [ -n "$hits" ]; then
    printf "%s\n" "TODO/FIXME/XXX without a ticket ref or owner:"
    printf "%s" "$hits" | head -20
    count=$(printf "%s" "$hits" | grep -c '' || echo 0)
    if [ "$count" -gt 20 ]; then
        printf "  … and %d more\n" $((count - 20))
    fi
fi
exit 0
