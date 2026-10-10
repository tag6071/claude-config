#!/usr/bin/env bash
# no_raw_colors — colours come from design tokens, not raw literals scattered in code.
#
# Stack contract: one token source (Tailwind theme / CSS custom props). Raw hex
# (#abc / #aabbcc / #aabbccdd) and rgb()/rgba()/hsl()/hsla() literals in component
# code or feature CSS mean a colour that lives outside the design system — the
# road to inconsistency. Token-definition files are exempt (that's WHERE colours
# are allowed to be literal): tailwind.config.*, components.json, and the global
# token sheets (globals.css / index.css / theme.css / tokens.css).
# No escape — the no_escape_comments lock bans bypass comments. Fix the violation.
# Fails (blocks). Self-skips when not a React project.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

pkgs=$(git ls-files 2>/dev/null | grep -E '(^|/)package\.json$' | grep -vE '(^|/)node_modules/' || true)
[ -n "$pkgs" ] || exit 0
echo "$pkgs" | xargs grep -lE '"react"[[:space:]]*:' 2>/dev/null | grep -q . || exit 0

# Token-definition files are exempt — colours are *supposed* to be literal there.
allow='(tailwind\.config\.|components\.json$|(^|/)(globals|index|[Aa]pp|theme)\.(css|scss)$|tokens\.(css|scss)$)'

src=$(git ls-files '*.tsx' '*.jsx' '*.css' 2>/dev/null \
      | grep -vE '(^|/)(node_modules|dist|build|\.archive[a-zA-Z0-9._-]*)/' \
      | grep -vE "$allow" || true)
[ -n "$src" ] || exit 0

# Color-shaped hex (3/4/6/8 hex digits) or rgb/hsl function literals.
pat='#[0-9a-fA-F]{3,4}\b|#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?\b|\b(rgba?|hsla?)\('

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    found=$(grep -nE "$pat" "$f" 2>/dev/null || true)
    [ -n "$found" ] && hits="$hits$f:"$'\n'"$(printf '%s' "$found" | head -5 | sed 's/^/    /')"$'\n'
done <<< "$src"

if [ -n "$hits" ]; then
    printf "%s\n" "Raw colour literal outside the token system — define it once as a token:"
    printf "%s" "$hits" | head -40 | sed 's/^/  /'
    printf "%s\n" "↳ add the colour to tailwind.config / the global token sheet, reference the token."
    printf "%s\n" "↳ NO escape — define the colour as a token (global sheet / tailwind.config) and reference it; brand SVG fills go in the token sheet too."
    exit 1
fi
exit 0
