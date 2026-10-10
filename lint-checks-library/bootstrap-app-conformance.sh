#!/usr/bin/env bash
# bootstrap-app-conformance — install the stack-conformance gate into one app.
#
# Idempotent. Mechanical half of the per-app foundation (the thin CLAUDE.md
# refactor is judgment, done separately). Safe to re-run: copies are no-clobber,
# the orchestrator is only generated when absent, the pre-commit hook is only
# installed when none exists.
#
# Usage:  bootstrap-app-conformance.sh <app-dir>
# Reads the pack from the lint-checks-library next to this script.

set -uo pipefail

APP="${1:?usage: bootstrap-app-conformance.sh <app-dir>}"
LIB="$(cd "$(dirname "$0")" && pwd)"
PACK="$LIB/stack-conformance"

cd "$APP" 2>/dev/null || { echo "✗ $APP: not a directory"; exit 2; }
git rev-parse --git-dir >/dev/null 2>&1 || { echo "✗ $APP: not a git repo — skipped"; exit 2; }
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
name="$(basename "$ROOT")"

mkdir -p scripts/lint-checks

# 1. Copy the stack-conformance checks (no-clobber — local edits are sacred).
cp -n "$PACK"/*.sh scripts/lint-checks/ 2>/dev/null || true
chmod +x scripts/lint-checks/*.sh 2>/dev/null || true

# 2. Generate the orchestrator from the template (only if absent).
if [ ! -f scripts/lint-anti-patterns.sh ]; then
    rows_file="$(mktemp)"
    cat > "$rows_file" <<'ROWS'
run_check "no_alien_lockfile"        scripts/lint-checks/no_alien_lockfile.sh        fail
run_check "frontend_framework"       scripts/lint-checks/frontend_framework.sh       fail
run_check "forms_competing_lib"      scripts/lint-checks/forms_competing_lib.sh      fail
run_check "forms_use_rhf"            scripts/lint-checks/forms_use_rhf.sh            warn
run_check "frontend_libs"            scripts/lint-checks/frontend_libs.sh            warn
run_check "no_mock_server"           scripts/lint-checks/no_mock_server.sh           warn
run_check "playwright_browsers_path" scripts/lint-checks/playwright_browsers_path.sh warn
run_check "edge_labels"              scripts/lint-checks/edge_labels.sh              warn
run_check "backend_stdlib_http"      scripts/lint-checks/backend_stdlib_http.sh      fail
run_check "backend_db_pgx"           scripts/lint-checks/backend_db_pgx.sh           warn
ROWS
    python3 - "$LIB/_template/lint-anti-patterns.sh" "$rows_file" > scripts/lint-anti-patterns.sh <<'PY'
import sys
tpl = open(sys.argv[1]).read()
rows = open(sys.argv[2]).read().rstrip("\n")
sys.stdout.write(tpl.replace("# {{CHECKS_BLOCK}}", rows))
PY
    rm -f "$rows_file"
    chmod +x scripts/lint-anti-patterns.sh
    echo "  + scripts/lint-anti-patterns.sh generated"
else
    echo "  = scripts/lint-anti-patterns.sh exists (left as-is)"
fi

# 3. WIP marker — app is pre-migration, gaps expected; gate reports, not blocks.
if [ ! -f .conformance-wip ]; then
    printf "%s\n" "Stack migration in progress. The conformance gate reports gaps as" \
        "warnings instead of blocking commits while this file exists." \
        "Close the gaps (see: bash scripts/lint-anti-patterns.sh), then delete" \
        "this file to make the gate a hard pre-commit block." > .conformance-wip
    echo "  + .conformance-wip dropped"
fi

# 4. Pre-commit hook — only if none exists (never clobber a user hook).
if [ ! -e .git/hooks/pre-commit ] && [ ! -f scripts/pre-commit ]; then
    sed 's#{{TEST_COMMAND_BLOCK}}#(no test gate wired yet — add your runner here)#' \
        "$LIB/_template/pre-commit" > scripts/pre-commit
    chmod +x scripts/pre-commit
    ln -sf ../../scripts/pre-commit .git/hooks/pre-commit
    echo "  + pre-commit hook wired"
else
    echo "  = pre-commit hook already present (left as-is)"
fi

echo "  → running gate:"
bash scripts/lint-anti-patterns.sh 2>&1 | tail -3 | sed 's/^/    /'
echo "✓ $name: conformance gate installed"
