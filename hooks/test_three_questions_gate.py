#!/usr/bin/python3
"""Regression test for three-questions-gate.is_mutation().

Locks in the read-only-Ansible carve-out so a `--tags validation` scan never
re-acquires the false-positive that forced the 3Q skip dance. Run standalone:

    python3 ~/.claude/hooks/test_three_questions_gate.py

Exits 0 if all cases pass, 1 otherwise. No pytest dependency (native first).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

GATE = Path(__file__).resolve().parent / "three-questions-gate.py"
spec = importlib.util.spec_from_file_location("three_questions_gate", GATE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# (command, expected is_mutation) — True = should be GATED.
CASES = [
    # The bug this test exists for: read-only scans must NOT be gated.
    (
        "uv run ansible-playbook -i hosts.ini playbook.yml --limit myhost --tags validation",
        False,
    ),
    ("ansible-playbook playbook.yml -t validate", False),
    ("ansible-playbook playbook.yml --tags=readback", False),
    # Mixed tag list carrying a write tag stays gated.
    ("ansible-playbook playbook.yml --tags validation,deploy", True),
    # A bare apply run is still a mutation.
    ("ansible-playbook site.yml", True),
    ("uv run ansible-playbook -i hosts.ini playbook.yml --limit myhost", True),
    # Dry-run / inspection flags exempt (prior behavior preserved).
    ("ansible-playbook site.yml --check", False),
    ("ansible-playbook site.yml --syntax-check", False),
    ("ansible-playbook site.yml --list-tasks", False),
    # --diff alone still APPLIES changes -> gated. With --check it's a dry run.
    ("ansible-playbook site.yml --diff", True),
    ("ansible-playbook site.yml --check --diff", False),
    # Unknown tag is not in the read-only allowlist -> gated.
    ("ansible-playbook site.yml --tags deploy", True),
    # Other mutation families unaffected.
    ("terraform apply", True),
    ("kubectl delete pod foo", True),
    ("git push --force origin main", True),
    # Plain reads are never gated.
    ("ls -la /etc", False),
    ("cat docs/VERIFIED-STATE.md", False),
]


def main() -> int:
    failures = []
    for command, want in CASES:
        got, matched = mod.is_mutation(command)
        if got != want:
            failures.append((command, want, got, matched))

    for command, want, got, matched in failures:
        print(
            f"FAIL: {command!r}\n      expected is_mutation={want}, got {got} "
            f"(matched={matched!r})",
            file=sys.stderr,
        )

    total = len(CASES)
    if failures:
        print(f"\n{len(failures)}/{total} cases FAILED", file=sys.stderr)
        return 1
    print(f"all {total} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
