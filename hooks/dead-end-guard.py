#!/usr/bin/env python3
"""
PostToolUse:Edit|Write|MultiEdit — DEAD-END GUARD.

A user-facing message that tells someone something is wrong and does NOT tell
them what to run, click, or change is a dead end. The user's only exit is to
open an AI session and ask which command they forgot — which is exactly what
happened with `mytool status` printing "connect it to the same network, then
retry" and nothing to type.

CLAUDE.md carries the rule ("every dead end names its exit, in that medium's own
terms"). A rule is guidance. This is the wall: the moment such a string is
written to a file, the model is handed the line back and told to attach the
exit. Block-class only — it fires on messages that ALREADY use dead-end
phrasing, so a message that merely reports a fact stays silent.

Clean = the same message also carries something the user can act on: a
backticked command, a `--flag`, a `Settings → …` path, a URL, a named
button/menu item, a next-step verb pointing at a real command.

Protocol: JSON on stdin. exit 0 = clean/not applicable (silent).
exit 2 = stderr fed back to the model as actionable feedback (the edit already
landed; this makes the model fix it now, not at commit).
Bypass: CLAUDE_SKIP_DEAD_END_GUARD=1
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

if os.environ.get("CLAUDE_SKIP_DEAD_END_GUARD"):
    sys.exit(0)

SOURCE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".rb", ".sh", ".zsh"}
EXCLUDED_DIR = re.compile(r"(^|/)(node_modules|dist|build|vendor|\.venv|\.archive[\w.-]*)/")

# Lines that PRINT to a human. A dead-end string in a comment or a docstring is
# prose about the code, not output the user will ever read.
OUTPUT_CALL = re.compile(
    r"\b(print|echo|puts|console\.(log|error|warn)|panic|fatal|"
    r"SystemExit|sys\.exit|raise\s+\w*Error|throw\s+new\s+\w*Error|"
    r"fmt\.(Print|Errorf)\w*|log\.(Fatal|Error)\w*|toast(\.\w+)?|alert)\s*\("
)

# High-precision dead ends: each one PROMISES a next step and then withholds it.
DEAD_END = re.compile(
    r"(try again|please retry|then retry|retry later|check your (settings|config\w*|connection)|"
    r"contact (support|your admin\w*)|something went wrong|an error occurred|unexpected error|"
    r"check the logs?|see the logs?|restart the \w+|reinstall|make sure (you|it|the)|"
    r"is not configured|not supported yet)",
    re.I,
)

# Anything the reader can actually DO carries one of these.
ACTIONABLE = re.compile(
    r"`[^`]+`"  # a backticked command / flag / identifier
    r"|--[a-z][\w-]+"  # a CLI flag
    r"|https?://"  # a link to the fix
    r"|→|->"  # a UI path: Settings → Developer options → …
    r"|\b(run|press|click|tap|open|set|add|remove|export)\b\s+[A-Za-z`'\"/.$-]"
)


def _call_span(lines: list[str], start: int) -> tuple[str, int]:
    """The whole output call beginning on lines[start], paren-matched (text, lines consumed).

    Checking line by line is wrong: the formatter splits a long message, so the failure half and
    the exit half land on different lines and a per-line check flags a message that DOES name its
    command. The unit of judgement is the call, not the line.
    """
    depth, out = 0, []
    for i in range(start, min(start + 25, len(lines))):
        out.append(lines[i])
        depth += lines[i].count("(") - lines[i].count(")")
        if depth <= 0:
            break
    return "\n".join(out), len(out)


def _is_prose(line: str) -> bool:
    """Comment or docstring — prose ABOUT the code, never read by the user at a terminal."""
    return line.strip().startswith(("#", "//", "*", '"""', "'''"))


def flagged(path: Path, text: str) -> list[tuple[int, str]]:
    """(line number, first line) for every printed dead end with no exit attached (pure)."""
    lines = text.splitlines()
    hits: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        if _is_prose(lines[i]) or not OUTPUT_CALL.search(lines[i]):
            i += 1
            continue
        span, consumed = _call_span(lines, i)
        if DEAD_END.search(span) and not ACTIONABLE.search(span):
            hits.append((i + 1, lines[i].strip()))
        i += max(consumed, 1)
    return hits


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    inp = payload.get("tool_input") or {}
    path = Path(inp.get("file_path") or "")
    if path.suffix not in SOURCE_EXT or EXCLUDED_DIR.search(str(path)):
        return 0
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0

    hits = flagged(path, text)
    if not hits:
        return 0

    print(
        f"DEAD-END GUARD: {path.name} prints a message that promises a next step and "
        f"withholds it. The user reading this has no way out but to ask an AI which "
        f"command they forgot.\n"
        + "\n".join(f"  {path.name}:{n}: {line[:120]}" for n, line in hits[:5])
        + "\n\nAttach the exit IN the message, in this medium's own terms: a CLI or error "
        "string names the literal command (`mytool status`) with real values; a UI names "
        "the control on the failing screen (Settings → Developer options); an API names the "
        "field or flag to change. Success messages name the next step too.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
