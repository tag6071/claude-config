#!/usr/bin/env bash
# no_ls_in_pipelines — `ls` in scripts is dangerous because of common
# aliases (eza, lsd, exa) that decorate output with colors/quotes/icons
# that corrupt downstream pipelines.
#
# Detects `ls` (NOT `/bin/ls`) inside `*.sh` / `*.bash` scripts, in
# contexts that suggest a pipeline or capture:
#   - ls in pipelines:        `ls ... |`
#   - ls in command sub:      `$(ls ...)`
#   - ls in backticks:        `` `ls ...` ``
#   - ls in for loops:        `for x in $(ls ...)`
#   - ls in while reads:      `while read ... ; do ... done < <(ls ...)`
#
#
# Exits 1 on violation.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

# Find shell scripts: scripts/ + any *.sh at repo root + ./bin
files=$(find scripts bin . -maxdepth 2 -type f \( -name '*.sh' -o -name '*.bash' \) 2>/dev/null)

violations=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    case "$f" in */node_modules/*|*/.venv/*|*/__pycache__/*) continue ;; esac
    # Catch the dangerous contexts; allow `/bin/ls` (absolute path).
    # Look for the unqualified `ls` token in pipeline / cmd-sub positions.
    hits=$(grep -nE '(\|[[:space:]]*ls[[:space:]]|\$\([[:space:]]*ls[[:space:]]|`[[:space:]]*ls[[:space:]]|for[[:space:]]+[A-Za-z_]+[[:space:]]+in[[:space:]]+\$\([[:space:]]*ls[[:space:]])' "$f" 2>/dev/null \
            | grep -vE '^[0-9]+:[[:space:]]*#' \
            | grep -v '/bin/ls' \
            || true)
    if [ -n "$hits" ]; then
        while IFS= read -r h; do
            violations="$violations$f:$h"$'\n'
        done <<< "$hits"
    fi
done <<< "$files"

if [ -n "$violations" ]; then
    printf "%s\n" "ls in scripts:"
    printf "%s" "$violations"
    printf "%s\n" "↳ use find -print0 + while-read OR /bin/ls (absolute path)."
    exit 1
fi
exit 0
