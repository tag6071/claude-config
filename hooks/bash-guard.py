#!/usr/bin/python3
"""
PreToolUse:Bash dispatcher — run all Bash guard hooks in ONE Python process.

Why: each `python3 hookX.py` spawn costs ~19ms of interpreter boot. With 6
Bash guards that's ~114ms of pure startup per Bash tool call, paid on every
command. This dispatcher boots Python once, then runs each guard's existing
`main()` in-process — same checks, same exit codes, same stderr, ~4x faster.

The individual guard files are UNTOUCHED (still runnable standalone). This file
only orchestrates: read the stdin payload once, replay it to each guard, capture
its exit code + stderr, and block on the FIRST that returns 2 — preserving the
original hook order and fail-on-first-block semantics.

A guard that RAISES is treated as non-blocking (matches old behavior: a crashed
standalone hook exits 1, which Claude Code does not treat as a block). Its
traceback is surfaced to stderr so breakage is visible, not silent.

Guard list is PER-HOST: read from `bash-guard.conf` (sibling file, one guard
basename per line, '#' comments ok). Mac and homeserver wire different guard sets, so
the list lives in conf while this dispatcher stays identical across hosts. If
conf is absent, fall back to the full known set (missing files skip cleanly).

Exit: 0 allow · 2 block (first blocking guard's stderr is forwarded).
"""
from __future__ import annotations

import importlib.util
import io
import sys
import traceback
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
CONF = HOOKS_DIR / "bash-guard.conf"

# Fallback if bash-guard.conf is absent. Order = original settings.json Bash
# chain, with block-secrets (the old Bash|Read group) appended last.
DEFAULT_GUARDS = [
    "block-prod",
    "enforce-green-commit",
    "lessons-trail",
    "db-safety",
    "three-questions-gate",
    "block-secrets",
]


def guard_list() -> list[str]:
    if not CONF.exists():
        return DEFAULT_GUARDS
    names: list[str] = []
    for raw in CONF.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            names.append(line.removesuffix(".py"))
    return names or DEFAULT_GUARDS


def load_guard(name: str):
    path = HOOKS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_guard(mod, raw: str) -> tuple[int, str]:
    """Run a guard's main() with `raw` as stdin; capture (exit_code, stderr)."""
    old_stdin, old_stderr = sys.stdin, sys.stderr
    sys.stdin = io.StringIO(raw)
    cap = io.StringIO()
    sys.stderr = cap
    code = 0
    try:
        ret = mod.main()
        code = ret if isinstance(ret, int) else 0
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception:
        # Match old behavior: a crashed standalone hook exits 1 (non-blocking).
        traceback.print_exc(file=cap)
        code = 1
    finally:
        sys.stdin, sys.stderr = old_stdin, old_stderr
    return code, cap.getvalue()


def main() -> int:
    raw = sys.stdin.read()
    for name in guard_list():
        try:
            mod = load_guard(name)
        except Exception:
            # A guard that won't even load (e.g. not present on this host) must
            # not wedge every Bash call — skip it.
            sys.stderr.write(f"[bash-guard] skipping {name} (not loadable on this host)\n")
            continue
        code, err = run_guard(mod, raw)
        if code == 2:
            if err:
                sys.stderr.write(err)
            return 2
        # Non-blocking crash (code 1, etc.): surface but continue (old semantics).
        if code not in (0, 2) and err:
            sys.stderr.write(err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
