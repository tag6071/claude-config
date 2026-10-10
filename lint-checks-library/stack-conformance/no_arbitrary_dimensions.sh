#!/usr/bin/env bash
# no_arbitrary_dimensions — type & spacing come from the scale, not ad-hoc values.
#
# Stack contract: Tailwind's theme IS the spacing/type scale (text-sm, p-4, gap-3).
# Same role → same token, everywhere — that's what stops the "jammed / inconsistent
# spacing" drift. The Tailwind bypass is arbitrary values: text-[13px], p-[13px],
# gap-[7px], leading-[18px]. This blocks those on the RHYTHM axes (typography +
# spacing) and bare font-size/line-height px literals in feature CSS. Width/height
# arbitrary values (w-[420px]) are NOT flagged — fixed sizes are legitimate.
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Fails (blocks). Self-skips when not a React project.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

pkgs=$(git ls-files 2>/dev/null | grep -E '(^|/)package\.json$' | grep -vE '(^|/)node_modules/' || true)
[ -n "$pkgs" ] || exit 0
echo "$pkgs" | xargs grep -lE '"react"[[:space:]]*:' 2>/dev/null | grep -q . || exit 0

# Tailwind arbitrary value carrying a raw px/rem/em on a rhythm axis:
#   text- leading- tracking- gap- space-x/y- and p*/m* (p,px,py,pt,pb,pl,pr,ps,pe,…)
tw='\b(text|leading|tracking|gap|space-[xy]|[pm][xytblrse]?)-\[[0-9.]+(px|rem|em)\]'

hits=""
src=$(git ls-files '*.tsx' '*.jsx' 2>/dev/null | grep -vE '(^|/)(node_modules|dist|build|\.archive[a-zA-Z0-9._-]*)/' || true)
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    found=$(grep -nE "$tw" "$f" 2>/dev/null || true)
    [ -n "$found" ] && hits="$hits$f:"$'\n'"$(printf '%s' "$found" | head -5 | sed 's/^/    /')"$'\n'
done <<< "$src"

# Bare font-size / line-height px in feature CSS (the global token sheet is exempt).
allow='((^|/)(globals|index|App|theme)\.(css|scss)$|tokens\.(css|scss)$)'
css=$(git ls-files '*.css' '*.scss' 2>/dev/null \
      | grep -vE '(^|/)(node_modules|dist|build|\.archive[a-zA-Z0-9._-]*)/' | grep -vE "$allow" || true)
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    found=$(grep -nE '(font-size|line-height)[[:space:]]*:[[:space:]]*[0-9.]+px' "$f" 2>/dev/null || true)
    [ -n "$found" ] && hits="$hits$f:"$'\n'"$(printf '%s' "$found" | head -5 | sed 's/^/    /')"$'\n'
done <<< "$css"

if [ -n "$hits" ]; then
    printf "%s\n" "Hardcoded type/spacing — use the Tailwind scale, not arbitrary values:"
    printf "%s" "$hits" | head -40 | sed 's/^/  /'
    printf "%s\n" "↳ text-[13px]→text-sm, p-[13px]→p-3, gap-[7px]→gap-2; configure the scale in tailwind.config."
    printf "%s\n" "↳ NO escape — same role → same scale token; add the value to tailwind.config."
    exit 1
fi
exit 0
