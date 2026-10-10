#!/usr/bin/env bash
# design_system_primitives — interactive primitives must be the shadcn/Radix
# components, not hand-rolled ones that ship accessibility bugs.
#
# Stack contract: shadcn/ui (Radix). A native <select> and a hand-rolled modal
# (a bare <div role="dialog">/aria-modal, or a JSX <dialog>) reinvent solved
# problems and lose focus-trap, aria-modal semantics, and Escape/restore-focus.
# Use shadcn `Select` / `Dialog` instead. Only fires once shadcn is installed
# (a components/ui dir exists) — it won't demand a component you don't have.
# No escape — the no_escape_comments lock bans bypass comments. Fix the violation.
# Fails (blocks). Self-skips when not a React project or shadcn isn't present.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

pkgs=$(git ls-files 2>/dev/null | grep -E '(^|/)package\.json$' | grep -vE '(^|/)node_modules/' || true)
[ -n "$pkgs" ] || exit 0
echo "$pkgs" | xargs grep -lE '"react"[[:space:]]*:' 2>/dev/null | grep -q . || exit 0

# shadcn present? (its components live in components/ui). If not, stay quiet.
git ls-files 2>/dev/null | grep -qE '(^|/)components/ui/' || exit 0

# Scan app code, NOT the shadcn components themselves (they wrap Radix legitimately).
src=$(git ls-files '*.tsx' '*.jsx' 2>/dev/null \
      | grep -vE '(^|/)(node_modules|dist|build|\.archive[a-zA-Z0-9._-]*)/' \
      | grep -vE '(^|/)components/ui/' || true)
[ -n "$src" ] || exit 0

# native <select…>, JSX <dialog…>, or a bare element carrying dialog/modal roles.
pat='<select[[:space:]/>]|<dialog[[:space:]/>]|role=("|.)dialog|aria-modal'

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    found=$(grep -nE "$pat" "$f" 2>/dev/null || true)
    [ -n "$found" ] && hits="$hits$f:"$'\n'"$(printf '%s' "$found" | head -5 | sed 's/^/    /')"$'\n'
done <<< "$src"

if [ -n "$hits" ]; then
    printf "%s\n" "Hand-rolled UI primitive — use the shadcn/Radix component (focus-trap + a11y for free):"
    printf "%s" "$hits" | head -40 | sed 's/^/  /'
    printf "%s\n" "↳ native <select> → shadcn Select; custom modal/overlay → shadcn Dialog."
    printf "%s\n" "↳ NO escape — use the shadcn/Radix component (Select/Dialog)."
    exit 1
fi
exit 0
