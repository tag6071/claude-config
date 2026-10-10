#!/usr/bin/python3
"""
Pins git-identity-guard.py. Run: python3 ~/.claude/hooks/test_git_identity_guard.py

Every case goes through bash-guard.py (the real dispatcher), not the guard in
isolation — so a guard that works but is unwired still FAILS this test.

Case 1 is the original defect, verbatim.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

DISPATCHER = Path(__file__).resolve().parent / "bash-guard.py"
BLOCK, ALLOW = 2, 0

PERSONAL = "you@example.com"
LAB = "12345678+your-github@users.noreply.github.com"

CASES: list[tuple[int, str, str]] = [
    # --- MUST BLOCK -------------------------------------------------------------
    (BLOCK, "the original defect, verbatim",
     f'cd /Users/you/code/myrepo && git add -A && git -c user.email={PERSONAL} '
     f'-c user.name=yourname commit -q -m "test: disambiguate locator"'),
    (BLOCK, "env-prefix override",
     f'GIT_AUTHOR_EMAIL={PERSONAL} git commit -m "x"'),
    (BLOCK, "committer env-prefix override",
     f'GIT_COMMITTER_EMAIL={PERSONAL} git commit -m "x"'),
    (BLOCK, "--author= with name+email",
     f'git commit --author="yourname <{PERSONAL}>" -m "x"'),
    (BLOCK, "writing personal identity into config",
     f'git config --global user.email {PERSONAL}'),
    (BLOCK, "filter-branch env-filter injection",
     f"git filter-branch -f --env-filter 'export GIT_AUTHOR_EMAIL={PERSONAL}' -- --all"),
    (BLOCK, "ANY unapproved identity, not just the personal one",
     'git -c user.email=someone@else.com commit -m "x"'),
    (BLOCK, "unapproved name via -c",
     'git -c user.name=yourname commit -m "x"'),

    # --- MUST ALLOW -------------------------------------------------------------
    (ALLOW, "the normal path: plain commit, identity flows from config",
     'git add -A && git commit -m "feat: the thing"'),
    (ALLOW, "allowlisted identity passed explicitly (e.g. a sanctioned rewrite)",
     f'git -c user.email={LAB} -c user.name=your-git-user commit -m "x"'),
    (ALLOW, "reading/filtering by author is not injecting one",
     f'git log --all --author={PERSONAL} --format="%h"'),
    (ALLOW, "auditing history for the leak must not be blocked",
     f"git log --all --format='%ae' | grep -c '{PERSONAL}'"),
    (ALLOW, "commit message that merely MENTIONS an email (elide_prose)",
     'git commit -m "fix: bounce handling for support@acme.com"'),
    (ALLOW, "unrelated git read",
     'git status --short && git show --stat HEAD'),
    (ALLOW, "not a git command at all",
     'echo hello && ls -la'),
]


def run(command: str) -> tuple[int, str]:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    p = subprocess.run(
        [sys.executable, str(DISPATCHER)],
        input=payload, capture_output=True, text=True,
    )
    return p.returncode, p.stderr


def main() -> int:
    failed = 0
    for want, label, command in CASES:
        got, err = run(command)
        ok = got == want
        if not ok:
            failed += 1
        verb = {BLOCK: "BLOCK", ALLOW: "ALLOW"}
        mark = "ok  " if ok else "FAIL"
        print(f"{mark} want {verb[want]:5s} got {verb.get(got, got)!s:5s}  {label}")
        if not ok and err:
            print(f"       stderr: {err.strip().splitlines()[0][:100]}")
    total = len(CASES)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
