#!/usr/bin/env bash
# gofmt_clean — every tracked .go file must match canonical gofmt output.
#
# golangci-lint does not check formatting by default, so drift accumulates
# silently until someone runs gofmt by hand and gets a 28-file diff mixed
# into their change. Catch it at the gate instead; the fix is always
# mechanical: `gofmt -w .`
#
# Fails on drift. Self-skips when no go.mod is present.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

git ls-files 2>/dev/null | grep -qE '(^|/)go\.mod$' || exit 0
command -v gofmt >/dev/null 2>&1 || exit 0

# Only tracked files — skips vendored/generated trees that aren't committed.
drifted=$(git ls-files '*.go' 2>/dev/null | xargs -r gofmt -l 2>/dev/null || true)

if [ -n "$drifted" ]; then
    printf "%s\n" "gofmt drift (fix: gofmt -w .):"
    printf "%s\n" "$drifted" | head -20
    exit 1
fi
exit 0
