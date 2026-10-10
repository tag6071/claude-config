#!/usr/bin/env bash
# no_mock_server — mocks must not run as a second server/port.
#
# Stack contract: one server. Mock DATA via MSW (in-app, env-toggled); mock UI
# directions as routes (the ui-mocks skill, one static server). A json-server
# dep or a separate mock package.json with its own dev/start script is the
# anti-pattern this catches.
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Warns (does not block). Self-skips when no package.json is present.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

pkgs=$(git ls-files 2>/dev/null | grep -E '(^|/)package\.json$' | grep -vE '(^|/)node_modules/' || true)
[ -n "$pkgs" ] || exit 0

hits=""

# 1. json-server / mock-server style deps
dep=$(echo "$pkgs" | xargs grep -lE '"(json-server|mock-server|@mock-server)"[[:space:]]*:' 2>/dev/null || true)
[ -n "$dep" ] && hits="$hits  json-server/mock-server dependency in: $dep"$'\n'

# 2. a package.json under a mock* directory with its own server script
while IFS= read -r f; do
    [ -z "$f" ] && continue
    case "$f" in
        *mock*/package.json)
            grep -qE '"(dev|start|serve)"[[:space:]]*:' "$f" 2>/dev/null \
                && hits="$hits  separate mock app with a server script: $f"$'\n' ;;
    esac
done <<< "$pkgs"

if [ -n "$hits" ]; then
    printf "%s\n" "Mock running as its own server/port — use MSW or one static server:"
    printf "%s" "$hits"
    printf "%s\n" "↳ mock DATA → MSW (env-toggled, in-app); 3 UI directions → ui-mocks (one server)."
fi
exit 0
