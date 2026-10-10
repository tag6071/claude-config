#!/usr/bin/env python3
"""
UserPromptSubmit hook — lazy-load topic-triggerable rule lessons.

The bulky "hard rules" that keep growing are split OUT of the always-loaded
CLAUDE.md into individual reference files under ~/.claude/lessons/. Each lesson
file carries its own trigger patterns in frontmatter. On each prompt this hook
scans the dir and injects ONLY the lessons whose triggers match — no match
means nothing is injected, so the files cost zero tokens until relevant.

This is the "reference files, loaded on demand" layer. Adding a new lesson =
drop a file in ~/.claude/lessons/ (no code change). Proactive tone rules
(no day-management, no refusal/uncertainty theater, no menus, lookup-first)
do NOT live here — they have no reliable keyword trigger and stay always-on
in CLAUDE.md.

Lesson file format (~/.claude/lessons/<name>.md):
    ---
    triggers:
      - 'regex matched case-insensitively against the prompt'
      - 'another regex'
    ---
    <lesson body, injected verbatim when any trigger matches>

Protocol (Claude Code UserPromptSubmit hook):
  stdin  : JSON, includes {"prompt": "<the user's message>"}
  stdout : JSON with hookSpecificOutput.additionalContext (injected verbatim)
  exit 0 : always (this hook never blocks a prompt)

Bypass: CLAUDE_SKIP_RULE_CARDS=1
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

BYPASS_ENV = "CLAUDE_SKIP_RULE_CARDS"
LESSONS_DIR = Path(os.path.expanduser("~/.claude/lessons"))


def load_prompt() -> str:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return ""
    if isinstance(data, dict):
        return str(data.get("prompt", "") or "")
    return ""


def parse_lesson(text: str) -> tuple[list[str], str]:
    """Return (trigger_regexes, body) from a lesson file's content.

    Frontmatter is a minimal hand-parsed block between the first two `---`
    lines: a `triggers:` key followed by `- '<regex>'` list items. No YAML
    dependency — native first, and the format is fixed and simple.
    """
    if not text.startswith("---"):
        return [], text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return [], text.strip()
    front, body = parts[1], parts[2]
    triggers: list[str] = []
    in_triggers = False
    for raw in front.splitlines():
        line = raw.strip()
        if line.startswith("triggers:"):
            in_triggers = True
            continue
        if in_triggers and line.startswith("- "):
            val = line[2:].strip().strip("'\"")
            if val:
                triggers.append(val)
        elif in_triggers and line and not line.startswith("-"):
            in_triggers = False
    return triggers, body.strip()


def matching_lessons(prompt: str) -> list[str]:
    if not LESSONS_DIR.is_dir():
        return []
    hits: list[str] = []
    for path in sorted(LESSONS_DIR.glob("*.md")):
        try:
            triggers, body = parse_lesson(path.read_text())
        except Exception:
            continue
        if not body:
            continue
        for pat in triggers:
            try:
                if re.search(pat, prompt, re.IGNORECASE):
                    hits.append(body)
                    break
            except re.error:
                continue  # a malformed regex in one lesson never breaks the rest
    return hits


def main() -> int:
    if os.environ.get(BYPASS_ENV):
        return 0
    prompt = load_prompt()
    if not prompt:
        return 0
    hits = matching_lessons(prompt)
    if not hits:
        return 0  # nothing relevant -> inject nothing -> zero cost
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n\n".join(hits),
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
