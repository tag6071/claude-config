#!/usr/bin/python3
"""
Locks the shared elision helper and its import robustness.

No pytest dependency (native first). Run standalone:
    python3 ~/.claude/hooks/test_hook_common.py
Exits 0 all-pass / 1 on failure.

Two things this pins:
  1. elide_prose blanks heredoc bodies and `git commit -m` text, nothing else.
  2. Every guard that imports hook_common still loads when exec'd via importlib
     from a FOREIGN sys.path — the exact context that failed during the collapse
     to a shared helper. A broken import there makes bash-guard.py silently SKIP
     a security guard, so this must never regress unnoticed.
"""
from __future__ import annotations

import importlib.util as iu
import os
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
spec = iu.spec_from_file_location("hook_common", HOOKS / "hook_common.py")
hc = iu.module_from_spec(spec)
spec.loader.exec_module(hc)

GUARDS_USING_HELPER = ["block-prod", "block-secrets", "probe-guard"]


def check_elide() -> int:
    fails = 0
    # heredoc body elided, verb inside vanishes
    got = hc.elide_prose("git commit -F - <<'EOF'\nun-truncate the thing\nEOF")
    if "truncate" in got.lower():
        fails += 1
        print(f"FAIL  heredoc body not elided: {got!r}")
    # shell AFTER the heredoc survives
    got = hc.elide_prose("git commit -F - <<'EOF'\nprose\nEOF\npsql -c 'TRUNCATE x'")
    if "TRUNCATE" not in got:
        fails += 1
        print(f"FAIL  real command after heredoc was eaten: {got!r}")
    # commit -m message elided, prefix kept
    got = hc.elide_prose("git commit -m 'fix: un-truncate'")
    if "truncate" in got.lower() or "git commit" not in got:
        fails += 1
        print(f"FAIL  commit -m not elided cleanly: {got!r}")
    # a plain command is untouched
    if hc.elide_prose("ls -la") != "ls -la":
        fails += 1
        print("FAIL  elide_prose mutated an ordinary command")
    return fails


def check_foreign_import() -> int:
    """Load each guard via importlib in a SUBPROCESS whose sys.path[0] is NOT the
    hooks dir — the exact context that broke during the collapse.

    os.chdir alone is not enough: sys.path is unaffected by it, and this test
    runner already put the hooks dir on sys.path. Only a fresh `python3 -c`
    interpreter from a foreign cwd reproduces sys.path[0] != hooks dir, so the
    guard's own `sys.path.insert(__file__ dir)` is the only thing that saves it.
    """
    import subprocess

    fails = 0
    foreign = os.path.dirname(str(HOOKS)) or "/"  # ~/.claude, not the hooks dir
    for g in GUARDS_USING_HELPER:
        harness = (
            "import importlib.util as iu, sys\n"
            f"assert {str(HOOKS)!r} not in sys.path, 'sys.path already has hooks dir'\n"
            f"s = iu.spec_from_file_location({g.replace('-', '_')!r}, {str(HOOKS / f'{g}.py')!r})\n"
            "m = iu.module_from_spec(s); s.loader.exec_module(m)\n"
            "assert callable(m.main)\n"
        )
        r = subprocess.run(
            [sys.executable, "-c", harness], cwd=foreign, capture_output=True, text=True
        )
        if r.returncode != 0:
            fails += 1
            last = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "?"
            print(f"FAIL  {g} does not load from foreign sys.path: {last}")
    return fails


def main() -> int:
    fails = check_elide() + check_foreign_import()
    if fails:
        print(f"\n{fails} FAILED")
        return 1
    print("all hook_common cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
