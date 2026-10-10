#!/usr/bin/env bash
# PostToolUse hook: COMMIT NUDGER.
#
# After Edit/Write/MultiEdit, if the working tree is dirty, inject a one-line
# reminder asking the model to commit at the next green checkpoint. Advisory
# only — does NOT block.
#
# The model's running checks (tests/lint/format/typecheck) are responsible
# for confirming green. This hook just makes "you forgot to commit" expensive
# to ignore by surfacing it after every edit.
#
# Bypass: export CLAUDE_SKIP_COMMIT_NUDGER=1

[ "${CLAUDE_SKIP_COMMIT_NUDGER:-}" = "1" ] && exit 0

payload=$(cat)
cwd=$(printf '%s' "$payload" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$cwd" ] && cwd="$PWD"

git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

status=$(git -C "$cwd" status --porcelain 2>/dev/null)
[ -z "$status" ] && exit 0

changed_count=$(printf '%s\n' "$status" | grep -c .)

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "[commit-nudger] working tree dirty (${changed_count} changed). At the next green checkpoint (tests + lint + format + typecheck PASS) — COMMIT before the next edit. Per ~/.claude/CLAUDE.md: 'Commit after every green checkpoint... Non-negotiable.'"
  }
}
EOF
