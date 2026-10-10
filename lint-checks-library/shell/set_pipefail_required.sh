#!/usr/bin/env bash
# set_pipefail_required — every shell script must opt into safe-mode flags.
#
# Required: SOME explicit `set -<flag>` line in the first 10 lines that
# includes at minimum `pipefail`, `errexit`, or `nounset`. Concrete forms
# that pass:
#   set -euo pipefail   ← most common safe combo
#   set -uo pipefail    ← orchestrators that handle their own errors
#   set -eo pipefail    ← strict-error + safe-pipeline
#   set -e              ← bare errexit, minimal
#
# Exempt by design:
#   - Pure `exec` shims (every non-comment line is `exec` or blank)
#
# Exits 1 on violation.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

files=$(find scripts bin . -maxdepth 2 -type f \( -name '*.sh' -o -name '*.bash' \) 2>/dev/null \
        | sed 's|^\./||' \
        | grep -vE '(^|/)node_modules/' \
        | sort -u || true)

violations=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    # First 25 lines — wide enough for verbose comment headers + the
    # `set` line that conventionally lives just above the actual code.
    head_lines=$(head -25 "$f")
    # Exempt: pure exec shim (every non-shebang, non-comment, non-blank
    # line is `exec ...`). Catches 2-line backwards-compat wrappers.
    body=$(grep -vE '^\s*(#|$)' "$f" 2>/dev/null | head -5)
    if [ -n "$body" ] && ! echo "$body" | grep -qvE '^\s*exec\s'; then
        continue
    fi
    # Pass if any of these patterns appears in the first 10 lines:
    #   - line starts with `set -...` and contains `pipefail`
    #   - line starts with `set -...` and includes `e` or `u` flag
    # Together this covers `set -euo pipefail`, `set -uo pipefail`,
    # `set -eo pipefail`, `set -e`, `set -u`, etc.
    if echo "$head_lines" | grep -qE '^\s*set\s+[^#]*pipefail'; then
        continue
    fi
    if echo "$head_lines" | grep -qE '^\s*set\s+-[a-zA-Z]*[eu]'; then
        continue
    fi
    violations="$violations$f"$'\n'
done <<< "$files"

if [ -n "$violations" ]; then
    printf "%s\n" "shell scripts missing safe-mode flags:"
    printf "%s" "$violations" | sed 's/^/    /'
    printf "%s\n" "↳ add 'set -euo pipefail' (or 'set -uo pipefail' for orchestrators)."
    exit 1
fi
exit 0
