#!/usr/bin/python3
"""
PreToolUse:Task/Agent hook: DELEGATE GATE (anti-blind-handoff).  App-agnostic.

Kills the recurring failure: the model delegates WATCHABLE, course-correctable
app-work (refactor / implement / fix / deploy / rebrand) to a background
subagent "for clean context", then sits idle while an unwatched agent produces
work the user can't see live or steer — and that the user then has to re-fix.

The user's standing rule (paraphrased from repeated feedback): quality-critical
work the user cares about belongs in the MAIN THREAD, verified step by step, not
handed to a blind agent. Soft intent failed "over and over"; this gives it teeth.

WHAT IT GATES (only writes-capable, build-shaped delegations)
-------------------------------------------------------------
ALLOW silently:
  - Read-only fan-out subagents: Explore, db-explorer, claude-code-guide,
    statusline-setup, Plan  (these can't mutate the user's app — exactly what
    background agents are GOOD at).
  - Any write-capable agent whose prompt is research/search only (no build verb).

BLOCK (exit 2) unless overridden:
  - Write-capable subagent (general-purpose / claude / fork / unknown) whose
    prompt or description contains a build/mutate verb (implement, refactor,
    fix, deploy, migrate, rewrite, rebrand, strip, ...).

RELEASE (any one clears the gate — no infinite trap):
  1. Read-only subagent type            -> allow.
  2. No build verb in prompt/description-> allow (research/search delegation).
  3. Explicit `DELEGATE-OK: <reason>` line in the Task prompt OR description,
     naming why this specifically can't be done in the watched main thread
     (genuinely parallel writes needing worktree isolation, a long mechanical
     sweep over 100s of files, an explicitly user-requested background run...).
  4. CLAUDE_ALLOW_DELEGATE=1 in env     -> bypass (single shell).

Hook protocol: reads JSON on stdin.  Exit 0 allow · exit 2 block (stderr -> model).

Self-test:  python3 delegate-gate.py --selftest
"""
from __future__ import annotations

import json
import os
import re
import sys

BYPASS_ENV = "CLAUDE_ALLOW_DELEGATE"

# Subagent types that physically cannot mutate the user's app (read-only / planning).
# Background delegation to these is GOOD and never gated.
READ_ONLY_TYPES = {
    "explore",
    "db-explorer",
    "claude-code-guide",
    "statusline-setup",
    "plan",
}

# Build/mutate verbs that mark a delegation as real app-work the user wants watched.
# Matched case-insensitively as whole words against prompt + description.
BUILD_VERBS = [
    "implement", "build", "refactor", "rewrite", "rework", "fix", "patch",
    "add", "create", "write", "edit", "modify", "change", "update", "replace",
    "delete", "remove", "rename", "migrate", "deploy", "redeploy", "install",
    "scaffold", "rebrand", "strip", "integrate", "wire up", "wire-up", "port",
    "refactoring", "implementing", "deploying", "migrating", "fixing",
]
BUILD_RE = re.compile(r"(?<![\w-])(" + "|".join(re.escape(v) for v in BUILD_VERBS) + r")(?![\w-])", re.I)

# The override token. Must be followed by a non-trivial reason (>= ~8 chars).
OVERRIDE_RE = re.compile(r"DELEGATE-OK\s*:\s*\S.{7,}", re.I | re.S)


def decide(tool_input: dict) -> tuple[bool, str]:
    """Return (block, reason). block=False -> allow."""
    subtype = str(tool_input.get("subagent_type") or "").strip().lower()
    prompt = str(tool_input.get("prompt") or "")
    desc = str(tool_input.get("description") or "")
    blob = f"{desc}\n{prompt}"

    if subtype in READ_ONLY_TYPES:
        return False, ""

    if OVERRIDE_RE.search(blob):
        return False, ""

    m = BUILD_RE.search(blob)
    if not m:
        return False, ""  # research/search delegation — fine to background

    return True, m.group(1)


BLOCK_MSG = """\
BLOCKED by ~/.claude/hooks/delegate-gate.py — you are about to hand WRITE-CAPABLE
app-work (verb: "{verb}", subagent: "{subtype}") to a background subagent you
cannot watch live or course-correct.

This is the exact pattern the user has had to re-fix "over and over": delegate for
"clean context", go idle, get back work that drifted and needs re-doing. The
default is the OPPOSITE — do build/refactor/fix/deploy work in the MAIN THREAD,
verified step by step, where the user can see and steer it.

To proceed, pick one:
  • Do the work HERE in the main thread (preferred — that's why this gate exists).
  • If delegation is genuinely the right call (parallel writes needing worktree
    isolation, a long mechanical sweep, or the user explicitly asked for a
    background run), add a line to the Task prompt/description:
        DELEGATE-OK: <why this can't be done in the watched main thread>
    and state that same justification to the user in chat.

Emergency bypass (user-set, single shell only): export {env}=1
"""


def main() -> int:
    if os.environ.get(BYPASS_ENV) == "1":
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # unparseable -> fail open, never wedge the harness

    if payload.get("tool_name") not in ("Task", "Agent"):
        return 0

    tool_input = payload.get("tool_input") or {}
    block, verb = decide(tool_input)
    if not block:
        return 0

    subtype = str(tool_input.get("subagent_type") or "(default)").strip() or "(default)"
    sys.stderr.write(BLOCK_MSG.format(verb=verb, subtype=subtype, env=BYPASS_ENV))
    return 2


# --------------------------------------------------------------------------- #
def _selftest() -> int:
    cases = [
        # (tool_input, expect_block)
        ({"subagent_type": "Explore", "prompt": "refactor everything"}, False),
        ({"subagent_type": "general-purpose", "prompt": "search for all usages of foo"}, False),
        ({"subagent_type": "general-purpose", "prompt": "refactor handles.go to ..."}, True),
        ({"subagent_type": "general-purpose", "description": "Refactoring struct", "prompt": "do it"}, True),
        ({"subagent_type": "claude", "prompt": "implement the rebrand and redeploy"}, True),
        ({"subagent_type": "general-purpose", "prompt": "fix the bug",
          "description": "DELEGATE-OK: parallel worktree writes, user asked for background run"}, False),
        ({"subagent_type": "db-explorer", "prompt": "delete bad rows? no, just inspect"}, False),
        ({"subagent_type": "general-purpose", "prompt": "find where the config is loaded"}, False),
        ({"subagent_type": "fork", "prompt": "migrate the schema"}, True),
    ]
    ok = True
    for ti, want in cases:
        got, verb = decide(ti)
        tag = "ok " if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"  [{tag}] block={got!s:5} want={want!s:5} verb={verb!r:14} {ti.get('subagent_type')}: {ti.get('prompt','')[:40]}")
    print("PASS" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(main())
