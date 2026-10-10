#!/usr/bin/python3
"""
PreToolUse:Bash hook — enforce the LESSONS.md provenance trail.

When a `git commit` has a `fix:` or `fix(scope):` subject, this hook blocks
the commit if neither `docs/LESSONS.md` nor `LESSONS.md` is in the staged
files. The intent: every bug-fix commit either ships an anti-repeat entry,
or makes an explicit decision that this fix doesn't need one.

The hook is a steer, not a wall — the bypass is one env var. The point is
to make the decision conscious, not to force a docs change every time.

Reads JSON from stdin (Claude Code hook protocol). Exits:
  0 -> allow commit (LESSONS.md staged, or fix doesn't qualify, or bypass set)
  2 -> block commit (stderr shown to Claude)

Activation conditions (ALL must hold for the hook to engage):
  - the staged commit message subject starts with `fix:` or `fix(...):` AND
  - `docs/LESSONS.md` (or `LESSONS.md` at repo root) exists in the repo AND
  - `docs/LESSONS.md` (or `LESSONS.md`) is NOT in the staged diff.

If LESSONS.md doesn't exist in the repo at all, the hook stays silent —
the indexability pattern hasn't been adopted here yet, and forcing it via
this hook would be intrusive. Run `/claudify deep` first.

Opt-out (single shell): CLAUDE_FIX_NO_LESSON=1
Hook-wide bypass:        CLAUDE_SKIP_LESSONS_HOOK=1
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

BYPASS_ENV = "CLAUDE_SKIP_LESSONS_HOOK"
PER_FIX_OK_ENV = "CLAUDE_FIX_NO_LESSON"


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"


def get_repo_root() -> Path | None:
    rc, out = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    if rc != 0:
        return None
    return Path(out)


def extract_commit_subject(command: str) -> str | None:
    """Best-effort extraction of the commit subject from a `git commit` shell command.

    Handles common forms:
      git commit -m "subject"
      git commit -m 'subject'
      git commit -m "$(cat <<'EOF' ... EOF )"  (HEREDOC — first non-empty line of body)
      git commit -m subject (unquoted single word)

    Returns the subject line or None if we cannot determine it.
    """
    # HEREDOC form — extract the first non-empty line inside.
    # `[^\n]*\n` (not `\s*\n`) because \s eats the newline we need to anchor on.
    here = re.search(r"<<\s*['\"]?(\w+)['\"]?[^\n]*\n(.*?)\n\s*\1", command, re.DOTALL)
    if here:
        body = here.group(2)
        for line in body.splitlines():
            line = line.strip()
            if line:
                return line

    # Plain -m "subject" or -m 'subject'
    m = re.search(r"-m\s+(['\"])(.*?)\1", command, re.DOTALL)
    if m:
        return m.group(2).splitlines()[0].strip() if m.group(2) else None

    # -m subject (unquoted)
    m = re.search(r"-m\s+(\S+)", command)
    if m:
        return m.group(1)

    return None


def is_fix_commit(subject: str) -> bool:
    return bool(re.match(r"^fix(\([^)]*\))?\s*:", subject))


def get_staged_files(repo: Path) -> list[str]:
    rc, out = run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], repo
    )
    if rc != 0:
        return []
    return [f for f in out.splitlines() if f]


def find_lessons_path(repo: Path) -> Path | None:
    """Return the repo-relative LESSONS.md path if one exists."""
    for rel in ("docs/LESSONS.md", "LESSONS.md"):
        if (repo / rel).exists():
            return Path(rel)
    return None


def main() -> int:
    if os.environ.get(BYPASS_ENV) == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""

    if not re.search(r"\bgit\s+commit\b", command):
        return 0

    subject = extract_commit_subject(command)
    if not subject or not is_fix_commit(subject):
        return 0

    repo = get_repo_root()
    if not repo:
        return 0

    lessons_rel = find_lessons_path(repo)
    if lessons_rel is None:
        # Repo hasn't adopted the indexability pattern — stay silent.
        return 0

    # Per-commit bypass — user has explicitly decided this fix doesn't warrant a lesson.
    if os.environ.get(PER_FIX_OK_ENV) == "1":
        return 0

    staged = get_staged_files(repo)
    if str(lessons_rel) in staged:
        return 0

    # We have a fix commit, LESSONS.md exists, but LESSONS.md is not staged.
    # Block with a clear, actionable message.
    sys.stderr.write(
        "BLOCKED: fix commit without a LESSONS.md entry.\n"
        "\n"
        f"  Commit subject: {subject}\n"
        f"  Expected entry in: {lessons_rel}\n"
        "\n"
        "Decide one of:\n"
        f"  1. Add a row to {lessons_rel} with this commit's intended hash and stage it.\n"
        "     (Use the commit subject as the rule; cite the commit you're about to make.)\n"
        f"  2. This fix doesn't warrant a lesson (trivial / one-off): export {PER_FIX_OK_ENV}=1\n"
        "     then re-run the commit.\n"
        "\n"
        "Why: the LESSONS.md provenance trail is how this repo stays self-documenting\n"
        "across AI sessions. Skipping it silently turns this file into noise.\n"
        f"\nHook-wide bypass (single shell): export {BYPASS_ENV}=1\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
