#!/usr/bin/env bash
# backend_stdlib_http — the Go backend must use stdlib net/http (1.22 ServeMux).
#
# Stack contract: stdlib net/http + log/slog. Third-party web frameworks/routers
# (gin, echo, fiber, chi, gorilla/mux) are out of contract.
# No escape — route with the stdlib 1.22 ServeMux.
# Fails (blocks). Self-skips when no go.mod is present.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

mods=$(git ls-files 2>/dev/null | grep -E '(^|/)go\.mod$' || true)
[ -n "$mods" ] || exit 0

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    m=$(grep -nE 'github\.com/(gin-gonic/gin|labstack/echo|gofiber/fiber|go-chi/chi|gorilla/mux)' "$f" 2>/dev/null || true)
    [ -n "$m" ] && hits="$hits$f:"$'\n'"$(printf '%s' "$m" | sed 's/^/    /')"$'\n'
done <<< "$mods"

if [ -n "$hits" ]; then
    printf "%s\n" "Third-party Go web framework — stack is stdlib net/http (1.22 ServeMux):"
    printf "%s" "$hits" | sed 's/^/  /'
    exit 1
fi
exit 0
