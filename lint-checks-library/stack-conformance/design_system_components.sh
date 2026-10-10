#!/usr/bin/env bash
# design_system_components — prefer the shadcn components over raw HTML controls.
#
# Stack contract: shadcn/ui. Raw <button>/<input>/<textarea> in app code drift
# off the design system (inconsistent focus rings, variants, sizing). Lighter
# touch than design_system_primitives (which BLOCKS the a11y-critical select /
# dialog) — this just WARNS so trivial cases stay frictionless. Only fires once
# shadcn is installed (a components/ui dir exists).
# No escape — the no_escape_comments lock bans bypass comments. Fix the violation.
# Warns (does not block). Self-skips when not a React project or shadcn absent.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

pkgs=$(git ls-files 2>/dev/null | grep -E '(^|/)package\.json$' | grep -vE '(^|/)node_modules/' || true)
[ -n "$pkgs" ] || exit 0
echo "$pkgs" | xargs grep -lE '"react"[[:space:]]*:' 2>/dev/null | grep -q . || exit 0
git ls-files 2>/dev/null | grep -qE '(^|/)components/ui/' || exit 0

src=$(git ls-files '*.tsx' '*.jsx' 2>/dev/null \
      | grep -vE '(^|/)(node_modules|dist|build|\.archive[a-zA-Z0-9._-]*)/' \
      | grep -vE '(^|/)components/ui/' || true)
[ -n "$src" ] || exit 0

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    found=$(grep -nE '<(button|input|textarea)[[:space:]>]' "$f" 2>/dev/null || true)
    [ -n "$found" ] && hits="$hits$f:"$'\n'"$(printf '%s' "$found" | head -4 | sed 's/^/    /')"$'\n'
done <<< "$src"

if [ -n "$hits" ]; then
    printf "%s\n" "Raw HTML control where a shadcn component exists — prefer Button/Input/Textarea:"
    printf "%s" "$hits" | head -30 | sed 's/^/  /'
    printf "%s\n" "↳ NO escape — use the shadcn component (Button/Input/Textarea)."
fi
exit 0
