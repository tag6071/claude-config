#!/usr/bin/env bash
# a11y_lint_enabled — don't disable Biome's accessibility rules.
#
# Stack contract: Biome ships its `a11y` lint group ON by default — free
# accessibility enforcement (labels, alt text, valid aria, keyboard handlers).
# This check exists so nobody quietly turns it off. It does NOT require you to
# add anything; it only fails if the Biome config explicitly disables a11y.
# No escape — re-enable a11y (silence individual rules inline if truly needed).
# Fails (blocks). Self-skips when no Biome config is present.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

cfgs=$(git ls-files 2>/dev/null | grep -E '(^|/)biome\.jsonc?$' || true)
[ -n "$cfgs" ] || exit 0

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    # whole-linter kill, or the a11y group set to "off"/false (allow whitespace/newlines)
    if grep -qE '"a11y"[[:space:]]*:[[:space:]]*"off"' "$f" 2>/dev/null \
       || grep -Pzoq '"a11y"\s*:\s*\{[^}]*"recommended"\s*:\s*false' "$f" 2>/dev/null \
       || grep -Pzoq '"linter"\s*:\s*\{[^}]*"enabled"\s*:\s*false' "$f" 2>/dev/null; then
        hits="$hits  $f"$'\n'
    fi
done <<< "$cfgs"

if [ -n "$hits" ]; then
    printf "%s\n" "Biome accessibility linting is disabled — re-enable the a11y group:"
    printf "%s" "$hits"
    printf "%s\n" "↳ keep \"a11y\" recommended on; silence a specific rule inline only if truly needed."
    exit 1
fi
exit 0
