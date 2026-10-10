#!/usr/bin/env bash
# unchecked_errors — `_ = funcThatReturnsErr()` patterns.
#
# `errcheck` / `golangci-lint` catch this better; this is a fallback
# regex check for repos without that toolchain installed. Catches the
# most common silent-error patterns.
#
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Warns. Exits 0.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

# Defer to golangci-lint when installed — its errcheck does this better
# (adopt, don't reinvent). This regex check is only the no-golangci fallback.
command -v golangci-lint >/dev/null 2>&1 && exit 0

files=$(git ls-files '*.go' 2>/dev/null | grep -v '_test\.go$' || true)

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    # Match `_, _ = ...` or `_ = funcCall(`
    found=$(grep -nE '^\s*_\s*[,]?\s*_?\s*=' "$f" 2>/dev/null \
            || true)
    if [ -n "$found" ]; then
        while IFS= read -r h; do
            hits="$hits$f:$h"$'\n'
        done <<< "$found"
    fi
done <<< "$files"

if [ -n "$hits" ]; then
    printf "%s\n" "Go: discarded error returns:"
    printf "%s" "$hits" | head -15
    printf "%s\n" "↳ install errcheck or golangci-lint for proper coverage."
fi
exit 0
