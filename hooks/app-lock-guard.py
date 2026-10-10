#!/usr/bin/python3
"""
PreToolUse:Bash guard — block locking a file so it can't be changed in place.

An app's settings must stay changeable from INSIDE the app. Making its config
immutable / read-only (chflags uchg, chattr +i, chmod a-w / 444) "protects" the
setting by forcing the user to run terminal commands before the app can save
again — an out-of-app manual process. The user rejected this outright after an app's config files
were locked: "anything that has to do with the app has to be fully within the
app. Self-contained … or never."

Fix the setting itself, or flip the app's OWN toggle (e.g. its auto-update
option), and stop. If a thing can only be protected from outside the app, say
so instead of building the workaround.

Unlocking (nouchg, chattr -i, chmod +w) is always allowed — it undoes a lock.
Reads JSON from stdin (Claude Code hook protocol). Exit 0 allow / 2 block.
Bypass: CLAUDE_ALLOW_FILE_LOCK=1.
"""
from __future__ import annotations

import json
import os
import re
import sys

from hook_common import elide_prose

BYPASS = "CLAUDE_ALLOW_FILE_LOCK"

LOCK_RE = re.compile(
    r"(?:^|[\n;|&(]|\bsudo\s+|\bxargs\s+)\s*"
    r"(chflags|chattr|chmod)\s+(?:-[RHLPVfhv]+\s+)*(\S+)((?:\s+\S+)*)",
    re.I,
)
# Key files legitimately go read-only (ssh refuses group/world-readable keys).
KEY_RE = re.compile(r"(\.pem|\.key|/id_[\w-]+|\.ssh/)", re.I)
IMMUTABLE_FLAGS = {"uchg", "uchange", "uimmutable", "schg", "schange", "simmutable",
                   "uappnd", "uappend", "sappnd", "sappend"}


def _locks(tool: str, mode: str, targets: str) -> bool:
    tool, mode = tool.lower(), mode.lower()
    if tool == "chflags":
        return any(f in IMMUTABLE_FLAGS for f in mode.split(","))
    if tool == "chattr":
        return mode.startswith("+") and "i" in mode
    # chmod: the owner loses write. Key files are exempt.
    if KEY_RE.search(targets):
        return False
    if mode.isdigit():
        return len(mode) >= 3 and mode[-3] in "0145"
    for clause in mode.split(","):
        m = re.fullmatch(r"([ugoa]*)([-=])([rwxXst]*)", clause)
        if m and (not m.group(1) or set(m.group(1)) & {"u", "a"}):
            if (m.group(2) == "-") == ("w" in m.group(3)):
                return True
    return False


def is_lock(cmd: str) -> bool:
    for m in LOCK_RE.finditer(elide_prose(cmd)):
        if _locks(m.group(1), m.group(2), m.group(3) or ""):
            return True
    return False


def main() -> int:
    if os.environ.get(BYPASS):
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if not cmd or not is_lock(cmd):
        return 0
    sys.stderr.write(
        "BLOCKED: this locks a file so it can't be changed in place.\n"
        "App settings must stay changeable from INSIDE the app — a lock forces the\n"
        "user to unlock from a terminal before the app can save. That is an\n"
        "out-of-app manual process, which the user has banned.\n"
        "Instead: set the value and stop, or use the app's own toggle. If it can\n"
        "only be protected from outside the app, tell the user that plainly.\n"
        "Undo an existing lock: chflags nouchg <file>  /  chmod u+w <file>\n"
        f"  offending: {cmd[:200]}\n"
        f"  override (only if the user asked for a lock): {BYPASS}=1\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
