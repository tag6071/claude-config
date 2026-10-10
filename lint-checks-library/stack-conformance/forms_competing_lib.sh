#!/usr/bin/env bash
# forms_competing_lib — forms must use react-hook-form + zod. Fails on rivals.
#
# Stack contract: react-hook-form + zod. Formik, react-final-form, redux-form
# are competing libraries and out of contract.
# No escape — migrate the form to react-hook-form + zod.
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
    m=$(grep -nE '"(formik|react-final-form|final-form|redux-form)"[[:space:]]*:' "$f" 2>/dev/null || true)
    [ -n "$m" ] && hits="$hits$f:"$'\n'"$(printf '%s' "$m" | sed 's/^/    /')"$'\n'
done <<< "$pkgs"

if [ -n "$hits" ]; then
    printf "%s\n" "Competing form library — stack is react-hook-form + zod:"
    printf "%s" "$hits" | sed 's/^/  /'
    exit 1
fi
exit 0
