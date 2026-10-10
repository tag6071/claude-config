#!/usr/bin/env bash
# Inject lightweight per-session context — free tokens, deterministic.
# Installed by the `claudify` skill. See ~/.claude/skills/claudify/SKILL.md.

if ! git rev-parse --git-dir > /dev/null 2>&1; then
  exit 0
fi

echo "[branch] $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"

status=$(git status --short 2>/dev/null | head -20)
if [ -n "$status" ]; then
  echo "[status]"
  echo "$status"
fi

echo "[recent commits]"
git log --oneline -5 2>/dev/null
