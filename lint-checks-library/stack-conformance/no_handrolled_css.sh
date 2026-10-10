#!/usr/bin/env bash
# no_handrolled_css — feature styling is Tailwind, not bespoke stylesheets.
#
# Stack contract: Tailwind utilities + tokens. A growing set of hand-written
# .css/.scss files (beyond the one global token/base sheet) is the slow drift
# into an unmaintainable parallel styling system. Warns (some files are
# legitimate — the global sheet, third-party imports) so a human can judge.
# Allowlisted: globals.css, index.css, App.css, theme.css, tokens.css.
# Warns (does not block). Self-skips when not a React project.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

pkgs=$(git ls-files 2>/dev/null | grep -E '(^|/)package\.json$' | grep -vE '(^|/)node_modules/' || true)
[ -n "$pkgs" ] || exit 0
echo "$pkgs" | xargs grep -lE '"react"[[:space:]]*:' 2>/dev/null | grep -q . || exit 0

allow='((^|/)(globals|index|App|theme)\.(css|scss)$|tokens\.(css|scss)$)'

extra=$(git ls-files '*.css' '*.scss' 2>/dev/null \
        | grep -vE '(^|/)(node_modules|dist|build|\.archive[a-zA-Z0-9._-]*)/' \
        | grep -vE "$allow" || true)

if [ -n "$extra" ]; then
    printf "%s\n" "Hand-written stylesheet(s) beyond the global token sheet — prefer Tailwind utilities:"
    printf '%s\n' "$extra" | sed 's/^/    /'
    printf "%s\n" "↳ move rules to Tailwind classes; keep one-off tokens in the global sheet."
fi
exit 0
