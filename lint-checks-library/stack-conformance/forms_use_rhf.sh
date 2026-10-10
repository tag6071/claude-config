#!/usr/bin/env bash
# forms_use_rhf — a React app with <form> elements should use react-hook-form.
#
# Stack contract: react-hook-form + zod. Hand-rolled <form> + useState handlers
# drift off-stack and ship without the baked-in validation/disabled/loading UX —
# the exact form rot this pack exists to stop. Use the scaffold's <AppForm>.
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Fails (blocks). Self-skips when not a React project.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

pkgs=$(git ls-files 2>/dev/null | grep -E '(^|/)package\.json$' | grep -vE '(^|/)node_modules/' || true)
[ -n "$pkgs" ] || exit 0

# React project?  (guard the file list — empty would hang grep on stdin)
echo "$pkgs" | xargs grep -lE '"react"[[:space:]]*:' 2>/dev/null | grep -q . || exit 0

# Already on react-hook-form anywhere? Then assume conformant, stay quiet.
if echo "$pkgs" | xargs grep -qE '"react-hook-form"[[:space:]]*:' 2>/dev/null; then
    exit 0
fi

src=$(git ls-files '*.tsx' '*.jsx' 2>/dev/null | grep -vE '(^|/)(node_modules|dist|build)/' || true)
hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    found=$(grep -nE '<form[[:space:]>]' "$f" 2>/dev/null || true)
    [ -n "$found" ] && hits="$hits$f: $(printf '%s' "$found" | head -1)"$'\n'
done <<< "$src"

if [ -n "$hits" ]; then
    printf "%s\n" "Hand-rolled <form> without react-hook-form (NO escape — use AppForm/rhf+zod):"
    printf "%s" "$hits" | head -15 | sed 's/^/  /'
    printf "%s\n" "↳ adopt react-hook-form + zod (the <AppForm>/useZodForm primitive) for these forms."
    exit 1
fi
exit 0
