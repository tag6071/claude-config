#!/usr/bin/env bash
# no_alien_lockfile — JS projects must use Bun. Fails on npm/yarn/pnpm lockfiles.
#
# Stack contract: Vite+Bun. The only allowed JS lockfile is bun.lockb / bun.lock.
# No escape — switch to Bun:  rm <lock> node_modules && bun install
# Fails (blocks). Self-skips when no alien lockfile is present.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

hits=$(git ls-files 2>/dev/null \
       | grep -E '(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml)$' \
       | grep -vE '(^|/)node_modules/' || true)

if [ -n "$hits" ]; then
    printf "%s\n" "Alien JS lockfile(s) — stack is Bun (use bun.lockb):"
    printf "%s\n" "$hits" | sed 's/^/  /'
    printf "%s\n" "↳ fix: rm the lockfile + node_modules, then 'bun install'."
    exit 1
fi
exit 0
