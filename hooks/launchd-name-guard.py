#!/usr/bin/python3
"""
PreToolUse hook (Write/Edit/MultiEdit): every background job must say what it is.

macOS labels a launch agent in System Settings > General > Login Items &
Extensions with the BASENAME OF ProgramArguments[0] -- not the Label, not the
plist filename, not any comment inside it. Point launchd at an interpreter and
the user gets a list of switches called "zsh", "uv", "python3", "ssh", none of
which say what is running or why, and none of which can be safely turned off
because nobody can tell which is which.

The fix is always the same: launchd starts a small wrapper executable whose
FILENAME is the description, in <System> <Thing> <Action> form --
"Server Disk Report", "Nightly Notes Sync" -- and the wrapper execs
the real command.

    #!/bin/zsh -l
    exec uv run "${0:A:h}/thing.py" "$@"

The general rule this enforces, of which launchd is one instance: ANY artifact
that surfaces in a user-facing system UI carries a name that identifies what it
does. Never the interpreter's name, never a generic one.

Fires only on files that are actually launchd job definitions (a .plist
declaring a Label plus ProgramArguments/Program). Fail-open on any parse error.

Exits: 0 allow - 2 block (stderr shown to Claude).
Bypass (user, single shell): export CLAUDE_ALLOW_LAUNCHD_NAME=1
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Names that describe HOW a job runs, never WHAT it does. Matched against the
# basename of the program launchd starts.
INTERPRETERS = {
    "sh", "bash", "zsh", "ksh", "fish", "dash", "csh", "tcsh",
    "python", "python2", "python3", "pythonw", "uv", "uvx", "pipx",
    "node", "npm", "npx", "bun", "deno", "ruby", "perl", "php", "java", "osascript",
    "ssh", "scp", "rsync", "curl", "wget", "env", "open", "sudo", "nice", "caffeinate",
    "docker", "make", "cargo", "go", "swift", "dotnet", "conda", "poetry", "rr",
}

# <string>...</string> immediately following the given <key>.
PROGRAM_ARGUMENTS = re.compile(
    r"<key>\s*ProgramArguments\s*</key>\s*<array>\s*<string>([^<]*)</string>",
    re.IGNORECASE | re.DOTALL,
)
PROGRAM = re.compile(
    r"<key>\s*Program\s*</key>\s*<string>([^<]*)</string>", re.IGNORECASE | re.DOTALL
)
LABEL = re.compile(r"<key>\s*Label\s*</key>\s*<string>([^<]*)</string>", re.IGNORECASE | re.DOTALL)


def is_launchd_plist(target: Path, text: str) -> bool:
    if target.suffix.lower() != ".plist":
        return False
    return bool(LABEL.search(text)) and bool(PROGRAM_ARGUMENTS.search(text) or PROGRAM.search(text))


def launched_program(text: str) -> str | None:
    for pattern in (PROGRAM, PROGRAM_ARGUMENTS):
        found = pattern.search(text)
        if found:
            return found.group(1).strip()
    return None


def basename(program: str) -> str:
    return program.rstrip("/").rsplit("/", 1)[-1]


def offence(program: str) -> str | None:
    """-> the reason this program name is unacceptable, or None if it is fine."""
    name = basename(program)
    if not name:
        return None
    if name.lower() in INTERPRETERS or name.lower().removesuffix(".sh") in INTERPRETERS:
        return f'launchd would label this job "{name}" -- an interpreter, not a description'
    # A lone lowercase token with no separators reads as a command, not a name.
    if re.fullmatch(r"[a-z0-9._-]+", name) and not re.search(r"[ _-]", name.strip("-_")):
        return f'launchd would label this job "{name}", which does not say what it does'
    return None


def written_text(tool: str, ti: dict) -> str:
    if tool == "Write":
        return ti.get("content") or ""
    if tool == "Edit":
        return ti.get("new_string") or ""
    if tool == "MultiEdit":
        return "\n".join(e.get("new_string") or "" for e in ti.get("edits") or [])
    return ""


def main() -> int:
    if os.environ.get("CLAUDE_ALLOW_LAUNCHD_NAME"):
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input") or {}
    path = ti.get("file_path") or ""
    if not path:
        return 0

    text = written_text(tool, ti)
    target = Path(path)
    if not is_launchd_plist(target, text):
        return 0

    program = launched_program(text)
    if not program:
        return 0
    reason = offence(program)
    if not reason:
        return 0

    sys.stderr.write(
        f"BLOCKED by ~/.claude/hooks/launchd-name-guard.py -- {target.name}\n"
        f"  {reason}.\n\n"
        "macOS labels a background job in System Settings > General > Login Items &\n"
        "Extensions with the BASENAME OF ProgramArguments[0]. Not the Label, not the\n"
        "plist filename. A list of entries called \"zsh\" and \"uv\" is a list nobody can\n"
        "audit or safely switch off.\n\n"
        "Point launchd at a wrapper whose FILENAME is the description, in\n"
        "<System> <Thing> <Action> form -- \"Server Disk Report\",\n"
        "\"Nightly Notes Sync\" -- and let the wrapper exec the real command:\n\n"
        '    #!/bin/zsh -l\n'
        '    exec uv run "${0:A:h}/thing.py" "$@"\n\n'
        "  <key>ProgramArguments</key>\n"
        "  <array><string>/path/to/Nightly Notes Sync</string></array>\n\n"
        "The rule generalises: anything you create that shows up in a user-facing\n"
        "system UI carries a name that identifies what it does.\n"
        "Bypass (user-set, single shell): export CLAUDE_ALLOW_LAUNCHD_NAME=1\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
