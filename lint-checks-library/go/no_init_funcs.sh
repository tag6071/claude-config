#!/usr/bin/env bash
# no_init_funcs — `func init()` is invisible side-effect-at-load.
#
# Allowed in narrow cases (registering with a global registry, etc) but
# usually a code-smell. Warn so the author justifies it.
#
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Warns. Exits 0.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

files=$(git ls-files '*.go' 2>/dev/null | grep -v '_test\.go$' || true)

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    # Find init() funcs (no escape — the lock bans bypass comments).
    found=$(awk '
        /^func init\(\)/ { print NR": "$0 }
    ' "$f" 2>/dev/null || true)
    if [ -n "$found" ]; then
        while IFS= read -r h; do
            hits="$hits$f:$h"$'\n'
        done <<< "$found"
    fi
done <<< "$files"

if [ -n "$hits" ]; then
    printf "%s\n" "Go: func init():"
    printf "%s" "$hits" | head -10
fi
exit 0
