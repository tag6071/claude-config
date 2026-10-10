#!/usr/bin/env bash
# assert_in_production — `assert` statements in production Python.
#
# `assert` is stripped when Python runs with `-O` (optimize). Using it
# for runtime validation is a recipe for silent failures in production.
# Tests are exempt — pytest relies on assert.
#
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Warns (does not block). Exits 0.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

# Tracked .py files, excluding tests/ + test_*.py / *_test.py
files=$(git ls-files '*.py' 2>/dev/null \
        | grep -vE '(^|/)(tests?|test_data|fixtures)/' \
        | grep -vE '(^|/)(test_[^/]+\.py|[^/]+_test\.py)$' \
        || true)

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    found=$(grep -nE '^\s*assert\s' "$f" 2>/dev/null \
            || true)
    if [ -n "$found" ]; then
        while IFS= read -r h; do
            hits="$hits$f:$h"$'\n'
        done <<< "$found"
    fi
done <<< "$files"

if [ -n "$hits" ]; then
    printf "%s\n" "assert in production .py:"
    printf "%s" "$hits" | head -15
    printf "%s\n" "↳ python -O strips asserts; use explicit raise / typed validation."
fi
exit 0
