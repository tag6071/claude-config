#!/usr/bin/python3
"""
PreToolUse hook: THREE-QUESTIONS GATE.

Blocks state-mutating Bash commands unless the model has answered
the three discipline-forcer questions (Q1/Q2/Q3) and written them
to <project-root>/.claude/3Q.md within the last THREE_Q_MAX_AGE_SEC.

The three questions (per ~/.claude/skills/3q/SKILL.md
and ~/.claude/lessons/three-questions.md):
  Q1 — Can't it be automated?
  Q2 — How did we get into this problem in the first place?
  Q3 — How can we not fall into this trap again?

If any of those gaps is open, the proposed mutation is suspect —
gather evidence / build durability first.

Reads JSON from stdin (Claude Code hook protocol). Exits:
  0 -> allow tool call
  2 -> block tool call (stderr shown to Claude)

Match set (mutation patterns):
  rr apply
  ansible-playbook ... (without --check / --syntax-check)
  terraform apply | tofu apply
  kubectl apply | kubectl create | kubectl delete | kubectl patch
  git push --force | git push -f | git push --force-with-lease

Carve-outs (no audit required):
  - Read-only Bash (the hook only triggers on the patterns above).
  - <root>/.claude/3Q.skip exists -> consume (delete) and allow once.
  - CLAUDE_SKIP_3Q_GATE=1 in env -> bypass entirely (single shell).

Project root resolution: walks up from `cwd` looking for `.claude/`
or `.git/`; falls back to cwd. 3Q.md lives at <root>/.claude/3Q.md.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

BYPASS_ENV = "CLAUDE_SKIP_3Q_GATE"
THREE_Q_MAX_AGE_SEC = 30 * 60  # 30 minutes

# Patterns for state-mutating commands. Each is a regex applied to
# the full Bash `command` string. Start narrow; expand as we find
# escape gaps.
MUTATION_PATTERNS = [
    # IaC mutations
    r"\brr\s+(apply)\b",
    r"\buv\s+run\s+rr\s+(apply)\b",
    # Generic Ansible mutation (not dry-run)
    # Match `ansible-playbook` followed by NO --check or --syntax-check
    # later in the command. We do a coarse check: pattern matches if
    # ansible-playbook appears AND neither --check nor --syntax-check
    # is present.
    # Handled by a separate two-stage check below — not via regex.
    # Terraform / OpenTofu
    r"\b(terraform|tofu)\s+apply\b",
    # Kubernetes mutations
    r"\bkubectl\s+(apply|create|delete|patch|replace|edit)\b",
    # Destructive git
    r"\bgit\s+push\s+(--force|-f|--force-with-lease)\b",
]


def project_root(cwd: Path) -> Path:
    p = cwd.resolve()
    for ancestor in [p, *p.parents]:
        if (ancestor / ".claude").is_dir():
            return ancestor
        if (ancestor / ".git").exists():
            return ancestor
    return p


# Ansible tags that only READ host/device state (no writes). A playbook run
# scoped via --tags ENTIRELY to these is read-only and must not trip the gate.
# Convention: `validation` is the IaC read-back tag.
READONLY_ANSIBLE_TAGS = {"validation", "validate", "read", "readback"}


def _ansible_is_readonly(command: str) -> bool:
    """True if an `ansible-playbook` invocation cannot mutate state.

    Read-only signals:
      - a dry-run / inspection flag: --check, --syntax-check, --list-tasks,
        --list-hosts. NOTE: --diff is NOT here — `ansible-playbook --diff`
        WITHOUT --check still APPLIES changes (it only prints them), so a bare
        --diff run is a mutation and stays gated.
      - the run is scoped via --tags/-t to ONLY read-only tags (every tag in
        the value is in READONLY_ANSIBLE_TAGS). A mixed list that also carries
        a write tag (e.g. `--tags validation,deploy`) is NOT read-only and
        stays gated.
    """
    if re.search(r"--(check|syntax-check|list-tasks|list-hosts)\b", command):
        return True
    m = re.search(r"(?:--tags|-t)[=\s]+([A-Za-z0-9_,\-]+)", command)
    if m:
        tags = {t for t in m.group(1).split(",") if t}
        if tags and tags <= READONLY_ANSIBLE_TAGS:
            return True
    return False


def is_mutation(command: str) -> tuple[bool, str]:
    """Return (is_mutation, matched_pattern_description)."""
    for pat in MUTATION_PATTERNS:
        if re.search(pat, command):
            return True, pat

    # Ansible-playbook: a mutation UNLESS the run is provably read-only — a
    # dry-run/inspection flag, or scoped to read-only --tags. See
    # _ansible_is_readonly for what counts.
    if re.search(r"\bansible-playbook\b", command):
        if not _ansible_is_readonly(command):
            return True, "ansible-playbook (without --check / read-only --tags)"

    return False, ""


def _read_stdin_json() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def _exit_block(message: str) -> None:
    # ADVISORY mode: nudge only, never block. Command proceeds.
    # Restore blocking by changing the first line of the message to a 1-liner
    # and sys.exit(0) back to sys.exit(2).
    first = message.splitlines()[0] if message else "[three-questions-gate]"
    print(f"{first}  (advisory — proceeding; consider /3q for destructive ops)",
          file=sys.stderr)
    sys.exit(0)


def _exit_allow() -> None:
    sys.exit(0)


def main() -> None:
    # Single-shell bypass
    if os.environ.get(BYPASS_ENV) == "1":
        _exit_allow()

    payload = _read_stdin_json()
    tool_name = payload.get("tool_name") or payload.get("tool") or ""
    if tool_name != "Bash":
        # Hook only gates Bash; other tools pass through.
        _exit_allow()

    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") or ""
    if not command:
        _exit_allow()

    mutates, matched = is_mutation(command)
    if not mutates:
        _exit_allow()

    # Resolve project root
    session_cwd = payload.get("cwd") or os.getcwd()
    root = project_root(Path(session_cwd))
    claude_dir = root / ".claude"
    three_q_path = claude_dir / "3Q.md"
    skip_path = claude_dir / "3Q.skip"

    # One-shot bypass via skip file
    if skip_path.exists():
        try:
            skip_path.unlink()
        except OSError:
            pass
        _exit_allow()

    # Require 3Q.md exists and is fresh
    if not three_q_path.exists():
        _exit_block(
            f"[three-questions-gate] BLOCKED — matched mutation pattern:\n"
            f"    {matched}\n"
            f"    command: {command}\n\n"
            f"No three-questions audit found at:\n"
            f"    {three_q_path}\n\n"
            f"Before running this, answer ALL THREE questions in writing\n"
            f"(see ~/.claude/skills/3q/SKILL.md):\n\n"
            f"  Q1  Can't it be automated?\n"
            f"  Q2  How did we get into this in the first place?\n"
            f"  Q3  How can we not fall into this trap again?\n\n"
            f"If any answer is 'I don't know' — that gap is the work,\n"
            f"not a reason to proceed.\n\n"
            f"Invoke the skill: /3q\n"
            f"Or write {three_q_path} directly using the SKILL.md template.\n\n"
            f"Escape valves (sparingly):\n"
            f"  - touch {skip_path}                   # one-shot bypass\n"
            f"      (run this in a SEPARATE Bash call BEFORE the gated command —\n"
            f"       a same-call `touch …; cmd` is evaluated as one string and\n"
            f"       still blocks, because the touch hasn't run at hook time)\n"
            f"  - export {BYPASS_ENV}=1               # shell-session bypass\n"
        )

    age = time.time() - three_q_path.stat().st_mtime
    if age > THREE_Q_MAX_AGE_SEC:
        _exit_block(
            f"[three-questions-gate] BLOCKED — matched mutation pattern:\n"
            f"    {matched}\n"
            f"    command: {command}\n\n"
            f"Three-questions audit at {three_q_path} is\n"
            f"{int(age / 60)} minutes old (max {THREE_Q_MAX_AGE_SEC // 60} minutes).\n\n"
            f"Re-run /3q for a fresh audit. The discipline\n"
            f"is that the answers reflect the CURRENT proposed action —\n"
            f"a stale audit doesn't.\n\n"
            f"Escape valves:\n"
            f"  - touch {skip_path}                   # one-shot bypass\n"
            f"      (run this in a SEPARATE Bash call BEFORE the gated command —\n"
            f"       a same-call `touch …; cmd` is evaluated as one string and\n"
            f"       still blocks, because the touch hasn't run at hook time)\n"
            f"  - export {BYPASS_ENV}=1               # shell-session bypass\n"
        )

    _exit_allow()


if __name__ == "__main__":
    main()
