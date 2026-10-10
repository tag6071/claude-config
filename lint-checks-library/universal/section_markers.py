#!/usr/bin/env python3
"""Section-marker hygiene — single-line titles only.

Detects multi-line section titles in `^# -----` style blocks (Python,
shell). Extensible to JS/Rust/Go `// -----` blocks via the SCAN_GLOBS
list at the top — tune per project.

A valid section is:
    # ---------------------------------------------------------------------------
    # <single-line title>
    # ---------------------------------------------------------------------------

Multi-line titles break `awk` recipes that grep section markers (the
recipe assumes one comment line between the two rule lines).

Exits 1 on violation.
"""
from __future__ import annotations

import glob
import re
import sys

# Tune per-project: which source globs to scan. Add as you add languages.
SCAN_GLOBS = [
    "server.py",
    "main.py",
    "app.py",
    "tools/*.py",
    "src/**/*.py",
    "scripts/*.py",
]

# Comment-style markers. Each entry: (regex matching the rule line,
# regex testing whether the title line looks like a comment).
STYLES = [
    (re.compile(r"^#\s*-{60,}\s*$"), re.compile(r"^\s*#")),       # Python / shell
    (re.compile(r"^//\s*-{60,}\s*$"), re.compile(r"^\s*//")),     # JS / Go / Rust
]


def _resolve_files() -> list[str]:
    seen = set()
    out = []
    for g in SCAN_GLOBS:
        for f in sorted(glob.glob(g, recursive=True)):
            if f not in seen:
                seen.add(f)
                out.append(f)
    return out


def main() -> int:
    violations: list[str] = []
    for f in _resolve_files():
        try:
            lines = open(f, encoding="utf-8").read().splitlines()
        except OSError:
            continue
        i = 0
        while i < len(lines):
            matched_style = None
            for rule, comment in STYLES:
                if rule.match(lines[i]):
                    matched_style = (rule, comment)
                    break
            if not matched_style:
                i += 1
                continue
            rule, comment = matched_style
            if i + 2 >= len(lines):
                violations.append(f"{f}:{i+1}: marker at end of file")
                break
            title = lines[i + 1]
            closer = lines[i + 2]
            if not comment.match(title):
                violations.append(f"{f}:{i+2}: marker not followed by comment")
            elif not rule.match(closer):
                violations.append(
                    f"{f}:{i+3}: multi-line section title — collapse to ONE line"
                )
            i += 3
    for v in violations:
        print(v)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
