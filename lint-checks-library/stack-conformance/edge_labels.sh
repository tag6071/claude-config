#!/usr/bin/env bash
# edge_labels — a containerized web app should carry the edge labels.
#
# Exposure contract: an app container publishes to 127.0.0.1 ONLY and
# carries caddy-docker-proxy labels so the edge serves it at <app>.home.arpa
# behind SSO — the single-entry floor. This check warns when a compose
# file publishes a loopback port but has no `caddy:` label (so a Phase-B session
# knows to add the block when it containerizes the app).
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Warns (does not block). Self-skips when no docker-compose.yml is present.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

composes=$(git ls-files 2>/dev/null | grep -E '(^|/)docker-compose\.ya?ml$' || true)
[ -n "$composes" ] || exit 0

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    # Publishes a loopback port?
    grep -qE '127\.0\.0\.1:[0-9]+' "$f" 2>/dev/null || continue
    # Already carries an edge label?
    grep -qE '^[[:space:]]*caddy:' "$f" 2>/dev/null && continue
    hits="$hits  $f"$'\n'
done <<< "$composes"

if [ -n "$hits" ]; then
    name="$(basename "$ROOT")"
    port="$(grep -hoE '127\.0\.0\.1:[0-9]+' "$composes" 2>/dev/null | head -1 | cut -d: -f2)"
    : "${port:=<port>}"
    printf "%s\n" "Containerized app with no edge labels — add the block to route it at $name.home.arpa behind SSO:"
    printf "%s\n" "$hits"
    printf "%s\n" "    labels:"
    printf "%s\n" "      caddy: $name.home.arpa"
    printf "%s\n" "      caddy.tls: internal"
    printf "%s\n" "      caddy.import_0: accesslog"
    printf "%s\n" "      caddy.import_1: sso             # SSO gate — single-entry floor"
    printf "%s\n" "      caddy.reverse_proxy: 127.0.0.1:$port"
    printf "%s\n" "↳ keep the port 127.0.0.1-only."
fi
exit 0
