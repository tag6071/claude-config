#!/usr/bin/env bash
# forms_server_validation — the Go backend validates every request body it reads.
#
# Stack contract: validate on BOTH sides. The client uses rhf+zod (the OpenAPI
# contract is the shared source of truth), but the server is the real gatekeeper.
# A handler file that decodes a request body (json.Decode / io.ReadAll(r.Body))
# but contains no validation call is the classic "trusted the client" hole.
# Heuristic, file-granular: if a Go file reads a body but shows no validation
# signal (Validate/valid/ozzo/go-playground/a guard returning 400), it's flagged.
# No escape — the no_escape_comments lock bans bypass comments; fix the violation.
# Fails (blocks). Self-skips when no go.mod is present.

set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

git ls-files 2>/dev/null | grep -qE '(^|/)go\.mod$' || exit 0

gofiles=$(git ls-files '*.go' 2>/dev/null \
          | grep -vE '(^|/)(vendor)/' \
          | grep -vE '_test\.go$' || true)
[ -n "$gofiles" ] || exit 0

reads_body='json\.NewDecoder\([^)]*\)\.Decode\(|\.Decode\(&|io\.ReadAll\(r\.Body\)|ioutil\.ReadAll\(r\.Body\)'
validates='[Vv]alidate|\.Valid\(|go-playground/validator|ozzo-validation|StatusBadRequest|http\.Error\([^,]*,[^,]*,[[:space:]]*400'

hits=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    # only handler files (touch http.ResponseWriter) that read a body
    grep -qE 'http\.ResponseWriter' "$f" 2>/dev/null || continue
    found=$(grep -nE "$reads_body" "$f" 2>/dev/null || true)
    [ -n "$found" ] || continue
    grep -qE "$validates" "$f" 2>/dev/null && continue
    hits="$hits$f:"$'\n'"$(printf '%s' "$found" | head -3 | sed 's/^/    /')"$'\n'
done <<< "$gofiles"

if [ -n "$hits" ]; then
    printf "%s\n" "Go handler reads a request body but shows no validation — server must not trust the client:"
    printf "%s" "$hits" | head -40 | sed 's/^/  /'
    printf "%s\n" "↳ validate the decoded struct (reject with 400 on bad input) before using it."
    printf "%s\n" "↳ NO escape — validate the decoded struct (reject with 400) before using it."
    exit 1
fi
exit 0
