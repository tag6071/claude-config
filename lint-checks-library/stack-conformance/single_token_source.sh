#!/usr/bin/env bash
# single_token_source — exactly one design-token source / one theme mechanism.
#
# Stack contract: ONE token system. Two traps this catches:
#   1. Two theme-switch mechanisms (e.g. both `data-theme` and `data-mode`) — a
#      sign a second, parallel theming scheme was bolted on.
#   2. `:root { --token: … }` custom-property definitions living in more than one
#      file — the "dead second design system" trap (one set goes stale and the
#      two drift apart).
# No escape — the no_escape_comments lock bans bypass comments. Fix the violation.
# Fails (blocks). Self-skips when not a React project.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

pkgs=$(git ls-files 2>/dev/null | grep -E '(^|/)package\.json$' | grep -vE '(^|/)node_modules/' || true)
[ -n "$pkgs" ] || exit 0
echo "$pkgs" | xargs grep -lE '"react"[[:space:]]*:' 2>/dev/null | grep -q . || exit 0

files=$(git ls-files '*.css' '*.tsx' '*.jsx' '*.ts' 2>/dev/null \
        | grep -vE '(^|/)(node_modules|dist|build|\.archive[a-zA-Z0-9._-]*)/' || true)
[ -n "$files" ] || exit 0

fail=0

# (1) competing theme-switch attribute names.
mechs=""
for attr in data-theme data-mode data-color-mode data-color-scheme; do
    if echo "$files" | xargs grep -lE "$attr(=|\")" 2>/dev/null | grep -q . ; then
        present=$(echo "$files" | xargs grep -lE "$attr(=|\")" 2>/dev/null || true)
        [ -n "$present" ] && mechs="$mechs $attr"
    fi
done
nmech=$(echo "$mechs" | wc -w | tr -d ' ')
if [ "${nmech:-0}" -gt 1 ]; then
    printf "%s\n" "Multiple theme-switch mechanisms — pick one:$mechs"
    fail=1
fi

# (2) :root custom-property definitions in more than one file.
tokfiles=$(echo "$files" \
    | xargs grep -lE ':root[^{]*\{' 2>/dev/null \
    | xargs grep -lE '\-\-[a-zA-Z0-9_-]+[[:space:]]*:' 2>/dev/null || true)
ntok=$(printf '%s\n' "$tokfiles" | grep -c . || true)
if [ "${ntok:-0}" -gt 1 ]; then
    printf "%s\n" "Design tokens defined in more than one file — consolidate to a single source:"
    printf '%s\n' "$tokfiles" | sed 's/^/    /'
    fail=1
fi

if [ "$fail" -eq 1 ]; then
    printf "%s\n" "↳ NO escape — consolidate to one token sheet + one theme mechanism."
    exit 1
fi
exit 0
