r"""Detect CODE_MAP line-number drift.

For each row of the shape ``| 123 | `funcname` |`` in
`docs/CODE_MAP.md`, grep the referenced source file for the function
definition. If the actual line differs from the claimed line by more
than 5, warn.

Per-file pattern:
  - Python (.py)  → `^def funcname(`
  - JS / MJS      → `^function funcname(` / `^async function funcname(`
                    / `^const funcname `
  - HTML, CSS     → skipped (id=, .class don't map 1:1 to line anchors)

H2/H3 headers that name a file are resolved to repo-relative paths.
Bare filenames in H2 ("## photos.py at a glance") default to:
  - `*.py`              → `tools/<name>` (most common in single-app repos)
  - `*.js`/`*.html`/... → `static/<name>`

Adjust the `_resolve()` defaults if your layout differs.

Exits 0 always (WARN-only).
"""
from __future__ import annotations

import re
import sys

ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*`(\w+)`\s*\|")
HEADER = re.compile(r"^###?\s+`?([^`\s]+\.\w+)`?")


def _resolve(path: str) -> str:
    if "/" in path or path == "server.py":
        return path
    if path.endswith(".py"):
        return f"tools/{path}"
    if path.endswith((".js", ".mjs", ".html", ".css")):
        return f"static/{path}"
    return path


PY_FN = lambda sym: re.compile(rf"^def\s+{re.escape(sym)}\b")  # noqa: E731
JS_FN = lambda sym: re.compile(  # noqa: E731
    rf"^(?:async\s+)?function\s+{re.escape(sym)}\b"
    rf"|^const\s+{re.escape(sym)}\b"
)


def main() -> int:
    try:
        src = open("docs/CODE_MAP.md", encoding="utf-8").read()
    except OSError:
        return 0   # No CODE_MAP — nothing to drift-check (check only WARNs anyway).

    current_file: str | None = None
    warnings: list[str] = []

    for line_no, line in enumerate(src.splitlines(), 1):
        h = HEADER.match(line)
        if h:
            f = _resolve(h.group(1).strip("`"))
            current_file = f if f.endswith((".py", ".js", ".mjs")) else None
            continue
        r = ROW.match(line)
        if not (r and current_file):
            continue
        claimed = int(r.group(1))
        symbol = r.group(2)
        try:
            target = open(current_file, encoding="utf-8").read().splitlines()
        except OSError:
            warnings.append(
                f"docs/CODE_MAP.md:{line_no}: source file missing: {current_file}"
            )
            continue
        pattern = PY_FN(symbol) if current_file.endswith(".py") else JS_FN(symbol)
        actual_lines = [i + 1 for i, ln in enumerate(target) if pattern.match(ln)]
        if not actual_lines:
            warnings.append(
                f"docs/CODE_MAP.md:{line_no}: "
                f"{current_file}::{symbol} not found in source"
            )
            continue
        actual = min(actual_lines, key=lambda x: abs(x - claimed))
        drift = abs(actual - claimed)
        if drift > 5:
            warnings.append(
                f"docs/CODE_MAP.md:{line_no}: {current_file}::{symbol} "
                f"claims L{claimed}, actually L{actual} (drift {drift})"
            )
    for w in warnings:
        print(w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
