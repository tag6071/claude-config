#!/usr/bin/env bash
# no_inline_styles — styling is Tailwind utilities + tokens, never inline/CSS-in-JS.
#
# Stack contract: Tailwind + design tokens. Two drifts are banned:
#   1. inline `style={{ ... }}` props on JSX, and
#   2. CSS-in-JS — a `<style>` JSX element (e.g. `<style>{CSS}</style>`), which
#      injects a hand-stitched stylesheet straight into the DOM (the exact way a
#      real session bypassed Tailwind and grew an unmaintainable parallel system).
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Fails (blocks). Self-skips when not a React project.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

pkgs=$(git ls-files 2>/dev/null | grep -E '(^|/)package\.json$' | grep -vE '(^|/)node_modules/' || true)
[ -n "$pkgs" ] || exit 0
echo "$pkgs" | xargs grep -lE '"react"[[:space:]]*:' 2>/dev/null | grep -q . || exit 0

src=$(git ls-files '*.tsx' '*.jsx' 2>/dev/null | grep -vE '(^|/)(node_modules|dist|build|\.archive[a-zA-Z0-9._-]*)/' || true)
[ -n "$src" ] || exit 0

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    found=$(grep -nE 'style=\{\{|<style[[:space:]>]' "$f" 2>/dev/null || true)
    [ -n "$found" ] && hits="$hits$f:"$'\n'"$(printf '%s' "$found" | head -5 | sed 's/^/    /')"$'\n'
done <<< "$src"

if [ -n "$hits" ]; then
    printf "%s\n" "Inline style / CSS-in-JS — stack is Tailwind utilities + design tokens:"
    printf "%s" "$hits" | head -40 | sed 's/^/  /'
    printf "%s\n" "↳ move to Tailwind classes (one-off values: tokens in tailwind.config / globals.css)."
    printf "%s\n" "↳ NO escape — move to Tailwind utilities/tokens. (A computed style={expr} is fine; an inline {{…}} literal is not.)"
    exit 1
fi
exit 0
