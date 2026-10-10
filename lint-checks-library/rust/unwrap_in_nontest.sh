#!/usr/bin/env bash
# unwrap_in_nontest — .unwrap() / .expect() outside tests.
#
# In test code they're fine (panic on failure = test failure). In
# production they're panic-on-error which is rarely what you want.
# `clippy` covers this better; this is a fallback for projects
# without clippy in CI.
#
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Warns. Exits 0.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

files=$(git ls-files '*.rs' 2>/dev/null \
        | grep -vE '(^|/)(tests?|benches|examples)/' \
        | grep -vE '_test\.rs$' \
        || true)

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    # Skip per-file #[cfg(test)] blocks isn't worth grepping line-by-line;
    # just match .unwrap() / .expect().
    found=$(grep -nE '\.(unwrap|expect)\s*\(' "$f" 2>/dev/null \
            || true)
    if [ -n "$found" ]; then
        while IFS= read -r h; do
            hits="$hits$f:$h"$'\n'
        done <<< "$found"
    fi
done <<< "$files"

if [ -n "$hits" ]; then
    printf "%s\n" "Rust: .unwrap()/.expect() in production:"
    printf "%s" "$hits" | head -15
    printf "%s\n" "↳ install clippy for proper coverage."
fi
exit 0
