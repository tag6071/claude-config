#!/usr/bin/python3
"""
Shared helpers for the PreToolUse Bash guards.

Underscore filename (not hyphenated) so it is importable — the guards themselves
are hyphenated and loaded via importlib by bash-guard.py, but they can `import
hook_common` because sys.path[0] is the hooks dir under both the standalone
(`python3 .../block-prod.py`) and dispatcher (`python3 .../bash-guard.py`)
invocations. Verified from a foreign cwd; a dispatcher-path test pins it.
"""
from __future__ import annotations

import re

# Body between `<<TAG` (or `<<'TAG'` / `<<"TAG"` / `<<-TAG`) and a line that is
# just TAG. Shell syntax AROUND the heredoc is preserved.
_HEREDOC = re.compile(
    r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?^\1\s*$",
    flags=re.DOTALL | re.MULTILINE,
)

# `git ... commit ... -m '<arg>'` / -m "<arg>". Captured prefix is kept so the
# command SHAPE stays visible; only the message text is elided. Non-greedy,
# terminated on the same quote class it opened with.
_GIT_COMMIT_MSG = re.compile(
    r"(\bgit\b[^|;&\n]*?\bcommit\b[^|;&\n]*?\s-m\s+)(['\"])((?:(?!\2).)*?)\2",
    flags=re.DOTALL,
)


def elide_prose(command: str) -> str:
    """Blank out heredoc bodies and `git commit -m` message text before scanning.

    PROSE THAT MENTIONS a verb/secret/probe is not the thing itself. A commit
    message saying "un-truncate" is not a TRUNCATE; a heredoc documenting
    `oidc.yml` is not a read of it. Shell OUTSIDE the prose is untouched, so a
    real destructive command lurking after a heredoc still gets caught.
    """
    out = _HEREDOC.sub("<heredoc-elided>", command)
    return _GIT_COMMIT_MSG.sub(r"\1<commit-msg-elided>", out)
