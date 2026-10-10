#!/usr/bin/env python3
"""Ban split-locator assertions in Playwright specs.

Detects the SPECIFIC historical anti-pattern:
    await expect(VAR).toHaveCount(N)
    await expect(VAR).toContainText(...)  # same VAR, next line

Both lines re-evaluate the locator query, BUT the second one inherits
the snapshot state from the first — under parallel load this can lock
onto stale DOM and fail without proper retry.

Combined `toContainText + toContainText` etc. are fine — both auto-retry
independently. Only the `toHaveCount` → text-method pair is flake-prone.

Exits 1 on violation.
"""
from __future__ import annotations

import glob
import re
import sys

SNAPSHOT_LOCKING = re.compile(
    r"^\s*await\s+expect\(([^)]+)\)\.(toHaveCount|toHaveLength)\b"
)
TEXT_FOLLOWUP = re.compile(
    r"^\s*await\s+expect\(([^)]+)\)\."
    r"(toContainText|toHaveText|toHaveAttribute|toHaveValue|toHaveCSS)\b"
)


def main() -> int:
    violations: list[str] = []
    spec_globs = (
        glob.glob("tests/*.spec.mjs")
        + glob.glob("tests/*.spec.ts")
        + glob.glob("tests/*.spec.js")
        + glob.glob("tests/**/*.spec.mjs", recursive=True)
        + glob.glob("tests/**/*.spec.ts", recursive=True)
        + glob.glob("tests/**/*.spec.js", recursive=True)
    )
    for f in sorted(set(spec_globs)):
        try:
            lines = open(f, encoding="utf-8").read().splitlines()
        except OSError:
            continue
        for i in range(len(lines) - 1):
            m1 = SNAPSHOT_LOCKING.match(lines[i])
            m2 = TEXT_FOLLOWUP.match(lines[i + 1])
            if not (m1 and m2):
                continue
            if m1.group(1) != m2.group(1):
                continue
            violations.append(
                f"{f}:{i+1}-{i+2}: `toHaveCount` then "
                f"`{m2.group(2)}` on `{m1.group(1).strip()}`"
            )
    if violations:
        print(
            "split-locator assertions:"
        )
        for v in violations:
            print(v)
        print("↳ combine into ONE auto-retrying assertion on the post-state.")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
