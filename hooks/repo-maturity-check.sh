#!/usr/bin/env bash
# repo-maturity-check — SessionStart hook.
#
# Surfaces missing scaffolding on every session start so the AI sees
# what's missing without relying on user memory. Cheap (~50ms): one
# git-call + three file probes.
#
# Output is a `[maturity]` bracket-tag block that follows the same
# convention as session-context.sh's [branch] / [status] / [recent commits].
#
# Tunables:
#   MIN_COMMITS  — projects with fewer commits are skipped (default 10)
#   MIN_AGE_DAYS — projects younger than this are skipped (default 2)
#
# To suppress for a specific repo, drop a sentinel:
#   touch .claude/maturity-check.skip

MIN_COMMITS="${CLAUDE_MATURITY_MIN_COMMITS:-10}"
MIN_AGE_DAYS="${CLAUDE_MATURITY_MIN_AGE_DAYS:-2}"

# Bail if not a git repo at all.
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# Per-repo opt-out sentinel.
[ -f .claude/maturity-check.skip ] && exit 0

commits=$(git rev-list --count HEAD 2>/dev/null || echo 0)
first_ts=$(git log --reverse --format="%ct" 2>/dev/null | head -1)
now_ts=$(date +%s)
age_days=$(( (now_ts - ${first_ts:-$now_ts}) / 86400 ))

# Skip young / small repos — scaffolding wouldn't earn its keep yet.
if [ "$commits" -lt "$MIN_COMMITS" ] || [ "$age_days" -lt "$MIN_AGE_DAYS" ]; then
    exit 0
fi

# Probe for the three scaffolding artifacts. Each missing one names the
# skill that installs it.
missing=()
[ ! -f CLAUDE.md ] && missing+=("  CLAUDE.md → /claudify")
[ ! -f docs/CODE_MAP.md ] && missing+=("  docs/CODE_MAP.md → /claudify deep")
[ ! -f scripts/lint-anti-patterns.sh ] && missing+=("  scripts/lint-anti-patterns.sh → /install-lint-rails")

if [ "${#missing[@]}" -eq 0 ]; then
    exit 0
fi

echo "[maturity] $commits commits over $age_days days — recommended scaffolding missing:"
printf '%s\n' "${missing[@]}"
