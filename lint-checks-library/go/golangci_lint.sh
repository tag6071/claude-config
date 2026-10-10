#!/usr/bin/env bash
# golangci_lint — run the BLESSED Go linter as the quality gate.
#
# golangci-lint is the blessed Go linter (bundles errcheck, govet, staticcheck,
# ineffassign, unused, gosimple …) — a single binary, install once. This is the
# real Go "code quality" gate the toolchain rule points at; gofmt + go vet are
# the always-bundled floor beneath it.
#   - installed  → run it; non-zero exit on findings (severity in pack.toml
#                  decides block vs warn; Step 5a downgrades dirty repos).
#   - not installed → nudge to install (the regex fallbacks unchecked_errors /
#                  no_init_funcs cover the basics meanwhile).
# No per-line escape — fix the finding or tune `.golangci.yml`.
# Self-skips when no go.mod is present.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

git ls-files 2>/dev/null | grep -qE '(^|/)go\.mod$' || exit 0

if ! command -v golangci-lint >/dev/null 2>&1; then
    printf "%s\n" "golangci-lint not installed — the blessed Go linter (errcheck/staticcheck/…):"
    printf "%s\n" "  go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest"
    printf "%s\n" "↳ until then only the regex fallback checks run (unchecked_errors, no_init_funcs)."
    exit 1
fi

if ! out=$(golangci-lint run ./... 2>&1); then
    printf "%s\n" "golangci-lint findings:"
    printf "%s\n" "$out" | head -40
    printf "%s\n" "↳ fix the finding, or tune .golangci.yml. (errcheck etc. live here, not in a hand-rolled check.)"
    exit 1
fi
exit 0
