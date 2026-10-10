#!/usr/bin/env bash
# frontend_framework — the frontend must be Vite. Fails on Next.js / SvelteKit / CRA.
#
# Stack contract: Vite + React. Next.js, SvelteKit and create-react-app are out.
# No escape — migrate to Vite (see the global stack contract in ~/.claude/CLAUDE.md).
# Fails (blocks). Self-skips when no package.json is present.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

pkgs=$(git ls-files 2>/dev/null | grep -E '(^|/)package\.json$' \
       | grep -vE '(^|/)node_modules/' || true)
[ -n "$pkgs" ] || exit 0

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    m=$(grep -nE '"(next|@sveltejs/kit|react-scripts)"[[:space:]]*:' "$f" 2>/dev/null || true)
    [ -n "$m" ] && hits="$hits$f:"$'\n'"$(printf '%s' "$m" | sed 's/^/    /')"$'\n'
done <<< "$pkgs"

if [ -n "$hits" ]; then
    printf "%s\n" "Non-Vite framework in package.json — stack is Vite+React:"
    printf "%s" "$hits" | sed 's/^/  /'
    printf "%s\n" "↳ next / sveltekit / create-react-app → migrate to Vite."
    exit 1
fi
exit 0
