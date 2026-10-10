#!/usr/bin/env bash
# no_escape_comments — the lock: NO self-granted lint bypass comments, ever.
#
# Every other check used to allow a `// FOO-OK: <reason>` escape — a comment the
# author writes to grant THEMSELVES a pass. That's a loophole: it lets slop ship
# with a plausible-sounding excuse and a green gate. This check bans the entire
# escape vocabulary in custom source, so a violation can only be FIXED, never
# excused. 100% compliance — no middle ground.
#
# Scope: tracked source in the repo, EXCLUDING dependencies (node_modules/vendor),
# build output, archives, and the lint-checks dir itself (the checks legitimately
# name these tokens in their own logic/help). Dependencies are never touched.
# No escape — that's the point.
# Fails (blocks). Self-skips on an empty repo.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

# any FOO-OK / FOO-BAR-OK token used as a bypass marker
pat='\b[A-Z][A-Z0-9]*(-[A-Z0-9]+)*-OK\b'

src=$(git ls-files 2>/dev/null \
      | grep -E '\.(tsx|jsx|ts|js|mjs|cjs|css|scss|go|py|rs|rb|sh|bash|vue|svelte)$' \
      | grep -vE '(^|/)(node_modules|vendor|dist|build|\.archive[a-zA-Z0-9._-]*)/' \
      | grep -vE '(^|/)scripts/lint-checks/' || true)
[ -n "$src" ] || exit 0

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    found=$(grep -nE "$pat" "$f" 2>/dev/null || true)
    [ -n "$found" ] && hits="$hits$f:"$'\n'"$(printf '%s' "$found" | head -5 | sed 's/^/    /')"$'\n'
done <<< "$src"

if [ -n "$hits" ]; then
    printf "%s\n" "Self-granted lint-bypass comment(s) — banned. Fix the code, don't excuse it:"
    printf "%s" "$hits" | head -60 | sed 's/^/  /'
    printf "%s\n" "↳ there is no escape hatch. Make the line actually compliant."
    exit 1
fi
exit 0
