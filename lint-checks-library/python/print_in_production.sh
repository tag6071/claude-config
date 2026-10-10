#!/usr/bin/env bash
# print_in_production — `print()` calls in production Python.
#
# Use proper logging (logging module, structured loggers, or an event
# bus). `print` is hard to disable, mixes with stdout from subprocesses,
# and can break JSON output pipelines.
#
# Exempt: scripts/, tests/, CLI entry-points (files containing
# `if __name__ == "__main__":`).
#
# Warns (does not block). Exits 0.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

files=$(git ls-files '*.py' 2>/dev/null \
        | grep -vE '(^|/)(tests?|scripts|bin|fixtures)/' \
        | grep -vE '(^|/)(test_[^/]+\.py|[^/]+_test\.py)$' \
        || true)

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    # Skip files that look like CLI entry points (have __name__ == __main__)
    if grep -qE '^if\s+__name__\s*==\s*["\x27]__main__["\x27]' "$f" 2>/dev/null; then
        continue
    fi
    found=$(grep -nE '^\s*print\s*\(' "$f" 2>/dev/null \
            || true)
    if [ -n "$found" ]; then
        while IFS= read -r h; do
            hits="$hits$f:$h"$'\n'
        done <<< "$found"
    fi
done <<< "$files"

if [ -n "$hits" ]; then
    printf "%s\n" "print() in production .py:"
    printf "%s" "$hits" | head -15
    printf "%s\n" "↳ use logging / structured output instead."
fi
exit 0
