#!/usr/bin/python3
"""
PreToolUse hook: PLAN GATE.

Blocks Edit / Write / MultiEdit / NotebookEdit unless the model has written
a plan for the current task to .claude/PLAN.md AND the user (or autonomous
agent) has approved by touching .claude/PLAN.approved (mtime > PLAN.md mtime
AND within APPROVAL_MAX_AGE_SEC of now).

Reads JSON from stdin (Claude Code hook protocol). Exits:
  0 -> allow tool call
  2 -> block tool call (stderr shown to Claude)

Carve-outs (no plan required):
  - Edit/Write/MultiEdit whose target is .claude/PLAN.md itself
    (so the model can write/update the plan in the first place).
  - Single-file Edit where max(old_lines, new_lines) <= SMALL_EDIT_LINES.
  - Write where content lines <= SMALL_WRITE_LINES.
  - .claude/PLAN.skip exists -> consume (delete) and allow once.
  - CLAUDE_SKIP_PLAN_GATE=1 in env -> bypass entirely (single shell).

Project root resolution: walks up from `cwd` looking for `.claude/` or
`.git/`; falls back to cwd. PLAN.md lives at <root>/.claude/PLAN.md.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

BYPASS_ENV = "CLAUDE_SKIP_PLAN_GATE"
APPROVAL_MAX_AGE_SEC = 30 * 60
SMALL_EDIT_LINES = 3
SMALL_WRITE_LINES = 5
PLAN_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def project_root(cwd: Path) -> Path:
    p = cwd.resolve()
    for ancestor in [p, *p.parents]:
        if (ancestor / ".claude").is_dir():
            return ancestor
        if (ancestor / ".git").exists():
            return ancestor
    return p


def line_count(s: str) -> int:
    if not s:
        return 0
    return s.count("\n") + (0 if s.endswith("\n") else 1)


def is_small_edit(tool_name: str, tool_input: dict) -> bool:
    if tool_name == "Edit":
        old = tool_input.get("old_string") or ""
        new = tool_input.get("new_string") or ""
        return max(line_count(old), line_count(new)) <= SMALL_EDIT_LINES
    if tool_name == "Write":
        content = tool_input.get("content") or ""
        return line_count(content) <= SMALL_WRITE_LINES
    return False


def is_plan_file(tool_input: dict, root: Path) -> bool:
    fp = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not fp:
        return False
    try:
        target = Path(fp).resolve()
    except Exception:
        return False
    plan_md = (root / ".claude" / "PLAN.md").resolve()
    return target == plan_md


def block(reason: str, root: Path) -> int:
    # ADVISORY mode: nudge only, never block. Edit proceeds.
    # Restore blocking by changing `return 0` to `return 2`.
    sys.stderr.write(
        f"[plan-gate · advisory] {reason} For non-trivial work, plan first.\n"
    )
    return 0


def main() -> int:
    if os.environ.get(BYPASS_ENV) == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_name = payload.get("tool_name")
    if tool_name not in PLAN_TOOLS:
        return 0

    tool_input = payload.get("tool_input") or {}
    cwd_str = payload.get("cwd") or os.getcwd()
    cwd = Path(cwd_str)
    root = project_root(cwd)

    if is_plan_file(tool_input, root):
        return 0

    if is_small_edit(tool_name, tool_input):
        return 0

    plan_md = root / ".claude" / "PLAN.md"
    plan_approved = root / ".claude" / "PLAN.approved"
    plan_skip = root / ".claude" / "PLAN.skip"

    if plan_skip.exists():
        try:
            plan_skip.unlink()
        except Exception:
            pass
        return 0

    if not plan_md.exists():
        return block(
            "No plan found. Plan before code: "
            "write the plan first, then ask the user to approve.",
            root,
        )

    if not plan_approved.exists():
        return block(
            f"Plan exists at {plan_md} but has not been approved yet.",
            root,
        )

    now = time.time()
    plan_mtime = plan_md.stat().st_mtime
    appr_mtime = plan_approved.stat().st_mtime

    if appr_mtime < plan_mtime:
        return block(
            "Plan was modified after approval — approval is stale.",
            root,
        )

    age = now - appr_mtime
    if age > APPROVAL_MAX_AGE_SEC:
        return block(
            f"Approval is {int(age // 60)} minutes old "
            f"(max {APPROVAL_MAX_AGE_SEC // 60}). "
            "Re-approve for the current task.",
            root,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
