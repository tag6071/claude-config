#!/usr/bin/env bash
# Stop hook: TEST GATE. Blocks the stop when the most recent commit is a
# feat: or fix: that touched user-facing files but included no test files.
# On homeserver (autonomous) this forces the agent to either write the test now
# or commit a chore: that justifies skipping — keeps autonomous shipping
# honest about coverage.
#
# WIP / uncommitted changes are NOT gated — only the most recent commit.
# Emergency bypass: export CLAUDE_SKIP_TEST_GATE=1

[ "${CLAUDE_SKIP_TEST_GATE:-}" = "1" ] && exit 0

cwd="${CLAUDE_PROJECT_DIR:-$PWD}"
git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
git -C "$cwd" rev-parse HEAD >/dev/null 2>&1 || exit 0

msg=$(git -C "$cwd" log -1 --pretty=%s 2>/dev/null)

# Only gate feat: / fix: commits. refactor/chore/docs/style/test pass through.
printf '%s' "$msg" | grep -qE '^(feat|fix)(\([^)]+\))?:' || exit 0

files=$(git -C "$cwd" show --name-only --pretty=format: HEAD 2>/dev/null)

# Same UI/CLI/TUI scope as the user-flow-test skill
ui_pattern='(^|/)(components|pages|views|routes|screens|templates|bin|cmd)/|src/cli/|\.(tsx|jsx|svelte|vue|html)$'
test_pattern='(^|/)(tests?|spec|__tests__)/|\.(test|spec)\.[a-zA-Z]+$'

ui_changed=$(printf '%s\n' "$files" | grep -E -i "$ui_pattern" || true)
[ -z "$ui_changed" ] && exit 0

test_included=$(printf '%s\n' "$files" | grep -E -i "$test_pattern" || true)
[ -n "$test_included" ] && exit 0

files_list=$(printf '%s\n' "$ui_changed" | head -5 | sed 's/^/  - /')

cat <<EOF
{
  "decision": "block",
  "reason": "TEST GATE blocked stop. Last commit was '${msg}' and touched user-facing files:\n${files_list}\n\nNo test files were included. Per the user-flow-test rule, make a follow-up commit NOW that is ONE of:\n  (a) 'test: <thing>' containing a real user-flow test you wrote and ran here, or\n  (b) 'test: verify existing coverage for <thing>' if existing tests already cover it — run them, show passing output, then commit (empty commit is fine), or\n  (c) 'chore: <thing> — no test needed because <reason>' if the change is trivially safe (rename, comment, no-behavior refactor).\n\nThis is autonomous mode — pick (a), (b), or (c) yourself, then the gate clears. Emergency bypass: export CLAUDE_SKIP_TEST_GATE=1"
}
EOF
