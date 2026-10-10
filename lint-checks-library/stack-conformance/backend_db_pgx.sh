#!/usr/bin/env bash
# backend_db_pgx — Go DB access should be sqlc + pgx on Postgres.
#
# Stack contract: sqlc + pgx + Postgres + goose migrations. ORMs (gorm) and
# other Postgres drivers (lib/pq, go-sql-driver/mysql) drift off-stack.
# Warns (a Go service may legitimately have no DB yet, or use sqlite for a
# local tool — hence warn, not block).
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Warns (does not block). Self-skips when no go.mod is present.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

mods=$(git ls-files 2>/dev/null | grep -E '(^|/)go\.mod$' || true)
[ -n "$mods" ] || exit 0

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    m=$(grep -nE 'gorm\.io/gorm|github\.com/(lib/pq|go-sql-driver/mysql|jmoiron/sqlx)' "$f" 2>/dev/null \
        || true)
    [ -n "$m" ] && hits="$hits$f:"$'\n'"$(printf '%s' "$m" | sed 's/^/    /')"$'\n'
done <<< "$mods"

if [ -n "$hits" ]; then
    printf "%s\n" "Off-stack Go DB layer — stack is sqlc + pgx + Postgres:"
    printf "%s" "$hits" | sed 's/^/  /'
    printf "%s\n" "↳ migrate to sqlc + pgx."
fi
exit 0
