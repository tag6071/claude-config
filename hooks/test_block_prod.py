#!/usr/bin/python3
"""
Regression tests for block-prod prose elision.

No pytest dependency (native first). Run standalone:
    python3 ~/.claude/hooks/test_block_prod.py
Exits 0 all-pass / 1 on failure.

The pin that matters: a destructive verb MENTIONED in a commit message or heredoc
body is not the verb. `block-prod` blocked a commit whose message said
"un-truncate" because the raw text contained TRUNCATE. But a real TRUNCATE outside
the prose must STILL block — that is the whole point of the guard.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent


def run(cmd: str) -> int:
    p = subprocess.run(
        [sys.executable, str(HOOKS / "block-prod.py")],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
        text=True,
        capture_output=True,
    )
    return p.returncode


# (command, expected_rc, note)  rc: 0 allow, 2 block
CASES = [
    # --- prose mentioning a verb must NOT block ---
    (
        "git commit -m 'fix: strip prose so un-truncate no longer self-blocks'",
        0,
        "the exact failure: TRUNCATE inside a commit message",
    ),
    (
        "git commit -q -F - <<'EOF'\nexplains why we no longer TRUNCATE in tests\nand never DROP the prod table\nEOF",
        0,
        "destructive verbs inside a heredoc commit body",
    ),
    (
        'git commit -m "note: DELETE FROM staging is fine, prod is off-limits"',
        0,
        "double-quoted message",
    ),
    # --- real destructive commands must STILL block ---
    (
        "psql -h prod -c 'TRUNCATE users'",
        2,
        "a genuine TRUNCATE outside any prose — the guard's reason to exist",
    ),
    (
        "git commit -F - <<'EOF'\nharmless prose\nEOF\npsql -c 'TRUNCATE users'",
        2,
        "real TRUNCATE AFTER a heredoc must not be masked by the elision",
    ),
    # --- unrelated commands sail through ---
    ("git status --short", 0, "hot path"),
    ("git commit -m 'ordinary message'", 0, "no verb anywhere"),
]


def main() -> int:
    fails = 0
    for cmd, want, note in CASES:
        got = run(cmd)
        if got != want:
            fails += 1
            verb = {0: "allow", 2: "block"}
            print(f"FAIL  expected={verb[want]} got={verb.get(got, got)}  {cmd[:60]!r}")
            print(f"      note: {note}")
    total = len(CASES)
    if fails:
        print(f"\n{fails}/{total} FAILED")
        return 1
    print(f"{total}/{total} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
